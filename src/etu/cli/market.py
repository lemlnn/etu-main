import requests

from etu.cli.common import require_sde
from etu.cli.inventory import resolve_type
from etu.cli.systems import resolve_system
from etu.market import (
    get_orders,
    get_best_buy,
    get_best_sell,
)
from etu.universe import get_system


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
