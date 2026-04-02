from pathlib import Path

from nwbforge.adapters import NeuroConvVideoAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def test_neuroconv_video_adapter_matches_mp4_file(tmp_path: Path) -> None:
    video_path = tmp_path / "recording.mp4"
    video_path.write_bytes(b"fake-video")

    adapter = NeuroConvVideoAdapter()

    assert (
        adapter.can_handle(
            SourceReference(
                source_id="video-1",
                location=video_path,
                source_type=SourceType.FILE,
                label="Behavior video",
            )
        )
        is True
    )


def test_neuroconv_video_adapter_inspects_video_fields(tmp_path: Path, monkeypatch) -> None:
    video_path = tmp_path / "recording.mp4"
    video_path.write_bytes(b"fake-video")
    source = SourceReference(
        source_id="video-1",
        location=video_path,
        source_type=SourceType.FILE,
        label="Behavior video",
    )

    class FakeInterface:
        def get_metadata(self):
            return {
                "Behavior": {
                    "ExternalVideos": {
                        "BehaviorVideo": {
                            "description": "Behavior camera.",
                        }
                    }
                }
            }

    adapter = NeuroConvVideoAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert result.record_type == "neuroconv_video"
    assert result.fields["video.count"].value == 1
    assert result.fields["video.source_kind"].value == "file"
    assert result.fields["video.video_name"].value == "BehaviorVideo"
