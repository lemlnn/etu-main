"""dogma presentation helpers for inventory item inspection"""

from functools import cache
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap


ASSET_DIR = (
    Path(__file__).resolve().parent
    / "assets"
    / "dogma"
)

REQUIRED_SKILL_ATTRIBUTE_IDS = {
    182,
    183,
    184,
    277,
    278,
    279,
    1285,
    1286,
    1287,
    1288,
    1289,
    1290,
}

FITTING_ATTRIBUTE_NAMES = {
    "cpu",
    "power",
    "upgradeCost",
    "rigSize",
}

FITTING_EFFECTS = {
    "hipower": (
        "High power",
        "Requires a high power slot",
    ),
    "medpower": (
        "Medium power",
        "Requires a medium power slot",
    ),
    "lopower": (
        "Low power",
        "Requires a low power slot",
    ),
    "rigslot": (
        "Rig",
        "Requires a rig slot",
    ),
    "subsystem": (
        "Subsystem",
        "Requires a subsystem slot",
    ),
    "turretfitted": (
        "Turret",
        "Requires a turret hardpoint",
    ),
    "launcherfitted": (
        "Launcher",
        "Requires a launcher hardpoint",
    ),
    "servicefitted": (
        "Service module",
        "Requires a service slot",
    ),
}

CHARGE_SIZES = {
    1: "Small",
    2: "Medium",
    3: "Large",
    4: "X-Large",
}


@cache
def dogma_pixmap(
    icon_id: int | None,
) -> QPixmap:
    if icon_id is None:
        return QPixmap()

    path = ASSET_DIR / f"{icon_id}.png"

    if not path.exists():
        return QPixmap()

    return QPixmap(str(path))


def dogma_icon(
    icon_id: int | None,
) -> QIcon:
    pixmap = dogma_pixmap(icon_id)

    if pixmap.isNull():
        return QIcon()

    return QIcon(pixmap)


def dogma_icon_size() -> QSize:
    return QSize(18, 18)


def is_attribute_visible(
    attribute: dict,
) -> bool:
    if not attribute.get("published"):
        return False

    if not attribute.get("display_name"):
        return False

    if (
        not attribute.get("display_when_zero")
        and abs(attribute.get("value", 0)) < 1e-12
    ):
        return False

    if attribute.get("attribute_id") in (
        REQUIRED_SKILL_ATTRIBUTE_IDS
    ):
        return False

    if attribute.get("name") in (
        FITTING_ATTRIBUTE_NAMES
    ):
        return False

    return True


def fitting_attributes(
    attributes: list[dict],
) -> list[dict]:
    return [
        attribute
        for attribute in attributes
        if attribute.get("name")
        in FITTING_ATTRIBUTE_NAMES
        and (
            attribute.get("display_when_zero")
            or abs(attribute.get("value", 0))
            > 1e-12
        )
    ]


def fitting_effect_rows(
    effects: list[dict],
) -> list[dict]:
    result = []

    for effect in effects:
        definition = FITTING_EFFECTS.get(
            effect.get("name", "").casefold()
        )

        if definition is None:
            continue

        label, value = definition
        result.append({
            "label": label,
            "value": value,
            "icon_id": effect.get("icon_id"),
        })

    return result


def format_dogma_value(
    attribute: dict,
) -> str:
    value = attribute.get("value", 0)
    name = attribute.get("name", "")

    if name == "chargeSize":
        return CHARGE_SIZES.get(
            int(round(value)),
            _format_number(value),
        )

    if name.startswith("chargeGroup"):
        return (
            attribute.get("reference_name")
            or _format_number(value)
        )

    unit_name = (
        attribute.get("unit_name")
        or ""
    ).casefold()
    unit_display = (
        attribute.get("unit_display_name")
        or ""
    ).strip()

    if unit_name == "milliseconds":
        return f"{_format_number(value / 1000)}s"

    if unit_name == "level":
        return f"Level {_format_number(value)}"

    if unit_name in {
        "inverse absolute percent",
        "inversed modifier percent",
    }:
        return f"{_format_number((1 - value) * 100)}%"

    if unit_name == "modifier percent":
        return f"{_format_number((value - 1) * 100)}%"

    if unit_name == "absolute percent":
        return f"{_format_number(value * 100)}%"

    formatted = _format_number(value)

    if unit_display:
        if unit_display == "%":
            return f"{formatted}%"

        return f"{formatted} {unit_display}"

    return formatted


def _format_number(value) -> str:
    value = float(value)

    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}"

    if abs(value) < 1:
        text = f"{value:,.2f}"
    elif abs(value) < 10:
        text = f"{value:,.2f}"
    else:
        text = f"{value:,.2f}"

    return text.rstrip("0").rstrip(".")
