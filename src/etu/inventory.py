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
