from etu.cli.common import require_sde
from etu.cli.search import (
    merge_matches,
    rank_system_matches,
)
from etu.universe import (
    find_system,
    find_system_fuzzy,
    get_system,
)


def search_system_by_name():
    if not require_sde():
        return

    selected = resolve_system()

    if selected is None:
        return

    system = get_system(selected["system_id"])

    print()
    print(f"Name: {system.get('name')}")
    print(f"System ID: {system.get('system_id')}")
    print(f"Security: {system.get('security_status'):.1f}")
    print(
        f"Constellation: {system.get('constellation_name')} - "
        f"ID: {system.get('constellation_id')}"
    )
    print(
        f"Region: {system.get('region_name')} - "
        f"ID: {system.get('region_id')}"
    )

    print()
    print("Connections:")

    for connection in system["connections"]:
        print(
            f"{connection['name']} - "
            f"ID: {connection['system_id']} - "
            f"Security: {connection['security_status']:.1f}"
        )

def search_system_by_id():
    if not require_sde():
        return

    raw_id = input("System ID: ").strip()

    try:
        system_id = int(raw_id)
    except ValueError:
        print("System ID must be a number.")
        return

    system = get_system(system_id)

    if system is None:
        print(f'No solar system found with ID "{system_id}".')
        return

    print()
    print(f"Name: {system.get('name')}")
    print(f"System ID: {system_id}")
    print(f"Security: {system.get('security_status'):.1f}")

    print(
        f"Constellation: {system.get('constellation_name')} - "
        f"ID: {system.get('constellation_id')}"
    )

    print(
        f"Region: {system.get('region_name')} - "
        f"ID: {system.get('region_id')}"
    )

    print()
    print("Connections:")

    for connection in system["connections"]:
        print(
            f"{connection['name']} - "
            f"ID: {connection['system_id']} - "
            f"Security: {connection['security_status']:.1f}"
        )

def select_system(matches):
    if len(matches) == 1:
        return matches[0]

    print()

    for number, match in enumerate(matches, start=1):
        print(
            f"[{number}] {match['name']} - "
            f"Security: {match['security_status']:.1f}"
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

def resolve_system():
    name = input("System: ").strip()

    partial_matches = find_system(name)

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

    fuzzy_matches = find_system_fuzzy(name)

    matches = merge_matches(
        fuzzy_matches,
        partial_matches,
        "system_id",
    )

    matches = rank_system_matches(
        name,
        matches,
    )

    matches = matches[:10]

    if not matches:
        print(f'No solar system found matching "{name}".')
        return None

    print()
    print(f'Matches for "{name}":')

    return select_system(matches)
