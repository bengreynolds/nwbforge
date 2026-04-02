import math
import struct
import wave
from pathlib import Path

from nwbforge.adapters import NeuroConvAudioAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def write_wave_file(path: Path) -> None:
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8000)
        frames = [
            struct.pack("<h", int(32767 * math.sin(2 * math.pi * 440 * index / 8000)))
            for index in range(800)
        ]
        wav_file.writeframes(b"".join(frames))


def test_neuroconv_audio_adapter_matches_wav_file(tmp_path: Path) -> None:
    audio_path = tmp_path / "tone.wav"
    write_wave_file(audio_path)

    adapter = NeuroConvAudioAdapter()

    assert (
        adapter.can_handle(
            SourceReference(
                source_id="audio-1",
                location=audio_path,
                source_type=SourceType.FILE,
                label="Reference audio",
            )
        )
        is True
    )


def test_neuroconv_audio_adapter_inspects_audio_count(tmp_path: Path) -> None:
    audio_path = tmp_path / "tone.wav"
    write_wave_file(audio_path)
    source = SourceReference(
        source_id="audio-1",
        location=audio_path,
        source_type=SourceType.FILE,
        label="Reference audio",
    )

    result = NeuroConvAudioAdapter().inspect(source)

    assert result.record_type == "neuroconv_audio"
    assert result.fields["audio.count"].value == 1
    assert result.fields["audio.source_kind"].value == "file"
