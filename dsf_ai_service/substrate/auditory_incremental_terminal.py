"""Incremental native-hop proposals for tutor-witnessed auditory terminals.

The owner in this module is deliberately outside L0--L4.  It carries a
bounded monotone dynamic-programming state over continuous 10 ms auditory L5
pressure and phase frames.  The state is proposal evidence only: it has no
candidate-level L4 field and therefore cannot recognize or release anything.

A proposed terminal must be rebuilt from its exact retained PCM through the
unchanged sixteen-port sensory provider and unchanged L0--L4 boundary.  The
existing ``AuditoryReciprocityOwner`` must then return one UNIQUE tutor label
from pressure, phase, topology, and every explicit L4 tuple.  UNKNOWN,
AMBIGUOUS, discontinuity, and resource exhaustion release nothing.

Terminal extent comes from the tutor-witnessed path length.  The current
reciprocity relation duration-normalizes complete candidates and does not
learn a separate variable-duration end transition.  Consequently this owner
can discover witnessed terminal extents at any native-hop offset, but it does
not claim to infer unwitnessed variable-duration endings.

Transport ids and receipts prove continuity only.  They never represent a
speaker, source, word, identity, meaning, or chi.  No text, ML model, acoustic
score, fitted threshold, or fixed vocabulary enters this module.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import struct
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AuditoryL5Experience,
    AuditoryL5Owner,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_STREAM_CAPACITY,
    PCM_STREAM_IDLE_SECONDS,
    AuditoryPCMContinuityReceipt,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
    MAX_INTERVAL_COMPONENTS_PER_CELL,
    MAX_PATH_BRANCHES_PER_CLASS,
    MAX_REACHABILITY_CELLS_PER_RECOGNITION,
    PCM_PRESSURE_QUANTUM,
    AuditoryRecognitionState,
    AuditoryReciprocityKind,
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    MAX_CAPTURE_SECONDS,
    OBSERVATION_HOP_SAMPLES,
    AuditoryFullFieldCapture,
    AuditoryGammatoneContinuationReceipt,
)


AUDITORY_INCREMENTAL_EVENT_SCHEMA = "guala.auditory.incremental_terminal.v1"
AUDITORY_INCREMENTAL_ADVANCE_SCHEMA = "guala.auditory.incremental_advance.v1"
MAX_EVENT_SAMPLES = PCM_SAMPLE_RATE_HZ * MAX_CAPTURE_SECONDS
MAX_EVENT_HOPS = MAX_EVENT_SAMPLES // OBSERVATION_HOP_SAMPLES
# This is a resource boundary, never a semantic threshold.  Exceeding the
# existing full-recognition work budget yields a typed indeterminate result.
MAX_ACTIVE_TRACKERS = max(
    1, MAX_REACHABILITY_CELLS_PER_RECOGNITION // MAX_EVENT_HOPS
)


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


def _canonical_digest(value: object, name: str) -> str:
    return sha256_digest(value, name)


class AuditoryIncrementalStatus(str, Enum):
    UNKNOWN = "unknown"
    CONTINUING = "continuing"
    RELEASED_UNIQUE = "released_unique"
    AMBIGUOUS = "ambiguous"
    INDETERMINATE_RESOURCE = "indeterminate_resource"
    DISCONTINUITY = "discontinuity"


def _event_payload(
    *,
    event_id: str,
    stream_id: str,
    source_sample_start: int,
    source_sample_end: int,
    tutor_label: str,
    structural_fingerprint: str,
    l5_authority_receipt_sha256: str,
    transport_receipt_sha256s: tuple[str, ...],
    cochlear_receipt_sha256s: tuple[str, ...],
    joint_settlement_receipt_sha256s: tuple[str, ...],
) -> dict[str, object]:
    return {
        "cochlear_receipt_sha256s": list(cochlear_receipt_sha256s),
        "event_id": event_id,
        "joint_settlement_receipt_sha256s": list(
            joint_settlement_receipt_sha256s
        ),
        "l5_authority_receipt_sha256": l5_authority_receipt_sha256,
        "recognition_state": AuditoryRecognitionState.UNIQUE.value,
        "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
        "schema": AUDITORY_INCREMENTAL_EVENT_SCHEMA,
        "source_sample_end": source_sample_end,
        "source_sample_start": source_sample_start,
        "stream_id": stream_id,
        "structural_fingerprint": structural_fingerprint,
        "transport_receipt_sha256s": list(transport_receipt_sha256s),
        "tutor_label": tutor_label,
    }


@dataclass(frozen=True, slots=True)
class AuditoryIncrementalTerminalEvent:
    event_id: str
    stream_id: str
    source_sample_start: int
    source_sample_end: int
    tutor_label: str
    structural_fingerprint: str
    l5_authority_receipt_sha256: str
    transport_receipt_sha256s: tuple[str, ...]
    cochlear_receipt_sha256s: tuple[str, ...]
    joint_settlement_receipt_sha256s: tuple[str, ...]
    authority_receipt_sha256: str

    @property
    def sample_count(self) -> int:
        return self.source_sample_end - self.source_sample_start

    def verify(self) -> None:
        if not isinstance(self.stream_id, str) or not self.stream_id:
            raise ValueError("incremental auditory event has no stream epoch")
        if (
            isinstance(self.source_sample_start, bool)
            or not isinstance(self.source_sample_start, int)
            or self.source_sample_start < 0
            or self.source_sample_start % OBSERVATION_HOP_SAMPLES
            or isinstance(self.source_sample_end, bool)
            or not isinstance(self.source_sample_end, int)
            or self.source_sample_end <= self.source_sample_start
            or self.sample_count > MAX_EVENT_SAMPLES
            or self.sample_count % OBSERVATION_HOP_SAMPLES
        ):
            raise ValueError("incremental auditory event interval is invalid")
        if not isinstance(self.tutor_label, str) or not self.tutor_label:
            raise ValueError("incremental auditory event has no tutor label")
        fingerprint = _canonical_digest(
            self.structural_fingerprint,
            "incremental auditory structural fingerprint",
        )
        l5_receipt = _canonical_digest(
            self.l5_authority_receipt_sha256,
            "incremental auditory L5 receipt",
        )
        receipt_groups = (
            self.transport_receipt_sha256s,
            self.cochlear_receipt_sha256s,
            self.joint_settlement_receipt_sha256s,
        )
        if any(not group for group in receipt_groups):
            raise ValueError("incremental auditory event lost causal evidence")
        transport, cochlear, joint = (
            tuple(
                _canonical_digest(value, "incremental auditory evidence receipt")
                for value in group
            )
            for group in receipt_groups
        )
        expected_id = _digest({
            "source_sample_end": self.source_sample_end,
            "source_sample_start": self.source_sample_start,
            "stream_id": self.stream_id,
            "structural_fingerprint": fingerprint,
        })
        if self.event_id != expected_id:
            raise ValueError("incremental auditory event identity changed")
        payload = _event_payload(
            event_id=expected_id,
            stream_id=self.stream_id,
            source_sample_start=self.source_sample_start,
            source_sample_end=self.source_sample_end,
            tutor_label=self.tutor_label,
            structural_fingerprint=fingerprint,
            l5_authority_receipt_sha256=l5_receipt,
            transport_receipt_sha256s=transport,
            cochlear_receipt_sha256s=cochlear,
            joint_settlement_receipt_sha256s=joint,
        )
        if _digest(payload) != _canonical_digest(
            self.authority_receipt_sha256,
            "incremental auditory event authority receipt",
        ):
            raise ValueError("incremental auditory event receipt was altered")


def _advance_payload(
    *,
    status: AuditoryIncrementalStatus,
    reply_candidate: AuditoryIncrementalTerminalEvent | None,
    processed_hops: int,
    active_tracker_count: int,
) -> dict[str, object]:
    return {
        "active_tracker_count": active_tracker_count,
        "processed_hops": processed_hops,
        "reply_candidate_receipt_sha256": (
            reply_candidate.authority_receipt_sha256
            if reply_candidate is not None else None
        ),
        "schema": AUDITORY_INCREMENTAL_ADVANCE_SCHEMA,
        "status": status.value,
    }


@dataclass(frozen=True, slots=True)
class AuditoryIncrementalAdvance:
    status: AuditoryIncrementalStatus
    reply_candidate: AuditoryIncrementalTerminalEvent | None
    processed_hops: int
    active_tracker_count: int
    authority_receipt_sha256: str

    def verify(self) -> None:
        if not isinstance(self.status, AuditoryIncrementalStatus):
            raise ValueError("incremental auditory status is invalid")
        for value, name in (
            (self.processed_hops, "processed hops"),
            (self.active_tracker_count, "active tracker count"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"incremental auditory {name} is invalid")
        if self.active_tracker_count > MAX_ACTIVE_TRACKERS:
            raise ValueError("incremental auditory tracker boundary was exceeded")
        if self.status is AuditoryIncrementalStatus.RELEASED_UNIQUE:
            if self.reply_candidate is None:
                raise ValueError("unique auditory release has no candidate")
            self.reply_candidate.verify()
        elif self.reply_candidate is not None:
            raise ValueError("non-unique auditory state exposed a reply candidate")
        payload = _advance_payload(
            status=self.status,
            reply_candidate=self.reply_candidate,
            processed_hops=self.processed_hops,
            active_tracker_count=self.active_tracker_count,
        )
        if _digest(payload) != _canonical_digest(
            self.authority_receipt_sha256,
            "incremental auditory advance receipt",
        ):
            raise ValueError("incremental auditory advance receipt was altered")


@dataclass(frozen=True, slots=True)
class _Branch:
    structural_fingerprint: str
    sample_count: int
    topology: tuple[tuple[object, ...], ...]
    # port -> frame -> (pressure, absolute phase turns)
    values: tuple[tuple[tuple[float, float], ...], ...]


@dataclass(frozen=True, slots=True)
class _Cell:
    tutor_label: str
    left: _Branch
    right: _Branch
    reference_count: int
    terminal_floor: int
    recurrence_incoming: tuple[tuple[int, ...], ...]


Interval = tuple[float, float]
IntervalSet = tuple[Interval, ...]


@dataclass(slots=True)
class _Tracker:
    cell_index: int
    start_sample: int
    frames_seen: int
    first_pressure: tuple[float, ...]
    first_phase: tuple[float, ...]
    previous_pressure: tuple[float, ...]
    previous_phase: tuple[float, ...]
    row: tuple[IntervalSet, ...] | None


@dataclass(frozen=True, slots=True)
class _Evidence:
    start: int
    end: int
    transport: str
    cochlear: str
    joint: str


@dataclass(frozen=True, slots=True)
class _Frame:
    completion_sample: int
    pressure: tuple[float, ...]
    phase: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class _PendingTerminal:
    start: int
    end: int
    tutor_label: str
    structural_fingerprint: str
    l5_authority_receipt_sha256: str
    transport_receipt_sha256s: tuple[str, ...]
    cochlear_receipt_sha256s: tuple[str, ...]
    joint_settlement_receipt_sha256s: tuple[str, ...]


def _branch_from_snapshot(value: object) -> _Branch:
    if not isinstance(value, dict):
        raise ValueError("incremental auditory witness is malformed")
    sample_count = value.get("sample_count")
    topology_raw = value.get("topology")
    packed_raw = value.get("packed_samples")
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count < 2
        or sample_count > MAX_EVENT_HOPS
        or not isinstance(topology_raw, list)
        or len(topology_raw) != COCHLEAR_CHANNEL_COUNT
        or not isinstance(packed_raw, list)
        or len(packed_raw) != COCHLEAR_CHANNEL_COUNT
    ):
        raise ValueError("incremental auditory witness exceeds its boundary")
    topology = []
    values = []
    for port_index, (raw_topology, encoded) in enumerate(
        zip(topology_raw, packed_raw, strict=True)
    ):
        if (
            not isinstance(raw_topology, dict)
            or raw_topology.get("topology_index") != port_index
            or raw_topology.get("substream_id")
            != AUDITORY_CHANNELS[port_index].name
            or not isinstance(encoded, str)
        ):
            raise ValueError("incremental auditory witness topology changed")
        coordinates = raw_topology.get("coordinates")
        if not isinstance(coordinates, list):
            raise ValueError("incremental auditory witness coordinates changed")
        topology.append((
            raw_topology.get("sensor_id"),
            raw_topology.get("substream_id"),
            raw_topology.get("topology_index"),
            tuple(tuple(item) for item in coordinates),
            raw_topology.get("physical_quantity"),
            raw_topology.get("physical_unit"),
        ))
        try:
            packed = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise ValueError(
                "incremental auditory witness samples cannot be decoded"
            ) from exc
        if len(packed) != sample_count * 16:
            raise ValueError("incremental auditory witness cardinality changed")
        unpacked = struct.unpack(f"<{sample_count * 2}d", packed)
        if any(not math.isfinite(item) for item in unpacked):
            raise ValueError("incremental auditory witness is not finite")
        values.append(tuple(
            (unpacked[index * 2], unpacked[index * 2 + 1])
            for index in range(sample_count)
        ))
    return _Branch(
        structural_fingerprint=_canonical_digest(
            value.get("structural_fingerprint"),
            "incremental auditory witness fingerprint",
        ),
        sample_count=sample_count,
        topology=tuple(topology),
        values=tuple(values),
    )


def _branch_sample(
    branch: _Branch,
    port: int,
    query_index: int,
    query_count: int,
) -> tuple[float, float]:
    """Return pressure and phase advance on the common reference grid."""

    if branch.sample_count == 1 or query_count == 1:
        pressure = branch.values[port][0][0]
        return pressure, 0.0
    position = query_index * (branch.sample_count - 1) / (query_count - 1)
    left_index = int(math.floor(position))
    right_index = min(left_index + 1, branch.sample_count - 1)
    weight = position - left_index
    left_pressure = branch.values[port][left_index][0]
    right_pressure = branch.values[port][right_index][0]

    def phase_advance(index: int) -> float:
        right = max(1, index)
        return (
            branch.values[port][right][1]
            - branch.values[port][right - 1][1]
        )

    left_phase = phase_advance(left_index)
    right_phase = phase_advance(right_index)
    return (
        left_pressure + weight * (right_pressure - left_pressure),
        left_phase + weight * (right_phase - left_phase),
    )


def _branch_phase_prior_pressure(
    branch: _Branch,
    port: int,
    query_index: int,
    query_count: int,
) -> float:
    position = (
        0.0
        if query_count == 1
        else query_index * (branch.sample_count - 1) / (query_count - 1)
    )
    prior_position = position - 1.0 if position >= 1.0 else position + 1.0
    left = int(math.floor(prior_position))
    right = min(left + 1, branch.sample_count - 1)
    weight = prior_position - left
    return (
        branch.values[port][left][0]
        + weight
        * (branch.values[port][right][0] - branch.values[port][left][0])
    )


def _phase_uncertainty(*pressures: float) -> float | None:
    quantum = float(PCM_PRESSURE_QUANTUM)
    if any(value <= quantum for value in pressures):
        return None
    return sum(
        math.asin(min(1.0, quantum / value)) / (2.0 * math.pi)
        for value in pressures
    )


def _intersect_lambda(
    interval: Interval,
    *,
    query: float,
    left: float,
    right: float,
    uncertainty: float,
) -> Interval | None:
    lower, upper = interval
    difference = right - left
    if difference == 0.0:
        return interval if abs(query - left) <= uncertainty else None
    first = (query - uncertainty - left) / difference
    second = (query + uncertainty - left) / difference
    result = (max(lower, min(first, second)), min(upper, max(first, second)))
    return result if result[0] <= result[1] else None


def _intersect_many(values: IntervalSet, local: Interval) -> IntervalSet | None:
    clipped = [
        (max(lower, local[0]), min(upper, local[1]))
        for lower, upper in values
        if max(lower, local[0]) <= min(upper, local[1])
    ]
    if not clipped:
        return ()
    clipped.sort()
    merged = [clipped[0]]
    for lower, upper in clipped[1:]:
        prior_lower, prior_upper = merged[-1]
        if lower <= prior_upper:
            merged[-1] = (prior_lower, max(prior_upper, upper))
        else:
            merged.append((lower, upper))
    if len(merged) > MAX_INTERVAL_COMPONENTS_PER_CELL:
        return None
    return tuple(merged)


def _local_interval(
    cell: _Cell,
    *,
    query_pressure: tuple[float, ...],
    query_phase_advance: tuple[float, ...],
    query_phase_prior_pressure: tuple[float, ...],
    reference_index: int,
) -> Interval | None:
    interval: Interval | None = (0.0, 1.0)
    pressure_uncertainty = 2.0 * float(PCM_PRESSURE_QUANTUM)
    for port in range(COCHLEAR_CHANNEL_COUNT):
        left_pressure, left_phase = _branch_sample(
            cell.left, port, reference_index, cell.reference_count
        )
        right_pressure, right_phase = _branch_sample(
            cell.right, port, reference_index, cell.reference_count
        )
        interval = _intersect_lambda(
            interval,
            query=query_pressure[port],
            left=left_pressure,
            right=right_pressure,
            uncertainty=pressure_uncertainty,
        )
        if interval is None:
            return None
        phase_uncertainty = _phase_uncertainty(
            query_pressure[port],
            query_phase_prior_pressure[port],
            left_pressure,
            _branch_phase_prior_pressure(
                cell.left, port, reference_index, cell.reference_count
            ),
            right_pressure,
            _branch_phase_prior_pressure(
                cell.right, port, reference_index, cell.reference_count
            ),
        )
        if phase_uncertainty is None:
            continue
        interval = _intersect_lambda(
            interval,
            query=query_phase_advance[port],
            left=left_phase,
            right=right_phase,
            uncertainty=phase_uncertainty,
        )
        if interval is None:
            return None
    return interval


def _cells_from_owner(owner: AuditoryReciprocityOwner) -> tuple[_Cell, ...]:
    snapshot = owner.snapshot()
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("schema") != AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA
        or not isinstance(snapshot.get("classes"), list)
        or snapshot.get("branch_capacity_per_class")
        != MAX_PATH_BRANCHES_PER_CLASS
    ):
        raise ValueError("incremental auditory learning snapshot is invalid")
    cells = []
    for learned in snapshot["classes"]:
        if not isinstance(learned, dict) or learned.get("kind") != (
            AuditoryReciprocityKind.SPOKEN_FORM.value
        ):
            continue
        label = learned.get("tutor_label")
        raw_branches = learned.get("branches")
        if (
            not isinstance(label, str)
            or not label
            or not isinstance(raw_branches, list)
            or not 1 <= len(raw_branches) <= MAX_PATH_BRANCHES_PER_CLASS
        ):
            raise ValueError("incremental auditory learned class is malformed")
        branches = tuple(_branch_from_snapshot(value) for value in raw_branches)
        if any(branch.topology != branches[0].topology for branch in branches[1:]):
            raise ValueError("incremental auditory learned topology changed")
        for left_index, left in enumerate(branches):
            for right in branches[left_index:]:
                reference_count = max(left.sample_count, right.sample_count)
                cells.append(_Cell(
                    tutor_label=label,
                    left=left,
                    right=right,
                    reference_count=reference_count,
                    terminal_floor=min(left.sample_count, right.sample_count),
                    # Tutor-witnessed terminal discovery always has the
                    # direct monotone path.  Recomputing optional recurrence
                    # shortcuts here would add quadratic boot work; the final
                    # existing reciprocity gate retains those semantics.
                    recurrence_incoming=tuple(
                        () for _ in range(reference_count)
                    ),
                ))
    return tuple(cells)


def _advance_row(
    cell: _Cell,
    previous: tuple[IntervalSet, ...] | None,
    *,
    pressure: tuple[float, ...],
    phase_advance: tuple[float, ...],
    phase_prior_pressure: tuple[float, ...],
) -> tuple[IntervalSet, ...] | None:
    current: list[IntervalSet] = [() for _ in range(cell.reference_count)]
    for reference_index in range(cell.reference_count):
        if previous is None and reference_index == 0:
            predecessors: IntervalSet = ((0.0, 1.0),)
        else:
            incoming = []
            if previous is not None:
                incoming.extend(previous[reference_index])
            if reference_index > 0:
                incoming.extend(current[reference_index - 1])
            if previous is not None and reference_index > 0:
                incoming.extend(previous[reference_index - 1])
            if previous is not None:
                for recurrent in cell.recurrence_incoming[reference_index]:
                    incoming.extend(previous[recurrent])
            predecessors = tuple(incoming)
        if not predecessors:
            continue
        local = _local_interval(
            cell,
            query_pressure=pressure,
            query_phase_advance=phase_advance,
            query_phase_prior_pressure=phase_prior_pressure,
            reference_index=reference_index,
        )
        if local is None:
            continue
        intersected = _intersect_many(predecessors, local)
        if intersected is None:
            return None
        current[reference_index] = intersected
    return tuple(current)


class AuditoryIncrementalTerminalOwner:
    """Bounded 10 ms proposal automaton with a full-field positive gate."""

    def __init__(
        self,
        *,
        reciprocity_owner: AuditoryReciprocityOwner,
        max_active_trackers: int = MAX_ACTIVE_TRACKERS,
        log_event=None,
        _prepared_cells: tuple[_Cell, ...] | None = None,
    ) -> None:
        if not isinstance(reciprocity_owner, AuditoryReciprocityOwner):
            raise TypeError("incremental terminal requires reciprocity ownership")
        if (
            isinstance(max_active_trackers, bool)
            or not isinstance(max_active_trackers, int)
            or max_active_trackers <= 0
            or max_active_trackers > MAX_ACTIVE_TRACKERS
        ):
            raise ValueError("incremental tracker capacity is invalid")
        self._reciprocity_owner = reciprocity_owner
        self._max_active_trackers = max_active_trackers
        self._log_event = log_event or (lambda *_args, **_kwargs: None)
        self._cells = (
            _cells_from_owner(reciprocity_owner)
            if _prepared_cells is None else _prepared_cells
        )
        self._lock = threading.RLock()
        self._clear_live_state()

    def _clear_live_state(self) -> None:
        self._stream_id: str | None = None
        self._last_transport: AuditoryPCMContinuityReceipt | None = None
        self._last_cochlear: AuditoryGammatoneContinuationReceipt | None = None
        self._last_result: AuditoryIncrementalAdvance | None = None
        self._buffer_start = 0
        self._pcm = bytearray()
        self._evidence: list[_Evidence] = []
        self._frames: list[_Frame] = []
        self._trackers: list[_Tracker] = []
        self._pending: dict[int, _PendingTerminal] = {}

    @property
    def active_tracker_count(self) -> int:
        with self._lock:
            return len(self._trackers)

    @property
    def retained_sample_count(self) -> int:
        with self._lock:
            return len(self._pcm) // 2

    @property
    def learned_cell_count(self) -> int:
        return len(self._cells)

    def snapshot(self) -> dict[str, object]:
        return {
            "active_state_persisted": False,
            "learned_cell_count": len(self._cells),
            "schema": "guala.auditory.incremental_snapshot.v1",
        }

    def _make_result(
        self,
        status: AuditoryIncrementalStatus,
        *,
        reply_candidate: AuditoryIncrementalTerminalEvent | None = None,
        processed_hops: int = 0,
    ) -> AuditoryIncrementalAdvance:
        payload = _advance_payload(
            status=status,
            reply_candidate=reply_candidate,
            processed_hops=processed_hops,
            active_tracker_count=len(self._trackers),
        )
        result = AuditoryIncrementalAdvance(
            status=status,
            reply_candidate=reply_candidate,
            processed_hops=processed_hops,
            active_tracker_count=len(self._trackers),
            authority_receipt_sha256=_digest(payload),
        )
        result.verify()
        self._last_result = result
        return result

    @staticmethod
    def _frame_values(
        capture: AuditoryFullFieldCapture,
        auditory_l5: AuditoryL5Experience,
    ) -> tuple[
        tuple[int, tuple[float, ...], tuple[float, ...]], ...
    ]:
        if len(auditory_l5.ports) != COCHLEAR_CHANNEL_COUNT:
            raise ValueError("incremental auditory L5 topology is incomplete")
        if any(
            len(port.samples) != capture.frame_count
            or len(port.l4_field_tuples) == 0
            or tuple(
                value.tuple_index for value in port.l4_field_tuples
            ) != tuple(range(len(port.l4_field_tuples)))
            or any(
                tuple(name for name, _ in value.fields) != DSF_FIELD_ORDER
                for value in port.l4_field_tuples
            )
            for port in auditory_l5.ports
        ):
            raise ValueError("incremental auditory L5 frame field is incomplete")
        completions = []
        for offset_ns in capture.channels[0].causal_offsets_ns:
            numerator = offset_ns * PCM_SAMPLE_RATE_HZ
            if numerator % 1_000_000_000:
                raise ValueError("incremental auditory frame left the native grid")
            completions.append(numerator // 1_000_000_000)
        frames = []
        for frame_index, completion in enumerate(completions):
            pressures = []
            phases = []
            for port_index, (channel, port) in enumerate(
                zip(capture.channels, auditory_l5.ports, strict=True)
            ):
                if (
                    port.topology_index != port_index
                    or port.substream_id != channel.definition.name
                    or port.samples[frame_index].source_index != frame_index
                    or Fraction.from_float(
                        channel.pressure_envelope_full_scale[frame_index]
                    ) != port.samples[frame_index].pressure
                    or Fraction.from_float(
                        channel.carrier_phase_turns[frame_index]
                    ) != port.samples[frame_index].phase_turns
                ):
                    raise ValueError(
                        "incremental auditory capture differs from settled L5"
                    )
                pressures.append(float(port.samples[frame_index].pressure))
                phases.append(float(port.samples[frame_index].phase_turns))
            frames.append((completion, tuple(pressures), tuple(phases)))
        return tuple(frames)

    @staticmethod
    def _verify_chunk(
        pcm_s16le: bytes,
        capture: AuditoryFullFieldCapture,
        auditory_l5: AuditoryL5Experience,
        transport: AuditoryPCMContinuityReceipt,
        cochlear: AuditoryGammatoneContinuationReceipt,
        joint: AuditoryStreamSettlementReceipt,
    ) -> tuple[tuple[int, tuple[float, ...], tuple[float, ...]], ...]:
        if not isinstance(transport, AuditoryPCMContinuityReceipt):
            raise TypeError("incremental terminal requires typed PCM continuity")
        if not isinstance(cochlear, AuditoryGammatoneContinuationReceipt):
            raise TypeError("incremental terminal requires typed cochlear continuity")
        if not isinstance(joint, AuditoryStreamSettlementReceipt):
            raise TypeError("incremental terminal requires typed joint settlement")
        if not isinstance(capture, AuditoryFullFieldCapture):
            raise TypeError("incremental terminal requires typed cochlear frames")
        if not isinstance(auditory_l5, AuditoryL5Experience):
            raise TypeError("incremental terminal requires typed auditory L5")
        transport.verify()
        cochlear.verify()
        joint.verify()
        auditory_l5.verify()
        if (
            not isinstance(pcm_s16le, bytes)
            or len(pcm_s16le) != transport.sample_count * 2
            or hashlib.sha256(pcm_s16le).hexdigest() != transport.pcm_sha256
        ):
            raise ValueError("incremental auditory PCM differs from transport")
        if (
            capture.source_first_sample_index != transport.first_sample_index
            or capture.input_sample_count != transport.sample_count
            or capture.continuation_receipt_sha256 != cochlear.receipt_sha256
            or cochlear.stream_id != transport.stream_id
            or cochlear.sequence != transport.sequence
            or cochlear.first_sample_index != transport.first_sample_index
            or cochlear.sample_count != transport.sample_count
            or cochlear.transport_receipt_sha256 != transport.receipt_sha256
            or joint.stream_id != transport.stream_id
            or joint.sequence != transport.sequence
            or joint.first_sample_index != transport.first_sample_index
            or joint.sample_count != transport.sample_count
            or joint.transport_receipt_sha256 != transport.receipt_sha256
            or joint.cochlear_receipt_sha256 != cochlear.receipt_sha256
            or joint.auditory_l5_authority_receipt_sha256
            != auditory_l5.authority_receipt_sha256
            or joint.assembly_id != auditory_l5.assembly_id
        ):
            raise ValueError("incremental auditory authorities are not joint")
        expected_start = Fraction(
            transport.source_epoch_start_ns,
            1_000_000_000,
        ) + Fraction(transport.first_sample_index, PCM_SAMPLE_RATE_HZ)
        expected_end = expected_start + Fraction(
            transport.sample_count, PCM_SAMPLE_RATE_HZ
        )
        if (
            joint.source_time_start != expected_start
            or joint.source_time_end != expected_end
            or auditory_l5.source_time_start != expected_start
            or auditory_l5.source_time_end != expected_end
        ):
            raise ValueError("incremental auditory source interval changed")
        frames = AuditoryIncrementalTerminalOwner._frame_values(
            capture, auditory_l5
        )
        if not frames:
            raise ValueError("incremental auditory chunk has no completed hop")
        if (
            frames[0][0] <= transport.first_sample_index
            or frames[-1][0] > transport.last_sample_index_exclusive
            or any(
                right[0] - left[0] != OBSERVATION_HOP_SAMPLES
                for left, right in zip(frames, frames[1:], strict=False)
            )
        ):
            raise ValueError("incremental auditory hop identity changed")
        return frames

    def _is_continuous(
        self,
        transport: AuditoryPCMContinuityReceipt,
        cochlear: AuditoryGammatoneContinuationReceipt,
    ) -> bool:
        prior_transport = self._last_transport
        prior_cochlear = self._last_cochlear
        return bool(
            prior_transport is not None
            and prior_cochlear is not None
            and transport.stream_id == prior_transport.stream_id
            and transport.source_epoch_start_ns
            == prior_transport.source_epoch_start_ns
            and transport.sequence == prior_transport.sequence + 1
            and transport.first_sample_index
            == prior_transport.last_sample_index_exclusive
            and transport.prior_receipt_sha256
            == prior_transport.receipt_sha256
            and cochlear.prior_state_receipt_sha256
            == prior_cochlear.receipt_sha256
        )

    def _append_pcm(
        self,
        pcm_s16le: bytes,
        transport: AuditoryPCMContinuityReceipt,
        cochlear: AuditoryGammatoneContinuationReceipt,
        joint: AuditoryStreamSettlementReceipt,
    ) -> bool:
        if not self._pcm:
            self._buffer_start = transport.first_sample_index
        expected = self._buffer_start + len(self._pcm) // 2
        if transport.first_sample_index != expected:
            raise RuntimeError("incremental auditory rolling PCM lost continuity")
        self._pcm.extend(pcm_s16le)
        self._evidence.append(_Evidence(
            start=transport.first_sample_index,
            end=transport.last_sample_index_exclusive,
            transport=transport.receipt_sha256,
            cochlear=cochlear.receipt_sha256,
            joint=joint.authority_receipt_sha256,
        ))
        current_end = transport.last_sample_index_exclusive
        keep_from = max(0, current_end - MAX_EVENT_SAMPLES)
        if keep_from <= self._buffer_start:
            return False
        drop = keep_from - self._buffer_start
        del self._pcm[:drop * 2]
        self._buffer_start = keep_from
        self._evidence = [value for value in self._evidence if value.end > keep_from]
        self._frames = [
            value for value in self._frames
            if value.completion_sample > keep_from
        ]
        expired = any(value.start_sample < keep_from for value in self._trackers)
        self._trackers = [
            value for value in self._trackers if value.start_sample >= keep_from
        ]
        if any(start < keep_from for start in self._pending):
            expired = True
            self._pending = {
                start: value
                for start, value in self._pending.items()
                if start >= keep_from
            }
        return expired

    def _candidate_pcm(self, start: int, end: int) -> bytes:
        first = start - self._buffer_start
        last = end - self._buffer_start
        if first < 0 or last <= first or last * 2 > len(self._pcm):
            raise RuntimeError("incremental auditory candidate left PCM retention")
        return bytes(self._pcm[first * 2:last * 2])

    def _candidate_evidence(
        self, start: int, end: int
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        values = [
            value for value in self._evidence
            if value.start < end and value.end > start
        ]
        if not values:
            raise RuntimeError("incremental auditory candidate has no evidence")
        return (
            tuple(value.transport for value in values),
            tuple(value.cochlear for value in values),
            tuple(value.joint for value in values),
        )

    def _full_gate(
        self, start: int, end: int
    ) -> tuple[AuditoryRecognitionState, _PendingTerminal | None]:
        if self._stream_id is None:
            raise RuntimeError("incremental auditory candidate has no stream")
        # Retained PCM proves exact sample identity, but the candidate field is
        # rebuilt from the already-continuous cochlear frames.  Resetting the
        # gammatone recurrence at ``start`` would fabricate a different sense.
        pcm_sha256 = hashlib.sha256(self._candidate_pcm(start, end)).hexdigest()
        selected = tuple(
            value for value in self._frames
            if start < value.completion_sample <= end
        )
        if (
            not selected
            or selected[0].completion_sample
            != start + OBSERVATION_HOP_SAMPLES
            or selected[-1].completion_sample != end
            or len(selected) != (end - start) // OBSERVATION_HOP_SAMPLES
        ):
            raise RuntimeError("incremental auditory candidate frame extent changed")
        epoch_start = self._evidence_epoch_start()
        ports = []
        for topology_index, definition in enumerate(AUDITORY_CHANNELS):
            ports.append(NativeSensorySubstreamInput(
                sense=PhysicalSense.SOUND,
                sensor_id="microphone-gammatone-cochlear-field",
                substream_id=definition.name,
                topology_index=topology_index,
                coordinates=(
                    NativeAxisCoordinate("cochlear-channel", definition.name),
                    NativeAxisCoordinate("centre-hz", str(definition.centre_hz)),
                    NativeAxisCoordinate(
                        "erb-width-hz", str(definition.erb_width_hz)
                    ),
                    NativeAxisCoordinate("gammatone-order", "4"),
                    NativeAxisCoordinate(
                        "observation-hop-samples",
                        str(OBSERVATION_HOP_SAMPLES),
                    ),
                ),
                physical_quantity="cochlear-pressure-envelope",
                physical_unit="full-scale-pressure",
                source_times=tuple(
                    epoch_start
                    + Fraction(value.completion_sample, PCM_SAMPLE_RATE_HZ)
                    for value in selected
                ),
                normalized_signal=tuple(
                    value.pressure[topology_index] for value in selected
                ),
                phase_turns=tuple(
                    Fraction.from_float(value.phase[topology_index])
                    for value in selected
                ),
            ))
        identity = _digest({
            "pcm_sha256": pcm_sha256,
            "source_sample_end": end,
            "source_sample_start": start,
            "stream_id": self._stream_id,
        })
        built = build_six_sense_full_field(
            assembly_id=f"auditory-incremental-{identity}",
            source_time_start=(
                epoch_start + Fraction(start, PCM_SAMPLE_RATE_HZ)
            ),
            source_time_end=epoch_start + Fraction(end, PCM_SAMPLE_RATE_HZ),
            observed_substreams={PhysicalSense.SOUND: tuple(ports)},
            states={
                sense: (
                    SenseBoundaryState.OBSERVED
                    if sense is PhysicalSense.SOUND
                    else SenseBoundaryState.SENSOR_UNAVAILABLE
                )
                for sense in SENSE_ORDER
            },
        )
        experience = AuditoryL5Owner(
            log_event=lambda *_args, **_kwargs: None
        ).settle(built, event_boundary="ambient")
        if experience is None:
            raise RuntimeError("incremental auditory candidate did not settle")
        experience.verify()
        recognition = self._reciprocity_owner.recognize(
            experience,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
        )
        if recognition.state is not AuditoryRecognitionState.UNIQUE:
            return recognition.state, None
        if not recognition.tutor_label:
            raise RuntimeError("unique incremental recognition has no tutor label")
        transport, cochlear, joint = self._candidate_evidence(start, end)
        return recognition.state, _PendingTerminal(
            start=start,
            end=end,
            tutor_label=recognition.tutor_label,
            structural_fingerprint=experience.structural_fingerprint,
            l5_authority_receipt_sha256=experience.authority_receipt_sha256,
            transport_receipt_sha256s=transport,
            cochlear_receipt_sha256s=cochlear,
            joint_settlement_receipt_sha256s=joint,
        )

    def _evidence_epoch_start(self) -> Fraction:
        if self._last_transport is None:
            raise RuntimeError("incremental auditory stream has no time authority")
        return Fraction(
            self._last_transport.source_epoch_start_ns,
            1_000_000_000,
        )

    def _event(self, value: _PendingTerminal) -> AuditoryIncrementalTerminalEvent:
        if self._stream_id is None:
            raise RuntimeError("incremental auditory terminal has no stream")
        event_id = _digest({
            "source_sample_end": value.end,
            "source_sample_start": value.start,
            "stream_id": self._stream_id,
            "structural_fingerprint": value.structural_fingerprint,
        })
        payload = _event_payload(
            event_id=event_id,
            stream_id=self._stream_id,
            source_sample_start=value.start,
            source_sample_end=value.end,
            tutor_label=value.tutor_label,
            structural_fingerprint=value.structural_fingerprint,
            l5_authority_receipt_sha256=value.l5_authority_receipt_sha256,
            transport_receipt_sha256s=value.transport_receipt_sha256s,
            cochlear_receipt_sha256s=value.cochlear_receipt_sha256s,
            joint_settlement_receipt_sha256s=(
                value.joint_settlement_receipt_sha256s
            ),
        )
        event = AuditoryIncrementalTerminalEvent(
            event_id=event_id,
            stream_id=self._stream_id,
            source_sample_start=value.start,
            source_sample_end=value.end,
            tutor_label=value.tutor_label,
            structural_fingerprint=value.structural_fingerprint,
            l5_authority_receipt_sha256=value.l5_authority_receipt_sha256,
            transport_receipt_sha256s=value.transport_receipt_sha256s,
            cochlear_receipt_sha256s=value.cochlear_receipt_sha256s,
            joint_settlement_receipt_sha256s=(
                value.joint_settlement_receipt_sha256s
            ),
            authority_receipt_sha256=_digest(payload),
        )
        event.verify()
        return event

    def _spawn(
        self,
        completion: int,
        pressure: tuple[float, ...],
        phase: tuple[float, ...],
    ) -> None:
        start = completion - OBSERVATION_HOP_SAMPLES
        pressure_uncertainty = 2.0 * float(PCM_PRESSURE_QUANTUM)
        for cell_index, cell in enumerate(self._cells):
            interval: Interval | None = (0.0, 1.0)
            for port in range(COCHLEAR_CHANNEL_COUNT):
                left, _ = _branch_sample(
                    cell.left, port, 0, cell.reference_count
                )
                right, _ = _branch_sample(
                    cell.right, port, 0, cell.reference_count
                )
                interval = _intersect_lambda(
                    interval,
                    query=pressure[port],
                    left=left,
                    right=right,
                    uncertainty=pressure_uncertainty,
                )
                if interval is None:
                    break
            if interval is not None:
                self._trackers.append(_Tracker(
                    cell_index=cell_index,
                    start_sample=start,
                    frames_seen=1,
                    first_pressure=pressure,
                    first_phase=phase,
                    previous_pressure=pressure,
                    previous_phase=phase,
                    row=None,
                ))

    def _advance_tracker(
        self,
        tracker: _Tracker,
        pressure: tuple[float, ...],
        phase: tuple[float, ...],
    ) -> bool | None:
        cell = self._cells[tracker.cell_index]
        delta = tuple(
            current - prior
            for current, prior in zip(
                phase, tracker.previous_phase, strict=True
            )
        )
        if tracker.row is None:
            first_row = _advance_row(
                cell,
                None,
                pressure=tracker.first_pressure,
                phase_advance=delta,
                phase_prior_pressure=pressure,
            )
            if first_row is None:
                return None
            if not any(first_row):
                return False
            row = _advance_row(
                cell,
                first_row,
                pressure=pressure,
                phase_advance=delta,
                phase_prior_pressure=tracker.first_pressure,
            )
        else:
            row = _advance_row(
                cell,
                tracker.row,
                pressure=pressure,
                phase_advance=delta,
                phase_prior_pressure=tracker.previous_pressure,
            )
        if row is None:
            return None
        if not any(row):
            return False
        tracker.row = row
        tracker.frames_seen += 1
        tracker.previous_pressure = pressure
        tracker.previous_phase = phase
        return bool(
            tracker.frames_seen >= cell.terminal_floor and row[-1]
        )

    @staticmethod
    def _resolve_closed(
        values: list[_PendingTerminal],
    ) -> tuple[_PendingTerminal | None, bool]:
        if not values:
            return None, False
        labels = {value.tutor_label for value in values}
        if len(labels) != 1:
            return None, True
        ordered = sorted(
            values,
            key=lambda value: (
                value.end - value.start,
                -value.start,
                value.structural_fingerprint,
            ),
            reverse=True,
        )
        return ordered[0], False

    def _process_frame(
        self,
        completion: int,
        pressure: tuple[float, ...],
        phase: tuple[float, ...],
    ) -> tuple[_PendingTerminal | None, bool, bool]:
        prior_pending = dict(self._pending)
        terminal_spans = set()
        survivors = []
        resource = False
        work_cells = 0
        for tracker in self._trackers:
            cell = self._cells[tracker.cell_index]
            work_cells += cell.reference_count * (
                2 if tracker.row is None else 1
            )
            if work_cells > MAX_REACHABILITY_CELLS_PER_RECOGNITION:
                self._trackers.clear()
                self._pending.clear()
                return None, False, True
            terminal = self._advance_tracker(tracker, pressure, phase)
            if terminal is None:
                resource = True
                self._pending.pop(tracker.start_sample, None)
            elif terminal is False:
                if tracker.row is not None and any(tracker.row):
                    survivors.append(tracker)
            else:
                survivors.append(tracker)
                terminal_spans.add((tracker.start_sample, completion))
        self._trackers = survivors
        self._spawn(completion, pressure, phase)
        if len(self._trackers) > self._max_active_trackers:
            self._trackers.clear()
            self._pending.clear()
            return None, False, True

        # Once a witnessed terminal exists, every later contiguous hop is a
        # same-start extension question.  The DP may retain lagging alternate
        # paths after the actual terminal; those paths cannot postpone closure
        # unless the freshly rebuilt full candidate is still UNIQUE.
        active_starts_before_gate = {
            value.start_sample for value in self._trackers
        }
        terminal_spans.update(
            (start, completion)
            for start, pending in self._pending.items()
            if start in active_starts_before_gate and completion > pending.end
        )

        ambiguous = False
        rejected_starts = set()
        for start, end in sorted(terminal_spans):
            state, pending = self._full_gate(start, end)
            if state is AuditoryRecognitionState.UNIQUE:
                if pending is None:
                    raise RuntimeError("unique full-field gate lost its terminal")
                self._pending[start] = pending
            elif state is AuditoryRecognitionState.AMBIGUOUS:
                self._pending.pop(start, None)
                rejected_starts.add(start)
                ambiguous = True
            elif state is AuditoryRecognitionState.INDETERMINATE:
                self._pending.pop(start, None)
                rejected_starts.add(start)
                resource = True
            else:
                if start in self._pending:
                    prior_pending[start] = self._pending.pop(start)
                rejected_starts.add(start)
        if rejected_starts:
            self._trackers = [
                value for value in self._trackers
                if value.start_sample not in rejected_starts
            ]
        active_starts = {value.start_sample for value in self._trackers}
        closed = []
        for start, pending in tuple(prior_pending.items()):
            if start not in active_starts and start not in self._pending:
                closed.append(pending)
        chosen, closure_ambiguity = self._resolve_closed(closed)
        ambiguous = ambiguous or closure_ambiguity
        if chosen is not None:
            self._trackers = [
                value for value in self._trackers
                if value.start_sample >= chosen.end
            ]
            self._pending = {
                start: value for start, value in self._pending.items()
                if start >= chosen.end
            }
        return chosen, ambiguous, resource

    def advance(
        self,
        *,
        pcm_s16le: bytes,
        capture: AuditoryFullFieldCapture,
        auditory_l5: AuditoryL5Experience,
        transport: AuditoryPCMContinuityReceipt,
        cochlear: AuditoryGammatoneContinuationReceipt,
        joint_settlement: AuditoryStreamSettlementReceipt,
    ) -> AuditoryIncrementalAdvance:
        frames = self._verify_chunk(
            pcm_s16le,
            capture,
            auditory_l5,
            transport,
            cochlear,
            joint_settlement,
        )
        with self._lock:
            if (
                self._last_transport is not None
                and transport.receipt_sha256
                == self._last_transport.receipt_sha256
            ):
                if self._last_result is None:
                    raise RuntimeError("incremental auditory retry has no result")
                return self._last_result
            first = self._last_transport is None
            valid_first = (
                transport.sequence == 0
                and transport.first_sample_index == 0
                and transport.prior_receipt_sha256 is None
                and cochlear.prior_state_receipt_sha256 is None
            )
            if (first and not valid_first) or (
                not first and not self._is_continuous(transport, cochlear)
            ):
                self._clear_live_state()
                return self._make_result(
                    AuditoryIncrementalStatus.DISCONTINUITY,
                    processed_hops=0,
                )
            if first:
                self._stream_id = transport.stream_id
            self._last_transport = transport
            self._last_cochlear = cochlear
            if not self._cells:
                return self._make_result(
                    AuditoryIncrementalStatus.UNKNOWN,
                    processed_hops=len(frames),
                )
            expired = self._append_pcm(
                pcm_s16le, transport, cochlear, joint_settlement
            )
            self._frames.extend(
                _Frame(completion, pressure, phase)
                for completion, pressure, phase in frames
            )
            released = []
            ambiguous = False
            resource = expired
            for completion, pressure, phase in frames:
                terminal, frame_ambiguous, frame_resource = self._process_frame(
                    completion, pressure, phase
                )
                ambiguous = ambiguous or frame_ambiguous
                resource = resource or frame_resource
                if terminal is not None:
                    released.append(terminal)
                if len(released) > 1:
                    released.clear()
                    resource = True
                    self._trackers.clear()
                    self._pending.clear()
                    break
            reply = self._event(released[0]) if len(released) == 1 else None
            if resource:
                reply = None
                status = AuditoryIncrementalStatus.INDETERMINATE_RESOURCE
            elif ambiguous:
                reply = None
                status = AuditoryIncrementalStatus.AMBIGUOUS
            elif reply is not None:
                status = AuditoryIncrementalStatus.RELEASED_UNIQUE
            elif self._trackers or self._pending:
                status = AuditoryIncrementalStatus.CONTINUING
            else:
                status = AuditoryIncrementalStatus.UNKNOWN
            result = self._make_result(
                status,
                reply_candidate=reply,
                processed_hops=len(frames),
            )
            self._log_event(
                "auditory_incremental_terminal_advanced",
                status=status.value,
                processed_hops=len(frames),
                active_tracker_count=len(self._trackers),
                reply_candidate_count=1 if reply is not None else 0,
            )
            return result

    def close_stream(self) -> AuditoryIncrementalAdvance:
        with self._lock:
            chosen, ambiguous = self._resolve_closed(list(self._pending.values()))
            reply = self._event(chosen) if chosen is not None else None
            self._clear_live_state()
            status = (
                AuditoryIncrementalStatus.AMBIGUOUS
                if ambiguous
                else AuditoryIncrementalStatus.RELEASED_UNIQUE
                if reply is not None
                else AuditoryIncrementalStatus.UNKNOWN
            )
            return self._make_result(status, reply_candidate=reply)


@dataclass(slots=True)
class _OwnedIncrementalTerminal:
    owner: AuditoryIncrementalTerminalOwner
    last_activity: float


class AuditoryIncrementalTerminalRegistry:
    """Bound one incremental terminal owner to each live PCM stream epoch."""

    def __init__(
        self,
        *,
        reciprocity_owner: AuditoryReciprocityOwner,
        clock=time.monotonic,
        stream_capacity: int = PCM_STREAM_CAPACITY,
        idle_seconds: int = PCM_STREAM_IDLE_SECONDS,
        log_event=None,
    ) -> None:
        if not isinstance(reciprocity_owner, AuditoryReciprocityOwner):
            raise TypeError("incremental registry requires reciprocity ownership")
        if (
            isinstance(stream_capacity, bool)
            or not isinstance(stream_capacity, int)
            or stream_capacity <= 0
            or isinstance(idle_seconds, bool)
            or not isinstance(idle_seconds, int)
            or idle_seconds <= 0
        ):
            raise ValueError("incremental registry bounds must be positive")
        self._reciprocity_owner = reciprocity_owner
        self._clock = clock
        self._stream_capacity = stream_capacity
        self._idle_seconds = idle_seconds
        self._log_event = log_event or (lambda *_args, **_kwargs: None)
        self._lock = threading.RLock()
        self._cells = _cells_from_owner(reciprocity_owner)
        self._streams: OrderedDict[str, _OwnedIncrementalTerminal] = (
            OrderedDict()
        )

    def _expire_locked(self, now: float) -> None:
        for stream_id in tuple(self._streams):
            if now - self._streams[stream_id].last_activity > self._idle_seconds:
                del self._streams[stream_id]
                self._log_event(
                    "auditory_incremental_terminal_expired",
                    stream_id=stream_id,
                )

    def advance(self, **authorities) -> AuditoryIncrementalAdvance:
        transport = authorities.get("transport")
        if not isinstance(transport, AuditoryPCMContinuityReceipt):
            raise TypeError("incremental registry requires typed PCM continuity")
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            mounted = self._streams.get(transport.stream_id)
            if transport.sequence == 0:
                if mounted is not None:
                    raise ValueError("incremental stream epoch already exists")
                if len(self._streams) >= self._stream_capacity:
                    raise RuntimeError("incremental stream capacity is full")
                mounted = _OwnedIncrementalTerminal(
                    owner=AuditoryIncrementalTerminalOwner(
                        reciprocity_owner=self._reciprocity_owner,
                        log_event=self._log_event,
                        _prepared_cells=self._cells,
                    ),
                    last_activity=now,
                )
                self._streams[transport.stream_id] = mounted
            elif mounted is None:
                raise ValueError("incremental stream epoch is unknown or expired")
            result = mounted.owner.advance(**authorities)
            if result.status is AuditoryIncrementalStatus.DISCONTINUITY:
                self._streams.pop(transport.stream_id, None)
                return result
            mounted.last_activity = now
            self._streams.move_to_end(transport.stream_id)
            return result

    def close(
        self,
        stream_id: str,
        *,
        release_terminal: bool,
    ) -> AuditoryIncrementalAdvance | None:
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError("incremental stream id is required")
        with self._lock:
            mounted = self._streams.pop(stream_id, None)
        if mounted is None or not release_terminal:
            return None
        return mounted.owner.close_stream()

    def refresh_learning(self) -> int:
        """Atomically rebuild tutor cells and discard provisional streams."""

        cells = _cells_from_owner(self._reciprocity_owner)
        with self._lock:
            count = len(self._streams)
            self._streams.clear()
            self._cells = cells
            return count

    def status(self) -> dict[str, int]:
        now = self._clock()
        with self._lock:
            self._expire_locked(now)
            return {
                "active_streams": len(self._streams),
                "stream_capacity": self._stream_capacity,
                "retained_samples": sum(
                    value.owner.retained_sample_count
                    for value in self._streams.values()
                ),
                "active_trackers": sum(
                    value.owner.active_tracker_count
                    for value in self._streams.values()
                ),
                "learned_cells": len(self._cells),
            }


__all__ = (
    "AUDITORY_INCREMENTAL_ADVANCE_SCHEMA",
    "AUDITORY_INCREMENTAL_EVENT_SCHEMA",
    "AuditoryIncrementalAdvance",
    "AuditoryIncrementalStatus",
    "AuditoryIncrementalTerminalEvent",
    "AuditoryIncrementalTerminalOwner",
    "AuditoryIncrementalTerminalRegistry",
    "MAX_ACTIVE_TRACKERS",
    "MAX_EVENT_SAMPLES",
    "MAX_EVENT_HOPS",
)
