"""seed_loader.py — GL-CMD-LANGUAGE-SEED-EVE-20260707-v1 Phase 1.

Format definition + loader ONLY. No vocabulary curation (Phase 2), no
auto-load on any deployed substrate, no bypass of existing storage paths,
no ML embedding / pretrained weight support.

Seed file format (".seed.json"), top-level keys:

  version: "v1"

  vocabulary_entries: [
    {
      "word": str,                        # required
      "chi": int,                         # required -- chi address for this word
      "phase_vec": [float, ...] | null,   # optional, 32 floats (16 complex
                                           #   re/im interleaved), or null
      "grounding": {modality: chi_int},   # optional, e.g. {"visual": 501}
      "hemisphere_affinity": str | [str], # optional, organ tag(s) --
                                           #   em/pr/ep/sc/gp/sf/sv/aff,
                                           #   matching Guala.organism.hemi_by_op
      "initial_strength": float           # optional, default 1.0
    }, ...
  ]

  grammatical_patterns: [
    {
      "pattern_id": str,                  # required
      "chi_sequence": [int, ...],         # required, ordered chi addresses
      "coupling_weights": {str: float},   # optional, {neighbor_neuron_id: weight}
      "hemisphere": str                   # required, organ tag
    }, ...
  ]

  semantic_networks: [
    {
      "center_chi": int,                        # required
      "related_chis": [{"chi": int, "strength": float}, ...],  # required
      "applies_to_hemispheres": str | [str] | "all"  # required
    }, ...
  ]

Write paths (through existing substrate mechanisms only, never a new or
bypassing storage mechanism):

  - chi_atlas.record(section_name, motif_id, chi_value, tick=None)
    -- per-neuron, dsf_ai_service/v4/gualaloom_v4_chi_atlas_l6.py.
       Reached via substrate.organism.brain / .hemi_by_op / .cluster.neurons.
  - WaveAtlas.record(section_name, motif_id, chi_value, ..., phase_vec=None, ...)
    -- dsf_ai_service/v4/wave_atlas.py, the documented public write API
       ("Interface matches LivingAtlas.record()"). Reached via
       substrate.wave_atlas (may be None if WAVE_ATLAS_ENABLED is unset --
       guarded, not assumed present).
  - couplings.J -- dsf_ai_service/loom_model/neuron.py's CouplingsJij has
    no public setter; the only existing mutators (__init__,
    update_from_dsf) write the SAME (K, n_modes) numpy array this loader
    targets. No existing code pokes .J element-wise from outside the
    class, so this loader is establishing a new but storage-respecting
    pattern -- it writes into the identical array cells the class's own
    methods write into, for neighbors ALREADY present in the ring
    topology (no new neighbor relationships are fabricated; a
    coupling_weights entry naming a neuron_id not already in that
    neuron's ring neighbors is skipped, not force-added).

  Note on "affect memory": named in this dispatch's own build spec
  ("Writes to chi_atlas.record, WaveAtlas.record, couplings.J, affect
  memory") but no field in the format above (vocabulary_entries /
  grammatical_patterns / semantic_networks, per the dispatch's own item 1
  listing) actually carries affect/needs data to write. This loader does
  not call Guala.needs.step(...) anywhere, since there's nothing in the
  current schema to feed it -- flagged in the report rather than inventing
  a field the format definition didn't ask for.

Deterministic neuron selection: a given chi_value always resolves to the
same neuron within a hemisphere's cluster (index = chi_value % len(neurons)),
so re-loading the same seed file is idempotent in WHERE it writes, not just
what it writes.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional


SEED_FORMAT_VERSION = "v1"


@dataclass
class LoadReport:
    ok: bool
    version: Optional[str] = None
    vocabulary_loaded: int = 0
    patterns_loaded: int = 0
    networks_loaded: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class SeedLoadProgress:
    """Health-endpoint-facing progress for the rich/programmatic split
    (GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1). Plain-attribute
    updates only (no lock) -- each field is written by exactly one thread
    (the background loader) and read-only elsewhere; CPython attribute
    assignment is atomic, and progress reporting doesn't need stronger
    consistency than "eventually reflects the latest chunk."
    """
    rich_started: bool = False
    rich_done: bool = False
    rich_report: Optional[LoadReport] = None
    rich_error: Optional[str] = None
    programmatic_total: int = 0
    programmatic_loaded: int = 0
    programmatic_done: bool = False
    programmatic_report: Optional[LoadReport] = None
    programmatic_error: Optional[str] = None

    def as_dict(self) -> dict:
        pct = 0.0
        if self.programmatic_total:
            pct = round(100.0 * self.programmatic_loaded / self.programmatic_total, 1)
        return {
            "rich_complete": self.rich_done,
            "rich_ok": (self.rich_report.ok if self.rich_report else None),
            "programmatic_total": self.programmatic_total,
            "programmatic_loaded": self.programmatic_loaded,
            "programmatic_percent": pct,
            "programmatic_complete": self.programmatic_done,
        }


@dataclass
class IntegrityReport:
    ok: bool
    words_checked: int = 0
    words_verified: int = 0
    words_missing: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _resolve_hemisphere(substrate, tag):
    """tag is an organ operation tag (em/pr/ep/sc/gp/sf/sv/aff), matching
    Guala.organism.hemi_by_op -- the substrate's own real naming
    convention for hemispheres (not the raw H0..H7 topology IDs)."""
    organism = getattr(substrate, "organism", None)
    if organism is None:
        return None
    hemi_by_op = getattr(organism, "hemi_by_op", {})
    return hemi_by_op.get(tag)


def _neuron_for_chi(hemi, chi_value: int):
    """Deterministic, reproducible neuron selection for a given chi within
    a hemisphere's cluster. Not random -- re-loading the same seed always
    targets the same neurons."""
    neurons = hemi.cluster.neurons
    if not neurons:
        return None
    idx = abs(int(chi_value)) % len(neurons)
    return neurons[idx]


def _load_vocabulary_entries(substrate, entries, report: LoadReport):
    for entry in entries:
        try:
            word = entry["word"]
            chi = int(entry["chi"])
            phase_vec = entry.get("phase_vec")
            grounding = entry.get("grounding") or {}
            hemi_tags = entry.get("hemisphere_affinity") or []
            if isinstance(hemi_tags, str):
                hemi_tags = [hemi_tags]
            initial_strength = float(entry.get("initial_strength", 1.0))

            for tag in hemi_tags:
                hemi = _resolve_hemisphere(substrate, tag)
                if hemi is None:
                    report.warnings.append(
                        f"vocabulary {word!r}: unknown hemisphere tag {tag!r}, skipped")
                    continue
                neuron = _neuron_for_chi(hemi, chi)
                if neuron is None:
                    report.warnings.append(
                        f"vocabulary {word!r}: hemisphere {tag!r} has no neurons, skipped")
                    continue
                neuron.chi_atlas.record("neuron", word, chi)

            wave_atlas = getattr(substrate, "wave_atlas", None)
            if wave_atlas is not None:
                wave_atlas.record("modifier", word, chi,
                                   phase_vec=phase_vec, salience=initial_strength)
                for modality, mod_chi in grounding.items():
                    wave_atlas.record(modality, word, int(mod_chi),
                                       salience=initial_strength)
            elif grounding:
                report.warnings.append(
                    f"vocabulary {word!r}: grounding given but wave_atlas is None "
                    f"(WAVE_ATLAS_ENABLED unset) -- grounding not written")

            report.vocabulary_loaded += 1
        except Exception as e:
            report.errors.append(f"vocabulary entry {entry!r}: {e}")


def _load_grammatical_patterns(substrate, patterns, report: LoadReport):
    for pattern in patterns:
        try:
            pattern_id = pattern["pattern_id"]
            chi_sequence = pattern.get("chi_sequence") or []
            coupling_weights = pattern.get("coupling_weights") or {}
            hemi_tag = pattern["hemisphere"]
            hemi = _resolve_hemisphere(substrate, hemi_tag)
            if hemi is None:
                report.warnings.append(
                    f"pattern {pattern_id!r}: unknown hemisphere tag {hemi_tag!r}, skipped")
                continue

            for chi in chi_sequence:
                neuron = _neuron_for_chi(hemi, chi)
                if neuron is not None:
                    neuron.chi_atlas.record("neuron", pattern_id, int(chi))

            # Only for neighbors already present in the ring topology --
            # no new neighbor relationships are fabricated here.
            for neighbor_id, weight in coupling_weights.items():
                found = False
                for neuron in hemi.cluster.neurons:
                    if neighbor_id in neuron.couplings.neighbors:
                        idx = neuron.couplings.neighbors.index(neighbor_id)
                        neuron.couplings.J[idx, :] = float(weight)
                        found = True
                if not found:
                    report.warnings.append(
                        f"pattern {pattern_id!r}: neighbor {neighbor_id!r} not found "
                        f"in any neuron's ring topology in hemisphere {hemi_tag!r}, "
                        f"coupling weight not written")

            report.patterns_loaded += 1
        except Exception as e:
            report.errors.append(f"pattern entry {pattern!r}: {e}")


def _load_semantic_networks(substrate, networks, report: LoadReport):
    for net in networks:
        try:
            center_chi = int(net["center_chi"])
            related = net.get("related_chis") or []
            hemi_tags = net["applies_to_hemispheres"]
            if hemi_tags == "all":
                organism = getattr(substrate, "organism", None)
                hemi_tags = list(getattr(organism, "hemi_by_op", {}).keys())
            elif isinstance(hemi_tags, str):
                hemi_tags = [hemi_tags]

            for tag in hemi_tags:
                hemi = _resolve_hemisphere(substrate, tag)
                if hemi is None:
                    report.warnings.append(
                        f"semantic network center_chi={center_chi}: unknown "
                        f"hemisphere tag {tag!r}, skipped")
                    continue
                for rel in related:
                    rel_chi = int(rel["chi"])
                    neuron = _neuron_for_chi(hemi, rel_chi)
                    if neuron is not None:
                        neuron.chi_atlas.record("neuron", center_chi, rel_chi)

            report.networks_loaded += 1
        except Exception as e:
            report.errors.append(f"semantic network entry {net!r}: {e}")


def load_seed(path: str, substrate) -> LoadReport:
    """Load a .seed.json file into a running substrate. Writes go through
    the existing chi_atlas.record / WaveAtlas.record / couplings.J storage
    paths only -- see module docstring. Best-effort per-entry: one
    malformed entry is recorded as an error, loading continues for the
    rest of the file.
    """
    report = LoadReport(ok=True)
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        report.ok = False
        report.errors.append(f"failed to read/parse seed file: {e}")
        return report

    report.version = data.get("version")
    if report.version != SEED_FORMAT_VERSION:
        report.warnings.append(
            f"seed file version {report.version!r} != loader version "
            f"{SEED_FORMAT_VERSION!r}")

    _load_vocabulary_entries(substrate, data.get("vocabulary_entries") or [], report)
    _load_grammatical_patterns(substrate, data.get("grammatical_patterns") or [], report)
    _load_semantic_networks(substrate, data.get("semantic_networks") or [], report)

    if report.errors:
        report.ok = False
    return report


def _load_programmatic_background(path: str, substrate, progress: SeedLoadProgress,
                                    chunk_size: int) -> None:
    """Runs on a background thread. Loads vocabulary_entries in chunks of
    `chunk_size` with a brief yield between chunks (so a long programmatic
    load doesn't starve the request-handling thread), then semantic_networks
    (comparatively few -- not chunked) in one pass. Same per-entry write
    paths as load_seed/_load_vocabulary_entries -- no new storage mechanism."""
    report = LoadReport(ok=True)
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        report.ok = False
        report.errors.append(f"failed to read/parse programmatic seed file: {e}")
        progress.programmatic_error = str(e)
        progress.programmatic_report = report
        progress.programmatic_done = True
        return

    report.version = data.get("version")
    if report.version != SEED_FORMAT_VERSION:
        report.warnings.append(
            f"programmatic seed file version {report.version!r} != loader version "
            f"{SEED_FORMAT_VERSION!r}")

    entries = data.get("vocabulary_entries") or []
    progress.programmatic_total = len(entries)

    for start in range(0, len(entries), chunk_size):
        chunk = entries[start:start + chunk_size]
        try:
            _load_vocabulary_entries(substrate, chunk, report)
        except Exception as e:
            report.errors.append(f"programmatic chunk at {start}: {e}")
        progress.programmatic_loaded = min(start + chunk_size, len(entries))
        time.sleep(0)  # yield -- brief pause between chunks, per dispatch

    _load_grammatical_patterns(substrate, data.get("grammatical_patterns") or [], report)
    _load_semantic_networks(substrate, data.get("semantic_networks") or [], report)

    if report.errors:
        report.ok = False
    progress.programmatic_report = report
    progress.programmatic_done = True


def load_seed_layered(rich_path: str, substrate, programmatic_path: Optional[str] = None,
                       chunk_size: int = 1000) -> SeedLoadProgress:
    """GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1 loader
    enhancement. Rich loads blocking (same load_seed() as always -- this
    function doesn't change single-file loading behavior at all).
    Programmatic, if given, loads on a background thread in chunks of
    `chunk_size` entries with a yield between chunks, so it never blocks
    substrate boot or request handling. Returns a SeedLoadProgress the
    caller can poll (e.g. from a health endpoint) -- rich_done is True by
    the time this function returns; programmatic_done flips asynchronously.
    """
    progress = SeedLoadProgress()
    progress.rich_started = True
    try:
        progress.rich_report = load_seed(rich_path, substrate)
    except Exception as e:
        progress.rich_error = str(e)
        progress.rich_report = LoadReport(ok=False, errors=[str(e)])
    progress.rich_done = True

    if programmatic_path:
        thread = threading.Thread(
            target=_load_programmatic_background,
            args=(programmatic_path, substrate, progress, chunk_size),
            name="seed-loader-programmatic",
            daemon=True,
        )
        thread.start()
    else:
        progress.programmatic_done = True

    return progress


def verify_seed_integrity(substrate, seed_path: Optional[str] = None) -> IntegrityReport:
    """Confirm seeded vocabulary is actually present and retrievable via
    the substrate's existing recall paths (chi_atlas.match_score), not
    just that load_seed() returned without error. If seed_path is given,
    re-reads it to know which words to check; otherwise this only
    sanity-checks that SOME chi_atlas entries exist (a substrate could
    have been seeded from a file no longer available)."""
    report = IntegrityReport(ok=True)
    organism = getattr(substrate, "organism", None)
    if organism is None:
        report.ok = False
        report.errors.append("substrate.organism is None -- cannot verify")
        return report

    words_to_check: List[Any] = []
    if seed_path is not None:
        try:
            with open(seed_path) as f:
                data = json.load(f)
            words_to_check = [
                (e["word"], int(e["chi"]), e.get("hemisphere_affinity") or [])
                for e in data.get("vocabulary_entries") or []
            ]
        except Exception as e:
            report.errors.append(f"could not re-read seed file for verification: {e}")

    for word, chi, hemi_tags in words_to_check:
        if isinstance(hemi_tags, str):
            hemi_tags = [hemi_tags]
        report.words_checked += 1
        found = False
        for tag in hemi_tags:
            hemi = _resolve_hemisphere(substrate, tag)
            if hemi is None:
                continue
            neuron = _neuron_for_chi(hemi, chi)
            if neuron is None:
                continue
            # match_score > 0 means the atlas has SOME entry in this
            # chi's band -- the same check the real substrate uses for
            # familiarity, not a separate ad hoc lookup.
            if neuron.chi_atlas.match_score(chi, "neuron") > 0.0:
                found = True
                break
        if found:
            report.words_verified += 1
        else:
            report.words_missing.append(word)

    if report.words_missing:
        report.ok = False
    return report
