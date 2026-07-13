"""Unmocked conformance for atomic committed-coexperience learning.

The fixture obtains its language geometry from the discrete one-sided
contingent cone and its five sensor geometries from the continuous physical
tangent producer.  CommitDecision is produced only by the real conjunction;
it is never constructed by this test.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.closed_experience import (
    L5ApplicabilityRule,
    MountedL5GovernanceProfile,
    SealedClosedExperience,
    l5_governance_profile_receipt_payload,
    seal_closed_experience,
)
from dsf_ai_service.glew_runtime.commit import (
    ApplicabilityState,
    AuthorityDisposition,
    BinaryAuthorityKind,
    BinaryCommitAuthority,
    CommitStatus,
    GovernedFact,
    L6ScopeAuthority,
    binary_authority_receipt_payload,
    evaluate_commit_boundary,
    l6_evaluation_receipt_payload,
    l6_scope_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.event_support import (
    EventSupportEvaluationStatus,
    MemoryEnergyAuthority,
    evaluate_event_support,
    memory_energy_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.experience_origin import (
    ExperienceOriginAuthority,
    ExperienceOriginKind,
    experience_origin_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.expression_learning import (
    CoexperiencedOutput,
    CommittedCoexperience,
    CommittedModeRelation,
    LearnedBindingState,
    create_coexperienced_no_output,
    create_learned_binding_genesis,
    derive_committed_mode_relation,
    learn_committed_binding_transaction,
    learned_binding_checkpoint_payload,
    restore_learned_binding_checkpoint,
)
from dsf_ai_service.glew_runtime.expression_modes import (
    ExpressionModeBoundaryResult,
    ExpressionRecognitionStatus,
    create_empty_expression_mode_bank,
    evaluate_expression_mode_boundary,
)
from dsf_ai_service.glew_runtime.expressions import (
    FieldExpressionStep,
    PrecisionScheduleAuthority,
    create_closed_experience_expression,
    precision_schedule_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.field import (
    ExactComplex,
    ExactFieldState,
    FieldEvolutionAuthority,
    MountedFieldTopology,
    canonical_component_partition,
    evolution_authority_receipt_payload,
    exact_field_state_receipt_payload,
    source_coefficients_for_injection,
)
from dsf_ai_service.glew_runtime.l6 import (
    LANE_ORDER,
    ActiveLaneState,
    Fixed42ConstraintStack,
    L6Evaluation,
    L6EvaluationStatus,
    L6Lane,
    L6PredicateInputs,
    evaluate_l6,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.output import (
    MotifEventKind,
    OutputBindingKind,
)
from dsf_ai_service.glew_runtime.physical_l6_tangents import (
    PhysicalTangentProductionStatus,
    produce_physical_l6_tangents,
)
from dsf_ai_service.glew_runtime.safe_mode import (
    IntegrityFact,
    IntegrityFactState,
    MountedSafeModeScope,
    evaluate_safe_mode,
    integrity_fact_receipt_payload,
    safe_mode_scope_receipt_payload,
)
from tests.glew_runtime.test_closed_experience_provider import (
    _physical_replay_bundle,
)
from tests.glew_runtime.test_typed_language_native_replay import (
    MountedReplay,
    _mounted_replay,
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _extend(
    registry: ReceiptRegistry,
    *payloads: bytes,
) -> ReceiptRegistry:
    records = list(registry.records)
    mounted = {value.digest: value.payload for value in records}
    for payload in payloads:
        digest = receipt_sha256(payload)
        prior = mounted.get(digest)
        if prior is not None:
            if prior != payload:
                raise AssertionError("test receipt digest collision")
            continue
        mounted[digest] = payload
        records.append(ReceiptRecord(digest, payload))
    return ReceiptRegistry(registry.profile_binding_sha256, tuple(records))


def _merge(
    registry: ReceiptRegistry,
    addition: ReceiptRegistry,
) -> ReceiptRegistry:
    if registry.profile_binding_sha256 != addition.profile_binding_sha256:
        raise AssertionError("test registries use different profiles")
    return _extend(registry, *(value.payload for value in addition.records))


def _mode_payloads(
    result: ExpressionModeBoundaryResult,
) -> tuple[bytes, ...]:
    payloads = [
        result.pre_growth_bank.receipt_payload,
        result.post_growth_bank.receipt_payload,
        result.receipt_payload,
    ]
    for bank in (result.pre_growth_bank, result.post_growth_bank):
        for mode in bank.modes:
            payloads.extend(
                (
                    mode.source_expression.receipt_payload,
                    mode.growth_proof_receipt_payload,
                    mode.receipt_payload,
                )
            )
    return tuple(payloads)


def _field_expression(
    *,
    mounted: MountedReplay,
    execution_index: int,
    identity: str,
    precision: PrecisionScheduleAuthority,
    physical_profile_receipt_sha256: str,
    receipt_registry: ReceiptRegistry,
):
    preparation = mounted.replay.executions[execution_index].preparation
    topology = mounted.topology
    registry = receipt_registry
    steps = []
    authority_payloads = []
    for index, event in enumerate(preparation.events):
        source = source_coefficients_for_injection(
            event.injection,
            event.source_time_end - event.source_time_start,
        )
        components = canonical_component_partition(topology.dimension, ())
        authority_id = f"{identity}:field:{index:08d}"
        payload = evolution_authority_receipt_payload(
            authority_id=authority_id,
            physical_profile_receipt_sha256=physical_profile_receipt_sha256,
            topology_authority_receipt_sha256=(
                topology.authority_receipt_sha256
            ),
            map_injection_receipt_sha256=event.injection.receipt_sha256,
            source_time_start=event.source_time_start,
            source_time_end=event.source_time_end,
            source_time_unit="expression-learning-structural-time",
            hbar=Fraction(1),
            hamiltonian=(),
            local_rates=(),
            source=source,
            component_partition=components,
            max_connected_component_dimension=1,
            precision_bits=256,
        )
        authority = FieldEvolutionAuthority(
            authority_id=authority_id,
            physical_profile_receipt_sha256=physical_profile_receipt_sha256,
            topology_authority_receipt_sha256=(
                topology.authority_receipt_sha256
            ),
            map_injection_receipt_sha256=event.injection.receipt_sha256,
            source_time_start=event.source_time_start,
            source_time_end=event.source_time_end,
            source_time_unit="expression-learning-structural-time",
            hbar=Fraction(1),
            hamiltonian=(),
            local_rates=(),
            source=source,
            max_connected_component_dimension=1,
            precision_bits=256,
            authority_receipt_sha256=receipt_sha256(payload),
        )
        steps.append(FieldExpressionStep(event.injection, authority))
        authority_payloads.append(payload)
    initial_payload = exact_field_state_receipt_payload(
        topology.authority_receipt_sha256,
        preparation.source_time_start,
        tuple(ExactComplex(Fraction(0)) for _ in range(topology.dimension)),
    )
    initial = ExactFieldState(
        topology.authority_receipt_sha256,
        preparation.source_time_start,
        tuple(ExactComplex(Fraction(0)) for _ in range(topology.dimension)),
        receipt_sha256(initial_payload),
    )
    registry = _extend(
        registry,
        *authority_payloads,
        initial_payload,
    )
    expression = create_closed_experience_expression(
        topology=topology,
        initial_state=initial,
        steps=tuple(steps),
        precision_authority=precision,
        receipt_registry=registry,
    )
    registry = _extend(registry, expression.receipt_payload)
    return preparation, expression, registry


def _recognize_pair(
    *,
    topology: MountedFieldTopology,
    precision: PrecisionScheduleAuthority,
    root_expression,
    content_expression,
    receipt_registry: ReceiptRegistry,
):
    empty = create_empty_expression_mode_bank(
        topology=topology,
        precision_authority=precision,
        receipt_registry=receipt_registry,
    )
    registry = _extend(receipt_registry, empty.receipt_payload)
    root_growth = evaluate_expression_mode_boundary(
        topology=topology,
        bank=empty,
        input_expression=root_expression,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(root_growth))
    assert root_growth.status is ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
    assert root_growth.post_growth_bank.rank == 1
    content_growth = evaluate_expression_mode_boundary(
        topology=topology,
        bank=root_growth.post_growth_bank,
        input_expression=content_expression,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(content_growth))
    assert content_growth.status is ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
    assert content_growth.post_growth_bank.rank == 2
    root_recognition = evaluate_expression_mode_boundary(
        topology=topology,
        bank=content_growth.post_growth_bank,
        input_expression=root_expression,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(root_recognition))
    content_recognition = evaluate_expression_mode_boundary(
        topology=topology,
        bank=content_growth.post_growth_bank,
        input_expression=content_expression,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(content_recognition))
    assert root_recognition.status is ExpressionRecognitionStatus.RECOGNIZED
    assert content_recognition.status is ExpressionRecognitionStatus.RECOGNIZED
    assert root_recognition.winner_mode_index != (
        content_recognition.winner_mode_index
    )
    return root_recognition, content_recognition, registry


def _seal_expression(
    *,
    topology: MountedFieldTopology,
    preparation,
    expression,
    recognition: ExpressionModeBoundaryResult,
    identity: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[SealedClosedExperience, ReceiptRegistry]:
    rules = tuple(
        L5ApplicabilityRule(
            fiber.lane_id,
            fiber.port_id,
            fact,
            ApplicabilityState.REQUIRED,
        )
        for fiber in topology.ordered_port_fibers
        for fact in (GovernedFact.S_UF, GovernedFact.R_UF)
    )
    l5_payload = l5_governance_profile_receipt_payload(
        profile_id=f"{identity}:L5",
        topology_authority_receipt_sha256=(
            topology.authority_receipt_sha256
        ),
        rules=rules,
    )
    l5 = MountedL5GovernanceProfile(
        f"{identity}:L5",
        topology.authority_receipt_sha256,
        rules,
        receipt_sha256(l5_payload),
    )
    registry = _extend(receipt_registry, l5_payload)
    sealed = seal_closed_experience(
        experience_id=identity,
        structural_time_unit="expression-learning-structural-time",
        preparation=preparation,
        topology=topology,
        l5_governance=l5,
        expression=expression,
        recognition=recognition,
        receipt_registry=registry,
    )
    return sealed, _merge(registry, sealed.receipt_registry)


def _physical_l6(
    mounted: MountedReplay,
    receipt_registry: ReceiptRegistry,
) -> tuple[L6Evaluation, ReceiptRegistry]:
    payloads: list[bytes] = []
    sensor_bundles = tuple(
        _physical_replay_bundle(
            lane=L6Lane(fiber.lane_id),
            native_port_id=fiber.port_id,
            pre_window=mounted.pre_window,
            payloads=payloads,
        )
        for fiber in mounted.topology.ordered_port_fibers
        if fiber.lane_id != L6Lane.LANGUAGE.value
    )
    registry = _extend(receipt_registry, *payloads)
    sensors = produce_physical_l6_tangents(
        bundles=sensor_bundles,
        pre_window_state=mounted.pre_window,
        receipt_registry=registry,
    )
    assert sensors.status is PhysicalTangentProductionStatus.KNOWN
    assert sensors.candidate_constraints is not None
    assert sensors.candidate_constraints.stack is not None
    registry = _merge(registry, sensors.receipt_registry)
    cone = mounted.replay.contingent_cone
    rows = (
        *cone.fixed42_stack.rows,
        *sensors.candidate_constraints.stack.rows,
    )
    stack = Fixed42ConstraintStack(rows)
    completeness = {
        L6Lane.LANGUAGE: cone.row_completeness_receipt_sha256,
        **{
            value.lane: value.receipt_sha256
            for value in sensors.lane_completeness_receipts
        },
    }
    sensor_u_star = {
        value.profile.lane: value.response_set.responses[0].l4_response.U_star_k
        for value in sensors.derived_ports
    }
    language_u_star = mounted.replay.executions[0].l4_response.U_star_k
    predicates = L6PredicateInputs(
        tuple(
            ActiveLaneState(
                lane,
                (
                    language_u_star
                    if lane is L6Lane.LANGUAGE
                    else sensor_u_star[lane]
                ),
                True,
                completeness[lane],
            )
            for lane in LANE_ORDER
        ),
        True,
    )
    evaluation = evaluate_l6(stack, predicates, registry)
    assert evaluation.status is L6EvaluationStatus.LOCK
    return evaluation, registry


def _committed(
    *,
    identity: str,
    sealed: SealedClosedExperience,
    topology: MountedFieldTopology,
    l6_evaluation: L6Evaluation,
    receipt_registry: ReceiptRegistry,
) -> tuple[CommittedCoexperience, ReceiptRegistry]:
    experience_digest = sealed.closed_experience.authority_receipt_sha256
    topology_digest = topology.authority_receipt_sha256
    safe_profile = _canonical_bytes(
        {
            "identity": identity,
            "schema": "glew.test.expression_learning.integrity_profile.v1",
        }
    )
    fact_ids = ("chemistry", "field", "persistence")
    safe_scope_payload = safe_mode_scope_receipt_payload(
        scope_id=f"{identity}:safe-scope",
        topology_authority_receipt_sha256=topology_digest,
        required_fact_ids=fact_ids,
        source_profile_receipt_sha256=receipt_sha256(safe_profile),
    )
    safe_scope = MountedSafeModeScope(
        f"{identity}:safe-scope",
        topology_digest,
        fact_ids,
        receipt_sha256(safe_profile),
        receipt_sha256(safe_scope_payload),
    )
    facts = []
    fact_payloads = []
    for fact_id in fact_ids:
        source = f"{identity}:integrity:{fact_id}".encode()
        payload = integrity_fact_receipt_payload(
            fact_id=fact_id,
            state=IntegrityFactState.CLEAR,
            topology_authority_receipt_sha256=topology_digest,
            closed_experience_receipt_sha256=experience_digest,
            source_operator_receipt_sha256=receipt_sha256(source),
        )
        facts.append(
            IntegrityFact(
                fact_id,
                IntegrityFactState.CLEAR,
                topology_digest,
                experience_digest,
                receipt_sha256(source),
                receipt_sha256(payload),
            )
        )
        fact_payloads.extend((source, payload))
    registry = _extend(
        receipt_registry,
        safe_profile,
        safe_scope_payload,
        *fact_payloads,
    )
    safe = evaluate_safe_mode(
        authority_id=f"{identity}:safe",
        topology_authority_receipt_sha256=topology_digest,
        closed_experience_receipt_sha256=experience_digest,
        scope=safe_scope,
        facts=tuple(facts),
        receipt_registry=registry,
    )
    assert safe.disposition is AuthorityDisposition.PASS
    registry = _extend(registry, *safe.generated_receipt_payloads)

    origin_source = f"{identity}:fresh-origin-source".encode()
    origin_payload = experience_origin_authority_receipt_payload(
        origin_id=f"{identity}:fresh-origin",
        kind=ExperienceOriginKind.FRESH_EXTERNAL,
        profile_binding_sha256=registry.profile_binding_sha256,
        topology_authority_receipt_sha256=topology_digest,
        closed_experience_receipt_sha256=experience_digest,
        source_authority_receipt_sha256=receipt_sha256(origin_source),
    )
    origin = ExperienceOriginAuthority(
        f"{identity}:fresh-origin",
        ExperienceOriginKind.FRESH_EXTERNAL,
        registry.profile_binding_sha256,
        topology_digest,
        experience_digest,
        receipt_sha256(origin_source),
        receipt_sha256(origin_payload),
    )
    energy_derivation = f"{identity}:memory-energy-derivation".encode()
    physical_profile = sealed.expression.steps[
        0
    ].authority.physical_profile_receipt_sha256
    energy_payload = memory_energy_authority_receipt_payload(
        authority_id=f"{identity}:memory-energy",
        energy_unit_id="expression-learning-energy-unit",
        exact_memory_energy=Fraction(1),
        derivation_receipt_sha256=receipt_sha256(energy_derivation),
        physical_profile_receipt_sha256=physical_profile,
    )
    energy = MemoryEnergyAuthority(
        f"{identity}:memory-energy",
        "expression-learning-energy-unit",
        Fraction(1),
        receipt_sha256(energy_derivation),
        physical_profile,
        receipt_sha256(energy_payload),
    )
    registry = _extend(
        registry,
        origin_source,
        origin_payload,
        energy_derivation,
        energy_payload,
    )
    event = evaluate_event_support(
        authority_id=f"{identity}:R-event",
        origin=origin,
        topology=topology,
        closed_experience_receipt_sha256=experience_digest,
        expression=sealed.expression,
        memory_energy=energy,
        receipt_registry=registry,
    )
    assert event.status is EventSupportEvaluationStatus.RESOLVED
    registry = _extend(registry, *event.generated_receipt_payloads)

    l6_payload = l6_evaluation_receipt_payload(l6_evaluation)
    l6_scope_payload = l6_scope_authority_receipt_payload(
        authority_id=f"{identity}:L6-scope",
        topology_authority_receipt_sha256=topology_digest,
        closed_experience_receipt_sha256=experience_digest,
        l6_evaluation_receipt_sha256=receipt_sha256(l6_payload),
    )
    l6_scope = L6ScopeAuthority(
        f"{identity}:L6-scope",
        topology_digest,
        experience_digest,
        receipt_sha256(l6_payload),
        receipt_sha256(l6_scope_payload),
    )
    global_source = _canonical_bytes(
        {
            "identity": identity,
            "scope": "independently_mounted_exact_global_uf_authority",
            "schema": "glew.test.expression_learning.global_uf_source.v1",
        }
    )
    global_payload = binary_authority_receipt_payload(
        authority_id=f"{identity}:global-UF",
        kind=BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
        disposition=AuthorityDisposition.PASS,
        topology_authority_receipt_sha256=topology_digest,
        closed_experience_receipt_sha256=experience_digest,
        source_operator_receipt_sha256=receipt_sha256(global_source),
    )
    global_uf = BinaryCommitAuthority(
        f"{identity}:global-UF",
        BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
        AuthorityDisposition.PASS,
        topology_digest,
        experience_digest,
        receipt_sha256(global_source),
        receipt_sha256(global_payload),
    )
    registry = _extend(
        registry,
        l6_payload,
        l6_scope_payload,
        global_source,
        global_payload,
    )
    decision = evaluate_commit_boundary(
        topology=topology,
        recognition=sealed.recognition,
        l6_evaluation=l6_evaluation,
        l6_scope=l6_scope,
        closed_experience=sealed.closed_experience,
        safe_mode=safe.authority,
        event_support=event.authority,
        evidence=sealed.evidence,
        l5_applicability=sealed.l5_applicability,
        global_uf_validation=global_uf,
        receipt_registry=registry,
    )
    assert decision.status is CommitStatus.COMMIT
    registry = _extend(registry, decision.receipt_payload)
    winner = sealed.recognition.winner_mode_index
    assert winner is not None
    committed = CommittedCoexperience(
        decision,
        sealed,
        sealed.recognition.pre_growth_bank.modes[winner],
    )
    committed.verify(registry)
    return committed, registry


@dataclass(frozen=True, slots=True)
class LearningWorld:
    mounted: MountedReplay
    root: CommittedCoexperience
    content: CommittedCoexperience
    initial_relation: CommittedModeRelation
    genesis: LearnedBindingState
    receipt_registry: ReceiptRegistry


@pytest.fixture(scope="module")
def learning_world() -> LearningWorld:
    mounted = _mounted_replay("b")
    l6, registry = _physical_l6(mounted, mounted.registry)
    physical_profile_payload = _canonical_bytes(
        {
            "identity": "expression-learning-shared-field-profile",
            "schema": "glew.test.expression_learning.exact_field_profile.v1",
        }
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="expression-learning-shared-precision",
        maximum_precision_bits=4096,
    )
    precision = PrecisionScheduleAuthority(
        "expression-learning-shared-precision",
        4096,
        receipt_sha256(precision_payload),
    )
    registry = _extend(
        registry,
        physical_profile_payload,
        precision_payload,
    )
    root_preparation, root_expression, registry = _field_expression(
        mounted=mounted,
        execution_index=1,
        identity="expression-learning-root",
        precision=precision,
        physical_profile_receipt_sha256=receipt_sha256(
            physical_profile_payload
        ),
        receipt_registry=registry,
    )
    content_preparation, content_expression, registry = _field_expression(
        mounted=mounted,
        execution_index=0,
        identity="expression-learning-content",
        precision=precision,
        physical_profile_receipt_sha256=receipt_sha256(
            physical_profile_payload
        ),
        receipt_registry=registry,
    )
    root_recognition, content_recognition, registry = _recognize_pair(
        topology=mounted.topology,
        precision=precision,
        root_expression=root_expression,
        content_expression=content_expression,
        receipt_registry=registry,
    )
    root_sealed, registry = _seal_expression(
        topology=mounted.topology,
        preparation=root_preparation,
        expression=root_expression,
        recognition=root_recognition,
        identity="expression-learning-root",
        receipt_registry=registry,
    )
    content_sealed, registry = _seal_expression(
        topology=mounted.topology,
        preparation=content_preparation,
        expression=content_expression,
        recognition=content_recognition,
        identity="expression-learning-content",
        receipt_registry=registry,
    )
    root, registry = _committed(
        identity="expression-learning-root",
        sealed=root_sealed,
        topology=mounted.topology,
        l6_evaluation=l6,
        receipt_registry=registry,
    )
    content, registry = _committed(
        identity="expression-learning-content",
        sealed=content_sealed,
        topology=mounted.topology,
        l6_evaluation=l6,
        receipt_registry=registry,
    )
    assert root.selected_mode.receipt_sha256 != content.selected_mode.receipt_sha256
    initial_relation, registry = derive_committed_mode_relation(
        relation_id="expression-learning-root-relation",
        committed=root,
        output_source_receipt_sha256=root.commit.receipt_sha256,
        receipt_registry=registry,
    )
    genesis = create_learned_binding_genesis(
        state_id="expression-learning-state",
        expression_id="expression-learning-expression",
        initial_relation=initial_relation,
        receipt_registry=registry,
    )
    return LearningWorld(
        mounted,
        root,
        content,
        initial_relation,
        genesis,
        genesis.receipt_registry,
    )

def _learn_content(world: LearningWorld) -> LearnedBindingState:
    return learn_committed_binding_transaction(
        state=world.genesis,
        committed=world.content,
        coexperienced_output=CoexperiencedOutput.from_typed_scalar(
            world.mounted.language
        ),
        prior_relation=world.initial_relation,
        relation_id="expression-learning-content-relation",
        expression_close=False,
        receipt_registry=world.receipt_registry,
    )


def _learn_close(
    world: LearningWorld,
    content: LearnedBindingState,
) -> LearnedBindingState:
    no_output, registry = create_coexperienced_no_output(
        event_id="expression-learning-explicit-close",
        sealed=world.root.sealed,
        source_authority_receipt_sha256=world.root.commit.receipt_sha256,
        receipt_registry=content.receipt_registry,
    )
    assert content.pending_relation is not None
    return learn_committed_binding_transaction(
        state=content,
        committed=world.root,
        coexperienced_output=CoexperiencedOutput.from_no_output(no_output),
        prior_relation=content.pending_relation,
        relation_id="expression-learning-close-relation",
        expression_close=True,
        receipt_registry=registry,
    )


def test_atomic_commit_binds_exact_mode_to_motif_to_typed_output(
    learning_world: LearningWorld,
) -> None:
    before_digest = learning_world.genesis.receipt_sha256
    before_records = learning_world.genesis.receipt_registry.records

    learned = _learn_content(learning_world)

    assert learning_world.genesis.receipt_sha256 == before_digest
    assert learning_world.genesis.receipt_registry.records == before_records
    assert learned.receipt_sha256 != before_digest
    assert learned.initial_event is not None
    assert learned.initial_event.event_kind is MotifEventKind.CONTENT
    stable = learned.stable_bank.resolve_unique(
        learning_world.root.selected_mode.receipt_sha256,
        learned.receipt_registry,
    )
    assert stable.motif_receipt_sha256 == learned.initial_event.motif_receipt_sha256
    bindings = learned.output_bank.for_motif(stable.motif_receipt_sha256)
    assert len(bindings) == 1
    binding = bindings[0]
    assert binding.kind is OutputBindingKind.LANGUAGE_SCALAR
    assert binding.trits == learning_world.mounted.language.event.trits
    assert binding.coexperienced_output_receipt_sha256 == (
        learning_world.mounted.language.event.event_receipt_sha256
    )
    assert binding.closed_experience_receipt_sha256 == (
        learning_world.content.sealed.closed_experience.authority_receipt_sha256
    )
    assert binding.sensory_evidence_receipt_sha256s == tuple(
        sorted(
            value.evidence_receipt_sha256
            for value in learning_world.content.sealed.evidence
            if value.lane_id != "language"
        )
    )
    learned.verify()

    with pytest.raises(ReceiptError, match="another prior relation"):
        learn_committed_binding_transaction(
            state=learning_world.genesis,
            committed=learning_world.content,
            coexperienced_output=CoexperiencedOutput.from_typed_scalar(
                learning_world.mounted.language
            ),
            prior_relation=learned.pending_relation,
            relation_id="expression-learning-rejected-relation",
            expression_close=False,
            receipt_registry=learned.receipt_registry,
        )
    assert learning_world.genesis.receipt_sha256 == before_digest
    assert learning_world.genesis.receipt_registry.records == before_records


def test_explicit_no_output_closes_only_after_the_committed_content_successor(
    learning_world: LearningWorld,
) -> None:
    content = _learn_content(learning_world)

    closed = _learn_close(learning_world, content)

    assert closed.terminal
    assert closed.pending_relation is None
    assert closed.initial_event is not None
    assert closed.initial_event.event_kind is MotifEventKind.CONTENT
    assert closed.output_bank.bindings == content.output_bank.bindings
    assert len(closed.stable_bank.bindings) == 2
    assert len(closed.motif_kinds) == 2
    close_kinds = tuple(
        value for value in closed.motif_kinds if value.kind.value == "expression_close"
    )
    assert len(close_kinds) == 1
    close_stable = closed.stable_bank.resolve_unique(
        learning_world.content.selected_mode.receipt_sha256,
        closed.receipt_registry,
    )
    assert close_stable.motif_receipt_sha256 == close_kinds[0].motif_receipt_sha256
    assert closed.output_bank.for_motif(close_stable.motif_receipt_sha256) == ()
    closed.verify()


def test_authenticated_checkpoint_is_bit_identical_and_tamper_fails_closed(
    learning_world: LearningWorld,
) -> None:
    closed = _learn_close(learning_world, _learn_content(learning_world))
    key = bytes(range(32))
    checkpoint = learned_binding_checkpoint_payload(
        state=closed,
        checkpoint_id="expression-learning-checkpoint",
        authentication_key=key,
        key_id="expression-learning-key",
    )

    restarted = restore_learned_binding_checkpoint(
        checkpoint_payload=checkpoint,
        authentication_key=key,
        expected_key_id="expression-learning-key",
    )

    assert restarted == closed
    assert restarted.receipt_sha256 == closed.receipt_sha256
    assert restarted.receipt_payload == closed.receipt_payload
    assert restarted.receipt_registry.records == closed.receipt_registry.records
    restarted.verify()

    envelope = json.loads(checkpoint)
    envelope["body"]["checkpoint_id"] = "expression-learning-tampered"
    tampered = _canonical_bytes(envelope)
    with pytest.raises(ReceiptError, match="authentication failed"):
        restore_learned_binding_checkpoint(
            checkpoint_payload=tampered,
            authentication_key=key,
            expected_key_id="expression-learning-key",
        )
    with pytest.raises(ReceiptError, match="authentication failed"):
        restore_learned_binding_checkpoint(
            checkpoint_payload=checkpoint,
            authentication_key=b"another-exact-checkpoint-key",
            expected_key_id="expression-learning-key",
        )

