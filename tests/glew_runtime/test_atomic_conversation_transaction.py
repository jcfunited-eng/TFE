"""Atomic conversation conformance over the fresh-reentry settlement boundary."""

from __future__ import annotations

from dsf_ai_service.glew_runtime import conversation
from dsf_ai_service.glew_runtime.commit import (
    CommitDecision,
    CommitStatus,
    _decision_payload,
)
from dsf_ai_service.glew_runtime.conversation import (
    ConversationCommitProviders,
    ConversationStatus,
    RememberedOutputProviders,
    run_clean_conversation_transaction,
)
from dsf_ai_service.glew_runtime.expression_modes import (
    create_empty_expression_mode_bank,
    evaluate_expression_mode_boundary,
)
from dsf_ai_service.glew_runtime.model import receipt_sha256
from dsf_ai_service.glew_runtime.recall_reentry import (
    CompleteExpressionResult,
    CompleteExpressionStatus,
    _complete_expression_result_payload,
)
from tests.glew_runtime.test_recall_self_sense_reentry import (
    _RealObjectProvider,
    _World,
    _committed_event,
    _output_bank,
    _output_binding,
    _physical_experience,
    _stable_bank,
    _stable_binding,
)


def _mounted_commit(world, recognition, sensory) -> CommitDecision:
    winner = recognition.winner_mode_index
    assert winner is not None
    selected = recognition.pre_growth_bank.modes[winner]
    experience = world.closed_experience("conversation", sensory)
    l6 = world.fact("conversation:l6")
    safe = world.fact("conversation:safe")
    event = world.fact("conversation:event-support")
    global_uf = world.fact("conversation:global-uf")
    evidence = tuple(value.evidence_receipt_sha256 for value in sensory)
    applicability = (world.fact("conversation:applicability"),)
    payload = _decision_payload(
        status=CommitStatus.COMMIT,
        selected_mode_index=winner,
        selected_mode_receipt_sha256=selected.receipt_sha256,
        findings=(),
        topology_receipt=(
            recognition.pre_growth_bank.topology_authority_receipt_sha256
        ),
        experience_receipt=experience,
        expression_recognition_receipt=recognition.receipt_sha256,
        pre_growth_expression_bank_receipt=(
            recognition.pre_growth_bank.receipt_sha256
        ),
        l6_evaluation_receipt=l6,
        safe_mode_receipt=safe,
        event_support_receipt=event,
        global_uf_receipt=global_uf,
        evidence_receipts=evidence,
        applicability_receipts=applicability,
    )
    return CommitDecision(
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
        global_uf_receipt_sha256=global_uf,
        evidence_receipt_sha256s=evidence,
        applicability_receipt_sha256s=applicability,
        receipt_sha256=world.mount(payload),
        receipt_payload=payload,
    )


def _conversation_fixture():
    world = _World()
    first = _physical_experience(world, axis=0)
    second = _physical_experience(world, axis=1)
    registry = world.registry()
    empty = create_empty_expression_mode_bank(
        topology=first.expression.topology,
        precision_authority=first.expression.precision_authority,
        receipt_registry=registry,
    )
    first_growth = evaluate_expression_mode_boundary(
        topology=first.expression.topology,
        bank=empty,
        input_expression=first.expression,
        receipt_registry=registry,
    )
    second_growth = evaluate_expression_mode_boundary(
        topology=first.expression.topology,
        bank=first_growth.post_growth_bank,
        input_expression=second.expression,
        receipt_registry=registry,
    )
    recognition = evaluate_expression_mode_boundary(
        topology=first.expression.topology,
        bank=second_growth.post_growth_bank,
        input_expression=first.expression,
        receipt_registry=registry,
    )
    world.mount(recognition.receipt_payload)
    for mode in recognition.pre_growth_bank.modes:
        world.mount(mode.receipt_payload)
    commit = _mounted_commit(world, recognition, first.sensory_evidence)

    motif = world.fact("conversation:content-motif")
    output_binding = _output_binding(
        world,
        binding_id="conversation-content-binding",
        motif_receipt_sha256=motif,
        scalar="g",
        sensory=first.sensory_evidence,
    )
    output_bank = _output_bank(world, (output_binding,))
    selected = recognition.pre_growth_bank.modes[
        recognition.winner_mode_index
    ]
    stable = _stable_binding(
        world,
        binding_id="conversation-mode-content",
        mode_receipt_sha256=selected.receipt_sha256,
        # Successor resolution keys on the mode's content-only field-evaluation
        # identity (the fixed preflight/recall path), so the binding must carry
        # the real recognized mode's identity, not the synthetic receipt default.
        mode_field_evaluation_identity_sha256=(
            selected.source_expression.field_evaluation_identity_sha256
        ),
        motif_receipt_sha256=motif,
    )
    stable_bank = _stable_bank(world, (stable,))
    initial_event = _committed_event(
        world,
        expression_id="atomic-conversation",
        event_id="atomic-content",
        motif_receipt_sha256=motif,
        sensory=first.sensory_evidence,
        output_bank=output_bank,
        source_state=world.fact("conversation:source-state"),
        edge=world.fact("conversation:edge"),
        result_state=world.fact("conversation:result-state"),
        full_field=first.expression.receipt_sha256,
        # The genesis event stores the CONTENT identity of its full field (the
        # field-evaluation identity), which the fixed preflight compares against
        # the turn's input expression -- so it must be the real identity of the
        # expression recognition ran on, not the synthetic placeholder default.
        full_field_evaluation_identity=(
            first.expression.field_evaluation_identity_sha256
        ),
        field_commit=commit.receipt_sha256,
        dominant_binding=stable.binding_receipt_sha256,
        closed_experience=commit.closed_experience_receipt_sha256,
        l6_lock=commit.l6_evaluation_receipt_sha256,
        # The initial event's Fact Strand is the root binding's own
        # ``source_fact_strand`` (as ``_make_initial_event`` mints it), so
        # ``_verify_initial_event`` resolves exactly this binding.
        fact_strand=stable.source_fact_strand_receipt_sha256,
    )
    provider = _RealObjectProvider(world, ())
    output = RememberedOutputProviders(
        binding_bank=output_bank,
        stable_mode_motif_bank=stable_bank,
        initial_event=initial_event,
        fresh_recall_provider=provider,
    )
    commit_inputs = ConversationCommitProviders(
        l6_evaluation=None,
        l6_scope=None,
        closed_experience=None,
        safe_mode=None,
        event_support=None,
        evidence=(),
        l5_applicability=(),
        global_uf_validation=None,
    )
    return world, first, recognition, commit, output, commit_inputs


def _mount_initial_results(monkeypatch, recognition, commit) -> None:
    monkeypatch.setattr(
        conversation,
        "evaluate_expression_mode_boundary",
        lambda **_: recognition,
    )
    monkeypatch.setattr(
        conversation,
        "evaluate_commit_boundary",
        lambda **_: commit,
    )


def test_atomic_transaction_delegates_complete_release_to_fresh_reentry(
    monkeypatch,
) -> None:
    world, physical, recognition, commit, output, commit_inputs = (
        _conversation_fixture()
    )
    _mount_initial_results(monkeypatch, recognition, commit)
    final_settlement = world.fact("conversation:final-output-settlement")
    transitions = (
        world.fact("conversation:transition:1"),
        world.fact("conversation:transition:2"),
    )
    complete_payload = _complete_expression_result_payload(
        status=CompleteExpressionStatus.RELEASED,
        text="go",
        final_output_settlement_receipt_sha256=final_settlement,
        transition_settlement_receipt_sha256s=transitions,
        missing_operator_id=None,
        reason="fresh full-field re-entry reached exact close",
    )
    complete = CompleteExpressionResult(
        status=CompleteExpressionStatus.RELEASED,
        text="go",
        final_output_settlement_receipt_sha256=final_settlement,
        transition_settlement_receipt_sha256s=transitions,
        missing_operator_id=None,
        reason="fresh full-field re-entry reached exact close",
        receipt_sha256=receipt_sha256(complete_payload),
        receipt_payload=complete_payload,
    )
    calls = []

    def settle(**kwargs):
        calls.append(kwargs)
        return complete

    monkeypatch.setattr(
        conversation,
        "settle_complete_remembered_expression",
        settle,
    )

    result = run_clean_conversation_transaction(
        topology=physical.expression.topology,
        mode_bank=recognition.pre_growth_bank,
        input_expression=physical.expression,
        h_mem_providers=(),
        commit_providers=commit_inputs,
        remembered_output=output,
        receipt_registry=world.registry(),
    )

    assert result.status is ConversationStatus.EXPRESSION_RELEASED
    assert result.visible_text == "go"
    assert result.transition_settlement_receipt_sha256s == transitions
    assert len(calls) == 1
    assert calls[0]["initial_event"] is output.initial_event
    assert calls[0]["provider"] is output.fresh_recall_provider


def test_fresh_reentry_unknown_never_leaks_private_text(monkeypatch) -> None:
    world, physical, recognition, commit, output, commit_inputs = (
        _conversation_fixture()
    )
    _mount_initial_results(monkeypatch, recognition, commit)
    real_settle = conversation.settle_complete_remembered_expression

    def missing_provider(**kwargs):
        return real_settle(**{**kwargs, "provider": None})

    monkeypatch.setattr(
        conversation,
        "settle_complete_remembered_expression",
        missing_provider,
    )

    result = run_clean_conversation_transaction(
        topology=physical.expression.topology,
        mode_bank=recognition.pre_growth_bank,
        input_expression=physical.expression,
        h_mem_providers=(),
        commit_providers=commit_inputs,
        remembered_output=output,
        receipt_registry=world.registry(),
    )

    assert result.status is ConversationStatus.EXPLICIT_UNKNOWN_SILENCE
    assert result.visible_text == ""
    assert result.silent
    assert result.complete_expression_receipt_sha256 is not None
    assert "fresh_reentry_UNKNOWN" in result.reason
