"""low-level universe queries for systems, regions, and static stargate links"""

from collections import deque
from functools import cache, lru_cache
import heapq

from etu.sde.database import connect
from etu.sde.search import KeywordTrieIndex, TrieIndexCache


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

def _build_system_search_index() -> KeywordTrieIndex:
    with connect() as db:
        rows = db.execute("""
            SELECT
                system_id,
                name,
                security_status
            FROM systems
        """).fetchall()

    return KeywordTrieIndex(rows)


_SYSTEM_SEARCH_INDEX = TrieIndexCache(
    _build_system_search_index
)


def find_systems_keywords(
    query: str,
    limit: int | None = 25,
) -> list[dict]:
    return _SYSTEM_SEARCH_INDEX.get().search(
        query,
        limit=limit,
    )


def find_systems(
    name: str,
    limit: int = 25,
) -> list[dict]:
    """Compatibility wrapper using keyword search semantics."""
    return find_systems_keywords(
        name,
        limit=limit,
    )

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

@cache
def _get_stargate_graph() -> dict[int, list[int]]:
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

    return graph

@cache
def _get_system_security() -> dict[int, float]:
    with connect() as db:
        results = db.execute("""
            SELECT
                system_id,
                security_status

            FROM systems
        """).fetchall()

    return {
        result["system_id"]: result["security_status"]
        for result in results
    }

def clear_universe_cache():
    clear_universe_search_cache()
    _get_stargate_graph.cache_clear()
    _get_system_security.cache_clear()
    _get_jump_distances.cache_clear()

def _get_route_details(route_ids: list[int]) -> list[dict]:
    placeholders = ", ".join(
        "?"
        for _ in route_ids
    )

    with connect() as db:
        results = db.execute(f"""
            SELECT
                systems.system_id,
                systems.name,
                systems.security_status,
                regions.region_id,
                regions.name AS region_name

            FROM systems

            JOIN regions
                ON systems.region_id = regions.region_id

            WHERE systems.system_id IN ({placeholders})
        """, route_ids).fetchall()

    systems = {
        result["system_id"]: dict(result)
        for result in results
    }

    return [
        systems[system_id]
        for system_id in route_ids
    ]

@lru_cache(maxsize=8)
def _get_jump_distances(
    system_id: int,
    max_jumps: int,
) -> dict[int, int]:
    graph = _get_stargate_graph()

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


def get_jump_distances(
    system_id: int,
    max_jumps: int = 40,
) -> dict[int, int]:
    # Return a copy so callers keep the previous mutable-dict contract
    # without being able to mutate a cached result shared by later calls.
    return _get_jump_distances(
        system_id,
        max_jumps,
    ).copy()

def get_route(
    origin_system_id: int,
    destination_system_id: int,
    mode: str = "shortest",
    avoided_system_ids: set[int] | None = None,
) -> list[dict] | None:
    if mode not in {
        "shortest",
        "safer",
        "less_secure",
        "highsec",
    }:
        raise ValueError(f'Unknown route mode "{mode}".')

    graph = _get_stargate_graph()
    security = _get_system_security()

    if (
        origin_system_id not in security
        or destination_system_id not in security
    ):
        return None

    # strict highsec routing refuses endpoints outside highsec too
    if mode == "highsec" and (
        security[origin_system_id] < 0.45
        or security[destination_system_id] < 0.45
    ):
        return None

    avoided = set(avoided_system_ids or set())
    avoided.discard(origin_system_id)
    avoided.discard(destination_system_id)

    # the first cost value is the route preference penalty, the second is normal jump count
    costs = {
        origin_system_id: (0, 0),
    }

    previous = {
        origin_system_id: None,
    }

    queue = [
        ((0, 0), origin_system_id),
    ]

    while queue:
        current_cost, current_system_id = heapq.heappop(queue)

        if current_cost != costs[current_system_id]:
            continue

        if current_system_id == destination_system_id:
            break

        for next_system_id in graph.get(
            current_system_id,
            [],
        ):
            if next_system_id in avoided:
                continue

            next_security = security.get(next_system_id)

            if next_security is None:
                continue

            if mode == "highsec" and next_security < 0.45:
                continue

            penalty = 0

            if mode == "safer" and next_security < 0.45:
                penalty = 1

            elif mode == "less_secure" and next_security >= 0.45:
                penalty = 1

            next_cost = (
                current_cost[0] + penalty,
                current_cost[1] + 1,
            )

            if (
                next_system_id not in costs
                or next_cost < costs[next_system_id]
            ):
                costs[next_system_id] = next_cost
                previous[next_system_id] = current_system_id

                heapq.heappush(
                    queue,
                    (
                        next_cost,
                        next_system_id,
                    ),
                )

    if destination_system_id not in previous:
        return None

    route_ids = []
    current_system_id = destination_system_id

    while current_system_id is not None:
        route_ids.append(current_system_id)
        current_system_id = previous[current_system_id]

    route_ids.reverse()

    return _get_route_details(route_ids)

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

def _build_region_search_index() -> KeywordTrieIndex:
    with connect() as db:
        rows = db.execute("""
            SELECT
                region_id,
                name
            FROM regions
        """).fetchall()

    return KeywordTrieIndex(rows)


_REGION_SEARCH_INDEX = TrieIndexCache(
    _build_region_search_index
)


def find_regions_keywords(
    query: str,
    limit: int | None = 25,
) -> list[dict]:
    return _REGION_SEARCH_INDEX.get().search(
        query,
        limit=limit,
    )


def warm_universe_search_indexes():
    _SYSTEM_SEARCH_INDEX.get()
    _REGION_SEARCH_INDEX.get()


def clear_universe_search_cache():
    _SYSTEM_SEARCH_INDEX.clear()
    _REGION_SEARCH_INDEX.clear()


def find_regions(
    name: str,
    limit: int = 25,
) -> list[dict]:
    """Compatibility wrapper using keyword search semantics."""
    return find_regions_keywords(
        name,
        limit=limit,
    )
