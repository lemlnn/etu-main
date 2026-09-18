"""main photon-inspired desktop shell"""

from importlib.metadata import (
    PackageNotFoundError,
    version,
)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from etu import sde
from etu.gui.pages.inventory import (
    InventoryPage,
)
from etu.gui.pages.market import MarketPage
from etu.gui.pages.navigation import (
    NavigationPage,
)
from etu.gui.pages.settings import SettingsPage
from etu.gui.pages.universe import UniversePage
from etu.gui.theme import COLORS, UNIT
from etu.gui.widgets import GridBackdrop


def get_version():
    try:
        return version("etu")
    except PackageNotFoundError:
        return "dev"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ETU")
        self.resize(
            UNIT * 180,
            UNIT * 108,
        )
        self.setMinimumSize(
            UNIT * 80,
            UNIT * 60,
        )

        self.pages = QStackedWidget()
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.page_titles = []

        root = QWidget()
        root.setObjectName("Root")

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        root_layout.setSpacing(0)

        rail = self._build_rail()
        workspace = self._build_workspace()

        root_layout.addWidget(rail)
        root_layout.addWidget(
            workspace,
            1,
        )

        self.setCentralWidget(root)

        self.nav_group.idClicked.connect(
            self.select_page
        )

        first = self.nav_group.button(0)
        if first is not None:
            first.setChecked(True)

        self.select_page(0)

    def _build_rail(self):
        rail = QFrame()
        rail.setObjectName("Rail")
        rail.setFixedWidth(UNIT * 7)

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(
            UNIT,
            UNIT,
            UNIT,
            UNIT,
        )
        layout.setSpacing(0)

        brand = QLabel("ETU")
        brand.setObjectName("Brand")
        brand.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(brand)
        layout.addSpacing(UNIT)

        inventory_page = InventoryPage()
        settings_page = SettingsPage()

        settings_page.inventory_settings_changed.connect(
            inventory_page.refresh_search_preferences
        )

        self._add_page(
            layout,
            "I",
            "Inventory",
            inventory_page,
        )
        self._add_page(
            layout,
            "U",
            "Universe",
            UniversePage(),
        )
        self._add_page(
            layout,
            "M",
            "Market",
            MarketPage(),
        )
        self._add_page(
            layout,
            "N",
            "Navigation",
            NavigationPage(),
        )

        layout.addStretch()

        self._add_page(
            layout,
            "S",
            "Settings",
            settings_page,
        )

        return rail

    def _build_workspace(self):
        workspace = QWidget()

        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        layout.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("TopBar")
        topbar.setFixedHeight(UNIT * 5)

        topbar_layout = QHBoxLayout(
            topbar
        )
        topbar_layout.setContentsMargins(
            UNIT,
            0,
            UNIT,
            0,
        )
        topbar_layout.setSpacing(UNIT)

        marker = QFrame()
        marker.setObjectName("TitleMarker")
        marker.setFixedSize(
            2,
            UNIT * 2,
        )

        self.page_title = QLabel(
            "Inventory"
        )
        self.page_title.setObjectName(
            "PageTitle"
        )

        topbar_layout.addWidget(marker)
        topbar_layout.addWidget(
            self.page_title
        )
        topbar_layout.addStretch()

        backdrop = GridBackdrop()

        backdrop_layout = QVBoxLayout(
            backdrop
        )
        backdrop_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        backdrop_layout.addWidget(
            self.pages
        )

        statusbar = QFrame()
        statusbar.setObjectName(
            "StatusBar"
        )
        statusbar.setFixedHeight(
            UNIT * 3
        )

        status_layout = QHBoxLayout(
            statusbar
        )
        status_layout.setContentsMargins(
            UNIT,
            0,
            UNIT,
            0,
        )

        left = QLabel(
            f"ETU dev-{get_version()}"
        )
        left.setObjectName("StatusText")

        status_layout.addWidget(left)
        status_layout.addStretch()

        layout.addWidget(topbar)
        layout.addWidget(
            backdrop,
            1,
        )
        layout.addWidget(statusbar)

        return workspace

    def _add_page(
        self,
        layout,
        glyph,
        name,
        page,
    ):
        index = self.pages.count()

        button = QPushButton(glyph)
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.setToolTip(name)
        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.nav_group.addButton(
            button,
            index,
        )

        self.pages.addWidget(page)
        self.page_titles.append(name)

        layout.addWidget(button)

    def select_page(self, index):
        self.pages.setCurrentIndex(index)

        name = self.page_titles[index]

        self.page_title.setText(name)
