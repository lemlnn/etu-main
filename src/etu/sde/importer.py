"""sde jsonl importer. it streams the files and loads tables in dependency order so the large dataset stays manageable"""

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from etu.sde.database import (
    SDE_DIR,
    _set_sde_build,
    _set_sde_schema_version,
    connect,
    create_database,
)


def import_sde(
    sde_dir: Path = SDE_DIR,
    build: int | None = None,
):
    create_database()

    with connect() as db:
        # ccp's sde is not guaranteed to be relationally closed; some exported
        # records can reference ids that are absent from another exported file
        # keep the declared relationships for normal etu access, but do not let
        # sqlite reject otherwise valid source rows while mirroring the sde
        db.execute("PRAGMA foreign_keys = OFF")

        # child tables are still cleared first so the dependency order stays explicit
        db.execute("DELETE FROM type_dogma_attributes")
        db.execute("DELETE FROM type_dogma_effects")
        db.execute("DELETE FROM type_materials")
        db.execute("DELETE FROM blueprint_products")
        db.execute("DELETE FROM dogma_attributes")
        db.execute("DELETE FROM dogma_effects")
        db.execute("DELETE FROM dogma_units")

        db.execute("DELETE FROM stargates")
        db.execute("DELETE FROM systems")
        db.execute("DELETE FROM constellations")
        db.execute("DELETE FROM regions")

        db.execute("DELETE FROM types")
        db.execute("DELETE FROM groups")
        db.execute("DELETE FROM categories")

        print("Importing categories...")
        _import_categories(db, sde_dir)

        print("Importing groups...")
        _import_groups(db, sde_dir)

        print("Importing types...")
        _import_types(db, sde_dir)

        print("Importing dogma units...")
        _import_dogma_units(db, sde_dir)

        print("Importing dogma attributes...")
        _import_dogma_attributes(db, sde_dir)

        print("Importing dogma effects...")
        _import_dogma_effects(db, sde_dir)

        print("Importing type dogma...")
        _import_type_dogma(db, sde_dir)

        print("Importing type materials...")
        _import_type_materials(db, sde_dir)

        print("Importing blueprint products...")
        _import_blueprint_products(db, sde_dir)

        print("Importing regions...")
        _import_regions(db, sde_dir)

        print("Importing constellations...")
        _import_constellations(db, sde_dir)

        print("Importing systems...")
        _import_systems(db, sde_dir)

        print("Importing stargates...")
        _import_stargates(db, sde_dir)

        if build is not None:
            _set_sde_build(db, build)

        _set_sde_schema_version(db)

    # SDE-backed indexes, route graphs, and composed Universe details are
    # immutable only until this replacement completes.  Clear them after the
    # transaction commits so the next read sees the new dataset.
    from etu.sde.inventory import clear_inventory_search_cache
    from etu.sde.universe import clear_universe_cache
    from etu.universe import clear_universe_detail_cache

    clear_inventory_search_cache()
    clear_universe_cache()
    clear_universe_detail_cache()

    print("SDE import complete.")


def _require_sde_file(
    filename: str,
    sde_dir: Path = SDE_DIR,
) -> Path:
    path = sde_dir / filename

    if not path.exists():
        raise FileNotFoundError(
            f'Could not find "{filename}" in:\n'
            f"{sde_dir}"
        )

    return path


def _read_jsonl(path: Path) -> Iterator[dict]:
    """
    stream a json lines file one record at a time
    """

    # large sde files are streamed rather than loaded into memory all at once
    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            yield json.loads(line)


def _english(value):
    if not isinstance(value, dict):
        return None

    return value.get("en")


def _import_categories(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "categories.jsonl",
        sde_dir,
    )

    rows = (
        (
            data["_key"],
            data["name"]["en"],
            int(data.get("published", False)),
        )
        for data in _read_jsonl(path)
    )

    db.executemany("""
        INSERT INTO categories (
            category_id,
            name,
            published
        )
        VALUES (?, ?, ?)
    """, rows)


def _import_groups(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "groups.jsonl",
        sde_dir,
    )

    rows = (
        (
            data["_key"],
            data["name"]["en"],
            data["categoryID"],
            int(data.get("published", False)),
        )
        for data in _read_jsonl(path)
    )

    db.executemany("""
        INSERT INTO groups (
            group_id,
            name,
            category_id,
            published
        )
        VALUES (?, ?, ?, ?)
    """, rows)


def _import_types(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "types.jsonl",
        sde_dir,
    )

    def rows():
        for data in _read_jsonl(path):
            description = _english(
                data.get("description")
            )

            yield (
                data["_key"],
                data["name"]["en"],
                description,
                data["groupID"],
                data.get("metaGroupID"),
                data.get("variationParentTypeID"),
                data.get("volume"),
                data.get("packagedVolume"),
                int(data.get("published", False)),
            )

    db.executemany("""
        INSERT INTO types (
            type_id,
            name,
            description,
            group_id,
            meta_group_id,
            variation_parent_type_id,
            volume,
            packaged_volume,
            published
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows())


def _import_dogma_units(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "dogmaUnits.jsonl",
        sde_dir,
    )

    rows = (
        (
            data["_key"],
            data["name"],
            _english(data.get("displayName")),
        )
        for data in _read_jsonl(path)
    )

    db.executemany("""
        INSERT INTO dogma_units (
            unit_id,
            name,
            display_name
        )
        VALUES (?, ?, ?)
    """, rows)


def _import_dogma_attributes(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "dogmaAttributes.jsonl",
        sde_dir,
    )

    rows = (
        (
            data["_key"],
            data["name"],
            _english(data.get("displayName")),
            data.get("iconID"),
            data.get("unitID"),
            int(data.get("published", False)),
            int(data.get("displayWhenZero", False)),
            data["dataType"],
        )
        for data in _read_jsonl(path)
    )

    db.executemany("""
        INSERT INTO dogma_attributes (
            attribute_id,
            name,
            display_name,
            icon_id,
            unit_id,
            published,
            display_when_zero,
            data_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)


def _import_dogma_effects(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "dogmaEffects.jsonl",
        sde_dir,
    )

    rows = (
        (
            data["_key"],
            data["name"],
            _english(data.get("displayName")),
            data.get("iconID"),
            int(data.get("published", False)),
        )
        for data in _read_jsonl(path)
    )

    db.executemany("""
        INSERT INTO dogma_effects (
            effect_id,
            name,
            display_name,
            icon_id,
            published
        )
        VALUES (?, ?, ?, ?, ?)
    """, rows)


def _import_type_dogma(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "typeDogma.jsonl",
        sde_dir,
    )

    def attribute_rows():
        for data in _read_jsonl(path):
            type_id = data["_key"]

            for index, attribute in enumerate(
                data.get("dogmaAttributes", ())
            ):
                yield (
                    type_id,
                    attribute["attributeID"],
                    attribute["value"],
                    index,
                )

    db.executemany("""
        INSERT INTO type_dogma_attributes (
            type_id,
            attribute_id,
            value,
            sort_index
        )
        VALUES (?, ?, ?, ?)
    """, attribute_rows())

    def effect_rows():
        for data in _read_jsonl(path):
            type_id = data["_key"]

            for index, effect in enumerate(
                data.get("dogmaEffects", ())
            ):
                yield (
                    type_id,
                    effect["effectID"],
                    int(effect.get("isDefault", False)),
                    index,
                )

    db.executemany("""
        INSERT INTO type_dogma_effects (
            type_id,
            effect_id,
            is_default,
            sort_index
        )
        VALUES (?, ?, ?, ?)
    """, effect_rows())


def _import_type_materials(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "typeMaterials.jsonl",
        sde_dir,
    )

    def rows():
        for data in _read_jsonl(path):
            type_id = data["_key"]

            for material in data.get(
                "materials",
                (),
            ):
                yield (
                    type_id,
                    material["materialTypeID"],
                    material["quantity"],
                )

    db.executemany("""
        INSERT INTO type_materials (
            type_id,
            material_type_id,
            quantity
        )
        VALUES (?, ?, ?)
    """, rows())


def _import_blueprint_products(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "blueprints.jsonl",
        sde_dir,
    )

    def rows():
        for data in _read_jsonl(path):
            blueprint_type_id = data.get(
                "blueprintTypeID",
                data["_key"],
            )
            manufacturing = (
                data.get("activities", {})
                .get("manufacturing")
            )

            if not manufacturing:
                continue

            for product in manufacturing.get(
                "products",
                (),
            ):
                yield (
                    blueprint_type_id,
                    product["typeID"],
                    product.get("quantity", 1),
                )

    db.executemany("""
        INSERT INTO blueprint_products (
            blueprint_type_id,
            product_type_id,
            quantity
        )
        VALUES (?, ?, ?)
    """, rows())


def _import_regions(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "mapRegions.jsonl",
        sde_dir,
    )

    rows = (
        (
            data["_key"],
            data["name"]["en"],
            data.get("factionID"),
            data.get("wormholeClassID"),
        )
        for data in _read_jsonl(path)
    )

    db.executemany("""
        INSERT INTO regions (
            region_id,
            name,
            faction_id,
            wormhole_class_id
        )
        VALUES (?, ?, ?, ?)
    """, rows)


def _import_constellations(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "mapConstellations.jsonl",
        sde_dir,
    )

    rows = (
        (
            data["_key"],
            data["name"]["en"],
            data["regionID"],
            data.get("factionID"),
            data.get("wormholeClassID"),
        )
        for data in _read_jsonl(path)
    )

    db.executemany("""
        INSERT INTO constellations (
            constellation_id,
            name,
            region_id,
            faction_id,
            wormhole_class_id
        )
        VALUES (?, ?, ?, ?, ?)
    """, rows)


def _import_systems(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "mapSolarSystems.jsonl",
        sde_dir,
    )

    rows = (
        (
            data["_key"],
            data["name"]["en"],
            data["constellationID"],
            data["regionID"],
            data["securityStatus"],
            data.get("securityClass"),
            data.get("factionID"),
            data.get("wormholeClassID"),
        )
        for data in _read_jsonl(path)
    )

    db.executemany("""
        INSERT INTO systems (
            system_id,
            name,
            constellation_id,
            region_id,
            security_status,
            security_class,
            faction_id,
            wormhole_class_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)


def _import_stargates(
    db: sqlite3.Connection,
    sde_dir: Path = SDE_DIR,
):
    path = _require_sde_file(
        "mapStargates.jsonl",
        sde_dir,
    )

    rows = (
        (
            data["_key"],
            data["solarSystemID"],
            data["destination"]["solarSystemID"],
            data["destination"]["stargateID"],
        )
        for data in _read_jsonl(path)
    )

    db.executemany("""
        INSERT INTO stargates (
            stargate_id,
            system_id,
            destination_system_id,
            destination_stargate_id
        )
        VALUES (?, ?, ?, ?)
    """, rows)
