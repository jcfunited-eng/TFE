"""
Phase 3 verification: GL-CMD-LATERAL-INHIBITION-EVE-20260618-04

A/B/C test:
  A: EMISSION_DYNAMICS=0 (current grandurun path)
  B: EMISSION_DYNAMICS=1, LATERAL_INHIBITION_ENABLED=0 (brief-03, no inhibition)
  C: EMISSION_DYNAMICS=1, LATERAL_INHIBITION_ENABLED=1 (this brief)
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["EMISSION_MODE"] = "grandurun"
os.environ["DEEP_ATLAS_ENABLED"] = "1"
os.environ["DEEP_PRIOR_ENABLED"] = "1"
os.environ["DECAY_PAUSED"] = "0"
os.environ["GRANDURUN_LEGACY_8D"] = "0"
os.environ["GRANDURUN_SPIN_VECTOR"] = "0"

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


def run_config(g, label, dynamics_flag, inhibition_flag):
    os.environ["EMISSION_DYNAMICS"] = str(dynamics_flag)
    os.environ["LATERAL_INHIBITION_ENABLED"] = str(inhibition_flag)

    # Reset emission system for clean test
    g._emission_system = None
    g._emission_token_vec = {}
    g._emission_word_map = {}
    g._emission_drive_tracker = {}

    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  EMISSION_DYNAMICS={dynamics_flag}  LATERAL_INHIBITION_ENABLED={inhibition_flag}")
    print(f"{'='*70}")

    results = {}
    for text in TEST_INPUTS:
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

        results[text] = {"emission": reply or "...", "event_data": event_data}

        print(f"\n  Input: '{text}'")
        print(f"  Emission: {reply or '...'}")
        if event_data:
            for key in ("n_commits", "per_section_dominant", "committed_sections",
                        "stage1_ms", "stage2_ms", "keyhole_fires",
                        "nmda_fired", "nmda_source_match"):
                if key in event_data:
                    print(f"    {key}: {event_data[key]}")

    return results


def evaluate_abc(a_results, b_results, c_results):
    print(f"\n{'='*70}")
    print("  PHASE 3 EVALUATION (A/B/C)")
    print(f"{'='*70}")

    # C1: commit_check fires for at least 3 of 5 inputs (C config)
    commit_count = 0
    for text, res in c_results.items():
        psd = res["event_data"].get("per_section_dominant", {})
        has_commit = any(v[2] == "commit" for v in psd.values() if v and len(v) >= 3)
        if has_commit:
            commit_count += 1
    c1_pass = commit_count >= 3
    print(f"\n  C1 (commit_check fires): {commit_count}/5 inputs with commits -> {'PASS' if c1_pass else 'FAIL'}")

    # C2: Subject or object varies across see/ocean/song
    vary_inputs = ["what do you see", "tell me about the ocean", "sing me a song"]
    subjects = set()
    objects = set()
    for text in vary_inputs:
        psd = c_results.get(text, {}).get("event_data", {}).get("per_section_dominant", {})
        sub = psd.get("subject", (None, None, None))
        obj = psd.get("object", (None, None, None))
        if sub and sub[1]:
            subjects.add(sub[1])
        if obj and obj[1]:
            objects.add(obj[1])
    c2_pass = len(subjects) >= 2 or len(objects) >= 2
    print(f"\n  C2 (variation across see/ocean/song):")
    print(f"    subjects: {subjects}")
    print(f"    objects:  {objects}")
    print(f"    -> {'PASS' if c2_pass else 'FAIL'}")

    # C3: Stage 2 latency < 100ms
    c3_pass = True
    for text, res in c_results.items():
        s2 = res["event_data"].get("stage2_ms", 0)
        if s2 > 100:
            c3_pass = False
            print(f"\n  C3 latency: Stage 2 {s2:.1f}ms > 100ms on '{text[:30]}'")
    if c3_pass:
        sample = list(c_results.values())[0]["event_data"]
        print(f"\n  C3 (latency < 100ms): PASS (Stage2={sample.get('stage2_ms',0):.1f}ms)")

    # Summary table
    print(f"\n  {'='*60}")
    print(f"  SUMMARY TABLE")
    print(f"  {'='*60}")
    for text in TEST_INPUTS:
        short = text[:35]
        ea = a_results.get(text, {}).get("emission", "...")
        eb = b_results.get(text, {}).get("emission", "...")
        ec = c_results.get(text, {}).get("emission", "...")
        print(f"\n  '{short}'")
        print(f"    A (grandurun):    {ea}")
        print(f"    B (dyn, no inh):  {eb}")
        print(f"    C (dyn + inh):    {ec}")
        psd = c_results.get(text, {}).get("event_data", {}).get("per_section_dominant", {})
        if psd:
            for sec, val in psd.items():
                if val and len(val) >= 3:
                    print(f"      {sec}: mode={val[0]} word={val[1]} via={val[2]}")

    overall = c1_pass and c2_pass and c3_pass
    print(f"\n  {'='*40}")
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")
    print(f"  {'='*40}")
    return overall


def main():
    print("GL-CMD-LATERAL-INHIBITION Phase 3 A/B/C Verification")
    print("=" * 70)

    g = build_seeded_engine()

    # A: current grandurun path
    a_results = run_config(g, "CONFIG A: Grandurun (current)", 0, 0)

    # B: dynamics without inhibition
    b_results = run_config(g, "CONFIG B: Dynamics, no inhibition", 1, 0)

    # C: dynamics with inhibition
    c_results = run_config(g, "CONFIG C: Dynamics + lateral inhibition", 1, 1)

    return evaluate_abc(a_results, b_results, c_results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
