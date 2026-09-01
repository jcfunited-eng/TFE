"""C-005 bounded causal evidence and one-timeline acoustic transport.

The retired layer-13/pre-drain tests that used to occupy this file described a
mechanism the organism no longer has.  These tests exercise the surviving
contracts: exact signed pressure composition, one authenticated native
advance, and bounded observer evidence for physical ordering and prediction.
"""

from __future__ import annotations

import struct
from types import SimpleNamespace

import pytest

from dsf_ai_service import native_production_app as production


def _acoustic_plan(external: tuple[int, ...]) -> production._AcousticHopPlan:
    return production._AcousticHopPlan(
        SimpleNamespace(occurrence_count=1),
        external,
        lambda composed: ("rebuilt", composed),
    )


def test_in_flight_acoustic_consequence_is_composed_once_with_exact_transport(
    monkeypatch,
) -> None:
    pressure = struct.pack("<3h", 7, -11, 13)
    body = struct.pack("<12h", *range(12))
    native_advance = lambda *_args: None
    organism = SimpleNamespace(
        in_flight_acoustic_source_tick=41,
        in_flight_acoustic_pressure_s16le=pressure,
        in_flight_acoustic_body_s16le=body,
        advance_in_flight_self_hearing_unsealed=native_advance,
    )
    admitted: dict[str, object] = {}

    def commit(_organism, episodes, intervals, **kwargs):
        admitted.update(episodes=episodes, intervals=intervals, kwargs=kwargs)
        return {"exact": "hop"}

    monkeypatch.setattr(production, "_commit_admitted_hop", commit)

    hop, audio = production._commit_one_timeline_hop(
        organism,
        _acoustic_plan((2, 3, 5)),
        ((1, 2),),
        purpose="coexisting-test",
        coexisting=True,
    )

    assert hop == {"exact": "hop"}
    assert audio is not None
    assert audio["pcm_s16le"] == pressure
    assert audio["organism_tick"] == 41
    assert audio["sample_count"] == 3
    assert audio["remaining_sample_count"] == 0
    assert admitted["episodes"] == ("rebuilt", (9, -8, 18))
    assert admitted["intervals"] == ((1, 2),)
    assert admitted["kwargs"] == {
        "purpose": "coexisting-test",
        "external_participant_action_receipt": None,
        "coexisting": True,
        "native_advance": native_advance,
        "native_advance_tail": (pressure, body, True, 3),
    }


def test_absent_in_flight_pressure_uses_the_authored_episode_once(monkeypatch) -> None:
    organism = SimpleNamespace(
        in_flight_acoustic_source_tick=None,
        in_flight_acoustic_pressure_s16le=None,
        in_flight_acoustic_body_s16le=None,
    )
    admitted: list[tuple[object, object, dict[str, object]]] = []

    def commit(_organism, episode, intervals, **kwargs):
        admitted.append((episode, intervals, kwargs))
        return {"exact": "ordinary"}

    monkeypatch.setattr(production, "_commit_admitted_hop", commit)
    plan = _acoustic_plan((2, 3, 5))
    hop, audio = production._commit_one_timeline_hop(
        organism,
        plan,
        ((1, 2),),
        purpose="ordinary-test",
    )

    assert hop == {"exact": "ordinary"}
    assert audio is None
    assert admitted == [
        (
            plan.episode,
            ((1, 2),),
            {
                "purpose": "ordinary-test",
                "external_participant_action_receipt": None,
                "coexisting": False,
            },
        )
    ]


def test_signed_pressure_overflow_refuses_before_native_advance(monkeypatch) -> None:
    pressure = struct.pack("<h", 1)
    organism = SimpleNamespace(
        in_flight_acoustic_source_tick=9,
        in_flight_acoustic_pressure_s16le=pressure,
        in_flight_acoustic_body_s16le=struct.pack("<4h", 0, 0, 0, 0),
        advance_in_flight_self_hearing_unsealed=lambda *_args: None,
    )
    called = False

    def commit(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(production, "_commit_admitted_hop", commit)

    with pytest.raises(ValueError, match="signed-16"):
        production._commit_one_timeline_hop(
            organism,
            _acoustic_plan((32_767,)),
            ((1, 1_000),),
            purpose="overflow-test",
        )
    assert called is False


def test_in_flight_transport_cardinality_mismatch_refuses() -> None:
    organism = SimpleNamespace(
        in_flight_acoustic_source_tick=9,
        in_flight_acoustic_pressure_s16le=struct.pack("<h", 1),
        in_flight_acoustic_body_s16le=None,
    )

    with pytest.raises(RuntimeError, match="lost cardinality"):
        production._commit_one_timeline_hop(
            organism,
            _acoustic_plan((0,)),
            ((1, 1_000),),
            purpose="cardinality-test",
        )


def test_frontier_evidence_keeps_only_current_and_preceding_distinct_sets() -> None:
    first = (("01" * 16, 5, 0, "02" * 16, 8, 0, 0, 1),)
    second = (("01" * 16, 5, 0, "03" * 16, 8, 1, 0, 2),)

    current, preceding, reached_and_foregone = (
        production._advance_bounded_frontier_evidence(
            (),
            (),
            (),
            {
                "physical_frontier_routes": first,
                "preceding_distinct_physical_frontier_routes": (),
                "reached_and_foregone_physical_frontier_routes": (),
            },
        )
    )
    current, preceding, reached_and_foregone = (
        production._advance_bounded_frontier_evidence(
            current,
            preceding,
            reached_and_foregone,
            {
                "physical_frontier_routes": second,
                "preceding_distinct_physical_frontier_routes": first,
                "reached_and_foregone_physical_frontier_routes": second,
            },
        )
    )

    assert current == second
    assert preceding == first
    assert reached_and_foregone == second


def test_working_causal_evidence_keeps_one_path_until_that_cause_settles() -> None:
    first = ("01" * 16, "02" * 16, 0, 7)
    second = ("02" * 16, "03" * 16, 0, 5)
    continuation, settlement = production._advance_bounded_working_causal_evidence(
        (),
        (),
        {
            "working_causal_continuations": ((first, second),),
            "settled_working_frontier": (),
        },
    )
    continuation, settlement = production._advance_bounded_working_causal_evidence(
        continuation,
        settlement,
        {
            "working_causal_continuations": (),
            "settled_working_frontier": (first, second),
        },
    )

    assert continuation == ((first, second),)
    assert settlement == (second,)


def test_prediction_evidence_keeps_two_alternatives_until_body_consequence() -> None:
    intrinsic_cause = "01" * 16
    first = (
        (intrinsic_cause, "02" * 16, 0, 7),
        ("02" * 16, "04" * 16, 0, 5),
    )
    second = (
        (intrinsic_cause, "03" * 16, 0, 6),
        ("03" * 16, "05" * 16, 0, 4),
    )
    consequence = ("06" * 16, "04" * 16, 0, 3)
    alternatives, returned = production._advance_bounded_prediction_evidence(
        (),
        (),
        {
            "physical_prediction_alternatives": (first, second),
            "body_consequence_transfers": (),
        },
    )
    alternatives, returned = production._advance_bounded_prediction_evidence(
        alternatives,
        returned,
        {
            "physical_prediction_alternatives": (),
            "body_consequence_transfers": (consequence,),
        },
    )

    assert alternatives == (first, second)
    assert returned == (consequence,)


def test_prediction_evidence_preserves_later_consequence_in_one_trajectory() -> None:
    intrinsic_cause = "01" * 16
    first = (
        (intrinsic_cause, "02" * 16, 0, 7),
        ("02" * 16, "04" * 16, 0, 5),
    )
    second = (
        (intrinsic_cause, "03" * 16, 0, 6),
        ("03" * 16, "05" * 16, 0, 4),
    )
    consequence = ("04" * 16, "06" * 16, 0, 3)

    alternatives, returned = production._advance_bounded_prediction_evidence(
        (),
        (),
        {
            "physical_prediction_alternatives": (first, second),
            "body_consequence_transfers": (consequence,),
        },
    )

    assert alternatives == (first, second)
    assert returned == (consequence,)
