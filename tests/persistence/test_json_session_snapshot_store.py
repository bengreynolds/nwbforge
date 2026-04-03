from datetime import UTC, datetime
from pathlib import Path

from nwbforge.domain.enums import (
    ConversionPathway,
    IssueSeverity,
    ReviewStatus,
    SessionStatus,
    SourceType,
    ValidationReviewStatus,
)
from nwbforge.domain.models import (
    ConversionSession,
    ExecutionReviewRecord,
    ProvenanceArtifact,
    ProvenanceRecord,
    SessionSnapshot,
    SourceReference,
    ValidationIssue,
    ValidationReviewOutcome,
    ValidationSummary,
)
from nwbforge.persistence import JsonSessionSnapshotStore


def test_json_session_snapshot_store_round_trips_snapshot(tmp_path: Path) -> None:
    created_at = datetime(2026, 3, 31, 18, 30, tzinfo=UTC)
    session = ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        status=SessionStatus.COMPLETED,
        sources=(
            SourceReference(
                source_id="source-1",
                location=Path("data") / "session_manifest.json",
                source_type=SourceType.FILE,
                label="Session manifest",
                adapter_hint="session_manifest",
            ),
        ),
        created_at=created_at,
        updated_at=created_at,
        notes=("pilot session",),
    )
    snapshot = SessionSnapshot(
        session=session,
        provenance_record=ProvenanceRecord(
            session_id=session.session_id,
            pathway=session.pathway,
            generated_artifacts=(
                ProvenanceArtifact(artifact_type="nwb", location=tmp_path / "session.nwb"),
                ProvenanceArtifact(
                    artifact_type="validation_report",
                    location=tmp_path / "validation-report.json",
                ),
            ),
            adapter_ids=("session_manifest",),
        ),
        validation_summary=ValidationSummary(
            issues=(
                ValidationIssue(
                    code="warning-1",
                    message="Example warning.",
                    severity=IssueSeverity.WARNING,
                    location="/general/subject",
                    tool="nwbinspector",
                ),
            )
        ),
        review_outcome=ValidationReviewOutcome(
            status=ValidationReviewStatus.REVIEW,
            blocks_completion=False,
            requires_manual_review=True,
            error_count=0,
            warning_count=1,
        ),
        review_record=ExecutionReviewRecord(
            session_id=session.session_id,
            reviewer="alice",
            decision=ReviewStatus.APPROVED,
            validation_status=ValidationReviewStatus.REVIEW,
            acknowledged_issue_refs=("warning-1@/general/subject",),
            rationale="Accepted after review.",
            reviewed_at=created_at,
        ),
    )

    store = JsonSessionSnapshotStore(tmp_path / "state")
    artifact = store.save(snapshot)
    loaded = store.load(session.session_id)

    assert artifact.artifact_type == "session_snapshot"
    assert loaded is not None
    assert loaded.session == snapshot.session
    assert loaded.provenance_record == snapshot.provenance_record
    assert loaded.validation_summary == snapshot.validation_summary
    assert loaded.review_outcome == snapshot.review_outcome
    assert loaded.review_record == snapshot.review_record
    assert loaded.snapshot_id is not None
    assert loaded.saved_at is not None
    assert artifact.location == tmp_path / "state" / session.session_id / "session-state.json"


def test_json_session_snapshot_store_returns_none_for_missing_session(tmp_path: Path) -> None:
    store = JsonSessionSnapshotStore(tmp_path / "state")

    assert store.load("missing-session") is None


def test_json_session_snapshot_store_tracks_version_history(tmp_path: Path) -> None:
    created_at = datetime(2026, 3, 31, 18, 30, tzinfo=UTC)
    session = ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        status=SessionStatus.READY_TO_WRITE,
        sources=(
            SourceReference(
                source_id="source-1",
                location=Path("data") / "session_manifest.json",
                source_type=SourceType.FILE,
                label="Session manifest",
                adapter_hint="session_manifest",
            ),
        ),
        created_at=created_at,
        updated_at=created_at,
    )
    store = JsonSessionSnapshotStore(tmp_path / "state", history_limit=5)

    first_artifact = store.save(SessionSnapshot(session=session))
    second_artifact = store.save(
        SessionSnapshot(
            session=ConversionSession(
                session_id=session.session_id,
                pathway=session.pathway,
                status=SessionStatus.COMPLETED,
                sources=session.sources,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
        )
    )

    history = store.list_history(session.session_id)

    assert len(history) == 2
    assert history[0].status == SessionStatus.COMPLETED.value
    assert history[1].status == SessionStatus.READY_TO_WRITE.value
    assert store.load_version(session.session_id, history[0].snapshot_id) is not None
    assert first_artifact.location == second_artifact.location


def test_json_session_snapshot_store_trims_history_to_limit(tmp_path: Path) -> None:
    session = ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        status=SessionStatus.READY_TO_WRITE,
    )
    store = JsonSessionSnapshotStore(tmp_path / "state", history_limit=2)

    store.save(SessionSnapshot(session=session))
    store.save(SessionSnapshot(session=session.transition(SessionStatus.VALIDATING)))
    store.save(SessionSnapshot(session=session.transition(SessionStatus.COMPLETED)))

    history = store.list_history(session.session_id)

    assert len(history) == 2
