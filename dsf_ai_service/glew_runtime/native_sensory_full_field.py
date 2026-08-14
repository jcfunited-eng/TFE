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
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from .closed_experience import (
    KernelNativeInputMap,
    KernelNativeInputSample,
    KernelNativeInputStream,
    RatifiedNativeL0L4Trace,
    SIGNED_UNIT_KERNEL_INPUT_MAP,
    kernel_native_input_receipt_payload,
    run_ratified_native_l0_l4_trace_typed,
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
from .structural_port_basin import port_kernel_basin_from_typed_trace


PROFILE_PAYLOAD = b"guala.live.native_sensory_l0_l4.profile.v1"
RELEVANCE_PAYLOAD = b"guala.live.native_sensory.exact_source_relevance.v1"
SOURCE_RELEVANCE_SCHEMA = "guala.live.native_sensory.source_relevance.v2"
UNIT_SOURCE_RELEVANCE_RULE = "exact-unit-source-relevance.v1"
PAIRED_SOURCE_RELEVANCE_RULE = (
    "exact-paired-squared-pressure-amplitude-relevance.v1"
)
ADAPTER_PROFILE_PAYLOAD = SIGNED_UNIT_KERNEL_INPUT_MAP.profile_payload
SOURCE_SAMPLE_COMMITMENT_SCHEMA = (
    "guala.exact_causal_experience.source_samples.v2"
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
# The fixed W1 retina has 3 rows, 9 columns, and 6 independent optical bands:
# 3 * 9 * 6 = 162 scalar structural ports.  This is a transport/resource
# boundary only; frozen L0--L4 is unchanged.
MAX_NATIVE_SIGHT_SUBSTREAMS = 162
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
    source_relevance: tuple[Fraction, ...] | None = None
    source_relevance_rule: str = UNIT_SOURCE_RELEVANCE_RULE
    source_relevance_origin_substream_id: str | None = None
    kernel_input_map: KernelNativeInputMap = (
        SIGNED_UNIT_KERNEL_INPUT_MAP
    )
    # Optional exact physical source authority when the sensor's native lattice
    # is not itself representable as binary64.  ``normalized_signal`` remains
    # a checked nearest-binary64 transport projection; this exact tuple feeds
    # the invertible dimensionless field already carried by GLJSRC02 into
    # unchanged L0-L4 and is recovered for receptor physics.  No second sample
    # or semantic value is introduced.
    exact_physical_signal: tuple[Fraction, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.sense, PhysicalSense):
            raise ValueError("native sensory input requires a typed sense")
        if not isinstance(self.kernel_input_map, KernelNativeInputMap):
            raise ValueError("native sensory kernel input map is not typed")
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
        if self.exact_physical_signal is not None and len(
            self.exact_physical_signal
        ) != len(self.normalized_signal):
            raise ValueError("exact physical source changed sample cardinality")
        if self.source_relevance is None:
            if (
                self.source_relevance_rule != UNIT_SOURCE_RELEVANCE_RULE
                or self.source_relevance_origin_substream_id is not None
            ):
                raise ValueError(
                    "unit source relevance changed its authority"
                )
        else:
            if (
                len(self.source_relevance) != len(self.normalized_signal)
                or self.source_relevance_rule
                != PAIRED_SOURCE_RELEVANCE_RULE
                or self.source_relevance_origin_substream_id is None
            ):
                raise ValueError(
                    "explicit source relevance authority is incomplete"
                )
            require_identifier(
                self.source_relevance_origin_substream_id,
                "native sensory relevance origin substream_id",
            )
            for index, relevance in enumerate(self.source_relevance):
                require_fraction(
                    relevance,
                    f"native sensory relevance {index}",
                )
                if not 0 <= relevance <= 1:
                    raise ValueError(
                        "native sensory relevance must remain in [0,1]"
                    )
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
            if self.exact_physical_signal is not None:
                physical = self.exact_physical_signal[index]
                require_fraction(
                    physical, f"native exact physical signal {index}"
                )
                if not -1 <= physical <= 1:
                    raise ValueError(
                        "native exact physical signal must remain in [-1,1]"
                    )
                if Fraction.from_float(float(physical)) != exact_signal:
                    raise ValueError(
                        "native binary64 signal is not the exact physical "
                        "source projection"
                    )


@dataclass(slots=True)
class _VerifiedFullFieldConstruction:
    boundary: SixSenseFullFieldBoundary
    receipt_registry: ReceiptRegistry
    source_sample_commitments: tuple[tuple[str, int, str], ...]
    source_native_inputs: tuple[
        tuple[str, NativeSensorySubstreamInput], ...
    ]
    source_l0_l4_supports: tuple[
        tuple[
            str,
            str,
            str,
            int,
            tuple[tuple[int, int], ...],
        ],
        ...,
    ]
    native_joint_source_episode: object
    native_full_field_bank: object
    verification_count: int = 0


@dataclass(frozen=True, slots=True)
class BuiltSixSenseFullField:
    boundary: SixSenseFullFieldBoundary
    receipt_registry: ReceiptRegistry
    source_sample_commitments: tuple[tuple[str, int, str], ...]
    _source_native_inputs: tuple[
        tuple[str, NativeSensorySubstreamInput], ...
    ]
    _source_l0_l4_supports: tuple[
        tuple[
            str,
            str,
            str,
            int,
            tuple[tuple[int, int], ...],
        ],
        ...,
    ]
    _native_joint_source_episode: object
    _native_full_field_bank: object
    _construction_authority: _VerifiedFullFieldConstruction | None

    @property
    def has_transaction_construction_authority(self) -> bool:
        return self._construction_authority is not None

    @property
    def native_full_field_bank(self) -> object:
        if self._construction_authority is None:
            raise ValueError(
                "six-sense full field lacks native transaction authority"
            )
        return self._native_full_field_bank

    @property
    def native_joint_source_episode(self) -> object:
        if self._construction_authority is None:
            raise ValueError(
                "six-sense full field lacks native transaction authority"
            )
        return self._native_joint_source_episode

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
        if authority is not None and authority.verification_count >= 2:
            return
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
            or authority.source_native_inputs
            is not self._source_native_inputs
            or authority.source_l0_l4_supports
            is not self._source_l0_l4_supports
            or authority.native_joint_source_episode
            is not self._native_joint_source_episode
            or authority.native_full_field_bank
            is not self._native_full_field_bank
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
        authority.verification_count += 1

    def source_sample_commitment(
        self,
        source_evidence_stream_receipt_sha256: str,
    ) -> tuple[int, str]:
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

    def source_l0_l4_support(
        self,
        *,
        trace_receipt_sha256: str,
        sense: str,
        substream_id: str,
        source_count: int,
    ) -> tuple[tuple[int, int], ...]:
        """Return exact L1-L3 intervals from the admitted live build."""

        matches = tuple(
            intervals
            for (
                digest,
                mounted_sense,
                mounted_substream,
                mounted_source_count,
                intervals,
            ) in self._source_l0_l4_supports
            if (
                digest == trace_receipt_sha256
                and mounted_sense == sense
                and mounted_substream == substream_id
                and mounted_source_count == source_count
            )
        )
        if len(matches) != 1:
            raise ValueError(
                "verified full field lacks one exact L0-L4 support"
            )
        return matches[0]

    def source_native_input(
        self,
        source_evidence_stream_receipt_sha256: str,
    ) -> NativeSensorySubstreamInput:
        """Return the exact parent-owned input of this live transaction."""

        matches = tuple(
            native
            for digest, native in self._source_native_inputs
            if digest == source_evidence_stream_receipt_sha256
        )
        if len(matches) != 1:
            raise ValueError(
                "verified full field lacks one exact native source"
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


def _resolved_source_relevance(
    native: NativeSensorySubstreamInput,
) -> tuple[Fraction, ...]:
    return (
        native.source_relevance
        if native.source_relevance is not None
        else (Fraction(1),) * len(native.normalized_signal)
    )


def _source_relevance_payload(
    native: NativeSensorySubstreamInput,
    relevances: tuple[Fraction, ...],
) -> bytes:
    return _canonical_bytes({
        "origin_substream_id": (
            native.source_relevance_origin_substream_id
            if native.source_relevance_origin_substream_id is not None
            else native.substream_id
        ),
        "relevance": [
            f"{value.numerator}/{value.denominator}"
            for value in relevances
        ],
        "rule": native.source_relevance_rule,
        "schema": SOURCE_RELEVANCE_SCHEMA,
        "sense": native.sense.value,
        "sensor_id": native.sensor_id,
        "substream_id": native.substream_id,
    })


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
                "relevance": (
                    f"{sample.relevance.numerator}/"
                    f"{sample.relevance.denominator}"
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
    relevances = _resolved_source_relevance(native)
    relevance_payload = _source_relevance_payload(
        native,
        relevances,
    )
    relevance_digest = receipt_sha256(relevance_payload)
    samples = tuple(
        EvidenceSample(
            source_index=index,
            timestamp=timestamp,
            signal=_fraction_from_binary64(signal, f"signal {index}"),
            relevance=relevance,
            phase_turns=phase,
        )
        for index, (timestamp, signal, phase, relevance) in enumerate(zip(
            native.source_times,
            native.normalized_signal,
            native.phase_turns,
            relevances,
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
            dimensionless_field=native.kernel_input_map.forward(
                sample.signal
            ),
            l0_relevance=sample.relevance,
        )
        for sample in samples
    )
    adapter_payload = kernel_native_input_receipt_payload(
        adapter_id="guala-live-native-sensory",
        adapter_profile_receipt_sha256=receipt_sha256(
            native.kernel_input_map.profile_payload
        ),
        lane_id=native.sense.value,
        port_id=native.substream_id,
        source_stream_receipt_sha256=source_digest,
        samples=adapter_samples,
        kernel_input_map=native.kernel_input_map,
    )
    adapter = KernelNativeInputStream(
        adapter_id="guala-live-native-sensory",
        adapter_profile_receipt_sha256=receipt_sha256(
            native.kernel_input_map.profile_payload
        ),
        lane_id=native.sense.value,
        port_id=native.substream_id,
        source_stream_receipt_sha256=source_digest,
        samples=adapter_samples,
        authority_receipt_sha256=receipt_sha256(adapter_payload),
        kernel_input_map=native.kernel_input_map,
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
            relevance_payload,
            native.kernel_input_map.profile_payload,
            source_payload,
            adapter_payload,
            profile_payload,
        ),
        source_sample_commitment_sha256=(
            _source_sample_commitment(samples)
        ),
    )


def _source_l0_l4_intervals_from_trace(
    trace: ReceiptRecord | RatifiedNativeL0L4Trace,
    *,
    source_count: int,
    tuple_count: int,
) -> tuple[tuple[int, int], ...]:
    """Derive the exact common L1-L3 source support from one trace."""

    raw_trace = (
        None
        if isinstance(trace, RatifiedNativeL0L4Trace)
        else json.loads(trace.payload)
    )
    layer_intervals = []
    typed_layers = (
        (trace.l1, trace.l2, trace.l3)
        if isinstance(trace, RatifiedNativeL0L4Trace)
        else None
    )
    for layer_index, layer_name in enumerate((
        "L1_GateL1State",
        "L2_GateInterpretation",
        "L3_ResonanceResult",
    )):
        if typed_layers is not None:
            rows = typed_layers[layer_index]
            intervals = tuple(
                (value.gate.start_idx, value.gate.end_idx)
                for value in rows
            )
        else:
            rows = raw_trace.get(layer_name)
            if not isinstance(rows, list):
                raise RuntimeError(
                    "exact field construction lost complete gate support"
                )
            intervals = tuple(
                (row.get("start_idx"), row.get("end_idx"))
                for row in rows
                if isinstance(row, dict)
            )
        if len(rows) != tuple_count:
            raise RuntimeError(
                "exact field construction lost complete gate support"
            )
        if (
            len(intervals) != len(rows)
            or any(
                isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(end, bool)
                or not isinstance(end, int)
                or not 0 <= start <= end < source_count
                for start, end in intervals
            )
        ):
            raise RuntimeError(
                "exact field gate support left source grid"
            )
        layer_intervals.append(intervals)
    if (
        len(set(layer_intervals)) != 1
        or any(
            start != prior_end + 1
            for prior_end, (start, _end) in zip(
                (-1, *(
                    end for _start, end in layer_intervals[0][:-1]
                )),
                layer_intervals[0],
                strict=True,
            )
        )
        or layer_intervals[0][-1][1] != source_count - 1
        or (
            len(trace.l4) != tuple_count
            if isinstance(trace, RatifiedNativeL0L4Trace)
            else (
                not isinstance(raw_trace.get("L4_DSF"), list)
                or len(raw_trace["L4_DSF"]) != tuple_count
            )
        )
    ):
        raise RuntimeError(
            "exact field gate supports diverged"
        )
    return layer_intervals[0]


def declare_joint_source_occurrences(
    *,
    observed_substreams: Mapping[
        PhysicalSense, tuple[NativeSensorySubstreamInput, ...]],
    declared_units: tuple[tuple[tuple[PhysicalSense, int], ...], ...],
    joint_relevance_profile_payload: bytes | None = None,
) -> tuple:
    """Author explicit GLJSRC02 occurrences from site-declared physical units.

    Each declared unit names, as ``(sense, topology_index)`` pairs, the
    receptor ports that the call site declares to settle jointly as one
    source occurrence (for example the spectral bands of one retinal cell,
    or both cochlear fields of one binaural acoustic event).  Nothing is
    inferred here: the unit declaration is the caller's own physical law,
    and a declared unit whose referenced receptor clocks disagree is
    rejected rather than repaired.  Joint relevance is declared exactly
    ``r(t) = 1`` under the canonical UF v1.4 piecewise-linear profile;
    port-local relevance is never promoted into joint relevance.  The
    GLJSRC02 encoder re-verifies that the declared units partition every
    observed receptor exactly once.
    """

    from .native_joint_source_episode import (
        NativeJointSourceOccurrenceInput,
        UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR,
    )

    relevance_payload = (
        joint_relevance_profile_payload
        if joint_relevance_profile_payload is not None
        else UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR
    )
    sense_offsets: dict[PhysicalSense, int] = {}
    ports_by_key: dict[
        tuple[PhysicalSense, int], NativeSensorySubstreamInput
    ] = {}
    running = 0
    for sense in SENSE_ORDER:
        ports = observed_substreams.get(sense, ())
        sense_offsets[sense] = running
        for port in ports:
            ports_by_key[(sense, port.topology_index)] = port
        running += len(ports)
    occurrences = []
    for unit in declared_units:
        if not unit:
            raise ValueError("declared joint-source unit is empty")
        global_indices = []
        for key in unit:
            sense, topology_index = key
            if key not in ports_by_key:
                raise ValueError(
                    "declared joint-source unit references an "
                    "unobserved receptor"
                )
            global_indices.append(sense_offsets[sense] + topology_index)
        port_indices = tuple(sorted(global_indices))
        if len(set(port_indices)) != len(port_indices):
            raise ValueError("declared joint-source unit repeats a receptor")
        source_times = ports_by_key[unit[0]].source_times
        if any(
            ports_by_key[key].source_times != source_times for key in unit
        ):
            raise ValueError(
                "declared joint-source unit clocks diverge across its "
                "receptors"
            )
        occurrences.append(
            NativeJointSourceOccurrenceInput(
                port_indices=port_indices,
                source_times=source_times,
                joint_intersample_profile_payload=(
                    UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR
                ),
                groups=(tuple(range(len(port_indices))),),
                joint_relevance_profile_payload=relevance_payload,
                joint_relevance=(Fraction(1),) * len(source_times),
            )
        )
    return tuple(
        sorted(occurrences, key=lambda value: value.port_indices)
    )


def build_six_sense_full_field(
    *,
    assembly_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    observed_substreams: Mapping[
        PhysicalSense, tuple[NativeSensorySubstreamInput, ...]],
    states: Mapping[PhysicalSense, SenseBoundaryState],
    occurrences: tuple["NativeJointSourceOccurrenceInput", ...],
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
    source_native_inputs = []
    source_l0_l4_supports = []
    from .native_joint_source_episode import (
        settle_native_joint_source_episode,
    )
    native_joint_source_episode = settle_native_joint_source_episode(
        assembly_id=assembly_id,
        observed_substreams=observed_substreams,
        states=states,
        occurrences=occurrences,
    )
    from .native_exact_field_batch import build_native_exact_field_batch
    native_batch = build_native_exact_field_batch(
        assembly_id=assembly_id,
        observed_substreams=observed_substreams,
        states=states,
    )
    parallel_results = native_batch.results
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
                trace = run_ratified_native_l0_l4_trace_typed(
                    stream=prepared.stream,
                    adapter=prepared.adapter,
                    receipt_registry=input_registry,
                )
                trace_record = ReceiptRecord(
                    digest=receipt_sha256(trace.raw_payload),
                    payload=trace.raw_payload,
                )
                basin, basin_payloads = port_kernel_basin_from_typed_trace(
                    lane_id=sense.value,
                    port_id=prepared.native.substream_id,
                    trace=trace,
                )
                source_intervals = _source_l0_l4_intervals_from_trace(
                    trace,
                    source_count=len(
                        prepared.native.normalized_signal
                    ),
                    tuple_count=len(
                        basin.exact_dsf_field_tuples
                    ),
                )
                port_results.append((
                    prepared.native,
                    prepared.profile,
                    prepared.input_payloads,
                    trace_record.digest,
                    trace_record.payload,
                    basin,
                    basin_payloads,
                    prepared.source_sample_commitment_sha256,
                    source_intervals,
                ))
        else:
            port_results = []
            for native in native_ports:
                result = parallel_results[result_index]
                result.verify_construction(
                    global_index=result_index,
                    native=native,
                    assembly_id=assembly_id,
                )
                result_index += 1
                port_results.append((
                    native,
                    result.profile,
                    result.input_payloads,
                    result.trace_digest,
                    result.trace_payload,
                    result.basin,
                    result.basin_payloads,
                    result.source_sample_commitment_sha256,
                    result.source_l0_l4_intervals,
                ))
            # Preserve the canonical registry order shared with serial
            # construction: every source/input authority precedes every
            # trace and basin authority. The unpack loop below intentionally
            # repeats these bytes before per-port trace payloads; registry
            # uniqueness removes the duplicate while retaining this order.
            for port_result in port_results:
                payloads.extend(port_result[2])
        for (
            native,
            profile,
            input_payloads,
            trace_digest,
            trace_payload,
            basin,
            basin_payloads,
            source_commitment,
            source_intervals,
        ) in port_results:
            payloads.extend(input_payloads)
            payloads.append(trace_payload)
            payloads.extend(basin_payloads)
            if (
                {
                    value.source_l0_l4_trace_receipt_sha256
                    for value in basin.exact_dsf_field_tuples
                }
                != {trace_digest}
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
            source_native_inputs.append((
                profile.physical_derivation_receipt_sha256,
                native,
            ))
            source_l0_l4_supports.append((
                trace_digest,
                sense.value,
                profile.substream_id,
                len(native.normalized_signal),
                source_intervals,
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
    source_native_input_tuple = tuple(source_native_inputs)
    source_l0_l4_support_tuple = tuple(source_l0_l4_supports)
    construction_authority = (
        _VerifiedFullFieldConstruction(
            assembly,
            registry,
            source_sample_commitment_tuple,
            source_native_input_tuple,
            source_l0_l4_support_tuple,
            native_joint_source_episode,
            native_batch.bank,
        )
        if _transaction_authority is _TRANSACTION_BUILD_REQUEST
        else None
    )
    built = BuiltSixSenseFullField(
        assembly,
        registry,
        source_sample_commitment_tuple,
        (
            source_native_input_tuple
            if construction_authority is not None
            else ()
        ),
        (
            source_l0_l4_support_tuple
            if construction_authority is not None
            else ()
        ),
        native_joint_source_episode,
        native_batch.bank,
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
    occurrences: tuple["NativeJointSourceOccurrenceInput", ...],
) -> BuiltSixSenseFullField:
    """Build a capability that must remain inside one engine transaction."""
    return build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        observed_substreams=observed_substreams,
        states=states,
        occurrences=occurrences,
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
    "PAIRED_SOURCE_RELEVANCE_RULE",
    "SOURCE_RELEVANCE_SCHEMA",
    "UNIT_SOURCE_RELEVANCE_RULE",
    "build_six_sense_full_field",
    "build_transaction_owned_six_sense_full_field",
    "declare_joint_source_occurrences",
)
