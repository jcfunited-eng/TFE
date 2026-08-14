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


def test_continuous_world_interval_reaches_native_action_and_sensed_return(
    monkeypatch,
) -> None:
    motor_action = {
        "moved": True,
        "signed_yaw_millidegrees": 5,
        "motor_unit_recruitment_count": 2,
        "world_revision": 17,
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
    assert autonomy["action"]["status"] == "native_motor_yaw_observed"
    assert autonomy["consequence"]["status"] == (
        "native_vestibular_consequence_observed"
    )
    assert autonomy["choice"]["available"] is False
    assert autonomy["thought"]["available"] is False


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
    assert all(
        value["before"] == value["after"]
        for key, value in observed["measured"].items()
        if key in production._UNATTENDED_EXACT_ENERGY_KEYS
    )
    autonomy = production._autonomy_record()
    assert autonomy["available"] is False
    assert autonomy["action_observed"] is False
    assert "rest, not activity" in autonomy["reason"]


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
