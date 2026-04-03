"""Toolkit-agnostic desktop settings screen model."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from threading import Lock

from nwbforge.app.services import UiSettings, UiSettingsService
from nwbforge.ui.errors import DefaultUiErrorPresenter, UiErrorPresenter
from nwbforge.ui.models import SettingsScreenState, SettingsScreenStateListener


class SettingsScreenModel:
    """Drive desktop settings editing and persistence for the UI."""

    def __init__(
        self,
        settings_service: UiSettingsService,
        *,
        error_presenter: UiErrorPresenter | None = None,
    ) -> None:
        self._settings_service = settings_service
        self._state = SettingsScreenState()
        self._listeners: list[SettingsScreenStateListener] = []
        self._lock = Lock()
        self._error_presenter = error_presenter or DefaultUiErrorPresenter()

    @property
    def state(self) -> SettingsScreenState:
        return self._state

    def subscribe(self, listener: SettingsScreenStateListener, *, emit_initial: bool = True) -> None:
        with self._lock:
            self._listeners.append(listener)
            state = self._state
        if emit_initial:
            listener(state)

    def load(self) -> SettingsScreenState:
        settings = self._settings_service.load()
        return self._set_state(self._state_from_settings(settings, status_message="Settings loaded."))

    def set_verbose_logging_enabled(self, enabled: bool) -> SettingsScreenState:
        return self._set_draft(verbose_logging_enabled=enabled)

    def set_file_logging_enabled(self, enabled: bool) -> SettingsScreenState:
        return self._set_draft(file_logging_enabled=enabled)

    def set_log_file_path(self, path_text: str) -> SettingsScreenState:
        return self._set_draft(log_file_path=path_text)

    def set_restore_latest_snapshot_on_load(self, enabled: bool) -> SettingsScreenState:
        return self._set_draft(restore_latest_snapshot_on_load=enabled)

    def set_recent_item_limit(self, limit: int) -> SettingsScreenState:
        return self._set_draft(recent_item_limit=max(int(limit), 1))

    def set_snapshot_history_limit(self, limit: int) -> SettingsScreenState:
        return self._set_draft(snapshot_history_limit=max(int(limit), 1))

    def discard_changes(self) -> SettingsScreenState:
        applied = self._state.applied_settings
        return self._set_state(self._state_from_settings(applied, status_message="Changes discarded."))

    def save(self) -> SettingsScreenState:
        try:
            settings = self._build_settings()
            saved = self._settings_service.save(settings)
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            return self._set_state(
                replace(
                    self._state,
                    status_message=user_error.message,
                    user_error=user_error,
                )
            )

        return self._set_state(self._state_from_settings(saved, status_message="Settings saved."))

    def record_recent_session(self, session_path: Path) -> SettingsScreenState:
        saved = self._settings_service.record_recent_session(session_path)
        return self._set_state(self._state_from_settings(saved, status_message="Session opened."))

    def record_recent_project(self, project_path: Path) -> SettingsScreenState:
        saved = self._settings_service.record_recent_project(project_path)
        return self._set_state(self._state_from_settings(saved, status_message="Project opened."))

    def record_output_directory(self, output_path: Path) -> SettingsScreenState:
        saved = self._settings_service.record_output_directory(output_path)
        return self._set_state(self._state_from_settings(saved, status_message="Output directory updated."))

    def _build_settings(self) -> UiSettings:
        path_text = self._state.log_file_path.strip()
        if self._state.file_logging_enabled and not path_text:
            raise ValueError("Log file path is required when file logging is enabled.")

        log_file_path = Path(path_text) if path_text else UiSettings().log_file_path
        applied = self._state.applied_settings
        return UiSettings(
            verbose_logging_enabled=self._state.verbose_logging_enabled,
            file_logging_enabled=self._state.file_logging_enabled,
            log_file_path=log_file_path,
            restore_latest_snapshot_on_load=self._state.restore_latest_snapshot_on_load,
            recent_item_limit=max(int(self._state.recent_item_limit), 1),
            snapshot_history_limit=max(int(self._state.snapshot_history_limit), 1),
            last_open_project_path=applied.last_open_project_path,
            recent_project_paths=applied.recent_project_paths,
            last_open_session_path=applied.last_open_session_path,
            recent_session_paths=applied.recent_session_paths,
            last_output_directory=applied.last_output_directory,
        )

    def _set_draft(self, **changes) -> SettingsScreenState:
        draft = replace(
            self._state,
            **changes,
            has_unsaved_changes=True,
            status_message="Settings changed.",
            user_error=None,
        )
        return self._set_state(draft)

    def _state_from_settings(self, settings: UiSettings, *, status_message: str) -> SettingsScreenState:
        return SettingsScreenState(
            applied_settings=settings,
            verbose_logging_enabled=settings.verbose_logging_enabled,
            file_logging_enabled=settings.file_logging_enabled,
            log_file_path=str(settings.log_file_path),
            restore_latest_snapshot_on_load=settings.restore_latest_snapshot_on_load,
            recent_item_limit=settings.recent_item_limit,
            snapshot_history_limit=settings.snapshot_history_limit,
            last_open_project_path=str(settings.last_open_project_path) if settings.last_open_project_path else "",
            recent_project_paths=tuple(str(path) for path in settings.recent_project_paths),
            last_open_session_path=str(settings.last_open_session_path) if settings.last_open_session_path else "",
            recent_session_paths=tuple(str(path) for path in settings.recent_session_paths),
            last_output_directory=str(settings.last_output_directory) if settings.last_output_directory else "",
            has_unsaved_changes=False,
            status_message=status_message,
            user_error=None,
        )

    def _set_state(self, new_state: SettingsScreenState) -> SettingsScreenState:
        with self._lock:
            self._state = new_state
            listeners = tuple(self._listeners)
            state = self._state
        for listener in listeners:
            listener(state)
        return state
