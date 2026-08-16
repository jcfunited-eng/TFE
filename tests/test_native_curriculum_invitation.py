"""Embodied curriculum invitation is the sole card-presentation gate."""

from __future__ import annotations

import json
import math
from dataclasses import replace

from fastapi.responses import JSONResponse
import pytest

from dsf_ai_service import native_production_app as production


def test_live_boundary_pose_gets_one_collision_free_visible_side_step(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    monkeypatch.setattr(production, "WORLD_AUTHORIZED", True)
    monkeypatch.setattr(production, "_world_authority", None)
    authority = production._world()
    snapshot = authority.observation_snapshot()
    her = next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)
    other = next(body for body in snapshot.bodies if body.body_id == "person-body-1")
    from dsf_ai_service.substrate.embodiment_world import PoseMM, PositionMM

    her = replace(
        her,
        pose=PoseMM(PositionMM(2_300, 4_500, 0), 322_872),
    )
    other = replace(
        other,
        pose=PoseMM(PositionMM(2_300, 5_002, 0), 270_000),
    )
    live_snapshot = replace(snapshot, bodies=(her, other))

    class LivePoseWorld:
        actor_ports = authority.actor_ports

        @staticmethod
        def observation_snapshot():
            return live_snapshot

    monkeypatch.setattr(production, "_world", lambda: LivePoseWorld())

    target = production._curriculum_participant_approach_payload()
    after = math.isqrt(
        (target["x_mm"] - her.pose.position.x) ** 2
        + (target["y_mm"] - her.pose.position.y) ** 2
    )

    assert (target["x_mm"], target["y_mm"]) == (2_802, 5_002)
    assert after > her.radius_mm + other.radius_mm


def test_direct_card_button_cannot_admit_without_embodied_invitation(
    monkeypatch,
) -> None:
    production._curriculum_invitation = None
    monkeypatch.setattr(
        production,
        "_read_manifest_card",
        lambda _card_id: {"surface": {"sha256": "99" * 32}},
    )
    built = False

    def build(*_args, **_kwargs):
        nonlocal built
        built = True
        return []

    monkeypatch.setattr(production, "_card_lesson_hop_episodes", build)
    response = production.teach_card({"card_id": "alphabet-a"})
    body = json.loads(response.body)

    assert response.status_code == 422
    assert body["accepted"] is False
    assert "embodied invitation receipt" in body["reason"]
    assert built is False


def test_pending_invitation_attends_only_when_its_frontier_reaches_motor() -> None:
    action_receipt = "55" * 32
    production._curriculum_invitation = {
        "outcome": "observing",
        "participant_action_causal_intent_receipt_sha256": action_receipt,
        "presentation_eligible": False,
    }
    production._active_external_participant_causal_motor_traces = {}

    production._settle_pending_curriculum_invitation(
        {
            "participant_action_causal_intent_receipt_sha256": action_receipt,
            "directed_physical_transfers": (("retina", "motor", 0, 1),),
        },
        organism_tick=21,
        state_sha256="77" * 32,
    )

    assert production._curriculum_invitation["outcome"] == "attended"
    assert production._curriculum_invitation["presentation_eligible"] is True
    assert production._curriculum_invitation["causal_directed_transfer_count"] == 1


@pytest.mark.parametrize(
    ("reached_retina", "causal_path_completed", "expected_outcome"),
    (
        (True, True, "attended"),
        (True, False, "declined"),
        (False, False, "not_reached"),
    ),
)
def test_invite_route_binds_card_to_exact_world_action_and_trace(
    monkeypatch,
    reached_retina: bool,
    causal_path_completed: bool,
    expected_outcome: str,
) -> None:
    action_receipt = "55" * 32
    action = {
        "causal_intent_receipt_sha256": action_receipt,
        "evidence_receipt_sha256": "66" * 32,
        "world_revision_before": 7,
        "world_revision_after": 8,
        "visual_changed_receptor_count": 1 if reached_retina else 0,
        "x_mm": 2_300,
        "y_mm": 5_001,
    }
    monkeypatch.setattr(
        production,
        "_read_manifest_card",
        lambda _card_id: {"surface": {"sha256": "99" * 32}},
    )
    monkeypatch.setattr(
        production,
        "_curriculum_participant_approach_payload",
        lambda: {
            "x_mm": 2_300,
            "y_mm": 5_001,
            "heading_millidegrees": 270_000,
            "signed_yaw_millidegrees": 100_000,
        },
    )
    monkeypatch.setattr(
        production,
        "world_other_body_move",
        lambda _payload: JSONResponse(
            status_code=200,
            content={
                "accepted": True,
                "ok": True,
                "action": action,
                "sensory_delivery": {
                    "organism_tick": 20,
                    "state_sha256": "77" * 32,
                },
            },
        ),
    )
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)
    production._last_transition_evidence = (
        {
            "participant_sensory_causal_use": {
                "participant_action_causal_intent_receipt_sha256": action_receipt,
                "directed_physical_transfers": (
                    ("retinal-lineage", "motor-lineage", 0, 2),
                ),
            }
        }
        if causal_path_completed
        else None
    )

    response = production.invite_card({"card_id": "alphabet-a"})
    body = json.loads(response.body)
    invitation = body["invitation"]

    assert response.status_code == 200
    assert body["accepted"] is True
    assert invitation["outcome"] == expected_outcome
    assert invitation["presentation_eligible"] is causal_path_completed
    assert invitation[
        "participant_action_causal_intent_receipt_sha256"
    ] == action_receipt
    assert invitation["surface_sha256"] == "99" * 32
    assert invitation["transport_metadata_only"] is True
