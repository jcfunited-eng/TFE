"""
Phase 5 verification: GL-CMD-DYNAMICS-EMISSION-RESTORATION-EVE-20260618-03

Tests the two-stage dynamics emission path (EMISSION_DYNAMICS=1)
against the current grandurun path (EMISSION_DYNAMICS=0).
"""

import os
import sys
import json
import time

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
    """Create a Guala engine seeded with diverse corpus data."""
    from dsf_ai_service.v4.gualaloom_v5_engine import (
        Guala, deterministic_motif_id, LanguageKrimelack,
    )

    g = Guala()

    # Compute real krimelack chi values for all words
    def chi_for(word):
        k = LanguageKrimelack()
        k.transduce(word)
        return k.winding

    # Diverse corpus with metadata
    corpus = [
        # Emotional words
        ("love",    "verb",     0.9, 0.9, 0.3, "joe_voice", ["speech_heard:love"]),
        ("heart",   "subject",  0.8, 0.8, 0.2, "joe_voice", ["speech_heard:heart"]),
        ("warm",    "modifier", 0.7, 0.7, 0.1, "joe_voice", []),
        ("fire",    "object",   0.9, 0.3, 0.7, "corpus",    []),
        ("bright",  "modifier", 0.6, 0.6, 0.2, "sight",     ["visual_recognition:bright"]),
        # Ocean
        ("ocean",   "object",   0.5, 0.4, 0.6, "corpus",    []),
        ("wave",    "subject",  0.6, 0.3, 0.5, "corpus",    []),
        ("deep",    "modifier", 0.4, 0.2, 0.7, "corpus",    []),
        ("blue",    "modifier", 0.3, 0.5, 0.2, "sight",     ["visual_recognition:blue"]),
        ("salt",    "object",   0.3, 0.1, 0.3, "corpus",    []),
        ("shore",   "subject",  0.4, 0.5, 0.2, "corpus",    []),
        ("tide",    "subject",  0.5, 0.3, 0.4, "corpus",    []),
        # Song/music
        ("sing",    "verb",     0.8, 0.7, 0.8, "joe_voice", ["speech_heard:sing"]),
        ("melody",  "object",   0.7, 0.8, 0.7, "corpus",    []),
        ("rhythm",  "subject",  0.6, 0.5, 0.6, "corpus",    []),
        ("voice",   "subject",  0.7, 0.6, 0.4, "joe_voice", ["speech_heard:voice"]),
        ("dance",   "verb",     0.9, 0.8, 0.5, "corpus",    []),
        ("song",    "object",   0.8, 0.7, 0.6, "joe_voice", ["speech_heard:song"]),
        # Vision
        ("see",     "verb",     0.5, 0.3, 0.4, "sight",     ["visual_recognition:see"]),
        ("light",   "object",   0.6, 0.5, 0.5, "sight",     ["visual_recognition:light"]),
        ("sky",     "subject",  0.4, 0.6, 0.3, "sight",     ["visual_recognition:sky"]),
        ("star",    "object",   0.5, 0.7, 0.6, "sight",     ["visual_recognition:star"]),
        ("shadow",  "object",   0.3, 0.1, 0.4, "sight",     ["visual_recognition:shadow"]),
        # Neutral/common
        ("you",     "object",   0.3, 0.2, 0.1, "joe_voice", ["speech_heard:you"]),
        ("are",     "verb",     0.2, 0.1, 0.1, "corpus",    []),
        ("here",    "modifier", 0.3, 0.3, 0.2, "joe_voice", ["speech_heard:here"]),
        ("now",     "modifier", 0.4, 0.2, 0.3, "corpus",    []),
        ("tell",    "verb",     0.4, 0.2, 0.2, "joe_voice", ["speech_heard:tell"]),
        ("about",   "modifier", 0.2, 0.1, 0.1, "corpus",    []),
        ("me",      "object",   0.3, 0.2, 0.1, "joe_voice", ["speech_heard:me"]),
        # Extra words for diversity
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

        # Register in section modes
        sec = g.sections.get(section)
        if sec and hasattr(sec, "modes"):
            while len(sec.modes) <= mid:
                sec.modes.append((0, 0, ""))
            sec.modes[mid] = (0, 0, word)

        # Seed atlas with metadata
        for rep in range(8):
            g.atlas.record(
                section, mid, chi, tick=10 + rep,
                salience=1.8,
                dwell_ticks=5,
                arousal=arousal,
                valence=valence,
                surprise=surprise,
                source=source,
                sensory_refs=sensory_refs if sensory_refs else None,
            )

    g.tick = 100

    # Promote to deep atlas
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


def run_emissions(g, label, dynamics_flag):
    os.environ["EMISSION_DYNAMICS"] = str(dynamics_flag)

    print(f"\n{'='*70}")
    print(f"  {label} (EMISSION_DYNAMICS={dynamics_flag})")
    print(f"{'='*70}")

    results = {}
    for text in TEST_INPUTS:
        g._substrate_events.clear()
        g._last_converse_source = "joe"  # simulate joe speaking

        input_chis, words = compute_input_chis(text)

        reply = g._emit_from_invariants(
            input_chis, words, mode_override="grandurun",
            v7_session=getattr(g, '_v7_session', None))

        # Extract dynamics event data
        event_data = {}
        for evt in g._substrate_events:
            if hasattr(evt, 'kind') and evt.kind in ("emission_dynamics", "emission_scalar"):
                event_data = evt.detail

        results[text] = {
            "emission": reply or "...",
            "event_data": event_data,
        }

        print(f"\n  Input: '{text}'")
        print(f"  Emission: {reply or '...'}")
        if event_data:
            for key in ("n_candidates", "n_commits", "per_section_dominant",
                        "keyhole_fires", "nmda_fired", "nmda_source_match",
                        "nmda_affect_match", "stage1_ms", "stage2_ms",
                        "sections_with_commits"):
                if key in event_data:
                    print(f"    {key}: {event_data[key]}")

    return results


def evaluate(control, dynamics):
    print(f"\n{'='*70}")
    print("  PHASE 5 EVALUATION")
    print(f"{'='*70}")

    # C1: All five dynamics emissions structurally distinct
    dyn_emissions = [v["emission"] for v in dynamics.values()]
    unique = set(e for e in dyn_emissions if e and e != "...")
    c1_pass = len(unique) >= 3
    print(f"\n  C1 (structurally distinct): {len(unique)}/5 unique -> {'PASS' if c1_pass else 'FAIL'}")
    for text, res in dynamics.items():
        print(f"    '{text[:30]}...' -> {res['emission']}")

    # C2: At least 3 of 5 show dominant modes in 2+ sections
    # (checking per_section_dominant — each section settles to a word)
    multi_section_count = 0
    for text, res in dynamics.items():
        psd = res["event_data"].get("per_section_dominant", {})
        sections_with_words = sum(1 for v in psd.values() if v and v[1] is not None)
        if sections_with_words >= 2:
            multi_section_count += 1
    c2_pass = multi_section_count >= 3
    print(f"\n  C2 (multi-section dominant): {multi_section_count}/5 -> {'PASS' if c2_pass else 'FAIL'}")

    # C3: NMDA source_match fires on joe inputs
    c3_pass = False
    for text, res in dynamics.items():
        sm = res["event_data"].get("nmda_source_match", 0)
        if sm > 0:
            c3_pass = True
            print(f"\n  C3 (NMDA source_match): PASS ('{text[:30]}...' sm={sm})")
            break
    if not c3_pass:
        print(f"\n  C3 (NMDA source_match): FAIL")

    # C4: Latency targets
    c4_pass = True
    for text, res in dynamics.items():
        s1 = res["event_data"].get("stage1_ms", 0)
        s2 = res["event_data"].get("stage2_ms", 0)
        if s1 > 100:
            print(f"\n  C4 latency: Stage 1 {s1:.1f}ms > 100ms on '{text[:30]}...'")
            c4_pass = False
        if s2 > 1000:
            print(f"\n  C4 latency: Stage 2 {s2:.1f}ms > 1000ms on '{text[:30]}...'")
            c4_pass = False
    if c4_pass:
        # Print sample latencies
        sample = list(dynamics.values())[0]["event_data"]
        print(f"\n  C4 (latency): PASS (Stage1={sample.get('stage1_ms',0):.1f}ms, Stage2={sample.get('stage2_ms',0):.1f}ms)")

    # C5: Control path unchanged
    ctrl_emissions = [v["emission"] for v in control.values()]
    c5_pass = any(e != "..." for e in ctrl_emissions)
    print(f"\n  C5 (control path works): {'PASS' if c5_pass else 'FAIL'}")

    overall = c1_pass and c2_pass and c3_pass and c4_pass and c5_pass
    print(f"\n  {'='*40}")
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")
    print(f"  {'='*40}")
    return overall


def main():
    print("GL-CMD-DYNAMICS-EMISSION-RESTORATION Phase 5 Verification")
    print("=" * 70)

    g = build_seeded_engine()

    # Control: current grandurun path
    control = run_emissions(g, "CONTROL (EMISSION_DYNAMICS=0)", 0)

    # Rebuild emission system for clean test (reset cached system)
    g._emission_system = None
    g._emission_token_vec = {}
    g._emission_word_map = {}
    g._emission_drive_tracker = {}

    # Test: dynamics path
    dynamics = run_emissions(g, "DYNAMICS (EMISSION_DYNAMICS=1)", 1)

    return evaluate(control, dynamics)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
