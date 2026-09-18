"""inventory cli flow. this module handles prompts and result selection while the actual lookups stay in ``etu.inventory``"""

from etu.cli.common import require_sde, select_match
from etu.search import find_exact_name
from etu.inventory import (
    find_type_keywords,
    get_type,
)


def _print_type(item):
    print()
    print(f"Name: {item.get('name')}")
    print(f"Type ID: {item.get('type_id')}")
    print(f"Group: {item.get('group_name')} - ID: {item.get('group_id')}")
    print(f"Category: {item.get('category_name')} - ID: {item.get('category_id')}")
    print(f"Volume: {item.get('volume')}")
    print(f"Published: {item.get('published')}")

    if description := item.get("description"):
        print()
        print("Description:")
        print(description)


def search_by_id():
    if not require_sde():
        return

    raw_id = input("Type ID: ").strip()

    try:
        type_id = int(raw_id)
    except ValueError:
        print("Type ID must be a number.")
        return

    item = get_type(type_id)

    if item is None:
        print(f'No inventory type found with ID "{type_id}".')
        return

    _print_type(item)


def search_by_name():
    if not require_sde():
        return

    selected = resolve_type()

    if selected is None:
        return

    item = get_type(selected["type_id"])
    _print_type(item)

def select_type(matches):
    return select_match(
        matches,
        lambda match: (
            f"{match['name']} - "
            f"{match['group_name']} - "
            f"ID: {match['type_id']}"
        ),
    )

def resolve_type():
    name = input("Item: ").strip()

    matches = find_type_keywords(
        name,
        limit=10,
        published_only=False,
    )

    exact_match = find_exact_name(name, matches)

    if exact_match is not None:
        return exact_match

    if not matches:
        print(f'No inventory type found matching "{name}".')
        return None

    print()
    print(f'Matches for "{name}":')

    return select_type(matches)

def inventory_menu():
    while True:
        print()
        print("Inventory")
        print()
        print("[1] Search by ID")
        print("[2] Search by name")
        print("[B] Back")

        choice = input("> ").strip().lower()

        if choice == "1":
            search_by_id()

        elif choice == "2":
            search_by_name()

        elif choice == "b":
            return

        else:
            print("Invalid option.")
