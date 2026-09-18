"""small helpers shared by the cli. right now this mostly makes sure the local sde is ready before other cli code uses it"""

from etu import sde


def require_sde():
    if sde.is_ready():
        return True

    print("SDE database has not been imported.")
    print("Use the Data menu to import/update the SDE.")

    return False


def select_match(matches, format_match):
    """Prompt for one result from an already-ranked match list."""
    if len(matches) == 1:
        return matches[0]

    print()

    for number, match in enumerate(matches, start=1):
        print(f"[{number}] {format_match(match)}")

    print("[B] Back")

    while True:
        choice = input("> ").strip().lower()

        if choice == "b":
            return None

        try:
            index = int(choice) - 1
        except ValueError:
            print("Invalid option.")
            continue

        if 0 <= index < len(matches):
            return matches[index]

        print("Invalid option.")

