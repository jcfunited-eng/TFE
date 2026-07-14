from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.commit import (
    closed_experience_seal_receipt_payload,
)
from dsf_ai_service.glew_runtime.fresh_recall_executor import (
    FreshRecallClosedExperienceExecutor,
    create_fresh_recall_archive_lineage,
)
from dsf_ai_service.glew_runtime.fresh_recall_provider import (
    verify_fresh_recall_archive_lineage_authority,
)
from dsf_ai_service.glew_runtime.language import encode_balanced_ternary_scalar
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.output import (
    CommittedMotifEvent,
    MotifBindingBank,
    MotifEventKind,
    MotifOutputBinding,
    OutputActuation,
    OutputBindingKind,
    OutputReason,
    OutputSettlementReceipt,
    OutputStatus,
    RememberedExpressionActuator,
    StageDisposition,
    _output_settlement_receipt_payload,
    committed_motif_event_receipt_payload,
    motif_binding_bank_receipt_payload,
    motif_output_binding_receipt_payload,
)
from tests.glew_runtime.test_recall_story_episode_archive import (
    admitted_archive,
)
from tests.glew_runtime.test_story_global_uf_basin import (
    _mounted_six_lane_preparation,
)


def _extend(registry: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    mounted = {value.digest: value.payload for value in registry.records}
    for payload in payloads:
        digest = receipt_sha256(payload)
        assert mounted.get(digest, payload) == payload
        mounted[digest] = payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(key, mounted[key]) for key in sorted(mounted)),
    )


def _merge(left: ReceiptRegistry, right: ReceiptRegistry) -> ReceiptRegistry:
    assert left.profile_binding_sha256 == right.profile_binding_sha256
    return _extend(left, *(value.payload for value in right.records))


def _binding(episode, profile, registry):
    expression = episode.evidence_preparation_receipt_sha256
    recognition = episode.boundary_receipt_sha256
    closed_payload = closed_experience_seal_receipt_payload(
        experience_id="fresh-recall-lineage-source-experience",
        topology_authority_receipt_sha256=(
            profile.topology.authority_receipt_sha256
        ),
        input_expression_receipt_sha256=expression,
        recognition_receipt_sha256=recognition,
        ordered_evidence_receipt_sha256s=(
            episode.sensory_evidence_receipt_sha256s
        ),
        source_time_start=Fraction(0),
        source_time_end=Fraction(14),
        structural_time_unit="test-structural-time",
    )
    motif_payload = b'{"schema":"glew.test.fresh_recall_lineage_motif.v1"}'
    strand_payload = b'{"schema":"glew.test.fresh_recall_lineage_strand.v1"}'
    output_payload = b'{"schema":"glew.test.fresh_recall_lineage_output.v1"}'
    binding_payload = motif_output_binding_receipt_payload(
        binding_id="fresh-recall-lineage-binding",
        profile_binding_sha256=profile.authority_receipt_sha256,
        motif_receipt_sha256=receipt_sha256(motif_payload),
        closed_experience_receipt_sha256=receipt_sha256(closed_payload),
        fact_strand_receipt_sha256=receipt_sha256(strand_payload),
        sensory_evidence_receipt_sha256s=tuple(
            sorted(episode.sensory_evidence_receipt_sha256s)
        ),
        coexperienced_output_receipt_sha256=receipt_sha256(output_payload),
        kind=OutputBindingKind.LANGUAGE_SCALAR,
        trits=encode_balanced_ternary_scalar(ord("b")),
        language_scalar_cardinality=1,
        no_output_cardinality=0,
    )
    mounted = _extend(
        registry,
        episode.episode_receipt_payload,
        closed_payload,
        motif_payload,
        strand_payload,
        output_payload,
        binding_payload,
    )
    value = MotifOutputBinding(
        "fresh-recall-lineage-binding",
        profile.authority_receipt_sha256,
        receipt_sha256(motif_payload),
        receipt_sha256(closed_payload),
        receipt_sha256(strand_payload),
        tuple(sorted(episode.sensory_evidence_receipt_sha256s)),
        receipt_sha256(output_payload),
        OutputBindingKind.LANGUAGE_SCALAR,
        encode_balanced_ternary_scalar(ord("b")),
        1,
        0,
        receipt_sha256(binding_payload),
    )
    value.verify(mounted)
    return value, mounted


@pytest.fixture(scope="module")
def exact_lineage_case():
    (
        profile,
        _,
        _,
        _,
        _,
        _,
        episode,
        _,
    ) = admitted_archive.__wrapped__()
    preparation, _, _, _, _, _, fresh_registry = (
        _mounted_six_lane_preparation()
    )
    registry = _merge(
        ReceiptRegistry(profile.authority_receipt_sha256, episode.receipt_records),
        fresh_registry,
    )
    binding, registry = _binding(episode, profile, registry)
    base = preparation.contexts[0]
    fresh_sensory = tuple(
        value for value in base.sealed.evidence if value.lane_id != "language"
    )
    lineage, registry = create_fresh_recall_archive_lineage(
        episode=episode,
        source_binding_receipt_sha256=binding.binding_receipt_sha256,
        fresh_closed_experience_receipt_sha256=(
            base.sealed.closed_experience.authority_receipt_sha256
        ),
        fresh_sensory_evidence=fresh_sensory,
        receipt_registry=registry,
    )
    return (
        episode,
        binding,
        fresh_sensory,
        lineage,
        base.sealed.closed_experience.authority_receipt_sha256,
        registry,
    )


def test_provider_accepts_exact_raw_lineage_not_topology_receipt_equality(
    exact_lineage_case,
):
    episode, binding, fresh_sensory, lineage, closed_receipt, registry = (
        exact_lineage_case
    )

    assert tuple(sorted(episode.sensory_evidence_receipt_sha256s)) != tuple(
        sorted(value.evidence_receipt_sha256 for value in fresh_sensory)
    )
    assert len(lineage.entries) == 5
    assert all(
        value.archived_raw_record_sha256 == value.fresh_raw_record_sha256
        for value in lineage.entries
    )

    verify_fresh_recall_archive_lineage_authority(
        episode=episode,
        archive_lineage=lineage,
        fresh_closed_experience_receipt_sha256=closed_receipt,
        fresh_sensory_evidence=fresh_sensory,
        source_binding=binding,
        receipt_registry=registry,
    )


def test_provider_archive_lineage_survives_exact_registry_restart(
    exact_lineage_case,
):
    episode, binding, fresh_sensory, lineage, closed_receipt, registry = (
        exact_lineage_case
    )
    restarted = ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(
            ReceiptRecord(value.digest, bytes(value.payload))
            for value in reversed(registry.records)
        ),
    )

    verify_fresh_recall_archive_lineage_authority(
        episode=episode,
        archive_lineage=lineage,
        fresh_closed_experience_receipt_sha256=closed_receipt,
        fresh_sensory_evidence=fresh_sensory,
        source_binding=binding,
        receipt_registry=restarted,
    )


def test_provider_rejects_omitted_or_substituted_archive_lineage(
    exact_lineage_case,
):
    episode, binding, fresh_sensory, lineage, closed_receipt, registry = (
        exact_lineage_case
    )
    omitted = replace(lineage, entries=lineage.entries[:-1])
    substituted_entry = replace(
        lineage.entries[0],
        fresh_evidence_receipt_sha256=(
            lineage.entries[1].fresh_evidence_receipt_sha256
        ),
    )
    substituted = replace(
        lineage,
        entries=(substituted_entry, *lineage.entries[1:]),
    )

    for changed in (omitted, substituted):
        with pytest.raises(
            ReceiptError,
            match="exact evidence pairings",
        ):
            verify_fresh_recall_archive_lineage_authority(
                episode=episode,
                archive_lineage=changed,
                fresh_closed_experience_receipt_sha256=closed_receipt,
                fresh_sensory_evidence=fresh_sensory,
                source_binding=binding,
                receipt_registry=registry,
            )


def test_archive_lineage_rejects_raw_l0_l4_trace_substitution(
    exact_lineage_case,
):
    episode, binding, fresh_sensory, _, closed_receipt, registry = (
        exact_lineage_case
    )
    changed = replace(
        fresh_sensory[0],
        raw_record=fresh_sensory[1].raw_record,
    )

    with pytest.raises(ReceiptError, match="raw L0-L4 trace"):
        create_fresh_recall_archive_lineage(
            episode=episode,
            source_binding_receipt_sha256=binding.binding_receipt_sha256,
            fresh_closed_experience_receipt_sha256=closed_receipt,
            fresh_sensory_evidence=(changed, *fresh_sensory[1:]),
            receipt_registry=registry,
        )


def test_provider_rejects_missing_lineage_receipt_after_restart(
    exact_lineage_case,
):
    episode, binding, fresh_sensory, lineage, closed_receipt, registry = (
        exact_lineage_case
    )
    restarted_without_lineage = ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(
            value
            for value in registry.records
            if value.digest != lineage.authority_receipt_sha256
        ),
    )

    with pytest.raises(ReceiptError, match="not mounted"):
        verify_fresh_recall_archive_lineage_authority(
            episode=episode,
            archive_lineage=lineage,
            fresh_closed_experience_receipt_sha256=closed_receipt,
            fresh_sensory_evidence=fresh_sensory,
            source_binding=binding,
            receipt_registry=restarted_without_lineage,
        )


# ---------------------------------------------------------------------------
# ``_verify_staged_source`` STAGED_PRIVATE coverage.
#
# Before this test module, NOTHING in the repository exercised
# ``FreshRecallClosedExperienceExecutor._verify_staged_source``'s
# ``STAGED_PRIVATE`` branch at all (confirmed by grep across ``tests/`` and
# ``dsf_ai_service/``). This is exactly the branch that carried the bug fixed
# above: it used to compare ``settlement.binding_receipt_sha256s`` against
# ``(source_binding.binding_receipt_sha256,)``, a value the real
# ``RememberedExpressionActuator._process_verified`` STAGED_PRIVATE branch
# never populates (``output.py``'s own fail-closed contract forbids any
# non-released settlement from exposing it), so the old check failed closed
# on every genuine private-staged recall. The tests below drive a REAL
# ``RememberedExpressionActuator.process()`` call (not a hand-built
# settlement) to prove the corrected check accepts a genuine result, and that
# it still fails closed for a genuine event mismatch and for a
# structurally-legal-per-``output.py``-but-actuator-impossible settlement
# (proving the new ``reason`` check is not dead weight).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def staged_source_case(exact_lineage_case):
    episode, binding, _fresh_sensory, _lineage, _closed_receipt, registry = (
        exact_lineage_case
    )

    placeholder_names = (
        "strand",
        "full_field",
        "field_commit",
        "dominant",
        "l6",
        "source_state",
        "transition",
        "result_state",
    )
    placeholders = {
        name: (
            f'{{"schema":"glew.test.verify_staged_source.{name}.v1"}}'
        ).encode()
        for name in placeholder_names
    }
    registry = _extend(registry, *placeholders.values())

    bank_payload = motif_binding_bank_receipt_payload(
        bank_id="verify-staged-source-bank",
        profile_binding_sha256=binding.profile_binding_sha256,
        bindings=(binding,),
    )
    bank = MotifBindingBank(
        "verify-staged-source-bank",
        binding.profile_binding_sha256,
        (binding,),
        receipt_sha256(bank_payload),
        bank_payload,
    )
    registry = _extend(registry, bank_payload)

    def _build_event(event_id: str) -> tuple[CommittedMotifEvent, ReceiptRegistry]:
        nonlocal registry
        kwargs = dict(
            expression_id="verify-staged-source-expression",
            event_id=event_id,
            event_kind=MotifEventKind.CONTENT,
            profile_binding_sha256=binding.profile_binding_sha256,
            motif_receipt_sha256=binding.motif_receipt_sha256,
            closed_experience_receipt_sha256=(
                binding.closed_experience_receipt_sha256
            ),
            fact_strand_receipt_sha256=receipt_sha256(placeholders["strand"]),
            sensory_evidence_receipt_sha256s=(
                binding.sensory_evidence_receipt_sha256s
            ),
            full_field_state_receipt_sha256=receipt_sha256(
                placeholders["full_field"]
            ),
            full_field_evaluation_identity_sha256=receipt_sha256(
                b"fresh-recall-executor-field-evaluation-identity"
            ),
            field_commit_receipt_sha256=receipt_sha256(
                placeholders["field_commit"]
            ),
            dominant_motif_commit_receipt_sha256=receipt_sha256(
                placeholders["dominant"]
            ),
            corrected_l6_lock_receipt_sha256=receipt_sha256(placeholders["l6"]),
            output_binding_bank_receipt_sha256=bank.bank_receipt_sha256,
            source_state_receipt_sha256=receipt_sha256(
                placeholders["source_state"]
            ),
            transition_edge_receipt_sha256=receipt_sha256(
                placeholders["transition"]
            ),
            result_state_receipt_sha256=receipt_sha256(
                placeholders["result_state"]
            ),
            expression_close_authority_receipt_sha256=None,
        )
        payload = committed_motif_event_receipt_payload(**kwargs)
        built = CommittedMotifEvent(
            **kwargs, event_receipt_sha256=receipt_sha256(payload)
        )
        registry = _extend(registry, payload)
        return built, registry

    event, registry = _build_event("verify-staged-source-event-1")
    other_event, registry = _build_event("verify-staged-source-event-2")
    assert event.event_receipt_sha256 != other_event.event_receipt_sha256

    actuator = RememberedExpressionActuator(
        expression_id="verify-staged-source-expression",
        profile_binding_sha256=binding.profile_binding_sha256,
        initial_state_receipt_sha256=receipt_sha256(
            placeholders["source_state"]
        ),
    )
    staged = actuator.process(
        event=event, binding_bank=bank, receipt_registry=registry
    )
    return episode, binding, event, other_event, staged, registry


def test_verify_staged_source_accepts_genuine_actuator_staged_private_result(
    staged_source_case,
):
    _episode, binding, event, _other_event, staged, registry = staged_source_case

    # Confirms the genuine actuator output is exactly what the fix's
    # reasoning claims: STAGED_PRIVATE with an EMPTY binding_receipt_sha256s
    # (never the tuple the old, buggy check demanded) and the one reason the
    # real actuator ever pairs with STAGED_PRIVATE.
    assert staged.receipt.status is OutputStatus.STAGED_PRIVATE
    assert staged.receipt.reason is OutputReason.UNIQUE_COEXPERIENCED_LANGUAGE_BINDING
    assert staged.receipt.binding_receipt_sha256s == ()

    executor = object.__new__(FreshRecallClosedExperienceExecutor)
    # Must not raise: this is the exact genuine-recall case the old check
    # broke.
    executor._verify_staged_source(
        source_event=event,
        staged_output=staged,
        source_binding=binding,
        receipt_registry=registry,
    )


def test_verify_staged_source_rejects_settlement_for_a_different_event(
    staged_source_case,
):
    _episode, binding, _event, other_event, staged, registry = staged_source_case

    executor = object.__new__(FreshRecallClosedExperienceExecutor)
    with pytest.raises(ReceiptError, match="not exactly private-staged"):
        executor._verify_staged_source(
            source_event=other_event,
            staged_output=staged,
            source_binding=binding,
            receipt_registry=registry,
        )


def test_verify_staged_source_rejects_wrong_reason_for_staged_private(
    staged_source_case,
):
    """Proves the new ``reason`` check is genuinely load-bearing.

    ``output._output_settlement_receipt_payload`` does not itself constrain
    ``reason`` against ``status`` for a non-released settlement -- this
    payload is structurally legal by ``output.py``'s own rules even though
    the real actuator would never produce it (its sole STAGED_PRIVATE call
    site always pairs it with UNIQUE_COEXPERIENCED_LANGUAGE_BINDING).
    """

    _episode, binding, event, _other_event, _staged, registry = staged_source_case

    tampered_kwargs = dict(
        expression_id=event.expression_id,
        event_id=event.event_id,
        event_receipt_sha256=event.event_receipt_sha256,
        source_state_receipt_sha256=event.source_state_receipt_sha256,
        transition_edge_receipt_sha256=event.transition_edge_receipt_sha256,
        result_state_receipt_sha256=event.result_state_receipt_sha256,
        status=OutputStatus.STAGED_PRIVATE,
        reason=OutputReason.COEXPERIENCED_NO_OUTPUT,
        stage_disposition=StageDisposition.RETAINED_PRIVATE,
        visible_text="",
        emitted_scalar_codepoints=(),
        contributing_event_receipt_sha256s=(),
        binding_receipt_sha256s=(),
        failure_detail="",
    )
    tampered_payload = _output_settlement_receipt_payload(**tampered_kwargs)
    tampered_receipt = OutputSettlementReceipt(
        **tampered_kwargs,
        receipt_sha256=receipt_sha256(tampered_payload),
        receipt_payload=tampered_payload,
    )
    tampered_staged = OutputActuation(text="", receipt=tampered_receipt)

    executor = object.__new__(FreshRecallClosedExperienceExecutor)
    with pytest.raises(ReceiptError, match="not exactly private-staged"):
        executor._verify_staged_source(
            source_event=event,
            staged_output=tampered_staged,
            source_binding=binding,
            receipt_registry=registry,
        )
