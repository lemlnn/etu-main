"""inventory gui using the existing local sde backend"""

from collections import defaultdict

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOption,
    QStyleOptionViewItem,
    QTabWidget,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from etu import sde
from etu.inventory import (
    get_type,
    get_type_dogma,
)
from etu.gui.dogma import (
    attribute_display_rows,
    dogma_icon,
    dogma_icon_size,
    fitting_attributes,
    fitting_effect_rows,
    format_dogma_value,
)
from etu.gui.meta import (
    META_GROUP_ROLE,
    MetaTagDelegate,
    meta_group_name,
)
from etu.gui.pages.base import BasePage
from etu.gui.search import (
    Debouncer,
    TypeCategoryFilter,
    match_count,
    search_types,
)
from etu.gui.preferences import inventory_search_preferences
from etu.gui.theme import COLORS, UNIT
from etu.gui.widgets import (
    CutButton,
    DetailRow,
    PhotonPanel,
    PhotonToolStrip,
    StatusLabel,
    panel_splitter,
)


ROMAN_LEVELS = {
    0: "-",
    1: "I",
    2: "II",
    3: "III",
    4: "IV",
    5: "V",
}

ATTRIBUTE_SECTION_ROLE = int(
    Qt.ItemDataRole.UserRole
) + 1
GROUP_HEADER_ROLE = ATTRIBUTE_SECTION_ROLE + 1


class InventoryDetailDelegate(QStyledItemDelegate):
    def paint(
        self,
        painter,
        option,
        index,
    ):
        if index.data(GROUP_HEADER_ROLE):
            option = QStyleOptionViewItem(option)
            option.state &= ~QStyle.StateFlag.State_MouseOver

        super().paint(
            painter,
            option,
            index,
        )


class InventoryPage(BasePage):
    def __init__(self):
        super().__init__(
            "Inventory",
        )

        search_panel = PhotonToolStrip()

        search_row = QHBoxLayout()
        search_row.setSpacing(UNIT)

        preferences = inventory_search_preferences()

        self.category_filter = TypeCategoryFilter(
            published_only=preferences.published_only,
            accessible_name="Inventory category filter",
        )

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search item keywords or enter a type ID"
        )
        self.search_input.setAccessibleName(
            "Item name or type ID"
        )

        self.search_button = CutButton("SEARCH")
        self.search_button.setAccessibleName(
            "Search inventory"
        )

        self._search_debouncer = Debouncer(
            self,
            self.search,
        )

        search_row.addWidget(
            self.category_filter
        )
        search_row.addWidget(
            self.search_input,
            1,
        )
        search_row.addWidget(
            self.search_button,
        )

        self.search_status = StatusLabel()

        search_panel.body_layout.addLayout(
            search_row
        )
        search_panel.body_layout.addWidget(
            self.search_status
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
        self.results.setItemDelegate(
            MetaTagDelegate(self.results)
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
        detail_panel.body_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        detail_panel.body_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setAccessibleName("Item information tabs")
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabBar().setUsesScrollButtons(True)
        self.tabs.tabBar().setElideMode(
            Qt.TextElideMode.ElideNone
        )

        self._build_description_tab()
        self._build_attributes_tab()
        self._build_fitting_tab()
        self._build_requirements_tab()
        self._build_used_with_tab()
        self._build_variations_tab()
        self._build_industry_tab()
        self._set_detail_tabs({})

        detail_panel.body_layout.addWidget(
            self.tabs,
            1,
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
        self.search_input.textChanged.connect(
            self._queue_search
        )
        self.category_filter.currentIndexChanged.connect(
            lambda _index: self.search()
        )
        self.results.currentItemChanged.connect(
            self.show_item
        )

        if not sde.is_ready():
            self.category_filter.setEnabled(False)
            self.search_input.setEnabled(False)
            self.search_button.setEnabled(False)
            self.results.addItem(
                "SDE database is not ready"
            )

    def _build_description_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(
            UNIT,
            UNIT,
            UNIT,
            UNIT,
        )
        layout.setSpacing(UNIT)

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
            layout.addWidget(row)

        description_label = QLabel("DESCRIPTION")
        description_label.setObjectName("SectionLabel")

        self.description = QTextBrowser()
        self.description.setAccessibleName("Item description")
        self.description.setPlaceholderText(
            "Select an item to inspect it"
        )

        layout.addSpacing(UNIT)
        layout.addWidget(description_label)
        layout.addWidget(
            self.description,
            1,
        )

        self.description_tab = tab
        self.tabs.addTab(
            self.description_tab,
            "Description",
        )

    def _build_attributes_tab(self):
        self.attributes_view = self._detail_tree(
            "Item dogma attributes",
        )
        self._configure_toggle_tree(
            self.attributes_view
        )
        self.attributes_view.setItemDelegate(
            InventoryDetailDelegate(
                self.attributes_view
            )
        )
        self.attributes_tab = self._tree_tab(
            self.attributes_view
        )
        self.tabs.addTab(
            self.attributes_tab,
            "Attributes",
        )

    def _build_fitting_tab(self):
        self.fitting_view = self._detail_tree(
            "Item fitting requirements",
        )
        self.fitting_tab = self._tree_tab(
            self.fitting_view
        )
        self.tabs.addTab(
            self.fitting_tab,
            "Fitting",
        )

    def _build_requirements_tab(self):
        self.requirements_view = self._detail_tree(
            "Required skills",
            decorated=True,
        )
        self._configure_toggle_tree(
            self.requirements_view
        )
        self.requirements_tab = self._tree_tab(
            self.requirements_view
        )
        self.tabs.addTab(
            self.requirements_tab,
            "Requirements",
        )

    def _configure_toggle_tree(
        self,
        tree,
    ):
        tree.setItemsExpandable(False)
        tree.itemPressed.connect(
            self._toggle_tree_item
        )
        tree.itemDoubleClicked.connect(
            self._toggle_tree_item
        )

    def _build_used_with_tab(self):
        self.used_with_view = self._related_tree(
            "Compatible item types"
        )
        self.used_with_tab = self._tree_tab(
            self.used_with_view
        )
        self.tabs.addTab(
            self.used_with_tab,
            "Used with",
        )

    def _build_variations_tab(self):
        self.variations_view = self._related_tree(
            "Item variations"
        )
        self.variations_tab = self._tree_tab(
            self.variations_view
        )
        self.tabs.addTab(
            self.variations_tab,
            "Variations",
        )

    def _build_industry_tab(self):
        self.industry_view = self._related_tree(
            "Industry information"
        )
        self.industry_tab = self._tree_tab(
            self.industry_view
        )
        self.tabs.addTab(
            self.industry_tab,
            "Industry",
        )

    def _tree_tab(self, tree):
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

    def _detail_tree(
        self,
        accessible_name,
        decorated=False,
    ):
        tree = QTreeWidget()
        tree.setObjectName("InventoryDetailTree")
        tree.setAccessibleName(accessible_name)
        tree.setColumnCount(2)
        tree.setHeaderHidden(True)
        tree.setRootIsDecorated(decorated)
        tree.setIndentation(UNIT * 2)
        tree.setIconSize(dogma_icon_size())
        tree.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        tree.setAlternatingRowColors(False)
        tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        tree.setStyleSheet(
            f"QTreeWidget#InventoryDetailTree {{"
            f" background: {COLORS['panel']};"
            f" alternate-background-color: {COLORS['panel']};"
            f" }}"
        )

        header = tree.header()
        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        return tree

    def _related_tree(
        self,
        accessible_name,
    ):
        tree = self._detail_tree(
            accessible_name,
            decorated=False,
        )
        tree.setItemsExpandable(False)
        tree.setStyleSheet(
            tree.styleSheet()
            + f"QTreeWidget#InventoryDetailTree::branch:hover {{"
            + f" background: {COLORS['panel_hover']};"
            + f" border-left: {UNIT}px solid {COLORS['panel']};"
            + " }"
            + f"QTreeWidget#InventoryDetailTree::item:hover {{"
            + f" background: {COLORS['panel_hover']};"
            + f" margin-right: {UNIT}px;"
            + " }"
            + f"QTreeWidget#InventoryDetailTree::item:has-children:hover {{"
            + f" margin-left: {UNIT}px;"
            + " }"
        )
        tree.setColumnCount(1)
        tree.header().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        return tree

    def _queue_search(self):
        self._search_debouncer.schedule()

    def refresh_search_preferences(self):
        preferences = inventory_search_preferences()
        self.category_filter.refresh(
            published_only=preferences.published_only,
        )
        self.search()

    def search(self):
        self._search_debouncer.cancel()
        query = self.search_input.text().strip()

        self.results.clear()

        if not query:
            self.search_status.set_status("")
            return

        preferences = inventory_search_preferences()
        limit = (
            None
            if preferences.show_all_results
            else preferences.result_limit
        )

        results = search_types(
            query,
            limit=limit,
            published_only=preferences.published_only,
            category_id=self.category_filter.currentData(),
        )

        self.results.setUpdatesEnabled(False)

        try:
            for result in results:
                self._add_result(result)
        finally:
            self.results.setUpdatesEnabled(True)

        if not results:
            self.search_status.set_status(
                f'No item found matching "{query}"',
                "warning",
            )
            return

        count = match_count(results)
        self.search_status.set_status(
            f"{count} match"
            if count == 1
            else f"{count} matches",
            "success",
        )

    def _add_result(self, result):
        item = QListWidgetItem(
            result["name"]
        )
        item.setData(
            Qt.ItemDataRole.UserRole,
            result["type_id"],
        )
        item.setData(
            META_GROUP_ROLE,
            result.get("meta_group_id"),
        )

        meta_name = meta_group_name(
            result.get("meta_group_id")
        )

        tooltip = (
            f"{result['name']}\n"
            f"Type ID {result['type_id']}"
        )

        if meta_name:
            tooltip += f"\n{meta_name}"

        item.setToolTip(tooltip)
        item.setData(
            Qt.ItemDataRole.AccessibleTextRole,
            (
                f"{result['name']}, {meta_name}"
                if meta_name
                else result["name"]
            ),
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

        self._show_description(data)

        if sde.needs_sde_refresh():
            self._show_refresh_required()
            return

        dogma = get_type_dogma(type_id)

        availability = {
            "attributes": self._show_attributes(
                dogma["attributes"]
            ),
            "fitting": self._show_fitting(
                dogma["attributes"],
                dogma["effects"],
            ),
            "requirements": self._show_requirements(
                dogma["requirements"]
            ),
            "used_with": self._show_grouped_types(
                self.used_with_view,
                dogma["used_with"],
                "No compatible items found",
            ),
            "variations": self._show_grouped_types(
                self.variations_view,
                dogma["variations"],
                "No variations found",
                minimum_rows=2,
            ),
            "industry": self._show_industry(
                dogma["blueprints"],
                dogma["materials"],
            ),
        }
        self._set_detail_tabs(availability)

    def _show_refresh_required(self):
        message = (
            "Refresh SDE in Settings "
            "to load item details"
        )

        for tree in (
            self.attributes_view,
            self.fitting_view,
            self.requirements_view,
            self.used_with_view,
            self.variations_view,
            self.industry_view,
        ):
            tree.clear()
            self._empty_tree(
                tree,
                message,
            )

        self._set_detail_tabs({})

    def _set_detail_tabs(
        self,
        availability,
    ):
        pages = {
            "attributes": self.attributes_tab,
            "fitting": self.fitting_tab,
            "requirements": self.requirements_tab,
            "used_with": self.used_with_tab,
            "variations": self.variations_tab,
            "industry": self.industry_tab,
        }

        current = self.tabs.currentWidget()

        for key, page in pages.items():
            index = self.tabs.indexOf(page)
            self.tabs.setTabVisible(
                index,
                bool(availability.get(key)),
            )

        if (
            current in pages.values()
            and not self.tabs.isTabVisible(
                self.tabs.indexOf(current)
            )
        ):
            self.tabs.setCurrentWidget(
                self.description_tab
            )

    def _show_description(self, data):
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
            data.get("description")
            or "No description available"
        )

    def _show_attributes(
        self,
        attributes,
    ):
        self.attributes_view.clear()
        rows = attribute_display_rows(attributes)

        if not rows:
            self._empty_tree(
                self.attributes_view,
                "No displayable dogma attributes",
            )
            return False

        for row in rows:
            if row["kind"] == "section":
                self._add_attribute_section(row)
                continue

            self._add_detail_item(
                self.attributes_view,
                row["label"],
                row["value"],
                row.get("icon_id"),
            )

        return True

    def _add_attribute_section(
        self,
        section,
    ):
        item = QTreeWidgetItem([
            section["label"],
            "",
        ])
        item.setData(
            0,
            ATTRIBUTE_SECTION_ROLE,
            True,
        )
        self.attributes_view.addTopLevelItem(item)

        for group in section["groups"]:
            self._group_header(
                item,
                group["label"],
            )

            for row in group["rows"]:
                self._add_detail_item(
                    item,
                    row["label"],
                    row["value"],
                    row.get("icon_id"),
                )

        item.setExpanded(False)
        self._set_attribute_section_state(item)

    def _set_attribute_section_state(
        self,
        item,
    ):
        expanded = item.isExpanded()
        item.setIcon(
            0,
            self._tree_branch_icon(expanded),
        )
        item.setData(
            0,
            Qt.ItemDataRole.AccessibleTextRole,
            (
                f"{item.text(0)}, "
                f"{'expanded' if expanded else 'collapsed'}"
            ),
        )


    def _tree_branch_icon(
        self,
        expanded,
    ):
        size = self.attributes_view.indentation()
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        option = QStyleOption()
        option.initFrom(self.attributes_view)
        option.rect = QRect(0, 0, size, size)
        primitive = (
            QStyle.PrimitiveElement.PE_IndicatorArrowDown
            if expanded
            else QStyle.PrimitiveElement.PE_IndicatorArrowRight
        )

        painter = QPainter(pixmap)
        self.attributes_view.style().drawPrimitive(
            primitive,
            option,
            painter,
            self.attributes_view,
        )
        painter.end()

        return QIcon(pixmap)

    def _show_fitting(
        self,
        attributes,
        effects,
    ):
        self.fitting_view.clear()

        rows = fitting_effect_rows(effects)

        for attribute in fitting_attributes(
            attributes
        ):
            rows.append({
                "label": (
                    attribute.get("display_name")
                    or attribute.get("name")
                ),
                "value": format_dogma_value(
                    attribute
                ),
                "icon_id": attribute.get(
                    "icon_id"
                ),
            })

        if not rows:
            self._empty_tree(
                self.fitting_view,
                "No fitting requirements",
            )
            return False

        for row in rows:
            self._add_detail_item(
                self.fitting_view,
                row["label"],
                row["value"],
                row.get("icon_id"),
            )

        return True

    def _show_requirements(
        self,
        requirements,
    ):
        self.requirements_view.clear()

        if not requirements:
            self._empty_tree(
                self.requirements_view,
                "No skill requirements",
            )
            return False

        for requirement in requirements:
            self._add_requirement(
                self.requirements_view,
                requirement,
            )

        self.requirements_view.expandAll()
        return True

    def _toggle_tree_item(
        self,
        item,
        column,
    ):
        if item.childCount() == 0:
            return

        item.setExpanded(
            not item.isExpanded()
        )

        if item.data(0, ATTRIBUTE_SECTION_ROLE):
            self._set_attribute_section_state(item)

    def _add_requirement(
        self,
        parent,
        requirement,
    ):
        level = int(
            requirement.get("level", 0)
        )
        item = QTreeWidgetItem([
            requirement.get("name", "Unknown skill"),
            ROMAN_LEVELS.get(
                level,
                str(level),
            ),
        ])
        item.setTextAlignment(
            1,
            int(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            ),
        )
        if isinstance(parent, QTreeWidget):
            parent.addTopLevelItem(item)
        else:
            parent.addChild(item)

        for child in requirement.get(
            "requirements",
            (),
        ):
            self._add_requirement(
                item,
                child,
            )

    def _show_grouped_types(
        self,
        tree,
        rows,
        empty_text,
        minimum_rows=1,
    ):
        tree.clear()

        if len(rows) < minimum_rows:
            self._empty_tree(
                tree,
                empty_text,
            )
            return False

        grouped = defaultdict(list)

        for row in rows:
            grouped[
                self._meta_heading(
                    row.get("meta_group_id")
                )
            ].append(row)

        for heading, items in grouped.items():
            header = self._group_header(
                tree,
                heading,
            )

            for row in items:
                child = QTreeWidgetItem([
                    row["name"]
                ])
                child.setToolTip(
                    0,
                    f"{row['name']}\nType ID {row['type_id']}",
                )
                header.addChild(child)

        tree.expandAll()
        return True

    def _show_industry(
        self,
        blueprints,
        materials,
    ):
        self.industry_view.clear()

        if not blueprints and not materials:
            self._empty_tree(
                self.industry_view,
                "No industry data",
            )
            return False

        if blueprints:
            header = self._group_header(
                self.industry_view,
                "Blueprint",
            )

            for blueprint in blueprints:
                header.addChild(
                    QTreeWidgetItem([
                        blueprint["name"]
                    ])
                )

        if materials:
            header = self._group_header(
                self.industry_view,
                "Reprocessed materials",
            )

            for material in materials:
                quantity = material["quantity"]
                unit = (
                    "Unit"
                    if quantity == 1
                    else "Units"
                )
                header.addChild(
                    QTreeWidgetItem([
                        f"{material['name']} "
                        f"({quantity:,} {unit})"
                    ])
                )

        self.industry_view.expandAll()
        return True

    def _add_detail_item(
        self,
        parent,
        label,
        value,
        icon_id=None,
    ):
        item = QTreeWidgetItem([
            str(label),
            str(value),
        ])

        icon = dogma_icon(icon_id)

        if not icon.isNull():
            item.setIcon(0, icon)

        item.setTextAlignment(
            1,
            int(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            ),
        )

        if isinstance(parent, QTreeWidget):
            parent.addTopLevelItem(item)
        else:
            parent.addChild(item)

    def _group_header(
        self,
        parent,
        text,
    ):
        item = QTreeWidgetItem([""])
        item.setFlags(
            item.flags()
            & ~Qt.ItemFlag.ItemIsSelectable
        )
        item.setData(
            0,
            GROUP_HEADER_ROLE,
            True,
        )

        if isinstance(parent, QTreeWidget):
            tree = parent
            tree.addTopLevelItem(item)
        else:
            tree = parent.treeWidget()
            parent.addChild(item)

        if tree.columnCount() > 1:
            item.setFirstColumnSpanned(True)

        label = QLabel(text)
        label.setObjectName("DogmaGroupHeader")
        label.setAccessibleName(text)
        label.setMinimumHeight(UNIT * 3)

        tree.setItemWidget(
            item,
            0,
            label,
        )

        return item

    def _empty_tree(
        self,
        tree,
        text,
    ):
        item = QTreeWidgetItem([text])
        item.setFlags(
            item.flags()
            & ~Qt.ItemFlag.ItemIsSelectable
        )
        tree.addTopLevelItem(item)

    def _meta_heading(
        self,
        meta_group_id,
    ):
        if meta_group_id in (None, 1):
            return "Tech I"

        return (
            meta_group_name(meta_group_id)
            or f"Meta Group {meta_group_id}"
        )
