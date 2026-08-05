from __future__ import annotations

import math
import struct
from dataclasses import replace
from pathlib import Path

import pytest

from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_RING_BYTES,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.browser_binaural_pcm_stream import (
    BINAURAL_CHANNEL_ORDER,
    BINAURAL_RING_BYTES_PER_STREAM,
    BrowserBinauralLineageMode,
    BrowserBinauralPCMStreamRegistry,
    future_browser_binaural_integration_contract,
)


ROOT = Path(__file__).resolve().parents[1]
LIVE_PAGE = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"
SOURCE_EPOCH_NS = 9_000_000_000
RENDER_FRAME_ORIGIN = 48_000


def _pcm(
    sample_count: int,
    *,
    frequency_hz: int,
    offset: int = 0,
) -> bytes:
    values = tuple(
        int(
            8_000 * math.sin(
                2 * math.pi * frequency_hz * (offset + index) / 16_000
            )
        )
        for index in range(sample_count)
    )
    return struct.pack(f"<{sample_count}h", *values)


def _opened():
    registry = BrowserBinauralPCMStreamRegistry()
    opened = registry.open()
    return registry, opened


def _lineage(
    registry: BrowserBinauralPCMStreamRegistry,
    stream_id: str,
):
    return registry.register_lineage(
        stream_id=stream_id,
        capture_session_sha256="1" * 64,
        worklet_source_sha256="2" * 64,
        media_track_settings_sha256="3" * 64,
        mode=BrowserBinauralLineageMode.DISCRETE_SOURCE_CHANNELS,
        media_track_channel_count=2,
        worklet_input_channel_count=2,
        channel_order=BINAURAL_CHANNEL_ORDER,
    )


def test_open_contract_requires_two_discrete_channels_without_hardware_claim():
    registry, opened = _opened()

    assert opened["channel_count"] == 2
    assert opened["channel_order"] == ["left", "right"]
    assert opened["lineage_mode"] == "discrete_source_channels"
    assert opened["binaural_hardware_authority_proven"] is False
    assert registry.status()["binaural_hardware_authority_proven"] is False


def test_contiguous_chunks_preserve_channels_and_one_exact_render_clock():
    registry, opened = _opened()
    lineage = _lineage(registry, opened["stream_id"])
    left_complete = _pcm(50_000, frequency_hz=440)
    right_complete = _pcm(50_000, frequency_hz=730)
    cuts = (19_333, 50_000)
    start = 0
    accepted = None
    prior = None
    for sequence, end in enumerate(cuts):
        accepted = registry.accept(
            stream_id=opened["stream_id"],
            lineage_receipt_sha256=lineage.receipt_sha256,
            sequence=sequence,
            first_sample_index=start,
            render_frame_start=RENDER_FRAME_ORIGIN + start,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=SOURCE_EPOCH_NS,
            left_pcm_s16le=left_complete[start * 2:end * 2],
            right_pcm_s16le=right_complete[start * 2:end * 2],
        )
        accepted.verify()
        assert accepted.receipt.prior_receipt_sha256 == prior
        prior = accepted.receipt.receipt_sha256
        start = end

    assert accepted is not None
    assert accepted.bounded_left_pcm_tail == left_complete
    assert accepted.bounded_right_pcm_tail == right_complete
    assert accepted.receipt.render_frame_end == (
        RENDER_FRAME_ORIGIN + 50_000
    )
    assert accepted.receipt.last_sample_index_exclusive == 50_000
    assert accepted.receipt.left_pcm_sha256 != (
        accepted.receipt.right_pcm_sha256
    )
    assert accepted.receipt.binaural_hardware_authority_proven is False


@pytest.mark.parametrize(
    "mode",
    (
        BrowserBinauralLineageMode.MONO_DUPLICATED,
        BrowserBinauralLineageMode.CHANNEL_AVERAGED,
        BrowserBinauralLineageMode.UNKNOWN_DERIVATION,
    ),
)
def test_mono_duplication_averaging_and_unknown_derivation_are_rejected(
    mode: BrowserBinauralLineageMode,
):
    registry, opened = _opened()

    with pytest.raises(
        ValueError,
        match="cannot become binaural authority",
    ):
        registry.register_lineage(
            stream_id=opened["stream_id"],
            capture_session_sha256="1" * 64,
            worklet_source_sha256="2" * 64,
            media_track_settings_sha256="3" * 64,
            mode=mode,
            media_track_channel_count=2,
            worklet_input_channel_count=2,
            channel_order=BINAURAL_CHANNEL_ORDER,
        )

    assert registry.status()["active_streams"] == 0
    assert registry.status()["lineage_rejections"] == 1


def test_one_channel_or_relabelled_channels_cannot_register():
    for media_channels, worklet_channels, order in (
        (1, 2, BINAURAL_CHANNEL_ORDER),
        (2, 1, BINAURAL_CHANNEL_ORDER),
        (2, 2, ("right", "left")),
    ):
        registry, opened = _opened()
        with pytest.raises(
            ValueError,
            match="cannot become binaural authority",
        ):
            registry.register_lineage(
                stream_id=opened["stream_id"],
                capture_session_sha256="1" * 64,
                worklet_source_sha256="2" * 64,
                media_track_settings_sha256="3" * 64,
                mode=(
                    BrowserBinauralLineageMode
                    .DISCRETE_SOURCE_CHANNELS
                ),
                media_track_channel_count=media_channels,
                worklet_input_channel_count=worklet_channels,
                channel_order=order,
            )
        assert registry.status()["active_streams"] == 0


def test_equal_samples_are_transportable_but_never_prove_two_microphones():
    registry, opened = _opened()
    lineage = _lineage(registry, opened["stream_id"])
    silence = b"\0\0" * 320

    accepted = registry.accept(
        stream_id=opened["stream_id"],
        lineage_receipt_sha256=lineage.receipt_sha256,
        sequence=0,
        first_sample_index=0,
        render_frame_start=RENDER_FRAME_ORIGIN,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=SOURCE_EPOCH_NS,
        left_pcm_s16le=silence,
        right_pcm_s16le=silence,
    )

    assert accepted.left_pcm_s16le == accepted.right_pcm_s16le
    assert accepted.lineage.channel_lineage_sha256s[0] != (
        accepted.lineage.channel_lineage_sha256s[1]
    )
    assert accepted.receipt.binaural_hardware_authority_proven is False
    assert accepted.lineage.binaural_hardware_authority_proven is False


@pytest.mark.parametrize(
    ("sequence", "first_sample_index", "render_frame_start", "source_epoch"),
    (
        (2, 320, RENDER_FRAME_ORIGIN + 320, SOURCE_EPOCH_NS),
        (1, 321, RENDER_FRAME_ORIGIN + 320, SOURCE_EPOCH_NS),
        (1, 320, RENDER_FRAME_ORIGIN + 321, SOURCE_EPOCH_NS),
        (1, 320, RENDER_FRAME_ORIGIN + 320, SOURCE_EPOCH_NS + 1),
    ),
)
def test_sequence_sample_render_or_epoch_discontinuity_closes_stream(
    sequence: int,
    first_sample_index: int,
    render_frame_start: int,
    source_epoch: int,
):
    registry, opened = _opened()
    lineage = _lineage(registry, opened["stream_id"])
    left = _pcm(320, frequency_hz=440)
    right = _pcm(320, frequency_hz=730)
    registry.accept(
        stream_id=opened["stream_id"],
        lineage_receipt_sha256=lineage.receipt_sha256,
        sequence=0,
        first_sample_index=0,
        render_frame_start=RENDER_FRAME_ORIGIN,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=SOURCE_EPOCH_NS,
        left_pcm_s16le=left,
        right_pcm_s16le=right,
    )

    with pytest.raises(ValueError, match="discontinuous|epoch changed"):
        registry.accept(
            stream_id=opened["stream_id"],
            lineage_receipt_sha256=lineage.receipt_sha256,
            sequence=sequence,
            first_sample_index=first_sample_index,
            render_frame_start=render_frame_start,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=source_epoch,
            left_pcm_s16le=left,
            right_pcm_s16le=right,
        )

    assert registry.status()["active_streams"] == 0


def test_unequal_channel_cardinality_is_rejected_before_mutation():
    registry, opened = _opened()
    lineage = _lineage(registry, opened["stream_id"])

    with pytest.raises(ValueError, match="shared sample clock"):
        registry.accept(
            stream_id=opened["stream_id"],
            lineage_receipt_sha256=lineage.receipt_sha256,
            sequence=0,
            first_sample_index=0,
            render_frame_start=RENDER_FRAME_ORIGIN,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=SOURCE_EPOCH_NS,
            left_pcm_s16le=b"\0\0" * 320,
            right_pcm_s16le=b"\0\0" * 319,
        )

    assert registry.status()["active_streams"] == 1
    assert registry.status()["accepted_chunks"] == 0


def test_two_channel_ring_is_bounded_without_interleaving_or_reordering():
    registry, opened = _opened()
    lineage = _lineage(registry, opened["stream_id"])
    left_first = _pcm(80_000, frequency_hz=440)
    right_first = _pcm(80_000, frequency_hz=730)
    left_second = _pcm(80_000, frequency_hz=440, offset=80_000)
    right_second = _pcm(80_000, frequency_hz=730, offset=80_000)
    registry.accept(
        stream_id=opened["stream_id"],
        lineage_receipt_sha256=lineage.receipt_sha256,
        sequence=0,
        first_sample_index=0,
        render_frame_start=RENDER_FRAME_ORIGIN,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=SOURCE_EPOCH_NS,
        left_pcm_s16le=left_first,
        right_pcm_s16le=right_first,
    )
    accepted = registry.accept(
        stream_id=opened["stream_id"],
        lineage_receipt_sha256=lineage.receipt_sha256,
        sequence=1,
        first_sample_index=80_000,
        render_frame_start=RENDER_FRAME_ORIGIN + 80_000,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=SOURCE_EPOCH_NS,
        left_pcm_s16le=left_second,
        right_pcm_s16le=right_second,
    )

    assert len(accepted.bounded_left_pcm_tail) == PCM_RING_BYTES
    assert len(accepted.bounded_right_pcm_tail) == PCM_RING_BYTES
    assert accepted.bounded_left_pcm_tail == (
        left_first + left_second
    )[-PCM_RING_BYTES:]
    assert accepted.bounded_right_pcm_tail == (
        right_first + right_second
    )[-PCM_RING_BYTES:]
    assert accepted.bounded_tail_first_sample_index == 32_000
    assert registry.status()["retained_pcm_bytes"] == (
        BINAURAL_RING_BYTES_PER_STREAM
    )


def test_receipt_rejects_cross_channel_substitution():
    registry, opened = _opened()
    lineage = _lineage(registry, opened["stream_id"])
    accepted = registry.accept(
        stream_id=opened["stream_id"],
        lineage_receipt_sha256=lineage.receipt_sha256,
        sequence=0,
        first_sample_index=0,
        render_frame_start=RENDER_FRAME_ORIGIN,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=SOURCE_EPOCH_NS,
        left_pcm_s16le=_pcm(320, frequency_hz=440),
        right_pcm_s16le=_pcm(320, frequency_hz=730),
    )
    changed_receipt = replace(
        accepted.receipt,
        left_pcm_sha256=accepted.receipt.right_pcm_sha256,
    )

    with pytest.raises(ValueError, match="continuity receipt changed"):
        changed_receipt.verify()


def test_native_ui_does_not_mount_unproven_binaural_transport():
    contract = future_browser_binaural_integration_contract()
    page = LIVE_PAGE.read_text(encoding="utf-8")

    assert contract["wired"] is False
    assert contract["hardware_authority_requirement"] == (
        "two physical discrete microphone channels remain externally unproven "
        "by browser transport"
    )
    assert "/api/v1/auditory/binaural-pcm/" not in page
    assert "W1BinauralAuditoryL5Owner" not in page
    assert 'capability("microphone")' in page
    assert "Local microphone active · no organism acceptance yet" in page
    assert "Local microphone active · organism accepted generation" in page
    assert 'schema:"guala.native.browser_audio_chunk.v1"' in page
    assert "result.accepted!==true" in page


def test_expired_dual_channel_epoch_cannot_resume():
    now = [0.0]
    registry = BrowserBinauralPCMStreamRegistry(
        clock=lambda: now[0],
        idle_seconds=5,
    )
    opened = registry.open()
    lineage = _lineage(registry, opened["stream_id"])
    now[0] = 6.0

    with pytest.raises(ValueError, match="unknown or expired"):
        registry.accept(
            stream_id=opened["stream_id"],
            lineage_receipt_sha256=lineage.receipt_sha256,
            sequence=0,
            first_sample_index=0,
            render_frame_start=RENDER_FRAME_ORIGIN,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=SOURCE_EPOCH_NS,
            left_pcm_s16le=b"\0\0" * 320,
            right_pcm_s16le=b"\0\0" * 320,
        )
