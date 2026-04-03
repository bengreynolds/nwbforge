from pathlib import Path

from nwbforge.adapters import NeuroConvScanImageAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def test_neuroconv_scanimage_adapter_matches_tiff_file(tmp_path: Path) -> None:
    image_path = tmp_path / "scanimage_00001.tif"
    image_path.write_bytes(b"II*\x00")

    adapter = NeuroConvScanImageAdapter()

    assert (
        adapter.can_handle(
            SourceReference(
                source_id="scanimage-1",
                location=image_path,
                source_type=SourceType.FILE,
                label="ScanImage TIFF",
            )
        )
        is True
    )


def test_neuroconv_scanimage_adapter_inspects_ophys_fields(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "scanimage_00001.tif"
    image_path.write_bytes(b"II*\x00")
    source = SourceReference(
        source_id="scanimage-1",
        location=image_path,
        source_type=SourceType.FILE,
        label="ScanImage TIFF",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "NWBFile": {"session_start_time": "2026-04-01T09:00:00-06:00"},
                "Ophys": {"TwoPhotonSeries": [{"name": "TwoPhotonSeriesChannel1"}]},
            }

    adapter = NeuroConvScanImageAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert result.record_type == "neuroconv_scanimage"
    assert result.fields["ophys.scanimage.source_format"].value == "scanimage_tiff"
    assert result.fields["ophys.scanimage.file_count"].value == 1
    assert result.fields["ophys.scanimage.photon_series_type"].value == "TwoPhotonSeries"
