import json
from pathlib import Path

from nwbforge.domain.enums import (
    ConversionPathway,
    IssueSeverity,
    ReviewStatus,
    SessionStatus,
    ValidationReviewStatus,
)
from nwbforge.domain.models import (
    ConversionSession,
    ExecutionReviewRecord,
    ProvenanceArtifact,
    ProvenanceRecord,
    ValidationIssue,
    ValidationReviewOutcome,
    ValidationSummary,
)
from nwbforge.validation import JsonExecutionReviewArtifactService


def test_json_execution_review_artifact_service_writes_review_record(tmp_path: Path) -> None:
    session = ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        status=SessionStatus.COMPLETED,
    )
    provenance_record = ProvenanceRecord(
        session_id=session.session_id,
        pathway=session.pathway,
        generated_artifacts=(ProvenanceArtifact(artifact_type="nwb", location=tmp_path / "session.nwb"),),
    )
    validation_summary = ValidationSummary(
        issues=(
            ValidationIssue(
                code="warning-1",
                message="Example warning.",
                severity=IssueSeverity.WARNING,
                location="/general/subject",
                tool="nwbinspector",
            ),
        )
    )
    review_outcome = ValidationReviewOutcome(
        status=ValidationReviewStatus.REVIEW,
        blocks_completion=False,
        requires_manual_review=True,
        error_count=0,
        warning_count=1,
    )
    review_record = ExecutionReviewRecord(
        session_id=session.session_id,
        reviewer="alice",
        decision=ReviewStatus.APPROVED,
        validation_status=ValidationReviewStatus.REVIEW,
        acknowledged_issue_refs=validation_summary.issue_refs(),
        rationale="Reviewed and accepted warning.",
    )

    artifact = JsonExecutionReviewArtifactService().write_review(
        session,
        provenance_record,
        validation_summary,
        review_outcome,
        review_record,
    )

    payload = json.loads(artifact.location.read_text(encoding="utf-8"))
    assert artifact.artifact_type == "review_decision"
    assert payload["session_id"] == "sess-001"
    assert payload["decision"] == "approved"
    assert payload["acknowledged_issue_refs"] == list(validation_summary.issue_refs())
    assert payload["review_outcome"]["status"] == "review"
