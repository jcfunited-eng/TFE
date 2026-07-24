from __future__ import annotations

import math
import struct
import wave
from io import BytesIO

import numpy as np
import pytest

from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_CHUNK_SAMPLES,
    PCM_RING_BYTES,
    PCM_SAMPLE_RATE_HZ,
    pcm_s16le_wav,
)
from dsf_ai_service.substrate.embodiment_world import MAX_VOCAL_SAMPLE_COUNT
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    MAX_EMITTED_PCM_SAMPLES,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_GAMMATONE_CONTINUATION_SCHEMA,
    AuditoryFullFieldStream,
    AuditoryFullFieldStreamRegistry,
    AuditoryRephaseGrid,
    transduce_auditory_full_field,
    transduce_rephased_auditory_interval,
)
import dsf_ai_service.substrate.senses.auditory_full_field_provider as provider


def _pcm(sample_count: int, *, offset: int = 0) -> bytes:
    values = tuple(
        int(12_000 * math.sin(2 * math.pi * 317 * (offset + index) / 16_000))
        for index in range(sample_count)
    )
    return struct.pack(f"<{len(values)}h", *values)


def _field(pcm: bytes):
    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float64) / 32768.0
    return transduce_auditory_full_field(
        samples, sample_rate_hz=PCM_SAMPLE_RATE_HZ
    )


def test_live_transport_window_is_one_physical_vocal_action() -> None:
    assert PCM_CHUNK_SAMPLES == 80_000
    assert MAX_VOCAL_SAMPLE_COUNT == PCM_CHUNK_SAMPLES
    assert MAX_EMITTED_PCM_SAMPLES == PCM_CHUNK_SAMPLES


def test_contiguous_chunks_reconstruct_identical_unsplit_auditory_field() -> None:
    registry = AuditoryPCMStreamRegistry()
    opened = registry.open()
    stream_id = opened["stream_id"]
    complete = _pcm(96_000)
    cuts = (17_333, 61_777, 96_000)
    start = 0
    accepted = None
    for sequence, end in enumerate(cuts):
        accepted = registry.accept(
            stream_id=stream_id,
            sequence=sequence,
            first_sample_index=start,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=complete[start * 2:end * 2],
        )
        accepted.receipt.verify()
        start = end

    assert accepted is not None
    assert accepted.bounded_pcm_tail == complete
    assert accepted.bounded_tail_first_sample_index == 0
    assert _field(accepted.bounded_pcm_tail) == _field(complete)


def test_rephased_interval_preserves_filter_history_and_localizes_hops(
    monkeypatch,
) -> None:
    monkeypatch.setattr(provider, "_native_gammatone_stream", None)
    prefix_samples = 333
    interval_samples = 640
    complete = _pcm(
        prefix_samples + interval_samples,
    )

    observed = transduce_rephased_auditory_interval(
        complete,
        source_sample_start=prefix_samples,
        input_sample_count=interval_samples,
    )
    reset = _field(complete[prefix_samples * 2:])

    assert observed.source_first_sample_index == prefix_samples
    assert observed.input_sample_count == interval_samples
    assert observed.frame_count == interval_samples // 160
    assert all(
        channel.carrier_phase_advance_turns[0] == 0.0
        for channel in observed.channels
    )
    assert any(
        actual.pressure_envelope_full_scale
        != restarted.pressure_envelope_full_scale
        for actual, restarted in zip(
            observed.channels, reset.channels, strict=True
        )
    )


def test_rephased_interval_at_genesis_is_the_canonical_field() -> None:
    complete = _pcm(640)

    assert transduce_rephased_auditory_interval(
        complete,
        source_sample_start=0,
        input_sample_count=640,
    ) == _field(complete)


def test_rephase_seed_preserves_history_across_transport_chunks() -> None:
    complete = _pcm(4_800)
    cut = 1_933
    registry = AuditoryPCMStreamRegistry()
    stream_id = registry.open()["stream_id"]
    stream = AuditoryFullFieldStream()
    first = registry.accept(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=1_000_000_000,
        pcm_s16le=complete[:cut * 2],
    )
    stream.advance(first.pcm_s16le, first.receipt)
    second = registry.accept(
        stream_id=stream_id,
        sequence=1,
        first_sample_index=cut,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=1_000_000_000,
        pcm_s16le=complete[cut * 2:],
    )
    capture, _receipt = stream.advance(
        second.pcm_s16le,
        second.receipt,
    )
    assert capture.rephase_seed is not None

    from_chunk = AuditoryRephaseGrid(
        second.pcm_s16le,
        candidate_hop_start=2_080,
        seed=capture.rephase_seed,
    ).capture(
        source_sample_start=2_111,
        input_sample_count=640,
    )
    from_genesis = AuditoryRephaseGrid(
        complete,
        candidate_hop_start=2_080,
    ).capture(
        source_sample_start=2_111,
        input_sample_count=640,
    )

    assert from_chunk == from_genesis


@pytest.mark.parametrize(
    ("sequence", "first_sample_index"),
    ((0, 10), (1, 0), (2, 32), (0, 0)),
)
def test_gap_duplicate_reorder_or_overlap_closes_epoch(
    sequence: int, first_sample_index: int
) -> None:
    registry = AuditoryPCMStreamRegistry()
    stream_id = registry.open()["stream_id"]
    first = _pcm(32)
    registry.accept(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=1_000_000_000,
        pcm_s16le=first,
    )
    with pytest.raises(ValueError, match="discontinuous"):
        registry.accept(
            stream_id=stream_id,
            sequence=sequence,
            first_sample_index=first_sample_index,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=_pcm(32, offset=32),
        )
    with pytest.raises(ValueError, match="unknown or expired"):
        registry.accept(
            stream_id=stream_id,
            sequence=1,
            first_sample_index=32,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=_pcm(32, offset=32),
        )
    assert registry.status()["active_streams"] == 0


def test_ring_is_bounded_and_preserves_sample_alignment() -> None:
    registry = AuditoryPCMStreamRegistry()
    stream_id = registry.open()["stream_id"]
    first = _pcm(80_000)
    second = _pcm(80_000, offset=80_000)
    registry.accept(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=1_000_000_000,
        pcm_s16le=first,
    )
    accepted = registry.accept(
        stream_id=stream_id,
        sequence=1,
        first_sample_index=80_000,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=1_000_000_000,
        pcm_s16le=second,
    )

    assert len(accepted.bounded_pcm_tail) == PCM_RING_BYTES
    assert accepted.bounded_tail_first_sample_index == 32_000
    assert accepted.bounded_pcm_tail == (first + second)[-PCM_RING_BYTES:]
    assert registry.status()["retained_pcm_bytes"] == PCM_RING_BYTES


def test_expired_stream_cannot_be_resumed() -> None:
    now = [0.0]
    registry = AuditoryPCMStreamRegistry(
        clock=lambda: now[0], idle_seconds=5
    )
    stream_id = registry.open()["stream_id"]
    now[0] = 6.0
    with pytest.raises(ValueError, match="unknown or expired"):
        registry.accept(
            stream_id=stream_id,
            sequence=0,
            first_sample_index=0,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=_pcm(32),
        )


def test_invalid_rate_shape_and_oversize_fail_before_state_mutation() -> None:
    registry = AuditoryPCMStreamRegistry()
    stream_id = registry.open()["stream_id"]
    with pytest.raises(ValueError, match="16 kHz"):
        registry.accept(
            stream_id=stream_id,
            sequence=0,
            first_sample_index=0,
            sample_rate_hz=48_000,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=b"\0\0",
        )
    with pytest.raises(ValueError, match="signed 16-bit"):
        registry.accept(
            stream_id=stream_id,
            sequence=0,
            first_sample_index=0,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=b"\0",
        )
    with pytest.raises(ValueError, match="sample boundary"):
        registry.accept(
            stream_id=stream_id,
            sequence=0,
            first_sample_index=0,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=b"\0\0" * (8 * PCM_SAMPLE_RATE_HZ + 1),
        )
    accepted = registry.accept(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=1_000_000_000,
        pcm_s16le=b"\0\0" * 32,
    )
    assert accepted.receipt.sequence == 0


def test_pcm_wav_wrapper_is_lossless_and_canonical() -> None:
    pcm = _pcm(321)
    encoded = pcm_s16le_wav(pcm)
    with wave.open(BytesIO(encoded), "rb") as stream:
        assert stream.getnchannels() == 1
        assert stream.getsampwidth() == 2
        assert stream.getframerate() == PCM_SAMPLE_RATE_HZ
        assert stream.getnframes() == 321
        assert stream.readframes(321) == pcm


def test_stateful_cochlea_is_exactly_invariant_to_transport_partition(
    monkeypatch,
) -> None:
    monkeypatch.setattr(provider, "_native_gammatone_field", None)
    monkeypatch.setattr(provider, "_native_gammatone_stream", None)
    registry = AuditoryPCMStreamRegistry()
    stream_id = registry.open()["stream_id"]
    stream = AuditoryFullFieldStream()
    complete = _pcm(96_000)
    cuts = (17_333, 61_777, 96_000)
    start = 0
    captures = []
    receipts = []
    for sequence, end in enumerate(cuts):
        accepted = registry.accept(
            stream_id=stream_id,
            sequence=sequence,
            first_sample_index=start,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=complete[start * 2:end * 2],
        )
        capture, receipt = stream.advance(
            accepted.pcm_s16le, accepted.receipt
        )
        captures.append(capture)
        receipts.append(receipt)
        start = end

    unsplit = _field(complete)
    assert receipts[0].prior_state_receipt_sha256 is None
    assert receipts[1].prior_state_receipt_sha256 == receipts[0].receipt_sha256
    assert receipts[2].prior_state_receipt_sha256 == receipts[1].receipt_sha256
    for receipt in receipts:
        receipt.verify()
        assert (
            receipt.payload()["schema"]
            == AUDITORY_GAMMATONE_CONTINUATION_SCHEMA
            == "guala.auditory_gammatone_continuation.v3"
        )
    for port_index, expected in enumerate(unsplit.channels):
        pressure = tuple(
            value
            for capture in captures
            for value in capture.channels[
                port_index
            ].pressure_envelope_full_scale
        )
        phase = tuple(
            value
            for capture in captures
            for value in capture.channels[port_index].carrier_phase_turns
        )
        phase_advance = tuple(
            value
            for capture in captures
            for value in capture.channels[
                port_index
            ].carrier_phase_advance_turns
        )
        normalized_phase_advance = tuple(
            value
            for capture in captures
            for value in capture.channels[
                port_index
            ].carrier_phase_advance_nyquist_fraction
        )
        offsets = tuple(
            value
            for capture in captures
            for value in capture.channels[port_index].causal_offsets_ns
        )
        assert pressure == expected.pressure_envelope_full_scale
        assert phase == expected.carrier_phase_turns
        assert phase_advance == expected.carrier_phase_advance_turns
        assert normalized_phase_advance == (
            expected.carrier_phase_advance_nyquist_fraction
        )
        assert offsets == expected.causal_offsets_ns


@pytest.mark.parametrize("first_cut", (161, 319, 320, 321))
def test_completed_phase_is_exact_across_arbitrary_hop_boundary_partitions(
    monkeypatch, first_cut: int
) -> None:
    monkeypatch.setattr(provider, "_native_gammatone_field", None)
    monkeypatch.setattr(provider, "_native_gammatone_stream", None)
    transport = AuditoryPCMStreamRegistry()
    stream_id = transport.open()["stream_id"]
    stream = AuditoryFullFieldStream()
    complete = _pcm(960)
    captures = []
    start = 0
    for sequence, end in enumerate((first_cut, 960)):
        accepted = transport.accept(
            stream_id=stream_id,
            sequence=sequence,
            first_sample_index=start,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=complete[start * 2:end * 2],
        )
        capture, receipt = stream.advance(
            accepted.pcm_s16le, accepted.receipt
        )
        receipt.verify()
        captures.append(capture)
        start = end

    expected = _field(complete)
    for channel_index, expected_channel in enumerate(expected.channels):
        actual_phase = tuple(
            value
            for capture in captures
            for value in capture.channels[channel_index].carrier_phase_turns
        )
        actual_advance = tuple(
            value
            for capture in captures
            for value in capture.channels[
                channel_index
            ].carrier_phase_advance_turns
        )
        actual_normalized = tuple(
            value
            for capture in captures
            for value in capture.channels[
                channel_index
            ].carrier_phase_advance_nyquist_fraction
        )
        assert actual_phase == expected_channel.carrier_phase_turns
        assert actual_advance == expected_channel.carrier_phase_advance_turns
        assert actual_normalized == (
            expected_channel.carrier_phase_advance_nyquist_fraction
        )


def test_native_one_shot_and_stream_phase_components_are_exactly_identical(
) -> None:
    if (
        provider._native_gammatone_field is None
        or provider._native_gammatone_stream is None
    ):
        pytest.skip("native auditory kernels are unavailable")
    transport = AuditoryPCMStreamRegistry()
    stream_id = transport.open()["stream_id"]
    stream = AuditoryFullFieldStream()
    complete = _pcm(960)
    captures = []
    start = 0
    for sequence, end in enumerate((321, 960)):
        accepted = transport.accept(
            stream_id=stream_id,
            sequence=sequence,
            first_sample_index=start,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=1_000_000_000,
            pcm_s16le=complete[start * 2:end * 2],
        )
        capture, _ = stream.advance(accepted.pcm_s16le, accepted.receipt)
        captures.append(capture)
        start = end

    expected = _field(complete)
    for channel_index, expected_channel in enumerate(expected.channels):
        for field_name in (
            "pressure_envelope_full_scale",
            "carrier_phase_turns",
            "carrier_phase_advance_turns",
            "carrier_phase_advance_nyquist_fraction",
        ):
            assert tuple(
                value
                for capture in captures
                for value in getattr(capture.channels[channel_index], field_name)
            ) == getattr(expected_channel, field_name)


def test_interleaved_streams_preserve_independent_cochlear_histories(
    monkeypatch,
) -> None:
    monkeypatch.setattr(provider, "_native_gammatone_field", None)
    monkeypatch.setattr(provider, "_native_gammatone_stream", None)
    transport = AuditoryPCMStreamRegistry()
    stream_ids = (transport.open()["stream_id"], transport.open()["stream_id"])
    cochleae = AuditoryFullFieldStreamRegistry()
    complete = (_pcm(640), _pcm(640, offset=177))
    captures = {stream_id: [] for stream_id in stream_ids}

    for sequence, (start, end) in enumerate(((0, 320), (320, 640))):
        for stream_index, stream_id in enumerate(stream_ids):
            accepted = transport.accept(
                stream_id=stream_id,
                sequence=sequence,
                first_sample_index=start,
                sample_rate_hz=PCM_SAMPLE_RATE_HZ,
                source_epoch_start_ns=(stream_index + 1) * 1_000_000_000,
                pcm_s16le=complete[stream_index][start * 2:end * 2],
            )
            capture, _ = cochleae.advance(
                accepted.pcm_s16le, accepted.receipt
            )
            captures[stream_id].append(capture)

    for stream_index, stream_id in enumerate(stream_ids):
        expected = _field(complete[stream_index])
        for port_index, port in enumerate(expected.channels):
            assert tuple(
                value
                for capture in captures[stream_id]
                for value in capture.channels[
                    port_index
                ].pressure_envelope_full_scale
            ) == port.pressure_envelope_full_scale
            assert tuple(
                value
                for capture in captures[stream_id]
                for value in capture.channels[
                    port_index
                ].carrier_phase_turns
            ) == port.carrier_phase_turns
    assert cochleae.status()["active_streams"] == 2
