from etu.cli.regions import (
    search_region_by_id,
    search_region_by_name,
)
from etu.cli.systems import (
    search_system_by_id,
    search_system_by_name,
)


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
