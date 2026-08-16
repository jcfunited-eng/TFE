from __future__ import annotations

from pathlib import Path

from dsf_ai_service import native_production_app as production


ROOT = Path(__file__).resolve().parents[1]


def test_topology_parity_motor_yaw_bridge_is_absent() -> None:
    production_source = (
        ROOT / "dsf_ai_service" / "native_production_app.py"
    ).read_text(encoding="utf-8")
    wrapper_source = (
        ROOT
        / "dsf_ai_service"
        / "glew_runtime"
        / "native_resident_organism.py"
    ).read_text(encoding="utf-8")
    native_source = (
        ROOT / "native" / "guala_core" / "src" / "virtual_body_yaw_motion.rs"
    ).read_text(encoding="utf-8")

    assert "_prepare_motor_yaw_action" not in production_source
    assert "exact_motor_unit_yaw_trajectory" not in wrapper_source
    assert "settle_motor_unit_yaw_actuation" not in native_source
    assert "topology_index % 2" not in native_source


def test_native_articulated_body_action_is_truthfully_projected(monkeypatch) -> None:
    motor_action = {
        "schema": "guala.native.articulated_body_action.v1",
        "moved": True,
        "root_motion": False,
        "body_state_before_sha256": "11" * 32,
        "body_state_after_sha256": "22" * 32,
        "body_effector_bindings": [
            {
                "motor_lineage": "33" * 16,
                "axis": "left_elbow_flexion",
                "direction": "toward_maximum",
                "outward_elementary_carriers": 7,
            }
        ],
        "articulated_body_consequences": [
            {
                "source_tick": 8,
                "axis": "left_elbow_flexion",
                "unit": "millidegree",
                "predecessor_position": 0,
                "successor_position": 7,
                "signed_displacement": 7,
                "toward_minimum_carriers": 0,
                "toward_maximum_carriers": 7,
                "opposed_carriers_per_terminal": 0,
                "applied_displacement_quanta": 7,
                "stalled_carriers": 0,
            }
        ],
        "body_proprioceptive_sources": [
            {
                "source_sha256": "44" * 32,
                "source_tick": 8,
                "port_count": 2,
                "sample_count": 4,
                "occurrence_count": 1,
                "occurrence_frame_count": 2,
            }
        ],
        "prepared_recruitments": [],
    }
    monkeypatch.setattr(
        production,
        "_last_unattended_evidence",
        {
            "category": "native_causal_action_observed",
            "declared_interval_milliseconds": 2_000,
            "hop_count": 8,
            "intake": "continuous-environment:test",
            "measured": {},
            "motor_action": motor_action,
            "organism_tick": 9,
            "receptor_ingress": {
                "changing_count": 0,
                "quiescent_count": 74,
                "sense_counts": {
                    "sight": 0,
                    "sound": 0,
                    "touch": 0,
                    "smell": 0,
                    "taste": 0,
                    "body": 74,
                },
                "source_hop_count": 1,
            },
            "state_sha256": "55" * 32,
            "world_revision": 1,
        },
    )

    observed = production._autonomy_record()

    assert observed["available"] is True
    assert observed["status"] == "native_causal_action_observed"
    assert observed["action_observed"] is True
    assert observed["action"]["status"] == "native_articulated_body_observed"
    assert observed["action"]["observed_effect"] == "1 typed body-axis consequences"
    assert observed["consequence"]["status"] == (
        "native_proprioceptive_consequence_observed"
    )
    assert observed["consequence"]["observed_effect"] == (
        "1 body-source receipts returned"
    )
    assert "prepared_recruitments" not in observed["motor_action"]
    assert observed["motor_action"] == {
        key: value
        for key, value in motor_action.items()
        if key != "prepared_recruitments"
    }
