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
    GenerationIdentityParameters,
)
from dsf_ai_service.glew_runtime.production_runtime_bootstrap import (
    bootstrap_production_clean_conversation_engine,
)
from dsf_ai_service.glew_runtime.seed_first_production_successor import (
    FIRST_SUCCESSOR_RELATION_ID,
    AlreadySeededError,
    seed_first_successor,
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
