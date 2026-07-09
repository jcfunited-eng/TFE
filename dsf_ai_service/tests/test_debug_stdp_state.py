"""
GL-CMD-STDP-INTROSPECTION-EVE-20260707-v1: verification for the
read-only /debug/stdp_state endpoint. Exercises the pure snapshot
functions against a real Guala() boot (not production state) plus the
actual FastAPI route via TestClient.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")


def _fresh_guala(event_driven=True):
    """Sets EVENT_DRIVEN_SUBSTRATE for the construction AND leaves it set
    afterward -- matches real deployments, where the env var is fixed for
    the process's whole lifetime (set once at container launch), not
    restored mid-run. Caller is responsible for resetting it if needed
    between test cases."""
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1" if event_driven else "0"
    return Guala()


def test_snapshot_on_fresh_boot_no_fires():
    """Fresh Guala(), nothing injected yet -- every metric group must
    return sane zero/empty defaults, no crash."""
    import dsf_ai_service.app as appmod
    g = _fresh_guala()
    try:
        snap = appmod._build_stdp_snapshot(g)
        assert snap["word_neuron_map"]["word_neuron_map_size"] == 0
        assert snap["word_neuron_map"]["words_with_only_one_neuron"] == 0
        assert snap["synapse_weight_distribution"]["total_synapses_updated"] == 0
        assert snap["fire_event_metrics"]["total_fire_events_since_boot"] == 0
        assert snap["fire_event_metrics"]["neurons_never_fired"] == len(g._all_neurons())
        assert snap["spike_bus_metrics"]["enabled"] is True
        assert snap["spike_bus_metrics"]["spike_queue_depth"] == 0
        assert snap["membrane_state"]["neurons_currently_above_emission_threshold"] == 0
        assert snap["substrate_identity"]["EVENT_DRIVEN_SUBSTRATE"] == "1"
        assert snap["substrate_identity"]["RECALL_BACKEND"] == "legacy"
        # no ECS_CONTAINER_METADATA_URI_V4 locally -- must degrade gracefully, not raise
        assert "unknown" in snap["substrate_identity"]["task_def"]
        assert snap["diagnostics"]["neurons_total"] == len(g._all_neurons())
        assert snap["diagnostics"]["neurons_snapshot_ok"] == len(g._all_neurons())
        assert snap["diagnostics"]["neurons_snapshot_failed"] == 0
        assert snap["diagnostics"]["neuron_snapshot_sample_error"] is None
        print("test_snapshot_on_fresh_boot_no_fires: PASS")
    finally:
        g.shutdown()


def test_snapshot_isolates_per_neuron_failure():
    """Reproduces the real production finding: a neuron missing a field
    the snapshot expects (e.g. _neuron_lock, as happens when
    guala_organism.pkl.gz predates that field -- pickle.load() never
    re-runs __init__) must not blank out every OTHER neuron's real data.
    One broken neuron out of N must yield N-1 good snapshots, not 0."""
    import dsf_ai_service.app as appmod
    g = _fresh_guala()
    try:
        all_neurons = g._all_neurons()
        assert len(all_neurons) >= 2
        victim = all_neurons[0]
        del victim._neuron_lock  # simulates a pre-Phase-1-v2 unpickled neuron

        snap = appmod._build_stdp_snapshot(g)
        diag = snap["diagnostics"]
        assert diag["neurons_total"] == len(all_neurons)
        assert diag["neurons_snapshot_failed"] == 1
        assert diag["neurons_snapshot_ok"] == len(all_neurons) - 1
        assert "_neuron_lock" in diag["neuron_snapshot_sample_error"]
        print("test_snapshot_isolates_per_neuron_failure: PASS")
    finally:
        g.shutdown()


def test_snapshot_reflects_real_word_injection_and_stdp():
    """Inject 'dog' several times via the real dual-write step() path,
    then confirm the snapshot's fire/word/synapse metrics move off their
    zero defaults with real (not fabricated) numbers."""
    import dsf_ai_service.app as appmod
    g = _fresh_guala()
    try:
        for i in range(5):
            g.organism.brain.step("dog", tick=i, input_chi=42, modality="language")
        time.sleep(0.1)  # let the spike-bus delivery thread drain

        snap = appmod._build_stdp_snapshot(g)
        assert snap["word_neuron_map"]["word_neuron_map_size"] >= 1
        assert "dog" in dict(g._word_neuron_map).keys()
        assert snap["fire_event_metrics"]["total_fire_events_since_boot"] > 0
        assert snap["fire_event_metrics"]["neurons_that_have_ever_fired"] > 0
        assert snap["spike_bus_metrics"]["total_spikes_injected_since_boot"] > 0
        assert snap["spike_bus_metrics"]["total_spikes_delivered_since_boot"] > 0
        # membrane state top-active list should reference real neuron ids
        top = snap["membrane_state"]["top_20_active_neurons"]
        assert len(top) > 0
        assert all("neuron_id" in e and "potential" in e for e in top)
        print("test_snapshot_reflects_real_word_injection_and_stdp: PASS")
    finally:
        g.shutdown()


def test_snapshot_degrades_gracefully_without_spike_bus():
    """EVENT_DRIVEN_SUBSTRATE=0 -- no spike bus constructed. Endpoint
    must not crash, must report enabled=False."""
    import dsf_ai_service.app as appmod
    g = _fresh_guala(event_driven=False)
    try:
        assert g._spike_bus is None
        snap = appmod._build_stdp_snapshot(g)
        assert snap["spike_bus_metrics"]["enabled"] is False
        assert snap["substrate_identity"]["EVENT_DRIVEN_SUBSTRATE"] == "0"
        print("test_snapshot_degrades_gracefully_without_spike_bus: PASS")
    finally:
        g.shutdown()


def test_snapshot_never_mutates_membrane_state():
    """Read-only guarantee: calling the snapshot twice back-to-back must
    not itself change membrane_potential (only real spike delivery
    should)."""
    import dsf_ai_service.app as appmod
    g = _fresh_guala()
    try:
        g.organism.brain.step("dog", tick=1, input_chi=42, modality="language")
        time.sleep(0.1)
        before = {n.neuron_id: n.membrane_potential for n in g._all_neurons()}
        appmod._build_stdp_snapshot(g)
        appmod._build_stdp_snapshot(g)
        after = {n.neuron_id: n.membrane_potential for n in g._all_neurons()}
        assert before == after, "snapshot call must never mutate raw membrane_potential"
        print("test_snapshot_never_mutates_membrane_state: PASS")
    finally:
        g.shutdown()


def test_snapshot_completes_well_under_budget():
    """Dispatch requires <500ms even under load; on a small local
    organism this should be orders of magnitude faster."""
    import dsf_ai_service.app as appmod
    g = _fresh_guala()
    try:
        for i in range(10):
            g.organism.brain.step("dog", tick=i, input_chi=42, modality="language")
        time.sleep(0.1)
        t0 = time.monotonic()
        appmod._build_stdp_snapshot(g)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        assert elapsed_ms < 500.0, f"snapshot took {elapsed_ms:.1f}ms, over budget"
        print(f"test_snapshot_completes_well_under_budget: PASS ({elapsed_ms:.2f}ms)")
    finally:
        g.shutdown()


def test_snapshot_includes_fire_rate_window_metrics_on_fresh_boot():
    """Fresh Guala(), nothing fired yet -- the new metric group must be
    present with sane zero defaults, no crash."""
    import dsf_ai_service.app as appmod
    g = _fresh_guala()
    try:
        snap = appmod._build_stdp_snapshot(g)
        frw = snap["fire_rate_window_metrics"]
        assert frw["neurons_with_runaway_fire_pattern"] == 0
        assert frw["runaway_neurons"] == []
        assert frw["window_n"] > 0
        assert frw["ceiling_hz"] > 0
        assert frw["total_fire_breaker_trips_since_boot_or_restore"] == 0
        print("test_snapshot_includes_fire_rate_window_metrics_on_fresh_boot: PASS")
    finally:
        g.shutdown()


def test_fire_rate_window_metrics_flags_incident_reproduction():
    """Phase 1 delivery plan Step 2's own verification requirement:
    replicate the real 2026-07-08/09 incident's observed numbers
    (~3800 fires/sec, sustained) directly against the metric function
    (a pure function of neuron snapshots -- no live Guala boot needed)
    and confirm it is flagged, while a neuron firing at a realistic
    STDP-driven rate is not, and a neuron with no fire history at all
    doesn't crash the computation."""
    import dsf_ai_service.app as appmod
    from dsf_ai_service.loom_model.neuron import (
        FIRE_BREAKER_WINDOW_N, FIRE_BREAKER_CEILING_HZ,
    )

    now = time.monotonic()

    def _window(interval_s):
        return [now - (FIRE_BREAKER_WINDOW_N - 1 - i) * interval_s
                for i in range(FIRE_BREAKER_WINDOW_N)]

    runaway_timestamps = _window(1.0 / 3800.0)   # the real incident's own rate
    normal_timestamps = _window(1.0 / 20.0)      # realistic STDP-driven rate

    neuron_snapshots = [
        {"neuron_id": "runaway_n", "recent_fire_timestamps": runaway_timestamps,
         "fire_breaker_trip_count": 5},
        {"neuron_id": "normal_n", "recent_fire_timestamps": normal_timestamps,
         "fire_breaker_trip_count": 0},
        {"neuron_id": "quiet_n", "recent_fire_timestamps": [], "fire_breaker_trip_count": 0},
        {"neuron_id": "sparse_n", "recent_fire_timestamps": [now - 10.0, now],
         "fire_breaker_trip_count": 0},
    ]

    metrics = appmod._fire_rate_window_metrics(neuron_snapshots, {"runaway_n": "ball"})

    assert metrics["window_n"] == FIRE_BREAKER_WINDOW_N
    assert metrics["ceiling_hz"] == FIRE_BREAKER_CEILING_HZ
    assert metrics["neurons_with_runaway_fire_pattern"] == 1
    assert len(metrics["runaway_neurons"]) == 1
    flagged = metrics["runaway_neurons"][0]
    assert flagged["neuron_id"] == "runaway_n"
    assert flagged["recent_fire_rate_hz"] > FIRE_BREAKER_CEILING_HZ
    assert flagged["word"] == "ball"
    assert metrics["total_fire_breaker_trips_since_boot_or_restore"] == 5
    print("test_fire_rate_window_metrics_flags_incident_reproduction: PASS")


def test_route_requires_api_key_when_configured():
    """With GUALALOOM_API_KEY set, the route must 401 without the
    header and 200 with the correct one -- confirms it actually joined
    the existing _api_key_dep gate, not a no-op."""
    old_key = os.environ.get("GUALALOOM_API_KEY")
    os.environ["GUALALOOM_API_KEY"] = "test-secret-123"
    try:
        import importlib
        import dsf_ai_service.app as appmod
        importlib.reload(appmod)  # re-read GUALALOOM_API_KEY at module scope
        from fastapi.testclient import TestClient

        g = _fresh_guala()
        appmod._guala = g
        try:
            client = TestClient(appmod.app)
            r_noauth = client.get("/debug/stdp_state")
            assert r_noauth.status_code == 401, r_noauth.text

            r_auth = client.get("/debug/stdp_state", headers={"X-API-Key": "test-secret-123"})
            assert r_auth.status_code == 200, r_auth.text
            body = r_auth.json()
            assert "word_neuron_map" in body
            assert "substrate_identity" in body
            print("test_route_requires_api_key_when_configured: PASS")
        finally:
            g.shutdown()
    finally:
        if old_key is None:
            os.environ.pop("GUALALOOM_API_KEY", None)
        else:
            os.environ["GUALALOOM_API_KEY"] = old_key
        import importlib
        import dsf_ai_service.app as appmod
        importlib.reload(appmod)


def test_route_returns_503_when_guala_not_loaded():
    import dsf_ai_service.app as appmod
    from fastapi.testclient import TestClient
    old_guala = appmod._guala
    appmod._guala = None
    try:
        client = TestClient(appmod.app)
        r = client.get("/debug/stdp_state")
        assert r.status_code == 503
        print("test_route_returns_503_when_guala_not_loaded: PASS")
    finally:
        appmod._guala = old_guala


if __name__ == "__main__":
    test_snapshot_on_fresh_boot_no_fires()
    test_snapshot_isolates_per_neuron_failure()
    test_snapshot_reflects_real_word_injection_and_stdp()
    test_snapshot_degrades_gracefully_without_spike_bus()
    test_snapshot_never_mutates_membrane_state()
    test_snapshot_completes_well_under_budget()
    test_snapshot_includes_fire_rate_window_metrics_on_fresh_boot()
    test_fire_rate_window_metrics_flags_incident_reproduction()
    test_route_requires_api_key_when_configured()
    test_route_returns_503_when_guala_not_loaded()
    print("ALL PASS: test_debug_stdp_state")
