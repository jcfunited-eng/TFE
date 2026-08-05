"""Read-only STDP snapshot and endpoint verification.

Activity-bearing cases use the organism sensory queue. Typed words are not
used to manufacture sensory fields or populate the retired word-neuron map.
"""

import importlib
import os
import sys
import time


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ.setdefault("SUBSTRATE_MODE", "embedded")


def _fresh_guala(event_driven=True):
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1" if event_driven else "0"
    return Guala()


def _inject_sensory_activity(guala, *, count):
    os.environ["SENSORY_SPIKE_INJECTION_ENABLED"] = "1"
    hemisphere_id = guala.organism.brain.hemispheres[0].hemi_id
    for tick in range(count):
        guala._enqueue_organism_sensory(
            hemisphere_id,
            [0.1, 0.2, 0.3, 0.4],
            tick=tick + 1,
            input_chi=5,
        )
    guala._organism_sensory_queue.join()
    deadline = time.monotonic() + 1.0
    while (
        time.monotonic() < deadline
        and guala._spike_bus.delivered_count
        < guala._spike_bus.injected_count
    ):
        time.sleep(0.01)


def test_snapshot_on_fresh_boot_no_fires():
    import dsf_ai_service.app as appmod

    guala = _fresh_guala()
    try:
        snapshot = appmod._build_stdp_snapshot(guala)
        assert snapshot["word_neuron_map"]["word_neuron_map_size"] == 0
        assert snapshot["word_neuron_map"]["words_with_only_one_neuron"] == 0
        assert (
            snapshot["synapse_weight_distribution"]["total_synapses_updated"]
            == 0
        )
        assert snapshot["fire_event_metrics"]["total_fire_events_since_boot"] == 0
        assert (
            snapshot["fire_event_metrics"]["neurons_never_fired"]
            == len(guala._all_neurons())
        )
        assert snapshot["spike_bus_metrics"]["enabled"] is True
        assert snapshot["spike_bus_metrics"]["spike_queue_depth"] == 0
        assert (
            snapshot["membrane_state"][
                "neurons_currently_above_emission_threshold"
            ]
            == 0
        )
        assert snapshot["substrate_identity"]["EVENT_DRIVEN_SUBSTRATE"] == "1"
        assert snapshot["substrate_identity"]["RECALL_BACKEND"] == "legacy"
        assert "unknown" in snapshot["substrate_identity"]["task_def"]
        assert snapshot["diagnostics"]["neurons_total"] == len(
            guala._all_neurons()
        )
        assert snapshot["diagnostics"]["neurons_snapshot_ok"] == len(
            guala._all_neurons()
        )
        assert snapshot["diagnostics"]["neurons_snapshot_failed"] == 0
        assert snapshot["diagnostics"]["neuron_snapshot_sample_error"] is None
    finally:
        guala.shutdown()


def test_snapshot_isolates_per_neuron_failure():
    import dsf_ai_service.app as appmod

    guala = _fresh_guala()
    try:
        all_neurons = guala._all_neurons()
        assert len(all_neurons) >= 2
        victim = all_neurons[0]
        del victim._neuron_lock

        snapshot = appmod._build_stdp_snapshot(guala)
        diagnostics = snapshot["diagnostics"]
        assert diagnostics["neurons_total"] == len(all_neurons)
        assert diagnostics["neurons_snapshot_failed"] == 1
        assert diagnostics["neurons_snapshot_ok"] == len(all_neurons) - 1
        assert "_neuron_lock" in diagnostics["neuron_snapshot_sample_error"]
    finally:
        guala.shutdown()


def test_snapshot_reflects_physical_sensory_injection_and_stdp():
    import dsf_ai_service.app as appmod

    guala = _fresh_guala()
    try:
        _inject_sensory_activity(guala, count=5)
        snapshot = appmod._build_stdp_snapshot(guala)

        assert snapshot["word_neuron_map"]["word_neuron_map_size"] == 0
        assert dict(guala._word_neuron_map) == {}
        assert snapshot["fire_event_metrics"]["total_fire_events_since_boot"] > 0
        assert (
            snapshot["fire_event_metrics"]["neurons_that_have_ever_fired"]
            > 0
        )
        assert (
            snapshot["spike_bus_metrics"]["total_spikes_injected_since_boot"]
            > 0
        )
        assert (
            snapshot["spike_bus_metrics"]["total_spikes_delivered_since_boot"]
            > 0
        )
        top = snapshot["membrane_state"]["top_20_active_neurons"]
        assert top
        assert all(
            "neuron_id" in entry and "potential" in entry for entry in top
        )
    finally:
        guala.shutdown()
        os.environ.pop("SENSORY_SPIKE_INJECTION_ENABLED", None)


def test_snapshot_degrades_gracefully_without_spike_bus():
    import dsf_ai_service.app as appmod

    guala = _fresh_guala(event_driven=False)
    try:
        assert guala._spike_bus is None
        snapshot = appmod._build_stdp_snapshot(guala)
        assert snapshot["spike_bus_metrics"]["enabled"] is False
        assert snapshot["substrate_identity"]["EVENT_DRIVEN_SUBSTRATE"] == "0"
    finally:
        guala.shutdown()


def test_snapshot_never_mutates_membrane_state():
    import dsf_ai_service.app as appmod

    guala = _fresh_guala()
    try:
        _inject_sensory_activity(guala, count=1)
        before = {
            neuron.neuron_id: neuron.membrane_potential
            for neuron in guala._all_neurons()
        }
        appmod._build_stdp_snapshot(guala)
        appmod._build_stdp_snapshot(guala)
        after = {
            neuron.neuron_id: neuron.membrane_potential
            for neuron in guala._all_neurons()
        }
        assert before == after
    finally:
        guala.shutdown()
        os.environ.pop("SENSORY_SPIKE_INJECTION_ENABLED", None)


def test_snapshot_completes_well_under_budget():
    import dsf_ai_service.app as appmod

    guala = _fresh_guala()
    try:
        _inject_sensory_activity(guala, count=10)
        started = time.monotonic()
        appmod._build_stdp_snapshot(guala)
        elapsed_ms = (time.monotonic() - started) * 1000.0
        assert elapsed_ms < 500.0
    finally:
        guala.shutdown()
        os.environ.pop("SENSORY_SPIKE_INJECTION_ENABLED", None)


def test_snapshot_includes_fire_rate_window_metrics_on_fresh_boot():
    import dsf_ai_service.app as appmod

    guala = _fresh_guala()
    try:
        snapshot = appmod._build_stdp_snapshot(guala)
        metrics = snapshot["fire_rate_window_metrics"]
        assert metrics["neurons_with_runaway_fire_pattern"] == 0
        assert metrics["runaway_neurons"] == []
        assert metrics["window_n"] > 0
        assert metrics["ceiling_hz"] > 0
        assert metrics["total_fire_breaker_trips_since_boot_or_restore"] == 0
    finally:
        guala.shutdown()


def test_fire_rate_window_metrics_flags_incident_reproduction():
    import dsf_ai_service.app as appmod
    from dsf_ai_service.loom_model.neuron import (
        FIRE_BREAKER_CEILING_HZ,
        FIRE_BREAKER_WINDOW_N,
    )

    now = time.monotonic()

    def _window(interval_seconds):
        return [
            now - (FIRE_BREAKER_WINDOW_N - 1 - index) * interval_seconds
            for index in range(FIRE_BREAKER_WINDOW_N)
        ]

    neuron_snapshots = [
        {
            "neuron_id": "runaway_n",
            "recent_fire_timestamps": _window(1.0 / 3800.0),
            "fire_breaker_trip_count": 5,
        },
        {
            "neuron_id": "normal_n",
            "recent_fire_timestamps": _window(1.0 / 20.0),
            "fire_breaker_trip_count": 0,
        },
        {
            "neuron_id": "quiet_n",
            "recent_fire_timestamps": [],
            "fire_breaker_trip_count": 0,
        },
        {
            "neuron_id": "sparse_n",
            "recent_fire_timestamps": [now - 10.0, now],
            "fire_breaker_trip_count": 0,
        },
    ]

    metrics = appmod._fire_rate_window_metrics(
        neuron_snapshots,
        {"runaway_n": "legacy-observational-label"},
    )

    assert metrics["window_n"] == FIRE_BREAKER_WINDOW_N
    assert metrics["ceiling_hz"] == FIRE_BREAKER_CEILING_HZ
    assert metrics["neurons_with_runaway_fire_pattern"] == 1
    assert len(metrics["runaway_neurons"]) == 1
    flagged = metrics["runaway_neurons"][0]
    assert flagged["neuron_id"] == "runaway_n"
    assert flagged["recent_fire_rate_hz"] > FIRE_BREAKER_CEILING_HZ
    assert flagged["word"] == "legacy-observational-label"
    assert metrics["total_fire_breaker_trips_since_boot_or_restore"] == 5


def test_route_requires_api_key_when_configured():
    old_key = os.environ.get("GUALALOOM_API_KEY")
    os.environ["GUALALOOM_API_KEY"] = "test-control-credential-" + "x" * 32
    try:
        import dsf_ai_service.app as appmod
        from fastapi.testclient import TestClient

        importlib.reload(appmod)
        guala = _fresh_guala()
        appmod._guala = guala
        try:
            client = TestClient(appmod.app)
            no_auth = client.get("/debug/stdp_state")
            assert no_auth.status_code == 401

            authenticated = client.get(
                "/debug/stdp_state",
                headers={"X-API-Key": os.environ["GUALALOOM_API_KEY"]},
            )
            assert authenticated.status_code == 200
            body = authenticated.json()
            assert "word_neuron_map" in body
            assert "substrate_identity" in body
        finally:
            guala.shutdown()
    finally:
        if old_key is None:
            os.environ.pop("GUALALOOM_API_KEY", None)
        else:
            os.environ["GUALALOOM_API_KEY"] = old_key
        import dsf_ai_service.app as appmod

        importlib.reload(appmod)


def test_route_returns_503_when_guala_not_loaded():
    import dsf_ai_service.app as appmod
    from fastapi.testclient import TestClient

    old_guala = appmod._guala
    appmod._guala = None
    try:
        client = TestClient(appmod.app)
        response = client.get("/debug/stdp_state")
        assert response.status_code == 503
    finally:
        appmod._guala = old_guala
