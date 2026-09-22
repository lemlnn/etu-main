"""Runtime filesystem locations that do not depend on the source checkout."""

import json
import os
from importlib.metadata import distributions
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname


def get_data_dir() -> Path:
    """Return ETU's writable per-user data directory."""
    override = os.environ.get("ETU_DATA_DIR")

    if override:
        return Path(override).expanduser().resolve()

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        root = (
            Path(base)
            if base
            else Path.home() / "AppData" / "Local"
        )
        return root / "ETU"

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "ETU"
        )

    base = os.environ.get("XDG_DATA_HOME")
    root = (
        Path(base).expanduser()
        if base
        else Path.home() / ".local" / "share"
    )
    return root / "etu"


def get_editable_project_root() -> Path | None:
    """Return the project root for an editable ETU install, when available."""
    for dist in distributions(name="etu"):
        direct_url_text = dist.read_text("direct_url.json")

        if not direct_url_text:
            continue

        try:
            direct_url = json.loads(direct_url_text)
        except (TypeError, ValueError):
            continue

        if not direct_url.get("dir_info", {}).get("editable"):
            continue

        parsed = urlsplit(str(direct_url.get("url", "")))

        if parsed.scheme != "file":
            continue

        path_text = url2pathname(unquote(parsed.path))

        if parsed.netloc:
            path_text = f"//{parsed.netloc}{path_text}"

        project_root = Path(path_text).resolve()

        if project_root.is_dir():
            return project_root

    return None


def get_legacy_data_dir() -> Path | None:
    """Return ETU's former source-tree data directory for one-time migration."""
    override = os.environ.get("ETU_LEGACY_DATA_DIR")

    if override:
        return Path(override).expanduser().resolve()

    project_root = get_editable_project_root()

    if project_root is None:
        return None

    legacy_data = project_root / "data"

    if legacy_data.resolve() == get_data_dir().resolve():
        return None

    return legacy_data
