#!/usr/bin/env python3
"""guala_recall_bitexact_replay.py — bit-exact offline replay of her live recall path.

Provenance: built 2026-07-03 for GL-CMD-S2A-RECALL-METHOD-C1-20260703-v1 (S2a),
promoted to project instrumentation per Eve's ruling on
GL-RPT-S2A-COLD-C1-20260703-v1 (the guala_atlas_query proxy was rejected as a
recall check — it reads chi-neighborhood proximity, not word-specific recall).

Standing rule (per that ruling): recall numbers for the ledger come ONLY from
this method — bit-exact offline replay against a save snapshot — cadence
weekly + after any recall-touching deploy.

What it does: constructs a bare `Guala()` instance and feeds it a downloaded
save snapshot (S3 backup or an EFS copy — same file set, same fidelity)
through the engine's OWN restore methods (_apply_core/_apply_atlas/
_apply_sections/_apply_visual/deep_atlas.load_from_json), rebuilds
_word_to_chi_index with the exact snippet from the engine's own boot sequence
(gualaloom_v5_engine.py, "GL-CMD-RECALL-WORD-INDEX-57 §1.4"), then calls the
real, unmodified _recall_response for each probe word — the identical code
path a live /converse turn runs. Zero perturbation of the live process: this
only ever reads a snapshot, never touches the running task.

Usage:
    python3 tools/guala_recall_bitexact_replay.py --snapshot-dir /path/to/snapshot
    python3 tools/guala_recall_bitexact_replay.py --snapshot-dir /path/to/snapshot \
        --words aap,ding,touching

The snapshot dir must contain (unwrapped-or-enveloped, either is handled):
guala_core.json, guala_atlas.json, guala_sections.json, guala_visual.json,
guala_deep_atlas.json — the same files a normal S3 backup or EFS state dir has.

Probe-set draw rule (when --words is not given): her full saved vocabulary,
alphabetic words with len>2, sorted, every (len//30)th word taken — the same
deterministic, non-cherry-picked rule declared in
GL-CMD-S2A-RECALL-METHOD-C1-20260703-v1.

Why this exists, in one paragraph (GL-CMD-157): the 6/22 population-collapse
audit proved a "100%" number can be a single-neuron ceiling replicated across
a degenerate population, not real discrimination — never trust a hit-rate
without checking what's behind it. cbe8ed2 proved a validated-in-harness
number (the "100% T5" of the -135/136/137 era) can silently diverge from
production for weeks — never inherit a number, measure it fresh, here,
against her real path. Joe's teaching-loop principle (cold ~95%, the loop
closes the residue through exposure) is why this harness measures COLD and
TAUGHT as a pair, never one alone.
"""
import argparse
import json
import os
import sys
from collections import defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# GL-CMD-157: minimal stopword filter for the coherence rule below. Kept
# small and boring on purpose — this is a filter, not a linguistics project.
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "am",
    "to", "of", "in", "on", "at", "for", "with", "and", "or", "but",
    "this", "that", "it", "its", "he", "she", "they", "we", "you", "i",
    "his", "her", "their", "our", "your", "my", "me", "him", "them",
}


def _tokens(text):
    """Lowercase, whitespace-split, stopword-filtered tokens. Empty for None."""
    if not text:
        return []
    return [t for t in text.lower().split() if t not in _STOPWORDS]


def is_coherent(returned_tokens, probe_word, caption_words):
    """GL-CMD-157 coherence rule, verbatim: a returned recall counts as
    coherent iff at least one of the returned tokens matches the probe word
    OR its bundle's caption words, non-stopword-filtered. Exact match only —
    no stemming, no fuzzy match, so this can't be quietly loosened later."""
    targets = {probe_word.lower()} | set(_tokens(caption_words))
    return bool(set(returned_tokens) & targets)


def _load(snapshot_dir, fname):
    with open(os.path.join(snapshot_dir, fname)) as f:
        raw = json.load(f)
    return raw.get("data", raw)


def build_replay_guala(snapshot_dir):
    """Construct a Guala() populated from a save snapshot via the engine's own
    restore methods. Returns the instance, ready for _recall_response calls."""
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    g = Guala()
    g._apply_core(_load(snapshot_dir, "guala_core.json"))
    g._apply_atlas(_load(snapshot_dir, "guala_atlas.json"))
    g._apply_sections(_load(snapshot_dir, "guala_sections.json"))
    g._apply_visual(_load(snapshot_dir, "guala_visual.json"), state_dir=snapshot_dir)
    g.deep_atlas.load_from_json(_load(snapshot_dir, "guala_deep_atlas.json"))

    # GL-CMD-RECALL-WORD-INDEX-57 §1.4 rebuild, verbatim from the engine's own
    # boot sequence (gualaloom_v5_engine.py, right after "[GualaLoom] Loaded:").
    g._word_to_chi_index = defaultdict(set)
    for chi_k, entries in g.atlas.entries.items():
        for e in entries:
            sec = g.sections.get(e.get("section", ""))
            if sec:
                mid = e.get("motif", 0)
                if mid < len(sec.modes):
                    _, _, w = sec.modes[mid]
                    if w:
                        g._word_to_chi_index[w.lower()].add(chi_k)
    return g


def draw_probe_words(snapshot_dir, n=30):
    """Deterministic, non-cherry-picked probe-set draw: her saved vocabulary,
    alphabetic words len>2, sorted, every (len//n)th word."""
    core = _load(snapshot_dir, "guala_core.json")
    vocab = core.get("vocab", [])
    clean = sorted(w for w in vocab if w.isalpha() and len(w) > 2)
    step = max(1, len(clean) // n)
    return clean[::step][:n]



# GL-CMD-RECALL-REACH-159 Part A: the two candidate section-surfaces, plus
# plain SVO as the unchanged-production baseline for candidate-set-size
# comparison. "svo" is not a proposed variant — it is what production does
# today, kept here so the crowding cost of L/LI has something to measure
# against.
VARIANTS = {
    "svo": ("subject", "verb", "object"),
    "L": ("subject", "verb", "object", "listen"),
    "LI": ("subject", "verb", "object", "listen", "intro"),
}


def probe(g, word, target_sections=("subject", "verb", "object")):
    """One recall probe: build input_chis/input_word_chis exactly as a live
    /converse turn does, call the real _recall_response, report hit/miss.
    Resets _last_recalled_pictures first — belt-and-suspenders now that
    GL-CMD-155 fixed the underlying leak in _recall_response itself, but kept
    here so this harness stays correct even if that regresses.
    target_sections: GL-CMD-159 Part A — forwarded verbatim to the engine's
    own _recall_response(target_sections=...) parameter; default matches
    unmodified production."""
    from dsf_ai_service.v4.gualaloom_v5_engine import _normalize_text
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack

    g._last_recalled_pictures = []
    words = _normalize_text(word)
    input_chis, input_word_chis = [], {}
    for w in words:
        tk = LanguageKrimelack()
        tk.transduce(w)
        input_chis.append(tk.winding)
        input_word_chis[w] = tk.winding
    recalled_text = g._recall_response(input_chis, input_word_chis, words,
                                        target_sections=target_sections)
    pics = getattr(g, "_last_recalled_pictures", [])
    return {
        "word": word,
        "hit": bool(recalled_text) or bool(pics),
        "recalled_text": recalled_text,
        "returned_tokens": _tokens(recalled_text),
        "n_pictures": len(pics),
    }


def word_own_chi(word):
    """The word's own chi address — identical computation to both the write
    path (gualaloom_v5_engine.py:1567, `lang_chi = self.language.winding`)
    and the read path (this file's `probe()`, and engine.py:3577-3579's
    `_chis_for_text`). No modulo, no drift — verified by direct code
    comparison for GL-CMD-158."""
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
    tk = LanguageKrimelack()
    tk.transduce(word)
    return tk.winding


def existence_trace(g, word):
    """A.1 EXISTENCE: does the taught binding exist in the snapshot?
    Vocab membership, and every atlas entry (any section) whose motif
    resolves to this exact word at this word's own chi."""
    chi = word_own_chi(word)
    wl = word.lower()
    in_vocab = wl in {v.lower() for v in g.vocab}
    own_entries = []
    for e in g.atlas.entries.get(chi, []):
        sec = g.sections.get(e.get("section", ""))
        if sec and e.get("motif", -1) < len(sec.modes):
            _, _, w = sec.modes[e["motif"]]
            if w and w.lower() == wl:
                in_deep = any(
                    de.get("section") == e.get("section")
                    and de.get("motif") == e.get("motif")
                    for de in g.deep_atlas.entries.get(chi, [])
                )
                own_entries.append({
                    "chi": chi, "section": e.get("section"),
                    "motif": e.get("motif"),
                    "strength": round(e.get("strength", -1), 4),
                    "in_deep": in_deep,
                })
    return {"word": word, "chi": chi, "in_vocab": in_vocab, "own_atlas_entries": own_entries}


def candidacy_trace(g, word, target_sections=("subject", "verb", "object")):
    """A.2 CANDIDACY: the exact _recall_from_atlas algorithm
    (gualaloom_v5_engine.py:3626-3683), reproduced verbatim but returning the
    FULL scored candidate list instead of just the top pick, plus whether the
    taught word's own motif appears in it and at what score. Also traces the
    -57 index (does self._word_to_chi_index contain this word at all) and the
    sight path (_recall_sight_from_atlas, :3582-3624) and the deep-atlas
    linked_chis expansion (_recall_response, :3522-3536) for completeness."""
    from collections import Counter
    wl = word.lower()
    chi = word_own_chi(word)
    in_index = wl in g._word_to_chi_index
    content_word_chis = set(g._word_to_chi_index.get(wl, ()))

    per_section = {}
    for target_section in target_sections:
        sec = g.sections.get(target_section)
        if not sec or not sec.modes:
            per_section[target_section] = {"candidates": [], "taught_present": False}
            continue
        candidates = Counter()
        for chi_k in content_word_chis:
            for e in g.atlas.entries.get(chi_k, []):
                if e["section"] == target_section and e["motif"] < len(sec.modes):
                    _, _, motif_word = sec.modes[e["motif"]]
                    if motif_word:
                        weight = 1.0 - e.get("function_score", 0.0)
                        candidates[e["motif"]] += weight
        ranked = []
        for motif_id, score in candidates.most_common():
            _, _, w = sec.modes[motif_id]
            ranked.append({"motif": motif_id, "word": w, "score": round(score, 4),
                            "qualifies (score>=2)": score >= 2})
        taught = next((r for r in ranked if r["word"] and r["word"].lower() == wl), None)
        winner = next((r for r in ranked if r["qualifies (score>=2)"]), None)
        per_section[target_section] = {
            "content_word_chis": sorted(content_word_chis),
            "candidates": ranked,
            "taught_present": taught is not None,
            "taught_entry": taught,
            "winner": winner,
        }

    # Sight path (_recall_sight_from_atlas) — for context; none of these 10
    # probes have a picture pairing, so this documents absence, not a defect.
    content_chis_sight = set(g._word_to_chi_index.get(wl, ())) if len(word) > 1 else set()
    sight_motif_ids = set()
    for target_chi in content_chis_sight:
        for d in range(-2, 3):
            for e in g.atlas.entries.get(target_chi + d, []):
                if e.get("section") == "sight":
                    sight_motif_ids.add(e.get("motif"))

    # Deep-atlas recall-time touchpoint: _recall_response's linked_chis
    # expansion (response_context/received_response links at this chi).
    deep_links = []
    for de in g.deep_atlas.entries.get(chi, []):
        if de.get("response_context") or de.get("received_response"):
            deep_links.append({"section": de.get("section"), "motif": de.get("motif"),
                                "response_context": de.get("response_context"),
                                "received_response": de.get("received_response")})

    return {
        "word": word, "chi": chi,
        "in_word_to_chi_index": in_index,
        "content_word_chis": sorted(content_word_chis),
        "sections": per_section,
        "sight_motif_ids_in_band": sorted(sight_motif_ids),
        "deep_atlas_linked_entries_at_own_chi": deep_links,
        "semantic_neighborhood_note": (
            "NOT PART OF THIS PATH — semantic_neighborhood is a channel in "
            "_emit_grandurun_vector (engine.py:162,210,2453), the emission/"
            "composition scorer. _recall_from_atlas and _recall_sight_from_atlas "
            "(engine.py:3582-3683) never reference it. Confirmed by grep, not "
            "assumed."
        ),
    }


def candidate_set_size(g, word, target_sections):
    """GL-CMD-159 A.2: total candidate-set size for one probe across
    target_sections — the pre-exclusion, pre-threshold candidate count
    _recall_from_atlas builds internally (reuses candidacy_trace's identical
    Counter reproduction, gualaloom_v5_engine.py:3626-3683, unfiltered by
    exclude_words so it doubles as the reachability signal below)."""
    trace = candidacy_trace(g, word, target_sections=target_sections)
    per_section_counts = {sec: len(info["candidates"])
                           for sec, info in trace["sections"].items()}
    return {
        "word": word,
        "per_section": per_section_counts,
        "total": sum(per_section_counts.values()),
        "reachable": any(info["taught_present"] for info in trace["sections"].values()),
    }


def variant_stats(g, words, target_sections):
    """GL-CMD-159 A.2/tiebreak: candidate-set size mean/max across a probe
    set for one variant, plus per-probe reachability (probe word present in
    its own candidate set at ANY target section, before self-exclusion —
    this is the F-1 reachability signal, distinct from whether _recall_
    response ultimately returns it after exclude_words filtering)."""
    sizes = [candidate_set_size(g, w, target_sections) for w in words]
    totals = [s["total"] for s in sizes]
    return {
        "target_sections": target_sections,
        "per_probe": sizes,
        "mean_total": round(sum(totals) / len(totals), 4) if totals else 0.0,
        "max_total": max(totals) if totals else 0,
        "n_reachable": sum(1 for s in sizes if s["reachable"]),
    }


def strongest_resident(g, chi, exclude_word=None):
    """A.4 helper: the highest-strength atlas entry at this exact chi, across
    all sections, excluding the probe's own word (so a taught word's own weak
    entry doesn't mask what it's actually competing with)."""
    best = None
    for e in g.atlas.entries.get(chi, []):
        sec = g.sections.get(e.get("section", ""))
        w = None
        if sec and e.get("motif", -1) < len(sec.modes):
            _, _, w = sec.modes[e["motif"]]
        if exclude_word and w and w.lower() == exclude_word.lower():
            continue
        strength = e.get("strength", -1)
        if best is None or strength > best["strength"]:
            best = {"section": e.get("section"), "word": w,
                     "strength": round(strength, 4), "motif": e.get("motif")}
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot-dir", required=True,
                     help="Directory with the downloaded save-snapshot JSON files "
                          "(S3 backup or EFS copy)")
    ap.add_argument("--words", default=None,
                     help="Comma-separated probe words. Default: draw 30 per the "
                          "declared deterministic rule.")
    ap.add_argument("--n", type=int, default=30,
                     help="Probe-set size when --words is not given (default 30)")
    ap.add_argument("--captions", default=None,
                     help="Comma-separated bundle-caption text per probe word, same "
                          "order/length as --words (for --quality-report's coherence "
                          "check). Default: each word's own caption is itself, i.e. "
                          "assumes guala_give_experience(caption=<word>).")
    ap.add_argument("--quality-report", action="store_true",
                     help="GL-CMD-157: print returned tokens per probe and the "
                          "coherence verdict (hit != coherent — a hit only means "
                          "_recall_response returned something non-empty).")
    ap.add_argument("--provenance", action="store_true",
                     help="GL-CMD-158: for each probe, trace existence (A.1) and "
                          "full candidacy at every recall stage (A.2) — deterministic, "
                          "read-only, same snapshot in -> same trace out every time.")
    ap.add_argument("--variant", choices=sorted(VARIANTS), default="svo",
                     help="GL-CMD-RECALL-REACH-159 Part A: recall's section surface. "
                          "'svo' = unmodified production (subject/verb/object) — the "
                          "baseline. 'L' = svo+listen. 'LI' = svo+listen+intro. "
                          "Forwarded to the engine's own _recall_response, not "
                          "reimplemented here.")
    ap.add_argument("--candidate-stats", action="store_true",
                     help="GL-CMD-159 A.2: candidate-set size (mean/max) per probe "
                          "across --variant's target_sections, vs the 'svo' baseline, "
                          "plus per-probe reachability (F-1's tiebreak signal).")
    args = ap.parse_args()

    target_sections = VARIANTS[args.variant]
    g = build_replay_guala(args.snapshot_dir)
    print(f"word_to_chi_index: {len(g._word_to_chi_index)} words indexed")
    print(f"n_pictures={len(g._pictures)}, n_sight_motifs={len(g.sight.motifs)}, "
          f"n_atlas_chi_keys={len(g.atlas.entries)}, "
          f"n_deep_atlas_entries={len(g.deep_atlas.entries)}")

    words = (args.words.split(",") if args.words
             else draw_probe_words(args.snapshot_dir, args.n))
    print(f"\nPROBE SET ({len(words)}): {words}")
    print(f"VARIANT: {args.variant!r} target_sections={target_sections}")

    captions = args.captions.split(",") if args.captions else words
    if len(captions) != len(words):
        raise SystemExit("--captions must have the same length as --words")

    results = [probe(g, w, target_sections=target_sections) for w in words]
    n_hits = sum(1 for r in results if r["hit"])
    print(f"\n=== RECALL: {n_hits}/{len(results)} = {100 * n_hits / len(results):.1f}% ===")
    for r, caption in zip(results, captions):
        line = (f"  {r['word']!r}: hit={r['hit']}  "
                f"recalled_text={r['recalled_text']!r}  n_pictures={r['n_pictures']}")
        if args.quality_report:
            coherent = r["hit"] and is_coherent(r["returned_tokens"], r["word"], caption)
            line += (f"  returned_tokens={r['returned_tokens']}  "
                     f"coherent={coherent if r['hit'] else 'n/a (miss)'}")
        print(line)

    if args.quality_report:
        hits = [r for r, c in zip(results, captions) if r["hit"]]
        n_coherent = sum(1 for r, c in zip(results, captions)
                          if r["hit"] and is_coherent(r["returned_tokens"], r["word"], c))
        if hits:
            print(f"\n=== QUALITY: {n_coherent}/{len(hits)} = "
                  f"{100 * n_coherent / len(hits):.1f}% of hits are coherent ===")
        else:
            print("\n=== QUALITY: n/a (no hits) ===")

    if args.candidate_stats:
        import json as _json
        print("\n" + "=" * 70)
        print(f"CANDIDATE-SET STATS (GL-CMD-159 A.2) — variant {args.variant!r}")
        print("=" * 70)
        stats = variant_stats(g, words, target_sections)
        print(_json.dumps(stats, indent=2, default=str))

    if args.provenance:
        import json as _json
        print("\n" + "=" * 70)
        print("PROVENANCE TRACE (GL-CMD-158)")
        print("=" * 70)
        for r, caption in zip(results, captions):
            w = r["word"]
            print(f"\n--- {w!r} ---")
            existence = existence_trace(g, w)
            print("A.1 EXISTENCE:", _json.dumps(existence, indent=2, default=str))
            candidacy = candidacy_trace(g, w, target_sections=target_sections)
            print("A.2 CANDIDACY:", _json.dumps(candidacy, indent=2, default=str))
            resident = strongest_resident(g, existence["chi"], exclude_word=w)
            returned_chis = [word_own_chi(t) for t in r["returned_tokens"]]
            print("A.4 CHI-COLLISION:", _json.dumps({
                "probe_chi": existence["chi"],
                "returned_tokens_and_chi": list(zip(r["returned_tokens"], returned_chis)),
                "strongest_resident_at_probe_chi": resident,
            }, indent=2, default=str))


if __name__ == "__main__":
    main()
