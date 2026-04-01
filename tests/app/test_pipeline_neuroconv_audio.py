import json
import math
import struct
import wave
from pathlib import Path

from pynwb import NWBHDF5IO

from nwbforge.adapters import AdapterRegistry, NeuroConvAudioAdapter, SessionManifestAdapter
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


def write_wave_file(path: Path) -> None:
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8000)
        frames = [
            struct.pack("<h", int(32767 * math.sin(2 * math.pi * 440 * index / 8000)))
            for index in range(800)
        ]
        wav_file.writeframes(b"".join(frames))


def make_pipeline() -> ConversionPipelineService:
    registry = AdapterRegistry()
    registry.register(SessionManifestAdapter())
    registry.register(NeuroConvAudioAdapter())
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


def make_manifest_and_audio_session(tmp_path: Path) -> ConversionSession:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "session-audio-01",
                    "description": "Audio acquisition",
                    "start_time": "2026-03-31T10:15:00-06:00",
                    "experiment_description": "Audio playback recording",
                },
                "subject": {
                    "subject_id": "mouse-03",
                    "species": "Mus musculus",
                    "sex": "U",
                    "age": "P45D",
                },
            }
        ),
        encoding="utf-8",
    )
    audio_path = tmp_path / "tone.wav"
    write_wave_file(audio_path)

    return ConversionSession(
        session_id="sess-audio",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=manifest_path,
                source_type=SourceType.FILE,
                label="Structured session manifest",
            ),
            SourceReference(
                source_id="audio",
                location=audio_path,
                source_type=SourceType.FILE,
                label="Reference audio",
            ),
        ),
    )


def test_pipeline_execute_writes_audio_from_neuroconv_source(tmp_path: Path) -> None:
    pipeline = make_pipeline()
    preview = pipeline.build_preview(make_manifest_and_audio_session(tmp_path))
    output_path = tmp_path / "generated" / "session.nwb"

    execution = pipeline.execute(preview, output_path)

    assert execution.session.status == SessionStatus.COMPLETED
    assert execution.validation_summary.is_passing() is True
    with NWBHDF5IO(str(output_path), "r") as io:
        nwbfile = io.read()
        assert nwbfile.stimulus is not None
        assert "AcousticWaveformSeries" in nwbfile.stimulus
