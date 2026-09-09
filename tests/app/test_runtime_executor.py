import json
from pathlib import Path

import pytest

pytest.importorskip("nwbinspector")

from nwbforge.adapters import AdapterRegistry, SessionManifestAdapter
from nwbforge.app.runtime import PipelineRuntimeError, PipelineStage, ThreadedConversionExecutor
from nwbforge.app.services import ConversionPipelineService, RegistrySourceInspectionService, SessionProvenanceService
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
                    "experiment_description": "Visual stimulation task",
                    "experimenter": "Researcher, Alice",
                    "institution": "Test University",
                },
                "subject": {
                    "subject_id": "mouse-01",
                    "species": "Mus musculus",
                    "sex": "U",
                    "age": "P90D",
                    "description": "Test subject",
                },
            }
        ),
        encoding="utf-8",
    )
    return ConversionSession(
        session_id="sess-runtime",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="manifest",
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


def test_pipeline_build_preview_emits_progress_events(tmp_path: Path) -> None:
    events = []
    preview = make_pipeline().build_preview(
        make_manifest_session(tmp_path),
        progress_callback=events.append,
    )

    assert preview.session.session_id == "sess-runtime"
    assert [event.stage for event in events] == [
        PipelineStage.INSPECTING,
        PipelineStage.INSPECTING,
        PipelineStage.NORMALIZING,
        PipelineStage.MAPPING,
        PipelineStage.REVIEW,
    ]
    assert events[-1].percent_complete == 100


def test_threaded_conversion_executor_wraps_failures_as_runtime_errors(tmp_path: Path) -> None:
    executor = ThreadedConversionExecutor(make_pipeline())
    bad_session = ConversionSession(
        session_id="sess-missing",
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

    future = executor.submit_preview(bad_session)

    with pytest.raises(PipelineRuntimeError, match="Preview generation failed"):
        future.result(timeout=10)

    executor.shutdown()
