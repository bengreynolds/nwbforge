from pathlib import Path

import pandas as pd

from nwbforge.adapters import NeuroConvDeepLabCutAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def write_deeplabcut_csv(path: Path) -> None:
    columns = pd.MultiIndex.from_tuples(
        [
            ("scorer", "nose", "x"),
            ("scorer", "nose", "y"),
            ("scorer", "nose", "likelihood"),
        ],
        names=["scorer", "bodyparts", "coords"],
    )
    dataframe = pd.DataFrame([[1.0, 2.0, 0.9], [1.5, 2.5, 0.95]], columns=columns)
    dataframe.to_csv(path)


def test_neuroconv_deeplabcut_adapter_matches_csv_file(tmp_path: Path) -> None:
    dlc_path = tmp_path / "deeplabcut.csv"
    write_deeplabcut_csv(dlc_path)

    adapter = NeuroConvDeepLabCutAdapter()

    assert (
        adapter.can_handle(
            SourceReference(
                source_id="dlc-1",
                location=dlc_path,
                source_type=SourceType.FILE,
                label="DeepLabCut pose data",
            )
        )
        is True
    )


def test_neuroconv_deeplabcut_adapter_inspects_pose_fields(tmp_path: Path) -> None:
    dlc_path = tmp_path / "deeplabcut.csv"
    write_deeplabcut_csv(dlc_path)
    source = SourceReference(
        source_id="dlc-1",
        location=dlc_path,
        source_type=SourceType.FILE,
        label="DeepLabCut pose data",
    )

    result = NeuroConvDeepLabCutAdapter().inspect(source)

    assert result.record_type == "neuroconv_deeplabcut"
    assert result.fields["behavior.deeplabcut.source_format"].value == "csv"
    assert result.fields["behavior.deeplabcut.bodypart_count"].value == 1
