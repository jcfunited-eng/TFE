"""tests/test_headless_speed_harness.py — Automated verification for Guala Headless Speed Harness.

Verifies:
1. Canonical initialization of HeadlessSpeedHarness with physical identity.
2. Direct-settlement single tick step advancing live organism tick.
3. Multi-tick batch simulation run (run_ticks) with empirical metrics collection.
4. Diurnal cycle and sleep pressure tracking contract.
5. Direct sensory block presentation.
6. Mathematical consistency and horizon extrapolation for the 2.5-year accelerated developmental roadmap.
7. Lever 4 Hierarchical Multi-Scale Stack integration (Micro reflex, Meso cadence, Macro cognitive intent).
8. Targeted Month 3 Acoustic Demand Syntax and Month 6 Valuation curriculum session.
9. Month 18-24 Deontic Theory of Mind prescriptive session.
10. Live production state checkpoint ingestion (Tick 1,767,000+, nights, vocal chains).
"""

from __future__ import annotations

import pytest

from tools.guala_headless_speed_harness import (
    DEFAULT_IDENTITY,
    REAL_TIME_TICKS_PER_SECOND,
    CurriculumReceipt,
    DeonticReceipt,
    HarnessMetrics,
    HeadlessSpeedHarness,
    SleepReceipt,
)


def test_speed_harness_initialization() -> None:
    """Verifies headless speed harness instantiates organism and world without network dependencies."""
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=1)
    assert harness.identity == DEFAULT_IDENTITY
    assert harness.live_tick == 1
    assert harness.world is not None
    assert harness.organism is not None
    assert harness.loop is not None
    assert harness.temporal_stack is not None


def test_speed_harness_single_step() -> None:
    """Verifies that step() advances live organism tick and performs physical settlement."""
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=10)
    init_tick = harness.live_tick
    result = harness.step()

    assert result is not None
    assert harness.live_tick == init_tick + 1


def test_speed_harness_run_ticks_and_metrics() -> None:
    """Verifies batch run_ticks accurately collects time, throughput, and organism dynamics."""
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=1)
    n_ticks = 5

    progress_reports: list[tuple[int, int, float]] = []

    def on_progress(done: int, total: int, elapsed: float) -> None:
        progress_reports.append((done, total, elapsed))

    metrics: HarnessMetrics = harness.run_ticks(
        n_ticks=n_ticks,
        progress_callback=on_progress,
        callback_interval=1,
    )

    assert metrics.organism_identity == DEFAULT_IDENTITY
    assert metrics.initial_tick == 1
    assert metrics.final_tick == 1 + n_ticks
    assert metrics.ticks_elapsed == n_ticks
    assert metrics.simulated_subjective_seconds == n_ticks * 0.25
    assert metrics.simulated_subjective_hours == (n_ticks * 0.25) / 3600.0
    assert metrics.wall_clock_seconds > 0.0
    assert metrics.ticks_per_second > 0.0
    assert metrics.overclock_speedup_factor == pytest.approx(
        metrics.ticks_per_second / REAL_TIME_TICKS_PER_SECOND, rel=1e-3
    )
    assert len(progress_reports) == n_ticks
    assert progress_reports[-1][0] == n_ticks
    assert isinstance(metrics.micro_interrupts_count, int)
    assert isinstance(metrics.macro_intents_completed, int)


def test_speed_harness_sleep_contract() -> None:
    """Verifies sleep pressure tracking conforms to diurnal cycle mechanics."""
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=1)
    sleep_state = harness.current_sleep_state()

    assert "asleep" in sleep_state
    assert isinstance(sleep_state["asleep"], bool)
    assert "pressure" in sleep_state
    assert len(sleep_state["pressure"]) == 2
    assert sleep_state["pressure"][0] >= 0
    assert sleep_state["pressure"][1] > 0
    assert "nights" in sleep_state
    assert isinstance(sleep_state["nights"], int)


def test_speed_harness_present_sensory_block() -> None:
    """Verifies direct presentation of sensory occurrence without HTTP ingress."""
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=1)
    result = harness.present_sensory_block(source="caretaker-food", food="apple")
    assert result is not None
    assert harness.live_tick == 2


def test_speed_harness_extrapolations() -> None:
    """Verifies developmental timeline extrapolation calculation and milestones."""
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=1)
    metrics = harness.run_ticks(n_ticks=4)
    extrapolations = harness.extrapolate_developmental_timeline(metrics)

    assert "current_benchmark" in extrapolations
    assert "projections" in extrapolations

    projections = extrapolations["projections"]
    required_milestones = [
        "1 Subjective Day (Diurnal Cycle)",
        "Month 1 (Sensory Habituation)",
        "Month 3 (Acoustic Demand Syntax)",
        "Month 6 (Acoustic Valuation)",
        "Month 12 ('Let's Play' Affordance)",
        "2.5 Years (Deontic Theory of Mind)",
    ]

    for milestone in required_milestones:
        assert milestone in projections
        data = projections[milestone]
        assert data["required_ticks"] > 0
        assert data["natural_realtime_days"] > 0
        assert data["accelerated_sim_days"] > 0
        assert data["accelerated_sim_hours"] > 0
        assert data["acceleration_factor"] > 0


def test_speed_harness_multi_scale_temporal_stack() -> None:
    """Verifies Lever 4 Multi-Scale Stack integration in headless speed harness."""
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=1)

    # Formulate Month 3 Teleological Demand Intent
    intent = harness.form_teleological_demand("toy-block", phoneme_tokens=("dah0", "bah1"))
    assert intent.target_entity_id == "toy-block"
    assert harness.temporal_stack.active_macro_intent is not None
    assert harness.temporal_stack.active_macro_intent.intent_type.value == "teleological_demand"

    # Step simulation
    metrics = harness.run_ticks(n_ticks=3)
    assert metrics.active_macro_intent_type == "teleological_demand"
    assert metrics.micro_interrupts_count >= 0

    # Formulate Month 6 Affective Valuation Intent
    val_intent = harness.form_affective_valuation("warm-blanket", phoneme_tokens=("kee0", "loo0"))
    assert val_intent.target_entity_id == "warm-blanket"
    assert harness.temporal_stack.active_macro_intent.intent_type.value == "affective_valuation"

    # Formulate Month 18-24 Deontic Prescription Intent
    deon_intent = harness.form_deontic_prescription("rest", phoneme_tokens=("dee0", "mah0"))
    assert deon_intent.syntactic_assembly_tokens == ("dee0", "mah0")
    assert harness.temporal_stack.active_macro_intent.intent_type.value == "deontic_theory_of_mind"


def test_speed_harness_curriculum_session() -> None:
    """Verifies full Month 3 Acoustic Demand and Month 6 Valuation curriculum session."""
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=1)
    receipt = harness.run_curriculum_session(target_entity_id="apple")

    assert isinstance(receipt, CurriculumReceipt)
    assert receipt.organism_identity == DEFAULT_IDENTITY
    assert receipt.target_entity_id == "apple"
    assert receipt.acoustic_cues_received == 3
    assert receipt.demand_intent_id.endswith("teleological_demand")
    assert receipt.demand_syllables_emitted == ("dah0", "bah1")
    assert receipt.demand_fulfilled is True
    assert receipt.demand_duration_beats > 0
    assert receipt.valuation_syllables_emitted == ("kee0", "loo0")
    assert receipt.valuation_fulfilled is True
    assert receipt.ticks_per_second > 0.0
    assert receipt.overclock_speedup_factor > 0.0


def test_speed_harness_deontic_theory_of_mind_session() -> None:
    """Verifies Month 18-24 Deontic Theory of Mind prescriptive session."""
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=1)
    receipt = harness.run_deontic_session(target_action="rest")

    assert isinstance(receipt, DeonticReceipt)
    assert receipt.organism_identity == DEFAULT_IDENTITY
    assert receipt.target_agent_id == "person-body-1"
    assert receipt.prescribed_action == "rest"
    assert receipt.acoustic_prompts_exchanged == 2
    assert receipt.deontic_intent_id.endswith("deontic_theory_of_mind")
    assert receipt.syllables_emitted == ("dee0", "mah0")
    assert receipt.deontic_fulfilled is True
    assert receipt.duration_beats > 0
    assert receipt.ticks_per_second > 0.0
    assert receipt.overclock_speedup_factor > 0.0


def test_speed_harness_sleep_settle_session() -> None:
    """Verifies caregiver bedtime settle and nocturnal sleep consolidation pass."""
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=1)
    harness.organism._state.setdefault("moments", {})["maternal_voice"] = {
        "count": 2,
        "tick": 1,
        "salience": 0.70,
        "held": "none",
        "source": "heard",
        "context": ["nursery"],
        "next": {},
        "fed": 0,
    }
    harness.organism._state["moments"]["dust_mote"] = {
        "count": 1,
        "tick": 2,
        "salience": 0.05,
        "held": "none",
        "source": "visual",
        "context": ["hallway"],
        "next": {},
        "fed": 0,
    }
    receipt = harness.run_sleep_settle_session(target_sleep_beats=10)

    assert isinstance(receipt, SleepReceipt)
    assert receipt.organism_identity == DEFAULT_IDENTITY
    assert receipt.bed_made is True
    assert set(receipt.bedding_items) == {"blanket", "pillow"}
    assert receipt.nights_completed >= 1
    assert receipt.sleep_beats_elapsed >= 10
    assert receipt.meanings_consolidated_count >= 1
    assert "maternal_voice" in harness.organism._state.get("meanings", {})
    assert "dust_mote" not in harness.organism._state.get("meanings", {})
    assert receipt.ticks_per_second > 0.0


def test_speed_harness_from_live_checkpoint() -> None:
    """Verifies that speed harness correctly boots from Guala's real live state checkpoint."""
    harness = HeadlessSpeedHarness.from_live_checkpoint(identity=DEFAULT_IDENTITY)
    assert harness.identity == DEFAULT_IDENTITY
    # Organism must be initialized at Guala's real continuous age (> 1.7 million ticks)
    assert harness.live_tick >= 1_750_000
    # Nights completed must reflect her actual history (6 nights)
    assert harness.organism.counts.get("nights", 0) >= 6
    # Learned vocal chains must reflect her active combinatorial chains
    assert harness.organism.counts.get("syllables", 0) >= 400
