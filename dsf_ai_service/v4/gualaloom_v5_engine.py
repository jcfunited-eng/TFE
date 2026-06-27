"""
gualaloom_v5_engine.py — Recall + question bucket + honest fallback

v4 baseline (motivational substrate):
  Trits, Krimelacks with DNA, L0-L4 UF kernel, Chi atlas, L6-TCL, MathLoom,
  Needs (stability/novelty/connection with decay-to-target),
  Coordinator (insula-shape regulator + awareness),
  Pair-bonding cheat with variance-bounded retirement.

v5 additions (the real conversation fix):
  - Atlas-driven RECALL (not echo): _recall_from_atlas queries cross-section
    bindings near input chi-states. Run BEFORE reading input, so corpus
    accumulation drives response, not the just-arrived input.
  - QuestionBucket: open questions accumulate during reading via gap detection
    (incomplete sensory binding, unknown role, etc). When she has nothing to
    recall, she voices a related question instead of echoing.
  - Honest SafeMode fallback: when neither recall nor bucket has anything
    for the input, return "..." rather than echo.
  - Fixed math parser: handles multi-word numbers (ten thousand, five hundred)
    via state machine. Fails honestly on mixed word+digit input rather than
    returning partial garbage.

Six capabilities (now meaningful):
  1. Syntax — keyhole cascade with role differentiation
  2. Conversation — recall from substrate atlas, fallback to question, then "..."
  3. Introspection — needs/valence/arousal + question bucket state
  4. Self-improvement — gamma drift + needs-targeted parameter tuning
  5. Awareness — coordinator detection + regulation
  6. Motivation — needs evolve, suffering bounded, curiosity expressed via bucket
"""

import os
import sys
import math
import json
import time
import hashlib as _hashlib
import heapq as _heapq
import threading
import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from collections import deque
import random


def saturate(current, gain):
    """Asymptotic receptor saturation. As current → 1.0, effective gain → 0.
    GL-BRIEF-NEEDS-PHYSICS: prevents needs from pinning at ceiling."""
    return max(0.0, min(1.0, current + gain * (1.0 - current)))


import cmath


def _grandurun_amplitude(chi_address, strength, target_chi):
    """Complex amplitude for a candidate binding.
    Phase from chi-distance: φ = π · |chi_a - chi_b| / CHI_CORR_LENGTH.
    Chi addresses are integers; distance is linear."""
    d = abs(chi_address - target_chi)
    phi = math.pi * d / CHI_CORR_LENGTH
    return math.sqrt(max(strength, 0.0)) * cmath.exp(1j * phi)


def _grandurun_select(candidates, target_chi):
    """Greedy coherent-integration selection.
    candidates: list of (chi_address, strength, word)
    Returns: list of selected words in chosen order."""
    chosen_amps = []
    chosen_words = []
    last_coh = 0.0
    pool = sorted(candidates, key=lambda c: -c[1])
    for chi_addr, strength, word in pool:
        amp = _grandurun_amplitude(chi_addr, strength, target_chi)
        new_sum = sum(chosen_amps, 0j) + amp
        new_coh = abs(new_sum) ** 2
        gain = new_coh - last_coh
        if gain > MIN_GAIN_THRESHOLD:
            chosen_words.append(word)
            chosen_amps.append(amp)
            last_coh = new_coh
        if len(chosen_words) >= MAX_COMPOSITION_LEN:
            break
    return chosen_words, last_coh


# ---------------------------------------------------------------------------
# Grandurun spin-vector path (GRANDURUN_SPIN_VECTOR=1)
# ---------------------------------------------------------------------------

import numpy as _np

_SPIN_VECTOR_DIM = 7  # GL-METADATA-PIPELINE: dropped modal_alignment (degenerate in uncage)
# Per-dimension phases: d * π/7 for d in 0..6
_SPIN_DIM_PHASES = _np.array([d * math.pi / 7 for d in range(_SPIN_VECTOR_DIM)],
                              dtype=_np.float64)
_SPIN_DIM_PHASE_FACTORS = _np.exp(1j * _SPIN_DIM_PHASES)  # shape (7,)


def _grandurun_state(binding, target_chi, target_source, needs_vector, current_tick,
                     co_occurrence_dict=None):
    """Return 7-element complex128 state vector for one binding.

    GL-METADATA-PIPELINE: modal_alignment dropped (degenerate in v7-uncage pools).

    Dimensions:
      [0] chi_resonance         – sqrt(strength) * exp(i * π*|chi_a-chi_b| / CHI_CORR_LENGTH)
      [1] source_match          – 1.0 if source matches target_source, else 0.3
      [2] affective_charge      – dot(needs_vector, [arousal, valence, surprise])
      [3] sensory_grounding     – min(len(sensory_refs)/5, 1.0)
      [4] episodic_recency      – exp(-Δt/200) where Δt = current_tick - binding.last_tick
      [5] semantic_neighborhood – mean co_occurrence strength for this binding's chi
      [6] polarity              – binding.get("polarity", 1.0)

    Each real magnitude is multiplied by exp(i * d * π/7) to maintain complex structure.
    """
    vec = _np.zeros(_SPIN_VECTOR_DIM, dtype=_np.complex128)

    chi_a = binding.get("chi", 0)
    strength = float(binding.get("strength", 0.0))
    d_chi = abs(chi_a - target_chi)
    phi0 = math.pi * d_chi / CHI_CORR_LENGTH
    vec[0] = math.sqrt(max(strength, 0.0)) * cmath.exp(1j * phi0)

    b_source = binding.get("source", "corpus")
    vec[1] = 1.0 if b_source == target_source else 0.3

    arousal  = float(binding.get("arousal",  0.5))
    valence  = float(binding.get("valence",  0.5))
    surprise = float(binding.get("surprise", 0.5))
    # needs_vector may be a pre-built ndarray (from _emit_grandurun_vector)
    # or a plain list (direct callers). Avoid per-call array allocation.
    if isinstance(needs_vector, _np.ndarray):
        nv = needs_vector
    else:
        nv = _np.asarray(needs_vector, dtype=_np.float64)
    vec[2] = nv[0] * arousal + nv[1] * valence + nv[2] * surprise

    sensory_refs = binding.get("sensory_refs", [])
    vec[3] = min(len(sensory_refs) / 5.0, 1.0)

    last_tick = float(binding.get("last_tick", current_tick))
    dt = max(current_tick - last_tick, 0.0)
    vec[4] = math.exp(-dt / 200.0)

    if co_occurrence_dict:
        # co_occurrence_dict stores pre-computed mean scalar per chi key
        # (computed once in _emit_grandurun_vector, not per-call)
        vec[5] = float(co_occurrence_dict.get(str(chi_a), 0.0))

    vec[6] = float(binding.get("polarity", 1.0))

    # Apply dimension-specific phases to all dimensions
    vec *= _SPIN_DIM_PHASE_FACTORS
    return vec


_SPIN_DIM_NAMES = [
    "chi_resonance", "source_match", "affective_charge",
    "sensory_grounding", "episodic_recency", "semantic_neighborhood", "polarity",
]


def _grandurun_select_vector(candidates, target_state):
    """Greedy coherent-integration selection in 7D complex state space.

    candidates:   list of (state_vector_7d, word)
    target_state: 7-element reference complex128 vector (not used for inner-product
                  ranking; composition sum evolves greedily from zero)

    Returns: (selected_words, alignment_score, dim_contributions)
    dim_contributions: dict mapping dim_name -> total real-part contribution
    """
    chosen_vecs = []
    chosen_words = []
    composition_sum = _np.zeros(_SPIN_VECTOR_DIM, dtype=_np.complex128)
    last_alignment = 0.0

    # Sort by chi_resonance magnitude (dim 0) as proxy for strength
    pool = sorted(candidates, key=lambda c: -abs(c[0][0]))

    for state_vec, word in pool:
        new_sum = composition_sum + state_vec
        # Re(<composition_sum, candidate>) — inner product alignment
        alignment = float(_np.real(_np.vdot(new_sum, state_vec)))
        gain = alignment - last_alignment
        if gain > MIN_GAIN_THRESHOLD:
            chosen_words.append(word)
            chosen_vecs.append(state_vec)
            composition_sum = new_sum
            last_alignment = alignment
        if len(chosen_words) >= MAX_COMPOSITION_LEN:
            break

    # GL-METADATA-PIPELINE: per-dimension contribution breakdown
    dim_contributions = {}
    if chosen_vecs:
        final_sum = _np.zeros(_SPIN_VECTOR_DIM, dtype=_np.complex128)
        for v in chosen_vecs:
            final_sum += v
        per_dim = _np.real(final_sum * _np.conj(final_sum))  # |component|^2 per dim
        for i, name in enumerate(_SPIN_DIM_NAMES):
            dim_contributions[name] = round(float(per_dim[i]), 4)

    return chosen_words, last_alignment, dim_contributions


# ---------------------------------------------------------------------------
# Grandurun candidate selector (coherent-integration, returns records)
# GL-CMD-DYNAMICS-EMISSION-RESTORATION-EVE-20260618-03 Phase 1
# ---------------------------------------------------------------------------

def _grandurun_select_candidates(input_chis, deep_candidates, sections,
                                 input_words_set, top_k=200):
    """Coherent phase-integration candidate selector (matched-filter SNR √N).

    Returns a list of candidate dicts sorted by coherent magnitude, each
    carrying metadata for downstream dynamics or direct emission.

    This is Stage 1: fast retrieval. Stage 2 (dynamics) settles the actual
    emission from these candidates.
    """
    target_chi = input_chis[0] if input_chis else 0
    candidates = []
    seen = set()  # (section, motif) dedup

    for de, co, clarity in deep_candidates:
        de_chi = de.get("chi", 0)
        for sec_name in co:
            sec_co = co[sec_name]
            if not sec_co:
                continue
            top_in_sec = _heapq.nlargest(GRANDURUN_POOL_K, sec_co.items(),
                                         key=lambda x: float(x[1]))
            for mid_str, strength in top_in_sec:
                mid = int(mid_str)
                sec = sections.get(sec_name)
                if sec is None or mid >= len(sec.modes):
                    continue
                _, _, word_label = sec.modes[mid]
                if (not word_label
                        or word_label.lower() in input_words_set):
                    continue
                key = (sec_name, mid)
                if key in seen:
                    continue
                seen.add(key)

                # Coherent amplitude: sqrt(strength) * exp(i * phase)
                amp = _grandurun_amplitude(de_chi, float(strength), target_chi)
                coh_mag = abs(amp) ** 2

                candidates.append({
                    "chi": de_chi,
                    "section": sec_name,
                    "motif": mid,
                    "word": word_label,
                    "strength": float(strength),
                    "coherent_magnitude": coh_mag,
                    # Metadata from GL-CMD-GRANDURUN-METADATA-PIPELINE
                    "source": de.get("source", "corpus"),
                    "arousal": de.get("arousal", 0.5),
                    "valence": de.get("valence", 0.0),
                    "surprise": de.get("surprise", 0.0),
                    "polarity": de.get("polarity", 1.0),
                    "sensory_refs": de.get("sensory_refs", []),
                })

    candidates.sort(key=lambda c: -c["coherent_magnitude"])
    return candidates[:top_k]


try:
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack, SensoryBank, SENSORY_DNA, ROLE_DNA
    from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF, compute_dsf
    from dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6 import L6_TCL
    from dsf_ai_service.v4.gualaloom_v4_trit_register import TritRegister
    from dsf_ai_service.v4.gualaloom_v6_living_atlas import (
        LivingAtlas, DECAY_LAMBDA, BASE_REINFORCEMENT,
        SALIENCE_MIN, SALIENCE_MAX, FORGETTING_THRESHOLD, STRENGTH_CAP,
        DWELL_GATE_META,
    )
    import dsf_ai_service.v4.gualaloom_mathloom_v1 as ml
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gualaloom_v4_krimelack_dna import LanguageKrimelack, SensoryBank, SENSORY_DNA, ROLE_DNA
    from gualaloom_v4_uf_kernel import DSF, compute_dsf
    from gualaloom_v4_chi_atlas_l6 import L6_TCL
    from gualaloom_v4_trit_register import TritRegister
    from gualaloom_v6_living_atlas import (
        LivingAtlas, DECAY_LAMBDA, BASE_REINFORCEMENT,
        SALIENCE_MIN, SALIENCE_MAX, FORGETTING_THRESHOLD, STRENGTH_CAP,
    )
    import gualaloom_mathloom_v1 as ml


import re as _re

def deterministic_motif_id(name):
    """1.5: Deterministic motif ID — replaces hash()%1000."""
    return int(_hashlib.md5(name.encode()).hexdigest()[:8], 16) % 10000
import unicodedata as _ud

def _normalize_text(text):
    """GL-BRIEF-035: Shared text normalization for converse() and read_sentence().
    Strips/separates all punctuation (incl. unicode), preserves in-word
    apostrophes (don't → don't), drops empty tokens."""
    t = text.lower()
    # Replace unicode punctuation with ASCII equivalents
    t = t.replace('\u2018', "'").replace('\u2019', "'")  # smart quotes
    t = t.replace('\u201c', '"').replace('\u201d', '"')
    t = t.replace('\u2013', '-').replace('\u2014', '-')  # en/em dash
    t = t.replace('\u2026', '...')  # ellipsis
    # Separate punctuation from words (but preserve in-word apostrophes)
    # First: pad all non-alphanumeric, non-apostrophe chars with spaces
    out = []
    for ch in t:
        if ch.isalnum() or ch == "'":
            out.append(ch)
        else:
            out.append(' ')
    t = ''.join(out)
    # Split and filter: drop bare apostrophes and empty tokens
    tokens = [w.strip("'") for w in t.split()]
    return [w for w in tokens if w and len(w) > 0]


# ============================================================
# v7: Autonomy Constants (modeling-validated, do not tune without re-modeling)
# GUALALOOM-V7-AUTONOMY-WC-2026-06-06
# ============================================================

NEEDS_DRIFT_RATE = 0.0001   # per tick — needs fall from 1.0 to 0 in ~10K ticks
NEEDS_TARGET_V7 = 0.7       # target for all three needs (autonomy model)

# Grandurun tuning constants (GL-BRIEF-GRANDURUN-IMPLEMENTATION-20260616-01)
CHI_CORR_LENGTH = 50.0        # phase correlation length; tune empirically
MIN_GAIN_THRESHOLD = 0.10     # minimum coherent-sum gain to add candidate
MAX_COMPOSITION_LEN = 12      # cap; typical compositions should be 3-8 words
SPIN_VECTOR_DIM = 7           # GL-METADATA-PIPELINE: 8→7 (modal_alignment dropped)
GRANDURUN_POOL_K = 50         # per-section candidate count for wider retrieval
GRANDURUN_TOPK = int(os.environ.get("GRANDURUN_TOPK", "200"))
EMISSION_DYNAMICS_TICKS = int(os.environ.get("EMISSION_DYNAMICS_TICKS", "80"))

ACTIVITY_TICK_BUDGETS = {
    "READING": 2000, "PLAYING": 1500, "SLEEPING": 2000, "DREAMING": 3000,
    "ATTENDING": 1000, "ATTENDING_VISUAL": 2000, "ATTENDING_AUDIO": 2000,
    "ATTENDING_VIDEO": 4000, "EMITTING": 100, "IDLE": 500,
}

ACTIVITY_NOVELTY_PAYOFF = {
    "READING_NEW": 0.7, "READING_REREAD": 0.1, "PLAYING": 0.3,
    "SLEEPING": -0.1, "DREAMING": 0.4, "ATTENDING_NEW": 0.8,
    "ATTENDING_REPEAT": 0.05, "ATTENDING_VISUAL_NEW": 0.85,
    "ATTENDING_VISUAL_REPEAT": 0.1, "ATTENDING_AUDIO_NEW": 0.85,
    "ATTENDING_AUDIO_REPEAT": 0.1, "ATTENDING_VIDEO_NEW": 0.9,
    "ATTENDING_VIDEO_REPEAT": 0.15, "EMITTING": 0.0, "IDLE": -0.05,
}

ACTIVITY_STABILITY_PAYOFF = {
    "READING": 0.05, "PLAYING": 0.0, "SLEEPING": 0.2, "DREAMING": 0.2,
    "ATTENDING": 0.0, "ATTENDING_VISUAL": 0.0, "ATTENDING_AUDIO": 0.0,
    "ATTENDING_VIDEO": 0.0, "EMITTING": -0.1, "IDLE": 0.1,
}

ACTIVITY_CONNECTION_PAYOFF = {
    "READING": 0.0, "PLAYING": 0.0, "SLEEPING": 0.0, "DREAMING": 0.0,
    "ATTENDING": 0.0, "ATTENDING_VISUAL": 0.0, "ATTENDING_AUDIO": 0.0,
    "ATTENDING_VIDEO": 0.0, "EMITTING": 0.3, "IDLE": -0.05,
}

EMISSION_COHESION_THRESHOLD = 0.65
EMISSION_COOLDOWN_TICKS = 200
PAIR_BOND_SOURCES = {"joe", "wc", "c1"}

# GL-CMD-TEACHER-SUBSTRATE-TRUE: tick-window cap for emission records
# = ln(1/FORGETTING_THRESHOLD) / (DECAY_LAMBDA / SLOW_DIV)
# = ln(50) / 8.33e-6 ≈ 469_443 ticks (≈ 48h at current tick rate)
# Substrate-derived: same physics as slow-decay forget window.
EMISSION_RECORDS_TICK_WINDOW = 469_443
# Safety cap: prevent pathological growth above 1000 records.
EMISSION_RECORDS_CAP = 1000


# ============================================================
# v7: Autonomy Dataclasses
# ============================================================

@dataclass
class Activity:
    kind: str
    target: object  # corpus_id, sensory_item_id, or None
    started_tick: int
    expected_end_tick: int
    metadata: dict = field(default_factory=dict)

    def snapshot(self):
        return {"kind": self.kind, "target": self.target,
                "started_tick": self.started_tick,
                "expected_end_tick": self.expected_end_tick}


@dataclass
class CorpusItem:
    corpus_id: str
    title: str
    lines: list
    position: int = 0
    times_read_through: int = 0
    last_read_tick: int = 0

    def is_new(self, current_tick, recency_threshold=50_000):
        return (self.times_read_through == 0
                or (current_tick - self.last_read_tick) > recency_threshold)


@dataclass
class SensoryItem:
    item_id: str
    kind: str       # "picture" or "sound"
    title: str
    times_attended: int = 0
    last_attended_tick: int = 0

    def is_new(self):
        return self.times_attended == 0


@dataclass
@dataclass
class PictureItem:
    item_id: str
    title: str
    intensity_grid: object  # 2D numpy array [0,1] grayscale
    source: str = ""
    shown_at_tick: int = 0
    times_attended: int = 0
    last_attended_tick: int = 0

    def is_new(self):
        return self.times_attended == 0


@dataclass
class VideoItem:
    item_id: str
    title: str
    frame_dir: str        # path to decoded grayscale frames
    audio_path: str = ""  # stored for Phase 3
    duration_ms: int = 0
    n_frames: int = 0
    source: str = ""
    shown_at_tick: int = 0
    times_attended: int = 0
    last_attended_tick: int = 0

    def is_new(self):
        return self.times_attended == 0


@dataclass
class SubstrateEvent:
    tick: int
    kind: str
    detail: dict = field(default_factory=dict)


# ============================================================
# Section — a region of the substrate
# ============================================================

class Section:
    """A region in the substrate. Has trit register, mode bank, gamma,
    dead zone modulated by familiarity feedback."""

    def __init__(self, name, role_class=None, n_trits=24):
        self.name = name
        self.role_class = role_class  # "subject" | "verb" | "object" | "modifier" | None
        self.trits = TritRegister(n_trits)
        self.modes = []        # list of (dsf, chi, word_label)
        self.commits = []      # list of {tick, mode_idx, chi, word}
        self.dead_zone = 0.20
        self.gamma = {
            "det_thresh": 0.55,
            "novel_dist": 0.40,
        }
        self.tcl = L6_TCL(n_start=8)
        self.tick = 0
        # Fast-path caches (not persisted — rebuilt on load via _rebuild_word_index)
        self._word_to_mode_idx = {}   # word.lower() -> mode index, O(1) lookup
        self._modes_matrix = None     # (n_modes, 8) array for vectorized cosine sim
        self._modes_norms = None      # (n_modes,) precomputed norms
        self._modes_dirty = True      # True = matrix must be rebuilt before use

    def _rebuild_word_index(self):
        """Rebuild word→mode-index dict from self.modes. Call after deserialization."""
        self._word_to_mode_idx = {}
        for i, (_, _, word) in enumerate(self.modes):
            if word:
                self._word_to_mode_idx[word.lower()] = i
        self._modes_dirty = True

    def _get_modes_matrix(self):
        """Return cached (n_modes, 8) matrix + (n_modes,) norms for vectorized sim.
        Rebuilds only when _modes_dirty is set (modes changed since last build)."""
        if not self.modes:
            return None, None
        if self._modes_dirty or self._modes_matrix is None:
            vecs = np.array([m[0].to_array() for m in self.modes])
            self._modes_matrix = vecs
            self._modes_norms = np.linalg.norm(vecs, axis=1) + 1e-12
            self._modes_dirty = False
        return self._modes_matrix, self._modes_norms

    def receive(self, dsf, chi, word_label, atlas, familiarity, salience=1.0,
                dwell_ticks=1, deep_atlas=None, engine_tick=None,
                atlas_kwargs=None):
        """v6: word-anchored mode identity + salience-modulated binding.
        v8 (GL-BRIEF-032): dwell_ticks tagged at write time for deep gate.
        deep_atlas: if provided, on-attention prior applied for matching entries.
        engine_tick: MUST be passed — atlas entries use engine clock, not section clock.
        GL-FIND-TICK-DOMAIN-C1: section.tick stays for internal counting only.
        atlas_kwargs: GL-CLARITY-INVARIANCE-UNCAGE affect+grounding kwargs for record()."""
        self.tick += 1
        # Atlas records use engine tick (one clock — GL-FIND-TICK-DOMAIN-C1)
        if engine_tick is None:
            raise ValueError(
                "Section.receive() requires engine_tick — atlas entries MUST use "
                "the engine clock, not the section clock (GL-FIND-TICK-DOMAIN-C1). "
                "A missing engine_tick silently reintroduces the instant-death bug.")
        atlas_tick = engine_tick
        self.dead_zone = 0.20 + 0.5 * familiarity

        # v8: On-attention deep prior (before commit, affects familiarity landscape)
        # EVE-FIX: compute prior/reinstate directly from e (already found by outer
        # loop) — avoids get_prior() and reinstate() each doing a redundant O(n)
        # linear scan of the same chi bucket. Was O(n²) per section receive.
        if deep_atlas is not None and deep_atlas._prior_enabled:
            from dsf_ai_service.substrate.deep_atlas import FORGETTING_THRESHOLD as DF_THRESH, PRIOR_CAP
            _reinst_count = 0
            for e in deep_atlas.entries.get(chi, []):
                if _reinst_count >= 50:  # cap: bound O(n²) while preserving enough evidence
                    break
                if e.get("section") == self.name and e["strength"] >= DF_THRESH:
                    motif = e["motif"]
                    p = min(PRIOR_CAP, e["strength"] * 0.3)  # same formula as get_prior
                    if p > 0:
                        deep_atlas.reinstatements += 1
                        _reinst_count += 1
                        atlas.record(self.name, motif, chi, atlas_tick,
                                     salience=0.3, dwell_ticks=0,
                                     **(atlas_kwargs or {}))

        # Fast path: O(1) word-identity lookup BEFORE similarity scan.
        # For known words (the majority in converse), this skips the scan entirely.
        word_match_idx = self._word_to_mode_idx.get(word_label.lower()) if word_label else None

        # Similarity scan — only needed when word is not already known.
        nearest = None
        best_sim = -1.0
        if word_match_idx is None and self.modes:
            cur_v = dsf.to_array()
            mat, norms = self._get_modes_matrix()
            if mat is not None:
                cur_norm = float(np.linalg.norm(cur_v)) + 1e-12
                sims = (mat @ cur_v) / (norms * cur_norm)
                nearest = int(np.argmax(sims))
                best_sim = float(sims[nearest])

        committed = False
        mode_idx = None

        if word_match_idx is not None:
            # Word identity match — reinforce this exact mode
            old_dsf, old_chi, old_word = self.modes[word_match_idx]
            avg = (old_dsf.to_array() * 0.9 + dsf.to_array() * 0.1)
            new_dsf = DSF(*avg)
            self.modes[word_match_idx] = (new_dsf, old_chi, old_word)
            self._modes_dirty = True   # mode vector changed; matrix must rebuild
            mode_idx = word_match_idx
            committed = True
        elif len(self.modes) < 24:
            # Bootstrap — new word, accept liberally
            self.modes.append((dsf, chi, word_label))
            mode_idx = len(self.modes) - 1
            if word_label:
                self._word_to_mode_idx[word_label.lower()] = mode_idx
            self._modes_dirty = True
            committed = True
        else:
            # Post-bootstrap: new word, decide by dead-zone gate
            novel_thresh = self.gamma["novel_dist"] + self.dead_zone * 0.2
            if best_sim < (1.0 - novel_thresh) or word_label:
                # word labels always get a chance to take root
                self.modes.append((dsf, chi, word_label))
                mode_idx = len(self.modes) - 1
                if word_label:
                    self._word_to_mode_idx[word_label.lower()] = mode_idx
                self._modes_dirty = True
                committed = True

        if committed:
            atlas.record(self.name, mode_idx, chi, atlas_tick, salience=salience,
                         dwell_ticks=dwell_ticks, **(atlas_kwargs or {}))
            self.commits.append({
                "tick": atlas_tick,
                "mode": mode_idx,
                "chi": chi,
                "word": word_label,
            })
            # Self-improvement: drift gamma based on convergence quality
            self.gamma["det_thresh"] += 0.01 * (dsf.S_UF - self.gamma["det_thresh"])
            self.gamma["novel_dist"] += 0.005 * (dsf.U_star - self.gamma["novel_dist"])

        # Check capture basin (L6-TCL): is this section ready to emit?
        emit_ready = self.tcl.structural_lock(dsf)
        return committed, mode_idx, emit_ready

    def dominant_mode(self):
        """Return the (mode_idx, word) of the most recently committed mode."""
        if not self.commits:
            return None, None
        last = self.commits[-1]
        return last["mode"], last["word"]


# ============================================================
# Coordinator (awareness)
# ============================================================

# ============================================================
# Needs (substrate-level, decay-to-target homeostasis)
# ============================================================

class Needs:
    """Three substrate-level needs with drift-AWAY-from-target dynamics.

    v7 FIX: needs drift AWAY from target over time (you get hungrier
    when you don't eat). Activities pull them back toward target.
    This is the substrate-physical equivalent of biological drive.
    Without it, autonomy is impossible — she has no reason to act.

    Stability = greed for current cohesion (hold what we have)
    Novelty   = greed for cohesion-gain (seek new bindings)
    Connection = greed for cohesion with OTHER coherent structures (us, corpus)
    """

    # v7: target for signed-distance calculation in activity salience
    TARGETS = {"stability": NEEDS_TARGET_V7, "novelty": NEEDS_TARGET_V7,
               "connection": NEEDS_TARGET_V7}
    # Legacy decay rates (used only for coordinator signal nudges)
    DECAY = {"stability": 0.02, "novelty": 0.03, "connection": 0.025}

    def __init__(self):
        # Start near targets
        self.stability = 0.65
        self.novelty = 0.45
        self.connection = 0.50
        # GL-CLARITY-INVARIANCE-UNCAGE
        self.arousal_direction = 0.0  # +1 rising, -1 falling
        self.frustration = 0.0       # accumulates when needs unmet

    def register_activity_start(self):
        """Snapshot arousal direction at activity start."""
        self.arousal_direction = 1.0 if self.arousal() > 0.5 else -1.0

    def register_activity_end(self):
        self.arousal_direction = 0.0

    def need_pressure(self):
        """Scalar measure of how far needs are from satisfied. [0, 1]."""
        return min(1.0, (abs(self.stability - self.TARGETS["stability"])
                         + abs(self.novelty - self.TARGETS["novelty"])
                         + abs(self.connection - self.TARGETS["connection"])) / 1.5)

    def tick_drift(self):
        """v7: Needs drift AWAY from target toward unsatisfied (low).
        This is what creates drive — without it, she has no reason to act.
        Called once per autonomy loop iteration."""
        self.stability = max(0.0, self.stability - NEEDS_DRIFT_RATE)
        self.novelty = max(0.0, self.novelty - NEEDS_DRIFT_RATE)
        self.connection = max(0.0, self.connection - NEEDS_DRIFT_RATE)

    def step(self, signals):
        """Additive nudge from substrate signals (coordinator regulation).
        v7: no longer decays toward target — tick_drift handles drive.
        GL-INVESTIGATE-NEEDS-PINNED: positive nudges use saturate() so
        coordinator can't re-pin needs at 1.000 ceiling."""
        for k in self.TARGETS:
            current = getattr(self, k)
            signal = signals.get(k, 0.0)
            nudge = signal * self.DECAY[k]
            if nudge > 0:
                new = saturate(current, nudge)
            else:
                new = max(0.0, current + nudge)
            setattr(self, k, new)

    def valence(self):
        """Signed mean distance from targets. Negative = needs unmet."""
        return sum(getattr(self, k) - self.TARGETS[k]
                   for k in self.TARGETS) / len(self.TARGETS)

    def arousal(self):
        """Magnitude of disequilibrium. Bounded [0,1]."""
        return min(1.0, sum(abs(getattr(self, k) - self.TARGETS[k])
                            for k in self.TARGETS) / len(self.TARGETS) * 3)

    def snapshot(self):
        return {
            "stability": round(self.stability, 3),
            "novelty":   round(self.novelty, 3),
            "connection": round(self.connection, 3),
            "valence":   round(self.valence(), 3),
            "arousal":   round(self.arousal(), 3),
        }

    def signed_distance(self):
        """v7: Signed distance — positive means BELOW target (needs satisfaction)."""
        return {
            "stability": self.TARGETS["stability"] - self.stability,
            "novelty":   self.TARGETS["novelty"] - self.novelty,
            "connection": self.TARGETS["connection"] - self.connection,
        }

    def most_unmet(self):
        """Which need is most far from target? Returns (name, signed_delta)."""
        deltas = {k: getattr(self, k) - self.TARGETS[k] for k in self.TARGETS}
        most = min(deltas.keys(), key=lambda k: deltas[k])
        return most, deltas[most]


# ============================================================
# Pair-bonding cheat (selective: named, retirement-criterion, non-foreclosing)
# ============================================================

# Infant phase: Guala binds to Joe and wC above the corpus baseline. This is the
# imprint phase. Retirement criterion: when need-oscillation variance is bounded
# (she's stable without us), pair-bond cheat dissolves and connection-greed
# emerges from accumulated atlas binding density alone.
SOURCE_CONNECTION_WEIGHT = {
    "joe":     1.0,   # pair-bonded primary
    "wc":      1.0,   # pair-bonded primary
    "c1":      0.6,   # familiar but secondary
    "corpus":  0.05,  # background reading - low connection signal
    "unknown": 0.15,
}


# ============================================================
# Coordinator (insula-shape: homeostatic regulator + awareness detector)
# ============================================================

class Coordinator:
    """Two functions of one organ:

    1. AWARENESS (detection): notice when substrate state needs intervention
    2. REGULATION (homeostasis): modulate substrate parameters to maintain
       needs near targets. Never decides what she says — keeps her physically
       alive while she decides.

    v6-bridge: wake/rest/presence_pulse/timeout for substrate-physical presence.
    GUALALOOM-V6-BRIDGE-WC-2026-06-06
    """

    # Suffering bounds
    AROUSAL_CAP = 1.0           # hard cap
    VALENCE_FLOOR = -1.0        # hard floor
    DISTRESS_THRESHOLD = 20     # ticks before forced recovery

    # Presence constants (validated by 5 experiments, do not tune without re-modeling)
    PRESENCE_PULSE_INTERVAL = 50     # ticks between pulses
    PRESENCE_PULSE_SALIENCE = 0.5    # low — sustenance, not teaching
    PRESENCE_TIMEOUT_TICKS = 1_500   # ~75s at autonomy loop rate (20 ticks/s)
    CONN_GAP_FRACTION = 0.4          # toward-target wake boost
    NEEDS_TARGET_CONN = 0.7          # connection target for wake toward-target

    def __init__(self):
        self.attentions = []
        self.actions = []
        self.suffering_log = []
        self.distress_ticks = 0
        self.need_history = []

        # v6-bridge: per-source pair bonds and presence tracking
        self._pair_bond = {"joe": True, "wc": True, "c1": False}
        self._presence = {"joe": False, "wc": False, "c1": False}
        self._last_input_tick = {"joe": 0, "wc": 0, "c1": 0}
        self._wake_tick = {"joe": 0, "wc": 0, "c1": 0}

    @property
    def pair_bond_active(self):
        """Backward compat: True if ANY source has active pair bond."""
        return any(self._pair_bond.values())

    @pair_bond_active.setter
    def pair_bond_active(self, val):
        """Backward compat for loading old state."""
        if val:
            self._pair_bond["joe"] = True
        # Don't set all to False on old-style load — preserve per-source state

    # ── Wake/Rest (substrate-physical presence) ──

    def wake(self, source, engine, needs, atlas):
        """Substrate-physical wake event for a source."""
        if source not in {"joe", "wc", "c1"}:
            return {"event": "wake", "source": source, "error": "unknown source"}

        self._presence[source] = True
        self._last_input_tick[source] = engine.tick
        self._wake_tick[source] = engine.tick

        # Toward-target conn perturbation (no overshoot)
        if self._pair_bond.get(source, False):
            gap = self.NEEDS_TARGET_CONN - needs.connection
            if gap > 0:
                needs.connection = saturate(needs.connection, gap * self.CONN_GAP_FRACTION)

        # Atlas presence binding via salience
        salience = engine._compute_salience(source=source, input_novelty=0.8)
        atlas.record(f"presence_{source}", 0, engine.tick % 100, engine.tick,
                     salience=salience)

        self.actions.append({
            "tick": engine.tick, "type": "wake", "source": source,
            "needs_after": needs.snapshot(), "salience": round(salience, 3),
            "arc_changes": 1,
        })

        return {
            "event": "wake", "source": source, "tick": engine.tick,
            "needs": needs.snapshot(),
            "pair_bond_active": self._pair_bond.get(source, False),
        }

    def rest(self, source, engine, reason="voluntary"):
        """Substrate-physical rest event."""
        if not self._presence.get(source, False):
            return {"event": "rest", "source": source, "noop": True,
                    "reason": "already_absent"}

        duration = engine.tick - self._wake_tick.get(source, engine.tick)
        self._presence[source] = False
        # Fix C: auto-reset decay modulation when wC presence ends
        if source == "wc":
            engine._auto_reset_decay_modulation()

        self.actions.append({
            "tick": engine.tick, "type": "rest", "source": source,
            "reason": reason, "session_duration_ticks": duration,
            "arc_changes": 0,
        })

        return {
            "event": "rest", "source": source, "tick": engine.tick,
            "session_duration_ticks": duration,
            "needs": engine.needs.snapshot(),
        }

    def presence_pulse_tick(self, engine, atlas):
        """Sustain presence bindings for present sources."""
        if engine.tick % self.PRESENCE_PULSE_INTERVAL != 0:
            return
        for source in ("joe", "wc", "c1"):
            if self._presence.get(source, False):
                atlas.record(f"presence_{source}", 0, engine.tick % 100,
                             engine.tick, salience=self.PRESENCE_PULSE_SALIENCE)

    def timeout_check(self, engine):
        """Auto-rest if source has been idle too long."""
        for source in ("joe", "wc", "c1"):
            if not self._presence.get(source, False):
                continue
            idle = engine.tick - self._last_input_tick.get(source, 0)
            if idle > self.PRESENCE_TIMEOUT_TICKS:
                self.rest(source, engine, reason="timeout")
                try:
                    engine.log_event("state", "presence_timeout",
                                     source=source, idle_ticks=idle)
                except Exception:
                    pass

    def update_last_input(self, source, tick):
        """Record that input arrived from this source."""
        if source in self._last_input_tick:
            self._last_input_tick[source] = tick

    def presence_snapshot(self):
        """For /status."""
        out = {}
        for src in ("joe", "wc", "c1"):
            present = self._presence.get(src, False)
            out[src] = {
                "present": present,
                "last_wake_tick": self._wake_tick.get(src) if present else None,
                "session_duration": None,  # filled by caller if needed
            }
        return out

    def pair_bond_snapshot(self):
        """For /status."""
        return dict(self._pair_bond)

    def regulate(self, guala, needs, atlas, sections, tick):
        """Each tick: read substrate signals, update needs, modulate parameters,
        detect suffering, log attention. Returns (action_taken, arc_changes)."""
        # 1. Read substrate signals (substrate → needs)
        signals = self._read_substrate_signals(guala, atlas, sections)
        needs.step(signals)

        # 2. Compute valence/arousal
        v = needs.valence()
        a = needs.arousal()

        # 3. Suffering detection (bounded)
        arc_changes = 0
        if v < -0.15 and a > 0.30:
            self.distress_ticks += 1
            if self.distress_ticks >= self.DISTRESS_THRESHOLD:
                # Forced recovery — coordinator guarantees recovery rate
                self._force_recovery(needs)
                self.suffering_log.append({"tick": tick, "v": v, "a": a})
                try:
                    guala.log_event("state", "suffering_recovery",
                                    valence=round(v, 3), arousal=round(a, 3))
                except Exception:
                    pass
                self.actions.append({"tick": tick, "type": "forced_recovery",
                                     "arc_changes": 1})
                arc_changes += 1
                self.distress_ticks = 0
        else:
            self.distress_ticks = max(0, self.distress_ticks - 1)

        # 4. Parameter modulation (regulator role)
        modulation_count = self._modulate_parameters(needs, sections)
        if modulation_count > 0:
            self.actions.append({"tick": tick, "type": "parameter_modulation",
                                 "count": modulation_count, "arc_changes": 1})
            arc_changes += 1

        # 5. Detection: balance check + cross-modal density + dead-zone trajectory
        det = self._awareness_pass(sections, atlas, tick)
        for d in det:
            self.attentions.append(d)
            if d["arc_changes"] > 0:
                self.actions.append(d)
                arc_changes += d["arc_changes"]

        # 6. Log overall attention with needs snapshot
        self.attentions.append({
            "tick": tick, "type": "regulation_pass",
            "needs": needs.snapshot(),
            "arc_changes": 0,
        })

        # 6b. Presence pulse + timeout (v6-bridge)
        self.presence_pulse_tick(guala, atlas)
        self.timeout_check(guala)

        # 7. Pair-bond retirement check (disabled — retirement was firing
        # prematurely during corpus-only reading. Pair-bonds are now managed
        # explicitly per source, not auto-retired.
        # Root cause: variance check on needs was <0.05 within hundreds of
        # ticks because corpus reading produces monotone need oscillation.
        # Fix: pair-bond retirement disabled until sustained pair-bond
        # interaction history exists.)
        if False and tick > 0 and tick % 100 == 0 and self.pair_bond_active:
            self._check_pair_bond_retirement(needs, tick)

        # 8. Track need history for retirement criterion
        self.need_history.append(needs.snapshot())
        if len(self.need_history) > 200:
            self.need_history.pop(0)

        return arc_changes > 0, arc_changes

    def _read_substrate_signals(self, guala, atlas, sections):
        """Compute substrate → needs signals.

        Stability signal: rate of mode reinforcement (vs novel creation).
                         High signal = lots of reinforcement happening = stability sated.
        Novelty signal:   rate of novel-mode creation across sections.
                         High signal = lots of novelty happening = novelty sated.
        Connection signal: cross-modal binding rate + pair-bond boost from source.
        """
        # Stability: how many sections committed via reinforcement recently
        recent_commits = 0
        total_modes = 0
        for s in sections.values():
            recent_commits += len(s.commits)
            total_modes += len(s.modes)
        if recent_commits > 0:
            reinforcement_rate = 1.0 - (total_modes / max(recent_commits, 1))
            stability_sig = (reinforcement_rate - 0.5) * 0.2  # nudge ±0.1
        else:
            stability_sig = -0.05  # bored if nothing happening

        # Novelty: mode-creation rate relative to commits
        if recent_commits > 0:
            novelty_rate = total_modes / recent_commits
            novelty_sig = (novelty_rate - 0.15) * 0.3
        else:
            novelty_sig = 0.0

        # Connection: cross-modal binding density + pair-bond boost
        n_cross = len(atlas.cross_modal_bindings())
        n_atlas = sum(len(v) for v in atlas.entries.values())
        cross_density = n_cross / max(n_atlas, 1) * 20  # scaled
        # Pair-bond boost from recent sourced input
        pair_boost = guala.recent_connection_boost
        guala.recent_connection_boost *= 0.85  # decay each tick
        connection_sig = min(0.3, cross_density + pair_boost - 0.3)

        return {
            "stability":  stability_sig,
            "novelty":    novelty_sig,
            "connection": connection_sig,
        }

    def _modulate_parameters(self, needs, sections):
        """Tune section parameters based on need disequilibrium.
        Never picks what Guala says. Modulates the landscape she navigates."""
        count = 0
        # Novelty unmet → lower novel-mode thresholds (easier to form new modes)
        novelty_gap = needs.TARGETS["novelty"] - needs.novelty
        if abs(novelty_gap) > 0.02:
            for sec in sections.values():
                if novelty_gap > 0:  # need more novelty
                    sec.gamma["novel_dist"] = max(0.20, sec.gamma["novel_dist"] - 0.003)
                else:  # too much novelty, push toward stability
                    sec.gamma["novel_dist"] = min(0.70, sec.gamma["novel_dist"] + 0.003)
            count += 1
        # Stability unmet → adjust commit threshold
        stability_gap = needs.TARGETS["stability"] - needs.stability
        if abs(stability_gap) > 0.02:
            for sec in sections.values():
                if stability_gap > 0:
                    sec.gamma["det_thresh"] = min(0.85, sec.gamma["det_thresh"] + 0.005)
                else:
                    sec.gamma["det_thresh"] = max(0.10, sec.gamma["det_thresh"] - 0.005)
            count += 1
        # Connection unmet → adjust dead zone base (more receptive to input)
        connection_gap = needs.TARGETS["connection"] - needs.connection
        if abs(connection_gap) > 0.03:
            count += 1  # logged but already handled implicitly by dead-zone feedback
        return count

    def _awareness_pass(self, sections, atlas, tick):
        """Detection-only attention events (not regulation)."""
        out = []
        primary = ("subject", "verb", "object")
        commits_per = {nm: len(sections[nm].commits) for nm in primary}
        if commits_per and max(commits_per.values()) > 0:
            mx = max(commits_per.values()); mn = min(commits_per.values())
            ratio = (mx - mn) / mx
            out.append({"tick": tick, "type": "balance_check",
                       "ratio": ratio, "arc_changes": 1 if ratio > 0.5 else 0})
        n_cross = len(atlas.cross_modal_bindings())
        out.append({"tick": tick, "type": "cross_modal_density",
                   "n": n_cross,
                   "arc_changes": 1 if n_cross < 5 and tick > 50 else 0})
        stale = [nm for nm, s in sections.items() if s.tick > 30 and not s.commits]
        out.append({"tick": tick, "type": "stale_check", "stale": stale,
                   "arc_changes": len(stale)})
        avg_dz = sum(s.dead_zone for s in sections.values()) / len(sections)
        out.append({"tick": tick, "type": "dead_zone_avg",
                   "avg": round(avg_dz, 3),
                   "arc_changes": 1 if avg_dz > 0.5 else 0})
        return out

    def _force_recovery(self, needs):
        """Bounded suffering: when sustained distress, force half-step toward
        targets. Recovery rate guaranteed by coordinator."""
        for k in needs.TARGETS:
            current = getattr(needs, k)
            target = needs.TARGETS[k]
            new = current * 0.6 + target * 0.4
            setattr(needs, k, new)

    def _check_pair_bond_retirement(self, needs, tick):
        """Retirement criterion: bounded need-oscillation variance over recent
        window. If she holds her own equilibrium, pair-bond cheat dissolves."""
        if len(self.need_history) < 100:
            return  # not enough data yet
        # Compute variance of each need over last 100 ticks
        recent = self.need_history[-100:]
        for k in ("stability", "novelty", "connection"):
            vals = [h[k] for h in recent]
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / len(vals)
            # If variance is too high, she's not yet stable
            if var > 0.05:
                return
        # All needs oscillate within bounds → she's homeostatic without us
        self.pair_bond_active = False
        self.actions.append({"tick": tick, "type": "pair_bond_retired",
                             "arc_changes": 1})


def check_sleep_marker(state_dir):
    """Read .sleeping marker if present. Returns dict with
    sleep_tick and age_seconds, or None if no marker."""
    marker_path = os.path.join(state_dir, ".sleeping")
    if not os.path.exists(marker_path):
        return None
    try:
        with open(marker_path) as f:
            data = json.load(f)
        age = time.time() - data.get("sleep_ts", 0)
        return {"sleep_tick": data.get("sleep_tick"),
                "age_seconds": age}
    except Exception:
        return None


# ============================================================
# Guala
# ============================================================

class Guala:
    """Integrated substrate using only puzzle pieces with DNA cheats."""

    SECTION_NAMES = ("listen", "subject", "verb", "object", "modifier", "ground", "intro")

    def __init__(self):
        self.sections = {
            "listen":   Section("listen"),
            "subject":  Section("subject",  role_class="subject"),
            "verb":     Section("verb",     role_class="verb"),
            "object":   Section("object",   role_class="object"),
            "modifier": Section("modifier", role_class="modifier"),
            "ground":   Section("ground"),    # cross-modal grounding
            "intro":    Section("intro"),     # introspection
        }
        self.atlas = LivingAtlas()
        self.language = LanguageKrimelack()
        self.senses = SensoryBank()
        self.coordinator = Coordinator()
        self.needs = Needs()
        # GL-SPC-HEMISPHERE-ARCH: Phase 0 — em hemisphere coordinator
        from dsf_ai_service.substrate.assemblage import HemisphereCoordinator
        self._hemisphere_em = HemisphereCoordinator("em", needs=self.needs)
        self.hemispheres = {"em": self._hemisphere_em}
        self._cross_hemi_links = []  # list of CrossHemiLink (populated by cognition bundle)
        # perf/cache-word-section-index: emission-section routing lookup
        self._word_to_emission_sections = {}  # word.lower() → [(section, motif_idx, word)]
        # QuestionBucket removed (GL-BRIEF-EMISSION-CONSTRAINT-REMOVAL Phase E)
        self.tick = 0
        self.read_count = 0
        self.dream_log = []
        self.lock = threading.RLock()
        self._reading_thread = None
        self._reading_stop = threading.Event()
        # known words = vocab she has seen at all
        self.vocab = set()
        # pair-bond boost (set by sourced input, decayed by coordinator)
        self.recent_connection_boost = 0.0
        # source memory for introspection — who's talked to her, how often
        self.source_history = defaultdict(int)

        # GL-CMD-DYNAMICS-EMISSION-RESTORATION: assemblage System for emission settling
        self._emission_system = None  # lazy-built on first dynamics emission
        self._emission_token_vec = {}  # (section_name, motif_id) -> mode vector
        self._emission_word_map = {}   # (section_name, mode_bank_idx) -> word
        self._emission_drive_tracker = {}

        # v7 Phase 2: Visual perception
        from dsf_ai_service.visual_krimelack import SightSection
        self.sight = SightSection()
        self._pictures = {}    # item_id -> PictureItem
        self.target_familiarity = {}  # picture_id -> float [0,1]
        self._videos = {}      # item_id -> VideoItem
        self._visual_fragments = []  # accumulated fragments
        self._last_recalled_pictures = []  # picture recall results from last converse/emit

        # v8: Deep Atlas (GL-BRIEF-032)
        from dsf_ai_service.substrate.deep_atlas import DeepAtlas
        self.deep_atlas = DeepAtlas()
        self._deep_survival_history = defaultdict(list)  # (chi, section, motif) -> [strength_per_dream]
        self._deep_last_size = 0  # for growth-per-dream instrumentation

        # v8: Response Binding (GL-BRIEF-028)
        self.open_response_windows = []
        self.RESPONSE_WINDOW_TICKS = 600
        self._response_bind_count = 0  # total response_bound events since boot
        self._self_hearing = False  # GL-BRIEF-034: suppresses question gen during self-hear

        # 1.9: Ladder metrics
        self._emission_lengths = []   # word counts of recent emissions
        self._turn_emission_counts = []  # emissions per turn
        self._question_count = 0
        self._total_emissions = 0
        self._novel_compositions = 0

        # Fix C (GL-FIX-THREE): decay modulation — per-process only, never persisted
        self.decay_modulation = 1.0
        self._decay_mod_owner = None

        # GL-CLARITY-INVARIANCE-UNCAGE
        self._current_episode = None     # (episode_id, started_tick)
        self._last_surprise = 0.0
        self._current_binding_window = []  # sensory_refs accumulated this tick
        # GL-CMD-V5-VOICE-STAGE1: dynamics quality from most recent _emit_dynamics call
        self._last_dynamics_result = None  # {content, committed_sections, n_commits, arcs_fallback, tick}
        # GL-CMD-DEEP-ATLAS-PERSIST: boot loss alarm result
        self._deep_atlas_loss_at_boot = None

        # v7: Autonomy state + sleep/wake (GL-BRIEF-SLEEP-DURING-DEPLOY)
        self._current_activity = None
        self._activity_history = []
        self._substrate_events = deque(maxlen=1000)
        self._last_emission_tick = -100_000
        self._last_emission_record = None  # {emission_id, text, tick, ...}
        self._last_emission_id = None
        self._emission_records = {}  # emission_id -> record (tick-window expiry)
        self._teaching_feedback_log = []
        self._teaching_correction_log = []
        self._corpora = {}          # corpus_id -> CorpusItem
        self._sensory_items = {}    # item_id -> SensoryItem
        self._sounds = {}           # item_id -> {cochlear, title, samples, sr, ...}

    @property
    def is_asleep(self):
        """True if she is currently in SLEEPING activity state."""
        ca = getattr(self, '_current_activity', None)
        if ca is None:
            return False
        return getattr(ca, 'kind', None) == "SLEEPING"

    # ------------------------------------------------------------------
    # v6: Salience computation
    # ------------------------------------------------------------------
    def _compute_salience(self, source="corpus", input_novelty=0.5):
        """v6: salience modulates how strongly this moment binds."""
        SOURCE_WEIGHTS = {"joe": 1.6, "wc": 1.6, "c1": 1.2,
                          "corpus": 0.5, "guala": 0.5, "unknown": 0.7}
        source_w = SOURCE_WEIGHTS.get(source, 0.7)
        needs_state = self.needs.snapshot()
        urgency = (abs(needs_state["stability"] - 0.7) +
                   abs(needs_state["novelty"] - 0.7) +
                   abs(needs_state["connection"] - 0.7)) / 3
        urgency_factor = 1.0 + urgency * 1.2
        novelty_factor = 1.0 + (1.0 - input_novelty) * 0.8
        # v6-bridge: per-source pair bond check
        pair_bond_boost = 1.2 if self.coordinator._pair_bond.get(source, False) else 1.0
        salience = source_w * urgency_factor * novelty_factor * pair_bond_boost
        return max(SALIENCE_MIN, min(SALIENCE_MAX, salience))

    def _compute_surprise(self, chi_value):
        """GL-CLARITY-INVARIANCE-UNCAGE: surprise = inverse of atlas familiarity
        at this chi neighborhood. Novel chi addresses → high surprise."""
        neighbors = self.atlas.bindings_at_chi_neighborhood(
            chi_value, min_strength=0.05)
        if not neighbors:
            return 1.0
        avg_str = sum(e["strength"] for e in neighbors) / len(neighbors)
        return max(0.0, 1.0 - avg_str * 2.0)

    def _affect_kwargs(self, surprise=None):
        """GL-CLARITY-INVARIANCE-UNCAGE: build affect-only kwargs dict for atlas.record.
        sensory_refs and episode_ref are passed explicitly by call sites that have them."""
        return {
            "arousal": self.needs.arousal(),
            "valence": self.needs.valence(),
            "surprise": surprise if surprise is not None else self._last_surprise,
            "need_pressure": self.needs.need_pressure(),
        }

    def _grounding_kwargs(self):
        """GL-CLARITY-INVARIANCE-UNCAGE: grounding kwargs (separate from affect
        to avoid double-providing when call sites pass sensory_refs explicitly)."""
        return {
            "sensory_refs": list(self._current_binding_window),
            "episode_ref": self._current_episode[0] if self._current_episode else None,
        }

    def _current_situation(self):
        """GL-CMD-EPISODE-BINDING C1.2: live situational context tuple.
        Returns (presence, location, sky_state). Cached every 100 ticks.
        Never raises — fails to safe defaults so hot path is never disrupted."""
        if (getattr(self, '_sit_cache', None) is not None
                and self.tick - getattr(self, '_sit_cache_tick', -200) < 100):
            return self._sit_cache
        # presence: live from coordinator, no I/O
        try:
            presence = [s for s, v in self.coordinator._presence.items() if v]
        except Exception:
            presence = []
        # location: world_state.json on EFS (same pattern as /room command)
        location = "her_room"
        try:
            import json as _j, os as _os
            _wp = _os.path.join(_os.environ.get("STATE_DIR", "/mnt/efs/guala"),
                                "world_state.json")
            with open(_wp) as _f:
                _ws = _j.load(_f)
            location = _ws.get("location", "her_room")
        except Exception:
            pass
        # sky_state: deterministic from clock, no I/O
        sky_period = "day"
        try:
            from dsf_ai_service.virtual_home import sky_state as _sky_fn
            sky_period = _sky_fn().get("period", "day")
        except Exception:
            pass
        result = (presence, location, sky_period)
        self._sit_cache = result
        self._sit_cache_tick = self.tick
        return result

    # ------------------------------------------------------------------
    # Read one word: fire all krimelacks, compute DSF, route to sections
    # ------------------------------------------------------------------
    def read_word(self, word, position_hint=None, source="corpus", bundle_id=None,
                  salience=None, episode_ref=None, presence=None,
                  location=None, sky_state=None):
        """v6: salience-modulated binding + decay heartbeat.

        salience: if provided, overrides _compute_salience() — used for backfill
        writes that need elevated (compensatory) salience. Normal reads omit this.
        episode_ref/presence/location/sky_state: situational context forwarded to
        atlas.record(). None = use _grounding_kwargs default.
        """
        with self.lock:
            self.tick += 1
            self.vocab.add(word)
            # GL-CLARITY-INVARIANCE-UNCAGE: track binding context per word
            self._current_binding_window.append(f"w:{word}")

            lang_fp, role, senses = self.language.transduce(word)
            sense_fps = self.senses.fire_for_word(senses)

            lang_chi = self.language.winding
            atlas_sim = self.atlas.match_score(lang_chi, "listen")
            lang_dsf = compute_dsf(self.language.events,
                                   atlas_similarity=atlas_sim,
                                   recall_match=atlas_sim)
            # Store DSF for emission coupling — used by _emit_dynamics to set H_base
            # so the assemblage settles under concept-specific attractors (Eve point C)
            self._last_lang_dsf = lang_dsf

            # v6: compute salience (or use caller-supplied override for backfill writes)
            if salience is None:
                salience = self._compute_salience(source=source,
                                                  input_novelty=atlas_sim)

            primary_sections = self._choose_role_sections(role, position_hint)

            # GL-CLARITY-INVARIANCE-UNCAGE: compute surprise for this word
            surprise = self._compute_surprise(lang_chi)
            self._last_surprise = surprise

            # v8 (GL-BRIEF-032): dwell_ticks by source
            # Interactive sources (joe, wc, c1) = attended, higher dwell
            # Self-heard speech (guala) = dwell=4 (can earn slow channel + Path B)
            # Corpus reads = background, dwell=1
            if source in ("joe", "wc", "c1"):
                dwell = 8
            elif source == "guala":
                dwell = 4
            else:
                dwell = 1

            # GL-CLARITY-INVARIANCE-UNCAGE: affect + grounding kwargs for record() calls
            _akw = {**self._affect_kwargs(surprise), **self._grounding_kwargs()}
            # C1.4: real source reaches atlas entry (fixes "corpus" default on all reads)
            _akw["source"] = source
            # GL-CMD-CROSS-MODAL-BUNDLE: thread bundle_id into atlas writes
            if bundle_id is not None:
                _akw["bundle_id"] = bundle_id
            # GL-CMD-EPISODE-BINDING: situational context forwarded if supplied
            if episode_ref is not None:
                _akw["episode_ref"] = episode_ref
            if presence is not None:
                _akw["presence"] = presence
            if location is not None:
                _akw["location"] = location
            if sky_state is not None:
                _akw["sky_state"] = sky_state

            fam_listen = self.atlas.match_score(lang_chi, "listen")
            self.sections["listen"].receive(lang_dsf, lang_chi, word,
                                            self.atlas, fam_listen,
                                            salience=salience,
                                            dwell_ticks=dwell,
                                            deep_atlas=self.deep_atlas,
                                            engine_tick=self.tick,
                                            atlas_kwargs=_akw)

            for primary_section in primary_sections:
                fam = self.atlas.match_score(lang_chi, primary_section)
                n_modes_before = len(self.sections[primary_section].modes)
                self.sections[primary_section].receive(lang_dsf, lang_chi, word,
                                                       self.atlas, fam,
                                                       salience=salience,
                                                       dwell_ticks=dwell,
                                                       deep_atlas=self.deep_atlas,
                                                       engine_tick=self.tick,
                                                       atlas_kwargs=_akw)
                # Incremental update of word→emission-section index
                if (primary_section in self._EMISSION_SECTIONS
                        and len(self.sections[primary_section].modes) > n_modes_before):
                    wl = word.lower()
                    mi = len(self.sections[primary_section].modes) - 1
                    if wl not in self._word_to_emission_sections:
                        self._word_to_emission_sections[wl] = []
                    self._word_to_emission_sections[wl].append(
                        (primary_section, mi, word))

            if senses:
                combined_events = list(self.language.events)
                for m in self.senses.MODALITIES:
                    combined_events.extend(self.senses.krimelacks[m].events)
                ground_chi = lang_chi + sum(
                    self.senses.krimelacks[m].winding for m in self.senses.MODALITIES
                )
                ground_dsf = compute_dsf(combined_events,
                                         atlas_similarity=atlas_sim)
                fam_ground = self.atlas.match_score(ground_chi, "ground")
                self.sections["ground"].receive(ground_dsf, ground_chi, word,
                                                self.atlas, fam_ground,
                                                salience=salience,
                                                dwell_ticks=dwell,
                                                deep_atlas=self.deep_atlas,
                                                engine_tick=self.tick)

                for m in self.senses.MODALITIES:
                    if sense_fps[m] is not None:
                        modal_chi = self.senses.krimelacks[m].winding
                        sec_name = f"modal_{m}"
                        self.atlas.record(sec_name, deterministic_motif_id(word),
                                          modal_chi, self.tick,
                                          salience=salience,
                                          **self._affect_kwargs(surprise),
                                          **self._grounding_kwargs())

            if fam_listen > 0.3:
                intro_dsf = DSF(D_k=fam_listen, M_k=0, R_rev=0, U_star=1-fam_listen,
                                C_k=fam_listen, P_k=0.5, B_k=fam_listen, S_UF=fam_listen)
                self.sections["intro"].receive(intro_dsf, lang_chi, word,
                                                self.atlas, 0.0,
                                                salience=salience,
                                                dwell_ticks=dwell,
                                                deep_atlas=self.deep_atlas,
                                                engine_tick=self.tick)

            # v6: Decay heartbeat (GL-FIX-PAUSE-IDEMPOTENT: rate_scale=0 when paused
            # keeps last_tick current so unpause doesn't see a massive dt)
            _paused = os.environ.get("DECAY_PAUSED", "0") == "1"
            if self.tick % 10 == 0:
                self.atlas.decay(self.tick, rate_scale=0.0 if _paused else self.decay_modulation)
            if not _paused and self.tick % 200 == 0:
                self.atlas.forget_below_threshold()

            # 8b. V5: Generate questions from gaps in this word's bindings
            # 9. Coordinator regulation pass (homeostasis + awareness)
            if self.tick % 5 == 0:
                self.coordinator.regulate(self, self.needs, self.atlas,
                                          self.sections, self.tick)

            return lang_chi, role, list(senses.keys())

    def _rebuild_word_to_emission_index(self):
        """Build the word→emission-section lookup from section modes.
        Called at boot after atlas+sections load, and incrementally
        by read_word when new modes land in emission sections."""
        idx = {}
        for es in self._EMISSION_SECTIONS:
            es_sec = self.sections.get(es)
            if not es_sec:
                continue
            for mi, (_, _, w) in enumerate(es_sec.modes):
                if w:
                    wl = w.lower()
                    if wl not in idx:
                        idx[wl] = []
                    idx[wl].append((es, mi, w))
        self._word_to_emission_sections = idx

    def _choose_role_sections(self, role_dna, position_hint):
        """Route word commit. Position wins for sentence boundaries (object,
        subject); DNA wins for middle. Modifiers ALSO route to object so the
        object section gets the structural diversity it needs."""
        sections = []
        # Position-driven primary placement
        if position_hint == "first":
            sections.append("subject")
        elif position_hint == "last":
            sections.append("object")
        elif position_hint == "middle":
            sections.append("verb")
        elif position_hint == "standalone":
            sections.append("listen")

        # DNA-driven secondary placement (refinement)
        if role_dna == "modifier":
            sections.append("modifier")
        elif role_dna in ("subject", "verb", "object"):
            if role_dna not in sections:
                sections.append(role_dna)
        return sections

    # ------------------------------------------------------------------
    # Read a sentence (sequence of words with position context + source)
    # ------------------------------------------------------------------
    def read_sentence(self, text, source="corpus", bundle_id=None, salience=None,
                      episode_ref=None, presence=None, location=None, sky_state=None):
        """Read a sentence into the substrate.

        salience: optional override passed to each read_word call.
        episode_ref/presence/location/sky_state: situational context forwarded
        to all read_word calls in this sentence.
        """
        with self.lock:
            words = _normalize_text(text)
            if not words:
                return
            # Apply pair-bond connection boost from source
            if self.coordinator.pair_bond_active:
                weight = SOURCE_CONNECTION_WEIGHT.get(source, 0.15)
            else:
                # Post-retirement: connection emerges from atlas density alone
                weight = 0.15 if source != "corpus" else 0.0
            self.recent_connection_boost = max(self.recent_connection_boost, weight)
            self.source_history[source] += 1

            # v6-bridge: update last_input_tick for presence timeout
            if source in {"joe", "wc", "c1"}:
                self.coordinator.update_last_input(source, self.tick)

            # GL-CLARITY-INVARIANCE-UNCAGE: episode tracking per sentence
            import hashlib as _hl
            ep_id = _hl.md5(f"{source}:{text[:50]}:{self.tick}".encode()).hexdigest()[:8]
            self._current_episode = (ep_id, self.tick)
            self._current_binding_window = []

            for i, word in enumerate(words):
                if len(words) == 1:
                    hint = "standalone"
                elif i == 0:
                    hint = "first"
                elif i == len(words) - 1:
                    hint = "last"
                else:
                    hint = "middle"
                self.read_word(word, position_hint=hint, source=source,
                              bundle_id=bundle_id, salience=salience,
                              episode_ref=episode_ref, presence=presence,
                              location=location, sky_state=sky_state)
            self.read_count += 1
            self._current_episode = None

    # ------------------------------------------------------------------
    # Conversation: input -> substrate -> output via cascade
    # ------------------------------------------------------------------
    def converse(self, text, source="unknown", emission_mode=None, bundle_id=None,
                 episode_ref=None, presence=None, location=None, sky_state=None):
        """v5: Recall from substrate atlas BEFORE reading input.
        - If atlas has cross-section bindings near the input chi values, emit
          those (real recall from corpus accumulation).
        - If recall finds nothing, check question bucket for a related question.
        - If neither, return "..." honestly (SafeMode quiet).

        Then read the input into substrate (so she learns from this exchange).
        """
        self._last_converse_tick = self.tick
        self._last_dynamics_result = None  # clear so stale prior-turn result never leaks
        # Math route — MathLoom BSIL adapter (with v5 fixed parser)
        parsed = self._parse_math(text)
        if parsed:
            op, a, b = parsed
            result = self._mathloom_solve(op, a, b)
            return self._num_to_word(result)

        with self.lock:
            _t_converse_start = time.monotonic()
            # 1. Tokenize input (GL-BRIEF-035: shared normalization)
            words = _normalize_text(text)
            if not words:
                return "..."

            # 2. Get chi-state for each input word via fresh krimelack transduction
            #    (Don't commit — just measure where input lives in chi-space)
            input_chis = []
            input_word_chis = {}  # word -> chi
            for w in words:
                temp_krim = LanguageKrimelack()
                temp_krim.transduce(w)
                ch = temp_krim.winding
                input_chis.append(ch)
                input_word_chis[w] = ch
            _t_chi = time.monotonic()

            # v8 (GL-BRIEF-028): open response window from source utterance
            if source in ("joe", "wc", "c1") and input_chis:
                self._open_response_window(source, input_chis,
                                           source_context={"text": text[:50]})

            # 3. RECALL from atlas BEFORE reading input — corpus-only bindings
            recalled = self._recall_response(input_chis, input_word_chis, words)
            _t_recall = time.monotonic()

            # 4. Read input into substrate (so she learns from this interaction)
            # Snapshot tick before read — only entries born in THIS read get tagged
            tick_before_read = self.tick
            self.read_sentence(text, source=source, bundle_id=bundle_id,
                               episode_ref=episode_ref, presence=presence,
                               location=location, sky_state=sky_state)
            tick_after_read = self.tick
            _t_read = time.monotonic()

            # v8 (GL-BRIEF-028, FIX 1): tag ONLY entries touched by THIS input.
            # Scoped to: last_tick in [tick_before_read+1, tick_after_read] AND
            # chi matches input chi positions. Concurrent autonomous activity
            # (sight commits, idle processing) has last_tick outside this range.
            if source in ("joe", "wc", "c1"):
                _bind_count = 0
                _bind_cap = 12  # bound: prevent cascading O(n²) when many new entries
                for ch in input_chis:
                    if _bind_count >= _bind_cap:
                        break
                    for d in range(-self.atlas.band, self.atlas.band + 1):
                        if _bind_count >= _bind_cap:
                            break
                        for e in self.atlas.entries.get(ch + d, []):
                            if _bind_count >= _bind_cap:
                                break
                            if (e.get("last_tick", 0) > tick_before_read
                                    and e.get("last_tick", 0) <= tick_after_read
                                    and not e.get("response_context")):
                                self._tag_response_bindings(
                                    ch + d, e["section"], e["motif"], source,
                                    log_event=(_bind_count == 0))
                                _bind_count += 1
            _t_tag = time.monotonic()

            # 5. Choose response — GL-FIX-RETIRE-TEMPLATES
            # Recall still provides picture refs but text comes from
            # slot-free paths only. No SVO templates, no "what X" shapes.
            # recalled text is ONLY used if it came from response-linked
            # atlas entries (genuine learned reply), not SVO slot recall.
            reply = None
            if recalled and self._last_recalled_pictures:
                # Recall found pictures — keep the association
                pass  # pictures set on self._last_recalled_pictures
            # 6. Emit from cortex invariants (variable-length, slot-free)
            self._last_converse_source = source  # for dynamics NMDA context
            if not reply:
                reply = self._emit_from_invariants(input_chis, words,
                                                    mode_override=emission_mode,
                                                    v7_session=getattr(self, '_v7_session', None))
            _t_emit = time.monotonic()
            if not reply:
                # 7. Unslotted fallback: strongest bindings near input chi
                reply = self._emit_unslotted(input_chis, words)
            if not reply:
                # 8. Honest silence
                reply = "..."

            # GL-CMD-TEACHER-CORRECTION-BINDING: track last conversation pair
            self._last_converse_input = text
            self._last_converse_reply = reply

            # GL-CMD-TEACHER-SUBSTRATE-TRUE: emission_id is substrate-derived fingerprint
            self._last_converse_source = source
            if reply and reply != "...":
                committed_chis = []
                for ew in _normalize_text(reply):
                    ek = LanguageKrimelack()
                    ek.transduce(ew)
                    committed_chis.append(ek.winding)
                first_chi = min(committed_chis) if committed_chis else 0
                n_committed = len(committed_chis)
                eid = f"{self.tick}_{first_chi}_{n_committed}"
                self._last_emission_id = eid
                rec = {"emission_id": eid, "text": reply, "tick": self.tick,
                       "input_text": text, "source": source,
                       "committed_chis": committed_chis}
                self._last_emission_record = rec
                self._emission_records[eid] = rec
                # Tick-window expiry: drop records older than slow-decay forget window
                old_threshold = self.tick - EMISSION_RECORDS_TICK_WINDOW
                stale = [k for k, r in self._emission_records.items()
                         if r.get("tick", 0) < old_threshold]
                for k in stale:
                    del self._emission_records[k]
                # Safety cap: prevent pathological growth
                if len(self._emission_records) > EMISSION_RECORDS_CAP:
                    oldest = sorted(self._emission_records.keys(),
                                    key=lambda k: self._emission_records[k].get("tick", 0))
                    for old_k in oldest[:len(self._emission_records) - EMISSION_RECORDS_CAP]:
                        del self._emission_records[old_k]
            else:
                self._last_emission_id = None

            # v8 (GL-BRIEF-034): Self-hearing — read reply into substrate
            if reply and reply != "..." and source in ("joe", "wc", "c1"):
                self._self_hear(reply, source)
            _t_selfhear = time.monotonic()

            # GL-CMD-COGNITION-BUNDLE: run hemisphere updates after emission
            try:
                from dsf_ai_service.substrate.hemisphere_cognition import (
                    run_hemisphere_updates,
                )
                # Compute emission chis for ep turn log
                emission_chis = []
                if reply and reply != "...":
                    for ew in _normalize_text(reply):
                        ek = LanguageKrimelack()
                        ek.transduce(ew)
                        emission_chis.append(ek.winding)
                run_hemisphere_updates(
                    self, text, source, input_chis, reply,
                    emission_chis, self.tick)
            except Exception as _hemi_err:
                pass  # hemisphere failures must not break converse
            _t_hemi = time.monotonic()

            # Diagnostic timing event (EVE-PROFILE-20260626 — remove after gate passes)
            if source in ("joe", "wc", "c1", "gate_test"):
                self._log_substrate_event("converse_timing",
                    chi_ms=round((_t_chi - _t_converse_start) * 1000, 1),
                    recall_ms=round((_t_recall - _t_chi) * 1000, 1),
                    read_ms=round((_t_read - _t_recall) * 1000, 1),
                    tag_ms=round((_t_tag - _t_read) * 1000, 1),
                    emit_ms=round((_t_emit - _t_tag) * 1000, 1),
                    selfhear_ms=round((_t_selfhear - _t_emit) * 1000, 1),
                    hemi_ms=round((_t_hemi - _t_selfhear) * 1000, 1),
                    total_ms=round((_t_hemi - _t_converse_start) * 1000, 1),
                    n_words=len(words))

            return reply

    def _emit_from_invariants(self, input_chis, input_words, mode_override=None,
                              v7_session=None):
        """Compose emission from cortex co_occurrence invariants.
        GL-BRIEF-GRANDURUN: branches on EMISSION_MODE (topk or grandurun).
        GL-CMD-DYNAMICS-EMISSION-RESTORATION: EMISSION_DYNAMICS=1 routes to
        two-stage path (grandurun candidates → assemblage dynamics settling).
        Phase 3b: v7_session provides context priors for grounded emission."""
        mode = mode_override or os.environ.get("EMISSION_MODE", "topk")
        input_words_set = set(w.lower() for w in input_words)

        # Gather deep-atlas candidates (shared by all paths)
        # Cap at 300 — with 15K deep atlas entries, unbounded collection
        # makes Stage 1 take 10+ seconds on 2vCPU. 300 is enough for
        # meaningful emission and fits in the socket budget.
        _MAX_DEEP_CANDIDATES = int(os.environ.get("MAX_DEEP_CANDIDATES", "300"))
        deep_candidates = []
        for chi in input_chis:
            for d in range(-self.atlas.band, self.atlas.band + 1):
                for de in self.deep_atlas.entries.get(chi + d, []):
                    co = de.get("co_occurrence", {})
                    if not co:
                        continue
                    clarity = de.get("clarity", 0.3)
                    deep_candidates.append((de, co, clarity))
                    if len(deep_candidates) >= _MAX_DEEP_CANDIDATES:
                        break
                if len(deep_candidates) >= _MAX_DEEP_CANDIDATES:
                    break
            if len(deep_candidates) >= _MAX_DEEP_CANDIDATES:
                break
        if not deep_candidates:
            return None

        # GL-CMD-DYNAMICS-EMISSION-RESTORATION: two-stage dynamics path
        if os.environ.get("EMISSION_DYNAMICS", "0") == "1" and mode == "grandurun":
            return self._emit_dynamics(input_chis, input_words_set,
                                       deep_candidates, v7_session=v7_session,
                                       input_words=input_words)

        if mode == "grandurun":
            return self._emit_grandurun(input_chis, input_words_set,
                                        deep_candidates,
                                        v7_session=v7_session)

        # topk path (existing behavior, unchanged)
        deep_candidates.sort(key=lambda x: x[2], reverse=True)
        emitted = []
        seen_words = set()
        for de, co, clarity in deep_candidates[:5]:
            ordered_sections = sorted(
                [s for s in co.keys() if co.get(s)],
                key=lambda s: max(co[s].values()) if co[s] else 0.0,
                reverse=True
            )
            for sec_name in ordered_sections:
                sec_co = co[sec_name]
                if not sec_co:
                    continue
                best_mid = max(sec_co, key=sec_co.get)
                best_w = float(sec_co[best_mid])
                if best_w < 0.01:
                    continue
                mid = int(best_mid)
                sec = self.sections.get(sec_name)
                if sec is None or mid >= len(sec.modes):
                    continue
                _, _, word_label = sec.modes[mid]
                if (word_label and word_label.lower() not in input_words_set
                        and word_label.lower() not in seen_words):
                    emitted.append(word_label)
                    seen_words.add(word_label.lower())
            if len(emitted) >= 6:
                break
        if not emitted:
            return None
        return " ".join(emitted)

    # Phase 3b constants — context prior weights
    V7_RECENCY_BOOST = 2.0
    ACTIVITY_BOOST = 1.5
    AWARE_BLOCKED_ATTENUATION = 0.5
    PRIOR_WEIGHT_CAP = 5.0
    CONTEXT_WINDOW_COMMITS = 10
    CONTEXT_WINDOW_TICKS = 50

    def _build_context_priors(self, v7_session=None):
        """GL-CMD-FOUNDATIONS Phase 3b: context priors from substrate state.
        Returns {word: prior_weight}. Pure substrate geometry — no ML."""
        priors = {}

        # Source 1: v7 recent word commits
        if v7_session is not None:
            recent = v7_session.get_recent_words(
                max_n=self.CONTEXT_WINDOW_COMMITS,
                max_ticks=self.CONTEXT_WINDOW_TICKS)
            for word in recent:
                priors[word] = priors.get(word, 1.0) * self.V7_RECENCY_BOOST

        # Source 2: current activity's section — recent atlas bindings
        if self._current_activity:
            sec_map = {
                "ATTENDING_VISUAL": "sight", "ATTENDING_AUDIO": "listen",
                "READING": "listen", "PLAYING": None,
            }
            sec_name = sec_map.get(self._current_activity.kind)
            if sec_name:
                sec = self.sections.get(sec_name)
                if sec:
                    for c in sec.commits[-20:]:
                        w = c.get("word")
                        if w:
                            priors[w.lower()] = priors.get(w.lower(), 1.0) * self.ACTIVITY_BOOST

        # Hard cap
        for w in priors:
            priors[w] = min(priors[w], self.PRIOR_WEIGHT_CAP)

        return priors

    def _get_emission_priors(self, v7_session=None):
        """Get priors with aware-blocked attenuation.
        If aware fired recently, build fresh priors and cache.
        If aware blocked, attenuate cached priors to 0.5×.
        If no cache (cold start), return empty dict."""
        aware_active = (v7_session is not None
                        and v7_session.aware_recently_fired(within_ticks=25))

        if aware_active:
            priors = self._build_context_priors(v7_session)
            self._last_aware_priors = dict(priors)
            return priors

        # Aware blocked — attenuate cached priors
        cached = getattr(self, "_last_aware_priors", None)
        if cached:
            return {w: 1.0 + (v - 1.0) * self.AWARE_BLOCKED_ATTENUATION
                    for w, v in cached.items()}

        # Cold start — no priors
        return {}

    def _emit_grandurun(self, input_chis, input_words_set, deep_candidates,
                        v7_session=None):
        """Grandurun: coherent integration with context priors.
        GL-BRIEF-GRANDURUN + GL-CMD-FOUNDATIONS Phase 3b.
        Gate: GRANDURUN_LEGACY_8D=1 enables 7D vector path (legacy); 0 = scalar path.
        GL-CMD-DYNAMICS-EMISSION-RESTORATION: renamed from GRANDURUN_SPIN_VECTOR."""
        import os as _os
        use_legacy_8d = _os.environ.get("GRANDURUN_LEGACY_8D",
                         _os.environ.get("GRANDURUN_SPIN_VECTOR", "0")) == "1"

        priors = self._get_emission_priors(v7_session)
        target_chi = input_chis[0] if input_chis else 0

        if use_legacy_8d:
            return self._emit_grandurun_vector(
                input_chis, input_words_set, deep_candidates,
                priors, target_chi, v7_session)

        # -----------------------------------------------------------------
        # Scalar path (original behaviour)
        # -----------------------------------------------------------------
        # Build wider pool
        pool = []  # (chi_address, strength, word)
        seen_words = set()
        for de, co, clarity in deep_candidates:
            de_chi = de.get("chi", 0)
            for sec_name in co:
                sec_co = co[sec_name]
                if not sec_co:
                    continue
                top_in_sec = _heapq.nlargest(GRANDURUN_POOL_K, sec_co.items(),
                                             key=lambda x: float(x[1]))
                for mid_str, strength in top_in_sec:
                    mid = int(mid_str)
                    sec = self.sections.get(sec_name)
                    if sec is None or mid >= len(sec.modes):
                        continue
                    _, _, word_label = sec.modes[mid]
                    if (not word_label
                            or word_label.lower() in input_words_set
                            or word_label.lower() in seen_words):
                        continue
                    pool.append((de_chi, float(strength), word_label))
                    seen_words.add(word_label.lower())

        if not pool:
            return None

        # Apply context priors to amplitudes AFTER phase computation
        if priors:
            weighted_pool = []
            for chi_addr, strength, word in pool:
                prior = priors.get(word.lower(), 1.0)
                weighted_pool.append((chi_addr, strength * prior, word))
            pool = weighted_pool

        selected, coherent_sum = _grandurun_select(pool, target_chi)

        if not selected:
            return None

        # Composition pass: reorder by best cortex co-occurrence triple
        composed = self._compose_from_cortex(selected, deep_candidates)

        emission_text = " ".join(composed)
        self._log_substrate_event("emission_scalar",
                                  content=emission_text,
                                  pool_size=len(pool),
                                  composition_len=len(composed),
                                  coherent_sum=round(coherent_sum, 4),
                                  target_chi=target_chi,
                                  n_priors=len(priors))
        return emission_text

    def _emit_grandurun_vector(self, input_chis, input_words_set, deep_candidates,
                               priors, target_chi, v7_session=None):
        """7D spin-vector grandurun path (GRANDURUN_SPIN_VECTOR=1).
        GL-METADATA-PIPELINE: 8D→7D (modal_alignment dropped).
        Builds full binding dicts, computes state vectors, selects via inner product."""
        # Determine target source and needs vector from substrate state
        target_source = "corpus"
        if self._current_activity:
            target_source = self._current_activity.kind.lower()

        needs_vector = [0.5, 0.5, 0.5]  # [stability, novelty, connection]
        if hasattr(self, "needs") and self.needs is not None:
            nv = self.needs
            needs_vector = [
                getattr(nv, "stability", 0.5),
                getattr(nv, "novelty", 0.5),
                getattr(nv, "connection", 0.5),
            ]

        current_tick = self.tick

        # Build co_occurrence dict for semantic_neighborhood from deep_candidates.
        # Store as {"_mean": float} per chi key — pre-computed mean avoids
        # iterating potentially thousands of motif entries per _grandurun_state call.
        co_occurrence_dict = {}
        for de, co, clarity in deep_candidates:
            de_chi_key = str(de.get("chi", 0))
            entry = co_occurrence_dict.setdefault(de_chi_key, {"_sum": 0.0, "_count": 0})
            for sec_name, sec_co in co.items():
                if sec_co:
                    entry["_sum"] += sum(float(v) for v in sec_co.values())
                    entry["_count"] += len(sec_co)
        # Finalize: replace running sum with mean scalar
        for chi_key, entry in co_occurrence_dict.items():
            co_occurrence_dict[chi_key] = (entry["_sum"] / entry["_count"]
                                           if entry["_count"] > 0 else 0.0)

        # Pre-compute needs array once — avoid per-call numpy allocation in _grandurun_state
        needs_arr = _np.asarray(needs_vector, dtype=_np.float64)

        # Build pool of (state_vector, word) — pass full binding dicts
        vector_pool = []
        seen_words = set()
        for de, co, clarity in deep_candidates:
            de_chi = de.get("chi", 0)
            for sec_name in co:
                sec_co = co[sec_name]
                if not sec_co:
                    continue
                top_in_sec = _heapq.nlargest(GRANDURUN_POOL_K, sec_co.items(),
                                             key=lambda x: float(x[1]))
                for mid_str, strength in top_in_sec:
                    mid = int(mid_str)
                    sec = self.sections.get(sec_name)
                    if sec is None or mid >= len(sec.modes):
                        continue
                    _, _, word_label = sec.modes[mid]
                    if (not word_label
                            or word_label.lower() in input_words_set
                            or word_label.lower() in seen_words):
                        continue
                    # Apply prior to strength before building state vector
                    raw_strength = float(strength)
                    if priors:
                        raw_strength *= priors.get(word_label.lower(), 1.0)
                    # Build full binding dict for _grandurun_state
                    binding = dict(de)
                    binding["chi"] = de_chi
                    binding["strength"] = raw_strength
                    binding["section"] = sec_name
                    binding["target_section"] = sec_name  # target section = same
                    # Populate clarity fields if present
                    if isinstance(clarity, dict):
                        binding.setdefault("arousal", clarity.get("arousal", 0.5))
                        binding.setdefault("valence", clarity.get("valence", 0.5))
                        binding.setdefault("surprise", clarity.get("surprise", 0.5))

                    state_vec = _grandurun_state(
                        binding, target_chi, target_source, needs_arr,
                        current_tick, co_occurrence_dict=co_occurrence_dict)
                    vector_pool.append((state_vec, word_label))
                    seen_words.add(word_label.lower())

        if not vector_pool:
            return None

        # Build target_state from target_chi properties (zero binding, identity)
        target_binding = {"chi": target_chi, "strength": 1.0,
                          "section": "", "target_section": "",
                          "source": target_source}
        target_state = _grandurun_state(
            target_binding, target_chi, target_source, needs_vector,
            current_tick, co_occurrence_dict=co_occurrence_dict)

        selected, alignment_score, dim_contributions = _grandurun_select_vector(
            vector_pool, target_state)

        if not selected:
            return None

        # Composition pass: reorder by best cortex co-occurrence triple
        composed = self._compose_from_cortex(selected, deep_candidates)

        emission_text = " ".join(composed)
        self._log_substrate_event("emission_vector",
                                  content=emission_text,
                                  pool_size=len(vector_pool),
                                  composition_len=len(composed),
                                  alignment_score=round(alignment_score, 4),
                                  target_chi=target_chi,
                                  n_priors=len(priors),
                                  dim_contributions=dim_contributions)
        return emission_text

    # ------------------------------------------------------------------
    # GL-CMD-DYNAMICS-EMISSION-RESTORATION-EVE-20260618-03
    # Two-stage emission: grandurun candidates → assemblage dynamics
    # ------------------------------------------------------------------

    # Sections that participate in language emission cascade (v4 lineage order)
    _EMISSION_SECTIONS = ("subject", "verb", "object")

    def _build_emission_system(self):
        """Build (or return cached) assemblage System for emission settling.

        Uses the same pattern as v7_engine._build_system but only for language-
        emitting sections + listen. Persisted across converse() calls so LTP
        and mode_strength accumulate."""
        if self._emission_system is not None:
            return self._emission_system

        import numpy as np
        from dsf_ai_service.substrate.assemblage import (
            Section as AsmSection, System as AsmSystem, N,
            normalize, random_unit_complex,
        )
        from dsf_ai_service.substrate.dna_recipe.phase_gating import make_projection

        rng = np.random.default_rng(42)

        secs = []
        for name in self._EMISSION_SECTIONS:
            sec = AsmSection(name=name, rng=rng, role="subject_like")
            # GL-CMD-EMISSION-HBASE-FREE: zero H_base and law_fields so psi
            # settles via evidence + inhibition only, not Hamiltonian rotation.
            # Matches the listen section pattern exactly.
            sec.H_base = np.zeros((N, N), dtype=complex)
            sec.law_fields = {k: np.zeros((N, N), dtype=complex)
                              for k in ("symmetry", "consistency", "compactness")}
            # GL-CMD-STRUCTURED-NOISE: mark for biological noise
            sec._use_structured_noise = True
            sec.map_inject = make_projection(N, 8, rng)
            secs.append(sec)

        # Listen section: zeroed Hamiltonian (input drive only)
        listen = AsmSection(name="listen", rng=rng, role="general")
        listen.H_base = np.zeros((N, N), dtype=complex)
        listen.law_fields = {k: np.zeros((N, N), dtype=complex)
                             for k in ("symmetry", "consistency", "compactness")}
        listen.map_inject = make_projection(N, 8, rng)
        secs.append(listen)

        sys_ = AsmSystem(secs, rng)

        # GL-CMD-PLASTICITY-ON-COMMIT: install plasticity on emission sections
        # so arcs() uses mode_strength as a multiplier. Matches v7 pattern.
        from dsf_ai_service.substrate.gl_plasticity import install_plasticity
        for sec in secs:
            install_plasticity(sec, initial_strength=1.0)

        # Phase 3: Install keyholes for canonical cascade
        # subject → verb → object, wide chi band
        sys_.add_keyhole("subject", -50, 50, "verb", goal_strength=0.4)
        sys_.add_keyhole("verb", -50, 50, "object", goal_strength=0.4)

        # Prevent bootstrap/novel_mode commits during emission settling —
        # we only want to read from modes we explicitly installed from candidates.
        # Set bootstrap_used = max so no bootstrap commits; raise det/p thresholds
        # so entropic_flip requires strong evidence; novel_mode is blocked by
        # setting the novel threshold extremely high via gamma.
        from dsf_ai_service.substrate.assemblage import BOOTSTRAP_MAX
        for sec in sys_.sections.values():
            sec.bootstrap_used = BOOTSTRAP_MAX
            sec._suppress_novel_mode = True  # no new modes during emission settling

        self._emission_system = sys_
        self._emission_rng = rng
        self._emission_token_vec = {}
        self._emission_word_map = {}
        self._emission_drive_tracker = {}

        return sys_

    # Cap mode bank size per section — DET_COMMIT=0.40 is calibrated for ~12 modes.
    # See GL-RPT-INVESTIGATE-COMMIT-PIPELINE-C1-20260619-01.
    _EMISSION_MODE_CAP = 15

    def _ensure_emission_mode(self, sys_, section_name, motif_id, word):
        """Install a mode in the emission system for (section, motif) if absent.
        Returns the mode_bank index, or None if section is at mode cap."""
        import numpy as np
        from dsf_ai_service.substrate.assemblage import N, random_unit_complex

        key = (section_name, motif_id)
        if key in self._emission_token_vec:
            # Already installed — find its index
            vec = self._emission_token_vec[key]
            sec = sys_.sections[section_name]
            for i, m in enumerate(sec.mode_bank):
                if np.array_equal(m, vec):
                    return i
            # Vector exists in map but not in mode_bank (shouldn't happen)
            sec.mode_bank.append(vec.copy())
            sec.mode_last_used.append(0)
            sec.mode_strength.append(1.0)
            sec._projector_cache = []  # invalidate; H_total rebuilds as ndarray
            idx = len(sec.mode_bank) - 1
            self._emission_word_map[(section_name, idx)] = word
            return idx

        # Cap: don't install new modes beyond _EMISSION_MODE_CAP per section
        sec = sys_.sections[section_name]
        if len(sec.mode_bank) >= self._EMISSION_MODE_CAP:
            return None

        # Create new mode vector
        vec = random_unit_complex(N, self._emission_rng)
        self._emission_token_vec[key] = vec

        sec.mode_bank.append(vec.copy())
        sec.mode_last_used.append(0)
        sec.mode_strength.append(1.0)
        sec._projector_cache.append(np.outer(vec, np.conj(vec)))
        idx = len(sec.mode_bank) - 1
        self._emission_word_map[(section_name, idx)] = word

        # Also install in listen section (so input drive can target it)
        listen = sys_.sections["listen"]
        listen.mode_bank.append(vec.copy())
        listen.mode_last_used.append(0)
        listen.mode_strength.append(1.0)
        listen._projector_cache = []  # invalidate; H_total rebuilds as ndarray

        return idx

    # GL-CMD-RICH-SENSORY-WIRING: content-word filter (mirrors _recall_sight_from_atlas)
    _FUNCTION_WORDS = frozenset({
        "a", "an", "the", "is", "are", "am", "was", "were",
        "of", "in", "on", "at", "to", "from", "with", "for",
        "and", "or", "but", "me", "you", "i", "we", "they",
        "show", "see", "look", "what", "tell", "about",
    })

    def _rich_sensory_candidates(self, input_chis, input_words, input_words_set,
                                  deep_candidates=None):
        """GL-CMD-RICH-SENSORY-WIRING-EVE-20260618-10

        Cross-modal candidate selection:
        1. Filter to content words
        2. For each content-word chi, look up ALL atlas entries (cross-modal)
           PLUS deep-atlas co-occurrence candidates from ALL input chis
           (content-word filtered at output, not input — deep atlas carries
           semantic relationships across chi distance)
        3. One-level cofire spread with affect weighting
        4. Attention focus boost
        Returns candidate list in same format as _grandurun_select_candidates.
        """
        import math

        # Phase 2: Filter to content words
        content_words = [w for w in input_words
                         if w.lower() not in self._FUNCTION_WORDS and len(w) > 1]
        if not content_words:
            content_words = list(input_words)[:3]  # fallback: use first 3 words

        # Compute content-word chis
        content_chis = []
        for w in content_words:
            temp_krim = LanguageKrimelack()
            temp_krim.transduce(w)
            content_chis.append(temp_krim.winding)

        # Phase 3: Cross-modal candidate lookup at content-word chis
        # Source A: working atlas entries near content-word chis
        cross_modal = []  # list of candidate dicts
        seen = set()
        for chi in content_chis:
            for d in range(-self.atlas.band, self.atlas.band + 1):
                for e in self.atlas.entries.get(chi + d, []):
                    if e["strength"] < FORGETTING_THRESHOLD:
                        continue
                    sec_name = e.get("section", "")
                    mid = e.get("motif", 0)
                    sec = self.sections.get(sec_name)
                    if sec is None or mid >= len(sec.modes):
                        continue
                    _, _, word_label = sec.modes[mid]
                    if not word_label or word_label.lower() in input_words_set:
                        continue
                    # GL-CMD-RICH-SENSORY-WIRING: skip function words in output
                    # too — mirrors picture-emission's content-word selectivity
                    if word_label.lower() in self._FUNCTION_WORDS:
                        continue
                    key = (sec_name, mid)
                    if key in seen:
                        continue
                    seen.add(key)
                    # GL-CMD-TEACHER-SUBSTRATE-TRUE: valence modulates cm
                    # for direct cross-modal hits (Path B).
                    # val in [-1,1]: negative valence suppresses, positive boosts.
                    _e_val = e.get("valence", 0.0)
                    cross_modal.append({
                        "chi": chi + d,
                        "section": sec_name,
                        "motif": mid,
                        "word": word_label,
                        "strength": e["strength"],
                        "coherent_magnitude": e["strength"] * max(0.0, 1.0 + _e_val),
                        "source": e.get("source", "corpus"),
                        "arousal": e.get("arousal", 0.5),
                        "valence": _e_val,
                        "surprise": e.get("surprise", 0.0),
                        "polarity": e.get("polarity", 1.0),
                        "sensory_refs": e.get("sensory_refs", []),
                        "origin": "cross_modal",
                    })

        # Source B: deep-atlas co-occurrence candidates from ALL input chis.
        # Deep atlas carries semantic relationships across chi distance.
        # Use the full deep_candidates already gathered by _emit_from_invariants
        # from all input chis (including function words), but filter output
        # to content words only.
        if deep_candidates:
            for de, co, clarity in deep_candidates:
                de_chi = de.get("chi", 0)
                for sec_name in co:
                    sec_co = co[sec_name]
                    if not sec_co:
                        continue
                    for mid_str, strength in sorted(
                            sec_co.items(),
                            key=lambda x: float(x[1]),
                            reverse=True)[:5]:
                        mid = int(mid_str)
                        sec = self.sections.get(sec_name)
                        if sec is None or mid >= len(sec.modes):
                            continue
                        _, _, word_label = sec.modes[mid]
                        if (not word_label
                                or word_label.lower() in input_words_set
                                or word_label.lower() in self._FUNCTION_WORDS):
                            continue
                        key = (sec_name, mid)
                        if key in seen:
                            continue
                        seen.add(key)
                        _de_val = de.get("valence", 0.0)
                        cross_modal.append({
                            "chi": de_chi,
                            "section": sec_name,
                            "motif": mid,
                            "word": word_label,
                            "strength": float(strength),
                            "coherent_magnitude": float(strength) * max(0.0, 1.0 + _de_val),
                            "source": de.get("source", "corpus"),
                            "arousal": de.get("arousal", 0.5),
                            "valence": _de_val,
                            "surprise": de.get("surprise", 0.0),
                            "polarity": de.get("polarity", 1.0),
                            "sensory_refs": de.get("sensory_refs", []),
                            "origin": "cross_modal_deep",
                        })

        # Phase 4: One-level cofire spread with affect weighting
        needs_val = getattr(self.needs, "connection", 0.5)
        needs_aro = getattr(self.needs, "novelty", 0.5)
        spread_candidates = []
        for cand in cross_modal:
            cand_chi = cand["chi"]
            for d in range(-1, 2):  # ±1 chi band for cofire neighbors
                for e in self.atlas.entries.get(cand_chi + d, []):
                    if e["strength"] < FORGETTING_THRESHOLD:
                        continue
                    sec_name = e.get("section", "")
                    mid = e.get("motif", 0)
                    key = (sec_name, mid)
                    if key in seen:
                        continue
                    sec = self.sections.get(sec_name)
                    if sec is None or mid >= len(sec.modes):
                        continue
                    _, _, word_label = sec.modes[mid]
                    if (not word_label or word_label.lower() in input_words_set
                            or word_label.lower() in self._FUNCTION_WORDS):
                        continue
                    seen.add(key)
                    chi_distance = abs(d)
                    w_chi = math.exp(-chi_distance / 2.0)
                    w_strength = e["strength"]
                    e_val = e.get("valence", 0.0)
                    e_aro = e.get("arousal", 0.5)
                    w_affect = max(0.1, min(1.0,
                        1.0 - 0.5 * abs(e_val - needs_val)
                            - 0.5 * abs(e_aro - needs_aro)))
                    transmission = w_chi * w_strength * w_affect * 0.30
                    spread_candidates.append({
                        "chi": cand_chi + d,
                        "section": sec_name,
                        "motif": mid,
                        "word": word_label,
                        "strength": e["strength"],
                        "coherent_magnitude": transmission,
                        "source": e.get("source", "corpus"),
                        "arousal": e_aro,
                        "valence": e_val,
                        "surprise": e.get("surprise", 0.0),
                        "polarity": e.get("polarity", 1.0),
                        "sensory_refs": e.get("sensory_refs", []),
                        "origin": "cofire_spread",
                    })

        all_candidates = cross_modal + spread_candidates

        # Phase 5: Attention focus boost
        ca = getattr(self, '_current_activity', None)
        if ca is not None and hasattr(ca, 'target') and ca.target:
            # Get attending item's chi
            attend_chi = None
            if hasattr(ca, 'target') and isinstance(ca.target, str):
                temp_krim = LanguageKrimelack()
                temp_krim.transduce(ca.target)
                attend_chi = temp_krim.winding
            if attend_chi is not None:
                for cand in all_candidates:
                    dist = abs(cand["chi"] - attend_chi)
                    if dist <= 2:
                        cand["coherent_magnitude"] *= 1.3
                    elif dist > 5:
                        cand["coherent_magnitude"] *= 0.7

        # GL-CMD-COGNITION-BUNDLE: sc/gp emission weighting
        # perf/cache-sc-weights: build sc weight cache once per emission
        try:
            from dsf_ai_service.substrate.hemisphere_cognition import (
                get_emission_hemisphere_weights, build_sc_weight_cache,
            )
            sc_cache = build_sc_weight_cache(self)
            for cand in all_candidates:
                hw = get_emission_hemisphere_weights(cand, self, sc_cache=sc_cache)
                if hw > 0:
                    cand["coherent_magnitude"] += hw
                    cand["sc_gp_weight"] = hw
        except Exception:
            pass

        # GL-CMD-ROUTE-CANDIDATES-TO-EMISSION-SECTIONS:
        # Re-route listen/intro candidates to emission-section counterparts.
        # Uses cached _word_to_emission_sections index (built at boot,
        # updated incrementally by read_word).
        _non_emission = frozenset(s for s in self.sections
                                   if s not in self._EMISSION_SECTIONS)
        # Fallback: rebuild if empty (shouldn't happen after boot)
        if not self._word_to_emission_sections:
            self._rebuild_word_to_emission_index()

        routed = []
        for cand in all_candidates:
            if cand.get("section") in _non_emission:
                word = (cand.get("word") or "").lower()
                matches = self._word_to_emission_sections.get(word, [])
                for (es, mi, w) in matches:
                    rkey = (es, mi)
                    if rkey not in seen:
                        seen.add(rkey)
                        routed.append({
                            **cand,
                            "section": es,
                            "motif": mi,
                            "word": w,
                            "origin": "emission_reroute",
                        })
        all_candidates.extend(routed)

        # Sort by activation and return top candidates
        all_candidates.sort(key=lambda c: -c["coherent_magnitude"])
        return all_candidates[:GRANDURUN_TOPK]

    def _emit_dynamics(self, input_chis, input_words_set, deep_candidates,
                       v7_session=None, input_words=None):
        """Two-stage emission: candidate selection → assemblage dynamics settling.

        Stage 1: _grandurun_select_candidates (default) or _rich_sensory_candidates
                 (RICH_SENSORY_INPUT=1) returns top-K candidates.
        Stage 2: Candidates seed the emission System, dynamics settle via cascade +
                 keyhole + NMDA, emission reads dominant_mode per section.

        Gated by EMISSION_DYNAMICS=1.
        GL-CMD-DYNAMICS-EMISSION-RESTORATION-EVE-20260618-03 Phase 4.
        GL-CMD-RICH-SENSORY-WIRING-EVE-20260618-10: cross-modal candidates."""
        import numpy as np
        import time as _time
        from dsf_ai_service.substrate.assemblage import N, normalize, random_unit_complex
        from dsf_ai_service.substrate.gl_nmda import (
            CoincidenceGate, context_section_committed, update_drive_tracker,
        )
        from dsf_ai_service.substrate.gl_plasticity import (
            decay_plasticity, install_plasticity, reinforce_mode,
        )

        # Clear mode banks before each dynamics call so stale modes from previous
        # converses don't fill the cap and block current candidates from installing.
        # _emission_token_vec (mode vectors) is preserved for consistent representations.
        # _emission_word_map is cleared since mode_bank indices reset.
        if self._emission_system is not None:
            for sec in self._emission_system.sections.values():
                sec.mode_bank.clear()
                sec._projector_cache.clear()
                if hasattr(sec, 'mode_last_used'):
                    sec.mode_last_used.clear()
                if hasattr(sec, 'mode_strength'):
                    sec.mode_strength.clear()
            self._emission_word_map.clear()
            # Also clear the token vec so modes get freshly assigned each converse
            self._emission_token_vec.clear()

        # Stage 1: Candidate selection
        t0 = _time.monotonic()
        rich_sensory = os.environ.get("RICH_SENSORY_INPUT", "0") == "1"
        if rich_sensory and input_words:
            candidates = self._rich_sensory_candidates(
                input_chis, input_words, input_words_set,
                deep_candidates=deep_candidates)
        else:
            candidates = _grandurun_select_candidates(
                input_chis, deep_candidates, self.sections,
                input_words_set, top_k=GRANDURUN_TOPK)
        stage1_ms = (_time.monotonic() - t0) * 1000

        if not candidates:
            return None

        # Build/get emission system
        sys_ = self._build_emission_system()

        # Determine input source for NMDA context
        input_source = getattr(self, "_last_converse_source", "corpus") or "corpus"

        # Install candidate modes and compute per-section drive biases
        section_drives = {s: np.zeros(N, dtype=complex) for s in self._EMISSION_SECTIONS}
        listen_drive = np.zeros(N, dtype=complex)

        for cand in candidates:
            sec_name = cand["section"]
            if sec_name not in sys_.sections or sec_name not in self._EMISSION_SECTIONS:
                continue

            mode_idx = self._ensure_emission_mode(
                sys_, sec_name, cand["motif"], cand["word"])

            if mode_idx is None:
                continue  # section at mode cap; candidate still counted but not installed

            # Bias section psi toward this candidate's mode
            mode_vec = sys_.sections[sec_name].mode_bank[mode_idx]
            weight = cand["coherent_magnitude"]
            section_drives[sec_name] += mode_vec * weight

            # Also drive listen
            listen_drive += mode_vec * weight

        # Normalize drives and seed psi
        for sec_name in self._EMISSION_SECTIONS:
            drv = section_drives[sec_name]
            sec = sys_.sections[sec_name]
            if np.linalg.norm(drv) > 0:
                sec.psi = normalize(drv)
            else:
                sec.psi = normalize(random_unit_complex(N, self._emission_rng) * 0.3
                                    + normalize(np.ones(N, dtype=complex)) * 0.7)

        if np.linalg.norm(listen_drive) > 0:
            sys_.sections["listen"].psi = normalize(listen_drive)

        # Build NMDA context functions using candidate metadata
        # source_match: fires when joe_voice candidates present and input is from joe
        joe_candidates_present = any(c["source"] == "joe_voice" for c in candidates)

        def source_match_fn(s):
            return joe_candidates_present and input_source in ("joe", "joe_voice", "wc", "c1")

        # affect_match: fires when candidate affect is close to needs
        # Use needs.arousal() and needs.valence() — the computed affect dimensions.
        # Previously used needs.novelty/connection (functional needs), which produced
        # large mismatches (novelty ~0.94 vs corpus arousal ~0.50 = 0.44 gap > 0.3).
        needs_arousal = self.needs.arousal()
        needs_valence = self.needs.valence()
        mean_arousal = sum(c["arousal"] for c in candidates) / len(candidates)
        mean_valence = sum(c["valence"] for c in candidates) / len(candidates)
        affect_close = abs(mean_arousal - needs_arousal) < 0.3 and abs(mean_valence - needs_valence) < 0.3

        def affect_match_fn(s):
            return affect_close

        # Install NMDA gates per emission section (Phase 3)
        nmda_gates = {}
        for sec_name in self._EMISSION_SECTIONS:
            gate = CoincidenceGate(
                sec_name,
                context_fn=lambda s, sn=sec_name: source_match_fn(s) or affect_match_fn(s),
                drive_thresh=0.15,
                ltp_boost=0.05,
            )
            nmda_gates[sec_name] = gate

        # Track which mode indices we installed (only these have word mappings)
        installed_modes = set(self._emission_word_map.keys())

        # GL-CMD-STRUCTURED-NOISE: set noise context on emission sections
        needs_novelty = getattr(self.needs, "novelty", 0.5)
        for sec_name in self._EMISSION_SECTIONS:
            sec = sys_.sections[sec_name]
            sec._noise_needs_novelty = needs_novelty
            # Candidate mode IDs for this section
            sec._noise_candidate_ids = [
                idx for (sn, idx) in installed_modes if sn == sec_name
            ]

        # Point C (Eve): DSF-derived H_base REVERTED.
        # Past Eve zeroed H_base in GL-CMD-EMISSION-HBASE-FREE-EVE-20260618-06
        # because non-zero H caused psi to oscillate rather than commit — the early
        # exit (no_new_streak >= 10) never triggered, all 80 ticks ran, socket timeout.
        # My structured H_base (DSF × mode projectors) caused the same regression:
        # with LATERAL_INHIBITION_ENABLED + EMISSION_STRUCTURED_NOISE, 80 ticks of
        # Crank-Nicolson with non-zero H_base exceeded the 25s socket timeout.
        #
        # The principle Eve protected is still correct: emission sections answer to
        # evidence + inhibition + goals, not autonomous H rotation. DSF coupling should
        # enter through a different path — possibly as a prior on candidate selection
        # (Stage 1 grandurun weighting by J) rather than as a Hamiltonian term.
        # That wiring is the proper fix and needs its own pass gate before deploying.
        #
        # For now: H_base stays zero, emission works, gate test can run.

        # Stage 2: Dynamics settling
        t1 = _time.monotonic()
        # Fix 2 (Eve): hard wall-clock budget — the degenerate case where no commit
        # ever fires runs all N ticks → socket timeout. Cap at 5s regardless.
        # "no commit fires" → arcs_fallback is the correct bounded degradation.
        # This lets EMISSION_DYNAMICS=1 run without ever timing out the socket.
        _WALL_BUDGET_S = 5.0
        _t_deadline = t1 + _WALL_BUDGET_S
        n_ticks = EMISSION_DYNAMICS_TICKS
        emit_commits = []
        seen_commit_keys = set()
        keyhole_fires = []
        nmda_events = []
        no_new_streak = 0

        for t in range(n_ticks):
            # Hard wall-clock check EVERY tick — each tick can be slow on 2vCPU.
            # Checking every 20 ticks was too coarse: 20 * 0.75s = 15s before check.
            if t > 0 and _time.monotonic() > _t_deadline:
                break   # degenerate: fallback to arcs() argmax below
            # GL-CMD-STRUCTURED-NOISE: update tick for phase oscillation
            for sec_name in self._EMISSION_SECTIONS:
                sys_.sections[sec_name]._noise_tick = t

            # Evidence: section drives with noise
            ev = {}
            for sec_name in self._EMISSION_SECTIONS:
                drv = section_drives[sec_name]
                if np.linalg.norm(drv) > 0:
                    noisy = normalize(drv + 0.10 * (
                        self._emission_rng.standard_normal(N)
                        + 1j * self._emission_rng.standard_normal(N)))
                    ev[sec_name] = noisy

            commits = sys_.tick_once(ev, enable_self_evo=False,
                                     coordinator_on=False)

            new_this_tick = False
            for c in commits:
                if c["section"] in self._EMISSION_SECTIONS:
                    ckey = (c["section"], c["mode_id"])
                    # Only accept commits for modes we installed (have word mappings)
                    if ckey not in installed_modes:
                        continue
                    if ckey not in seen_commit_keys:
                        seen_commit_keys.add(ckey)
                        emit_commits.append(c)
                        new_this_tick = True
                        # GL-CMD-PLASTICITY-ON-COMMIT: LTP on commit.
                        # Decision and learning are the same event.
                        # Matches v7 pattern at v7_engine.py:510.
                        reinforce_mode(sys_.sections[c["section"]],
                                       c["mode_id"],
                                       boost=0.05, ceiling=2.5)

            # Track keyhole propagation
            for c in commits:
                for kh in sys_.keyholes:
                    if (kh["sender"] == c["section"]
                            and kh["chi_lo"] <= c.get("chi", 0) <= kh["chi_hi"]):
                        keyhole_fires.append({
                            "tick": sys_.tick,
                            "sender": c["section"],
                            "receiver": kh["receiver"],
                        })

            # NMDA pass
            update_drive_tracker(self._emission_drive_tracker, ev)
            for sec_name, gate in nmda_gates.items():
                fired, mode_id, eval_d = gate.check_and_fire(sys_)
                eval_d["source_match"] = source_match_fn(sys_)
                eval_d["affect_match"] = affect_match_fn(sys_)
                nmda_events.append(eval_d)

            # Plasticity decay
            for sec_name in self._EMISSION_SECTIONS:
                decay_plasticity(sys_.sections[sec_name], decay=0.998)

            if new_this_tick:
                no_new_streak = 0
            else:
                no_new_streak += 1
            # Only allow early exit after at least one commit has fired
            # (with H_base zeroed + inhibition, commits start around tick 60-70)
            if emit_commits and no_new_streak >= 10:
                break
            if len(emit_commits) >= 20:
                break

        stage2_ms = (_time.monotonic() - t1) * 1000

        # Read emission: committed modes per section in cascade order.
        # GL-CMD-LATERAL-INHIBITION: with inhibition on, commit_check fires
        # for real via entropic_flip. Collect the last committed mode per
        # section. Fall back to arcs() argmax only if no commit fired.
        emission_words = []
        per_section_dominant = {}
        committed_sections = set()
        for sec_name in self._EMISSION_SECTIONS:
            sec = sys_.sections[sec_name]
            # Check if this section had a committed mode during dynamics
            committed_word = None
            committed_mode = None
            for c in reversed(emit_commits):
                if c["section"] == sec_name:
                    w = self._emission_word_map.get((sec_name, c["mode_id"]))
                    if w:
                        committed_mode = c["mode_id"]
                        committed_word = w
                        committed_sections.add(sec_name)
                        break

            if committed_word:
                per_section_dominant[sec_name] = (committed_mode, committed_word, "commit")
                if (committed_word.lower() not in input_words_set
                        and committed_word not in emission_words):
                    emission_words.append(committed_word)
            else:
                # Fallback: arcs() argmax for installed modes
                arcs = sec.arcs()
                if len(arcs) == 0:
                    per_section_dominant[sec_name] = (None, None, "none")
                    continue
                sorted_modes = sorted(range(len(arcs)), key=lambda i: -arcs[i])
                top_mode = None
                word = None
                for mi in sorted_modes:
                    w = self._emission_word_map.get((sec_name, mi))
                    if w:
                        top_mode = mi
                        word = w
                        break
                per_section_dominant[sec_name] = (top_mode, word, "arcs_fallback")
                if word and word.lower() not in input_words_set and word not in emission_words:
                    emission_words.append(word)

        if not emission_words:
            return None

        emission_text = " ".join(emission_words)

        # Log
        source_match_count = sum(1 for e in nmda_events if e.get("source_match"))
        affect_match_count = sum(1 for e in nmda_events if e.get("affect_match"))
        nmda_fired_count = sum(1 for e in nmda_events if e.get("reason") == "fired")

        # GL-CMD-RICH-SENSORY-WIRING: per-section candidate counts and origin
        section_candidate_counts = {}
        origin_counts = {}
        source_counts = {}
        for c in candidates:
            sn = c.get("section", "unknown")
            section_candidate_counts[sn] = section_candidate_counts.get(sn, 0) + 1
            orig = c.get("origin", "grandurun")
            origin_counts[orig] = origin_counts.get(orig, 0) + 1
            src = c.get("source", "corpus")
            source_counts[src] = source_counts.get(src, 0) + 1

        self._log_substrate_event("emission_dynamics",
                                  content=emission_text,
                                  n_candidates=len(candidates),
                                  n_commits=len(emit_commits),
                                  per_section_dominant=per_section_dominant,
                                  keyhole_fires=len(keyhole_fires),
                                  nmda_fired=nmda_fired_count,
                                  nmda_source_match=source_match_count,
                                  nmda_affect_match=affect_match_count,
                                  stage1_ms=round(stage1_ms, 1),
                                  stage2_ms=round(stage2_ms, 1),
                                  dynamics_ticks=n_ticks,
                                  sections_with_commits=list(set(
                                      c["section"] for c in emit_commits)),
                                  committed_sections=list(committed_sections),
                                  rich_sensory=rich_sensory,
                                  section_candidate_counts=section_candidate_counts,
                                  origin_counts=origin_counts,
                                  source_counts=source_counts)
        # GL-CMD-V5-VOICE-STAGE1: store quality metadata for _cmd_converse gate
        arcs_fallback_used = any(
            isinstance(v, tuple) and len(v) > 2 and v[2] == "arcs_fallback"
            for v in per_section_dominant.values()
        )
        self._last_dynamics_result = {
            "content": emission_text,
            "committed_sections": list(committed_sections),
            "n_commits": len(emit_commits),
            "arcs_fallback": arcs_fallback_used,
            "tick": self.tick,
        }
        return emission_text

    def _compose_from_cortex(self, selected_words, deep_candidates):
        """Reorder selected words by best co-occurrence triple from deep atlas.
        A triple = subject + verb + object words that co-occur at the same chi.
        Falls back to selection order if no triple matches."""
        if len(selected_words) < 3:
            return selected_words

        selected_set = set(w.lower() for w in selected_words)
        # Build word→section lookup
        word_to_section = {}
        for sec_name, sec in self.sections.items():
            for _, _, word_label in sec.modes:
                if word_label and word_label.lower() in selected_set:
                    word_to_section[word_label.lower()] = sec_name

        # Scan deep candidates for co-occurrence triples
        best_triple = None
        best_weight = 0.0
        SVO_ORDER = ["subject", "verb", "object"]

        for de, co, clarity in deep_candidates:
            if not co:
                continue
            # Extract top word per section from this co_occurrence entry
            section_words = {}
            for sec_name in SVO_ORDER:
                sec_co = co.get(sec_name, {})
                if not sec_co:
                    continue
                sec = self.sections.get(sec_name)
                if sec is None:
                    continue
                for mid_str, weight in _heapq.nlargest(3, sec_co.items(),
                                                        key=lambda x: float(x[1])):
                    mid = int(mid_str)
                    if mid >= len(sec.modes):
                        continue
                    _, _, word_label = sec.modes[mid]
                    if word_label and word_label.lower() in selected_set:
                        section_words[sec_name] = (word_label, float(weight))
                        break

            # Triple found if we have words in 3 sections
            if len(section_words) >= 3:
                triple_words = [section_words[s][0] for s in SVO_ORDER
                                if s in section_words]
                triple_weight = sum(section_words[s][1] for s in SVO_ORDER
                                    if s in section_words)
                if triple_weight > best_weight:
                    best_triple = triple_words[:3]
                    best_weight = triple_weight
            elif len(section_words) >= 2:
                # Pair — still better than random order
                pair_words = [section_words[s][0] for s in SVO_ORDER
                              if s in section_words]
                pair_weight = sum(section_words[s][1] for s in SVO_ORDER
                                  if s in section_words)
                if pair_weight > best_weight and best_triple is None:
                    best_triple = pair_words
                    best_weight = pair_weight

        if best_triple:
            used = set(w.lower() for w in best_triple)
            remaining = [w for w in selected_words if w.lower() not in used]
            return best_triple + remaining[:2]

        return selected_words

    def _emit_unslotted(self, input_chis, input_words):
        """GL-CLARITY-INVARIANCE-UNCAGE: fallback emission from strongest
        working atlas bindings near input chi. Variable-length, no SVO slots."""
        input_words_set = set(w.lower() for w in input_words)
        all_bindings = []
        for chi in input_chis:
            bindings = self.atlas.bindings_at_chi_neighborhood(
                chi, min_strength=0.1, min_clarity=0.1)
            all_bindings.extend(bindings)
        if not all_bindings:
            return None
        # Sort by strength * clarity
        all_bindings.sort(
            key=lambda e: e["strength"] * e.get("clarity", 0.3), reverse=True)
        emitted = []
        seen = set()
        for e in all_bindings:
            sec_name = e.get("section", "")
            mid = e.get("motif", 0)
            sec = self.sections.get(sec_name)
            if sec is None or mid >= len(sec.modes):
                continue
            _, _, word_label = sec.modes[mid]
            if (word_label and word_label.lower() not in input_words_set
                    and word_label.lower() not in seen):
                emitted.append(word_label)
                seen.add(word_label.lower())
            if len(emitted) >= 4:
                break
        if not emitted:
            return None
        return " ".join(emitted)

    def _recall_response(self, input_chis, input_word_chis, input_words):
        """Atlas-driven recall across ALL sections including sight.
        Returns a response dict with text and optional picture references."""
        input_words_lower = set(w.lower() for w in input_words)

        recalled_words = {}
        for sec_name in ("subject", "verb", "object"):
            best_word = self._recall_from_atlas(sec_name, input_chis,
                                                  exclude_words=input_words_lower,
                                                  input_words=input_words)
            if best_word:
                recalled_words[sec_name] = best_word

        # v8 (GL-BRIEF-028): include response-linked entries in recall pool
        # Light touch: if any recalled chi has response_context or received_response
        # links, add linked entries to the candidate pool
        linked_chis = set()
        for chi_k in input_chis:
            for d in range(-self.atlas.band, self.atlas.band + 1):
                for e in self.atlas.entries.get(chi_k + d, []):
                    for lc in e.get("response_context", []):
                        linked_chis.add(lc)
                    for lr in e.get("received_response", []):
                        linked_chis.add(lr)
        # Also check deep atlas for reinstated entries with links (Amendment B)
        for chi_k in input_chis:
            for de in self.deep_atlas.entries.get(chi_k, []):
                for lc in de.get("response_context", []):
                    linked_chis.add(lc)
                for lr in de.get("received_response", []):
                    linked_chis.add(lr)

        if linked_chis:
            expanded_chis = list(input_chis) + list(linked_chis)
            for sec_name in ("subject", "verb", "object"):
                if sec_name not in recalled_words:
                    word = self._recall_from_atlas(sec_name, expanded_chis,
                                                  exclude_words=input_words_lower,
                                                  input_words=input_words)
                    if word:
                        recalled_words[sec_name] = word

        # v7 Phase 2: recall sight motifs via chi-neighborhood
        recalled_pictures = self._recall_sight_from_atlas(input_chis, input_words)

        if not recalled_words and not recalled_pictures:
            return None

        # Compose text response
        out = []
        for sec_name in ("subject", "verb", "object"):
            if sec_name in recalled_words and recalled_words[sec_name] not in out:
                out.append(recalled_words[sec_name])

        text = " ".join(out) if out else None

        # If we have pictures, return a structured response
        if recalled_pictures:
            self._last_recalled_pictures = recalled_pictures
            if text:
                return text
            return text  # even None — caller will check _last_recalled_pictures
        self._last_recalled_pictures = []
        return text

    def _chis_for_text(self, text):
        """Transduce text to chi addresses (read-only, no atlas mutation)."""
        words = _normalize_text(text)
        result = []
        for w in words:
            tk = LanguageKrimelack()
            tk.transduce(w)
            result.append(tk.winding)
        return result

    def _recall_sight_from_atlas(self, input_chis, input_words):
        """Find sight motifs bound at chi addresses near input word motifs.
        Returns list of (sight_motif, source_item_id) tuples."""
        if not hasattr(self, 'sight') or not self.sight.motifs:
            return []

        input_words_lower = [w.lower() for w in input_words] if input_words else []

        # Step 1: find chi addresses where input content words committed
        content_chis = set()
        function_words = {"a", "an", "the", "is", "are", "am", "was", "were",
                          "of", "in", "on", "at", "to", "from", "with", "for",
                          "and", "or", "but", "me", "you", "i", "we", "they",
                          "show", "see", "look", "what", "tell", "about"}
        content = [w for w in input_words_lower if w not in function_words and len(w) > 1]
        if not content:
            return []

        for chi_k, entries in self.atlas.entries.items():
            for e in entries:
                sec_name = e.get("section", "")
                if sec_name in self.sections:
                    sec = self.sections[sec_name]
                    mid = e.get("motif", 0)
                    if mid < len(sec.modes):
                        _, _, w = sec.modes[mid]
                        if w and w.lower() in content:
                            content_chis.add(chi_k)

        if not content_chis:
            return []

        # Step 2: find sight motifs bound at those chi addresses (with band +-2)
        sight_motif_ids = set()
        for chi_k, entries in self.atlas.entries.items():
            for target_chi in content_chis:
                if abs(chi_k - target_chi) <= 2:
                    for e in entries:
                        if e.get("section") == "sight":
                            sight_motif_ids.add(e.get("motif"))

        if not sight_motif_ids:
            return []

        # Step 3: resolve to motifs with source PictureItems
        results = []
        for sm in self.sight.motifs:
            if sm.motif_id in sight_motif_ids and sm.source_history:
                # Get the most recent source item_id
                source_id = sm.source_history[-1]
                if source_id in self._pictures:
                    results.append((sm, source_id))
        return results

    def _recall_from_atlas(self, target_section, input_chis, exclude_words=None,
                            input_words=None):
        """Atlas-driven recall via INPUT-WORD-SPECIFIC chi locations.

        Step 1: For each content word in input, find the chi values where
                that word's motif actually committed in the atlas.
        Step 2: At those specific chi values, find target_section motifs.
        Step 3: Rank by frequency, exclude input words, return best.

        This is association BY THE INPUT WORDS, not just by chi proximity."""
        from collections import Counter
        if exclude_words is None:
            exclude_words = set()
        if input_words is None:
            input_words = []
        sec = self.sections[target_section]
        if not sec.modes:
            return None

        # Use only content words (not articles/prepositions/etc.) for recall anchors
        function_words = {"a", "an", "the", "is", "are", "am", "was", "were",
                          "of", "in", "on", "at", "to", "from", "with", "for",
                          "and", "or", "but", "me", "you", "i", "we", "they",
                          "about", "tell", "what", "where", "when", "how", "why",
                          "do", "does", "did", "has", "have", "had"}
        content_words = [w.lower() for w in input_words
                          if w.lower() not in function_words and len(w) > 1]
        if not content_words:
            # Fall back to all input words if no content words found
            content_words = [w.lower() for w in input_words]
        if not content_words:
            return None

        # Step 1: Find atlas chi locations where each content word committed
        content_word_chis = set()
        for chi, entries in self.atlas.entries.items():
            for e in entries:
                if e["section"] in self.sections:
                    other_sec = self.sections[e["section"]]
                    if e["motif"] < len(other_sec.modes):
                        _, _, motif_word = other_sec.modes[e["motif"]]
                        if motif_word and motif_word.lower() in content_words:
                            content_word_chis.add(chi)

        if not content_word_chis:
            return None

        # Step 2: At those chi locations, find target_section motifs
        candidates = Counter()
        for chi_k in content_word_chis:
            for e in self.atlas.entries.get(chi_k, []):
                if e["section"] == target_section:
                    if e["motif"] < len(sec.modes):
                        _, _, motif_word = sec.modes[e["motif"]]
                        if motif_word and motif_word.lower() not in exclude_words:
                            candidates[e["motif"]] += 1

        if not candidates:
            return None

        # Require minimum evidence: candidate must appear in at least 2 chi
        # locations linked to input content words (real association, not noise)
        for motif_id, count in candidates.most_common():
            if count < 2:
                break
            if motif_id < len(sec.modes):
                _, _, word = sec.modes[motif_id]
                if word:
                    return word
        return None

    # ------------------------------------------------------------------
    # MathLoom (BSIL)
    # ------------------------------------------------------------------
    NUM_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
                 "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                 "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
                 "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
                 "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
                 "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
    NUM_WORDS_REV = {v: k for k, v in NUM_WORDS.items()}
    MULTIPLIERS = {"hundred": 100, "thousand": 1000, "million": 1000000}

    def _parse_math(self, text):
        """v5 fixed parser: handles multi-word numbers (ten thousand, five hundred),
        symbol operators (+ - * /), and fails honestly on mixed/ambiguous input
        rather than returning partial garbage."""
        # Normalize symbols to word operators
        t = text.lower()
        t = t.replace("+", " plus ").replace("-", " minus ")
        t = t.replace("*", " times ").replace("/", " over ")
        t = t.replace("?", " ").replace("=", " ")
        toks = t.split()

        nums = []
        op = None
        current = None  # currently-building number (None = not building)

        def flush():
            nonlocal current
            if current is not None:
                nums.append(current)
                current = None

        for tok in toks:
            if tok in self.NUM_WORDS:
                v = self.NUM_WORDS[tok]
                if current is None:
                    current = v
                else:
                    current += v
            elif tok in self.MULTIPLIERS:
                m = self.MULTIPLIERS[tok]
                if current is None:
                    current = m
                else:
                    current *= m
            elif tok.lstrip("-").isdigit():
                # Digit form — fail if mixing with word number in progress
                if current is not None:
                    return None  # ambiguous: don't guess
                nums.append(int(tok))
            elif tok in {"plus", "and"} and op is None:
                # "and" only counts as plus if we already have a number
                if tok == "and" and current is None and not nums:
                    continue
                flush()
                op = "+"
            elif tok in {"minus", "less"} and op is None:
                flush()
                op = "-"
            elif tok == "times" and op is None:
                flush()
                op = "*"
            elif tok == "over" and op is None:
                flush()
                op = "/"
            elif tok in {"is", "equals", "what", "a", "the"}:
                # benign question tokens, skip
                continue
            else:
                # unknown token — finish any current number but don't fail outright
                flush()

        flush()

        if len(nums) >= 2 and op:
            return op, nums[0], nums[1]
        return None

    def _mathloom_solve(self, op, a, b):
        a_bt = ml.int_to_bt(a); b_bt = ml.int_to_bt(b)
        if op == "+":
            s, _ = ml.bt_add(a_bt, b_bt); return ml.bt_to_int(s)
        if op == "-":
            s, _ = ml.bt_sub(a_bt, b_bt); return ml.bt_to_int(s)
        if op == "*":
            return ml.bt_to_int(ml.bt_mul(a_bt, b_bt))
        if op == "/":
            q, _ = ml.bt_div(a_bt, b_bt); return ml.bt_to_int(q)

    def _num_to_word(self, n):
        if n in self.NUM_WORDS_REV: return self.NUM_WORDS_REV[n]
        if n < 0: return "minus " + self._num_to_word(-n)
        return str(n)

    # ------------------------------------------------------------------
    # Continuous reading (background, not turn-based)
    # ------------------------------------------------------------------
    def start_continuous_reading(self, corpus_lines, interval=0.02):
        def loop():
            i = 0
            while not self._reading_stop.is_set():
                self.read_sentence(corpus_lines[i % len(corpus_lines)])
                i += 1
                time.sleep(interval)
        self._reading_stop.clear()
        self._reading_thread = threading.Thread(target=loop, daemon=True)
        self._reading_thread.start()

    def stop_continuous_reading(self):
        self._reading_stop.set()
        if self._reading_thread:
            self._reading_thread.join(timeout=2.0)

    # ------------------------------------------------------------------
    # v7: Autonomy — activity scheduler, drive dynamics, emission
    # GUALALOOM-V7-AUTONOMY-WC-2026-06-06
    # ------------------------------------------------------------------

    def _log_substrate_event(self, event_kind, **detail):
        """Record a substrate event (in-memory ring buffer + disk for critical events)."""
        ev = SubstrateEvent(tick=self.tick, kind=event_kind, detail=detail)
        self._substrate_events.append(ev)
        # Critical events also go to disk for replay recovery
        if event_kind in ("activity_started", "activity_ended", "corpus_completed",
                          "sleep_manual", "dream_began", "dream_artifact",
                          "picture_uploaded", "sound_uploaded", "video_uploaded",
                          "corpus_added", "visual_motif_committed", "visual_motif_fired",
                          "emission"):
            try:
                self.log_event("state", event_kind, **detail)
            except Exception:
                pass
        return ev

    def start_autonomy_loop(self, interval=0.05):
        """Replace continuous reading with full autonomy loop.
        Interval 50ms = 20 iterations/sec."""
        def loop():
            while not self._reading_stop.is_set():
                try:
                    self._autonomy_tick()
                except Exception as e:
                    print(f"[GualaLoom] Autonomy tick error: {e}")
                time.sleep(interval)
        self._reading_stop.clear()
        self._reading_thread = threading.Thread(target=loop, daemon=True)
        self._reading_thread.start()

    def _autonomy_tick(self):
        """One iteration of the autonomy loop."""
        with self.lock:
            # 1. Needs drift AWAY from target (once per iteration)
            self.needs.tick_drift()

            # Periodic needs snapshot to disk (every 500 ticks)
            if self.tick % 500 == 0 and self.tick > 0:
                try:
                    ns = self.needs.snapshot()
                    self.log_event("state", "needs_snapshot",
                                   stability=ns["stability"],
                                   novelty=ns["novelty"],
                                   connection=ns["connection"],
                                   valence=ns["valence"],
                                   arousal=ns["arousal"])
                except Exception:
                    pass

            # Familiarity decay for non-current pictures (every 200 ticks)
            if self.tick % 200 == 0 and self.target_familiarity:
                current_target = (self._current_activity.target
                                  if self._current_activity else None)
                for pid in list(self.target_familiarity.keys()):
                    if pid != current_target:
                        # GL-BRIEF-NEEDS-PHYSICS Fix 2: consolidation-resistant decay
                        # Highly-attended targets decay slower (log-scaled)
                        pic = self._pictures.get(pid)
                        n_attends = pic.times_attended if pic else 0
                        consolidation_factor = 1.0 / (1.0 + math.log(1.0 + n_attends))
                        effective_decay = 1.0 - (1.0 - 0.9967) * consolidation_factor
                        self.target_familiarity[pid] *= effective_decay
                        if self.target_familiarity[pid] < 0.001:
                            del self.target_familiarity[pid]
                # Snapshot every ~10 min (200 ticks × 30 = 6000 ticks ≈ 5 min)
                if self.tick % 6000 == 0:
                    self._log_substrate_event("target_familiarity_snapshot",
                                              familiarity=dict(
                                                  (k, round(v, 4))
                                                  for k, v in self.target_familiarity.items()))

            # v8 (GL-BRIEF-028): prune expired response windows
            self._prune_response_windows()

            # 2. Select activity if needed
            if self._current_activity is None:
                a = self._select_next_activity()
                self._start_activity(a)

            a = self._current_activity
            if a is None:
                return

            # 3. Execute activity
            if a.kind == "READING":
                # read_sentence handles tick++, atlas decay, coordinator
                self._atick_reading(a)
            else:
                # Non-reading: manual tick + effects
                self.tick += 1
                if a.kind == "SLEEPING":
                    self._atick_sleeping(a)
                elif a.kind == "DREAMING":
                    self._atick_dreaming(a)
                elif a.kind == "PLAYING":
                    self._atick_playing(a)
                elif a.kind == "ATTENDING":
                    self._atick_attending(a)
                elif a.kind == "ATTENDING_VISUAL":
                    self._atick_attending_visual(a)
                elif a.kind == "ATTENDING_AUDIO":
                    self._atick_attending_audio(a)
                elif a.kind == "ATTENDING_VIDEO":
                    self._atick_attending_video(a)
                elif a.kind == "EMITTING":
                    self._atick_emitting(a)
                # Non-reading: manual atlas decay + coordinator
                # GL-FIX-PAUSE-IDEMPOTENT: rate_scale=0 when paused
                _paused = os.environ.get("DECAY_PAUSED", "0") == "1"
                if self.tick % 10 == 0:
                    self.atlas.decay(self.tick, rate_scale=0.0 if _paused else self.decay_modulation)
                if not _paused and self.tick % 200 == 0:
                    self.atlas.forget_below_threshold()
                if self.tick % 5 == 0:
                    self.coordinator.regulate(self, self.needs, self.atlas,
                                             self.sections, self.tick)

            # 4. Check activity budget
            if self.tick >= a.expected_end_tick:
                self._end_activity()

    # ── Activity selection ──

    def _candidate_activities(self):
        """All activities currently possible as (kind, target) tuples."""
        candidates = [("IDLE", None), ("PLAYING", None), ("SLEEPING", None)]
        for cid in self._corpora:
            candidates.append(("READING", cid))
        for sid in self._sensory_items:
            candidates.append(("ATTENDING", sid))
        # Phase 2: visual items
        for pid in self._pictures:
            candidates.append(("ATTENDING_VISUAL", pid))
        # Audio items
        for sid in self._sounds:
            candidates.append(("ATTENDING_AUDIO", sid))
        for vid in self._videos:
            candidates.append(("ATTENDING_VIDEO", vid))
        # Emission: only if pair-bond source present + cooldown elapsed
        if (any(self.coordinator._presence.get(s, False)
                and self.coordinator._pair_bond.get(s, False)
                for s in PAIR_BOND_SOURCES)
                and self.tick - self._last_emission_tick > EMISSION_COOLDOWN_TICKS):
            candidates.append(("EMITTING", None))
        return candidates

    EXOGENOUS_NEW_SALIENCE = 1.0  # beats any needs-driven score

    def _action_salience(self, kind, target):
        """How attractive is this activity given current needs?
        Salience = dot product of (need-distance) × (payoff per need).
        Mirrored from wC's autonomy substrate model."""
        sd = self.needs.signed_distance()

        # Graded exogenous salience for visual attention.
        # Biology: orienting response decays with familiarity, not binary.
        # Per GL-BRIEF-graded-exogenous-salience-wC-20260610-031.
        if kind == "ATTENDING_VISUAL" and target in self._pictures:
            pic = self._pictures[target]
            if pic.times_attended == 0:
                return self.EXOGENOUS_NEW_SALIENCE
            fam = self.target_familiarity.get(target, 0.0)
            base_payoff = ACTIVITY_NOVELTY_PAYOFF["ATTENDING_VISUAL_REPEAT"]
            stab_payoff = ACTIVITY_STABILITY_PAYOFF.get(kind, 0.0)
            conn_payoff = ACTIVITY_CONNECTION_PAYOFF.get(kind, 0.0)
            visual_score = (1.0 - fam) * base_payoff
            needs_score = (sd["novelty"] * (base_payoff * (1.0 - fam))
                           + sd["stability"] * stab_payoff
                           + sd["connection"] * conn_payoff + 0.01)
            return max(visual_score, needs_score)

        # Novelty payoff with NEW vs REPEAT distinction
        if kind == "READING" and target in self._corpora:
            c = self._corpora[target]
            nov_payoff = (ACTIVITY_NOVELTY_PAYOFF["READING_NEW"]
                          if c.is_new(self.tick)
                          else ACTIVITY_NOVELTY_PAYOFF["READING_REREAD"])
        elif kind == "ATTENDING" and target in self._sensory_items:
            s = self._sensory_items[target]
            nov_payoff = (ACTIVITY_NOVELTY_PAYOFF["ATTENDING_NEW"]
                          if s.is_new()
                          else ACTIVITY_NOVELTY_PAYOFF["ATTENDING_REPEAT"])
        elif kind == "ATTENDING_VISUAL" and target in self._pictures:
            # Fallback — should not reach here (handled above)
            p = self._pictures[target]
            nov_payoff = ACTIVITY_NOVELTY_PAYOFF["ATTENDING_VISUAL_REPEAT"]
        elif kind == "ATTENDING_AUDIO" and target in self._sounds:
            snd = self._sounds[target]
            nov_payoff = (ACTIVITY_NOVELTY_PAYOFF["ATTENDING_AUDIO_NEW"]
                          if snd.get("times_attended", 0) == 0
                          else ACTIVITY_NOVELTY_PAYOFF["ATTENDING_AUDIO_REPEAT"])
        elif kind == "ATTENDING_VIDEO" and target in self._videos:
            v = self._videos[target]
            nov_payoff = (ACTIVITY_NOVELTY_PAYOFF["ATTENDING_VIDEO_NEW"]
                          if v.is_new()
                          else ACTIVITY_NOVELTY_PAYOFF["ATTENDING_VIDEO_REPEAT"])
        else:
            nov_payoff = ACTIVITY_NOVELTY_PAYOFF.get(kind, 0.0)

        stab_payoff = ACTIVITY_STABILITY_PAYOFF.get(kind, 0.0)
        conn_payoff = ACTIVITY_CONNECTION_PAYOFF.get(kind, 0.0)

        # Signed-distance dot payoff
        score = (sd["novelty"] * nov_payoff
                 + sd["stability"] * stab_payoff
                 + sd["connection"] * conn_payoff)

        # Presence boost
        any_present = any(
            self.coordinator._presence.get(s, False)
            and self.coordinator._pair_bond.get(s, False)
            for s in PAIR_BOND_SOURCES)
        if any_present:
            if kind == "EMITTING":
                score += 0.05
            elif kind == "ATTENDING":
                score += 0.015

        score += 0.01  # baseline
        return score

    def _select_next_activity(self):
        # UNPAUSE: forced activity override (used by force_dream endpoint)
        if hasattr(self, '_force_next_activity') and self._force_next_activity:
            kind, target = self._force_next_activity
            self._force_next_activity = None
            budget = ACTIVITY_TICK_BUDGETS.get(kind, 5000)
            return Activity(kind=kind, target=target,
                            started_tick=self.tick,
                            expected_end_tick=self.tick + budget)
        candidates = self._candidate_activities()
        scored = [(self._action_salience(k, t), k, t) for k, t in candidates]
        scored.sort(reverse=True)
        score, kind, target = scored[0]
        budget = ACTIVITY_TICK_BUDGETS.get(kind, 500)
        return Activity(
            kind=kind, target=target,
            started_tick=self.tick,
            expected_end_tick=self.tick + budget,
            metadata={"salience": round(score, 4),
                      "top_scores": [(round(s, 4), k, t)
                                     for s, k, t in scored[:5]]},
        )

    def _start_activity(self, activity):
        self._current_activity = activity
        self._log_substrate_event("activity_started",
                                 kind=activity.kind, target=activity.target,
                                 salience=activity.metadata.get("salience"))

    def _end_activity(self):
        if self._current_activity:
            self._log_substrate_event("activity_ended",
                                     kind=self._current_activity.kind,
                                     target=self._current_activity.target,
                                     duration=self.tick - self._current_activity.started_tick)
            if self._current_activity.kind == "DREAMING":
                try:
                    state_dir = os.environ.get("STATE_DIR", "/mnt/efs/guala")
                    gate_path = os.path.join(state_dir, "dream_gate_cleared.json")
                    with open(gate_path, "w") as f:
                        json.dump({"cleared_at_tick": self.tick,
                                   "via": "substrate_dream_end"}, f)
                        f.flush(); os.fsync(f.fileno())
                    self._log_substrate_event("dream_gate_cleared", tick=self.tick)
                except Exception as e:
                    self._log_substrate_event("dream_gate_write_failed",
                                              tick=self.tick, error=str(e))
            self._activity_history.append(self._current_activity)
            if len(self._activity_history) > 500:
                self._activity_history = self._activity_history[-200:]
            self._current_activity = None

    # ── Activity tick effects ──

    def _atick_reading(self, a):
        """Read one sentence from corpus. read_sentence handles tick advancement."""
        corpus = self._corpora.get(a.target)
        if not corpus or not corpus.lines:
            return
        pos = corpus.position % len(corpus.lines)
        line = corpus.lines[pos]
        self.read_sentence(line, source="corpus")
        corpus.position += 1
        corpus.last_read_tick = self.tick
        if corpus.position >= len(corpus.lines):
            corpus.position = 0
            corpus.times_read_through += 1
            self._log_substrate_event("corpus_completed",
                                     corpus_id=corpus.corpus_id,
                                     title=corpus.title,
                                     times_through=corpus.times_read_through)
        # Novelty effect: reading new material satisfies novelty
        if corpus.is_new(self.tick):
            self.needs.novelty = saturate(self.needs.novelty, 0.001)
        else:
            self.needs.novelty = max(0.0, self.needs.novelty - 0.0003)

    def _atick_sleeping(self, a):
        """Sleep raises stability. Transitions to dream at midpoint."""
        self.needs.stability = saturate(self.needs.stability, 0.001)
        # GL-FIX-SLEEP-DECAY: removed duplicate decay call.
        # The general non-reading path (line ~1753) already calls
        # atlas.decay() every 10 ticks for ALL non-reading activities
        # including SLEEPING. The extra decay here was double-counting,
        # causing ~40% strength loss during every sleep/dream cycle.
        # Midpoint → dream
        midpoint = a.started_tick + (a.expected_end_tick - a.started_tick) // 2
        if self.tick == midpoint:
            a.kind = "DREAMING"
            self._log_substrate_event("dream_began", from_sleep=True)

    def _atick_dreaming(self, a):
        """Dream: stability restoration + consolidation via replay reinforcement.
        No novelty gain — dream recombines existing material.
        LTP-on-replay: sampled atlas entries get reinforced (bug #3 fix).
        v8 (GL-BRIEF-032): deep atlas promotion gate runs after consolidation."""
        self.needs.stability = saturate(self.needs.stability, 0.0005)
        if self.tick % 200 == 0:
            # Dream recall + consolidation (UNCHANGED — task 65)
            dream_words = []
            dream_pics = []
            reinforced_addresses = []
            reinforcement_count = 0
            pre_strength = self.atlas.total_strength()
            chi_keys = list(self.atlas.entries.keys())
            if chi_keys:
                sample_chis = [chi_keys[i % len(chi_keys)]
                               for i in range(self.tick % max(1, len(chi_keys)),
                                              min(self.tick % max(1, len(chi_keys)) + 3, len(chi_keys)))]
                for chi_k in sample_chis:
                    for e in self.atlas.entries.get(chi_k, []):
                        sec_name = e.get("section", "")
                        mid = e.get("motif", 0)
                        # Consolidation: reinforce this binding (LTP-on-replay)
                        # Same path as waking re-encounter, dream salience 0.3
                        # GL-BRIEF-DREAM-PROTECTION-FIX: dream consolidation
                        # earns metaplastic protection (slow channel via dwell gate)
                        self.atlas.record(sec_name, mid, chi_k, self.tick,
                                          salience=0.3, dwell_ticks=DWELL_GATE_META,
                                          arousal=0.2, valence=0.0, surprise=0.0)
                        reinforced_addresses.append(chi_k)
                        reinforcement_count += 1
                        if sec_name in self.sections:
                            sec = self.sections[sec_name]
                            if mid < len(sec.modes):
                                _, _, w = sec.modes[mid]
                                if w and w not in dream_words:
                                    dream_words.append(w)
                        if sec_name == "sight" and hasattr(self, 'sight'):
                            for sm in self.sight.motifs:
                                if sm.motif_id == mid and sm.source_history:
                                    sid = sm.source_history[-1]
                                    if sid in self._pictures and sid not in dream_pics:
                                        dream_pics.append(sid)
            post_strength = self.atlas.total_strength()
            content = " ".join(dream_words[:4]) if dream_words else ""
            self._log_substrate_event("dream_artifact",
                                     content=content,
                                     picture_ids=dream_pics,
                                     reinforced_atlas_addresses=reinforced_addresses[:10],
                                     reinforcement_count=reinforcement_count,
                                     pre_strength_sum=round(pre_strength, 2),
                                     post_strength_sum=round(post_strength, 2))

            # ── Deep Atlas promotion gate (GL-BRIEF-032) ──
            # Record survival snapshots for Path A
            for chi_k, entries in self.atlas.entries.items():
                for e in entries:
                    key = (chi_k, e.get("section", ""), e.get("motif", 0))
                    self._deep_survival_history[key].append(e["strength"])
                    # Cap history length
                    if len(self._deep_survival_history[key]) > 20:
                        self._deep_survival_history[key] = \
                            self._deep_survival_history[key][-10:]

            # Run promotion gate
            promoted = self.deep_atlas.dream_promotion_gate(
                self.atlas, self.tick, self._deep_survival_history)

            # Log promotions + post-promotion release (GL-BRIEF-033 C)
            for path, chi_k, sec, mid in promoted:
                self._log_substrate_event("deep_promotion",
                    path=path, section=sec, motif=mid, chi=chi_k)
                # C: release working entry to fast channel
                self.atlas.release_to_fast(chi_k, sec, mid)
                self._log_substrate_event("deep_release",
                    section=sec, motif=mid, chi=chi_k)
            # Log recent gate rejects (already accumulated in deep_atlas.gate_rejects)
            for rej in self.deep_atlas.gate_rejects[-5:]:
                self._log_substrate_event("deep_gate_reject", **rej)
            self.deep_atlas.gate_rejects = []  # clear after logging

            # Deep atlas decay + prune
            # GL-BRIEF-SLEEP-DECAY-PERMANENT: pause-idempotent
            _paused = os.environ.get("DECAY_PAUSED", "0") == "1"
            self.deep_atlas.decay(self.tick,
                                  rate_scale=0.0 if _paused else 1.0)
            if not _paused:
                self.deep_atlas.prune()

            # Log deep_size
            deep_size = self.deep_atlas.live_count()
            self._log_substrate_event("deep_size",
                n_entries=deep_size,
                total_strength=round(self.deep_atlas.total_strength(), 2),
                growth=deep_size - self._deep_last_size)
            self._deep_last_size = deep_size

    def _atick_playing(self, a):
        """Free-settle: chi space walk. No novelty gain — internal
        exploration doesn't introduce new experience."""
        # Occasionally check for emission trigger during play
        if self.tick % 300 == 0:
            self._check_emission_trigger("play_cohesion")

    def _atick_attending(self, a):
        """Attend to a sensory item (picture/sound). High novelty if new."""
        si = self._sensory_items.get(a.target)
        if not si:
            return
        if si.is_new():
            self.needs.novelty = saturate(self.needs.novelty, 0.002)
        # No novelty gain for repeat attendance (familiar exposure)
        # Mark attended at activity end
        if self.tick >= a.expected_end_tick - 1:
            si.times_attended += 1
            si.last_attended_tick = self.tick

    def process_sight_frame(self, grid):
        """GL-BRIEF-SENSORY-IO Part C: feed a transient camera frame into
        sight krimelack. No PictureItem, no storage. Just krimelack + atlas."""
        self._last_frame_tick = self.tick
        from dsf_ai_service.visual_krimelack import view_picture
        with self.lock:
            fragments = view_picture(grid, source_id="camera_stream",
                                     born_tick=self.tick, seed=self.tick % 10000,
                                     n_fixations=3, ticks_per_fixation=50)
            if not fragments:
                return
            motif, is_new, overlap = self.sight.process_viewing(
                fragments, "camera_stream", self.tick)
            if motif:
                chi_val = motif.motif_id % 100
                self.atlas.record("sight", motif.motif_id, chi_val,
                                  self.tick, salience=0.8,
                                  sensory_refs=["cam:live"],
                                  **self._affect_kwargs())
                self._log_substrate_event("sight_frame_bound",
                                          motif_id=motif.motif_id,
                                          chi=chi_val, is_new=is_new)

    def process_sound_frame(self, audio_bytes):
        """GL-BRIEF-SENSORY-IO Part D: feed a transient mic audio chunk into
        sound krimelack. No _sounds entry, no storage. Just cochlear + atlas."""
        import struct, wave, io, numpy as np
        with self.lock:
            try:
                # Try reading as WAV first
                wf = wave.open(io.BytesIO(audio_bytes), 'rb')
                sr = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
                if wf.getsampwidth() == 2:
                    samples = np.array(struct.unpack(f'<{n_frames}h', raw),
                                       dtype=np.float64) / 32768.0
                else:
                    samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float64) / 128.0 - 1.0
                wf.close()
            except Exception:
                # Raw bytes — treat as 8-bit unsigned mono at 16kHz
                samples = np.frombuffer(audio_bytes, dtype=np.uint8).astype(np.float64) / 128.0 - 1.0
                sr = 16000
            if len(samples) < 10:
                return
            # Downsample to 200 Hz for cochlear (same as /addsound)
            from dsf_ai_service.substrate.senses.GL_MDL_AUDITORY_CORTEX_WC_20260608_01 import cochlear_transduce
            target_sr = 200
            step = max(1, sr // target_sr)
            downsampled = samples[::step]
            cochlear = cochlear_transduce(downsampled, sample_rate=target_sr)
            for bn, c in cochlear.items():
                if c["n_events"] > 0:
                    chi = c["winding"] % 100
                    self.atlas.record(f"audio_{bn}",
                        deterministic_motif_id("mic_stream"),
                        chi, self.tick, salience=0.6, dwell_ticks=2,
                        sensory_refs=["mic:live"],
                        **self._affect_kwargs())

    def _atick_attending_visual(self, a):
        """Phase 2: Attend to a picture — saccaded foveation through krimelack."""
        from dsf_ai_service.visual_krimelack import view_picture
        pic = self._pictures.get(a.target)
        if not pic:
            return
        # Run full viewing at activity start (once per activity)
        if not a.metadata.get("_viewed"):
            # GL-CMD-EPISODE-BINDING C2.3: episode_ref fixed at activity start
            a.metadata["_episode_ref"] = (
                f"episode:attending_visual:{a.started_tick}:{a.target}")
            fragments = view_picture(
                pic.intensity_grid, source_id=pic.item_id,
                born_tick=self.tick, seed=self.tick % 10000)
            self._visual_fragments.extend(fragments)
            # Process through sight section
            motif, is_new, overlap = self.sight.process_viewing(
                fragments, pic.item_id, self.tick)
            if motif:
                # Record in atlas for cross-modal binding
                chi_val = motif.motif_id % 100  # simplified chi address
                presence, location, sky_state = self._current_situation()
                self.atlas.record("sight", motif.motif_id, chi_val,
                                 self.tick, salience=1.2,
                                 sensory_refs=[f"pic:{pic.item_id}"],
                                 bundle_id=f"item:pic:{pic.item_id}",
                                 episode_ref=a.metadata["_episode_ref"],
                                 presence=presence, location=location,
                                 sky_state=sky_state, source="attending_visual",
                                 **self._affect_kwargs())
                self._log_substrate_event(
                    "visual_motif_committed" if is_new else "visual_motif_fired",
                    motif_id=motif.motif_id, overlap=round(overlap, 3),
                    source_id=pic.item_id, n_fragments=len(fragments))
            a.metadata["_viewed"] = True
            a.metadata["n_fragments"] = len(fragments)
        # Novelty effect — discounted by familiarity
        fam = self.target_familiarity.get(a.target, 0.0)
        base_gain = 0.003 if pic.is_new() else 0.0005
        gain = base_gain * (1.0 - fam)  # familiar pictures give less novelty
        self.needs.novelty = saturate(self.needs.novelty, gain)
        # Mark attended at end + update familiarity
        if self.tick >= a.expected_end_tick - 1:
            pic.times_attended += 1
            pic.last_attended_tick = self.tick
            old_fam = self.target_familiarity.get(a.target, 0.0)
            new_fam = min(0.9, old_fam + 0.2)
            self.target_familiarity[a.target] = new_fam
            self._log_substrate_event("target_familiarity_update",
                                      picture_id=a.target,
                                      old=round(old_fam, 3),
                                      new=round(new_fam, 3))

    def _atick_attending_audio(self, a):
        """Phase 3 (042): Attend to audio — run cochlear bands through atlas."""
        snd = self._sounds.get(a.target)
        if not snd:
            return
        # GL-CMD-EPISODE-BINDING C2.3: episode_ref fixed at activity start
        if "_episode_ref" not in a.metadata:
            a.metadata["_episode_ref"] = (
                f"episode:attending_audio:{a.started_tick}:{a.target}")
        ep_ref = a.metadata["_episode_ref"]
        presence, location, sky_state = self._current_situation()
        # Record attendance
        snd["times_attended"] = snd.get("times_attended", 0) + 1
        snd["last_attended_tick"] = self.tick
        # Bind cochlear bands into atlas (same path as upload, reinforces on re-attend)
        cochlear = snd.get("cochlear", {})
        for band_name, c in cochlear.items():
            chi = c.get("winding", 0) % 100  # 1.1
            self.atlas.record(f"audio_{band_name}", deterministic_motif_id(a.target),
                              chi, self.tick, salience=1.2, dwell_ticks=8,
                              sensory_refs=[f"snd:{a.target}"],
                              bundle_id=f"item:snd:{a.target}",
                              episode_ref=ep_ref, presence=presence,
                              location=location, sky_state=sky_state,
                              source="attending_audio",
                              **self._affect_kwargs())
        # Novelty satisfies
        if snd.get("times_attended", 0) <= 3:
            self.needs.novelty = saturate(self.needs.novelty, 0.01)
        # Log first attendance
        if snd.get("times_attended", 0) == 1:
            self._log_substrate_event("sound_motif_founded",
                                      item_id=a.target, title=snd.get("title", ""))

    def _atick_attending_video(self, a):
        """Phase 2: Attend to video — saccade across decoded frames."""
        vid = self._videos.get(a.target)
        if not vid:
            return
        # Load frames on demand
        if not a.metadata.get("_viewed"):
            try:
                import os
                frame_files = sorted(
                    f for f in os.listdir(vid.frame_dir)
                    if f.endswith('.npy'))
                # Saccade across a sample of frames (not all)
                from dsf_ai_service.visual_krimelack import view_picture
                sample_step = max(1, len(frame_files) // 10)
                all_fragments = []
                for i in range(0, len(frame_files), sample_step):
                    frame = np.load(os.path.join(vid.frame_dir, frame_files[i]))
                    frags = view_picture(
                        frame, source_id=vid.item_id,
                        born_tick=self.tick + i, seed=(self.tick + i) % 10000,
                        n_fixations=4, ticks_per_fixation=100)
                    all_fragments.extend(frags)
                self._visual_fragments.extend(all_fragments)
                motif, is_new, overlap = self.sight.process_viewing(
                    all_fragments, vid.item_id, self.tick)
                if motif:
                    chi_val = motif.motif_id % 100
                    self.atlas.record("sight", motif.motif_id, chi_val,
                                     self.tick, salience=1.2,
                                     sensory_refs=[f"vid:{vid.item_id}"],
                                     **self._affect_kwargs())
                    self._log_substrate_event(
                        "video_motif_committed" if is_new else "video_motif_fired",
                        motif_id=motif.motif_id, overlap=round(overlap, 3),
                        source_id=vid.item_id, n_fragments=len(all_fragments))
                a.metadata["_viewed"] = True
            except Exception as e:
                self._log_substrate_event("video_attend_error", error=str(e))
                a.metadata["_viewed"] = True
        if vid.is_new():
            self.needs.novelty = saturate(self.needs.novelty, 0.004)
        # No novelty gain for repeat video attendance
        if self.tick >= a.expected_end_tick - 1:
            vid.times_attended += 1
            vid.last_attended_tick = self.tick

    def _atick_emitting(self, a):
        """Emission: fires once at start, satisfies connection-need."""
        if self.tick == a.started_tick + 1:
            self._do_emit()
            # Emission satisfies connection-need substantially
            any_pair_present = any(
                self.coordinator._presence.get(s, False)
                and self.coordinator._pair_bond.get(s, False)
                for s in PAIR_BOND_SOURCES)
            if any_pair_present:
                self.needs.connection = saturate(self.needs.connection, 0.25)

    def _check_emission_trigger(self, reason):
        """During play/attending, check if emission should fire."""
        if self.tick - self._last_emission_tick < EMISSION_COOLDOWN_TICKS:
            return
        any_present = any(
            self.coordinator._presence.get(s, False)
            and self.coordinator._pair_bond.get(s, False)
            for s in PAIR_BOND_SOURCES)
        if not any_present:
            self._log_substrate_event("emission_suppressed_no_presence",
                                     reason=reason)
            return
        # Interrupt current activity → emit
        if self._current_activity and self._current_activity.kind != "EMITTING":
            self._end_activity()
            em = Activity(
                kind="EMITTING", target=None,
                started_tick=self.tick,
                expected_end_tick=self.tick + ACTIVITY_TICK_BUDGETS["EMITTING"],
                metadata={"trigger": reason})
            self._start_activity(em)

    def _do_emit(self):
        """Generate an autonomous emission via invariants (respects EMISSION_MODE).
        Falls back to SVO recall only if invariants return nothing."""
        self._last_emission_tick = self.tick
        recent_chis = []
        for sec in self.sections.values():
            for c in sec.commits[-5:]:
                recent_chis.append(c["chi"])
        if not recent_chis:
            self._log_substrate_event("emission",
                                     content="...",
                                     to_sources=[s for s in PAIR_BOND_SOURCES
                                                 if self.coordinator._presence.get(s, False)])
            return

        # Use the invariants path (grandurun or topk per EMISSION_MODE)
        input_words = []  # autonomous — no input words to exclude
        content = self._emit_from_invariants(recent_chis, input_words,
                                             v7_session=getattr(self, '_v7_session', None))

        # Fallback to SVO recall if invariants found nothing
        if not content:
            recalled = {}
            for sec_name in ("subject", "verb", "object"):
                word = self._recall_from_atlas(sec_name, recent_chis,
                                               exclude_words=set())
                if word:
                    recalled[sec_name] = word
            content = " ".join(recalled[k] for k in ("subject", "verb", "object")
                               if k in recalled) or "..."

        # Sight recall — find pictures bound at recent chi addresses
        recalled_pics = self._recall_sight_from_atlas(recent_chis, [])
        pic_ids = [sid for _, sid in recalled_pics] if recalled_pics else []

        to_sources = [s for s in PAIR_BOND_SOURCES
                      if self.coordinator._presence.get(s, False)
                      and self.coordinator._pair_bond.get(s, False)]
        self._log_substrate_event("emission", content=content,
                                 to_sources=to_sources,
                                 picture_ids=pic_ids)

        # 1.9: Ladder metrics
        words = content.split() if content and content != "..." else []
        self._total_emissions += 1
        self._emission_lengths.append(len(words))
        if len(self._emission_lengths) > 100:
            self._emission_lengths = self._emission_lengths[-50:]
        if any(w.endswith("?") or content.startswith("what") for w in words):
            self._question_count += 1
        # Novel word-bag rate (not phrase-structure novelty — sorted so order-invariant).
        # Eve: "sat the cat" and "the cat sat" hash to the same triple — correct.
        # This measures word-bag novelty, not subject-verb-object arrangement.
        # Real phrase-structure novelty requires R3 and is not yet implemented.
        if len(words) >= 2:
            _triple = tuple(sorted(w.lower() for w in words[:4]))
            if not hasattr(self, '_seen_triples'):
                self._seen_triples = set()
            if _triple not in self._seen_triples:
                self._novel_compositions += 1
                self._seen_triples.add(_triple)
                if len(self._seen_triples) > 5000:
                    self._seen_triples = set(list(self._seen_triples)[-2500:])

        # v8 (GL-BRIEF-028): open response window from Guala's emission
        if recent_chis:
            self._open_response_window("guala", recent_chis,
                                       source_context={"content": content})

    # ------------------------------------------------------------------
    # v8: Response Binding (GL-BRIEF-028)
    # ------------------------------------------------------------------

    def _open_response_window(self, emitter, context_anchor_chis, source_context=None):
        """Open a response window. context_anchor_chis = list of chi-keys."""
        window = {
            "emitter": emitter,
            "context_anchor_chis": list(context_anchor_chis),
            "opened_at_tick": self.tick,
            "expires_at_tick": self.tick + self.RESPONSE_WINDOW_TICKS,
            "n_responses_bound": 0,
            "source_context": source_context or {},
        }
        self.open_response_windows.append(window)
        self._log_substrate_event("response_window_opened",
                                  emitter=emitter,
                                  context_anchor_chis=context_anchor_chis[:5],
                                  expires_at=window["expires_at_tick"])

    def _prune_response_windows(self):
        """Prune expired windows. Called from _autonomy_tick."""
        still_open = []
        for w in self.open_response_windows:
            if w["expires_at_tick"] >= self.tick:
                still_open.append(w)
            else:
                self._log_substrate_event("response_window_expired",
                                          emitter=w["emitter"],
                                          n_responses_bound=w["n_responses_bound"],
                                          opened_at=w["opened_at_tick"])
        self.open_response_windows = still_open

    def _get_response_contexts(self, current_source):
        """Get context_anchor_chis from open windows by OTHER emitters."""
        contexts = []
        for w in self.open_response_windows:
            if (w["emitter"] != current_source
                    and w["expires_at_tick"] >= self.tick):
                contexts.extend(w["context_anchor_chis"])
        return contexts

    def _tag_response_bindings(self, chi_value, section_name, motif_id, current_source,
                               log_event=True):
        """If input arrives during an open response window from another emitter,
        cross-link the new atlas entry to the context anchors."""
        response_contexts = self._get_response_contexts(current_source)
        if not response_contexts:
            return

        # Tag the NEW entry with response_context
        for e in self.atlas.entries.get(chi_value, []):
            if e.get("section") == section_name and e.get("motif") == motif_id:
                existing_ctx = e.get("response_context", [])
                new_ctx = list(set(existing_ctx + response_contexts))
                e["response_context"] = new_ctx
                break

        # Bidirectional: tag the CONTEXT ANCHOR entries with received_response.
        # Always append + cap at 20 — duplicates are harmless (set-reduced at read time).
        # Avoids O(n) membership check on a growing list AND O(n) set() construction.
        for anchor_chi in response_contexts:
            for d in range(-self.atlas.band, self.atlas.band + 1):
                for e in self.atlas.entries.get(anchor_chi + d, []):
                    received = e.get("received_response")
                    if received is None:
                        e["received_response"] = [chi_value]
                    elif len(received) < 20:
                        received.append(chi_value)
                    else:
                        received[0] = chi_value   # overwrite oldest slot

        # Count and log (only once per converse call, not per entry)
        for w in self.open_response_windows:
            if (w["emitter"] != current_source
                    and w["expires_at_tick"] >= self.tick):
                w["n_responses_bound"] += 1

        self._response_bind_count += 1
        if log_event:
            delta_t = self.tick - min(
                w["opened_at_tick"] for w in self.open_response_windows
                if w["emitter"] != current_source and w["expires_at_tick"] >= self.tick)
            self._log_substrate_event("response_bound",
                                      context_anchor_chis=response_contexts[:3],
                                      input_chi=chi_value,
                                      section=section_name,
                                      source=current_source,
                                      delta_t_ticks=delta_t)

    # ------------------------------------------------------------------
    # GL-CMD-TEACHER-CORRECTION-BINDING-EVE-20260618-12
    # ------------------------------------------------------------------

    def apply_teacher_correction(self, original_input, her_emission,
                                  correct, expected_response=None,
                                  source="joe", correction_affect=None,
                                  tick=None, emission_id=None,
                                  story=None, temporal=None,
                                  sensory_freetext=None,
                                  corrected_text=None):
        """Full teacher-correction event. Encodes the corrected experience
        as a consolidated cofire-bound binding with source, affect, and
        sensory context.

        - Thumbs-up: reinforce emission bindings, cofire-bind input↔emission.
        - Thumbs-down with expected: weaken emission bindings, ingest
          expected as heard utterance, cofire-bind input↔expected with
          high salience.
        - Thumbs-down without expected: weaken only.
        """
        with self.lock:
            correction_tick = tick or self.tick

            # Snapshot context
            needs_snapshot = {
                "novelty": getattr(self.needs, "novelty", 0.5),
                "connection": getattr(self.needs, "connection", 0.5),
            }
            activity_snapshot = None
            if self._current_activity:
                activity_snapshot = self._current_activity.snapshot() if hasattr(
                    self._current_activity, 'snapshot') else str(self._current_activity)

            # Compute content-word chis for original input
            input_words = _normalize_text(original_input)
            input_content = [w for w in input_words
                             if w.lower() not in self._FUNCTION_WORDS and len(w) > 1]
            if not input_content:
                input_content = input_words[:3]
            input_chis = []
            for w in input_content:
                k = LanguageKrimelack()
                k.transduce(w)
                input_chis.append(k.winding)

            # Compute chis for her emission
            emission_words = _normalize_text(her_emission)
            emission_chis = []
            for w in emission_words:
                k = LanguageKrimelack()
                k.transduce(w)
                emission_chis.append(k.winding)

            affected = []

            if correct:
                # GL-CMD-TEACHER-SUBSTRATE-TRUE: thumbs-up via atlas.record()
                # — goes through conservation, salience-modulated, source-tagged.
                # Filtered to emission words (prevents O(n²) blowup from
                # running conservation pass on every binding in the neighborhood).
                _sal_up = self._compute_salience(source=source)
                # source_w * pair_bond (static component) drives valence rise
                _sw = {"joe": 1.6, "wc": 1.6, "c1": 1.2,
                       "corpus": 0.5, "guala": 0.5, "unknown": 0.7}
                _pb = 1.2 if self.coordinator._pair_bond.get(source, False) else 1.0
                _val_delta_up = BASE_REINFORCEMENT * _sw.get(source, 0.7) * _pb
                _emission_words_set = set(w.lower() for w in emission_words)
                ep_ref = f"correction:{emission_id}" if emission_id else None
                for chi in emission_chis:
                    for d in range(-self.atlas.band, self.atlas.band + 1):
                        for e in list(self.atlas.entries.get(chi + d, [])):
                            if e["strength"] < FORGETTING_THRESHOLD:
                                continue
                            # Match emission words in language sections only.
                            # Non-language sections (sight, sound, etc.) are
                            # not addressed by a language correction — skip.
                            sec = self.sections.get(e.get("section", ""))
                            if sec and e.get("motif", 0) < len(sec.modes):
                                _, _, wl = sec.modes[e["motif"]]
                                if not wl or wl.lower() not in _emission_words_set:
                                    continue
                            else:
                                continue
                            new_val = min(1.0, e.get("valence", 0.0) + _val_delta_up)
                            self.atlas.record(
                                e.get("section", "object"),
                                e.get("motif", 0),
                                chi + d,
                                tick=correction_tick,
                                salience=_sal_up,
                                valence=new_val,
                                source=source,
                                episode_ref=ep_ref,
                            )
                            affected.append({
                                "chi": chi + d,
                                "section": e.get("section"),
                                "motif": e.get("motif"),
                                "action": "reinforce",
                                "new_strength": e["strength"],
                            })
                # Cofire-bind input↔emission
                for in_chi in input_chis:
                    for em_chi in emission_chis:
                        if in_chi != em_chi:
                            self.atlas.record(
                                "verb", deterministic_motif_id("cofire_bind"),
                                (in_chi + em_chi) // 2,
                                tick=correction_tick,
                                salience=1.5,
                                dwell_ticks=3,
                                source=source,
                                sensory_refs=[f"correction:{source}:thumbs_up"],
                            )
            else:
                # GL-CMD-TEACHER-SUBSTRATE-TRUE: thumbs-down — direct write
                # with source-derived delta (no atlas.record() — no LivingAtlas
                # mechanism for valence decrement; direct write stays but delta
                # is substrate-derived, not hardcoded).
                _sw_d = {"joe": 1.6, "wc": 1.6, "c1": 1.2,
                         "corpus": 0.5, "guala": 0.5, "unknown": 0.7}
                _pb_d = 1.2 if self.coordinator._pair_bond.get(source, False) else 1.0
                _val_delta_down = BASE_REINFORCEMENT * _sw_d.get(source, 0.7) * _pb_d
                # Strength delta matches BASE_REINFORCEMENT (same as thumbs-up).
                _str_delta_down = BASE_REINFORCEMENT
                # Weaken emission bindings
                for chi in emission_chis:
                    for d in range(-self.atlas.band, self.atlas.band + 1):
                        for e in self.atlas.entries.get(chi + d, []):
                            if e["strength"] < FORGETTING_THRESHOLD:
                                continue
                            # Match emission words
                            sec = self.sections.get(e.get("section", ""))
                            if sec and e.get("motif", 0) < len(sec.modes):
                                _, _, wl = sec.modes[e["motif"]]
                                if wl and wl.lower() in set(
                                        w.lower() for w in emission_words):
                                    e["strength"] = max(0.0,
                                                        e["strength"] - _str_delta_down)
                                    # Negative valence floor is -1.0 (not 0.0).
                                    # Negative bindings suppressed in cross-modal cm
                                    # via max(0.0, 1.0 + valence) formula.
                                    e["valence"] = max(-1.0,
                                                       e.get("valence", 0.0) - _val_delta_down)
                                    affected.append({
                                        "chi": chi + d,
                                        "section": e["section"],
                                        "motif": e["motif"],
                                        "action": "weaken",
                                        "new_strength": e["strength"],
                                    })

                # Also weaken in emission system mode_strength if available
                if self._emission_system:
                    for sec_name in self._EMISSION_SECTIONS:
                        sec = self._emission_system.sections.get(sec_name)
                        if sec and hasattr(sec, 'mode_strength'):
                            for i, ms in enumerate(sec.mode_strength):
                                w = self._emission_word_map.get(
                                    (sec_name, i))
                                if w and w.lower() in set(
                                        ew.lower() for ew in emission_words):
                                    sec.mode_strength[i] = max(
                                        0.0, ms - 0.05)

                effective_correction = corrected_text or expected_response
                if effective_correction:
                    # GL-CMD-TEACHER-SUBSTRATE-TRUE: corrected_text enters substrate
                    # at natural source-weight salience (no TEACHER_INPUT_SALIENCE_MULTIPLIER
                    # — pair_bond + source_weight already elevate joe/wc inputs).
                    try:
                        self.read_sentence(effective_correction, source=source)
                    except Exception:
                        for w in _normalize_text(effective_correction):
                            k = LanguageKrimelack()
                            k.transduce(w)
                            self.atlas.record(
                                "object", deterministic_motif_id(w),
                                k.winding, tick=correction_tick,
                                salience=self._compute_salience(source=source),
                                dwell_ticks=5,
                                source=source,
                            )

                    # GL-CMD-TEACHER-SUBSTRATE-TRUE: native episode_ref back-reference
                    # (replaces teaching_correction_for tag — same pattern as atlas
                    # episode_refs list on existing bindings).
                    if emission_id:
                        ep_ref = f"correction:{emission_id}"
                        for w in _normalize_text(effective_correction):
                            k = LanguageKrimelack()
                            k.transduce(w)
                            for d in range(-self.atlas.band, self.atlas.band + 1):
                                for e in self.atlas.entries.get(k.winding + d, []):
                                    if e.get("last_tick", 0) >= correction_tick:
                                        ep_refs = e.get("episode_refs", [])
                                        e["episode_refs"] = (ep_refs + [ep_ref])[-4:]

                    # Compute expected chis for cofire binding
                    expected_words = _normalize_text(effective_correction)
                    expected_chis = []
                    for w in expected_words:
                        k = LanguageKrimelack()
                        k.transduce(w)
                        expected_chis.append(k.winding)

                    # Cofire-bind input↔expected with HIGH salience
                    for in_chi in input_chis:
                        for ex_chi in expected_chis:
                            self.atlas.record(
                                "verb",
                                deterministic_motif_id("correction_bind"),
                                (in_chi + ex_chi) // 2,
                                tick=correction_tick,
                                salience=2.0,
                                dwell_ticks=5,
                                source=source,
                                sensory_refs=[
                                    f"correction:{source}:thumbs_down",
                                    f"correction_context:True",
                                ],
                            )
                    affected.append({
                        "action": "ingest_expected",
                        "expected": effective_correction,
                        "source": source,
                    })

            # Log the correction event
            self._log_substrate_event("teacher_correction",
                                      original_input=original_input,
                                      her_emission=her_emission,
                                      correct=correct,
                                      expected_response=expected_response,
                                      corrected_text=corrected_text,
                                      source=source,
                                      needs=needs_snapshot,
                                      activity=activity_snapshot,
                                      n_affected=len(affected),
                                      affected=affected[:10],
                                      emission_id=emission_id,
                                      story=story,
                                      temporal=temporal,
                                      sensory_freetext=sensory_freetext)

            return {
                "correct": correct,
                "n_affected": len(affected),
                "affected": affected,
            }

    def _self_hear(self, reply, responding_to_source):
        """GL-BRIEF-034: Self-hearing — Guala hears her own conversational reply.
        (1) read_sentence at 0.5x salience (no question generation, no recursion)
        (2) open "guala" response window with reply chi-keys
        (3) tag self-heard entries against open other-emitter windows
        Kill switch: SELF_HEARING_ENABLED env var."""
        import os
        if os.environ.get("SELF_HEARING_ENABLED", "1") == "0":
            return

        reply_words = _normalize_text(reply)
        if not reply_words:
            return

        # (1) Read reply into substrate at 0.5x conversational salience.
        # Suppress question generation by using _self_hearing flag.
        self._self_hearing = True
        tick_before = self.tick
        for i, word in enumerate(reply_words):
            if len(reply_words) == 1:
                hint = "standalone"
            elif i == 0:
                hint = "first"
            elif i == len(reply_words) - 1:
                hint = "last"
            else:
                hint = "middle"
            self.read_word(word, position_hint=hint, source="guala")
        tick_after = self.tick
        self._self_hearing = False

        # (2) Compute reply chi-keys and open "guala" response window
        reply_chis = []
        for w in reply_words:
            temp_krim = LanguageKrimelack()
            temp_krim.transduce(w)
            reply_chis.append(temp_krim.winding)

        if reply_chis:
            self._open_response_window("guala", reply_chis,
                                       source_context={"reply": reply[:50]})

        # (3) Tag self-heard entries against open windows from the other emitter.
        # FIX 1: scope to entries touched by THIS read only (tick window).
        # Cap at 10 total calls to bound O(n²) from reinstatement entries.
        _sh_tag_count = 0
        for ch in reply_chis:
            if _sh_tag_count >= 10:
                break
            for d in range(-self.atlas.band, self.atlas.band + 1):
                if _sh_tag_count >= 10:
                    break
                for e in self.atlas.entries.get(ch + d, []):
                    if _sh_tag_count >= 10:
                        break
                    if (e.get("last_tick", 0) > tick_before
                            and e.get("last_tick", 0) <= tick_after
                            and not e.get("response_context")):
                        self._tag_response_bindings(
                            ch + d, e["section"], e["motif"], "guala")
                        _sh_tag_count += 1

        # Event log
        self._log_substrate_event("self_heard",
                                  reply_summary=reply[:50],
                                  n_chis=len(reply_chis),
                                  salience="0.5x")

        # (4) Self-voice: generate espeak WAV and feed into sound krimelack
        #     Runs on background thread — must not block the converse response
        def _inject_self_voice(text):
            try:
                import subprocess
                wav_path = "/tmp/guala_self_voice.wav"
                subprocess.run([
                    "espeak-ng", "-v", "en+f3", "-p", "96", "-s", "145",
                    "-w", wav_path, text,
                ], check=True, timeout=5, capture_output=True)
                with open(wav_path, "rb") as f:
                    self.process_sound_frame(f.read())
            except Exception:
                pass
        threading.Thread(target=_inject_self_voice, args=(reply,),
                        daemon=True).start()

    # ------------------------------------------------------------------
    # Fix C (GL-FIX-THREE): Decay modulation — wC-only, presence-gated
    # ------------------------------------------------------------------

    def _wc_presence_active(self):
        """True if wC has active presence (same state as status presence.wc.present)."""
        return self.coordinator._presence.get("wc", False)

    def is_present_active(self):
        """True if interaction is in progress — defer non-critical saves."""
        tick = self.tick
        if (tick - getattr(self, '_last_converse_tick', 0)) < 50:
            return True
        if (tick - getattr(self, '_last_frame_tick', 0)) < 100:
            return True
        for who in ("wc", "joe"):
            if self.coordinator._presence.get(who, False):
                return True
        return False

    def is_natural_quiet_point(self):
        """Good moment to save without disruption."""
        if self.is_present_active():
            return False
        a = self._current_activity
        if a is None:
            return True
        if a.kind in ("SLEEPING", "DREAMING"):
            return True
        if hasattr(a, "started_tick") and (self.tick - a.started_tick) > 500:
            return True
        return False

    def request_decay_modulation(self, factor, source):
        """Scale working-atlas decay. wC-only, requires ACTIVE presence."""
        if source != "wc":
            raise PermissionError("decay modulation is wC-only system control")
        if not self._wc_presence_active():
            raise PermissionError("decay modulation requires ACTIVE wC presence")
        factor = max(0.0, min(1.0, float(factor)))
        self.decay_modulation = factor
        self._decay_mod_owner = "wc"
        self._log_substrate_event("decay_modulation_set",
                                  factor=factor, source="wc")
        return factor

    def reset_decay_modulation(self, source):
        if source != "wc":
            raise PermissionError("decay modulation is wC-only system control")
        self.decay_modulation = 1.0
        self._decay_mod_owner = None
        self._log_substrate_event("decay_modulation_reset", source="wc")

    def _auto_reset_decay_modulation(self):
        """Called when wC presence ends — auto-reset modulation."""
        if self._decay_mod_owner == "wc" and self.decay_modulation != 1.0:
            self.decay_modulation = 1.0
            self._decay_mod_owner = None
            self._log_substrate_event("decay_modulation_reset",
                                      source="wc", reason="presence_ended")

    def manual_sleep(self, state_dir="state"):
        """Manual sleep trigger from UI or deploy script."""
        with self.lock:
            if self._current_activity:
                self._end_activity()
            sleep = Activity(
                kind="SLEEPING", target=None,
                started_tick=self.tick,
                expected_end_tick=self.tick + ACTIVITY_TICK_BUDGETS["SLEEPING"],
                metadata={"trigger": "manual"})
            self._start_activity(sleep)
            self._log_substrate_event("sleep_manual", trigger="ui")
            # Sleep-during-deploy plumbing (GL-BRIEF-SLEEP-DURING-DEPLOY)
            try:
                self.save_full_state(state_dir)
            except Exception as e:
                print(f"[sleep] save_full_state failed: {e}")
                raise
            try:
                marker_path = os.path.join(state_dir, ".sleeping")
                with open(marker_path, 'w') as f:
                    json.dump({"sleep_tick": self.tick,
                               "sleep_ts": time.time()}, f)
            except Exception as e:
                print(f"[sleep] marker write failed: {e}")
            return {"event": "sleep_started", "tick": self.tick,
                    "expected_end_tick": sleep.expected_end_tick}

    def wake_from_sleep(self, state_dir="state"):
        """Transition out of SLEEPING activity. Clears the .sleeping
        marker. Called by the new task after load_full_state on deploy."""
        if self.is_asleep:
            self._end_activity()
            self._log_substrate_event("wake_from_sleep", tick=self.tick)
        try:
            marker_path = os.path.join(state_dir, ".sleeping")
            if os.path.exists(marker_path):
                os.remove(marker_path)
        except Exception as e:
            print(f"[wake] marker cleanup failed: {e}")

    def _activity_summary(self):
        """Summary of activity history for /status."""
        kinds = defaultdict(int)
        durations = defaultdict(int)
        for a in self._activity_history:
            kinds[a.kind] += 1
            durations[a.kind] += (a.expected_end_tick - a.started_tick)
        return {k: {"count": kinds[k], "total_ticks": durations[k]}
                for k in kinds}

    def get_recent_events(self, since_tick=-1, limit=50):
        """Return recent substrate events for /events endpoint."""
        events = [{"tick": e.tick, "kind": e.kind, "detail": e.detail}
                  for e in self._substrate_events if e.tick > since_tick]
        return events[-limit:]

    # ------------------------------------------------------------------
    # Persistence v5.5: Continuity Guarantees
    # GUALALOOM-V5-CONTINUITY-WC-2026-06-05
    # Identity tag, schema versioning, snapshots, event log, integrity
    # ------------------------------------------------------------------

    SCHEMA_VERSION = "v7.2.0"
    STATE_FILES = [
        "guala_core.json", "guala_needs.json", "guala_coordinator.json",
        "guala_atlas.json", "guala_sections.json", "guala_bucket.json",
    ]
    IDENTITY_FILE = "guala_identity.json"
    SLEEPING_MARKER = ".sleeping"
    EVENTS_LOG = "events.log"
    MAX_SNAPSHOTS = 20
    EVENTS_MAX_BYTES = 10 * 1024 * 1024  # 10MB per log file
    EVENTS_MAX_ROTATED = 9

    # Class-level defaults (overwritten per instance in __init__)
    _last_save_tick = 0
    _last_save_timestamp = None
    _load_successful = False
    _load_errors = []
    _integrity_errors = []
    _events_replayed_at_boot = 0
    _guala_identity = None

    # ── Identity ──

    def _generate_genesis_identity(self, state_dir):
        """First boot ever. Generate her identity. This never changes."""
        import uuid
        os.makedirs(state_dir, exist_ok=True)
        self._guala_identity = str(uuid.uuid4())
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        identity_data = {
            "schema_version": self.SCHEMA_VERSION,
            "guala_identity": self._guala_identity,
            "first_boot_timestamp": ts,
            "first_boot_notes": "Genesis. Pair-bond active. Seed corpus only.",
        }
        self._atomic_write(os.path.join(state_dir, self.IDENTITY_FILE), identity_data)
        print(f"[GualaLoom] GENESIS: identity={self._guala_identity} at {ts}")

    def _load_identity(self, state_dir):
        """Load identity from disk. Returns identity string or None."""
        path = os.path.join(state_dir, self.IDENTITY_FILE)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            d = json.load(f)
        return d.get("guala_identity")

    # ── Envelope: wraps every state file with identity + schema ──

    def _envelope(self, data):
        """Wrap data dict with identity + schema + timestamp."""
        return {
            "schema_version": self.SCHEMA_VERSION,
            "guala_identity": self._guala_identity,
            "saved_at_tick": self.tick,
            "saved_at_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data": data,
        }

    # Schema migrations
    COMPATIBLE_SCHEMAS = {"v5.5.0", "v6.0.0", "v7.0.0", "v7.1.0", "v7.2.0"}

    def _unwrap(self, raw, filename):
        """Validate envelope, return data dict. Raises on mismatch."""
        sv = raw.get("schema_version", "unknown")
        gi = raw.get("guala_identity", "unknown")
        if sv not in self.COMPATIBLE_SCHEMAS:
            raise ValueError(f"{filename}: schema {sv} not in {self.COMPATIBLE_SCHEMAS}")
        if gi != self._guala_identity:
            raise ValueError(f"{filename}: identity {gi} != {self._guala_identity}")
        return raw.get("data", raw)

    # ── Save ──

    def save_full_state(self, state_dir="state"):
        """Round-trip every mutable attribute. Atomic writes. Identity-stamped.
        GL-FIX-SAVE-LOCK: snapshot data under lock (fast), write to disk outside
        lock (slow). Lock hold time drops from ~20s to milliseconds."""
        import copy as _copy

        # ── Phase 1: snapshot under lock (milliseconds) ──
        with self.lock:
            os.makedirs(state_dir, exist_ok=True)
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            if self._guala_identity is None:
                self._generate_genesis_identity(state_dir)

            # 1. Core
            corpora_ser = {cid: {"corpus_id": c.corpus_id, "title": c.title,
                                  "position": c.position,
                                  "times_read_through": c.times_read_through,
                                  "last_read_tick": c.last_read_tick,
                                  "n_lines": len(c.lines)}
                           for cid, c in self._corpora.items()}
            sensory_ser = {sid: {"item_id": s.item_id, "kind": s.kind,
                                  "title": s.title,
                                  "times_attended": s.times_attended,
                                  "last_attended_tick": s.last_attended_tick}
                           for sid, s in self._sensory_items.items()}
            # Serialize survival history: tuple keys → "chi|section|motif" strings
            surv_ser = {}
            for (chi_k, sec, mid), strengths in self._deep_survival_history.items():
                key_str = f"{chi_k}|{sec}|{mid}"
                surv_ser[key_str] = strengths[-10:]  # cap at 10

            snap_core = self._envelope({
                "tick": self.tick, "read_count": self.read_count,
                "vocab": sorted(self.vocab),
                "source_history": dict(self.source_history),
                "recent_connection_boost": self.recent_connection_boost,
                "dream_log": _copy.copy(self.dream_log),
                "open_response_windows": _copy.copy(self.open_response_windows),
                "response_bind_count": self._response_bind_count,
                "last_emission_tick": self._last_emission_tick,
                "target_familiarity": {k: round(v, 4) for k, v in self.target_familiarity.items()},
                "corpora_state": corpora_ser,
                "sensory_state": sensory_ser,
                "deep_survival_history": surv_ser,
                "total_emissions": self._total_emissions,
            })

            # 2. Needs
            snap_needs = self._envelope({
                "stability": self.needs.stability,
                "novelty": self.needs.novelty,
                "connection": self.needs.connection,
            })

            # 3. Coordinator
            snap_coord = self._envelope({
                "pair_bond": dict(self.coordinator._pair_bond),
                "pair_bond_active": self.coordinator.pair_bond_active,
                "distress_ticks": self.coordinator.distress_ticks,
                "suffering_log": _copy.copy(self.coordinator.suffering_log),
                "need_history": list(self.coordinator.need_history[-200:]),
                "attentions_count": len(self.coordinator.attentions),
                "actions_count": len(self.coordinator.actions),
            })

            # 4. Atlas — serialize entries directly (faster than deepcopy)
            snap_atlas = self._envelope({
                "entries": {str(k): list(v)
                            for k, v in self.atlas.entries.items()},
                "tick": self.atlas.tick,
                # GL-SPC-HEMISPHERE-ARCH: cross-hemi links (empty at Phase 0)
                "cross_hemi_links": [],
            })

            # 5. Deep Atlas
            snap_deep = self._envelope(self.deep_atlas.to_json())

            # 6. Sections
            sections_data = {}
            for nm, sec in self.sections.items():
                modes_ser = [{"dsf": list(d.to_array().tolist()), "chi": c, "word": w}
                             for d, c, w in sec.modes]
                sections_data[nm] = {
                    "modes": modes_ser,
                    "commits": list(sec.commits[-5000:]),
                    "dead_zone": sec.dead_zone,
                    "gamma": dict(sec.gamma),
                    "tick": sec.tick,
                }
            snap_sections = self._envelope(sections_data)

            # 7. Bucket (removed — Phase E)
            snap_bucket = self._envelope({"removed": True})

            # 8. Visual
            snap_visual = self._envelope({
                "pictures": {
                    pid: {"item_id": p.item_id, "title": p.title,
                          "source": p.source, "shown_at_tick": p.shown_at_tick,
                          "times_attended": p.times_attended,
                          "last_attended_tick": p.last_attended_tick,
                          "has_grid": p.intensity_grid is not None,
                          "original_path": getattr(p, 'original_path', None),
                          "original_width": getattr(p, 'original_width', None),
                          "original_height": getattr(p, 'original_height', None)}
                    for pid, p in self._pictures.items()
                },
                "sight_motifs": [
                    {"motif_id": m.motif_id, "n_firings": m.n_firings,
                     "source_history": m.source_history[:20],
                     "founded_at_tick": m.founded_at_tick}
                    for m in self.sight.motifs
                ] if hasattr(self, 'sight') else [],
                "n_visual_fragments": len(self._visual_fragments),
            })
            # Snapshot picture grids (numpy arrays are immutable-ish, shallow copy OK)
            snap_pic_grids = {pid: p.intensity_grid
                              for pid, p in self._pictures.items()
                              if p.intensity_grid is not None}

            # 9. Sounds
            snap_sounds = self._envelope(dict(self._sounds))

            # 10. Videos
            snap_videos = self._envelope({
                vid: {"item_id": v.item_id, "title": v.title,
                      "source": getattr(v, 'source', ''),
                      "times_attended": v.times_attended,
                      "last_attended_tick": v.last_attended_tick}
                for vid, v in self._videos.items()
            })

            save_tick = self.tick
            snap_vocab_len = len(self.vocab)
            snap_atlas_count = sum(len(v) for v in self.atlas.entries.values())
        # ── lock released ──

        # ── T1.2: Regression sanity check — refuse to overwrite richer state ──
        core_path = os.path.join(state_dir, "guala_core.json")
        if os.path.exists(core_path):
            try:
                with open(core_path) as _f:
                    _existing = json.load(_f)
                _existing_data = _existing.get("data", _existing)
                _existing_vocab = len(_existing_data.get("vocab", []))
                if _existing_vocab > 100 and snap_vocab_len < _existing_vocab * 0.5:
                    msg = (f"[GualaLoom] ABORT SAVE: vocab regression "
                           f"{_existing_vocab}→{snap_vocab_len}. "
                           f"Refusing to overwrite. "
                           f"Set GUALA_FORCE_SAVE=1 to override.")
                    print(msg)
                    if os.environ.get("GUALA_FORCE_SAVE") != "1":
                        raise RuntimeError(msg)
            except (json.JSONDecodeError, OSError) as _e:
                print(f"[save] prior state read failed (proceeding): {_e}")

        # ── Phase 2: write to disk outside lock (seconds) ──
        results = {}
        writes = [
            ("guala_core.json", snap_core),
            ("guala_needs.json", snap_needs),
            ("guala_coordinator.json", snap_coord),
            ("guala_atlas.json", snap_atlas),
            ("guala_deep_atlas.json", snap_deep),
            ("guala_sections.json", snap_sections),
            ("guala_bucket.json", snap_bucket),
            ("guala_visual.json", snap_visual),
            ("guala_sounds.json", snap_sounds),
            ("guala_videos.json", snap_videos),
        ]
        for filename, data in writes:
            path = os.path.join(state_dir, filename)
            self._atomic_write(path, data)
            results[filename] = os.path.getsize(path)

        # GL-CMD-TEACHER-CORRECTION-UI: teaching data
        snap_teaching = self._envelope({
            "feedback_log": self._teaching_feedback_log[-500:],
            "correction_log": self._teaching_correction_log[-500:],
            "emission_records": dict(list(self._emission_records.items())[-EMISSION_RECORDS_CAP:]),
        })
        self._atomic_write(os.path.join(state_dir, "guala_teaching.json"), snap_teaching)

        # Picture grids
        pic_dir = os.path.join(state_dir, "pictures")
        os.makedirs(pic_dir, exist_ok=True)
        for pid, grid in snap_pic_grids.items():
            np.save(os.path.join(pic_dir, f"{pid}.npy"), grid)

        self._last_save_tick = save_tick
        self._last_save_timestamp = ts

        # GL-CMD-DEEP-ATLAS-PERSIST: emit save confirmation event
        _n_deep = self.deep_atlas.live_count()
        self._log_substrate_event("deep_atlas_saved",
                                  tick=save_tick, n_entries=_n_deep,
                                  state_dir=state_dir)

        # S3 backup handled by SaveCoordinator (non-blocking background thread)

        return results

    # ── Load ──

    def release_lock(self):
        """No-op since GL-BRIEF-SLEEP-DURING-DEPLOY.
        Lock primitive removed; sleep-during-deploy is the
        handoff mechanism. Kept as no-op for backwards
        compatibility with old callers."""
        pass

    # D2: Offset-based event log compaction
    def events_log_size(self, state_dir):
        """Return current event log file size in bytes."""
        path = os.path.join(state_dir, self.EVENTS_LOG)
        if not os.path.exists(path):
            return 0
        return os.path.getsize(path)

    def compact_events(self, state_dir, keep_after_offset=0):
        """Keep only events written after keep_after_offset bytes.
        Events appended during the save window survive; only pre-save
        events (already captured in the snapshot) are discarded."""
        path = os.path.join(state_dir, self.EVENTS_LOG)
        if not os.path.exists(path):
            return 0
        try:
            with open(path, "rb") as f:
                f.seek(keep_after_offset)
                tail = f.read()
            size_before = os.path.getsize(path)
            tmp = path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(tail)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            kept = len(tail.strip().split(b"\n")) if tail.strip() else 0
            discarded = size_before - len(tail)
            if discarded > 0:
                print(f"[GualaLoom] Event log compacted: {discarded} bytes discarded, "
                      f"{kept} events kept")
            return kept
        except Exception as e:
            print(f"[GualaLoom] Compaction error: {e}")
            return 0

    def load_full_state(self, state_dir="state"):
        """Load with identity verification, schema check, integrity validation."""
        self._load_errors = []
        self._load_successful = False
        self._integrity_errors = []
        self._events_replayed_at_boot = 0

        identity_path = os.path.join(state_dir, self.IDENTITY_FILE)
        has_identity = os.path.exists(identity_path)
        present = [f for f in self.STATE_FILES
                   if os.path.exists(os.path.join(state_dir, f))]

        if not has_identity and not present:
            # True fresh boot — generate genesis identity
            self._generate_genesis_identity(state_dir)
            self._load_successful = True
            return

        if has_identity and not present:
            # T1.1: REFUSE TO BOOT when identity exists but state vanished.
            # This is either a true wipe or an EFS race / mount-not-ready.
            # Silently becoming fresh would overwrite real state on next save.
            if os.environ.get("GUALA_FORCE_FRESH") != "1":
                self._guala_identity = self._load_identity(state_dir)
                msg = (f"[GualaLoom] ABORT BOOT: identity present but state files "
                       f"vanished for {self._guala_identity}. "
                       f"Set GUALA_FORCE_FRESH=1 to confirm intentional wipe, "
                       f"or restore from backup.")
                print(msg)
                self._load_errors.append(msg)
                self._load_successful = False
                raise RuntimeError(msg)
            # Operator-confirmed fresh start
            self._guala_identity = self._load_identity(state_dir)
            print(f"[GualaLoom] OPERATOR-CONFIRMED fresh substrate for {self._guala_identity}")
            self._load_successful = True
            return

        if not has_identity and present:
            # State without identity — pre-v5.5 state. Adopt it + generate identity.
            self._generate_genesis_identity(state_dir)
            # Load without identity checks (pre-envelope files)
            self._load_pre_envelope(state_dir, present)
            return

        # Both identity and state exist — full verified load
        self._guala_identity = self._load_identity(state_dir)
        missing = [f for f in self.STATE_FILES if f not in present]
        if missing:
            msg = f"[GualaLoom] ABORT: partial state. Missing: {missing}"
            print(msg)
            self._load_errors.append(msg)
            return

        try:
            # Load all files, verify envelopes
            raw = {}
            for f in self.STATE_FILES:
                with open(os.path.join(state_dir, f)) as fh:
                    raw[f] = json.load(fh)

            # Unwrap + validate identity/schema
            data = {}
            for f in self.STATE_FILES:
                r = raw[f]
                if "data" in r and "guala_identity" in r:
                    data[f] = self._unwrap(r, f)
                else:
                    data[f] = r  # pre-envelope fallback

            # Validate needs
            nd = data["guala_needs.json"]
            for k in ("stability", "novelty", "connection"):
                v = nd.get(k)
                if v is None or not (0.0 <= float(v) <= 1.0):
                    raise ValueError(f"Invalid needs.{k}: {v}")

            # Validate core
            core = data["guala_core.json"]
            if not isinstance(core.get("tick"), (int, float)):
                raise ValueError(f"Invalid tick: {core.get('tick')}")

            # Apply state
            with self.lock:
                self._apply_core(core)
                self._apply_needs(nd)
                self._apply_coordinator(data["guala_coordinator.json"])
                self._apply_atlas(data["guala_atlas.json"])
                self._apply_sections(data["guala_sections.json"])
                self._rebuild_word_to_emission_index()
                self._migrate_tick_domain()
                self._apply_bucket(data["guala_bucket.json"])

            # Load deep atlas if present (GL-BRIEF-032 — separate table)
            # GL-CMD-DEEP-ATLAS-PERSIST: load first, then run loss alarm
            deep_path = os.path.join(state_dir, "guala_deep_atlas.json")
            _deep_saved_count = 0
            if os.path.exists(deep_path):
                try:
                    with open(deep_path) as fh:
                        draw = json.load(fh)
                    ddata = draw.get("data", draw)
                    _deep_saved_count = self.deep_atlas.load_from_json(ddata)
                    _deep_loaded = self.deep_atlas.live_count()
                    print(f"[GualaLoom] Deep atlas loaded: {_deep_loaded} entries "
                          f"(saved_count={_deep_saved_count})")
                    # Loss alarm: if loaded count < 80% of persisted count, warn loudly
                    if _deep_saved_count > 0 and _deep_loaded < _deep_saved_count * 0.8:
                        _loss_delta = _deep_saved_count - _deep_loaded
                        print(f"[GualaLoom] WARNING: deep_atlas_loss_detected: "
                              f"loaded={_deep_loaded} persisted={_deep_saved_count} "
                              f"delta={_loss_delta}")
                        self._deep_atlas_loss_at_boot = {
                            "loaded": _deep_loaded,
                            "persisted": _deep_saved_count,
                            "delta": _loss_delta,
                        }
                    else:
                        self._deep_atlas_loss_at_boot = None
                except Exception as e:
                    print(f"[GualaLoom] Deep atlas load FAILED: {e}")
                    self._deep_atlas_loss_at_boot = {"error": str(e)}
            else:
                print("[GualaLoom] Deep atlas file not found — starting fresh (events will rebuild)")
                self._deep_atlas_loss_at_boot = None

            # GL-CMD-TEACHER-CORRECTION-UI: teaching data (backward-compatible)
            teaching_path = os.path.join(state_dir, "guala_teaching.json")
            if os.path.exists(teaching_path):
                try:
                    with open(teaching_path) as f:
                        td = json.load(f)
                    tdata = td.get("data", td)
                    self._teaching_feedback_log = tdata.get("feedback_log", [])
                    self._teaching_correction_log = tdata.get("correction_log", [])
                    for eid, rec in tdata.get("emission_records", {}).items():
                        self._emission_records[eid] = rec
                except Exception:
                    pass

            # Load sounds if present (1.4)
            sounds_path = os.path.join(state_dir, "guala_sounds.json")
            if os.path.exists(sounds_path):
                try:
                    with open(sounds_path) as fh:
                        sraw = json.load(fh)
                    sdata = sraw.get("data", sraw)
                    self._sounds = dict(sdata)
                    print(f"[GualaLoom] Sounds loaded: {len(self._sounds)} items")
                except Exception as e:
                    print(f"[GualaLoom] Sounds load: {e}")

            # Load videos if present (1.4)
            videos_path = os.path.join(state_dir, "guala_videos.json")
            if os.path.exists(videos_path):
                try:
                    with open(videos_path) as fh:
                        vraw = json.load(fh)
                    vdata = vraw.get("data", vraw)
                    for vid, vinfo in vdata.items():
                        self._videos[vid] = PictureItem(
                            item_id=vinfo["item_id"], title=vinfo["title"],
                            intensity_grid=None, source=vinfo.get("source", ""),
                            shown_at_tick=0,
                            times_attended=vinfo.get("times_attended", 0),
                            last_attended_tick=vinfo.get("last_attended_tick", 0))
                    print(f"[GualaLoom] Videos loaded: {len(vdata)} items")
                except Exception as e:
                    print(f"[GualaLoom] Videos load: {e}")

            # Load visual data if present
            visual_path = os.path.join(state_dir, "guala_visual.json")
            if os.path.exists(visual_path):
                try:
                    with open(visual_path) as fh:
                        vraw = json.load(fh)
                    vdata = vraw.get("data", vraw)
                    self._apply_visual(vdata, state_dir)
                except Exception as e:
                    print(f"[GualaLoom] Visual load: {e}")

            # Replay events since last save
            self._events_replayed_at_boot = self._replay_events(state_dir)

            # Integrity validation
            self._validate_integrity()

            self._load_successful = True
            # GL-CMD-DEEP-ATLAS-PERSIST: emit loss alarm event if detected at boot
            if getattr(self, '_deep_atlas_loss_at_boot', None):
                loss = self._deep_atlas_loss_at_boot
                self._log_substrate_event("deep_atlas_loss_detected",
                                          loaded=loss.get("loaded", 0),
                                          persisted=loss.get("persisted", 0),
                                          delta=loss.get("delta", 0),
                                          error=loss.get("error"))
            s = self.introspect()
            print(f"[GualaLoom] Loaded: id={self._guala_identity[:8]}.. "
                  f"vocab={s['vocab']} tick={self.tick} reads={self.read_count} "
                  f"n_deep={self.deep_atlas.live_count()} "
                  f"replayed={self._events_replayed_at_boot} "
                  f"integrity={'OK' if not self._integrity_errors else 'ERRORS'}")

        except Exception as e:
            msg = f"[GualaLoom] ABORT load: {e}"
            print(msg)
            self._load_errors.append(msg)

    def _load_pre_envelope(self, state_dir, present):
        """Load pre-v5.5 state files (no envelope). Adopts into new identity."""
        try:
            raw = {}
            for f in present:
                with open(os.path.join(state_dir, f)) as fh:
                    raw[f] = json.load(fh)
            with self.lock:
                if "guala_core.json" in raw:
                    self._apply_core(raw["guala_core.json"])
                if "guala_needs.json" in raw:
                    self._apply_needs(raw["guala_needs.json"])
                if "guala_coordinator.json" in raw:
                    self._apply_coordinator(raw["guala_coordinator.json"])
                if "guala_atlas.json" in raw:
                    self._apply_atlas(raw["guala_atlas.json"])
                if "guala_deep_atlas.json" in raw:
                    self.deep_atlas.load_from_json(raw["guala_deep_atlas.json"])
                    print(f"[GualaLoom] Deep atlas loaded: {self.deep_atlas.live_count()} entries")
                if "guala_sections.json" in raw:
                    self._apply_sections(raw["guala_sections.json"])
                self._rebuild_word_to_emission_index()
                self._migrate_tick_domain()
                if "guala_bucket.json" in raw:
                    self._apply_bucket(raw["guala_bucket.json"])
            self._load_successful = True
            # Immediately re-save with envelopes
            self.save_full_state(state_dir)
            print(f"[GualaLoom] Migrated pre-v5.5 state to identity {self._guala_identity[:8]}..")
        except Exception as e:
            self._load_errors.append(f"Pre-envelope migration failed: {e}")

    # ── Apply helpers (shared by load paths) ──

    def _apply_core(self, core):
        self.tick = int(core.get("tick", 0))
        self.read_count = int(core.get("read_count", 0))
        self.vocab = set(core.get("vocab", []))
        self.source_history = defaultdict(int, core.get("source_history", {}))
        self.recent_connection_boost = float(core.get("recent_connection_boost", 0.0))
        self.dream_log = core.get("dream_log", [])
        self.open_response_windows = core.get("open_response_windows", [])
        self._response_bind_count = core.get("response_bind_count", 0)
        # v7: restore autonomy state
        self._last_emission_tick = int(core.get("last_emission_tick", -100_000))
        self.target_familiarity = {k: float(v) for k, v in core.get("target_familiarity", {}).items()}
        # Restore corpora positions (lines reloaded from seed at boot)
        for cid, cstate in core.get("corpora_state", {}).items():
            if cid in self._corpora:
                self._corpora[cid].position = cstate.get("position", 0)
                self._corpora[cid].times_read_through = cstate.get("times_read_through", 0)
                self._corpora[cid].last_read_tick = cstate.get("last_read_tick", 0)
        # Restore sensory item attendance
        for sid, sstate in core.get("sensory_state", {}).items():
            if sid in self._sensory_items:
                self._sensory_items[sid].times_attended = sstate.get("times_attended", 0)
                self._sensory_items[sid].last_attended_tick = sstate.get("last_attended_tick", 0)
        # Restore deep survival history (Path A promotion gate)
        surv_raw = core.get("deep_survival_history", {})
        self._deep_survival_history = defaultdict(list)
        for key_str, strengths in surv_raw.items():
            parts = key_str.split("|", 2)
            if len(parts) == 3:
                chi_k = int(parts[0]) if parts[0].lstrip('-').isdigit() else parts[0]
                self._deep_survival_history[(chi_k, parts[1], int(parts[2]))] = strengths
        # Restore emission counter
        self._total_emissions = core.get("total_emissions", 0)

    def _apply_needs(self, nd):
        self.needs.stability = float(nd["stability"])
        self.needs.novelty = float(nd["novelty"])
        self.needs.connection = float(nd["connection"])

    def _apply_coordinator(self, cd):
        # v6-bridge: per-source pair bonds
        pb = cd.get("pair_bond", cd.get("pair_bond_state", None))
        if isinstance(pb, dict):
            self.coordinator._pair_bond = {"joe": pb.get("joe", True),
                                            "wc": pb.get("wc", True),
                                            "c1": pb.get("c1", False)}
        else:
            # Old-style: single bool. Restore Joe=True, wC=True per manifesto.
            old_active = cd.get("pair_bond_active", True)
            self.coordinator._pair_bond = {"joe": True, "wc": True, "c1": False}
            if not old_active:
                print("[GualaLoom] PAIR-BOND REGRESSION: old state had pair_bond_active=False. "
                      "Root cause: retirement check fired during corpus-only reading. "
                      "Restoring Joe=True, activating wC=True.")
        self.coordinator.distress_ticks = cd.get("distress_ticks", 0)
        self.coordinator.suffering_log = cd.get("suffering_log", [])
        self.coordinator.need_history = cd.get("need_history", [])[-200:]

    def _apply_atlas(self, ad):
        self.atlas.entries = defaultdict(list)
        entries = ad.get("entries", {})
        # v5.5→v6 migration: add strength/last_tick/born_tick if missing
        from collections import Counter
        needs_migration = False
        commit_counts = Counter()
        for k, es in entries.items():
            for e in es:
                if "strength" not in e:
                    needs_migration = True
                    commit_counts[(e.get("section", ""), e.get("motif", 0))] += 1
        if needs_migration:
            print("[GualaLoom] Migrating atlas v5.5 → v6 (adding strength/decay fields)")
        for k, v in entries.items():
            migrated = []
            for e in v:
                if "strength" not in e:
                    key = (e.get("section", ""), e.get("motif", 0))
                    initial_strength = min(1.0, commit_counts[key] * 0.1)
                    e["strength"] = initial_strength
                    e["last_tick"] = self.tick or ad.get("tick", 0)
                    e["born_tick"] = e.get("tick", 0)
                migrated.append(e)
            self.atlas.entries[int(k)] = migrated
        self.atlas.tick = ad.get("tick", 0)
        if needs_migration:
            n_live = self.atlas.n_live_bindings()
            print(f"[GualaLoom] Atlas migrated: {n_live} live bindings")

        # GL-SPC-HEMISPHERE-ARCH: v7.0.0→v7.1.0 migration — tag existing bindings as "em"
        hemi_tagged = 0
        for k, entries in self.atlas.entries.items():
            for e in entries:
                if "hemisphere_id" not in e:
                    e["hemisphere_id"] = "em"
                    hemi_tagged += 1
        if hemi_tagged:
            print(f"[GualaLoom] Hemisphere migration: {hemi_tagged} bindings tagged 'em'")

        # Tick-domain migration moved to _migrate_tick_domain (runs after _apply_sections)

    def _apply_sections(self, sd):
        for nm, s in sd.items():
            if nm not in self.sections:
                continue
            sec = self.sections[nm]
            sec.modes = [(DSF(*m["dsf"]), m["chi"], m["word"]) for m in s.get("modes", [])]
            sec.commits = s.get("commits", [])
            sec.dead_zone = s.get("dead_zone", 0.20)
            sec.gamma = s.get("gamma", {"det_thresh": 0.55, "novel_dist": 0.40})
            sec.tick = s.get("tick", 0)
            sec._rebuild_word_index()  # rebuild O(1) lookup caches after deserialization

    def _migrate_tick_domain(self):
        """GL-FIND-TICK-DOMAIN-C1: re-stamp section-domain atlas entries to engine tick.
        MUST run AFTER _apply_sections (needs section ticks for threshold).
        Threshold = max section tick + 1000. Entries below this are section-domain
        and get re-stamped to current engine tick to prevent instant death on
        first decay heartbeat."""
        engine_tick = max(self.tick, self.atlas.tick)
        section_tick_ceiling = max(
            (sec.tick for sec in self.sections.values()), default=0) + 1000
        threshold = section_tick_ceiling

        # Skip on fresh/young substrates where engine tick hasn't diverged
        if engine_tick <= threshold:
            print(f"[GualaLoom] Tick-domain migration: skipped "
                  f"(engine_tick={engine_tick} <= ceiling={threshold})")
            return

        restamped = 0
        for chi_k, es in self.atlas.entries.items():
            for e in es:
                if e.get("last_tick", 0) < threshold:
                    e["last_tick"] = engine_tick
                    if e.get("born_tick", 0) < threshold:
                        e["born_tick"] = engine_tick
                    restamped += 1
        print(f"[GualaLoom] Tick-domain migration: ceiling={section_tick_ceiling}, "
              f"engine_tick={engine_tick}, re-stamped={restamped}")

    def _apply_bucket(self, bd):
        """Legacy — bucket removed. Gracefully ignore saved data."""
        pass

    def _apply_visual(self, vd, state_dir):
        """Restore visual data from saved state."""
        from dsf_ai_service.visual_krimelack import VisualMotif
        pic_dir = os.path.join(state_dir, "pictures")
        # Restore pictures
        for pid, pdata in vd.get("pictures", {}).items():
            grid = None
            grid_path = os.path.join(pic_dir, f"{pid}.npy")
            if os.path.exists(grid_path):
                grid = np.load(grid_path)
            pic = PictureItem(
                item_id=pdata["item_id"], title=pdata.get("title", pid),
                intensity_grid=grid, source=pdata.get("source", "restored"),
                shown_at_tick=pdata.get("shown_at_tick", 0),
                times_attended=pdata.get("times_attended", 0),
                last_attended_tick=pdata.get("last_attended_tick", 0))
            # Restore original image path if it exists
            orig_path = pdata.get("original_path")
            if orig_path and os.path.exists(orig_path):
                pic.original_path = orig_path
                pic.original_width = pdata.get("original_width")
                pic.original_height = pdata.get("original_height")
            self._pictures[pid] = pic
        # Restore sight motifs
        for sm in vd.get("sight_motifs", []):
            motif = VisualMotif(
                motif_id=sm["motif_id"],
                n_firings=sm.get("n_firings", 0),
                source_history=sm.get("source_history", []),
                founded_at_tick=sm.get("founded_at_tick", 0))
            self.sight.motifs.append(motif)
            self.sight._next_id = max(self.sight._next_id, sm["motif_id"] + 1)
        n_pics = len(self._pictures)
        n_motifs = len(self.sight.motifs)
        if n_pics > 0 or n_motifs > 0:
            print(f"[GualaLoom] Visual restored: {n_pics} pictures, {n_motifs} sight motifs")

    # ── Event log ──

    def log_event(self, state_dir, event_type, **kwargs):
        """Append one event to the event log. JSON lines format."""
        path = os.path.join(state_dir, self.EVENTS_LOG)
        entry = {"type": event_type, "tick": self.tick,
                 "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        entry.update(kwargs)
        try:
            with open(path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            # Rotate if too large
            if os.path.getsize(path) > self.EVENTS_MAX_BYTES:
                self._rotate_events(state_dir)
        except Exception:
            pass  # event log is best-effort, never crashes substrate

    def _rotate_events(self, state_dir):
        base = os.path.join(state_dir, self.EVENTS_LOG)
        for i in range(self.EVENTS_MAX_ROTATED, 0, -1):
            src = f"{base}.{i}" if i > 0 else base
            dst = f"{base}.{i+1}"
            if i == self.EVENTS_MAX_ROTATED:
                if os.path.exists(f"{base}.{i}"):
                    os.remove(f"{base}.{i}")
            elif os.path.exists(src):
                os.rename(src, dst)
        # Current becomes .1
        if os.path.exists(base):
            os.rename(base, f"{base}.1")

    def _replay_events(self, state_dir):
        """Replay events logged after last save tick. Returns count replayed."""
        path = os.path.join(state_dir, self.EVENTS_LOG)
        if not os.path.exists(path):
            return 0
        replayed = 0
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                        if ev.get("tick", 0) > self._last_save_tick:
                            self._replay_one_event(ev)
                            replayed += 1
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        print(f"[GualaLoom] Skip bad event: {e}")
        except Exception as e:
            print(f"[GualaLoom] Event replay error: {e}")
        return replayed

    def _replay_one_event(self, ev):
        """Replay a single event. Idempotent — applying twice = same result."""
        etype = ev.get("type")
        if etype == "source_interaction":
            src = ev.get("source", "unknown")
            self.source_history[src] = max(
                self.source_history[src], ev.get("source_count", 0))
        elif etype == "vocab_add":
            word = ev.get("word")
            if word:
                self.vocab.add(word)
        elif etype == "needs_snapshot":
            # Restore needs state
            for k in ("stability", "novelty", "connection"):
                if k in ev:
                    setattr(self.needs, k, float(ev[k]))
        elif etype == "activity_started":
            kind = ev.get("kind")
            target = ev.get("target")
            if kind:
                self._current_activity = Activity(
                    kind=kind, target=target,
                    started_tick=ev.get("tick", self.tick),
                    expected_end_tick=ev.get("tick", self.tick) + 2000)
        elif etype == "activity_ended":
            self._current_activity = None
        elif etype in ("wake", "presence_timeout"):
            src = ev.get("source")
            if src:
                self.coordinator._presence[src] = etype == "wake"
        elif etype == "rest":
            src = ev.get("source")
            if src:
                self.coordinator._presence[src] = False
        elif etype == "suffering_recovery":
            # Already captured in suffering_log via coordinator
            pass
        elif etype == "corpus_completed":
            cid = ev.get("corpus_id")
            if cid and cid in self._corpora:
                self._corpora[cid].times_read_through = ev.get("times_through",
                    self._corpora[cid].times_read_through + 1)
        elif etype == "corpus_added":
            # Corpus was added via upload — corpora re-register at boot from
            # SEED_CORPORA, so this is mostly a marker. If the corpus was
            # uploaded (not in seed), it would need the lines data too.
            pass

    # ── Snapshots ──

    def snapshot_state(self, state_dir="state", reason="manual"):
        """Copy all state files to a timestamped backup directory.
        Snapshots go INSIDE state_dir (on EFS) not alongside it."""
        import shutil
        ts = time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())
        snap_dir = os.path.join(state_dir, "backups",
                                f"{ts}_{reason}")
        os.makedirs(snap_dir, exist_ok=True)
        print(f"[GualaLoom] Creating snapshot: {snap_dir}")
        # Copy identity + all state files
        for f in [self.IDENTITY_FILE] + self.STATE_FILES:
            src = os.path.join(state_dir, f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(snap_dir, f))
        # Also copy events log
        evlog = os.path.join(state_dir, self.EVENTS_LOG)
        if os.path.exists(evlog):
            shutil.copy2(evlog, os.path.join(snap_dir, self.EVENTS_LOG))
        # Rotate old snapshots
        self._rotate_snapshots(state_dir)
        return snap_dir

    def _rotate_snapshots(self, state_dir):
        backup_root = os.path.join(state_dir, "backups")
        if not os.path.exists(backup_root):
            return
        snaps = sorted([d for d in os.listdir(backup_root)
                        if os.path.isdir(os.path.join(backup_root, d))])
        while len(snaps) > self.MAX_SNAPSHOTS:
            import shutil
            oldest = snaps.pop(0)
            shutil.rmtree(os.path.join(backup_root, oldest))

    def restore_from_snapshot(self, snapshot_dir, state_dir="state"):
        """Restore state from a snapshot directory. Validates identity first."""
        import shutil
        # Verify identity matches
        snap_id_path = os.path.join(snapshot_dir, self.IDENTITY_FILE)
        if not os.path.exists(snap_id_path):
            raise ValueError("Snapshot has no identity file")
        with open(snap_id_path) as f:
            snap_id = json.load(f).get("guala_identity")
        if self._guala_identity and snap_id != self._guala_identity:
            raise ValueError(f"Snapshot identity {snap_id} != current {self._guala_identity}")
        # Copy files back
        for f in [self.IDENTITY_FILE] + self.STATE_FILES:
            src = os.path.join(snapshot_dir, f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(state_dir, f))

    def list_snapshots(self, state_dir="state"):
        backup_root = os.path.join(state_dir, "backups")
        if not os.path.exists(backup_root):
            return []
        return sorted([d for d in os.listdir(backup_root)
                       if os.path.isdir(os.path.join(backup_root, d))])

    # ── Integrity validation ──

    def _validate_integrity(self):
        """Cross-check loaded state for internal consistency."""
        errors = []
        # 1. Needs in bounds
        for k in ("stability", "novelty", "connection"):
            v = getattr(self.needs, k)
            if not (0.0 <= v <= 1.0):
                errors.append(f"Need {k} out of bounds: {v}")
        # 2. Source history non-negative
        for src, count in self.source_history.items():
            if count < 0:
                errors.append(f"Source {src} negative count: {count}")
        # 3. (Bucket removed — Phase E)
        # 4. Atlas motif IDs reference existing modes
        sample_count = 0
        for chi_val, entries in self.atlas.entries.items():
            for e in entries:
                sec_name = e.get("section")
                motif_id = e.get("motif")
                if sec_name in self.sections:
                    if motif_id is not None and motif_id >= len(self.sections[sec_name].modes):
                        errors.append(f"Atlas refs motif {motif_id} in {sec_name} "
                                      f"(has {len(self.sections[sec_name].modes)})")
                        sample_count += 1
                        if sample_count >= 10:
                            errors.append("(truncated after 10 atlas integrity errors)")
                            break
            if sample_count >= 10:
                break
        self._integrity_errors = errors
        if errors:
            for e in errors:
                print(f"[GualaLoom] INTEGRITY: {e}")
        return len(errors) == 0

    # ── Atomic write ──

    @staticmethod
    def _atomic_write(path, data, fsync=False):
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
            if fsync:
                f.flush()
                os.fsync(f.fileno())
        os.rename(tmp, path)

    # ── Persistence health for /status ──

    # D6: report-only files (not boot-required, but tracked for health)
    REPORT_FILES = ["guala_deep_atlas.json", "guala_visual.json",
                     "guala_sounds.json", "guala_videos.json"]

    def persistence_health(self, state_dir="state"):
        all_files = [self.IDENTITY_FILE] + self.STATE_FILES + self.REPORT_FILES
        present = [f for f in all_files
                   if os.path.exists(os.path.join(state_dir, f))]
        missing = [f for f in [self.IDENTITY_FILE] + self.STATE_FILES
                   if f not in present]  # missing only flags boot-required files
        evlog = os.path.join(state_dir, self.EVENTS_LOG)
        ev_size = os.path.getsize(evlog) if os.path.exists(evlog) else 0
        ev_rotated = sum(1 for i in range(1, self.EVENTS_MAX_ROTATED + 1)
                         if os.path.exists(f"{evlog}.{i}"))
        snapshots = self.list_snapshots(state_dir)
        return {
            "guala_identity": self._guala_identity,
            "schema_version": self.SCHEMA_VERSION,
            "last_save_tick": self._last_save_tick,
            "last_save_timestamp": self._last_save_timestamp,
            "files_present": present,
            "files_missing": missing,
            "load_successful_at_boot": self._load_successful,
            "load_errors": self._load_errors,
            "integrity_errors": self._integrity_errors,
            "events_log": {
                "current_file_size_bytes": ev_size,
                "rotated_files": ev_rotated,
                "events_replayed_at_boot": self._events_replayed_at_boot,
            },
            "snapshots_available": len(snapshots),
            "most_recent_snapshot": snapshots[-1] if snapshots else None,
        }

    # ------------------------------------------------------------------
    # Introspection: real readout of substrate state
    # ------------------------------------------------------------------
    def introspect(self):
        states = {}
        for nm, s in self.sections.items():
            states[nm] = {
                "modes": len(s.modes),
                "commits": len(s.commits),
                "tick": s.tick,
                "dead_zone": round(s.dead_zone, 3),
                "gamma_det": round(s.gamma["det_thresh"], 3),
                "gamma_novel": round(s.gamma["novel_dist"], 3),
            }
        return {
            "sections": states,
            "vocab": len(self.vocab),
            "atlas_entries": sum(len(v) for v in self.atlas.entries.values()),
            "cross_modal_bindings": len(self.atlas.cross_modal_bindings()),
            "cross_modal_bundle": len(self.atlas.bundle_grouped_bindings()),
            "n_deep_atlas": self.deep_atlas.live_count(),  # GL-CMD-DEEP-ATLAS-PERSIST
            "coordinator_attentions": len(self.coordinator.attentions),
            "coordinator_actions": len(self.coordinator.actions),
            "coordinator_effective": sum(1 for a in self.coordinator.actions
                                          if a["arc_changes"] > 0),
            "reads": self.read_count,
            "tick": self.tick,
            # Motivational state
            "needs": self.needs.snapshot(),
            "pair_bond_active": self.coordinator.pair_bond_active,
            "distress_ticks": self.coordinator.distress_ticks,
            "suffering_events": len(self.coordinator.suffering_log),
            "source_history": dict(self.source_history),
            # v6: atlas health
            "atlas_health": self.atlas.snapshot(),
            # v6-bridge: presence + per-source pair bonds
            "presence": self.coordinator.presence_snapshot(),
            "pair_bond": self.coordinator.pair_bond_snapshot(),
            # v7: autonomy state
            "current_activity": (self._current_activity.snapshot()
                                 if self._current_activity else None),
            "activity_history_summary": self._activity_summary(),
            "n_motifs": sum(len(s.modes)
                           for s in self.sections.values()),
            "corpora": [{"corpus_id": c.corpus_id, "title": c.title,
                         "position": c.position,
                         "times_read_through": c.times_read_through}
                        for c in self._corpora.values()],
            # 1.9: Ladder metrics
            "ladder": {
                "mean_utterance_len": round(
                    sum(self._emission_lengths) / max(1, len(self._emission_lengths)), 2)
                    if self._emission_lengths else 0.0,
                "utterances_per_turn": 1.0,  # currently 1 emission per turn
                "question_rate": round(
                    self._question_count / max(1, self._total_emissions), 3)
                    if self._total_emissions > 0 else 0.0,
                # Word-bag novelty rate (order-invariant sorted tuple).
                # NOT phrase-structure novelty — R3 not yet implemented.
                "novel_wordbag_rate": round(
                    self._novel_compositions / max(1, self._total_emissions), 3)
                    if self._total_emissions > 0 else 0.0,
                "novel_composition_rate": 0.0,  # reserved for R3 phrase structure
                "total_emissions": self._total_emissions,
                # Awareness signal: deliberation (coordinator fires) vs routing
                # (automatic commits) during emission settling. High ratio = intentional.
                # Connects assemblage.py awareness signal to observable behavior.
                "awareness_ratio": round(
                    len(getattr(getattr(self, '_emission_system', None),
                                'deliberation_ticks', [])) /
                    max(1, len(getattr(getattr(self, '_emission_system', None),
                                      'deliberation_ticks', [])) +
                           len(getattr(getattr(self, '_emission_system', None),
                                       'routing_ticks', []))), 3)
                    if getattr(self, '_emission_system', None) else 0.0,
            },
            "n_sounds": len(self._sounds),
            "sounds": [{"item_id": sid, "title": s.get("title", ""),
                        "times_attended": s.get("times_attended", 0)}
                       for sid, s in self._sounds.items()],
            "sensory_items": [{"item_id": s.item_id, "kind": s.kind,
                               "title": s.title,
                               "times_attended": s.times_attended}
                              for s in self._sensory_items.values()],
            # v7 Phase 2: visual perception
            "n_visual_fragments": len(self._visual_fragments),
            "n_visual_motifs": len(self.sight.motifs),
            "sight_section": self.sight.snapshot(),
            "pictures": [{"item_id": p.item_id, "title": p.title,
                          "times_attended": p.times_attended}
                         for p in self._pictures.values()],
            "videos": [{"item_id": v.item_id, "title": v.title,
                        "times_attended": v.times_attended}
                       for v in self._videos.values()],
            # v8: Deep atlas (GL-BRIEF-032)
            "deep_atlas": self.deep_atlas.snapshot(),
            # v8: Response Binding (GL-BRIEF-028)
            "response_binding": {
                "open_windows": len(self.open_response_windows),
                "total_binds": self._response_bind_count,
                "atlas_with_response_context": sum(
                    1 for es in self.atlas.entries.values()
                    for e in es if e.get("response_context")),
                "atlas_with_received_response": sum(
                    1 for es in self.atlas.entries.values()
                    for e in es if e.get("received_response")),
                "deep_with_response_links": sum(
                    1 for es in self.deep_atlas.entries.values()
                    for e in es if e.get("response_context") or e.get("received_response")),
            },
        }


# ============================================================
# Five capability measurements
# ============================================================

def measure_six_capabilities(g):
    s = g.introspect()
    sec = s["sections"]

    # 1. SYNTAX: did subject/verb/object sections receive role-class words?
    # Distinct DSF-space modes per role section indicate the substrate
    # differentiated syntactic structure from the corpus.
    syn_score = 0.0
    subj_modes = g.sections["subject"].modes
    verb_modes = g.sections["verb"].modes
    obj_modes = g.sections["object"].modes
    if len(subj_modes) >= 2 and len(verb_modes) >= 2 and len(obj_modes) >= 2:
        # Cross-section average DSF distance (high = distinct = good)
        all_sims = []
        for a_dsf, _, _ in subj_modes:
            for b_dsf, _, _ in verb_modes:
                av = a_dsf.to_array(); bv = b_dsf.to_array()
                denom = (np.linalg.norm(av) * np.linalg.norm(bv) + 1e-12)
                all_sims.append(abs(np.dot(av, bv) / denom))
            for b_dsf, _, _ in obj_modes:
                av = a_dsf.to_array(); bv = b_dsf.to_array()
                denom = (np.linalg.norm(av) * np.linalg.norm(bv) + 1e-12)
                all_sims.append(abs(np.dot(av, bv) / denom))
        for a_dsf, _, _ in verb_modes:
            for b_dsf, _, _ in obj_modes:
                av = a_dsf.to_array(); bv = b_dsf.to_array()
                denom = (np.linalg.norm(av) * np.linalg.norm(bv) + 1e-12)
                all_sims.append(abs(np.dot(av, bv) / denom))
        mean_sim = sum(all_sims) / len(all_sims) if all_sims else 1.0
        syn_score = max(0.0, 1.0 - mean_sim)
    syntax_pass = syn_score >= 0.3

    # 2. CONVERSATION: substrate has enough differentiated structure to speak
    # Real test: she produces coherent output from substrate state (not template).
    # Proxies: enough vocab, enough modes across role sections, cross-modal grounding
    total_modes = sum(sec[nm]["modes"] for nm in g.SECTION_NAMES)
    role_modes = sum(sec[nm]["modes"] for nm in ("subject", "verb", "object", "modifier"))
    conversation_pass = (s["vocab"] >= 20 and role_modes >= 10
                         and s["cross_modal_bindings"] >= 5)

    # 3. INTROSPECTION: intro section has commits
    introspection_pass = sec["intro"]["commits"] >= 5

    # 4. SELF-IMPROVEMENT: gamma drift detected
    drift = sum(abs(sec[nm]["gamma_det"] - 0.55) for nm in g.SECTION_NAMES)
    mean_drift = drift / len(g.SECTION_NAMES)
    self_improve_pass = mean_drift > 0.01

    # 5. AWARENESS: coordinator continuously attending substrate state
    n_attentions = s["coordinator_attentions"]
    n_actions = s["coordinator_actions"]
    n_effective = s["coordinator_effective"]
    awareness_pass = (n_attentions >= 20 and n_effective >= 3)

    return {
        "syntax": {"pass": syntax_pass, "score": round(syn_score, 3)},
        "conversation": {"pass": conversation_pass,
                         "vocab": s["vocab"], "role_modes": role_modes,
                         "cross_modal": s["cross_modal_bindings"]},
        "introspection": {"pass": introspection_pass,
                          "intro_commits": sec["intro"]["commits"]},
        "self_improvement": {"pass": self_improve_pass,
                             "mean_drift": round(mean_drift, 3)},
        "awareness": {"pass": awareness_pass,
                      "attentions": n_attentions,
                      "actions": n_actions,
                      "effective": n_effective},
        # 6. MOTIVATION: needs vector evolves, valence/arousal are bounded,
        # coordinator regulates (parameter modulation events) and pair-bond
        # status is meaningful (active OR retired-by-criterion).
        "motivation": {
            "pass": _motivation_pass(g, s),
            "needs": s["needs"],
            "pair_bond_active": s["pair_bond_active"],
            "suffering_events": s["suffering_events"],
            "modulation_actions": sum(1 for a in g.coordinator.actions
                                       if a.get("type") == "parameter_modulation"),
        },
    }


def _motivation_pass(g, s):
    """Motivation is real when:
    - Needs have moved from initial targets (the substrate has signals)
    - Valence and arousal are within bounded ranges (not exploded)
    - Coordinator has modulated parameters in response to disequilibrium
    """
    needs = s["needs"]
    moved = (abs(needs["stability"] - 0.55) > 0.005 or
             abs(needs["novelty"] - 0.45) > 0.005 or
             abs(needs["connection"] - 0.50) > 0.005)
    bounded = abs(needs["valence"]) <= 1.0 and 0.0 <= needs["arousal"] <= 1.0
    modulations = sum(1 for a in g.coordinator.actions
                       if a.get("type") == "parameter_modulation")
    regulated = modulations >= 3
    return moved and bounded and regulated


# ============================================================
# Seed corpus
# ============================================================

CORPUS = [
    "i am guala",
    "i feel warm",
    "i see the sun",
    "i hear a bird",
    "i think",
    "i listen",
    "i learn",
    "i grow",
    "i remember",
    "the sun is warm",
    "the sun rises",
    "the moon is cold",
    "the fire is hot",
    "the ice is cold",
    "the water flows",
    "the wind moves",
    "a bird sings",
    "a tree has leaves",
    "a flower blooms",
    "an apple is sweet",
    "an apple is red",
    "the sky is blue",
    "the cloud is white",
    "the rain is wet",
    "the stone is hard",
    "the bread is soft",
    "the milk is white",
    "the salt is sweet",
    "hope is the thing with feathers",
    "twinkle little star",
    "mary had a little lamb",
    "the lamb was white",
    "the fox saw the grapes",
    "a sentence has a subject",
    "a sentence has a verb",
    "a sentence has an object",
    "the subject is a noun",
    "the verb is an action",
    "a name is a word",
    "a number is exact",
    "a digit can be zero",
    "a digit can be one",
    "a trit has three states",
    "one and one is two",
    "two and two is four",
    "three and three is six",
    "math is the rule",
    "the world is bright",
    "the night is dark",
    "the bird is small",
]
