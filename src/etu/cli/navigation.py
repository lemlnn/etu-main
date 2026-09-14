"""navigation cli for planning routes through static stargate connections"""

from etu.cli.common import require_sde
from etu.cli.systems import resolve_system
from etu.universe import get_route


ROUTE_MODES = {
    "1": ("shortest", "Shortest"),
    "2": ("safer", "Safer"),
    "3": ("less_secure", "Less Secure"),
    "4": ("highsec", "Highsec Only"),
}


def select_route_mode():
    while True:
        print()
        print("Route Preference")
        print()
        print("[1] Shortest")
        print("[2] Safer")
        print("[3] Less Secure")
        print("[4] Highsec Only")
        print("[B] Back")

        choice = input("> ").strip().lower()

        if choice == "b":
            return None

        if choice in ROUTE_MODES:
            return ROUTE_MODES[choice]

        print("Invalid option.")


def collect_waypoints():
    waypoints = []

    while True:
        choice = input("Add waypoint? [y/N]: ").strip().lower()

        if choice not in {"y", "yes"}:
            return waypoints

        waypoint = resolve_system(
            f"Waypoint {len(waypoints) + 1}"
        )

        if waypoint is None:
            return waypoints

        waypoints.append(waypoint)


def collect_avoided_systems():
    avoided = []

    while True:
        choice = input("Add avoided system? [y/N]: ").strip().lower()

        if choice not in {"y", "yes"}:
            return avoided

        system = resolve_system(
            f"Avoid {len(avoided) + 1}"
        )

        if system is None:
            return avoided

        if any(
            existing["system_id"] == system["system_id"]
            for existing in avoided
        ):
            print("System is already being avoided.")
            continue

        avoided.append(system)


def build_route(points, mode, avoided_system_ids):
    route = []

    for index in range(len(points) - 1):
        origin = points[index]
        destination = points[index + 1]

        segment = get_route(
            origin["system_id"],
            destination["system_id"],
            mode,
            avoided_system_ids,
        )

        if segment is None:
            return None, origin, destination

        if route:
            segment = segment[1:]

        route.extend(segment)

    return route, None, None


def get_security_summary(route):
    highsec = 0
    lowsec = 0
    nullsec = 0

    for system in route:
        security = system["security_status"]

        if security >= 0.45:
            highsec += 1

        elif security > 0.0:
            lowsec += 1

        else:
            nullsec += 1

    return {
        "highsec": highsec,
        "lowsec": lowsec,
        "nullsec": nullsec,
    }


def print_route(route, mode_name, waypoints, avoided):
    jumps = len(route) - 1
    security = get_security_summary(route)

    print()
    print(
        f"Route: {route[0]['name']} -> "
        f"{route[-1]['name']}"
    )
    print(f"Preference: {mode_name}")
    print(f"Jumps: {jumps}")
    print(
        f"Security: {security['highsec']} highsec - "
        f"{security['lowsec']} lowsec - "
        f"{security['nullsec']} nullsec"
    )

    if waypoints:
        print(
            "Waypoints: "
            + " -> ".join(
                waypoint["name"]
                for waypoint in waypoints
            )
        )

    if avoided:
        print(
            "Avoiding: "
            + ", ".join(
                system["name"]
                for system in avoided
            )
        )

    print()

    previous_region = None

    for jump, system in enumerate(route):
        if (
            previous_region is not None
            and system["region_name"] != previous_region
        ):
            print()
            print(f"Entering {system['region_name']}")
            print()

        print(
            f"[{jump}] {system['name']} - "
            f"Security: {system['security_status']:.1f} - "
            f"Region: {system['region_name']}"
        )

        previous_region = system["region_name"]


def plan_route():
    if not require_sde():
        return

    route_mode = select_route_mode()

    if route_mode is None:
        return

    mode, mode_name = route_mode

    origin = resolve_system("Origin")

    if origin is None:
        return

    waypoints = collect_waypoints()

    destination = resolve_system("Destination")

    if destination is None:
        return

    avoided = collect_avoided_systems()
    avoided_system_ids = {
        system["system_id"]
        for system in avoided
    }

    points = [
        origin,
        *waypoints,
        destination,
    ]

    route, failed_origin, failed_destination = build_route(
        points,
        mode,
        avoided_system_ids,
    )

    if route is None:
        print()
        print(
            f"No {mode_name.lower()} static stargate route found "
            f"from {failed_origin['name']} to {failed_destination['name']}."
        )
        return

    print_route(
        route,
        mode_name,
        waypoints,
        avoided,
    )


def navigation_menu():
    while True:
        print()
        print("Navigation")
        print()
        print("[1] Plan route")
        print("[B] Back")

        choice = input("> ").strip().lower()

        if choice == "1":
            plan_route()

        elif choice == "b":
            return

        else:
            print("Invalid option.")
