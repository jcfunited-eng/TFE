import pytest
import os
import sys

from tools.monitor_phase_space_entropy import (
    compute_action_entropy,
    compute_sequential_constraint,
    compute_diurnal_coverage,
    run_monitor,
    PHYSICS_FLOOR,
)

LOG_PATH = "/workspaces/Tao_Financial_Engine/guala_caretaker/caretaker.log"


def test_action_entropy_deterministic_bounds():
    # Uniform 4 actions: H = 2.0 bits, ratio = 1.0 (fails upper limit > 0.95)
    actions_uniform = ["body", "bite", "turn_left", "turn_right"] * 100
    res_uniform = compute_action_entropy(actions_uniform)
    assert res_uniform["shannon_entropy_bits"] == 2.0
    assert res_uniform["entropy_ratio"] == 1.0

    # Natural skewed biological action distribution:
    actions_natural = (
        ["body"] * 500
        + ["turn_right"] * 250
        + ["turn_left"] * 200
        + ["toward_thing"] * 150
        + ["bite"] * 80
        + ["release"] * 60
    )
    res_natural = compute_action_entropy(actions_natural)
    assert 0.50 <= res_natural["entropy_ratio"] <= 0.95
    assert res_natural["pass"] is True
    assert res_natural["score"] == 1.0


def test_sequential_constraint_calculation():
    # Deterministic sequence: body -> toward_thing -> bite -> release
    actions = ["body", "toward_thing", "bite", "release"] * 50
    res = compute_sequential_constraint(actions)
    assert res["conditional_entropy_bits"] == 0.0
    assert res["mutual_information_bits"] > 0.0
    assert res["constraint_ratio"] > 0.0


def test_diurnal_coverage():
    lines = [
        "2026-09-17T01:00:00Z number-06 block 1/5 accepted tick 100 world action body\n",
        "2026-09-17T02:00:00Z number-06 block 2/5 accepted tick 200 world action bite\n",
        "2026-09-17T03:00:00Z number-06 block 3/5 accepted tick 300 world action turn_left\n",
    ]
    res = compute_diurnal_coverage(lines)
    assert res["active_hours_in_log"] == 3
    assert res["coverage_ratio"] == round(3 / 24.0, 4)


@pytest.mark.skipif(not os.path.exists(LOG_PATH), reason="Caretaker log not found")
def test_run_monitor_on_live_caretaker_log():
    res = run_monitor(log_path=LOG_PATH, check_live=False)
    assert "composite_score" in res
    assert res["composite_score"] >= PHYSICS_FLOOR
    assert res["overall_pass"] is True

