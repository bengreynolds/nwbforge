"""Backend service for assembling draft conversion sessions from real inputs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import logging

from nwbforge.adapters import AdapterRegistry
from nwbforge.adapters.base import SourceAdapter
from nwbforge.app.logging import get_logger, log_event
from nwbforge.domain.enums import ConversionPathway, IssueSeverity, SessionStatus, SourceType
from nwbforge.domain.models import ConversionSession, SourceReference


@dataclass(frozen=True, slots=True)
class SessionAssemblyIssue:
    """A reviewable issue discovered while assembling a session draft."""

    code: str
    message: str
    severity: IssueSeverity
    location: Path | None = None


@dataclass(frozen=True, slots=True)
class SessionAssemblySource:
    """A UI-facing draft source assembled from one selected path."""

    source_id: str
    ingest_kind: str
    selection_label: str
    route_name: str | None
    group_key: str
    group_label: str
    location: Path
    source_type: SourceType
    label: str
    matching_adapter_ids: tuple[str, ...]
    suggested_adapter_id: str | None
    suggested_pathway: ConversionPathway
    entry_path_kind: str | None = None
    entry_role_label: str | None = None
    entry_validation_status: str | None = None
    structured_bundle_member_count: int = 0
    structured_bundle_member_labels: tuple[str, ...] = ()
    workflow_adapter_id: str | None = None
    workflow_display_name: str | None = None
    role: str = "primary"
    metadata_overrides: dict[str, str] | None = None
    sidecar_for_source_id: str | None = None
    sidecar_for_label: str | None = None
    context_source_id: str | None = None
    context_label: str | None = None
    needs_review: bool = False


@dataclass(frozen=True, slots=True)
class SessionAssemblyGroup:
    """A reviewable grouping suggestion spanning one or more assembled sources."""

    group_key: str
    group_label: str
    suggested_pathway: ConversionPathway
    source_ids: tuple[str, ...]
    source_count: int
    group_kind: str = "folder"
    anchor_path: Path | None = None
    canonical_source_id: str | None = None
    canonical_source_label: str | None = None
    canonical_source_path: Path | None = None
    canonical_entry_role_label: str | None = None
    canonical_selection_label: str | None = None
    canonical_bundle_member_count: int = 0
    canonical_bundle_member_labels: tuple[str, ...] = ()
    workflow_adapter_id: str | None = None
    workflow_display_name: str | None = None
    grouping_reason: str = ""
    member_labels: tuple[str, ...] = ()
    primary_count: int = 0
    supplemental_count: int = 0
    metadata_count: int = 0
    review_issue_count: int = 0
    requires_confirmation: bool = False
    needs_review: bool = False
    is_confirmed: bool = False


@dataclass(frozen=True, slots=True)
class SessionAssemblyDraft:
    """A suggested conversion-session draft built from selected real inputs."""

    session_id: str
    title: str | None
    pathway: ConversionPathway
    sources: tuple[SessionAssemblySource, ...]
    groups: tuple[SessionAssemblyGroup, ...]
    issues: tuple[SessionAssemblyIssue, ...]
    metadata_overrides: dict[str, str]
    source_metadata_overrides: dict[str, dict[str, str]]

    @property
    def can_create_session(self) -> bool:
        return bool(self.sources) and not any(issue.severity is IssueSeverity.ERROR for issue in self.issues)


@dataclass(frozen=True, slots=True)
class SessionAssemblyWorkspace:
    """Persistable in-progress state for the direct-ingest session builder."""

    selected_paths: tuple[Path, ...]
    source_intents: dict[str, dict[str, str]] | None = None
    project_path: Path | None = None
    has_unsaved_changes: bool = False
    session_id: str = ""
    title: str = ""
    source_roles: dict[str, str] | None = None
    group_overrides: dict[str, str] | None = None
    confirmed_group_keys: tuple[str, ...] | None = None
    metadata_overrides: dict[str, str] | None = None
    source_metadata_overrides: dict[str, dict[str, str]] | None = None


@dataclass(frozen=True, slots=True)
class SupportedRouteEntryProfile:
    """First-pass expectations for one structured supported-route entry path."""

    entry_kind: str
    entry_role_label: str
    file_suffixes: tuple[str, ...] = ()
    file_names: tuple[str, ...] = ()
    directory_markers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StructuredBundlePreview:
    """Conservative summary of files represented by one structured entry path."""

    member_count: int = 0
    member_labels: tuple[str, ...] = ()
    member_paths: tuple[Path, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkflowGroupingMatch:
    """One conservative direct-ingest grouping matched to a workflow adapter."""

    workflow_adapter_id: str
    workflow_display_name: str
    member_paths: tuple[Path, ...]
    group_key: str
    group_label: str
    context_source_id: str | None
    context_label: str | None


class JsonSessionAssemblyWorkspaceStore:
    """Persist in-progress session assembly state for desktop reopen flows."""

    def __init__(self, workspace_path: Path) -> None:
        self._workspace_path = workspace_path

    def save(self, workspace: SessionAssemblyWorkspace) -> None:
        payload = {
            "selected_paths": [str(path) for path in workspace.selected_paths],
            "source_intents": {
                str(path_text): {
                    str(key): str(value)
                    for key, value in dict(intent).items()
                    if str(value).strip()
                }
                for path_text, intent in dict(workspace.source_intents or {}).items()
                if intent
            },
            "project_path": str(workspace.project_path) if workspace.project_path is not None else None,
            "has_unsaved_changes": workspace.has_unsaved_changes,
            "session_id": workspace.session_id,
            "title": workspace.title,
            "source_roles": dict(workspace.source_roles or {}),
            "group_overrides": dict(workspace.group_overrides or {}),
            "confirmed_group_keys": tuple(workspace.confirmed_group_keys or ()),
            "metadata_overrides": dict(workspace.metadata_overrides or {}),
            "source_metadata_overrides": {
                str(source_id): {
                    str(key): str(value)
                    for key, value in overrides.items()
                    if str(value).strip()
                }
                for source_id, overrides in (workspace.source_metadata_overrides or {}).items()
                if overrides
            },
        }
        self._workspace_path.parent.mkdir(parents=True, exist_ok=True)
        self._workspace_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def load(self) -> SessionAssemblyWorkspace | None:
        if not self._workspace_path.exists():
            return None
        payload = json.loads(self._workspace_path.read_text(encoding="utf-8"))
        return SessionAssemblyWorkspace(
            selected_paths=tuple(Path(path) for path in payload.get("selected_paths", ())),
            source_intents={
                str(path_text): {
                    str(key): str(value)
                    for key, value in dict(intent).items()
                }
                for path_text, intent in dict(payload.get("source_intents", {})).items()
            },
            project_path=Path(payload["project_path"]) if payload.get("project_path") else None,
            has_unsaved_changes=bool(payload.get("has_unsaved_changes", False)),
            session_id=str(payload.get("session_id", "")),
            title=str(payload.get("title", "")),
            source_roles={str(key): str(value) for key, value in dict(payload.get("source_roles", {})).items()},
            group_overrides={str(key): str(value) for key, value in dict(payload.get("group_overrides", {})).items()},
            confirmed_group_keys=tuple(str(key) for key in payload.get("confirmed_group_keys", ())),
            metadata_overrides={
                str(key): str(value) for key, value in dict(payload.get("metadata_overrides", {})).items()
            },
            source_metadata_overrides={
                str(source_id): {
                    str(key): str(value)
                    for key, value in dict(overrides).items()
                }
                for source_id, overrides in dict(payload.get("source_metadata_overrides", {})).items()
            },
        )

    def clear(self) -> None:
        if self._workspace_path.exists():
            self._workspace_path.unlink()


class SessionAssemblyService:
    """Inspect selected paths and assemble a suggested conversion-session draft."""

    _logger = get_logger(__name__)
    _VALID_SOURCE_ROLES = {"primary", "supplemental", "metadata"}
    _DESKTOP_SESSION_FILENAMES = {"session_manifest.json", "custom_session.json", "hybrid_session.json"}
    _METADATA_SIDECAR_SUFFIXES = {".json", ".yaml", ".yml", ".txt"}
    _BUNDLE_PREVIEW_LIMIT = 5
    _CUSTOM_ALLOWED_FILE_SUFFIXES = {
        ".avi",
        ".bin",
        ".bmp",
        ".continuous",
        ".csv",
        ".dat",
        ".env",
        ".flv",
        ".gif",
        ".h5",
        ".hdf5",
        ".isxd",
        ".jpeg",
        ".jpg",
        ".json",
        ".mat",
        ".mesc",
        ".mkv",
        ".mov",
        ".mp4",
        ".nev",
        ".nse",
        ".ntt",
        ".oebin",
        ".pl2",
        ".plx",
        ".png",
        ".raw",
        ".rec",
        ".rhd",
        ".rhs",
        ".sbx",
        ".set",
        ".smr",
        ".smrx",
        ".tbk",
        ".tdx",
        ".tev",
        ".tif",
        ".tiff",
        ".tin",
        ".tsq",
        ".tsv",
        ".txt",
        ".wav",
        ".wmv",
        ".xlsm",
        ".xlsx",
        ".xml",
        ".yaml",
        ".yml",
    }
    _ROUTE_ADAPTER_IDS: dict[str, tuple[str, ...]] = {
        "audio": ("neuroconv_audio",),
        "alphaomega": ("neuroconv_alphaomega",),
        "axon": ("neuroconv_axon",),
        "axona": ("neuroconv_axona",),
        "biocam": ("neuroconv_biocam",),
        "blackrock": ("neuroconv_blackrock", "neuroconv_blackrock_sorting"),
        "brukertiff": ("neuroconv_brukertiff_singleplane", "neuroconv_brukertiff_multiplane"),
        "caiman": ("neuroconv_caiman_segmentation",),
        "cellexplorer": ("neuroconv_cellexplorer_sorting",),
        "cnmfe": ("neuroconv_cnmfe_segmentation",),
        "deeplabcut": ("neuroconv_deeplabcut",),
        "edf": ("neuroconv_edf",),
        "excel": ("neuroconv_excel_time_intervals",),
        "extract": ("neuroconv_extract_segmentation",),
        "femtonics": ("neuroconv_femtonics",),
        "hdf5": ("neuroconv_hdf5_imaging",),
        "image": ("neuroconv_image",),
        "inscopix": ("neuroconv_inscopix", "neuroconv_inscopix_segmentation"),
        "intan": ("neuroconv_intan",),
        "kilosort": ("neuroconv_kilosort_sorting",),
        "lightningpose": ("neuroconv_lightningpose",),
        "maxone": ("neuroconv_maxone",),
        "mcsraw": ("neuroconv_mcsraw",),
        "mearec": ("neuroconv_mearec",),
        "medpc": ("neuroconv_medpc",),
        "micromanager": ("neuroconv_micromanager_tiff",),
        "miniscope": ("neuroconv_miniscope",),
        "neuralynx": (
            "neuroconv_neuralynx",
            "neuroconv_neuralynx_sorting",
            "neuroconv_neuralynx_nvt",
        ),
        "neuroscope": ("neuroconv_neuroscope", "neuroconv_neuroscope_sorting"),
        "openephys_binary": ("neuroconv_openephys_binary", "neuroconv_openephys_binary_analog"),
        "openephys_legacy": ("neuroconv_openephys_legacy",),
        "phy": ("neuroconv_phy_sorting",),
        "plexon": ("neuroconv_plexon", "neuroconv_plexon_sorting"),
        "plexon2": ("neuroconv_plexon2",),
        "scanbox": ("neuroconv_scanbox",),
        "scanimage": ("neuroconv_scanimage",),
        "scanimage_legacy": ("neuroconv_scanimage_legacy",),
        "sleap": ("neuroconv_sleap",),
        "spike2": ("neuroconv_spike2",),
        "spikegadgets": ("neuroconv_spikegadgets",),
        "spikeglx": ("neuroconv_spikeglx",),
        "suite2p": ("neuroconv_suite2p_segmentation",),
        "tdt": ("neuroconv_tdt",),
        "tdt_fiber_photometry": ("neuroconv_tdt_fiber_photometry",),
        "thor": ("neuroconv_thor",),
        "tiff": ("neuroconv_tiff_imaging",),
        "videos": ("neuroconv_video",),
        "whitematter": ("neuroconv_whitematter",),
        "session_manifest": ("session_manifest",),
        "custom_session": ("custom_json_session",),
    }
    _ROUTE_ENTRY_PROFILES: dict[str, SupportedRouteEntryProfile] = {
        "audio": SupportedRouteEntryProfile(
            entry_kind="either",
            entry_role_label="audio file or root directory",
            file_suffixes=(".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff"),
        ),
        "deeplabcut": SupportedRouteEntryProfile(
            entry_kind="file",
            entry_role_label="project or result file",
            file_suffixes=(".csv", ".h5"),
        ),
        "excel": SupportedRouteEntryProfile(
            entry_kind="file",
            entry_role_label="spreadsheet",
            file_suffixes=(".xlsx", ".xlsm", ".xls"),
        ),
        "hdf5": SupportedRouteEntryProfile(
            entry_kind="file",
            entry_role_label="main imaging file",
            file_suffixes=(".h5", ".hdf5"),
        ),
        "image": SupportedRouteEntryProfile(
            entry_kind="either",
            entry_role_label="image file or root directory",
            file_suffixes=(".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff"),
        ),
        "lightningpose": SupportedRouteEntryProfile(
            entry_kind="file",
            entry_role_label="result file",
            file_suffixes=(".csv",),
        ),
        "micromanager": SupportedRouteEntryProfile(
            entry_kind="either",
            entry_role_label="main imaging file or root directory",
            file_suffixes=(".tif", ".tiff"),
        ),
        "scanbox": SupportedRouteEntryProfile(
            entry_kind="file",
            entry_role_label="main imaging file",
            file_suffixes=(".sbx",),
        ),
        "scanimage": SupportedRouteEntryProfile(
            entry_kind="either",
            entry_role_label="main imaging file or root directory",
            file_suffixes=(".tif", ".tiff"),
        ),
        "scanimage_legacy": SupportedRouteEntryProfile(
            entry_kind="either",
            entry_role_label="main imaging file or root directory",
            file_suffixes=(".tif", ".tiff"),
        ),
        "session_manifest": SupportedRouteEntryProfile(
            entry_kind="either",
            entry_role_label="manifest file or session directory",
            file_names=("session_manifest.json",),
            directory_markers=("session_manifest.json",),
        ),
        "sleap": SupportedRouteEntryProfile(
            entry_kind="file",
            entry_role_label="project or result file",
            file_suffixes=(".csv", ".h5", ".slp"),
        ),
        "suite2p": SupportedRouteEntryProfile(
            entry_kind="directory",
            entry_role_label="root directory",
        ),
        "tdt": SupportedRouteEntryProfile(
            entry_kind="directory",
            entry_role_label="block directory",
        ),
        "tdt_fiber_photometry": SupportedRouteEntryProfile(
            entry_kind="directory",
            entry_role_label="block directory",
        ),
        "thor": SupportedRouteEntryProfile(
            entry_kind="file",
            entry_role_label="main imaging file",
            file_suffixes=(".tif", ".tiff"),
        ),
        "tiff": SupportedRouteEntryProfile(
            entry_kind="either",
            entry_role_label="main imaging file or root directory",
            file_suffixes=(".tif", ".tiff"),
        ),
        "videos": SupportedRouteEntryProfile(
            entry_kind="either",
            entry_role_label="video file or root directory",
            file_suffixes=(".avi", ".flv", ".mkv", ".mov", ".mp4", ".wmv"),
        ),
    }

    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry

    def filter_custom_selected_paths(
        self,
        selected_paths: tuple[Path, ...],
    ) -> tuple[tuple[Path, ...], tuple[str, ...]]:
        """Return accepted custom paths plus rejection messages for unsupported selections."""

        accepted: list[Path] = []
        rejected_messages: list[str] = []
        for path in self._normalize_paths(selected_paths):
            if self._is_supported_custom_path(path):
                accepted.append(path)
                continue
            rejected_messages.append(
                f"Ignored custom input '{path.name}' because its file type is not currently accepted for direct ingest."
            )
        return tuple(accepted), tuple(rejected_messages)

    def validate_supported_selected_paths(
        self,
        selected_paths: tuple[Path, ...],
        *,
        route_name: str,
        route_display_name: str,
    ) -> tuple[tuple[Path, ...], dict[str, dict[str, str]], tuple[str, ...]]:
        """Validate supported-route entry selections and return accepted intents plus rejections."""

        accepted_paths: list[Path] = []
        accepted_intents: dict[str, dict[str, str]] = {}
        rejected_messages: list[str] = []
        for path in self._normalize_paths(selected_paths):
            intent, rejection_message = self._validate_supported_selected_path(
                path,
                route_name=route_name,
                route_display_name=route_display_name,
            )
            if rejection_message is not None:
                rejected_messages.append(rejection_message)
                continue
            accepted_paths.append(path)
            accepted_intents[str(path.resolve())] = intent
        return tuple(accepted_paths), accepted_intents, tuple(rejected_messages)

    def assemble_draft(
        self,
        selected_paths: tuple[Path, ...],
        *,
        source_intents: dict[str, dict[str, str]] | None = None,
        session_id: str | None = None,
        title: str | None = None,
        source_roles: dict[str, str] | None = None,
        group_overrides: dict[str, str] | None = None,
        confirmed_group_keys: tuple[str, ...] | None = None,
        metadata_overrides: dict[str, str] | None = None,
        source_metadata_overrides: dict[str, dict[str, str]] | None = None,
    ) -> SessionAssemblyDraft:
        """Build a suggested session draft from one or more selected files or folders."""

        normalized_paths = self._normalize_paths(selected_paths)
        sidecar_links = self._detect_sidecar_links(normalized_paths)
        source_ids_by_path: dict[Path, str] = {}
        existing_ids: list[str] = []
        for path in normalized_paths:
            source_id = self._build_source_id(path, tuple(existing_ids))
            existing_ids.append(source_id)
            source_ids_by_path[path.resolve()] = source_id

        draft_sources: list[SessionAssemblySource] = []
        issues: list[SessionAssemblyIssue] = []
        normalized_source_roles = {
            str(key): self._normalize_source_role(value)
            for key, value in (source_roles or {}).items()
        }
        normalized_source_intents = {
            str(Path(path_text).resolve()): {
                str(key): str(value).strip()
                for key, value in dict(intent).items()
                if str(value).strip()
            }
            for path_text, intent in (source_intents or {}).items()
            if intent
        }
        normalized_group_overrides = {
            str(key): str(value).strip()
            for key, value in (group_overrides or {}).items()
            if str(value).strip()
        }
        normalized_confirmed_group_keys = {
            str(group_key).strip()
            for group_key in (confirmed_group_keys or ())
            if str(group_key).strip()
        }
        normalized_metadata_overrides = {
            str(key): str(value).strip()
            for key, value in (metadata_overrides or {}).items()
            if str(value).strip()
        }
        normalized_source_metadata_overrides = {
            str(source_id): {
                str(key): str(value).strip()
                for key, value in dict(overrides).items()
                if str(value).strip()
            }
            for source_id, overrides in (source_metadata_overrides or {}).items()
            if overrides
        }
        workflow_group_matches = self._detect_workflow_group_matches(
            normalized_paths,
            normalized_source_intents,
            source_ids_by_path,
            normalized_source_roles,
        )
        structured_bundle_previews = self._structured_bundle_previews_for_paths(
            normalized_paths,
            normalized_source_intents,
        )
        absorbed_member_paths = self._absorbed_structured_member_paths(
            normalized_paths,
            normalized_source_intents,
            structured_bundle_previews,
        )
        group_assignments = self._group_assignments(
            normalized_paths,
            sidecar_links,
            normalized_source_intents,
            source_ids_by_path,
            workflow_group_matches,
        )
        supported_anchor_details = self._supported_anchor_details(
            normalized_paths,
            normalized_source_intents,
            source_ids_by_path,
        )
        log_event(
            self._logger,
            logging.INFO,
            "Assembling direct-ingest session draft.",
            selected_path_count=len(normalized_paths),
            group_count=len(self._grouped_paths(
                normalized_paths,
                sidecar_links,
                normalized_source_intents,
                source_ids_by_path,
                workflow_group_matches,
            )),
            sidecar_link_count=len(sidecar_links),
            structured_anchor_count=len(supported_anchor_details),
            absorbed_structured_member_count=len(absorbed_member_paths),
            workflow_group_count=len(workflow_group_matches),
            requested_session_id=session_id or "",
        )

        for index, path in enumerate(normalized_paths, start=1):
            resolved_path = path.resolve()
            absorbed_anchor = absorbed_member_paths.get(resolved_path)
            if absorbed_anchor is not None:
                absorbed_intent = normalized_source_intents.get(str(absorbed_anchor), {})
                anchor_selection_label = absorbed_intent.get("route_display_name") or absorbed_anchor.name
                issues.append(
                    SessionAssemblyIssue(
                        code="session-assembly-structured-member-absorbed",
                        message=(
                            f"Selected path '{path.name}' is already represented by the structured source "
                            f"'{anchor_selection_label}' and will remain inside that dataset bundle."
                        ),
                        severity=IssueSeverity.INFO,
                        location=path,
                    )
                )
                continue
            source_id = source_ids_by_path[path.resolve()]
            group_key, group_label, context_source_id, context_label = group_assignments[path.resolve()]
            override_group = normalized_group_overrides.get(source_id)
            if override_group:
                group_key = f"manual:{override_group.lower()}"
                group_label = override_group
            source_intent = normalized_source_intents.get(str(path.resolve()), {})
            ingest_kind = (
                "supported" if source_intent.get("ingest_kind") == "supported" else "custom"
            )
            route_name = source_intent.get("route_name") or None
            route_display_name = source_intent.get("route_display_name") or None
            entry_path_kind = source_intent.get("entry_path_kind") or None
            entry_role_label = source_intent.get("entry_role_label") or None
            entry_validation_status = source_intent.get("entry_validation_status") or None
            selection_label = route_display_name or ("Custom" if ingest_kind == "custom" else "NeuroConv")
            source_reference = self._build_matching_source_reference(
                source_id=source_id,
                path=path,
                route_name=route_name,
            )
            structured_bundle = (
                structured_bundle_previews.get(resolved_path, StructuredBundlePreview())
                if ingest_kind == "supported"
                else StructuredBundlePreview()
            )
            matches = self._matching_adapters_for_route(source_reference, route_name)
            matching_ids = tuple(adapter.adapter_id for adapter in matches)
            suggested_pathway = (
                ConversionPathway.SUPPORTED
                if ingest_kind == "supported" and not matches
                else self._suggest_source_pathway(matches)
            )
            suggested_adapter_id = matching_ids[0] if len(matching_ids) == 1 else None
            needs_review = len(matching_ids) != 1
            sidecar_anchor = sidecar_links.get(path.resolve())
            nearby_anchor_candidates = (
                self._supported_anchor_candidates_for_path(path, supported_anchor_details)
                if ingest_kind == "custom" and sidecar_anchor is None and context_source_id is None
                else ()
            )
            workflow_match = workflow_group_matches.get(group_key)
            role = normalized_source_roles.get(source_id, self._default_role_for_index(index, sidecar_anchor is not None))

            if ingest_kind == "supported" and route_name and not matching_ids:
                issues.append(
                    SessionAssemblyIssue(
                        code="session-assembly-selected-route-mismatch",
                        message=(
                            f"The selected source for '{selection_label}' did not match the expected adapter family. "
                            "Review the chosen NeuroConv package and dataset entry path before preview."
                        ),
                        severity=IssueSeverity.ERROR,
                        location=path,
                    )
                )
            elif not matching_ids:
                issues.append(
                    SessionAssemblyIssue(
                        code="session-assembly-no-adapter-match",
                        message=(
                            f"No registered adapter matched '{path.name}'. The source will be treated as "
                            "custom and will require review."
                        ),
                        severity=IssueSeverity.WARNING,
                        location=path,
                    )
                )
            elif len(matching_ids) > 1:
                issues.append(
                    SessionAssemblyIssue(
                        code="session-assembly-ambiguous-adapter-match",
                        message=(
                            f"Multiple adapters matched '{path.name}': {', '.join(matching_ids)}. "
                            "Review adapter selection before preview."
                        ),
                        severity=IssueSeverity.WARNING,
                        location=path,
                    )
                )

            if sidecar_anchor is not None:
                issues.append(
                    SessionAssemblyIssue(
                        code="session-assembly-sidecar-association",
                        message=(
                            f"Associated likely metadata sidecar '{path.name}' with '{sidecar_anchor.name}'. "
                            "Review the grouping and role before preview."
                        ),
                        severity=IssueSeverity.INFO,
                        location=path,
                    )
                )
            elif context_source_id is not None and ingest_kind == "custom":
                issues.append(
                    SessionAssemblyIssue(
                        code="session-assembly-custom-context-association",
                        message=(
                            f"Associated custom input '{path.name}' with structured source '{context_label}'. "
                            "Review the bundle and role before preview."
                        ),
                        severity=IssueSeverity.INFO,
                        location=path,
                    )
                )
            elif len(nearby_anchor_candidates) > 1:
                issues.append(
                    SessionAssemblyIssue(
                        code="session-assembly-ambiguous-custom-context",
                        message=(
                            f"Custom input '{path.name}' is near multiple structured dataset selections. "
                            "It remains separate until you review the grouping."
                        ),
                        severity=IssueSeverity.WARNING,
                        location=path,
                    )
                )

            draft_sources.append(
                SessionAssemblySource(
                    source_id=source_reference.source_id,
                    ingest_kind=ingest_kind,
                    selection_label=selection_label,
                    route_name=route_name,
                    group_key=group_key,
                    group_label=group_label,
                    location=path,
                    source_type=source_reference.source_type,
                    label=source_reference.label,
                    matching_adapter_ids=matching_ids,
                    suggested_adapter_id=suggested_adapter_id,
                    suggested_pathway=suggested_pathway,
                    entry_path_kind=entry_path_kind,
                    entry_role_label=entry_role_label,
                    entry_validation_status=entry_validation_status,
                    structured_bundle_member_count=structured_bundle.member_count,
                    structured_bundle_member_labels=structured_bundle.member_labels,
                    workflow_adapter_id=workflow_match.workflow_adapter_id if workflow_match is not None else None,
                    workflow_display_name=workflow_match.workflow_display_name if workflow_match is not None else None,
                    role=role,
                    metadata_overrides=dict(normalized_source_metadata_overrides.get(source_id, {})),
                    sidecar_for_source_id=source_ids_by_path.get(sidecar_anchor) if sidecar_anchor is not None else None,
                    sidecar_for_label=sidecar_anchor.name if sidecar_anchor is not None else None,
                    context_source_id=context_source_id,
                    context_label=context_label,
                    needs_review=needs_review,
                )
            )

        grouped_sources: dict[str, list[SessionAssemblySource]] = {}
        for source in draft_sources:
            grouped_sources.setdefault(source.group_key, []).append(source)

        group_summaries: list[SessionAssemblyGroup] = []

        for group_key, sources in grouped_sources.items():
            group_label = sources[0].group_label
            group_pathways = {source.suggested_pathway for source in sources}
            group_pathway = (
                ConversionPathway.HYBRID if len(group_pathways) > 1 else next(iter(group_pathways))
            )
            is_confirmed = group_key in normalized_confirmed_group_keys
            auto_grouped = len(sources) > 1 and not any(source.group_key.startswith("manual:") for source in sources)
            requires_confirmation = auto_grouped or len(group_pathways) > 1
            needs_group_review = any(source.needs_review for source in sources) or (
                not is_confirmed and requires_confirmation
            )
            anchor_path = (
                sources[0].location.parent if sources[0].location.is_file() else sources[0].location
            )
            group_kind = self._group_kind_for_key(group_key, sources)
            canonical_source = self._canonical_source_for_group(group_key, sources)
            workflow_match = workflow_group_matches.get(group_key)
            grouping_reason = self._group_reason_for(
                group_key=group_key,
                sources=sources,
                group_kind=group_kind,
                group_pathways=group_pathways,
                workflow_display_name=workflow_match.workflow_display_name if workflow_match is not None else None,
            )
            review_issue_count = sum(1 for source in sources if source.needs_review)

            if auto_grouped and not is_confirmed:
                issues.append(
                    SessionAssemblyIssue(
                        code="session-assembly-auto-grouped-inputs",
                        message=(
                            f"Auto-grouped {len(sources)} selected inputs under '{group_label}'. "
                            "Confirm they belong to the same conversion session."
                        ),
                        severity=IssueSeverity.INFO,
                        location=(
                            sources[0].location.parent
                            if sources[0].location.is_file()
                            else sources[0].location
                        ),
                    )
                )

            if len(group_pathways) > 1 and not is_confirmed:
                issues.append(
                    SessionAssemblyIssue(
                        code="session-assembly-mixed-group-pathways",
                        message=(
                            f"Grouped sources under '{group_label}' span supported and custom-looking inputs. "
                            "Review the bundle before preview."
                        ),
                        severity=IssueSeverity.WARNING,
                        location=(
                            sources[0].location.parent
                            if sources[0].location.is_file()
                            else sources[0].location
                        ),
                    )
                )

            if requires_confirmation and not is_confirmed:
                issues.append(
                    SessionAssemblyIssue(
                        code="session-assembly-unconfirmed-group",
                        message=(
                            f"Confirm grouped dataset '{group_label}' before creating a conversion session."
                        ),
                        severity=IssueSeverity.ERROR,
                        location=anchor_path,
                    )
                )

            group_summaries.append(
                SessionAssemblyGroup(
                    group_key=group_key,
                    group_label=group_label,
                    suggested_pathway=group_pathway,
                    source_ids=tuple(source.source_id for source in sources),
                    source_count=len(sources),
                    group_kind=group_kind,
                    anchor_path=anchor_path,
                    canonical_source_id=canonical_source.source_id if canonical_source is not None else None,
                    canonical_source_label=canonical_source.label if canonical_source is not None else None,
                    canonical_source_path=canonical_source.location if canonical_source is not None else None,
                    canonical_entry_role_label=(
                        canonical_source.entry_role_label if canonical_source is not None else None
                    ),
                    canonical_selection_label=(
                        canonical_source.selection_label if canonical_source is not None else None
                    ),
                    canonical_bundle_member_count=(
                        canonical_source.structured_bundle_member_count if canonical_source is not None else 0
                    ),
                    canonical_bundle_member_labels=(
                        canonical_source.structured_bundle_member_labels if canonical_source is not None else ()
                    ),
                    workflow_adapter_id=workflow_match.workflow_adapter_id if workflow_match is not None else None,
                    workflow_display_name=workflow_match.workflow_display_name if workflow_match is not None else None,
                    grouping_reason=grouping_reason,
                    member_labels=tuple(source.label for source in sources),
                    primary_count=sum(1 for source in sources if source.role == "primary"),
                    supplemental_count=sum(1 for source in sources if source.role == "supplemental"),
                    metadata_count=sum(1 for source in sources if source.role == "metadata"),
                    review_issue_count=review_issue_count + (
                        1 if requires_confirmation and not is_confirmed else 0
                    ),
                    requires_confirmation=requires_confirmation,
                    needs_review=needs_group_review,
                    is_confirmed=is_confirmed,
                )
            )

        suggested_session_id = session_id.strip() if session_id and session_id.strip() else self._build_session_id(normalized_paths)
        suggested_title = title.strip() if title and title.strip() else self._build_title(normalized_paths)

        if not draft_sources:
            issues.append(
                SessionAssemblyIssue(
                    code="session-assembly-no-inputs",
                    message="Add at least one file or folder before creating a conversion session.",
                    severity=IssueSeverity.ERROR,
                )
            )
        elif not any(source.role == "primary" for source in draft_sources):
            issues.append(
                SessionAssemblyIssue(
                    code="session-assembly-no-primary-source",
                    message="Select at least one primary source before creating a conversion session.",
                    severity=IssueSeverity.ERROR,
                )
            )

        return SessionAssemblyDraft(
            session_id=suggested_session_id,
            title=suggested_title,
            pathway=self._suggest_session_pathway(tuple(draft_sources)),
            sources=tuple(draft_sources),
            groups=tuple(sorted(group_summaries, key=lambda group: (group.group_label.lower(), group.group_key))),
            issues=tuple(issues),
            metadata_overrides=normalized_metadata_overrides,
            source_metadata_overrides=normalized_source_metadata_overrides,
        )

    def create_session(self, draft: SessionAssemblyDraft) -> ConversionSession:
        """Create a real conversion session from an assembled draft."""

        if not draft.can_create_session:
            raise ValueError("Session draft is not ready to create.")

        sidecar_ids_by_anchor: dict[str, tuple[str, ...]] = {}
        for source in draft.sources:
            if source.sidecar_for_source_id is None:
                continue
            sidecar_ids_by_anchor[source.sidecar_for_source_id] = tuple(
                dict.fromkeys(sidecar_ids_by_anchor.get(source.sidecar_for_source_id, ()) + (source.source_id,))
            )

        sources = tuple(
            SourceReference(
                source_id=source.source_id,
                location=source.location,
                source_type=source.source_type,
                label=source.label,
                role=source.role,
                adapter_hint=source.suggested_adapter_id,
                metadata={
                    "session_assembly.ingest_kind": source.ingest_kind,
                    "session_assembly.selection_label": source.selection_label,
                    "session_assembly.route_name": source.route_name or "",
                    "session_assembly.group_key": source.group_key,
                    "session_assembly.group_label": source.group_label,
                    "session_assembly.entry_path_kind": source.entry_path_kind or "",
                    "session_assembly.entry_role_label": source.entry_role_label or "",
                    "session_assembly.entry_validation_status": source.entry_validation_status or "",
                    "session_assembly.structured_bundle_member_count": str(source.structured_bundle_member_count),
                    "session_assembly.structured_bundle_member_labels_json": json.dumps(
                        list(source.structured_bundle_member_labels)
                    ),
                    "session_assembly.workflow_adapter_id": source.workflow_adapter_id or "",
                    "session_assembly.workflow_display_name": source.workflow_display_name or "",
                    "session_assembly.group_confirmed": str(
                        next(
                            (
                                group.is_confirmed
                                for group in draft.groups
                                if group.group_key == source.group_key
                            ),
                            False,
                        )
                    ).lower(),
                    "session_assembly.sidecar_for_source_id": source.sidecar_for_source_id or "",
                    "session_assembly.sidecar_for_label": source.sidecar_for_label or "",
                    "session_assembly.context_source_id": source.context_source_id or "",
                    "session_assembly.context_label": source.context_label or "",
                },
                sidecar_ids=sidecar_ids_by_anchor.get(source.source_id, ()),
            )
            for source in draft.sources
        )
        session = ConversionSession(
            session_id=draft.session_id,
            pathway=draft.pathway,
            sources=sources,
            title=draft.title,
            metadata_overrides=dict(draft.metadata_overrides),
            source_metadata_overrides={
                str(source_id): dict(overrides)
                for source_id, overrides in draft.source_metadata_overrides.items()
                if overrides
            },
        ).transition(status=SessionStatus.SOURCES_ADDED)
        log_event(
            self._logger,
            logging.INFO,
            "Created conversion session from direct-ingest draft.",
            session_id=session.session_id,
            pathway=session.pathway.value,
            source_count=len(session.sources),
        )
        return session

    @staticmethod
    def _normalize_paths(selected_paths: tuple[Path, ...]) -> tuple[Path, ...]:
        seen: set[Path] = set()
        normalized: list[Path] = []
        for path in selected_paths:
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            normalized.append(resolved)
        return tuple(normalized)

    def _build_source_id(self, path: Path, existing_ids: tuple[str, ...]) -> str:
        base = self._slugify(path.stem if path.is_file() else path.name) or "source"
        seen_ids = set(existing_ids)
        candidate = base
        counter = 2
        while candidate in seen_ids:
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    def _build_session_id(self, normalized_paths: tuple[Path, ...]) -> str:
        if not normalized_paths:
            return "new-conversion-session"
        first = normalized_paths[0]
        base = self._slugify(first.stem if first.is_file() else first.name) or "session"
        if len(normalized_paths) == 1:
            return f"session-{base}"
        return f"session-{base}-{len(normalized_paths)}-sources"

    @staticmethod
    def _build_title(normalized_paths: tuple[Path, ...]) -> str | None:
        if not normalized_paths:
            return None
        first = normalized_paths[0]
        if len(normalized_paths) == 1:
            return f"Conversion for {first.name}"
        return f"Conversion for {first.name} and {len(normalized_paths) - 1} more sources"

    def _validate_supported_selected_path(
        self,
        path: Path,
        *,
        route_name: str,
        route_display_name: str,
    ) -> tuple[dict[str, str], str | None]:
        profile = self._ROUTE_ENTRY_PROFILES.get(route_name)
        if profile is not None:
            rejection = self._validate_supported_path_against_profile(
                path,
                route_display_name=route_display_name,
                profile=profile,
            )
            if rejection is not None:
                return {}, rejection
        source_reference = self._build_matching_source_reference(
            source_id="supported-selection",
            path=path,
            route_name=route_name,
        )
        matches = self._matching_adapters_for_route(source_reference, route_name)
        return (
            {
                "ingest_kind": "supported",
                "route_name": route_name,
                "route_display_name": route_display_name,
                "entry_path_kind": "directory" if path.is_dir() else "file",
                "entry_role_label": (
                    profile.entry_role_label
                    if profile is not None
                    else ("root directory" if path.is_dir() else "main file")
                ),
                "entry_validation_status": "validated" if matches else "review",
            },
            None,
        )

    @classmethod
    def _validate_supported_path_against_profile(
        cls,
        path: Path,
        *,
        route_display_name: str,
        profile: SupportedRouteEntryProfile,
    ) -> str | None:
        if profile.entry_kind == "file" and path.is_dir():
            return (
                f"Ignored '{path.name}' for {route_display_name} because this route expects a "
                f"{profile.entry_role_label}, not a folder."
            )
        if profile.entry_kind == "directory" and path.is_file():
            return (
                f"Ignored '{path.name}' for {route_display_name} because this route expects a "
                f"{profile.entry_role_label}, not a standalone file."
            )
        if path.is_file():
            lowered_name = path.name.lower()
            if profile.file_names and lowered_name not in profile.file_names:
                expected_names = ", ".join(profile.file_names)
                return (
                    f"Ignored '{path.name}' for {route_display_name} because the selected entry should be one of: "
                    f"{expected_names}."
                )
            if profile.file_suffixes and not cls._path_has_supported_suffix(path, profile.file_suffixes):
                expected_suffixes = ", ".join(profile.file_suffixes)
                return (
                    f"Ignored '{path.name}' for {route_display_name} because the selected entry should use one of: "
                    f"{expected_suffixes}."
                )
        if path.is_dir() and profile.directory_markers:
            if not any((path / marker).exists() for marker in profile.directory_markers):
                expected_markers = ", ".join(profile.directory_markers)
                return (
                    f"Ignored '{path.name}' for {route_display_name} because the selected directory does not contain "
                    f"the expected entry marker(s): {expected_markers}."
                )
        return None

    @classmethod
    def _build_matching_source_reference(
        cls,
        *,
        source_id: str,
        path: Path,
        route_name: str | None,
    ) -> SourceReference:
        allowed_adapter_ids = cls._ROUTE_ADAPTER_IDS.get(route_name or "")
        adapter_hint = allowed_adapter_ids[0] if allowed_adapter_ids and len(allowed_adapter_ids) == 1 else None
        return SourceReference(
            source_id=source_id,
            location=path,
            source_type=SourceType.DIRECTORY if path.is_dir() else SourceType.FILE,
            label=path.name,
            adapter_hint=adapter_hint,
        )

    def _matching_adapters_for_route(
        self,
        source_reference: SourceReference,
        route_name: str | None,
    ) -> tuple[SourceAdapter, ...]:
        matches = self._registry.matching_adapters(source_reference)
        return self._filter_matches_for_route(route_name, matches)

    @classmethod
    def _structured_bundle_previews_for_paths(
        cls,
        normalized_paths: tuple[Path, ...],
        source_intents: dict[str, dict[str, str]],
    ) -> dict[Path, StructuredBundlePreview]:
        previews: dict[Path, StructuredBundlePreview] = {}
        for path in normalized_paths:
            intent = source_intents.get(str(path.resolve()), {})
            if intent.get("ingest_kind") != "supported":
                continue
            previews[path.resolve()] = cls._structured_bundle_preview(
                path,
                route_name=intent.get("route_name") or None,
                entry_path_kind=intent.get("entry_path_kind") or None,
            )
        return previews

    @staticmethod
    def _absorbed_structured_member_paths(
        normalized_paths: tuple[Path, ...],
        source_intents: dict[str, dict[str, str]],
        bundle_previews: dict[Path, StructuredBundlePreview],
    ) -> dict[Path, Path]:
        selected_paths = {path.resolve() for path in normalized_paths}
        supported_anchors = {
            path.resolve()
            for path in normalized_paths
            if source_intents.get(str(path.resolve()), {}).get("ingest_kind") == "supported"
        }
        anchor_candidates_by_member: dict[Path, list[Path]] = {}
        for anchor_path, preview in bundle_previews.items():
            for member_path in preview.member_paths:
                resolved_member = member_path.resolve()
                if resolved_member == anchor_path:
                    continue
                if resolved_member not in selected_paths:
                    continue
                anchor_candidates_by_member.setdefault(resolved_member, []).append(anchor_path)
        absorbed_paths: dict[Path, Path] = {}
        for member_path, anchor_candidates in anchor_candidates_by_member.items():
            unique_candidates = tuple(
                sorted(dict.fromkeys(anchor_candidates), key=lambda item: item.as_posix().lower())
            )
            if len(unique_candidates) != 1:
                continue
            anchor_path = unique_candidates[0]
            if member_path in supported_anchors:
                continue
            absorbed_paths[member_path] = anchor_path
        return absorbed_paths

    @staticmethod
    def _path_has_supported_suffix(path: Path, suffixes: tuple[str, ...]) -> bool:
        lowered_suffixes = tuple(suffix.lower() for suffix in path.suffixes)
        if not lowered_suffixes:
            return False
        if lowered_suffixes[-1] in suffixes:
            return True
        for width in range(2, len(lowered_suffixes) + 1):
            if "".join(lowered_suffixes[-width:]) in suffixes:
                return True
        return False

    def _group_assignments(
        self,
        normalized_paths: tuple[Path, ...],
        sidecar_links: dict[Path, Path],
        source_intents: dict[str, dict[str, str]],
        source_ids_by_path: dict[Path, str],
        workflow_group_matches: dict[str, WorkflowGroupingMatch],
    ) -> dict[Path, tuple[str, str, str | None, str | None]]:
        descriptor_directories = {
            path.parent.resolve(): path
            for path in normalized_paths
            if path.is_file() and path.name.lower() in self._DESKTOP_SESSION_FILENAMES
        }
        assignments: dict[Path, tuple[str, str, str | None, str | None]] = {}
        supported_anchor_details = self._supported_anchor_details(
            normalized_paths,
            source_intents,
            source_ids_by_path,
        )

        for workflow_match in workflow_group_matches.values():
            for member_path in workflow_match.member_paths:
                assignments[member_path.resolve()] = (
                    workflow_match.group_key,
                    workflow_match.group_label,
                    workflow_match.context_source_id,
                    workflow_match.context_label,
                )
        for resolved, assignment in supported_anchor_details.items():
            assignments.setdefault(resolved, assignment)

        for path in normalized_paths:
            resolved = path.resolve()
            anchor = sidecar_links.get(resolved)
            if anchor is None:
                continue
            anchor_resolved = anchor.resolve()
            anchor_assignment = assignments.get(anchor_resolved)
            if anchor_assignment is None:
                anchor_assignment = (
                    f"sidecar-bundle:{anchor.parent.resolve().as_posix().lower()}:{anchor.stem.lower()}",
                    anchor.stem or anchor.parent.name or "Session",
                    source_ids_by_path.get(anchor_resolved),
                    anchor.name,
                )
                assignments[anchor_resolved] = anchor_assignment
            assignments[resolved] = anchor_assignment

        for path in normalized_paths:
            resolved = path.resolve()
            if resolved in assignments:
                continue
            anchor_candidates = self._supported_anchor_candidates_for_path(path, supported_anchor_details)
            if len(anchor_candidates) == 1:
                anchor_path = anchor_candidates[0]
                assignments[resolved] = supported_anchor_details[anchor_path]
                continue
            if len(anchor_candidates) > 1:
                candidate_assignments = {
                    assignments.get(anchor_path.resolve())
                    for anchor_path in anchor_candidates
                    if assignments.get(anchor_path.resolve()) is not None
                }
                if len(candidate_assignments) == 1:
                    shared_assignment = next(iter(candidate_assignments))
                    if shared_assignment is not None:
                        assignments[resolved] = shared_assignment
                        continue
            assignments[resolved] = self._base_group_for_path(path, descriptor_directories)
        return assignments

    def _detect_workflow_group_matches(
        self,
        normalized_paths: tuple[Path, ...],
        source_intents: dict[str, dict[str, str]],
        source_ids_by_path: dict[Path, str],
        source_roles: dict[str, str],
    ) -> dict[str, WorkflowGroupingMatch]:
        supported_paths = tuple(
            path
            for path in normalized_paths
            if source_intents.get(str(path.resolve()), {}).get("ingest_kind") == "supported"
        )
        if len(supported_paths) < 2:
            return {}

        supported_by_parent: dict[Path, list[Path]] = {}
        for path in supported_paths:
            supported_by_parent.setdefault(path.parent.resolve(), []).append(path)

        workflow_matches: dict[str, WorkflowGroupingMatch] = {}
        for parent_path, parent_supported_paths in supported_by_parent.items():
            if len(parent_supported_paths) < 2:
                continue
            candidate_sources = tuple(
                self._build_workflow_candidate_source(
                    path=path,
                    route_name=source_intents.get(str(path.resolve()), {}).get("route_name") or None,
                    source_id=source_ids_by_path[path.resolve()],
                    role=source_roles.get(
                        source_ids_by_path[path.resolve()],
                        self._default_role_for_index(normalized_paths.index(path) + 1),
                    ),
                )
                for path in parent_supported_paths
            )
            candidate_workflows = []
            for workflow_adapter in self._registry.matching_workflow_adapters(candidate_sources):
                match_sources = getattr(workflow_adapter, "match_sources", None)
                if not callable(match_sources):
                    continue
                matched_sources = match_sources(candidate_sources)
                if matched_sources is None or len(matched_sources) < 2:
                    continue
                matched_paths = tuple(
                    sorted(
                        {source.location.resolve() for source in matched_sources.values()},
                        key=lambda item: item.as_posix().lower(),
                    )
                )
                if len(matched_paths) < 2:
                    continue
                candidate_workflows.append((workflow_adapter, matched_paths, matched_sources))
            if len(candidate_workflows) != 1:
                continue
            workflow_adapter, matched_paths, matched_sources = candidate_workflows[0]
            canonical_source = self._workflow_canonical_source(matched_sources.values())
            group_key = f"workflow:{workflow_adapter.adapter_id}:{parent_path.as_posix().lower()}"
            group_label = parent_path.name or workflow_adapter.display_name
            workflow_matches[group_key] = WorkflowGroupingMatch(
                workflow_adapter_id=workflow_adapter.adapter_id,
                workflow_display_name=workflow_adapter.display_name,
                member_paths=matched_paths,
                group_key=group_key,
                group_label=group_label,
                context_source_id=canonical_source.source_id if canonical_source is not None else None,
                context_label=workflow_adapter.display_name,
            )
        return workflow_matches

    def _supported_anchor_details(
        self,
        normalized_paths: tuple[Path, ...],
        source_intents: dict[str, dict[str, str]],
        source_ids_by_path: dict[Path, str],
    ) -> dict[Path, tuple[str, str, str | None, str | None]]:
        details: dict[Path, tuple[str, str, str | None, str | None]] = {}
        for path in normalized_paths:
            intent = source_intents.get(str(path.resolve()), {})
            if intent.get("ingest_kind") != "supported":
                continue
            resolved = path.resolve()
            route_display_name = intent.get("route_display_name") or "NeuroConv"
            group_label = resolved.stem if resolved.is_file() else resolved.name or route_display_name
            context_label = route_display_name or group_label
            details[resolved] = (
                f"supported-anchor:{route_display_name.lower()}:{resolved.as_posix().lower()}",
                group_label,
                source_ids_by_path[resolved],
                context_label,
            )
        return details

    @staticmethod
    def _supported_anchor_candidates_for_path(
        path: Path,
        supported_anchor_details: dict[Path, tuple[str, str, str | None, str | None]],
    ) -> tuple[Path, ...]:
        resolved = path.resolve()
        candidates: list[Path] = []
        for anchor_path in supported_anchor_details:
            if anchor_path == resolved:
                continue
            if anchor_path.is_dir():
                if anchor_path in resolved.parents or resolved.parent == anchor_path.parent:
                    candidates.append(anchor_path)
                continue
            if resolved.parent == anchor_path.parent:
                candidates.append(anchor_path)
        return tuple(sorted(dict.fromkeys(candidates), key=lambda candidate: candidate.as_posix().lower()))

    def _base_group_for_path(
        self,
        path: Path,
        descriptor_directories: dict[Path, Path],
    ) -> tuple[str, str, str | None, str | None]:
        if path.is_dir():
            resolved = path.resolve()
            return str(resolved), resolved.name or "Session", None, None
        if path.name.lower() in self._DESKTOP_SESSION_FILENAMES:
            parent = path.parent.resolve()
            return str(parent), parent.name or path.stem, None, None
        parent = path.parent.resolve()
        if parent in descriptor_directories:
            return (f"descriptor-parent:{parent.as_posix().lower()}", parent.name or path.stem, None, None)
        if path.suffix.lower() in self._METADATA_SIDECAR_SUFFIXES:
            return (
                f"sidecar-stem:{parent.as_posix().lower()}:{path.stem.lower()}",
                path.stem or parent.name,
                None,
                None,
            )
        return (str(parent), parent.name or path.stem, None, None)

    def _grouped_paths(
        self,
        normalized_paths: tuple[Path, ...],
        sidecar_links: dict[Path, Path],
        source_intents: dict[str, dict[str, str]],
        source_ids_by_path: dict[Path, str],
        workflow_group_matches: dict[str, WorkflowGroupingMatch],
    ) -> dict[str, list[Path]]:
        groups: dict[str, list[Path]] = {}
        for path, (_, group_label, _, _) in self._group_assignments(
            normalized_paths,
            sidecar_links,
            source_intents,
            source_ids_by_path,
            workflow_group_matches,
        ).items():
            groups.setdefault(group_label, []).append(path)
        return groups

    @staticmethod
    def _canonical_source_for_group(
        group_key: str,
        sources: list[SessionAssemblySource],
    ) -> SessionAssemblySource | None:
        if group_key.startswith("workflow:"):
            return next(
                (
                    source
                    for source in sources
                    if source.ingest_kind == "supported" and source.role == "primary"
                ),
                next((source for source in sources if source.ingest_kind == "supported"), None),
            )
        if group_key.startswith("supported-anchor:"):
            return next((source for source in sources if source.ingest_kind == "supported"), None)
        return None

    @staticmethod
    def _group_kind_for_key(group_key: str, sources: list[SessionAssemblySource]) -> str:
        if group_key.startswith("manual:"):
            return "manual"
        if group_key.startswith("workflow:"):
            return "workflow_bundle"
        if group_key.startswith("sidecar-bundle:"):
            return "sidecar_bundle"
        if group_key.startswith("supported-anchor:"):
            return "supported_anchor"
        if group_key.startswith("descriptor-parent:"):
            return "descriptor_parent"
        if len(sources) == 1 and sources[0].location.is_dir():
            return "directory"
        return "folder"

    @staticmethod
    def _group_reason_for(
        *,
        group_key: str,
        sources: list[SessionAssemblySource],
        group_kind: str,
        group_pathways: set[ConversionPathway],
        workflow_display_name: str | None = None,
    ) -> str:
        if group_key.startswith("manual:"):
            return "Created or corrected manually in the direct-ingest workspace."
        if group_key.startswith("workflow:") and workflow_display_name:
            supported_count = sum(1 for source in sources if source.ingest_kind == "supported")
            if len(sources) > supported_count:
                return (
                    f"Grouped around supported sources matched as the '{workflow_display_name}' combined NeuroConv "
                    "workflow, with nearby supplemental or custom inputs attached for review."
                )
            return (
                f"Grouped matched supported sources as the '{workflow_display_name}' combined NeuroConv workflow."
            )
        if group_key.startswith("sidecar-bundle:"):
            return "Grouped by same-stem metadata sidecar detection."
        supported_sources = [source for source in sources if source.ingest_kind == "supported"]
        if group_key.startswith("supported-anchor:") and supported_sources:
            anchor_label = supported_sources[0].selection_label
            entry_role_label = supported_sources[0].entry_role_label or "dataset entry path"
            bundle_count = supported_sources[0].structured_bundle_member_count
            bundle_text = (
                f" with {bundle_count} resolved bundle member{'s' if bundle_count != 1 else ''}"
                if bundle_count
                else ""
            )
            if len(sources) > 1:
                return (
                    f"Grouped around the selected {anchor_label} {entry_role_label}{bundle_text} with nearby custom or supplemental inputs."
                )
            return f"Selected {anchor_label} {entry_role_label} treated as one structured source bundle{bundle_text}."
        if group_key.startswith("descriptor-parent:"):
            return "Grouped under a recognized session-descriptor parent directory."
        if len(group_pathways) > 1:
            return "Grouped by shared location, but contains mixed supported/custom-looking inputs."
        if len(sources) == 1 and group_kind == "directory":
            return "Single selected directory treated as one dataset bundle."
        if len(sources) > 1:
            return "Grouped automatically from the same selected folder."
        return "Single selected file treated as its own dataset bundle."

    def _build_workflow_candidate_source(
        self,
        *,
        path: Path,
        route_name: str | None,
        source_id: str,
        role: str,
    ) -> SourceReference:
        source_reference = self._build_matching_source_reference(
            source_id=source_id,
            path=path,
            route_name=route_name,
        )
        matches = self._matching_adapters_for_route(source_reference, route_name)
        adapter_hint = matches[0].adapter_id if len(matches) == 1 else source_reference.adapter_hint
        return SourceReference(
            source_id=source_reference.source_id,
            location=source_reference.location,
            source_type=source_reference.source_type,
            label=source_reference.label,
            role=role,
            adapter_hint=adapter_hint,
        )

    @staticmethod
    def _workflow_canonical_source(
        sources,
    ) -> SourceReference | None:
        source_items = tuple(sources)
        return next(
            (source for source in source_items if source.role == "primary"),
            source_items[0] if source_items else None,
        )

    def _detect_sidecar_links(self, normalized_paths: tuple[Path, ...]) -> dict[Path, Path]:
        primary_candidates = {
            (path.parent.resolve(), path.stem.lower()): path.resolve()
            for path in normalized_paths
            if path.is_file() and path.suffix.lower() not in self._METADATA_SIDECAR_SUFFIXES
        }
        sidecar_links: dict[Path, Path] = {}
        for path in normalized_paths:
            if not path.is_file():
                continue
            if path.suffix.lower() not in self._METADATA_SIDECAR_SUFFIXES:
                continue
            anchor = primary_candidates.get((path.parent.resolve(), path.stem.lower()))
            if anchor is None:
                continue
            sidecar_links[path.resolve()] = anchor
        return sidecar_links

    @classmethod
    def _filter_matches_for_route(
        cls,
        route_name: str | None,
        matches: tuple[SourceAdapter, ...],
    ) -> tuple[SourceAdapter, ...]:
        if route_name is None:
            return matches
        allowed_adapter_ids = cls._ROUTE_ADAPTER_IDS.get(route_name)
        if not allowed_adapter_ids:
            return matches
        return tuple(adapter for adapter in matches if adapter.adapter_id in allowed_adapter_ids)

    def _is_supported_custom_path(self, path: Path) -> bool:
        if path.is_dir():
            return True
        source_reference = SourceReference(
            source_id="custom-selection",
            location=path,
            source_type=SourceType.FILE,
            label=path.name,
        )
        if self._registry.matching_adapters(source_reference):
            return True
        suffixes = tuple(suffix.lower() for suffix in path.suffixes)
        if not suffixes:
            return False
        if suffixes[-1] in self._CUSTOM_ALLOWED_FILE_SUFFIXES:
            return True
        if len(suffixes) >= 2 and "".join(suffixes[-2:]) in {".raw.h5"}:
            return True
        return False

    @staticmethod
    def _slugify(value: str) -> str:
        collapsed = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return collapsed

    @classmethod
    def _normalize_source_role(cls, value: str | None) -> str:
        normalized = str(value or "").strip().lower() or "primary"
        if normalized not in cls._VALID_SOURCE_ROLES:
            return "primary"
        return normalized

    @staticmethod
    def _default_role_for_index(index: int, is_sidecar: bool = False) -> str:
        if is_sidecar:
            return "metadata"
        if index == 1:
            return "primary"
        return "supplemental"

    @staticmethod
    def _suggest_source_pathway(matches) -> ConversionPathway:
        if not matches:
            return ConversionPathway.CUSTOM

        supported = any(
            ConversionPathway.SUPPORTED in adapter.capabilities.supported_pathways for adapter in matches
        )
        custom_or_hybrid = any(
            pathway in adapter.capabilities.supported_pathways
            for adapter in matches
            for pathway in (ConversionPathway.CUSTOM, ConversionPathway.HYBRID)
        )
        if supported and custom_or_hybrid:
            return ConversionPathway.HYBRID
        if supported:
            return ConversionPathway.SUPPORTED
        return ConversionPathway.CUSTOM

    @staticmethod
    def _suggest_session_pathway(sources: tuple[SessionAssemblySource, ...]) -> ConversionPathway:
        if not sources:
            return ConversionPathway.CUSTOM
        has_supported = any(source.suggested_pathway is ConversionPathway.SUPPORTED for source in sources)
        has_custom = any(source.suggested_pathway is ConversionPathway.CUSTOM for source in sources)
        has_hybrid = any(source.suggested_pathway is ConversionPathway.HYBRID for source in sources)
        if has_hybrid or (has_supported and has_custom):
            return ConversionPathway.HYBRID
        if has_supported:
            return ConversionPathway.SUPPORTED
        return ConversionPathway.CUSTOM

    @classmethod
    def _structured_bundle_preview(
        cls,
        path: Path,
        *,
        route_name: str | None,
        entry_path_kind: str | None,
    ) -> StructuredBundlePreview:
        if route_name is None:
            return (
                StructuredBundlePreview(member_count=1, member_labels=(path.name,), member_paths=(path.resolve(),))
                if path.is_file()
                else StructuredBundlePreview()
            )

        if path.is_file():
            member_paths = [path.resolve()]
            if route_name == "thor":
                experiment_xml = path.parent / "Experiment.xml"
                if experiment_xml.is_file():
                    member_paths.append(experiment_xml.resolve())
            if route_name == "scanbox":
                scanbox_sidecar = path.with_suffix(".mat")
                if scanbox_sidecar.is_file():
                    member_paths.append(scanbox_sidecar.resolve())
            return cls._bundle_preview_from_member_paths(member_paths)

        if not path.is_dir():
            return StructuredBundlePreview()

        try:
            if route_name == "session_manifest":
                members = [(path / marker).resolve() for marker in ("session_manifest.json",) if (path / marker).is_file()]
                return cls._bundle_preview_from_member_paths(members)
            if route_name == "miniscope":
                members = cls._directory_member_paths(
                    path,
                    suffixes=(".avi",),
                    explicit_names=("metaData.json",),
                )
                return cls._bundle_preview_from_member_paths(members)
            if route_name == "micromanager":
                members = cls._directory_member_paths(
                    path,
                    suffixes=(".ome.tif", ".ome.tiff", ".tif", ".tiff"),
                    contains_tokens=("displaysettings",),
                )
                return cls._bundle_preview_from_member_paths(members)
            if route_name == "brukertiff":
                members = cls._directory_member_paths(
                    path,
                    suffixes=(".tif", ".tiff", ".xml"),
                )
                return cls._bundle_preview_from_member_paths(members)
            if route_name in {"audio", "image", "videos", "scanimage", "scanimage_legacy", "tiff"}:
                profile = cls._ROUTE_ENTRY_PROFILES.get(route_name)
                members = cls._directory_member_paths(path, suffixes=profile.file_suffixes if profile is not None else ())
                return cls._bundle_preview_from_member_paths(members)
            if route_name in {"tdt", "tdt_fiber_photometry"}:
                members = cls._directory_member_paths(path, suffixes=(".tbk", ".tdx", ".tev", ".tsq"))
                return cls._bundle_preview_from_member_paths(members)

            members = cls._directory_member_paths(path)
            if members:
                return cls._bundle_preview_from_member_paths(members)
        except OSError:
            return StructuredBundlePreview()

        if entry_path_kind == "directory":
            return StructuredBundlePreview()
        return StructuredBundlePreview(member_count=1, member_labels=(path.name,), member_paths=(path.resolve(),))

    @classmethod
    def _bundle_preview_from_labels(cls, labels: list[str] | tuple[str, ...]) -> StructuredBundlePreview:
        ordered = tuple(
            label
            for label in sorted(dict.fromkeys(str(label) for label in labels if str(label).strip()), key=str.lower)
        )
        if not ordered:
            return StructuredBundlePreview()
        return StructuredBundlePreview(
            member_count=len(ordered),
            member_labels=ordered[: cls._BUNDLE_PREVIEW_LIMIT],
        )

    @classmethod
    def _bundle_preview_from_member_paths(
        cls,
        member_paths: list[Path] | tuple[Path, ...],
    ) -> StructuredBundlePreview:
        ordered_paths = tuple(
            sorted(
                dict.fromkeys(path.resolve() for path in member_paths if path.exists()),
                key=lambda item: item.as_posix().lower(),
            )
        )
        if not ordered_paths:
            return StructuredBundlePreview()
        ordered_labels = tuple(path.name for path in ordered_paths)
        return StructuredBundlePreview(
            member_count=len(ordered_paths),
            member_labels=ordered_labels[: cls._BUNDLE_PREVIEW_LIMIT],
            member_paths=ordered_paths,
        )

    @classmethod
    def _directory_member_names(
        cls,
        path: Path,
        *,
        suffixes: tuple[str, ...] = (),
        explicit_names: tuple[str, ...] = (),
        contains_tokens: tuple[str, ...] = (),
    ) -> list[str]:
        lowered_explicit = {name.lower() for name in explicit_names}
        lowered_tokens = tuple(token.lower() for token in contains_tokens)
        normalized_suffixes = tuple(suffix.lower() for suffix in suffixes)
        members: list[str] = []
        for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
            if child.is_dir():
                if not normalized_suffixes and not lowered_explicit and not lowered_tokens:
                    members.append(child.name + "/")
                continue
            lowered_name = child.name.lower()
            if lowered_name in lowered_explicit:
                members.append(child.name)
                continue
            if lowered_tokens and any(token in lowered_name for token in lowered_tokens):
                members.append(child.name)
                continue
            if normalized_suffixes and cls._path_has_supported_suffix(child, normalized_suffixes):
                members.append(child.name)
                continue
            if not normalized_suffixes and not lowered_explicit and not lowered_tokens:
                members.append(child.name)
        return members

    @classmethod
    def _directory_member_paths(
        cls,
        path: Path,
        *,
        suffixes: tuple[str, ...] = (),
        explicit_names: tuple[str, ...] = (),
        contains_tokens: tuple[str, ...] = (),
    ) -> list[Path]:
        lowered_explicit = {name.lower() for name in explicit_names}
        lowered_tokens = tuple(token.lower() for token in contains_tokens)
        normalized_suffixes = tuple(suffix.lower() for suffix in suffixes)
        members: list[Path] = []
        for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
            if child.is_dir():
                if not normalized_suffixes and not lowered_explicit and not lowered_tokens:
                    members.append(child.resolve())
                continue
            lowered_name = child.name.lower()
            if lowered_name in lowered_explicit:
                members.append(child.resolve())
                continue
            if lowered_tokens and any(token in lowered_name for token in lowered_tokens):
                members.append(child.resolve())
                continue
            if normalized_suffixes and cls._path_has_supported_suffix(child, normalized_suffixes):
                members.append(child.resolve())
                continue
            if not normalized_suffixes and not lowered_explicit and not lowered_tokens:
                members.append(child.resolve())
        return members
