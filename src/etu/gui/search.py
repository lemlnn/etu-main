"""keyword search helpers and inline suggestion support shared by GUI pages"""

from PySide6.QtCore import (
    QObject,
    QSignalBlocker,
    QStringListModel,
    QTimer,
    Qt,
)
from etu import sde

from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QLineEdit,
)

from etu.inventory import (
    find_type_keywords,
    get_type,
    get_filterable_type_categories,
)
from etu.universe import (
    find_constellation_keywords,
    find_region_keywords,
    find_system_keywords,
    find_universe_keywords,
    get_constellation,
    get_region,
    get_system,
)


SEARCH_DEBOUNCE_MS = 250
CATEGORY_FILTER_VISIBLE_ROWS = 10

def _match_count(matches) -> int:
    if not matches:
        return 0

    return int(
        matches[0].get(
            "match_count",
            len(matches),
        )
    )

def search_types(
    query,
    limit=25,
    published_only=True,
    category_id=None,
):
    query = query.strip()

    if not query:
        return []

    if query.isdigit():
        item = get_type(int(query))

        if item is None:
            return []

        if published_only and not item.get("published"):
            return []

        if (
            category_id is not None
            and item.get("category_id") != int(category_id)
        ):
            return []

        item = dict(item)
        item["match_count"] = 1
        return [item]

    return find_type_keywords(
        query,
        limit=limit,
        published_only=published_only,
        category_id=category_id,
    )


def _universe_exact_result(kind, object_id):
    if kind == "system":
        data = sde.get_system(object_id)
        id_key = "system_id"

    elif kind == "constellation":
        data = sde.get_constellation(object_id)
        id_key = "constellation_id"

    elif kind == "region":
        data = sde.get_region_summary(object_id)
        id_key = "region_id"

    else:
        return None

    if data is None:
        return None

    result = dict(data)
    result["kind"] = kind
    result["object_id"] = result[id_key]
    result["match_count"] = 1
    return result

def _exact_result_matches_space(result, space):
    if not space:
        return True

    if result["kind"] == "system":
        return result.get("space_kind") == space

    return int(result.get(f"{space}_count", 0) or 0) > 0

def search_universe(
    query,
    limit=50,
    *,
    kind=None,
    space=None,
):
    query = query.strip()

    if not query:
        return []

    if query.isdigit():
        object_id = int(query)
        kinds = (kind,) if kind else (
            "system",
            "constellation",
            "region",
        )

        for candidate_kind in kinds:
            result = _universe_exact_result(
                candidate_kind,
                object_id,
            )

            if (
                result is not None
                and _exact_result_matches_space(result, space)
            ):
                return [result]

        return []

    return find_universe_keywords(
        query,
        limit=limit,
        kind=kind,
        space=space,
    )

def search_constellations(query, limit=25):
    query = query.strip()

    if not query:
        return []

    if query.isdigit():
        result = _universe_exact_result(
            "constellation",
            int(query),
        )
        return [result] if result else []

    return find_constellation_keywords(
        query,
        limit=limit,
    )

def search_systems(query, limit=25):
    query = query.strip()

    if not query:
        return []

    if query.isdigit():
        system = get_system(int(query))

        if system is None:
            return []

        system = dict(system)
        system["match_count"] = 1
        return [system]

    return find_system_keywords(
        query,
        limit=limit,
    )

def search_regions(query, limit=25):
    query = query.strip()

    if not query:
        return []

    if query.isdigit():
        region = get_region(int(query))

        if region is None:
            return []

        region = dict(region)
        region["match_count"] = 1
        return [region]

    return find_region_keywords(
        query,
        limit=limit,
    )

def match_count(matches) -> int:
    """Return the full keyword-match count carried by SDE search rows."""
    return _match_count(matches)

def resolve_type(
    query,
    *,
    category_id=None,
):
    matches = search_types(
        query,
        limit=1,
        published_only=True,
        category_id=category_id,
    )
    return matches[0] if matches else None

def resolve_system(query):
    matches = search_systems(query, limit=1)
    return matches[0] if matches else None

def resolve_constellation(query):
    matches = search_constellations(query, limit=1)
    return matches[0] if matches else None

def resolve_region(query):
    matches = search_regions(query, limit=1)
    return matches[0] if matches else None

class TypeCategoryFilter(QComboBox):
    """SDE-backed inventory-category selector shared by item search surfaces."""

    def __init__(
        self,
        parent=None,
        *,
        published_only: bool = True,
        accessible_name: str = "Item category filter",
    ):
        super().__init__(parent)
        self.setAccessibleName(accessible_name)
        self.setMaxVisibleItems(CATEGORY_FILTER_VISIBLE_ROWS)
        self.view().setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.refresh(published_only=published_only)

    def _popup_max_height(self) -> int:
        view = self.view()
        row_height = max(
            view.sizeHintForRow(0),
            22,
        )
        return (
            row_height * CATEGORY_FILTER_VISIBLE_ROWS
            + (view.frameWidth() * 2)
        )

    def _resize_popup(self):
        view = self.view()
        maximum_height = self._popup_max_height()
        view.setMaximumHeight(maximum_height)

        popup = view.window()
        if popup.height() > maximum_height:
            popup.resize(
                popup.width(),
                maximum_height,
            )

    def showPopup(self):
        self.view().setMaximumHeight(
            self._popup_max_height()
        )
        super().showPopup()
        self._resize_popup()
        QTimer.singleShot(0, self._resize_popup)

    def refresh(
        self,
        *,
        published_only: bool = True,
    ):
        current = self.currentData()
        blocker = QSignalBlocker(self)

        self.clear()
        self.addItem(
            "ALL CATEGORIES",
            None,
        )

        if sde.is_ready():
            categories = get_filterable_type_categories(
                published_only=published_only,
            )
        else:
            categories = []

        for category in categories:
            self.addItem(
                str(category["name"]).upper(),
                int(category["category_id"]),
            )

        if current is not None:
            index = self.findData(current)

            if index >= 0:
                self.setCurrentIndex(index)

        del blocker

class Debouncer(QObject):
    """Reusable single-shot debounce timer for GUI search interactions."""

    def __init__(
        self,
        parent,
        callback,
        *,
        delay_ms: int = SEARCH_DEBOUNCE_MS,
    ):
        super().__init__(parent)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(
            max(0, int(delay_ms))
        )
        self._timer.timeout.connect(callback)

    @property
    def delay_ms(self) -> int:
        return self._timer.interval()

    def schedule(self):
        self._timer.start()

    def cancel(self):
        self._timer.stop()

    def is_pending(self) -> bool:
        return self._timer.isActive()

class KeywordSuggestions(QObject):
    """Attach a debounced, keyboard-accessible suggestion popup to a line edit."""

    def __init__(
        self,
        line_edit: QLineEdit,
        search_function,
        *,
        accessible_name: str,
        limit: int = 8,
        delay_ms: int = SEARCH_DEBOUNCE_MS,
    ):
        super().__init__(line_edit)

        self._line_edit = line_edit
        self._search_function = search_function
        self._limit = max(1, int(limit))

        self._model = QStringListModel(self)
        self._completer = QCompleter(
            self._model,
            line_edit,
        )
        self._completer.setWidget(line_edit)
        self._completer.setCompletionMode(
            QCompleter.CompletionMode.UnfilteredPopupCompletion
        )
        self._completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self._completer.setMaxVisibleItems(
            self._limit
        )

        popup = self._completer.popup()
        popup.setObjectName("SearchSuggestions")
        popup.setAccessibleName(accessible_name)
        popup.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        popup.setTextElideMode(
            Qt.TextElideMode.ElideRight
        )

        line_edit.setCompleter(self._completer)

        self._debouncer = Debouncer(
            self,
            self.refresh,
            delay_ms=delay_ms,
        )

        line_edit.textEdited.connect(
            self._queue_refresh
        )

    @property
    def completer(self):
        return self._completer

    def _queue_refresh(self):
        self._completer.popup().hide()
        self._debouncer.schedule()

    def refresh(self):
        self._debouncer.cancel()
        query = self._line_edit.text().strip()

        if not query:
            self.clear()
            return

        matches = self._search_function(
            query,
            self._limit,
        )

        suggestions = []
        seen = set()

        for match in matches:
            name = str(match.get("name", "")).strip()

            if not name or name in seen:
                continue

            seen.add(name)
            suggestions.append(name)

        self._model.setStringList(suggestions)

        if not suggestions:
            self._completer.popup().hide()
            return

        if not self._line_edit.hasFocus():
            return

        popup = self._completer.popup()
        popup.setMinimumWidth(
            self._line_edit.width()
        )
        popup.setMaximumWidth(
            self._line_edit.width()
        )
        self._completer.complete(
            self._line_edit.rect()
        )

    def clear(self):
        self._debouncer.cancel()
        self._model.setStringList([])
        self._completer.popup().hide()
