import re

from etu import esi


def clean_description(description: str) -> str: 
    description = description.replace("<br>", "\n")
    return re.sub(r"<[^>]+>", "", description)

def get_type(type_id: int) -> dict:
    data = esi.get(f"/universe/types/{type_id}/")

    if "description" in data:
        data["description"] = clean_description(data["description"])

    return data

def get_group(group_id: int) -> dict:
    data = esi.get(f"/universe/groups/{group_id}/")

    return data

def get_category(category_id: int) -> dict:
    data = esi.get(f"/universe/categories/{category_id}/")

    return data

def find_type(name: str) -> list[dict]:
    data = esi.post(
        "/universe/ids/",
        [name]
    )

    return data.get("inventory_types", [])
