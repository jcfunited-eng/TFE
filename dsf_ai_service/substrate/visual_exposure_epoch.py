"""Transient acquisition continuity for paired browser camera exposures.

This authority proves only that two visual preparations were accepted on
successive chunks of one server-issued, gap-free PCM acquisition epoch.  It
does not prove that a visual region is the same physical object, that a visible
region produced a sound, or that a client timestamp is identity.  The state is
capacity bounded, process local, and intentionally absent from persistence.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Mapping

from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMContinuityReceipt,
    PCM_STREAM_CAPACITY,
    PCM_STREAM_IDLE_SECONDS,
)


VISUAL_EXPOSURE_EPOCH_SCHEMA = "guala.visual_exposure_epoch.v1"
VISUAL_EXPOSURE_EPOCH_STATE_SCHEMA = "guala.visual_exposure_epoch.state.v1"
MAX_VISUAL_EXPOSURE_EPOCH_STATE_BYTES = 16 * 1024


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _key_bytes(value: object) -> bytes:
    if isinstance(value, str):
        encoded = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        encoded = bytes(value)
    else:
        raise TypeError("visual exposure epoch key must be bytes or text")
    if not encoded:
        raise ValueError("visual exposure epoch key cannot be empty")
    return hashlib.sha256(b"guala-visual-exposure-epoch-key-v1\0" + encoded).digest()


def _sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} is not a lowercase SHA-256 digest")
    return value


def _hmac(key: bytes, domain: bytes, payload: object) -> str:
    return hmac.new(
        key,
        domain + b"\0" + _canonical_bytes(payload),
        hashlib.sha256,
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class VisualExposureEpochEvidence:
    stream_id: str
    sequence: int
    auditory_pcm_receipt_sha256: str
    observed_prior_epoch_receipt_sha256: str | None
    authenticated_predecessor_epoch_receipt_sha256: str | None
    authenticated_predecessor_terminal_frame_sha256: str | None
    current_initial_frame_sha256: str
    current_terminal_frame_sha256: str
    current_preparation_receipt_sha256: str
    relation: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "auditory_pcm_receipt_sha256": self.auditory_pcm_receipt_sha256,
            "authenticated_predecessor_epoch_receipt_sha256": (
                self.authenticated_predecessor_epoch_receipt_sha256
            ),
            "authenticated_predecessor_terminal_frame_sha256": (
                self.authenticated_predecessor_terminal_frame_sha256
            ),
            "current_initial_frame_sha256": self.current_initial_frame_sha256,
            "current_preparation_receipt_sha256": (
                self.current_preparation_receipt_sha256
            ),
            "current_terminal_frame_sha256": self.current_terminal_frame_sha256,
            "observed_prior_epoch_receipt_sha256": (
                self.observed_prior_epoch_receipt_sha256
            ),
            "relation": self.relation,
            "schema": VISUAL_EXPOSURE_EPOCH_SCHEMA,
            "sequence": self.sequence,
            "stream_id": self.stream_id,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class VisualExposureEpochAuthority:
    """Capacity-bounded owner of acquisition predecessor evidence."""

    def __init__(
        self,
        *,
        authority_key: object,
        stream_capacity: int = PCM_STREAM_CAPACITY,
        idle_seconds: int = PCM_STREAM_IDLE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            isinstance(stream_capacity, bool)
            or not isinstance(stream_capacity, int)
            or stream_capacity <= 0
            or stream_capacity > PCM_STREAM_CAPACITY
        ):
            raise ValueError("visual exposure epoch capacity is invalid")
        if (
            isinstance(idle_seconds, bool)
            or not isinstance(idle_seconds, int)
            or idle_seconds <= 0
        ):
            raise ValueError("visual exposure epoch idle boundary is invalid")
        self._key = _key_bytes(authority_key)
        self._stream_capacity = stream_capacity
        self._idle_seconds = idle_seconds
        self._clock = clock
        self._lock = threading.RLock()
        self._streams: OrderedDict[str, dict[str, object]] = OrderedDict()

    def _expire_locked(self, now: float) -> None:
        expired = tuple(
            stream_id
            for stream_id, state in self._streams.items()
            if now - float(state["last_activity"]) > self._idle_seconds
        )
        for stream_id in expired:
            del self._streams[stream_id]

    def _seal(self, payload: Mapping[str, object]) -> VisualExposureEpochEvidence:
        signature = _hmac(
            self._key,
            b"guala-visual-exposure-epoch-evidence-v1",
            payload,
        )
        receipt = hashlib.sha256(
            b"guala-visual-exposure-epoch-receipt-v1\0"
            + _canonical_bytes({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ).hexdigest()
        return VisualExposureEpochEvidence(
            stream_id=str(payload["stream_id"]),
            sequence=int(payload["sequence"]),
            auditory_pcm_receipt_sha256=str(
                payload["auditory_pcm_receipt_sha256"]
            ),
            observed_prior_epoch_receipt_sha256=payload[
                "observed_prior_epoch_receipt_sha256"
            ],
            authenticated_predecessor_epoch_receipt_sha256=payload[
                "authenticated_predecessor_epoch_receipt_sha256"
            ],
            authenticated_predecessor_terminal_frame_sha256=payload[
                "authenticated_predecessor_terminal_frame_sha256"
            ],
            current_initial_frame_sha256=str(
                payload["current_initial_frame_sha256"]
            ),
            current_terminal_frame_sha256=str(
                payload["current_terminal_frame_sha256"]
            ),
            current_preparation_receipt_sha256=str(
                payload["current_preparation_receipt_sha256"]
            ),
            relation=str(payload["relation"]),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=receipt,
        )

    def verify(self, evidence: VisualExposureEpochEvidence) -> None:
        if not isinstance(evidence, VisualExposureEpochEvidence):
            raise TypeError("visual exposure evidence is not typed")
        if not evidence.stream_id:
            raise ValueError("visual exposure evidence has no stream")
        if (
            isinstance(evidence.sequence, bool)
            or not isinstance(evidence.sequence, int)
            or evidence.sequence < 0
        ):
            raise ValueError("visual exposure evidence sequence is invalid")
        for digest, label in (
            (evidence.auditory_pcm_receipt_sha256, "auditory PCM receipt"),
            (evidence.current_initial_frame_sha256, "initial frame receipt"),
            (evidence.current_terminal_frame_sha256, "terminal frame receipt"),
            (
                evidence.current_preparation_receipt_sha256,
                "visual preparation receipt",
            ),
        ):
            _sha256(digest, f"visual exposure {label}")
        for digest, label in (
            (
                evidence.observed_prior_epoch_receipt_sha256,
                "observed prior epoch receipt",
            ),
            (
                evidence.authenticated_predecessor_epoch_receipt_sha256,
                "authenticated predecessor epoch receipt",
            ),
            (
                evidence.authenticated_predecessor_terminal_frame_sha256,
                "authenticated predecessor terminal frame receipt",
            ),
        ):
            if digest is not None:
                _sha256(digest, f"visual exposure {label}")
        if evidence.relation == "first_in_epoch":
            if (
                evidence.authenticated_predecessor_epoch_receipt_sha256
                is not None
                or evidence.authenticated_predecessor_terminal_frame_sha256
                is not None
            ):
                raise ValueError("first visual exposure claimed a predecessor")
        elif evidence.relation == "authenticated_predecessor_evidence":
            if (
                evidence.observed_prior_epoch_receipt_sha256 is None
                or evidence.authenticated_predecessor_epoch_receipt_sha256
                != evidence.observed_prior_epoch_receipt_sha256
                or evidence.authenticated_predecessor_terminal_frame_sha256
                is None
            ):
                raise ValueError("visual predecessor evidence is incomplete")
        else:
            raise ValueError("visual exposure relation changed")
        payload = evidence.payload()
        expected_hmac = _hmac(
            self._key,
            b"guala-visual-exposure-epoch-evidence-v1",
            payload,
        )
        if not hmac.compare_digest(expected_hmac, evidence.authority_hmac_sha256):
            raise ValueError("visual exposure evidence HMAC changed")
        expected_receipt = hashlib.sha256(
            b"guala-visual-exposure-epoch-receipt-v1\0"
            + _canonical_bytes({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ).hexdigest()
        if not hmac.compare_digest(
            expected_receipt, evidence.authority_receipt_sha256
        ):
            raise ValueError("visual exposure evidence receipt changed")

    def from_record(self, value: object) -> VisualExposureEpochEvidence:
        if not isinstance(value, Mapping):
            raise ValueError("visual exposure evidence record changed")
        required = {
            "auditory_pcm_receipt_sha256",
            "authenticated_predecessor_epoch_receipt_sha256",
            "authenticated_predecessor_terminal_frame_sha256",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "current_initial_frame_sha256",
            "current_preparation_receipt_sha256",
            "current_terminal_frame_sha256",
            "observed_prior_epoch_receipt_sha256",
            "relation",
            "schema",
            "sequence",
            "stream_id",
        }
        if (
            set(value) != required
            or value.get("schema") != VISUAL_EXPOSURE_EPOCH_SCHEMA
        ):
            raise ValueError("visual exposure evidence record changed")
        evidence = VisualExposureEpochEvidence(
            stream_id=value["stream_id"],
            sequence=value["sequence"],
            auditory_pcm_receipt_sha256=value["auditory_pcm_receipt_sha256"],
            observed_prior_epoch_receipt_sha256=value[
                "observed_prior_epoch_receipt_sha256"
            ],
            authenticated_predecessor_epoch_receipt_sha256=value[
                "authenticated_predecessor_epoch_receipt_sha256"
            ],
            authenticated_predecessor_terminal_frame_sha256=value[
                "authenticated_predecessor_terminal_frame_sha256"
            ],
            current_initial_frame_sha256=value["current_initial_frame_sha256"],
            current_terminal_frame_sha256=value["current_terminal_frame_sha256"],
            current_preparation_receipt_sha256=value[
                "current_preparation_receipt_sha256"
            ],
            relation=value["relation"],
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=value["authority_receipt_sha256"],
        )
        self.verify(evidence)
        return evidence

    def prepare(
        self,
        *,
        auditory: AuditoryPCMContinuityReceipt,
        frame_receipt_sha256s: tuple[str, ...],
        preparation_receipt_sha256: str,
    ) -> VisualExposureEpochEvidence:
        if not isinstance(auditory, AuditoryPCMContinuityReceipt):
            raise TypeError("visual exposure epoch requires typed PCM continuity")
        auditory.verify()
        if not 4 <= len(frame_receipt_sha256s) <= 8:
            raise ValueError("visual exposure epoch requires four through eight frames")
        for digest in frame_receipt_sha256s:
            _sha256(digest, "visual exposure frame receipt")
        _sha256(preparation_receipt_sha256, "visual preparation receipt")
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            prior = self._streams.get(auditory.stream_id)
            observed_prior = (
                str(prior["authority_receipt_sha256"])
                if prior is not None
                else None
            )
            continuous = bool(
                prior is not None
                and auditory.sequence == int(prior["sequence"]) + 1
                and auditory.prior_receipt_sha256
                == prior["auditory_pcm_receipt_sha256"]
            )
            payload = {
                "auditory_pcm_receipt_sha256": auditory.receipt_sha256,
                "authenticated_predecessor_epoch_receipt_sha256": (
                    observed_prior if continuous else None
                ),
                "authenticated_predecessor_terminal_frame_sha256": (
                    str(prior["current_terminal_frame_sha256"])
                    if continuous
                    else None
                ),
                "current_initial_frame_sha256": frame_receipt_sha256s[0],
                "current_preparation_receipt_sha256": (
                    preparation_receipt_sha256
                ),
                "current_terminal_frame_sha256": frame_receipt_sha256s[-1],
                "observed_prior_epoch_receipt_sha256": observed_prior,
                "relation": (
                    "authenticated_predecessor_evidence"
                    if continuous
                    else "first_in_epoch"
                ),
                "schema": VISUAL_EXPOSURE_EPOCH_SCHEMA,
                "sequence": auditory.sequence,
                "stream_id": auditory.stream_id,
            }
            evidence = self._seal(payload)
            self.verify(evidence)
            return evidence

    def commit(self, evidence: VisualExposureEpochEvidence) -> None:
        self.verify(evidence)
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            current = self._streams.get(evidence.stream_id)
            current_receipt = (
                str(current["authority_receipt_sha256"])
                if current is not None
                else None
            )
            if current_receipt != evidence.observed_prior_epoch_receipt_sha256:
                raise RuntimeError("visual exposure epoch changed before commit")
            if current is None and len(self._streams) >= self._stream_capacity:
                raise RuntimeError("visual exposure epoch capacity is full")
            self._streams[evidence.stream_id] = {
                "auditory_pcm_receipt_sha256": (
                    evidence.auditory_pcm_receipt_sha256
                ),
                "authority_receipt_sha256": evidence.authority_receipt_sha256,
                "current_preparation_receipt_sha256": (
                    evidence.current_preparation_receipt_sha256
                ),
                "current_terminal_frame_sha256": (
                    evidence.current_terminal_frame_sha256
                ),
                "last_activity": now,
                "sequence": evidence.sequence,
            }
            self._streams.move_to_end(evidence.stream_id)

    def clear(self, stream_id: str) -> bool:
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError("visual exposure epoch stream id is required")
        with self._lock:
            return self._streams.pop(stream_id, None) is not None

    def snapshot_encoded(self) -> bytes:
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            payload = {
                "idle_seconds": self._idle_seconds,
                "schema": VISUAL_EXPOSURE_EPOCH_STATE_SCHEMA,
                "stream_capacity": self._stream_capacity,
                "streams": list(self._streams.items()),
            }
            envelope = {
                "payload": payload,
                "state_hmac_sha256": _hmac(
                    self._key,
                    b"guala-visual-exposure-epoch-state-v1",
                    payload,
                ),
            }
            encoded = _canonical_bytes(envelope)
            if len(encoded) > MAX_VISUAL_EXPOSURE_EPOCH_STATE_BYTES:
                raise RuntimeError("visual exposure epoch state exceeded its boundary")
            return encoded

    def rollback_encoded(self, encoded: bytes) -> None:
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("visual exposure epoch state must be nonempty bytes")
        if len(encoded) > MAX_VISUAL_EXPOSURE_EPOCH_STATE_BYTES:
            raise ValueError("visual exposure epoch state exceeded its boundary")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("visual exposure epoch state is invalid JSON") from error
        if _canonical_bytes(envelope) != encoded:
            raise ValueError("visual exposure epoch state is not canonical")
        if not isinstance(envelope, dict) or set(envelope) != {
            "payload",
            "state_hmac_sha256",
        }:
            raise ValueError("visual exposure epoch envelope changed")
        payload = envelope["payload"]
        if (
            not isinstance(payload, dict)
            or set(payload)
            != {"idle_seconds", "schema", "stream_capacity", "streams"}
            or payload["schema"] != VISUAL_EXPOSURE_EPOCH_STATE_SCHEMA
            or payload["stream_capacity"] != self._stream_capacity
            or payload["idle_seconds"] != self._idle_seconds
            or not isinstance(payload["streams"], list)
            or len(payload["streams"]) > self._stream_capacity
        ):
            raise ValueError("visual exposure epoch state changed")
        expected = _hmac(
            self._key,
            b"guala-visual-exposure-epoch-state-v1",
            payload,
        )
        if not hmac.compare_digest(expected, envelope["state_hmac_sha256"]):
            raise ValueError("visual exposure epoch state authentication failed")
        restored: OrderedDict[str, dict[str, object]] = OrderedDict()
        for item in payload["streams"]:
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not item[0]
                or not isinstance(item[1], dict)
                or set(item[1])
                != {
                    "auditory_pcm_receipt_sha256",
                    "authority_receipt_sha256",
                    "current_preparation_receipt_sha256",
                    "current_terminal_frame_sha256",
                    "last_activity",
                    "sequence",
                }
            ):
                raise ValueError("visual exposure epoch stream state changed")
            state = dict(item[1])
            if (
                isinstance(state["sequence"], bool)
                or not isinstance(state["sequence"], int)
                or state["sequence"] < 0
                or isinstance(state["last_activity"], bool)
                or not isinstance(state["last_activity"], (int, float))
                or not math.isfinite(float(state["last_activity"]))
            ):
                raise ValueError("visual exposure epoch sequence changed")
            for key in (
                "auditory_pcm_receipt_sha256",
                "authority_receipt_sha256",
                "current_preparation_receipt_sha256",
                "current_terminal_frame_sha256",
            ):
                _sha256(state[key], f"visual exposure state {key}")
            if item[0] in restored:
                raise ValueError("visual exposure epoch repeated a stream")
            restored[item[0]] = state
        with self._lock:
            self._streams = restored

    def status(self) -> dict[str, object]:
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            return {
                "active_streams": len(self._streams),
                "stream_capacity": self._stream_capacity,
                "retained_raw_frame_bytes": 0,
                "persistence": "disabled",
                "identity_authority": False,
            }


__all__ = (
    "MAX_VISUAL_EXPOSURE_EPOCH_STATE_BYTES",
    "VISUAL_EXPOSURE_EPOCH_SCHEMA",
    "VisualExposureEpochAuthority",
    "VisualExposureEpochEvidence",
)
