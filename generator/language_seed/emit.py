"""emit.py -- .seed.json emitter + integrity validation.

Combines chi_addresser/grounding/semantic_net/affect/grammar output into
the seed file format Phase 1 defined, runs the dispatch's own integrity
checks before ever writing a file, and halts (raises SeedIntegrityError)
on any failure -- "no corrupt seed ever gets shipped."

SCHEMA GAP FLAGGED FOR EVE: Phase 1's finalized format
(vocabulary_entries: word/chi/phase_vec/grounding/hemisphere_affinity/
initial_strength) has no field for affect data -- Phase 1's own report
named this exact gap (finding #3: "affect memory has no schema field...
Eve's call whether Phase 2 needs one"). This dispatch still requires
building affect.py and validating "affect values within valid ranges,"
so real affect IS computed for every word. Rather than silently drop it
or silently invent undocumented behavior, one small ADDITIVE field is
appended per vocabulary entry: `"affect": {"valence","arousal",
"dominance","source"}`. This is non-breaking: seed_loader.py's
_load_vocabulary_entries only reads known keys via .get(), so an
unrecognized "affect" key is inert (present in the file, written nowhere)
until Eve authorizes a loader amendment to consume it. Not a Phase-1
loader modification -- no loader code changed.
"""

from __future__ import annotations

import json
from typing import Dict, List

from generator.language_seed import config


class SeedIntegrityError(Exception):
    pass


def build_vocabulary_entry(word: str, chi: int, tier: str,
                            grounding: Dict[str, int],
                            affect: tuple) -> dict:
    v, a, d, source = affect
    return {
        "word": word,
        "chi": chi,
        "phase_vec": None,
        "grounding": grounding,
        "hemisphere_affinity": list(config.LANGUAGE_ORGANS),
        "initial_strength": 1.0 if tier == "rich" else 0.5,
        "affect": {
            "valence": round(v, 4),
            "arousal": round(a, 4),
            "dominance": round(d, 4),
            "source": source,
        },
    }


def assemble(vocabulary_entries: List[dict], grammatical_patterns: List[dict],
             semantic_networks: List[dict]) -> dict:
    return {
        "version": config.SEED_FORMAT_VERSION,
        "vocabulary_entries": vocabulary_entries,
        "grammatical_patterns": grammatical_patterns,
        "semantic_networks": semantic_networks,
    }


def validate(seed: dict, additional_valid_chis: "set | None" = None) -> List[str]:
    """Returns a list of integrity errors (empty == pass). Never raises
    itself -- callers decide whether to halt.

    additional_valid_chis: chis known-seeded by a companion file that is
    guaranteed already loaded by the time this seed's references are
    resolved (e.g. rich.seed.json's chis when validating
    programmatic.seed.json -- rich loads blocking-first, per the loader
    spec, so a programmatic entry referencing a rich chi is legitimate
    even though rich's vocabulary_entries aren't in THIS file)."""
    errors: List[str] = []

    vocab = seed.get("vocabulary_entries") or []
    patterns = seed.get("grammatical_patterns") or []
    networks = seed.get("semantic_networks") or []

    seen_chi: Dict[int, str] = {}
    valid_chis = set(additional_valid_chis or ())
    for entry in vocab:
        chi = entry["chi"]
        word = entry["word"]
        if not (config.CHI_MIN <= chi <= config.CHI_MAX):
            errors.append(f"vocabulary {word!r}: chi {chi} out of range 0-{config.CHI_MAX}")
            continue
        if chi in seen_chi:
            errors.append(f"chi collision: {chi} used by both {seen_chi[chi]!r} and {word!r}")
            continue
        seen_chi[chi] = word
        valid_chis.add(chi)

    for entry in vocab:
        word = entry["word"]
        for modality, mod_chi in (entry.get("grounding") or {}).items():
            if not (config.CHI_MIN <= mod_chi <= config.CHI_MAX):
                errors.append(f"vocabulary {word!r}: grounding[{modality}] chi {mod_chi} out of range")
            elif mod_chi not in valid_chis:
                errors.append(f"vocabulary {word!r}: grounding[{modality}] chi {mod_chi} does not reference a seeded entry")
        affect = entry.get("affect")
        if affect is not None:
            v, a, d = affect["valence"], affect["arousal"], affect["dominance"]
            if not (-1.0 <= v <= 1.0):
                errors.append(f"vocabulary {word!r}: affect.valence {v} out of range -1..1")
            if not (0.0 <= a <= 1.0):
                errors.append(f"vocabulary {word!r}: affect.arousal {a} out of range 0..1")
            if not (0.0 <= d <= 1.0):
                errors.append(f"vocabulary {word!r}: affect.dominance {d} out of range 0..1")
        for tag in (entry.get("hemisphere_affinity") or []):
            if tag not in config.ALL_ORGAN_TAGS:
                errors.append(f"vocabulary {word!r}: unknown hemisphere_affinity tag {tag!r}")

    seen_pattern_ids = set()
    for pattern in patterns:
        pid = pattern["pattern_id"]
        key = (pid, pattern["hemisphere"])
        if key in seen_pattern_ids:
            errors.append(f"pattern {pid!r}/{pattern['hemisphere']}: duplicate pattern_id+hemisphere")
        seen_pattern_ids.add(key)
        if pattern["hemisphere"] not in config.ALL_ORGAN_TAGS:
            errors.append(f"pattern {pid!r}: unknown hemisphere tag {pattern['hemisphere']!r}")
        for chi in pattern.get("chi_sequence") or []:
            if not (config.CHI_MIN <= chi <= config.CHI_MAX):
                errors.append(f"pattern {pid!r}: chi_sequence value {chi} out of range")
        for neighbor_id, weight in (pattern.get("coupling_weights") or {}).items():
            lo, hi = config.J_VALID_RANGE
            if not (lo <= weight <= hi):
                errors.append(f"pattern {pid!r}: coupling_weights[{neighbor_id}]={weight} outside J range {config.J_VALID_RANGE}")

    for net in networks:
        center = net["center_chi"]
        if not (config.CHI_MIN <= center <= config.CHI_MAX):
            errors.append(f"semantic network center_chi {center} out of range")
        elif center not in valid_chis:
            errors.append(f"semantic network center_chi {center} does not reference a seeded entry")
        for rel in net.get("related_chis") or []:
            rchi, strength = rel["chi"], rel["strength"]
            if not (config.CHI_MIN <= rchi <= config.CHI_MAX):
                errors.append(f"semantic network {center}: related chi {rchi} out of range")
            elif rchi not in valid_chis:
                errors.append(f"semantic network {center}: related chi {rchi} does not reference a seeded entry")
            if not (0.0 <= strength <= 1.0):
                errors.append(f"semantic network {center}: related chi {rchi} strength {strength} out of range 0..1")
        for tag in (net.get("applies_to_hemispheres") or []):
            if tag not in config.ALL_ORGAN_TAGS and tag != "all":
                errors.append(f"semantic network {center}: unknown hemisphere tag {tag!r}")

    return errors


def emit(seed: dict, path: str, additional_valid_chis: "set | None" = None) -> None:
    errors = validate(seed, additional_valid_chis=additional_valid_chis)
    if errors:
        raise SeedIntegrityError(
            f"{len(errors)} integrity error(s), first 20: " + " | ".join(errors[:20]))
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seed, f)
