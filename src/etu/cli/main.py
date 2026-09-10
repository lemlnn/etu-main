"""top-level etu menu. it stays focused on routing so adding features does not turn the entry point into another giant file"""

from etu.cli.data import data_menu
from etu.cli.inventory import inventory_menu
from etu.cli.market import market_menu
from etu.cli.universe import universe_menu


def main():
    while True:
        print()
        print("ETU dev-0.1.1")
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
