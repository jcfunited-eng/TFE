"""Embodied curriculum invitation is the sole card-presentation gate."""

from __future__ import annotations

import json
from fastapi.responses import JSONResponse

from dsf_ai_service import native_production_app as production


def test_direct_card_button_cannot_admit_without_prepared_occurrence(
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
    assert "prepared physical-occurrence receipt" in body["reason"]
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
        None,
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


def test_invite_prepares_exact_media_without_claiming_attention_or_moving_body(
    monkeypatch,
) -> None:
    class Pointer:
        organism_tick = 20
        state_sha256 = "77" * 32

    class Restored:
        pointer = Pointer()

    class Snapshot:
        revision = 7

    class World:
        @staticmethod
        def observation_snapshot():
            return Snapshot()

    monkeypatch.setattr(
        production,
        "_read_manifest_card",
        lambda _card_id: {"surface": {"sha256": "99" * 32}},
    )
    monkeypatch.setattr(production, "_runtime", lambda: (Restored(), object()))
    monkeypatch.setattr(production, "_world", lambda: World())
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)

    response = production.invite_card({"card_id": "alphabet-a"})
    body = json.loads(response.body)
    invitation = body["invitation"]

    assert response.status_code == 200
    assert body["accepted"] is True
    assert invitation["outcome"] == "presentable"
    assert invitation["presentation_eligible"] is True
    assert invitation["status"] == "tutor_physical_presentation_prepared"
    assert invitation["observed_at_organism_tick"] == 20
    assert invitation["observed_state_sha256"] == "77" * 32
    assert invitation["world_revision_before"] == 7
    assert invitation["world_revision_after"] == 7
    assert "participant_action" not in body
    assert "participant_action_causal_intent_receipt_sha256" not in invitation
    assert invitation["python_attention_authority"] is False
    assert invitation["scripted_acceptance_authority"] is False
    assert invitation["surface_sha256"] == "99" * 32
    assert invitation["transport_metadata_only"] is True


def test_invite_with_presentation_consumes_preparation_once_without_participant(
    monkeypatch,
) -> None:
    class Pointer:
        organism_tick = 20
        state_sha256 = "77" * 32

    class Restored:
        pointer = Pointer()

    class Snapshot:
        revision = 7

    class World:
        @staticmethod
        def observation_snapshot():
            return Snapshot()

    experience = {"surface": {"sha256": "99" * 32}}
    consumed: list[str] = []

    def commit(
        episodes,
        intake,
        card_id,
        committed_experience,
        presentation,
        preparation_receipt,
    ):
        assert episodes == ["one-physical-episode"]
        assert intake == "curriculum-card:alphabet-a:full"
        assert card_id == "alphabet-a"
        assert committed_experience is experience
        assert presentation == "full"
        assert preparation_receipt == production._curriculum_invitation[
            "invitation_receipt_sha256"
        ]
        consumed.append(preparation_receipt)
        return {
            "hop_count": 1,
            "persisted": {"organism_tick": 21, "state_sha256": "88" * 32},
            "receptor_ingress": {"changing_count": 1},
            "totals": {"physically_transitioned_neuron_count": 1},
        }

    monkeypatch.setattr(production, "_read_manifest_card", lambda _card_id: experience)
    monkeypatch.setattr(production, "_runtime", lambda: (Restored(), object()))
    monkeypatch.setattr(production, "_world", lambda: World())
    monkeypatch.setattr(
        production,
        "_card_lesson_hop_episodes",
        lambda *_args: ["one-physical-episode"],
    )
    monkeypatch.setattr(production, "_perform_card_lesson_intake", commit)
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)
    monkeypatch.setattr(
        production,
        "_intrinsic_curiosity_record",
        lambda: {
            "status": "not_claimed_by_tutor_transport",
            "social_experience_claimed": False,
        },
    )

    response = production.invite_card(
        {"card_id": "alphabet-a", "presentation": "full"}
    )
    body = json.loads(response.body)

    assert response.status_code == 200
    assert body["lesson"]["accepted"] is True
    assert body["lesson"]["hop_count"] == 1
    assert len(consumed) == 1
    assert "participant_action" not in body


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
