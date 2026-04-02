"""Qt main window for the first NWB Forge desktop shell."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMessageBox, QProgressBar, QStatusBar

from nwbforge.domain.models import ConversionSession
from nwbforge.ui import (
    CompositeUiLogSink,
    DesktopShellModel,
    FileUiLogSink,
    FileMenuAction,
    InMemoryUiLogSink,
    UiLogHandler,
    UiLogSubscriptionSink,
    UserFacingError,
)
from nwbforge.ui.conversion_session import ConversionSessionScreenModel
from nwbforge.ui.models import ConversionSessionScreenState, PackageInstallerState, SettingsScreenState, StatusBarState
from nwbforge.ui.package_setup import PackageInstallerScreenModel
from nwbforge.ui.settings import SettingsScreenModel
from nwbforge.ui.qt.bridge import StateBridge
from nwbforge.ui.qt.conversion_session_widget import ConversionSessionWidget
from nwbforge.ui.qt.log_viewer import LogViewerDockWidget
from nwbforge.ui.qt.package_dialog import PackageInstallerDialog
from nwbforge.ui.qt.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """Minimal Qt desktop shell bound to the UI model layer."""

    def __init__(
        self,
        shell_model: DesktopShellModel,
        settings_screen_model: SettingsScreenModel,
        package_screen_model: PackageInstallerScreenModel,
        conversion_screen_model: ConversionSessionScreenModel,
        *,
        log_sink: UiLogSubscriptionSink | None = None,
        log_file_path: Path | None = None,
        session_loader: Callable[[Path], ConversionSession] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("NWB Forge")
        self.resize(1120, 760)

        self._shell_model = shell_model
        self._settings_screen_model = settings_screen_model
        self._package_screen_model = package_screen_model
        self._conversion_screen_model = conversion_screen_model
        self._session_loader = session_loader or self._default_session_loader
        self._recent_session_actions: list[QAction] = []
        self._last_recorded_output_directory: Path | None = None
        self._last_error_signature: tuple[str, str, str | None, str] | None = None
        self._viewer_log_sink = log_sink or InMemoryUiLogSink()
        self._log_handler: UiLogHandler | None = None
        self._applied_settings = self._settings_screen_model.state.applied_settings
        self._configure_logging(self._applied_settings, log_file_path=log_file_path)
        self._shell_model.attach_log_sink(self._viewer_log_sink)

        self._build_file_menu()
        self._build_status_bar()

        self._conversion_widget = ConversionSessionWidget(
            self._conversion_screen_model,
            self,
            output_path_selector=self._choose_output_path,
        )
        self.setCentralWidget(self._conversion_widget)

        self._log_dock = LogViewerDockWidget(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._log_dock)
        self._log_dock.hide()

        self._package_dialog = PackageInstallerDialog(self._package_screen_model, self)
        self._package_dialog.finished.connect(lambda _: self._shell_model.close_active_dialog())

        self._settings_dialog = SettingsDialog(self._settings_screen_model, self)
        self._settings_dialog.finished.connect(lambda _: self._shell_model.close_active_dialog())

        self._shell_bridge = StateBridge(self)
        self._shell_bridge.state_changed.connect(self._apply_shell_state)
        self._shell_model.subscribe(self._shell_bridge.publish)

        self._settings_bridge = StateBridge(self)
        self._settings_bridge.state_changed.connect(self._apply_settings_state)
        self._settings_screen_model.subscribe(self._settings_bridge.publish)

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
    def settings_dialog(self) -> SettingsDialog:
        return self._settings_dialog

    @property
    def log_dock(self) -> LogViewerDockWidget:
        return self._log_dock

    @property
    def file_menu(self):
        return self._file_menu

    @property
    def log_sink(self) -> UiLogSubscriptionSink:
        return self._viewer_log_sink

    def _configure_logging(self, settings, *, log_file_path: Path | None = None) -> None:
        logger = logging.getLogger("nwbforge")
        if self._log_handler is not None:
            logger.removeHandler(self._log_handler)
            self._log_handler.close()

        effective_log_path = log_file_path
        if settings.file_logging_enabled:
            effective_log_path = settings.log_file_path

        handler_sink: UiLogSubscriptionSink | CompositeUiLogSink = self._viewer_log_sink
        if effective_log_path is not None:
            handler_sink = CompositeUiLogSink(self._viewer_log_sink, FileUiLogSink(effective_log_path))

        self._log_handler = UiLogHandler(handler_sink)
        logger.addHandler(self._log_handler)
        logger.setLevel(logging.DEBUG if settings.verbose_logging_enabled else logging.INFO)
        self._shell_model.set_verbose_logging_enabled(settings.verbose_logging_enabled)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._log_handler is not None:
            logging.getLogger("nwbforge").removeHandler(self._log_handler)
            self._log_handler.close()
        super().closeEvent(event)

    def _build_file_menu(self) -> None:
        self._file_menu = self.menuBar().addMenu("&File")

        self._new_session_action = QAction("New Session", self)
        self._new_session_action.triggered.connect(self._new_session)
        self._file_menu.addAction(self._new_session_action)

        self._open_session_action = QAction("Open Session...", self)
        self._open_session_action.triggered.connect(self._open_session_from_dialog)
        self._file_menu.addAction(self._open_session_action)

        self._reopen_last_session_action = QAction("Reopen Last Session", self)
        self._reopen_last_session_action.triggered.connect(self._reopen_last_session)
        self._file_menu.addAction(self._reopen_last_session_action)

        self._recent_sessions_menu = self._file_menu.addMenu("Open Recent")
        self._recent_sessions_menu.setEnabled(False)

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

    def _open_session_from_dialog(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Conversion Session",
            str(Path.cwd()),
            "Conversion sessions (session_manifest.json custom_session.json hybrid_session.json);;JSON files (*.json)",
        )
        if not selected_path:
            return

        self._load_session(Path(selected_path))

    def _choose_output_path(self, current_path: Path | None) -> Path | None:
        initial_path = current_path
        if initial_path is None:
            output_directory = self._settings_screen_model.state.applied_settings.last_output_directory
            if output_directory is not None and self._conversion_screen_model.state.session is not None:
                initial_path = output_directory / f"{self._conversion_screen_model.state.session.session_id}.nwb"
            elif self._conversion_screen_model.state.session is not None:
                initial_path = self._default_output_path_for_session(self._conversion_screen_model.state.session)

        start_location = str(initial_path) if initial_path is not None else str(self._default_output_directory())
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose NWB Output Path",
            start_location,
            "NWB files (*.nwb)",
        )
        if not selected_path:
            return None
        return Path(selected_path)

    def _new_session(self) -> None:
        self._conversion_screen_model.clear_session()
        self._shell_model.set_status_bar(
            StatusBarState(
                stage_key="session:new",
                message="Started a new session.",
                percent_complete=0,
                is_busy=False,
                is_error=False,
            )
        )

    def _reopen_last_session(self) -> None:
        last_path = self._settings_screen_model.state.applied_settings.last_open_session_path
        if last_path is None or not last_path.exists():
            self._shell_model.set_status_bar(
                StatusBarState(
                    stage_key="session:reopen:error",
                    message="No recent session is available to reopen.",
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
                user_error=UserFacingError(
                    title="Reopen Session Error",
                    message="No recent session is available to reopen.",
                    category="session",
                ),
            )
            return

        self._load_session(last_path)

    def _load_session(self, session_path: Path) -> None:
        try:
            session = self._session_loader(session_path)
        except Exception as exc:
            self._shell_model.set_status_bar(
                StatusBarState(
                    stage_key="session:open:error",
                    message=str(exc),
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
                user_error=UserFacingError(
                    title="Open Session Error",
                    message=str(exc),
                    detail=f"Could not load session from {session_path}.",
                    category="session",
                ),
            )
            return

        self._settings_screen_model.record_recent_session(session_path)
        self._conversion_widget.load_session(session)
        default_output_path = self._default_output_path_for_session(session)
        self._conversion_screen_model.set_output_path(default_output_path)
        self._shell_model.set_status_bar(
            StatusBarState(
                stage_key="session:loaded",
                message=f"Loaded session {session.session_id}.",
                percent_complete=100,
                is_busy=False,
                is_error=False,
            )
        )

    def _default_output_path_for_session(self, session: ConversionSession) -> Path:
        output_directory = self._settings_screen_model.state.applied_settings.last_output_directory
        if output_directory is None:
            output_directory = self._default_output_directory()
        return output_directory / f"{session.session_id}.nwb"

    @staticmethod
    def _default_output_directory() -> Path:
        output_directory = (Path.cwd() / ".nwbforge" / "outputs").resolve()
        output_directory.mkdir(parents=True, exist_ok=True)
        return output_directory

    def _rebuild_recent_sessions_menu(self, recent_paths: tuple[str, ...]) -> None:
        self._recent_sessions_menu.clear()
        self._recent_session_actions.clear()
        if not recent_paths:
            self._recent_sessions_menu.setEnabled(False)
            return

        self._recent_sessions_menu.setEnabled(True)
        for path_text in recent_paths:
            action = QAction(path_text, self)
            action.triggered.connect(lambda checked=False, value=path_text: self._load_session(Path(value)))
            self._recent_sessions_menu.addAction(action)
            self._recent_session_actions.append(action)

    @staticmethod
    def _default_session_loader(session_path: Path) -> ConversionSession:
        from nwbforge.app.desktop import load_desktop_session

        return load_desktop_session(session_path)

    def _apply_shell_state(self, state) -> None:
        self._status_label.setText(state.status_bar.message)
        self._progress_bar.setValue(state.status_bar.percent_complete)
        self._log_dock.setVisible(state.is_log_viewer_visible)
        self._log_dock.set_entries(state.log_entries)
        self._show_user_error_if_needed(state.last_user_error)

        if state.active_dialog == "settings" and not self._settings_dialog.isVisible():
            self._settings_dialog.show()
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
        elif state.active_dialog != "settings" and self._settings_dialog.isVisible():
            self._settings_dialog.hide()

        if state.active_dialog == "install_packages" and not self._package_dialog.isVisible():
            self._package_dialog.show()
            self._package_dialog.raise_()
            self._package_dialog.activateWindow()
        elif state.active_dialog != "install_packages" and self._package_dialog.isVisible():
            self._package_dialog.hide()

    def _show_user_error_if_needed(self, error: UserFacingError | None) -> None:
        if error is None:
            self._last_error_signature = None
            return

        signature = (error.title, error.message, error.detail, error.category)
        if signature == self._last_error_signature:
            return

        self._last_error_signature = signature
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Warning)
        message_box.setWindowTitle(error.title)
        message_box.setText(error.message)
        if error.detail:
            message_box.setDetailedText(error.detail)
        message_box.open()

    def _apply_settings_state(self, state: SettingsScreenState) -> None:
        self._rebuild_recent_sessions_menu(state.recent_session_paths)
        self._reopen_last_session_action.setEnabled(bool(state.last_open_session_path))
        if state.applied_settings != self._applied_settings:
            self._applied_settings = state.applied_settings
            self._configure_logging(state.applied_settings)

        if state.user_error is not None:
            self._shell_model.set_status_bar(
                StatusBarState(
                    stage_key="settings:error",
                    message=state.user_error.message,
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
                user_error=state.user_error,
            )
            return

        self._shell_model.set_status_bar(
            StatusBarState(
                stage_key="settings",
                message=state.status_message,
                percent_complete=100 if not state.has_unsaved_changes else 0,
                is_busy=False,
                is_error=False,
            )
        )

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
        if state.output_path is not None:
            candidate_directory = state.output_path.parent.resolve()
            if candidate_directory != self._last_recorded_output_directory:
                self._last_recorded_output_directory = candidate_directory
                self._settings_screen_model.record_output_directory(state.output_path)

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
