import pytest
from dsf_ai_service.episodic_binding_engine import (
    compute_somatic_salience,
    should_consolidate,
    create_episodic_key,
    evaluate_anticipatory_consequence,
    SALIENCE_THRESHOLD,
    EpisodicFrame,
)


def test_pool_shock_single_trial_consolidation():
    """Validates the Pool Shock Principle:
    A high-salience traumatic shock or boundary event consolidates immediately on trial 1.
    """
    salience = compute_somatic_salience(
        shock_magnitude=1.0,
        pain_signal=True,
        boundary_collision=True,
    )
    assert salience >= SALIENCE_THRESHOLD
    assert salience == 1.0

    # Single exposure must consolidate!
    assert should_consolidate(salience, count=1) is True


def test_hunger_quench_salience():
    """A large meal intake (e.g. 80,000 ug) produces significant salience."""
    salience = compute_somatic_salience(reserve_delta_ug=80_000)
    assert salience >= 0.40
    assert should_consolidate(salience, count=2) is True


def test_low_salience_background_filtering():
    """Routine floor sitting with zero somatic gradient does not consolidate on trial 1."""
    salience = compute_somatic_salience(
        reserve_delta_ug=0,
        shock_magnitude=0.0,
        boundary_collision=False,
        pain_signal=False,
    )
    assert salience < SALIENCE_THRESHOLD
    assert should_consolidate(salience, count=1) is False
    # Requisite repetition permits eventual consolidation
    assert should_consolidate(salience, count=2) is True


def test_anticipatory_veto_under_threat_cue():
    """Prior episode of shock when touching exposed wire vetoes subsequent touch attempt."""
    meanings = {
        "wire_shock_ep": {
            "figure": "exposed_wire",
            "source": "heard",
            "room": "garden",
            "acts": {
                "touch": [1, -1.0],  # 1 try, -1.0 net valence (shock)
            },
            "fed": 0,
        }
    }

    valence, reason = evaluate_anticipatory_consequence(
        candidate_act="touch",
        visual_figure="exposed_wire",
        acoustic_event="radio_buzz",
        room="garden",
        meanings=meanings,
    )

    assert valence < -0.35
    assert reason is not None
    assert "vetoed" in reason


def test_anticipatory_promotion_under_food_cue():
    """Prior episode of eating apple promotes bite action."""
    meanings = {
        "apple_fed_ep": {
            "figure": "apple",
            "source": "heard",
            "room": "dining",
            "acts": {
                "bite": [3, 2.5],
            },
            "fed": 3,
        }
    }

    valence, reason = evaluate_anticipatory_consequence(
        candidate_act="bite",
        visual_figure="apple",
        acoustic_event="crunch",
        room="dining",
        meanings=meanings,
    )

    assert valence > 0.35
    assert reason is not None
    assert "promoted" in reason


def test_episodic_frame_roundtrip():
    frame = EpisodicFrame(
        key="test1234",
        tick=1000,
        room="library",
        pose=(100, 200),
        visual_figure="book",
        acoustic_event="page_turn",
        tactile="paper",
        somatic_delta=0.5,
        action="grasp",
        consequence="held_book",
        salience=0.8,
    )
    d = frame.to_dict()
    restored = EpisodicFrame.from_dict(d)
    assert restored == frame

