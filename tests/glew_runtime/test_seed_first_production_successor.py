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
from dsf_ai_service.glew_runtime.model import receipt_sha256
from dsf_ai_service.glew_runtime.production_runtime_bootstrap import (
    bootstrap_production_clean_conversation_engine,
)
from dsf_ai_service.glew_runtime.seed_first_production_successor import (
    FIRST_SUCCESSOR_RELATION_ID,
    AlreadySeededError,
    seed_first_successor,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    mount_packaged_production_story_chemistry,
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
