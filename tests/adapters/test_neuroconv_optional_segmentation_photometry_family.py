from pathlib import Path
from importlib import import_module

import pytest

from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


segmentation_module = import_module("nwbforge.adapters.supported.segmentation.neuroconv")
fiber_photometry_module = import_module("nwbforge.adapters.supported.fiber_photometry.neuroconv")

NeuroConvCaimanSegmentationAdapter = getattr(segmentation_module, "NeuroConvCaimanSegmentationAdapter")
NeuroConvCnmfeSegmentationAdapter = getattr(segmentation_module, "NeuroConvCnmfeSegmentationAdapter")
NeuroConvExtractSegmentationAdapter = getattr(segmentation_module, "NeuroConvExtractSegmentationAdapter")
NeuroConvInscopixSegmentationAdapter = getattr(segmentation_module, "NeuroConvInscopixSegmentationAdapter")
NeuroConvSuite2pSegmentationAdapter = getattr(segmentation_module, "NeuroConvSuite2pSegmentationAdapter")
NeuroConvTdtFiberPhotometryAdapter = getattr(fiber_photometry_module, "NeuroConvTdtFiberPhotometryAdapter", None)


def test_caiman_segmentation_prefers_distinctive_hdf5_names(tmp_path: Path) -> None:
    source_path = tmp_path / "caiman_estimates.h5"
    source_path.write_bytes(b"fake-caiman")

    adapter = NeuroConvCaimanSegmentationAdapter()

    assert adapter.can_handle(
        SourceReference(
            source_id="caiman-1",
            location=source_path,
            source_type=SourceType.FILE,
            label="Caiman estimates",
        )
    )


def test_cnmfe_segmentation_prefers_cnmfe_style_mat_names(tmp_path: Path) -> None:
    source_path = tmp_path / "session_cnmfe_output.mat"
    source_path.write_bytes(b"fake-cnmfe")

    adapter = NeuroConvCnmfeSegmentationAdapter()

    assert adapter.can_handle(
        SourceReference(
            source_id="cnmfe-1",
            location=source_path,
            source_type=SourceType.FILE,
            label="CNMFE output",
        )
    )


def test_extract_segmentation_requires_sampling_frequency(tmp_path: Path) -> None:
    source_path = tmp_path / "extract_output.mat"
    source_path.write_bytes(b"fake-extract")
    source_without_config = SourceReference(
        source_id="extract-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="EXTRACT output",
    )
    source_with_config = SourceReference(
        source_id="extract-2",
        location=source_path,
        source_type=SourceType.FILE,
        label="EXTRACT output",
        metadata={"neuroconv.interface_kwargs_json": '{"sampling_frequency": 30.0}'},
    )

    adapter = NeuroConvExtractSegmentationAdapter()

    assert adapter.can_handle(source_without_config) is False
    assert adapter.can_handle(source_with_config) is True


def test_inscopix_segmentation_can_use_explicit_hint(tmp_path: Path) -> None:
    source_path = tmp_path / "session_cellset.isxd"
    source_path.write_text("isxd", encoding="utf-8")

    adapter = NeuroConvInscopixSegmentationAdapter()

    assert adapter.can_handle(
        SourceReference(
            source_id="inscopix-seg-1",
            location=source_path,
            source_type=SourceType.FILE,
            label="Inscopix segmentation",
            adapter_hint=adapter.adapter_id,
        )
    )


def test_suite2p_segmentation_matches_distinctive_folder(tmp_path: Path) -> None:
    source_dir = tmp_path / "suite2p"
    source_dir.mkdir()
    for filename in ("ops.npy", "stat.npy", "iscell.npy"):
        (source_dir / filename).write_bytes(b"npy")

    adapter = NeuroConvSuite2pSegmentationAdapter()

    assert adapter.can_handle(
        SourceReference(
            source_id="suite2p-1",
            location=source_dir,
            source_type=SourceType.DIRECTORY,
            label="Suite2p folder",
        )
    )


def test_tdt_fiber_photometry_is_hint_driven(tmp_path: Path) -> None:
    if NeuroConvTdtFiberPhotometryAdapter is None:
        pytest.skip("TDT fiber photometry optional dependencies are not installed in this environment.")

    source_dir = tmp_path / "tdt-block"
    source_dir.mkdir()
    (source_dir / "block.Tsq").write_text("tdt", encoding="utf-8")

    adapter = NeuroConvTdtFiberPhotometryAdapter()
    source = SourceReference(
        source_id="tdt-fp-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="TDT fiber photometry",
        adapter_hint=adapter.adapter_id,
    )

    assert adapter.can_handle(source) is True
