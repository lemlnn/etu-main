# etu-main

A helper utility for EVE Online.

## Internal project layout

```text
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
│       ├── __main__.py         # CLI entry point
│       ├── cli/                # Terminal interface and user input flow
│       │   ├── __init__.py
│       │   ├── common.py       # Shared CLI helpers
│       │   ├── data.py         # SDE update menu and errors
│       │   ├── inventory.py    # Inventory search and selection UI
│       │   ├── main.py         # Main ETU menu
│       │   ├── market.py       # Market search UI
│       │   ├── regions.py      # Region search and selection UI
│       │   ├── search.py       # Shared search ranking helpers
│       │   ├── systems.py      # Solar-system search and selection UI
│       │   └── universe.py     # Universe menu
│       ├── sde/                # Static data database layer
│       │   ├── __init__.py     # Public SDE interface
│       │   ├── database.py     # SQLite paths, schema, and database state
│       │   ├── importer.py     # JSONL SDE import logic
│       │   ├── inventory.py    # Inventory SDE queries and fuzzy search
│       │   ├── universe.py     # Universe SDE queries and fuzzy search
│       │   └── updater.py      # SDE download and update logic
│       ├── esi.py              # Handles requests to EVE ESI
│       ├── inventory.py        # Inventory/type logic used by ETU
│       ├── market.py           # Market order logic used by ETU
│       └── universe.py         # System and region logic used by ETU
├── .gitignore                  # Files/directories Git should ignore
├── LICENSE
├── pyproject.toml              # Package metadata, dependencies, and entry point
└── README.md
```
