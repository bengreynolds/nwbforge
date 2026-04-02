from pathlib import Path

from nwbforge.adapters import (
    NeuroConvBrukerTiffMultiPlaneAdapter,
    NeuroConvBrukerTiffSinglePlaneAdapter,
    NeuroConvFemtonicsAdapter,
    NeuroConvInscopixAdapter,
    NeuroConvMicroManagerTiffAdapter,
    NeuroConvMiniscopeAdapter,
    NeuroConvScanboxAdapter,
    NeuroConvScanImageAdapter,
    NeuroConvScanImageLegacyAdapter,
    NeuroConvTiffImagingAdapter,
    NeuroConvThorAdapter,
)
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def test_micromanager_adapter_matches_directory_with_ome_tiffs(tmp_path: Path) -> None:
    source_dir = tmp_path / "micromanager"
    source_dir.mkdir()
    (source_dir / "MMStack_1.ome.tif").write_bytes(b"fake-tiff")
    (source_dir / "DisplaySettings.json").write_text("{}", encoding="utf-8")

    adapter = NeuroConvMicroManagerTiffAdapter()

    assert adapter.can_handle(
        SourceReference(
            source_id="micromanager-1",
            location=source_dir,
            source_type=SourceType.DIRECTORY,
            label="Micro-Manager directory",
        )
    )


def test_bruker_singleplane_adapter_matches_singleplane_folder(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "bruker-single"
    source_dir.mkdir()
    (source_dir / "recording.ome.tif").write_bytes(b"fake-bruker")
    (source_dir / "recording.xml").write_text("<PVScan />", encoding="utf-8")
    (source_dir / "recording.env").write_text("env", encoding="utf-8")
    adapter = NeuroConvBrukerTiffSinglePlaneAdapter()
    monkeypatch.setattr(
        adapter.interface_cls,
        "get_streams",
        classmethod(lambda cls, folder_path: {"channel_streams": ["Ch1"], "plane_streams": {"Ch1": ["Plane1"]}}),
    )

    assert adapter.can_handle(
        SourceReference(
            source_id="bruker-single-1",
            location=source_dir,
            source_type=SourceType.DIRECTORY,
            label="Bruker single-plane directory",
        )
    )


def test_bruker_multiplane_adapter_extracts_plane_summary(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "bruker-multi"
    source_dir.mkdir()
    (source_dir / "recording.ome.tif").write_bytes(b"fake-bruker")
    (source_dir / "recording.xml").write_text("<PVScan />", encoding="utf-8")
    (source_dir / "recording.env").write_text("env", encoding="utf-8")
    source = SourceReference(
        source_id="bruker-multi-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="Bruker multi-plane directory",
    )

    adapter = NeuroConvBrukerTiffMultiPlaneAdapter()
    monkeypatch.setattr(
        adapter.interface_cls,
        "get_streams",
        classmethod(
            lambda cls, folder_path: {"channel_streams": ["Ch1"], "plane_streams": {"Ch1": ["Plane1", "Plane2"]}}
        ),
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "NWBFile": {"session_start_time": "2026-04-02T09:00:00-06:00"},
                "Ophys": {"Device": [{"name": "Bruker Ultima"}], "TwoPhotonSeries": [{"name": "TwoPhotonSeries"}]},
            }

    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert result.record_type == "neuroconv_brukertiff_multiplane"
    assert result.fields["ophys.brukertiff_multiplane.max_plane_count"].value == 2


def test_femtonics_adapter_matches_mesc_and_extracts_metadata(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "session.mesc"
    source_path.write_bytes(b"fake-mesc")
    source = SourceReference(
        source_id="femtonics-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Femtonics MESc",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "NWBFile": {"session_start_time": "2026-04-02T09:00:00-06:00"},
                "Ophys": {"Device": [{"name": "Femtonics"}], "TwoPhotonSeries": [{"name": "TwoPhotonSeries"}]},
            }

    adapter = NeuroConvFemtonicsAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ophys.femtonics.device_name"].value == "Femtonics"


def test_inscopix_adapter_matches_isxd_and_extracts_summary(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.isxd"
    source_path.write_text("inscopix", encoding="utf-8")
    source = SourceReference(
        source_id="inscopix-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Inscopix recording",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "NWBFile": {"session_start_time": "2026-04-02T09:00:00-06:00", "session_id": "inscopix-01"},
                "Ophys": {"Device": [{"name": "Inscopix nVista"}], "OnePhotonSeries": [{"name": "OnePhotonSeries"}]},
            }

    adapter = NeuroConvInscopixAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ophys.inscopix.photon_series_type"].value == "OnePhotonSeries"


def test_scanimage_current_and_legacy_routes_do_not_overlap(tmp_path: Path, monkeypatch) -> None:
    legacy_path = tmp_path / "legacy.tif"
    legacy_path.write_bytes(b"legacy")
    modern_path = tmp_path / "modern.tif"
    modern_path.write_bytes(b"modern")

    monkeypatch.setattr(
        NeuroConvScanImageAdapter.interface_cls,
        "get_scanimage_version",
        classmethod(lambda cls, file_path: 3 if Path(file_path).name == "legacy.tif" else 5),
    )

    current_adapter = NeuroConvScanImageAdapter()
    legacy_adapter = NeuroConvScanImageLegacyAdapter()

    legacy_source = SourceReference(
        source_id="scanimage-legacy-1",
        location=legacy_path,
        source_type=SourceType.FILE,
        label="Legacy ScanImage TIFF",
    )
    modern_source = SourceReference(
        source_id="scanimage-modern-1",
        location=modern_path,
        source_type=SourceType.FILE,
        label="Modern ScanImage TIFF",
    )

    assert current_adapter.can_handle(legacy_source) is False
    assert legacy_adapter.can_handle(legacy_source) is True
    assert current_adapter.can_handle(modern_source) is True
    assert legacy_adapter.can_handle(modern_source) is False


def test_miniscope_adapter_inspects_directory_metadata(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "miniscope"
    source_dir.mkdir()
    (source_dir / "metaData.json").write_text("{}", encoding="utf-8")
    (source_dir / "recording.avi").write_bytes(b"fake-avi")
    source = SourceReference(
        source_id="miniscope-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="Miniscope folder",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "NWBFile": {"session_start_time": "2026-04-01T09:00:00-06:00"},
                "Ophys": {
                    "Device": [{"name": "MiniScopeV4"}],
                    "OnePhotonSeries": [{"name": "OnePhotonSeriesMini"}],
                },
            }

    adapter = NeuroConvMiniscopeAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert result.record_type == "neuroconv_miniscope"
    assert result.fields["ophys.miniscope.device_name"].value == "MiniScopeV4"
    assert result.fields["ophys.miniscope.is_one_photon"].value is True


def test_scanbox_adapter_matches_sbx_and_extracts_summary(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.sbx"
    source_path.write_bytes(b"fake-sbx")
    source = SourceReference(
        source_id="scanbox-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Scanbox recording",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "NWBFile": {"session_start_time": "2026-04-02T09:00:00-06:00"},
                "Ophys": {"Device": [{"name": "Scanbox"}], "TwoPhotonSeries": [{"name": "TwoPhotonSeries"}]},
            }

    adapter = NeuroConvScanboxAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["ophys.scanbox.device_name"].value == "Scanbox"


def test_thor_adapter_matches_tiff_with_experiment_xml_and_extracts_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    image_path = tmp_path / "ChanA_001_001_001_001.tif"
    image_path.write_bytes(b"fake-tiff")
    (tmp_path / "Experiment.xml").write_text("<ThorImageExperiment />", encoding="utf-8")
    source = SourceReference(
        source_id="thor-1",
        location=image_path,
        source_type=SourceType.FILE,
        label="Thor TIFF",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "NWBFile": {"session_start_time": "2026-04-01T09:00:00-06:00"},
                "Ophys": {
                    "Device": [{"name": "ThorMicroscope"}],
                    "TwoPhotonSeries": [{"name": "TwoPhotonSeriesDefault"}],
                },
            }

    adapter = NeuroConvThorAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.record_type == "neuroconv_thor"
    assert result.fields["ophys.thor.device_name"].value == "ThorMicroscope"
    assert result.fields["ophys.thor.photon_series_type"].value == "TwoPhotonSeries"


def test_generic_tiff_adapter_requires_config_and_avoids_distinctive_tiff_routes(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "generic.tif"
    source_path.write_bytes(b"fake-tiff")
    source_without_config = SourceReference(
        source_id="tiff-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Generic TIFF",
    )
    source_with_config = SourceReference(
        source_id="tiff-2",
        location=source_path,
        source_type=SourceType.FILE,
        label="Generic TIFF",
        metadata={"neuroconv.interface_kwargs_json": '{"sampling_frequency": 10.0, "num_channels": 1}'},
    )

    monkeypatch.setattr("nwbforge.adapters.supported.imaging.neuroconv._scanimage_matches_current", lambda location: False)
    monkeypatch.setattr("nwbforge.adapters.supported.imaging.neuroconv._scanimage_matches_legacy", lambda location: False)

    class FakeInterface:
        def get_metadata(self):
            return {"NWBFile": {"session_start_time": "2026-04-02T09:00:00-06:00"}, "Ophys": {}}

    adapter = NeuroConvTiffImagingAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    assert adapter.can_handle(source_without_config) is False
    result = adapter.inspect(source_with_config)
    assert result.fields["ophys.tiff.sampling_frequency"].value == 10.0
    assert result.fields["ophys.tiff.file_count"].value == 1
