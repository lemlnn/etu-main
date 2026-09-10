"""small helpers shared by the cli. right now this mostly makes sure the local sde is ready before other cli code uses it"""

from etu import sde


def require_sde():
    if sde.is_ready():
        return True

    print("SDE database has not been imported.")
    print("Use the Data menu to import/update the SDE.")

    return False
