import os
import queue
import sys
import threading
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _bare_engine():
    """Build only the lifecycle-bearing surface needed by these unit tests."""
    engine = Guala.__new__(Guala)
    engine._engine_quiesced = False
    engine._engine_quiescence_complete = False
    engine._engine_mutation_condition = threading.Condition()
    engine._engine_mutation_admission_open = True
    engine._engine_active_mutations = 0
    engine._engine_mutation_local = threading.local()
    engine._engine_raw_threads = set()
    engine._engine_raw_threads_started = 0
    engine._engine_raw_threads_completed = 0
    engine._reading_stop = threading.Event()
    engine._reading_thread = None
    engine._daydream_running = False
    engine._daydream_thread = None
    engine._live_converse_pending = 0
    engine._live_converse_state_lock = threading.Lock()
    engine._auditory_incremental_terminals = SimpleNamespace(
        authority_counts=lambda: {
            "issued_terminal_authorities": 0,
            "in_flight_terminal_authorities": 0,
        }
    )
    engine._organism_queue = None
    engine._organism_worker_thread = None
    engine._organism_sensory_queue = queue.Queue()
    engine._tapestry_queue = None
    engine._tapestry_worker_thread = None
    engine._diary_queue = None
    engine._diary_thread = None
    engine._spike_bus = None
    engine._corpora = {}
    return engine


def _wait_until_closed(engine, timeout=1.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with engine._engine_mutation_condition:
            if not engine._engine_mutation_admission_open:
                return
        time.sleep(0.001)
    raise AssertionError("engine mutation admission did not close")


def test_quiescence_waits_for_inherited_background_mutation():
    engine = _bare_engine()
    worker_started = threading.Event()
    release_worker = threading.Event()
    worker_finished = threading.Event()
    result = {}

    def accepted_continuation():
        worker_started.set()
        assert release_worker.wait(1.0)
        engine.add_corpus("accepted", "Accepted", ["one sentence"])
        worker_finished.set()

    def quiesce():
        result["certificate"] = engine.strict_shutdown(timeout=1.0)

    with engine._engine_mutation_scope("foreground"):
        engine._start_engine_background_thread(
            accepted_continuation, name="accepted-continuation")
        assert worker_started.wait(1.0)
        quiesce_thread = threading.Thread(target=quiesce)
        quiesce_thread.start()
        _wait_until_closed(engine)

    with pytest.raises(RuntimeError, match="rejected during quiescence"):
        engine.add_corpus("late", "Late", ["must be rejected"])
    assert quiesce_thread.is_alive()

    release_worker.set()
    assert worker_finished.wait(1.0)
    quiesce_thread.join(timeout=1.0)
    assert not quiesce_thread.is_alive()

    certificate = result["certificate"]
    assert "accepted" in engine._corpora
    assert certificate["active_mutations"] == 0
    assert certificate["raw_threads"]["started"] == 1
    assert certificate["raw_threads"]["completed"] == 1
    assert certificate["raw_threads"]["alive"] == []


def test_strict_shutdown_propagates_incomplete_background_work():
    engine = _bare_engine()
    release_worker = threading.Event()

    with engine._engine_mutation_scope("foreground"):
        worker = engine._start_engine_background_thread(
            lambda: release_worker.wait(1.0), name="blocked-continuation")

    with pytest.raises(RuntimeError, match=r"mutation\(s\) active"):
        engine.strict_shutdown(timeout=0.01)
    assert not engine._engine_quiescence_complete

    release_worker.set()
    worker.join(timeout=1.0)
    certificate = engine.strict_shutdown(timeout=1.0)
    assert certificate["raw_threads"]["completed"] == 1


def test_spike_bus_delivery_counts_are_retained_in_certificate():
    engine = _bare_engine()

    class FakeSpikeBus:
        injected_count = 7
        delivered_count = 4
        dropped_count = 1
        _thread = None

        def __init__(self):
            self.queued = 2
            self.quiesce_timeout = None

        def qsize(self):
            return self.queued

        def quiesce(self, timeout):
            self.quiesce_timeout = timeout
            self.delivered_count = 6
            self.queued = 0

    spike_bus = FakeSpikeBus()
    engine._spike_bus = spike_bus
    certificate = engine.strict_shutdown(timeout=1.0)

    assert spike_bus.quiesce_timeout is not None
    assert certificate["spike_bus"] == {
        "enabled": True,
        "injected_before_drain": 7,
        "delivered_before_drain": 4,
        "dropped_before_drain": 1,
        "queued_before_drain": 2,
        "injected": 7,
        "delivered": 6,
        "dropped": 1,
        "queued": 0,
        "thread_alive": False,
    }


def test_direct_mutation_entry_is_rejected_after_strict_cleanup():
    engine = _bare_engine()
    engine.add_corpus("before", "Before", ["accepted"])
    engine.strict_shutdown(timeout=1.0)

    with pytest.raises(RuntimeError, match="add_corpus"):
        engine.add_corpus("after", "After", ["rejected"])
    assert set(engine._corpora) == {"before"}


def test_real_engine_drains_mutation_queues_and_spikes(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "1")
    monkeypatch.setenv("SELF_VOICE_AUDIO_ENABLED", "0")
    engine = Guala()
    engine.read_sentence("the warm sun rises", source="corpus")

    certificate = engine.strict_shutdown(timeout=30.0)

    assert certificate["queues"]
    assert all(
        details == {"unfinished": 0, "queued": 0}
        for details in certificate["queues"].values())
    spike = certificate["spike_bus"]
    assert spike["injected"] > 0
    assert spike["injected"] == spike["delivered"] + spike["dropped"]
    assert spike["queued"] == 0
    assert spike["thread_alive"] is False
