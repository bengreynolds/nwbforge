import json
from datetime import datetime
from pathlib import Path

from dateutil.tz import tzlocal
from nwbforge.adapters import AdapterRegistry, SessionManifestAdapter
from nwbforge.app.services import ConversionPipelineService, RegistrySourceInspectionService, SessionProvenanceService
from nwbforge.domain.enums import ConversionPathway, SessionStatus, SourceType
from nwbforge.domain.models import ConversionSession, ProvenanceArtifact, SourceReference
from nwbforge.mapping import PyNWBAssemblyService, RuleBasedMappingPlanner
from nwbforge.normalization import RuleBasedNormalizationService
from pynwb import NWBHDF5IO, NWBFile
from nwbforge.validation import (
    ArtifactValidationService,
    CompositeValidationService,
    NWBInspectorValidationService,
    PyNWBSchemaValidationService,
)
from pynwb.file import Subject


def make_manifest_session(tmp_path: Path) -> ConversionSession:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "session-01",
                    "description": "Visual task recording",
                    "start_time": "2026-03-31T10:15:00-06:00",
                    "experimenter": "Researcher A",
                },
                "subject": {
                    "subject_id": "mouse-01",
                    "species": "Mus musculus",
                },
                "keywords": ["vision", "behavior"],
                "operator_note": "check sync alignment",
            }
        ),
        encoding="utf-8",
    )
    source = SourceReference(
        source_id="source-1",
        location=manifest_path,
        source_type=SourceType.FILE,
        label="Structured session manifest",
    )
    return ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        sources=(source,),
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
        assembly_service=PyNWBAssemblyService(),
    )


def write_valid_nwb(path: Path) -> None:
    nwbfile = NWBFile(
        session_description="Validation test session",
        identifier="validation-test",
        session_start_time=datetime.now(tzlocal()),
        experimenter=["Researcher, Alice"],
        experiment_description="Test experiment",
        institution="Test University",
        keywords=["validation"],
    )
    nwbfile.subject = Subject(
        subject_id="mouse-01",
        species="Mus musculus",
        sex="U",
        age="P90D",
        description="Test subject",
    )
    with NWBHDF5IO(path=str(path), mode="w") as io:
        io.write(nwbfile)


def test_pipeline_build_preview_chains_existing_services(tmp_path: Path) -> None:
    preview = make_pipeline().build_preview(make_manifest_session(tmp_path))

    assert preview.session.status == SessionStatus.REVIEW
    assert preview.extraction_results[0].adapter_id == "session_manifest"
    assert preview.normalized_metadata.subject.subject_id is not None
    assert preview.provenance_record.adapter_ids == ("session_manifest",)
    assert any(decision.target_path == "NWBFile.session_description" for decision in preview.mapping_plan.decisions)


def test_pipeline_evaluate_outputs_marks_completed_for_valid_artifacts(tmp_path: Path) -> None:
    pipeline = make_pipeline()
    preview = pipeline.build_preview(make_manifest_session(tmp_path))
    nwb_file = tmp_path / "output.nwb"
    write_valid_nwb(nwb_file)

    execution = pipeline.evaluate_outputs(
        preview,
        output_artifacts=(
            ProvenanceArtifact(artifact_type="nwb", location=nwb_file),
        ),
    )

    assert execution.session.status == SessionStatus.COMPLETED
    assert execution.validation_summary.is_passing() is True
    assert execution.provenance_record.generated_artifacts[0].location == nwb_file


def test_pipeline_evaluate_outputs_marks_failed_for_invalid_artifacts(tmp_path: Path) -> None:
    pipeline = make_pipeline()
    preview = pipeline.build_preview(make_manifest_session(tmp_path))

    execution = pipeline.evaluate_outputs(
        preview,
        output_artifacts=(
            ProvenanceArtifact(artifact_type="report", location=tmp_path / "missing.json"),
        ),
    )

    assert execution.session.status == SessionStatus.FAILED
    assert execution.validation_summary.is_passing() is False


def test_pipeline_execute_writes_and_validates_nwb_output(tmp_path: Path) -> None:
    pipeline = make_pipeline()
    preview = pipeline.build_preview(make_manifest_session(tmp_path))
    output_path = tmp_path / "generated" / "session.nwb"

    execution = pipeline.execute(preview, output_path)

    assert execution.session.status == SessionStatus.FAILED
    assert output_path.exists() is True
    assert execution.output_artifacts[0].artifact_type == "nwb"
    assert any(issue.tool == "nwbinspector" for issue in execution.validation_summary.errors())
