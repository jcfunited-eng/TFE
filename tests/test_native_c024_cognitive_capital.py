from __future__ import annotations

import json
from pathlib import Path
import re

from dsf_ai_service import native_production_app as serving


ROOT = Path(__file__).resolve().parents[1]


def _section(available: bool, status: str = "test") -> dict[str, object]:
    return {
        "available": available,
        "status": status,
        "reason": "test evidence" if available else "not observed",
    }


def _record() -> dict[str, object]:
    sensory = _section(True)
    for modality in (
        "visual",
        "auditory",
        "touch",
        "temperature",
        "smell",
        "taste",
        "proprioception",
        "vestibular",
        "interoception",
    ):
        sensory[modality] = _section(False)
    return {
        "sensory": sensory,
        "fractals": _section(False),
        "formations": {**_section(True), "mosaic_count": 0},
        "recall": _section(False),
        "attention": _section(False),
        "working_causal_state": _section(False),
        "prediction": _section(False),
        "affective_balance": _section(False),
        "articulation": _section(False),
        "intrinsic_curiosity": _section(False),
        "choice": _section(False),
        "play": _section(False),
        "body": _section(False),
        "identity": {**_section(True), "value": "test-organism"},
        "persistence": {**_section(True), "current_ref": "a" * 64},
    }


def _ui_array(name: str) -> tuple[str, ...]:
    source = (ROOT / "dsf_ai_service/static/loomscan.html").read_text(
        encoding="utf-8"
    )
    matched = re.search(rf"const {name}=(\[[^;]+\]);", source)
    assert matched is not None
    return tuple(json.loads(matched.group(1)))


def test_axes_match_the_truthful_loom_and_empty_evidence_stays_empty(
    monkeypatch,
) -> None:
    monkeypatch.setattr(serving, "_last_transition_evidence", None)
    monkeypatch.setattr(serving, "_last_causal_cross_context_use_evidence", None)
    capital = serving._cognitive_capital_record(_record())

    assert tuple(capital["capabilities"]) == serving.COGNITIVE_CAPITAL_CAPABILITIES
    assert tuple(capital["dimensions"]) == serving.COGNITIVE_CAPITAL_DIMENSIONS
    assert tuple(capital["capabilities"]) == _ui_array("CAPITAL_CAPABILITIES")
    assert tuple(capital["dimensions"]) == _ui_array("CAPITAL_DIMENSIONS")
    assert capital["credits"] == []
    assert capital["available"] is False
    assert capital["scalar_score_authority"] is False
    assert capital["cognition_authority"] is False


def test_exact_sensory_ingress_credits_only_the_reached_senses(monkeypatch) -> None:
    record = _record()
    record["sensory"]["visual"] = _section(True, "visual_mounted")
    record["sensory"]["auditory"] = _section(True, "auditory_mounted")
    monkeypatch.setattr(
        serving,
        "_last_transition_evidence",
        {
            "organism_tick": 41,
            "receptor_ingress": {
                "sense_counts": {
                    "sight": 27,
                    "sound": 0,
                    "touch": 3,
                    "smell": 0,
                    "taste": 0,
                    "body": 0,
                }
            },
            "totals": {},
            "vestibular_tick_count": 0,
        },
    )

    capital = serving._cognitive_capital_record(record)
    cells = {(credit["capability"], credit["dimension"]) for credit in capital["credits"]}

    assert ("Vision", "availability") in cells
    assert ("Hearing", "availability") in cells
    assert ("Vision", "participation") in cells
    assert ("Touch", "participation") in cells
    assert ("Hearing", "participation") not in cells
    assert ("Multisensory integration", "participation") in cells


def test_causal_reassembly_credits_use_but_not_unproved_meaning(monkeypatch) -> None:
    formation_receipt = "f" * 64
    causal = {
        **_section(
            True,
            "retained_formation_caused_body_action_and_sensed_consequence",
        ),
        "formation_receipt_sha256": formation_receipt,
        "intake": "continuous-environment:c024-test",
        "action": {"command_sha256": "a" * 64},
        "sensed_consequence": {"successor_state_sha256": "b" * 64},
    }
    record = _record()
    record["formations"]["mosaic_count"] = 1
    record["body"] = {
        **_section(True, "native_body_action_and_sensed_return_observed"),
        "causal_cross_context_use": causal,
    }
    monkeypatch.setattr(serving, "_last_transition_evidence", None)

    capital = serving._cognitive_capital_record(record)
    cells = {(credit["capability"], credit["dimension"]) for credit in capital["credits"]}

    assert ("Recall", "recall") in cells
    assert ("Recall", "causal_use") in cells
    assert ("Episodic memory", "durability") in cells
    assert ("Recall", "durability") not in cells
    assert ("Motor and actuator control", "autonomous_use") in cells
    assert ("Autonomous cognition and action", "causal_use") in cells
    for unproved in (
        "Relational thought",
        "Language comprehension",
        "Social cognition and other-perspective",
        "Motivation, needs, and curiosity",
        "Creativity and self-expression",
    ):
        assert not any(credit["capability"] == unproved for credit in capital["credits"])
    keys = [
        (credit["capability"], credit["dimension"])
        for credit in capital["credits"]
    ]
    assert len(keys) == len(set(keys))
    assert len(keys) <= len(serving.COGNITIVE_CAPITAL_CAPABILITIES) * len(
        serving.COGNITIVE_CAPITAL_DIMENSIONS
    )
    assert all(
        set(credit)
        == {"capability", "dimension", "evidence"}
        for credit in capital["credits"]
    )
    assert all(
        evidence
        and all(
            set(reference) == {"kind", "path", "receipt_sha256"}
            for reference in evidence
        )
        for evidence in (credit["evidence"] for credit in capital["credits"])
    )


def test_later_quiet_transition_does_not_erase_the_bounded_causal_witness(
    monkeypatch,
) -> None:
    witness = {
        "formation_receipt_sha256": "f" * 64,
        "intake": "continuous-environment:c024-test",
        "organism_tick": 88_004,
        "state_sha256": "a" * 64,
        "action": {"command_sha256": "b" * 64},
        "sensed_consequence": {"successor_state_sha256": "a" * 64},
    }
    monkeypatch.setattr(serving, "_last_causal_cross_context_use_evidence", witness)
    monkeypatch.setattr(
        serving,
        "_last_transition_evidence",
        {"organism_tick": 88_056, "causal_cross_context_use": None},
    )

    record = serving._causal_cross_context_use_record()
    assert record["available"] is True
    assert record["evidence_organism_tick"] == 88_004
    assert record["formation_receipt_sha256"] == "f" * 64


def test_sensorimotor_play_credits_only_observed_play_dimensions(monkeypatch) -> None:
    record = _record()
    record["play"] = {
        **_section(True, "sensorimotor_play_observed"),
        "changed_world_context": True,
        "evidence_receipt_sha256": "e" * 64,
        "formation_receipt_sha256": "f" * 64,
        "fun": _section(True, "positive_engagement_trajectory_observed"),
        "varied_displacement": True,
        "voluntary_return": True,
    }
    monkeypatch.setattr(serving, "_last_transition_evidence", None)

    capital = serving._cognitive_capital_record(record)
    cells = {
        (credit["capability"], credit["dimension"])
        for credit in capital["credits"]
    }

    assert {
        ("Play and exploration", "availability"),
        ("Play and exploration", "participation"),
        ("Play and exploration", "causal_use"),
        ("Play and exploration", "autonomous_use"),
        ("Play and exploration", "integration_depth"),
    }.issubset(cells)
    assert ("Play and exploration", "transfer") in cells
    assert ("Play and exploration", "durability") not in cells
    assert not any(
        capability == "Creativity and self-expression"
        for capability, _ in cells
    )
