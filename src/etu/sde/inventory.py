"""low-level inventory queries against etu's sqlite sde. the queries return plain dictionaries so higher layers stay simple"""

from rapidfuzz import fuzz, process

from etu.sde.database import connect


def get_category(category_id: int) -> dict | None:
    with connect() as db:
        result = db.execute("""
            SELECT
                category_id,
                name,
                published
            FROM categories
            WHERE category_id = ?
        """, (category_id,)).fetchone()

    if result is None:
        return None

    return dict(result)

def get_group(group_id: int) -> dict | None:
    with connect() as db:
        result = db.execute("""
            SELECT
                groups.group_id,
                groups.name,
                groups.category_id,
                groups.published,
                categories.name AS category_name

            FROM groups

            JOIN categories
                ON groups.category_id = categories.category_id

            WHERE groups.group_id = ?
        """, (group_id,)).fetchone()

    if result is None:
        return None

    return dict(result)

def get_type(type_id: int) -> dict | None:
    """
    return an inventory type with its group/category already resolved
    """

    with connect() as db:
        result = db.execute("""
            SELECT
                types.type_id,
                types.name,
                types.description,
                types.volume,
                types.packaged_volume,
                types.published,

                groups.group_id,
                groups.name AS group_name,

                categories.category_id,
                categories.name AS category_name

            FROM types

            JOIN groups
                ON types.group_id = groups.group_id

            JOIN categories
                ON groups.category_id = categories.category_id

            WHERE types.type_id = ?
        """, (type_id,)).fetchone()

    if result is None:
        return None

    return dict(result)

def find_types(name: str, limit: int = 25) -> list[dict]:
    """
    search inventory types by name

    exact matches are sorted first, followed by partial matches
    """

    search = f"%{name}%"

    with connect() as db:
        results = db.execute("""
            SELECT
                types.type_id,
                types.name,

                groups.group_id,
                groups.name AS group_name,

                categories.category_id,
                categories.name AS category_name

            FROM types

            JOIN groups
                ON types.group_id = groups.group_id

            JOIN categories
                ON groups.category_id = categories.category_id

            WHERE types.name LIKE ? COLLATE NOCASE

            ORDER BY
                CASE
                    WHEN lower(types.name) = lower(?) THEN 0
                    ELSE 1
                END,
                types.name

            LIMIT ?
        """, (
            search,
            name,
            limit,
        )).fetchall()

    return [dict(result) for result in results]

def find_types_fuzzy(
    name: str,
    limit: int = 10,
    cutoff: float = 60,
) -> list[dict]:
    with connect() as db:
        results = db.execute("""
            SELECT
                types.type_id,
                types.name,

                groups.group_id,
                groups.name AS group_name,

                categories.category_id,
                categories.name AS category_name

            FROM types

            JOIN groups
                ON types.group_id = groups.group_id

            JOIN categories
                ON groups.category_id = categories.category_id
        """).fetchall()

    rows = [dict(result) for result in results]

    choices = {
        row["type_id"]: row["name"]
        for row in rows
    }

    # rapidfuzz adds typo tolerance without changing the exact/partial sql search path
    matches = process.extract(
        name,
        choices,
        scorer=fuzz.ratio,
        processor=str.casefold,
        limit=limit,
        score_cutoff=cutoff,
    )

    rows_by_id = {
        row["type_id"]: row
        for row in rows
    }

    return [
        rows_by_id[type_id]
        for _, _, type_id in matches
    ]
