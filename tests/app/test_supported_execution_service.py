import json
from pathlib import Path

from pynwb import NWBHDF5IO

from nwbforge.adapters import AdapterRegistry, NeuroConvCsvTimeIntervalsAdapter, SessionManifestAdapter
from nwbforge.app.services import (
    NeuroConvSupportedExecutionService,
    RegistrySourceInspectionService,
    SessionProvenanceService,
)
from nwbforge.app.services.pipeline import ConversionPipelineService
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


def test_supported_execution_service_writes_neuroconv_trial_output(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "session-01",
                    "description": "Visual task recording",
                    "start_time": "2026-03-31T10:15:00-06:00",
                    "experiment_description": "Visual stimulation task",
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
    csv_path = tmp_path / "trials.csv"
    csv_path.write_text("start_time,stop_time,condition\n0.5,1.0,left\n1.2,1.8,right\n", encoding="utf-8")

    session = ConversionSession(
        session_id="sess-supported-exec",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=manifest_path,
                source_type=SourceType.FILE,
                label="Structured session manifest",
            ),
            SourceReference(
                source_id="trials",
                location=csv_path,
                source_type=SourceType.FILE,
                label="Trial intervals",
            ),
        ),
    )

    registry = AdapterRegistry()
    registry.register(SessionManifestAdapter())
    registry.register(NeuroConvCsvTimeIntervalsAdapter())
    pipeline = ConversionPipelineService(
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

    preview = pipeline.build_preview(session)
    output_path = tmp_path / "generated" / "session.nwb"
    execution = pipeline.execute(preview, output_path)

    assert execution.validation_summary.is_passing() is True
    with NWBHDF5IO(str(output_path), "r") as io:
        nwbfile = io.read()
        assert nwbfile.session_description == "Visual task recording"
        assert nwbfile.subject is not None
        assert nwbfile.subject.subject_id == "mouse-01"
        assert nwbfile.trials is not None
        assert nwbfile.trials["condition"][:].tolist() == ["left", "right"]
