from __future__ import annotations

import subprocess
import sys
import threading
import wave
from io import BytesIO
import numpy as np
import pytest

import dsf_ai_service.substrate_runner as substrate_runner
from dsf_ai_service.substrate.ring_buffer import (
    InputRing,
    InputRingCapacityError,
)


def test_webm_decoder_places_duration_and_byte_walls_inside_ffmpeg(
    monkeypatch,
) -> None:
    observed = {}
    pcm = b"\x00\x00" * (
        substrate_runner._AUDITORY_PCM_SAMPLE_RATE_HZ
        * substrate_runner._AUDITORY_PCM_MAX_SECONDS
    )
    real_popen = subprocess.Popen

    def bounded_popen(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return real_popen(
            [
                sys.executable,
                "-c",
                f"import sys; sys.stdout.buffer.write(b'\\0' * {len(pcm)})",
            ],
            **kwargs,
        )

    monkeypatch.setattr(substrate_runner.subprocess, "Popen", bounded_popen)
    wav_bytes = substrate_runner._webm_to_wav_bytes(b"bounded-webm")

    assert wav_bytes is not None
    with wave.open(BytesIO(wav_bytes), "rb") as stream:
        assert stream.getframerate() == 16_000
        assert stream.getnchannels() == 1
        assert stream.getsampwidth() == 2
        assert stream.getnframes() == 16_000 * 8
    command = observed["command"]
    assert command[command.index("-t") + 1] == "8.0000625"
    assert command[command.index("-fs") + 1] == str(
        substrate_runner._AUDITORY_PCM_MAX_BYTES
        + substrate_runner._AUDITORY_PCM_DECODE_SENTINEL_BYTES
    )
    assert observed["kwargs"]["stdout"] == subprocess.PIPE
    assert observed["kwargs"]["stderr"] == subprocess.DEVNULL


def test_webm_decoder_rejects_the_one_sample_overrun_sentinel(
    monkeypatch,
) -> None:
    overrun = b"\x00" * (
        substrate_runner._AUDITORY_PCM_MAX_BYTES
        + substrate_runner._AUDITORY_PCM_DECODE_SENTINEL_BYTES
    )
    real_popen = subprocess.Popen

    def overrun_popen(_command, **kwargs):
        return real_popen(
            [
                sys.executable,
                "-c",
                f"import sys; sys.stdout.buffer.write(b'\\0' * {len(overrun)})",
            ],
            **kwargs,
        )

    monkeypatch.setattr(
        substrate_runner.subprocess,
        "Popen",
        overrun_popen,
    )
    assert substrate_runner._webm_to_wav_bytes(b"too-long") is None


def test_input_ring_fails_before_slot_overwrite_and_resumes_after_drain() -> None:
    ring = InputRing(size=4, max_pending_bytes=100_000)
    assert [
        ring.publish("wake_signal", "system", marker=f"event-{index}")
        for index in range(4)
    ] == [0, 1, 2, 3]

    with pytest.raises(InputRingCapacityError, match="slot capacity"):
        ring.publish("wake_signal", "system", marker="must-not-overwrite")

    assert ring.pending == 4
    assert ring.rejected_events == 1
    first = ring.drain(max_n=2)
    assert [event["seq"] for event in first] == [0, 1]
    assert ring.publish("wake_signal", "system", reason="resume") == 4
    remaining = ring.drain(max_n=4)
    assert [event["seq"] for event in remaining] == [2, 3, 4]
    assert ring.pending == 0
    assert ring.pending_transport_bytes == 0


def test_ring_write_handler_reports_capacity_refusal_without_false_ack() -> None:
    previous = substrate_runner._input_ring
    substrate_runner._input_ring = InputRing(size=1, max_pending_bytes=10_000)
    try:
        admitted = substrate_runner.handle_ring_write({
            "kind": "sight_sequence",
            "source": "camera_stream",
            "data": {"frames": ["first"]},
        })
        refused = substrate_runner.handle_ring_write({
            "kind": "sight_sequence",
            "source": "camera_stream",
            "data": {"frames": ["second"]},
        })
    finally:
        substrate_runner._input_ring = previous

    assert admitted == {
        "ok": True,
        "transport_receipt": {
            "kind": "sight_sequence",
            "sequence": 0,
        },
    }
    assert refused["ok"] is False
    assert "slot capacity" in refused["error"]
    assert refused["input_pending"] == 1
    assert refused["input_rejected_events"] == 1


def test_input_ring_enforces_pending_transport_bytes_without_mutation() -> None:
    ring = InputRing(size=8, max_pending_bytes=220)
    first_seq = ring.publish("admin_command", "wc", command="status")
    admitted_bytes = ring.pending_transport_bytes

    with pytest.raises(InputRingCapacityError, match="transport-byte capacity"):
        ring.publish("sound_window", "joe", audio_b64="A" * 500)

    assert first_seq == 0
    assert ring.pending == 1
    assert ring.pending_transport_bytes == admitted_bytes
    assert ring._claim_seq == 1
    assert ring.drain() == [
        {
            "seq": 0,
            "kind": "admin_command",
            "source": "wc",
            "data": {"command": "status"},
        }
    ]
    assert ring.pending_transport_bytes == 0


def test_input_ring_multiwriter_admission_never_overwrites() -> None:
    ring = InputRing(size=8, max_pending_bytes=100_000)
    barrier = threading.Barrier(17)
    accepted = []
    rejected = []
    result_lock = threading.Lock()

    def publish(index):
        barrier.wait()
        try:
            result = ring.publish(
                "experience_bundle", f"writer-{index}", value=index
            )
        except InputRingCapacityError:
            with result_lock:
                rejected.append(index)
        else:
            with result_lock:
                accepted.append(result)

    threads = [threading.Thread(target=publish, args=(index,)) for index in range(16)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()

    assert sorted(accepted) == list(range(8))
    assert len(rejected) == 8
    drained = ring.drain(max_n=8)
    assert [event["seq"] for event in drained] == list(range(8))
    assert len({event["source"] for event in drained}) == 8


def test_input_ring_recovers_a_legacy_lapped_cursor_instead_of_stalling() -> None:
    ring = InputRing(size=4, max_pending_bytes=100_000)
    with ring._state_lock:
        ring._claim_seq = 6
        ring._read_seq = 0
        ring._pending_transport_bytes = 0
        for seq in range(2, 6):
            index = seq & ring._mask
            event = {
                "seq": seq,
                "kind": "rest_signal",
                "source": "legacy",
                "data": {"value": seq},
            }
            transport_bytes = ring._transport_bytes(
                event["kind"], event["source"], event["data"]
            )
            ring._data[index] = event
            ring._slot_transport_bytes[index] = transport_bytes
            ring._pending_transport_bytes += transport_bytes
            ring._seq_array[index] = np.uint64(seq)

    drained = ring.drain(max_n=4)
    assert [event["seq"] for event in drained] == [2, 3, 4, 5]
    assert ring.pending == 0
    assert ring.pending_transport_bytes == 0
    assert ring.overrun_recoveries == 1
