"""Deterministic bounded video decoding for Guala's existing senses.

The result is sampled light plus mono pressure on one 250 ms clock.  It does
not inspect captions, names, objects, speech, or meaning.  Original bytes are
preserved separately by :mod:`bounded_source_media_store` before this decoder
is allowed to run.
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dsf_ai_service.bounded_source_media_store import MAX_SOURCE_MEDIA_BYTES


VIDEO_SAMPLE_RATE_HZ = 16_000
VIDEO_HOP_MILLISECONDS = 250
VIDEO_MAX_HOPS = 24
VIDEO_FRAME_WIDTH = 768
VIDEO_FRAME_HEIGHT = 432
VIDEO_MAX_DECODED_FRAME_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class BoundedVideoSensorySource:
    source_bytes_sha256: str
    frame_png_bytes: tuple[bytes, ...]
    frame_sha256s: tuple[str, ...]
    pcm_s16le: bytes
    pcm_sha256: str
    sample_rate_hz: int
    hop_milliseconds: int

    @property
    def hop_count(self) -> int:
        return len(self.frame_png_bytes)

    def public_projection(self) -> dict[str, object]:
        return {
            "cognition_authority": False,
            "frame_sha256s": list(self.frame_sha256s),
            "hop_count": self.hop_count,
            "hop_milliseconds": self.hop_milliseconds,
            "pcm_sample_count": len(self.pcm_s16le) // 2,
            "pcm_sha256": self.pcm_sha256,
            "sample_rate_hz": self.sample_rate_hz,
            "semantic_authority": False,
            "source_bytes_sha256": self.source_bytes_sha256,
        }


def _run(command: list[str], description: str) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"{description} failed: {type(error).__name__}") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()[:240]
        raise ValueError(f"{description} failed: {detail or completed.returncode}")
    return completed


def decode_bounded_video(
    source_bytes: bytes,
    *,
    ffmpeg_binary: str = "ffmpeg",
    ffprobe_binary: str = "ffprobe",
) -> BoundedVideoSensorySource:
    """Decode at most six seconds onto the mounted audiovisual timebase."""

    if (
        not isinstance(source_bytes, bytes)
        or not source_bytes
        or len(source_bytes) > MAX_SOURCE_MEDIA_BYTES
    ):
        raise ValueError("video source bytes exceed their bound")
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    with tempfile.TemporaryDirectory(prefix="guala-video-") as directory_name:
        directory = Path(directory_name)
        source_path = directory / "source.bin"
        frames_path = directory / "frames"
        audio_path = directory / "audio.pcm"
        source_path.write_bytes(source_bytes)
        frames_path.mkdir()
        frame_pattern = frames_path / "%03d.png"
        frame_filter = (
            f"fps={1000 // VIDEO_HOP_MILLISECONDS},"
            f"scale={VIDEO_FRAME_WIDTH}:{VIDEO_FRAME_HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={VIDEO_FRAME_WIDTH}:{VIDEO_FRAME_HEIGHT}:"
            "(ow-iw)/2:(oh-ih)/2:black,setsar=1"
        )
        _run(
            [
                ffmpeg_binary,
                "-nostdin",
                "-v",
                "error",
                "-threads",
                "1",
                "-i",
                str(source_path),
                "-map",
                "0:v:0",
                "-vf",
                frame_filter,
                "-frames:v",
                str(VIDEO_MAX_HOPS),
                str(frame_pattern),
            ],
            "video light decode",
        )
        frame_files = tuple(sorted(frames_path.glob("*.png")))
        if not 0 < len(frame_files) <= VIDEO_MAX_HOPS:
            raise ValueError("video produced no bounded light frames")
        frames = tuple(path.read_bytes() for path in frame_files)
        if sum(len(frame) for frame in frames) > VIDEO_MAX_DECODED_FRAME_BYTES:
            raise ValueError("decoded video light exceeds its byte bound")
        probe = _run(
            [
                ffprobe_binary,
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                str(source_path),
            ],
            "video sound probe",
        )
        sample_count = (
            len(frames)
            * VIDEO_SAMPLE_RATE_HZ
            * VIDEO_HOP_MILLISECONDS
            // 1000
        )
        if probe.stdout.strip():
            duration = len(frames) * VIDEO_HOP_MILLISECONDS / 1000
            _run(
                [
                    ffmpeg_binary,
                    "-nostdin",
                    "-v",
                    "error",
                    "-threads",
                    "1",
                    "-i",
                    str(source_path),
                    "-map",
                    "0:a:0",
                    "-af",
                    "apad",
                    "-ac",
                    "1",
                    "-ar",
                    str(VIDEO_SAMPLE_RATE_HZ),
                    "-t",
                    f"{duration:.6f}",
                    "-f",
                    "s16le",
                    str(audio_path),
                ],
                "video pressure decode",
            )
            pcm = audio_path.read_bytes()
            expected_bytes = sample_count * 2
            if len(pcm) < expected_bytes:
                pcm += b"\x00" * (expected_bytes - len(pcm))
            pcm = pcm[:expected_bytes]
        else:
            pcm = b"\x00" * (sample_count * 2)
    return BoundedVideoSensorySource(
        source_bytes_sha256=source_digest,
        frame_png_bytes=frames,
        frame_sha256s=tuple(hashlib.sha256(frame).hexdigest() for frame in frames),
        pcm_s16le=pcm,
        pcm_sha256=hashlib.sha256(pcm).hexdigest(),
        sample_rate_hz=VIDEO_SAMPLE_RATE_HZ,
        hop_milliseconds=VIDEO_HOP_MILLISECONDS,
    )
