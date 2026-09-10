import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

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

        db.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
            )
        """)

def get_sde_build() -> int | None:
    create_database()

    with connect() as db:
        result = db.execute("""
            SELECT value
            FROM metadata
            WHERE key = 'sde_build'
        """).fetchone()

    if result is None:
        return None

    return int(result["value"])

def _set_sde_build(
    db: sqlite3.Connection,
    build: int,
):
    db.execute("""
        INSERT INTO metadata (key, value)
        VALUES ('sde_build', ?)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
    """, (str(build),))

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
