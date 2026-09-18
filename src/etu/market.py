"""market data helpers. esi provides regional orders, and this layer can narrow them to a selected system"""

import requests

from etu import esi
from etu.universe import get_jump_distances


PLEX_TYPE_ID = 44_992
GLOBAL_PLEX_REGION_ID = 19_000_001
GLOBAL_MARKET_NAME = "GLOBAL"


def is_global_market_type(type_id):
    """Return whether an item belongs to EVE's special global market."""
    try:
        return int(type_id) == PLEX_TYPE_ID
    except (TypeError, ValueError):
        return False


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

    return max(
        (
            order["price"]
            for order in orders
            if order["is_buy_order"]
        ),
        default=None,
    )

def get_best_sell(region_id, type_id, system_id=None):
    orders = get_orders(
        region_id,
        type_id,
        system_id,
    )

    return min(
        (
            order["price"]
            for order in orders
            if not order["is_buy_order"]
        ),
        default=None,
    )

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

def get_history(region_id, type_id):
    response = esi.get(
        f"/markets/{region_id}/history",
        params={
            "type_id": type_id,
        },
    )

    return response

def get_history_stats(history, days=30):
    if not history:
        return None

    history = sorted(
        history,
        key=lambda day: day["date"],
    )

    period = history[-days:]

    total_volume = sum(
        day["volume"]
        for day in period
    )

    if total_volume > 0:
        average_price = sum(
            day["average"] * day["volume"]
            for day in period
        ) / total_volume

    else:
        average_price = sum(
            day["average"]
            for day in period
        ) / len(period)

    return {
        "days": len(period),
        "average": average_price,
        "highest": max(
            day["highest"]
            for day in period
        ),
        "lowest": min(
            day["lowest"]
            for day in period
        ),
        "total_volume": total_volume,
        "average_daily_volume": total_volume / len(period),
        "order_count": sum(
            day["order_count"]
            for day in period
        ),
        "latest": period[-1],
    }