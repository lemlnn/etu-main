from rapidfuzz import fuzz, process

from etu.sde.database import connect


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

def find_systems_fuzzy(
    name: str,
    limit: int = 10,
    cutoff: float = 60,
) -> list[dict]:
    with connect() as db:
        results = db.execute("""
            SELECT
                system_id,
                name,
                security_status

            FROM systems
        """).fetchall()

    rows = [dict(result) for result in results]

    choices = {
        row["system_id"]: row["name"]
        for row in rows
    }

    matches = process.extract(
        name,
        choices,
        scorer=fuzz.ratio,
        processor=str.casefold,
        limit=limit,
        score_cutoff=cutoff,
    )

    rows_by_id = {
        row["system_id"]: row
        for row in rows
    }

    return [
        rows_by_id[system_id]
        for _, _, system_id in matches
    ]

def get_region(region_id: int) -> dict | None:
    with connect() as db:
        result = db.execute("""
            SELECT
                region_id,
                name,
                faction_id,
                wormhole_class_id

            FROM regions

            WHERE region_id = ?
        """, (region_id,)).fetchone()

    if result is None:
        return None

    return dict(result)

def find_regions(name: str, limit: int = 25) -> list[dict]:
    search = f"%{name}%"

    with connect() as db:
        results = db.execute("""
            SELECT
                region_id,
                name

            FROM regions

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

def find_regions_fuzzy(
    name: str,
    limit: int = 10,
    cutoff: float = 60,
) -> list[dict]:
    with connect() as db:
        results = db.execute("""
            SELECT
                region_id,
                name

            FROM regions
        """).fetchall()

    rows = [dict(result) for result in results]

    choices = {
        row["region_id"]: row["name"]
        for row in rows
    }

    matches = process.extract(
        name,
        choices,
        scorer=fuzz.ratio,
        processor=str.casefold,
        limit=limit,
        score_cutoff=cutoff,
    )

    rows_by_id = {
        row["region_id"]: row
        for row in rows
    }

    return [
        rows_by_id[region_id]
        for _, _, region_id in matches
    ]
