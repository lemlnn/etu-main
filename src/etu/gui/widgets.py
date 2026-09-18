"""small reusable photon-style gui primitives"""

from PySide6.QtCore import QObject, QRunnable, Signal, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableView,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from etu.gui.theme import COLORS, UNIT


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(object)
    finished = Signal()


class FunctionWorker(QRunnable):
    def __init__(
        self,
        function,
        *args,
        **kwargs,
    ):
        super().__init__()

        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.function(
                *self.args,
                **self.kwargs,
            )

        except Exception as error:
            self.signals.error.emit(error)

        else:
            self.signals.result.emit(result)

        finally:
            self.signals.finished.emit()


class StatusLabel(QLabel):
    def __init__(
        self,
        text="",
        parent=None,
    ):
        super().__init__(text, parent)
        self.setObjectName("StatusText")
        self.setAccessibleName("Status")
        self.setWordWrap(True)
        self.set_status(text)

    def set_status(
        self,
        text,
        kind="normal",
    ):
        text = str(text)
        self.setText(text)
        self.setAccessibleDescription(text)
        self.setVisible(bool(text))
        self.setProperty(
            "statusKind",
            kind,
        )
        self.style().unpolish(self)
        self.style().polish(self)



class GridBackdrop(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(
            self.rect(),
            QColor(COLORS["void"]),
        )


class PhotonPanel(QFrame):
    def __init__(
        self,
        title,
        meta=None,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("Panel")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("PanelHeader")
        header.setFixedHeight(UNIT * 3)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(
            UNIT,
            0,
            UNIT,
            0,
        )
        header_layout.setSpacing(UNIT)

        title_label = QLabel(title)
        title_label.setObjectName("PanelTitle")

        header_layout.addWidget(title_label)
        header_layout.addStretch()

        if meta:
            meta_label = QLabel(meta)
            meta_label.setObjectName("PanelMeta")
            header_layout.addWidget(meta_label)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(
            UNIT,
            UNIT,
            UNIT,
            UNIT,
        )
        self.body_layout.setSpacing(UNIT)

        root.addWidget(header)
        root.addWidget(self.body, 1)


class PhotonToolStrip(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolStrip")

        self.body_layout = QVBoxLayout(self)
        self.body_layout.setContentsMargins(
            UNIT,
            UNIT,
            UNIT,
            UNIT,
        )
        self.body_layout.setSpacing(UNIT)



def panel_splitter(
    *panels,
    sizes=None,
    orientation=Qt.Orientation.Horizontal,
):
    """build a panel splitter with one consistent divider between panes"""

    splitter = QSplitter(orientation)
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(1)

    panel_count = len(panels)

    for index, panel in enumerate(panels):
        if panel_count == 1:
            edge = "single"

        elif index == 0:
            edge = "first"

        elif index == panel_count - 1:
            edge = "last"

        else:
            edge = "middle"

        panel.setProperty(
            "splitEdge",
            edge,
        )
        panel.setProperty(
            "splitAxis",
            "horizontal"
            if orientation == Qt.Orientation.Horizontal
            else "vertical",
        )
        splitter.addWidget(panel)

    if sizes:
        splitter.setSizes(sizes)

    return splitter


class _WeightedTableMixin:
    """Shared responsive column sizing for item- and model-backed tables."""

    def _init_weighted_table(
        self,
        columns,
        weights=None,
        minimum_widths=None,
    ):
        self._weighted_column_count = columns
        self._column_weights = list(
            weights or [1] * columns
        )
        self._minimum_widths = list(
            minimum_widths or [1] * columns
        )

        if len(self._column_weights) != columns:
            raise ValueError(
                "column weight count must match table column count"
            )

        if len(self._minimum_widths) != columns:
            raise ValueError(
                "minimum width count must match table column count"
            )

        self.setContentsMargins(0, 0, 0, 0)
        self.setViewportMargins(0, 0, 0, 0)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(0)
        self.setMidLineWidth(0)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self._programmatic_resize = False

        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsMovable(False)
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        header.setSectionResizeMode(
            columns - 1,
            QHeaderView.ResizeMode.Fixed,
        )
        header.setMinimumSectionSize(1)
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        header.setTextElideMode(Qt.TextElideMode.ElideRight)
        header.sectionResized.connect(
            self._on_section_resized
        )

    def set_column_weights(self, weights):
        if len(weights) != self._weighted_column_count:
            raise ValueError(
                "column weight count must match table column count"
            )

        self._column_weights = list(weights)
        self._resize_weighted_columns()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_weighted_columns()

    def showEvent(self, event):
        super().showEvent(event)
        self._resize_weighted_columns()

    def _on_section_resized(
        self,
        column,
        old_width,
        new_width,
    ):
        if self._programmatic_resize:
            return

        if column >= self._weighted_column_count - 1:
            return

        available_width = (
            self.horizontalHeader()
            .viewport()
            .width()
        )

        if available_width <= 0:
            return

        minimum_width = self._minimum_widths[column]
        minimum_total = sum(self._minimum_widths)

        if available_width <= minimum_total:
            self._programmatic_resize = True
            try:
                self.setColumnWidth(
                    column,
                    max(minimum_width, new_width),
                )
            finally:
                self._programmatic_resize = False
            return

        max_width = (
            available_width
            - sum(self._minimum_widths[column + 1:])
            - sum(
                self.columnWidth(index)
                for index in range(column)
            )
        )
        clamped_width = max(
            minimum_width,
            min(new_width, max_width),
        )
        delta = clamped_width - old_width

        self._programmatic_resize = True
        try:
            if clamped_width != new_width:
                self.setColumnWidth(column, clamped_width)

            if delta > 0:
                remaining = delta

                for other in range(
                    column + 1,
                    self._weighted_column_count,
                ):
                    current = self.columnWidth(other)
                    minimum = self._minimum_widths[other]
                    available = max(0, current - minimum)
                    take = min(available, remaining)

                    if take:
                        self.setColumnWidth(
                            other,
                            current - take,
                        )
                        remaining -= take

                    if remaining <= 0:
                        break

                if remaining > 0:
                    self.setColumnWidth(
                        column,
                        clamped_width - remaining,
                    )

            elif delta < 0:
                other = column + 1
                self.setColumnWidth(
                    other,
                    self.columnWidth(other) - delta,
                )

        finally:
            self._programmatic_resize = False

        self._column_weights = [
            max(
                1,
                self.columnWidth(index)
                - self._minimum_widths[index],
            )
            for index in range(self._weighted_column_count)
        ]

    def _resize_weighted_columns(self):
        if not self._column_weights:
            return

        available_width = (
            self.horizontalHeader()
            .viewport()
            .width()
        )

        if available_width <= 0:
            return

        minimum_total = sum(self._minimum_widths)

        if available_width <= minimum_total:
            widths = list(self._minimum_widths)
        else:
            remaining_width = available_width - minimum_total
            total_weight = sum(self._column_weights)

            if total_weight <= 0:
                return

            widths = []
            used_width = 0
            last_column = self._weighted_column_count - 1

            for column, (weight, minimum_width) in enumerate(
                zip(self._column_weights, self._minimum_widths)
            ):
                if column == last_column:
                    width = max(
                        minimum_width,
                        available_width - used_width,
                    )
                else:
                    extra_width = int(
                        remaining_width * weight / total_weight
                    )
                    width = minimum_width + extra_width
                    used_width += width

                widths.append(width)

        self._programmatic_resize = True
        try:
            for column, width in enumerate(widths):
                self.setColumnWidth(column, width)
        finally:
            self._programmatic_resize = False


class WeightedTableWidget(_WeightedTableMixin, QTableWidget):
    """Responsive item-backed table with sane column minimums."""

    def __init__(
        self,
        rows,
        columns,
        weights=None,
        minimum_widths=None,
        parent=None,
    ):
        super().__init__(rows, columns, parent)
        self._init_weighted_table(
            columns,
            weights,
            minimum_widths,
        )


class WeightedTableView(_WeightedTableMixin, QTableView):
    """Responsive model-backed table using the same geometry as ETU tables."""

    def __init__(
        self,
        columns,
        weights=None,
        minimum_widths=None,
        parent=None,
    ):
        super().__init__(parent)
        self._init_weighted_table(
            columns,
            weights,
            minimum_widths,
        )


class CutButton(QPushButton):
    def __init__(
        self,
        text,
        parent=None,
    ):
        super().__init__(text, parent)

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        # custom-painted buttons use the same outer height as styled text fields
        self.setMinimumHeight(30)

        text_width = self.fontMetrics().horizontalAdvance(
            text
        )
        self.setMinimumWidth(
            max(
                UNIT * 9,
                text_width + (UNIT * 2) + 2,
            )
        )
        self.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed,
        )

        self.setStyleSheet(
            "background: transparent; border: 0;"
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            False,
        )

        rect = self.rect().adjusted(
            0,
            0,
            -1,
            -1,
        )

        cut = UNIT

        path = QPainterPath()
        path.moveTo(rect.left(), rect.top())
        path.lineTo(
            rect.right() - cut,
            rect.top(),
        )
        path.lineTo(
            rect.right(),
            rect.top() + cut,
        )
        path.lineTo(
            rect.right(),
            rect.bottom(),
        )
        path.lineTo(
            rect.left(),
            rect.bottom(),
        )
        path.closeSubpath()

        if not self.isEnabled():
            fill = COLORS["panel"]
            border = COLORS["line"]
            text = COLORS["text_disabled"]

        elif self.isDown():
            fill = COLORS["accent_dim"]
            border = COLORS["accent_bright"]
            text = COLORS["text_bright"]

        elif self.hasFocus():
            fill = COLORS["panel_hover"]
            border = COLORS["accent"]
            text = COLORS["text_bright"]

        elif self.underMouse():
            fill = COLORS["panel_hover"]
            border = COLORS["accent"]
            text = COLORS["text_bright"]

        else:
            fill = COLORS["panel_raised"]
            border = COLORS["line"]
            text = COLORS["text"]

        painter.fillPath(
            path,
            QColor(fill),
        )

        painter.setPen(
            QPen(
                QColor(border),
                1,
            )
        )
        painter.drawPath(path)

        painter.setPen(
            QColor(text)
        )
        painter.setFont(
            self.font()
        )
        painter.drawText(
            rect.adjusted(
                UNIT,
                0,
                -UNIT,
                0,
            ),
            Qt.AlignmentFlag.AlignCenter,
            self.text(),
        )


class DetailRow(QWidget):
    def __init__(
        self,
        label,
        value="-",
        wrap=False,
        parent=None,
    ):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UNIT)

        label_widget = QLabel(label.upper())
        label_widget.setObjectName("SectionLabel")
        label_widget.setFixedWidth(UNIT * 15)

        self.value_widget = QLabel(str(value))
        self.value_widget.setObjectName("Value")
        self.value_widget.setWordWrap(wrap)
        self.value_widget.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout.addWidget(label_widget)
        layout.addWidget(self.value_widget, 1)

    def set_value(self, value):
        self.value_widget.setText(str(value))
