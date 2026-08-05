"""Isolated bilateral cross-receptor resonance trajectory probe.

This file is an audit boundary, not production architecture.  It evaluates
one precise L5 proposition without changing the canonical L0--L4 kernel:

* both physical ears remain distinct;
* all sixteen cumulative-phase receptors in each ear are graph vertices;
* all 496 unordered edges of the fixed 32-vertex topology execute the pinned
  certified gamma-squared operator;
* every edge fact and all 64 pressure/phase L4 support receipts survive;
* the scalar graph meet is retained only as an operator diagnostic and never
  participates in relation, memory, sound identity, or word identity;
* labels are admitted only after the complete relation matrix exists.

The only tested relation in this first probe is exact reciprocal L6 recurrence
of corresponding certified edge facts.  It has no score, tolerance, nearest
match, interpolation, alignment, transcript, or label input.  Failure is a
falsification result, not a reason to silently invent another quotient.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import wave
import zipfile
from dataclasses import asdict, dataclass
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from dsf_ai_service.glew_runtime.closed_experience import (
    source_evidence_stream_receipt_payload,
)
from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptRegistry,
    receipt_sha256,
    sha256_digest,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.operators import (
    CausalGrid,
    MountedResonanceGraph,
    RequiredEdge,
    ResonanceOperatorAuthority,
    causal_grid_receipt_payload,
    compute_resonance_confirmation,
    resonance_graph_receipt_payload,
    resonance_operator_receipt_payload,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    auditory_pressure_energy_relevance,
)
from dsf_ai_service.substrate.canonical_l6 import (
    L6Direction,
    canonical_l6_direction,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    COCHLEAR_CHANNEL_COUNT,
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
    AuditoryFullFieldCapture,
    transduce_auditory_full_field,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    binaural_sound_field_inputs,
    signed_pcm16_samples,
)
from tools.isolated_w1_physical_stereo_path import (
    PhysicalStereoAuditAuthority,
)
from tools.probe_auditory_full_field_separability_census import (
    ARCHIVE_SHA256,
    COMMANDS,
    CorpusItem,
    _select_corpus,
)


SCHEMA = "guala.audit.bilateral_cross_receptor_trajectory.v1"
RELATION_SCHEMA = (
    "guala.audit.bilateral_cross_receptor_trajectory_relation.v1"
)
REPORT_SCHEMA = (
    "guala.audit.bilateral_cross_receptor_trajectory_census.v1"
)
GRAPH_ID = "guala-auditory-complete-bilateral-cumulative-phase-32-v1"
GRID_ID = "guala-auditory-bilateral-receptor-causal-grid-v1"
OPERATOR_ID = "guala-auditory-bilateral-ruf-arb-v1"
PRECISION_BITS = 256
VERTEX_COUNT = COCHLEAR_CHANNEL_COUNT * 2
EDGE_COUNT = VERTEX_COUNT * (VERTEX_COUNT - 1) // 2
L4_SUPPORT_COUNT = VERTEX_COUNT * 2
AUTHORITY_KEY = (
    b"guala-auditory-bilateral-cross-receptor-census-20260727"
)
PROFILE = b"guala.auditory.bilateral.cross-receptor.profile.v1"
CALIBRATION = (
    b"guala.auditory.bilateral.cross-receptor.calibration.v1"
)
RELEVANCE = (
    b"guala.auditory.bilateral.cross-receptor.relevance-p-squared.v1"
)


class TrajectoryState(str, Enum):
    OBSERVED = "observed"
    UNRESOLVED = "unresolved"
    RESOURCE_EXHAUSTED = "resource_exhausted"


@dataclass(frozen=True, slots=True)
class CertifiedEdgeFact:
    left_vertex: str
    right_vertex: str
    lower_mantissa: int
    lower_exponent: int
    upper_mantissa: int
    upper_exponent: int
    proved_zero_energy: bool

    def token(self) -> tuple[object, ...]:
        return (
            self.left_vertex,
            self.right_vertex,
            self.lower_mantissa,
            self.lower_exponent,
            self.upper_mantissa,
            self.upper_exponent,
            self.proved_zero_energy,
        )


@dataclass(frozen=True, slots=True)
class AuditoryBilateralResonanceTrajectory:
    state: TrajectoryState
    source_receipt_sha256s: tuple[str, str]
    frame_count: int
    graph_authority_receipt_sha256: str
    grid_authority_receipt_sha256: str
    operator_authority_receipt_sha256: str
    edge_facts: tuple[CertifiedEdgeFact, ...]
    l4_support_receipt_sha256s: tuple[str, ...]
    left_capture_receipt_sha256: str
    right_capture_receipt_sha256: str
    spatially_resolved: bool
    diagnostic_scalar_meet_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "diagnostic_scalar_meet_receipt_sha256": (
                self.diagnostic_scalar_meet_receipt_sha256
            ),
            "edge_facts": [asdict(value) for value in self.edge_facts],
            "frame_count": self.frame_count,
            "graph_authority_receipt_sha256": (
                self.graph_authority_receipt_sha256
            ),
            "grid_authority_receipt_sha256": (
                self.grid_authority_receipt_sha256
            ),
            "l4_support_receipt_sha256s": list(
                self.l4_support_receipt_sha256s
            ),
            "left_capture_receipt_sha256": (
                self.left_capture_receipt_sha256
            ),
            "operator_authority_receipt_sha256": (
                self.operator_authority_receipt_sha256
            ),
            "right_capture_receipt_sha256": (
                self.right_capture_receipt_sha256
            ),
            "schema": SCHEMA,
            "source_receipt_sha256s": list(
                self.source_receipt_sha256s
            ),
            "spatially_resolved": self.spatially_resolved,
            "state": self.state.value,
        }

    def verify(self) -> None:
        for value, name in (
            (
                self.graph_authority_receipt_sha256,
                "bilateral graph authority",
            ),
            (
                self.grid_authority_receipt_sha256,
                "bilateral grid authority",
            ),
            (
                self.operator_authority_receipt_sha256,
                "bilateral operator authority",
            ),
            (
                self.left_capture_receipt_sha256,
                "left capture authority",
            ),
            (
                self.right_capture_receipt_sha256,
                "right capture authority",
            ),
            (
                self.diagnostic_scalar_meet_receipt_sha256,
                "diagnostic scalar meet receipt",
            ),
            (
                self.authority_receipt_sha256,
                "trajectory authority",
            ),
            *(
                (value, "source authority")
                for value in self.source_receipt_sha256s
            ),
            *(
                (value, "L4 support authority")
                for value in self.l4_support_receipt_sha256s
            ),
        ):
            sha256_digest(value, name)
        expected_vertices = tuple(
            f"{ear}:erb_{channel:02d}"
            for ear in ("left", "right")
            for channel in range(COCHLEAR_CHANNEL_COUNT)
        )
        expected_edges = tuple(
            (expected_vertices[left], expected_vertices[right])
            for left in range(VERTEX_COUNT)
            for right in range(left + 1, VERTEX_COUNT)
        )
        if (
            self.state is not TrajectoryState.OBSERVED
            or not 0 < self.frame_count <= 800
            or len(self.edge_facts) != EDGE_COUNT
            or tuple(
                (value.left_vertex, value.right_vertex)
                for value in self.edge_facts
            )
            != expected_edges
            or len(self.l4_support_receipt_sha256s)
            != L4_SUPPORT_COUNT
            or self.authority_receipt_sha256 != _digest(self.payload())
        ):
            raise ValueError(
                "bilateral cross-receptor trajectory authority changed"
            )


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _root(schema: str, values: Iterable[str]) -> str:
    return _digest({
        "schema": schema,
        "sha256s": sorted(set(values)),
    })


def _l6_payload(value: L6Direction) -> dict[str, object]:
    return {
        "dimensions": value.dimensions,
        "effective_dimensions": value.effective_dimensions,
        "knee": value.knee,
        "locked": value.locked,
        "matching_non_null": value.matching_non_null,
        "matching_quiescent": value.matching_quiescent,
    }


def _capture_receipt(capture: AuditoryFullFieldCapture) -> str:
    capture.__post_init__()
    return _digest({
        "channels": [
            {
                "cumulative_phase_turns": [
                    float(value).hex()
                    for value in channel.carrier_phase_turns
                ],
                "pressure_envelope": [
                    float(value).hex()
                    for value in channel.pressure_envelope_full_scale
                ],
            }
            for channel in capture.channels
        ],
        "frame_count": capture.frame_count,
        "input_sample_count": capture.input_sample_count,
        "provider_schema": capture.provider_schema,
        "schema": "guala.audit.bilateral_capture_authority.v1",
    })


def _stream_authorities(
    left: AuditoryFullFieldCapture,
    right: AuditoryFullFieldCapture,
) -> tuple[
    tuple[EvidenceStream, ...],
    ReceiptRegistry,
    CausalGrid,
    MountedResonanceGraph,
    ResonanceOperatorAuthority,
]:
    left.__post_init__()
    right.__post_init__()
    if (
        left.frame_count != right.frame_count
        or left.frame_count <= 0
        or tuple(left.channels[0].causal_offsets_ns)
        != tuple(right.channels[0].causal_offsets_ns)
    ):
        raise ValueError(
            "bilateral captures lack one exact common causal grid"
        )
    profile_digest = receipt_sha256(PROFILE)
    calibration_digest = receipt_sha256(CALIBRATION)
    relevance_digest = receipt_sha256(RELEVANCE)
    timestamps = tuple(
        Fraction(value, 1_000_000_000)
        for value in left.channels[0].causal_offsets_ns
    )
    weights = tuple(
        Fraction(OBSERVATION_HOP_SAMPLES, REQUIRED_SAMPLE_RATE_HZ)
        for _timestamp in timestamps
    )
    streams = []
    for ear_id, capture in (("left", left), ("right", right)):
        for channel_index, channel in enumerate(capture.channels):
            relevances = tuple(
                auditory_pressure_energy_relevance(value)
                for value in channel.pressure_envelope_full_scale
            )
            streams.append(EvidenceStream(
                lane_id="sound",
                port_id=f"{ear_id}:erb_{channel_index:02d}",
                evidence_id=(
                    f"{ear_id}-erb-{channel_index:02d}-cumulative-phase"
                ),
                source_epoch="bilateral-cross-receptor-event",
                port_kind="cochlear-cumulative-carrier-phase",
                physical_unit="turns",
                profile_binding_sha256=profile_digest,
                calibration_receipt_sha256=calibration_digest,
                relevance_receipt_sha256=relevance_digest,
                samples=tuple(
                    EvidenceSample(
                        source_index=index,
                        timestamp=timestamps[index],
                        signal=Fraction.from_float(
                            channel.carrier_phase_advance_nyquist_fraction[
                                index
                            ]
                        ),
                        relevance=relevances[index],
                        phase_turns=Fraction.from_float(
                            channel.carrier_phase_turns[index]
                        ),
                    )
                    for index in range(capture.frame_count)
                ),
            ))
    streams_tuple = tuple(streams)
    required_edges = tuple(
        RequiredEdge(
            streams_tuple[left_index].key,
            streams_tuple[right_index].key,
        )
        for left_index in range(VERTEX_COUNT)
        for right_index in range(left_index + 1, VERTEX_COUNT)
    )
    grid_payload = causal_grid_receipt_payload(
        GRID_ID,
        timestamps,
        weights,
    )
    graph_payload = resonance_graph_receipt_payload(
        GRAPH_ID,
        required_edges,
    )
    operator_payload = resonance_operator_receipt_payload(
        OPERATOR_ID,
        PRECISION_BITS,
    )
    stream_payloads = tuple(
        source_evidence_stream_receipt_payload(value)
        for value in streams_tuple
    )
    registry = ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=(
            CALIBRATION,
            RELEVANCE,
            grid_payload,
            graph_payload,
            operator_payload,
            *stream_payloads,
        ),
    )
    grid = CausalGrid(
        grid_id=GRID_ID,
        timestamps=timestamps,
        positive_weights=weights,
        grid_receipt_sha256=receipt_sha256(grid_payload),
    )
    graph = MountedResonanceGraph(
        graph_id=GRAPH_ID,
        required_edges=required_edges,
        authority_receipt_sha256=receipt_sha256(graph_payload),
    )
    operator = ResonanceOperatorAuthority(
        operator_id=OPERATOR_ID,
        precision_bits=PRECISION_BITS,
        authority_receipt_sha256=receipt_sha256(operator_payload),
    )
    return streams_tuple, registry, grid, graph, operator


def build_trajectory(
    *,
    left_capture: AuditoryFullFieldCapture,
    right_capture: AuditoryFullFieldCapture,
    l4_support_receipt_sha256s: Sequence[str],
    source_receipt_sha256s: tuple[str, str],
) -> AuditoryBilateralResonanceTrajectory:
    """Execute all 496 certified edges and preserve complete support."""

    if len(l4_support_receipt_sha256s) != L4_SUPPORT_COUNT:
        raise ValueError(
            "bilateral trajectory requires all 64 L4 support receipts"
        )
    for value in (*l4_support_receipt_sha256s, *source_receipt_sha256s):
        sha256_digest(value, "bilateral trajectory source support")
    streams, registry, grid, graph, operator = _stream_authorities(
        left_capture,
        right_capture,
    )
    confirmation = compute_resonance_confirmation(
        streams,
        grid,
        graph,
        operator,
        registry,
    )
    edge_facts = tuple(
        CertifiedEdgeFact(
            left_vertex=value.edge.left_port_key[1],
            right_vertex=value.edge.right_port_key[1],
            lower_mantissa=value.gamma_squared.lower_mantissa,
            lower_exponent=value.gamma_squared.lower_exponent,
            upper_mantissa=value.gamma_squared.upper_mantissa,
            upper_exponent=value.gamma_squared.upper_exponent,
            proved_zero_energy=value.proved_zero_energy,
        )
        for value in confirmation.edge_facts
    )
    diagnostic_scalar_meet = _digest({
        "ball": asdict(confirmation.value),
        "forbidden_as_identity": True,
        "schema": "guala.audit.bilateral_scalar_diagnostic.v1",
    })
    provisional = AuditoryBilateralResonanceTrajectory(
        state=TrajectoryState.OBSERVED,
        source_receipt_sha256s=source_receipt_sha256s,
        frame_count=left_capture.frame_count,
        graph_authority_receipt_sha256=(
            confirmation.graph_authority_receipt_sha256
        ),
        grid_authority_receipt_sha256=grid.grid_receipt_sha256,
        operator_authority_receipt_sha256=(
            confirmation.operator_authority_receipt_sha256
        ),
        edge_facts=edge_facts,
        l4_support_receipt_sha256s=tuple(
            l4_support_receipt_sha256s
        ),
        left_capture_receipt_sha256=_capture_receipt(left_capture),
        right_capture_receipt_sha256=_capture_receipt(right_capture),
        spatially_resolved=(
            _capture_receipt(left_capture)
            != _capture_receipt(right_capture)
        ),
        diagnostic_scalar_meet_receipt_sha256=(
            diagnostic_scalar_meet
        ),
        authority_receipt_sha256="0" * 64,
    )
    result = AuditoryBilateralResonanceTrajectory(
        state=provisional.state,
        source_receipt_sha256s=provisional.source_receipt_sha256s,
        frame_count=provisional.frame_count,
        graph_authority_receipt_sha256=(
            provisional.graph_authority_receipt_sha256
        ),
        grid_authority_receipt_sha256=(
            provisional.grid_authority_receipt_sha256
        ),
        operator_authority_receipt_sha256=(
            provisional.operator_authority_receipt_sha256
        ),
        edge_facts=provisional.edge_facts,
        l4_support_receipt_sha256s=(
            provisional.l4_support_receipt_sha256s
        ),
        left_capture_receipt_sha256=(
            provisional.left_capture_receipt_sha256
        ),
        right_capture_receipt_sha256=(
            provisional.right_capture_receipt_sha256
        ),
        spatially_resolved=provisional.spatially_resolved,
        diagnostic_scalar_meet_receipt_sha256=(
            provisional.diagnostic_scalar_meet_receipt_sha256
        ),
        authority_receipt_sha256=_digest(provisional.payload()),
    )
    result.verify()
    return result


def relate_trajectories(
    left: AuditoryBilateralResonanceTrajectory,
    right: AuditoryBilateralResonanceTrajectory,
) -> dict[str, object]:
    """Relate only corresponding complete edge facts with reciprocal L6."""

    left.verify()
    right.verify()
    if tuple(
        (value.left_vertex, value.right_vertex)
        for value in left.edge_facts
    ) != tuple(
        (value.left_vertex, value.right_vertex)
        for value in right.edge_facts
    ):
        raise ValueError("bilateral relation topology changed")
    matching = sum(
        left_fact.token() == right_fact.token()
        for left_fact, right_fact in zip(
            left.edge_facts,
            right.edge_facts,
            strict=True,
        )
    )
    left_l6 = canonical_l6_direction(
        dimensions=len(left.edge_facts),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    right_l6 = canonical_l6_direction(
        dimensions=len(right.edge_facts),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    payload = {
        "exact_matching_edge_fact_count": matching,
        "labels_used": False,
        "left_l6": _l6_payload(left_l6),
        "left_trajectory_receipt_sha256": (
            left.authority_receipt_sha256
        ),
        "relation_locked": left_l6.locked and right_l6.locked,
        "right_l6": _l6_payload(right_l6),
        "right_trajectory_receipt_sha256": (
            right.authority_receipt_sha256
        ),
        "scalar_meet_used": False,
        "schema": RELATION_SCHEMA,
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


def _sense_states() -> dict[PhysicalSense, SenseBoundaryState]:
    return {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SOUND
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }


def _l4_supports(
    *,
    item: CorpusItem,
    left_pcm: bytes,
    right_pcm: bytes,
) -> tuple[str, ...]:
    anchor = Fraction(item.ordinal * 4)
    inputs = (
        *binaural_sound_field_inputs(
            ear="left",
            topology_index=0,
            pcm=left_pcm,
            source_time_start=anchor,
        ),
        *binaural_sound_field_inputs(
            ear="right",
            topology_index=32,
            pcm=right_pcm,
            source_time_start=anchor,
        ),
    )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"bilateral-resonance-{item.item_id}",
        source_time_start=anchor,
        source_time_end=anchor + Fraction(
            len(left_pcm) // 2,
            REQUIRED_SAMPLE_RATE_HZ,
        ),
        observed_substreams={PhysicalSense.SOUND: inputs},
        states=_sense_states(),
    )
    built.verify_construction()
    sound = next(
        value for value in built.boundary.boundaries
        if value.sense is PhysicalSense.SOUND
    )
    result = tuple(
        value.kernel_basin.authority_receipt_sha256
        for value in sound.substreams
    )
    if len(result) != L4_SUPPORT_COUNT:
        raise ValueError("bilateral L4 support topology changed")
    return result


def _read_pcm(data: bytes) -> bytes:
    with wave.open(io.BytesIO(data), "rb") as source:
        if (
            source.getnchannels() != 1
            or source.getsampwidth() != 2
            or source.getframerate() != REQUIRED_SAMPLE_RATE_HZ
            or source.getcomptype() != "NONE"
        ):
            raise ValueError("speech corpus PCM authority changed")
        return source.readframes(source.getnframes())


def _transduce_pcm(pcm: bytes) -> AuditoryFullFieldCapture:
    return transduce_auditory_full_field(
        np.asarray(
            signed_pcm16_samples(pcm),
            dtype=np.float64,
        ) / 32_768.0,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )


def _build_corpus_trajectory(
    *,
    item: CorpusItem,
    pcm: bytes,
    authority: PhysicalStereoAuditAuthority,
) -> AuditoryBilateralResonanceTrajectory:
    physical = authority.render(
        (pcm,),
        source_ordinals=(item.ordinal % 2,),
    )
    source_digest = hashlib.sha256(pcm).hexdigest()
    left_digest = hashlib.sha256(physical.left_pcm_s16le).hexdigest()
    right_digest = hashlib.sha256(physical.right_pcm_s16le).hexdigest()
    supports = _l4_supports(
        item=item,
        left_pcm=physical.left_pcm_s16le,
        right_pcm=physical.right_pcm_s16le,
    )
    return build_trajectory(
        left_capture=_transduce_pcm(physical.left_pcm_s16le),
        right_capture=_transduce_pcm(physical.right_pcm_s16le),
        l4_support_receipt_sha256s=supports,
        source_receipt_sha256s=(
            _digest({
                "ear_pcm_sha256": left_digest,
                "physical_capture_receipt_sha256": (
                    physical.authority_receipt_sha256
                ),
                "source_pcm_sha256": source_digest,
            }),
            _digest({
                "ear_pcm_sha256": right_digest,
                "physical_capture_receipt_sha256": (
                    physical.authority_receipt_sha256
                ),
                "source_pcm_sha256": source_digest,
            }),
        ),
    )


def _evaluate(
    *,
    items: Sequence[CorpusItem],
    trajectories: Mapping[str, AuditoryBilateralResonanceTrajectory],
) -> dict[str, object]:
    matrix = tuple(
        tuple(
            relate_trajectories(
                trajectories[left.item_id],
                trajectories[right.item_id],
            )
            for right in items
        )
        for left in items
    )
    within_total = 0
    within_locked = 0
    cross_total = 0
    cross_locked = 0
    for left_index, left in enumerate(items):
        for right_index in range(left_index + 1, len(items)):
            right = items[right_index]
            locked = bool(
                matrix[left_index][right_index]["relation_locked"]
            )
            if left.oracle_command == right.oracle_command:
                within_total += 1
                within_locked += int(locked)
            else:
                cross_total += 1
                cross_locked += int(locked)
    references = {
        command: tuple(
            index for index, item in enumerate(items)
            if (
                item.oracle_command == command
                and item.split == "reference"
            )
        )
        for command in COMMANDS
    }
    held_out_total = 0
    held_out_pass = 0
    for query_index, query in enumerate(items):
        if query.split != "held_out":
            continue
        held_out_total += 1
        expected = references[query.oracle_command]
        wrong = tuple(
            index
            for command, indices in references.items()
            if command != query.oracle_command
            for index in indices
        )
        passed = (
            all(
                matrix[query_index][index]["relation_locked"]
                for index in expected
            )
            and not any(
                matrix[query_index][index]["relation_locked"]
                for index in wrong
            )
        )
        held_out_pass += int(passed)
    return {
        "cross_command_locked_pairs": cross_locked,
        "cross_command_pair_count": cross_total,
        "held_out_pass_count": held_out_pass,
        "held_out_total": held_out_total,
        "matrix": matrix,
        "within_command_locked_pairs": within_locked,
        "within_command_pair_count": within_total,
    }


def run_census(archive_path: Path) -> dict[str, object]:
    """Run the label-blind complete 64-speaker trajectory census."""

    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("speech corpus archive authority changed")
    authority = PhysicalStereoAuditAuthority(
        authority_key=AUTHORITY_KEY
    )
    with zipfile.ZipFile(archive_path) as archive:
        items = _select_corpus(archive)
        pcm_by_item = {
            item.item_id: _read_pcm(archive.read(item.archive_member))
            for item in items
        }
    trajectories = {}
    executor = start_exact_field_executor()
    executor.assert_healthy()
    try:
        for item in items:
            trajectories[item.item_id] = _build_corpus_trajectory(
                item=item,
                pcm=pcm_by_item[item.item_id],
                authority=authority,
            )
    finally:
        stop_exact_field_executor()
    evaluation = _evaluate(
        items=items,
        trajectories=trajectories,
    )
    report = {
        "archive_sha256": ARCHIVE_SHA256,
        "edge_count_per_trajectory": EDGE_COUNT,
        "evaluation": evaluation,
        "experience_count": len(trajectories),
        "labels_used_by_construction_or_relations": False,
        "l0_l4_modified": False,
        "l4_support_count_per_trajectory": L4_SUPPORT_COUNT,
        "production_modified": False,
        "reduced_relation": (
            "exact equality of corresponding certified 496-edge facts; "
            "the complete fields remain retained but do not enter this "
            "first recurrence relation"
        ),
        "relation_losses": [
            "pressure-field values do not enter edge-fact equality",
            "D/M/R/U/C/P/B values remain authenticated support rather than "
            "relation dimensions",
            "the relation requires exact equality of certified edge balls",
        ],
        "scalar_meet_used_by_relation": False,
        "schema": REPORT_SCHEMA,
        "source_disjoint_speaker_count": len({
            item.speaker_id for item in items
        }),
        "spatially_resolved_count": sum(
            value.spatially_resolved
            for value in trajectories.values()
        ),
        "trajectory_authority_root_sha256": _root(
            "guala.audit.bilateral_trajectory_authorities.v1",
            (
                value.authority_receipt_sha256
                for value in trajectories.values()
            ),
        ),
    }
    return report | {
        "authority_receipt_sha256": _digest(report),
    }


def _summary(report: Mapping[str, object]) -> dict[str, object]:
    evaluation = report["evaluation"]
    if not isinstance(evaluation, Mapping):
        raise ValueError("bilateral census evaluation changed")
    return {
        key: value
        for key, value in report.items()
        if key != "evaluation"
    } | {
        "evaluation": {
            key: value
            for key, value in evaluation.items()
            if key != "matrix"
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = run_census(args.archive)
    if args.output is not None:
        args.output.write_bytes(
            json.dumps(
                report,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            ).encode("utf-8") + b"\n"
        )
    print(json.dumps(
        _summary(report) if args.summary else report,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
