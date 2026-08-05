"""Real multi-scalar turn scheduler (section 9.3's "typed-language turn
scheduler" -- ``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-
20260713-v1.md``).

Why this module exists
-----------------------
``ProductionCleanConversationEngine.run_clean_conversation``
(``clean_conversation_engine.py``) can only process exactly one Unicode
scalar of text per call -- its own ``_build_turn_expression`` rejects any
turn whose ``text`` is not length 1 (see that module's docstring, "One real
language scalar per turn"). Real conversational text is never one scalar
long, so something has to turn a real, multi-character turn into a sequence
of real one-scalar calls. Section 9.3 names that authority the "multi-scalar
turn scheduler." This module is that authority. It does not modify
``ProductionCleanConversationEngine`` or ``real_experience_learning_pipeline.py``
in any way -- it only calls their already-real, already-committed public
surface, once per scalar.

The structural question this module had to answer first
-----------------------------------------------------------
Before writing a scheduler, it had to be settled whether "one scalar per
causal-window tick" is a genuine, unavoidable physical fact of the
typed-language kernel binding, or an arbitrary simplification Step 4 made
that a scheduler could instead relax directly. It is the latter, for a
narrow reason, and the former for a different, real reason -- both
confirmed directly against the code, not assumed:

* ``language.py``'s own ``TypedLanguageEvent``/``capture_typed_language``/
  ``build_typed_language_frozen_kernel_input`` already fully support
  arbitrarily many Unicode scalars in ONE typed-language event.
  ``TypedLanguageEvent.from_text`` already loops
  ``for scalar_index, scalar in enumerate(normalized_text)``, encoding each
  character's own 14 balanced-ternary trit places independently (see
  ``BalancedTrit.scalar_index``); ``capture_typed_language`` and
  ``TypedLanguageEvent.__post_init__`` already require nothing more than
  "one strictly-increasing source timestamp per valid trit, across however
  many characters." Nothing in ``language.py`` itself limits an event to one
  scalar.
* ``real_experience_learning_pipeline._build_typed_language_lane`` -- the
  thin, Step-4-only wrapper ``clean_conversation_engine.py`` actually calls
  -- is what hard-codes ``if len(text) != 1: raise ReceiptError(...)``, and
  then derives its ``trits``/``valid_times`` via
  ``encode_balanced_ternary_scalar(ord(text))``: a call that only works at
  all because ``ord()`` itself requires exactly one character, not because
  any deeper law requires it. This is an arbitrary (if reasonable) Step-4
  simplification: generalizing it to loop over every character with its own
  ``scalar_index``, exactly the way ``TypedLanguageEvent.from_text`` already
  does internally, would not violate anything in ``language.py``.
* The one place a REAL, unavoidable structural floor does exist is the
  shared causal grid: every valid trit -- across however many scalars share
  one causal window -- needs its own, later timestamp, and the number of
  timestamps in one causal grid is finite. ``clean_conversation_engine.py``
  enforces this directly (``_build_turn_expression``: ``valid_count >
  len(self._mounted_runtime.causal_grid.timestamps)`` fails closed), and
  both that module and ``real_experience_learning_pipeline.py`` size their
  grids at exactly five timestamps specifically because "the typed-language
  scalar's real balanced-ternary encoding needs up to five valid trit
  places" for one scalar (see both modules' own docstrings) -- a deliberate
  sizing choice tied to hosting ONE scalar, not a fixed law of the universe
  that a grid can never be larger. Fitting N scalars' worth of valid trits
  into that same, single, five-instant scene would require enlarging the
  shared grid (and therefore the shared five-sense scene) to match -- a
  much larger, riskier change to already-committed sense-evolution sizing,
  out of this module's scope and unnecessary for what section 9.3 actually
  asks for.

Given that, the structurally correct way to process a real multi-character
turn -- without touching either already-committed module -- is not to
relax ``_build_typed_language_lane``'s guard at all. It is to run N
genuinely independent one-scalar causal windows in strict causal order,
each through the engine's own real, unmodified ``run_clean_conversation``
entry point. This module confirmed directly (see
``real_experience_learning_pipeline.py``'s own two-scene bootstrap in
``learn_one_real_multimodal_expression``, and
``test_clean_conversation_engine.py``'s own fixture, which independently
mounts a distinct ``StoryChemistryRuntime`` per scene) that this is exactly
how this codebase already treats "one scene" today: nothing anywhere
threads an evolved sensory boundary state from one scene into the next --
each scene, everywhere in this codebase, starts from an externally supplied
``StoryChemistryRuntime`` and is judged entirely on its own. This module
follows that same, already-established precedent for each scalar's own
scene, rather than inventing a chaining mechanism the substrate does not
actually have (see "The story-chemistry gap" below).

Why calling the engine once per scalar is structurally correct, not a
workaround
------------------------------------------------------------------------
``commit.py``'s real fail-closed commit boundary is defined per causal
window: every commit-eligible turn independently supplies its own
recognition, its own L6 evaluation, its own event support, and so on, and
``run_clean_conversation_transaction`` decides -- for that one window --
whether to commit. There is no real notion anywhere in this codebase of
"partial commit" spanning only some trit-places of a longer utterance;
commit is already, by design, an all-or-nothing verdict over one causal
window. So the only way to give each real Unicode scalar its own honest
commit opportunity is to give each one its own causal window -- which is
exactly what calling ``run_clean_conversation`` once per scalar produces,
using the engine's own real, unmodified recognition/commit/learn machinery
every time. This module never re-evaluates recognition or commit itself,
never fabricates a ``ConversationTransactionResult``, and never learns
anything on the engine's behalf.

What genuinely evolves from one scalar to the next within one turn
------------------------------------------------------------------------
``ProductionCleanConversationEngine`` is constructed once and its
``self._mode_bank``/``self._learned_state``/``self._registry`` persist
across calls (see ``clean_conversation_engine.py``'s own
``_run_locked``/``_learn_and_persist``). Because this scheduler always
calls ``run_clean_conversation`` on the SAME engine instance, in real causal
order, every scalar after the first genuinely sees the real accumulated
effect of every earlier scalar in this turn: mode-bank growth folded back in
after recognition, and any real commit's learned binding folded back in
before the next scalar's own recognition is even evaluated. That
accumulation is real and load-bearing, not fabricated by this scheduler --
it already happens with any two separate real turns, and happens here
because these calls are, honestly, just separate real turns run in
sequence.

The story-chemistry gap (an honest, confirmed, pre-existing limitation --
not invented here)
------------------------------------------------------------------------
``StoryChemistryRuntime`` (``story_chemistry.py``) is an immutable value.
``real_experience_learning_pipeline._evolve_real_causal_window`` internally
chains it across one scene's own instants (``current_runtime =
evolved.runtime``), but returns only the resulting ``StoryFrozenKernelInputs``
bridge -- never the advanced runtime itself. ``story_chemistry.
build_story_frozen_kernel_inputs`` (the function that bridge comes from)
carries no runtime field either. So there is no path, anywhere in this
codebase today, for a caller to recover the sensory state a scene's own five
instants evolved into, let alone feed it into the next scene. Confirming
this is not a gap this scheduler introduces: ``learn_one_real_multimodal_
expression``'s own two real scenes ("root", "content") each mount their own,
independent ``StoryChemistryRuntime``; ``test_clean_conversation_engine.py``'s
own fixture does the same. No real code path anywhere threads chemistry
state between scenes. Consistent with that existing, already-committed
design, this scheduler passes one caller-supplied ``StoryChemistryRuntime``
to every scalar's call -- the same single per-call argument
``CleanConversationEngine.run_clean_conversation``'s own Protocol already
requires -- rather than fabricating a chaining mechanism that does not
exist. Each scalar's own five sensed instants therefore genuinely start
fresh from that same externally supplied boundary state; only the engine's
own cognitive state (mode bank, learned bindings, receipt registry) is what
genuinely carries forward scalar to scalar. A caller who does want each
scalar to start from a distinct sensory boundary state may already do so
today, with no change to this module, by supplying a different, independently
mounted ``StoryChemistryRuntime`` for the whole turn versus another turn --
exactly the granularity this codebase already supports.

No fabricated single answer for a turn
------------------------------------------
A real multi-character turn may contain scalars that each land on a
genuinely different, honest outcome: one may commit, another may stay typed
silence, a third may release its own real recognized visible text. This
module never blends those into one invented sentence. ``MultiScalarTurnResult``
reports every real per-scalar ``ConversationTransactionResult`` verbatim,
plus honestly derived (never fabricated) aggregate facts.
"""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

from .conversation import ConversationTransactionResult
from .conversation_service import (
    CleanConversationEngine,
    CleanConversationTurn,
    clean_conversation_turn_receipt_payload,
)
from .model import ReceiptError, receipt_sha256, require_identifier
from .story_chemistry import StoryChemistryRuntime


@runtime_checkable
class _TurnSerializingEngine(Protocol):
    """An engine that can serialize a WHOLE turn against its own single shared
    learned state.

    This is a narrow, optional capability kept deliberately separate from the
    ``CleanConversationEngine`` Protocol so adding it never changes that
    Protocol's ``isinstance`` contract for the unrelated engine doubles other
    modules inject. ``ProductionCleanConversationEngine.serialize_turn``
    provides it; any engine that does not is simply run without turn-level
    serialization (a ``nullcontext``).
    """

    def serialize_turn(self) -> AbstractContextManager: ...


def default_scalar_task_id(task_id: str, index: int) -> str:
    """The default, deterministic per-scalar task id this scheduler derives
    when a caller does not supply an explicit override: exposed publicly so
    a caller (or a test replaying an already-committed scene's exact
    identity) can predict or reproduce it without duplicating this format
    string."""

    require_identifier(task_id, "multi-scalar turn task_id")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ReceiptError("multi-scalar turn scalar index must be a nonnegative integer")
    return f"{task_id}-scalar-{index:04d}"


@dataclass(frozen=True, slots=True)
class ScalarTurnOutcome:
    """Exactly what one real call to ``run_clean_conversation`` produced for
    one real Unicode scalar of this turn's text, in this turn's own real
    causal order. Never synthesized -- ``result`` is the real, unmodified,
    self-verifying ``ConversationTransactionResult`` the engine itself
    returned for this scalar's own real causal window."""

    scalar_index: int
    scalar_text: str
    scalar_task_id: str
    result: ConversationTransactionResult

    def __post_init__(self) -> None:
        if (
            isinstance(self.scalar_index, bool)
            or not isinstance(self.scalar_index, int)
            or self.scalar_index < 0
        ):
            raise ReceiptError(
                "multi-scalar turn scalar_index must be a nonnegative integer"
            )
        if not isinstance(self.scalar_text, str) or len(self.scalar_text) != 1:
            raise ReceiptError(
                "multi-scalar turn scalar_text must be exactly one Unicode scalar"
            )
        require_identifier(self.scalar_task_id, "multi-scalar turn scalar_task_id")
        if not isinstance(self.result, ConversationTransactionResult):
            raise ReceiptError(
                "multi-scalar turn scalar outcome requires a real typed "
                "conversation result"
            )

    @property
    def committed(self) -> bool:
        """True iff THIS scalar's own real call produced a genuine full-field
        commit. ``conversation.py`` populates
        ``initial_event_receipt_sha256`` only after
        ``commit.status is CommitStatus.COMMIT`` (see
        ``clean_conversation_engine.py``'s own module docstring, point 7) --
        the same already-public, already-honest signal that module already
        relies on, reused here rather than re-derived."""

        return self.result.initial_event_receipt_sha256 is not None

    @property
    def silent(self) -> bool:
        return self.result.silent


@dataclass(frozen=True, slots=True)
class MultiScalarTurnResult:
    """The one real, aggregate report for a whole multi-character turn:
    every real per-scalar ``ScalarTurnOutcome`` this turn produced, in real
    causal order, plus honest, derived-not-fabricated aggregate facts. This
    is never a single blended response -- see the module docstring, "No
    fabricated single answer for a turn"."""

    task_id: str
    text: str
    outcomes: tuple[ScalarTurnOutcome, ...]

    def __post_init__(self) -> None:
        require_identifier(self.task_id, "multi-scalar turn task_id")
        if not isinstance(self.text, str) or not self.text:
            raise ReceiptError("multi-scalar turn requires nonempty text")
        if not isinstance(self.outcomes, tuple) or not self.outcomes:
            raise ReceiptError(
                "multi-scalar turn requires at least one real per-scalar outcome"
            )
        if len(self.outcomes) != len(self.text):
            raise ReceiptError(
                "multi-scalar turn outcome count must equal this turn's own "
                "Unicode scalar count"
            )
        task_ids = []
        for index, (expected_scalar, outcome) in enumerate(zip(self.text, self.outcomes)):
            if outcome.scalar_index != index:
                raise ReceiptError(
                    "multi-scalar turn outcomes are not in real causal order"
                )
            if outcome.scalar_text != expected_scalar:
                raise ReceiptError(
                    "multi-scalar turn outcome scalar_text differs from this "
                    "turn's own text at that position"
                )
            task_ids.append(outcome.scalar_task_id)
        if len(set(task_ids)) != len(task_ids):
            raise ReceiptError(
                "multi-scalar turn outcomes must have distinct scalar_task_ids"
            )

    @property
    def any_commit(self) -> bool:
        """Honest aggregate: did ANY scalar in this turn produce a real
        full-field commit? See ``committed_scalar_indices`` for exactly
        which ones, and ``outcomes`` for every real per-scalar result --
        this property never stands in for that detail."""

        return any(outcome.committed for outcome in self.outcomes)

    @property
    def committed_scalar_indices(self) -> tuple[int, ...]:
        return tuple(outcome.scalar_index for outcome in self.outcomes if outcome.committed)

    @property
    def all_silent(self) -> bool:
        return all(outcome.silent for outcome in self.outcomes)

    @property
    def visible_scalar_texts(self) -> tuple[str, ...]:
        """Every scalar whose OWN real result actually released visible
        text, reported individually in real causal order -- never
        concatenated into one invented sentence. Zero, one, or many entries
        are all honest outcomes."""

        return tuple(
            outcome.result.visible_text for outcome in self.outcomes if not outcome.silent
        )


class MultiScalarTurnScheduler:
    """Drives a real multi-character turn through a real
    ``CleanConversationEngine`` one Unicode scalar at a time, in real causal
    order, using exclusively that engine's own real, unmodified
    ``run_clean_conversation`` entry point (see module docstring for why
    this is structurally correct, not a workaround).

    This scheduler owns no cognition, no recognition rule, and no commit
    rule of its own -- it only sequences real per-scalar calls and reports
    every real result honestly.
    """

    def __init__(self, *, engine: CleanConversationEngine) -> None:
        if not isinstance(engine, CleanConversationEngine):
            raise ReceiptError(
                "multi-scalar turn scheduler requires a real CleanConversationEngine"
            )
        self._engine = engine

    def run_turn(
        self,
        *,
        task_id: str,
        text: str,
        story_chemistry: StoryChemistryRuntime,
        source: str = "multi-scalar-turn",
        scalar_task_ids: Sequence[str] | None = None,
    ) -> MultiScalarTurnResult:
        """Process ``text`` as a real, ordered sequence of one-scalar turns.

        ``story_chemistry`` is the one real, externally-mounted sensory
        boundary state supplied to every scalar's own call (see module
        docstring, "The story-chemistry gap" -- there is no real mechanism
        anywhere in this codebase to chain an evolved sensory runtime from
        one scene into the next, so this scheduler does not fabricate one).

        ``scalar_task_ids``, when supplied, must have exactly one entry per
        Unicode scalar in ``text`` and every entry must be distinct; this
        lets a caller reproduce an already-committed scene's exact task
        identity for one or more scalars (for example, to replay a scalar
        that was already proven to commit under a specific task id and
        chemistry state). When omitted, each scalar's task id is
        ``default_scalar_task_id(task_id, index)``.
        """

        require_identifier(task_id, "multi-scalar turn task_id")
        if not isinstance(text, str) or not text:
            raise ReceiptError("multi-scalar turn requires nonempty text")
        if not isinstance(story_chemistry, StoryChemistryRuntime):
            raise ReceiptError(
                "multi-scalar turn scheduler requires a real mounted story "
                "chemistry runtime"
            )
        if scalar_task_ids is None:
            resolved_task_ids = tuple(
                default_scalar_task_id(task_id, index) for index in range(len(text))
            )
        else:
            resolved_task_ids = tuple(scalar_task_ids)
            if len(resolved_task_ids) != len(text):
                raise ReceiptError(
                    "multi-scalar turn scalar_task_ids must have exactly one "
                    "entry per Unicode scalar in text"
                )
            for candidate in resolved_task_ids:
                require_identifier(candidate, "multi-scalar turn scalar_task_id")
            if len(set(resolved_task_ids)) != len(resolved_task_ids):
                raise ReceiptError(
                    "multi-scalar turn scalar_task_ids must be distinct"
                )

        # Turn-level serialization (Fix 1). The engine's own lock serializes
        # individual SCALARS, not whole turns: two overlapping ``/converse``
        # requests each call ``run_turn`` on the SAME shared engine through
        # app.py's lifecycle executor, and without a turn mutex their scalars
        # interleave against that engine's single shared learned state, letting
        # one turn's end-of-turn deferred flush durably commit ANOTHER turn's
        # mid-turn, in-flight learns. Holding the engine's turn mutex for the
        # whole scalar sequence makes turns fully serial -- architecture-
        # consistent for a system that deliberately speaks with one mouth, one
        # conversation turn at a time -- so each turn's single deferred flush
        # covers exactly its own learns. The mutex lives on the ENGINE (not on
        # this scheduler instance), so two schedulers wrapping the same engine
        # still serialize. Engines without the capability run unchanged.
        if isinstance(self._engine, _TurnSerializingEngine):
            turn_guard: AbstractContextManager = self._engine.serialize_turn()
        else:
            turn_guard = nullcontext()

        outcomes: list[ScalarTurnOutcome] = []
        with turn_guard:
            for index, scalar in enumerate(text):
                outcomes.append(
                    self._run_one_scalar(
                        index=index,
                        scalar=scalar,
                        total=len(text),
                        scalar_task_id=resolved_task_ids[index],
                        story_chemistry=story_chemistry,
                        source=source,
                    )
                )

        return MultiScalarTurnResult(task_id=task_id, text=text, outcomes=tuple(outcomes))

    def _run_one_scalar(
        self,
        *,
        index: int,
        scalar: str,
        total: int,
        scalar_task_id: str,
        story_chemistry: StoryChemistryRuntime,
        source: str,
    ) -> ScalarTurnOutcome:
        """Run exactly one real Unicode scalar of a turn through the engine's
        own unmodified ``run_clean_conversation`` and wrap its real, unmodified
        result. Called only from inside :meth:`run_turn`'s turn-serialization
        guard, in real causal order; owns no cognition, recognition, or commit
        rule of its own."""

        payload = clean_conversation_turn_receipt_payload(
            task_id=scalar_task_id, text=scalar, source=source
        )
        turn = CleanConversationTurn(
            task_id=scalar_task_id,
            text=scalar,
            source=source,
            receipt_sha256=receipt_sha256(payload),
            receipt_payload=payload,
        )
        turn.verify()
        # The one real, non-fabricated end-of-message fact this scheduler
        # already knows structurally: whether this is the LAST real Unicode
        # scalar of the real per-request message. It is threaded to the
        # engine so that, per design section 12, the final scalar of a
        # committing turn closes the accumulated expression (making it
        # emittable at exact close) while every earlier scalar keeps
        # accumulating. This is a true fact about where the real message
        # ends -- not a guess about semantic completeness, and not invented
        # content. The scheduler owns no cognition here: it only reports the
        # real index; the engine owns whether a close actually happens (only
        # if the final scalar genuinely committed).
        is_final_scalar = index == total - 1
        # ``defer_persistence=True`` is the second real, structural fact
        # this scheduler owns (utterance-transaction Milestone 1): these N
        # one-scalar calls are ONE real per-request turn, so their durable
        # store commit is batched -- every scalar still learns for real,
        # per scalar, in memory (all receipt mechanisms unchanged), and
        # the engine fires exactly one ImmutableGenerationStore commit at
        # this turn's final scalar iff any scalar changed learned state.
        # A death mid-turn leaves the store at the pre-turn generation
        # (the deferred turn performs no store write before its single
        # flush), which is the store's own atomic-commit contract extended
        # to the whole turn. Single-scalar callers that bypass this
        # scheduler keep the historical commit-immediately behaviour
        # (the engine's parameter defaults to False).
        result = self._engine.run_clean_conversation(
            turn=turn,
            story_chemistry=story_chemistry,
            is_final_scalar=is_final_scalar,
            defer_persistence=True,
        )
        if not isinstance(result, ConversationTransactionResult):
            raise ReceiptError(
                "clean conversation engine returned an untyped result for "
                f"scalar {index} of a real multi-scalar turn"
            )
        result.verify()
        return ScalarTurnOutcome(
            scalar_index=index,
            scalar_text=scalar,
            scalar_task_id=scalar_task_id,
            result=result,
        )


__all__ = (
    "MultiScalarTurnResult",
    "MultiScalarTurnScheduler",
    "ScalarTurnOutcome",
    "default_scalar_task_id",
)
