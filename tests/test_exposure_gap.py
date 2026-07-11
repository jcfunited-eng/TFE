"""
test_exposure_gap.py — local functional tests for
GL-FIX-EXPOSURE-GAP-C1-20260711

Tests against the REAL Guala engine (dsf_ai_service/v4/gualaloom_v5_engine.py)
and the REAL LivingAtlas (dsf_ai_service/v4/gualaloom_v6_living_atlas.py), not
mocks. Context: GL-RPT-BRAIN-THEORY-OF-MIND-SCOPE-C1-20260711-v1 found every
existing "who" mechanism (presence, pair-bond, episodic source) is single-
point-of-view provenance -- a tag on the substrate's own one memory, never a
second, independent representation of someone else's mind -- and explicitly
ruled real theory-of-mind out of scope without further design input. This
dispatch does NOT build theory-of-mind. It builds one honestly-scoped,
strictly narrower thing that report's own §7 identified as a real, buildable
next step beyond mere presence-tagging: knowledge-GAP tracking. Concretely --
does the substrate have a real record of a specific source's presence ever
co-occurring with a specific binding, across ALL the times that binding was
touched (not just the most recent one)?

Before this dispatch, LivingAtlas.record()'s `presence` field was last-write-
wins (see record()'s own "situation — last-write-wins" comment) -- a binding
formed while Joe was present, later reinforced while he was away, would
silently forget Joe was ever there. presence_ever/presence_observations fix
that by accumulating the SAME real per-call presence snapshot instead of
overwriting it. exposure_gap()/exposure_gap_for_word()/
_episodic_exposure_gap() are the new read-only queries built on top.

HONEST SCOPE (see each new method's own docstring for the full statement):
a "gap" (True) result means "no record of this source's presence in Guala's
OWN log," never "this source doesn't know it" -- they could have learned it
anywhere outside anything Guala tracks. This cannot represent a source
holding a FALSE belief, only recorded-absent vs. recorded-present vs.
honestly-unknown (no data at all, never conflated with a gap). This is not
theory of mind and nothing in this file should be read as testing that it is.

Covers:
1.  Atlas-level, direct: a fresh binding recorded with presence=["wc"] then
    reinforced with presence=["joe"] -- exposure_gap() shows BOTH joe and wc
    as "seen" (not gaps), proving real accumulation across separate calls.
2.  Atlas-level: the OLD last-write-wins `presence` field on that same entry
    only shows the MOST RECENT source (joe) -- the concrete "old field loses
    history, new field doesn't" contrast that motivates this fix.
3.  Atlas-level: a binding whose record() calls never received a `presence`
    kwarg at all (plain corpus-style write) -> exposure_gap() returns None
    (honest "no data"), never a dict asserting a gap from missing data.
4.  Atlas-level: no live binding at this chi at all -> None.
5.  Atlas-level: empty tracked_sources -> None, no exception.
6.  Atlas-level: a binding whose strength has decayed below
    FORGETTING_THRESHOLD is not counted as live data -> None, even though
    presence was once recorded on it.
7.  Engine, real converse() path, word learned while a source was ABSENT:
    Joe never wakes at all; wc converses about a nonsense word -> Joe is
    flagged as a real, traceable knowledge gap for that word.
8.  Engine, real converse() path, word learned while present: Joe wakes and
    converses about a nonsense word -> Joe is NOT flagged as a gap for that
    word.
9.  Engine: never-committed word -> exposure_gap_for_word() is None.
10. Engine: a word read via plain read_word(source="corpus") (no presence
    ever threaded through, matching ordinary autonomous reading) ->
    exposure_gap_for_word() is None, not a false gap claim.
11. Engine, real converse() path, cross-turn accumulation: the SAME word
    reinforced across two real converse() turns from two different lone-
    present sources (wc, then joe, with wc's presence flag flipped off in
    between via the same direct-state-manipulation convention
    test_presence_keepalive.py already uses) -> exposure_gap_for_word()
    shows BOTH as seen, while recall_scene_for_word()'s own (unchanged)
    last-write-wins `presence` field shows only the second (joe) -- the
    same real old-field-vs-new-field contrast as test 1/2, now proven
    through the actual production converse() call path, not direct
    LivingAtlas calls.
12. Episodic memory: a concept with no episodic record at all ->
    _episodic_exposure_gap() is None.
13. Episodic memory: a concept recorded once, with Joe absent (wc present)
    -> Joe flagged as a gap, wc not.
14. Episodic memory: the SAME concept recorded a second time, later, with
    Joe present -> Joe is no longer flagged as a gap (real accumulation
    across genuinely distinct episodic records, append-only by design).
15. tracked_sources is read live from Coordinator._presence's own keys, not
    hardcoded -- exposure_gap_for_word()/_episodic_exposure_gap() results
    always cover exactly {"joe", "wc", "c1"} for a real Guala().
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402
from dsf_ai_service.v4.gualaloom_v6_living_atlas import (  # noqa: E402
    LivingAtlas, FORGETTING_THRESHOLD,
)


# ---------------------------------------------------------------------
# Atlas-level, direct (fast, precise, no engine overhead)
# ---------------------------------------------------------------------

def test_1_atlas_accumulates_across_separate_calls():
    print("Test 1: exposure_gap() accumulates presence across separate "
          "record() calls (creation + reinforcement)...")
    atlas = LivingAtlas()
    atlas.record("listen", 1, 500, tick=1, presence=["wc"])
    # Same (section, motif) near the same chi -> reinforces the SAME entry.
    atlas.record("listen", 1, 500, tick=2, presence=["joe"])
    gap = atlas.exposure_gap(500, ("joe", "wc", "c1"))
    assert gap == {"joe": False, "wc": False, "c1": True}, (
        f"expected both joe and wc recorded as SEEN (accumulated across "
        f"both calls) and c1 as a real gap, got {gap}")
    print(f"  OK: {gap}")


def test_2_old_presence_field_is_still_last_write_wins():
    print("Test 2: the OLD `presence` field on the same entry is still "
          "last-write-wins (only the most recent source) -- the exact "
          "history loss exposure_gap's accumulation fixes...")
    atlas = LivingAtlas()
    atlas.record("listen", 1, 500, tick=1, presence=["wc"])
    atlas.record("listen", 1, 500, tick=2, presence=["joe"])
    entry = atlas.entries[500][0]
    assert entry["presence"] == ["joe"], (
        f"expected last-write-wins `presence` to show only the most "
        f"recent source, got {entry['presence']}")
    assert set(entry["presence_ever"]) == {"wc", "joe"}, (
        f"expected presence_ever to have accumulated BOTH sources, got "
        f"{entry['presence_ever']}")
    assert entry["presence_observations"] == 2
    print(f"  OK: presence={entry['presence']!r} (lossy) vs. "
          f"presence_ever={entry['presence_ever']!r} (complete)")


def test_3_no_presence_data_is_honest_unknown_not_a_gap():
    print("Test 3: a binding that never had a real presence check "
          "recorded -> None (honest unknown), never asserted as a gap...")
    atlas = LivingAtlas()
    atlas.record("listen", 2, 600, tick=1)  # presence kwarg omitted entirely
    gap = atlas.exposure_gap(600, ("joe", "wc", "c1"))
    assert gap is None, (
        f"missing presence data must resolve to None, not a gap dict; "
        f"got {gap}")
    print("  OK: None")


def test_4_no_binding_at_all():
    print("Test 4: no live binding anywhere near this chi -> None...")
    atlas = LivingAtlas()
    gap = atlas.exposure_gap(123456, ("joe", "wc", "c1"))
    assert gap is None
    print("  OK: None")


def test_5_empty_tracked_sources():
    print("Test 5: empty tracked_sources -> None, no exception...")
    atlas = LivingAtlas()
    atlas.record("listen", 1, 500, tick=1, presence=["wc"])
    assert atlas.exposure_gap(500, ()) is None
    assert atlas.exposure_gap(500, None) is None
    print("  OK")


def test_6_forgotten_binding_not_counted_as_live_data():
    print("Test 6: a binding whose strength has decayed below "
          "FORGETTING_THRESHOLD is not counted as live evidence...")
    atlas = LivingAtlas()
    atlas.record("listen", 1, 700, tick=1, presence=["wc"])
    # record() writes one entry PER chi bucket across the whole band
    # (chi_value +/- atlas.band), not just at chi_value itself -- exposure_
    # gap() aggregates across that same band, so every real entry in it
    # must be pushed below threshold for this to be a genuine "nothing
    # live here" case rather than an artifact of only clearing one of
    # several duplicate band entries.
    entry_count = 0
    for d in range(-atlas.band, atlas.band + 1):
        for e in atlas.entries.get(700 + d, []):
            assert e["strength"] >= FORGETTING_THRESHOLD  # sanity: real binding
            e["strength"] = FORGETTING_THRESHOLD / 2.0  # simulate real decay
            entry_count += 1
    assert entry_count > 0, "sanity: record() must have written real entries"
    gap = atlas.exposure_gap(700, ("joe", "wc", "c1"))
    assert gap is None, (
        f"a forgotten (below-threshold) binding must not produce a gap "
        f"claim even though presence was once recorded on it; got {gap}")
    print("  OK: None (forgotten binding correctly excluded)")


# ---------------------------------------------------------------------
# Engine-level, real converse()/read_word() production paths
# ---------------------------------------------------------------------

def _wake(g, source):
    g.coordinator.wake(source, g, g.needs, g.atlas)


def test_7_real_converse_word_learned_while_source_absent():
    print("Test 7: real converse() path -- a word learned while Joe was "
          "genuinely absent is correctly flagged as a knowledge gap for "
          "Joe...")
    g = Guala()
    _wake(g, "wc")  # joe and c1 never wake -- genuinely absent throughout
    assert g.coordinator._presence["joe"] is False
    g.converse("the zorbnak flew quietly overhead", source="wc")
    gap = g.exposure_gap_for_word("zorbnak")
    assert gap is not None, "expected real presence data, not None"
    assert gap["joe"] is True, (
        f"Joe was never present -- expected a real gap, got {gap}")
    assert gap["wc"] is False, (
        f"wc was present and speaking -- expected NOT a gap, got {gap}")
    assert gap["c1"] is True
    print(f"  OK: {gap}")


def test_8_real_converse_word_learned_while_source_present():
    print("Test 8: real converse() path -- a word learned while Joe was "
          "present is NOT flagged as a gap for Joe...")
    g = Guala()
    _wake(g, "joe")
    assert g.coordinator._presence["joe"] is True
    g.converse("the plimwaddle is a strange invention", source="joe")
    gap = g.exposure_gap_for_word("plimwaddle")
    assert gap is not None
    assert gap["joe"] is False, (
        f"Joe was present for this exact turn -- expected NOT a gap, got "
        f"{gap}")
    print(f"  OK: {gap}")


def test_9_never_committed_word_is_none():
    print("Test 9: a word never committed anywhere -> None...")
    g = Guala()
    assert g.exposure_gap_for_word("nowhere_word_never_seen_xyz") is None
    assert g.exposure_gap_for_word("") is None
    assert g.exposure_gap_for_word(None) is None
    print("  OK")


def test_10_plain_corpus_read_has_no_presence_data():
    print("Test 10: plain read_word(source='corpus'), no presence ever "
          "threaded through -> None, not a false gap claim...")
    g = Guala()
    g.read_word("ordinarybookword", source="corpus")
    gap = g.exposure_gap_for_word("ordinarybookword")
    assert gap is None, (
        f"a corpus-only read with no real presence check must be honest "
        f"'unknown' (None), never a gap dict asserted from missing data; "
        f"got {gap}")
    print("  OK: None")


def test_11_real_converse_cross_turn_accumulation_vs_old_field():
    print("Test 11: real converse() path, same word reinforced across two "
          "turns from two different lone-present sources -- exposure_gap "
          "sees BOTH, recall_scene_for_word's last-write-wins field sees "
          "only the second...")
    g = Guala()
    _wake(g, "wc")
    g.converse("a gribblewhack sat on the shelf", source="wc")

    # wc genuinely leaves, joe genuinely arrives -- same direct-state
    # convention test_presence_keepalive.py already uses (manipulating
    # coordinator state directly to deterministically model a real
    # presence transition without waiting out a real timeout).
    g.coordinator._presence["wc"] = False
    _wake(g, "joe")
    assert g.coordinator._presence["wc"] is False
    assert g.coordinator._presence["joe"] is True
    # _current_situation() caches its (presence, location, sky_state)
    # result for 100 ticks (see that method's own docstring) -- a real,
    # pre-existing production behavior, not something this fix touches.
    # Advance well past it so the second converse() turn resolves a
    # genuinely FRESH presence snapshot instead of replaying the first
    # turn's cached one (which would silently mask the real state change
    # this test exists to exercise).
    g.tick += 150

    g.converse("the gribblewhack is odd today", source="joe")

    gap = g.exposure_gap_for_word("gribblewhack")
    assert gap["wc"] is False, (
        f"wc's earlier real presence must still be on record even after "
        f"a later reinforcement by a different lone source; got {gap}")
    assert gap["joe"] is False
    assert gap["c1"] is True

    scene = g.recall_scene_for_word("gribblewhack")
    assert scene is not None
    assert scene["presence"] == ["joe"], (
        f"sanity check: the OLD last-write-wins field should show only "
        f"the most recent source (joe), losing wc's earlier real "
        f"presence -- got {scene['presence']}. If this fails, the "
        f"contrast this test demonstrates no longer holds.")
    print(f"  OK: exposure_gap={gap} (complete) vs. "
          f"recall_scene presence={scene['presence']} (lossy, unchanged)")


# ---------------------------------------------------------------------
# Episodic-memory-level, real _record_episodic_experience() history
# ---------------------------------------------------------------------

def test_12_episodic_no_record_is_none():
    print("Test 12: a concept with no episodic memory at all -> None...")
    g = Guala()
    assert g._episodic_exposure_gap("never_experienced_concept_xyz") is None
    print("  OK")


def test_13_episodic_gap_when_recorded_while_source_absent():
    print("Test 13: a concept recorded episodically while Joe was "
          "genuinely absent -> Joe flagged as a real gap...")
    g = Guala()
    _wake(g, "wc")
    assert g.coordinator._presence["joe"] is False
    g._record_episodic_experience("birthday_cake_test_concept")
    gap = g._episodic_exposure_gap("birthday_cake_test_concept")
    assert gap is not None
    assert gap["joe"] is True, f"expected a real gap for joe, got {gap}"
    assert gap["wc"] is False
    print(f"  OK: {gap}")


def test_14_episodic_gap_closes_on_a_later_genuine_exposure():
    print("Test 14: the SAME concept, recorded a SECOND time later while "
          "Joe is present -> the gap closes (real accumulation across "
          "genuinely distinct episodic records)...")
    g = Guala()
    _wake(g, "wc")
    g._record_episodic_experience("second_exposure_test_concept")
    gap_before = g._episodic_exposure_gap("second_exposure_test_concept")
    assert gap_before["joe"] is True

    _wake(g, "joe")
    # Same 100-tick _current_situation() cache as test 11 -- advance past
    # it so this second episodic record resolves joe's real, current
    # presence instead of replaying the first record's cached snapshot.
    g.tick += 150
    g._record_episodic_experience("second_exposure_test_concept")
    gap_after = g._episodic_exposure_gap("second_exposure_test_concept")
    assert gap_after["joe"] is False, (
        f"a later genuine exposure must close the gap, got {gap_after}")
    assert gap_after["wc"] is False, "wc's earlier exposure must persist"
    print(f"  OK: before={gap_before} -> after={gap_after}")


def test_15_tracked_sources_read_live_from_coordinator():
    print("Test 15: tracked_sources always matches Coordinator._presence's "
          "own live roster, not a hardcoded list...")
    g = Guala()
    _wake(g, "joe")
    g.converse("a quibnorf appeared suddenly", source="joe")
    gap = g.exposure_gap_for_word("quibnorf")
    assert set(gap.keys()) == set(g.coordinator._presence.keys()), (
        f"exposure_gap_for_word's source roster {set(gap.keys())} must "
        f"match the live Coordinator._presence roster "
        f"{set(g.coordinator._presence.keys())}")
    print(f"  OK: {sorted(gap.keys())}")


if __name__ == "__main__":
    tests = [
        test_1_atlas_accumulates_across_separate_calls,
        test_2_old_presence_field_is_still_last_write_wins,
        test_3_no_presence_data_is_honest_unknown_not_a_gap,
        test_4_no_binding_at_all,
        test_5_empty_tracked_sources,
        test_6_forgotten_binding_not_counted_as_live_data,
        test_7_real_converse_word_learned_while_source_absent,
        test_8_real_converse_word_learned_while_source_present,
        test_9_never_committed_word_is_none,
        test_10_plain_corpus_read_has_no_presence_data,
        test_11_real_converse_cross_turn_accumulation_vs_old_field,
        test_12_episodic_no_record_is_none,
        test_13_episodic_gap_when_recorded_while_source_absent,
        test_14_episodic_gap_closes_on_a_later_genuine_exposure,
        test_15_tracked_sources_read_live_from_coordinator,
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
