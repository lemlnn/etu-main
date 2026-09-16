"""search helpers shared by gui pages"""

from rapidfuzz import fuzz

from etu.inventory import (
    find_type,
    find_type_fuzzy,
    get_type,
)
from etu.universe import (
    find_region,
    find_region_fuzzy,
    find_system,
    find_system_fuzzy,
    get_region,
    get_system,
)


def _merge_matches(*groups, id_key):
    merged = []
    seen = set()

    for group in groups:
        for match in group:
            match_id = match[id_key]

            if match_id in seen:
                continue

            seen.add(match_id)
            merged.append(match)

    return merged


def _rank_matches(query, matches):
    query = query.casefold()

    def score(match):
        name = match["name"].casefold()

        if name == query:
            return (4, 100)

        if name.startswith(query):
            return (3, 100)

        if query in name:
            return (2, 100)

        return (
            1,
            fuzz.ratio(query, name),
        )

    return sorted(
        matches,
        key=score,
        reverse=True,
    )


def search_types(query, limit=25):
    query = query.strip()

    if not query:
        return []

    if query.isdigit():
        item = get_type(int(query))
        return [item] if item else []

    matches = _merge_matches(
        find_type(query),
        find_type_fuzzy(query),
        id_key="type_id",
    )

    return _rank_matches(
        query,
        matches,
    )[:limit]


def search_systems(query, limit=25):
    query = query.strip()

    if not query:
        return []

    if query.isdigit():
        system = get_system(int(query))
        return [system] if system else []

    matches = _merge_matches(
        find_system(query),
        find_system_fuzzy(query),
        id_key="system_id",
    )

    return _rank_matches(
        query,
        matches,
    )[:limit]


def search_regions(query, limit=25):
    query = query.strip()

    if not query:
        return []

    if query.isdigit():
        region = get_region(int(query))
        return [region] if region else []

    matches = _merge_matches(
        find_region(query),
        find_region_fuzzy(query),
        id_key="region_id",
    )

    return _rank_matches(
        query,
        matches,
    )[:limit]


def resolve_type(query):
    matches = search_types(query, limit=1)
    return matches[0] if matches else None


def resolve_system(query):
    matches = search_systems(query, limit=1)
    return matches[0] if matches else None


def resolve_region(query):
    matches = search_regions(query, limit=1)
    return matches[0] if matches else None
