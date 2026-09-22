"""tests/test_hierarchical_temporal_stack.py — Automated verification for Hierarchical Multi-Scale Stack.

Verifies:
1. Micro-scale (10 ms) thermal nociceptive reflex firing and prompt mitigation.
2. Micro-scale tactile and acoustic shock protection.
3. Meso-scale (250 ms) beat cadence coordination.
4. Macro-scale (2 - 10 s) cognitive intent lifecycle (teleological demand, affective valuation, deontic theory of mind).
5. Cross-scale coupling: Micro-reflex preempting active macro-intent upon physical violation.
6. Decoupled token advancement from intent fulfillment (SH-A1-05).
"""

from __future__ import annotations

import pytest

from dsf_ai_service.guala_hierarchical_stack import (
    ACOUSTIC_SHOCK_FLOOR,
    CONTACT_SHOCK_THRESHOLD,
    MICRO_FRAME_MICROSECONDS,
    MICRO_FRAMES_PER_BEAT,
    NOCICEPTION_MILLIKELVIN,
    HierarchicalTemporalStack,
    MacroIntent,
    MacroIntentType,
    MesoBeatField,
    MicroInterrupt,
    MicroReflexField,
)


def test_micro_reflex_thermal_nociception_interrupt() -> None:
    """Verifies that temperatures >= 340 K (340,000 mK) fire a sub-tick micro-interrupt."""
    micro = MicroReflexField()

    # Safe temperature: 310 K (310,000 mK)
    interrupts = micro.evaluate_subframes(
        tick=1,
        heard_frames=None,
        skin_contact=0.1,
        skin_temperature_millikelvin=310_000,
        touch_surface_millikelvin=310_000,
        held_surface_millikelvin=310_000,
        held_entity_id="cool_toy",
    )
    assert len(interrupts) == 0

    # Hazardous burn temperature: 350 K (350,000 mK)
    hazard_temp = 350_000
    interrupts = micro.evaluate_subframes(
        tick=2,
        heard_frames=None,
        skin_contact=0.1,
        skin_temperature_millikelvin=hazard_temp,
        touch_surface_millikelvin=hazard_temp,
        held_surface_millikelvin=hazard_temp,
        held_entity_id="hot_plate",
    )
    assert len(interrupts) == 1
    assert interrupts[0].trigger == "thermal_nociception"
    assert interrupts[0].mitigation_action == "release"
    assert interrupts[0].severity == pytest.approx(1.0)
    assert interrupts[0].entity_id == "hot_plate"
    assert len(micro.interrupt_history) == 1


def test_micro_reflex_tactile_and_acoustic_shock() -> None:
    """Verifies contact shock (>0.95) and acoustic gammatone shock (>0.90) trigger micro-interrupts."""
    micro = MicroReflexField()

    # Contact shock
    interrupts = micro.evaluate_subframes(
        tick=1,
        heard_frames=None,
        skin_contact=0.98,
        skin_temperature_millikelvin=310_000,
        touch_surface_millikelvin=310_000,
    )
    assert len(interrupts) == 1
    assert interrupts[0].trigger == "contact_shock"
    assert interrupts[0].mitigation_action == "retract"

    # Acoustic gammatone shock
    shock_frame = [0.0] * 16
    shock_frame[4] = 0.95  # Exceeds ACOUSTIC_SHOCK_FLOOR = 0.90
    interrupts = micro.evaluate_subframes(
        tick=2,
        heard_frames=[shock_frame],
        skin_contact=0.0,
        skin_temperature_millikelvin=310_000,
        touch_surface_millikelvin=310_000,
    )
    assert len(interrupts) == 1
    assert interrupts[0].trigger == "acoustic_shock"
    assert interrupts[0].mitigation_action == "startle_freeze"


def test_meso_beat_field_step() -> None:
    """Verifies meso-scale step increments beat count."""
    meso = MesoBeatField()
    assert meso.beat_count == 0
    assert meso.step(1) == 1
    assert meso.step(2) == 2
    assert meso.beat_count == 2


def test_macro_intent_teleological_demand_lifecycle() -> None:
    """Verifies acoustic demand intent forms, advances phonemic syllables, and fulfills upon verified goal attainment (SH-A1-05)."""
    stack = HierarchicalTemporalStack()

    intent = stack.form_teleological_demand(target_entity_id="apple", tick=10, phoneme_tokens=("dah0", "bah1"))
    assert intent.intent_type == MacroIntentType.TELEOLOGICAL_DEMAND
    assert intent.target_entity_id == "apple"
    assert intent.syntactic_assembly_tokens == ("dah0", "bah1")
    assert intent.is_active is True

    # Advance syllables across beats
    token1 = stack.macro.advance_active_token()
    assert token1 == "dah0"
    assert stack.active_macro_intent is not None
    assert stack.active_macro_intent.current_token_index == 1
    assert stack.active_macro_intent.is_active is True

    token2 = stack.macro.advance_active_token()
    assert token2 == "bah1"
    # Syllables emitted: tokens are exhausted, but intent strictly remains active until physical goal is verified
    assert stack.active_macro_intent is not None
    assert stack.active_macro_intent.current_token_index == 2
    assert stack.active_macro_intent.tokens_exhausted is True
    assert stack.active_macro_intent.fulfilled is False

    # Goal reached on subsequent beat fulfills the intent
    fulfilled_intent = stack.macro.step(tick=12, goal_reached=True)
    assert fulfilled_intent is not None
    assert fulfilled_intent.fulfilled is True
    assert stack.active_macro_intent is None
    assert len(stack.macro.completed_intents) == 1
    assert stack.macro.completed_intents[0].fulfilled is True


def test_macro_intent_abort_when_target_vanishes() -> None:
    """Verifies macro-intent cleanly aborts if target entity is removed from environment."""
    stack = HierarchicalTemporalStack()
    stack.form_teleological_demand(target_entity_id="milk_bottle", tick=100)

    assert stack.active_macro_intent is not None

    # Step with target still present
    intent = stack.macro.step(tick=101, target_entity_present=True)
    assert intent is not None
    assert intent.is_active is True

    # Step with target vanished
    intent = stack.macro.step(tick=102, target_entity_present=False)
    assert intent is not None
    assert intent.aborted is True
    assert intent.abort_reason == "target_entity_vanished"
    assert stack.active_macro_intent is None


def test_macro_intent_abort_on_duration_timeout() -> None:
    """Verifies macro-intent aborts when duration ceiling is exceeded."""
    stack = HierarchicalTemporalStack()
    # Form intent with 8-beat duration ceiling
    stack.macro.form_intent(
        intent_type=MacroIntentType.IDLE_EXPLORATION,
        target_entity_id=None,
        tick=50,
        duration_beats=8,
    )

    assert stack.active_macro_intent is not None

    # Step within ceiling (7 beats elapsed)
    intent = stack.macro.step(tick=57, target_entity_present=True)
    assert intent is not None
    assert intent.is_active is True

    # Step past ceiling (8 beats elapsed)
    intent = stack.macro.step(tick=58, target_entity_present=True)
    assert intent is not None
    assert intent.aborted is True
    assert intent.abort_reason == "duration_ceiling_exceeded"
    assert stack.active_macro_intent is None


def test_cross_scale_coupling_micro_preempts_macro() -> None:
    """Verifies that an immediate micro-reflex (burn) aborts any active macro intent."""
    stack = HierarchicalTemporalStack()
    # Guala has an active teleological demand to reach for a glowing object
    stack.form_teleological_demand(target_entity_id="lantern", tick=20)
    assert stack.active_macro_intent is not None

    # Evaluate cycle where held lantern surface temperature spikes past nociception threshold
    interrupts, active_macro = stack.evaluate_cycle(
        tick=21,
        heard_frames=None,
        skin_contact=0.2,
        skin_temperature_millikelvin=310_000,
        touch_surface_millikelvin=345_000,
        held_surface_millikelvin=345_000,
        held_entity_id="lantern",
    )

    assert len(interrupts) == 1
    assert interrupts[0].trigger == "thermal_nociception"
    # Macro intent was aborted by the micro reflex
    assert active_macro is not None
    assert active_macro.aborted is True
    assert "micro_reflex_thermal_nociception" in active_macro.abort_reason
