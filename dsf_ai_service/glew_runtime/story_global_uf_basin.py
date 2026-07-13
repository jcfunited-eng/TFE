"""Two-stage six-lane story Global-UF execution.

Preparation executes the authenticated five-sense story and the one mounted
typed-language capture through frozen L0--L4, mounts all sensor tangent rows
plus the complete typed contingent cone, and seals every replay separately.
It creates no origin, SafeMode, event-support, L6-scope, or commit authority.

Evaluation accepts those authorities only after the caller has mounted them
for each exact replay seal.  Missing, reused, or cross-scoped authority fails
closed.  Exact seven-field L4 tuples remain the primary Global-UF evidence;
sign classes are derived secondary metadata only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Iterable, Mapping

from .certified_backend import CertifiedBall
from .closed_experience import (
    ClosedExperienceEvidencePreparation,
    KernelNativeInputStream,
    MountedL5GovernanceProfile,
    ProviderStatus,
    SealedClosedExperience,
    prepare_closed_experience_evidence,
    seal_closed_experience,
)
from .commit import (
    ApplicabilityState,
    AuthorityDisposition,
    GovernedFact,
    L6ScopeAuthority,
    PendingGlobalUFConjunction,
    evaluate_pending_global_uf_conjunction,
    l6_evaluation_receipt_payload,
)
from .event_support import (
    EventSupportEvaluation,
    EventSupportEvaluationStatus,
    MemoryEnergyAuthority,
    evaluate_event_support,
)
from .experience_origin import ExperienceOriginAuthority, ExperienceOriginKind
from .expression_modes import (
    ExpressionModeBank,
    ExpressionModeBoundaryResult,
    ExpressionRecognitionStatus,
    evaluate_expression_mode_boundary,
)
from .expressions import (
    ClosedExperienceFieldExpression,
    ExpressionEvaluationStatus,
    FieldExpressionEvaluation,
    FieldExpressionStep,
    PrecisionScheduleAuthority,
    create_closed_experience_expression,
    evaluate_closed_experience_expression,
)
from .field import (
    ExactFieldState,
    FieldEvolutionAuthority,
    HamiltonianEntry,
    LocalRate,
    MountedFieldTopology,
    canonical_component_partition,
    evolution_authority_receipt_payload,
    source_coefficients_for_injection,
)
from .global_uf import (
    CertifiedNonnegativeClass,
    CertifiedOperatorBasinSignature,
    CommitBasinSignature,
    ExactDSFFieldTupleReceipt,
    GlobalUFReplayOutcome,
    GlobalUFReplayRequest,
    GlobalUFReplayResponse,
    GlobalUFValidationResult,
    L5DispositionState,
    L6BasinClass,
    L6BasinSignature,
    L6BasisRowSignature,
    LayerBranchGateSignature,
    MountedPreWindowState,
    MountedRawObservationWindow,
    MountedSensorResolutionProfile,
    NamedSignZeroClass,
    ObservationCoordinate,
    OperatorAvailability,
    PortKernelBasinSignature,
    PortL5BasinDisposition,
    PortReplayReceipt,
    ReplayKind,
    ReplayOutcomeStatus,
    SensorCodeResolution,
    SensorIntegerObservation,
    SignZeroClass,
    StableModeBasinSignature,
    StableModeState,
    StructuralBasinSignature,
    TypedUnicodeObservation,
    enumerate_global_uf_replay_requests,
    evaluate_global_uf_validation,
    exact_dsf_field_tuple_receipt_payload,
    global_uf_replay_outcome_receipt_payload,
    port_kernel_basin_receipt_payload,
    port_replay_receipt_payload,
    raw_observation_window_receipt_payload,
    sensor_resolution_profile_receipt_payload,
)
from .l6 import (
    ActiveLaneState,
    ConstraintRow,
    ExactRankReceipt,
    Fixed42ConstraintStack,
    L6Evaluation,
    L6EvaluationStatus,
    L6Lane,
    L6PredicateInputs,
    exact_rank_receipt,
    evaluate_l6,
)
from .language import TypedLanguageFrozenKernelInput
from .model import (
    EvidenceStream,
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)
from .operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    ResonanceOperatorAuthority,
)
from .physical_l6_tangents import (
    LaneCompletenessReceipt,
    PhysicalL6TangentProduction,
    PhysicalTangentProductionStatus,
    produce_physical_l6_tangents,
)
from .safe_mode import (
    IntegrityFact,
    MountedSafeModeScope,
    SafeModeEvaluation,
    evaluate_safe_mode,
)
from .story_chemistry import StoryChemistryRuntime
from .story_native_replay import (
    MountedAuthenticatedClosedStoryBoundary,
    MountedStoryNativeReplayProfile,
    MountedStorySensorState,
    StoryNativeReplayResult,
    StoryNativeReplayStatus,
    execute_story_native_replay,
)
from .typed_language_native_replay import (
    TypedLanguageNativeReplayResult,
    execute_typed_language_native_replay,
)


STORY_GLOBAL_UF_BASIN_OPERATOR_ID = "glew.story_global_uf.six_lane_two_stage.v2"
_DSF_FIELDS = ("D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "exact fraction")
    return f"{value.numerator}/{value.denominator}"


def _extend_records(
    registry: ReceiptRegistry, records: Iterable[ReceiptRecord]
) -> ReceiptRegistry:
    mounted = {value.digest: value.payload for value in registry.records}
    for record in records:
        if not isinstance(record, ReceiptRecord):
            raise ReceiptError("story Global-UF received an untyped receipt")
        prior = mounted.get(record.digest)
        if prior is not None and prior != record.payload:
            raise ReceiptError("story Global-UF receipt digest collision")
        mounted[record.digest] = record.payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(key, mounted[key]) for key in sorted(mounted)),
    )


def _extend_payloads(
    registry: ReceiptRegistry, payloads: Iterable[bytes]
) -> ReceiptRegistry:
    return _extend_records(
        registry,
        tuple(ReceiptRecord(receipt_sha256(value), value) for value in payloads),
    )


def story_global_uf_basin_profile_receipt_payload(
    *,
    profile_id: str,
    story_replay_profile_receipt_sha256: str,
    physical_profile_receipt_sha256: str,
    initial_field_state_receipt_sha256: str,
    hbar: Fraction,
    hamiltonian: tuple[HamiltonianEntry, ...],
    local_rates: tuple[LocalRate, ...],
    source_time_unit: str,
    max_connected_component_dimension: int,
    field_precision_bits: int,
    precision_authority_receipt_sha256: str,
    mode_bank_receipt_sha256: str,
    l5_governance_receipt_sha256: str,
) -> bytes:
    require_identifier(profile_id, "story Global-UF profile id")
    require_identifier(source_time_unit, "story Global-UF time unit")
    for value in (
        story_replay_profile_receipt_sha256,
        physical_profile_receipt_sha256,
        initial_field_state_receipt_sha256,
        precision_authority_receipt_sha256,
        mode_bank_receipt_sha256,
        l5_governance_receipt_sha256,
    ):
        sha256_digest(value, "story Global-UF profile receipt")
    require_fraction(hbar, "story Global-UF hbar")
    if hbar <= 0:
        raise ReceiptError("story Global-UF hbar must be positive")
    return _canonical_bytes(
        {
            "field_evolution": {
                "field_precision_bits": field_precision_bits,
                "hamiltonian": [
                    {
                        "column": item.column,
                        "imag": _fraction_text(item.value.imag),
                        "real": _fraction_text(item.value.real),
                        "row": item.row,
                    }
                    for item in hamiltonian
                ],
                "hbar": _fraction_text(hbar),
                "initial_field_state_receipt_sha256": initial_field_state_receipt_sha256,
                "local_rates": [
                    {
                        "decay": _fraction_text(item.decay),
                        "growth": _fraction_text(item.growth),
                        "index": item.index,
                    }
                    for item in local_rates
                ],
                "max_connected_component_dimension": max_connected_component_dimension,
                "physical_profile_receipt_sha256": physical_profile_receipt_sha256,
                "source_time_unit": source_time_unit,
            },
            "l5_governance_receipt_sha256": l5_governance_receipt_sha256,
            "mode_bank_receipt_sha256": mode_bank_receipt_sha256,
            "operator": STORY_GLOBAL_UF_BASIN_OPERATOR_ID,
            "precision_authority_receipt_sha256": precision_authority_receipt_sha256,
            "profile_id": profile_id,
            "schema": "glew.story_global_uf.basin_runtime_profile.v2",
            "story_replay_profile_receipt_sha256": story_replay_profile_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class MountedStoryGlobalUFBasinProfile:
    profile_id: str
    story_replay_profile_receipt_sha256: str
    physical_profile_receipt_sha256: str
    initial_field_state: ExactFieldState
    hbar: Fraction
    hamiltonian: tuple[HamiltonianEntry, ...]
    local_rates: tuple[LocalRate, ...]
    source_time_unit: str
    max_connected_component_dimension: int
    field_precision_bits: int
    precision_authority: PrecisionScheduleAuthority
    mode_bank: ExpressionModeBank
    l5_governance: MountedL5GovernanceProfile
    authority_receipt_sha256: str
    authority_receipt_payload: bytes

    def verify(
        self,
        *,
        story_profile: MountedStoryNativeReplayProfile,
        pre_window_state: MountedPreWindowState,
        topology: MountedFieldTopology,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.story_replay_profile_receipt_sha256 != story_profile.authority_receipt_sha256:
            raise ReceiptError("basin profile belongs to another story profile")
        story_profile.verify(receipt_registry)
        topology.verify(receipt_registry)
        expected_story = tuple(item.key for item in story_profile.topology.ordered_port_fibers)
        actual = tuple(item.key for item in topology.ordered_port_fibers)
        if tuple(key for key in actual if key in set(expected_story)) != expected_story:
            raise ReceiptError("six-lane topology does not preserve all story ports")
        if len(actual) != 6 or {key[0] for key in actual} != {item.value for item in L6Lane}:
            raise ReceiptError("story Global-UF requires exactly all six native lanes")
        receipt_registry.resolve(self.physical_profile_receipt_sha256, "physical profile")
        self.initial_field_state.verify(receipt_registry)
        if (
            self.initial_field_state.topology_authority_receipt_sha256
            != topology.authority_receipt_sha256
            or len(self.initial_field_state.amplitudes) != topology.dimension
            or self.initial_field_state.source_time >= story_profile.grid.timestamps[0]
            or pre_window_state.field_state_receipt_sha256
            != self.initial_field_state.authority_receipt_sha256
        ):
            raise ReceiptError("initial six-lane field differs from pre-window state")
        self.precision_authority.verify(receipt_registry)
        self.mode_bank.verify(topology=topology, receipt_registry=receipt_registry)
        if pre_window_state.mode_state_receipt_sha256 != self.mode_bank.receipt_sha256:
            raise ReceiptError("pre-window state names another expression-mode bank")
        self.l5_governance.verify(topology, receipt_registry)
        expected = story_global_uf_basin_profile_receipt_payload(
            profile_id=self.profile_id,
            story_replay_profile_receipt_sha256=self.story_replay_profile_receipt_sha256,
            physical_profile_receipt_sha256=self.physical_profile_receipt_sha256,
            initial_field_state_receipt_sha256=self.initial_field_state.authority_receipt_sha256,
            hbar=self.hbar,
            hamiltonian=self.hamiltonian,
            local_rates=self.local_rates,
            source_time_unit=self.source_time_unit,
            max_connected_component_dimension=self.max_connected_component_dimension,
            field_precision_bits=self.field_precision_bits,
            precision_authority_receipt_sha256=self.precision_authority.authority_receipt_sha256,
            mode_bank_receipt_sha256=self.mode_bank.receipt_sha256,
            l5_governance_receipt_sha256=self.l5_governance.authority_receipt_sha256,
        )
        if self.authority_receipt_payload != expected:
            raise ReceiptError("basin profile differs from canonical bytes")
        if receipt_registry.resolve(self.authority_receipt_sha256, "basin profile") != expected:
            raise ReceiptError("basin profile differs from mounted receipt")


@dataclass(frozen=True, slots=True)
class StoryReplayExpressionFacts:
    expression: ClosedExperienceFieldExpression
    evaluation: FieldExpressionEvaluation
    recognition: ExpressionModeBoundaryResult
    receipt_registry: ReceiptRegistry


@dataclass(frozen=True, slots=True)
class PreparedStoryReplayContext:
    request: GlobalUFReplayRequest
    streams: tuple[EvidenceStream, ...]
    kernel_inputs: tuple[KernelNativeInputStream, ...]
    preparation: ClosedExperienceEvidencePreparation
    expression_facts: StoryReplayExpressionFacts
    sealed: SealedClosedExperience


@dataclass(frozen=True, slots=True)
class StoryGlobalUFPreparation:
    story_replay_results: tuple[StoryNativeReplayResult, ...]
    language_replay: TypedLanguageNativeReplayResult
    sensor_l6_production: PhysicalL6TangentProduction
    fixed42_stack: Fixed42ConstraintStack
    fixed42_rank: ExactRankReceipt
    lane_completeness_receipts: tuple[LaneCompletenessReceipt, ...]
    observation_window: MountedRawObservationWindow
    sensor_resolution_profile: MountedSensorResolutionProfile
    contexts: tuple[PreparedStoryReplayContext, ...]
    base_closed_experience_receipt_sha256: str
    receipt_registry: ReceiptRegistry


@dataclass(frozen=True, slots=True)
class MountedStoryReplayAuthorities:
    request_receipt_sha256: str
    origin: ExperienceOriginAuthority
    safe_mode_scope: MountedSafeModeScope
    safe_mode_facts: tuple[IntegrityFact, ...]
    safe_mode_evaluation: SafeModeEvaluation
    memory_energy: MemoryEnergyAuthority | None
    event_support_evaluation: EventSupportEvaluation
    l6_predicates: L6PredicateInputs
    l6_evaluation: L6Evaluation
    l6_scope: L6ScopeAuthority
    pending_conjunction: PendingGlobalUFConjunction


@dataclass(frozen=True, slots=True)
class StoryGlobalUFExecutionResult:
    preparation: StoryGlobalUFPreparation
    validation: GlobalUFValidationResult
    receipt_registry: ReceiptRegistry


def _expression_payloads(value: ExpressionModeBoundaryResult) -> tuple[bytes, ...]:
    payloads = [
        value.pre_growth_bank.receipt_payload,
        value.post_growth_bank.receipt_payload,
        value.receipt_payload,
    ]
    for mode in value.post_growth_bank.modes:
        payloads.extend((mode.growth_proof_receipt_payload, mode.receipt_payload))
    return tuple(payloads)


def _build_expression_facts(
    *,
    context_id: str,
    preparation: ClosedExperienceEvidencePreparation,
    topology: MountedFieldTopology,
    profile: MountedStoryGlobalUFBasinProfile,
    receipt_registry: ReceiptRegistry,
) -> StoryReplayExpressionFacts:
    registry = _extend_records(receipt_registry, preparation.receipt_registry.records)
    steps = []
    payloads = []
    components = canonical_component_partition(topology.dimension, profile.hamiltonian)
    for index, event in enumerate(preparation.events):
        source = source_coefficients_for_injection(
            event.injection, event.source_time_end - event.source_time_start
        )
        authority_id = f"{context_id}:field:{index:08d}"
        payload = evolution_authority_receipt_payload(
            authority_id=authority_id,
            physical_profile_receipt_sha256=profile.physical_profile_receipt_sha256,
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            map_injection_receipt_sha256=event.injection.receipt_sha256,
            source_time_start=event.source_time_start,
            source_time_end=event.source_time_end,
            source_time_unit=profile.source_time_unit,
            hbar=profile.hbar,
            hamiltonian=profile.hamiltonian,
            local_rates=profile.local_rates,
            source=source,
            component_partition=components,
            max_connected_component_dimension=profile.max_connected_component_dimension,
            precision_bits=profile.field_precision_bits,
        )
        authority = FieldEvolutionAuthority(
            authority_id,
            profile.physical_profile_receipt_sha256,
            topology.authority_receipt_sha256,
            event.injection.receipt_sha256,
            event.source_time_start,
            event.source_time_end,
            profile.source_time_unit,
            profile.hbar,
            profile.hamiltonian,
            profile.local_rates,
            source,
            profile.max_connected_component_dimension,
            profile.field_precision_bits,
            receipt_sha256(payload),
        )
        steps.append(FieldExpressionStep(event.injection, authority, ()))
        payloads.append(payload)
    registry = _extend_payloads(registry, payloads)
    expression = create_closed_experience_expression(
        topology=topology,
        initial_state=profile.initial_field_state,
        steps=steps,
        precision_authority=profile.precision_authority,
        receipt_registry=registry,
    )
    registry = _extend_payloads(registry, (expression.receipt_payload,))
    evaluation = evaluate_closed_experience_expression(expression, receipt_registry=registry)
    if evaluation.status is not ExpressionEvaluationStatus.CERTIFIED:
        raise ReceiptError("story expression did not certify")
    registry = _extend_payloads(registry, (evaluation.receipt_payload,))
    recognition = evaluate_expression_mode_boundary(
        topology=topology,
        bank=profile.mode_bank,
        input_expression=expression,
        receipt_registry=registry,
    )
    if recognition.status is ExpressionRecognitionStatus.UNKNOWN:
        raise ReceiptError("story expression recognition is UNKNOWN")
    registry = _extend_payloads(registry, _expression_payloads(recognition))
    return StoryReplayExpressionFacts(expression, evaluation, recognition, registry)


def _sign(value: Fraction) -> SignZeroClass:
    return (
        SignZeroClass.NEGATIVE
        if value < 0
        else SignZeroClass.POSITIVE
        if value > 0
        else SignZeroClass.EXACT_ZERO
    )


def _fraction(value: object, name: str) -> Fraction:
    if isinstance(value, bool):
        raise ReceiptError(f"{name} is not an exact numeric coordinate")
    try:
        return Fraction(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise ReceiptError(f"{name} is not an exact rational") from exc


def _classes(values: Mapping[str, object]) -> tuple[NamedSignZeroClass, ...]:
    return tuple(
        NamedSignZeroClass(name, _sign(_fraction(value, name)))
        for name, value in sorted(values.items())
    )


def _lossless_id(prefix: str, value: object) -> str:
    return f"{prefix}-{_canonical_bytes(value).hex()}"


def _port_kernel_basin(
    *, lane_id: str, port_id: str, raw_record: ReceiptRecord
) -> tuple[PortKernelBasinSignature, tuple[bytes, ...]]:
    raw = json.loads(raw_record.payload)
    l0, l1, l2, l3, l4 = (
        raw["L0_SEV"],
        raw["L1_GateL1State"],
        raw["L2_GateInterpretation"],
        raw["L3_ResonanceResult"],
        raw["L4_DSF"],
    )
    tuples = []
    tuple_payloads = []
    for index, item in enumerate(l4):
        values = {name: _fraction(item[name], name) for name in _DSF_FIELDS}
        payload = exact_dsf_field_tuple_receipt_payload(
            lane_id=lane_id,
            port_id=port_id,
            tuple_index=index,
            source_l0_l4_trace_receipt_sha256=raw_record.digest,
            **values,
        )
        tuples.append(
            ExactDSFFieldTupleReceipt(
                lane_id,
                port_id,
                index,
                *(values[name] for name in _DSF_FIELDS),
                raw_record.digest,
                receipt_sha256(payload),
            )
        )
        tuple_payloads.append(payload)
    layers = (
        LayerBranchGateSignature(
            0,
            _lossless_id("L0", {"sample_count": len(l0)}),
            tuple(f"sample-{index:08d}" for index in range(len(l0))),
            _classes({f"{i:08d}:{k}": v for i, row in enumerate(l0) for k, v in row.items()}),
        ),
        LayerBranchGateSignature(
            1,
            _lossless_id("L1", [{k: row[k] for k in ("C_k", "N_gate", "start_idx", "end_idx", "projections")} for row in l1]),
            tuple(_lossless_id(f"gate-{i:08d}", {"start_idx": row["start_idx"], "end_idx": row["end_idx"]}) for i, row in enumerate(l1)),
            _classes({
                **{f"{i:08d}:delta_g": row["delta_g"] for i, row in enumerate(l1)},
                **{f"{i:08d}:TVR:{axis}": value for i, row in enumerate(l1) for axis, value in zip("TVR", row["TVR"], strict=True)},
            }),
        ),
        LayerBranchGateSignature(
            2,
            _lossless_id("L2", [{k: row[k] for k in ("IAS_k", "regime", "start_idx", "end_idx")} for row in l2]),
            tuple(_lossless_id(f"gate-{i:08d}", row["regime"]) for i, row in enumerate(l2)),
            _classes({
                **{f"{i:08d}:{name}": row[name] for i, row in enumerate(l2) for name in ("S_k", "U_k", "w_k")},
                **{f"{i:08d}:CV:{axis}": value for i, row in enumerate(l2) for axis, value in zip("TVR", row["CV_k"], strict=True)},
            }),
        ),
        LayerBranchGateSignature(
            3,
            _lossless_id("L3", [{k: row[k] for k in ("Hyst_k", "g_k", "start_idx", "end_idx")} for row in l3]),
            tuple(_lossless_id(f"gate-{i:08d}", {"Hyst_k": row["Hyst_k"], "g_k": row["g_k"]}) for i, row in enumerate(l3)),
            _classes({f"{i:08d}:{name}": row[name] for i, row in enumerate(l3) for name in ("R_k", "URF_k")}),
        ),
        LayerBranchGateSignature(
            4,
            _lossless_id("L4", {"gate_count": len(l4)}),
            tuple(f"gate-{index:08d}" for index in range(len(l4))),
            _classes({f"{i:08d}:{name}": getattr(item, name) for i, item in enumerate(tuples) for name in _DSF_FIELDS}),
        ),
    )
    payload = port_kernel_basin_receipt_payload(
        lane_id=lane_id,
        port_id=port_id,
        layers=layers,
        exact_dsf_field_tuples=tuple(tuples),
    )
    return (
        PortKernelBasinSignature(
            lane_id, port_id, layers, tuple(tuples), receipt_sha256(payload)
        ),
        (*tuple_payloads, payload),
    )


def _ball_bounds(value: CertifiedBall) -> tuple[Fraction, Fraction]:
    return (
        Fraction(value.lower_mantissa) * Fraction(2) ** value.lower_exponent,
        Fraction(value.upper_mantissa) * Fraction(2) ** value.upper_exponent,
    )


def _operator_basins(
    preparation: ClosedExperienceEvidencePreparation,
) -> tuple[CertifiedOperatorBasinSignature, CertifiedOperatorBasinSignature, bytes, bytes]:
    support = preparation.support_floor
    if support.value < 0:
        raise ReceiptError("S_UF left its nonnegative physical domain")
    s_class = (
        CertifiedNonnegativeClass.EXACT_ZERO
        if support.value == 0
        else CertifiedNonnegativeClass.CERTIFIED_POSITIVE
    )
    s_payload = _canonical_bytes(
        {
            "preparation_receipt_sha256": preparation.receipt_sha256,
            "schema": "glew.story_global_uf.S_UF_basin.v2",
            "value": _fraction_text(support.value),
            "value_class": s_class.value,
        }
    )
    lower, upper = _ball_bounds(preparation.resonance_confirmation.value)
    if lower == upper == 0:
        r_class = CertifiedNonnegativeClass.EXACT_ZERO
    elif lower > 0:
        r_class = CertifiedNonnegativeClass.CERTIFIED_POSITIVE
    else:
        raise ReceiptError("R_UF enclosure does not resolve zero versus positive")
    r_payload = _canonical_bytes(
        {
            "certified_lower": _fraction_text(lower),
            "certified_upper": _fraction_text(upper),
            "preparation_receipt_sha256": preparation.receipt_sha256,
            "schema": "glew.story_global_uf.R_UF_basin.v2",
            "value_class": r_class.value,
        }
    )
    return (
        CertifiedOperatorBasinSignature(OperatorAvailability.AVAILABLE, s_class, receipt_sha256(s_payload)),
        CertifiedOperatorBasinSignature(OperatorAvailability.AVAILABLE, r_class, receipt_sha256(r_payload)),
        s_payload,
        r_payload,
    )


def _l5_dispositions(
    sealed: SealedClosedExperience,
) -> tuple[tuple[PortL5BasinDisposition, ...], tuple[bytes, ...]]:
    by_key: dict[tuple[str, str], list] = {}
    for item in sealed.l5_applicability:
        by_key.setdefault((item.lane_id, item.port_id), []).append(item)
    values, payloads = [], []
    for key in tuple(dict.fromkeys((item.lane_id, item.port_id) for item in sealed.l5_applicability)):
        rules = by_key[key]
        if any(item.state is ApplicabilityState.UNKNOWN for item in rules):
            raise ReceiptError("L5 applicability is UNKNOWN")
        if all(item.state is ApplicabilityState.NOT_APPLICABLE for item in rules):
            state, disposition = L5DispositionState.NOT_APPLICABLE, None
        else:
            state = L5DispositionState.APPLIED
            disposition = ":".join(f"{item.fact.value}-{item.state.value}" for item in rules)
        payload = _canonical_bytes(
            {
                "closed_experience_receipt_sha256": sealed.closed_experience.authority_receipt_sha256,
                "disposition_id": disposition,
                "l5_applicability_receipt_sha256s": [item.authority_receipt_sha256 for item in rules],
                "lane_id": key[0],
                "port_id": key[1],
                "schema": "glew.story_global_uf.port_L5_basin.v2",
                "state": state.value,
            }
        )
        values.append(PortL5BasinDisposition(key[0], key[1], state, disposition, receipt_sha256(payload)))
        payloads.append(payload)
    return tuple(values), tuple(payloads)


def _independent_rows(rows: tuple[ConstraintRow, ...]) -> tuple[ConstraintRow, ...]:
    chosen: list[ConstraintRow] = []
    rank = 0
    for row in sorted(rows, key=lambda value: value.provenance.identity):
        candidate = Fixed42ConstraintStack((*chosen, row))
        candidate_rank = exact_rank_receipt(candidate).rank
        if candidate_rank > rank:
            chosen.append(row)
            rank = candidate_rank
    return tuple(chosen)


def _l6_basin(stack: Fixed42ConstraintStack, evaluation: L6Evaluation) -> tuple[L6BasinSignature, bytes]:
    if evaluation.status is L6EvaluationStatus.UNKNOWN_NO_LOCK:
        raise ReceiptError("L6 evaluation is UNKNOWN")
    basis_rows = _independent_rows(stack.rows)
    signatures = tuple(
        sorted(
            (
                L6BasisRowSignature(
                    row.provenance.row_id,
                    row.provenance.operator_id,
                    row.coefficients,
                    row.provenance.receipt_sha256,
                )
                for row in basis_rows
            ),
            key=lambda value: value.canonical_key,
        )
    )
    pivots = exact_rank_receipt(Fixed42ConstraintStack(basis_rows)).pivot_columns
    basin_class = L6BasinClass.LOCK if evaluation.status is L6EvaluationStatus.LOCK else L6BasinClass.NO_LOCK
    payload = _canonical_bytes(
        {
            "basin_class": basin_class.value,
            "complete_stack_row_receipt_sha256s": [row.provenance.receipt_sha256 for row in stack.rows],
            "n_effective": 42 - len(signatures),
            "pivot_columns": list(pivots),
            "rank": len(signatures),
            "row_basis_receipt_sha256s": [row.authority_receipt_sha256 for row in signatures],
            "schema": "glew.story_global_uf.fixed42_basin.v2",
        }
    )
    return L6BasinSignature(signatures, len(signatures), 42 - len(signatures), pivots, basin_class, receipt_sha256(payload)), payload


def _stable_mode(value: ExpressionModeBoundaryResult) -> tuple[StableModeBasinSignature, bytes]:
    if value.status is ExpressionRecognitionStatus.RECOGNIZED:
        if value.winner_mode_index is None:
            raise ReceiptError("recognized expression lacks a mode")
        mode = value.pre_growth_bank.modes[value.winner_mode_index]
        state, index, digest = StableModeState.SELECTED, mode.mode_index, mode.receipt_sha256
    elif value.status in (
        ExpressionRecognitionStatus.BOOTSTRAP_SILENCE,
        ExpressionRecognitionStatus.NOVEL_SILENCE,
        ExpressionRecognitionStatus.AMBIGUOUS_SILENCE,
    ):
        state, index, digest = StableModeState.NO_STABLE_MODE, None, None
    else:
        raise ReceiptError("expression-mode boundary is unresolved")
    payload = _canonical_bytes(
        {
            "recognition_receipt_sha256": value.receipt_sha256,
            "schema": "glew.story_global_uf.stable_mode_basin.v2",
            "selected_mode_index": index,
            "selected_mode_receipt_sha256": digest,
            "state": state.value,
        }
    )
    return StableModeBasinSignature(state, index, digest, receipt_sha256(payload)), payload


def _complete_l6(
    sensor: PhysicalL6TangentProduction,
    language: TypedLanguageNativeReplayResult,
) -> tuple[Fixed42ConstraintStack, ExactRankReceipt, tuple[LaneCompletenessReceipt, ...], ReceiptRegistry]:
    if sensor.status is not PhysicalTangentProductionStatus.KNOWN or sensor.candidate_constraints is None or sensor.candidate_constraints.stack is None:
        raise ReceiptError(f"sensor Fixed42 production unresolved: {sensor.reason}")
    registry = _extend_records(sensor.receipt_registry, language.receipt_registry.records)
    cone = language.contingent_cone
    rows = tuple(sorted((*sensor.candidate_constraints.stack.rows, *cone.fixed42_stack.rows), key=lambda value: value.provenance.identity))
    stack = Fixed42ConstraintStack(rows)
    completeness_by_lane = {item.lane: item for item in sensor.lane_completeness_receipts}
    language_payload = registry.resolve(cone.row_completeness_receipt_sha256, "language row completeness")
    completeness_by_lane[L6Lane.LANGUAGE] = LaneCompletenessReceipt(
        L6Lane.LANGUAGE,
        cone.row_completeness_receipt_sha256,
        language_payload,
    )
    completeness = tuple(completeness_by_lane[lane] for lane in L6Lane)
    if tuple(item.lane for item in completeness) != tuple(L6Lane):
        raise ReceiptError("Fixed42 completeness does not cover all six lanes")
    return stack, exact_rank_receipt(stack), completeness, registry


def _full_sensor_execution(
    *,
    execution,
    typed_input: TypedLanguageFrozenKernelInput,
    topology: MountedFieldTopology,
    grid: CausalGrid,
    support_domain: MountedSupportDomain,
    resonance_graph: MountedResonanceGraph,
    resonance_operator: ResonanceOperatorAuthority,
    source_time_start: Fraction,
    receipt_registry: ReceiptRegistry,
):
    prepared = prepare_closed_experience_evidence(
        streams=(typed_input.stream, *execution.streams),
        kernel_inputs=(typed_input.kernel_input, *execution.kernel_inputs),
        source_time_start=source_time_start,
        grid=grid,
        support_domain=support_domain,
        resonance_graph=resonance_graph,
        resonance_operator=resonance_operator,
        topology=topology,
        receipt_registry=receipt_registry,
    )
    if not isinstance(prepared, ClosedExperienceEvidencePreparation) or prepared.status is not ProviderStatus.READY:
        raise ReceiptError("six-lane sensor replay preparation is unresolved")
    return (typed_input.stream, *execution.streams), (typed_input.kernel_input, *execution.kernel_inputs), prepared


def prepare_story_global_uf(
    *,
    story_profile: MountedStoryNativeReplayProfile,
    basin_profile: MountedStoryGlobalUFBasinProfile,
    boundary: MountedAuthenticatedClosedStoryBoundary,
    pre_window_state: MountedPreWindowState,
    story_runtime: StoryChemistryRuntime,
    sensor_states: tuple[MountedStorySensorState, ...],
    typed_input: TypedLanguageFrozenKernelInput,
    topology: MountedFieldTopology,
    grid: CausalGrid,
    support_domain: MountedSupportDomain,
    resonance_graph: MountedResonanceGraph,
    resonance_operator: ResonanceOperatorAuthority,
    receipt_registry: ReceiptRegistry,
) -> StoryGlobalUFPreparation:
    """Execute, dimensionalize, and seal; create no governance authority."""

    typed_input.verify()
    registry = _extend_records(receipt_registry, typed_input.receipt_registry.records)
    basin_profile.verify(
        story_profile=story_profile,
        pre_window_state=pre_window_state,
        topology=topology,
        receipt_registry=registry,
    )
    story_results = tuple(
        execute_story_native_replay(
            target_lane=port.lane,
            target_field_port_id=port.field_port_id,
            profile=story_profile,
            boundary=boundary,
            pre_window_state=pre_window_state,
            story_runtime=story_runtime,
            sensor_states=sensor_states,
            receipt_registry=registry,
        )
        for port in story_profile.ports
    )
    if any(item.status is not StoryNativeReplayStatus.READY for item in story_results):
        raise ReceiptError("one native story replay is unresolved")
    for item in story_results:
        registry = _extend_records(registry, item.receipt_registry.records)
    nonlanguage_base = story_results[0].executions[0]
    language = execute_typed_language_native_replay(
        provider_id="story-global-uf-typed-language",
        typed_input=typed_input,
        pre_window_state=pre_window_state,
        nonlanguage_streams=nonlanguage_base.streams,
        nonlanguage_kernel_inputs=nonlanguage_base.kernel_inputs,
        source_time_start=basin_profile.initial_field_state.source_time,
        topology=topology,
        grid=grid,
        support_domain=support_domain,
        resonance_graph=resonance_graph,
        resonance_operator=resonance_operator,
        receipt_registry=registry,
    )
    registry = _extend_records(registry, language.receipt_registry.records)
    bundles = tuple(item.bundle for item in story_results if item.bundle is not None)
    sensor_production = produce_physical_l6_tangents(
        bundles=bundles,
        pre_window_state=pre_window_state,
        receipt_registry=registry,
    )
    stack, rank, completeness, registry = _complete_l6(sensor_production, language)

    base_language = language.executions[0]
    base_facts = _build_expression_facts(
        context_id=f"{boundary.boundary_id}:global-uf:base",
        preparation=base_language.preparation,
        topology=topology,
        profile=basin_profile,
        receipt_registry=registry,
    )
    registry = _extend_records(registry, base_facts.receipt_registry.records)
    base_sealed = seal_closed_experience(
        experience_id=f"{boundary.boundary_id}:global-uf:base",
        structural_time_unit=basin_profile.source_time_unit,
        preparation=base_language.preparation,
        topology=topology,
        l5_governance=basin_profile.l5_governance,
        expression=base_facts.expression,
        recognition=base_facts.recognition,
        receipt_registry=registry,
    )
    registry = _extend_records(registry, base_sealed.receipt_registry.records)
    base_digest = base_sealed.closed_experience.authority_receipt_sha256
    sensor_observations = tuple(
        sorted(
            (
                SensorIntegerObservation(
                    ObservationCoordinate(port.lane.value, port.field_port_id, 0, port.scene_coordinate_id),
                    port.base_raw_code,
                )
                for port in story_profile.ports
            ),
            key=lambda value: value.coordinate,
        )
    )
    typed_observation = TypedUnicodeObservation(
        ObservationCoordinate(
            L6Lane.LANGUAGE.value,
            typed_input.stream.port_id,
            0,
            f"{typed_input.event.event_id}-unicode",
        ),
        typed_input.event.normalized_text,
    )
    window_payload = raw_observation_window_receipt_payload(
        window_id=f"{boundary.boundary_id}:global-uf-window",
        sensor_observations=sensor_observations,
        typed_unicode_observations=(typed_observation,),
    )
    window = MountedRawObservationWindow(
        f"{boundary.boundary_id}:global-uf-window",
        sensor_observations,
        (typed_observation,),
        receipt_sha256(window_payload),
    )
    port_by_coordinate = {item.scene_coordinate_id: item for item in story_profile.ports}
    resolutions = tuple(
        SensorCodeResolution(
            item.coordinate,
            port_by_coordinate[item.coordinate.coordinate_id].minimum_raw_code,
            port_by_coordinate[item.coordinate.coordinate_id].maximum_raw_code,
            port_by_coordinate[item.coordinate.coordinate_id].physical_quantum,
            port_by_coordinate[item.coordinate.coordinate_id].authority_receipt_sha256,
        )
        for item in sensor_observations
    )
    resolution_payload = sensor_resolution_profile_receipt_payload(
        profile_id=f"{boundary.boundary_id}:sensor-resolution",
        observation_window_receipt_sha256=receipt_sha256(window_payload),
        resolutions=resolutions,
    )
    resolution = MountedSensorResolutionProfile(
        f"{boundary.boundary_id}:sensor-resolution",
        receipt_sha256(window_payload),
        resolutions,
        receipt_sha256(resolution_payload),
    )
    registry = _extend_payloads(registry, (window_payload, resolution_payload))
    requests = enumerate_global_uf_replay_requests(
        topology=topology,
        closed_experience_receipt_sha256=base_digest,
        observation_window=window,
        sensor_resolution_profile=resolution,
        pre_window_state=pre_window_state,
        receipt_registry=registry,
    )
    registry = _extend_payloads(registry, (item.receipt_payload for item in requests))
    contexts = []
    for request in requests:
        if request.kind is ReplayKind.BASE:
            streams = (base_language.language_stream, *nonlanguage_base.streams)
            inputs = (base_language.language_kernel_input, *nonlanguage_base.kernel_inputs)
            preparation, facts, sealed = base_language.preparation, base_facts, base_sealed
        else:
            if request.target_coordinate is None:
                raise ReceiptError("adjacent request lacks a target")
            target = next(
                item for item in story_results
                if item.bundle is not None
                and item.bundle.profile.sensor_coordinates[0].coordinate_id
                == request.target_coordinate.coordinate_id
            )
            requested = {item.coordinate.coordinate_id: item.raw_code for item in request.sensor_codes}
            coordinate = target.bundle.profile.sensor_coordinates[0]
            execution = next(item for item in target.executions if item.case.sensor_codes[0].raw_code == requested[coordinate.coordinate_id])
            streams, inputs, preparation = _full_sensor_execution(
                execution=execution,
                typed_input=typed_input,
                topology=topology,
                grid=grid,
                support_domain=support_domain,
                resonance_graph=resonance_graph,
                resonance_operator=resonance_operator,
                source_time_start=basin_profile.initial_field_state.source_time,
                receipt_registry=registry,
            )
            registry = _extend_records(registry, preparation.receipt_registry.records)
            facts = _build_expression_facts(
                context_id=request.request_id,
                preparation=preparation,
                topology=topology,
                profile=basin_profile,
                receipt_registry=registry,
            )
            registry = _extend_records(registry, facts.receipt_registry.records)
            sealed = seal_closed_experience(
                experience_id=f"{request.request_id}:replay",
                structural_time_unit=basin_profile.source_time_unit,
                preparation=preparation,
                topology=topology,
                l5_governance=basin_profile.l5_governance,
                expression=facts.expression,
                recognition=facts.recognition,
                receipt_registry=registry,
            )
            registry = _extend_records(registry, sealed.receipt_registry.records)
        contexts.append(PreparedStoryReplayContext(request, streams, inputs, preparation, facts, sealed))
    seals = tuple(item.sealed.closed_experience.authority_receipt_sha256 for item in contexts)
    if len(set(seals)) != len(seals):
        raise ReceiptError("a counterfactual reused another replay seal")
    return StoryGlobalUFPreparation(
        story_results,
        language,
        sensor_production,
        stack,
        rank,
        completeness,
        window,
        resolution,
        tuple(contexts),
        base_digest,
        registry,
    )


def _expected_l6_predicates(
    context: PreparedStoryReplayContext,
    preparation: StoryGlobalUFPreparation,
    disruption_clear: bool | None,
) -> L6PredicateInputs:
    completeness = {item.lane: item.receipt_sha256 for item in preparation.lane_completeness_receipts}
    evidence = {item.lane_id: item for item in context.preparation.evidence}
    return L6PredicateInputs(
        tuple(
            ActiveLaneState(
                lane,
                evidence[lane.value].coordinates.U_star_k,
                True,
                completeness[lane],
            )
            for lane in L6Lane
        ),
        disruption_clear,
    )


def _verify_authorities(
    *,
    context: PreparedStoryReplayContext,
    mounted: MountedStoryReplayAuthorities,
    preparation: StoryGlobalUFPreparation,
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
) -> None:
    if mounted.request_receipt_sha256 != context.request.receipt_sha256:
        raise ReceiptError("replay authorities belong to another request")
    seal = context.sealed.closed_experience
    mounted.origin.verify(receipt_registry)
    if (
        mounted.origin.topology_authority_receipt_sha256 != topology.authority_receipt_sha256
        or mounted.origin.closed_experience_receipt_sha256 != seal.authority_receipt_sha256
    ):
        raise ReceiptError("replay origin belongs to another exact seal")
    recomputed_safe = evaluate_safe_mode(
        authority_id=mounted.safe_mode_evaluation.authority.authority_id,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=seal.authority_receipt_sha256,
        scope=mounted.safe_mode_scope,
        facts=mounted.safe_mode_facts,
        receipt_registry=receipt_registry,
    )
    if recomputed_safe != mounted.safe_mode_evaluation:
        raise ReceiptError("mounted SafeMode differs from exact replay evaluation")
    recomputed_event = evaluate_event_support(
        authority_id=mounted.event_support_evaluation.authority.authority_id,
        origin=mounted.origin,
        topology=topology,
        closed_experience_receipt_sha256=seal.authority_receipt_sha256,
        expression=context.expression_facts.expression,
        memory_energy=mounted.memory_energy,
        receipt_registry=receipt_registry,
    )
    if recomputed_event != mounted.event_support_evaluation or recomputed_event.status is not EventSupportEvaluationStatus.RESOLVED:
        raise ReceiptError("mounted R_event differs from exact replay evaluation")
    expected_predicates = _expected_l6_predicates(context, preparation, mounted.l6_predicates.disruption_clear)
    if mounted.l6_predicates != expected_predicates:
        raise ReceiptError("mounted L6 predicates differ from exact six-lane field")
    recomputed_l6 = evaluate_l6(preparation.fixed42_stack, mounted.l6_predicates, receipt_registry)
    if recomputed_l6 != mounted.l6_evaluation:
        raise ReceiptError("mounted L6 differs from exact complete row set")
    mounted.l6_scope.verify(
        topology_receipt=topology.authority_receipt_sha256,
        experience_receipt=seal.authority_receipt_sha256,
        evaluation=mounted.l6_evaluation,
        receipt_registry=receipt_registry,
    )
    recomputed_pending = evaluate_pending_global_uf_conjunction(
        topology=topology,
        recognition=context.expression_facts.recognition,
        l6_evaluation=mounted.l6_evaluation,
        l6_scope=mounted.l6_scope,
        closed_experience=seal,
        safe_mode=mounted.safe_mode_evaluation.authority,
        event_support=mounted.event_support_evaluation.authority,
        evidence=context.sealed.evidence,
        l5_applicability=context.sealed.l5_applicability,
        receipt_registry=receipt_registry,
    )
    if recomputed_pending != mounted.pending_conjunction:
        raise ReceiptError("mounted pending conjunction differs from real commit boundary")


def _make_basin(
    *,
    context: PreparedStoryReplayContext,
    mounted: MountedStoryReplayAuthorities,
    preparation: StoryGlobalUFPreparation,
    topology: MountedFieldTopology,
    receipt_registry: ReceiptRegistry,
) -> tuple[StructuralBasinSignature, ReceiptRegistry]:
    registry = receipt_registry
    kernels, payloads = [], []
    evidence = {item.key: item for item in context.preparation.evidence}
    for fiber in topology.ordered_port_fibers:
        basin, generated = _port_kernel_basin(
            lane_id=fiber.lane_id,
            port_id=fiber.port_id,
            raw_record=evidence[fiber.key].raw_record,
        )
        kernels.append(basin)
        payloads.extend(generated)
    s_uf, r_uf, s_payload, r_payload = _operator_basins(context.preparation)
    l5, l5_payloads = _l5_dispositions(context.sealed)
    l6, l6_payload = _l6_basin(preparation.fixed42_stack, mounted.l6_evaluation)
    stable, stable_payload = _stable_mode(context.expression_facts.recognition)
    registry = _extend_payloads(
        registry,
        (*payloads, s_payload, r_payload, *l5_payloads, l6_payload, stable_payload),
    )
    return StructuralBasinSignature(
        tuple(kernels),
        s_uf,
        r_uf,
        l5,
        l6,
        stable,
        CommitBasinSignature(mounted.pending_conjunction),
    ), registry


@dataclass(slots=True)
class _ReplayProvider:
    responses: Mapping[str, GlobalUFReplayResponse]

    def replay_from_immutable_pre_window(self, request: GlobalUFReplayRequest) -> GlobalUFReplayResponse | None:
        return self.responses.get(request.receipt_sha256)


def _outcome(
    *,
    context: PreparedStoryReplayContext,
    basin: StructuralBasinSignature,
    preparation: StoryGlobalUFPreparation,
    topology: MountedFieldTopology,
    pre_window_state: MountedPreWindowState,
    receipt_registry: ReceiptRegistry,
) -> tuple[GlobalUFReplayResponse, ReceiptRegistry]:
    l5_by_key = {item.key: item.authority_receipt_sha256 for item in basin.l5_dispositions}
    input_by_key = {item.key: item for item in context.kernel_inputs}
    evidence_by_key = {item.key: item for item in context.preparation.evidence}
    ports, payloads = [], []
    for fiber in topology.ordered_port_fibers:
        payload = port_replay_receipt_payload(
            lane_id=fiber.lane_id,
            port_id=fiber.port_id,
            request_receipt_sha256=context.request.receipt_sha256,
            source_observation_receipt_sha256=input_by_key[fiber.key].source_stream_receipt_sha256,
            l0_l4_trace_receipt_sha256=evidence_by_key[fiber.key].raw_record.digest,
            l5_governance_receipt_sha256=l5_by_key[fiber.key],
        )
        ports.append(
            PortReplayReceipt(
                fiber.lane_id,
                fiber.port_id,
                context.request.receipt_sha256,
                input_by_key[fiber.key].source_stream_receipt_sha256,
                evidence_by_key[fiber.key].raw_record.digest,
                l5_by_key[fiber.key],
                receipt_sha256(payload),
            )
        )
        payloads.append(payload)
    registry = _extend_payloads(receipt_registry, payloads)
    replay_digest = context.sealed.closed_experience.authority_receipt_sha256
    outcome_payload = global_uf_replay_outcome_receipt_payload(
        outcome_id=f"{context.request.request_id}:resolved-story-basin",
        status=ReplayOutcomeStatus.RESOLVED,
        reason=None,
        request_receipt_sha256=context.request.receipt_sha256,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        base_closed_experience_receipt_sha256=preparation.base_closed_experience_receipt_sha256,
        replay_closed_experience_receipt_sha256=replay_digest,
        observation_window_receipt_sha256=preparation.observation_window.authority_receipt_sha256,
        sensor_resolution_profile_receipt_sha256=preparation.sensor_resolution_profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        port_replay_receipts=tuple(ports),
        basin_signature=basin,
    )
    outcome = GlobalUFReplayOutcome(
        f"{context.request.request_id}:resolved-story-basin",
        ReplayOutcomeStatus.RESOLVED,
        None,
        context.request.receipt_sha256,
        topology.authority_receipt_sha256,
        preparation.base_closed_experience_receipt_sha256,
        replay_digest,
        preparation.observation_window.authority_receipt_sha256,
        preparation.sensor_resolution_profile.authority_receipt_sha256,
        pre_window_state.authority_receipt_sha256,
        tuple(ports),
        basin,
        receipt_sha256(outcome_payload),
    )
    registry = _extend_payloads(registry, (outcome_payload,))
    outcome.verify(request=context.request, topology=topology, receipt_registry=registry)
    return GlobalUFReplayResponse(outcome, registry.records), registry


def evaluate_story_global_uf(
    *,
    authority_id: str,
    preparation: StoryGlobalUFPreparation,
    mounted_authorities: tuple[MountedStoryReplayAuthorities, ...],
    topology: MountedFieldTopology,
    pre_window_state: MountedPreWindowState,
    receipt_registry: ReceiptRegistry,
) -> StoryGlobalUFExecutionResult:
    """Evaluate only caller-mounted, replay-specific authorities."""

    require_identifier(authority_id, "story Global-UF authority id")
    registry = _extend_records(preparation.receipt_registry, receipt_registry.records)
    by_request = {item.request_receipt_sha256: item for item in mounted_authorities}
    if len(by_request) != len(mounted_authorities) or set(by_request) != {item.request.receipt_sha256 for item in preparation.contexts}:
        raise ReceiptError("mounted authorities do not exactly cover every replay")
    authority_identity_sets = []
    responses = {}
    base_origin_kind = None
    for context in preparation.contexts:
        mounted = by_request[context.request.receipt_sha256]
        _verify_authorities(
            context=context,
            mounted=mounted,
            preparation=preparation,
            topology=topology,
            receipt_registry=registry,
        )
        if base_origin_kind is None:
            base_origin_kind = mounted.origin.kind
            if base_origin_kind is ExperienceOriginKind.EXPLICIT_STORY_EMULATOR:
                if mounted.event_support_evaluation.exact_r_event is None or mounted.event_support_evaluation.exact_r_event <= 0:
                    raise ReceiptError("fresh story base lacks positive exact R_event")
            elif base_origin_kind is ExperienceOriginKind.SELF_GENERATED_RECALL:
                if mounted.event_support_evaluation.exact_r_event != 0:
                    raise ReceiptError("self recall base lacks exact-zero fresh R_event")
            else:
                raise ReceiptError("story Global-UF origin is not story or self recall")
        elif mounted.origin.kind is not base_origin_kind:
            raise ReceiptError("counterfactual changed experience origin kind")
        if base_origin_kind is ExperienceOriginKind.SELF_GENERATED_RECALL and mounted.event_support_evaluation.exact_r_event != 0:
            raise ReceiptError("self-recall counterfactual gained fresh event energy")
        identities = (
            mounted.origin.authority_receipt_sha256,
            mounted.safe_mode_evaluation.authority.authority_receipt_sha256,
            mounted.event_support_evaluation.authority.authority_receipt_sha256,
            mounted.l6_scope.authority_receipt_sha256,
            mounted.pending_conjunction.receipt_sha256,
        )
        authority_identity_sets.append(identities)
        basin, registry = _make_basin(
            context=context,
            mounted=mounted,
            preparation=preparation,
            topology=topology,
            receipt_registry=registry,
        )
        response, registry = _outcome(
            context=context,
            basin=basin,
            preparation=preparation,
            topology=topology,
            pre_window_state=pre_window_state,
            receipt_registry=registry,
        )
        responses[context.request.receipt_sha256] = response
    for index in range(len(authority_identity_sets[0])):
        values = tuple(item[index] for item in authority_identity_sets)
        if len(set(values)) != len(values):
            raise ReceiptError("a counterfactual inherited a BASE authority")
    validation = evaluate_global_uf_validation(
        authority_id=authority_id,
        topology=topology,
        closed_experience_receipt_sha256=preparation.base_closed_experience_receipt_sha256,
        observation_window=preparation.observation_window,
        sensor_resolution_profile=preparation.sensor_resolution_profile,
        pre_window_state=pre_window_state,
        replay_provider=_ReplayProvider(responses),
        receipt_registry=registry,
    )
    return StoryGlobalUFExecutionResult(preparation, validation, validation.receipt_registry)


__all__ = (
    "MountedStoryGlobalUFBasinProfile",
    "MountedStoryReplayAuthorities",
    "PreparedStoryReplayContext",
    "STORY_GLOBAL_UF_BASIN_OPERATOR_ID",
    "StoryGlobalUFExecutionResult",
    "StoryGlobalUFPreparation",
    "StoryReplayExpressionFacts",
    "evaluate_story_global_uf",
    "prepare_story_global_uf",
    "story_global_uf_basin_profile_receipt_payload",
)
