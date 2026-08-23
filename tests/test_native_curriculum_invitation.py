"""Embodied curriculum invitation is the sole card-presentation gate."""

from __future__ import annotations

import json
import math
from dataclasses import replace

from fastapi.responses import JSONResponse
import pytest

from dsf_ai_service import native_production_app as production


def test_live_boundary_pose_gets_one_collision_free_retinal_approach(
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
        pose=PoseMM(PositionMM(2_300, 4_500, 0), 323_874),
    )
    other = replace(
        other,
        pose=PoseMM(PositionMM(3_386, 4_250, 0), 167_036),
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

    assert after > her.radius_mm + other.radius_mm
    from dsf_ai_service.substrate.w1_physical_receptors import _retinal_projection

    moved_other = replace(
        other,
        pose=PoseMM(
            PositionMM(target["x_mm"], target["y_mm"], 0),
            target["heading_millidegrees"],
        ),
    )
    candidate = replace(snapshot, bodies=(her, moved_other))
    assert _retinal_projection(candidate) != _retinal_projection(live_snapshot)


def test_visible_side_step_refuses_a_path_blocked_by_a_placed_object(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    monkeypatch.setattr(production, "WORLD_AUTHORIZED", True)
    monkeypatch.setattr(production, "_world_authority", None)
    authority = production._world()
    snapshot = authority.observation_snapshot()
    her = next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)
    other = next(body for body in snapshot.bodies if body.body_id == "person-body-1")
    from dsf_ai_service.substrate.embodiment_world import (
        EmbodiedObject,
        PoseMM,
        PositionMM,
    )

    her = replace(her, pose=PoseMM(PositionMM(2_300, 4_500, 0), 322_872))
    other = replace(other, pose=PoseMM(PositionMM(2_300, 5_002, 0), 270_000))
    blocker = EmbodiedObject(
        object_id="path-blocker",
        radius_mm=100,
        mass_grams=1_000,
        position=PositionMM(2_551, 5_002, 0),
    )
    blocked_snapshot = replace(
        snapshot,
        bodies=(her, other),
        objects=snapshot.objects + (blocker,),
    )

    class BlockedWorld:
        actor_ports = authority.actor_ports

        @staticmethod
        def observation_snapshot():
            return blocked_snapshot

    monkeypatch.setattr(production, "_world", lambda: BlockedWorld())

    with pytest.raises(
        production._CurriculumInvitationRefusal,
        match="no one-step collision-free in-room approach",
    ):
        production._curriculum_participant_approach_payload()


def test_boundary_approach_produces_an_exact_retinal_change(
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

    her = replace(her, pose=PoseMM(PositionMM(2_300, 4_500, 0), 322_872))
    other = replace(other, pose=PoseMM(PositionMM(3_710, 4_775, 0), 191_036))
    live_snapshot = replace(snapshot, bodies=(her, other))

    class BoundaryWorld:
        actor_ports = authority.actor_ports

        @staticmethod
        def observation_snapshot():
            return live_snapshot

    monkeypatch.setattr(production, "_world", lambda: BoundaryWorld())

    target = production._curriculum_participant_approach_payload()
    from dsf_ai_service.substrate.w1_physical_receptors import _retinal_projection

    moved_other = replace(
        other,
        pose=PoseMM(
            PositionMM(target["x_mm"], target["y_mm"], 0),
            target["heading_millidegrees"],
        ),
    )
    candidate = replace(snapshot, bodies=(her, moved_other))

    assert _retinal_projection(candidate) != _retinal_projection(live_snapshot)


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


def test_participant_path_enters_native_attention_without_motor_requirement() -> None:
    receptor = "01" * 16
    ordering = "02" * 16
    reached = "03" * 16
    foregone = "04" * 16
    action_receipt = "55" * 32
    first = (receptor, ordering, 0, 5)
    selected = (ordering, reached, 0, 3)
    def interval(predecessor_tick, *, perturbed=(), frontier=()):
        return {
            "predecessor_organism_tick": predecessor_tick,
            "organism_tick": predecessor_tick + 1,
            "externally_perturbed_neuron_lineages": perturbed,
            "internally_reassembled_formation_cues": (),
            "motor_unit_recruitments": (),
            "emitted_neuron_fractals": (),
            "changed_contact_channel_states": (),
            "affective_balance_trajectories": (),
            "causal_frontier_advances": frontier,
        }
    hop = {
        "predecessor_organism_tick": 19,
        "organism_tick": 22,
        "causal_interval_evidence": (
            interval(19, perturbed=(receptor,)),
            interval(20, frontier=((*first, ordering),)),
            interval(21, frontier=((*selected, reached),)),
        ),
        "physical_frontier_routes": (
            (ordering, 11, 0, reached, 9, 1, 0, 3),
        ),
        "preceding_distinct_physical_frontier_routes": (
            (ordering, 11, 0, foregone, 9, 2, 0, 0),
        ),
        "reached_and_foregone_physical_frontier_routes": (
            (ordering, 11, 0, reached, 9, 1, 0, 3),
            (ordering, 11, 0, foregone, 9, 2, 0, 0),
        ),
    }

    _active, completed = production._advance_causal_motor_traces(
        object(),
        {},
        {},
        hop,
        external_participant_action_receipt=action_receipt,
    )
    proof = completed["external_participant_attention"]

    assert proof is not None
    assert proof["participant_action_causal_intent_receipt_sha256"] == action_receipt
    assert proof["directed_physical_transfers"] == (first, selected)
    assert proof["matched_attention_transfer"] == selected
    assert "motor_unit_recruitment" not in proof


def test_unrelated_sparse_attention_cannot_accept_participant_invitation() -> None:
    receptor = "01" * 16
    participant_route = "02" * 16
    unrelated = "03" * 16
    reached = "04" * 16
    foregone = "05" * 16
    witness = {
        "participant_action_causal_intent_receipt_sha256": "55" * 32,
        "origin_lineages": (receptor,),
        "origin_organism_tick": 20,
        "paths": ((participant_route, ((receptor, participant_route, 0, 5),)),),
    }
    hop = {
        "organism_tick": 22,
        "physical_frontier_routes": (
            (unrelated, 11, 0, reached, 9, 1, 0, 3),
        ),
        "preceding_distinct_physical_frontier_routes": (
            (unrelated, 11, 0, foregone, 9, 2, 0, 0),
        ),
        "reached_and_foregone_physical_frontier_routes": (
            (unrelated, 11, 0, reached, 9, 1, 0, 3),
            (unrelated, 11, 0, foregone, 9, 2, 0, 0),
        ),
    }

    assert production._external_participant_attention_from_path_witness(
        witness,
        hop,
    ) is None


@pytest.mark.parametrize(
    ("reached_retina", "causal_path_completed", "expected_outcome"),
    (
        (True, True, "presentable"),
        (True, False, "presentable"),
        (False, False, "not_reached"),
    ),
)
def test_invite_route_binds_card_to_physical_retinal_delivery_only(
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
            "participant_sensory_attention": {
                "participant_action_causal_intent_receipt_sha256": action_receipt,
                "directed_physical_transfers": (
                    ("retinal-lineage", "attention-route-lineage", 0, 2),
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
    assert invitation["presentation_eligible"] is reached_retina
    assert "causal_directed_transfer_count" not in invitation
    assert invitation[
        "participant_action_causal_intent_receipt_sha256"
    ] == action_receipt
    assert invitation["surface_sha256"] == "99" * 32
    assert invitation["transport_metadata_only"] is True


def test_retinal_body_read_uses_the_transition_lock(monkeypatch) -> None:
    lock_depth = 0

    class TrackingTransitionLock:
        def __enter__(self):
            nonlocal lock_depth
            lock_depth += 1
            return self

        def __exit__(self, _error_type, _error, _traceback):
            nonlocal lock_depth
            lock_depth -= 1

    class Readiness:
        articulated_body_axes = ("left-eye", "right-eye")

    class Organism:
        @staticmethod
        def readiness():
            assert lock_depth == 1
            return Readiness()

    class Restored:
        organism = Organism()

    monkeypatch.setattr(production, "_transition_lock", TrackingTransitionLock())
    monkeypatch.setattr(production, "_runtime", lambda: (Restored(), object()))

    assert production._current_retinal_body_axes() == ("left-eye", "right-eye")
    assert lock_depth == 0


def test_invited_card_can_settle_before_external_admission_ends(monkeypatch) -> None:
    invitation_receipt = "77" * 32
    lock_depth = 0

    class TrackingTransitionLock:
        def __enter__(self):
            nonlocal lock_depth
            lock_depth += 1
            return self

        def __exit__(self, _error_type, _error, _traceback):
            nonlocal lock_depth
            lock_depth -= 1

    monkeypatch.setattr(production, "_transition_lock", TrackingTransitionLock())
    monkeypatch.setattr(
        production,
        "_read_manifest_card",
        lambda _card_id: {"surface": {"sha256": "99" * 32}},
    )

    def build_lesson(*_args):
        assert lock_depth == 1
        return [("episode", [(0, 1)])]

    monkeypatch.setattr(
        production,
        "_card_lesson_hop_episodes",
        build_lesson,
    )
    monkeypatch.setattr(
        production,
        "_embodied_curriculum_invitation",
        lambda **_kwargs: JSONResponse(
            status_code=200,
            content={
                "accepted": True,
                "ok": True,
                "invitation": {
                    "invitation_receipt_sha256": invitation_receipt,
                },
            },
        ),
    )
    observed: dict[str, object] = {}

    def perform(*args):
        observed["args"] = args
        return {
            "hop_count": 3,
            "observation": {"large_private_body": [1, 2, 3]},
            "persisted": {"organism_tick": 44, "state_sha256": "88" * 32},
            "receptor_ingress": {"changing_count": 2},
            "totals": {"dsf_delivery_count": 7},
        }

    monkeypatch.setattr(production, "_perform_card_lesson_intake", perform)
    monkeypatch.setattr(
        production,
        "_last_intrinsic_curiosity_evidence",
        None,
    )

    response = production.invite_card(
        {"card_id": "alphabet-a", "presentation": "full"}
    )
    body = json.loads(response.body)

    assert response.status_code == 200
    assert lock_depth == 0
    assert observed["args"][0] == [("episode", [(0, 1)])]
    assert observed["args"][5] == invitation_receipt
    assert body["lesson"] == {
        "accepted": True,
        "card_id": "alphabet-a",
        "curiosity_status": "physical_curiosity_mounted_awaiting_causal_witness",
        "hop_count": 3,
        "persisted": {"organism_tick": 44, "state_sha256": "88" * 32},
        "presentation": "full",
        "receptor_ingress": {"changing_count": 2},
        "social_experience_claimed": False,
        "totals": {"dsf_delivery_count": 7},
    }
    assert "observation" not in body["lesson"]
