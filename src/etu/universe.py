from etu import sde


def get_system(system_id: int) -> dict | None:
    data = sde.get_system(system_id)

    if data is None:
        return None

    data["connections"] = sde.get_system_connections(system_id)

    return data

def find_system(name: str) -> list[dict]:
    return sde.find_systems(name)

def find_system_fuzzy(name: str) -> list[dict]:
    return sde.find_systems_fuzzy(name)

def get_region(region_id: int) -> dict | None:
    return sde.get_region(region_id)

def find_region(name: str) -> list[dict]:
    return sde.find_regions(name)

def find_region_fuzzy(name: str) -> list[dict]:
    return sde.find_regions_fuzzy(name)