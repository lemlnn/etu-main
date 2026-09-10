import json
import sqlite3
import zipfile

import requests

from etu import sde
from etu.inventory import (
    find_type,
    get_type,
)
from etu.universe import (
    find_system,
    get_system,
)
from etu.market import (
    get_orders,
    get_best_buy,
    get_best_sell,
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


def get_market_ids():
    raw_region_id = input("Region ID: ").strip()
    raw_type_id = input("Type ID: ").strip()

    try:
        region_id = int(raw_region_id)
        type_id = int(raw_type_id)

    except ValueError:
        print("Region ID and Type ID must be numbers.")
        return None

    return region_id, type_id


def search_market_orders():
    ids = get_market_ids()

    if ids is None:
        return

    region_id, type_id = ids

    orders = get_orders(region_id, type_id)

    if not orders:
        print("No market orders found.")
        return

    print()

    for order in orders:
        order_type = "BUY" if order["is_buy_order"] else "SELL"

        print(
            f"{order_type} - "
            f"{order['price']:,.2f} ISK - "
            f"Volume: {order['volume_remain']:,} - "
            f"Location: {order['location_id']}"
        )


def search_best_buy():
    ids = get_market_ids()

    if ids is None:
        return

    region_id, type_id = ids

    price = get_best_buy(region_id, type_id)

    if price is None:
        print("No buy orders found.")
        return

    print()
    print(f"Best buy: {price:,.2f} ISK")


def search_best_sell():
    ids = get_market_ids()

    if ids is None:
        return

    region_id, type_id = ids

    price = get_best_sell(region_id, type_id)

    if price is None:
        print("No sell orders found.")
        return

    print()
    print(f"Best sell: {price:,.2f} ISK")


def update_static_data():
    try:
        sde.update_sde()

    except requests.RequestException as error:
        print(f"Download error: {error}")

    except zipfile.BadZipFile:
        print("Downloaded SDE archive is invalid.")

    except (
        FileNotFoundError,
        RuntimeError,
        json.JSONDecodeError,
    ) as error:
        print(f"SDE error: {error}")

    except sqlite3.Error as error:
        print(f"Database error: {error}")


def require_sde():
    if sde.is_ready():
        return True

    print("SDE database has not been imported.")
    print("Use the Data menu to import/update the SDE.")

    return False


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


def universe_menu():
    while True:
        print()
        print("Universe")
        print()
        print("[1] Search system by ID")
        print("[2] Search system by name")
        print("[B] Back")

        choice = input("> ").strip().lower()

        if choice == "1":
            search_system_by_id()

        elif choice == "2":
            search_system_by_name()

        elif choice == "b":
            return

        else:
            print("Invalid option.")


def market_menu():
    while True:
        print()
        print("Market")
        print()
        print("[1] Search all orders for an item")
        print("[2] Search best buy order in region for an item")
        print("[3] Search best sell order in region for an item")
        print("[B] Back")

        choice = input("> ").strip().lower()

        try:
            if choice == "1":
                search_market_orders()

            elif choice == "2":
                search_best_buy()

            elif choice == "3":
                search_best_sell()

            elif choice == "b":
                return

            else:
                print("Invalid option.")

        except requests.RequestException as error:
            print(f"ESI request failed: {error}")


def data_menu():
    while True:
        print()
        print("Data")
        print()
        print("[1] Check/update SDE")
        print("[B] Back")

        choice = input("> ").strip().lower()

        if choice == "1":
            update_static_data()

        elif choice == "b":
            return

        else:
            print("Invalid option.")


def main():
    while True:
        print()
        print("ETU dev-0.0.7")
        print()
        print("[1] Inventory")
        print("[2] Universe")
        print("[3] Market")
        print("[4] Data")
        print("[Q] Quit")

        choice = input("> ").strip().lower()

        if choice == "1":
            inventory_menu()

        elif choice == "2":
            universe_menu()

        elif choice == "3":
            market_menu()

        elif choice == "4":
            data_menu()

        elif choice == "q":
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()