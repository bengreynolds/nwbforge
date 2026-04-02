"""Application services for persisting resumable session snapshots."""

from __future__ import annotations

import logging

from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.services.models import ConversionExecution, ConversionPreview, ReviewSubmission
from nwbforge.domain.contracts import SessionSnapshotStore
from nwbforge.domain.models import SessionSnapshot


class SessionPersistenceService:
    """Persist execution and review state as resumable session snapshots."""

    _logger = get_logger(__name__)

    def __init__(self, snapshot_store: SessionSnapshotStore) -> None:
        self._snapshot_store = snapshot_store

    def persist_preview(self, preview: ConversionPreview):
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
        return self._snapshot_store.save(snapshot)

    def persist_execution(self, execution: ConversionExecution):
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
        return self._snapshot_store.save(snapshot)

    def persist_review_submission(self, submission: ReviewSubmission):
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
        return self._snapshot_store.save(snapshot)

    def load(self, session_id: str) -> SessionSnapshot | None:
        log_event(
            self._logger,
            logging.DEBUG,
            "Loading session snapshot.",
            session_id=session_id,
        )
        return self._snapshot_store.load(session_id)
