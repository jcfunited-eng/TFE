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
"""
import argparse
import json
import os
import sys
from collections import defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


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


def probe(g, word):
    """One recall probe: build input_chis/input_word_chis exactly as a live
    /converse turn does, call the real _recall_response, report hit/miss.
    Resets _last_recalled_pictures first — belt-and-suspenders now that
    GL-CMD-155 fixed the underlying leak in _recall_response itself, but kept
    here so this harness stays correct even if that regresses."""
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
    recalled_text = g._recall_response(input_chis, input_word_chis, words)
    pics = getattr(g, "_last_recalled_pictures", [])
    return {
        "word": word,
        "hit": bool(recalled_text) or bool(pics),
        "recalled_text": recalled_text,
        "n_pictures": len(pics),
    }


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
    args = ap.parse_args()

    g = build_replay_guala(args.snapshot_dir)
    print(f"word_to_chi_index: {len(g._word_to_chi_index)} words indexed")
    print(f"n_pictures={len(g._pictures)}, n_sight_motifs={len(g.sight.motifs)}, "
          f"n_atlas_chi_keys={len(g.atlas.entries)}, "
          f"n_deep_atlas_entries={len(g.deep_atlas.entries)}")

    words = (args.words.split(",") if args.words
             else draw_probe_words(args.snapshot_dir, args.n))
    print(f"\nPROBE SET ({len(words)}): {words}")

    results = [probe(g, w) for w in words]
    n_hits = sum(1 for r in results if r["hit"])
    print(f"\n=== RECALL: {n_hits}/{len(results)} = {100 * n_hits / len(results):.1f}% ===")
    for r in results:
        print(f"  {r['word']!r}: hit={r['hit']}  "
              f"recalled_text={r['recalled_text']!r}  n_pictures={r['n_pictures']}")


if __name__ == "__main__":
    main()
