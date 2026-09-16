"""inventory service layer between the cli and sde. it also cleans ccp item descriptions before displaying them"""

import re

from etu import sde


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

def find_type(name: str) -> list[dict]:
    return sde.find_types(name)

def find_type_fuzzy(name: str) -> list[dict]:
    return sde.find_types_fuzzy(name)


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
