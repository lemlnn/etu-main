from etu import sde


def require_sde():
    if sde.is_ready():
        return True

    print("SDE database has not been imported.")
    print("Use the Data menu to import/update the SDE.")

    return False
