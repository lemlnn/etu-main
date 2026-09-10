import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from etu.sde.database import (
    SDE_DIR,
    _set_sde_build,
    connect,
    create_database,
)


def import_sde(
    sde_dir: Path = SDE_DIR,
    build: int | None = None,
):
    create_database()

    with connect() as db:
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
    Stream a JSON Lines file one record at a time.
    """

    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            yield json.loads(line)

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
            description = (data.get("description") or {}).get("en")

            yield (
                data["_key"],
                data["name"]["en"],
                description,
                data["groupID"],
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
            volume,
            packaged_volume,
            published
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
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
