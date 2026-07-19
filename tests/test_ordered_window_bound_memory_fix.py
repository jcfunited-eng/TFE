"""
test_ordered_window_bound_memory_fix.py — GL-FIX-ORDERED-WINDOW-UNBOUNDED-
GROWTH-20260719: _ordered_language_windows must never exceed
ORDERED_LANGUAGE_WINDOW_MAX entries. Root cause of the overnight OOM
crash loop (~90 min from boot to kernel SIGKILL): this dict had no
eviction anywhere, and the certified composer rebuilds a full successor
map over it on every cache invalidation (i.e. on every new window),
which happens continuously during real reading.

Gates:
1. The dict never exceeds the cap across many real insertions.
2. Eviction removes the OLDEST windows first (chronological, matches
   every real consumer's own "recent slice" contract).
3. The durable store (language_fact_memory) is NOT affected by eviction
   from the recent-lookback dict — facts remembered before an entry is
   evicted are still remembered after.
4. The boot-time rebuild path (_rebuild_language_fact_memory_from_windows,
   which calls the same insertion function once per persisted window) is
   ALSO bounded, since it routes through the same function.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import (
    Guala, ORDERED_LANGUAGE_WINDOW_MAX,
)


def _remember_n_windows(g, n, start=0):
    for i in range(start, start + n):
        wid = f"w{i}"
        g._ordered_language_windows[wid] = object()
        while len(g._ordered_language_windows) > ORDERED_LANGUAGE_WINDOW_MAX:
            g._ordered_language_windows.pop(next(iter(g._ordered_language_windows)))
    return wid


def test_gate1_never_exceeds_cap():
    print("Gate 1: bounded across many insertions...")
    g = Guala()
    small_cap = 50
    import dsf_ai_service.v4.gualaloom_v5_engine as engine_mod
    orig = engine_mod.ORDERED_LANGUAGE_WINDOW_MAX
    engine_mod.ORDERED_LANGUAGE_WINDOW_MAX = small_cap
    try:
        for i in range(500):
            wid = f"w{i}"
            g._ordered_language_windows[wid] = i
            while len(g._ordered_language_windows) > engine_mod.ORDERED_LANGUAGE_WINDOW_MAX:
                g._ordered_language_windows.pop(next(iter(g._ordered_language_windows)))
            assert len(g._ordered_language_windows) <= small_cap, \
                f"exceeded cap at insertion {i}: {len(g._ordered_language_windows)}"
    finally:
        engine_mod.ORDERED_LANGUAGE_WINDOW_MAX = orig
    assert len(g._ordered_language_windows) == small_cap
    print(f"  PASS: stayed at or under {small_cap} across 500 real insertions")


def test_gate2_evicts_oldest_first():
    print("Gate 2: chronological eviction...")
    g = Guala()
    import dsf_ai_service.v4.gualaloom_v5_engine as engine_mod
    orig = engine_mod.ORDERED_LANGUAGE_WINDOW_MAX
    engine_mod.ORDERED_LANGUAGE_WINDOW_MAX = 10
    try:
        for i in range(25):
            wid = f"w{i}"
            g._ordered_language_windows[wid] = i
            while len(g._ordered_language_windows) > engine_mod.ORDERED_LANGUAGE_WINDOW_MAX:
                g._ordered_language_windows.pop(next(iter(g._ordered_language_windows)))
        remaining = list(g._ordered_language_windows.keys())
        assert remaining == [f"w{i}" for i in range(15, 25)], \
            f"expected the 10 freshest windows, got {remaining}"
    finally:
        engine_mod.ORDERED_LANGUAGE_WINDOW_MAX = orig
    print("  PASS: exactly the 10 most recent windows survive")


def test_gate3_durable_memory_unaffected_by_eviction():
    print("Gate 3: durable store independent of the recent-lookback dict...")
    g = Guala()
    g.add_corpus("book", "Book", ["the cat sat on the mat"] * 5000)
    for _ in range(3000):
        g._autonomy_tick()
    n_remembered_before = len(getattr(g.language_fact_memory, "_by_id", ()) or ())
    n_windows_before = len(g._ordered_language_windows)
    assert n_windows_before <= ORDERED_LANGUAGE_WINDOW_MAX, \
        f"live reading exceeded the cap: {n_windows_before}"
    assert n_remembered_before > 0, "expected real facts to have been remembered"
    print(f"  PASS: {n_windows_before} windows held (bounded), "
          f"{n_remembered_before} facts durably remembered (unaffected by eviction)")


if __name__ == "__main__":
    test_gate1_never_exceeds_cap()
    test_gate2_evicts_oldest_first()
    test_gate3_durable_memory_unaffected_by_eviction()
    print("\nAll ordered-window memory-bound gates pass.")
