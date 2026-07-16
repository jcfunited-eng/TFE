"""Save-time organism quiescence (2026-07-16 seal incident).

The sealed-deploy full save pickled the organism while the lock-free
organism worker mutated its deques -> "deque mutated during iteration"
-> seal 503 -> deploy fail-back. The fix parks the organism worker and
the spike-bus delivery thread between items for the duration of the
pickle, with a bounded retry as the honest fallback.

These tests drive the REAL worker thread and the REAL save path.
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from dsf_ai_service.substrate.spike_bus import SpikeBus


def test_spike_bus_pause_parks_delivery_and_resume_releases():
    delivered = []

    class _Neuron:
        def receive_spike(self, spike):
            delivered.append(spike.target_neuron_id)

    bus = SpikeBus({"n1": _Neuron()})
    bus.start()
    try:
        assert bus.pause(5.0) is True
        bus.inject("n1", "src", 1.0)
        time.sleep(0.2)
        assert delivered == []  # parked: nothing delivers
        bus.resume()
        deadline = time.monotonic() + 5.0
        while not delivered and time.monotonic() < deadline:
            time.sleep(0.01)
        assert delivered == ["n1"]  # resume releases the held spike
    finally:
        bus.stop()


def test_spike_bus_pause_is_immediate_noop_when_never_started():
    bus = SpikeBus({})
    assert bus.pause(0.1) is True
    bus.resume()


@pytest.fixture()
def engine(tmp_path):
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    g = Guala()
    g.add_corpus("seed", "Seed", ["the sun rises in the morning"])
    g.load_full_state(str(tmp_path))
    yield g, str(tmp_path)
    try:
        g.shutdown()
    except Exception:
        pass


def test_full_save_survives_sustained_worker_mutation(engine):
    g, state_dir = engine
    stop = threading.Event()

    def _feeder():
        i = 0
        while not stop.is_set():
            g._enqueue_organism_remember(f"word{i % 97}")
            i += 1
            time.sleep(0.001)

    t = threading.Thread(target=_feeder, daemon=True)
    t.start()
    try:
        # Let the worker build a real backlog so the pickle window is
        # guaranteed to overlap live experience_word() mutation absent
        # the park (this is the exact seal-incident condition).
        time.sleep(1.0)
        for _ in range(3):
            # A mutation race raises via _raise_persistence_failures
            # ("full save failed ... deque mutated during iteration") --
            # exactly the 2026-07-16 seal 503. Not raising IS the fix.
            results = g.save_full_state(state_dir)
            assert any(k.startswith("guala_organism.pkl.gz")
                       for k in results), results
    finally:
        stop.set()
        t.join(timeout=5)


def test_worker_park_and_release_round_trip(engine):
    g, _ = engine
    g._enqueue_organism_remember("hello")  # ensures worker thread exists
    deadline = time.monotonic() + 5.0
    while g._organism_worker_thread is None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert g._organism_worker_thread is not None

    g._organism_pause_req.set()
    assert g._organism_pause_ack.wait(10.0), "worker never acknowledged park"
    # Parked: enqueued work must NOT be processed.
    before = g._organism_queue.unfinished_tasks
    g._enqueue_organism_remember("held")
    time.sleep(0.3)
    assert g._organism_queue.unfinished_tasks >= before + 1

    g._organism_pause_req.clear()
    deadline = time.monotonic() + 10.0
    while (g._organism_queue.unfinished_tasks > 0
           and time.monotonic() < deadline):
        time.sleep(0.05)
    assert g._organism_queue.unfinished_tasks == 0, "worker never resumed"


def test_settle_queues_drains_backlog_then_reports(engine):
    g, _ = engine
    stop = threading.Event()

    def _feeder():
        for i in range(300):
            if stop.is_set():
                return
            g._enqueue_organism_remember(f"settle{i % 53}")

    t = threading.Thread(target=_feeder, daemon=True)
    t.start()
    t.join(timeout=10)
    stop.set()
    # Generous budget: the worker chews the backlog; settle returns
    # telemetry instead of the 2026-07-16 seal 503.
    proof = g.settle_queues(budget_s=120.0, threshold=8)
    assert proof["settled"] is True
    assert proof["started"].get("organism", 0) >= 0
    assert all(v <= 8 for v in proof["remaining"].values())


def test_settle_queues_budget_expiry_names_the_backlog(engine):
    g, _ = engine
    # Park the worker so the backlog cannot drain, then demand settle
    # with a zero budget: it must raise naming the busy queue.
    g._enqueue_organism_remember("hold")
    deadline = time.monotonic() + 5.0
    while g._organism_worker_thread is None and time.monotonic() < deadline:
        time.sleep(0.01)
    g._organism_pause_req.set()
    assert g._organism_pause_ack.wait(10.0)
    try:
        for i in range(20):
            g._enqueue_organism_remember(f"stuck{i}")
        with pytest.raises(RuntimeError, match="settle budget expired.*organism"):
            g.settle_queues(budget_s=0.0, threshold=1)
    finally:
        g._organism_pause_req.clear()
