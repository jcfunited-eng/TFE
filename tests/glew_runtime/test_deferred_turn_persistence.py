"""Real, non-monkeypatched conformance for utterance-transaction Milestone 1:
one ``ImmutableGenerationStore`` commit per real multi-scalar turn.

What Milestone 1 changed (``clean_conversation_engine.py`` /
``multi_scalar_turn_scheduler.py``): within one real scheduler turn, every
committing scalar still learns for real, per scalar, IN MEMORY -- every
receipt mechanism, every learn transaction, every checkpoint-tick advance is
byte-identical to the historical per-scalar chain -- but the store commit
itself (8 fsyncs + two full re-read/re-hash verification passes per commit)
is deferred and fired exactly once, at the turn's final scalar, iff ANY
scalar of the turn genuinely changed learned state. The expression-close
learn at the final scalar folds into that same single commit. Single-scalar
callers outside the scheduler keep the historical commit-immediately
behaviour (``defer_persistence`` defaults to ``False`` everywhere).

The three hard requirements proven here, each with real machinery only:

1. Crash mid-turn: a deferred turn performs NO store write before its single
   end-of-turn flush, so death between scalars leaves the store's last
   pre-turn generation untouched and fully restorable -- proven both at the
   byte level (CURRENT pointer + generation directory unchanged) and through
   the real production bootstrap restore
   (``test_crash_between_deferred_scalars_restores_pre_turn_generation``).

2. Equivalence: the generation a deferred turn persists at close is
   byte-identical (same tick, same checkpoint ids, same learned-state /
   archive / identity-binding payloads) to what today's per-scalar commit
   chain produces for the same turn, because the deferred path consumes
   checkpoint ticks exactly as the immediate path does and only batches the
   store I/O (``test_deferred_turn_generation_equals_per_scalar_chain*``).

3. Honesty: an in-memory failure during a later scalar leaves the engine
   REPORTING (``has_unpersisted_learned_state``) that its in-memory learned
   state is ahead of the persisted generation -- never silently claiming
   durability it does not have -- and any later successful checkpoint commit
   persists the full current state and clears the claim
   (``test_mid_turn_failure_never_claims_unpersisted_state``).

Every fixture below is the same real, non-monkeypatched construction the
sibling test modules already drive: the fast module-scoped engine fixture
from ``test_clean_conversation_engine.py`` (genuine six-lane runtime, real
rank-two mode bank, real learned binding) and, for the production-restore
proof, the exact seeder + bootstrap cold-start pattern
``test_seed_first_production_successor.py`` proved.
"""

from __future__ import annotations

import json
import shutil
import threading
import time

import pytest

from dsf_ai_service.glew_runtime.clean_conversation_engine import (
    ARCHIVE_CHECKPOINT_RELATIVE_PATH,
    CHECKPOINT_RELATIVE_PATHS,
    GENERATION_IDENTITY_BINDING_RELATIVE_PATH,
    LEARNING_CHECKPOINT_RELATIVE_PATH,
    _canonical_bytes,
)
from dsf_ai_service.glew_runtime.expression_learning import (
    learned_binding_checkpoint_payload,
    restore_learned_binding_checkpoint,
)
from dsf_ai_service.glew_runtime.coexperienced_scene_archive import (
    coexperienced_scene_archive_checkpoint_payload,
)
from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.multi_scalar_turn_scheduler import (
    MultiScalarTurnScheduler,
    default_scalar_task_id,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    CURRENT_NAME,
    GENERATIONS_DIRECTORY,
)

from tests.glew_runtime.test_clean_conversation_engine import (
    _CHECKPOINT_KEY,
    _CHECKPOINT_KEY_ID,
    _ENGINE_ID,
    _build_engine,
    _mount_test_chemistry_runtime,
    _new_generation_store,
    _turn,
    fixture,
)
from tests.glew_runtime.test_seed_first_production_successor import (
    _cold_start,
    _keys,
    _story_chemistry,
)
from dsf_ai_service.glew_runtime.seed_first_production_successor import (
    seed_first_successor,
)


def _generation_directories(store) -> list[str]:
    return sorted(
        entry.name for entry in (store.root / GENERATIONS_DIRECTORY).iterdir()
    )


def _scalar_call(
    engine, story_chemistry, task_id: str, text: str, *,
    is_final_scalar: bool, defer_persistence: bool = False,
):
    """One real per-scalar engine call -- the exact call shape the scheduler
    makes, exposed here so the per-scalar (historical) chain and the deferred
    chain can be driven with IDENTICAL turn identities."""

    return engine.run_clean_conversation(
        turn=_turn(task_id, text, source="deferred-persistence-test"),
        story_chemistry=story_chemistry,
        is_final_scalar=is_final_scalar,
        defer_persistence=defer_persistence,
    )


def _learning_probe_payload(engine) -> bytes:
    """The engine's CURRENT in-memory learned state as one canonical,
    HMAC-signed checkpoint payload under a fixed probe id -- byte equality of
    two engines' probes proves their learned states are byte-identical."""

    return learned_binding_checkpoint_payload(
        state=engine._learned_state,
        checkpoint_id="deferred-persistence-equivalence-probe",
        authentication_key=_CHECKPOINT_KEY,
        key_id=_CHECKPOINT_KEY_ID,
    )


def _archive_probe_payload(engine) -> bytes:
    return coexperienced_scene_archive_checkpoint_payload(
        archive=engine._scene_archive,
        checkpoint_id="deferred-persistence-archive-probe",
        authentication_key=_CHECKPOINT_KEY,
        key_id=_CHECKPOINT_KEY_ID,
    )


# ---------------------------------------------------------------------------
# Hard requirement 1, byte level: a deferred turn performs NO store I/O before
# its single flush, so death between scalars leaves the pre-turn generation
# untouched, fully verified, and restorable.
# ---------------------------------------------------------------------------


def test_deferred_scalar_writes_nothing_and_death_between_scalars_keeps_pre_turn_generation(
    fixture, tmp_path_factory
):
    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    # Establish the real pre-turn generation via the engine's OWN checkpoint
    # path (production always has one -- the seeded generation -- before any
    # turn runs).
    engine._persist_checkpoint()
    pre_current_bytes = (generation_store.root / CURRENT_NAME).read_bytes()
    pre_generations = _generation_directories(generation_store)
    pre_loaded = generation_store.load_current()
    pre_bindings = len(engine._learned_state.output_bank.bindings)
    assert not engine.has_unpersisted_learned_state

    # One real committing NON-final scalar of a deferred (multi-scalar) turn:
    # the fixture's root scene replay genuinely commits and genuinely learns,
    # in memory only.
    result = _scalar_call(
        engine,
        fixture["root_chemistry"],
        fixture["root_task_id"],
        "a",
        is_final_scalar=False,
        defer_persistence=True,
    )
    result.verify()
    assert result.initial_event_receipt_sha256 is not None  # it really committed
    assert len(engine._learned_state.output_bank.bindings) == pre_bindings + 1
    # The engine honestly reports its in-memory state is ahead of the store.
    assert engine.has_unpersisted_learned_state

    # ZERO store I/O happened for that scalar: the CURRENT pointer bytes and
    # the immutable generation directory set are untouched.
    assert (generation_store.root / CURRENT_NAME).read_bytes() == pre_current_bytes
    assert _generation_directories(generation_store) == pre_generations

    # Death between scalars: the engine above is simply never called again (a
    # deferred turn's only store write is its final flush, which never ran).
    # A genuine independent read of the same store re-verifies the whole
    # pre-turn generation byte-for-byte -- nothing half-written anywhere.
    restored = generation_store.load_current()
    assert restored.generation_uuid == pre_loaded.generation_uuid
    assert restored.manifest_sha256 == pre_loaded.manifest_sha256
    assert restored.tick == pre_loaded.tick

    # And the restored learned state is exactly the pre-turn state (the
    # mid-turn in-memory learn is honestly gone with the crashed process).
    learning_envelope = restored.payload(LEARNING_CHECKPOINT_RELATIVE_PATH)
    restored_state = restore_learned_binding_checkpoint(
        checkpoint_payload=_canonical_bytes(learning_envelope),
        authentication_key=_CHECKPOINT_KEY,
        expected_key_id=_CHECKPOINT_KEY_ID,
    )
    restored_state.verify()
    assert len(restored_state.output_bank.bindings) == pre_bindings


# ---------------------------------------------------------------------------
# Hard requirement 1, production level: the exact seeder + bootstrap restore
# pattern ``test_seed_first_production_successor.py`` proved, with the crash
# landing between a deferred turn's scalars.
# ---------------------------------------------------------------------------


def test_crash_between_deferred_scalars_restores_pre_turn_generation(tmp_path):
    chemistry_hmac_key, checkpoint_hmac_key = _keys()
    seed_first_successor(
        generation_store_root=tmp_path,
        chemistry_hmac_key=chemistry_hmac_key,
        checkpoint_hmac_key=checkpoint_hmac_key,
    )
    pre_current_bytes = (tmp_path / CURRENT_NAME).read_bytes()
    pre_generations = sorted(
        entry.name for entry in (tmp_path / GENERATIONS_DIRECTORY).iterdir()
    )

    engine = _cold_start(tmp_path, chemistry_hmac_key, checkpoint_hmac_key)
    story_chemistry = _story_chemistry(chemistry_hmac_key)
    assert len(engine._learned_state.stable_bank.bindings) == 1

    # Regrow the rank-0 bank live (bootstrap-silent growth, no commit, no
    # persistence) -- the proven precondition for a committing repeat-'a'.
    _scalar_call(engine, story_chemistry, "regrow-a", "a", is_final_scalar=False)
    _scalar_call(engine, story_chemistry, "regrow-b", "b", is_final_scalar=False)
    assert engine._mode_bank.rank == 2

    # A real committing NON-final scalar of a deferred multi-scalar turn: it
    # genuinely learns the second successor IN MEMORY, and defers the commit.
    nonfinal = _scalar_call(
        engine,
        story_chemistry,
        "crash-nonfinal-a",
        "a",
        is_final_scalar=False,
        defer_persistence=True,
    )
    assert nonfinal.initial_event_receipt_sha256 is not None  # really committed
    assert len(engine._learned_state.stable_bank.bindings) == 2  # learned in memory
    assert engine.has_unpersisted_learned_state
    # The store is byte-for-byte the seeded pre-turn generation.
    assert (tmp_path / CURRENT_NAME).read_bytes() == pre_current_bytes
    assert sorted(
        entry.name for entry in (tmp_path / GENERATIONS_DIRECTORY).iterdir()
    ) == pre_generations

    # Death between scalars: the doomed engine is never called again. A
    # GENUINE second cold-start through the real production bootstrap (full
    # manifest/hash/HMAC verification) restores the last pre-turn generation.
    restored_engine = _cold_start(tmp_path, chemistry_hmac_key, checkpoint_hmac_key)
    restored = restored_engine._learned_state
    restored.verify()
    assert restored.initial_event is not None
    assert len(restored.stable_bank.bindings) == 1  # exactly the pre-turn state
    assert len(restored.output_bank.bindings) == 1
    assert not restored.terminal
    assert not restored_engine.has_unpersisted_learned_state


# ---------------------------------------------------------------------------
# Hard requirement 2: the deferred turn's single persisted generation is
# byte-identical (tick, checkpoint ids, learned state, archive, identity
# binding, restored state) to today's per-scalar commit chain for the SAME
# turn -- proven for both deferred shapes:
#   (a) the state change happens at a NON-final scalar and the end-of-turn
#       flush carries it (final scalar honestly does not commit), and
#   (b) the final scalar commits and the expression-close learn folds into
#       the turn's single commit.
# ---------------------------------------------------------------------------


def _assert_stores_and_states_equivalent(engine_a, store_a, engine_b, store_b):
    a_current = store_a.load_current()
    b_current = store_b.load_current()

    # Same tick, and exactly one immutable generation on each side.
    assert a_current.tick == b_current.tick
    assert len(_generation_directories(store_a)) == 1
    assert len(_generation_directories(store_b)) == 1

    # All three persisted checkpoint payloads are identical (the store
    # envelope differs only by its random generation UUID; the payloads --
    # checkpoint ids, HMAC signatures, receipt records, episodes, identity
    # binding -- are what the engine wrote, canonical and deterministic).
    for relative_path in CHECKPOINT_RELATIVE_PATHS:
        assert a_current.payload(relative_path) == b_current.payload(relative_path), (
            f"persisted payload diverged for {relative_path!r}"
        )

    # The two engines' live in-memory learned states and archives are
    # byte-identical under one probe checkpoint id.
    assert _learning_probe_payload(engine_a) == _learning_probe_payload(engine_b)
    assert _archive_probe_payload(engine_a) == _archive_probe_payload(engine_b)

    # Genuine restores off both stores are byte-identical too, and equal the
    # deferred engine's own in-memory claim (the deferred engine never claims
    # state the store does not hold).
    restored_states = []
    for store in (store_a, store_b):
        envelope = store.load_current().payload(LEARNING_CHECKPOINT_RELATIVE_PATH)
        state = restore_learned_binding_checkpoint(
            checkpoint_payload=_canonical_bytes(envelope),
            authentication_key=_CHECKPOINT_KEY,
            expected_key_id=_CHECKPOINT_KEY_ID,
        )
        state.verify()
        restored_states.append(state)
    probe = lambda state: learned_binding_checkpoint_payload(  # noqa: E731
        state=state,
        checkpoint_id="deferred-persistence-equivalence-probe",
        authentication_key=_CHECKPOINT_KEY,
        key_id=_CHECKPOINT_KEY_ID,
    )
    assert probe(restored_states[0]) == probe(restored_states[1])
    assert probe(restored_states[1]) == _learning_probe_payload(engine_b)


def test_deferred_turn_generation_equals_per_scalar_chain_flush_shape(
    fixture, tmp_path_factory
):
    """Shape (a): scalar 0 ('a', the fixture's root replay) commits and learns;
    scalar 1 ('q') is genuinely novel, grows a mode, and honestly does NOT
    commit -- so the deferred engine's single commit is the END-OF-TURN FLUSH,
    fired even though the final scalar itself committed nothing."""

    store_a = _new_generation_store(tmp_path_factory)
    engine_a = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=store_a,
    )
    store_b = _new_generation_store(tmp_path_factory)
    engine_b = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=store_b,
    )

    text = "aq"
    task_id = "equiv-flush-turn"
    # The committing scalar must replay the fixture's root scene identity (the
    # scheduler's own documented ``scalar_task_ids`` replay affordance).
    scalar_task_ids = (fixture["root_task_id"], default_scalar_task_id(task_id, 1))

    # Engine A: today's historical per-scalar commit chain (defer never set).
    for index, scalar in enumerate(text):
        _scalar_call(
            engine_a,
            fixture["root_chemistry"],
            scalar_task_ids[index],
            scalar,
            is_final_scalar=index == len(text) - 1,
        )

    # Engine B: the SAME turn through the real production entry point, which
    # now signals deferral itself.
    scheduler = MultiScalarTurnScheduler(engine=engine_b)
    result = scheduler.run_turn(
        task_id=task_id,
        text=text,
        story_chemistry=fixture["root_chemistry"],
        source="deferred-persistence-test",
        scalar_task_ids=scalar_task_ids,
    )
    assert result.committed_scalar_indices == (0,)  # non-final commit, final none
    assert not engine_b.has_unpersisted_learned_state  # the flush really ran

    _assert_stores_and_states_equivalent(engine_a, store_a, engine_b, store_b)


def test_deferred_turn_generation_equals_per_scalar_chain_close_shape(
    fixture, tmp_path_factory
):
    """Shape (b): scalar 0 ('q') is novel and commits nothing; scalar 1 ('a',
    the root replay) is the FINAL scalar, genuinely commits, and closes the
    accumulated expression -- the close learn folds into the turn's single
    commit (the close's own immediate persist IS the one commit; the flush is
    a no-op)."""

    store_a = _new_generation_store(tmp_path_factory)
    engine_a = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=store_a,
    )
    store_b = _new_generation_store(tmp_path_factory)
    engine_b = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=store_b,
    )

    text = "qa"
    task_id = "equiv-close-turn"
    scalar_task_ids = (default_scalar_task_id(task_id, 0), fixture["root_task_id"])

    for index, scalar in enumerate(text):
        _scalar_call(
            engine_a,
            fixture["root_chemistry"],
            scalar_task_ids[index],
            scalar,
            is_final_scalar=index == len(text) - 1,
        )

    scheduler = MultiScalarTurnScheduler(engine=engine_b)
    result = scheduler.run_turn(
        task_id=task_id,
        text=text,
        story_chemistry=fixture["root_chemistry"],
        source="deferred-persistence-test",
        scalar_task_ids=scalar_task_ids,
    )
    assert result.committed_scalar_indices == (1,)  # only the final scalar
    assert not engine_b.has_unpersisted_learned_state

    # Both engines really closed the accumulated expression at the final scalar.
    assert engine_a._learned_state.terminal
    assert engine_b._learned_state.terminal
    assert engine_a._learned_state.pending_relation is None
    assert engine_b._learned_state.pending_relation is None

    _assert_stores_and_states_equivalent(engine_a, store_a, engine_b, store_b)


# ---------------------------------------------------------------------------
# A turn with ZERO learned-state changes commits nothing at all.
# ---------------------------------------------------------------------------


def test_deferred_turn_with_no_state_change_commits_nothing(fixture, tmp_path_factory):
    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    scheduler = MultiScalarTurnScheduler(engine=engine)

    # Two genuinely novel scalars: both grow modes, neither commits, nothing
    # learns -- so the turn's flush finds nothing pending and writes nothing.
    result = scheduler.run_turn(
        task_id="no-state-change-turn",
        text="vw",
        story_chemistry=_mount_test_chemistry_runtime(),
        source="deferred-persistence-test",
    )
    assert result.all_silent
    assert not result.any_commit
    assert not engine.has_unpersisted_learned_state
    assert not (generation_store.root / CURRENT_NAME).exists()
    assert _generation_directories(generation_store) == []


# ---------------------------------------------------------------------------
# Hard requirement 3, honesty flag truthful in every path: an immediate-mode
# store commit that genuinely fails at the OS level leaves the engine REPORTING
# that its in-memory learned state is ahead of the persisted generation -- it
# never reads False while memory is ahead, not even in a terminal (closed)
# state that will never consume another tick (verifier Fix 3;
# repro_flag_false_negative.py).
# ---------------------------------------------------------------------------


def test_immediate_commit_failure_keeps_honesty_flag_truthful(fixture, tmp_path_factory):
    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    pre_state = engine._learned_state
    assert not engine.has_unpersisted_learned_state

    # Make the store genuinely unable to commit at the OS level: replace the
    # generations directory with a regular file, so the commit's own mkdir of
    # `.building-<uuid>` fails with ENOTDIR -- the exact shape of a real
    # transient EFS/disk fault raising out of ImmutableGenerationStore.commit
    # (no engine logic is monkeypatched).
    gen_dir = generation_store.root / GENERATIONS_DIRECTORY
    shutil.rmtree(gen_dir)
    gen_dir.write_bytes(b"")
    try:
        # A single-scalar deferred turn whose one scalar commits AND closes:
        # the close's immediate persist is the turn's only commit, and it fails
        # at the store layer AFTER the in-memory close mutation has happened.
        scheduler = MultiScalarTurnScheduler(engine=engine)
        with pytest.raises(OSError):
            scheduler.run_turn(
                task_id="immediate-fail-turn",
                text="a",
                story_chemistry=fixture["root_chemistry"],
                source="deferred-persistence-test",
                scalar_task_ids=(fixture["root_task_id"],),
            )
    finally:
        gen_dir.unlink()
        gen_dir.mkdir()

    # In-memory learned state really moved (the close made it terminal), the
    # store published NO generation, and the honesty flag reports EXACTLY that
    # -- ahead of the store -- even though this was an immediate commit with no
    # deferred tick, and even though the terminal state will never consume
    # another checkpoint tick to self-heal.
    assert engine._learned_state is not pre_state
    assert engine._learned_state.terminal
    assert not (generation_store.root / CURRENT_NAME).exists()
    assert _generation_directories(generation_store) == []
    assert engine.has_unpersisted_learned_state


# ---------------------------------------------------------------------------
# Hard requirement 4, aborted-turn durability (verifier Fix 2): when a later
# scalar of a deferred turn raises, the EARLIER scalars' already-learned,
# receipt-verified state is flushed before the abort propagates -- an aborted
# turn is never LESS durable than baseline per-scalar mode, and no stranded
# pending state is left for deploy quiescence to lose. The aborted scalar
# itself learned nothing. (Process-death mid-turn semantics are unchanged --
# see the crash tests above -- because those never raise; the engine is simply
# never called again.)
# ---------------------------------------------------------------------------


def test_aborted_deferred_turn_flushes_already_learned_state(fixture, tmp_path_factory):
    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )

    # Scalar 0 of a deferred turn: really commits, really learns, in memory
    # only -- store I/O batched, nothing on disk yet.
    first = _scalar_call(
        engine,
        fixture["root_chemistry"],
        fixture["root_task_id"],
        "a",
        is_final_scalar=False,
        defer_persistence=True,
    )
    assert first.initial_event_receipt_sha256 is not None
    assert engine.has_unpersisted_learned_state
    assert not (generation_store.root / CURRENT_NAME).exists()
    state_after_learn = _learning_probe_payload(engine)

    # A LATER scalar of the same turn fails for real: a malformed multi-scalar
    # text is the engine's own genuine fail-closed ReceiptError, raised INSIDE
    # the locked transaction (real_experience_learning_pipeline's own
    # "exactly one Unicode scalar" guard) BEFORE any state mutation, aborting
    # the turn.
    with pytest.raises(ReceiptError, match="exactly one Unicode"):
        _scalar_call(
            engine,
            fixture["root_chemistry"],
            "aborting-final-scalar",
            "xy",
            is_final_scalar=True,
            defer_persistence=True,
        )

    # The abort flushed scalar 0's already-receipt-verified learn before
    # propagating: the engine now honestly reports NO unpersisted state, and a
    # genuine independent read of the store restores exactly scalar 0's learn.
    # The aborted scalar contributed nothing -- the persisted state is byte-for
    # -byte the state after scalar 0's learn, unchanged by the failed scalar.
    assert not engine.has_unpersisted_learned_state
    assert _learning_probe_payload(engine) == state_after_learn
    current = generation_store.load_current()
    assert current.tick == 0  # scalar 0's one deferred checkpoint tick
    assert len(_generation_directories(generation_store)) == 1

    persisted_envelope = current.payload(LEARNING_CHECKPOINT_RELATIVE_PATH)
    restored_state = restore_learned_binding_checkpoint(
        checkpoint_payload=_canonical_bytes(persisted_envelope),
        authentication_key=_CHECKPOINT_KEY,
        expected_key_id=_CHECKPOINT_KEY_ID,
    )
    restored_state.verify()
    expected_envelope = json.loads(
        learned_binding_checkpoint_payload(
            state=engine._learned_state,
            checkpoint_id=f"{_ENGINE_ID}-learning-0",
            authentication_key=_CHECKPOINT_KEY,
            key_id=_CHECKPOINT_KEY_ID,
        )
    )
    assert json.loads(_canonical_bytes(persisted_envelope)) == expected_envelope
    # The identity binding cites the same tick's checkpoint ids, and the
    # archived scene episode from scalar 0's learn rode the same single commit.
    identity_envelope = current.payload(GENERATION_IDENTITY_BINDING_RELATIVE_PATH)
    assert identity_envelope["learning_checkpoint_id"] == f"{_ENGINE_ID}-learning-0"
    assert identity_envelope["archive_checkpoint_id"] == f"{_ENGINE_ID}-archive-0"
    archive_envelope = current.payload(ARCHIVE_CHECKPOINT_RELATIVE_PATH)
    assert len(archive_envelope["body"]["episodes"]) == 1


# ---------------------------------------------------------------------------
# Hard requirement 5, turn-level serialization (verifier Fix 1): the engine's
# own lock serializes SCALARS, not TURNS -- two overlapping /converse requests
# each call run_turn on the SAME shared engine, and without a turn mutex their
# scalars interleave, so one turn's end-of-turn deferred flush could durably
# commit ANOTHER turn's mid-turn, in-flight learns. A turn mutex held by
# run_turn for the whole turn makes turns fully serial, so each turn's single
# deferred flush covers exactly its own learns.
# ---------------------------------------------------------------------------


class _TurnConcurrencyProbeEngine:
    """Test instrument (fakes NO cognition): delegates every call to a real
    ``ProductionCleanConversationEngine`` but, on each scalar, records the
    calling thread and sleeps briefly BEFORE delegating -- outside the engine's
    own locks -- to widen the window in which a second concurrent turn could
    interleave its scalars. ``serialize_turn`` is forwarded so ``run_turn``
    still acquires the real engine turn mutex; without that mutex this sleep
    would let the other turn's scalars interleave, and the recorded thread
    sequence would show it. Every real result comes from the wrapped engine."""

    def __init__(self, inner, *, entry_log, guard, hold_s):
        self._inner = inner
        self._entry_log = entry_log
        self._guard = guard
        self._hold_s = hold_s

    def run_clean_conversation(
        self, *, turn, story_chemistry, is_final_scalar=False, defer_persistence=False
    ):
        thread_name = threading.current_thread().name
        with self._guard:
            self._entry_log.append(thread_name)
        # Yield for real with NO engine lock held here: without the turn mutex
        # this hands the other thread's scalar the interleave window.
        time.sleep(self._hold_s)
        return self._inner.run_clean_conversation(
            turn=turn,
            story_chemistry=story_chemistry,
            is_final_scalar=is_final_scalar,
            defer_persistence=defer_persistence,
        )

    def serialize_turn(self):
        return self._inner.serialize_turn()


def test_two_concurrent_run_turns_fully_serialize(fixture, tmp_path_factory):
    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    # A real pre-turn generation, as production always has one.
    engine._persist_checkpoint()
    pre_generations = _generation_directories(generation_store)
    assert len(pre_generations) == 1
    pre_bindings = len(engine._learned_state.output_bank.bindings)
    assert not engine.has_unpersisted_learned_state

    entry_log = []
    guard = threading.Lock()
    probe_engine = _TurnConcurrencyProbeEngine(
        engine, entry_log=entry_log, guard=guard, hold_s=0.05
    )
    scheduler = MultiScalarTurnScheduler(engine=probe_engine)
    chemistry_b = _mount_test_chemistry_runtime()

    # Turn A ("aq"): scalar 'a' is the fixture's committing root replay (learns
    # one binding, deferred), scalar 'q' is novel and does not commit -- so A's
    # single end-of-turn flush carries A's one real learn. Turn B ("vw"): two
    # novel scalars, neither commits, nothing learns -- so B's flush is a clean
    # no-op. In the pre-fix interleaving, B's flush would instead durably commit
    # A's mid-turn 'a' learn (and lower A's honesty flag); the turn mutex
    # forbids B from running a single scalar until A's whole turn has completed.
    results = {}
    errors = {}

    def run_a():
        try:
            results["A"] = scheduler.run_turn(
                task_id="serialize-turn-a",
                text="aq",
                story_chemistry=fixture["root_chemistry"],
                source="deferred-persistence-test",
                scalar_task_ids=(
                    fixture["root_task_id"],
                    default_scalar_task_id("serialize-turn-a", 1),
                ),
            )
        except BaseException as exc:  # pragma: no cover - surfaced via assert
            errors["A"] = exc

    def run_b():
        try:
            results["B"] = scheduler.run_turn(
                task_id="serialize-turn-b",
                text="vw",
                story_chemistry=chemistry_b,
                source="deferred-persistence-test",
            )
        except BaseException as exc:  # pragma: no cover - surfaced via assert
            errors["B"] = exc

    thread_a = threading.Thread(target=run_a, name="turn-A")
    thread_b = threading.Thread(target=run_b, name="turn-B")
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=30)
    thread_b.join(timeout=30)
    assert not errors, f"a concurrent run_turn raised: {errors}"
    assert not thread_a.is_alive() and not thread_b.is_alive()

    # Serialization proof: collapsing the per-scalar entry sequence to runs of
    # the same owning thread yields AT MOST two groups -- one turn's scalars ran
    # entirely before the other's, never interleaved. (Without the turn mutex
    # the 50ms window makes the sequence [A, B, A, B], four groups.)
    assert len(entry_log) == 4  # 2 scalars of A + 2 scalars of B
    groups = [
        name for i, name in enumerate(entry_log) if i == 0 or name != entry_log[i - 1]
    ]
    assert len(groups) <= 2, f"turns interleaved: {entry_log}"

    # Each turn's flush covered exactly its own learns: A committed its one 'a'
    # learn, B committed nothing. Exactly one new generation exists beyond the
    # pre-turn one, the flag is down, and a genuine restore yields pre-turn +
    # A's single binding -- never a half-turn, and never B's absence of a learn
    # masquerading as a commit.
    assert results["A"].committed_scalar_indices == (0,)
    assert results["B"].all_silent and not results["B"].any_commit
    assert not engine.has_unpersisted_learned_state
    assert len(_generation_directories(generation_store)) == len(pre_generations) + 1
    current = generation_store.load_current()
    restored = restore_learned_binding_checkpoint(
        checkpoint_payload=_canonical_bytes(
            current.payload(LEARNING_CHECKPOINT_RELATIVE_PATH)
        ),
        authentication_key=_CHECKPOINT_KEY,
        expected_key_id=_CHECKPOINT_KEY_ID,
    )
    restored.verify()
    assert len(restored.output_bank.bindings) == pre_bindings + 1
