"""Ratified native-sensory adapter into the exact six-sense L0--L4 boundary.

The adapter preserves each provider-declared substream independently, applies
the canonical invertible ``F = 1 + s/2`` map, and runs the frozen ``uf_core``
layers without changing them.  It returns a fully mounted and verified
``SixSenseFullFieldBoundary``.  No L5 meaning, chi identity, word label, or
compatibility vector is introduced here.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from .closed_experience import (
    KernelNativeInputSample,
    KernelNativeInputStream,
    kernel_native_input_receipt_payload,
    run_ratified_native_l0_l4_trace,
    source_evidence_stream_receipt_payload,
)
from .model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
)
from .sensory_full_field_boundary import (
    NativeAxisCoordinate,
    NativeSenseTopology,
    NativeSubstreamProfile,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
    SensoryFullFieldBoundary,
    SensorySubstreamFullField,
    SixSenseFullFieldBoundary,
    native_sense_topology_receipt_payload,
    native_substream_profile_receipt_payload,
    sensory_full_field_boundary_receipt_payload,
    six_sense_full_field_boundary_receipt_payload,
)
from .story_global_uf_basin import port_kernel_basin_from_trace_record


PROFILE_PAYLOAD = b"guala.live.native_sensory_l0_l4.profile.v1"
RELEVANCE_PAYLOAD = b"guala.live.native_sensory.exact_source_relevance.v1"
ADAPTER_PROFILE_PAYLOAD = b"guala.live.native_sensory.F_equals_1_plus_s_over_2.v1"

# Deterministic resource-safety boundary. These are transport/runtime limits,
# not sensory physics and not cognition. They cap the largest single causal
# settlement that this live adapter will admit so one request cannot recreate
# the historical unbounded-memory failure.
MAX_NATIVE_SUBSTREAMS_PER_SENSE = 16
MAX_NATIVE_SOUND_SUBSTREAMS = 32
MAX_NATIVE_SAMPLES_PER_SUBSTREAM = 2048
MAX_NATIVE_SAMPLES_PER_SETTLEMENT = 32768


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_from_binary64(value: object, name: str) -> Fraction:
    if isinstance(value, bool):
        raise ValueError(f"{name} is not a numeric sample")
    encoded = float(value)
    if not math.isfinite(encoded):
        raise ValueError(f"{name} must be finite")
    return Fraction.from_float(encoded)


def _unique_payloads(payloads: list[bytes]) -> tuple[bytes, ...]:
    by_digest: dict[str, bytes] = {}
    for payload in payloads:
        digest = receipt_sha256(payload)
        existing = by_digest.get(digest)
        if existing is not None and existing != payload:
            raise RuntimeError("sensory receipt digest collision")
        by_digest[digest] = payload
    return tuple(by_digest.values())


@dataclass(frozen=True, slots=True)
class NativeSensorySubstreamInput:
    sense: PhysicalSense
    sensor_id: str
    substream_id: str
    topology_index: int
    coordinates: tuple[NativeAxisCoordinate, ...]
    physical_quantity: str
    physical_unit: str
    source_times: tuple[Fraction, ...]
    normalized_signal: tuple[float, ...]
    phase_turns: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.sense, PhysicalSense):
            raise ValueError("native sensory input requires a typed sense")
        require_identifier(self.sensor_id, "native sensory sensor_id")
        require_identifier(self.substream_id, "native sensory substream_id")
        if self.topology_index < 0:
            raise ValueError("native sensory topology index cannot be negative")
        if not self.coordinates:
            raise ValueError("native sensory coordinates cannot be empty")
        if not self.normalized_signal:
            raise ValueError("native sensory signal cannot be empty")
        if len(self.normalized_signal) > MAX_NATIVE_SAMPLES_PER_SUBSTREAM:
            raise ValueError("native sensory substream exceeds the settlement sample boundary")
        if not (
            len(self.source_times)
            == len(self.normalized_signal)
            == len(self.phase_turns)
        ):
            raise ValueError("native sensory sample fields changed cardinality")
        previous = None
        for index, (timestamp, signal, phase) in enumerate(zip(
                self.source_times,
                self.normalized_signal,
                self.phase_turns,
                strict=True)):
            require_fraction(timestamp, f"native sensory timestamp {index}")
            require_fraction(phase, f"native sensory phase {index}")
            if previous is not None and timestamp <= previous:
                raise ValueError("native sensory timestamps must increase")
            previous = timestamp
            exact_signal = _fraction_from_binary64(
                signal, f"native sensory signal {index}")
            if not -1 <= exact_signal <= 1:
                raise ValueError("native sensory signal must remain in [-1,1]")


@dataclass(frozen=True, slots=True)
class BuiltSixSenseFullField:
    boundary: SixSenseFullFieldBoundary
    receipt_registry: ReceiptRegistry


@dataclass(frozen=True, slots=True)
class _PreparedPort:
    native: NativeSensorySubstreamInput
    stream: EvidenceStream
    adapter: KernelNativeInputStream
    profile: NativeSubstreamProfile
    input_payloads: tuple[bytes, ...]


def _prepare_port(
    native: NativeSensorySubstreamInput,
    *,
    assembly_id: str,
) -> _PreparedPort:
    profile_digest = receipt_sha256(PROFILE_PAYLOAD)
    calibration_payload = _canonical_bytes({
        "physical_quantity": native.physical_quantity,
        "physical_unit": native.physical_unit,
        "range": "[-1,1]",
        "schema": "guala.live.native_sensory_calibration.v1",
        "sense": native.sense.value,
        "sensor_id": native.sensor_id,
        "substream_id": native.substream_id,
    })
    calibration_digest = receipt_sha256(calibration_payload)
    relevance_digest = receipt_sha256(RELEVANCE_PAYLOAD)
    samples = tuple(
        EvidenceSample(
            source_index=index,
            timestamp=timestamp,
            signal=_fraction_from_binary64(signal, f"signal {index}"),
            relevance=Fraction(1),
            phase_turns=phase,
        )
        for index, (timestamp, signal, phase) in enumerate(zip(
            native.source_times,
            native.normalized_signal,
            native.phase_turns,
            strict=True,
        ))
    )
    stream = EvidenceStream(
        lane_id=native.sense.value,
        port_id=native.substream_id,
        evidence_id=f"evidence-{assembly_id}-{native.sense.value}-{native.topology_index}",
        source_epoch=assembly_id,
        port_kind=native.physical_quantity,
        physical_unit=native.physical_unit,
        profile_binding_sha256=profile_digest,
        calibration_receipt_sha256=calibration_digest,
        relevance_receipt_sha256=relevance_digest,
        samples=samples,
    )
    source_payload = source_evidence_stream_receipt_payload(stream)
    source_digest = receipt_sha256(source_payload)
    adapter_samples = tuple(
        KernelNativeInputSample(
            source_index=sample.source_index,
            timestamp=sample.timestamp,
            dimensionless_field=Fraction(1) + sample.signal / 2,
            l0_relevance=sample.relevance,
        )
        for sample in samples
    )
    adapter_payload = kernel_native_input_receipt_payload(
        adapter_id="guala-live-native-sensory",
        adapter_profile_receipt_sha256=receipt_sha256(ADAPTER_PROFILE_PAYLOAD),
        lane_id=native.sense.value,
        port_id=native.substream_id,
        source_stream_receipt_sha256=source_digest,
        samples=adapter_samples,
    )
    adapter = KernelNativeInputStream(
        adapter_id="guala-live-native-sensory",
        adapter_profile_receipt_sha256=receipt_sha256(ADAPTER_PROFILE_PAYLOAD),
        lane_id=native.sense.value,
        port_id=native.substream_id,
        source_stream_receipt_sha256=source_digest,
        samples=adapter_samples,
        authority_receipt_sha256=receipt_sha256(adapter_payload),
    )
    profile_payload = native_substream_profile_receipt_payload(
        sense=native.sense,
        sensor_id=native.sensor_id,
        substream_id=native.substream_id,
        topology_index=native.topology_index,
        coordinates=native.coordinates,
        physical_quantity=native.physical_quantity,
        physical_unit=native.physical_unit,
        physical_derivation_receipt_sha256=source_digest,
    )
    profile = NativeSubstreamProfile(
        sense=native.sense,
        sensor_id=native.sensor_id,
        substream_id=native.substream_id,
        topology_index=native.topology_index,
        coordinates=native.coordinates,
        physical_quantity=native.physical_quantity,
        physical_unit=native.physical_unit,
        physical_derivation_receipt_sha256=source_digest,
        authority_receipt_sha256=receipt_sha256(profile_payload),
    )
    return _PreparedPort(
        native=native,
        stream=stream,
        adapter=adapter,
        profile=profile,
        input_payloads=(
            calibration_payload,
            RELEVANCE_PAYLOAD,
            ADAPTER_PROFILE_PAYLOAD,
            source_payload,
            adapter_payload,
            profile_payload,
        ),
    )


def build_six_sense_full_field(
    *,
    assembly_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    observed_substreams: Mapping[
        PhysicalSense, tuple[NativeSensorySubstreamInput, ...]],
    states: Mapping[PhysicalSense, SenseBoundaryState],
) -> BuiltSixSenseFullField:
    """Build and verify one exact, complete six-sense pre-L5 boundary."""
    require_identifier(assembly_id, "six-sense assembly_id")
    require_fraction(source_time_start, "source_time_start")
    require_fraction(source_time_end, "source_time_end")
    if source_time_end <= source_time_start:
        raise ValueError("six-sense source interval must be positive")
    if set(states) != set(SENSE_ORDER):
        raise ValueError("six-sense states must explicitly cover every sense")
    if set(observed_substreams) != {
        sense for sense, state in states.items()
        if state is SenseBoundaryState.OBSERVED
    }:
        raise ValueError("observed sensory inputs and states disagree")

    for native_ports in observed_substreams.values():
        for port in native_ports:
            if (port.source_times[0] < source_time_start
                    or port.source_times[-1] > source_time_end):
                raise ValueError(
                    "native sensory sample time falls outside the causal interval")

    prepared_by_sense: dict[PhysicalSense, tuple[_PreparedPort, ...]] = {}
    payloads = [PROFILE_PAYLOAD]
    total_samples = 0
    for sense in SENSE_ORDER:
        native_ports = observed_substreams.get(sense, ())
        if native_ports:
            substream_capacity = (
                MAX_NATIVE_SOUND_SUBSTREAMS
                if sense is PhysicalSense.SOUND
                else MAX_NATIVE_SUBSTREAMS_PER_SENSE
            )
            if len(native_ports) > substream_capacity:
                raise ValueError("native sensory topology exceeds the settlement port boundary")
            if tuple(port.sense for port in native_ports) != (sense,) * len(native_ports):
                raise ValueError("native topology crosses sense boundaries")
            if tuple(port.topology_index for port in native_ports) != tuple(
                    range(len(native_ports))):
                raise ValueError("native sensory topology is incomplete or reordered")
            prepared = tuple(
                _prepare_port(port, assembly_id=assembly_id)
                for port in native_ports
            )
            total_samples += sum(
                len(port.normalized_signal) for port in native_ports)
            if total_samples > MAX_NATIVE_SAMPLES_PER_SETTLEMENT:
                raise ValueError("native sensory inputs exceed the total settlement sample boundary")
            prepared_by_sense[sense] = prepared
            for port in prepared:
                payloads.extend(port.input_payloads)

    input_registry = ReceiptRegistry.from_payloads(
        profile_payload=PROFILE_PAYLOAD,
        receipt_payloads=tuple(
            payload for payload in _unique_payloads(payloads)
            if payload != PROFILE_PAYLOAD
        ),
    )
    substreams_by_sense: dict[
        PhysicalSense, tuple[SensorySubstreamFullField, ...]] = {}
    topology_by_sense: dict[PhysicalSense, NativeSenseTopology] = {}
    for sense, prepared_ports in prepared_by_sense.items():
        full_substreams = []
        for prepared in prepared_ports:
            trace_record = run_ratified_native_l0_l4_trace(
                stream=prepared.stream,
                adapter=prepared.adapter,
                receipt_registry=input_registry,
            )
            payloads.append(trace_record.payload)
            basin, basin_payloads = port_kernel_basin_from_trace_record(
                lane_id=sense.value,
                port_id=prepared.native.substream_id,
                trace_record=trace_record,
            )
            payloads.extend(basin_payloads)
            full_substreams.append(
                SensorySubstreamFullField(prepared.profile, basin))
        profiles = tuple(port.profile for port in prepared_ports)
        topology_payload = native_sense_topology_receipt_payload(
            topology_id=f"topology-{assembly_id}-{sense.value}",
            sense=sense,
            profiles=profiles,
        )
        payloads.append(topology_payload)
        topology = NativeSenseTopology(
            topology_id=f"topology-{assembly_id}-{sense.value}",
            sense=sense,
            profiles=profiles,
            authority_receipt_sha256=receipt_sha256(topology_payload),
        )
        topology_by_sense[sense] = topology
        substreams_by_sense[sense] = tuple(full_substreams)

    causal_payload = _canonical_bytes({
        "assembly_id": assembly_id,
        "schema": "guala.live.sensory_causal_window.v1",
        "source_time_end": str(source_time_end),
        "source_time_start": str(source_time_start),
    })
    payloads.append(causal_payload)
    causal_digest = receipt_sha256(causal_payload)
    boundaries = []
    for sense in SENSE_ORDER:
        state = states[sense]
        topology = topology_by_sense.get(sense)
        substreams = substreams_by_sense.get(sense, ())
        evidence_payload = _canonical_bytes({
            "assembly_id": assembly_id,
            "schema": "guala.live.sensory_state_evidence.v1",
            "sense": sense.value,
            "state": state.value,
            "topology_receipt_sha256": (
                topology.authority_receipt_sha256 if topology else None),
        })
        payloads.append(evidence_payload)
        boundary_payload = sensory_full_field_boundary_receipt_payload(
            boundary_id=f"boundary-{assembly_id}-{sense.value}",
            sense=sense,
            state=state,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            causal_window_receipt_sha256=causal_digest,
            state_evidence_receipt_sha256=receipt_sha256(evidence_payload),
            topology=topology,
            substreams=substreams,
        )
        payloads.append(boundary_payload)
        boundaries.append(SensoryFullFieldBoundary(
            boundary_id=f"boundary-{assembly_id}-{sense.value}",
            sense=sense,
            state=state,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            causal_window_receipt_sha256=causal_digest,
            state_evidence_receipt_sha256=receipt_sha256(evidence_payload),
            topology=topology,
            substreams=substreams,
            authority_receipt_sha256=receipt_sha256(boundary_payload),
        ))
    boundary_tuple = tuple(boundaries)
    assembly_payload = six_sense_full_field_boundary_receipt_payload(
        assembly_id=assembly_id,
        boundaries=boundary_tuple,
    )
    payloads.append(assembly_payload)
    assembly = SixSenseFullFieldBoundary(
        assembly_id=assembly_id,
        boundaries=boundary_tuple,
        authority_receipt_sha256=receipt_sha256(assembly_payload),
    )
    registry = ReceiptRegistry.from_payloads(
        profile_payload=PROFILE_PAYLOAD,
        receipt_payloads=tuple(
            payload for payload in _unique_payloads(payloads)
            if payload != PROFILE_PAYLOAD
        ),
    )
    assembly.verify(registry)
    return BuiltSixSenseFullField(assembly, registry)


__all__ = (
    "BuiltSixSenseFullField",
    "MAX_NATIVE_SAMPLES_PER_SETTLEMENT",
    "MAX_NATIVE_SAMPLES_PER_SUBSTREAM",
    "MAX_NATIVE_SOUND_SUBSTREAMS",
    "MAX_NATIVE_SUBSTREAMS_PER_SENSE",
    "NativeSensorySubstreamInput",
    "build_six_sense_full_field",
)
