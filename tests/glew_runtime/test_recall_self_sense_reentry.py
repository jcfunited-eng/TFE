"""Vertical conformance for fresh recall self-sense expression settlement."""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.glew_runtime.commit import (
    CommitDecision,
    CommitStatus,
    _decision_payload,
    closed_experience_seal_receipt_payload,
)
from dsf_ai_service.glew_runtime.expression_modes import (
    ExpressionModeBoundaryResult,
    create_empty_expression_mode_bank,
    evaluate_expression_mode_boundary,
)
from dsf_ai_service.glew_runtime.expressions import (
    FieldExpressionStep,
    PrecisionScheduleAuthority,
    create_closed_experience_expression,
    evaluate_closed_experience_expression,
    precision_schedule_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.field import (
    ExactComplex,
    PortFiber,
    PortTransportEvidence,
)
from dsf_ai_service.glew_runtime.language import encode_balanced_ternary_scalar
import pytest

from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.output import (
    CommittedMotifEvent,
    MotifBindingBank,
    MotifEventKind,
    MotifOutputBinding,
    OutputBindingKind,
    committed_motif_event_receipt_payload,
    expression_close_authority_receipt_payload,
    motif_binding_bank_receipt_payload,
    motif_output_binding_receipt_payload,
)
from dsf_ai_service.glew_runtime.recall_reentry import (
    FRESH_RECALL_SELF_SENSE_OPERATOR_ID,
    CompleteExpressionStatus,
    RecallTransitionSettlement,
    RecallTransitionStatus,
    StableModeMotifBank,
    StableModeMotifBinding,
    fresh_recall_provider_authority_receipt_payload,
    recall_expression_input_receipt_payload,
    recall_transition_settlement_receipt_payload,
    recalled_language_transduction_receipt_payload,
    settle_complete_remembered_expression,
    stable_mode_motif_bank_receipt_payload,
    stable_mode_motif_binding_receipt_payload,
    transition_context_match_receipt_payload,
    transition_context_receipt_payload,
)
from tests.glew_runtime.test_field import (
    COMMON_AUTHORITIES,
    evidence,
    evolution_authority,
    exact_state,
    make_injection,
)


class _World:
    def __init__(self) -> None:
        self.profile_payload = b"recall-self-sense-integration-profile"
        self.profile_sha256 = receipt_sha256(self.profile_payload)
        self.payloads: dict[str, bytes] = {
            self.profile_sha256: self.profile_payload
        }
        for payload in COMMON_AUTHORITIES:
            self.mount(payload)

    def mount(self, payload: bytes) -> str:
        digest = receipt_sha256(payload)
        self.payloads[digest] = payload
        return digest

    def fact(self, name: str) -> str:
        return self.mount(f"recall-fact:{name}".encode())

    def closed_experience(
        self,
        name: str,
        sensory: tuple[PortTransportEvidence, ...],
    ) -> str:
        language_payload = json.dumps(
            {
                "lane_id": "language",
                "schema": "glew.field.transport_evidence.v1",
            },
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        language_receipt = self.mount(language_payload)
        payload = closed_experience_seal_receipt_payload(
            experience_id=f"{name}:closed-experience",
            topology_authority_receipt_sha256=self.fact(f"{name}:topology"),
            input_expression_receipt_sha256=self.fact(f"{name}:expression"),
            recognition_receipt_sha256=self.fact(f"{name}:recognition"),
            ordered_evidence_receipt_sha256s=(
                language_receipt,
                *(value.evidence_receipt_sha256 for value in sensory),
            ),
            source_time_start=Fraction(0),
            source_time_end=Fraction(1),
            structural_time_unit="structural_second",
        )
        return self.mount(payload)

    def registry(self, *extra: bytes) -> ReceiptRegistry:
        combined = dict(self.payloads)
        for payload in extra:
            combined[receipt_sha256(payload)] = payload
        return ReceiptRegistry.from_payloads(
            profile_payload=self.profile_payload,
            receipt_payloads=tuple(
                payload
                for digest, payload in combined.items()
                if digest != self.profile_sha256
            ),
        )


@dataclass(frozen=True)
class _PhysicalExperience:
    expression: object
    evaluation: object
    language_evidence: PortTransportEvidence
    sensory_evidence: tuple[PortTransportEvidence, ...]


def _physical_experience(
    world: _World,
    *,
    axis: int,
) -> _PhysicalExperience:
    lanes = (
        ("language", "typed"),
        ("sight", "retina"),
        ("sound", "cochlea"),
        ("touch", "skin"),
    )
    records = []
    for lane_index, (lane, port) in enumerate(lanes):
        values = [Fraction(0)] * 19
        if lane_index == 0:
            values[axis] = Fraction(1)
        else:
            values[(axis + lane_index) % 19] = Fraction(1, lane_index + 2)
        records.append(evidence(lane, port, tuple(values)))
    fibers = tuple(PortFiber(lane, port) for lane, port in lanes)
    topology, injection, injection_payloads = make_injection(
        fibers,
        tuple(records),
    )
    authority, authority_payload = evolution_authority(
        topology,
        injection,
        max_component=topology.dimension,
    )
    initial, initial_payload = exact_state(
        topology,
        Fraction(5),
        (ExactComplex(Fraction(0)),) * topology.dimension,
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="recall-expression-precision",
        maximum_precision_bits=4096,
    )
    precision = PrecisionScheduleAuthority(
        authority_id="recall-expression-precision",
        maximum_precision_bits=4096,
        authority_receipt_sha256=receipt_sha256(precision_payload),
    )
    for payload in (
        *injection_payloads,
        authority_payload,
        initial_payload,
        precision_payload,
    ):
        world.mount(payload)
    registry = world.registry()
    expression = create_closed_experience_expression(
        topology=topology,
        initial_state=initial,
        steps=(FieldExpressionStep(injection, authority),),
        precision_authority=precision,
        receipt_registry=registry,
    )
    evaluation = evaluate_closed_experience_expression(
        expression,
        receipt_registry=registry,
    )
    world.mount(expression.receipt_payload)
    world.mount(evaluation.receipt_payload)
    return _PhysicalExperience(
        expression=expression,
        evaluation=evaluation,
        language_evidence=records[0][0],
        sensory_evidence=tuple(
            sorted(
                (record[0] for record in records[1:]),
                key=lambda value: value.evidence_receipt_sha256,
            )
        ),
    )


def _output_binding(
    world: _World,
    *,
    binding_id: str,
    motif_receipt_sha256: str,
    scalar: str,
    sensory: tuple[PortTransportEvidence, ...],
) -> MotifOutputBinding:
    closed = world.closed_experience(binding_id, sensory)
    strand = world.fact(f"{binding_id}:strand")
    output = world.fact(f"{binding_id}:typed-output")
    sensory_digests = tuple(
        value.evidence_receipt_sha256 for value in sensory
    )
    trits = encode_balanced_ternary_scalar(ord(scalar))
    payload = motif_output_binding_receipt_payload(
        binding_id=binding_id,
        profile_binding_sha256=world.profile_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        closed_experience_receipt_sha256=closed,
        fact_strand_receipt_sha256=strand,
        sensory_evidence_receipt_sha256s=sensory_digests,
        coexperienced_output_receipt_sha256=output,
        kind=OutputBindingKind.LANGUAGE_SCALAR,
        trits=trits,
        language_scalar_cardinality=1,
        no_output_cardinality=0,
    )
    return MotifOutputBinding(
        binding_id=binding_id,
        profile_binding_sha256=world.profile_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        closed_experience_receipt_sha256=closed,
        fact_strand_receipt_sha256=strand,
        sensory_evidence_receipt_sha256s=sensory_digests,
        coexperienced_output_receipt_sha256=output,
        kind=OutputBindingKind.LANGUAGE_SCALAR,
        trits=trits,
        language_scalar_cardinality=1,
        no_output_cardinality=0,
        binding_receipt_sha256=world.mount(payload),
    )


def _output_bank(
    world: _World,
    bindings: tuple[MotifOutputBinding, ...],
) -> MotifBindingBank:
    ordered = tuple(
        sorted(
            bindings,
            key=lambda value: (
                value.motif_receipt_sha256,
                value.binding_id,
                value.binding_receipt_sha256,
            ),
        )
    )
    payload = motif_binding_bank_receipt_payload(
        bank_id="recall-output-bank",
        profile_binding_sha256=world.profile_sha256,
        bindings=ordered,
    )
    return MotifBindingBank(
        bank_id="recall-output-bank",
        profile_binding_sha256=world.profile_sha256,
        bindings=ordered,
        bank_receipt_sha256=world.mount(payload),
        bank_receipt_payload=payload,
    )


def _commit(
    world: _World,
    recognition: ExpressionModeBoundaryResult,
    *,
    name: str,
    sensory: tuple[PortTransportEvidence, ...],
) -> CommitDecision:
    winner = recognition.winner_mode_index
    assert winner is not None
    selected = recognition.pre_growth_bank.modes[winner]
    experience = world.closed_experience(name, sensory)
    l6 = world.fact(f"{name}:l6")
    safe = world.fact(f"{name}:safe")
    event = world.fact(f"{name}:event-support")
    uf = world.fact(f"{name}:global-uf")
    evidence_receipts = (world.fact(f"{name}:commit-evidence"),)
    applicability = (world.fact(f"{name}:applicability"),)
    payload = _decision_payload(
        status=CommitStatus.COMMIT,
        selected_mode_index=winner,
        selected_mode_receipt_sha256=selected.receipt_sha256,
        findings=(),
        topology_receipt=recognition.pre_growth_bank.topology_authority_receipt_sha256,
        experience_receipt=experience,
        expression_recognition_receipt=recognition.receipt_sha256,
        pre_growth_expression_bank_receipt=(
            recognition.pre_growth_bank.receipt_sha256
        ),
        l6_evaluation_receipt=l6,
        safe_mode_receipt=safe,
        event_support_receipt=event,
        global_uf_receipt=uf,
        evidence_receipts=evidence_receipts,
        applicability_receipts=applicability,
    )
    result = CommitDecision(
        status=CommitStatus.COMMIT,
        selected_mode_index=winner,
        selected_mode_receipt_sha256=selected.receipt_sha256,
        findings=(),
        topology_authority_receipt_sha256=(
            recognition.pre_growth_bank.topology_authority_receipt_sha256
        ),
        closed_experience_receipt_sha256=experience,
        expression_recognition_receipt_sha256=recognition.receipt_sha256,
        pre_growth_expression_bank_receipt_sha256=(
            recognition.pre_growth_bank.receipt_sha256
        ),
        l6_evaluation_receipt_sha256=l6,
        safe_mode_receipt_sha256=safe,
        event_support_receipt_sha256=event,
        global_uf_receipt_sha256=uf,
        evidence_receipt_sha256s=evidence_receipts,
        applicability_receipt_sha256s=applicability,
        receipt_sha256=world.mount(payload),
        receipt_payload=payload,
    )
    result.verify()
    return result


def _stable_binding(
    world: _World,
    *,
    binding_id: str,
    mode_receipt_sha256: str,
    motif_receipt_sha256: str,
) -> StableModeMotifBinding:
    strand = world.fact(f"{binding_id}:mode-motif-strand")
    prior = world.fact(f"{binding_id}:prior-relation")
    input_expr = world.fact(f"{binding_id}:input-expression")
    sensory = (world.fact(f"{binding_id}:sensory"),)
    context_payload = transition_context_receipt_payload(
        profile_binding_sha256=world.profile_sha256,
        mode_receipt_sha256=mode_receipt_sha256,
        prior_relation_receipt_sha256=prior,
        input_expression_receipt_sha256=input_expr,
        sensory_evidence_receipt_sha256s=sensory,
        closed_experience_receipt_sha256=world.fact(f"{binding_id}:closed"),
        recognition_receipt_sha256=world.fact(f"{binding_id}:recognition"),
        commit_receipt_sha256=world.fact(f"{binding_id}:commit"),
        memory_output_bank_receipt_sha256=world.fact(f"{binding_id}:mem-output"),
        memory_stable_bank_receipt_sha256=world.fact(f"{binding_id}:mem-stable"),
    )
    context_digest = world.mount(context_payload)
    context_match = receipt_sha256(
        transition_context_match_receipt_payload(
            prior_relation_receipt_sha256=prior,
            input_expression_receipt_sha256=input_expr,
            sensory_evidence_receipt_sha256s=sensory,
        )
    )
    payload = stable_mode_motif_binding_receipt_payload(
        binding_id=binding_id,
        profile_binding_sha256=world.profile_sha256,
        mode_receipt_sha256=mode_receipt_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        source_fact_strand_receipt_sha256=strand,
        transition_context_receipt_sha256=context_digest,
        transition_context_match_sha256=context_match,
    )
    return StableModeMotifBinding(
        binding_id=binding_id,
        profile_binding_sha256=world.profile_sha256,
        mode_receipt_sha256=mode_receipt_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        source_fact_strand_receipt_sha256=strand,
        transition_context_receipt_sha256=context_digest,
        transition_context_match_sha256=context_match,
        binding_receipt_sha256=world.mount(payload),
    )


def _stable_bank(
    world: _World,
    bindings: tuple[StableModeMotifBinding, ...],
) -> StableModeMotifBank:
    ordered = tuple(
        sorted(
            bindings,
            key=lambda value: (
                value.mode_receipt_sha256,
                value.binding_id,
                value.binding_receipt_sha256,
            ),
        )
    )
    payload = stable_mode_motif_bank_receipt_payload(
        bank_id="stable-mode-motif-bank",
        profile_binding_sha256=world.profile_sha256,
        bindings=ordered,
    )
    return StableModeMotifBank(
        bank_id="stable-mode-motif-bank",
        profile_binding_sha256=world.profile_sha256,
        bindings=ordered,
        bank_receipt_sha256=world.mount(payload),
        bank_receipt_payload=payload,
    )


def _committed_event(
    world: _World,
    *,
    expression_id: str,
    event_id: str,
    motif_receipt_sha256: str,
    sensory: tuple[PortTransportEvidence, ...],
    output_bank: MotifBindingBank,
    source_state: str,
    edge: str,
    result_state: str,
    full_field: str,
    field_commit: str,
    dominant_binding: str,
    closed_experience: str,
    l6_lock: str,
    kind: MotifEventKind = MotifEventKind.CONTENT,
    fact_strand: str | None = None,
) -> CommittedMotifEvent:
    close_authority = None
    if kind is MotifEventKind.EXPRESSION_CLOSE:
        close_payload = expression_close_authority_receipt_payload(
            expression_id=expression_id,
            close_motif_receipt_sha256=motif_receipt_sha256,
        )
        close_authority = world.mount(close_payload)
    # A genesis-anchored initial event's Fact Strand is exactly the root
    # binding's ``source_fact_strand`` (``expression_learning._make_initial_
    # event`` guarantees it); callers verifying that event resolve the binding
    # by that strand, so they can pass it explicitly here.
    strand = (
        fact_strand
        if fact_strand is not None
        else world.fact(f"{event_id}:event-strand")
    )
    sensory_digests = tuple(
        value.evidence_receipt_sha256 for value in sensory
    )
    payload = committed_motif_event_receipt_payload(
        expression_id=expression_id,
        event_id=event_id,
        event_kind=kind,
        profile_binding_sha256=world.profile_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        closed_experience_receipt_sha256=closed_experience,
        fact_strand_receipt_sha256=strand,
        sensory_evidence_receipt_sha256s=sensory_digests,
        full_field_state_receipt_sha256=full_field,
        field_commit_receipt_sha256=field_commit,
        dominant_motif_commit_receipt_sha256=dominant_binding,
        corrected_l6_lock_receipt_sha256=l6_lock,
        output_binding_bank_receipt_sha256=output_bank.bank_receipt_sha256,
        source_state_receipt_sha256=source_state,
        transition_edge_receipt_sha256=edge,
        result_state_receipt_sha256=result_state,
        expression_close_authority_receipt_sha256=close_authority,
    )
    return CommittedMotifEvent(
        expression_id=expression_id,
        event_id=event_id,
        event_kind=kind,
        profile_binding_sha256=world.profile_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        closed_experience_receipt_sha256=closed_experience,
        fact_strand_receipt_sha256=strand,
        sensory_evidence_receipt_sha256s=sensory_digests,
        full_field_state_receipt_sha256=full_field,
        field_commit_receipt_sha256=field_commit,
        dominant_motif_commit_receipt_sha256=dominant_binding,
        corrected_l6_lock_receipt_sha256=l6_lock,
        output_binding_bank_receipt_sha256=output_bank.bank_receipt_sha256,
        source_state_receipt_sha256=source_state,
        transition_edge_receipt_sha256=edge,
        result_state_receipt_sha256=result_state,
        expression_close_authority_receipt_sha256=close_authority,
        event_receipt_sha256=world.mount(payload),
    )


@dataclass(frozen=True)
class _TransitionTemplate:
    physical: _PhysicalExperience
    recognition: ExpressionModeBoundaryResult
    commit: CommitDecision
    stable_binding: StableModeMotifBinding
    next_event: CommittedMotifEvent


class _RealObjectProvider:
    operator_id = FRESH_RECALL_SELF_SENSE_OPERATOR_ID

    def __init__(
        self,
        world: _World,
        templates: tuple[_TransitionTemplate, ...],
    ) -> None:
        self.world = world
        self.templates = list(templates)
        self.provider_id = "real-object-test-provider"
        authority_payload = fresh_recall_provider_authority_receipt_payload(
            provider_id=self.provider_id,
            profile_binding_sha256=world.profile_sha256,
        )
        self.authority_receipt_sha256 = world.mount(authority_payload)

    def settle(
        self,
        *,
        source_event,
        staged_output,
        source_binding,
        output_binding_bank,
        stable_mode_motif_bank,
        receipt_registry,
    ) -> RecallTransitionSettlement:
        template = self.templates.pop(0)
        physical = template.physical
        language = physical.language_evidence
        sensory = physical.sensory_evidence
        transduction_payload = recalled_language_transduction_receipt_payload(
            source_binding_receipt_sha256=source_binding.binding_receipt_sha256,
            language_transport_evidence_receipt_sha256=(
                language.evidence_receipt_sha256
            ),
        )
        transduction = self.world.mount(transduction_payload)
        input_payload = recall_expression_input_receipt_payload(
            source_event_receipt_sha256=source_event.event_receipt_sha256,
            staged_output_settlement_receipt_sha256=(
                staged_output.receipt.receipt_sha256
            ),
            source_binding_receipt_sha256=source_binding.binding_receipt_sha256,
            cited_sensory_evidence_receipt_sha256s=tuple(
                value.evidence_receipt_sha256 for value in sensory
            ),
            language_transport_evidence_receipt_sha256=(
                language.evidence_receipt_sha256
            ),
            language_transduction_receipt_sha256=transduction,
            map_injection_receipt_sha256s=tuple(
                step.injection.receipt_sha256
                for step in physical.expression.steps
            ),
            expression_receipt_sha256=physical.expression.receipt_sha256,
        )
        input_authority = self.world.mount(input_payload)
        settlement_payload = recall_transition_settlement_receipt_payload(
            status=RecallTransitionStatus.COMMITTED,
            provider_id=self.provider_id,
            provider_authority_receipt_sha256=self.authority_receipt_sha256,
            source_event_receipt_sha256=source_event.event_receipt_sha256,
            staged_output_settlement_receipt_sha256=(
                staged_output.receipt.receipt_sha256
            ),
            source_binding_receipt_sha256=source_binding.binding_receipt_sha256,
            cited_sensory_evidence_receipt_sha256s=tuple(
                value.evidence_receipt_sha256 for value in sensory
            ),
            language_transport_evidence_receipt_sha256=(
                language.evidence_receipt_sha256
            ),
            language_transduction_receipt_sha256=transduction,
            expression_input_authority_receipt_sha256=input_authority,
            expression_receipt_sha256=physical.expression.receipt_sha256,
            expression_evaluation_receipt_sha256=(
                physical.evaluation.receipt_sha256
            ),
            expression_recognition_receipt_sha256=(
                template.recognition.receipt_sha256
            ),
            commit_decision_receipt_sha256=template.commit.receipt_sha256,
            stable_mode_motif_binding_receipt_sha256=(
                template.stable_binding.binding_receipt_sha256
            ),
            next_event_receipt_sha256=template.next_event.event_receipt_sha256,
            missing_operator_id=None,
            reason="real full-field expression produced one committed next motif",
        )
        settlement_digest = self.world.mount(settlement_payload)
        registry = self.world.registry()
        return RecallTransitionSettlement(
            status=RecallTransitionStatus.COMMITTED,
            provider_id=self.provider_id,
            provider_authority_receipt_sha256=self.authority_receipt_sha256,
            source_event_receipt_sha256=source_event.event_receipt_sha256,
            staged_output_settlement_receipt_sha256=(
                staged_output.receipt.receipt_sha256
            ),
            source_binding_receipt_sha256=source_binding.binding_receipt_sha256,
            cited_sensory_evidence=sensory,
            language_transport_evidence=language,
            language_transduction_receipt_sha256=transduction,
            expression_input_authority_receipt_sha256=input_authority,
            expression=physical.expression,
            expression_evaluation=physical.evaluation,
            expression_recognition=template.recognition,
            commit_decision=template.commit,
            stable_mode_motif_binding_receipt_sha256=(
                template.stable_binding.binding_receipt_sha256
            ),
            next_event=template.next_event,
            missing_operator_id=None,
            reason="real full-field expression produced one committed next motif",
            receipt_registry=registry,
            receipt_sha256=settlement_digest,
            receipt_payload=settlement_payload,
        )


def _scenario():
    world = _World()
    first = _physical_experience(world, axis=0)
    second = _physical_experience(world, axis=1)
    registry = world.registry()
    mode_bank = create_empty_expression_mode_bank(
        topology=first.expression.topology,
        precision_authority=first.expression.precision_authority,
        receipt_registry=registry,
    )
    first_growth = evaluate_expression_mode_boundary(
        topology=first.expression.topology,
        bank=mode_bank,
        input_expression=first.expression,
        receipt_registry=registry,
    )
    second_growth = evaluate_expression_mode_boundary(
        topology=first.expression.topology,
        bank=first_growth.post_growth_bank,
        input_expression=second.expression,
        receipt_registry=registry,
    )
    recognized_first = evaluate_expression_mode_boundary(
        topology=first.expression.topology,
        bank=second_growth.post_growth_bank,
        input_expression=first.expression,
        receipt_registry=registry,
    )
    recognized_second = evaluate_expression_mode_boundary(
        topology=first.expression.topology,
        bank=second_growth.post_growth_bank,
        input_expression=second.expression,
        receipt_registry=registry,
    )
    for value in (
        recognized_first,
        recognized_second,
    ):
        world.mount(value.receipt_payload)
        for mode in value.pre_growth_bank.modes:
            world.mount(mode.receipt_payload)

    motif_g = world.fact("motif:g")
    motif_o = world.fact("motif:o")
    motif_close = world.fact("motif:close")
    binding_g = _output_binding(
        world,
        binding_id="binding:g",
        motif_receipt_sha256=motif_g,
        scalar="g",
        sensory=first.sensory_evidence,
    )
    binding_o = _output_binding(
        world,
        binding_id="binding:o",
        motif_receipt_sha256=motif_o,
        scalar="o",
        sensory=second.sensory_evidence,
    )
    output_bank = _output_bank(world, (binding_g, binding_o))
    commit_first = _commit(
        world,
        recognized_first,
        name="first",
        sensory=first.sensory_evidence,
    )
    commit_second = _commit(
        world,
        recognized_second,
        name="second",
        sensory=second.sensory_evidence,
    )
    mode_for_first = recognized_first.pre_growth_bank.modes[
        recognized_first.winner_mode_index
    ]
    mode_for_second = recognized_second.pre_growth_bank.modes[
        recognized_second.winner_mode_index
    ]
    stable_first = _stable_binding(
        world,
        binding_id="mode-to-o",
        mode_receipt_sha256=mode_for_first.receipt_sha256,
        motif_receipt_sha256=motif_o,
    )
    stable_second = _stable_binding(
        world,
        binding_id="mode-to-close",
        mode_receipt_sha256=mode_for_second.receipt_sha256,
        motif_receipt_sha256=motif_close,
    )
    stable_bank = _stable_bank(world, (stable_first, stable_second))

    state_a = world.fact("state:a")
    state_b = world.fact("state:b")
    state_c = world.fact("state:c")
    state_d = world.fact("state:d")
    initial = _committed_event(
        world,
        expression_id="complete-go",
        event_id="initial-g",
        motif_receipt_sha256=motif_g,
        sensory=first.sensory_evidence,
        output_bank=output_bank,
        source_state=state_a,
        edge=world.fact("edge:g"),
        result_state=state_b,
        full_field=world.fact("initial:field"),
        field_commit=world.fact("initial:commit"),
        dominant_binding=world.fact("initial:dominant"),
        closed_experience=world.closed_experience(
            "initial",
            first.sensory_evidence,
        ),
        l6_lock=world.fact("initial:l6"),
    )
    event_o = _committed_event(
        world,
        expression_id="complete-go",
        event_id="next-o",
        motif_receipt_sha256=motif_o,
        sensory=first.sensory_evidence,
        output_bank=output_bank,
        source_state=state_b,
        edge=world.fact("edge:o"),
        result_state=state_c,
        full_field=first.evaluation.receipt_sha256,
        field_commit=commit_first.receipt_sha256,
        dominant_binding=stable_first.binding_receipt_sha256,
        closed_experience=commit_first.closed_experience_receipt_sha256,
        l6_lock=commit_first.l6_evaluation_receipt_sha256,
    )
    event_close = _committed_event(
        world,
        expression_id="complete-go",
        event_id="exact-close",
        motif_receipt_sha256=motif_close,
        sensory=second.sensory_evidence,
        output_bank=output_bank,
        source_state=state_c,
        edge=world.fact("edge:close"),
        result_state=state_d,
        full_field=second.evaluation.receipt_sha256,
        field_commit=commit_second.receipt_sha256,
        dominant_binding=stable_second.binding_receipt_sha256,
        closed_experience=commit_second.closed_experience_receipt_sha256,
        l6_lock=commit_second.l6_evaluation_receipt_sha256,
        kind=MotifEventKind.EXPRESSION_CLOSE,
    )
    provider = _RealObjectProvider(
        world,
        (
            _TransitionTemplate(
                first,
                recognized_first,
                commit_first,
                stable_first,
                event_o,
            ),
            _TransitionTemplate(
                second,
                recognized_second,
                commit_second,
                stable_second,
                event_close,
            ),
        ),
    )
    return world, initial, output_bank, stable_bank, provider


def test_real_full_field_reentry_releases_one_complete_expression() -> None:
    world, initial, output_bank, stable_bank, provider = _scenario()

    result = settle_complete_remembered_expression(
        expression_id="complete-go",
        initial_event=initial,
        output_binding_bank=output_bank,
        stable_mode_motif_bank=stable_bank,
        receipt_registry=world.registry(),
        provider=provider,
    )

    assert result.status is CompleteExpressionStatus.RELEASED
    assert result.text == "go"
    assert result.missing_operator_id is None
    assert len(result.transition_settlement_receipt_sha256s) == 2


def test_missing_reentry_provider_is_typed_unknown_and_never_leaks_fragment() -> None:
    world, initial, output_bank, stable_bank, _ = _scenario()

    result = settle_complete_remembered_expression(
        expression_id="complete-go",
        initial_event=initial,
        output_binding_bank=output_bank,
        stable_mode_motif_bank=stable_bank,
        receipt_registry=world.registry(),
        provider=None,
    )

    assert result.status is CompleteExpressionStatus.UNKNOWN_SILENCE
    assert result.text == ""
    assert result.missing_operator_id == FRESH_RECALL_SELF_SENSE_OPERATOR_ID


def test_stable_bank_holds_and_resolves_multiple_successors_of_one_mode():
    """Owner Requirement 2 (successor keying), bank mechanics, design G2.

    A committed mode may now own several successors keyed by distinct
    transition contexts.  ``resolve_for_transition`` fires the successor for a
    given reproducible context; ``resolve_for_source_relation`` re-derives the
    genesis-anchored root successor; and the recall-transition
    ``resolve_unique`` honestly fails closed on a multi-successor mode (the
    fresh-commit self-recall chain cannot disambiguate siblings of the same
    mode at recall time), never returning a wrong successor.
    """

    world = _World()
    mode = world.fact("g2-shared-mode")
    binding_a = _stable_binding(
        world,
        binding_id="g2-successor-a",
        mode_receipt_sha256=mode,
        motif_receipt_sha256=world.fact("g2-motif-a"),
    )
    binding_b = _stable_binding(
        world,
        binding_id="g2-successor-b",
        mode_receipt_sha256=mode,
        motif_receipt_sha256=world.fact("g2-motif-b"),
    )
    # Two successors, SAME mode, genuinely distinct transition contexts.
    assert binding_a.mode_receipt_sha256 == binding_b.mode_receipt_sha256
    assert (
        binding_a.transition_context_match_sha256
        != binding_b.transition_context_match_sha256
    )
    assert (
        binding_a.source_fact_strand_receipt_sha256
        != binding_b.source_fact_strand_receipt_sha256
    )

    bank = _stable_bank(world, (binding_a, binding_b))
    registry = world.registry()

    # resolve_for_transition selects the sibling for THIS reproducible context.
    assert (
        bank.resolve_for_transition(
            mode_receipt_sha256=mode,
            transition_context_match_sha256=binding_a.transition_context_match_sha256,
            receipt_registry=registry,
        ).binding_receipt_sha256
        == binding_a.binding_receipt_sha256
    )
    assert (
        bank.resolve_for_transition(
            mode_receipt_sha256=mode,
            transition_context_match_sha256=binding_b.transition_context_match_sha256,
            receipt_registry=registry,
        ).binding_receipt_sha256
        == binding_b.binding_receipt_sha256
    )

    # resolve_for_source_relation selects the sibling by its source relation.
    assert (
        bank.resolve_for_source_relation(
            mode_receipt_sha256=mode,
            source_fact_strand_receipt_sha256=binding_a.source_fact_strand_receipt_sha256,
            receipt_registry=registry,
        ).binding_receipt_sha256
        == binding_a.binding_receipt_sha256
    )

    # The recall-transition resolver honestly fails closed on a mode that owns
    # several distinct successors (never a wrong successor).
    with pytest.raises(ReceiptError, match="conflicting stable motif bindings"):
        bank.resolve_unique(mode, registry)

    # An unknown transition context is honest fail-closed silence, not a guess.
    with pytest.raises(ReceiptError, match="under this transition context"):
        bank.resolve_for_transition(
            mode_receipt_sha256=mode,
            transition_context_match_sha256=world.fact("g2-unknown-context"),
            receipt_registry=registry,
        )
