"""
test_read_sentence_lock_granularity_concurrency.py — real-threading
adversarial tests for GL-FIX-LOCK-GRANULARITY-C1-20260710.

Unlike test_read_sentence_lock_granularity.py (single-threaded functional
tests), this file drives ACTUAL concurrent threads against the real engine,
matching the established pattern in tests/test_presence_keepalive_
concurrency.py (see that file's own docstring) -- real Guala() instances,
real threading.Thread, real self.lock, no mocks of the locking mechanism
itself.

Background: read_sentence() (dsf_ai_service/v4/gualaloom_v5_engine.py) used
to wrap its ENTIRE per-word loop in `with self.lock:`, so the lock was held
for a whole sentence's worth of work (organism recall, tapestry settle
physics, section commits -- real, non-trivial per-word cost), contended by
camera/mic frame handling and periodic autosave. Measured live: 12-48s
stalls, a single turn spending ~20 of its ~50+ total seconds just waiting
on this lock. The fix narrows the critical section from "one sentence" to
"one word" (read_word() already wraps its own body in `with self.lock:`;
read_sentence() no longer additionally wraps the loop), made safe by
converting self._current_episode and self._prev_phase_vec from shared
instance attributes into call-local values threaded explicitly through
each read_word() call (see read_word()'s own docstring for the mechanism).

Tests here prove, with real threads:
  1. The lock is observably free DURING a real multi-word sentence, not
     held continuously start-to-finish.
  2. Two real concurrent sentences from different sources do not serialize
     for their full combined duration.
  3. Two real concurrent sentences from different sources, driven through
     genuinely interleaved read_word() calls, do NOT cross-contaminate each
     other's episode_ref or phase-vector rotation chain -- the actual
     correctness hazard the dispatch identified, not just a performance
     question.
"""

import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala, Section  # noqa: E402


class _SlowSectionReceive:
    """Context manager: patches Section.receive (called by every word,
    every section it's routed to) to sleep briefly before doing the real
    work, so a multi-word sentence takes long enough to observe interleaving
    -- same "monkeypatch a real call site with an artificial delay to
    simulate real substrate cost under load" convention
    test_presence_keepalive_concurrency.py already uses for
    _emit_from_invariants."""

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


def test_lock_releases_between_words_not_held_for_whole_sentence():
    """Uses a BLOCKING contender (not a non-blocking spin-poll) so it can't
    miss a brief release window and can't false-positive on a startup/
    teardown scheduling race either: it counts how many times a second
    thread manages to acquire+release g.lock WHILE the sentence is still
    genuinely in flight (timestamped acquisitions strictly before
    read_sentence() returns). Old (buggy) behavior holds the lock
    continuously for the whole sentence, so a contender can only ever grab
    it once, right at/after the very end -- never mid-flight. New (fixed)
    behavior releases it once per word, so a contender should win it
    several times while words are still being processed."""
    print("Concurrency test 1: self.lock is observably free DURING a real "
          "multi-word sentence (not held continuously start-to-finish)...")
    g = Guala()
    words = [f"lockword{i}" for i in range(12)]
    text = " ".join(words)

    with _SlowSectionReceive(0.03):
        acquisitions = []  # monotonic timestamps of successful acquire+release
        stop_contender = threading.Event()
        contender_errors = []

        def _contender():
            try:
                while not stop_contender.is_set():
                    got = g.lock.acquire(timeout=0.5)
                    if got:
                        acquisitions.append(time.monotonic())
                        g.lock.release()
                        time.sleep(0.001)  # brief yield so it doesn't hog re-acquisition
            except Exception as e:
                contender_errors.append(e)

        contender = threading.Thread(target=_contender, daemon=True)
        contender.start()
        t0 = time.monotonic()
        g.read_sentence(text, source="joe")
        t_end = time.monotonic()
        elapsed = t_end - t0
        stop_contender.set()
        contender.join(timeout=5)

    assert not contender_errors, f"contender raised: {contender_errors}"
    assert elapsed > 0.1, (
        f"sentence completed suspiciously fast ({elapsed:.3f}s) -- the "
        "artificial per-call slowdown may not have taken effect; test "
        "would be inconclusive")

    mid_flight = [t for t in acquisitions if t < t_end]
    print(f"  sentence took {elapsed:.3f}s; contender acquired the lock "
          f"{len(acquisitions)} times total, {len(mid_flight)} of them "
          "strictly before read_sentence() returned")
    # Empirically tuned against this exact test (12 words, 0.03s/receive()
    # call, 1ms contender yield): the OLD (pre-fix, whole-sentence-locked)
    # code consistently measures exactly 1 -- the single real release,
    # right at/after the very end, occasionally timestamped a hair before
    # t_end by scheduling noise, never truly mid-flight. The NEW (per-word)
    # code consistently measures 3-7 across repeated runs. >=2 sits with a
    # full point of margin below every observed NEW-code run and above
    # every observed OLD-code run.
    assert len(mid_flight) >= 2, (
        "REGRESSION: a competing thread almost never got g.lock while the "
        f"{len(words)}-word sentence ({elapsed:.3f}s) was still in flight "
        f"(only {len(mid_flight)} mid-flight acquisitions) -- the lock is "
        "still being held for the whole sentence, not released between "
        "words")

    # Directly operationalizes "no longer blocked for the FULL sentence
    # duration" (the dispatch's own wording): the longest single stretch
    # between two consecutive wins (or from sentence-start to the first
    # win) is how long a real third party (camera/mic/autosave) could be
    # made to wait in the worst case observed here. Under the old bug that
    # stretch is the ENTIRE sentence (elapsed); under the fix it should be
    # a small fraction of it (bounded by roughly one word's own critical
    # section, not the whole sentence).
    gap_points = [t0] + mid_flight + ([t_end] if not mid_flight else [])
    max_gap = max(b - a for a, b in zip(gap_points, gap_points[1:]))
    print(f"  longest single stretch without a lock hand-off: {max_gap:.3f}s "
          f"(sentence total {elapsed:.3f}s)")
    assert max_gap < elapsed * 0.6, (
        f"REGRESSION: the longest uninterrupted lock-hold stretch "
        f"({max_gap:.3f}s) is most of the sentence's total duration "
        f"({elapsed:.3f}s) -- a real third party could still be blocked "
        "for close to the full sentence, not just one word")
    print(f"  OK: a competing thread acquired the lock {len(mid_flight)} "
          "separate times WHILE the sentence was still running, longest "
          f"single wait was {max_gap:.3f}s of {elapsed:.3f}s total")


def test_concurrent_sentence_from_second_source_starts_well_before_first_finishes():
    """A cleaner, corrected version of the natural first idea for this test
    (measure each thread's own read_sentence() wall time and compare their
    sum against real concurrent wall time) -- that comparison turns out NOT
    to discriminate old vs. new code at all: under a single shared lock with
    only two contenders and no idle gaps to fill, the total amount of
    (artificially slowed) per-word work is conserved either way, so overall
    wall time for the pair is similar whether the lock is held per-sentence
    or per-word (confirmed empirically against both versions of the engine
    before this test was written this way). The property that TRUE finding
    should establish -- and does -- is that a second source's sentence can
    start making its own real per-word progress soon after it's called,
    instead of being stuck waiting for the first source's ENTIRE sentence
    to finish first. This logs every real read_word() call's timestamp (via
    the same instance-level wrapping used in the cross-contamination test
    below) and checks source b's FIRST word is processed well before source
    a's LAST word, rather than only after."""
    print("Concurrency test 2: a second source's sentence starts making "
          "real progress without waiting for the first source's ENTIRE "
          "sentence to finish first...")
    g = Guala()

    call_log = []
    log_lock = threading.Lock()
    orig_read_word = g.read_word

    def _logging_read_word(word, *a, **kw):
        result = orig_read_word(word, *a, **kw)
        with log_lock:
            call_log.append((time.monotonic(), kw.get("source")))
        return result

    g.read_word = _logging_read_word

    words_a = [f"alphaword{i}" for i in range(14)]
    words_b = [f"bravoword{i}" for i in range(14)]
    errors = []

    def _run(words, source, delay_before=0.0):
        try:
            if delay_before:
                time.sleep(delay_before)
            g.read_sentence(" ".join(words), source=source)
        except Exception as e:
            errors.append((source, e))

    with _SlowSectionReceive(0.03):
        t_start = time.monotonic()
        th_a = threading.Thread(target=_run, args=(words_a, "joe"))
        th_b = threading.Thread(target=_run, args=(words_b, "wc", 0.02))
        th_a.start()
        th_b.start()
        th_a.join(timeout=30)
        th_b.join(timeout=30)

    assert not errors, f"read_sentence raised in a background thread: {errors}"
    assert len(call_log) == len(words_a) + len(words_b)

    a_times = [t - t_start for t, s in call_log if s == "joe"]
    b_times = [t - t_start for t, s in call_log if s == "wc"]
    assert a_times and b_times
    a_last = max(a_times)
    b_first = min(b_times)
    print(f"  a's last word processed at t={a_last:.3f}s, b's first word "
          f"processed at t={b_first:.3f}s (b called read_sentence at "
          "~t=0.02s)")
    # Under the old bug, b cannot do ANY of its own per-word work (b's
    # read_sentence() blocks on self.lock at its very first line) until a's
    # entire sentence -- all 14 words -- has finished, so b_first would be
    # >= a_last. Under the fix, b's first word should land well before a's
    # last, proving b did not have to wait out the whole sentence.
    assert b_first < a_last * 0.9, (
        f"REGRESSION: b's first word (t={b_first:.3f}s) did not start "
        f"meaningfully before a's last word (t={a_last:.3f}s) -- b "
        "appears to have waited for a's entire sentence instead of "
        "interleaving with it")
    print("  OK: b's sentence started making real progress well before "
          "a's sentence finished")


def test_concurrent_sentences_do_not_cross_contaminate_episode_or_phase_vec():
    """The actual correctness hazard (not just performance): with the lock
    narrowed to per-word, two sentences' read_word() calls can now
    genuinely interleave in wall-clock time. Confirms neither sentence's
    episode_ref nor its phase-vector rotation chain leaks into the other's,
    by logging every real read_word() call (word, source, the episode_ref/
    prev_phase_vec it was given, and the phase_vec it returned) from both
    threads and replaying each source's own chain independently."""
    print("Concurrency test 3: real concurrent sentences do not cross-"
          "contaminate episode_ref or phase-vector rotation state...")
    g = Guala()

    call_log = []
    log_lock = threading.Lock()
    orig_read_word = g.read_word  # already bound

    def _logging_read_word(word, *a, **kw):
        result = orig_read_word(word, *a, **kw)
        with log_lock:
            call_log.append({
                "word": word,
                "source": kw.get("source"),
                "episode_ref": kw.get("episode_ref"),
                "prev_in": kw.get("prev_phase_vec"),
                "phase_out": result[3],
            })
        return result

    g.read_word = _logging_read_word

    # Distinct vocabularies so each sentence's own words are unambiguous.
    words_a = ["mercury", "venus", "earth", "mars", "jupiter", "saturn"]
    words_b = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    errors = []

    def _run(words, source, delay_before=0.0):
        try:
            if delay_before:
                time.sleep(delay_before)
            g.read_sentence(" ".join(words), source=source)
        except Exception as e:
            errors.append((source, e))

    with _SlowSectionReceive(0.02):
        th_a = threading.Thread(target=_run, args=(words_a, "joe"))
        th_b = threading.Thread(target=_run, args=(words_b, "wc", 0.01))
        th_a.start()
        th_b.start()
        th_a.join(timeout=30)
        th_b.join(timeout=30)

    assert not errors, f"read_sentence raised in a background thread: {errors}"
    assert len(call_log) == len(words_a) + len(words_b), (
        f"expected {len(words_a) + len(words_b)} logged read_word calls, "
        f"got {len(call_log)}")

    # Sanity: prove real interleaving actually happened -- otherwise this
    # test would be vacuously passing because the threads happened to run
    # back-to-back rather than genuinely overlapping.
    sources_in_order = [c["source"] for c in call_log]
    first_b_idx = next(i for i, s in enumerate(sources_in_order) if s == "wc")
    last_a_idx = max(i for i, s in enumerate(sources_in_order) if s == "joe")
    assert first_b_idx < last_a_idx, (
        "no interleaving observed between the two sources' calls "
        f"({sources_in_order}) -- test is inconclusive, not a pass")

    for source, words in (("joe", words_a), ("wc", words_b)):
        entries = [c for c in call_log if c["source"] == source]
        assert [e["word"] for e in entries] == words, (
            f"{source}'s own call order got scrambled: "
            f"{[e['word'] for e in entries]} != {words}")

        # Episode tag: every word of THIS source's sentence must share one
        # real episode_ref, and it must never equal a value seen for the
        # other source (that would mean the shared self._current_episode
        # attribute leaked across the two concurrent sentences).
        ep_refs = {e["episode_ref"] for e in entries}
        assert len(ep_refs) == 1 and next(iter(ep_refs)) is not None, (
            f"{source}: episode_ref not consistent across its own "
            f"sentence: {ep_refs}")

        # Phase-vector chain continuity: word i's incoming prev_phase_vec
        # must be EXACTLY the object this same source's own word (i-1)
        # returned (skip-on-None semantics preserved) -- never something
        # that came from the other thread's interleaved calls.
        assert entries[0]["prev_in"] is None, (
            f"{source}: first word did not start with prev_phase_vec=None "
            f"(got {entries[0]['prev_in']!r}) -- possible cross-"
            "contamination from the other concurrent sentence")
        last_good = None
        for i, e in enumerate(entries):
            expected_prev = last_good
            actual_prev = e["prev_in"]
            assert (actual_prev is expected_prev) or (
                actual_prev is None and expected_prev is None
            ), (
                f"{source} word[{i}]={e['word']!r}: prev_phase_vec was "
                f"{'<some array>' if actual_prev is not None else None}, "
                f"expected {'<same array as previous phase_out>' if expected_prev is not None else None} "
                "-- the call-local phase-vector chain diverged, likely "
                "cross-contaminated by the other concurrent sentence")
            if e["phase_out"] is not None:
                last_good = e["phase_out"]

    ep_joe = {c["episode_ref"] for c in call_log if c["source"] == "joe"}
    ep_wc = {c["episode_ref"] for c in call_log if c["source"] == "wc"}
    assert ep_joe.isdisjoint(ep_wc), (
        f"joe's episode_ref(s) {ep_joe} overlap wc's {ep_wc} -- cross-"
        "contamination between concurrent sentences")

    print(f"  OK: {len(call_log)} real interleaved read_word() calls across "
          "2 concurrent sentences -- zero episode_ref or phase-vector "
          "cross-contamination")


if __name__ == "__main__":
    tests = [
        test_lock_releases_between_words_not_held_for_whole_sentence,
        test_concurrent_sentence_from_second_source_starts_well_before_first_finishes,
        test_concurrent_sentences_do_not_cross_contaminate_episode_or_phase_vec,
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
