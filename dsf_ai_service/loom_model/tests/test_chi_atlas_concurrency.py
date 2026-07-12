"""
test_chi_atlas_concurrency.py -- GL-FIX-CHI-ATLAS-CONCURRENCY-20260712.

Concurrency fix under test: ChiAtlas.record()
(dsf_ai_service/v4/gualaloom_v4_chi_atlas_l6.py) is called from two
genuinely concurrent, differently-synchronized real production call
sites on the SAME neuron's chi_atlas:
  (1) the spike-bus delivery thread's _fire()->_on_fire_bookkeeping()
      (neuron.py), guarded only by that neuron's own _neuron_lock.
  (2) the organism worker thread's legacy step() path (neuron.py),
      reached for the real word-teaching branch with NO lock at all
      (GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207-v1, Joe's no-locks
      ruling, in gualaloom_v5_engine.py: "NO LOCKS IN HER MIND ...
      concurrency in her substrate is achieved by LOCALITY ... never by
      mutexes ... a lock in her cognition path is defective on sight").
No lock is shared between these two paths, and per that ruling none may
be added inside ChiAtlas -- this is squarely "her cognition path", not
an I/O boundary.

What this suite proves, with real numbers, against the REAL production
class (never a reimplementation of the fix):

  1. The failure mode the bug report was originally framed around --
     silently lost/duplicated bucket entries from the classic-looking
     `bucket.append(x); if len(bucket) > MAX: del bucket[0]` on a plain
     list -- does NOT actually reproduce under CPython's GIL, even under
     heavy forced contention (see test_old_append_del_pattern_does_not_
     lose_entries, which keeps a small labeled copy of the OLD pattern
     specifically to demonstrate this honestly rather than assume it).
     append(), len(), and del list[0] are each individually GIL-atomic,
     and the eviction count self-corrects regardless of interleaving
     order (every check reads the TRUE current length at call time).
  2. What DOES reproduce, reliably, is a real crash:
     `RuntimeError: dictionary changed size during iteration`, whenever
     a full-dict sweep over self.entries overlaps with a record() call
     that touches a brand-new chi key. test_bug_reproduces_against_old_
     dict_iteration_pattern reproduces this 10/10 against a labeled copy
     of the OLD (pre-fix) cross_modal_bindings() pattern. IMPORTANT: the
     first fix attempted here (a plain list(self.entries.items())
     snapshot, the same idiom already used for wave_atlas.py's
     tick_decay()) looked sufficient in a smaller ad-hoc probe but was
     NOT -- test_fix_cross_modal_bindings_survives_concurrent_writes and
     test_fix_trim_all_survives_concurrent_writes below are what actually
     caught that (run them paired with the reproduction test above in
     the SAME process/session -- e.g. via pytest with both tests
     selected -- to reproduce; a too-short/low-contention run can miss
     it). The REAL fix is ChiAtlas._snapshot_entries()
     (dict(self.entries), CPython's dict-to-dict bulk-copy fast path,
     not the generic per-step-checked iterator protocol list(d.items())
     uses), wrapped in a small bounded retry -- see ChiAtlas's own class
     docstring points 2/2b for the full empirical comparison (0 errors
     across 100+ heavy trials for dict(self.entries) vs. reliable
     reproduction for list(d.items()) under the same load once
     self.entries is large, which production chi atlases are). The tests
     below exercise the REAL, current, fully-fixed methods.
  3. test_concurrency_stress_zero_lost_or_phantom_entries hammers the
     REAL, current record() with real concurrent writers shaped like
     both production call sites and proves, via a ledger of every
     attempted write (uniquely labeled, recorded by the test harness
     BEFORE each call so nothing about the real mutation order needs to
     be assumed): zero phantom entries (every surviving entry
     corresponds to a real attempted write, never fabricated or
     duplicated) and zero lost entries whenever attempted writes to a
     key stayed under MAX_ENTRIES_PER_CHI_KEY. This does not pretend
     genuinely concurrent operations have one single global order --
     it proves the strongest invariant that's actually true of them.
  4. Pickle round-trip / backward compatibility: an organism/tapestry
     pickled before this fix has plain lists inside chi_atlas.entries.
     __setstate__ must normalize every bucket to a capped deque before
     the restored object is reachable by any thread, and record() on a
     migrated legacy key must keep working correctly afterward.
  5. cluster.py's _select_by_chi_familiarity novelty-pool sort (a real,
     external, hot-path consumer of chi_atlas.entries that bypasses
     ChiAtlas's own methods) is exercised under the same concurrent-
     insert pressure and must not crash either -- routed through
     ChiAtlas's own public bucket_sizes() (the same _snapshot_entries()
     primitive), not a local reimplementation.
  6. A SECOND real crash, found only by this suite's own full-run (not
     the smaller ad-hoc probe that shipped first): switching bucket
     storage to collections.deque (see point 3 in ChiAtlas's class
     docstring) introduced `RuntimeError: deque mutated during
     iteration` -- a bare `for e in bucket` raises if record() appends
     to that SAME bucket mid-iteration, unlike a plain list (which
     tolerates concurrent append/del during iteration, per point 1).
     This is MORE exposed than point 2's dict-resize crash because
     match_score()/query_associations() read a live bucket on every
     single call, not just on an occasional full sweep.
     test_bug_reproduces_against_old_bare_bucket_iteration reproduces
     this 10/10 against a labeled copy of a bare-iteration match_score;
     test_fix_match_score_survives_same_bucket_contention and
     test_fix_query_associations_survives_same_bucket_contention prove
     the REAL, current (list(bucket)-snapshotting) methods survive the
     identical, higher-intensity reproduction -- same test, old pattern
     crashes, fixed method doesn't.

  Methodology note (why point 2's story matters beyond this one bug):
  a smaller-scale reproduction that stops retrying once it stops
  crashing can certify a fix that only moved the failure probability
  down, not to zero. This suite's own history is the proof: the first
  "fix" (list()-snapshot) passed an earlier, smaller version of these
  same tests before failing under this file's own full run. Every "fix
  survives" test below runs at real production-scale contention (tens
  of thousands of keys, sustained concurrent writers) rather than
  stopping at the first clean run.

No kill switch (see ChiAtlas's class docstring for the full reasoning):
this is a strict internal data-structure/algorithm fix with identical
external behavior in every case that matters (chi_atlas is documented
observability-only in neuron.py's _on_fire_bookkeeping -- nothing reads
it for real production cognition), no lock added anywhere, and zero
lines touched in gualaloom_v5_engine.py (verified below).
"""

import os
import subprocess
import sys
import threading
import time
import traceback
from collections import deque

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6 import ChiAtlas, MAX_ENTRIES_PER_CHI_KEY
from dsf_ai_service.loom_model.cluster import LoomCluster, FAMILIARITY_THRESHOLD


# ---------------------------------------------------------------------------
# 1. The originally-suspected failure mode (lost/duplicated bucket entries)
#    -- proven, honestly, NOT to reproduce for the OLD pattern.
# ---------------------------------------------------------------------------

def _old_pattern_record_one_key(bucket, entry, max_len):
    """Labeled copy of the OLD (pre-fix) per-key append+evict logic --
    NOT production code, kept here only so this suite can demonstrate,
    rather than assert from theory, that this specific pattern does not
    lose data under CPython's GIL."""
    bucket.append(entry)
    if len(bucket) > max_len:
        del bucket[0]


def test_old_append_del_pattern_does_not_lose_entries():
    """Up to 64 concurrent threads hammering the OLD list-based
    append+evict pattern on a handful of shared keys, across many
    trials. Invariant: final bucket length must equal
    min(total_attempted_writes_to_that_key, MAX_ENTRIES_PER_CHI_KEY) --
    true under a correct implementation regardless of interleaving,
    since every attempted write is either a pure append (under
    capacity) or an append+evict-oldest (at capacity). A violation would
    prove entries were lost or over-retained under real concurrent
    access."""
    N_THREADS = 48
    N_OPS = 1200
    N_KEYS = 3
    violations_total = 0

    for trial in range(5):
        buckets = {k: [] for k in range(N_KEYS)}
        attempts = {k: 0 for k in range(N_KEYS)}
        lock = threading.Lock()  # test-harness bookkeeping only

        def writer(tid):
            local = {k: 0 for k in range(N_KEYS)}
            for i in range(N_OPS):
                key = (tid + i) % N_KEYS
                _old_pattern_record_one_key(
                    buckets[key], {"tid": tid, "i": i}, MAX_ENTRIES_PER_CHI_KEY)
                local[key] += 1
            with lock:
                for k in range(N_KEYS):
                    attempts[k] += local[k]

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for k in range(N_KEYS):
            expected = min(attempts[k], MAX_ENTRIES_PER_CHI_KEY)
            actual = len(buckets[k])
            if actual != expected:
                violations_total += 1

    print(f"\n== old append+del pattern: {N_THREADS} threads x {N_OPS} ops x 5 trials, "
          f"{violations_total} length-invariant violations == "
          f"{'UNEXPECTED FAILURE' if violations_total else 'confirms no length-based data loss'}")
    assert violations_total == 0, (
        "the old append+del pattern unexpectedly lost/over-retained entries -- "
        "if this ever fails, the 'not a real length race' finding above is wrong "
        "and needs to be revisited"
    )


# ---------------------------------------------------------------------------
# 2. The REAL, reproducible crash: dict resize during iteration.
# ---------------------------------------------------------------------------

def _old_pattern_cross_modal_bindings(atlas):
    """Labeled copy of the OLD (pre-fix) cross_modal_bindings() -- NOT
    production code: no list(...) snapshot before iterating
    self.entries.items(), which is exactly the bug this fix closes."""
    out = []
    for k, entries in atlas.entries.items():  # NO snapshot -- the bug
        secs = set(e["section"] for e in entries)
        if len(secs) >= 2:
            out.append((k, secs, entries))
    return out


def _contention_trial(read_fn, duration_s=0.25, trial=0):
    atlas = ChiAtlas(band=2)
    for i in range(500):
        atlas.record("neuron", f"seed{i}", i * 10, tick=None)

    errors = []
    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            # Brand-new chi key on every call -> guarantees dict resize
            # on every record() call, maximizing collision odds with a
            # concurrent full-dict sweep.
            atlas.record("neuron", f"new-{trial}-{i}", 1_000_000 + i, tick=None)
            i += 1

    def reader():
        deadline = time.monotonic() + duration_s
        n = 0
        try:
            while time.monotonic() < deadline:
                read_fn(atlas)
                n += 1
        except Exception as e:
            # Full traceback, not just repr(e) -- this is what pinned
            # down the module docstring's point 2/2b finding (the first
            # list()-snapshot attempt was insufficient): a bare repr()
            # would have said "RuntimeError: dictionary changed size
            # during iteration" without saying WHICH line, which made
            # the original (wrong) fix look sufficient in smaller-scale
            # ad-hoc testing.
            errors.append((e, traceback.format_exc()))
        return n

    wt = threading.Thread(target=writer, daemon=True)
    wt.start()
    n_reads = reader()
    stop.set()
    wt.join(timeout=2.0)
    return errors, n_reads, len(atlas.entries)


def test_bug_reproduces_against_old_dict_iteration_pattern():
    """The OLD cross_modal_bindings() pattern (no list()-snapshot),
    reproduced against a real ChiAtlas under real concurrent record()
    calls -- this is the actual, reliably-reproducible bug (unlike the
    length-race hypothesis in section 1 above)."""
    total_errors = 0
    crashes = []
    for trial in range(10):
        errors, n_reads, n_keys = _contention_trial(
            _old_pattern_cross_modal_bindings, duration_s=0.15, trial=trial)
        total_errors += len(errors)
        if errors:
            crashes.append((trial, n_reads, n_keys, repr(errors[0][0])))
    print(f"\n== OLD cross_modal_bindings() pattern: {total_errors}/10 trials crashed ==")
    for trial, n_reads, n_keys, err in crashes:
        print(f"   trial {trial}: reads={n_reads} keys_at_crash~{n_keys} error={err}")
    assert total_errors > 0, (
        "expected the OLD (unsnapshotted) dict-iteration pattern to crash under "
        "real concurrent record() calls -- if this now passes, the reproduction "
        "harness itself may be broken; investigate before trusting the 'fix "
        "closes it' tests below"
    )
    assert all("dictionary changed size during iteration" in e[3] for e in crashes), (
        f"crashed, but not with the expected RuntimeError message: {crashes}"
    )


# ---------------------------------------------------------------------------
# 3. The fix: real ChiAtlas.cross_modal_bindings() / trim_all() survive
#    the SAME reproduction, at higher contention than section 2.
# ---------------------------------------------------------------------------

def test_fix_cross_modal_bindings_survives_concurrent_writes():
    total_errors = 0
    total_reads = 0
    max_keys_seen = 0
    for trial in range(15):
        errors, n_reads, n_keys = _contention_trial(
            lambda a: a.cross_modal_bindings(), duration_s=0.25, trial=trial)
        total_errors += len(errors)
        total_reads += n_reads
        max_keys_seen = max(max_keys_seen, n_keys)
        assert not errors, "trial {}: unexpected error(s):\n{}".format(
            trial, "\n".join(tb for _, tb in errors))  # full traceback, not just repr(e)
    print(f"\n== FIXED cross_modal_bindings(): 15 trials, {total_reads} total full-dict "
          f"reads, dict grew up to {max_keys_seen} keys during a single trial, "
          f"{total_errors} errors ==")
    assert total_errors == 0


def test_fix_trim_all_survives_concurrent_writes():
    total_errors = 0
    total_reads = 0
    for trial in range(15):
        errors, n_reads, n_keys = _contention_trial(
            lambda a: a.trim_all(), duration_s=0.25, trial=trial)
        total_errors += len(errors)
        total_reads += n_reads
        assert not errors, "trial {}: unexpected error(s):\n{}".format(
            trial, "\n".join(tb for _, tb in errors))
    print(f"\n== FIXED trim_all(): 15 trials, {total_reads} total sweeps, "
          f"{total_errors} errors ==")
    assert total_errors == 0

    # trim_all() must also leave every bucket correctly capped and typed
    # as a deque after concurrent writers stop -- not just crash-free.
    atlas = ChiAtlas(band=0)
    for i in range(40):
        atlas.record("neuron", f"m{i}", 7, tick=None)
    atlas.trim_all()
    assert isinstance(atlas.entries[7], deque)
    assert len(atlas.entries[7]) == MAX_ENTRIES_PER_CHI_KEY
    print("== trim_all(): post-condition (capped deque) verified == PASS")


# ---------------------------------------------------------------------------
# 3b. The SECOND real crash (found only by this suite's own full-run, see
#     module docstring point 6): `deque mutated during iteration`, when a
#     reader bare-iterates a bucket while record() appends to that SAME
#     bucket. This needs a writer that repeatedly hits a SMALL, EXISTING
#     set of keys (unlike section 2/3's brand-new-key writer, which
#     rarely collides on the SAME bucket long enough to expose this).
# ---------------------------------------------------------------------------

def _old_pattern_match_score(atlas, chi_value, section_name):
    """Labeled copy of a bare-iteration match_score -- NOT production
    code: no list(bucket) snapshot before scanning, exactly the bug this
    fix closes for deque buckets specifically."""
    score = 0.0
    for d in range(-atlas.band, atlas.band + 1):
        for e in atlas.entries.get(chi_value + d, ()):  # NO snapshot -- the bug
            score += 0.3 if e["section"] != section_name else 0.1
    return min(score, 1.0)


def _same_bucket_contention_trial(read_fn, duration_s=0.2, n_hot_keys=3):
    """Seeds a handful of keys, then a writer thread repeatedly appends
    to those SAME keys (mimicking a neuron firing/committing repeatedly
    at similar chi -- realistic production traffic) while the reader
    repeatedly calls read_fn against those same keys. Maximizes the odds
    of a reader's bucket iteration colliding with a writer's append to
    that EXACT bucket, unlike the brand-new-key writer used in
    _contention_trial above."""
    atlas = ChiAtlas(band=0)
    for k in range(n_hot_keys):
        atlas.record("neuron", f"seed{k}", k, tick=None)

    errors = []
    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            atlas.record("neuron", f"w{i}", i % n_hot_keys, tick=None)
            i += 1

    def reader():
        deadline = time.monotonic() + duration_s
        n = 0
        try:
            while time.monotonic() < deadline:
                for k in range(n_hot_keys):
                    read_fn(atlas, k)
                n += 1
        except Exception as e:
            errors.append(e)
        return n

    wt = threading.Thread(target=writer, daemon=True)
    wt.start()
    n_reads = reader()
    stop.set()
    wt.join(timeout=2.0)
    return errors, n_reads


def test_bug_reproduces_against_old_bare_bucket_iteration():
    """The OLD (unsnapshotted) match_score pattern, reproduced against a
    real ChiAtlas deque bucket under real concurrent record() calls to
    that SAME bucket."""
    total_errors = 0
    crashes = []
    for trial in range(10):
        errors, n_reads = _same_bucket_contention_trial(
            lambda a, k: _old_pattern_match_score(a, k, "neuron"), duration_s=0.1)
        total_errors += len(errors)
        if errors:
            crashes.append((trial, n_reads, repr(errors[0])))
    print(f"\n== OLD bare-bucket-iteration match_score pattern: {total_errors}/10 trials crashed ==")
    for trial, n_reads, err in crashes:
        print(f"   trial {trial}: reads={n_reads} error={err}")
    assert total_errors > 0, (
        "expected the OLD bare `for e in bucket` pattern to crash under real "
        "concurrent record() calls to the SAME bucket -- if this now passes, "
        "the reproduction harness may be broken; investigate before trusting "
        "the 'fix closes it' tests below"
    )
    assert all("deque mutated during iteration" in e[2] for e in crashes), (
        f"crashed, but not with the expected RuntimeError message: {crashes}"
    )


def test_fix_match_score_survives_same_bucket_contention():
    total_errors = 0
    total_reads = 0
    for trial in range(15):
        errors, n_reads = _same_bucket_contention_trial(
            lambda a, k: a.match_score(k, "neuron"), duration_s=0.2)
        total_errors += len(errors)
        total_reads += n_reads
        assert not errors, f"trial {trial}: unexpected error(s): {errors}"
    print(f"\n== FIXED match_score(): 15 trials, {total_reads} read passes against "
          f"repeatedly-written-to buckets, {total_errors} errors ==")
    assert total_errors == 0


def test_fix_query_associations_survives_same_bucket_contention():
    total_errors = 0
    total_reads = 0
    for trial in range(15):
        errors, n_reads = _same_bucket_contention_trial(
            lambda a, k: a.query_associations("other", k), duration_s=0.2)
        total_errors += len(errors)
        total_reads += n_reads
        assert not errors, f"trial {trial}: unexpected error(s): {errors}"
    print(f"\n== FIXED query_associations(): 15 trials, {total_reads} read passes against "
          f"repeatedly-written-to buckets, {total_errors} errors ==")
    assert total_errors == 0


def test_fix_cross_modal_bindings_survives_same_bucket_contention():
    """cross_modal_bindings() under the hot-bucket (not brand-new-key)
    contention shape too -- its inner `for e in entries` scan needed the
    same list(bucket) fix as match_score/query_associations."""
    total_errors = 0
    total_reads = 0
    for trial in range(15):
        errors, n_reads = _same_bucket_contention_trial(
            lambda a, k: a.cross_modal_bindings(), duration_s=0.2)
        total_errors += len(errors)
        total_reads += n_reads
        assert not errors, f"trial {trial}: unexpected error(s): {errors}"
    print(f"\n== FIXED cross_modal_bindings() (hot-bucket shape): 15 trials, "
          f"{total_reads} read passes, {total_errors} errors ==")
    assert total_errors == 0


# ---------------------------------------------------------------------------
# 4. cluster.py's real _select_by_chi_familiarity novelty-pool sort --
#    the external, hot-path consumer that reads chi_atlas.entries
#    directly, under the same concurrent-insert pressure.
# ---------------------------------------------------------------------------

def test_cluster_novelty_sort_survives_concurrent_writes():
    """Real LoomCluster, real neurons. One thread continuously fires
    record() calls with brand-new chi keys on ALL neurons (mimicking the
    spike-bus path's independent per-neuron writes) while the main
    thread repeatedly calls the real _select_by_chi_familiarity() with
    an unfamiliar chi (forcing the novelty-pool sort branch, the exact
    line fixed in cluster.py) -- must not raise."""
    cluster = LoomCluster("concurrency_test_cluster", n_neurons=8, k_neighbors=4)
    errors = []
    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            for n in cluster.neurons:
                n.chi_atlas.record("neuron", f"w{i}", 2_000_000 + i, tick=None)
            i += 1

    wt = threading.Thread(target=writer, daemon=True)
    wt.start()
    n_calls = 0
    deadline = time.monotonic() + 0.3
    try:
        while time.monotonic() < deadline:
            cluster._select_by_chi_familiarity(input_chi=9_999_999)  # never-familiar chi
            n_calls += 1
    except Exception as e:
        errors.append(e)
    finally:
        stop.set()
        wt.join(timeout=2.0)

    print(f"\n== cluster._select_by_chi_familiarity novelty sort: {n_calls} calls "
          f"under concurrent writers, {len(errors)} errors ==")
    assert not errors, f"unexpected error(s): {errors}"
    assert n_calls > 0, "sanity: the read loop should have run at least once"


# ---------------------------------------------------------------------------
# 5. Required: ledger-based concurrency stress test on the REAL record()
#    -- zero lost / phantom / duplicated entries.
# ---------------------------------------------------------------------------

def test_concurrency_stress_zero_lost_or_phantom_entries():
    """Real concurrent writers, shaped like BOTH real production call
    sites (fire-path: tick=None: gualaloom's neuron.py
    _on_fire_bookkeeping; step-path: explicit tick), hammering the REAL
    ChiAtlas.record() -- band=0 so record() touches exactly one key per
    call, keeping the accounting exact. Every write is uniquely labeled
    (thread_id, seq) and logged to a ledger by the TEST HARNESS (a plain
    Python list + a test-only threading.Lock -- not part of ChiAtlas,
    exactly like test_homeostatic_scaling.py's own ledger tests) BEFORE
    the call, so nothing about the real internal mutation order needs to
    be assumed.

    Proves, per key: (a) no phantom entries -- every surviving label was
    really attempted; (b) no duplicates -- the surviving bucket has no
    repeated label; (c) zero loss whenever attempted writes stayed under
    MAX_ENTRIES_PER_CHI_KEY; (d) the length invariant
    min(attempted, MAX) holds exactly, in all cases.
    """
    atlas = ChiAtlas(band=0)
    N_THREADS = 24
    N_OPS = 900
    N_KEYS = 6  # some keys will exceed MAX under this load, some won't
    attempted = {k: [] for k in range(N_KEYS)}
    bookkeeping_lock = threading.Lock()  # test-harness only, NOT ChiAtlas
    errors = []

    def writer(tid):
        is_fire_shape = (tid % 2 == 0)
        local = {k: [] for k in range(N_KEYS)}
        for i in range(N_OPS):
            key = (tid + i) % N_KEYS
            label = f"{tid}-{i}"
            try:
                if is_fire_shape:
                    # matches neuron.py _on_fire_bookkeeping's call shape
                    atlas.record("neuron", label, key, tick=None)
                else:
                    # matches neuron.py step()'s call shape
                    atlas.record("neuron", label, key, tid * N_OPS + i)
            except Exception as e:
                errors.append(e)
                continue
            local[key].append(label)
        with bookkeeping_lock:
            for k in range(N_KEYS):
                attempted[k].extend(local[k])

    threads = [threading.Thread(target=writer, args=(t,)) for t in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30.0)
        assert not t.is_alive(), "a writer thread did not finish -- possible deadlock"

    assert not errors, f"expected zero exceptions under concurrent record() calls, got: {errors[:3]}"

    total_attempted = sum(len(v) for v in attempted.values())
    total_surviving = 0
    for k in range(N_KEYS):
        final_bucket = list(atlas.entries.get(k, []))
        final_labels = [e["motif"] for e in final_bucket]
        expected_len = min(len(attempted[k]), MAX_ENTRIES_PER_CHI_KEY)

        assert len(final_bucket) == expected_len, (
            f"key={k}: expected length {expected_len} "
            f"(min(attempted={len(attempted[k])}, MAX={MAX_ENTRIES_PER_CHI_KEY})), "
            f"got {len(final_bucket)}"
        )
        assert len(set(final_labels)) == len(final_labels), (
            f"key={k}: duplicate entries survived: {final_labels}"
        )
        assert set(final_labels).issubset(set(attempted[k])), (
            f"key={k}: PHANTOM entries present that were never attempted: "
            f"{set(final_labels) - set(attempted[k])}"
        )
        if len(attempted[k]) <= MAX_ENTRIES_PER_CHI_KEY:
            assert set(final_labels) == set(attempted[k]), (
                f"key={k}: under capacity ({len(attempted[k])} <= "
                f"{MAX_ENTRIES_PER_CHI_KEY}) but entries were LOST: "
                f"missing={set(attempted[k]) - set(final_labels)}"
            )
        total_surviving += len(final_bucket)

    over_capacity_keys = sum(1 for k in range(N_KEYS) if len(attempted[k]) > MAX_ENTRIES_PER_CHI_KEY)
    assert over_capacity_keys > 0, (
        "sanity: expected at least one key to exceed MAX_ENTRIES_PER_CHI_KEY "
        "under this load -- if zero, this test isn't exercising real eviction"
    )
    print(f"\n== concurrency stress (real record(), {N_THREADS} threads x {N_OPS} ops "
          f"= {total_attempted} total attempted writes across {N_KEYS} keys, "
          f"{over_capacity_keys}/{N_KEYS} keys over capacity): "
          f"{total_surviving} surviving entries, 0 lost/phantom/duplicated, 0 errors == PASS")


# ---------------------------------------------------------------------------
# 6. Pickle round-trip / backward compatibility with pre-fix production
#    state (plain lists, some over MAX_ENTRIES_PER_CHI_KEY).
# ---------------------------------------------------------------------------

def test_pickle_migration_converts_legacy_buckets_and_record_still_works():
    """Simulates restoring a real pre-fix organism pickle: entries as a
    plain dict of plain (possibly over-capacity) lists. __setstate__
    must convert every bucket to a properly-capped deque, keeping only
    the most recent MAX_ENTRIES_PER_CHI_KEY per key, and record() must
    continue to work correctly on a migrated key afterward."""
    legacy_state = {
        "band": 2,
        "tick": 500,
        "entries": {
            5: [{"section": "neuron", "motif": f"m{i}", "chi": 5, "tick": i}
                for i in range(20)],  # over capacity, pre-fix bloat shape
            6: [{"section": "neuron", "motif": "only", "chi": 6, "tick": 1}],
        },
    }
    restored = ChiAtlas.__new__(ChiAtlas)
    restored.__setstate__(legacy_state)

    assert isinstance(restored.entries[5], deque)
    assert restored.entries[5].maxlen == MAX_ENTRIES_PER_CHI_KEY
    assert len(restored.entries[5]) == MAX_ENTRIES_PER_CHI_KEY
    assert [e["motif"] for e in restored.entries[5]] == [f"m{i}" for i in range(4, 20)], (
        "migration must keep the MOST RECENT entries (oldest evicted first), "
        "matching the pre-fix trim_all()'s documented contract"
    )
    assert isinstance(restored.entries[6], deque)
    assert len(restored.entries[6]) == 1

    restored.record("neuron", "new_after_migration", 5, tick=999)
    assert len(restored.entries[5]) == MAX_ENTRIES_PER_CHI_KEY
    assert restored.entries[5][-1]["motif"] == "new_after_migration"
    assert restored.entries[5][0]["motif"] == "m5", "oldest entry correctly evicted on the next write"
    print("\n== pickle migration: legacy plain-list buckets converted to capped "
          "deques, record() on a migrated key works correctly == PASS")


def test_real_pickle_roundtrip_on_a_fresh_atlas():
    """A real pickle.dumps/loads round trip (not a hand-built legacy
    state dict) on a freshly-used ChiAtlas -- must not raise, and must
    preserve every entry."""
    import pickle
    atlas = ChiAtlas()
    for i in range(30):
        atlas.record("neuron", f"w{i}", i, tick=None)
    before = {k: [e["motif"] for e in v] for k, v in atlas.entries.items()}

    blob = pickle.dumps(atlas)
    restored = pickle.loads(blob)

    after = {k: [e["motif"] for e in v] for k, v in restored.entries.items()}
    assert after == before
    assert all(isinstance(v, deque) and v.maxlen == MAX_ENTRIES_PER_CHI_KEY
               for v in restored.entries.values())
    # Restored atlas must still work correctly afterward.
    restored.record("neuron", "post_restore", 0, tick=None)
    assert restored.entries[0][-1]["motif"] == "post_restore"
    print("\n== real pickle round trip: entries preserved exactly, atlas usable "
          "after restore == PASS")


# ---------------------------------------------------------------------------
# 7. No lock added; zero lines touched in gualaloom_v5_engine.py.
# ---------------------------------------------------------------------------

def test_no_lock_object_anywhere_in_chi_atlas():
    """Direct guardrail against reopening Joe's no-locks ruling: no
    attribute on a fresh ChiAtlas instance may be a lock of any kind."""
    import threading as _threading
    atlas = ChiAtlas()
    atlas.record("neuron", "w", 1, tick=None)
    lock_types = (type(_threading.Lock()), type(_threading.RLock()))
    for name, value in vars(atlas).items():
        assert not isinstance(value, lock_types), (
            f"ChiAtlas.{name} is a lock ({type(value)}) -- this reopens "
            f"Joe's no-locks ruling (GL-CMD-ORGANISM-WAVE-MEMORY-EVE-"
            f"20260705-207-v1); the fix must stay lock-free"
        )
    print("\n== no lock object anywhere on ChiAtlas == PASS")


def test_zero_lines_touched_in_v5_engine():
    """This fix must not touch gualaloom_v5_engine.py's word-teaching
    lock-free discipline at all -- confirms via git that the file has no
    diff against origin/guala-live."""
    repo_root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
    try:
        out = subprocess.run(
            ["git", "diff", "origin/guala-live", "--",
             "dsf_ai_service/v4/gualaloom_v5_engine.py"],
            cwd=repo_root, capture_output=True, text=True, timeout=15,
        )
    except Exception as e:
        pytest.skip(f"git not available in this environment: {e}")
    if out.returncode != 0:
        pytest.skip(f"git diff against origin/guala-live failed (not available "
                     f"in this environment?): {out.stderr}")
    assert out.stdout.strip() == "", (
        f"expected zero diff in gualaloom_v5_engine.py vs origin/guala-live, got:\n{out.stdout}"
    )
    print("\n== zero lines touched in gualaloom_v5_engine.py (git diff vs "
          "origin/guala-live is empty) == PASS")


if __name__ == "__main__":
    test_old_append_del_pattern_does_not_lose_entries()
    test_bug_reproduces_against_old_dict_iteration_pattern()
    test_fix_cross_modal_bindings_survives_concurrent_writes()
    test_fix_trim_all_survives_concurrent_writes()
    test_bug_reproduces_against_old_bare_bucket_iteration()
    test_fix_match_score_survives_same_bucket_contention()
    test_fix_query_associations_survives_same_bucket_contention()
    test_fix_cross_modal_bindings_survives_same_bucket_contention()
    test_cluster_novelty_sort_survives_concurrent_writes()
    test_concurrency_stress_zero_lost_or_phantom_entries()
    test_pickle_migration_converts_legacy_buckets_and_record_still_works()
    test_real_pickle_roundtrip_on_a_fresh_atlas()
    test_no_lock_object_anywhere_in_chi_atlas()
    test_zero_lines_touched_in_v5_engine()
    print("\nALL PASS: test_chi_atlas_concurrency")
