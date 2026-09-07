from __future__ import annotations

import hashlib
import math
import struct

import pytest

from dsf_ai_service.guala_cochlea import (
    CHANNELS_PER_EAR,
    EAR_COUNT,
    HOP_SAMPLES,
    OBSERVATION_SAMPLES,
    SAMPLE_RATE_HZ,
    one_self_hearing_hop,
)


def _packed(samples: tuple[int, ...]) -> bytes:
    return struct.pack(f"<{len(samples)}h", *samples)


def _result_sha256(samples: tuple[int, ...]) -> str:
    result = one_self_hearing_hop(_packed(samples))
    return hashlib.sha256(repr(result).encode("utf-8")).hexdigest()


def test_one_hop_matches_protected_old_shell_transduction_vectors() -> None:
    signals = {
        "silence": (
            (0,) * HOP_SAMPLES,
            "7c1e0af394956fa5f7112fd21d71c83f8e0f9ca21d9b366fc73a6bed702d1181",
        ),
        "impulse": (
            (32_767,) + (0,) * (HOP_SAMPLES - 1),
            "a646c3b20a38aabcc77c7fe39b127450bea1da933b5b93c000168d63c0386804",
        ),
        "tone-440": (
            tuple(
                round(12_000 * math.sin(2 * math.pi * 440 * index / SAMPLE_RATE_HZ))
                for index in range(HOP_SAMPLES)
            ),
            "b2e4eebb44bcb4fe6c92e98b6c0440a0355a14d4bb1ce6c9dbd8082da36cf01f",
        ),
    }
    for samples, expected_sha256 in signals.values():
        assert _result_sha256(samples) == expected_sha256


def test_one_hop_has_exact_clock_anatomy_and_consumption_boundary() -> None:
    samples = tuple(((index * 7_919) % 65_536) - 32_768 for index in range(4_500))
    times, legacy, cochleae, consumed = one_self_hearing_hop(_packed(samples))

    assert consumed == HOP_SAMPLES
    assert len(times) == HOP_SAMPLES // OBSERVATION_SAMPLES + 1
    assert len(legacy) == len(times)
    assert len(cochleae) == CHANNELS_PER_EAR * EAR_COUNT
    assert all(len(channel) == len(times) for channel in cochleae)
    assert cochleae[:CHANNELS_PER_EAR] == cochleae[CHANNELS_PER_EAR:]
    assert hashlib.sha256(
        repr((times, legacy, cochleae, consumed)).encode("utf-8")
    ).hexdigest() == (
        "bf56698e9e6ee1b992e173250c3b5e65b06f1c00010ba78a38e70eab4bbe9af0"
    )


def test_one_hop_refuses_empty_odd_width_and_non_bytes_pressure() -> None:
    with pytest.raises(ValueError, match="empty"):
        one_self_hearing_hop(b"")
    with pytest.raises(ValueError, match="signed-16 width"):
        one_self_hearing_hop(b"\x00")
    with pytest.raises(ValueError, match="empty"):
        one_self_hearing_hop(bytearray(b"\x00\x00"))  # type: ignore[arg-type]
