from __future__ import annotations

import json
import logging
from pathlib import Path
from subprocess import CompletedProcess

from PySide6.QtCore import Qt

from nwbforge.app.packages import PackageInstallationService, PackageManagementService
from nwbforge.app.runtime import PipelineProgressEvent, PipelineRuntimeError, PipelineStage, ThreadedPackageInstallationExecutor
from nwbforge.app.services import ExecutionReviewService, PackageManagementController, UiSettingsService
from nwbforge.domain.enums import ConversionPathway, IssueSeverity, SessionStatus, SourceType, ValidationReviewStatus
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
from nwbforge.app.services.models import ConversionExecution, ConversionPreview
from nwbforge.ui import DesktopShellModel, PackageInstallerScreenModel, SettingsScreenModel
from nwbforge.ui.conversion_session import ConversionSessionScreenModel
from nwbforge.ui.qt import MainWindow
from nwbforge.validation import JsonExecutionReviewArtifactService


class FakeRunner:
    def run(self, command, *, cwd: Path):
        return CompletedProcess(args=list(command), returncode=0, stdout="ok", stderr="")


class FakeConversionExecutor:
    def __init__(self, preview_result: ConversionPreview, execution_result: ConversionExecution) -> None:
        self._preview_result = preview_result
        self._execution_result = execution_result

    def submit_preview(self, session, *, progress_callback=None):
        from concurrent.futures import Future

        future: Future[ConversionPreview] = Future()
        if progress_callback is not None:
            progress_callback(
                PipelineProgressEvent(
                    session_id=session.session_id,
                    stage=PipelineStage.READY_TO_WRITE,
                    percent_complete=100,
                    message="Preview ready to write.",
                )
            )
        future.set_result(self._preview_result)
        return future

    def submit_execute(self, preview, output_path: Path, *, progress_callback=None):
        from concurrent.futures import Future

        future: Future[ConversionExecution] = Future()
        if progress_callback is not None:
            progress_callback(
                PipelineProgressEvent(
                    session_id=preview.session.session_id,
                    stage=PipelineStage.COMPLETED,
                    percent_complete=100,
                    message="Conversion completed successfully.",
                )
            )
        future.set_result(self._execution_result)
        return future


def make_package_screen(tmp_path: Path) -> PackageInstallerScreenModel:
    package_service = PackageManagementService(selection_path=tmp_path / "selection.json")
    installation_service = PackageInstallationService(
        package_service,
        repo_root=tmp_path,
        command_runner=FakeRunner(),
    )
    executor = ThreadedPackageInstallationExecutor(installation_service)
    controller = PackageManagementController(package_service, executor)
    return PackageInstallerScreenModel(controller)


def make_settings_screen(tmp_path: Path) -> SettingsScreenModel:
    return SettingsScreenModel(UiSettingsService(tmp_path / "ui-settings.json"))


def make_session(tmp_path: Path) -> ConversionSession:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "sess-qt"}}), encoding="utf-8")
    return ConversionSession(
        session_id="sess-qt",
        pathway=ConversionPathway.SUPPORTED,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=manifest_path,
                source_type=SourceType.FILE,
                label="Structured session manifest",
            ),
        ),
    )


def make_preview_and_execution(
    session: ConversionSession,
    *,
    validation_summary: ValidationSummary | None = None,
    review_outcome: ValidationReviewOutcome | None = None,
    generated_artifacts: tuple[ProvenanceArtifact, ...] = (),
) -> tuple[ConversionPreview, ConversionExecution]:
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
    execution = ConversionExecution(
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
        validation_summary=validation_summary or ValidationSummary(),
        review_outcome=review_outcome
        or ValidationReviewOutcome(
            status=ValidationReviewStatus.PASS,
            blocks_completion=False,
            requires_manual_review=False,
            error_count=0,
            warning_count=0,
        ),
    )
    return preview, execution


def test_main_window_file_menu_and_log_dock(qapp, tmp_path: Path) -> None:
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    log_file_path = tmp_path / "ui.log.jsonl"
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
        log_file_path=log_file_path,
    )
    window.show()
    qapp.processEvents()

    file_actions = window.file_menu.actions()
    labels = [action.text() for action in file_actions]
    assert "Install Extensions / Packages" in labels

    window._toggle_log_viewer_action.trigger()
    qapp.processEvents()
    assert window.log_dock.isVisible() is True

    logger = logging.getLogger("nwbforge.tests.qt")
    logger.info("Widget log message", extra={"nwbforge_context": {"session_id": "sess-qt"}})
    qapp.processEvents()
    assert "Widget log message" in window.log_dock.editor.toPlainText()
    assert log_file_path.exists()
    assert "Widget log message" in log_file_path.read_text(encoding="utf-8")

    window._install_packages_action.trigger()
    qapp.processEvents()
    assert window.package_dialog.isVisible() is True

    window.close()


def test_conversion_widget_and_package_dialog_bind_models(qapp, tmp_path: Path) -> None:
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    package_screen = make_package_screen(tmp_path)
    settings_screen = make_settings_screen(tmp_path)
    conversion_screen = ConversionSessionScreenModel(FakeConversionExecutor(preview, execution))
    window = MainWindow(DesktopShellModel(), settings_screen, package_screen, conversion_screen)
    window.show()
    qapp.processEvents()

    window.conversion_widget.load_session(session)
    qapp.processEvents()
    assert "sess-qt" in window.conversion_widget._session_label.text()

    window.conversion_widget._preview_button.click()
    qapp.processEvents()
    assert window.conversion_widget._result_label.text() == "Preview status: ready_to_write"
    assert window.statusBar().findChild(type(window._progress_bar)) is not None

    window.conversion_widget._output_path_edit.setText("C:/tmp/output.nwb")
    window.conversion_widget._execute_button.click()
    qapp.processEvents()
    assert window.conversion_widget._result_label.text() == "Execution status: completed"
    assert window.conversion_widget._artifact_list.count() == 0

    window.package_dialog.show()
    qapp.processEvents()
    assert window.package_dialog._route_list.count() > 0
    assert window.package_dialog._install_button.isEnabled() is True

    window.close()


def test_main_window_shows_user_error_dialog(qapp, tmp_path: Path, monkeypatch) -> None:
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    shell = DesktopShellModel()
    shown = {}

    def fake_open(message_box) -> None:
        shown["title"] = message_box.windowTitle()
        shown["text"] = message_box.text()
        shown["detail"] = message_box.detailedText()

    monkeypatch.setattr("nwbforge.ui.qt.main_window.QMessageBox.open", fake_open)

    window = MainWindow(
        shell,
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
    )
    window.show()
    qapp.processEvents()

    shell.apply_pipeline_error(
        PipelineRuntimeError(
            stage=PipelineStage.FAILED,
            user_message="Conversion failed.",
            detail="Missing session metadata.",
            session_id=session.session_id,
        )
    )
    qapp.processEvents()

    assert shown == {
        "title": "Conversion Error",
        "text": "Conversion failed.",
        "detail": "Missing session metadata.",
    }

    window.close()


def test_settings_dialog_updates_runtime_logging_preferences(qapp, tmp_path: Path) -> None:
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    shell = DesktopShellModel()
    settings_screen = make_settings_screen(tmp_path)
    window = MainWindow(
        shell,
        settings_screen,
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
    )
    window.show()
    qapp.processEvents()

    window._settings_action.trigger()
    qapp.processEvents()
    assert window.settings_dialog.isVisible() is True

    settings_dialog = window.settings_dialog
    settings_dialog._verbose_checkbox.setChecked(True)
    settings_dialog._file_logging_checkbox.setChecked(True)
    settings_dialog._log_path_edit.setText(str(tmp_path / "logs" / "runtime.jsonl"))
    settings_dialog._save_button.click()
    qapp.processEvents()

    assert shell.state.verbose_logging_enabled is True
    assert logging.getLogger("nwbforge").level == logging.DEBUG

    logger = logging.getLogger("nwbforge.tests.qt.settings")
    logger.info("Settings dialog log entry", extra={"nwbforge_context": {"dialog": "settings"}})
    qapp.processEvents()
    assert "Settings dialog log entry" in window.log_dock.editor.toPlainText()
    assert (tmp_path / "logs" / "runtime.jsonl").exists()

    window.close()


def test_conversion_widget_submits_review(qapp, tmp_path: Path) -> None:
    session = make_session(tmp_path)
    issue = ValidationIssue(
        code="nwbinspector-warning",
        message="Review the subject metadata.",
        severity=IssueSeverity.WARNING,
        location="/general/subject",
        tool="nwbinspector",
    )
    preview, execution = make_preview_and_execution(
        session,
        validation_summary=ValidationSummary(issues=(issue,)),
        review_outcome=ValidationReviewOutcome(
            status=ValidationReviewStatus.REVIEW,
            blocks_completion=False,
            requires_manual_review=True,
            error_count=0,
            warning_count=1,
        ),
    )
    conversion_screen = ConversionSessionScreenModel(
        FakeConversionExecutor(preview, execution),
        review_service=ExecutionReviewService(JsonExecutionReviewArtifactService()),
    )
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        conversion_screen,
    )
    window.show()
    qapp.processEvents()

    window.conversion_widget.load_session(session)
    window.conversion_widget._preview_button.click()
    qapp.processEvents()
    window.conversion_widget._output_path_edit.setText("C:/tmp/output.nwb")
    window.conversion_widget._execute_button.click()
    qapp.processEvents()

    assert window.conversion_widget._issue_list.count() == 1
    window.conversion_widget._reviewer_edit.setText("alice")
    issue_item = window.conversion_widget._issue_list.item(0)
    issue_item.setCheckState(Qt.CheckState.Checked)
    qapp.processEvents()
    window.conversion_widget._approve_button.click()
    qapp.processEvents()

    assert "approved" in window.conversion_widget._review_status_label.text()
    window.close()


def test_main_window_opens_manifest_session_from_file_menu(qapp, tmp_path: Path, monkeypatch) -> None:
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
    )
    window.show()
    qapp.processEvents()

    monkeypatch.setattr(
        "nwbforge.ui.qt.main_window.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(session.sources[0].location), "session_manifest.json"),
    )

    window._open_session_action.trigger()
    qapp.processEvents()

    assert "desktop-" in window.conversion_widget._session_label.text()
    window.close()


def test_conversion_widget_lists_generated_artifacts(qapp, tmp_path: Path) -> None:
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(
        session,
        generated_artifacts=(
            ProvenanceArtifact(
                artifact_type="validation_report",
                location=tmp_path / "validation-report.json",
                description="Validation report artifact",
            ),
        ),
    )
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
    )
    window.show()
    qapp.processEvents()

    window.conversion_widget.load_session(session)
    window.conversion_widget._preview_button.click()
    qapp.processEvents()
    window.conversion_widget._output_path_edit.setText("C:/tmp/output.nwb")
    window.conversion_widget._execute_button.click()
    qapp.processEvents()

    assert window.conversion_widget._artifact_list.count() == 1
    assert "validation-report.json" in window.conversion_widget._artifact_list.item(0).text()
    window.close()
