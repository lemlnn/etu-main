"""settings and local data status page"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QWidget,
)

from etu import sde
from etu.gui.pages.base import BasePage
from etu.gui.preferences import (
    MAX_INVENTORY_RESULT_LIMIT,
    MIN_INVENTORY_RESULT_LIMIT,
    inventory_search_preferences,
    set_inventory_published_only,
    set_inventory_result_limit,
    set_inventory_show_all_results,
)
from etu.gui.theme import UNIT
from etu.gui.widgets import (
    CutButton,
    DetailRow,
    PhotonPanel,
    StatusLabel,
)
from etu.sde.universe import clear_universe_cache


class SettingsPage(BasePage):
    inventory_settings_changed = Signal()

    def __init__(self):
        super().__init__(
            "Settings",
        )

        self._latest_build = None
        self._update_ready = False

        data_panel = PhotonPanel(
            "STATIC DATA",
        )
        data_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )

        self.status_row = DetailRow(
            "SDE Status"
        )
        self.build_row = DetailRow(
            "SDE Build"
        )
        self.database_row = DetailRow(
            "Database",
            str(sde.DB_PATH),
            wrap=True,
        )

        data_panel.body_layout.addWidget(
            self.status_row
        )
        data_panel.body_layout.addWidget(
            self.build_row
        )
        data_panel.body_layout.addWidget(
            self.database_row
        )

        self.update_button = CutButton(
            "CHECK FOR SDE UPDATE"
        )
        self.update_button.setAccessibleName(
            "Check for SDE update"
        )
        self.update_status = StatusLabel()

        data_panel.body_layout.addSpacing(
            UNIT
        )
        data_panel.body_layout.addWidget(
            self.update_button
        )
        data_panel.body_layout.addWidget(
            self.update_status
        )

        inventory_panel = PhotonPanel(
            "INVENTORY SETTINGS",
        )
        inventory_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )

        preferences = inventory_search_preferences()

        self.show_all_results = QCheckBox(
            "SHOW ALL SEARCH RESULTS"
        )
        self.show_all_results.setObjectName(
            "SettingsToggle"
        )
        self.show_all_results.setAccessibleName(
            "Show all inventory search results"
        )
        self.show_all_results.setChecked(
            preferences.show_all_results
        )

        self.published_only = QCheckBox(
            "PUBLISHED ITEMS ONLY"
        )
        self.published_only.setObjectName(
            "SettingsToggle"
        )
        self.published_only.setAccessibleName(
            "Show published inventory items only"
        )
        self.published_only.setChecked(
            preferences.published_only
        )

        self.result_limit_row = QWidget()
        result_limit_layout = QHBoxLayout(
            self.result_limit_row
        )
        result_limit_layout.setContentsMargins(
            0, 0, 0, 0
        )
        result_limit_layout.setSpacing(UNIT)

        result_limit_label = QLabel(
            "RESULT LIMIT"
        )
        result_limit_label.setObjectName(
            "SectionLabel"
        )
        result_limit_label.setFixedWidth(
            UNIT * 15
        )

        self.result_limit = QSpinBox()
        self.result_limit.setObjectName(
            "SettingsNumber"
        )
        self.result_limit.setAccessibleName(
            "Maximum inventory search results"
        )
        self.result_limit.setRange(
            MIN_INVENTORY_RESULT_LIMIT,
            MAX_INVENTORY_RESULT_LIMIT,
        )
        self.result_limit.setValue(
            preferences.result_limit
        )
        self.result_limit.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )
        self.result_limit.setFixedWidth(UNIT * 12)

        result_limit_layout.addWidget(
            result_limit_label
        )
        result_limit_layout.addWidget(
            self.result_limit
        )
        result_limit_layout.addStretch()

        inventory_panel.body_layout.addWidget(
            self.show_all_results
        )
        inventory_panel.body_layout.addWidget(
            self.result_limit_row
        )
        inventory_panel.body_layout.addWidget(
            self.published_only
        )

        self.root_layout.addWidget(
            data_panel
        )
        self.root_layout.addWidget(
            inventory_panel
        )
        self.root_layout.addStretch()

        self.update_button.clicked.connect(
            self._update_action
        )
        self.show_all_results.toggled.connect(
            self._set_show_all_results
        )
        self.result_limit.valueChanged.connect(
            self._set_result_limit
        )
        self.published_only.toggled.connect(
            self._set_published_only
        )

        self._sync_result_limit_visibility()
        self.refresh_status()

    def _sync_result_limit_visibility(self):
        self.result_limit_row.setVisible(
            not self.show_all_results.isChecked()
        )

    def _set_show_all_results(self, enabled):
        set_inventory_show_all_results(enabled)
        self._sync_result_limit_visibility()
        self.inventory_settings_changed.emit()

    def _set_result_limit(self, limit):
        set_inventory_result_limit(limit)
        self.inventory_settings_changed.emit()

    def _set_published_only(self, enabled):
        set_inventory_published_only(enabled)
        self.inventory_settings_changed.emit()

    def refresh_status(self):
        ready = sde.is_ready()
        build = (
            sde.get_sde_build()
            if ready
            else None
        )

        refresh_required = (
            ready
            and sde.needs_sde_refresh()
        )

        self.status_row.set_value(
            "REFRESH REQUIRED"
            if refresh_required
            else (
                "READY"
                if ready
                else "NOT READY"
            )
        )

        if refresh_required:
            self._update_ready = True
            self.update_button.setText(
                "REFRESH SDE"
            )

        self.build_row.set_value(
            build or "UNKNOWN"
        )
        self.database_row.set_value(
            sde.DB_PATH
        )

    def _update_action(self):
        if self._update_ready:
            self._start_update()
        else:
            self._check_for_update()

    def _set_busy(self, busy):
        self.update_button.setEnabled(
            not busy
        )

    def _check_for_update(self):
        self._set_busy(True)
        self.update_status.set_status(
            "Checking current SDE build"
        )

        def result(latest_build):
            self._latest_build = latest_build
            installed = sde.get_sde_build()
            refresh_required = (
                sde.needs_sde_refresh()
            )

            if (
                installed == latest_build
                and not refresh_required
            ):
                self._update_ready = False
                self.update_button.setText(
                    "CHECK FOR SDE UPDATE"
                )
                self.update_status.set_status(
                    f"SDE is up to date · build {latest_build}",
                    "success",
                )
                return

            self._update_ready = True

            if (
                installed == latest_build
                and refresh_required
            ):
                self.update_button.setText(
                    "REFRESH SDE"
                )
                self.update_status.set_status(
                    "Local SDE refresh required · "
                    f"build {latest_build}",
                    "warning",
                )
                return
            self.update_button.setText(
                "UPDATE SDE"
            )
            self.update_status.set_status(
                f"Update available · "
                f"{installed or 'none'} → {latest_build}",
                "warning",
            )

        def error(exception):
            self.update_status.set_status(
                f"SDE update check failed · {exception}",
                "error",
            )

        def finished():
            self._set_busy(False)

        self.run_task(
            sde.get_latest_sde_build,
            result,
            error,
            finished,
        )

    def _start_update(self):
        self._set_busy(True)
        self.update_status.set_status(
            "Downloading and importing SDE"
        )

        def result(_):
            clear_universe_cache()
            self._update_ready = False
            self.update_button.setText(
                "CHECK FOR SDE UPDATE"
            )
            self.refresh_status()
            self.update_status.set_status(
                f"SDE updated · build {sde.get_sde_build()}",
                "success",
            )

        def error(exception):
            self.update_status.set_status(
                f"SDE update failed · {exception}",
                "error",
            )

        def finished():
            self._set_busy(False)

        self.run_task(
            sde.update_sde,
            result,
            error,
            finished,
        )
