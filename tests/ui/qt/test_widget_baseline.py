from __future__ import annotations

from dataclasses import replace
import json
import logging
from pathlib import Path
from subprocess import CompletedProcess

from PySide6.QtCore import Qt
import nwbforge.ui.qt.main_window as main_window_module

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.registry import AdapterRegistry
from nwbforge.app.packages import InstallMode, InstallPreset, PackageInstallationService, PackageManagementService
from nwbforge.app.desktop import build_adapter_registry
from nwbforge.app.runtime import PipelineProgressEvent, PipelineRuntimeError, PipelineStage, ThreadedPackageInstallationExecutor
from nwbforge.app.services import (
    ExecutionReviewService,
    JsonSessionAssemblyWorkspaceStore,
    PackageManagementController,
    SessionAssemblyService,
    SessionPersistenceService,
    UiSettingsService,
)
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
    ExtractedField,
    ExtractionResult,
    MappingPlan,
    NormalizedSubject,
    NormalizedSessionMetadata,
    NormalizedMetadataBundle,
    NormalizedValue,
    ProvenanceArtifact,
    ProvenanceRecord,
    SourceReference,
    ValidationIssue,
    ValidationReviewOutcome,
    ValidationSummary,
)
from nwbforge.app.services.models import ConversionExecution, ConversionPreview
from nwbforge.ui import DesktopShellModel, PackageInstallerScreenModel, SessionAssemblyScreenModel, SettingsScreenModel
from nwbforge.ui.conversion_session import ConversionSessionScreenModel
from nwbforge.ui.models import MetadataDisagreementItem, MetadataDisagreementSourceItem
from nwbforge.ui.qt import MainWindow
from nwbforge.ui.qt.session_assembly_dialog import SessionAssemblyDialog
from nwbforge.validation import JsonExecutionReviewArtifactService
from nwbforge.persistence import JsonSessionSnapshotStore


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


class _WorkflowRouteAdapter:
    version = "0.0.0"
    capabilities = AdapterCapabilities(supported_pathways=(ConversionPathway.SUPPORTED,))

    def __init__(self, adapter_id: str, *, source_type: SourceType) -> None:
        self.adapter_id = adapter_id
        self.display_name = adapter_id
        self.source_types = (source_type,)

    def can_handle(self, source: SourceReference) -> bool:
        return source.adapter_hint == self.adapter_id

    def inspect(self, source: SourceReference):  # pragma: no cover - not used in this test
        raise NotImplementedError


class _TiffSuite2pWorkflowAdapter:
    adapter_id = "workflow_tiff_suite2p"
    display_name = "TIFF + Suite2p Workflow"
    version = "0.0.0"
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )

    def can_handle_sources(self, sources: tuple[SourceReference, ...]) -> bool:
        return self.match_sources(sources) is not None

    def inspect_sources(self, sources: tuple[SourceReference, ...]):  # pragma: no cover - not used in this test
        raise NotImplementedError

    def match_sources(self, sources: tuple[SourceReference, ...]) -> dict[str, SourceReference] | None:
        imaging = [
            source
            for source in sources
            if source.adapter_hint == "neuroconv_tiff_imaging" and source.role == "primary"
        ]
        segmentation = [
            source
            for source in sources
            if source.adapter_hint == "neuroconv_suite2p_segmentation"
        ]
        if len(imaging) != 1 or len(segmentation) != 1:
            return None
        return {"imaging": imaging[0], "segmentation": segmentation[0]}


def _build_workflow_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(_WorkflowRouteAdapter("neuroconv_tiff_imaging", source_type=SourceType.DIRECTORY))
    registry.register(_WorkflowRouteAdapter("neuroconv_suite2p_segmentation", source_type=SourceType.DIRECTORY))
    registry.register_workflow(_TiffSuite2pWorkflowAdapter())
    return registry


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
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
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


def make_custom_session(tmp_path: Path) -> ConversionSession:
    custom_path = tmp_path / "custom_session.json"
    custom_path.parent.mkdir(parents=True, exist_ok=True)
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-qt"}}), encoding="utf-8")
    return ConversionSession(
        session_id="custom-qt",
        pathway=ConversionPathway.CUSTOM,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="custom",
                location=custom_path,
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="primary",
                adapter_hint="custom_json_session",
            ),
        ),
    )


def make_hybrid_session(tmp_path: Path) -> ConversionSession:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"session": {"session_id": "hybrid-qt"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"signal_sets": []}), encoding="utf-8")
    return ConversionSession(
        session_id="hybrid-qt",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=manifest_path,
                source_type=SourceType.FILE,
                label="Structured session manifest",
            ),
            SourceReference(
                source_id="custom",
                location=custom_path,
                source_type=SourceType.FILE,
                label="Custom supplemental source",
                role="supplemental",
                adapter_hint="custom_json_session",
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
    assert "New Session" in labels
    assert "Import / Compatibility" in labels
    assert "Optional Workflow Support" in labels
    compatibility_labels = [action.text() for action in window._import_compatibility_menu.actions()]
    assert "Import Session JSON (Compatibility)..." in compatibility_labels
    assert "Reopen Last Imported Session" in compatibility_labels
    assert window._recent_sessions_menu.title() == "Open Recent Imported Session"
    assert window.workspace_tabs.currentWidget() is window.session_assembly_dialog
    assert window.workspace_tabs.tabText(0) == "New Session"
    assert window.workspace_tabs.tabText(1) == "Conversion"
    assert window.workspace_tabs.isTabVisible(2) is False
    assert window._workspace_title_label.text() == "New Conversion Session"
    assert "Add files or folders" in window._workspace_subtitle_label.text()

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
    assert window.workspace_tabs.currentWidget() is window.package_dialog
    assert window.workspace_tabs.isTabVisible(window.workspace_tabs.indexOf(window.package_dialog)) is True

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
    window.workspace_tabs.setCurrentWidget(window.conversion_widget)
    qapp.processEvents()
    assert window._workspace_title_label.text() == "sess-qt"
    assert "Supported pathway" in window._workspace_subtitle_label.text()
    assert "sess-qt" in window.conversion_widget._session_label.text()
    assert window.conversion_widget._session_summary_group.title() == "Session Overview"
    assert window.conversion_widget._source_detail_group.title() == "Selected Data Source"
    assert window.conversion_widget._execution_group.title() == "Execution Status"
    assert window.conversion_widget._review_group.title() == "Quality Check and Review"
    assert window.conversion_widget._artifact_group.title() == "Generated Artifacts"
    assert window.conversion_widget._stage_value_label.text() == "sources_added"
    assert window.conversion_widget._pathway_label.text() == "supported"
    assert window.conversion_widget._source_count_label.text() == "1"
    assert window.conversion_widget._source_role_label.text() == "primary"
    assert window.conversion_widget._source_adapter_label.text() == "Auto-detect"
    assert window.conversion_widget._review_guidance_label.text() == "Run preview or execution to unlock review guidance."
    assert window.conversion_widget._workflow_steps_label.text().startswith("Workflow:")
    assert window.conversion_widget._session_details_toggle.isChecked() is False
    assert window.conversion_widget._session_summary_group.isHidden() is True
    assert window.conversion_widget._output_path_edit.isVisible() is True
    assert "sess-qt | supported workflow | 1 data source" in window.conversion_widget._session_context_label.text()
    assert window.conversion_widget._advanced_toggle.isChecked() is False
    assert window.conversion_widget._advanced_resolution_group.isHidden() is True
    assert window.conversion_widget._workspace_tabs.isTabVisible(4) is False
    assert window.conversion_widget._workspace_tabs.isTabVisible(5) is False
    assert window.conversion_widget._readiness_metric_value.text() == "Blocked"
    assert "blocked by build preview" in window.conversion_widget._readiness_summary_label.text().lower()
    assert "Build Preview" in window.conversion_widget._next_action_label.text()
    assert "build preview" in window.conversion_widget._ready_to_write_label.text()
    assert "Session loaded: done" in window.conversion_widget._pre_write_checklist_label.text()
    assert "Preview built: pending" in window.conversion_widget._pre_write_checklist_label.text()
    assert "Metadata review: waiting for preview" in window.conversion_widget._pre_write_checklist_label.text()
    assert "Output path chosen: pending" in window.conversion_widget._pre_write_checklist_label.text()
    assert (
        window.conversion_widget._role_policy_label.text()
        == "Data source priority during conflict review: primary sources take precedence over metadata sources, which take precedence over supplemental sources."
    )
    assert window.conversion_widget._workspace_tabs.count() == 6
    assert window.conversion_widget._workspace_tabs.tabText(0) == "1. Run Overview"
    assert window.conversion_widget._workspace_tabs.tabText(1) == "2. Metadata Review"
    assert window.conversion_widget._workspace_tabs.tabText(2) == "3. Quality Review"
    assert window.conversion_widget._workspace_tabs.tabText(3) == "4. Artifacts"
    assert window.conversion_widget._workspace_tabs.tabText(4) == "History"
    assert window.conversion_widget._workspace_tabs.tabText(5) == "Diagnostics"
    assert window.conversion_widget._workspace_tabs.currentIndex() == 0
    assert window.conversion_widget._pathway_metric_value.text() == "supported"
    assert window.conversion_widget._stage_metric_value.text() == "sources added"
    assert window._close_current_session_action.isEnabled() is False

    window.conversion_widget._workspace_tabs.setCurrentIndex(2)
    qapp.processEvents()
    assert window.conversion_widget._reviewer_edit.isVisible() is True
    assert window.conversion_widget._validation_summary_label.isVisible() is True
    assert window.conversion_widget._review_outcome_label.isVisible() is True
    assert window.conversion_widget._review_status_label.isVisible() is True
    assert "Conversion results available: pending" in window.conversion_widget._review_checklist_label.text()
    window.conversion_widget._workspace_tabs.setCurrentIndex(0)
    qapp.processEvents()

    window.conversion_widget._session_details_toggle.setChecked(True)
    qapp.processEvents()
    assert window.conversion_widget._session_summary_group.isHidden() is False

    window.conversion_widget._advanced_toggle.setChecked(True)
    qapp.processEvents()
    assert window.conversion_widget._advanced_resolution_group.isHidden() is False
    assert window.conversion_widget._workspace_tabs.isTabVisible(4) is True
    assert window.conversion_widget._workspace_tabs.isTabVisible(5) is True

    window.conversion_widget._preview_button.click()
    qapp.processEvents()
    assert window.conversion_widget._result_label.text() == "Preview status: ready_to_write"
    assert window.conversion_widget._stage_value_label.text() == "ready_to_write"
    assert "Choose Output" in window.conversion_widget._next_action_label.text()
    assert "choose output path" in window.conversion_widget._ready_to_write_label.text()
    assert window.conversion_widget._workspace_tabs.currentIndex() == 0
    assert window.statusBar().findChild(type(window._progress_bar)) is not None
    assert window.conversion_widget._readiness_metric_value.text() == "Blocked"
    assert "blocked by choose output path" in window.conversion_widget._readiness_summary_label.text().lower()
    assert "Preview built: done" in window.conversion_widget._pre_write_checklist_label.text()
    assert "Metadata review: done" in window.conversion_widget._pre_write_checklist_label.text()
    assert "Output path chosen: pending" in window.conversion_widget._pre_write_checklist_label.text()
    window.conversion_widget._advanced_toggle.setChecked(True)
    qapp.processEvents()
    assert window.conversion_widget._progress_history_list.count() >= 1
    assert window.conversion_widget._progress_history_list.item(0).text().startswith("[Ready]")

    window.conversion_widget._output_path_edit.setText("C:/tmp/output.nwb")
    qapp.processEvents()
    assert window.conversion_widget._output_value_label.text() == "C:/tmp/output.nwb"
    assert window.conversion_widget._readiness_metric_value.text() == "Ready to Write"
    assert "ready to write" in window.conversion_widget._readiness_summary_label.text().lower()
    assert "Current step: Write NWB." in window.conversion_widget._next_action_label.text()
    assert "Output path chosen: done" in window.conversion_widget._pre_write_checklist_label.text()
    window.conversion_widget._execute_button.click()
    qapp.processEvents()
    assert window.conversion_widget._result_label.text() == "Execution status: completed"
    assert window.conversion_widget._artifact_list.count() == 0
    assert window.conversion_widget._artifact_count_value_label.text() == "0 artifacts"
    assert window.conversion_widget._readiness_metric_value.text() == "Completed"
    assert "output and generated artifacts are ready" in window.conversion_widget._readiness_summary_label.text().lower()
    assert "Conversion results available: done" in window.conversion_widget._review_checklist_label.text()
    assert "Decision recorded: not required" in window.conversion_widget._review_checklist_label.text()
    assert any(
        window.conversion_widget._progress_history_list.item(index).text().startswith("[Complete]")
        for index in range(window.conversion_widget._progress_history_list.count())
    )
    assert window.conversion_widget._workspace_tabs.currentIndex() == 0

    window._install_packages_action.trigger()
    qapp.processEvents()
    assert window.package_dialog._header_title_label.text() == "Optional Workflow Support"
    assert window.package_dialog._route_group.isHidden() is True
    assert window.package_dialog._route_list.count() > 0
    assert window.package_dialog._install_button.isEnabled() is True

    window.close()


def test_package_dialog_mode_and_preset_hooks_normalize_combo_values(qapp, tmp_path: Path) -> None:
    package_screen = make_package_screen(tmp_path)
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        package_screen,
        ConversionSessionScreenModel(FakeConversionExecutor(*make_preview_and_execution(make_session(tmp_path)))),
    )
    window.show()
    qapp.processEvents()

    window._install_packages_action.trigger()
    qapp.processEvents()

    full_index = window.package_dialog._mode_combo.findData(InstallMode.FULL.value)
    window.package_dialog._mode_combo.setCurrentIndex(full_index)
    qapp.processEvents()
    assert package_screen.state.install_mode is InstallMode.FULL
    assert package_screen.state.install_preset is InstallPreset.FULL

    selected_index = window.package_dialog._mode_combo.findData(InstallMode.SELECTED.value)
    custom_index = window.package_dialog._preset_combo.findData(InstallPreset.CUSTOM.value)
    window.package_dialog._mode_combo.setCurrentIndex(selected_index)
    window.package_dialog._preset_combo.setCurrentIndex(custom_index)
    qapp.processEvents()
    assert package_screen.state.install_mode is InstallMode.SELECTED
    assert package_screen.state.install_preset is InstallPreset.CUSTOM
    assert window.package_dialog._route_group.isHidden() is False
    assert window.package_dialog._route_list.isEnabled() is True

    first_item = window.package_dialog._route_list.item(0)
    first_item.setCheckState(Qt.CheckState.Checked)
    qapp.processEvents()
    assert first_item.data(Qt.ItemDataRole.UserRole) in package_screen.state.selected_routes

    window.package_dialog._install_button.click()
    qapp.processEvents()
    assert package_screen.state.progress_event is not None

    window.close()
    package_screen.shutdown()


def test_conversion_widget_uses_split_session_and_review_layout(qapp, tmp_path: Path) -> None:
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

    splitter = window.conversion_widget._splitter
    assert splitter.count() == 2
    assert splitter.widget(0) is window.conversion_widget._session_summary_group
    assert splitter.widget(1).layout().itemAt(0).widget() is window.conversion_widget._workspace_tabs
    assert window.conversion_widget._scroll_area.widgetResizable() is True
    assert window.conversion_widget._workspace_tabs.usesScrollButtons() is True
    assert splitter.childrenCollapsible() is True
    assert window.conversion_widget._session_summary_group.isHidden() is True

    window.conversion_widget._session_details_toggle.setChecked(True)
    qapp.processEvents()
    assert window.conversion_widget._session_summary_group.isHidden() is False

    window.conversion_widget._session_details_toggle.setChecked(False)
    qapp.processEvents()
    assert window.conversion_widget._session_summary_group.isHidden() is True

    window.close()


def test_embedded_workspace_panels_are_scrollable_and_keep_manual_tab_selection(qapp, tmp_path: Path) -> None:
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    shell = DesktopShellModel()
    window = MainWindow(
        shell,
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
    )
    window.show()
    qapp.processEvents()

    assert window.workspace_tabs.usesScrollButtons() is True
    assert window.package_dialog._scroll_area.widgetResizable() is True
    assert window.settings_dialog._scroll_area.widgetResizable() is True
    assert window.session_assembly_dialog._scroll_area.widgetResizable() is True
    assert window.session_assembly_dialog._workspace_tabs.usesScrollButtons() is True
    assert window.session_assembly_dialog._workspace_splitter.childrenCollapsible() is True

    window._install_packages_action.trigger()
    qapp.processEvents()
    window._toggle_log_viewer_action.trigger()
    qapp.processEvents()
    assert window.workspace_tabs.currentWidget() is window.package_dialog

    window.workspace_tabs.setCurrentWidget(window.settings_dialog)
    qapp.processEvents()
    shell.set_status_bar(main_window_module.StatusBarState(stage_key="ui:test", message="Settings still focused."))
    qapp.processEvents()
    assert window.workspace_tabs.currentWidget() is window.settings_dialog
    assert window.workspace_tabs.isTabVisible(window.workspace_tabs.indexOf(window.package_dialog)) is False

    window.settings_dialog.reject()
    qapp.processEvents()
    assert window.workspace_tabs.currentWidget() is window.session_assembly_dialog

    window.conversion_widget.load_session(session)
    window.workspace_tabs.setCurrentWidget(window.conversion_widget)
    qapp.processEvents()
    window.workspace_tabs.setCurrentWidget(window.settings_dialog)
    qapp.processEvents()
    window.settings_dialog.reject()
    qapp.processEvents()
    assert window.workspace_tabs.currentWidget() is window.conversion_widget

    window.close()


def test_conversion_widget_chooses_output_path(qapp, tmp_path: Path, monkeypatch) -> None:
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
        "nwbforge.ui.qt.main_window.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(tmp_path / "chosen-output.nwb"), "NWB files (*.nwb)"),
    )

    window.conversion_widget.load_session(session)
    window.conversion_widget._choose_output_button.click()
    qapp.processEvents()

    assert window.conversion_widget._output_path_edit.text().endswith("chosen-output.nwb")
    window.close()


def test_conversion_widget_preserves_selected_source_across_state_updates(qapp, tmp_path: Path) -> None:
    session = make_hybrid_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
    )
    window.show()
    qapp.processEvents()

    window.conversion_widget.load_session(session)
    qapp.processEvents()
    window.conversion_widget._source_list.setCurrentRow(1)
    qapp.processEvents()
    assert window.conversion_widget._source_role_label.text() == "supplemental"

    window.conversion_widget._preview_button.click()
    qapp.processEvents()

    assert window.conversion_widget._source_list.currentItem() is not None
    assert window.conversion_widget._source_list.currentItem().data(Qt.ItemDataRole.UserRole) == "custom"
    assert window.conversion_widget._source_role_label.text() == "supplemental"
    window.close()


def test_conversion_widget_shows_recovered_snapshot_state(qapp, tmp_path: Path) -> None:
    session = make_session(tmp_path)
    validation_summary = ValidationSummary(
        issues=(
            ValidationIssue(
                code="nwbinspector-warning",
                message="Subject metadata should be reviewed.",
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
    preview, execution = make_preview_and_execution(
        session,
        validation_summary=validation_summary,
        review_outcome=review_outcome,
        generated_artifacts=(
            ProvenanceArtifact(
                artifact_type="nwb",
                location=tmp_path / "outputs" / "recovered-output.nwb",
                description="Recovered NWB output",
            ),
            ProvenanceArtifact(
                artifact_type="validation_report",
                location=tmp_path / "outputs" / "validation-report.json",
                description="Recovered validation report",
            ),
        ),
    )
    persistence_service = SessionPersistenceService(JsonSessionSnapshotStore(tmp_path / "session-state"))
    persistence_service.persist_execution(execution)

    screen = ConversionSessionScreenModel(
        FakeConversionExecutor(preview, execution),
        persistence_service=persistence_service,
    )
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        screen,
    )
    window.show()
    qapp.processEvents()

    window.conversion_widget.load_session(session)
    qapp.processEvents()

    assert window.conversion_widget._status_label.text() == "Recovered latest saved session state."
    assert window.conversion_widget._result_label.text() == "Recovered session status: completed"
    assert window.conversion_widget._validation_summary_label.text() == "Validation summary: 0 errors, 1 warnings"
    assert "manual review=True" in window.conversion_widget._review_outcome_label.text()
    assert window.conversion_widget._artifact_count_value_label.text() == "2 artifacts"
    assert window.conversion_widget._output_path_edit.text().endswith("recovered-output.nwb")
    assert "Latest state: recovery" in window.conversion_widget._diagnostics_summary_label.text()
    assert "Recovered latest saved session state." in window.conversion_widget._diagnostics_summary_label.text()
    window.conversion_widget._advanced_toggle.setChecked(True)
    qapp.processEvents()
    assert window.conversion_widget._snapshot_history_list.count() >= 1
    assert "results state" in window.conversion_widget._snapshot_history_list.item(0).text()
    assert "pending review record" in window.conversion_widget._snapshot_history_list.item(0).text()
    assert "2 artifacts" in window.conversion_widget._selected_snapshot_summary_label.text()
    assert "1 issues" in window.conversion_widget._selected_snapshot_summary_label.text()
    assert "not reviewed" in window.conversion_widget._selected_snapshot_summary_label.text()
    assert "Restoring replaces the current session view with this saved state." in (
        window.conversion_widget._selected_snapshot_summary_label.text()
    )

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
    assert window.workspace_tabs.currentWidget() is window.settings_dialog

    settings_dialog = window.settings_dialog
    assert settings_dialog._header_title_label.text() == "Settings"
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
    assert "Manual review is required." in window.conversion_widget._review_guidance_label.text()
    assert window.conversion_widget._acknowledgement_summary_label.text() == "Acknowledged 0 of 1 issues."
    assert "Conversion results available: done" in window.conversion_widget._review_checklist_label.text()
    assert "Validation issues acknowledged: pending" in window.conversion_widget._review_checklist_label.text()
    assert "Reviewer recorded: pending" in window.conversion_widget._review_checklist_label.text()
    assert "Decision recorded: pending" in window.conversion_widget._review_checklist_label.text()
    assert window.conversion_widget._workspace_tabs.currentIndex() == 0
    window.conversion_widget._reviewer_edit.setText("alice")
    issue_item = window.conversion_widget._issue_list.item(0)
    issue_item.setCheckState(Qt.CheckState.Checked)
    qapp.processEvents()
    assert window.conversion_widget._acknowledgement_summary_label.text() == "Acknowledged 1 of 1 issues."
    assert "Validation issues acknowledged: done" in window.conversion_widget._review_checklist_label.text()
    assert "Reviewer recorded: done" in window.conversion_widget._review_checklist_label.text()
    window.conversion_widget._approve_button.click()
    qapp.processEvents()

    assert "approved" in window.conversion_widget._review_status_label.text()
    assert "Decision recorded: done" in window.conversion_widget._review_checklist_label.text()
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


def test_main_window_opens_custom_session_from_file_menu(qapp, tmp_path: Path, monkeypatch) -> None:
    session = make_custom_session(tmp_path)
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
        lambda *args, **kwargs: (str(session.sources[0].location), "custom_session.json"),
    )

    window._open_session_action.trigger()
    qapp.processEvents()

    assert "desktop-custom-" in window.conversion_widget._session_label.text()
    assert window.conversion_widget._pathway_label.text() == "custom"
    assert window.conversion_widget._source_adapter_label.text() == "custom_json_session"
    window.close()


def test_main_window_opens_hybrid_session_from_file_menu(qapp, tmp_path: Path, monkeypatch) -> None:
    session = make_hybrid_session(tmp_path)
    hybrid_path = tmp_path / "hybrid_session.json"
    hybrid_path.write_text(
        json.dumps(
            {
                "session_id": "desktop-hybrid-qt",
                "sources": [
                    {"source_id": "manifest", "location": "session_manifest.json", "label": "Structured session manifest"},
                    {
                        "source_id": "custom",
                        "location": "custom_session.json",
                        "label": "Custom supplemental source",
                        "adapter_hint": "custom_json_session",
                        "role": "supplemental",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
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
        lambda *args, **kwargs: (str(hybrid_path), "hybrid_session.json"),
    )

    window._open_session_action.trigger()
    qapp.processEvents()

    assert window.conversion_widget._pathway_label.text() == "hybrid"
    assert window.conversion_widget._source_count_label.text() == "2"
    assert "desktop-hybrid-qt" in window.conversion_widget._session_label.text()
    window.close()


def test_main_window_new_and_reopen_session_actions(qapp, tmp_path: Path, monkeypatch) -> None:
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    settings_screen = make_settings_screen(tmp_path)
    window = MainWindow(
        DesktopShellModel(),
        settings_screen,
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
    window._new_session_action.trigger()
    qapp.processEvents()
    assert window.workspace_tabs.currentWidget() is window.session_assembly_dialog
    assert "desktop-" in window.conversion_widget._session_label.text()
    window.session_assembly_dialog.reject()
    qapp.processEvents()
    assert window.workspace_tabs.currentWidget() is window.conversion_widget

    window._reopen_last_session_action.trigger()
    qapp.processEvents()
    assert "desktop-" in window.conversion_widget._session_label.text()
    window.close()


def test_main_window_builds_session_from_new_session_dialog(qapp, tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
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
        "nwbforge.ui.qt.session_assembly_dialog.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(manifest_path)], "All supported inputs (*.*)"),
    )

    window._new_session_action.trigger()
    qapp.processEvents()
    assert window.workspace_tabs.currentWidget() is window.session_assembly_dialog

    dialog = window.session_assembly_dialog
    assert dialog._workspace_tabs.count() == 3
    assert dialog._workspace_tabs.tabText(0) == "Grouping"
    assert dialog._workspace_tabs.tabText(1) == "Session Metadata"
    assert dialog._workspace_tabs.tabText(2) == "Selected Data Source Metadata"
    dialog._add_files_button.click()
    qapp.processEvents()
    assert dialog._input_list.count() == 1
    assert dialog._pathway_label.text() == "supported"
    assert dialog._create_button.isEnabled() is True

    dialog._create_button.click()
    qapp.processEvents()

    assert window.workspace_tabs.currentWidget() is window.conversion_widget
    assert "session-" in window.conversion_widget._session_label.text()
    assert window.conversion_widget._pathway_label.text() == "supported"
    assert window.conversion_widget._source_count_label.text() == "1"
    window.close()


def test_main_window_keeps_multiple_sessions_in_conversion_tabs(qapp, tmp_path: Path) -> None:
    first_session = make_session(tmp_path)
    second_session = make_custom_session(tmp_path)
    preview, execution = make_preview_and_execution(first_session)
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
    )
    window.show()
    qapp.processEvents()

    window._load_built_session(first_session)
    qapp.processEvents()
    window._load_built_session(second_session)
    qapp.processEvents()

    assert window.conversion_widget._session_tabs.count() == 2
    assert window.conversion_widget._session_tabs.isHidden() is False
    assert window.conversion_widget._session_tabs.tabText(0) == "sess-qt"
    assert window.conversion_widget._session_tabs.tabText(1) == "custom-qt"
    assert window._close_current_session_action.isEnabled() is True
    assert window._close_current_session_action.text() == "Close Current Session (custom-qt)"
    assert "custom-qt" in window.conversion_widget._session_label.text()

    window.conversion_widget._session_tabs.setCurrentIndex(0)
    qapp.processEvents()
    assert "sess-qt" in window.conversion_widget._session_label.text()
    assert window._close_current_session_action.text() == "Close Current Session (sess-qt)"

    window._close_current_session_action.trigger()
    qapp.processEvents()
    assert window.conversion_widget._session_tabs.count() == 1
    assert window.conversion_widget._session_tabs.tabText(0) == "custom-qt"
    assert window._close_current_session_action.isEnabled() is True
    assert "custom-qt" in window.conversion_widget._session_label.text()

    window._close_current_session_action.trigger()
    qapp.processEvents()
    assert window.conversion_widget._session_tabs.count() == 0
    assert window._close_current_session_action.isEnabled() is False
    window.close()


def test_main_window_shows_project_context_in_conversion_session_tabs(qapp, tmp_path: Path) -> None:
    project_path = tmp_path / "projects" / "saved-project.nwbforge-project.json"
    session = make_session(tmp_path)
    shell_model = DesktopShellModel()
    session = replace(
        session,
        sources=(
            replace(
                session.sources[0],
                metadata={
                    **session.sources[0].metadata,
                    "session_assembly.project_path": str(project_path.resolve()),
                    "session_assembly.project_name": project_path.name,
                },
            ),
        ),
    )
    preview, execution = make_preview_and_execution(session)
    window = MainWindow(
        shell_model,
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
    )
    window.show()
    qapp.processEvents()

    window._load_built_session(session)
    qapp.processEvents()

    assert window.conversion_widget._session_tabs.tabText(0) == "saved-project | sess-qt"
    tooltip = window.conversion_widget._session_tabs.tabToolTip(0)
    assert "project=saved-project.nwbforge-project.json" in tooltip
    assert str(project_path.resolve()) in tooltip
    assert "Project: saved-project" in window._workspace_subtitle_label.text()
    assert window._workspace_badge_label.text() == "saved-project | Sources Added"
    assert window._close_current_session_action.text() == "Close Current Session (saved-project | sess-qt)"
    assert shell_model.state.status_bar.message == "Built session sess-qt from project saved-project."
    assert "Project: saved-project | sess-qt" in window.conversion_widget._session_context_label.text()
    window.conversion_widget._session_details_toggle.setChecked(True)
    qapp.processEvents()
    assert window.conversion_widget._project_origin_label.text() == str(project_path.resolve())
    window.close()


def test_main_window_builds_session_from_dialog_with_roles_and_overrides(qapp, tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    session = make_hybrid_session(tmp_path)
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
        "nwbforge.ui.qt.session_assembly_dialog.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(manifest_path), str(custom_path)], "All supported inputs (*.*)"),
    )

    window._new_session_action.trigger()
    qapp.processEvents()
    dialog = window.session_assembly_dialog
    dialog._add_files_button.click()
    qapp.processEvents()

    dialog._source_list.setCurrentRow(0)
    qapp.processEvents()
    dialog._role_combo.setCurrentText("metadata")
    qapp.processEvents()
    dialog._source_list.setCurrentRow(1)
    qapp.processEvents()
    dialog._role_combo.setCurrentText("primary")
    qapp.processEvents()
    dialog._metadata_override_edits["subject.subject_id"].setText("qt-override-mouse-01")
    qapp.processEvents()
    assert dialog._create_button.isEnabled() is False
    dialog._confirm_all_groups_button.click()
    qapp.processEvents()
    dialog._create_button.click()
    qapp.processEvents()

    assert window.conversion_widget._pathway_label.text() == "hybrid"
    assert window.conversion_widget._source_role_label.text() == "metadata"
    assert (
        window.conversion_widget._screen_model.state.session.metadata_overrides["subject.subject_id"]
        == "qt-override-mouse-01"
    )
    window.close()


def test_session_assembly_dialog_edits_source_metadata_override(qapp, tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    session = make_hybrid_session(tmp_path)
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
        "nwbforge.ui.qt.session_assembly_dialog.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(manifest_path), str(custom_path)], "All supported inputs (*.*)"),
    )

    window._new_session_action.trigger()
    qapp.processEvents()
    dialog = window.session_assembly_dialog
    dialog._add_files_button.click()
    qapp.processEvents()

    dialog._source_list.setCurrentRow(1)
    qapp.processEvents()
    dialog._source_metadata_override_edits["subject.subject_id"].setText("custom-source-qt-01")
    qapp.processEvents()
    dialog._confirm_all_groups_button.click()
    qapp.processEvents()
    dialog._create_button.click()
    qapp.processEvents()

    assert (
        window.conversion_widget._screen_model.state.session.source_metadata_overrides["custom-session"]["subject.subject_id"]
        == "custom-source-qt-01"
    )
    window.close()


def test_session_assembly_dialog_edits_group_label_and_shows_sidecar_association(
    qapp, tmp_path: Path, monkeypatch
) -> None:
    image_path = tmp_path / "recording.tif"
    image_path.write_text("binary-placeholder", encoding="utf-8")
    sidecar_path = tmp_path / "recording.json"
    sidecar_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
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
        "nwbforge.ui.qt.session_assembly_dialog.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(image_path), str(sidecar_path)], "All supported inputs (*.*)"),
    )

    window._new_session_action.trigger()
    qapp.processEvents()
    dialog = window.session_assembly_dialog
    dialog._add_files_button.click()
    qapp.processEvents()

    dialog._source_list.setCurrentRow(1)
    qapp.processEvents()
    assert dialog._selected_sidecar_label.text() == "recording.tif"

    dialog._group_edit.setText("Manual Metadata Group")
    dialog._group_edit.editingFinished.emit()
    qapp.processEvents()

    assert dialog._source_list.currentItem() is not None
    assert "Manual Metadata Group" in dialog._source_list.currentItem().text()
    assert dialog._selected_sidecar_label.text() == "recording.tif"
    window.close()


def test_session_assembly_dialog_shows_detected_group_summary(qapp, tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
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
        "nwbforge.ui.qt.session_assembly_dialog.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(manifest_path), str(custom_path)], "All supported inputs (*.*)"),
    )

    window._new_session_action.trigger()
    qapp.processEvents()
    dialog = window.session_assembly_dialog
    dialog._add_files_button.click()
    qapp.processEvents()

    assert dialog._group_list.count() == 1
    assert dialog._selected_group_label.text() == tmp_path.name
    assert dialog._selected_group_pathway_label.text() == "hybrid"
    assert dialog._selected_group_kind_label.text() == "folder"
    assert str(tmp_path) in dialog._selected_group_anchor_label.text()
    assert "mixed supported/custom-looking inputs" in dialog._selected_group_reason_label.text()
    assert "session_manifest.json" in dialog._selected_group_members_label.text()
    assert "custom_session.json" in dialog._selected_group_members_label.text()
    assert "confirmation required" in dialog._selected_group_counts_label.text()
    window.close()


def test_session_assembly_dialog_shows_matched_workflow_group_details(qapp, tmp_path: Path) -> None:
    imaging_dir = tmp_path / "imaging"
    imaging_dir.mkdir()
    (imaging_dir / "plane-01.tif").write_text("binary-placeholder", encoding="utf-8")
    suite2p_dir = tmp_path / "suite2p"
    suite2p_dir.mkdir()
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("operator notes", encoding="utf-8")

    screen = SessionAssemblyScreenModel(SessionAssemblyService(_build_workflow_registry()))
    screen.add_supported_paths((imaging_dir,), route_name="tiff", route_display_name="TIFF Imaging")
    screen.add_supported_paths((suite2p_dir,), route_name="suite2p", route_display_name="Suite2p")
    screen.add_custom_paths((notes_path,))

    dialog = SessionAssemblyDialog(screen)
    dialog.show()
    qapp.processEvents()

    assert dialog._group_list.count() == 1
    assert dialog._selected_group_kind_label.text() == "workflow bundle"
    assert dialog._selected_group_workflow_label.text() == "TIFF + Suite2p Workflow"
    assert "combined NeuroConv workflow" in dialog._selected_group_reason_label.text()

    dialog.close()


def test_session_assembly_dialog_absorbs_selected_structured_bundle_member(qapp, tmp_path: Path) -> None:
    thor_file = tmp_path / "Image_0001_0001.tif"
    thor_file.write_text("binary-placeholder", encoding="utf-8")
    experiment_xml = tmp_path / "Experiment.xml"
    experiment_xml.write_text("<Experiment />", encoding="utf-8")

    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))
    screen.add_supported_paths((thor_file,), route_name="thor", route_display_name="Thor")
    screen.add_custom_paths((experiment_xml,))

    dialog = SessionAssemblyDialog(screen)
    dialog.show()
    qapp.processEvents()

    assert dialog._input_list.count() == 2
    assert dialog._source_list.count() == 1
    assert "2 resolved members" in dialog._selected_bundle_label.text()
    assert dialog._summary_label.text().startswith("1 sources in 1 groups, 2 selected inputs")
    assert "1 input absorbed into structured bundles." in dialog._summary_label.text()
    assert dialog._input_list.item(1).text().endswith("(inside structured bundle)")
    assert "Already represented by a selected structured source bundle." in dialog._input_list.item(1).toolTip()

    dialog.close()


def test_session_assembly_dialog_can_split_selected_group(qapp, tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
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
        "nwbforge.ui.qt.session_assembly_dialog.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(manifest_path), str(custom_path)], "All supported inputs (*.*)"),
    )

    window._new_session_action.trigger()
    qapp.processEvents()
    dialog = window.session_assembly_dialog
    dialog._add_files_button.click()
    qapp.processEvents()

    dialog._split_group_button.click()
    qapp.processEvents()

    assert dialog._group_list.count() == 2
    window.close()


def test_session_assembly_dialog_can_create_and_move_named_groups(qapp, tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("freeform notes", encoding="utf-8")
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
        "nwbforge.ui.qt.session_assembly_dialog.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(manifest_path), str(custom_path), str(notes_path)], "All supported inputs (*.*)"),
    )

    window._new_session_action.trigger()
    qapp.processEvents()
    dialog = window.session_assembly_dialog
    dialog._add_files_button.click()
    qapp.processEvents()

    dialog._source_list.clearSelection()
    dialog._source_list.item(1).setSelected(True)
    dialog._source_list.item(2).setSelected(True)
    dialog._selected_group_edit.setText("Merged Review Bundle")
    dialog._create_group_from_selection_button.click()
    qapp.processEvents()

    group_labels = [dialog._source_list.item(row).text() for row in range(dialog._source_list.count())]
    assert any("Merged Review Bundle" in label for label in group_labels[1:])
    assert any(
        dialog._group_list.item(row).text().startswith("[custom] Merged Review Bundle")
        or "Merged Review Bundle" in dialog._group_list.item(row).text()
        for row in range(dialog._group_list.count())
    )
    assert dialog._group_list.count() == 2
    window.close()


def test_main_window_opens_and_saves_project_from_direct_ingest(qapp, tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    project_path = tmp_path / "projects" / "session.nwbforge-project.json"
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    settings_screen = make_settings_screen(tmp_path)
    window = MainWindow(
        DesktopShellModel(),
        settings_screen,
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
    )
    window.show()
    qapp.processEvents()

    monkeypatch.setattr(
        "nwbforge.ui.qt.session_assembly_dialog.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(manifest_path)], "All supported inputs (*.*)"),
    )
    monkeypatch.setattr(
        "nwbforge.ui.qt.main_window.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(project_path), "NWB Forge projects (*.nwbforge-project.json)"),
    )
    monkeypatch.setattr(
        "nwbforge.ui.qt.main_window.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(project_path), "NWB Forge projects (*.nwbforge-project.json)")
        if args[1] == "Open Conversion Project"
        else (str(manifest_path), "session_manifest.json"),
    )

    window._new_session_action.trigger()
    qapp.processEvents()
    dialog = window.session_assembly_dialog
    dialog._add_files_button.click()
    qapp.processEvents()
    window._save_project_as_action.trigger()
    qapp.processEvents()

    assert project_path.exists() is True
    assert dialog._header_title_label.text() == "Conversion Project"
    assert settings_screen.state.recent_project_paths[0] == str(project_path.resolve())

    dialog.reject()
    qapp.processEvents()
    window._open_project_action.trigger()
    qapp.processEvents()

    assert window.workspace_tabs.currentWidget() is window.session_assembly_dialog
    assert window.session_assembly_dialog._input_list.count() == 1
    assert window.session_assembly_dialog._project_label.text() == str(project_path.resolve())
    window.close()


def test_main_window_can_start_and_delete_direct_ingest_projects(qapp, tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    project_path = tmp_path / "projects" / "delete-me.nwbforge-project.json"
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
        "nwbforge.ui.qt.session_assembly_dialog.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(manifest_path)], "All supported inputs (*.*)"),
    )
    monkeypatch.setattr(
        "nwbforge.ui.qt.main_window.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(project_path), "NWB Forge projects (*.nwbforge-project.json)"),
    )
    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "question",
        lambda *args, **kwargs: main_window_module.QMessageBox.StandardButton.Yes,
    )

    window._new_session_action.trigger()
    qapp.processEvents()
    dialog = window.session_assembly_dialog
    dialog._add_files_button.click()
    qapp.processEvents()
    window._save_project_as_action.trigger()
    qapp.processEvents()

    assert project_path.exists() is True

    window._delete_project_action.trigger()
    qapp.processEvents()
    assert project_path.exists() is False
    assert window.workspace_tabs.currentWidget() is window.session_assembly_dialog
    assert dialog._input_list.count() == 0
    assert dialog._project_label.text() == "Unsaved project"

    dialog._add_files_button.click()
    qapp.processEvents()
    assert dialog._input_list.count() == 1

    window._new_project_action.trigger()
    qapp.processEvents()
    assert dialog._input_list.count() == 0
    assert dialog._project_label.text() == "Unsaved project"
    window.close()


def test_main_window_restores_new_session_draft(qapp, tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    session_assembly_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=JsonSessionAssemblyWorkspaceStore(tmp_path / "state" / "session-draft.json"),
    )
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
        session_assembly_screen_model=session_assembly_screen,
    )
    window.show()
    qapp.processEvents()

    monkeypatch.setattr(
        "nwbforge.ui.qt.session_assembly_dialog.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(manifest_path)], "All supported inputs (*.*)"),
    )

    window._new_session_action.trigger()
    qapp.processEvents()
    dialog = window.session_assembly_dialog
    dialog._add_files_button.click()
    qapp.processEvents()
    dialog._role_combo.setCurrentText("metadata")
    dialog._metadata_override_edits["subject.subject_id"].setText("restored-mouse-01")
    qapp.processEvents()
    dialog.reject()
    qapp.processEvents()

    window._new_session_action.trigger()
    qapp.processEvents()
    assert dialog._input_list.count() == 1
    assert dialog._role_combo.currentText() == "metadata"
    assert dialog._metadata_override_edits["subject.subject_id"].text() == "restored-mouse-01"
    window.close()


def test_session_assembly_dialog_exposes_structured_source_selector(qapp, tmp_path: Path) -> None:
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    session_assembly_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
    )
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
        session_assembly_screen_model=session_assembly_screen,
    )
    window.show()
    qapp.processEvents()

    window._new_session_action.trigger()
    qapp.processEvents()
    dialog = window.session_assembly_dialog

    assert dialog._source_type_combo.count() >= 1
    assert dialog._source_type_combo.itemText(0) == "Custom"
    assert dialog._add_files_button.text() == "Add Custom Files..."
    assert dialog._add_folder_button.text() == "Add Custom Folder..."

    window.close()


def test_session_assembly_dialog_shows_canonical_entry_for_structured_group(qapp, tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("operator notes", encoding="utf-8")
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    session_assembly_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
    )
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
        session_assembly_screen_model=session_assembly_screen,
    )
    window.show()
    qapp.processEvents()

    session_assembly_screen.add_supported_paths(
        (manifest_path,),
        route_name="session_manifest",
        route_display_name="Session Manifest",
    )
    session_assembly_screen.add_custom_paths((notes_path,))
    qapp.processEvents()

    dialog = window.session_assembly_dialog
    dialog._sync_selected_group()

    assert "session_manifest.json" in dialog._selected_group_canonical_label.text()
    assert "Session Manifest manifest file or session directory" in dialog._selected_group_canonical_label.text()
    assert str(manifest_path.resolve()) in dialog._selected_group_canonical_label.text()

    window.close()


def test_session_assembly_dialog_shows_resolved_bundle_summary_for_supported_source(qapp, tmp_path: Path) -> None:
    thor_file = tmp_path / "Image_0001_0001.tif"
    thor_file.write_text("binary-placeholder", encoding="utf-8")
    (tmp_path / "Experiment.xml").write_text("<Experiment />", encoding="utf-8")
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    session_assembly_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
    )
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
        session_assembly_screen_model=session_assembly_screen,
    )
    window.show()
    qapp.processEvents()

    session_assembly_screen.add_supported_paths(
        (thor_file,),
        route_name="thor",
        route_display_name="Thor",
    )
    qapp.processEvents()

    dialog = window.session_assembly_dialog
    dialog._source_list.setCurrentRow(0)
    qapp.processEvents()

    assert "2 resolved members" in dialog._selected_bundle_label.text()
    assert "Experiment.xml" in dialog._selected_bundle_label.text()
    assert "Image_0001_0001.tif" in dialog._selected_bundle_label.text()

    window.close()


def test_main_window_applies_last_output_directory_default(qapp, tmp_path: Path, monkeypatch) -> None:
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    settings_screen = make_settings_screen(tmp_path)
    settings_screen.load()
    settings_screen.record_output_directory(tmp_path / "exports" / "prior-output.nwb")
    window = MainWindow(
        DesktopShellModel(),
        settings_screen,
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

    expected_name = "desktop-" + session.sources[0].location.parent.name + ".nwb"
    assert window.conversion_widget._output_path_edit.text().endswith(expected_name)
    assert "exports" in window.conversion_widget._output_path_edit.text()
    window.close()


def test_main_window_uses_app_state_output_directory_when_no_prior_output_exists(
    qapp, tmp_path: Path, monkeypatch
) -> None:
    session = make_session(tmp_path)
    preview, execution = make_preview_and_execution(session)
    settings_screen = make_settings_screen(tmp_path)
    settings_screen.load()
    monkeypatch.chdir(tmp_path)
    window = MainWindow(
        DesktopShellModel(),
        settings_screen,
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

    expected_directory = (tmp_path / ".nwbforge" / "outputs").resolve()
    expected_name = "desktop-" + session.sources[0].location.parent.name + ".nwb"
    assert window.conversion_widget._output_path_edit.text().endswith(expected_name)
    assert str(expected_directory) in window.conversion_widget._output_path_edit.text()
    assert expected_directory.exists() is True

    window.close()


def test_main_window_tracks_recent_sessions_menu(qapp, tmp_path: Path, monkeypatch) -> None:
    first = make_session(tmp_path / "first")
    second = make_session(tmp_path / "second")
    preview, execution = make_preview_and_execution(first)
    settings_screen = make_settings_screen(tmp_path)
    window = MainWindow(
        DesktopShellModel(),
        settings_screen,
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
    )
    window.show()
    qapp.processEvents()

    selected_paths = iter(
        [
            (str(first.sources[0].location), "session_manifest.json"),
            (str(second.sources[0].location), "session_manifest.json"),
        ]
    )
    monkeypatch.setattr(
        "nwbforge.ui.qt.main_window.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: next(selected_paths),
    )

    window._open_session_action.trigger()
    qapp.processEvents()
    window._open_session_action.trigger()
    qapp.processEvents()

    recent_actions = window._recent_sessions_menu.actions()
    assert len(recent_actions) == 2
    assert "second" in recent_actions[0].text()
    assert "first" in recent_actions[1].text()
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
    assert window.conversion_widget._artifact_count_value_label.text() == "1 artifacts"
    assert window.conversion_widget._workspace_tabs.currentIndex() == 0
    window.close()


def test_conversion_widget_opens_selected_artifact_and_folder(qapp, tmp_path: Path, monkeypatch) -> None:
    session = make_session(tmp_path)
    artifact_path = tmp_path / "reports" / "validation-report.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("{}", encoding="utf-8")
    preview, execution = make_preview_and_execution(
        session,
        generated_artifacts=(
            ProvenanceArtifact(
                artifact_type="validation_report",
                location=artifact_path,
                description="Validation report artifact",
            ),
        ),
    )
    opened_urls: list[str] = []
    monkeypatch.setattr(
        main_window_module.QDesktopServices,
        "openUrl",
        lambda url: opened_urls.append(url.toLocalFile()) or True,
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

    window.conversion_widget._artifact_list.setCurrentRow(0)
    qapp.processEvents()
    window.conversion_widget._open_artifact_button.click()
    window.conversion_widget._reveal_artifact_button.click()
    qapp.processEvents()

    assert opened_urls == [artifact_path.as_posix(), artifact_path.parent.as_posix()]
    window.close()


def test_conversion_widget_opens_validation_and_review_artifacts(qapp, tmp_path: Path, monkeypatch) -> None:
    session = make_session(tmp_path)
    validation_report = tmp_path / "reports" / "validation-report.json"
    validation_report.parent.mkdir(parents=True, exist_ok=True)
    validation_report.write_text("{}", encoding="utf-8")
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
        generated_artifacts=(
            ProvenanceArtifact(
                artifact_type="validation_report",
                location=validation_report,
                description="Validation report artifact",
            ),
        ),
    )
    opened_urls: list[str] = []
    monkeypatch.setattr(
        main_window_module.QDesktopServices,
        "openUrl",
        lambda url: opened_urls.append(url.toLocalFile()) or True,
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
    window.conversion_widget._reviewer_edit.setText("alice")
    issue_item = window.conversion_widget._issue_list.item(0)
    issue_item.setCheckState(Qt.CheckState.Checked)
    qapp.processEvents()
    window.conversion_widget._approve_button.click()
    qapp.processEvents()

    window.conversion_widget._open_validation_report_button.click()
    window.conversion_widget._open_review_artifact_button.click()
    qapp.processEvents()

    assert opened_urls[0] == validation_report.as_posix()
    assert opened_urls[1].endswith("review-decision.json")
    window.close()


def test_conversion_widget_projects_metadata_review_workspace(qapp, tmp_path: Path) -> None:
    session = ConversionSession(
        session_id="hybrid-review-qt",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=tmp_path / "session_manifest.json",
                source_type=SourceType.FILE,
                label="Structured session manifest",
                role="primary",
            ),
            SourceReference(
                source_id="custom",
                location=tmp_path / "custom_session.json",
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="supplemental",
            ),
        ),
    )
    preview = ConversionPreview(
        session=session.transition(SessionStatus.READY_TO_WRITE),
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
                    notes=("Retained value from primary source over supplemental source.",),
                )
            ),
            session=NormalizedSessionMetadata(),
        ),
        mapping_plan=MappingPlan(pathway=session.pathway, decisions=(), issues=()),
        provenance_record=ProvenanceRecord(
            session_id=session.session_id,
            pathway=session.pathway,
            input_artifacts=(),
            generated_artifacts=(),
        ),
    )
    _, execution = make_preview_and_execution(session)
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
    window.conversion_widget._workspace_tabs.setCurrentIndex(1)
    qapp.processEvents()

    assert window.conversion_widget._disagreement_list.count() == 1
    assert window.conversion_widget._workspace_tabs.currentIndex() == 1
    assert "subject.subject_id" in window.conversion_widget._selected_disagreement_value_label.text()
    assert window.conversion_widget._selected_disagreement_source_list.count() == 2
    assert "Pending Review" in window.conversion_widget._disagreement_list.item(0).text()
    assert "primary-mouse-01" in window.conversion_widget._disagreement_list.item(0).text()
    assert not window.conversion_widget._custom_session_override_toggle.isChecked()
    assert not window.conversion_widget._manual_session_override_edit.isVisible()
    assert (
        "use the selected source value as the preferred session value"
        in window.conversion_widget._recommended_resolution_label.text().lower()
    )
    window.close()


def test_conversion_widget_sorts_pending_metadata_conflicts_before_resolved(qapp, tmp_path: Path) -> None:
    session = ConversionSession(
        session_id="hybrid-review-order-qt",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=tmp_path / "session_manifest.json",
                source_type=SourceType.FILE,
                label="Structured session manifest",
                role="primary",
            ),
            SourceReference(
                source_id="custom",
                location=tmp_path / "custom_session.json",
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="supplemental",
            ),
        ),
    )
    preview, execution = make_preview_and_execution(session)
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor(preview, execution)),
    )
    window.show()
    qapp.processEvents()

    window.conversion_widget.load_session(session)
    window.conversion_widget._screen_model.restore_state(
        replace(
            window.conversion_widget._screen_model.state,
            metadata_disagreements=(
                MetadataDisagreementItem(
                    canonical_key="session.session_description",
                    resolved_value="override description",
                    resolved_origin="adapter_extracted",
                    source_ids=("manifest", "custom"),
                    source_values=(
                        MetadataDisagreementSourceItem(
                            source_id="manifest",
                            source_label="Structured session manifest",
                            role="primary",
                            extracted_key="session.session_description",
                            value="manifest description",
                        ),
                        MetadataDisagreementSourceItem(
                            source_id="custom",
                            source_label="Custom session JSON",
                            role="supplemental",
                            extracted_key="session.session_description",
                            value="custom description",
                        ),
                    ),
                    session_override_value="override description",
                    resolution_status="session_override",
                    resolution_history=(
                        "Session override currently resolves session.session_description to 'override description'.",
                    ),
                    pending_resolution=False,
                ),
                MetadataDisagreementItem(
                    canonical_key="subject.subject_id",
                    resolved_value="primary-mouse-01",
                    resolved_origin="adapter_extracted",
                    source_ids=("manifest", "custom"),
                    source_values=(
                        MetadataDisagreementSourceItem(
                            source_id="manifest",
                            source_label="Structured session manifest",
                            role="primary",
                            extracted_key="subject.subject_id",
                            value="primary-mouse-01",
                        ),
                        MetadataDisagreementSourceItem(
                            source_id="custom",
                            source_label="Custom session JSON",
                            role="supplemental",
                            extracted_key="subject.subject_id",
                            value="custom-mouse-01",
                        ),
                    ),
                    resolution_status="pending",
                    pending_resolution=True,
                ),
            ),
        )
    )
    qapp.processEvents()
    window.conversion_widget._disagreement_filter_combo.setCurrentText("All conflicts")
    qapp.processEvents()

    assert window.conversion_widget._disagreement_list.count() == 2
    assert "Pending Review" in window.conversion_widget._disagreement_list.item(0).text()
    assert "subject.subject_id" in window.conversion_widget._disagreement_list.item(0).text()
    assert "Resolved" in window.conversion_widget._disagreement_list.item(1).text()
    assert "session.session_description" in window.conversion_widget._disagreement_list.item(1).text()
    window.close()


def test_conversion_widget_can_apply_session_override_from_metadata_review(qapp, tmp_path: Path) -> None:
    session = ConversionSession(
        session_id="hybrid-review-qt",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=tmp_path / "session_manifest.json",
                source_type=SourceType.FILE,
                label="Structured session manifest",
                role="primary",
            ),
            SourceReference(
                source_id="custom",
                location=tmp_path / "custom_session.json",
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="supplemental",
            ),
        ),
    )
    preview = ConversionPreview(
        session=session.transition(SessionStatus.READY_TO_WRITE),
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
        mapping_plan=MappingPlan(pathway=session.pathway, decisions=(), issues=()),
        provenance_record=ProvenanceRecord(
            session_id=session.session_id,
            pathway=session.pathway,
            input_artifacts=(),
            generated_artifacts=(),
        ),
    )
    _, execution = make_preview_and_execution(session)
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
    window.conversion_widget._selected_disagreement_source_list.setCurrentRow(1)
    qapp.processEvents()

    recommendation_text = window.conversion_widget._recommended_resolution_label.text()
    assert "Structured session manifest" in recommendation_text
    assert "preferred session value" in recommendation_text

    window.conversion_widget._use_source_value_button.click()
    qapp.processEvents()

    assert (
        window.conversion_widget._screen_model.state.session.metadata_overrides["subject.subject_id"]
        == "custom-mouse-01"
    )
    assert window.conversion_widget._screen_model.state.preview is None
    assert "Applied session override" in window.conversion_widget._status_label.text()
    window.close()


def test_conversion_widget_can_apply_source_override_from_metadata_review(qapp, tmp_path: Path) -> None:
    session = ConversionSession(
        session_id="hybrid-source-review-qt",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=tmp_path / "session_manifest.json",
                source_type=SourceType.FILE,
                label="Structured session manifest",
                role="primary",
            ),
            SourceReference(
                source_id="custom",
                location=tmp_path / "custom_session.json",
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="supplemental",
            ),
        ),
    )
    preview = ConversionPreview(
        session=session.transition(SessionStatus.READY_TO_WRITE),
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
        mapping_plan=MappingPlan(pathway=session.pathway, decisions=(), issues=()),
        provenance_record=ProvenanceRecord(
            session_id=session.session_id,
            pathway=session.pathway,
            input_artifacts=(),
            generated_artifacts=(),
        ),
    )
    _, execution = make_preview_and_execution(session)
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
    window.conversion_widget._advanced_toggle.setChecked(True)
    qapp.processEvents()
    window.conversion_widget._selected_disagreement_source_list.setCurrentRow(1)
    qapp.processEvents()
    window.conversion_widget._selected_source_override_edit.setText("manual-custom-01")
    qapp.processEvents()
    window.conversion_widget._apply_source_override_button.click()
    qapp.processEvents()

    assert (
        window.conversion_widget._screen_model.state.session.source_metadata_overrides["custom"]["subject.subject_id"]
        == "manual-custom-01"
    )
    assert window.conversion_widget._screen_model.state.preview is None
    assert "Applied source override" in window.conversion_widget._status_label.text()
    window.close()


def test_conversion_widget_can_apply_manual_session_override_from_metadata_review(qapp, tmp_path: Path) -> None:
    session = ConversionSession(
        session_id="hybrid-manual-review-qt",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=tmp_path / "session_manifest.json",
                source_type=SourceType.FILE,
                label="Structured session manifest",
                role="primary",
            ),
            SourceReference(
                source_id="custom",
                location=tmp_path / "custom_session.json",
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="supplemental",
            ),
        ),
    )
    preview = ConversionPreview(
        session=session.transition(SessionStatus.READY_TO_WRITE),
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
        mapping_plan=MappingPlan(pathway=session.pathway, decisions=(), issues=()),
        provenance_record=ProvenanceRecord(
            session_id=session.session_id,
            pathway=session.pathway,
            input_artifacts=(),
            generated_artifacts=(),
        ),
    )
    _, execution = make_preview_and_execution(session)
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
    window.conversion_widget._custom_session_override_toggle.setChecked(True)
    qapp.processEvents()
    window.conversion_widget._manual_session_override_edit.setText("manual-session-01")
    qapp.processEvents()
    window.conversion_widget._apply_manual_session_override_button.click()
    qapp.processEvents()

    assert (
        window.conversion_widget._screen_model.state.session.metadata_overrides["subject.subject_id"]
        == "manual-session-01"
    )
    assert "Applied session override" in window.conversion_widget._status_label.text()
    window.close()


def test_conversion_widget_can_use_selected_source_value_as_source_override(qapp, tmp_path: Path) -> None:
    session = ConversionSession(
        session_id="hybrid-source-value-review-qt",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=tmp_path / "session_manifest.json",
                source_type=SourceType.FILE,
                label="Structured session manifest",
                role="primary",
            ),
            SourceReference(
                source_id="custom",
                location=tmp_path / "custom_session.json",
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="supplemental",
            ),
        ),
    )
    preview = ConversionPreview(
        session=session.transition(SessionStatus.READY_TO_WRITE),
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
        mapping_plan=MappingPlan(pathway=session.pathway, decisions=(), issues=()),
        provenance_record=ProvenanceRecord(
            session_id=session.session_id,
            pathway=session.pathway,
            input_artifacts=(),
            generated_artifacts=(),
        ),
    )
    _, execution = make_preview_and_execution(session)
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
    window.conversion_widget._advanced_toggle.setChecked(True)
    qapp.processEvents()
    window.conversion_widget._selected_disagreement_source_list.setCurrentRow(1)
    qapp.processEvents()
    window.conversion_widget._use_source_value_as_source_override_button.click()
    qapp.processEvents()

    assert (
        window.conversion_widget._screen_model.state.session.source_metadata_overrides["custom"]["subject.subject_id"]
        == "custom-mouse-01"
    )
    assert "Applied source override" in window.conversion_widget._status_label.text()
    window.close()


def test_conversion_widget_filters_resolved_metadata_conflicts(qapp, tmp_path: Path) -> None:
    session = ConversionSession(
        session_id="hybrid-filter-review-qt",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=tmp_path / "session_manifest.json",
                source_type=SourceType.FILE,
                label="Structured session manifest",
                role="primary",
            ),
            SourceReference(
                source_id="custom",
                location=tmp_path / "custom_session.json",
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="supplemental",
            ),
        ),
        metadata_overrides={"subject.subject_id": "resolved-mouse-01"},
    )
    preview = ConversionPreview(
        session=session.transition(SessionStatus.READY_TO_WRITE),
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
        mapping_plan=MappingPlan(pathway=session.pathway, decisions=(), issues=()),
        provenance_record=ProvenanceRecord(
            session_id=session.session_id,
            pathway=session.pathway,
            input_artifacts=(),
            generated_artifacts=(),
        ),
    )
    _, execution = make_preview_and_execution(session)
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

    assert "0 pending review" in window.conversion_widget._metadata_resolution_summary_label.text()
    assert "1 resolved" in window.conversion_widget._metadata_resolution_summary_label.text()
    window.conversion_widget._disagreement_filter_combo.setCurrentText("Resolved only")
    qapp.processEvents()
    assert "Resolved" in window.conversion_widget._disagreement_list.item(0).text()
    assert window.conversion_widget._disagreement_list.count() == 1
    window.conversion_widget._disagreement_filter_combo.setCurrentText("Pending only")
    qapp.processEvents()
    assert window.conversion_widget._disagreement_list.count() == 0
    window.close()


def test_conversion_widget_can_clear_all_overrides_for_selected_field(qapp, tmp_path: Path) -> None:
    session = ConversionSession(
        session_id="hybrid-clear-all-review-qt",
        pathway=ConversionPathway.HYBRID,
        status=SessionStatus.SOURCES_ADDED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=tmp_path / "session_manifest.json",
                source_type=SourceType.FILE,
                label="Structured session manifest",
                role="primary",
            ),
            SourceReference(
                source_id="custom",
                location=tmp_path / "custom_session.json",
                source_type=SourceType.FILE,
                label="Custom session JSON",
                role="supplemental",
            ),
        ),
        metadata_overrides={"subject.subject_id": "session-value"},
        source_metadata_overrides={"custom": {"subject.subject_id": "source-value"}},
    )
    preview = ConversionPreview(
        session=session.transition(SessionStatus.READY_TO_WRITE),
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
        mapping_plan=MappingPlan(pathway=session.pathway, decisions=(), issues=()),
        provenance_record=ProvenanceRecord(
            session_id=session.session_id,
            pathway=session.pathway,
            input_artifacts=(),
            generated_artifacts=(),
        ),
    )
    _, execution = make_preview_and_execution(session)
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
    window.conversion_widget._advanced_toggle.setChecked(True)
    qapp.processEvents()
    window.conversion_widget._disagreement_filter_combo.setCurrentText("All conflicts")
    qapp.processEvents()
    assert window.conversion_widget._custom_session_override_toggle.isChecked()
    assert (
        window.conversion_widget._selected_session_override_status_label.text()
        == "Preferred session value: session-value"
    )
    assert (
        window.conversion_widget._selected_source_override_status_label.text()
        == "Source-specific overrides: Custom session JSON: source-value"
    )
    assert "session override" in window.conversion_widget._selected_resolution_status_label.text().lower()
    assert "session override" in window.conversion_widget._disagreement_list.item(0).text().lower()
    assert "Resolution state: session override" in window.conversion_widget._disagreement_list.item(0).toolTip()
    window.conversion_widget._clear_all_field_overrides_button.click()
    qapp.processEvents()

    assert window.conversion_widget._screen_model.state.session is not None
    assert window.conversion_widget._screen_model.state.session.metadata_overrides == {}
    assert window.conversion_widget._screen_model.state.session.source_metadata_overrides == {}
    assert "Cleared all overrides" in window.conversion_widget._status_label.text()
    window.close()


def test_conversion_widget_surfaces_missing_artifact_error(qapp, tmp_path: Path) -> None:
    session = make_session(tmp_path)
    missing_artifact = tmp_path / "reports" / "missing-validation-report.json"
    preview, execution = make_preview_and_execution(
        session,
        generated_artifacts=(
            ProvenanceArtifact(
                artifact_type="validation_report",
                location=missing_artifact,
                description="Missing validation report artifact",
            ),
        ),
    )
    shell_model = DesktopShellModel()
    window = MainWindow(
        shell_model,
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

    window.conversion_widget._open_validation_report_button.click()
    qapp.processEvents()

    assert shell_model.state.last_user_error is not None
    assert shell_model.state.last_user_error.title == "Artifact Open Error"
    assert shell_model.state.last_user_error.message == "The selected artifact no longer exists."
    assert shell_model.state.status_bar.is_error is True
    window.close()


def test_conversion_widget_surfaces_open_failure_error(qapp, tmp_path: Path, monkeypatch) -> None:
    session = make_session(tmp_path)
    artifact_path = tmp_path / "reports" / "validation-report.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("{}", encoding="utf-8")
    preview, execution = make_preview_and_execution(
        session,
        generated_artifacts=(
            ProvenanceArtifact(
                artifact_type="validation_report",
                location=artifact_path,
                description="Validation report artifact",
            ),
        ),
    )
    monkeypatch.setattr(
        main_window_module.QDesktopServices,
        "openUrl",
        lambda url: False,
    )
    shell_model = DesktopShellModel()
    window = MainWindow(
        shell_model,
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

    window.conversion_widget._open_validation_report_button.click()
    qapp.processEvents()

    assert shell_model.state.last_user_error is not None
    assert shell_model.state.last_user_error.title == "Artifact Open Error"
    assert shell_model.state.last_user_error.message == "The selected artifact could not be opened."
    assert shell_model.state.status_bar.is_error is True
    window.close()
