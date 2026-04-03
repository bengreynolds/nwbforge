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
    role: str = "primary"
    metadata_overrides: dict[str, str] | None = None
    sidecar_for_source_id: str | None = None
    sidecar_for_label: str | None = None
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
    _ROUTE_ADAPTER_IDS: dict[str, tuple[str, ...]] = {
        "audio": ("neuroconv_audio",),
        "alphaomega": ("neuroconv_alphaomega",),
        "axon": ("neuroconv_axon",),
        "axona": ("neuroconv_axona",),
        "biocam": ("neuroconv_biocam",),
        "blackrock": ("neuroconv_blackrock", "neuroconv_blackrock_sorting"),
        "brukertiff": ("neuroconv_brukertiff_single_plane", "neuroconv_brukertiff_multi_plane"),
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
    }

    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry

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
        log_event(
            self._logger,
            logging.INFO,
            "Assembling direct-ingest session draft.",
            selected_path_count=len(normalized_paths),
            group_count=len(self._grouped_paths(normalized_paths, sidecar_links)),
            sidecar_link_count=len(sidecar_links),
            requested_session_id=session_id or "",
        )
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
        group_assignments = self._group_assignments(normalized_paths, sidecar_links)

        for index, path in enumerate(normalized_paths, start=1):
            source_id = source_ids_by_path[path.resolve()]
            group_key, group_label = group_assignments[path.resolve()]
            override_group = normalized_group_overrides.get(source_id)
            if override_group:
                group_key = f"manual:{override_group.lower()}"
                group_label = override_group
            source_reference = SourceReference(
                source_id=source_id,
                location=path,
                source_type=SourceType.DIRECTORY if path.is_dir() else SourceType.FILE,
                label=path.name,
            )
            source_intent = normalized_source_intents.get(str(path.resolve()), {})
            ingest_kind = (
                "supported" if source_intent.get("ingest_kind") == "supported" else "custom"
            )
            route_name = source_intent.get("route_name") or None
            route_display_name = source_intent.get("route_display_name") or None
            selection_label = route_display_name or ("Custom" if ingest_kind == "custom" else "NeuroConv")
            matches = self._registry.matching_adapters(source_reference)
            matches = self._filter_matches_for_route(route_name, matches)
            matching_ids = tuple(adapter.adapter_id for adapter in matches)
            suggested_pathway = (
                ConversionPathway.SUPPORTED
                if ingest_kind == "supported" and not matches
                else self._suggest_source_pathway(matches)
            )
            suggested_adapter_id = matching_ids[0] if len(matching_ids) == 1 else None
            needs_review = len(matching_ids) != 1
            sidecar_anchor = sidecar_links.get(path.resolve())
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
                    role=role,
                    metadata_overrides=dict(normalized_source_metadata_overrides.get(source_id, {})),
                    sidecar_for_source_id=source_ids_by_path.get(sidecar_anchor) if sidecar_anchor is not None else None,
                    sidecar_for_label=sidecar_anchor.name if sidecar_anchor is not None else None,
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
            grouping_reason = self._group_reason_for(
                group_key=group_key,
                sources=sources,
                group_kind=group_kind,
                group_pathways=group_pathways,
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

    def _group_assignments(
        self,
        normalized_paths: tuple[Path, ...],
        sidecar_links: dict[Path, Path],
    ) -> dict[Path, tuple[str, str]]:
        descriptor_directories = {
            path.parent.resolve(): path
            for path in normalized_paths
            if path.is_file() and path.name.lower() in self._DESKTOP_SESSION_FILENAMES
        }
        assignments: dict[Path, tuple[str, str]] = {}

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
                )
                assignments[anchor_resolved] = anchor_assignment
            assignments[resolved] = anchor_assignment

        for path in normalized_paths:
            resolved = path.resolve()
            if resolved in assignments:
                continue
            assignments[resolved] = self._base_group_for_path(path, descriptor_directories)
        return assignments

    def _base_group_for_path(
        self,
        path: Path,
        descriptor_directories: dict[Path, Path],
    ) -> tuple[str, str]:
        if path.is_dir():
            resolved = path.resolve()
            return str(resolved), resolved.name or "Session"
        if path.name.lower() in self._DESKTOP_SESSION_FILENAMES:
            parent = path.parent.resolve()
            return str(parent), parent.name or path.stem
        parent = path.parent.resolve()
        if parent in descriptor_directories:
            return (f"descriptor-parent:{parent.as_posix().lower()}", parent.name or path.stem)
        if path.suffix.lower() in self._METADATA_SIDECAR_SUFFIXES:
            return (f"sidecar-stem:{parent.as_posix().lower()}:{path.stem.lower()}", path.stem or parent.name)
        return (str(parent), parent.name or path.stem)

    def _grouped_paths(
        self,
        normalized_paths: tuple[Path, ...],
        sidecar_links: dict[Path, Path],
    ) -> dict[str, list[Path]]:
        groups: dict[str, list[Path]] = {}
        for path, (_, group_label) in self._group_assignments(normalized_paths, sidecar_links).items():
            groups.setdefault(group_label, []).append(path)
        return groups

    @staticmethod
    def _group_kind_for_key(group_key: str, sources: list[SessionAssemblySource]) -> str:
        if group_key.startswith("manual:"):
            return "manual"
        if group_key.startswith("sidecar-bundle:"):
            return "sidecar_bundle"
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
    ) -> str:
        if group_key.startswith("manual:"):
            return "Created or corrected manually in the direct-ingest workspace."
        if group_key.startswith("sidecar-bundle:"):
            return "Grouped by same-stem metadata sidecar detection."
        if group_key.startswith("descriptor-parent:"):
            return "Grouped under a recognized session-descriptor parent directory."
        if len(group_pathways) > 1:
            return "Grouped by shared location, but contains mixed supported/custom-looking inputs."
        if len(sources) == 1 and group_kind == "directory":
            return "Single selected directory treated as one dataset bundle."
        if len(sources) > 1:
            return "Grouped automatically from the same selected folder."
        return "Single selected file treated as its own dataset bundle."

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
