"""market page backed by public esi data"""

from PySide6.QtCore import QAbstractTableModel, QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from etu import sde
from etu.gui.pages.base import BasePage
from etu.gui.search import (
    KeywordSuggestions,
    TypeCategoryFilter,
    resolve_region,
    resolve_system,
    resolve_type,
    search_regions,
    search_systems,
    search_types,
)
from etu.gui.theme import COLORS, UNIT
from etu.gui.widgets import (
    CutButton,
    PhotonPanel,
    PhotonToolStrip,
    StatusLabel,
    WeightedTableView,
    WeightedTableWidget,
)
from etu.market import (
    GLOBAL_MARKET_NAME,
    GLOBAL_PLEX_REGION_ID,
    PLEX_TYPE_ID,
    get_buy_orders_reaching_system,
    get_history,
    get_location_names,
    get_orders,
    is_global_market_type,
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
        "1 Jump"
        if jumps == 1
        else f"{jumps} Jumps"
    )


def _location_name(order, names):
    location_id = order["location_id"]

    return names.get(
        location_id,
        f"Player Structure - {location_id}",
    )


def _distance_text(order):
    order_range = order.get("range")
    distance = order.get("distance")

    if order_range == "station":
        return "Exact Station"

    if distance == 0:
        return "Same System"

    if distance == 1:
        return "1 Jump"

    if distance is not None:
        return f"{distance} Jumps"

    return "Unknown"


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


def _compact_number(value):
    value = float(value)
    absolute = abs(value)

    for threshold, suffix in (
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    ):
        if absolute >= threshold:
            scaled = value / threshold
            precision = 0 if abs(scaled) >= 100 else 1
            return f"{scaled:.{precision}f}{suffix}"

    return f"{value:,.0f}"


class MarketOrdersModel(QAbstractTableModel):
    """Virtualized order rows so large markets do not create thousands of widgets."""

    HEADERS = (
        "PRICE",
        "VOLUME",
        "LOCATION",
        "RANGE",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []

    def rowCount(self, parent=None):
        return 0 if parent and parent.isValid() else len(self._rows)

    def columnCount(self, parent=None):
        return 0 if parent and parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
            and 0 <= section < len(self.HEADERS)
        ):
            return self.HEADERS[section]

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return ALIGN_LEFT

        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = self._rows[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return row[index.column()]

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return ALIGN_LEFT

        if (
            role == Qt.ItemDataRole.ToolTipRole
            and index.column() == 2
        ):
            return row[2]

        return None

    def clear(self):
        if not self._rows:
            return

        self.beginResetModel()
        self._rows = []
        self.endResetModel()

    def set_orders(self, orders, names):
        rows = []

        for order in orders:
            location_text = _location_name(order, names)
            rows.append((
                f"{order['price']:,.2f} ISK",
                f"{order['volume_remain']:,}",
                location_text,
                _format_order_range(order),
            ))

        self.beginResetModel()
        self._rows = rows
        self.endResetModel()


class MarketOrderPanel(PhotonPanel):
    """Resizable order-book pane with a stable, top-anchored table viewport."""

    def __init__(self, title, table, parent=None):
        super().__init__(title, parent=parent)
        self._table = table

        # Let the table viewport resize continuously with the splitter. The
        # panel itself owns the boundary, so the table can run flush to that
        # boundary without an extra internal bottom inset.
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        self.body_layout.addWidget(table, 1)

        table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setMinimumHeight(UNIT * 11)


class MarketHistoryGraph(QWidget):
    """Compact cached ETU-styled market history chart with price and volume."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._history = []
        self._hover_index = None
        self._static_cache = None
        self._cache_key = None
        self._cache_geometry = None
        self._resize_cache_timer = QTimer(self)
        self._resize_cache_timer.setSingleShot(True)
        self._resize_cache_timer.setInterval(60)
        self._resize_cache_timer.timeout.connect(
            self._finish_resize_cache
        )
        self.setMouseTracking(True)
        self.setAttribute(
            Qt.WidgetAttribute.WA_OpaquePaintEvent,
            True,
        )
        self.setAccessibleName("Market history graph")
        self.setAccessibleDescription(
            "Daily average, low, high, and volume market history"
        )
        self.setMinimumHeight(UNIT * 30)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    def _invalidate_cache(self):
        self._static_cache = None
        self._cache_key = None
        self._cache_geometry = None

    def _finish_resize_cache(self):
        # During a live resize the existing pixmap is scaled temporarily.
        # Rebuild the crisp graph once resize events have settled.
        self._invalidate_cache()
        self.update()

    def clear(self):
        self._history = []
        self._hover_index = None
        self._resize_cache_timer.stop()
        self._invalidate_cache()
        self.setAccessibleDescription(
            "No market history loaded"
        )
        self.update()

    def set_history(self, history):
        self._history = [
            dict(day)
            for day in history
        ]
        self._hover_index = None
        self._resize_cache_timer.stop()
        self._invalidate_cache()

        if self._history:
            first = self._history[0]["date"]
            last = self._history[-1]["date"]
            self.setAccessibleDescription(
                f"{len(self._history)} daily market history points "
                f"from {first} through {last}"
            )
        else:
            self.setAccessibleDescription(
                "No market history loaded"
            )

        self.update()

    def resizeEvent(self, event):
        # Coalesce a burst of resize events instead of rebuilding a complex
        # history graph for every intermediate window size.
        if self._static_cache is not None:
            self._resize_cache_timer.start()
        else:
            self._invalidate_cache()

        super().resizeEvent(event)

    def leaveEvent(self, event):
        if self._hover_index is not None:
            old_index = self._hover_index
            self._hover_index = None
            self._update_hover_regions(old_index, None)

        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        if not self._history:
            super().mouseMoveEvent(event)
            return

        price_rect, _, _ = self._plot_rects()
        x = event.position().x()

        if x < price_rect.left() or x > price_rect.right():
            index = None
        elif len(self._history) == 1:
            index = 0
        else:
            fraction = (
                (x - price_rect.left())
                / max(1.0, price_rect.width())
            )
            index = round(
                fraction * (len(self._history) - 1)
            )
            index = max(
                0,
                min(index, len(self._history) - 1),
            )

        if index != self._hover_index:
            old_index = self._hover_index
            self._hover_index = index
            self._update_hover_regions(old_index, index)

        super().mouseMoveEvent(event)

    def _plot_rects(self):
        rect = QRectF(self.rect())
        left = UNIT * 9
        right = UNIT * 8
        top = UNIT * 5
        bottom = UNIT * 5
        gap = UNIT * 5

        usable_height = max(
            UNIT * 12,
            rect.height() - top - bottom - gap,
        )
        price_height = usable_height * 0.72
        volume_height = usable_height - price_height

        price_rect = QRectF(
            rect.left() + left,
            rect.top() + top,
            max(1.0, rect.width() - left - right),
            max(1.0, price_height),
        )
        volume_rect = QRectF(
            price_rect.left(),
            price_rect.bottom() + gap,
            price_rect.width(),
            max(1.0, volume_height),
        )

        return price_rect, volume_rect, rect

    @staticmethod
    def _x_for_index(rect, index, count):
        if count <= 1:
            return rect.center().x()

        return (
            rect.left()
            + rect.width() * index / (count - 1)
        )

    @staticmethod
    def _y_for_value(rect, value, minimum, maximum):
        if maximum <= minimum:
            return rect.center().y()

        fraction = (value - minimum) / (maximum - minimum)
        return rect.bottom() - rect.height() * fraction

    def _draw_empty(self, painter):
        painter.setPen(QColor(COLORS["text_muted"]))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "Load market history to view graph",
        )

    def _draw_outline(self, painter):
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(COLORS["line"]), 1))
        painter.drawRect(
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        )

    def _price_bounds(self):
        minimum = min(
            float(day["lowest"])
            for day in self._history
        )
        maximum = max(
            float(day["highest"])
            for day in self._history
        )
        span = maximum - minimum

        if span <= 0:
            padding = max(1.0, abs(maximum) * 0.05)
        else:
            padding = span * 0.08

        return minimum - padding, maximum + padding

    def _display_samples(self, pixel_width):
        """Aggregate only when multiple days would occupy the same screen pixel."""
        count = len(self._history)
        target = max(2, int(pixel_width))

        if count <= target:
            return [
                (
                    index,
                    float(day["average"]),
                    float(day["lowest"]),
                    float(day["highest"]),
                    float(day["volume"]),
                )
                for index, day in enumerate(self._history)
            ]

        samples = []

        for bucket in range(target):
            start = bucket * count // target
            end = max(
                start + 1,
                (bucket + 1) * count // target,
            )
            segment = self._history[start:end]
            representative = (start + end - 1) / 2
            samples.append((
                representative,
                sum(float(day["average"]) for day in segment)
                / len(segment),
                min(float(day["lowest"]) for day in segment),
                max(float(day["highest"]) for day in segment),
                max(float(day["volume"]) for day in segment),
            ))

        return samples

    def _static_cache_key(self):
        return (
            self.width(),
            self.height(),
            round(self.devicePixelRatioF(), 3),
            len(self._history),
        )

    def _build_static_cache(self):
        dpr = max(1.0, self.devicePixelRatioF())
        pixel_width = max(1, round(self.width() * dpr))
        pixel_height = max(1, round(self.height() * dpr))
        cache = QPixmap(pixel_width, pixel_height)
        cache.setDevicePixelRatio(dpr)
        cache.fill(QColor(COLORS["base"]))

        painter = QPainter(cache)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        if not self._history:
            self._draw_empty(painter)
            self._draw_outline(painter)
            painter.end()
            self._static_cache = cache
            self._cache_geometry = None
            self._cache_key = self._static_cache_key()
            return

        price_rect, volume_rect, _ = self._plot_rects()
        count = len(self._history)
        price_min, price_max = self._price_bounds()
        volume_max = max(
            1.0,
            max(float(day["volume"]) for day in self._history),
        )
        samples = self._display_samples(price_rect.width())

        painter.setFont(self.font())
        for step in range(5):
            fraction = step / 4
            y = price_rect.top() + price_rect.height() * fraction
            value = price_max - (price_max - price_min) * fraction

            painter.setPen(QPen(QColor(COLORS["line"]), 1))
            painter.drawLine(
                QPointF(price_rect.left(), y),
                QPointF(price_rect.right(), y),
            )
            painter.setPen(QColor(COLORS["text_muted"]))
            painter.drawText(
                QRectF(
                    0,
                    y - UNIT,
                    price_rect.left() - UNIT,
                    UNIT * 2,
                ),
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter,
                _compact_number(value),
            )

        painter.setPen(QColor(COLORS["text_muted"]))
        painter.drawText(
            QRectF(UNIT, UNIT, UNIT * 16, UNIT * 2),
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter,
            "PRICE (ISK)",
        )

        high_points = []
        low_points = []
        average_points = []

        for index, average, low, high, _volume in samples:
            x = self._x_for_index(price_rect, index, count)
            high_points.append(QPointF(
                x,
                self._y_for_value(
                    price_rect,
                    high,
                    price_min,
                    price_max,
                ),
            ))
            low_points.append(QPointF(
                x,
                self._y_for_value(
                    price_rect,
                    low,
                    price_min,
                    price_max,
                ),
            ))
            average_points.append(QPointF(
                x,
                self._y_for_value(
                    price_rect,
                    average,
                    price_min,
                    price_max,
                ),
            ))

        range_polygon = QPolygonF(
            high_points + list(reversed(low_points))
        )
        range_fill = QColor(COLORS["panel_hover"])
        range_fill.setAlpha(150)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(range_fill)
        painter.drawPolygon(range_polygon)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.setPen(QPen(QColor(COLORS["text_bright"]), 2))
        painter.drawPolyline(QPolygonF(average_points))

        painter.setPen(QPen(QColor(COLORS["line"]), 1))
        painter.drawLine(
            QPointF(volume_rect.left(), volume_rect.top()),
            QPointF(volume_rect.right(), volume_rect.top()),
        )
        painter.setPen(QColor(COLORS["text_muted"]))
        painter.drawText(
            QRectF(
                UNIT,
                volume_rect.top() - UNIT * 3,
                UNIT * 20,
                UNIT * 2,
            ),
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter,
            "VOLUME (UNITS)",
        )
        painter.drawText(
            QRectF(
                UNIT,
                volume_rect.top(),
                price_rect.left() - UNIT * 2,
                UNIT * 2,
            ),
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter,
            _compact_number(volume_max),
        )
        painter.drawText(
            QRectF(
                UNIT,
                volume_rect.bottom() - UNIT * 2,
                price_rect.left() - UNIT * 2,
                UNIT * 2,
            ),
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter,
            "0",
        )

        slot_width = (
            volume_rect.width() / len(samples)
            if len(samples) > 1
            else volume_rect.width()
        )
        bar_width = max(
            1.0,
            min(UNIT, slot_width * 0.7),
        )
        volume_color = QColor(COLORS["accent_dim"])

        for index, _average, _low, _high, volume in samples:
            x = self._x_for_index(volume_rect, index, count)
            height = volume_rect.height() * volume / volume_max
            painter.fillRect(
                QRectF(
                    x - bar_width / 2,
                    volume_rect.bottom() - height,
                    bar_width,
                    height,
                ),
                volume_color,
            )

        label_count = min(5, count)
        label_indexes = []

        for slot in range(label_count):
            index = (
                0
                if label_count == 1
                else round(slot * (count - 1) / (label_count - 1))
            )
            if index not in label_indexes:
                label_indexes.append(index)

        painter.setPen(QColor(COLORS["text_muted"]))

        for index in label_indexes:
            day = self._history[index]
            x = self._x_for_index(volume_rect, index, count)
            painter.drawText(
                QRectF(
                    x - UNIT * 7,
                    volume_rect.bottom() + UNIT,
                    UNIT * 14,
                    UNIT * 2,
                ),
                Qt.AlignmentFlag.AlignHCenter
                | Qt.AlignmentFlag.AlignVCenter,
                day["date"],
            )

        # Align the legend to the vertical center of the PRICE (ISK) label.
        legend_y = UNIT * 2
        painter.setPen(QPen(QColor(COLORS["text_bright"]), 2))
        painter.drawLine(
            QPointF(price_rect.right() - UNIT * 31, legend_y),
            QPointF(price_rect.right() - UNIT * 28, legend_y),
        )
        painter.setPen(QColor(COLORS["text_muted"]))
        painter.drawText(
            QRectF(
                price_rect.right() - UNIT * 27,
                legend_y - UNIT,
                UNIT * 10,
                UNIT * 2,
            ),
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter,
            "AVERAGE",
        )
        painter.fillRect(
            QRectF(
                price_rect.right() - UNIT * 16,
                legend_y - 3,
                UNIT * 3,
                6,
            ),
            range_fill,
        )
        painter.drawText(
            QRectF(
                price_rect.right() - UNIT * 12,
                legend_y - UNIT,
                UNIT * 12,
                UNIT * 2,
            ),
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter,
            "LOW / HIGH",
        )
        self._draw_outline(painter)
        painter.end()

        self._static_cache = cache
        self._cache_geometry = (
            price_rect,
            volume_rect,
            price_min,
            price_max,
        )
        self._cache_key = self._static_cache_key()

    def _hover_geometry(self, index):
        if (
            index is None
            or not self._history
            or self._cache_geometry is None
        ):
            return None

        price_rect, volume_rect, price_min, price_max = self._cache_geometry
        day = self._history[index]
        count = len(self._history)
        x = self._x_for_index(price_rect, index, count)
        average_y = self._y_for_value(
            price_rect,
            float(day["average"]),
            price_min,
            price_max,
        )
        lines = [
            day["date"],
            f"Average  {day['average']:,.2f} ISK",
            f"Low      {day['lowest']:,.2f} ISK",
            f"High     {day['highest']:,.2f} ISK",
            f"Volume   {day['volume']:,}",
        ]
        metrics = self.fontMetrics()
        tooltip_width = max(
            metrics.horizontalAdvance(line)
            for line in lines
        ) + UNIT * 3
        tooltip_height = (
            len(lines) * (metrics.height() + 2)
            + UNIT * 2
        )
        tooltip_x = x + UNIT * 2

        if tooltip_x + tooltip_width > price_rect.right():
            tooltip_x = x - tooltip_width - UNIT * 2

        tooltip_x = max(price_rect.left(), tooltip_x)
        tooltip_rect = QRectF(
            tooltip_x,
            price_rect.top() + UNIT,
            tooltip_width,
            tooltip_height,
        )
        line_rect = QRectF(
            x - 3,
            price_rect.top(),
            6,
            volume_rect.bottom() - price_rect.top(),
        )
        dirty_rect = line_rect.united(
            tooltip_rect.adjusted(-2, -2, 2, 2)
        )

        return x, average_y, tooltip_rect, lines, dirty_rect

    def _update_hover_regions(self, old_index, new_index):
        dirty = None

        for index in (old_index, new_index):
            geometry = self._hover_geometry(index)

            if geometry is None:
                continue

            rect = geometry[4]
            dirty = rect if dirty is None else dirty.united(rect)

        if dirty is None:
            self.update()
        else:
            self.update(dirty.toAlignedRect())

    def _draw_hover(self, painter):
        if (
            self._hover_index is None
            or not self._history
            or self._cache_geometry is None
        ):
            return

        geometry = self._hover_geometry(self._hover_index)

        if geometry is None:
            return

        x, average_y, tooltip_rect, lines, _dirty_rect = geometry
        price_rect, volume_rect, _price_min, _price_max = self._cache_geometry

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )
        painter.setPen(QPen(QColor(COLORS["line_bright"]), 1))
        painter.drawLine(
            QPointF(x, price_rect.top()),
            QPointF(x, volume_rect.bottom()),
        )
        painter.setBrush(QColor(COLORS["text_bright"]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(x, average_y), 3, 3)

        metrics = painter.fontMetrics()

        painter.setBrush(QColor(COLORS["panel_raised"]))
        painter.setPen(QPen(QColor(COLORS["line_bright"]), 1))
        painter.drawRect(tooltip_rect)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(COLORS["text"]))

        text_y = tooltip_rect.top() + UNIT
        line_height = metrics.height() + 2

        for line in lines:
            painter.drawText(
                QRectF(
                    tooltip_rect.left() + UNIT,
                    text_y,
                    tooltip_rect.width() - UNIT * 2,
                    line_height,
                ),
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter,
                line,
            )
            text_y += line_height

    def paintEvent(self, event):
        key = self._static_cache_key()

        if self._static_cache is None:
            self._build_static_cache()
        elif self._cache_key != key:
            if not self._resize_cache_timer.isActive():
                self._build_static_cache()

        painter = QPainter(self)

        if self._cache_key == key:
            painter.drawPixmap(0, 0, self._static_cache)
            self._draw_hover(painter)
        else:
            # Keep resize interaction responsive by stretching the previous
            # cached frame until the short resize debounce expires.
            painter.drawPixmap(
                self.rect(),
                self._static_cache,
            )


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
        self._standard_scope = "system"

        control_panel = PhotonToolStrip()

        row = QHBoxLayout()
        row.setSpacing(UNIT)

        self.category_filter = TypeCategoryFilter(
            published_only=True,
            accessible_name="Market item category filter",
        )

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

        self.item_suggestions = KeywordSuggestions(
            self.item_input,
            lambda query, limit: search_types(
                query,
                limit=limit,
                published_only=True,
                category_id=self.category_filter.currentData(),
            ),
            accessible_name="Market item suggestions",
        )
        self.location_suggestions = KeywordSuggestions(
            self.location_input,
            self._search_location_suggestions,
            accessible_name="Market location suggestions",
        )

        row.addWidget(
            self.category_filter
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

        (
            self.sell_orders_table,
            self.sell_orders_model,
        ) = self._build_orders_table(
            "Sell orders"
        )
        sell_orders_panel = MarketOrderPanel(
            "SELL ORDERS",
            self.sell_orders_table,
        )

        (
            self.buy_orders_table,
            self.buy_orders_model,
        ) = self._build_orders_table(
            "Buy orders"
        )
        buy_orders_panel = MarketOrderPanel(
            "BUY ORDERS",
            self.buy_orders_table,
        )

        self.orders_splitter = QSplitter(
            Qt.Orientation.Vertical
        )
        self.orders_splitter.setObjectName(
            "MarketOrdersSplitter"
        )
        self.orders_splitter.setChildrenCollapsible(False)
        self.orders_splitter.setHandleWidth(UNIT * 3)
        # The model-backed order tables are cheap to relayout, so resize
        # the panes directly while the divider is dragged.
        self.orders_splitter.setOpaqueResize(True)
        self.orders_splitter.addWidget(sell_orders_panel)
        self.orders_splitter.addWidget(buy_orders_panel)
        self.orders_splitter.setStretchFactor(0, 1)
        self.orders_splitter.setStretchFactor(1, 1)
        self.orders_splitter.setSizes([1, 1])

        orders_layout.addWidget(
            self.orders_splitter,
            1,
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

        self.history_views = QTabWidget()
        self.history_views.setAccessibleName(
            "Market history view mode"
        )
        self.history_views.setDocumentMode(True)
        self.history_views.tabBar().setExpanding(False)
        self.history_views.tabBar().setUsesScrollButtons(False)
        self.history_views.setElideMode(Qt.TextElideMode.ElideNone)

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
        self.history_table.setObjectName("MarketHistoryTable")
        self.history_table.setAccessibleName(
            "Market history table"
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

        self.history_graph = MarketHistoryGraph()

        self.history_views.addTab(
            self.history_table,
            "TABLE",
        )
        self.history_views.addTab(
            self.history_graph,
            "GRAPH",
        )
        history_layout.addWidget(
            self.history_views
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
        self.reachable_table.setObjectName("MarketReachableTable")
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
        self.tabs.setTabVisible(
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
        self.item_input.textChanged.connect(
            self._sync_global_scope_option
        )
        self.category_filter.currentIndexChanged.connect(
            self._category_changed
        )
        self.location_input.textEdited.connect(
            self._invalidate_query
        )
        self.scope.currentIndexChanged.connect(
            self._scope_changed
        )
        self.item_suggestions.completer.activated.connect(
            lambda _text: self._invalidate_query()
        )
        self.location_suggestions.completer.activated.connect(
            lambda _text: self._invalidate_query()
        )

        self._update_scope_controls()

        if not sde.is_ready():
            self.category_filter.setEnabled(False)
            self.item_input.setEnabled(False)
            self.scope.setEnabled(False)
            self.location_input.setEnabled(False)
            self.load_button.setEnabled(False)
            self.status.set_status(
                "SDE database is not ready",
                "error",
            )

    def _build_orders_table(self, accessible_name):
        model = MarketOrdersModel(self)
        table = WeightedTableView(
            4,
            weights=[
                20,
                16,
                48,
                16,
            ],
            minimum_widths=[
                UNIT * 12,
                UNIT * 12,
                UNIT * 28,
                UNIT * 11,
            ],
        )
        table.setModel(model)
        table.setAccessibleName(accessible_name)
        table.horizontalHeader().setDefaultAlignment(ALIGN_LEFT)
        table.verticalHeader().setVisible(False)
        table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        table.setAlternatingRowColors(True)
        return table, model

    def _category_changed(self, _index=None):
        self._invalidate_query()
        self._sync_global_scope_option()
        self.item_suggestions.refresh()

    def _item_query_is_plex(self):
        query = self.item_input.text().strip()

        if (
            query.casefold() != "plex"
            and query != str(PLEX_TYPE_ID)
        ):
            return False

        if not sde.is_ready():
            return False

        item = resolve_type(
            query,
            category_id=self.category_filter.currentData(),
        )

        return (
            item is not None
            and is_global_market_type(item["type_id"])
        )

    def _sync_global_scope_option(self, _text=None):
        show_global = self._item_query_is_plex()
        global_index = self.scope.findData("global")

        if show_global:
            if global_index < 0:
                self.scope.addItem(
                    "GLOBAL",
                    "global",
                )
                global_index = self.scope.findData("global")

            current_scope = self.scope.currentData()

            if current_scope in ("system", "region"):
                self._standard_scope = current_scope

            if current_scope != "global":
                self.scope.setCurrentIndex(global_index)

            return

        if global_index < 0:
            return

        if self.scope.currentData() == "global":
            standard_index = self.scope.findData(
                self._standard_scope
            )

            if standard_index < 0:
                standard_index = self.scope.findData("system")

            if standard_index >= 0:
                self.scope.setCurrentIndex(standard_index)

        global_index = self.scope.findData("global")

        if global_index >= 0:
            self.scope.removeItem(global_index)

        self._update_scope_controls()

    def _search_location_suggestions(
        self,
        query,
        limit,
    ):
        scope = self.scope.currentData()

        if scope == "system":
            return search_systems(
                query,
                limit=limit,
            )

        if scope == "region":
            return search_regions(
                query,
                limit=limit,
            )

        return []

    def _update_scope_controls(self):
        is_global = self.scope.currentData() == "global"

        self.location_input.setEnabled(
            not is_global and sde.is_ready()
        )
        self.location_input.setPlaceholderText(
            "Not required for global PLEX market"
            if is_global
            else "System or region name or ID"
        )

        if is_global:
            self.location_input.clear()
            self.location_suggestions.completer.popup().hide()

    def _sync_reachable_tab(self):
        available = (
            self._selection is not None
            and self._selection.get("scope") == "system"
        )

        if not available and self.tabs.currentIndex() == 2:
            self.tabs.setCurrentIndex(0)

        self.tabs.setTabVisible(2, available)

    def _scope_changed(self, _index=None):
        scope = self.scope.currentData()

        if scope in ("system", "region"):
            self._standard_scope = scope

        self._update_scope_controls()
        self._invalidate_query()
        self._sync_reachable_tab()
        self.location_suggestions.refresh()

    def _set_scope(self, scope):
        index = self.scope.findData(scope)

        if index >= 0 and index != self.scope.currentIndex():
            self.scope.setCurrentIndex(index)

    def _invalidate_query(self):
        if self._selection is None:
            return

        self._generation += 1
        self._selection = None
        self._loaded_tabs.clear()
        self._sync_reachable_tab()
        self.status.set_status(
            "Query changed   press LOAD to refresh"
        )

    def load_query(self):
        item_query = self.item_input.text().strip()

        if not item_query:
            self.status.set_status(
                "Item is required",
                "warning",
            )
            return

        item = resolve_type(
            item_query,
            category_id=self.category_filter.currentData(),
        )

        if item is None:
            self.status.set_status(
                f'No item found matching "{item_query}"',
                "warning",
            )
            return

        scope = self.scope.currentData()

        # PLEX has its own ESI market region, so regional/system queries
        # would incorrectly look empty. Selecting PLEX always uses it.
        if is_global_market_type(item["type_id"]):
            self._sync_global_scope_option()

            if self.scope.findData("global") < 0:
                self.scope.addItem(
                    "GLOBAL",
                    "global",
                )

            if scope != "global":
                self._set_scope("global")

            scope = "global"

        elif scope == "global":
            self.status.set_status(
                "Global market is only available for PLEX",
                "warning",
            )
            return

        location_query = self.location_input.text().strip()

        if scope != "global" and not location_query:
            self.status.set_status(
                "Location is required for system or region scope",
                "warning",
            )
            return

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

        elif scope == "region":
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

        else:
            selection = {
                "type_id": item["type_id"],
                "item_name": item["name"],
                "system_id": None,
                "system_name": None,
                "region_id": GLOBAL_PLEX_REGION_ID,
                "region_name": GLOBAL_MARKET_NAME,
                "scope": "global",
            }

        self._generation += 1
        self._selection = selection
        self._loaded_tabs.clear()
        self._clear_tables()
        self._sync_reachable_tab()

        self._load_tab(
            self.tabs.currentIndex()
        )

    def _clear_tables(self):
        self.sell_orders_model.clear()
        self.buy_orders_model.clear()
        self.history_table.setRowCount(0)
        self.history_graph.clear()
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
                f"Market request failed     {exception}",
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

        if selection["scope"] == "system":
            location = selection["system_name"]
        else:
            location = selection["region_name"]

        counts = {
            0: (
                self.sell_orders_model.rowCount()
                + self.buy_orders_model.rowCount()
            ),
            1: self.history_table.rowCount(),
            2: self.reachable_table.rowCount(),
        }
        labels = {
            0: "orders",
            1: "history days",
            2: "reachable buy orders",
        }

        self.status.set_status(
            f"{selection['item_name']}     {location}     "
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
        self.sell_orders_model.set_orders(
            sell_orders,
            names,
        )
        self.buy_orders_model.set_orders(
            buy_orders,
            names,
        )

    def _history_loaded(self, history):
        history = sorted(
            history,
            key=lambda day: day["date"],
        )
        self.history_graph.set_history(history)
        table_history = list(reversed(history))

        table = self.history_table
        table.setUpdatesEnabled(False)

        try:
            table.setRowCount(len(table_history))

            for row_index, day in enumerate(table_history):
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
