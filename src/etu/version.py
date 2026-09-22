"""ETU package-version helpers used by GUI, CLI, and HTTP clients."""

from functools import cache
from importlib.metadata import distributions
import tomllib

from etu.paths import get_editable_project_root


@cache
def get_version() -> str:
    """Return ETU's version from editable source or installed metadata."""
    project_root = get_editable_project_root()

    if project_root is not None:
        pyproject = project_root / "pyproject.toml"

        try:
            with pyproject.open("rb") as file:
                project = tomllib.load(file).get("project", {})

            if project.get("name") == "etu":
                source_version = project.get("version")

                if source_version:
                    return str(source_version)

        except (OSError, tomllib.TOMLDecodeError):
            pass

    candidates = list(distributions(name="etu"))

    if not candidates:
        return "dev"

    return candidates[0].version


def get_development_version() -> str:
    """Return the version label used by ETU development builds."""
    package_version = get_version()
    return (
        "dev"
        if package_version == "dev"
        else f"dev-{package_version}"
    )
