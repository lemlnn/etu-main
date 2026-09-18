"""region search ui. it stays separate from systems because both search paths are already growing on their own"""

from etu.cli.common import require_sde, select_match
from etu.search import find_exact_name
from etu.universe import (
    find_region_keywords,
    get_region,
)


def _print_region(region):
    print()
    print(f"Name: {region.get('name')}")
    print(f"Region ID: {region.get('region_id')}")
    print(f"Faction ID: {region.get('faction_id')}")
    print(f"Wormhole Class ID: {region.get('wormhole_class_id')}")


def select_region(matches):
    return select_match(
        matches,
        lambda match: (
            f"{match['name']} - "
            f"ID: {match['region_id']}"
        ),
    )

def resolve_region():
    name = input("Region: ").strip()

    matches = find_region_keywords(
        name,
        limit=10,
    )

    exact_match = find_exact_name(name, matches)

    if exact_match is not None:
        return exact_match

    if not matches:
        print(f'No region found matching "{name}".')
        return None

    print()
    print(f'Matches for "{name}":')

    return select_region(matches)

def search_region_by_id():
    if not require_sde():
        return

    raw_id = input("Region ID: ").strip()

    try:
        region_id = int(raw_id)
    except ValueError:
        print("Region ID must be a number.")
        return

    region = get_region(region_id)

    if region is None:
        print(f'No region found with ID "{region_id}".')
        return

    _print_region(region)


def search_region_by_name():
    if not require_sde():
        return

    selected = resolve_region()

    if selected is None:
        return

    region = get_region(selected["region_id"])
    _print_region(region)
