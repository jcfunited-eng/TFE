"""
Phase 8 verification: GL-CMD-RICH-SENSORY-WIRING-EVE-20260618-10

A/B/C test:
  A: EMISSION_DYNAMICS=0 (current grandurun path)
  B: EMISSION_DYNAMICS=1, RICH_SENSORY_INPUT=0 (brief-06 dynamics)
  C: EMISSION_DYNAMICS=1, RICH_SENSORY_INPUT=1 (this brief)

Success criteria for C:
  1. >=3/5 inputs: content-word activations dominate (no "are" flooding)
  2. Cross-modal candidates from >=2 sections on content-rich inputs
  3. "tell me about the ocean" shows ocean-related cross-modal binding
  4. Latency < 200ms Stage 1 + Stage 2 combined
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

    # Richer corpus with explicit cross-modal bindings
    corpus = [
        ("love",    "verb",     0.9, 0.9, 0.3, "joe_voice", ["speech_heard:love"]),
        ("heart",   "subject",  0.8, 0.8, 0.2, "joe_voice", ["speech_heard:heart"]),
        ("warm",    "modifier", 0.7, 0.7, 0.1, "joe_voice", []),
        ("fire",    "object",   0.9, 0.3, 0.7, "corpus",    []),
        ("bright",  "modifier", 0.6, 0.6, 0.2, "sight",     ["visual_recognition:bright"]),
        ("ocean",   "object",   0.5, 0.4, 0.6, "corpus",    ["visual_recognition:ocean_picture"]),
        ("wave",    "subject",  0.6, 0.3, 0.5, "corpus",    ["audio_heard:wave_sound"]),
        ("deep",    "modifier", 0.4, 0.2, 0.7, "corpus",    []),
        ("blue",    "modifier", 0.3, 0.5, 0.2, "sight",     ["visual_recognition:blue"]),
        ("salt",    "object",   0.3, 0.1, 0.3, "corpus",    ["taste:salt"]),
        ("shore",   "subject",  0.4, 0.5, 0.2, "corpus",    ["visual_recognition:shore"]),
        ("tide",    "subject",  0.5, 0.3, 0.4, "corpus",    []),
        ("sing",    "verb",     0.8, 0.7, 0.8, "joe_voice", ["speech_heard:sing"]),
        ("melody",  "object",   0.7, 0.8, 0.7, "corpus",    ["audio_heard:melody_sound"]),
        ("rhythm",  "subject",  0.6, 0.5, 0.6, "corpus",    []),
        ("voice",   "subject",  0.7, 0.6, 0.4, "joe_voice", ["speech_heard:voice", "audio_heard:voice_sound"]),
        ("dance",   "verb",     0.9, 0.8, 0.5, "corpus",    []),
        ("song",    "object",   0.8, 0.7, 0.6, "joe_voice", ["speech_heard:song", "audio_heard:song_sound"]),
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
        ("water",   "object",   0.4, 0.3, 0.3, "corpus",    ["visual_recognition:water"]),
        ("sun",     "subject",  0.5, 0.7, 0.3, "sight",     ["visual_recognition:sun"]),
        ("moon",    "object",   0.4, 0.5, 0.5, "corpus",    ["visual_recognition:moon"]),
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


def run_config(g, label, dynamics_flag, rich_flag):
    os.environ["EMISSION_DYNAMICS"] = str(dynamics_flag)
    os.environ["RICH_SENSORY_INPUT"] = str(rich_flag)

    # Reset emission system for clean test
    g._emission_system = None
    g._emission_token_vec = {}
    g._emission_word_map = {}
    g._emission_drive_tracker = {}

    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  EMISSION_DYNAMICS={dynamics_flag}  RICH_SENSORY_INPUT={rich_flag}")
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
            for key in ("n_candidates", "n_commits", "per_section_dominant",
                        "stage1_ms", "stage2_ms", "rich_sensory",
                        "section_candidate_counts", "origin_counts",
                        "source_counts"):
                if key in event_data:
                    print(f"    {key}: {event_data[key]}")

    return results


def evaluate_abc(a_results, b_results, c_results):
    print(f"\n{'='*70}")
    print("  PHASE 8 EVALUATION (A/B/C)")
    print(f"{'='*70}")

    # C1: Content-word activations dominate (no "are" flooding)
    # Check that >=3/5 inputs don't have "are" as an emission word
    content_dominant_count = 0
    for text, res in c_results.items():
        emission = res.get("emission", "...")
        words = emission.split() if emission else []
        function_words = {"a", "an", "the", "is", "are", "am", "was", "were",
                          "of", "in", "on", "at", "to", "from", "with", "for",
                          "and", "or", "but", "me", "you", "i", "we", "they"}
        content_count = sum(1 for w in words if w.lower() not in function_words)
        func_count = sum(1 for w in words if w.lower() in function_words)
        if content_count > func_count:
            content_dominant_count += 1
    c1_pass = content_dominant_count >= 3
    print(f"\n  C1 (content > function words): {content_dominant_count}/5 -> {'PASS' if c1_pass else 'FAIL'}")

    # C2: Cross-modal candidates from >=2 sections on content-rich inputs
    content_inputs = ["tell me about the ocean", "sing me a song", "what do you see"]
    c2_pass = False
    for text in content_inputs:
        scc = c_results.get(text, {}).get("event_data", {}).get("section_candidate_counts", {})
        if len(scc) >= 2:
            c2_pass = True
            print(f"\n  C2 (cross-modal >=2 sections): '{text[:30]}' -> sections: {scc}")
            break
    if not c2_pass:
        print(f"\n  C2 (cross-modal >=2 sections): FAIL")
    print(f"  C2: {'PASS' if c2_pass else 'FAIL'}")

    # C3: "tell me about the ocean" shows ocean-related binding
    ocean_text = "tell me about the ocean"
    ocean_res = c_results.get(ocean_text, {})
    ocean_emission = ocean_res.get("emission", "...")
    ocean_related = {"ocean", "wave", "shore", "tide", "salt", "water", "deep", "blue", "sea"}
    ocean_words_found = [w for w in ocean_emission.split() if w.lower() in ocean_related]
    c3_pass = len(ocean_words_found) > 0
    print(f"\n  C3 (ocean-related in emission): '{ocean_emission}' -> found: {ocean_words_found}")
    print(f"  C3: {'PASS' if c3_pass else 'FAIL'}")

    # C4: Latency < 200ms Stage1 + Stage2
    c4_pass = True
    for text, res in c_results.items():
        s1 = res["event_data"].get("stage1_ms", 0)
        s2 = res["event_data"].get("stage2_ms", 0)
        total = s1 + s2
        if total > 200:
            c4_pass = False
            print(f"\n  C4 latency: {total:.1f}ms > 200ms on '{text[:30]}'")
    if c4_pass:
        print(f"\n  C4 (latency < 200ms): PASS")
    print(f"  C4: {'PASS' if c4_pass else 'FAIL'}")

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
        print(f"    A (grandurun):      {ea}")
        print(f"    B (dynamics only):  {eb}")
        print(f"    C (rich sensory):   {ec}")
        scc = c_results.get(text, {}).get("event_data", {}).get("section_candidate_counts", {})
        oc = c_results.get(text, {}).get("event_data", {}).get("origin_counts", {})
        sc = c_results.get(text, {}).get("event_data", {}).get("source_counts", {})
        if scc:
            print(f"      sections: {scc}  origins: {oc}  sources: {sc}")

    overall = c1_pass and c2_pass and c3_pass and c4_pass
    print(f"\n  {'='*40}")
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")
    print(f"  C1 (content dominance): {'PASS' if c1_pass else 'FAIL'}")
    print(f"  C2 (cross-modal >=2):   {'PASS' if c2_pass else 'FAIL'}")
    print(f"  C3 (ocean-related):     {'PASS' if c3_pass else 'FAIL'}")
    print(f"  C4 (latency < 200ms):   {'PASS' if c4_pass else 'FAIL'}")
    print(f"  {'='*40}")
    return overall


def main():
    print("GL-CMD-RICH-SENSORY-WIRING Phase 8 A/B/C Verification")
    print("=" * 70)

    g = build_seeded_engine()

    # A: current grandurun path
    a_results = run_config(g, "CONFIG A: Grandurun (current)", 0, 0)

    # B: dynamics without rich sensory
    b_results = run_config(g, "CONFIG B: Dynamics, no rich sensory", 1, 0)

    # C: dynamics with rich sensory
    c_results = run_config(g, "CONFIG C: Dynamics + rich sensory", 1, 1)

    return evaluate_abc(a_results, b_results, c_results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
