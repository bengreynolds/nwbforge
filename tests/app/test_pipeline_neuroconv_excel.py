import json
from pathlib import Path

import pandas as pd
from pynwb import NWBHDF5IO

from nwbforge.adapters import AdapterRegistry, NeuroConvExcelTimeIntervalsAdapter, SessionManifestAdapter
from nwbforge.app.services import ConversionPipelineService, RegistrySourceInspectionService, SessionProvenanceService
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
    registry.register(NeuroConvExcelTimeIntervalsAdapter())
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


def make_manifest_and_trials_session(tmp_path: Path) -> ConversionSession:
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
    excel_path = tmp_path / "trials.xlsx"
    pd.DataFrame(
        [
            {"start_time": 0.5, "stop_time": 1.0, "condition": "left", "correct": True},
            {"start_time": 1.2, "stop_time": 1.8, "condition": "right", "correct": False},
        ]
    ).to_excel(excel_path, index=False)
    return ConversionSession(
        session_id="sess-excel",
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
                location=excel_path,
                source_type=SourceType.FILE,
                label="Trial intervals",
            ),
        ),
    )


def test_pipeline_execute_writes_trials_from_neuroconv_excel_source(tmp_path: Path) -> None:
    pipeline = make_pipeline()
    preview = pipeline.build_preview(make_manifest_and_trials_session(tmp_path))
    output_path = tmp_path / "generated" / "session.nwb"

    execution = pipeline.execute(preview, output_path)

    assert execution.session.status == SessionStatus.COMPLETED
    assert execution.validation_summary.is_passing() is True
    with NWBHDF5IO(str(output_path), "r") as io:
        nwbfile = io.read()
        assert nwbfile.trials is not None
        assert nwbfile.trials["start_time"][:].tolist() == [0.5, 1.2]
        assert nwbfile.trials["condition"][:].tolist() == ["left", "right"]
        assert nwbfile.trials["correct"][:].tolist() == [True, False]
