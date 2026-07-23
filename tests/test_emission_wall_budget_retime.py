"""
test_emission_wall_budget_retime.py — local functional tests for
GL-FIX-EMISSION-BUDGET-RETIME-20260710 (root-caused in GL-RPT-SINGLE-WORD-
UNAWARE-ROOTCAUSE-C1-20260710-v1 #3a: "properly re-time" branch, NOT the
declined revert-of-2d83ca4 branch).

Tests against the REAL Guala engine (dsf_ai_service/v4/gualaloom_v5_engine.py)
and the REAL, unmodified _emit_dynamics Stage-2 settling loop that owns
EMISSION_WALL_BUDGET_S -- the exact constant that gates the keyhole cascade
(subject->verb->object->modifier->ground->intro) 2d83ca4 extended without
raising this budget. Only Stage 1 (candidate SOURCING) is stubbed, using
the same seam tonight's own test_reflection_emission_candidates.py
established (_word_to_emission_sections / organism.recall_fast stubs),
extended here to also stub the module-level _grandurun_select_candidates
directly so Stage 2 always receives a rich, real, all-six-section
candidate pool -- Stage 1's own selection logic is orthogonal to what's
under test (the settling budget itself).

Every test that needs to observe the wall-clock deadline actually bind
injects an EXPLICIT, small, synthetic per-tick delay around the real,
unmodified System.tick_once() call (never inside production code) --
this is the only way to exercise a multi-hundred-millisecond wall-clock
budget deterministically and fast in an otherwise-uncontended local test
process, where the real per-tick compute cost is ~2ms (see
GL-RPT-EMISSION-COST-C1-20260702-87-v2: live-measured median 2.175ms/tick,
p95 2.228ms/tick, same zeroed-H_base/no-inhibition config still deployed
today) -- nowhere near large enough on its own to make either 1.5s or 3.0s
bind in a fast local process. The delay stands in for real production
contention (GIL/thread contention under load), never presented as a
literal production measurement of this specific loop.

Covers:
1.  Default budget is 3.0s, not the old 1.5s -- observed behaviorally
    (env unset), not by string-matching source.
2.  A tiny explicit budget truncates the settling loop to fewer ticks
    than a large explicit budget, same candidate pool, same rng draw
    (env override mechanism still works after the retime).
3.  The new, larger default does not slow down the common, fast,
    uncontended case at all -- real production per-tick cost, no
    synthetic delay, stage2_ms stays a small fraction of the new budget
    (the higher ceiling is a ceiling, not a mandatory wait).
4.  Under a moderate synthetic contention delay, the new default (3.0s)
    reaches at least as many ticks as the old default (1.5s) would have,
    for the identical rng draw -- direct evidence the retime is monotonic
    headroom, not a behavior change in the fast path.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["EMISSION_MODE"] = "grandurun"
os.environ["EMISSION_DYNAMICS"] = "1"
os.environ["EMISSION_DYNAMICS_TICKS"] = "80"
os.environ["GRANDURUN_SPIN_VECTOR"] = "1"
os.environ["DECAY_PAUSED"] = "0"
for _unset in ("GRANDURUN_LEGACY_8D", "LATERAL_INHIBITION_ENABLED",
               "EMISSION_STRUCTURED_NOISE", "RICH_SENSORY_INPUT",
               "RECALL_BACKEND"):
    os.environ.pop(_unset, None)

import dsf_ai_service.v4.gualaloom_v5_engine as engine_mod  # noqa: E402
from dsf_ai_service.v4.gualaloom_v5_engine import Guala, LanguageKrimelack  # noqa: E402
import dsf_ai_service.substrate.assemblage as asm_mod  # noqa: E402


def _chi_for(word):
    k = LanguageKrimelack()
    k.transduce(word)
    return k.winding


# One dominant candidate + weak distractors per section -- a real, low-
# ambiguity turn, same shape as a genuine resolved utterance. Covers all
# six _EMISSION_SECTIONS so the full post-2d83ca4 cascade
# (subject->verb->object->modifier->ground->intro) has real candidates to
# settle onto at every hop.
_SECTION_WORDS = {
    "subject":  ["heart", "wave", "shore", "tide"],
    "verb":     ["love", "sing", "dance", "hold"],
    "object":   ["fire", "ocean", "melody", "song"],
    "modifier": ["warm", "bright", "deep", "blue"],
    "ground":   ["night", "morning", "home", "distance"],
    "intro":    ["well", "so", "still", "then"],
}


def _build_candidates():
    cands = []
    for sec, words in _SECTION_WORDS.items():
        for i, w in enumerate(words):
            weight = 0.85 if i == 0 else max(0.05, 0.20 - 0.02 * i)
            cands.append({
                "chi": _chi_for(w),
                "section": sec,
                "motif": f"{sec}:{w}",
                "word": w,
                "strength": weight,
                "coherent_magnitude": weight,
                "source": "joe" if i % 3 == 0 else "corpus",
                "arousal": 0.5,
                "valence": 0.3,
                "polarity": 1.0,
                "sensory_refs": [],
                "origin": "grandurun",
            })
    return cands


_BASE_CANDIDATES = _build_candidates()


def _stub_stage1(*_a, **_kw):
    return [dict(c) for c in _BASE_CANDIDATES]


def _make_engine():
    g = Guala()
    # Real committed-section-home gate (_word_to_emission_sections) is
    # bypassed via a minimal non-empty Stage-1 source, same convention
    # test_reflection_emission_candidates.py's _stub_organism_self_echo
    # uses -- isolates Stage 2 (the settling loop under test) from Stage
    # 1's own, separately-validated selection logic.
    g._brain_emission_candidates = lambda input_words: [({}, {}, 1.0)]
    return g


def _run_trial(g, wall_budget_s, per_tick_delay_s=0.0):
    os.environ["EMISSION_WALL_BUDGET_S"] = str(wall_budget_s)
    engine_mod._grandurun_select_candidates = _stub_stage1

    tick_counter = {"n": 0}
    orig_tick_once = asm_mod.System.tick_once

    def _counting(self_, *a, **kw):
        tick_counter["n"] += 1
        if per_tick_delay_s:
            time.sleep(per_tick_delay_s)
        return orig_tick_once(self_, *a, **kw)

    asm_mod.System.tick_once = _counting
    t0 = time.monotonic()
    try:
        reply = g._emit_from_invariants(
            [], [], mode_override="grandurun").content or None
    finally:
        asm_mod.System.tick_once = orig_tick_once
    wall_ms = (time.monotonic() - t0) * 1000

    ev = {}
    for evt in g._substrate_events:
        if hasattr(evt, "kind") and evt.kind == "emission_dynamics":
            ev = evt.detail
    g._substrate_events.clear()

    return {
        "reply": reply,
        "n_commits": ev.get("n_commits", 0),
        "committed_sections": ev.get("committed_sections", []),
        "stage2_ms": ev.get("stage2_ms", 0.0),
        "ticks_run": tick_counter["n"],
        "wall_ms": wall_ms,
    }


def test_1_default_budget_is_3s_not_1point5s():
    print("Test 1: default EMISSION_WALL_BUDGET_S is 3.0s (env unset), "
          "not the old 1.5s -- observed behaviorally...")
    os.environ.pop("EMISSION_WALL_BUDGET_S", None)
    g = _make_engine()
    engine_mod._grandurun_select_candidates = _stub_stage1

    # 150ms/tick: this candidate pool's natural (no_new_streak) exit point
    # sits right around tick 11 (empirically calibrated). At 150ms/tick the
    # OLD 1.5s budget deterministically truncates at exactly 10 ticks
    # (10 * 150ms = 1500ms, the deadline check fires before tick 11 can
    # start); the NEW 3.0s budget/default has enough room for the natural
    # ~11-tick exit to happen on its own instead of being cut off by the
    # deadline. This is a real, reproducible (fixed-seed rng) difference,
    # not a timing-flake -- verified directly against this exact candidate
    # pool before asserting.
    tick_counter = {"n": 0}
    orig_tick_once = asm_mod.System.tick_once

    def _counting(self_, *a, **kw):
        tick_counter["n"] += 1
        time.sleep(0.150)
        return orig_tick_once(self_, *a, **kw)

    asm_mod.System.tick_once = _counting
    try:
        os.environ.pop("EMISSION_WALL_BUDGET_S", None)  # exercise the code default
        t0 = time.monotonic()
        reply = g._emit_from_invariants(
            [], [], mode_override="grandurun").content or None
        wall_s = time.monotonic() - t0
    finally:
        asm_mod.System.tick_once = orig_tick_once

    print(f"  default budget: ticks_run={tick_counter['n']} wall_s={wall_s:.2f} reply={reply!r}")
    # Old 1.5s budget deterministically caps this exact scenario at 10
    # ticks (see module docstring test-design note above) -- the default
    # must reach strictly more than that to prove it's really 3.0s now.
    assert tick_counter["n"] > 10, (
        f"only {tick_counter['n']} ticks ran under the default budget at "
        f"150ms/tick -- matches the OLD 1.5s default's hard 10-tick cap, "
        f"not the retimed 3.0s one")
    assert wall_s < 3.3, f"default budget run took {wall_s:.2f}s, over the 3.0s ceiling + slack"
    print("  OK")


def test_2_explicit_budget_still_overridable_and_causal():
    print("Test 2: tiny explicit budget truncates ticks vs a large one, "
          "same candidate pool/rng draw (env override still works)...")
    g_small = _make_engine()
    g_large = _make_engine()  # fresh engine -> identical fixed-seed rng stream
    r_small = _run_trial(g_small, wall_budget_s=0.25, per_tick_delay_s=0.090)
    r_large = _run_trial(g_large, wall_budget_s=3.0, per_tick_delay_s=0.090)
    print(f"  budget=0.25s: ticks_run={r_small['ticks_run']}")
    print(f"  budget=3.0s:  ticks_run={r_large['ticks_run']}")
    assert r_small["ticks_run"] < r_large["ticks_run"], (
        f"small budget ({r_small['ticks_run']} ticks) did not truncate relative "
        f"to large budget ({r_large['ticks_run']} ticks) -- env override broken")
    assert r_small["ticks_run"] <= 4, (
        f"budget=0.25s at 90ms/tick should cut off within ~2-3 ticks, "
        f"got {r_small['ticks_run']}")
    print("  OK")


def test_3_new_default_does_not_slow_down_fast_uncontended_path():
    print("Test 3: new (larger) default budget does not change behavior on "
          "the common fast/uncontended path -- it's a ceiling, not a wait...")
    os.environ.pop("EMISSION_WALL_BUDGET_S", None)
    g = _make_engine()
    r = _run_trial(g, wall_budget_s=3.0, per_tick_delay_s=0.0)  # real per-tick cost, no injected delay
    print(f"  ticks_run={r['ticks_run']} stage2_ms={r['stage2_ms']:.1f} "
          f"wall_ms={r['wall_ms']:.1f} n_commits={r['n_commits']} reply={r['reply']!r}")
    assert r["n_commits"] > 0, "sharp/low-ambiguity candidate pool should commit for real"
    # Real per-tick cost is ~2ms (GL-RPT-EMISSION-COST-C1-20260702-87-v2); a
    # natural exit (no_new_streak or tick cap) should land the whole call
    # in well under a second even against the new 3.0s ceiling -- the
    # ceiling only matters when something is actually slow.
    assert r["wall_ms"] < 1000, (
        f"fast/uncontended path took {r['wall_ms']:.1f}ms -- the higher "
        f"default budget should not have changed common-case latency")
    print("  OK")


def test_4_default_reaches_at_least_as_many_ticks_as_old_default_would_have():
    print("Test 4: under moderate synthetic contention, the new default "
          "(env unset -> 3.0s) reaches >= ticks than the OLD 1.5s default "
          "would have, same rng draw...")
    g_old = _make_engine()
    g_new = _make_engine()
    r_old = _run_trial(g_old, wall_budget_s=1.5, per_tick_delay_s=0.060)
    os.environ.pop("EMISSION_WALL_BUDGET_S", None)
    r_new_default_ticks = {"n": 0}
    orig_tick_once = asm_mod.System.tick_once

    def _counting(self_, *a, **kw):
        r_new_default_ticks["n"] += 1
        time.sleep(0.060)
        return orig_tick_once(self_, *a, **kw)

    asm_mod.System.tick_once = _counting
    engine_mod._grandurun_select_candidates = _stub_stage1
    try:
        os.environ.pop("EMISSION_WALL_BUDGET_S", None)
        g_new._emit_from_invariants([], [], mode_override="grandurun")
    finally:
        asm_mod.System.tick_once = orig_tick_once
    g_new._substrate_events.clear()

    print(f"  old (1.5s) ticks_run={r_old['ticks_run']}  "
          f"new default ticks_run={r_new_default_ticks['n']}")
    assert r_new_default_ticks["n"] >= r_old["ticks_run"], (
        "retimed default reached fewer ticks than the old 1.5s budget would "
        "have under the same contention -- this should never regress")
    print("  OK")


if __name__ == "__main__":
    tests = [
        test_1_default_budget_is_3s_not_1point5s,
        test_2_explicit_budget_still_overridable_and_causal,
        test_3_new_default_does_not_slow_down_fast_uncontended_path,
        test_4_default_reaches_at_least_as_many_ticks_as_old_default_would_have,
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
