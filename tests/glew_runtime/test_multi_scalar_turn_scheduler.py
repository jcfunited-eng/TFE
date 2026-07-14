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


def test_multi_scalar_turn_first_scalar_grows_a_new_mode_and_stays_silent(
    fixture, tmp_path_factory
):
    """Re-pinned for owner Requirement 1 (certified-residual growth arbiter).

    Under the pre-Requirement-1 winner-take-all dominance rule, a genuinely
    new one-scalar scene was RECOGNIZED as one of the two bootstrap modes and
    committed (the old premise of this test).  The recognition boundary now
    makes the certified orthogonal residual against the whole existing basis
    the arbiter: a scalar carrying genuine energy outside every existing mode
    GROWS a new mode and stays novel-silent instead of being absorbed.

    So this fixture's genuinely new scalar 'q' no longer commits -- it grows a
    third mode and returns honest ``NOVEL_SILENCE``.  Its real recognition
    still ran (proving the real per-scalar sensory/expression pipeline
    executed), no commit or learn occurred, and no checkpoint generation was
    persisted."""

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    rank_before = engine._mode_bank.rank
    scheduler = MultiScalarTurnScheduler(engine=engine)

    result = scheduler.run_turn(
        task_id="multi-scalar-grow-turn",
        text="q",
        story_chemistry=fixture["root_chemistry"],
    )

    assert len(result.outcomes) == 1
    outcome = result.outcomes[0]
    assert outcome.scalar_index == 0
    assert outcome.scalar_text == "q"
    outcome.result.verify()
    # Real recognition genuinely ran, but the certified out-of-span residual
    # grew a new mode and stayed silent: no commit, no learn.
    assert outcome.result.recognition_receipt_sha256 is not None
    assert outcome.result.commit_receipt_sha256 is None
    assert outcome.result.initial_event_receipt_sha256 is None
    assert not outcome.committed
    assert outcome.silent
    assert outcome.result.status is ConversationStatus.EXPLICIT_NO_COMMIT_SILENCE
    assert "novel_silence" in outcome.result.reason
    assert result.any_commit is False
    assert result.committed_scalar_indices == ()

    # The novel scalar grew a genuinely new mode (Requirement 1) ...
    assert engine._mode_bank.rank == rank_before + 1
    # ... and, because nothing committed or learned, no new checkpoint
    # generation was persisted.
    assert not (generation_store.root / "CURRENT").exists()


def test_multi_scalar_turn_novel_scalars_each_grow_their_own_mode_and_stay_silent(
    fixture, tmp_path_factory
):
    """Re-pinned for owner Requirement 1 (certified-residual growth arbiter).

    Under the pre-Requirement-1 winner-take-all rule this fixture's two novel
    scalars were each RECOGNIZED as an existing mode and committed, and the
    SECOND then hit the one-successor-per-mode wall -- the exact class of fault
    the live "hello there" turn hit.  With the certified-residual arbiter, each
    genuinely new scalar instead carries certified energy outside every
    existing mode, so each GROWS its own new mode and stays novel-silent.

    Running two novel scalars ('q', then 'p') in real sequence on the same
    engine therefore grows the mode bank by exactly two, commits neither, and
    stays honestly silent throughout -- no exhaustion wall, no raised error, no
    fabricated content.  The scheduler reports the engine's real per-scalar
    results verbatim."""

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    rank_before = engine._mode_bank.rank
    scheduler = MultiScalarTurnScheduler(engine=engine)

    result = scheduler.run_turn(
        task_id="multi-scalar-grow-turn",
        text="qp",
        story_chemistry=fixture["root_chemistry"],
    )

    assert len(result.outcomes) == 2
    for outcome in result.outcomes:
        outcome.result.verify()
        # Each novel scalar's recognition genuinely ran, grew a new mode, and
        # stayed silent: no commit, no learn.
        assert outcome.result.recognition_receipt_sha256 is not None
        assert not outcome.committed
        assert outcome.silent
        assert outcome.result.status is (
            ConversationStatus.EXPLICIT_NO_COMMIT_SILENCE
        )
        assert "novel_silence" in outcome.result.reason
        assert outcome.result.visible_text == ""

    # Each of the two genuinely novel scalars grew its own new mode
    # (Requirement 1), so the bank grew by exactly two -- no exhaustion wall.
    assert engine._mode_bank.rank == rank_before + 2
    assert result.any_commit is False
    assert result.committed_scalar_indices == ()
    assert result.all_silent is True
    # Nothing committed or learned, so no checkpoint generation was persisted.
    assert not (generation_store.root / "CURRENT").exists()


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
