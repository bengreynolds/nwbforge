from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from nwbforge.app.runtime import PipelineProgressEvent, PipelineRuntimeError, PipelineStage
from nwbforge.app.services import ExecutionReviewService, SessionPersistenceService
from nwbforge.app.services.models import ConversionExecution, ConversionPreview
from nwbforge.domain.enums import (
    ConversionPathway,
    IssueSeverity,
    ReviewStatus,
    SessionStatus,
    SourceType,
    ValidationReviewStatus,
    ValueOrigin,
)
from nwbforge.domain.models import (
    ConversionSession,
    ExecutionReviewRecord,
    ExtractedField,
    ExtractionResult,
    MappingPlan,
    NormalizedSessionMetadata,
    NormalizedMetadataBundle,
    NormalizedSubject,
    NormalizedValue,
    ProvenanceArtifact,
    ProvenanceRecord,
    SourceReference,
    ValidationIssue,
    ValidationReviewOutcome,
    ValidationSummary,
)
from nwbforge.validation import JsonExecutionReviewArtifactService
from nwbforge.ui import ConversionSessionScreenModel
from nwbforge.persistence import JsonSessionSnapshotStore


class FakeConversionExecutor:
    def __init__(
        self,
        *,
        preview_result: ConversionPreview | Exception,
        execution_result: ConversionExecution | Exception | None = None,
    ) -> None:
        self._preview_result = preview_result
        self._execution_result = execution_result

    def submit_preview(self, session, *, progress_callback=None):
        future: Future[ConversionPreview] = Future()
        if progress_callback is not None:
            progress_callback(
                PipelineProgressEvent(
                    session_id=session.session_id,
                    stage=PipelineStage.INSPECTING,
                    percent_complete=10,
                    message="Inspecting sources.",
                )
            )
        if isinstance(self._preview_result, Exception):
            future.set_exception(self._preview_result)
        else:
            future.set_result(self._preview_result)
        return future

    def submit_execute(self, preview, output_path: Path, *, progress_callback=None):
        future: Future[ConversionExecution] = Future()
        if progress_callback is not None:
            progress_callback(
                PipelineProgressEvent(
                    session_id=preview.session.session_id,
                    stage=PipelineStage.WRITING,
                    percent_complete=25,
                    message="Writing NWB output.",
                )
            )
        execution_result = self._execution_result
        if execution_result is None:
            raise AssertionError("Execution result was not configured.")
        if isinstance(execution_result, Exception):
            future.set_exception(execution_result)
        else:
            future.set_result(execution_result)
        return future


def make_session() -> ConversionSession:
    return ConversionSession(
        session_id="session-ui-01",
        pathway=ConversionPathway.SUPPORTED,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=Path("C:/tmp/session_manifest.json"),
                source_type=SourceType.FILE,
                label="Structured session manifest",
            ),
        ),
    )


def make_preview(
    session: ConversionSession,
    *,
    extraction_results: tuple[ExtractionResult, ...] | None = None,
    normalized_metadata: NormalizedMetadataBundle | None = None,
) -> ConversionPreview:
    extraction_result = ExtractionResult(
        source_id="manifest",
        adapter_id="session_manifest",
        record_type="session_manifest",
        fields={
            "session.session_id": ExtractedField(
                key="session.session_id",
                value="session-ui-01",
                source_id="manifest",
            )
        },
        issues=(),
    )
    return ConversionPreview(
        session=session.transition(SessionStatus.READY_TO_WRITE),
        extraction_results=extraction_results or (extraction_result,),
        normalized_metadata=normalized_metadata or NormalizedMetadataBundle(),
        mapping_plan=MappingPlan(pathway=session.pathway, decisions=(), issues=()),
        provenance_record=ProvenanceRecord(
            session_id=session.session_id,
            pathway=session.pathway,
            input_artifacts=(
                ProvenanceArtifact(
                    artifact_type="input",
                    location=session.sources[0].location,
                    description=session.sources[0].label,
                ),
            ),
            generated_artifacts=(),
        ),
    )


def make_execution(
    preview: ConversionPreview,
    *,
    issues: tuple[ValidationIssue, ...] = (),
    review_outcome: ValidationReviewOutcome | None = None,
    generated_artifacts: tuple[ProvenanceArtifact, ...] = (),
) -> ConversionExecution:
    validation_summary = ValidationSummary(issues=issues)
    return ConversionExecution(
        preview=preview,
        session=preview.session.transition(SessionStatus.COMPLETED),
        output_artifacts=(
            ProvenanceArtifact(
                artifact_type="nwb",
                location=Path("C:/tmp/output.nwb"),
                description="Converted NWB file",
            ),
        ),
        provenance_record=ProvenanceRecord(
            session_id=preview.provenance_record.session_id,
            pathway=preview.provenance_record.pathway,
            input_artifacts=preview.provenance_record.input_artifacts,
            generated_artifacts=generated_artifacts,
        ),
        validation_summary=validation_summary,
        review_outcome=review_outcome
        or ValidationReviewOutcome(
            status=ValidationReviewStatus.PASS,
            blocks_completion=False,
            requires_manual_review=False,
            error_count=0,
            warning_count=0,
        ),
    )


def test_conversion_session_screen_model_loads_and_runs_preview() -> None:
    session = make_session()
    preview = make_preview(session)
    screen = ConversionSessionScreenModel(FakeConversionExecutor(preview_result=preview))

    loaded_state = screen.load_session(session)
    future = screen.start_preview()
    result = future.result(timeout=5)

    assert loaded_state.session == session
    assert result == preview
    assert screen.state.preview == preview
    assert screen.state.session == preview.session
    assert screen.state.progress_event is not None
    assert screen.state.progress_event.stage is PipelineStage.INSPECTING
    assert len(screen.state.progress_history) >= 1
    assert screen.state.progress_history[-1].stage == PipelineStage.INSPECTING.value
    assert screen.state.is_preview_running is False
    assert screen.state.can_run_execution is True


def test_conversion_session_screen_model_can_clear_session() -> None:
    session = make_session()
    screen = ConversionSessionScreenModel(FakeConversionExecutor(preview_result=make_preview(session)))

    screen.load_session(session)
    state = screen.clear_session()

    assert state.session is None
    assert state.preview is None
    assert state.execution is None


def test_conversion_session_screen_model_runs_execution_after_preview() -> None:
    session = make_session()
    preview = make_preview(session)
    execution = make_execution(preview)
    screen = ConversionSessionScreenModel(
        FakeConversionExecutor(preview_result=preview, execution_result=execution)
    )
    screen.load_session(session)
    screen.start_preview().result(timeout=5)

    future = screen.start_execution(Path("C:/tmp/output.nwb"))
    result = future.result(timeout=5)

    assert result == execution
    assert screen.state.execution == execution
    assert screen.state.output_path == Path("C:/tmp/output.nwb")
    assert screen.state.progress_event is not None
    assert screen.state.progress_event.stage is PipelineStage.WRITING
    assert len(screen.state.progress_history) >= 2
    assert screen.state.progress_history[-1].stage == PipelineStage.WRITING.value
    assert screen.state.is_execution_running is False
    assert screen.state.validation_issues == ()


def test_conversion_session_screen_model_projects_generated_artifacts() -> None:
    session = make_session()
    preview = make_preview(session)
    execution = make_execution(
        preview,
        generated_artifacts=(
            ProvenanceArtifact(
                artifact_type="validation_report",
                location=Path("C:/tmp/validation-report.json"),
                description="Validation report artifact",
            ),
        ),
    )
    screen = ConversionSessionScreenModel(
        FakeConversionExecutor(preview_result=preview, execution_result=execution)
    )
    screen.load_session(session)
    screen.start_preview().result(timeout=5)
    screen.start_execution(Path("C:/tmp/output.nwb")).result(timeout=5)

    assert len(screen.state.generated_artifacts) == 1
    assert screen.state.generated_artifacts[0].artifact_type == "validation_report"


def test_conversion_session_screen_model_projects_metadata_disagreements_from_preview() -> None:
    session = ConversionSession(
        session_id="session-ui-02",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=Path("C:/tmp/session_manifest.json"),
                source_type=SourceType.FILE,
                label="Structured session manifest",
                role="primary",
            ),
            SourceReference(
                source_id="custom",
                location=Path("C:/tmp/custom_session.json"),
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="supplemental",
            ),
        ),
    )
    extraction_results = (
        ExtractionResult(
            source_id="manifest",
            adapter_id="session_manifest",
            record_type="session_manifest",
            fields={
                "subject.subject_id": ExtractedField(
                    key="subject.subject_id",
                    value="primary-mouse-01",
                    source_id="manifest",
                )
            },
        ),
        ExtractionResult(
            source_id="custom",
            adapter_id="custom_json_session",
            record_type="custom_session",
            fields={
                "subject.subject_id": ExtractedField(
                    key="subject.subject_id",
                    value="custom-mouse-01",
                    source_id="custom",
                )
            },
        ),
    )
    normalized_metadata = NormalizedMetadataBundle(
        subject=NormalizedSubject(
            subject_id=NormalizedValue(
                "primary-mouse-01",
                origin=ValueOrigin.ADAPTER_EXTRACTED,
                source_ids=("manifest", "custom"),
                review_status=ReviewStatus.NEEDS_REVIEW,
                notes=(
                    "Multiple extracted fields mapped to the same canonical value.",
                    "Retained value from primary source over supplemental source.",
                ),
            )
        ),
        session=NormalizedSessionMetadata(),
    )
    preview = make_preview(
        session,
        extraction_results=extraction_results,
        normalized_metadata=normalized_metadata,
    )
    screen = ConversionSessionScreenModel(FakeConversionExecutor(preview_result=preview))

    screen.load_session(session)
    screen.start_preview().result(timeout=5)

    assert len(screen.state.metadata_disagreements) == 1
    disagreement = screen.state.metadata_disagreements[0]
    assert disagreement.canonical_key == "subject.subject_id"
    assert disagreement.resolved_value == "primary-mouse-01"
    assert [item.source_id for item in disagreement.source_values] == ["manifest", "custom"]
    assert disagreement.resolution_status == "pending"
    assert disagreement.resolution_history == ("No override history recorded for this field yet.",)


def test_conversion_session_screen_model_applies_session_override_from_metadata_disagreement() -> None:
    session = ConversionSession(
        session_id="session-ui-03",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=Path("C:/tmp/session_manifest.json"),
                source_type=SourceType.FILE,
                label="Structured session manifest",
                role="primary",
            ),
            SourceReference(
                source_id="custom",
                location=Path("C:/tmp/custom_session.json"),
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="supplemental",
            ),
        ),
    )
    preview = make_preview(
        session,
        extraction_results=(
            ExtractionResult(
                source_id="manifest",
                adapter_id="session_manifest",
                record_type="session_manifest",
                fields={
                    "subject.subject_id": ExtractedField(
                        key="subject.subject_id",
                        value="primary-mouse-01",
                        source_id="manifest",
                    )
                },
            ),
            ExtractionResult(
                source_id="custom",
                adapter_id="custom_json_session",
                record_type="custom_session",
                fields={
                    "subject.subject_id": ExtractedField(
                        key="subject.subject_id",
                        value="custom-mouse-01",
                        source_id="custom",
                    )
                },
            ),
        ),
        normalized_metadata=NormalizedMetadataBundle(
            subject=NormalizedSubject(
                subject_id=NormalizedValue(
                    "primary-mouse-01",
                    origin=ValueOrigin.ADAPTER_EXTRACTED,
                    source_ids=("manifest", "custom"),
                    review_status=ReviewStatus.NEEDS_REVIEW,
                )
            ),
            session=NormalizedSessionMetadata(),
        ),
    )
    screen = ConversionSessionScreenModel(FakeConversionExecutor(preview_result=preview))

    screen.load_session(session)
    screen.start_preview().result(timeout=5)
    state = screen.apply_session_override("subject.subject_id", "custom-mouse-01")

    assert state.session is not None
    assert state.session.metadata_overrides["subject.subject_id"] == "custom-mouse-01"
    assert state.preview is None
    assert state.execution is None
    assert state.metadata_disagreements == ()
    assert "Applied session override" in (state.review_message or "")


def test_conversion_session_screen_model_can_clear_session_override() -> None:
    session = make_session()
    session = ConversionSession(
        session_id=session.session_id,
        pathway=session.pathway,
        status=session.status,
        sources=session.sources,
        metadata_overrides={"subject.subject_id": "override-mouse-01"},
    )
    preview = make_preview(session)
    screen = ConversionSessionScreenModel(FakeConversionExecutor(preview_result=preview))

    screen.load_session(session)
    state = screen.clear_session_override("subject.subject_id")

    assert state.session is not None
    assert state.session.metadata_overrides == {}
    assert "Cleared session override" in (state.review_message or "")


def test_conversion_session_screen_model_can_apply_source_override() -> None:
    session = make_session()
    preview = make_preview(session)
    screen = ConversionSessionScreenModel(FakeConversionExecutor(preview_result=preview))

    screen.load_session(session)
    state = screen.apply_source_override("manifest", "subject.subject_id", "source-specific-mouse-01")

    assert state.session is not None
    assert state.session.source_metadata_overrides["manifest"]["subject.subject_id"] == "source-specific-mouse-01"
    assert state.preview is None
    assert "Applied source override" in (state.review_message or "")


def test_conversion_session_screen_model_can_clear_source_override() -> None:
    session = make_session()
    session = ConversionSession(
        session_id=session.session_id,
        pathway=session.pathway,
        status=session.status,
        sources=session.sources,
        source_metadata_overrides={"manifest": {"subject.subject_id": "source-specific-mouse-01"}},
    )
    preview = make_preview(session)
    screen = ConversionSessionScreenModel(FakeConversionExecutor(preview_result=preview))

    screen.load_session(session)
    state = screen.clear_source_override("manifest", "subject.subject_id")

    assert state.session is not None
    assert state.session.source_metadata_overrides == {}
    assert "Cleared source override" in (state.review_message or "")


def test_conversion_session_screen_model_can_clear_all_field_overrides() -> None:
    session = ConversionSession(
        session_id="session-ui-04",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=Path("C:/tmp/session_manifest.json"),
                source_type=SourceType.FILE,
                label="Structured session manifest",
                role="primary",
            ),
            SourceReference(
                source_id="custom",
                location=Path("C:/tmp/custom_session.json"),
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="supplemental",
            ),
        ),
        metadata_overrides={"subject.subject_id": "session-value"},
        source_metadata_overrides={"custom": {"subject.subject_id": "source-value"}},
    )
    preview = make_preview(session)
    screen = ConversionSessionScreenModel(FakeConversionExecutor(preview_result=preview))

    screen.load_session(session)
    state = screen.clear_all_field_overrides("subject.subject_id")

    assert state.session is not None
    assert state.session.metadata_overrides == {}
    assert state.session.source_metadata_overrides == {}
    assert "Cleared all overrides" in (state.review_message or "")


def test_conversion_session_screen_model_surfaces_runtime_errors() -> None:
    session = make_session()
    error = PipelineRuntimeError(
        stage=PipelineStage.FAILED,
        user_message="Preview generation failed.",
        session_id=session.session_id,
    )
    screen = ConversionSessionScreenModel(FakeConversionExecutor(preview_result=error))
    screen.load_session(session)

    future = screen.start_preview()

    with pytest.raises(PipelineRuntimeError, match="Preview generation failed"):
        future.result(timeout=5)

    assert screen.state.error_message == "Preview generation failed."
    assert screen.state.user_error is not None
    assert screen.state.user_error.category == "conversion"
    assert screen.state.is_preview_running is False


def test_conversion_session_screen_model_submits_review(tmp_path: Path) -> None:
    session = make_session()
    preview = make_preview(session)
    issue = ValidationIssue(
        code="nwbinspector-warning",
        message="Subject metadata should be reviewed.",
        severity=IssueSeverity.WARNING,
        location="/general/subject",
        tool="nwbinspector",
    )
    execution = make_execution(
        preview,
        issues=(issue,),
        review_outcome=ValidationReviewOutcome(
            status=ValidationReviewStatus.REVIEW,
            blocks_completion=False,
            requires_manual_review=True,
            error_count=0,
            warning_count=1,
        ),
    )
    screen = ConversionSessionScreenModel(
        FakeConversionExecutor(preview_result=preview, execution_result=execution),
        review_service=ExecutionReviewService(JsonExecutionReviewArtifactService()),
    )
    screen.load_session(session)
    screen.start_preview().result(timeout=5)
    screen.start_execution(Path("C:/tmp/output.nwb")).result(timeout=5)

    assert len(screen.state.validation_issues) == 1
    screen.set_reviewer_name("alice")
    screen.set_issue_acknowledged(screen.state.validation_issues[0].issue_ref, True)
    submission = screen.submit_review(ReviewStatus.APPROVED)

    assert submission.review_record.decision == ReviewStatus.APPROVED
    assert screen.state.last_review_submission == submission
    assert "approved" in screen.state.review_message


def test_conversion_session_screen_model_persists_preview_execution_and_review() -> None:
    session = make_session()
    preview = make_preview(session)
    issue = ValidationIssue(
        code="nwbinspector-warning",
        message="Subject metadata should be reviewed.",
        severity=IssueSeverity.WARNING,
        location="/general/subject",
        tool="nwbinspector",
    )
    execution = make_execution(
        preview,
        issues=(issue,),
        review_outcome=ValidationReviewOutcome(
            status=ValidationReviewStatus.REVIEW,
            blocks_completion=False,
            requires_manual_review=True,
            error_count=0,
            warning_count=1,
        ),
    )

    with TemporaryDirectory() as temp_dir:
        persistence_service = SessionPersistenceService(
            JsonSessionSnapshotStore(Path(temp_dir) / "session-state")
        )
        screen = ConversionSessionScreenModel(
            FakeConversionExecutor(preview_result=preview, execution_result=execution),
            review_service=ExecutionReviewService(JsonExecutionReviewArtifactService()),
            persistence_service=persistence_service,
        )
        screen.load_session(session)
        screen.start_preview().result(timeout=5)

        preview_snapshot = persistence_service.load(preview.session.session_id)
        assert preview_snapshot is not None
        assert preview_snapshot.session == preview.session
        assert preview_snapshot.validation_summary is None

        screen.start_execution(Path("C:/tmp/output.nwb")).result(timeout=5)
        execution_snapshot = persistence_service.load(execution.session.session_id)
        assert execution_snapshot is not None
        assert execution_snapshot.validation_summary == execution.validation_summary

        screen.set_reviewer_name("alice")
        screen.set_issue_acknowledged(screen.state.validation_issues[0].issue_ref, True)
        screen.submit_review(ReviewStatus.APPROVED)

        review_snapshot = persistence_service.load(execution.session.session_id)
        assert review_snapshot is not None
        assert review_snapshot.review_record is not None
        assert review_snapshot.review_record.decision == ReviewStatus.APPROVED


def test_conversion_session_screen_model_recovers_latest_snapshot_on_load() -> None:
    session = make_session()
    preview = make_preview(session)
    issue = ValidationIssue(
        code="nwbinspector-warning",
        message="Subject metadata should be reviewed.",
        severity=IssueSeverity.WARNING,
        location="/general/subject",
        tool="nwbinspector",
    )
    report_artifact = ProvenanceArtifact(
        artifact_type="validation_report",
        location=Path("C:/tmp/validation-report.json"),
        description="Validation report artifact",
    )
    nwb_artifact = ProvenanceArtifact(
        artifact_type="nwb",
        location=Path("C:/tmp/recovered-output.nwb"),
        description="Recovered NWB output",
    )
    execution = make_execution(
        preview,
        issues=(issue,),
        generated_artifacts=(nwb_artifact, report_artifact),
        review_outcome=ValidationReviewOutcome(
            status=ValidationReviewStatus.REVIEW,
            blocks_completion=False,
            requires_manual_review=True,
            error_count=0,
            warning_count=1,
        ),
    )

    with TemporaryDirectory() as temp_dir:
        persistence_service = SessionPersistenceService(
            JsonSessionSnapshotStore(Path(temp_dir) / "session-state")
        )
        persistence_service.persist_execution(execution)
        review_service = ExecutionReviewService(JsonExecutionReviewArtifactService())
        review_submission = review_service.submit_review(
            execution,
            reviewer="alice",
            decision=ReviewStatus.APPROVED,
            acknowledged_issue_refs=(execution.validation_summary.issue_refs()[0],),
        )
        persistence_service.persist_review_submission(review_submission)

        screen = ConversionSessionScreenModel(
            FakeConversionExecutor(preview_result=preview, execution_result=execution),
            review_service=review_service,
            persistence_service=persistence_service,
        )

        state = screen.load_session(session)

        assert state.session is not None
        assert state.session.status == execution.session.status
        assert state.recovery_message == "Recovered latest saved session state."
        assert state.output_path == Path("C:/tmp/recovered-output.nwb")
        assert len(state.generated_artifacts) == 3
        assert {artifact.artifact_type for artifact in state.generated_artifacts} == {
            "nwb",
            "validation_report",
            "review_decision",
        }
        assert state.persisted_validation_summary == execution.validation_summary
        assert state.persisted_review_outcome == execution.review_outcome
        assert len(state.validation_issues) == 1
        assert state.validation_issues[0].is_acknowledged is True
        assert state.reviewer_name == "alice"
        assert "Recovered review approved by alice." == state.review_message
        assert len(state.snapshot_history) >= 2


def test_conversion_session_screen_model_can_restore_selected_snapshot() -> None:
    session = make_session()
    preview = make_preview(session)
    execution = make_execution(preview)

    with TemporaryDirectory() as temp_dir:
        persistence_service = SessionPersistenceService(
            JsonSessionSnapshotStore(Path(temp_dir) / "session-state", history_limit=5)
        )
        persistence_service.persist_preview(preview)
        persistence_service.persist_execution(execution)
        screen = ConversionSessionScreenModel(
            FakeConversionExecutor(preview_result=preview, execution_result=execution),
            persistence_service=persistence_service,
        )

        state = screen.load_session(session)
        preview_snapshot_id = state.snapshot_history[-1].snapshot_id
        restored = screen.restore_snapshot(preview_snapshot_id)

        assert restored.execution is None
        assert restored.persisted_validation_summary is None
        assert "Restored snapshot" in (restored.recovery_message or "")


def test_conversion_session_screen_model_can_disable_snapshot_recovery_on_load() -> None:
    session = make_session()
    preview = make_preview(session)

    with TemporaryDirectory() as temp_dir:
        persistence_service = SessionPersistenceService(
            JsonSessionSnapshotStore(Path(temp_dir) / "session-state")
        )
        persistence_service.persist_preview(preview)
        screen = ConversionSessionScreenModel(
            FakeConversionExecutor(preview_result=preview),
            persistence_service=persistence_service,
            restore_latest_snapshot_on_load=False,
        )

        state = screen.load_session(session)

        assert state.preview is None
        assert state.generated_artifacts == ()
        assert state.recovery_message == "Saved snapshot recovery is disabled in settings."
