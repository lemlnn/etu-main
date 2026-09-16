"""top-level etu menu. it stays focused on routing so adding features does not turn the entry point into another giant file"""

import subprocess
import sys

from etu.cli.data import data_menu
from etu.cli.inventory import inventory_menu
from etu.cli.market import market_menu
from etu.cli.universe import universe_menu
from etu.cli.navigation import navigation_menu


def launch_gui():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "etu.gui",
        ],
        check=False,
    )

    if result.returncode != 0:
        print("ETU GUI closed with an error.")


def main():
    while True:
        print()
        print("ETU dev-0.1.4")
        print()
        print("[1] Inventory")
        print("[2] Universe")
        print("[3] Market")
        print("[4] Navigation")
        print("[5] Data")
        print("[G] Launch GUI")
        print("[Q] Quit")

        choice = input("> ").strip().lower()

        if choice == "1":
            inventory_menu()

        elif choice == "2":
            universe_menu()

        elif choice == "3":
            market_menu()

        elif choice == "4":
            navigation_menu()

        elif choice == "5":
            data_menu()

        elif choice == "g":
            launch_gui()

        elif choice == "q":
            break

        else:
            print("Invalid option.")
