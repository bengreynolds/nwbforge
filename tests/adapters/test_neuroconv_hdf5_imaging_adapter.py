from pathlib import Path

from nwbforge.adapters import NeuroConvHdf5ImagingAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def test_neuroconv_hdf5_imaging_adapter_matches_h5_file(tmp_path: Path) -> None:
    image_path = tmp_path / "recording.h5"
    image_path.write_bytes(b"fake-hdf5")

    adapter = NeuroConvHdf5ImagingAdapter()

    assert (
        adapter.can_handle(
            SourceReference(
                source_id="hdf5-1",
                location=image_path,
                source_type=SourceType.FILE,
                label="HDF5 imaging",
            )
        )
        is True
    )


def test_neuroconv_hdf5_imaging_adapter_inspects_ophys_fields(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "recording.h5"
    image_path.write_bytes(b"fake-hdf5")
    source = SourceReference(
        source_id="hdf5-1",
        location=image_path,
        source_type=SourceType.FILE,
        label="HDF5 imaging",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "Ophys": {
                    "ImagingPlane": [{"name": "Plane1"}],
                }
            }

    adapter = NeuroConvHdf5ImagingAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert result.record_type == "neuroconv_hdf5_imaging"
    assert result.fields["ophys.hdf5.source_format"].value == "h5"
    assert result.fields["ophys.hdf5.mov_field"].value == "mov"
    assert result.fields["ophys.hdf5.has_imaging_plane_metadata"].value is True
