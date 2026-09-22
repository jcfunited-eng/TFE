from __future__ import annotations

import pytest
from tools.benchmark_associative_grounding import run_benchmark


def test_associative_grounding_benchmark() -> None:
    """Option 1: Automated Associative Grounding Benchmark regression verification."""
    report = run_benchmark()

    # Verify report structure
    assert "benchmark" in report
    assert "physics_floor" in report
    assert report["physics_floor"] == 0.85
    assert "tests" in report
    assert "scores" in report

    # Test 1: Clean baseline grounding & causal credit
    t1 = report["tests"]["test1_clean_grounding"]
    assert t1["passed"] is True
    assert t1["intake_micrograms"] > 0
    assert t1["bites"] >= 1
    assert t1["moments_formed"] >= 1
    assert t1["fed_causal_credits"] >= 1
    assert report["scores"]["clean_grounding_score"] == 1.0

    # Test 2: Acoustic noise resilience
    t2 = report["tests"]["test2_acoustic_noise"]
    assert t2["passed"] is True
    assert t2["mean_spectral_fidelity"] >= 0.85
    assert report["scores"]["acoustic_resilience_score"] >= 0.85
    for detail in t2["details"]:
        assert detail["gate_event_closed"] is True
        assert detail["cochlear_cosine_similarity"] > 0.70

    # Test 3: Visual lighting invariance
    t3 = report["tests"]["test3_visual_lighting"]
    assert t3["passed"] is True
    assert t3["unique_keys_count"] == 1
    assert report["scores"]["visual_invariant_score"] == 1.0

    # Test 4: Temporal binding window & decay
    t4 = report["tests"]["test4_temporal_binding"]
    assert t4["passed"] is True
    assert t4["within_window_bound"] is True
    assert t4["outside_window_decayed"] is True
    assert report["scores"]["temporal_binding_score"] == 1.0

    # Composite verdict must enforce the canonical 85% physics floor
    assert report["overall_robustness_score"] >= 0.85
    assert report["verdict"] == "PASS"
