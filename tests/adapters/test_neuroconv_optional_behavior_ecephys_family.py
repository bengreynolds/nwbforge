import json
from pathlib import Path

from nwbforge.adapters import (
    NeuroConvAxonAdapter,
    NeuroConvEdfAdapter,
    NeuroConvIntanAdapter,
    NeuroConvMedPCAdapter,
    NeuroConvOpenEphysBinaryAdapter,
    NeuroConvSpikeGadgetsAdapter,
    NeuroConvSpikeGLXAdapter,
)
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


def test_axon_adapter_matches_abf_and_extracts_fields(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.abf"
    source_path.write_bytes(b"fake-abf")
    source = SourceReference(
        source_id="axon-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Axon recording",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "NWBFile": {"session_start_time": "2026-04-01T09:00:00-06:00"},
                "Ecephys": {"Device": [{"name": "Axon Instruments"}], "ElectrodeGroup": [{"name": "GroupA"}]},
            }

    adapter = NeuroConvAxonAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.record_type == "neuroconv_axon"
    assert result.fields["ecephys.axon.device_name"].value == "Axon Instruments"


def test_edf_adapter_matches_edf_and_tracks_skipped_channels(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.edf"
    source_path.write_bytes(b"fake-edf")
    source = SourceReference(
        source_id="edf-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="EDF recording",
        metadata={"neuroconv.interface_kwargs_json": json.dumps({"channels_to_skip": ["ECG"]})},
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "EDF Recording"}], "ElectrodeGroup": []}}

    adapter = NeuroConvEdfAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ecephys.edf.channels_to_skip_count"].value == 1


def test_spikegadgets_adapter_matches_rec_and_extracts_stream_info(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.rec"
    source_path.write_bytes(b"fake-rec")
    source = SourceReference(
        source_id="spikegadgets-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="SpikeGadgets recording",
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "SpikeGadgets"}], "ElectrodeGroup": [{"name": "A"}]}}

    adapter = NeuroConvSpikeGadgetsAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ecephys.spikegadgets.stream_id"].value == "trodes"


def test_openephys_binary_adapter_requires_unambiguous_or_configured_stream(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "openephys"
    source_dir.mkdir()
    (source_dir / "structure.oebin").write_text("{}", encoding="utf-8")

    adapter = NeuroConvOpenEphysBinaryAdapter()
    monkeypatch.setattr(
        adapter.interface_cls,
        "get_stream_names",
        classmethod(lambda cls, folder_path: ["Record Node 101#AP", "Record Node 101#LFP"]),
    )

    ambiguous_source = SourceReference(
        source_id="oe-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="OpenEphys binary folder",
    )
    configured_source = SourceReference(
        source_id="oe-2",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="OpenEphys binary folder",
        metadata={"neuroconv.interface_kwargs_json": json.dumps({"stream_name": "Record Node 101#AP"})},
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "OpenEphys Binary"}], "ElectrodeGroup": [{"name": "A"}]}}

    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    assert adapter.can_handle(ambiguous_source) is False
    result = adapter.inspect(configured_source)
    assert result.fields["ecephys.openephys_binary.stream_name"].value == "Record Node 101#AP"


def test_spikeglx_adapter_auto_resolves_single_stream_folder(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "spikeglx"
    source_dir.mkdir()
    (source_dir / "sample_g0_t0.imec0.ap.bin").write_bytes(b"fake-bin")
    source = SourceReference(
        source_id="spikeglx-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="SpikeGLX folder",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "NWBFile": {"session_start_time": "2026-04-01T09:00:00-06:00"},
                "Ecephys": {"Device": [{"name": "NeuropixelsImec0"}], "ElectrodeGroup": [{"name": "Shank0"}]},
            }

    adapter = NeuroConvSpikeGLXAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ecephys.spikeglx.stream_id"].value == "imec0.ap"
    assert result.fields["ecephys.spikeglx.stream_count"].value == 1
