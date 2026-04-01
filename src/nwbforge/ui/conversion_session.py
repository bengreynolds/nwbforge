"""Toolkit-agnostic conversion-session screen model."""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path
from threading import Lock

from nwbforge.app.runtime import ConversionExecutor
from nwbforge.app.services.models import ConversionExecution, ConversionPreview
from nwbforge.domain.models import ConversionSession
from nwbforge.ui.models import (
    ConversionSessionScreenState,
    ConversionSessionStateListener,
    conversion_source_items,
)


class ConversionSessionScreenModel:
    """Drive preview/execution state for a future conversion-session screen."""

    def __init__(self, executor: ConversionExecutor) -> None:
        self._executor = executor
        self._state = ConversionSessionScreenState()
        self._listeners: list[ConversionSessionStateListener] = []
        self._lock = Lock()

    @property
    def state(self) -> ConversionSessionScreenState:
        return self._state

    def subscribe(self, listener: ConversionSessionStateListener, *, emit_initial: bool = True) -> None:
        with self._lock:
            self._listeners.append(listener)
            state = self._state
        if emit_initial:
            listener(state)

    def load_session(self, session: ConversionSession) -> ConversionSessionScreenState:
        return self._set_state(
            ConversionSessionScreenState(
                session=session,
                sources=conversion_source_items(session.sources),
            )
        )

    def start_preview(self) -> Future[ConversionPreview]:
        session = self._require_session()
        self._set_state(
            replace(
                self._state,
                is_preview_running=True,
                error_message=None,
                preview=None,
                execution=None,
                progress_event=None,
            )
        )
        future = self._executor.submit_preview(session, progress_callback=self._handle_progress)
        future.add_done_callback(self._handle_preview_complete)
        return future

    def start_execution(self, output_path: Path) -> Future[ConversionExecution]:
        preview = self._require_preview()
        self._set_state(
            replace(
                self._state,
                is_execution_running=True,
                output_path=output_path,
                error_message=None,
                execution=None,
                progress_event=None,
            )
        )
        future = self._executor.submit_execute(
            preview,
            output_path,
            progress_callback=self._handle_progress,
        )
        future.add_done_callback(self._handle_execution_complete)
        return future

    def shutdown(self, wait: bool = True) -> None:
        shutdown = getattr(self._executor, "shutdown", None)
        if shutdown is not None:
            shutdown(wait=wait)

    def _handle_progress(self, event) -> None:
        self._set_state(replace(self._state, progress_event=event, error_message=None))

    def _handle_preview_complete(self, future: Future[ConversionPreview]) -> None:
        try:
            preview = future.result()
        except Exception as exc:
            user_message = getattr(exc, "user_message", str(exc))
            self._set_state(
                replace(
                    self._state,
                    is_preview_running=False,
                    error_message=user_message,
                )
            )
            return

        self._set_state(
            replace(
                self._state,
                session=preview.session,
                sources=conversion_source_items(preview.session.sources),
                preview=preview,
                execution=None,
                is_preview_running=False,
                error_message=None,
            )
        )

    def _handle_execution_complete(self, future: Future[ConversionExecution]) -> None:
        try:
            execution = future.result()
        except Exception as exc:
            user_message = getattr(exc, "user_message", str(exc))
            self._set_state(
                replace(
                    self._state,
                    is_execution_running=False,
                    error_message=user_message,
                )
            )
            return

        self._set_state(
            replace(
                self._state,
                session=execution.session,
                sources=conversion_source_items(execution.session.sources),
                execution=execution,
                preview=execution.preview,
                is_execution_running=False,
                error_message=None,
            )
        )

    def _require_session(self) -> ConversionSession:
        if self._state.session is None:
            raise ValueError("Conversion session screen requires a loaded session before preview can start.")
        return self._state.session

    def _require_preview(self) -> ConversionPreview:
        if self._state.preview is None:
            raise ValueError("Conversion preview must be available before execution can start.")
        return self._state.preview

    def _set_state(self, new_state: ConversionSessionScreenState) -> ConversionSessionScreenState:
        with self._lock:
            self._state = new_state
            listeners = tuple(self._listeners)
            state = self._state
        for listener in listeners:
            listener(state)
        return state
