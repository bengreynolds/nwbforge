import json
from pathlib import Path

from pynwb import NWBHDF5IO

from nwbforge.adapters import AdapterRegistry, NeuroConvFicTracAdapter, SessionManifestAdapter
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


def write_fictrac_file(path: Path) -> None:
    rows = []
    for index in range(3):
        values = [0.0] * 25
        values[0] = index
        values[14] = 0.1 * index
        values[15] = 0.2 * index
        values[16] = 0.3 * index
        values[18] = 0.4 * index
        values[19] = 0.5 * index
        values[20] = 0.6 * index
        values[21] = index * 100.0
        rows.append(",".join(str(value) for value in values))
    path.write_text("\n".join(rows), encoding="utf-8")


def make_pipeline() -> ConversionPipelineService:
    registry = AdapterRegistry()
    registry.register(SessionManifestAdapter())
    registry.register(NeuroConvFicTracAdapter())
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


def make_manifest_and_fictrac_session(tmp_path: Path) -> ConversionSession:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "session-fictrac-01",
                    "description": "FicTrac behavior acquisition",
                    "start_time": "2026-04-01T10:15:00-06:00",
                    "experiment_description": "FicTrac spherical treadmill session",
                },
                "subject": {
                    "subject_id": "fly-01",
                    "species": "Drosophila melanogaster",
                    "sex": "U",
                    "age": "P5D",
                },
            }
        ),
        encoding="utf-8",
    )
    fictrac_path = tmp_path / "fictrac.dat"
    write_fictrac_file(fictrac_path)

    return ConversionSession(
        session_id="sess-fictrac",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=manifest_path,
                source_type=SourceType.FILE,
                label="Structured session manifest",
            ),
            SourceReference(
                source_id="fictrac",
                location=fictrac_path,
                source_type=SourceType.FILE,
                label="FicTrac behavior",
            ),
        ),
    )


def test_pipeline_execute_writes_fictrac_from_neuroconv_source(tmp_path: Path) -> None:
    pipeline = make_pipeline()
    preview = pipeline.build_preview(make_manifest_and_fictrac_session(tmp_path))
    output_path = tmp_path / "generated" / "session.nwb"

    execution = pipeline.execute(preview, output_path)

    assert execution.session.status == SessionStatus.COMPLETED
    assert execution.validation_summary.is_passing() is True
    with NWBHDF5IO(str(output_path), "r") as io:
        nwbfile = io.read()
        assert "behavior" in nwbfile.processing
        assert "FicTrac" in nwbfile.processing["behavior"].data_interfaces
