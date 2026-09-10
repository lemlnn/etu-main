etu-main

A helper utility for EVE Online.

Internal project layout

```
etu-main/
├── data/
│   ├── etu.db                  # Generated local SQLite database
│   └── sde/                    # Extracted EVE Static Data Export files
│       ├── categories.jsonl
│       ├── groups.jsonl
│       ├── mapConstellations.jsonl
│       ├── mapRegions.jsonl
│       ├── mapSolarSystems.jsonl
│       ├── mapStargates.jsonl
│       └── types.jsonl
├── src/
│   └── etu/
│       ├── __init__.py         # Package initializer
│       ├── __main__.py         # Current CLI frontend
│       ├── esi.py              # Handles requests to EVE ESI
│       ├── inventory.py        # Inventory/type logic used by ETU
│       ├── market.py           # Market order logic used by ETU
│       ├── sde.py              # Imports, stores, and queries static EVE data
│       └── universe.py         # System and region logic used by ETU
├── .gitignore                  # Files/directories Git should ignore
├── LICENSE
├── pyproject.toml              # Package metadata, dependencies, and entry point
└── README.md