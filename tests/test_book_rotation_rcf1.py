"""
test_book_rotation_rcf1.py — GL-SPC-DRIVE-PHYSICS-SUBSTRATE-TRUE-20260718-v1
RCF-1: book-rotation fix (Step 1 of the drive-physics sequencing).

Gates:
1. Repeat penalty: with identical organism freshness, a heavily-read
   corpus scores strictly lower READING salience than an unread one.
2. LRU tie-break: an epsilon-tie between two READING candidates is won
   by the least-recently-read corpus.
3. Rotation: once the winner's last_read_tick advances, the next
   selection flips to the other corpus (no more same-pick-forever).
4. Real preference respected: a salience gap wider than the epsilon is
   never overridden by recency.
5. Targetless kinds never win a tie-break against a real target; an
   all-targetless tie keeps the existing deterministic order.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import (
    Guala, SALIENCE_TIE_EPSILON,
)


def _engine_with_two_books():
    g = Guala()
    g.add_corpus("book_a", "Book A",
                 ["the cat sat on the mat", "the dog ran far away"])
    g.add_corpus("book_b", "Book B",
                 ["one bird flew over trees", "the moon rose at night"])
    return g


def test_gate1_repeat_penalty_lowers_reading_salience():
    print("Gate 1: repeat penalty...")
    g = _engine_with_two_books()
    # Identical organism freshness for both corpora isolates the blend.
    g._reading_freshness_from_organism = lambda c: 0.9
    g.tick = 500_000
    a, b = g._corpora["book_a"], g._corpora["book_b"]
    a.times_read_through, a.last_read_tick = 2347, g.tick - 10
    b.times_read_through, b.last_read_tick = 0, 0

    sal_a = g._action_salience("READING", "book_a")
    sal_b = g._action_salience("READING", "book_b")
    assert sal_a < sal_b, \
        f"2347-read corpus must score below unread one: {sal_a} >= {sal_b}"
    print(f"  PASS: repeated={sal_a:.4f} < unread={sal_b:.4f}")


def test_gate2_lru_tie_break_prefers_least_recent():
    print("Gate 2: LRU tie-break...")
    g = _engine_with_two_books()
    g.tick = 100_000
    g._corpora["book_a"].last_read_tick = 90_000   # recent
    g._corpora["book_b"].last_read_tick = 10_000   # long ago
    g._candidate_activities = lambda: [("READING", "book_a"),
                                       ("READING", "book_b")]
    g._action_salience = lambda k, t: 0.5          # exact tie

    act = g._select_next_activity()
    assert (act.kind, act.target) == ("READING", "book_b"), \
        f"Least-recently-read must win the tie, got {act.target}"
    print("  PASS: least-recently-read corpus won the tie")


def test_gate3_rotation_across_selections():
    print("Gate 3: rotation...")
    g = _engine_with_two_books()
    g.tick = 100_000
    g._corpora["book_a"].last_read_tick = 90_000
    g._corpora["book_b"].last_read_tick = 10_000
    g._candidate_activities = lambda: [("READING", "book_a"),
                                       ("READING", "book_b")]
    g._action_salience = lambda k, t: 0.5

    first = g._select_next_activity().target
    g._corpora[first].last_read_tick = g.tick       # as a real read would
    g.tick += 1000
    second = g._select_next_activity().target
    assert first != second, \
        f"Selection must rotate, picked {first} twice"
    print(f"  PASS: rotated {first} -> {second}")


def test_gate4_real_preference_not_overridden():
    print("Gate 4: real preference respected...")
    g = _engine_with_two_books()
    g.tick = 100_000
    g._corpora["book_a"].last_read_tick = 99_000   # much more recent
    g._corpora["book_b"].last_read_tick = 0
    gap = SALIENCE_TIE_EPSILON * 4
    g._candidate_activities = lambda: [("READING", "book_a"),
                                       ("READING", "book_b")]
    g._action_salience = \
        lambda k, t: 0.6 if t == "book_a" else 0.6 - gap

    act = g._select_next_activity()
    assert act.target == "book_a", \
        f"A real salience gap must stand, got {act.target}"
    print("  PASS: scored preference not overridden by recency")


def test_gate5_targetless_kinds_never_win_tie():
    print("Gate 5: targetless exclusion...")
    g = _engine_with_two_books()
    g.tick = 100_000
    g._corpora["book_a"].last_read_tick = 99_999
    g._candidate_activities = lambda: [("IDLE", None),
                                       ("SLEEPING", None),
                                       ("READING", "book_a")]
    g._action_salience = lambda k, t: 0.5          # three-way tie

    act = g._select_next_activity()
    assert act.kind == "READING", \
        f"Real target must beat targetless kinds on a tie, got {act.kind}"

    # All-targetless tie: existing deterministic order stands, no crash.
    g._candidate_activities = lambda: [("IDLE", None), ("SLEEPING", None)]
    act = g._select_next_activity()
    assert act.kind in ("IDLE", "SLEEPING")
    print("  PASS: targetless kinds excluded from LRU, all-targetless intact")


if __name__ == "__main__":
    test_gate1_repeat_penalty_lowers_reading_salience()
    test_gate2_lru_tie_break_prefers_least_recent()
    test_gate3_rotation_across_selections()
    test_gate4_real_preference_not_overridden()
    test_gate5_targetless_kinds_never_win_tie()
    print("\nAll RCF-1 gates pass.")
