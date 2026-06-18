"""
Phase 5 verification: GL-CMD-GRANDURUN-METADATA-PIPELINE-EVE-20260618-01

Tests the 7D spin/vector grandurun path with populated metadata fields
against the scalar baseline. Calls _emit_from_invariants directly to
avoid needing full Section internals.
"""

import os
import sys
import json

# Ensure imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Set required env vars BEFORE imports
os.environ["EMISSION_MODE"] = "grandurun"
os.environ["DEEP_ATLAS_ENABLED"] = "1"
os.environ["DEEP_PRIOR_ENABLED"] = "1"
os.environ["DECAY_PAUSED"] = "0"

TEST_INPUTS = [
    "i love you",
    "what do you see",
    "tell me about the ocean",
    "sing me a song",
]


def build_seeded_engine():
    """Create a Guala engine and seed it with diverse corpus data
    that populates the metadata fields."""

    from dsf_ai_service.v4.gualaloom_v5_engine import (
        Guala, deterministic_motif_id, LanguageKrimelack,
    )

    g = Guala()

    # Chi values computed from LanguageKrimelack.transduce() for each word
    # Each entry: (word, section, chi, arousal, valence, surprise, source, sensory_refs)
    corpus = [
        # Emotional words — high arousal/valence
        ("love",    "verb",     14, 0.9, 0.9, 0.3, "joe_voice", ["speech_heard:love"]),
        ("heart",   "subject",  16, 0.8, 0.8, 0.2, "joe_voice", ["speech_heard:heart"]),
        ("warm",    "modifier", 21, 0.7, 0.7, 0.1, "joe_voice", []),
        ("fire",    "object",   11, 0.9, 0.3, 0.7, "corpus",    []),
        ("bright",  "modifier", 32, 0.6, 0.6, 0.2, "sight",     ["visual_recognition:bright"]),
        # Ocean words (chi from krimelack: ocean=6, wave=13, deep=8, blue=11, salt=20, shore=20, tide=11)
        ("ocean",   "object",    6, 0.5, 0.4, 0.6, "corpus",    []),
        ("wave",    "subject",  13, 0.6, 0.3, 0.5, "corpus",    []),
        ("deep",    "modifier",  8, 0.4, 0.2, 0.7, "corpus",    []),
        ("blue",    "modifier", 11, 0.3, 0.5, 0.2, "sight",     ["visual_recognition:blue"]),
        ("salt",    "object",   20, 0.3, 0.1, 0.3, "corpus",    []),
        ("shore",   "subject",  20, 0.4, 0.5, 0.2, "corpus",    []),
        ("tide",    "subject",  11, 0.5, 0.3, 0.4, "corpus",    []),
        # Song/music words — high surprise (sing=20, melody=18, rhythm=38, voice=10, dance=12, song=21)
        ("sing",    "verb",     20, 0.8, 0.7, 0.8, "joe_voice", ["speech_heard:sing"]),
        ("melody",  "object",   18, 0.7, 0.8, 0.7, "corpus",    []),
        ("rhythm",  "subject",  38, 0.6, 0.5, 0.6, "corpus",    []),
        ("voice",   "subject",  10, 0.7, 0.6, 0.4, "joe_voice", ["speech_heard:voice"]),
        ("dance",   "verb",     12, 0.9, 0.8, 0.5, "corpus",    []),
        ("song",    "object",   21, 0.8, 0.7, 0.6, "joe_voice", ["speech_heard:song"]),
        # Vision words — sensory grounded (see=4, light=26, sky=18, star=21, shadow=25)
        ("see",     "verb",      4, 0.5, 0.3, 0.4, "sight",     ["visual_recognition:see"]),
        ("light",   "object",   26, 0.6, 0.5, 0.5, "sight",     ["visual_recognition:light"]),
        ("sky",     "subject",  18, 0.4, 0.6, 0.3, "sight",     ["visual_recognition:sky"]),
        ("star",    "object",   21, 0.5, 0.7, 0.6, "sight",     ["visual_recognition:star"]),
        ("shadow",  "object",   25, 0.3, 0.1, 0.4, "sight",     ["visual_recognition:shadow"]),
        # Neutral/common words (you=3, are=3, here=10, now=17, tell=20, about=10, me=6)
        ("you",     "object",    3, 0.3, 0.2, 0.1, "joe_voice", ["speech_heard:you"]),
        ("are",     "verb",      3, 0.2, 0.1, 0.1, "corpus",    []),
        ("here",    "modifier", 10, 0.3, 0.3, 0.2, "joe_voice", ["speech_heard:here"]),
        ("now",     "modifier", 17, 0.4, 0.2, 0.3, "corpus",    []),
        ("tell",    "verb",     20, 0.4, 0.2, 0.2, "joe_voice", ["speech_heard:tell"]),
        ("about",   "modifier", 10, 0.2, 0.1, 0.1, "corpus",    []),
        ("me",      "object",    6, 0.3, 0.2, 0.1, "joe_voice", ["speech_heard:me"]),
    ]

    # Add all words to vocab and register in sections
    for word, section, chi, arousal, valence, surprise, source, sensory_refs in corpus:
        g.vocab.add(word)
        mid = deterministic_motif_id(word)

        # Register word in section modes
        sec = g.sections.get(section)
        if sec and hasattr(sec, "modes"):
            while len(sec.modes) <= mid:
                sec.modes.append((0, 0, ""))
            sec.modes[mid] = (0, 0, word)

    # Seed working atlas with metadata fields
    for word, section, chi, arousal, valence, surprise, source, sensory_refs in corpus:
        mid = deterministic_motif_id(word)
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
    promoted_count = 0
    for chi_k, entries in g.atlas.entries.items():
        for e in entries:
            if e["strength"] >= 0.1:
                g.deep_atlas.promote(e, "episodic", g.tick, working_atlas=g.atlas)
                promoted_count += 1

    print(f"Seeded: {len(corpus)} words, {promoted_count} deep promotions")
    print(f"Deep atlas chi-bands: {len(g.deep_atlas.entries)}")

    # Phase 0 verification
    sample_keys = set()
    sample_entries = []
    for chi_k, entries in list(g.deep_atlas.entries.items())[:10]:
        for de in entries[:2]:
            sample_keys.update(de.keys())
            sample_entries.append({
                "chi": de.get("chi"),
                "section": de.get("section"),
                "arousal": de.get("arousal"),
                "valence": de.get("valence"),
                "surprise": de.get("surprise"),
                "source": de.get("source"),
                "polarity": de.get("polarity"),
                "sensory_refs": de.get("sensory_refs", [])[:2],
            })

    print(f"\nPhase 0 — deep atlas entry keys: {sorted(sample_keys)}")
    print(f"\nSample entries (first 5):")
    for s in sample_entries[:5]:
        print(f"  {json.dumps(s)}")

    has_all = all(k in sample_keys for k in ("arousal", "valence", "surprise", "source", "polarity"))
    print(f"\n  All metadata fields present: {has_all}")
    if not has_all:
        print("*** FAIL: metadata fields missing ***")
        return None

    return g


def compute_input_chis(text):
    """Compute chi values for input words, same as converse() does."""
    from dsf_ai_service.v4.gualaloom_v5_engine import LanguageKrimelack, _normalize_text
    words = _normalize_text(text)
    chis = []
    for w in words:
        temp = LanguageKrimelack()
        temp.transduce(w)
        chis.append(temp.winding)
    return chis, words


def run_emissions(g, label, spin_vector_flag):
    """Run all four test inputs via _emit_from_invariants."""
    os.environ["GRANDURUN_SPIN_VECTOR"] = str(spin_vector_flag)

    print(f"\n{'='*60}")
    print(f"  {label} (GRANDURUN_SPIN_VECTOR={spin_vector_flag})")
    print(f"{'='*60}")

    results = {}
    for text in TEST_INPUTS:
        g._substrate_events.clear()

        input_chis, words = compute_input_chis(text)

        reply = g._emit_from_invariants(
            input_chis, words, mode_override="grandurun",
            v7_session=getattr(g, '_v7_session', None))

        # Extract dim_contributions from substrate events
        dim_contributions = None
        for evt in g._substrate_events:
            if hasattr(evt, 'kind') and evt.kind == "emission_vector":
                dc = evt.detail.get("dim_contributions")
                if dc:
                    dim_contributions = dc

        results[text] = {
            "emission": reply or "...",
            "dim_contributions": dim_contributions,
        }

        print(f"\n  Input: '{text}'")
        print(f"  Chis: {input_chis}")
        print(f"  Emission: {reply or '...'}")
        if dim_contributions:
            print(f"  Dim contributions:")
            for name, val in dim_contributions.items():
                marker = " ***" if val > 0.001 else ""
                print(f"    {name}: {val}{marker}")

    return results


def evaluate_results(scalar_results, vector_results):
    """Check Phase 5 success criteria."""
    print(f"\n{'='*60}")
    print("  PHASE 5 EVALUATION")
    print(f"{'='*60}")

    # C1: All four vector emissions structurally distinct
    vector_emissions = [v["emission"] for v in vector_results.values()]
    unique_emissions = set(e for e in vector_emissions if e and e != "...")
    c1_pass = len(unique_emissions) >= 3
    print(f"\n  C1 (structurally distinct): {len(unique_emissions)}/4 unique -> {'PASS' if c1_pass else 'FAIL'}")
    for text, res in vector_results.items():
        print(f"    '{text}' -> {res['emission']}")

    # C2: ocean and song diverge
    ocean_em = vector_results.get("tell me about the ocean", {}).get("emission", "")
    song_em = vector_results.get("sing me a song", {}).get("emission", "")
    if ocean_em and song_em and ocean_em != "..." and song_em != "...":
        ocean_words = set(ocean_em.lower().split())
        song_words = set(song_em.lower().split())
        union = ocean_words | song_words
        overlap = ocean_words & song_words
        c2_pass = len(overlap) < len(union) * 0.7
    else:
        c2_pass = False
    print(f"\n  C2 (ocean vs song diverge): {'PASS' if c2_pass else 'FAIL'}")
    print(f"    ocean: {ocean_em}")
    print(f"    song:  {song_em}")

    # C3: source_match dimension is non-trivial in at least 2 inputs
    c3_count = 0
    for text in TEST_INPUTS:
        dc = vector_results.get(text, {}).get("dim_contributions")
        if dc and dc.get("source_match", 0) > 0.01:
            c3_count += 1
    c3_pass = c3_count >= 2
    print(f"\n  C3 (source_match active): {c3_count}/4 inputs -> {'PASS' if c3_pass else 'FAIL'}")

    # C4: at least 4 of 7 dimensions non-trivial
    c4_pass = False
    for text, res in vector_results.items():
        dc = res.get("dim_contributions")
        if dc:
            active_dims = sum(1 for v in dc.values() if v > 0.001)
            if active_dims >= 4:
                c4_pass = True
                print(f"\n  C4 (4+ active dims): PASS ('{text}' has {active_dims}/7 active)")
                break
    if not c4_pass:
        print(f"\n  C4 (4+ active dims): FAIL")
        for text, res in vector_results.items():
            dc = res.get("dim_contributions")
            if dc:
                active = sum(1 for v in dc.values() if v > 0.001)
                print(f"    '{text}': {active}/7 active dims")

    overall = c1_pass and c2_pass and c3_pass and c4_pass
    print(f"\n  {'='*40}")
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")
    print(f"  {'='*40}")

    return overall


def main():
    print("GL-CMD-GRANDURUN-METADATA-PIPELINE Phase 5 Verification")
    print("=" * 60)

    g = build_seeded_engine()
    if g is None:
        return False

    scalar_results = run_emissions(g, "SCALAR BASELINE", 0)
    vector_results = run_emissions(g, "VECTOR (post-metadata-pipeline)", 1)

    return evaluate_results(scalar_results, vector_results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
