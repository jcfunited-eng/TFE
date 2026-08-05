"""Receipt-bound bridge from lived causal episodes into relation memory.

This module does not recognize an expression and does not assign semantic
labels.  It authorizes one directed relation only when already-mounted,
expression-backed mode endpoints are joined by authenticated causal order and
the same closed experience carries exact origin, event-support, full L0--L4
field, and local memory-element authority.

Fresh supported episodes create the existing conservative ``RelationDrive``.
Quiet recovery episodes create the existing ``AllLaneNegativeSpaceProof``, but
only after inspecting the actual typed ``N_gate`` coordinate on every native
L1 closure from every lane active in the interval.  Opaque "lane proof"
receipts are never accepted as semantic Negative Space evidence.

A newly learned relation enters an existing memory simplex at exact zero mass.
No old component changes and no normalization, threshold, score, centroid,
field-evaluation identity, or similarity comparison participates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from typing import Sequence

from .certified_backend import (
    FLINT_VERSION,
    PYTHON_FLINT_VERSION,
    PYTHON_FLINT_WHEEL_SHA256,
    CertifiedBall,
)
from .closed_experience import ClosedExperienceEvidencePreparation
from .event_support import EventSupportEvaluation, EventSupportEvaluationStatus
from .experience_origin import ExperienceOriginAuthority, ExperienceOriginKind
from .expression_modes import ExpressionModeBank
from .expressions import ClosedExperienceFieldExpression
from .field import MountedFieldTopology
from .memory import (
    MEMORY_MASS_UNIT,
    SIMPLEX_CONSTRAINT_ID,
    AllLaneNegativeSpaceProof,
    CertifiedMemoryMassState,
    DirectedRelation,
    ExactMemoryMassState,
    MemoryElementCalibration,
    MemoryMassState,
    RelationDrive,
    _certified_state_payload,
    _exact_state_payload,
    _relation_payload,
    all_lane_negative_space_receipt_payload,
    relation_drive_receipt_payload,
)
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)


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


def _ball_payload(value: CertifiedBall) -> dict[str, object]:
    return {
        "flint_version": value.flint_version,
        "lower_exponent": value.lower_exponent,
        "lower_mantissa": value.lower_mantissa,
        "python_flint_version": value.python_flint_version,
        "upper_exponent": value.upper_exponent,
        "upper_mantissa": value.upper_mantissa,
        "wheel_sha256": value.wheel_sha256,
        "working_precision_bits": value.working_precision_bits,
    }


def _ball_bounds(value: CertifiedBall) -> tuple[Fraction, Fraction]:
    if not isinstance(value, CertifiedBall):
        raise ReceiptError("R_UF requires a certified interval")
    if (
        value.python_flint_version != PYTHON_FLINT_VERSION
        or value.flint_version != FLINT_VERSION
        or value.wheel_sha256 != PYTHON_FLINT_WHEEL_SHA256
    ):
        raise ReceiptError("R_UF carries a different certified backend authority")
    return (
        Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent,
        Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent,
    )


def _extend_registry(
    registry: ReceiptRegistry, payloads: Sequence[bytes]
) -> ReceiptRegistry:
    if not isinstance(registry, ReceiptRegistry):
        raise ReceiptError("receipt extension requires an immutable registry")
    records = list(registry.records)
    mounted = {value.digest: value.payload for value in records}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("receipt extension requires nonempty exact bytes")
        digest = receipt_sha256(payload)
        previous = mounted.get(digest)
        if previous is not None:
            if previous != payload:
                raise ReceiptError("receipt digest names different exact bytes")
            continue
        records.append(ReceiptRecord(digest=digest, payload=payload))
        mounted[digest] = payload
    return ReceiptRegistry(
        profile_binding_sha256=registry.profile_binding_sha256,
        records=tuple(records),
    )


def _verify_expression_binds_preparation(
    *,
    preparation: ClosedExperienceEvidencePreparation,
    expression: ClosedExperienceFieldExpression,
) -> None:
    if expression.receipt_sha256 == expression.field_evaluation_identity_sha256:
        raise ReceiptError("field-evaluation identity cannot be episode authority")
    if (
        expression.topology_authority_receipt_sha256
        != preparation.topology_authority_receipt_sha256
        or expression.initial_state.source_time != preparation.source_time_start
        or len(expression.steps) != len(preparation.events)
    ):
        raise ReceiptError("episode expression does not cover the prepared field")
    for event, step in zip(preparation.events, expression.steps, strict=True):
        if (
            step.injection.receipt_sha256 != event.injection.receipt_sha256
            or step.authority.source_time_start != event.source_time_start
            or step.authority.source_time_end != event.source_time_end
        ):
            raise ReceiptError("episode expression differs from native closure order")


def causal_direction_authority_receipt_payload(
    *,
    authority_id: str,
    relation: DirectedRelation,
    source_expression_receipt_sha256: str,
    target_expression_receipt_sha256: str,
    source_occurrence_receipt_sha256: str,
    consequence_occurrence_receipt_sha256: str,
    cause_consequence_source_receipt_sha256: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    consequence_time_start: Fraction,
    consequence_time_end: Fraction,
    structural_time_unit: str,
) -> bytes:
    require_identifier(authority_id, "causal direction authority_id")
    if not isinstance(relation, DirectedRelation):
        raise ReceiptError("causal direction requires a typed directed relation")
    for digest, name in (
        (source_expression_receipt_sha256, "source expression receipt"),
        (target_expression_receipt_sha256, "target expression receipt"),
        (source_occurrence_receipt_sha256, "source occurrence receipt"),
        (consequence_occurrence_receipt_sha256, "consequence occurrence receipt"),
        (cause_consequence_source_receipt_sha256, "causal source receipt"),
    ):
        sha256_digest(digest, name)
    for value, name in (
        (source_time_start, "causal source_time_start"),
        (source_time_end, "causal source_time_end"),
        (consequence_time_start, "causal consequence_time_start"),
        (consequence_time_end, "causal consequence_time_end"),
    ):
        require_fraction(value, name)
    if source_time_end <= source_time_start:
        raise ReceiptError("causal source occurrence requires a positive interval")
    if consequence_time_end <= consequence_time_start:
        raise ReceiptError("causal consequence occurrence requires a positive interval")
    if consequence_time_start < source_time_end:
        raise ReceiptError("causal consequence begins before its source closes")
    require_identifier(structural_time_unit, "causal structural_time_unit")
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "cause_consequence_source_receipt_sha256": (
                cause_consequence_source_receipt_sha256
            ),
            "consequence_occurrence_receipt_sha256": (
                consequence_occurrence_receipt_sha256
            ),
            "consequence_time_end": _fraction_text(consequence_time_end),
            "consequence_time_start": _fraction_text(consequence_time_start),
            "direction_rule": (
                "authenticated_cause_then_consequence;timing_alone_is_insufficient"
            ),
            "endpoint_identity": (
                "stable_expression_mode_receipt_plus_source_expression_receipt"
            ),
            "relation": _relation_payload(relation),
            "schema": "glew.memory.causal_direction_authority.v1",
            "source_expression_receipt_sha256": (
                source_expression_receipt_sha256
            ),
            "source_occurrence_receipt_sha256": source_occurrence_receipt_sha256,
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "structural_time_unit": structural_time_unit,
            "target_expression_receipt_sha256": (
                target_expression_receipt_sha256
            ),
        }
    )


class CausalDirectionSourceKind(str, Enum):
    EMBODIED_INTERVENTION = "embodied_intervention"
    EXPLICIT_STORY_CAUSAL_EVENT = "explicit_story_causal_event"


def cause_consequence_source_receipt_payload(
    *,
    source_kind: CausalDirectionSourceKind,
    relation: DirectedRelation,
    source_occurrence_receipt_sha256: str,
    consequence_occurrence_receipt_sha256: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    consequence_time_start: Fraction,
    consequence_time_end: Fraction,
    structural_time_unit: str,
    causal_mechanism_authority_receipt_sha256: str,
) -> bytes:
    """Canonical upstream proof that causality, not timing, supplied direction."""

    if not isinstance(source_kind, CausalDirectionSourceKind):
        raise ReceiptError("causal direction source kind is not typed")
    if not isinstance(relation, DirectedRelation):
        raise ReceiptError("causal direction source requires a typed relation")
    for digest, name in (
        (source_occurrence_receipt_sha256, "source occurrence receipt"),
        (consequence_occurrence_receipt_sha256, "consequence occurrence receipt"),
        (causal_mechanism_authority_receipt_sha256, "causal mechanism authority"),
    ):
        sha256_digest(digest, name)
    for value, name in (
        (source_time_start, "causal source_time_start"),
        (source_time_end, "causal source_time_end"),
        (consequence_time_start, "causal consequence_time_start"),
        (consequence_time_end, "causal consequence_time_end"),
    ):
        require_fraction(value, name)
    if (
        source_time_end <= source_time_start
        or consequence_time_end <= consequence_time_start
        or consequence_time_start < source_time_end
    ):
        raise ReceiptError("causal source intervals are not ordered positive intervals")
    require_identifier(structural_time_unit, "causal structural_time_unit")
    return _canonical_bytes(
        {
            "causal_mechanism_authority_receipt_sha256": (
                causal_mechanism_authority_receipt_sha256
            ),
            "consequence_occurrence_receipt_sha256": (
                consequence_occurrence_receipt_sha256
            ),
            "consequence_time_end": _fraction_text(consequence_time_end),
            "consequence_time_start": _fraction_text(consequence_time_start),
            "predicate": (
                "mounted_causal_mechanism_establishes_source_produced_consequence"
            ),
            "relation": _relation_payload(relation),
            "schema": "glew.memory.authenticated_cause_consequence_source.v1",
            "source_kind": source_kind.value,
            "source_occurrence_receipt_sha256": source_occurrence_receipt_sha256,
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "structural_time_unit": structural_time_unit,
            "timing_only_authority": False,
        }
    )


@dataclass(frozen=True, slots=True)
class CausalDirectionAuthority:
    """Authenticated direction between two stable expression-backed modes."""

    authority_id: str
    relation: DirectedRelation
    source_expression_receipt_sha256: str
    target_expression_receipt_sha256: str
    source_occurrence_receipt_sha256: str
    consequence_occurrence_receipt_sha256: str
    cause_consequence_source_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    consequence_time_start: Fraction
    consequence_time_end: Fraction
    structural_time_unit: str
    authority_receipt_sha256: str

    def payload(self) -> bytes:
        return causal_direction_authority_receipt_payload(
            authority_id=self.authority_id,
            relation=self.relation,
            source_expression_receipt_sha256=(
                self.source_expression_receipt_sha256
            ),
            target_expression_receipt_sha256=(
                self.target_expression_receipt_sha256
            ),
            source_occurrence_receipt_sha256=(
                self.source_occurrence_receipt_sha256
            ),
            consequence_occurrence_receipt_sha256=(
                self.consequence_occurrence_receipt_sha256
            ),
            cause_consequence_source_receipt_sha256=(
                self.cause_consequence_source_receipt_sha256
            ),
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            consequence_time_start=self.consequence_time_start,
            consequence_time_end=self.consequence_time_end,
            structural_time_unit=self.structural_time_unit,
        )

    def verify(
        self,
        *,
        topology: MountedFieldTopology,
        bank: ExpressionModeBank,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        bank.verify(topology=topology, receipt_registry=receipt_registry)
        if self.relation.source_mode_index == self.relation.target_mode_index:
            raise ReceiptError("causal relation endpoints must be distinct modes")
        if (
            self.relation.source_mode_index >= bank.rank
            or self.relation.target_mode_index >= bank.rank
        ):
            raise ReceiptError("causal relation endpoint lies outside the mode bank")
        source = bank.modes[self.relation.source_mode_index]
        target = bank.modes[self.relation.target_mode_index]
        if (
            source.receipt_sha256 != self.relation.source_mode_receipt_sha256
            or target.receipt_sha256 != self.relation.target_mode_receipt_sha256
            or source.source_expression.receipt_sha256
            != self.source_expression_receipt_sha256
            or target.source_expression.receipt_sha256
            != self.target_expression_receipt_sha256
        ):
            raise ReceiptError("causal direction names different stable mode endpoints")
        for digest, name in (
            (bank.receipt_sha256, "expression mode bank"),
            (source.receipt_sha256, "causal source mode"),
            (target.receipt_sha256, "causal target mode"),
        ):
            receipt_registry.resolve(digest, name)
        for digest, name in (
            (self.source_occurrence_receipt_sha256, "causal source occurrence"),
            (
                self.consequence_occurrence_receipt_sha256,
                "causal consequence occurrence",
            ),
            (
                self.cause_consequence_source_receipt_sha256,
                "authenticated cause-consequence source",
            ),
        ):
            receipt_registry.resolve(digest, name)
        source_payload = receipt_registry.resolve(
            self.cause_consequence_source_receipt_sha256,
            "authenticated cause-consequence source",
        )
        try:
            source_record = json.loads(source_payload)
            source_kind = CausalDirectionSourceKind(source_record["source_kind"])
            mechanism_receipt = source_record[
                "causal_mechanism_authority_receipt_sha256"
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise ReceiptError(
                "authenticated cause-consequence source is malformed"
            ) from exc
        receipt_registry.resolve(
            mechanism_receipt, "causal mechanism authority receipt"
        )
        expected_source = cause_consequence_source_receipt_payload(
            source_kind=source_kind,
            relation=self.relation,
            source_occurrence_receipt_sha256=(
                self.source_occurrence_receipt_sha256
            ),
            consequence_occurrence_receipt_sha256=(
                self.consequence_occurrence_receipt_sha256
            ),
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            consequence_time_start=self.consequence_time_start,
            consequence_time_end=self.consequence_time_end,
            structural_time_unit=self.structural_time_unit,
            causal_mechanism_authority_receipt_sha256=mechanism_receipt,
        )
        if source_payload != expected_source:
            raise ReceiptError(
                "cause-consequence source does not bind this exact direction"
            )
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "causal direction authority"
        )
        expected = self.payload()
        if mounted != expected or receipt_sha256(expected) != self.authority_receipt_sha256:
            raise ReceiptError("causal direction differs from mounted exact bytes")


def create_causal_direction_authority(
    *,
    authority_id: str,
    relation: DirectedRelation,
    bank: ExpressionModeBank,
    topology: MountedFieldTopology,
    source_occurrence_receipt_sha256: str,
    consequence_occurrence_receipt_sha256: str,
    cause_consequence_source_receipt_sha256: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    consequence_time_start: Fraction,
    consequence_time_end: Fraction,
    structural_time_unit: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[CausalDirectionAuthority, ReceiptRegistry]:
    bank.verify(topology=topology, receipt_registry=receipt_registry)
    if (
        relation.source_mode_index >= bank.rank
        or relation.target_mode_index >= bank.rank
    ):
        raise ReceiptError("causal relation endpoint lies outside the mode bank")
    source = bank.modes[relation.source_mode_index]
    target = bank.modes[relation.target_mode_index]
    authority = CausalDirectionAuthority(
        authority_id=authority_id,
        relation=relation,
        source_expression_receipt_sha256=source.source_expression.receipt_sha256,
        target_expression_receipt_sha256=target.source_expression.receipt_sha256,
        source_occurrence_receipt_sha256=source_occurrence_receipt_sha256,
        consequence_occurrence_receipt_sha256=consequence_occurrence_receipt_sha256,
        cause_consequence_source_receipt_sha256=(
            cause_consequence_source_receipt_sha256
        ),
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        consequence_time_start=consequence_time_start,
        consequence_time_end=consequence_time_end,
        structural_time_unit=structural_time_unit,
        authority_receipt_sha256="0" * 64,
    )
    payload = authority.payload()
    authority = replace(
        authority, authority_receipt_sha256=receipt_sha256(payload)
    )
    extended = _extend_registry(receipt_registry, (payload,))
    authority.verify(topology=topology, bank=bank, receipt_registry=extended)
    return authority, extended


class CausalRelationEpisodePhase(str, Enum):
    SUPPORT = "support"
    RECOVERY = "recovery"


def _lane_negative_space_payload(
    *,
    lane_id: str,
    topology_authority_receipt_sha256: str,
    preparation_receipt_sha256: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    structural_time_unit: str,
    evidence_receipt_sha256s: Sequence[str],
) -> bytes:
    return _canonical_bytes(
        {
            "evidence_receipt_sha256s": list(evidence_receipt_sha256s),
            "lane_id": lane_id,
            "predicate": "every_actual_native_L1_closure_has_exact_N_gate=1",
            "preparation_receipt_sha256": preparation_receipt_sha256,
            "schema": "glew.memory.semantic_lane_negative_space.v1",
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "structural_time_unit": structural_time_unit,
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


def _support_intent_payload(
    *,
    episode_id: str,
    relation: DirectedRelation,
    exact_r_event: Fraction,
    delta: Fraction,
) -> bytes:
    if exact_r_event <= 0 or delta <= 0:
        raise ReceiptError("relation support intent requires positive energy and duration")
    return _canonical_bytes(
        {
            "episode_id": episode_id,
            "excitation_equation": "g=R_event/delta;g*delta=R_event",
            "exact_r_event": _fraction_text(exact_r_event),
            "joint_energy_density": _fraction_text(exact_r_event / delta),
            "relation": _relation_payload(relation),
            "relation_support": "1/1",
            "schema": "glew.memory.causal_relation_support_intent.v1",
        }
    )


def _semantic_negative_space_proof(
    *,
    preparation: ClosedExperienceEvidencePreparation,
    topology: MountedFieldTopology,
    structural_time_unit: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[AllLaneNegativeSpaceProof, tuple[bytes, ...], ReceiptRegistry]:
    by_lane: dict[str, list[str]] = {}
    for event in preparation.events:
        for evidence in event.evidence:
            by_lane.setdefault(evidence.lane_id, []).append(
                evidence.evidence_receipt_sha256
            )
            if evidence.coordinates.N_gate != Fraction(1):
                raise ReceiptError(
                    f"lane {evidence.lane_id!r} has actual L1 N_gate != 1"
                )
    active_lanes = tuple(sorted(by_lane))
    if not active_lanes:
        raise ReceiptError("Negative Space recovery requires actual active lanes")
    topology_lanes = {value.lane_id for value in topology.ordered_port_fibers}
    if not set(active_lanes).issubset(topology_lanes):
        raise ReceiptError("Negative Space evidence names an unmounted lane")
    lane_payloads = tuple(
        _lane_negative_space_payload(
            lane_id=lane_id,
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            preparation_receipt_sha256=preparation.receipt_sha256,
            source_time_start=preparation.source_time_start,
            source_time_end=preparation.source_time_end,
            structural_time_unit=structural_time_unit,
            evidence_receipt_sha256s=tuple(by_lane[lane_id]),
        )
        for lane_id in active_lanes
    )
    lane_digests = tuple(receipt_sha256(value) for value in lane_payloads)
    aggregate_payload = all_lane_negative_space_receipt_payload(
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        source_time_start=preparation.source_time_start,
        source_time_end=preparation.source_time_end,
        structural_time_unit=structural_time_unit,
        active_lane_ids=active_lanes,
        lane_l1_proof_receipt_sha256s=lane_digests,
    )
    proof = AllLaneNegativeSpaceProof(
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        source_time_start=preparation.source_time_start,
        source_time_end=preparation.source_time_end,
        structural_time_unit=structural_time_unit,
        active_lane_ids=active_lanes,
        lane_l1_proof_receipt_sha256s=lane_digests,
        aggregate_receipt_sha256=receipt_sha256(aggregate_payload),
    )
    extended = _extend_registry(
        receipt_registry, (*lane_payloads, aggregate_payload)
    )
    proof.verify(extended)
    return proof, (*lane_payloads, aggregate_payload), extended


def causal_relation_episode_receipt_payload(
    *,
    episode_id: str,
    phase: CausalRelationEpisodePhase,
    relation: DirectedRelation,
    direction_authority_receipt_sha256: str,
    topology_authority_receipt_sha256: str,
    preparation_receipt_sha256: str,
    expression_receipt_sha256: str,
    closed_experience_receipt_sha256: str,
    origin_authority_receipt_sha256: str,
    origin_kind: ExperienceOriginKind,
    event_support_authority_receipt_sha256: str,
    exact_r_event: Fraction,
    resonance_receipt_sha256: str,
    resonance_value: CertifiedBall,
    calibration_receipt_sha256: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    structural_time_unit: str,
    output_receipt_sha256: str,
) -> bytes:
    require_identifier(episode_id, "causal relation episode_id")
    if not isinstance(phase, CausalRelationEpisodePhase):
        raise ReceiptError("causal relation episode phase is not typed")
    require_fraction(exact_r_event, "causal episode R_event")
    if exact_r_event < 0:
        raise ReceiptError("causal episode R_event cannot be negative")
    return _canonical_bytes(
        {
            "calibration_receipt_sha256": calibration_receipt_sha256,
            "closed_experience_receipt_sha256": (
                closed_experience_receipt_sha256
            ),
            "direction_authority_receipt_sha256": (
                direction_authority_receipt_sha256
            ),
            "episode_id": episode_id,
            "event_support_authority_receipt_sha256": (
                event_support_authority_receipt_sha256
            ),
            "exact_r_event": _fraction_text(exact_r_event),
            "expression_receipt_sha256": expression_receipt_sha256,
            "identity_exclusions": [
                "centroid",
                "field_evaluation_identity",
                "similarity_score",
            ],
            "origin_authority_receipt_sha256": origin_authority_receipt_sha256,
            "origin_kind": origin_kind.value,
            "output_receipt_sha256": output_receipt_sha256,
            "phase": phase.value,
            "preparation_receipt_sha256": preparation_receipt_sha256,
            "relation": _relation_payload(relation),
            "resonance_receipt_sha256": resonance_receipt_sha256,
            "resonance_value": _ball_payload(resonance_value),
            "schema": "glew.memory.causal_relation_episode_authority.v1",
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "structural_time_unit": structural_time_unit,
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class CausalRelationEpisodeAuthority:
    """One complete, exact causal relation support or recovery episode."""

    episode_id: str
    phase: CausalRelationEpisodePhase
    relation: DirectedRelation
    direction_authority_receipt_sha256: str
    topology_authority_receipt_sha256: str
    preparation_receipt_sha256: str
    expression_receipt_sha256: str
    closed_experience_receipt_sha256: str
    origin_authority_receipt_sha256: str
    origin_kind: ExperienceOriginKind
    event_support_authority_receipt_sha256: str
    exact_r_event: Fraction
    resonance_receipt_sha256: str
    resonance_value: CertifiedBall
    calibration_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    structural_time_unit: str
    output_receipt_sha256: str
    authority_receipt_sha256: str

    @property
    def delta(self) -> Fraction:
        return self.source_time_end - self.source_time_start

    def payload(self) -> bytes:
        return causal_relation_episode_receipt_payload(
            episode_id=self.episode_id,
            phase=self.phase,
            relation=self.relation,
            direction_authority_receipt_sha256=(
                self.direction_authority_receipt_sha256
            ),
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            preparation_receipt_sha256=self.preparation_receipt_sha256,
            expression_receipt_sha256=self.expression_receipt_sha256,
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            origin_authority_receipt_sha256=(
                self.origin_authority_receipt_sha256
            ),
            origin_kind=self.origin_kind,
            event_support_authority_receipt_sha256=(
                self.event_support_authority_receipt_sha256
            ),
            exact_r_event=self.exact_r_event,
            resonance_receipt_sha256=self.resonance_receipt_sha256,
            resonance_value=self.resonance_value,
            calibration_receipt_sha256=self.calibration_receipt_sha256,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            structural_time_unit=self.structural_time_unit,
            output_receipt_sha256=self.output_receipt_sha256,
        )

    def verify(
        self,
        *,
        topology: MountedFieldTopology,
        bank: ExpressionModeBank,
        direction: CausalDirectionAuthority,
        preparation: ClosedExperienceEvidencePreparation,
        expression: ClosedExperienceFieldExpression,
        origin: ExperienceOriginAuthority,
        event_support: EventSupportEvaluation,
        calibration: MemoryElementCalibration,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        preparation.verify(topology, receipt_registry)
        expression.verify(receipt_registry)
        _verify_expression_binds_preparation(
            preparation=preparation, expression=expression
        )
        direction.verify(
            topology=topology, bank=bank, receipt_registry=receipt_registry
        )
        origin.verify(receipt_registry)
        event_support.verify(
            origin=origin,
            topology=topology,
            closed_experience_receipt_sha256=(
                self.closed_experience_receipt_sha256
            ),
            expression=expression,
            receipt_registry=receipt_registry,
        )
        calibration.verify(receipt_registry)
        if (
            self.relation != direction.relation
            or self.direction_authority_receipt_sha256
            != direction.authority_receipt_sha256
            or self.topology_authority_receipt_sha256
            != topology.authority_receipt_sha256
            or self.preparation_receipt_sha256 != preparation.receipt_sha256
            or self.expression_receipt_sha256 != expression.receipt_sha256
            or self.closed_experience_receipt_sha256
            != origin.closed_experience_receipt_sha256
            or direction.consequence_occurrence_receipt_sha256
            != self.closed_experience_receipt_sha256
            or direction.consequence_time_start != preparation.source_time_start
            or direction.consequence_time_end != preparation.source_time_end
            or direction.target_expression_receipt_sha256
            != expression.receipt_sha256
            or self.origin_authority_receipt_sha256
            != origin.authority_receipt_sha256
            or self.origin_kind is not origin.kind
            or self.event_support_authority_receipt_sha256
            != event_support.authority.authority_receipt_sha256
            or self.exact_r_event != event_support.exact_r_event
            or self.calibration_receipt_sha256
            != calibration.calibration_receipt_sha256
            or self.relation != calibration.relation
            or self.source_time_start != preparation.source_time_start
            or self.source_time_end != preparation.source_time_end
            or self.structural_time_unit != calibration.structural_time_unit
        ):
            raise ReceiptError("causal relation episode dependencies changed")
        if event_support.status is not EventSupportEvaluationStatus.RESOLVED:
            raise ReceiptError("causal relation episode requires resolved exact R_event")
        if self.exact_r_event is None or self.exact_r_event < 0:
            raise ReceiptError("causal relation episode lacks nonnegative exact R_event")
        if self.delta <= 0:
            raise ReceiptError("causal relation episode requires positive exact duration")
        preparation_payload = json.loads(preparation.receipt_payload)
        resonance_receipt = preparation_payload.get(
            "resonance_confirmation_receipt_sha256"
        )
        if resonance_receipt != self.resonance_receipt_sha256:
            raise ReceiptError("causal relation episode names another R_UF receipt")
        if self.resonance_value != preparation.resonance_confirmation.value:
            raise ReceiptError("causal relation episode carries another R_UF interval")
        output = receipt_registry.resolve(
            self.output_receipt_sha256, "episode output receipt"
        )
        if self.phase is CausalRelationEpisodePhase.SUPPORT:
            lower, _ = _ball_bounds(self.resonance_value)
            if lower <= 0:
                raise ReceiptError("supported episode lacks certified positive R_UF")
            if self.exact_r_event <= 0:
                raise ReceiptError("supported episode lacks positive exact R_event")
            expected_output = _support_intent_payload(
                episode_id=self.episode_id,
                relation=self.relation,
                exact_r_event=self.exact_r_event,
                delta=self.delta,
            )
            if output != expected_output:
                raise ReceiptError("supported episode output intent changed")
        elif self.phase is CausalRelationEpisodePhase.RECOVERY:
            by_lane: dict[str, list[str]] = {}
            for event in preparation.events:
                for evidence in event.evidence:
                    if evidence.coordinates.N_gate != Fraction(1):
                        raise ReceiptError(
                            f"lane {evidence.lane_id!r} has actual L1 N_gate != 1"
                        )
                    by_lane.setdefault(evidence.lane_id, []).append(
                        evidence.evidence_receipt_sha256
                    )
            active_lanes = tuple(sorted(by_lane))
            lane_payloads = tuple(
                _lane_negative_space_payload(
                    lane_id=lane_id,
                    topology_authority_receipt_sha256=(
                        topology.authority_receipt_sha256
                    ),
                    preparation_receipt_sha256=preparation.receipt_sha256,
                    source_time_start=preparation.source_time_start,
                    source_time_end=preparation.source_time_end,
                    structural_time_unit=self.structural_time_unit,
                    evidence_receipt_sha256s=tuple(by_lane[lane_id]),
                )
                for lane_id in active_lanes
            )
            lane_digests = tuple(receipt_sha256(value) for value in lane_payloads)
            expected_output = all_lane_negative_space_receipt_payload(
                topology_authority_receipt_sha256=(
                    topology.authority_receipt_sha256
                ),
                source_time_start=preparation.source_time_start,
                source_time_end=preparation.source_time_end,
                structural_time_unit=self.structural_time_unit,
                active_lane_ids=active_lanes,
                lane_l1_proof_receipt_sha256s=lane_digests,
            )
            if output != expected_output:
                raise ReceiptError("recovery output is not semantic all-lane proof")
            for digest, expected_lane in zip(
                lane_digests, lane_payloads, strict=True
            ):
                if (
                    receipt_registry.resolve(
                        digest, "semantic lane Negative Space proof"
                    )
                    != expected_lane
                ):
                    raise ReceiptError("semantic lane proof changed")
        else:
            raise ReceiptError("causal relation episode phase is not typed")
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "causal relation episode authority"
        )
        expected = self.payload()
        if mounted != expected or receipt_sha256(expected) != self.authority_receipt_sha256:
            raise ReceiptError("causal relation episode differs from mounted exact bytes")


@dataclass(frozen=True, slots=True)
class CausalRelationSupportMaterial:
    authority: CausalRelationEpisodeAuthority
    drive: RelationDrive
    receipt_registry: ReceiptRegistry


@dataclass(frozen=True, slots=True)
class CausalRelationRecoveryMaterial:
    authority: CausalRelationEpisodeAuthority
    negative_space_proof: AllLaneNegativeSpaceProof
    receipt_registry: ReceiptRegistry


def _episode_common(
    *,
    episode_id: str,
    phase: CausalRelationEpisodePhase,
    direction: CausalDirectionAuthority,
    topology: MountedFieldTopology,
    preparation: ClosedExperienceEvidencePreparation,
    expression: ClosedExperienceFieldExpression,
    origin: ExperienceOriginAuthority,
    event_support: EventSupportEvaluation,
    calibration: MemoryElementCalibration,
    output_receipt_sha256: str,
) -> CausalRelationEpisodeAuthority:
    if origin.kind not in {
        ExperienceOriginKind.FRESH_EXTERNAL,
        ExperienceOriginKind.EXPLICIT_STORY_EMULATOR,
    }:
        raise ReceiptError("relation episodes require fresh lived or explicit story origin")
    if event_support.status is not EventSupportEvaluationStatus.RESOLVED:
        raise ReceiptError("relation episode R_event is UNKNOWN")
    if event_support.exact_r_event is None:
        raise ReceiptError("relation episode lacks exact R_event")
    preparation_payload = json.loads(preparation.receipt_payload)
    resonance_receipt = preparation_payload[
        "resonance_confirmation_receipt_sha256"
    ]
    authority = CausalRelationEpisodeAuthority(
        episode_id=episode_id,
        phase=phase,
        relation=direction.relation,
        direction_authority_receipt_sha256=direction.authority_receipt_sha256,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        preparation_receipt_sha256=preparation.receipt_sha256,
        expression_receipt_sha256=expression.receipt_sha256,
        closed_experience_receipt_sha256=origin.closed_experience_receipt_sha256,
        origin_authority_receipt_sha256=origin.authority_receipt_sha256,
        origin_kind=origin.kind,
        event_support_authority_receipt_sha256=(
            event_support.authority.authority_receipt_sha256
        ),
        exact_r_event=event_support.exact_r_event,
        resonance_receipt_sha256=resonance_receipt,
        resonance_value=preparation.resonance_confirmation.value,
        calibration_receipt_sha256=calibration.calibration_receipt_sha256,
        source_time_start=preparation.source_time_start,
        source_time_end=preparation.source_time_end,
        structural_time_unit=calibration.structural_time_unit,
        output_receipt_sha256=output_receipt_sha256,
        authority_receipt_sha256="0" * 64,
    )
    return authority


def create_causal_relation_support_episode(
    *,
    episode_id: str,
    direction: CausalDirectionAuthority,
    topology: MountedFieldTopology,
    bank: ExpressionModeBank,
    preparation: ClosedExperienceEvidencePreparation,
    expression: ClosedExperienceFieldExpression,
    origin: ExperienceOriginAuthority,
    event_support: EventSupportEvaluation,
    calibration: MemoryElementCalibration,
    receipt_registry: ReceiptRegistry,
) -> CausalRelationSupportMaterial:
    """Create an exact support episode and its existing conservative drive."""

    preparation.verify(topology, receipt_registry)
    lower, _ = _ball_bounds(preparation.resonance_confirmation.value)
    if lower <= 0:
        raise ReceiptError("R_UF does not certify strictly positive resonance")
    if event_support.exact_r_event is None or event_support.exact_r_event <= 0:
        raise ReceiptError("supported relation requires strictly positive exact R_event")
    delta = preparation.source_time_end - preparation.source_time_start
    if delta <= 0:
        raise ReceiptError("supported relation requires positive exact duration")
    density = event_support.exact_r_event / delta

    provisional = _episode_common(
        episode_id=episode_id,
        phase=CausalRelationEpisodePhase.SUPPORT,
        direction=direction,
        topology=topology,
        preparation=preparation,
        expression=expression,
        origin=origin,
        event_support=event_support,
        calibration=calibration,
        output_receipt_sha256="0" * 64,
    )
    # The drive binds the episode authority, while the episode binds the drive.
    # Break that receipt cycle with one exact output-intent receipt, then bind
    # both final receipts to it.
    output_intent = _support_intent_payload(
        episode_id=episode_id,
        relation=direction.relation,
        exact_r_event=event_support.exact_r_event,
        delta=delta,
    )
    output_intent_digest = receipt_sha256(output_intent)
    authority = replace(
        provisional,
        output_receipt_sha256=output_intent_digest,
        authority_receipt_sha256="0" * 64,
    )
    authority_payload = authority.payload()
    authority = replace(
        authority,
        authority_receipt_sha256=receipt_sha256(authority_payload),
    )
    drive_payload = relation_drive_receipt_payload(
        relation=direction.relation,
        joint_energy_density=density,
        relation_support=Fraction(1),
        experience_origin=origin.kind.value,
        full_field_commit_receipt_sha256=authority.authority_receipt_sha256,
    )
    drive = RelationDrive(
        relation=direction.relation,
        joint_energy_density=density,
        relation_support=Fraction(1),
        experience_origin=origin.kind.value,
        full_field_commit_receipt_sha256=authority.authority_receipt_sha256,
        drive_receipt_sha256=receipt_sha256(drive_payload),
    )
    extended = _extend_registry(
        receipt_registry, (output_intent, authority_payload, drive_payload)
    )
    authority.verify(
        topology=topology,
        bank=bank,
        direction=direction,
        preparation=preparation,
        expression=expression,
        origin=origin,
        event_support=event_support,
        calibration=calibration,
        receipt_registry=extended,
    )
    drive.verify(extended)
    if drive.excitation_rate * authority.delta != authority.exact_r_event:
        raise ReceiptError("relation drive does not conserve exact episode support")
    return CausalRelationSupportMaterial(authority, drive, extended)


def create_causal_relation_recovery_episode(
    *,
    episode_id: str,
    direction: CausalDirectionAuthority,
    topology: MountedFieldTopology,
    bank: ExpressionModeBank,
    preparation: ClosedExperienceEvidencePreparation,
    expression: ClosedExperienceFieldExpression,
    origin: ExperienceOriginAuthority,
    event_support: EventSupportEvaluation,
    calibration: MemoryElementCalibration,
    receipt_registry: ReceiptRegistry,
) -> CausalRelationRecoveryMaterial:
    """Create no drive; authorize decay only from actual exact L1 N_gate=1."""

    preparation.verify(topology, receipt_registry)
    proof, _, with_proof = _semantic_negative_space_proof(
        preparation=preparation,
        topology=topology,
        structural_time_unit=calibration.structural_time_unit,
        receipt_registry=receipt_registry,
    )
    provisional = _episode_common(
        episode_id=episode_id,
        phase=CausalRelationEpisodePhase.RECOVERY,
        direction=direction,
        topology=topology,
        preparation=preparation,
        expression=expression,
        origin=origin,
        event_support=event_support,
        calibration=calibration,
        output_receipt_sha256=proof.aggregate_receipt_sha256,
    )
    authority_payload = provisional.payload()
    authority = replace(
        provisional,
        authority_receipt_sha256=receipt_sha256(authority_payload),
    )
    extended = _extend_registry(with_proof, (authority_payload,))
    authority.verify(
        topology=topology,
        bank=bank,
        direction=direction,
        preparation=preparation,
        expression=expression,
        origin=origin,
        event_support=event_support,
        calibration=calibration,
        receipt_registry=extended,
    )
    proof.verify(extended)
    return CausalRelationRecoveryMaterial(authority, proof, extended)


def relation_domain_extension_receipt_payload(
    *,
    episode_authority_receipt_sha256: str,
    prior_state_receipt_sha256: str,
    result_state_receipt_sha256: str,
    relation: DirectedRelation,
) -> bytes:
    return _canonical_bytes(
        {
            "added_mass": "0/1",
            "episode_authority_receipt_sha256": (
                episode_authority_receipt_sha256
            ),
            "mass_conservation": "old_components_unchanged;total=1",
            "prior_state_receipt_sha256": prior_state_receipt_sha256,
            "relation": _relation_payload(relation),
            "result_state_receipt_sha256": result_state_receipt_sha256,
            "schema": "glew.memory.zero_mass_relation_domain_extension.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class RelationDomainExtensionResult:
    state: MemoryMassState
    prior_state_receipt_sha256: str
    episode_authority_receipt_sha256: str
    added_relation: DirectedRelation
    receipt_sha256: str
    receipt_payload: bytes
    receipt_registry: ReceiptRegistry

    def verify(self, prior_state: MemoryMassState) -> None:
        prior_state.verify()
        self.state.verify()
        if self.prior_state_receipt_sha256 != prior_state.receipt_sha256:
            raise ReceiptError("domain extension names another prior state")
        if self.added_relation in prior_state.relation_order:
            raise ReceiptError("domain extension relation already existed")
        expected_order = tuple(sorted((*prior_state.relation_order, self.added_relation)))
        if self.state.relation_order != expected_order:
            raise ReceiptError("domain extension changed canonical relation order")
        prior_by_relation = dict(
            zip(prior_state.relation_order, prior_state.active_masses, strict=True)
        )
        result_by_relation = dict(
            zip(self.state.relation_order, self.state.active_masses, strict=True)
        )
        if any(
            result_by_relation[relation] != mass
            for relation, mass in prior_by_relation.items()
        ):
            raise ReceiptError("domain extension changed an existing relation mass")
        added = result_by_relation[self.added_relation]
        if isinstance(added, Fraction):
            if added != 0:
                raise ReceiptError("new relation did not enter at exact zero mass")
        elif _ball_bounds(added) != (Fraction(0), Fraction(0)):
            raise ReceiptError("new certified relation did not enter at exact zero")
        if self.state.quiescent_mass != prior_state.quiescent_mass:
            raise ReceiptError("domain extension changed quiescent mass")
        if (
            self.state.source_time != prior_state.source_time
            or self.state.structural_time_unit != prior_state.structural_time_unit
            or self.state.topology_authority_receipt_sha256
            != prior_state.topology_authority_receipt_sha256
        ):
            raise ReceiptError("domain extension changed memory state scope")
        expected = relation_domain_extension_receipt_payload(
            episode_authority_receipt_sha256=(
                self.episode_authority_receipt_sha256
            ),
            prior_state_receipt_sha256=self.prior_state_receipt_sha256,
            result_state_receipt_sha256=self.state.receipt_sha256,
            relation=self.added_relation,
        )
        if (
            self.receipt_payload != expected
            or self.receipt_sha256 != receipt_sha256(expected)
            or self.receipt_registry.resolve(
                self.receipt_sha256, "relation domain extension receipt"
            )
            != expected
        ):
            raise ReceiptError("relation domain extension differs from exact bytes")


def extend_relation_domain_with_zero_mass(
    *,
    state: MemoryMassState,
    episode: CausalRelationEpisodeAuthority,
    receipt_registry: ReceiptRegistry,
) -> RelationDomainExtensionResult:
    """Insert one causally authorized relation without moving memory mass."""

    if not isinstance(state, (ExactMemoryMassState, CertifiedMemoryMassState)):
        raise ReceiptError("relation domain extension requires a typed memory state")
    state.verify()
    if episode.phase is not CausalRelationEpisodePhase.SUPPORT:
        raise ReceiptError("only a supported causal episode can extend relation domain")
    mounted_episode = receipt_registry.resolve(
        episode.authority_receipt_sha256, "causal relation episode authority"
    )
    if mounted_episode != episode.payload():
        raise ReceiptError("causal relation episode differs from mounted exact bytes")
    relation = episode.relation
    if relation in state.relation_order:
        raise ReceiptError("causal relation already exists in memory domain")
    order = tuple(sorted((*state.relation_order, relation)))
    old = dict(zip(state.relation_order, state.active_masses, strict=True))
    if isinstance(state, ExactMemoryMassState):
        active = tuple(old.get(value, Fraction(0)) for value in order)
        state_payload = _exact_state_payload(
            source_time=state.source_time,
            structural_time_unit=state.structural_time_unit,
            topology_authority_receipt_sha256=(
                state.topology_authority_receipt_sha256
            ),
            relation_order=order,
            quiescent_mass=state.quiescent_mass,
            active_masses=active,
        )
        result_state: MemoryMassState = ExactMemoryMassState(
            source_time=state.source_time,
            structural_time_unit=state.structural_time_unit,
            topology_authority_receipt_sha256=(
                state.topology_authority_receipt_sha256
            ),
            relation_order=order,
            quiescent_mass=state.quiescent_mass,
            active_masses=active,
            receipt_sha256=receipt_sha256(state_payload),
            receipt_payload=state_payload,
        )
    else:
        precision = max(value.working_precision_bits for value in state.components)
        zero = CertifiedBall(
            lower_mantissa=0,
            lower_exponent=0,
            upper_mantissa=0,
            upper_exponent=0,
            working_precision_bits=precision,
            python_flint_version=PYTHON_FLINT_VERSION,
            flint_version=FLINT_VERSION,
            wheel_sha256=PYTHON_FLINT_WHEEL_SHA256,
        )
        active = tuple(old.get(value, zero) for value in order)
        state_payload = _certified_state_payload(
            source_time=state.source_time,
            structural_time_unit=state.structural_time_unit,
            topology_authority_receipt_sha256=(
                state.topology_authority_receipt_sha256
            ),
            relation_order=order,
            quiescent_mass=state.quiescent_mass,
            active_masses=active,
        )
        result_state = CertifiedMemoryMassState(
            source_time=state.source_time,
            structural_time_unit=state.structural_time_unit,
            topology_authority_receipt_sha256=(
                state.topology_authority_receipt_sha256
            ),
            relation_order=order,
            quiescent_mass=state.quiescent_mass,
            active_masses=active,
            exact_total_mass=MEMORY_MASS_UNIT,
            constraint_id=SIMPLEX_CONSTRAINT_ID,
            receipt_sha256=receipt_sha256(state_payload),
            receipt_payload=state_payload,
        )
    extension_payload = relation_domain_extension_receipt_payload(
        episode_authority_receipt_sha256=episode.authority_receipt_sha256,
        prior_state_receipt_sha256=state.receipt_sha256,
        result_state_receipt_sha256=result_state.receipt_sha256,
        relation=relation,
    )
    extended = _extend_registry(
        receipt_registry, (state_payload, extension_payload)
    )
    result = RelationDomainExtensionResult(
        state=result_state,
        prior_state_receipt_sha256=state.receipt_sha256,
        episode_authority_receipt_sha256=episode.authority_receipt_sha256,
        added_relation=relation,
        receipt_sha256=receipt_sha256(extension_payload),
        receipt_payload=extension_payload,
        receipt_registry=extended,
    )
    result.verify(state)
    if isinstance(result_state, ExactMemoryMassState):
        if (
            result_state.quiescent_mass
            + sum(result_state.active_masses, Fraction(0))
            != MEMORY_MASS_UNIT
        ):
            raise ReceiptError("relation domain extension changed exact total mass")
    return result
