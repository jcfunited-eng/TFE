"""Headless proof of unattended time (autonomy increment 1, 2026-08-06).

The PASSAGE OF TIME is the medium, never a cause: production grants the
organism genuinely dark, silent, unattended intervals (the same lawful
construction as a lesson's ended hops) and reports ONLY what measurably
happened in them.  Proven here, on the real native organism:

- an unattended interval commits its hops, persists exactly once, and the
  truth-coupled autonomy observation reports the measured category;
- a zero-change interval reports genuine rest (``no_internal_cause``),
  never activity;
- an external intake holding the transition lock preempts unattended time
  cleanly (the organism is untouched);
- an energy-exhausted body pauses unattended time with the honest reason;
- the env switch disables the medium entirely;
- autonomous thought, action, attention, and choice remain unmounted and
  ``action_observed`` stays False in every state.
"""

from __future__ import annotations

import json
import threading

import pytest

from dsf_ai_service import native_production_app as production


@pytest.fixture()
def lean_app(monkeypatch, tmp_path):
    monkeypatch.setattr(production, "STATE_ROOT", tmp_path)
    monkeypatch.delenv(production.UNATTENDED_TIME_ENV, raising=False)
    monkeypatch.delenv(production.UNATTENDED_CADENCE_ENV, raising=False)
    yield tmp_path
    production._stop_unattended_time()
    production._restored = None
    production._admission = None
    production._boot_error = None
    production._public_observation_body = None
    production._public_observation_etag = None
    production._last_transition_evidence = None
    production._last_unattended_evidence = None
    production._last_unattended_pause = None
    production._pcm_sessions.clear()


def _autonomy() -> dict:
    return json.loads(production._public_observation_body)["autonomy"]


def _assert_no_action_claim(autonomy: dict) -> None:
    assert autonomy["action_observed"] is False
    for name in ("thought", "action", "attention", "choice", "consequence"):
        assert autonomy[name]["available"] is False
        assert autonomy[name]["status"] == "not_mounted"


def test_unattended_interval_commits_persists_and_truth_couples(lean_app) -> None:
    production._startup()
    genesis_sha = production._restored.pointer.state_sha256

    # Before any interval: the autonomy section refuses honestly.
    autonomy = _autonomy()
    assert autonomy["available"] is False
    assert autonomy["status"] == "no_unattended_interval_this_process"
    _assert_no_action_claim(autonomy)

    # First-ever dark interval: the first exact dark optical occurrence
    # settles the retinal cohort and the metabolism comes alive — measured
    # energy movement, categorized as self-maintenance.  (Measured
    # 2026-08-06 on this exact path: 27 neurons transition, 27 genuine
    # fractals, the recovery reservoir fills and its genesis cost is spent.)
    first = production._attempt_unattended_interval()
    assert first["delivered"] is True
    assert first["outcome"] == "self_maintenance_observed"
    assert first["hop_count"] == production.UNATTENDED_HOPS_PER_INTERVAL
    assert first["measured"]["recovery_fuel_quanta_delta"] > 0

    # The interval persisted exactly like a lesson: durable CURRENT advanced.
    assert production._restored.pointer.state_sha256 != genesis_sha
    assert (
        production._restored.pointer.state_sha256 == first["state_sha256"]
    )
    assert (
        production._restored.pointer.organism_tick
        == production.UNATTENDED_HOPS_PER_INTERVAL
    )
    evidence = production._last_transition_evidence
    assert evidence["intake"].startswith("unattended-interval:")
    assert evidence["hop_count"] == production.UNATTENDED_HOPS_PER_INTERVAL

    # Truth-coupling, positive direction: measured change flips available.
    autonomy = _autonomy()
    assert autonomy["available"] is True
    assert autonomy["status"] == "self_maintenance_observed"
    assert autonomy["self_maintenance"]["recovery_fuel_quanta_delta"] > 0
    _assert_no_action_claim(autonomy)

    # Second interval: the settled newborn body genuinely rests — zero
    # physical change, reported as rest, never as activity.
    second = production._attempt_unattended_interval()
    assert second["delivered"] is True
    assert second["outcome"] == "no_internal_cause"
    measured = second["measured"]
    assert measured["physically_transitioned_neuron_count"] == 0
    assert all(
        measured[f"{key}_delta"] == 0
        for key in production._UNATTENDED_ENERGY_KEYS
    )

    # Truth-coupling, negative direction: zero change flips available off.
    autonomy = _autonomy()
    assert autonomy["available"] is False
    assert autonomy["status"] == "no_internal_cause"
    assert "rest, not activity" in autonomy["reason"]
    _assert_no_action_claim(autonomy)

    # Restart from disk: the unattended generations restore exactly.
    production._startup()
    assert (
        production._restored.pointer.organism_tick
        == 2 * production.UNATTENDED_HOPS_PER_INTERVAL
    )


def test_external_intake_preempts_unattended_time_cleanly(lean_app) -> None:
    production._startup()
    tick_before = production._restored.pointer.organism_tick
    sha_before = production._restored.pointer.state_sha256

    # An external intake holds the transition lock; unattended time must
    # step aside without waiting and without touching the organism.
    acquired = production._transition_lock.acquire(blocking=False)
    assert acquired
    try:
        outcome = production._attempt_unattended_interval()
    finally:
        production._transition_lock.release()
    assert outcome["delivered"] is False
    assert outcome["outcome"] == "deferred_external_intake_in_flight"
    assert "never contends" in outcome["reason"]
    assert production._restored.pointer.organism_tick == tick_before
    assert production._restored.pointer.state_sha256 == sha_before

    # Once the external intake releases the lock, unattended time resumes
    # normally on the next attempt.
    resumed = production._attempt_unattended_interval()
    assert resumed["delivered"] is True


def test_energy_exhausted_body_pauses_unattended_time(lean_app, monkeypatch) -> None:
    production._startup()
    tick_before = production._restored.pointer.organism_tick

    real_record = production._native_record

    def exhausted_record():
        record = real_record()
        record["energy_exhausted"] = True
        return record

    monkeypatch.setattr(production, "_native_record", exhausted_record)
    outcome = production._attempt_unattended_interval()
    assert outcome["delivered"] is False
    assert outcome["outcome"] == "paused_energy_exhausted"
    assert "must not burn residual fuel" in outcome["reason"]
    assert production._restored.pointer.organism_tick == tick_before

    # The pause is visible in the truth-coupled autonomy observation.
    autonomy = _autonomy()
    assert autonomy["unattended_time"]["last_pause"]["outcome"] == (
        "paused_energy_exhausted"
    )
    _assert_no_action_claim(autonomy)


def test_env_switch_disables_unattended_time(lean_app, monkeypatch) -> None:
    production._startup()
    monkeypatch.setenv(production.UNATTENDED_TIME_ENV, "0")
    tick_before = production._restored.pointer.organism_tick

    outcome = production._attempt_unattended_interval()
    assert outcome["delivered"] is False
    assert outcome["outcome"] == "disabled"
    assert production._restored.pointer.organism_tick == tick_before

    production._start_unattended_time()
    assert production._unattended_thread is None

    # The observation cache is rebuilt per committed transition; rebuild it
    # here to read the config truthfully (in production the env switch is
    # fixed at process start).
    production._refresh_public_observation_cache()
    autonomy = _autonomy()
    assert autonomy["unattended_time"]["enabled"] is False


def test_fed_then_rested_organism_reports_measured_self_maintenance(
    lean_app,
) -> None:
    """Fed-then-rested: lessons burn fuel and separate membrane charge; the
    feed regenerates fuel and vents heat; unattended intervals then measure
    the organism's own retained-state physics (settling, and the membrane
    return when its elementary-charge floor and dissipation lattice allow a
    whole charge to move)."""

    production._startup()
    # First dark interval settles the cohort and wakes the metabolism.
    first = production._attempt_unattended_interval()
    assert first["outcome"] == "self_maintenance_observed"

    for _ in range(2):
        response = production.teach_card({"card_id": "alphabet-a"})
        assert response.status_code == 200
    after_lessons = production._native_record()
    assert after_lessons["recovery_spent_quanta"] > 0
    assert after_lessons["separated_elementary_charges"] != 0

    # Feed: authored nutrition regenerates fuel from spent material.
    fed = production._perform_nutrition_intake(100)
    assert fed["nutrition"]["regenerated_fuel_quanta"] == 100

    # Rest: the interval measures what ACTUALLY happened.  Measured on this
    # path (2026-08-06): tens of neurons keep settling per interval with
    # zero-or-single-quantum ledger movement, so the honest category is
    # settling or self-maintenance — and the observation must claim exactly
    # the measured one, never action.
    rested = production._attempt_unattended_interval()
    assert rested["delivered"] is True
    assert rested["outcome"] in (
        "retained_state_settling_observed",
        "self_maintenance_observed",
    )
    assert rested["measured"]["physically_transitioned_neuron_count"] > 0

    autonomy = _autonomy()
    assert autonomy["available"] is True
    assert autonomy["status"] == rested["outcome"]
    _assert_no_action_claim(autonomy)


def test_unattended_loop_thread_delivers_and_stops(lean_app, monkeypatch) -> None:
    production._startup()
    monkeypatch.setenv(production.UNATTENDED_CADENCE_ENV, "0.05")

    production._start_unattended_time()
    assert production._unattended_thread is not None
    assert production._unattended_thread.is_alive()
    try:
        delivered = threading.Event()

        def wait_for_interval() -> None:
            import time

            deadline = time.monotonic() + 60.0
            while time.monotonic() < deadline:
                if production._last_unattended_evidence is not None:
                    delivered.set()
                    return
                time.sleep(0.05)

        wait_for_interval()
        assert delivered.is_set(), "loop never granted an interval"
    finally:
        production._stop_unattended_time()
    assert production._unattended_thread is None
