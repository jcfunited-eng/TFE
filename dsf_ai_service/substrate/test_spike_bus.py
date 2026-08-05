"""
GL-CMD-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-EVE-20260707-v1: unit tests for
spike_bus.py. Isolated -- no LoomNeuron/Guala involved, uses a stub target.
"""

import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dsf_ai_service.substrate.spike_bus import SpikeBus, PendingSpike


class _StubNeuron:
    def __init__(self, neuron_id):
        self.neuron_id = neuron_id
        self.received = []
        self.lock = threading.Lock()

    def receive_spike(self, spike):
        with self.lock:
            self.received.append(spike)


class _ExplodingNeuron:
    def receive_spike(self, spike):
        raise RuntimeError("boom")


def test_inject_and_deliver_immediate():
    target = _StubNeuron("n1")
    bus = SpikeBus(neuron_registry={"n1": target})
    bus.start()
    try:
        bus.inject(target_id="n1", source_id="n0", weight=0.5, arrival_delay_ms=0.0)
        deadline = time.time() + 2.0
        while not target.received and time.time() < deadline:
            time.sleep(0.01)
        assert len(target.received) == 1
        assert target.received[0].weight == 0.5
        assert target.received[0].source_neuron_id == "n0"
        assert bus.delivered_count == 1
    finally:
        bus.stop()
    print("test_inject_and_deliver_immediate: PASS")


def test_delay_ordering():
    target = _StubNeuron("n1")
    bus = SpikeBus(neuron_registry={"n1": target})
    bus.start()
    try:
        # inject out of order; later-arrival first, earlier-arrival second
        bus.inject(target_id="n1", source_id="late", weight=1.0, arrival_delay_ms=80.0)
        bus.inject(target_id="n1", source_id="early", weight=2.0, arrival_delay_ms=10.0)
        deadline = time.time() + 2.0
        while len(target.received) < 2 and time.time() < deadline:
            time.sleep(0.01)
        assert len(target.received) == 2
        assert target.received[0].source_neuron_id == "early"
        assert target.received[1].source_neuron_id == "late"
    finally:
        bus.stop()
    print("test_delay_ordering: PASS")


def test_unknown_target_dropped_not_crashed():
    bus = SpikeBus(neuron_registry={})
    bus.start()
    try:
        bus.inject(target_id="ghost", source_id="n0", weight=1.0)
        deadline = time.time() + 1.0
        while bus.dropped_count == 0 and time.time() < deadline:
            time.sleep(0.01)
        assert bus.dropped_count == 1
    finally:
        bus.stop()
    print("test_unknown_target_dropped_not_crashed: PASS")


def test_exception_in_receive_spike_does_not_kill_thread():
    target = _ExplodingNeuron()
    good_target = _StubNeuron("good")
    bus = SpikeBus(neuron_registry={"bad": target, "good": good_target})
    bus.start()
    try:
        bus.inject(target_id="bad", source_id="n0", weight=1.0)
        bus.inject(target_id="good", source_id="n0", weight=1.0)
        deadline = time.time() + 2.0
        while not good_target.received and time.time() < deadline:
            time.sleep(0.01)
        assert good_target.received, "delivery loop died after an exception"
        assert bus.dropped_count == 1
        assert bus.delivered_count == 1
    finally:
        bus.stop()
    print("test_exception_in_receive_spike_does_not_kill_thread: PASS")


def test_qsize_reflects_pending_and_stop_joins_cleanly():
    bus = SpikeBus(neuron_registry={})
    bus.start()
    try:
        bus.inject(target_id="ghost1", source_id="n0", weight=1.0, arrival_delay_ms=5000)
        bus.inject(target_id="ghost2", source_id="n0", weight=1.0, arrival_delay_ms=5000)
        assert bus.qsize() >= 1  # at least one still pending (far-future arrival)
    finally:
        t0 = time.time()
        bus.stop()
        stop_elapsed = time.time() - t0
    assert stop_elapsed < 5.5, f"stop() took too long: {stop_elapsed}s"
    print("test_qsize_reflects_pending_and_stop_joins_cleanly: PASS")


def test_concurrent_injection_from_multiple_threads():
    target = _StubNeuron("n1")
    N_THREADS, N_PER_THREAD = 8, 50
    bus = SpikeBus(
        neuron_registry={"n1": target},
        pending_capacity=N_THREADS * N_PER_THREAD,
    )
    bus.start()
    try:
        def worker():
            for _ in range(N_PER_THREAD):
                bus.inject(target_id="n1", source_id="w", weight=1.0)

        threads = [threading.Thread(target=worker) for _ in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        deadline = time.time() + 5.0
        expected = N_THREADS * N_PER_THREAD
        while len(target.received) < expected and time.time() < deadline:
            time.sleep(0.02)
        assert len(target.received) == expected, (
            f"expected {expected} spikes, got {len(target.received)} "
            f"(dropped={bus.dropped_count})")
    finally:
        bus.stop()
    print("test_concurrent_injection_from_multiple_threads: PASS")


def test_pending_admission_is_hard_bounded_and_fails_without_mutation():
    target = _StubNeuron("n1")
    bus = SpikeBus(
        neuron_registry={"n1": target},
        pending_capacity=2,
    )
    bus.inject(
        target_id="n1",
        source_id="first",
        weight=1.0,
        arrival_delay_ms=10.0,
    )
    bus.inject(
        target_id="n1",
        source_id="second",
        weight=1.0,
        arrival_delay_ms=10.0,
    )

    with pytest.raises(RuntimeError, match="pending capacity is full"):
        bus.inject(
            target_id="n1",
            source_id="rejected",
            weight=1.0,
            arrival_delay_ms=10.0,
        )

    assert bus.pending_capacity == 2
    assert bus.qsize() == 2
    assert bus.injected_count == 2


def test_full_bounded_queue_drains_every_accepted_future_spike():
    target = _StubNeuron("n1")
    bus = SpikeBus(
        neuron_registry={"n1": target},
        pending_capacity=2,
    )
    bus.inject(
        target_id="n1",
        source_id="first",
        weight=1.0,
        arrival_delay_ms=10.0,
    )
    bus.inject(
        target_id="n1",
        source_id="second",
        weight=1.0,
        arrival_delay_ms=10.0,
    )
    bus.start()

    bus.quiesce(timeout=2.0)

    assert bus.qsize() == 0
    assert bus.injected_count == 2
    assert bus.delivered_count == 2
    assert bus.dropped_count == 0
    assert bus._queue.unfinished_tasks == 0
    assert [item.source_neuron_id for item in target.received] == [
        "first",
        "second",
    ]


if __name__ == "__main__":
    test_inject_and_deliver_immediate()
    test_delay_ordering()
    test_unknown_target_dropped_not_crashed()
    test_exception_in_receive_spike_does_not_kill_thread()
    test_qsize_reflects_pending_and_stop_joins_cleanly()
    test_concurrent_injection_from_multiple_threads()
    print("ALL PASS: test_spike_bus")
