import sqlite3

from etu import sde
from etu.inventory import (
    find_type,
    get_type,
    get_group,
    get_category,
)
from etu.universe import (
    find_system,
    get_system,
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

def search_system_by_name():
    if not require_sde():
        return

    name = input("System name: ").strip()

    matches = find_system(name)

    if not matches:
        print(f'No solar system found named "{name}".')
        return

    for match in matches:
        print(
            f"{match['name']} - ID: {match['system_id']} - "
            f"Security: {match['security_status']:.1f}"
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
    print("ETU dev-0.0.5")
    print()
    print("[1] Search inventory type by ID")
    print("[2] Search inventory type by name")
    print("[3] Import/update SDE")
    print("[4] Search solar system by ID")
    print("[5] Search solar system by name")

    choice = input("> ").strip()

    if choice == "1":
        search_by_id()

    elif choice == "2":
        search_by_name()

    elif choice == "3":
        import_static_data()

    elif choice == "4":
        search_system_by_id()

    elif choice == "5":
        search_system_by_name()

    else:
        print("Invalid option.")

if __name__ == "__main__":
    main()