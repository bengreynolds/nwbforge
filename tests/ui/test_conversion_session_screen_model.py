from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path

import pytest

from nwbforge.app.runtime import PipelineProgressEvent, PipelineRuntimeError, PipelineStage
from nwbforge.app.services import ExecutionReviewService
from nwbforge.app.services.models import ConversionExecution, ConversionPreview
from nwbforge.domain.enums import ConversionPathway, IssueSeverity, ReviewStatus, SessionStatus, SourceType, ValidationReviewStatus
from nwbforge.domain.models import (
    ConversionSession,
    ExecutionReviewRecord,
    ExtractedField,
    ExtractionResult,
    MappingPlan,
    NormalizedMetadataBundle,
    ProvenanceArtifact,
    ProvenanceRecord,
    SourceReference,
    ValidationIssue,
    ValidationReviewOutcome,
    ValidationSummary,
)
from nwbforge.validation import JsonExecutionReviewArtifactService
from nwbforge.ui import ConversionSessionScreenModel


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


def make_preview(session: ConversionSession) -> ConversionPreview:
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
        extraction_results=(extraction_result,),
        normalized_metadata=NormalizedMetadataBundle(),
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
