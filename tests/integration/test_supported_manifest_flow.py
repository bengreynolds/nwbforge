import json
from pathlib import Path

from nwbforge.adapters import AdapterRegistry, SessionManifestAdapter
from nwbforge.app.services import RegistrySourceInspectionService
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ConversionSession, SourceReference
from nwbforge.mapping import RuleBasedMappingPlanner
from nwbforge.normalization import RuleBasedNormalizationService


def test_supported_manifest_flow_produces_reviewable_mapping_plan(tmp_path: Path) -> None:
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
    session = ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        sources=(source,),
    )

    registry = AdapterRegistry()
    registry.register(SessionManifestAdapter())

    extraction = RegistrySourceInspectionService(registry).inspect(session, "source-1")
    normalized = RuleBasedNormalizationService().normalize(session, (extraction,))
    plan = RuleBasedMappingPlanner().plan(session, normalized)

    assert extraction.record_type == "session_manifest"
    assert normalized.session.session_description is not None
    assert normalized.session.experiment_description is not None
    assert normalized.subject.subject_id is not None
    assert normalized.subject.sex is not None
    assert len(normalized.devices) == 1
    assert normalized.devices[0].name.value == "Camera One"
    assert len(normalized.acquisition_streams) == 1
    assert normalized.acquisition_streams[0].name.value == "Lick Trace"
    assert any(decision.target_path == "NWBFile.session_description" for decision in plan.decisions)
    assert any(decision.target_path == "NWBFile.experiment_description" for decision in plan.decisions)
    assert any(decision.target_path == "Device[camera-1].name" for decision in plan.decisions)
    assert any(
        decision.target_path == "BehavioralTimeSeries[behavior].TimeSeries[lick-trace].data"
        for decision in plan.decisions
    )
    assert any(decision.source_key == "operator_note" for decision in plan.decisions)
