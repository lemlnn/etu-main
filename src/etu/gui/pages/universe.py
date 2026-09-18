"""universe search page backed by the local sde"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTextBrowser,
)

from etu import sde
from etu.gui.pages.base import BasePage
from etu.gui.search import (
    match_count,
    search_regions,
    search_systems,
)
from etu.gui.theme import UNIT
from etu.gui.widgets import (
    CutButton,
    PhotonPanel,
    PhotonToolStrip,
    StatusLabel,
    panel_splitter,
)
from etu.universe import (
    get_region,
    get_system,
)


class UniversePage(BasePage):
    def __init__(self):
        super().__init__(
            "Universe",
        )

        search_panel = PhotonToolStrip()

        row = QHBoxLayout()
        row.setSpacing(UNIT)

        self.kind = QComboBox()
        self.kind.addItem(
            "SOLAR SYSTEM",
            "system",
        )
        self.kind.addItem(
            "REGION",
            "region",
        )
        self.kind.setAccessibleName(
            "Universe search type"
        )

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search New Eden by name or ID"
        )
        self.search_input.setAccessibleName(
            "System or region name or ID"
        )

        self.search_button = CutButton(
            "SEARCH"
        )
        self.search_button.setAccessibleName(
            "Search universe"
        )

        row.addWidget(self.kind)
        row.addWidget(
            self.search_input,
            1,
        )
        row.addWidget(
            self.search_button
        )

        self.status = StatusLabel()

        search_panel.body_layout.addLayout(
            row
        )
        search_panel.body_layout.addWidget(
            self.status
        )

        results_panel = PhotonPanel(
            "RESULTS",
        )

        self.results = QListWidget()
        self.results.setAccessibleName("Universe search results")
        self.results.setAlternatingRowColors(
            True
        )
        self.results.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.results.setTextElideMode(
            Qt.TextElideMode.ElideRight
        )

        results_panel.body_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        results_panel.body_layout.addWidget(
            self.results
        )

        detail_panel = PhotonPanel(
            "UNIVERSE DATA",
        )

        self.details = QTextBrowser()
        self.details.setAccessibleName("Universe details")
        self.details.setPlaceholderText(
            "Select a result to inspect it"
        )

        detail_panel.body_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        detail_panel.body_layout.addWidget(
            self.details
        )

        splitter = panel_splitter(
            results_panel,
            detail_panel,
            sizes=[
                UNIT * 44,
                UNIT * 86,
            ],
        )
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)

        self.root_layout.addWidget(
            search_panel
        )
        self.root_layout.addWidget(
            splitter,
            1,
        )

        self.search_button.clicked.connect(
            self.search
        )
        self.search_input.returnPressed.connect(
            self.search
        )
        self.kind.currentIndexChanged.connect(
            self._kind_changed
        )
        self.results.currentItemChanged.connect(
            self.show_result
        )

        if not sde.is_ready():
            self.search_input.setEnabled(False)
            self.kind.setEnabled(False)
            self.search_button.setEnabled(False)
            self.status.set_status(
                "SDE database is not ready",
                "error",
            )

    def _kind_changed(self):
        self.results.clear()
        self.details.clear()
        self.status.set_status("")

    def search(self):
        query = self.search_input.text().strip()

        if not query:
            self.status.set_status(
                "Enter a system or region name or ID",
                "warning",
            )
            return

        kind = self.kind.currentData()

        if kind == "system":
            matches = search_systems(
                query,
                limit=50,
            )
        else:
            matches = search_regions(
                query,
                limit=50,
            )

        self.results.clear()
        self.details.clear()

        if not matches:
            self.status.set_status(
                f'No {kind} found matching "{query}"',
                "warning",
            )
            return

        for match in matches:
            self._add_result(
                kind,
                match,
            )

        count = match_count(matches)
        self.status.set_status(
            f"{count} match"
            if count == 1
            else f"{count} matches",
            "success",
        )
        self.results.setCurrentRow(0)

    def _add_result(
        self,
        kind,
        match,
    ):
        if kind == "system":
            security = match.get(
                "security_status"
            )
            text = (
                f"{match['name']}  ·  "
                f"{security:.1f}"
                if security is not None
                else match["name"]
            )
            object_id = match["system_id"]

        else:
            text = match["name"]
            object_id = match["region_id"]

        item = QListWidgetItem(text)
        item.setData(
            Qt.ItemDataRole.UserRole,
            (
                kind,
                object_id,
            ),
        )
        item.setToolTip(
            f"{match['name']}\nID {object_id}"
        )
        self.results.addItem(item)

    def show_result(
        self,
        current,
        previous,
    ):
        if current is None:
            return

        payload = current.data(
            Qt.ItemDataRole.UserRole
        )

        if not payload:
            return

        kind, object_id = payload

        if kind == "system":
            self._show_system(object_id)
        else:
            self._show_region(object_id)

    def _show_system(self, system_id):
        system = get_system(system_id)

        if system is None:
            self.details.setPlainText(
                "System data is unavailable"
            )
            return

        security = system.get(
            "security_status"
        )

        lines = [
            f"Name: {system.get('name', '-')}",
            f"System ID: {system.get('system_id', '-')}",
            (
                f"Security: {security:.3f}"
                if security is not None
                else "Security: -"
            ),
            (
                "Constellation: "
                f"{system.get('constellation_name', '-')} "
                f"[{system.get('constellation_id', '-')}]"
            ),
            (
                "Region: "
                f"{system.get('region_name', '-')} "
                f"[{system.get('region_id', '-')}]"
            ),
            f"Security Class: {system.get('security_class') or '-'}",
            f"Faction ID: {system.get('faction_id') or '-'}",
            f"Wormhole Class ID: {system.get('wormhole_class_id') or '-'}",
            "",
            "Connections",
        ]

        connections = system.get(
            "connections",
            [],
        )

        if connections:
            for connection in connections:
                lines.append(
                    f"{connection['name']}  ·  "
                    f"{connection['security_status']:.1f}  ·  "
                    f"{connection['system_id']}"
                )
        else:
            lines.append("No static stargate connections")

        self.details.setPlainText(
            "\n".join(lines)
        )

    def _show_region(self, region_id):
        region = get_region(region_id)

        if region is None:
            self.details.setPlainText(
                "Region data is unavailable"
            )
            return

        lines = [
            f"Name: {region.get('name', '-')}",
            f"Region ID: {region.get('region_id', '-')}",
            f"Faction ID: {region.get('faction_id') or '-'}",
            f"Wormhole Class ID: {region.get('wormhole_class_id') or '-'}",
        ]

        self.details.setPlainText(
            "\n".join(lines)
        )
