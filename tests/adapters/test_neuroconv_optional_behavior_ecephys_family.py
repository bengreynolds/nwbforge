import json
from pathlib import Path

from nwbforge.adapters import NeuroConvIntanAdapter, NeuroConvMedPCAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def test_medpc_adapter_requires_config_and_extracts_summary_fields(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "session.txt"
    source_path.write_text("fake medpc export", encoding="utf-8")
    source = SourceReference(
        source_id="medpc-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="MedPC session",
        metadata={
            "neuroconv.interface_kwargs_json": json.dumps(
                {
                    "session_conditions": {"box": "A"},
                    "start_variable": "A",
                    "metadata_medpc_name_to_info_dict": {"B": {"name": "lever_presses"}},
                    "aligned_timestamp_names": ["reward_times"],
                }
            )
        },
    )

    class FakeInterface:
        def get_metadata(self):
            return {"MedPC": {"box": "A", "program": "example"}}

    adapter = NeuroConvMedPCAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.record_type == "neuroconv_medpc"
    assert result.fields["behavior.medpc.mapped_variable_count"].value == 1
    assert result.fields["behavior.medpc.aligned_timestamp_count"].value == 1


def test_intan_adapter_matches_distinctive_suffix_and_extracts_fields(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.rhd"
    source_path.write_bytes(b"fake-intan")
    source = SourceReference(
        source_id="intan-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Intan recording",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "NWBFile": {"session_start_time": "2026-04-01T09:00:00-06:00"},
                "Ecephys": {
                    "Device": [{"name": "Intan RHD"}],
                    "ElectrodeGroup": [{"name": "GroupA"}, {"name": "GroupB"}],
                },
            }

    adapter = NeuroConvIntanAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.record_type == "neuroconv_intan"
    assert result.fields["ecephys.intan.device_name"].value == "Intan RHD"
    assert result.fields["ecephys.intan.electrode_group_count"].value == 2
