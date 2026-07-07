"""spike_bus.py -- GL-CMD-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-EVE-20260707-v1.

Blueprint: GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v1 SS3.3 (spike propagation).

Central priority queue of pending spikes ordered by arrival time. A
dedicated background thread drains the queue and delivers each spike to
its target neuron's `receive_spike(spike)` once its arrival time has
elapsed.

STATUS: built and unit-tested in isolation. NOT wired into LoomBrain.step,
LoomCluster.step, or Guala's lifecycle -- see
GL-RPT-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-C1-20260707-v1.md for why
(halt condition: the wiring step would sever the production hot path from
the krimelack/DSF/psi_lattice computation that currently produces
everything chi_atlas/binding_atlas/recall/emission read; no specified
replacement exists). This module is self-contained infrastructure, usable
once that architectural question is resolved.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger("guala.spike_bus")


@dataclass(order=True)
class PendingSpike:
    arrival_time: float                # wall clock (time.monotonic()) when this spike arrives
    target_neuron_id: str = field(compare=False)
    source_neuron_id: str = field(compare=False)
    weight: float = field(compare=False)
    metadata: dict = field(default_factory=dict, compare=False)


class SpikeBus:
    """neuron_registry: Dict[str, Any] (or any object supporting `.get(id)`)
    mapping neuron_id -> neuron instance. Neurons must expose
    `receive_spike(spike: PendingSpike) -> None`.
    """

    # How long the delivery loop blocks on an empty queue before re-checking
    # the stop signal. Bounds shutdown latency without busy-spinning.
    _QUEUE_POLL_TIMEOUT_S = 0.01
    # A spike whose arrival is still in the future gets requeued and the
    # loop sleeps at most this long before re-checking the head of the
    # queue (a new, earlier-arriving spike may be injected in the meantime).
    _MAX_WAIT_SLEEP_S = 0.05
    # Below this remaining wait, deliver immediately rather than requeue --
    # avoids churning the queue for negligible waits.
    _MIN_REQUEUE_WAIT_S = 0.001

    def __init__(self, neuron_registry: Dict[str, object]):
        self._queue: "queue.PriorityQueue[PendingSpike]" = queue.PriorityQueue()
        self._neuron_registry = neuron_registry
        self._stopping = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # Observability -- read by health checks / harness event-driven
        # verification (queue depth over time, delivered/dropped counts).
        self.delivered_count = 0
        self.dropped_count = 0
        self.injected_count = 0

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stopping.clear()
        self._thread = threading.Thread(
            target=self._delivery_loop, daemon=True, name="spike_bus"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stopping.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def qsize(self) -> int:
        return self._queue.qsize()

    def inject(self, target_id: str, source_id: str, weight: float,
               arrival_delay_ms: float = 0.0, metadata: Optional[dict] = None) -> None:
        arrival_time = time.monotonic() + arrival_delay_ms / 1000.0
        spike = PendingSpike(
            arrival_time=arrival_time,
            target_neuron_id=target_id,
            source_neuron_id=source_id,
            weight=weight,
            metadata=metadata or {},
        )
        self._queue.put(spike)
        self.injected_count += 1

    def _delivery_loop(self) -> None:
        while not self._stopping.is_set():
            try:
                spike = self._queue.get(timeout=self._QUEUE_POLL_TIMEOUT_S)
            except queue.Empty:
                continue

            now = time.monotonic()
            wait = spike.arrival_time - now
            if wait > self._MIN_REQUEUE_WAIT_S:
                # Not due yet -- put it back and wait a bounded amount
                # before re-checking (a newer, earlier spike may arrive,
                # or the stop signal may fire).
                self._queue.put(spike)
                time.sleep(min(wait, self._MAX_WAIT_SLEEP_S))
                continue

            target = self._neuron_registry.get(spike.target_neuron_id)
            if target is None:
                self.dropped_count += 1
                logger.warning("spike dropped -- unknown target %s", spike.target_neuron_id)
                continue
            try:
                target.receive_spike(spike)
                self.delivered_count += 1
            except Exception:
                self.dropped_count += 1
                logger.exception("spike delivery failed, target=%s", spike.target_neuron_id)
