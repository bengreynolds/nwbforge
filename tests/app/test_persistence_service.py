from pathlib import Path

from nwbforge.app.services import (
    ConversionExecution,
    ConversionPreview,
    ExecutionReviewService,
    SessionPersistenceService,
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
    MappingPlan,
    NormalizedMetadataBundle,
    ProvenanceArtifact,
    ProvenanceRecord,
    ValidationIssue,
    ValidationReviewOutcome,
    ValidationSummary,
)
from nwbforge.persistence import JsonSessionSnapshotStore
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
        ),
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
        validation_summary=ValidationSummary(issues=issues),
        review_outcome=review_outcome
        or ValidationReviewOutcome(
            status=ValidationReviewStatus.PASS,
            blocks_completion=False,
            requires_manual_review=False,
            error_count=0,
            warning_count=0,
        ),
    )


def test_session_persistence_service_persists_execution_state(tmp_path: Path) -> None:
    service = SessionPersistenceService(JsonSessionSnapshotStore(tmp_path / "state"))
    execution = make_execution(tmp_path)

    artifact = service.persist_execution(execution)
    snapshot = service.load(execution.session.session_id)

    assert artifact.artifact_type == "session_snapshot"
    assert snapshot is not None
    assert snapshot.session == execution.session
    assert snapshot.review_record is None
    assert snapshot.review_outcome == execution.review_outcome


def test_session_persistence_service_persists_review_submission_state(tmp_path: Path) -> None:
    issue = ValidationIssue(
        code="warning-1",
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
    review_submission = ExecutionReviewService(
        JsonExecutionReviewArtifactService()
    ).submit_review(
        execution,
        reviewer="alice",
        decision=ReviewStatus.APPROVED,
        acknowledged_issue_refs=execution.validation_summary.issue_refs(),
        rationale="Accepted after warning review.",
    )
    service = SessionPersistenceService(JsonSessionSnapshotStore(tmp_path / "state"))

    service.persist_review_submission(review_submission)
    snapshot = service.load(execution.session.session_id)

    assert snapshot is not None
    assert snapshot.review_record == review_submission.review_record
    assert snapshot.provenance_record == review_submission.provenance_record
    assert snapshot.provenance_record.generated_artifacts[-1].artifact_type == "review_decision"
