"""Real, non-monkeypatched conformance for the recall-settlement cycle bound in
``dsf_ai_service.glew_runtime.recall_reentry.settle_complete_remembered_expression``.

Background (the pre-existing defect this bound closes)
-----------------------------------------------------
The settlement loop walks committed motif transitions until an exact expression
close or the first UNKNOWN.  The actuator's only cycle guard trips when an exact
``(source_state, transition_edge)`` pair repeats -- but every committed
transition hash-chains the prior result state into the next one (see
``CoexperiencedSceneRecallProvider.settle``'s ``fresh_result_state`` /
``fresh_transition_edge`` payloads), so the exact state and edge advance every
iteration and never repeat, even while the underlying mode/motif content
revisits the same two nodes forever.  With two learned successors that reference
each other (``mode0 -> 'b'`` and ``mode1 -> 'a'`` where 'a' recognises as mode0
and 'b' as mode1) a committing turn's recall spins without termination.  In
production each scheduler turn runs in a thread-pool executor with no per-call
timeout, so this stranded a worker thread permanently.

The fix adds a SECOND, independent structural bound: a genuinely terminating
settlement resolves at most one distinct successor binding per committed content
transition and (deterministic resolution) never revisits a mode it already left,
so the number of committed transitions is bounded by the number of distinct
learned successor bindings in the fixed stable mode/motif bank.  Exceeding that
count is proof of a real cycle -- never a false positive on a long-but-finite
chain, because the initial event's own successor is consumed before the loop, so
a legitimate chain always stays at least one under the count.

Both tests drive the REAL production seeder + bootstrap restore + live engine /
scheduler -- nothing is monkeypatched.
"""

from __future__ import annotations

import secrets
import time

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
from dsf_ai_service.glew_runtime.multi_scalar_turn_scheduler import (
    MultiScalarTurnScheduler,
)
from dsf_ai_service.glew_runtime.production_runtime_bootstrap import (
    bootstrap_production_clean_conversation_engine,
)
from dsf_ai_service.glew_runtime.seed_first_production_successor import (
    seed_first_successor,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    mount_packaged_production_story_chemistry,
)

# The exact loud diagnostic the bound prints when it fails closed on a cycle.
_CEILING_DIAGNOSTIC = "recall settlement exceeded the learned-successor ceiling"


def _keys() -> tuple[bytes, bytes]:
    return secrets.token_bytes(32), secrets.token_bytes(32)


def _cold_start(tmp_path, chemistry_hmac_key: bytes, checkpoint_hmac_key: bytes):
    """A real cold-start / restore through the exact production bootstrap the
    app uses, with the exact same production calibration/identity the seeder
    uses."""

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


def _story_chemistry(chemistry_hmac_key: bytes):
    return mount_packaged_production_story_chemistry(
        runtime_authentication_key=chemistry_hmac_key,
        runtime_key_id=calibration.CHEMISTRY_HMAC_KEY_ID,
    ).runtime


def _committing_turn(engine, story_chemistry, task_id: str, text: str, is_final_scalar: bool):
    payload = clean_conversation_turn_receipt_payload(
        task_id=task_id, text=text, source="cycle-bound-test"
    )
    turn = CleanConversationTurn(
        task_id=task_id,
        text=text,
        source="cycle-bound-test",
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    turn.verify()
    return engine.run_clean_conversation(
        turn=turn, story_chemistry=story_chemistry, is_final_scalar=is_final_scalar
    )


def _scheduler_turn(scheduler, story_chemistry, task_id: str, text: str):
    return scheduler.run_turn(
        task_id=task_id, text=text, story_chemistry=story_chemistry, source="cycle-bound-test"
    )


# ---------------------------------------------------------------------------
# (a) the EXACT cyclic scenario the prior agent found fails closed to honest
#     silence quickly, instead of spinning a worker thread forever.
# ---------------------------------------------------------------------------


def test_cyclic_recall_graph_fails_closed_to_silence_not_hang(tmp_path, capfd):
    """Reproduce the exact two-successor mutually-referencing cycle end to end
    and prove the new bound fails it closed to honest silence in well under a
    second, with the loud ``[glew]`` diagnostic, without corrupting state.

    Construction (all real, no monkeypatch):
      * Seed the first successor (``mode0 -> 'b'``), genuine cold-start off disk.
      * Regrow the rank-0 bank to rank two with the genesis scalars 'a'/'b'.
      * A committing NON-final 'a' turn accumulates the SECOND content successor
        ``mode1 -> 'a'`` (``expression_close=False``).  Its OWN recall runs on
        the still-acyclic seeded graph (fast silence).  After it, the learned
        graph is cyclic: ``mode0 -> 'b' -> mode1 -> 'a' -> mode0 -> ...``.
      * A further committing 'a' turn is the FIRST recall over the now-cyclic
        graph.  Pre-fix this spun 45s+ at 95% CPU with no termination; the
        actuator's exact-(state,edge) guard never fires because the result state
        hash-chains forward every iteration.

    The new bound catches it: the bank holds exactly two learned successor
    bindings, so the walk is allowed at most two committed transitions; the
    third is proof of a cycle and the loop fails closed to typed silence.
    """

    chemistry_hmac_key, checkpoint_hmac_key = _keys()
    seed_first_successor(
        generation_store_root=tmp_path,
        chemistry_hmac_key=chemistry_hmac_key,
        checkpoint_hmac_key=checkpoint_hmac_key,
    )
    engine = _cold_start(tmp_path, chemistry_hmac_key, checkpoint_hmac_key)
    story_chemistry = _story_chemistry(chemistry_hmac_key)

    # Regrow rank-0 -> rank-2 (bootstrap-silent growth, no commit).
    _committing_turn(engine, story_chemistry, "regrow-a", "a", is_final_scalar=False)
    _committing_turn(engine, story_chemistry, "regrow-b", "b", is_final_scalar=False)
    assert engine._mode_bank.rank == 2
    # Only the seeded successor exists so far -> graph is still acyclic.
    assert len(engine._learned_state.stable_bank.bindings) == 1

    # Accumulate the second, mutually-referencing successor (mode1 -> 'a').  This
    # turn's own recall is over the acyclic seeded graph (fast, honest silence).
    nonfinal = _committing_turn(engine, story_chemistry, "nonfinal-a", "a", is_final_scalar=False)
    assert nonfinal.initial_event_receipt_sha256 is not None  # it really committed
    assert not engine._learned_state.terminal
    # The learned graph is now genuinely cyclic: exactly two learned successors.
    assert len(engine._learned_state.stable_bank.bindings) == 2
    n_bindings = len(engine._learned_state.stable_bank.bindings)

    capfd.readouterr()  # drop any earlier output so we capture only the cyclic turn

    # The FIRST recall over the cyclic graph.  With the bound, this returns
    # quickly instead of hanging; time it to prove there is no spin.
    started = time.monotonic()
    cyclic = _committing_turn(engine, story_chemistry, "cyclic-a", "a", is_final_scalar=True)
    elapsed = time.monotonic() - started

    # Honest silence -- never a raw exception, never a hang, never fabricated text.
    assert cyclic.status is ConversationStatus.EXPLICIT_UNKNOWN_SILENCE
    assert cyclic.silent
    assert cyclic.visible_text == ""
    assert _CEILING_DIAGNOSTIC in cyclic.reason

    # Sub-second-class, and unambiguously not the pre-fix 45s+ spin.
    assert elapsed < 20.0

    # The loud diagnostic fired on the established ``[glew]`` channel, and it
    # tripped at the small, well-justified count: exactly one past the bound
    # (n_bindings + 1 committed transitions), so the overrun is minimal.
    out, _ = capfd.readouterr()
    assert "[glew] " + _CEILING_DIAGNOSTIC in out
    assert f"> {n_bindings} distinct learned successor bindings" in out
    assert f"{n_bindings + 1} committed transitions" in out

    # No state corruption: the learned state still verifies, and the engine is
    # still usable for a subsequent, non-cyclic real request.
    engine._learned_state.verify()
    novel = _committing_turn(engine, story_chemistry, "novel-q", "q", is_final_scalar=True)
    assert novel.status is ConversationStatus.EXPLICIT_NO_COMMIT_SILENCE
    assert novel.silent


# ---------------------------------------------------------------------------
# (b) a legitimate, genuinely-terminating recall chain is NOT falsely tripped:
#     the real close+release path still speaks, and the bound never fires.
# ---------------------------------------------------------------------------


def test_legitimate_closed_chain_releases_and_bound_never_trips(tmp_path, capfd):
    """A real terminating recall chain (``root -> 'b' -> close``) still releases
    its visible text 'b', and the cycle bound never fires on it.

    This is the same fully-automatic close+emit flow the prior agent proved
    through the real production entry point (``MultiScalarTurnScheduler``), used
    here as the no-false-positive guarantee: a legitimate chain resolves one
    committed content transition plus the close, strictly fewer than the number
    of learned successor bindings in the bank (the initial event's own successor
    is consumed before the settlement loop), so the bound has provable margin and
    must never trip.  If it did, the emission below would be silenced and the
    ceiling diagnostic would appear -- both are asserted absent.
    """

    chemistry_hmac_key, checkpoint_hmac_key = _keys()
    seed_first_successor(
        generation_store_root=tmp_path,
        chemistry_hmac_key=chemistry_hmac_key,
        checkpoint_hmac_key=checkpoint_hmac_key,
    )
    engine = _cold_start(tmp_path, chemistry_hmac_key, checkpoint_hmac_key)
    scheduler = MultiScalarTurnScheduler(engine=engine)
    story_chemistry = _story_chemistry(chemistry_hmac_key)

    # Regrow the rank-0 bank live to rank two through the scheduler.
    _scheduler_turn(scheduler, story_chemistry, "regrow-a", "a")
    _scheduler_turn(scheduler, story_chemistry, "regrow-b", "b")
    assert engine._mode_bank.rank == 2

    # First repeat 'a' (its single scalar IS final): recall is honest silence
    # (the seeded 'b' has no successor yet), then the engine closes the
    # accumulated 'b' expression at its leaf -- a clean, acyclic close.
    first = _scheduler_turn(scheduler, story_chemistry, "close-a", "a")
    assert first.all_silent
    assert engine._learned_state.terminal

    capfd.readouterr()  # only capture the releasing turn's output below

    # Second repeat 'a' under a fresh id -> the legitimate terminating chain
    # RELEASES 'b'.  This is a real recall settlement over the closed graph.
    second = _scheduler_turn(scheduler, story_chemistry, "emit-a", "a")
    assert not second.all_silent
    assert second.visible_scalar_texts == ("b",)
    result = second.outcomes[0].result
    result.verify()
    assert result.status is ConversationStatus.EXPRESSION_RELEASED
    assert result.visible_text == "b"

    # The bound never fired on the legitimate chain: no ceiling diagnostic, and
    # the release reason is not the fail-closed reason.
    out, _ = capfd.readouterr()
    assert _CEILING_DIAGNOSTIC not in out
    assert _CEILING_DIAGNOSTIC not in result.reason
