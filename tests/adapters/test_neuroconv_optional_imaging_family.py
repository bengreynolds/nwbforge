from pathlib import Path

from nwbforge.adapters import (
    NeuroConvMicroManagerTiffAdapter,
    NeuroConvMiniscopeAdapter,
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
