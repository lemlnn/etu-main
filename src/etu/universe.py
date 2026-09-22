"""Universe service layer between GUI/CLI callers and the local SDE."""

from copy import deepcopy
from functools import cache

from etu import sde


def _sde_signature() -> tuple[int, int] | None:
    try:
        stat = sde.DB_PATH.stat()
    except OSError:
        return None

    return (
        stat.st_mtime_ns,
        stat.st_size,
    )


@cache
def _get_system_details(
    system_id: int,
    _signature: tuple[int, int] | None,
) -> dict | None:
    data = sde.get_system(system_id)

    if data is None:
        return None

    # Attach static stargate connections so callers get a complete system view.
    data["connections"] = sde.get_system_connections(system_id)
    return data


def get_system(system_id: int) -> dict | None:
    data = _get_system_details(
        system_id,
        _sde_signature(),
    )
    return deepcopy(data) if data is not None else None


def get_constellation(constellation_id: int) -> dict | None:
    return sde.get_constellation(constellation_id)


@cache
def _get_constellation_details(
    constellation_id: int,
    _signature: tuple[int, int] | None,
) -> dict | None:
    data = sde.get_constellation(constellation_id)

    if data is None:
        return None

    data["systems"] = sde.get_constellation_systems(constellation_id)
    data["borders"] = sde.get_constellation_borders(constellation_id)
    return data


def get_constellation_details(constellation_id: int) -> dict | None:
    data = _get_constellation_details(
        constellation_id,
        _sde_signature(),
    )
    return deepcopy(data) if data is not None else None


def get_region(region_id: int) -> dict | None:
    return sde.get_region(region_id)


@cache
def _get_region_details(
    region_id: int,
    _signature: tuple[int, int] | None,
) -> dict | None:
    data = sde.get_region_summary(region_id)

    if data is None:
        return None

    data["constellations"] = sde.get_region_constellations(region_id)
    data["systems"] = sde.get_region_systems(region_id)
    data["borders"] = sde.get_region_borders(region_id)
    return data


def get_region_details(region_id: int) -> dict | None:
    data = _get_region_details(
        region_id,
        _sde_signature(),
    )
    return deepcopy(data) if data is not None else None


def clear_universe_detail_cache():
    """Clear static detail aggregates after an SDE replacement."""
    _get_system_details.cache_clear()
    _get_constellation_details.cache_clear()
    _get_region_details.cache_clear()


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


def find_constellation(name: str) -> list[dict]:
    return sde.find_constellations(name)


def find_constellation_keywords(
    query: str,
    limit: int | None = 25,
) -> list[dict]:
    return sde.find_constellations_keywords(
        query,
        limit=limit,
    )


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


def find_universe_keywords(
    query: str,
    limit: int | None = 25,
    *,
    kind: str | None = None,
    space: str | None = None,
) -> list[dict]:
    return sde.find_universe_keywords(
        query,
        limit=limit,
        kind=kind,
        space=space,
    )


def get_jump_distances(
    system_id: int,
    max_jumps: int = 40,
) -> dict[int, int]:
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
