import json
from pathlib import Path

from nwbforge.adapters import CustomJsonSessionAdapter
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import SourceReference


def test_custom_json_session_adapter_handles_custom_session_file(tmp_path: Path) -> None:
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(
        json.dumps(
            {
                "recording_context": {
                    "recording_id": "custom-01",
                    "summary": "Custom sensor session",
                    "started_at": "2026-03-31T10:15:00-06:00",
                    "operator_name": "Researcher, Alice",
                },
                "animal_profile": {
                    "identifier": "mouse-01",
                    "species_name": "Mus musculus",
                },
                "equipment": [
                    {
                        "device_key": "wheel-sensor",
                        "name": "Wheel Encoder",
                        "description": "Custom wheel sensor",
                    }
                ],
                "signal_sets": [
                    {
                        "stream_key": "wheel-velocity",
                        "name": "Wheel Velocity",
                        "modality": "behavior",
                        "data": [0.0, 1.0],
                        "unit": "cm/s",
                        "rate": 20.0,
                    }
                ],
                "annotations": {
                    "operator_note": "custom note",
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
    )

    adapter = CustomJsonSessionAdapter()
    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert ConversionPathway.CUSTOM in adapter.capabilities.supported_pathways
    assert ConversionPathway.HYBRID in adapter.capabilities.supported_pathways
    assert result.adapter_id == "custom_json_session"
    assert result.fields["recording_context.recording_id"].value == "custom-01"
    assert result.fields["animal_profile.identifier"].value == "mouse-01"
    assert result.fields["devices.wheel-sensor.name"].value == "Wheel Encoder"
    assert result.fields["acquisition_streams.wheel-velocity.name"].value == "Wheel Velocity"
    assert result.fields["annotations.operator_note"].value == "custom note"


def test_custom_json_session_adapter_handles_directory_source(tmp_path: Path) -> None:
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(
        json.dumps({"recording_context": {"recording_id": "custom-02"}}),
        encoding="utf-8",
    )
    source = SourceReference(
        source_id="custom-source",
        location=tmp_path,
        source_type=SourceType.DIRECTORY,
        label="Custom session directory",
    )

    adapter = CustomJsonSessionAdapter()

    assert adapter.can_handle(source) is True
    assert adapter.inspect(source).fields["recording_context.recording_id"].value == "custom-02"
