from etu import sde


def get_system(system_id: int) -> dict | None:
    data = sde.get_system(system_id)

    if data is None:
        return None

    data["connections"] = sde.get_system_connections(system_id)

    return data

def find_system(name: str) -> list[dict]:
    return sde.find_systems(name)