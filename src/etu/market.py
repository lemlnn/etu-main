"""market data helpers. esi provides regional orders, and this layer can narrow them to a selected system"""

import requests

from etu import esi
from etu.universe import get_jump_distances

def get_orders(region_id, type_id, system_id=None):
    response = esi.get_pages(
        f"/markets/{region_id}/orders",
        params={
            "order_type": "all",
            "type_id": type_id,
        },
    )

    # the esi route is regional, so system scope is a local filter on the returned orders
    if system_id is not None:
        response = [
            order
            for order in response
            if order["system_id"] == system_id
        ]

    return response

def get_best_buy(region_id, type_id, system_id=None):
    orders = get_orders(
        region_id,
        type_id,
        system_id,
    )

    if not orders:
        return None

    buy_orders = [
        order
        for order in orders
        if order["is_buy_order"]
    ]

    if not buy_orders:
        return None

    highest_buy = max(
        order["price"]
        for order in buy_orders
    )

    return highest_buy

def get_best_sell(region_id, type_id, system_id=None):
    orders = get_orders(
        region_id,
        type_id,
        system_id,
    )

    if not orders:
        return None

    sell_orders = [
        order
        for order in orders
        if not order["is_buy_order"]
    ]

    if not sell_orders:
        return None

    cheapest_sell = min(
        order["price"]
        for order in sell_orders
    )

    return cheapest_sell

def get_location_names(location_ids):
    # public name resolution works for normal stations; larger structure ids are left for sso later
    station_ids = [
        location_id
        for location_id in set(location_ids)
        if location_id <= 2_147_483_647
    ]

    if not station_ids:
        return {}

    try:
        results = esi.post(
            "/universe/names",
            station_ids,
        )
    except requests.HTTPError:
        return {}

    return {
        result["id"]: result["name"]
        for result in results
        if result["category"] == "station"
    }

def get_buy_orders_reaching_system(region_id, type_id, system_id):
    orders = get_orders(
        region_id,
        type_id,
    )

    distances = get_jump_distances(
        system_id,
        40,
    )

    matching_orders = []

    for order in orders:
        if not order["is_buy_order"]:
            continue

        order_range = order["range"]
        order_system_id = order["system_id"]
        distance = distances.get(order_system_id)

        if order_range == "region":
            matches = True

        elif order_range == "solarsystem":
            matches = order_system_id == system_id

        elif order_range == "station":
            matches = order_system_id == system_id

        else:
            try:
                max_jumps = int(order_range)
            except ValueError:
                continue

            matches = (
                distance is not None
                and distance <= max_jumps
            )

        if not matches:
            continue

        result = dict(order)
        result["distance"] = distance

        matching_orders.append(result)

    return matching_orders