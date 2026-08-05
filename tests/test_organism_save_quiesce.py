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
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
