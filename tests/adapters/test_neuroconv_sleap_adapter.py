from pathlib import Path

from nwbforge.adapters import NeuroConvSLEAPAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def test_neuroconv_sleap_adapter_matches_slp_file(tmp_path: Path) -> None:
    sleap_path = tmp_path / "tracking.slp"
    sleap_path.write_bytes(b"fake-slp")

    adapter = NeuroConvSLEAPAdapter()

    assert (
        adapter.can_handle(
            SourceReference(
                source_id="sleap-1",
                location=sleap_path,
                source_type=SourceType.FILE,
                label="SLEAP pose data",
            )
        )
        is True
    )


def test_neuroconv_sleap_adapter_inspects_pose_fields(tmp_path: Path, monkeypatch) -> None:
    sleap_path = tmp_path / "tracking.slp"
    sleap_path.write_bytes(b"fake-slp")
    source = SourceReference(
        source_id="sleap-1",
        location=sleap_path,
        source_type=SourceType.FILE,
        label="SLEAP pose data",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "PoseEstimation": {
                    "PoseEstimationContainers": {
                        "SLEAPPose": {
                            "name": "SLEAPPose",
                        }
                    }
                }
            }

    adapter = NeuroConvSLEAPAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert result.record_type == "neuroconv_sleap"
    assert result.fields["behavior.sleap.source_format"].value == "slp"
    assert result.fields["behavior.sleap.pose_container_count"].value == 1
    assert result.fields["behavior.sleap.pose_container_name"].value == "SLEAPPose"
