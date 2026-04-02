"""Toolkit-agnostic direct-ingest session-assembly screen model."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from threading import Lock

from nwbforge.app.services import SessionAssemblyService
from nwbforge.ui.errors import DefaultUiErrorPresenter, UiErrorPresenter
from nwbforge.ui.models import (
    SessionAssemblyIssueItem,
    SessionAssemblySourceItem,
    SessionAssemblyState,
    SessionAssemblyStateListener,
)


class SessionAssemblyScreenModel:
    """Drive direct file/folder ingestion and draft session assembly for the desktop UI."""

    def __init__(
        self,
        assembly_service: SessionAssemblyService,
        *,
        error_presenter: UiErrorPresenter | None = None,
    ) -> None:
        self._assembly_service = assembly_service
        self._state = SessionAssemblyState()
        self._listeners: list[SessionAssemblyStateListener] = []
        self._lock = Lock()
        self._error_presenter = error_presenter or DefaultUiErrorPresenter()

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
        return self._set_state(SessionAssemblyState())

    def add_paths(self, paths: tuple[Path, ...]) -> SessionAssemblyState:
        combined = self._state.selected_paths + tuple(path.resolve() for path in paths)
        return self._refresh(selected_paths=combined)

    def remove_paths(self, paths: tuple[Path, ...]) -> SessionAssemblyState:
        removed = {path.resolve() for path in paths}
        remaining = tuple(path for path in self._state.selected_paths if path.resolve() not in removed)
        return self._refresh(selected_paths=remaining)

    def set_session_id(self, session_id: str) -> SessionAssemblyState:
        return self._refresh(session_id=session_id)

    def set_title(self, title: str) -> SessionAssemblyState:
        return self._refresh(title=title)

    def create_session(self):
        if self._state.draft is None:
            raise ValueError("Session assembly requires at least one selected input.")
        try:
            return self._assembly_service.create_session(self._state.draft)
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
    ) -> SessionAssemblyState:
        next_paths = selected_paths if selected_paths is not None else self._state.selected_paths
        next_session_id = session_id if session_id is not None else self._state.session_id
        next_title = title if title is not None else self._state.title
        try:
            draft = self._assembly_service.assemble_draft(
                next_paths,
                session_id=next_session_id,
                title=next_title,
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
        return self._set_state(
            SessionAssemblyState(
                selected_paths=resolved_paths,
                session_id=draft.session_id,
                title=draft.title or "",
                suggested_pathway=draft.pathway.value,
                sources=tuple(
                    SessionAssemblySourceItem(
                        source_id=source.source_id,
                        label=source.label,
                        location=source.location,
                        source_type=source.source_type.value,
                        suggested_pathway=source.suggested_pathway.value,
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

    def _set_state(self, new_state: SessionAssemblyState) -> SessionAssemblyState:
        with self._lock:
            self._state = new_state
            listeners = tuple(self._listeners)
            state = self._state
        for listener in listeners:
            listener(state)
        return state
