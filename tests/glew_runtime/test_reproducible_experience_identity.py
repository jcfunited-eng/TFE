"""Real, non-monkeypatched proof for the reproducible-experience-identity fix
(design ``GL-SPC-REPRODUCIBLE-EXPERIENCE-IDENTITY-DESIGN-20260714-v3``).

The fix removed the request UUID's physical authority over sensory content:
``clean_conversation_engine._scene_descriptors`` no longer takes a ``task_id``
and returns a fixed, canonical "no real camera/mic attached this turn" reading
indexed by instant position only.  These tests drive the REAL production entry
path with two GENUINELY DIFFERENT request ids minted exactly the way
``app.py`` mints them (``f"cv_{tick}_{uuid4().hex[:8]}"`` -- a fresh ``uuid4``
per request, NEVER a test-chosen fixed string reused twice, which is precisely
the blind spot the design's section 9 calls out).

What is PROVEN here (all real, no monkeypatching):

* The fix works at the field level: two same-text turns under two different
  real request ids now produce a BIT-IDENTICAL numeric field (the quantity
  recognition actually operates on), while their receipt-identity naming
  correctly still differs (bookkeeping -- distinct moments).
* Growth is NOT degenerate under constant sensory: a genuinely new scalar
  still certifies a strictly-positive orthogonal residual and grows a new
  mode purely from the language lane (design section 7's load-bearing
  assumption -- the growth/distinctness direction HOLDS).  This is also
  proven by ``test_expression_mode_growth_arbiter.py`` continuing to pass
  under the fix.

What is HONESTLY DISPROVEN here (real evidence, not papered over):

* Making the field identical is NECESSARY but NOT SUFFICIENT for the live
  engine to RECOGNIZE a repeat.  Under the LIVE certified-residual arbiter
  (``clean_conversation_engine.py`` line ~880), the only path to
  ``RECOGNIZED`` for an in-span input is a certified-ZERO orthogonal residual,
  and the only way that residual is exactly zero is the exact-DAG-match branch
  (``expression_modes.py`` ``matching_mode_index``), which compares
  ``receipt_sha256``.  Because the design deliberately keeps ``task_id`` in the
  field expression's ``identity`` (receipt-identity bookkeeping, section 5),
  the second occurrence's receipt differs, ``matching_mode_index`` never fires,
  the numerically-computed residual straddles zero, and the turn resolves to
  ``AMBIGUOUS_SILENCE`` -- honest silence, but NOT the ``RECOGNIZED`` the
  reviewer's harm requires.  The fix is a strict improvement over the pre-fix
  random-sensory baseline (which manufactured a spurious ``NOVEL_SILENCE``
  growth for every repeat), but the true unblock for recognition-of-a-repeat
  is a reproducible field-expression identity (or a recognition-rule change),
  not this sensory fix alone.  These tests pin that real, measured behaviour so
  a future change that reaches ``RECOGNIZED`` fails them loudly (the safe
  direction) rather than a false claim silently standing.
"""

from __future__ import annotations

import uuid
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.certified_backend import load_pinned_flint
from dsf_ai_service.glew_runtime.clean_conversation_engine import (
    _CANONICAL_ABSENT_FILL_VALUE,
    _CANONICAL_ABSENT_VISUAL_SEED_BASE,
    _scene_descriptors,
)
from dsf_ai_service.glew_runtime.conversation import ConversationStatus
from dsf_ai_service.glew_runtime.expression_modes import (
    RECOGNITION_ARBITER_CERTIFIED_RESIDUAL,
    ExpressionRecognitionStatus,
    evaluate_expression_mode_boundary,
)
from dsf_ai_service.glew_runtime.expressions import evaluate_closed_experience_in_arb

# Reuse the real, proven, non-monkeypatched helpers and the module-scoped
# ``fixture`` (a genuinely bootstrapped rank-two engine world). Importing the
# fixture makes it resolvable by pytest in this module.
from tests.glew_runtime.test_clean_conversation_engine import (  # noqa: F401
    _build_engine,
    _build_mounted_runtime,
    _build_scene,
    _extend,
    _merge,
    _mode_payloads,
    _mount_test_chemistry_runtime,
    _new_generation_store,
    _turn,
    fixture,
)


def _ball_bound(mantissa: int, exponent: int) -> Fraction:
    """Exact value of a certified-ball mantissa*2**exponent, without the float
    overflow that ``mantissa * 2 ** exponent`` hits when a near-zero residual
    is represented with a huge mantissa and a large negative exponent."""

    if mantissa == 0:
        return Fraction(0)
    if exponent >= 0:
        return Fraction(mantissa * (2 ** exponent))
    return Fraction(mantissa, 2 ** (-exponent))


def _real_request_task_id() -> str:
    """A fresh request id minted exactly the way ``app.py`` mints one per real
    conversational turn (``app.py:2618``): ``f"cv_{tick}_{uuid4().hex[:8]}"``,
    a genuinely random UUID, unique for every request even for identical text.
    """

    tick = uuid.uuid4().int % 1_000_000
    return f"cv_{tick}_{uuid.uuid4().hex[:8]}"


def _field_repr(expression, *, precision_bits: int = 128) -> tuple[str, ...]:
    """The numeric field vector recognition actually operates on
    (``expression_modes.field`` = ``evaluate_closed_experience_in_arb``),
    rendered as exact per-component strings for bit-level comparison."""

    flint = load_pinned_flint()
    with flint.ctx.workprec(precision_bits):
        values = evaluate_closed_experience_in_arb(
            expression,
            flint=flint,
            precision_bits=precision_bits,
            hermitian_evaluators={},
        )
        return tuple(str(value) for value in values)


@pytest.fixture(scope="module")
def rank_two_world():
    """A real rank-two mode bank bootstrapped from two genuinely different real
    request ids (same 'a'/'b' genesis texts as production), so every recognition
    below runs against a real, non-toy bank -- the design's own G0/G2 bar."""

    mounted_runtime = _build_mounted_runtime()
    registry = _merge(
        _mount_test_chemistry_runtime().receipt_registry,
        mounted_runtime.receipt_registry,
    )

    root_expr, _, _, registry = _build_scene(
        mounted_runtime=mounted_runtime,
        task_id=_real_request_task_id(),
        text="a",
        chemistry_runtime=_mount_test_chemistry_runtime(),
        registry=registry,
    )
    content_expr, _, _, registry = _build_scene(
        mounted_runtime=mounted_runtime,
        task_id=_real_request_task_id(),
        text="b",
        chemistry_runtime=_mount_test_chemistry_runtime(),
        registry=registry,
    )

    r0 = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=mounted_runtime.expression_mode_bank,
        input_expression=root_expr,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(r0))
    r1 = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=r0.post_growth_bank,
        input_expression=content_expr,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(r1))

    # G0 (design section 7.4, the ratification gate): the genesis bootstrap
    # still grows rank 0 -> 2 under CONSTANT sensory -- the language lane alone
    # certifies "b" as an independent second basis mode against "a".
    assert r0.post_growth_bank.rank == 1
    assert r1.post_growth_bank.rank == 2

    return {
        "topology": mounted_runtime.field_topology,
        "mounted_runtime": mounted_runtime,
        "bank": r1.post_growth_bank,
        "root_expr": root_expr,
        "registry": registry,
    }


# --------------------------------------------------------------------------
# G4 -- the request id has no physical authority (machine-checkable, direct)
# --------------------------------------------------------------------------


def test_scene_descriptors_no_longer_accepts_a_task_id():
    """The request UUID cannot influence sensory content because it can no
    longer be passed at all: the signature dropped ``task_id`` entirely."""

    with pytest.raises(TypeError):
        _scene_descriptors("cv_1_deadbeef", count=5)  # type: ignore[call-arg]

    # And two independent calls of the same length are byte-identical.
    assert _scene_descriptors(count=5) == _scene_descriptors(count=5)


def test_canonical_absent_reading_is_the_zero_seed_of_the_old_formula():
    """The fixed canonical values are exactly what the old per-id SHA formula
    produced for a zero seed byte -- structure byte-identical, only the
    cross-request randomness removed."""

    descriptors = _scene_descriptors(count=5)
    assert _CANONICAL_ABSENT_FILL_VALUE == 0.15
    assert _CANONICAL_ABSENT_VISUAL_SEED_BASE == 10_000
    for index, descriptor in enumerate(descriptors):
        assert descriptor.visual_fill_value == 0.15
        assert descriptor.visual_seed == 10_000 + index * 257
        assert descriptor.auditory_born_tick == index * 100


# --------------------------------------------------------------------------
# G1 -- same text, two REAL distinct request ids => identical numeric field
# --------------------------------------------------------------------------


def test_same_text_two_real_request_ids_produce_identical_field_but_distinct_receipts(
    rank_two_world,
):
    """The headline of the fix: two byte-identical utterances arriving under two
    genuinely different real request ids now produce a BIT-IDENTICAL numeric
    field (what recognition operates on), while their receipt-identity naming
    correctly still differs (distinct moments -- bookkeeping)."""

    mounted_runtime = rank_two_world["mounted_runtime"]
    registry = rank_two_world["registry"]

    id_1 = _real_request_task_id()
    id_2 = _real_request_task_id()
    assert id_1 != id_2

    expr_1, _, _, registry = _build_scene(
        mounted_runtime=mounted_runtime,
        task_id=id_1,
        text="a",
        chemistry_runtime=_mount_test_chemistry_runtime(),
        registry=registry,
    )
    expr_2, _, _, registry = _build_scene(
        mounted_runtime=mounted_runtime,
        task_id=id_2,
        text="a",
        chemistry_runtime=_mount_test_chemistry_runtime(),
        registry=registry,
    )

    # Numeric field: BIT-IDENTICAL (the fix's real achievement).
    assert _field_repr(expr_1) == _field_repr(expr_2)

    # Receipt identity: correctly DIFFERENT (id-bearing bookkeeping, design
    # section 5 -- distinct moments carry distinct receipts).
    assert expr_1.receipt_sha256 != expr_2.receipt_sha256


# --------------------------------------------------------------------------
# G2 -- genuinely different text still grows, from the language lane alone
# --------------------------------------------------------------------------


def test_genuinely_different_text_grows_a_new_mode_from_language_alone(rank_two_world):
    """Growth is NOT degenerate under constant sensory (design section 7): a
    genuinely new scalar certifies strictly-positive out-of-span energy and
    grows a new mode -- driven purely by the language lane, since the five
    sensory lanes are now held constant across every turn."""

    mounted_runtime = rank_two_world["mounted_runtime"]
    novel_expr, _, _, registry = _build_scene(
        mounted_runtime=mounted_runtime,
        task_id=_real_request_task_id(),
        text="q",
        chemistry_runtime=_mount_test_chemistry_runtime(),
        registry=rank_two_world["registry"],
    )

    result = evaluate_expression_mode_boundary(
        topology=rank_two_world["topology"],
        bank=rank_two_world["bank"],
        input_expression=novel_expr,
        receipt_registry=registry,
        recognition_arbiter=RECOGNITION_ARBITER_CERTIFIED_RESIDUAL,
    )
    result.verify()
    assert result.status is ExpressionRecognitionStatus.NOVEL_SILENCE
    assert result.post_growth_bank.rank == 3
    assert result.mutation is True
    ball = result.certified_residual_energy
    lower = _ball_bound(ball.lower_mantissa, ball.lower_exponent)
    assert lower > 0  # certified strictly positive, not a threshold


# --------------------------------------------------------------------------
# The honest disproof -- a same-text repeat is NOT recognized under the live
# arbiter, it is AMBIGUOUS_SILENCE (necessary-but-not-sufficient).
# --------------------------------------------------------------------------


def test_same_text_repeat_under_live_arbiter_is_ambiguous_not_recognized_and_not_grown(
    rank_two_world,
):
    """Necessary-but-not-sufficient, proven with real numbers.

    A same-text repeat under a fresh real request id has a field IDENTICAL to
    the stored mode (proven above), so under the LIVE certified-residual
    arbiter it (correctly) does NOT manufacture a spurious NOVEL_SILENCE growth
    -- the strict improvement over the pre-fix random-sensory baseline.  But it
    also does NOT reach RECOGNIZED: the certified residual straddles zero (never
    exactly [0,0], because the exact-DAG-match ``matching_mode_index`` path
    needs an exact ``receipt_sha256`` match, which the fresh request id breaks),
    so the arbiter honestly returns AMBIGUOUS_SILENCE.  This is the real,
    located gap -- pinned here, not papered over.
    """

    mounted_runtime = rank_two_world["mounted_runtime"]

    # A fresh-request-id turn of the SAME text as the stored root mode "a".
    repeat_expr, _, _, registry = _build_scene(
        mounted_runtime=mounted_runtime,
        task_id=_real_request_task_id(),
        text="a",
        chemistry_runtime=_mount_test_chemistry_runtime(),
        registry=rank_two_world["registry"],
    )

    # Its field is identical to the stored root mode (fresh id, same text).
    assert _field_repr(repeat_expr) == _field_repr(rank_two_world["root_expr"])
    # But its receipt differs (so matching_mode_index cannot fire).
    assert repeat_expr.receipt_sha256 != rank_two_world["root_expr"].receipt_sha256

    result = evaluate_expression_mode_boundary(
        topology=rank_two_world["topology"],
        bank=rank_two_world["bank"],
        input_expression=repeat_expr,
        receipt_registry=registry,
        recognition_arbiter=RECOGNITION_ARBITER_CERTIFIED_RESIDUAL,
    )
    result.verify()

    # Honest silence, NOT recognition, and crucially NOT a spurious growth.
    assert result.status is ExpressionRecognitionStatus.AMBIGUOUS_SILENCE
    assert result.winner_mode_index is None
    assert result.mutation is False
    assert result.post_growth_bank.rank == 2  # no spurious mode manufactured

    # The certified residual straddles zero: not certified-positive (so no
    # growth) and not certified-zero (so no RECOGNIZED).
    ball = result.certified_residual_energy
    lower = _ball_bound(ball.lower_mantissa, ball.lower_exponent)
    upper = _ball_bound(ball.upper_mantissa, ball.upper_exponent)
    assert lower < 0 < upper


def test_end_to_end_fresh_id_repeat_through_real_engine_stays_silent_without_growth(
    fixture, tmp_path_factory
):
    """Highest-fidelity confirmation, end-to-end through the REAL
    ``ProductionCleanConversationEngine.run_clean_conversation``.

    ``test_clean_conversation_engine.test_real_end_to_end_commit_and_learn_no_
    monkeypatching`` commits+learns ONLY because it reuses ``fixture[
    "root_task_id"]`` verbatim (the exact-DAG-match shortcut).  Real live
    traffic never reuses an id.  Driving the SAME text under a FRESH real
    request id -- what production actually does -- the engine recognizes at the
    field level but the live certified-residual arbiter returns
    AMBIGUOUS_SILENCE, so no commit and no learn occur, and (unlike the pre-fix
    random-sensory baseline) no spurious mode is grown.
    """

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    rank_before = engine._mode_bank.rank

    # Same text "a" as the learned root scene, but a genuinely fresh request id.
    turn = _turn(_real_request_task_id(), "a")
    result = engine.run_clean_conversation(
        turn=turn, story_chemistry=_mount_test_chemistry_runtime()
    )
    result.verify()

    # Recognition ran for real, but no commit / no learn happened -- the engine
    # has a dedicated status for exactly this: the certified-residual arbiter
    # returned ambiguous silence for the fresh-id repeat, so there is no
    # RECOGNIZED mode to commit against.
    assert result.recognition_receipt_sha256 is not None
    assert result.status is ConversationStatus.EXPLICIT_NO_COMMIT_SILENCE
    assert result.reason == "recognition_ambiguous_silence"
    assert result.commit_receipt_sha256 is None
    assert result.initial_event_receipt_sha256 is None
    assert result.silent

    # No spurious mode was manufactured for the repeat (the real improvement
    # over the pre-fix random-sensory baseline, which grew one per repeat).
    assert engine._mode_bank.rank == rank_before
