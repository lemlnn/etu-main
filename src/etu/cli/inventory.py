from etu.cli.common import require_sde
from etu.cli.search import merge_matches
from etu.inventory import (
    find_type,
    find_type_fuzzy,
    get_type,
)


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

    print()
    print(f"Name: {item.get('name')}")
    print(f"Type ID: {type_id}")
    print(f"Group: {item.get('group_name')} - ID: {item.get('group_id')}")
    print(f"Category: {item.get('category_name')} - ID: {item.get('category_id')}")
    print(f"Volume: {item.get('volume')}")
    print(f"Published: {item.get('published')}")

    if description := item.get("description"):
        print()
        print("Description:")
        print(description)


def search_by_name():
    if not require_sde():
        return

    selected = resolve_type()

    if selected is None:
        return

    item = get_type(selected["type_id"])

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

def select_type(matches):
    if len(matches) == 1:
        return matches[0]

    print()

    for number, match in enumerate(matches, start=1):
        print(
            f"[{number}] {match['name']} - "
            f"{match['group_name']} - "
            f"ID: {match['type_id']}"
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

def resolve_type():
    name = input("Item: ").strip()

    partial_matches = find_type(name)

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

    fuzzy_matches = find_type_fuzzy(name)

    matches = merge_matches(
        fuzzy_matches,
        partial_matches,
        "type_id",
    )

    matches = matches[:10]

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
