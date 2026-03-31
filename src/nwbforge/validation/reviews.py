"""Review artifact persistence for validation-driven workflow decisions."""

from __future__ import annotations

import json
from pathlib import Path

from nwbforge.domain.contracts import ReviewArtifactService
from nwbforge.domain.models import (
    ConversionSession,
    ExecutionReviewRecord,
    ProvenanceArtifact,
    ProvenanceRecord,
    ValidationReviewOutcome,
    ValidationSummary,
)


class JsonExecutionReviewArtifactService(ReviewArtifactService):
    """Persist a review decision as a machine-readable JSON artifact."""

    def __init__(self, filename: str = "review-decision.json") -> None:
        self._filename = filename

    def write_review(
        self,
        session: ConversionSession,
        provenance_record: ProvenanceRecord,
        validation_summary: ValidationSummary,
        review_outcome: ValidationReviewOutcome,
        review_record: ExecutionReviewRecord,
    ) -> ProvenanceArtifact:
        review_path = self._review_path(session, provenance_record)
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(
            json.dumps(
                self._payload(
                    session,
                    provenance_record,
                    validation_summary,
                    review_outcome,
                    review_record,
                ),
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return ProvenanceArtifact(
            artifact_type="review_decision",
            location=review_path,
            description="Machine-readable review decision record.",
        )

    def _review_path(
        self,
        session: ConversionSession,
        provenance_record: ProvenanceRecord,
    ) -> Path:
        if provenance_record.generated_artifacts:
            return provenance_record.generated_artifacts[0].location.parent / self._filename
        return Path("artifacts") / session.session_id / self._filename

    @staticmethod
    def _payload(
        session: ConversionSession,
        provenance_record: ProvenanceRecord,
        validation_summary: ValidationSummary,
        review_outcome: ValidationReviewOutcome,
        review_record: ExecutionReviewRecord,
    ) -> dict[str, object]:
        return {
            "session_id": session.session_id,
            "pathway": str(session.pathway),
            "decision": str(review_record.decision),
            "reviewer": review_record.reviewer,
            "reviewed_at": review_record.reviewed_at.isoformat(),
            "validation_status": str(review_record.validation_status),
            "acknowledged_issue_refs": list(review_record.acknowledged_issue_refs),
            "override_blocks_completion": review_record.override_blocks_completion,
            "rationale": review_record.rationale,
            "validation_issue_refs": list(validation_summary.issue_refs()),
            "generated_artifact_types": [
                artifact.artifact_type for artifact in provenance_record.generated_artifacts
            ],
            "review_outcome": {
                "status": str(review_outcome.status),
                "blocks_completion": review_outcome.blocks_completion,
                "requires_manual_review": review_outcome.requires_manual_review,
            },
        }
