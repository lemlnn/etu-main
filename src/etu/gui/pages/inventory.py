"""inventory gui using the existing local sde backend"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from etu import sde
from etu.inventory import (
    find_type,
    find_type_fuzzy,
    get_type,
)
from etu.gui.pages.base import BasePage
from etu.gui.theme import UNIT
from etu.gui.widgets import (
    CutButton,
    DetailRow,
    PhotonPanel,
    PhotonToolStrip,
    panel_splitter,
)


class InventoryPage(BasePage):
    def __init__(self):
        super().__init__(
            "Inventory",
        )

        search_panel = PhotonToolStrip()

        search_row = QHBoxLayout()
        search_row.setSpacing(UNIT)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search item name or enter a type ID"
        )
        self.search_input.setAccessibleName(
            "Item name or type ID"
        )

        self.search_button = CutButton("SEARCH")
        self.search_button.setAccessibleName(
            "Search inventory"
        )

        search_row.addWidget(
            self.search_input,
            1,
        )
        search_row.addWidget(
            self.search_button,
        )

        search_panel.body_layout.addLayout(
            search_row
        )

        self.root_layout.addWidget(
            search_panel
        )

        results_panel = PhotonPanel(
            "RESULTS",
        )
        results_panel.setMinimumWidth(
            UNIT * 20
        )

        self.results = QListWidget()
        self.results.setAccessibleName("Inventory search results")
        self.results.setAlternatingRowColors(True)
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
            "ITEM DATA",
        )
        detail_panel.setMinimumWidth(
            UNIT * 32
        )

        details = QWidget()
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        details_layout.setSpacing(UNIT)

        self.detail_rows = {
            "name": DetailRow("Name"),
            "type_id": DetailRow("Type ID"),
            "group": DetailRow("Group"),
            "category": DetailRow("Category"),
            "volume": DetailRow("Volume"),
            "packaged_volume": DetailRow(
                "Packaged Volume"
            ),
            "published": DetailRow("Published"),
        }

        for row in self.detail_rows.values():
            details_layout.addWidget(row)

        description_label = QLabel("DESCRIPTION")
        description_label.setObjectName("SectionLabel")

        self.description = QTextBrowser()
        self.description.setAccessibleName("Item description")
        self.description.setPlaceholderText(
            "Select an item to inspect it"
        )

        details_layout.addSpacing(UNIT)
        details_layout.addWidget(
            description_label
        )
        details_layout.addWidget(
            self.description,
            1,
        )

        detail_panel.body_layout.addWidget(
            details
        )

        splitter = panel_splitter(
            results_panel,
            detail_panel,
            sizes=[
                UNIT * 40,
                UNIT * 88,
            ],
        )
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)

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
        self.results.currentItemChanged.connect(
            self.show_item
        )

        if not sde.is_ready():
            self.search_input.setEnabled(False)
            self.search_button.setEnabled(False)
            self.results.addItem(
                "SDE database is not ready"
            )

    def search(self):
        query = self.search_input.text().strip()

        if not query:
            return

        self.results.clear()

        if query.isdigit():
            data = get_type(int(query))

            if data is not None:
                self._add_result(data)

            return

        exact = find_type(query)
        fuzzy = find_type_fuzzy(query)

        merged = {}
        for result in exact + fuzzy:
            merged[result["type_id"]] = result

        for result in list(merged.values())[:50]:
            self._add_result(result)

    def _add_result(self, result):
        item = QListWidgetItem(
            result["name"]
        )
        item.setData(
            Qt.ItemDataRole.UserRole,
            result["type_id"],
        )
        item.setToolTip(
            f"{result['name']}\n"
            f"Type ID {result['type_id']}"
        )

        self.results.addItem(item)

    def show_item(
        self,
        current,
        previous,
    ):
        if current is None:
            return

        type_id = current.data(
            Qt.ItemDataRole.UserRole
        )

        if type_id is None:
            return

        data = get_type(type_id)

        if data is None:
            return

        self.detail_rows["name"].set_value(
            data.get("name", "-")
        )
        self.detail_rows["type_id"].set_value(
            data.get("type_id", "-")
        )
        self.detail_rows["group"].set_value(
            f"{data.get('group_name', '-')} "
            f"[{data.get('group_id', '-')}]"
        )
        self.detail_rows["category"].set_value(
            f"{data.get('category_name', '-')} "
            f"[{data.get('category_id', '-')}]"
        )

        volume = data.get("volume")
        packaged = data.get(
            "packaged_volume"
        )

        self.detail_rows["volume"].set_value(
            f"{volume:,.2f} m³"
            if volume is not None
            else "-"
        )
        self.detail_rows[
            "packaged_volume"
        ].set_value(
            f"{packaged:,.2f} m³"
            if packaged is not None
            else "-"
        )
        self.detail_rows[
            "published"
        ].set_value(
            "YES"
            if data.get("published")
            else "NO"
        )

        self.description.setPlainText(
            data.get("description") or ""
        )
