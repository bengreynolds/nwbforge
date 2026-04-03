"""Toolkit-agnostic direct-ingest session-assembly screen model."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from threading import Lock
import logging

from nwbforge.app.packages.catalog import ROUTE_PACKAGE_CATALOG, route_dependencies_available
from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.services import (
    JsonSessionAssemblyWorkspaceStore,
    JsonSessionAssemblyProjectStore,
    SessionAssemblyService,
    SessionAssemblyWorkspace,
)
from nwbforge.ui.errors import DefaultUiErrorPresenter, UiErrorPresenter
from nwbforge.ui.models import (
    SessionAssemblyGroupItem,
    SessionAssemblyIssueItem,
    SessionAssemblySourceItem,
    SessionAssemblyState,
    SessionAssemblyStateListener,
    SessionAssemblySourceTypeOption,
)


class SessionAssemblyScreenModel:
    """Drive direct file/folder ingestion and draft session assembly for the desktop UI."""

    _logger = get_logger(__name__)

    def __init__(
        self,
        assembly_service: SessionAssemblyService,
        *,
        error_presenter: UiErrorPresenter | None = None,
        workspace_store: JsonSessionAssemblyWorkspaceStore | None = None,
        project_store: JsonSessionAssemblyProjectStore | None = None,
    ) -> None:
        self._assembly_service = assembly_service
        self._source_type_options = self._build_source_type_options()
        self._state = SessionAssemblyState(source_type_options=self._source_type_options)
        self._listeners: list[SessionAssemblyStateListener] = []
        self._lock = Lock()
        self._error_presenter = error_presenter or DefaultUiErrorPresenter()
        self._workspace_store = workspace_store
        self._project_store = project_store or JsonSessionAssemblyProjectStore()
        self._restore_workspace()

    @property
    def state(self) -> SessionAssemblyState:
        return self._state

    def subscribe(self, listener: SessionAssemblyStateListener, *, emit_initial: bool = True) -> None:
        with self._lock:
            self._listeners.append(listener)
            state = self._state
        if emit_initial:
            listener(state)

    def reset(self) -> SessionAssemblyState:
        log_event(self._logger, logging.INFO, "Reset direct-ingest session assembly state.")
        state = self._set_state(SessionAssemblyState(source_type_options=self._source_type_options))
        self._clear_workspace()
        return state

    def load_project(self, project_path: Path) -> SessionAssemblyState:
        document = self._project_store.load(project_path)
        log_event(
            self._logger,
            logging.INFO,
            "Loaded direct-ingest project.",
            project_path=str(document.project_path),
            selected_path_count=len(document.workspace.selected_paths),
        )
        state = self._refresh(
            selected_paths=document.workspace.selected_paths,
            source_intents={
                str(path_text): dict(intent)
                for path_text, intent in (document.workspace.source_intents or {}).items()
            },
            session_id=document.workspace.session_id,
            title=document.workspace.title,
            source_roles=dict(document.workspace.source_roles or {}),
            group_overrides=dict(document.workspace.group_overrides or {}),
            confirmed_group_keys=tuple(document.workspace.confirmed_group_keys or ()),
            metadata_overrides=dict(document.workspace.metadata_overrides or {}),
            source_metadata_overrides={
                str(source_id): dict(overrides)
                for source_id, overrides in (document.workspace.source_metadata_overrides or {}).items()
            },
        )
        state = self._set_state(
            replace(
                state,
                project_path=document.project_path,
                has_unsaved_changes=False,
            )
        )
        self._persist_workspace(state)
        return state

    def save_project(self, project_path: Path | None = None) -> SessionAssemblyState:
        if project_path is None:
            project_path = self._state.project_path
        if project_path is None:
            raise ValueError("Choose a project path before saving.")

        workspace = self._workspace_from_state(self._state)
        document = self._project_store.save(project_path, workspace)
        log_event(
            self._logger,
            logging.INFO,
            "Saved direct-ingest project.",
            project_path=str(document.project_path),
            selected_path_count=len(workspace.selected_paths),
        )
        state = replace(
            self._state,
            project_path=document.project_path,
            has_unsaved_changes=False,
            error_message=None,
            user_error=None,
        )
        state = self._set_state(state)
        self._persist_workspace(state)
        return state

    def add_paths(self, paths: tuple[Path, ...]) -> SessionAssemblyState:
        return self.add_custom_paths(paths)

    def add_custom_paths(self, paths: tuple[Path, ...]) -> SessionAssemblyState:
        accepted_paths, rejected_messages = self._assembly_service.filter_custom_selected_paths(paths)
        log_event(
            self._logger,
            logging.INFO,
            "Adding custom paths to direct-ingest workspace.",
            added_path_count=len(accepted_paths),
            rejected_path_count=len(rejected_messages),
        )
        if not accepted_paths and rejected_messages:
            return self._set_state(
                replace(
                    self._state,
                    error_message=" ".join(rejected_messages),
                    user_error=None,
                )
            )
        resolved_paths = tuple(path.resolve() for path in accepted_paths)
        combined = self._state.selected_paths + resolved_paths
        next_source_intents = dict(self._state.source_intents)
        for path in resolved_paths:
            next_source_intents[str(path)] = {"ingest_kind": "custom"}
        state = self._refresh(selected_paths=combined, source_intents=next_source_intents)
        if rejected_messages:
            return self._set_state(
                replace(
                    state,
                    error_message=" ".join(rejected_messages),
                    user_error=None,
                )
            )
        return state

    def add_supported_paths(
        self,
        paths: tuple[Path, ...],
        *,
        route_name: str,
        route_display_name: str,
    ) -> SessionAssemblyState:
        accepted_paths, accepted_intents, rejected_messages = self._assembly_service.validate_supported_selected_paths(
            paths,
            route_name=route_name,
            route_display_name=route_display_name,
        )
        log_event(
            self._logger,
            logging.INFO,
            "Adding NeuroConv-supported paths to direct-ingest workspace.",
            added_path_count=len(accepted_paths),
            rejected_path_count=len(rejected_messages),
            route_name=route_name,
        )
        if not accepted_paths and rejected_messages:
            return self._set_state(
                replace(
                    self._state,
                    error_message=" ".join(rejected_messages),
                    user_error=None,
                )
            )
        resolved_paths = tuple(path.resolve() for path in accepted_paths)
        combined = self._state.selected_paths + resolved_paths
        next_source_intents = dict(self._state.source_intents)
        for path_text, intent in accepted_intents.items():
            next_source_intents[str(path_text)] = dict(intent)
        state = self._refresh(selected_paths=combined, source_intents=next_source_intents)
        if rejected_messages:
            return self._set_state(
                replace(
                    state,
                    error_message=" ".join(rejected_messages),
                    user_error=None,
                )
            )
        return state

    def remove_paths(self, paths: tuple[Path, ...]) -> SessionAssemblyState:
        log_event(
            self._logger,
            logging.INFO,
            "Removing paths from direct-ingest workspace.",
            removed_path_count=len(paths),
        )
        removed = {path.resolve() for path in paths}
        remaining = tuple(path for path in self._state.selected_paths if path.resolve() not in removed)
        next_source_intents = {
            str(path_text): dict(intent)
            for path_text, intent in self._state.source_intents.items()
            if Path(path_text).resolve() not in removed
        }
        return self._refresh(selected_paths=remaining, source_intents=next_source_intents)

    def set_session_id(self, session_id: str) -> SessionAssemblyState:
        return self._refresh(session_id=session_id)

    def set_title(self, title: str) -> SessionAssemblyState:
        return self._refresh(title=title)

    def set_metadata_override(self, key: str, value: str) -> SessionAssemblyState:
        next_overrides = dict(self._state.metadata_overrides)
        if value.strip():
            next_overrides[key] = value.strip()
        else:
            next_overrides.pop(key, None)
        return self._refresh(metadata_overrides=next_overrides)

    def set_source_metadata_override(self, source_id: str, key: str, value: str) -> SessionAssemblyState:
        next_overrides = {
            item.source_id: dict(item.metadata_overrides)
            for item in self._state.sources
            if item.metadata_overrides
        }
        source_overrides = dict(next_overrides.get(source_id, {}))
        if value.strip():
            source_overrides[key] = value.strip()
        else:
            source_overrides.pop(key, None)
        if source_overrides:
            next_overrides[source_id] = source_overrides
        else:
            next_overrides.pop(source_id, None)
        return self._refresh(source_metadata_overrides=next_overrides)

    def set_source_group_label(self, source_id: str, group_label: str) -> SessionAssemblyState:
        normalized_label = group_label.strip()
        log_event(
            self._logger,
            logging.INFO,
            "Updated source grouping in direct-ingest workspace.",
            source_id=source_id,
            group_label=normalized_label,
        )
        next_group_overrides = {source.source_id: source.group_label for source in self._state.sources}
        if normalized_label:
            next_group_overrides[source_id] = normalized_label
        else:
            next_group_overrides.pop(source_id, None)
        return self._refresh(group_overrides=next_group_overrides)

    def set_group_label_for_sources(
        self,
        source_ids: tuple[str, ...],
        group_label: str,
    ) -> SessionAssemblyState:
        normalized_label = group_label.strip()
        if not source_ids:
            return self._state
        log_event(
            self._logger,
            logging.INFO,
            "Updated grouping for multiple direct-ingest sources.",
            source_count=len(source_ids),
            group_label=normalized_label,
        )
        next_group_overrides = {source.source_id: source.group_label for source in self._state.sources}
        for source_id in source_ids:
            if normalized_label:
                next_group_overrides[source_id] = normalized_label
            else:
                next_group_overrides.pop(source_id, None)
        return self._refresh(group_overrides=next_group_overrides)

    def split_sources_into_individual_groups(self, source_ids: tuple[str, ...]) -> SessionAssemblyState:
        if not source_ids:
            return self._state
        log_event(
            self._logger,
            logging.INFO,
            "Split selected sources into individual direct-ingest groups.",
            source_count=len(source_ids),
        )
        next_group_overrides = {source.source_id: source.group_label for source in self._state.sources}
        used_labels = {source.group_label for source in self._state.sources if source.source_id not in source_ids}
        for source in self._state.sources:
            if source.source_id not in source_ids:
                continue
            base_label = source.location.stem if source.location.is_file() else source.location.name
            next_label = base_label or source.label or source.source_id
            counter = 2
            while next_label in used_labels:
                next_label = f"{base_label or source.label or source.source_id} {counter}"
                counter += 1
            used_labels.add(next_label)
            next_group_overrides[source.source_id] = next_label
        return self._refresh(group_overrides=next_group_overrides)

    def split_group(self, group_key: str) -> SessionAssemblyState:
        source_ids = tuple(
            source.source_id for source in self._state.sources if source.group_key == group_key
        )
        return self.split_sources_into_individual_groups(source_ids)

    def rename_group(self, group_key: str, group_label: str) -> SessionAssemblyState:
        source_ids = tuple(
            source.source_id for source in self._state.sources if source.group_key == group_key
        )
        return self.set_group_label_for_sources(source_ids, group_label)

    def confirm_group(self, group_key: str) -> SessionAssemblyState:
        next_confirmed = {
            group.group_key
            for group in self._state.groups
            if group.is_confirmed or group.group_key == group_key
        }
        log_event(
            self._logger,
            logging.INFO,
            "Confirmed direct-ingest dataset group.",
            group_key=group_key,
        )
        return self._refresh(confirmed_group_keys=tuple(sorted(next_confirmed)))

    def unconfirm_group(self, group_key: str) -> SessionAssemblyState:
        next_confirmed = tuple(
            group.group_key
            for group in self._state.groups
            if group.is_confirmed and group.group_key != group_key
        )
        log_event(
            self._logger,
            logging.INFO,
            "Unconfirmed direct-ingest dataset group.",
            group_key=group_key,
        )
        return self._refresh(confirmed_group_keys=next_confirmed)

    def confirm_all_groups(self) -> SessionAssemblyState:
        next_confirmed = tuple(group.group_key for group in self._state.groups)
        log_event(
            self._logger,
            logging.INFO,
            "Confirmed all direct-ingest dataset groups.",
            group_count=len(next_confirmed),
        )
        return self._refresh(confirmed_group_keys=next_confirmed)

    def create_session(self):
        if self._state.draft is None:
            raise ValueError("Session assembly requires at least one selected input.")
        log_event(
            self._logger,
            logging.INFO,
            "Creating conversion session from direct-ingest workspace.",
            session_id=self._state.draft.session_id,
            pathway=self._state.draft.pathway.value,
            source_count=len(self._state.draft.sources),
            issue_count=len(self._state.draft.issues),
        )
        try:
            session = self._assembly_service.create_session(self._state.draft)
            self._clear_workspace()
            self._set_state(SessionAssemblyState(source_type_options=self._source_type_options))
            return session
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            self._set_state(
                replace(
                    self._state,
                    error_message=user_error.message,
                    user_error=user_error,
                )
            )
            raise

    def _refresh(
        self,
        *,
        selected_paths: tuple[Path, ...] | None = None,
        source_intents: dict[str, dict[str, str]] | None = None,
        session_id: str | None = None,
        title: str | None = None,
        source_roles: dict[str, str] | None = None,
        group_overrides: dict[str, str] | None = None,
        confirmed_group_keys: tuple[str, ...] | None = None,
        metadata_overrides: dict[str, str] | None = None,
        source_metadata_overrides: dict[str, dict[str, str]] | None = None,
    ) -> SessionAssemblyState:
        next_paths = selected_paths if selected_paths is not None else self._state.selected_paths
        next_source_intents = source_intents if source_intents is not None else self._state.source_intents
        next_session_id = session_id if session_id is not None else self._state.session_id
        next_title = title if title is not None else self._state.title
        current_roles = (
            {source.source_id: source.role for source in self._state.sources}
            if self._state.sources
            else {}
        )
        current_group_overrides = (
            {
                source.source_id: source.group_label
                for source in self._state.sources
                if source.group_key.startswith("manual:")
            }
            if self._state.sources
            else {}
        )
        next_source_roles = source_roles if source_roles is not None else current_roles
        next_group_overrides = group_overrides if group_overrides is not None else current_group_overrides
        current_confirmed_group_keys = tuple(
            group.group_key
            for group in self._state.groups
            if group.is_confirmed
        )
        next_confirmed_group_keys = (
            confirmed_group_keys if confirmed_group_keys is not None else current_confirmed_group_keys
        )
        next_metadata_overrides = (
            metadata_overrides if metadata_overrides is not None else self._state.metadata_overrides
        )
        current_source_metadata_overrides = {
            item.source_id: dict(item.metadata_overrides)
            for item in self._state.sources
            if item.metadata_overrides
        }
        next_source_metadata_overrides = (
            source_metadata_overrides
            if source_metadata_overrides is not None
            else current_source_metadata_overrides
        )
        try:
            draft = self._assembly_service.assemble_draft(
                next_paths,
                source_intents=next_source_intents,
                session_id=next_session_id,
                title=next_title,
                source_roles=next_source_roles,
                group_overrides=next_group_overrides,
                confirmed_group_keys=next_confirmed_group_keys,
                metadata_overrides=next_metadata_overrides,
                source_metadata_overrides=next_source_metadata_overrides,
            )
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            return self._set_state(
                replace(
                    self._state,
                    selected_paths=tuple(path.resolve() for path in next_paths),
                    source_intents={
                        str(path_text): dict(intent)
                        for path_text, intent in next_source_intents.items()
                    },
                    error_message=user_error.message,
                    user_error=user_error,
                )
            )

        resolved_paths = tuple(path.resolve() for path in next_paths)
        state = self._set_state(
            SessionAssemblyState(
                selected_paths=resolved_paths,
                source_type_options=self._source_type_options,
                source_intents={
                    str(path_text): dict(intent)
                    for path_text, intent in next_source_intents.items()
                },
                session_id=draft.session_id,
                title=draft.title or "",
                suggested_pathway=draft.pathway.value,
                metadata_overrides=dict(draft.metadata_overrides),
                source_metadata_overrides={
                    str(source_id): dict(overrides)
                    for source_id, overrides in draft.source_metadata_overrides.items()
                },
                groups=tuple(
                    SessionAssemblyGroupItem(
                        group_key=group.group_key,
                        group_label=group.group_label,
                        suggested_pathway=group.suggested_pathway.value,
                        group_kind=group.group_kind,
                        anchor_path=group.anchor_path,
                        canonical_source_id=group.canonical_source_id,
                        canonical_source_label=group.canonical_source_label,
                        canonical_source_path=group.canonical_source_path,
                        canonical_entry_role_label=group.canonical_entry_role_label,
                        canonical_selection_label=group.canonical_selection_label,
                        grouping_reason=group.grouping_reason,
                        member_labels=group.member_labels,
                        source_ids=group.source_ids,
                        source_count=group.source_count,
                        primary_count=group.primary_count,
                        supplemental_count=group.supplemental_count,
                        metadata_count=group.metadata_count,
                        review_issue_count=group.review_issue_count,
                        requires_confirmation=group.requires_confirmation,
                        needs_review=group.needs_review,
                        is_confirmed=group.is_confirmed,
                    )
                    for group in draft.groups
                ),
                sources=tuple(
                    SessionAssemblySourceItem(
                        source_id=source.source_id,
                        ingest_kind=source.ingest_kind,
                        selection_label=source.selection_label,
                        route_name=source.route_name,
                        group_key=source.group_key,
                        group_label=source.group_label,
                        label=source.label,
                        location=source.location,
                        source_type=source.source_type.value,
                        suggested_pathway=source.suggested_pathway.value,
                        entry_path_kind=source.entry_path_kind,
                        entry_role_label=source.entry_role_label,
                        entry_validation_status=source.entry_validation_status,
                        role=source.role,
                        metadata_overrides=dict(source.metadata_overrides or {}),
                        sidecar_for_source_id=source.sidecar_for_source_id,
                        sidecar_for_label=source.sidecar_for_label,
                        context_source_id=source.context_source_id,
                        context_label=source.context_label,
                        matching_adapter_ids=source.matching_adapter_ids,
                        suggested_adapter_id=source.suggested_adapter_id,
                        needs_review=source.needs_review,
                    )
                    for source in draft.sources
                ),
                issues=tuple(
                    SessionAssemblyIssueItem(
                        code=issue.code,
                        message=issue.message,
                        severity=issue.severity.value,
                        location=issue.location,
                    )
                    for issue in draft.issues
                ),
                draft=draft,
                project_path=self._state.project_path,
                has_unsaved_changes=self._state.project_path is not None or bool(resolved_paths),
                error_message=None,
                user_error=None,
            )
        )
        self._persist_workspace(state)
        return state

    def _set_state(self, new_state: SessionAssemblyState) -> SessionAssemblyState:
        with self._lock:
            self._state = new_state
            listeners = tuple(self._listeners)
            state = self._state
        for listener in listeners:
            listener(state)
        return state

    def set_source_role(self, source_id: str, role: str) -> SessionAssemblyState:
        log_event(
            self._logger,
            logging.INFO,
            "Updated source role in direct-ingest workspace.",
            source_id=source_id,
            role=role,
        )
        next_roles = {source.source_id: source.role for source in self._state.sources}
        next_roles[source_id] = role
        return self._refresh(source_roles=next_roles)

    def _restore_workspace(self) -> None:
        if self._workspace_store is None:
            return
        workspace = self._workspace_store.load()
        if workspace is None:
            return
        log_event(
            self._logger,
            logging.INFO,
            "Restoring persisted direct-ingest workspace.",
            selected_path_count=len(workspace.selected_paths),
        )
        self._refresh(
            selected_paths=workspace.selected_paths,
            source_intents={
                str(path_text): dict(intent)
                for path_text, intent in (workspace.source_intents or {}).items()
            },
            session_id=workspace.session_id,
            title=workspace.title,
            source_roles=dict(workspace.source_roles or {}),
            group_overrides=dict(workspace.group_overrides or {}),
            confirmed_group_keys=tuple(workspace.confirmed_group_keys or ()),
            metadata_overrides=dict(workspace.metadata_overrides or {}),
            source_metadata_overrides={
                str(source_id): dict(overrides)
                for source_id, overrides in (workspace.source_metadata_overrides or {}).items()
            },
        )
        self._set_state(
            replace(
                self._state,
                project_path=workspace.project_path,
                has_unsaved_changes=workspace.has_unsaved_changes,
                source_type_options=self._source_type_options,
            )
        )

    def _persist_workspace(self, state: SessionAssemblyState) -> None:
        if self._workspace_store is None:
            return
        if not state.selected_paths and not state.metadata_overrides:
            self._workspace_store.clear()
            return
        log_event(
            self._logger,
            logging.DEBUG,
            "Persisting direct-ingest workspace.",
            selected_path_count=len(state.selected_paths),
            source_count=len(state.sources),
            override_count=len(state.metadata_overrides),
        )
        self._workspace_store.save(self._workspace_from_state(state))

    def _clear_workspace(self) -> None:
        if self._workspace_store is not None:
            self._workspace_store.clear()

    @staticmethod
    def _workspace_from_state(state: SessionAssemblyState) -> SessionAssemblyWorkspace:
        return SessionAssemblyWorkspace(
            selected_paths=state.selected_paths,
            source_intents={
                str(path_text): dict(intent)
                for path_text, intent in state.source_intents.items()
            },
            project_path=state.project_path,
            has_unsaved_changes=state.has_unsaved_changes,
            session_id=state.session_id,
            title=state.title,
            source_roles={source.source_id: source.role for source in state.sources},
            group_overrides={
                source.source_id: source.group_label
                for source in state.sources
                if source.group_key.startswith("manual:")
            },
            confirmed_group_keys=tuple(
                group.group_key
                for group in state.groups
                if group.is_confirmed
            ),
            metadata_overrides=dict(state.metadata_overrides),
            source_metadata_overrides={
                source.source_id: dict(source.metadata_overrides)
                for source in state.sources
                if source.metadata_overrides
            },
        )

    @staticmethod
    def _build_source_type_options() -> tuple[SessionAssemblySourceTypeOption, ...]:
        options = [
            SessionAssemblySourceTypeOption(
                ingest_kind="custom",
                label="Custom",
                description="Add arbitrary files or folders for later review and organization.",
            )
        ]
        installed_routes = sorted(
            (
                spec
                for spec in ROUTE_PACKAGE_CATALOG
                if spec.implemented_in_code and route_dependencies_available(spec.route_name)
            ),
            key=lambda spec: spec.display_name.lower(),
        )
        options.extend(
            SessionAssemblySourceTypeOption(
                ingest_kind="supported",
                label=spec.display_name,
                route_name=spec.route_name,
                description=(
                    f"{spec.description} Select the package's project file, main file, or root directory "
                    "as the canonical dataset entry."
                ),
            )
            for spec in installed_routes
        )
        return tuple(options)
