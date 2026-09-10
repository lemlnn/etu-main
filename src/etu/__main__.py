import json
import sqlite3
import zipfile
import requests

from rapidfuzz import fuzz
from etu import sde
from etu.inventory import (
    find_type,
    find_type_fuzzy,
    get_type,
)
from etu.universe import (
    find_system,
    find_system_fuzzy,
    get_system,
    find_region,
    find_region_fuzzy,
    get_region,
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

def search_market_orders():
    selection = get_market_selection()

    if selection is None:
        return

    orders = get_orders(
        selection["region_id"],
        selection["type_id"],
    )

    if not orders:
        print("No market orders found.")
        return

    print()
    print(f"Item: {selection['item_name']}")
    print(f"Region: {selection['region_name']}")
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
    selection = get_market_selection()

    if selection is None:
        return

    price = get_best_buy(
        selection["region_id"],
        selection["type_id"],
    )

    if price is None:
        print("No buy orders found.")
        return

    print()
    print(f"Item: {selection['item_name']}")
    print(f"Region: {selection['region_name']}")
    print(f"Best buy: {price:,.2f} ISK")

def search_best_sell():
    selection = get_market_selection()

    if selection is None:
        return

    price = get_best_sell(
        selection["region_id"],
        selection["type_id"],
    )

    if price is None:
        print("No sell orders found.")
        return

    print()
    print(f"Item: {selection['item_name']}")
    print(f"Region: {selection['region_name']}")
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

def rank_system_matches(query, matches):
    query = query.casefold()

    def score(match):
        name = match["name"].casefold()

        if name == query:
            return (4, 100)

        if name.startswith(query):
            return (3, 100)

        if query in name:
            return (2, 100)

        return (1, fuzz.ratio(query, name))

    return sorted(
        matches,
        key=score,
        reverse=True,
    )

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

def merge_matches(fuzzy_matches, partial_matches, id_key):
    combined = []
    seen = set()

    for match in fuzzy_matches + partial_matches:
        match_id = match[id_key]

        if match_id in seen:
            continue

        seen.add(match_id)
        combined.append(match)

    return combined

def get_market_selection():
    if not require_sde():
        return None

    item = resolve_type()

    if item is None:
        return None

    system_match = resolve_system()

    if system_match is None:
        return None

    system = get_system(system_match["system_id"])

    return {
        "type_id": item["type_id"],
        "item_name": item["name"],
        "system_id": system["system_id"],
        "system_name": system["name"],
        "region_id": system["region_id"],
        "region_name": system["region_name"],
    }

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
        print("[3] Search region by ID")
        print("[4] Search region by name")
        print("[B] Back")

        choice = input("> ").strip().lower()

        if choice == "1":
            search_system_by_id()

        elif choice == "2":
            search_system_by_name()

        elif choice == "3":
            search_region_by_id()

        elif choice == "4":
            search_region_by_name()

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
        print("[2] Search best buy order for an item")
        print("[3] Search best sell order for an item")
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
        print("ETU dev-0.0.8")
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