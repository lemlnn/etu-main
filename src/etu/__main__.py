import sqlite3

from etu import sde
from etu.inventory import (
    find_type,
    get_type,
    get_group,
    get_category,
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
    
    name = input("Item name: ").strip()

    matches = find_type(name)

    if not matches:
        print(f'No inventory type found named "{name}".')
        return

    for match in matches:
        print(
            f"{match['name']} - ID: {match['type_id']} - "
            f"{match['group_name']} - {match['category_name']}"
        )

def import_static_data():
    try:
        sde.import_sde()

    except FileNotFoundError as error:
        print(error)

    except sqlite3.Error as error:
        print(f"Database error: {error}")

def require_sde():
    if sde.is_ready():
        return True

    print("SDE database has not been imported.")
    print("Use option [3] to import/update the SDE.")
    return False

def main():
    print("ETU dev-0.0.4")
    print()
    print("[1] Search inventory type by ID")
    print("[2] Search inventory type by name")
    print("[3] Import/update SDE")

    choice = input("> ").strip()

    if choice == "1":
        search_by_id()

    elif choice == "2":
        search_by_name()

    elif choice == "3":
        import_static_data()

    else:
        print("Invalid option.")

if __name__ == "__main__":
    main()