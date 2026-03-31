import json
from pathlib import Path

import pytest

from nwbforge.app.services import (
    ConversionExecution,
    ConversionPreview,
    ExecutionReviewService,
    ReviewDecisionError,
)
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
    MappingPlan,
    NormalizedMetadataBundle,
    ProvenanceArtifact,
    ProvenanceRecord,
    ValidationIssue,
    ValidationReviewOutcome,
    ValidationSummary,
)
from nwbforge.validation import JsonExecutionReviewArtifactService


def make_execution(
    tmp_path: Path,
    *,
    issues: tuple[ValidationIssue, ...] = (),
    review_outcome: ValidationReviewOutcome | None = None,
) -> ConversionExecution:
    session = ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        status=SessionStatus.COMPLETED,
    )
    preview = ConversionPreview(
        session=session,
        extraction_results=(),
        normalized_metadata=NormalizedMetadataBundle(),
        mapping_plan=MappingPlan(pathway=session.pathway),
        provenance_record=ProvenanceRecord(
            session_id=session.session_id,
            pathway=session.pathway,
            input_artifacts=(),
            generated_artifacts=(),
        ),
    )
    validation_summary = ValidationSummary(issues=issues)
    outcome = review_outcome or ValidationReviewOutcome(
        status=ValidationReviewStatus.PASS,
        blocks_completion=False,
        requires_manual_review=False,
        error_count=0,
        warning_count=0,
    )
    provenance_record = ProvenanceRecord(
        session_id=session.session_id,
        pathway=session.pathway,
        generated_artifacts=(ProvenanceArtifact(artifact_type="nwb", location=tmp_path / "session.nwb"),),
    )
    return ConversionExecution(
        preview=preview,
        session=session,
        output_artifacts=provenance_record.generated_artifacts,
        provenance_record=provenance_record,
        validation_summary=validation_summary,
        review_outcome=outcome,
    )


def test_execution_review_service_persists_clean_approval(tmp_path: Path) -> None:
    execution = make_execution(tmp_path)

    submission = ExecutionReviewService(JsonExecutionReviewArtifactService()).submit_review(
        execution,
        reviewer="alice",
        decision=ReviewStatus.APPROVED,
    )

    assert submission.review_record.decision == ReviewStatus.APPROVED
    assert submission.review_artifact.artifact_type == "review_decision"
    assert submission.provenance_record.generated_artifacts[-1].artifact_type == "review_decision"


def test_execution_review_service_requires_acknowledgement_for_review_required_execution(
    tmp_path: Path,
) -> None:
    issue = ValidationIssue(
        code="nwbinspector-demo",
        message="Example warning.",
        severity=IssueSeverity.WARNING,
        location="/general/subject",
        tool="nwbinspector",
    )
    execution = make_execution(
        tmp_path,
        issues=(issue,),
        review_outcome=ValidationReviewOutcome(
            status=ValidationReviewStatus.REVIEW,
            blocks_completion=False,
            requires_manual_review=True,
            error_count=0,
            warning_count=1,
        ),
    )
    service = ExecutionReviewService(JsonExecutionReviewArtifactService())

    with pytest.raises(ReviewDecisionError):
        service.submit_review(
            execution,
            reviewer="alice",
            decision=ReviewStatus.APPROVED,
        )

    submission = service.submit_review(
        execution,
        reviewer="alice",
        decision=ReviewStatus.APPROVED,
        acknowledged_issue_refs=execution.validation_summary.issue_refs(),
        rationale="Reviewed the warning and accepted the output.",
    )

    assert submission.review_record.acknowledged_issue_refs == execution.validation_summary.issue_refs()


def test_execution_review_service_requires_override_for_blocked_approval(tmp_path: Path) -> None:
    issue = ValidationIssue(
        code="schema-error",
        message="Required field missing.",
        severity=IssueSeverity.ERROR,
        location="/session_start_time",
        tool="pynwb",
    )
    execution = make_execution(
        tmp_path,
        issues=(issue,),
        review_outcome=ValidationReviewOutcome(
            status=ValidationReviewStatus.BLOCKED,
            blocks_completion=True,
            requires_manual_review=True,
            error_count=1,
            warning_count=0,
        ),
    )
    service = ExecutionReviewService(JsonExecutionReviewArtifactService())

    with pytest.raises(ReviewDecisionError):
        service.submit_review(
            execution,
            reviewer="alice",
            decision=ReviewStatus.APPROVED,
            acknowledged_issue_refs=execution.validation_summary.issue_refs(),
        )

    submission = service.submit_review(
        execution,
        reviewer="alice",
        decision=ReviewStatus.APPROVED,
        acknowledged_issue_refs=execution.validation_summary.issue_refs(),
        override_blocks_completion=True,
        rationale="Temporary override for internal prototype review.",
    )

    payload = json.loads(submission.review_artifact.location.read_text(encoding="utf-8"))
    assert payload["override_blocks_completion"] is True
    assert payload["decision"] == "approved"
