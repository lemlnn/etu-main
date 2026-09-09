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
│       └── types.jsonl
├── src/
│   └── etu/
│       ├── __init__.py         # Blank for now
│       ├── __main__.py         # Temporary frontend before the TUI
│       ├── esi.py              # Handles requests to EVE ESI
│       ├── inventory.py        # Inventory/type logic used by ETU
│       ├── sde.py              # Imports, stores, and queries static EVE data
│       └── universe.py         # Systems and constellations logic used by ETU
├── tests/                      # Testing site for ETU components
├── .gitignore                  # Files/directories Git should ignore
├── LICENSE
├── pyproject.toml              # Package metadata, dependencies, and entry point
└── README.md
