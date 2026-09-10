from etu.cli.common import require_sde
from etu.cli.search import merge_matches
from etu.universe import (
    find_region,
    find_region_fuzzy,
    get_region,
)


def select_region(matches):
    if len(matches) == 1:
        return matches[0]

    print()

    for number, match in enumerate(matches, start=1):
        print(
            f"[{number}] {match['name']} - "
            f"ID: {match['region_id']}"
        )

    print("[B] Back")

    while True:
        choice = input("> ").strip().lower()

        if choice == "b":
            return None

        try:
            index = int(choice) - 1
        except ValueError:
            print("Invalid option.")
            continue

        if 0 <= index < len(matches):
            return matches[index]

        print("Invalid option.")

def resolve_region():
    name = input("Region: ").strip()

    partial_matches = find_region(name)

    exact_match = next(
        (
            match
            for match in partial_matches
            if match["name"].casefold() == name.casefold()
        ),
        None,
    )

    if exact_match is not None:
        return exact_match

    fuzzy_matches = find_region_fuzzy(name)

    matches = merge_matches(
        fuzzy_matches,
        partial_matches,
        "region_id",
    )

    matches = matches[:10]

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

    print()
    print(f"Name: {region.get('name')}")
    print(f"Region ID: {region.get('region_id')}")
    print(f"Faction ID: {region.get('faction_id')}")
    print(f"Wormhole Class ID: {region.get('wormhole_class_id')}")

def search_region_by_name():
    if not require_sde():
        return

    selected = resolve_region()

    if selected is None:
        return

    region = get_region(selected["region_id"])

    print()
    print(f"Name: {region.get('name')}")
    print(f"Region ID: {region.get('region_id')}")
    print(f"Faction ID: {region.get('faction_id')}")
    print(f"Wormhole Class ID: {region.get('wormhole_class_id')}")
