"""
test_word_order_relation.py — local functional tests for
GL-CMD-WORD-ORDER-RELATION-C1-20260711

Tests against the REAL Guala engine (dsf_ai_service/v4/gualaloom_v5_engine.py),
not mocks. Context: the substrate has no mechanism for real "order/sequence"
between words/events (position_hint only routes first/middle/last ROUTING
WORDS by sentence position; real text recall runs through a single
population vote keyed on the last content word only; the one existing
novelty counter is explicitly order-blind, "sorted so order-invariant").
This dispatch adds one pure-reader method, _word_order_relation(word_a,
word_b), that answers "did she encounter A before or after B" by comparing
each word's most recent real commit tick (Section.commits, persisted
across restarts) plus episodic-memory tick (self._episodic_memory) --
never a guess, honest "unknown" when no real record exists -- and wires
it into _form_reflection() so the new capability is genuinely used, not
dead code.

Covers:
1.  Real committed words, known tick ordering: word committed first ->
    "before" when compared to a word committed later, and "after" the
    other way around.
2.  Same real engine tick (two sections committed within the same
    read_word() call share one engine tick) -> "same", a genuine
    simultaneity, not a tie-break artifact.
3.  Unknown: a word never committed anywhere (no section commit, no
    episodic record) -> "unknown", both directions.
4.  Unknown: empty/None word arguments -> "unknown", no exception.
5.  Case-insensitivity: matches the same convention as _word_to_mode_idx/
    _word_to_chi_index (word.lower()).
6.  A word committed in more than one section uses the MOST RECENT tick
    across all of them, not just the first section checked.
7.  Episodic-memory-only source: a concept recorded via
    _record_episodic_experience but never committed as a section word
    still resolves (honest, from a second real, independent tick source).
8.  Reentrant-safe: _word_order_relation can be called while the caller
    already holds self.lock (self.lock is an RLock; _form_reflection()
    is always invoked from _autonomy_tick() under self.lock) without
    deadlocking. Verified with a background-thread + join(timeout=...)
    safety net so a real regression fails loudly instead of hanging the
    suite.
9.  _form_reflection() wiring: context_order key present, and genuinely
    reflects real committed order between the concept and its real
    context word(s) -- not merely present-but-empty decoration.
10. _form_reflection() wiring, honest-unknown case: a context word that
    was recorded episodically (via the trailing-context window) but was
    never itself committed to any section resolves to "unknown" in
    context_order, without raising and without fabricating an order.
11. _form_reflection() output changes: two reflections built from
    genuinely different real commit orderings produce genuinely
    different context_order values -- proves the field tracks real data,
    not a constant/decorative default.
"""

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402


def test_1_before_and_after_real_committed_words():
    print("Test 1: real committed words, known tick order -> before/after...")
    g = Guala()
    g.read_word("alpha", source="corpus")
    g.read_word("beta", source="corpus")
    assert g._word_order_relation("alpha", "beta") == "before"
    assert g._word_order_relation("beta", "alpha") == "after"
    print("  OK")


def test_2_same_tick_within_one_read_word_call():
    print("Test 2: sections committed within the SAME read_word() call "
          "share one engine tick -> 'same'...")
    g = Guala()
    g.read_word("gizmo", source="corpus")
    # "gizmo" is committed to more than one section (e.g. "listen" plus a
    # primary role section) within this single call, all under the same
    # engine_tick -- comparing it against itself must be a real "same",
    # not an artifact.
    assert g._word_order_relation("gizmo", "gizmo") == "same"

    # Direct fixture for two genuinely DIFFERENT words landing on the same
    # real tick -- exactly what happens when read_word() commits several
    # sections for one call (listen/primary/ground/intro all share one
    # engine_tick). Writing straight into a section's own real "commits"
    # list (the same {"tick", "mode", "chi", "word", "grounded"} shape
    # Section.receive() itself appends) is a controlled, deterministic
    # substitute for that multi-section fan-out -- same convention
    # test_reflection_emission_candidates.py's own _commit_word() helper
    # uses, not a fabrication of real pipeline data.
    sec = g.sections["subject"]
    sec.commits.append({"tick": 999, "mode": 0, "chi": 0.0,
                         "word": "north", "grounded": False})
    sec.commits.append({"tick": 999, "mode": 1, "chi": 0.0,
                         "word": "south", "grounded": False})
    assert g._word_order_relation("north", "south") == "same"
    print("  OK")


def test_3_unknown_for_never_committed_words():
    print("Test 3: a word never committed anywhere -> 'unknown', both "
          "directions...")
    g = Guala()
    g.read_word("alpha", source="corpus")
    assert g._word_order_relation("alpha", "nowhere_word_xyz") == "unknown"
    assert g._word_order_relation("nowhere_word_xyz", "alpha") == "unknown"
    assert g._word_order_relation("nope1_xyz", "nope2_xyz") == "unknown"
    print("  OK")


def test_4_unknown_for_empty_or_none_args():
    print("Test 4: empty/None word args -> 'unknown', no exception...")
    g = Guala()
    assert g._word_order_relation("", "beta") == "unknown"
    assert g._word_order_relation("alpha", "") == "unknown"
    assert g._word_order_relation(None, None) == "unknown"
    assert g._word_order_relation(None, "alpha") == "unknown"
    print("  OK")


def test_5_case_insensitive():
    print("Test 5: case-insensitive lookup, matching _word_to_mode_idx's "
          "own .lower() convention...")
    g = Guala()
    g.read_word("Alpha", source="corpus")
    g.read_word("BETA", source="corpus")
    assert g._word_order_relation("alpha", "beta") == "before"
    assert g._word_order_relation("ALPHA", "Beta") == "before"
    print("  OK")


def test_6_most_recent_tick_across_multiple_sections():
    print("Test 6: a word committed in more than one section uses the "
          "MOST RECENT tick across all of them...")
    g = Guala()
    g.read_word("recur", source="corpus")
    g.read_word("marker", source="corpus")
    # Re-commit "recur" later -- its most recent real tick should now be
    # AFTER "marker", even though its first commit was before "marker".
    g.read_word("recur", source="corpus")
    assert g._word_order_relation("marker", "recur") == "before"
    assert g._word_order_relation("recur", "marker") == "after"
    print("  OK")


def test_7_episodic_only_source_resolves():
    print("Test 7: a concept recorded only via episodic memory (never "
          "committed as a section word) still resolves...")
    g = Guala()
    g.read_word("early_word", source="corpus")
    # Advance the engine tick with an unrelated real commit so the
    # episodic-memory tick recorded below is deterministically LATER than
    # "early_word"'s section-commit tick, instead of coincidentally tying
    # (self.tick is otherwise untouched between the two).
    g.read_word("filler_word", source="corpus")
    g._episodic_recent_concepts.append("early_word")
    g._record_episodic_experience("episodic_only_concept")
    # "episodic_only_concept" was never passed to read_word() -- it has no
    # section commit at all, only an episodic-memory tick.
    rel = g._word_order_relation("early_word", "episodic_only_concept")
    assert rel == "before", (
        f"expected 'early_word' (committed first) before "
        f"'episodic_only_concept' (episodic-only, recorded later), got "
        f"{rel!r} -- episodic-only source may not be consulted correctly")
    print(f"  OK: {rel}")


def test_8_reentrant_safe_under_self_lock():
    print("Test 8: reentrant-safe when caller already holds self.lock "
          "(RLock) -- verified with a join(timeout) safety net...")
    g = Guala()
    g.read_word("alpha", source="corpus")
    g.read_word("beta", source="corpus")

    result = {}

    def _run():
        with g.lock:
            result["rel"] = g._word_order_relation("alpha", "beta")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=5.0)
    assert not t.is_alive(), (
        "_word_order_relation deadlocked when called while self.lock was "
        "already held -- self.lock must be an RLock for this to be safe")
    assert result.get("rel") == "before", f"unexpected result: {result}"
    print("  OK: no deadlock, correct result under nested lock")


def test_9_form_reflection_includes_context_order():
    print("Test 9: _form_reflection() output includes a real, correct "
          "context_order...")
    g = Guala()
    g.read_word("party", source="corpus")
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")
    g.read_word("cake", source="corpus")

    reflection = g._form_reflection()
    assert reflection is not None
    assert reflection["concept"] == "cake"
    assert reflection["context_then"] == ["party"]
    assert "context_order" in reflection, (
        "_form_reflection() must surface real order information for its "
        "context words, not just context_then")
    assert reflection["context_order"] == {"party": "before"}, (
        f"expected party (committed first) 'before' cake (committed "
        f"after), got {reflection['context_order']}")
    print(f"  OK: {reflection['context_order']}")


def test_10_form_reflection_honest_unknown_for_uncommitted_context_word():
    print("Test 10: a context word with no real commit at all resolves "
          "to 'unknown' in context_order, no exception...")
    g = Guala()
    # "ghost_word" enters the episodic trailing-context window but is
    # never itself committed to any section or recorded episodically.
    g._episodic_recent_concepts.append("ghost_word")
    g._record_episodic_experience("cake")
    g.read_word("cake", source="corpus")

    reflection = g._form_reflection()
    assert reflection is not None
    assert reflection["context_then"] == ["ghost_word"]
    assert reflection["context_order"] == {"ghost_word": "unknown"}, (
        f"expected honest 'unknown' for a never-committed context word, "
        f"got {reflection['context_order']}")
    print(f"  OK: {reflection['context_order']}")


def test_11_form_reflection_context_order_tracks_real_data():
    print("Test 11: two reflections built from genuinely different real "
          "commit orderings produce genuinely different context_order "
          "values -- proves the field isn't a decorative constant...")
    g = Guala()

    # Story A: "party" committed BEFORE "cake".
    g.read_word("party", source="corpus")
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")
    g.read_word("cake", source="corpus")
    reflection_a = g._form_reflection()
    assert reflection_a["context_order"] == {"party": "before"}

    g.tick += Guala.REFLECTION_MIN_TICKS_BETWEEN

    # Story B: re-commit "party" AFTER "cake" this time, then reflect on
    # cake again with party still the freshest context word.
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")
    g.read_word("party", source="corpus")  # now party's most recent tick > cake's
    reflection_b = g._form_reflection()
    assert reflection_b["context_order"] == {"party": "after"}, (
        f"expected order to flip once the real underlying commit order "
        f"flipped, got {reflection_b['context_order']}")
    print(f"  OK: story A={reflection_a['context_order']} -> "
          f"story B={reflection_b['context_order']}")


if __name__ == "__main__":
    tests = [
        test_1_before_and_after_real_committed_words,
        test_2_same_tick_within_one_read_word_call,
        test_3_unknown_for_never_committed_words,
        test_4_unknown_for_empty_or_none_args,
        test_5_case_insensitive,
        test_6_most_recent_tick_across_multiple_sections,
        test_7_episodic_only_source_resolves,
        test_8_reentrant_safe_under_self_lock,
        test_9_form_reflection_includes_context_order,
        test_10_form_reflection_honest_unknown_for_uncommitted_context_word,
        test_11_form_reflection_context_order_tracks_real_data,
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
