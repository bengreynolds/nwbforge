"""Toolkit-agnostic direct-ingest session-assembly screen model."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from threading import Lock
import logging

from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.services import (
    JsonSessionAssemblyWorkspaceStore,
    SessionAssemblyService,
    SessionAssemblyWorkspace,
)
from nwbforge.ui.errors import DefaultUiErrorPresenter, UiErrorPresenter
from nwbforge.ui.models import (
    SessionAssemblyIssueItem,
    SessionAssemblySourceItem,
    SessionAssemblyState,
    SessionAssemblyStateListener,
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
    ) -> None:
        self._assembly_service = assembly_service
        self._state = SessionAssemblyState()
        self._listeners: list[SessionAssemblyStateListener] = []
        self._lock = Lock()
        self._error_presenter = error_presenter or DefaultUiErrorPresenter()
        self._workspace_store = workspace_store
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
        state = self._set_state(SessionAssemblyState())
        self._clear_workspace()
        return state

    def add_paths(self, paths: tuple[Path, ...]) -> SessionAssemblyState:
        log_event(
            self._logger,
            logging.INFO,
            "Adding paths to direct-ingest workspace.",
            added_path_count=len(paths),
        )
        combined = self._state.selected_paths + tuple(path.resolve() for path in paths)
        return self._refresh(selected_paths=combined)

    def remove_paths(self, paths: tuple[Path, ...]) -> SessionAssemblyState:
        log_event(
            self._logger,
            logging.INFO,
            "Removing paths from direct-ingest workspace.",
            removed_path_count=len(paths),
        )
        removed = {path.resolve() for path in paths}
        remaining = tuple(path for path in self._state.selected_paths if path.resolve() not in removed)
        return self._refresh(selected_paths=remaining)

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

    def create_session(self):
        if self._state.draft is None:
            raise ValueError("Session assembly requires at least one selected input.")
        try:
            session = self._assembly_service.create_session(self._state.draft)
            self._clear_workspace()
            self._set_state(SessionAssemblyState())
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
        session_id: str | None = None,
        title: str | None = None,
        source_roles: dict[str, str] | None = None,
        metadata_overrides: dict[str, str] | None = None,
    ) -> SessionAssemblyState:
        next_paths = selected_paths if selected_paths is not None else self._state.selected_paths
        next_session_id = session_id if session_id is not None else self._state.session_id
        next_title = title if title is not None else self._state.title
        current_roles = (
            {source.source_id: source.role for source in self._state.sources}
            if self._state.sources
            else {}
        )
        next_source_roles = source_roles if source_roles is not None else current_roles
        next_metadata_overrides = (
            metadata_overrides if metadata_overrides is not None else self._state.metadata_overrides
        )
        try:
            draft = self._assembly_service.assemble_draft(
                next_paths,
                session_id=next_session_id,
                title=next_title,
                source_roles=next_source_roles,
                metadata_overrides=next_metadata_overrides,
            )
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            return self._set_state(
                replace(
                    self._state,
                    selected_paths=tuple(path.resolve() for path in next_paths),
                    error_message=user_error.message,
                    user_error=user_error,
                )
            )

        resolved_paths = tuple(path.resolve() for path in next_paths)
        state = self._set_state(
            SessionAssemblyState(
                selected_paths=resolved_paths,
                session_id=draft.session_id,
                title=draft.title or "",
                suggested_pathway=draft.pathway.value,
                metadata_overrides=dict(draft.metadata_overrides),
                sources=tuple(
                    SessionAssemblySourceItem(
                        source_id=source.source_id,
                        group_key=source.group_key,
                        group_label=source.group_label,
                        label=source.label,
                        location=source.location,
                        source_type=source.source_type.value,
                        suggested_pathway=source.suggested_pathway.value,
                        role=source.role,
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
            session_id=workspace.session_id,
            title=workspace.title,
            source_roles=dict(workspace.source_roles or {}),
            metadata_overrides=dict(workspace.metadata_overrides or {}),
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
        self._workspace_store.save(
            SessionAssemblyWorkspace(
                selected_paths=state.selected_paths,
                session_id=state.session_id,
                title=state.title,
                source_roles={source.source_id: source.role for source in state.sources},
                metadata_overrides=dict(state.metadata_overrides),
            )
        )

    def _clear_workspace(self) -> None:
        if self._workspace_store is not None:
            self._workspace_store.clear()
