"""Bounded exact auditory peak-relation neurons before semantic grounding.

The verified receptor boundary supplies 224 independent trajectories:
sixteen cochlear receptors times pressure/phase times every explicit
D/M/R/U/C/P/B field.  The authoritative upper-pressure basin and cumulative
phase winding remain the physical receptor gate.

Within each trajectory, exact-equal runs collapse and exact local extrema
form consecutive peak-to-peak spans.  One primitive q cell records two spans
(three extrema): current direction, current/prior span-magnitude order,
current/prior same-polarity endpoint order, and current/prior duration order.
All relations are exact Fraction/integer comparisons.  They are invariant to
positive affine gain/offset and uniform positive tempo scaling.  This is an
approved nuisance quotient: it intentionally loses absolute level and
within-cell magnitude ratio.  It is never raw-experience, word, meaning, or
L6 identity.

A q cell becomes recurrent only after two physically source-disjoint
experiences.  It retains both raw exact peak witnesses, full-field tuple and
occurrence receipts, and source lineage after verbatim experience fades.
Cells are directly indexed; there is no n-gram scan, similarity score,
tolerance, fitted threshold, field merge, or scalar flattening.  Ordered and
co-firing q assemblies are formed later by causal grounding, where lived
positive and contrast consequences refine or fission meaning.
"""

from __future__ import annotations

import hashlib
import json
import threading
from contextlib import contextmanager
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from typing import Callable

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import ReceiptError, sha256_digest
from dsf_ai_service.glew_runtime.operators import ResonanceConfirmation
from dsf_ai_service.substrate.auditory_event_boundary import (
    partition_auditory_energy_basins,
)
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorFullFieldEvent,
    AuditoryVerifiedReceptorEventCapability,
    AuditoryWindingState,
)
from dsf_ai_service.substrate.auditory_receptor_resonance_graph import (
    AuditoryPhaseResonanceGraphAuthority,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    PCM_PRESSURE_QUANTUM,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    MAX_CAPTURE_SECONDS,
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)


AUDITORY_RECURRENT_MOTIF_SCHEMA = "guala.auditory.peak_relation_neuron.v2"
AUDITORY_RECURRENT_MOTIF_STATE_SCHEMA = (
    "guala.auditory.peak_relation_bank_state.v3"
)
AUDITORY_RECEPTOR_OCCURRENCE_SCHEMA = (
    "guala.auditory.receptor_occurrence.v1"
)
AUDITORY_RECEPTOR_EXPERIENCE_SCHEMA = (
    "guala.auditory.receptor_motif_experience.v1"
)
AUDITORY_FULL_FIELD_RANK_SCHEMA = (
    "guala.auditory.paired_full_field_trajectory_rank.v1"
)
AUDITORY_MOTIF_RESOURCE_PROFILE_SCHEMA = (
    "guala.auditory.motif_resource_profile.v2"
)
_IMMEDIATELY_PRIOR_RESOURCE_DERIVATION = (
    "canonical_json_worst_case_from_physical_frame_and_topology_bounds"
)
AUDITORY_RECURRENT_MOTIF_OPERATOR = (
    "exact_peak_to_peak_full_field_relation_v2"
)
AUDITORY_RECEPTOR_EXPERIENCE_COMPOSITION_OPERATOR = (
    "exact_contiguous_receptor_experience_composition_v1"
)
_VERIFIED_RECEPTOR_EXPERIENCE_AUTHORITY = object()
_VERIFIED_RANK_COMPUTATION_AUTHORITY = object()

MAX_AUDITORY_RECEPTOR_FRAMES = (
    MAX_CAPTURE_SECONDS
    * REQUIRED_SAMPLE_RATE_HZ
    // OBSERVATION_HOP_SAMPLES
)
_TEMPORAL_TRANSITION_LENGTH = 2
_EXPECTED_CHANNEL_IDS = tuple(value.name for value in AUDITORY_CHANNELS)
_HEX = frozenset("0123456789abcdef")


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


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("auditory motif values must be exact Fractions")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or "/" not in value:
        raise ValueError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name} is not an exact fraction") from exc
    if _fraction_text(result) != value:
        raise ValueError(f"{name} is not canonically encoded")
    return result


def _require_sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _require_identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
    ):
        raise ValueError(f"{name} must be a canonical identifier")
    return value


@dataclass(frozen=True, slots=True, order=True)
class AuditoryReceptorIdentity:
    cochlear_index: int
    channel_id: str
    winding_direction: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.cochlear_index, bool)
            or not isinstance(self.cochlear_index, int)
            or not 0 <= self.cochlear_index < COCHLEAR_CHANNEL_COUNT
            or self.channel_id != _EXPECTED_CHANNEL_IDS[self.cochlear_index]
            or self.winding_direction not in (-1, 1)
        ):
            raise ValueError("auditory receptor identity left physical topology")

    def payload(self) -> dict[str, object]:
        return {
            "channel_id": self.channel_id,
            "cochlear_index": self.cochlear_index,
            "winding_direction": self.winding_direction,
        }


AuditoryReceptorState = tuple[AuditoryReceptorIdentity, ...]
AuditoryReceptorChain = tuple[AuditoryReceptorState, ...]


def _chain_payload(
    chain: AuditoryReceptorChain,
) -> list[list[dict[str, object]]]:
    return [
        [receptor.payload() for receptor in state]
        for state in chain
    ]


def _chain_from_payload(
    value: object,
    *,
    minimum_length: int = _TEMPORAL_TRANSITION_LENGTH,
) -> AuditoryReceptorChain:
    if not isinstance(value, list):
        raise ValueError("auditory motif chain is not an array")
    states: list[AuditoryReceptorState] = []
    for raw_state in value:
        if not isinstance(raw_state, list):
            raise ValueError("auditory motif receptor state is not an array")
        receptors: list[AuditoryReceptorIdentity] = []
        for raw_receptor in raw_state:
            if not isinstance(raw_receptor, dict):
                raise ValueError("auditory motif receptor is not typed")
            receptors.append(AuditoryReceptorIdentity(
                cochlear_index=raw_receptor.get("cochlear_index"),
                channel_id=raw_receptor.get("channel_id"),
                winding_direction=raw_receptor.get("winding_direction"),
            ))
        state = tuple(receptors)
        if not state or tuple(sorted(set(state))) != state:
            raise ValueError("auditory motif receptor state changed")
        states.append(state)
    chain = tuple(states)
    if not minimum_length <= len(chain) <= MAX_AUDITORY_RECEPTOR_FRAMES:
        raise ValueError("auditory motif chain is not a bounded transition")
    return chain


def _max_serialized_state_bytes() -> int:
    receptor_size = max(
        len(_canonical_bytes(AuditoryReceptorIdentity(
            cochlear_index=index,
            channel_id=channel_id,
            winding_direction=-1,
        ).payload()))
        for index, channel_id in enumerate(_EXPECTED_CHANNEL_IDS)
    )
    return (
        2
        + COCHLEAR_CHANNEL_COUNT * receptor_size
        + (COCHLEAR_CHANNEL_COUNT - 1)
    )


def _derived_worst_case_encoded_bytes(
    *,
    ear_count: int,
    max_motif_neurons: int,
    max_pending_experiences: int,
    max_exact_fraction_text_bytes: int,
) -> int:
    """Conservative canonical-byte bound for the two-ear physical q bank."""

    relation_cells = ear_count * COCHLEAR_CHANNEL_COUNT * 2 * len(
        DSF_FIELD_ORDER
    ) * (2 * 3 * 3 * 3)
    recurrent_cells = min(relation_cells, max_motif_neurons)
    primed_cells = min(
        relation_cells,
        relation_cells * max_pending_experiences,
    )
    point_bytes = (
        2 * max_exact_fraction_text_bytes
        + 2 * 64
        + 512
    )
    witness_bytes = (
        3 * point_bytes
        + 16 * 67
        + 2_048
    )
    recurrent_cell_bytes = 2 * witness_bytes + 4_096
    primed_cell_bytes = witness_bytes + 2_048
    bounded_history_bytes = relation_cells * (2 * 67 + 128)
    envelope_bytes = 1_048_576
    return (
        recurrent_cells * recurrent_cell_bytes
        + primed_cells * primed_cell_bytes
        + bounded_history_bytes
        + envelope_bytes
    )


def _immediately_prior_worst_case_encoded_bytes(
    *,
    ear_count: int,
    max_exact_fraction_text_bytes: int,
) -> int:
    """Reproduce only the immediately prior undercounted profile receipt."""

    relation_cells = ear_count * COCHLEAR_CHANNEL_COUNT * 2 * len(
        DSF_FIELD_ORDER
    ) * (2 * 3 * 3 * 3)
    point_bytes = (
        2 * max_exact_fraction_text_bytes
        + 2 * 64
        + 512
    )
    witness_bytes = (
        3 * point_bytes
        + 16 * 67
        + 2_048
    )
    recurrent_cell_bytes = 2 * witness_bytes + 4_096
    bounded_history_bytes = relation_cells * (2 * 67 + 128)
    return (
        relation_cells * recurrent_cell_bytes
        + bounded_history_bytes
        + 1_048_576
    )


@dataclass(frozen=True, slots=True)
class AuditoryMotifResourceProfile:
    profile_id: str
    ear_count: int
    max_motif_neurons: int
    max_pending_experiences: int
    max_work_cells_per_observation: int
    max_exact_fraction_text_bytes: int
    max_encoded_state_bytes: int
    encoded_state_allocation_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        ear_count: int = 1,
        max_motif_neurons: int,
        max_pending_experiences: int,
        max_work_cells_per_observation: int,
        max_exact_fraction_text_bytes: int,
        encoded_state_allocation_bytes: int | None = None,
    ) -> "AuditoryMotifResourceProfile":
        for value, name in (
            (ear_count, "ear count"),
            (max_motif_neurons, "motif neurons"),
            (max_pending_experiences, "pending experiences"),
            (max_work_cells_per_observation, "work cells"),
            (max_exact_fraction_text_bytes, "exact fraction text bytes"),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(f"auditory motif {name} must be positive")
        if ear_count not in (1, 2):
            raise ValueError("auditory motif profile supports one or two ears")
        exact_cells = AUDITORY_PEAK_RELATION_CELL_COUNT * ear_count
        if max_motif_neurons != exact_cells:
            raise ValueError(
                "auditory motif neuron authority must equal physical q cells"
            )
        encoded = _derived_worst_case_encoded_bytes(
            ear_count=ear_count,
            max_motif_neurons=max_motif_neurons,
            max_pending_experiences=max_pending_experiences,
            max_exact_fraction_text_bytes=max_exact_fraction_text_bytes,
        )
        allocation = (
            encoded
            if encoded_state_allocation_bytes is None
            else encoded_state_allocation_bytes
        )
        if (
            isinstance(allocation, bool)
            or not isinstance(allocation, int)
            or not 0 < allocation <= encoded
        ):
            raise ValueError(
                "auditory motif encoded-state allocation must be positive "
                "and no larger than its derived worst-case bound"
            )
        provisional = cls(
            profile_id=_require_identifier(profile_id, "resource profile"),
            ear_count=ear_count,
            max_motif_neurons=max_motif_neurons,
            max_pending_experiences=max_pending_experiences,
            max_work_cells_per_observation=max_work_cells_per_observation,
            max_exact_fraction_text_bytes=max_exact_fraction_text_bytes,
            max_encoded_state_bytes=encoded,
            encoded_state_allocation_bytes=allocation,
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            ear_count=provisional.ear_count,
            max_motif_neurons=provisional.max_motif_neurons,
            max_pending_experiences=provisional.max_pending_experiences,
            max_work_cells_per_observation=(
                provisional.max_work_cells_per_observation
            ),
            max_exact_fraction_text_bytes=(
                provisional.max_exact_fraction_text_bytes
            ),
            max_encoded_state_bytes=provisional.max_encoded_state_bytes,
            encoded_state_allocation_bytes=(
                provisional.encoded_state_allocation_bytes
            ),
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "derivation": (
                "canonical_json_worst_case_from_physical_frame_topology_"
                "and_pending_cohort_bounds_v2"
            ),
            "max_encoded_state_bytes": self.max_encoded_state_bytes,
            "encoded_state_allocation_bytes": (
                self.encoded_state_allocation_bytes
            ),
            "ear_count": self.ear_count,
            "max_motif_neurons": self.max_motif_neurons,
            "max_pending_experiences": self.max_pending_experiences,
            "max_exact_fraction_text_bytes": (
                self.max_exact_fraction_text_bytes
            ),
            "max_work_cells_per_observation": (
                self.max_work_cells_per_observation
            ),
            "physical_frame_bound": MAX_AUDITORY_RECEPTOR_FRAMES,
            "profile_id": self.profile_id,
            "schema": AUDITORY_MOTIF_RESOURCE_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _require_identifier(self.profile_id, "resource profile")
        for value, name in (
            (self.ear_count, "ear count"),
            (self.max_motif_neurons, "motif neurons"),
            (self.max_pending_experiences, "pending experiences"),
            (self.max_work_cells_per_observation, "work cells"),
            (
                self.max_exact_fraction_text_bytes,
                "exact fraction text bytes",
            ),
            (self.max_encoded_state_bytes, "encoded state"),
            (
                self.encoded_state_allocation_bytes,
                "encoded state allocation",
            ),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(f"auditory motif {name} must be positive")
        if (
            self.ear_count not in (1, 2)
            or self.max_motif_neurons
            != AUDITORY_PEAK_RELATION_CELL_COUNT * self.ear_count
        ):
            raise ValueError("auditory motif profile topology changed")
        expected_bytes = _derived_worst_case_encoded_bytes(
            ear_count=self.ear_count,
            max_motif_neurons=self.max_motif_neurons,
            max_pending_experiences=self.max_pending_experiences,
            max_exact_fraction_text_bytes=(
                self.max_exact_fraction_text_bytes
            ),
        )
        if self.max_encoded_state_bytes != expected_bytes:
            raise ValueError("auditory motif encoded-state derivation changed")
        if self.encoded_state_allocation_bytes > expected_bytes:
            raise ValueError(
                "auditory motif encoded-state allocation exceeds derivation"
            )
        _require_sha256(
            self.authority_receipt_sha256,
            "auditory motif resource profile",
        )
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError("auditory motif resource profile receipt changed")


def _exact_rank_provenance(
    rows: tuple[tuple[Fraction, ...], ...],
) -> tuple[int, tuple[int, ...], int]:
    field_count = len(DSF_FIELD_ORDER)
    basis: list[tuple[int, list[Fraction]]] = []
    first_ordinal_by_rank: dict[int, int] = {}
    for ordinal, source_row in enumerate(rows, start=1):
        if len(source_row) != field_count:
            raise ValueError("auditory exact-rank row width changed")
        row = list(source_row)
        for pivot_column, basis_row in basis:
            factor = row[pivot_column]
            if factor:
                row = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(
                        row,
                        basis_row,
                        strict=True,
                    )
                ]
        pivot_column = next(
            (
                column
                for column, value in enumerate(row)
                if value
            ),
            None,
        )
        if pivot_column is None:
            continue
        pivot = row[pivot_column]
        row = [value / pivot for value in row]
        updated_basis = []
        for existing_pivot, basis_row in basis:
            factor = basis_row[pivot_column]
            if factor:
                basis_row = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(
                        basis_row,
                        row,
                        strict=True,
                    )
                ]
            updated_basis.append((existing_pivot, basis_row))
        updated_basis.append((pivot_column, row))
        basis = sorted(updated_basis, key=lambda value: value[0])
        first_ordinal_by_rank.setdefault(len(basis), ordinal)
        if len(basis) == field_count:
            break
    pivots = tuple(value[0] for value in basis)
    rank = len(pivots)
    return (
        rank,
        pivots,
        0 if rank == 0 else first_ordinal_by_rank[rank],
    )


def _exact_rank(
    rows: tuple[tuple[Fraction, ...], ...],
) -> tuple[int, tuple[int, ...]]:
    rank, pivots, _first_terminal_ordinal = (
        _exact_rank_provenance(rows)
    )
    return rank, pivots


@dataclass(frozen=True, slots=True)
class AuditoryReceptorOccurrence:
    receptor: AuditoryReceptorIdentity
    source_index: int
    source_time: Fraction
    causal_interval_end: Fraction
    winding_delta: int
    pressure_fields: tuple[tuple[str, Fraction], ...]
    phase_fields: tuple[tuple[str, Fraction], ...]
    pressure_field_receipt_sha256: str
    phase_field_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "phase_field_receipt_sha256": self.phase_field_receipt_sha256,
            "phase_fields": [
                [name, _fraction_text(value)]
                for name, value in self.phase_fields
            ],
            "pressure_basin": "authoritative_upper",
            "pressure_field_receipt_sha256": (
                self.pressure_field_receipt_sha256
            ),
            "pressure_fields": [
                [name, _fraction_text(value)]
                for name, value in self.pressure_fields
            ],
            "receptor": self.receptor.payload(),
            "schema": AUDITORY_RECEPTOR_OCCURRENCE_SCHEMA,
            "source_index": self.source_index,
            "source_time": _fraction_text(self.source_time),
            "causal_interval_end": _fraction_text(
                self.causal_interval_end
            ),
            "winding_delta": self.winding_delta,
        }

    def verify(self) -> None:
        self.receptor.__post_init__()
        if (
            isinstance(self.source_index, bool)
            or not isinstance(self.source_index, int)
            or self.source_index < 0
            or not isinstance(self.source_time, Fraction)
            or not isinstance(self.causal_interval_end, Fraction)
            or self.causal_interval_end <= self.source_time
            or isinstance(self.winding_delta, bool)
            or not isinstance(self.winding_delta, int)
            or self.winding_delta == 0
            or (1 if self.winding_delta > 0 else -1)
            != self.receptor.winding_direction
        ):
            raise ValueError("auditory receptor occurrence changed")
        for fields in (self.pressure_fields, self.phase_fields):
            if (
                tuple(name for name, _value in fields) != DSF_FIELD_ORDER
                or any(
                    not isinstance(value, Fraction)
                    for _name, value in fields
                )
            ):
                raise ValueError("auditory receptor occurrence flattened DSF")
        _require_sha256(
            self.pressure_field_receipt_sha256,
            "pressure field authority",
        )
        _require_sha256(
            self.phase_field_receipt_sha256,
            "phase field authority",
        )
        _require_sha256(
            self.authority_receipt_sha256,
            "receptor occurrence authority",
        )
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError("auditory receptor occurrence receipt changed")


@dataclass(frozen=True, slots=True)
class ExactComponentTrajectoryRankProof:
    component_id: str
    component_kind: str
    event_count: int
    rank: int
    pivot_fields: tuple[str, ...]
    first_terminal_rank_event_ordinal: int
    source_field_receipt_sha256s: tuple[str, ...]
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "component_kind": self.component_kind,
            "event_count": self.event_count,
            "field_order": list(DSF_FIELD_ORDER),
            "first_terminal_rank_event_ordinal": (
                self.first_terminal_rank_event_ordinal
            ),
            "operator": "exact_fraction_gaussian_elimination_v1",
            "pivot_fields": list(self.pivot_fields),
            "rank": self.rank,
            "schema": AUDITORY_FULL_FIELD_RANK_SCHEMA,
            "source_field_receipt_sha256s": list(
                self.source_field_receipt_sha256s
            ),
        }

    def verify(
        self,
        rows: tuple[tuple[Fraction, ...], ...],
        source_receipts: tuple[str, ...],
    ) -> None:
        _require_identifier(self.component_id, "rank component")
        if (
            self.component_kind not in ("pressure", "phase")
            or self.event_count != len(rows)
            or self.source_field_receipt_sha256s != source_receipts
        ):
            raise ValueError("auditory component rank proof changed")
        exact_rank, pivots, first = _exact_rank_provenance(rows)
        if (
            self.rank != exact_rank
            or self.pivot_fields
            != tuple(DSF_FIELD_ORDER[index] for index in pivots)
        ):
            raise ValueError("auditory component rank result changed")
        if self.first_terminal_rank_event_ordinal != first:
            raise ValueError("auditory component first terminal rank changed")
        _require_sha256(
            self.authority_receipt_sha256,
            "component rank authority",
        )
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError("auditory component rank receipt changed")


@dataclass(frozen=True, slots=True)
class _VerifiedRankComputationCapability:
    proof: ExactComponentTrajectoryRankProof
    channel_occurrences: tuple[AuditoryReceptorOccurrence, ...]
    component_kind: str
    rows: tuple[tuple[Fraction, ...], ...]
    source_receipts: tuple[str, ...]
    _construction_authority: object

    def verify_linkage(
        self,
        *,
        proof: ExactComponentTrajectoryRankProof,
        channel_occurrences: tuple[AuditoryReceptorOccurrence, ...],
        component_kind: str,
        rows: tuple[tuple[Fraction, ...], ...],
        source_receipts: tuple[str, ...],
    ) -> None:
        if (
            self._construction_authority
            is not _VERIFIED_RANK_COMPUTATION_AUTHORITY
            or self.proof is not proof
            or self.channel_occurrences is not channel_occurrences
            or self.component_kind != component_kind
            or self.rows != rows
            or self.source_receipts != source_receipts
            or proof.event_count != len(rows)
            or proof.source_field_receipt_sha256s != source_receipts
            or _digest(proof.payload()) != proof.authority_receipt_sha256
        ):
            raise ValueError(
                "auditory rank computation left verified custody"
            )


def _rank_proof(
    *,
    component_id: str,
    component_kind: str,
    rows: tuple[tuple[Fraction, ...], ...],
    source_receipts: tuple[str, ...],
    channel_occurrences: tuple[AuditoryReceptorOccurrence, ...],
) -> tuple[
    ExactComponentTrajectoryRankProof,
    _VerifiedRankComputationCapability,
]:
    rank, pivots, first = _exact_rank_provenance(rows)
    provisional = ExactComponentTrajectoryRankProof(
        component_id=component_id,
        component_kind=component_kind,
        event_count=len(rows),
        rank=rank,
        pivot_fields=tuple(DSF_FIELD_ORDER[index] for index in pivots),
        first_terminal_rank_event_ordinal=first,
        source_field_receipt_sha256s=source_receipts,
        authority_receipt_sha256="0" * 64,
    )
    result = ExactComponentTrajectoryRankProof(
        component_id=provisional.component_id,
        component_kind=provisional.component_kind,
        event_count=provisional.event_count,
        rank=provisional.rank,
        pivot_fields=provisional.pivot_fields,
        first_terminal_rank_event_ordinal=(
            provisional.first_terminal_rank_event_ordinal
        ),
        source_field_receipt_sha256s=(
            provisional.source_field_receipt_sha256s
        ),
        authority_receipt_sha256=_digest(provisional.payload()),
    )
    return result, _VerifiedRankComputationCapability(
        proof=result,
        channel_occurrences=channel_occurrences,
        component_kind=component_kind,
        rows=rows,
        source_receipts=source_receipts,
        _construction_authority=_VERIFIED_RANK_COMPUTATION_AUTHORITY,
    )


@dataclass(frozen=True, slots=True)
class AuditoryReceptorExperience:
    source_event_receipt_sha256: str
    source_event_receipt_sha256s: tuple[str, ...]
    source_continuity_receipt_sha256s: tuple[str, ...]
    source_frame_count: int
    occurrences: tuple[AuditoryReceptorOccurrence, ...]
    causal_segments: tuple[AuditoryReceptorChain, ...]
    causal_segment_source_indices: tuple[tuple[int, ...], ...]
    unresolved_source_indices: tuple[int, ...]
    component_rank_proofs: tuple[ExactComponentTrajectoryRankProof, ...]
    resonance_graph_authority_receipt_sha256: str | None
    resonance_operator_authority_receipt_sha256: str | None
    resonance_result_receipt_sha256: str | None
    authority_receipt_sha256: str

    @property
    def resonance_mount_state(self) -> str:
        if self.resonance_operator_authority_receipt_sha256 is not None:
            return "graph_and_result_mounted"
        if self.resonance_graph_authority_receipt_sha256 is not None:
            return "graph_mounted_result_unresolved"
        return "not_mounted_no_claim"

    def payload(self) -> dict[str, object]:
        return {
            "causal_segments": [
                _chain_payload(segment) for segment in self.causal_segments
            ],
            "causal_segment_source_indices": [
                list(indices)
                for indices in self.causal_segment_source_indices
            ],
            "component_rank_receipts": [
                proof.authority_receipt_sha256
                for proof in self.component_rank_proofs
            ],
            "occurrence_receipts": [
                occurrence.authority_receipt_sha256
                for occurrence in self.occurrences
            ],
            "resonance_graph_authority_receipt_sha256": (
                self.resonance_graph_authority_receipt_sha256
            ),
            "resonance_mount_state": self.resonance_mount_state,
            "resonance_operator_authority_receipt_sha256": (
                self.resonance_operator_authority_receipt_sha256
            ),
            "resonance_result_receipt_sha256": (
                self.resonance_result_receipt_sha256
            ),
            "schema": AUDITORY_RECEPTOR_EXPERIENCE_SCHEMA,
            "source_event_receipt_sha256": self.source_event_receipt_sha256,
            "source_event_receipt_sha256s": list(
                self.source_event_receipt_sha256s
            ),
            "source_continuity_receipt_sha256s": list(
                self.source_continuity_receipt_sha256s
            ),
            "source_frame_count": self.source_frame_count,
            "unresolved_source_indices": list(
                self.unresolved_source_indices
            ),
        }

    def verify(
        self,
        *,
        _rank_capabilities: (
            tuple[_VerifiedRankComputationCapability, ...] | None
        ) = None,
        _constructed_occurrences_by_channel: (
            tuple[tuple[AuditoryReceptorOccurrence, ...], ...] | None
        ) = None,
    ) -> None:
        _require_sha256(
            self.source_event_receipt_sha256,
            "source receptor event",
        )
        if (
            not isinstance(self.source_event_receipt_sha256s, tuple)
            or not self.source_event_receipt_sha256s
            or any(
                _require_sha256(value, "source receptor event lineage")
                is not value
                for value in self.source_event_receipt_sha256s
            )
            or not isinstance(
                self.source_continuity_receipt_sha256s,
                tuple,
            )
            or any(
                _require_sha256(value, "source continuity authority")
                is not value
                for value in self.source_continuity_receipt_sha256s
            )
            or isinstance(self.source_frame_count, bool)
            or not isinstance(self.source_frame_count, int)
            or not 0 < self.source_frame_count <= MAX_AUDITORY_RECEPTOR_FRAMES
        ):
            raise ValueError("auditory receptor source lineage changed")
        if self.source_continuity_receipt_sha256s:
            expected_source = _digest({
                "operator": (
                    AUDITORY_RECEPTOR_EXPERIENCE_COMPOSITION_OPERATOR
                ),
                "source_continuity_receipt_sha256s": list(
                    self.source_continuity_receipt_sha256s
                ),
                "source_event_receipt_sha256s": list(
                    self.source_event_receipt_sha256s
                ),
                "source_frame_count": self.source_frame_count,
            })
        elif len(self.source_event_receipt_sha256s) == 1:
            expected_source = self.source_event_receipt_sha256s[0]
        else:
            raise ValueError(
                "composed auditory receptor source lacks continuity authority"
            )
        if self.source_event_receipt_sha256 != expected_source:
            raise ValueError("auditory receptor source authority changed")
        if (
            not isinstance(self.occurrences, tuple)
            or not isinstance(self.causal_segments, tuple)
            or not isinstance(self.causal_segment_source_indices, tuple)
            or len(self.causal_segment_source_indices)
            != len(self.causal_segments)
            or not isinstance(self.unresolved_source_indices, tuple)
            or tuple(sorted(set(self.unresolved_source_indices)))
            != self.unresolved_source_indices
            or any(
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < MAX_AUDITORY_RECEPTOR_FRAMES
                or index >= self.source_frame_count
                for index in self.unresolved_source_indices
            )
            or len(self.component_rank_proofs)
            != COCHLEAR_CHANNEL_COUNT * 2
        ):
            raise ValueError("auditory receptor experience changed")
        for occurrence in self.occurrences:
            occurrence.verify()
            if occurrence.source_index >= self.source_frame_count:
                raise ValueError(
                    "auditory receptor occurrence left source interval"
                )
        for segment, source_indices in zip(
            self.causal_segments,
            self.causal_segment_source_indices,
            strict=True,
        ):
            if not segment or len(segment) > MAX_AUDITORY_RECEPTOR_FRAMES:
                raise ValueError("auditory receptor causal segment changed")
            if (
                len(source_indices) != len(segment)
                or any(
                    isinstance(index, bool)
                    or not isinstance(index, int)
                    or not 0 <= index < self.source_frame_count
                    for index in source_indices
                )
                or any(
                    right <= left
                    for left, right in zip(
                        source_indices,
                        source_indices[1:],
                    )
                )
                or set(source_indices).intersection(
                    self.unresolved_source_indices
                )
            ):
                raise ValueError(
                    "auditory receptor causal source support changed"
                )
            for state in segment:
                if not state or tuple(sorted(set(state))) != state:
                    raise ValueError("auditory receptor co-firing state changed")
                for receptor in state:
                    receptor.__post_init__()
        if (
            (_rank_capabilities is None)
            != (_constructed_occurrences_by_channel is None)
        ):
            raise ValueError(
                "auditory constructed rank custody is incomplete"
            )
        if _rank_capabilities is None:
            occurrences_by_channel = _occurrences_by_channel(
                self.occurrences
            )
        else:
            if (
                len(_rank_capabilities)
                != COCHLEAR_CHANNEL_COUNT * 2
                or len(_constructed_occurrences_by_channel)
                != COCHLEAR_CHANNEL_COUNT
                or _occurrences_by_channel(self.occurrences)
                != _constructed_occurrences_by_channel
            ):
                raise ValueError(
                    "auditory constructed occurrence custody changed"
                )
            occurrences_by_channel = (
                _constructed_occurrences_by_channel
            )
        for index, channel_id in enumerate(_EXPECTED_CHANNEL_IDS):
            channel_occurrences = occurrences_by_channel[index]
            for offset, kind in enumerate(("pressure", "phase")):
                proof = self.component_rank_proofs[index * 2 + offset]
                fields = tuple(
                    tuple(
                        value for _name, value in (
                            occurrence.pressure_fields
                            if kind == "pressure"
                            else occurrence.phase_fields
                        )
                    )
                    for occurrence in channel_occurrences
                )
                receipts = tuple(
                    occurrence.pressure_field_receipt_sha256
                    if kind == "pressure"
                    else occurrence.phase_field_receipt_sha256
                    for occurrence in channel_occurrences
                )
                if (
                    proof.component_id != f"{channel_id}_{kind}"
                    or proof.component_kind != kind
                ):
                    raise ValueError("auditory component rank topology changed")
                if _rank_capabilities is None:
                    proof.verify(fields, receipts)
                else:
                    _rank_capabilities[
                        index * 2 + offset
                    ].verify_linkage(
                        proof=proof,
                        channel_occurrences=channel_occurrences,
                        component_kind=kind,
                        rows=fields,
                        source_receipts=receipts,
                    )
        if self.resonance_graph_authority_receipt_sha256 is not None:
            _require_sha256(
                self.resonance_graph_authority_receipt_sha256,
                "resonance graph authority",
            )
        if self.resonance_operator_authority_receipt_sha256 is not None:
            _require_sha256(
                self.resonance_operator_authority_receipt_sha256,
                "resonance operator authority",
            )
            if self.resonance_graph_authority_receipt_sha256 is None:
                raise ValueError("resonance result lacks graph authority")
            _require_sha256(
                self.resonance_result_receipt_sha256,
                "resonance result",
            )
        elif self.resonance_result_receipt_sha256 is not None:
            raise ValueError("resonance result lacks operator authority")
        _require_sha256(
            self.authority_receipt_sha256,
            "auditory receptor experience",
        )
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError("auditory receptor experience receipt changed")


@dataclass(frozen=True, slots=True)
class AuditoryVerifiedReceptorExperienceCapability:
    """Child/request-local identity for one deeply verified experience."""

    experience: AuditoryReceptorExperience
    _construction_authority: object

    def verify_identity(
        self,
        experience: AuditoryReceptorExperience,
    ) -> None:
        if (
            self._construction_authority
            is not _VERIFIED_RECEPTOR_EXPERIENCE_AUTHORITY
            or self.experience is not experience
        ):
            raise ValueError(
                "auditory receptor experience left verified custody"
            )


def verify_receptor_experience_custody(
    experience: AuditoryReceptorExperience,
) -> AuditoryVerifiedReceptorExperienceCapability:
    if not isinstance(experience, AuditoryReceptorExperience):
        raise TypeError("auditory receptor experience is not typed")
    experience.verify()
    return AuditoryVerifiedReceptorExperienceCapability(
        experience=experience,
        _construction_authority=(
            _VERIFIED_RECEPTOR_EXPERIENCE_AUTHORITY
        ),
    )


def _verified_receptor_experience_custody(
    experience: AuditoryReceptorExperience,
) -> AuditoryVerifiedReceptorExperienceCapability:
    return AuditoryVerifiedReceptorExperienceCapability(
        experience=experience,
        _construction_authority=(
            _VERIFIED_RECEPTOR_EXPERIENCE_AUTHORITY
        ),
    )


def _occurrences_by_channel(
    occurrences: tuple[AuditoryReceptorOccurrence, ...],
) -> tuple[tuple[AuditoryReceptorOccurrence, ...], ...]:
    grouped: list[list[AuditoryReceptorOccurrence]] = [
        [] for _channel_id in _EXPECTED_CHANNEL_IDS
    ]
    for occurrence in occurrences:
        grouped[occurrence.receptor.cochlear_index].append(occurrence)
    return tuple(tuple(values) for values in grouped)


def _authoritative_upper_basin(
    pressure: tuple[Fraction, ...],
) -> tuple[int, ...] | None:
    try:
        partition = partition_auditory_energy_basins(
            tuple((float(value),) for value in pressure),
            pressure_uncertainty_full_scale=float(PCM_PRESSURE_QUANTUM),
        )
    except ValueError:
        return None
    return partition.upper_indices


def receptor_experience_from_full_field_event(
    event: AuditoryReceptorFullFieldEvent,
    *,
    verified_capability: (
        AuditoryVerifiedReceptorEventCapability | None
    ) = None,
    resonance_graph: AuditoryPhaseResonanceGraphAuthority | None = None,
    resonance_confirmation: ResonanceConfirmation | None = None,
) -> AuditoryReceptorExperience:
    """Consume one verified receptor boundary without reconstructing L5."""

    if not isinstance(event, AuditoryReceptorFullFieldEvent):
        raise TypeError("auditory motif intake requires receptor full-field event")
    if verified_capability is None:
        event.verify()
    else:
        verified_capability.verify_identity(event)
    if resonance_graph is not None:
        if not isinstance(
            resonance_graph,
            AuditoryPhaseResonanceGraphAuthority,
        ):
            raise TypeError("auditory motif resonance graph is not typed")
        resonance_graph.verify()
    if resonance_confirmation is not None:
        if (
            not isinstance(resonance_confirmation, ResonanceConfirmation)
            or resonance_graph is None
            or resonance_confirmation.graph_authority_receipt_sha256
            != resonance_graph.graph.authority_receipt_sha256
            or resonance_confirmation.required_edges
            != resonance_graph.graph.required_edges
        ):
            raise ReceiptError(
                "auditory motif resonance result lacks its mounted graph"
            )

    occurrences: list[AuditoryReceptorOccurrence] = []
    unresolved: list[int] = []
    segments: list[AuditoryReceptorChain] = []
    current_segment: list[AuditoryReceptorState] = []
    segment_source_indices: list[tuple[int, ...]] = []
    current_source_indices: list[int] = []
    for source_index in range(event.frame_count):
        frames = tuple(
            channel.frames[source_index] for channel in event.channels
        )
        if any(
            frame.winding_state is not AuditoryWindingState.SETTLED
            or frame.winding_delta is None
            for frame in frames
        ) or event.frame_count == 1:
            unresolved.append(source_index)
            if current_segment:
                segments.append(tuple(current_segment))
                segment_source_indices.append(
                    tuple(current_source_indices)
                )
                current_segment = []
                current_source_indices = []
            continue
        upper = _authoritative_upper_basin(tuple(
            frame.pressure_amplitude for frame in frames
        ))
        if upper is None:
            unresolved.append(source_index)
            if current_segment:
                segments.append(tuple(current_segment))
                segment_source_indices.append(
                    tuple(current_source_indices)
                )
                current_segment = []
                current_source_indices = []
            continue
        receptors: list[AuditoryReceptorIdentity] = []
        for channel_index in upper:
            channel = event.channels[channel_index]
            frame = frames[channel_index]
            if frame.winding_delta == 0:
                continue
            receptor = AuditoryReceptorIdentity(
                cochlear_index=channel_index,
                channel_id=channel.channel_id,
                winding_direction=(
                    1 if frame.winding_delta > 0 else -1
                ),
            )
            pressure_field = channel.pressure_fields[
                frame.pressure_field_tuple_index
            ]
            phase_field = channel.phase_fields[
                frame.phase_field_tuple_index
            ]
            provisional = AuditoryReceptorOccurrence(
                receptor=receptor,
                source_index=source_index,
                source_time=frame.source_time,
                causal_interval_end=(
                    event.channels[channel_index].frames[
                        source_index + 1
                    ].source_time
                    if source_index + 1 < event.frame_count
                    else frame.source_time
                    + (
                        frame.source_time
                        - event.channels[channel_index].frames[
                            source_index - 1
                        ].source_time
                    )
                ),
                winding_delta=frame.winding_delta,
                pressure_fields=pressure_field.fields,
                phase_fields=phase_field.fields,
                pressure_field_receipt_sha256=(
                    pressure_field.authority_receipt_sha256
                ),
                phase_field_receipt_sha256=(
                    phase_field.authority_receipt_sha256
                ),
                authority_receipt_sha256="0" * 64,
            )
            occurrence = AuditoryReceptorOccurrence(
                receptor=provisional.receptor,
                source_index=provisional.source_index,
                source_time=provisional.source_time,
                causal_interval_end=provisional.causal_interval_end,
                winding_delta=provisional.winding_delta,
                pressure_fields=provisional.pressure_fields,
                phase_fields=provisional.phase_fields,
                pressure_field_receipt_sha256=(
                    provisional.pressure_field_receipt_sha256
                ),
                phase_field_receipt_sha256=(
                    provisional.phase_field_receipt_sha256
                ),
                authority_receipt_sha256=_digest(provisional.payload()),
            )
            occurrences.append(occurrence)
            receptors.append(receptor)
        if receptors:
            state = tuple(sorted(set(receptors)))
            if not current_segment or current_segment[-1] != state:
                current_segment.append(state)
                current_source_indices.append(source_index)
    if current_segment:
        segments.append(tuple(current_segment))
        segment_source_indices.append(tuple(current_source_indices))

    ordered_occurrences = tuple(occurrences)
    occurrences_by_channel = _occurrences_by_channel(
        ordered_occurrences
    )
    proofs: list[ExactComponentTrajectoryRankProof] = []
    rank_capabilities: list[_VerifiedRankComputationCapability] = []
    for channel_index, channel_id in enumerate(_EXPECTED_CHANNEL_IDS):
        channel_occurrences = occurrences_by_channel[channel_index]
        for kind in ("pressure", "phase"):
            rows = tuple(
                tuple(
                    value for _name, value in (
                        occurrence.pressure_fields
                        if kind == "pressure"
                        else occurrence.phase_fields
                    )
                )
                for occurrence in channel_occurrences
            )
            source_receipts = tuple(
                occurrence.pressure_field_receipt_sha256
                if kind == "pressure"
                else occurrence.phase_field_receipt_sha256
                for occurrence in channel_occurrences
            )
            proof, rank_capability = _rank_proof(
                component_id=f"{channel_id}_{kind}",
                component_kind=kind,
                rows=rows,
                source_receipts=source_receipts,
                channel_occurrences=channel_occurrences,
            )
            proofs.append(proof)
            rank_capabilities.append(rank_capability)
    graph_receipt = (
        None
        if resonance_graph is None
        else resonance_graph.graph.authority_receipt_sha256
    )
    operator_receipt = (
        None
        if resonance_confirmation is None
        else resonance_confirmation.operator_authority_receipt_sha256
    )
    result_receipt = (
        None
        if resonance_confirmation is None
        else _digest({
            "edge_facts": [
                {
                    "gamma_squared": {
                        "lower_exponent": edge.gamma_squared.lower_exponent,
                        "lower_mantissa": edge.gamma_squared.lower_mantissa,
                        "upper_exponent": edge.gamma_squared.upper_exponent,
                        "upper_mantissa": edge.gamma_squared.upper_mantissa,
                        "working_precision_bits": (
                            edge.gamma_squared.working_precision_bits
                        ),
                    },
                    "left_port_key": list(edge.edge.left_port_key),
                    "proved_zero_energy": edge.proved_zero_energy,
                    "right_port_key": list(edge.edge.right_port_key),
                }
                for edge in resonance_confirmation.edge_facts
            ],
            "graph_authority_receipt_sha256": (
                resonance_confirmation.graph_authority_receipt_sha256
            ),
            "grid_id": resonance_confirmation.grid_id,
            "operator_authority_receipt_sha256": (
                resonance_confirmation.operator_authority_receipt_sha256
            ),
            "value": {
                "lower_exponent": resonance_confirmation.value.lower_exponent,
                "lower_mantissa": resonance_confirmation.value.lower_mantissa,
                "upper_exponent": resonance_confirmation.value.upper_exponent,
                "upper_mantissa": resonance_confirmation.value.upper_mantissa,
                "working_precision_bits": (
                    resonance_confirmation.value.working_precision_bits
                ),
            },
        })
    )
    provisional_experience = AuditoryReceptorExperience(
        source_event_receipt_sha256=event.authority_receipt_sha256,
        source_event_receipt_sha256s=(
            event.authority_receipt_sha256,
        ),
        source_continuity_receipt_sha256s=(),
        source_frame_count=event.frame_count,
        occurrences=ordered_occurrences,
        causal_segments=tuple(segments),
        causal_segment_source_indices=tuple(segment_source_indices),
        unresolved_source_indices=tuple(sorted(set(unresolved))),
        component_rank_proofs=tuple(proofs),
        resonance_graph_authority_receipt_sha256=graph_receipt,
        resonance_operator_authority_receipt_sha256=operator_receipt,
        resonance_result_receipt_sha256=result_receipt,
        authority_receipt_sha256="0" * 64,
    )
    experience = AuditoryReceptorExperience(
        source_event_receipt_sha256=(
            provisional_experience.source_event_receipt_sha256
        ),
        source_event_receipt_sha256s=(
            provisional_experience.source_event_receipt_sha256s
        ),
        source_continuity_receipt_sha256s=(
            provisional_experience.source_continuity_receipt_sha256s
        ),
        source_frame_count=provisional_experience.source_frame_count,
        occurrences=provisional_experience.occurrences,
        causal_segments=provisional_experience.causal_segments,
        causal_segment_source_indices=(
            provisional_experience.causal_segment_source_indices
        ),
        unresolved_source_indices=(
            provisional_experience.unresolved_source_indices
        ),
        component_rank_proofs=(
            provisional_experience.component_rank_proofs
        ),
        resonance_graph_authority_receipt_sha256=(
            provisional_experience
            .resonance_graph_authority_receipt_sha256
        ),
        resonance_operator_authority_receipt_sha256=(
            provisional_experience
            .resonance_operator_authority_receipt_sha256
        ),
        resonance_result_receipt_sha256=(
            provisional_experience.resonance_result_receipt_sha256
        ),
        authority_receipt_sha256=_digest(
            provisional_experience.payload()
        ),
    )
    experience.verify(
        _rank_capabilities=tuple(rank_capabilities),
        _constructed_occurrences_by_channel=(
            occurrences_by_channel
        ),
    )
    return experience


def verified_receptor_experience_from_full_field_event(
    event: AuditoryReceptorFullFieldEvent,
    *,
    verified_capability: AuditoryVerifiedReceptorEventCapability,
    resonance_graph: AuditoryPhaseResonanceGraphAuthority | None = None,
    resonance_confirmation: ResonanceConfirmation | None = None,
) -> tuple[
    AuditoryReceptorExperience,
    AuditoryVerifiedReceptorExperienceCapability,
]:
    """Construct and deeply verify once, then retain request-local custody."""
    experience = receptor_experience_from_full_field_event(
        event,
        verified_capability=verified_capability,
        resonance_graph=resonance_graph,
        resonance_confirmation=resonance_confirmation,
    )
    return experience, _verified_receptor_experience_custody(experience)


def _compose_contiguous_receptor_experiences(
    experiences: tuple[AuditoryReceptorExperience, ...],
    *,
    continuity_receipt_sha256s: tuple[str, ...],
    verified_capabilities: (
        tuple[AuditoryVerifiedReceptorExperienceCapability, ...]
        | None
    ),
) -> tuple[
    AuditoryReceptorExperience,
    AuditoryVerifiedReceptorExperienceCapability,
]:
    """Compose exactly continued receptor intervals without a false barrier.

    The caller must first verify physical transport and settlement adjacency.
    Those immutable joint-settlement receipts become the composition
    authority.  Source indices are rebased into one non-overlapping interval;
    an adjacent causal segment is joined only when neither side contains an
    unresolved frame at the transport edge.
    """

    if (
        not isinstance(experiences, tuple)
        or not experiences
        or not isinstance(continuity_receipt_sha256s, tuple)
        or len(continuity_receipt_sha256s) != len(experiences)
    ):
        raise ValueError(
            "auditory receptor composition requires matched typed intervals"
        )
    if (
        verified_capabilities is not None
        and len(verified_capabilities) != len(experiences)
    ):
        raise ValueError(
            "auditory receptor verified custody cardinality changed"
        )
    for index, experience in enumerate(experiences):
        if not isinstance(experience, AuditoryReceptorExperience):
            raise TypeError(
                "auditory receptor composition requires typed experiences"
            )
        if verified_capabilities is None:
            experience.verify()
        else:
            verified_capabilities[index].verify_identity(experience)
    for receipt in continuity_receipt_sha256s:
        _require_sha256(receipt, "auditory receptor continuity authority")
    if (
        len(set(continuity_receipt_sha256s))
        != len(continuity_receipt_sha256s)
    ):
        raise ValueError("auditory receptor continuity authority is duplicated")
    source_frame_count = sum(
        experience.source_frame_count for experience in experiences
    )
    if source_frame_count > MAX_AUDITORY_RECEPTOR_FRAMES:
        raise AuditoryMotifCapacityError(
            "composed auditory receptor frame authority exhausted"
        )
    source_receipts = tuple(
        receipt
        for experience in experiences
        for receipt in experience.source_event_receipt_sha256s
    )
    if len(set(source_receipts)) != len(source_receipts):
        raise ValueError("auditory receptor source interval overlaps")

    composed_occurrences: list[AuditoryReceptorOccurrence] = []
    composed_segments: list[list[AuditoryReceptorState]] = []
    composed_segment_indices: list[list[int]] = []
    composed_unresolved: list[int] = []
    offset = 0
    prior_last_time: Fraction | None = None
    for experience in experiences:
        if experience.occurrences:
            first_time = min(
                occurrence.source_time
                for occurrence in experience.occurrences
            )
            if (
                prior_last_time is not None
                and first_time < prior_last_time
            ):
                raise ValueError(
                    "auditory receptor composition support overlaps in time"
                )
            prior_last_time = max(
                occurrence.causal_interval_end
                for occurrence in experience.occurrences
            )
        shifted_occurrences = []
        for occurrence in experience.occurrences:
            provisional = AuditoryReceptorOccurrence(
                receptor=occurrence.receptor,
                source_index=occurrence.source_index + offset,
                source_time=occurrence.source_time,
                causal_interval_end=occurrence.causal_interval_end,
                winding_delta=occurrence.winding_delta,
                pressure_fields=occurrence.pressure_fields,
                phase_fields=occurrence.phase_fields,
                pressure_field_receipt_sha256=(
                    occurrence.pressure_field_receipt_sha256
                ),
                phase_field_receipt_sha256=(
                    occurrence.phase_field_receipt_sha256
                ),
                authority_receipt_sha256="0" * 64,
            )
            shifted = AuditoryReceptorOccurrence(
                receptor=provisional.receptor,
                source_index=provisional.source_index,
                source_time=provisional.source_time,
                causal_interval_end=provisional.causal_interval_end,
                winding_delta=provisional.winding_delta,
                pressure_fields=provisional.pressure_fields,
                phase_fields=provisional.phase_fields,
                pressure_field_receipt_sha256=(
                    provisional.pressure_field_receipt_sha256
                ),
                phase_field_receipt_sha256=(
                    provisional.phase_field_receipt_sha256
                ),
                authority_receipt_sha256=_digest(provisional.payload()),
            )
            shifted_occurrences.append(shifted)
        composed_occurrences.extend(shifted_occurrences)
        shifted_unresolved = tuple(
            index + offset
            for index in experience.unresolved_source_indices
        )
        composed_unresolved.extend(shifted_unresolved)
        for segment_index, (segment, source_indices) in enumerate(zip(
            experience.causal_segments,
            experience.causal_segment_source_indices,
            strict=True,
        )):
            shifted_indices = [
                index + offset for index in source_indices
            ]
            joins_prior = (
                segment_index == 0
                and bool(composed_segments)
                and not any(
                    index > composed_segment_indices[-1][-1]
                    for index in composed_unresolved
                    if index < offset
                )
                and not any(
                    index < shifted_indices[0]
                    for index in shifted_unresolved
                )
            )
            if joins_prior:
                if composed_segments[-1][-1] == segment[0]:
                    composed_segments[-1].extend(segment[1:])
                    composed_segment_indices[-1].extend(
                        shifted_indices[1:]
                    )
                else:
                    composed_segments[-1].extend(segment)
                    composed_segment_indices[-1].extend(shifted_indices)
            else:
                composed_segments.append(list(segment))
                composed_segment_indices.append(shifted_indices)
        offset += experience.source_frame_count

    ordered_occurrences = tuple(composed_occurrences)
    occurrences_by_channel = _occurrences_by_channel(
        ordered_occurrences
    )
    proofs: list[ExactComponentTrajectoryRankProof] = []
    rank_capabilities: list[_VerifiedRankComputationCapability] = []
    for channel_index, channel_id in enumerate(_EXPECTED_CHANNEL_IDS):
        channel_occurrences = occurrences_by_channel[channel_index]
        for kind in ("pressure", "phase"):
            rows = tuple(
                tuple(
                    value for _name, value in (
                        occurrence.pressure_fields
                        if kind == "pressure"
                        else occurrence.phase_fields
                    )
                )
                for occurrence in channel_occurrences
            )
            receipts = tuple(
                occurrence.pressure_field_receipt_sha256
                if kind == "pressure"
                else occurrence.phase_field_receipt_sha256
                for occurrence in channel_occurrences
            )
            proof, rank_capability = _rank_proof(
                component_id=f"{channel_id}_{kind}",
                component_kind=kind,
                rows=rows,
                source_receipts=receipts,
                channel_occurrences=channel_occurrences,
            )
            proofs.append(proof)
            rank_capabilities.append(rank_capability)
    source_authority = _digest({
        "operator": AUDITORY_RECEPTOR_EXPERIENCE_COMPOSITION_OPERATOR,
        "source_continuity_receipt_sha256s": list(
            continuity_receipt_sha256s
        ),
        "source_event_receipt_sha256s": list(source_receipts),
        "source_frame_count": source_frame_count,
    })
    provisional = AuditoryReceptorExperience(
        source_event_receipt_sha256=source_authority,
        source_event_receipt_sha256s=source_receipts,
        source_continuity_receipt_sha256s=(
            continuity_receipt_sha256s
        ),
        source_frame_count=source_frame_count,
        occurrences=ordered_occurrences,
        causal_segments=tuple(
            tuple(segment) for segment in composed_segments
        ),
        causal_segment_source_indices=tuple(
            tuple(indices) for indices in composed_segment_indices
        ),
        unresolved_source_indices=tuple(
            sorted(set(composed_unresolved))
        ),
        component_rank_proofs=tuple(proofs),
        resonance_graph_authority_receipt_sha256=None,
        resonance_operator_authority_receipt_sha256=None,
        resonance_result_receipt_sha256=None,
        authority_receipt_sha256="0" * 64,
    )
    result = AuditoryReceptorExperience(
        source_event_receipt_sha256=(
            provisional.source_event_receipt_sha256
        ),
        source_event_receipt_sha256s=(
            provisional.source_event_receipt_sha256s
        ),
        source_continuity_receipt_sha256s=(
            provisional.source_continuity_receipt_sha256s
        ),
        source_frame_count=provisional.source_frame_count,
        occurrences=provisional.occurrences,
        causal_segments=provisional.causal_segments,
        causal_segment_source_indices=(
            provisional.causal_segment_source_indices
        ),
        unresolved_source_indices=(
            provisional.unresolved_source_indices
        ),
        component_rank_proofs=provisional.component_rank_proofs,
        resonance_graph_authority_receipt_sha256=None,
        resonance_operator_authority_receipt_sha256=None,
        resonance_result_receipt_sha256=None,
        authority_receipt_sha256=_digest(provisional.payload()),
    )
    result.verify(
        _rank_capabilities=tuple(rank_capabilities),
        _constructed_occurrences_by_channel=(
            occurrences_by_channel
        ),
    )
    return result, _verified_receptor_experience_custody(result)


def compose_contiguous_receptor_experiences(
    experiences: tuple[AuditoryReceptorExperience, ...],
    *,
    continuity_receipt_sha256s: tuple[str, ...],
) -> AuditoryReceptorExperience:
    """Compose public experiences after one full audit of every input."""
    result, _capability = _compose_contiguous_receptor_experiences(
        experiences,
        continuity_receipt_sha256s=continuity_receipt_sha256s,
        verified_capabilities=None,
    )
    return result


def compose_verified_contiguous_receptor_experiences(
    experiences: tuple[AuditoryReceptorExperience, ...],
    *,
    continuity_receipt_sha256s: tuple[str, ...],
    verified_capabilities: tuple[
        AuditoryVerifiedReceptorExperienceCapability,
        ...,
    ],
) -> tuple[
    AuditoryReceptorExperience,
    AuditoryVerifiedReceptorExperienceCapability,
]:
    """Compose child-owned inputs without repeating their deep audits."""
    return _compose_contiguous_receptor_experiences(
        experiences,
        continuity_receipt_sha256s=continuity_receipt_sha256s,
        verified_capabilities=verified_capabilities,
    )


class AuditoryMotifCapacityError(RuntimeError):
    """A bounded auditory peak operation cannot complete atomically."""


class AuditoryMotifObservationState(str, Enum):
    OBSERVED = "observed"
    INDETERMINATE_RESOURCE = "indeterminate_resource"
    DUPLICATE_EXPERIENCE = "duplicate_experience"
    AWAITING_EXACT_WINDOW_COMPOSITION = (
        "awaiting_exact_window_composition"
    )


@dataclass(frozen=True, slots=True)
class AuditoryMotifObservation:
    state: AuditoryMotifObservationState
    firing_motif_neuron_ids: tuple[str, ...]
    newly_grown_motif_neuron_ids: tuple[str, ...]
    reinforced_motif_neuron_ids: tuple[str, ...]
    unresolved_source_indices: tuple[int, ...]
    work_cells: int
    reason: str
    activations: tuple["AuditoryMotifActivation", ...] = ()


@dataclass(frozen=True, slots=True)
class AuditoryMotifFiring:
    state: AuditoryMotifObservationState
    firing_motif_neuron_ids: tuple[str, ...]
    unresolved_source_indices: tuple[int, ...]
    work_cells: int
    reason: str
    activations: tuple["AuditoryMotifActivation", ...] = ()


_PEAK_RELATION_VALUES = (-1, 0, 1)
_PEAK_RELATIONS_PER_LANE = 2 * 3 * 3 * 3
AUDITORY_PEAK_RELATION_LANE_COUNT = (
    COCHLEAR_CHANNEL_COUNT * 2 * len(DSF_FIELD_ORDER)
)
AUDITORY_PEAK_RELATION_CELL_COUNT = (
    AUDITORY_PEAK_RELATION_LANE_COUNT * _PEAK_RELATIONS_PER_LANE
)
AUDITORY_PEAK_RELATION_COUNTER_BITS = 16
AUDITORY_PEAK_RELATION_COUNTER_MAX = (
    (1 << AUDITORY_PEAK_RELATION_COUNTER_BITS) - 1
)
AUDITORY_PEAK_RELATION_MAX_SOURCE_EVENTS = 16
AUDITORY_PEAK_FADE_LOG_CAPACITY = AUDITORY_PEAK_RELATION_CELL_COUNT
AUDITORY_PEAK_FADE_TOTAL_MAX = (1 << 64) - 1
AUDITORY_PEAK_WITNESS_SCHEMA = "guala.auditory.peak_relation_witness.v1"
AUDITORY_PEAK_FADE_SCHEMA = "guala.auditory.peak_relation_fade.v1"


def _order_relation(left: Fraction | int, right: Fraction | int) -> int:
    return int(left > right) - int(left < right)


@dataclass(frozen=True, slots=True, order=True)
class AuditoryPeakLane:
    cochlear_index: int
    channel_id: str
    component_kind: str
    field_name: str
    ear_id: str = "mono"

    def verify(self) -> None:
        if (
            isinstance(self.cochlear_index, bool)
            or not isinstance(self.cochlear_index, int)
            or not 0 <= self.cochlear_index < COCHLEAR_CHANNEL_COUNT
            or self.channel_id != _EXPECTED_CHANNEL_IDS[self.cochlear_index]
            or self.component_kind not in ("pressure", "phase")
            or self.field_name not in DSF_FIELD_ORDER
            or self.ear_id not in ("mono", "left", "right")
        ):
            raise ValueError("auditory peak lane left the full-field topology")

    def payload(self) -> dict[str, object]:
        return {
            "channel_id": self.channel_id,
            "cochlear_index": self.cochlear_index,
            "component_kind": self.component_kind,
            "ear_id": self.ear_id,
            "field_name": self.field_name,
        }


@dataclass(frozen=True, slots=True, order=True)
class AuditoryPeakRelation:
    direction: int
    span_magnitude_relation: int
    same_polarity_endpoint_relation: int
    span_duration_relation: int

    def verify(self) -> None:
        if (
            self.direction not in (-1, 1)
            or self.span_magnitude_relation not in _PEAK_RELATION_VALUES
            or self.same_polarity_endpoint_relation not in _PEAK_RELATION_VALUES
            or self.span_duration_relation not in _PEAK_RELATION_VALUES
        ):
            raise ValueError("auditory peak relation left its exact topology")

    def payload(self) -> dict[str, int]:
        return {
            "direction": self.direction,
            "same_polarity_endpoint_relation": (
                self.same_polarity_endpoint_relation
            ),
            "span_duration_relation": self.span_duration_relation,
            "span_magnitude_relation": self.span_magnitude_relation,
        }


@dataclass(frozen=True, slots=True)
class AuditoryPeakPoint:
    source_index: int
    source_time: Fraction
    value: Fraction
    field_tuple_receipt_sha256: str
    occurrence_receipt_sha256: str

    def verify(self) -> None:
        if (
            isinstance(self.source_index, bool)
            or not isinstance(self.source_index, int)
            or self.source_index < 0
            or not isinstance(self.source_time, Fraction)
            or not isinstance(self.value, Fraction)
        ):
            raise ValueError("auditory peak point changed")
        _require_sha256(
            self.field_tuple_receipt_sha256,
            "auditory peak full-field tuple",
        )
        _require_sha256(
            self.occurrence_receipt_sha256,
            "auditory peak occurrence",
        )

    def payload(self) -> dict[str, object]:
        return {
            "field_tuple_receipt_sha256": (
                self.field_tuple_receipt_sha256
            ),
            "occurrence_receipt_sha256": (
                self.occurrence_receipt_sha256
            ),
            "source_index": self.source_index,
            "source_time": _fraction_text(self.source_time),
            "value": _fraction_text(self.value),
        }


@dataclass(frozen=True, slots=True)
class AuditoryPeakWitness:
    lane: AuditoryPeakLane
    relation: AuditoryPeakRelation
    extrema: tuple[AuditoryPeakPoint, AuditoryPeakPoint, AuditoryPeakPoint]
    source_experience_receipt_sha256: str
    source_event_receipt_sha256s: tuple[str, ...]
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "extrema": [value.payload() for value in self.extrema],
            "lane": self.lane.payload(),
            "relation": self.relation.payload(),
            "schema": AUDITORY_PEAK_WITNESS_SCHEMA,
            "source_event_receipt_sha256s": list(
                self.source_event_receipt_sha256s
            ),
            "source_experience_receipt_sha256": (
                self.source_experience_receipt_sha256
            ),
        }

    def verify(self) -> None:
        self.lane.verify()
        self.relation.verify()
        if (
            not isinstance(self.extrema, tuple)
            or len(self.extrema) != 3
            or not all(
                isinstance(value, AuditoryPeakPoint)
                for value in self.extrema
            )
            or not isinstance(self.source_event_receipt_sha256s, tuple)
            or not self.source_event_receipt_sha256s
            or len(self.source_event_receipt_sha256s)
            > AUDITORY_PEAK_RELATION_MAX_SOURCE_EVENTS
            or len(set(self.source_event_receipt_sha256s))
            != len(self.source_event_receipt_sha256s)
        ):
            raise ValueError("auditory peak witness changed")
        for value in self.extrema:
            value.verify()
        for digest in self.source_event_receipt_sha256s:
            _require_sha256(digest, "auditory peak source event")
        _require_sha256(
            self.source_experience_receipt_sha256,
            "auditory peak source experience",
        )
        _require_sha256(
            self.authority_receipt_sha256,
            "auditory peak witness",
        )
        first, middle, last = self.extrema
        if not (
            first.source_index < middle.source_index < last.source_index
            and first.source_time < middle.source_time < last.source_time
        ):
            raise ValueError("auditory peak witness lost causal order")
        prior_delta = middle.value - first.value
        current_delta = last.value - middle.value
        if prior_delta == 0 or current_delta == 0:
            raise ValueError("auditory peak witness lost a physical span")
        expected = AuditoryPeakRelation(
            direction=1 if current_delta > 0 else -1,
            span_magnitude_relation=_order_relation(
                abs(current_delta),
                abs(prior_delta),
            ),
            same_polarity_endpoint_relation=_order_relation(
                last.value,
                first.value,
            ),
            span_duration_relation=_order_relation(
                last.source_time - middle.source_time,
                middle.source_time - first.source_time,
            ),
        )
        if self.relation != expected:
            raise ValueError("auditory peak relation changed its raw witness")
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError("auditory peak witness receipt changed")


def _peak_neuron_id(
    lane: AuditoryPeakLane,
    relation: AuditoryPeakRelation,
) -> str:
    return _digest({
        "lane": lane.payload(),
        "operator": AUDITORY_RECURRENT_MOTIF_OPERATOR,
        "relation": relation.payload(),
    })


@dataclass(frozen=True, slots=True)
class AuditoryMotifNeuron:
    neuron_id: str
    lane: AuditoryPeakLane
    relation: AuditoryPeakRelation
    support_witnesses: tuple[AuditoryPeakWitness, AuditoryPeakWitness]
    strength: int

    @property
    def independent_experience_count(self) -> int:
        return len(self.support_witnesses)

    @property
    def support_experience_receipt_sha256s(self) -> tuple[str, ...]:
        return tuple(
            value.source_experience_receipt_sha256
            for value in self.support_witnesses
        )

    def verify(self) -> None:
        self.lane.verify()
        self.relation.verify()
        _require_sha256(self.neuron_id, "auditory peak neuron")
        if (
            self.neuron_id != _peak_neuron_id(self.lane, self.relation)
            or not isinstance(self.support_witnesses, tuple)
            or len(self.support_witnesses) != 2
            or any(
                not isinstance(value, AuditoryPeakWitness)
                for value in self.support_witnesses
            )
            or isinstance(self.strength, bool)
            or not isinstance(self.strength, int)
            or not 2 <= self.strength <= AUDITORY_PEAK_RELATION_COUNTER_MAX
        ):
            raise ValueError("auditory peak neuron changed")
        for witness in self.support_witnesses:
            witness.verify()
            if (
                witness.lane != self.lane
                or witness.relation != self.relation
            ):
                raise ValueError("auditory peak neuron support changed")
        left, right = self.support_witnesses
        if (
            left.source_experience_receipt_sha256
            == right.source_experience_receipt_sha256
            or set(left.source_event_receipt_sha256s).intersection(
                right.source_event_receipt_sha256s
            )
        ):
            raise ValueError("auditory peak neuron support is not independent")


@dataclass(frozen=True, slots=True)
class _PeakAtom:
    neuron_id: str
    witness: AuditoryPeakWitness
    full_field_occurrences: tuple[AuditoryReceptorOccurrence, ...]
    atom_ordinal: int


def _group_peak_atoms(
    atoms: tuple[_PeakAtom, ...],
) -> tuple[tuple[str, tuple[_PeakAtom, ...]], ...]:
    grouped: dict[str, list[_PeakAtom]] = {}
    for atom in atoms:
        grouped.setdefault(atom.neuron_id, []).append(atom)
    return tuple(
        (neuron_id, tuple(values))
        for neuron_id, values in grouped.items()
    )


_PREPARED_PEAK_CONSTRUCTION_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class AuditoryPreparedPeakExperience:
    """One request-local exact extraction shared by firing and learning."""

    experience: AuditoryReceptorExperience
    atoms: tuple[_PeakAtom, ...]
    atom_groups: tuple[tuple[str, tuple[_PeakAtom, ...]], ...]
    work_cells: int
    authority_receipt_sha256: str
    _construction_authority: object

    def payload(self) -> dict[str, object]:
        return {
            "atom_support": [
                {
                    "atom_ordinal": atom.atom_ordinal,
                    "full_field_occurrence_receipt_sha256s": [
                        value.authority_receipt_sha256
                        for value in atom.full_field_occurrences
                    ],
                    "neuron_id": atom.neuron_id,
                    "witness_receipt_sha256": (
                        atom.witness.authority_receipt_sha256
                    ),
                }
                for atom in self.atoms
            ],
            "schema": "guala.auditory.prepared_peak_experience.v1",
            "source_experience_receipt_sha256": (
                self.experience.authority_receipt_sha256
            ),
            "work_cells": self.work_cells,
        }

    def verify(self) -> None:
        if (
            self._construction_authority
            is not _PREPARED_PEAK_CONSTRUCTION_AUTHORITY
        ):
            raise ValueError(
                "prepared auditory peaks lack construction authority"
            )
        self.experience.verify()
        if (
            not isinstance(self.atoms, tuple)
            or isinstance(self.work_cells, bool)
            or not isinstance(self.work_cells, int)
            or self.work_cells
            != len(self.experience.occurrences) * 2 * len(
                DSF_FIELD_ORDER
            ) + len(self.atoms)
        ):
            raise ValueError("prepared auditory peak work changed")
        for atom in self.atoms:
            if not isinstance(atom, _PeakAtom):
                raise TypeError("prepared auditory peak atom is not typed")
            atom.witness.verify()
            if (
                atom.neuron_id
                != _peak_neuron_id(
                    atom.witness.lane,
                    atom.witness.relation,
                )
                or
                atom.witness.source_experience_receipt_sha256
                != self.experience.authority_receipt_sha256
                or atom.witness.source_event_receipt_sha256s
                != self.experience.source_event_receipt_sha256s
                or not atom.full_field_occurrences
                or any(
                    value.receptor.cochlear_index
                    != atom.witness.lane.cochlear_index
                    for value in atom.full_field_occurrences
                )
                or not {
                    value.occurrence_receipt_sha256
                    for value in atom.witness.extrema
                }.issubset({
                    value.authority_receipt_sha256
                    for value in atom.full_field_occurrences
                })
            ):
                raise ValueError("prepared auditory peak support changed")
            for value in atom.full_field_occurrences:
                value.verify()
        if (
            not isinstance(self.atom_groups, tuple)
            or self.atom_groups != _group_peak_atoms(self.atoms)
        ):
            raise ValueError("prepared auditory peak grouping changed")
        _require_sha256(
            self.authority_receipt_sha256,
            "prepared auditory peak experience",
        )
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError("prepared auditory peak receipt changed")


def _peak_point(
    occurrence: AuditoryReceptorOccurrence,
    *,
    component_kind: str,
    field_name: str,
) -> AuditoryPeakPoint:
    fields = (
        occurrence.pressure_fields
        if component_kind == "pressure"
        else occurrence.phase_fields
    )
    receipt = (
        occurrence.pressure_field_receipt_sha256
        if component_kind == "pressure"
        else occurrence.phase_field_receipt_sha256
    )
    return AuditoryPeakPoint(
        source_index=occurrence.source_index,
        source_time=occurrence.source_time,
        value=dict(fields)[field_name],
        field_tuple_receipt_sha256=receipt,
        occurrence_receipt_sha256=occurrence.authority_receipt_sha256,
    )


def _peak_atoms_from_experience(
    experience: AuditoryReceptorExperience,
    *,
    ear_id: str = "mono",
    source_episode_receipt_sha256: str | None = None,
    source_event_receipt_sha256s: tuple[str, ...] | None = None,
) -> tuple[_PeakAtom, ...]:
    if ear_id not in ("mono", "left", "right"):
        raise ValueError("auditory peak ear identity changed")
    episode_receipt = (
        experience.authority_receipt_sha256
        if source_episode_receipt_sha256 is None
        else _require_sha256(
            source_episode_receipt_sha256,
            "auditory peak source episode",
        )
    )
    event_receipts = (
        experience.source_event_receipt_sha256s
        if source_event_receipt_sha256s is None
        else source_event_receipt_sha256s
    )
    atoms: list[_PeakAtom] = []
    occurrences_by_channel = _occurrences_by_channel(
        experience.occurrences
    )
    for cochlear_index, channel_id in enumerate(_EXPECTED_CHANNEL_IDS):
        channel_occurrences = occurrences_by_channel[cochlear_index]
        occurrence_position_by_source_index = {
            occurrence.source_index: position
            for position, occurrence in enumerate(channel_occurrences)
        }
        if len(occurrence_position_by_source_index) != len(
            channel_occurrences
        ):
            raise ValueError(
                "auditory peak channel contains duplicate source indices"
            )
        for component_kind in ("pressure", "phase"):
            for field_index, field_name in enumerate(DSF_FIELD_ORDER):
                points = tuple(
                    AuditoryPeakPoint(
                        source_index=value.source_index,
                        source_time=value.source_time,
                        value=(
                            value.pressure_fields
                            if component_kind == "pressure"
                            else value.phase_fields
                        )[field_index][1],
                        field_tuple_receipt_sha256=(
                            value.pressure_field_receipt_sha256
                            if component_kind == "pressure"
                            else value.phase_field_receipt_sha256
                        ),
                        occurrence_receipt_sha256=(
                            value.authority_receipt_sha256
                        ),
                    )
                    for value in channel_occurrences
                )
                if len(points) < 3:
                    continue
                runs: list[list[AuditoryPeakPoint]] = []
                for point in points:
                    if runs and runs[-1][-1].value == point.value:
                        runs[-1].append(point)
                    else:
                        runs.append([point])
                if len(runs) < 3:
                    continue
                extrema_indices = [0]
                for index in range(1, len(runs) - 1):
                    prior = _order_relation(
                        runs[index][-1].value,
                        runs[index - 1][-1].value,
                    )
                    following = _order_relation(
                        runs[index + 1][-1].value,
                        runs[index][-1].value,
                    )
                    if prior != following:
                        extrema_indices.append(index)
                extrema_indices.append(len(runs) - 1)
                extrema = tuple(
                    runs[index][-1] for index in extrema_indices
                )
                lane = AuditoryPeakLane(
                    cochlear_index=cochlear_index,
                    channel_id=channel_id,
                    component_kind=component_kind,
                    field_name=field_name,
                    ear_id=ear_id,
                )
                for ordinal in range(2, len(extrema)):
                    selected = (
                        extrema[ordinal - 2],
                        extrema[ordinal - 1],
                        extrema[ordinal],
                    )
                    prior_delta = selected[1].value - selected[0].value
                    current_delta = selected[2].value - selected[1].value
                    if prior_delta == 0 or current_delta == 0:
                        continue
                    relation = AuditoryPeakRelation(
                        direction=1 if current_delta > 0 else -1,
                        span_magnitude_relation=_order_relation(
                            abs(current_delta),
                            abs(prior_delta),
                        ),
                        same_polarity_endpoint_relation=_order_relation(
                            selected[2].value,
                            selected[0].value,
                        ),
                        span_duration_relation=_order_relation(
                            selected[2].source_time
                            - selected[1].source_time,
                            selected[1].source_time
                            - selected[0].source_time,
                        ),
                    )
                    provisional = AuditoryPeakWitness(
                        lane=lane,
                        relation=relation,
                        extrema=selected,
                        source_experience_receipt_sha256=(
                            episode_receipt
                        ),
                        source_event_receipt_sha256s=(
                            event_receipts
                        ),
                        authority_receipt_sha256="0" * 64,
                    )
                    witness = AuditoryPeakWitness(
                        lane=provisional.lane,
                        relation=provisional.relation,
                        extrema=provisional.extrema,
                        source_experience_receipt_sha256=(
                            provisional.source_experience_receipt_sha256
                        ),
                        source_event_receipt_sha256s=(
                            provisional.source_event_receipt_sha256s
                        ),
                        authority_receipt_sha256=_digest(
                            provisional.payload()
                        ),
                    )
                    start = selected[0].source_index
                    end = selected[2].source_index
                    start_position = occurrence_position_by_source_index[
                        start
                    ]
                    end_position = occurrence_position_by_source_index[end]
                    support = channel_occurrences[
                        start_position:end_position + 1
                    ]
                    atoms.append(_PeakAtom(
                        neuron_id=_peak_neuron_id(lane, relation),
                        witness=witness,
                        full_field_occurrences=support,
                        atom_ordinal=ordinal - 2,
                    ))
    return tuple(atoms)


@dataclass(frozen=True, slots=True)
class AuditoryMotifActivation:
    neuron_id: str
    segment_index: int
    state_ordinal_start: int
    state_ordinal_end: int
    source_index_start: int
    source_index_end: int
    source_time_start: Fraction
    source_time_end: Fraction
    full_field_occurrences: tuple[AuditoryReceptorOccurrence, ...]
    ear_id: str = "mono"

    def verify(
        self,
        neuron: AuditoryMotifNeuron,
        experience: AuditoryReceptorExperience,
    ) -> None:
        neuron.verify()
        experience.verify()
        if (
            self.neuron_id != neuron.neuron_id
            or self.ear_id != neuron.lane.ear_id
            or not self.full_field_occurrences
            or self.source_index_start
            != min(
                value.source_index
                for value in self.full_field_occurrences
            )
            or self.source_index_end
            != max(
                value.source_index
                for value in self.full_field_occurrences
            )
            or self.source_time_start
            != min(
                value.source_time
                for value in self.full_field_occurrences
            )
            or self.source_time_end
            != max(
                value.causal_interval_end
                for value in self.full_field_occurrences
            )
            or self.state_ordinal_end != self.state_ordinal_start + 1
        ):
            raise ValueError("auditory peak activation support changed")
        for value in self.full_field_occurrences:
            value.verify()
        candidates = _peak_atoms_from_experience(
            experience,
            ear_id=self.ear_id,
            source_episode_receipt_sha256=(
                neuron.support_witnesses[0]
                .source_experience_receipt_sha256
                if self.ear_id != "mono"
                else None
            ),
        )
        if not any(
            value.neuron_id == self.neuron_id
            and value.atom_ordinal == self.state_ordinal_start
            and value.witness.lane.cochlear_index == self.segment_index // 2
            and min(
                item.source_index
                for item in value.full_field_occurrences
            )
            == self.source_index_start
            and max(
                item.source_index
                for item in value.full_field_occurrences
            )
            == self.source_index_end
            for value in candidates
        ):
            raise ValueError("auditory peak activation relation changed")


def _peak_activation(
    neuron: AuditoryMotifNeuron,
    atom: _PeakAtom,
) -> AuditoryMotifActivation:
    occurrences = atom.full_field_occurrences
    result = AuditoryMotifActivation(
        neuron_id=neuron.neuron_id,
        segment_index=(
            neuron.lane.cochlear_index * 2
            + int(neuron.lane.component_kind == "phase")
        ),
        state_ordinal_start=atom.atom_ordinal,
        state_ordinal_end=atom.atom_ordinal + 1,
        source_index_start=min(
            value.source_index for value in occurrences
        ),
        source_index_end=max(
            value.source_index for value in occurrences
        ),
        source_time_start=min(
            value.source_time for value in occurrences
        ),
        source_time_end=max(
            value.causal_interval_end for value in occurrences
        ),
        full_field_occurrences=occurrences,
        ear_id=neuron.lane.ear_id,
    )
    return result


def _peak_atoms_fit_fraction_authority(
    atoms: tuple[_PeakAtom, ...],
    profile: AuditoryMotifResourceProfile,
) -> bool:
    limit = profile.max_exact_fraction_text_bytes
    return all(
        len(_fraction_text(value).encode("utf-8")) <= limit
        for atom in atoms
        for point in atom.witness.extrema
        for value in (point.source_time, point.value)
    )


def _witness_fits_fraction_authority(
    witness: AuditoryPeakWitness,
    profile: AuditoryMotifResourceProfile,
) -> bool:
    return all(
        len(_fraction_text(value).encode("utf-8"))
        <= profile.max_exact_fraction_text_bytes
        for point in witness.extrema
        for value in (point.source_time, point.value)
    )


def auditory_peak_bank_max_encoded_bytes(
    profile: AuditoryMotifResourceProfile,
    *,
    ear_count: int = 1,
) -> int:
    """Conservative canonical-byte authority for every physical q cell."""

    profile.verify()
    if ear_count not in (1, 2):
        raise ValueError("auditory peak bank supports one or two ears")
    if ear_count != profile.ear_count:
        raise ValueError("auditory peak bank ear topology changed")
    result = _derived_worst_case_encoded_bytes(
        ear_count=ear_count,
        max_motif_neurons=profile.max_motif_neurons,
        max_pending_experiences=profile.max_pending_experiences,
        max_exact_fraction_text_bytes=(
            profile.max_exact_fraction_text_bytes
        ),
    )
    if result != profile.max_encoded_state_bytes:
        raise ValueError("peak-bank byte derivation changed")
    return result


def _witness_record(value: AuditoryPeakWitness) -> dict[str, object]:
    value.verify()
    return value.payload() | {
        "authority_receipt_sha256": value.authority_receipt_sha256,
    }


def _custodied_witness_record(
    value: AuditoryPeakWitness,
) -> dict[str, object]:
    """Serialize an immutable witness already owned by the audited bank."""

    return value.payload() | {
        "authority_receipt_sha256": value.authority_receipt_sha256,
    }


def _point_from_record(value: object) -> AuditoryPeakPoint:
    if not isinstance(value, dict):
        raise ValueError("auditory peak point record changed")
    result = AuditoryPeakPoint(
        source_index=value.get("source_index"),
        source_time=_fraction(
            value.get("source_time"),
            "auditory peak point time",
        ),
        value=_fraction(value.get("value"), "auditory peak value"),
        field_tuple_receipt_sha256=value.get(
            "field_tuple_receipt_sha256"
        ),
        occurrence_receipt_sha256=value.get(
            "occurrence_receipt_sha256"
        ),
    )
    result.verify()
    return result


def _witness_from_record(value: object) -> AuditoryPeakWitness:
    if not isinstance(value, dict):
        raise ValueError("auditory peak witness record changed")
    raw_lane = value.get("lane")
    raw_relation = value.get("relation")
    raw_extrema = value.get("extrema")
    raw_sources = value.get("source_event_receipt_sha256s")
    if (
        not isinstance(raw_lane, dict)
        or not isinstance(raw_relation, dict)
        or not isinstance(raw_extrema, list)
        or len(raw_extrema) != 3
        or not isinstance(raw_sources, list)
    ):
        raise ValueError("auditory peak witness record changed")
    result = AuditoryPeakWitness(
        lane=AuditoryPeakLane(
            cochlear_index=raw_lane.get("cochlear_index"),
            channel_id=raw_lane.get("channel_id"),
            component_kind=raw_lane.get("component_kind"),
            field_name=raw_lane.get("field_name"),
            ear_id=raw_lane.get("ear_id"),
        ),
        relation=AuditoryPeakRelation(
            direction=raw_relation.get("direction"),
            span_magnitude_relation=raw_relation.get(
                "span_magnitude_relation"
            ),
            same_polarity_endpoint_relation=raw_relation.get(
                "same_polarity_endpoint_relation"
            ),
            span_duration_relation=raw_relation.get(
                "span_duration_relation"
            ),
        ),
        extrema=tuple(_point_from_record(item) for item in raw_extrema),
        source_experience_receipt_sha256=value.get(
            "source_experience_receipt_sha256"
        ),
        source_event_receipt_sha256s=tuple(raw_sources),
        authority_receipt_sha256=value.get("authority_receipt_sha256"),
    )
    result.verify()
    return result


def _peak_state_encoded(
    profile: AuditoryMotifResourceProfile,
    neurons: dict[str, AuditoryMotifNeuron],
    primed: dict[str, AuditoryPeakWitness],
    fade_receipts: list[str],
    fade_total_count: int,
    recent_experience_receipts: list[str],
    ear_ids: tuple[str, ...],
) -> bytes:
    body = {
        "fade_receipts": list(fade_receipts),
        "fade_total_count": fade_total_count,
        "ear_ids": list(ear_ids),
        "motif_neurons": [
            {
                "lane": value.lane.payload(),
                "neuron_id": value.neuron_id,
                "relation": value.relation.payload(),
                "strength": value.strength,
                "support_witnesses": [
                    _custodied_witness_record(item)
                    for item in value.support_witnesses
                ],
            }
            for value in (
                neurons[key] for key in sorted(neurons)
            )
        ],
        "primed_cells": [
            {
                "neuron_id": key,
                "witness": _custodied_witness_record(primed[key]),
            }
            for key in sorted(primed)
        ],
        "recent_experience_receipts": list(
            recent_experience_receipts
        ),
        "resource_profile": (
            profile.payload()
            | {
                "authority_receipt_sha256": (
                    profile.authority_receipt_sha256
                )
            }
        ),
        "schema": AUDITORY_RECURRENT_MOTIF_STATE_SCHEMA,
    }
    return _canonical_bytes({
        "body": body,
        "body_sha256": _digest(body),
    })


def _retire_primed_experience_cohorts(
    primed: dict[str, AuditoryPeakWitness],
    *,
    chronological_experience_receipts: list[str],
    max_pending_experiences: int,
) -> dict[str, AuditoryPeakWitness]:
    """Retain the exact newest bounded cohorts after comparison has occurred."""

    pending_receipts = {
        witness.source_experience_receipt_sha256
        for witness in primed.values()
    }
    chronological_pending = [
        receipt
        for receipt in chronological_experience_receipts
        if receipt in pending_receipts
    ]
    if (
        len(set(chronological_pending)) != len(chronological_pending)
        or set(chronological_pending) != pending_receipts
    ):
        raise RuntimeError(
            "primed auditory experience chronology is incomplete"
        )
    retained_receipts = set(
        chronological_pending[-max_pending_experiences:]
    )
    return {
        neuron_id: witness
        for neuron_id, witness in primed.items()
        if witness.source_experience_receipt_sha256 in retained_receipts
    }


def _fade_receipt(experience: AuditoryReceptorExperience) -> str:
    return _digest({
        "distillation": (
            "all_peak_relation_cells_extracted_before_raw_release"
        ),
        "schema": AUDITORY_PEAK_FADE_SCHEMA,
        "source_event_receipt_sha256s": list(
            experience.source_event_receipt_sha256s
        ),
        "source_experience_receipt_sha256": (
            experience.authority_receipt_sha256
        ),
    })


def _activation_payload(
    activation: AuditoryMotifActivation,
) -> dict[str, object]:
    return {
        "ear_id": activation.ear_id,
        "full_field_occurrences": [
            occurrence.payload()
            | {
                "authority_receipt_sha256": (
                    occurrence.authority_receipt_sha256
                )
            }
            for occurrence in activation.full_field_occurrences
        ],
        "neuron_id": activation.neuron_id,
        "segment_index": activation.segment_index,
        "source_index_end": activation.source_index_end,
        "source_index_start": activation.source_index_start,
        "source_time_end": _fraction_text(activation.source_time_end),
        "source_time_start": _fraction_text(activation.source_time_start),
        "state_ordinal_end": activation.state_ordinal_end,
        "state_ordinal_start": activation.state_ordinal_start,
    }


def _verify_activation_result(
    activation: AuditoryMotifActivation,
    *,
    firing_ids: tuple[str, ...],
    ear_ids: tuple[str, ...],
) -> None:
    if not isinstance(activation, AuditoryMotifActivation):
        raise TypeError("binaural peak activation is not typed")
    _require_sha256(activation.neuron_id, "binaural peak neuron")
    if (
        activation.neuron_id not in firing_ids
        or activation.ear_id not in ear_ids
        or isinstance(activation.segment_index, bool)
        or not isinstance(activation.segment_index, int)
        or not 0 <= activation.segment_index < COCHLEAR_CHANNEL_COUNT * 2
        or isinstance(activation.state_ordinal_start, bool)
        or not isinstance(activation.state_ordinal_start, int)
        or activation.state_ordinal_start < 0
        or activation.state_ordinal_end
        != activation.state_ordinal_start + 1
        or isinstance(activation.source_index_start, bool)
        or not isinstance(activation.source_index_start, int)
        or isinstance(activation.source_index_end, bool)
        or not isinstance(activation.source_index_end, int)
        or not isinstance(activation.source_time_start, Fraction)
        or not isinstance(activation.source_time_end, Fraction)
        or not activation.full_field_occurrences
    ):
        raise ValueError("binaural peak activation structure changed")
    for occurrence in activation.full_field_occurrences:
        occurrence.verify()
        if (
            occurrence.receptor.cochlear_index
            != activation.segment_index // 2
        ):
            raise ValueError("binaural peak activation changed cochlear lane")
    if (
        len({
            value.authority_receipt_sha256
            for value in activation.full_field_occurrences
        })
        != len(activation.full_field_occurrences)
        or activation.source_index_start
        != min(
            value.source_index
            for value in activation.full_field_occurrences
        )
        or activation.source_index_end
        != max(
            value.source_index
            for value in activation.full_field_occurrences
        )
        or activation.source_time_start
        != min(
            value.source_time
            for value in activation.full_field_occurrences
        )
        or activation.source_time_end
        != max(
            value.causal_interval_end
            for value in activation.full_field_occurrences
        )
    ):
        raise ValueError("binaural peak activation causal support changed")


def _verify_result_ids(values: tuple[str, ...], name: str) -> None:
    if (
        not isinstance(values, tuple)
        or values != tuple(sorted(set(values)))
    ):
        raise ValueError(f"{name} must be an ordered unique tuple")
    for value in values:
        _require_sha256(value, name)


def _verify_result_common(
    *,
    state: object,
    firing_ids: tuple[str, ...],
    unresolved: tuple[int, ...],
    work_cells: object,
    reason: object,
    activations: tuple[AuditoryMotifActivation, ...],
    ear_ids: tuple[str, ...],
) -> None:
    if not isinstance(state, AuditoryMotifObservationState):
        raise TypeError("binaural peak result state is not typed")
    _verify_result_ids(firing_ids, "binaural firing neuron")
    if (
        not isinstance(unresolved, tuple)
        or unresolved != tuple(sorted(set(unresolved)))
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in unresolved
        )
        or isinstance(work_cells, bool)
        or not isinstance(work_cells, int)
        or work_cells < 0
        or not isinstance(reason, str)
        or not reason
        or reason != reason.strip()
        or not isinstance(activations, tuple)
    ):
        raise ValueError("binaural peak nested result changed")
    if (
        state is not AuditoryMotifObservationState.OBSERVED
        and (firing_ids or activations)
    ):
        raise ValueError("indeterminate binaural result falsely fired")
    for activation in activations:
        _verify_activation_result(
            activation,
            firing_ids=firing_ids,
            ear_ids=ear_ids,
        )


def _observation_payload(
    observation: AuditoryMotifObservation,
) -> dict[str, object]:
    return {
        "activations": [
            _activation_payload(value)
            for value in observation.activations
        ],
        "firing_motif_neuron_ids": list(
            observation.firing_motif_neuron_ids
        ),
        "newly_grown_motif_neuron_ids": list(
            observation.newly_grown_motif_neuron_ids
        ),
        "reason": observation.reason,
        "reinforced_motif_neuron_ids": list(
            observation.reinforced_motif_neuron_ids
        ),
        "state": observation.state.value,
        "unresolved_source_indices": list(
            observation.unresolved_source_indices
        ),
        "work_cells": observation.work_cells,
    }


def _firing_payload(firing: AuditoryMotifFiring) -> dict[str, object]:
    return {
        "activations": [
            _activation_payload(value)
            for value in firing.activations
        ],
        "firing_motif_neuron_ids": list(
            firing.firing_motif_neuron_ids
        ),
        "reason": firing.reason,
        "state": firing.state.value,
        "unresolved_source_indices": list(
            firing.unresolved_source_indices
        ),
        "work_cells": firing.work_cells,
    }


@dataclass(frozen=True, slots=True)
class AuditoryBinauralMotifObservation:
    source_settlement_receipt_sha256: str
    ear_ids: tuple[str, str]
    observation: AuditoryMotifObservation
    authority_receipt_sha256: str

    @property
    def firing_motif_neuron_ids(self) -> tuple[str, ...]:
        return self.observation.firing_motif_neuron_ids

    @property
    def activations(self) -> tuple[AuditoryMotifActivation, ...]:
        return self.observation.activations

    def payload(self) -> dict[str, object]:
        return {
            "ear_ids": list(self.ear_ids),
            "observation": _observation_payload(self.observation),
            "schema": "guala.auditory.binaural_peak_observation.v1",
            "source_settlement_receipt_sha256": (
                self.source_settlement_receipt_sha256
            ),
        }

    def verify(self) -> None:
        _require_sha256(
            self.source_settlement_receipt_sha256,
            "binaural peak source settlement",
        )
        _require_sha256(
            self.authority_receipt_sha256,
            "binaural peak observation",
        )
        if self.ear_ids != ("left", "right"):
            raise ValueError("binaural peak ear topology changed")
        if not isinstance(self.observation, AuditoryMotifObservation):
            raise TypeError("binaural peak observation is not typed")
        _verify_result_common(
            state=self.observation.state,
            firing_ids=self.observation.firing_motif_neuron_ids,
            unresolved=self.observation.unresolved_source_indices,
            work_cells=self.observation.work_cells,
            reason=self.observation.reason,
            activations=self.observation.activations,
            ear_ids=self.ear_ids,
        )
        _verify_result_ids(
            self.observation.newly_grown_motif_neuron_ids,
            "newly grown binaural peak neuron",
        )
        _verify_result_ids(
            self.observation.reinforced_motif_neuron_ids,
            "reinforced binaural peak neuron",
        )
        if set(
            self.observation.newly_grown_motif_neuron_ids
        ).intersection(
            self.observation.reinforced_motif_neuron_ids
        ):
            raise ValueError("binaural peak growth and reinforcement overlap")
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError("binaural peak observation authority changed")


@dataclass(frozen=True, slots=True)
class AuditoryBinauralMotifFiring:
    source_settlement_receipt_sha256: str
    ear_ids: tuple[str, str]
    firing: AuditoryMotifFiring
    authority_receipt_sha256: str

    @property
    def firing_motif_neuron_ids(self) -> tuple[str, ...]:
        return self.firing.firing_motif_neuron_ids

    @property
    def activations(self) -> tuple[AuditoryMotifActivation, ...]:
        return self.firing.activations

    def payload(self) -> dict[str, object]:
        return {
            "ear_ids": list(self.ear_ids),
            "firing": _firing_payload(self.firing),
            "schema": "guala.auditory.binaural_peak_firing.v1",
            "source_settlement_receipt_sha256": (
                self.source_settlement_receipt_sha256
            ),
        }

    def verify(self) -> None:
        _require_sha256(
            self.source_settlement_receipt_sha256,
            "binaural peak source settlement",
        )
        _require_sha256(
            self.authority_receipt_sha256,
            "binaural peak firing",
        )
        if self.ear_ids != ("left", "right"):
            raise ValueError("binaural peak ear topology changed")
        if not isinstance(self.firing, AuditoryMotifFiring):
            raise TypeError("binaural peak firing is not typed")
        _verify_result_common(
            state=self.firing.state,
            firing_ids=self.firing.firing_motif_neuron_ids,
            unresolved=self.firing.unresolved_source_indices,
            work_cells=self.firing.work_cells,
            reason=self.firing.reason,
            activations=self.firing.activations,
            ear_ids=self.ear_ids,
        )
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError("binaural peak firing authority changed")


@dataclass(frozen=True, slots=True)
class _BinauralMotifOwnerState:
    neurons: tuple[tuple[str, AuditoryMotifNeuron], ...]
    primed: tuple[tuple[str, AuditoryPeakWitness], ...]
    fade_receipts: tuple[str, ...]
    fade_total_count: int
    recent_experience_receipts: tuple[str, ...]
    seen_experience_receipts: frozenset[str]
    encoded_state_cache: bytes | None


_PREPARED_BINAURAL_MOTIF_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class PreparedAuditoryBinauralMotifObservation:
    """One exact two-ear sensory-learning mutation held outside live state."""

    observation: AuditoryBinauralMotifObservation
    _prior_state: _BinauralMotifOwnerState
    _staged_state: _BinauralMotifOwnerState
    _event: tuple[str, tuple[tuple[str, object], ...]] | None
    _construction_authority: object


@dataclass(frozen=True, slots=True)
class AuditoryBinauralMotifCommitUndo:
    """Exact authority to restore one just-committed binaural observation."""

    prepared: PreparedAuditoryBinauralMotifObservation


_BINAURAL_VISIBILITY_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class AuditoryBinauralMotifVisibilityInstall:
    _prepared: PreparedAuditoryBinauralMotifObservation
    _neurons: dict[str, AuditoryMotifNeuron]
    _primed: dict[str, AuditoryPeakWitness]
    _fade_receipts: list[str]
    _fade_total_count: int
    _recent_experience_receipts: list[str]
    _seen_experience_receipts: set[str]
    _encoded_state_cache: bytes | None
    _owner_authority: object
    _construction_authority: object


class AuditoryRecurrentMotifOwner:
    """Indexed bounded bank of exact recurrent peak-to-peak field neurons."""

    def __init__(
        self,
        resource_profile: AuditoryMotifResourceProfile,
        *,
        log_event: Callable[..., None] | None = None,
        ear_ids: tuple[str, ...] = ("mono",),
    ) -> None:
        if not isinstance(resource_profile, AuditoryMotifResourceProfile):
            raise TypeError("auditory motif owner requires a resource profile")
        resource_profile.verify()
        if ear_ids not in (("mono",), ("left", "right")):
            raise ValueError("auditory peak owner topology must be mono or binaural")
        if resource_profile.ear_count != len(ear_ids):
            raise ValueError(
                "auditory peak owner and profile ear topology differ"
            )
        self._profile = resource_profile
        self._ear_ids = ear_ids
        self._neurons: dict[str, AuditoryMotifNeuron] = {}
        self._primed: dict[str, AuditoryPeakWitness] = {}
        self._fade_receipts: list[str] = []
        self._fade_total_count = 0
        self._recent_experience_receipts: list[str] = []
        self._seen_experience_receipts: set[str] = set()
        self._prepared_peak: AuditoryPreparedPeakExperience | None = None
        self._prepared_binaural: (
            PreparedAuditoryBinauralMotifObservation | None
        ) = None
        self._encoded_state_cache: bytes | None = None
        self._log_event = log_event
        self._visibility_install: (
            AuditoryBinauralMotifVisibilityInstall | None
        ) = None
        self._visibility_rollback: (
            AuditoryBinauralMotifCommitUndo | None
        ) = None
        self._visibility_owner_authority = object()
        self._lock = threading.RLock()

    def _require_public_visibility_locked(self) -> None:
        if (
            self._visibility_install is not None
            or self._visibility_rollback is not None
        ):
            raise RuntimeError(
                "binaural motif visibility transaction is in progress"
            )

    @property
    def resource_profile(self) -> AuditoryMotifResourceProfile:
        return self._profile

    @property
    def motif_neurons(self) -> tuple[AuditoryMotifNeuron, ...]:
        with self._lock:
            self._require_public_visibility_locked()
            return tuple(
                self._neurons[key] for key in sorted(self._neurons)
            )

    @property
    def pending_experience_count(self) -> int:
        with self._lock:
            self._require_public_visibility_locked()
            return len({
                value.source_experience_receipt_sha256
                for value in self._primed.values()
            })

    def prepare(
        self,
        experience: AuditoryReceptorExperience,
        *,
        verified_capability: (
            AuditoryVerifiedReceptorExperienceCapability | None
        ) = None,
    ) -> AuditoryPreparedPeakExperience:
        """Extract mono q atoms once for prelearning fire plus observation."""

        with self._lock:
            self._require_public_visibility_locked()
            if self._prepared_peak is not None:
                raise AuditoryMotifCapacityError(
                    "auditory prepared peak request capacity exhausted"
                )
        if not isinstance(experience, AuditoryReceptorExperience):
            raise TypeError("auditory peak preparation requires typed experience")
        if verified_capability is None:
            experience.verify()
        else:
            verified_capability.verify_identity(experience)
        if self._ear_ids != ("mono",):
            raise TypeError("binaural auditory peak preparation is separate")
        atoms = _peak_atoms_from_experience(experience)
        atom_groups = _group_peak_atoms(atoms)
        work_cells = len(experience.occurrences) * 2 * len(
            DSF_FIELD_ORDER
        ) + len(atoms)
        provisional = AuditoryPreparedPeakExperience(
            experience=experience,
            atoms=atoms,
            atom_groups=atom_groups,
            work_cells=work_cells,
            authority_receipt_sha256="0" * 64,
            _construction_authority=(
                _PREPARED_PEAK_CONSTRUCTION_AUTHORITY
            ),
        )
        result = replace(
            provisional,
            authority_receipt_sha256=_digest(provisional.payload()),
        )
        _require_sha256(
            result.authority_receipt_sha256,
            "prepared auditory peak experience",
        )
        if _digest(result.payload()) != result.authority_receipt_sha256:
            raise ValueError("prepared auditory peak receipt changed")
        with self._lock:
            self._require_public_visibility_locked()
            if self._prepared_peak is not None:
                raise AuditoryMotifCapacityError(
                    "auditory prepared peak request capacity exhausted"
                )
            self._prepared_peak = result
        return result

    def _mono_peak_input(
        self,
        value: (
            AuditoryReceptorExperience
            | AuditoryPreparedPeakExperience
        ),
    ) -> tuple[
        AuditoryReceptorExperience,
        tuple[_PeakAtom, ...],
        tuple[tuple[str, tuple[_PeakAtom, ...]], ...],
        int,
    ]:
        if isinstance(value, AuditoryPreparedPeakExperience):
            if (
                value._construction_authority
                is not _PREPARED_PEAK_CONSTRUCTION_AUTHORITY
            ):
                raise ValueError(
                    "prepared auditory peaks lack construction authority"
                )
            if (
                not isinstance(value.atoms, tuple)
                or isinstance(value.work_cells, bool)
                or not isinstance(value.work_cells, int)
                or value.work_cells
                != len(value.experience.occurrences) * 2 * len(
                    DSF_FIELD_ORDER
                ) + len(value.atoms)
            ):
                raise ValueError("prepared auditory peak work changed")
            with self._lock:
                self._require_public_visibility_locked()
                if self._prepared_peak is not value:
                    raise ValueError(
                        "prepared auditory peaks left owner custody"
                    )
            return (
                value.experience,
                value.atoms,
                value.atom_groups,
                value.work_cells,
            )
        if not isinstance(value, AuditoryReceptorExperience):
            raise TypeError("auditory peak input requires typed experience")
        value.verify()
        atoms = _peak_atoms_from_experience(value)
        return (
            value,
            atoms,
            _group_peak_atoms(atoms),
            len(value.occurrences) * 2 * len(DSF_FIELD_ORDER)
            + len(atoms),
        )

    def _capacity_result(
        self,
        experience: AuditoryReceptorExperience,
        *,
        work_cells: int,
        reason: str,
    ) -> AuditoryMotifObservation:
        return AuditoryMotifObservation(
            state=AuditoryMotifObservationState.INDETERMINATE_RESOURCE,
            firing_motif_neuron_ids=(),
            newly_grown_motif_neuron_ids=(),
            reinforced_motif_neuron_ids=(),
            unresolved_source_indices=(
                experience.unresolved_source_indices
            ),
            work_cells=work_cells,
            reason=reason,
        )

    def observe(
        self,
        experience: (
            AuditoryReceptorExperience
            | AuditoryPreparedPeakExperience
        ),
    ) -> AuditoryMotifObservation:
        if self._ear_ids != ("mono",):
            raise TypeError("binaural auditory peak owner requires observe_binaural")
        experience, atoms, atom_groups, work_cells = self._mono_peak_input(
            experience,
        )
        if (
            len(experience.source_event_receipt_sha256s)
            > AUDITORY_PEAK_RELATION_MAX_SOURCE_EVENTS
        ):
            return self._capacity_result(
                experience,
                work_cells=0,
                reason="source-lineage physical authority exhausted",
            )
        if not _peak_atoms_fit_fraction_authority(
            atoms,
            self._profile,
        ):
            return self._capacity_result(
                experience,
                work_cells=work_cells,
                reason="exact peak Fraction byte authority exhausted",
            )
        if work_cells > self._profile.max_work_cells_per_observation:
            return self._capacity_result(
                experience,
                work_cells=work_cells,
                reason="auditory peak work-cell authority exhausted",
            )
        atoms_by_neuron = dict(atom_groups)
        with self._lock:
            self._require_public_visibility_locked()
            if (
                experience.authority_receipt_sha256
                in self._seen_experience_receipts
            ):
                return AuditoryMotifObservation(
                    state=AuditoryMotifObservationState.DUPLICATE_EXPERIENCE,
                    firing_motif_neuron_ids=(),
                    newly_grown_motif_neuron_ids=(),
                    reinforced_motif_neuron_ids=(),
                    unresolved_source_indices=(
                        experience.unresolved_source_indices
                    ),
                    work_cells=work_cells,
                    reason="source experience already supports the peak bank",
                )
            staged_neurons = dict(self._neurons)
            staged_primed = dict(self._primed)
            new_ids: list[str] = []
            reinforced: list[str] = []
            source_set = set(experience.source_event_receipt_sha256s)
            for neuron_id, neuron_atoms in atom_groups:
                atom = neuron_atoms[0]
                existing = staged_neurons.get(neuron_id)
                if existing is not None:
                    if any(
                        source_set.intersection(
                            witness.source_event_receipt_sha256s
                        )
                        for witness in existing.support_witnesses
                    ):
                        continue
                    staged_neurons[neuron_id] = AuditoryMotifNeuron(
                        neuron_id=existing.neuron_id,
                        lane=existing.lane,
                        relation=existing.relation,
                        support_witnesses=existing.support_witnesses,
                        strength=min(
                            AUDITORY_PEAK_RELATION_COUNTER_MAX,
                            existing.strength + 1,
                        ),
                    )
                    reinforced.append(neuron_id)
                    continue
                prior = staged_primed.get(neuron_id)
                if prior is None:
                    staged_primed[neuron_id] = atom.witness
                    continue
                if source_set.intersection(
                    prior.source_event_receipt_sha256s
                ):
                    continue
                neuron = AuditoryMotifNeuron(
                    neuron_id=neuron_id,
                    lane=atom.witness.lane,
                    relation=atom.witness.relation,
                    support_witnesses=(prior, atom.witness),
                    strength=2,
                )
                neuron.verify()
                staged_neurons[neuron_id] = neuron
                staged_primed.pop(neuron_id)
                new_ids.append(neuron_id)
            if len(staged_neurons) > self._profile.max_motif_neurons:
                return self._capacity_result(
                    experience,
                    work_cells=work_cells,
                    reason="peak-neuron physical allocation exhausted",
                )
            staged_recent = [
                *self._recent_experience_receipts,
                experience.authority_receipt_sha256,
            ][-AUDITORY_PEAK_FADE_LOG_CAPACITY:]
            staged_primed = _retire_primed_experience_cohorts(
                staged_primed,
                chronological_experience_receipts=staged_recent,
                max_pending_experiences=(
                    self._profile.max_pending_experiences
                ),
            )
            fade = _fade_receipt(experience)
            staged_fades = [*self._fade_receipts, fade]
            if len(staged_fades) > AUDITORY_PEAK_FADE_LOG_CAPACITY:
                staged_fades = staged_fades[
                    -AUDITORY_PEAK_FADE_LOG_CAPACITY:
                ]
            encoded = _peak_state_encoded(
                self._profile,
                staged_neurons,
                staged_primed,
                staged_fades,
                min(
                    AUDITORY_PEAK_FADE_TOTAL_MAX,
                    self._fade_total_count + 1,
                ),
                staged_recent,
                self._ear_ids,
            )
            if len(encoded) > self._profile.encoded_state_allocation_bytes:
                return self._capacity_result(
                    experience,
                    work_cells=work_cells,
                    reason="peak-bank canonical-byte allocation exhausted",
                )
            self._neurons = staged_neurons
            self._primed = staged_primed
            self._fade_receipts = staged_fades
            self._fade_total_count = min(
                AUDITORY_PEAK_FADE_TOTAL_MAX,
                self._fade_total_count + 1,
            )
            self._recent_experience_receipts = staged_recent
            self._seen_experience_receipts = set(
                self._recent_experience_receipts
            )
            self._encoded_state_cache = encoded
            firing_ids = tuple(sorted(
                set(atoms_by_neuron).intersection(self._neurons)
            ))
            activations = tuple(
                _peak_activation(self._neurons[neuron_id], atom)
                for neuron_id in firing_ids
                for atom in atoms_by_neuron[neuron_id]
            )
        if self._log_event is not None:
            self._log_event(
                "auditory_peak_experience_faded",
                fade_receipt_sha256=fade,
                source_experience_receipt_sha256=(
                    experience.authority_receipt_sha256
                ),
            )
        return AuditoryMotifObservation(
            state=AuditoryMotifObservationState.OBSERVED,
            firing_motif_neuron_ids=firing_ids,
            newly_grown_motif_neuron_ids=tuple(sorted(new_ids)),
            reinforced_motif_neuron_ids=tuple(sorted(reinforced)),
            unresolved_source_indices=(
                experience.unresolved_source_indices
            ),
            work_cells=work_cells,
            reason=(
                "exact peak-to-peak full-field relations observed; "
                "meaning remains causal and separate"
            ),
            activations=activations,
        )

    def fire(
        self,
        experience: (
            AuditoryReceptorExperience
            | AuditoryPreparedPeakExperience
        ),
    ) -> AuditoryMotifFiring:
        if self._ear_ids != ("mono",):
            raise TypeError("binaural auditory peak owner requires fire_binaural")
        experience, atoms, atom_groups, work_cells = self._mono_peak_input(
            experience
        )
        if not _peak_atoms_fit_fraction_authority(
            atoms,
            self._profile,
        ):
            return AuditoryMotifFiring(
                state=AuditoryMotifObservationState.INDETERMINATE_RESOURCE,
                firing_motif_neuron_ids=(),
                unresolved_source_indices=(
                    experience.unresolved_source_indices
                ),
                work_cells=work_cells,
                reason="exact peak Fraction byte authority exhausted",
            )
        if work_cells > self._profile.max_work_cells_per_observation:
            return AuditoryMotifFiring(
                state=AuditoryMotifObservationState.INDETERMINATE_RESOURCE,
                firing_motif_neuron_ids=(),
                unresolved_source_indices=(
                    experience.unresolved_source_indices
                ),
                work_cells=work_cells,
                reason="auditory peak work-cell authority exhausted",
            )
        atoms_by_neuron = dict(atom_groups)
        with self._lock:
            self._require_public_visibility_locked()
            firing_ids = tuple(sorted(
                set(atoms_by_neuron).intersection(self._neurons)
            ))
            activations = tuple(
                _peak_activation(self._neurons[neuron_id], atom)
                for neuron_id in firing_ids
                for atom in atoms_by_neuron[neuron_id]
            )
        return AuditoryMotifFiring(
            state=AuditoryMotifObservationState.OBSERVED,
            firing_motif_neuron_ids=firing_ids,
            unresolved_source_indices=(
                experience.unresolved_source_indices
            ),
            work_cells=work_cells,
            reason=(
                "indexed exact peak-to-peak field neurons fired; no score, "
                "threshold, label, or learning was applied"
            ),
            activations=activations,
        )

    def discard_prepared(
        self,
        prepared: AuditoryPreparedPeakExperience,
    ) -> bool:
        if not isinstance(prepared, AuditoryPreparedPeakExperience):
            raise TypeError("auditory prepared peak discard is not typed")
        with self._lock:
            self._require_public_visibility_locked()
            if self._prepared_peak is prepared:
                self._prepared_peak = None
                return True
            if self._prepared_peak is not None:
                raise ValueError(
                    "another prepared auditory peak owns request custody"
                )
            return False

    def _binaural_state_locked(self) -> _BinauralMotifOwnerState:
        return _BinauralMotifOwnerState(
            neurons=tuple(self._neurons.items()),
            primed=tuple(self._primed.items()),
            fade_receipts=tuple(self._fade_receipts),
            fade_total_count=self._fade_total_count,
            recent_experience_receipts=tuple(
                self._recent_experience_receipts
            ),
            seen_experience_receipts=frozenset(
                self._seen_experience_receipts
            ),
            encoded_state_cache=self._encoded_state_cache,
        )

    def _install_binaural_state_locked(
        self,
        state: _BinauralMotifOwnerState,
    ) -> None:
        self._neurons = dict(state.neurons)
        self._primed = dict(state.primed)
        self._fade_receipts = list(state.fade_receipts)
        self._fade_total_count = state.fade_total_count
        self._recent_experience_receipts = list(
            state.recent_experience_receipts
        )
        self._seen_experience_receipts = set(
            state.seen_experience_receipts
        )
        self._encoded_state_cache = state.encoded_state_cache

    def _stage_binaural_observation_locked(
        self,
        settlement,
        observation: AuditoryMotifObservation,
        *,
        prior_state: _BinauralMotifOwnerState,
        staged_state: _BinauralMotifOwnerState,
        event: tuple[str, tuple[tuple[str, object], ...]] | None,
    ) -> PreparedAuditoryBinauralMotifObservation:
        result = self._binaural_observation(settlement, observation)
        result.verify()
        return PreparedAuditoryBinauralMotifObservation(
            observation=result,
            _prior_state=prior_state,
            _staged_state=staged_state,
            _event=event,
            _construction_authority=(
                _PREPARED_BINAURAL_MOTIF_AUTHORITY
            ),
        )

    def _require_prepared_binaural_locked(
        self,
        prepared: PreparedAuditoryBinauralMotifObservation,
    ) -> PreparedAuditoryBinauralMotifObservation:
        self._require_public_visibility_locked()
        if (
            not isinstance(
                prepared,
                PreparedAuditoryBinauralMotifObservation,
            )
            or prepared._construction_authority
            is not _PREPARED_BINAURAL_MOTIF_AUTHORITY
            or self._prepared_binaural is not prepared
        ):
            raise ValueError(
                "prepared binaural motif observation changed custody"
            )
        prepared.observation.verify()
        return prepared

    def prepare_binaural(
        self,
        settlement,
    ) -> PreparedAuditoryBinauralMotifObservation:
        """Stage one two-ear sensory-learning mutation without publishing it."""

        from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
            W1BinauralReceptorSettlement,
        )

        if not isinstance(settlement, W1BinauralReceptorSettlement):
            raise TypeError("binaural peak observation requires W1 settlement")
        settlement.verify()
        if self._ear_ids != ("left", "right"):
            raise TypeError("mono auditory peak owner cannot observe binaural")
        with self._lock:
            self._require_public_visibility_locked()
            if self._prepared_binaural is not None:
                raise AuditoryMotifCapacityError(
                    "binaural auditory peak observation is already prepared"
                )
            prepared = self._prepare_binaural_locked(settlement)
            self._prepared_binaural = prepared
            return prepared

    def _prepare_binaural_locked(
        self,
        settlement,
    ) -> PreparedAuditoryBinauralMotifObservation:
        prior_state = self._binaural_state_locked()
        source_receipt = settlement.authority_receipt_sha256
        atoms = tuple(
            atom
            for ear in settlement.ears
            for atom in _peak_atoms_from_experience(
                ear.experience,
                ear_id=ear.ear_id,
                source_episode_receipt_sha256=source_receipt,
            )
        )
        work_cells = sum(
            len(ear.experience.occurrences)
            * 2
            * len(DSF_FIELD_ORDER)
            for ear in settlement.ears
        ) + len(atoms)
        unresolved = tuple(sorted({
            value
            for ear in settlement.ears
            for value in ear.experience.unresolved_source_indices
        }))
        if not _peak_atoms_fit_fraction_authority(
            atoms,
            self._profile,
        ):
            observation = AuditoryMotifObservation(
                state=AuditoryMotifObservationState.INDETERMINATE_RESOURCE,
                firing_motif_neuron_ids=(),
                newly_grown_motif_neuron_ids=(),
                reinforced_motif_neuron_ids=(),
                unresolved_source_indices=unresolved,
                work_cells=work_cells,
                reason="binaural exact peak Fraction byte authority exhausted",
            )
            return self._stage_binaural_observation_locked(
                settlement,
                observation,
                prior_state=prior_state,
                staged_state=prior_state,
                event=None,
            )
        if work_cells > self._profile.max_work_cells_per_observation:
            observation = AuditoryMotifObservation(
                state=AuditoryMotifObservationState.INDETERMINATE_RESOURCE,
                firing_motif_neuron_ids=(),
                newly_grown_motif_neuron_ids=(),
                reinforced_motif_neuron_ids=(),
                unresolved_source_indices=unresolved,
                work_cells=work_cells,
                reason="binaural auditory peak work authority exhausted",
            )
            return self._stage_binaural_observation_locked(
                settlement,
                observation,
                prior_state=prior_state,
                staged_state=prior_state,
                event=None,
            )
        first_atom: dict[str, _PeakAtom] = {}
        atoms_by_neuron: dict[str, list[_PeakAtom]] = {}
        for atom in atoms:
            first_atom.setdefault(atom.neuron_id, atom)
            atoms_by_neuron.setdefault(atom.neuron_id, []).append(atom)
        with self._lock:
            if source_receipt in self._seen_experience_receipts:
                observation = AuditoryMotifObservation(
                    state=AuditoryMotifObservationState.DUPLICATE_EXPERIENCE,
                    firing_motif_neuron_ids=(),
                    newly_grown_motif_neuron_ids=(),
                    reinforced_motif_neuron_ids=(),
                    unresolved_source_indices=unresolved,
                    work_cells=work_cells,
                    reason="W1 settlement already supports the peak bank",
                )
                return self._stage_binaural_observation_locked(
                    settlement,
                    observation,
                    prior_state=prior_state,
                    staged_state=prior_state,
                    event=None,
                )
            staged_neurons = dict(self._neurons)
            staged_primed = dict(self._primed)
            new_ids: list[str] = []
            reinforced: list[str] = []
            for neuron_id, atom in first_atom.items():
                existing = staged_neurons.get(neuron_id)
                if existing is not None:
                    if any(
                        witness.source_experience_receipt_sha256
                        == source_receipt
                        for witness in existing.support_witnesses
                    ):
                        continue
                    staged_neurons[neuron_id] = AuditoryMotifNeuron(
                        neuron_id=existing.neuron_id,
                        lane=existing.lane,
                        relation=existing.relation,
                        support_witnesses=existing.support_witnesses,
                        strength=min(
                            AUDITORY_PEAK_RELATION_COUNTER_MAX,
                            existing.strength + 1,
                        ),
                    )
                    reinforced.append(neuron_id)
                    continue
                prior = staged_primed.get(neuron_id)
                if prior is None:
                    staged_primed[neuron_id] = atom.witness
                    continue
                if (
                    prior.source_experience_receipt_sha256
                    == source_receipt
                ):
                    continue
                neuron = AuditoryMotifNeuron(
                    neuron_id=neuron_id,
                    lane=atom.witness.lane,
                    relation=atom.witness.relation,
                    support_witnesses=(prior, atom.witness),
                    strength=2,
                )
                neuron.verify()
                staged_neurons[neuron_id] = neuron
                staged_primed.pop(neuron_id)
                new_ids.append(neuron_id)
            if len(staged_neurons) > self._profile.max_motif_neurons:
                observation = AuditoryMotifObservation(
                    state=AuditoryMotifObservationState.INDETERMINATE_RESOURCE,
                    firing_motif_neuron_ids=(),
                    newly_grown_motif_neuron_ids=(),
                    reinforced_motif_neuron_ids=(),
                    unresolved_source_indices=unresolved,
                    work_cells=work_cells,
                    reason="binaural peak-neuron allocation exhausted",
                )
                return self._stage_binaural_observation_locked(
                    settlement,
                    observation,
                    prior_state=prior_state,
                    staged_state=prior_state,
                    event=None,
                )
            fade = _digest({
                "distillation": (
                    "both_ears_peak_cells_extracted_before_raw_release"
                ),
                "schema": AUDITORY_PEAK_FADE_SCHEMA,
                "source_settlement_receipt_sha256": source_receipt,
            })
            staged_fades = [
                *self._fade_receipts,
                fade,
            ][-AUDITORY_PEAK_FADE_LOG_CAPACITY:]
            staged_recent = [
                *self._recent_experience_receipts,
                source_receipt,
            ][-AUDITORY_PEAK_FADE_LOG_CAPACITY:]
            staged_primed = _retire_primed_experience_cohorts(
                staged_primed,
                chronological_experience_receipts=staged_recent,
                max_pending_experiences=(
                    self._profile.max_pending_experiences
                ),
            )
            encoded = _peak_state_encoded(
                self._profile,
                staged_neurons,
                staged_primed,
                staged_fades,
                min(
                    AUDITORY_PEAK_FADE_TOTAL_MAX,
                    self._fade_total_count + 1,
                ),
                staged_recent,
                self._ear_ids,
            )
            if len(encoded) > self._profile.encoded_state_allocation_bytes:
                observation = AuditoryMotifObservation(
                    state=AuditoryMotifObservationState.INDETERMINATE_RESOURCE,
                    firing_motif_neuron_ids=(),
                    newly_grown_motif_neuron_ids=(),
                    reinforced_motif_neuron_ids=(),
                    unresolved_source_indices=unresolved,
                    work_cells=work_cells,
                    reason="binaural peak canonical-byte allocation exhausted",
                )
                return self._stage_binaural_observation_locked(
                    settlement,
                    observation,
                    prior_state=prior_state,
                    staged_state=prior_state,
                    event=None,
                )
            staged_fade_total_count = min(
                AUDITORY_PEAK_FADE_TOTAL_MAX,
                self._fade_total_count + 1,
            )
            firing_ids = tuple(sorted(
                set(atoms_by_neuron).intersection(staged_neurons)
            ))
            activations = tuple(
                _peak_activation(staged_neurons[neuron_id], atom)
                for neuron_id in firing_ids
                for atom in atoms_by_neuron[neuron_id]
            )
            staged_state = _BinauralMotifOwnerState(
                neurons=tuple(staged_neurons.items()),
                primed=tuple(staged_primed.items()),
                fade_receipts=tuple(staged_fades),
                fade_total_count=staged_fade_total_count,
                recent_experience_receipts=tuple(staged_recent),
                seen_experience_receipts=frozenset(staged_recent),
                encoded_state_cache=encoded,
            )
        observation = AuditoryMotifObservation(
            state=AuditoryMotifObservationState.OBSERVED,
            firing_motif_neuron_ids=firing_ids,
            newly_grown_motif_neuron_ids=tuple(sorted(new_ids)),
            reinforced_motif_neuron_ids=tuple(sorted(reinforced)),
            unresolved_source_indices=unresolved,
            work_cells=work_cells,
            reason=(
                "both ears observed atomically as one exact W1 peak episode"
            ),
            activations=activations,
        )
        return self._stage_binaural_observation_locked(
            settlement,
            observation,
            prior_state=prior_state,
            staged_state=staged_state,
            event=(
                "auditory_binaural_peak_experience_faded",
                (
                    ("fade_receipt_sha256", fade),
                    (
                        "source_settlement_receipt_sha256",
                        source_receipt,
                    ),
                ),
            ),
        )

    def commit_prepared_binaural(
        self,
        prepared: PreparedAuditoryBinauralMotifObservation,
    ) -> AuditoryBinauralMotifCommitUndo:
        """Publish one verified staged observation and return exact undo."""

        with self._lock:
            current = self._require_prepared_binaural_locked(prepared)
            if self._binaural_state_locked() != current._prior_state:
                raise RuntimeError(
                    "prepared binaural motif owner state changed before commit"
                )
            undo = AuditoryBinauralMotifCommitUndo(prepared=current)
            if current._event is not None and self._log_event is not None:
                event_name, event_fields = current._event
                self._log_event(event_name, **dict(event_fields))
            try:
                self._install_binaural_state_locked(
                    current._staged_state
                )
            except BaseException:
                self._install_binaural_state_locked(current._prior_state)
                raise
            self._prepared_binaural = None
            return undo

    def preverify_binaural_visibility_install(
        self,
        prepared: PreparedAuditoryBinauralMotifObservation,
    ) -> AuditoryBinauralMotifVisibilityInstall:
        """Allocate and verify every staged object before world commit."""

        with self._lock:
            current = self._require_prepared_binaural_locked(prepared)
            if self._binaural_state_locked() != current._prior_state:
                raise RuntimeError(
                    "prepared binaural motif owner state changed"
                )
            staged = current._staged_state
            return AuditoryBinauralMotifVisibilityInstall(
                _prepared=current,
                _neurons=dict(staged.neurons),
                _primed=dict(staged.primed),
                _fade_receipts=list(staged.fade_receipts),
                _fade_total_count=staged.fade_total_count,
                _recent_experience_receipts=list(
                    staged.recent_experience_receipts
                ),
                _seen_experience_receipts=set(
                    staged.seen_experience_receipts
                ),
                _encoded_state_cache=staged.encoded_state_cache,
                _owner_authority=self._visibility_owner_authority,
                _construction_authority=(
                    _BINAURAL_VISIBILITY_AUTHORITY
                ),
            )

    @contextmanager
    def binaural_visibility_transaction(
        self,
        install: AuditoryBinauralMotifVisibilityInstall,
    ):
        """Hide the physical/sensory boundary from public readers."""

        with self._lock:
            self._require_public_visibility_locked()
            if (
                not isinstance(
                    install,
                    AuditoryBinauralMotifVisibilityInstall,
                )
                or install._construction_authority
                is not _BINAURAL_VISIBILITY_AUTHORITY
                or install._owner_authority
                is not self._visibility_owner_authority
                or self._visibility_install is not None
                or self._prepared_binaural is not install._prepared
                or self._binaural_state_locked()
                != install._prepared._prior_state
            ):
                raise ValueError(
                    "binaural motif visibility install changed custody"
                )
            self._visibility_install = install
            installed = [False]

            def install_now() -> AuditoryBinauralMotifCommitUndo:
                assert self._visibility_install is install
                assert not installed[0]
                undo = AuditoryBinauralMotifCommitUndo(
                    prepared=install._prepared
                )
                self._neurons = install._neurons
                self._primed = install._primed
                self._fade_receipts = install._fade_receipts
                self._fade_total_count = install._fade_total_count
                self._recent_experience_receipts = (
                    install._recent_experience_receipts
                )
                self._seen_experience_receipts = (
                    install._seen_experience_receipts
                )
                self._encoded_state_cache = (
                    install._encoded_state_cache
                )
                self._prepared_binaural = None
                installed[0] = True
                return undo

            try:
                yield install_now
            finally:
                self._visibility_install = None

    @contextmanager
    def committed_binaural_rollback_transaction(
        self,
        undo: AuditoryBinauralMotifCommitUndo,
    ):
        """Hold public visibility while one current binaural tail is undone."""

        if not isinstance(undo, AuditoryBinauralMotifCommitUndo):
            raise TypeError(
                "binaural motif rollback authority is not typed"
            )
        prepared = undo.prepared
        if (
            not isinstance(
                prepared,
                PreparedAuditoryBinauralMotifObservation,
            )
            or prepared._construction_authority
            is not _PREPARED_BINAURAL_MOTIF_AUTHORITY
        ):
            raise ValueError(
                "binaural motif rollback authority changed"
            )
        with self._lock:
            self._require_public_visibility_locked()
            if (
                self._prepared_binaural is not None
                or self._binaural_state_locked()
                != prepared._staged_state
            ):
                raise ValueError(
                    "committed binaural motif owner state changed"
                )
            rolled_back = [False]
            self._visibility_rollback = undo

            def rollback_now() -> None:
                assert not rolled_back[0]
                self._install_binaural_state_locked(
                    prepared._prior_state
                )
                rolled_back[0] = True

            try:
                yield rollback_now
            finally:
                self._visibility_rollback = None

    def rollback_committed_binaural(
        self,
        undo: AuditoryBinauralMotifCommitUndo,
    ) -> None:
        """Restore all seven fields and reopen the exact preparation."""

        if not isinstance(undo, AuditoryBinauralMotifCommitUndo):
            raise TypeError("binaural motif rollback authority is not typed")
        prepared = undo.prepared
        if (
            not isinstance(
                prepared,
                PreparedAuditoryBinauralMotifObservation,
            )
            or prepared._construction_authority
            is not _PREPARED_BINAURAL_MOTIF_AUTHORITY
        ):
            raise ValueError("binaural motif rollback authority changed")
        with self._lock:
            self._require_public_visibility_locked()
            if self._prepared_binaural is not None:
                raise RuntimeError(
                    "binaural motif owner already has a preparation"
                )
            if self._binaural_state_locked() != prepared._staged_state:
                raise ValueError(
                    "committed binaural motif owner state changed"
                )
            try:
                self._install_binaural_state_locked(
                    prepared._prior_state
                )
            except BaseException:
                self._install_binaural_state_locked(
                    prepared._staged_state
                )
                raise
            self._prepared_binaural = prepared

    def discard_prepared_binaural(
        self,
        prepared: PreparedAuditoryBinauralMotifObservation,
    ) -> None:
        """Release one staged observation without changing sensory learning."""

        with self._lock:
            self._require_prepared_binaural_locked(prepared)
            self._prepared_binaural = None

    def observe_binaural(
        self,
        settlement,
    ) -> AuditoryBinauralMotifObservation:
        """Preserve immediate observation through the prepared transaction."""

        with self._lock:
            prepared = self.prepare_binaural(settlement)
            try:
                self.commit_prepared_binaural(prepared)
            except BaseException:
                if self._prepared_binaural is prepared:
                    self.discard_prepared_binaural(prepared)
                raise
            return prepared.observation

    def fire_binaural(
        self,
        settlement,
    ) -> AuditoryBinauralMotifFiring:
        """Fire both ear banks atomically without learning."""

        from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
            W1BinauralReceptorSettlement,
        )

        if not isinstance(settlement, W1BinauralReceptorSettlement):
            raise TypeError("binaural peak firing requires W1 settlement")
        settlement.verify()
        if self._ear_ids != ("left", "right"):
            raise TypeError("mono auditory peak owner cannot fire binaural")
        atoms = tuple(
            atom
            for ear in settlement.ears
            for atom in _peak_atoms_from_experience(
                ear.experience,
                ear_id=ear.ear_id,
                source_episode_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
            )
        )
        work_cells = sum(
            len(ear.experience.occurrences)
            * 2
            * len(DSF_FIELD_ORDER)
            for ear in settlement.ears
        ) + len(atoms)
        unresolved = tuple(sorted({
            value
            for ear in settlement.ears
            for value in ear.experience.unresolved_source_indices
        }))
        if not _peak_atoms_fit_fraction_authority(
            atoms,
            self._profile,
        ):
            firing = AuditoryMotifFiring(
                state=AuditoryMotifObservationState.INDETERMINATE_RESOURCE,
                firing_motif_neuron_ids=(),
                unresolved_source_indices=unresolved,
                work_cells=work_cells,
                reason="binaural exact peak Fraction byte authority exhausted",
            )
            return self._binaural_firing(settlement, firing)
        if work_cells > self._profile.max_work_cells_per_observation:
            firing = AuditoryMotifFiring(
                state=AuditoryMotifObservationState.INDETERMINATE_RESOURCE,
                firing_motif_neuron_ids=(),
                unresolved_source_indices=unresolved,
                work_cells=work_cells,
                reason="binaural auditory peak work authority exhausted",
            )
            return self._binaural_firing(settlement, firing)
        atoms_by_neuron: dict[str, list[_PeakAtom]] = {}
        for atom in atoms:
            atoms_by_neuron.setdefault(atom.neuron_id, []).append(atom)
        with self._lock:
            self._require_public_visibility_locked()
            firing_ids = tuple(sorted(
                set(atoms_by_neuron).intersection(self._neurons)
            ))
            activations = tuple(
                _peak_activation(self._neurons[neuron_id], atom)
                for neuron_id in firing_ids
                for atom in atoms_by_neuron[neuron_id]
            )
        firing = AuditoryMotifFiring(
            state=AuditoryMotifObservationState.OBSERVED,
            firing_motif_neuron_ids=firing_ids,
            unresolved_source_indices=unresolved,
            work_cells=work_cells,
            reason="both exact W1 ear q banks fired atomically",
            activations=activations,
        )
        return self._binaural_firing(settlement, firing)

    def _binaural_firing(
        self,
        settlement,
        firing: AuditoryMotifFiring,
    ) -> AuditoryBinauralMotifFiring:
        provisional = AuditoryBinauralMotifFiring(
            source_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            ear_ids=("left", "right"),
            firing=firing,
            authority_receipt_sha256="0" * 64,
        )
        result = replace(
            provisional,
            authority_receipt_sha256=_digest(provisional.payload()),
        )
        result.verify()
        return result

    def _binaural_observation(
        self,
        settlement,
        observation: AuditoryMotifObservation,
    ) -> AuditoryBinauralMotifObservation:
        provisional = AuditoryBinauralMotifObservation(
            source_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            ear_ids=("left", "right"),
            observation=observation,
            authority_receipt_sha256="0" * 64,
        )
        result = replace(
            provisional,
            authority_receipt_sha256=_digest(provisional.payload()),
        )
        result.verify()
        return result

    def status(self) -> dict[str, object]:
        with self._lock:
            self._require_public_visibility_locked()
            encoded = self._encoded_state_cache
            if encoded is None:
                encoded = _peak_state_encoded(
                    self._profile,
                    self._neurons,
                    self._primed,
                    self._fade_receipts,
                    self._fade_total_count,
                    self._recent_experience_receipts,
                    self._ear_ids,
                )
                if self._prepared_binaural is None:
                    self._encoded_state_cache = encoded
            used = len(encoded)
            return {
                "canonical_state_allocation_bytes": (
                    self._profile.encoded_state_allocation_bytes
                ),
                "canonical_state_remaining_bytes": (
                    self._profile.encoded_state_allocation_bytes - used
                ),
                "canonical_state_used_bytes": used,
                "fade_receipt_counter_saturated": (
                    self._fade_total_count
                    == AUDITORY_PEAK_FADE_TOTAL_MAX
                ),
                "fade_receipt_count": len(self._fade_receipts),
                "fade_receipt_eviction_count": max(
                    0,
                    self._fade_total_count - len(self._fade_receipts),
                ),
                "fade_total_count": self._fade_total_count,
                "motif_neuron_count": len(self._neurons),
                "pending_peak_cell_count": len(self._primed),
                "prepared_peak_request_count": int(
                    self._prepared_peak is not None
                ),
                "prepared_binaural_observation_count": int(
                    self._prepared_binaural is not None
                ),
                "physical_peak_cell_count": (
                    AUDITORY_PEAK_RELATION_CELL_COUNT
                    * len(self._ear_ids)
                ),
                "schema": (
                    "guala.auditory.peak_relation_bank_status.v1"
                ),
            }

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            self._require_public_visibility_locked()
            if self._prepared_peak is not None:
                raise RuntimeError(
                    "auditory peak state has a live prepared request"
                )
            encoded = self._encoded_state_cache
            if encoded is None:
                encoded = _peak_state_encoded(
                    self._profile,
                    self._neurons,
                    self._primed,
                    self._fade_receipts,
                    self._fade_total_count,
                    self._recent_experience_receipts,
                    self._ear_ids,
                )
                if self._prepared_binaural is None:
                    self._encoded_state_cache = encoded
        if len(encoded) > self._profile.encoded_state_allocation_bytes:
            raise AuditoryMotifCapacityError(
                "auditory peak state exceeds its physical allocation"
            )
        return encoded

    @classmethod
    def restore_encoded(
        cls,
        encoded: bytes,
    ) -> "AuditoryRecurrentMotifOwner":
        if not isinstance(encoded, bytes):
            raise TypeError("auditory peak state must be immutable bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("auditory peak state is not JSON") from exc
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {"body", "body_sha256"}
            or not isinstance(envelope["body"], dict)
            or _digest(envelope["body"]) != envelope["body_sha256"]
            or _canonical_bytes(envelope) != encoded
        ):
            raise ValueError("auditory peak state seal changed")
        body = envelope["body"]
        if body.get("schema") != AUDITORY_RECURRENT_MOTIF_STATE_SCHEMA:
            raise ValueError("auditory peak state schema changed")
        raw_profile = body.get("resource_profile")
        if not isinstance(raw_profile, dict):
            raise ValueError("auditory peak resource profile is absent")
        profile = AuditoryMotifResourceProfile(
            profile_id=raw_profile.get("profile_id"),
            ear_count=raw_profile.get("ear_count"),
            max_motif_neurons=raw_profile.get("max_motif_neurons"),
            max_pending_experiences=raw_profile.get(
                "max_pending_experiences"
            ),
            max_work_cells_per_observation=raw_profile.get(
                "max_work_cells_per_observation"
            ),
            max_exact_fraction_text_bytes=raw_profile.get(
                "max_exact_fraction_text_bytes"
            ),
            max_encoded_state_bytes=raw_profile.get(
                "max_encoded_state_bytes"
            ),
            encoded_state_allocation_bytes=raw_profile.get(
                "encoded_state_allocation_bytes"
            ),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        profile.verify()
        if len(encoded) > profile.encoded_state_allocation_bytes:
            raise ValueError("auditory peak state exceeds receipted allocation")
        raw_neurons = body.get("motif_neurons")
        raw_primed = body.get("primed_cells")
        raw_fades = body.get("fade_receipts")
        raw_fade_total = body.get("fade_total_count")
        raw_recent = body.get("recent_experience_receipts")
        raw_ear_ids = body.get("ear_ids")
        if (
            not isinstance(raw_neurons, list)
            or not isinstance(raw_primed, list)
            or not isinstance(raw_fades, list)
            or isinstance(raw_fade_total, bool)
            or not isinstance(raw_fade_total, int)
            or not 0 <= raw_fade_total <= AUDITORY_PEAK_FADE_TOTAL_MAX
            or not isinstance(raw_recent, list)
            or not isinstance(raw_ear_ids, list)
            or len(raw_neurons) > profile.max_motif_neurons
            or len(raw_fades) > AUDITORY_PEAK_FADE_LOG_CAPACITY
            or len(raw_recent) > AUDITORY_PEAK_FADE_LOG_CAPACITY
            or raw_fade_total < len(raw_fades)
            or (
                raw_fade_total < AUDITORY_PEAK_FADE_LOG_CAPACITY
                and raw_fade_total != len(raw_fades)
            )
            or (
                raw_fade_total >= AUDITORY_PEAK_FADE_LOG_CAPACITY
                and len(raw_fades) != AUDITORY_PEAK_FADE_LOG_CAPACITY
            )
        ):
            raise ValueError("auditory peak state collections changed")
        owner = cls(profile, ear_ids=tuple(raw_ear_ids))
        for raw in raw_neurons:
            if (
                not isinstance(raw, dict)
                or not isinstance(raw.get("support_witnesses"), list)
                or len(raw["support_witnesses"]) != 2
            ):
                raise ValueError("auditory peak neuron record changed")
            witnesses = tuple(
                _witness_from_record(value)
                for value in raw["support_witnesses"]
            )
            neuron = AuditoryMotifNeuron(
                neuron_id=raw.get("neuron_id"),
                lane=witnesses[0].lane,
                relation=witnesses[0].relation,
                support_witnesses=witnesses,
                strength=raw.get("strength"),
            )
            neuron.verify()
            if neuron.lane.ear_id not in owner._ear_ids:
                raise ValueError("auditory peak neuron left owner ear topology")
            if any(
                not _witness_fits_fraction_authority(value, profile)
                for value in neuron.support_witnesses
            ):
                raise ValueError(
                    "auditory peak neuron exceeds Fraction byte authority"
                )
            if neuron.neuron_id in owner._neurons:
                raise ValueError("auditory peak neuron is duplicated")
            owner._neurons[neuron.neuron_id] = neuron
        for raw in raw_primed:
            if not isinstance(raw, dict):
                raise ValueError("primed auditory peak cell changed")
            witness = _witness_from_record(raw.get("witness"))
            if witness.lane.ear_id not in owner._ear_ids:
                raise ValueError("primed peak cell left owner ear topology")
            if not _witness_fits_fraction_authority(witness, profile):
                raise ValueError(
                    "primed peak cell exceeds Fraction byte authority"
                )
            neuron_id = raw.get("neuron_id")
            if (
                neuron_id != _peak_neuron_id(
                    witness.lane,
                    witness.relation,
                )
                or neuron_id in owner._neurons
                or neuron_id in owner._primed
            ):
                raise ValueError("primed auditory peak cell changed")
            owner._primed[neuron_id] = witness
        owner._seen_experience_receipts = {
            witness.source_experience_receipt_sha256
            for witness in (
                *owner._primed.values(),
                *(
                    item
                    for neuron in owner._neurons.values()
                    for item in neuron.support_witnesses
                ),
            )
        }
        owner._fade_receipts = [
            _require_sha256(value, "auditory peak fade")
            for value in raw_fades
        ]
        owner._fade_total_count = raw_fade_total
        owner._recent_experience_receipts = [
            _require_sha256(value, "recent auditory peak experience")
            for value in raw_recent
        ]
        if len(set(owner._recent_experience_receipts)) != len(
            owner._recent_experience_receipts
        ):
            raise ValueError("recent auditory peak experience is duplicated")
        if (
            owner.pending_experience_count
            > profile.max_pending_experiences
        ):
            raise ValueError(
                "primed auditory experiences exceed receipted capacity"
            )
        owner._seen_experience_receipts = set(
            owner._recent_experience_receipts
        )
        if owner.snapshot_encoded() != encoded:
            raise ValueError("auditory peak cold state changed")
        return owner


def migrate_immediately_prior_motif_profile(
    encoded: bytes,
) -> AuditoryRecurrentMotifOwner:
    """Reissue one authenticated prior-profile payload under current bounds."""

    if not isinstance(encoded, bytes):
        raise TypeError("prior auditory peak state must be immutable bytes")
    try:
        envelope = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("prior auditory peak state is not JSON") from exc
    if (
        not isinstance(envelope, dict)
        or set(envelope) != {"body", "body_sha256"}
        or not isinstance(envelope.get("body"), dict)
        or _canonical_bytes(envelope) != encoded
        or _digest(envelope["body"]) != envelope.get("body_sha256")
    ):
        raise ValueError("prior auditory peak state seal changed")
    body = envelope["body"]
    if body.get("schema") != AUDITORY_RECURRENT_MOTIF_STATE_SCHEMA:
        raise ValueError("prior auditory peak state schema changed")
    raw_profile = body.get("resource_profile")
    expected_profile_fields = {
        "authority_receipt_sha256",
        "derivation",
        "ear_count",
        "encoded_state_allocation_bytes",
        "max_encoded_state_bytes",
        "max_exact_fraction_text_bytes",
        "max_motif_neurons",
        "max_pending_experiences",
        "max_work_cells_per_observation",
        "physical_frame_bound",
        "profile_id",
        "schema",
    }
    if (
        not isinstance(raw_profile, dict)
        or set(raw_profile) != expected_profile_fields
    ):
        raise ValueError("prior auditory motif profile shape changed")
    integer_fields = (
        "ear_count",
        "encoded_state_allocation_bytes",
        "max_encoded_state_bytes",
        "max_exact_fraction_text_bytes",
        "max_motif_neurons",
        "max_pending_experiences",
        "max_work_cells_per_observation",
        "physical_frame_bound",
    )
    if any(
        isinstance(raw_profile.get(name), bool)
        or not isinstance(raw_profile.get(name), int)
        or raw_profile[name] <= 0
        for name in integer_fields
    ):
        raise ValueError("prior auditory motif profile capacity changed")
    ear_count = raw_profile["ear_count"]
    expected_cells = AUDITORY_PEAK_RELATION_CELL_COUNT * ear_count
    prior_maximum = _immediately_prior_worst_case_encoded_bytes(
        ear_count=ear_count,
        max_exact_fraction_text_bytes=(
            raw_profile["max_exact_fraction_text_bytes"]
        ),
    )
    prior_payload = {
        "derivation": _IMMEDIATELY_PRIOR_RESOURCE_DERIVATION,
        "max_encoded_state_bytes": prior_maximum,
        "encoded_state_allocation_bytes": (
            raw_profile["encoded_state_allocation_bytes"]
        ),
        "ear_count": ear_count,
        "max_motif_neurons": raw_profile["max_motif_neurons"],
        "max_pending_experiences": (
            raw_profile["max_pending_experiences"]
        ),
        "max_exact_fraction_text_bytes": (
            raw_profile["max_exact_fraction_text_bytes"]
        ),
        "max_work_cells_per_observation": (
            raw_profile["max_work_cells_per_observation"]
        ),
        "physical_frame_bound": MAX_AUDITORY_RECEPTOR_FRAMES,
        "profile_id": raw_profile["profile_id"],
        "schema": AUDITORY_MOTIF_RESOURCE_PROFILE_SCHEMA,
    }
    if (
        ear_count not in (1, 2)
        or raw_profile["max_motif_neurons"] != expected_cells
        or raw_profile["encoded_state_allocation_bytes"] > prior_maximum
        or raw_profile
        != (
            prior_payload
            | {
                "authority_receipt_sha256": _digest(prior_payload),
            }
        )
    ):
        raise ValueError(
            "auditory motif state is not the immediately prior profile"
        )
    current_profile = AuditoryMotifResourceProfile.create(
        profile_id=raw_profile["profile_id"],
        ear_count=ear_count,
        max_motif_neurons=raw_profile["max_motif_neurons"],
        max_pending_experiences=(
            raw_profile["max_pending_experiences"]
        ),
        max_work_cells_per_observation=(
            raw_profile["max_work_cells_per_observation"]
        ),
        max_exact_fraction_text_bytes=(
            raw_profile["max_exact_fraction_text_bytes"]
        ),
        encoded_state_allocation_bytes=(
            raw_profile["encoded_state_allocation_bytes"]
        ),
    )
    migrated_body = json.loads(_canonical_bytes(body))
    migrated_body["resource_profile"] = (
        current_profile.payload()
        | {
            "authority_receipt_sha256": (
                current_profile.authority_receipt_sha256
            ),
        }
    )
    migrated_encoded = _canonical_bytes({
        "body": migrated_body,
        "body_sha256": _digest(migrated_body),
    })
    owner = AuditoryRecurrentMotifOwner.restore_encoded(migrated_encoded)
    restored_body = json.loads(owner.snapshot_encoded())["body"]
    if {
        key: value
        for key, value in restored_body.items()
        if key != "resource_profile"
    } != {
        key: value
        for key, value in body.items()
        if key != "resource_profile"
    }:
        raise RuntimeError(
            "auditory motif profile migration changed learned state"
        )
    return owner


__all__ = (
    "AUDITORY_FULL_FIELD_RANK_SCHEMA",
    "AUDITORY_MOTIF_RESOURCE_PROFILE_SCHEMA",
    "AUDITORY_PEAK_RELATION_CELL_COUNT",
    "AUDITORY_PEAK_RELATION_COUNTER_MAX",
    "AUDITORY_PEAK_RELATION_LANE_COUNT",
    "AUDITORY_RECEPTOR_OCCURRENCE_SCHEMA",
    "AUDITORY_RECEPTOR_EXPERIENCE_SCHEMA",
    "AUDITORY_RECEPTOR_EXPERIENCE_COMPOSITION_OPERATOR",
    "AUDITORY_RECURRENT_MOTIF_OPERATOR",
    "AUDITORY_RECURRENT_MOTIF_SCHEMA",
    "AuditoryMotifCapacityError",
    "AuditoryBinauralMotifFiring",
    "AuditoryBinauralMotifCommitUndo",
    "AuditoryBinauralMotifVisibilityInstall",
    "AuditoryBinauralMotifObservation",
    "AuditoryMotifFiring",
    "AuditoryMotifNeuron",
    "AuditoryMotifObservation",
    "AuditoryMotifObservationState",
    "AuditoryMotifResourceProfile",
    "AuditoryPeakLane",
    "AuditoryPeakPoint",
    "AuditoryPeakRelation",
    "AuditoryPeakWitness",
    "AuditoryPreparedPeakExperience",
    "PreparedAuditoryBinauralMotifObservation",
    "AuditoryReceptorExperience",
    "AuditoryReceptorIdentity",
    "AuditoryReceptorOccurrence",
    "AuditoryRecurrentMotifOwner",
    "AuditoryVerifiedReceptorExperienceCapability",
    "ExactComponentTrajectoryRankProof",
    "MAX_AUDITORY_RECEPTOR_FRAMES",
    "compose_contiguous_receptor_experiences",
    "compose_verified_contiguous_receptor_experiences",
    "auditory_peak_bank_max_encoded_bytes",
    "migrate_immediately_prior_motif_profile",
    "receptor_experience_from_full_field_event",
    "verify_receptor_experience_custody",
    "verified_receptor_experience_from_full_field_event",
)
