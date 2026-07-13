"""Fail-closed native multi-port coupling without scalar-port flattening.

The coupler performs only the exact operation declared by a mounted receipt:
an affine raw-code calibration followed by exact Krimelack phase transport.
Native relevance is supplied by the native port's own receipted physical
operator.  This module never fabricates kinetics or chooses between ports.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from typing import Mapping, Sequence

from .model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptError,
    ReceiptRegistry,
    require_fraction,
    require_identifier,
    receipt_sha256,
    sha256_digest,
)


class Sense(str, Enum):
    SIGHT = "sight"
    SOUND = "sound"
    TOUCH = "touch"
    SMELL = "smell"
    TASTE = "taste"


class PortKind(str, Enum):
    TONIC = "tonic"
    PHASIC = "phasic"


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


def native_port_calibration_receipt_payload(
    *,
    sense: Sense,
    transducer_id: str,
    port_id: str,
    port_kind: PortKind,
    physical_unit: str,
    raw_scale: Fraction,
    raw_offset: Fraction,
    phase_kappa: Fraction,
    calibration_id: str,
    physical_profile_receipt_sha256: str,
    relevance_operator_id: str,
    relevance_receipt_sha256: str,
) -> bytes:
    """Canonical boundary calibration receipt (not the native physics profile)."""

    return _canonical_bytes(
        {
            "calibration_id": calibration_id,
            "phase_kappa": _fraction_text(phase_kappa),
            "physical_profile_receipt_sha256": physical_profile_receipt_sha256,
            "physical_unit": physical_unit,
            "port_id": port_id,
            "port_kind": port_kind.value,
            "raw_offset": _fraction_text(raw_offset),
            "raw_scale": _fraction_text(raw_scale),
            "relevance_operator_id": relevance_operator_id,
            "relevance_receipt_sha256": relevance_receipt_sha256,
            "schema": "glew.native_port_calibration.v1",
            "sense": sense.value,
            "transducer_id": transducer_id,
        }
    )


@dataclass(frozen=True, slots=True)
class NativePortCalibration:
    """Signed authority for one native output port and no other port."""

    sense: Sense
    transducer_id: str
    port_id: str
    port_kind: PortKind
    physical_unit: str
    raw_scale: Fraction
    raw_offset: Fraction
    phase_kappa: Fraction
    calibration_id: str
    physical_profile_receipt_sha256: str
    calibration_receipt_sha256: str
    relevance_operator_id: str
    relevance_receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.sense, Sense):
            raise ReceiptError("sense must be a mounted sensory Sense")
        if not isinstance(self.port_kind, PortKind):
            raise ReceiptError("port_kind must be tonic or phasic")
        require_identifier(self.transducer_id, "transducer_id")
        require_identifier(self.port_id, "port_id")
        require_identifier(self.physical_unit, "physical_unit")
        require_identifier(self.calibration_id, "calibration_id")
        require_identifier(self.relevance_operator_id, "relevance_operator_id")
        require_fraction(self.raw_scale, "raw_scale")
        require_fraction(self.raw_offset, "raw_offset")
        require_fraction(self.phase_kappa, "phase_kappa")
        if self.raw_scale == 0:
            raise ReceiptError("raw_scale cannot be zero")
        sha256_digest(
            self.physical_profile_receipt_sha256,
            "physical_profile_receipt_sha256",
        )
        sha256_digest(self.calibration_receipt_sha256, "calibration_receipt_sha256")
        sha256_digest(self.relevance_receipt_sha256, "relevance_receipt_sha256")

    @property
    def key(self) -> tuple[str, str]:
        return (self.sense.value, self.port_id)

    def calibrate(self, raw_code: int) -> Fraction:
        if isinstance(raw_code, bool) or not isinstance(raw_code, int):
            raise ReceiptError("raw_code must be an integer")
        signal = self.raw_scale * raw_code + self.raw_offset
        if not -1 <= signal <= 1:
            raise ReceiptError("raw code maps outside [-1, 1]; saturation is forbidden")
        return signal

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.physical_profile_receipt_sha256,
            "physical_profile_receipt_sha256",
        )
        receipt_registry.resolve(
            self.relevance_receipt_sha256,
            "relevance_receipt_sha256",
        )
        mounted = receipt_registry.resolve(
            self.calibration_receipt_sha256,
            "calibration_receipt_sha256",
        )
        expected = self.canonical_receipt_payload()
        if mounted != expected:
            raise ReceiptError("native calibration fields do not match the mounted receipt")

    def canonical_receipt_payload(self) -> bytes:
        return native_port_calibration_receipt_payload(
            sense=self.sense,
            transducer_id=self.transducer_id,
            port_id=self.port_id,
            port_kind=self.port_kind,
            physical_unit=self.physical_unit,
            raw_scale=self.raw_scale,
            raw_offset=self.raw_offset,
            phase_kappa=self.phase_kappa,
            calibration_id=self.calibration_id,
            physical_profile_receipt_sha256=self.physical_profile_receipt_sha256,
            relevance_operator_id=self.relevance_operator_id,
            relevance_receipt_sha256=self.relevance_receipt_sha256,
        )


@dataclass(frozen=True, slots=True)
class NativePortSample:
    """A raw port sample with relevance from its native physical operator."""

    source_epoch: str
    sample_index: int
    timestamp: Fraction
    raw_code: int
    native_relevance: Fraction
    valid: bool = True
    fault: str | None = None

    def __post_init__(self) -> None:
        require_identifier(self.source_epoch, "source_epoch")
        if isinstance(self.sample_index, bool) or not isinstance(self.sample_index, int):
            raise ReceiptError("sample_index must be an integer")
        if self.sample_index < 0:
            raise ReceiptError("sample_index cannot be negative")
        require_fraction(self.timestamp, "timestamp")
        require_fraction(self.native_relevance, "native_relevance")
        if isinstance(self.raw_code, bool) or not isinstance(self.raw_code, int):
            raise ReceiptError("raw_code must be an integer")
        if not isinstance(self.valid, bool):
            raise ReceiptError("valid must be a bool")
        if self.valid:
            if self.fault is not None:
                raise ReceiptError("a valid sample cannot carry a fault")
            if not 0 <= self.native_relevance <= 1:
                raise ReceiptError("native relevance must be in [0, 1]")
        else:
            require_identifier(self.fault or "", "fault")


def native_sample_batch_receipt_payload(
    *,
    batch_id: str,
    calibration_id: str,
    port_id: str,
    samples: Sequence[NativePortSample],
) -> bytes:
    return _canonical_bytes(
        {
            "batch_id": batch_id,
            "calibration_id": calibration_id,
            "port_id": port_id,
            "samples": [
                {
                    "fault": sample.fault,
                    "native_relevance": _fraction_text(sample.native_relevance),
                    "raw_code": sample.raw_code,
                    "sample_index": sample.sample_index,
                    "source_epoch": sample.source_epoch,
                    "timestamp": _fraction_text(sample.timestamp),
                    "valid": sample.valid,
                }
                for sample in samples
            ],
            "schema": "glew.native_port_sample_batch.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class NativeSampleBatch:
    """Mounted output receipt binding every native value supplied to coupling."""

    batch_id: str
    calibration_id: str
    port_id: str
    samples: tuple[NativePortSample, ...]
    batch_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.batch_id, "batch_id")
        require_identifier(self.calibration_id, "calibration_id")
        require_identifier(self.port_id, "port_id")
        if not isinstance(self.samples, tuple) or not self.samples:
            raise ReceiptError("native sample batch requires a nonempty immutable tuple")
        if not all(isinstance(sample, NativePortSample) for sample in self.samples):
            raise ReceiptError("native sample batch contains a non-sample value")
        sha256_digest(self.batch_receipt_sha256, "batch_receipt_sha256")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        mounted = receipt_registry.resolve(
            self.batch_receipt_sha256, "batch_receipt_sha256"
        )
        expected = native_sample_batch_receipt_payload(
            batch_id=self.batch_id,
            calibration_id=self.calibration_id,
            port_id=self.port_id,
            samples=self.samples,
        )
        if mounted != expected:
            raise ReceiptError("native sample values do not match the mounted batch receipt")

    @classmethod
    def from_samples(
        cls,
        *,
        batch_id: str,
        calibration_id: str,
        port_id: str,
        samples: Sequence[NativePortSample],
    ) -> tuple["NativeSampleBatch", bytes]:
        frozen_samples = tuple(samples)
        payload = native_sample_batch_receipt_payload(
            batch_id=batch_id,
            calibration_id=calibration_id,
            port_id=port_id,
            samples=frozen_samples,
        )
        return (
            cls(
                batch_id=batch_id,
                calibration_id=calibration_id,
                port_id=port_id,
                samples=frozen_samples,
                batch_receipt_sha256=receipt_sha256(payload),
            ),
            payload,
        )


@dataclass(frozen=True, slots=True)
class NativePortState:
    """Persistent exact source and phase state; gates never reset this state."""

    calibration_id: str
    source_epoch: str
    last_sample_index: int
    last_timestamp: Fraction
    phase_turns: Fraction
    genesis_receipt_sha256: str
    disrupted: bool = False

    def __post_init__(self) -> None:
        require_identifier(self.calibration_id, "calibration_id")
        require_identifier(self.source_epoch, "source_epoch")
        if isinstance(self.last_sample_index, bool) or not isinstance(
            self.last_sample_index, int
        ):
            raise ReceiptError("last_sample_index must be an integer")
        if self.last_sample_index < -1:
            raise ReceiptError("last_sample_index cannot be less than -1")
        require_fraction(self.last_timestamp, "last_timestamp")
        require_fraction(self.phase_turns, "phase_turns")
        sha256_digest(self.genesis_receipt_sha256, "genesis_receipt_sha256")
        if not isinstance(self.disrupted, bool):
            raise ReceiptError("disrupted must be a bool")


@dataclass(frozen=True, slots=True)
class CouplingFailure:
    port_key: tuple[str, str]
    reason: str

    def __post_init__(self) -> None:
        require_identifier(self.reason, "reason")


@dataclass(frozen=True, slots=True)
class CouplingResult:
    """Pure result: failure carries the updated disrupted state and no evidence."""

    state: NativePortState
    evidence: EvidenceStream | None
    failure: CouplingFailure | None

    def __post_init__(self) -> None:
        if (self.evidence is None) == (self.failure is None):
            raise ReceiptError("coupling result must carry exactly evidence or failure")


def _latched_state(state: NativePortState, sample: NativePortSample) -> NativePortState:
    """Advance provable source time/index while refusing phase extrapolation."""

    next_index = max(state.last_sample_index, sample.sample_index)
    next_time = max(state.last_timestamp, sample.timestamp)
    return replace(
        state,
        last_sample_index=next_index,
        last_timestamp=next_time,
        disrupted=True,
    )


def _failure(
    calibration: NativePortCalibration,
    state: NativePortState,
    sample: NativePortSample,
    reason: str,
) -> CouplingResult:
    return CouplingResult(
        state=_latched_state(state, sample),
        evidence=None,
        failure=CouplingFailure(calibration.key, reason),
    )


def couple_native_port(
    calibration: NativePortCalibration,
    sample_batch: NativeSampleBatch,
    initial_state: NativePortState,
    receipt_registry: ReceiptRegistry,
) -> CouplingResult:
    """Couple one native port with exact rational calibration and phase.

    Any fault invalidates the whole open batch.  Source time advances when it
    can be ordered, phase does not extrapolate, and disruption stays latched.
    """

    if not isinstance(calibration, NativePortCalibration):
        raise ReceiptError("a native-port calibration receipt is required")
    if not isinstance(initial_state, NativePortState):
        raise ReceiptError("a persistent native-port phase state is required")
    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("a mounted immutable receipt registry is required")
    calibration.verify(receipt_registry)
    receipt_registry.resolve(initial_state.genesis_receipt_sha256, "genesis_receipt_sha256")
    if not isinstance(sample_batch, NativeSampleBatch):
        raise ReceiptError("native port coupling requires a mounted sample batch")
    sample_batch.verify(receipt_registry)
    if sample_batch.calibration_id != calibration.calibration_id:
        raise ReceiptError("sample batch calibration does not match the mounted port")
    if sample_batch.port_id != calibration.port_id:
        raise ReceiptError("sample batch port does not match the mounted port")
    if calibration.calibration_id != initial_state.calibration_id:
        raise ReceiptError("state calibration does not match the mounted port")
    if initial_state.disrupted:
        raise ReceiptError("disrupted phase state requires explicit recalibration authority")
    state = initial_state
    admitted: list[EvidenceSample] = []
    for sample in sample_batch.samples:
        if not isinstance(sample, NativePortSample):
            raise ReceiptError("all native samples must be NativePortSample receipts")
        if sample.source_epoch != state.source_epoch:
            return _failure(calibration, state, sample, "source_epoch_changed")
        if sample.sample_index != state.last_sample_index + 1:
            return _failure(calibration, state, sample, "nonconsecutive_sample_index")
        if sample.timestamp < state.last_timestamp or (
            state.last_sample_index >= 0 and sample.timestamp == state.last_timestamp
        ):
            return _failure(calibration, state, sample, "nonincreasing_source_time")
        if not sample.valid:
            return _failure(calibration, state, sample, f"invalid_sample:{sample.fault}")
        try:
            signal = calibration.calibrate(sample.raw_code)
        except ReceiptError as exc:
            return _failure(calibration, state, sample, f"calibration_fault:{exc}")

        delta_t = sample.timestamp - state.last_timestamp
        phase = state.phase_turns + calibration.phase_kappa * signal * delta_t
        admitted.append(
            EvidenceSample(
                source_index=sample.sample_index,
                timestamp=sample.timestamp,
                signal=signal,
                relevance=sample.native_relevance,
                phase_turns=phase,
            )
        )
        state = replace(
            state,
            last_sample_index=sample.sample_index,
            last_timestamp=sample.timestamp,
            phase_turns=phase,
        )

    return CouplingResult(
        state=state,
        evidence=EvidenceStream(
            lane_id=calibration.sense.value,
            port_id=calibration.port_id,
            evidence_id=(
                f"{state.source_epoch}:{calibration.port_id}:"
                f"{admitted[0].source_index}:{admitted[-1].source_index}"
            ),
            source_epoch=state.source_epoch,
            port_kind=calibration.port_kind.value,
            physical_unit=calibration.physical_unit,
            profile_binding_sha256=receipt_registry.profile_binding_sha256,
            calibration_receipt_sha256=calibration.calibration_receipt_sha256,
            relevance_receipt_sha256=calibration.relevance_receipt_sha256,
            samples=tuple(admitted),
        ),
        failure=None,
    )


def couple_mounted_sense(
    calibrations: Sequence[NativePortCalibration],
    sample_batches: Mapping[str, NativeSampleBatch],
    initial_states: Mapping[str, NativePortState],
    receipt_registry: ReceiptRegistry,
) -> tuple[CouplingResult, ...]:
    """Couple every mounted native port independently and in declared order.

    The mounted set, sample-batch set, and state set must match exactly.  A
    caller cannot silently omit an inconvenient port or inject an undeclared
    one.  No result in the returned tuple is averaged or selected.
    """

    if not isinstance(calibrations, Sequence) or isinstance(calibrations, (str, bytes)):
        raise ReceiptError("calibrations must be a sequence")
    if not calibrations:
        raise ReceiptError("at least one mounted native port is required")
    ports = tuple(calibration.port_id for calibration in calibrations)
    if len(set(ports)) != len(ports):
        raise ReceiptError("mounted native port ids must be unique within a sense")
    senses = {calibration.sense for calibration in calibrations}
    if len(senses) != 1:
        raise ReceiptError("one mounted-sense call cannot mix senses")
    expected = set(ports)
    if set(sample_batches) != expected:
        raise ReceiptError("sample batches must exactly match the mounted native ports")
    if set(initial_states) != expected:
        raise ReceiptError("phase states must exactly match the mounted native ports")
    return tuple(
        couple_native_port(
            calibration,
            sample_batches[calibration.port_id],
            initial_states[calibration.port_id],
            receipt_registry,
        )
        for calibration in calibrations
    )
