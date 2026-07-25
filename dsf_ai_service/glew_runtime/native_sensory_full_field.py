"""Ratified native-sensory adapter into the exact six-sense L0--L4 boundary.

The adapter preserves each provider-declared substream independently, applies
the canonical invertible ``F = 1 + s/2`` map, and runs the frozen ``uf_core``
layers without changing them.  It returns a fully mounted and verified
``SixSenseFullFieldBoundary``.  No L5 meaning, chi identity, word label, or
compatibility vector is introduced here.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
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
SOURCE_SAMPLE_COMMITMENT_SCHEMA = (
    "guala.exact_causal_experience.source_samples.v1"
)

# Deterministic resource-safety boundary. These are transport/runtime limits,
# not sensory physics and not cognition. They cap the largest single causal
# settlement that this live adapter will admit so one request cannot recreate
# the historical unbounded-memory failure.
MAX_NATIVE_SUBSTREAMS_PER_SENSE = 16
# Two physical ears, each retaining the canonical sixteen cochlear bands as
# independent pressure and phase-advance components: 2 * 16 * 2 = 64.
# This is a transport/resource boundary only; frozen L0--L4 is unchanged.
MAX_NATIVE_SOUND_SUBSTREAMS = 64
# W1 admits at most 3 non-self bodies plus 16 objects, each preserving four
# independent physical axes: (3 + 16) * 4 = 76 scalar structural ports.
MAX_NATIVE_SIGHT_SUBSTREAMS = 76
MAX_NATIVE_SAMPLES_PER_SUBSTREAM = 2048
MAX_NATIVE_SAMPLES_PER_SETTLEMENT = 32768

_TRANSACTION_BUILD_REQUEST = object()


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
class _VerifiedFullFieldConstruction:
    boundary: SixSenseFullFieldBoundary
    receipt_registry: ReceiptRegistry
    source_sample_commitments: tuple[tuple[str, int, str], ...]


@dataclass(frozen=True, slots=True)
class BuiltSixSenseFullField:
    boundary: SixSenseFullFieldBoundary
    receipt_registry: ReceiptRegistry
    source_sample_commitments: tuple[tuple[str, int, str], ...]
    _construction_authority: _VerifiedFullFieldConstruction | None

    @property
    def has_transaction_construction_authority(self) -> bool:
        try:
            self.verify_construction()
        except ValueError:
            return False
        return True

    def verify_construction(
        self,
        *,
        boundary: SixSenseFullFieldBoundary | None = None,
        receipt_registry: ReceiptRegistry | None = None,
    ) -> None:
        """Authenticate one immutable, request-local completed build.

        This capability cannot be serialized or recreated from receipt text.
        It only avoids repeating verification while the exact frozen objects
        that were fully verified by ``build_six_sense_full_field`` remain
        inside the same transaction.
        """
        authority = self._construction_authority
        if not isinstance(
            authority,
            _VerifiedFullFieldConstruction,
        ):
            raise ValueError(
                "six-sense full field lacks construction authority"
            )
        if (
            authority.boundary is not self.boundary
            or authority.receipt_registry is not self.receipt_registry
            or authority.source_sample_commitments
            is not self.source_sample_commitments
        ):
            raise ValueError(
                "six-sense full field construction authority was copied"
            )
        if (
            boundary is not None
            and boundary is not self.boundary
        ) or (
            receipt_registry is not None
            and receipt_registry is not self.receipt_registry
        ):
            raise ValueError(
                "six-sense full field left its verified transaction"
            )

    def source_sample_commitment(
        self,
        source_evidence_stream_receipt_sha256: str,
    ) -> tuple[int, str]:
        self.verify_construction()
        matches = tuple(
            (sample_count, commitment)
            for digest, sample_count, commitment
            in self.source_sample_commitments
            if digest == source_evidence_stream_receipt_sha256
        )
        if len(matches) != 1:
            raise ValueError(
                "verified full field lacks one exact source commitment"
            )
        return matches[0]


@dataclass(frozen=True, slots=True)
class _PreparedPort:
    native: NativeSensorySubstreamInput
    stream: EvidenceStream
    adapter: KernelNativeInputStream
    profile: NativeSubstreamProfile
    input_payloads: tuple[bytes, ...]
    source_sample_commitment_sha256: str


def _source_sample_commitment(
    samples: tuple[EvidenceSample, ...],
) -> str:
    payload = {
        "samples": [
            {
                "phase_turns": (
                    f"{sample.phase_turns.numerator}/"
                    f"{sample.phase_turns.denominator}"
                ),
                "signal": (
                    f"{sample.signal.numerator}/{sample.signal.denominator}"
                ),
                "source_index": sample.source_index,
                "timestamp": (
                    f"{sample.timestamp.numerator}/"
                    f"{sample.timestamp.denominator}"
                ),
            }
            for sample in samples
        ],
        "schema": SOURCE_SAMPLE_COMMITMENT_SCHEMA,
    }
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


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
        source_sample_commitment_sha256=(
            _source_sample_commitment(samples)
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
    _transaction_authority: object | None = None,
) -> BuiltSixSenseFullField:
    """Build and verify one exact, complete six-sense pre-L5 boundary."""
    if (
        _transaction_authority is not None
        and _transaction_authority
        is not _TRANSACTION_BUILD_REQUEST
    ):
        raise ValueError("native full-field transaction authority is invalid")
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

    payloads = [PROFILE_PAYLOAD]
    total_samples = 0
    ordered_native_ports: list[
        tuple[PhysicalSense, NativeSensorySubstreamInput]
    ] = []
    for sense in SENSE_ORDER:
        native_ports = observed_substreams.get(sense, ())
        if native_ports:
            substream_capacity = (
                MAX_NATIVE_SOUND_SUBSTREAMS
                if sense is PhysicalSense.SOUND
                else MAX_NATIVE_SIGHT_SUBSTREAMS
                if sense is PhysicalSense.SIGHT
                else MAX_NATIVE_SUBSTREAMS_PER_SENSE
            )
            if len(native_ports) > substream_capacity:
                raise ValueError("native sensory topology exceeds the settlement port boundary")
            if tuple(port.sense for port in native_ports) != (sense,) * len(native_ports):
                raise ValueError("native topology crosses sense boundaries")
            if tuple(port.topology_index for port in native_ports) != tuple(
                    range(len(native_ports))):
                raise ValueError("native sensory topology is incomplete or reordered")
            total_samples += sum(
                len(port.normalized_signal) for port in native_ports)
            if total_samples > MAX_NATIVE_SAMPLES_PER_SETTLEMENT:
                raise ValueError("native sensory inputs exceed the total settlement sample boundary")
            ordered_native_ports.extend(
                (sense, port) for port in native_ports
            )

    substreams_by_sense: dict[
        PhysicalSense, tuple[SensorySubstreamFullField, ...]] = {}
    topology_by_sense: dict[PhysicalSense, NativeSenseTopology] = {}
    source_sample_commitments = []
    from .exact_field_executor import exact_field_executor
    executor = exact_field_executor()
    if (
        executor is None
        and os.environ.get(
            "GUALA_EXACT_FIELD_EXECUTOR_REQUIRED",
            "0",
        ) == "1"
    ):
        raise RuntimeError(
            "required exact field executor owner is absent"
        )
    parallel_results = (
        executor.build_ports(
            (native, assembly_id)
            for _sense, native in ordered_native_ports
        )
        if executor is not None and ordered_native_ports
        else ()
        if executor is not None
        else None
    )
    result_index = 0
    for sense in SENSE_ORDER:
        native_ports = observed_substreams.get(sense, ())
        if not native_ports:
            continue
        full_substreams = []
        profiles = []
        if parallel_results is None:
            prepared_ports = tuple(
                _prepare_port(port, assembly_id=assembly_id)
                for port in native_ports
            )
            for prepared in prepared_ports:
                payloads.extend(prepared.input_payloads)
            input_registry = ReceiptRegistry.from_payloads(
                profile_payload=PROFILE_PAYLOAD,
                receipt_payloads=tuple(
                    payload
                    for payload in _unique_payloads(payloads)
                    if payload != PROFILE_PAYLOAD
                ),
            )
            port_results = []
            for prepared in prepared_ports:
                trace_record = run_ratified_native_l0_l4_trace(
                    stream=prepared.stream,
                    adapter=prepared.adapter,
                    receipt_registry=input_registry,
                )
                basin, basin_payloads = port_kernel_basin_from_trace_record(
                    lane_id=sense.value,
                    port_id=prepared.native.substream_id,
                    trace_record=trace_record,
                )
                port_results.append((
                    prepared.native,
                    prepared.profile,
                    prepared.input_payloads,
                    trace_record,
                    basin,
                    basin_payloads,
                    prepared.source_sample_commitment_sha256,
                ))
        else:
            port_results = []
            for native in native_ports:
                result = parallel_results[result_index]
                result_index += 1
                expected = _prepare_port(
                    native,
                    assembly_id=assembly_id,
                )
                if (
                    result.profile != expected.profile
                    or result.input_payloads != expected.input_payloads
                    or result.source_sample_commitment_sha256
                    != expected.source_sample_commitment_sha256
                ):
                    raise RuntimeError(
                        "exact field worker changed native input authority"
                    )
                port_results.append((
                    native,
                    expected.profile,
                    expected.input_payloads,
                    result.trace,
                    result.basin,
                    result.basin_payloads,
                    expected.source_sample_commitment_sha256,
                ))
            for port_result in port_results:
                payloads.extend(port_result[2])
        for (
            native,
            profile,
            input_payloads,
            trace_record,
            basin,
            basin_payloads,
            source_commitment,
        ) in port_results:
            payloads.extend(input_payloads)
            payloads.append(trace_record.payload)
            payloads.extend(basin_payloads)
            if (
                {
                    value.source_l0_l4_trace_receipt_sha256
                    for value in basin.exact_dsf_field_tuples
                }
                != {trace_record.digest}
            ):
                raise RuntimeError(
                    "exact field worker changed its trace authority"
                )
            full_substreams.append(
                SensorySubstreamFullField(profile, basin)
            )
            profiles.append(profile)
            source_sample_commitments.append((
                profile.physical_derivation_receipt_sha256,
                len(native.normalized_signal),
                source_commitment,
            ))
        profiles = tuple(profiles)
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

    if (
        parallel_results is not None
        and result_index != len(parallel_results)
    ):
        raise RuntimeError(
            "exact field worker changed complete topology cardinality"
        )

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
    source_sample_commitment_tuple = tuple(
        source_sample_commitments
    )
    construction_authority = (
        _VerifiedFullFieldConstruction(
            assembly,
            registry,
            source_sample_commitment_tuple,
        )
        if _transaction_authority is _TRANSACTION_BUILD_REQUEST
        else None
    )
    built = BuiltSixSenseFullField(
        assembly,
        registry,
        source_sample_commitment_tuple,
        construction_authority,
    )
    if _transaction_authority is not None:
        built.verify_construction(
            boundary=assembly,
            receipt_registry=registry,
        )
    return built


def build_transaction_owned_six_sense_full_field(
    *,
    assembly_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    observed_substreams: Mapping[
        PhysicalSense, tuple[NativeSensorySubstreamInput, ...]],
    states: Mapping[PhysicalSense, SenseBoundaryState],
) -> BuiltSixSenseFullField:
    """Build a capability that must remain inside one engine transaction."""
    return build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        observed_substreams=observed_substreams,
        states=states,
        _transaction_authority=(
            _TRANSACTION_BUILD_REQUEST
        ),
    )


__all__ = (
    "BuiltSixSenseFullField",
    "MAX_NATIVE_SAMPLES_PER_SETTLEMENT",
    "MAX_NATIVE_SAMPLES_PER_SUBSTREAM",
    "MAX_NATIVE_SOUND_SUBSTREAMS",
    "MAX_NATIVE_SIGHT_SUBSTREAMS",
    "MAX_NATIVE_SUBSTREAMS_PER_SENSE",
    "NativeSensorySubstreamInput",
    "build_six_sense_full_field",
    "build_transaction_owned_six_sense_full_field",
)
