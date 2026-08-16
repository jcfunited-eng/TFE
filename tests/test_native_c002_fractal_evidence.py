"""C-002 production-boundary proof for exact neuronal-fractal evidence."""

from __future__ import annotations

import json

from dsf_ai_service import native_production_app as production


def test_disposable_experience_exposes_exact_post_settlement_evidence(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    production._restored = None
    production._admission = None
    production._boot_error = None
    production._public_observation_body = None
    production._public_observation_etag = None
    production._last_transition_evidence = None

    production._startup()
    invitation = {
        "schema": production.CURRICULUM_INVITATION_SCHEMA,
        "card_id": "alphabet-a",
        "outcome": "attended",
        "presentation_eligible": True,
        "participant_action_causal_intent_receipt_sha256": "33" * 32,
        "reason": "test fixture exact causal continuation",
        "status": "participant_causal_continuation_observed",
    }
    invitation["invitation_receipt_sha256"] = production._receipt(invitation)
    production._curriculum_invitation = invitation
    response = production.teach_card(
        {
            "card_id": "alphabet-a",
            "invitation_receipt_sha256": invitation[
                "invitation_receipt_sha256"
            ],
        }
    )
    result = json.loads(response.body)
    evidence = result["observation"]["emitted_neuron_fractals"]

    assert response.status_code == 200
    assert result["totals"]["complete_neuron_fractal_count"] == len(evidence)
    assert evidence
    causal_lineages = {
        (
            item["predecessor_organism_tick"],
            item["organism_tick"],
            item["neuron_lineage"],
        )
        for item in evidence
    }
    assert len(causal_lineages) == len(evidence)
    for item in evidence:
        assert item["predecessor_organism_tick"] < item["organism_tick"]
        assert len(item["neuron_lineage"]) == 32
        assert item["sparse_retained_delta"]

    public = json.loads(production._public_observation_body)
    assert public["fractals"]["formed_evidence_in_last_experience"] == evidence
