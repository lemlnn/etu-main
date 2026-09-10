"""low-level universe queries for systems, regions, and static stargate links. fuzzy lookup works directly from the sde names here"""

from rapidfuzz import fuzz, process
from collections import deque

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

# these are static stargate links from the sde; dynamic wormhole connections are not part of this data
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

def get_jump_distances(system_id: int, max_jumps: int = 40) -> dict[int, int]:
    with connect() as db:
        results = db.execute("""
            SELECT
                system_id,
                destination_system_id

            FROM stargates
        """).fetchall()

    graph = {}

    for result in results:
        graph.setdefault(
            result["system_id"],
            [],
        ).append(
            result["destination_system_id"]
        )

    distances = {
        system_id: 0,
    }

    queue = deque([
        system_id,
    ])

    while queue:
        current_system_id = queue.popleft()
        current_distance = distances[current_system_id]

        if current_distance >= max_jumps:
            continue

        for destination_system_id in graph.get(
            current_system_id,
            [],
        ):
            if destination_system_id in distances:
                continue

            distances[destination_system_id] = current_distance + 1
            queue.append(destination_system_id)

    return distances

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

    # fuzzy matching is useful for normal typos; the cli adds extra prefix ranking for j-space searches
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
