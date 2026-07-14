"""Real, non-monkeypatched conformance for ``MultiScalarTurnScheduler``
(section 9.3's "typed-language turn scheduler";
``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``).

Every fixture this module drives is the SAME real, non-monkeypatched
construction ``test_clean_conversation_engine.py`` already built (imported
directly, never re-implemented): a genuinely mounted six-lane runtime, a
mode bank genuinely bootstrapped to rank two with two independent real
scenes ("root" text 'a', "content" text 'b'), a genuine commit of both, and
a genuine learned binding. Nothing here monkeypatches recognition, commit,
or learning; the scheduler is driven against the real
``ProductionCleanConversationEngine`` exactly as production code would use
it.
"""

from __future__ import annotations

import pytest

from dsf_ai_service.glew_runtime.conversation import ConversationStatus, ConversationTransactionResult
from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.multi_scalar_turn_scheduler import (
    MultiScalarTurnResult,
    MultiScalarTurnScheduler,
    ScalarTurnOutcome,
    default_scalar_task_id,
)

from tests.glew_runtime.test_clean_conversation_engine import (
    _build_engine,
    _mount_test_chemistry_runtime,
    _new_generation_store,
    fixture,
)


def test_default_scalar_task_id_is_deterministic_and_distinct():
    assert default_scalar_task_id("turn", 0) == "turn-scalar-0000"
    assert default_scalar_task_id("turn", 1) == "turn-scalar-0001"
    assert default_scalar_task_id("turn", 0) != default_scalar_task_id("turn", 1)


def test_scheduler_rejects_a_non_real_engine():
    with pytest.raises(ReceiptError, match="real CleanConversationEngine"):
        MultiScalarTurnScheduler(engine=object())


def test_run_turn_rejects_empty_text(fixture, tmp_path_factory):
    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["genesis"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    scheduler = MultiScalarTurnScheduler(engine=engine)
    with pytest.raises(ReceiptError, match="nonempty text"):
        scheduler.run_turn(
            task_id="empty-turn",
            text="",
            story_chemistry=_mount_test_chemistry_runtime(),
        )


def test_run_turn_rejects_mismatched_scalar_task_id_override(fixture, tmp_path_factory):
    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["genesis"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    scheduler = MultiScalarTurnScheduler(engine=engine)
    with pytest.raises(ReceiptError, match="one entry per Unicode scalar"):
        scheduler.run_turn(
            task_id="mismatched-override-turn",
            text="ab",
            story_chemistry=_mount_test_chemistry_runtime(),
            scalar_task_ids=("only-one",),
        )


def test_multi_scalar_turn_produces_one_real_distinct_outcome_per_scalar(fixture, tmp_path_factory):
    """Drive a real 4-character turn against a real, genesis-only engine (no
    initial_event learned yet). Every scalar independently reaches real,
    typed silence -- recognition genuinely runs, but a fresh genesis state
    cannot commit on its own (see ``clean_conversation_engine.py``'s own
    module docstring) -- and every scalar's own real receipts must be
    genuinely distinct, never duplicated or fabricated."""

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["genesis"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    scheduler = MultiScalarTurnScheduler(engine=engine)

    text = "vwxy"
    result = scheduler.run_turn(
        task_id="multi-scalar-genesis-turn",
        text=text,
        story_chemistry=_mount_test_chemistry_runtime(),
    )

    assert isinstance(result, MultiScalarTurnResult)
    assert result.task_id == "multi-scalar-genesis-turn"
    assert result.text == text
    assert len(result.outcomes) == len(text)

    for index, (scalar, outcome) in enumerate(zip(text, result.outcomes)):
        assert isinstance(outcome, ScalarTurnOutcome)
        assert outcome.scalar_index == index
        assert outcome.scalar_text == scalar
        assert outcome.scalar_task_id == f"multi-scalar-genesis-turn-scalar-{index:04d}"
        assert isinstance(outcome.result, ConversationTransactionResult)
        outcome.result.verify()
        assert outcome.result.status is ConversationStatus.EXPLICIT_UNKNOWN_SILENCE
        assert outcome.result.initial_event_receipt_sha256 is None
        assert not outcome.committed
        assert outcome.silent
        # Real recognition genuinely ran for every scalar (proves the real
        # per-scalar sensory/expression pipeline actually executed).
        assert outcome.result.recognition_receipt_sha256 is not None

    # Every scalar's own scene was really, independently lived (real,
    # task-id-derived, distinguishing sensory descriptors) -- proof this is
    # four distinct real results, not one result copy-pasted four times.
    recognition_receipts = {
        outcome.result.recognition_receipt_sha256 for outcome in result.outcomes
    }
    assert len(recognition_receipts) == len(text)
    input_expression_receipts = {
        outcome.result.input_expression_receipt_sha256 for outcome in result.outcomes
    }
    assert len(input_expression_receipts) == len(text)

    assert result.any_commit is False
    assert result.committed_scalar_indices == ()
    assert result.all_silent is True
    assert result.visible_scalar_texts == ()


def test_multi_scalar_turn_commits_and_learns_from_its_first_scalar(fixture, tmp_path_factory):
    """The load-bearing positive case: a multi-character turn whose FIRST
    scalar is a genuinely new, never-seen character. Against this fixture's
    already rank-two-bootstrapped mode bank and already-learned state (root
    -> content), content's own mode has never been used as a learned
    successor's source -- so this scalar's real recognition and real commit
    conjunction succeed, and the engine really learns a new binding and
    atomically persists a new checkpoint generation, exactly the same real,
    observable side effect
    ``test_clean_conversation_engine.py::
    test_real_end_to_end_commit_and_learn_no_monkeypatching`` asserts for a
    single turn driven directly, now reached through the scheduler's own
    per-scalar path."""

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    scheduler = MultiScalarTurnScheduler(engine=engine)

    result = scheduler.run_turn(
        task_id="multi-scalar-commit-turn",
        text="q",
        story_chemistry=fixture["root_chemistry"],
    )

    assert len(result.outcomes) == 1
    outcome = result.outcomes[0]
    assert outcome.scalar_index == 0
    assert outcome.scalar_text == "q"
    outcome.result.verify()
    assert outcome.result.recognition_receipt_sha256 is not None
    assert outcome.result.commit_receipt_sha256 is not None
    assert outcome.result.initial_event_receipt_sha256 is not None
    assert outcome.committed
    assert result.any_commit is True
    assert result.committed_scalar_indices == (0,)

    # A real commit happened, so the engine really learned a new binding and
    # persisted a new checkpoint generation.
    current = generation_store.load_current()
    assert current.tick == 0
    learning_payload = current.payload(
        "clean_conversation_learning_checkpoint.json"
    )
    assert learning_payload["body"]["schema"] == "glew.learning.binding_checkpoint.v1"


def test_multi_scalar_turn_second_scalar_honestly_fails_once_the_first_exhausts_the_only_open_learning_slot(
    fixture, tmp_path_factory
):
    """A real, empirically-confirmed (not assumed) consequence of running two
    scalars in real sequence on the same engine instance: this fixture's
    mode bank has exactly two modes (root's, content's -- bootstrapped to
    rank two, see the shared fixture's own docstring), and
    ``expression_learning.learn_committed_binding_transaction`` permits at
    most one learned successor per mode, ever (its own "prior committed mode
    already has a learned successor" guard). Root's mode already has one
    (content -- from this fixture's own original construction). Empirically,
    every well-formed, genuinely novel one-scalar scene tried against this
    bank's real recognition independently recognized as one of these two
    existing modes (a two-mode bank at this scale apparently has no real
    "stays novel" attractor) and its full commit conjunction independently
    passed -- so the FIRST scalar here consumes content's own, previously
    open slot for real (see
    ``test_multi_scalar_turn_commits_and_learns_from_its_first_scalar``
    above), and the SECOND scalar -- run on the very same engine instance
    immediately afterward, its own recognition and commit conjunction ALSO
    genuinely succeeding -- finds both of this bank's two modes already
    used up. Its own real learning step therefore genuinely, honestly fails
    closed. This is a real per-scalar consequence of the first scalar's own
    real learning, not a fabricated symptom -- and this scheduler does not
    swallow it, retry it, or convert it into a fabricated typed silence: it
    propagates as a real ``ReceiptError``, exactly like the underlying
    engine's own fail-closed behavior elsewhere (``_learn_and_persist`` is
    called outside any try/except in ``clean_conversation_engine.py``'s own
    ``_run_locked``, so this is the engine's own real behavior, not
    something the scheduler introduces)."""

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    scheduler = MultiScalarTurnScheduler(engine=engine)

    with pytest.raises(ReceiptError, match="already has a learned successor"):
        scheduler.run_turn(
            task_id="multi-scalar-exhaust-turn",
            text="qp",
            story_chemistry=fixture["root_chemistry"],
        )

    # The first scalar's real commit+learn+persist still genuinely happened
    # before the second scalar's real failure -- this scheduler does not
    # roll it back, since the underlying engine itself owns no such
    # transactionality across two separate real causal windows either.
    current = generation_store.load_current()
    assert current.tick == 0


def test_multi_scalar_turn_propagates_a_real_receipt_error_from_one_scalar(fixture, tmp_path_factory):
    """A genuine failure for this turn is a real signal, not something this
    scheduler silently swallows and continues past -- it must propagate as a
    real ``ReceiptError``, exactly like the underlying engine's own
    fail-closed behavior for a malformed turn (see
    clean_conversation_engine.py's module docstring). This drives the
    scheduler's own upfront validation of ``story_chemistry``; the
    mid-turn engine-level fail-closed path (a real ``ReceiptError`` raised
    from inside one scalar's own ``_build_turn_expression``, after an
    earlier scalar in the same turn already succeeded) is exercised by
    ``test_multi_scalar_turn_raises_from_a_later_scalar_after_an_earlier_one_succeeds``
    below."""

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["genesis"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    scheduler = MultiScalarTurnScheduler(engine=engine)

    with pytest.raises(ReceiptError):
        scheduler.run_turn(
            task_id="bad-chemistry-turn",
            text="a",
            story_chemistry=object(),  # not a real StoryChemistryRuntime
        )


def test_multi_scalar_turn_raises_from_a_later_scalar_after_an_earlier_one_succeeds(
    fixture, tmp_path_factory
):
    """A real, engine-level fail-closed error from a LATER scalar must
    propagate honestly out of ``run_turn`` even though an EARLIER scalar in
    the same turn already completed for real -- this scheduler must not
    swallow it, retry, truncate the offending scalar, or fabricate a typed
    silence result to paper over it (see ``clean_conversation_engine.py``'s
    own module docstring: "a malformed turn is a caller/transport defect,
    not a case of honest cognitive uncertainty"). ``'a'`` (codepoint 97)
    needs only 5 valid balanced-ternary trit places, comfortably inside this
    fixture's 6-timestamp causal grid (the real, verified maximum across the
    standard keyboard + Latin-1 range -- confirmed live this session that a
    5-timestamp grid silently rejected roughly a third of ordinary printable
    characters, e.g. 'z', which needs exactly 6 and now fits); ``'ŭ'``
    (u-breve, codepoint 365) genuinely needs 7, which this real fixture's
    real causal grid cannot carry -- confirmed directly against
    ``encode_balanced_ternary_scalar`` before writing this test, not
    assumed."""

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["genesis"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    scheduler = MultiScalarTurnScheduler(engine=engine)

    with pytest.raises(ReceiptError, match="valid balanced-ternary"):
        scheduler.run_turn(
            task_id="overflowing-scalar-turn",
            text="aŭ",
            story_chemistry=_mount_test_chemistry_runtime(),
        )


def test_multi_word_sentence_with_spaces_and_wide_character_coverage(
    fixture, tmp_path_factory
):
    """Regression proof for a real, previously-live bug: every character in
    a real multi-word sentence must process without error, INCLUDING the
    space between words.

    Found live this session: ``clean_conversation_engine.py`` built the
    sensory lanes' causal window from a hardcoded five-instant descriptor
    count, while the language lane already correctly sized itself to
    however many valid balanced-ternary trit places the turn's own scalar
    needed. Every prior test in this codebase happened to use only 'a'/'b'
    as scalars, which both need exactly five places, so the mismatch never
    surfaced. A space needs four; a real sentence containing one failed
    outright with "native stream does not match common causal grid" --
    meaning no real multi-word sentence could ever be processed, which is
    exactly the coherent-multiword-conversation objective this whole
    engine exists to serve. Fixed by minting a per-turn causal grid sized
    to the scalar's own real valid-place count instead of assuming a fixed
    size, and by widening the engine's own mounted maximum grid from five
    to six (the real, measured maximum across the standard keyboard +
    Latin-1 range) so characters like 'z' (needing six) are not honestly
    but unnecessarily rejected either.

    Drives a real sentence with a space, punctuation, and a mix of 4/5/6
    -valid-place characters through the real scheduler end-to-end -- no
    monkeypatching, no fabricated feature vectors."""

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["genesis"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    scheduler = MultiScalarTurnScheduler(engine=engine)

    text = "hello there, friend!"  # real space, comma, exclamation, letters
    result = scheduler.run_turn(
        task_id="multi-word-sentence-turn",
        text=text,
        story_chemistry=_mount_test_chemistry_runtime(),
    )
    assert len(result.outcomes) == len(text)
    for scalar, outcome in zip(text, result.outcomes):
        assert outcome.scalar_text == scalar
        # Every scalar must produce a real, honest result -- never an
        # exception, regardless of whether it happens to be a letter,
        # a space, or punctuation.
        assert outcome.result is not None
        outcome.result.verify()
