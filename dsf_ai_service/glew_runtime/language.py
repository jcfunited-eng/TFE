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

from .closed_experience import (
    KernelNativeInputSample,
    KernelNativeInputStream,
    kernel_native_input_receipt_payload,
    source_evidence_stream_receipt_payload,
)
from .model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
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
        expected_trits = tuple(
            trit
            for scalar_index, scalar in enumerate(self.normalized_text)
            for trit in encode_balanced_ternary_scalar(
                ord(scalar),
                scalar_index,
            )
        )
        if self.trits != expected_trits:
            raise ReceiptError(
                "typed-language trits differ from canonical scalar encoding"
            )
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


def _capture_typed_language_on_complete_grid(
    *,
    event: TypedLanguageEvent,
    initial_state: TypedLanguageState,
    complete_grid_times: tuple[Fraction, ...],
    receipt_registry: ReceiptRegistry,
) -> tuple[EvidenceStream, TypedLanguageState]:
    """Preserve every canonical trit place on one complete causal grid."""

    capture_typed_language(event, initial_state, receipt_registry)
    if (
        not isinstance(complete_grid_times, tuple)
        or len(complete_grid_times) != len(event.trits)
    ):
        raise ReceiptError(
            "complete typed grid requires one time for every canonical trit place"
        )
    previous: Fraction | None = None
    for timestamp in complete_grid_times:
        require_fraction(timestamp, "complete typed-grid timestamp")
        if previous is not None and timestamp <= previous:
            raise ReceiptError(
                "complete typed-grid timestamps must increase strictly"
            )
        previous = timestamp
    admitted_times = tuple(
        timestamp
        for trit, timestamp in zip(
            event.trits,
            complete_grid_times,
            strict=True,
        )
        if trit.valid
    )
    if admitted_times != event.valid_sample_times:
        raise ReceiptError(
            "typed event valid-place times differ from the complete grid"
        )

    state = initial_state
    samples: list[EvidenceSample] = []
    for trit, timestamp in zip(
        event.trits,
        complete_grid_times,
        strict=True,
    ):
        if timestamp < state.last_timestamp or (
            state.last_source_index >= 0 and timestamp == state.last_timestamp
        ):
            raise ReceiptError("typed-language source time is not strictly increasing")
        source_index = state.last_source_index + 1
        signal = Fraction(trit.value)
        relevance = Fraction(1) if trit.valid else Fraction(0)
        phase = state.phase_turns + event.phase_kappa * signal * (
            timestamp - state.last_timestamp
        )
        samples.append(
            EvidenceSample(
                source_index=source_index,
                timestamp=timestamp,
                signal=signal,
                relevance=relevance,
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
            physical_unit="canonical_balanced_trit_place",
            profile_binding_sha256=receipt_registry.profile_binding_sha256,
            calibration_receipt_sha256=event.phase_calibration_receipt_sha256,
            relevance_receipt_sha256=event.interface_receipt_sha256,
            samples=tuple(samples),
        ),
        state,
    )


def typed_language_state_receipt_payload(state: TypedLanguageState) -> bytes:
    if not isinstance(state, TypedLanguageState):
        raise ReceiptError("typed-language state receipt requires a typed state")
    return _canonical_bytes(
        {
            "disrupted": state.disrupted,
            "genesis_receipt_sha256": state.genesis_receipt_sha256,
            "last_source_index": state.last_source_index,
            "last_timestamp": _fraction_text(state.last_timestamp),
            "phase_calibration_id": state.phase_calibration_id,
            "phase_turns": _fraction_text(state.phase_turns),
            "schema": "glew.typed_language_state.v1",
            "source_epoch": state.source_epoch,
        }
    )


def typed_language_kernel_binding_receipt_payload(
    *,
    adapter_id: str,
    interface_id: str,
    interface_receipt_sha256: str,
    phase_calibration_receipt_sha256: str,
    derivation_receipt_sha256: str,
) -> bytes:
    for value, description in (
        (interface_receipt_sha256, "typed kernel interface receipt"),
        (
            phase_calibration_receipt_sha256,
            "typed kernel phase-calibration receipt",
        ),
        (derivation_receipt_sha256, "typed kernel derivation receipt"),
    ):
        sha256_digest(value, description)
    return _canonical_bytes(
        {
            "adapter_id": require_identifier(
                adapter_id,
                "typed-language kernel adapter id",
            ),
            "derivation_receipt_sha256": derivation_receipt_sha256,
            "interface_id": require_identifier(
                interface_id,
                "typed-language kernel interface id",
            ),
            "interface_receipt_sha256": interface_receipt_sha256,
            "kernel_map": {
                "forward": "F=1+s/2",
                "inverse": "s=2*(F-1)",
                "relevance": "valid_typed_interface_event_identity",
                "signal_domain": "balanced_trit_-1_0_1",
            },
            "phase_calibration_receipt_sha256": (
                phase_calibration_receipt_sha256
            ),
            "schema": "glew.typed_language_frozen_kernel_binding.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class MountedTypedLanguageKernelBinding:
    adapter_id: str
    interface_id: str
    interface_receipt_sha256: str
    phase_calibration_receipt_sha256: str
    derivation_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return typed_language_kernel_binding_receipt_payload(
            adapter_id=self.adapter_id,
            interface_id=self.interface_id,
            interface_receipt_sha256=self.interface_receipt_sha256,
            phase_calibration_receipt_sha256=(
                self.phase_calibration_receipt_sha256
            ),
            derivation_receipt_sha256=self.derivation_receipt_sha256,
        )

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        for digest, description in (
            (self.interface_receipt_sha256, "typed interface receipt"),
            (
                self.phase_calibration_receipt_sha256,
                "typed phase-calibration receipt",
            ),
            (self.derivation_receipt_sha256, "typed kernel derivation receipt"),
        ):
            receipt_registry.resolve(digest, description)
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256,
            "typed-language frozen-kernel binding receipt",
        )
        expected = self.payload()
        if (
            mounted != expected
            or receipt_sha256(expected) != self.authority_receipt_sha256
        ):
            raise ReceiptError(
                "typed-language frozen-kernel binding differs from receipt"
            )


def typed_language_capture_receipt_payload(
    *,
    event_receipt_sha256: str,
    initial_state_receipt_sha256: str,
    final_state_receipt_sha256: str,
    source_stream_receipt_sha256: str,
    kernel_binding_receipt_sha256: str,
) -> bytes:
    for value, description in (
        (event_receipt_sha256, "typed capture event receipt"),
        (initial_state_receipt_sha256, "typed capture initial-state receipt"),
        (final_state_receipt_sha256, "typed capture final-state receipt"),
        (source_stream_receipt_sha256, "typed capture source-stream receipt"),
        (kernel_binding_receipt_sha256, "typed capture kernel-binding receipt"),
    ):
        sha256_digest(value, description)
    return _canonical_bytes(
        {
            "event_receipt_sha256": event_receipt_sha256,
            "final_state_receipt_sha256": final_state_receipt_sha256,
            "initial_state_receipt_sha256": initial_state_receipt_sha256,
            "kernel_binding_receipt_sha256": kernel_binding_receipt_sha256,
            "operator": "glew.typed_language.capture_to_frozen_kernel.v1",
            "schema": "glew.typed_language_capture.v1",
            "source_stream_receipt_sha256": source_stream_receipt_sha256,
        }
    )


def _extend_registry(
    receipt_registry: ReceiptRegistry,
    payloads: Sequence[bytes],
) -> ReceiptRegistry:
    records = list(receipt_registry.records)
    mounted = {value.digest: value.payload for value in records}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("typed-language bridge produced an empty receipt")
        digest = receipt_sha256(payload)
        if digest in mounted:
            if mounted[digest] != payload:
                raise ReceiptError("typed-language bridge receipt collision")
            continue
        records.append(ReceiptRecord(digest, payload))
        mounted[digest] = payload
    return ReceiptRegistry(
        receipt_registry.profile_binding_sha256,
        tuple(records),
    )


@dataclass(frozen=True, slots=True)
class TypedLanguageFrozenKernelInput:
    event: TypedLanguageEvent
    initial_state: TypedLanguageState
    final_state: TypedLanguageState
    stream: EvidenceStream
    kernel_input: KernelNativeInputStream
    kernel_binding: MountedTypedLanguageKernelBinding
    initial_state_receipt_sha256: str
    final_state_receipt_sha256: str
    capture_receipt_sha256: str
    receipt_registry: ReceiptRegistry

    def verify(self) -> None:
        self.kernel_binding.verify(self.receipt_registry)
        if self.event.interface_id != self.kernel_binding.interface_id:
            raise ReceiptError("typed event uses another kernel interface")
        if (
            self.event.interface_receipt_sha256
            != self.kernel_binding.interface_receipt_sha256
            or self.event.phase_calibration_receipt_sha256
            != self.kernel_binding.phase_calibration_receipt_sha256
        ):
            raise ReceiptError("typed event uses another mounted kernel authority")
        initial_payload = typed_language_state_receipt_payload(
            self.initial_state
        )
        final_payload = typed_language_state_receipt_payload(self.final_state)
        for digest, payload, description in (
            (
                self.initial_state_receipt_sha256,
                initial_payload,
                "typed initial-state receipt",
            ),
            (
                self.final_state_receipt_sha256,
                final_payload,
                "typed final-state receipt",
            ),
        ):
            if (
                receipt_sha256(payload) != digest
                or self.receipt_registry.resolve(digest, description) != payload
            ):
                raise ReceiptError(f"{description} differs from exact state")
        if len(self.stream.samples) == len(self.event.trits):
            rebuilt_stream, rebuilt_state = (
                _capture_typed_language_on_complete_grid(
                    event=self.event,
                    initial_state=self.initial_state,
                    complete_grid_times=tuple(
                        value.timestamp for value in self.stream.samples
                    ),
                    receipt_registry=self.receipt_registry,
                )
            )
        else:
            rebuilt_stream, rebuilt_state = capture_typed_language(
                self.event,
                self.initial_state,
                self.receipt_registry,
            )
        if rebuilt_stream != self.stream or rebuilt_state != self.final_state:
            raise ReceiptError("typed capture cannot be reproduced exactly")
        stream_payload = source_evidence_stream_receipt_payload(self.stream)
        stream_digest = receipt_sha256(stream_payload)
        if self.receipt_registry.resolve(
            stream_digest,
            "typed source-stream receipt",
        ) != stream_payload:
            raise ReceiptError("typed source stream differs from mounted receipt")
        self.kernel_input.verify(self.stream, self.receipt_registry)
        capture_payload = typed_language_capture_receipt_payload(
            event_receipt_sha256=self.event.event_receipt_sha256,
            initial_state_receipt_sha256=self.initial_state_receipt_sha256,
            final_state_receipt_sha256=self.final_state_receipt_sha256,
            source_stream_receipt_sha256=stream_digest,
            kernel_binding_receipt_sha256=(
                self.kernel_binding.authority_receipt_sha256
            ),
        )
        if (
            receipt_sha256(capture_payload) != self.capture_receipt_sha256
            or self.receipt_registry.resolve(
                self.capture_receipt_sha256,
                "typed-language capture receipt",
            )
            != capture_payload
        ):
            raise ReceiptError("typed-language capture receipt changed")


def build_typed_language_frozen_kernel_input(
    *,
    event: TypedLanguageEvent,
    initial_state: TypedLanguageState,
    kernel_binding: MountedTypedLanguageKernelBinding,
    receipt_registry: ReceiptRegistry,
    complete_grid_times: Sequence[Fraction] | None = None,
) -> TypedLanguageFrozenKernelInput:
    """Capture one typed event and bind it to the frozen L0--L4 input map.

    When a complete grid is supplied, every canonical balanced-ternary place
    is retained.  Places inside the minimal representation keep unit event
    relevance even when their trit value is zero.  Only explicit
    padding-invalid places carry zero relevance.
    """

    if not isinstance(kernel_binding, MountedTypedLanguageKernelBinding):
        raise ReceiptError("typed language requires a mounted kernel binding")
    kernel_binding.verify(receipt_registry)
    if event.interface_id != kernel_binding.interface_id:
        raise ReceiptError("typed event interface differs from kernel binding")
    if (
        event.interface_receipt_sha256
        != kernel_binding.interface_receipt_sha256
        or event.phase_calibration_receipt_sha256
        != kernel_binding.phase_calibration_receipt_sha256
    ):
        raise ReceiptError("typed event authorities differ from kernel binding")
    if complete_grid_times is None:
        stream, final_state = capture_typed_language(
            event,
            initial_state,
            receipt_registry,
        )
        expected_relevance = tuple(
            Fraction(1) for _ in stream.samples
        )
    else:
        complete_times = tuple(complete_grid_times)
        stream, final_state = _capture_typed_language_on_complete_grid(
            event=event,
            initial_state=initial_state,
            complete_grid_times=complete_times,
            receipt_registry=receipt_registry,
        )
        expected_relevance = tuple(
            Fraction(1) if trit.valid else Fraction(0)
            for trit in event.trits
        )
    if not stream.samples:
        raise ReceiptError("typed event produced no kernel samples")
    if (
        tuple(value.relevance for value in stream.samples)
        != expected_relevance
        or any(
            value.signal not in (Fraction(-1), Fraction(0), Fraction(1))
            for value in stream.samples
        )
    ):
        raise ReceiptError(
            "typed kernel input lost exact trit-place validity or relevance"
        )
    stream_payload = source_evidence_stream_receipt_payload(stream)
    stream_digest = receipt_sha256(stream_payload)
    kernel_samples = tuple(
        KernelNativeInputSample(
            source_index=value.source_index,
            timestamp=value.timestamp,
            dimensionless_field=Fraction(1) + value.signal / 2,
            l0_relevance=value.relevance,
        )
        for value in stream.samples
    )
    kernel_payload = kernel_native_input_receipt_payload(
        adapter_id=kernel_binding.adapter_id,
        adapter_profile_receipt_sha256=(
            kernel_binding.authority_receipt_sha256
        ),
        lane_id=stream.lane_id,
        port_id=stream.port_id,
        source_stream_receipt_sha256=stream_digest,
        samples=kernel_samples,
    )
    kernel_input = KernelNativeInputStream(
        adapter_id=kernel_binding.adapter_id,
        adapter_profile_receipt_sha256=(
            kernel_binding.authority_receipt_sha256
        ),
        lane_id=stream.lane_id,
        port_id=stream.port_id,
        source_stream_receipt_sha256=stream_digest,
        samples=kernel_samples,
        authority_receipt_sha256=receipt_sha256(kernel_payload),
    )
    initial_payload = typed_language_state_receipt_payload(initial_state)
    final_payload = typed_language_state_receipt_payload(final_state)
    capture_payload = typed_language_capture_receipt_payload(
        event_receipt_sha256=event.event_receipt_sha256,
        initial_state_receipt_sha256=receipt_sha256(initial_payload),
        final_state_receipt_sha256=receipt_sha256(final_payload),
        source_stream_receipt_sha256=stream_digest,
        kernel_binding_receipt_sha256=kernel_binding.authority_receipt_sha256,
    )
    registry = _extend_registry(
        receipt_registry,
        (
            initial_payload,
            final_payload,
            stream_payload,
            kernel_payload,
            capture_payload,
        ),
    )
    result = TypedLanguageFrozenKernelInput(
        event=event,
        initial_state=initial_state,
        final_state=final_state,
        stream=stream,
        kernel_input=kernel_input,
        kernel_binding=kernel_binding,
        initial_state_receipt_sha256=receipt_sha256(initial_payload),
        final_state_receipt_sha256=receipt_sha256(final_payload),
        capture_receipt_sha256=receipt_sha256(capture_payload),
        receipt_registry=registry,
    )
    result.verify()
    return result
