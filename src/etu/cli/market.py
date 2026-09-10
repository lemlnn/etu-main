"""market cli flow. this module handles scope selection and readable output while ``etu.market`` deals with the esi data"""

import requests

from etu.cli.common import require_sde
from etu.cli.inventory import resolve_type
from etu.cli.systems import resolve_system
from etu.cli.regions import resolve_region
from etu.market import (
    get_orders,
    get_best_buy,
    get_best_sell,
    get_location_names,
)
from etu.universe import get_system

ORDER_DISPLAY_LIMIT = 10

def print_order_group(title, orders, location_names):
    print(title)
    print()

    for order in orders[:ORDER_DISPLAY_LIMIT]:
        location_id = order["location_id"]

        location_name = location_names.get(
            location_id,
            f"Player Structure - {location_id}",
        )

        print(
            f"{order['price']:,.2f} ISK - "
            f"Volume: {order['volume_remain']:,} - "
            f"Location: {location_name}"
        )

    remaining = len(orders) - ORDER_DISPLAY_LIMIT

    if remaining > 0:
        print()
        print(f"... {remaining:,} more orders")

def search_market_orders():
    selection = get_market_selection()

    if selection is None:
        return

    orders = get_orders(
        selection["region_id"],
        selection["type_id"],
        selection["system_id"],
    )

    if not orders:
        print("No market orders found.")
        return

    # sell orders read naturally cheapest-first; buy orders are the opposite
    sell_orders = sorted(
        [
            order
            for order in orders
            if not order["is_buy_order"]
        ],
        key=lambda order: order["price"],
    )

    buy_orders = sorted(
        [
            order
            for order in orders
            if order["is_buy_order"]
        ],
        key=lambda order: order["price"],
        reverse=True,
    )

    # resolve all public station names in one batch instead of making a request per order
    location_ids = [
        order["location_id"]
        for order in orders
    ]

    location_names = get_location_names(
        location_ids,
    )

    print()
    print(f"Item: {selection['item_name']}")

    if selection["system_id"] is not None:
        print(f"System: {selection['system_name']}")
        print(f"Region: {selection['region_name']}")

    else:
        print(f"Region: {selection['region_name']}")

    if sell_orders:
        print()
        print_order_group(
            "Sell Orders",
            sell_orders,
            location_names,
        )

    if buy_orders:
        print()
        print_order_group(
            "Buy Orders",
            buy_orders,
            location_names,
        )

def search_best_buy():
    selection = get_market_selection()

    if selection is None:
        return

    price = get_best_buy(
        selection["region_id"],
        selection["type_id"],
        selection["system_id"],
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
        selection["system_id"],
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

    while True:
        print()
        print("Market Scope")
        print()
        print("[1] System")
        print("[2] Region")
        print("[B] Back")

        choice = input("> ").strip().lower()

        if choice == "1":
            # esi market orders are regional, but the result can be filtered down to this system later
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

        elif choice == "2":
            region = resolve_region()

            if region is None:
                return None

            return {
                "type_id": item["type_id"],
                "item_name": item["name"],
                "system_id": None,
                "system_name": None,
                "region_id": region["region_id"],
                "region_name": region["name"],
            }

        elif choice == "b":
            return None

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
