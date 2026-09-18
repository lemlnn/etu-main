"""solar-system search UI using deterministic keyword matching"""

from etu.cli.common import require_sde, select_match
from etu.search import find_exact_name
from etu.universe import (
    find_system_keywords,
    get_system,
)


def _print_system(system):
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


def search_system_by_name():
    if not require_sde():
        return

    selected = resolve_system()

    if selected is None:
        return

    system = get_system(selected["system_id"])
    _print_system(system)


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

    _print_system(system)

def select_system(matches):
    return select_match(
        matches,
        lambda match: (
            f"{match['name']} - "
            f"Security: {match['security_status']:.1f}"
        ),
    )

def resolve_system(prompt="System"):
    name = input(f"{prompt}: ").strip()

    if not name:
        print("System name cannot be empty.")
        return None

    matches = find_system_keywords(
        name,
        limit=10,
    )

    exact_match = find_exact_name(name, matches)

    if exact_match is not None:
        return exact_match

    if not matches:
        print(f'No solar system found matching "{name}".')
        return None

    print()
    print(f'Matches for "{name}":')

    return select_system(matches)
