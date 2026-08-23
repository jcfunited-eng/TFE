"""A-001 continuous native life at the production translation boundary.

Python supplies bounded physical intervals.  It never selects a thought,
attention route, or action.  The same native organism consumes the interval,
persists one successor, and may expose a native motor consequence.  Reading the
public observation is inert.
"""

from __future__ import annotations

import json
import threading
from types import SimpleNamespace

from dsf_ai_service import native_production_app as production
from dsf_ai_service.substrate.embodiment_world import (
    ENVIRONMENT_PORT_ID,
    EmbodimentWorldAuthority,
)


def _native_record(tick: int, state: str) -> dict[str, object]:
    return {
        **{
            key: (0, 1)
            for key in production._UNATTENDED_EXACT_ENERGY_KEYS
        },
        "organism_tick": tick,
        "state_sha256": state,
    }


def _transition_result(motor_action: dict[str, object] | None) -> dict[str, object]:
    return {
        "hop_count": production.UNATTENDED_HOPS_PER_INTERVAL,
        "observation": {"motor_action": motor_action},
        "receptor_ingress": {
            "changing_count": 1,
            "quiescent_count": 5,
            "sense_counts": {
                "body": 1,
                "sight": 1,
                "smell": 1,
                "sound": 1,
                "taste": 1,
                "touch": 1,
            },
            "source_hop_count": production.UNATTENDED_HOPS_PER_INTERVAL,
        },
        "totals": {
            "complete_neuron_fractal_count": 1,
            "metabolically_perturbed_body_receptor_count": 0,
            "partial_cue_reassembly_count": 1,
            "physically_transitioned_neuron_count": 1,
            "rest_recovered_neuron_count": 0,
        },
    }


def _mount_translation_boundary(monkeypatch, *, before, after, result) -> list[str]:
    records = iter((before, after))
    admitted_intakes: list[str] = []
    monkeypatch.setattr(production, "_restored", SimpleNamespace())
    monkeypatch.setattr(production, "_admission", SimpleNamespace())
    monkeypatch.setattr(production, "_native_record", lambda: next(records))
    monkeypatch.setattr(
        production,
        "_unattended_interval_episodes",
        lambda _interval_id: (
            [(object(), [])],
            {
                "external_luminance_present": True,
                "external_smell_present": False,
                "passive_interval_receipt_sha256": "33" * 32,
                "retinal_heading_offset_millidegrees": 0,
                "world_revision_before": 16,
                "world_revision": 17,
            },
        ),
    )

    def admit(_episodes, intake):
        admitted_intakes.append(intake)
        return result

    monkeypatch.setattr(production, "_perform_admitted_intake_locked", admit)
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)
    production._external_intake_waiting.clear()
    production._last_unattended_evidence = None
    production._last_unattended_pause = None
    return admitted_intakes


def test_retinal_heading_is_read_from_the_persisted_native_neck(monkeypatch) -> None:
    readiness = SimpleNamespace(
        articulated_body_axes=(
            (0, "torso_pitch", "millidegree", 0, -30_000, 0, 45_000),
            (2, "neck_yaw", "millidegree", -17_250, -75_000, 0, 75_000),
        )
    )
    organism = SimpleNamespace(readiness=lambda: readiness)
    monkeypatch.setattr(
        production,
        "_restored",
        SimpleNamespace(organism=organism),
    )
    monkeypatch.setattr(production, "_admission", SimpleNamespace())

    assert production._current_retinal_heading_offset_millidegrees() == -17_250


def test_unattended_transport_advances_and_persists_world_owned_time(
    monkeypatch,
) -> None:
    world = EmbodimentWorldAuthority(
        authority_key=b"unattended-passive-world-test-key"
    )
    before = world.observation_snapshot()
    persisted: list[bytes] = []
    monkeypatch.setattr(production, "_world", lambda: world)
    monkeypatch.setattr(production, "_persist_world_body", persisted.append)

    execution = production._advance_passive_world_interval()

    assert execution.port_id == ENVIRONMENT_PORT_ID
    assert execution.actor_body_id is None
    assert execution.after.revision == before.revision + 1
    assert persisted == [world.encoded_snapshot()]
    assert world.recent_applied_receipts() == ()


def test_continuous_world_interval_reaches_native_action_and_sensed_return(
    monkeypatch,
) -> None:
    motor_action = {
        "schema": "guala.native.articulated_body_action.v1",
        "moved": True,
        "root_motion": False,
        "motor_unit_recruitment_count": 2,
        "articulated_body_consequences": [
            {"axis": "left_elbow_flexion", "signed_displacement": 5}
        ],
        "body_proprioceptive_sources": [
            {"source_sha256": "44" * 32, "source_tick": 40}
        ],
    }
    intakes = _mount_translation_boundary(
        monkeypatch,
        before=_native_record(40, "11" * 32),
        after=_native_record(41, "22" * 32),
        result=_transition_result(motor_action),
    )

    observed = production._attempt_unattended_interval()

    assert observed["delivered"] is True
    assert observed["outcome"] == "native_causal_action_observed"
    assert observed["organism_tick"] == 41
    assert observed["state_sha256"] == "22" * 32
    assert len(intakes) == 1
    assert intakes[0].startswith("continuous-environment:")
    assert production._last_unattended_pause is None

    autonomy = production._autonomy_record()
    assert autonomy["available"] is True
    assert autonomy["action_observed"] is True
    assert autonomy["action"]["status"] == "native_articulated_body_observed"
    assert autonomy["consequence"]["status"] == (
        "native_proprioceptive_consequence_observed"
    )
    assert autonomy["choice"]["available"] is False
    assert autonomy["thought"]["available"] is False


def test_unmoved_motor_record_is_not_reported_as_a_body_action(monkeypatch) -> None:
    motor_action = {
        "schema": "guala.native.articulated_body_action.v1",
        "moved": False,
        "root_motion": False,
        "motor_unit_recruitment_count": 0,
        "articulated_body_consequences": [],
        "body_proprioceptive_sources": [],
    }
    _mount_translation_boundary(
        monkeypatch,
        before=_native_record(41, "22" * 32),
        after=_native_record(42, "33" * 32),
        result=_transition_result(motor_action),
    )

    observed = production._attempt_unattended_interval()

    assert observed["delivered"] is True
    assert observed["outcome"] == "continuous_environment_observed"
    assert production._autonomy_record()["action_observed"] is False


def test_exactly_unchanged_interval_is_rest_not_activity(monkeypatch) -> None:
    unchanged = _native_record(50, "33" * 32)
    result = _transition_result(None)
    result["totals"] = {
        **result["totals"],
        "complete_neuron_fractal_count": 0,
        "partial_cue_reassembly_count": 0,
        "physically_transitioned_neuron_count": 0,
    }
    _mount_translation_boundary(
        monkeypatch,
        before=unchanged,
        after=dict(unchanged),
        result=result,
    )

    observed = production._attempt_unattended_interval()

    assert observed["delivered"] is True
    assert observed["outcome"] == "no_internal_cause"
    assert observed["motor_action"] is None
    assert not any(
        observed["measured"]["energy_coordinate_changes"].values()
    )
    assert observed["measured"]["exact_energy_coordinates_resident"] is True
    assert observed["measured"]["exact_energy_coordinates_transported"] is False
    autonomy = production._autonomy_record()
    assert autonomy["available"] is False
    assert autonomy["action_observed"] is False
    assert "rest, not activity" in autonomy["reason"]


def test_unattended_observer_never_copies_unbounded_energy_coordinates(
    monkeypatch,
) -> None:
    huge = 10**5000
    before = {
        key: (huge, 1) for key in production._UNATTENDED_EXACT_ENERGY_KEYS
    }
    before.update(organism_tick=60, state_sha256="44" * 32)
    after = dict(before)
    after["available_energy_zeptojoules"] = (huge - 1, 1)
    after.update(organism_tick=61, state_sha256="55" * 32)
    _mount_translation_boundary(
        monkeypatch,
        before=before,
        after=after,
        result=_transition_result(None),
    )

    observed = production._attempt_unattended_interval()
    public = production._autonomy_record()

    assert observed["outcome"] == "continuous_environment_observed"
    assert observed["measured"]["energy_coordinate_changes"] == {
        "available_energy_zeptojoules": True,
        "dissipated_energy_zeptojoules": False,
        "spent_energy_zeptojoules": False,
        "thermal_energy_zeptojoules": False,
    }
    encoded = production._canonical(public)
    assert b'"before"' not in encoded
    assert b'"after"' not in encoded


def test_external_intake_preempts_without_advancing_the_organism(monkeypatch) -> None:
    monkeypatch.setattr(production, "_restored", SimpleNamespace())
    monkeypatch.setattr(production, "_admission", SimpleNamespace())
    production._external_intake_waiting.set()
    try:
        observed = production._attempt_unattended_interval()
    finally:
        production._external_intake_waiting.clear()

    assert observed == production._last_unattended_pause
    assert observed["delivered"] is False
    assert observed["outcome"] == "deferred_external_intake_waiting"


def test_public_observation_read_is_inert(monkeypatch) -> None:
    attempted = threading.Event()
    monkeypatch.setattr(
        production,
        "_attempt_unattended_interval",
        lambda: attempted.set(),
    )
    monkeypatch.setattr(production, "_public_observation_body", b"{}")
    monkeypatch.setattr(production, "_public_observation_etag", '"test"')

    response = production.native_observation()

    assert response.status_code == 200
    assert json.loads(response.body) == {}
    assert attempted.is_set() is False


def test_one_process_thread_delivers_and_stops(monkeypatch) -> None:
    delivered = threading.Event()

    def one_interval() -> dict[str, object]:
        delivered.set()
        production._unattended_stop.set()
        return {"delivered": True}

    production._stop_unattended_time()
    monkeypatch.delenv(production.UNATTENDED_TIME_ENV, raising=False)
    monkeypatch.setattr(production, "_attempt_unattended_interval", one_interval)

    production._start_unattended_time()
    thread = production._unattended_thread
    assert thread is not None
    assert delivered.wait(1.0)
    production._stop_unattended_time()

    assert production._unattended_thread is None
    assert thread.is_alive() is False


def test_environment_can_disable_transport_without_creating_an_owner(
    monkeypatch,
) -> None:
    production._stop_unattended_time()
    monkeypatch.setenv(production.UNATTENDED_TIME_ENV, "0")

    observed = production._attempt_unattended_interval()
    production._start_unattended_time()

    assert observed["delivered"] is False
    assert observed["outcome"] == "disabled"
    assert production._unattended_thread is None
