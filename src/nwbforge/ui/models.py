"""Toolkit-agnostic state models for the desktop UI shell."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Callable

from nwbforge.app.packages import (
    InstallMode,
    InstallPreset,
    PackageCompatibilityIssue,
    PackageInstallPreview,
    PackageInstallProgressEvent,
    PackageSelection,
    RoutePackageSpec,
)
from nwbforge.app.runtime import PipelineProgressEvent
from nwbforge.app.services.models import ConversionExecution, ConversionPreview
from nwbforge.domain.models import ConversionSession, SourceReference
from nwbforge.ui.errors import UserFacingError
from nwbforge.ui.logs import UiLogEntry


class FileMenuAction(StrEnum):
    """Top-level file-menu actions exposed by the desktop shell."""

    SETTINGS = "settings"
    INSTALL_PACKAGES = "install_packages"
    TOGGLE_LOG_VIEWER = "toggle_log_viewer"


@dataclass(frozen=True, slots=True)
class FileMenuEntry:
    """A user-visible file-menu entry."""

    action: FileMenuAction
    label: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class StatusBarState:
    """Status bar information bound to current runtime work."""

    stage_key: str
    message: str
    percent_complete: int = 0
    is_busy: bool = False
    is_error: bool = False


@dataclass(frozen=True, slots=True)
class PackageInstallerState:
    """State consumable by an initial setup or extension-install screen."""

    install_mode: InstallMode = InstallMode.SELECTED
    install_preset: InstallPreset = InstallPreset.COMMON
    available_routes: tuple[RoutePackageSpec, ...] = ()
    selected_routes: tuple[str, ...] = ()
    saved_selection: PackageSelection | None = None
    preview: PackageInstallPreview | None = None
    issues: tuple[PackageCompatibilityIssue, ...] = ()
    resolved_extras: tuple[str, ...] = ()
    is_installable: bool = False
    is_install_running: bool = False
    progress_event: PackageInstallProgressEvent | None = None
    error_message: str | None = None
    user_error: UserFacingError | None = None
    last_completed_routes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConversionSourceItem:
    """A UI-facing summary of one session source."""

    source_id: str
    label: str
    source_type: str
    location: Path
    adapter_hint: str | None = None


@dataclass(frozen=True, slots=True)
class ConversionSessionScreenState:
    """State consumable by a conversion-session screen."""

    session: ConversionSession | None = None
    sources: tuple[ConversionSourceItem, ...] = ()
    preview: ConversionPreview | None = None
    execution: ConversionExecution | None = None
    progress_event: PipelineProgressEvent | None = None
    output_path: Path | None = None
    error_message: str | None = None
    user_error: UserFacingError | None = None
    is_preview_running: bool = False
    is_execution_running: bool = False

    @property
    def can_run_preview(self) -> bool:
        return self.session is not None and not self.is_preview_running and not self.is_execution_running

    @property
    def can_run_execution(self) -> bool:
        return self.preview is not None and not self.is_preview_running and not self.is_execution_running


def conversion_source_items(sources: tuple[SourceReference, ...]) -> tuple[ConversionSourceItem, ...]:
    """Project domain source references into UI-facing source summaries."""

    return tuple(
        ConversionSourceItem(
            source_id=source.source_id,
            label=source.label,
            source_type=source.source_type.value,
            location=source.location,
            adapter_hint=source.adapter_hint,
        )
        for source in sources
    )


def default_file_menu_entries() -> tuple[FileMenuEntry, ...]:
    """Return the current file-menu baseline for the desktop shell."""

    return (
        FileMenuEntry(
            action=FileMenuAction.SETTINGS,
            label="Settings",
        ),
        FileMenuEntry(
            action=FileMenuAction.INSTALL_PACKAGES,
            label="Install Extensions / Packages",
        ),
        FileMenuEntry(
            action=FileMenuAction.TOGGLE_LOG_VIEWER,
            label="Toggle Log Viewer",
        ),
    )


@dataclass(frozen=True, slots=True)
class DesktopShellState:
    """High-level shell state shared across future desktop views."""

    status_bar: StatusBarState = field(
        default_factory=lambda: StatusBarState(
            stage_key="idle",
            message="Ready.",
            percent_complete=0,
            is_busy=False,
            is_error=False,
        )
    )
    file_menu_entries: tuple[FileMenuEntry, ...] = field(default_factory=default_file_menu_entries)
    is_log_viewer_visible: bool = False
    active_dialog: str | None = None
    verbose_logging_enabled: bool = False
    log_entries: tuple[UiLogEntry, ...] = ()
    last_user_error: UserFacingError | None = None


ShellStateListener = Callable[[DesktopShellState], None]
PackageInstallerStateListener = Callable[[PackageInstallerState], None]
ConversionSessionStateListener = Callable[[ConversionSessionScreenState], None]
