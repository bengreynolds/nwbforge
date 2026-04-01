"""Application services for persisting resumable session snapshots."""

from __future__ import annotations

from nwbforge.app.services.models import ConversionExecution, ConversionPreview, ReviewSubmission
from nwbforge.domain.contracts import SessionSnapshotStore
from nwbforge.domain.models import SessionSnapshot


class SessionPersistenceService:
    """Persist execution and review state as resumable session snapshots."""

    def __init__(self, snapshot_store: SessionSnapshotStore) -> None:
        self._snapshot_store = snapshot_store

    def persist_preview(self, preview: ConversionPreview):
        snapshot = SessionSnapshot(
            session=preview.session,
            provenance_record=preview.provenance_record,
        )
        return self._snapshot_store.save(snapshot)

    def persist_execution(self, execution: ConversionExecution):
        snapshot = SessionSnapshot(
            session=execution.session,
            provenance_record=execution.provenance_record,
            validation_summary=execution.validation_summary,
            review_outcome=execution.review_outcome,
        )
        return self._snapshot_store.save(snapshot)

    def persist_review_submission(self, submission: ReviewSubmission):
        snapshot = SessionSnapshot(
            session=submission.execution.session,
            provenance_record=submission.provenance_record,
            validation_summary=submission.execution.validation_summary,
            review_outcome=submission.execution.review_outcome,
            review_record=submission.review_record,
        )
        return self._snapshot_store.save(snapshot)

    def load(self, session_id: str) -> SessionSnapshot | None:
        return self._snapshot_store.load(session_id)
