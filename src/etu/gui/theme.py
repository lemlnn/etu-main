"""caldari-inspired photon theme tokens and qt styling"""

from pathlib import Path
import zipfile

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QFont, QFontDatabase


UNIT = 8

TYPE_SCALE = {
    "micro": 8,
    "small": 9,
    "body": 10,
    "label": 10,
    "title": 14,
    "brand": 16,
}

COLORS = {
    "void": "#070707",
    "base": "#0b0b0b",
    "panel": "#101010",
    "panel_raised": "#151515",
    "panel_hover": "#1b1b1b",
    "line": "#2b2b2b",
    "line_bright": "#5f5f5f",
    "accent": "#707070",
    "accent_bright": "#9a9a9a",
    "accent_dim": "#242424",
    "text": "#d0d0d0",
    "text_bright": "#ececec",
    "text_muted": "#9b9b9b",
    "text_disabled": "#666666",
    "success": "#b8b8b8",
    "warning": "#c4c4c4",
    "danger": "#d0d0d0",
}


def _load_bundled_jura() -> str | None:
    project_root = Path(__file__).resolve().parents[3]
    font_zip = project_root / "Jura.zip"

    if not font_zip.exists():
        return None

    try:
        with zipfile.ZipFile(font_zip) as archive:
            font_data = archive.read(
                "Jura-VariableFont_wght.ttf"
            )

    except (
        OSError,
        KeyError,
        zipfile.BadZipFile,
    ):
        return None

    font_id = QFontDatabase.addApplicationFontFromData(
        QByteArray(font_data)
    )

    if font_id == -1:
        return None

    families = QFontDatabase.applicationFontFamilies(
        font_id
    )

    if not families:
        return None

    return families[0]


def app_font() -> QFont:
    family = _load_bundled_jura()

    if family is None:
        families = set(
            QFontDatabase.families()
        )

        family = (
            "Jura"
            if "Jura" in families
            else "Sans Serif"
        )

    font = QFont(family)
    font.setPointSize(TYPE_SCALE["body"])
    font.setWeight(QFont.Weight.DemiBold)
    font.setHintingPreference(
        QFont.HintingPreference.PreferVerticalHinting
    )
    font.setStyleStrategy(
        QFont.StyleStrategy.PreferAntialias
    )

    return font


def stylesheet() -> str:
    c = COLORS
    t = TYPE_SCALE

    return f"""
    * {{
        outline: 0;
    }}

    QWidget {{
        color: {c["text"]};
        background: transparent;
        font-size: {t["body"]}pt;
    }}

    QMainWindow,
    QWidget#Root {{
        background: {c["void"]};
    }}

    QFrame#Rail {{
        background: {c["base"]};
        border-right: 1px solid {c["line"]};
    }}

    QFrame#TopBar {{
        background: {c["base"]};
        border: 0;
        border-bottom: 1px solid {c["line"]};
    }}

    QFrame#TitleMarker {{
        background: {c["line_bright"]};
        border: 0;
    }}

    QFrame#StatusBar {{
        background: {c["base"]};
        border-top: 1px solid {c["line"]};
    }}

    QLabel#Brand {{
        color: {c["text_bright"]};
        font-size: 15pt;
        font-weight: 700;
    }}

    QLabel#BrandSub {{
        color: {c["text_muted"]};
        font-size: {t["micro"]}pt;
        font-weight: 600;
    }}

    QLabel#PageTitle {{
        color: {c["text_bright"]};
        font-size: 11pt;
        font-weight: 600;
    }}

    QLabel#StatusText,
    QLabel#Muted {{
        color: {c["text_muted"]};
        font-size: {t["small"]}pt;
        font-weight: 600;
    }}

    QLabel#StatusText[statusKind="success"] {{
        color: {c["success"]};
    }}

    QLabel#StatusText[statusKind="warning"] {{
        color: {c["warning"]};
    }}

    QLabel#StatusText[statusKind="error"] {{
        color: {c["danger"]};
    }}

    QLabel#SectionLabel {{
        color: {c["text_muted"]};
        font-size: {t["small"]}pt;
        font-weight: 600;
    }}

    QLabel#DogmaGroupHeader {{
        background: {c["panel_raised"]};
        color: {c["text_bright"]};
        padding: 0 8px;
        font-size: {t["small"]}pt;
        font-weight: 600;
    }}

    QLabel#Value {{
        color: {c["text_bright"]};
    }}

    QFrame#Panel {{
        background: {c["panel"]};
        border: 0;
    }}

    QFrame#PanelHeader {{
        background: {c["panel_raised"]};
        border: 0;
        border-bottom: 1px solid {c["line"]};
    }}

    QLabel#PanelTitle {{
        color: {c["text"]};
        font-size: {t["small"]}pt;
        font-weight: 600;
    }}

    QLabel#PanelMeta {{
        color: {c["text_muted"]};
        font-size: {t["micro"]}pt;
        font-weight: 600;
    }}

    QFrame#ToolStrip {{
        background: {c["panel"]};
        border: 0;
        border-bottom: 1px solid {c["line"]};
    }}

    QPushButton#NavButton {{
        min-width: 40px;
        max-width: 40px;
        min-height: 40px;
        max-height: 40px;
        margin: 0;
        padding: 0;
        background: transparent;
        border: 0;
        border-left: 2px solid transparent;
        color: {c["text_muted"]};
        font-size: 10pt;
        font-weight: 600;
    }}

    QPushButton#NavButton:hover {{
        background: {c["panel_raised"]};
        color: {c["text_bright"]};
    }}

    QPushButton#NavButton:checked {{
        background: {c["panel_raised"]};
        border-left: 2px solid {c["accent_bright"]};
        color: {c["text_bright"]};
    }}

    QPushButton#NavButton:focus {{
        background: {c["panel_hover"]};
        border-left: 2px solid {c["accent"]};
        color: {c["text_bright"]};
    }}

    QPushButton#FlatButton {{
        min-height: 28px;
        padding: 0 10px;
        background: {c["panel_raised"]};
        border: 1px solid {c["line"]};
        color: {c["text"]};
    }}

    QPushButton#FlatButton:hover {{
        background: {c["panel_hover"]};
        border-color: {c["accent"]};
        color: {c["text_bright"]};
    }}

    QPushButton#FlatButton:pressed {{
        background: {c["accent_dim"]};
    }}

    QPushButton#FlatButton:focus {{
        background: {c["panel_hover"]};
        border-color: {c["accent"]};
        color: {c["text_bright"]};
    }}

    QPushButton#FlatButton:disabled {{
        background: {c["panel"]};
        border-color: {c["line"]};
        color: {c["text_disabled"]};
    }}

    QLineEdit,
    QComboBox,
    QSpinBox#SettingsNumber {{
        min-height: 28px;
        padding: 0 8px;
        background: {c["base"]};
        border: 1px solid {c["line"]};
        color: {c["text"]};
        selection-background-color: {c["accent_dim"]};
        selection-color: {c["text_bright"]};
    }}

    QLineEdit:hover,
    QComboBox:hover,
    QSpinBox#SettingsNumber:hover {{
        border-color: {c["line_bright"]};
    }}

    QLineEdit:focus,
    QComboBox:focus,
    QSpinBox#SettingsNumber:focus {{
        background: {c["panel"]};
        border-color: {c["accent"]};
        color: {c["text_bright"]};
    }}

    QLineEdit::placeholder {{
        color: {c["text_disabled"]};
    }}

    QCheckBox#SettingsToggle {{
        min-height: 28px;
        spacing: 8px;
        color: {c["text"]};
        font-size: {t["small"]}pt;
        font-weight: 600;
    }}

    QCheckBox#SettingsToggle::indicator {{
        width: 14px;
        height: 14px;
        background: {c["base"]};
        border: 1px solid {c["line_bright"]};
    }}

    QCheckBox#SettingsToggle::indicator:hover {{
        border-color: {c["accent_bright"]};
    }}

    QCheckBox#SettingsToggle::indicator:checked {{
        background: {c["accent_bright"]};
        border-color: {c["accent_bright"]};
    }}

    QCheckBox#SettingsToggle:focus {{
        color: {c["text_bright"]};
    }}

    QCheckBox#SettingsToggle:focus::indicator {{
        border-color: {c["text_bright"]};
    }}

    QComboBox::drop-down {{
        border: 0;
        width: 22px;
    }}

    QComboBox QAbstractItemView {{
        background: {c["panel_raised"]};
        border: 1px solid {c["line"]};
        color: {c["text"]};
        selection-background-color: {c["accent_dim"]};
    }}

    QAbstractItemView#SearchSuggestions {{
        background: {c["panel_raised"]};
        border: 1px solid {c["line"]};
        color: {c["text"]};
        selection-background-color: {c["accent_dim"]};
        selection-color: {c["text_bright"]};
    }}

    QAbstractItemView#SearchSuggestions::item {{
        min-height: 22px;
        padding: 0 8px;
        border: 0;
    }}

    QAbstractItemView#SearchSuggestions::item:hover {{
        background: {c["panel_hover"]};
        color: {c["text_bright"]};
    }}

    QTabWidget::pane {{
        border: 0;
        background: {c["panel"]};
    }}

    QTabBar {{
        background: {c["base"]};
    }}

    QTabBar::tab {{
        min-height: 26px;
        padding: 0 12px;
        margin: 0;
        background: transparent;
        border: 0;
        border-bottom: 2px solid transparent;
        color: {c["text_muted"]};
        font-size: {t["small"]}pt;
        font-weight: 600;
    }}

    QTabBar::tab:hover {{
        background: {c["panel_raised"]};
        color: {c["text"]};
    }}

    QTabBar::tab:selected {{
        background: {c["panel_raised"]};
        border-bottom: 2px solid {c["accent_bright"]};
        color: {c["text_bright"]};
    }}

    QListWidget,
    QTreeWidget,
    QTextBrowser {{
        background: {c["base"]};
        border: 0;
        color: {c["text"]};
    }}

    QListWidget,
    QTreeWidget {{
        alternate-background-color: {c["panel"]};
    }}

    QTableWidget {{
        background: {c["base"]};
        border: 0;
        alternate-background-color: {c["panel"]};
        gridline-color: {c["line"]};
        color: {c["text"]};
        padding: 0;
        margin: 0;
    }}

    QListWidget::item,
    QTreeWidget::item {{
        min-height: 22px;
        padding: 0 8px;
        border: 0;
    }}

    QListWidget::item:hover,
    QTreeWidget::item:hover {{
        background: {c["panel_hover"]};
    }}

    QListWidget::item:selected,
    QTreeWidget::item:selected {{
        background: {c["accent_dim"]};
        color: {c["text_bright"]};
    }}

    QHeaderView {{
        background: {c["panel_raised"]};
    }}

    QHeaderView::section {{
        min-height: 22px;
        padding: 0 8px;
        background: {c["panel_raised"]};
        border: 0;
        border-right: 1px solid {c["line"]};
        border-bottom: 1px solid {c["line"]};
        color: {c["text"]};
        font-size: {t["small"]}pt;
        font-weight: 600;
    }}

    QTableWidget::item {{
        min-height: 22px;
        padding: 1px 8px;
        border-bottom: 1px solid {c["line"]};
    }}

    QTableWidget::item:hover {{
        background: {c["panel_hover"]};
    }}

    QTableWidget::item:selected {{
        background: {c["accent_dim"]};
        color: {c["text_bright"]};
    }}

    QSplitter::handle {{
        background: {c["line"]};
    }}

    QSplitter::handle:hover {{
        background: {c["accent"]};
    }}

    QSplitter::handle:horizontal {{
        width: 1px;
    }}

    QSplitter::handle:vertical {{
        height: 1px;
    }}

    QScrollBar:vertical {{
        width: 6px;
        background: {c["base"]};
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        min-height: 28px;
        background: {c["line_bright"]};
    }}

    QScrollBar::handle:vertical:hover {{
        background: {c["accent"]};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        height: 6px;
        background: {c["base"]};
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        min-width: 28px;
        background: {c["line_bright"]};
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {c["accent"]};
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    QToolTip {{
        background: {c["panel_raised"]};
        border: 1px solid {c["line_bright"]};
        color: {c["text_bright"]};
        padding: 4px 6px;
    }}
    """
