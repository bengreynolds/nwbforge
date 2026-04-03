from pathlib import Path

import pandas as pd

from nwbforge.adapters import NeuroConvLightningPoseAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def write_lightningpose_csv(path: Path) -> None:
    dataframe = pd.DataFrame(
        [
            [0, 1.0, 2.0, 0.95],
            [1, 1.5, 2.5, 0.97],
        ],
        columns=pd.MultiIndex.from_tuples(
            [
                ("frame", "frame", "index"),
                ("LightningPose", "nose", "x"),
                ("LightningPose", "nose", "y"),
                ("LightningPose", "nose", "likelihood"),
            ]
        ),
    )
    dataframe.to_csv(path, index=False)


def test_neuroconv_lightningpose_adapter_matches_csv_with_video_sidecar(tmp_path: Path) -> None:
    csv_path = tmp_path / "pose.csv"
    write_lightningpose_csv(csv_path)
    (tmp_path / "pose.mp4").write_bytes(b"fake-video")

    adapter = NeuroConvLightningPoseAdapter()

    assert (
        adapter.can_handle(
            SourceReference(
                source_id="lightningpose-1",
                location=csv_path,
                source_type=SourceType.FILE,
                label="LightningPose predictions",
            )
        )
        is True
    )


def test_neuroconv_lightningpose_adapter_inspects_pose_fields(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "pose.csv"
    write_lightningpose_csv(csv_path)
    (tmp_path / "pose.mp4").write_bytes(b"fake-video")
    source = SourceReference(
        source_id="lightningpose-1",
        location=csv_path,
        source_type=SourceType.FILE,
        label="LightningPose predictions",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "Behavior": {
                    "PoseEstimation": {
                        "name": "PoseEstimation",
                        "camera_name": "CameraPoseEstimation",
                    }
                }
            }

    adapter = NeuroConvLightningPoseAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert result.record_type == "neuroconv_lightningpose"
    assert result.fields["behavior.lightningpose.source_format"].value == "csv"
    assert result.fields["behavior.lightningpose.keypoint_count"].value == 1
    assert result.fields["behavior.lightningpose.has_original_video"].value is True
