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
from nwbforge.app.services import UiSettings
from nwbforge.app.services.session_assembly import SessionAssemblyDraft
from nwbforge.app.services.models import ConversionExecution, ConversionPreview, ReviewSubmission
from nwbforge.domain.enums import ReviewStatus
from nwbforge.domain.models import (
    ConversionSession,
    SourceReference,
    ValidationReviewOutcome,
    ValidationSummary,
)
from nwbforge.ui.errors import UserFacingError
from nwbforge.ui.logs import UiLogEntry


class FileMenuAction(StrEnum):
    """Top-level file-menu actions exposed by the desktop shell."""

    NEW_SESSION = "new_session"
    OPEN_PROJECT = "open_project"
    SAVE_PROJECT = "save_project"
    SAVE_PROJECT_AS = "save_project_as"
    OPEN_SESSION = "open_session"
    REOPEN_LAST_SESSION = "reopen_last_session"
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
    role: str
    adapter_hint: str | None = None
    media_type: str | None = None


@dataclass(frozen=True, slots=True)
class SessionAssemblySourceItem:
    """A UI-facing summary of one selected input in session assembly."""

    source_id: str
    group_key: str
    group_label: str
    label: str
    location: Path
    source_type: str
    suggested_pathway: str
    role: str = "primary"
    metadata_overrides: dict[str, str] = field(default_factory=dict)
    sidecar_for_source_id: str | None = None
    sidecar_for_label: str | None = None
    matching_adapter_ids: tuple[str, ...] = ()
    suggested_adapter_id: str | None = None
    needs_review: bool = False


@dataclass(frozen=True, slots=True)
class SessionAssemblyGroupItem:
    """A UI-facing summary of one auto-detected or manually corrected group."""

    group_key: str
    group_label: str
    suggested_pathway: str
    group_kind: str = "folder"
    anchor_path: Path | None = None
    grouping_reason: str = ""
    member_labels: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    source_count: int = 0
    primary_count: int = 0
    supplemental_count: int = 0
    metadata_count: int = 0
    review_issue_count: int = 0
    requires_confirmation: bool = False
    needs_review: bool = False
    is_confirmed: bool = False


@dataclass(frozen=True, slots=True)
class SessionAssemblyIssueItem:
    """A UI-facing issue discovered while assembling a draft session."""

    code: str
    message: str
    severity: str
    location: Path | None = None


@dataclass(frozen=True, slots=True)
class SessionAssemblyState:
    """State consumable by a direct-ingest session-assembly screen."""

    selected_paths: tuple[Path, ...] = ()
    project_path: Path | None = None
    session_id: str = ""
    title: str = ""
    suggested_pathway: str = "custom"
    metadata_overrides: dict[str, str] = field(default_factory=dict)
    source_metadata_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    groups: tuple[SessionAssemblyGroupItem, ...] = ()
    sources: tuple[SessionAssemblySourceItem, ...] = ()
    issues: tuple[SessionAssemblyIssueItem, ...] = ()
    draft: SessionAssemblyDraft | None = None
    has_unsaved_changes: bool = False
    error_message: str | None = None
    user_error: UserFacingError | None = None

    @property
    def can_create_session(self) -> bool:
        return self.draft is not None and self.draft.can_create_session


@dataclass(frozen=True, slots=True)
class ValidationIssueItem:
    """A UI-facing validation issue with acknowledgement state."""

    issue_ref: str
    code: str
    message: str
    severity: str
    location: str | None = None
    tool: str | None = None
    is_acknowledged: bool = False


@dataclass(frozen=True, slots=True)
class GeneratedArtifactItem:
    """A UI-facing generated artifact summary."""

    artifact_type: str
    location: Path
    description: str | None = None


@dataclass(frozen=True, slots=True)
class MetadataDisagreementSourceItem:
    """One source-specific value contributing to a mixed-source disagreement."""

    source_id: str
    source_label: str
    role: str
    extracted_key: str
    value: str
    override_value: str | None = None


@dataclass(frozen=True, slots=True)
class MetadataDisagreementItem:
    """A resolved canonical metadata value that still needs mixed-source review."""

    canonical_key: str
    resolved_value: str
    resolved_origin: str
    source_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    source_values: tuple[MetadataDisagreementSourceItem, ...] = ()
    session_override_value: str | None = None
    resolution_status: str = "pending"
    resolution_notes: tuple[str, ...] = ()
    resolution_history: tuple[str, ...] = ()
    pending_resolution: bool = True


@dataclass(frozen=True, slots=True)
class ConversionSessionScreenState:
    """State consumable by a conversion-session screen."""

    session: ConversionSession | None = None
    sources: tuple[ConversionSourceItem, ...] = ()
    preview: ConversionPreview | None = None
    execution: ConversionExecution | None = None
    persisted_validation_summary: ValidationSummary | None = None
    persisted_review_outcome: ValidationReviewOutcome | None = None
    progress_event: PipelineProgressEvent | None = None
    output_path: Path | None = None
    generated_artifacts: tuple[GeneratedArtifactItem, ...] = ()
    validation_issues: tuple[ValidationIssueItem, ...] = ()
    metadata_disagreements: tuple[MetadataDisagreementItem, ...] = ()
    reviewer_name: str = ""
    review_rationale: str = ""
    override_blocks_completion: bool = False
    last_review_submission: ReviewSubmission | None = None
    review_message: str | None = None
    recovery_message: str | None = None
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

    @property
    def can_submit_review(self) -> bool:
        return (
            self.execution is not None
            and bool(self.reviewer_name.strip())
            and not self.is_preview_running
            and not self.is_execution_running
        )

    @property
    def acknowledged_issue_refs(self) -> tuple[str, ...]:
        return tuple(issue.issue_ref for issue in self.validation_issues if issue.is_acknowledged)


@dataclass(frozen=True, slots=True)
class SettingsScreenState:
    """State consumable by a desktop settings screen."""

    applied_settings: UiSettings = field(default_factory=UiSettings)
    verbose_logging_enabled: bool = False
    file_logging_enabled: bool = False
    log_file_path: str = str(UiSettings().log_file_path)
    last_open_project_path: str = ""
    recent_project_paths: tuple[str, ...] = ()
    last_open_session_path: str = ""
    recent_session_paths: tuple[str, ...] = ()
    last_output_directory: str = ""
    has_unsaved_changes: bool = False
    status_message: str = "Ready."
    user_error: UserFacingError | None = None


def conversion_source_items(sources: tuple[SourceReference, ...]) -> tuple[ConversionSourceItem, ...]:
    """Project domain source references into UI-facing source summaries."""

    return tuple(
        ConversionSourceItem(
            source_id=source.source_id,
            label=source.label,
            source_type=source.source_type.value,
            location=source.location,
            role=source.role,
            adapter_hint=source.adapter_hint,
            media_type=source.media_type,
        )
        for source in sources
    )


def default_file_menu_entries() -> tuple[FileMenuEntry, ...]:
    """Return the current file-menu baseline for the desktop shell."""

    return (
        FileMenuEntry(
            action=FileMenuAction.NEW_SESSION,
            label="New Session",
        ),
        FileMenuEntry(
            action=FileMenuAction.OPEN_PROJECT,
            label="Open Project...",
        ),
        FileMenuEntry(
            action=FileMenuAction.SAVE_PROJECT,
            label="Save Project",
        ),
        FileMenuEntry(
            action=FileMenuAction.SAVE_PROJECT_AS,
            label="Save Project As...",
        ),
        FileMenuEntry(
            action=FileMenuAction.OPEN_SESSION,
            label="Open Session...",
        ),
        FileMenuEntry(
            action=FileMenuAction.REOPEN_LAST_SESSION,
            label="Reopen Last Session",
        ),
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
SettingsScreenStateListener = Callable[[SettingsScreenState], None]
SessionAssemblyStateListener = Callable[[SessionAssemblyState], None]
