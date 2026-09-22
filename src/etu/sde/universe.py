"""Low-level universe queries for hierarchy, search, and static stargate links."""

from collections import deque
from functools import cache, lru_cache
import heapq

from etu.sde.database import connect
from etu.sde.search import KeywordTrieIndex, TrieIndexCache


WORMHOLE_SYSTEM_MIN = 31_000_000
WORMHOLE_SYSTEM_MAX = 31_999_999

SPACE_FILTER_KEYS = {
    "highsec": "has_highsec",
    "lowsec": "has_lowsec",
    "nullsec": "has_nullsec",
    "wormhole": "has_wormhole",
}


def _space_kind(system_id: int, security_status: float) -> str:
    if WORMHOLE_SYSTEM_MIN <= int(system_id) <= WORMHOLE_SYSTEM_MAX:
        return "wormhole"

    security_status = float(security_status)

    if security_status >= 0.45:
        return "highsec"

    if security_status > 0.0:
        return "lowsec"

    return "nullsec"


def _space_flags(system_id: int, security_status: float) -> dict[str, int]:
    kind = _space_kind(system_id, security_status)
    return {
        "has_highsec": int(kind == "highsec"),
        "has_lowsec": int(kind == "lowsec"),
        "has_nullsec": int(kind == "nullsec"),
        "has_wormhole": int(kind == "wormhole"),
    }


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

    output = dict(result)
    output["space_kind"] = _space_kind(
        output["system_id"],
        output["security_status"],
    )
    return output


def get_constellation(constellation_id: int) -> dict | None:
    with connect() as db:
        result = db.execute("""
            SELECT
                constellations.constellation_id,
                constellations.name,
                constellations.faction_id,
                constellations.wormhole_class_id,
                regions.region_id,
                regions.name AS region_name,
                COUNT(systems.system_id) AS system_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 0
                    WHEN systems.security_status >= 0.45 THEN 1
                    ELSE 0
                END) AS highsec_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 0
                    WHEN systems.security_status > 0.0
                         AND systems.security_status < 0.45 THEN 1
                    ELSE 0
                END) AS lowsec_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 0
                    WHEN systems.security_status <= 0.0 THEN 1
                    ELSE 0
                END) AS nullsec_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 1
                    ELSE 0
                END) AS wormhole_count

            FROM constellations

            JOIN regions
                ON constellations.region_id = regions.region_id

            LEFT JOIN systems
                ON systems.constellation_id = constellations.constellation_id

            WHERE constellations.constellation_id = ?

            GROUP BY constellations.constellation_id
        """, (
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            constellation_id,
        )).fetchone()

    return dict(result) if result is not None else None


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

    return dict(result) if result is not None else None


def get_region_summary(region_id: int) -> dict | None:
    with connect() as db:
        result = db.execute("""
            SELECT
                regions.region_id,
                regions.name,
                regions.faction_id,
                regions.wormhole_class_id,
                (
                    SELECT COUNT(*)
                    FROM constellations
                    WHERE constellations.region_id = regions.region_id
                ) AS constellation_count,
                COUNT(systems.system_id) AS system_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 0
                    WHEN systems.security_status >= 0.45 THEN 1
                    ELSE 0
                END) AS highsec_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 0
                    WHEN systems.security_status > 0.0
                         AND systems.security_status < 0.45 THEN 1
                    ELSE 0
                END) AS lowsec_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 0
                    WHEN systems.security_status <= 0.0 THEN 1
                    ELSE 0
                END) AS nullsec_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 1
                    ELSE 0
                END) AS wormhole_count

            FROM regions

            LEFT JOIN systems
                ON systems.region_id = regions.region_id

            WHERE regions.region_id = ?

            GROUP BY regions.region_id
        """, (
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            region_id,
        )).fetchone()

    return dict(result) if result is not None else None

def get_system_connections(system_id: int) -> list[dict]:
    with connect() as db:
        results = db.execute("""
            SELECT DISTINCT
                systems.system_id,
                systems.name,
                systems.security_status,
                systems.constellation_id,
                constellations.name AS constellation_name,
                systems.region_id,
                regions.name AS region_name

            FROM stargates

            JOIN systems
                ON stargates.destination_system_id = systems.system_id

            JOIN constellations
                ON systems.constellation_id = constellations.constellation_id

            JOIN regions
                ON systems.region_id = regions.region_id

            WHERE stargates.system_id = ?

            ORDER BY systems.name
        """, (system_id,)).fetchall()

    output = []

    for result in results:
        row = dict(result)
        row["space_kind"] = _space_kind(
            row["system_id"],
            row["security_status"],
        )
        output.append(row)

    return output


def get_constellation_systems(constellation_id: int) -> list[dict]:
    with connect() as db:
        results = db.execute("""
            SELECT
                systems.system_id,
                systems.name,
                systems.security_status,
                systems.security_class,
                systems.constellation_id,
                constellations.name AS constellation_name,
                systems.region_id,
                regions.name AS region_name

            FROM systems

            JOIN constellations
                ON systems.constellation_id = constellations.constellation_id

            JOIN regions
                ON systems.region_id = regions.region_id

            WHERE systems.constellation_id = ?

            ORDER BY systems.name
        """, (constellation_id,)).fetchall()

    output = []

    for result in results:
        row = dict(result)
        row["space_kind"] = _space_kind(
            row["system_id"],
            row["security_status"],
        )
        output.append(row)

    return output


def get_region_systems(region_id: int) -> list[dict]:
    with connect() as db:
        results = db.execute("""
            SELECT
                systems.system_id,
                systems.name,
                systems.security_status,
                systems.security_class,
                systems.constellation_id,
                constellations.name AS constellation_name,
                systems.region_id,
                regions.name AS region_name

            FROM systems

            JOIN constellations
                ON systems.constellation_id = constellations.constellation_id

            JOIN regions
                ON systems.region_id = regions.region_id

            WHERE systems.region_id = ?

            ORDER BY systems.name
        """, (region_id,)).fetchall()

    output = []

    for result in results:
        row = dict(result)
        row["space_kind"] = _space_kind(
            row["system_id"],
            row["security_status"],
        )
        output.append(row)

    return output


def get_region_constellations(region_id: int) -> list[dict]:
    with connect() as db:
        results = db.execute("""
            SELECT
                constellations.constellation_id,
                constellations.name,
                constellations.region_id,
                regions.name AS region_name,
                COUNT(systems.system_id) AS system_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 0
                    WHEN systems.security_status >= 0.45 THEN 1
                    ELSE 0
                END) AS highsec_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 0
                    WHEN systems.security_status > 0.0
                         AND systems.security_status < 0.45 THEN 1
                    ELSE 0
                END) AS lowsec_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 0
                    WHEN systems.security_status <= 0.0 THEN 1
                    ELSE 0
                END) AS nullsec_count,
                SUM(CASE
                    WHEN systems.system_id BETWEEN ? AND ? THEN 1
                    ELSE 0
                END) AS wormhole_count

            FROM constellations

            JOIN regions
                ON constellations.region_id = regions.region_id

            LEFT JOIN systems
                ON systems.constellation_id = constellations.constellation_id

            WHERE constellations.region_id = ?

            GROUP BY constellations.constellation_id
            ORDER BY constellations.name
        """, (
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            WORMHOLE_SYSTEM_MIN,
            WORMHOLE_SYSTEM_MAX,
            region_id,
        )).fetchall()

    return [dict(result) for result in results]


def _get_borders(
    column: str,
    object_id: int,
) -> list[dict]:
    if column not in {"constellation_id", "region_id"}:
        raise ValueError("Unsupported universe border column")

    with connect() as db:
        results = db.execute(f"""
            SELECT DISTINCT
                source.system_id AS source_system_id,
                source.name AS source_system_name,
                destination.system_id AS destination_system_id,
                destination.name AS destination_system_name,
                destination.constellation_id AS destination_constellation_id,
                destination_constellation.name AS destination_constellation_name,
                destination.region_id AS destination_region_id,
                destination_region.name AS destination_region_name

            FROM stargates

            JOIN systems AS source
                ON stargates.system_id = source.system_id

            JOIN systems AS destination
                ON stargates.destination_system_id = destination.system_id

            JOIN constellations AS destination_constellation
                ON destination.constellation_id =
                   destination_constellation.constellation_id

            JOIN regions AS destination_region
                ON destination.region_id = destination_region.region_id

            WHERE source.{column} = ?
              AND destination.{column} != ?

            ORDER BY
                source.name,
                destination_region.name,
                destination.name
        """, (object_id, object_id)).fetchall()

    return [dict(result) for result in results]


def get_constellation_borders(constellation_id: int) -> list[dict]:
    return _get_borders(
        "constellation_id",
        constellation_id,
    )


def get_region_borders(region_id: int) -> list[dict]:
    return _get_borders(
        "region_id",
        region_id,
    )


def _build_universe_search_index() -> KeywordTrieIndex:
    with connect() as db:
        system_rows = db.execute("""
            SELECT
                systems.system_id,
                systems.name,
                systems.security_status,
                systems.constellation_id,
                constellations.name AS constellation_name,
                systems.region_id,
                regions.name AS region_name

            FROM systems

            JOIN constellations
                ON systems.constellation_id = constellations.constellation_id

            JOIN regions
                ON systems.region_id = regions.region_id
        """).fetchall()

        constellation_rows = db.execute("""
            SELECT
                constellations.constellation_id,
                constellations.name,
                constellations.region_id,
                regions.name AS region_name

            FROM constellations

            JOIN regions
                ON constellations.region_id = regions.region_id
        """).fetchall()

        region_rows = db.execute("""
            SELECT
                region_id,
                name
            FROM regions
        """).fetchall()

    constellation_stats: dict[int, dict[str, int]] = {}
    region_stats: dict[int, dict[str, int]] = {}
    rows = []

    def stats_for(mapping, key):
        return mapping.setdefault(
            int(key),
            {
                "system_count": 0,
                "highsec_count": 0,
                "lowsec_count": 0,
                "nullsec_count": 0,
                "wormhole_count": 0,
            },
        )

    for result in system_rows:
        row = dict(result)
        kind = _space_kind(
            row["system_id"],
            row["security_status"],
        )
        flags = _space_flags(
            row["system_id"],
            row["security_status"],
        )
        rows.append({
            **row,
            **flags,
            "kind": "system",
            "object_id": row["system_id"],
            "space_kind": kind,
        })

        for mapping, key in (
            (constellation_stats, row["constellation_id"]),
            (region_stats, row["region_id"]),
        ):
            stats = stats_for(mapping, key)
            stats["system_count"] += 1
            stats[f"{kind}_count"] += 1

    for result in constellation_rows:
        row = dict(result)
        stats = stats_for(
            constellation_stats,
            row["constellation_id"],
        )
        rows.append({
            **row,
            **stats,
            "system_id": None,
            "security_status": None,
            "constellation_name": row["name"],
            "kind": "constellation",
            "object_id": row["constellation_id"],
            "has_highsec": int(stats["highsec_count"] > 0),
            "has_lowsec": int(stats["lowsec_count"] > 0),
            "has_nullsec": int(stats["nullsec_count"] > 0),
            "has_wormhole": int(stats["wormhole_count"] > 0),
        })

    for result in region_rows:
        row = dict(result)
        stats = stats_for(
            region_stats,
            row["region_id"],
        )
        rows.append({
            **row,
            **stats,
            "system_id": None,
            "security_status": None,
            "constellation_id": None,
            "constellation_name": None,
            "region_name": row["name"],
            "kind": "region",
            "object_id": row["region_id"],
            "has_highsec": int(stats["highsec_count"] > 0),
            "has_lowsec": int(stats["lowsec_count"] > 0),
            "has_nullsec": int(stats["nullsec_count"] > 0),
            "has_wormhole": int(stats["wormhole_count"] > 0),
        })

    return KeywordTrieIndex(
        rows,
        facet_keys=(
            "kind",
            "has_highsec",
            "has_lowsec",
            "has_nullsec",
            "has_wormhole",
        ),
    )


_UNIVERSE_SEARCH_INDEX = TrieIndexCache(
    _build_universe_search_index
)


def find_universe_keywords(
    query: str,
    limit: int | None = 25,
    *,
    kind: str | None = None,
    space: str | None = None,
) -> list[dict]:
    filters = {}

    if kind:
        filters["kind"] = kind

    if space:
        facet = SPACE_FILTER_KEYS.get(space)

        if facet is None:
            raise ValueError(f'Unknown universe space filter "{space}"')

        filters[facet] = 1

    return _UNIVERSE_SEARCH_INDEX.get().search(
        query,
        limit=limit,
        filters=filters,
    )


def find_systems_keywords(
    query: str,
    limit: int | None = 25,
) -> list[dict]:
    return find_universe_keywords(
        query,
        limit=limit,
        kind="system",
    )


def find_constellations_keywords(
    query: str,
    limit: int | None = 25,
) -> list[dict]:
    return find_universe_keywords(
        query,
        limit=limit,
        kind="constellation",
    )


def find_regions_keywords(
    query: str,
    limit: int | None = 25,
) -> list[dict]:
    return find_universe_keywords(
        query,
        limit=limit,
        kind="region",
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


def find_constellations(
    name: str,
    limit: int = 25,
) -> list[dict]:
    """Compatibility wrapper using keyword search semantics."""
    return find_constellations_keywords(
        name,
        limit=limit,
    )


def find_regions(
    name: str,
    limit: int = 25,
) -> list[dict]:
    """Compatibility wrapper using keyword search semantics."""
    return find_regions_keywords(
        name,
        limit=limit,
    )


def warm_universe_search_indexes():
    _UNIVERSE_SEARCH_INDEX.get()


def clear_universe_search_cache():
    _UNIVERSE_SEARCH_INDEX.clear()


# These are static stargate links from the SDE. Dynamic wormhole connections
# are not part of this graph.
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
    # Return a copy so callers keep the previous mutable-dict contract without
    # being able to mutate a cached result shared by later calls.
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

    # Strict highsec routing refuses endpoints outside highsec too.
    if mode == "highsec" and (
        security[origin_system_id] < 0.45
        or security[destination_system_id] < 0.45
    ):
        return None

    avoided = set(avoided_system_ids or set())
    avoided.discard(origin_system_id)
    avoided.discard(destination_system_id)

    # The first cost value is the route preference penalty, the second is
    # normal jump count.
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
