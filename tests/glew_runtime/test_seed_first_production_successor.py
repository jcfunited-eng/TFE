"""Real, non-monkeypatched conformance for
``dsf_ai_service.glew_runtime.seed_first_production_successor``.

Every test below drives the same real, already-committed production machinery
the seeder itself drives (``bootstrap_production_clean_conversation_engine``,
the real ``learn_committed_binding_transaction`` first-learn cycle, and the
live engine's OWN ``_persist_checkpoint`` over a real
``ImmutableGenerationStore``). Nothing here monkeypatches bootstrap, recognition,
learning, or persistence; the HMAC keys are real, test-generated random bytes;
the round trip is a genuine second cold-start off disk.
"""

from __future__ import annotations

import secrets

import pytest

from dsf_ai_service.glew_runtime import (
    PRODUCTION_SENSOR_CALIBRATION_UNRATIFIED_v1 as calibration,
)
from dsf_ai_service.glew_runtime.clean_conversation_engine import (
    CleanConversationTurn,
    GenerationIdentityParameters,
)
from dsf_ai_service.glew_runtime.conversation import ConversationStatus
from dsf_ai_service.glew_runtime.conversation_service import (
    clean_conversation_turn_receipt_payload,
)
from dsf_ai_service.glew_runtime.coexperienced_scene_archive import (
    CoexperiencedSceneArchive,
    create_coexperienced_scene_episode,
)
from dsf_ai_service.glew_runtime.expression_learning import (
    CoexperiencedOutput,
    _sensory_receipts,
    create_coexperienced_no_output,
    learn_committed_binding_transaction,
)
from dsf_ai_service.glew_runtime.model import receipt_sha256
from dsf_ai_service.glew_runtime.production_runtime_bootstrap import (
    _merge_registry,
    bootstrap_genesis_learned_binding_state,
    bootstrap_production_clean_conversation_engine,
)
from dsf_ai_service.glew_runtime.seed_first_production_successor import (
    FIRST_SUCCESSOR_RELATION_ID,
    AlreadySeededError,
    seed_first_successor,
)
from dsf_ai_service.glew_runtime.six_lane_runtime_mount import mount_six_lane_runtime
from dsf_ai_service.glew_runtime.story_chemistry import (
    authenticate_production_story_chemistry_profile,
    mount_packaged_production_story_chemistry,
    production_story_chemistry_profile_payload,
)
from dsf_ai_service.substrate.immutable_generation_store import CURRENT_NAME


def _keys() -> tuple[bytes, bytes]:
    # Real, test-generated random HMAC secrets (never the placeholder key ids).
    return secrets.token_bytes(32), secrets.token_bytes(32)


def _cold_start(tmp_path, chemistry_hmac_key: bytes, checkpoint_hmac_key: bytes):
    """A real cold-start / restore through the exact production bootstrap the
    app uses, with the exact same production calibration/identity the seeder
    uses -- so a restore here observes precisely what the live app would."""

    parameters = calibration.production_six_lane_runtime_parameters(
        engine_id=calibration.ENGINE_ID,
        chemistry_authentication_key=chemistry_hmac_key,
        chemistry_key_id=calibration.CHEMISTRY_HMAC_KEY_ID,
    )
    identity = GenerationIdentityParameters(
        genesis_identity=calibration.GENESIS_IDENTITY_UUID,
        genesis_generation_uuid=calibration.GENESIS_GENERATION_UUID,
        genesis_tick=0,
    )
    return bootstrap_production_clean_conversation_engine(
        generation_store_root=tmp_path,
        story_chemistry_authentication_key=chemistry_hmac_key,
        story_chemistry_key_id=calibration.CHEMISTRY_HMAC_KEY_ID,
        six_lane_runtime_parameters=parameters,
        checkpoint_authentication_key=checkpoint_hmac_key,
        checkpoint_key_id=calibration.CHECKPOINT_HMAC_KEY_ID,
        generation_identity=identity,
        engine_id=calibration.ENGINE_ID,
    )


# ---------------------------------------------------------------------------
# (a) seeding succeeds and produces a real non-None initial_event after restore
# ---------------------------------------------------------------------------


def test_seed_first_successor_produces_a_real_initial_event_after_restore(tmp_path):
    chemistry_hmac_key, checkpoint_hmac_key = _keys()

    # Before seeding: a genuine fresh cold-start has never learned anything.
    fresh = _cold_start(tmp_path, chemistry_hmac_key, checkpoint_hmac_key)
    assert fresh._learned_state.initial_event is None
    assert not (tmp_path / CURRENT_NAME).exists()

    # Seed exactly once -- runs its own internal, real, non-mocked round-trip
    # proof before returning (raises if that proof fails).
    seed_first_successor(
        generation_store_root=tmp_path,
        chemistry_hmac_key=chemistry_hmac_key,
        checkpoint_hmac_key=checkpoint_hmac_key,
    )

    # A CURRENT generation now exists on disk.
    assert (tmp_path / CURRENT_NAME).exists()

    # An independent cold-start off that SAME directory (a distinct in-memory
    # engine, a genuine restore) now has a real, non-None initial_event.
    restored_engine = _cold_start(tmp_path, chemistry_hmac_key, checkpoint_hmac_key)
    restored = restored_engine._learned_state
    assert restored.initial_event is not None
    assert restored.initial_event.event_receipt_sha256
    restored.verify()

    # The restored state genuinely reflects the seeded successor: exactly one
    # learned output binding (the "b" scalar) and a non-empty stable bank
    # (LearnedBindingState.verify requires stable_bank <=> initial_event).
    assert len(restored.output_bank.bindings) == 1
    assert restored.stable_bank.bindings


# ---------------------------------------------------------------------------
# (b) running a SECOND time against the same non-empty store fails closed
# ---------------------------------------------------------------------------


def test_seed_first_successor_refuses_to_seed_twice(tmp_path):
    chemistry_hmac_key, checkpoint_hmac_key = _keys()

    seed_first_successor(
        generation_store_root=tmp_path,
        chemistry_hmac_key=chemistry_hmac_key,
        checkpoint_hmac_key=checkpoint_hmac_key,
    )

    # Second run against the now-seeded store must raise loudly, never silently
    # overwrite or duplicate.
    with pytest.raises(AlreadySeededError):
        seed_first_successor(
            generation_store_root=tmp_path,
            chemistry_hmac_key=chemistry_hmac_key,
            checkpoint_hmac_key=checkpoint_hmac_key,
        )

    # And the original seeded generation is still intact and restorable.
    restored_engine = _cold_start(tmp_path, chemistry_hmac_key, checkpoint_hmac_key)
    assert restored_engine._learned_state.initial_event is not None


def test_seed_first_successor_rejects_empty_keys(tmp_path):
    chemistry_hmac_key, checkpoint_hmac_key = _keys()
    with pytest.raises(ValueError):
        seed_first_successor(
            generation_store_root=tmp_path,
            chemistry_hmac_key=b"",
            checkpoint_hmac_key=checkpoint_hmac_key,
        )
    with pytest.raises(ValueError):
        seed_first_successor(
            generation_store_root=tmp_path,
            chemistry_hmac_key=chemistry_hmac_key,
            checkpoint_hmac_key=b"",
        )
    # A rejected pre-flight must not have created a generation.
    assert not (tmp_path / CURRENT_NAME).exists()


def test_first_successor_relation_id_is_engine_scoped():
    # The deterministic relation id is anchored to the production engine id, so
    # a re-run (or the live app) references the same stable identity.
    assert FIRST_SUCCESSOR_RELATION_ID.startswith(calibration.ENGINE_ID)


def _story_chemistry(chemistry_hmac_key: bytes):
    mounted = mount_packaged_production_story_chemistry(
        runtime_authentication_key=chemistry_hmac_key,
        runtime_key_id=calibration.CHEMISTRY_HMAC_KEY_ID,
    )
    return mounted.runtime


def _run_turn(engine, story_chemistry, task_id: str, text: str):
    payload = clean_conversation_turn_receipt_payload(
        task_id=task_id, text=text, source="restart-recall-test"
    )
    turn = CleanConversationTurn(
        task_id=task_id,
        text=text,
        source="restart-recall-test",
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    turn.verify()
    return engine.run_clean_conversation(turn=turn, story_chemistry=story_chemistry)


def test_seeded_successor_resolves_after_restart_and_live_bank_regrowth(tmp_path):
    """The restart-specific stable-binding-resolution fix, proven end-to-end.

    This is the FOURTH-layer sibling of the reproducible-experience-identity
    defects: a request/transport bookkeeping identifier (here, embedded in a
    mode's full ``mode_receipt_sha256``) was given physical authority over a
    decision that should depend only on the mode's physical field content.

    The seeder plants exactly one real learned successor whose stable
    mode/motif binding was keyed on the SEEDED root mode's full receipt.  A
    genuine second cold-start restores that binding, but -- by an already
    disclosed, separate limitation (no ``ExpressionModeBank`` checkpoint exists)
    -- the mode bank is freshly mounted at rank zero and must regrow live.
    Feeding the same 'a'/'b' genesis scalars regrows BRAND-NEW mode objects
    whose full receipts differ from the seed's (different growth-event
    bookkeeping) even though their field-evaluation identity is bit-identical.

    Before the fix, recognising a third 'a' correctly matched the regrown mode
    by field content, but the stable-binding preflight was still keyed on the
    bookkeeping-tainted full receipt, so it failed closed with
    ``receipt_failure:selected mode has no stable motif binding``.  The fix
    keys stable-binding resolution on the mode's content-only field-evaluation
    identity (exact equality, no tolerance), so a legitimately regrown mode
    resolves its stored successor.

    This drives the REAL production seeder + bootstrap restore + live engine --
    no monkeypatching -- and proves the failure is gone.  This fixture seeds an
    EMPTY coexperienced-scene archive, so the turn then honestly lands on the
    separate, pre-existing, documented empty-archive fresh-recall gap (the same
    ``fresh_reentry_UNKNOWN`` state ``test_reproducible_experience_identity``'s
    same-process end-to-end test reaches), never fabricated output.
    """

    chemistry_hmac_key, checkpoint_hmac_key = _keys()
    seed_first_successor(
        generation_store_root=tmp_path,
        chemistry_hmac_key=chemistry_hmac_key,
        checkpoint_hmac_key=checkpoint_hmac_key,
    )

    # A genuine second cold-start off disk: the stable bank is RESTORED (with
    # the seed's own mode receipts) while the ExpressionModeBank is freshly
    # mounted at rank zero and must regrow live.
    engine = _cold_start(tmp_path, chemistry_hmac_key, checkpoint_hmac_key)
    story_chemistry = _story_chemistry(chemistry_hmac_key)

    seeded_binding = engine._learned_state.stable_bank.bindings[0]
    seeded_mode_receipt = seeded_binding.mode_receipt_sha256

    # Regrow the freshly-mounted bank to rank two with the same genesis scalars
    # the seed used (bootstrap-silent growth; no commit yet).
    _run_turn(engine, story_chemistry, "restart-a-1", "a")
    _run_turn(engine, story_chemistry, "restart-b-1", "b")
    assert engine._mode_bank.rank == 2

    # The freshly-regrown mode 0 is the SAME physical field as the seeded mode
    # (identical field-evaluation identity) but a DIFFERENT full receipt --
    # exactly the divergence the fix must bridge.
    regrown_mode = engine._mode_bank.modes[0]
    assert regrown_mode.receipt_sha256 != seeded_mode_receipt
    assert (
        regrown_mode.source_expression.field_evaluation_identity_sha256
        == seeded_binding.mode_field_evaluation_identity_sha256
    )

    # The real test: a third 'a' under a FRESH request id recognises + commits
    # against the regrown mode, reaches the learned genesis initial event, and
    # its stable-motif preflight now RESOLVES (keyed on content identity).
    result = _run_turn(engine, story_chemistry, "restart-a-2-fresh-id", "a")
    result.verify()

    assert result.recognition_receipt_sha256 is not None
    assert result.commit_receipt_sha256 is not None
    assert result.initial_event_receipt_sha256 is not None

    # The fixed defect is GONE: a legitimately regrown mode no longer fails the
    # bookkeeping-tainted receipt lookup.
    assert "no stable motif binding" not in result.reason

    # Only the separate, documented empty-archive fresh-recall gap remains.
    assert result.status is ConversationStatus.EXPLICIT_UNKNOWN_SILENCE
    assert "fresh_reentry_UNKNOWN" in result.reason
    assert "no coexperienced scene" in result.reason
    assert result.silent
    assert result.visible_text == ""


# ---------------------------------------------------------------------------
# The FIFTH-layer investigation: the restart+regrow archive-miss is the empty
# archive, NOT a bookkeeping-vs-content key mismatch -- and what actually gates
# real spoken output. (docs handoff: GL-FIX-RECALL-FIFTH-LAYER-*.)
# ---------------------------------------------------------------------------


def _rederive_production_genesis(chemistry_hmac_key: bytes):
    """Re-derive the deterministic production genesis byte-identically to the
    seeder (same real, non-monkeypatched pipeline), returning the
    ``GenesisBootstrapResult`` so a test can build the exact learned/archived
    shapes a real learn cycle produces."""

    parameters = calibration.production_six_lane_runtime_parameters(
        engine_id=calibration.ENGINE_ID,
        chemistry_authentication_key=chemistry_hmac_key,
        chemistry_key_id=calibration.CHEMISTRY_HMAC_KEY_ID,
    )
    chemistry_envelope = authenticate_production_story_chemistry_profile(
        profile_body_payload=production_story_chemistry_profile_payload(),
        runtime_authentication_key=chemistry_hmac_key,
        runtime_key_id=calibration.CHEMISTRY_HMAC_KEY_ID,
    )
    mounted_runtime = mount_six_lane_runtime(
        story_chemistry_profile_bytes=chemistry_envelope,
        story_chemistry_authentication_key=chemistry_hmac_key,
        story_chemistry_expected_key_id=calibration.CHEMISTRY_HMAC_KEY_ID,
        **parameters.as_mount_kwargs(),
    )
    base_registry = _merge_registry(
        mounted_runtime.story_chemistry_runtime.receipt_registry,
        mounted_runtime.receipt_registry,
    )
    return bootstrap_genesis_learned_binding_state(
        mounted_runtime=mounted_runtime,
        engine_id=calibration.ENGINE_ID,
        chemistry_authentication_key=chemistry_hmac_key,
        chemistry_key_id=calibration.CHEMISTRY_HMAC_KEY_ID,
        typed_language_phase_calibration_id=parameters.typed_language_phase_calibration_id,
        typed_language_phase_kappa=parameters.typed_language_phase_kappa,
        receipt_registry=base_registry,
    )


def _bootstrap_scene_task_id() -> str:
    # ``bootstrap_genesis_learned_binding_state``'s default bootstrap scene id.
    return f"{calibration.ENGINE_ID}-genesis-bootstrap"


def test_restart_regrow_archive_miss_is_the_empty_archive_not_a_key_mismatch(tmp_path):
    """The restart+regrow recall miss is the seed's EMPTY archive, not a
    bookkeeping-vs-content mismatch in the archive resolve KEY.

    The hypothesized "fifth layer" was that ``archive.resolve`` misses because a
    fresh turn's own recomputed ``sensory_evidence_receipt_sha256s`` differ from
    the stored episode's (a bookkeeping-tainted lookup, the sibling of the four
    fixes before it). This test proves that is NOT what happens here: the miss
    occurs against a genuinely EMPTY archive (``seed_first_successor`` persists
    an empty ``CoexperiencedSceneArchive`` -- ``seed_first_production_successor.
    py`` lines under "-- 4. persist ..."), and the regrowth turns 'a'/'b' commit
    nothing (rank-0/rank-1 growth is ``EXPLICIT_NO_COMMIT_SILENCE``), so they
    never learn or archive anything either. There is simply no episode to
    resolve -- a genuinely different, pre-existing limitation, not the receipt
    defect class.

    It then REFUTES the key-mismatch hypothesis directly: the restored
    successor binding's own six-lane sensory receipts ARE a valid, resolvable
    archive key -- the episode a close-capable seed would have archived (built
    from the restored binding + the deterministic bootstrap scene id) resolves
    that exact binding with no key change at all. So the resolve key is not the
    blocker; the archive being empty is.
    """

    chemistry_hmac_key, checkpoint_hmac_key = _keys()
    seed_first_successor(
        generation_store_root=tmp_path,
        chemistry_hmac_key=chemistry_hmac_key,
        checkpoint_hmac_key=checkpoint_hmac_key,
    )
    engine = _cold_start(tmp_path, chemistry_hmac_key, checkpoint_hmac_key)
    story_chemistry = _story_chemistry(chemistry_hmac_key)

    # The seed persisted an EMPTY scene archive -- nothing to recall against.
    assert engine._scene_archive.episodes == ()

    # Regrow the rank-0 bank; both regrowth turns are honest no-commit silence
    # (growth, never a commit), so they archive nothing.
    r_a = _run_turn(engine, story_chemistry, "restart-a-1", "a")
    r_b = _run_turn(engine, story_chemistry, "restart-b-1", "b")
    assert r_a.status is ConversationStatus.EXPLICIT_NO_COMMIT_SILENCE
    assert r_b.status is ConversationStatus.EXPLICIT_NO_COMMIT_SILENCE
    assert engine._mode_bank.rank == 2
    # The archive is STILL empty going into the third 'a' -- the resolve that is
    # about to miss runs against zero stored episodes.
    assert engine._scene_archive.episodes == ()

    result = _run_turn(engine, story_chemistry, "restart-a-2-fresh-id", "a")
    result.verify()
    assert result.status is ConversationStatus.EXPLICIT_UNKNOWN_SILENCE
    assert "no coexperienced scene" in result.reason

    # --- Refute the key-mismatch hypothesis directly -------------------------
    # The restored successor binding's own sensory receipts ARE a resolvable
    # key: the episode a close-capable seed would have persisted (built from the
    # restored binding + the deterministic bootstrap scene id, NO key change)
    # resolves that exact binding. The resolve key was never the blocker.
    restored_binding = engine._learned_state.output_bank.bindings[0]
    assert restored_binding.decoded_scalar() == "b"
    would_be_episode = create_coexperienced_scene_episode(
        profile_binding_sha256=engine._registry.profile_binding_sha256,
        motif_receipt_sha256=restored_binding.motif_receipt_sha256,
        sensory_evidence_receipt_sha256s=(
            restored_binding.sensory_evidence_receipt_sha256s
        ),
        coexperienced_scalar_text="b",
        scene_task_id=_bootstrap_scene_task_id(),
        scene_language_text="b",
        engine_id=calibration.ENGINE_ID,
    )
    populated = CoexperiencedSceneArchive().with_episode(would_be_episode)
    resolved = populated.resolve(
        profile_binding_sha256=restored_binding.profile_binding_sha256,
        sensory_evidence_receipt_sha256s=(
            restored_binding.sensory_evidence_receipt_sha256s
        ),
    )
    assert resolved.episode_receipt_sha256 == would_be_episode.episode_receipt_sha256


def test_production_path_speaks_when_successor_is_archived_and_closed(tmp_path):
    """Definitive end-to-end proof: through the REAL production bootstrap +
    genuine restart off disk + live rank-0 -> rank-2 regrowth, a repeated 'a'
    under a fresh id RELEASES the recalled scalar 'b' -- the actual spoken
    output the whole investigation chain was chasing -- WHEN, and only when, the
    two remaining gates are closed:

      1. the successor scene EPISODE is archived (so recall has something to
         reconstruct), and
      2. the expression is explicitly CLOSED (so ``recall_reentry`` releases
         visible text at exact close -- design section 12's named cognition
         gate).

    Neither gate is the receipt/bookkeeping defect class. This builds exactly
    the closed + archived shape a close-capable seed would persist, using only
    real, non-monkeypatched learning functions (``learn_committed_binding_
    transaction``, ``create_coexperienced_no_output``, ``create_coexperienced_
    scene_episode``), persists it via the engine's own ``_persist_checkpoint``,
    restarts through the real bootstrap, regrows the bank live, and repeats 'a'
    under a fresh id. Crucially, the archive resolves with the UNCHANGED receipt
    key: the archived episode and the learned binding share the deterministic
    genesis scene id, so their six-lane sensory receipts match with no
    content-digest change -- confirming the resolve key was never the blocker.
    """

    chemistry_hmac_key, checkpoint_hmac_key = _keys()

    # Cold-start a genuinely fresh store (initial_event is None).
    engine = _cold_start(tmp_path, chemistry_hmac_key, checkpoint_hmac_key)
    assert engine._learned_state.initial_event is None

    # Build a CLOSED successor (root -> 'b' -> close) + the archived 'b' episode.
    gr = _rederive_production_genesis(chemistry_hmac_key)
    learned = learn_committed_binding_transaction(
        state=gr.genesis,
        committed=gr.bootstrap_committed,
        coexperienced_output=CoexperiencedOutput.from_typed_scalar(
            gr.bootstrap_language
        ),
        prior_relation=gr.initial_relation,
        relation_id=FIRST_SUCCESSOR_RELATION_ID,
        expression_close=False,
        receipt_registry=gr.genesis.receipt_registry,
    )
    no_output, reg_close = create_coexperienced_no_output(
        event_id=f"{calibration.ENGINE_ID}-close-evt",
        sealed=gr.root_committed.sealed,
        source_authority_receipt_sha256=gr.root_committed.commit.receipt_sha256,
        receipt_registry=learned.receipt_registry,
    )
    closed = learn_committed_binding_transaction(
        state=learned,
        committed=gr.root_committed,
        coexperienced_output=CoexperiencedOutput.from_no_output(no_output),
        prior_relation=learned.pending_relation,
        relation_id=f"{calibration.ENGINE_ID}-close-rel",
        expression_close=True,
        receipt_registry=reg_close,
    )
    closed.verify()
    assert closed.terminal and closed.pending_relation is None

    content_binding = learned.output_bank.bindings[0]
    assert content_binding.decoded_scalar() == "b"
    # The archived episode's receipts are exactly the binding's own six-lane
    # receipts (no content-digest change), keyed by the same bootstrap scene id.
    assert content_binding.sensory_evidence_receipt_sha256s == _sensory_receipts(
        gr.bootstrap_committed.sealed
    )
    episode = create_coexperienced_scene_episode(
        profile_binding_sha256=closed.receipt_registry.profile_binding_sha256,
        motif_receipt_sha256=content_binding.motif_receipt_sha256,
        sensory_evidence_receipt_sha256s=(
            content_binding.sensory_evidence_receipt_sha256s
        ),
        coexperienced_scalar_text="b",
        scene_task_id=_bootstrap_scene_task_id(),
        scene_language_text="b",
        engine_id=calibration.ENGINE_ID,
    )
    archive = CoexperiencedSceneArchive().with_episode(episode)

    # Install the closed + archived successor and persist via the engine's OWN
    # real checkpoint path (the same one the live engine uses).
    engine._learned_state = closed
    engine._scene_archive = archive
    engine._live_recall_state.update(
        mode_bank=engine._mode_bank,
        scene_archive=archive,
        motif_kinds=closed.motif_kinds,
    )
    engine._persist_checkpoint()

    # A GENUINE second cold-start off disk (a distinct in-memory engine).
    restarted = _cold_start(tmp_path, chemistry_hmac_key, checkpoint_hmac_key)
    story_chemistry = _story_chemistry(chemistry_hmac_key)
    assert restarted._learned_state.initial_event is not None
    # The scene episode SURVIVED the restart (design section 9's promise, now
    # actually met because the episode was archived).
    assert len(restarted._scene_archive.episodes) == 1
    assert restarted._mode_bank.rank == 0

    # Regrow the rank-0 bank live to rank two with the same genesis scalars.
    _run_turn(restarted, story_chemistry, "restart-a-1", "a")
    _run_turn(restarted, story_chemistry, "restart-b-1", "b")
    assert restarted._mode_bank.rank == 2

    # Repeat 'a' under a genuinely fresh request id -> REAL SPOKEN OUTPUT.
    result = _run_turn(restarted, story_chemistry, "restart-a-2-fresh-id", "a")
    result.verify()
    assert result.status is ConversationStatus.EXPRESSION_RELEASED
    assert result.visible_text == "b"
    assert result.commit_receipt_sha256 is not None
    # Not the bookkeeping gates the four prior fixes removed.
    assert "no coexperienced scene" not in result.reason
    assert "no stable motif binding" not in result.reason
    assert (
        "initial event cites a different full-field commit" not in result.reason
    )
