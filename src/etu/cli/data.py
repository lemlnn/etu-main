"""data menu for checking and updating the sde. common failures are handled here instead of dropping out of the cli"""

import json
import sqlite3
import zipfile

import requests

from etu import sde


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
