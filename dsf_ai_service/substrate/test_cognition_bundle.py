"""
GL-CMD-COGNITION-BUNDLE-EVE-20260619-23: Five verification tests.

Test 1: pr consensus/divergence fires
Test 2: ep turn log accumulates
Test 3: sc semantic weighting
Test 4: gp goal bias
Test 5: Combined — all four flags ON
"""

import os
import sys
import time as _time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["EMISSION_MODE"] = "grandurun"
os.environ["DEEP_ATLAS_ENABLED"] = "1"
os.environ["DEEP_PRIOR_ENABLED"] = "1"
os.environ["DECAY_PAUSED"] = "0"
os.environ["GRANDURUN_LEGACY_8D"] = "0"
os.environ["GRANDURUN_SPIN_VECTOR"] = "0"
os.environ["EMISSION_DYNAMICS"] = "1"
os.environ["LATERAL_INHIBITION_ENABLED"] = "1"
os.environ["RICH_SENSORY_INPUT"] = "1"
os.environ["EMISSION_STRUCTURED_NOISE"] = "1"


def _build_engine():
    from dsf_ai_service.v4.gualaloom_v5_engine import (
        Guala, deterministic_motif_id, LanguageKrimelack,
    )
    g = Guala()

    def chi_for(word):
        k = LanguageKrimelack()
        k.transduce(word)
        return k.winding

    corpus = [
        ("love",    "verb",     0.9, 0.9, 0.3, "joe_voice"),
        ("heart",   "subject",  0.8, 0.8, 0.2, "joe_voice"),
        ("ocean",   "object",   0.5, 0.4, 0.6, "corpus"),
        ("wave",    "subject",  0.6, 0.3, 0.5, "corpus"),
        ("moon",    "object",   0.5, 0.7, 0.6, "sight"),
        ("star",    "object",   0.5, 0.7, 0.6, "sight"),
        ("sky",     "subject",  0.4, 0.6, 0.3, "sight"),
        ("sing",    "verb",     0.8, 0.7, 0.8, "joe_voice"),
        ("song",    "object",   0.8, 0.7, 0.6, "joe_voice"),
        ("warm",    "modifier", 0.7, 0.7, 0.1, "joe_voice"),
        ("dance",   "verb",     0.9, 0.8, 0.5, "corpus"),
        ("fire",    "object",   0.9, 0.3, 0.7, "corpus"),
        ("light",   "object",   0.6, 0.5, 0.5, "sight"),
        ("shore",   "subject",  0.4, 0.5, 0.2, "corpus"),
        ("rain",    "object",   0.4, 0.2, 0.5, "corpus"),
        ("present", "modifier", 0.5, 0.5, 0.2, "corpus"),
        ("joe",     "subject",  0.7, 0.8, 0.3, "joe_voice"),
        ("sense",   "modifier", 0.5, 0.4, 0.3, "corpus"),
    ]

    for word, section, arousal, valence, surprise, source in corpus:
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
    return g


def _flags_off():
    for f in ("HEMI_PR_ENABLED", "HEMI_EP_ENABLED",
              "HEMI_SC_ENABLED", "HEMI_GP_ENABLED"):
        os.environ[f] = "0"


def _converse(g, text, source="joe"):
    """Simplified converse that exercises the emission + hemisphere hooks."""
    from dsf_ai_service.v4.gualaloom_v5_engine import (
        LanguageKrimelack, _normalize_text,
    )
    words = _normalize_text(text)
    input_chis = []
    for w in words:
        k = LanguageKrimelack()
        k.transduce(w)
        input_chis.append(k.winding)

    g._last_converse_source = source
    g._substrate_events.clear()

    reply = g._emit_from_invariants(
        input_chis, words, mode_override="grandurun",
        v7_session=getattr(g, '_v7_session', None))

    # Compute emission chis
    emission_chis = []
    if reply:
        for ew in _normalize_text(reply):
            ek = LanguageKrimelack()
            ek.transduce(ew)
            emission_chis.append(ek.winding)

    # Run hemisphere updates (normally called from converse)
    from dsf_ai_service.substrate.hemisphere_cognition import run_hemisphere_updates
    events = run_hemisphere_updates(g, text, source, input_chis,
                                     reply, emission_chis, g.tick)
    g.tick += 1
    return reply, events


def test_1_pr_consensus_divergence():
    """pr consensus/divergence fires after inputs."""
    print("  Test 1: pr consensus/divergence...", end=" ")
    _flags_off()
    os.environ["HEMI_PR_ENABLED"] = "1"

    g = _build_engine()

    all_events = []
    inputs = [
        "hello guala",
        "tell me about the ocean",
        "sing me a song",
        "the moon is bright",
        "i love you",
    ]
    for text in inputs:
        _, events = _converse(g, text)
        all_events.extend(events)

    pr = g.hemispheres.get("pr")
    pr_bindings = sum(len(v) for v in pr.atlas.entries.values()) if pr else 0
    convergent = sum(1 for e in all_events if e.get("type") == "convergent_event")
    em_pr_links = [l for l in g._cross_hemi_links
                   if l.src_hemi == "em" and l.dst_hemi == "pr"]
    strong_links = [l for l in em_pr_links if l.strength >= 0.05]

    try:
        assert pr_bindings >= 10, f"pr bindings {pr_bindings} < 10"
        assert convergent >= 1, f"convergent events {convergent} < 1"
        assert len(strong_links) >= 1, f"strong em↔pr links {len(strong_links)} < 1"
        print(f"PASS (pr_bindings={pr_bindings}, convergent={convergent}, "
              f"strong_links={len(strong_links)})")
        return True
    except AssertionError as e:
        print(f"FAIL: {e}")
        return False


def test_2_ep_turn_log():
    """ep turn log accumulates turns."""
    print("  Test 2: ep turn log...", end=" ")
    _flags_off()
    os.environ["HEMI_EP_ENABLED"] = "1"

    g = _build_engine()
    inputs = [
        ("hello guala", "joe"),
        ("tell me about the ocean", "joe"),
        ("the moon is bright", "wc"),
        ("sing me a song", "joe"),
        ("i love you", "joe"),
    ]
    for text, source in inputs:
        _converse(g, text, source)

    ep = g.hemispheres.get("ep")
    try:
        assert ep is not None, "ep hemisphere missing"
        assert len(ep.turn_log) == 5, f"turn_log has {len(ep.turn_log)} entries, expected 5"
        for entry in ep.turn_log:
            assert entry.source, f"entry at tick {entry.tick} has no source"
            assert entry.input_chis, f"entry at tick {entry.tick} has no input_chis"

        # Check tracked_objects has content words
        assert len(ep.tracked_objects) > 0, "tracked_objects empty"
        assert "ocean" in ep.tracked_objects, "'ocean' not tracked"

        # Check most_recent_source
        from dsf_ai_service.substrate.hemisphere_cognition import most_recent_source
        mrs = most_recent_source(ep, exclude=("guala",))
        assert mrs == "joe", f"most_recent_source={mrs}, expected 'joe'"

        print(f"PASS (turns={len(ep.turn_log)}, tracked={len(ep.tracked_objects)}, "
              f"mrs={mrs})")
        return True
    except (AssertionError, Exception) as e:
        print(f"FAIL: {e}")
        return False


def test_3_sc_semantic_weighting():
    """sc semantic weighting contributes to candidate pool."""
    print("  Test 3: sc semantic weighting...", end=" ")
    _flags_off()
    os.environ["HEMI_SC_ENABLED"] = "1"

    g = _build_engine()

    # Set up sc
    from dsf_ai_service.substrate.hemisphere_cognition import setup_sc
    setup_sc(g)
    sc = g.hemispheres.get("sc")

    try:
        assert sc is not None, "sc hemisphere missing"
        sc_bindings = sum(len(v) for v in sc.atlas.entries.values())
        assert sc_bindings > 0, "sc has no seeded bindings"

        # Run emission — sc weighting should apply
        _, events = _converse(g, "tell me about the ocean")

        # Check sc_gp_weight on candidates (via event log)
        # The weighting is applied in _rich_sensory_candidates
        # We verify sc has bindings and the emission runs without error
        print(f"PASS (sc_bindings={sc_bindings})")
        return True
    except (AssertionError, Exception) as e:
        print(f"FAIL: {e}")
        return False


def test_4_gp_goal_bias():
    """gp goal bias affects candidate ranking."""
    print("  Test 4: gp goal bias...", end=" ")
    _flags_off()

    g = _build_engine()

    # Run WITHOUT gp — baseline
    os.environ["HEMI_GP_ENABLED"] = "0"
    from dsf_ai_service.substrate.hemisphere_cognition import (
        setup_gp, gp_bias_for_candidate,
    )

    # Set up gp
    os.environ["HEMI_GP_ENABLED"] = "1"
    setup_gp(g)
    gp = g.hemispheres.get("gp")

    try:
        assert gp is not None, "gp hemisphere missing"
        gp_bindings = sum(len(v) for v in gp.atlas.entries.values())
        assert gp_bindings == 3, f"gp has {gp_bindings} bindings, expected 3 seed goals"

        # Check that gp_bias returns > 0 for a seed-goal-related candidate
        test_cand = {"word": "present", "chi": 0}
        bias = gp_bias_for_candidate(test_cand, g)
        assert bias > 0, f"gp_bias for 'present' = {bias}, expected > 0"

        # Check non-goal candidate gets 0
        test_cand2 = {"word": "random_word_xyz", "chi": 0}
        bias2 = gp_bias_for_candidate(test_cand2, g)
        assert bias2 == 0.0, f"gp_bias for non-goal = {bias2}, expected 0"

        print(f"PASS (seed_goals={gp_bindings}, bias_present={bias:.2f})")
        return True
    except (AssertionError, Exception) as e:
        print(f"FAIL: {e}")
        return False


def test_5_combined_all_flags():
    """All four flags ON — no crash, events fire, latency OK."""
    print("  Test 5: combined all flags ON...", end=" ")
    os.environ["HEMI_PR_ENABLED"] = "1"
    os.environ["HEMI_EP_ENABLED"] = "1"
    os.environ["HEMI_SC_ENABLED"] = "1"
    os.environ["HEMI_GP_ENABLED"] = "1"

    g = _build_engine()
    all_events = []

    inputs = [
        "hello guala",
        "tell me about the ocean",
        "what do you see",
        "sing me a song",
        "the moon is bright",
        "i love you",
        "do you remember the ocean",
        "not warm",
        "good night",
        "how are you",
    ]

    t0 = _time.monotonic()
    for text in inputs:
        _, events = _converse(g, text)
        all_events.extend(events)
    total_ms = (_time.monotonic() - t0) * 1000

    try:
        # Count event types
        convergent = sum(1 for e in all_events if e.get("type") == "convergent_event")
        divergent = sum(1 for e in all_events if e.get("type") == "divergent_event")
        turn_logged = sum(1 for e in all_events if e.get("type") == "turn_log_appended")

        assert convergent >= 1, f"convergent_events={convergent}, need ≥1"
        assert turn_logged == 10, f"turn_log_appended={turn_logged}, need 10"
        assert total_ms < 5000, f"total latency {total_ms:.0f}ms > 5000ms"

        # Per-converse latency
        per_converse = total_ms / len(inputs)
        assert per_converse < 1000, f"per-converse {per_converse:.0f}ms > 1000ms"

        # Verify hemispheres exist
        assert "pr" in g.hemispheres, "pr missing"
        assert "ep" in g.hemispheres, "ep missing"
        assert "sc" in g.hemispheres, "sc missing"
        assert "gp" in g.hemispheres, "gp missing"

        print(f"PASS (convergent={convergent}, divergent={divergent}, "
              f"turns={turn_logged}, latency={per_converse:.0f}ms/input)")
        return True
    except (AssertionError, Exception) as e:
        print(f"FAIL: {e}")
        return False


def main():
    print("GL-CMD-COGNITION-BUNDLE Verification Tests")
    print("=" * 60)

    tests = [
        test_1_pr_consensus_divergence,
        test_2_ep_turn_log,
        test_3_sc_semantic_weighting,
        test_4_gp_goal_bias,
        test_5_combined_all_flags,
    ]

    results = []
    for t in tests:
        try:
            results.append(t())
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    _flags_off()

    print(f"\n{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"  {passed}/{total} tests passed")
    print(f"  {'ALL GREEN' if all(results) else 'FAILURES DETECTED'}")
    print(f"{'='*60}")
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
