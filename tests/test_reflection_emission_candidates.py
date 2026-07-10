"""
test_reflection_emission_candidates.py — local functional tests for
GL-CMD-REFLECTION-EMISSION-EVE-20260710

Tests against the REAL Guala engine (dsf_ai_service/v4/gualaloom_v5_engine.py),
not mocks. Mirrors the coverage shape of imagination's own (unshipped-as-a-
file, but adversarially reviewed) local test suite from commit 79e0233:
chain-of-custody, cap enforcement, weight damping, both kill switches, a
fresh-boot-zero-reflections case, and a malformed/legacy-entry safety case.

Covers:
1.  Fresh boot: zero reflections yet -> honest empty, no exception.
2.  Seed-word gate: an unknown seed word (no real committed section home)
    never unlocks a walk, even if a matching reflection exists.
3.  Chain of custody: a real _record_episodic_experience() +
    _form_reflection() call sequence produces a candidate whose word is
    exactly the real, previously co-experienced context word -- nothing
    fabricated.
4.  Self-echo / exclude_words respected.
5.  Only the single freshest matching reflection is used -- distinct
    remembered stories are never merged.
6.  Weight equals the fixed, documented, damped constant (REFLECTION_
    BASE_STRENGTH * REFLECTION_EMISSION_WEIGHT_SCALE), and stays well
    below a real full-confidence candidate's weight.
7.  Cap: _brain_emission_candidates_legacy never merges more than
    REFLECTION_EMISSION_MAX_CANDIDATES_PER_TURN reflection-origin
    candidates into the final list, even when a reflection's context
    holds more real, grounded words than the cap.
8.  Kill switch: REFLECTION_EMISSION_ENABLED=False suppresses the merge
    entirely (module-level constant, monkeypatched like IMAGINATION_
    ENABLED would need to be -- both are bound once at import time, not
    re-read per call).
9.  Full real wiring path: _brain_emission_candidates_legacy surfaces a
    reflection-origin candidate end to end, tagged "origin": "reflection",
    merged into the SAME candidate list the rest of emission scoring
    already consumes.
10. Weight genuinely governs ranking: the topk selection path's own sort
    (deep_candidates.sort(key=lambda x: x[2], reverse=True), exactly as
    _emit_from_invariants' topk branch does it) puts a real full-
    confidence candidate ahead of a reflection-origin one.
11. Adversarial: a malformed/legacy entry sitting in self._reflections
    (missing "context_then" key, or "context_then": None, or missing
    "concept") never raises -- honest empty for that entry, rest of the
    turn unaffected. Simulates "a future writer changes the not-
    persisted-today invariant" per the function's own docstring caveat.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dsf_ai_service.v4.gualaloom_v5_engine as engine_mod  # noqa: E402
from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402


def _commit_word(g, word, section="subject", mode_idx=0):
    """Directly give a word a real, single-location committed section
    home in _word_to_emission_sections -- the same real-grounding gate
    every candidate source in this codebase already trusts (see
    _brain_emission_candidates_legacy's own docstring). A single-location
    list is deliberate: _best_fit_location returns locations[0] directly
    whenever len(locations) == 1, without touching sec.modes/DSF state at
    all, so this is a safe, minimal fixture -- not a fabrication of the
    real production commit pipeline, just a controlled, deterministic
    substitute for it (same convention test_autonomy_drive.py's own
    test_gate5 uses when it directly sets g.needs.connection rather than
    driving a real need-satisfying activity to completion)."""
    wl = word.lower()
    g._word_to_emission_sections.setdefault(wl, []).append((section, mode_idx, word))


def _stub_organism_self_echo(g, word):
    """_brain_emission_candidates_legacy early-returns [] (line ~4788,
    "if not merged_votes: return []") before ever reaching the deep_atlas/
    imagination/reflection merge stages, whenever organism.recall_fast
    has nothing to vote -- true of a fresh, untrained Guala() for any
    word (verified directly: Guala().organism.recall_fast(...) returns
    an empty Counter for a never-taught word). Stubbing a self-echo-only
    vote for `word` is the minimal way to pass that early gate: the
    function's own self-echo filter (w.lower() in input_words_lower)
    excludes a self-vote from contributing any real candidate, so this
    isolates the reflection merge as the only real candidate source
    under test, without needing to actually train the organism (a
    separate, independently-validated mechanism, not what's under test
    here)."""
    from collections import Counter
    g.organism.recall_fast = lambda signal, _w=word: Counter({_w: 1})


def test_1_fresh_boot_zero_reflections():
    print("Test 1: fresh boot, zero reflections -> honest empty...")
    g = Guala()
    assert len(g._reflections) == 0
    _commit_word(g, "cake")
    assert g._reflection_candidates("cake") == []
    print("  OK")


def test_2_seed_word_gate():
    print("Test 2: unknown seed word never unlocks a walk...")
    g = Guala()
    _commit_word(g, "party")
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")
    g._form_reflection()
    assert len(g._reflections) == 1
    # "cake" itself was never committed to a section -- gate must hold
    # even though a real matching reflection exists.
    assert g._reflection_candidates("cake") == []
    print("  OK")


def test_3_chain_of_custody():
    print("Test 3: real episodic experience -> real reflection -> real "
          "candidate, nothing fabricated...")
    g = Guala()
    _commit_word(g, "cake")
    _commit_word(g, "party")
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")  # context = ["party"], real write
    reflection = g._form_reflection()
    assert reflection is not None
    assert reflection["concept"] == "cake"
    assert reflection["context_then"] == ["party"]

    out = g._reflection_candidates("cake")
    assert len(out) == 1, f"expected exactly one real candidate, got {out}"
    word_label, weight, section, mode_idx = out[0]
    assert word_label == "party", (
        f"candidate word must be the real co-experienced word, got {word_label!r}")
    assert section == "subject" and mode_idx == 0
    print(f"  OK: candidate={out[0]}")


def test_4_exclude_words_and_self_echo():
    print("Test 4: exclude_words + self-echo respected...")
    g = Guala()
    _commit_word(g, "cake")
    _commit_word(g, "party")
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")
    g._form_reflection()

    # exclude_words suppresses "party"
    out = g._reflection_candidates("cake", exclude_words={"party"})
    assert out == [], f"exclude_words not respected: {out}"

    # seed word can never nominate itself even if somehow present in its
    # own context_then
    g._reflections[-1]["context_then"] = ["cake"]
    out2 = g._reflection_candidates("cake")
    assert out2 == [], f"self-echo not excluded: {out2}"
    print("  OK")


def test_5_only_freshest_reflection_used():
    print("Test 5: distinct remembered stories are never merged...")
    g = Guala()
    for w in ("cake", "party", "beach", "kite"):
        _commit_word(g, w)

    # Older story: cake near a party.
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")
    g._form_reflection()
    g.tick += engine_mod.Guala.REFLECTION_MIN_TICKS_BETWEEN

    # _record_episodic_experience's own "context" is a real, honest
    # sliding recency window (EPISODIC_RECENT_CONTEXT_WINDOW), not a
    # story boundary -- "party" would legitimately still appear in a
    # SECOND story's context if it's still within the trailing-5 window,
    # and that's correct behavior for that (already-shipped, unmodified)
    # function, not something this test should fight. To build a
    # genuinely distinct second story for this test, age "party" out of
    # the trailing-5 window first with real (uncommitted, so gate-
    # excluded either way) filler concepts -- isolating what's actually
    # under test here: that _reflection_candidates itself never reaches
    # back past the freshest matching reflection, whatever that
    # reflection's own real context turned out to contain.
    for filler in ("f1", "f2", "f3", "f4", "f5"):
        g._episodic_recent_concepts.append(filler)

    # Fresher, distinct story: cake near a beach/kite day instead.
    g._episodic_recent_concepts.append("beach")
    g._episodic_recent_concepts.append("kite")
    g._record_episodic_experience("cake")
    g._form_reflection()

    assert len(g._reflections) == 2
    assert g._reflections[-1]["context_then"] == ["f3", "f4", "f5", "beach", "kite"], (
        f"fixture assumption about the trailing-5 window broke: "
        f"{g._reflections[-1]['context_then']}")
    out = g._reflection_candidates("cake")
    words = sorted(w for w, _wt, _s, _m in out)
    assert "party" not in words, (
        f"stale story's context leaked into the fresh reflection's candidates: {words}")
    assert set(words) <= {"beach", "kite"}, f"unexpected words: {words}"
    assert words, "expected at least one real word from the freshest story"
    print(f"  OK: only fresh story's words surfaced: {words}")


def test_6_weight_is_fixed_and_damped():
    print("Test 6: weight equals the documented damped constant, well "
          "below a real full-confidence candidate...")
    g = Guala()
    _commit_word(g, "cake")
    _commit_word(g, "party")
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")
    g._form_reflection()

    out = g._reflection_candidates("cake")
    assert len(out) == 1
    _word, weight, _section, _mode = out[0]
    expected = engine_mod.REFLECTION_BASE_STRENGTH * engine_mod.REFLECTION_EMISSION_WEIGHT_SCALE
    assert abs(weight - expected) < 1e-12, f"weight {weight} != expected {expected}"
    assert weight < 1.0, "a reflection candidate must never reach full confidence"
    print(f"  OK: weight={weight} (base={engine_mod.REFLECTION_BASE_STRENGTH} x "
          f"scale={engine_mod.REFLECTION_EMISSION_WEIGHT_SCALE})")


def test_7_cap_enforced_in_full_wiring():
    print("Test 7: cap enforced even when context holds more real words "
          "than REFLECTION_EMISSION_MAX_CANDIDATES_PER_TURN...")
    g = Guala()
    words = ["cake", "party", "beach", "kite", "sun"]
    for w in words:
        _commit_word(g, w)
    for w in words[1:]:
        g._episodic_recent_concepts.append(w)
    g._record_episodic_experience("cake")  # context_then = last 5 -> 4 real words
    reflection = g._form_reflection()
    assert len(reflection["context_then"]) >= 2, "fixture needs >1 context word"

    # _reflection_candidates itself can return more than the per-turn cap
    # (same as _imagination_candidates) -- the cap lives in the caller.
    raw = g._reflection_candidates("cake")
    assert len(raw) >= 2, f"fixture didn't produce enough raw candidates: {raw}"

    _stub_organism_self_echo(g, "cake")
    candidates = g._brain_emission_candidates_legacy(["cake"])
    reflection_candidates = [c for c in candidates if c[0].get("origin") == "reflection"]
    assert len(reflection_candidates) == engine_mod.REFLECTION_EMISSION_MAX_CANDIDATES_PER_TURN, (
        f"cap not exactly respected: {len(reflection_candidates)} reflection "
        f"candidates in final list "
        f"(cap={engine_mod.REFLECTION_EMISSION_MAX_CANDIDATES_PER_TURN}, "
        f"raw available={len(raw)})")
    print(f"  OK: {len(reflection_candidates)} reflection candidate(s) survived "
          f"merge (raw available: {len(raw)})")


def test_8_kill_switch_suppresses_merge():
    print("Test 8: REFLECTION_EMISSION_ENABLED=False suppresses the merge "
          "entirely...")
    g = Guala()
    _commit_word(g, "cake")
    _commit_word(g, "party")
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")
    g._form_reflection()

    # _reflection_candidates itself is unconditional -- the gate lives in
    # the caller, same architecture as IMAGINATION_ENABLED.
    assert g._reflection_candidates("cake"), "fixture must produce a real candidate"
    _stub_organism_self_echo(g, "cake")

    old = engine_mod.REFLECTION_EMISSION_ENABLED
    engine_mod.REFLECTION_EMISSION_ENABLED = False
    try:
        candidates = g._brain_emission_candidates_legacy(["cake"])
        reflection_candidates = [c for c in candidates if c[0].get("origin") == "reflection"]
        assert reflection_candidates == [], (
            f"kill switch did not suppress reflection candidates: {reflection_candidates}")
    finally:
        engine_mod.REFLECTION_EMISSION_ENABLED = old
    print("  OK: kill switch suppressed the merge")


def test_9_full_wiring_end_to_end():
    print("Test 9: full production wiring path surfaces a real "
          "reflection-origin candidate, merged into the SAME candidate "
          "list...")
    g = Guala()
    assert engine_mod.REFLECTION_EMISSION_ENABLED is True, (
        "default must be ON -- see module-level comment for the "
        "chain-of-custody reasoning")
    _commit_word(g, "cake")
    _commit_word(g, "party")
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")
    g._form_reflection()
    _stub_organism_self_echo(g, "cake")

    candidates = g._brain_emission_candidates_legacy(["cake"])
    reflection_candidates = [c for c in candidates if c[0].get("origin") == "reflection"]
    assert len(reflection_candidates) == 1, (
        f"expected exactly one reflection candidate merged in, got {reflection_candidates}")
    de, co, weight = reflection_candidates[0]
    assert de["origin"] == "reflection"
    assert "subject" in co and "0" in co["subject"]
    print(f"  OK: {reflection_candidates[0]}")


def test_10_weight_governs_topk_ordering():
    print("Test 10: weight genuinely governs the real topk selection "
          "sort (same key _emit_from_invariants' topk branch uses)...")
    g = Guala()
    _commit_word(g, "cake")
    _commit_word(g, "party")
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")
    g._form_reflection()
    _stub_organism_self_echo(g, "cake")

    candidates = list(g._brain_emission_candidates_legacy(["cake"]))
    reflection_candidates = [c for c in candidates if c[0].get("origin") == "reflection"]
    assert reflection_candidates, "fixture must produce a reflection candidate"

    # A real, full-confidence candidate for a different word/section --
    # shape identical to what the organism-vote / deep_atlas loops in
    # _brain_emission_candidates_legacy themselves produce.
    real_de = {"co_occurrence": {"object": {"0": 0.9}}, "clarity": 0.9, "origin": "brain"}
    candidates.append((real_de, real_de["co_occurrence"], 0.9))

    # Exactly the sort _emit_from_invariants' topk branch performs.
    candidates.sort(key=lambda x: x[2], reverse=True)
    assert candidates[0][0]["origin"] == "brain", (
        "a real full-confidence candidate must outrank a reflection-origin "
        "one -- weight is not being genuinely respected")
    print("  OK: real candidate sorted ahead of the reflection candidate")


def test_11_malformed_entry_missing_context_then_key():
    print("Test 11a: malformed entry missing 'context_then' key is safe...")
    g = Guala()
    _commit_word(g, "cake")
    g._reflections.append({"concept": "cake", "tick": g.tick})  # no context_then at all
    out = g._reflection_candidates("cake")
    assert out == [], f"expected honest empty, got {out}"
    print("  OK")


def test_11_malformed_entry_none_context_then():
    print("Test 11b: legacy entry with context_then explicitly None is "
          "safe (dict.get(key, default) does NOT catch an explicit None "
          "value -- this is the specific class of bug the 'or []' guard "
          "defends against)...")
    g = Guala()
    _commit_word(g, "cake")
    g._reflections.append({"concept": "cake", "tick": g.tick,
                            "context_then": None})
    out = g._reflection_candidates("cake")
    assert out == [], f"expected honest empty, got {out}"
    print("  OK")


def test_11_malformed_entry_missing_concept():
    print("Test 11c: malformed entry missing 'concept' key, sitting as the "
          "FRESHEST (newest) entry, is safely skipped -- the scan falls "
          "through to the older, real, well-formed reflection instead of "
          "raising...")
    g = Guala()
    _commit_word(g, "cake")
    _commit_word(g, "party")
    g._episodic_recent_concepts.append("party")
    g._record_episodic_experience("cake")
    g._form_reflection()  # real, well-formed entry, appended FIRST (older)

    # Malformed entry with no "concept" key at all, appended AFTER (newest).
    g._reflections.append({"tick": g.tick, "context_then": ["party"]})

    out = g._reflection_candidates("cake")
    words = [w for w, _wt, _s, _m in out]
    assert words == ["party"], f"expected ['party'], got {words}"
    print(f"  OK: {out}")


def test_11_malformed_entry_non_string_context_word():
    print("Test 11d: a non-string entry inside context_then is skipped, "
          "not fatal...")
    g = Guala()
    _commit_word(g, "cake")
    _commit_word(g, "party")
    g._reflections.append({"concept": "cake", "tick": 1,
                            "context_then": [None, 42, "", "party"]})
    out = g._reflection_candidates("cake")
    words = [w for w, _wt, _s, _m in out]
    assert words == ["party"], f"expected only the real string word, got {words}"
    print("  OK")


if __name__ == "__main__":
    tests = [
        test_1_fresh_boot_zero_reflections,
        test_2_seed_word_gate,
        test_3_chain_of_custody,
        test_4_exclude_words_and_self_echo,
        test_5_only_freshest_reflection_used,
        test_6_weight_is_fixed_and_damped,
        test_7_cap_enforced_in_full_wiring,
        test_8_kill_switch_suppresses_merge,
        test_9_full_wiring_end_to_end,
        test_10_weight_governs_topk_ordering,
        test_11_malformed_entry_missing_context_then_key,
        test_11_malformed_entry_none_context_then,
        test_11_malformed_entry_missing_concept,
        test_11_malformed_entry_non_string_context_word,
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
