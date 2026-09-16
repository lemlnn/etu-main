# ETU - EVE Tracking Utility

ETU is an in-development helper utility for **EVE Online** built around CCP's ESI API and the EVE Static Data Export (SDE).

The project currently focuses on fast local lookups, market tools, universe data, and route planning from a terminal interface. The long-term goal is to grow ETU into a broader EVE companion application while keeping the underlying data and feature layers reusable outside the CLI.

> ETU is still in active development. Features, commands, file layout, and behavior may change between development versions.

## Interfaces

### Desktop GUI

ETU now includes a functional Qt desktop interface with pages for:

- Inventory
- Universe
- Market
- Navigation
- Settings / SDE maintenance

The GUI is built with **PySide6 / Qt 6 Widgets** and uses a Photon-inspired interface

Launch it directly with:

```bash
python -m etu.gui
```

Or launch ETU normally and choose:

```text
[G] Launch GUI
```

### Terminal Interface

The original CLI remains available and uses the same ETU service and data modules.

Some advanced navigation controls, including ordered waypoints and avoided systems, are currently exposed through the CLI while the GUI continues to be worked on.

## Current Features

### Inventory

- search inventory types by ID or name
- fuzzy name matching for misspelled item names
- view type, group, and category IDs
- view volume, publication state, and cleaned item descriptions
- local lookups through the imported SDE database

### Universe

- search solar systems by ID or name
- fuzzy and prefix-aware system search, including J-space names
- view security status, constellation, and region information
- view static stargate connections
- search regions by ID or name

### Market

- retrieve paginated regional market orders through ESI
- view market orders by region or filter them to a selected system
- sort sell orders from lowest to highest price
- sort buy orders from highest to lowest price
- view best buy and best sell prices
- resolve public NPC station IDs to readable station names
- identify unresolved player-owned structures until authenticated structure lookup is added
- find buy orders that can reach a selected system based on order range and stargate distance
- view regional market history and recent market statistics

### Navigation

- plan routes through the static stargate network
- shortest-route planning
- safer routing
- less-secure routing
- highsec-only routing
- ordered waypoints
- avoided systems
- route security summaries
- region transition markers
- fuzzy system lookup for origins, destinations, waypoints, and avoided systems

Navigation uses the static stargate network from the SDE. Dynamic wormhole connections are not included.

### Data

- check the installed SDE build
- download newer SDE builds from CCP
- extract only the data ETU currently needs
- import static data into a local SQLite database
- keep SDE download and extraction files temporary during updates

## Requirements

- Python 3.11 or newer
- `requests`
- `rapidfuzz`
- `PySide6`

The Python dependencies are installed automatically through `pyproject.toml`.

## Installation

Clone the repository:

```bash
git clone https://github.com/lemlnn/etu-main.git
cd etu-main
```

Install ETU in editable mode:

```bash
python -m pip install -e .
```

Then run:

```bash
etu
```

Editable installation is currently the recommended setup while ETU is under active development.

## First-Time Setup

ETU needs its local SDE database before inventory, universe, navigation, and other static-data-backed features can work.

Start ETU:

```bash
etu
```

Then open:

```text
Data

[1] Check/update SDE
```

ETU will check the latest SDE build, download it if needed, import the required data, and create the local SQLite database.

## Main Menu

The current terminal interface is organized around the main feature areas:

```text
ETU dev-...

[1] Inventory
[2] Universe
[3] Market
[4] Navigation
[5] Data
[G] Launch GUI
[Q] Quit
```

## Project Layout

The current tracked source layout is:

```text
etu-main/
├── src/
│   └── etu/
│       ├── __init__.py
│       ├── __main__.py             # package entry point
│       │
│       ├── cli/                    # terminal interface and user input flow
│       │   ├── __init__.py
│       │   ├── common.py           # shared cli helpers
│       │   ├── data.py             # sde update menu and error handling
│       │   ├── inventory.py        # inventory search and selection ui
│       │   ├── main.py             # top-level etu menu
│       │   ├── market.py           # market ui and formatting
│       │   ├── navigation.py       # route planning ui
│       │   ├── regions.py          # region search and selection ui
│       │   ├── search.py           # shared search ranking helpers
│       │   ├── systems.py          # solar-system search and selection ui
│       │   └── universe.py         # universe submenu
│       │
│       ├── gui/
│       │   ├── __init__.py         # package marker for etu's graphical interface
│       │   ├── __main__.py         # entry point for python -m etu.gui
│       │   ├── app.py              # creates and configures qapplication
│       │   ├── search.py           # takes fuzzy search from the cli functions
│       │   ├── theme.py            # gui palette, spacing, etc
│       │   ├── widgets.py          # contains the responsive parts of the application
│       │   ├── window.py           # main desktop shell
│       │   └── pages/
│       │       ├── __init__.py     # package marker for the GUI page modules
│       │       ├── base.py         # provides the standard page layout and shared task handling
│       │       ├── inventory.py    # renders inventory tab, functionality pulled from cli
│       │       ├── market.py       # renders market tab, functionality pulled from cli
│       │       ├── navigation.py   # renders nav tab, functionality pulled from cli
│       │       ├── settings.py     # renders settings, functionality pulled from cli
│       │       └── universe.py     # renders universe tab, functionality pulled from cli
│       │
│       ├── sde/                    # static-data database layer
│       │   ├── __init__.py         # public sde interface
│       │   ├── database.py         # sqlite paths, schema, and metadata
│       │   ├── importer.py         # jsonl import logic
│       │   ├── inventory.py        # inventory queries and fuzzy search
│       │   ├── universe.py         # universe queries, stargates, and routing
│       │   └── updater.py          # sde download and update logic
│       │
│       ├── esi.py                  # public esi request and pagination helpers
│       ├── inventory.py            # inventory service layer
│       ├── market.py               # market data and market-range logic
│       └── universe.py             # universe and navigation service layer
│
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
```

## Runtime Data

ETU creates local runtime data outside the tracked source tree:

```text
etu-main/
└── data/
    └── etu.db
```

`etu.db` is the generated SQLite database containing the imported static data and ETU metadata.

SDE archives and extracted JSONL files are handled in temporary directories during updates rather than being kept permanently in the repository.

## Architecture

ETU keeps static and live data separate:

```text
EVE Static Data Export
        ↓
temporary extraction
        ↓
SQLite database
        ↓
inventory / universe / navigation

CCP ESI
   ↓
esi.py
   ↓
market and other live-data features
```

Static or slow-changing data is kept locally so common searches do not require repeated network requests. Live information, such as market orders and history, is retrieved through ESI.

The CLI is kept separate from the underlying feature modules so the same backend logic can later be reused by other interfaces.

## Current Limitations

ETU does not currently include EVE SSO authentication.

Because of that:

- player-owned structure names may remain unresolved
- authenticated character and corporation data is not available yet
- structure-specific authenticated market data is not available
- navigation only knows static stargates and cannot track live wormhole connections

These are planned areas for later development.

## Planned Direction

Some of the larger areas planned for ETU include:

- EVE SSO authentication
- character and account-aware features
- assets and container handling
- skill and skill-queue tracking
- wallet, industry, contracts, fittings, and other private ESI data
- improved caching and persistence
- expanded market analysis

## License

ETU is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

EVE Online and related names and assets belong to CCP Games. ETU is an unofficial community project and is not affiliated with or endorsed by CCP Games.

Font is from Google Fonts, Jura

## Extras

- READMEs are really annoying to make
- Good GUI is so damn hard
