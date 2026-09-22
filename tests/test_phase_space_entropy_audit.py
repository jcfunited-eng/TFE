from __future__ import annotations

import pytest
from tools.audit_phase_space_entropy import audit_phase_space_entropy


def test_phase_space_entropy_audit() -> None:
    """Option 3: 24-Hour Behavioral Phase-Space Entropy Audit regression verification."""
    report = audit_phase_space_entropy()

    # Verify report structure
    assert "audit" in report
    assert "physics_floor" in report
    assert report["physics_floor"] == 0.85
    assert "metrics" in report
    assert "scores" in report

    # 1. Action Entropy
    m_ent = report["metrics"]["action_entropy"]
    assert m_ent["total_action_events"] > 1000
    assert m_ent["unique_action_types"] >= 10
    assert 0.50 <= m_ent["entropy_ratio"] <= 0.95
    assert m_ent["homeostatic_band_pass"] is True
    assert report["scores"]["action_entropy_score"] == 1.0

    # 2. Sequential Dynamics
    m_seq = report["metrics"]["sequential_dynamics"]
    assert m_seq["structured_intentional_flow"] is True
    assert 0.05 <= m_seq["sequential_constraint_ratio"] <= 0.35
    assert report["scores"]["transition_dynamics_score"] == 1.0

    # 3. Diurnal Coverage
    m_diur = report["metrics"]["diurnal_coverage"]
    assert m_diur["passed"] is True
    assert m_diur["active_hours_count"] >= 22
    assert m_diur["coverage_ratio"] >= 0.90
    assert report["scores"]["diurnal_coverage_score"] >= 0.90

    # 4. Basin Simulation
    m_basin = report["metrics"]["basin_simulation"]
    assert m_basin["passed"] is True
    assert m_basin["reserve_maintained"] is True
    assert m_basin["clock_continuity"] is True
    assert report["scores"]["basin_simulation_score"] == 1.0

    # Composite verdict must enforce the canonical 85% physics floor
    assert report["overall_entropy_audit_score"] >= 0.85
    assert report["verdict"] == "PASS"
