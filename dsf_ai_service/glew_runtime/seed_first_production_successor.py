"""One-time seeder: plant the first real learned successor into the live
``ProductionCleanConversationEngine`` generation store BEFORE the
``GLEW_CONVERSATION_ENGINE_ENABLED`` flag is ever turned on.

    ================================================================
    WHY THIS SCRIPT EXISTS -- READ THIS FIRST
    ================================================================

``dsf_ai_service/glew_runtime/production_runtime_bootstrap.py``'s real
cold-start (``bootstrap_production_clean_conversation_engine``) lives two real,
mutually independent genesis scenes through the real six-lane pipeline to grow
the mode bank to rank two and seed a genuinely honest fresh-genesis
``LearnedBindingState`` -- but that state's ``initial_event`` is ALWAYS ``None``
after bootstrap (by design: nothing beyond the genesis root relation is ever
learned inside bootstrap itself).

The live conversational entry point ``run_clean_conversation`` /
``_run_locked`` returns typed silence *immediately* whenever
``initial_event is None`` -- BEFORE any commit or learn is ever attempted (see
``clean_conversation_engine.py`` around the ``self._learned_state.initial_event
is None`` guard). So a fresh cold-start engine can never learn its own first
successor through the live path: it is a genuine, confirmed chicken-and-egg
gap. The engine can only learn on live turns once it *already* has a non-None
``initial_event``.

Someone must therefore seed exactly one real first learned successor into the
store, once, before the flag is turned on. This script does exactly that, and
nothing more. It is a ONE-TIME operation and fails closed if run against an
already-seeded store (it never overwrites or duplicates an existing
generation).

    ================================================================
    WHAT IS AND IS NOT FABRICATED
    ================================================================

Nothing here is fabricated. This runs the same real, proven Step-4
first-learn-cycle mechanism ``real_experience_learning_pipeline`` uses
(``expression_learning.learn_committed_binding_transaction``) on top of a real,
bootstrapped ``LearnedBindingState``, producing a real, receipt-verified,
non-None first ``CommittedMotifEvent``. The persistence is the exact same
``ImmutableGenerationStore.commit(...)`` the live engine's own
``_persist_checkpoint`` uses -- this script literally calls that method rather
than reimplementing it. The round trip (persist, then a genuine second
cold-start restore off disk) is proven for real, on every run, before the
script reports success -- never mocked, never monkeypatched.

    ================================================================
    THE SPECIFIC COEXPERIENCED SCALAR CHOSEN (documented plainly)
    ================================================================

The bootstrap already lives two real genesis scenes with arbitrary-but-real
technical bootstrap content: a root scene whose single Unicode scalar is
``production_runtime_bootstrap.DEFAULT_GENESIS_ROOT_TEXT`` (``"a"``) and a
second "bootstrap" scene whose single scalar is
``DEFAULT_GENESIS_BOOTSTRAP_TEXT`` (``"b"``). This seeder learns the FIRST real
successor as exactly that already-lived second genesis scene: it maps the root
scene's committed mode -> the ``"b"`` scene's real coexperienced typed scalar
(via the genesis bootstrap's own ``bootstrap_committed`` /
``bootstrap_language`` / ``initial_relation``). It invents no new third scene.

That the specific scalar is ``"b"`` is an arbitrary technical bootstrapping
choice, exactly analogous to (and reusing) the arbitrary-but-real ``"a"`` /
``"b"`` scenes ``production_runtime_bootstrap.py`` already uses for genesis.
This is purely a mechanism-priming step to close the chicken-and-egg gap -- it
is deliberately NOT a meaningful "first word" or teaching moment, and must not
be dressed up as one. It just makes ``initial_event`` non-None with real,
byte-verified content so the live engine can learn everything afterward on real
turns.

This mirrors, one-for-one, the already-proven template
``tests/glew_runtime/test_production_runtime_bootstrap.py::
test_restore_round_trip_matches_persisted_learned_state`` -- the same genesis
derivation, the same ``learn_committed_binding_transaction`` call over the
bootstrap scene, and the same store-commit-then-cold-start-restore round trip.

    ================================================================
    HOW A HUMAN OPERATOR RUNS THIS FOR REAL (later, not here)
    ================================================================

This script is built and locally proven here; it is NOT run against real
production by this task. A human operator will later run it via ``ECS Exec``
into the live container, with the real production secrets already present in
the environment (the same two env vars the app itself reads):

    GLEW_CHEMISTRY_HMAC_KEY   -- from AWS Secrets Manager
    GLEW_CHECKPOINT_HMAC_KEY  -- from AWS Secrets Manager

and the store root resolved exactly as the app resolves it
(``resolve_default_generation_store_root()`` -- reads
``GLEW_CONVERSATION_ENGINE_STORE_ROOT`` or derives a sibling of ``STATE_DIR``),
optionally overridden by a single explicit CLI path argument. The final line of
output is unambiguous:

    SEED_RESULT=SUCCESS ...        (exit 0)
    SEED_RESULT=FAILURE: <reason>  (exit 1)

Only after this prints ``SEED_RESULT=SUCCESS`` should ``GLEW_CONVERSATION_
ENGINE_ENABLED`` ever be turned on.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dsf_ai_service.glew_runtime import (
    PRODUCTION_SENSOR_CALIBRATION_UNRATIFIED_v1 as calibration,
)
from dsf_ai_service.glew_runtime.clean_conversation_engine import (
    GenerationIdentityParameters,
)
from dsf_ai_service.glew_runtime.expression_learning import (
    CoexperiencedOutput,
    learn_committed_binding_transaction,
)
from dsf_ai_service.glew_runtime.production_runtime_bootstrap import (
    _merge_registry,
    bootstrap_genesis_learned_binding_state,
    bootstrap_production_clean_conversation_engine,
    resolve_default_generation_store_root,
)
from dsf_ai_service.glew_runtime.six_lane_runtime_mount import mount_six_lane_runtime
from dsf_ai_service.glew_runtime.story_chemistry import (
    authenticate_production_story_chemistry_profile,
    production_story_chemistry_profile_payload,
)
from dsf_ai_service.substrate.immutable_generation_store import CURRENT_NAME


# Matches dsf_ai_service/app.py's GLEW_CHEMISTRY_HMAC_KEY_ENV /
# GLEW_CHECKPOINT_HMAC_KEY_ENV exactly (the two runtime HMAC secrets the live
# app reads from AWS Secrets Manager at startup). Kept as local constants so
# importing this script pulls in no app.py startup side effects.
GLEW_CHEMISTRY_HMAC_KEY_ENV = "GLEW_CHEMISTRY_HMAC_KEY"
GLEW_CHECKPOINT_HMAC_KEY_ENV = "GLEW_CHECKPOINT_HMAC_KEY"

# The deterministic relation id for the single first-successor learn cycle.
# Arbitrary-but-fixed technical id, in the same spirit as the bootstrap's own
# ``{root_scene_id}-initial-relation``.
FIRST_SUCCESSOR_RELATION_ID = f"{calibration.ENGINE_ID}-first-production-successor-relation"


class AlreadySeededError(RuntimeError):
    """Raised when the target store already contains a real learned successor.

    Seeding is a ONE-TIME operation. This is a hard, fail-closed refusal: the
    seeder must never overwrite or duplicate an already-seeded generation.
    """


def _production_parameters_and_identity(
    *, chemistry_hmac_key: bytes
) -> tuple[object, GenerationIdentityParameters]:
    """Build the six-lane runtime parameters and genesis identity triple
    BYTE-IDENTICALLY to ``dsf_ai_service/app.py::_boot_glew_conversation_engine``
    -- same ``ENGINE_ID``, same ``GENESIS_IDENTITY_UUID`` /
    ``GENESIS_GENERATION_UUID`` from the calibration module, same chemistry key
    id. If these diverge, the seeded generation would not restore when the real
    app boots with the flag on."""

    if getattr(calibration, "STATUS", None) != "unratified_placeholder":
        raise RuntimeError(
            "GLEW sensor calibration module lost its unratified_placeholder marker"
        )

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
    return parameters, identity


def _cold_start(
    *,
    generation_store_root: Path,
    chemistry_hmac_key: bytes,
    checkpoint_hmac_key: bytes,
    parameters,
    identity: GenerationIdentityParameters,
):
    """Real cold-start / restore through the exact production bootstrap the app
    uses. Against an empty store this yields a fresh-genesis engine
    (``initial_event is None``); against an already-seeded store it restores
    (``initial_event is not None``)."""

    return bootstrap_production_clean_conversation_engine(
        generation_store_root=generation_store_root,
        story_chemistry_authentication_key=chemistry_hmac_key,
        story_chemistry_key_id=calibration.CHEMISTRY_HMAC_KEY_ID,
        six_lane_runtime_parameters=parameters,
        checkpoint_authentication_key=checkpoint_hmac_key,
        checkpoint_key_id=calibration.CHECKPOINT_HMAC_KEY_ID,
        generation_identity=identity,
        engine_id=calibration.ENGINE_ID,
    )


def _learn_first_successor(*, chemistry_hmac_key: bytes, parameters):
    """Re-derive the real genesis bootstrap deterministically (identical to
    what the cold-start engine already holds -- byte-checked by the caller),
    then learn exactly one real successor over the already-lived second genesis
    scene (the ``"b"`` scalar) via the same real
    ``learn_committed_binding_transaction`` mechanism
    ``real_experience_learning_pipeline`` uses.

    ``bootstrap_production_clean_conversation_engine`` discards the intermediate
    ``GenesisBootstrapResult`` (it keeps only the finished genesis state), so
    the ``bootstrap_committed`` / ``bootstrap_language`` / ``initial_relation``
    needed to learn a successor are not reachable through the engine object.
    The genesis pipeline is fully deterministic, so re-deriving it here yields a
    byte-identical genesis -- the caller asserts that identity before persisting.
    """

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
    genesis_result = bootstrap_genesis_learned_binding_state(
        mounted_runtime=mounted_runtime,
        engine_id=calibration.ENGINE_ID,
        chemistry_authentication_key=chemistry_hmac_key,
        chemistry_key_id=calibration.CHEMISTRY_HMAC_KEY_ID,
        typed_language_phase_calibration_id=parameters.typed_language_phase_calibration_id,
        typed_language_phase_kappa=parameters.typed_language_phase_kappa,
        receipt_registry=base_registry,
    )
    if genesis_result.genesis.initial_event is not None:
        raise RuntimeError(
            "genesis bootstrap unexpectedly produced a non-None initial_event"
        )

    learned = learn_committed_binding_transaction(
        state=genesis_result.genesis,
        committed=genesis_result.bootstrap_committed,
        coexperienced_output=CoexperiencedOutput.from_typed_scalar(
            genesis_result.bootstrap_language
        ),
        prior_relation=genesis_result.initial_relation,
        relation_id=FIRST_SUCCESSOR_RELATION_ID,
        expression_close=False,
        receipt_registry=genesis_result.genesis.receipt_registry,
    )
    if learned.initial_event is None:
        raise RuntimeError(
            "first-successor learn cycle did not produce a real initial_event"
        )
    learned.verify()
    return genesis_result, learned


def seed_first_successor(
    *,
    generation_store_root: Path,
    chemistry_hmac_key: bytes,
    checkpoint_hmac_key: bytes,
) -> None:
    """Seed exactly one real first learned successor into the generation store
    at ``generation_store_root`` -- the one-time operation that closes the
    fresh-cold-start chicken-and-egg gap before the engine flag is turned on.

    Fails closed (raises :class:`AlreadySeededError`) if the store already
    holds a learned successor; never overwrites or duplicates.

    Steps (each proven real, none mocked):

    1. Cold-start through the exact production bootstrap the app uses.
    2. Confirm the fresh-genesis engine's ``initial_event is None`` (refuse
       loudly otherwise -- that means the store is already seeded).
    3. Learn one real successor (the ``"b"`` genesis scalar) via the real
       ``learn_committed_binding_transaction`` mechanism.
    4. Persist via the live engine's OWN ``_persist_checkpoint`` -- the same
       real ``ImmutableGenerationStore.commit(...)`` the running engine uses,
       not a reimplementation.
    5. Cold-start AGAIN off disk (a genuine restore, a distinct in-memory
       object) and assert the restored ``initial_event`` is non-None and
       byte-matches what was just persisted.
    """

    if not isinstance(chemistry_hmac_key, bytes) or not chemistry_hmac_key:
        raise ValueError("chemistry_hmac_key must be non-empty bytes")
    if not isinstance(checkpoint_hmac_key, bytes) or not checkpoint_hmac_key:
        raise ValueError("checkpoint_hmac_key must be non-empty bytes")

    generation_store_root = Path(generation_store_root)

    # Fast, explicit fail-closed pre-check: a real prior generation already
    # exists here. Refuse before doing any expensive genesis work. (The engine
    # guard in step 2 is the authoritative check; this is a clearer early
    # refusal that matches the store's own CURRENT-pointer semantics.)
    if (generation_store_root / CURRENT_NAME).exists():
        raise AlreadySeededError(
            f"generation store at {generation_store_root} already has a CURRENT "
            "generation -- this is a one-time seeder and refuses to overwrite or "
            "duplicate an already-seeded store"
        )

    parameters, identity = _production_parameters_and_identity(
        chemistry_hmac_key=chemistry_hmac_key
    )

    # --- 1. cold-start (real production bootstrap) -----------------------
    engine = _cold_start(
        generation_store_root=generation_store_root,
        chemistry_hmac_key=chemistry_hmac_key,
        checkpoint_hmac_key=checkpoint_hmac_key,
        parameters=parameters,
        identity=identity,
    )

    # --- 2. fail-closed guard: must be a genuinely fresh genesis ---------
    if engine._learned_state.initial_event is not None:
        raise AlreadySeededError(
            "cold-start restored an engine whose initial_event is already "
            "non-None -- the store is already seeded; refusing to seed twice"
        )
    engine._learned_state.verify()

    # --- 3. learn one real first successor -------------------------------
    genesis_result, learned = _learn_first_successor(
        chemistry_hmac_key=chemistry_hmac_key, parameters=parameters
    )

    # The re-derived genesis must byte-match the engine's own fresh genesis;
    # otherwise the two derivations diverged and persisting ``learned`` would be
    # inconsistent with the engine's live state. This is a real consistency
    # gate, not decoration.
    if genesis_result.genesis.receipt_sha256 != engine._learned_state.receipt_sha256:
        raise RuntimeError(
            "re-derived genesis does not byte-match the cold-start engine's "
            "genesis; refusing to persist an inconsistent successor"
        )

    # --- 4. persist via the engine's OWN real persistence path -----------
    # Reuse ``_persist_checkpoint`` exactly (do not reimplement persistence):
    # install the just-learned state as the engine's learned state and drive
    # the engine's own checkpoint commit. ``engine._scene_archive`` is the
    # empty ``CoexperiencedSceneArchive`` the fresh-genesis bootstrap already
    # constructed -- persisting it matches the proven round-trip template
    # (which also persists an empty archive; a restored generation's mode bank
    # is re-mounted at rank zero, so scene episodes would be recall-inert until
    # re-lived anyway -- design section 9).
    engine._learned_state = learned
    engine._persist_checkpoint()

    # --- 5. genuine round-trip proof (real restore off disk) -------------
    restored_engine = _cold_start(
        generation_store_root=generation_store_root,
        chemistry_hmac_key=chemistry_hmac_key,
        checkpoint_hmac_key=checkpoint_hmac_key,
        parameters=parameters,
        identity=identity,
    )
    restored = restored_engine._learned_state
    if restored.initial_event is None:
        raise RuntimeError(
            "round-trip restore produced a None initial_event after seeding"
        )
    if restored.receipt_sha256 != learned.receipt_sha256:
        raise RuntimeError(
            "round-trip restored learned-state receipt does not match the "
            "persisted successor"
        )
    if restored.receipt_payload != learned.receipt_payload:
        raise RuntimeError(
            "round-trip restored learned-state payload does not byte-match the "
            "persisted successor"
        )
    if (
        restored.initial_event.event_receipt_sha256
        != learned.initial_event.event_receipt_sha256
    ):
        raise RuntimeError(
            "round-trip restored initial_event does not match the persisted "
            "successor"
        )
    if restored.output_bank.bank_receipt_sha256 != learned.output_bank.bank_receipt_sha256:
        raise RuntimeError("round-trip restored output_bank does not match")
    if restored.stable_bank.bank_receipt_sha256 != learned.stable_bank.bank_receipt_sha256:
        raise RuntimeError("round-trip restored stable_bank does not match")
    if restored.terminal != learned.terminal:
        raise RuntimeError("round-trip restored terminal flag does not match")
    restored.verify()


def _resolve_store_root(argv: list[str]) -> Path:
    """Resolve the store root exactly as the app does
    (``resolve_default_generation_store_root`` -> reads
    ``GLEW_CONVERSATION_ENGINE_STORE_ROOT`` or derives a sibling of
    ``STATE_DIR``), unless a single explicit path override is given on the
    command line."""

    overrides = [value for value in argv[1:] if not value.startswith("-")]
    if len(overrides) > 1:
        raise SystemExit(
            "usage: python -m dsf_ai_service.glew_runtime.seed_first_production_successor "
            "[STORE_ROOT]"
        )
    if overrides:
        return Path(overrides[0])
    return resolve_default_generation_store_root()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)

    chem_secret = os.environ.get(GLEW_CHEMISTRY_HMAC_KEY_ENV, "")
    ckpt_secret = os.environ.get(GLEW_CHECKPOINT_HMAC_KEY_ENV, "")
    if not chem_secret:
        print(
            f"SEED_RESULT=FAILURE: {GLEW_CHEMISTRY_HMAC_KEY_ENV} is unset -- "
            "export the real AWS Secrets Manager chemistry HMAC secret before "
            "running the seeder"
        )
        return 1
    if not ckpt_secret:
        print(
            f"SEED_RESULT=FAILURE: {GLEW_CHECKPOINT_HMAC_KEY_ENV} is unset -- "
            "export the real AWS Secrets Manager checkpoint HMAC secret before "
            "running the seeder"
        )
        return 1

    # Same UTF-8 encoding the app uses for both secrets (see
    # app.py::_boot_glew_conversation_engine).
    chemistry_hmac_key = chem_secret.encode("utf-8")
    checkpoint_hmac_key = ckpt_secret.encode("utf-8")

    try:
        store_root = _resolve_store_root(argv)
        store_root.mkdir(parents=True, exist_ok=True)
        seed_first_successor(
            generation_store_root=store_root,
            chemistry_hmac_key=chemistry_hmac_key,
            checkpoint_hmac_key=checkpoint_hmac_key,
        )
    except AlreadySeededError as error:
        print(f"SEED_RESULT=FAILURE: already-seeded: {error}")
        return 1
    except Exception as error:  # noqa: BLE001 -- report any failure unambiguously
        print(f"SEED_RESULT=FAILURE: {type(error).__name__}: {error}")
        return 1

    print(
        f"SEED_RESULT=SUCCESS store_root={store_root} "
        f"engine_id={calibration.ENGINE_ID} "
        f"relation_id={FIRST_SUCCESSOR_RELATION_ID} "
        "(one real first learned successor persisted and round-trip restored; "
        "GLEW_CONVERSATION_ENGINE_ENABLED may now be turned on)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = (
    "AlreadySeededError",
    "GLEW_CHEMISTRY_HMAC_KEY_ENV",
    "GLEW_CHECKPOINT_HMAC_KEY_ENV",
    "FIRST_SUCCESSOR_RELATION_ID",
    "seed_first_successor",
    "main",
)
