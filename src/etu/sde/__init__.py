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
    find_types_fuzzy,
    get_category,
    get_group,
    get_type,
)
from etu.sde.universe import (
    find_regions,
    find_regions_fuzzy,
    find_systems,
    find_systems_fuzzy,
    get_jump_distances,
    get_region,
    get_route,
    get_system,
    get_system_connections,
)
from etu.sde.updater import (
    LATEST_SDE_URL,
    REQUIRED_SDE_FILES,
    SDE_DOWNLOAD_URL,
    get_latest_sde_build,
    update_sde,
)
