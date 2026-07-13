"""Typed-language authority as an explicit artificial interface event.

Text is not represented as ligand chemistry.  An admitted valid trit carries
unit event relevance because its occurrence at this interface is a proved
binary fact, not a guessed semantic or biological magnitude.  Signal content,
event relevance, phase, original bytes, and NFC-normalized Unicode remain
separate receipts.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Sequence

from .model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptError,
    ReceiptRegistry,
    require_fraction,
    require_identifier,
    sha256_digest,
)


TRIT_PLACES = 14


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def typed_interface_receipt_payload(interface_id: str) -> bytes:
    return _canonical_bytes(
        {
            "interface_id": interface_id,
            "relevance_authority": "one_iff_valid_interface_event_admitted",
            "schema": "glew.typed_artificial_interface.v1",
            "transduction": "explicitly_artificial_not_chemistry",
        }
    )


def typed_phase_calibration_receipt_payload(
    phase_calibration_id: str, phase_kappa: Fraction
) -> bytes:
    return _canonical_bytes(
        {
            "phase_calibration_id": phase_calibration_id,
            "phase_kappa_turns_per_trit_per_source_time": _fraction_text(phase_kappa),
            "schema": "glew.typed_phase_calibration.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class BalancedTrit:
    scalar_index: int
    place: int
    value: int
    valid: bool

    def __post_init__(self) -> None:
        if self.scalar_index < 0:
            raise ReceiptError("scalar_index cannot be negative")
        if not 0 <= self.place < TRIT_PLACES:
            raise ReceiptError("balanced-ternary place is outside the 14-place receipt")
        if self.value not in (-1, 0, 1):
            raise ReceiptError("balanced trit must be -1, 0, or +1")
        if not isinstance(self.valid, bool):
            raise ReceiptError("balanced-trit validity must be a bool")


def encode_balanced_ternary_scalar(codepoint: int, scalar_index: int = 0) -> tuple[BalancedTrit, ...]:
    """Encode one Unicode scalar in 14 LSF places with explicit padding validity."""

    if isinstance(codepoint, bool) or not isinstance(codepoint, int):
        raise ReceiptError("Unicode scalar must be an integer")
    if not 0 <= codepoint <= 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
        raise ReceiptError("value is not a Unicode scalar")
    if isinstance(scalar_index, bool) or not isinstance(scalar_index, int):
        raise ReceiptError("scalar_index must be an integer")

    remaining = codepoint
    values: list[int] = []
    if remaining == 0:
        values.append(0)
    while remaining:
        remaining, remainder = divmod(remaining, 3)
        if remainder == 2:
            remainder = -1
            remaining += 1
        values.append(remainder)
    if len(values) > TRIT_PLACES:
        raise ReceiptError("Unicode scalar exceeds the canonical 14-place encoding")
    return tuple(
        BalancedTrit(
            scalar_index=scalar_index,
            place=place,
            value=values[place] if place < len(values) else 0,
            valid=place < len(values),
        )
        for place in range(TRIT_PLACES)
    )


@dataclass(frozen=True, slots=True)
class TypedLanguageEvent:
    event_id: str
    interface_id: str
    source_epoch: str
    original_utf8: bytes
    normalized_text: str
    trits: tuple[BalancedTrit, ...]
    valid_sample_times: tuple[Fraction, ...]
    interface_receipt_sha256: str
    event_receipt_sha256: str
    phase_calibration_id: str
    phase_kappa: Fraction
    phase_calibration_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.event_id, "event_id")
        require_identifier(self.interface_id, "interface_id")
        require_identifier(self.source_epoch, "source_epoch")
        if not isinstance(self.original_utf8, bytes):
            raise ReceiptError("original_utf8 must be bytes")
        if not isinstance(self.normalized_text, str) or not self.normalized_text:
            raise ReceiptError("typed-language event cannot be empty")
        if unicodedata.normalize("NFC", self.original_utf8.decode("utf-8")) != self.normalized_text:
            raise ReceiptError("normalized_text must be NFC of original_utf8")
        if not isinstance(self.trits, tuple) or not self.trits:
            raise ReceiptError("typed-language event requires balanced-trit receipts")
        valid_count = sum(trit.valid for trit in self.trits)
        if len(self.valid_sample_times) != valid_count:
            raise ReceiptError("one exact source timestamp is required for every valid trit")
        previous: Fraction | None = None
        for timestamp in self.valid_sample_times:
            require_fraction(timestamp, "valid_sample_time")
            if previous is not None and timestamp <= previous:
                raise ReceiptError("typed-language source timestamps must increase strictly")
            previous = timestamp
        sha256_digest(self.interface_receipt_sha256, "interface_receipt_sha256")
        sha256_digest(self.event_receipt_sha256, "event_receipt_sha256")
        require_identifier(self.phase_calibration_id, "phase_calibration_id")
        require_fraction(self.phase_kappa, "phase_kappa")
        sha256_digest(
            self.phase_calibration_receipt_sha256,
            "phase_calibration_receipt_sha256",
        )

    @classmethod
    def from_text(
        cls,
        *,
        text: str,
        event_id: str,
        interface_id: str,
        source_epoch: str,
        valid_sample_times: Sequence[Fraction],
        interface_receipt_sha256: str,
        event_receipt_sha256: str,
        phase_calibration_id: str,
        phase_kappa: Fraction,
        phase_calibration_receipt_sha256: str,
    ) -> "TypedLanguageEvent":
        if not isinstance(text, str) or not text:
            raise ReceiptError("typed-language event requires nonempty Unicode text")
        original = text.encode("utf-8")
        normalized = unicodedata.normalize("NFC", text)
        trits = tuple(
            trit
            for scalar_index, scalar in enumerate(normalized)
            for trit in encode_balanced_ternary_scalar(ord(scalar), scalar_index)
        )
        return cls(
            event_id=event_id,
            interface_id=interface_id,
            source_epoch=source_epoch,
            original_utf8=original,
            normalized_text=normalized,
            trits=trits,
            valid_sample_times=tuple(valid_sample_times),
            interface_receipt_sha256=interface_receipt_sha256,
            event_receipt_sha256=event_receipt_sha256,
            phase_calibration_id=phase_calibration_id,
            phase_kappa=phase_kappa,
            phase_calibration_receipt_sha256=phase_calibration_receipt_sha256,
        )

    def canonical_event_payload(self) -> bytes:
        return _canonical_bytes(
            {
                "event_id": self.event_id,
                "interface_id": self.interface_id,
                "normalized_text": self.normalized_text,
                "original_utf8_hex": self.original_utf8.hex(),
                "schema": "glew.typed_language_event.v1",
                "source_epoch": self.source_epoch,
                "trits": [
                    {
                        "place": trit.place,
                        "scalar_index": trit.scalar_index,
                        "valid": trit.valid,
                        "value": trit.value,
                    }
                    for trit in self.trits
                ],
                "valid_sample_times": [
                    _fraction_text(value) for value in self.valid_sample_times
                ],
            }
        )


def typed_language_event_receipt_payload(
    *,
    text: str,
    event_id: str,
    interface_id: str,
    source_epoch: str,
    valid_sample_times: Sequence[Fraction],
) -> bytes:
    """Build exact event bytes before constructing its digest-bound object."""

    if not isinstance(text, str) or not text:
        raise ReceiptError("typed-language event requires nonempty Unicode text")
    normalized = unicodedata.normalize("NFC", text)
    trits = tuple(
        trit
        for scalar_index, scalar in enumerate(normalized)
        for trit in encode_balanced_ternary_scalar(ord(scalar), scalar_index)
    )
    provisional = TypedLanguageEvent(
        event_id=event_id,
        interface_id=interface_id,
        source_epoch=source_epoch,
        original_utf8=text.encode("utf-8"),
        normalized_text=normalized,
        trits=trits,
        valid_sample_times=tuple(valid_sample_times),
        interface_receipt_sha256="0" * 64,
        event_receipt_sha256="0" * 64,
        phase_calibration_id="payload-only",
        phase_kappa=Fraction(0),
        phase_calibration_receipt_sha256="0" * 64,
    )
    return provisional.canonical_event_payload()


@dataclass(frozen=True, slots=True)
class TypedLanguageState:
    phase_calibration_id: str
    source_epoch: str
    last_source_index: int
    last_timestamp: Fraction
    phase_turns: Fraction
    genesis_receipt_sha256: str
    disrupted: bool = False

    def __post_init__(self) -> None:
        require_identifier(self.phase_calibration_id, "phase_calibration_id")
        require_identifier(self.source_epoch, "source_epoch")
        if self.last_source_index < -1:
            raise ReceiptError("last_source_index cannot be less than -1")
        require_fraction(self.last_timestamp, "last_timestamp")
        require_fraction(self.phase_turns, "phase_turns")
        sha256_digest(self.genesis_receipt_sha256, "genesis_receipt_sha256")


def capture_typed_language(
    event: TypedLanguageEvent,
    initial_state: TypedLanguageState,
    receipt_registry: ReceiptRegistry,
) -> tuple[EvidenceStream, TypedLanguageState]:
    """Admit one artificial interface event with exact unit-event relevance."""

    if event.phase_calibration_id != initial_state.phase_calibration_id:
        raise ReceiptError("typed-language phase calibration does not match state")
    if event.source_epoch != initial_state.source_epoch:
        raise ReceiptError("typed-language source epoch changed")
    if initial_state.disrupted:
        raise ReceiptError("disrupted typed-language state requires explicit recalibration")
    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("a mounted immutable receipt registry is required")
    mounted_interface = receipt_registry.resolve(
        event.interface_receipt_sha256, "interface_receipt_sha256"
    )
    if mounted_interface != typed_interface_receipt_payload(event.interface_id):
        raise ReceiptError("typed interface does not match its mounted authority receipt")
    mounted_phase = receipt_registry.resolve(
        event.phase_calibration_receipt_sha256,
        "phase_calibration_receipt_sha256",
    )
    if mounted_phase != typed_phase_calibration_receipt_payload(
        event.phase_calibration_id, event.phase_kappa
    ):
        raise ReceiptError("typed phase fields do not match the mounted calibration receipt")
    mounted_event = receipt_registry.resolve(
        event.event_receipt_sha256, "event_receipt_sha256"
    )
    if mounted_event != event.canonical_event_payload():
        raise ReceiptError("typed event values do not match the mounted event receipt")
    receipt_registry.resolve(initial_state.genesis_receipt_sha256, "genesis_receipt_sha256")

    valid_trits = tuple(trit for trit in event.trits if trit.valid)
    state = initial_state
    samples: list[EvidenceSample] = []
    for trit, timestamp in zip(valid_trits, event.valid_sample_times, strict=True):
        if timestamp < state.last_timestamp or (
            state.last_source_index >= 0 and timestamp == state.last_timestamp
        ):
            raise ReceiptError("typed-language source time is not strictly increasing")
        source_index = state.last_source_index + 1
        signal = Fraction(trit.value)
        phase = state.phase_turns + event.phase_kappa * signal * (
            timestamp - state.last_timestamp
        )
        samples.append(
            EvidenceSample(
                source_index=source_index,
                timestamp=timestamp,
                signal=signal,
                relevance=Fraction(1),
                phase_turns=phase,
            )
        )
        state = replace(
            state,
            last_source_index=source_index,
            last_timestamp=timestamp,
            phase_turns=phase,
        )

    return (
        EvidenceStream(
            lane_id="language",
            port_id=event.interface_id,
            evidence_id=event.event_id,
            source_epoch=event.source_epoch,
            port_kind="artificial_interface_event",
            physical_unit="valid_balanced_trit_event",
            profile_binding_sha256=receipt_registry.profile_binding_sha256,
            calibration_receipt_sha256=event.phase_calibration_receipt_sha256,
            relevance_receipt_sha256=event.interface_receipt_sha256,
            samples=tuple(samples),
        ),
        state,
    )
