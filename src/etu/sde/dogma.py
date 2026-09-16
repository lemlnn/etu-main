"""static dogma and related inventory queries used by item inspection views"""

from etu.sde.database import connect


REQUIRED_SKILL_ATTRIBUTES = (
    (182, 277),
    (183, 278),
    (184, 279),
    (1285, 1286),
    (1289, 1287),
    (1290, 1288),
)


def get_type_dogma_attributes(
    type_id: int,
) -> list[dict]:
    with connect() as db:
        rows = db.execute("""
            SELECT
                type_dogma_attributes.attribute_id,
                type_dogma_attributes.value,
                type_dogma_attributes.sort_index,
                dogma_attributes.name,
                dogma_attributes.display_name,
                dogma_attributes.icon_id,
                dogma_attributes.published,
                dogma_attributes.display_when_zero,
                dogma_attributes.data_type,
                dogma_units.unit_id,
                dogma_units.name AS unit_name,
                dogma_units.display_name AS unit_display_name

            FROM type_dogma_attributes

            JOIN dogma_attributes
                ON type_dogma_attributes.attribute_id
                    = dogma_attributes.attribute_id

            LEFT JOIN dogma_units
                ON dogma_attributes.unit_id
                    = dogma_units.unit_id

            WHERE type_dogma_attributes.type_id = ?

            ORDER BY type_dogma_attributes.sort_index
        """, (type_id,)).fetchall()

    result = [dict(row) for row in rows]

    group_ids = {
        int(row["value"])
        for row in result
        if row["name"].startswith("chargeGroup")
        and row["value"] > 0
    }

    if group_ids:
        placeholders = ",".join(
            "?" for _ in group_ids
        )

        with connect() as db:
            group_rows = db.execute(
                f"""
                SELECT group_id, name
                FROM groups
                WHERE group_id IN ({placeholders})
                """,
                tuple(sorted(group_ids)),
            ).fetchall()

        group_names = {
            row["group_id"]: row["name"]
            for row in group_rows
        }

        for row in result:
            if row["name"].startswith("chargeGroup"):
                row["reference_name"] = group_names.get(
                    int(row["value"])
                )

    return result


def get_type_dogma_effects(
    type_id: int,
) -> list[dict]:
    with connect() as db:
        rows = db.execute("""
            SELECT
                type_dogma_effects.effect_id,
                type_dogma_effects.is_default,
                type_dogma_effects.sort_index,
                dogma_effects.name,
                dogma_effects.display_name,
                dogma_effects.icon_id,
                dogma_effects.published

            FROM type_dogma_effects

            JOIN dogma_effects
                ON type_dogma_effects.effect_id
                    = dogma_effects.effect_id

            WHERE type_dogma_effects.type_id = ?

            ORDER BY type_dogma_effects.sort_index
        """, (type_id,)).fetchall()

    return [dict(row) for row in rows]


def get_direct_skill_requirements(
    type_id: int,
) -> list[dict]:
    attribute_ids = {
        attribute_id
        for pair in REQUIRED_SKILL_ATTRIBUTES
        for attribute_id in pair
    }
    placeholders = ",".join(
        "?" for _ in attribute_ids
    )

    with connect() as db:
        rows = db.execute(
            f"""
            SELECT attribute_id, value
            FROM type_dogma_attributes
            WHERE type_id = ?
              AND attribute_id IN ({placeholders})
            """,
            (type_id, *sorted(attribute_ids)),
        ).fetchall()

        values = {
            row["attribute_id"]: row["value"]
            for row in rows
        }

        requirements = []

        for skill_attribute, level_attribute in (
            REQUIRED_SKILL_ATTRIBUTES
        ):
            skill_value = values.get(
                skill_attribute
            )

            if not skill_value:
                continue

            skill_id = int(skill_value)
            skill = db.execute("""
                SELECT type_id, name
                FROM types
                WHERE type_id = ?
            """, (skill_id,)).fetchone()

            if skill is None:
                continue

            level = int(
                round(
                    values.get(
                        level_attribute,
                        0,
                    )
                )
            )

            requirements.append({
                "type_id": skill["type_id"],
                "name": skill["name"],
                "level": level,
            })

    return requirements


def get_skill_requirement_tree(
    type_id: int,
    max_depth: int = 8,
) -> list[dict]:
    def build(
        current_type_id,
        depth,
        path,
    ):
        if depth >= max_depth:
            return []

        result = []

        for requirement in get_direct_skill_requirements(
            current_type_id
        ):
            skill_id = requirement["type_id"]
            node = dict(requirement)

            if skill_id in path:
                node["requirements"] = []
            else:
                node["requirements"] = build(
                    skill_id,
                    depth + 1,
                    path | {skill_id},
                )

            result.append(node)

        return result

    return build(
        type_id,
        0,
        {type_id},
    )


def get_type_variations(
    type_id: int,
) -> list[dict]:
    with connect() as db:
        selected = db.execute("""
            SELECT
                type_id,
                variation_parent_type_id
            FROM types
            WHERE type_id = ?
        """, (type_id,)).fetchone()

        if selected is None:
            return []

        parent_id = (
            selected["variation_parent_type_id"]
            or selected["type_id"]
        )

        rows = db.execute("""
            SELECT
                types.type_id,
                types.name,
                types.meta_group_id,
                groups.group_id,
                groups.name AS group_name

            FROM types

            JOIN groups
                ON types.group_id = groups.group_id

            WHERE types.published = 1
              AND (
                    types.type_id = ?
                    OR types.variation_parent_type_id = ?
              )

            ORDER BY
                COALESCE(types.meta_group_id, 1),
                types.name
        """, (
            parent_id,
            parent_id,
        )).fetchall()

    return [dict(row) for row in rows]


def get_type_used_with(
    type_id: int,
) -> list[dict]:
    with connect() as db:
        group_rows = db.execute("""
            SELECT DISTINCT
                CAST(type_dogma_attributes.value AS INTEGER)
                    AS group_id

            FROM type_dogma_attributes

            JOIN dogma_attributes
                ON type_dogma_attributes.attribute_id
                    = dogma_attributes.attribute_id

            WHERE type_dogma_attributes.type_id = ?
              AND dogma_attributes.name LIKE 'chargeGroup%'
              AND type_dogma_attributes.value > 0
        """, (type_id,)).fetchall()

        group_ids = [
            row["group_id"]
            for row in group_rows
        ]

        if not group_ids:
            return []

        size_row = db.execute("""
            SELECT type_dogma_attributes.value

            FROM type_dogma_attributes

            JOIN dogma_attributes
                ON type_dogma_attributes.attribute_id
                    = dogma_attributes.attribute_id

            WHERE type_dogma_attributes.type_id = ?
              AND dogma_attributes.name = 'chargeSize'

            LIMIT 1
        """, (type_id,)).fetchone()

        charge_size = (
            size_row["value"]
            if size_row is not None
            else None
        )

        group_placeholders = ",".join(
            "?" for _ in group_ids
        )

        parameters = list(group_ids)
        size_filter = ""

        if charge_size is not None:
            size_filter = """
                AND EXISTS (
                    SELECT 1
                    FROM type_dogma_attributes AS candidate_size
                    JOIN dogma_attributes AS size_attribute
                        ON candidate_size.attribute_id
                            = size_attribute.attribute_id
                    WHERE candidate_size.type_id = types.type_id
                      AND size_attribute.name = 'chargeSize'
                      AND candidate_size.value = ?
                )
            """
            parameters.append(charge_size)

        rows = db.execute(
            f"""
            SELECT
                types.type_id,
                types.name,
                types.meta_group_id,
                groups.group_id,
                groups.name AS group_name

            FROM types

            JOIN groups
                ON types.group_id = groups.group_id

            WHERE types.published = 1
              AND types.group_id IN ({group_placeholders})
              {size_filter}

            ORDER BY
                COALESCE(types.meta_group_id, 1),
                types.name
            """,
            tuple(parameters),
        ).fetchall()

    return [dict(row) for row in rows]


def get_type_materials(
    type_id: int,
) -> list[dict]:
    with connect() as db:
        rows = db.execute("""
            SELECT
                type_materials.material_type_id AS type_id,
                types.name,
                types.meta_group_id,
                type_materials.quantity

            FROM type_materials

            JOIN types
                ON type_materials.material_type_id
                    = types.type_id

            WHERE type_materials.type_id = ?

            ORDER BY types.name
        """, (type_id,)).fetchall()

    return [dict(row) for row in rows]


def get_type_blueprints(
    type_id: int,
) -> list[dict]:
    with connect() as db:
        rows = db.execute("""
            SELECT
                blueprint_products.blueprint_type_id
                    AS type_id,
                types.name,
                types.meta_group_id,
                blueprint_products.quantity

            FROM blueprint_products

            JOIN types
                ON blueprint_products.blueprint_type_id
                    = types.type_id

            WHERE blueprint_products.product_type_id = ?

            ORDER BY types.name
        """, (type_id,)).fetchall()

    return [dict(row) for row in rows]
