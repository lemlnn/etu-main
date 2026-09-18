"""inventory service layer between the cli and sde. it also cleans ccp item descriptions before displaying them"""

import re

from etu import sde


# User-facing category filters should represent practical player-owned item
# families rather than every published type category in the SDE.  The SDE
# also marks world objects and legacy/internal-like categories as published
# (for example Celestial and Asteroid), which makes a raw category list noisy.
FILTERABLE_TYPE_CATEGORY_IDS = frozenset({
    4,      # Material
    6,      # Ship
    7,      # Module
    8,      # Charge
    9,      # Blueprint
    16,     # Skill
    17,     # Commodity
    18,     # Drone
    20,     # Implant
    22,     # Deployable
    23,     # Starbase
    30,     # Apparel
    32,     # Subsystem
    34,     # Ancient Relics
    35,     # Decryptors
    39,     # Infrastructure Upgrades
    40,     # Sovereignty Structures
    43,     # Planetary Commodities
    46,     # Orbitals
    63,     # Special Edition Assets
    65,     # Structure
    66,     # Structure Module
    87,     # Fighter
    91,     # SKINs
    2100,   # Expert Systems
    2118,   # Personalization
    2143,   # Colony Resources
})


def clean_description(description: str) -> str:
    description = description.replace("<br>", "\n")
    return re.sub(r"<[^>]+>", "", description)

def get_type(type_id: int) -> dict | None:
    data = sde.get_type(type_id)

    if data is None:
        return None

    if data.get("description"):
        data["description"] = clean_description(data["description"])

    return data

def get_group(group_id: int) -> dict | None:
    return sde.get_group(group_id)

def get_category(category_id: int) -> dict | None:
    return sde.get_category(category_id)

def get_type_categories(
    published_only: bool = True,
) -> list[dict]:
    return sde.get_type_categories(
        published_only=published_only,
    )


def get_filterable_type_categories(
    published_only: bool = True,
) -> list[dict]:
    """Return the practical item categories exposed by GUI search filters."""
    return [
        category
        for category in get_type_categories(
            published_only=published_only,
        )
        if int(category["category_id"])
        in FILTERABLE_TYPE_CATEGORY_IDS
    ]

def find_type(name: str) -> list[dict]:
    return sde.find_types(name)

def find_type_keywords(
    query: str,
    limit: int | None = 50,
    published_only: bool = True,
    category_id: int | None = None,
) -> list[dict]:
    return sde.find_types_keywords(
        query,
        limit=limit,
        published_only=published_only,
        category_id=category_id,
    )


def get_type_dogma(type_id: int) -> dict:
    return {
        "attributes": sde.get_type_dogma_attributes(type_id),
        "effects": sde.get_type_dogma_effects(type_id),
        "requirements": sde.get_skill_requirement_tree(type_id),
        "used_with": sde.get_type_used_with(type_id),
        "variations": sde.get_type_variations(type_id),
        "blueprints": sde.get_type_blueprints(type_id),
        "materials": sde.get_type_materials(type_id),
    }
