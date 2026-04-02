"""Backend service for assembling draft conversion sessions from real inputs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import logging

from nwbforge.adapters import AdapterRegistry
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
    group_key: str
    group_label: str
    location: Path
    source_type: SourceType
    label: str
    matching_adapter_ids: tuple[str, ...]
    suggested_adapter_id: str | None
    suggested_pathway: ConversionPathway
    role: str = "primary"
    needs_review: bool = False


@dataclass(frozen=True, slots=True)
class SessionAssemblyDraft:
    """A suggested conversion-session draft built from selected real inputs."""

    session_id: str
    title: str | None
    pathway: ConversionPathway
    sources: tuple[SessionAssemblySource, ...]
    issues: tuple[SessionAssemblyIssue, ...]
    metadata_overrides: dict[str, str]

    @property
    def can_create_session(self) -> bool:
        return bool(self.sources) and not any(issue.severity is IssueSeverity.ERROR for issue in self.issues)


@dataclass(frozen=True, slots=True)
class SessionAssemblyWorkspace:
    """Persistable in-progress state for the direct-ingest session builder."""

    selected_paths: tuple[Path, ...]
    session_id: str = ""
    title: str = ""
    source_roles: dict[str, str] | None = None
    metadata_overrides: dict[str, str] | None = None


class JsonSessionAssemblyWorkspaceStore:
    """Persist in-progress session assembly state for desktop reopen flows."""

    def __init__(self, workspace_path: Path) -> None:
        self._workspace_path = workspace_path

    def save(self, workspace: SessionAssemblyWorkspace) -> None:
        payload = {
            "selected_paths": [str(path) for path in workspace.selected_paths],
            "session_id": workspace.session_id,
            "title": workspace.title,
            "source_roles": dict(workspace.source_roles or {}),
            "metadata_overrides": dict(workspace.metadata_overrides or {}),
        }
        self._workspace_path.parent.mkdir(parents=True, exist_ok=True)
        self._workspace_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def load(self) -> SessionAssemblyWorkspace | None:
        if not self._workspace_path.exists():
            return None
        payload = json.loads(self._workspace_path.read_text(encoding="utf-8"))
        return SessionAssemblyWorkspace(
            selected_paths=tuple(Path(path) for path in payload.get("selected_paths", ())),
            session_id=str(payload.get("session_id", "")),
            title=str(payload.get("title", "")),
            source_roles={str(key): str(value) for key, value in dict(payload.get("source_roles", {})).items()},
            metadata_overrides={
                str(key): str(value) for key, value in dict(payload.get("metadata_overrides", {})).items()
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

    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry

    def assemble_draft(
        self,
        selected_paths: tuple[Path, ...],
        *,
        session_id: str | None = None,
        title: str | None = None,
        source_roles: dict[str, str] | None = None,
        metadata_overrides: dict[str, str] | None = None,
    ) -> SessionAssemblyDraft:
        """Build a suggested session draft from one or more selected files or folders."""

        normalized_paths = self._normalize_paths(selected_paths)
        grouped_paths = self._grouped_paths(normalized_paths)
        log_event(
            self._logger,
            logging.INFO,
            "Assembling direct-ingest session draft.",
            selected_path_count=len(normalized_paths),
            group_count=len(grouped_paths),
            requested_session_id=session_id or "",
        )
        draft_sources: list[SessionAssemblySource] = []
        issues: list[SessionAssemblyIssue] = []
        normalized_source_roles = {
            str(key): self._normalize_source_role(value)
            for key, value in (source_roles or {}).items()
        }
        normalized_metadata_overrides = {
            str(key): str(value).strip()
            for key, value in (metadata_overrides or {}).items()
            if str(value).strip()
        }

        for index, path in enumerate(normalized_paths, start=1):
            group_key, group_label = self._group_for_path(path)
            source_id = self._build_source_id(path, draft_sources)
            source_reference = SourceReference(
                source_id=source_id,
                location=path,
                source_type=SourceType.DIRECTORY if path.is_dir() else SourceType.FILE,
                label=path.name,
            )
            matches = self._registry.matching_adapters(source_reference)
            matching_ids = tuple(adapter.adapter_id for adapter in matches)
            suggested_pathway = self._suggest_source_pathway(matches)
            suggested_adapter_id = matching_ids[0] if len(matching_ids) == 1 else None
            needs_review = len(matching_ids) != 1
            role = normalized_source_roles.get(source_id, self._default_role_for_index(index))

            if not matching_ids:
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

            draft_sources.append(
                SessionAssemblySource(
                    source_id=source_reference.source_id,
                    group_key=group_key,
                    group_label=group_label,
                    location=path,
                    source_type=source_reference.source_type,
                    label=source_reference.label,
                    matching_adapter_ids=matching_ids,
                    suggested_adapter_id=suggested_adapter_id,
                    suggested_pathway=suggested_pathway,
                    role=role,
                    needs_review=needs_review,
                )
            )

        for group_label, paths in grouped_paths.items():
            if len(paths) < 2:
                continue
            issues.append(
                SessionAssemblyIssue(
                    code="session-assembly-auto-grouped-inputs",
                    message=(
                        f"Auto-grouped {len(paths)} selected inputs under '{group_label}'. "
                        "Confirm they belong to the same conversion session."
                    ),
                    severity=IssueSeverity.INFO,
                    location=paths[0].parent if paths[0].is_file() else paths[0],
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
            issues=tuple(issues),
            metadata_overrides=normalized_metadata_overrides,
        )

    def create_session(self, draft: SessionAssemblyDraft) -> ConversionSession:
        """Create a real conversion session from an assembled draft."""

        if not draft.can_create_session:
            raise ValueError("Session draft is not ready to create.")

        sources = tuple(
            SourceReference(
                source_id=source.source_id,
                location=source.location,
                source_type=source.source_type,
                label=source.label,
                role=source.role,
                adapter_hint=source.suggested_adapter_id,
                metadata={
                    "session_assembly.group_key": source.group_key,
                    "session_assembly.group_label": source.group_label,
                },
            )
            for source in draft.sources
        )
        session = ConversionSession(
            session_id=draft.session_id,
            pathway=draft.pathway,
            sources=sources,
            title=draft.title,
            metadata_overrides=dict(draft.metadata_overrides),
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

    def _build_source_id(self, path: Path, existing_sources: list[SessionAssemblySource]) -> str:
        base = self._slugify(path.stem if path.is_file() else path.name) or "source"
        existing_ids = {source.source_id for source in existing_sources}
        candidate = base
        counter = 2
        while candidate in existing_ids:
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

    def _group_for_path(self, path: Path) -> tuple[str, str]:
        if path.is_dir():
            return str(path), path.name
        if path.name.lower() in self._DESKTOP_SESSION_FILENAMES:
            parent = path.parent.resolve()
            return str(parent), parent.name or path.stem
        parent = path.parent.resolve()
        return str(parent), parent.name or path.stem

    def _grouped_paths(self, normalized_paths: tuple[Path, ...]) -> dict[str, list[Path]]:
        groups: dict[str, list[Path]] = {}
        for path in normalized_paths:
            _, group_label = self._group_for_path(path)
            groups.setdefault(group_label, []).append(path)
        return groups

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
    def _default_role_for_index(index: int) -> str:
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
