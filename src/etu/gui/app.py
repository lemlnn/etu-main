"""qt application bootstrap for etu"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

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

    return app.exec()
