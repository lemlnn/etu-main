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

RIG_SIZES = {
    1: "Small",
    2: "Medium",
    3: "Large",
    4: "Capital",
}

REFERENCE_UNITS = {
    "groupid",
    "typeid",
    "attributeid",
}

METERS_PER_AU = 149_597_870_700


FIT_RESTRICTION_FAMILIES = (
    ("canFitShipGroup", "Ship classes"),
    ("canFitShipType", "Ship types"),
)


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



def attribute_display_rows(
    attributes: list[dict],
) -> list[dict]:
    """Build semantic rows for the item attributes view."""

    rows = []
    attribute_values = {
        attribute.get("name"): attribute.get("value", 0)
        for attribute in attributes
    }
    warp_speed_multiplier = attribute_values.get(
        "warpSpeedMultiplier"
    )
    warp_speed_role_bonus = attribute_values.get(
        "shipRoleBonusWarpSpeed",
        0,
    )
    restrictions = {
        label: []
        for _, label in FIT_RESTRICTION_FAMILIES
    }
    restriction_icon = None

    for attribute in attributes:
        if not is_attribute_visible(attribute):
            continue

        name = attribute.get("name", "")
        restriction_label = next(
            (
                label
                for prefix, label
                in FIT_RESTRICTION_FAMILIES
                if name.startswith(prefix)
            ),
            None,
        )

        if restriction_label is not None:
            if restriction_icon is None:
                restriction_icon = attribute.get("icon_id")

            value = format_dogma_value(attribute)
            values = restrictions[restriction_label]

            if value not in values:
                values.append(value)

            continue

        display_attribute = attribute

        if (
            name == "baseWarpSpeed"
            and warp_speed_multiplier is not None
        ):
            display_attribute = dict(attribute)
            display_attribute["value"] = (
                attribute.get("value", 0)
                * warp_speed_multiplier
                * (1 + warp_speed_role_bonus / 100)
            )

        rows.append({
            "kind": "attribute",
            "label": (
                attribute.get("display_name")
                or attribute.get("name")
            ),
            "value": format_dogma_value(
                display_attribute
            ),
            "icon_id": attribute.get("icon_id"),
        })

    if not any(restrictions.values()):
        return rows

    restriction_groups = []
    icon_pending = True

    for label, values in restrictions.items():
        if not values:
            continue

        group_rows = []

        for index, value in enumerate(values):
            group_rows.append({
                "label": "",
                "value": value,
                "icon_id": (
                    restriction_icon
                    if icon_pending and index == 0
                    else None
                ),
            })

        restriction_groups.append({
            "label": label,
            "rows": group_rows,
        })
        icon_pending = False

    rows.append({
        "kind": "section",
        "label": "Can only be fitted to",
        "groups": restriction_groups,
    })

    return rows

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

    if name == "rigSize":
        return RIG_SIZES.get(
            int(round(value)),
            _format_number(value),
        )

    if name == "maxDirectionalScanRange":
        return (
            f"{_format_number(value / METERS_PER_AU)} AU"
        )

    if name == "skillTimeConstant":
        return f"{_format_number(value)}x"

    unit_name = (
        attribute.get("unit_name")
        or ""
    ).casefold()
    unit_display = (
        attribute.get("unit_display_name")
        or ""
    ).strip()

    if unit_name in REFERENCE_UNITS:
        return (
            attribute.get("reference_name")
            or _format_number(value)
        )

    if unit_name == "boolean":
        return "Yes" if value else "No"

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

    if unit_display.casefold() == "sec":
        return f"{formatted}s"

    if unit_display:
        if unit_display == "%":
            return f"{formatted}%"

        return f"{formatted} {unit_display}"

    return formatted


def _format_number(value) -> str:
    value = float(value)

    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}"

    return f"{value:,.2f}".rstrip("0").rstrip(".")
