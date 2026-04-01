"""Qt main window for the first NWB Forge desktop shell."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QProgressBar, QStatusBar

from nwbforge.ui import DesktopShellModel, FileMenuAction, InMemoryUiLogSink, UiLogHandler
from nwbforge.ui.conversion_session import ConversionSessionScreenModel
from nwbforge.ui.models import ConversionSessionScreenState, PackageInstallerState, StatusBarState
from nwbforge.ui.package_setup import PackageInstallerScreenModel
from nwbforge.ui.qt.bridge import StateBridge
from nwbforge.ui.qt.conversion_session_widget import ConversionSessionWidget
from nwbforge.ui.qt.log_viewer import LogViewerDockWidget
from nwbforge.ui.qt.package_dialog import PackageInstallerDialog


class MainWindow(QMainWindow):
    """Minimal Qt desktop shell bound to the UI model layer."""

    def __init__(
        self,
        shell_model: DesktopShellModel,
        package_screen_model: PackageInstallerScreenModel,
        conversion_screen_model: ConversionSessionScreenModel,
        *,
        log_sink: InMemoryUiLogSink | None = None,
        parent=None,
    ) -> None:
        self._log_sink = log_sink or InMemoryUiLogSink()
        self._log_handler = UiLogHandler(self._log_sink)
        logger = logging.getLogger("nwbforge")
        logger.addHandler(self._log_handler)
        logger.setLevel(logging.INFO)

        super().__init__(parent)
        self.setWindowTitle("NWB Forge")
        self.resize(1120, 760)

        self._shell_model = shell_model
        self._package_screen_model = package_screen_model
        self._conversion_screen_model = conversion_screen_model
        self._shell_model.attach_log_sink(self._log_sink)

        self._build_file_menu()
        self._build_status_bar()

        self._conversion_widget = ConversionSessionWidget(self._conversion_screen_model, self)
        self.setCentralWidget(self._conversion_widget)

        self._log_dock = LogViewerDockWidget(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._log_dock)
        self._log_dock.hide()

        self._package_dialog = PackageInstallerDialog(self._package_screen_model, self)
        self._package_dialog.finished.connect(lambda _: self._shell_model.close_active_dialog())

        self._shell_bridge = StateBridge(self)
        self._shell_bridge.state_changed.connect(self._apply_shell_state)
        self._shell_model.subscribe(self._shell_bridge.publish)

        self._package_bridge = StateBridge(self)
        self._package_bridge.state_changed.connect(self._apply_package_state)
        self._package_screen_model.subscribe(self._package_bridge.publish)

        self._conversion_bridge = StateBridge(self)
        self._conversion_bridge.state_changed.connect(self._apply_conversion_state)
        self._conversion_screen_model.subscribe(self._conversion_bridge.publish)

    @property
    def conversion_widget(self) -> ConversionSessionWidget:
        return self._conversion_widget

    @property
    def package_dialog(self) -> PackageInstallerDialog:
        return self._package_dialog

    @property
    def log_dock(self) -> LogViewerDockWidget:
        return self._log_dock

    @property
    def file_menu(self):
        return self._file_menu

    def closeEvent(self, event) -> None:  # noqa: N802
        logging.getLogger("nwbforge").removeHandler(self._log_handler)
        self._log_handler.close()
        super().closeEvent(event)

    def _build_file_menu(self) -> None:
        self._file_menu = self.menuBar().addMenu("&File")

        self._settings_action = QAction("Settings", self)
        self._settings_action.triggered.connect(
            lambda: self._shell_model.invoke_file_menu_action(FileMenuAction.SETTINGS)
        )
        self._file_menu.addAction(self._settings_action)

        self._install_packages_action = QAction("Install Extensions / Packages", self)
        self._install_packages_action.triggered.connect(
            lambda: self._shell_model.invoke_file_menu_action(FileMenuAction.INSTALL_PACKAGES)
        )
        self._file_menu.addAction(self._install_packages_action)

        self._toggle_log_viewer_action = QAction("Toggle Log Viewer", self)
        self._toggle_log_viewer_action.triggered.connect(
            lambda: self._shell_model.invoke_file_menu_action(FileMenuAction.TOGGLE_LOG_VIEWER)
        )
        self._file_menu.addAction(self._toggle_log_viewer_action)

    def _build_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        self._status_label = QLabel("Ready.", self)
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        status_bar.addWidget(self._status_label, 1)
        status_bar.addPermanentWidget(self._progress_bar)

    def _apply_shell_state(self, state) -> None:
        self._status_label.setText(state.status_bar.message)
        self._progress_bar.setValue(state.status_bar.percent_complete)
        self._log_dock.setVisible(state.is_log_viewer_visible)
        self._log_dock.set_entries(state.log_entries)

        if state.active_dialog == "install_packages" and not self._package_dialog.isVisible():
            self._package_dialog.show()
            self._package_dialog.raise_()
            self._package_dialog.activateWindow()
        elif state.active_dialog != "install_packages" and self._package_dialog.isVisible():
            self._package_dialog.hide()

        if state.active_dialog == "settings":
            QMessageBox.information(self, "Settings", "Settings UI is not implemented yet.")
            self._shell_model.close_active_dialog()

    def _apply_package_state(self, state: PackageInstallerState) -> None:
        if state.user_error is not None:
            self._shell_model.set_status_bar(
                StatusBarState(
                    stage_key="packages:error",
                    message=state.user_error.message,
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
                user_error=state.user_error,
            )
            return

        if state.progress_event is not None:
            self._shell_model.set_status_bar(
                StatusBarState(
                    stage_key=f"packages:{state.progress_event.stage.value}",
                    message=state.progress_event.message,
                    percent_complete=state.progress_event.percent_complete,
                    is_busy=state.progress_event.stage.value not in {"completed", "failed"},
                    is_error=state.progress_event.stage.value == "failed",
                )
            )

    def _apply_conversion_state(self, state: ConversionSessionScreenState) -> None:
        if state.user_error is not None:
            self._shell_model.set_status_bar(
                StatusBarState(
                    stage_key="conversion:error",
                    message=state.user_error.message,
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
                user_error=state.user_error,
            )
            return

        if state.progress_event is not None:
            self._shell_model.set_status_bar(
                StatusBarState(
                    stage_key=state.progress_event.stage.value,
                    message=state.progress_event.message,
                    percent_complete=state.progress_event.percent_complete,
                    is_busy=state.progress_event.stage.value not in {"completed", "failed"},
                    is_error=state.progress_event.stage.value == "failed",
                )
            )
            return

        if state.execution is not None:
            self._shell_model.set_status_bar(
                StatusBarState(
                    stage_key=state.execution.session.status.value,
                    message=f"Execution {state.execution.session.status.value}.",
                    percent_complete=100,
                    is_busy=False,
                    is_error=state.execution.session.status.value == "failed",
                )
            )
