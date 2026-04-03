"""Application services for persisting resumable session snapshots."""

from __future__ import annotations

import logging
from time import perf_counter

from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.services.models import ConversionExecution, ConversionPreview, ReviewSubmission
from nwbforge.domain.contracts import SessionSnapshotStore
from nwbforge.domain.models import SessionSnapshot, SessionSnapshotHistoryEntry


class SessionPersistenceService:
    """Persist execution and review state as resumable session snapshots."""

    _logger = get_logger(__name__)

    def __init__(self, snapshot_store: SessionSnapshotStore) -> None:
        self._snapshot_store = snapshot_store

    def persist_preview(self, preview: ConversionPreview):
        started = perf_counter()
        log_event(
            self._logger,
            logging.DEBUG,
            "Persisting preview snapshot.",
            session_id=preview.session.session_id,
        )
        snapshot = SessionSnapshot(
            session=preview.session,
            provenance_record=preview.provenance_record,
        )
        artifact = self._snapshot_store.save(snapshot)
        log_event(
            self._logger,
            logging.DEBUG,
            "Persisted preview snapshot.",
            session_id=preview.session.session_id,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
        return artifact

    def persist_execution(self, execution: ConversionExecution):
        started = perf_counter()
        log_event(
            self._logger,
            logging.DEBUG,
            "Persisting execution snapshot.",
            session_id=execution.session.session_id,
            generated_artifact_count=len(execution.provenance_record.generated_artifacts),
        )
        snapshot = SessionSnapshot(
            session=execution.session,
            provenance_record=execution.provenance_record,
            validation_summary=execution.validation_summary,
            review_outcome=execution.review_outcome,
        )
        artifact = self._snapshot_store.save(snapshot)
        log_event(
            self._logger,
            logging.DEBUG,
            "Persisted execution snapshot.",
            session_id=execution.session.session_id,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
        return artifact

    def persist_review_submission(self, submission: ReviewSubmission):
        started = perf_counter()
        log_event(
            self._logger,
            logging.DEBUG,
            "Persisting review snapshot.",
            session_id=submission.execution.session.session_id,
            decision=submission.review_record.decision.value,
        )
        snapshot = SessionSnapshot(
            session=submission.execution.session,
            provenance_record=submission.provenance_record,
            validation_summary=submission.execution.validation_summary,
            review_outcome=submission.execution.review_outcome,
            review_record=submission.review_record,
        )
        artifact = self._snapshot_store.save(snapshot)
        log_event(
            self._logger,
            logging.DEBUG,
            "Persisted review snapshot.",
            session_id=submission.execution.session.session_id,
            decision=submission.review_record.decision.value,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
        return artifact

    def load(self, session_id: str) -> SessionSnapshot | None:
        started = perf_counter()
        log_event(
            self._logger,
            logging.DEBUG,
            "Loading session snapshot.",
            session_id=session_id,
        )
        snapshot = self._snapshot_store.load(session_id)
        log_event(
            self._logger,
            logging.DEBUG,
            "Loaded session snapshot.",
            session_id=session_id,
            found=snapshot is not None,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
        return snapshot

    def list_history(self, session_id: str) -> tuple[SessionSnapshotHistoryEntry, ...]:
        started = perf_counter()
        history = self._snapshot_store.list_history(session_id)
        log_event(
            self._logger,
            logging.DEBUG,
            "Listed session snapshot history.",
            session_id=session_id,
            snapshot_count=len(history),
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
        return history

    def load_version(self, session_id: str, snapshot_id: str) -> SessionSnapshot | None:
        started = perf_counter()
        snapshot = self._snapshot_store.load_version(session_id, snapshot_id)
        log_event(
            self._logger,
            logging.DEBUG,
            "Loaded session snapshot version.",
            session_id=session_id,
            snapshot_id=snapshot_id,
            found=snapshot is not None,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
        return snapshot

    def set_history_limit(self, history_limit: int) -> None:
        setter = getattr(self._snapshot_store, "set_history_limit", None)
        if setter is not None:
            setter(history_limit)
