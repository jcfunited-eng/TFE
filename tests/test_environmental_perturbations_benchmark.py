from __future__ import annotations

import pytest
from tools.benchmark_environmental_perturbations import run_benchmark


def test_environmental_perturbations_benchmark() -> None:
    """Option 2: Dynamic Environmental Perturbation Challenge regression verification."""
    report = run_benchmark()

    # Verify report structure
    assert "benchmark" in report
    assert "physics_floor" in report
    assert report["physics_floor"] == 0.85
    assert "challenges" in report
    assert "scores" in report

    # Challenge 1: Acoustic stream truncation & quiet dropout
    c1 = report["challenges"]["challenge1_acoustic_dropout"]
    assert c1["passed"] is True
    assert c1["event_opened_on_truncation"] is True
    assert c1["clean_closure_on_dropout"] is True
    assert c1["recovery_beats"] <= 2
    assert report["scores"]["acoustic_dropout_score"] == 1.0

    # Challenge 2: Visual blackout & exact re-acquisition
    c2 = report["challenges"]["challenge2_visual_blackout"]
    assert c2["passed"] is True
    assert c2["blackout_suppressed_figure"] is True
    assert c2["hash_exact_match"] is True
    assert c2["recovery_beats"] <= 2
    assert report["scores"]["visual_blackout_score"] == 1.0

    # Challenge 3: Object snatch mid-feeding
    c3 = report["challenges"]["challenge3_object_snatch"]
    assert c3["passed"] is True
    assert c3["bites_initiated"] >= 1
    assert c3["organism_tick_continuity"] is True
    assert c3["graceful_transition"] is True
    assert c3["recovery_beats"] <= 1
    assert report["scores"]["object_snatch_score"] == 1.0

    # Challenge 4: Thermal nociception & protective reflex
    c4 = report["challenges"]["challenge4_thermal_nociception"]
    assert c4["passed"] is True
    assert c4["pain_signal_active"] is True
    assert c4["protective_release_triggered"] is True
    assert c4["recovery_latency_beats"] == 0
    assert "burns" in c4["reflex_reason"]
    assert report["scores"]["thermal_nociception_score"] == 1.0

    # Composite verdict must enforce canonical 85% physics floor
    assert report["overall_perturbation_score"] >= 0.85
    assert report["verdict"] == "PASS"
