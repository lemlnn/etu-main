import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
SDE_DIR = DATA_DIR / "sde"
DB_PATH = DATA_DIR / "etu.db"

def connect() -> sqlite3.Connection:
    """
    Open ETU's local SQLite database.
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    db.execute("PRAGMA foreign_keys = ON")

    return db

def create_database():
    """
    Create ETU's static-data tables if they do not already exist.
    """

    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                published INTEGER NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                published INTEGER NOT NULL,

                FOREIGN KEY (category_id)
                    REFERENCES categories(category_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS types (
                type_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                group_id INTEGER NOT NULL,
                volume REAL,
                packaged_volume REAL,
                published INTEGER NOT NULL,

                FOREIGN KEY (group_id)
                    REFERENCES groups(group_id)
            )
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_types_name
            ON types(name)
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS regions (
                region_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                faction_id INTEGER,
                wormhole_class_id INTEGER
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS constellations (
                constellation_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                region_id INTEGER NOT NULL,
                faction_id INTEGER,
                wormhole_class_id INTEGER,

                FOREIGN KEY (region_id)
                    REFERENCES regions(region_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS systems (
                system_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                constellation_id INTEGER NOT NULL,
                region_id INTEGER NOT NULL,
                security_status REAL NOT NULL,
                security_class TEXT,
                faction_id INTEGER,
                wormhole_class_id INTEGER,

                FOREIGN KEY (constellation_id)
                    REFERENCES constellations(constellation_id),

                FOREIGN KEY (region_id)
                    REFERENCES regions(region_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS stargates (
                stargate_id INTEGER PRIMARY KEY,
                system_id INTEGER NOT NULL,
                destination_system_id INTEGER NOT NULL,
                destination_stargate_id INTEGER NOT NULL,

                FOREIGN KEY (system_id)
                    REFERENCES systems(system_id),

                FOREIGN KEY (destination_system_id)
                    REFERENCES systems(system_id)
            )
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_systems_name
            ON systems(name)
        """)

def _require_sde_file(filename: str) -> Path:
    """
    Return the path to an SDE file or fail with a useful message.
    """

    path = SDE_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f'Could not find "{filename}" in:\n'
            f"{SDE_DIR}\n\n"
            "Make sure the JSONL SDE files have been extracted there."
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

def _import_categories(db: sqlite3.Connection):
    path = _require_sde_file("categories.jsonl")

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

def _import_groups(db: sqlite3.Connection):
    path = _require_sde_file("groups.jsonl")

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

def _import_types(db: sqlite3.Connection):
    path = _require_sde_file("types.jsonl")

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

def import_sde():
    """
    Rebuild ETU's local static-data tables from the SDE.
    """

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
        _import_categories(db)

        print("Importing groups...")
        _import_groups(db)

        print("Importing types...")
        _import_types(db)

        print("Importing regions...")
        _import_regions(db)

        print("Importing constellations...")
        _import_constellations(db)

        print("Importing systems...")
        _import_systems(db)

        print("Importing stargates...")
        _import_stargates(db)

    print("SDE import complete.")

def _import_regions(db: sqlite3.Connection):
    path = _require_sde_file("mapRegions.jsonl")

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

def _import_constellations(db: sqlite3.Connection):
    path = _require_sde_file("mapConstellations.jsonl")

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

def _import_systems(db: sqlite3.Connection):
    path = _require_sde_file("mapSolarSystems.jsonl")

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

def _import_stargates(db: sqlite3.Connection):
    path = _require_sde_file("mapStargates.jsonl")

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

def is_ready() -> bool:
    """
    Return True if the local SDE database exists and contains
    inventory types and solar systems.
    """

    if not DB_PATH.exists():
        return False

    try:
        with connect() as db:
            types = db.execute(
                "SELECT COUNT(*) FROM types"
            ).fetchone()

            systems = db.execute(
                "SELECT COUNT(*) FROM systems"
            ).fetchone()

            return types[0] > 0 and systems[0] > 0

    except sqlite3.OperationalError:
        return False

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
    Return an inventory type with its group/category already resolved.
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
    Search inventory types by name.

    Exact matches are sorted first, followed by partial matches.
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

def get_system(system_id: int) -> dict | None:
    with connect() as db:
        result = db.execute("""
            SELECT
                systems.system_id,
                systems.name,
                systems.security_status,
                systems.security_class,
                systems.faction_id,
                systems.wormhole_class_id,

                constellations.constellation_id,
                constellations.name AS constellation_name,

                regions.region_id,
                regions.name AS region_name

            FROM systems

            JOIN constellations
                ON systems.constellation_id = constellations.constellation_id

            JOIN regions
                ON systems.region_id = regions.region_id

            WHERE systems.system_id = ?
        """, (system_id,)).fetchone()

    if result is None:
        return None

    return dict(result)

def find_systems(name: str, limit: int = 25) -> list[dict]:
    search = f"%{name}%"

    with connect() as db:
        results = db.execute("""
            SELECT
                system_id,
                name,
                security_status

            FROM systems

            WHERE name LIKE ? COLLATE NOCASE

            ORDER BY
                CASE
                    WHEN lower(name) = lower(?) THEN 0
                    ELSE 1
                END,
                name

            LIMIT ?
        """, (
            search,
            name,
            limit,
        )).fetchall()

    return [dict(result) for result in results]

def get_system_connections(system_id: int) -> list[dict]:
    with connect() as db:
        results = db.execute("""
            SELECT
                systems.system_id,
                systems.name,
                systems.security_status

            FROM stargates

            JOIN systems
                ON stargates.destination_system_id = systems.system_id

            WHERE stargates.system_id = ?

            ORDER BY systems.name
        """, (system_id,)).fetchall()

    return [dict(result) for result in results]