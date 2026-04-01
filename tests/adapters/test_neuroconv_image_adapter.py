from pathlib import Path

from PIL import Image

from nwbforge.adapters import NeuroConvImageAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def test_neuroconv_image_adapter_matches_png_file(tmp_path: Path) -> None:
    image_path = tmp_path / "frame.png"
    Image.new("RGB", (4, 4), color=(255, 0, 0)).save(image_path)

    adapter = NeuroConvImageAdapter()

    assert (
        adapter.can_handle(
            SourceReference(
                source_id="image-1",
                location=image_path,
                source_type=SourceType.FILE,
                label="Reference image",
            )
        )
        is True
    )


def test_neuroconv_image_adapter_inspects_image_count(tmp_path: Path) -> None:
    image_path = tmp_path / "frame.png"
    Image.new("RGB", (4, 4), color=(0, 255, 0)).save(image_path)
    source = SourceReference(
        source_id="image-1",
        location=image_path,
        source_type=SourceType.FILE,
        label="Reference image",
    )

    result = NeuroConvImageAdapter().inspect(source)

    assert result.record_type == "neuroconv_image"
    assert result.fields["images.count"].value == 1
    assert result.fields["images.images_location"].value == "acquisition"
