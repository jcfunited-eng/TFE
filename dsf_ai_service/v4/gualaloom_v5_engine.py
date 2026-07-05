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
import calendar
import queue as _queue
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


def _grandurun_amplitude_multichi(chi_candidate, strength, input_chis):
    """GL-CMD-COMPOSER-MULTIANCHOR-43 §2.1: multi-anchor amplitude.
    Sums amplitude over each input chi, normalizes by count.
    Same phase math as _grandurun_amplitude; chi-geometric meaning of all
    input words contributes rather than only the first."""
    if not input_chis:
        return complex(0.0, 0.0)
    total = sum(_grandurun_amplitude(chi_candidate, strength, tc) for tc in input_chis)
    return total / len(input_chis)


def _grandurun_select_multichi(candidates, input_chis):
    """GL-CMD-EMISSION-PERF-45 §2.2: greedy coherent selection with vectorized
    amplitude pre-compute. Decisions (running sum, gain threshold) remain sequential.
    candidates: list of (chi_address, strength, word)
    Returns: list of selected words in chosen order."""
    if not candidates:
        return [], 0.0
    pool = sorted(candidates, key=lambda c: -c[1])
    anchors = _np.array(input_chis if input_chis else [0], dtype=_np.float64)
    # Pre-compute all amplitudes in one vectorized op
    pool_chis = _np.array([c[0] for c in pool], dtype=_np.float64)
    pool_str  = _np.array([c[1] for c in pool], dtype=_np.float64)
    phi = _np.pi * _np.abs(pool_chis[:, None] - anchors[None, :]) / CHI_CORR_LENGTH
    amp_matrix = _np.sqrt(_np.maximum(pool_str[:, None], 0.0)) * _np.exp(1j * phi)
    amps_vec = amp_matrix.mean(axis=1)  # complex amplitude per candidate

    chosen_amps = []
    chosen_words = []
    last_coh = 0.0
    for i, (chi_addr, strength, word) in enumerate(pool):
        amp = complex(amps_vec[i])
        new_sum = sum(chosen_amps, 0j) + amp
        new_coh = abs(new_sum) ** 2
        if new_coh - last_coh > MIN_GAIN_THRESHOLD:
            chosen_words.append(word)
            chosen_amps.append(amp)
            last_coh = new_coh
        if len(chosen_words) >= MAX_COMPOSITION_LEN:
            break
    return chosen_words, last_coh


def _grandurun_select(candidates, target_chi):
    """GL-CMD-EMISSION-PERF-45 §2.2: greedy coherent selection with vectorized
    amplitude pre-compute (single anchor). Greedy loop stays sequential.
    candidates: list of (chi_address, strength, word)
    Returns: list of selected words in chosen order."""
    if not candidates:
        return [], 0.0
    pool = sorted(candidates, key=lambda c: -c[1])
    pool_chis = _np.array([c[0] for c in pool], dtype=_np.float64)
    pool_str  = _np.array([c[1] for c in pool], dtype=_np.float64)
    phi = _np.pi * _np.abs(pool_chis - float(target_chi)) / CHI_CORR_LENGTH
    amps_vec = _np.sqrt(_np.maximum(pool_str, 0.0)) * _np.exp(1j * phi)

    chosen_amps = []
    chosen_words = []
    last_coh = 0.0
    for i, (chi_addr, strength, word) in enumerate(pool):
        amp = complex(amps_vec[i])
        new_sum = sum(chosen_amps, 0j) + amp
        new_coh = abs(new_sum) ** 2
        if new_coh - last_coh > MIN_GAIN_THRESHOLD:
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

    GL-CMD-EMISSION-PERF-45 §2.1: two-pass numpy vectorized amplitude computation.
    Pass 1: collect candidate metadata (chi, strength, word) without amplitude.
    Pass 2: single numpy matrix op for all amplitudes — O(n_cands * n_anchors)
    in one vectorized call instead of ~25,200 scalar cmath.exp() calls.
    Result: Stage 1 time <5ms vs 551ms scalar loop.
    """
    _input_chis_arr = input_chis if input_chis else [0]

    # Pass 1: collect pending candidates (no amplitude computation yet)
    pending = []  # (de_chi, strength, sec_name, mid, word_label, metadata_dict)
    seen = set()

    for de, co, clarity in deep_candidates:
        de_chi = de.get("chi", 0)
        meta = {
            "source": de.get("source", "corpus"),
            "arousal": de.get("arousal", 0.5),
            "valence": de.get("valence", 0.0),
            "surprise": de.get("surprise", 0.0),
            "polarity": de.get("polarity", 1.0),
            "sensory_refs": de.get("sensory_refs", []),
        }
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
                if not word_label or word_label.lower() in input_words_set:
                    continue
                key = (sec_name, mid)
                if key in seen:
                    continue
                seen.add(key)
                pending.append((de_chi, float(strength), sec_name, mid, word_label, meta))

    if not pending:
        return []

    # Pass 2: vectorized amplitude — one numpy matrix op for all candidates × all anchors
    # phi[i, j] = π * |chi_i - input_chi_j| / CHI_CORR_LENGTH
    # amp[i, j] = sqrt(strength_i) * exp(1j * phi[i, j])
    # coh_mag[i] = |mean(amp[i, :], axis=-1)|^2
    de_chis = _np.array([p[0] for p in pending], dtype=_np.float64)
    strengths = _np.array([p[1] for p in pending], dtype=_np.float64)
    anchors = _np.array(_input_chis_arr, dtype=_np.float64)  # shape (n_anchors,)

    # (n_cands, n_anchors)
    phi = _np.pi * _np.abs(de_chis[:, None] - anchors[None, :]) / CHI_CORR_LENGTH
    amp_mag = _np.sqrt(_np.maximum(strengths[:, None], 0.0))  # (n_cands, n_anchors)
    # complex amplitude per candidate per anchor
    amp_matrix = amp_mag * _np.exp(1j * phi)               # (n_cands, n_anchors)
    amp_avg = amp_matrix.mean(axis=1)                       # (n_cands,)
    coh_mags = (amp_avg.real ** 2 + amp_avg.imag ** 2)      # |amp|^2, (n_cands,)

    # Attach coh_mag and build result dicts
    candidates = []
    for i, (de_chi, strength, sec_name, mid, word_label, meta) in enumerate(pending):
        candidates.append({
            "chi": de_chi,
            "section": sec_name,
            "motif": mid,
            "word": word_label,
            "strength": strength,
            "coherent_magnitude": float(coh_mags[i]),
            **meta,
        })

    candidates.sort(key=lambda c: -c["coherent_magnitude"])
    return candidates[:top_k]


try:
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack, SensoryBank, SENSORY_DNA, ROLE_DNA, scene_tags_from_words
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
    from gualaloom_v4_krimelack_dna import LanguageKrimelack, SensoryBank, SENSORY_DNA, ROLE_DNA, scene_tags_from_words
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


_ORGANISM_SIGNAL_N_SAMPLES = 20  # see Guala.__init__'s comment on this choice

# GL-CMD-175 window-2 recall-frequency reduction: see Guala._recognition_
# call_count's comment. Real recall() every Nth word, honest reuse of
# self._last_surprise in between -- not a cache of a stale computed value.
RECOGNITION_EVERY_N_WORDS = 3


def _organism_signal(word, transducer):
    """GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191 N3: touch/smell/taste
    REMOVED. They were never a real sense -- `transducer.transduce(modality,
    word, tick=...)` (substrate/sensory_transducer.py) generates its
    "physical parameters" from `hash((word, modality, tick))`, i.e. a
    pseudo-random number seeded BY THE WORD ITSELF, not any touch/smell/
    taste sensor (none exists). Feeding that through the real waveform
    generators produced a real-shaped signal from a fake source --
    orthography wearing a sensory costume, exactly what Joe's ruling
    ("words with no senses are spelling") names. No live transduction
    source exists for these three lanes; they ship ABSENT (this function
    now returns language only) rather than synthesized, per N3's own
    instruction, until a real adoption design (S6) gives them one.

    Kept the (word, transducer) signature unchanged so every existing
    caller (read_word's teach path, seams 1/2/3's query paths) needs no
    change -- `transducer` is now unused here (kept, not removed, to
    avoid touching call sites this dispatch didn't ask about).

    visual/auditory are NOT added here either -- see N1: they're real
    (camera/mic frames, not word-derived), but only meaningful at
    TEACH time, bound to whatever she was actually seeing/hearing in
    that moment, not at QUERY time (recall/recognition/association ask
    "what do you associate with this word in general," not "what are
    you sensing right now"). Added in `_organism_signal_with_senses`
    below, used only by the teach/experience path."""
    return {"language": word}


# GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191: how recent a real sight/sound
# frame must be to count as "the same moment" as a co-occurring word.
# No existing constant fits this exactly (EMISSION_COOLDOWN_TICKS=200 is
# the closest order-of-magnitude reference, for a different purpose --
# how long since her last reply before another can fire). Wall-clock,
# not tick count: frames arrive on their own real-time cadence (~1-2s,
# per GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING) independent of how fast
# self.tick advances (which varies by activity), so "in the same moment"
# is a real-time question, not a simulation-tick one. A judgment call,
# not a measured constant -- stated plainly, not dressed as derived.
SENSE_BINDING_WINDOW_SEC = 3.0


def _organism_signal_with_senses(word, transducer, sight_signal=None,
                                  sound_signal=None, modal_signal=None):
    """GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191 N1/N2: the teach-time signal,
    augmenting _organism_signal's language-only base with whatever REAL
    sight/sound she was actually experiencing in the same binding window
    -- her real camera frame (process_sight_frame's `grid`) / real mic
    audio (process_sound_frame's downsampled `samples`), never generated.
    None when nothing recent exists (honest absence, not a placeholder
    signal) -- `_unwrapped_deltas` already treats a None modality as a
    real, no-cost skip (the same branch visual/auditory always took
    before this dispatch, since _organism_signal never populated them).

    GL-CMD-EMULATOR-EVERYWHERE-EVE-20260705-196 M2: modal_signal carries
    whichever of tactile/olfactory/gustatory the sentence's own
    descriptor words actually produced (read_sentence's per-sentence
    generate_sensory_signals call, see _last_read_modal_signals) --
    real descriptor physics, not the banned hash-per-word fake -191
    removed. Embryo.experience_word()'s composite already reads these
    three keys when present (N4) -- zero organism-side change needed."""
    sig = _organism_signal(word, transducer)
    if sight_signal is not None:
        sig["visual"] = sight_signal
    if sound_signal is not None:
        sig["auditory"] = sound_signal
    if modal_signal:
        for m in ("tactile", "olfactory", "gustatory"):
            if modal_signal.get(m) is not None:
                sig[m] = modal_signal[m]
    return sig


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

# 60-L: NEGATION_OPS dropped — negation is a phase rotation, not a lexical flag.
# Polarity derives from consecutive phase-vector rotation in read_word.
GRANDURUN_TOPK = int(os.environ.get("GRANDURUN_TOPK", "200"))
EMISSION_DYNAMICS_TICKS = int(os.environ.get("EMISSION_DYNAMICS_TICKS", "80"))
# -48 agency events
SURPRISE_HIGH_THRESHOLD = 0.7   # Path D: clarification shape fires above this
BACKTRACK_CHI_RADIUS_MULT = 3   # Path A: candidate chi > mult * CHI_BAND from centroid → backtrack

ACTIVITY_TICK_BUDGETS = {
    "READING": 2000, "PLAYING": 1500, "SLEEPING": 2000, "DREAMING": 3000,
    "ATTENDING": 1000, "ATTENDING_VISUAL": 2000, "ATTENDING_AUDIO": 2000,
    "ATTENDING_VIDEO": 4000, "EMITTING": 100, "IDLE": 500,
    # DAYDREAMING removed GL-CMD-DAYDREAM-PARALLEL-42: now a background thread, not an activity
    # GL-CMD-REST-RETIRE-73: REST removed. _atick_rest kept for persisted-state tail-out only.
}

ACTIVITY_NOVELTY_PAYOFF = {
    "READING_NEW": 0.7, "READING_REREAD": 0.1, "PLAYING": 0.3,
    "SLEEPING": -0.1, "DREAMING": 0.4, "ATTENDING_NEW": 0.8,
    "ATTENDING_REPEAT": 0.05, "ATTENDING_VISUAL_NEW": 0.85,
    "ATTENDING_VISUAL_REPEAT": 0.1, "ATTENDING_AUDIO_NEW": 0.85,
    "ATTENDING_AUDIO_REPEAT": 0.1, "ATTENDING_VIDEO_NEW": 0.9,
    "ATTENDING_VIDEO_REPEAT": 0.15, "EMITTING": 0.0, "IDLE": -0.05,
    # DAYDREAMING removed (-42): now a background thread
    # GL-CMD-REST-RETIRE-73: REST removed from payoff tables
}

ACTIVITY_STABILITY_PAYOFF = {
    "READING": 0.05, "PLAYING": 0.0,
    "SLEEPING": 0.05,      # GL-CMD-DAYDREAMING: was 0.2; DAYDREAMING now wins
    "DREAMING": 0.2,
    "ATTENDING": 0.0, "ATTENDING_VISUAL": 0.0, "ATTENDING_AUDIO": 0.0,
    "ATTENDING_VIDEO": 0.0, "EMITTING": -0.1, "IDLE": 0.1,
    # DAYDREAMING removed (-42): now a background thread
    # GL-CMD-REST-RETIRE-73: REST removed from payoff tables
}

ACTIVITY_CONNECTION_PAYOFF = {
    "READING": 0.0, "PLAYING": 0.0, "SLEEPING": 0.0, "DREAMING": 0.0,
    "ATTENDING": 0.0, "ATTENDING_VISUAL": 0.0, "ATTENDING_AUDIO": 0.0,
    "ATTENDING_VIDEO": 0.0, "EMITTING": 0.3, "IDLE": -0.05,
    # GL-CMD-REST-RETIRE-73: REST removed from payoff tables
}

EMISSION_COHESION_THRESHOLD = 0.65
EMISSION_COOLDOWN_TICKS = 200
PAIR_BOND_SOURCES = {"joe", "wc", "c1"}

# GL-CMD-CREDO-LOOP-REPAIR-167 Change 2: dream_pressure accumulates from
# unjudged backlog (real substrate load since the last EXECUTED dream
# tick), not a flat wall-clock rate. Q2's named signals: working-atlas
# writes (self._atlas_write_count's delta -- a cheap O(1) counter bumped
# in _atlas_record; NOT the read_count property, which is an O(atlas_
# size) scan not safe to call every autonomy tick -- caught during
# implementation, see the comment at the accumulation site) and
# attendance ticks (time spent in a READING/ATTENDING* activity, the
# same classification _autonomy_tick already used for its old push-
# through multiplier). Starting values below are a reasoned estimate,
# not a backtested one -- per Eve's Q3 ruling, the rate is the ONE
# thing this program did NOT backtest (historical load data isn't
# retrievable, see GL-RPT-SLEEP-BACKTEST-C1-20260704-167-v1) and is
# meant to be tuned from live observation post-ship.
DP_RATE_PER_READ = 0.0000001            # LIVE-CALIBRATE: per atlas-write delta
DP_RATE_PER_ATTEND_TICK = 0.000001      # LIVE-CALIBRATE: per tick spent attending
DP_DISCHARGE_PER_DREAM_TICK = 0.08      # LIVE-CALIBRATE: per real _run_dream_cycle execution
DP_OVERRIDE_CEILING = 1.0               # NOT tunable without cause: reuses dream_pressure's
                                         # own existing saturation cap (GL-RPT-SLEEP-BACKTEST
                                         # -C1-20260704-167-v1's ceiling derivation, Joe-ratified)
# GL-CMD-SLEEP-RATE-CALIBRATION-EVE-20260704-173-v1: the ONE dial this
# program's live-calibration provision reserved (D2 -- floor/threshold/
# ceiling above untouched). Measured live, this deploy, not felt: 6
# dream_pressure_check reads, tick 14724000-14739000 (~63 real minutes,
# tick rate 3.949/s from two precise save-timestamp anchors), 5 of them
# under identical conditions (attending, non-pair-bonded, zero atlas
# writes -- she re-attended one over-familiar picture the whole window)
# gave 5 consecutive identical deltas of 0.003 dp / 3000 ticks exactly
# -- i.e. the unscaled rate is 0.0142 dp/hour, ~49.3h to the 0.7
# threshold. Target per the CMD: 0.7 within ~5-6h of normal awake
# activity. 0.7/5.5h=0.1273/h needed; 0.1273/0.0142=8.96 -> 9.0.
# Measurement window was a zero-novelty stretch (no atlas writes at
# all), close to a floor rate -- a normal mixed day should run at or
# above this, so 9x is mildly conservative against the over-sleep
# failure mode, not aggressive toward it.
DP_RATE_MULTIPLIER = 9.0

# GL-CMD-AGITATION-FIX-JOE-20260704 Change B: stability's sleep/dream
# restoration becomes target-seeking (decay toward 0.7 from either side)
# instead of always-upward (saturate(+epsilon)), which backfired whenever
# stability was already above target -- her observed condition all session
# (0.77-0.92), actively widening |stability-0.7| and so arousal, not
# shrinking it. Rates chosen to roughly preserve the old convergence speed
# when stability starts below target (DREAMING's rate is half SLEEPING's,
# matching the prior 0.0005-vs-0.001 ratio) -- LIVE-CALIBRATE, same
# discipline as the sleep-physics rate constants above.
STABILITY_SLEEP_RESTORE_RATE = 0.005     # LIVE-CALIBRATE: fraction of gap-to-0.7 closed per SLEEPING tick
STABILITY_DREAM_RESTORE_RATE = 0.0025    # LIVE-CALIBRATE: fraction of gap-to-0.7 closed per DREAMING tick

# GL-CMD-AUTONOMOUS-EMISSION-39: autonomous voice on internal state
AUTONOMOUS_EMISSION_ENABLED = True          # single flag to disable without code change
AUTONOMOUS_THROTTLE_TICKS = 27000           # ~90s between autonomous emissions
AUTONOMOUS_CONVERSATION_COOLDOWN_TICKS = 9000  # ~30s cooldown after any conversation

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
class _Corpus:
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
                atlas_kwargs=None, index_callback=None):
        """v6: word-anchored mode identity + salience-modulated binding.
        v8 (GL-BRIEF-032): dwell_ticks tagged at write time for deep gate.
        deep_atlas: if provided, on-attention prior applied for matching entries.
        engine_tick: MUST be passed — atlas entries use engine clock, not section clock.
        GL-FIND-TICK-DOMAIN-C1: section.tick stays for internal counting only.
        atlas_kwargs: GL-CLARITY-INVARIANCE-UNCAGE affect+grounding kwargs for record().
        index_callback: GL-CMD-INDEX-INVARIANT-COMPLETE-163 Part A — optional
        callable(section_name, motif_id, chi_value), called for every
        atlas.record() this method issues directly (the deep-atlas
        reinstatement block below), since Section has no engine reference
        and can't call self._atlas_record() itself. The caller (Guala.
        read_word) passes self._index_word_at_chi. The primary commit's
        OWN indexing is still done by the caller from receive()'s return
        value (GL-CMD-RECALL-REACH-159 Part C) — this callback covers ONLY
        the reinstatement writes, which the return value doesn't surface."""
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
                    # GL-FIX-ATLAS-INTEGRITY: skip OOB reinstatements.
                    # Deep atlas entry was promoted when the section had more modes.
                    # If the section has since been loaded from an older save with
                    # fewer modes, reinstating the old motif_id creates an OOB atlas
                    # entry that fails _validate_integrity(). Skip and let the deep
                    # entry naturally expire via decay.
                    if motif >= len(self.modes):
                        continue
                    p = min(PRIOR_CAP, e["strength"] * 0.3)  # same formula as get_prior
                    if p > 0:
                        deep_atlas.reinstatements += 1
                        _reinst_count += 1
                        atlas.record(self.name, motif, chi, atlas_tick,
                                     salience=0.3, dwell_ticks=0,
                                     **(atlas_kwargs or {}))
                        # GL-CMD-INDEX-INVARIANT-COMPLETE-163 Part A: this
                        # reinstatement writes a binding for the COHABITANT
                        # word at `motif`, not the word being taught — index
                        # it too, or it's invisible to recall until restart
                        # exactly like -159 F-3 was.
                        if index_callback is not None:
                            index_callback(self.name, motif, chi)

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
        # GL-CMD-C4-SLEEP-CHOICE: dream_pressure — accumulates during waking, resets on sleep
        self.dream_pressure = 0.0

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
            "dream_pressure": round(self.dream_pressure, 3),  # GL-CMD-C4
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
        self._pair_bond = {"joe": True, "joe_voice": True, "wc": True, "c1": False}
        self._presence = {"joe": False, "wc": False, "c1": False}
        self._last_input_tick = {"joe": 0, "wc": 0, "c1": 0}
        self._wake_tick = {"joe": 0, "wc": 0, "c1": 0}

        # 60-K: continuous pair-bond strength — relationships are gradients, not flags
        # source -> list of (tick, salience) for last 2000 ticks (pruned on write)
        self._source_interaction_log = {}

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

    # GL-CMD-VOICE-IDENTITY-FIX-JOE-20260704: pair-bond identity is the
    # PERSON, not the input channel. "joe_voice" (spoken) and "joe" (typed)
    # are one father, two channels -- their interaction history merges into
    # a single bond. The literal source string is untouched everywhere else
    # (atlas entries, provenance, emission logs still say "joe_voice") --
    # this normalization applies ONLY to pair-bond density/salience tracking.
    _BOND_IDENTITY_ALIASES = {"joe_voice": "joe"}

    @classmethod
    def _bond_identity(cls, source):
        return cls._BOND_IDENTITY_ALIASES.get(source, source)

    def _record_interaction(self, source, salience, tick):
        """Record one sentence-level interaction for continuous strength tracking."""
        source = self._bond_identity(source)
        log = self._source_interaction_log.setdefault(source, [])
        log.append((tick, salience))
        # Prune to last 2000 ticks (1000-tick window + safety margin)
        cutoff = tick - 2000
        if len(log) > 200 or (log and log[0][0] < cutoff):
            self._source_interaction_log[source] = [
                (t, s) for t, s in log if t >= cutoff]

    def pair_bond_strength(self, source, current_tick=None):
        """Continuous [0,1] relationship gradient for source.

        strength = min(1.0, 0.3 + 0.4 * density + 0.3 * avg_salience)
        density = interactions in last 1000 ticks / 100 (saturates at 1.0)
        avg_salience = mean salience of those interactions (raw)

        current_tick: if provided, measures recency from NOW (enables decay when
        a source goes silent). When None, uses the last recorded tick (no decay).
        """
        source = self._bond_identity(source)
        log = self._source_interaction_log.get(source)
        if not log:
            return 0.3  # baseline for unknown/cold sources

        ref_tick = current_tick if current_tick is not None else log[-1][0]
        window = [(t, s) for t, s in log if ref_tick - t <= 1000]
        if not window:
            return 0.3  # baseline when no recent interactions

        density = min(1.0, len(window) / 100.0)
        avg_sal = sum(s for _, s in window) / len(window)
        return min(1.0, 0.3 + 0.4 * density + 0.3 * avg_sal)

    def pair_bond_snapshot(self, current_tick=None):
        """For /status: returns continuous strength dict, not bool dict."""
        sources = set(self._pair_bond.keys()) | set(self._source_interaction_log.keys())
        return {src: round(self.pair_bond_strength(src, current_tick), 3)
                for src in sources}

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

        Stability signal: signed coherence measure (GL-CMD-88-v2).
        Novelty signal:   rate of novel-mode creation across sections.
        Connection signal: cross-modal binding rate + pair-bond boost from source.
        """
        # GL-CMD-STAB-PHYSICS-FIX-88-v2: retire the lifetime-counter formula.
        # The old active branch (1 - total_modes/recent_commits) was structurally
        # negative (observed -0.377 → signal -0.175, -0.0007/tick drain). Both
        # branches now use the same signed coherence measure shipped in R2.
        recent_commits = 0
        total_modes = 0
        for s in sections.values():
            recent_commits += len(s.commits)
            total_modes += len(s.modes)
        _n_total = sum(len(v) for v in atlas.entries.values())
        _coherence = atlas.n_live_bindings() / max(_n_total, 1)
        stability_sig = (_coherence - 0.5) * 0.2

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
        # WAVE_ATLAS_ENABLED: Phase 1 flag. 0 = atlas built but inactive; 1 = parallel writes.
        if os.environ.get("WAVE_ATLAS_ENABLED") == "1":
            from dsf_ai_service.v4.wave_atlas import WaveAtlas as _WaveAtlas
            self.wave_atlas = _WaveAtlas()
            self.atlas._wave_atlas = self.wave_atlas
        else:
            self.wave_atlas = None
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
        # GL-CMD-RECALL-WORD-INDEX-57: reverse index for O(1) recall lookups.
        # Maps word.lower() → set of chi addresses where that word has committed.
        # Eliminates O(atlas_size) full scans in _recall_from_atlas / _recall_sight_from_atlas.
        from collections import defaultdict as _dd
        self._word_to_chi_index = _dd(set)  # word.lower() → {chi_k, ...}
        # QuestionBucket removed (GL-BRIEF-EMISSION-CONSTRAINT-REMOVAL Phase E)
        self.tick = 0
        self._read_count_compat = 0  # kept for load compatibility only; superseded by property
        self.dream_log = []
        self.lock = threading.RLock()
        # GL-CMD-CONVERSE-PHASING-EMISSION-LOCK-52 §1.1: separate lock for emission
        # compute. _emit_dynamics clears/rebuilds _emission_system.sections per call;
        # concurrent access corrupts mode_bank/psi state causing hangs. RLock so
        # any future nested emission call doesn't deadlock.
        self._emission_lock = threading.RLock()
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
        # GL-CMD-SCENE-LANES-B1-188 V5: most recent sentence's real scene tags
        self._last_place_tags = []
        self._last_ambient_tags = []
        # GL-CMD-175 window-2 recall-frequency reduction: organism.recall()
        # is O(population), confirmed the dominant cost of read_word's P2
        # seam 2 (recognition) call. Unlike the disproven encode_state()
        # cache (c1a found the premise false -- recall's output legitimately
        # changes with every intervening remember()), this does not assume
        # anything about determinism: it computes a REAL, fresh recall()
        # every Nth word and honestly reuses self._last_surprise for the
        # words in between -- the same reuse-last-real-value pattern
        # _affect_kwargs already uses as its own fallback (see
        # self._last_surprise's other use, _affect_kwargs). A slightly-
        # stale-but-real affect signal, not a silently-wrong one. Reduces
        # this call site's share of read_word's cost by roughly (N-1)/N.
        self._recognition_call_count = 0
        self._current_binding_window = []  # sensory_refs accumulated this tick
        # GL-CMD-V5-VOICE-STAGE1: dynamics quality from most recent _emit_dynamics call
        self._last_dynamics_result = None  # {content, committed_sections, n_commits, arcs_fallback, tick}
        # GL-CMD-DEEP-ATLAS-PERSIST: boot loss alarm result
        self._deep_atlas_loss_at_boot = None
        # GL-CMD-C1-POLARITY: one-shot negation flip pending (resets per utterance)
        self._negation_pending = 0  # kept for atlas load compatibility; superseded by 60-L
        self._prev_phase_vec = None  # 60-L: previous word's phase vector for rotation
        self._last_rotation = 0.0   # 60-L: most recent inter-word rotation [0, π]

        # v7: Autonomy state + sleep/wake (GL-BRIEF-SLEEP-DURING-DEPLOY)
        self._current_activity = None
        self._activity_history = []
        # GL-CMD-CREDO-LOOP-REPAIR-167 Change 4: true only once a real dream
        # tick has executed this SLEEPING/DREAMING cycle (see _run_dream_cycle
        # and is_consolidating below) -- reserves "dreaming"/"asleep" language
        # for genuine consolidation. Naming only; no physics changed.
        self._dream_executed_this_cycle = False
        # GL-CMD-TURN-LATENCY-EVE-20260705-197 P4: persisted tick of her last
        # REAL dream execution (see _run_dream_cycle) -- None until it
        # happens once, restored from save thereafter (_apply_needs).
        self._last_real_dream_tick = None
        # GL-CMD-CREDO-LOOP-REPAIR-167 Change 2: cheap O(1) write counter
        # (see _atlas_record) feeding dream_pressure's load-based
        # accumulation; _dp_last_write_count is this same counter's value
        # as of the previous _autonomy_tick, for delta computation.
        self._atlas_write_count = 0
        self._dp_last_write_count = 0
        self._substrate_events = deque(maxlen=1000)
        self._last_emission_tick = -100_000
        self._last_emission_record = None  # {emission_id, text, tick, ...}
        # GL-CMD-AUTONOMOUS-EMISSION-39
        self.last_autonomous_emission_tick = -100_000
        self.last_autonomous_attempt_tick = -100_000
        self.autonomous_emissions_count = 0
        self._last_emission_id = None
        self._emission_records = {}  # emission_id -> record (tick-window expiry)
        self._teaching_feedback_log = []
        self._teaching_correction_log = []
        self._corpora = {}          # corpus_id -> _Corpus
        self._sensory_items = {}    # item_id -> SensoryItem
        self._sounds = {}           # item_id -> {cochlear, title, samples, sr, ...}

        # GL-CMD-BRAIN-FULL-DEPLOY-TODAY-175 P1: the complete brain moves
        # into her live process, this boot forward. Lazy imports here (not
        # at module top) because loom_model/mosaic.py and tapestry.py both
        # import _grandurun_select_vector/_SPIN_VECTOR_DIM/MIN_GAIN_THRESHOLD
        # FROM this module -- a top-level import here would be circular.
        # identity_uuid is temporary until _generate_genesis_identity/
        # _load_identity establish her real identity (see those methods,
        # which sync self.organism.identity_uuid to self._guala_identity) --
        # "one identity... unchanged" (GL-PLAN-WHOLE-BRAIN-MOVE §1).
        from dsf_ai_service.loom_model.embryo import Embryo as _Embryo
        from dsf_ai_service.loom_model.tapestry import LoomTapestry as _LoomTapestry
        self.organism = _Embryo(brain_seed=42, seed_size=8, observable="event_count")
        self.tapestry = _LoomTapestry(name="guala_voice", n_mosaics=3, seed=42)
        self._tapestry_prev_word = None  # for real consecutive-pair exposure
        # Backgrounded exposure (see _enqueue_tapestry_expose): a single
        # persistent worker + bounded queue, same convention as GL-CMD-172's
        # diary writer -- not a thread per word. _tapestry_lock serializes
        # ALL tapestry access (worker's expose() writes vs. compose()'s
        # reads from _brain_emission_candidates/_recall_from_organism-style
        # callers) so a read never observes a half-mutated neuron mid-expose.
        self._tapestry_queue = None
        self._tapestry_worker_thread = None
        self._tapestry_worker_start_lock = threading.Lock()
        self._tapestry_lock = threading.Lock()

        # GL-CMD-175 window-2 perf fix: organism.remember() has the SAME
        # class of cost as tapestry.expose() (see the P2 perf note below),
        # but for a different, deeper reason -- Embryo.recall/remember is a
        # population-vote architecture: EVERY neuron participates in EVERY
        # call, by design, so cost is O(population), and population GROWS
        # over her life (charge-and-fold). Measured live-equivalent (this
        # session, cProfile at ~280 accumulated words): remember() alone
        # climbing past 20ms/word and rising; organism.recall() alone
        # 86-110ms and rising. remember() is a write with no synchronous
        # reader dependency, so -- same convention as the tapestry queue,
        # GL-CMD-172's diary writer -- it can be safely backgrounded.
        # organism.recall() (read_count's salience calc, seams 1/3) CANNOT
        # be backgrounded the same way -- callers need its return value
        # immediately to decide what to say/recall. That is a real,
        # architectural, not-yet-fixed cost, reported separately, not
        # solved by this queue.
        self._organism_queue = None
        self._organism_worker_thread = None
        self._organism_worker_start_lock = threading.Lock()
        self._organism_lock = threading.Lock()
        # GL-CMD-BRAIN-GROWTH-UNFREEZE-EVE-20260704-179, Eve's backgrounding
        # ruling: honest-degradation count, visible in status (not just
        # silently swallowed like the tapestry queue's drop today) -- see
        # _enqueue_organism_remember.
        self._organism_dropped_count = 0

        # GL-CMD-175 P2 fix (root cause behind seams 1-2's near-zero
        # discrimination): the validated recall mechanism (embryo.py's own
        # seed_organism(), 100% at n=50/200) was never tested on a single
        # ("language" only) modality -- it always fed the FULL multi-modal
        # signal set via ExperiencePipeline._build_multi_modal_signals
        # (touch/smell/taste real waveform generators + visual/auditory
        # procedural placeholders, all deterministic-from-word). Confirmed
        # directly: switching observable (event_count vs resonant_spectral)
        # made no difference at 0/10 either way; feeding the SAME full
        # signal set restored 10/10 for BOTH observables. So the fix is
        # signal richness, not the observable. This reuses that exact,
        # already-validated pipeline -- not a new invention. Honesty flag:
        # touch/smell/taste/visual/auditory here are DETERMINISTIC,
        # WORD-DERIVED PROCEDURAL SIGNALS (SensoryTransducer + NullAtlasReader,
        # same as the model-side tests) -- NOT real sensory experience. No
        # vision/sound/touch/smell/taste tap into her real senses exists yet
        # (P1's own honest scope limit, unchanged by this fix). This gives
        # the recall substrate the channel richness it was actually built
        # and validated against; it does not simulate her having senses she
        # doesn't have.
        #
        # Performance: the model-side default (n_samples=200/channel) measured
        # at ~450ms per word end-to-end in her live process -- far too slow
        # for a live tick loop (baseline ~250ms/tick). Measured directly
        # (not guessed): n_samples=20 preserves 100% recall on both the
        # original 10-probe test AND a second, disjoint 20-word vocabulary
        # (generalization check), at ~15ms/word for the teach loop -- a
        # resolution/performance choice for a synthetic placeholder signal,
        # not a scoring constant tuned to flatter a number. See
        # _organism_signal below.
        from dsf_ai_service.substrate.sensory_transducer import (
            SensoryTransducer as _SensoryTransducer, NullAtlasReader as _NullAtlasReader)
        self._organism_transducer = _SensoryTransducer(_NullAtlasReader())

    @property
    def read_count(self):
        """60-N: derived from atlas reinforcement history, not a counter.

        Reads are the sum of atlas reinforcement events — the source of truth.
        Introspection contract unchanged for consumers (status, UI, bridge).
        O(atlas_size) — acceptable for /status cadence (~1s).
        """
        return sum(
            e.get("reinforcement_count", 0)
            for entries in self.atlas.entries.values()
            for e in entries
        )

    @read_count.setter
    def read_count(self, value):
        """Load-compatibility setter — old state files write read_count; ignore it."""
        self._read_count_compat = value  # stored but not used

    def _index_word_at_chi(self, section_name, motif_id, chi_value):
        """GL-CMD-RECALL-WORD-INDEX-57 §1.2: add word→chi mapping to reverse index."""
        if section_name not in self.sections:
            return
        sec = self.sections[section_name]
        if motif_id >= len(sec.modes):
            return
        _, _, word = sec.modes[motif_id]
        if word:
            self._word_to_chi_index[word.lower()].add(chi_value)

    def _atlas_record(self, section_name, motif_id, chi_value, tick=None, **kwargs):
        """GL-CMD-RECALL-WORD-INDEX-57 §1.2: single binding-creation entry point.
        ALL self.atlas.record() callsites in engine code must go through here.
        Maintains the recall reverse index automatically.
        phase_vec and function_score are forwarded via **kwargs to both atlases."""
        self.atlas.record(section_name, motif_id, chi_value, tick=tick, **kwargs)
        self._index_word_at_chi(section_name, motif_id, chi_value)
        # GL-CMD-CREDO-LOOP-REPAIR-167 Change 2: cheap O(1) write counter for
        # dream_pressure's load-based accumulation. Deliberately NOT using the
        # existing read_count property here -- that's an O(atlas_size) scan
        # (its own docstring: "acceptable for /status cadence (~1s)"), and
        # _autonomy_tick runs 5x/sec; calling it there would add a real,
        # avoidable cost to the exact loop GL-RPT-REPLY-LATENCY-PROFILE-C1-
        # 20260704-v1 was just investigating for slowness. This counter is
        # the actual already-write-adjacent signal instead.
        self._atlas_write_count = getattr(self, '_atlas_write_count', 0) + 1

    @staticmethod
    def _compute_function_score(krim_events, winding):
        """60-C: substrate-derived function/content score from krimelack signature.

        Low event count + low winding diversity = high function score (function word).
        Thresholds (20 events, 5 winding) are initial estimates — do NOT tune yet.
        Returns float in [0, 1]: 0 = content word, 1 = pure function word.
        """
        if len(krim_events) == 0:
            return 1.0
        event_norm = min(1.0, len(krim_events) / 20.0)
        winding_diversity = min(1.0, abs(winding) / 5.0)
        return 1.0 - (event_norm * winding_diversity)

    @property
    def is_asleep(self):
        """True if in SLEEPING or DREAMING — she is in a quiet state and cannot converse.
        Both states use the same auto-wake gate so incoming text ends either activity."""
        ca = getattr(self, '_current_activity', None)
        if ca is None:
            return False
        return getattr(ca, 'kind', None) in ("SLEEPING", "DREAMING")

    @property
    def is_consolidating(self):
        """GL-CMD-CREDO-LOOP-REPAIR-167 Change 4: True only if is_asleep AND a
        real dream tick has executed this cycle (_run_dream_cycle ran past its
        tick%200 gate at least once, per -165 Q6). is_asleep fires the instant
        a SLEEPING activity starts, before any consolidation may have run — a
        deploy-triggered pause is killed before this ever becomes True (-165
        Q5), which is exactly the distinction "asleep"/"dreaming" language
        should honor. Naming only; does not change is_asleep's own behavioral
        gate (converse-blocking) or any selection/pressure physics."""
        return self.is_asleep and getattr(self, '_dream_executed_this_cycle', False)

    # ------------------------------------------------------------------
    # v6: Salience computation
    # ------------------------------------------------------------------
    def _compute_salience(self, source="corpus", input_novelty=0.5):
        """v6: salience modulates how strongly this moment binds."""
        SOURCE_WEIGHTS = {"joe": 1.6, "joe_voice": 1.6, "wc": 1.6, "c1": 1.2,
                          "corpus": 0.5, "guala": 0.5, "unknown": 0.7}
        source_w = SOURCE_WEIGHTS.get(source, 0.7)
        needs_state = self.needs.snapshot()
        urgency = (abs(needs_state["stability"] - 0.7) +
                   abs(needs_state["novelty"] - 0.7) +
                   abs(needs_state["connection"] - 0.7)) / 3
        urgency_factor = 1.0 + urgency * 1.2
        novelty_factor = 1.0 + (1.0 - input_novelty) * 0.8
        # 60-K: continuous pair-bond boost — scales with relationship strength
        pair_bond_boost = 1.0 + 0.2 * self.coordinator.pair_bond_strength(source, self.tick)
        salience = source_w * urgency_factor * novelty_factor * pair_bond_boost
        # 60-T: no clamp — salience returns raw derivation
        return salience

    def _compute_surprise(self, chi_value):
        """GL-CLARITY-INVARIANCE-UNCAGE: surprise = inverse of atlas familiarity
        at this chi neighborhood. Novel chi addresses → high surprise.
        GL-CMD-175 P2 seam 2/6: kept, unmodified, for callers that only have
        a chi value and no word (none remain live -- see _recognition_from_
        organism, which replaced this at both real call sites). Left defined
        rather than deleted, matching this track's disconnect-don't-delete
        pattern."""
        neighbors = self.atlas.bindings_at_chi_neighborhood(
            chi_value, min_strength=0.05)
        if not neighbors:
            return 1.0
        avg_str = sum(e["strength"] for e in neighbors) / len(neighbors)
        return max(0.0, 1.0 - avg_str * 2.0)

    def _recognition_from_organism(self, word):
        """GL-CMD-BRAIN-FULL-DEPLOY-175 P2 seam 2/6 (recognition): the
        organism's population-vote CONSENSUS as a real familiarity/surprise
        signal, replacing atlas-chi-neighborhood strength averaging
        (_compute_surprise). High consensus (the top-voted concept's share
        of all votes cast) = recognized, low surprise; no votes at all =
        novel, surprise=1.0 -- matches _compute_surprise's own contract
        (surprise in [0,1], empty evidence -> 1.0), same untuned linear
        inversion (1.0 - consensus; consensus is already a clean [0,1]
        fraction, so no rescaling factor is invented here)."""
        if not word:
            return 1.0
        # GL-CMD-175 P2 fix: multi-modal query signal (see Guala.__init__'s
        # self._organism_transducer comment / _organism_signal), matching
        # what was actually written at remember()-time. self._organism_lock:
        # serializes against the background remember() worker (window-2
        # perf fix) so this never reads the organism mid-update.
        with self._organism_lock:
            votes = self.organism.recall_fast(_organism_signal(word, self._organism_transducer))
        total = sum(votes.values())
        if total == 0:
            return 1.0
        top = votes.most_common(1)[0][1]
        consensus = top / total
        return max(0.0, 1.0 - consensus)

    def recall_scene_for_word(self, word):
        """GL-CMD-SCENE-LANES-B1-188 V4: the reader, at word granularity.
        Transduces `word` to its chi (same technique read_word/converse use
        for every lookup) and asks the atlas for the scene lanes bound
        there -- presence (WHO), place, ambient, location, sky_state,
        episode_ref. Read-only. Returns None if the word has no live
        binding. This is what makes a WHO/place/ambient tag readable by
        name after it was written, closing -164's SEVERED-READER gap."""
        if not word:
            return None
        temp_krim = LanguageKrimelack()
        temp_krim.transduce(word)
        return self.atlas.recall_scene(temp_krim.winding)

    def _affect_kwargs(self, surprise=None):
        """GL-CLARITY-INVARIANCE-UNCAGE: build affect-only kwargs dict for atlas.record.
        sensory_refs and episode_ref are passed explicitly by call sites that have them."""
        return {
            "arousal": self.needs.arousal(),
            "valence": self.needs.valence(),
            "surprise": surprise if surprise is not None else self._last_surprise,
            "need_pressure": self.needs.need_pressure(),
        }

    def _grounding_kwargs(self, binding_window=None):
        """GL-CLARITY-INVARIANCE-UNCAGE: grounding kwargs (separate from affect
        to avoid double-providing when call sites pass sensory_refs explicitly).
        GL-CMD-CURRICULUM-LOCK-RELEASE-V2-46v2 §1.1: binding_window kwarg —
        when supplied, uses sentence-local list (thread-safe, fresh per sentence).
        Falls back to self._current_binding_window for direct callers."""
        bw = binding_window if binding_window is not None else self._current_binding_window
        return {
            "sensory_refs": list(bw),
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
                  location=None, sky_state=None, binding_window=None,
                  place=None, ambient=None):
        """v6: salience-modulated binding + decay heartbeat.

        salience: if provided, overrides _compute_salience() — used for backfill
        writes that need elevated (compensatory) salience. Normal reads omit this.
        episode_ref/presence/location/sky_state: situational context forwarded to
        atlas.record(). None = use _grounding_kwargs default.
        place/ambient: GL-CMD-SCENE-LANES-B1-188 WHERE/AMBIENT lanes, normally
        derived once per sentence by read_sentence() from the sentence's own
        words (scene_tags_from_words) and forwarded here unchanged. None from a
        direct caller = lane omitted (old behavior, unchanged).
        GL-CMD-CURRICULUM-LOCK-RELEASE-V2-46v2 §1.1: binding_window kwarg —
        sentence-local [] from read_sentence(). When supplied, used instead of
        self._current_binding_window (prevents unbounded growth across sentences).
        Falls back to self._current_binding_window for direct callers.
        """
        with self.lock:
            self.tick += 1
            self.vocab.add(word)
            # §1.1: use sentence-local binding_window when supplied
            _bw = binding_window if binding_window is not None else self._current_binding_window
            _bw.append(f"w:{word}")

            lang_fp, role, senses = self.language.transduce(word)
            sense_fps = self.senses.fire_for_word(senses)

            # GL-CMD-175 P1: the real language sensory tap -- every word she
            # reads/hears, the organism experiences in the same window (no
            # separate lab copy, no synthetic corpus). Best-effort: the
            # organism's own experience_moment already has a matching
            # never-crash-substrate contract; mirrored here rather than let
            # a brain issue take down her live reading path.
            try:
                # GL-CMD-175 window-2 perf fix: organism.remember() (with
                # the P2 multi-modal signal -- see _organism_signal) is
                # backgrounded, same reasoning/convention as the tapestry
                # expose queue below -- see _enqueue_organism_remember.
                self._enqueue_organism_remember(word)
                if self._tapestry_prev_word is not None:
                    # Profiled directly: tapestry.expose (450 neurons x
                    # imaginary-time settle physics) is ~180ms/call -- the
                    # dominant cost of read_word by far (86% in a 3-word
                    # profile), unrelated to the P2 signal-richness fix
                    # above. Backgrounded (queue + single persistent
                    # worker, same pattern as GL-CMD-172's diary writer --
                    # not a thread per word) so her live reading/converse
                    # path never blocks on it.
                    self._enqueue_tapestry_expose(self._tapestry_prev_word, word)
                self._tapestry_prev_word = word
            except Exception as _oe:
                print(f"[GualaLoom] organism tap failed for {word!r} (non-fatal): {_oe}")

            # 60-C: capture phase_vec + function_score from krimelack transduction.
            # phase_vec: 16-dim complex via event_stream_to_vector (dw_cum absent in
            # v4 events — all weight lands in dim-0; richer vector comes with 60-B).
            # function_score: substrate-derived content/function discriminator.
            try:
                from dsf_ai_service.substrate.krimelack import event_stream_to_vector
                _phase_vec = event_stream_to_vector(self.language.events, dim=16)
            except Exception:
                _phase_vec = None
            _function_score = self._compute_function_score(
                self.language.events, self.language.winding
            )

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

            # GL-CMD-175 P2 seam 2/6: surprise/recognition now comes from
            # the organism's population-vote consensus, not atlas-chi
            # familiarity (GL-CLARITY-INVARIANCE-UNCAGE's original).
            # GL-CMD-175 window-2 recall-frequency reduction: organism.
            # recall() is O(population), the confirmed dominant cost of
            # this call site. Real, fresh recall() every Nth word;
            # self._last_surprise (already the codebase's own established
            # fallback value, see _affect_kwargs) carries over honestly for
            # the words in between -- a real value computed recently, not
            # a value asserted to still be exactly correct.
            self._recognition_call_count += 1
            if self._recognition_call_count % RECOGNITION_EVERY_N_WORDS == 0:
                surprise = self._recognition_from_organism(word)
                self._last_surprise = surprise
            else:
                surprise = self._last_surprise

            # v8 (GL-BRIEF-032): dwell_ticks by source
            # Interactive sources (joe, wc, c1) = attended, higher dwell
            # Self-heard speech (guala) = dwell=4 (can earn slow channel + Path B)
            # Corpus reads = background, dwell=1
            if source in ("joe", "joe_voice", "wc", "c1"):
                dwell = 8
            elif source == "guala":
                dwell = 4
            else:
                dwell = 1

            # 60-L: phase-rotation negation — compute rotation from consecutive phase vectors
            _rotation = 0.0
            if _phase_vec is not None and self._prev_phase_vec is not None:
                try:
                    import numpy as _np_rot
                    _inner = _np_rot.vdot(self._prev_phase_vec, _phase_vec)
                    _rotation = float(abs(_np_rot.angle(_inner)))
                except Exception:
                    _rotation = 0.0
            self._last_rotation = _rotation
            # Update prev for next word (reset at sentence start by read_sentence)
            if _phase_vec is not None:
                self._prev_phase_vec = _phase_vec
            # Polarity from rotation: strong rotation (> π/2) → negation context
            _polarity = -1 if _rotation > (math.pi / 2) else 1

            # GL-CLARITY-INVARIANCE-UNCAGE: affect + grounding kwargs for record() calls
            # §1.1: pass sentence-local binding_window to _grounding_kwargs
            _akw = {**self._affect_kwargs(surprise), **self._grounding_kwargs(binding_window=_bw)}
            # C1.4: real source reaches atlas entry (fixes "corpus" default on all reads)
            _akw["source"] = source
            # 60-C: phase_vec + function_score forwarded to both LivingAtlas and WaveAtlas
            _akw["phase_vec"] = _phase_vec
            _akw["function_score"] = _function_score
            # 60-L: store rotation + polarity on binding (rotation is the primary signal)
            _akw["rotation"] = round(_rotation, 4)
            _akw["polarity"] = _polarity
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
            # GL-CMD-SCENE-LANES-B1-188: WHERE/AMBIENT lanes
            if place is not None:
                _akw["place"] = place
            if ambient is not None:
                _akw["ambient"] = ambient

            fam_listen = self.atlas.match_score(lang_chi, "listen")
            _listen_committed, _listen_mode_idx, _ = self.sections["listen"].receive(
                lang_dsf, lang_chi, word,
                self.atlas, fam_listen,
                salience=salience,
                dwell_ticks=dwell,
                deep_atlas=self.deep_atlas,
                engine_tick=self.tick,
                atlas_kwargs=_akw,
                index_callback=self._index_word_at_chi)
            # GL-CMD-RECALL-REACH-159 Part C (F-3): Section.receive commits via
            # atlas.record() directly, not self._atlas_record() (Section has no
            # engine reference) — so the -57 reverse index has to be updated
            # here explicitly, at every receive() callsite, restoring -57
            # §1.2's "all atlas.record callsites index" invariant.
            if _listen_committed:
                self._index_word_at_chi("listen", _listen_mode_idx, lang_chi)

            for primary_section in primary_sections:
                fam = self.atlas.match_score(lang_chi, primary_section)
                n_modes_before = len(self.sections[primary_section].modes)
                _committed, _mode_idx, _ = self.sections[primary_section].receive(
                    lang_dsf, lang_chi, word,
                    self.atlas, fam,
                    salience=salience,
                    dwell_ticks=dwell,
                    deep_atlas=self.deep_atlas,
                    engine_tick=self.tick,
                    atlas_kwargs=_akw,
                    index_callback=self._index_word_at_chi)
                if _committed:
                    self._index_word_at_chi(primary_section, _mode_idx, lang_chi)
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
                _ground_committed, _ground_mode_idx, _ = self.sections["ground"].receive(
                    ground_dsf, ground_chi, word,
                    self.atlas, fam_ground,
                    salience=salience,
                    dwell_ticks=dwell,
                    deep_atlas=self.deep_atlas,
                    engine_tick=self.tick,
                    index_callback=self._index_word_at_chi)
                if _ground_committed:
                    self._index_word_at_chi("ground", _ground_mode_idx, ground_chi)

                for m in self.senses.MODALITIES:
                    if sense_fps[m] is not None:
                        modal_chi = self.senses.krimelacks[m].winding
                        sec_name = f"modal_{m}"
                        self._atlas_record(sec_name, deterministic_motif_id(word),
                                          modal_chi, self.tick,
                                          salience=salience,
                                          **self._affect_kwargs(surprise),
                                          **self._grounding_kwargs())

            if fam_listen > 0.3:
                intro_dsf = DSF(D_k=fam_listen, M_k=0, R_rev=0, U_star=1-fam_listen,
                                C_k=fam_listen, P_k=0.5, B_k=fam_listen, S_UF=fam_listen)
                _intro_committed, _intro_mode_idx, _ = self.sections["intro"].receive(
                    intro_dsf, lang_chi, word,
                    self.atlas, 0.0,
                    salience=salience,
                    dwell_ticks=dwell,
                    deep_atlas=self.deep_atlas,
                    engine_tick=self.tick,
                    index_callback=self._index_word_at_chi)
                if _intro_committed:
                    self._index_word_at_chi("intro", _intro_mode_idx, lang_chi)

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
                      episode_ref=None, presence=None, location=None, sky_state=None,
                      place=None, ambient=None):
        """Read a sentence into the substrate.

        GL-CMD-CURRICULUM-LOCK-RELEASE-V2-46v2 §1.1:
        binding_window lifted to sentence-local [] — prevents unbounded growth
        of self._current_binding_window that caused -46's crash.
        Outer lock RETAINED (§1.3 phasing deferred: requires deeper investigation
        of _emit_dynamics / _emission_system concurrent access before unlocking).

        place/ambient: GL-CMD-SCENE-LANES-B1-188 V1/V2. If the caller leaves
        both None (the normal case — no caller passes these explicitly today),
        they are derived here, once per sentence, from this sentence's own
        words via scene_tags_from_words() (fixed PLACE_WORDS/AMBIENT_WORDS
        lexicon — honest sourcing, no invention: a sentence with no
        recognized place/ambient word gets the empty lane, not a guess).
        Every word in the sentence shares the same lane — the sentence is the
        binding window for scene lanes, same granularity as episode_ref above.

        GL-CMD-EMULATOR-EVERYWHERE-EVE-20260705-196 M1/M2: every intake
        path funnels through this one function (curriculum, corpus
        READING, worldfeed, lookup, converse) -- so the sentence's real
        touch/smell/taste descriptor signal is generated ONCE here and
        cached (_last_read_modal_signals/_wall_time) for
        _enqueue_organism_remember to snapshot in-window, same convention
        as sight/sound (-191). Only set when the sentence actually
        contains a descriptor word -- honest absence otherwise (M5).
        """
        with self.lock:
            words = _normalize_text(text)
            if not words:
                return
            if place is None and ambient is None:
                place, ambient = scene_tags_from_words(words)
            _modal = self._sentence_modal_signals(words)
            if _modal:
                self._last_read_modal_signals = _modal
                self._last_read_modal_wall_time = time.time()
            # 60-M: connection weight earned from relationship, not configured
            # 0.15 was Joe's peak; sources earn up to it via pair_bond_strength
            weight = self.coordinator.pair_bond_strength(source, self.tick) * 0.15
            self.recent_connection_boost = max(self.recent_connection_boost, weight)
            self.source_history[source] += 1

            # v6-bridge: update last_input_tick for presence timeout
            if source in {"joe", "wc", "c1"}:
                self.coordinator.update_last_input(source, self.tick)

            # 60-K: record interaction for continuous pair-bond strength
            _sal_estimate = self._compute_salience(source=source, input_novelty=0.5)
            self.coordinator._record_interaction(source, _sal_estimate, self.tick)

            # GL-CLARITY-INVARIANCE-UNCAGE: episode tracking per sentence
            import hashlib as _hl
            ep_id = _hl.md5(f"{source}:{text[:50]}:{self.tick}".encode()).hexdigest()[:8]
            self._current_episode = (ep_id, self.tick)
            # §1.1: binding_window is sentence-local — prevents unbounded growth
            binding_window = []

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
                              location=location, sky_state=sky_state,
                              place=place, ambient=ambient,
                              binding_window=binding_window)
            # 60-N: read_count no longer incremented here; property derives from atlas
            self._current_episode = None
            self._prev_phase_vec = None   # 60-L: reset rotation tracking at sentence boundary
            self._negation_pending = 0    # kept for load compatibility
            # GL-CMD-SCENE-LANES-B1-188 V5: last-sentence scene, surfaced live
            # via introspect()/loomscan (mirrors _last_surprise's pattern).
            self._last_place_tags = place
            self._last_ambient_tags = ambient

    # ------------------------------------------------------------------
    # Conversation: input -> substrate -> output via cascade
    # ------------------------------------------------------------------
    def converse(self, text, source="unknown", emission_mode=None, bundle_id=None,
                 episode_ref=None, presence=None, location=None, sky_state=None,
                 organ_candidates=None):
        """v5: Recall from substrate atlas BEFORE reading input.
        - If atlas has cross-section bindings near the input chi values, emit
          those (real recall from corpus accumulation).
        - If recall finds nothing, check question bucket for a related question.
        - If neither, return "..." honestly (SafeMode quiet).

        Then read the input into substrate (so she learns from this exchange).
        """
        # GL-CMD-SCENE-LANES-B1-188 V4: WHO/location/sky_state were written
        # only for autonomous attending (_atick_attending_visual/_audio via
        # _current_situation) -- never for converse, confirmed by -164's
        # audit ("presence tags... never for converse"). Same real, no-I/O
        # source, computed here so every converse turn writes a real WHO tag
        # too. Caller-supplied values (none exist today) still win.
        if presence is None and location is None and sky_state is None:
            presence, location, sky_state = self._current_situation()
        # GL-CMD-CONVERSE-PHASING-EMISSION-LOCK-52 §1.2: feature-flagged phased path.
        # CONVERSE_PHASED=1 → _converse_phased (split self.lock + self._emission_lock).
        # CONVERSE_PHASED=0 (default) → original single-lock body below.
        if os.environ.get("CONVERSE_PHASED", "0") == "1":
            return self._converse_phased(
                text, source, emission_mode, bundle_id,
                episode_ref, presence, location, sky_state, organ_candidates)

        # GL-CMD-CURRICULUM-LOCK-RELEASE-V2-46v2: §1.3 phasing deferred.
        # _emit_dynamics() writes to self._emission_system.sections (mode_bank,
        # psi, etc.) — concurrent access without a lock would corrupt these.
        # Retained original single-lock pattern. §1.1 (binding_window in
        # read_sentence) and §1.2 (network timeouts) are the active fixes.
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
            if source in ("joe", "joe_voice", "wc", "c1") and input_chis:
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
            if source in ("joe", "joe_voice", "wc", "c1"):
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
            reply = None
            if recalled and self._last_recalled_pictures:
                # Recall found pictures — keep the association
                pass  # pictures set on self._last_recalled_pictures
            # 6. Emit from the organism's recall/compose (GL-CMD-175 P3)
            self._last_converse_source = source  # for dynamics NMDA context
            if not reply:
                reply = self._emit_from_invariants(input_chis, words,
                                                    mode_override=emission_mode,
                                                    v7_session=getattr(self, '_v7_session', None),
                                                    organ_candidates=organ_candidates)
            _t_emit = time.monotonic()
            # GL-NOTE-VOICE-WIRING-RULING W3: the old unslotted-atlas-binding
            # fallback disconnects at cutover -- same "old gather" family as
            # the SVO-recall fallback it names explicitly. One mind, one
            # mouth: honest silence, never backfilled from atlas bindings.
            if not reply:
                reply = "..."

            # GL-CMD-TEACHER-CORRECTION-BINDING: track last conversation pair
            self._last_converse_input = text
            self._last_converse_reply = reply

            # GL-CMD-TEACHER-SUBSTRATE-TRUE: emission_id is substrate-derived fingerprint
            # GL-CMD-TURN-LATENCY-EVE-20260705-197 P3: reply words transduced
            # ONCE, shared with self_hear + the hemisphere-update block below.
            # (c1b's -197 commit applied P2/P3 to _converse_phased, the live
            # path; this fallback -- CONVERSE_PHASED=0 -- was the one gap
            # left, fixed here for consistency, same pattern.)
            self._last_converse_source = source
            reply_chis = []
            if reply and reply != "...":
                for ew in _normalize_text(reply):
                    ek = LanguageKrimelack()
                    ek.transduce(ew)
                    reply_chis.append(ek.winding)
                committed_chis = reply_chis
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
            _t_reply_ready = time.monotonic()

            # GL-CMD-TURN-LATENCY-EVE-20260705-197 P2: release the reply
            # before self-hear -- same background-continuation pattern as
            # _converse_phased (the live production path); mirrored here so
            # this fallback path (CONVERSE_PHASED=0) behaves identically.
            if source in ("joe", "joe_voice", "wc", "c1", "gate_test"):
                self._log_substrate_event("converse_reply_released",
                    reply_ready_ms=round((_t_reply_ready - _t_converse_start) * 1000, 1),
                    n_words=len(words))

            def _post_reply_continuation():
                _t_ph_start = time.monotonic()
                # v8 (GL-BRIEF-034): Self-hearing — read reply into substrate
                if reply and reply != "..." and source in ("joe", "joe_voice", "wc", "c1"):
                    self._self_hear(reply, source, reply_chis=reply_chis)
                _t_ph_selfhear = time.monotonic()
                # GL-CMD-COGNITION-BUNDLE: run hemisphere updates after emission
                try:
                    from dsf_ai_service.substrate.hemisphere_cognition import (
                        run_hemisphere_updates,
                    )
                    run_hemisphere_updates(
                        self, text, source, input_chis, reply,
                        reply_chis, self.tick)
                except Exception:
                    pass  # hemisphere failures must not break converse
                _t_ph_hemi = time.monotonic()
                if source in ("joe", "joe_voice", "wc", "c1", "gate_test"):
                    self._log_substrate_event("converse_timing",
                        chi_ms=round((_t_chi - _t_converse_start) * 1000, 1),
                        recall_ms=round((_t_recall - _t_chi) * 1000, 1),
                        read_ms=round((_t_read - _t_recall) * 1000, 1),
                        tag_ms=round((_t_tag - _t_read) * 1000, 1),
                        emit_ms=round((_t_emit - _t_tag) * 1000, 1),
                        selfhear_ms=round((_t_ph_selfhear - _t_ph_start) * 1000, 1),
                        hemi_ms=round((_t_ph_hemi - _t_ph_selfhear) * 1000, 1),
                        background_ms=round((_t_ph_hemi - _t_ph_start) * 1000, 1),
                        total_ms=round((_t_reply_ready - _t_converse_start) * 1000, 1),
                        n_words=len(words), released_before_selfhear=True)

            threading.Thread(target=_post_reply_continuation, daemon=True,
                             name="converse-posthear").start()
            return reply

    # ── GL-CMD-CONVERSE-PHASING-EMISSION-LOCK-52 §1.2 ──────────────────────────

    def _converse_phased(self, text, source, emission_mode, bundle_id,
                         episode_ref, presence, location, sky_state, organ_candidates):
        """Phased converse: splits self.lock and self._emission_lock to allow
        curriculum to interleave between phases.

        Phase 1: tokenize + chi transduction — NO lock
        Phase 2: open_response_window state write — brief self.lock
        Phase 3: _recall_response atlas reads — NO lock (race-tolerant)
        Phase 4: read_sentence input — per-word self.lock (via -46v2 §1.1)
        Phase 5: tag_response_bindings — brief self.lock
        Phase 6: _emit_from_invariants / _emit_dynamics — self._emission_lock
        Phase 7: engine state writes — brief self.lock
        Phase 8: _self_hear → read_sentence — per-word self.lock
        Phase 9: hemisphere updates — NO lock
        Phase 10: timing log — _log_substrate_event (internal sync)
        """
        _t0 = time.monotonic()
        self._last_converse_tick = self.tick
        self._last_dynamics_result = None

        # Phase 1: tokenize + chi transduction (no lock — pure local computation)
        parsed = self._parse_math(text)
        if parsed:
            op, a, b = parsed
            result = self._mathloom_solve(op, a, b)
            return self._num_to_word(result)

        words = _normalize_text(text)
        if not words:
            return "..."

        input_chis = []
        input_word_chis = {}
        for w in words:
            temp_krim = LanguageKrimelack()
            temp_krim.transduce(w)
            ch = temp_krim.winding
            input_chis.append(ch)
            input_word_chis[w] = ch
        _t_chi = time.monotonic()

        # Phase 2: open_response_window (brief self.lock — mutates open_response_windows)
        with self.lock:
            if source in ("joe", "joe_voice", "wc", "c1") and input_chis:
                self._open_response_window(source, input_chis,
                                           source_context={"text": text[:50]})

        # Phase 3: recall (no lock — reads atlas, race-tolerant)
        recalled = self._recall_response(input_chis, input_word_chis, words)
        _t_recall = time.monotonic()

        # Phase 4: read input (per-word self.lock internally via -46v2 §1.1)
        tick_before_read = self.tick
        self.read_sentence(text, source=source, bundle_id=bundle_id,
                           episode_ref=episode_ref, presence=presence,
                           location=location, sky_state=sky_state)
        tick_after_read = self.tick
        _t_read = time.monotonic()

        # Phase 5: tag response bindings (brief self.lock — mutates atlas entries)
        if source in ("joe", "joe_voice", "wc", "c1"):
            with self.lock:
                _bind_count = 0
                _bind_cap = 12
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

        # Phase 6: emission (self._emission_lock — serializes _emit_dynamics mutation
        # of _emission_system.sections; curriculum and /converse can interleave here
        # via self.lock, but only one thread enters _emit_dynamics at a time)
        _lock_wait_start = time.monotonic()
        with self._emission_lock:
            _lock_wait_ms = (time.monotonic() - _lock_wait_start) * 1000
            _emit_start = time.monotonic()
            self._last_converse_source = source  # for dynamics NMDA context
            reply = None
            if recalled and self._last_recalled_pictures:
                pass  # pictures set on self._last_recalled_pictures
            if not reply:
                reply = self._emit_from_invariants(input_chis, words,
                                                   mode_override=emission_mode,
                                                   v7_session=getattr(self, '_v7_session', None),
                                                   organ_candidates=organ_candidates)
            # GL-NOTE-VOICE-WIRING-RULING W3: the old unslotted-atlas-binding
            # fallback disconnects at cutover -- same "old gather" family as
            # the SVO-recall fallback it names explicitly.
            if not reply:
                # -48 Path D: clarification shape on high-surprise, low-coherence input
                # GL-CMD-175 P2 seam 2/6: organism consensus, not atlas chi.
                _input_surprise = max(
                    (self._recognition_from_organism(w) for w in words),
                    default=0.0) if words else 0.0
                if _input_surprise > SURPRISE_HIGH_THRESHOLD:
                    self._log_substrate_event("agency_clarification_shape",
                        surprise=round(_input_surprise, 3),
                        input_words=words[:5], source=source)
                    reply = "hm"  # minimal clarification signal
                else:
                    reply = "..."
            _emit_compute_ms = (time.monotonic() - _emit_start) * 1000
        _t_emit = time.monotonic()

        # §1.4: log emission_lock contention when above thresholds
        if _lock_wait_ms > 100 or _emit_compute_ms > 1500:
            try:
                self._log_substrate_event("converse_emission_lock",
                    wait_ms=round(_lock_wait_ms, 1),
                    compute_ms=round(_emit_compute_ms, 1),
                    source=source)
            except Exception:
                pass

        # Phase 7: engine state writes (brief self.lock — mutates _emission_records)
        # GL-CMD-TURN-LATENCY-EVE-20260705-197 P3: reply words transduced ONCE
        # here and shared with self_hear (Phase 8) and the hemisphere-update
        # block (Phase 9) below, instead of each re-running fresh
        # LanguageKrimelacks over the identical, deterministic reply text.
        with self.lock:
            self._last_converse_input = text
            self._last_converse_reply = reply
            self._last_converse_source = source
            reply_chis = []
            if reply and reply != "...":
                for ew in _normalize_text(reply):
                    ek = LanguageKrimelack()
                    ek.transduce(ew)
                    reply_chis.append(ek.winding)
                committed_chis = reply_chis
                first_chi = min(committed_chis) if committed_chis else 0
                n_committed = len(committed_chis)
                eid = f"{self.tick}_{first_chi}_{n_committed}"
                self._last_emission_id = eid
                rec = {"emission_id": eid, "text": reply, "tick": self.tick,
                       "input_text": text, "source": source,
                       "committed_chis": committed_chis}
                self._last_emission_record = rec
                self._emission_records[eid] = rec
                old_threshold = self.tick - EMISSION_RECORDS_TICK_WINDOW
                stale = [k for k, v in self._emission_records.items()
                         if v.get("tick", 0) < old_threshold]
                for k in stale:
                    del self._emission_records[k]
                if len(self._emission_records) > EMISSION_RECORDS_CAP:
                    oldest = sorted(self._emission_records,
                                    key=lambda k: self._emission_records[k].get("tick", 0))
                    for k in oldest[:len(self._emission_records) - EMISSION_RECORDS_CAP]:
                        del self._emission_records[k]
            else:
                self._last_emission_id = None
        _t_reply_ready = time.monotonic()

        # GL-CMD-TURN-LATENCY-EVE-20260705-197 P2: RELEASE THE REPLY BEFORE
        # SELF-HEAR. Phases 8 (self_hear) and 9 (hemisphere updates) used to
        # run before this function returned, gating Joe seeing her answer on
        # her hearing herself say it. They now run as a same-request
        # background continuation -- same pattern _self_hear's own step 4
        # (self-voice injection) already uses (a daemon thread, fire-and-
        # forget). Binding semantics preserved: same process, same tick
        # neighborhood -- the queue/lock machinery self_hear and
        # run_hemisphere_updates use is already safe from other background
        # writers (organism-writer, tapestry-writer, self-voice). The
        # SELF_HEARING_ENABLED kill switch is untouched (still checked
        # inside _self_hear itself).
        if source in ("joe", "joe_voice", "wc", "c1", "gate_test"):
            self._log_substrate_event("converse_reply_released",
                reply_ready_ms=round((_t_reply_ready - _t0) * 1000, 1),
                n_words=len(words))

        def _post_reply_continuation():
            _t_ph_start = time.monotonic()
            # Phase 8: self-hear (per-word self.lock internally)
            if reply and reply != "..." and source in ("joe", "joe_voice", "wc", "c1"):
                self._self_hear(reply, source, reply_chis=reply_chis)
            _t_ph_selfhear = time.monotonic()
            # Phase 9: hemisphere updates (no lock — separate state domain)
            try:
                from dsf_ai_service.substrate.hemisphere_cognition import run_hemisphere_updates
                run_hemisphere_updates(self, text, source, input_chis, reply,
                                       reply_chis, self.tick)
            except Exception:
                pass
            _t_ph_hemi = time.monotonic()
            # Phase 10: timing log -- total_ms is the FOREGROUND (perceived)
            # latency captured before backgrounding; selfhear_ms/hemi_ms/
            # background_ms are the deferred cost, visible but no longer
            # gating the reply.
            if source in ("joe", "joe_voice", "wc", "c1", "gate_test"):
                self._log_substrate_event("converse_timing",
                    chi_ms=round((_t_chi - _t0) * 1000, 1),
                    recall_ms=round((_t_recall - _t_chi) * 1000, 1),
                    read_ms=round((_t_read - _t_recall) * 1000, 1),
                    tag_ms=round((_t_tag - _t_read) * 1000, 1),
                    emit_ms=round((_t_emit - _t_tag) * 1000, 1),
                    selfhear_ms=round((_t_ph_selfhear - _t_ph_start) * 1000, 1),
                    hemi_ms=round((_t_ph_hemi - _t_ph_selfhear) * 1000, 1),
                    background_ms=round((_t_ph_hemi - _t_ph_start) * 1000, 1),
                    total_ms=round((_t_reply_ready - _t0) * 1000, 1),
                    n_words=len(words),
                    phased=True, released_before_selfhear=True)

        threading.Thread(target=_post_reply_continuation, daemon=True,
                         name="converse-posthear").start()
        return reply

    def _tapestry_worker_loop(self):
        """GL-CMD-175 P2 perf fix: single persistent background writer for
        tapestry exposure -- see _enqueue_tapestry_expose."""
        while True:
            item = self._tapestry_queue.get()
            if item is None:
                return
            word_a, word_b = item
            with self._tapestry_lock:
                for m in self.tapestry.mosaics:
                    m.expose(word_a, word_b)
                self.tapestry._tick += 2

    def _ensure_tapestry_worker(self):
        if self._tapestry_queue is not None:
            return
        with self._tapestry_worker_start_lock:
            if self._tapestry_queue is not None:  # lost a race to another thread
                return
            self._tapestry_queue = _queue.Queue(maxsize=2000)
            t = threading.Thread(target=self._tapestry_worker_loop,
                                 daemon=True, name="tapestry-writer")
            t.start()
            self._tapestry_worker_thread = t

    def _enqueue_tapestry_expose(self, word_a, word_b):
        """GL-CMD-175 P2 perf fix: profiled directly (cProfile, 3-word
        sample) at ~180ms/call -- LoomMosaic.expose's imaginary-time settle
        physics across 450 real neurons, the dominant cost of read_word by
        far (86% of its time). Backgrounded: single persistent worker +
        bounded queue, same convention as GL-CMD-172's diary writer (never
        one thread per word -- that risked its own thread-creation-
        overhead regression, the exact concern -172's design note already
        raised for a similar per-event pattern). Drops under sustained
        back-pressure (queue.Full) rather than blocking her live reading/
        converse path -- an honest degradation (some exposures lost under
        load), not a silent stall. self._tapestry_lock (held here and by
        compose()'s callers) keeps a concurrent read from observing a
        neuron mid-settle."""
        try:
            self._ensure_tapestry_worker()
            self._tapestry_queue.put_nowait((word_a, word_b))
        except _queue.Full:
            pass
        except Exception:
            pass

    def _organism_worker_loop(self):
        """GL-CMD-175 window-2 perf fix, upgraded per
        GL-CMD-BRAIN-GROWTH-UNFREEZE-EVE-20260704-179's backgrounding
        ruling: single persistent background writer, now calling
        organism.experience_word() (binding write + the real q-charge
        fold cascade) instead of bare organism.remember() -- see
        _enqueue_organism_remember. Computes _organism_signal() here too
        (not at the read_word call site) -- that computation (waveform
        generation) is itself real work, kept off the synchronous hot
        path along with the organism call.

        In-order processing (Eve's condition): a single worker thread
        pulling from one queue.Queue is FIFO by construction -- no
        extra logic needed, just never spin a second worker.

        task_done() (Eve's condition -- queue drained before
        save_full_state): required for queue.join() to mean anything;
        called in both the success and failure path so a raised
        exception can't wedge a future join() forever."""
        while True:
            item = self._organism_queue.get()
            if item is None:
                self._organism_queue.task_done()
                return
            # GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191 N1/N2: item is now
            # (word, sight_signal, sound_signal, modal_signal) -- the
            # sight/sound/modal snapshots taken at ENQUEUE time (inside
            # _enqueue_organism_remember, synchronously, cheap), not at
            # whatever moment the worker eventually processes this item
            # (which could be seconds later under backlog -- using a
            # signal fetched THEN would bind the word to the wrong
            # moment). modal_signal added by GL-CMD-EMULATOR-EVERYWHERE-
            # EVE-20260705-196 M2 (tactile/olfactory/gustatory, real
            # descriptor physics, same in-window snapshot discipline).
            word, sight_signal, sound_signal, modal_signal = item
            try:
                signal = _organism_signal_with_senses(
                    word, self._organism_transducer, sight_signal,
                    sound_signal, modal_signal)
                with self._organism_lock:
                    self.organism.experience_word(word, signal)
                # GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191 X1: "verifiable in
                # the event/atlas record" -- experience_word() itself logs
                # nothing (model-layer, no engine event stream access);
                # without this, a multi-sense binding was invisible to
                # anyone watching the live event log, same blind spot -187
                # fixed for the cognition meter. Logged here, not inside
                # the model layer, so this stays engine-side instrumentation
                # (Vehicle-appropriate) rather than a cognition change.
                # GL-CMD-EMULATOR-EVERYWHERE-196 S2: modal lane names added.
                _modal_present = (modal_signal or {})
                self._log_substrate_event(
                    "organism_experience_bound", word=word,
                    has_sight=sight_signal is not None,
                    has_sound=sound_signal is not None,
                    senses=[m for m, present in
                            (("sight", sight_signal is not None),
                             ("sound", sound_signal is not None),
                             ("tactile", _modal_present.get("tactile") is not None),
                             ("olfactory", _modal_present.get("olfactory") is not None),
                             ("gustatory", _modal_present.get("gustatory") is not None))
                            if present])
            except Exception as _oe:
                print(f"[GualaLoom] organism experience_word failed for "
                      f"{word!r} (non-fatal): {_oe}")
            finally:
                self._organism_queue.task_done()

    def _ensure_organism_worker(self):
        if self._organism_queue is not None:
            return
        with self._organism_worker_start_lock:
            if self._organism_queue is not None:  # lost a race to another thread
                return
            self._organism_queue = _queue.Queue(maxsize=2000)
            t = threading.Thread(target=self._organism_worker_loop,
                                 daemon=True, name="organism-writer")
            t.start()
            self._organism_worker_thread = t

    def _enqueue_organism_remember(self, word):
        """GL-CMD-175 window-2 perf fix: organism.remember() measured live-
        equivalent at 20ms/word and climbing at only ~280 accumulated
        words (population-vote architecture -- cost is O(population),
        population grows with her life). Backgrounded: single persistent
        worker + bounded queue, same convention as the tapestry writer and
        GL-CMD-172's diary writer.

        GL-CMD-BRAIN-GROWTH-UNFREEZE-EVE-20260704-179: the worker now
        calls organism.experience_word() (measured 22.3x organism.
        remember()'s own cost, see the -179 report) -- backgrounding it
        the same way is exactly what makes that cost safe to pay at all.
        Drops under sustained back-pressure (queue.Full) rather than
        blocking her live reading/converse path -- an honest degradation
        (some experience lost under load), not a silent stall -- and per
        Eve's ruling, that degradation is now COUNTED, not just
        swallowed (self._organism_dropped_count, surfaced in /status).
        self._organism_lock (held by the worker and by recall()/
        save_full_state() callers) keeps a concurrent read from
        observing the organism mid-update.

        GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191 N1/N2: snapshots whatever
        real sight/sound signal is still within SENSE_BINDING_WINDOW_SEC
        of THIS MOMENT (wall-clock, not tick -- see that constant's own
        comment) and carries it into the queue alongside the word, so the
        binding reflects what she was actually seeing/hearing when the
        word was read, not whatever's most recent by the time a
        backlogged worker gets to it.

        GL-CMD-EMULATOR-EVERYWHERE-EVE-20260705-196 M2: same snapshot
        discipline for _last_read_modal_signals (tactile/olfactory/
        gustatory, generated once per sentence in read_sentence from the
        sentence's own descriptor words -- see _sentence_modal_signals).
        Every intake path that calls read_sentence (curriculum, corpus
        READING, worldfeed, lookup, converse) shares this one snapshot
        point -- no per-path duplication needed."""
        now = time.time()
        sight_signal = None
        if (getattr(self, '_last_sight_wall_time', None) is not None
                and now - self._last_sight_wall_time <= SENSE_BINDING_WINDOW_SEC):
            sight_signal = self._last_sight_signal
        sound_signal = None
        if (getattr(self, '_last_sound_wall_time', None) is not None
                and now - self._last_sound_wall_time <= SENSE_BINDING_WINDOW_SEC):
            sound_signal = self._last_sound_signal
        modal_signal = None
        if (getattr(self, '_last_read_modal_wall_time', None) is not None
                and now - self._last_read_modal_wall_time <= SENSE_BINDING_WINDOW_SEC):
            modal_signal = self._last_read_modal_signals
        try:
            self._ensure_organism_worker()
            self._organism_queue.put_nowait(
                (word, sight_signal, sound_signal, modal_signal))
        except _queue.Full:
            self._organism_dropped_count += 1
        except Exception:
            pass

    def _brain_emission_candidates(self, input_words):
        """GL-CMD-BRAIN-FULL-DEPLOY-TODAY-175 P3 / GL-NOTE-VOICE-WIRING-
        RULING W2: the organism's own mind (tapestry recall/compose, built
        on -169's Embryo + real experience via read_word's tap) supplies
        emission candidates, replacing the deep-atlas co-occurrence gather.

        Query: the most salient real word available -- the current
        utterance's last word if present (converse), else the last word
        she's actually processed (autonomous emission has no input_words
        of its own).

        Candidates are translated into _emit_from_invariants' existing
        (de, co, clarity) shape via _word_to_emission_sections -- the
        existing reverse index of words that have themselves already
        committed to a mode in an emission section. This means only
        words the organism recalls AND that already have a real,
        committed home in a section can be said -- reusing committed
        reality, never inventing a new mode slot.

        Returns [] (honest empty, per W3) on any failure to produce a
        real candidate -- never partially substitutes the old gather."""
        query = (input_words[-1] if input_words else self._tapestry_prev_word)
        if not query:
            return []
        # GL-CMD-VOICE-ORGANISM-CANDIDATES-195: candidates come from the
        # organism's population-vote recall (Embryo.recall_fast) — the same
        # validated mechanism seams 1/3 (_recall_from_organism /
        # _association_from_organism) already use live, and the one the
        # memory spec grades as her working word memory (per-neuron
        # BindingAtlas x ring-position diversity, population vote).
        # The prior source, tapestry.compose's last_input_word decode, was
        # audit-proven a query echo chamber (2026-07-05): recall() writes
        # the query into every neuron's single word slot before decoding
        # it back. No per-word memory existed on that path at all. Retired
        # here as candidate source per W2's own principle: one mind, one
        # mouth — and the mind's real recall is the organism vote.
        try:
            with self._organism_lock:
                votes = self.organism.recall_fast(
                    _organism_signal(query, self._organism_transducer))
        except Exception as _oe:
            print(f"[GualaLoom] organism recall failed for query={query!r} "
                  f"(non-fatal, honest empty): {_oe}")
            return []
        if not votes:
            return []
        total = sum(votes.values())
        candidates = []
        n_with_section_home = 0
        for w, n_votes in votes.most_common(MAX_COMPOSITION_LEN):
            if not w or w.lower() == query.lower():
                continue  # association, not self-echo (seam-3 convention)
            locations = self._word_to_emission_sections.get(w.lower())
            if not locations:
                continue  # only words with a real committed section home
            n_with_section_home += 1
            section, mode_idx, _matched_word = locations[-1]  # most recent commit
            weight = (n_votes / total) if total else 0.0
            co = {section: {mode_idx: weight}}
            de = {"co_occurrence": co, "clarity": weight, "origin": "brain"}
            candidates.append((de, co, weight))
        # GL-CMD-VOICE-ORGANISM-CANDIDATES-195 P3 (c1 addition -- not in the
        # attached patch, added here to satisfy D2/X1's reporting need):
        # vote-spread visibility, the same blind spot -187 named for the
        # cognition meter. n_voted_words: distinct words the population
        # voted for at all. n_with_section_home: of the sampled top-K, how
        # many already have a committed section slot. n_candidates: final
        # count after also excluding self-echo.
        self._log_substrate_event("emission_diag",
                                  query=query,
                                  n_voted_words=len(votes),
                                  n_with_section_home=n_with_section_home,
                                  n_candidates=len(candidates))
        return candidates

    def _emit_from_invariants(self, input_chis, input_words, mode_override=None,
                              v7_session=None, organ_candidates=None):
        """Compose emission from the organism's recall/compose output.
        GL-CMD-175 P3 / GL-NOTE-VOICE-WIRING-RULING: candidates come from
        the brain (see _brain_emission_candidates), NOT the deep-atlas
        co-occurrence gather -- disconnected at cutover (W3). If the
        brain supplies nothing, this returns None (honest empty); no
        backfill from deep_atlas. organ_candidates kept as an accepted
        (now-unused) parameter -- its only real caller is the dead
        remote-mode substrate_runner.py path (not exercised in embedded
        production); removing the parameter isn't necessary for the
        cutover and keeps that dead call site from erroring outright.
        GL-BRIEF-GRANDURUN: branches on EMISSION_MODE (topk or grandurun),
        unchanged below this candidate-source swap.
        GL-CMD-DYNAMICS-EMISSION-RESTORATION: EMISSION_DYNAMICS=1 routes to
        two-stage path (grandurun candidates → assemblage dynamics settling).
        Phase 3b: v7_session provides context priors for grounded emission."""
        mode = mode_override or os.environ.get("EMISSION_MODE", "topk")
        input_words_set = set(w.lower() for w in input_words)

        deep_candidates = self._brain_emission_candidates(input_words)
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
        # GL-CMD-COMPOSER-MULTIANCHOR-43 §2.3: keep target_chi for vector path;
        # scalar path now uses multi-anchor (all input_chis).
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

        # GL-CMD-COMPOSER-MULTIANCHOR-43 §2.3: multi-anchor selection
        selected, coherent_sum = _grandurun_select_multichi(pool, input_chis)

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
                                  n_anchors=len(input_chis),
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

        # GL-CMD-COMPOSER-MULTIANCHOR-43 §2.4: multi-anchor target_state.
        # Average 7D state vectors over all input chis rather than using only input_chis[0].
        # Each input chi contributes equally to the reference field the candidates align with.
        if len(input_chis) <= 1:
            target_binding = {"chi": target_chi, "strength": 1.0,
                              "section": "", "target_section": "",
                              "source": target_source}
            target_state = _grandurun_state(
                target_binding, target_chi, target_source, needs_arr,
                current_tick, co_occurrence_dict=co_occurrence_dict)
        else:
            state_sum = _np.zeros(_SPIN_VECTOR_DIM, dtype=_np.complex128)
            for tc in input_chis:
                tb = {"chi": tc, "strength": 1.0,
                      "section": "", "target_section": "", "source": target_source}
                state_sum += _grandurun_state(tb, tc, target_source, needs_arr,
                                              current_tick, co_occurrence_dict=co_occurrence_dict)
            target_state = state_sum / len(input_chis)

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
                        # GL-CMD-SCENE-LANES-B1-188 V4: reader -- these were
                        # write-only on the atlas entry (-164's audit finding)
                        # until recall actually surfaced them here.
                        "presence": e.get("presence"),
                        "location": e.get("location"),
                        "place": e.get("place"),
                        "ambient": e.get("ambient"),
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
                            "presence": de.get("presence"),
                            "location": de.get("location"),
                            "place": de.get("place"),
                            "ambient": de.get("ambient"),
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
                        "presence": e.get("presence"),
                        "location": e.get("location"),
                        "place": e.get("place"),
                        "ambient": e.get("ambient"),
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

        # GL-CMD-C1-POLARITY: apply polarity alignment penalty before sort.
        # Query polarity = current negation state (odd flips pending → -1).
        # Mismatch reduces coherent_magnitude by POLARITY_PENALTY=0.3 (multiplicative).
        # Candidates with polarity=0 (ambiguous) are neutral.
        _POLARITY_PENALTY = 0.3
        # 60-L: query polarity from phase rotation (replaces _negation_pending)
        _query_polarity = -1 if getattr(self, '_last_rotation', 0.0) > (math.pi / 2) else 1
        _polarity_mixed = False
        for cand in all_candidates:
            cand_pol = cand.get("polarity", 1)
            if cand_pol == 0:
                continue  # ambiguous — neutral
            if cand_pol != _query_polarity:
                cand["coherent_magnitude"] *= (1.0 - _POLARITY_PENALTY)
                _polarity_mixed = True
        if _polarity_mixed:
            self._log_substrate_event("polarity_alignment",
                                      query_polarity=_query_polarity,
                                      penalty=_POLARITY_PENALTY)

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

        # -48 Path A: backtracking — remove candidates with chi too far from input centroid
        if candidates and input_chis:
            _centroid = sum(input_chis) / len(input_chis)
            _chi_radius = getattr(self.atlas, 'band', 2) * BACKTRACK_CHI_RADIUS_MULT
            for _bt in range(3):
                if not candidates:
                    break
                _top = candidates[0]
                if abs(_top["chi"] - _centroid) > _chi_radius:
                    self._log_substrate_event("agency_backtrack",
                        motif_id=_top.get("motif"), chi=_top.get("chi"),
                        centroid=round(_centroid, 1), radius=_chi_radius,
                        word=_top.get("word"), attempt=_bt + 1)
                    candidates = candidates[1:]
                else:
                    break

        # -48 Path B: conflict resolution — detect raw tie before gp-bias resolves it
        _raw_tie = False
        if len(candidates) >= 2:
            _s0 = candidates[0]["coherent_magnitude"]
            _s1 = candidates[1]["coherent_magnitude"]
            if _s0 > 0 and abs(_s0 - _s1) / _s0 < 0.05:
                _raw_tie = True

        # -48 Path C: cross-modal fallback — promote from deep atlas when live gives nothing
        if not candidates and deep_candidates:
            self._log_substrate_event("agency_cross_modal_fallback",
                input_chis=input_chis[:5], n_deep=len(deep_candidates))
            _best_de, _best_co, _best_clarity = max(deep_candidates, key=lambda x: x[2])
            for _sec_name, _co_sec in _best_co.items():
                if _sec_name not in self._EMISSION_SECTIONS or not _co_sec:
                    continue
                _best_mid_str = max(_co_sec, key=_co_sec.get)
                _mid = int(_best_mid_str)
                _sec = self.sections.get(_sec_name)
                if _sec and _mid < len(_sec.modes):
                    _, _, _word = _sec.modes[_mid]
                    if _word:
                        candidates.append({
                            "chi": _best_de.get("chi", 0),
                            "section": _sec_name, "motif": _mid, "word": _word,
                            "strength": float(_co_sec[_best_mid_str]),
                            "coherent_magnitude": _best_clarity,
                            "source": _best_de.get("source", "corpus"),
                            "arousal": _best_de.get("arousal", 0.5),
                            "valence": _best_de.get("valence", 0.0),
                            "polarity": _best_de.get("polarity", 1.0),
                            "sensory_refs": _best_de.get("sensory_refs", []),
                            "origin": "cross_modal_fallback",
                        })
                        break

        # gp-bias: multiply coherent_magnitude by chi-proximity to dominant-need goal seed
        _gp_bias_applied = False
        _gp_hemi = getattr(self, 'hemispheres', {}).get('gp') if candidates else None
        if _gp_hemi is not None:
            _ns = self.needs.snapshot()
            # Dominant need = whichever is furthest from its target (0.7)
            _dominant = max(('stability', 'novelty', 'connection'),
                            key=lambda n: abs(_ns.get(n, 0.5) - 0.7))
            _need_to_label = {'stability': 'be_present',
                              'novelty': 'form_sensory_bindings',
                              'connection': 'respond_to_joe'}
            _goal_chi = None
            for _chi_k, _ges in _gp_hemi.atlas.entries.items():
                for _ge in _ges:
                    if _ge.get('label') == _need_to_label.get(_dominant):
                        _goal_chi = int(_chi_k)
                        break
                if _goal_chi is not None:
                    break
            if _goal_chi is not None:
                _chi_band = getattr(self.atlas, 'band', 2)
                for _c in candidates:
                    _dist = abs(_c['chi'] - _goal_chi)
                    _bias = 1.0 + 0.5 * max(0.0, 1.0 - _dist / (_chi_band * 3))
                    _c['coherent_magnitude'] = _c['coherent_magnitude'] * _bias
                    _c['gp_bias'] = round(_bias, 4)
                candidates.sort(key=lambda c: -c['coherent_magnitude'])
                _gp_bias_applied = True

        # Path B resolution: log tie (now resolved by gp-bias if applied)
        if _raw_tie and len(candidates) >= 2:
            self._log_substrate_event("agency_conflict_tie",
                cand_a=candidates[0].get("word"),
                cand_b=candidates[1].get("word"),
                score_a=round(candidates[0]["coherent_magnitude"], 4),
                score_b=round(candidates[1]["coherent_magnitude"], 4),
                resolution="gp_bias" if _gp_bias_applied else "first",
                gp_bias_applied=_gp_bias_applied)

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
        # source_match: fires when pair-bond candidates present and input is from pair-bond source
        # GL-CMD-NMDA-SOURCE-MATCH-75: text converse sets source="joe"/"wc"/"c1";
        # speech transcription sets "joe_voice". All four are pair-bond sources.
        # Prior code checked only "joe_voice" — always False for typed input.
        joe_candidates_present = any(
            c["source"] in ("joe", "joe_voice", "wc", "c1")
            for c in candidates
        )

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
        # GL-FIX-CONVERSE-LATENCY: reduce from 5s → 1.5s so /converse Phase 6
        # (_emission_lock) + autonomy emission (_emission_lock) combined stay under 3s.
        _WALL_BUDGET_S = float(os.environ.get("EMISSION_WALL_BUDGET_S", "1.5"))
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
                                     coordinator_on=True)

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
                                  source_counts=source_counts,
                                  polarity_mixed=any(
                                      c.get("polarity", 1) != 1
                                      for c in emit_commits),
                                  organ_in_commits=any(
                                      c.get("origin") == "organ"
                                      for c in emit_commits),
                                  gp_bias_applied=_gp_bias_applied)
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
            "organ_in_commits": any(c.get("origin") == "organ" for c in emit_commits),
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

    def _recall_from_organism(self, input_words):
        """GL-CMD-BRAIN-FULL-DEPLOY-175 P2, seam 1/6 (recall): the organism's
        own population-vote recall (Embryo.recall, GL-CMD-169), built on
        real experience via read_word's P1 language tap -- replacing the
        atlas-dict-substrate lookup (_recall_from_atlas).

        The shell's per-section (subject/verb/object/listen) structure has
        no organism analog: Embryo.recall is a single population vote
        across the whole organism, not a grammatical-role lookup. Rather
        than force a fake per-section split, this queries the organism
        ONCE per call and returns its single top-voted concept -- an
        honest architectural difference, not a simulated seam pretending
        to have section structure it doesn't.

        Query word: the last content word (len>1), matching
        _brain_emission_candidates' established convention -- same
        "most salient real word" choice, so the brain interface is
        consistent across recall and emission. Returns None (no minimum-
        evidence padding, no invented candidate) if there's no content
        word or the organism's vote is empty."""
        content_words = [w for w in (input_words or []) if len(w) > 1]
        if not content_words:
            return None
        query = content_words[-1]
        # GL-CMD-175 P2 fix: multi-modal query signal, matching what was
        # actually written at remember()-time (see _organism_signal).
        # self._organism_lock: see read_count's salience calc comment.
        with self._organism_lock:
            votes = self.organism.recall_fast(_organism_signal(query, self._organism_transducer))
        top = votes.most_common(1)
        return top[0][0] if top else None

    def _association_from_organism(self, seed_word):
        """GL-CMD-BRAIN-FULL-DEPLOY-175 P2 seam 3/6 (association): "what
        goes with this word" via the organism's own recall, replacing
        _daydream_tick's deep_atlas.entries[chi].co_occurrence walk.

        Query the organism for seed_word; if it recalls something OTHER
        than the seed itself (an association, not a self-echo) AND that
        associated word already has a real committed section slot (same
        _word_to_emission_sections reuse as _brain_emission_candidates/
        seam 1), return (section, mode_idx, word, weight) -- weight is
        the population-vote consensus for the associated word (same
        measure seam 2's recognition uses), standing in for deep_atlas's
        co_occurrence strength. Returns None on no association, no
        section slot, or self-echo -- honest empty, not padded.

        Scope: this replaces ONLY the "near" associative surfacing
        (_daydream_tick's main co_occurrence walk). The novel-jump
        (Extension A, a deliberately random far-chi exploration) and
        consolidation (Extension C, deep_atlas's own invariant
        maintenance) are untouched -- neither is really "association,"
        and expanding scope to them wasn't part of this seam."""
        if not seed_word:
            return None
        associated_word = self._recall_from_organism([seed_word])
        if not associated_word or associated_word.lower() == seed_word.lower():
            return None
        locations = self._word_to_emission_sections.get(associated_word.lower())
        if not locations:
            return None
        section, mode_idx, word = locations[-1]
        with self._organism_lock:
            votes = self.organism.recall_fast(_organism_signal(seed_word, self._organism_transducer))
        total = sum(votes.values())
        weight = (votes.get(associated_word, 0) / total) if total else 0.0
        return (section, mode_idx, word, weight)

    def _recall_response(self, input_chis, input_word_chis, input_words,
                          target_sections=("subject", "verb", "object", "listen")):
        """GL-CMD-BRAIN-FULL-DEPLOY-175 P2 seam 1/6: text recall now comes
        from the organism (_recall_from_organism), not the atlas-dict
        per-section lookup -- old shell path (_recall_from_atlas's SVO/
        listen loop, the response-linked-entries expansion) disconnected,
        per "old shell paths disconnected from those decisions." Picture
        recall (_recall_sight_from_atlas) is UNCHANGED -- no vision tap
        exists yet (P1 only wired the language sense), so cross-modal
        picture recall honestly stays on the old path until a real visual
        tap is built; noted, not silently left ambiguous.

        target_sections kept as a parameter for signature compatibility
        (tools/guala_recall_bitexact_replay.py calls this with
        target_sections=... explicitly) but no longer consulted --
        the organism has no section structure to select from."""
        recalled_text = self._recall_from_organism(input_words)

        # v7 Phase 2: recall sight motifs via chi-neighborhood (unchanged)
        recalled_pictures = self._recall_sight_from_atlas(input_chis, input_words)

        if not recalled_text and not recalled_pictures:
            self._last_recalled_pictures = []  # GL-CMD-155: don't leak a stale hit
            return None

        if recalled_pictures:
            self._last_recalled_pictures = recalled_pictures
            return recalled_text  # even None — caller will check _last_recalled_pictures
        self._last_recalled_pictures = []
        return recalled_text

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

        # Step 1: find chi addresses where input words committed.
        # 60-C: hardcoded function_words removed — all words contribute chi addresses.
        content_chis = set()
        content = [w for w in input_words_lower if len(w) > 1]
        if not content:
            return []

        # GL-CMD-RECALL-WORD-INDEX-57 §1.6/§1.7: O(content_words) index lookup
        for w in content:
            content_chis.update(self._word_to_chi_index.get(w, ()))

        if not content_chis:
            return []

        # Step 2: find sight motifs bound at those chi addresses (with band +-2)
        # §1.8: direct neighborhood lookup — O(content_chis × 5) instead of O(N×M)
        sight_motif_ids = set()
        for target_chi in content_chis:
            for d in range(-2, 3):
                for e in self.atlas.entries.get(target_chi + d, []):
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

        # 60-C: all words go in — function_score on bindings downweights function words.
        # Hardcoded function_words list removed; substrate-derived score handles it.
        content_words = [w.lower() for w in input_words if len(w) > 1]
        if not content_words:
            return None

        # Step 1: GL-CMD-RECALL-WORD-INDEX-57 §1.5: O(content_words) index lookup
        content_word_chis = set()
        for w in content_words:
            content_word_chis.update(self._word_to_chi_index.get(w, ()))

        if not content_word_chis:
            return None

        # Step 2: At those chi locations, find target_section motifs.
        # 60-C: weight by (1 - function_score) so content bindings rank higher.
        candidates = Counter()
        for chi_k in content_word_chis:
            for e in self.atlas.entries.get(chi_k, []):
                if e["section"] == target_section:
                    if e["motif"] < len(sec.modes):
                        _, _, motif_word = sec.modes[e["motif"]]
                        if motif_word and motif_word.lower() not in exclude_words:
                            weight = 1.0 - e.get("function_score", 0.0)
                            candidates[e["motif"]] += weight

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
        # Critical events also go to disk for replay recovery — background thread
        # to avoid EFS write latency blocking the caller (inside self.lock).
        if event_kind in ("activity_started", "activity_ended", "corpus_completed",
                          "sleep_manual", "dream_began", "dream_artifact",
                          "picture_uploaded", "sound_uploaded", "video_uploaded",
                          "corpus_added", "visual_motif_committed", "visual_motif_fired",
                          "emission"):
            try:
                _ek, _det = event_kind, dict(detail)
                import threading as _t
                _t.Thread(target=lambda: self.log_event("state", _ek, **_det),
                          daemon=True, name=f"ev-log-{event_kind[:8]}").start()
            except Exception:
                pass
        # GL-CMD-EVENT-RETENTION-FIX-172 R3: EVERY event kind also goes to
        # the durable diary — not gated by the 12-kind whitelist above,
        # which stays governing ONLY the crash-replay log + CloudWatch
        # mirror. Non-blocking (single queue put, see enqueue_diary_event).
        self.enqueue_diary_event(
            "state", event_kind, detail, self.tick,
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        return ev

    # ── GL-CMD-DAYDREAM-PARALLEL-42: background associative activation ──────

    def start_daydream_loop(self):
        """Parallel chi-neighborhood walk. Runs alongside all foreground activity.
        Does NOT trigger commit gate or emission. 0.5s interval (2 Hz)."""
        if getattr(self, '_daydream_thread', None) is not None:
            return
        self._daydream_running = True

        def _loop():
            while self._daydream_running:
                try:
                    self._daydream_tick()
                except Exception:
                    pass
                time.sleep(0.5)

        self._daydream_thread = threading.Thread(target=_loop, daemon=True,
                                                  name="daydream-loop")
        self._daydream_thread.start()

    def _daydream_tick(self):
        """One pass of parallel associative surfacing.

        GL-CMD-EMISSION-PERF-45 §2.3: three-phase lock pattern.
        Phase 1 (lock): snapshot substrate state (recent_chis/words, needs,
          tick, band, atlas chi keys).
        Phase 2 (no lock): GL-CMD-175 P2 seam 3/6 -- the "near" association
          now comes from the organism (_association_from_organism), not
          deep_atlas.entries[chi].co_occurrence. Novel-jump candidate
          selection (Extension A) untouched -- deliberately random
          exploration, not really "association." Lock held fraction: <5%.
        Phase 3 (lock): atlas.record() writes + log events + consolidation
          (Extension C, untouched -- deep_atlas's own invariant upkeep).

        Honesty note: the old affect-weighting (Extension B) read the
        SPECIFIC deep_atlas entry's own recorded valence/arousal (from
        whenever that association was originally learned). The organism
        has no per-binding affect record, so this now reflects only her
        CURRENT needs state (still real, just a different, coarser
        signal than before) -- not fabricated, but changed; named here."""
        import random as _random

        # ── Phase 1: snapshot under lock ──────────────────────────────────────
        with self.lock:
            recent_chis = []
            recent_words = []
            for sec in self.sections.values():
                for c in sec.commits[-10:]:
                    recent_chis.append(c["chi"])
                    recent_words.append(c.get("word", ""))
            if not recent_chis:
                return
            snap_tick = self.tick
            snap_band = self.atlas.band
            snap_arousal = self.needs.arousal()
            snap_valence = self.needs.valence()
            _idx = snap_tick % len(recent_chis)
            seed_chi = recent_chis[_idx]
            seed_word = recent_words[_idx]
            # Snapshot atlas chi keys for novel jump (just the keys, not entries)
            atlas_chi_keys = list(self.atlas.entries.keys())

        # ── Phase 2: organism association query + novel-jump (no lock) ────────
        assoc = self._association_from_organism(seed_word)
        if assoc is None:
            return
        top_sec, top_mid, assoc_word, consensus = assoc
        ek = LanguageKrimelack()
        ek.transduce(assoc_word)
        top_chi = ek.winding
        # Extension B, adapted: no per-binding affect record from the
        # organism (see docstring) -- toward-baseline bias driven by her
        # CURRENT needs state only.
        v_after = snap_valence * 0.5
        a_after = (snap_arousal + 0.5) * 0.5
        affect_bias = max(0.1, 1.0 - abs(v_after) * 0.5 - abs(a_after - 0.5) * 0.5)
        top_w = consensus * affect_bias

        # Extension A: novel-jump candidate selection (no lock needed for deep_atlas reads)
        far_write = None  # (far_sec, far_mid_id, far_chi, far_w)
        if _random.random() < 1.0 / max(2, snap_band):
            min_dist = 5 * snap_band
            far_candidates = [c for c in atlas_chi_keys if abs(c - seed_chi) >= min_dist]
            if far_candidates:
                far_chi = far_candidates[snap_tick % len(far_candidates)]
                for de in self.deep_atlas.entries.get(far_chi, []):  # deep_atlas reads are safe
                    co = de.get("co_occurrence", {})
                    if not co:
                        continue
                    far_w = 0.0
                    far_sec = far_mid_id = None
                    for sec_name, motif_dict in co.items():
                        if motif_dict:
                            mid_str = max(motif_dict, key=motif_dict.get)
                            if motif_dict[mid_str] > far_w:
                                far_w = motif_dict[mid_str]
                                far_sec = sec_name
                                far_mid_id = int(mid_str)
                    if far_sec is not None:
                        far_write = (far_sec, far_mid_id, far_chi, far_w)
                    break

        # Extension C: consolidation flag (no lock for read)
        do_consolidate = (snap_tick % max(1, snap_band * 10) == 0)

        # ── Phase 3: writes + log events under lock ────────────────────────────
        with self.lock:
            # Resolve word labels (need self.sections, must be under lock for consistency)
            word_label = ""
            if top_sec in self.sections:
                sec_obj = self.sections[top_sec]
                if top_mid < len(sec_obj.modes):
                    _, _, word_label = sec_obj.modes[top_mid]

            self._atlas_record(
                section_name=top_sec, motif_id=top_mid, chi_value=top_chi,
                tick=snap_tick, salience=top_w, dwell_ticks=1,
                arousal=snap_arousal * 0.3, valence=snap_valence * 0.3,
                surprise=0.0, source="daydream",
            )
            if word_label:
                self._log_substrate_event("daydream_surface",
                    seed_chi=seed_chi, surfaced_chi=top_chi,
                    section=top_sec, word=word_label,
                    strength=round(top_w, 3))

            if far_write is not None:
                far_sec, far_mid_id, far_chi, far_w = far_write
                self._atlas_record(
                    section_name=far_sec, motif_id=far_mid_id, chi_value=far_chi,
                    tick=snap_tick, salience=far_w, dwell_ticks=1,
                    arousal=snap_arousal * 0.3, valence=snap_valence * 0.3,
                    surprise=0.5, source="daydream",
                )
                if far_sec in self.sections and far_mid_id < len(self.sections[far_sec].modes):
                    _, _, far_label = self.sections[far_sec].modes[far_mid_id]
                    self._log_substrate_event("daydream_novel",
                        seed_chi=seed_chi, far_chi=far_chi,
                        near_word=word_label, far_word=far_label,
                        far_strength=round(far_w, 3))

            if do_consolidate:
                for de in self.deep_atlas.entries.get(top_chi, []):
                    if de.get("section") == top_sec and de.get("motif") == top_mid:
                        self.deep_atlas._update_invariant(de, top_chi, self.atlas)
                        self._log_substrate_event("daydream_consolidate",
                            chi=top_chi, section=top_sec, motif=top_mid)
                        break

    def add_corpus(self, corpus_id, title, lines):
        """Register a corpus for autonomous reading."""
        self._corpora[corpus_id] = _Corpus(
            corpus_id=corpus_id, title=title, lines=lines)

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
        # GL-CMD-AUTONOMY-EMITTING-PHASING-53 §1.1: env-var gate.
        # AUTONOMY_PHASED=1 → _autonomy_tick_phased() which releases self.lock
        # during EMITTING activity compute (uses self._emission_lock instead).
        # AUTONOMY_PHASED=0 (default) → original single-lock body unchanged.
        if os.environ.get("AUTONOMY_PHASED", "0") == "1":
            self._autonomy_tick_phased()
            return
        with self.lock:
            # GL-CMD-AGITATION-FIX-JOE-20260704: compute activity kind once,
            # early -- shared by the needs-drift gate below and dream_
            # pressure's own gate (Change 2) further down.
            _ca_kind = getattr(self._current_activity, 'kind', None)

            # 1. Needs drift AWAY from target (once per iteration) -- paused
            # during SLEEPING/DREAMING (Change A: reuses dream_pressure's own
            # sleep-gate, GL-CMD-CREDO-LOOP-REPAIR-167 Change 2). She cannot
            # act on the drive tick_drift exists to create while
            # unconscious; letting it keep eroding needs anyway -- connection
            # especially, since nothing else replenishes it asleep -- is what
            # pinned arousal at 1.0 during tonight's sleep cycles (GL-RPT-
            # AGITATION-FIX-C1-20260704-v1). coordinator.regulate()'s real-
            # signal path (a few lines below, runs every 5 ticks regardless
            # of activity) is untouched, so genuine contact/new bindings can
            # still move her while asleep.
            if _ca_kind not in (None, "SLEEPING", "DREAMING"):
                self.needs.tick_drift()

            # Periodic needs snapshot to disk (every 500 ticks) — background thread
            # to avoid EFS write latency inside self.lock
            if self.tick % 500 == 0 and self.tick > 0:
                try:
                    ns = self.needs.snapshot()
                    _ns = dict(ns)
                    import threading as _t
                    _t.Thread(target=lambda: self.log_event(
                        "state", "needs_snapshot",
                        stability=_ns["stability"], novelty=_ns["novelty"],
                        connection=_ns["connection"], valence=_ns["valence"],
                        arousal=_ns["arousal"]),
                        daemon=True, name="needs-log").start()
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

            # GL-CMD-CREDO-LOOP-REPAIR-167 Change 2: dream_pressure accumulates
            # from unjudged backlog -- real substrate load since the last
            # EXECUTED dream tick (_dream_executed_this_cycle / Change 4) --
            # not a flat wall-clock rate (GL-CMD-SLEEP-RATE-68's a00b36f,
            # 2026-07-01, was a reverse-engineered rate constant; see GL-RPT-
            # SLEEP-BACKTEST-C1-20260704-167-v1's Q2-c verdict). Two signals
            # (Eve's Q2 ruling): working-atlas writes and attendance ticks.
            # Writes use self._atlas_write_count (a cheap O(1) counter bumped
            # in _atlas_record, NOT self.read_count -- that property is an
            # O(atlas_size) scan documented as "acceptable for /status
            # cadence (~1s)"; calling it here, 5x/sec, would add a real cost
            # to the exact loop GL-RPT-REPLY-LATENCY-PROFILE-C1-20260704-v1
            # was just investigating for slowness. Caught during
            # implementation, not assumed from the backtest's naming.
            _write_delta = max(0, getattr(self, '_atlas_write_count', 0)
                                  - getattr(self, '_dp_last_write_count', 0))
            self._dp_last_write_count = getattr(self, '_atlas_write_count', 0)

            # _ca_kind already computed above (GL-CMD-AGITATION-FIX-JOE-20260704)
            if _ca_kind not in (None, "SLEEPING", "DREAMING"):
                _attending = _ca_kind in ("READING", "ATTENDING",
                                          "ATTENDING_VISUAL",
                                          "ATTENDING_AUDIO",
                                          "ATTENDING_VIDEO")
                _pair_bond_active = any(
                    self.coordinator._presence.get(s, False)
                    and self.coordinator._pair_bond.get(s, False)
                    for s in PAIR_BOND_SOURCES
                )

                _dp_rate = (_write_delta * DP_RATE_PER_READ
                            + (DP_RATE_PER_ATTEND_TICK if _attending else 0.0)) * DP_RATE_MULTIPLIER
                if _pair_bond_active:
                    _dp_rate *= 0.3  # push-through: actively interacting perceives less backlog growth

                self.needs.dream_pressure = min(1.0, self.needs.dream_pressure + _dp_rate)

                # GL-CMD-SLEEP-RATE-68 (retained): periodic pressure telemetry (~every 10 min)
                if self.tick % 3000 == 0:
                    self._log_substrate_event(
                        "dream_pressure_check",
                        dp=round(self.needs.dream_pressure, 4),
                        dp_rate=round(_dp_rate, 8),
                        write_delta=_write_delta,
                        activity=_ca_kind,
                        pair_bond=_pair_bond_active,
                        attending=_attending,
                    )

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
                # DAYDREAMING removed (-42): now a background thread, not an activity
                elif a.kind == "REST":           # GL-CMD-C4-SLEEP-CHOICE
                    self._atick_rest(a)
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
        # GL-CMD-DAYDREAM-PARALLEL-42: DAYDREAMING removed from scheduler (now background thread)
        # GL-CMD-REST-RETIRE-73: REST removed. IDLE remains as the low-engagement waking option.
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

    # GL-CMD-BEHAVIOR-REPERTOIRE-EVE-20260705-185 B2: same reference scale
    # _Corpus.is_new() already uses for "not recently read" -- reused, not
    # a new invented constant. The one dial: how fast disuse recovers
    # freshness.
    RECENCY_RECOVERY_TICKS = 50_000

    @staticmethod
    def _habituation_freshness(times_seen, ticks_since_last=None):
        """GL-CMD-CREDO-LOOP-REPAIR-167 Change 1: continuous habituation
        decay, same curve for EVERY target-based activity kind — no kind
        gets a needs-independent exception. times_seen=0 -> 1.0 (fully
        fresh); decays as 1/(1+ln(1+times_seen)). This is -107's own
        ATTENDING_VISUAL-only curve (GL-BRIEF-graded-exogenous-salience-
        wC-20260610-031's biological argument: orienting response decays
        continuously, not as a binary cliff), now applied symmetrically.

        GL-CMD-BEHAVIOR-REPERTOIRE-EVE-20260705-185 B2: root-caused why
        audio/rest/other kinds structurally can never win once any target
        accumulates heavy historical exposure (e.g. smoke-test sounds
        attended 300-2000+ times each early on) -- times_seen only ever
        grows, so this curve alone can never recover; a kind over-exposed
        once is locked out of competing forever, regardless of how much
        real time has since passed with zero further exposure. That is
        exactly the "orienting response decays continuously" biological
        argument this function's OWN docstring already cites -- disuse is
        supposed to let habituation fade, and nothing here modeled disuse
        at all. ticks_since_last (optional, backward compatible -- None
        preserves the exact old behavior for any caller not yet passing
        it) blends the static exposure-decay floor toward fully-fresh
        (1.0) as elapsed time since last exposure grows, saturating
        smoothly (never a cliff, same continuous-decay principle as the
        base curve) rather than a hard reset."""
        base = 1.0 / (1.0 + math.log(1.0 + max(0, times_seen)))
        if not ticks_since_last or ticks_since_last <= 0:
            return base
        recovery = 1.0 - math.exp(-ticks_since_last / Guala.RECENCY_RECOVERY_TICKS)
        return base + (1.0 - base) * recovery

    def _reading_freshness_from_organism(self, corpus):
        """GL-CMD-BRAIN-FULL-DEPLOY-175 P2 seam 4/6 (habituation, READING
        only): a real organism-derived freshness signal, replacing
        _habituation_freshness(times_read_through) for corpus re-reading.
        Samples real words from the corpus's own text (read_word actually
        feeds this content through the organism, repeatedly, on each real
        read) and averages the organism's own recognition/surprise (seam
        2) across them -- same [0,1] convention as _habituation_freshness
        (1.0 = fully fresh/novel). Returns None if the corpus has no
        real text to sample (an edge case, not "no organism signal").

        Scope, stated honestly: ATTENDING_VISUAL/AUDIO/VIDEO habituation
        is NOT handed over by this seam. Pictures/sounds/videos have no
        real organism sensory connection -- P1 only wired language.
        Feeding the organism a picture's TITLE as a stand-in for having
        seen it would be feeding it something she never actually
        perceived -- exactly the simulated-seam this track's standing
        order prohibits. Those three stay on the old times_attended
        counters until a real visual/audio tap exists; not silently left
        ambiguous, just out of what a language-only organism can honestly
        answer for.

        Inherited risk, named plainly: seam 3 found the organism's
        recognition can be confidently WRONG about genuinely novel
        content (no reject option in the underlying recall). The same
        risk applies here -- a corpus she's never read could, in
        principle, sample words that happen to read as familiar.
        Not fixed here; same open question as seam 3's report."""
        words = []
        for line in corpus.lines[:5]:
            words.extend(w for w in line.lower().split() if len(w) > 1)
        if not words:
            return None
        # GL-CMD-175 window-2 recall-frequency reduction: organism.recall()
        # is O(population), confirmed the dominant live cost. 3 real,
        # freshly-computed samples instead of 10 -- an honest, coarser
        # average (real signal, less of it), not a cached/stale one; this
        # call site has no interleaved remember() between its own recall()
        # calls, so the reduction is purely about call count, same
        # reasoning as read_word's recognition-frequency reduction above.
        sample = words[:3]
        surprises = [self._recognition_from_organism(w) for w in sample]
        return sum(surprises) / len(surprises)

    def _action_salience(self, kind, target):
        """How attractive is this activity given current needs?
        Salience = dot product of (need-distance) × (payoff per need).
        Mirrored from wC's autonomy substrate model.
        GL-CMD-CREDO-LOOP-REPAIR-167 Change 1: habituation (which SPECIFIC
        target looks fresh) and need-satisfaction (whether to seek that
        kind of experience AT ALL) are two different questions. Every
        target-based kind answers the first the same way (_habituation_
        freshness, blended continuously into nov_payoff) and is then
        scored ONLY by the same signed-distance formula everyone else
        uses — no kind returns early with a floor (max(x, needs_score))
        that lets it out-bid the whole needs system, including sleep,
        regardless of how satisfied she already is. -107's ATTENDING_
        VISUAL-only exception is retired; its own curve is what's now
        shared by everyone."""
        sd = self.needs.signed_distance()

        # Habituation-decayed novelty payoff: continuous interpolation
        # between each kind's own NEW and REPEAT/REREAD payoff, keyed by
        # how fresh THIS SPECIFIC target still is. Symmetric across every
        # target-based kind — no exceptions.
        _habituation_eligible = False
        if kind == "READING" and target in self._corpora:
            _habituation_eligible = True
            c = self._corpora[target]
            # GL-CMD-175 P2 seam 4/6: organism-derived freshness, replacing
            # the times_read_through counter for this kind only (see
            # _reading_freshness_from_organism for ATTENDING_*'s scope
            # limit). None only for a corpus with no real text to sample
            # -- a data-availability edge case, not "old shell fallback".
            fresh = self._reading_freshness_from_organism(c)
            if fresh is None:
                fresh = 0.5  # neutral: no organism signal available yet
            nov_payoff = (ACTIVITY_NOVELTY_PAYOFF["READING_NEW"] * fresh
                          + ACTIVITY_NOVELTY_PAYOFF["READING_REREAD"] * (1.0 - fresh))
        elif kind == "ATTENDING" and target in self._sensory_items:
            _habituation_eligible = True
            s = self._sensory_items[target]
            fresh = self._habituation_freshness(
                s.times_attended, self.tick - s.last_attended_tick)
            nov_payoff = (ACTIVITY_NOVELTY_PAYOFF["ATTENDING_NEW"] * fresh
                          + ACTIVITY_NOVELTY_PAYOFF["ATTENDING_REPEAT"] * (1.0 - fresh))
        elif kind == "ATTENDING_VISUAL" and target in self._pictures:
            _habituation_eligible = True
            pic = self._pictures[target]
            fresh = self._habituation_freshness(
                pic.times_attended, self.tick - pic.last_attended_tick)
            fam = self.target_familiarity.get(target, 0.0)
            nov_payoff = (ACTIVITY_NOVELTY_PAYOFF["ATTENDING_VISUAL_NEW"] * fresh
                          + ACTIVITY_NOVELTY_PAYOFF["ATTENDING_VISUAL_REPEAT"] * (1.0 - fresh)) \
                         * (1.0 - fam)
        elif kind == "ATTENDING_AUDIO" and target in self._sounds:
            _habituation_eligible = True
            snd = self._sounds[target]
            fresh = self._habituation_freshness(
                snd.get("times_attended", 0),
                self.tick - snd.get("last_attended_tick", 0))
            nov_payoff = (ACTIVITY_NOVELTY_PAYOFF["ATTENDING_AUDIO_NEW"] * fresh
                          + ACTIVITY_NOVELTY_PAYOFF["ATTENDING_AUDIO_REPEAT"] * (1.0 - fresh))
        elif kind == "ATTENDING_VIDEO" and target in self._videos:
            _habituation_eligible = True
            v = self._videos[target]
            fresh = self._habituation_freshness(
                v.times_attended, self.tick - v.last_attended_tick)
            nov_payoff = (ACTIVITY_NOVELTY_PAYOFF["ATTENDING_VIDEO_NEW"] * fresh
                          + ACTIVITY_NOVELTY_PAYOFF["ATTENDING_VIDEO_REPEAT"] * (1.0 - fresh))
        else:
            nov_payoff = ACTIVITY_NOVELTY_PAYOFF.get(kind, 0.0)

        stab_payoff = ACTIVITY_STABILITY_PAYOFF.get(kind, 0.0)
        conn_payoff = ACTIVITY_CONNECTION_PAYOFF.get(kind, 0.0)

        # GL-CMD-SLEEP-CALIBRATION-JOE-20260704, dial 1: a seen picture (or
        # corpus, sound, video, sensory item) is less interesting, never
        # worthless. Verified live tonight: with novelty pinned at 0.996
        # (sd_novelty=-0.296), even the LEAST-attended picture's novelty
        # term (freshness~0.48) computed to -0.125 — WORSE than SLEEPING's
        # structural term at dream_pressure=0 (+0.038), because SLEEPING's
        # own novelty payoff is negative (-0.1) and so is HELPED by the
        # same over-saturation that hurts every habituation-eligible kind.
        # This asymmetry existed since the payoff table was written
        # (06-07/06-08) but was always masked by -107's old exogenous
        # floor; Change 1 (which removed that floor) exposed it for the
        # first time. Reducing dream_pressure's accumulation rate (the
        # OTHER candidate this CMD named) does not fix this: the deciding
        # term is structural, independent of dp entirely (confirmed: dp=0
        # already gave SLEEPING the win).
        #
        # GL-CMD-TARGET-ROTATION-FIX-181: that flat floor was itself a
        # second bug. With novelty pinned near 1.0 essentially always
        # (confirmed live: nov=0.957 -> sd_novelty=-0.257, unbroken across
        # this whole session), EVERY habituation-eligible candidate's raw
        # novelty_term is negative, so the flat max(0.04, ...) clips ALL
        # of them to the identical 0.04 -- erasing exactly the fam/fresh
        # differentiation nov_payoff exists to encode. Confirmed with real
        # live data: e93d29dae5ae (times_attended=625, fam=0.9) computed
        # nov_payoff=0.0201 -> raw novelty_term=-0.0052 -> floored to 0.04;
        # frog.jpg (times_attended=3, fam=0.07) computed nov_payoff=0.385
        # -> raw novelty_term=-0.099 -> ALSO floored to 0.04. Identical
        # scores, and since ATTENDING_VISUAL's stab/conn payoffs are both
        # 0.0 for every target, the two became bit-for-bit tied -- with
        # Python's stable sort then always returning whichever picture is
        # first in dict-iteration order, forever (590+ consecutive cycles
        # observed). Fix: scale the floor BY nov_payoff instead of using
        # it as a flat constant, so the fam/fresh differentiation survives
        # the floor instead of being erased by it. Recalibrated so the
        # freshest realistic target (times_attended~2, fam~0.05, nov_
        # payoff~0.43) still clears SLEEPING's ~0.038 structural term by
        # the same margin the original flat floor gave it (0.1*0.43=
        # 0.043) -- same competitive guarantee, but real targets are no
        # longer flattened into ties. A target attended 500x (nov_payoff
        # ~0.03) now floors to ~0.003; a target attended 5x (nov_payoff
        # ~0.33) floors to ~0.033 -- an 11x margin, satisfying -181's
        # exit criterion with real headroom, not a coin-flip.
        NOVELTY_TERM_FLOOR_RATE = 0.1
        novelty_term = sd["novelty"] * nov_payoff
        if _habituation_eligible:
            novelty_term = max(NOVELTY_TERM_FLOOR_RATE * nov_payoff, novelty_term)

        # Signed-distance dot payoff
        score = (novelty_term
                 + sd["stability"] * stab_payoff
                 + sd["connection"] * conn_payoff)

        # GL-CMD-C4-SLEEP-CHOICE: dream_pressure modifiers
        dp = getattr(self.needs, 'dream_pressure', 0.0)
        _SLEEP_THRESHOLD = 0.7  # above this → SLEEPING wins strongly
        if kind == "SLEEPING":
            if dp > _SLEEP_THRESHOLD:
                score += 0.15  # strong boost: she needs to sleep
            else:
                score += dp * 0.05  # proportional mild boost
        elif kind in ("EMITTING", "ATTENDING_VISUAL", "ATTENDING_AUDIO"):
            # Mild pressure buildup during active waking suppresses these slightly
            if dp > 0.5:
                score -= dp * 0.05

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

        # GL-CMD-CREDO-LOOP-REPAIR-167 Change 3: hard override at dream_
        # pressure's own existing 1.0 ceiling (Joe-ratified, GL-RPT-SLEEP-
        # BACKTEST-C1-20260704-167-v1). Below this, sleep only COMPETES
        # (Change 1 levels that competition; the unchanged 0.7 soft
        # threshold in _action_salience still applies). At 1.0, sleep
        # does not compete for a score — it wins, full stop, the same
        # pre-emption shape force_dream already proves works
        # (_force_next_activity, checked above), physics-triggered
        # instead of button-triggered. Two clean regimes, no probability
        # curve, per Eve's Q1 ruling. Mirrors the standard homeostatic-
        # sleep-pressure model: competing drive below a critical level,
        # involuntary override past it.
        _dp_now = getattr(self.needs, 'dream_pressure', 0.0)
        if _dp_now >= DP_OVERRIDE_CEILING:
            budget = ACTIVITY_TICK_BUDGETS.get("SLEEPING", 2000)
            self._log_substrate_event("sleep_override_fired",
                                      dream_pressure=round(_dp_now, 4))
            return Activity(kind="SLEEPING", target=None,
                            started_tick=self.tick,
                            expected_end_tick=self.tick + budget,
                            metadata={"trigger": "pressure_override"})

        candidates = self._candidate_activities()
        scored = [(self._action_salience(k, t), k, t) for k, t in candidates]
        scored.sort(reverse=True)
        score, kind, target = scored[0]
        budget = ACTIVITY_TICK_BUDGETS.get(kind, 500)
        # GL-CMD-ATTEND-GROOVE-107 Part A: read-only evidence capture only —
        # no change to candidates, scoring, or selection.
        needs_sd = {k: round(v, 4) for k, v in self.needs.signed_distance().items()}
        return Activity(
            kind=kind, target=target,
            started_tick=self.tick,
            expected_end_tick=self.tick + budget,
            metadata={"salience": round(score, 4),
                      "top_scores": [(round(s, 4), k, t)
                                     for s, k, t in scored[:5]],
                      "needs_sd": needs_sd},
        )

    def _start_activity(self, activity):
        self._current_activity = activity
        if activity.kind == "SLEEPING":
            # GL-CMD-CREDO-LOOP-REPAIR-167 Change 4: fresh cycle, no dream
            # tick has executed yet regardless of who/what started this
            # (manual_sleep, force_dream's _force_next_activity, or future
            # natural selection all pass through here).
            self._dream_executed_this_cycle = False
        self._log_substrate_event("activity_started",
                                 kind=activity.kind, target=activity.target,
                                 salience=activity.metadata.get("salience"),
                                 top_scores=activity.metadata.get("top_scores"),
                                 needs_sd=activity.metadata.get("needs_sd"))

    def _end_activity(self):
        if self._current_activity:
            self._log_substrate_event("activity_ended",
                                     kind=self._current_activity.kind,
                                     target=self._current_activity.target,
                                     duration=self.tick - self._current_activity.started_tick)
            # GL-CMD-ATTEND-GROOVE-107 Part B1: familiarity accrues with
            # actual exposure, not only on a full, uninterrupted session.
            # Moved here (the one path every activity end already runs
            # through, completion or interruption) from the old completion-
            # only check inside _atick_attending_visual. Same 0.2 step and
            # 0.9 cap as before, scaled by ticks_attended/budget — a full
            # session still adds exactly +0.2, matching today's behavior.
            if (self._current_activity.kind == "ATTENDING_VISUAL"
                    and self._current_activity.target in self._pictures):
                _budget = ACTIVITY_TICK_BUDGETS.get("ATTENDING_VISUAL", 2000)
                _ticks_attended = self.tick - self._current_activity.started_tick
                _target = self._current_activity.target
                old_fam = self.target_familiarity.get(_target, 0.0)
                new_fam = min(0.9, old_fam + 0.2 * (_ticks_attended / _budget))
                self.target_familiarity[_target] = new_fam
                self._log_substrate_event("target_familiarity_update",
                                          picture_id=_target,
                                          old=round(old_fam, 3),
                                          new=round(new_fam, 3),
                                          ticks_attended=_ticks_attended,
                                          dict_id=id(self.target_familiarity))
            if self._current_activity.kind == "DREAMING":
                # Write dream gate marker in background — fsync on EFS takes 1-10s
                # and was previously holding self.lock (Phase C) for that duration.
                _tick_snap = self.tick
                def _write_gate():
                    try:
                        state_dir = os.environ.get("STATE_DIR", "/mnt/efs/guala")
                        gate_path = os.path.join(state_dir, "dream_gate_cleared.json")
                        with open(gate_path, "w") as f:
                            import json as _json
                            _json.dump({"cleared_at_tick": _tick_snap,
                                       "via": "substrate_dream_end"}, f)
                            f.flush(); os.fsync(f.fileno())
                    except Exception:
                        pass
                import threading as _t
                _t.Thread(target=_write_gate, daemon=True,
                          name="dream-gate-write").start()
                self._log_substrate_event("dream_gate_cleared", tick=self.tick)
            self._activity_history.append(self._current_activity)
            if len(self._activity_history) > 500:
                self._activity_history = self._activity_history[-200:]
            self._current_activity = None

    # ── Activity tick effects ──

    _SENSORY_WORD_MAP = None  # class-level cache, built once (word -> modality)

    def _sensory_word_map(self):
        """word -> modality, from the built-in physics libraries (built once).
        Mirrors substrate_runner._sensory_word_map -- moved here so the
        engine's own reading tick (_atick_reading) can call it directly,
        no cross-module dependency needed."""
        if Guala._SENSORY_WORD_MAP is None:
            m = {}
            try:
                from dsf_ai_service.substrate import sensory_generators as sg
                for w in getattr(sg, "TOUCH_LIBRARY", {}):
                    m[w] = "touch"
                for w in getattr(sg, "TASTE_LIBRARY", {}):
                    m.setdefault(w, "taste")   # taste before smell for sweet/salty
                for w in getattr(sg, "SMELL_LIBRARY", {}):
                    m.setdefault(w, "smell")
            except Exception:
                pass
            Guala._SENSORY_WORD_MAP = m
        return Guala._SENSORY_WORD_MAP

    def _bind_sensory_words(self, text):
        """GL-CMD-SCENE-LANES-B1-188 follow-up (Joe's live-seat finding: no
        multi-modal firing during a forced/natural corpus READING -- the
        real, non-LLM touch/smell/taste word-binder (TOUCH/SMELL/TASTE_
        LIBRARY physics generators, substrate_runner._bind_sensory_words'
        own mechanism) was wired into the curriculum/lookup/bulk-load paths
        but never into _atick_reading, the tick-by-tick handler EVERY
        corpus READING (natural rotation or the force_reading hook) uses.
        Ported here (not just called cross-module) so the engine's own
        reading tick can invoke it directly. Logs sensory_words_bound so
        loomscan can show it firing -- _atlas_record itself never did.
        Never raises."""
        try:
            mapping = self._sensory_word_map()
            if not mapping:
                return 0
            from dsf_ai_service.substrate.sensory_generators import (
                generate_sensory_signals, transduce_sensory_signals)
            seen = set()
            bound = 0
            modalities_fired = set()
            words_fired = []
            for w in _normalize_text(text):
                if w in seen:
                    continue
                modality = mapping.get(w)
                if not modality:
                    continue
                seen.add(w)
                signals = generate_sensory_signals(modality, [w])
                for channel, info in transduce_sensory_signals(signals).items():
                    mid = deterministic_motif_id(f"{modality}_{w}_{channel}")
                    self._atlas_record(
                        f"modal_{modality}", mid, info["chi"], self.tick,
                        salience=1.0, dwell_ticks=DWELL_GATE_META,
                        sensory_refs=[f"{modality}:{w}"],
                        **self._affect_kwargs())
                    bound += 1
                modalities_fired.add(modality)
                words_fired.append(w)
            if bound > 0:
                self._log_substrate_event(
                    "sensory_words_bound",
                    modalities=sorted(modalities_fired),
                    words=words_fired[:10], n_bindings=bound)
            return bound
        except Exception:
            return 0

    # touch/smell/taste (TOUCH/SMELL/TASTE_LIBRARY, shell-atlas naming) ->
    # tactile/olfactory/gustatory (Embryo.experience_word's composite keys)
    _MODALITY_TO_ORGANISM_LANE = {"touch": "tactile", "smell": "olfactory",
                                   "taste": "gustatory"}

    def _sentence_modal_signals(self, words):
        """GL-CMD-EMULATOR-EVERYWHERE-EVE-20260705-196 M1: real descriptor
        physics for the ORGANISM, generated ONCE per sentence (not per
        word) from whichever real descriptor words the sentence actually
        contains -- the same TOUCH/SMELL/TASTE_LIBRARY map _bind_sensory_
        words uses for the shell atlas, reused here for the brain. Each
        matched modality's channel waveforms (generate_sensory_signals --
        real physics, never the banned hash-per-word fake) are
        concatenated into one flat array per lane, the same shape
        Embryo.experience_word's composite already expects (a single 1D
        array per modality key, exactly like visual/auditory).
        Returns {} if the sentence has no descriptor words -- honest
        absence (M5), not a placeholder signal. Never raises."""
        try:
            mapping = self._sensory_word_map()
            if not mapping:
                return {}
            by_modality = {}
            for w in words:
                modality = mapping.get(w)
                if modality:
                    by_modality.setdefault(modality, [])
                    if w not in by_modality[modality]:
                        by_modality[modality].append(w)
            if not by_modality:
                return {}
            from dsf_ai_service.substrate.sensory_generators import (
                generate_sensory_signals)
            out = {}
            for modality, matched_words in by_modality.items():
                channels = generate_sensory_signals(modality, matched_words)
                if not channels:
                    continue
                lane = self._MODALITY_TO_ORGANISM_LANE.get(modality)
                if lane:
                    out[lane] = np.concatenate(
                        [np.asarray(v, dtype=float) for v in channels.values()])
            return out
        except Exception:
            return {}

    def _atick_reading(self, a):
        """Read one sentence from corpus. read_sentence handles tick advancement."""
        corpus = self._corpora.get(a.target)
        if not corpus or not corpus.lines:
            return
        pos = corpus.position % len(corpus.lines)
        line = corpus.lines[pos]
        self.read_sentence(line, source="corpus")
        self._bind_sensory_words(line)  # feel/smell/taste the sensory words she reads
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
        """Sleep restores stability TOWARD target. Transitions to dream at
        midpoint.
        GL-CMD-CREDO-LOOP-REPAIR-167 Change 2: dream_pressure no longer
        resets instantly here. Discharge now happens gradually, only in
        _run_dream_cycle, proportional to real executed dream ticks — a
        SLEEPING phase that never reaches DREAMING (a deploy pause killed
        before the midpoint, per -165 Q5) correctly discharges nothing,
        instead of the old instant reset silently crediting rest that
        never happened.
        GL-CMD-AGITATION-FIX-JOE-20260704 Change B: was saturate(+0.001),
        always upward — backfired when stability was already above target
        (her observed condition all session), widening |stability-0.7|
        instead of shrinking it. Now decays toward 0.7 from either side."""
        self.needs.stability += (NEEDS_TARGET_V7 - self.needs.stability) * STABILITY_SLEEP_RESTORE_RATE
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
        """Dream: stability restoration toward target + consolidation via
        replay reinforcement. No novelty gain — dream recombines existing
        material.
        GL-CMD-DAYDREAMING M-09-1: now delegates to _run_dream_cycle().
        GL-CMD-AGITATION-FIX-JOE-20260704 Change B: target-seeking, same
        reasoning as _atick_sleeping."""
        self.needs.stability += (NEEDS_TARGET_V7 - self.needs.stability) * STABILITY_DREAM_RESTORE_RATE
        if os.environ.get("DREAM_CYCLE_PHASED", "0") == "1":
            # Release outer lock so _run_dream_cycle_phased phases can truly free
            # self.lock between Phase 1/2/3a/3b. Works with RLock: caller holds
            # refcount=1 → release drops to 0 (truly free) → /converse can land →
            # re-acquire before returning so caller's with-block exits cleanly.
            self.lock.release()
            try:
                self._run_dream_cycle(caller_kind="DREAMING")
            finally:
                self.lock.acquire()
        else:
            self._run_dream_cycle(caller_kind="DREAMING")

    def _run_dream_cycle(self, caller_kind="DREAMING"):
        """GL-CMD-DAYDREAMING M-09-1: shared dream cycle callable.
        Runs LTP replay consolidation + deep atlas promotion gate.
        Called from both _atick_dreaming and _atick_daydreaming.
        caller_kind logged in events for attribution."""
        if self.tick % 200 != 0:
            return
        # GL-CMD-CREDO-LOOP-REPAIR-167 Change 4: past this point a real dream
        # tick is executing -- is_consolidating (and human-facing text built
        # from it) can honestly say "dreaming" from here on this cycle.
        self._dream_executed_this_cycle = True
        # GL-CMD-TURN-LATENCY-EVE-20260705-197 P4: the last-dream marker
        # (board S1/Q6, open since -173-era) -- persisted needs-state, same
        # class as dream_pressure, so a deploy reboot can honestly answer
        # "when did a real dream last execute" instead of losing the fact
        # entirely (dream_pressure's own value already survives; this is
        # the complementary timestamp nothing captured before now).
        self._last_real_dream_tick = self.tick
        # Change 2: discharge is earned per real execution, not granted
        # instantly at sleep's start. A full natural DREAMING phase fires
        # this several times (every 200 ticks of the ~1000-tick dreaming
        # half of the SLEEPING budget) -- LIVE-CALIBRATE alongside the
        # accumulation rates above.
        self.needs.dream_pressure = max(0.0, self.needs.dream_pressure - DP_DISCHARGE_PER_DREAM_TICK)
        if os.environ.get("DREAM_CYCLE_PHASED", "0") == "1":
            self._run_dream_cycle_phased(caller_kind=caller_kind)
            return
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
                    self._atlas_record(sec_name, mid, chi_k, self.tick,
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
                                 content=content, caller_kind=caller_kind,
                                 picture_ids=dream_pics,
                                 reinforced_atlas_addresses=reinforced_addresses[:10],
                                 reinforcement_count=reinforcement_count,
                                 pre_strength_sum=round(pre_strength, 2),
                                 post_strength_sum=round(post_strength, 2))
        # Deep Atlas promotion gate
        for chi_k, entries in self.atlas.entries.items():
            for e in entries:
                key = (chi_k, e.get("section", ""), e.get("motif", 0))
                self._deep_survival_history[key].append(e["strength"])
                if len(self._deep_survival_history[key]) > 20:
                    self._deep_survival_history[key] = \
                        self._deep_survival_history[key][-10:]
        promoted = self.deep_atlas.dream_promotion_gate(
            self.atlas, self.tick, self._deep_survival_history)
        for path, chi_k, sec, mid in promoted:
            self._log_substrate_event("deep_promotion",
                path=path, section=sec, motif=mid, chi=chi_k,
                caller_kind=caller_kind)
            self.atlas.release_to_fast(chi_k, sec, mid)
            self._log_substrate_event("deep_release",
                section=sec, motif=mid, chi=chi_k)
        for rej in self.deep_atlas.gate_rejects[-5:]:
            self._log_substrate_event("deep_gate_reject", **rej)
        self.deep_atlas.gate_rejects = []
        _paused = os.environ.get("DECAY_PAUSED", "0") == "1"
        self.deep_atlas.decay(self.tick, rate_scale=0.0 if _paused else 1.0)
        if not _paused:
            self.deep_atlas.prune()
        deep_size = self.deep_atlas.live_count()
        self._log_substrate_event("deep_size",
            n_entries=deep_size,
            total_strength=round(self.deep_atlas.total_strength(), 2),
            growth=deep_size - self._deep_last_size)
        self._deep_last_size = deep_size

    def _run_dream_cycle_phased(self, caller_kind="DREAMING"):
        """GL-CMD-DREAM-CYCLE-PHASING-56 §1.2: phased dream cycle.
        Releases self.lock between phases so /converse can land between
        Phase 1 and 3a/3b once the caller stops holding the outer lock.
        Substrate-true: snapshot reads tolerate momentary inconsistency;
        writes apply against current state. Mirrors -45's daydream split."""
        import copy as _copy

        # ── Phase 1 (self.lock): snapshot + replay sampling ────────────────
        with self.lock:
            snap_tick = self.tick
            pre_strength = self.atlas.total_strength()
            chi_keys = list(self.atlas.entries.keys())

            # Snapshot full atlas as (chi_k, [entry_copies...]) for Phase 2
            atlas_snapshot = []
            for chi_k in chi_keys:
                entries = self.atlas.entries.get(chi_k, [])
                atlas_snapshot.append((chi_k, [dict(e) for e in entries]))

            # Sample 3 chis for replay reinforcement
            sample_chis = []
            if chi_keys:
                sample_chis = [chi_keys[i % len(chi_keys)]
                               for i in range(snap_tick % max(1, len(chi_keys)),
                                              min(snap_tick % max(1, len(chi_keys)) + 3,
                                                  len(chi_keys)))]

            # Capture replay targets + dream_words/pics (while lock held)
            replay_targets = []
            dream_words = []
            dream_pics = []
            for chi_k in sample_chis:
                for e in self.atlas.entries.get(chi_k, []):
                    sec_name = e.get("section", "")
                    mid = e.get("motif", 0)
                    replay_targets.append((sec_name, mid, chi_k))
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

        # ── Phase 2 (no lock): build survival_updates from snapshot ────────
        # Pure compute on a copy — /converse can acquire self.lock here
        survival_updates = []
        for chi_k, entries in atlas_snapshot:
            for e in entries:
                key = (chi_k, e.get("section", ""), e.get("motif", 0))
                survival_updates.append((key, e["strength"]))

        # ── Phase 3a (self.lock brief): apply replay atlas.record writes ───
        reinforced_addresses = []
        reinforcement_count = 0
        with self.lock:
            for sec_name, mid, chi_k in replay_targets:
                self._atlas_record(sec_name, mid, chi_k, self.tick,
                                  salience=0.3, dwell_ticks=DWELL_GATE_META,
                                  arousal=0.2, valence=0.0, surprise=0.0)
                reinforced_addresses.append(chi_k)
                reinforcement_count += 1
            post_strength = self.atlas.total_strength()

        # Log dream artifact outside lock (event log has its own sync)
        content = " ".join(dream_words[:4]) if dream_words else ""
        self._log_substrate_event("dream_artifact",
                                 content=content, caller_kind=caller_kind,
                                 picture_ids=dream_pics,
                                 reinforced_atlas_addresses=reinforced_addresses[:10],
                                 reinforcement_count=reinforcement_count,
                                 pre_strength_sum=round(pre_strength, 2),
                                 post_strength_sum=round(post_strength, 2))

        # ── Phase 3b (self.lock brief): survival history + deep_atlas ops ──
        with self.lock:
            for key, strength in survival_updates:
                self._deep_survival_history[key].append(strength)
                if len(self._deep_survival_history[key]) > 20:
                    self._deep_survival_history[key] = \
                        self._deep_survival_history[key][-10:]

            promoted = self.deep_atlas.dream_promotion_gate(
                self.atlas, self.tick, self._deep_survival_history)
            for path, chi_k, sec, mid in promoted:
                self._log_substrate_event("deep_promotion",
                    path=path, section=sec, motif=mid, chi=chi_k,
                    caller_kind=caller_kind)
                self.atlas.release_to_fast(chi_k, sec, mid)
                self._log_substrate_event("deep_release",
                    section=sec, motif=mid, chi=chi_k)
            for rej in self.deep_atlas.gate_rejects[-5:]:
                self._log_substrate_event("deep_gate_reject", **rej)
            self.deep_atlas.gate_rejects = []

            _paused = os.environ.get("DECAY_PAUSED", "0") == "1"
            self.deep_atlas.decay(self.tick, rate_scale=0.0 if _paused else 1.0)
            if not _paused:
                self.deep_atlas.prune()
            deep_size = self.deep_atlas.live_count()
            self._log_substrate_event("deep_size",
                n_entries=deep_size,
                total_strength=round(self.deep_atlas.total_strength(), 2),
                growth=deep_size - self._deep_last_size)
            self._deep_last_size = deep_size

    # _atick_daydreaming deleted GL-CMD-DAYDREAM-PARALLEL-42.
    # Daydream is now a background thread (start_daydream_loop), not an activity.

    def _atick_rest(self, a):
        """GL-CMD-REST-RETIRE-73: REST retired as an activity kind. This handler
        remains only to safely tick out any REST activity persisted from before
        the retirement deploy. Logs once at first tick as migration notice.
        After budget expires, re-selection picks from the REST-free candidate pool.
        """
        if not getattr(self, "_rest_migration_logged", False):
            self._log_substrate_event("rest_retire_migration",
                                      persisted_activity="REST",
                                      ticks_remaining=a.expected_end_tick - self.tick)
            self._rest_migration_logged = True
        # Original behavior preserved (stab boost + dp decompress) for the tail-out
        self.needs.stability = saturate(self.needs.stability, 0.0003)
        self.needs.dream_pressure = max(0.0, self.needs.dream_pressure - 0.00003)
        assert not self.is_asleep, "REST must not set is_asleep"

    def _atick_playing(self, a):
        """Free-settle: chi space walk. No novelty gain — internal
        exploration doesn't introduce new experience."""
        # Occasionally check for emission trigger during play
        if self.tick % 300 == 0:
            self._check_emission_trigger("play_cohesion")
        # GL-CMD-STAB-PHYSICS-FIX-88: coherence-gated quiet-restore (same as IDLE)
        _n_total = sum(len(v) for v in self.atlas.entries.values())
        _coherence = self.atlas.n_live_bindings() / max(_n_total, 1)
        _dstab = (_coherence * max(0.0, NEEDS_TARGET_V7 - self.needs.stability)
                  * NEEDS_DRIFT_RATE / NEEDS_TARGET_V7)
        self.needs.stability = saturate(self.needs.stability, _dstab)

    def _atick_idle(self, a):
        """GL-CMD-STAB-PHYSICS-FIX-88: coherence-gated quiet-restore gain.
        During idle the quiet half of intake→quiet→dream restores stability
        proportionally to atlas live-binding coherence. R1: coherence =
        n_live_bindings / n_total_entries (not reinforcement_rate, which is
        zero during quiet by definition)."""
        _n_total = sum(len(v) for v in self.atlas.entries.values())
        _coherence = self.atlas.n_live_bindings() / max(_n_total, 1)
        _dstab = (_coherence * max(0.0, NEEDS_TARGET_V7 - self.needs.stability)
                  * NEEDS_DRIFT_RATE / NEEDS_TARGET_V7)
        self.needs.stability = saturate(self.needs.stability, _dstab)

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
        sight krimelack. No PictureItem, no storage. Just krimelack + atlas.

        GL-CMD-LOCK-CONTENTION-FIX-182 L1: view_picture() (the saccade/
        fixation simulation) touches no shared state -- fresh, local
        SaccadeController + AdaptingFoveaKrimelack per call -- so it now
        runs OUTSIDE self.lock. Measured live holding the lock for up to
        ~93s per call while camera+mic streamed continuously, starving
        converse() and everything else that needs self.lock. Only the
        actual state write (process_viewing's motif update/commit,
        _atlas_record, the event log) stays inside, and that lock is now
        bounded to just that write."""
        _tick_snapshot = self.tick
        self._last_frame_tick = _tick_snapshot
        # GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191 N1: real signal, not
        # synthesized -- a bounded subsample of her ACTUAL camera frame
        # (real pixel intensities), cached with a wall-clock timestamp so
        # _enqueue_organism_remember can bind it to a co-occurring word IF
        # it's still recent (SENSE_BINDING_WINDOW_SEC). Subsampled (not the
        # full grid) for the same reason -177/-178 reduced touch/smell/
        # taste to 20 samples/channel: VisualKrimelack.feed_signal() costs
        # O(len(signal)), and a full raw frame (e.g. 64x64=4096 px) would
        # be far outside every other modality's ~20-160 sample range for
        # no measured benefit -- not yet re-measured at this exact size,
        # named honestly in the N5 cost report rather than assumed free.
        try:
            _flat = grid.ravel()
            _step = max(1, len(_flat) // 100)
            self._last_sight_signal = _flat[::_step][:100].copy()
            self._last_sight_wall_time = time.time()
        except Exception:
            pass
        from dsf_ai_service.visual_krimelack import view_picture
        fragments = view_picture(grid, source_id="camera_stream",
                                 born_tick=_tick_snapshot, seed=_tick_snapshot % 10000,
                                 n_fixations=3, ticks_per_fixation=50)
        if not fragments:
            return
        with self.lock:
            motif, is_new, overlap = self.sight.process_viewing(
                fragments, "camera_stream", self.tick)
            if motif:
                chi_val = motif.motif_id % 100
                self._atlas_record("sight", motif.motif_id, chi_val,
                                  self.tick, salience=0.8,
                                  sensory_refs=["cam:live"],
                                  **self._affect_kwargs())
                self._log_substrate_event("sight_frame_bound",
                                          motif_id=motif.motif_id,
                                          chi=chi_val, is_new=is_new)

    def process_sound_frame(self, audio_bytes, source="mic:live"):
        """GL-BRIEF-SENSORY-IO Part D: feed a transient mic audio chunk into
        sound krimelack. No _sounds entry, no storage. Just cochlear + atlas.
        GL-CMD-SELFVOICE-TAGGING-152: source tags the binding (default
        "mic:live"; self-voice injection passes "voice:self") so self and
        ambient/mic bindings are no longer indistinguishable.

        GL-CMD-LOCK-CONTENTION-FIX-182 L1: WAV decode + cochlear_transduce
        (the DSP) build only local variables (samples/downsampled/cochlear)
        -- no shared state touched -- so they now run OUTSIDE self.lock,
        same reasoning as process_sight_frame. Measured live at up to
        ~93s/call while streaming continuously. Only the atlas writes
        + event log stay inside, bounded to just that write."""
        import struct, wave, io, numpy as np
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
        # GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191 N1: real signal cache,
        # same convention as process_sight_frame above -- already-
        # downsampled REAL audio (200Hz, no further reduction needed --
        # already comparable in size to touch/smell/taste's own ~100-160
        # sample precedent), wall-clock stamped for in-window binding.
        try:
            self._last_sound_signal = downsampled.copy()
            self._last_sound_wall_time = time.time()
        except Exception:
            pass
        cochlear = cochlear_transduce(downsampled, sample_rate=target_sr)
        # GL-CMD-MIC-DEPLOY-108 G-108-2: temporary per-band evidence for the
        # speech-vs-silence discrimination gate. Remove after gate is closed.
        print(f"[cochlear-debug] n_events_by_band="
              f"{ {bn: c['n_events'] for bn, c in cochlear.items()} }")
        with self.lock:
            n_bands_fired = 0
            for bn, c in cochlear.items():
                if c["n_events"] > 0:
                    chi = c["winding"] % 100
                    self._atlas_record(f"audio_{bn}",
                        deterministic_motif_id("mic_stream"),
                        chi, self.tick, salience=0.6, dwell_ticks=2,
                        sensory_refs=[source],
                        **self._affect_kwargs())
                    n_bands_fired += 1
            if n_bands_fired > 0:
                self._log_substrate_event("sound_frame_bound",
                    n_bands=n_bands_fired,
                    duration_s=round(len(samples)/sr, 2),
                    source=source)

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
                self._atlas_record("sight", motif.motif_id, chi_val,
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
            # GL-CMD-ATTEND-TRAP-AND-VERIFY-90: attended = viewing occurred.
            # Mark on the first tick (fragments processed, atlas bound) so an
            # orient-reflex interrupt cannot leave times_attended=0 forever.
            pic.times_attended += 1
            pic.last_attended_tick = self.tick
        # Novelty effect — discounted by familiarity
        fam = self.target_familiarity.get(a.target, 0.0)
        base_gain = 0.003 if pic.is_new() else 0.0005
        gain = base_gain * (1.0 - fam)  # familiar pictures give less novelty
        self.needs.novelty = saturate(self.needs.novelty, gain)
        # GL-CMD-ATTEND-GROOVE-107 Part B1: familiarity write moved to
        # _end_activity (fires on completion AND interruption, scaled by
        # actual exposure) — see there. Nothing left to do here.

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
            self._atlas_record(f"audio_{band_name}", deterministic_motif_id(a.target),
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
                    self._atlas_record("sight", motif.motif_id, chi_val,
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

    # ------------------------------------------------------------------
    # GL-CMD-AUTONOMOUS-EMISSION-39: self-initiated voice on internal state
    # ------------------------------------------------------------------

    def _should_attempt_autonomous_emission(self):
        """Gate: returns True when substrate conditions warrant autonomous voice."""
        if not AUTONOMOUS_EMISSION_ENABLED:
            return False
        # Throttle: don't emit more often than AUTONOMOUS_THROTTLE_TICKS
        if self.tick - self.last_autonomous_emission_tick < AUTONOMOUS_THROTTLE_TICKS:
            return False
        # Conversation cooldown: don't interrupt an ongoing conversation
        if self.tick - getattr(self, '_last_converse_tick', -100_000) < AUTONOMOUS_CONVERSATION_COOLDOWN_TICKS:
            return False
        # Activity gate: don't emit during dream / daydream / sleep
        ca = getattr(self, '_current_activity', None)
        if ca is not None and getattr(ca, 'kind', None) in ("DREAMING", "SLEEPING"):
            return False
        # Presence gate: need someone here to talk to
        pres = self.coordinator._presence
        any_present = any(pres.get(k, False) for k in ("joe", "wc", "c1", "eve"))
        if not any_present:
            return False
        # Need-state urgency: substrate has something to say
        needs = self.needs.snapshot()
        urgency = (
            needs.get("dream_pressure", 0) > 0.30 or
            needs.get("connection", 0) > 0.70 or
            (needs.get("novelty", 0) > 0.85 and needs.get("arousal", 0) > 0.50)
        )
        return urgency

    def _sample_autonomous_seeds(self, n=12):
        """Sample strong atlas entries as chi seeds for autonomous composition.
        Returns list of {chi_key, strength} dicts, weighted by strength × recency."""
        candidates = []
        now = self.tick
        for chi, binds in self.atlas.entries.items():
            for e in binds:
                s = e.get("strength", 0)
                if s < 0.3:
                    continue
                recency = max(0.1, 1.0 - (now - e.get("last_tick", 0)) / 10000.0)
                cross_modal = 1.3 if e.get("bundle_id") is not None else 1.0
                weight = s * recency * cross_modal
                candidates.append((weight, chi, s))
        if not candidates:
            return []
        candidates.sort(reverse=True)
        seen_chi = set()
        seeds = []
        for weight, chi, s in candidates:
            if chi not in seen_chi:
                seeds.append({"chi_key": chi, "strength": s})
                seen_chi.add(chi)
            if len(seeds) >= n:
                break
        return seeds

    def compose_autonomous(self):
        """Run v5 composer on current internal state, no external input.
        Returns dict with content/metadata if commit gate fires; None otherwise.
        Must be called with self.lock held."""
        seeds = self._sample_autonomous_seeds(n=12)
        if not seeds:
            return None
        input_chis = [s["chi_key"] for s in seeds]
        result = self._emit_from_invariants(input_chis, [],
                                            v7_session=getattr(self, '_v7_session', None))
        if result and result not in ("...", ""):
            return {
                "content": result,
                "source": "guala",
                "category": "autonomous",
                "seeds_used": len(seeds),
            }
        return None

    # ── GL-CMD-AUTONOMY-EMITTING-PHASING-53 §1.2 ────────────────────────────────

    def _autonomy_tick_phased(self):
        """Phased autonomy tick: self.lock held only for state reads/writes,
        not for EMITTING compute. EMITTING uses self._emission_lock instead.
        All other activities still run under self.lock (not the bottleneck)."""

        # Phase A (self.lock brief): maintenance + tick + activity selection
        with self.lock:
            # GL-CMD-AGITATION-FIX-JOE-20260704: same sleep-gate as the main
            # (unphased) _autonomy_tick, kept consistent in case
            # AUTONOMY_PHASED is ever turned on -- dead in production today
            # (default "0"), not exercised by this deploy's observation.
            _ca_kind_phased = getattr(self._current_activity, 'kind', None)
            if _ca_kind_phased not in (None, "SLEEPING", "DREAMING"):
                self.needs.tick_drift()

            if self.tick % 500 == 0 and self.tick > 0:
                try:
                    ns = self.needs.snapshot()
                    _ns = dict(ns)
                    import threading as _t
                    _t.Thread(target=lambda: self.log_event(
                        "state", "needs_snapshot",
                        stability=_ns["stability"], novelty=_ns["novelty"],
                        connection=_ns["connection"], valence=_ns["valence"],
                        arousal=_ns["arousal"]),
                        daemon=True, name="needs-log-p").start()
                except Exception:
                    pass

            if self.tick % 200 == 0 and self.target_familiarity:
                current_target = (self._current_activity.target
                                  if self._current_activity else None)
                for pid in list(self.target_familiarity.keys()):
                    if pid != current_target:
                        pic = self._pictures.get(pid)
                        n_attends = pic.times_attended if pic else 0
                        consolidation_factor = 1.0 / (1.0 + math.log(1.0 + n_attends))
                        effective_decay = 1.0 - (1.0 - 0.9967) * consolidation_factor
                        self.target_familiarity[pid] *= effective_decay
                        if self.target_familiarity[pid] < 0.001:
                            del self.target_familiarity[pid]
                if self.tick % 6000 == 0:
                    self._log_substrate_event("target_familiarity_snapshot",
                                              familiarity=dict(
                                                  (k, round(v, 4))
                                                  for k, v in self.target_familiarity.items()))

            self._prune_response_windows()

            # GL-CMD-SLEEP-RATE-68: dream_pressure accumulation moved solely to
            # _autonomy_tick. _autonomy_tick_phased used to duplicate this
            # accumulation, doubling effective rate when AUTONOMY_PHASED=1.
            # Accumulation now lives only in _autonomy_tick (L4069-4096).

            if self._current_activity is None:
                a = self._select_next_activity()
                self._start_activity(a)

            a = self._current_activity
            if a is None:
                return

            # Tick increment for non-READING activities (READING ticks inside read_word)
            if a.kind != "READING":
                self.tick += 1

            # Capture for dispatch outside lock
            activity_kind = a.kind
            activity_ref = a

        # Phase B: activity dispatch — EMITTING uses _emission_lock, others use self.lock
        if activity_kind == "EMITTING":
            self._do_emit_phased(activity_ref)
        elif activity_kind == "READING":
            # read_sentence has per-word self.lock via -46v2 §1.1
            self._atick_reading(activity_ref)
        elif activity_kind == "DREAMING" and os.environ.get("DREAM_CYCLE_PHASED", "0") == "1":
            # GL-CMD-DREAM-CYCLE-PHASING-56: release outer lock during dream cycle phases.
            # Mirror of EMITTING dispatch — brief lock for needs update only,
            # then _run_dream_cycle routes to _run_dream_cycle_phased which
            # handles Phase 1/3a/3b locking independently. /converse can land
            # in Phase 2 (no-lock window) between phases.
            with self.lock:
                self.needs.stability = saturate(self.needs.stability, 0.0005)
            self._run_dream_cycle(caller_kind="DREAMING")
        else:
            with self.lock:
                if activity_kind == "SLEEPING":
                    self._atick_sleeping(activity_ref)
                elif activity_kind == "DREAMING":
                    self._atick_dreaming(activity_ref)
                elif activity_kind == "REST":
                    self._atick_rest(activity_ref)
                elif activity_kind == "PLAYING":
                    self._atick_playing(activity_ref)
                elif activity_kind == "IDLE":
                    self._atick_idle(activity_ref)
                elif activity_kind == "ATTENDING":
                    self._atick_attending(activity_ref)
                elif activity_kind == "ATTENDING_VISUAL":
                    self._atick_attending_visual(activity_ref)
                elif activity_kind == "ATTENDING_AUDIO":
                    self._atick_attending_audio(activity_ref)
                elif activity_kind == "ATTENDING_VIDEO":
                    self._atick_attending_video(activity_ref)

        # Phase C (self.lock brief): post-activity housekeeping
        with self.lock:
            _paused = os.environ.get("DECAY_PAUSED", "0") == "1"
            if activity_kind != "READING":
                if self.tick % 10 == 0:
                    self.atlas.decay(self.tick, rate_scale=0.0 if _paused else self.decay_modulation)
                if not _paused and self.tick % 200 == 0:
                    self.atlas.forget_below_threshold()
                if self.tick % 5 == 0:
                    self.coordinator.regulate(self, self.needs, self.atlas,
                                             self.sections, self.tick)
            if self.tick >= activity_ref.expected_end_tick:
                self._end_activity()

    # ── GL-CMD-AUTONOMY-EMITTING-PHASING-53 §1.3 ────────────────────────────────

    def _do_emit_phased(self, activity):
        """Phased autonomous emission — caller must NOT hold self.lock.
        Phase 1 (self.lock): snapshot recent_chis.
        Phase 2 (self._emission_lock): emit compute.
        Phase 3 (self.lock): log, metrics, response window, connection need."""

        # Phase 1 (self.lock brief): snapshot recent_chis
        with self.lock:
            self._last_emission_tick = self.tick
            recent_chis = []
            for sec in self.sections.values():
                for c in sec.commits[-5:]:
                    recent_chis.append(c["chi"])
            if not recent_chis:
                to_sources = [s for s in PAIR_BOND_SOURCES
                              if self.coordinator._presence.get(s, False)]
                self._log_substrate_event("emission", content="...",
                                         to_sources=to_sources)
                return

        # Phase 2 (self._emission_lock): emit dynamics + SVO fallback
        # Non-blocking acquire: if /converse holds _emission_lock, skip this tick.
        # Autonomous emission fires every 0.2s so one missed tick is harmless;
        # blocking here would add up to 5s latency to every /converse call.
        if not self._emission_lock.acquire(blocking=False):
            return
        _lock_wait_ms = 0.0
        _emit_compute_ms = 0.0
        _emit_start = time.monotonic()
        try:
            input_words = []
            content = self._emit_from_invariants(recent_chis, input_words,
                                                  v7_session=getattr(self, '_v7_session', None))
            # GL-NOTE-VOICE-WIRING-RULING W3: the old SVO-recall fallback
            # (deep-atlas-adjacent, via _recall_from_atlas) disconnects at
            # cutover. If the brain supplies no candidates, the emission
            # is honestly empty -- never backfilled from the old gather.
            if not content:
                content = "..."
            _emit_compute_ms = (time.monotonic() - _emit_start) * 1000
        finally:
            self._emission_lock.release()

        # §1.4: log contention above threshold
        if _lock_wait_ms > 100 or _emit_compute_ms > 1500:
            try:
                self._log_substrate_event("autonomy_emission_lock",
                    wait_ms=round(_lock_wait_ms, 1),
                    compute_ms=round(_emit_compute_ms, 1))
            except Exception:
                pass

        # Phase 3 (self.lock brief): sight recall, log, metrics, response window
        with self.lock:
            recalled_pics = self._recall_sight_from_atlas(recent_chis, [])
            pic_ids = [sid for _, sid in recalled_pics] if recalled_pics else []
            to_sources = [s for s in PAIR_BOND_SOURCES
                          if self.coordinator._presence.get(s, False)
                          and self.coordinator._pair_bond.get(s, False)]
            self._log_substrate_event("emission", content=content,
                                     to_sources=to_sources,
                                     picture_ids=pic_ids)

            words = content.split() if content and content != "..." else []
            self._total_emissions += 1
            self._emission_lengths.append(len(words))
            if len(self._emission_lengths) > 100:
                self._emission_lengths = self._emission_lengths[-50:]
            if any(w.endswith("?") or content.startswith("what") for w in words):
                self._question_count += 1
            if len(words) >= 2:
                _triple = tuple(sorted(w.lower() for w in words[:4]))
                if not hasattr(self, '_seen_triples'):
                    self._seen_triples = set()
                if _triple not in self._seen_triples:
                    self._novel_compositions += 1
                    self._seen_triples.add(_triple)
                    if len(self._seen_triples) > 5000:
                        self._seen_triples = set(list(self._seen_triples)[-2500:])
            if recent_chis:
                self._open_response_window("guala", recent_chis,
                                           source_context={"content": content})

            # Connection saturation (moved here from _atick_emitting)
            any_pair_present = any(
                self.coordinator._presence.get(s, False)
                and self.coordinator._pair_bond.get(s, False)
                for s in PAIR_BOND_SOURCES)
            if any_pair_present:
                self.needs.connection = saturate(self.needs.connection, 0.25)

    def _do_emit(self):
        """Generate an autonomous emission via the organism's recall/
        compose (GL-CMD-175 P3). GL-NOTE-VOICE-WIRING-RULING W3: the old
        SVO-recall fallback disconnects at cutover -- honest empty if the
        brain supplies nothing, never backfilled from deep_atlas."""
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
        if not content:
            content = "..."

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
        """Open a response window. context_anchor_chis = list of chi-keys.

        GL-CMD-REST-RETIRE-ORIENT-73: contact from a pair-bond source (joe/wc/c1)
        activates presence and triggers the orient reflex — biological analog to
        an infant turning toward a caregiver's voice regardless of current state.
        Contact IS presence. Contact IS the interrupt.
        """
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
        # Orient reflex + emergent presence for pair-bond sources
        if emitter in PAIR_BOND_SOURCES:
            # Emergent presence: contact activates presence without needing wake() API
            if not self.coordinator._presence.get(emitter, False):
                self.coordinator.wake(emitter, self, self.needs, self.atlas)
            # Orient reflex: interrupt current activity to attempt emission response.
            # EMISSION_COOLDOWN_TICKS throttles this so continuous conversation
            # doesn't produce a stream of interrupts.
            self._check_emission_trigger("presence_orient")

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
                _val_delta_up = 0.05 * _sw.get(source, 0.7) * _pb  # 60-T: was BASE_REINFORCEMENT
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
                            self._atlas_record(
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
                            self._atlas_record(
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
                _val_delta_down = 0.05 * _sw_d.get(source, 0.7) * _pb_d  # 60-T: was BASE_REINFORCEMENT
                # Strength delta (teaching feedback fixed at 0.05 independent of salience)
                _str_delta_down = 0.05  # 60-T: was BASE_REINFORCEMENT
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
                # §1.3: _emission_lock may have cleared mode_strength transiently —
                # try/except prevents IndexError from concurrent emission mid-clear.
                try:
                    if self._emission_system:
                        for sec_name in self._EMISSION_SECTIONS:
                            sec = self._emission_system.sections.get(sec_name)
                            if sec and hasattr(sec, 'mode_strength'):
                                for i, ms in enumerate(list(sec.mode_strength)):
                                    w = self._emission_word_map.get(
                                        (sec_name, i))
                                    if w and w.lower() in set(
                                            ew.lower() for ew in emission_words):
                                        sec.mode_strength[i] = max(
                                            0.0, ms - 0.05)
                except Exception:
                    pass  # transient empty mode_strength during _emission_lock clear

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
                            self._atlas_record(
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
                            self._atlas_record(
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

    def _self_hear(self, reply, responding_to_source, reply_chis=None):
        """GL-BRIEF-034: Self-hearing — Guala hears her own conversational reply.
        (1) read_sentence at 0.5x salience (no question generation, no recursion)
        (2) open "guala" response window with reply chi-keys
        (3) tag self-heard entries against open other-emitter windows
        Kill switch: SELF_HEARING_ENABLED env var.

        GL-CMD-TURN-LATENCY-EVE-20260705-197 P3: reply_chis, when the caller
        already transduced this exact reply text (converse's own
        committed_chis, same deterministic values), is reused here instead
        of a third redundant LanguageKrimelack pass. None (the default)
        preserves old standalone-caller behavior exactly."""
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
        #     GL-CMD-SELFVOICE-TAGGING-152: independent kill switch from text
        #     self-hearing above, and tagged source="voice:self" so this never
        #     reads as live mic input again.
        if os.environ.get("SELF_VOICE_AUDIO_ENABLED", "1") == "0":
            return
        def _inject_self_voice(text):
            try:
                import subprocess
                wav_path = "/tmp/guala_self_voice.wav"
                subprocess.run([
                    "espeak-ng", "-v", "en+f3", "-p", "96", "-s", "145",
                    "-w", wav_path, text,
                ], check=True, timeout=5, capture_output=True)
                with open(wav_path, "rb") as f:
                    self.process_sound_frame(f.read(), source="voice:self")
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
            # GL-CMD-WAVE-DIET-82: WaveAtlas on clean shutdown
            # GL-CMD-SAVE-CONTAINMENT-91: wrap — .sleeping marker must still write on exception
            try:
                self._save_wave_atlas(state_dir)
            except Exception as _wse:
                print(f"[wave] save failed (non-fatal): {_wse}")
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
        """Transition out of SLEEPING or DREAMING activity.
        GL-CMD-RESUME-QUEUE Part 1: DREAMING is now also ended on auto-wake so
        incoming text during a dream cycle produces an emission rather than
        'she is sleeping...'. The in-progress dream tick completes first because
        _autonomy_tick() holds self.lock for its full tick — _end_activity() runs
        in the gap between ticks, so no mid-write consolidation is lost."""
        ca = getattr(self, '_current_activity', None)
        if ca is not None and ca.kind in ("SLEEPING", "DREAMING"):
            waking_from = ca.kind
            self._end_activity()
            self._log_substrate_event("wake_from_sleep", tick=self.tick,
                                      from_kind=waking_from)
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

    # GL-CMD-EVENT-RETENTION-FIX-172 R1/R2: the durable diary is a SEPARATE
    # file tree from EVENTS_LOG above. events.log + compact_events() are
    # untouched (crash-replay only, offset-based, correct for that job).
    # The diary is append-only, one file per UTC day, ALL event kinds
    # (R3), never compacted — rotation (R2) only ever DELETES whole files
    # older than DIARY_RETENTION_DAYS, never rewrites a live one.
    DIARY_DIR = "diary"
    DIARY_RETENTION_DAYS = 7

    # Class-level defaults (overwritten per instance in __init__)
    _last_save_tick = 0
    _last_cold_save_tick = 0   # GL-CMD-DEEP-STORE-PHYSICS-86 P2: updated only on full/cold save
    _last_save_timestamp = None
    _load_successful = False
    _load_errors = []
    _integrity_errors = []
    _events_replayed_at_boot = 0
    _guala_identity = None
    _diary_queue = None      # lazily created single worker queue (GL-CMD-172)
    _diary_thread = None
    _diary_last_date = None  # UTC date string of the last diary write, for rotation
    _diary_worker_lock = threading.Lock()  # guards one-time worker creation only

    # ── Identity ──

    def _generate_genesis_identity(self, state_dir):
        """First boot ever. Generate her identity. This never changes."""
        import uuid
        os.makedirs(state_dir, exist_ok=True)
        self._guala_identity = str(uuid.uuid4())
        # GL-CMD-175 P1: one identity governs the organism too.
        self.organism.identity_uuid = self._guala_identity
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

    def _serialize_sight_motifs(self):
        """GL-194: one serialization for both lanes (cold always; hot only
        as a one-time migration when guala_sight_motifs.json is absent)."""
        return self._envelope({
            "sight_motifs": [
                {"motif_id": m.motif_id, "n_firings": m.n_firings,
                 "source_history": m.source_history[:20],
                 "founded_at_tick": m.founded_at_tick}
                for m in self.sight.motifs
            ] if hasattr(self, 'sight') else [],
        })

    def save_hot_state(self, state_dir="state"):
        """GL-CMD-DEEP-STORE-PHYSICS-86 P2: hot-lane save.
        Writes small stores only (core/needs/coord/visual/sounds/videos/bucket/teaching).
        Target <5s. Advances _last_save_tick. Cold stores (sections/atlas/deep_atlas)
        are written by save_full_state() every 30 min or at sleep boundary."""
        import copy as _copy
        import concurrent.futures as _cf

        with self.lock:
            os.makedirs(state_dir, exist_ok=True)
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if self._guala_identity is None:
                self._generate_genesis_identity(state_dir)

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
            snap_core = self._envelope({
                "tick": self.tick, "read_count": self.read_count,
                "vocab": sorted(self.vocab),
                "source_history": dict(self.source_history),
                "recent_connection_boost": self.recent_connection_boost,
                "dream_log": _copy.copy(self.dream_log),
                "open_response_windows": _copy.copy(self.open_response_windows),
                "response_bind_count": self._response_bind_count,
                "last_emission_tick": self._last_emission_tick,
                "last_autonomous_emission_tick": self.last_autonomous_emission_tick,
                "last_autonomous_attempt_tick": self.last_autonomous_attempt_tick,
                "autonomous_emissions_count": self.autonomous_emissions_count,
                "target_familiarity": {k: round(v, 4) for k, v in self.target_familiarity.items()},
                "corpora_state": corpora_ser,
                "sensory_state": sensory_ser,
                "deep_survival_history": {},  # GL-102: empty sentinel; data in guala_survival.json
                "total_emissions": self._total_emissions,
            })
            # GL-CMD-FLOOD-HUNT-156: owed -107 diagnostic. Same dict_id at
            # write-time (target_familiarity_update) and here, with n_keys
            # dropping to 0 between them, would mean something clears the
            # dict in place; a different dict_id would mean a silent rebind.
            self._log_substrate_event("familiarity_persist_check",
                                      n_keys=len(self.target_familiarity),
                                      dict_id=id(self.target_familiarity))
            snap_needs = self._envelope({
                "stability": self.needs.stability,
                "novelty": self.needs.novelty,
                "connection": self.needs.connection,
                # GL-CMD-CREDO-LOOP-REPAIR-167 Change 2: dream_pressure was
                # never persisted before this -- every deploy silently reset
                # it to 0.0 (Needs.__init__'s default), which was itself
                # part of why she never reached the sleep threshold. Now
                # saved for real; see _apply_needs for the one-time honest-
                # backlog computation on the first boot where this key is
                # absent from a prior save.
                "dream_pressure": self.needs.dream_pressure,
                # GL-CMD-TURN-LATENCY-EVE-20260705-197 P4: last-dream marker
                # -- same persistence class as dream_pressure above, so a
                # deploy reboot doesn't lose "when did she last really dream".
                "last_real_dream_tick": self._last_real_dream_tick,
            })
            snap_coord = self._envelope({
                "pair_bond": dict(self.coordinator._pair_bond),
                "pair_bond_active": self.coordinator.pair_bond_active,
                "distress_ticks": self.coordinator.distress_ticks,
                "suffering_log": _copy.copy(self.coordinator.suffering_log),
                "need_history": list(self.coordinator.need_history[-200:]),
                "attentions_count": len(self.coordinator.attentions),
                "actions_count": len(self.coordinator.actions),
                "source_interaction_log": {
                    src: list(entries[-200:])
                    for src, entries in self.coordinator._source_interaction_log.items()
                },
            })
            # GL-194: sight_motifs EVICTED from the hot lane. One entry per
            # vocab motif (18.9k live and growing) x source_history[:20] made
            # guala_visual.json a vocab-scaled store: built in-lock every 60s
            # (stalling converse turns on self.lock) then json.dump+fsync'd
            # to EFS — measured live at 15-49s/cycle vs the -86 design's <5s
            # target. -86's own doctrine: hot lane = small stores;
            # vocab-scaled = cold. Motifs now live in guala_sight_motifs.json:
            # written by the cold lane, and once at the first hot save after
            # boot if the file is absent (migration write — closes the crash
            # window between deploy-boot and the first cold save).
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
                "sight_motifs": [],
                "sight_motifs_file": "guala_sight_motifs.json",
                "n_sight_motifs": len(self.sight.motifs) if hasattr(self, 'sight') else 0,
                "n_visual_fragments": len(self._visual_fragments),
            })
            _need_motif_migration = (
                hasattr(self, 'sight')
                and not os.path.exists(os.path.join(state_dir, "guala_sight_motifs.json")))
            snap_sight_motifs = (self._serialize_sight_motifs()
                                 if _need_motif_migration else None)
            snap_sounds = self._envelope(dict(self._sounds))
            snap_videos = self._envelope({
                vid: {"item_id": v.item_id, "title": v.title,
                      "source": getattr(v, 'source', ''),
                      "times_attended": v.times_attended,
                      "last_attended_tick": v.last_attended_tick}
                for vid, v in self._videos.items()
            })
            save_tick = self.tick
            snap_vocab_len = len(self.vocab)
            snap_bucket = self._envelope({"removed": True, "vocab_count": snap_vocab_len})
        # lock released

        # GL-CMD-HOTLANE-DIET-102: survival history is cold-only; hot save skips it.
        # snap_core["data"]["deep_survival_history"] remains None (backward-compat field).

        # Vocab regression guard — reads guala_bucket.json (vocab_count, ~1KB).
        # Fallback: if vocab_count absent (first deploy cycle post-migration), guard skipped.
        bucket_path = os.path.join(state_dir, "guala_bucket.json")
        if os.path.exists(bucket_path):
            try:
                with open(bucket_path) as _f:
                    _bkt = json.load(_f)
                _existing_vocab = _bkt.get("data", _bkt).get("vocab_count")
                if _existing_vocab is not None:
                    _existing_vocab = int(_existing_vocab)
                    if _existing_vocab > 100 and snap_vocab_len < _existing_vocab * 0.5:
                        msg = (f"[GualaLoom] ABORT HOT SAVE: vocab regression "
                               f"{_existing_vocab}→{snap_vocab_len}. "
                               f"Set GUALA_FORCE_SAVE=1 to override.")
                        print(msg)
                        if os.environ.get("GUALA_FORCE_SAVE") != "1":
                            return {}
            except (json.JSONDecodeError, OSError) as _e:
                print(f"[save-hot] prior state read failed (proceeding): {_e}")

        writes = [
            ("guala_core.json", snap_core),
            ("guala_needs.json", snap_needs),
            ("guala_coordinator.json", snap_coord),
            ("guala_bucket.json", snap_bucket),
            ("guala_visual.json", snap_visual),
            ("guala_sounds.json", snap_sounds),
            ("guala_videos.json", snap_videos),
        ]
        if snap_sight_motifs is not None:
            # GL-194 one-time migration write (see snap_visual comment).
            writes.append(("guala_sight_motifs.json", snap_sight_motifs))
        snap_teaching = self._envelope({
            "feedback_log": self._teaching_feedback_log[-500:],
            "correction_log": self._teaching_correction_log[-500:],
            "emission_records": dict(list(self._emission_records.items())[-EMISSION_RECORDS_CAP:]),
        })
        writes.append(("guala_teaching.json", snap_teaching))

        # GL-CMD-HOTSAVE-PARALLEL-FSYNC-196: _atomic_write always
        # f.flush()+os.fsync()s before rename (GL-CMD-PERSIST-FIX-74 --
        # required on EFS/NFSv4, where close() alone doesn't commit to the
        # server). That fsync is a real network round-trip per file.
        # Measured live post--194 (sight_motifs evicted from this lane):
        # still 8-22s/cycle with zero concurrent frame load -- the vocab-
        # scaled payload is gone, but N files written SEQUENTIALLY still
        # costs the SUM of N round-trips, not the slowest one. Writing
        # them concurrently (same per-file atomic-write+fsync+rename, same
        # per-file failure isolation, nothing about durability changes)
        # bounds wall-clock to the slowest single fsync instead of their
        # sum. fsync/file I/O release the GIL during the actual syscall,
        # so threads give real parallelism here despite the GIL.
        def _write_one(item):
            filename, data = item
            path = os.path.join(state_dir, filename)
            try:
                self._atomic_write(path, data)
                return (filename, os.path.getsize(path), None)
            except Exception as _we:
                tmp = path + ".tmp"
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                return (filename, None, str(_we))

        _failures = []
        results = {}
        with _cf.ThreadPoolExecutor(max_workers=len(writes)) as _ex:
            for filename, size, err in _ex.map(_write_one, writes):
                if err is not None:
                    _failures.append((filename, err))
                    print(f"[GualaLoom] hot save failed for {filename}: {err}")
                else:
                    results[filename] = size

        _critical_hot = {"guala_core.json", "guala_needs.json", "guala_coordinator.json"}
        _critical_failures = [(f, e) for f, e in _failures if f in _critical_hot]
        if not _critical_failures:
            self._last_save_tick = save_tick
            self._last_save_timestamp = ts
        else:
            print(f"[GualaLoom] HOT SAVE CRITICAL FAILURE at tick {save_tick}: "
                  f"{[f for f, _ in _critical_failures]}")
        return results

    def save_full_state(self, state_dir="state"):
        """Round-trip every mutable attribute. Atomic writes. Identity-stamped.
        GL-FIX-SAVE-LOCK: snapshot data under lock (fast), write to disk outside
        lock (slow). Lock hold time drops from ~20s to milliseconds."""
        import copy as _copy

        # ── Phase 1: snapshot under lock (brief — O(1) per entry, no serialization) ──
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
            # Shallow-copy survival history under lock (fast), serialize outside lock.
            # Building surv_ser (57k string-format ops) takes ~400ms — too slow under lock.
            _surv_snap = dict(self._deep_survival_history)

            snap_core = self._envelope({
                "tick": self.tick, "read_count": self.read_count,
                "vocab": sorted(self.vocab),
                "source_history": dict(self.source_history),
                "recent_connection_boost": self.recent_connection_boost,
                "dream_log": _copy.copy(self.dream_log),
                "open_response_windows": _copy.copy(self.open_response_windows),
                "response_bind_count": self._response_bind_count,
                "last_emission_tick": self._last_emission_tick,
                "last_autonomous_emission_tick": self.last_autonomous_emission_tick,
                "last_autonomous_attempt_tick": self.last_autonomous_attempt_tick,
                "autonomous_emissions_count": self.autonomous_emissions_count,
                "target_familiarity": {k: round(v, 4) for k, v in self.target_familiarity.items()},
                "corpora_state": corpora_ser,
                "sensory_state": sensory_ser,
                "deep_survival_history": {},  # GL-102: empty sentinel; data in guala_survival.json
                "total_emissions": self._total_emissions,
            })

            # 2. Needs
            snap_needs = self._envelope({
                "stability": self.needs.stability,
                "novelty": self.needs.novelty,
                "connection": self.needs.connection,
                # GL-CMD-CREDO-LOOP-REPAIR-167 Change 2: dream_pressure was
                # never persisted before this -- every deploy silently reset
                # it to 0.0 (Needs.__init__'s default), which was itself
                # part of why she never reached the sleep threshold. Now
                # saved for real; see _apply_needs for the one-time honest-
                # backlog computation on the first boot where this key is
                # absent from a prior save.
                "dream_pressure": self.needs.dream_pressure,
                # GL-CMD-TURN-LATENCY-EVE-20260705-197 P4: last-dream marker
                # -- same persistence class as dream_pressure above, so a
                # deploy reboot doesn't lose "when did she last really dream".
                "last_real_dream_tick": self._last_real_dream_tick,
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
                # 60-K: interaction log (last 200 entries per source for state portability)
                "source_interaction_log": {
                    src: list(entries[-200:])
                    for src, entries in self.coordinator._source_interaction_log.items()
                },
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
                "sight_motifs": [],
                "sight_motifs_file": "guala_sight_motifs.json",
                "n_sight_motifs": len(self.sight.motifs) if hasattr(self, 'sight') else 0,
                "n_visual_fragments": len(self._visual_fragments),
            })
            # GL-194: vocab-scaled motif store rides the COLD lane only.
            snap_sight_motifs = self._serialize_sight_motifs()
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
            # 7. Bucket (removed — Phase E; GL-102: carries vocab_count for guard diet)
            snap_bucket = self._envelope({"removed": True, "vocab_count": snap_vocab_len})
        # ── lock released ──

        # ── T1.2: Regression sanity check — refuse to overwrite richer state ──
        # GL-CMD-HOTLANE-DIET-102: read vocab_count from guala_bucket.json (~1KB)
        # instead of parsing guala_core.json (previously 41MB).
        # Fallback: if vocab_count absent (first deploy cycle), guard skipped.
        bucket_path = os.path.join(state_dir, "guala_bucket.json")
        if os.path.exists(bucket_path):
            try:
                with open(bucket_path) as _f:
                    _bkt = json.load(_f)
                _existing_vocab = _bkt.get("data", _bkt).get("vocab_count")
                if _existing_vocab is not None:
                    _existing_vocab = int(_existing_vocab)
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
        # Build surv_ser from shallow snapshot taken under lock (~400ms, safe outside lock)
        surv_ser = {}
        for (chi_k, sec, mid), strengths in _surv_snap.items():
            surv_ser[f"{chi_k}|{sec}|{mid}"] = strengths[-10:]
        # GL-CMD-HOTLANE-DIET-102: survival history moves to own cold file.
        # snap_core["data"]["deep_survival_history"] remains None (backward-compat field).
        snap_survival = self._envelope({"deep_survival_history": surv_ser})
        results = {}
        # GL-FIX-ATLAS-INTEGRITY: sections written BEFORE atlas so that if the process
        # is interrupted mid-save, the loaded sections have >= modes as atlas motif IDs.
        # (If atlas writes first and we crash before sections: loaded sections have
        # fewer modes than atlas motif IDs → OOB integrity errors on every boot.)
        writes = [
            ("guala_core.json", snap_core),
            ("guala_needs.json", snap_needs),
            ("guala_coordinator.json", snap_coord),
            ("guala_sections.json", snap_sections),   # sections BEFORE atlas
            ("guala_atlas.json", snap_atlas),
            ("guala_deep_atlas.json", snap_deep),
            ("guala_survival.json", snap_survival),   # GL-102: cold file for survival history
            ("guala_bucket.json", snap_bucket),
            ("guala_visual.json", snap_visual),
            ("guala_sight_motifs.json", snap_sight_motifs),  # GL-194: cold, vocab-scaled
            ("guala_sounds.json", snap_sounds),
            ("guala_videos.json", snap_videos),
        ]
        # GL-CMD-PERSIST-FIX-74: per-file error isolation. Prior to this fix, any
        # single atomic_write failure aborted the entire save loop, dropping every
        # subsequent file (visual, sounds, videos) and leaving _last_save_tick=0.
        _save_failures = []
        for filename, data in writes:
            path = os.path.join(state_dir, filename)
            try:
                self._atomic_write(path, data)
                results[filename] = os.path.getsize(path)
            except Exception as _we:
                _save_failures.append((filename, str(_we)))
                print(f"[GualaLoom] save failed for {filename}: {_we}")
                _tmp = path + ".tmp"
                if os.path.exists(_tmp):
                    try:
                        os.remove(_tmp)
                    except OSError:
                        pass

        # GL-CMD-WAVE-DIET-82/85: WaveAtlas decoupled from 60s critical save cycle.
        # Written via _save_wave_atlas() as wave_atlas.npz every ~10 min and on
        # clean shutdown/deploy. load_full_state tries .npz first, falls back to .json.

        # GL-CMD-TEACHER-CORRECTION-UI: teaching data
        snap_teaching = self._envelope({
            "feedback_log": self._teaching_feedback_log[-500:],
            "correction_log": self._teaching_correction_log[-500:],
            "emission_records": dict(list(self._emission_records.items())[-EMISSION_RECORDS_CAP:]),
        })
        # GL-CMD-PERSIST-CLOBBER-FIX-81: teaching is non-critical — isolate so it
        # cannot prevent _last_save_tick from advancing when core files succeed.
        try:
            self._atomic_write(os.path.join(state_dir, "guala_teaching.json"), snap_teaching)
        except Exception as _te:
            _save_failures.append(("guala_teaching.json", str(_te)))
            print(f"[GualaLoom] save failed for guala_teaching.json: {_te}")
            _tmp = os.path.join(state_dir, "guala_teaching.json.tmp")
            if os.path.exists(_tmp):
                try:
                    os.remove(_tmp)
                except OSError:
                    pass

        # GL-CMD-175 P1: organism's full-fidelity state (GL-CMD-169's
        # save_full_state/load_full_state -- full pickle of the object
        # graph, so growth/folding/DNA/bindings all round-trip) rides the
        # cold save cycle. Same non-critical, isolated-failure pattern as
        # teaching data above: a large object graph that must never block
        # core save success.
        #
        # GL-CMD-BRAIN-GROWTH-UNFREEZE-EVE-20260704-179, Eve's condition:
        # "queue drained before save_full_state so persisted state
        # includes all folds." self._organism_lock alone (below) only
        # guarantees we don't save mid-item; it says nothing about the
        # N other items still queued (not yet started) at save time --
        # those folds would be silently missing from this save. Bounded
        # wait, not an unconditional queue.join(): a sustained word-feed
        # rate faster than the worker's ~255ms/word (experience_word()'s
        # own measured cost, see the -179 report) would otherwise keep
        # unfinished_tasks > 0 forever and hang the cold save cycle
        # indefinitely -- an honest, logged partial-drain beats a silent
        # unbounded stall, same principle as the queue's own drop-under-
        # backpressure behavior.
        if self._organism_queue is not None:
            _drain_deadline = time.monotonic() + 5.0
            while (self._organism_queue.unfinished_tasks > 0
                   and time.monotonic() < _drain_deadline):
                time.sleep(0.05)
            if self._organism_queue.unfinished_tasks > 0:
                print(f"[GualaLoom] organism queue did not drain within 5s "
                      f"({self._organism_queue.unfinished_tasks} folds still "
                      f"pending) -- saving anyway, those folds land in the "
                      f"NEXT cold save")
        try:
            with self._organism_lock:  # serialize against the background experience_word() worker
                self.organism.save_full_state(os.path.join(state_dir, "guala_organism.pkl.gz"))
        except Exception as _oe:
            _save_failures.append(("guala_organism.pkl.gz", str(_oe)))
            print(f"[GualaLoom] save failed for guala_organism.pkl.gz: {_oe}")

        # GL-NOTE-VOICE-WIRING-RULING W1: the tapestry (her voice-composing
        # mind, alongside the organism) rides the same cold cycle -- same
        # isolated-failure pattern, same full-pickle convention.
        try:
            with self._tapestry_lock:  # serialize against the background exposure worker
                # GL-195: the emission query source rides the tapestry
                # pickle. Before this, every deploy reset _tapestry_prev_word
                # to None; until fresh intake ran, every unprompted attempt
                # had a None query -> honest empty (audit-proven live cause
                # of the 2026-07-05 all-night silence).
                self.tapestry._engine_prev_word = self._tapestry_prev_word
                self.tapestry.save_full_state(os.path.join(state_dir, "guala_tapestry.pkl.gz"))
        except Exception as _te:
            _save_failures.append(("guala_tapestry.pkl.gz", str(_te)))
            print(f"[GualaLoom] save failed for guala_tapestry.pkl.gz: {_te}")

        # Picture grids — incremental + per-item isolation.
        # Grids are immutable post-upload (same pid = same 64×64 content).
        # Skip existing files with correct size to avoid hammering EFS.
        pic_dir = os.path.join(state_dir, "pictures")
        os.makedirs(pic_dir, exist_ok=True)
        _GRID_BYTES = 32896  # 64×64 float64 array + numpy header ≈ 32896 B
        _grids_t0 = time.time()
        for pid, grid in snap_pic_grids.items():
            if grid is None:
                continue
            grid_path = os.path.join(pic_dir, f"{pid}.npy")
            try:
                if os.path.exists(grid_path) and os.path.getsize(grid_path) == _GRID_BYTES:
                    continue  # already on EFS, skip
                np.save(grid_path, grid)
            except Exception as _ge:
                _save_failures.append((f"pictures/{pid}.npy", str(_ge)))
                print(f"[GualaLoom] save failed for pictures/{pid}.npy: {_ge}")
        results["_grids_dt"] = time.time() - _grids_t0

        # GL-CMD-PERSIST-FIX-74: mark survival based on critical-file success only.
        _critical = {"guala_core.json", "guala_needs.json", "guala_coordinator.json",
                     "guala_sections.json", "guala_atlas.json"}
        _critical_failures = [(f, e) for f, e in _save_failures if f in _critical]
        if not _critical_failures:
            self._last_save_tick = save_tick
            self._last_cold_save_tick = save_tick  # GL-CMD-DEEP-STORE-PHYSICS-86 P2
            self._last_save_timestamp = ts
            if _save_failures:
                self._log_substrate_event("save_partial",
                                          tick=save_tick,
                                          failed_files=[f for f, _ in _save_failures])
        else:
            self._log_substrate_event("save_critical_failure",
                                      tick=save_tick,
                                      failed_files=[f for f, _ in _critical_failures])
            print(f"[GualaLoom] CRITICAL SAVE FAILURE at tick {save_tick}: "
                  f"{[f for f, _ in _critical_failures]}")

        # GL-CMD-DEEP-ATLAS-PERSIST: emit save confirmation event
        _n_deep = self.deep_atlas.live_count()
        self._log_substrate_event("deep_atlas_saved",
                                  tick=save_tick, n_entries=_n_deep,
                                  state_dir=state_dir)

        # S3 backup handled by SaveCoordinator (non-blocking background thread)

        return results

    def _save_wave_atlas(self, state_dir):
        """GL-CMD-WAVE-SEMANTICS-85 Part C.1: persist WaveAtlas as numpy .npz.
        Much smaller than JSON after Part B.3 migration (~8-25k bindings → <5MB).
        Falls back to JSON if npz write fails (non-fatal in both cases)."""
        if self.wave_atlas is None:
            return
        try:
            n_cells = len(self.wave_atlas.cells)
            n_bind = sum(len(c.bindings) for c in self.wave_atlas.cells.values())
            npz_path = os.path.join(state_dir, "wave_atlas.npz")
            tmp_path = npz_path + ".tmp"
            self.wave_atlas.to_npz(tmp_path)
            # GL-RPT-PERSIST-FIX-74 discipline: fsync data + directory before rename
            with open(tmp_path, "rb") as _f:
                os.fsync(_f.fileno())
            _dir_fd = os.open(state_dir, os.O_RDONLY)
            try:
                os.fsync(_dir_fd)
            finally:
                os.close(_dir_fd)
            os.rename(tmp_path, npz_path)
            file_mb = os.path.getsize(npz_path) / 1e6
            print(f"[GualaLoom] WaveAtlas saved (npz): {n_cells} cells, "
                  f"{n_bind} bindings, {file_mb:.1f}MB")
        except Exception as _we:
            print(f"[GualaLoom] WaveAtlas npz save failed (non-fatal): {_we}")

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
            self.organism.identity_uuid = self._guala_identity  # GL-CMD-175 P1
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
        self.organism.identity_uuid = self._guala_identity  # GL-CMD-175 P1
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

            # GL-CMD-175 P1: restore the organism (full-fidelity, GL-CMD-169's
            # save_full_state/load_full_state -- pickle of the whole object
            # graph, so growth/folding/DNA/bindings all round-trip, not just
            # a hand-picked subset). Absence at boot means either a true
            # first boot (organism from __init__ stands, freshly born under
            # her now-synced identity) or a pre-175 state directory (same
            # honest fresh-organism outcome) -- never an error, per the
            # same "no silent fallback for a MISSING file" reasoning
            # deep_atlas/survival/teaching above already use.
            organism_path = os.path.join(state_dir, "guala_organism.pkl.gz")
            if os.path.exists(organism_path):
                try:
                    self.organism = type(self.organism).load_full_state(organism_path)
                    if self.organism.identity_uuid != self._guala_identity:
                        # G-2-class anomaly: her identity is authoritative
                        # (_load_identity, above) -- never let a mismatched
                        # organism silently pass as a second identity.
                        print(f"[GualaLoom] WARNING: organism identity "
                              f"{self.organism.identity_uuid} != her identity "
                              f"{self._guala_identity} -- correcting to hers")
                        self.organism.identity_uuid = self._guala_identity
                    print(f"[GualaLoom] Organism restored: identity={self.organism.identity_uuid} "
                          f"tick={self.organism.tick} pop="
                          f"{sum(len(h.cluster.neurons) for h in self.organism.brain.hemispheres)}")
                except Exception as e:
                    print(f"[GualaLoom] Organism restore FAILED (organism from boot stands): {e}")
            else:
                print("[GualaLoom] No guala_organism.pkl.gz — organism starts fresh this boot")

            # GL-NOTE-VOICE-WIRING-RULING W1: restore the tapestry alongside
            # the organism -- same honest-fresh-on-absence reasoning.
            tapestry_path = os.path.join(state_dir, "guala_tapestry.pkl.gz")
            if os.path.exists(tapestry_path):
                try:
                    self.tapestry = type(self.tapestry).load_full_state(tapestry_path)
                    # GL-195: restore the emission query source (see save).
                    _pw = getattr(self.tapestry, "_engine_prev_word", None)
                    if _pw:
                        self._tapestry_prev_word = _pw
                    print(f"[GualaLoom] Tapestry restored: tick={self.tapestry._tick} "
                          f"neurons={self.tapestry.total_neurons} "
                          f"prev_word={'set' if _pw else 'none'}")
                except Exception as e:
                    print(f"[GualaLoom] Tapestry restore FAILED (tapestry from boot stands): {e}")
            else:
                print("[GualaLoom] No guala_tapestry.pkl.gz — tapestry starts fresh this boot")

            # GL-CMD-HOTLANE-DIET-102: load survival history from own cold file.
            # _apply_core() already set _deep_survival_history from core.json's field
            # (backward compat). If guala_survival.json exists, it overrides that.
            survival_path = os.path.join(state_dir, "guala_survival.json")
            if os.path.exists(survival_path):
                try:
                    with open(survival_path) as fh:
                        sraw = json.load(fh)
                    sdata = sraw.get("data", sraw)
                    surv_raw = sdata.get("deep_survival_history", {})
                    self._deep_survival_history = defaultdict(list)
                    for key_str, strengths in surv_raw.items():
                        parts = key_str.split("|", 2)
                        if len(parts) == 3:
                            chi_k = int(parts[0]) if parts[0].lstrip('-').isdigit() else parts[0]
                            self._deep_survival_history[(chi_k, parts[1], int(parts[2]))] = strengths
                    print(f"[GualaLoom] Survival history loaded from guala_survival.json: "
                          f"{len(self._deep_survival_history)} entries")
                except Exception as e:
                    print(f"[GualaLoom] Survival history load FAILED: {e} — using core.json fallback")
            else:
                _sc = len(self._deep_survival_history)
                print(f"[GualaLoom] No guala_survival.json — survival history from core.json "
                      f"fallback ({_sc} entries)")

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
                    # GL-194: motifs live in their own cold file now.
                    # Prefer it; fall back to legacy inline sight_motifs
                    # (pre-194 saves) so no on-disk state is stranded.
                    sm_path = os.path.join(state_dir, "guala_sight_motifs.json")
                    if os.path.exists(sm_path):
                        try:
                            with open(sm_path) as fh2:
                                smraw = json.load(fh2)
                            smdata = smraw.get("data", smraw)
                            vdata["sight_motifs"] = smdata.get("sight_motifs", [])
                        except Exception as _sme:
                            print(f"[GualaLoom] sight_motifs load failed, "
                                  f"using inline legacy if any: {_sme}")
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

            # GL-CMD-RECALL-WORD-INDEX-57 §1.4: rebuild reverse word→chi index from atlas
            n_indexed = 0
            from collections import defaultdict as _dd
            self._word_to_chi_index = _dd(set)
            for chi_k, entries in self.atlas.entries.items():
                for e in entries:
                    sec = self.sections.get(e.get("section", ""))
                    if sec:
                        mid = e.get("motif", 0)
                        if mid < len(sec.modes):
                            _, _, w = sec.modes[mid]
                            if w:
                                self._word_to_chi_index[w.lower()].add(chi_k)
                                n_indexed += 1
            print(f"[GualaLoom] Recall word index rebuilt: {len(self._word_to_chi_index)} words, {n_indexed} entries")

            # 64-C / 85-C1/R2: WaveAtlas — try .npz first, then .json fallback.
            # R2: collapse-on-load after every load (idempotent; correctness
            # must not depend on the manual migrate_wave_atlas endpoint).
            if self.wave_atlas is not None:
                _wave_npz = os.path.join(state_dir, "wave_atlas.npz")
                _wave_json = os.path.join(state_dir, "wave_atlas.json")
                _wave_loaded = False

                if os.path.exists(_wave_npz):
                    try:
                        n_cells = self.wave_atlas.load_from_npz(_wave_npz)
                        print(f"[GualaLoom] WaveAtlas loaded from disk (npz): {n_cells} cells, "
                              f"{self.wave_atlas.binding_count()} bindings")
                        _wave_loaded = True
                    except Exception as _wle:
                        print(f"[GualaLoom] WaveAtlas npz load failed ({_wle}), trying json")

                if not _wave_loaded and os.path.exists(_wave_json):
                    try:
                        import json as _wjson
                        with open(_wave_json, "r") as _wf:
                            _raw_bytes = _wf.read()
                        n_cells = self.wave_atlas.load_from_dict(_wjson.loads(_raw_bytes))
                        print(f"[GualaLoom] WaveAtlas loaded from disk (json): {n_cells} cells, "
                              f"{self.wave_atlas.binding_count()} bindings")
                        _wave_loaded = True
                        # R2: async S3 archive of raw json before first npz save
                        def _archive_json_to_s3(_rb=_raw_bytes.encode("utf-8")):
                            try:
                                import boto3 as _b3, gzip as _gz, time as _t
                                _s3 = _b3.client("s3", region_name="us-east-1")
                                _ts = _t.strftime("%Y-%m-%d_%H-%M-%S", _t.gmtime())
                                _gz_bytes = _gz.compress(_rb, compresslevel=6)
                                _s3.put_object(
                                    Bucket="dsf-ai-site-backups",
                                    Key=f"guala/wave_migrate_pre/{_ts}_wave_atlas_raw_boot.json.gz",
                                    Body=_gz_bytes,
                                    ContentType="application/gzip",
                                )
                                print(f"[wave] json fallback archived to S3 ({len(_gz_bytes)/1e6:.1f}MB)")
                            except Exception as _ae:
                                print(f"[wave] json S3 archive failed (non-fatal): {_ae}")
                        import threading as _thr
                        _thr.Thread(target=_archive_json_to_s3, daemon=True).start()
                    except Exception as _wle:
                        print(f"[GualaLoom] WaveAtlas json load failed ({_wle}), rebuilding")

                if not _wave_loaded:
                    # First boot after WaveAtlas enabled — rebuild once
                    self.wave_atlas.rebuild_from(self.atlas)
                    print(f"[GualaLoom] WaveAtlas rebuilt from LivingAtlas (one-time): "
                          f"{self.wave_atlas.cell_count()} cells, "
                          f"{self.wave_atlas.binding_count()} bindings")

                # R2: collapse-on-load (idempotent; near-free post-migration)
                _pre_col = self.wave_atlas.binding_count()
                _col_r = self.wave_atlas.collapse_by_key()
                _post_col = _col_r["after"]
                print(f"[wave] collapse-on-load: {_pre_col}→{_post_col} bindings "
                      f"(wired={self.atlas._wave_atlas is self.wave_atlas})")

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
        self.last_autonomous_emission_tick = int(core.get("last_autonomous_emission_tick", -100_000))
        self.last_autonomous_attempt_tick = int(core.get("last_autonomous_attempt_tick", -100_000))
        self.autonomous_emissions_count = int(core.get("autonomous_emissions_count", 0))
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
        # GL-CMD-CREDO-LOOP-REPAIR-167 Change 2 + Joe's boot-init directive:
        # dream_pressure was never persisted before this fix (see the save
        # side) -- restore it normally if present. On the first boot where
        # it's absent, initialize it from her actual accumulated backlog,
        # not a fresh 0.0: the debt is real, the gauge should start honest.
        # No historical per-tick activity log survives across boots to
        # replay exactly, so this uses attendance-ticks (self.tick, her
        # whole recorded lifetime) against the same DP_RATE_PER_ATTEND_TICK
        # the ongoing accumulator uses -- the honest assumption given this
        # session's own evidence found no executed dream tick, ever, in
        # her recorded history (-165, -167 Q6, Joe's two live force_dream
        # tests). Atlas-write backlog is NOT included here: _apply_atlas
        # runs after this in the restore sequence, so self.atlas isn't
        # populated yet at this point -- ticks alone already exceed the
        # 1.0 ceiling by a wide margin, so this omission doesn't change
        # the computed value. Clipped to 1.0 same as the ongoing model.
        if "dream_pressure" in nd:
            self.needs.dream_pressure = float(nd["dream_pressure"])
        else:
            _boot_backlog = min(1.0, self.tick * DP_RATE_PER_ATTEND_TICK)
            self.needs.dream_pressure = _boot_backlog
            print(f"[dream-pressure-init] persisted dream_pressure absent -- "
                  f"initialized from real backlog: tick={self.tick} -> "
                  f"dream_pressure={_boot_backlog:.4f} "
                  f"(GL-CMD-CREDO-LOOP-REPAIR-167)")
            self._log_substrate_event("dream_pressure_boot_init",
                                      tick=self.tick,
                                      computed_dream_pressure=round(_boot_backlog, 4))
        # GL-CMD-TURN-LATENCY-EVE-20260705-197 P4: last-dream marker restore.
        # Absent on the first boot before this fix ever saved it (or if she
        # has genuinely never dreamed yet) -- None is the honest value, not
        # a guess. dream_pressure itself is restored above, UNCHANGED by
        # this -- the marker is a complementary fact, not a substitute.
        self._last_real_dream_tick = nd.get("last_real_dream_tick")
        print(f"[dream-marker-restore] last_real_dream_tick="
              f"{self._last_real_dream_tick!r} dream_pressure="
              f"{self.needs.dream_pressure:.4f} (GL-CMD-TURN-LATENCY-197 P4)")

    def _apply_coordinator(self, cd):
        # v6-bridge: per-source pair bonds
        pb = cd.get("pair_bond", cd.get("pair_bond_state", None))
        if isinstance(pb, dict):
            self.coordinator._pair_bond = {"joe": pb.get("joe", True),
                                            "joe_voice": pb.get("joe_voice", True),
                                            "wc": pb.get("wc", True),
                                            "c1": pb.get("c1", False)}
        else:
            # Old-style: single bool. Restore Joe=True, wC=True per manifesto.
            old_active = cd.get("pair_bond_active", True)
            self.coordinator._pair_bond = {"joe": True, "joe_voice": True,
                                            "wc": True, "c1": False}
            if not old_active:
                print("[GualaLoom] PAIR-BOND REGRESSION: old state had pair_bond_active=False. "
                      "Root cause: retirement check fired during corpus-only reading. "
                      "Restoring Joe=True, activating wC=True.")
        self.coordinator.distress_ticks = cd.get("distress_ticks", 0)
        self.coordinator.suffering_log = cd.get("suffering_log", [])
        self.coordinator.need_history = cd.get("need_history", [])[-200:]
        # 60-K: restore interaction log (list of [tick, salience] from JSON)
        raw_log = cd.get("source_interaction_log", {})
        merged_log = {
            src: [(int(t), float(s)) for t, s in entries]
            for src, entries in raw_log.items()
        }
        # GL-CMD-VOICE-IDENTITY-FIX-JOE-20260704: one-time migration. Any
        # "joe_voice" interaction history accumulated before this fix (the
        # separate person the pair-bond table had grown) merges into "joe"'s
        # log here, once, at load -- same identity, same relationship,
        # channel-tagging elsewhere (atlas entries, provenance) is untouched.
        # After this boot, _record_interaction/pair_bond_strength normalize
        # "joe_voice" to "joe" at write/read time, so this key never
        # reappears; this merge only ever fires once, on the first load of
        # state saved before the fix.
        voice_log = merged_log.pop("joe_voice", None)
        if voice_log:
            combined = merged_log.get("joe", []) + voice_log
            combined.sort(key=lambda t_s: t_s[0])
            merged_log["joe"] = combined
        self.coordinator._source_interaction_log = merged_log

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
        print(f"[GualaLoom] _apply_visual: {len(vd.get('pictures',{}))} pictures, {len(vd.get('sight_motifs',[]))} motifs in data")
        from dsf_ai_service.visual_krimelack import VisualMotif
        pic_dir = os.path.join(state_dir, "pictures")
        # Restore pictures
        for pid, pdata in vd.get("pictures", {}).items():
            try:
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
                orig_path = pdata.get("original_path")
                if orig_path and os.path.exists(orig_path):
                    pic.original_path = orig_path
                    pic.original_width = pdata.get("original_width")
                    pic.original_height = pdata.get("original_height")
                self._pictures[pid] = pic
            except Exception as _pe:
                print(f"[GualaLoom] picture load failed for {pid}: {_pe}")
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
            line = json.dumps(entry)
            with open(path, "a") as f:
                f.write(line + "\n")
            # GL-CMD-EVENT-RETENTION-FIX-172 R4: mirror to stdout so the
            # unlimited-retention CloudWatch log group becomes a backstop
            # independent of events.log's own (crash-replay-sized) window.
            # Whitelist-governed by construction: log_event is only ever
            # called for the 12 whitelisted kinds (_log_substrate_event)
            # plus this same explicit call path — no new per-tick spam.
            print(f"[GualaLoom][diary-mirror] {line}", flush=True)
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
                # GL-CMD-WAVE-DIET-82: clamp replayed budget to canonical value.
                # Hardcoded 2000 gave EMITTING 2000 ticks instead of its 100-tick
                # budget, causing 33-min lock-hold that starved the save cycle.
                _budget = ACTIVITY_TICK_BUDGETS.get(kind, 2000)
                self._current_activity = Activity(
                    kind=kind, target=target,
                    started_tick=ev.get("tick", self.tick),
                    expected_end_tick=ev.get("tick", self.tick) + _budget)
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

    # ── Diary (GL-CMD-EVENT-RETENTION-FIX-172 R1-R3) ──
    # A durable, full-width, append-only record — separate from EVENTS_LOG
    # above. events.log/compact_events/_replay_events (crash replay) are
    # completely untouched by everything below: different file tree
    # (DIARY_DIR), different write path, never compacted.

    def _diary_worker_loop(self, state_dir):
        """Single persistent background writer — NOT one thread per event.
        The existing whitelist path (_log_substrate_event -> log_event)
        spawns a thread per whitelisted event; doing that for ALL ~40+
        event kinds (R3's full width, some of which are high-frequency
        per-tick kinds) would risk thread-creation overhead becoming its
        own live-path regression, independent of disk I/O cost. One queue,
        one worker, matches the existing SaveCoordinator S3-queue
        convention (save_coordinator.py) rather than inventing a new
        pattern."""
        while True:
            item = self._diary_queue.get()
            if item is None:
                return
            event_kind, detail, tick, ts = item
            self._write_diary_entry(state_dir, event_kind, detail, tick, ts)

    def _ensure_diary_worker(self, state_dir):
        if self._diary_queue is not None:
            return
        with self._diary_worker_lock:
            if self._diary_queue is not None:   # re-check: lost a race to another thread
                return
            self._diary_queue = _queue.Queue(maxsize=4000)
            t = threading.Thread(target=self._diary_worker_loop, args=(state_dir,),
                                 daemon=True, name="diary-writer")
            t.start()
            self._diary_thread = t

    def enqueue_diary_event(self, state_dir, event_kind, detail, tick, ts):
        """R3: called for EVERY substrate event kind (not just the 12-kind
        disk whitelist) — non-blocking, drops under back-pressure rather
        than ever stalling the caller (same never-crash-substrate
        contract as log_event)."""
        try:
            self._ensure_diary_worker(state_dir)
            self._diary_queue.put_nowait((event_kind, dict(detail), tick, ts))
        except _queue.Full:
            pass
        except Exception:
            pass

    def _diary_path_for_date(self, state_dir, date_str):
        return os.path.join(state_dir, self.DIARY_DIR, f"{date_str}.log")

    def _diary_prune(self, state_dir):
        """R2: retention enforced by deleting whole files older than
        DIARY_RETENTION_DAYS at rotation (day-boundary crossing) — never
        by rewriting a live file, unlike compact_events' in-place model."""
        diary_dir = os.path.join(state_dir, self.DIARY_DIR)
        if not os.path.isdir(diary_dir):
            return
        cutoff_epoch = time.time() - self.DIARY_RETENTION_DAYS * 86400
        for fname in os.listdir(diary_dir):
            if not fname.endswith(".log"):
                continue
            try:
                file_epoch = calendar.timegm(time.strptime(fname[:-4], "%Y-%m-%d"))
            except ValueError:
                continue
            if file_epoch < cutoff_epoch:
                try:
                    os.remove(os.path.join(diary_dir, fname))
                except OSError:
                    pass

    def _write_diary_entry(self, state_dir, event_kind, detail, tick, ts):
        """R1/R3: append one JSON line to TODAY's dated diary file. Runs on
        the single diary-writer thread only — never on the caller's stack.
        Best-effort: a bad detail dict degrades to a stringified entry
        (json.dumps(..., default=str)) rather than silently dropping the
        event, since R3 explicitly widens the record to kinds that were
        never JSON-serialized before and may hold non-serializable values."""
        date_str = ts[:10]
        diary_dir = os.path.join(state_dir, self.DIARY_DIR)
        path = self._diary_path_for_date(state_dir, date_str)
        entry = {"type": event_kind, "tick": tick, "ts": ts}
        entry.update(detail)
        try:
            os.makedirs(diary_dir, exist_ok=True)
            with open(path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
            if date_str != self._diary_last_date:
                self._diary_last_date = date_str
                self._diary_prune(state_dir)
        except Exception:
            pass  # diary is best-effort, same never-crash-substrate contract as log_event

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
        # GL-CMD-WAVE-DIET-82: save WaveAtlas before snapshot
        # GL-CMD-SAVE-CONTAINMENT-91: wrap — file copy loop must continue regardless
        try:
            self._save_wave_atlas(state_dir)
        except Exception as _wse:
            print(f"[wave] save failed (non-fatal): {_wse}")
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
        """Cross-check loaded state for internal consistency.
        GL-FIX-ATLAS-INTEGRITY: OOB atlas entries are pruned (not just logged)."""
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
        # 4. Atlas motif IDs reference existing modes — prune OOB entries
        pruned = 0
        sample_count = 0
        for chi_val in list(self.atlas.entries.keys()):
            entries = self.atlas.entries[chi_val]
            valid = []
            for e in entries:
                sec_name = e.get("section")
                motif_id = e.get("motif")
                if sec_name in self.sections and motif_id is not None:
                    if motif_id >= len(self.sections[sec_name].modes):
                        if sample_count < 10:
                            errors.append(f"Atlas refs motif {motif_id} in {sec_name} "
                                          f"(has {len(self.sections[sec_name].modes)})")
                        sample_count += 1
                        pruned += 1
                        continue  # drop this entry
                valid.append(e)
            self.atlas.entries[chi_val] = valid
        if sample_count >= 10:
            errors.append(f"(... and {sample_count - 10} more OOB entries, {pruned} total pruned)")
        elif pruned > 0:
            errors.append(f"({pruned} OOB atlas entries pruned)")
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
            # GL-CMD-PERSIST-FIX-74: always flush before rename. On EFS (NFSv4)
            # the kernel page cache is not flushed to the server at close() time,
            # so os.rename finds no tmp file (ENOENT) despite it being written.
            # f.flush() pushes Python buffer to OS; fsync() commits to NFS server.
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp, path)

    # ── Persistence health for /status ──

    # D6: report-only files (not boot-required, but tracked for health)
    REPORT_FILES = ["guala_deep_atlas.json", "guala_visual.json",
                     "guala_sight_motifs.json",  # GL-194
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
            "last_cold_save_tick": self._last_cold_save_tick,
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
            "pair_bond": self.coordinator.pair_bond_snapshot(current_tick=self.tick),
            # GL-CMD-SCENE-LANES-B1-188 V5: real WHERE/AMBIENT of the most
            # recently read sentence (any source -- book, converse, corpus),
            # surfaced live for loomscan's place/ambient panels. Empty lists
            # are honest ("this sentence had no recognized scene word"), not
            # an error -- same "no lanes yet" honesty the panel already had,
            # now driven by real data instead of a hardcoded string.
            "scene_lanes": {
                "place": getattr(self, "_last_place_tags", None) or [],
                "ambient": getattr(self, "_last_ambient_tags", None) or [],
            },
            # GL-CMD-BRAIN-GROWTH-UNFREEZE-EVE-20260704-179, Eve's
            # backgrounding ruling: "dropped/queued counts visible in
            # status" -- experience_word()'s ~255ms/word cost (22.3x
            # organism.remember()'s own, see the -179 report) means this
            # queue is the one to actually watch for backlog/drops.
            "organism_worker": {
                "queued": (self._organism_queue.qsize()
                          if self._organism_queue is not None else 0),
                "dropped": self._organism_dropped_count,
            },
            # GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1 item 3: "no direct live
            # population counter exists... recommending a field get added
            # next to organism_worker" -- built here. Real neuron count,
            # not a proxy: the -179 exit condition promised population
            # visibility, this is what makes recall_ms's rise (12-21ms ->
            # 152.8ms, live-observed as growth's first indirect evidence)
            # directly confirmable instead of inferred.
            "organism_population": sum(len(h.cluster.neurons)
                                       for h in self.organism.brain.hemispheres),
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
