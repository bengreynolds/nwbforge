import json
from pathlib import Path

from nwbforge.adapters import (
    NeuroConvAlphaOmegaAdapter,
    NeuroConvAxonAdapter,
    NeuroConvAxonaAdapter,
    NeuroConvBiocamAdapter,
    NeuroConvBlackrockAdapter,
    NeuroConvEdfAdapter,
    NeuroConvIntanAdapter,
    NeuroConvMCSRawAdapter,
    NeuroConvMedPCAdapter,
    NeuroConvNeuralynxAdapter,
    NeuroConvNeuralynxNvtAdapter,
    NeuroConvNeuroScopeAdapter,
    NeuroConvOpenEphysBinaryAnalogAdapter,
    NeuroConvOpenEphysBinaryAdapter,
    NeuroConvOpenEphysLegacyAdapter,
    NeuroConvPlexonAdapter,
    NeuroConvSpikeGadgetsAdapter,
    NeuroConvSpikeGLXAdapter,
    NeuroConvTdtAdapter,
    NeuroConvWhiteMatterAdapter,
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


def test_alphaomega_adapter_matches_mpx_folder_and_extracts_summary_fields(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "alphaomega"
    source_dir.mkdir()
    (source_dir / "session.mpx").write_bytes(b"fake-mpx")
    source = SourceReference(
        source_id="alphaomega-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="AlphaOmega folder",
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "AlphaOmega"}], "ElectrodeGroup": [{"name": "A"}]}}

    adapter = NeuroConvAlphaOmegaAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ecephys.alphaomega.mpx_file_count"].value == 1


def test_axona_adapter_prefers_set_or_bin_with_set_sidecar(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.bin"
    source_path.write_bytes(b"fake-bin")
    source_path.with_suffix(".set").write_text("fake-set", encoding="utf-8")
    source = SourceReference(
        source_id="axona-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Axona recording",
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "Axona"}], "ElectrodeGroup": [{"name": "Tet1"}]}}

    adapter = NeuroConvAxonaAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ecephys.axona.has_set_sidecar"].value is True


def test_blackrock_adapter_matches_nsx_and_extracts_suffix(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.ns6"
    source_path.write_bytes(b"fake-nsx")
    source = SourceReference(
        source_id="blackrock-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Blackrock recording",
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "Blackrock"}], "ElectrodeGroup": [{"name": "ArrayA"}]}}

    adapter = NeuroConvBlackrockAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ecephys.blackrock.nsx_suffix"].value == ".ns6"


def test_biocam_adapter_matches_bwr_and_extracts_fields(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.bwr"
    source_path.write_bytes(b"fake-bwr")
    source = SourceReference(
        source_id="biocam-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Biocam recording",
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "Biocam"}], "ElectrodeGroup": [{"name": "A"}]}}

    adapter = NeuroConvBiocamAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ecephys.biocam.device_name"].value == "Biocam"


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


def test_mcsraw_adapter_matches_raw_and_extracts_fields(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.raw"
    source_path.write_bytes(b"fake-raw")
    source = SourceReference(
        source_id="mcsraw-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="MCSRaw recording",
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "MCSRaw"}], "ElectrodeGroup": [{"name": "MEA"}]}}

    adapter = NeuroConvMCSRawAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ecephys.mcsraw.device_name"].value == "MCSRaw"


def test_neuralynx_adapter_requires_unambiguous_or_configured_stream(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "neuralynx"
    source_dir.mkdir()
    (source_dir / "CSC1.ncs").write_bytes(b"fake-ncs")
    adapter = NeuroConvNeuralynxAdapter()
    monkeypatch.setattr(
        adapter.interface_cls,
        "get_stream_names",
        classmethod(lambda cls, folder_path: ["StreamA", "StreamB"]),
    )

    ambiguous_source = SourceReference(
        source_id="neuralynx-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="Neuralynx folder",
    )
    configured_source = SourceReference(
        source_id="neuralynx-2",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="Neuralynx folder",
        metadata={"neuroconv.interface_kwargs_json": json.dumps({"stream_name": "StreamA"})},
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "Neuralynx"}], "ElectrodeGroup": [{"name": "A"}]}}

    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    assert adapter.can_handle(ambiguous_source) is False
    result = adapter.inspect(configured_source)
    assert result.fields["ecephys.neuralynx.stream_name"].value == "StreamA"


def test_neuralynx_nvt_adapter_matches_nvt_and_extracts_behavior_summary(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "tracking.nvt"
    source_path.write_bytes(b"fake-nvt")
    source = SourceReference(
        source_id="nvt-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Neuralynx NVT tracking",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "NWBFile": {"session_start_time": "2026-04-02T09:00:00-06:00"},
                "Behavior": {"tracking.nvt": {"position_name": "NvtSpatialSeries"}},
            }

    adapter = NeuroConvNeuralynxNvtAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["behavior.neuralynx_nvt.container_name"].value == "tracking.nvt"


def test_neuroscope_adapter_requires_xml_sidecar_or_config(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.dat"
    source_path.write_bytes(b"fake-dat")
    adapter = NeuroConvNeuroScopeAdapter()
    source_without_xml = SourceReference(
        source_id="neuroscope-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="NeuroScope recording",
    )
    source_with_config = SourceReference(
        source_id="neuroscope-2",
        location=source_path,
        source_type=SourceType.FILE,
        label="NeuroScope recording",
        metadata={"neuroconv.interface_kwargs_json": json.dumps({"xml_file_path": str(tmp_path / "recording.xml")})},
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "NeuroScope"}], "ElectrodeGroup": [{"name": "A"}]}}

    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    assert adapter.can_handle(source_without_xml) is False
    result = adapter.inspect(source_with_config)
    assert result.fields["ecephys.neuroscope.has_xml_sidecar"].value is True


def test_openephys_binary_analog_adapter_requires_unambiguous_or_configured_stream(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "openephys-analog"
    source_dir.mkdir()
    (source_dir / "structure.oebin").write_text("{}", encoding="utf-8")

    adapter = NeuroConvOpenEphysBinaryAnalogAdapter()
    monkeypatch.setattr(
        adapter.interface_cls,
        "get_stream_names",
        classmethod(lambda cls, folder_path: ["AnalogA", "AnalogB"]),
        raising=False,
    )

    ambiguous_source = SourceReference(
        source_id="oe-analog-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="OpenEphys analog folder",
    )
    configured_source = SourceReference(
        source_id="oe-analog-2",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="OpenEphys analog folder",
        metadata={"neuroconv.interface_kwargs_json": json.dumps({"stream_name": "AnalogA"})},
    )

    class FakeInterface:
        def get_metadata(self):
            return {"NWBFile": {"session_start_time": "2026-04-02T09:00:00-06:00"}}

    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    assert adapter.can_handle(ambiguous_source) is False
    result = adapter.inspect(configured_source)
    assert result.fields["ecephys.openephys_binary_analog.stream_name"].value == "AnalogA"


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


def test_openephys_legacy_adapter_requires_unambiguous_or_configured_stream(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "openephys-legacy"
    source_dir.mkdir()
    (source_dir / "100_CH1.continuous").write_bytes(b"fake-continuous")

    adapter = NeuroConvOpenEphysLegacyAdapter()
    monkeypatch.setattr(
        adapter.interface_cls,
        "get_stream_names",
        classmethod(lambda cls, folder_path: ["LegacyA", "LegacyB"]),
    )

    ambiguous_source = SourceReference(
        source_id="oe-legacy-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="OpenEphys legacy folder",
    )
    configured_source = SourceReference(
        source_id="oe-legacy-2",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="OpenEphys legacy folder",
        metadata={"neuroconv.interface_kwargs_json": json.dumps({"stream_name": "LegacyA"})},
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "OpenEphys Legacy"}], "ElectrodeGroup": [{"name": "A"}]}}

    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    assert adapter.can_handle(ambiguous_source) is False
    result = adapter.inspect(configured_source)
    assert result.fields["ecephys.openephys_legacy.stream_name"].value == "LegacyA"


def test_plexon_adapter_matches_plx_and_extracts_stream_name(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.plx"
    source_path.write_bytes(b"fake-plx")
    source = SourceReference(
        source_id="plexon-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Plexon recording",
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "Plexon"}], "ElectrodeGroup": [{"name": "A"}]}}

    adapter = NeuroConvPlexonAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ecephys.plexon.stream_name"].value == "WB-Wideband"


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


def test_tdt_adapter_requires_gain_and_extracts_configuration(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "tdt"
    source_dir.mkdir()
    (source_dir / "block.tsq").write_bytes(b"fake-tsq")
    missing_gain_source = SourceReference(
        source_id="tdt-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="TDT folder",
    )
    configured_source = SourceReference(
        source_id="tdt-2",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="TDT folder",
        metadata={"neuroconv.interface_kwargs_json": json.dumps({"gain": 0.195, "stream_name": "Wav1"})},
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "TDT"}], "ElectrodeGroup": [{"name": "A"}]}}

    adapter = NeuroConvTdtAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    assert adapter.can_handle(missing_gain_source) is False
    result = adapter.inspect(configured_source)
    assert result.fields["ecephys.tdt.gain"].value == 0.195
    assert result.fields["ecephys.tdt.stream_name"].value == "Wav1"


def test_whitematter_adapter_requires_shape_config_and_avoids_axona_collision(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.bin"
    source_path.write_bytes(b"fake-white-matter")
    blocked_source = SourceReference(
        source_id="whitematter-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="WhiteMatter binary",
    )
    configured_source = SourceReference(
        source_id="whitematter-2",
        location=source_path,
        source_type=SourceType.FILE,
        label="WhiteMatter binary",
        metadata={"neuroconv.interface_kwargs_json": json.dumps({"sampling_frequency": 30000.0, "num_channels": 32})},
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "WhiteMatter"}], "ElectrodeGroup": [{"name": "A"}]}}

    adapter = NeuroConvWhiteMatterAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    assert adapter.can_handle(blocked_source) is False
    result = adapter.inspect(configured_source)
    assert result.fields["ecephys.whitematter.num_channels"].value == 32
