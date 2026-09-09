import json
import shutil
import sqlite3
import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path

import requests
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
SDE_DIR = DATA_DIR / "sde"
DB_PATH = DATA_DIR / "etu.db"

LATEST_SDE_URL = (
    "https://developers.eveonline.com/"
    "static-data/tranquility/latest.jsonl"
)

SDE_DOWNLOAD_URL = (
    "https://developers.eveonline.com/"
    "static-data/tranquility/"
    "eve-online-static-data-{build}-jsonl.zip"
)

REQUIRED_SDE_FILES = {
    "categories.jsonl",
    "groups.jsonl",
    "types.jsonl",
    "mapRegions.jsonl",
    "mapConstellations.jsonl",
    "mapSolarSystems.jsonl",
    "mapStargates.jsonl",
}

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

def get_latest_sde_build() -> int:
    response = requests.get(
        LATEST_SDE_URL,
        timeout=15,
    )

    response.raise_for_status()

    for line in response.text.splitlines():
        if not line.strip():
            continue

        record = json.loads(line)

        if record.get("_key") != "sde":
            continue

        if "buildNumber" in record:
            return int(record["buildNumber"])

        if "_value" in record:
            value = record["_value"]

            if isinstance(value, dict):
                return int(value["buildNumber"])

            return int(value)

    raise RuntimeError(
        "Could not find the SDE build number."
    )

def _download_sde(
    build: int,
    destination: Path,
):
    url = SDE_DOWNLOAD_URL.format(build=build)

    response = requests.get(
        url,
        stream=True,
        timeout=(10, 120),
    )

    response.raise_for_status()

    downloaded = 0

    with open(destination, "wb") as file:
        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):
            if not chunk:
                continue

            file.write(chunk)

            downloaded += len(chunk)

            print(
                f"\rDownloaded: "
                f"{downloaded / 1024 / 1024:.1f} MiB",
                end="",
            )

    print()

def update_sde():
    print("Checking for SDE updates...")

    latest_build = get_latest_sde_build()
    installed_build = get_sde_build()

    print(
        f"Installed SDE: "
        f"{installed_build or 'unknown'}"
    )
    print(f"Latest SDE:    {latest_build}")

    if installed_build == latest_build:
        print("SDE is already up to date.")
        return

    with tempfile.TemporaryDirectory(
        prefix="etu-sde-"
    ) as temp:
        temp_dir = Path(temp)

        zip_path = temp_dir / "sde.zip"
        extracted_dir = temp_dir / "sde"

        print()
        print("Downloading SDE...")

        _download_sde(
            latest_build,
            zip_path,
        )

        print("Extracting required files...")

        _extract_required_files(
            zip_path,
            extracted_dir,
        )

        print("Importing SDE...")

        import_sde(
            sde_dir=extracted_dir,
            build=latest_build,
        )

    print(
        f"SDE updated to build "
        f"{latest_build}."
    )

def _extract_required_files(
    zip_path: Path,
    destination: Path,
):
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    found = set()

    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            filename = Path(member.filename).name

            if filename not in REQUIRED_SDE_FILES:
                continue

            target = destination / filename

            with archive.open(member) as source:
                with open(target, "wb") as output:
                    shutil.copyfileobj(source, output)

            found.add(filename)

    missing = REQUIRED_SDE_FILES - found

    if missing:
        missing_text = ", ".join(sorted(missing))

        raise RuntimeError(
            f"SDE archive is missing: {missing_text}"
        )
    
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