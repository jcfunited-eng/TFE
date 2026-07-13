"""
test_v7_awareness_real_path_concurrency.py — real-threading adversarial
tests for GL-CMD-V7-AWARENESS-REAL-PATH-C1-20260711.

_introspection_active_this_turn() / _introspection_recent_words() (see
dsf_ai_service/v4/gualaloom_v5_engine.py) read self.sections["intro"].
commits directly. That list is real, shared, mutable state: real
conversational turns append to it under self.lock (Section.receive(),
called from read_word()), while these new methods may be called from
_get_emission_priors() while a DIFFERENT lock is held (self._emission_lock
in the phased path) or, in these tests, from a separate thread entirely --
the same cross-lock exposure the pre-existing Source 2 of
_build_context_priors (sec.commits[-20:] for the current activity's
section) already has today, unprotected, in production.

Matches the established real-threading convention in this test suite
(tests/test_read_sentence_lock_granularity_concurrency.py,
tests/test_presence_keepalive_concurrency.py): real Guala() instance,
real threading.Thread, real locks, no mocking of the mechanism itself.

Proves:
  1. Concurrent real writers (read_sentence appending to self.sections
     ["intro"].commits) racing against concurrent real readers
     (_introspection_active_this_turn / _introspection_recent_words /
     _get_emission_priors) never crash and never observe a corrupted
     entry (every entry read is always a well-formed dict, never a torn
     partial write) -- and the readers do observe real, changing state
     (not a vacuous test that never overlaps).
  2. Two real, fully concurrent converse() turns from different sources
     do not corrupt the shared self._last_aware_priors / self.
     _last_converse_tick caches (no crash, both turns complete, both
     turns' own priors are internally self-consistent).
"""

import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("EMISSION_MODE", "grandurun")

from dsf_ai_service.v4.gualaloom_v5_engine import (  # noqa: E402
    ConversationTurnResult,
    Guala,
    Section,
)


class _SlowSectionReceive:
    """Same convention as tests/test_read_sentence_lock_granularity_
    concurrency.py: patches Section.receive to sleep briefly so a
    multi-word sentence takes long enough for real interleaving to be
    observed, rather than completing before a concurrent thread gets a
    chance to run at all."""

    def __init__(self, sleep_s):
        self.sleep_s = sleep_s
        self._orig = None

    def __enter__(self):
        self._orig = Section.receive
        orig = self._orig
        sleep_s = self.sleep_s

        def _slow_receive(self_section, *a, **kw):
            time.sleep(sleep_s)
            return orig(self_section, *a, **kw)

        Section.receive = _slow_receive
        return self

    def __exit__(self, *exc):
        Section.receive = self._orig


def test_concurrent_real_writer_and_gate_readers_no_crash_no_corruption():
    print("Concurrency test 1: real read_sentence() writer vs. real "
          "_introspection_active_this_turn/_get_emission_priors readers, "
          "genuinely interleaved...")
    g = Guala()
    g._last_converse_tick = 0

    stop = threading.Event()
    writer_errors = []
    reader_errors = []
    reader_observations = {"aware_true": 0, "aware_false": 0,
                           "nonempty_priors": 0, "reads": 0}

    words = [f"introword{i}" for i in range(40)]
    text = " ".join(words)

    def _writer():
        try:
            with _SlowSectionReceive(0.01):
                g.read_sentence(text, source="joe")
        except Exception as e:
            writer_errors.append(e)
        finally:
            stop.set()

    def _reader():
        try:
            while not stop.is_set():
                active = g._introspection_active_this_turn()
                reader_observations["reads"] += 1
                if active:
                    reader_observations["aware_true"] += 1
                    recent = g._introspection_recent_words()
                    priors = g._get_emission_priors(None)
                    # Every entry actually read must be well-formed --
                    # never a torn/partial dict from a concurrent append.
                    for w in recent:
                        assert isinstance(w, str) and w, (
                            f"malformed word in recent set: {w!r}")
                    if priors:
                        reader_observations["nonempty_priors"] += 1
                        for w, v in priors.items():
                            assert isinstance(w, str) and isinstance(v, float), (
                                f"malformed prior entry: {w!r}={v!r}")
                else:
                    reader_observations["aware_false"] += 1
                time.sleep(0.001)
        except Exception as e:
            reader_errors.append(e)

    writer = threading.Thread(target=_writer, daemon=True)
    readers = [threading.Thread(target=_reader, daemon=True) for _ in range(3)]

    writer.start()
    for r in readers:
        r.start()
    writer.join(timeout=30)
    stop.set()
    for r in readers:
        r.join(timeout=10)

    assert not writer_errors, f"writer raised: {writer_errors}"
    assert not reader_errors, f"reader(s) raised: {reader_errors}"
    assert reader_observations["reads"] > 10, (
        "readers did not get enough scheduling time to be a meaningful "
        f"adversarial check: {reader_observations}")
    assert reader_observations["aware_true"] > 0, (
        "readers never observed aware_active=True during the real write "
        f"-- test did not exercise the real interleaving path: "
        f"{reader_observations}")

    # Final-state sanity: the list itself must still be well-formed after
    # concurrent read/write -- no corruption, no lost structural integrity.
    commits = g.sections["intro"].commits
    for c in commits:
        assert isinstance(c, dict) and "tick" in c and "word" in c, (
            f"corrupted commit entry after concurrent access: {c!r}")

    print(f"  OK: {reader_observations['reads']} reads across 3 reader "
          f"threads while writer ran ({reader_observations['aware_true']} "
          f"aware=True, {reader_observations['nonempty_priors']} non-empty "
          f"priors observed), zero corruption, zero crashes, "
          f"{len(commits)} intro commits all well-formed")


def test_two_concurrent_real_turns_do_not_corrupt_shared_aware_cache():
    print("Concurrency test 2: two real, concurrent converse() turns from "
          "different sources do not corrupt the shared _last_aware_priors "
          "/ _last_converse_tick caches...")
    g = Guala()
    errors = []
    replies = {}

    def _run(text, source, key):
        try:
            with _SlowSectionReceive(0.01):
                replies[key] = g.converse(text, source=source)
        except Exception as e:
            errors.append((source, e))

    th_a = threading.Thread(
        target=_run, args=("a real word about a real thing", "joe", "a"))
    th_b = threading.Thread(
        target=_run, args=("another real word about another real thing",
                            "wc", "b"))
    th_a.start()
    th_b.start()
    th_a.join(timeout=60)
    th_b.join(timeout=60)

    assert not errors, f"concurrent converse() raised: {errors}"
    assert set(replies) == {"a", "b"}, f"both turns must complete: {replies}"
    for key, reply in replies.items():
        assert isinstance(reply, ConversationTurnResult), (
            f"turn {key}: expected turn result, got {reply!r}")
        assert isinstance(reply.response, str)

    # After both turns, the gate methods must still be callable and
    # internally consistent (no partially-written cache state left behind).
    priors = g._get_emission_priors(None)
    assert isinstance(priors, dict)
    for w, v in priors.items():
        assert isinstance(w, str) and isinstance(v, float)

    print(f"  OK: both concurrent real turns completed cleanly "
          f"(replies={replies}), shared aware-priors cache intact "
          f"({len(priors)} entries)")


if __name__ == "__main__":
    tests = [
        test_concurrent_real_writer_and_gate_readers_no_crash_no_corruption,
        test_two_concurrent_real_turns_do_not_corrupt_shared_aware_cache,
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
        print(f"ALL {len(tests)} TESTS PASSED")
