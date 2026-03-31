from datetime import UTC, datetime
from pathlib import Path

from nwbforge.domain.enums import (
    ConversionPathway,
    IssueSeverity,
    MappingAction,
    ReviewStatus,
    SessionStatus,
    SourceType,
    ValidationReviewStatus,
    ValueOrigin,
)
from nwbforge.domain.models import (
    AcquisitionStream,
    ConversionSession,
    ExecutionReviewRecord,
    MappingDecision,
    MappingPlan,
    NormalizedMetadataBundle,
    NormalizedSessionMetadata,
    NormalizedSubject,
    NormalizedValue,
    ProvenanceArtifact,
    ProvenanceRecord,
    ReviewIssue,
    SourceReference,
    ValidationIssue,
    ValidationSummary,
)


def test_conversion_session_add_source_updates_status_and_ids() -> None:
    created_at = datetime(2026, 3, 31, 21, 0, tzinfo=UTC)
    source = SourceReference(
        source_id="raw-ephys",
        location=Path("data/session_01"),
        source_type=SourceType.DIRECTORY,
        label="Raw ephys folder",
    )
    session = ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        created_at=created_at,
        updated_at=created_at,
    )

    updated = session.add_source(source, updated_at=created_at)

    assert updated.status == SessionStatus.SOURCES_ADDED
    assert updated.source_ids == ("raw-ephys",)
    assert session.sources == ()


def test_normalized_bundle_surfaces_pending_review_values() -> None:
    review_value = NormalizedValue(
        value="mouse-01",
        origin=ValueOrigin.INFERRED,
        review_status=ReviewStatus.NEEDS_REVIEW,
        source_ids=("manifest",),
    )
    session_description = NormalizedValue(
        value="Visual stimulation",
        origin=ValueOrigin.USER_SUPPLIED,
    )
    stream = AcquisitionStream(
        stream_id="stream-01",
        name=NormalizedValue(value="ecephys", origin=ValueOrigin.ADAPTER_EXTRACTED),
        modality="ecephys",
        source_ids=("raw-ephys",),
        metadata={"clock_alignment": review_value},
    )
    bundle = NormalizedMetadataBundle(
        subject=NormalizedSubject(subject_id=review_value),
        session=NormalizedSessionMetadata(session_description=session_description),
        acquisition_streams=(stream,),
    )

    pending = bundle.pending_review_values()

    assert len(pending) == 2
    assert all(value.review_status == ReviewStatus.NEEDS_REVIEW for value in pending)


def test_mapping_plan_exposes_blocking_issues_and_review_state() -> None:
    decision = MappingDecision(
        source_key="session.operator_notes",
        target_path="general/notes",
        action=MappingAction.DESCRIBE,
        rationale="Preserve free-text operator context",
        review_status=ReviewStatus.NEEDS_REVIEW,
    )
    issue = ReviewIssue(
        code="missing-subject-species",
        message="Species is required before export.",
        severity=IssueSeverity.ERROR,
    )
    plan = MappingPlan(
        pathway=ConversionPathway.CUSTOM,
        decisions=(decision,),
        issues=(issue,),
    )

    assert plan.requires_manual_review() is True
    assert plan.blocking_issues() == (issue,)
    assert plan.target_paths() == ("general/notes",)


def test_provenance_and_validation_models_provide_basic_summaries() -> None:
    raw_artifact = ProvenanceArtifact(
        artifact_type="input",
        location=Path("data/session_01/raw.bin"),
        sha256="abc123",
    )
    report_artifact = ProvenanceArtifact(
        artifact_type="report",
        location=Path("artifacts/session_01/report.json"),
    )
    record = ProvenanceRecord(
        session_id="sess-001",
        pathway=ConversionPathway.HYBRID,
        input_artifacts=(raw_artifact,),
        generated_artifacts=(report_artifact,),
        adapter_ids=("spikeglx", "custom-annotations"),
    )
    validation = ValidationSummary(
        issues=(
            ValidationIssue(
                code="schema-warning",
                message="Optional field missing",
                severity=IssueSeverity.WARNING,
                tool="pynwb.validate",
            ),
        )
    )

    assert record.artifact_locations() == (
        Path("data/session_01/raw.bin"),
        Path("artifacts/session_01/report.json"),
    )
    assert validation.errors() == ()
    assert len(validation.warnings()) == 1
    assert validation.issue_refs() == ("schema-warning",)
    assert validation.is_passing() is True


def test_execution_review_record_captures_review_metadata() -> None:
    record = ExecutionReviewRecord(
        session_id="sess-001",
        reviewer="alice",
        decision=ReviewStatus.APPROVED,
        validation_status=ValidationReviewStatus.REVIEW,
        acknowledged_issue_refs=("warning-1",),
        rationale="Accepted after manual review.",
    )

    assert record.reviewer == "alice"
    assert record.decision == ReviewStatus.APPROVED
    assert record.acknowledged_issue_refs == ("warning-1",)
