"""Toolkit-agnostic desktop shell model."""

from __future__ import annotations

from dataclasses import replace

from nwbforge.app.packages import PackageInstallProgressEvent, PackageInstallStage
from nwbforge.app.runtime import PipelineProgressEvent, PipelineRuntimeError, PipelineStage
from nwbforge.app.packages.execution import PackageInstallRuntimeError
from nwbforge.ui.errors import DefaultUiErrorPresenter, UiErrorPresenter
from nwbforge.ui.logs import UiLogSubscriptionSink
from nwbforge.ui.models import (
    DesktopShellState,
    FileMenuAction,
    ShellStateListener,
    StatusBarState,
)


class DesktopShellModel:
    """Track shell state for menus, status text, and log-viewer visibility."""

    def __init__(
        self,
        *,
        log_sink: UiLogSubscriptionSink | None = None,
        error_presenter: UiErrorPresenter | None = None,
    ) -> None:
        self._state = DesktopShellState()
        self._listeners: list[ShellStateListener] = []
        self._log_sink = log_sink
        self._error_presenter = error_presenter or DefaultUiErrorPresenter()
        if self._log_sink is not None:
            self._log_sink.subscribe(self._handle_log_entries)

    @property
    def state(self) -> DesktopShellState:
        return self._state

    def subscribe(self, listener: ShellStateListener, *, emit_initial: bool = True) -> None:
        self._listeners.append(listener)
        if emit_initial:
            listener(self._state)

    def invoke_file_menu_action(self, action: FileMenuAction) -> DesktopShellState:
        if action in {
            FileMenuAction.OPEN_PROJECT,
            FileMenuAction.SAVE_PROJECT,
            FileMenuAction.SAVE_PROJECT_AS,
            FileMenuAction.OPEN_SESSION,
            FileMenuAction.REOPEN_LAST_SESSION,
        }:
            return self._state

        if action is FileMenuAction.NEW_SESSION:
            return self._set_state(replace(self._state, active_dialog="new_session"))

        if action is FileMenuAction.TOGGLE_LOG_VIEWER:
            return self._set_state(
                replace(
                    self._state,
                    is_log_viewer_visible=not self._state.is_log_viewer_visible,
                    active_dialog=None,
                )
            )

        if action is FileMenuAction.SETTINGS:
            return self._set_state(replace(self._state, active_dialog="settings"))

        if action is FileMenuAction.INSTALL_PACKAGES:
            return self._set_state(replace(self._state, active_dialog="install_packages"))

        raise ValueError(f"Unsupported file-menu action {action!r}.")

    def close_active_dialog(self) -> DesktopShellState:
        return self._set_state(replace(self._state, active_dialog=None))

    def set_verbose_logging_enabled(self, enabled: bool) -> DesktopShellState:
        return self._set_state(replace(self._state, verbose_logging_enabled=enabled))

    def attach_log_sink(self, log_sink: UiLogSubscriptionSink) -> None:
        if self._log_sink is log_sink:
            return
        self._log_sink = log_sink
        self._log_sink.subscribe(self._handle_log_entries)

    def set_status_bar(
        self,
        status_bar: StatusBarState,
        *,
        user_error=None,
    ) -> DesktopShellState:
        return self._set_state(
            replace(
                self._state,
                status_bar=status_bar,
                last_user_error=user_error,
            )
        )

    def apply_pipeline_progress(self, event: PipelineProgressEvent) -> DesktopShellState:
        return self._set_state(
            replace(
                self._state,
                status_bar=StatusBarState(
                    stage_key=event.stage.value,
                    message=event.message,
                    percent_complete=event.percent_complete,
                    is_busy=event.stage not in {PipelineStage.COMPLETED, PipelineStage.FAILED},
                    is_error=event.stage is PipelineStage.FAILED,
                ),
                last_user_error=None,
            )
        )

    def apply_pipeline_error(self, error: PipelineRuntimeError) -> DesktopShellState:
        user_error = self._error_presenter.present(error)
        return self._set_state(
            replace(
                self._state,
                status_bar=StatusBarState(
                    stage_key=error.stage.value,
                    message=user_error.message,
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
                last_user_error=user_error,
            )
        )

    def apply_package_progress(self, event: PackageInstallProgressEvent) -> DesktopShellState:
        return self._set_state(
            replace(
                self._state,
                status_bar=StatusBarState(
                    stage_key=f"packages:{event.stage.value}",
                    message=event.message,
                    percent_complete=event.percent_complete,
                    is_busy=event.stage not in {PackageInstallStage.COMPLETED, PackageInstallStage.FAILED},
                    is_error=event.stage is PackageInstallStage.FAILED,
                ),
                last_user_error=None,
            )
        )

    def apply_package_error(self, error: PackageInstallRuntimeError) -> DesktopShellState:
        user_error = self._error_presenter.present(error)
        return self._set_state(
            replace(
                self._state,
                status_bar=StatusBarState(
                    stage_key=f"packages:{error.stage.value}",
                    message=user_error.message,
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
                last_user_error=user_error,
            )
        )

    def _handle_log_entries(self, entries) -> None:
        self._set_state(replace(self._state, log_entries=entries))

    def _set_state(self, new_state: DesktopShellState) -> DesktopShellState:
        self._state = new_state
        for listener in self._listeners:
            listener(self._state)
        return self._state
