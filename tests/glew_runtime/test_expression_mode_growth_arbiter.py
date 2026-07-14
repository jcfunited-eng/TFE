"""Direct, non-monkeypatched proof of the owner-Requirement-1 certified-residual
growth/recognition arbiter (design ``GL-SPC-MODE-GROWTH-AND-SUCCESSOR-KEYING-
DESIGN-20260714-v2`` section 8, test G1).

Every object here is real: a genuinely mounted six-lane runtime, a mode bank
genuinely bootstrapped to rank two through the real six-lane pipeline (reusing
``test_clean_conversation_engine``'s own proven helpers, never re-implemented),
and real full-field ``ClosedExperienceFieldExpression`` inputs.  Nothing
monkeypatches recognition or growth.

The proof is a same-input contrast: one genuinely novel scene is evaluated
against the identical rank-two bank under both arbiters.

* ``RECOGNITION_ARBITER_CERTIFIED_RESIDUAL`` (live conversation): the scene
  carries certified energy outside every existing mode, so it GROWS a new mode
  and stays ``NOVEL_SILENCE`` instead of being misrecognized.
* ``RECOGNITION_ARBITER_INTERVAL_DOMINANCE`` (legacy nearest-reference): the
  same scene is absorbed as whichever existing mode uniquely dominates.

An exact repeat recognizes its own mode with no growth under the new arbiter,
so within-span/exact-repeat recognition is preserved.
"""

from __future__ import annotations

import pytest

from dsf_ai_service.glew_runtime.expression_modes import (
    RECOGNITION_ARBITER_CERTIFIED_RESIDUAL,
    RECOGNITION_ARBITER_INTERVAL_DOMINANCE,
    ExpressionRecognitionStatus,
    evaluate_expression_mode_boundary,
)

from tests.glew_runtime.test_clean_conversation_engine import (
    _build_mounted_runtime,
    _build_scene,
    _extend,
    _merge,
    _mode_payloads,
    _mount_test_chemistry_runtime,
)


@pytest.fixture(scope="module")
def rank_two_world():
    """A real rank-two mode bank plus the receipts to recognize against it."""

    mounted_runtime = _build_mounted_runtime()
    root_chemistry = _mount_test_chemistry_runtime()
    content_chemistry = _mount_test_chemistry_runtime()
    registry = _merge(root_chemistry.receipt_registry, mounted_runtime.receipt_registry)

    root_expression, _, _, registry = _build_scene(
        mounted_runtime=mounted_runtime,
        task_id="arbiter-root",
        text="a",
        chemistry_runtime=root_chemistry,
        registry=registry,
    )
    content_expression, _, _, registry = _build_scene(
        mounted_runtime=mounted_runtime,
        task_id="arbiter-content",
        text="b",
        chemistry_runtime=content_chemistry,
        registry=registry,
    )

    empty_bank = mounted_runtime.expression_mode_bank
    root_growth = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=empty_bank,
        input_expression=root_expression,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(root_growth))
    content_growth = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=root_growth.post_growth_bank,
        input_expression=content_expression,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(content_growth))
    grown_bank = content_growth.post_growth_bank
    assert grown_bank.rank == 2

    novel_chemistry = _mount_test_chemistry_runtime()
    novel_expression, _, _, registry = _build_scene(
        mounted_runtime=mounted_runtime,
        task_id="arbiter-novel",
        text="q",
        chemistry_runtime=novel_chemistry,
        registry=registry,
    )

    return {
        "topology": mounted_runtime.field_topology,
        "bank": grown_bank,
        "root_expression": root_expression,
        "novel_expression": novel_expression,
        "registry": registry,
    }


def test_certified_positive_residual_grows_a_new_mode_and_stays_novel_silent(rank_two_world):
    """G1(a): a genuinely novel scene with certified out-of-span energy grows a
    new mode and stays ``NOVEL_SILENCE`` under the certified-residual arbiter --
    regardless of which existing mode's activation was numerically larger."""

    result = evaluate_expression_mode_boundary(
        topology=rank_two_world["topology"],
        bank=rank_two_world["bank"],
        input_expression=rank_two_world["novel_expression"],
        receipt_registry=rank_two_world["registry"],
        recognition_arbiter=RECOGNITION_ARBITER_CERTIFIED_RESIDUAL,
    )
    result.verify()
    assert result.status is ExpressionRecognitionStatus.NOVEL_SILENCE
    assert result.winner_mode_index is None
    assert result.post_growth_bank.rank == 3
    assert result.mutation is True
    # The growth is certified, not a threshold: the residual's certified lower
    # bound is strictly positive.
    lower = (
        result.certified_residual_energy.lower_mantissa
        * 2**result.certified_residual_energy.lower_exponent
    )
    assert lower > 0


def test_exact_repeat_recognizes_its_own_mode_without_growth(rank_two_world):
    """G1(b): an exact repeat certifies residual-zero, so it recognizes its own
    stored mode with no growth -- within-span/exact-repeat recognition is
    preserved by the new arbiter."""

    result = evaluate_expression_mode_boundary(
        topology=rank_two_world["topology"],
        bank=rank_two_world["bank"],
        input_expression=rank_two_world["root_expression"],
        receipt_registry=rank_two_world["registry"],
        recognition_arbiter=RECOGNITION_ARBITER_CERTIFIED_RESIDUAL,
    )
    result.verify()
    assert result.status is ExpressionRecognitionStatus.RECOGNIZED
    assert result.winner_mode_index is not None
    assert result.post_growth_bank.rank == 2
    assert result.mutation is False
    assert result.certified_residual_energy.lower_mantissa == 0
    assert result.certified_residual_energy.upper_mantissa == 0


def test_the_same_novel_scene_is_absorbed_by_the_legacy_dominance_arbiter(rank_two_world):
    """The arbiter parameter is load-bearing: the IDENTICAL novel scene that
    grows-and-stays-silent under the certified-residual arbiter is instead
    classified as an existing mode under the legacy interval-dominance arbiter
    (the nearest-reference rule sound voicing discrimination relies on).  This
    is exactly the misrecognition owner Requirement 1 removes for live
    experience."""

    certified = evaluate_expression_mode_boundary(
        topology=rank_two_world["topology"],
        bank=rank_two_world["bank"],
        input_expression=rank_two_world["novel_expression"],
        receipt_registry=rank_two_world["registry"],
        recognition_arbiter=RECOGNITION_ARBITER_CERTIFIED_RESIDUAL,
    )
    legacy = evaluate_expression_mode_boundary(
        topology=rank_two_world["topology"],
        bank=rank_two_world["bank"],
        input_expression=rank_two_world["novel_expression"],
        receipt_registry=rank_two_world["registry"],
        recognition_arbiter=RECOGNITION_ARBITER_INTERVAL_DOMINANCE,
    )
    certified.verify()
    legacy.verify()
    # Same input, same bank, genuinely different decision.
    assert certified.status is ExpressionRecognitionStatus.NOVEL_SILENCE
    assert legacy.status is ExpressionRecognitionStatus.RECOGNIZED
    assert legacy.winner_mode_index is not None
    assert legacy.winner_mode_index < rank_two_world["bank"].rank
