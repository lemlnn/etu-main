"""settings and local data status page"""

from PySide6.QtWidgets import QSizePolicy

from etu import sde
from etu.gui.pages.base import BasePage
from etu.gui.theme import UNIT
from etu.gui.widgets import (
    CutButton,
    DetailRow,
    PhotonPanel,
    StatusLabel,
)
from etu.sde.universe import clear_universe_cache


class SettingsPage(BasePage):
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

        self.root_layout.addWidget(
            data_panel
        )
        self.root_layout.addStretch()

        self.update_button.clicked.connect(
            self._update_action
        )

        self.refresh_status()

    def refresh_status(self):
        ready = sde.is_ready()
        build = (
            sde.get_sde_build()
            if ready
            else None
        )

        self.status_row.set_value(
            "READY"
            if ready
            else "NOT READY"
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

            if installed == latest_build:
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
