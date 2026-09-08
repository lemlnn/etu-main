import requests

from etu.inventory import find_type, get_type


def search_by_id():
    raw_id = input("Type ID: ").strip()

    try:
        type_id = int(raw_id)
    except ValueError:
        print("Type ID must be a number.")
        return

    data = get_type(type_id)

    print()
    print(f"Name: {data.get('name')}")
    print(f"Type ID: {type_id}")
    print(f"Group ID: {data.get('group_id')}")
    print(f"Volume: {data.get('volume')}")
    print(f"Published: {data.get('published')}")

    if description := data.get("description"):
        print()
        print("Description:")
        print(description)


def search_by_name():
    name = input("Item name: ").strip()

    matches = find_type(name)

    if not matches:
        print(f'No inventory type found named "{name}".')
        return

    for match in matches:
        print(f"{match['name']} - ID: {match['id']}")


def main():
    print("ETU dev-0.0.1")
    print()
    print("[1] Search inventory type by ID")
    print("[2] Search inventory type by name")

    choice = input("> ").strip()

    try:
        if choice == "1":
            search_by_id()

        elif choice == "2":
            search_by_name()

        else:
            print("Invalid option.")

    except requests.HTTPError as error:
        if error.response.status_code == 404:
            print("ESI could not find that object.")
        else:
            print(f"ESI returned an error: {error}")

    except requests.RequestException as error:
        print(f"Network request failed: {error}")


if __name__ == "__main__":
    main()