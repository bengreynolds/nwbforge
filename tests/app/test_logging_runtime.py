import json
import logging
from pathlib import Path

import pytest

from nwbforge.adapters import AdapterRegistry, SessionManifestAdapter
from nwbforge.app.desktop import build_adapter_registry
from nwbforge.app.runtime import ThreadedConversionExecutor
from nwbforge.app.services import (
    ConversionPipelineService,
    RegistrySourceInspectionService,
    SessionAssemblyService,
    SessionProvenanceService,
    UiSettingsService,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ConversionSession, SourceReference
from nwbforge.mapping import PyNWBAssemblyService, RuleBasedMappingPlanner
from nwbforge.normalization import RuleBasedNormalizationService
from nwbforge.validation import (
    ArtifactValidationService,
    CompositeValidationService,
    DefaultValidationReviewPolicyService,
    JsonValidationReportService,
    NWBInspectorValidationService,
    PyNWBSchemaValidationService,
)


def make_manifest_session(tmp_path: Path) -> ConversionSession:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "session-01",
                    "description": "Visual task recording",
                    "start_time": "2026-03-31T10:15:00-06:00",
                },
                "subject": {
                    "subject_id": "mouse-01",
                    "species": "Mus musculus",
                    "sex": "U",
                    "age": "P90D",
                },
            }
        ),
        encoding="utf-8",
    )
    return ConversionSession(
        session_id="sess-logging",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="source-1",
                location=manifest_path,
                source_type=SourceType.FILE,
                label="Structured session manifest",
            ),
        ),
    )


def make_pipeline() -> ConversionPipelineService:
    registry = AdapterRegistry()
    registry.register(SessionManifestAdapter())
    return ConversionPipelineService(
        inspection_service=RegistrySourceInspectionService(registry),
        normalization_service=RuleBasedNormalizationService(),
        mapping_planner=RuleBasedMappingPlanner(),
        provenance_service=SessionProvenanceService(),
        validation_service=CompositeValidationService(
            (
                ArtifactValidationService(),
                PyNWBSchemaValidationService(),
                NWBInspectorValidationService(),
            )
        ),
        validation_policy_service=DefaultValidationReviewPolicyService(),
        validation_report_service=JsonValidationReportService(),
        assembly_service=PyNWBAssemblyService(),
    )


def test_pipeline_logs_structured_preview_events(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)

    preview = make_pipeline().build_preview(make_manifest_session(tmp_path))

    assert preview.session.session_id == "sess-logging"
    records = [record for record in caplog.records if hasattr(record, "nwbforge_context")]
    assert any(record.message == "Starting preview build." for record in records)
    assert any(record.message == "Built mapping plan." for record in records)
    start_record = next(record for record in records if record.message == "Starting preview build.")
    assert start_record.nwbforge_context["session_id"] == "sess-logging"


def test_executor_logs_structured_failure_context(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)
    executor = ThreadedConversionExecutor(make_pipeline())
    bad_session = ConversionSession(
        session_id="sess-missing-log",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="missing",
                location=tmp_path / "missing_manifest.json",
                source_type=SourceType.FILE,
                label="Missing manifest",
            ),
        ),
    )

    with pytest.raises(Exception):
        executor.submit_preview(bad_session).result(timeout=10)

    records = [record for record in caplog.records if hasattr(record, "nwbforge_context")]
    failure_record = next(record for record in records if record.message == "Preview execution failed.")
    assert failure_record.nwbforge_context["session_id"] == "sess-missing-log"
    assert failure_record.nwbforge_context["detail"] == "No adapter matched source 'missing'."
    executor.shutdown()


def test_session_assembly_service_logs_structured_draft_context(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text('{"session": {"session_id": "supported-01"}}', encoding="utf-8")

    draft = SessionAssemblyService(build_adapter_registry()).assemble_draft((manifest_path,))

    assert draft.session_id.startswith("session-")
    records = [record for record in caplog.records if hasattr(record, "nwbforge_context")]
    assembly_record = next(record for record in records if record.message == "Assembling direct-ingest session draft.")
    assert assembly_record.nwbforge_context["selected_path_count"] == 1


def test_ui_settings_service_logs_save_context(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    service = UiSettingsService(tmp_path / "ui-settings.json")

    saved = service.record_output_directory(tmp_path / "outputs" / "result.nwb")

    assert saved.last_output_directory == (tmp_path / "outputs").resolve()
    records = [record for record in caplog.records if hasattr(record, "nwbforge_context")]
    save_record = next(record for record in records if record.message == "Saved desktop settings.")
    assert save_record.nwbforge_context["settings_path"].endswith("ui-settings.json")
