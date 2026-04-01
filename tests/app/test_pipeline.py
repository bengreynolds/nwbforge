import json
from datetime import datetime
from pathlib import Path

from dateutil.tz import tzlocal
from nwbforge.adapters import AdapterRegistry, CustomJsonSessionAdapter, SessionManifestAdapter
from nwbforge.app.services import ConversionPipelineService, RegistrySourceInspectionService, SessionProvenanceService
from nwbforge.domain.enums import ConversionPathway, SessionStatus, SourceType
from nwbforge.domain.models import ConversionSession, ProvenanceArtifact, SourceReference
from nwbforge.mapping import PyNWBAssemblyService, RuleBasedMappingPlanner
from nwbforge.normalization import RuleBasedNormalizationService
from pynwb import NWBHDF5IO, NWBFile
from nwbforge.validation import (
    ArtifactValidationService,
    CompositeValidationService,
    DefaultValidationReviewPolicyService,
    JsonValidationReportService,
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
                    "experiment_description": "Visual stimulation task",
                    "start_time": "2026-03-31T10:15:00-06:00",
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
                "devices": [
                    {
                        "device_id": "camera-1",
                        "name": "Camera One",
                        "description": "Behavior camera",
                        "manufacturer": "Acme Imaging",
                    }
                ],
                "acquisition_streams": [
                    {
                        "stream_id": "lick-trace",
                        "name": "Lick Trace",
                        "modality": "behavior",
                        "description": "Example lick signal",
                        "data": [0.1, 0.2, 0.3],
                        "unit": "a.u.",
                        "rate": 10.0,
                    },
                    {
                        "stream_id": "animal-position",
                        "name": "Animal Position",
                        "modality": "behavior",
                        "behavior_type": "position",
                        "description": "Tracked animal position",
                        "data": [[0.0, 1.0], [1.5, 2.5], [3.0, 4.0]],
                        "unit": "meters",
                        "reference_frame": "origin at top-left corner of arena",
                        "rate": 20.0,
                    }
                ],
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
    registry.register(CustomJsonSessionAdapter())
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


def make_custom_session(tmp_path: Path) -> ConversionSession:
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(
        json.dumps(
            {
                "recording_context": {
                    "recording_id": "custom-run-01",
                    "summary": "Custom rotary encoder and notes stream",
                    "study_description": "Custom-path workflow slice",
                    "started_at": "2026-03-31T10:15:00-06:00",
                    "operator_name": "Researcher, Alice",
                    "institute_name": "Test University",
                    "group_name": "Systems Lab",
                },
                "animal_profile": {
                    "identifier": "mouse-custom-01",
                    "species_name": "Mus musculus",
                    "sex_code": "U",
                    "life_stage": "P90D",
                    "birth_date": "2025-12-31T00:00:00-07:00",
                    "notes": "Custom workflow subject",
                    "strain_name": "C57BL/6J",
                },
                "equipment": [
                    {
                        "device_key": "wheel-sensor",
                        "name": "Wheel Encoder",
                        "description": "Custom wheel rotation sensor",
                        "manufacturer": "Custom Lab Systems",
                    }
                ],
                "signal_sets": [
                    {
                        "stream_key": "wheel-velocity",
                        "name": "Wheel Velocity",
                        "modality": "behavior",
                        "description": "Wheel velocity trace",
                        "data": [0.0, 0.2, 0.5, 0.4],
                        "unit": "cm/s",
                        "rate": 20.0,
                    }
                ],
                "annotations": {
                    "keywords": ["custom", "wheel"],
                    "task_variant": "free_running",
                    "operator_note": "Velocity derived from custom firmware stream",
                },
                "analysis_context": {
                    "sync_method": "shared_daq_clock",
                },
            }
        ),
        encoding="utf-8",
    )
    source = SourceReference(
        source_id="custom-source",
        location=custom_path,
        source_type=SourceType.FILE,
        label="Custom session JSON",
        adapter_hint="custom_json_session",
    )
    return ConversionSession(
        session_id="sess-custom-001",
        pathway=ConversionPathway.CUSTOM,
        sources=(source,),
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
    assert preview.normalized_metadata.subject.age is not None
    assert len(preview.normalized_metadata.devices) == 1
    assert len(preview.normalized_metadata.acquisition_streams) == 2
    assert preview.provenance_record.adapter_ids == ("session_manifest",)
    assert any(decision.target_path == "NWBFile.session_description" for decision in preview.mapping_plan.decisions)
    assert any(decision.target_path == "Device[camera-1].name" for decision in preview.mapping_plan.decisions)
    assert any(
        decision.target_path == "BehavioralTimeSeries[behavior].TimeSeries[lick-trace].data"
        for decision in preview.mapping_plan.decisions
    )
    assert any(
        decision.target_path == "Position[position].SpatialSeries[animal-position].data"
        for decision in preview.mapping_plan.decisions
    )


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
    assert execution.review_outcome.status == "pass"
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
    assert execution.review_outcome.blocks_completion is True


def test_pipeline_execute_writes_and_validates_nwb_output(tmp_path: Path) -> None:
    pipeline = make_pipeline()
    preview = pipeline.build_preview(make_manifest_session(tmp_path))
    output_path = tmp_path / "generated" / "session.nwb"

    execution = pipeline.execute(preview, output_path)

    assert execution.session.status == SessionStatus.COMPLETED
    assert output_path.exists() is True
    assert execution.output_artifacts[0].artifact_type == "nwb"
    assert execution.output_artifacts[1].artifact_type == "validation_report"
    assert execution.validation_summary.is_passing() is True
    assert not execution.validation_summary.errors()
    assert execution.review_outcome.status == "pass"
    with NWBHDF5IO(str(output_path), "r") as io:
        nwbfile = io.read()
        assert "behavior" in nwbfile.acquisition
        assert "Lick Trace" in nwbfile.acquisition["behavior"].time_series
        assert "position" in nwbfile.acquisition
        assert "Animal Position" in nwbfile.acquisition["position"].spatial_series
    report_path = execution.output_artifacts[1].location
    assert report_path.exists() is True
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_payload["session_id"] == "sess-001"
    assert report_payload["review_outcome"]["status"] == "pass"
    assert report_payload["generated_artifacts"][0]["artifact_type"] == "nwb"


def test_pipeline_execute_custom_session_routes_through_direct_pynwb_path(tmp_path: Path) -> None:
    pipeline = make_pipeline()
    preview = pipeline.build_preview(make_custom_session(tmp_path))
    output_path = tmp_path / "generated" / "custom-session.nwb"

    execution = pipeline.execute(preview, output_path)

    assert preview.session.pathway == ConversionPathway.CUSTOM
    assert preview.session.status == SessionStatus.REVIEW
    assert any(
        decision.target_path == "BehavioralTimeSeries[behavior].TimeSeries[wheel-velocity].data"
        for decision in preview.mapping_plan.decisions
    )
    assert any(issue.field == "annotations.operator_note" for issue in preview.mapping_plan.issues)
    assert execution.session.status == SessionStatus.COMPLETED
    assert execution.validation_summary.is_passing() is True
    assert output_path.exists() is True
    with NWBHDF5IO(str(output_path), "r") as io:
        nwbfile = io.read()
        assert "behavior" in nwbfile.acquisition
        assert "Wheel Velocity" in nwbfile.acquisition["behavior"].time_series
