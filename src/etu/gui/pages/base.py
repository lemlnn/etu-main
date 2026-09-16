"""shared page framing for the etu gui"""

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from etu.gui.theme import UNIT
from etu.gui.widgets import FunctionWorker


class BasePage(QWidget):
    def __init__(
        self,
        title,
        subtitle=None,
        source=None,
        parent=None,
    ):
        super().__init__(parent)

        self.page_title = title
        self.setAccessibleName(f"{title} page")
        self._workers = set()
        self._thread_pool = QThreadPool.globalInstance()

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(
            UNIT,
            UNIT,
            UNIT,
            UNIT,
        )
        self.root_layout.setSpacing(UNIT)

    def run_task(
        self,
        function,
        on_result,
        on_error=None,
        on_finished=None,
        *args,
        **kwargs,
    ):
        worker = FunctionWorker(
            function,
            *args,
            **kwargs,
        )

        self._workers.add(worker)

        worker.signals.result.connect(
            on_result
        )

        if on_error is not None:
            worker.signals.error.connect(
                on_error
            )

        def finished():
            self._workers.discard(worker)

            if on_finished is not None:
                on_finished()

        worker.signals.finished.connect(
            finished
        )

        self._thread_pool.start(worker)
        return worker
