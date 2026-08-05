"""Exact immutable evidence shared by the clean GLEW upstream providers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from fractions import Fraction
from types import MappingProxyType
from typing import Mapping, Sequence


_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class ReceiptError(ValueError):
    """A required physical or interface receipt is absent or inconsistent."""


def sha256_digest(value: str, field_name: str = "receipt_sha256") -> str:
    """Validate the canonical lowercase encoding of a SHA-256 digest."""

    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ReceiptError(f"{field_name} must be 64 lowercase hexadecimal characters")
    return value


def receipt_sha256(payload: bytes) -> str:
    """Return the digest used to bind an immutable receipt payload."""

    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class ReceiptRecord:
    """Exact immutable receipt bytes bound to their verified digest."""

    digest: str
    payload: bytes

    def __post_init__(self) -> None:
        sha256_digest(self.digest, "receipt.digest")
        if not isinstance(self.payload, bytes) or not self.payload:
            raise ReceiptError("receipt payload must be nonempty exact bytes")
        if receipt_sha256(self.payload) != self.digest:
            raise ReceiptError("receipt payload does not match its SHA-256 digest")


@dataclass(frozen=True, slots=True)
class ReceiptRegistry:
    """Mounted receipt authority for one exact profile binding.

    A digest-shaped string is never accepted as proof by itself.  Every digest
    used at runtime must resolve to exact verified bytes in this immutable
    registry, and every evidence stream carries this registry's profile bind.
    """

    profile_binding_sha256: str
    records: tuple[ReceiptRecord, ...]
    _by_digest: Mapping[str, bytes] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        sha256_digest(self.profile_binding_sha256, "profile_binding_sha256")
        if not isinstance(self.records, tuple) or not self.records:
            raise ReceiptError("receipt registry requires immutable receipt records")
        by_digest: dict[str, bytes] = {}
        for record in self.records:
            if not isinstance(record, ReceiptRecord):
                raise ReceiptError("receipt registry contains a non-receipt record")
            if record.digest in by_digest:
                raise ReceiptError("receipt registry contains a duplicate digest")
            by_digest[record.digest] = record.payload
        if self.profile_binding_sha256 not in by_digest:
            raise ReceiptError("profile binding bytes must be mounted in the registry")
        object.__setattr__(self, "_by_digest", MappingProxyType(by_digest))

    @classmethod
    def from_payloads(
        cls,
        *,
        profile_payload: bytes,
        receipt_payloads: Sequence[bytes],
    ) -> "ReceiptRegistry":
        if not isinstance(profile_payload, bytes) or not profile_payload:
            raise ReceiptError("profile payload must be nonempty exact bytes")
        payloads = (profile_payload, *tuple(receipt_payloads))
        records = tuple(
            ReceiptRecord(digest=receipt_sha256(payload), payload=payload)
            for payload in payloads
        )
        return cls(
            profile_binding_sha256=receipt_sha256(profile_payload),
            records=records,
        )

    def resolve(self, digest: str, field_name: str = "receipt") -> bytes:
        sha256_digest(digest, field_name)
        try:
            return self._by_digest[digest]
        except KeyError as exc:
            raise ReceiptError(f"{field_name} is not mounted in the active receipt registry") from exc


def require_identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ReceiptError(f"{field_name} must be a nonempty canonical identifier")
    return value


def require_fraction(value: Fraction, field_name: str) -> Fraction:
    if not isinstance(value, Fraction):
        raise ReceiptError(f"{field_name} must be fractions.Fraction")
    return value


@dataclass(frozen=True, slots=True)
class EvidenceSample:
    """One admitted exact sample from one independently retained port."""

    source_index: int
    timestamp: Fraction
    signal: Fraction
    relevance: Fraction
    phase_turns: Fraction

    def __post_init__(self) -> None:
        if isinstance(self.source_index, bool) or not isinstance(self.source_index, int):
            raise ReceiptError("source_index must be an integer")
        if self.source_index < 0:
            raise ReceiptError("source_index cannot be negative")
        require_fraction(self.timestamp, "timestamp")
        require_fraction(self.signal, "signal")
        require_fraction(self.relevance, "relevance")
        require_fraction(self.phase_turns, "phase_turns")
        if not -1 <= self.signal <= 1:
            raise ReceiptError("signal must remain in the calibrated interval [-1, 1]")
        if not 0 <= self.relevance <= 1:
            raise ReceiptError("relevance must remain in the exact interval [0, 1]")


@dataclass(frozen=True, slots=True)
class EvidenceStream:
    """One port's evidence; a stream is never an aggregate of native ports."""

    lane_id: str
    port_id: str
    evidence_id: str
    source_epoch: str
    port_kind: str
    physical_unit: str
    profile_binding_sha256: str
    calibration_receipt_sha256: str
    relevance_receipt_sha256: str
    samples: tuple[EvidenceSample, ...]

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, "lane_id")
        require_identifier(self.port_id, "port_id")
        require_identifier(self.evidence_id, "evidence_id")
        require_identifier(self.source_epoch, "source_epoch")
        require_identifier(self.port_kind, "port_kind")
        require_identifier(self.physical_unit, "physical_unit")
        sha256_digest(self.profile_binding_sha256, "profile_binding_sha256")
        sha256_digest(self.calibration_receipt_sha256, "calibration_receipt_sha256")
        sha256_digest(self.relevance_receipt_sha256, "relevance_receipt_sha256")
        if not isinstance(self.samples, tuple) or not self.samples:
            raise ReceiptError("evidence stream requires a nonempty immutable sample tuple")
        previous_index = self.samples[0].source_index - 1
        previous_time: Fraction | None = None
        for sample in self.samples:
            if sample.source_index != previous_index + 1:
                raise ReceiptError("evidence stream indices must be consecutive")
            if previous_time is not None and sample.timestamp <= previous_time:
                raise ReceiptError("evidence stream timestamps must be strictly increasing")
            previous_index = sample.source_index
            previous_time = sample.timestamp

    @property
    def key(self) -> tuple[str, str]:
        return (self.lane_id, self.port_id)
