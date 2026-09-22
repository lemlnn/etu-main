"""Interactive universe browser backed by the local SDE."""

from PySide6.QtCore import QEvent, QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from etu import sde
from etu.gui.pages.base import BasePage
from etu.gui.search import (
    Debouncer,
    match_count,
    search_universe,
)
from etu.gui.theme import COLORS, UNIT
from etu.gui.widgets import (
    CutButton,
    DetailRow,
    PhotonPanel,
    PhotonToolStrip,
    StatusLabel,
    panel_splitter,
)
from etu.universe import (
    get_constellation_details,
    get_region_details,
    get_system,
)


KIND_LABELS = {
    "system": "SOLAR SYSTEM",
    "constellation": "CONSTELLATION",
    "region": "REGION",
}

SPACE_LABELS = {
    "highsec": "HIGHSEC",
    "lowsec": "LOWSEC",
    "nullsec": "NULLSEC",
    "wormhole": "WORMHOLE",
}


class UniverseDetailRow(DetailRow):
    activated = Signal(object)

    def __init__(self, label="", value="-", *, parent=None):
        super().__init__(label, value, parent=parent)
        self.label_widget = self.layout().itemAt(0).widget()
        self._target = None
        self.value_widget.installEventFilter(self)

    def set_detail(self, label, value, target=None):
        self.label_widget.setText(str(label).upper())
        self.value_widget.setText(str(value))
        self._target = target

        if target is None:
            self.value_widget.unsetCursor()
            self.value_widget.setToolTip("")
        else:
            self.value_widget.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            self.value_widget.setToolTip(
                f"Open {target[2]}"
            )

    def eventFilter(self, watched, event):
        if (
            watched is self.value_widget
            and self._target is not None
            and event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.activated.emit(self._target)
            return True

        return super().eventFilter(watched, event)


class UniversePage(BasePage):
    navigation_origin_requested = Signal(str)
    navigation_destination_requested = Signal(str)

    def __init__(self):
        super().__init__("Universe")

        self._current_kind = None
        self._current_object_id = None
        self._current_system_name = None

        search_panel = PhotonToolStrip()
        row = QHBoxLayout()
        row.setSpacing(UNIT)

        self.kind = QComboBox()
        self.kind.addItem("ALL OBJECTS", None)
        self.kind.addItem("SOLAR SYSTEM", "system")
        self.kind.addItem("CONSTELLATION", "constellation")
        self.kind.addItem("REGION", "region")
        self.kind.setAccessibleName("Universe search type")

        self.space = QComboBox()
        self.space.addItem("ALL SPACE", None)
        self.space.addItem("HIGHSEC", "highsec")
        self.space.addItem("LOWSEC", "lowsec")
        self.space.addItem("NULLSEC", "nullsec")
        self.space.addItem("WORMHOLE", "wormhole")
        self.space.setAccessibleName("Universe space filter")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search New Eden by name or ID"
        )
        self.search_input.setAccessibleName(
            "System, constellation, or region name or ID"
        )

        self.search_button = CutButton("SEARCH")
        self.search_button.setAccessibleName("Search universe")

        row.addWidget(self.kind)
        row.addWidget(self.space)
        row.addWidget(self.search_input, 1)
        row.addWidget(self.search_button)

        self.status = StatusLabel()
        search_panel.body_layout.addLayout(row)
        search_panel.body_layout.addWidget(self.status)

        results_panel = PhotonPanel("RESULTS")
        self.results = QListWidget()
        self.results.setAccessibleName("Universe search results")
        self.results.setAlternatingRowColors(True)
        self.results.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.results.setTextElideMode(Qt.TextElideMode.ElideRight)
        results_panel.body_layout.setContentsMargins(0, 0, 0, 0)
        results_panel.body_layout.addWidget(self.results)

        detail_panel = PhotonPanel("UNIVERSE DATA")
        self.detail_tabs = QTabWidget()
        self.detail_tabs.setAccessibleName("Universe data views")
        self.detail_tabs.setDocumentMode(True)
        self.detail_tabs.tabBar().setExpanding(False)
        self.detail_tabs.tabBar().setUsesScrollButtons(True)
        self.detail_tabs.tabBar().setElideMode(
            Qt.TextElideMode.ElideNone
        )

        self.overview_page = QWidget()
        overview_layout = QVBoxLayout(self.overview_page)
        overview_layout.setContentsMargins(
            UNIT,
            UNIT,
            UNIT,
            UNIT,
        )
        overview_layout.setSpacing(0)

        self.overview_placeholder = QTextBrowser()
        self.overview_placeholder.setAccessibleName(
            "Universe overview placeholder"
        )
        self.overview_placeholder.setPlaceholderText(
            "Select a result to inspect it"
        )

        self.overview_content = QWidget()
        overview_content_layout = QGridLayout(
            self.overview_content
        )
        overview_content_layout.setContentsMargins(0, 0, 0, 0)
        overview_content_layout.setSpacing(0)

        self.overview_rows_container = QWidget()
        self.overview_rows_layout = QVBoxLayout(
            self.overview_rows_container
        )
        self.overview_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.overview_rows_layout.setSpacing(UNIT)
        self.overview_rows = []

        for _index in range(10):
            self._append_overview_row()

        self.overview_rows_layout.addStretch(1)
        overview_content_layout.addWidget(
            self.overview_rows_container,
            0,
            0,
        )

        self.overview_actions = QWidget()
        action_layout = QHBoxLayout(self.overview_actions)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(UNIT)

        self.origin_button = CutButton("SET AS ORIGIN")
        self.origin_button.setAccessibleName(
            "Set selected system as navigation origin"
        )
        self.destination_button = CutButton("SET AS DESTINATION")
        self.destination_button.setAccessibleName(
            "Set selected system as navigation destination"
        )
        action_layout.addWidget(self.origin_button)
        action_layout.addWidget(self.destination_button)
        self.overview_actions.setVisible(False)
        overview_content_layout.addWidget(
            self.overview_actions,
            0,
            0,
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignRight,
        )

        overview_layout.addWidget(self.overview_placeholder, 1)
        overview_layout.addWidget(self.overview_content, 1)

        self.connections_view = self._make_related_tree(
            accessible_name="Static system connections",
            columns=4,
        )
        self.systems_view = self._make_related_tree(
            accessible_name="Universe systems",
            columns=4,
        )
        self.constellations_view = self._make_related_tree(
            accessible_name="Region constellations",
            columns=6,
        )
        self.borders_view = self._make_related_tree(
            accessible_name="Universe static borders",
            columns=5,
        )

        self.connections_page = self._tree_tab(
            self.connections_view
        )
        self.constellations_page = self._tree_tab(
            self.constellations_view
        )
        self.systems_page = self._tree_tab(
            self.systems_view
        )
        self.borders_page = self._tree_tab(
            self.borders_view
        )

        self.tab_indexes = {
            "overview": self.detail_tabs.addTab(
                self.overview_page,
                "Overview",
            ),
            "connections": self.detail_tabs.addTab(
                self.connections_page,
                "Connections",
            ),
            "constellations": self.detail_tabs.addTab(
                self.constellations_page,
                "Constellations",
            ),
            "systems": self.detail_tabs.addTab(
                self.systems_page,
                "Systems",
            ),
            "borders": self.detail_tabs.addTab(
                self.borders_page,
                "Borders",
            ),
        }

        detail_panel.body_layout.setContentsMargins(0, 0, 0, 0)
        detail_panel.body_layout.setSpacing(0)
        detail_panel.body_layout.addWidget(self.detail_tabs)

        splitter = panel_splitter(
            results_panel,
            detail_panel,
            sizes=[UNIT * 44, UNIT * 86],
        )
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)

        self.root_layout.addWidget(search_panel)
        self.root_layout.addWidget(splitter, 1)

        self.search_debouncer = Debouncer(
            self,
            self.search,
        )

        self.search_button.clicked.connect(
            self._search_immediately
        )
        self.search_input.returnPressed.connect(
            self._search_immediately
        )
        self.search_input.textEdited.connect(
            self._search_text_edited
        )
        self.kind.currentIndexChanged.connect(
            self._filter_changed
        )
        self.space.currentIndexChanged.connect(
            self._filter_changed
        )
        self.results.currentItemChanged.connect(
            self.show_result
        )
        self.connections_view.itemClicked.connect(
            self._tree_target_clicked
        )
        self.systems_view.itemClicked.connect(
            self._tree_target_clicked
        )
        self.constellations_view.itemClicked.connect(
            self._tree_target_clicked
        )
        self.borders_view.itemClicked.connect(
            self._tree_target_clicked
        )
        self.origin_button.clicked.connect(
            self._request_origin
        )
        self.destination_button.clicked.connect(
            self._request_destination
        )

        self._clear_details()

        if not sde.is_ready():
            self.search_input.setEnabled(False)
            self.kind.setEnabled(False)
            self.space.setEnabled(False)
            self.search_button.setEnabled(False)
            self.status.set_status(
                "SDE database is not ready",
                "error",
            )

    @staticmethod
    def _tree_tab(tree):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(
            UNIT,
            UNIT,
            UNIT,
            UNIT,
        )
        layout.setSpacing(0)
        layout.addWidget(tree)
        return tab

    @staticmethod
    def _make_related_tree(
        *,
        accessible_name,
        columns,
    ):
        tree = QTreeWidget()
        tree.setObjectName("UniverseRelatedTree")
        tree.setAccessibleName(accessible_name)
        tree.setColumnCount(columns)
        tree.setHeaderHidden(True)
        tree.setRootIsDecorated(False)
        tree.setItemsExpandable(False)
        tree.setIndentation(0)
        tree.setUniformRowHeights(True)
        tree.setAlternatingRowColors(False)
        tree.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        tree.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        tree.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        tree.setStyleSheet(
            f"QTreeWidget#UniverseRelatedTree {{"
            f" background: {COLORS['panel']};"
            f" alternate-background-color: {COLORS['panel']};"
            f" }}"
            f"QTreeWidget#UniverseRelatedTree::branch:hover {{"
            f" background: {COLORS['panel_hover']};"
            f" border-left: {UNIT}px solid {COLORS['panel']};"
            f" }}"
            f"QTreeWidget#UniverseRelatedTree::item:hover {{"
            f" background: {COLORS['panel_hover']};"
            f" }}"
        )

        header = tree.header()

        for column in range(columns - 1):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        header.setSectionResizeMode(
            columns - 1,
            QHeaderView.ResizeMode.Stretch,
        )
        return tree

    def _search_text_edited(self, text):
        if text.strip():
            self.search_debouncer.schedule()
        else:
            self.search_debouncer.cancel()
            self.results.clear()
            self.status.set_status("")
            self._clear_details()

    def _search_immediately(self):
        self.search_debouncer.cancel()
        self.search(manual=True)

    def _filter_changed(self, _index=None):
        if self.search_input.text().strip():
            self._search_immediately()
        else:
            self.results.clear()
            self.status.set_status("")
            self._clear_details()

    def search(self, manual=False):
        query = self.search_input.text().strip()

        if not query:
            if manual:
                self.status.set_status(
                    "Enter a universe name or ID",
                    "warning",
                )
            return

        matches = search_universe(
            query,
            limit=100,
            kind=self.kind.currentData(),
            space=self.space.currentData(),
        )

        self.results.clear()
        self._clear_details()

        if not matches:
            self.status.set_status(
                f'No universe objects found matching "{query}"',
                "warning",
            )
            return

        for match in matches:
            self._add_result(match)

        count = match_count(matches)
        self.status.set_status(
            f"{count} match" if count == 1 else f"{count} matches",
            "success",
        )
        self.results.setCurrentRow(0)

    def _add_result(self, match):
        kind = match["kind"]
        name = match["name"]

        if kind == "system":
            security = match.get("security_status")
            region = match.get("region_name") or "-"
            text = (
                f"{name} {security:.1f} - {region}"
                if security is not None
                else f"{name} - {region}"
            )
            object_id = match["system_id"]

        elif kind == "constellation":
            text = (
                f"{name} CONSTELLATION - "
                f"{match.get('region_name') or '-'}"
            )
            object_id = match["constellation_id"]

        else:
            system_count = int(match.get("system_count", 0) or 0)
            text = f"{name} REGION - {system_count} systems"
            object_id = match["region_id"]

        item = QListWidgetItem(text)
        item.setData(
            Qt.ItemDataRole.UserRole,
            (kind, int(object_id), name),
        )
        item.setToolTip(
            f"{name}\n{KIND_LABELS[kind]}\nID {object_id}"
        )
        self.results.addItem(item)

    def show_result(self, current, previous):
        if current is None:
            return

        payload = current.data(Qt.ItemDataRole.UserRole)

        if not payload:
            return

        kind, object_id, _name = payload
        self._inspect(kind, object_id)

    def _inspect(self, kind, object_id):
        self._current_kind = kind
        self._current_object_id = object_id
        self._current_system_name = None
        self.overview_actions.setVisible(False)

        if kind == "system":
            self._show_system(object_id)
        elif kind == "constellation":
            self._show_constellation(object_id)
        else:
            self._show_region(object_id)

    def _set_visible_tabs(self, names):
        names = set(names)

        for name, index in self.tab_indexes.items():
            self.detail_tabs.setTabVisible(
                index,
                name in names,
            )

        self.detail_tabs.setCurrentIndex(
            self.tab_indexes["overview"]
        )

    def _append_overview_row(self):
        row = UniverseDetailRow()
        row.activated.connect(
            self._overview_target_requested
        )
        row.setVisible(False)
        self.overview_rows.append(row)
        self.overview_rows_layout.addWidget(row)
        return row

    def _overview_target_requested(self, target):
        self._navigate_to(*target)

    def _clear_overview_rows(self):
        for row in self.overview_rows:
            row.setVisible(False)
            row.set_detail("", "-")

    def _clear_details(self):
        self._current_kind = None
        self._current_object_id = None
        self._current_system_name = None
        self.overview_actions.setVisible(False)
        self._set_visible_tabs({"overview"})

        self._clear_overview_rows()

        for tree in (
            self.connections_view,
            self.systems_view,
            self.constellations_view,
            self.borders_view,
        ):
            tree.clear()

        self.overview_content.setVisible(False)
        self.overview_placeholder.setVisible(True)

    def _set_overview(self, rows):
        self._clear_overview_rows()
        self.overview_placeholder.setVisible(False)
        self.overview_content.setVisible(True)

        while len(self.overview_rows) < len(rows):
            self._append_overview_row()

        for row_widget, (label, value, target) in zip(
            self.overview_rows,
            rows,
        ):
            row_widget.set_detail(
                label,
                value,
                target,
            )
            row_widget.setVisible(True)

    @staticmethod
    def _count(data, key):
        return int(data.get(key, 0) or 0)

    def _show_system(self, system_id):
        system = get_system(system_id)

        if system is None:
            self._set_overview([
                ("STATUS", "System data is unavailable", None),
            ])
            return

        self._current_system_name = system["name"]
        self.overview_actions.setVisible(True)
        self._set_visible_tabs({"overview", "connections"})

        security = system.get("security_status")
        self._set_overview([
            ("NAME", system.get("name", "-"), None),
            ("SYSTEM ID", system.get("system_id", "-"), None),
            (
                "SECURITY",
                f"{security:.3f}" if security is not None else "-",
                None,
            ),
            (
                "SPACE",
                SPACE_LABELS.get(system.get("space_kind"), "-") ,
                None,
            ),
            ("SECURITY CLASS", system.get("security_class") or "-", None),
            (
                "CONSTELLATION",
                system.get("constellation_name", "-"),
                (
                    "constellation",
                    int(system["constellation_id"]),
                    system.get("constellation_name", "-"),
                ),
            ),
            (
                "REGION",
                system.get("region_name", "-"),
                (
                    "region",
                    int(system["region_id"]),
                    system.get("region_name", "-"),
                ),
            ),
            ("FACTION ID", system.get("faction_id") or "-", None),
            ("CONNECTIONS", len(system.get("connections", [])), None),
        ])

        connections = system.get("connections", [])
        self.connections_view.clear()

        for connection in connections:
            values = (
                connection["name"],
                f"{connection['security_status']:.1f}",
                connection["constellation_name"],
                connection["region_name"],
            )
            target = (
                "system",
                int(connection["system_id"]),
                connection["name"],
            )
            self._add_target_item(
                self.connections_view,
                values,
                target,
            )

    def _show_constellation(self, constellation_id):
        constellation = get_constellation_details(constellation_id)

        if constellation is None:
            self._set_overview([
                ("STATUS", "Constellation data is unavailable", None),
            ])
            return

        self._set_visible_tabs({"overview", "systems", "borders"})
        systems = constellation.get("systems", [])
        borders = constellation.get("borders", [])

        self._set_overview([
            ("NAME", constellation.get("name", "-"), None),
            (
                "CONSTELLATION ID",
                constellation.get("constellation_id", "-"),
                None,
            ),
            (
                "REGION",
                constellation.get("region_name", "-"),
                (
                    "region",
                    int(constellation["region_id"]),
                    constellation.get("region_name", "-"),
                ),
            ),
            ("SYSTEMS", self._count(constellation, "system_count"), None),
            ("HIGHSEC", self._count(constellation, "highsec_count"), None),
            ("LOWSEC", self._count(constellation, "lowsec_count"), None),
            ("NULLSEC", self._count(constellation, "nullsec_count"), None),
            ("WORMHOLE", self._count(constellation, "wormhole_count"), None),
            ("FACTION ID", constellation.get("faction_id") or "-", None),
            ("BORDERS", len(borders), None),
        ])

        self._populate_systems(systems, context_key="region_name")

        self._populate_borders(borders, constellation_mode=True)

    def _show_region(self, region_id):
        region = get_region_details(region_id)

        if region is None:
            self._set_overview([
                ("STATUS", "Region data is unavailable", None),
            ])
            return

        self._set_visible_tabs({
            "overview",
            "constellations",
            "systems",
            "borders",
        })
        constellations = region.get("constellations", [])
        systems = region.get("systems", [])
        borders = region.get("borders", [])

        self._set_overview([
            ("NAME", region.get("name", "-"), None),
            ("REGION ID", region.get("region_id", "-"), None),
            (
                "CONSTELLATIONS",
                self._count(region, "constellation_count"),
                None,
            ),
            ("SYSTEMS", self._count(region, "system_count"), None),
            ("HIGHSEC", self._count(region, "highsec_count"), None),
            ("LOWSEC", self._count(region, "lowsec_count"), None),
            ("NULLSEC", self._count(region, "nullsec_count"), None),
            ("WORMHOLE", self._count(region, "wormhole_count"), None),
            ("FACTION ID", region.get("faction_id") or "-", None),
            ("BORDERS", len(borders), None),
        ])

        self.constellations_view.clear()

        for constellation in constellations:
            values = [
                constellation["name"],
                f"{self._count(constellation, 'system_count')} systems",
            ]

            for key, label in (
                ("highsec_count", "HIGHSEC"),
                ("lowsec_count", "LOWSEC"),
                ("nullsec_count", "NULLSEC"),
                ("wormhole_count", "WORMHOLE"),
            ):
                count = self._count(constellation, key)
                values.append(f"{count} {label}" if count else "")

            target = (
                "constellation",
                int(constellation["constellation_id"]),
                constellation["name"],
            )
            self._add_target_item(
                self.constellations_view,
                values,
                target,
            )

        self._populate_systems(systems, context_key="constellation_name")

        self._populate_borders(borders, constellation_mode=False)

    def _populate_systems(self, systems, *, context_key):
        self.systems_view.clear()

        for system in systems:
            values = (
                system["name"],
                f"{system['security_status']:.1f}",
                SPACE_LABELS.get(system.get("space_kind"), "-"),
                system.get(context_key, "-"),
            )
            target = (
                "system",
                int(system["system_id"]),
                system["name"],
            )
            self._add_target_item(
                self.systems_view,
                values,
                target,
            )

    def _populate_borders(self, borders, *, constellation_mode):
        self.borders_view.clear()

        for border in borders:
            values = [
                border["source_system_name"],
                "->",
                border["destination_system_name"],
            ]

            if constellation_mode:
                values.extend((
                    border["destination_constellation_name"],
                    border["destination_region_name"],
                ))
            else:
                values.extend((
                    "",
                    border["destination_region_name"],
                ))

            target = (
                "system",
                int(border["destination_system_id"]),
                border["destination_system_name"],
            )
            self._add_target_item(
                self.borders_view,
                values,
                target,
            )

    @staticmethod
    def _add_target_item(tree, values, target):
        values = [str(value) for value in values]
        item = QTreeWidgetItem(values)
        item.setData(0, Qt.ItemDataRole.UserRole, target)

        accessible_text = "  ".join(
            value for value in values if value
        )
        item.setData(
            0,
            Qt.ItemDataRole.AccessibleTextRole,
            accessible_text,
        )

        for column in range(tree.columnCount()):
            item.setToolTip(column, f"Open {target[2]}")

        tree.addTopLevelItem(item)

    def _tree_target_clicked(self, item, _column):
        target = item.data(0, Qt.ItemDataRole.UserRole)

        if target:
            self._navigate_to(*target)

    def _navigate_to(self, kind, object_id, name):
        kind_index = self.kind.findData(kind)
        all_space_index = self.space.findData(None)

        with QSignalBlocker(self.kind):
            if kind_index >= 0:
                self.kind.setCurrentIndex(kind_index)

        with QSignalBlocker(self.space):
            if all_space_index >= 0:
                self.space.setCurrentIndex(all_space_index)

        self.search_input.setText(name)
        self.search_debouncer.cancel()
        self.search()

        for row in range(self.results.count()):
            item = self.results.item(row)
            payload = item.data(Qt.ItemDataRole.UserRole)

            if payload and payload[0] == kind and payload[1] == object_id:
                self.results.setCurrentRow(row)
                break

    def _request_origin(self):
        if self._current_system_name:
            self.navigation_origin_requested.emit(
                self._current_system_name
            )

    def _request_destination(self):
        if self._current_system_name:
            self.navigation_destination_requested.emit(
                self._current_system_name
            )
