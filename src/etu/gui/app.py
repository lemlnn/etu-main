"""qt application bootstrap for etu"""

import sys
from threading import Thread

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from etu import sde
from etu.gui.theme import (
    app_font,
    stylesheet,
)
from etu.gui.window import MainWindow


def main():
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ETU")
    app.setOrganizationName("ETU")
    app.setStyle("Fusion")
    app.setFont(app_font())
    app.setStyleSheet(stylesheet())

    window = MainWindow()
    window.show()

    # Build the common published-item/system/region tries after the window is
    # visible so the first live search does not pay the one-time index cost.
    Thread(
        target=sde.warm_search_indexes,
        name="etu-search-index-warmup",
        daemon=True,
    ).start()

    return app.exec()
