"""
Real-threading adversarial tests for the dormant legacy daydream loop.

Matches the established pattern in tests/test_presence_keepalive_
concurrency.py and tests/test_read_sentence_lock_granularity_concurrency.py
(see those files' own docstrings): real Guala() instances, real
threading.Thread, real self.lock -- no mocks of the locking mechanism
itself. Production boot no longer calls start_daydream_loop(); these tests
exercise the retained method directly only so dormant code cannot silently
rot before the planned sense-triggered redesign replaces it.

_daydream_tick() already wraps ALL exceptions in the background loop
itself (try/except: pass in start_daydream_loop's _loop closure) so a
broken tick can never crash the process -- these tests check for that
condition directly via a wrapped tick counter instead of relying on an
uncaught exception to surface, and separately prove the loop does not
introduce a deadlock against the real self.lock used by read_word/
read_sentence/converse.
"""

import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402


def _stop_daydream(g):
    if getattr(g, '_daydream_thread', None) is not None:
        g._daydream_running = False
        g._daydream_thread.join(timeout=3)


def test_daydream_loop_concurrent_with_real_conversation_no_crash_no_deadlock():
    print("Concurrency test: real daydream-loop thread running alongside a "
          "real converse() turn and a real background reader -- no crash, "
          "no deadlock, bounded completion time...")

    g = Guala()
    for src in ("joe", "wc", "c1"):
        g.coordinator.wake(src, g, g.needs, g.atlas)

    # Real recent activity so _daydream_tick has a real seed to walk from
    # (otherwise it would spend the whole test hitting its own early
    # `if not recent_chis: return` -- not a meaningful adversarial check).
    g.read_sentence("the warm sun is bright today", source="corpus")

    tick_errors = []
    tick_count = {"n": 0}
    orig_tick = g._daydream_tick

    def _counting_tick():
        tick_count["n"] += 1
        try:
            orig_tick()
        except Exception as e:
            tick_errors.append(e)
            raise

    g._daydream_tick = _counting_tick
    g.start_daydream_loop()

    stop_flag = threading.Event()
    bg_errors = []

    def _background_reader():
        i = 0
        while not stop_flag.is_set():
            try:
                g.read_word(f"bgword{i % 20}", source="corpus")
            except Exception as e:
                bg_errors.append(e)
                return
            i += 1

    bg_thread = threading.Thread(target=_background_reader, daemon=True,
                                  name="bg-reader")
    bg_thread.start()

    # Run converse() on its own thread with a hard join timeout instead of
    # calling it inline -- a true deadlock must not be able to hang this
    # test process indefinitely; it must fail loudly instead.
    conv_result = {}

    def _do_converse():
        try:
            conv_result["reply"] = g.converse(
                "tell me something", source="joe").response
        except Exception as e:
            conv_result["error"] = e

    conv_thread = threading.Thread(target=_do_converse, daemon=True,
                                    name="conv-thread")
    t0 = time.monotonic()
    conv_thread.start()
    conv_thread.join(timeout=60)
    elapsed = time.monotonic() - t0
    conv_finished = not conv_thread.is_alive()

    stop_flag.set()
    bg_thread.join(timeout=5)
    _stop_daydream(g)
    g._daydream_tick = orig_tick

    assert conv_finished, (
        f"converse() did not complete within 60s with the daydream loop "
        "running concurrently -- possible deadlock introduced by wiring "
        "start_daydream_loop() into the real boot path")
    assert "error" not in conv_result, f"converse() raised: {conv_result.get('error')!r}"
    assert isinstance(conv_result.get("reply"), str)
    assert not bg_errors, f"background reader raised: {bg_errors}"
    assert not tick_errors, f"_daydream_tick raised: {tick_errors}"
    assert tick_count["n"] > 0, (
        "daydream loop never actually ticked during the test window -- "
        "test would be inconclusive, not a real adversarial check")

    print(f"  OK: converse() completed in {elapsed:.2f}s, daydream ticked "
          f"{tick_count['n']} times concurrently, zero errors on any thread")


def test_daydream_loop_survives_sustained_multithreaded_load():
    print("Concurrency test: daydream loop survives ~3s of sustained real "
          "concurrent load from multiple simultaneous readers/converse "
          "turns without crashing or hanging on shutdown...")

    g = Guala()
    for src in ("joe", "wc", "c1"):
        g.coordinator.wake(src, g, g.needs, g.atlas)
    g.read_sentence("a small cat sits near the warm fire", source="corpus")

    tick_errors = []
    orig_tick = g._daydream_tick

    def _guarded_tick():
        try:
            orig_tick()
        except Exception as e:
            tick_errors.append(e)
            raise

    g._daydream_tick = _guarded_tick
    g.start_daydream_loop()

    stop_flag = threading.Event()
    errors = []

    def _reader(tag):
        i = 0
        while not stop_flag.is_set():
            try:
                g.read_word(f"{tag}{i % 20}", source="corpus")
            except Exception as e:
                errors.append((tag, e))
                return
            i += 1

    def _converser(tag, source):
        i = 0
        while not stop_flag.is_set():
            try:
                g.converse(f"hello there {tag} {i}", source=source)
            except Exception as e:
                errors.append((tag, e))
                return
            i += 1
            time.sleep(0.05)

    threads = [
        threading.Thread(target=_reader, args=("reader_a",), daemon=True),
        threading.Thread(target=_reader, args=("reader_b",), daemon=True),
        threading.Thread(target=_converser, args=("joe_turn", "joe"), daemon=True),
        threading.Thread(target=_converser, args=("wc_turn", "wc"), daemon=True),
    ]
    for t in threads:
        t.start()

    time.sleep(3.0)
    stop_flag.set()
    for t in threads:
        t.join(timeout=10)
        assert not t.is_alive(), f"{t.name} did not stop within 10s -- possible deadlock"

    _stop_daydream(g)
    g._daydream_tick = orig_tick

    assert not errors, f"real concurrent activity raised: {errors}"
    assert not tick_errors, f"_daydream_tick raised under sustained load: {tick_errors}"
    print(f"  OK: 3s of sustained 4-thread real load + daydream loop -- "
          f"all threads stopped cleanly, zero errors, final tick={g.tick}")


if __name__ == "__main__":
    tests = [
        test_daydream_loop_concurrent_with_real_conversation_no_crash_no_deadlock,
        test_daydream_loop_survives_sustained_multithreaded_load,
    ]
    failures = []
    for t in tests:
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            failures.append((t.__name__, str(e)))
    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED: {len(failures)}/{len(tests)}")
        for name, err in failures:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print(f"ALL {len(tests)} CONCURRENCY TESTS PASSED")
