"""Real-threading presence keepalive gates.

These tests create actual background reading pressure through ``read_word``.
The adversarial turn waits for the structural tick threshold itself instead
of assuming a particular machine can produce 1,500 ticks in six seconds.
Every engine is shut down so test workers cannot leak into later gates.
"""

import os
import threading
import time

from dsf_ai_service.v4.gualaloom_v5_engine import Coordinator, Guala


def _wake_tracked_sources(engine):
    for source in ("joe", "wc", "c1"):
        engine.coordinator.wake(
            source, engine, engine.needs, engine.atlas)


def test_concurrent_background_load_does_not_time_out_active_source():
    old_phased = os.environ.get("CONVERSE_PHASED")
    os.environ["CONVERSE_PHASED"] = "1"
    engine = Guala()
    _wake_tracked_sources(engine)
    stop = threading.Event()
    pressure_reached = threading.Event()
    background_errors = []
    original_emit = engine._emit_from_invariants

    def background_reader():
        index = 0
        while not stop.is_set():
            try:
                engine.read_word(
                    f"bgword{index % 20}", source="corpus")
            except Exception as error:
                background_errors.append(error)
                return
            index += 1

    def pressure_gated_emit(*args, **kwargs):
        deadline = time.monotonic() + 30.0
        while (
            engine.tick <= Coordinator.PRESENCE_TIMEOUT_TICKS
            and not background_errors
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        if engine.tick > Coordinator.PRESENCE_TIMEOUT_TICKS:
            pressure_reached.set()
        return original_emit(*args, **kwargs)

    background = threading.Thread(
        target=background_reader, daemon=True)
    engine._emit_from_invariants = pressure_gated_emit
    background.start()
    try:
        reply = engine.converse(
            "tell me something", source="joe").response
        assert not background_errors
        assert isinstance(reply, str)
        assert pressure_reached.is_set(), (
            "real background reading did not cross the presence timeout "
            "threshold within the 30-second test ceiling"
        )
        engine.coordinator.timeout_check(engine)
        assert engine.coordinator._presence["joe"] is True
    finally:
        stop.set()
        background.join(timeout=5)
        engine._emit_from_invariants = original_emit
        if old_phased is None:
            os.environ.pop("CONVERSE_PHASED", None)
        else:
            os.environ["CONVERSE_PHASED"] = old_phased
        engine.shutdown()


def test_concurrent_background_load_still_times_out_truly_absent_source():
    engine = Guala()
    _wake_tracked_sources(engine)
    stop = threading.Event()
    background_errors = []

    def background_reader():
        for index in range(3000):
            if stop.is_set():
                return
            try:
                engine.read_word(
                    f"bgword{index % 20}", source="corpus")
            except Exception as error:
                background_errors.append(error)
                return

    background = threading.Thread(
        target=background_reader, daemon=True)
    background.start()
    try:
        background.join(timeout=30)
        stop.set()
        assert not background.is_alive()
        assert not background_errors
        assert engine.tick > Coordinator.PRESENCE_TIMEOUT_TICKS

        engine.coordinator.timeout_check(engine)
        assert engine.coordinator._presence["wc"] is False
        assert engine.coordinator._presence["joe"] is False
        assert engine.coordinator._presence["c1"] is False
    finally:
        stop.set()
        background.join(timeout=5)
        engine.shutdown()


def test_default_path_survives_long_wait_for_lock():
    assert os.environ.get("CONVERSE_PHASED", "0") == "0"
    engine = Guala()
    _wake_tracked_sources(engine)
    hold_seconds = 4.0
    lock_acquired = threading.Event()

    def hold_lock():
        with engine.lock:
            lock_acquired.set()
            time.sleep(hold_seconds)

    holder = threading.Thread(target=hold_lock, daemon=True)
    holder.start()
    try:
        assert lock_acquired.wait(timeout=5)
        engine.coordinator._last_input_tick["joe"] = engine.tick

        started = time.monotonic()
        reply = engine.converse(
            "hello, are you there", source="joe").response
        elapsed = time.monotonic() - started
        holder.join(timeout=5)

        assert isinstance(reply, str)
        assert elapsed >= hold_seconds * 0.9
        engine.coordinator.timeout_check(engine)
        assert engine.coordinator._presence["joe"] is True
    finally:
        holder.join(timeout=5)
        engine.shutdown()
