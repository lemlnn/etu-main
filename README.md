# ETU - EVE Tracking Utility

ETU is an in-development companion utility for **EVE Online** built around CCP's ESI API and the EVE Static Data Export (SDE).

The project provides both a Qt desktop GUI and terminal interface over shared data and service layers. It currently focuses on fast local SDE lookups, dogma inspection, public market tools, universe data, and static route planning while keeping the underlying feature code reusable across interfaces.

> ETU is still in active development. Features, commands, file layout, and behavior may change between development versions.

## Interfaces

### Desktop GUI

ETU now includes a functional Qt desktop interface with pages for:

- Inventory
- Universe
- Market
- Navigation
- Settings / SDE maintenance

The GUI is built with **PySide6 / Qt 6 Widgets** and uses a Photon-inspired interface.

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

- search inventory types by ID or name with debounced live results and match counts
- use deterministic keyword matching backed by reusable in-memory trie indexes
- filter results by player-facing SDE item category
- configure published-only filtering, result limits, or show-all results from Settings
- view type, group, category, volume, publication state, and descriptions
- identify Tech II, Tech III, faction, deadspace, officer, storyline, abyssal, limited-time, premium, and structure meta groups using EVE's native item tags
- inspect published dogma attributes with readable values and EVE icons
- resolve dogma booleans, type/group references, rig sizes, training attributes, time values, d-scan range, and other special units into readable values
- calculate displayed ship warp speed from the ship's base speed, multiplier, and applicable role bonus
- view fitting requirements including CPU, powergrid, rig size, calibration, slot type, and hardpoint requirements
- collapse long ship fitting-restriction lists into ship-class and ship-type groups
- view recursive skill requirements and required skill levels
- browse compatible charges from modules and reverse "used with" relationships from ammo, crystals, scripts, probes, paste, and other charge-category items
- browse item variations grouped by meta classification
- view manufacturing blueprints and reprocessing materials
- local lookups through the imported SDE database

### Universe

- search solar systems, constellations, and regions by ID or name from one live browser
- filter Universe results by object type and security-space classification
- reuse in-memory trie indexes for deterministic keyword and substring-friendly lookups, including J-space names
- inspect structured system, constellation, and region overviews without repeated graph scans
- browse static system connections, constellation membership, region systems, and cross-border stargate links
- jump between related Universe objects directly from detail views
- send an inspected solar system to Navigation as the route origin or destination
- cache static Universe detail aggregates and invalidate them when the local SDE changes

### Market

- inline debounced keyword suggestions for item and system/region searches
- filter item searches with the same player-facing SDE category list used by Inventory
- retrieve paginated regional market orders through ESI
- view market orders by region or filter them to a selected system
- use CCP's global PLEX market automatically when PLEX is selected; GLOBAL scope is hidden for normal items
- display sell and buy orders simultaneously in separate, vertically resizable panes
- sort sell orders from lowest to highest price and buy orders from highest to lowest price
- use model-backed order tables so very large order books do not create thousands of individual table widgets
- resolve public NPC station IDs to readable station names
- identify unresolved player-owned structures until authenticated structure lookup is added
- find buy orders that can reach a selected system based on order range and static stargate distance
- hide Reachable Buy Orders unless a loaded SYSTEM-scope query can use it
- view market history as either a table or interactive graph
- graph daily average price, low/high price range, and traded volume with exact hover details
- cache static graph rendering and reduce repaint work during hover and window resizing

### Navigation

- inline debounced keyword suggestions for origin and destination systems
- plan routes through the static stargate network
- shortest-route planning
- safer routing
- less-secure routing
- highsec-only routing
- ordered waypoints
- avoided systems
- route security summaries
- region transition markers
- keyword system lookup for origins, destinations, waypoints, and avoided systems

Navigation uses the static stargate network from the SDE. Dynamic wormhole connections are not included.

### Settings

- manage the local SDE database and refresh state
- configure Inventory to show published items only or include unpublished/internal SDE entries
- choose between showing all Inventory search matches or limiting the displayed result count
- keep GUI search preferences persistent through Qt settings

### Data

- check the installed SDE build
- download newer SDE builds from CCP
- extract only the data ETU currently needs
- import inventory, universe, dogma, material, and blueprint data into SQLite
- track ETU's local SDE schema independently from the CCP SDE build
- detect when an existing database requires a structural refresh
- keep SDE download and extraction files temporary during updates

## Requirements

- Python 3.11 or newer
- `requests`
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
│       │   ├── systems.py          # solar-system search and selection ui
│       │   └── universe.py         # universe submenu
│       │
│       ├── gui/
│       │   ├── __init__.py         # package marker for etu's graphical interface
│       │   ├── __main__.py         # entry point for python -m etu.gui
│       │   ├── app.py              # creates and configures qapplication
│       │   ├── dogma.py            # dogma formatting and icon presentation
│       │   ├── meta.py             # meta-group tags and list delegate
│       │   ├── preferences.py      # persistent GUI preference keys and defaults
│       │   ├── search.py           # keyword lookup, category filters, and live suggestions
│       │   ├── theme.py            # gui palette, spacing, etc
│       │   ├── widgets.py          # contains the responsive parts of the application
│       │   ├── window.py           # main desktop shell
│       │   ├── assets/
│       │   │   ├── dogma/          # EVE dogma attribute/effect icons
│       │   │   └── meta/           # EVE item meta-group tags
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
│       │   ├── dogma.py            # dogma, materials, blueprints, and compatibility queries
│       │   ├── importer.py         # jsonl import logic
│       │   ├── inventory.py        # inventory queries and category metadata
│       │   ├── search.py           # reusable trie-backed SDE keyword indexes
│       │   ├── universe.py         # universe queries, stargates, and routing
│       │   └── updater.py          # sde download and update logic
│       │
│       ├── esi.py                  # public esi request and pagination helpers
│       ├── inventory.py            # inventory service layer
│       ├── market.py               # market data and market-range logic
│       ├── paths.py                # installation-safe runtime/resource paths
│       ├── search.py               # shared keyword matching helpers
│       ├── universe.py             # universe and navigation service layer
│       └── version.py              # shared package-version helpers
│
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
```

## Runtime Data

ETU stores writable runtime data in the platform's per-user data directory rather than inside the source checkout:

- Linux: `$XDG_DATA_HOME/etu/etu.db`, or `~/.local/share/etu/etu.db` when `XDG_DATA_HOME` is unset
- macOS: `~/Library/Application Support/ETU/etu.db`
- Windows: `%LOCALAPPDATA%\ETU\etu.db`

Set `ETU_DATA_DIR` to override the runtime data directory. Editable installs also recognize the former project-local `data/etu.db` location and migrate a usable legacy database into the per-user location when needed.

`etu.db` is the generated SQLite database containing the imported static data and ETU metadata. SDE archives and extracted JSONL files are handled in temporary directories during updates rather than being kept permanently in the repository.

ETU also tracks its own SDE schema version. After an ETU update adds new static-data requirements, Settings may report `REFRESH REQUIRED` even when the installed CCP SDE build is already current. Refreshing the SDE rebuilds the local database with the additional data.

## Versioning

ETU's development version is declared once in `pyproject.toml` under `[project].version`. The CLI banner, GUI, and ESI `User-Agent` derive their version from the shared package-version helper instead of maintaining separate hardcoded values. Editable installs read the active project's `pyproject.toml`, while normal installs use installed package metadata.

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

Static or slow-changing data is kept locally so common searches do not require repeated network requests. Name searches build reusable in-memory trie indexes from the local SDE and invalidate them when the database changes. GUI live searches are debounced so typing does not repeatedly trigger broad database work.

Live information, such as market orders and history, is retrieved through ESI. Large market order books use model-backed Qt tables, while the history graph caches its static rendering so scrolling, hovering, and window resizing do not unnecessarily rebuild thousands of visual elements.

The CLI is kept separate from the underlying feature modules so the same backend logic can be reused by the desktop interface.

## Current Limitations

ETU does not currently include EVE SSO authentication.

Because of that:

- player-owned structure names may remain unresolved
- authenticated character and corporation data is not available yet
- structure-specific authenticated market data is not available
- navigation only knows static stargates and cannot track live wormhole connections
- ESI only provides ETU's GLOBAL market scope for PLEX; normal items remain system/region scoped rather than being synthesized into an ETU-wide global order book

These are planned areas for later development.

## Planned Direction

Some of the larger areas planned for ETU include:

- EVE SSO authentication
- character and account-aware features
- assets and container handling
- skill and skill-queue tracking
- wallet, industry, contracts, fittings, and other private ESI data
- improved caching and persistence
- expanded market analysis and longer-term market tooling

## License and Third-Party Assets

ETU's original source code is licensed under the Apache License 2.0.
See [LICENSE](LICENSE) for details.

Files under `src/etu/gui/assets/` include artwork and interface assets
from EVE Online that are owned by CCP hf. These assets are not licensed
under the Apache License 2.0 and remain the property of CCP hf. They are
included solely for use with this EVE Online third-party application and
are subject to CCP's applicable developer and content terms.

© 2014 CCP hf. All rights reserved. "EVE", "EVE Online", "CCP", and all
related logos and images are trademarks or registered trademarks of CCP hf.

This material is used with limited permission of CCP Games.
No official affiliation or endorsement by CCP Games is stated or implied.

ETU is an independent, unofficial third-party application.

The Jura typeface is distributed separately under its applicable font license.

## Extras

- READMEs are really annoying to make
- Good GUI is so damn hard
