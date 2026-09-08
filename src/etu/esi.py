import requests

BASE_URL = "https://esi.evetech.net"

HEADERS = {
    "X-Compatibility-Date": "2026-09-08",
    "User-Agent": "ETU/0.0.1"
}


def get(path: str, params: dict | None = None) -> dict:
    response = requests.get(
        f"{BASE_URL}{path}",
        headers=HEADERS,
        params=params,
        timeout=10
    )

    response.raise_for_status()
    return response.json()


def post(path: str, json_data) -> dict:
    response = requests.post(
        f"{BASE_URL}{path}",
        headers=HEADERS,
        json=json_data,
        timeout=10
    )

    response.raise_for_status()
    return response.json()