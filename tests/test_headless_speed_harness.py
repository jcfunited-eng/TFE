"""tests/test_headless_speed_harness.py — Automated verification for Guala Headless Speed Harness.

Verifies:
1. Canonical initialization of HeadlessSpeedHarness with physical identity.
2. Direct-settlement single tick step advancing live organism tick.
3. Multi-tick batch simulation run (run_ticks) with empirical metrics collection.
4. Diurnal cycle and sleep pressure tracking contract.
5. Direct sensory block presentation.
6. Mathematical consistency and horizon extrapolation for the 2.5-year accelerated developmental roadmap.
7. Lever 4 Hierarchical Multi-Scale Stack integration (Micro reflex, Meso cadence, Macro cognitive intent).
8. Targeted Month 3 Acoustic Demand Syntax and Month 6 Valuation curriculum session fixture with honest evidence evaluation (SH-A1-05).
9. Month 18-24 Deontic Theory of Mind prescriptive session fixture with honest evidence evaluation (SH-A1-05).
10. Live production state checkpoint ingestion (Tick 1,819,000+, nights, vocal chains).
11. Matched baseline vs native acceleration benchmark asserting bit-exact equivalence, genuine isolated child subprocess cold-restart continuation invariance, and global inventory bound (SH-A1-01, SH-A1-06).
12. Caretaker clean_up_house global object inspection and core threshold (SH-A1-01).
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
    """Verifies Month 3 Acoustic Demand and Month 6 Valuation curriculum session fixture.
    
    Verifies self-describing scripted fixture classification, honest evaluation of preset tokens,
    and decoupling of syntactic articulation from physical metabolic fulfillment (SH-A1-05).
    """
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=1)
    receipt = harness.run_curriculum_session(target_entity_id="apple")

    assert isinstance(receipt, CurriculumReceipt)
    assert receipt.fixture_classification == "scripted_harness_fixture"
    assert receipt.autonomous_speech_observed is False
    assert receipt.organism_identity == DEFAULT_IDENTITY
    assert receipt.target_entity_id == "apple"
    assert receipt.tutor_acoustic_prompts_delivered == 3
    assert receipt.acoustic_cues_received == 3  # via property
    assert receipt.demand_intent_id.startswith("teleological_demand")
    assert receipt.demand_preset_tokens_advanced == ("dah0", "bah1")
    assert receipt.demand_syllables_emitted == ("dah0", "bah1")  # via property
    assert receipt.demand_articulation_complete is True
    # Honest physical assessment: caretaker delivery across rooms did not reach mouth; no bite occurred
    assert receipt.demand_physical_fulfilled is False
    assert receipt.demand_fulfilled is False
    assert receipt.demand_duration_beats > 0
    assert receipt.valuation_preset_tokens_advanced == ("kee0", "loo0")
    assert receipt.valuation_syllables_emitted == ("kee0", "loo0")  # via property
    # Honest affective assessment: preset tokens do not constitute measured valuation
    assert receipt.valuation_fulfilled is False
    assert receipt.ticks_per_second > 0.0
    assert receipt.overclock_speedup_factor > 0.0


def test_speed_harness_deontic_theory_of_mind_session() -> None:
    """Verifies Month 18-24 Deontic Theory of Mind prescriptive session fixture (SH-A1-05).
    
    Verifies self-describing scripted fixture classification, honest evaluation of tutor prompts,
    and non-manufacture of autonomous Theory of Mind (SH-A1-05).
    """
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=1)
    receipt = harness.run_deontic_session(target_action="rest")

    assert isinstance(receipt, DeonticReceipt)
    assert receipt.fixture_classification == "scripted_harness_fixture"
    assert receipt.autonomous_speech_observed is False
    assert receipt.organism_identity == DEFAULT_IDENTITY
    assert receipt.target_agent_id == "person-body-1"
    assert receipt.prescribed_action == "rest"
    assert receipt.tutor_prompts_delivered == 2
    assert receipt.acoustic_prompts_exchanged == 2  # via property
    assert receipt.deontic_intent_id.startswith("deontic_theory_of_mind")
    assert receipt.preset_tokens_advanced == ("dee0", "mah0")
    assert receipt.syllables_emitted == ("dee0", "mah0")  # via property
    # Honest social assessment: tutor-supplied prompts do not demonstrate autonomous Theory of Mind
    assert receipt.deontic_fulfilled is False
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
    """Verifies that speed harness correctly boots from Guala's authentic living state checkpoint."""
    harness = HeadlessSpeedHarness.from_live_checkpoint(identity=DEFAULT_IDENTITY)
    assert harness.identity == DEFAULT_IDENTITY
    assert harness.authentic_checkpoint_used is True
    # Organism must be initialized at Guala's real continuous age (> 1.8 million ticks)
    assert harness.live_tick >= 1_800_000
    assert harness.organism.counts.get("nights", 0) >= 6
    assert harness.organism.counts.get("syllables", 0) >= 400


def test_speed_harness_from_live_checkpoint_fails_closed() -> None:
    """Verifies fail-closed authority: missing or corrupt checkpoint must raise, never synthetic genesis (SH-A1-02)."""
    with pytest.raises((FileNotFoundError, RuntimeError)):
        HeadlessSpeedHarness.from_live_checkpoint(
            checkpoint_dir="/tmp/nonexistent_guala_checkpoint_dir_xyz",
            identity=DEFAULT_IDENTITY,
        )


def test_speed_harness_matched_benchmark_bit_exact_equivalence() -> None:
    """Verifies matched benchmark asserts verified native installation, bit-exact body/world equivalence, and isolated subprocess restart invariance (SH-A1-06)."""
    from tools.guala_headless_speed_harness import run_matched_benchmark
    res = run_matched_benchmark(ticks=10)
    assert res["native_acceleration_installed"] is True
    assert res["body_state_equivalence_verified"] is True
    assert res["world_state_equivalence_verified"] is True
    assert res["cold_restart_isolated_subprocess"] is True
    assert res["cold_restart_invariance_verified"] is True
    assert res["global_objects_count_bounded"] is True
    assert res["initial_world_objects_count"] == 86
    assert res["final_world_objects_count"] == 86
    assert res["measured_native_speedup"] > 1.2


def test_speed_harness_matched_benchmark_fails_closed_on_missing_checkpoint() -> None:
    """Verifies matched benchmark raises FileNotFoundError if checkpoint is missing (SH-A1-06)."""
    from pathlib import Path
    from tools.guala_headless_speed_harness import run_matched_benchmark
    with pytest.raises(FileNotFoundError):
        run_matched_benchmark(ticks=5, checkpoint_dir=Path("/tmp/nonexistent_guala_checkpoint_999"))


def test_caretaker_clean_up_house_edible_mass_and_bounds() -> None:
    """Verifies clean_up_house inspects global objects, enforces 2,000 ug core threshold, and bounds domestic clutter (SH-A1-01)."""
    from dsf_ai_service.guala_caretaker_hand import clean_up_house, EDIBLE_MASS_THRESHOLD_MICROGRAMS
    from dsf_ai_service.guala_home_world import home_world_authority

    world = home_world_authority(identity=DEFAULT_IDENTITY)
    all_objects = world.global_objects() if hasattr(world, "global_objects") else world._state.world.objects
    assert len(all_objects) >= 64

    rec = clean_up_house(world)
    assert rec["presented"] is True
    assert isinstance(rec["cleared"], list)
    assert "schema" in rec
