"""End-to-end proof for GL-SPC-RECALL-BASIN-RECONCILIATION-DESIGN-20260714-v1.

Implements the design's section 11 test plan (T1-T5) against real, non-
monkeypatched objects: real six-lane runtime, real recognition, real commit,
real deterministic scene reconstruction, and the real, unmodified
``recall_reentry`` machinery. Every learned state below is built by driving
the same real ``expression_learning`` transaction functions the existing
fixtures use (including a real ``expression_close=True`` via the committed
precedent ``real_experience_learning_pipeline.close_real_multimodal_
expression``); nothing here monkeypatches recognition, commit, or recall.

WHAT THESE TESTS PROVE, AND ONE HONEST BLOCKER THEY DOCUMENT
-----------------------------------------------------------
The recall-RESOLUTION subsystem this design delivers (design sections 6.1 and
6.2) is fully correct and proven here: for a real learned binding, the
executor deterministically re-runs the engine's own six-lane scene, recognizes
it against the engine's live grown bank, and evaluates a fresh full-field
``SELF_GENERATED_RECALL`` commit with exact-zero ``R_event`` -- and the
regenerated six-lane sensory receipts equal the learned binding's exactly
(the section 6.2 step-7 tripwire), producing a genuinely fresh commit receipt
distinct from the learn-time one.

Emission (releasing the recalled scalar as visible text) is currently BLOCKED
by a real, deeper problem the design did not anticipate -- and which its own
section 13 explicitly predicted would surface here as a red test on the first
run ("Settlement schema mismatch trips inside the unchanged
``RecallTransitionSettlement.verify``"):

    ``recall_reentry.RecallTransitionSettlement.verify`` (recall_reentry.py
    ~714-736) models the recalled expression as referencing EXACTLY ONE
    language evidence record (``language_transport_evidence``, the terminal
    transport) plus the cited senses. But a real scene built by the engine's
    own ``real_experience_learning_pipeline._build_typed_language_lane``
    references one language evidence record PER VALID TRIT PLACE of the
    scalar, and every printable Unicode scalar has 4-5 valid trit places over
    the engine's 5-instant grid. So the settlement's ``MapInject`` subset
    check fails on the 3-4 non-terminal language records, for EVERY real
    scalar. This is not specific to this design's provider: the pre-existing
    five-sense ``FullFieldFreshRecallProvider`` has the identical
    ``max(language)`` / ``sensory = non-language`` structure and hits the same
    wall (and no existing test ever drives a real executor+provider through
    ``settle_complete_remembered_expression`` to a release -- every release
    test uses a hand-built single-language-instant ``_physical_experience``).

Fixing emission requires changing ``recall_reentry.py`` (extending the
settlement to carry every language evidence, not just the terminal), which the
design's section 7.3 explicitly forbids and which lies outside this subsystem.
These tests therefore prove the resolution core and assert the emission
blocker HONESTLY (typed silence with the exact ``recall_reentry`` reason),
rather than forcing a fabricated release.
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction

import pytest

import tests.glew_runtime.test_clean_conversation_engine as CCE
from dsf_ai_service.glew_runtime.clean_conversation_engine import (
    CHECKPOINT_RELATIVE_PATHS,
    GenerationIdentityParameters,
    ProductionCleanConversationEngine,
    _build_commit_providers,
)
from dsf_ai_service.glew_runtime.commit import CommitStatus, evaluate_commit_boundary
from dsf_ai_service.glew_runtime.conversation import ConversationStatus
from dsf_ai_service.glew_runtime.expression_learning import (
    CoexperiencedOutput,
    CommittedCoexperience,
    _sensory_receipts,
    create_coexperienced_no_output,
    create_learned_binding_genesis,
    derive_committed_mode_relation,
    learn_committed_binding_transaction,
)
from dsf_ai_service.glew_runtime.experience_origin import ExperienceOriginKind
from dsf_ai_service.glew_runtime.expression_modes import (
    ExpressionRecognitionStatus,
    evaluate_expression_mode_boundary,
)
from dsf_ai_service.glew_runtime.model import ReceiptError, receipt_sha256
from dsf_ai_service.glew_runtime.output import RememberedExpressionActuator
from dsf_ai_service.glew_runtime.real_experience_learning_pipeline import (
    _commit_real_scene,
    _physical_l6_evaluation,
    _seal,
)
from dsf_ai_service.glew_runtime.recall_reentry import _canonical_source_binding
from dsf_ai_service.glew_runtime.coexperienced_scene_archive import (
    CoexperiencedSceneArchive,
    coexperienced_scene_archive_checkpoint_payload,
    create_coexperienced_scene_episode,
    restore_coexperienced_scene_archive_checkpoint,
)
from dsf_ai_service.glew_runtime.coexperienced_scene_recall_executor import (
    CoexperiencedSceneRecallExecutor,
    CoexperiencedSceneRecallRuntime,
    LiveRecallState,
)
from dsf_ai_service.glew_runtime.coexperienced_scene_recall_provider import (
    CoexperiencedSceneRecallProvider,
)
from dsf_ai_service.glew_runtime.recall_reentry import (
    fresh_recall_provider_authority_receipt_payload,
)

from dsf_ai_service.substrate.immutable_generation_store import ImmutableGenerationStore


_ROOT_TASK = "recall-basin-root"
_CONTENT_TASK = "recall-basin-content"
_GENESIS_IDENTITY = GenerationIdentityParameters(
    genesis_identity="66666666-6666-4666-8666-666666666666",
    genesis_generation_uuid="77777777-7777-8777-8777-777777777777",
    genesis_tick=0,
)


@pytest.fixture(scope="module")
def world():
    """Build a real six-lane runtime grown to rank two, then a real learned +
    explicitly-CLOSED expression: ``root_mode -> content_motif('b')`` and
    ``content_mode -> close_motif`` (via the real ``expression_close=True``
    transaction). Archive the coexperienced content scene. Everything is a
    genuine receipt-verified object driven through the same real Step 1-5
    machinery the committed fixtures use."""

    mr = CCE._build_mounted_runtime()
    rc = CCE._mount_test_chemistry_runtime()
    cc = CCE._mount_test_chemistry_runtime()
    reg = CCE._merge(rc.receipt_registry, mr.receipt_registry)

    re_, rl, rp, reg = CCE._build_scene(
        mounted_runtime=mr, task_id=_ROOT_TASK, text="a", chemistry_runtime=rc, registry=reg
    )
    ce, cl, cp, reg = CCE._build_scene(
        mounted_runtime=mr, task_id=_CONTENT_TASK, text="b", chemistry_runtime=cc, registry=reg
    )

    eb = mr.expression_mode_bank
    g1 = evaluate_expression_mode_boundary(
        topology=mr.field_topology, bank=eb, input_expression=re_, receipt_registry=reg
    )
    reg = CCE._extend(reg, *CCE._mode_payloads(g1))
    g2 = evaluate_expression_mode_boundary(
        topology=mr.field_topology, bank=g1.post_growth_bank, input_expression=ce, receipt_registry=reg
    )
    reg = CCE._extend(reg, *CCE._mode_payloads(g2))
    grown = g2.post_growth_bank
    assert grown.rank == 2

    rr = evaluate_expression_mode_boundary(
        topology=mr.field_topology, bank=grown, input_expression=re_, receipt_registry=reg
    )
    reg = CCE._extend(reg, *CCE._mode_payloads(rr))
    cr = evaluate_expression_mode_boundary(
        topology=mr.field_topology, bank=grown, input_expression=ce, receipt_registry=reg
    )
    reg = CCE._extend(reg, *CCE._mode_payloads(cr))
    assert rr.status is ExpressionRecognitionStatus.RECOGNIZED
    assert cr.status is ExpressionRecognitionStatus.RECOGNIZED

    l6, reg = _physical_l6_evaluation(
        topology=mr.field_topology, pre_window=mr.pre_window_state, registry=reg
    )
    rs, reg = _seal(
        topology=mr.field_topology, preparation=rp, expression=re_, recognition=rr, identity=_ROOT_TASK, registry=reg
    )
    cs, reg = _seal(
        topology=mr.field_topology, preparation=cp, expression=ce, recognition=cr, identity=_CONTENT_TASK, registry=reg
    )

    # Root commit via the engine's own _build_commit_providers (the scene the
    # engine re-commits byte-for-byte on a trigger turn); content commit via
    # the simpler _commit_real_scene (never replayed as initial_event).
    rcp, reg = _build_commit_providers(
        identity=_ROOT_TASK, sealed=rs, topology=mr.field_topology, l6_evaluation=l6, registry=reg
    )
    rcd = evaluate_commit_boundary(
        topology=mr.field_topology, recognition=rr,
        l6_evaluation=rcp.l6_evaluation, l6_scope=rcp.l6_scope, closed_experience=rcp.closed_experience,
        safe_mode=rcp.safe_mode, event_support=rcp.event_support, evidence=rcp.evidence,
        l5_applicability=rcp.l5_applicability, global_uf_validation=rcp.global_uf_validation, receipt_registry=reg,
    )
    assert rcd.status is CommitStatus.COMMIT
    reg = CCE._extend(reg, rcd.receipt_payload)
    root_committed = CommittedCoexperience(rcd, rs, rr.pre_growth_bank.modes[rr.winner_mode_index])
    root_committed.verify(reg)
    content_committed, reg = _commit_real_scene(
        identity=_CONTENT_TASK, sealed=cs, topology=mr.field_topology, l6_evaluation=l6, registry=reg
    )

    init_rel, reg = derive_committed_mode_relation(
        relation_id=f"{_ROOT_TASK}-rel", committed=root_committed,
        output_source_receipt_sha256=root_committed.commit.receipt_sha256, receipt_registry=reg,
    )
    gen = create_learned_binding_genesis(
        state_id="recall-basin-state", expression_id="recall-basin-expr", initial_relation=init_rel, receipt_registry=reg
    )
    learned = learn_committed_binding_transaction(
        state=gen, committed=content_committed,
        coexperienced_output=CoexperiencedOutput.from_typed_scalar(cl),
        prior_relation=init_rel, relation_id=f"{_CONTENT_TASK}-rel",
        expression_close=False, receipt_registry=gen.receipt_registry,
    )
    # Real explicit close (mirrors real_experience_learning_pipeline.
    # close_real_multimodal_expression): content_mode -> close_motif.
    no_output, reg_close = create_coexperienced_no_output(
        event_id="recall-basin-close-evt", sealed=root_committed.sealed,
        source_authority_receipt_sha256=root_committed.commit.receipt_sha256,
        receipt_registry=learned.receipt_registry,
    )
    closed = learn_committed_binding_transaction(
        state=learned, committed=root_committed,
        coexperienced_output=CoexperiencedOutput.from_no_output(no_output),
        prior_relation=learned.pending_relation, relation_id="recall-basin-close-rel",
        expression_close=True, receipt_registry=reg_close,
    )
    assert closed.terminal and closed.pending_relation is None
    assert len(closed.stable_bank.bindings) == 2  # root->content, content->close

    content_binding = closed.output_bank.bindings[0]
    assert content_binding.decoded_scalar() == "b"
    episode = create_coexperienced_scene_episode(
        profile_binding_sha256=closed.receipt_registry.profile_binding_sha256,
        motif_receipt_sha256=content_binding.motif_receipt_sha256,
        sensory_evidence_receipt_sha256s=content_binding.sensory_evidence_receipt_sha256s,
        coexperienced_scalar_text="b", scene_task_id=_CONTENT_TASK, scene_language_text="b",
        engine_id=CCE._ENGINE_ID,
    )
    scene_archive = CoexperiencedSceneArchive().with_episode(episode)

    return {
        "mounted_runtime": mr,
        "grown_bank": grown,
        "empty_bank": eb,
        "l6": l6,
        "learned": learned,
        "closed": closed,
        "episode": episode,
        "scene_archive": scene_archive,
        "content_binding": content_binding,
        "content_committed": content_committed,
        "root_committed": root_committed,
        "root_chemistry": rc,
        "content_sealed": cs,
    }


def _recall_subsystem(world, *, learned_state, scene_archive, mode_bank, base_registry):
    """Build the real recall subsystem (executor + provider) exactly as the
    bootstrap does, sharing one LiveRecallState. Returns (provider, executor,
    live_state, registry-with-provider-authority-mounted)."""

    grown_runtime = dataclasses.replace(world["mounted_runtime"], expression_mode_bank=mode_bank)
    live = LiveRecallState(mode_bank=mode_bank, scene_archive=scene_archive, motif_kinds=learned_state.motif_kinds)
    runtime = CoexperiencedSceneRecallRuntime(
        mounted_runtime=grown_runtime, engine_id=CCE._ENGINE_ID,
        physical_profile_receipt_sha256=receipt_sha256(CCE._engine_physical_profile_payload()),
        typed_language_phase_calibration_id=f"{CCE._ENGINE_ID}-typed-phase",
        typed_language_phase_kappa=Fraction(1, 7),
        chemistry_authentication_key=CCE._CHEM_KEY, chemistry_key_id=CCE._CHEM_KEY_ID,
        l6_evaluation=world["l6"],
    )
    executor = CoexperiencedSceneRecallExecutor(
        executor_id="recall-basin-executor", runtime=runtime, live_recall_state=live
    )
    provider_id = f"{CCE._ENGINE_ID}-recall-basin-provider"
    provider_payload = fresh_recall_provider_authority_receipt_payload(
        provider_id=provider_id, profile_binding_sha256=base_registry.profile_binding_sha256
    )
    registry = CCE._extend(base_registry, provider_payload)
    provider = CoexperiencedSceneRecallProvider(
        provider_id=provider_id, profile_binding_sha256=registry.profile_binding_sha256,
        executor=executor, authority_receipt_sha256=receipt_sha256(provider_payload),
    )
    return provider, executor, live, registry


def _build_engine(world, *, learned_state, scene_archive, mode_bank, generation_store):
    provider, executor, live, registry = _recall_subsystem(
        world, learned_state=learned_state, scene_archive=scene_archive,
        mode_bank=mode_bank, base_registry=learned_state.receipt_registry,
    )
    grown_runtime = dataclasses.replace(world["mounted_runtime"], expression_mode_bank=mode_bank)
    engine = ProductionCleanConversationEngine(
        mounted_runtime=grown_runtime, learned_state=learned_state, receipt_registry=registry,
        fresh_recall_provider=provider,
        typed_language_phase_calibration_id=f"{CCE._ENGINE_ID}-typed-phase",
        typed_language_phase_kappa=Fraction(1, 7),
        generation_identity=_GENESIS_IDENTITY, generation_store=generation_store,
        checkpoint_authentication_key=CCE._CHECKPOINT_KEY, checkpoint_key_id=CCE._CHECKPOINT_KEY_ID,
        coexperienced_scene_archive=scene_archive, live_recall_state=live, engine_id=CCE._ENGINE_ID,
    )
    return engine, provider, executor


def _new_store(tmp_path_factory) -> ImmutableGenerationStore:
    root = tmp_path_factory.mktemp("recall-basin-store")
    return ImmutableGenerationStore(root, identity="recall-basin-identity", required_files=CHECKPOINT_RELATIVE_PATHS)


def _staged(world, learned_state, registry):
    """Run the actuator on the learned initial event to obtain a real
    STAGED_PRIVATE output + its canonical source binding (the real inputs the
    executor consumes), without any monkeypatching."""

    initial = learned_state.initial_event
    actuator = RememberedExpressionActuator(
        expression_id=initial.expression_id, profile_binding_sha256=registry.profile_binding_sha256,
        initial_state_receipt_sha256=initial.source_state_receipt_sha256,
    )
    output = actuator.process(event=initial, binding_bank=learned_state.output_bank, receipt_registry=registry)
    source_binding = _canonical_source_binding(initial, learned_state.output_bank)
    return initial, output, source_binding


# ---------------------------------------------------------------------------
# T1 -- learn then recall within one engine (the headline test)
# ---------------------------------------------------------------------------


def test_T1_recall_resolution_produces_a_fresh_full_field_self_recall_commit(world):
    """T1 (resolution half, fully proven): the real executor deterministically
    re-runs the learned coexperienced scene, recognizes it against the engine's
    live grown bank, and evaluates a fresh full-field SELF_GENERATED_RECALL
    commit whose regenerated six-lane sensory receipts equal the learned
    binding's exactly -- and whose commit receipt is DISTINCT from the
    learn-time commit (a genuine re-commit, not a replayed value)."""

    provider, executor, live, registry = _recall_subsystem(
        world, learned_state=world["closed"], scene_archive=world["scene_archive"],
        mode_bank=world["grown_bank"], base_registry=world["closed"].receipt_registry,
    )
    initial, output, source_binding = _staged(world, world["closed"], registry)

    execution = executor.execute(
        source_event=initial, staged_output=output, source_binding=source_binding, receipt_registry=registry,
    )
    execution.verify(registry)

    # Recognized against the live grown bank (design section 3.4 / 5).
    assert execution.recognition.status is ExpressionRecognitionStatus.RECOGNIZED
    assert execution.recognition.winner_mode_index is not None
    # Self-generated recall origin (exact-zero fresh R_event is enforced inside
    # the executor: it raises unless event_support.exact_r_event == 0).
    assert execution.experience_origin.kind is ExperienceOriginKind.SELF_GENERATED_RECALL
    # A genuine full-field commit.
    assert execution.commit_decision.status is CommitStatus.COMMIT
    # The section 6.2 step-7 tripwire holds by construction: the regenerated
    # six-lane sensory receipts equal the exact receipts the learned binding
    # carries -- documenting bit-exact deterministic reconstruction.
    regenerated = tuple(sorted(v.evidence_receipt_sha256 for v in execution.sensory_evidence))
    assert regenerated == source_binding.sensory_evidence_receipt_sha256s
    # Fresh re-commit, not a replay: distinct from the content scene's
    # learn-time commit (the live bank has grown; the recall origin differs).
    assert execution.commit_decision.receipt_sha256 != world["content_committed"].commit.receipt_sha256


def test_T1_emission_is_currently_blocked_by_the_recall_reentry_language_multiplicity(world, tmp_path_factory):
    """T1 (emission half, HONEST blocker -- see module docstring): driving the
    full engine turn over the closed, archived expression reconstructs and
    re-commits the scene correctly, but ``recall_reentry.RecallTransition
    Settlement.verify`` rejects the settlement because the real reconstructed
    expression references one language evidence record per valid trit place
    (4-5 for every printable scalar), while that verifier accepts only the
    single terminal language transport. The turn therefore yields typed
    silence -- never a fabricated scalar -- with the exact recall_reentry
    reason. This is the design's own section 13 tripwire #3 firing as
    predicted, and it also blocks the pre-existing five-sense provider."""

    store = _new_store(tmp_path_factory)
    engine, provider, executor = _build_engine(
        world, learned_state=world["closed"], scene_archive=world["scene_archive"],
        mode_bank=world["grown_bank"], generation_store=store,
    )
    # Trigger turn reconstructs the ROOT scene (the initial event is anchored
    # to the genesis root relation, so conversation._preflight_initial_output
    # requires the trigger commit to equal the root's).
    turn = CCE._turn(_ROOT_TASK, "a")
    result = engine.run_clean_conversation(turn=turn, story_chemistry=world["root_chemistry"])
    result.verify()

    assert result.status is not ConversationStatus.EXPRESSION_RELEASED
    assert result.visible_text == ""  # honest typed silence, never a fabricated scalar
    # The commit genuinely happened (recognition + commit are real); the recall
    # settlement is what fails, inside the unchanged recall_reentry verifier.
    assert result.commit_receipt_sha256 is not None
    assert "MapInject" in result.reason or "language plus cited senses" in result.reason


# ---------------------------------------------------------------------------
# T2 -- recall miss is honest silence
# ---------------------------------------------------------------------------


def test_T2_recall_miss_is_honest_typed_silence(world, tmp_path_factory):
    """T2: a scene with no archived episode yields typed silence -- the
    executor's ``archive.resolve`` raises and the turn is silent, never
    gibberish and never a fabricated scalar."""

    store = _new_store(tmp_path_factory)
    empty_archive = CoexperiencedSceneArchive()
    engine, provider, executor = _build_engine(
        world, learned_state=world["closed"], scene_archive=empty_archive,
        mode_bank=world["grown_bank"], generation_store=store,
    )
    # Direct proof: archive.resolve raises inside the executor for the real
    # staged source binding.
    initial, output, source_binding = _staged(world, world["closed"], engine._registry)
    with pytest.raises(ReceiptError, match="no coexperienced scene has this exact"):
        executor.execute(
            source_event=initial, staged_output=output, source_binding=source_binding,
            receipt_registry=engine._registry,
        )
    # End-to-end: the turn commits but recall misses -> honest typed silence.
    turn = CCE._turn(_ROOT_TASK, "a")
    result = engine.run_clean_conversation(turn=turn, story_chemistry=world["root_chemistry"])
    result.verify()
    assert result.status is not ConversationStatus.EXPRESSION_RELEASED
    assert result.visible_text == ""


# ---------------------------------------------------------------------------
# T3 -- determinism / tamper tripwire
# ---------------------------------------------------------------------------


def test_T3_deterministic_reconstruction_and_tamper_tripwires(world):
    """T3: re-running the executor for the same episode twice produces
    byte-identical sealed/commit receipts; and mutating a reconstruction input
    fails closed at a deterministic tripwire rather than silently emitting a
    different scene."""

    provider, executor, live, registry = _recall_subsystem(
        world, learned_state=world["closed"], scene_archive=world["scene_archive"],
        mode_bank=world["grown_bank"], base_registry=world["closed"].receipt_registry,
    )
    initial, output, source_binding = _staged(world, world["closed"], registry)

    first = executor.execute(source_event=initial, staged_output=output, source_binding=source_binding, receipt_registry=registry)
    second = executor.execute(source_event=initial, staged_output=output, source_binding=source_binding, receipt_registry=registry)
    assert first.sealed.closed_experience.authority_receipt_sha256 == second.sealed.closed_experience.authority_receipt_sha256
    assert first.commit_decision.receipt_sha256 == second.commit_decision.receipt_sha256
    assert tuple(v.evidence_receipt_sha256 for v in first.sensory_evidence) == tuple(
        v.evidence_receipt_sha256 for v in second.sensory_evidence
    )

    # Tamper A -- a poisoned episode carrying the binding's receipt key but a
    # WRONG scene_task_id reconstructs a different scene: the section 6.2
    # step-7 receipt-equality assertion fails closed.
    poisoned_episode = create_coexperienced_scene_episode(
        profile_binding_sha256=registry.profile_binding_sha256,
        motif_receipt_sha256=world["content_binding"].motif_receipt_sha256,
        sensory_evidence_receipt_sha256s=world["content_binding"].sensory_evidence_receipt_sha256s,
        coexperienced_scalar_text="a", scene_task_id=_ROOT_TASK, scene_language_text="a",
        engine_id=CCE._ENGINE_ID,
    )
    poisoned_archive = CoexperiencedSceneArchive().with_episode(poisoned_episode)
    _, poisoned_executor, _, poisoned_reg = _recall_subsystem(
        world, learned_state=world["closed"], scene_archive=poisoned_archive,
        mode_bank=world["grown_bank"], base_registry=world["closed"].receipt_registry,
    )
    p_initial, p_output, p_source = _staged(world, world["closed"], poisoned_reg)
    with pytest.raises(ReceiptError, match="reconstruction drifted"):
        poisoned_executor.execute(
            source_event=p_initial, staged_output=p_output, source_binding=p_source, receipt_registry=poisoned_reg,
        )

    # Tamper B -- mutating the physical-profile receipt in the recall runtime
    # ALSO fails closed, though at a different deterministic tripwire than the
    # design named: the mutated receipt is not mounted in the active registry,
    # so ``_build_expression``'s evolution-authority check rejects it. (The
    # physical profile does not feed the sensory receipts, so step 7 does not
    # fire for it; the substrate fails closed anyway. Documented finding.)
    bad_runtime = dataclasses.replace(
        executor._runtime, physical_profile_receipt_sha256=receipt_sha256(b"recall-basin-tampered-profile"),
    )
    bad_executor = CoexperiencedSceneRecallExecutor(
        executor_id="recall-basin-bad", runtime=bad_runtime, live_recall_state=live,
    )
    with pytest.raises(ReceiptError):
        bad_executor.execute(source_event=initial, staged_output=output, source_binding=source_binding, receipt_registry=registry)


# ---------------------------------------------------------------------------
# T4 -- archive checkpoint round-trip
# ---------------------------------------------------------------------------


def test_T4_archive_checkpoint_round_trip(world):
    """T4: checkpoint the scene archive, restore it from bytes, and confirm the
    restored episode resolves identically (byte-equal episode receipt)."""

    archive = world["scene_archive"]
    payload = coexperienced_scene_archive_checkpoint_payload(
        archive=archive, checkpoint_id="recall-basin-checkpoint-0",
        authentication_key=CCE._CHECKPOINT_KEY, key_id=CCE._CHECKPOINT_KEY_ID,
    )
    restored = restore_coexperienced_scene_archive_checkpoint(
        checkpoint_payload=payload, authentication_key=CCE._CHECKPOINT_KEY, expected_key_id=CCE._CHECKPOINT_KEY_ID,
    )
    assert restored.receipt_sha256 == archive.receipt_sha256
    binding = world["content_binding"]
    resolved = restored.resolve(
        profile_binding_sha256=binding.profile_binding_sha256,
        sensory_evidence_receipt_sha256s=binding.sensory_evidence_receipt_sha256s,
    )
    assert resolved.episode_receipt_sha256 == world["episode"].episode_receipt_sha256
    assert resolved.episode_receipt_payload == world["episode"].episode_receipt_payload

    # Tampering the signed checkpoint bytes fails closed.
    with pytest.raises(ReceiptError):
        restore_coexperienced_scene_archive_checkpoint(
            checkpoint_payload=payload, authentication_key=b"a-different-key", expected_key_id=CCE._CHECKPOINT_KEY_ID,
        )


# ---------------------------------------------------------------------------
# T5 -- restart bound (documents design section 9)
# ---------------------------------------------------------------------------


def test_T5_cross_restart_recall_is_bounded_to_honest_silence(world, tmp_path_factory):
    """T5: after a restart the mode bank remounts at rank zero (design section
    9). The restored, byte-real closed learned state and scene archive survive,
    but a rank-zero bank cannot recognize the trigger scene, so recall is inert
    and the turn is honest typed silence (not an error) -- the single remaining
    gate on cross-restart recall, with an explicit test a future mode-bank
    restore change can flip."""

    store = _new_store(tmp_path_factory)
    engine, provider, executor = _build_engine(
        world, learned_state=world["closed"], scene_archive=world["scene_archive"],
        mode_bank=world["empty_bank"], generation_store=store,
    )
    turn = CCE._turn(_ROOT_TASK, "a")
    result = engine.run_clean_conversation(turn=turn, story_chemistry=world["root_chemistry"])
    result.verify()
    assert result.status is not ConversationStatus.EXPRESSION_RELEASED
    assert result.visible_text == ""
    # No commit fires against a rank-zero bank, so recall never even attempts.
    assert result.commit_receipt_sha256 is None
