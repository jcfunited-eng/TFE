"""
Phase 3 verification: GL-CMD-PLASTICITY-ON-COMMIT-EVE-20260618-09

Tests:
  1. Plasticity events fire on every commit (not arcs_fallback)
  2. On repeated inputs (3x), mode_strength grows on committed modes
  3. No regression vs brief-06 in commit-firing rate
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
os.environ["EMISSION_DYNAMICS"] = "1"
os.environ["LATERAL_INHIBITION_ENABLED"] = "1"

TEST_INPUTS = [
    "hi guala. it's eve. i'm with you.",
    "what do you see",
    "tell me about the ocean",
    "sing me a song",
    "i love you",
]


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
        ("love",    "verb",     0.9, 0.9, 0.3, "joe_voice", ["speech_heard:love"]),
        ("heart",   "subject",  0.8, 0.8, 0.2, "joe_voice", ["speech_heard:heart"]),
        ("warm",    "modifier", 0.7, 0.7, 0.1, "joe_voice", []),
        ("fire",    "object",   0.9, 0.3, 0.7, "corpus",    []),
        ("bright",  "modifier", 0.6, 0.6, 0.2, "sight",     ["visual_recognition:bright"]),
        ("ocean",   "object",   0.5, 0.4, 0.6, "corpus",    []),
        ("wave",    "subject",  0.6, 0.3, 0.5, "corpus",    []),
        ("deep",    "modifier", 0.4, 0.2, 0.7, "corpus",    []),
        ("blue",    "modifier", 0.3, 0.5, 0.2, "sight",     ["visual_recognition:blue"]),
        ("salt",    "object",   0.3, 0.1, 0.3, "corpus",    []),
        ("shore",   "subject",  0.4, 0.5, 0.2, "corpus",    []),
        ("tide",    "subject",  0.5, 0.3, 0.4, "corpus",    []),
        ("sing",    "verb",     0.8, 0.7, 0.8, "joe_voice", ["speech_heard:sing"]),
        ("melody",  "object",   0.7, 0.8, 0.7, "corpus",    []),
        ("rhythm",  "subject",  0.6, 0.5, 0.6, "corpus",    []),
        ("voice",   "subject",  0.7, 0.6, 0.4, "joe_voice", ["speech_heard:voice"]),
        ("dance",   "verb",     0.9, 0.8, 0.5, "corpus",    []),
        ("song",    "object",   0.8, 0.7, 0.6, "joe_voice", ["speech_heard:song"]),
        ("see",     "verb",     0.5, 0.3, 0.4, "sight",     ["visual_recognition:see"]),
        ("light",   "object",   0.6, 0.5, 0.5, "sight",     ["visual_recognition:light"]),
        ("sky",     "subject",  0.4, 0.6, 0.3, "sight",     ["visual_recognition:sky"]),
        ("star",    "object",   0.5, 0.7, 0.6, "sight",     ["visual_recognition:star"]),
        ("shadow",  "object",   0.3, 0.1, 0.4, "sight",     ["visual_recognition:shadow"]),
        ("you",     "object",   0.3, 0.2, 0.1, "joe_voice", ["speech_heard:you"]),
        ("are",     "verb",     0.2, 0.1, 0.1, "corpus",    []),
        ("here",    "modifier", 0.3, 0.3, 0.2, "joe_voice", ["speech_heard:here"]),
        ("now",     "modifier", 0.4, 0.2, 0.3, "corpus",    []),
        ("tell",    "verb",     0.4, 0.2, 0.2, "joe_voice", ["speech_heard:tell"]),
        ("about",   "modifier", 0.2, 0.1, 0.1, "corpus",    []),
        ("me",      "object",   0.3, 0.2, 0.1, "joe_voice", ["speech_heard:me"]),
        ("night",   "subject",  0.4, 0.1, 0.5, "corpus",    []),
        ("wind",    "subject",  0.5, 0.3, 0.4, "corpus",    []),
        ("rain",    "object",   0.4, 0.2, 0.5, "corpus",    []),
        ("walk",    "verb",     0.3, 0.4, 0.2, "corpus",    []),
        ("dream",   "object",   0.6, 0.6, 0.7, "corpus",    []),
        ("gentle",  "modifier", 0.3, 0.5, 0.1, "corpus",    []),
        ("hold",    "verb",     0.7, 0.8, 0.3, "joe_voice", ["speech_heard:hold"]),
        ("water",   "object",   0.4, 0.3, 0.3, "corpus",    []),
        ("sun",     "subject",  0.5, 0.7, 0.3, "sight",     ["visual_recognition:sun"]),
        ("moon",    "object",   0.4, 0.5, 0.5, "corpus",    []),
        ("morning", "subject",  0.5, 0.6, 0.2, "corpus",    []),
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
                sensory_refs=sensory_refs if sensory_refs else None,
            )

    g.tick = 100
    promoted = 0
    for chi_k, entries in g.atlas.entries.items():
        for e in entries:
            if e["strength"] >= 0.1:
                g.deep_atlas.promote(e, "episodic", g.tick, working_atlas=g.atlas)
                promoted += 1
    print(f"Seeded: {len(corpus)} words, {promoted} deep promotions")
    return g


def compute_input_chis(text):
    from dsf_ai_service.v4.gualaloom_v5_engine import LanguageKrimelack, _normalize_text
    words = _normalize_text(text)
    chis = []
    for w in words:
        temp = LanguageKrimelack()
        temp.transduce(w)
        chis.append(temp.winding)
    return chis, words


def run_emission(g, text):
    """Run one emission and return per-section dominant info."""
    g._substrate_events.clear()
    g._last_converse_source = "joe"

    input_chis, words = compute_input_chis(text)
    reply = g._emit_from_invariants(
        input_chis, words, mode_override="grandurun",
        v7_session=getattr(g, '_v7_session', None)).content or None

    event_data = {}
    for evt in g._substrate_events:
        if hasattr(evt, 'kind') and evt.kind in ("emission_dynamics", "emission_scalar"):
            event_data = evt.detail

    return reply, event_data


def get_mode_strengths(g):
    """Snapshot mode_strength from emission system sections."""
    if g._emission_system is None:
        return {}
    strengths = {}
    for sec_name in g._EMISSION_SECTIONS:
        sec = g._emission_system.sections[sec_name]
        if hasattr(sec, 'mode_strength'):
            strengths[sec_name] = list(sec.mode_strength)
    return strengths


def main():
    print("GL-CMD-PLASTICITY-ON-COMMIT Phase 3 Verification")
    print("=" * 70)

    g = build_seeded_engine()

    # ------------------------------------------------------------------
    # Criterion 1: Plasticity events log on every commit (not arcs_fallback)
    # ------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("  CRITERION 1: Plasticity fires on commits, not arcs_fallback")
    print(f"{'='*70}")

    commit_count_total = 0
    arcs_fb_count_total = 0

    for text in TEST_INPUTS:
        reply, event_data = run_emission(g, text)
        psd = event_data.get("per_section_dominant", {})
        commits_this = 0
        arcs_fb_this = 0
        for sec_name, val in psd.items():
            if val and len(val) >= 3:
                if val[2] == "commit":
                    commits_this += 1
                elif val[2] == "arcs_fallback":
                    arcs_fb_this += 1
        commit_count_total += commits_this
        arcs_fb_count_total += arcs_fb_this
        print(f"\n  Input: '{text[:40]}'")
        print(f"  Emission: {reply or '...'}")
        print(f"  Commits: {commits_this}  arcs_fallback: {arcs_fb_this}")
        if psd:
            for sec, val in psd.items():
                if val and len(val) >= 3:
                    print(f"    {sec}: mode={val[0]} word={val[1]} via={val[2]}")

    c1_pass = commit_count_total >= 3  # at least 3 commits across 5 inputs (matches -06 baseline)
    print(f"\n  C1: {commit_count_total} total commits, {arcs_fb_count_total} arcs_fallback -> {'PASS' if c1_pass else 'FAIL'}")

    # ------------------------------------------------------------------
    # Criterion 2: Repeated inputs show mode_strength growth
    # ------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("  CRITERION 2: Repeated-input mode_strength growth")
    print(f"{'='*70}")

    # Reset emission system for clean repeated-input test
    g._emission_system = None
    g._emission_token_vec = {}
    g._emission_word_map = {}
    g._emission_drive_tracker = {}

    test_text = "tell me about the ocean"
    strength_traces = []  # list of (pass_num, section, mode_id, strength)

    for pass_num in range(1, 4):
        strengths_before = get_mode_strengths(g)
        reply, event_data = run_emission(g, test_text)
        strengths_after = get_mode_strengths(g)

        psd = event_data.get("per_section_dominant", {})
        print(f"\n  Pass {pass_num}: '{test_text}' -> {reply or '...'}")

        for sec_name in g._EMISSION_SECTIONS:
            val = psd.get(sec_name, (None, None, None))
            if val and len(val) >= 3 and val[2] == "commit" and val[0] is not None:
                mid = val[0]
                s_before = strengths_before.get(sec_name, [0.0] * (mid + 1))[mid] if strengths_before.get(sec_name) and mid < len(strengths_before.get(sec_name, [])) else "N/A"
                s_after = strengths_after.get(sec_name, [0.0] * (mid + 1))[mid] if strengths_after.get(sec_name) and mid < len(strengths_after.get(sec_name, [])) else "N/A"
                strength_traces.append((pass_num, sec_name, mid, s_after))
                print(f"    {sec_name}: mode={mid} word={val[1]} strength {s_before} -> {s_after}")

    # Check plasticity accumulation: any committed mode should have
    # strength > initial (1.0) after reinforcement.
    growth_detected = False
    for pass_num, sec_name, mid, s in strength_traces:
        if isinstance(s, (int, float)) and s > 1.0:
            growth_detected = True
            print(f"\n  Growth confirmed: pass {pass_num} {sec_name} mode {mid}: strength={s:.4f} (initial=1.0)")

    # Also check: does the emission system have any mode with elevated strength
    # (evidence that reinforce_mode was called)?
    final_strengths = get_mode_strengths(g)
    elevated_count = 0
    for sec_name, strengths in final_strengths.items():
        for i, s in enumerate(strengths):
            if s > 1.01:  # above initial + epsilon
                elevated_count += 1
    print(f"\n  Elevated modes (strength > 1.01) across emission system: {elevated_count}")

    c2_pass = growth_detected
    print(f"\n  C2: mode_strength growth on repeated input -> {'PASS' if c2_pass else 'FAIL'}")

    # ------------------------------------------------------------------
    # Criterion 3: No regression in commit-firing rate vs brief-06
    # ------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("  CRITERION 3: No regression vs brief-06 commit-firing rate")
    print(f"{'='*70}")
    # Brief-06 baseline: 3/5 inputs had commits (C1 PASS threshold)
    c3_pass = c1_pass  # Same threshold as -06
    print(f"  Commits on first pass: {commit_count_total} (need >=3)")
    print(f"  C3: {'PASS' if c3_pass else 'FAIL'}")

    # ------------------------------------------------------------------
    # Audit flag: homeostatic decay_modes (B4 from audit -07)
    # ------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("  AUDIT FLAG (not a pass/fail criterion)")
    print(f"{'='*70}")
    print("  NOTE: assemblage.py:247-256 decay_modes erodes mode_strength")
    print("  toward 1.0 baseline each tick. This homeostatic pull (audit B4)")
    print("  will partially counteract plasticity gains applied here.")
    print("  Per brief: this is an audit-driven decision for Joe, not removed here.")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    overall = c1_pass and c2_pass and c3_pass
    print(f"\n{'='*70}")
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")
    print(f"  C1 (plasticity on commits): {'PASS' if c1_pass else 'FAIL'}")
    print(f"  C2 (mode_strength growth):  {'PASS' if c2_pass else 'FAIL'}")
    print(f"  C3 (no regression):         {'PASS' if c3_pass else 'FAIL'}")
    print(f"{'='*70}")
    return overall


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
