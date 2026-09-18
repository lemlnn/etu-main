"""universe service layer between the cli and sde. it attaches static stargate connections before returning a full system result"""

from etu import sde


def get_system(system_id: int) -> dict | None:
    data = sde.get_system(system_id)

    if data is None:
        return None

    # connections are attached here so callers get one complete system object instead of doing another lookup themselves
    data["connections"] = sde.get_system_connections(system_id)

    return data

def find_system(name: str) -> list[dict]:
    return sde.find_systems(name)

def find_system_keywords(
    query: str,
    limit: int | None = 25,
) -> list[dict]:
    return sde.find_systems_keywords(
        query,
        limit=limit,
    )

def get_region(region_id: int) -> dict | None:
    return sde.get_region(region_id)

def find_region(name: str) -> list[dict]:
    return sde.find_regions(name)

def find_region_keywords(
    query: str,
    limit: int | None = 25,
) -> list[dict]:
    return sde.find_regions_keywords(
        query,
        limit=limit,
    )

def get_jump_distances(system_id: int, max_jumps: int = 40) -> dict[int, int]:
    return sde.get_jump_distances(
        system_id,
        max_jumps,
    )

def get_route(
    origin_system_id: int,
    destination_system_id: int,
    mode: str = "shortest",
    avoided_system_ids: set[int] | None = None,
) -> list[dict] | None:
    return sde.get_route(
        origin_system_id,
        destination_system_id,
        mode,
        avoided_system_ids,
    )
