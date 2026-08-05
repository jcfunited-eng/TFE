from __future__ import annotations

import ast
import inspect
from fractions import Fraction

import tools.probe_causal_thing_full_field_invariant_walkup as module
from tools.probe_causal_thing_full_field_invariant_walkup import (
    AuditItem,
    _direction_word,
    _invariants,
    _route,
)


def _item(item_id: str) -> AuditItem:
    return AuditItem(
        item_id=item_id,
        oracle_command="audit-only",
        speaker_id=item_id,
        archive_member=f"{item_id}.wav",
        kind="grounded-training-variant",
        ordinal=1,
    )


def test_run_word_is_exactly_gain_invariant_but_retains_plateaus() -> None:
    source = (
        Fraction(1),
        Fraction(2),
        Fraction(3),
        Fraction(2),
        Fraction(1),
    )
    gained = tuple(value * 7 for value in source)
    slowed = (
        Fraction(1),
        Fraction(2),
        Fraction(2),
        Fraction(3),
        Fraction(3),
        Fraction(2),
        Fraction(2),
        Fraction(1),
    )
    assert _direction_word(source) == (1, -1)
    assert _direction_word(gained) == _direction_word(source)
    assert _direction_word(slowed) != _direction_word(source)


def test_exact_intersection_and_negative_space_fission_are_causal() -> None:
    a1, a2, b1, b2 = map(_item, ("a1", "a2", "b1", "b2"))
    shared = ("shared",)
    only_a = ("only-a",)
    only_b = ("only-b",)
    variants = {
        "a1": frozenset((shared, only_a, ("a-noise-1",))),
        "a2": frozenset((shared, only_a, ("a-noise-2",))),
        "b1": frozenset((shared, only_b, ("b-noise-1",))),
        "b2": frozenset((shared, only_b, ("b-noise-2",))),
    }
    invariants, shared_count = _invariants(
        {"thing-a": (a1, a2), "thing-b": (b1, b2)},
        variants,
    )
    assert shared_count == 1
    assert invariants == {
        "thing-a": frozenset((only_a,)),
        "thing-b": frozenset((only_b,)),
    }
    assert _route(
        invariants, frozenset((only_a, ("unrelated",)))
    ) == ("unique", ("thing-a",))
    assert _route(
        invariants, frozenset((("unrelated",),))
    ) == ("unresolved", ())


def test_empty_invariant_cannot_match_every_query_vacuously() -> None:
    assert _route(
        {"empty": frozenset(), "real": frozenset((("required",),))},
        frozenset((("other",),)),
    ) == ("unresolved", ())


def test_query_path_has_no_similarity_or_score_operation() -> None:
    tree = ast.parse(inspect.getsource(module))
    forbidden = {
        "argmax",
        "argmin",
        "corrcoef",
        "dot",
        "mean",
        "median",
        "norm",
        "polyfit",
    }
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    } | {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
    }
    assert not forbidden.intersection(called)
