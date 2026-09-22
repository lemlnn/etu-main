"""sqlite setup and metadata helpers for etu's local sde copy. the schema stays in one place for the importer to build on"""

import os
import sqlite3

from etu.paths import get_data_dir, get_legacy_data_dir


DATA_DIR = get_data_dir()
SDE_DIR = DATA_DIR / "sde"
DB_PATH = DATA_DIR / "etu.db"

SDE_SCHEMA_VERSION = 3
_LEGACY_MIGRATION_CHECKED = False


def _database_has_sde_data(path) -> bool:
    """Return whether a database contains the core imported SDE datasets."""
    if not path.is_file():
        return False

    try:
        uri = f"{path.resolve().as_uri()}?mode=ro"

        with sqlite3.connect(uri, uri=True) as db:
            types = db.execute(
                "SELECT COUNT(*) FROM types"
            ).fetchone()
            systems = db.execute(
                "SELECT COUNT(*) FROM systems"
            ).fetchone()

        return bool(types[0] > 0 and systems[0] > 0)

    except (OSError, sqlite3.DatabaseError):
        return False


def _migrate_legacy_database() -> bool:
    """Copy a populated pre-0.1.8 source-tree database into user data once."""
    global _LEGACY_MIGRATION_CHECKED

    if _LEGACY_MIGRATION_CHECKED:
        return False

    if _database_has_sde_data(DB_PATH):
        _LEGACY_MIGRATION_CHECKED = True
        return False

    legacy_data = get_legacy_data_dir()

    if legacy_data is None:
        _LEGACY_MIGRATION_CHECKED = True
        return False

    legacy_db = legacy_data / "etu.db"

    if not _database_has_sde_data(legacy_db):
        _LEGACY_MIGRATION_CHECKED = True
        return False

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    migration_path = DATA_DIR / "etu.db.migrating"
    migration_path.unlink(missing_ok=True)

    source_uri = f"{legacy_db.resolve().as_uri()}?mode=ro"

    try:
        with sqlite3.connect(source_uri, uri=True) as source:
            with sqlite3.connect(migration_path) as destination:
                source.backup(destination)

        os.replace(migration_path, DB_PATH)
        _LEGACY_MIGRATION_CHECKED = True

    finally:
        migration_path.unlink(missing_ok=True)

    return True


def connect() -> sqlite3.Connection:
    """
    open etu's local sqlite database
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(DB_PATH)
    # named columns make the query layer much easier to turn into normal dictionaries
    db.row_factory = sqlite3.Row

    db.execute("PRAGMA foreign_keys = ON")

    return db


def _column_exists(
    db: sqlite3.Connection,
    table: str,
    column: str,
) -> bool:
    rows = db.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return any(
        row["name"] == column
        for row in rows
    )


def create_database():
    """
    create etu's static-data tables if they do not already exist
    """

    _migrate_legacy_database()

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
                meta_group_id INTEGER,
                variation_parent_type_id INTEGER,
                volume REAL,
                packaged_volume REAL,
                published INTEGER NOT NULL,

                FOREIGN KEY (group_id)
                    REFERENCES groups(group_id)
            )
        """)

        # older etu databases are upgraded in place, then refreshed from the current sde
        if not _column_exists(
            db,
            "types",
            "meta_group_id",
        ):
            db.execute("""
                ALTER TABLE types
                ADD COLUMN meta_group_id INTEGER
            """)

        if not _column_exists(
            db,
            "types",
            "variation_parent_type_id",
        ):
            db.execute("""
                ALTER TABLE types
                ADD COLUMN variation_parent_type_id INTEGER
            """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_types_name
            ON types(name)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_types_variation_parent
            ON types(variation_parent_type_id)
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS dogma_units (
                unit_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS dogma_attributes (
                attribute_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT,
                icon_id INTEGER,
                unit_id INTEGER,
                published INTEGER NOT NULL,
                display_when_zero INTEGER NOT NULL,
                data_type INTEGER NOT NULL,

                FOREIGN KEY (unit_id)
                    REFERENCES dogma_units(unit_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS dogma_effects (
                effect_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT,
                icon_id INTEGER,
                published INTEGER NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS type_dogma_attributes (
                type_id INTEGER NOT NULL,
                attribute_id INTEGER NOT NULL,
                value REAL NOT NULL,
                sort_index INTEGER NOT NULL,

                PRIMARY KEY (type_id, attribute_id),

                FOREIGN KEY (type_id)
                    REFERENCES types(type_id),

                FOREIGN KEY (attribute_id)
                    REFERENCES dogma_attributes(attribute_id)
            )
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_type_dogma_attributes_type
            ON type_dogma_attributes(type_id)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_type_dogma_attributes_attribute
            ON type_dogma_attributes(attribute_id)
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS type_dogma_effects (
                type_id INTEGER NOT NULL,
                effect_id INTEGER NOT NULL,
                is_default INTEGER NOT NULL,
                sort_index INTEGER NOT NULL,

                PRIMARY KEY (type_id, effect_id),

                FOREIGN KEY (type_id)
                    REFERENCES types(type_id),

                FOREIGN KEY (effect_id)
                    REFERENCES dogma_effects(effect_id)
            )
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_type_dogma_effects_type
            ON type_dogma_effects(type_id)
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS type_materials (
                type_id INTEGER NOT NULL,
                material_type_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,

                PRIMARY KEY (type_id, material_type_id),

                FOREIGN KEY (type_id)
                    REFERENCES types(type_id),

                FOREIGN KEY (material_type_id)
                    REFERENCES types(type_id)
            )
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_type_materials_type
            ON type_materials(type_id)
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS blueprint_products (
                blueprint_type_id INTEGER NOT NULL,
                product_type_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,

                PRIMARY KEY (
                    blueprint_type_id,
                    product_type_id
                ),

                FOREIGN KEY (blueprint_type_id)
                    REFERENCES types(type_id),

                FOREIGN KEY (product_type_id)
                    REFERENCES types(type_id)
            )
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_blueprint_products_product
            ON blueprint_products(product_type_id)
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
            CREATE INDEX IF NOT EXISTS idx_constellations_region
            ON constellations(region_id)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_systems_constellation
            ON systems(constellation_id)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_systems_region
            ON systems(region_id)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_stargates_system
            ON stargates(system_id)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_stargates_destination_system
            ON stargates(destination_system_id)
        """)

        # the installed sde build is stored here so the updater knows whether it actually needs to download anything
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


def get_sde_schema_version() -> int | None:
    create_database()

    with connect() as db:
        result = db.execute("""
            SELECT value
            FROM metadata
            WHERE key = 'sde_schema_version'
        """).fetchone()

    if result is None:
        return None

    return int(result["value"])


def _set_sde_schema_version(
    db: sqlite3.Connection,
):
    db.execute("""
        INSERT INTO metadata (key, value)
        VALUES ('sde_schema_version', ?)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
    """, (str(SDE_SCHEMA_VERSION),))


def needs_sde_refresh() -> bool:
    return (
        get_sde_schema_version()
        != SDE_SCHEMA_VERSION
    )


def is_ready() -> bool:
    """
    return true if the local sde database exists and contains
    inventory types and solar systems
    """

    try:
        create_database()

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
