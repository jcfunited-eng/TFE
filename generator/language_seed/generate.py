"""generate.py -- top-level orchestrator.

GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1.

Pipeline:
  1. Preload all sources.
  2. Assemble master vocabulary (WordNet unioned with SCOWL, well-formed,
     capped at config.MAX_TOTAL_VOCAB) and rank it (frequency-based, see
     FrequencySource docstring for the COCA+Oxford substitution note) to
     pick the rich-layer top 50,000.
  3. Two-pass deterministic chi assignment across the WHOLE vocabulary
     (both layers share one address space) via chi_addresser.
  4. Build the ConceptNet index for exactly this vocabulary (one stream
     pass over the dump).
  5. Per word: grounding (rich only), affect (both, rich uses direct
     lexicon lookup + inheritance fallback; programmatic uses inheritance
     only), semantic network (rich: full; programmatic: minimal anchor).
  6. Build grammatical patterns once (rich.seed.json only).
  7. Validate + emit rich.seed.json and programmatic.seed.json.

Run: python -m generator.language_seed.generate [--limit N] [--rich-only]
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Dict, List, Set, Tuple

from generator.language_seed import affect as affect_mod
from generator.language_seed import chi_addresser as chi_mod
from generator.language_seed import config
from generator.language_seed import emit as emit_mod
from generator.language_seed import grammar as grammar_mod
from generator.language_seed import grounding as grounding_mod
from generator.language_seed import semantic_net as semnet_mod
from generator.language_seed import sources as sources_mod


def log(msg: str) -> None:
    print(f"[generate] {msg}", file=sys.stderr, flush=True)


def assemble_master_vocab(wn: sources_mod.WordNetSource, scowl: sources_mod.ScowlSource,
                           limit: "int | None" = None) -> Set[str]:
    vocab = set(wn.index.keys()) | set(scowl.index.keys())
    if limit is not None:
        # deterministic: keep the `limit` most WordNet-familiar single-word
        # entries first (for small smoke tests), else fall back alphabetical
        ranked = sorted(vocab, key=lambda w: (-(wn.index[w].familiarity if w in wn.index else 0), w))
        vocab = set(ranked[:limit])
    elif len(vocab) > config.MAX_TOTAL_VOCAB:
        # trim the most obscure SCOWL-only (non-WordNet) tail first
        scowl_only = [w for w in vocab if w not in wn.index]
        scowl_only.sort(key=lambda w: (-scowl.index[w], w))  # worst (highest) tier first... reverse below
        scowl_only.sort(key=lambda w: (scowl.index[w], w))
        keep_budget = config.MAX_TOTAL_VOCAB - len(vocab) + len(scowl_only)
        drop_n = len(vocab) - config.MAX_TOTAL_VOCAB
        drop_n = max(0, min(drop_n, len(scowl_only)))
        to_drop = set(sorted(scowl_only, key=lambda w: (-scowl.index[w], w))[:drop_n])
        vocab -= to_drop
    return vocab


def rank_vocab(vocab: Set[str], wn: sources_mod.WordNetSource,
                freq: sources_mod.FrequencySource) -> List[str]:
    def sort_key(word: str) -> Tuple[int, int, str]:
        freq_hit = freq.lookup(word)
        if freq_hit is not None:
            return (0, freq_hit[0], word)
        entry = wn.index.get(word)
        familiarity = entry.familiarity if entry else 0
        return (1, -familiarity, word)
    return sorted(vocab, key=sort_key)


def cluster_key_for(word: str, wn: sources_mod.WordNetSource, ud: sources_mod.UDSource) -> str:
    entry = wn.index.get(word)
    if entry and entry.primary_lexname:
        return entry.primary_lexname
    upos = ud.lookup(word)
    if upos:
        return f"_nonwordnet.{upos}"
    return "_unclustered"


def run(limit: "int | None" = None, rich_only: bool = False,
        programmatic_only: bool = False, tag: str = "") -> dict:
    t_start = time.time()
    metrics: Dict[str, dict] = {}

    def timed(name, fn):
        t0 = time.time()
        result = fn()
        metrics[name] = {"seconds": round(time.time() - t0, 2)}
        log(f"{name} done in {metrics[name]['seconds']}s")
        return result

    log("preloading sources...")
    wn = sources_mod.WordNetSource()
    timed("wordnet_preload", wn.preload)

    scowl = sources_mod.ScowlSource(max_tier=70)
    timed("scowl_preload", scowl.preload)

    freq = sources_mod.FrequencySource()
    timed("frequency_preload", freq.preload)

    cmu = sources_mod.CmuDictSource()
    timed("cmudict_preload", cmu.preload)

    nrc_emotion = sources_mod.NrcEmotionSource()
    timed("nrc_emotion_preload", nrc_emotion.preload)

    nrc_vad = sources_mod.NrcVadSource()
    timed("nrc_vad_preload", nrc_vad.preload)

    warriner = sources_mod.WarrinerSource()
    timed("warriner_preload", warriner.preload)

    ud = sources_mod.UDSource()
    timed("ud_preload", ud.preload)

    imagenet = sources_mod.ImageNetSource(wn)
    timed("imagenet_preload", imagenet.preload)

    log("assembling master vocabulary...")
    vocab = assemble_master_vocab(wn, scowl, limit=limit)
    log(f"master vocabulary size: {len(vocab)}")

    ranked = rank_vocab(vocab, wn, freq)
    rich_size = min(config.RICH_LAYER_SIZE, len(ranked)) if limit is None else max(1, len(ranked) // 2)
    rich_words = set(ranked[:rich_size])
    programmatic_words = set(ranked[rich_size:])
    log(f"rich layer: {len(rich_words)} words, programmatic layer: {len(programmatic_words)} words")

    cn = sources_mod.ConceptNetSource()
    cache_name = f"conceptnet_index{tag}.json" if tag else "conceptnet_index.json"
    timed("conceptnet_build_index", lambda: cn.build_index(vocab, cache_name=cache_name))

    log("assigning chi addresses...")
    t0 = time.time()
    cluster_counts: Dict[str, int] = {}
    word_cluster: Dict[str, str] = {}
    for word in vocab:
        ck = cluster_key_for(word, wn, ud)
        word_cluster[word] = ck
        cluster_counts[ck] = cluster_counts.get(ck, 0) + 1
    addresser = chi_mod.ChiAddresser(cluster_counts)
    for word in sorted(vocab):
        addresser.assign(word, word_cluster[word])
    word_to_chi = addresser.word_to_chi
    metrics["chi_assignment"] = {"seconds": round(time.time() - t0, 2)}
    log(f"chi assignment done in {metrics['chi_assignment']['seconds']}s, "
        f"{len(word_to_chi)} addresses, {len(addresser.used)} used slots")

    grounding_builder = grounding_mod.GroundingBuilder(wn, imagenet, cmu, cn)
    affect_resolver = affect_mod.AffectResolver(nrc_vad, warriner, nrc_emotion)

    rich_word_to_chi = {w: word_to_chi[w] for w in rich_words}

    rich_entries: List[dict] = []
    rich_networks: List[dict] = []
    log("building rich layer entries...")
    t0 = time.time()
    for word in ranked[:rich_size]:
        chi = word_to_chi[word]
        wn_entry = wn.index.get(word)
        grounding = grounding_builder.build(word, chi, wn_entry)
        net = semnet_mod.build_semantic_network(word, chi, wn_entry, cn.lookup(word), rich_word_to_chi)
        affect = affect_resolver.resolve(word, chi, "rich", net["related_chis"] if net else None)
        rich_entries.append(emit_mod.build_vocabulary_entry(word, chi, "rich", grounding, affect))
        if net:
            rich_networks.append(net)
    metrics["rich_entry_build"] = {"seconds": round(time.time() - t0, 2)}
    log(f"rich entries built in {metrics['rich_entry_build']['seconds']}s")

    rich_patterns = grammar_mod.build_patterns(word_to_chi, ud)

    rich_seed = emit_mod.assemble(rich_entries, rich_patterns, rich_networks)
    rich_chis = {e["chi"] for e in rich_entries}

    programmatic_entries: List[dict] = []
    programmatic_networks: List[dict] = []
    if not rich_only:
        log("building programmatic layer entries...")
        t0 = time.time()
        for word in ranked[rich_size:]:
            chi = word_to_chi[word]
            wn_entry = wn.index.get(word)
            net = semnet_mod.build_minimal_anchor(word, chi, wn_entry, rich_word_to_chi)
            affect = affect_resolver.resolve(word, chi, "programmatic", net["related_chis"] if net else None)
            programmatic_entries.append(
                emit_mod.build_vocabulary_entry(word, chi, "programmatic", {}, affect))
            if net:
                programmatic_networks.append(net)
        metrics["programmatic_entry_build"] = {"seconds": round(time.time() - t0, 2)}
        log(f"programmatic entries built in {metrics['programmatic_entry_build']['seconds']}s")

    programmatic_seed = emit_mod.assemble(programmatic_entries, [], programmatic_networks)

    log("validating + writing rich.seed.json...")
    rich_path = config.output_path(f"rich{tag}.seed.json")
    emit_mod.emit(rich_seed, rich_path)
    log(f"wrote {rich_path}")

    prog_path = None
    if not rich_only:
        log("validating + writing programmatic.seed.json...")
        prog_path = config.output_path(f"programmatic{tag}.seed.json")
        emit_mod.emit(programmatic_seed, prog_path, additional_valid_chis=rich_chis)
        log(f"wrote {prog_path}")

    metrics["total_seconds"] = round(time.time() - t_start, 2)
    metrics["affect_source_counts"] = affect_resolver.source_counts
    metrics["affect_defaulted_count"] = affect_resolver.defaulted_count
    metrics["rich_count"] = len(rich_entries)
    metrics["programmatic_count"] = len(programmatic_entries)
    metrics["rich_networks_count"] = len(rich_networks)
    metrics["programmatic_networks_count"] = len(programmatic_networks)
    metrics["patterns_count"] = len(rich_patterns)
    metrics["rich_path"] = rich_path
    metrics["programmatic_path"] = prog_path
    metrics["master_vocab_size"] = len(vocab)

    log(f"total generation time: {metrics['total_seconds']}s")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--rich-only", action="store_true")
    parser.add_argument("--tag", type=str, default="")
    args = parser.parse_args()
    result = run(limit=args.limit, rich_only=args.rich_only, tag=args.tag)
    import json
    print(json.dumps(result, indent=2))
