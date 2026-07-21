"""Bounded continuity authority for browser microphone PCM transport.

The browser transport is not cognition and does not decide whether sound is
speech.  This owner proves only that successive 16 kHz mono PCM chunks belong
to one gap-free sample sequence.  Stream identifiers are routing epochs, never
speaker identity.  A discontinuity is terminal for that epoch and no later
chunk can repair or bridge it.

Only a bounded eight-second PCM tail is retained.  It is transient process
state and is intentionally not persisted: a restart is a real discontinuity.
"""

from __future__ import annotations

import hashlib
import io
import json
import secrets
import threading
import time
import wave
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable


PCM_SAMPLE_RATE_HZ = 16_000
PCM_SAMPLE_WIDTH_BYTES = 2
PCM_CHUNK_SAMPLES = 5 * PCM_SAMPLE_RATE_HZ
PCM_MAX_CHUNK_SAMPLES = 8 * PCM_SAMPLE_RATE_HZ
PCM_RING_SAMPLES = 8 * PCM_SAMPLE_RATE_HZ
PCM_RING_BYTES = PCM_RING_SAMPLES * PCM_SAMPLE_WIDTH_BYTES
PCM_STREAM_CAPACITY = 4
PCM_STREAM_IDLE_SECONDS = 30
PCM_CONTINUITY_SCHEMA = "guala.auditory_pcm_continuity.v1"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class AuditoryPCMContinuityReceipt:
    stream_id: str
    sequence: int
    first_sample_index: int
    sample_count: int
    source_epoch_start_ns: int
    prior_receipt_sha256: str | None
    pcm_sha256: str
    receipt_sha256: str

    @property
    def last_sample_index_exclusive(self) -> int:
        return self.first_sample_index + self.sample_count

    def payload(self) -> dict:
        return {
            "first_sample_index": self.first_sample_index,
            "pcm_sha256": self.pcm_sha256,
            "prior_receipt_sha256": self.prior_receipt_sha256,
            "sample_count": self.sample_count,
            "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
            "schema": PCM_CONTINUITY_SCHEMA,
            "sequence": self.sequence,
            "stream_id": self.stream_id,
            "source_epoch_start_ns": self.source_epoch_start_ns,
        }

    def verify(self) -> None:
        if _digest(self.payload()) != self.receipt_sha256:
            raise ValueError("auditory PCM continuity receipt was altered")


@dataclass(frozen=True, slots=True)
class AcceptedAuditoryPCMChunk:
    receipt: AuditoryPCMContinuityReceipt
    pcm_s16le: bytes
    bounded_pcm_tail: bytes
    bounded_tail_first_sample_index: int


@dataclass(slots=True)
class _StreamState:
    stream_id: str
    expected_sequence: int
    expected_first_sample_index: int
    prior_receipt_sha256: str | None
    source_epoch_start_ns: int | None
    pcm_tail: bytearray
    tail_first_sample_index: int
    last_activity: float


class AuditoryPCMStreamRegistry:
    """Own a small set of transient, server-issued PCM stream epochs."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        stream_capacity: int = PCM_STREAM_CAPACITY,
        idle_seconds: int = PCM_STREAM_IDLE_SECONDS,
    ) -> None:
        if stream_capacity <= 0 or idle_seconds <= 0:
            raise ValueError("auditory PCM registry bounds must be positive")
        self._clock = clock
        self._stream_capacity = int(stream_capacity)
        self._idle_seconds = int(idle_seconds)
        self._lock = threading.RLock()
        self._streams: OrderedDict[str, _StreamState] = OrderedDict()
        self._accepted = 0
        self._discontinuities = 0

    def _expire_locked(self, now: float) -> None:
        expired = [
            stream_id
            for stream_id, state in self._streams.items()
            if now - state.last_activity > self._idle_seconds
        ]
        for stream_id in expired:
            del self._streams[stream_id]

    def open(self) -> dict:
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            if len(self._streams) >= self._stream_capacity:
                raise RuntimeError("auditory PCM stream capacity is full")
            stream_id = secrets.token_urlsafe(24)
            self._streams[stream_id] = _StreamState(
                stream_id=stream_id,
                expected_sequence=0,
                expected_first_sample_index=0,
                prior_receipt_sha256=None,
                source_epoch_start_ns=None,
                pcm_tail=bytearray(),
                tail_first_sample_index=0,
                last_activity=now,
            )
            return {
                "stream_id": stream_id,
                "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
                "chunk_samples": PCM_CHUNK_SAMPLES,
                "max_chunk_samples": PCM_MAX_CHUNK_SAMPLES,
                "continuity": "new_epoch",
            }
    def close(self, stream_id: str) -> bool:
        with self._lock:
            return self._streams.pop(stream_id, None) is not None

    def reject(self, stream_id: str) -> None:
        with self._lock:
            if self._streams.pop(stream_id, None) is not None:
                self._discontinuities += 1

    def accept(
        self,
        *,
        stream_id: str,
        sequence: int,
        first_sample_index: int,
        sample_rate_hz: int,
        source_epoch_start_ns: int,
        pcm_s16le: bytes,
    ) -> AcceptedAuditoryPCMChunk:
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError("auditory PCM stream id is required")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            raise ValueError("auditory PCM sequence is invalid")
        if (
            isinstance(first_sample_index, bool)
            or not isinstance(first_sample_index, int)
            or first_sample_index < 0
        ):
            raise ValueError("auditory PCM first sample index is invalid")
        if sample_rate_hz != PCM_SAMPLE_RATE_HZ:
            raise ValueError("auditory PCM transport requires 16 kHz samples")
        if (
            isinstance(source_epoch_start_ns, bool)
            or not isinstance(source_epoch_start_ns, int)
            or source_epoch_start_ns <= 0
        ):
            raise ValueError("auditory PCM source epoch is invalid")
        if not isinstance(pcm_s16le, bytes) or len(pcm_s16le) % 2:
            raise ValueError("auditory PCM payload is not signed 16-bit mono")
        sample_count = len(pcm_s16le) // PCM_SAMPLE_WIDTH_BYTES
        if sample_count == 0 or sample_count > PCM_MAX_CHUNK_SAMPLES:
            raise ValueError("auditory PCM chunk exceeds its sample boundary")

        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            state = self._streams.get(stream_id)
            if state is None:
                self._discontinuities += 1
                raise ValueError("auditory PCM stream epoch is unknown or expired")
            if (
                sequence != state.expected_sequence
                or first_sample_index != state.expected_first_sample_index
            ):
                del self._streams[stream_id]
                self._discontinuities += 1
                raise ValueError(
                    "auditory PCM stream is discontinuous; the epoch was closed"
                )
            if state.source_epoch_start_ns is None:
                state.source_epoch_start_ns = source_epoch_start_ns
            elif source_epoch_start_ns != state.source_epoch_start_ns:
                del self._streams[stream_id]
                self._discontinuities += 1
                raise ValueError(
                    "auditory PCM source epoch changed; the stream was closed"
                )

            pcm_sha256 = hashlib.sha256(pcm_s16le).hexdigest()
            payload = {
                "first_sample_index": first_sample_index,
                "pcm_sha256": pcm_sha256,
                "prior_receipt_sha256": state.prior_receipt_sha256,
                "sample_count": sample_count,
                "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
                "schema": PCM_CONTINUITY_SCHEMA,
                "sequence": sequence,
                "stream_id": stream_id,
                "source_epoch_start_ns": source_epoch_start_ns,
            }
            receipt = AuditoryPCMContinuityReceipt(
                stream_id=stream_id,
                sequence=sequence,
                first_sample_index=first_sample_index,
                sample_count=sample_count,
                source_epoch_start_ns=source_epoch_start_ns,
                prior_receipt_sha256=state.prior_receipt_sha256,
                pcm_sha256=pcm_sha256,
                receipt_sha256=_digest(payload),
            )
            receipt.verify()

            state.pcm_tail.extend(pcm_s16le)
            if len(state.pcm_tail) > PCM_RING_BYTES:
                removed_bytes = len(state.pcm_tail) - PCM_RING_BYTES
                if removed_bytes % PCM_SAMPLE_WIDTH_BYTES:
                    raise RuntimeError("auditory PCM ring lost sample alignment")
                del state.pcm_tail[:removed_bytes]
                state.tail_first_sample_index += (
                    removed_bytes // PCM_SAMPLE_WIDTH_BYTES
                )
            state.expected_sequence += 1
            state.expected_first_sample_index += sample_count
            state.prior_receipt_sha256 = receipt.receipt_sha256
            state.last_activity = now
            self._streams.move_to_end(stream_id)
            self._accepted += 1
            return AcceptedAuditoryPCMChunk(
                receipt=receipt,
                pcm_s16le=pcm_s16le,
                bounded_pcm_tail=bytes(state.pcm_tail),
                bounded_tail_first_sample_index=state.tail_first_sample_index,
            )

    def status(self) -> dict:
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            return {
                "active_streams": len(self._streams),
                "stream_capacity": self._stream_capacity,
                "ring_capacity_bytes_per_stream": PCM_RING_BYTES,
                "accepted_chunks": self._accepted,
                "discontinuities": self._discontinuities,
                "retained_pcm_bytes": sum(
                    len(state.pcm_tail) for state in self._streams.values()
                ),
            }


def pcm_s16le_wav(pcm_s16le: bytes) -> bytes:
    """Wrap already-canonical transport samples without decoding/resampling."""
    if not isinstance(pcm_s16le, bytes) or not pcm_s16le or len(pcm_s16le) % 2:
        raise ValueError("auditory PCM payload is not signed 16-bit mono")
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(PCM_SAMPLE_WIDTH_BYTES)
        stream.setframerate(PCM_SAMPLE_RATE_HZ)
        stream.writeframes(pcm_s16le)
    return output.getvalue()


__all__ = (
    "AcceptedAuditoryPCMChunk",
    "AuditoryPCMContinuityReceipt",
    "AuditoryPCMStreamRegistry",
    "PCM_CHUNK_SAMPLES",
    "PCM_CONTINUITY_SCHEMA",
    "PCM_MAX_CHUNK_SAMPLES",
    "PCM_RING_BYTES",
    "PCM_SAMPLE_RATE_HZ",
    "pcm_s16le_wav",
)
