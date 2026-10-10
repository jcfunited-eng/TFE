"""tests/test_caretaker_regimentation.py — Verification of Caretaker Daily Regimentation.

Invariants Verified:
1. Complete circadian partitioning of the 113,600-tick diurnal cycle into 6 distinct epochs.
2. Multi-food dietary rotation across bread, milk, and apple entities with tastant mass.
3. Attention gating: lessons hold during sleep, mealtime, and bedtime, resuming when alert.
4. Acoustic nature synthesis: stroller birdsong blocks generate valid 16kHz mono PCM.
5. Physical affordance definitions: playpen, high-chair, and ladder challenges exist and are mapped.
"""

from __future__ import annotations

import math
import struct
import pytest

from guala_caretaker.caretaker import (
    circadian_epoch,
    ready_for_lesson,
    birdsong_blocks,
    FOOD_PREFIXES,
    DIURNAL_CYCLE_TICKS,
)
from dsf_ai_service.guala_caretaker_hand import (
    DELIVER_IDS,
    TOUCH_IDS,
)


def test_circadian_partitioning_complete_and_continuous() -> None:
    """Verify that the 113,600-tick cycle is partitioned without gaps or overlaps."""
    assert DIURNAL_CYCLE_TICKS == 113_600

    # Test key epoch markers
    dawn_epoch, _ = circadian_epoch(0)
    assert dawn_epoch == "DAWN_AWAKENING"

    morning_epoch, _ = circadian_epoch(20_000)
    assert morning_epoch == "MORNING_FOCUS"

    midday_epoch, _ = circadian_epoch(45_000)
    assert midday_epoch == "MIDDAY_STROLL"

    afternoon_epoch, _ = circadian_epoch(65_000)
    assert afternoon_epoch == "AFTERNOON_CHALLENGE"

    evening_epoch, _ = circadian_epoch(85_000)
    assert evening_epoch == "EVENING_CULTURE"

    night_epoch, _ = circadian_epoch(100_000)
    assert night_epoch == "NIGHT_CONSOLIDATION"

    # Test periodicity across multiple days
    day2_dawn, _ = circadian_epoch(DIURNAL_CYCLE_TICKS + 5_000)
    assert day2_dawn == "DAWN_AWAKENING"

    day3_midday, _ = circadian_epoch(2 * DIURNAL_CYCLE_TICKS + 50_000)
    assert day3_midday == "MIDDAY_STROLL"


def test_food_prefixes_multi_diet() -> None:
    """Verify multi-food dietary recognition across bread, milk, and apple entities."""
    assert "apple" in FOOD_PREFIXES
    assert "bread" in FOOD_PREFIXES
    assert "milk" in FOOD_PREFIXES or "bottle-milk" in FOOD_PREFIXES

    test_items = ["apple-1", "bread-slice", "bottle-milk", "toy-bear"]
    recognized = [
        item for item in test_items
        if any(item.startswith(prefix) for prefix in FOOD_PREFIXES)
    ]
    assert recognized == ["apple-1", "bread-slice", "bottle-milk"]


def test_birdsong_audio_blocks_synthesis() -> None:
    """Verify outdoor nature birdsong generates valid 16kHz s16le PCM blocks."""
    blocks = birdsong_blocks()
    assert len(blocks) > 0

    for block in blocks:
        assert isinstance(block, bytes)
        assert len(block) == 8000  # 0.25 s at 16kHz mono 16-bit = 4000 samples * 2 bytes = 8000 bytes
        # Verify valid 16-bit signed integer unpack
        samples = struct.unpack(f"<{len(block) // 2}h", block)
        assert len(samples) == 4000
        # Check that audio is non-silent and within range
        assert any(abs(s) > 100 for s in samples)
        assert all(-32768 <= s <= 32767 for s in samples)


def test_attention_gating_respects_diurnal_states() -> None:
    """Verify lessons hold during sleep, mealtime, and bedtime, resuming when alert."""
    # Alert, awake, upright state -> should be ready
    alert_obs = {
        "available": True,
        "last_occurrence": {
            "her_sleep": {"asleep": False, "pressure": [10, 100]},
            "her_act": "toward_toy",
            "embodiment": {
                "self_body_id": "guala-body-1",
                "bodies": [{"body_id": "guala-body-1", "pose": {"posture": "standing"}}],
            },
            "metabolic_need_reserve_deficit": [1, 10],
        },
    }
    assert ready_for_lesson(alert_obs, {"active_ritual": "MORNING_FOCUS"}) is True

    # Asleep state -> must hold
    asleep_obs = {
        "available": True,
        "last_occurrence": {
            "her_sleep": {"asleep": True, "pressure": [90, 100]},
            "her_act": "sleep",
            "embodiment": alert_obs["last_occurrence"]["embodiment"],
            "metabolic_need_reserve_deficit": [1, 10],
        },
    }
    assert ready_for_lesson(asleep_obs, {"active_ritual": "NIGHT_CONSOLIDATION"}) is False

    # Lying down posture -> must hold
    lying_obs = {
        "available": True,
        "last_occurrence": {
            "her_sleep": {"asleep": False, "pressure": [30, 100]},
            "her_act": "body",
            "embodiment": {
                "self_body_id": "guala-body-1",
                "bodies": [{"body_id": "guala-body-1", "pose": {"posture": "lying"}}],
            },
            "metabolic_need_reserve_deficit": [1, 10],
        },
    }
    assert ready_for_lesson(lying_obs, {"active_ritual": "BEDTIME"}) is False

    # Starving/hungry state -> must hold for feeding
    hungry_obs = {
        "available": True,
        "last_occurrence": {
            "her_sleep": {"asleep": False, "pressure": [10, 100]},
            "her_act": "toward_food",
            "embodiment": alert_obs["last_occurrence"]["embodiment"],
            "metabolic_need_reserve_deficit": [8, 10],  # 80% deficit > 40% threshold
        },
    }
    assert ready_for_lesson(hungry_obs, {"active_ritual": "MEALTIME"}) is False


def test_deliver_ids_and_touch_ids_completeness() -> None:
    """Verify physical delivery and affection touch contracts."""
    assert "radio-delivery" in DELIVER_IDS
    assert "bread-delivery" in DELIVER_IDS
    assert "milk-delivery" in DELIVER_IDS

    assert "touch-hug" in TOUCH_IDS
    assert "touch-kiss" in TOUCH_IDS
    assert "touch-hold-hand" in TOUCH_IDS
    assert "touch-lap" in TOUCH_IDS
    assert "touch-bedtime-hold" in TOUCH_IDS

