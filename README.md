# etu-main

A helper utility for EVE Online.

## Internal project layout

```text
etu/
├── README.md
├── LICENSE
├── pyproject.toml
├── src/
│   └── etu/
│       ├── __init__.py   # Blank for now
│       ├── __main__.py   # Temporary frontend for testing before the TUI
│       ├── esi.py        # Handles requests to EVE ESI
│       └── inventory.py  # Converts/raw ESI inventory data into ETU objects
└── tests/                # Component and integration tests
