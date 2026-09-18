"""persistent GUI preferences shared by settings and feature pages"""

from dataclasses import dataclass

from PySide6.QtCore import QSettings


INVENTORY_SHOW_ALL_RESULTS = "inventory/show_all_results"
INVENTORY_RESULT_LIMIT = "inventory/result_limit"
INVENTORY_PUBLISHED_ONLY = "inventory/published_only"

DEFAULT_INVENTORY_SHOW_ALL_RESULTS = False
DEFAULT_INVENTORY_RESULT_LIMIT = 50
DEFAULT_INVENTORY_PUBLISHED_ONLY = True

MIN_INVENTORY_RESULT_LIMIT = 1
MAX_INVENTORY_RESULT_LIMIT = 100_000


@dataclass(frozen=True)
class InventorySearchPreferences:
    show_all_results: bool
    result_limit: int
    published_only: bool


def _settings() -> QSettings:
    return QSettings()


def inventory_search_preferences() -> InventorySearchPreferences:
    settings = _settings()
    result_limit = settings.value(
        INVENTORY_RESULT_LIMIT,
        DEFAULT_INVENTORY_RESULT_LIMIT,
        type=int,
    )
    result_limit = max(
        MIN_INVENTORY_RESULT_LIMIT,
        min(MAX_INVENTORY_RESULT_LIMIT, result_limit),
    )

    return InventorySearchPreferences(
        show_all_results=settings.value(
            INVENTORY_SHOW_ALL_RESULTS,
            DEFAULT_INVENTORY_SHOW_ALL_RESULTS,
            type=bool,
        ),
        result_limit=result_limit,
        published_only=settings.value(
            INVENTORY_PUBLISHED_ONLY,
            DEFAULT_INVENTORY_PUBLISHED_ONLY,
            type=bool,
        ),
    )


def set_inventory_show_all_results(enabled: bool):
    _settings().setValue(
        INVENTORY_SHOW_ALL_RESULTS,
        bool(enabled),
    )


def set_inventory_result_limit(limit: int):
    limit = max(
        MIN_INVENTORY_RESULT_LIMIT,
        min(MAX_INVENTORY_RESULT_LIMIT, int(limit)),
    )
    _settings().setValue(
        INVENTORY_RESULT_LIMIT,
        limit,
    )


def set_inventory_published_only(enabled: bool):
    _settings().setValue(
        INVENTORY_PUBLISHED_ONLY,
        bool(enabled),
    )
