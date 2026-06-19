"""
Phase 3 verification: GL-CMD-TEACHER-CORRECTION-BINDING-EVE-20260618-12

Tests:
  1. apply_teacher_correction produces correct atlas changes
  2. Repeated correction produces drift toward expected
  3. Event log captures full correction payload
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["EMISSION_MODE"] = "grandurun"
os.environ["DEEP_ATLAS_ENABLED"] = "1"
os.environ["DEEP_PRIOR_ENABLED"] = "1"
os.environ["DECAY_PAUSED"] = "0"
os.environ["GRANDURUN_LEGACY_8D"] = "0"
os.environ["GRANDURUN_SPIN_VECTOR"] = "0"
os.environ["LATERAL_INHIBITION_ENABLED"] = "1"
os.environ["EMISSION_DYNAMICS"] = "1"
os.environ["RICH_SENSORY_INPUT"] = "1"


def build_seeded_engine():
    from dsf_ai_service.v4.gualaloom_v5_engine import (
        Guala, deterministic_motif_id, LanguageKrimelack,
    )

    g = Guala()

    def chi_for(word):
        k = LanguageKrimelack()
        k.transduce(word)
        return k.winding

    corpus = [
        ("love",    "verb",     0.9, 0.9, 0.3, "joe_voice", []),
        ("heart",   "subject",  0.8, 0.8, 0.2, "joe_voice", []),
        ("ocean",   "object",   0.5, 0.4, 0.6, "corpus",    []),
        ("wave",    "subject",  0.6, 0.3, 0.5, "corpus",    []),
        ("moon",    "object",   0.5, 0.7, 0.6, "sight",     []),
        ("star",    "object",   0.5, 0.7, 0.6, "sight",     []),
        ("sky",     "subject",  0.4, 0.6, 0.3, "sight",     []),
        ("are",     "verb",     0.2, 0.1, 0.1, "corpus",    []),
        ("see",     "verb",     0.5, 0.3, 0.4, "sight",     []),
        ("light",   "object",   0.6, 0.5, 0.5, "sight",     []),
        ("dance",   "verb",     0.9, 0.8, 0.5, "corpus",    []),
        ("fire",    "object",   0.9, 0.3, 0.7, "corpus",    []),
        ("sing",    "verb",     0.8, 0.7, 0.8, "joe_voice", []),
        ("song",    "object",   0.8, 0.7, 0.6, "joe_voice", []),
    ]

    for word, section, arousal, valence, surprise, source, sensory_refs in corpus:
        chi = chi_for(word)
        g.vocab.add(word)
        mid = deterministic_motif_id(word)
        sec = g.sections.get(section)
        if sec and hasattr(sec, "modes"):
            while len(sec.modes) <= mid:
                sec.modes.append((0, 0, ""))
            sec.modes[mid] = (0, 0, word)
        for rep in range(8):
            g.atlas.record(
                section, mid, chi, tick=10 + rep,
                salience=1.8, dwell_ticks=5,
                arousal=arousal, valence=valence, surprise=surprise,
                source=source,
            )

    g.tick = 100
    for chi_k, entries in g.atlas.entries.items():
        for e in entries:
            if e["strength"] >= 0.1:
                g.deep_atlas.promote(e, "episodic", g.tick, working_atlas=g.atlas)
    print(f"Seeded: {len(corpus)} words")
    return g


def get_binding_strength(g, word):
    """Find total binding strength for a word across the atlas."""
    from dsf_ai_service.v4.gualaloom_v5_engine import (
        deterministic_motif_id, LanguageKrimelack,
    )
    k = LanguageKrimelack()
    k.transduce(word)
    chi = k.winding
    mid = deterministic_motif_id(word)
    total = 0.0
    for d in range(-g.atlas.band, g.atlas.band + 1):
        for e in g.atlas.entries.get(chi + d, []):
            if e.get("motif") == mid:
                total += e["strength"]
    return total


def main():
    print("GL-CMD-TEACHER-CORRECTION-BINDING Phase 3 Verification")
    print("=" * 70)

    g = build_seeded_engine()

    # ------------------------------------------------------------------
    # Test 1: Thumbs-down with expected response
    # ------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("  TEST 1: Thumbs-down with expected response")
    print(f"{'='*70}")

    # Snapshot "are" strength before
    are_before = get_binding_strength(g, "are")
    moon_before = get_binding_strength(g, "moon")
    print(f"  Before: 'are' strength={are_before:.3f}, 'moon' strength={moon_before:.3f}")

    # Apply correction: she said "are are are", should have said "the moon"
    g._substrate_events.clear()
    result = g.apply_teacher_correction(
        original_input="what do you see",
        her_emission="are are are",
        correct=False,
        expected_response="the moon",
        source="joe",
    )

    are_after = get_binding_strength(g, "are")
    moon_after = get_binding_strength(g, "moon")
    print(f"  After:  'are' strength={are_after:.3f}, 'moon' strength={moon_after:.3f}")
    print(f"  Result: {result['n_affected']} affected bindings")

    # Check: "are" should be weaker, "moon" should be same or stronger
    weakened = are_after < are_before
    expected_ingested = result['n_affected'] > 0
    print(f"  'are' weakened: {weakened}")
    print(f"  Expected ingested: {expected_ingested}")

    # Check event log
    correction_events = [evt for evt in g._substrate_events
                         if hasattr(evt, 'kind') and evt.kind == "teacher_correction"]
    event_logged = len(correction_events) > 0
    print(f"  Event logged: {event_logged}")
    if correction_events:
        evt = correction_events[0]
        print(f"    correct={evt.detail.get('correct')}")
        print(f"    expected={evt.detail.get('expected_response')}")
        print(f"    source={evt.detail.get('source')}")
        print(f"    n_affected={evt.detail.get('n_affected')}")

    c1_pass = weakened and expected_ingested and event_logged
    print(f"\n  C1: {'PASS' if c1_pass else 'FAIL'}")

    # ------------------------------------------------------------------
    # Test 2: Repeated correction produces drift
    # ------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("  TEST 2: Repeated correction → drift toward expected")
    print(f"{'='*70}")

    moon_strengths = [moon_after]
    for rep in range(3):
        g.apply_teacher_correction(
            original_input="what do you see",
            her_emission="are are are",
            correct=False,
            expected_response="the moon",
            source="joe",
        )
        ms = get_binding_strength(g, "moon")
        moon_strengths.append(ms)
        print(f"  Rep {rep+1}: moon strength={ms:.3f}")

    # Moon should be getting stronger (or at least not weaker)
    drift_detected = moon_strengths[-1] > moon_strengths[0]
    print(f"  Moon strength trace: {[f'{s:.3f}' for s in moon_strengths]}")
    print(f"  Drift detected: {drift_detected}")

    c2_pass = drift_detected
    print(f"\n  C2: {'PASS' if c2_pass else 'FAIL'}")

    # ------------------------------------------------------------------
    # Test 3: Thumbs-up reinforcement
    # ------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("  TEST 3: Thumbs-up reinforces emission bindings")
    print(f"{'='*70}")

    love_before = get_binding_strength(g, "love")
    g._substrate_events.clear()
    result = g.apply_teacher_correction(
        original_input="i love you",
        her_emission="love you",
        correct=True,
        source="joe",
    )
    love_after = get_binding_strength(g, "love")
    print(f"  Before: 'love' strength={love_before:.3f}")
    print(f"  After:  'love' strength={love_after:.3f}")
    print(f"  Reinforced: {love_after >= love_before}")

    # Check event log
    correction_events = [evt for evt in g._substrate_events
                         if hasattr(evt, 'kind') and evt.kind == "teacher_correction"]
    c3_logged = len(correction_events) > 0
    if correction_events:
        evt = correction_events[0]
        print(f"  Event: correct={evt.detail.get('correct')}, n_affected={evt.detail.get('n_affected')}")

    c3_pass = love_after >= love_before and c3_logged
    print(f"\n  C3: {'PASS' if c3_pass else 'FAIL'}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    overall = c1_pass and c2_pass and c3_pass
    print(f"\n{'='*70}")
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")
    print(f"  C1 (atlas changes):    {'PASS' if c1_pass else 'FAIL'}")
    print(f"  C2 (drift):            {'PASS' if c2_pass else 'FAIL'}")
    print(f"  C3 (thumbs-up + log):  {'PASS' if c3_pass else 'FAIL'}")
    print(f"{'='*70}")
    return overall


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
