"""market page backed by public esi data"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QTabWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from etu import sde
from etu.gui.pages.base import BasePage
from etu.gui.search import (
    resolve_region,
    resolve_system,
    resolve_type,
)
from etu.gui.theme import UNIT
from etu.gui.widgets import (
    CutButton,
    PhotonPanel,
    PhotonToolStrip,
    StatusLabel,
    WeightedTableWidget,
)
from etu.market import (
    get_buy_orders_reaching_system,
    get_history,
    get_location_names,
    get_orders,
)
from etu.universe import (
    get_region,
    get_system,
)


def _format_order_range(order):
    order_range = order.get("range")

    if order_range == "station":
        return "Station"

    if order_range == "solarsystem":
        return "System"

    if order_range == "region":
        return "Region"

    try:
        jumps = int(order_range)
    except (TypeError, ValueError):
        return str(order_range or "-")

    return (
        "1 jump"
        if jumps == 1
        else f"{jumps} jumps"
    )


def _location_name(order, names):
    location_id = order["location_id"]

    return names.get(
        location_id,
        f"Player Structure · {location_id}",
    )


def _distance_text(order):
    order_range = order.get("range")
    distance = order.get("distance")

    if order_range == "station":
        return "location required"

    if distance == 0:
        return "same system"

    if distance == 1:
        return "1 jump"

    if distance is not None:
        return f"{distance} jumps"

    return "unknown"


def _resolve_location_names(orders):
    location_ids = list(dict.fromkeys(
        order["location_id"]
        for order in orders
    ))

    names = {}

    for start in range(0, len(location_ids), 900):
        names.update(
            get_location_names(
                location_ids[
                    start:start + 900
                ]
            )
        )

    return names


ALIGN_LEFT = (
    Qt.AlignmentFlag.AlignLeft
    | Qt.AlignmentFlag.AlignVCenter
)
def _item(text, alignment=ALIGN_LEFT):
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(alignment)

    return item


def _set_headers(table, headers):
    table.horizontalHeader().setDefaultAlignment(
        ALIGN_LEFT
    )

    for column, (text, alignment) in enumerate(headers):
        item = QTableWidgetItem(text)
        item.setTextAlignment(alignment)
        table.setHorizontalHeaderItem(column, item)


class MarketPage(BasePage):
    def __init__(self):
        super().__init__(
            "Market",
        )

        self._selection = None
        self._generation = 0
        self._loaded_tabs = set()
        self._loading_tabs = set()
        self._active_tasks = 0

        control_panel = PhotonToolStrip()

        row = QHBoxLayout()
        row.setSpacing(UNIT)

        self.item_input = QLineEdit()
        self.item_input.setPlaceholderText(
            "Item name or type ID"
        )
        self.item_input.setAccessibleName(
            "Item name or type ID"
        )

        self.scope = QComboBox()
        self.scope.addItem(
            "SYSTEM",
            "system",
        )
        self.scope.addItem(
            "REGION",
            "region",
        )

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText(
            "System or region name or ID"
        )
        self.location_input.setAccessibleName(
            "System or region name or ID"
        )

        self.load_button = CutButton("LOAD")
        self.load_button.setAccessibleName(
            "Load market data"
        )

        row.addWidget(
            self.item_input,
            2,
        )
        row.addWidget(self.scope)
        row.addWidget(
            self.location_input,
            2,
        )
        row.addWidget(
            self.load_button
        )

        self.status = StatusLabel()

        control_panel.body_layout.addLayout(
            row
        )
        control_panel.body_layout.addWidget(
            self.status
        )

        self.tabs = QTabWidget()
        self.tabs.setAccessibleName("Market data views")

        tab_bar = self.tabs.tabBar()
        tab_bar.setAccessibleName("Market data tabs")
        tab_bar.setExpanding(False)
        tab_bar.setUsesScrollButtons(True)

        # tabs keep their natural text width and scroll only when the window is genuinely too narrow
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone)

        orders = QWidget()
        orders_layout = QVBoxLayout(orders)
        orders_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        orders_layout.setSpacing(0)

        self.orders_table = WeightedTableWidget(
            0,
            5,
            weights=[
                18,
                12,
                16,
                38,
                16,
            ],
            minimum_widths=[
                UNIT * 12,
                UNIT * 12,
                UNIT * 12,
                UNIT * 28,
                UNIT * 11,
            ],
        )
        _set_headers(
            self.orders_table,
            [
                ("PRICE", ALIGN_LEFT),
                ("ORDER TYPE", ALIGN_LEFT),
                ("VOLUME", ALIGN_LEFT),
                ("LOCATION", ALIGN_LEFT),
                ("RANGE", ALIGN_LEFT),
            ],
        )
        self.orders_table.verticalHeader().setVisible(
            False
        )
        self.orders_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.orders_table.setAlternatingRowColors(
            True
        )
        orders_layout.addWidget(
            self.orders_table
        )

        history = QWidget()
        history_layout = QVBoxLayout(history)
        history_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        history_layout.setSpacing(0)

        self.history_table = WeightedTableWidget(
            0,
            5,
            weights=[
                18,
                22,
                20,
                20,
                20,
            ],
            minimum_widths=[
                UNIT * 13,
                UNIT * 14,
                UNIT * 12,
                UNIT * 12,
                UNIT * 12,
            ],
        )
        _set_headers(
            self.history_table,
            [
                ("DATE", ALIGN_LEFT),
                ("AVERAGE", ALIGN_LEFT),
                ("LOW", ALIGN_LEFT),
                ("HIGH", ALIGN_LEFT),
                ("VOLUME", ALIGN_LEFT),
            ],
        )
        self.history_table.verticalHeader().setVisible(
            False
        )
        self.history_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.history_table.setAlternatingRowColors(
            True
        )
        history_layout.addWidget(
            self.history_table
        )

        reachable = QWidget()
        reachable_layout = QVBoxLayout(
            reachable
        )
        reachable_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        reachable_layout.setSpacing(0)

        self.reachable_table = WeightedTableWidget(
            0,
            5,
            weights=[
                18,
                15,
                14,
                16,
                37,
            ],
            minimum_widths=[
                UNIT * 12,
                UNIT * 11,
                UNIT * 10,
                UNIT * 12,
                UNIT * 28,
            ],
        )
        _set_headers(
            self.reachable_table,
            [
                ("PRICE", ALIGN_LEFT),
                ("VOLUME", ALIGN_LEFT),
                ("RANGE", ALIGN_LEFT),
                ("DISTANCE", ALIGN_LEFT),
                ("LOCATION", ALIGN_LEFT),
            ],
        )
        self.reachable_table.verticalHeader().setVisible(
            False
        )
        self.reachable_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.reachable_table.setAlternatingRowColors(
            True
        )
        reachable_layout.addWidget(
            self.reachable_table
        )

        self.tabs.addTab(
            orders,
            "ORDERS",
        )
        self.tabs.addTab(
            history,
            "HISTORY",
        )
        self.tabs.addTab(
            reachable,
            "REACHABLE BUY ORDERS",
        )
        self.tabs.setTabEnabled(
            2,
            False,
        )

        self.root_layout.addWidget(
            control_panel
        )
        self.root_layout.addWidget(
            self.tabs,
            1,
        )

        self.load_button.clicked.connect(
            self.load_query
        )
        self.item_input.returnPressed.connect(
            self.load_query
        )
        self.location_input.returnPressed.connect(
            self.load_query
        )
        self.tabs.currentChanged.connect(
            self._tab_changed
        )
        self.item_input.textEdited.connect(
            self._invalidate_query
        )
        self.location_input.textEdited.connect(
            self._invalidate_query
        )
        self.scope.currentIndexChanged.connect(
            self._invalidate_query
        )

        if not sde.is_ready():
            self.item_input.setEnabled(False)
            self.scope.setEnabled(False)
            self.location_input.setEnabled(False)
            self.load_button.setEnabled(False)
            self.status.set_status(
                "SDE database is not ready",
                "error",
            )

    def _invalidate_query(self):
        if self.sender() is self.scope:
            if (
                self.scope.currentData() == "region"
                and self.tabs.currentIndex() == 2
            ):
                self.tabs.setCurrentIndex(0)

            if self.scope.currentData() == "region":
                self.tabs.setTabEnabled(
                    2,
                    False,
                )

        if self._selection is None:
            return

        self._generation += 1
        self._selection = None
        self._loaded_tabs.clear()
        self.status.set_status(
            "Query changed · press LOAD to refresh"
        )

    def load_query(self):
        item_query = self.item_input.text().strip()
        location_query = self.location_input.text().strip()

        if not item_query or not location_query:
            self.status.set_status(
                "Item and location are required",
                "warning",
            )
            return

        item = resolve_type(item_query)

        if item is None:
            self.status.set_status(
                f'No item found matching "{item_query}"',
                "warning",
            )
            return

        scope = self.scope.currentData()

        if scope == "system":
            match = resolve_system(
                location_query
            )

            if match is None:
                self.status.set_status(
                    f'No system found matching "{location_query}"',
                    "warning",
                )
                return

            system = get_system(
                match["system_id"]
            )

            if system is None:
                self.status.set_status(
                    "System data is unavailable",
                    "error",
                )
                return

            selection = {
                "type_id": item["type_id"],
                "item_name": item["name"],
                "system_id": system["system_id"],
                "system_name": system["name"],
                "region_id": system["region_id"],
                "region_name": system["region_name"],
                "scope": "system",
            }

        else:
            match = resolve_region(
                location_query
            )

            if match is None:
                self.status.set_status(
                    f'No region found matching "{location_query}"',
                    "warning",
                )
                return

            region = get_region(
                match["region_id"]
            )

            if region is None:
                self.status.set_status(
                    "Region data is unavailable",
                    "error",
                )
                return

            selection = {
                "type_id": item["type_id"],
                "item_name": item["name"],
                "system_id": None,
                "system_name": None,
                "region_id": region["region_id"],
                "region_name": region["name"],
                "scope": "region",
            }

        self._generation += 1
        self._selection = selection
        self._loaded_tabs.clear()
        self._clear_tables()
        self.tabs.setTabEnabled(
            2,
            scope == "system",
        )

        if (
            scope == "region"
            and self.tabs.currentIndex() == 2
        ):
            self.tabs.setCurrentIndex(0)

        self._load_tab(
            self.tabs.currentIndex()
        )

    def _clear_tables(self):
        self.orders_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.reachable_table.setRowCount(0)

    def _tab_changed(self, index):
        if self._selection is None:
            return

        self._load_tab(index)

    def _load_tab(self, index):
        if self._selection is None:
            return

        if index == 2 and self._selection["scope"] != "system":
            self.status.set_status(
                "Reachable buy orders require system scope",
                "warning",
            )
            return

        if index in self._loaded_tabs:
            self._show_loaded_status(index)
            return

        generation = self._generation
        key = (
            generation,
            index,
        )

        if key in self._loading_tabs:
            return

        self._loading_tabs.add(key)
        self._active_tasks += 1
        self.load_button.setEnabled(False)

        if index == 0:
            function = self._fetch_orders
            handler = self._orders_loaded
            label = "orders"

        elif index == 1:
            function = self._fetch_history
            handler = self._history_loaded
            label = "history"

        else:
            function = self._fetch_reachable
            handler = self._reachable_loaded
            label = "reachable buy orders"

        self.status.set_status(
            f"Loading {label}"
        )

        selection = dict(
            self._selection
        )

        def result(data):
            if generation != self._generation:
                return

            handler(data)
            self._loaded_tabs.add(index)
            self._show_loaded_status(index)

        def error(exception):
            if generation != self._generation:
                return

            self.status.set_status(
                f"Market request failed · {exception}",
                "error",
            )

        def finished():
            self._loading_tabs.discard(key)
            self._active_tasks = max(
                0,
                self._active_tasks - 1,
            )

            if self._active_tasks == 0:
                self.load_button.setEnabled(
                    sde.is_ready()
                )

        self.run_task(
            function,
            result,
            error,
            finished,
            selection,
        )

    def _show_loaded_status(self, index):
        selection = self._selection

        if selection is None:
            return

        location = (
            selection["system_name"]
            if selection["scope"] == "system"
            else selection["region_name"]
        )

        counts = {
            0: self.orders_table.rowCount(),
            1: self.history_table.rowCount(),
            2: self.reachable_table.rowCount(),
        }
        labels = {
            0: "orders",
            1: "history days",
            2: "reachable buy orders",
        }

        self.status.set_status(
            f"{selection['item_name']} · {location} · "
            f"{counts[index]} {labels[index]}",
            "success",
        )

    @staticmethod
    def _fetch_orders(selection):
        orders = get_orders(
            selection["region_id"],
            selection["type_id"],
            selection["system_id"],
        )

        names = _resolve_location_names(
            orders
        )

        return (
            orders,
            names,
        )

    @staticmethod
    def _fetch_history(selection):
        return get_history(
            selection["region_id"],
            selection["type_id"],
        )

    @staticmethod
    def _fetch_reachable(selection):
        orders = get_buy_orders_reaching_system(
            selection["region_id"],
            selection["type_id"],
            selection["system_id"],
        )

        names = _resolve_location_names(
            orders
        )

        return (
            orders,
            names,
        )

    def _orders_loaded(self, payload):
        orders, names = payload

        sell_orders = sorted(
            (
                order
                for order in orders
                if not order["is_buy_order"]
            ),
            key=lambda order: order["price"],
        )
        buy_orders = sorted(
            (
                order
                for order in orders
                if order["is_buy_order"]
            ),
            key=lambda order: order["price"],
            reverse=True,
        )
        ordered = [
            *sell_orders,
            *buy_orders,
        ]

        table = self.orders_table
        table.setUpdatesEnabled(False)

        try:
            table.setRowCount(len(ordered))

            for row_index, order in enumerate(ordered):
                price = _item(
                    f"{order['price']:,.2f} ISK"
                )
                order_type = _item(
                    "BUY"
                    if order["is_buy_order"]
                    else "SELL"
                )
                volume = _item(
                    f"{order['volume_remain']:,}"
                )
                location_text = _location_name(
                    order,
                    names,
                )
                location = _item(
                    location_text
                )
                location.setToolTip(
                    location_text
                )
                order_range = _item(
                    _format_order_range(order)
                )

                for column, cell in enumerate((
                    price,
                    order_type,
                    volume,
                    location,
                    order_range,
                )):
                    table.setItem(
                        row_index,
                        column,
                        cell,
                    )

        finally:
            table.setUpdatesEnabled(True)

    def _history_loaded(self, history):
        history = sorted(
            history,
            key=lambda day: day["date"],
            reverse=True,
        )

        table = self.history_table
        table.setUpdatesEnabled(False)

        try:
            table.setRowCount(len(history))

            for row_index, day in enumerate(history):
                cells = (
                    _item(day["date"]),
                    _item(
                        f"{day['average']:,.2f} ISK"
                    ),
                    _item(
                        f"{day['lowest']:,.2f} ISK"
                    ),
                    _item(
                        f"{day['highest']:,.2f} ISK"
                    ),
                    _item(
                        f"{day['volume']:,}"
                    ),
                )

                for column, cell in enumerate(cells):
                    table.setItem(
                        row_index,
                        column,
                        cell,
                    )

        finally:
            table.setUpdatesEnabled(True)

    def _reachable_loaded(self, payload):
        orders, names = payload
        orders = sorted(
            orders,
            key=lambda order: order["price"],
            reverse=True,
        )

        table = self.reachable_table
        table.setUpdatesEnabled(False)

        try:
            table.setRowCount(len(orders))

            for row_index, order in enumerate(orders):
                location_text = _location_name(
                    order,
                    names,
                )
                location = _item(
                    location_text
                )
                location.setToolTip(
                    location_text
                )

                cells = (
                    _item(
                        f"{order['price']:,.2f} ISK"
                    ),
                    _item(
                        f"{order['volume_remain']:,}"
                    ),
                    _item(
                        _format_order_range(order)
                    ),
                    _item(
                        _distance_text(order)
                    ),
                    location,
                )

                for column, cell in enumerate(cells):
                    table.setItem(
                        row_index,
                        column,
                        cell,
                    )

        finally:
            table.setUpdatesEnabled(True)
