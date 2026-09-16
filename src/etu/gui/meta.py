"""meta-group tag assets and inventory-list rendering"""

from functools import cache
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QIcon, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)


META_GROUP_ROLE = (
    int(Qt.ItemDataRole.UserRole) + 1
)

ASSET_DIR = (
    Path(__file__).resolve().parent
    / "assets"
    / "meta"
)

META_TAGS = {
    2: ("Tech II", "tech_ii.png"),
    3: ("Storyline", "storyline.png"),
    4: ("Faction", "faction.png"),
    5: ("Officer", "officer.png"),
    6: ("Deadspace", "deadspace.png"),
    14: ("Tech III", "tech_iii.png"),
    15: ("Abyssal", "abyssal.png"),
    17: ("Premium", "premium.png"),
    19: ("Limited Time", "limited_time.png"),
    52: (
        "Structure Faction",
        "structure_faction.png",
    ),
    53: (
        "Structure Tech II",
        "structure_tech_ii.png",
    ),
    54: (
        "Structure Tech I",
        "structure_tech_i.png",
    ),
}


def meta_group_name(
    meta_group_id: int | None,
) -> str | None:
    if meta_group_id is None:
        return None

    tag = META_TAGS.get(meta_group_id)

    if tag is None:
        return None

    return tag[0]


@cache
def meta_tag_pixmap(
    meta_group_id: int | None,
) -> QPixmap:
    if meta_group_id is None:
        return QPixmap()

    tag = META_TAGS.get(meta_group_id)

    if tag is None:
        return QPixmap()

    path = ASSET_DIR / tag[1]

    if not path.exists():
        return QPixmap()

    return QPixmap(str(path))


class MetaTagDelegate(QStyledItemDelegate):
    """draw native-size eve meta tags at the leading edge of inventory rows"""

    TAG_LEFT = 4
    TEXT_LEFT = 8
    TAG_TEXT_GAP = 2
    RIGHT_PADDING = 8
    MINIMUM_HEIGHT = 22

    def paint(
        self,
        painter,
        option,
        index,
    ):
        style_option = QStyleOptionViewItem(
            option
        )
        self.initStyleOption(
            style_option,
            index,
        )

        text = style_option.text
        style_option.text = ""
        style_option.icon = QIcon()

        style = (
            style_option.widget.style()
            if style_option.widget is not None
            else QApplication.style()
        )

        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            style_option,
            painter,
            style_option.widget,
        )

        meta_group_id = index.data(
            META_GROUP_ROLE
        )
        tag = meta_tag_pixmap(
            meta_group_id
        )

        text_left = (
            option.rect.left()
            + self.TEXT_LEFT
        )

        if not tag.isNull():
            tag_x = (
                option.rect.left()
                + self.TAG_LEFT
            )
            tag_y = (
                option.rect.top()
                + max(
                    0,
                    (
                        option.rect.height()
                        - tag.height()
                    )
                    // 2,
                )
            )

            painter.drawPixmap(
                tag_x,
                tag_y,
                tag,
            )

            text_left = (
                tag_x
                + tag.width()
                + self.TAG_TEXT_GAP
            )

        text_rect = QRect(
            text_left,
            option.rect.top(),
            max(
                0,
                option.rect.right()
                - text_left
                - self.RIGHT_PADDING
                + 1,
            ),
            option.rect.height(),
        )

        selected = bool(
            option.state
            & QStyle.StateFlag.State_Selected
        )

        role = (
            QPalette.ColorRole.HighlightedText
            if selected
            else QPalette.ColorRole.Text
        )

        painter.save()
        painter.setPen(
            option.palette.color(role)
        )
        painter.setFont(option.font)

        display_text = (
            option.fontMetrics.elidedText(
                str(text),
                Qt.TextElideMode.ElideRight,
                text_rect.width(),
            )
        )

        painter.drawText(
            text_rect,
            int(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
            ),
            display_text,
        )
        painter.restore()

    def sizeHint(
        self,
        option,
        index,
    ) -> QSize:
        hint = super().sizeHint(
            option,
            index,
        )
        tag = meta_tag_pixmap(
            index.data(META_GROUP_ROLE)
        )

        return QSize(
            hint.width(),
            max(
                hint.height(),
                tag.height(),
                self.MINIMUM_HEIGHT,
            ),
        )
