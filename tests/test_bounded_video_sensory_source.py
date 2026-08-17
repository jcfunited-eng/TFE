from __future__ import annotations

import subprocess

import pytest

from dsf_ai_service.bounded_video_sensory_source import decode_bounded_video


def _fixture(tmp_path, *, sound: bool) -> bytes:
    destination = tmp_path / ("sounded.mp4" if sound else "silent.mp4")
    command = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=160x90:r=8:d=1",
    ]
    if sound:
        command.extend(
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=16000:duration=1",
                "-shortest",
            ]
        )
    command.extend(["-threads", "1", "-y", str(destination)])
    completed = subprocess.run(command, capture_output=True, check=False)
    if completed.returncode != 0:
        pytest.skip(completed.stderr.decode("utf-8", "replace"))
    return destination.read_bytes()


def test_video_becomes_bounded_light_and_pressure_on_one_clock(tmp_path) -> None:
    source = _fixture(tmp_path, sound=True)
    first = decode_bounded_video(source)
    second = decode_bounded_video(source)

    assert first.hop_count == 4
    assert len(first.frame_sha256s) == first.hop_count
    assert len(first.pcm_s16le) == first.hop_count * 4_000 * 2
    assert any(first.pcm_s16le)
    assert first.frame_sha256s == second.frame_sha256s
    assert first.pcm_sha256 == second.pcm_sha256
    projection = first.public_projection()
    assert projection["semantic_authority"] is False
    assert projection["cognition_authority"] is False


def test_silent_video_carries_true_silence_not_invented_sound(tmp_path) -> None:
    decoded = decode_bounded_video(_fixture(tmp_path, sound=False))

    assert decoded.hop_count == 4
    assert decoded.pcm_s16le == b"\x00" * (4 * 4_000 * 2)


def test_audio_only_source_is_not_mislabeled_as_video(tmp_path) -> None:
    destination = tmp_path / "audio.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-y",
            str(destination),
        ],
        check=True,
    )

    with pytest.raises(ValueError, match="video light decode failed"):
        decode_bounded_video(destination.read_bytes())
