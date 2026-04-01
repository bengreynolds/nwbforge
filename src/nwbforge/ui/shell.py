"""Toolkit-agnostic desktop shell model."""

from __future__ import annotations

from dataclasses import replace

from nwbforge.app.packages import PackageInstallProgressEvent, PackageInstallStage
from nwbforge.app.runtime import PipelineProgressEvent, PipelineRuntimeError, PipelineStage
from nwbforge.app.packages.execution import PackageInstallRuntimeError
from nwbforge.ui.models import (
    DesktopShellState,
    FileMenuAction,
    ShellStateListener,
    StatusBarState,
)


class DesktopShellModel:
    """Track shell state for menus, status text, and log-viewer visibility."""

    def __init__(self) -> None:
        self._state = DesktopShellState()
        self._listeners: list[ShellStateListener] = []

    @property
    def state(self) -> DesktopShellState:
        return self._state

    def subscribe(self, listener: ShellStateListener, *, emit_initial: bool = True) -> None:
        self._listeners.append(listener)
        if emit_initial:
            listener(self._state)

    def invoke_file_menu_action(self, action: FileMenuAction) -> DesktopShellState:
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
            )
        )

    def apply_pipeline_error(self, error: PipelineRuntimeError) -> DesktopShellState:
        return self._set_state(
            replace(
                self._state,
                status_bar=StatusBarState(
                    stage_key=error.stage.value,
                    message=error.user_message,
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
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
            )
        )

    def apply_package_error(self, error: PackageInstallRuntimeError) -> DesktopShellState:
        return self._set_state(
            replace(
                self._state,
                status_bar=StatusBarState(
                    stage_key=f"packages:{error.stage.value}",
                    message=error.user_message,
                    percent_complete=100,
                    is_busy=False,
                    is_error=True,
                ),
            )
        )

    def _set_state(self, new_state: DesktopShellState) -> DesktopShellState:
        self._state = new_state
        for listener in self._listeners:
            listener(self._state)
        return self._state
