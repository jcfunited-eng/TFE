"""Bounded durable observation receipt for one committed card lesson."""

from __future__ import annotations

import json

from dsf_ai_service import native_production_app as production


def _result(successor: str, tick: int) -> dict[str, object]:
    totals = {
        "complete_neuron_fractal_count": 27,
        "current_cohort_evaluation_count": 9,
        "dsf_delivery_count": 954,
        "endogenous_partial_cue_reassembly_count": 0,
        "partial_cue_reassembly_count": 0,
        "physically_transitioned_neuron_count": 1487,
        "recurrent_complete_neuron_fractal_count": 0,
    }
    return {
        "accepted": True,
        "ok": True,
        "hop_count": 9,
        "vestibular_tick_count": 0,
        "observation": {"state_sha256": successor},
        "persisted": {
            "organism_tick": tick,
            "predecessor_state_sha256": "aa" * 32,
            "schema": production.PERSISTENCE_SCHEMA,
            "state_bytes": 24_465_080,
            "state_sha256": successor,
        },
        "schema": "guala.native_admitted_intake_result.v1",
        "totals": totals,
    }


def test_latest_card_receipt_is_exact_bounded_and_survives_later_transition(
    monkeypatch,
    tmp_path,
) -> None:
    first_successor = "bb" * 32
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    monkeypatch.setattr(
        production,
        "_perform_admitted_intake_locked",
        lambda _episodes, _intake: _result(first_successor, 38_665),
    )
    monkeypatch.setattr(production, "_committed_card_occupancy", lambda *_: None)
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)
    production._last_card_lesson_receipt = None
    production._last_card_lesson_receipt_error = None

    experience = {
        "surface": {"sha256": "99" * 32},
        "tutor_audio": {"sha256": "77" * 32},
    }
    invitation = {
        "schema": production.CURRICULUM_INVITATION_SCHEMA,
        "card_id": "number-07",
        "outcome": "attended",
        "presentation_eligible": True,
        "participant_action_causal_intent_receipt_sha256": "44" * 32,
        "reason": "test fixture exact causal continuation",
        "status": "participant_causal_continuation_observed",
    }
    invitation["invitation_receipt_sha256"] = production._receipt(invitation)
    production._curriculum_invitation = invitation
    result = production._perform_card_lesson_intake(
        [],
        "curriculum-card:number-07:full",
        "number-07",
        experience,
        "full",
        invitation["invitation_receipt_sha256"],
    )

    path = tmp_path / production.CARD_LESSON_RECEIPT_FILE
    assert result["durable_receipt"]["available"] is True
    assert path.is_file()
    assert path.stat().st_size <= production.CARD_LESSON_RECEIPT_MAX_BYTES
    stored = json.loads(path.read_bytes())
    assert stored["card_id"] == "number-07"
    assert stored["surface_sha256"] == "99" * 32
    assert stored["invitation_receipt_sha256"] == invitation[
        "invitation_receipt_sha256"
    ]
    assert stored["successor_state_sha256"] == first_successor
    assert stored["transport_metadata_only"] is True
    assert production._card_lesson_receipt_digest(stored) == stored["receipt_sha256"]

    # A later continuous transition may replace the process's generic latest
    # transition, but it cannot replace this intake-specific receipt.
    production._last_transition_evidence = {
        "intake": "continuous-environment:later",
        "state_sha256": "cc" * 32,
    }
    assert production._card_lesson_receipt_record()["card_id"] == "number-07"

    # Process restart reloads exactly the same fixed record from disk.
    production._last_card_lesson_receipt = None
    assert production._load_card_lesson_receipt() == stored
