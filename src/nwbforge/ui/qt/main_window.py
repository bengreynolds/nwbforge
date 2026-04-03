"""Qt main window for the first NWB Forge desktop shell."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMessageBox, QProgressBar, QStatusBar, QTabWidget, QVBoxLayout, QWidget

from nwbforge.app.logging import get_logger, log_event
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
from nwbforge.ui.models import (
    ConversionSessionScreenState,
    PackageInstallerState,
    SessionAssemblyState,
    SettingsScreenState,
    StatusBarState,
)
from nwbforge.ui.package_setup import PackageInstallerScreenModel
from nwbforge.ui.session_assembly import SessionAssemblyScreenModel
from nwbforge.ui.settings import SettingsScreenModel
from nwbforge.ui.qt.bridge import StateBridge
from nwbforge.ui.qt.conversion_session_widget import ConversionSessionWidget
from nwbforge.ui.qt.log_viewer import LogViewerDockWidget
from nwbforge.ui.qt.nwb_viewer_widget import NwbViewerWidget
from nwbforge.ui.qt.package_dialog import PackageInstallerDialog
from nwbforge.ui.qt.session_assembly_dialog import SessionAssemblyDialog
from nwbforge.ui.qt.settings_dialog import SettingsDialog
from nwbforge.ui.qt.styling import apply_window_chrome, build_page_header


class MainWindow(QMainWindow):
    """Minimal Qt desktop shell bound to the UI model layer."""

    _logger = get_logger(__name__)

    def __init__(
        self,
        shell_model: DesktopShellModel,
        settings_screen_model: SettingsScreenModel,
        package_screen_model: PackageInstallerScreenModel,
        conversion_screen_model: ConversionSessionScreenModel,
        session_assembly_screen_model: SessionAssemblyScreenModel | None = None,
        *,
        log_sink: UiLogSubscriptionSink | None = None,
        log_file_path: Path | None = None,
        session_loader: Callable[[Path], ConversionSession] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("NWB Forge")
        self.resize(1220, 820)
        apply_window_chrome(self)

        self._shell_model = shell_model
        self._settings_screen_model = settings_screen_model
        self._package_screen_model = package_screen_model
        if session_assembly_screen_model is None:
            from nwbforge.app.desktop import build_adapter_registry
            from nwbforge.app.services import SessionAssemblyService

            session_assembly_screen_model = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))
        self._session_assembly_screen_model = session_assembly_screen_model
        self._conversion_screen_model = conversion_screen_model
        self._session_loader = session_loader or self._default_session_loader
        self._recent_session_actions: list[QAction] = []
        self._recent_project_actions: list[QAction] = []
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
            artifact_opener=self._open_artifact_path,
            artifact_revealer=self._reveal_artifact_path,
        )
        self._session_assembly_dialog = SessionAssemblyDialog(
            self._session_assembly_screen_model,
            self,
            session_created=self._load_built_session,
        )
        self._session_assembly_dialog.dismissed.connect(self._shell_model.close_active_dialog)
        self._package_dialog = PackageInstallerDialog(self._package_screen_model, self)
        self._package_dialog.dismissed.connect(self._shell_model.close_active_dialog)
        self._settings_dialog = SettingsDialog(self._settings_screen_model, self)
        self._settings_dialog.dismissed.connect(self._shell_model.close_active_dialog)
        self._nwb_viewer_widget = NwbViewerWidget(parent=self)
        self._nwb_viewer_widget.status_message_changed.connect(self.statusBar().showMessage)

        (
            self._workspace_header,
            self._workspace_title_label,
            self._workspace_subtitle_label,
            self._workspace_badge_label,
        ) = build_page_header(
            "Conversion Workspace",
            "Create sessions, review metadata, run conversions, and inspect generated artifacts in one desktop workflow.",
            badge_text="Direct Ingest Ready",
            parent=self,
        )

        self._workspace_tabs = QTabWidget(self)
        self._workspace_tabs.setDocumentMode(True)
        self._workspace_tabs.addTab(self._conversion_widget, "Conversion")
        self._workspace_tabs.addTab(self._session_assembly_dialog, "New Session")
        self._workspace_tabs.addTab(self._package_dialog, "Packages")
        self._workspace_tabs.addTab(self._settings_dialog, "Settings")
        self._workspace_tabs.addTab(self._nwb_viewer_widget, "NWB Viewer")
        self._workspace_tabs.currentChanged.connect(self._sync_tab_header)

        central = QWidget(self)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(18, 18, 18, 18)
        central_layout.setSpacing(14)
        central_layout.addWidget(self._workspace_header)
        central_layout.addWidget(self._workspace_tabs, 1)
        self.setCentralWidget(central)

        self._log_dock = LogViewerDockWidget(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._log_dock)
        self._log_dock.hide()

        self._shell_bridge = StateBridge(self)
        self._shell_bridge.state_changed.connect(self._apply_shell_state)
        self._shell_model.subscribe(self._shell_bridge.publish)

        self._settings_bridge = StateBridge(self)
        self._settings_bridge.state_changed.connect(self._apply_settings_state)
        self._settings_screen_model.subscribe(self._settings_bridge.publish)

        self._package_bridge = StateBridge(self)
        self._package_bridge.state_changed.connect(self._apply_package_state)
        self._package_screen_model.subscribe(self._package_bridge.publish)

        self._session_assembly_bridge = StateBridge(self)
        self._session_assembly_bridge.state_changed.connect(self._apply_session_assembly_state)
        self._session_assembly_screen_model.subscribe(self._session_assembly_bridge.publish)

        self._conversion_bridge = StateBridge(self)
        self._conversion_bridge.state_changed.connect(self._apply_conversion_state)
        self._conversion_screen_model.subscribe(self._conversion_bridge.publish)
        self._sync_tab_header(self._workspace_tabs.currentIndex())

    @property
    def conversion_widget(self) -> ConversionSessionWidget:
        return self._conversion_widget

    @property
    def package_dialog(self) -> PackageInstallerDialog:
        return self._package_dialog

    @property
    def session_assembly_dialog(self) -> SessionAssemblyDialog:
        return self._session_assembly_dialog

    @property
    def settings_dialog(self) -> SettingsDialog:
        return self._settings_dialog

    @property
    def nwb_viewer_widget(self) -> NwbViewerWidget:
        return self._nwb_viewer_widget

    @property
    def log_dock(self) -> LogViewerDockWidget:
        return self._log_dock

    @property
    def file_menu(self):
        return self._file_menu

    @property
    def workspace_tabs(self) -> QTabWidget:
        return self._workspace_tabs

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
        self._new_session_action.triggered.connect(
            lambda: self._shell_model.invoke_file_menu_action(FileMenuAction.NEW_SESSION)
        )
        self._file_menu.addAction(self._new_session_action)

        self._open_project_action = QAction("Open Project...", self)
        self._open_project_action.triggered.connect(self._open_project_from_dialog)
        self._file_menu.addAction(self._open_project_action)

        self._save_project_action = QAction("Save Project", self)
        self._save_project_action.triggered.connect(self._save_project)
        self._file_menu.addAction(self._save_project_action)

        self._save_project_as_action = QAction("Save Project As...", self)
        self._save_project_as_action.triggered.connect(self._save_project_as)
        self._file_menu.addAction(self._save_project_as_action)

        self._open_session_action = QAction("Open Session...", self)
        self._open_session_action.triggered.connect(self._open_session_from_dialog)
        self._file_menu.addAction(self._open_session_action)

        self._open_nwb_viewer_action = QAction("Open NWB...", self)
        self._open_nwb_viewer_action.triggered.connect(self._open_nwb_viewer_from_dialog)
        self._file_menu.addAction(self._open_nwb_viewer_action)

        self._recent_projects_menu = self._file_menu.addMenu("Open Recent Project")
        self._recent_projects_menu.setEnabled(False)

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
            log_event(self._logger, logging.DEBUG, "Open Session dialog canceled.")
            return

        log_event(self._logger, logging.INFO, "Selected session file from desktop dialog.", session_path=selected_path)
        self._load_session(Path(selected_path))

    def _open_nwb_viewer_from_dialog(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open NWB File",
            str(Path.cwd()),
            "NWB files (*.nwb);;All files (*)",
        )
        if not selected_path:
            log_event(self._logger, logging.DEBUG, "Open NWB dialog canceled.")
            return
        self.open_nwb_viewer(Path(selected_path))

    def _open_project_from_dialog(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Conversion Project",
            str(Path.cwd()),
            "NWB Forge projects (*.nwbforge-project.json);;JSON files (*.json)",
        )
        if not selected_path:
            log_event(self._logger, logging.DEBUG, "Open Project dialog canceled.")
            return

        self._load_project(Path(selected_path))

    def _save_project(self) -> None:
        project_path = self._session_assembly_screen_model.state.project_path
        if project_path is None:
            self._save_project_as()
            return
        self._save_project_to_path(project_path)

    def _save_project_as(self) -> None:
        current_project_path = self._session_assembly_screen_model.state.project_path
        start_location = str(current_project_path) if current_project_path is not None else str(
            Path.cwd() / ".nwbforge-project.json"
        )
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Conversion Project",
            start_location,
            "NWB Forge projects (*.nwbforge-project.json);;JSON files (*.json)",
        )
        if not selected_path:
            log_event(self._logger, logging.DEBUG, "Save Project As dialog canceled.", start_location=start_location)
            return
        save_path = Path(selected_path)
        if "".join(save_path.suffixes[-2:]).lower() != ".nwbforge-project.json":
            save_path = save_path.with_name(f"{save_path.stem}.nwbforge-project.json")
        self._save_project_to_path(save_path)

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
            log_event(self._logger, logging.DEBUG, "Output path chooser canceled.", start_location=start_location)
            return None
        log_event(self._logger, logging.INFO, "Selected NWB output path from desktop dialog.", output_path=selected_path)
        return Path(selected_path)

    def _reopen_last_session(self) -> None:
        last_path = self._settings_screen_model.state.applied_settings.last_open_session_path
        if last_path is None or not last_path.exists():
            log_event(self._logger, logging.WARNING, "Reopen Last Session failed because no recent session was available.")
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

        log_event(self._logger, logging.INFO, "Reopening last desktop session.", session_path=str(last_path))
        self._load_session(last_path)

    def _load_project(self, project_path: Path) -> None:
        log_event(self._logger, logging.INFO, "Loading direct-ingest project.", project_path=str(project_path))
        try:
            self._session_assembly_screen_model.load_project(project_path)
            self._settings_screen_model.record_recent_project(project_path)
            self._shell_model.invoke_file_menu_action(FileMenuAction.NEW_SESSION)
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "Direct-ingest project load failed.",
                project_path=str(project_path),
                error=str(exc),
            )
            self._shell_model.set_status_bar(
                StatusBarState(
                    stage_key="project:open:error",
                    message=str(exc),
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
                user_error=UserFacingError(
                    title="Open Project Error",
                    message=str(exc),
                    detail=f"Could not load project from {project_path}.",
                    category="project",
                ),
            )
            return

        self._shell_model.set_status_bar(
            StatusBarState(
                stage_key="project:loaded",
                message=f"Loaded project {project_path.name}.",
                percent_complete=100,
                is_busy=False,
                is_error=False,
            )
        )

    def _save_project_to_path(self, project_path: Path) -> None:
        try:
            state = self._session_assembly_screen_model.save_project(project_path)
            if state.project_path is not None:
                self._settings_screen_model.record_recent_project(state.project_path)
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "Direct-ingest project save failed.",
                project_path=str(project_path),
                error=str(exc),
            )
            self._shell_model.set_status_bar(
                StatusBarState(
                    stage_key="project:save:error",
                    message=str(exc),
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
                user_error=UserFacingError(
                    title="Save Project Error",
                    message=str(exc),
                    detail=f"Could not save project to {project_path}.",
                    category="project",
                ),
            )
            return

        log_event(self._logger, logging.INFO, "Saved direct-ingest project.", project_path=str(project_path))
        self._shell_model.set_status_bar(
            StatusBarState(
                stage_key="project:saved",
                message=f"Saved project {project_path.name}.",
                percent_complete=100,
                is_busy=False,
                is_error=False,
            )
        )
        if not self._session_assembly_dialog.isVisible():
            self._shell_model.invoke_file_menu_action(FileMenuAction.NEW_SESSION)

    def _load_session(self, session_path: Path) -> None:
        log_event(self._logger, logging.INFO, "Loading desktop session.", session_path=str(session_path))
        try:
            session = self._session_loader(session_path)
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "Desktop session load failed.",
                session_path=str(session_path),
                error=str(exc),
            )
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

        self._activate_loaded_session(session, session_path=session_path)
        log_event(
            self._logger,
            logging.INFO,
            "Loaded desktop session successfully.",
            session_id=session.session_id,
            pathway=session.pathway.value,
            source_count=len(session.sources),
        )
        self._shell_model.set_status_bar(
            StatusBarState(
                stage_key="session:loaded",
                message=f"Loaded session {session.session_id}.",
                percent_complete=100,
                is_busy=False,
                is_error=False,
            )
        )

    def _load_built_session(self, session: ConversionSession) -> None:
        log_event(
            self._logger,
            logging.INFO,
            "Loaded session created from direct-ingest dialog.",
            session_id=session.session_id,
            pathway=session.pathway.value,
            source_count=len(session.sources),
        )
        self._activate_loaded_session(session)
        self._shell_model.set_status_bar(
            StatusBarState(
                stage_key="session:assembled",
                message=f"Built session {session.session_id} from selected inputs.",
                percent_complete=100,
                is_busy=False,
                is_error=False,
            )
        )

    def _activate_loaded_session(self, session: ConversionSession, *, session_path: Path | None = None) -> None:
        if session_path is not None:
            self._settings_screen_model.record_recent_session(session_path)
        self._conversion_widget.load_session(session)
        default_output_path = self._default_output_path_for_session(session)
        log_event(
            self._logger,
            logging.DEBUG,
            "Activated loaded desktop session.",
            session_id=session.session_id,
            default_output_path=str(default_output_path),
        )
        self._conversion_screen_model.set_output_path(default_output_path)
        self._workspace_tabs.setCurrentWidget(self._conversion_widget)

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

    def _rebuild_recent_projects_menu(self, recent_paths: tuple[str, ...]) -> None:
        self._recent_projects_menu.clear()
        self._recent_project_actions.clear()
        if not recent_paths:
            self._recent_projects_menu.setEnabled(False)
            return

        self._recent_projects_menu.setEnabled(True)
        for path_text in recent_paths:
            action = QAction(path_text, self)
            action.triggered.connect(lambda checked=False, value=path_text: self._load_project(Path(value)))
            self._recent_projects_menu.addAction(action)
            self._recent_project_actions.append(action)

    def _open_artifact_path(self, path: Path) -> bool:
        if path.suffix.lower() == ".nwb":
            self.open_nwb_viewer(path)
            return True
        return self._open_desktop_path(
            path,
            title="Artifact Open Error",
            missing_message="The selected artifact no longer exists.",
            failure_message="The selected artifact could not be opened.",
            category="artifact",
        )

    def _reveal_artifact_path(self, path: Path) -> bool:
        return self._open_desktop_path(
            path.parent,
            title="Artifact Folder Error",
            missing_message="The artifact folder no longer exists.",
            failure_message="The artifact folder could not be opened.",
            category="artifact",
        )

    def _open_desktop_path(
        self,
        path: Path,
        *,
        title: str,
        missing_message: str,
        failure_message: str,
        category: str,
    ) -> bool:
        resolved_path = path.resolve()
        if not resolved_path.exists():
            log_event(
                self._logger,
                logging.WARNING,
                "Desktop path action failed because the target no longer exists.",
                path=str(resolved_path),
                action=category,
            )
            self._shell_model.set_status_bar(
                StatusBarState(
                    stage_key="artifact:error",
                    message=missing_message,
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
                user_error=UserFacingError(
                    title=title,
                    message=missing_message,
                    detail=str(resolved_path),
                    category=category,
                ),
            )
            return False

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(resolved_path)))
        if opened:
            log_event(
                self._logger,
                logging.INFO,
                "Opened desktop path successfully.",
                path=str(resolved_path),
                action=category,
            )
            return True

        log_event(
            self._logger,
            logging.ERROR,
            "Desktop path action failed to open target.",
            path=str(resolved_path),
            action=category,
        )
        self._shell_model.set_status_bar(
            StatusBarState(
                stage_key="artifact:error",
                message=failure_message,
                percent_complete=100,
                is_busy=False,
                is_error=True,
            ),
            user_error=UserFacingError(
                title=title,
                message=failure_message,
                detail=str(resolved_path),
                category=category,
            ),
        )
        return False

    def open_nwb_viewer(self, file_path: Path | None = None) -> NwbViewerWidget:
        if file_path is not None:
            self._nwb_viewer_widget.open_file(file_path)
        self._workspace_tabs.setCurrentWidget(self._nwb_viewer_widget)
        if file_path is not None:
            log_event(self._logger, logging.INFO, "Opened NWB file in integrated viewer.", nwb_path=str(file_path))
        else:
            log_event(self._logger, logging.INFO, "Focused integrated NWB viewer tab.")
        return self._nwb_viewer_widget

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
        if state.active_dialog == "settings":
            self._workspace_tabs.setCurrentWidget(self._settings_dialog)
        elif state.active_dialog == "new_session":
            self._workspace_tabs.setCurrentWidget(self._session_assembly_dialog)
        elif state.active_dialog == "install_packages":
            self._workspace_tabs.setCurrentWidget(self._package_dialog)
        elif state.active_dialog is None and self._workspace_tabs.currentWidget() in {
            self._settings_dialog,
            self._session_assembly_dialog,
            self._package_dialog,
        }:
            self._workspace_tabs.setCurrentWidget(self._conversion_widget)

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
        self._rebuild_recent_projects_menu(state.recent_project_paths)
        self._rebuild_recent_sessions_menu(state.recent_session_paths)
        self._reopen_last_session_action.setEnabled(bool(state.last_open_session_path))
        if state.applied_settings != self._applied_settings:
            self._applied_settings = state.applied_settings
            self._configure_logging(state.applied_settings)
            self._conversion_screen_model.set_restore_latest_snapshot_on_load(
                state.applied_settings.restore_latest_snapshot_on_load
            )
            self._conversion_screen_model.set_snapshot_history_limit(
                state.applied_settings.snapshot_history_limit
            )

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
        self._sync_workspace_header(state)
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
            return

    def _apply_session_assembly_state(self, state: SessionAssemblyState) -> None:
        self._save_project_action.setEnabled(bool(state.selected_paths))
        self._save_project_as_action.setEnabled(bool(state.selected_paths))
        if self._workspace_tabs.currentWidget() is self._session_assembly_dialog:
            self._sync_tab_header(self._workspace_tabs.currentIndex())

    def _sync_tab_header(self, index: int) -> None:
        widget = self._workspace_tabs.widget(index)
        if widget is self._conversion_widget:
            self._sync_workspace_header(self._conversion_screen_model.state)
            return
        if widget is self._session_assembly_dialog:
            self._workspace_title_label.setText("New Conversion Session")
            self._workspace_subtitle_label.setText(
                "Add files or folders, review grouped bundles, and assemble a draft session inside the main workspace."
            )
            if self._workspace_badge_label is not None:
                self._workspace_badge_label.setText("Direct Ingest")
            return
        if widget is self._package_dialog:
            self._workspace_title_label.setText("Extensions / Packages")
            self._workspace_subtitle_label.setText(
                "Manage route-based optional dependencies in the current development environment without leaving the main window."
            )
            if self._workspace_badge_label is not None:
                self._workspace_badge_label.setText("Environment")
            return
        if widget is self._settings_dialog:
            self._workspace_title_label.setText("Settings")
            self._workspace_subtitle_label.setText(
                "Review desktop preferences, verbose logging, and file-log behavior in the same workspace."
            )
            if self._workspace_badge_label is not None:
                self._workspace_badge_label.setText("Preferences")
            return
        if widget is self._nwb_viewer_widget:
            self._workspace_title_label.setText("NWB Viewer")
            self._workspace_subtitle_label.setText(
                "Inspect any NWB file in read-only mode without opening a separate application window."
            )
            if self._workspace_badge_label is not None:
                self._workspace_badge_label.setText("Read Only")
            return

    def _sync_workspace_header(self, state: ConversionSessionScreenState) -> None:
        if self._workspace_tabs.currentWidget() is not self._conversion_widget:
            return
        if state.session is None:
            self._workspace_title_label.setText("Conversion Workspace")
            self._workspace_subtitle_label.setText(
                "Start a new conversion session, review grouped inputs, and run preview or write workflows."
            )
            if self._workspace_badge_label is not None:
                self._workspace_badge_label.setText("Awaiting Session")
            return

        source_count = len(state.session.sources)
        project_text = f"{state.session.pathway.value.title()} pathway | {source_count} source"
        if source_count != 1:
            project_text += "s"
        if state.output_path is not None:
            project_text += f" | Output: {state.output_path.name}"
        self._workspace_title_label.setText(state.session.session_id)
        self._workspace_subtitle_label.setText(project_text)
        if self._workspace_badge_label is not None:
            badge_text = state.progress_event.stage.value if state.progress_event is not None else state.session.status.value
            self._workspace_badge_label.setText(badge_text.replace("_", " ").title())
