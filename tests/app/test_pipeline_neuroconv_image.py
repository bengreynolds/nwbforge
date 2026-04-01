import json
from pathlib import Path

from PIL import Image
from pynwb import NWBHDF5IO

from nwbforge.adapters import AdapterRegistry, NeuroConvImageAdapter, SessionManifestAdapter
from nwbforge.app.services import (
    ConversionPipelineService,
    NeuroConvSupportedExecutionService,
    RegistrySourceInspectionService,
    SessionProvenanceService,
)
from nwbforge.domain.enums import ConversionPathway, SessionStatus, SourceType
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


def make_pipeline() -> ConversionPipelineService:
    registry = AdapterRegistry()
    registry.register(SessionManifestAdapter())
    registry.register(NeuroConvImageAdapter())
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
        supported_execution_service=NeuroConvSupportedExecutionService(registry),
    )


def make_manifest_and_image_session(tmp_path: Path) -> ConversionSession:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "session-img-01",
                    "description": "Static image acquisition",
                    "start_time": "2026-03-31T10:15:00-06:00",
                    "experiment_description": "Image stimulus capture",
                    "institution": "Test University",
                },
                "subject": {
                    "subject_id": "mouse-02",
                    "species": "Mus musculus",
                    "sex": "U",
                    "age": "P60D",
                },
            }
        ),
        encoding="utf-8",
    )
    image_path = tmp_path / "reference.png"
    Image.new("RGB", (4, 4), color=(0, 0, 255)).save(image_path)

    return ConversionSession(
        session_id="sess-image",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=manifest_path,
                source_type=SourceType.FILE,
                label="Structured session manifest",
            ),
            SourceReference(
                source_id="image",
                location=image_path,
                source_type=SourceType.FILE,
                label="Reference image",
            ),
        ),
    )


def test_pipeline_execute_writes_image_from_neuroconv_source(tmp_path: Path) -> None:
    pipeline = make_pipeline()
    preview = pipeline.build_preview(make_manifest_and_image_session(tmp_path))
    output_path = tmp_path / "generated" / "session.nwb"

    execution = pipeline.execute(preview, output_path)

    assert execution.session.status == SessionStatus.COMPLETED
    assert execution.validation_summary.is_passing() is True
    with NWBHDF5IO(str(output_path), "r") as io:
        nwbfile = io.read()
        assert nwbfile.acquisition is not None
        assert "Images" in nwbfile.acquisition
