"""navigation page backed by the local static stargate graph"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidgetItem,
)

from etu import sde
from etu.gui.pages.base import BasePage
from etu.gui.search import (
    KeywordSuggestions,
    resolve_system,
    search_systems,
)
from etu.gui.theme import UNIT
from etu.gui.widgets import (
    CutButton,
    DetailRow,
    PhotonPanel,
    PhotonToolStrip,
    StatusLabel,
    WeightedTableWidget,
)
from etu.universe import get_route


ROUTE_MODES = {
    "SHORTEST": "shortest",
    "SAFER": "safer",
    "LESS SECURE": "less_secure",
    "HIGHSEC ONLY": "highsec",
}


def _security_summary(route):
    summary = {
        "highsec": 0,
        "lowsec": 0,
        "nullsec": 0,
    }

    for system in route:
        security = system["security_status"]

        if security >= 0.45:
            summary["highsec"] += 1

        elif security > 0.0:
            summary["lowsec"] += 1

        else:
            summary["nullsec"] += 1

    return summary


class NavigationPage(BasePage):
    def __init__(self):
        super().__init__(
            "Navigation",
        )

        planner = PhotonToolStrip()

        grid = QGridLayout()
        grid.setHorizontalSpacing(UNIT)
        grid.setVerticalSpacing(UNIT)

        self.origin = QLineEdit()
        self.origin.setPlaceholderText(
            "Origin"
        )
        self.origin.setAccessibleName("Origin system")

        self.destination = QLineEdit()
        self.destination.setPlaceholderText(
            "Destination"
        )
        self.destination.setAccessibleName(
            "Destination system"
        )

        self.preference = QComboBox()
        for label, mode in ROUTE_MODES.items():
            self.preference.addItem(
                label,
                mode,
            )

        self.plan_button = CutButton("PLAN")
        self.plan_button.setAccessibleName(
            "Plan route"
        )

        self.origin_suggestions = KeywordSuggestions(
            self.origin,
            search_systems,
            accessible_name="Origin system suggestions",
        )
        self.destination_suggestions = KeywordSuggestions(
            self.destination,
            search_systems,
            accessible_name="Destination system suggestions",
        )

        grid.addWidget(
            self.origin,
            0,
            0,
        )
        grid.addWidget(
            self.destination,
            0,
            1,
        )
        grid.addWidget(
            self.preference,
            0,
            2,
        )
        grid.addWidget(
            self.plan_button,
            0,
            3,
        )

        self.status = StatusLabel()
        grid.addWidget(
            self.status,
            1,
            0,
            1,
            4,
        )

        planner.body_layout.addLayout(
            grid
        )

        self.summary_panel = PhotonPanel(
            "ROUTE STATUS",
        )

        summary_row = QHBoxLayout()
        summary_row.setSpacing(UNIT * 2)

        self.summary_rows = {
            "jumps": DetailRow("Jumps"),
            "highsec": DetailRow("Highsec"),
            "lowsec": DetailRow("Lowsec"),
            "nullsec": DetailRow("Nullsec"),
        }

        for row in self.summary_rows.values():
            summary_row.addWidget(row)

        self.summary_panel.body_layout.addLayout(
            summary_row
        )

        route_panel = PhotonPanel(
            "ROUTE",
        )

        self.route_table = WeightedTableWidget(
            0,
            4,
            weights=[
                12,
                34,
                18,
                36,
            ],
            minimum_widths=[
                UNIT * 8,
                UNIT * 16,
                UNIT * 11,
                UNIT * 16,
            ],
        )
        self.route_table.setAccessibleName("Route systems")
        self.route_table.setHorizontalHeaderLabels([
            "JUMP",
            "SYSTEM",
            "SECURITY",
            "REGION",
        ])
        self.route_table.verticalHeader().setVisible(
            False
        )
        self.route_table.setAlternatingRowColors(
            True
        )

        route_panel.body_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        route_panel.body_layout.addWidget(
            self.route_table
        )

        self.root_layout.addWidget(
            planner
        )
        self.root_layout.addWidget(
            self.summary_panel
        )
        self.root_layout.addWidget(
            route_panel,
            1,
        )

        self.plan_button.clicked.connect(
            self.plan_route
        )
        self.origin.returnPressed.connect(
            self.plan_route
        )
        self.destination.returnPressed.connect(
            self.plan_route
        )

        if not sde.is_ready():
            self.origin.setEnabled(False)
            self.destination.setEnabled(False)
            self.preference.setEnabled(False)
            self.plan_button.setEnabled(False)
            self.status.set_status(
                "SDE database is not ready",
                "error",
            )

    def set_origin_system(self, system_name):
        self.origin.setText(str(system_name))
        self.origin.setFocus()

    def set_destination_system(self, system_name):
        self.destination.setText(str(system_name))
        self.destination.setFocus()

    def plan_route(self):
        origin_query = self.origin.text().strip()
        destination_query = self.destination.text().strip()

        if not origin_query or not destination_query:
            self.status.set_status(
                "Origin and destination are required",
                "warning",
            )
            return

        origin = resolve_system(origin_query)

        if origin is None:
            self.status.set_status(
                f'No system found matching "{origin_query}"',
                "warning",
            )
            return

        destination = resolve_system(
            destination_query
        )

        if destination is None:
            self.status.set_status(
                f'No system found matching "{destination_query}"',
                "warning",
            )
            return

        mode = self.preference.currentData()

        self.status.set_status(
            "Calculating route"
        )

        route = get_route(
            origin["system_id"],
            destination["system_id"],
            mode,
        )

        if route is None:
            label = self.preference.currentText().lower()
            self.route_table.setRowCount(0)
            self._clear_summary()
            self.status.set_status(
                f"No {label} static stargate route found from "
                f"{origin['name']} to {destination['name']}",
                "warning",
            )
            return

        self._populate_route(route)
        self._update_summary(route)

        self.status.set_status(
            f"{origin['name']} → {destination['name']}     "
            f"{len(route) - 1} jumps     "
            f"{self.preference.currentText()}",
            "success",
        )

    def _clear_summary(self):
        for row in self.summary_rows.values():
            row.set_value("-")

    def _update_summary(self, route):
        security = _security_summary(route)

        self.summary_rows["jumps"].set_value(
            len(route) - 1
        )
        self.summary_rows["highsec"].set_value(
            security["highsec"]
        )
        self.summary_rows["lowsec"].set_value(
            security["lowsec"]
        )
        self.summary_rows["nullsec"].set_value(
            security["nullsec"]
        )

    def _populate_route(self, route):
        self.route_table.setRowCount(
            len(route)
        )

        for row_index, system in enumerate(route):
            jump = QTableWidgetItem(
                str(row_index)
            )
            jump.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            name = QTableWidgetItem(
                system["name"]
            )

            security = QTableWidgetItem(
                f"{system['security_status']:.1f}"
            )
            security.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            region = QTableWidgetItem(
                system["region_name"]
            )

            self.route_table.setItem(
                row_index,
                0,
                jump,
            )
            self.route_table.setItem(
                row_index,
                1,
                name,
            )
            self.route_table.setItem(
                row_index,
                2,
                security,
            )
            self.route_table.setItem(
                row_index,
                3,
                region,
            )
