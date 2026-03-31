import json
from pathlib import Path

from nwbforge.adapters import SessionManifestAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def test_session_manifest_adapter_handles_manifest_file(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "session-01",
                    "description": "Visual task recording",
                    "start_time": "2026-03-31T10:15:00-06:00",
                },
                "subject": {"subject_id": "mouse-01", "species": "Mus musculus"},
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

    adapter = SessionManifestAdapter()
    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.adapter_id == "session_manifest"
    assert result.fields["session.session_id"].value == "session-01"
    assert result.fields["subject.subject_id"].value == "mouse-01"
    assert result.fields["devices.0.name"].value == "Camera One"
    assert result.fields["acquisition_streams.0.name"].value == "Lick Trace"
    assert result.fields["keywords"].value == ["vision", "behavior"]


def test_session_manifest_adapter_handles_directory_source(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "session-01"}}), encoding="utf-8")
    source = SourceReference(
        source_id="source-1",
        location=tmp_path,
        source_type=SourceType.DIRECTORY,
        label="Manifest directory",
    )

    adapter = SessionManifestAdapter()

    assert adapter.can_handle(source) is True
    assert adapter.inspect(source).fields["session.session_id"].value == "session-01"
