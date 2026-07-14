"""Real tests for ``ProductionRecallReplayIntegrityProvider`` (Step 5).

Every fixture here is genuine, already-established production machinery:
the real archived episode fixture from
``test_recall_story_episode_archive.py::admitted_archive`` and the real
six-lane replay-context preparation from
``test_story_global_uf_basin.py::_mounted_six_lane_preparation`` (the exact
same two fixtures ``test_fresh_recall_executor.py`` already combines).  The
committed motif event / staged output / output binding are built with the
same real, public receipt-payload constructors production code uses
(``output.committed_motif_event_receipt_payload`` /
``output.motif_output_binding_receipt_payload`` / the real
``OutputSettlementReceipt``), following the exact pattern
``test_fresh_recall_executor.py::_binding`` already establishes for a
``MotifOutputBinding`` fixture.

Three scenarios prove the tri-state contract for real:

* genuine, unmodified inputs -> every fact CLEAR, and the result plugs
  cleanly into the real ``safe_mode.evaluate_safe_mode`` gate as PASS;
* a real field substitution (``dataclasses.replace``, per the module
  docstring's honest note on why this -- not a random byte flip -- is the
  only tamper this architecture can manifest) targeting exactly one fact's
  real ground truth -> FAULT for that fact alone, the other two remain
  CLEAR, and ``evaluate_safe_mode`` genuinely fails;
* a receipt genuinely absent from the registry -> UNKNOWN (never a guessed
  CLEAR or FAULT), and ``evaluate_safe_mode`` genuinely reports UNKNOWN.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.commit import AuthorityDisposition
from dsf_ai_service.glew_runtime.fresh_recall_executor import (
    MountedRecallReplayIntegrity,
)
from dsf_ai_service.glew_runtime.global_uf import ReplayKind
from dsf_ai_service.glew_runtime.language import encode_balanced_ternary_scalar
from dsf_ai_service.glew_runtime.model import (
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.output import (
    CommittedMotifEvent,
    MotifEventKind,
    MotifOutputBinding,
    OutputActuation,
    OutputBindingKind,
    OutputReason,
    OutputSettlementReceipt,
    OutputStatus,
    StageDisposition,
    _output_settlement_receipt_payload,
    committed_motif_event_receipt_payload,
    motif_output_binding_receipt_payload,
)
from dsf_ai_service.glew_runtime.recall_replay_integrity_provider import (
    ProductionRecallReplayIntegrityProvider,
)
from dsf_ai_service.glew_runtime.safe_mode import (
    IntegrityFactState,
    evaluate_safe_mode,
)
from tests.glew_runtime.test_recall_story_episode_archive import admitted_archive
from tests.glew_runtime.test_story_global_uf_basin import _mounted_six_lane_preparation


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


def _real_committed_event(
    *, episode, sensory: tuple[str, ...], registry: ReceiptRegistry
) -> tuple[CommittedMotifEvent, ReceiptRegistry]:
    placeholders = {
        name: f'{{"schema":"glew.test.recall_replay_integrity.{name}.v1"}}'.encode()
        for name in (
            "motif",
            "closed",
            "strand",
            "full_field",
            "field_commit",
            "dominant",
            "l6",
            "bank",
            "source_state",
            "transition",
            "result_state",
        )
    }
    kwargs = dict(
        expression_id="recall-replay-integrity-expression",
        event_id="recall-replay-integrity-event",
        event_kind=MotifEventKind.CONTENT,
        profile_binding_sha256=episode.profile_binding_sha256,
        motif_receipt_sha256=receipt_sha256(placeholders["motif"]),
        closed_experience_receipt_sha256=receipt_sha256(placeholders["closed"]),
        fact_strand_receipt_sha256=receipt_sha256(placeholders["strand"]),
        sensory_evidence_receipt_sha256s=sensory,
        full_field_state_receipt_sha256=receipt_sha256(placeholders["full_field"]),
        field_commit_receipt_sha256=receipt_sha256(placeholders["field_commit"]),
        dominant_motif_commit_receipt_sha256=receipt_sha256(placeholders["dominant"]),
        corrected_l6_lock_receipt_sha256=receipt_sha256(placeholders["l6"]),
        output_binding_bank_receipt_sha256=receipt_sha256(placeholders["bank"]),
        source_state_receipt_sha256=receipt_sha256(placeholders["source_state"]),
        transition_edge_receipt_sha256=receipt_sha256(placeholders["transition"]),
        result_state_receipt_sha256=receipt_sha256(placeholders["result_state"]),
        expression_close_authority_receipt_sha256=None,
    )
    event_payload = committed_motif_event_receipt_payload(**kwargs)
    event = CommittedMotifEvent(
        **kwargs,
        event_receipt_sha256=receipt_sha256(event_payload),
    )
    registry = _extend(registry, *placeholders.values(), event_payload)
    return event, registry


def _real_binding(
    *, episode, sensory: tuple[str, ...], registry: ReceiptRegistry
) -> tuple[MotifOutputBinding, ReceiptRegistry]:
    placeholders = {
        name: f'{{"schema":"glew.test.recall_replay_integrity_binding.{name}.v1"}}'.encode()
        for name in ("motif", "closed", "strand", "output")
    }
    binding_kwargs = dict(
        binding_id="recall-replay-integrity-binding",
        profile_binding_sha256=episode.profile_binding_sha256,
        motif_receipt_sha256=receipt_sha256(placeholders["motif"]),
        closed_experience_receipt_sha256=receipt_sha256(placeholders["closed"]),
        fact_strand_receipt_sha256=receipt_sha256(placeholders["strand"]),
        sensory_evidence_receipt_sha256s=sensory,
        coexperienced_output_receipt_sha256=receipt_sha256(placeholders["output"]),
        kind=OutputBindingKind.LANGUAGE_SCALAR,
        trits=encode_balanced_ternary_scalar(ord("b")),
        language_scalar_cardinality=1,
        no_output_cardinality=0,
    )
    binding_payload = motif_output_binding_receipt_payload(**binding_kwargs)
    binding = MotifOutputBinding(
        binding_kwargs["binding_id"],
        binding_kwargs["profile_binding_sha256"],
        binding_kwargs["motif_receipt_sha256"],
        binding_kwargs["closed_experience_receipt_sha256"],
        binding_kwargs["fact_strand_receipt_sha256"],
        binding_kwargs["sensory_evidence_receipt_sha256s"],
        binding_kwargs["coexperienced_output_receipt_sha256"],
        binding_kwargs["kind"],
        binding_kwargs["trits"],
        binding_kwargs["language_scalar_cardinality"],
        binding_kwargs["no_output_cardinality"],
        receipt_sha256(binding_payload),
    )
    registry = _extend(registry, *placeholders.values(), binding_payload)
    return binding, registry


def _real_staged_output(*, event: CommittedMotifEvent) -> OutputActuation:
    settlement_kwargs = dict(
        expression_id=event.expression_id,
        event_id=event.event_id,
        event_receipt_sha256=event.event_receipt_sha256,
        source_state_receipt_sha256=event.source_state_receipt_sha256,
        transition_edge_receipt_sha256=event.transition_edge_receipt_sha256,
        result_state_receipt_sha256=event.result_state_receipt_sha256,
        status=OutputStatus.STAGED_PRIVATE,
        reason=OutputReason.UNIQUE_COEXPERIENCED_LANGUAGE_BINDING,
        stage_disposition=StageDisposition.RETAINED_PRIVATE,
        visible_text="",
        emitted_scalar_codepoints=(),
        contributing_event_receipt_sha256s=(),
        binding_receipt_sha256s=(),
        failure_detail="",
    )
    settlement_payload = _output_settlement_receipt_payload(**settlement_kwargs)
    receipt = OutputSettlementReceipt(
        **settlement_kwargs,
        receipt_sha256=receipt_sha256(settlement_payload),
        receipt_payload=settlement_payload,
    )
    return OutputActuation(text="", receipt=receipt)


@pytest.fixture(scope="module")
def real_scenario():
    (profile, _, _, _, _, _, episode, _archive) = admitted_archive.__wrapped__()
    preparation, _, _, _, _, _, fresh_registry = _mounted_six_lane_preparation()
    registry = _merge(
        ReceiptRegistry(profile.authority_receipt_sha256, episode.receipt_records),
        fresh_registry,
    )
    # ``episode.episode_receipt_payload`` is the episode's own top-level
    # receipt; it is deliberately NOT part of ``episode.receipt_records``
    # (see ``recall_story_episode_archive.create_recall_story_episode``:
    # that tuple is captured from the registry *before* the top-level
    # payload is computed), so real callers -- and this fixture -- must
    # mount it explicitly, exactly as
    # ``test_fresh_recall_executor.py::_binding`` already does.
    registry = _extend(registry, episode.episode_receipt_payload)

    context = next(
        value for value in preparation.contexts if value.request.kind is ReplayKind.BASE
    )
    sensory = tuple(sorted(episode.sensory_evidence_receipt_sha256s))
    event, registry = _real_committed_event(
        episode=episode, sensory=sensory, registry=registry
    )
    binding, registry = _real_binding(
        episode=episode, sensory=sensory, registry=registry
    )
    staged = _real_staged_output(event=event)
    return episode, context, event, staged, binding, registry


def _fact_states(mounted: MountedRecallReplayIntegrity) -> dict[str, IntegrityFactState]:
    return {fact.fact_id: fact.state for fact in mounted.safe_mode_facts}


def _assert_registry_is_append_only(
    before: ReceiptRegistry, after: MountedRecallReplayIntegrity
) -> None:
    assert after.receipt_registry.profile_binding_sha256 == before.profile_binding_sha256
    for record in before.records:
        assert after.receipt_registry.resolve(record.digest) == record.payload


def test_genuine_unmodified_inputs_are_all_clear_and_pass_safe_mode(real_scenario):
    episode, context, event, staged, binding, registry = real_scenario
    provider = ProductionRecallReplayIntegrityProvider()

    mounted = provider.mount_integrity(
        context=context,
        episode=episode,
        source_event=event,
        staged_output=staged,
        source_binding=binding,
        receipt_registry=registry,
    )

    assert isinstance(mounted, MountedRecallReplayIntegrity)
    assert mounted.request_receipt_sha256 == context.request.receipt_sha256
    assert _fact_states(mounted) == {
        "chemistry": IntegrityFactState.CLEAR,
        "field": IntegrityFactState.CLEAR,
        "persistence": IntegrityFactState.CLEAR,
    }
    assert mounted.disruption_clear is True
    _assert_registry_is_append_only(registry, mounted)

    # Every returned authority round-trips through its OWN established
    # verification without raising.
    mounted.safe_mode_scope.verify(
        topology_receipt=context.request.topology_authority_receipt_sha256,
        receipt_registry=mounted.receipt_registry,
    )
    for fact in mounted.safe_mode_facts:
        fact.verify(
            topology_receipt=context.request.topology_authority_receipt_sha256,
            experience_receipt=context.sealed.closed_experience.authority_receipt_sha256,
            receipt_registry=mounted.receipt_registry,
        )

    # This is the real, downstream safety gate this integrity result feeds
    # (fresh_recall_executor.py:742): a genuinely CLEAR result must PASS it.
    safe = evaluate_safe_mode(
        authority_id="test-recall-replay-integrity-safe-mode-clear",
        topology_authority_receipt_sha256=context.request.topology_authority_receipt_sha256,
        closed_experience_receipt_sha256=(
            context.sealed.closed_experience.authority_receipt_sha256
        ),
        scope=mounted.safe_mode_scope,
        facts=mounted.safe_mode_facts,
        receipt_registry=mounted.receipt_registry,
    )
    assert safe.disposition is AuthorityDisposition.PASS


def test_tampered_chemistry_state_faults_only_chemistry(real_scenario):
    episode, context, event, staged, binding, registry = real_scenario
    # A real field substitution: the episode's own POST-window receiver
    # state (a real, valid receipt set from the SAME episode) is swapped in
    # for its PRE-window receiver state. This is the only reachable tamper
    # for a content-addressed dataclass with no self-checking
    # ``__post_init__`` (see module docstring): the object stays
    # structurally legal, but its own top-level receipt now disagrees with
    # what its (unchanged) fields actually recompute to.
    assert (
        episode.pre_window_receiver_state_receipt_sha256s
        != episode.post_window_receiver_state_receipt_sha256s
    )
    tampered_episode = replace(
        episode,
        pre_window_receiver_state_receipt_sha256s=(
            episode.post_window_receiver_state_receipt_sha256s
        ),
    )

    provider = ProductionRecallReplayIntegrityProvider()
    mounted = provider.mount_integrity(
        context=context,
        episode=tampered_episode,
        source_event=event,
        staged_output=staged,
        source_binding=binding,
        receipt_registry=registry,
    )

    states = _fact_states(mounted)
    assert states["chemistry"] is IntegrityFactState.FAULT
    assert states["field"] is IntegrityFactState.CLEAR
    assert states["persistence"] is IntegrityFactState.CLEAR
    assert mounted.disruption_clear is False

    safe = evaluate_safe_mode(
        authority_id="test-recall-replay-integrity-safe-mode-fault",
        topology_authority_receipt_sha256=context.request.topology_authority_receipt_sha256,
        closed_experience_receipt_sha256=(
            context.sealed.closed_experience.authority_receipt_sha256
        ),
        scope=mounted.safe_mode_scope,
        facts=mounted.safe_mode_facts,
        receipt_registry=mounted.receipt_registry,
    )
    assert safe.disposition is AuthorityDisposition.FAIL


def test_swapped_sensory_linkage_faults_only_persistence(real_scenario):
    episode, context, event, staged, binding, registry = real_scenario
    # A real field substitution targeting persistence specifically: the
    # output binding now names a different (but still well-formed, sorted,
    # unique, real-digest-shaped) sensory-evidence receipt set than the
    # episode it is supposedly bound to -- e.g. a caller swapped in a
    # different real episode's sensory receipts while keeping everything
    # else the same.
    substitute_sensory = tuple(
        sorted(
            receipt_sha256(f"glew-test-substitute-sense-{index}".encode())
            for index in range(5)
        )
    )
    assert substitute_sensory != tuple(sorted(binding.sensory_evidence_receipt_sha256s))
    swapped_binding = replace(
        binding, sensory_evidence_receipt_sha256s=substitute_sensory
    )

    provider = ProductionRecallReplayIntegrityProvider()
    mounted = provider.mount_integrity(
        context=context,
        episode=episode,
        source_event=event,
        staged_output=staged,
        source_binding=swapped_binding,
        receipt_registry=registry,
    )

    states = _fact_states(mounted)
    assert states["chemistry"] is IntegrityFactState.CLEAR
    assert states["field"] is IntegrityFactState.CLEAR
    assert states["persistence"] is IntegrityFactState.FAULT
    assert mounted.disruption_clear is False

    safe = evaluate_safe_mode(
        authority_id="test-recall-replay-integrity-safe-mode-fault-persistence",
        topology_authority_receipt_sha256=context.request.topology_authority_receipt_sha256,
        closed_experience_receipt_sha256=(
            context.sealed.closed_experience.authority_receipt_sha256
        ),
        scope=mounted.safe_mode_scope,
        facts=mounted.safe_mode_facts,
        receipt_registry=mounted.receipt_registry,
    )
    assert safe.disposition is AuthorityDisposition.FAIL


def test_tampered_field_expression_linkage_faults_only_field(real_scenario):
    episode, context, event, staged, binding, registry = real_scenario
    # A real field substitution targeting the "field" fact specifically: the
    # sealed closed-experience's own recorded ``recognition_receipt_sha256``
    # is swapped for its (real, valid, but different) input-expression
    # receipt, so the seal's stored linkage no longer matches the
    # independently-produced field expression/recognition this SAME replay
    # context actually computed.
    seal = context.sealed.closed_experience
    assert seal.recognition_receipt_sha256 != seal.input_expression_receipt_sha256
    tampered_seal = replace(
        seal, recognition_receipt_sha256=seal.input_expression_receipt_sha256
    )
    tampered_sealed = replace(context.sealed, closed_experience=tampered_seal)
    tampered_context = replace(context, sealed=tampered_sealed)

    provider = ProductionRecallReplayIntegrityProvider()
    mounted = provider.mount_integrity(
        context=tampered_context,
        episode=episode,
        source_event=event,
        staged_output=staged,
        source_binding=binding,
        receipt_registry=registry,
    )

    states = _fact_states(mounted)
    assert states["chemistry"] is IntegrityFactState.CLEAR
    assert states["field"] is IntegrityFactState.FAULT
    assert states["persistence"] is IntegrityFactState.CLEAR
    assert mounted.disruption_clear is False

    safe = evaluate_safe_mode(
        authority_id="test-recall-replay-integrity-safe-mode-fault-field",
        topology_authority_receipt_sha256=context.request.topology_authority_receipt_sha256,
        closed_experience_receipt_sha256=(
            tampered_context.sealed.closed_experience.authority_receipt_sha256
        ),
        scope=mounted.safe_mode_scope,
        facts=mounted.safe_mode_facts,
        receipt_registry=mounted.receipt_registry,
    )
    assert safe.disposition is AuthorityDisposition.FAIL


def test_missing_episode_receipt_is_unknown_not_a_guess(real_scenario):
    episode, context, event, staged, binding, registry = real_scenario
    # A genuine missing-data case: the episode's own top-level receipt is
    # absent from the active registry (e.g. a restart that failed to
    # rehydrate it). The comparison genuinely cannot be performed, so the
    # real fact must be UNKNOWN -- never a guessed CLEAR or FAULT.
    registry_missing_episode_receipt = ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(
            record
            for record in registry.records
            if record.digest != episode.episode_receipt_sha256
        ),
    )
    assert len(registry_missing_episode_receipt.records) == len(registry.records) - 1

    provider = ProductionRecallReplayIntegrityProvider()
    mounted = provider.mount_integrity(
        context=context,
        episode=episode,
        source_event=event,
        staged_output=staged,
        source_binding=binding,
        receipt_registry=registry_missing_episode_receipt,
    )

    states = _fact_states(mounted)
    assert states["chemistry"] is IntegrityFactState.UNKNOWN
    assert states["persistence"] is IntegrityFactState.UNKNOWN
    assert states["field"] is IntegrityFactState.CLEAR
    assert mounted.disruption_clear is None

    safe = evaluate_safe_mode(
        authority_id="test-recall-replay-integrity-safe-mode-unknown",
        topology_authority_receipt_sha256=context.request.topology_authority_receipt_sha256,
        closed_experience_receipt_sha256=(
            context.sealed.closed_experience.authority_receipt_sha256
        ),
        scope=mounted.safe_mode_scope,
        facts=mounted.safe_mode_facts,
        receipt_registry=mounted.receipt_registry,
    )
    assert safe.disposition is AuthorityDisposition.UNKNOWN


def test_mount_integrity_rejects_untyped_inputs(real_scenario):
    episode, context, event, staged, binding, registry = real_scenario
    provider = ProductionRecallReplayIntegrityProvider()
    with pytest.raises(Exception):
        provider.mount_integrity(
            context=context,
            episode="not-a-real-episode",
            source_event=event,
            staged_output=staged,
            source_binding=binding,
            receipt_registry=registry,
        )
