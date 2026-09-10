from etu import esi

def get_orders(region_id, type_id):
    response = esi.get(
        f"/markets/{region_id}/orders",
        params={
            "order_type": "all",
            "type_id": type_id,
        },
    )

    return response

def get_best_buy(region_id, type_id):
    orders = get_orders(region_id, type_id)

    if orders is None:
        return None
    buy_orders = [
        order
        for order in orders
        if order["is_buy_order"]
    ]

    highest_buy = max(
        order["price"]
        for order in buy_orders
    )

    return highest_buy

def get_best_sell(region_id, type_id):
    orders = get_orders(region_id, type_id)

    if orders is None:
        return None

    sell_orders = [
        order
        for order in orders
        if not order["is_buy_order"]
    ]

    cheapest_sell = min(
        order["price"]
        for order in sell_orders
    )

    return cheapest_sell
