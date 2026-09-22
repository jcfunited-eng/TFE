"""Bounded dual-channel browser PCM continuity without false ear authority.

This is a parallel contract to the existing mono browser transport.  It never
upgrades, duplicates, splits, or re-labels mono PCM.  One admitted epoch must
declare two discrete worklet input channels, preserve their PCM bytes in
separate buffers, and prove that sequence, sample index, render-frame index,
sample count, sample rate, and source epoch advance on one shared clock.

Browser declarations cannot cryptographically prove that two physical
microphones exist.  Every receipt therefore says
``binaural_hardware_authority_proven=False``.  Explicit mono duplication,
channel averaging, unknown channel derivation, shared channel lineage, and any
clock discontinuity are rejected.  Equal left/right sample values are not
treated as proof of duplication because physical silence or a centered source
can produce equal measurements.

The browser worklet and bounded HTTP transport are wired, while physical
binaural and exact-separation authority intentionally remain ``wired=False``.
One projected captured channel may continue through the existing mono
Krimelack path without being described as binaural.  Exact source separation
still requires independent anonymous acoustic-path evidence.  This transport
layer does not evaluate or reduce DSF.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_CHUNK_SAMPLES,
    PCM_MAX_CHUNK_SAMPLES,
    PCM_RING_BYTES,
    PCM_SAMPLE_RATE_HZ,
    PCM_SAMPLE_WIDTH_BYTES,
    PCM_STREAM_CAPACITY,
    PCM_STREAM_IDLE_SECONDS,
)


BROWSER_BINAURAL_LINEAGE_SCHEMA = (
    "guala.browser_binaural_pcm_lineage.v1"
)
BROWSER_BINAURAL_CONTINUITY_SCHEMA = (
    "guala.browser_binaural_pcm_continuity.v1"
)
BROWSER_BINAURAL_INTEGRATION_SCHEMA = (
    "guala.browser_binaural_pcm_future_integration.v1"
)
BINAURAL_CHANNEL_COUNT = 2
BINAURAL_CHANNEL_ORDER = ("left", "right")
BINAURAL_RING_BYTES_PER_STREAM = BINAURAL_CHANNEL_COUNT * PCM_RING_BYTES


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


class BrowserBinauralLineageMode(str, Enum):
    DISCRETE_SOURCE_CHANNELS = "discrete_source_channels"
    MONO_DUPLICATED = "mono_duplicated"
    CHANNEL_AVERAGED = "channel_averaged"
    UNKNOWN_DERIVATION = "unknown_derivation"


@dataclass(frozen=True, slots=True)
class BrowserBinauralLineageReceipt:
    stream_id: str
    capture_session_sha256: str
    worklet_source_sha256: str
    media_track_settings_sha256: str
    mode: BrowserBinauralLineageMode
    media_track_channel_count: int
    worklet_input_channel_count: int
    channel_order: tuple[str, ...]
    channel_lineage_sha256s: tuple[str, ...]
    binaural_hardware_authority_proven: bool
    receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "binaural_hardware_authority_proven": (
                self.binaural_hardware_authority_proven
            ),
            "capture_session_sha256": self.capture_session_sha256,
            "channel_lineage_sha256s": list(
                self.channel_lineage_sha256s
            ),
            "channel_order": list(self.channel_order),
            "media_track_channel_count": (
                self.media_track_channel_count
            ),
            "media_track_settings_sha256": (
                self.media_track_settings_sha256
            ),
            "mode": self.mode.value,
            "schema": BROWSER_BINAURAL_LINEAGE_SCHEMA,
            "stream_id": self.stream_id,
            "worklet_input_channel_count": (
                self.worklet_input_channel_count
            ),
            "worklet_source_sha256": self.worklet_source_sha256,
        }

    def verify(self) -> None:
        if (
            not isinstance(self.stream_id, str)
            or not self.stream_id
            or self.mode
            is not BrowserBinauralLineageMode.DISCRETE_SOURCE_CHANNELS
            or self.media_track_channel_count != BINAURAL_CHANNEL_COUNT
            or self.worklet_input_channel_count
            != BINAURAL_CHANNEL_COUNT
            or self.channel_order != BINAURAL_CHANNEL_ORDER
            or len(self.channel_lineage_sha256s)
            != BINAURAL_CHANNEL_COUNT
            or len(set(self.channel_lineage_sha256s))
            != BINAURAL_CHANNEL_COUNT
            or self.binaural_hardware_authority_proven is not False
        ):
            raise ValueError(
                "browser binaural channel lineage is not discrete"
            )
        for value, name in (
            (self.capture_session_sha256, "capture session"),
            (self.worklet_source_sha256, "worklet source"),
            (
                self.media_track_settings_sha256,
                "media track settings",
            ),
            (self.channel_lineage_sha256s[0], "left channel lineage"),
            (self.channel_lineage_sha256s[1], "right channel lineage"),
        ):
            _sha256(value, f"browser binaural {name}")
        if _digest(self.payload()) != self.receipt_sha256:
            raise ValueError(
                "browser binaural channel lineage receipt changed"
            )


@dataclass(frozen=True, slots=True)
class BrowserBinauralContinuityReceipt:
    stream_id: str
    sequence: int
    first_sample_index: int
    render_frame_start: int
    sample_count: int
    source_epoch_start_ns: int
    lineage_receipt_sha256: str
    prior_receipt_sha256: str | None
    left_pcm_sha256: str
    right_pcm_sha256: str
    binaural_hardware_authority_proven: bool
    receipt_sha256: str

    @property
    def last_sample_index_exclusive(self) -> int:
        return self.first_sample_index + self.sample_count

    @property
    def render_frame_end(self) -> int:
        return self.render_frame_start + self.sample_count

    def payload(self) -> dict[str, object]:
        return {
            "binaural_hardware_authority_proven": (
                self.binaural_hardware_authority_proven
            ),
            "channel_order": list(BINAURAL_CHANNEL_ORDER),
            "first_sample_index": self.first_sample_index,
            "left_pcm_sha256": self.left_pcm_sha256,
            "lineage_receipt_sha256": self.lineage_receipt_sha256,
            "prior_receipt_sha256": self.prior_receipt_sha256,
            "render_frame_start": self.render_frame_start,
            "right_pcm_sha256": self.right_pcm_sha256,
            "sample_count": self.sample_count,
            "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
            "schema": BROWSER_BINAURAL_CONTINUITY_SCHEMA,
            "sequence": self.sequence,
            "source_epoch_start_ns": self.source_epoch_start_ns,
            "stream_id": self.stream_id,
        }

    def verify(self) -> None:
        if (
            not isinstance(self.stream_id, str)
            or not self.stream_id
            or isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
            or isinstance(self.first_sample_index, bool)
            or not isinstance(self.first_sample_index, int)
            or self.first_sample_index < 0
            or isinstance(self.render_frame_start, bool)
            or not isinstance(self.render_frame_start, int)
            or self.render_frame_start < 0
            or isinstance(self.sample_count, bool)
            or not isinstance(self.sample_count, int)
            or not 1 <= self.sample_count <= PCM_MAX_CHUNK_SAMPLES
            or isinstance(self.source_epoch_start_ns, bool)
            or not isinstance(self.source_epoch_start_ns, int)
            or self.source_epoch_start_ns <= 0
            or self.binaural_hardware_authority_proven is not False
        ):
            raise ValueError(
                "browser binaural continuity boundary changed"
            )
        for value, name in (
            (self.lineage_receipt_sha256, "lineage"),
            (self.left_pcm_sha256, "left PCM"),
            (self.right_pcm_sha256, "right PCM"),
        ):
            _sha256(value, f"browser binaural {name}")
        if self.prior_receipt_sha256 is not None:
            _sha256(
                self.prior_receipt_sha256,
                "browser binaural prior continuity",
            )
        if _digest(self.payload()) != self.receipt_sha256:
            raise ValueError(
                "browser binaural continuity receipt changed"
            )


@dataclass(frozen=True, slots=True)
class AcceptedBrowserBinauralPCMChunk:
    receipt: BrowserBinauralContinuityReceipt
    lineage: BrowserBinauralLineageReceipt
    left_pcm_s16le: bytes
    right_pcm_s16le: bytes
    bounded_left_pcm_tail: bytes
    bounded_right_pcm_tail: bytes
    bounded_tail_first_sample_index: int

    def verify(self) -> None:
        self.receipt.verify()
        self.lineage.verify()
        if (
            self.receipt.lineage_receipt_sha256
            != self.lineage.receipt_sha256
            or hashlib.sha256(self.left_pcm_s16le).hexdigest()
            != self.receipt.left_pcm_sha256
            or hashlib.sha256(self.right_pcm_s16le).hexdigest()
            != self.receipt.right_pcm_sha256
            or len(self.left_pcm_s16le)
            != self.receipt.sample_count * PCM_SAMPLE_WIDTH_BYTES
            or len(self.right_pcm_s16le)
            != self.receipt.sample_count * PCM_SAMPLE_WIDTH_BYTES
            or len(self.bounded_left_pcm_tail) > PCM_RING_BYTES
            or len(self.bounded_right_pcm_tail) > PCM_RING_BYTES
            or len(self.bounded_left_pcm_tail)
            != len(self.bounded_right_pcm_tail)
        ):
            raise ValueError(
                "accepted browser binaural pressure changed"
            )


@dataclass(slots=True)
class _BrowserBinauralStreamState:
    stream_id: str
    expected_sequence: int
    expected_first_sample_index: int
    expected_render_frame: int | None
    render_frame_origin: int | None
    source_epoch_start_ns: int | None
    lineage: BrowserBinauralLineageReceipt | None
    prior_receipt_sha256: str | None
    left_tail: bytearray
    right_tail: bytearray
    tail_first_sample_index: int
    last_activity: float


class BrowserBinauralPCMStreamRegistry:
    """Own bounded candidate two-channel browser pressure epochs."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        stream_capacity: int = PCM_STREAM_CAPACITY,
        idle_seconds: int = PCM_STREAM_IDLE_SECONDS,
    ) -> None:
        if stream_capacity <= 0 or idle_seconds <= 0:
            raise ValueError(
                "browser binaural registry bounds must be positive"
            )
        self._clock = clock
        self._stream_capacity = int(stream_capacity)
        self._idle_seconds = int(idle_seconds)
        self._lock = threading.RLock()
        self._streams: OrderedDict[
            str, _BrowserBinauralStreamState
        ] = OrderedDict()
        self._accepted = 0
        self._discontinuities = 0
        self._lineage_rejections = 0

    def _expire_locked(self, now: float) -> None:
        expired = tuple(
            stream_id
            for stream_id, state in self._streams.items()
            if now - state.last_activity > self._idle_seconds
        )
        for stream_id in expired:
            del self._streams[stream_id]

    def open(self) -> dict[str, object]:
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            if len(self._streams) >= self._stream_capacity:
                raise RuntimeError(
                    "browser binaural stream capacity is full"
                )
            stream_id = secrets.token_urlsafe(24)
            self._streams[stream_id] = _BrowserBinauralStreamState(
                stream_id=stream_id,
                expected_sequence=0,
                expected_first_sample_index=0,
                expected_render_frame=None,
                render_frame_origin=None,
                source_epoch_start_ns=None,
                lineage=None,
                prior_receipt_sha256=None,
                left_tail=bytearray(),
                right_tail=bytearray(),
                tail_first_sample_index=0,
                last_activity=now,
            )
            return {
                "binaural_hardware_authority_proven": False,
                "channel_count": BINAURAL_CHANNEL_COUNT,
                "channel_order": list(BINAURAL_CHANNEL_ORDER),
                "chunk_samples": PCM_CHUNK_SAMPLES,
                "continuity": "new_epoch_requires_discrete_lineage",
                "lineage_mode": (
                    BrowserBinauralLineageMode
                    .DISCRETE_SOURCE_CHANNELS.value
                ),
                "max_chunk_samples": PCM_MAX_CHUNK_SAMPLES,
                "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
                "stream_id": stream_id,
            }

    def close(self, stream_id: str) -> bool:
        with self._lock:
            return self._streams.pop(stream_id, None) is not None

    def reject(self, stream_id: str) -> None:
        with self._lock:
            if self._streams.pop(stream_id, None) is not None:
                self._discontinuities += 1

    def register_lineage(
        self,
        *,
        stream_id: str,
        capture_session_sha256: str,
        worklet_source_sha256: str,
        media_track_settings_sha256: str,
        mode: BrowserBinauralLineageMode,
        media_track_channel_count: int,
        worklet_input_channel_count: int,
        channel_order: tuple[str, ...],
    ) -> BrowserBinauralLineageReceipt:
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError(
                "browser binaural stream id is required"
            )
        for value, name in (
            (capture_session_sha256, "capture session"),
            (worklet_source_sha256, "worklet source"),
            (media_track_settings_sha256, "media track settings"),
        ):
            _sha256(value, f"browser binaural {name}")
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            state = self._streams.get(stream_id)
            if state is None:
                self._discontinuities += 1
                raise ValueError(
                    "browser binaural stream epoch is unknown or expired"
                )
            if state.lineage is not None:
                del self._streams[stream_id]
                self._lineage_rejections += 1
                raise ValueError(
                    "browser binaural lineage cannot change inside an epoch"
                )
            if (
                not isinstance(mode, BrowserBinauralLineageMode)
                or mode
                is not BrowserBinauralLineageMode
                .DISCRETE_SOURCE_CHANNELS
                or media_track_channel_count
                != BINAURAL_CHANNEL_COUNT
                or worklet_input_channel_count
                != BINAURAL_CHANNEL_COUNT
                or channel_order != BINAURAL_CHANNEL_ORDER
            ):
                del self._streams[stream_id]
                self._lineage_rejections += 1
                raise ValueError(
                    "mono duplication, averaging, or unknown channel "
                    "derivation cannot become binaural authority"
                )
            lineages = tuple(
                _digest({
                    "capture_session_sha256": capture_session_sha256,
                    "channel_index": channel_index,
                    "channel_name": channel_name,
                    "stream_id": stream_id,
                    "worklet_source_sha256": worklet_source_sha256,
                })
                for channel_index, channel_name in enumerate(
                    BINAURAL_CHANNEL_ORDER
                )
            )
            payload = {
                "binaural_hardware_authority_proven": False,
                "capture_session_sha256": capture_session_sha256,
                "channel_lineage_sha256s": list(lineages),
                "channel_order": list(BINAURAL_CHANNEL_ORDER),
                "media_track_channel_count": media_track_channel_count,
                "media_track_settings_sha256": (
                    media_track_settings_sha256
                ),
                "mode": mode.value,
                "schema": BROWSER_BINAURAL_LINEAGE_SCHEMA,
                "stream_id": stream_id,
                "worklet_input_channel_count": (
                    worklet_input_channel_count
                ),
                "worklet_source_sha256": worklet_source_sha256,
            }
            receipt = BrowserBinauralLineageReceipt(
                stream_id=stream_id,
                capture_session_sha256=capture_session_sha256,
                worklet_source_sha256=worklet_source_sha256,
                media_track_settings_sha256=(
                    media_track_settings_sha256
                ),
                mode=mode,
                media_track_channel_count=media_track_channel_count,
                worklet_input_channel_count=(
                    worklet_input_channel_count
                ),
                channel_order=BINAURAL_CHANNEL_ORDER,
                channel_lineage_sha256s=lineages,
                binaural_hardware_authority_proven=False,
                receipt_sha256=_digest(payload),
            )
            receipt.verify()
            state.lineage = receipt
            state.last_activity = now
            return receipt

    def accept(
        self,
        *,
        stream_id: str,
        lineage_receipt_sha256: str,
        sequence: int,
        first_sample_index: int,
        render_frame_start: int,
        sample_rate_hz: int,
        source_epoch_start_ns: int,
        left_pcm_s16le: bytes,
        right_pcm_s16le: bytes,
    ) -> AcceptedBrowserBinauralPCMChunk:
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError(
                "browser binaural stream id is required"
            )
        _sha256(
            lineage_receipt_sha256,
            "browser binaural lineage receipt",
        )
        for value, name in (
            (sequence, "sequence"),
            (first_sample_index, "first sample index"),
            (render_frame_start, "render frame start"),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(f"browser binaural {name} is invalid")
        if sample_rate_hz != PCM_SAMPLE_RATE_HZ:
            raise ValueError(
                "browser binaural transport requires 16 kHz samples"
            )
        if (
            isinstance(source_epoch_start_ns, bool)
            or not isinstance(source_epoch_start_ns, int)
            or source_epoch_start_ns <= 0
        ):
            raise ValueError(
                "browser binaural source epoch is invalid"
            )
        for value, name in (
            (left_pcm_s16le, "left"),
            (right_pcm_s16le, "right"),
        ):
            if not isinstance(value, bytes) or len(value) % 2:
                raise ValueError(
                    f"browser binaural {name} PCM is not signed 16-bit"
                )
        if len(left_pcm_s16le) != len(right_pcm_s16le):
            raise ValueError(
                "browser binaural channels left their shared sample clock"
            )
        sample_count = (
            len(left_pcm_s16le) // PCM_SAMPLE_WIDTH_BYTES
        )
        if not 1 <= sample_count <= PCM_MAX_CHUNK_SAMPLES:
            raise ValueError(
                "browser binaural chunk exceeds its sample boundary"
            )

        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            state = self._streams.get(stream_id)
            if state is None:
                self._discontinuities += 1
                raise ValueError(
                    "browser binaural stream epoch is unknown or expired"
                )
            lineage = state.lineage
            if (
                lineage is None
                or lineage.receipt_sha256
                != lineage_receipt_sha256
            ):
                del self._streams[stream_id]
                self._discontinuities += 1
                raise ValueError(
                    "browser binaural discrete lineage is absent or changed"
                )
            if (
                sequence != state.expected_sequence
                or first_sample_index
                != state.expected_first_sample_index
            ):
                del self._streams[stream_id]
                self._discontinuities += 1
                raise ValueError(
                    "browser binaural sample stream is discontinuous; "
                    "the epoch was closed"
                )
            if state.render_frame_origin is None:
                state.render_frame_origin = render_frame_start
                state.expected_render_frame = render_frame_start
            if (
                render_frame_start != state.expected_render_frame
                or render_frame_start - state.render_frame_origin
                != first_sample_index
            ):
                del self._streams[stream_id]
                self._discontinuities += 1
                raise ValueError(
                    "browser binaural render clock is discontinuous; "
                    "the epoch was closed"
                )
            if state.source_epoch_start_ns is None:
                state.source_epoch_start_ns = source_epoch_start_ns
            elif (
                state.source_epoch_start_ns != source_epoch_start_ns
            ):
                del self._streams[stream_id]
                self._discontinuities += 1
                raise ValueError(
                    "browser binaural source epoch changed; "
                    "the stream was closed"
                )
            payload = {
                "binaural_hardware_authority_proven": False,
                "channel_order": list(BINAURAL_CHANNEL_ORDER),
                "first_sample_index": first_sample_index,
                "left_pcm_sha256": hashlib.sha256(
                    left_pcm_s16le
                ).hexdigest(),
                "lineage_receipt_sha256": lineage.receipt_sha256,
                "prior_receipt_sha256": state.prior_receipt_sha256,
                "render_frame_start": render_frame_start,
                "right_pcm_sha256": hashlib.sha256(
                    right_pcm_s16le
                ).hexdigest(),
                "sample_count": sample_count,
                "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
                "schema": BROWSER_BINAURAL_CONTINUITY_SCHEMA,
                "sequence": sequence,
                "source_epoch_start_ns": source_epoch_start_ns,
                "stream_id": stream_id,
            }
            receipt = BrowserBinauralContinuityReceipt(
                stream_id=stream_id,
                sequence=sequence,
                first_sample_index=first_sample_index,
                render_frame_start=render_frame_start,
                sample_count=sample_count,
                source_epoch_start_ns=source_epoch_start_ns,
                lineage_receipt_sha256=lineage.receipt_sha256,
                prior_receipt_sha256=state.prior_receipt_sha256,
                left_pcm_sha256=payload["left_pcm_sha256"],
                right_pcm_sha256=payload["right_pcm_sha256"],
                binaural_hardware_authority_proven=False,
                receipt_sha256=_digest(payload),
            )
            receipt.verify()
            state.left_tail.extend(left_pcm_s16le)
            state.right_tail.extend(right_pcm_s16le)
            if len(state.left_tail) > PCM_RING_BYTES:
                removed = len(state.left_tail) - PCM_RING_BYTES
                if (
                    removed % PCM_SAMPLE_WIDTH_BYTES
                    or len(state.right_tail) - removed != PCM_RING_BYTES
                ):
                    raise RuntimeError(
                        "browser binaural ring lost channel alignment"
                    )
                del state.left_tail[:removed]
                del state.right_tail[:removed]
                state.tail_first_sample_index += (
                    removed // PCM_SAMPLE_WIDTH_BYTES
                )
            state.expected_sequence += 1
            state.expected_first_sample_index += sample_count
            state.expected_render_frame = (
                render_frame_start + sample_count
            )
            state.prior_receipt_sha256 = receipt.receipt_sha256
            state.last_activity = now
            self._streams.move_to_end(stream_id)
            self._accepted += 1
            accepted = AcceptedBrowserBinauralPCMChunk(
                receipt=receipt,
                lineage=lineage,
                left_pcm_s16le=left_pcm_s16le,
                right_pcm_s16le=right_pcm_s16le,
                bounded_left_pcm_tail=bytes(state.left_tail),
                bounded_right_pcm_tail=bytes(state.right_tail),
                bounded_tail_first_sample_index=(
                    state.tail_first_sample_index
                ),
            )
            accepted.verify()
            return accepted

    def status(self) -> dict[str, object]:
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            return {
                "accepted_chunks": self._accepted,
                "active_streams": len(self._streams),
                "binaural_hardware_authority_proven": False,
                "discontinuities": self._discontinuities,
                "lineage_rejections": self._lineage_rejections,
                "retained_pcm_bytes": sum(
                    len(state.left_tail) + len(state.right_tail)
                    for state in self._streams.values()
                ),
                "ring_capacity_bytes_per_stream": (
                    BINAURAL_RING_BYTES_PER_STREAM
                ),
                "stream_capacity": self._stream_capacity,
            }


def future_browser_binaural_integration_contract() -> dict[str, object]:
    """Describe the wired transport and still-unwired physical boundary."""

    return {
        "app_chunk_endpoint": "/api/v1/auditory/binaural-pcm/chunk",
        "app_close_endpoint": "/api/v1/auditory/binaural-pcm/close",
        "app_lineage_endpoint": "/api/v1/auditory/binaural-pcm/lineage",
        "app_open_endpoint": "/api/v1/auditory/binaural-pcm/open",
        "browser_transport_wired": True,
        "channel_count": BINAURAL_CHANNEL_COUNT,
        "channel_order": list(BINAURAL_CHANNEL_ORDER),
        "current_live_browser_path": (
            "active_left_channel_krimelack_plus_"
            "discrete_pair_hardware_unproven"
        ),
        "downstream_engine_admission": (
            "accept_continuous_binaural_pcm("
            "left_pcm_s16le,right_pcm_s16le,continuity_receipt)"
        ),
        "downstream_full_field_owner": "W1BinauralAuditoryL5Owner",
        "engine_room_hearing_wired": False,
        "hardware_authority_requirement": (
            "two physical discrete microphone channels remain externally "
            "unproven by browser transport"
        ),
        "path_conditioned_separation_owner": (
            "W1AuthenticatedMultiEmitterCaptureOwner"
        ),
        "required_worklet_processor": (
            "GualaDiscreteBinauralPCMTransport"
        ),
        "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
        "schema": BROWSER_BINAURAL_INTEGRATION_SCHEMA,
        "wired": False,
    }


__all__ = [
    "AcceptedBrowserBinauralPCMChunk",
    "BINAURAL_CHANNEL_COUNT",
    "BINAURAL_CHANNEL_ORDER",
    "BINAURAL_RING_BYTES_PER_STREAM",
    "BROWSER_BINAURAL_CONTINUITY_SCHEMA",
    "BROWSER_BINAURAL_INTEGRATION_SCHEMA",
    "BROWSER_BINAURAL_LINEAGE_SCHEMA",
    "BrowserBinauralContinuityReceipt",
    "BrowserBinauralLineageMode",
    "BrowserBinauralLineageReceipt",
    "BrowserBinauralPCMStreamRegistry",
    "future_browser_binaural_integration_contract",
]
