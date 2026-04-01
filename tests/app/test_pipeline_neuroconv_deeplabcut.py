import json
from pathlib import Path

import pandas as pd
from pynwb import NWBHDF5IO

from nwbforge.adapters import AdapterRegistry, NeuroConvDeepLabCutAdapter, SessionManifestAdapter
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


def write_deeplabcut_csv(path: Path) -> None:
    columns = pd.MultiIndex.from_tuples(
        [
            ("scorer", "nose", "x"),
            ("scorer", "nose", "y"),
            ("scorer", "nose", "likelihood"),
        ],
        names=["scorer", "bodyparts", "coords"],
    )
    dataframe = pd.DataFrame([[1.0, 2.0, 0.9], [1.5, 2.5, 0.95]], columns=columns)
    dataframe.to_csv(path)


def make_pipeline() -> ConversionPipelineService:
    registry = AdapterRegistry()
    registry.register(SessionManifestAdapter())
    registry.register(NeuroConvDeepLabCutAdapter())
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


def make_manifest_and_dlc_session(tmp_path: Path) -> ConversionSession:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "session-dlc-01",
                    "description": "DeepLabCut pose estimation",
                    "start_time": "2026-04-01T10:15:00-06:00",
                    "experiment_description": "DeepLabCut pose session",
                },
                "subject": {
                    "subject_id": "mouse-04",
                    "species": "Mus musculus",
                    "sex": "U",
                    "age": "P45D",
                },
            }
        ),
        encoding="utf-8",
    )
    dlc_path = tmp_path / "deeplabcut.csv"
    write_deeplabcut_csv(dlc_path)

    return ConversionSession(
        session_id="sess-dlc",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=manifest_path,
                source_type=SourceType.FILE,
                label="Structured session manifest",
            ),
            SourceReference(
                source_id="dlc",
                location=dlc_path,
                source_type=SourceType.FILE,
                label="DeepLabCut pose data",
            ),
        ),
    )


def test_pipeline_execute_writes_deeplabcut_from_neuroconv_source(tmp_path: Path) -> None:
    pipeline = make_pipeline()
    preview = pipeline.build_preview(make_manifest_and_dlc_session(tmp_path))
    output_path = tmp_path / "generated" / "session.nwb"

    execution = pipeline.execute(preview, output_path)

    assert execution.session.status == SessionStatus.COMPLETED
    assert execution.validation_summary.is_passing() is True
    with NWBHDF5IO(str(output_path), "r") as io:
        nwbfile = io.read()
        assert "behavior" in nwbfile.processing
        assert len(nwbfile.processing["behavior"].data_interfaces) >= 1
