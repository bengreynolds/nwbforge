"""Temporary desktop launcher for manual NWB Forge UI testing."""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
from subprocess import CompletedProcess
import json
import logging

from nwbforge.app.packages import PackageInstallationService, PackageManagementService
from nwbforge.app.runtime import PipelineProgressEvent, PipelineStage, ThreadedPackageInstallationExecutor
from nwbforge.app.services import ExecutionReviewService, PackageManagementController, UiSettingsService
from nwbforge.app.services.models import ConversionExecution, ConversionPreview
from nwbforge.domain.enums import (
    ConversionPathway,
    IssueSeverity,
    SessionStatus,
    SourceType,
    ValidationReviewStatus,
)
from nwbforge.domain.models import (
    ConversionSession,
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
from nwbforge.ui import ConversionSessionScreenModel, DesktopShellModel, PackageInstallerScreenModel, SettingsScreenModel
from nwbforge.ui.qt import MainWindow, ensure_application
from nwbforge.validation import JsonExecutionReviewArtifactService


class DemoPackageRunner:
    """No-op package runner for UI testing."""

    def run(self, command, *, cwd: Path):
        logging.getLogger("nwbforge.demo").info(
            "Demo package install requested.",
            extra={"nwbforge_context": {"command": list(command), "cwd": str(cwd)}},
        )
        return CompletedProcess(args=list(command), returncode=0, stdout="demo install completed", stderr="")


class DemoConversionExecutor:
    """Immediate conversion executor for manual UI testing."""

    def __init__(self, preview_result: ConversionPreview, execution_result: ConversionExecution) -> None:
        self._preview_result = preview_result
        self._execution_result = execution_result

    def submit_preview(self, session, *, progress_callback=None):
        future: Future[ConversionPreview] = Future()
        if progress_callback is not None:
            progress_callback(
                PipelineProgressEvent(
                    session_id=session.session_id,
                    stage=PipelineStage.INSPECTING,
                    percent_complete=15,
                    message="Inspecting demo sources.",
                )
            )
            progress_callback(
                PipelineProgressEvent(
                    session_id=session.session_id,
                    stage=PipelineStage.READY_TO_WRITE,
                    percent_complete=100,
                    message="Preview ready.",
                )
            )
        future.set_result(self._preview_result)
        return future

    def submit_execute(self, preview, output_path: Path, *, progress_callback=None):
        future: Future[ConversionExecution] = Future()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("Temporary UI-test artifact", encoding="utf-8")
        updated_execution = ConversionExecution(
            preview=self._execution_result.preview,
            session=self._execution_result.session,
            output_artifacts=(
                ProvenanceArtifact(
                    artifact_type="nwb",
                    location=output_path,
                    description="Temporary UI-test NWB artifact placeholder.",
                ),
            ),
            provenance_record=self._execution_result.provenance_record,
            validation_summary=self._execution_result.validation_summary,
            review_outcome=self._execution_result.review_outcome,
        )
        if progress_callback is not None:
            progress_callback(
                PipelineProgressEvent(
                    session_id=preview.session.session_id,
                    stage=PipelineStage.WRITING,
                    percent_complete=60,
                    message="Writing demo output.",
                )
            )
            progress_callback(
                PipelineProgressEvent(
                    session_id=preview.session.session_id,
                    stage=PipelineStage.COMPLETED,
                    percent_complete=100,
                    message="Demo conversion completed.",
                )
            )
        future.set_result(updated_execution)
        return future


def build_demo_session(workdir: Path) -> ConversionSession:
    demo_dir = workdir / ".nwbforge" / "demo-data"
    demo_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = demo_dir / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "demo-session-001",
                    "session_description": "Temporary desktop UI test session.",
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return ConversionSession(
        session_id="demo-session-001",
        pathway=ConversionPathway.SUPPORTED,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=manifest_path,
                source_type=SourceType.FILE,
                label="Demo session manifest",
            ),
        ),
    )


def build_demo_preview_and_execution(session: ConversionSession, workdir: Path) -> tuple[ConversionPreview, ConversionExecution]:
    preview = ConversionPreview(
        session=session.transition(SessionStatus.READY_TO_WRITE),
        extraction_results=(
            ExtractionResult(
                source_id="manifest",
                adapter_id="session_manifest",
                record_type="session_manifest",
                fields={
                    "session.session_id": ExtractedField(
                        key="session.session_id",
                        value=session.session_id,
                        source_id="manifest",
                    )
                },
            ),
        ),
        normalized_metadata=NormalizedMetadataBundle(),
        mapping_plan=MappingPlan(pathway=session.pathway),
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
        ),
    )
    validation_issue = ValidationIssue(
        code="demo-review-warning",
        message="Review the temporary demo metadata before approval.",
        severity=IssueSeverity.WARNING,
        location="/general/subject",
        tool="demo",
    )
    output_path = workdir / ".nwbforge" / "demo-data" / "demo-output.nwb"
    execution = ConversionExecution(
        preview=preview,
        session=preview.session.transition(SessionStatus.COMPLETED),
        output_artifacts=(
            ProvenanceArtifact(
                artifact_type="nwb",
                location=output_path,
                description="Temporary demo output.",
            ),
        ),
        provenance_record=preview.provenance_record,
        validation_summary=ValidationSummary(issues=(validation_issue,)),
        review_outcome=ValidationReviewOutcome(
            status=ValidationReviewStatus.REVIEW,
            blocks_completion=False,
            requires_manual_review=True,
            error_count=0,
            warning_count=1,
        ),
    )
    return preview, execution


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    app_state_dir = repo_root / ".nwbforge"
    app_state_dir.mkdir(parents=True, exist_ok=True)

    settings_service = UiSettingsService(app_state_dir / "ui-settings.json")
    settings_screen = SettingsScreenModel(settings_service)

    package_service = PackageManagementService(selection_path=app_state_dir / "install-selection.json")
    installation_service = PackageInstallationService(
        package_service,
        repo_root=repo_root,
        command_runner=DemoPackageRunner(),
    )
    package_executor = ThreadedPackageInstallationExecutor(installation_service)
    package_controller = PackageManagementController(package_service, package_executor)
    package_screen = PackageInstallerScreenModel(package_controller)

    session = build_demo_session(repo_root)
    preview, execution = build_demo_preview_and_execution(session, repo_root)
    conversion_screen = ConversionSessionScreenModel(
        DemoConversionExecutor(preview, execution),
        review_service=ExecutionReviewService(JsonExecutionReviewArtifactService()),
    )

    shell = DesktopShellModel()
    app = ensure_application()
    window = MainWindow(
        shell,
        settings_screen,
        package_screen,
        conversion_screen,
        log_file_path=app_state_dir / "logs" / "desktop-ui.jsonl",
    )
    window.show()
    window.conversion_widget.load_session(session)
    logging.getLogger("nwbforge.demo").info(
        "Temporary desktop UI launcher started.",
        extra={"nwbforge_context": {"session_id": session.session_id}},
    )
    try:
        return app.exec()
    finally:
        conversion_screen.shutdown(wait=False)
        package_screen.shutdown(wait=False)


if __name__ == "__main__":
    raise SystemExit(main())
