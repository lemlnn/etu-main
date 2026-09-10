"""small public esi client. raw http and pagination behavior stay here so feature modules do not repeat it"""

import requests

BASE_URL = "https://esi.evetech.net"

HEADERS = {
    "X-Compatibility-Date": "2026-09-10",
    "User-Agent": "ETU/dev-0.1.0"
}

def get(path: str, params: dict | None = None) -> dict | list:
    response = requests.get(
        f"{BASE_URL}{path}",
        headers=HEADERS,
        params=params,
        timeout=10
    )

    response.raise_for_status()
    return response.json()

def get_pages(path: str, params: dict | None = None) -> list:
    first_params = dict(params or {})
    first_params["page"] = 1

    response = requests.get(
        f"{BASE_URL}{path}",
        headers=HEADERS,
        params=first_params,
        timeout=10
    )

    response.raise_for_status()

    records = response.json()

    # some esi routes spread results across pages, so the first response is used to find the total
    total_pages = int(response.headers.get("X-Pages", 1))

    for page in range(2, total_pages + 1):
        page_params = dict(params or {})
        page_params["page"] = page

        response = requests.get(
            f"{BASE_URL}{path}",
            headers=HEADERS,
            params=page_params,
            timeout=10
        )

        response.raise_for_status()
        records.extend(response.json())

    return records

def post(path: str, json_data) -> dict | list:
    response = requests.post(
        f"{BASE_URL}{path}",
        headers=HEADERS,
        json=json_data,
        timeout=10
    )

    response.raise_for_status()
    return response.json()