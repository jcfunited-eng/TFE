"""Certified conservative Krimelack relation memory for GLEW.

Memory is one unit of physical mass shared by an explicit quiescent reservoir
and a canonical set of directed mode relations.  A fresh, externally receipted
experience transfers reservoir mass into supported relations.  Active mass can
return to the reservoir only while every mounted active lane carries a
receipted canonical L1 Negative Space proof.

For one exact structural-time interval the column state ``x`` obeys

    dx/dt = G x
    x(t + dt) = exp(G dt) x(t)

where ``G`` has nonnegative off-diagonals and exact zero column sums.  Those two
algebraic facts preserve nonnegativity and total mass without clipping,
thresholding, deletion, ceilings, or post-normalization.  Certified component
enclosures are always carried with the exact affine simplex constraint; they
are never interpreted as independently selectable midpoint values.

The same correlated relation masses can be evaluated into the direction-
distinct Hermitian memory operator

    K(u->v) = ((A + A*) + i(A - A*)) / (2 sqrt(2)),  A = u v*

using pinned Arb arithmetic.  The current field evolution accepts only exact
rational Hamiltonian entries, so this module exposes a fail-closed integration
boundary rather than rationalizing the irrational factor or selecting interval
midpoints.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from .certified_backend import (
    FLINT_VERSION,
    PYTHON_FLINT_VERSION,
    PYTHON_FLINT_WHEEL_SHA256,
    CertifiedBall,
    arb_fraction,
    canonical_ball,
    load_pinned_flint,
)
from .field import CertifiedComplexBall, MountedFieldTopology
from .model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)
from .modes import CertifiedModeBank


MEMORY_MASS_UNIT = Fraction(1)
MASS_FLOW_OPERATOR_ID = "conservative_krimelack_relation_mass_exponential.v1"
H_MEM_OPERATOR_ID = "directed_hermitian_correlated_relation_field.v1"
SIMPLEX_CONSTRAINT_ID = "nonnegative_exact_affine_memory_simplex.v1"
FIELD_H_MEM_INTEGRATION_REQUIREMENT = (
    "dsf_ai_service.glew_runtime.field.FieldEvolutionAuthority.hamiltonian "
    "must accept expression-bound CertifiedComplexBall Hermitian entries, and "
    "evolve those balls in the same pinned Arb solve; its current ExactComplex "
    "rational-only boundary cannot ingest 1/(2*sqrt(2)). Midpoint selection or "
    "rational substitution is forbidden."
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


def _complex_ball_payload(value: CertifiedComplexBall) -> dict[str, object]:
    return {"imag": _ball_payload(value.imag), "real": _ball_payload(value.real)}


def _ball_bounds(value: CertifiedBall) -> tuple[Fraction, Fraction]:
    _verify_ball_authority(value)
    return (
        Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent,
        Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent,
    )


def _verify_ball_authority(value: CertifiedBall) -> None:
    if not isinstance(value, CertifiedBall):
        raise ReceiptError("memory state contains a non-certified component")
    if (
        value.python_flint_version != PYTHON_FLINT_VERSION
        or value.flint_version != FLINT_VERSION
        or value.wheel_sha256 != PYTHON_FLINT_WHEEL_SHA256
    ):
        raise ReceiptError("memory state carries a different certified backend authority")


def _dyadic_pair(value: Fraction) -> tuple[int, int]:
    denominator = value.denominator
    if denominator & (denominator - 1):
        raise ReceiptError("certified memory endpoint is not dyadic")
    return value.numerator, -(denominator.bit_length() - 1)


def _arb_from_ball(flint, value: CertifiedBall):
    """Reconstruct the complete endpoint interval, never a nominal value.

    Arb's constructor uses midpoint-radius storage internally.  Both exact
    outward endpoints participate here; the midpoint is not returned, compared,
    stored, or granted decision authority.
    """

    lower, upper = _ball_bounds(value)
    midpoint = (lower + upper) / 2
    radius = (upper - lower) / 2
    return flint.arb(_dyadic_pair(midpoint), _dyadic_pair(radius))


def _negate_ball(value: CertifiedBall) -> CertifiedBall:
    return CertifiedBall(
        lower_mantissa=-value.upper_mantissa,
        lower_exponent=value.upper_exponent,
        upper_mantissa=-value.lower_mantissa,
        upper_exponent=value.lower_exponent,
        working_precision_bits=value.working_precision_bits,
        python_flint_version=value.python_flint_version,
        flint_version=value.flint_version,
        wheel_sha256=value.wheel_sha256,
    )


def _precision_for_inputs(
    fractions: Sequence[Fraction], balls: Sequence[CertifiedBall]
) -> int:
    bits = 1
    for value in fractions:
        require_fraction(value, "certified memory input")
        bits = max(
            bits,
            abs(value.numerator).bit_length(),
            value.denominator.bit_length(),
        )
    for value in balls:
        _verify_ball_authority(value)
        bits = max(
            bits,
            abs(value.lower_mantissa).bit_length(),
            abs(value.upper_mantissa).bit_length(),
        )
    required = bits + 64
    return 1 << (required - 1).bit_length()


@dataclass(frozen=True, order=True, slots=True)
class DirectedRelation:
    """One canonical directed relation between two full-field modes."""

    source_mode_index: int
    target_mode_index: int
    source_mode_receipt_sha256: str
    target_mode_receipt_sha256: str

    def __post_init__(self) -> None:
        for name, value in (
            ("source_mode_index", self.source_mode_index),
            ("target_mode_index", self.target_mode_index),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ReceiptError(f"{name} must be a nonnegative integer")
        sha256_digest(
            self.source_mode_receipt_sha256, "relation source-mode receipt"
        )
        sha256_digest(
            self.target_mode_receipt_sha256, "relation target-mode receipt"
        )


def _relation_payload(relation: DirectedRelation) -> dict[str, object]:
    if not isinstance(relation, DirectedRelation):
        raise ReceiptError("relation memory contains an untyped relation")
    return {
        "source_mode_index": relation.source_mode_index,
        "source_mode_receipt_sha256": relation.source_mode_receipt_sha256,
        "target_mode_index": relation.target_mode_index,
        "target_mode_receipt_sha256": relation.target_mode_receipt_sha256,
    }


def _validate_relation_order(relations: Sequence[DirectedRelation]) -> None:
    if not all(isinstance(value, DirectedRelation) for value in relations):
        raise ReceiptError("relation order contains an untyped relation")
    if tuple(relations) != tuple(sorted(relations)) or len(set(relations)) != len(relations):
        raise ReceiptError("relations must be unique and in canonical directed order")


@dataclass(frozen=True, slots=True)
class ExactMemoryMassState:
    """Exact initial/quiescent state before any transcendental mass flow."""

    source_time: Fraction
    structural_time_unit: str
    topology_authority_receipt_sha256: str
    relation_order: tuple[DirectedRelation, ...]
    quiescent_mass: Fraction
    active_masses: tuple[Fraction, ...]
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        require_fraction(self.source_time, "memory source_time")
        require_identifier(self.structural_time_unit, "memory structural_time_unit")
        sha256_digest(
            self.topology_authority_receipt_sha256,
            "memory topology authority receipt",
        )
        _validate_relation_order(self.relation_order)
        if len(self.active_masses) != len(self.relation_order):
            raise ReceiptError("active memory masses do not cover the canonical relations")
        require_fraction(self.quiescent_mass, "quiescent memory mass")
        for value in self.active_masses:
            require_fraction(value, "active memory mass")
        if self.quiescent_mass < 0 or any(value < 0 for value in self.active_masses):
            raise ReceiptError("memory mass cannot be negative")
        if self.quiescent_mass + sum(self.active_masses, Fraction(0)) != MEMORY_MASS_UNIT:
            raise ReceiptError("exact memory state does not conserve its one mass unit")
        sha256_digest(self.receipt_sha256, "exact memory state receipt")
        if not isinstance(self.receipt_payload, bytes) or not self.receipt_payload:
            raise ReceiptError("exact memory state requires canonical receipt bytes")
        if receipt_sha256(self.receipt_payload) != self.receipt_sha256:
            raise ReceiptError("exact memory state payload does not match its digest")

    def verify(self) -> None:
        expected = _exact_state_payload(
            source_time=self.source_time,
            structural_time_unit=self.structural_time_unit,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            relation_order=self.relation_order,
            quiescent_mass=self.quiescent_mass,
            active_masses=self.active_masses,
        )
        if expected != self.receipt_payload:
            raise ReceiptError("exact memory state differs from its receipt")


def _exact_state_payload(
    *,
    source_time: Fraction,
    structural_time_unit: str,
    topology_authority_receipt_sha256: str,
    relation_order: Sequence[DirectedRelation],
    quiescent_mass: Fraction,
    active_masses: Sequence[Fraction],
) -> bytes:
    return _canonical_bytes(
        {
            "active_masses": [_fraction_text(value) for value in active_masses],
            "constraint": SIMPLEX_CONSTRAINT_ID,
            "mass_total": _fraction_text(MEMORY_MASS_UNIT),
            "quiescent_mass": _fraction_text(quiescent_mass),
            "relation_order": [_relation_payload(value) for value in relation_order],
            "schema": "glew.memory.exact_correlated_mass_state.v1",
            "source_time": _fraction_text(source_time),
            "structural_time_unit": structural_time_unit,
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


def create_quiescent_memory_state(
    *,
    source_time: Fraction,
    structural_time_unit: str,
    topology_authority_receipt_sha256: str,
    relations: Sequence[DirectedRelation] = (),
) -> ExactMemoryMassState:
    """Create one clean state with all mass in the quiet reservoir."""

    require_fraction(source_time, "memory source_time")
    require_identifier(structural_time_unit, "memory structural_time_unit")
    sha256_digest(topology_authority_receipt_sha256, "memory topology receipt")
    ordered = tuple(relations)
    _validate_relation_order(ordered)
    active = (Fraction(0),) * len(ordered)
    payload = _exact_state_payload(
        source_time=source_time,
        structural_time_unit=structural_time_unit,
        topology_authority_receipt_sha256=topology_authority_receipt_sha256,
        relation_order=ordered,
        quiescent_mass=MEMORY_MASS_UNIT,
        active_masses=active,
    )
    return ExactMemoryMassState(
        source_time=source_time,
        structural_time_unit=structural_time_unit,
        topology_authority_receipt_sha256=topology_authority_receipt_sha256,
        relation_order=ordered,
        quiescent_mass=MEMORY_MASS_UNIT,
        active_masses=active,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )


@dataclass(frozen=True, slots=True)
class CertifiedMemoryMassState:
    """Outward component enclosures plus one inseparable exact simplex."""

    source_time: Fraction
    structural_time_unit: str
    topology_authority_receipt_sha256: str
    relation_order: tuple[DirectedRelation, ...]
    quiescent_mass: CertifiedBall
    active_masses: tuple[CertifiedBall, ...]
    exact_total_mass: Fraction
    constraint_id: str
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        require_fraction(self.source_time, "memory source_time")
        require_identifier(self.structural_time_unit, "memory structural_time_unit")
        sha256_digest(
            self.topology_authority_receipt_sha256,
            "memory topology authority receipt",
        )
        _validate_relation_order(self.relation_order)
        if len(self.active_masses) != len(self.relation_order):
            raise ReceiptError("certified masses do not cover the canonical relations")
        _verify_ball_authority(self.quiescent_mass)
        for value in self.active_masses:
            _verify_ball_authority(value)
        require_fraction(self.exact_total_mass, "memory exact_total_mass")
        if self.exact_total_mass != MEMORY_MASS_UNIT:
            raise ReceiptError("memory field has exactly one conserved mass unit")
        if self.constraint_id != SIMPLEX_CONSTRAINT_ID:
            raise ReceiptError("certified memory state lost its correlated simplex")
        self._verify_simplex_feasibility()
        sha256_digest(self.receipt_sha256, "certified memory state receipt")
        if not isinstance(self.receipt_payload, bytes) or not self.receipt_payload:
            raise ReceiptError("certified memory state requires canonical receipt bytes")
        if receipt_sha256(self.receipt_payload) != self.receipt_sha256:
            raise ReceiptError("certified memory state payload does not match its digest")

    def _verify_simplex_feasibility(self) -> None:
        bounds = tuple(_ball_bounds(value) for value in self.components)
        if any(upper < 0 or lower > MEMORY_MASS_UNIT for lower, upper in bounds):
            raise ReceiptError("a component enclosure excludes the nonnegative simplex")
        if sum((lower for lower, _ in bounds), Fraction(0)) > MEMORY_MASS_UNIT:
            raise ReceiptError("component lower bounds exclude conserved total mass")
        if sum((upper for _, upper in bounds), Fraction(0)) < MEMORY_MASS_UNIT:
            raise ReceiptError("component upper bounds exclude conserved total mass")

    @property
    def components(self) -> tuple[CertifiedBall, ...]:
        return (self.quiescent_mass, *self.active_masses)

    def verify(self) -> None:
        expected = _certified_state_payload(
            source_time=self.source_time,
            structural_time_unit=self.structural_time_unit,
            topology_authority_receipt_sha256=(
                self.topology_authority_receipt_sha256
            ),
            relation_order=self.relation_order,
            quiescent_mass=self.quiescent_mass,
            active_masses=self.active_masses,
        )
        if expected != self.receipt_payload:
            raise ReceiptError("certified memory state differs from its receipt")


def _certified_state_payload(
    *,
    source_time: Fraction,
    structural_time_unit: str,
    topology_authority_receipt_sha256: str,
    relation_order: Sequence[DirectedRelation],
    quiescent_mass: CertifiedBall,
    active_masses: Sequence[CertifiedBall],
) -> bytes:
    return _canonical_bytes(
        {
            "active_mass_enclosures": [_ball_payload(value) for value in active_masses],
            "constraint": {
                "equation": "m_quiescent+sum(m_active[e])=1",
                "id": SIMPLEX_CONSTRAINT_ID,
                "nonnegative_domain": True,
            },
            "mass_total": _fraction_text(MEMORY_MASS_UNIT),
            "quiescent_mass_enclosure": _ball_payload(quiescent_mass),
            "relation_order": [_relation_payload(value) for value in relation_order],
            "schema": "glew.memory.certified_correlated_mass_state.v1",
            "source_time": _fraction_text(source_time),
            "structural_time_unit": structural_time_unit,
            "topology_authority_receipt_sha256": (
                topology_authority_receipt_sha256
            ),
        }
    )


MemoryMassState = ExactMemoryMassState | CertifiedMemoryMassState


def _state_digest(state: MemoryMassState) -> str:
    return state.receipt_sha256


def _state_components(state: MemoryMassState):
    return (state.quiescent_mass, *state.active_masses)


def memory_element_calibration_receipt_payload(
    *,
    element_id: str,
    relation: DirectedRelation,
    stiffness: Fraction,
    damping: Fraction,
    structural_time_unit: str,
    derivation_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "damping": _fraction_text(damping),
            "derivation_receipt_sha256": derivation_receipt_sha256,
            "element_id": element_id,
            "frequency_equation": "nu=stiffness/damping",
            "relation": _relation_payload(relation),
            "schema": "glew.memory.local_element_calibration.v1",
            "stiffness": _fraction_text(stiffness),
            "structural_time_unit": structural_time_unit,
        }
    )


@dataclass(frozen=True, slots=True)
class MemoryElementCalibration:
    """Measured or emulated local stiffness/damping authority."""

    element_id: str
    relation: DirectedRelation
    stiffness: Fraction
    damping: Fraction
    structural_time_unit: str
    derivation_receipt_sha256: str
    calibration_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.element_id, "memory element_id")
        if not isinstance(self.relation, DirectedRelation):
            raise ReceiptError("memory calibration requires a directed relation")
        require_fraction(self.stiffness, "memory stiffness")
        require_fraction(self.damping, "memory damping")
        if self.stiffness <= 0 or self.damping <= 0:
            raise ReceiptError("memory stiffness and damping must be strictly positive")
        require_identifier(self.structural_time_unit, "calibration structural_time_unit")
        sha256_digest(self.derivation_receipt_sha256, "calibration derivation receipt")
        sha256_digest(self.calibration_receipt_sha256, "memory calibration receipt")

    @property
    def frequency(self) -> Fraction:
        return self.stiffness / self.damping

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.derivation_receipt_sha256, "memory calibration derivation receipt"
        )
        mounted = receipt_registry.resolve(
            self.calibration_receipt_sha256, "memory calibration receipt"
        )
        expected = memory_element_calibration_receipt_payload(
            element_id=self.element_id,
            relation=self.relation,
            stiffness=self.stiffness,
            damping=self.damping,
            structural_time_unit=self.structural_time_unit,
            derivation_receipt_sha256=self.derivation_receipt_sha256,
        )
        if mounted != expected:
            raise ReceiptError("memory calibration differs from its mounted receipt")


def relation_drive_receipt_payload(
    *,
    relation: DirectedRelation,
    joint_energy_density: Fraction,
    relation_support: Fraction,
    experience_origin: str,
    full_field_commit_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "experience_origin": experience_origin,
            "excitation_equation": "g=joint_energy_density*relation_support",
            "full_field_commit_receipt_sha256": full_field_commit_receipt_sha256,
            "joint_energy_density": _fraction_text(joint_energy_density),
            "relation": _relation_payload(relation),
            "relation_support": _fraction_text(relation_support),
            "schema": "glew.memory.full_field_relation_drive.v1",
        }
    )


@dataclass(frozen=True, slots=True)
class RelationDrive:
    """Exact full-field support from one eligible fresh lived experience."""

    relation: DirectedRelation
    joint_energy_density: Fraction
    relation_support: Fraction
    experience_origin: str
    full_field_commit_receipt_sha256: str
    drive_receipt_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.relation, DirectedRelation):
            raise ReceiptError("relation drive requires a directed relation")
        require_fraction(self.joint_energy_density, "joint memory energy density")
        require_fraction(self.relation_support, "relation support")
        if self.joint_energy_density < 0:
            raise ReceiptError("joint memory energy density cannot be negative")
        if not Fraction(0) <= self.relation_support <= Fraction(1):
            raise ReceiptError("relation support must remain in the Cauchy-Schwarz interval")
        if self.experience_origin not in {"fresh_external", "explicit_story_emulator"}:
            raise ReceiptError(
                "only fresh external or explicit story-emulator experience can fund memory"
            )
        sha256_digest(self.full_field_commit_receipt_sha256, "full-field commit receipt")
        sha256_digest(self.drive_receipt_sha256, "relation drive receipt")

    @property
    def excitation_rate(self) -> Fraction:
        return self.joint_energy_density * self.relation_support

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.full_field_commit_receipt_sha256, "full-field commit receipt"
        )
        mounted = receipt_registry.resolve(self.drive_receipt_sha256, "relation drive receipt")
        expected = relation_drive_receipt_payload(
            relation=self.relation,
            joint_energy_density=self.joint_energy_density,
            relation_support=self.relation_support,
            experience_origin=self.experience_origin,
            full_field_commit_receipt_sha256=self.full_field_commit_receipt_sha256,
        )
        if mounted != expected:
            raise ReceiptError("relation drive differs from its mounted receipt")


def all_lane_negative_space_receipt_payload(
    *,
    topology_authority_receipt_sha256: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    structural_time_unit: str,
    active_lane_ids: Sequence[str],
    lane_l1_proof_receipt_sha256s: Sequence[str],
) -> bytes:
    return _canonical_bytes(
        {
            "active_lane_ids": list(active_lane_ids),
            "lane_l1_proof_receipt_sha256s": list(lane_l1_proof_receipt_sha256s),
            "predicate": "every_authoritatively_active_lane_is_canonical_L1_Negative_Space",
            "schema": "glew.memory.all_lane_negative_space_proof.v1",
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "structural_time_unit": structural_time_unit,
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class AllLaneNegativeSpaceProof:
    """Exact interval-bound proof authorizing natural memory decay."""

    topology_authority_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    structural_time_unit: str
    active_lane_ids: tuple[str, ...]
    lane_l1_proof_receipt_sha256s: tuple[str, ...]
    aggregate_receipt_sha256: str

    def __post_init__(self) -> None:
        sha256_digest(self.topology_authority_receipt_sha256, "Negative Space topology receipt")
        require_fraction(self.source_time_start, "Negative Space source_time_start")
        require_fraction(self.source_time_end, "Negative Space source_time_end")
        if self.source_time_end <= self.source_time_start:
            raise ReceiptError("Negative Space proof requires a positive source-time interval")
        require_identifier(self.structural_time_unit, "Negative Space structural_time_unit")
        if not self.active_lane_ids:
            raise ReceiptError("all-lane Negative Space proof requires active lanes")
        for lane_id in self.active_lane_ids:
            require_identifier(lane_id, "Negative Space lane_id")
        if self.active_lane_ids != tuple(sorted(self.active_lane_ids)) or len(
            set(self.active_lane_ids)
        ) != len(self.active_lane_ids):
            raise ReceiptError("Negative Space active lanes must be unique and canonical")
        if len(self.lane_l1_proof_receipt_sha256s) != len(self.active_lane_ids):
            raise ReceiptError("every active lane requires one canonical L1 proof")
        for digest in self.lane_l1_proof_receipt_sha256s:
            sha256_digest(digest, "lane L1 Negative Space proof receipt")
        sha256_digest(self.aggregate_receipt_sha256, "all-lane Negative Space receipt")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.topology_authority_receipt_sha256, "Negative Space topology receipt"
        )
        for digest in self.lane_l1_proof_receipt_sha256s:
            receipt_registry.resolve(digest, "lane L1 Negative Space proof receipt")
        mounted = receipt_registry.resolve(
            self.aggregate_receipt_sha256, "all-lane Negative Space receipt"
        )
        expected = all_lane_negative_space_receipt_payload(
            topology_authority_receipt_sha256=self.topology_authority_receipt_sha256,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            structural_time_unit=self.structural_time_unit,
            active_lane_ids=self.active_lane_ids,
            lane_l1_proof_receipt_sha256s=self.lane_l1_proof_receipt_sha256s,
        )
        if mounted != expected:
            raise ReceiptError("all-lane Negative Space proof differs from its receipt")


def mass_flow_authority_receipt_payload(
    *,
    authority_id: str,
    prior_state_receipt_sha256: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    structural_time_unit: str,
    calibration_receipt_sha256s: Sequence[str],
    drive_receipt_sha256s: Sequence[str],
    negative_space_receipt_sha256: str | None,
) -> bytes:
    return _canonical_bytes(
        {
            "authority_id": authority_id,
            "backend": {
                "flint": FLINT_VERSION,
                "python_flint": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            },
            "calibration_receipt_sha256s": list(calibration_receipt_sha256s),
            "drive_receipt_sha256s": list(drive_receipt_sha256s),
            "equation": "x_next=exp(G*delta_structural_time)*x",
            "negative_space_receipt_sha256": negative_space_receipt_sha256,
            "operator": MASS_FLOW_OPERATOR_ID,
            "prior_state_receipt_sha256": prior_state_receipt_sha256,
            "schema": "glew.memory.mass_flow_authority.v1",
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "structural_time_unit": structural_time_unit,
        }
    )


@dataclass(frozen=True, slots=True)
class MemoryMassFlowAuthority:
    authority_id: str
    prior_state_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    structural_time_unit: str
    calibrations: tuple[MemoryElementCalibration, ...]
    drives: tuple[RelationDrive, ...]
    negative_space_proof: AllLaneNegativeSpaceProof | None
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.authority_id, "memory mass-flow authority_id")
        sha256_digest(self.prior_state_receipt_sha256, "prior memory state receipt")
        require_fraction(self.source_time_start, "memory source_time_start")
        require_fraction(self.source_time_end, "memory source_time_end")
        if self.source_time_end <= self.source_time_start:
            raise ReceiptError("memory evolution requires positive structural time")
        require_identifier(self.structural_time_unit, "memory structural_time_unit")
        if not all(isinstance(value, MemoryElementCalibration) for value in self.calibrations):
            raise ReceiptError("mass-flow authority contains an invalid calibration")
        if not all(isinstance(value, RelationDrive) for value in self.drives):
            raise ReceiptError("mass-flow authority contains an invalid drive")
        if self.negative_space_proof is not None and not isinstance(
            self.negative_space_proof, AllLaneNegativeSpaceProof
        ):
            raise ReceiptError("mass-flow authority contains an invalid Negative Space proof")
        sha256_digest(self.authority_receipt_sha256, "memory mass-flow authority receipt")

    @property
    def delta(self) -> Fraction:
        return self.source_time_end - self.source_time_start

    def verify(self, state: MemoryMassState, receipt_registry: ReceiptRegistry) -> None:
        state.verify()
        if self.prior_state_receipt_sha256 != _state_digest(state):
            raise ReceiptError("mass-flow authority names a different prior memory state")
        if self.source_time_start != state.source_time:
            raise ReceiptError("memory state and mass-flow authority source times differ")
        if self.structural_time_unit != state.structural_time_unit:
            raise ReceiptError("memory state and calibration use different structural time")
        calibration_relations = tuple(value.relation for value in self.calibrations)
        if calibration_relations != state.relation_order:
            raise ReceiptError("one canonical local calibration is required for every relation")
        if len({value.element_id for value in self.calibrations}) != len(self.calibrations):
            raise ReceiptError("one physical memory element cannot calibrate multiple relations")
        for calibration in self.calibrations:
            if calibration.structural_time_unit != self.structural_time_unit:
                raise ReceiptError("memory calibration has incompatible structural-time units")
            calibration.verify(receipt_registry)
        drive_relations = tuple(value.relation for value in self.drives)
        if drive_relations != tuple(sorted(drive_relations)) or len(set(drive_relations)) != len(
            drive_relations
        ):
            raise ReceiptError("relation drives must be unique and canonical")
        if not set(drive_relations).issubset(set(state.relation_order)):
            raise ReceiptError("relation drive lies outside the canonical memory domain")
        for drive in self.drives:
            drive.verify(receipt_registry)
        if self.negative_space_proof is not None:
            proof = self.negative_space_proof
            proof.verify(receipt_registry)
            if (
                proof.topology_authority_receipt_sha256
                != state.topology_authority_receipt_sha256
            ):
                raise ReceiptError(
                    "Negative Space proof belongs to a different field topology"
                )
            if (
                proof.source_time_start != self.source_time_start
                or proof.source_time_end != self.source_time_end
                or proof.structural_time_unit != self.structural_time_unit
            ):
                raise ReceiptError("Negative Space proof covers a different interval")
            if any(drive.relation_support != 0 for drive in self.drives):
                raise ReceiptError("supported experience and all-lane Negative Space cannot coexist")
        expected = mass_flow_authority_receipt_payload(
            authority_id=self.authority_id,
            prior_state_receipt_sha256=self.prior_state_receipt_sha256,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            structural_time_unit=self.structural_time_unit,
            calibration_receipt_sha256s=tuple(
                value.calibration_receipt_sha256 for value in self.calibrations
            ),
            drive_receipt_sha256s=tuple(value.drive_receipt_sha256 for value in self.drives),
            negative_space_receipt_sha256=(
                None
                if self.negative_space_proof is None
                else self.negative_space_proof.aggregate_receipt_sha256
            ),
        )
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "memory mass-flow authority receipt"
        )
        if mounted != expected:
            raise ReceiptError("memory mass-flow authority differs from its receipt")


@dataclass(frozen=True, slots=True)
class MemoryGeneratorEntry:
    row: int
    column: int
    value: Fraction


def _memory_generator(
    state: MemoryMassState, authority: MemoryMassFlowAuthority
) -> tuple[MemoryGeneratorEntry, ...]:
    relation_index = {value: index + 1 for index, value in enumerate(state.relation_order)}
    drives = {value.relation: value for value in authority.drives}
    calibration = {value.relation: value for value in authority.calibrations}
    entries: dict[tuple[int, int], Fraction] = {}
    total_growth = Fraction(0)
    decay_enabled = authority.negative_space_proof is not None
    for relation in state.relation_order:
        index = relation_index[relation]
        drive = drives.get(relation)
        growth = Fraction(0) if drive is None else drive.excitation_rate
        decay = calibration[relation].frequency if decay_enabled else Fraction(0)
        if growth:
            entries[(index, 0)] = growth
            total_growth += growth
        if decay:
            entries[(0, index)] = decay
            entries[(index, index)] = -decay
    if total_growth:
        entries[(0, 0)] = -total_growth
    result = tuple(
        MemoryGeneratorEntry(row, column, value)
        for (row, column), value in sorted(entries.items())
    )
    dimension = len(state.relation_order) + 1
    for column in range(dimension):
        column_sum = sum(
            (entry.value for entry in result if entry.column == column), Fraction(0)
        )
        if column_sum != 0:
            raise ReceiptError("memory generator does not have exact zero column sums")
        if any(
            entry.row != entry.column and entry.value < 0
            for entry in result
            if entry.column == column
        ):
            raise ReceiptError("memory generator has a negative off-diagonal")
    return result


@dataclass(frozen=True, slots=True)
class MemoryMassFlowReceipt:
    authority_receipt_sha256: str
    prior_state_receipt_sha256: str
    result_state_receipt_sha256: str
    generator_entries: tuple[MemoryGeneratorEntry, ...]
    precision_bits: int
    receipt_sha256: str
    receipt_payload: bytes


@dataclass(frozen=True, slots=True)
class MemoryMassFlowResult:
    state: CertifiedMemoryMassState
    receipt: MemoryMassFlowReceipt


def _mass_flow_result_payload(
    *,
    authority: MemoryMassFlowAuthority,
    generator: Sequence[MemoryGeneratorEntry],
    precision_bits: int,
    result_state_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "affine_conservation": "exact_zero_column_sums",
            "authority_receipt_sha256": authority.authority_receipt_sha256,
            "backend": {
                "flint": FLINT_VERSION,
                "precision_bits": precision_bits,
                "python_flint": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            },
            "generator_entries": [
                {
                    "column": value.column,
                    "row": value.row,
                    "value": _fraction_text(value.value),
                }
                for value in generator
            ],
            "nonnegative_proof": "Metzler_generator_matrix_exponential",
            "operator": MASS_FLOW_OPERATOR_ID,
            "prior_state_receipt_sha256": authority.prior_state_receipt_sha256,
            "result_state_receipt_sha256": result_state_receipt_sha256,
            "schema": "glew.memory.mass_flow_result.v1",
        }
    )


def evolve_relation_mass(
    *,
    state: MemoryMassState,
    authority: MemoryMassFlowAuthority,
    receipt_registry: ReceiptRegistry,
) -> MemoryMassFlowResult:
    """Evaluate one conservative, exact-time relation-mass exponential."""

    if not isinstance(state, (ExactMemoryMassState, CertifiedMemoryMassState)):
        raise ReceiptError("memory evolution requires a typed correlated state")
    if not isinstance(authority, MemoryMassFlowAuthority):
        raise ReceiptError("memory evolution requires a typed mass-flow authority")
    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("memory evolution requires an immutable receipt registry")
    authority.verify(state, receipt_registry)
    generator = _memory_generator(state, authority)
    exact_inputs = [authority.delta]
    exact_inputs.extend(value.value for value in generator)
    state_balls: list[CertifiedBall] = []
    if isinstance(state, ExactMemoryMassState):
        exact_inputs.extend(_state_components(state))
    else:
        state_balls.extend(state.components)
    precision_bits = _precision_for_inputs(exact_inputs, state_balls)
    flint = load_pinned_flint()
    dimension = len(state.relation_order) + 1
    with flint.ctx.workprec(precision_bits):
        matrix = flint.arb_mat(dimension, dimension)
        for entry in generator:
            matrix[entry.row, entry.column] = arb_fraction(flint, entry.value)
        transition = (matrix * arb_fraction(flint, authority.delta)).exp()
        if not all(
            transition[row, column].is_finite()
            for row in range(dimension)
            for column in range(dimension)
        ):
            raise ReceiptError("memory matrix exponential is nonfinite")
        initial_values = tuple(
            arb_fraction(flint, value)
            if isinstance(value, Fraction)
            else _arb_from_ball(flint, value)
            for value in _state_components(state)
        )
        initial = flint.arb_mat(dimension, 1, list(initial_values))
        evolved = transition * initial
        values = tuple(evolved[index, 0] for index in range(dimension))
        if not all(value.is_finite() for value in values):
            raise ReceiptError("memory mass result is nonfinite")
        balls = tuple(canonical_ball(value, precision_bits) for value in values)
    state_payload = _certified_state_payload(
        source_time=authority.source_time_end,
        structural_time_unit=authority.structural_time_unit,
        topology_authority_receipt_sha256=(
            state.topology_authority_receipt_sha256
        ),
        relation_order=state.relation_order,
        quiescent_mass=balls[0],
        active_masses=balls[1:],
    )
    result_state = CertifiedMemoryMassState(
        source_time=authority.source_time_end,
        structural_time_unit=authority.structural_time_unit,
        topology_authority_receipt_sha256=(
            state.topology_authority_receipt_sha256
        ),
        relation_order=state.relation_order,
        quiescent_mass=balls[0],
        active_masses=balls[1:],
        exact_total_mass=MEMORY_MASS_UNIT,
        constraint_id=SIMPLEX_CONSTRAINT_ID,
        receipt_sha256=receipt_sha256(state_payload),
        receipt_payload=state_payload,
    )
    result_payload = _mass_flow_result_payload(
        authority=authority,
        generator=generator,
        precision_bits=precision_bits,
        result_state_receipt_sha256=result_state.receipt_sha256,
    )
    flow_receipt = MemoryMassFlowReceipt(
        authority_receipt_sha256=authority.authority_receipt_sha256,
        prior_state_receipt_sha256=authority.prior_state_receipt_sha256,
        result_state_receipt_sha256=result_state.receipt_sha256,
        generator_entries=generator,
        precision_bits=precision_bits,
        receipt_sha256=receipt_sha256(result_payload),
        receipt_payload=result_payload,
    )
    return MemoryMassFlowResult(state=result_state, receipt=flow_receipt)


def validity_mask_receipt_payload(
    *,
    mask_id: str,
    topology_authority_receipt_sha256: str,
    dimension: int,
    active_coordinates: Sequence[int],
) -> bytes:
    return _canonical_bytes(
        {
            "active_coordinates": list(active_coordinates),
            "dimension": dimension,
            "mask_id": mask_id,
            "schema": "glew.memory.current_validity_operator.v1",
            "topology_authority_receipt_sha256": topology_authority_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class MemoryValidityMask:
    mask_id: str
    topology_authority_receipt_sha256: str
    dimension: int
    active_coordinates: tuple[int, ...]
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.mask_id, "memory validity mask_id")
        sha256_digest(self.topology_authority_receipt_sha256, "validity topology receipt")
        if isinstance(self.dimension, bool) or not isinstance(self.dimension, int) or self.dimension <= 0:
            raise ReceiptError("validity-mask dimension must be positive")
        if not self.active_coordinates:
            raise ReceiptError("validity mask must retain at least one coordinate")
        if self.active_coordinates != tuple(sorted(self.active_coordinates)) or len(
            set(self.active_coordinates)
        ) != len(self.active_coordinates):
            raise ReceiptError("validity coordinates must be unique and canonical")
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value >= self.dimension
            for value in self.active_coordinates
        ):
            raise ReceiptError("validity coordinate lies outside the field")
        sha256_digest(self.authority_receipt_sha256, "validity-mask authority receipt")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        receipt_registry.resolve(
            self.topology_authority_receipt_sha256, "validity topology receipt"
        )
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256, "validity-mask authority receipt"
        )
        expected = validity_mask_receipt_payload(
            mask_id=self.mask_id,
            topology_authority_receipt_sha256=self.topology_authority_receipt_sha256,
            dimension=self.dimension,
            active_coordinates=self.active_coordinates,
        )
        if mounted != expected:
            raise ReceiptError("validity mask differs from its mounted receipt")


def h_mem_authority_receipt_payload(
    *,
    operator_id: str,
    memory_state_receipt_sha256: str,
    mode_bank_receipt_sha256: str,
    validity_mask_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes(
        {
            "backend": {
                "flint": FLINT_VERSION,
                "python_flint": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            },
            "formula": (
                "sum_e(m_e*((A_e+A_e_dagger)+i*(A_e-A_e_dagger))/(2*sqrt(2)))"
            ),
            "memory_state_receipt_sha256": memory_state_receipt_sha256,
            "mode_bank_receipt_sha256": mode_bank_receipt_sha256,
            "operator_id": operator_id,
            "schema": "glew.memory.H_mem_authority.v1",
            "validity_mask_receipt_sha256": validity_mask_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class HMemOperatorAuthority:
    operator_id: str
    memory_state_receipt_sha256: str
    mode_bank_receipt_sha256: str
    validity_mask_receipt_sha256: str
    authority_receipt_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.operator_id, "H_mem operator_id")
        if self.operator_id != H_MEM_OPERATOR_ID:
            raise ReceiptError("unratified H_mem operator identifier")
        sha256_digest(self.memory_state_receipt_sha256, "H_mem memory state receipt")
        sha256_digest(self.mode_bank_receipt_sha256, "H_mem mode-bank receipt")
        sha256_digest(self.validity_mask_receipt_sha256, "H_mem validity-mask receipt")
        sha256_digest(self.authority_receipt_sha256, "H_mem authority receipt")

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        mounted = receipt_registry.resolve(self.authority_receipt_sha256, "H_mem authority receipt")
        expected = h_mem_authority_receipt_payload(
            operator_id=self.operator_id,
            memory_state_receipt_sha256=self.memory_state_receipt_sha256,
            mode_bank_receipt_sha256=self.mode_bank_receipt_sha256,
            validity_mask_receipt_sha256=self.validity_mask_receipt_sha256,
        )
        if mounted != expected:
            raise ReceiptError("H_mem authority differs from its mounted receipt")


@dataclass(frozen=True, slots=True)
class CertifiedMemoryHamiltonian:
    dimension: int
    entries: tuple[tuple[CertifiedComplexBall, ...], ...]
    memory_state_receipt_sha256: str
    mode_bank_receipt_sha256: str
    validity_mask_receipt_sha256: str
    authority_receipt_sha256: str
    expression_receipt_sha256: str
    expression_receipt_payload: bytes
    spectral_norm_bound: Fraction
    working_precision_bits: int
    receipt_sha256: str
    receipt_payload: bytes

    def __post_init__(self) -> None:
        if (
            isinstance(self.dimension, bool)
            or not isinstance(self.dimension, int)
            or self.dimension <= 0
        ):
            raise ReceiptError("certified H_mem dimension must be positive")
        for value, name in (
            (self.memory_state_receipt_sha256, "H_mem memory-state receipt"),
            (self.mode_bank_receipt_sha256, "H_mem mode-bank receipt"),
            (self.validity_mask_receipt_sha256, "H_mem validity-mask receipt"),
            (self.authority_receipt_sha256, "H_mem authority receipt"),
            (self.expression_receipt_sha256, "H_mem expression receipt"),
            (self.receipt_sha256, "H_mem result receipt"),
        ):
            sha256_digest(value, name)
        require_fraction(self.spectral_norm_bound, "H_mem spectral-norm bound")
        if self.spectral_norm_bound != MEMORY_MASS_UNIT:
            raise ReceiptError("H_mem bound must follow the conserved memory mass unit")
        if (
            isinstance(self.working_precision_bits, bool)
            or not isinstance(self.working_precision_bits, int)
            or self.working_precision_bits <= 0
        ):
            raise ReceiptError("H_mem precision must be a positive integer")
        if not isinstance(self.receipt_payload, bytes) or not self.receipt_payload:
            raise ReceiptError("H_mem result requires canonical receipt bytes")

    def verify(self) -> None:
        if (
            not isinstance(self.expression_receipt_payload, bytes)
            or not self.expression_receipt_payload
            or receipt_sha256(self.expression_receipt_payload)
            != self.expression_receipt_sha256
        ):
            raise ReceiptError("H_mem expression receipt payload is not content-bound")
        if len(self.entries) != self.dimension or any(
            len(row) != self.dimension for row in self.entries
        ):
            raise ReceiptError("certified H_mem matrix dimension is inconsistent")
        for row in range(self.dimension):
            for column in range(self.dimension):
                value = self.entries[row][column]
                if not isinstance(value, CertifiedComplexBall):
                    raise ReceiptError("certified H_mem contains an invalid entry")
                if self.entries[column][row].real != value.real or self.entries[
                    column
                ][row].imag != _negate_ball(value.imag):
                    raise ReceiptError("certified H_mem lost expression-level Hermiticity")
        expected = _h_mem_result_payload(
            dimension=self.dimension,
            entries=self.entries,
            memory_state_receipt_sha256=self.memory_state_receipt_sha256,
            mode_bank_receipt_sha256=self.mode_bank_receipt_sha256,
            validity_mask_receipt_sha256=self.validity_mask_receipt_sha256,
            authority_receipt_sha256=self.authority_receipt_sha256,
            expression_receipt_sha256=self.expression_receipt_sha256,
            spectral_norm_bound=self.spectral_norm_bound,
            working_precision_bits=self.working_precision_bits,
        )
        if expected != self.receipt_payload or receipt_sha256(expected) != self.receipt_sha256:
            raise ReceiptError("certified H_mem differs from its result receipt")

    def require_field_integration(self) -> None:
        """Fail closed until field evolution accepts certified Hermitian balls."""

        raise MemoryFieldIntegrationRequired(FIELD_H_MEM_INTEGRATION_REQUIREMENT)


class MemoryFieldIntegrationRequired(ReceiptError):
    """The certified operator exists but the rational-only field cannot ingest it."""


def _h_mem_expression_payload(
    *,
    state: MemoryMassState,
    bank: CertifiedModeBank,
    validity_mask: MemoryValidityMask,
) -> bytes:
    masses = state.active_masses
    return _canonical_bytes(
        {
            "direction_rule": "ordered_mode_pair_uses_positive_i_skew_term",
            "factor": "1/(2*sqrt(2))",
            "mass_expressions": [
                (
                    {"exact": _fraction_text(value)}
                    if isinstance(value, Fraction)
                    else {"certified_interval": _ball_payload(value)}
                )
                for value in masses
            ],
            "mass_correlation": {
                "constraint": SIMPLEX_CONSTRAINT_ID,
                "independent_component_selection": "forbidden",
                "state_receipt_sha256": state.receipt_sha256,
            },
            "memory_state_receipt_sha256": state.receipt_sha256,
            "mode_bank_receipt_sha256": bank.receipt_sha256,
            "relations": [_relation_payload(value) for value in state.relation_order],
            "schema": "glew.memory.H_mem_correlated_expression.v1",
            "validity_mask_receipt_sha256": validity_mask.authority_receipt_sha256,
        }
    )


def _h_mem_result_payload(
    *,
    dimension: int,
    entries: Sequence[Sequence[CertifiedComplexBall]],
    memory_state_receipt_sha256: str,
    mode_bank_receipt_sha256: str,
    validity_mask_receipt_sha256: str,
    authority_receipt_sha256: str,
    expression_receipt_sha256: str,
    spectral_norm_bound: Fraction,
    working_precision_bits: int,
) -> bytes:
    return _canonical_bytes(
        {
            "authority_receipt_sha256": authority_receipt_sha256,
            "backend": {
                "flint": FLINT_VERSION,
                "precision_bits": working_precision_bits,
                "python_flint": PYTHON_FLINT_VERSION,
                "threads": 1,
                "wheel_sha256": PYTHON_FLINT_WHEEL_SHA256,
            },
            "dimension": dimension,
            "entries": [
                [_complex_ball_payload(value) for value in row] for row in entries
            ],
            "expression_receipt_sha256": expression_receipt_sha256,
            "hermiticity": "same_correlated_expression_and_exact_conjugate_assignment",
            "integration_status": "certified_operator_waiting_for_ball_Hamiltonian_field_ingestion",
            "memory_state_receipt_sha256": memory_state_receipt_sha256,
            "mode_bank_receipt_sha256": mode_bank_receipt_sha256,
            "schema": "glew.memory.certified_H_mem.v1",
            "spectral_norm_bound": _fraction_text(spectral_norm_bound),
            "validity_mask_receipt_sha256": validity_mask_receipt_sha256,
        }
    )


def _mass_arb(flint, value: Fraction | CertifiedBall):
    return arb_fraction(flint, value) if isinstance(value, Fraction) else _arb_from_ball(flint, value)


def _mass_is_exact_zero(value: Fraction | CertifiedBall) -> bool:
    if isinstance(value, Fraction):
        return value == 0
    lower, upper = _ball_bounds(value)
    return lower == 0 and upper == 0


def build_certified_h_mem(
    *,
    topology: MountedFieldTopology,
    bank: CertifiedModeBank,
    state: MemoryMassState,
    validity_mask: MemoryValidityMask,
    authority: HMemOperatorAuthority,
    receipt_registry: ReceiptRegistry,
) -> CertifiedMemoryHamiltonian:
    """Evaluate the direction-distinct Hermitian memory field with Arb."""

    if not isinstance(receipt_registry, ReceiptRegistry):
        raise ReceiptError("H_mem requires an immutable receipt registry")
    topology.verify(receipt_registry)
    bank.verify(topology, recompute=True)
    state.verify()
    validity_mask.verify(receipt_registry)
    authority.verify(receipt_registry)
    if validity_mask.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
        raise ReceiptError("H_mem validity mask belongs to a different topology")
    if validity_mask.dimension != bank.dimension:
        raise ReceiptError("H_mem validity mask and mode bank dimensions differ")
    if authority.memory_state_receipt_sha256 != state.receipt_sha256:
        raise ReceiptError("H_mem authority names a different memory state")
    if authority.mode_bank_receipt_sha256 != bank.receipt_sha256:
        raise ReceiptError("H_mem authority names a different mode bank")
    if authority.validity_mask_receipt_sha256 != validity_mask.authority_receipt_sha256:
        raise ReceiptError("H_mem authority names a different validity mask")
    if state.topology_authority_receipt_sha256 != topology.authority_receipt_sha256:
        raise ReceiptError("memory mass state belongs to a different topology")
    active_relation_masses = tuple(
        (relation, mass)
        for relation, mass in zip(
            state.relation_order, state.active_masses, strict=True
        )
        if not _mass_is_exact_zero(mass)
    )
    if any(
        relation.source_mode_index >= bank.rank or relation.target_mode_index >= bank.rank
        for relation, _ in active_relation_masses
    ):
        raise ReceiptError("memory relation names an unavailable full-field mode")
    for relation, _ in active_relation_masses:
        if (
            relation.source_mode_receipt_sha256
            != bank.modes[relation.source_mode_index].receipt_sha256
            or relation.target_mode_receipt_sha256
            != bank.modes[relation.target_mode_index].receipt_sha256
        ):
            raise ReceiptError(
                "memory relation endpoint identity differs from the full-field mode bank"
            )
    fraction_inputs: list[Fraction] = []
    ball_inputs: list[CertifiedBall] = []
    for value in state.active_masses:
        if isinstance(value, Fraction):
            fraction_inputs.append(value)
        else:
            ball_inputs.append(value)
    for mode in bank.modes:
        for amplitude in mode.projective_components:
            fraction_inputs.extend((amplitude.real, amplitude.imag))
    precision_bits = max(
        bank.working_precision_bits,
        _precision_for_inputs(fraction_inputs, ball_inputs),
    )
    flint = load_pinned_flint()
    active = set(validity_mask.active_coordinates)
    with flint.ctx.workprec(precision_bits):
        normalized: list[tuple[object, ...]] = []
        exact_masked_modes = []
        for mode in bank.modes:
            exact_values = tuple(
                amplitude
                if index in active
                else type(amplitude)(Fraction(0), Fraction(0))
                for index, amplitude in enumerate(mode.projective_components)
            )
            exact_norm_squared = sum(
                (
                    value.real * value.real + value.imag * value.imag
                    for value in exact_values
                ),
                Fraction(0),
            )
            if exact_norm_squared <= 0:
                raise ReceiptError("current validity mask cannot certify a nonzero endpoint mode")
            values = tuple(
                flint.acb(
                    arb_fraction(flint, value.real),
                    arb_fraction(flint, value.imag),
                )
                for value in exact_values
            )
            norm = arb_fraction(flint, exact_norm_squared).sqrt()
            exact_masked_modes.append(exact_values)
            normalized.append(tuple(value / norm for value in values))

        for relation, _ in active_relation_masses:
            if relation.source_mode_index == relation.target_mode_index:
                continue
            left = exact_masked_modes[relation.source_mode_index]
            right = exact_masked_modes[relation.target_mode_index]
            left_norm = sum(
                (value.real * value.real + value.imag * value.imag for value in left),
                Fraction(0),
            )
            right_norm = sum(
                (value.real * value.real + value.imag * value.imag for value in right),
                Fraction(0),
            )
            inner_real = sum(
                (
                    u.real * v.real + u.imag * v.imag
                    for u, v in zip(left, right, strict=True)
                ),
                Fraction(0),
            )
            inner_imag = sum(
                (
                    u.real * v.imag - u.imag * v.real
                    for u, v in zip(left, right, strict=True)
                ),
                Fraction(0),
            )
            gram = left_norm * right_norm - (
                inner_real * inner_real + inner_imag * inner_imag
            )
            if gram <= 0:
                raise ReceiptError("validity mask makes directed mode endpoints dependent or ambiguous")

        mass_expressions = tuple(
            (relation, _mass_arb(flint, mass))
            for relation, mass in active_relation_masses
        )
        sqrt_two = flint.arb(2).sqrt()
        denominator = 2 * sqrt_two
        matrix: list[list[object | None]] = [
            [None for _ in range(bank.dimension)] for _ in range(bank.dimension)
        ]
        imaginary_unit = flint.acb(0, 1)
        for row in range(bank.dimension):
            for column in range(row, bank.dimension):
                expression = flint.acb(0)
                for relation, mass in mass_expressions:
                    source = normalized[relation.source_mode_index]
                    target = normalized[relation.target_mode_index]
                    if relation.source_mode_index == relation.target_mode_index:
                        relation_value = source[row] * source[column].conjugate()
                    else:
                        a = source[row] * target[column].conjugate()
                        a_dagger = target[row] * source[column].conjugate()
                        relation_value = (
                            (a + a_dagger) + imaginary_unit * (a - a_dagger)
                        ) / denominator
                    expression += mass * relation_value
                if row == column:
                    expression = flint.acb(expression.real, 0)
                if not expression.is_finite():
                    raise ReceiptError("H_mem expression is nonfinite")
                matrix[row][column] = expression
                if row != column:
                    matrix[column][row] = expression.conjugate()
        entries = tuple(
            tuple(
                CertifiedComplexBall(
                    real=canonical_ball(value.real, precision_bits),
                    imag=canonical_ball(value.imag, precision_bits),
                )
                for value in row
                if value is not None
            )
            for row in matrix
        )
    expression_payload = _h_mem_expression_payload(
        state=state, bank=bank, validity_mask=validity_mask
    )
    expression_digest = receipt_sha256(expression_payload)
    result_payload = _h_mem_result_payload(
        dimension=bank.dimension,
        entries=entries,
        memory_state_receipt_sha256=state.receipt_sha256,
        mode_bank_receipt_sha256=bank.receipt_sha256,
        validity_mask_receipt_sha256=validity_mask.authority_receipt_sha256,
        authority_receipt_sha256=authority.authority_receipt_sha256,
        expression_receipt_sha256=expression_digest,
        spectral_norm_bound=MEMORY_MASS_UNIT,
        working_precision_bits=precision_bits,
    )
    result = CertifiedMemoryHamiltonian(
        dimension=bank.dimension,
        entries=entries,
        memory_state_receipt_sha256=state.receipt_sha256,
        mode_bank_receipt_sha256=bank.receipt_sha256,
        validity_mask_receipt_sha256=validity_mask.authority_receipt_sha256,
        authority_receipt_sha256=authority.authority_receipt_sha256,
        expression_receipt_sha256=expression_digest,
        expression_receipt_payload=expression_payload,
        spectral_norm_bound=MEMORY_MASS_UNIT,
        working_precision_bits=precision_bits,
        receipt_sha256=receipt_sha256(result_payload),
        receipt_payload=result_payload,
    )
    result.verify()
    return result


__all__ = (
    "AllLaneNegativeSpaceProof",
    "CertifiedMemoryHamiltonian",
    "CertifiedMemoryMassState",
    "DirectedRelation",
    "ExactMemoryMassState",
    "FIELD_H_MEM_INTEGRATION_REQUIREMENT",
    "HMemOperatorAuthority",
    "H_MEM_OPERATOR_ID",
    "MASS_FLOW_OPERATOR_ID",
    "MEMORY_MASS_UNIT",
    "MemoryElementCalibration",
    "MemoryFieldIntegrationRequired",
    "MemoryMassFlowAuthority",
    "MemoryMassFlowReceipt",
    "MemoryMassFlowResult",
    "MemoryValidityMask",
    "RelationDrive",
    "all_lane_negative_space_receipt_payload",
    "build_certified_h_mem",
    "create_quiescent_memory_state",
    "evolve_relation_mass",
    "h_mem_authority_receipt_payload",
    "mass_flow_authority_receipt_payload",
    "memory_element_calibration_receipt_payload",
    "relation_drive_receipt_payload",
    "validity_mask_receipt_payload",
)
