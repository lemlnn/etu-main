"""public surface for the sde package. it re-exports the useful pieces so the rest of etu does not care how this folder is split"""

from etu.sde.database import (
    DATA_DIR,
    DB_PATH,
    PROJECT_ROOT,
    SDE_DIR,
    SDE_SCHEMA_VERSION,
    connect,
    create_database,
    get_sde_build,
    get_sde_schema_version,
    is_ready,
    needs_sde_refresh,
)
from etu.sde.importer import import_sde
from etu.sde.dogma import (
    get_direct_skill_requirements,
    get_skill_requirement_tree,
    get_type_blueprints,
    get_type_dogma_attributes,
    get_type_dogma_effects,
    get_type_materials,
    get_type_used_with,
    get_type_variations,
)
from etu.sde.inventory import (
    find_types,
    clear_inventory_search_cache,
    find_types_keywords,
    get_category,
    get_group,
    get_type_categories,
    get_type,
    warm_type_search_index,
)
from etu.sde.universe import (
    clear_universe_search_cache,
    find_regions,
    find_regions_keywords,
    find_systems,
    find_systems_keywords,
    get_jump_distances,
    get_region,
    get_route,
    get_system,
    get_system_connections,
    warm_universe_search_indexes,
)
from etu.sde.updater import (
    LATEST_SDE_URL,
    REQUIRED_SDE_FILES,
    SDE_DOWNLOAD_URL,
    get_latest_sde_build,
    update_sde,
)


def warm_search_indexes():
    """Warm the default GUI search indexes without building unpublished inventory."""
    if not is_ready():
        return

    warm_type_search_index(True)
    warm_universe_search_indexes()


def clear_search_caches():
    clear_inventory_search_cache()
    clear_universe_search_cache()
