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
  - Honest SafeMode: when the field does not commit, remain silent.
  - Fixed math parser: handles multi-word numbers (ten thousand, five hundred)
    via state machine. Fails honestly on mixed word+digit input rather than
    returning partial garbage.

Six capabilities (now meaningful):
  1. Syntax — keyhole cascade with role differentiation
  2. Conversation — speech only from committed substrate settlement
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
import contextlib
import functools
import queue as _queue
import hashlib as _hashlib
import heapq as _heapq
import threading
import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from collections import deque
import random


def _engine_mutation_entry(method):
    """Make one public engine mutation participate in quiescence admission.

    The underlying scope is re-entrant per thread, so public entry points may
    call one another without double-counting or being rejected midway through
    an already-admitted operation.
    """
    @functools.wraps(method)
    def guarded(self, *args, **kwargs):
        with self._engine_mutation_scope(method.__name__):
            return method(self, *args, **kwargs)
    return guarded


def saturate(current, gain):
    """Asymptotic receptor saturation. As current → 1.0, effective gain → 0.
    GL-BRIEF-NEEDS-PHYSICS: prevents needs from pinning at ceiling."""
    return max(0.0, min(1.0, current + gain * (1.0 - current)))


class GualaBootIdentityUnreadableHalt(RuntimeError):
    """NAMED loud halt (P4): guala_identity.json exists but cannot be read/
    parsed.  The one boot method (GL-SPC-SUBSTRATE-TRUE §boot) has exactly
    three identity outcomes: present -> continue, absent -> genesis,
    unreadable -> THIS halt.  Never silently re-genesis over a real identity."""


class GualaBootStateIntegrityHalt(RuntimeError):
    """NAMED loud halt (P4): the state directory is internally inconsistent
    at boot (identity present with state files vanished, or state files
    present without an identity).  No flag overrides this; recovery is the
    operator's explicit restore command (tools/restore_from_s3.py), run while
    the service is stopped."""


@dataclass(frozen=True)
class ConversationTurnResult:
    """Immutable truth produced by one complete conversation turn."""

    response: str
    response_source: str
    emission_id: str | None = None
    committed_sections: tuple = ()
    recalled_pictures: tuple = ()
    source_turn_index: int | None = None
    commit_provenance: tuple = ()


@dataclass(frozen=True)
class EmissionCandidateProvenance:
    """Exact candidate attribution carried by a committed installed mode."""

    section: str
    mode_id: int
    word: str
    source: str | None = None
    origin: str | None = None
    chi: object = None
    sensory_refs: tuple = ()
    episode_refs: tuple = ()
    bundle_ids: tuple = ()
    window_id: str | None = None
    window_entry_index: int | None = None
    trace_id: str | None = None
    source_strand_id: str | None = None
    structural_fingerprint: str | None = None
    modalities: tuple = ()

    def as_record(self):
        return {
            "section": self.section,
            "mode_id": self.mode_id,
            "word": self.word,
            "source": self.source,
            "origin": self.origin,
            "chi": self.chi,
            "sensory_refs": list(self.sensory_refs),
            "episode_refs": list(self.episode_refs),
            "bundle_ids": list(self.bundle_ids),
            "window_id": self.window_id,
            "window_entry_index": self.window_entry_index,
            "trace_id": self.trace_id,
            "source_strand_id": self.source_strand_id,
            "structural_fingerprint": self.structural_fingerprint,
            "modalities": list(self.modalities),
        }


@dataclass(frozen=True)
class EmissionSettlement:
    """Turn-local result of one assemblage emission settlement."""

    content: str = ""
    committed_sections: tuple = ()
    n_commits: int = 0
    organ_in_commits: bool = False
    tick: int = 0
    commit_provenance: tuple = ()


@dataclass(frozen=True)
class FactEmissionSupport:
    """One exact closed-window entry supporting one emitted Fact token."""

    window_id: str
    entry_index: int
    experience_origin: str
    source_tag: str
    trace_id: str
    source_strand_id: str
    modalities: tuple

    def as_record(self):
        return {
            "window_id": self.window_id,
            "entry_index": self.entry_index,
            "experience_origin": self.experience_origin,
            "source_tag": self.source_tag,
            "trace_id": self.trace_id,
            "source_strand_id": self.source_strand_id,
            "modalities": list(self.modalities),
        }


@dataclass(frozen=True)
class FactEmissionTokenProvenance:
    """Full structural class and every exact occurrence behind one token."""

    word: str
    structural_fingerprint: str
    recognized_strand_ids: tuple
    supports: tuple

    def as_record(self):
        return {
            "authority": "language_fact_strand_reciprocity_v1",
            "word": self.word,
            "structural_fingerprint": self.structural_fingerprint,
            "recognized_strand_ids": list(self.recognized_strand_ids),
            "supports": [support.as_record() for support in self.supports],
        }


def _provenance_tuple(value):
    """Freeze an existing metadata value without inferring missing entries."""
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


_CANDIDATE_PROVENANCE_KEYS = (
    "source", "origin", "chi", "sensory_refs",
    "episode_ref", "episode_refs", "bundle_id", "bundle_ids",
)


def _candidate_provenance_evidence(record, origin=None):
    """Copy only provenance evidence that an upstream record actually has."""
    evidence = {
        key: record[key]
        for key in _CANDIDATE_PROVENANCE_KEYS
        if key in record
    }
    if origin is not None:
        evidence["origin"] = origin
    return evidence


def _freeze_candidate_provenance(candidate, section, mode_id):
    evidence = candidate.get("_provenance_evidence")
    if not isinstance(evidence, dict):
        evidence = _candidate_provenance_evidence(candidate)
    episode_refs = _provenance_tuple(evidence.get("episode_refs"))
    if not episode_refs:
        episode_refs = _provenance_tuple(evidence.get("episode_ref"))
    bundle_ids = _provenance_tuple(evidence.get("bundle_ids"))
    if not bundle_ids:
        bundle_ids = _provenance_tuple(evidence.get("bundle_id"))
    return EmissionCandidateProvenance(
        section=section,
        mode_id=mode_id,
        word=candidate.get("word") or "",
        source=evidence.get("source"),
        origin=evidence.get("origin"),
        chi=evidence.get("chi"),
        sensory_refs=_provenance_tuple(evidence.get("sensory_refs")),
        episode_refs=episode_refs,
        bundle_ids=bundle_ids)


def _committed_candidate_provenance(selected_commits, installed_provenance):
    """Return attribution only for the exact commits rendered as words.

    A section can commit more than once while settling, but emission rendering
    selects one final mapped mode per section and can then suppress that word
    when it repeats the input or an earlier rendered word.  Attribution must
    follow that rendered selection rather than every transient dynamics
    commit, or an earlier displaced candidate can falsely certify the utterance.
    """
    committed = []
    for commit in selected_commits:
        matches = tuple(
            provenance
            for provenance in installed_provenance.get(
                (commit["section"], commit["mode_id"]), ())
            if provenance.word == commit["word"])
        if len(matches) != 1:
            return ()
        committed.append(matches[0])
    return tuple(committed)


def _provenance_has_lived_link(provenance):
    if not isinstance(provenance, EmissionCandidateProvenance):
        return False
    if not isinstance(provenance.source, str) or not provenance.source.strip():
        return False
    if not isinstance(provenance.origin, str) or not provenance.origin.strip():
        return False
    return any(
        ref is not None and ref != ""
        for refs in (provenance.sensory_refs,
                     provenance.episode_refs,
                     provenance.bundle_ids)
        for ref in refs)


def _settlement_has_certified_provenance(settlement):
    if not isinstance(settlement, EmissionSettlement):
        return False
    provenance = settlement.commit_provenance
    sections = settlement.committed_sections
    if (settlement.n_commits <= 0
            or settlement.n_commits != len(sections)
            or settlement.n_commits != len(provenance)):
        return False
    for section, item in zip(sections, provenance):
        if (not _provenance_has_lived_link(item)
                or item.section != section
                or not isinstance(item.mode_id, int)
                or item.mode_id < 0
                or not item.word):
            return False
    if settlement.content != " ".join(item.word for item in provenance):
        return False
    has_organ = any(item.origin == "organ" for item in provenance)
    return settlement.organ_in_commits is has_organ


def _record_has_certified_provenance(record):
    if not isinstance(record, dict):
        return False
    provenance = record.get("commit_provenance")
    sections = record.get("committed_sections")
    n_commits = record.get("n_commits")
    if (not isinstance(provenance, list)
            or not isinstance(sections, list)
            or not isinstance(n_commits, int)
            or n_commits <= 0
            or n_commits != len(sections)
            or n_commits != len(provenance)):
        return False
    words = []
    has_organ = False
    for section, item in zip(sections, provenance):
        if not isinstance(item, dict):
            return False
        source = item.get("source")
        origin = item.get("origin")
        links = (
            _provenance_tuple(item.get("sensory_refs"))
            + _provenance_tuple(item.get("episode_refs"))
            + _provenance_tuple(item.get("bundle_ids")))
        if (not isinstance(source, str) or not source.strip()
                or not isinstance(origin, str) or not origin.strip()
                or item.get("section") != section
                or not isinstance(item.get("mode_id"), int)
                or item["mode_id"] < 0
                or not item.get("word")
                or not any(link is not None and link != "" for link in links)):
            return False
        words.append(item["word"])
        has_organ = has_organ or origin == "organ"
    expected_source = "v5_commit_organ" if has_organ else "v5_commit"
    return (record.get("text") == " ".join(words)
            and record.get("response_source") == expected_source)


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

    running_sum = 0j
    chosen_words = []
    last_coh = 0.0
    for i, (chi_addr, strength, word) in enumerate(pool):
        amp = complex(amps_vec[i])
        new_sum = running_sum + amp
        new_coh = abs(new_sum) ** 2
        gain = new_coh - last_coh
        # GL-RPT-COGNITION-AT-SPEED root-cause fix (post-incident, 2026-07-05):
        # gain must be checked as a FRACTION of the coherence already
        # present (ΔC/C > threshold, i.e. per-word-normalized coherence),
        # not an absolute constant and not even gain-vs-|S| (magnitude).
        # Absolute gain ~ 2|S||a| GROWS with |S| so an absolute floor can
        # never terminate -- once six emission sections widened the
        # candidate pool, every candidate cleared the old fixed bar,
        # producing an unbounded accept run (49s-94s settle latency, live
        # incident). Note gain-vs-|S| (magnitude, not squared) was tried
        # first and measured to NOT be enough: in a fully-coherent pool it
        # degenerates to a constant per-word bar independent of pool size,
        # so a large aligned pool still selects ~all of it (verified:
        # 9333/20000 and 10820/20000 in an offline sweep). Gain-vs-C
        # (squared/fractional) gives a genuine bound even in the
        # worst-case fully-aligned pool (k < 2/MIN_GAIN_THRESHOLD = 20,
        # independent of n) -- termination is the coherence physics
        # itself, not a word-count cap (Joe's no-caps ruling stays intact,
        # see GL-CMD-NO-CAPS-COHERENCE-SPEAKS-EVE-20260705-203 -- nothing
        # here caps word count, the physics just naturally stops adding).
        # Running-sum accumulator (was `sum(chosen_amps, 0j)` re-summed
        # from scratch every candidate, O(n*k)) also collapses to O(1)
        # per candidate here.
        if gain > MIN_GAIN_THRESHOLD * last_coh:
            chosen_words.append(word)
            running_sum = new_sum
            last_coh = new_coh
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

    running_sum = 0j
    chosen_words = []
    last_coh = 0.0
    for i, (chi_addr, strength, word) in enumerate(pool):
        amp = complex(amps_vec[i])
        new_sum = running_sum + amp
        new_coh = abs(new_sum) ** 2
        gain = new_coh - last_coh
        # Fractional relative-gain stopping rule (ΔC/C > threshold) + O(1)
        # running accumulator -- see the matching comment in
        # _grandurun_select_multichi above.
        if gain > MIN_GAIN_THRESHOLD * last_coh:
            chosen_words.append(word)
            running_sum = new_sum
            last_coh = new_coh
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
    last_mag_sq = 0.0  # |composition_sum|^2 -- "coherence density already present"

    # Sort by chi_resonance magnitude (dim 0) as proxy for strength
    pool = sorted(candidates, key=lambda c: -abs(c[0][0]))

    for state_vec, word in pool:
        new_sum = composition_sum + state_vec
        # Re(<composition_sum, candidate>) — inner product alignment
        alignment = float(_np.real(_np.vdot(new_sum, state_vec)))
        gain = alignment - last_alignment
        # GL-RPT-COGNITION-AT-SPEED root-cause fix: same disease as the
        # scalar selectors -- alignment scales with |composition_sum|, so
        # an absolute gain floor never terminates once the pool is large.
        # A gain-vs-magnitude bar was tried first and measured insufficient
        # (degenerates to a constant per-word bar in a fully-coherent pool,
        # so a large aligned pool still selects nearly all of it). Scaling
        # by the squared magnitude instead (ΔC/C fractional form, matching
        # the scalar-selector fix) gives a genuine bound even in the
        # worst-case fully-aligned pool, independent of pool size -- word
        # count stays uncapped (Joe's ruling, -203) but termination is now
        # the coherence physics itself, not a length fence.
        if gain > MIN_GAIN_THRESHOLD * last_mag_sq:
            chosen_words.append(word)
            chosen_vecs.append(state_vec)
            composition_sum = new_sum
            last_alignment = alignment
            last_mag_sq = float(_np.real(_np.vdot(composition_sum, composition_sum)))
        # GL-CMD-NO-CAPS-COHERENCE-SPEAKS-EVE-20260705-203 U0a: no length
        # ceiling here either -- same coherence-gain-only stopping rule.

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
    pending = []  # chi, strength, section, mode, word, physics, evidence
    seen = set()

    for de, co, clarity in deep_candidates:
        de_chi = de.get("chi", 0)
        physics_meta = {
            "arousal": de.get("arousal", 0.5),
            "valence": de.get("valence", 0.0),
            "surprise": de.get("surprise", 0.0),
            "polarity": de.get("polarity", 1.0),
        }
        provenance_evidence = _candidate_provenance_evidence(de)
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
                pending.append((de_chi, float(strength), sec_name, mid,
                                word_label, physics_meta,
                                provenance_evidence))

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
    for i, (de_chi, strength, sec_name, mid, word_label, physics_meta,
            provenance_evidence) in enumerate(pending):
        candidate = {
            "chi": de_chi,
            "section": sec_name,
            "motif": mid,
            "word": word_label,
            "strength": strength,
            "coherent_magnitude": float(coh_mags[i]),
            "_provenance_evidence": dict(provenance_evidence),
            **physics_meta,
        }
        if "source" in provenance_evidence:
            candidate["source"] = provenance_evidence["source"]
        if "origin" in provenance_evidence:
            candidate["origin"] = provenance_evidence["origin"]
        candidates.append(candidate)

    candidates.sort(key=lambda c: -c["coherent_magnitude"])
    # GL-CMD-SLOT-LIMITS-REMOVAL-EVE-20260707-v1: audited, NOT removed.
    # Initially looked like exactly the "[:N] truncation hiding candidates
    # from an otherwise-uncapped downstream selector" pattern this
    # dispatch targets -- but the comment on GRANDURUN_TOPK's own
    # definition (a few lines above this function, dated 2026-07-05,
    # GL-CMD-ENABLE-COGNITION-EVE-20260705-211) documents a real, prior,
    # carefully-reasoned finding: too many competing candidates measurably
    # breaks the emission commit step itself ("200 competing candidates
    # makes the settle-on-one-winner commit step nearly impossible"), not
    # just a performance cost. This is a real constraint on the emission
    # mechanism's own correctness, not an arbitrary slot limit -- kept
    # as-is. See the accompanying report.
    #
    # GRANDURUN_SECTION_FLOOR_ENABLED (default OFF, byte-identical to prior
    # behavior when off): a flat global top_k cut on one shared
    # coherent_magnitude ranking systematically starves whichever of the 6
    # _EMISSION_SECTIONS her learned vocabulary scores lower for this turn
    # (measured live: modifier/ground sat at 8-36% "capacity" vs 127-148%
    # for subject/verb/intro) -- those sections then get ZERO candidates,
    # so evidence_pressure==0, so Section.commit_check's evidence floor
    # (assemblage.py, "if evidence_pressure < 0.15: return False, None")
    # hard-blocks them regardless of keyhole excitation. Fix: reserve a
    # small per-section floor from each section's OWN best-scoring
    # candidates (same coherent_magnitude ordering, just filtered), then
    # fill the rest of top_k by the existing global ranking. This is a
    # redistribution of the same ranked candidate list, not synthetic
    # evidence -- a section with fewer real candidates than the floor just
    # contributes what it has.
    if os.environ.get("GRANDURUN_SECTION_FLOOR_ENABLED", "0") != "1":
        return candidates[:top_k]

    _FLOOR_SECTIONS = ("subject", "verb", "object", "modifier", "ground", "intro")
    # ~1/4 of top_k spread across the 6 sections, floor of 3 so even a
    # small top_k still guarantees every section a real shot.
    min_per_section = max(3, top_k // (len(_FLOOR_SECTIONS) * 4))

    floor_selected = []
    floor_taken_ids = set()
    for sec_name in _FLOOR_SECTIONS:
        # `candidates` is already globally sorted by -coherent_magnitude,
        # so filtering preserves that same per-section ordering -- no
        # re-sort needed to get each section's own best first.
        sec_cands = [c for c in candidates if c["section"] == sec_name]
        take = sec_cands[:min_per_section]
        floor_selected.extend(take)
        floor_taken_ids.update(id(c) for c in take)

    remaining_budget = max(0, top_k - len(floor_selected))
    overflow = [c for c in candidates if id(c) not in floor_taken_ids][:remaining_budget]

    result = floor_selected + overflow
    result.sort(key=lambda c: -c["coherent_magnitude"])
    # Defensive cap: only binds if a pathologically small top_k makes the
    # floor reservation itself (min_per_section * 6 sections) exceed top_k
    # -- never happens at the real GRANDURUN_TOPK=200 default (floor sums
    # to ~50) but keeps the "returns at most top_k" contract callers rely
    # on for any configured value.
    return result[:top_k]


try:
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack, SensoryBank, SENSORY_DNA, ROLE_DNA, scene_tags_from_words
    from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF, compute_dsf
    from dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6 import L6_TCL, CHI_BAND as _CHI_ATLAS_BAND
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
    from gualaloom_v4_chi_atlas_l6 import L6_TCL, CHI_BAND as _CHI_ATLAS_BAND
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

# GL-FIX-LOCK-GRANULARITY-C1-20260710: sentinel distinguishing "caller did
# not pass prev_phase_vec at all" (legacy direct-caller behavior -- read_word
# reads/updates the shared self._prev_phase_vec instance attribute exactly
# as before) from "caller explicitly passed None" (a real value meaning "no
# previous word in THIS call-local chain yet" -- read_sentence's own case
# for a sentence's first word). Plain None can't distinguish these two
# cases, hence the dedicated sentinel object.
_PHASE_VEC_UNSET = object()


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

# 2026-07-09 credo fix (Joe: "language cannot really have meaning without
# the equality of experience as tied to our senses"): which atlas section
# NAMES represent a genuinely real or deliberately-curated sensory moment,
# versus the always-on, word-triggered SENSORY_DNA/sensory_generators
# auto-fire that happens on ~150-190 hardcoded words regardless of whether
# any real camera/mic/experience is involved (read_word's `modal_{m}`
# writer, `_bind_sensory_words`'s `modal_{modality}` writer -- both
# confirmed fake, admitted placeholders in their own source comments).
# Real/deliberate sections, by construction, never use the "modal_"
# prefix: bare "sight" and "audio_*" (real camera/mic frames or an
# uploaded picture/sound, process_sight_frame/process_sound_frame,
# gualaloom_v5_engine.py ~7262-7396), and "touch_*"/"smell_*"/"taste_*"
# (app.py's /bundle: give_experience handler -- a human deliberately
# asserting a real sensory quality for an actual experience, run through
# sensory_generators.py's real waveform-shape physics, never automatic).
REAL_GROUNDING_SECTION_PREFIXES = ("audio_", "touch_", "smell_", "taste_")
REAL_GROUNDING_EXACT_SECTIONS = {"sight"}
FAKE_MODAL_SECTIONS = {"modal_sight", "modal_sound", "modal_touch",
                        "modal_smell", "modal_taste"}


def _require_grounded_speech():
    """Joe's ruling, 2026-07-09: only speak words tied to a real experience,
    or say nothing. Kill switch (not a hedge on the ruling itself, a dial
    for the measured severity of its effect) -- default ON, same
    env-var-gate convention as DEEP_ATLAS_ENABLED/DEEP_PRIOR_ENABLED.
    Re-read per call (hot path, but a plain dict lookup -- same convention
    read_word already uses for DECAY_PAUSED)."""
    return os.environ.get("REQUIRE_GROUNDED_SPEECH", "1") != "0"


def _deep_atlas_eligibility_backfill_enabled():
    """GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711 Part 1: kill switch
    for wiring DeepAtlas.strength into the real-speech eligibility backfill
    (_entry_grants_grounding / _backfill_grounded_from_deep_atlas /
    _backfill_eligibility_for_promotion). Default OFF pending real live
    validation -- matches the daydream-reconnect precedent from earlier
    tonight (gl-daydream-reconnect-20260711), except this is HIGHER blast
    radius, not lower: it is a second, independent path to a word ever
    being eligible to speak at all, layered on top of the real-grounding
    gate _require_grounded_speech() already enforces. Re-read per call,
    same convention as _require_grounded_speech (this is not a hot path --
    only consulted during boot-time index rebuilds and the once-per-real-
    dream-cycle-promotion trigger, both already-infrequent events)."""
    return os.environ.get("DEEP_ATLAS_ELIGIBILITY_BACKFILL_ENABLED", "0") == "1"

# --- GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2 (dual-write/dual-read) ---
# HEURISTIC: ENTRY_CHI_BAND=8 -- how far chi injection reaches when
# selecting entry neurons for a chi-anchored input. Class: from-design.
# Measurement plan: verify entry neurons cover a plausible neighborhood;
# adjust if injection is too narrow (recognition fails) or too broad
# (specificity lost).
ENTRY_CHI_BAND = 8
# HEURISTIC: ENTRY_SAMPLE_SIZE=16 -- fallback random injection size when
# no chi anchor is available. Class: from-design. Measurement plan:
# measure recognition quality under the fallback path; adjust if too
# silent or too broad.
ENTRY_SAMPLE_SIZE = 16

# --- GL-CMD-ENTRY-NEURON-BROADEN (kill-switched, default OFF) ---
# Real, measured finding (2026-07-12): commit 712578f's fix (16 -> 1 entry
# neuron per word) correctly closed the 25%-of-population-per-word
# over-injection incident, but as a side effect real connection formation
# (distinct (source, target) synapse pairs ever touched, tracked in
# LoomNeuron._incoming_synapse_weights) collapsed to almost nothing: a
# live production boot ran 3+ hours of real conversation and only ever
# touched 7 synapses total -- exactly ENTRY_CHI_BAND's k_neighbors=7 for
# ONE hemisphere, i.e. only ONE entry-neuron firing event's propagation
# ever completed (see GL-RPT-BLUEPRINT-DEPLOYMENT-AUDIT-C1-20260712-v1).
#
# Direct measurement (fresh organism, 243 distinct words, see this
# dispatch's own test file) of what widening entry count actually costs:
#   entries=1 (today):  breadth mean=0.125, max=0.125 (1 hemisphere, always)
#   entries=2 (nearest by chi, GLOBALLY): breadth max=0.250 -- lands
#       exactly on the incident's own 25% threshold whenever the 2nd
#       nearest neuron falls in a DIFFERENT hemisphere (measured: it does,
#       for essentially every word tested).
#   entries=3/4 (nearest by chi, GLOBALLY): breadth = 0.250 for EVERY word
#       tested -- unsafe, matches the incident condition, not shipped.
#
# The safe version constrains broadening to the PRIMARY match's OWN
# hemisphere (see _broaden_entry_neurons_same_hemisphere): every
# hemisphere is a fully-connected 8-neuron clique (SEED_SIZE_PER_
# HEMISPHERE=8, k_neighbors clamped to 7, see cluster.py), so ANY subset
# of that one hemisphere's 8 neurons as entries can never make the
# propagation-touched set exceed that same 8-neuron hemisphere --
# 8/64=0.125 injection breadth, HALF the 25% incident threshold, and
# INDEPENDENT of how many of the 8 are chosen as entries (2, 3, or even
# all 8) -- this is a structural ceiling, not a tuned number. Verified
# directly: see test_entry_neuron_broaden.py's
# test_broaden_on_stays_bounded_to_one_hemisphere.
#
# What DOES grow with entry count is exactly the thing that was measured
# anemic: 1 entry -> 7 possible (source, target) pairs get a chance to be
# touched per word (that one entry's own 7 outgoing synapses); 2 entries
# in the same clique -> up to 14 DISTINCT pairs (each entry's own 7
# outgoing edges, no overlap between the two entries' own outgoing sets)
# -- literally double the connection-formation surface per word, at zero
# additional injection-breadth cost. Default count of 2 is the smallest
# possible increase over today's 1 (task's own guidance: "1 -> 2 or 3,
# not back to 16"); left configurable via ENTRY_NEURON_BROADEN_COUNT for
# a future, separately-decided step to 3 (also measured safe, still
# bounded to one hemisphere) without a code change.
#
# Kill switch: default OFF (ENTRY_NEURON_BROADEN_ENABLED unset or != "1"),
# read fresh on every call (same convention as SENSORY_SPIKE_INJECTION_
# ENABLED above) so it can be toggled per-test without reconstructing
# Guala or reloading this module. When OFF, _select_entry_neurons is
# byte-identical to pre-this-change behavior -- the broadening branch is
# never even reached (see test_broaden_default_off_is_byte_identical_to_
# baseline).
ENTRY_NEURON_BROADEN_COUNT = 2
# HEURISTIC: EMISSION_THRESHOLD=0.5, TOP_K_EMISSION=20 -- membrane-state
# emission candidate selection (RECALL_BACKEND=stdp only; not used in
# production during Phase 1). Class: from-design. Measurement plan:
# verify emission candidates match legacy top candidates in shadow mode;
# adjust if quality degrades.
EMISSION_THRESHOLD = 0.5
TOP_K_EMISSION = 20


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


def _organism_query_signal_auditory(sound_signal):
    """GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-208: the auditory-only
    mirror of _organism_signal's language-only base -- a genuine SENSORY
    cue with no word at all ("what does this sound go with"), the shape
    the -207/-208 partial-cue fix (per-lane binding + masked match in
    loom_model/binding_atlas.py) makes meaningful for the first time.
    Callers must use Embryo.recall(), not recall_fast() -- recall_fast's
    own proven scope excludes visual/auditory signals (brain.py
    docstring), and production's real query shape (_organism_signal) has
    never sent one, so recall_fast has no path exercised for this cue."""
    return {"auditory": sound_signal}


# ============================================================
# v7: Autonomy Constants (modeling-validated, do not tune without re-modeling)
# GUALALOOM-V7-AUTONOMY-WC-2026-06-06
# ============================================================

NEEDS_DRIFT_RATE = 0.0001   # per tick — needs fall from 1.0 to 0 in ~10K ticks
NEEDS_TARGET_V7 = 0.7       # target for all three needs (autonomy model)

# Grandurun tuning constants (GL-BRIEF-GRANDURUN-IMPLEMENTATION-20260616-01)
CHI_CORR_LENGTH = 50.0        # phase correlation length; tune empirically
MIN_GAIN_THRESHOLD = 0.10     # minimum coherent-sum gain to add candidate
# GL-CMD-NO-CAPS-COHERENCE-SPEAKS-EVE-20260705-203 U0c: the length-cap
# constant (was 12) is deleted entirely -- Joe's ruling: no caps, no hard
# ceilings on her speech. MIN_GAIN_THRESHOLD above is now the only
# stopping rule anywhere in the speech chain; deleting the constant (not
# just its uses) so no future path can quietly re-import a length fence.
SPIN_VECTOR_DIM = 7           # GL-METADATA-PIPELINE: 8→7 (modal_alignment dropped)
GRANDURUN_POOL_K = 50         # per-section candidate count for wider retrieval

# 60-L: NEGATION_OPS dropped — negation is a phase rotation, not a lexical flag.
# Polarity derives from consecutive phase-vector rotation in read_word.
GRANDURUN_TOPK = int(os.environ.get("GRANDURUN_TOPK", "200"))
# GL-CMD-ENABLE-COGNITION-EVE-20260705-211 RCA / Joe decision 2026-07-06:
# _rich_sensory_candidates was truncating to GRANDURUN_TOPK (200), which is
# effectively no cap at all for its multi-source fan-out (cross-modal +
# deep-atlas + cofire-spread + re-routing) -- the plain default path never
# generates anywhere near 200 raw candidates so the same shared constant
# never binds there. 200 competing candidates makes the settle-on-one-
# winner commit step nearly impossible. Own, separate, much smaller cap:
# richer than the default path's natural ~10-13, without drowning it.
RICH_SENSORY_TOPK = int(os.environ.get("RICH_SENSORY_TOPK", "10"))
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

# GL-DES-ENGINE-PLAY-WORLD-V0-C1-20260711: how often, within a single
# PLAYING activity, _atick_playing checks for a real, already-known
# picture+word pairing to revisit (see docs/GL-DES-ENGINE-PLAY-WORLD-V0-
# C1-20260711-v1.md §3.1). 500 keeps this cheaper than the codebase's
# existing amortized-check cadences (target_familiarity decay/snapshot
# and forget_stale_* both run at tick%200; Play's own emission-trigger
# check already runs at tick%300) -- roughly 2-3 checks per full
# 1500-tick PLAYING session (ACTIVITY_TICK_BUDGETS["PLAYING"]), not a
# per-tick cost. _atick_playing runs inside the caller's already-held
# self.lock (an RLock, 5Hz nominal tick rate) -- see the design doc §3.3
# for the full cost/lock analysis behind this choice.
PLAY_REVISIT_INTERVAL_TICKS = 500
# Deliberately ~10x smaller than ATTENDING_VISUAL's up-to-0.2-per-full-
# session familiarity step (GL-CMD-ATTEND-GROOVE-107): a brief, passing
# re-notice during play is not a dedicated viewing session and should
# not earn as much familiarity as one. Same field, same 0.9 cap, smaller
# step -- see design doc §3.1 step 4.
PLAY_FAMILIARITY_BUMP = 0.02

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

# Change 4 (GL-SPC-SUBSTRATE-TRUE-SINGLE-STACK-20260716-v3, release-policy
# note a): ONE MOUTH.  Every release label in this tuple passes the same
# voice (TTS) + self-hearing boundary; labels stay distinct end-to-end so
# telemetry always says which authority released.  Silence and retired
# legacy labels (e.g. "v5_commit") are deliberately NOT here — they never
# gain a voice.  This is the single authority both the engine's _self_hear
# gate and the runner's TTS gate consult; never fork a second copy.
VOICED_RELEASE_SOURCES = ("fact_strand_commit", "assemblage_commit")

# Change 4 (spec v3 release-policy note b): the autonomous loop queries the
# certified composer with seeds drawn from the organism's own lived content.
# HARD CONSTRAINT (documented production regression, GL 2026-07-06 recall
# wiring): seeds NEVER come from atlas candidate/neighborhood dumps — only
# from committed BindingWindow words and the current activity's target.
AUTONOMOUS_COMPOSER_SEED_WINDOWS = 6   # freshest committed windows considered
AUTONOMOUS_COMPOSER_SEED_ATTEMPTS = 3  # composer queries per 90s cycle (cost bound)
AUTONOMOUS_COMPOSER_SEED_PREFIX = 2    # lived-opening words used as one query

# Change 4 adversarial-review fixes (2026-07-16).  F1: without these two
# gates the self-hear loop CLOSES — an autonomous release re-enters via
# _self_hear as a fresh emulated window (touch/taste/smell emulator entries
# make it multimodal), lands in _ordered_language_windows as the FRESHEST
# window, seeds the next cycle, and the composer re-releases a shrinking
# suffix of her own last utterance forever under the certified label.
# (a) Words she heard herself say are MEMORY — they still exist, still
#     certify for conversation recall — but they never SEED autonomous
#     speech.  These are the source tags her own released words carry.
AUTONOMOUS_SEED_SELF_SOURCE_TAGS = frozenset({
    "guala",        # _self_hear -> read_sentence(source="guala")
    "guala:self",   # _bind_certified_fact_emission_to_active_window
    "voice:self",   # self-voice audio injection (sound lane, listed for closure)
})
# (b) A release whose text equals any of the last K autonomous releases is
#     refused (repeat_suppressed) — falls through to assemblage/silence.
AUTONOMOUS_RELEASE_REPEAT_WINDOW = 8
# F3: wall-clock budget for the certified compose section of one autonomous
# cycle (the composer rebuild is O(corpus) until Change 1's cached composer
# lands; this bound guards self.lock hold time now and stays correct after).
AUTONOMOUS_COMPOSE_BUDGET_MS_DEFAULT = 250.0
# TTS input cap: espeak-ng runs under a 5s subprocess timeout; long certified
# continuations blew past it and produced a silent voice.  Truncation is
# logged (tts_truncated), never silent.
TTS_MAX_CHARS = 200

# 2026-07-10 GL-CMD-AUTONOMOUS-INTEREST-REFINEMENT: real research (Schmidhuber
# 1991/2010 compression-progress; Oudeyer & Kaplan 2007 learning-progress
# intrinsic motivation) says a sustained novelty LEVEL just means "under-
# stimulated" -- the real trigger for unprompted expression is the RATE
# novelty is moving, not its level. NOVELTY_HISTORY_MAX bounds a per-gate-
# check recent sample window (same evict-oldest convention used elsewhere
# in this file). NOVELTY_RISE_MIN is the minimum real increase across that
# window to count as "rising" rather than noise -- set to 10% of Needs.
# DECAY["novelty"] (0.03, this codebase's own existing scale for "one
# meaningful positive nudge"), not an invented number.
NOVELTY_HISTORY_MAX = 20
NOVELTY_RISE_MIN = 0.003

# GL-CMD-TEACHER-SUBSTRATE-TRUE: tick-window cap for emission records
# = ln(1/FORGETTING_THRESHOLD) / (DECAY_LAMBDA / SLOW_DIV)
# = ln(50) / 8.33e-6 ≈ 469_443 ticks (≈ 48h at current tick rate)
# Substrate-derived: same physics as slow-decay forget window.
EMISSION_RECORDS_TICK_WINDOW = 469_443
# Safety cap: prevent pathological growth above 1000 records.
EMISSION_RECORDS_CAP = 1000

# 2026-07-10 GL-CMD-SLEEP-REORGANIZE: Blueprint Phase 5 ("sleep as work").
# Diekelmann & Born 2010 (active systems consolidation) and Wagner et al.
# (sleep-inspires-insight) both describe sleep forming NEW tentative links
# between recently co-active regions, distinct from strengthening links
# already known -- deep_atlas's existing promote()/dream_promotion_gate only
# does the latter (reinforce an existing working-atlas entry). This adds the
# former as a separate, low-confidence, explicitly-tagged, real-data-only
# mechanism: pair up real entries from THIS dream cycle's own sample_chis
# (never fabricated content) that are chi-proximate and not already linked,
# write a tentative hypothesis entry using deep_atlas's real schema. Kept
# out of promote() itself since promote() expects a working-atlas-style
# entry and derives co_occurrence from live neighborhood -- not the right
# shape for "two specific things just co-occurred in this reorganize pass."
# REORGANIZE_ENABLED: single flag, same convention as DEEP_ATLAS_ENABLED/
# EVENT_DRIVEN_SUBSTRATE -- instant live rollback without a redeploy.
REORGANIZE_ENABLED = os.environ.get("REORGANIZE_ENABLED", "1") != "0"
REORGANIZE_CHI_BAND = 3            # tighter than working atlas's default band=2 search+1 slack
REORGANIZE_HYPOTHESIS_STRENGTH = 0.05   # just above deep_atlas.FORGETTING_THRESHOLD (0.02)
REORGANIZE_MAX_PER_CYCLE = 5        # bounded: sample_chis itself is capped at 5, so <=10 pairs considered
REORGANIZE_HYPOTHESIS_TTL_TICKS = 40_000  # ~ a few real sleep cycles at 200-tick dream spacing
# GL-CMD-SLEEP-REORGANIZE follow-on (adversarial review, 2026-07-10): the
# tracking deque must hold every entry alive for the FULL TTL window at the
# max sustained creation rate, or deque(maxlen=...) silently FIFO-evicts
# still-young entries before they ever reach the TTL check -- orphaning them
# to deep_atlas's own near-zero decay (hundreds of thousands of ticks),
# recreating the exact class of bloat incident this file has hit twice
# before. Worst case: REORGANIZE_MAX_PER_CYCLE new/merged entries every
# dream cycle (every 200 ticks) for the entire TTL window =
# 5 * (40_000 / 200) = 1000. Set the cap to exactly that derived worst case,
# not an arbitrary smaller number.
REORGANIZE_TRACKING_MAX = REORGANIZE_MAX_PER_CYCLE * (REORGANIZE_HYPOTHESIS_TTL_TICKS // 200)

# 2026-07-10 GL-CMD-SENSORY-ECHO-REPLAY-REVISIT: _replay_sensory_echo (see
# its own docstring) was built, shipped, then hard-disabled (`if False and`)
# the same night after live converse_timing showed read_ms jump from ~6s to
# 24.4s of a 27.2s turn -- a 200-entry scan cap was added as a mitigation
# attempt but "didn't bring it back down" per that incident's own report
# (docs/GL-RPT-ENABLE-COGNITION-C1-20260705-211-v1-RCA.md), and the real
# cost was never actually isolated before it was cut out. Direct
# measurement tonight against a realistic-scale atlas (~9000 entries/200
# chi keys, matching real production) with the CURRENT cap in place shows
# ~0.03ms/call -- roughly 3 orders of magnitude too fast to explain that
# regression, which doesn't match the incident report and needs a live,
# monitored trial to resolve (local testing on a fresh, low-density
# organism has already been shown once this week not to catch every
# production-scale effect). Gated behind its own kill switch, DEFAULT OFF
# -- this restores an operator's ability to try it without a code change,
# it does NOT itself re-enable the mechanism.
SENSORY_ECHO_REPLAY_ENABLED = os.environ.get("SENSORY_ECHO_REPLAY_ENABLED", "0") != "0"

# GL-CMD-REFLECTION-EVE-20260710 (imagination half): surfaces
# reorganize_hypothesis entries (see _dream_reorganize) as low-weight
# emission candidates via _imagination_candidates -- see that function's
# own docstring for the full design and why this is NOT the same pool
# _deep_atlas_neighbor_candidates draws from. IMAGINATION_ENABLED: same
# kill-switch convention as REORGANIZE_ENABLED/SENSORY_ECHO_REPLAY_ENABLED
# -- default ON since this only ever surfaces already-real, already-
# gated content at a damped weight, but instantly revertible without a
# redeploy if live behavior looks wrong. IMAGINATION_WEIGHT_SCALE damps
# a hypothesis's raw (already-low, REORGANIZE_HYPOTHESIS_STRENGTH=0.05
# ceiling) weight further, so a confirmed real candidate of equal raw
# strength always wins. IMAGINATION_MAX_CANDIDATES_PER_TURN keeps this
# a subtle background flavor, not a second voice.
IMAGINATION_ENABLED = os.environ.get("IMAGINATION_ENABLED", "1") != "0"
IMAGINATION_WEIGHT_SCALE = 0.3
IMAGINATION_MAX_CANDIDATES_PER_TURN = 1

# GL-CMD-REFLECTION-EMISSION-EVE-20260710 (reflection half, follow-on to
# the imagination half above): surfaces words that were genuinely
# co-present in a real remembered episode as low-weight emission
# candidates via _reflection_candidates -- see that function's own
# docstring for the full design and why this draws from self._reflections
# (real _form_reflection output), a completely different real-data pool
# from _imagination_candidates' deep_atlas hypothesis walk. Same
# kill-switch convention as IMAGINATION_ENABLED/REORGANIZE_ENABLED/
# SENSORY_ECHO_REPLAY_ENABLED. Default ON, decided only after inspecting
# _form_reflection and its restore path directly (2026-07-10): every
# reflection field traces to _record_episodic_experience (a genuinely
# curated give_experience call, never plain corpus reading) or her own
# real current needs state, nothing fabricated, and self._reflections
# itself is never persisted/restored (fresh empty deque every process
# boot, same honest-empty-on-restart convention as _novelty_history) --
# so there is no restored-JSON-shaped attack surface here the way there
# is for _form_reflection's own episodic-memory inputs. Same real-
# committed-section-home gate as every other candidate source.
# REFLECTION_BASE_STRENGTH is an engineered constant, not a derived/
# stored weight -- a reflection has no per-word co_occurrence value the
# way a deep_atlas hypothesis entry does (reflections are never written
# to deep_atlas at all), so every candidate word from a single matched
# reflection shares one fixed, deliberately low strength, chosen in the
# same ballpark as REORGANIZE_HYPOTHESIS_STRENGTH so a reflection
# candidate competes at roughly the same order of magnitude as an
# imagined one. REFLECTION_EMISSION_WEIGHT_SCALE damps that further, same
# role as IMAGINATION_WEIGHT_SCALE, so a confirmed real candidate of
# equal raw strength always wins. REFLECTION_EMISSION_MAX_CANDIDATES_
# PER_TURN keeps this a subtle background flavor, never a second voice --
# same cap value and reasoning as imagination's.
REFLECTION_EMISSION_ENABLED = os.environ.get("REFLECTION_EMISSION_ENABLED", "1") != "0"
REFLECTION_BASE_STRENGTH = 0.05
REFLECTION_EMISSION_WEIGHT_SCALE = 0.3
REFLECTION_EMISSION_MAX_CANDIDATES_PER_TURN = 1

# GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1 / GL-CMD-CREDO-RELEVANCE-WEIGHT-
# C1-20260711: the credo/grounded-speech gate (_word_to_emission_sections
# membership, REQUIRE_GROUNDED_SPEECH) is a binary pass/fail with zero
# notion of how relevant an eligible candidate actually is to the CURRENT
# turn -- a common function word clears "has she ever said this" far more
# reliably than a specific content word, so candidate generation
# structurally favored generic filler. Fix (see _brain_emission_
# candidates_legacy's deep_atlas gather): a candidate word that resonates
# with MORE THAN ONE of the turn's own input words -- i.e. shows up in
# more than one query word's own real deep_atlas co-occurrence
# neighborhood, via _deep_atlas_neighbor_candidates' existing walk, not a
# new relevance mechanism -- is real spreading-activation convergence and
# is weighted up accordingly. DEEP_ATLAS_RELEVANCE_BOOST_PER_SEED: how
# much extra weight each additional distinct converging input word adds
# (linear, HEURISTIC, same "class: from-design" convention as this file's
# other engineered constants -- e.g. CHI_CORR_LENGTH, IMAGINATION_WEIGHT_
# SCALE). DEEP_ATLAS_RELEVANCE_BOOST_MAX caps the multiplier so a turn
# with many query words can't let convergence COUNT alone dominate the
# real, measured co-occurrence strength that still anchors every
# candidate's base weight. A candidate that only ONE seed word surfaces
# (the common case) gets a 1.0x boost -- i.e. numerically IDENTICAL
# behavior to before this fix; only genuine multi-word convergence
# changes anything. This never changes ELIGIBILITY (the real-grounding
# gate itself, and _deep_atlas_neighbor_candidates' own walk, are
# untouched) -- only the WEIGHT/ORDER among already-eligible candidates.
DEEP_ATLAS_RELEVANCE_BOOST_PER_SEED = 0.5
DEEP_ATLAS_RELEVANCE_BOOST_MAX = 3.0


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
                "expected_end_tick": self.expected_end_tick,
                "metadata": dict(self.metadata)}


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

# 2026-07-08 bloat fix: save_full_state has always truncated
# sec.commits to this exact number when writing guala_sections.json
# (list(sec.commits[-5000:])) -- but the LIVE, in-memory self.commits
# was never capped, only sliced at save time. Confirmed live: three
# sections (listen/verb/intro) were already observed at 5610 commits,
# past the "5000" every status readout implies is a ceiling, ~15
# minutes after a save had them at exactly 5000 -- proof the number
# people read off guala_status is a save-path illusion, not a real
# runtime constraint. Reusing the SAME already-intended number here
# (not a new heuristic) so append time actually matches what save time
# always claimed.
SECTION_COMMITS_MAX = 5000

# GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1 #3b (wC live
# telemetry): self.modes -- the actual per-section vocabulary bank --
# has NEVER had a size cap at all (only self.commits does, above).
# Confirmed live: three sections (listen/verb/intro, the generic/common
# ones) had already grown to 127-148% of this exact number with zero
# bound, while subject/object/modifier/ground -- the sections that would
# hold real topic-specific content -- sat 8-36% full. The emission
# agreement mechanism needs multiple sections to agree; three sections
# flooded with generic filler and four starved of real content is
# exactly why replies collapse to single generic words. Reusing the
# SAME number as SECTION_COMMITS_MAX (not inventing a second heuristic)
# since it's already the number every status readout and this class's
# own prior comment (above) treated as the intended ceiling.
SECTION_MODE_CAP = 5000

# GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1 fix #1: Section.receive()'s
# similarity-scan fallback (for any word that misses the O(1)
# word-identity fast path) previously scanned EVERY alive mode in the
# section -- confirmed the dominant real cost of a live conversational
# turn (77-92% of total wall-clock, "listen" section alone measured
# 8,000-16,000ms/sentence once it passed 14,000+ modes,
# GL-BUG-MODES-MATRIX-THRASH). Biological framing (Joe-approved):
# sensory input is coarsely pre-categorized (e.g. odorant receptor
# type) BEFORE any detailed comparison, so only a small, already-
# relevant neighborhood is ever compared in detail -- this codebase
# already has exactly this pattern for cross-section chi binding
# (ChiAtlas, dsf_ai_service/v4/gualaloom_v4_chi_atlas_l6.py, CHI_BAND=2),
# just never applied to a single section's OWN mode bank. Reuses that
# same already-tuned band width (not a new heuristic) for the
# analogous "how far in chi is still worth comparing in detail"
# tradeoff, applied read-side the same way ChiAtlas.match_score() scans
# +/-band around the query chi.
SECTION_CHI_BAND = _CHI_ATLAS_BAND


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
        self._modes_matrix = None     # (n_alive_modes, 8) array for vectorized cosine sim
        self._modes_norms = None      # (n_alive_modes,) precomputed norms
        self._modes_dirty = True      # True = matrix must be rebuilt before use
        self._alive_row_of_mode = {}  # real mode_idx -> row in the compacted matrix
        # 2026-07-08 GL-BUG-MODES-MATRIX-THRASH follow-up: self.modes has
        # never had any forgetting -- every genuinely new word becomes a
        # permanent entry, and _get_modes_matrix's O(n_modes) cosine scan
        # is exactly what cost ~26s live on 2026-07-06 once "listen"
        # reached 14,000+ modes. Mode INDEX is load-bearing elsewhere
        # (LivingAtlas/DeepAtlas bindings and WindowManager entries are
        # keyed by motif=mode_idx; see the GL-FIX-ATLAS-INTEGRITY guard
        # in receive() below for a documented past incident from an
        # index/mode-count mismatch) -- self.modes must NEVER shrink or
        # reorder, or every existing binding that references an index
        # past the removed one silently points at the wrong word. So
        # forgetting here means tombstoning a mode IN PLACE (excluded
        # from matching, index and content otherwise untouched forever),
        # never deleting or reusing its slot. These two arrays are the
        # same "not persisted, rebuilt on load" class as the caches
        # above -- not restored from a save, reinitialized fresh (all
        # alive, last-active=now) by _rebuild_word_index so a deploy
        # never mass-forgets everything on its first tick.
        self._mode_last_active_tick = []  # index-aligned with self.modes
        self._mode_alive = []             # index-aligned with self.modes
        # GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1 #3b: running
        # count of alive (non-tombstoned) modes, kept in sync by every
        # place that flips _mode_alive (append, _evict_weakest_mode,
        # forget_stale_modes) and recomputed from scratch in
        # _rebuild_word_index (the one place _mode_alive itself can be
        # reset out from under this counter, e.g. on load). O(1) cap
        # check in receive() instead of an O(n_modes) sum() on every
        # single new-word commit.
        self._n_alive = 0
        # GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1 #3b (v2
        # fix, post-adversarial-review): the real mode-indices that are
        # currently alive, maintained incrementally at every mutation
        # site (append/evict/forget/rebuild) -- O(1) add/discard, never
        # a scan. _evict_weakest_mode() needs exactly this (which real
        # indices are alive) and NOTHING else; it must not go through
        # _get_modes_matrix()/_alive_row_of_mode; that path (re)builds a
        # full (n_alive, 8) numpy similarity matrix from range(len(self.
        # modes)) -- the FULL PHYSICAL HISTORY -- whenever _modes_dirty
        # is set, which _evict_weakest_mode() itself sets on every call.
        # A section needing multiple evictions in one receive() (the
        # exact live state this fix ships into: 127-148% over cap) was
        # measured triggering that full rebuild on every eviction after
        # the first -- 2.0-5.7s for a single word, inside self.lock,
        # confirmed by direct adversarial review before this version.
        self._alive_indices = set()
        # GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1 fix #1: chi_value (int,
        # the exact value passed into receive() and stored per-mode as
        # self.modes[i][1]) -> set of currently-alive real mode indices
        # with that exact chi. Maintained incrementally at the SAME
        # mutation sites _alive_indices already is (add in
        # _append_new_mode, discard in _evict_weakest_mode and
        # forget_stale_modes, full rebuild in _rebuild_word_index) --
        # never scanned/rebuilt from self.modes in the per-word hot
        # path. receive()'s similarity-scan fallback uses this (via
        # _chi_neighborhood_indices/_get_chi_neighborhood_matrix below)
        # to restrict the O(n) matmul fallback to a small +/-
        # SECTION_CHI_BAND neighborhood instead of every alive mode in
        # the section -- the coarse pre-categorization step described
        # above. A chi key's set is deleted once empty (discard helper
        # below) so this doesn't accumulate empty entries forever across
        # a section's full lifetime chi range.
        self._chi_buckets = {}

    def _chi_bucket_add(self, chi, mode_idx):
        """Add mode_idx to its exact-chi bucket. See self._chi_buckets."""
        self._chi_buckets.setdefault(chi, set()).add(mode_idx)

    def _chi_bucket_discard(self, chi, mode_idx):
        """Remove mode_idx from its exact-chi bucket (mode tombstoned/
        evicted), deleting the bucket entirely once empty so a long-
        lived section's full lifetime chi range doesn't leave behind an
        ever-growing number of empty set entries."""
        bucket = self._chi_buckets.get(chi)
        if bucket is not None:
            bucket.discard(mode_idx)
            if not bucket:
                del self._chi_buckets[chi]

    def _chi_neighborhood_indices(self, chi):
        """Union of alive real mode indices whose OWN chi falls within
        SECTION_CHI_BAND of the query chi -- same read-side band-scan
        ChiAtlas.match_score() already uses (+/-CHI_BAND around the
        query key), applied here to this section's own per-mode chi
        instead of ChiAtlas's cross-section binding entries."""
        out = set()
        for d in range(-SECTION_CHI_BAND, SECTION_CHI_BAND + 1):
            bucket = self._chi_buckets.get(chi + d)
            if bucket:
                out |= bucket
        return out

    def _get_chi_neighborhood_matrix(self, chi):
        """Vectorized sim data restricted to alive modes within
        SECTION_CHI_BAND of the given chi -- the O(n_alive) full-section
        fallback scan's replacement (GL-RPT-READ-MS-ROOTCAUSE-C1-
        20260711-v1 fix #1). Returns (real_indices, matrix, norms), all
        None if no alive mode falls in the neighborhood.

        Deliberately NOT cached and deliberately independent of
        _get_modes_matrix()/_modes_matrix/_modes_dirty/
        _alive_row_of_mode -- that is a SEPARATE full-alive-set cache
        that existed solely to serve the full-section scan this method
        replaces (see the reinforcement branch's comment in receive(),
        word_match_idx hit, for what became of it: an already-existing,
        already-safe "cache not built yet" fallback, not a new gap).
        This method is small and chi-varying per call (bounded by
        neighborhood occupancy, not section size), so it is simply
        recomputed each time rather than cached; it never reads or
        invalidates the other cache, and the other cache never reads or
        invalidates this one."""
        candidate_indices = self._chi_neighborhood_indices(chi)
        if not candidate_indices:
            return None, None, None
        real_indices = list(candidate_indices)
        vecs = np.array([self.modes[i][0].to_array() for i in real_indices])
        norms = np.linalg.norm(vecs, axis=1) + 1e-12
        return real_indices, vecs, norms

    # HEURISTIC: reuses LivingAtlas's own real, already-tuned decay
    # constants (DECAY_LAMBDA=1e-4/tick, FORGETTING_THRESHOLD=0.02) to
    # derive the same effective "how long without reinforcement before
    # something is considered forgotten" window, rather than inventing a
    # new, unrelated number for a structurally analogous kind of memory.
    # ln(0.02)/-0.0001 ≈ 39,120 ticks.
    MODE_FORGET_TICKS = int(math.log(0.02) / -0.0001)

    def _rebuild_word_index(self, current_tick=0):
        """Rebuild word→mode-index dict from self.modes. Call after
        deserialization. current_tick: the ENGINE's current tick (not
        this section's own persisted tick, which may be stale relative
        to it, GL-FIND-TICK-DOMAIN-C1) -- used only to seed
        _mode_last_active_tick for modes restored from a save that
        predates this field, so a deploy doesn't treat every existing
        mode as instantly 39,120 ticks stale."""
        self._word_to_mode_idx = {}
        for i, (_, _, word) in enumerate(self.modes):
            if word:
                self._word_to_mode_idx[word.lower()] = i
        n = len(self.modes)
        if len(self._mode_last_active_tick) != n:
            self._mode_last_active_tick = [current_tick] * n
        if len(self._mode_alive) != n:
            self._mode_alive = [True] * n
        # GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1 #3b: always
        # recompute (not just on the branches above) -- this is the one
        # place _mode_alive can be reset out from under the running
        # counter (fresh load), so re-derive it from source of truth
        # every call. O(n) but this method only runs at load/deserialize
        # time, never in the per-word hot path.
        self._n_alive = sum(1 for a in self._mode_alive if a)
        self._alive_indices = {i for i, a in enumerate(self._mode_alive) if a}
        # GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1 fix #1: rebuild the
        # chi-bucket index from source of truth the same way
        # _alive_indices itself is rebuilt just above -- this is the one
        # place _chi_buckets can be reset out from under a load (same
        # reasoning as _n_alive's comment above). O(n_alive), load/
        # deserialize time only, never the per-word hot path.
        self._chi_buckets = {}
        for i in self._alive_indices:
            self._chi_bucket_add(self.modes[i][1], i)
        self._modes_dirty = True

    def _get_modes_matrix(self):
        """Return cached (n_alive, 8) matrix + (n_alive,) norms for
        vectorized sim, restricted to modes not yet forgotten.

        GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1 fix #1: this built the
        FULL alive-set matrix receive()'s similarity-scan fallback used
        to compare a new word against -- confirmed the dominant real
        cost of a live turn once a section passed ~14,000 modes. receive()
        now calls _get_chi_neighborhood_matrix() instead (a small, chi-
        restricted matrix built fresh per call, not this cache), so this
        method has no remaining call site and self._alive_row_of_mode
        (below) is never populated -- the reinforcement branch in
        receive() (word_match_idx hit) already had an explicit, safe
        "cache not built yet" fallback for exactly this state (mark
        _modes_dirty and move on), so nothing reads a stale/empty value
        here. Left in place rather than deleted to keep this fix's diff
        scoped to the scan it replaces; a future change is free to remove
        this and the in-place-update branch together if it wants the
        dead weight gone, but doing so is out of scope for this fix.

        Rebuilds only when _modes_dirty is set (modes changed or a
        forget pass ran since last build)."""
        if not self.modes:
            return None, None
        if self._modes_dirty or self._modes_matrix is None:
            alive_indices = [i for i in range(len(self.modes))
                              if i < len(self._mode_alive) and self._mode_alive[i]]
            self._alive_row_of_mode = {mode_i: row_i for row_i, mode_i in enumerate(alive_indices)}
            if not alive_indices:
                self._modes_matrix = None
                self._modes_norms = None
            else:
                vecs = np.array([self.modes[i][0].to_array() for i in alive_indices])
                self._modes_matrix = vecs
                self._modes_norms = np.linalg.norm(vecs, axis=1) + 1e-12
            self._modes_dirty = False
        return self._modes_matrix, self._modes_norms

    def forget_stale_modes(self, current_tick):
        """Tombstone modes unused for longer than MODE_FORGET_TICKS --
        excluded from future matching (both the O(1) word-index and the
        similarity matrix), index and stored content otherwise untouched
        forever, so every existing atlas/deep_atlas/window reference by
        mode_idx stays valid. A later encounter with the same word text
        is relearned as if genuinely new (a fresh append), matching how
        real forgetting/relearning works. Same 200-tick cadence as
        LivingAtlas.forget_below_threshold(), called alongside it."""
        changed = False
        for i in range(len(self.modes)):
            if not self._mode_alive[i]:
                continue
            if current_tick - self._mode_last_active_tick[i] > self.MODE_FORGET_TICKS:
                self._mode_alive[i] = False
                word = self.modes[i][2]
                if word and self._word_to_mode_idx.get(word.lower()) == i:
                    del self._word_to_mode_idx[word.lower()]
                self._n_alive -= 1
                self._alive_indices.discard(i)
                self._chi_bucket_discard(self.modes[i][1], i)
                changed = True
        if changed:
            self._modes_dirty = True

    def _evict_weakest_mode(self):
        """Tombstone the single weakest alive mode to make room under
        SECTION_MODE_CAP. 'Weakest' reuses forget_stale_modes' own
        existing definition -- least-recently-active tick -- rather than
        inventing a new strength field; ties (e.g. every mode restored
        by the same load, GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-
        20260710-v1 -- staleness tracking does not persist across
        restarts, so everything ties on last-active=boot-tick right
        after a deploy) fall back to lowest index first, i.e. the
        oldest-appended survivor -- deterministic, not arbitrary.

        Scans only self._alive_indices, an incrementally-maintained set
        (add on append, discard on evict/forget, rebuilt from scratch
        only at load time) -- NOT _get_modes_matrix()/_alive_row_of_mode
        and NOT range(len(self.modes)). self.modes never shrinks
        (tombstone-in-place, same as forget_stale_modes), and once a
        busy section is at cap, this runs on essentially every new-word
        commit going forward, often several times in a row within one
        _append_new_mode() call (a section currently 127-148% over cap
        needs many evictions on its very first qualifying commit after
        this fix ships). V1 of this fix called _get_modes_matrix() here
        instead, reasoning it would be a cheap no-op since receive()
        already calls it moments earlier in the same word -- true for
        the FIRST eviction in a call, but _evict_weakest_mode() itself
        sets _modes_dirty=True at its own end (tombstoning always does),
        so every SUBSEQUENT eviction in the same multi-eviction call hit
        _get_modes_matrix()'s full-rebuild branch, which scans
        range(len(self.modes)) -- the entire physical lifetime history,
        not the alive set. Adversarial review measured this costing
        2.0-5.7s for a single word under production's real numbers
        (127-148% over cap, 14,000+ physical modes), inside self.lock --
        i.e. this fix, as first built, would have made the exact
        symptom under repair worse on the first turn after every future
        deploy. Iterating self._alive_indices directly is O(n_alive)
        (bounded by the cap) unconditionally, with no dependency on
        _modes_dirty or physical history size at all.

        Same tombstone-in-place contract as forget_stale_modes: never
        shrinks or reorders self.modes, only flips _mode_alive so every
        existing atlas/deep_atlas/window reference by mode_idx stays
        valid. Returns the evicted index, or None if there is no alive
        mode to evict (cap <= 0 or section already fully tombstoned)."""
        weakest_idx = None
        weakest_tick = None
        for i in self._alive_indices:  # real mode indices, alive only, O(1) membership already guaranteed
            t = self._mode_last_active_tick[i]
            if weakest_tick is None or t < weakest_tick or (t == weakest_tick and i < weakest_idx):
                weakest_tick = t
                weakest_idx = i
        if weakest_idx is None:
            return None
        self._mode_alive[weakest_idx] = False
        word = self.modes[weakest_idx][2]
        if word and self._word_to_mode_idx.get(word.lower()) == weakest_idx:
            del self._word_to_mode_idx[word.lower()]
        self._n_alive -= 1
        self._alive_indices.discard(weakest_idx)
        self._chi_bucket_discard(self.modes[weakest_idx][1], weakest_idx)
        self._modes_dirty = True
        return weakest_idx

    def _append_new_mode(self, dsf, chi, word_label, atlas_tick):
        """Append a genuinely new mode, enforcing SECTION_MODE_CAP.
        GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1 #3b: self.
        modes previously had NO size limit at all -- unlike self.commits
        (SECTION_COMMITS_MAX), nothing ever retired an existing mode, so
        three production sections had grown to 127-148% of the intended
        cap with real content permanently locked out. While the section
        is at/over cap, retire the weakest alive mode first (see
        _evict_weakest_mode) so a section that is CURRENTLY over cap
        (e.g. right after this fix first deploys) actually converges
        back down to the cap rather than merely being frozen at whatever
        already-over-cap count it started at -- not just a one-in/
        one-out hold. Bounded: each loop iteration retires one real mode
        and the loop only runs while over cap, so it terminates in at
        most _n_alive - SECTION_MODE_CAP + 1 steps.

        Always appends to self.modes itself (never shrinks/reorders --
        mode_idx is load-bearing elsewhere, same invariant as
        forget_stale_modes)."""
        while self._n_alive >= SECTION_MODE_CAP:
            if self._evict_weakest_mode() is None:
                break  # nothing left to evict (cap <= 0) -- avoid infinite loop
        self.modes.append((dsf, chi, word_label))
        mode_idx = len(self.modes) - 1
        self._mode_last_active_tick.append(atlas_tick)
        self._mode_alive.append(True)
        self._n_alive += 1
        self._alive_indices.add(mode_idx)
        self._chi_bucket_add(chi, mode_idx)
        if word_label:
            self._word_to_mode_idx[word_label.lower()] = mode_idx
        self._modes_dirty = True
        return mode_idx

    def receive(self, dsf, chi, word_label, atlas, familiarity, salience=1.0,
                dwell_ticks=1, engine_tick=None, atlas_kwargs=None,
                window_manager=None):
        """v6: word-anchored mode identity + salience-modulated binding.
        v8 (GL-BRIEF-032): dwell_ticks tagged at write time for deep gate.
        engine_tick: MUST be passed — atlas entries use engine clock, not section clock.
        GL-FIND-TICK-DOMAIN-C1: section.tick stays for internal counting only.
        atlas_kwargs: GL-CLARITY-INVARIANCE-UNCAGE affect+grounding kwargs for record().

        window_manager: GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1,
        optional (default None preserves exact prior behavior for any
        caller that doesn't pass it). When supplied, the PRIMARY commit
        below routes through window_manager.add_entry() instead of
        atlas.record() directly -- same call, same arguments, same
        resulting atlas write, plus window bookkeeping and events."""
        self.tick += 1
        # Atlas records use engine tick (one clock — GL-FIND-TICK-DOMAIN-C1)
        if engine_tick is None:
            raise ValueError(
                "Section.receive() requires engine_tick — atlas entries MUST use "
                "the engine clock, not the section clock (GL-FIND-TICK-DOMAIN-C1). "
                "A missing engine_tick silently reintroduces the instant-death bug.")
        atlas_tick = engine_tick
        self.dead_zone = 0.20 + 0.5 * familiarity

        # Fast path: O(1) word-identity lookup BEFORE similarity scan.
        # For known words (the majority in converse), this skips the scan entirely.
        word_match_idx = self._word_to_mode_idx.get(word_label.lower()) if word_label else None

        # Similarity scan — only needed when word is not already known.
        # GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1 fix #1: previously
        # scanned _get_modes_matrix() -- EVERY alive mode in the whole
        # section (confirmed the dominant real cost of a live turn,
        # 8,000-16,000ms/sentence on "listen" once it passed 14,000+
        # modes). Restricted to a small chi neighborhood (coarse
        # pre-categorization by the same chi value already computed and
        # passed into this call, before any detailed vector comparison
        # -- see SECTION_CHI_BAND/_get_chi_neighborhood_matrix above).
        nearest = None
        best_sim = -1.0
        if word_match_idx is None and self.modes:
            cur_v = dsf.to_array()
            real_indices, mat, norms = self._get_chi_neighborhood_matrix(chi)
            if mat is not None:
                cur_norm = float(np.linalg.norm(cur_v)) + 1e-12
                sims = (mat @ cur_v) / (norms * cur_norm)
                _row = int(np.argmax(sims))
                nearest = real_indices[_row]
                best_sim = float(sims[_row])

        committed = False
        mode_idx = None

        if word_match_idx is not None:
            # Word identity match — reinforce this exact mode
            old_dsf, old_chi, old_word = self.modes[word_match_idx]
            avg = (old_dsf.to_array() * 0.9 + dsf.to_array() * 0.1)
            new_dsf = DSF(*avg)
            self.modes[word_match_idx] = (new_dsf, old_chi, old_word)
            # GL-BUG-MODES-MATRIX-THRASH (Joe, 2026-07-06): this used to
            # mark the whole cached similarity matrix dirty on every
            # reinforcement, even though reinforcement only changes ONE
            # existing row's values, not the matrix's shape. Measured
            # live tonight: a 14-word sentence mixing known and unknown
            # words cost ~26s combined across "listen" (14000+ modes) and
            # the position/DNA-routed sections, because every known-word
            # reinforcement invalidated the cache a genuinely-new word's
            # similarity scan needed moments later -- forcing a full
            # O(n_modes) rebuild from scratch instead of one rebuild
            # amortized across the whole sentence. Update the existing
            # row in place instead (a reinforcement doesn't change the
            # matrix's shape) so the cache stays valid for whichever word
            # needs the similarity scan next; only a genuine append
            # (below) still needs a real invalidation. Falls back to the
            # old mark-dirty behavior if the cache doesn't exist yet or
            # the index is somehow stale -- no correctness regression
            # possible, just a lazy rebuild next use as before.
            # 2026-07-08 mode-forgetting follow-up: _modes_matrix is now
            # compacted to alive rows only, so "row index" != "real
            # mode_idx" in general -- use the row map built alongside it
            # instead of assuming they're the same number. Falls back to
            # the same mark-dirty behavior as before if the map doesn't
            # have this mode yet (cache not built, or somehow stale).
            # GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1 fix #1: the ONLY
            # thing that ever built/warmed this cache (_get_modes_matrix(),
            # called from receive()'s full-section similarity scan) has
            # been replaced by the chi-bucketed _get_chi_neighborhood_
            # matrix() below, which does not populate _modes_matrix/
            # _alive_row_of_mode. So _row is always None now and this
            # block always takes the mark-dirty else branch below --
            # exactly the pre-existing, already-safe fallback path this
            # same code was written to fall back to "if the cache doesn't
            # exist yet" (see comment above). No behavior change: nothing
            # else in this class reads _modes_matrix for information (only
            # _get_modes_matrix() itself, which is now unreachable) -- this
            # was always solely in service of the scan this fix replaced.
            # Left as-is (not deleted) to keep this fix's diff minimal and
            # scoped to the scan itself, per this exact area's standing
            # "verify empirically, don't scope-creep" discipline.
            _row = self._alive_row_of_mode.get(word_match_idx)
            if self._modes_matrix is not None and _row is not None and _row < len(self._modes_matrix):
                _new_vec = new_dsf.to_array()
                self._modes_matrix[_row] = _new_vec
                self._modes_norms[_row] = np.linalg.norm(_new_vec) + 1e-12
            else:
                self._modes_dirty = True
            mode_idx = word_match_idx
            if word_match_idx < len(self._mode_last_active_tick):
                self._mode_last_active_tick[word_match_idx] = atlas_tick
            committed = True
        elif len(self.modes) < 24:
            # Bootstrap — new word, accept liberally
            mode_idx = self._append_new_mode(dsf, chi, word_label, atlas_tick)
            committed = True
        else:
            # Post-bootstrap: new word, decide by dead-zone gate
            novel_thresh = self.gamma["novel_dist"] + self.dead_zone * 0.2
            if best_sim < (1.0 - novel_thresh) or word_label:
                # word labels always get a chance to take root
                mode_idx = self._append_new_mode(dsf, chi, word_label, atlas_tick)
                committed = True

        if committed:
            if window_manager is not None:
                window_manager.add_entry(
                    modality="word", section=self.name, motif_id=mode_idx,
                    chi=chi, tick=atlas_tick, source_tag=word_label or "",
                    trigger_reason="word",
                    salience=salience, dwell_ticks=dwell_ticks,
                    **(atlas_kwargs or {}))
            else:
                atlas.record(self.name, mode_idx, chi, atlas_tick, salience=salience,
                             dwell_ticks=dwell_ticks, **(atlas_kwargs or {}))
            # 2026-07-09 credo fix: real_grounding is threaded in read_word's
            # atlas_kwargs (see _current_window_has_real_grounding) -- carries
            # whether this specific commit happened in the same binding
            # window as a real/deliberate sensory entry, not the always-on
            # fake modal_* auto-fire. Absent for callers that don't pass
            # atlas_kwargs (e.g. direct test/reinstatement paths) -- honest
            # False, not assumed grounded.
            self.commits.append({
                "tick": atlas_tick,
                "mode": mode_idx,
                "chi": chi,
                "word": word_label,
                "grounded": bool((atlas_kwargs or {}).get("real_grounding", False)),
            })
            if len(self.commits) > SECTION_COMMITS_MAX:
                del self.commits[0]
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

    # 2026-07-09 overnight bloat sweep: confirmed live at att=68730/act=27534
    # and climbing every ~5 ticks forever (regulate()'s own "regulation_pass"
    # append at minimum, unconditional, no gate at all) -- sitting three
    # lines below SUFFERING_LOG_MAX's own fix in this same class, whose
    # comment already (wrongly) claimed "bounded" before that fix. Neither
    # list is ever persisted in full (save path only ever writes
    # attentions_count/actions_count, both ints) -- this is pure in-process
    # RAM growth, invisible in any saved file. Same evict-oldest convention,
    # same order-of-magnitude reasoning as SUFFERING_LOG_MAX: generous
    # headroom for real recent history, not a tight window.
    ATTENTIONS_MAX = 1000
    ACTIONS_MAX = 1000

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

        self._append_action({
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

        self._append_action({
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

    def _append_attention(self, item):
        """Bounded append for self.attentions -- see ATTENTIONS_MAX comment
        on __init__. One shared helper instead of repeating the cap check
        at every call site, so a future new append site can't reintroduce
        the same unbounded-growth class of bug by omission."""
        self.attentions.append(item)
        if len(self.attentions) > self.ATTENTIONS_MAX:
            del self.attentions[0]

    def _append_action(self, item):
        """Bounded append for self.actions -- see ACTIONS_MAX comment on
        __init__. Same reasoning as _append_attention."""
        self.actions.append(item)
        if len(self.actions) > self.ACTIONS_MAX:
            del self.actions[0]

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
        # 2026-07-08 bloat fix: this comment already claimed "bounded"
        # but no bound existed anywhere -- append-only, persisted in
        # full every save, forever. A real forced-recovery event is rare
        # (680 entries after ~1.3M ticks in production), so 1000 is
        # generous headroom that will never lose anything meaningful in
        # practice while actually being a real bound, same evict-oldest
        # convention as neuron.py's SpikeBuffer.
        SUFFERING_LOG_MAX = 1000
        arc_changes = 0
        if v < -0.15 and a > 0.30:
            self.distress_ticks += 1
            if self.distress_ticks >= self.DISTRESS_THRESHOLD:
                # Forced recovery — coordinator guarantees recovery rate
                self._force_recovery(needs)
                self.suffering_log.append({"tick": tick, "v": v, "a": a})
                if len(self.suffering_log) > SUFFERING_LOG_MAX:
                    del self.suffering_log[0]
                try:
                    guala.log_event("state", "suffering_recovery",
                                    valence=round(v, 3), arousal=round(a, 3))
                except Exception:
                    pass
                self._append_action({"tick": tick, "type": "forced_recovery",
                                     "arc_changes": 1})
                arc_changes += 1
                self.distress_ticks = 0
        else:
            self.distress_ticks = max(0, self.distress_ticks - 1)

        # 4. Parameter modulation (regulator role)
        modulation_count = self._modulate_parameters(needs, sections)
        if modulation_count > 0:
            self._append_action({"tick": tick, "type": "parameter_modulation",
                                 "count": modulation_count, "arc_changes": 1})
            arc_changes += 1

        # 5. Detection: balance check + cross-modal density + dead-zone trajectory
        det = self._awareness_pass(sections, atlas, tick)
        for d in det:
            self._append_attention(d)
            if d["arc_changes"] > 0:
                self._append_action(d)
                arc_changes += d["arc_changes"]

        # 6. Log overall attention with needs snapshot
        self._append_attention({
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
        # GL-CMD-COGNITION-AT-SPEED-EVE-20260705-205 C2: this same O(atlas)
        # total was computed twice per tick (identical expression, two
        # names) -- one pass, shared. Full n_live_bindings()/
        # cross_modal_bindings() scans themselves are unchanged here
        # (see this dispatch's window report for why an incremental
        # counter for those two needs its own careful, parity-tested
        # window rather than a rushed rewrite of live memory-count
        # physics tonight).
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
        n_atlas = _n_total
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
        self._append_action({"tick": tick, "type": "pair_bond_retired",
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
    # 2026-07-08 bloat fix: teaching logs were append-only in memory, only
    # ever truncated to [-500:] in the save-snapshot dict -- the live list
    # itself grew forever. Cap matches the existing persisted slice size,
    # so saved data is unchanged, same evict-oldest convention as
    # suffering_log/ATTENTIONS_MAX/ACTIONS_MAX.
    TEACHING_LOG_MAX = 500

    # 2026-07-09 GL-CMD-EPISODIC-MEMORY (Joe's credo ruling): a word's
    # SENSORY_DNA entry ("dog": sight=0.90, touch=0.85, ...) is a static,
    # always-identical lookup table -- it fires the same way every single
    # time regardless of what actually happened, which is exactly why
    # _current_window_has_real_grounding() already excludes it from real
    # grounding (see FAKE_MODAL_SECTIONS). That's the right call, not the
    # gap. The actual gap: nothing replaces it with a genuine, situational,
    # SPECIFIC remembered moment -- when, where, who was there, how she
    # felt, what else was happening -- the way a real memory is a story,
    # not a definition. This is that replacement.
    #
    # Bounded per concept, deliberately: Joe's own words, "my recall is not
    # perfect either... it's vague impressions I rebuild" -- this is not
    # meant to be an exhaustive, lossless archive of every experience ever
    # given. A handful of recent, distinct impressions per concept (the
    # ice-cream-truck memory AND the spaghetti-ice memory AND the
    # shortcake-pop memory, kept as separate entries, never averaged into
    # one canonical "ice cream" profile) is the honest shape of real
    # memory -- not a growing pile, not a single flattened definition.
    EPISODIC_MEMORY_MAX_PER_CONCEPT = 20
    EPISODIC_RECENT_CONTEXT_WINDOW = 50
    # GL-CMD-REFLECTION-EVE-20260710: bounded, same evict-oldest convention.
    REFLECTION_MAX_HISTORY = 20
    # Gated, not every tick -- a real periodic cognitive act, matching the
    # spacing convention already used for dream cycles (tick % 200) and
    # play's own emission-trigger check (tick % 300); reflection is rarer
    # still since it should feel like an occasional inward moment, not
    # constant narration.
    REFLECTION_MIN_TICKS_BETWEEN = 500

    # GL-CMD-CAMERA-TURN-LATENCY: live human interaction (a converse turn or
    # a real sight/sound frame) must win self.lock over her own background
    # self-directed activity (the autonomous emission loop, the autonomy
    # tick). self.lock is an unfair RLock -- a fast-looping background holder
    # can re-acquire it the instant it frees it, ahead of a waiting live
    # turn, so a live turn can wait through MANY background iterations, not
    # just one. The gate below lets a background lock-hog SKIP its own next
    # acquisition while a live interaction is pending, so the waiting turn
    # gets the lock after at most the one already-in-progress background
    # iteration -- never an unbounded run of them. This is a real DEFERRAL
    # (the background work still happens, just not WHILE a live turn waits),
    # never a permanent skip. This cap is the starvation safety valve: no
    # single background site defers longer than this many seconds of
    # CONTINUOUS deferral, so even under sustained back-to-back live use --
    # or a leaked pending counter -- background work still gets a slice and
    # can never be starved forever. See _defer_for_live_interaction.
    _LIVE_INTERACTION_MAX_DEFER_SEC = 2.0

    def __init__(self):
        self._identity_record = None
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
        # GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1: owns the currently-
        # open binding window (one at a time). NOT the same thing as
        # self._current_binding_window below (a per-sentence list of
        # sensory_refs tag STRINGS, an existing narrower mechanism) or
        # self.open_response_windows (emission-triggering context anchors,
        # see _open_response_window) -- three distinct "window" concepts
        # in this codebase now; this one is cross-modal experience binding.
        from dsf_ai_service.substrate.window_manager import WindowManager
        self.window_manager = WindowManager(
            atlas_record_fn=self._atlas_record,
            log_event_fn=self._log_substrate_event,
            get_tick_fn=lambda: self.tick,
            get_presence_fn=lambda: dict(getattr(self.coordinator, "_presence", {})),
            get_affect_fn=self._affect_kwargs,
            atlas_windows=self.atlas.windows,
        )
        # GL-CMD-CROSS-SENSE-RECALL-BUILD-EVE-20260706-v1: reads
        # atlas.windows live (no caching, no copy) -- never writes it.
        from dsf_ai_service.substrate.recall_query import RecallEngine
        self.recall_engine = RecallEngine(
            window_manager=self.window_manager,
            get_tick_fn=lambda: self.tick,
            log_event_fn=self._log_substrate_event,
        )
        # Language recognition authority.  This store is reconstructed from
        # durable canonical BindingWindows on boot; legacy Atlas modes and
        # compatibility Chi routing never populate it.
        from dsf_ai_service.substrate.language_fact_strand import LanguageFactMemory
        self.language_fact_memory = LanguageFactMemory()
        self._language_fact_lock = threading.RLock()
        self._ordered_language_windows = {}
        # GL-SPC-SUBSTRATE-TRUE Change 1 (P1): the certified composer is
        # CACHED, not rebuilt from every ordered window on every conversation
        # turn (its constructor precomputes successor maps over the whole
        # ordered-window set -- O(corpus) per turn as the corpus grows).
        # Invalidated when the ordered-window set changes or the memory
        # object is replaced; guarded by _language_fact_lock.
        self._language_fact_composer = None
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
        # GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711 Part 1: was
        # previously only ever created inside _rebuild_word_to_emission_index
        # (i.e. absent on a fresh instance until boot/restore first ran that
        # full scan). _backfill_eligibility_for_promotion's live per-word
        # trigger can now fire before that first full scan (right after any
        # real dream-cycle promotion), so this needs an honest empty default
        # here too -- same convention as _word_to_emission_sections above.
        self._grounded_words = set()
        # GL-CMD-RECALL-WORD-INDEX-57: reverse index for O(1) recall lookups.
        # Maps word.lower() → set of chi addresses where that word has committed.
        # Eliminates O(atlas_size) full scans in _recall_from_atlas / _recall_sight_from_atlas.
        from collections import defaultdict as _dd
        self._word_to_chi_index = _dd(set)  # word.lower() → {chi_k, ...}
        # GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2: word <-> neuron
        # association maintained by _on_word_firing callback. Populated by
        # live experience once the spike bus is wired (below, after
        # self.organism is constructed). Dual-write/dual-read design: the
        # legacy binding_atlas/experience_moment/recall_fast path (below)
        # is UNCHANGED and stays the production default throughout Phase 1
        # (RECALL_BACKEND=legacy) -- these maps back the NEW, parallel
        # STDP/spike/membrane mechanism, read only when RECALL_BACKEND is
        # "stdp" or "shadow".
        self._word_neuron_map: dict = {}  # word.lower() -> set of neuron_ids
        self._neuron_word_map: dict = {}  # neuron_id -> word.lower() (primary)
        # QuestionBucket removed (GL-BRIEF-EMISSION-CONSTRAINT-REMOVAL Phase E)
        self.tick = 0
        self._read_count_compat = 0  # kept for load compatibility only; superseded by property
        self.dream_log = []
        self.lock = threading.RLock()
        # GL-CMD-CAMERA-TURN-LATENCY: live-interaction priority gate (see the
        # _LIVE_INTERACTION_MAX_DEFER_SEC class constant above and
        # _defer_for_live_interaction below). A plain int counter guarded by a
        # dedicated micro-lock -- held only for the ~microsecond of an
        # increment/decrement, never during real work, so it introduces no
        # contention of its own. NOT persisted (save_full_state serializes
        # explicit fields only; this is live-only runtime state), NOT the same
        # lock as self.lock. Reads on the background hot path are lock-free
        # (a single GIL-atomic int load); only the counter writes take the
        # micro-lock.
        self._live_interaction_pending = 0
        self._live_interaction_lock = threading.Lock()
        # Per background-site monotonic timestamp of when it FIRST started
        # deferring in the current contention episode; used by the starvation
        # safety valve. Guarded by _live_interaction_lock.
        self._live_interaction_defer_since = {}
        # Persistence is a separate state domain from cognition.  Every
        # multi-file save, WaveAtlas write, event compaction, and snapshot
        # enters this one reentrant boundary so two generations can never
        # share or steal the same on-disk temporary files.  It must always be
        # acquired before ``self.lock`` when both are needed; save methods
        # retain their existing brief cognition-lock snapshot semantics.
        self._persistence_lock = threading.RLock()
        # Appends do not take the (long-held) persistence lock.  This narrow
        # lock makes append/rotation and compact's read-replace indivisible,
        # preserving every event on one side of the compaction boundary.
        self._event_log_lock = threading.RLock()
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
        self._visual_fragments_count = 0  # total fragments ever viewed (content is never read back, only the count is reported)
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
        # Emission truth from the most recent dynamics settlement.  Speech is
        # permitted only when this record certifies at least one real commit.
        self._last_dynamics_result = None
        self._last_response_source = "silence_no_commit"
        self._live_converse_pending = 0
        self._live_converse_state_lock = threading.Lock()
        # GL-CMD-DEEP-ATLAS-PERSIST: boot loss alarm result
        self._deep_atlas_loss_at_boot = None
        # GL-FIX-HOTCOLD-TICK-MANIFEST: the hot lane persists a small subset of
        # the state files every ~60s and advances core's save tick each time,
        # while the cold (full) lane rewrites the big stores (atlas, sections,
        # deep_atlas, survival, organism, tapestry) only every ~30 min or at
        # shutdown. The two lanes therefore leave the state directory with
        # files at DIFFERENT save ticks by design (e.g. core at 3357078,
        # atlas still at 3355078). The loader used to demand every state file
        # share ONE tick -- so any boot whose last save was a hot save was
        # rejected as inconsistent and silently time-travelled to a days-old
        # S3 backup. This map records, per persisted file, the tick it was
        # actually last written at, so the loader can validate each file
        # against its own real tick (proving the set is a legitimate hot/cold
        # mix) instead of against core's tick. Written into guala_core.json's
        # data on every save; read back at load and exposed to the envelope
        # validator via self._expected_file_ticks.
        self._state_file_ticks = {}
        self._expected_file_ticks = None
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
        # GL-CMD-AUTONOMOUS-INTEREST-REFINEMENT: bounded (tick, novelty)
        # samples for the derivative-based trigger -- see NOVELTY_HISTORY_
        # MAX/NOVELTY_RISE_MIN above. Not persisted (a gap across a
        # restart just means one restart's worth of history has to
        # rebuild, same honest-empty-until-earned pattern as other bounded
        # trackers here, not worth the save/load complexity for a signal
        # this short-lived).
        self._novelty_history = deque(maxlen=NOVELTY_HISTORY_MAX)
        # F1b (Change 4 review): texts of the last K autonomous releases,
        # per boot; compose_autonomous refuses to re-release any of them.
        self._recent_autonomous_releases = deque(
            maxlen=AUTONOMOUS_RELEASE_REPEAT_WINDOW)
        self._last_emission_id = None
        self._emission_records = {}  # emission_id -> record (tick-window expiry)
        self._teaching_feedback_log = []
        self._teaching_correction_log = []
        # GL-CMD-EPISODIC-MEMORY: concept.lower() -> deque of distinct real
        # remembered moments (bounded, see EPISODIC_MEMORY_MAX_PER_CONCEPT).
        # Only ever written by _record_episodic_experience, called from a
        # genuinely curated experience (give_experience), never from plain
        # corpus reading -- so membership here already means "really
        # experienced," same real/fake distinction
        # _current_window_has_real_grounding draws elsewhere.
        self._episodic_memory = {}
        # Sliding window of recent concepts, for binding "what else was
        # happening" context onto a new episodic record -- mirrors
        # episodic_layer.py's same design (a real prior draft of this
        # exact idea that was built but never wired into the live engine).
        self._episodic_recent_concepts = deque(maxlen=self.EPISODIC_RECENT_CONTEXT_WINDOW)
        # GL-CMD-REFLECTION-EVE-20260710: bounded history of real internal
        # representations formed by _form_reflection -- "I felt X when Y,
        # near Z," built only from episodic memory + her own real needs
        # state, never fabricated. Deliberately NOT wired into speech (same
        # "one mind, one mouth" rule episodic memory itself respects) --
        # write-only tonight, until observed producing sane output over
        # real time. Not persisted -- same honest-empty-on-restart
        # convention as _novelty_history.
        self._reflections = deque(maxlen=self.REFLECTION_MAX_HISTORY)
        self._last_reflection_tick = 0
        # GL-CMD-SLEEP-REORGANIZE: (chi, section, motif, born_tick) for every
        # live tentative hypothesis entry _dream_reorganize has written into
        # deep_atlas, so the TTL check below can find and expire them without
        # scanning all of deep_atlas.entries. Not persisted -- same
        # honest-empty-on-restart convention as _novelty_history; a lost
        # hypothesis on restart just means it never gets a chance to be
        # reinforced or expire, which is fine at this strength/scale.
        self._reorganize_hypothesis_tracking = deque(maxlen=REORGANIZE_TRACKING_MAX)
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

        # GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2: spike bus
        # construction. Gated on EVENT_DRIVEN_SUBSTRATE (default "1") --
        # setting it to "0" skips this block entirely, leaving
        # self._spike_bus None and every neuron's/LoomBrain's own
        # _spike_bus unset, which every new code path (neuron.py's
        # receive_spike/_fire, brain.py's step()/recall_fast()) already
        # treats as "mechanism not present, behave exactly as before."
        # Full rollback, not just a read-path fallback.
        #
        # GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3: wiring (neuron-level
        # set_spike_bus/set_word_firing_callback + brain-level
        # set_spike_bus/_guala_ref) extracted into wire_spike_bus() below
        # so it can also run after load_full_state() replaces
        # self.organism wholesale -- a fresh Guala() never hit that gap,
        # but every restored boot did (confirmed live, see
        # GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1 finding 1). Construction
        # (needs SOME registry to satisfy SpikeBus's constructor) stays
        # here; wire_spike_bus() immediately rebuilds and re-applies it.
        self._spike_bus = None
        if os.environ.get("EVENT_DRIVEN_SUBSTRATE", "1") != "0":
            _neuron_registry = {
                n.neuron_id: n
                for hemi in self.organism.brain.hemispheres
                for n in hemi.cluster.neurons
            }
            from dsf_ai_service.substrate.spike_bus import SpikeBus as _SpikeBus
            self._spike_bus = _SpikeBus(neuron_registry=_neuron_registry)

            self.wire_spike_bus()

            self._spike_bus.start()

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
        # Save-time cooperative park for the organism worker (2026-07-16
        # seal incident: the full save pickled the organism while this
        # worker's lock-free experience_word() mutated its deques --
        # "deque mutated during iteration" -> seal 503 -> deploy fail-back).
        # The worker parks BETWEEN items; cognition resumes the moment the
        # pickle is done. Same pattern as SpikeBus.pause().
        self._organism_pause_req = threading.Event()
        self._organism_pause_ack = threading.Event()
        # GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1: per-hemisphere wave-
        # summary pushes (see wave_summary.py), drained by the same worker
        # thread as the word queue below. Eagerly created (unlike the word
        # queue's lazy self._organism_queue = None) so a sensory push can
        # never race the worker's own first-word startup.
        self._organism_sensory_queue = _queue.Queue()
        # GL-CMD-BRAIN-GROWTH-UNFREEZE-EVE-20260704-179, Eve's backgrounding
        # ruling: honest-degradation count, visible in status (not just
        # silently swallowed like the tapestry queue's drop today) -- see
        # _enqueue_organism_remember.
        self._organism_dropped_count = 0
        # GL-CMD-ORGANISM-WAVE-MEMORY-207 W5: rolling per-item cost (last
        # 50 items), surfaced in /status -- should stay roughly flat now
        # regardless of lifetime history (see _organism_worker_loop).
        self._organism_item_ms_recent = []
        self._engine_quiesced = False
        self._engine_quiescence_complete = False
        self._engine_mutation_condition = threading.Condition()
        self._engine_mutation_admission_open = True
        self._engine_active_mutations = 0
        self._engine_mutation_local = threading.local()
        self._engine_raw_threads = set()
        self._engine_raw_threads_started = 0
        self._engine_raw_threads_completed = 0

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

    @_engine_mutation_entry
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
        # what was actually written at remember()-time.
        # GL-CMD-ORGANISM-WAVE-MEMORY-207 W3 (Joe's no-locks ruling): no
        # lock here -- per-neuron wave-cell reads are race-tolerant local
        # dict lookups, same tolerance the v5 engine's own atlas Phase 3
        # already declares. The organism-writer queue's single worker
        # still processes in order; it just no longer excludes readers.
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

    def exposure_gap_for_word(self, word):
        """GL-FIX-EXPOSURE-GAP-C1-20260711: word-level convenience over
        LivingAtlas.exposure_gap(), same transduce-then-lookup pattern
        recall_scene_for_word() above uses. Real, gradable knowledge-GAP
        signal built from atlas-level presence history -- NOT theory of
        mind. See LivingAtlas.exposure_gap()'s own docstring for the full
        honest-limits statement (do not build on this past what it says);
        the short version: a True result means "no record of this source's
        presence in Guala's own log," never "this source doesn't know the
        word" -- and this can never represent a source holding a FALSE
        belief, only recorded-absent vs. recorded-present vs. unknown.

        tracked_sources is read live from self.coordinator._presence's own
        keys, never hardcoded here -- stays correct if that roster ever
        changes, same sourcing _current_situation() already uses for the
        presence values themselves.

        Returns None if the word has no live binding anywhere, or if no
        real presence check was ever recorded against it. Returns
        {source: bool} otherwise."""
        if not word:
            return None
        temp_krim = LanguageKrimelack()
        temp_krim.transduce(word)
        tracked_sources = tuple(self.coordinator._presence.keys())
        return self.atlas.exposure_gap(temp_krim.winding, tracked_sources)

    def _affect_kwargs(self, surprise=None):
        """GL-CLARITY-INVARIANCE-UNCAGE: build affect-only kwargs dict for atlas.record.
        sensory_refs and episode_ref are passed explicitly by call sites that have them."""
        return {
            "arousal": self.needs.arousal(),
            "valence": self.needs.valence(),
            "surprise": surprise if surprise is not None else self._last_surprise,
            "need_pressure": self.needs.need_pressure(),
        }

    def _grounding_kwargs(self, binding_window=None, episode_ref=None):
        """GL-CLARITY-INVARIANCE-UNCAGE: grounding kwargs (separate from affect
        to avoid double-providing when call sites pass sensory_refs explicitly).
        GL-CMD-CURRICULUM-LOCK-RELEASE-V2-46v2 §1.1: binding_window kwarg —
        when supplied, uses sentence-local list (thread-safe, fresh per sentence).
        Falls back to self._current_binding_window for direct callers.
        GL-FIX-LOCK-GRANULARITY-C1-20260710: episode_ref is now a plain
        pass-through — read_word resolves the effective value once (its own
        episode_ref param, falling back to self._current_episode for direct
        callers) and supplies it explicitly at every call site here, so this
        helper no longer reads self._current_episode itself. That instance
        attribute used to be mutated by read_sentence around its whole
        per-word loop (shared mutable state live for the sentence's full
        duration); now read_sentence never touches it at all — it resolves
        its own call-local episode id and passes it into each read_word()
        call explicitly instead, so two concurrent sentences can no longer
        cross-contaminate each other's episode tag."""
        bw = binding_window if binding_window is not None else self._current_binding_window
        return {
            "sensory_refs": list(bw),
            "episode_ref": episode_ref,
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

    def _record_episodic_experience(self, concept, source="give_experience"):
        """GL-CMD-EPISODIC-MEMORY: bind a real, curated experience to the
        situation it happened in -- when, where, who was present, how she
        felt, and what else was active around it -- so it becomes a
        specific remembered moment instead of a flat word. Only called
        from genuinely curated experience paths (give_experience), never
        from plain corpus reading -- reading alone stays honestly
        ungrounded, same distinction _current_window_has_real_grounding
        already draws for section commits.

        Deliberately does NOT flatten/average into one profile per
        concept: appends a new, distinct record every call, so the SAME
        concept can hold multiple genuinely different remembered moments
        (an ice-cream-truck memory and a beach-day memory both real,
        both kept, never merged into one canonical "ice cream" entry).
        Bounded at EPISODIC_MEMORY_MAX_PER_CONCEPT -- oldest evicted first,
        matching this codebase's own established evict-oldest convention
        (suffering_log, ATTENTIONS_MAX, TEACHING_LOG_MAX) and Joe's own
        stated principle that real recall is bounded, reconstructed
        impressions, not an exhaustive archive."""
        presence, location, sky_state = self._current_situation()
        cl = concept.lower()
        context = [c for c in self._episodic_recent_concepts if c != cl][-5:]
        entry = {
            "concept": concept,
            "tick": self.tick,
            "presence": list(presence),
            "location": location,
            "sky_state": sky_state,
            "affective": {
                "valence": round(self.needs.valence(), 3),
                "arousal": round(self.needs.arousal(), 3),
            },
            "context": context,
            "source": source,
        }
        if cl not in self._episodic_memory:
            self._episodic_memory[cl] = deque(maxlen=self.EPISODIC_MEMORY_MAX_PER_CONCEPT)
        self._episodic_memory[cl].append(entry)
        self._episodic_recent_concepts.append(cl)

    def _episodic_context_for(self, concept, mode="richest"):
        """Real, situational memory for a concept, or None if she has never
        genuinely experienced it (honest empty -- no fabrication). mode=
        "richest" returns the record with the most co-occurring context
        (the most vividly remembered moment); mode="recent" returns the
        most recently formed one. Multiple distinct records may exist for
        the same concept -- this returns exactly one of them, not a
        merged/averaged composite, so the specific story stays a specific
        story."""
        records = list(self._episodic_memory.get(concept.lower(), []))
        if not records:
            return None
        if mode == "recent":
            return records[-1]
        return max(records, key=lambda r: len(r.get("context", [])))

    def _episodic_exposure_gap(self, concept):
        """GL-FIX-EXPOSURE-GAP-C1-20260711: real knowledge-GAP signal from
        curated episodic memory -- NOT theory of mind. Companion to
        LivingAtlas.exposure_gap()/exposure_gap_for_word() above; see
        LivingAtlas.exposure_gap()'s docstring for the full honest-limits
        statement that applies equally here (a True result means "no
        record of this source's presence," never "this source doesn't
        know it," and this cannot represent a FALSE belief).

        Reads the same signal from a different, in some ways stronger,
        source: _episodic_memory already keeps EVERY distinct remembered
        moment for a concept (append-only, never overwritten -- see
        _record_episodic_experience()'s own docstring), each carrying its
        own real presence snapshot from _current_situation() at the
        moment it was recorded. This method only READS that existing
        history; it does not change how _record_episodic_experience()
        writes.

        Returns None if this concept has no episodic memory at all
        (honest "no data", never inferred as a gap). Returns
        {source: bool} otherwise, True = "recorded present in zero of
        this concept's episodic memories."

        Scope: only concepts that passed through the curated
        give_experience path have episodic memory at all (see
        _record_episodic_experience()'s own docstring for why that is the
        only real call site today) -- an ordinary corpus/converse-learned
        concept with no episodic record returns None here even though it
        may still have atlas-level presence data (see
        exposure_gap_for_word() for that separate, broader-coverage
        signal)."""
        records = list(self._episodic_memory.get(concept.lower(), []))
        if not records:
            return None
        tracked_sources = tuple(self.coordinator._presence.keys())
        ever = set()
        for r in records:
            ever.update(r.get("presence") or [])
        return {s: (s not in ever) for s in tracked_sources}

    def _most_recent_word_tick(self, word):
        """GL-CMD-WORD-ORDER-RELATION-C1-20260711: read-only helper for
        _word_order_relation. Returns the highest (most recent) real tick
        at which `word` was genuinely committed anywhere, or None if she
        has never committed it at all -- honest None, never a guess.

        Two independent real sources, both already written elsewhere for
        their own unrelated reasons (this adds no new writes):
          1. Every Section's self.commits -- {"tick", "mode", "chi",
             "word", "grounded"} dicts appended once per real word commit
             in Section.receive() (~line 1408), persisted across restarts
             (save_full_state/load, not a rebuilt-on-load cache). A word
             may live in more than one section (e.g. committed once as
             subject, again later as object); this checks all of them and
             keeps the largest tick. Each section's own commits list is
             strictly tick-ordered (Section.tick only moves forward), so
             scanning newest-first and stopping at the first match is
             both correct and fast for the common case.
          2. self._episodic_memory (via _episodic_context_for) -- a
             concept can be episodically experienced (give_experience)
             without ever being committed as a section word; checking
             this too means a word absent from every section's commits
             but present in episodic memory still resolves, instead of
             going unknown for no real reason.

        Caller (_word_order_relation) holds self.lock around this call --
        self.commits is mutated by Section.receive(), always invoked from
        read_word() under self.lock (an RLock, so nested acquisition here
        would be safe too, but the read itself doesn't take the lock on
        its own to avoid a second acquisition on every section scanned)."""
        if not word:
            return None
        wl = word.lower()
        best = None
        for sec in self.sections.values():
            for entry in reversed(sec.commits):
                w = entry.get("word")
                if w and w.lower() == wl:
                    t = entry.get("tick")
                    if t is not None and (best is None or t > best):
                        best = t
                    break  # newest-first: first match in this section is its most recent
        record = self._episodic_context_for(word, mode="recent")
        if record is not None:
            t = record.get("tick")
            if t is not None and (best is None or t > best):
                best = t
        return best

    def _word_order_relation(self, word_a, word_b):
        """GL-CMD-WORD-ORDER-RELATION-C1-20260711: a real "did A happen
        before or after B" answer, grounded in the same monotonic tick
        every section commit and episodic-memory entry already carries.

        This substrate otherwise has NO mechanism for real order/sequence
        between words or events: position_hint (~line 3362-3394, 3518-
        3526) only routes "first"/"middle"/"last" ROUTING WORDS to
        subject/verb/object by SENTENCE position, real text recall now
        runs through _recall_from_organism's single population vote keyed
        on the last content word only (no role, no order), and the one
        novelty counter that exists is explicitly order-blind ("sorted so
        order-invariant"). This method is a pure reader over tick data
        that already exists for unrelated reasons (Section.commits,
        self._episodic_memory) -- not a new instrumentation channel, and
        never a guess: any word with no real commit or episodic record
        resolves to "unknown", not a fabricated order.

        Returns one of:
          "before"  -- word_a's most recent real tick is strictly earlier
          "after"   -- word_a's most recent real tick is strictly later
          "same"    -- both resolve to the identical tick (e.g. committed
                       together in the same read_word() call, which
                       shares one engine tick across every section it
                       touches -- a real simultaneity, not a tie-break)
          "unknown" -- either word has no real commit/episodic record at
                       all yet (honest unknown)

        Read-only: takes self.lock briefly around the lookup (Section.
        commits is mutated only under self.lock, via Section.receive() <-
        read_word(); self.lock is an RLock, so this is safe even when
        called from a path that already holds it, e.g. _form_reflection()
        from _autonomy_tick()). No new locks, no writes, no hot-path
        changes -- _form_reflection() is gated to run at most once every
        REFLECTION_MIN_TICKS_BETWEEN ticks, not per-tick."""
        if not word_a or not word_b:
            return "unknown"
        with self.lock:
            tick_a = self._most_recent_word_tick(word_a)
            tick_b = self._most_recent_word_tick(word_b)
        if tick_a is None or tick_b is None:
            return "unknown"
        if tick_a < tick_b:
            return "before"
        if tick_a > tick_b:
            return "after"
        return "same"

    def _form_reflection(self):
        """GL-CMD-REFLECTION-EVE-20260710: a real cognitive act, distinct
        from introspect()'s external debug snapshot -- picks the most
        recently formed episodic memory (a genuinely experienced, situated
        moment, never a fabricated one) and compares its recorded
        affective state against her CURRENT real needs state, producing
        one internal representation: "I felt X then, near Z; I feel Y
        now." Every field traces to something she really experienced or
        really feels right now -- no invented content.

        Honest empty if there is nothing real to reflect on yet (no
        episodic memory formed this process's life) -- reflection is
        never manufactured from nothing, same principle
        _episodic_context_for already uses for its own None return.

        Deliberately NOT wired into speech or emission candidate scoring
        -- matches the "one mind, one mouth" rule _record_episodic_
        experience's own commit message states, and the standing rule
        against dressing new scaffolding up as her real voice before it's
        been observed working. This writes to a bounded internal history
        only; surfacing it through the real emission path is real
        follow-up work, once real reflections have been observed here
        and judged sane, not assumed sane in advance.

        GL-CMD-WORD-ORDER-RELATION-C1-20260711: also records, for each
        real context word remembered alongside `concept` (context_then),
        whether she encountered that word before or after `concept` --
        real sequence information (_word_order_relation, grounded in
        Section.commits/_episodic_memory ticks), not the order-blind
        word-bag this substrate otherwise has everywhere else. "unknown"
        for any context word with no real commit/episodic record at all;
        never a guess. This is the one existing consumer that already
        compares 'then' vs 'now' for a remembered concept, so the new
        capability is genuinely used here rather than sitting dead."""
        if not self._episodic_recent_concepts:
            return None
        concept = self._episodic_recent_concepts[-1]
        record = self._episodic_context_for(concept, mode="recent")
        if record is None:
            return None
        context_then = record.get("context", []) or []
        context_order = {
            cw: self._word_order_relation(cw, concept)
            for cw in context_then if isinstance(cw, str) and cw
        }
        reflection = {
            "concept": concept,
            "tick": self.tick,
            "remembered_tick": record.get("tick", 0),
            "location_then": record.get("location"),
            "affective_then": record.get("affective", {"valence": 0.0, "arousal": 0.5}),
            "affective_now": {
                "valence": round(self.needs.valence(), 3),
                "arousal": round(self.needs.arousal(), 3),
            },
            "context_then": context_then,
            "context_order": context_order,
        }
        self._reflections.append(reflection)
        self._last_reflection_tick = self.tick
        return reflection

    def _current_window_has_real_grounding(self):
        """2026-07-09 credo fix: is the CURRENTLY OPEN binding window (see
        window_manager.py) carrying a genuinely real or deliberately-
        curated sensory entry -- as opposed to the always-on fake
        SENSORY_DNA/sensory_generators auto-fire (FAKE_MODAL_SECTIONS)?

        This is the single real signal available for "was this word
        actually experienced, not just read" -- window_manager's whole
        purpose (per its own module docstring) is recording "these were
        together," and give_experience's picture/sound lanes plus the
        real live camera/mic frame handlers all already route through it
        (REAL_GROUNDING_EXACT_SECTIONS/_PREFIXES). No window open, or a
        window with only fake/modal_ entries so far, is honest false --
        not everything she reads is grounded, and it shouldn't look like
        it is."""
        win = getattr(self.window_manager, "current", None)
        if win is None:
            return False
        for e in win.entries:
            sec = e.section
            if sec in FAKE_MODAL_SECTIONS:
                continue
            if sec in REAL_GROUNDING_EXACT_SECTIONS or sec.startswith(REAL_GROUNDING_SECTION_PREFIXES):
                return True
        return False

    def _forget_stale_sensory_items(self):
        """2026-07-09 bloat fix: real uploaded pictures/sounds/videos had
        NO forgetting at all -- every item stayed in memory (and, for
        pictures/videos, on real EFS disk) forever, regardless of whether
        she'd attended it in months. Reuses Section.MODE_FORGET_TICKS
        (already derived from LivingAtlas's own real decay constants:
        ln(0.02)/-0.0001 ticks) as the same "how long unattended before
        forgotten" window a word mode uses -- a picture she hasn't
        attended in that long is exactly as forgotten as a word would be.
        Deliberately NOT a count-based cap (unlike window_manager's
        MAX_CLOSED_WINDOWS, pure bookkeeping with no meaning of its own)
        -- this is real content, so it decays on the same real attention-
        recency physics as anything else she remembers, per Joe's ruling
        2026-07-09 ("decay and forgetting properly utilized where it
        makes sense"), not an arbitrary ceiling.

        Grace period: a just-created, never-yet-attended item is judged
        from its OWN creation tick (shown_at_tick for pictures/videos,
        created_tick for sounds -- added alongside this fix since sounds
        never tracked one before), not tick 0 -- else everything freshly
        added would look infinitely stale before the attention loop ever
        reaches it. Missing created_tick on pre-existing sound records
        (saved before this fix) defaults to "now," not 0 -- an unknown
        creation time must never look ancient by default; that would mass-
        forget a whole category of real content the first time this runs.

        Best-effort file cleanup for pictures/videos (their real EFS
        artifacts) -- swallows errors, never crashes the substrate, same
        convention as S3Consumer._delete_object."""
        threshold = Section.MODE_FORGET_TICKS
        forgotten = {"pictures": 0, "sounds": 0, "videos": 0}

        for pid in list(self._pictures.keys()):
            pic = self._pictures[pid]
            last_active = max(pic.last_attended_tick, pic.shown_at_tick)
            if self.tick - last_active <= threshold:
                continue
            orig_path = getattr(pic, "original_path", None)
            if orig_path:
                try:
                    if os.path.exists(orig_path):
                        os.remove(orig_path)
                except Exception:
                    pass
            del self._pictures[pid]
            forgotten["pictures"] += 1

        for sid in list(self._sounds.keys()):
            snd = self._sounds[sid]
            last_active = max(snd.get("last_attended_tick", 0),
                              snd.get("created_tick", self.tick))
            if self.tick - last_active > threshold:
                del self._sounds[sid]
                forgotten["sounds"] += 1

        for vid in list(self._videos.keys()):
            vitem = self._videos[vid]
            last_active = max(vitem.last_attended_tick, vitem.shown_at_tick)
            if self.tick - last_active <= threshold:
                continue
            frame_dir = getattr(vitem, "frame_dir", None)
            if frame_dir:
                try:
                    import shutil
                    if os.path.isdir(frame_dir):
                        shutil.rmtree(frame_dir, ignore_errors=True)
                except Exception:
                    pass
            del self._videos[vid]
            forgotten["videos"] += 1

        if any(forgotten.values()):
            self._log_substrate_event("sensory_items_forgotten", **forgotten)
        return forgotten

    # ------------------------------------------------------------------
    # Read one word: fire all krimelacks, compute DSF, route to sections
    # ------------------------------------------------------------------
    @_engine_mutation_entry
    def read_word(self, word, position_hint=None, source="corpus", bundle_id=None,
                  salience=None, episode_ref=None, presence=None,
                  location=None, sky_state=None, binding_window=None,
                  place=None, ambient=None, prev_phase_vec=_PHASE_VEC_UNSET):
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
        GL-FIX-LOCK-GRANULARITY-C1-20260710: prev_phase_vec kwarg — the
        previous word's phase vector for 60-L rotation/negation, call-local
        from read_sentence()'s own loop variable (never touches the shared
        self._prev_phase_vec instance attribute when supplied, even when the
        supplied value is None — a sentence's first word legitimately has no
        predecessor). Omitting the kwarg entirely (the _PHASE_VEC_UNSET
        default) preserves the OLD behavior exactly for direct callers that
        don't thread it: read from and write back to self._prev_phase_vec.
        Returns this word's own computed phase vector (or None) as the 4th
        element of the return tuple so a caller chaining calls (read_sentence)
        can feed it back in as next word's prev_phase_vec without ever
        reading engine instance state. The 5th element is this call's own
        profiling dict (previously read back afterward via the instance
        attribute self._read_word_last_profile — see that attribute's
        assignment below for why a caller now reads it from here instead).
        Full return shape: (lang_chi, role, senses, phase_vec, profile).
        """
        with self.lock:
            # GL-DIAG-READ-WORD-TIMING (Joe, 2026-07-06): instrumentation
            # only, no behavior change -- read_ms has measured 5-24s live
            # tonight with no proven internal breakdown; every prior fix
            # was guesswork until real diagnostic data settled it, so this
            # gets the same treatment instead of another guess. Overwritten
            # (not accumulated) each call; read_sentence sums these across
            # its whole word loop and logs one aggregate event per turn.
            _prof_t0 = time.monotonic()
            _prof = {}
            def _prof_mark(_key, _t_prev):
                _t_now = time.monotonic()
                _prof[_key] = _prof.get(_key, 0.0) + (_t_now - _t_prev) * 1000.0
                return _t_now
            self.tick += 1
            self.vocab.add(word)
            # §1.1: use sentence-local binding_window when supplied
            _bw = binding_window if binding_window is not None else self._current_binding_window
            _bw.append(f"w:{word}")

            lang_fp, role, senses = self.language.transduce(word)
            sense_fps = self.senses.fire_for_word(senses)
            _prof_t0 = _prof_mark("transduce", _prof_t0)

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
            _prof_t0 = _prof_mark("organism_enqueue", _prof_t0)

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
            _prof_t0 = _prof_mark("phase_dsf", _prof_t0)

            # v6: compute salience (or use caller-supplied override for backfill writes)
            if salience is None:
                salience = self._compute_salience(source=source,
                                                  input_novelty=atlas_sim)

            primary_sections = self._choose_role_sections(role, position_hint)
            _prof_t0 = _prof_mark("salience_role", _prof_t0)

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
            _prof_t0 = _prof_mark("recognition", _prof_t0)

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
            # GL-FIX-LOCK-GRANULARITY-C1-20260710: prev_phase_vec is call-local
            # when the caller (read_sentence) supplies it explicitly -- only
            # falls back to the shared self._prev_phase_vec instance attribute
            # for legacy direct callers that omit the kwarg entirely (see
            # _PHASE_VEC_UNSET / docstring above). This is what lets
            # read_sentence's per-word loop run without holding self.lock for
            # the whole sentence: two concurrent sentences each carry their
            # own local "previous word" state instead of racing on one
            # shared instance attribute.
            _prev_phase_vec_unset = prev_phase_vec is _PHASE_VEC_UNSET
            _effective_prev_phase_vec = self._prev_phase_vec if _prev_phase_vec_unset else prev_phase_vec
            _rotation = 0.0
            if _phase_vec is not None and _effective_prev_phase_vec is not None:
                try:
                    import numpy as _np_rot
                    _inner = _np_rot.vdot(_effective_prev_phase_vec, _phase_vec)
                    _rotation = float(abs(_np_rot.angle(_inner)))
                except Exception:
                    _rotation = 0.0
            self._last_rotation = _rotation
            # Update prev for next word. Legacy direct-caller path (kwarg
            # omitted) still mutates the shared instance attribute exactly as
            # before (reset at sentence start by read_sentence in the old
            # code -- read_sentence no longer does this at all now, see
            # below). Call-scoped path (read_sentence) leaves self._prev_
            # phase_vec untouched entirely; the caller threads the new value
            # through via this function's return value instead.
            if _prev_phase_vec_unset and _phase_vec is not None:
                self._prev_phase_vec = _phase_vec
            # Polarity from rotation: strong rotation (> π/2) → negation context
            _polarity = -1 if _rotation > (math.pi / 2) else 1

            # GL-FIX-LOCK-GRANULARITY-C1-20260710: resolve episode_ref once,
            # locally, instead of letting _grounding_kwargs() read the shared
            # self._current_episode instance attribute (formerly mutated by
            # read_sentence around its whole per-word loop -- see that
            # function's own comment). Direct callers that don't pass
            # episode_ref still fall back to self._current_episode exactly as
            # before; read_sentence now always supplies its own call-local
            # value explicitly, so this fallback is effectively dormant for
            # the sentence path (by design -- self._current_episode is no
            # longer written by anything).
            _effective_episode_ref = (episode_ref if episode_ref is not None
                                       else (self._current_episode[0] if self._current_episode else None))

            # GL-CLARITY-INVARIANCE-UNCAGE: affect + grounding kwargs for record() calls
            # §1.1: pass sentence-local binding_window to _grounding_kwargs
            _akw = {**self._affect_kwargs(surprise),
                    **self._grounding_kwargs(binding_window=_bw, episode_ref=_effective_episode_ref)}
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
            # GL-CMD-EPISODE-BINDING: situational context -- episode_ref is
            # already resolved into _akw via _grounding_kwargs() above (GL-FIX-
            # LOCK-GRANULARITY-C1-20260710); this block no longer needs to
            # re-override it (removed 2026-07-10, was dead-equivalent logic
            # duplicating the same precedence _effective_episode_ref already
            # applies).
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
            # 2026-07-09 credo fix: real/deliberate sensory co-occurrence
            # in the currently-open binding window, threaded down to
            # Section.receive's commit record (see _rebuild_word_to_
            # emission_index and REQUIRE_GROUNDED_SPEECH for how this
            # gates what she's allowed to speak).
            _akw["real_grounding"] = self._current_window_has_real_grounding()

            fam_listen = self.atlas.match_score(lang_chi, "listen")
            _listen_committed, _listen_mode_idx, _ = self.sections["listen"].receive(
                lang_dsf, lang_chi, word,
                self.atlas, fam_listen,
                salience=salience,
                dwell_ticks=dwell,
                engine_tick=self.tick,
                atlas_kwargs=_akw,
                window_manager=None)
            # GL-CMD-RECALL-REACH-159 Part C (F-3): Section.receive commits via
            # atlas.record() directly, not self._atlas_record() (Section has no
            # engine reference) — so the -57 reverse index has to be updated
            # here explicitly, at every receive() callsite, restoring -57
            # §1.2's "all atlas.record callsites index" invariant.
            if _listen_committed:
                self._index_word_at_chi("listen", _listen_mode_idx, lang_chi)
            _prof_t0 = _prof_mark("listen_receive", _prof_t0)

            for primary_section in primary_sections:
                fam = self.atlas.match_score(lang_chi, primary_section)
                n_modes_before = len(self.sections[primary_section].modes)
                _committed, _mode_idx, _ = self.sections[primary_section].receive(
                    lang_dsf, lang_chi, word,
                    self.atlas, fam,
                    salience=salience,
                    dwell_ticks=dwell,
                    engine_tick=self.tick,
                    atlas_kwargs=_akw,
                    window_manager=None)
                if _committed:
                    self._index_word_at_chi(primary_section, _mode_idx, lang_chi)
                # Incremental update of word→emission-section index
                # 2026-07-09 credo fix: only add a brand-new word to the
                # speakable index immediately if THIS first occurrence was
                # itself really grounded (_akw["real_grounding"], same value
                # already computed above for this word event). A word whose
                # first occurrence isn't grounded but is later re-taught in
                # a genuinely grounded moment still becomes speakable --
                # just at the next _rebuild_word_to_emission_index() full
                # scan (boot/restore), not instantly here, since reinforcement
                # of an existing mode doesn't change len(modes) and so never
                # reaches this incremental branch at all.
                if (primary_section in self._EMISSION_SECTIONS
                        and len(self.sections[primary_section].modes) > n_modes_before
                        and (not _require_grounded_speech() or _akw.get("real_grounding"))):
                    wl = word.lower()
                    mi = len(self.sections[primary_section].modes) - 1
                    if wl not in self._word_to_emission_sections:
                        self._word_to_emission_sections[wl] = []
                    self._word_to_emission_sections[wl].append(
                        (primary_section, mi, word))
            _prof_t0 = _prof_mark("primary_sections_receive", _prof_t0)

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
                    engine_tick=self.tick,
                    atlas_kwargs=_akw,
                    window_manager=None)
                if _ground_committed:
                    self._index_word_at_chi("ground", _ground_mode_idx, ground_chi)

                for m in self.senses.MODALITIES:
                    if sense_fps[m] is not None:
                        modal_chi = self.senses.krimelacks[m].winding
                        sec_name = f"modal_{m}"
                        # Legacy SENSORY_DNA compatibility record.  It is not
                        # an observed or emulated experience and therefore
                        # must never enter canonical BindingWindow memory.
                        self._atlas_record(
                            sec_name, deterministic_motif_id(word),
                            modal_chi, tick=self.tick,
                            source=source,
                            salience=salience,
                            **self._affect_kwargs(surprise),
                            # GL-FIX-LOCK-GRANULARITY-C1-20260710: this call
                            # site used to call _grounding_kwargs() bare,
                            # relying on it to read self._current_episode
                            # directly -- now that read_sentence no longer
                            # writes that attribute, the resolved call-local
                            # value has to be threaded through explicitly
                            # here too, same as the _akw build above, or
                            # modal window entries would silently lose their
                            # episode tag in the common (no-contention) case.
                            **self._grounding_kwargs(episode_ref=_effective_episode_ref))
            _prof_t0 = _prof_mark("ground_modal", _prof_t0)

            # GL-BUG-SELFHEAR-INTRO-RATCHET (found live 2026-07-06): this commit
            # used to fire unconditionally on familiarity alone, with no check
            # of position_hint or source. A single-word reply is always heard
            # back via _self_hear as position_hint="standalone", which never
            # routes to subject/verb/object (_choose_role_sections only sends
            # "standalone" to listen) -- but this intro commit fired anyway,
            # stamping a brand-new tick on "intro" for that exact word every
            # single time she heard herself say it. Since _word_to_emission_
            # sections' recency ordering (see _rebuild_word_to_emission_index)
            # picks candidates' section by whichever commit is most recent,
            # a word that ever became a one-word reply would have its "intro"
            # entry perpetually refreshed by self-hearing while its real
            # subject/verb/object history (if any) stayed frozen at whatever
            # tick it last occurred in real multi-word input -- a self-
            # reinforcing ratchet that locks a word into "intro, forever"
            # the moment it's said once. Confirmed live: "chimney" carries a
            # real verb commit from tick 15049925, but intro shows that SAME
            # tick plus a second entry at 15255380 -- the exact tick she said
            # "chimney" as a lone reply. Gated on self._self_hearing so
            # hearing her own genuine multi-word speech still refreshes
            # intro normally (no bug there -- position_hint routes real
            # first/middle/last words to subject/verb/object too in that
            # case); only the standalone-echo case that could never balance
            # itself out is suppressed.
            if fam_listen > 0.3 and not self._self_hearing:
                intro_dsf = DSF(D_k=fam_listen, M_k=0, R_rev=0, U_star=1-fam_listen,
                                C_k=fam_listen, P_k=0.5, B_k=fam_listen, S_UF=fam_listen)
                _intro_committed, _intro_mode_idx, _ = self.sections["intro"].receive(
                    intro_dsf, lang_chi, word,
                    self.atlas, 0.0,
                    salience=salience,
                    dwell_ticks=dwell,
                    engine_tick=self.tick,
                    atlas_kwargs=_akw,
                    window_manager=None)
                if _intro_committed:
                    self._index_word_at_chi("intro", _intro_mode_idx, lang_chi)
            _prof_t0 = _prof_mark("intro_receive", _prof_t0)

            # v6: Decay heartbeat (GL-FIX-PAUSE-IDEMPOTENT: rate_scale=0 when paused
            # keeps last_tick current so unpause doesn't see a massive dt)
            _paused = os.environ.get("DECAY_PAUSED", "0") == "1"
            if self.tick % 10 == 0:
                self.atlas.decay(self.tick, rate_scale=0.0 if _paused else self.decay_modulation)
                if self.hemispheres:
                    from dsf_ai_service.substrate.hemisphere_cognition import decay_hemisphere_atlases
                    decay_hemisphere_atlases(self, self.tick, rate_scale=0.0 if _paused else self.decay_modulation)
            if not _paused and self.tick % 200 == 0:
                self.atlas.forget_below_threshold()
                if self.hemispheres:
                    from dsf_ai_service.substrate.hemisphere_cognition import forget_hemisphere_atlases
                    forget_hemisphere_atlases(self)
                for _sec in self.sections.values():
                    _sec.forget_stale_modes(self.tick)
                self._forget_stale_sensory_items()

            # 8b. V5: Generate questions from gaps in this word's bindings
            # 9. Coordinator regulation pass (homeostasis + awareness)
            if self.tick % 5 == 0:
                self.coordinator.regulate(self, self.needs, self.atlas,
                                          self.sections, self.tick)
            _prof_mark("decay_coordinator", _prof_t0)
            self._read_word_last_profile = _prof

            # GL-FIX-LOCK-GRANULARITY-C1-20260710: _phase_vec appended so
            # read_sentence() can chain it into the NEXT word's prev_phase_vec
            # without ever touching self._prev_phase_vec (see docstring).
            # _prof appended too — read_sentence used to read this call's
            # profile back via self._read_word_last_profile immediately after
            # the call returned, which was only race-free because the outer
            # self.lock used to stay held for the whole sentence; now that
            # the lock releases between words, that instance-attribute
            # read-back could otherwise be clobbered by a different thread's
            # read_word() call in the gap, so it's threaded through the
            # return value instead. self._read_word_last_profile itself is
            # left in place unchanged for any other/future direct introspection.
            return lang_chi, role, list(senses.keys()), _phase_vec, _prof

    def _rebuild_word_to_emission_index(self):
        """Build the word→emission-section lookup from section commits.
        Called at boot after atlas+sections load, and incrementally
        by read_word when new modes land in emission sections.

        GL-BUG-INTRO-DOMINANCE (found live 2026-07-06): this used to walk
        self._EMISSION_SECTIONS in its FIXED tuple order ("subject", "verb",
        "object", "modifier", "ground", "intro") and append each section's
        modes in that order -- since "intro" is last in the tuple and
        commits there on almost any familiar word (fam_listen > 0.3), its
        entry landed last in every word's list regardless of when it
        actually happened. _brain_emission_candidates' locations[-1]
        ("most recent commit") then silently meant "intro, if it ever
        committed" instead of true recency -- collapsing every reply to a
        single intro-section word, every time, on every deploy (this
        rebuild runs at every boot/state-load). Fixed by ordering on each
        commit's real engine tick (Section.commits already records one)
        instead of iteration/append order.

        2026-07-09 credo fix: when _require_grounded_speech() is on, a word
        only enters this index (i.e. is allowed to be spoken at all -- see
        _brain_emission_candidates_legacy/_association_from_organism/
        _deep_atlas_neighbor_candidates, which all gate on membership here)
        if it has EVER had a real-grounded commit. Going forward that comes
        straight from Section.commits' own "grounded" field (set in
        read_word/Section.receive from _current_window_has_real_grounding).
        For vocabulary taught before this field existed, the only real
        signal available is deep_atlas's own co_occurrence record --
        _backfill_grounded_from_deep_atlas cross-references it once here."""
        entries = []
        grounded_words = set()
        for es in self._EMISSION_SECTIONS:
            es_sec = self.sections.get(es)
            if not es_sec:
                continue
            for c in es_sec.commits:
                w = c.get("word")
                if w:
                    entries.append((c.get("tick", 0), es, c.get("mode"), w))
                    if c.get("grounded"):
                        grounded_words.add(w.lower())
        if _require_grounded_speech():
            grounded_words |= self._backfill_grounded_from_deep_atlas()
        entries.sort(key=lambda e: e[0])
        idx = {}
        for _tick, es, mi, w in entries:
            wl = w.lower()
            if _require_grounded_speech() and wl not in grounded_words:
                continue
            if wl not in idx:
                idx[wl] = []
            idx[wl].append((es, mi, w))
        self._word_to_emission_sections = idx
        self._grounded_words = grounded_words

    def _backfill_grounded_from_deep_atlas(self):
        """2026-07-09 credo fix: retroactive grounding signal for vocabulary
        committed before Section.commits tracked "grounded" directly.
        deep_atlas's own co_occurrence invariant (_update_invariant in
        deep_atlas.py) already records, per promoted entry, every OTHER
        section that shared its chi neighborhood at promotion/reinforcement
        time -- real/deliberate sections (REAL_GROUNDING_EXACT_SECTIONS/
        _PREFIXES) showing up there means a real sensory moment genuinely
        touched that neighborhood, which is exactly what "grounded" means.
        Only entries in the 6 real speakable sections are considered (deep_
        atlas also holds the fake modal_* population itself, which this
        never treats as grounding evidence on its own). Honest empty if
        deep_atlas has nothing for a word -- no assumption either way.

        GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711 Part 1: the
        per-entry decision itself now lives in _entry_grants_grounding
        (shared with _backfill_eligibility_for_promotion's live per-word
        trigger, so there is exactly one definition of "grounded enough").
        This function's own iteration, ordering, and cost profile
        (O(all deep_atlas entries), called only from
        _rebuild_word_to_emission_index at boot/restore) are UNCHANGED."""
        grounded = set()
        for chi_k, des in self.deep_atlas.entries.items():
            for de in des:
                # GL-CMD-SLEEP-REORGANIZE follow-on (adversarial review,
                # 2026-07-10): a reorganize hypothesis's co_occurrence is a
                # speculative chi-proximity guess, not a real sensory
                # moment -- letting it satisfy the credo/grounding gate
                # would unlock a word for real speech on the strength of a
                # never-confirmed pairing, defeating the whole point of
                # this gate (2026-07-09 credo fix, same docstring above).
                if de.get("source_path") == "reorganize_hypothesis":
                    continue
                section = de.get("section")
                if section not in self._EMISSION_SECTIONS:
                    continue
                if not self._entry_grants_grounding(de):
                    continue
                sec_obj = self.sections.get(section)
                motif = de.get("motif")
                if sec_obj is None or motif is None or motif >= len(sec_obj.modes):
                    continue
                word_label = sec_obj.modes[motif][2]
                if word_label:
                    grounded.add(word_label.lower())
        return grounded

    def _entry_grants_grounding(self, de):
        """GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711 Part 1: single
        source of truth for whether one deep-atlas entry counts as real
        grounding evidence for the credo/emission-eligibility gate. Used by
        both _backfill_grounded_from_deep_atlas's full boot-time scan and
        _backfill_eligibility_for_promotion's live per-word trigger (fired
        right after DeepAtlas.dream_promotion_gate promotes an entry) --
        one definition, reused in both places, never a second parallel one.

        Two independent real signals, either sufficient on its own:
        1. has_real (2026-07-09 credo fix, unchanged): this entry's
           co_occurrence invariant shows its chi neighborhood genuinely
           touched a real camera/mic/touch/smell/taste section at some
           point.
        2. DEEP_ATLAS_ELIGIBILITY_BACKFILL_ENABLED (default OFF): this
           entry's OWN accumulated strength has reached DeepAtlas's
           existing Path-A survival bar (deep_atlas.ELIGIBILITY_STRENGTH_
           THETA -- literally SURVIVAL_THETA reused, not a new number).
           That is the same graduated "promoted enough" notion
           dream_promotion_gate already requires real, repeated survival
           across SURVIVAL_CONSECUTIVE dream cycles to reach -- reused
           here instead of a second, invented threshold. This is what
           lets a word taught ONLY through text (e.g. "ocean"), never
           once co-occurring with real sensory grounding, still earn real
           speakability purely through survived repetition -- exactly the
           comprehension/production dissociation the research behind this
           change describes. A word with zero real exposure never reaches
           this path at all: strength only exists on an entry because a
           real working-atlas commit (Section.receive, a real read_word
           event) put it there and a real dream cycle promoted it."""
        co = de.get("co_occurrence") or {}
        has_real = any(
            (s in REAL_GROUNDING_EXACT_SECTIONS or s.startswith(REAL_GROUNDING_SECTION_PREFIXES))
            for s in co if s not in FAKE_MODAL_SECTIONS
        )
        if has_real:
            return True
        if not _deep_atlas_eligibility_backfill_enabled():
            return False
        from dsf_ai_service.substrate.deep_atlas import ELIGIBILITY_STRENGTH_THETA
        return de.get("strength", 0.0) >= ELIGIBILITY_STRENGTH_THETA

    def _backfill_eligibility_for_promotion(self, chi_k, section, motif):
        """GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711 Part 1: real,
        already-rate-limited trigger -- called immediately after
        DeepAtlas.dream_promotion_gate actually promotes ONE entry (see
        _run_dream_cycle/_run_dream_cycle_phased, right after their
        `promoted` loop), never continuously and never a full
        _rebuild_word_to_emission_index() scan. Re-checks JUST this one
        word's eligibility using the exact same _entry_grants_grounding
        logic the boot-time backfill uses, and if it now qualifies, folds
        it into self._word_to_emission_sections/self._grounded_words
        directly via _grant_emission_eligibility_for_word.

        No-op (a couple of cheap dict/env-var checks) unless
        DEEP_ATLAS_ELIGIBILITY_BACKFILL_ENABLED=1 AND
        _require_grounded_speech() is on -- with the kill switch at its
        default OFF this function does nothing at all beyond the first
        env-var read, adding no meaningful cost to the real dream-cycle
        path (which already holds self.lock at both call sites)."""
        if not _deep_atlas_eligibility_backfill_enabled():
            return
        if not _require_grounded_speech():
            return
        if section not in self._EMISSION_SECTIONS:
            return
        sec_obj = self.sections.get(section)
        if sec_obj is None or motif is None or motif >= len(sec_obj.modes):
            return
        word = sec_obj.modes[motif][2]
        if not word:
            return
        wl = word.lower()
        if wl in self._word_to_emission_sections:
            return  # already eligible -- nothing to add, never re-derived/removed
        de = None
        for e in self.deep_atlas.entries.get(chi_k, []):
            if e.get("section") == section and e.get("motif") == motif:
                de = e
                break
        if de is None or de.get("source_path") == "reorganize_hypothesis":
            return
        if not self._entry_grants_grounding(de):
            return
        self._grant_emission_eligibility_for_word(word)

    def _grant_emission_eligibility_for_word(self, word):
        """GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711 Part 1: scoped,
        single-word version of _rebuild_word_to_emission_index's core loop
        -- collects every EXISTING real commit for this ONE word across the
        real emission sections (Section.commits, already-recorded history,
        nothing new fabricated) and installs them, without rescanning any
        other word's commits (that full scan remains
        _rebuild_word_to_emission_index's job alone, still boot/restore-
        only, cost profile unchanged). Additive only: the sole caller
        (_backfill_eligibility_for_promotion) already checked this word is
        not yet in self._word_to_emission_sections, so this only ever ADDS
        a new key, never overwrites or removes an existing one."""
        wl = word.lower()
        entries = []
        for es in self._EMISSION_SECTIONS:
            es_sec = self.sections.get(es)
            if not es_sec:
                continue
            for c in es_sec.commits:
                w = c.get("word")
                if w and w.lower() == wl:
                    entries.append((c.get("tick", 0), es, c.get("mode"), w))
        if not entries:
            return
        entries.sort(key=lambda e: e[0])
        self._word_to_emission_sections[wl] = [(es, mi, w) for _tick, es, mi, w in entries]
        self._grounded_words.add(wl)

    def _choose_role_sections(self, role_dna, position_hint):
        """Route word commit. Position wins for sentence boundaries (object,
        subject); DNA wins for middle. Modifiers ALSO route to object so the
        object section gets the structural diversity it needs.

        GL-BUG-GROUND-INTRO-UNREACHABLE (found live 2026-07-05): "ground"
        and "intro" added as DNA-driven secondary placements, same pattern
        as "modifier" -- ADDITIONAL to whatever position_hint already
        chose, never a replacement. Before this, no branch here could ever
        select either section: two of her seven sections were completely
        unreachable regardless of what she read."""
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
        elif role_dna == "ground":
            sections.append("ground")
        elif role_dna == "intro":
            sections.append("intro")
        elif role_dna in ("subject", "verb", "object"):
            if role_dna not in sections:
                sections.append(role_dna)
        return sections

    # ------------------------------------------------------------------
    # Read a sentence (sequence of words with position context + source)
    # ------------------------------------------------------------------
    @staticmethod
    def _canonical_context_values(value):
        """Preserve supplied scene values in deterministic first-seen order."""
        if value is None:
            return ()
        if isinstance(value, dict):
            values = [key for key, active in value.items() if active]
        elif isinstance(value, (list, tuple, set)):
            values = list(value)
        else:
            values = [value]
        return tuple(dict.fromkeys(
            str(item).strip().lower() for item in values
            if str(item).strip()))

    def _add_canonical_scene_entries(
            self, *, context_id, source, episode_ref, bundle_id,
            place, ambient, presence, experience_origin):
        """Bind only explicitly sourced story/context lanes in this window."""
        from dsf_ai_service.substrate.language_fact_strand import (
            construct_language_fact_strand,
        )

        lanes = (
            ("place", self._canonical_context_values(place)),
            ("ambient", self._canonical_context_values(ambient)),
            ("participant", self._canonical_context_values(presence)),
        )
        for modality, values in lanes:
            for value in values:
                fact = construct_language_fact_strand(value)
                self.window_manager.add_entry(
                    modality=modality,
                    section=f"story_{modality}",
                    motif_id=int(fact.structural_fingerprint[:16], 16),
                    chi=fact.topology.chi,
                    tick=self.tick,
                    source_tag=source,
                    context_id=context_id,
                    trigger_reason="story_context",
                    mirror_atlas=False,
                    structural_fact=fact.to_dict(),
                    detail={
                        "context_value": value,
                        "experience_origin": experience_origin,
                    },
                    source=source,
                    episode_ref=episode_ref,
                    bundle_id=bundle_id,
                )

    def _add_canonical_emulator_entries(
            self, words, *, context_id, source, episode_ref, bundle_id,
            experience_origin):
        """Bind exact descriptor waveforms and their complete DSF fields.

        Each descriptor is transduced independently.  Multiple descriptors
        are never averaged into a single proxy, because doing so would erase
        the distinctions this emulator exists to supply.
        """
        from dsf_ai_service.substrate.krimelack import Krimelack
        from dsf_ai_service.substrate.language_fact_strand import ExplicitDSF
        from dsf_ai_service.substrate.sensory_generators import (
            generate_sensory_signals,
        )

        mapping = self._sensory_word_map()
        descriptors = tuple(dict.fromkeys(
            word for word in words if word in mapping))
        organism_lanes = {}
        for descriptor in descriptors:
            modality = mapping[descriptor]
            signals = generate_sensory_signals(modality, [descriptor])
            lane = self._MODALITY_TO_ORGANISM_LANE.get(modality)
            if lane and signals:
                organism_lanes.setdefault(lane, []).extend(
                    np.asarray(waveform, dtype=float)
                    for waveform in signals.values())
            for channel, waveform in signals.items():
                samples = np.asarray(waveform, dtype=float)
                if samples.size < 2:
                    continue
                maximum = float(np.max(np.abs(samples)))
                if maximum < 1e-9:
                    continue
                transducer = Krimelack(
                    omega_0=2.0, kappa=60.0, dt=0.02,
                    integration_threshold=math.pi / 3)
                transducer.feed_signal(samples / maximum)
                sensory_dsf = ExplicitDSF.from_kernel(
                    compute_dsf(transducer.events))
                sensory_fact = {
                    "schema": "canonical_sensory_field_v1",
                    "descriptor": descriptor,
                    "channel": channel,
                    "waveform": [float(sample) for sample in samples],
                    "events": [dict(event) for event in transducer.events],
                    "dsf": sensory_dsf.to_dict(),
                    "winding": int(transducer.winding),
                    "chi": int(transducer.winding % 100),
                }
                self.window_manager.add_entry(
                    modality=modality,
                    section=f"emulator_{modality}",
                    motif_id=deterministic_motif_id(
                        f"{modality}:{descriptor}:{channel}"),
                    chi=sensory_fact["chi"],
                    tick=self.tick,
                    source_tag=source,
                    context_id=context_id,
                    trigger_reason="experience_emulator",
                    mirror_atlas=False,
                    structural_fact=sensory_fact,
                    sensory_refs=[f"{modality}:{descriptor}:{channel}"],
                    detail={
                        "descriptor": descriptor,
                        "channel": channel,
                        "experience_origin": experience_origin,
                    },
                    source=source,
                    episode_ref=episode_ref,
                    bundle_id=bundle_id,
                )
        return {
            lane: np.concatenate(waveforms)
            for lane, waveforms in organism_lanes.items()
            if waveforms
        }

    def _add_canonical_language_entry(
            self, word, language_position, *, context_id, source,
            episode_ref, bundle_id, experience_origin):
        """Add exactly one ordered full-field language fact for one token."""
        from dsf_ai_service.substrate.language_fact_strand import (
            construct_language_fact_strand,
        )

        fact = construct_language_fact_strand(word)
        self.window_manager.add_entry(
            modality="word",
            section="language_fact",
            motif_id=int(fact.structural_fingerprint[:16], 16),
            chi=fact.topology.chi,
            tick=self.tick,
            source_tag=source,
            context_id=context_id,
            trigger_reason="language_fact",
            language_position=language_position,
            mirror_atlas=False,
            structural_fact=fact.to_dict(),
            detail={
                "language_form": fact.language_form,
                "experience_origin": experience_origin,
            },
            source=source,
            episode_ref=episode_ref,
            bundle_id=bundle_id,
        )

    def _bind_certified_fact_emission_to_active_window(self, turn_result):
        """Complete the lived exchange with the words Guala actually emitted."""
        if (not isinstance(turn_result, ConversationTurnResult)
                or turn_result.response_source != "fact_strand_commit"
                or not turn_result.response):
            return 0
        words = _normalize_text(turn_result.response)
        if (not words
                or turn_result.committed_sections != tuple(
                    "language_fact" for _ in words)):
            raise ValueError(
                "certified Fact emission and committed words disagree")
        context_id = self.window_manager.active_context_id
        window = self.window_manager.current
        if context_id is None or window is None:
            raise RuntimeError(
                "certified Fact emission lacks an active experience window")
        detail = window.context_detail or {}
        origin = detail.get("experience_origin")
        if origin not in {"emulated", "observed"}:
            raise ValueError(
                "active emission experience lacks an approved origin")
        existing_positions = [
            entry.language_position for entry in window.entries
            if entry.modality == "word" and entry.language_position is not None
        ]
        first_position = max(existing_positions, default=-1) + 1
        for offset, word in enumerate(words):
            self._add_canonical_language_entry(
                word,
                first_position + offset,
                context_id=context_id,
                source="guala:self",
                episode_ref=detail.get("episode_ref"),
                bundle_id=detail.get("bundle_id"),
                experience_origin=origin,
            )
        return len(words)

    @staticmethod
    def _observed_sight_receipts_are_certified(window):
        """Require complete, content-bound native sight evidence."""
        from dsf_ai_service.visual_krimelack import (
            validate_visual_fragment_receipt,
        )

        sight_entries = [
            entry for entry in window.get("entries") or []
            if entry.get("modality") == "sight"
        ]
        if not sight_entries:
            return False
        has_native_events = False
        for entry in sight_entries:
            receipt = (entry.get("provenance") or {}).get(
                "structural_fact")
            if not validate_visual_fragment_receipt(receipt):
                return False
            if receipt["events"]:
                has_native_events = True
        return has_native_events

    def _remember_closed_language_window(self, window_id):
        """Commit closed-window language facts with exact lived citations."""
        from dsf_ai_service.substrate.language_fact_strand import (
            BindingWindowCitation,
            FactProvenance,
            LanguageFactStrand,
            construct_language_fact_strand,
        )
        from dsf_ai_service.substrate.language_fact_composer import (
            OrderedBindingWindow,
            WindowTokenOccurrence,
        )

        window = self.window_manager.closed_window(window_id)
        if window is None:
            raise RuntimeError(f"closed BindingWindow {window_id!r} is absent")
        if window.get("close_reason") not in {
                "context_complete", "give_experience_complete"}:
            raise ValueError(
                f"BindingWindow {window_id!r} is not a completed experience")
        origin = (window.get("context_detail") or {}).get("experience_origin")
        if origin not in {"emulated", "observed"}:
            raise ValueError(
                f"BindingWindow {window_id!r} lacks an approved experience origin")
        if (origin == "observed"
                and any(entry.get("modality") == "sight"
                        for entry in window.get("entries") or [])
                and not self._observed_sight_receipts_are_certified(window)):
            raise ValueError(
                f"BindingWindow {window_id!r} lacks certified native sight")
        modalities = tuple(dict.fromkeys(
            str(entry["modality"]).strip().lower()
            for entry in window.get("entries") or []))
        citation = BindingWindowCitation(
            window_id=window_id,
            experience_origin=origin,
            modalities=modalities,
        )
        facts = []
        occurrences = []
        for entry in window.get("entries") or []:
            if entry.get("modality") != "word":
                continue
            stored = (entry.get("provenance") or {}).get("structural_fact")
            if not isinstance(stored, dict):
                raise ValueError(
                    f"language entry {entry.get('entry_index')} lacks a Fact Strand")
            provisional = LanguageFactStrand.from_dict(stored)
            fact = construct_language_fact_strand(
                provisional.language_form,
                provenance=FactProvenance(
                    source_tag=entry.get("source_tag") or "",
                    trace_id=f"{window_id}:{entry['entry_index']}",
                    windows=(citation,),
                ),
            )
            facts.append(fact)
            if citation.is_multimodal_language_experience:
                occurrences.append(WindowTokenOccurrence(
                    fact=fact,
                    window_id=window_id,
                    entry_index=int(entry["entry_index"]),
                ))
        with self._language_fact_lock:
            remembered = sum(
                int(self.language_fact_memory.remember(fact))
                for fact in facts
                if fact.has_structural_evidence)
            if occurrences:
                self._ordered_language_windows[window_id] = OrderedBindingWindow(
                    window_id=window_id,
                    experience_origin=origin,
                    tokens=tuple(occurrences),
                )
                # New ordered window: the cached composer's precomputed
                # successor maps are stale — rebuild lazily on next compose.
                # (Memory-only growth needs no invalidation: the composer
                # holds a live reference and recalls through it.)
                self._language_fact_composer = None
        return remembered

    def _rebuild_language_fact_memory_from_windows(self):
        """Rebuild the derivative recognition index from durable windows.

        GL-SPC-SUBSTRATE-TRUE Change 1 (boot step 4, 'derived indexes'):
        qualification runs over the boot scan's small per-window METADATA
        (close reason, experience origin, modality summary) -- window
        CONTENT is fetched on demand, and only for the windows that
        qualify.  A non-qualifying window (the overwhelming majority:
        audio episodes, sight-only windows, boundary closes) is never
        materialized at all."""
        from dsf_ai_service.substrate.language_fact_strand import LanguageFactMemory

        with self._language_fact_lock:
            self.language_fact_memory = LanguageFactMemory()
            self._ordered_language_windows = {}
            self._language_fact_composer = None  # memory object replaced
        remembered = 0
        for window_id in sorted(self.window_manager.window_ids()):
            meta = self.window_manager.window_metadata(window_id)
            if meta is None:
                continue
            if meta.get("content_released"):
                # Distilled (gist-only) window: its language facts were
                # extracted at close; verbatim entries no longer exist to
                # re-cite (Change-3 forgetting lane).
                continue
            if meta.get("close_reason") not in {
                    "context_complete", "give_experience_complete"}:
                continue
            if meta.get("experience_origin") not in {"emulated", "observed"}:
                continue
            if "word" not in (meta.get("modalities") or ()):
                continue
            remembered += self._remember_closed_language_window(window_id)
        return remembered

    def _compose_language_fact_settlement(self, words):
        """Compose only from the atomically published Fact/window state."""
        from dsf_ai_service.substrate.language_fact_composer import (
            DeterministicWindowComposer,
        )
        from dsf_ai_service.substrate.language_fact_strand import (
            construct_language_fact_strand,
        )

        try:
            queries = tuple(
                construct_language_fact_strand(word) for word in words)
        except (TypeError, ValueError):
            return EmissionSettlement(tick=self.tick)

        with self._language_fact_lock:
            # Cached certified composer (GL-SPC-SUBSTRATE-TRUE Change 1, P1):
            # construction precomputes successor maps over EVERY ordered
            # window, so per-turn reconstruction scaled with the whole lived
            # language corpus. Build once, reuse until a new ordered window
            # arrives (invalidation in _remember_closed_language_window /
            # _rebuild_language_fact_memory_from_windows).
            # Change-4 merge note (2026-07-16): this cache SUBSUMES the
            # autonomous path's former per-cycle composer snapshot — the
            # seed attempts now reuse this cached instance across attempts
            # AND cycles; the AUTONOMOUS_COMPOSE_BUDGET_MS bound still
            # guards the cache-invalidated (rebuild) case.
            composer = self._language_fact_composer
            if composer is None:
                composer = DeterministicWindowComposer(
                    self.language_fact_memory,
                    tuple(
                        self._ordered_language_windows[window_id]
                        for window_id in sorted(self._ordered_language_windows)),
                )
                self._language_fact_composer = composer
            continuation = composer.continue_from_sequence(queries)
            memory_strand_count = len(getattr(
                self.language_fact_memory, "_by_id", ()) or ())
            ordered_window_count = len(self._ordered_language_windows)

        # The composer's stop_reason was computed and discarded for three
        # weeks while the symptom went undiagnosable (war-room synthesis
        # 2026-07-16).  One event per compose makes the certified path's
        # growth measurable — the instrument for it to ever become primary.
        try:
            self._log_substrate_event(
                "fact_compose",
                stop_reason=(continuation.stop_reason.value
                             if continuation.stop_reason else None),
                recall_reason=(continuation.recall_reason.value
                               if continuation.recall_reason else None),
                n_queries=len(queries),
                n_emitted=len(continuation.emitted_tokens),
                memory_strands=memory_strand_count,
                ordered_windows=ordered_window_count,
            )
        except Exception:
            pass

        provenance = []
        for token in continuation.emitted_tokens:
            supports = tuple(
                FactEmissionSupport(
                    window_id=item.window_id,
                    entry_index=item.entry_index,
                    experience_origin=item.experience_origin,
                    source_tag=item.source_tag,
                    trace_id=item.trace_id,
                    source_strand_id=item.source_strand_id,
                    modalities=item.modalities,
                )
                for item in token.entry_provenance)
            provenance.append(FactEmissionTokenProvenance(
                word=token.language_form,
                structural_fingerprint=token.structural_fingerprint,
                recognized_strand_ids=tuple(
                    strand.strand_id for strand in token.recognized_strands),
                supports=supports,
            ))
        if not provenance:
            return EmissionSettlement(tick=self.tick)
        return EmissionSettlement(
            content=" ".join(item.word for item in provenance),
            committed_sections=tuple("language_fact" for _ in provenance),
            n_commits=len(provenance),
            organ_in_commits=False,
            tick=self.tick,
            commit_provenance=tuple(provenance),
        )

    def _fact_settlement_has_certified_provenance(self, settlement):
        """Recheck every full-field lock and exact window entry before speech."""
        from dsf_ai_service.substrate.language_fact_strand import (
            BindingWindowCitation,
            FactProvenance,
            LanguageFactStrand,
            construct_language_fact_strand,
        )

        if not isinstance(settlement, EmissionSettlement):
            return False
        provenance = settlement.commit_provenance
        if (settlement.n_commits <= 0
                or settlement.n_commits != len(provenance)
                or settlement.committed_sections != tuple(
                    "language_fact" for _ in provenance)
                or settlement.organ_in_commits):
            return False
        verified_words = []
        with self._language_fact_lock:
            for item in provenance:
                if (not isinstance(item, FactEmissionTokenProvenance)
                        or not item.word
                        or not item.supports):
                    return False
                try:
                    query = construct_language_fact_strand(item.word)
                except (TypeError, ValueError):
                    return False
                recall = self.language_fact_memory.recall(query)
                if not recall.recognized:
                    return False
                recalled_classes = {
                    strand.structural_fingerprint
                    for strand in recall.matched_strands}
                recalled_ids = {
                    strand.strand_id for strand in recall.matched_strands}
                if (recalled_classes != {item.structural_fingerprint}
                        or not item.recognized_strand_ids
                        or not set(item.recognized_strand_ids).issubset(
                            recalled_ids)):
                    return False

                for support in item.supports:
                    if not isinstance(support, FactEmissionSupport):
                        return False
                    window = self.window_manager.closed_window(
                        support.window_id)
                    if (window is None
                            or window.get("close_reason") not in {
                                "context_complete", "give_experience_complete"}):
                        return False
                    origin = (window.get("context_detail") or {}).get(
                        "experience_origin")
                    if (origin == "observed"
                            and any(entry.get("modality") == "sight"
                                    for entry in window.get("entries") or [])
                            and not self._observed_sight_receipts_are_certified(
                                window)):
                        return False
                    modalities = tuple(dict.fromkeys(
                        str(entry["modality"]).strip().lower()
                        for entry in window.get("entries") or []))
                    if (origin != support.experience_origin
                            or modalities != support.modalities):
                        return False
                    entries = window.get("entries") or []
                    if (support.entry_index < 0
                            or support.entry_index >= len(entries)):
                        return False
                    entry = entries[support.entry_index]
                    if (entry.get("entry_index") != support.entry_index
                            or entry.get("modality") != "word"
                            or entry.get("source_tag", "") != support.source_tag
                            or support.trace_id != (
                                f"{support.window_id}:{support.entry_index}")):
                        return False
                    stored = (entry.get("provenance") or {}).get(
                        "structural_fact")
                    if not isinstance(stored, dict):
                        return False
                    try:
                        provisional = LanguageFactStrand.from_dict(stored)
                        citation = BindingWindowCitation(
                            window_id=support.window_id,
                            experience_origin=origin,
                            modalities=modalities,
                        )
                        if not citation.is_multimodal_language_experience:
                            return False
                        reconstructed = construct_language_fact_strand(
                            provisional.language_form,
                            provenance=FactProvenance(
                                source_tag=support.source_tag,
                                trace_id=support.trace_id,
                                windows=(citation,),
                            ),
                        )
                    except (TypeError, ValueError):
                        return False
                    if (provisional.language_form != item.word
                            or reconstructed.structural_fingerprint
                            != item.structural_fingerprint
                            or reconstructed.strand_id
                            != support.source_strand_id
                            or support.source_strand_id not in recalled_ids):
                        return False
                verified_words.append(item.word)
        return settlement.content == " ".join(verified_words)

    @_engine_mutation_entry
    def read_sentence(self, text, source="corpus", bundle_id=None, salience=None,
                      episode_ref=None, presence=None, location=None, sky_state=None,
                      place=None, ambient=None, experience_origin="emulated"):
        """Read a sentence into the substrate.

        GL-CMD-CURRICULUM-LOCK-RELEASE-V2-46v2 §1.1:
        binding_window lifted to sentence-local [] — prevents unbounded growth
        of self._current_binding_window that caused -46's crash.

        GL-FIX-LOCK-GRANULARITY-C1-20260710: the per-word loop below no
        longer holds self.lock for the whole sentence. It USED to (see prior
        revisions of this docstring: "Outer lock RETAINED, §1.3 phasing
        deferred") because self.lock is also contended by camera/mic frame
        handling and periodic autosave — holding it across every word of a
        sentence (each read_word() call doing real, non-trivial work: organism
        recall, tapestry settle physics, section commits) measured as real
        12-48s live stalls, with a single user turn once spending ~20 of its
        ~50+ total seconds just waiting on this lock for free. read_word()
        itself already wraps its own body in `with self.lock:` — the fix is
        this function no longer ALSO wraps the loop, so the lock is acquired
        and released once per word instead of once per sentence.
        This only became safe to do once two pieces of state this function
        used to mutate on `self` — self._current_episode and
        self._prev_phase_vec — stopped being shared mutable instance
        attributes read/written by every word of every concurrent sentence
        (see read_word's episode_ref/prev_phase_vec params and its own
        docstring). Both are now call-local variables here instead, threaded
        explicitly into (and, for the phase vector, back out of) each
        read_word() call — two concurrent sentences from different sources
        can no longer corrupt each other's episode tag or rotation/negation
        signal by interleaving between words.
        The brief preamble above the loop (pair-bond bookkeeping, modal
        signal caching, episode id derivation) and the brief epilogue below
        it (profile-timing log, last-place/ambient bookkeeping) are each
        still individually locked — they run ONCE per sentence (not once per
        word) and were never the source of the measured stalls, so keeping
        them atomic costs nothing and preserves their existing consistency
        guarantees unchanged. Per dispatch: no broader lock split (e.g.
        separate locks for camera/mic/autosave) is in scope here — self.tick,
        self.atlas.entries, self.sections[*].modes, and self.window_manager
        are one shared object graph that would need its own locking design
        first.

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
        if experience_origin not in {"emulated", "observed"}:
            raise ValueError(
                "experience_origin must be exactly 'emulated' or 'observed'")
        _existing_context_id = self.window_manager.active_context_id
        if _existing_context_id is not None:
            _existing_window = self.window_manager.current
            _existing_origin = (
                (_existing_window.context_detail or {}).get("experience_origin")
                if _existing_window is not None else None)
            if _existing_origin not in {"emulated", "observed"}:
                raise ValueError(
                    f"outer BindingWindow {_existing_context_id!r} lacks an "
                    "approved experience_origin")
            experience_origin = _existing_origin
        with self.lock:
            words = _normalize_text(text)
            if not words:
                return
            if place is None and ambient is None:
                place, ambient = scene_tags_from_words(words)
            # 60-M: connection weight earned from relationship, not configured
            # 0.15 was Joe's peak; sources earn up to it via pair_bond_strength
            weight = self.coordinator.pair_bond_strength(source, self.tick) * 0.15
            self.recent_connection_boost = max(self.recent_connection_boost, weight)
            self.source_history[source] += 1
            source_turn_index = self.source_history[source]

            # v6-bridge: update last_input_tick for presence timeout
            if source in {"joe", "wc", "c1"}:
                self.coordinator.update_last_input(source, self.tick)
                # GL-FIX-VOICE-PRESENCE-20260712: contact IS presence, same
                # rule _open_response_window already applies for converse()
                # (GL-CMD-REST-RETIRE-ORIENT-73) -- extended here so intake
                # paths that call read_sentence() directly without going
                # through converse() (namely: the passive mic/Whisper
                # pipeline, GL-CMD-VOICE-TO-WORDS-153) also establish real
                # presence. This does NOT force a reply -- no
                # _check_emission_trigger call here -- it only unblocks the
                # existing need-driven scheduler/autonomous-emission loop to
                # organically consider reacting to what she just heard, the
                # same way she already can react to anything else she senses.
                # Joe's direction: she is not a chatbot gated on being
                # directly addressed.
                if not self.coordinator._presence.get(source, False):
                    self.coordinator.wake(source, self, self.needs, self.atlas)

            # 60-K: record interaction for continuous pair-bond strength
            _sal_estimate = self._compute_salience(source=source, input_novelty=0.5)
            self.coordinator._record_interaction(source, _sal_estimate, self.tick)

            # GL-CLARITY-INVARIANCE-UNCAGE: episode tracking per sentence.
            # GL-FIX-LOCK-GRANULARITY-C1-20260710: call-local now — NOT
            # written to self._current_episode (formerly shared instance
            # state, mutated here and read by every word's read_word() call;
            # see this function's own docstring for why that was unsafe once
            # the per-word loop stopped holding self.lock continuously).
            # A caller-supplied episode_ref (rare — no production caller
            # passes one today) still wins over the auto-generated id below,
            # same precedence as before.
            ep_id = f"episode:{source}:{source_turn_index}"
            _resolved_episode_ref = episode_ref if episode_ref is not None else ep_id
            _fact_context_id = (
                _existing_context_id
                or f"language:{source}:{source_turn_index}")
            _owns_fact_context = _existing_context_id is None
            # §1.1: binding_window is sentence-local — prevents unbounded growth
            binding_window = []
            # GL-DIAG-READ-WORD-TIMING: aggregate read_word's per-call profile
            # across this sentence's whole word loop -- see read_word's own
            # comment for why. Only logged for real conversational sources
            # (same gate converse_timing already uses) to avoid per-word
            # spam from autonomous curriculum/corpus reading.
            _read_profile_agg = {}
            # 60-L: previous word's phase vector, call-local now (was
            # self._prev_phase_vec, reset by this function at sentence start/
            # end — see read_word's prev_phase_vec param and docstring for
            # why sharing it on `self` was unsafe once the loop below stopped
            # holding self.lock for the whole sentence).
            _prev_phase_vec_local = None

        # The caller owns this exact sentence boundary.  A failed sentence is
        # still closed for audit, but is never committed to recognition.
        if _owns_fact_context:
            self.window_manager.begin_context(
                _fact_context_id,
                trigger_reason="language_experience",
                context_detail={
                    "experience_origin": experience_origin,
                    "source": source,
                    "episode_ref": _resolved_episode_ref,
                    "bundle_id": bundle_id,
                },
            )
        _sentence_complete = False
        try:
            self._add_canonical_scene_entries(
                context_id=_fact_context_id,
                source=source,
                episode_ref=_resolved_episode_ref,
                bundle_id=bundle_id,
                place=place,
                ambient=ambient,
                presence=presence,
                experience_origin=experience_origin,
            )
            _modal = self._add_canonical_emulator_entries(
                words,
                context_id=_fact_context_id,
                source=source,
                episode_ref=_resolved_episode_ref,
                bundle_id=bundle_id,
                experience_origin=experience_origin,
            )
            if _modal:
                with self.lock:
                    self._last_read_modal_signals = _modal
                    self._last_read_modal_wall_time = time.time()

            # GL-FIX-LOCK-GRANULARITY-C1-20260710: self.lock is released
            # between words.  The BindingWindow context is caller-local and
            # remains exact even when other sentences interleave.
            for i, word in enumerate(words):
                if len(words) == 1:
                    hint = "standalone"
                elif i == 0:
                    hint = "first"
                elif i == len(words) - 1:
                    hint = "last"
                else:
                    hint = "middle"
                _, _, _, _new_phase_vec, _wp = self.read_word(
                    word, position_hint=hint, source=source,
                    bundle_id=bundle_id, salience=salience,
                    episode_ref=_resolved_episode_ref, presence=presence,
                    location=location, sky_state=sky_state,
                    place=place, ambient=ambient,
                    binding_window=binding_window,
                    prev_phase_vec=_prev_phase_vec_local)
                self._add_canonical_language_entry(
                    word,
                    i,
                    context_id=_fact_context_id,
                    source=source,
                    episode_ref=_resolved_episode_ref,
                    bundle_id=bundle_id,
                    experience_origin=experience_origin,
                )
                if _new_phase_vec is not None:
                    _prev_phase_vec_local = _new_phase_vec
                if _wp:
                    for _k, _v in _wp.items():
                        _read_profile_agg[_k] = (
                            _read_profile_agg.get(_k, 0.0) + _v)
            _sentence_complete = True
        finally:
            _closed_window_id = None
            if _owns_fact_context:
                _closed_window_id = self.window_manager.end_context(
                    _fact_context_id,
                    "context_complete" if _sentence_complete else "context_failed")

        if _owns_fact_context:
            if _closed_window_id is None:
                raise RuntimeError(
                    f"language BindingWindow {_fact_context_id!r} did not close")
            self._remember_closed_language_window(_closed_window_id)

        with self.lock:
            if source in ("joe", "joe_voice", "wc", "c1", "gate_test") and _read_profile_agg:
                self._log_substrate_event("read_sentence_timing",
                                          n_words=len(words),
                                          **{k: round(v, 1) for k, v in _read_profile_agg.items()})
            # 60-N: read_count no longer incremented here; property derives from atlas
            self._negation_pending = 0    # kept for load compatibility
            # GL-CMD-SCENE-LANES-B1-188 V5: last-sentence scene, surfaced live
            # via introspect()/loomscan (mirrors _last_surprise's pattern).
            self._last_place_tags = place
            self._last_ambient_tags = ambient
        return source_turn_index

    # ------------------------------------------------------------------
    # Conversation: input -> substrate -> output via cascade
    # ------------------------------------------------------------------
    def _renew_presence(self, source):
        """GL-FIX-PRESENCE-KEEPALIVE-C1-20260710: renew this source's
        last-input tick right now. Single-shot -- see _presence_keepalive()
        for the real fix (a heartbeat spanning the whole call). Kept as a
        small standalone helper because _presence_keepalive's own first
        renewal, and a couple of natural checkpoints, use it directly."""
        if source in ("joe", "wc", "c1"):
            self.coordinator.update_last_input(source, self.tick)

    @contextlib.contextmanager
    def _presence_keepalive(self, source, interval_s=0.5):
        """GL-FIX-PRESENCE-KEEPALIVE-C1-20260710: keep `source`'s presence
        alive for the full wall-clock duration of the wrapped block, not
        just at its start.

        Root cause (GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1
        item #4): presence.timeout_check() compares a single GLOBAL
        engine.tick against a per-source _last_input_tick snapshot taken
        once, at the moment read_sentence started. engine.tick advances
        from every source combined (autonomous curriculum/worldfeed
        reading, sensory frame processing, other sessions' own turns —
        every read_word() call anywhere bumps it), not just this source's
        own words. Real turns now take 50+ seconds end-to-end, and:
          (a) a caller can sit blocked well before read_sentence ever
              runs, waiting on self.lock (confirmed live: frame calls
              holding it 12-48s, one case ~93s) — their presence isn't
              renewed at all during that wait under the pre-fix code;
          (b) _converse_phased's own Phase 6 (emission) deliberately
              releases self.lock (self._emission_lock is a separate lock)
              so curriculum/autonomy CAN interleave and advance the
              global tick while this source's own turn is still inside
              that phase; and
          (c) (found by real-threading adversarial testing, not just
              reasoning: a single slow phase -- e.g. emission alone under
              load -- can by itself exceed 1500 ticks of background
              advancement before that phase even returns, so renewing
              only at phase BOUNDARIES is provably insufficient; a real
              call-duration heartbeat is required.)
        Either way, 1500 ticks (PRESENCE_TIMEOUT_TICKS — validated
        elsewhere, NOT changed here) of unrelated background advancement
        can plausibly elapse during one still-in-flight exchange, so
        timeout_check() (invoked from ANY thread's read_word, every 5
        global ticks) auto-rests a source who never actually left.

        Mechanism: renews once immediately (synchronous, covers the
        instant this call began — including time spent waiting for
        self.lock before read_sentence even starts), then starts a
        lightweight daemon thread that renews every `interval_s` wall-
        clock seconds until the wrapped block exits (success or
        exception) — interval_s=0.5s gives ~2 renewals/sec, far more
        frequent than any realistic single phase could burn through 1500
        ticks of background load (measured background read_word rate on
        a cold engine: ~250 calls/s — even at that rate 0.5s is only
        ~125 ticks, 12x headroom under the threshold).

        Scoping / safety: no-ops entirely for sources that aren't
        presence-tracked ("corpus", "curriculum", "joe_voice", etc. — same
        gate read_sentence's original single renewal already used). Only
        ever touches `source`'s own _last_input_tick — never any other
        source's — so it cannot make another source's presence "stick".
        Does not touch PRESENCE_TIMEOUT_TICKS. update_last_input() is a
        single dict-key assignment on an already-existing key (no read-
        modify-write), so calling it from the heartbeat thread without
        self.lock introduces no new race — this is pure bookkeeping-
        timestamp plumbing, never memory/recall/decision content."""
        if source not in ("joe", "wc", "c1"):
            yield
            return
        self._renew_presence(source)
        stop_event = threading.Event()

        def _heartbeat():
            while not stop_event.wait(interval_s):
                try:
                    self._renew_presence(source)
                except Exception:
                    pass  # heartbeat must never break the real turn

        hb_thread = self._start_engine_background_thread(
            _heartbeat, daemon=True,
            name=f"presence-keepalive-{source}")
        try:
            yield
        finally:
            stop_event.set()
            hb_thread.join(timeout=interval_s + 2.0)

    @_engine_mutation_entry
    def converse(self, text, source="unknown", emission_mode=None, bundle_id=None,
                 episode_ref=None, presence=None, location=None, sky_state=None,
                 organ_candidates=None):
        """v5: Recall from substrate atlas BEFORE reading input.
        - If atlas has cross-section bindings near the input chi values, emit
          those (real recall from corpus accumulation).
        - If recall finds nothing, check question bucket for a related question.
        - If neither, return neutral silence.

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
        # GL-FIX-PRESENCE-KEEPALIVE-C1-20260710: keep this source's presence
        # alive for the FULL wall-clock duration of this call -- BEFORE any
        # lock wait, BEFORE the math-parse shortcut in either path below
        # (both of which could otherwise skip read_sentence's own renewal
        # entirely), and THROUGHOUT any single slow phase (a heartbeat
        # thread, not just phase-boundary renewals -- see
        # _presence_keepalive's docstring for why boundary-only renewal was
        # proven insufficient by real-threading adversarial testing).
        with self._live_converse_state_lock:
            self._live_converse_pending += 1
        try:
            with self._presence_keepalive(source):
                return self._converse_body(
                    text, source, emission_mode, bundle_id, episode_ref,
                    presence, location, sky_state, organ_candidates)
        finally:
            with self._live_converse_state_lock:
                if self._live_converse_pending <= 0:
                    raise RuntimeError("live converse counter underflow")
                self._live_converse_pending -= 1

    def _converse_body(self, text, source, emission_mode, bundle_id,
                       episode_ref, presence, location, sky_state,
                       organ_candidates):
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
        response_source = "silence_no_commit"
        committed_sections = ()
        # Math route — MathLoom BSIL adapter (with v5 fixed parser)
        parsed = self._parse_math(text)
        if parsed:
            op, a, b = parsed
            result = self._mathloom_solve(op, a, b)
            response = self._num_to_word(result)
            self._last_response_source = "mathloom"  # diagnostic only
            self._last_emission_id = None  # diagnostic only
            return ConversationTurnResult(response, "mathloom")

        with self.lock:
            _t_converse_start = time.monotonic()
            # 1. Tokenize input (GL-BRIEF-035: shared normalization)
            words = _normalize_text(text)
            if not words:
                self._last_response_source = "silence_empty_input"  # diagnostic only
                self._last_emission_id = None  # diagnostic only
                return ConversationTurnResult("", "silence_empty_input")

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
            recalled, recalled_pictures = self._recall_response(
                input_chis, input_word_chis, words)
            fact_settlement = self._compose_language_fact_settlement(words)
            _t_recall = time.monotonic()

            # 4. Read input into substrate (so she learns from this interaction)
            # Snapshot tick before read — only entries born in THIS read get tagged
            tick_before_read = self.tick
            source_turn_index = self.read_sentence(
                text, source=source, bundle_id=bundle_id,
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
            # 6. Fact-Strand composer preferred; when it has nothing to
            # release, the substrate's own assemblage voice settles the turn
            # (Joe's 2026-07-16 ruling — see _committed_emission_response).
            self._last_converse_source = source
            settlement = fact_settlement
            if getattr(fact_settlement, "n_commits", 0) <= 0:
                settlement = self._emit_from_invariants(
                    input_chis, words, mode_override=emission_mode,
                    v7_session=getattr(self, "_v7_session", None))
            _t_emit = time.monotonic()
            reply, response_source = self._committed_emission_response(
                settlement)
            if reply:
                committed_sections = settlement.committed_sections

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
            if reply:
                for ew in _normalize_text(reply):
                    ek = LanguageKrimelack()
                    ek.transduce(ew)
                    reply_chis.append(ek.winding)
                committed_chis = reply_chis
                first_chi = min(committed_chis) if committed_chis else 0
                n_committed = len(committed_chis)
                eid = (f"{source}:{source_turn_index}:"
                       f"{self.tick}_{first_chi}_{n_committed}")
                emission_id = eid
                rec = {"emission_id": eid, "text": reply, "tick": self.tick,
                       "input_text": text, "source": source,
                       "committed_chis": committed_chis,
                       "committed_sections": list(
                           settlement.committed_sections),
                       "n_commits": settlement.n_commits,
                       "response_source": response_source,
                       "commit_provenance": [
                           provenance.as_record()
                           for provenance in settlement.commit_provenance]}
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
                emission_id = None
                self._last_emission_record = None
            # Retained only for introspection/diagnostics. Interfaces consume
            # the immutable turn result below, never these shared fields.
            self._last_response_source = response_source
            self._last_emission_id = emission_id
            _t_reply_ready = time.monotonic()
            reply_emission_id = emission_id
            reply_response_source = response_source

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
                if reply and source in ("joe", "joe_voice", "wc", "c1"):
                    self._self_hear(
                        reply, source, reply_chis=reply_chis,
                        emission_id=reply_emission_id,
                        response_source=reply_response_source)
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

            self._start_engine_background_thread(
                _post_reply_continuation, daemon=True,
                name="converse-posthear")
            return ConversationTurnResult(
                response=reply,
                response_source=response_source,
                emission_id=emission_id,
                committed_sections=committed_sections,
                recalled_pictures=recalled_pictures,
                source_turn_index=source_turn_index,
                commit_provenance=settlement.commit_provenance)

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
        response_source = "silence_no_commit"
        committed_sections = ()

        # Phase 1: tokenize + chi transduction (no lock — pure local computation)
        parsed = self._parse_math(text)
        if parsed:
            op, a, b = parsed
            result = self._mathloom_solve(op, a, b)
            response = self._num_to_word(result)
            self._last_response_source = "mathloom"  # diagnostic only
            self._last_emission_id = None  # diagnostic only
            return ConversationTurnResult(response, "mathloom")

        words = _normalize_text(text)
        if not words:
            self._last_response_source = "silence_empty_input"  # diagnostic only
            self._last_emission_id = None  # diagnostic only
            return ConversationTurnResult("", "silence_empty_input")

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
        recalled, recalled_pictures = self._recall_response(
            input_chis, input_word_chis, words)
        fact_settlement = self._compose_language_fact_settlement(words)
        _t_recall = time.monotonic()

        # Phase 4: read input (per-word self.lock internally via -46v2 §1.1)
        tick_before_read = self.tick
        source_turn_index = self.read_sentence(
            text, source=source, bundle_id=bundle_id,
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
            self._last_converse_source = source
            settlement = fact_settlement
            if getattr(fact_settlement, "n_commits", 0) <= 0:
                # Fact-Strand had nothing to release — the substrate's own
                # assemblage voice settles the turn (Joe's 2026-07-16 ruling,
                # see _committed_emission_response).  _emission_lock is an
                # RLock; _emit_from_invariants re-acquires it safely inline.
                settlement = self._emit_from_invariants(
                    input_chis, words, mode_override=emission_mode,
                    v7_session=getattr(self, "_v7_session", None))
            reply, response_source = self._committed_emission_response(
                settlement)
            if reply:
                committed_sections = settlement.committed_sections
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
            if reply:
                for ew in _normalize_text(reply):
                    ek = LanguageKrimelack()
                    ek.transduce(ew)
                    reply_chis.append(ek.winding)
                committed_chis = reply_chis
                first_chi = min(committed_chis) if committed_chis else 0
                n_committed = len(committed_chis)
                eid = (f"{source}:{source_turn_index}:"
                       f"{self.tick}_{first_chi}_{n_committed}")
                emission_id = eid
                rec = {"emission_id": eid, "text": reply, "tick": self.tick,
                       "input_text": text, "source": source,
                       "committed_chis": committed_chis,
                       "committed_sections": list(
                           settlement.committed_sections),
                       "n_commits": settlement.n_commits,
                       "response_source": response_source,
                       "commit_provenance": [
                           provenance.as_record()
                           for provenance in settlement.commit_provenance]}
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
                emission_id = None
                self._last_emission_record = None
            # Diagnostic mirrors only; the immutable return value is the
            # interface authority for this exact turn.
            self._last_response_source = response_source
            self._last_emission_id = emission_id
        _t_reply_ready = time.monotonic()
        reply_emission_id = emission_id
        reply_response_source = response_source

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
            if reply and source in ("joe", "joe_voice", "wc", "c1"):
                self._self_hear(
                    reply, source, reply_chis=reply_chis,
                    emission_id=reply_emission_id,
                    response_source=reply_response_source)
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

        self._start_engine_background_thread(
            _post_reply_continuation, daemon=True,
            name="converse-posthear")
        return ConversationTurnResult(
            response=reply,
            response_source=response_source,
            emission_id=emission_id,
            committed_sections=committed_sections,
            recalled_pictures=recalled_pictures,
            source_turn_index=source_turn_index,
            commit_provenance=settlement.commit_provenance)

    def _ensure_engine_lifecycle_state(self):
        """Initialize lifecycle fields on narrow legacy/test constructions."""
        if hasattr(self, "_engine_mutation_condition"):
            return
        bootstrap_lock = self.__dict__.setdefault(
            "_engine_lifecycle_bootstrap_lock", threading.Lock())
        with bootstrap_lock:
            if hasattr(self, "_engine_mutation_condition"):
                return
            self._engine_quiesced = getattr(self, "_engine_quiesced", False)
            self._engine_quiescence_complete = False
            self._engine_mutation_condition = threading.Condition()
            self._engine_mutation_admission_open = True
            self._engine_active_mutations = 0
            self._engine_mutation_local = threading.local()
            self._engine_raw_threads = set()
            self._engine_raw_threads_started = 0
            self._engine_raw_threads_completed = 0

    @contextlib.contextmanager
    def _engine_mutation_scope(self, owner):
        """Atomically admit one engine mutation, including nested calls."""
        self._ensure_engine_lifecycle_state()
        depth = getattr(self._engine_mutation_local, "depth", 0)
        if depth:
            self._engine_mutation_local.depth = depth + 1
            try:
                yield
            finally:
                self._engine_mutation_local.depth = depth
            return

        with self._engine_mutation_condition:
            if not self._engine_mutation_admission_open:
                raise RuntimeError(
                    f"engine mutation rejected during quiescence: {owner}")
            self._engine_active_mutations += 1
        self._engine_mutation_local.depth = 1
        try:
            yield
        finally:
            self._engine_mutation_local.depth = 0
            with self._engine_mutation_condition:
                if self._engine_active_mutations <= 0:
                    raise RuntimeError("engine mutation counter underflow")
                self._engine_active_mutations -= 1
                self._engine_mutation_condition.notify_all()

    def _start_engine_background_thread(self, target, *, name, args=(),
                                        daemon=True):
        """Start and retain an accepted engine continuation.

        Registration and mutation counting happen before ``Thread.start``.
        A continuation spawned by an already-admitted mutation remains part of
        that accepted operation even if quiescence closes admission between the
        foreground return and the continuation's work.
        """
        self._ensure_engine_lifecycle_state()
        inherited = getattr(self._engine_mutation_local, "depth", 0) > 0

        def run_registered():
            self._engine_mutation_local.depth = 1
            try:
                target(*args)
            finally:
                self._engine_mutation_local.depth = 0
                with self._engine_mutation_condition:
                    self._engine_raw_threads_completed += 1
                    if self._engine_active_mutations <= 0:
                        raise RuntimeError("engine background counter underflow")
                    self._engine_active_mutations -= 1
                    self._engine_mutation_condition.notify_all()

        thread = threading.Thread(target=run_registered, daemon=daemon,
                                  name=name)
        with self._engine_mutation_condition:
            if not self._engine_mutation_admission_open and not inherited:
                raise RuntimeError(
                    f"engine background work rejected during quiescence: {name}")
            self._engine_raw_threads = {
                registered
                for registered in self._engine_raw_threads
                if registered.is_alive()
            }
            self._engine_active_mutations += 1
            self._engine_raw_threads_started += 1
            self._engine_raw_threads.add(thread)
            try:
                thread.start()
            except Exception:
                self._engine_raw_threads.discard(thread)
                self._engine_raw_threads_started -= 1
                self._engine_active_mutations -= 1
                self._engine_mutation_condition.notify_all()
                raise
        return thread

    def _close_engine_mutation_admission(self):
        self._ensure_engine_lifecycle_state()
        with self._engine_mutation_condition:
            self._engine_mutation_admission_open = False
            self._engine_mutation_condition.notify_all()

    def _wait_for_engine_mutations(self, deadline):
        with self._engine_mutation_condition:
            while self._engine_active_mutations:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError(
                        "engine quiescence timed out with "
                        f"{self._engine_active_mutations} mutation(s) active")
                self._engine_mutation_condition.wait(timeout=remaining)

    def _join_engine_raw_threads(self, deadline):
        with self._engine_mutation_condition:
            threads = tuple(self._engine_raw_threads)
        alive = []
        for thread in threads:
            if thread is threading.current_thread():
                alive.append(thread.name)
                continue
            thread.join(timeout=max(0.0, deadline - time.monotonic()))
            if thread.is_alive():
                alive.append(thread.name)
        if alive:
            raise RuntimeError(
                "engine quiescence timed out joining raw threads: "
                + ", ".join(sorted(alive)))
        with self._engine_mutation_condition:
            if (self._engine_raw_threads_completed
                    != self._engine_raw_threads_started):
                raise RuntimeError(
                    "engine raw-thread completion mismatch "
                    f"(started={self._engine_raw_threads_started}, "
                    f"completed={self._engine_raw_threads_completed})")
            self._engine_raw_threads.clear()
            return {
                "started": self._engine_raw_threads_started,
                "completed": self._engine_raw_threads_completed,
                "joined_at_quiescence": len(threads),
                "alive": [],
            }

    def settle_queues(self, budget_s=420.0, threshold=8):
        """Pre-seal settle: with the substrate asleep (manual_sleep is the
        intake hold), give the background workers their own generous budget
        to chew accumulated backlog BEFORE the strict quiescence window
        opens. 2026-07-16: two scripted seals 503'd on backlog drains
        (organism 721 unfinished, then tapestry 1708) that no strict 120s
        window can absorb once the substrate's life is rich enough to keep
        its queues fed -- the fix is a settle phase, not a bigger strict
        window. Settling is observational only: no admission close, no
        thread joins, so failure leaves the substrate exactly as alive as
        before. Raises RuntimeError with per-queue counts on budget expiry
        (the seal surfaces it as an honest 503)."""
        deadline = time.monotonic() + float(budget_s)
        queues = tuple(
            (name, q) for name, q in (
                ("organism", getattr(self, "_organism_queue", None)),
                ("organism_sensory", getattr(
                    self, "_organism_sensory_queue", None)),
                ("tapestry", getattr(self, "_tapestry_queue", None)),
                ("diary", getattr(self, "_diary_queue", None)),
            ) if q is not None)
        started = {name: q.unfinished_tasks for name, q in queues}
        while True:
            busy = {name: q.unfinished_tasks for name, q in queues
                    if q.unfinished_tasks > threshold}
            if not busy:
                remaining = {n: q.unfinished_tasks for n, q in queues}
                print(f"[GualaLoom][seal-settle] settled: started={started} "
                      f"remaining={remaining}", flush=True)
                return {"settled": True, "budget_s": float(budget_s),
                        "threshold": threshold, "started": started,
                        "remaining": remaining}
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "seal settle budget expired with backlog: "
                    + ", ".join(f"{n}={c}" for n, c in sorted(busy.items())))
            time.sleep(0.25)

    def quiesce_background_workers(self, timeout=120.0):
        """Stop, drain, and join every engine-owned mutation source.

        This is a lifecycle boundary, not a best-effort shutdown.  It either
        proves every engine thread/queue is quiet or raises with the exact
        owners still active; callers must not seal persistence after failure.
        """
        deadline = time.monotonic() + float(timeout)

        def remaining():
            return max(0.0, deadline - time.monotonic())

        self._engine_quiescence_complete = False
        self._close_engine_mutation_admission()
        self._reading_stop.set()
        self._daydream_running = False

        for thread_name in ("_reading_thread", "_daydream_thread"):
            thread = getattr(self, thread_name, None)
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout=remaining())
                if thread.is_alive():
                    raise RuntimeError(
                        f"quiescence timed out joining {thread.name}")

        self._wait_for_engine_mutations(deadline)
        with self._live_converse_state_lock:
            pending_turns = self._live_converse_pending
        if pending_turns:
            raise RuntimeError(
                f"engine mutation counter reached zero with {pending_turns} "
                "conversation(s) still active")
        raw_thread_certificate = self._join_engine_raw_threads(deadline)

        # No foreground operation, accepted continuation, or engine loop can
        # now produce another queue item. Freeze the lazy queues before
        # measuring and draining their accepted work.
        self._engine_quiesced = True

        queues = tuple(
            (name, queue)
            for name, queue in (
                ("organism", getattr(self, "_organism_queue", None)),
                ("organism_sensory", getattr(
                    self, "_organism_sensory_queue", None)),
                ("tapestry", getattr(self, "_tapestry_queue", None)),
                ("diary", getattr(self, "_diary_queue", None)),
            )
            if queue is not None)
        for name, queue in queues:
            while queue.unfinished_tasks:
                if remaining() <= 0:
                    raise RuntimeError(
                        f"quiescence timed out draining {name} queue "
                        f"({queue.unfinished_tasks} unfinished)")
                time.sleep(min(0.05, remaining()))

        worker_specs = (
            (getattr(self, "_organism_queue", None),
             getattr(self, "_organism_worker_thread", None)),
            (getattr(self, "_tapestry_queue", None),
             getattr(self, "_tapestry_worker_thread", None)),
            (getattr(self, "_diary_queue", None),
             getattr(self, "_diary_thread", None)),
        )
        for queue, thread in worker_specs:
            if queue is None or thread is None or not thread.is_alive():
                continue
            queue.put(None, timeout=remaining())
            thread.join(timeout=remaining())
            if thread.is_alive():
                raise RuntimeError(
                    f"quiescence timed out joining {thread.name}")
            if queue.unfinished_tasks:
                raise RuntimeError(
                    f"{thread.name} exited with unfinished queue tasks")

        spike_certificate = {"enabled": False}
        if getattr(self, "_spike_bus", None) is not None:
            spike_certificate = {
                "enabled": True,
                "injected_before_drain": self._spike_bus.injected_count,
                "delivered_before_drain": self._spike_bus.delivered_count,
                "dropped_before_drain": self._spike_bus.dropped_count,
                "queued_before_drain": self._spike_bus.qsize(),
            }
            self._spike_bus.quiesce(timeout=remaining())
            spike_certificate.update({
                "injected": self._spike_bus.injected_count,
                "delivered": self._spike_bus.delivered_count,
                "dropped": self._spike_bus.dropped_count,
                "queued": self._spike_bus.qsize(),
                "thread_alive": bool(
                    getattr(self._spike_bus, "_thread", None)
                    and self._spike_bus._thread.is_alive()),
            })

        queue_certificate = {
            name: {"unfinished": queue.unfinished_tasks, "queued": queue.qsize()}
            for name, queue in queues
        }
        self._engine_quiescence_complete = True
        return {
            "pending_turns": 0,
            "active_mutations": 0,
            "engine_threads_joined": True,
            "queues_drained": True,
            "raw_threads": raw_thread_certificate,
            "queues": queue_certificate,
            "spike_bus": spike_certificate,
        }

    def resume_after_failed_quiescence(self):
        """Composite quiescence is intentionally irreversible."""
        raise RuntimeError(
            "engine quiescence is irreversible; process replacement is required")

    def strict_shutdown(self, timeout=120.0):
        """Quiesce a discarded instance and propagate any incomplete proof."""
        return self.quiesce_background_workers(timeout=timeout)

    def shutdown(self):
        """GL-BUG-GUALA-WORKER-THREAD-LEAK (found live during -203/-205
        emission-section testing): every Guala() instance starts its own
        organism-writer/tapestry-writer/diary-writer daemon threads
        (_ensure_organism_worker/_ensure_tapestry_worker/_ensure_diary_worker)
        and NOTHING ever stopped them -- each worker loop's own `while True:
        item = queue.get(); if item is None: return` sentinel exists but was
        never invoked anywhere. In production this cost nothing (one Guala
        per process, process exit kills daemon threads for free), but any
        code path that constructs more than one Guala in a single process
        (every test file that builds several engines, admin re-init, etc.)
        leaks three live threads per instance forever -- each one still
        holding its old organism/tapestry alive (blocking GC) and competing
        for the GIL with every later instance. Measured live: read_sentence
        cost grew 2.0s -> 7.2s -> 10.6s -> 13.3s across 4 successive
        unshut-down Guala() instances in one process (thread count 4 -> 7
        -> 10 -> 13), a genuine multi-minute hang at just a handful of
        instances. Call this when an instance is truly done (test teardown,
        any future re-init path) to signal all three workers to exit."""
        try:
            self.quiesce_background_workers(timeout=5.0)
        except Exception:
            # Test/process teardown fallback only.  Production sealing calls
            # quiesce_background_workers directly and must propagate failure.
            self._reading_stop.set()
            self._daydream_running = False
            for q in (getattr(self, "_organism_queue", None),
                      getattr(self, "_tapestry_queue", None),
                      getattr(self, "_diary_queue", None)):
                if q is not None:
                    try:
                        q.put_nowait(None)
                    except Exception:
                        pass
            if getattr(self, "_spike_bus", None) is not None:
                self._spike_bus.stop()

    def _tapestry_worker_loop(self):
        """GL-CMD-175 P2 perf fix: single persistent background writer for
        tapestry exposure -- see _enqueue_tapestry_expose."""
        while True:
            item = self._tapestry_queue.get()
            try:
                if item is None:
                    return
                word_a, word_b = item
                with self._tapestry_lock:
                    for m in self.tapestry.mosaics:
                        m.expose(word_a, word_b)
                    self.tapestry._tick += 2
            finally:
                self._tapestry_queue.task_done()

    def _ensure_tapestry_worker(self):
        if self._tapestry_queue is not None:
            return
        with self._tapestry_worker_start_lock:
            if self._tapestry_queue is not None:  # lost a race to another thread
                return
            # GL-CMD-SLOT-LIMITS-REMOVAL-EVE-20260707-v1: maxsize=2000
            # KEPT, not removed -- same confirmed runaway pattern as
            # _organism_queue (direct stress test: unbounded feeder grew
            # this queue by ~2.3M items and ~200MB RSS every 3 seconds
            # with the cap removed). See the accompanying report.
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
        if self._engine_quiesced:
            raise RuntimeError("tapestry mutation rejected after quiescence")
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
        exception can't wedge a future join() forever.

        GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1: also drains
        self._organism_sensory_queue (per-hemisphere wave-summary
        pushes, see wave_summary.py) on this SAME single thread -- moves
        the 64x neuron.step() cost off _autonomy_tick's synchronous path
        entirely (measured there at 246-290ms/call, confirmed via a
        controlled isolated timing comparison, see GL-RPT-WAVE-ATLAS-
        DECAY-BUILD-C1-20260707-v3 -- wave-atlas decay never touched
        this cost since it scales with organism-internal state, not
        wave-atlas size). Word queue keeps priority: checked first,
        non-blocking; sensory queue checked next, non-blocking; a short
        (0.1s) blocking wait on the word queue is the idle path so this
        thread never busy-spins when both are empty -- not a tuned
        priority weight, just how two queues share one consumer without
        polling in a hot loop."""
        while True:
            if self._organism_pause_req.is_set():
                # Save-time park: acknowledge, hold between items, resume
                # the instant the save clears the request. Never parks
                # mid-item, so no fold is ever half-applied.
                self._organism_pause_ack.set()
                while self._organism_pause_req.is_set():
                    time.sleep(0.02)
                self._organism_pause_ack.clear()
                continue
            try:
                item = self._organism_queue.get_nowait()
                source = "word"
            except _queue.Empty:
                item = None
                source = None
            if source is None:
                try:
                    item = self._organism_sensory_queue.get_nowait()
                    source = "sensory"
                except _queue.Empty:
                    source = None
            if source is None:
                try:
                    item = self._organism_queue.get(timeout=0.1)
                    source = "word"
                except _queue.Empty:
                    continue  # nothing arrived within the wait window -- re-check both

            if source == "sensory":
                hemi_id, input_signal, sensory_tick, input_chi = item
                _sensory_t0 = time.monotonic()
                try:
                    hemi = self.organism.brain._hemi_map.get(hemi_id)
                    if hemi is not None:
                        # --- GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3 ---
                        # Dual-write spike injection at the actual production
                        # convergence point (LoomBrain.step, where this
                        # mechanism originally lived, has zero production
                        # callers -- confirmed in GL-RPT-PHASE-1-V2-REVIVE-
                        # C1-20260708-v2). Runs alongside the legacy hemi.step
                        # below, never instead of it. No-op if the spike bus
                        # isn't wired (EVENT_DRIVEN_SUBSTRATE=0, or restore
                        # hasn't completed wire_spike_bus() yet).
                        #
                        # GL-CMD-SENSORY-SPIKE-GATE-EVE-20260709-v1: gated
                        # SEPARATELY from the word branch below via
                        # SENSORY_SPIKE_INJECTION_ENABLED (default "0", i.e.
                        # off), independent of EVENT_DRIVEN_SUBSTRATE. Real
                        # incident tonight: wave-atlas cells never decay to
                        # exactly zero, so this branch never goes quiet --
                        # one entry neuron per hemisphere gets kicked
                        # continuously (confirmed live: 14M+ fire events,
                        # 3792/sec, zero synapses ever updated). The word
                        # branch is not implicated and stays on the existing
                        # EVENT_DRIVEN_SUBSTRATE gate, unchanged.
                        try:
                            _brain = self.organism.brain
                            if (getattr(_brain, '_spike_bus', None) is not None
                                    and os.environ.get(
                                        "SENSORY_SPIKE_INJECTION_ENABLED", "0") == "1"):
                                _brain._inject_input_as_spikes(
                                    input_signal=input_signal,
                                    input_chi=input_chi,
                                    modality=hemi_id,
                                )
                        except Exception as _inj_e:
                            print(f"[GualaLoom] spike injection (sensory) "
                                  f"non-fatal fail hemi={hemi_id!r}: {_inj_e}")
                        # --- End injection ---
                        with self._organism_lock:
                            hemi.step(input_signal, sensory_tick, input_chi)
                        self._log_substrate_event(
                            "sensory_organism_processed", tick=sensory_tick,
                            hemi_id=hemi_id,
                            wall_clock_delay=round(time.monotonic() - _sensory_t0, 4))
                except Exception as _se:
                    print(f"[GualaLoom] organism sensory step failed for "
                          f"hemi={hemi_id!r} (non-fatal): {_se}")
                finally:
                    self._organism_sensory_queue.task_done()
                continue

            # source == "word"
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
            _item_t0 = time.monotonic()
            try:
                signal = _organism_signal_with_senses(
                    word, self._organism_transducer, sight_signal,
                    sound_signal, modal_signal)

                # --- GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3 ---
                # Dual-write spike injection at the actual production
                # convergence point for text (see sensory branch above for
                # the same reasoning). input_chi recomputed from the word
                # via a throwaway LanguageKrimelack -- same primitive used
                # elsewhere in this file for the identical purpose (e.g.
                # recall_scene_for_word above), deterministic: same word
                # always produces the same chi. Runs alongside the legacy
                # experience_word() call below, never instead of it.
                try:
                    _brain = self.organism.brain
                    if getattr(_brain, '_spike_bus', None) is not None:
                        _inject_krim = LanguageKrimelack()
                        _inject_krim.transduce(word)
                        _word_chi = _inject_krim.winding
                        _brain._inject_input_as_spikes(
                            input_signal=word,
                            input_chi=_word_chi,
                            modality="language",
                        )
                except Exception as _inj_e:
                    print(f"[GualaLoom] spike injection (word) non-fatal "
                          f"fail word={word!r}: {_inj_e}")
                # --- End injection ---

                # GL-CMD-ORGANISM-WAVE-MEMORY-207 W3 (Joe's no-locks
                # ruling): writes are lock-free spill_write into per-neuron
                # wave cells now. The single worker thread's queue.get()
                # loop is what keeps writes in FIFO order (Eve's -179
                # condition); the lock was never needed for that, only for
                # excluding readers, and readers no longer need excluding.
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
                # GL-CMD-GROWTH-TRUTH-EVE-20260705-198 P3b: "growth we
                # cannot see is growth we cannot verify" -- one
                # organism_fold event per real division, drained right
                # after the experience_word() call that may have caused
                # it (folding is synchronous within that call).
                for _fold in self.organism.pop_fold_events():
                    self._log_substrate_event("organism_fold", word=word,
                                              **_fold)
            except Exception as _oe:
                print(f"[GualaLoom] organism experience_word failed for "
                      f"{word!r} (non-fatal): {_oe}")
            finally:
                # GL-CMD-ORGANISM-WAVE-MEMORY-207 W5: rolling per-item cost,
                # surfaced in /status next to queued/dropped -- the honest
                # number that used to climb unbounded with lifetime history
                # (20ms/word "and climbing" per -179) and should now stay
                # roughly flat regardless of how long she's been alive.
                _item_ms = (time.monotonic() - _item_t0) * 1000.0
                self._organism_item_ms_recent.append(_item_ms)
                if len(self._organism_item_ms_recent) > 50:
                    self._organism_item_ms_recent.pop(0)
                self._organism_queue.task_done()

    def _ensure_organism_worker(self):
        if self._organism_queue is not None:
            return
        with self._organism_worker_start_lock:
            if self._organism_queue is not None:  # lost a race to another thread
                return
            # GL-CMD-SLOT-LIMITS-REMOVAL-EVE-20260707-v1: maxsize=2000
            # KEPT, not removed -- confirmed via direct stress test that
            # this specific queue has no other bounding mechanism: an
            # unbounded feeder outpacing the single-threaded organism
            # worker (already documented as slow under real contention
            # earlier this session) grew the queue by ~2.4M items and
            # ~200MB of RSS every 3 seconds, unbounded, with the cap
            # removed. This is the dispatch's own named halt condition
            # ("Runaway after cap removal -- cap was catching real bug"),
            # confirmed empirically, not assumed. See the accompanying
            # report for the full test.
            self._organism_queue = _queue.Queue(maxsize=2000)
            t = threading.Thread(target=self._organism_worker_loop,
                                 daemon=True, name="organism-writer")
            t.start()
            self._organism_worker_thread = t

    def _enqueue_organism_sensory(self, hemi_id, input_signal, tick, input_chi=None):
        """GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1: per-hemisphere
        wave-summary push (see wave_summary.py), drained asynchronously
        by the same worker thread as the word queue. self._organism_
        sensory_queue is unbounded (no maxsize, unlike the word queue) --
        put() here never blocks the caller (the main autonomy tick), by
        construction, not by a size check.

        _ensure_organism_worker() is called here too (not just from the
        word-enqueue paths): the worker thread only starts on its first
        real item, and a sensory push can legitimately be the FIRST
        organism-bound work of a fresh boot (e.g. give_experience before
        any word has been read) -- without this call, sensory items would
        sit in the queue forever with no thread ever draining them.

        input_chi: GL-CMD-BRAIN-STEP-CHI-DISPATCH-EVE-20260707-v2, passed
        through to hemi.step at drain time. None (default) preserves prior
        behavior exactly (all neurons step)."""
        if self._engine_quiesced:
            raise RuntimeError("organism sensory mutation rejected after quiescence")
        self._ensure_organism_worker()
        self._organism_sensory_queue.put((hemi_id, input_signal, tick, input_chi))

    def _replay_sensory_echo(self, word):
        """GL-CMD-ENABLE-COGNITION-EVE-20260705-211 / Joe 2026-07-06: replay
        a word's own REAL past sensory grounding when no live camera/mic
        frame exists right now.

        "Real" is narrow and deliberate here: an atlas entry only counts if
        its own sensory_refs contains a reference to an actual stored
        picture/sound/camera/video ("pic:", "snd:", "cam:", "vid:" prefixes
        -- the same real-source tags this file already writes at teach
        time, e.g. line ~6291's `sensory_refs=[f"pic:{pic.item_id}"]").
        Anything else (empty, or a non-sensory tag like a teacher
        correction's own bookkeeping refs) means this word was never
        really grounded, and this returns (None, None) -- no growth
        funded, same as if this function didn't exist. No invented
        signal: every number driving the returned waveform (strength,
        valence, arousal) is a real value this exact binding already had
        recorded from when it was really grounded, not a fabricated one.

        Physically-motivated shape, same idiom as
        sensory_generators.generate_touch_waveform's channels: the memory's
        own recorded strength sets how strong the echo is, its arousal sets
        how long it stays vivid before fading (a more arousing memory
        lingers longer -- the exact asymmetry AdaptingFoveaKrimelack's own
        adapt/recover already uses), its valence sets a phase drift (the
        same role valence already plays on live bindings elsewhere in this
        file, e.g. line ~3671's `coherent_magnitude = strength * (1+valence)`).

        Returns (sight_echo, sound_echo); either may be None depending on
        which real modality the strongest matching binding actually had."""
        # GL-CMD-ENABLE-COGNITION-EVE-20260705-211 / Joe 2026-07-06, caught
        # live the same night this shipped: this runs synchronously, once
        # per word, in the read_word() hot path (the organism write itself
        # is backgrounded, but this snapshot step is not). Scanning every
        # entry in the chi neighborhood unbounded is the exact same mistake
        # already fixed once tonight in pr_consensus_divergence -- same
        # fix, same reasoning: a hard cap on entries actually examined, not
        # on atlas size. A grounded word usually isn't hiding as the 501st
        # entry checked; capping trades a small chance of missing a real
        # grounding for a bounded, constant-time cost on every single word.
        _REPLAY_SCAN_CAP = 200
        k = LanguageKrimelack()
        k.transduce(word)
        chi = k.winding
        best = None
        best_refs = []
        _scanned = 0
        for d in range(-self.atlas.band, self.atlas.band + 1):
            for e in self.atlas.entries.get(chi + d, []):
                _scanned += 1
                if _scanned > _REPLAY_SCAN_CAP:
                    break
                refs = e.get("sensory_refs") or []
                if not refs:
                    continue
                real_refs = [r for r in refs if isinstance(r, str)
                             and r.split(":", 1)[0] in ("pic", "snd", "cam", "vid")]
                if not real_refs:
                    continue
                sec = self.sections.get(e.get("section", ""))
                if not sec or e.get("motif", 0) >= len(sec.modes):
                    continue
                _, _, wl = sec.modes[e["motif"]]
                if not wl or wl.lower() != word.lower():
                    continue
                if best is None or e.get("strength", 0) > best.get("strength", 0):
                    best, best_refs = e, real_refs
            if _scanned > _REPLAY_SCAN_CAP:
                break
        if best is None:
            return None, None

        strength = float(best.get("strength", 0.5))
        valence = float(best.get("valence", 0.0))
        arousal = float(best.get("arousal", 0.5))
        t = np.linspace(0, 2.0, 200)
        tau = 0.4 + 1.0 * arousal
        echo = strength * np.exp(-t / tau) * np.cos(2 * np.pi * (1.0 + valence) * t)

        had_visual = any(r.startswith(("pic:", "cam:", "vid:")) for r in best_refs)
        had_auditory = any(r.startswith("snd:") for r in best_refs)
        return (echo if had_visual else None), (echo if had_auditory else None)

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
        # GL-CMD-ENABLE-COGNITION-EVE-20260705-211 / Joe 2026-07-06: no live
        # camera/mic frame is the overwhelming common case (reading,
        # conversation). Before this, that meant this word contributes
        # zero growth-funding, full stop -- even for a word she has
        # genuinely, really seen or heard before. A person doesn't need
        # their eyes pointed at the Alps to have "Alps" mean something --
        # the word reopens their own real memory of it. Same principle
        # here: if no live frame exists, check whether this word has ever
        # been REALLY sensory-grounded (see _replay_sensory_echo's own
        # docstring for exactly what counts as real), and replay a signal
        # built from that real binding's own recorded numbers. An
        # ungrounded word still gets nothing, honestly, same as before.
        # GL-CMD-ENABLE-COGNITION-EVE-20260705-211 / Joe 2026-07-06: disabled
        # again, same night, after live converse_timing showed read_ms at
        # 24.4s of a 27.2s total turn -- read_ms was ~6s on the immediately
        # prior deploy, before this call existed. The 200-entry cap alone
        # didn't bring it back down, and a raw profile of the cheap parts
        # (LanguageKrimelack.transduce: 0.05ms/word) doesn't explain the
        # gap, so something about this call's real cost isn't understood
        # yet. 2026-07-10: gated behind SENSORY_ECHO_REPLAY_ENABLED (default
        # OFF, see its own comment above) instead of hardcoded off, so it
        # can be tried live and instantly reverted without a redeploy.
        if SENSORY_ECHO_REPLAY_ENABLED and sight_signal is None and sound_signal is None:
            _replay_sight, _replay_sound = self._replay_sensory_echo(word)
            if _replay_sight is not None:
                sight_signal = _replay_sight
            if _replay_sound is not None:
                sound_signal = _replay_sound
        if self._engine_quiesced:
            raise RuntimeError("organism mutation rejected after quiescence")
        try:
            self._ensure_organism_worker()
            self._organism_queue.put_nowait(
                (word, sight_signal, sound_signal, modal_signal))
        except _queue.Full:
            self._organism_dropped_count += 1
        except Exception:
            pass

    def _enqueue_organism_experience_explicit(self, word, sound_signal=None,
                                               sight_signal=None):
        """GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-208: explicit-signal
        sibling of _enqueue_organism_remember, for callers that already
        HAVE a real sight/sound signal in hand (e.g. /bundle:'s referenced
        or freshly-uploaded picture/sound teaching) rather than reading
        the shared _last_sight_signal/_last_sound_signal caches. Those
        caches are for the ambient, continuous LIVE camera/mic case and
        are wall-clock windowed (SENSE_BINDING_WINDOW_SEC) against real
        frames arriving on their own cadence -- a caller-supplied signal
        would race a concurrent real mic/camera frame in the moment
        between being set there and read here. This bypasses that cache
        entirely: the signal travels straight into the same queue the
        worker already drains, so it is the SAME experience_word() call,
        same single-writer FIFO discipline, same worker thread -- no new
        organism-write mechanism, only a second way to reach the queue."""
        if self._engine_quiesced:
            raise RuntimeError("explicit organism mutation rejected after quiescence")
        try:
            self._ensure_organism_worker()
            self._organism_queue.put_nowait((word, sight_signal, sound_signal, None))
        except _queue.Full:
            self._organism_dropped_count += 1
        except Exception:
            pass

    def _best_fit_location(self, locations):
        """GL-BUG-SLOTS-NOT-PATTERNS (Joe, 2026-07-06): a candidate word's
        grammatical role was being chosen by _word_to_emission_sections'
        write-time recency (itself already fixed once tonight, from a worse
        bug where raw section-iteration order beat real timestamps) -- but
        recency-of-write is still not a real pattern match, it's a clock
        reading. A word that has ever occupied more than one role section
        carries a DIFFERENT DSF fingerprint in each one (Section.receive
        reinforces its OWN copy of that word's pattern toward whatever
        context it was written in each time). The substrate-native question
        -- which of this word's role-homes actually fits what's happening
        RIGHT NOW, not which was written most recently -- is answered by
        comparing each home's stored DSF against self._last_lang_dsf (the
        live DSF of what she just read, set in read_word/read_sentence,
        already used elsewhere for this same emission-coupling purpose) via
        cosine similarity -- the same comparison Section.receive's own
        similarity scan already does, just applied across a word's
        different role-homes instead of across different words. This also
        makes the self-hearing ratchet fixed earlier tonight structurally
        moot for any word with more than one real role-home: a stale echo
        commit no longer wins just by being newest, it has to actually
        resemble the current moment.
        Falls back to the most recent location when only one exists, or
        when no current DSF is available yet (e.g. the very first turn),
        rather than guessing further."""
        if len(locations) == 1:
            return locations[0]
        cur_dsf = getattr(self, "_last_lang_dsf", None)
        if cur_dsf is None:
            return locations[-1]
        cur = cur_dsf.to_array()
        cur_norm = np.linalg.norm(cur)
        if cur_norm < 1e-12:
            return locations[-1]
        best_loc = None
        best_score = -2.0  # cosine similarity range is [-1, 1]
        for loc in locations:
            sec_name, mode_idx, _ = loc
            sec = self.sections.get(sec_name)
            if sec is None or mode_idx >= len(sec.modes):
                continue
            mode_dsf = sec.modes[mode_idx][0].to_array()
            mode_norm = np.linalg.norm(mode_dsf)
            if mode_norm < 1e-12:
                continue
            score = float(np.dot(mode_dsf, cur) / (mode_norm * cur_norm))
            if score > best_score:
                best_score = score
                best_loc = loc
        return best_loc if best_loc is not None else locations[-1]

    # ------------------------------------------------------------------
    # GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3: idempotent spike-bus
    # wiring, extracted from __init__ so it can also run after
    # load_full_state() replaces self.organism wholesale (see that
    # method for the call site). __init__ still constructs self._spike_bus
    # itself -- this method only wires an ALREADY-CONSTRUCTED bus onto
    # whatever the current self.organism happens to be.
    # ------------------------------------------------------------------

    def wire_spike_bus(self):
        """Wire self._spike_bus onto every neuron and onto LoomBrain.

        Idempotent -- safe to call multiple times (each call rebuilds the
        registry and re-applies the same references) and safe to call
        when self._spike_bus is None (EVENT_DRIVEN_SUBSTRATE=0 or not
        constructed yet), in which case it's a no-op.

        GL-CMD-MOOD-BROADCAST-WIRE-20260712: also (re-)wires the global
        mood/affect broadcast (neuron.py's LoomNeuron.set_mood_source /
        brain.py's LoomBrain.wire_mood_broadcast) onto the same
        just-rebuilt neuron population, via the same call sites this
        method already has (construction, gualaloom_v5_engine.py:2586;
        post-restore, gualaloom_v5_engine.py:12078+) -- deliberately NOT
        a new, separate call site of its own. Correct to gate this on the
        same early return above: LoomNeuron.receive_spike() -- the only
        place _mood_source is ever read (see neuron.py) -- is itself only
        ever invoked by SpikeBus delivery (substrate/spike_bus.py), so
        with no spike bus there is no receive_spike() call for a mood
        source to modulate either way; wiring it independently of the bus
        would be a real no-op dressed as a live connection. self.needs
        (gualaloom_v5_engine.py:2355) is constructed once in __init__,
        before this method's first call, and is only ever mutated in
        place thereafter (_apply_needs et al. assign fields, never
        rebind self.needs) -- so the SAME real Needs instance stays
        correctly wired across every restore, with no risk of wiring a
        stale/discarded one. MOOD_BROADCAST_ENABLED stays the sole
        behavior gate (default OFF): this only ever assigns a reference,
        exactly mirroring set_spike_bus/set_word_firing_callback above.
        """
        if getattr(self, '_spike_bus', None) is None:
            return

        # Rebuilt against CURRENT self.organism every call -- after
        # load_full_state() replaces self.organism, any registry built
        # at __init__ time points at now-discarded neuron objects.
        neuron_registry = {
            n.neuron_id: n
            for hemi in self.organism.brain.hemispheres
            for n in hemi.cluster.neurons
        }

        if hasattr(self._spike_bus, '_neuron_registry'):
            self._spike_bus._neuron_registry = neuron_registry

        for neuron in neuron_registry.values():
            neuron.set_spike_bus(self._spike_bus)
            neuron.set_word_firing_callback(self._on_word_firing)

        self.organism.brain.set_spike_bus(self._spike_bus)
        self.organism.brain._guala_ref = self
        self.organism.brain.wire_mood_broadcast(self.needs)

    # ------------------------------------------------------------------
    # GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2: word<->neuron
    # population mapping + entry-neuron selection for the new (parallel,
    # not-yet-production-serving) STDP/spike/membrane mechanism.
    # ------------------------------------------------------------------

    def _on_word_firing(self, word, neuron_id: str) -> None:
        """Called by LoomNeuron._on_fire_bookkeeping (via
        set_word_firing_callback, wired in __init__) when a word context
        is available at fire time -- i.e. this neuron just fired as a
        direct entry point for a word injection (see neuron.py's
        EXTERNAL_SOURCE_PREFIX handling in _fire). Maintains bidirectional
        word<->neuron association for the new event-driven path. word is
        None for fires with no word context (propagated spikes, non-
        language injection) -- those don't touch either map."""
        if not word:
            return
        wl = word.lower()
        self._word_neuron_map.setdefault(wl, set()).add(neuron_id)
        if neuron_id not in self._neuron_word_map:
            self._neuron_word_map[neuron_id] = wl

    def _all_neurons(self):
        """Flat iterator over every neuron in the substrate. Mirrors
        brain.py's own list-comprehension idiom (used inside
        recall_fast's legacy event_count branch)."""
        return [
            n
            for hemi in self.organism.brain.hemispheres
            for n in hemi.cluster.neurons
        ]

    def _neuron_to_word(self, neuron):
        """Primary word associated with this neuron, if any (from the
        new word_neuron_map, not the legacy binding_atlas)."""
        return self._neuron_word_map.get(neuron.neuron_id)

    # chi wraps modularly everywhere else this codebase treats it as an
    # address (wave_atlas's chi % N_CELLS, _map_inject's wrap-around
    # distance) -- 262144, matches tools/wave_constants.py N_CELLS and
    # neuron.py's MAX_CHI_DISTANCE (duplicated locally rather than
    # cross-imported: neuron.py already imports FROM this module for
    # _grandurun_state/_SPIN_VECTOR_DIM, so importing back would be
    # circular; this file already has no such import, so it stays a
    # plain local constant like neuron.py's own copy).
    _CHI_ADDRESS_SPACE = 262144

    def _chi_to_neurons(self, chi: int, band=None):
        """Neurons whose chi_position is within `band` of `chi`, wrapping
        both through the chi address space before comparing.

        Two real gaps closed here now that chi_position is finally
        populated on every neuron (previously always None -- this always
        returned [] and every entry fell through to the
        ENTRY_SAMPLE_SIZE random fallback, unconditionally, for every
        single word):

        1. Real chi (krimelack winding) never resets and grows
           unboundedly over a krimelack's lifetime (measured directly:
           30000+ after 2000 words, and production has processed far
           more than that) while chi_position is fixed at seed --
           without wrapping, a raw difference against a large or
           negative chi would essentially never land near any neuron.
           Reducing both sides through the same modulus this codebase
           already uses for chi elsewhere (wave_atlas, _map_inject) is
           completing an existing convention, not inventing a new one.
        2. ENTRY_CHI_BAND=8 assumed a population dense enough that band=8
           would cover a real neighborhood; at the organism's real size
           this seed produces (64 neurons spread across the full chi
           address space), 8 is far smaller than the ~4096 average
           spacing between neurons, so band=8 would still almost never
           match anyone even with wrapping fixed. The band this function
           actually needs is derived from real population geometry (half
           the average spacing, the minimum for every wrapped chi value
           to have some neuron within reach) rather than the flat
           constant, and recomputes as the organism grows via folding
           division rather than going stale.
        """
        neurons = [n for n in self._all_neurons() if n.chi_position is not None]
        if not neurons:
            return []
        if band is None:
            avg_spacing = self._CHI_ADDRESS_SPACE / len(neurons)
            band = max(ENTRY_CHI_BAND, avg_spacing / 2.0)
        space = self._CHI_ADDRESS_SPACE
        chi_wrapped = chi % space
        matches = []
        for n in neurons:
            raw_dist = abs(n.chi_position - chi_wrapped)
            wrap_dist = min(raw_dist, space - raw_dist)
            if wrap_dist <= band:
                matches.append(n)
        return matches

    def _select_entry_neurons(self, input_chi, modality=None):
        """Select neurons to receive initial spike injection for a given
        input. Phase 1: chi-proximity if input_chi provided; otherwise
        (or if chi-proximity finds nothing -- always true in Phase 1 per
        _chi_to_neurons's note above) falls back to a small random
        sample. Called from LoomBrain._inject_input_as_spikes via
        self._guala_ref.

        GL-CMD-ENTRY-NEURON-BROADEN (see ENTRY_NEURON_BROADEN_COUNT's
        module comment for the full safety reasoning): when
        ENTRY_NEURON_BROADEN_ENABLED="1" and chi-proximity found at least
        one real candidate, widen the entry set to up to
        ENTRY_NEURON_BROADEN_COUNT neurons drawn from the SAME hemisphere
        as the primary match -- never touches the random-fallback branch
        below, never crosses a hemisphere boundary. Default OFF: this
        branch is not reached at all unless the env var is explicitly
        set, so existing behavior is unchanged byte-for-byte by default."""
        if input_chi is not None:
            candidates = self._chi_to_neurons(input_chi)
            if candidates:
                if os.environ.get("ENTRY_NEURON_BROADEN_ENABLED", "0") == "1":
                    candidates = self._broaden_entry_neurons_same_hemisphere(
                        candidates, input_chi)
                return candidates
        all_neurons = self._all_neurons()
        return random.sample(all_neurons, min(ENTRY_SAMPLE_SIZE, len(all_neurons)))

    def _broaden_entry_neurons_same_hemisphere(self, candidates, input_chi):
        """Widen `candidates` (chi-proximity matches, at least one real
        neuron per caller) up to ENTRY_NEURON_BROADEN_COUNT total, adding
        only neurons from the SAME hemisphere as candidates[0] -- see
        ENTRY_NEURON_BROADEN_COUNT's module comment for why this
        structurally bounds injection breadth to one hemisphere
        (8/64=12.5%) regardless of the target count.

        No-op (returns `candidates` unchanged) if already at or above the
        target count, if the primary's hemisphere can't be resolved, or
        once the hemisphere's own population is exhausted -- this never
        raises and never returns fewer than it was given.

        Additional neurons are chosen deterministically: nearest by
        wrapped chi-distance to `input_chi` first (same metric
        _chi_to_neurons already uses), neuron_id as a tie-breaker so two
        runs with identical state always pick the same set -- no
        randomness introduced here, unlike the unrelated random-fallback
        branch in the caller.

        Scope of the "bounded to one hemisphere" guarantee: this method
        only ever ADDS same-hemisphere-as-candidates[0] neurons -- it
        does not filter `candidates` itself down to one hemisphere. On
        today's real population, _chi_to_neurons empirically always
        returns exactly one candidate (verified across 163 real words in
        test_entry_neuron_broaden.py), so this distinction is moot in
        production right now. If population growth (Phase 2, not yet
        built -- see GL-RPT-BLUEPRINT-DEPLOYMENT-AUDIT-C1-20260712-v1)
        ever makes _chi_to_neurons itself return multi-hemisphere
        candidates, that would already be true with this flag OFF -- a
        pre-existing property of chi-proximity matching, not a new risk
        this addition introduces. test_broaden_on_stays_bounded_to_one_
        hemisphere asserts the single-hemisphere invariant directly
        against real state rather than assuming it, so it will fail
        loudly (not silently drift) if that ever changes.
        """
        target_count = max(1, int(
            os.environ.get("ENTRY_NEURON_BROADEN_COUNT", str(ENTRY_NEURON_BROADEN_COUNT))))
        if len(candidates) >= target_count:
            return candidates
        primary = candidates[0]
        hemi_id = primary.neuron_id.split("_n")[0]
        hemi = self.organism.brain._hemi_map.get(hemi_id)
        if hemi is None:
            return candidates
        existing_ids = {n.neuron_id for n in candidates}
        space = self._CHI_ADDRESS_SPACE
        chi_wrapped = input_chi % space
        pool = []
        for n in hemi.cluster.neurons:
            if n.neuron_id in existing_ids or n.chi_position is None:
                continue
            raw_dist = abs(n.chi_position - chi_wrapped)
            wrap_dist = min(raw_dist, space - raw_dist)
            pool.append((wrap_dist, n.neuron_id, n))
        pool.sort(key=lambda t: (t[0], t[1]))
        extra_needed = target_count - len(candidates)
        extended = list(candidates) + [n for _, _, n in pool[:extra_needed]]
        return extended

    def _brain_emission_candidates(self, input_words):
        """GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2 item 8, extended
        by GL-CMD-EMISSION-SHADOW-EVE-20260709 (design only -- NOT
        enabled by default, NOT deployed; see that dispatch's report for
        the halt-condition data this needs before any real cutover):
        three-way dispatch on RECALL_BACKEND, mirroring recall_fast's
        own dispatcher (brain.py) exactly, same env var, same shape of
        contract. "legacy" (default, unchanged): calls
        _brain_emission_candidates_legacy only -- byte-for-byte the
        production path throughout Phase 1. "stdp": calls
        _brain_emission_candidates_membrane only -- not used in
        production during Phase 1. "shadow": runs BOTH, logs a
        comparison via _log_emission_shadow_comparison, and returns the
        LEGACY result UNCHANGED -- observation-only, zero behavior
        change for callers, same non-fatal-on-failure contract as
        recall_fast's shadow branch (a membrane exception during shadow
        never prevents the legacy result from being returned).

        2026-07-08 note (superseded by the above): this docstring used
        to say "there's no separate shadow comparison for emission
        specifically" because emission's candidate SHAPE ((de, co,
        weight) tuples referencing _word_to_emission_sections) has no
        direct membrane-state equivalent, and recall_fast's own shadow
        log (which legacy's candidate gather already calls through,
        unchanged, once per query word) was the only signal that
        existed. That's still true of the raw shapes -- they are NOT
        comparable value-for-value, see _log_emission_shadow_comparison
        for how they're actually reconciled -- but recall_fast's shadow
        only ever compares individual per-query-word vote Counters, never
        the assembled, filtered CANDIDATE LIST this function returns
        (post section-home gating, self-echo exclusion, deep_atlas
        merge). That's a coarser, functionally different signal
        recall_fast's own shadow log can't see, which is what this
        extension adds."""
        backend = os.environ.get("RECALL_BACKEND", "legacy")
        if backend == "stdp":
            return self._brain_emission_candidates_membrane(input_words)
        elif backend == "shadow":
            legacy_candidates = self._brain_emission_candidates_legacy(input_words)
            try:
                membrane_candidates = self._brain_emission_candidates_membrane(input_words)
                self._log_emission_shadow_comparison(legacy_candidates, membrane_candidates, input_words)
            except Exception as _se:
                print(f"[GualaLoom] membrane shadow emission comparison failed "
                      f"(non-fatal, legacy candidates still returned): {_se}")
            return legacy_candidates
        return self._brain_emission_candidates_legacy(input_words)

    def _brain_emission_candidates_membrane(self, input_words):
        """New (not production-serving during Phase 1) emission backend:
        current neuron membrane state, decayed to now without disturbing
        it, top-K by activation among neurons with a known word
        association. HEURISTIC EMISSION_THRESHOLD/TOP_K_EMISSION (module
        level)."""
        now = time.monotonic()
        candidates = []
        for neuron in self._all_neurons():
            with neuron._neuron_lock:
                dt_ms = (now - neuron.last_update_time_s) * 1000.0
                if dt_ms > 0:
                    decay = math.exp(-dt_ms / neuron.tau_m_ms)
                    potential = (
                        neuron.membrane_rest
                        + (neuron.membrane_potential - neuron.membrane_rest) * decay
                    )
                else:
                    potential = neuron.membrane_potential

            if potential > EMISSION_THRESHOLD:
                associated_word = self._neuron_to_word(neuron)
                if associated_word:
                    candidates.append((neuron.chi_position, potential, associated_word))

        return sorted(candidates, key=lambda x: x[1], reverse=True)[:TOP_K_EMISSION]

    # --- GL-CMD-EMISSION-SHADOW-EVE-20260709 (design only -- not enabled,
    # not deployed): shadow-comparison support for _brain_emission_candidates.
    # ---
    # The two candidate SHAPES are not comparable value-for-value:
    #   legacy:   (de, co, weight) -- co={section: {mode_idx: weight}},
    #             weight is a vote-FRACTION in [0,1] (n_votes/total),
    #             already gated on self._word_to_emission_sections (a real
    #             committed section/mode home) and on self-echo exclusion.
    #   membrane: (chi_position, potential, word) -- potential is a raw
    #             membrane-potential float (no fixed range), word comes
    #             straight from _neuron_to_word with NO section-home gate
    #             and NO self-echo exclusion at all.
    # A raw comparison of these tuples means nothing (different units,
    # different filtering). What's actually comparable is WHICH WORDS
    # each path would nominate to speak -- so both are resolved down to
    # an ordered (word, weight) list first, and it's those WORD lists
    # that get compared. See _log_emission_shadow_comparison for the
    # agreement metric built on top of that.

    def _emission_legacy_top_words(self, candidates, k=5):
        """Resolve legacy's (de, co, weight) candidates into an ordered,
        deduplicated (word, weight) list -- using the EXACT SAME
        section/mode resolution _emit_from_invariants' topk path
        already uses (ordered_sections by max mode value, best_mid by
        max weight in that section) -- so this reflects what would
        actually be said, not an internal weight number invented just
        for this comparison."""
        ranked = sorted(candidates, key=lambda c: c[2], reverse=True)
        out = []
        seen = set()
        for de, co, weight in ranked:
            ordered_sections = sorted(
                [s for s in co.keys() if co.get(s)],
                key=lambda s: max(co[s].values()) if co[s] else 0.0,
                reverse=True)
            word = None
            for sec_name in ordered_sections:
                sec_co = co[sec_name]
                if not sec_co:
                    continue
                best_mid = max(sec_co, key=sec_co.get)
                sec = self.sections.get(sec_name)
                if sec is None or int(best_mid) >= len(sec.modes):
                    continue
                _, _, word_label = sec.modes[int(best_mid)]
                if word_label:
                    word = word_label.lower()
                break
            if word and word not in seen:
                seen.add(word)
                out.append((word, weight))
            if len(out) >= k:
                break
        return out

    def _emission_membrane_top_words(self, candidates, k=5, grounded_only=False):
        """Resolve membrane's (chi_position, potential, word) candidates
        (already sorted desc by potential) into an ordered, deduplicated
        (word, potential) list. grounded_only=True additionally filters
        to words with a real committed section home
        (self._word_to_emission_sections) -- the same real constraint
        legacy's own candidates already satisfy by construction. Without
        this filter, membrane can surface words legacy could never
        speak at all, which would inflate "disagreement" for a reason
        that has nothing to do with whether the STDP mechanism
        remembers the same things -- see _log_emission_shadow_comparison."""
        out = []
        seen = set()
        for _chi_pos, potential, word in candidates:
            if not word:
                continue
            wl = word.lower()
            if grounded_only and wl not in self._word_to_emission_sections:
                continue
            if wl in seen:
                continue
            seen.add(wl)
            out.append((wl, potential))
            if len(out) >= k:
                break
        return out

    def _log_emission_shadow_comparison(self, legacy_candidates, membrane_candidates,
                                         input_words) -> None:
        """Log a disagreement-relevant comparison between legacy and
        membrane emission candidates during RECALL_BACKEND=shadow.
        Observation only -- never affects what _brain_emission_candidates
        returns (mirrors brain.py's _log_recall_shadow_comparison
        contract exactly).

        top1_agree is the metric the >50%-disagreement halt condition
        (GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2's halt #3,
        extended to this seam) should actually be computed from, over a
        real observation window -- mirrors recall_fast's own
        `top_match` bool:
          - both legacy and grounded-membrane produce nothing -> agree
            (True). Silence agreeing with silence is real agreement,
            not a vacuous case to discard.
          - one produces a top word and the other produces nothing ->
            disagree (False). One backend would speak, the other would
            stay silent -- that's exactly the kind of divergence this
            halt condition exists to catch, not a case to skip.
          - both produce a top word -> agree iff it's the same word.

        top5_jaccard is a softer secondary signal (word-set overlap
        across the top 5 of each, post-grounding) -- useful diagnostic
        beyond the single pass/fail bit, not itself a halt criterion.

        membrane_top5_raw (unfiltered) is logged alongside
        membrane_top5_grounded (filtered to a real section home) so the
        "different candidate pool, not different memory" gap stays
        visible in the data rather than being silently averaged away --
        n_membrane_candidates_raw vs n_membrane_candidates_grounded on
        their own already say a lot about whether membrane's signal
        even reaches emission-eligible words at all."""
        legacy_top = self._emission_legacy_top_words(legacy_candidates, k=5)
        membrane_raw = self._emission_membrane_top_words(membrane_candidates, k=5, grounded_only=False)
        membrane_grounded = self._emission_membrane_top_words(membrane_candidates, k=5, grounded_only=True)

        legacy_top1 = legacy_top[0][0] if legacy_top else None
        membrane_top1 = membrane_grounded[0][0] if membrane_grounded else None
        if legacy_top1 is None and membrane_top1 is None:
            top1_agree = True
        elif legacy_top1 is None or membrane_top1 is None:
            top1_agree = False
        else:
            top1_agree = (legacy_top1 == membrane_top1)

        legacy_words = {w for w, _ in legacy_top}
        membrane_words = {w for w, _ in membrane_grounded}
        union = legacy_words | membrane_words
        top5_jaccard = (len(legacy_words & membrane_words) / len(union)) if union else 1.0

        self._log_substrate_event(
            "emission_shadow",
            queries=list(input_words)[:12] if input_words else [],
            legacy_top5=legacy_top,
            membrane_top5_raw=membrane_raw,
            membrane_top5_grounded=membrane_grounded,
            n_legacy_candidates=len(legacy_candidates),
            n_membrane_candidates_raw=len(membrane_candidates),
            n_membrane_candidates_grounded=len(membrane_words),
            top1_agree=top1_agree,
            top5_jaccard=top5_jaccard,
        )

    def _brain_emission_candidates_legacy(self, input_words):
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
        real candidate -- never partially substitutes the old gather.

        GL-BUG-LAST-WORD-CONCEPTUALIZATION (Joe, 2026-07-06): this used to
        query the organism with ONLY input_words[-1] -- one anchor word,
        not the utterance she was actually replying to. That's not
        conceptualization, it's a one-word echo association. A real
        utterance's meaning comes from ALL its words together, so this now
        queries the organism once per input word (bounded, see cap below)
        and merges the vote distributions, giving candidates a chance to
        resonate with the whole thought instead of whichever word
        happened to land last.

        GL-CMD-CREDO-RELEVANCE-WEIGHT-C1-20260711: the deep_atlas gather
        below additionally ranks/weights its candidates by real
        cross-query convergence (see DEEP_ATLAS_RELEVANCE_BOOST_PER_SEED's
        own comment) -- a word that resonates with more than one of this
        turn's input words outranks one only a single, possibly generic,
        seed word surfaces. Eligibility (the real-grounding gate) is
        unchanged; only weight/order among already-eligible candidates."""
        queries = list(input_words) if input_words else (
            [self._tapestry_prev_word] if self._tapestry_prev_word else [])
        if not queries:
            return []
        # Bound worst-case cost (she should be faster than a human at this,
        # not slower) -- ordinary conversational turns are well under this;
        # only a pasted wall of text would ever hit it.
        _QUERY_WORD_CAP = 12
        queries = queries[-_QUERY_WORD_CAP:]
        input_words_lower = set(w.lower() for w in input_words) if input_words else set()
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
        from collections import Counter as _Counter
        merged_votes = _Counter()
        n_queries_ok = 0
        for q in queries:
            try:
                # GL-CMD-ORGANISM-WAVE-MEMORY-207 W3: no lock -- see
                # _recognition_from_organism's matching comment.
                votes = self.organism.recall_fast(
                    _organism_signal(q, self._organism_transducer))
            except Exception as _oe:
                print(f"[GualaLoom] organism recall failed for query={q!r} "
                      f"(non-fatal, skipped): {_oe}")
                continue
            if votes:
                n_queries_ok += 1
                merged_votes.update(votes)
        if not merged_votes:
            return []
        total = sum(merged_votes.values())
        candidates = []
        n_with_section_home = 0
        # GL-CMD-NO-CAPS-COHERENCE-SPEAKS-EVE-20260705-203 U0b: the pre-trim
        # to a fixed vote count is deleted -- the physics downstream (the
        # greedy coherence selectors) sees her FULL vote distribution;
        # selection is the physics' job, not a slice's.
        for w, n_votes in merged_votes.most_common():
            if not w or w.lower() in input_words_lower:
                continue  # association, not self-echo (seam-3 convention)
            locations = self._word_to_emission_sections.get(w.lower())
            if not locations:
                continue  # only words with a real committed section home
            n_with_section_home += 1
            section, mode_idx, _matched_word = self._best_fit_location(locations)
            weight = (n_votes / total) if total else 0.0
            co = {section: {mode_idx: weight}}
            de = {"co_occurrence": co, "clarity": weight, "origin": "brain"}
            candidates.append((de, co, weight))
            input_words_lower.add(w.lower())  # don't also deep-atlas-surface this word below

        # 2026-07-08 finding: recall_exact_or_best (binding_atlas.py) fixed
        # recall_fast's degenerate all-words-cosine-1.0 bug, but that makes
        # recall_fast an IDENTITY function for anything she's been taught by
        # name -- queried with "dog" it now unanimously votes "dog", which
        # the "association, not self-echo" filter above always excludes.
        # Verified directly: every merged_votes entry for a sentence of
        # known words is 100% self-match, so the loop above now produces
        # zero candidates for exactly the inputs it most needs to handle.
        # The organism's population vote was never really supplying
        # association -- before the recognition fix it degenerately
        # matched every query to one fixed arbitrary word ("ball"), which
        # happened to slip past the self-echo check by coincidence, not by
        # being a real association.
        #
        # deep_atlas.entries[chi].co_occurrence (deep_atlas.py) is a
        # different kind of measure -- what else was recorded, across real
        # dream-cycle consolidation, near this word's own chi neighborhood
        # (cross-modal: modal_sound/modal_touch/smell_*/touch_temperature
        # sections alongside language ones, GL-CMD-DEEP-STORE-PHYSICS-86).
        # It measures co-occurrence, not identity, so it cannot degenerate
        # into self-echo the way recall_fast does. This is real sensory-
        # grounded association data that GL-CMD-VOICE-ORGANISM-CANDIDATES-195
        # stopped using for emission candidates in favor of the (now-proven
        # broken-for-this-purpose) organism vote; restoring it here as an
        # addition, not a replacement, so a query word that hasn't yet
        # survived to deep memory still falls back to whatever the
        # organism-vote path above can offer.
        # GL-CMD-CREDO-RELEVANCE-WEIGHT-C1-20260711: survey pass first --
        # call the SAME _deep_atlas_neighbor_candidates walk per query
        # word (unchanged function, unchanged real co-occurrence data),
        # but against a FIXED exclusion snapshot rather than one that
        # grows as we go -- so a candidate word that genuinely co-occurs
        # with more than one of this turn's own input words is visible
        # as such, instead of being silently claimed by whichever query
        # happened to run first and hidden from every later query's own
        # walk. This only changes what the RANKING pass below can see;
        # it does not add, remove, or re-gate any candidate word.
        _deep_exclude_snapshot = set(input_words_lower)
        _deep_proposals = {}  # word.lower() -> [(weight, section, mode_idx, word_label, query)]
        for q in queries:
            for word_label, weight, section, mode_idx in \
                    self._deep_atlas_neighbor_candidates(q, exclude_words=_deep_exclude_snapshot):
                _deep_proposals.setdefault(word_label.lower(), []).append(
                    (weight, section, mode_idx, word_label, q))

        n_deep_candidates = 0
        for wl, proposals in _deep_proposals.items():
            if wl in input_words_lower:
                continue  # already claimed by an earlier source this turn
            # Relevance = how many DISTINCT input words this candidate's
            # own real co-occurrence data actually resonates with --
            # spreading-activation convergence, not raw frequency. A
            # word proposed by only one seed (the common case) gets
            # n_distinct_queries==1 -> boost factor 1.0 -> unchanged
            # weight/behavior.
            n_distinct_queries = len(set(p[4] for p in proposals))
            best_weight, section, mode_idx, word_label, _q = max(proposals, key=lambda p: p[0])
            relevance_boost = 1.0 + min(
                DEEP_ATLAS_RELEVANCE_BOOST_MAX - 1.0,
                DEEP_ATLAS_RELEVANCE_BOOST_PER_SEED * (n_distinct_queries - 1))
            weight = best_weight * relevance_boost
            co = {section: {str(mode_idx): weight}}
            de = {"co_occurrence": co, "clarity": weight, "origin": "deep_atlas"}
            candidates.append((de, co, weight))
            input_words_lower.add(wl)
            n_deep_candidates += 1

        # GL-CMD-REFLECTION-EVE-20260710 (imagination half): a separate,
        # narrowly-scoped, low-weight source -- see _imagination_
        # candidates' own docstring for why this is NOT merged into the
        # deep_atlas loop above. Capped at IMAGINATION_MAX_CANDIDATES_
        # PER_TURN so a speculative recombination stays a subtle
        # background flavor, never a competing voice.
        n_imagination_candidates = 0
        if IMAGINATION_ENABLED:
            for q in queries:
                if n_imagination_candidates >= IMAGINATION_MAX_CANDIDATES_PER_TURN:
                    break
                for word_label, weight, section, mode_idx in \
                        self._imagination_candidates(q, exclude_words=input_words_lower):
                    if n_imagination_candidates >= IMAGINATION_MAX_CANDIDATES_PER_TURN:
                        break
                    co = {section: {str(mode_idx): weight}}
                    de = {"co_occurrence": co, "clarity": weight, "origin": "imagination"}
                    candidates.append((de, co, weight))
                    input_words_lower.add(word_label.lower())
                    n_imagination_candidates += 1

        # GL-CMD-REFLECTION-EMISSION-EVE-20260710 (reflection half): a
        # separate, narrowly-scoped, low-weight source, structurally
        # parallel to imagination above but drawing from self._reflections
        # (real remembered episodes) instead of deep_atlas hypotheses --
        # see _reflection_candidates' own docstring. Capped at
        # REFLECTION_EMISSION_MAX_CANDIDATES_PER_TURN so a remembered
        # moment stays a subtle background flavor, never a competing
        # voice.
        n_reflection_candidates = 0
        if REFLECTION_EMISSION_ENABLED:
            for q in queries:
                if n_reflection_candidates >= REFLECTION_EMISSION_MAX_CANDIDATES_PER_TURN:
                    break
                for word_label, weight, section, mode_idx in \
                        self._reflection_candidates(q, exclude_words=input_words_lower):
                    if n_reflection_candidates >= REFLECTION_EMISSION_MAX_CANDIDATES_PER_TURN:
                        break
                    co = {section: {str(mode_idx): weight}}
                    de = {"co_occurrence": co, "clarity": weight, "origin": "reflection"}
                    candidates.append((de, co, weight))
                    input_words_lower.add(word_label.lower())
                    n_reflection_candidates += 1

        # GL-CMD-VOICE-ORGANISM-CANDIDATES-195 P3 (c1 addition -- not in the
        # attached patch, added here to satisfy D2/X1's reporting need):
        # vote-spread visibility, the same blind spot -187 named for the
        # cognition meter. n_voted_words: distinct words the population
        # voted for at all. n_with_section_home: of the sampled top-K, how
        # many already have a committed section slot. n_candidates: final
        # count after also excluding self-echo.
        self._log_substrate_event("emission_diag",
                                  queries=queries[:12],
                                  n_queries_ok=n_queries_ok,
                                  n_voted_words=len(merged_votes),
                                  n_with_section_home=n_with_section_home,
                                  n_deep_candidates=n_deep_candidates,
                                  n_imagination_candidates=n_imagination_candidates,
                                  n_reflection_candidates=n_reflection_candidates,
                                  n_candidates=len(candidates))
        return candidates

    def _deep_atlas_neighbor_candidates(self, seed_word, exclude_words=None):
        """Real cross-modal association: walk deep_atlas.entries at
        seed_word's own chi, reading the co_occurrence invariant each
        deep entry there accumulated during real dream-cycle consolidation
        (deep_atlas.py's _update_invariant, weighted from the actual
        working-atlas chi neighborhood at promotion/reinforcement time --
        includes cross-modal sections like modal_sound/modal_touch/
        smell_*/touch_temperature wherever real sensory grounding landed
        near that word, not just language).

        Returns a list of (word_label, weight, section, mode_idx) -- self-
        echo and words already claimed by the caller excluded via
        exclude_words (lowercased). Honest empty if seed_word never
        survived to deep memory (deep_atlas write path is dream-cycle-only,
        gated by real reinforcement -- see DeepAtlas.dream_promotion_gate),
        or if everything found there is excluded.

        2026-07-08: gated on seed_word actually being known (a real
        committed section home, same index _brain_emission_candidates_
        legacy already trusts for this purpose) -- chi is a bounded,
        wrapping address (_CHI_ADDRESS_SPACE-class collision space, see
        _chi_to_neurons), so an ungated lookup returns a confident,
        real-looking association for words never taught at all
        ('zzznever' -> 'starts', 'xqrqz' -> 'starring', both measured
        directly). That's the exact >95%-false-confidence class b593603
        already found in the organism-recall version of this problem;
        checking real committed-word status first closes it here too."""
        if not seed_word or seed_word.lower() not in self._word_to_emission_sections:
            return []
        exclude = set(exclude_words or ())
        exclude.add(seed_word.lower())
        ek = LanguageKrimelack()
        ek.transduce(seed_word)
        chi = ek.winding
        out = []
        seen = set()
        for de in self.deep_atlas.entries.get(chi, []):
            entry_strength = de.get("strength", 0.0)
            if entry_strength <= 0.0:
                continue
            # GL-CMD-SLEEP-REORGANIZE follow-on (adversarial review,
            # 2026-07-10): this is the live conversational recall path --
            # a reorganize_hypothesis entry's single, never-confirmed link
            # would otherwise surface as a real spoken word candidate,
            # indistinguishable from a genuine dream-confirmed cross-modal
            # association. Reorganize is deliberately silent until
            # something real (dream_promotion_gate) confirms it.
            if de.get("source_path") == "reorganize_hypothesis":
                continue
            for section, motif_dict in de.get("co_occurrence", {}).items():
                sec_obj = self.sections.get(section)
                if sec_obj is None:
                    continue
                for mid_str, w in motif_dict.items():
                    mid = int(mid_str)
                    if mid >= len(sec_obj.modes):
                        continue
                    _, _, word_label = sec_obj.modes[mid]
                    if not word_label:
                        continue
                    wl = word_label.lower()
                    if wl in exclude or wl in seen:
                        continue
                    # 2026-07-09 credo fix: sec_obj.modes is the RAW mode
                    # list, ungated -- resolving a candidate word straight
                    # from it (as this always has) bypasses the grounded-
                    # speech filter entirely, since that filter lives in
                    # _word_to_emission_sections, not on modes itself. The
                    # seed_word check above only gates where the walk is
                    # allowed to START; every candidate WORD it surfaces
                    # needs the same real-grounding bar the seed word did.
                    if _require_grounded_speech() and wl not in self._word_to_emission_sections:
                        continue
                    seen.add(wl)
                    out.append((word_label, w * entry_strength, section, mid))
        return out

    def _imagination_candidates(self, seed_word, exclude_words=None):
        """GL-CMD-REFLECTION-EVE-20260710 (imagination half): surface
        tentative, never-yet-confirmed cross-domain links _dream_
        reorganize formed during sleep (source_path=="reorganize_
        hypothesis") as LOW-WEIGHT emission candidates -- structurally
        the same act as association (_deep_atlas_neighbor_candidates
        above), but over hypotheses instead of dream-confirmed memory.
        Both sides of every hypothesis are real, previously-experienced
        entries (see _dream_reorganize's own docstring) -- nothing here
        is invented content, only an honestly speculative RECOMBINATION
        of two real things she's actually experienced, never linked
        before.

        Deliberately excluded from _deep_atlas_neighbor_candidates
        (2026-07-10 adversarial review) because an unconfirmed guess
        must never be indistinguishable from real, dream-confirmed
        association in the SAME candidate pool at full weight. This is
        the narrow, opposite mechanism: hypotheses ONLY, explicitly
        tagged ("origin": "imagination" at the caller), and damped by
        IMAGINATION_WEIGHT_SCALE so a real candidate of equal raw
        strength always outweighs an imagined one -- a speculative
        thought competes for attention, it does not compete on equal
        footing with something she actually, confirmedly knows.

        Same real-grounding gate as the association path: only words she
        can already really speak are ever surfaced -- a hypothesis's
        chi-proximity guess is never allowed to unlock NEW vocabulary on
        its own (that's exactly what _backfill_grounded_from_deep_atlas's
        own hypothesis exclusion already guards, unchanged here)."""
        if not seed_word or seed_word.lower() not in self._word_to_emission_sections:
            return []
        exclude = set(exclude_words or ())
        exclude.add(seed_word.lower())
        ek = LanguageKrimelack()
        ek.transduce(seed_word)
        chi = ek.winding
        out = []
        seen = set()
        for de in self.deep_atlas.entries.get(chi, []):
            if de.get("source_path") != "reorganize_hypothesis":
                continue
            entry_strength = de.get("strength", 0.0)
            if entry_strength <= 0.0:
                continue
            for section, motif_dict in de.get("co_occurrence", {}).items():
                sec_obj = self.sections.get(section)
                if sec_obj is None:
                    continue
                for mid_str, w in motif_dict.items():
                    mid = int(mid_str)
                    if mid >= len(sec_obj.modes):
                        continue
                    _, _, word_label = sec_obj.modes[mid]
                    if not word_label:
                        continue
                    wl = word_label.lower()
                    if wl in exclude or wl in seen:
                        continue
                    if _require_grounded_speech() and wl not in self._word_to_emission_sections:
                        continue
                    seen.add(wl)
                    out.append((word_label, w * entry_strength * IMAGINATION_WEIGHT_SCALE,
                               section, mid))
        return out

    def _reflection_candidates(self, seed_word, exclude_words=None):
        """GL-CMD-REFLECTION-EMISSION-EVE-20260710: surface words that
        were genuinely co-present in a real remembered episode as
        LOW-WEIGHT emission candidates -- structurally the same act as
        _imagination_candidates above, but drawn from self._reflections
        (see _form_reflection's own docstring) instead of deep_atlas
        sleep-formed hypotheses. self._reflections' own "context_then"
        field traces back to _record_episodic_experience's "context"
        field, itself only ever populated from self._episodic_recent_
        concepts at the moment of a genuinely curated give_experience
        call (never plain corpus reading) -- so every word this can
        possibly surface is a real thing she really experienced
        alongside the concept she's reflecting on, nothing invented.

        Deliberately a separate, narrower mechanism from
        _imagination_candidates: reflection has no per-word
        co_occurrence weight the way a deep_atlas hypothesis entry does
        (reflections are never written to deep_atlas at all), so every
        candidate word from a single matched reflection shares one
        fixed, deliberately low REFLECTION_BASE_STRENGTH, damped
        further by REFLECTION_EMISSION_WEIGHT_SCALE -- same role as
        IMAGINATION_WEIGHT_SCALE, so a real candidate of equal raw
        strength from any other source always outweighs a remembered
        one.

        Same real-grounding gate as every other candidate source: only
        words she can already really speak are surfaced. Unlike
        _imagination_candidates / _deep_atlas_neighbor_candidates (which
        walk deep_atlas's own ungated sec_obj.modes and must separately
        check _require_grounded_speech()), every candidate word here is
        resolved directly through self._word_to_emission_sections, which
        is itself already built under that same gate (see its own
        rebuild-time filtering) -- so a direct lookup already IS the
        gate, no second check needed.

        Reads self._reflections newest-first (a deque, so this is a
        simple reversed() walk) and stops at the first reflection whose
        concept matches seed_word, mirroring _record_episodic_
        experience's own "never merge distinct stories" principle --
        a fresher reflection about the same concept is used whole,
        never blended with an older one still sitting in the bounded
        history.

        2026-07-10 adversarial review note: every entry in
        self._reflections is written only by _form_reflection's own
        controlled dict literal (all fields always present) and this
        deque is never persisted/restored across a process restart (see
        its own __init__ comment) -- so a malformed/legacy entry is not
        reachable through any live path today. The isinstance()/.get()/
        `or` defensive accessors below are kept anyway as cheap
        insurance against a future writer changing that, matching this
        codebase's established convention (same style _form_reflection
        itself uses for its own, genuinely-restorable episodic-memory
        inputs) -- 2026-07-10 adversarial review caught and this fixes a
        real crash here: a non-string entry inside context_then (e.g. a
        stray int) reached word_label.lower() unguarded and raised
        AttributeError, which would have propagated out of
        _brain_emission_candidates_legacy uncaught (no try/except
        wraps that call site, same as its sibling _imagination_
        candidates/_deep_atlas_neighbor_candidates calls) -- a single
        malformed context_then entry would have broken emission
        candidate gathering for the whole turn."""
        if not seed_word or seed_word.lower() not in self._word_to_emission_sections:
            return []
        exclude = set(exclude_words or ())
        exclude.add(seed_word.lower())
        seed_lower = seed_word.lower()
        out = []
        seen = set()
        for reflection in reversed(self._reflections):
            concept = reflection.get("concept")
            if not concept or not isinstance(concept, str) or concept.lower() != seed_lower:
                continue
            context_then = reflection.get("context_then") or []
            for word_label in context_then:
                if not word_label or not isinstance(word_label, str):
                    continue
                wl = word_label.lower()
                if wl in exclude or wl in seen:
                    continue
                locations = self._word_to_emission_sections.get(wl)
                if not locations:
                    continue  # real-committed-section-home gate
                section, mode_idx, matched_word = self._best_fit_location(locations)
                seen.add(wl)
                out.append((matched_word or word_label,
                            REFLECTION_BASE_STRENGTH * REFLECTION_EMISSION_WEIGHT_SCALE,
                            section, mode_idx))
            break  # only the single freshest matching reflection
        return out

    def _committed_emission_response(self, settlement):
        """Return source-certified speech or deterministic neutral silence.

        Language Fact-Strand reciprocity remains the PREFERRED authority and
        its certification is untouched.  Joe's ruling 2026-07-16 (war-room
        GL emission synthesis): the substrate's own assemblage settlement is
        re-admitted as a release authority when it carries a real dynamics
        commit — a partial, explicit reversal of 8835cfc's sole-authority
        clause, which had muted every voice path since 2026-07-13 while the
        assemblage verifiably kept committing real NMDA-gated words (the
        discarded 'dog' commit, event seq 18739-18746).  Released assemblage
        speech carries its own distinct label so every reply stays auditable
        by authority; a reply is labeled fact_strand_commit ONLY when the
        certifier passed.
        """
        if self._fact_settlement_has_certified_provenance(settlement):
            return settlement.content, "fact_strand_commit"
        if (isinstance(settlement, EmissionSettlement)
                and settlement.n_commits >= 1
                and settlement.content
                and len(settlement.commit_provenance) == settlement.n_commits
                and all(isinstance(item, EmissionCandidateProvenance)
                        for item in settlement.commit_provenance)
                and " ".join(item.word for item in settlement.commit_provenance)
                == settlement.content):
            return settlement.content, "assemblage_commit"
        return "", "silence_no_commit"

    def _fact_record_has_certified_provenance(self, record):
        """Rehydrate a stored Fact settlement and run the live verifier."""
        if (not isinstance(record, dict)
                or record.get("response_source") != "fact_strand_commit"):
            return False
        try:
            items = []
            for raw in record.get("commit_provenance") or []:
                if raw.get("authority") != "language_fact_strand_reciprocity_v1":
                    return False
                supports = tuple(FactEmissionSupport(
                    window_id=support["window_id"],
                    entry_index=support["entry_index"],
                    experience_origin=support["experience_origin"],
                    source_tag=support["source_tag"],
                    trace_id=support["trace_id"],
                    source_strand_id=support["source_strand_id"],
                    modalities=tuple(support["modalities"]),
                ) for support in raw["supports"])
                items.append(FactEmissionTokenProvenance(
                    word=raw["word"],
                    structural_fingerprint=raw["structural_fingerprint"],
                    recognized_strand_ids=tuple(raw["recognized_strand_ids"]),
                    supports=supports,
                ))
            settlement = EmissionSettlement(
                content=record.get("text", ""),
                committed_sections=tuple(record.get("committed_sections") or ()),
                n_commits=record.get("n_commits", 0),
                organ_in_commits=False,
                tick=record.get("tick", 0),
                commit_provenance=tuple(items),
            )
        except (KeyError, TypeError, ValueError):
            return False
        return self._fact_settlement_has_certified_provenance(settlement)

    def _certified_emission_record(self, emission_id):
        """Return a feedback-safe emission record, or None.

        Records written before response-source provenance was introduced
        cannot distinguish a genuine commit from the retired fallback.  They
        remain persisted as history but are deliberately ineligible for new
        reinforcement; guessing would risk strengthening fabricated speech.
        """
        if not emission_id:
            return None
        record = self._emission_records.get(emission_id)
        if not self._fact_record_has_certified_provenance(record):
            return None
        return record

    def _try_acquire_autonomous_emission(self):
        """Enter emission only when no conversation was counted first.

        The state lock makes the pending-turn check and nonblocking RLock
        acquisition one ordering decision.  Autonomous callers that already
        hold ``self.lock`` must never wait for the emission lock because a
        phased conversation can hold that lock before taking ``self.lock``.
        """
        with self._live_converse_state_lock:
            if self._live_converse_pending > 0:
                return False
            return self._emission_lock.acquire(blocking=False)

    def _emit_from_invariants(self, input_chis, input_words, mode_override=None,
                              v7_session=None, organ_candidates=None):
        """Settle organism candidates and return committed content only.

        The former ``topk`` and scalar-grandurun branches returned ranked
        candidates without a dynamics commit.  They remain available as
        diagnostic functions but are retired as voice paths.  Production
        speech now has one source: assemblage dynamics with a real commit.
        """
        with self._emission_lock:
            mode = mode_override or os.environ.get("EMISSION_MODE", "topk")
            if (os.environ.get("EMISSION_DYNAMICS", "0") != "1"
                    or mode != "grandurun"):
                return EmissionSettlement(tick=self.tick)

            input_words_set = set(w.lower() for w in input_words)
            deep_candidates = self._brain_emission_candidates(input_words)
            if not deep_candidates:
                return EmissionSettlement(tick=self.tick)

            return self._emit_dynamics(
                input_chis, input_words_set, deep_candidates,
                v7_session=v7_session, input_words=input_words)

    # Phase 3b constants — context prior weights
    INTRO_RECENCY_BOOST = 2.0
    ACTIVITY_BOOST = 1.5
    AWARE_BLOCKED_ATTENUATION = 0.5
    PRIOR_WEIGHT_CAP = 5.0
    CONTEXT_WINDOW_COMMITS = 10
    CONTEXT_WINDOW_TICKS = 50
    # GL-CMD-V7-AWARENESS-REAL-PATH-C1-20260711: bounded tail scanned by
    # _introspection_active_this_turn/_introspection_recent_words below.
    # self.sections["intro"].commits is allowed to grow to SECTION_COMMITS_
    # MAX (5000) over the organism's life -- this keeps both real-signal
    # lookups O(200) regardless, same "generous headroom, real bound"
    # convention as SUFFERING_LOG_MAX/ATTENTIONS_MAX elsewhere in this file.
    INTROSPECTION_SCAN_TAIL = 200

    def _introspection_active_this_turn(self):
        """Real, grounded replacement for the retired v7_session.aware_
        recently_fired(within_ticks=25) gate. GL-CMD-V7-AWARENESS-REAL-
        PATH-C1-20260711.

        True iff the organism's OWN real "intro" (introspection) section
        actually committed -- Section.receive() -> self.commits.append(),
        see ~line 1408 -- while THIS turn's real input words were being
        read. Reads self._last_converse_tick (stamped at the very top of
        both _converse_body and _converse_phased, before read_sentence()
        runs -- see those methods) against self.sections["intro"].commits
        (the same real, bounded, persistent commit list read_word() has
        always populated for every real conversational turn, independent
        of this change). This reuses the exact tick_before_read/tick_
        after_read "did X happen during THIS turn" boundary _converse_
        body's own response-binding tagging already relies on (see the
        v8 FIX 1 block there) instead of inventing a new recency-window
        constant with no empirical basis.

        Never constructs, attaches, or calls anything on a V7Session
        (substrate/v7_engine.py) -- that object is a fully separate,
        isolated toy substrate reachable only via the /v7/* endpoints,
        and its own aware/intro gates only ever reflect ITS OWN separate
        simulated conversation (populated by V7Session.converse(), which
        the real conversation path must never call)."""
        sec = self.sections.get("intro")
        if not sec or not sec.commits:
            return False
        since_tick = getattr(self, "_last_converse_tick", None)
        if since_tick is None:
            return False
        return any(c.get("tick", 0) > since_tick
                   for c in sec.commits[-self.INTROSPECTION_SCAN_TAIL:])

    def _introspection_recent_words(self, max_n=10, max_ticks=50):
        """Real, grounded replacement for the retired v7_session.
        get_recent_words(). Returns the set of words the organism's own
        real "intro" section actually committed recently -- read directly
        from self.sections["intro"].commits (real {tick, mode, chi, word,
        grounded} entries, see Section.receive() ~line 1408), never from a
        separate/simulated session. See _introspection_active_this_turn
        for why this is safe and grounded."""
        sec = self.sections.get("intro")
        if not sec or not sec.commits:
            return set()
        tail = sec.commits[-self.INTROSPECTION_SCAN_TAIL:]
        tick = self.tick
        by_count = {c["word"].lower() for c in tail[-max_n:] if c.get("word")}
        by_tick = {c["word"].lower() for c in tail
                   if c.get("word") and tick - c.get("tick", 0) <= max_ticks}
        return by_count | by_tick

    def _build_context_priors(self, v7_session=None):
        """GL-CMD-FOUNDATIONS Phase 3b: context priors from substrate state.
        Returns {word: prior_weight}. Pure substrate geometry — no ML.

        GL-CMD-V7-AWARENESS-REAL-PATH-C1-20260711: Source 1 now reads the
        organism's own real introspection history directly (see
        _introspection_recent_words) instead of v7_session.get_recent_
        words(). v7_session (a fully separate, isolated simulated
        substrate -- see substrate/v7_engine.py:V7Session) is never
        constructed, attached, or read on this path any more. Kept as an
        accepted, now-unused parameter (same convention as
        organ_candidates on _emit_from_invariants above) purely so
        existing call sites that still thread it through don't need to
        change."""
        priors = {}

        # Source 1: organism's own real introspection-section recent words
        recent = self._introspection_recent_words(
            max_n=self.CONTEXT_WINDOW_COMMITS,
            max_ticks=self.CONTEXT_WINDOW_TICKS)
        for word in recent:
            priors[word] = priors.get(word, 1.0) * self.INTRO_RECENCY_BOOST

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
        If no cache (cold start), return empty dict.

        GL-CMD-V7-AWARENESS-REAL-PATH-C1-20260711: aware_active now reads
        the organism's OWN real state (_introspection_active_this_turn)
        instead of v7_session.aware_recently_fired() -- v7_session was
        never populated on this path in production anyway (_v7_session is
        only ever assigned by the isolated /v7/* endpoint handlers, see
        substrate_runner.py:_ensure_v7_link), so this gate was previously
        permanently dead. v7_session kept as an accepted, unused
        parameter -- see _build_context_priors docstring."""
        aware_active = self._introspection_active_this_turn()

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
    # GL-CMD-NO-CAPS-COHERENCE-SPEAKS-EVE-20260705-203 U2 (real live mechanism,
    # follow-on to the dispatch's named dead-code targets): extended from
    # (subject, verb, object) to include modifier/ground/intro too -- these
    # three sections were never even CONSTRUCTED in the assemblage-dynamics
    # system (_build_emission_system below just loops over this tuple), so
    # her live speech was structurally capped at 3 words -- one per section
    # -- regardless of every other cap already removed. This tuple ALSO
    # gates whether read_word's _word_to_emission_sections reverse index
    # (used by _brain_emission_candidates and _compose_from_cortex) records
    # a commit at all (see read_word's "primary_section in self.
    # _EMISSION_SECTIONS" check) -- so extending it here is what makes the
    # GL-BUG-GROUND-INTRO-UNREACHABLE fix (ROLE_DNA + _choose_role_sections)
    # visible anywhere downstream; neither fix does anything alone.
    # "listen" stays separate/excluded on purpose (unchanged): it's her
    # input-echo channel (zeroed-Hamiltonian, driven only by what she just
    # heard), not an output channel -- same distinction the code already
    # drew for it everywhere else in this function.
    _EMISSION_SECTIONS = ("subject", "verb", "object", "modifier", "ground", "intro")

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
        # 2026-07-10 GL-CMD-KEYHOLE-EXTENSION: object → modifier → ground →
        # intro, continuing the exact same designed cascade in
        # _EMISSION_SECTIONS' own declared order, same wide chi band and
        # goal_strength as the two links above -- no new topology theory,
        # no new tuning, just carrying the already-proven pattern to the
        # three sections that were deliberately left unwired in the
        # earlier, more conservative pass (see this file's own prior
        # comment, preserved below). Per this session's research into
        # completing the AE-Substrate blueprint (Dell 1986 interactive
        # activation; Houghton 1990/Bullock & Rhodes 2003 competitive
        # queuing), a designed excitatory chain across ALL grammar slots,
        # not just the first two, is what actually produces graded,
        # ordered multi-slot output instead of three slots settling
        # independently with no relation to what came before them.
        sys_.add_keyhole("object", -50, 50, "modifier", goal_strength=0.4)
        sys_.add_keyhole("modifier", -50, 50, "ground", goal_strength=0.4)
        sys_.add_keyhole("ground", -50, 50, "intro", goal_strength=0.4)
        # Prior conservative-pass rationale, preserved: modifier/ground/
        # intro previously got NO keyhole wiring at all, settling
        # independently from their own candidate-driven psi drive
        # (section_drives below), same as "listen" already does, rather
        # than guessing a cascade topology for them against code with a
        # documented history of settling regressions (H_base oscillation,
        # socket timeouts). That caution is still the reason this
        # extension reuses the identical wide band/goal_strength already
        # proven safe on subject→verb→object, rather than inventing new
        # parameters for the extension.

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
                        "arousal": e.get("arousal", 0.5),
                        "valence": _e_val,
                        "surprise": e.get("surprise", 0.0),
                        "polarity": e.get("polarity", 1.0),
                        # GL-CMD-SCENE-LANES-B1-188 V4: reader -- these were
                        # write-only on the atlas entry (-164's audit finding)
                        # until recall actually surfaced them here.
                        "presence": e.get("presence"),
                        "location": e.get("location"),
                        "place": e.get("place"),
                        "ambient": e.get("ambient"),
                        "origin": "cross_modal",
                        "_provenance_evidence":
                            _candidate_provenance_evidence(
                                e, origin="cross_modal"),
                        **({"source": e["source"]}
                           if "source" in e else {}),
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
                            "arousal": de.get("arousal", 0.5),
                            "valence": _de_val,
                            "surprise": de.get("surprise", 0.0),
                            "polarity": de.get("polarity", 1.0),
                            "presence": de.get("presence"),
                            "location": de.get("location"),
                            "place": de.get("place"),
                            "ambient": de.get("ambient"),
                            "origin": "cross_modal_deep",
                            "_provenance_evidence":
                                _candidate_provenance_evidence(
                                    de, origin="cross_modal_deep"),
                            **({"source": de["source"]}
                               if "source" in de else {}),
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
                        "arousal": e_aro,
                        "valence": e_val,
                        "surprise": e.get("surprise", 0.0),
                        "polarity": e.get("polarity", 1.0),
                        "presence": e.get("presence"),
                        "location": e.get("location"),
                        "place": e.get("place"),
                        "ambient": e.get("ambient"),
                        "origin": "cofire_spread",
                        "_provenance_evidence":
                            _candidate_provenance_evidence(
                                e, origin="cofire_spread"),
                        **({"source": e["source"]}
                           if "source" in e else {}),
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
                        rerouted_evidence = dict(
                            cand.get("_provenance_evidence", {}))
                        rerouted_evidence["origin"] = "emission_reroute"
                        routed.append({
                            **cand,
                            "section": es,
                            "motif": mi,
                            "word": w,
                            "origin": "emission_reroute",
                            "_provenance_evidence": rerouted_evidence,
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
        return all_candidates[:RICH_SENSORY_TOPK]

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
            return EmissionSettlement(tick=self.tick)

        # GL-CMD-V7-AWARENESS-REAL-PATH-C1-20260711: real introspection-
        # derived bias, same shape as the gp-bias reweight above but
        # sourced from the organism's own real "intro" section state (see
        # _get_emission_priors / _introspection_active_this_turn) rather
        # than a synthetic/session signal. Applied ONCE here, before the
        # per-tick settling loop below -- a single O(len(candidates))
        # reweight, not a per-tick cost, so it cannot affect the wall-
        # clock settling budget (_WALL_BUDGET_S) that loop is already
        # bounded by. Never constructs or touches V7Session.
        _aware_priors = self._get_emission_priors(v7_session)
        if _aware_priors:
            for _c in candidates:
                _prior = _aware_priors.get((_c.get("word") or "").lower())
                if _prior:
                    _c["coherent_magnitude"] = _c["coherent_magnitude"] * _prior
            candidates.sort(key=lambda c: -c["coherent_magnitude"])

        # Build/get emission system
        sys_ = self._build_emission_system()

        # Determine input source for NMDA context
        input_source = getattr(self, "_last_converse_source", "corpus") or "corpus"

        # Install candidate modes and compute per-section drive biases
        section_drives = {s: np.zeros(N, dtype=complex) for s in self._EMISSION_SECTIONS}
        listen_drive = np.zeros(N, dtype=complex)
        installed_candidate_provenance = {}

        for cand in candidates:
            sec_name = cand["section"]
            if sec_name not in sys_.sections or sec_name not in self._EMISSION_SECTIONS:
                continue

            mode_idx = self._ensure_emission_mode(
                sys_, sec_name, cand["motif"], cand["word"])

            if mode_idx is None:
                continue  # section at mode cap; candidate still counted but not installed

            provenance = _freeze_candidate_provenance(
                cand, sec_name, mode_idx)
            installed_candidate_provenance.setdefault(
                (sec_name, mode_idx), []).append(provenance)

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
            c.get("source") in ("joe", "joe_voice", "wc", "c1")
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
        # The wall-clock budget bounds a degenerate settlement.  Reaching the
        # deadline without a commit produces neutral silence, never a ranked
        # candidate presented as if the field had settled.
        # GL-FIX-CONVERSE-LATENCY: reduce from 5s → 1.5s so /converse Phase 6
        # (_emission_lock) + autonomy emission (_emission_lock) combined stay under 3s.
        #
        # GL-FIX-EMISSION-BUDGET-RETIME-20260710: 1.5s -> 3.0s. 2026-07-10's
        # keyhole wiring extension (2d83ca4) added excitatory handoffs
        # object->modifier->ground->intro on top of the existing
        # subject->verb->object chain, without raising this budget -- root-
        # caused live (GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1
        # #3) to real conversation windows closing on quiet_timeout with zero
        # commits. A straight revert of 2d83ca4 was built and measured
        # against a real harness at this budget and produced a NET
        # REGRESSION (silence 25% -> 50%) -- correctly declined, not repeated
        # here; the extra excitatory edges only ever LOWER downstream commit
        # thresholds, they help.
        #
        # This is a re-time, not a guess: 2d83ca4 added handoffs, not
        # per-tick compute -- all six _EMISSION_SECTIONS + listen were
        # already built and evolved every tick since 2026-07-05's
        # GL-CMD-NO-CAPS-COHERENCE-SPEAKS-203, so a naive "3x the handoffs ->
        # 2.5x the budget" scaling would be measuring the wrong thing. Real
        # live per-tick cost (GL-RPT-EMISSION-COST-C1-20260702-87-v2, median
        # 2.175ms/tick, p95 2.228ms/tick, same zeroed-H_base/no-inhibition
        # config still deployed today) puts a full 80-tick run at ~178ms of
        # pure compute -- an 8.4x margin under the old 1.5s already. A local
        # harness reproduced that same per-tick cost. The deadline being hit
        # in production despite that margin is best explained by real
        # GIL/thread contention inflating wall-clock cost per tick under
        # load (this session's own broader findings: tick_rate collapse,
        # severe lock contention elsewhere in the same process) -- not by
        # 2d83ca4 making the settling loop itself more expensive to compute.
        # 3.0s gives real headroom against that contention while landing
        # exactly on the ceiling this constant's OWN prior comment already
        # established as safe ("combined stay under 3s"); it does not
        # override that design intent, it uses the rest of the budget that
        # intent always allowed. _emission_lock's other caller (autonomous
        # emission, below) acquires non-blocking specifically so it never
        # stacks with /converse's blocking use, so this budget's only real
        # cost is /converse's own Phase 6 -- a small, bounded addition
        # against a real total turn time (~50-55s, per the same root-cause
        # doc) dominated by other locks, not this one.
        _WALL_BUDGET_S = float(os.environ.get("EMISSION_WALL_BUDGET_S", "3.0"))
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
                break
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
            # GL-CMD-NO-CAPS-COHERENCE-SPEAKS-203: the len(emit_commits) >= 20
            # early-break is deleted -- a second, arbitrary numeric ceiling
            # the real safety net (the wall-clock deadline check at the top
            # of this loop) already makes redundant. With more sections now
            # competing for commits (_EMISSION_SECTIONS above), a fixed
            # commit-count cap would unfairly starve later-settling
            # sections of their turn within the same tick budget -- the
            # settle-or-timeout rule, not an arbitrary count, is the only
            # terminator now.

        stage2_ms = (_time.monotonic() - t1) * 1000

        # Read only modes that genuinely committed during this settlement.
        emission_words = []
        selected_commits = []
        per_section_dominant = {}
        committed_sections = []
        for sec_name in self._EMISSION_SECTIONS:
            # Check if this section had a committed mode during dynamics
            committed_word = None
            committed_mode = None
            for c in reversed(emit_commits):
                if c["section"] == sec_name:
                    w = self._emission_word_map.get((sec_name, c["mode_id"]))
                    if w:
                        committed_mode = c["mode_id"]
                        committed_word = w
                        break

            if committed_word:
                per_section_dominant[sec_name] = (committed_mode, committed_word, "commit")
                if (committed_word.lower() not in input_words_set
                        and committed_word not in emission_words):
                    emission_words.append(committed_word)
                    committed_sections.append(sec_name)
                    selected_commits.append({
                        "section": sec_name,
                        "mode_id": committed_mode,
                        "word": committed_word,
                    })
            else:
                per_section_dominant[sec_name] = (None, None, "none")

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
            orig = c.get("origin")
            if orig is not None:
                origin_counts[orig] = origin_counts.get(orig, 0) + 1
            src = c.get("source")
            if src is not None:
                source_counts[src] = source_counts.get(src, 0) + 1

        commit_provenance = _committed_candidate_provenance(
            selected_commits, installed_candidate_provenance)
        organ_in_commits = any(
            provenance.origin == "organ"
            for provenance in commit_provenance)
        commit_provenance_records = [
            provenance.as_record() for provenance in commit_provenance]

        self._log_substrate_event("emission_dynamics",
                                  content=emission_text,
                                  n_candidates=len(candidates),
                                  n_commits=len(selected_commits),
                                  dynamics_commits=len(emit_commits),
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
                                  organ_in_commits=organ_in_commits,
                                  commit_provenance=commit_provenance_records,
                                  gp_bias_applied=_gp_bias_applied,
                                  aware_priors_applied=bool(_aware_priors),
                                  n_aware_priors=len(_aware_priors))
        # Store the settlement truth consumed by every speech interface.
        settlement = EmissionSettlement(
            content=emission_text,
            committed_sections=tuple(committed_sections),
            n_commits=len(selected_commits),
            organ_in_commits=organ_in_commits,
            tick=self.tick,
            commit_provenance=commit_provenance)
        self._last_dynamics_result = {
            "content": emission_text,
            "committed_sections": list(committed_sections),
            "n_commits": len(selected_commits),
            "dynamics_commits": len(emit_commits),
            "organ_in_commits": settlement.organ_in_commits,
            "commit_provenance": commit_provenance_records,
            "tick": self.tick,
        }
        return settlement

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
        # GL-CMD-NO-CAPS-COHERENCE-SPEAKS-EVE-20260705-203 U2: extended from
        # ["subject", "verb", "object"] to her full section set -- modifier/
        # ground/intro/listen words can take structural positions too.
        # Order comes from her own co-occurrence record (the scan below),
        # length from her own coherence physics (U0/U1) -- no new grammar,
        # no templates, no constants (reuses the existing SECTION_NAMES).
        SVO_ORDER = list(self.SECTION_NAMES)

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
            # GL-CMD-NO-CAPS-COHERENCE-SPEAKS-EVE-20260705-203 U1: the
            # orderer orders, never truncates -- ALL remaining selected
            # words follow the anchor, in their own coherence-selection
            # order, not just the first two.
            return best_triple + remaining

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
        # GL-CMD-ORGANISM-WAVE-MEMORY-207 W3: no lock -- see
        # _recognition_from_organism's matching comment.
        votes = self.organism.recall_fast(_organism_signal(query, self._organism_transducer))
        top = votes.most_common(1)
        return top[0][0] if top else None

    def _recall_from_organism_auditory(self, sound_signal):
        """GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-208: cross-sense
        recall -- the organism's best-voted concept from a real sound
        waveform ALONE, no word. Mirrors _recall_from_organism's
        contract (top vote or None) but deliberately uses
        Embryo.recall(), not recall_fast(): recall_fast's proven scope
        is language/tactile/olfactory/gustatory only (brain.py
        docstring) and raises NotImplementedError for a live
        visual/auditory signal -- recall() is the general, always-
        correct (if slower) path, and correctness matters far more than
        speed for a once-per-cue verification query, not a hot
        converse-turn path."""
        if sound_signal is None:
            return None
        with self._organism_lock:
            votes = self.organism.recall(_organism_query_signal_auditory(sound_signal))
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
        # GL-CMD-ORGANISM-WAVE-MEMORY-207 W3: no lock -- see
        # _recognition_from_organism's matching comment.
        votes = self.organism.recall_fast(_organism_signal(seed_word, self._organism_transducer))
        total = sum(votes.values())
        weight = (votes.get(associated_word, 0) / total) if total else 0.0
        return (section, mode_idx, word, weight)

    def _association_from_deep_atlas(self, seed_word):
        """2026-07-08: real near-association via deep_atlas's own
        co_occurrence invariant (_deep_atlas_neighbor_candidates), restoring
        the mechanism _association_from_organism replaced (per that
        method's own docstring: "replacing _daydream_tick's
        deep_atlas.entries[chi].co_occurrence walk"). That replacement's
        own commit message reported it surfaced a false-confidence finding
        in organism recall; this session found the sharper version of the
        same problem -- recall_exact_or_best now makes recall_fast a pure
        identity function for taught words, so _association_from_organism's
        self-echo guard fires on every call, permanently. deep_atlas's
        co_occurrence measures what else co-occurred near this word during
        real dream-cycle consolidation (cross-modal: modal_sound/
        modal_touch/smell_*/touch_temperature sections included wherever
        real sensory grounding landed there), which is a different
        question than identity and can't collapse the same way.

        Returns (section, mode_idx, word, weight), or None if seed_word
        hasn't yet survived to deep memory or nothing there clears the
        self-echo/known-section-home filters."""
        neighbors = self._deep_atlas_neighbor_candidates(seed_word)
        if not neighbors:
            return None
        word_label, weight, section, mode_idx = max(neighbors, key=lambda n: n[1])
        return (section, mode_idx, word_label, weight)

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

        target_sections is retained for diagnostic replay selection but is no
        longer consulted by the organism.  Returns the text recall and an
        immutable picture-recall snapshot from this exact call; callers never
        read the shared last-picture diagnostic to construct a response."""
        recalled_text = self._recall_from_organism(input_words)

        # v7 Phase 2: recall sight motifs via chi-neighborhood (unchanged)
        recalled_pictures = self._recall_sight_from_atlas(input_chis, input_words)

        if not recalled_text and not recalled_pictures:
            self._last_recalled_pictures = []  # GL-CMD-155: don't leak a stale hit
            return None, ()

        if recalled_pictures:
            self._last_recalled_pictures = recalled_pictures
            return recalled_text, tuple(recalled_pictures)
        self._last_recalled_pictures = []
        return recalled_text, ()

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
    @_engine_mutation_entry
    def start_continuous_reading(self, corpus_lines, interval=0.02):
        current = getattr(self, "_reading_thread", None)
        if current is not None and current.is_alive():
            return

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
                self._start_engine_background_thread(
                    lambda: self.log_event("state", _ek, **_det),
                    daemon=True, name=f"ev-log-{event_kind[:8]}")
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

    @_engine_mutation_entry
    def start_daydream_loop(self):
        """Parallel chi-neighborhood walk. Runs alongside all foreground activity.
        Does NOT trigger commit gate or emission. 0.5s interval (2 Hz)."""
        current = getattr(self, '_daydream_thread', None)
        if current is not None and current.is_alive():
            return
        self._daydream_running = True

        def _loop():
            while self._daydream_running:
                try:
                    with self._engine_mutation_scope("daydream_tick"):
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

        # ── Phase 2: association query + novel-jump (no lock) ────────────────
        # 2026-07-08: deep_atlas's real co_occurrence walk preferred over
        # the organism-vote proxy -- see _association_from_deep_atlas's
        # docstring. Organism-vote kept as fallback for a seed_word that
        # hasn't yet survived to deep memory (new/rarely-reinforced words).
        assoc = self._association_from_deep_atlas(seed_word)
        if assoc is None:
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
                    # GL-CMD-SLEEP-REORGANIZE follow-on (adversarial review,
                    # 2026-07-10): without this, a reorganize hypothesis's
                    # single, never-confirmed co_occurrence link could
                    # surface here as a "far_word" novel-jump discovery --
                    # written into the real working atlas AND logged as a
                    # daydream_novel event, indistinguishable from a
                    # genuine, organism-earned association. Reorganize's
                    # own honest-low-confidence design is defeated if a
                    # different mechanism launders it into a real-looking
                    # "discovery" the moment it's created.
                    if de.get("source_path") == "reorganize_hypothesis":
                        continue
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

    @_engine_mutation_entry
    def add_corpus(self, corpus_id, title, lines):
        """Register a corpus for autonomous reading."""
        self._corpora[corpus_id] = _Corpus(
            corpus_id=corpus_id, title=title, lines=lines)

    def _has_pending_cognitive_work(self):
        """GL-CMD-COGNITION-AT-SPEED-EVE-20260705-205 C1: reads EXISTING
        state only (no new constants) to answer one question -- is there
        real work waiting right now? Open response windows, an active
        (non-idle, non-sleeping) activity, a non-empty organism/tapestry
        worker queue, or elevated arousal all say yes. This does not slow
        anything down when false (see start_autonomy_loop) -- it exists so
        tick_rate telemetry (C5) can report WHY she's ticking at whatever
        rate she's ticking at, not to gate speed on it."""
        if self.open_response_windows:
            return True
        _kind = getattr(self._current_activity, 'kind', None)
        if _kind is not None and _kind not in ("IDLE", "SLEEPING"):
            return True
        if self._organism_queue is not None and not self._organism_queue.empty():
            return True
        if self._tapestry_queue is not None and not self._tapestry_queue.empty():
            return True
        if self.needs.arousal() > 0.5:  # existing needs midpoint, not a new tunable
            return True
        return False

    # GL-CMD-COGNITION-AT-SPEED-EVE-20260705-205 C1: measured, not guessed
    # (first build here tried literal time.sleep(0) -- "brief OS yield,
    # nothing more" -- and it regressed real converse() latency: mean
    # ~665ms with no autonomy loop running at all, vs ~1105ms once the
    # loop ran flat-out with sleep(0), an 8-way A/B sweep of yield values
    # (0/0.0005/0.001/0.002/0.003/0.004/0.005/0.01/0.02) showed converse()
    # latency tracks its own ~665ms unrelated baseline at any yield
    # >=0.001s, but degrades sharply below that -- Python's threading.Lock
    # is not FIFO-fair, so a thread re-acquiring it near-instantly after
    # release can starve a different thread waiting on the same lock
    # (converse's own brief lock phases). 0.001s is the smallest value
    # that measured clean in that sweep (312.9 ticks/sec, 687.6ms mean
    # converse latency -- within noise of the no-loop baseline). This is
    # a measured technical requirement of sharing one non-fair lock
    # across threads, not a cognitive pacing cap: the deeper fix (a fair
    # lock, or the fuller interpreter-isolation C4 scopes) is named, not
    # smuggled past, in this window's report.
    #
    # INCIDENT, 2026-07-05: 0.001s (the value the local A/B sweep above
    # measured clean) caused a real live stall in production minutes
    # after deploy -- tick_rate collapsed to ~0.3/sec and a live
    # converse() call sat "settling" 24s+ with no sign of returning.
    # Rolled back immediately. Root cause NOT fully isolated: a 15-
    # thread concurrent-converse local repro at 0.001s did NOT reproduce
    # it, meaning the actual trigger needs the OTHER real background
    # threads production has and this repro didn't (organism-writer,
    # tapestry-writer, curriculum feeder, frame processing, self-voice)
    # -- self.lock is acquired from more places than converse() and the
    # autonomy loop alone. Raised to 0.02s: a deliberately conservative
    # safety margin chosen AFTER a live incident, not a guess -- still a
    # measured ~15-25x floor over the original 0.2s (so "compute follows
    # need" still holds far more than before), while leaving much more
    # headroom against contention this session couldn't fully
    # characterize with the tools available tonight. Tightening this
    # further needs real production thread-dump/profiling instrumentation,
    # not another guess-and-redeploy cycle -- named as its own follow-up,
    # not silently dropped.
    _AUTONOMY_YIELD_SEC = 0.02

    @_engine_mutation_entry
    def start_autonomy_loop(self, interval=None):
        """GL-CMD-COGNITION-AT-SPEED-EVE-20260705-205 C1: COMPUTE FOLLOWS
        NEED (Joe's ruling). The fixed interval=0.05s/0.2s sleep here was
        the single largest gap between measured capability (625 ticks/sec
        possible, single thread, per Eve's cProfile) and measured reality
        (~3/sec) -- a hardcoded nap on top of a 1.6ms thought. Deleted.
        The loop now ticks continuously, yielding _AUTONOMY_YIELD_SEC
        between ticks regardless of busy/idle state (see that constant's
        own comment for why this exists and how its value was measured,
        not guessed) -- delivering hundreds of ticks/sec either way.
        _has_pending_cognitive_work exists for telemetry (tick_rate
        reporting), not for gating -- speed is never conditioned on it.
        `interval` kwarg accepted for backward compatibility with
        existing callers (app.py, substrate_runner.py) -- ignored; a
        deprecation note, not a new pacing knob."""
        current = getattr(self, "_reading_thread", None)
        if current is not None and current.is_alive():
            return

        def loop():
            _window_start = time.monotonic()
            _window_ticks = 0
            self._tick_rate_ref_tick = self.tick
            self._tick_rate_ref_time = _window_start
            while not self._reading_stop.is_set():
                try:
                    with self._engine_mutation_scope("autonomy_tick"):
                        self._autonomy_tick()
                except Exception as e:
                    print(f"[GualaLoom] Autonomy tick error: {e}")
                _window_ticks += 1
                _now = time.monotonic()
                _elapsed = _now - _window_start
                if _elapsed >= 1.0:
                    # GL-RPT-COGNITION-AT-SPEED root-cause fix: this
                    # reference (tick, time) pair is refreshed here, but
                    # get_tick_rate() below recomputes the RATE at read
                    # time using the CURRENT clock -- not this precomputed
                    # ratio. A precomputed self._tick_rate froze at its
                    # last-good value exactly when the loop got stuck
                    # inside one long _autonomy_tick() call (a 49s-94s
                    # emission), showing a normal-looking rate during the
                    # live incident instead of an honest one.
                    self._tick_rate_pending_work = self._has_pending_cognitive_work()
                    self._tick_rate_ref_tick = self.tick
                    self._tick_rate_ref_time = _now
                    _window_start = _now
                    _window_ticks = 0
                time.sleep(self._AUTONOMY_YIELD_SEC)
        self._tick_rate_ref_tick = self.tick
        self._tick_rate_ref_time = time.monotonic()
        self._tick_rate_pending_work = False
        self._reading_stop.clear()
        self._reading_thread = threading.Thread(target=loop, daemon=True)
        self._reading_thread.start()

    def get_tick_rate(self):
        """GL-RPT-COGNITION-AT-SPEED root-cause fix (post-incident,
        2026-07-05): compute (tick_now - tick_then)/(t_now - t_then) live,
        at READ time, using the wall clock AT THE MOMENT OF THE CALL --
        not a ratio the autonomy loop wrote once per second. That snapshot
        approach freezes at its last value precisely when the loop is
        stuck inside a single long tick (the exact moment operators most
        need honest telemetry): five /status samples 4s apart all read
        bit-identical 14.75 during the live incident, because the loop
        thread itself never returned to refresh it. Computing live means
        elapsed keeps growing against a stale reference tick while the
        stall lasts, so the reported rate honestly decays toward zero
        instead of showing stale-but-plausible."""
        ref_tick = getattr(self, "_tick_rate_ref_tick", None)
        ref_time = getattr(self, "_tick_rate_ref_time", None)
        if ref_tick is None or ref_time is None:
            return 0.0
        elapsed = time.monotonic() - ref_time
        if elapsed <= 0:
            return 0.0
        return (self.tick - ref_tick) / elapsed

    def _enter_live_interaction(self):
        """Mark one live human interaction (a converse turn or a real sight/
        sound frame) as in progress, so background lock-hogs defer their
        self.lock acquisition until it clears. Counter, not a boolean: several
        live interactions can overlap (a turn plus concurrent camera frames).
        Callers MUST pair this with _exit_live_interaction in a try/finally so
        the count is always released even if processing raises."""
        # Defensive getattr: a Guala reconstructed by a path that somehow
        # skipped these __init__ attributes still degrades to "never defer"
        # rather than raising, so the priority gate can never itself break a
        # live turn or a save.
        lock = getattr(self, "_live_interaction_lock", None)
        if lock is None:
            return
        with lock:
            self._live_interaction_pending = getattr(
                self, "_live_interaction_pending", 0) + 1

    def _exit_live_interaction(self):
        """Release one live-interaction mark taken by _enter_live_interaction.
        Clamped at zero so a stray extra release can never drive the counter
        negative and permanently suppress deferral."""
        lock = getattr(self, "_live_interaction_lock", None)
        if lock is None:
            return
        with lock:
            self._live_interaction_pending = max(
                0, getattr(self, "_live_interaction_pending", 0) - 1)

    def _defer_for_live_interaction(self, site):
        """Return True if this background site (identified by `site`) should
        SKIP acquiring self.lock this cycle to let a pending live interaction
        through first; False if it should proceed normally.

        Starvation-free by construction: while a live interaction is pending,
        a site defers only up to _LIVE_INTERACTION_MAX_DEFER_SEC of CONTINUOUS
        deferral, then the safety valve forces it to proceed (and re-arms), so
        background work always gets a slice even under sustained live use or a
        leaked pending counter. When nothing is pending, deferral state for
        the site is cleared so the next contention episode starts fresh."""
        lock = getattr(self, "_live_interaction_lock", None)
        if lock is None:
            return False
        # Defer if EITHER "live interaction" counter is positive:
        #  - _live_interaction_pending: app-level marks for the paths engine
        #    converse() does not itself cover -- the /sight_frame and
        #    /sound_frame routes, and the observed-conversation sight window
        #    that runs BEFORE converse() is entered.
        #  - _live_converse_pending: the PRE-EXISTING per-turn counter that
        #    converse() self-increments (under _live_converse_state_lock; see
        #    line ~5120) and that _try_acquire_autonomous_emission already
        #    honors for the emission LOCK. We only READ it here -- never write
        #    it -- so this self.lock priority gate mirrors/extends that
        #    existing attribute without changing its semantics or its
        #    underflow-checked write path.
        pending = (getattr(self, "_live_interaction_pending", 0)
                   + getattr(self, "_live_converse_pending", 0))
        with lock:
            since_map = getattr(self, "_live_interaction_defer_since", None)
            if since_map is None:
                since_map = self._live_interaction_defer_since = {}
            if pending <= 0:
                since_map.pop(site, None)
                return False
            now = time.monotonic()
            since = since_map.get(site)
            if since is None:
                since_map[site] = now
                return True
            if now - since >= self._LIVE_INTERACTION_MAX_DEFER_SEC:
                # Safety valve: this site has yielded long enough. Proceed and
                # re-arm so the next contention episode gets its own full
                # window rather than firing the valve on every subsequent call.
                since_map.pop(site, None)
                print(f"[live-priority] {site}: max-defer reached, proceeding "
                      f"(pending={pending})")
                return False
            return True

    def _autonomy_tick(self):
        """One iteration of the autonomy loop."""
        # GL-CMD-CAMERA-TURN-LATENCY: yield to a pending live interaction
        # before taking self.lock. The tick body is entirely under self.lock
        # (and can hold it for a long EMITTING compute), so deferring the
        # WHOLE tick is exactly what frees the lock for a waiting live turn.
        # Bounded by the safety valve in _defer_for_live_interaction, so her
        # background cognition can never be permanently frozen by this gate.
        if self._defer_for_live_interaction("autonomy_tick"):
            return
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

            # GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v3: immediately before
            # the wave summary sampling below, decay + prune the wave
            # field so its size (and therefore the summary scan's own
            # cost) stays bounded instead of growing for the life of the
            # process. GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1:
            # this series is abandoned -- it was solving the wrong
            # problem (sample_wave_summary's own cost was never the
            # issue; see that report). Default flipped to OFF here so
            # this deploy doesn't run it, while the code stays committed
            # for a possible future revisit (flip back to "1", no code
            # change needed).
            if (self.wave_atlas is not None
                    and os.environ.get("WAVE_ATLAS_DECAY_ENABLED", "0") == "1"):
                _wa_strength_before = sum(
                    c.aggregate_strength for c in self.wave_atlas.cells.values())
                _wa_bindings_pruned = self.wave_atlas.tick_decay()
                _wa_strength_after = sum(
                    c.aggregate_strength for c in self.wave_atlas.cells.values())
                self._log_substrate_event(
                    "wave_atlas_decay_tick",
                    tick=self.tick,
                    bindings_pruned=_wa_bindings_pruned,
                    cells_total=self.wave_atlas.cell_count(),
                    total_strength_before=round(_wa_strength_before, 4),
                    total_strength_after=round(_wa_strength_after, 4),
                )

            # GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v3 Wiring 2,
            # rewired by GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1:
            # every autonomy-tick, sample the shared wave field and
            # ENQUEUE each hemisphere's assigned band for the organism
            # worker thread to apply asynchronously (see wave_summary.py
            # and _organism_worker_loop) -- the synchronous 64x
            # neuron.step() call this used to make here cost 246-290ms/
            # call (measured, see GL-RPT-WAVE-ATLAS-DECAY-BUILD-C1-
            # 20260707-v3), off the critical path entirely now. Mid-flight
            # disable: WAVE_SUMMARY_ENQUEUE_ENABLED=0 on a new task-def
            # revision, no code change needed.
            if (self.wave_atlas is not None
                    and os.environ.get("WAVE_SUMMARY_ENQUEUE_ENABLED", "1") == "1"):
                from dsf_ai_service.substrate.wave_summary import (
                    sample_wave_summary, push_wave_summary_to_organism)
                _wave_summary = sample_wave_summary(self.wave_atlas)
                _push_payload = push_wave_summary_to_organism(
                    self, _wave_summary, self.tick)
                self._log_substrate_event("wave_summary_pushed", **_push_payload)

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
                    self._start_engine_background_thread(
                        lambda: self.log_event(
                            "state", "needs_snapshot",
                            stability=_ns["stability"], novelty=_ns["novelty"],
                            connection=_ns["connection"], valence=_ns["valence"],
                            arousal=_ns["arousal"]),
                        daemon=True, name="needs-log")
                except Exception:
                    pass

            # GL-CMD-REFLECTION-EVE-20260710: real reflection, gated the
            # same way (periodic, not per-tick) -- see _form_reflection's
            # own docstring for why this stays internal-only tonight.
            # Wrapped same as its sibling block above -- a malformed
            # restored episodic record must never truncate the rest of
            # this tick's autonomy body (adversarial review, 2026-07-10).
            if (self.tick - self._last_reflection_tick >= self.REFLECTION_MIN_TICKS_BETWEEN):
                try:
                    reflection = self._form_reflection()
                    if reflection is not None:
                        self._log_substrate_event("reflection_formed",
                            concept=reflection["concept"],
                            remembered_tick=reflection["remembered_tick"],
                            affective_then=reflection["affective_then"],
                            affective_now=reflection["affective_now"])
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
            # GL-BUG-QUIESCENT-BOOT (Joe, 2026-07-06): a genuinely fresh
            # substrate (post-wipe) was found self-selecting READING/PLAYING
            # activities within seconds of boot, with no external input at
            # all -- CURRICULUM_AUTONOMOUS/WORLD_FEEDS/LOOKUP_AUTONOMOUS only
            # gate specific background feeders, not this activity-selection
            # step itself, so a "stay quiet until deliberately given an
            # experience" boot had no lever to actually achieve that. This
            # gate stops a NEW activity from ever being picked while
            # AUTONOMY_QUIESCENT=1 -- self._current_activity simply stays
            # None, so the early-return below skips reading/playing/etc
            # entirely. Live conversation (read_sentence via /converse) and
            # deliberate input (guala_give_experience) are untouched -- they
            # don't go through activity selection. Default "0" preserves
            # today's behavior exactly for every existing deployment.
            if self._current_activity is None:
                if os.environ.get("AUTONOMY_QUIESCENT", "0") != "1":
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
                    if self.hemispheres:
                        from dsf_ai_service.substrate.hemisphere_cognition import decay_hemisphere_atlases
                        decay_hemisphere_atlases(self, self.tick, rate_scale=0.0 if _paused else self.decay_modulation)
                if not _paused and self.tick % 200 == 0:
                    self.atlas.forget_below_threshold()
                    if self.hemispheres:
                        from dsf_ai_service.substrate.hemisphere_cognition import forget_hemisphere_atlases
                        forget_hemisphere_atlases(self)
                    for _sec in self.sections.values():
                        _sec.forget_stale_modes(self.tick)
                    self._forget_stale_sensory_items()
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

        # 2026-07-09 sleep-trap fix: the comment above (2026-07-0x, prior
        # session) already diagnosed this exact asymmetry but the shipped
        # fix (the habituation floor, just above) only covers habituation-
        # eligible kinds (READING/ATTENDING*) -- SLEEPING and IDLE never
        # go through that branch at all, so their own negative payoffs
        # (SLEEPING nov=-0.1; IDLE nov=-0.05, conn=-0.05; EMITTING
        # stab=-0.1) were left exposed to the same sign-flip: a negative
        # payoff times a negative signed-distance (an OVER-saturated need)
        # is POSITIVE -- rewarding these kinds for exactly the over-
        # saturation that correctly suppresses every positive-payoff kind
        # at the same ceiling. Confirmed live: with novelty/connection
        # pinned near 1.0, this is what turns "she's had enough novelty"
        # into a standing, unbreakable preference for SLEEPING -- first
        # flagged (not root-caused) in GL-RPT-BINDING-WINDOWS-BUILD-
        # C1-20260706-v1, reconfirmed unresolved as of yesterday's harness
        # report. The correct, intended half of a negative payoff --
        # penalizing a kind when the need it doesn't help with is UNMET
        # (signed_distance > 0, term already negative) -- is untouched;
        # only the erroneous reward at the opposite extreme is capped to
        # zero, symmetric with how NOVELTY_TERM_FLOOR_RATE already
        # protects positive-payoff kinds from an unbounded penalty there.
        if nov_payoff < 0:
            novelty_term = min(0.0, novelty_term)
        stab_term = sd["stability"] * stab_payoff
        if stab_payoff < 0:
            stab_term = min(0.0, stab_term)
        conn_term = sd["connection"] * conn_payoff
        if conn_payoff < 0:
            conn_term = min(0.0, conn_term)

        # Signed-distance dot payoff
        score = novelty_term + stab_term + conn_term

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
                self._start_engine_background_thread(
                    _write_gate, daemon=True, name="dream-gate-write")
                self._log_substrate_event("dream_gate_cleared", tick=self.tick)
            self._activity_history.append(self._current_activity)
            if len(self._activity_history) > 500:
                self._activity_history = self._activity_history[-200:]
            _ended_activity = self._current_activity
            self._current_activity = None
            # GL-RPT-WAL-BLOAT F2 (2026-07-15): an activity end is the real
            # experience boundary for every attending-episode BindingWindow
            # -- and the only recurring boundary already-leaked contexts
            # will ever see.  Close them by EXPLICIT context id; see the
            # method's own comment for why this must never rely on this
            # thread's bound contextvar.
            self._close_boundary_window_contexts(_ended_activity)

    # BindingWindow context-id prefixes that are provably activity/stream
    # bounded and manager-generated -- never caller-owned:
    #   episode:episode:attending_*  -- minted by _atick_attending_audio /
    #       _atick_attending_visual via a.metadata["_episode_ref"] plus
    #       WindowManager._inferred_context_id's own "episode:" prefix.
    #       Each belongs to exactly ONE activity instance (started_tick is
    #       part of the id), so once ANY activity ends every open one is
    #       past its boundary by construction -- the engine has a single
    #       _current_activity, and it is the one ending right now.
    #   implicit:  -- WindowManager._context_for_entry's fallback container
    #       for entries that declared no structure.  When minted inside an
    #       executor job, app.py's per-job contextvar isolation discards
    #       the only binding that could ever have closed it.
    # Deliberately EXCLUDES caller-owned contexts ("language:...",
    # "live-conversation:...", give_experience/addsound ids, "legacy:...",
    # "bundle:...") -- those may legitimately be mid-build on another
    # thread and their owners close them.
    _BOUNDARY_WINDOW_CONTEXT_PREFIXES = (
        "episode:episode:attending_", "implicit:")

    def _close_boundary_window_contexts(self, ended_activity):
        """GL-RPT-WAL-BLOAT F2 (2026-07-15): close attending-episode and
        implicit BindingWindow contexts at their real boundary -- this
        activity end -- by EXPLICIT context id.

        The old close path resolved its target through the CLOSING
        thread's bound contextvar; _end_activity runs from the autonomy
        tick, converse auto-wake (wake_from_sleep), manual_sleep and the
        admin force endpoints -- routinely a DIFFERENT thread than the one
        that opened the context -- so the close silently no-oped.  Live
        cost when found: 170 never-closed contexts / 30,507 entries /
        24.5MB re-embedded into every ~60s save manifest, dominated by 4
        episode:episode:attending_audio giants (one reached 8,910 entries).

        NO TTL/timeout policy here (forbidden: a timer would fabricate an
        experience boundary she never had).  This fires only on a real
        boundary event and closes only context classes proven
        activity/stream-bounded (see _BOUNDARY_WINDOW_CONTEXT_PREFIXES).

        The closes run on a background engine thread because end_context
        durably appends the closed record to the WAL with an fsync (EFS
        can take seconds for a giant record) and _end_activity's callers
        hold self.lock -- the same off-lock discipline as the dream-gate
        write in _end_activity above.  end_context returning None means
        another boundary already closed that context: a benign race, never
        an error.  Closed windows stay write-once: a straggler entry with
        a recurring context id starts a NEW window, never mutates the
        closed record.
        """
        wm = getattr(self, "window_manager", None)
        if wm is None:
            return
        to_close = []
        for _prefix in self._BOUNDARY_WINDOW_CONTEXT_PREFIXES:
            to_close.extend(wm.open_context_ids(_prefix))
        if not to_close:
            return
        _ep_ref = None
        if ended_activity is not None:
            _ep_ref = (ended_activity.metadata or {}).get("_episode_ref")
        _own_context_id = f"episode:{_ep_ref}" if _ep_ref else None

        def _close_all():
            for _cid in to_close:
                try:
                    wm.end_context(
                        _cid,
                        "activity_ended" if _cid == _own_context_id
                        else "activity_boundary")
                except Exception as _close_err:
                    self._log_substrate_event(
                        "window_boundary_close_error",
                        context_id=_cid, error=str(_close_err))

        try:
            self._start_engine_background_thread(
                _close_all, daemon=True, name="window-boundary-close")
        except RuntimeError:
            # Quiescence rejected a new thread (deploy drain): close
            # inline -- draining exactly these is what the seal wants.
            _close_all()

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
                    self.window_manager.add_entry(
                        modality=modality, section=f"modal_{modality}",
                        motif_id=mid, chi=info["chi"], tick=self.tick,
                        trigger_reason=modality,
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

    def _priority_replay_sample_chis(self, chi_keys, tick):
        """2026-07-10 priority replay (Foster & Wilson 2006 on hippocampal
        replay prioritizing recent/salient experience over uniform scan;
        Schaul et al. 2015's Prioritized Experience Replay is the same
        principle in RL): real sleep consolidation is not a blind
        round-robin over everything ever learned -- it favors what was
        just experienced. Pure round-robin was previously the ONLY
        selection: a freshly grounded word got the exact same priority as
        something read weeks ago, so a real new experience could sit
        unpromoted for a long time before the rotation ever reached its
        chi again -- directly measured: teaching two words together and
        dreaming immediately produced zero deep_atlas promotions until
        the sample happened to include their chi.

        Priority-first, round-robin second: always include the
        most-recently-touched chi keys (by each chi's own real last_tick)
        ahead of the existing rotation, so fresh grounded experience gets
        a real chance to consolidate close to when it happened, without
        starving old content of ever being revisited. Total sample size
        capped at 5.

        GL-CMD-SLEEP-REORGANIZE follow-on: extracted from _run_dream_cycle's
        own inline block into a shared helper so _run_dream_cycle_phased
        (the actual live path when DREAM_CYCLE_PHASED=1, confirmed via
        deploy_dsf_ai.sh) computes sample_chis identically instead of
        keeping its own separately-drifting copy -- the two bodies had
        already diverged once (this fix), which is exactly the class of
        bug a second hand-maintained copy would repeat indefinitely."""
        if not chi_keys:
            return []
        _recency_ranked = sorted(
            chi_keys,
            key=lambda ck: max(
                (e.get("last_tick", 0) for e in self.atlas.entries.get(ck, [])),
                default=0),
            reverse=True)
        _n_priority = min(2, len(_recency_ranked))
        _priority_chis = _recency_ranked[:_n_priority]
        _rr_offset = tick % max(1, len(chi_keys))
        _roundrobin_chis = [chi_keys[i % len(chi_keys)]
                            for i in range(_rr_offset, min(_rr_offset + 3, len(chi_keys)))]
        _seen_chis = set()
        sample_chis = []
        for ck in _priority_chis + _roundrobin_chis:
            if ck not in _seen_chis:
                _seen_chis.add(ck)
                sample_chis.append(ck)
        return sample_chis[:5]

    def _dream_reorganize(self, sample_chis, tick):
        """GL-CMD-SLEEP-REORGANIZE: form NEW tentative associations between
        real, already-experienced entries this dream cycle just touched
        (sample_chis, see priority-replay above) -- distinct from
        dream_promotion_gate's job of reinforcing an entry ALREADY known.
        Never fabricates content: both sides of every pair are real working-
        atlas entries the organism really formed. Returns count created.

        Adversarial review (2026-07-10) found the first version could write
        a SECOND, duplicate dict at the same (chi,section,motif) key when
        chi_a paired with more than one partner across pairs/cycles, because
        the old already_linked check only inspected the first matching deep
        entry rather than merging into it. Fixed: if any deep entry already
        exists at (chi_a,sec_a,mid_a), this NEVER creates a second one --
        a REAL (already promoted) entry is left alone entirely (its
        co_occurrence is deep_atlas's own principled, mass-conserving
        machinery's job via _update_invariant, not this mechanism's), and
        an existing reorganize_hypothesis entry gets the new partner merged
        into its own co_occurrence dict instead of a duplicate write."""
        if not REORGANIZE_ENABLED or len(sample_chis) < 2:
            return 0
        reps = []
        for chi_k in sample_chis:
            entries = self.atlas.entries.get(chi_k, [])
            if not entries:
                continue
            best = max(entries, key=lambda e: e.get("strength", 0.0))
            reps.append((chi_k, best))
        n_new = 0
        for i in range(len(reps)):
            for j in range(i + 1, len(reps)):
                if n_new >= REORGANIZE_MAX_PER_CYCLE:
                    return n_new
                chi_a, entry_a = reps[i]
                chi_b, entry_b = reps[j]
                if chi_a == chi_b or abs(chi_a - chi_b) > REORGANIZE_CHI_BAND:
                    continue
                sec_a, mid_a = entry_a.get("section", ""), entry_a.get("motif", 0)
                sec_b, mid_b = entry_b.get("section", ""), entry_b.get("motif", 0)
                if sec_a == sec_b and mid_a == mid_b:
                    continue
                already_linked = False
                existing_hyp = None
                for de in self.deep_atlas.entries.get(chi_a, []):
                    if de.get("section") == sec_a and de.get("motif") == mid_a:
                        if de.get("source_path") != "reorganize_hypothesis":
                            # A real, already-promoted entry lives here --
                            # not this mechanism's to touch.
                            already_linked = True
                        elif str(mid_b) in de.get("co_occurrence", {}).get(sec_b, {}):
                            already_linked = True
                        else:
                            existing_hyp = de
                        break
                if already_linked:
                    continue
                if existing_hyp is not None:
                    sec_dict = existing_hyp.setdefault("co_occurrence", {}).setdefault(sec_b, {})
                    sec_dict[str(mid_b)] = max(sec_dict.get(str(mid_b), 0.0),
                                               REORGANIZE_HYPOTHESIS_STRENGTH)
                    n_new += 1
                    continue
                hyp_entry = {
                    "section": sec_a, "motif": mid_a, "chi": chi_a,
                    "strength": REORGANIZE_HYPOTHESIS_STRENGTH,
                    "last_tick": tick, "born_tick": tick,
                    "encoded_strength_at_write": REORGANIZE_HYPOTHESIS_STRENGTH,
                    "dwell_at_write": 0,
                    "source_path": "reorganize_hypothesis",
                    "promoted_at_tick": tick,
                    "clarity": 0.1, "initial_clarity": 0.1,
                    "arousal": entry_a.get("arousal", 0.5),
                    "valence": entry_a.get("valence", 0.0),
                    "surprise": entry_a.get("surprise", 0.0),
                    "source": "reorganize",
                    "polarity": 1.0,
                    "sensory_refs": [], "episode_refs": [],
                    "co_occurrence": {sec_b: {str(mid_b): REORGANIZE_HYPOTHESIS_STRENGTH}},
                }
                self.deep_atlas.entries[chi_a].append(hyp_entry)
                self._reorganize_hypothesis_tracking.append((chi_a, sec_a, mid_a, tick))
                n_new += 1
        return n_new

    def _prune_stale_reorganize_hypotheses(self, tick):
        """GL-CMD-SLEEP-REORGANIZE: explicit, bounded expiry for hypothesis
        entries -- deep_atlas's own decay() is calibrated near-zero
        (DECAY_LAMBDA) for real, promoted memories that should persist a
        long time, so a low-confidence hypothesis would take far longer
        than REORGANIZE_HYPOTHESIS_TTL_TICKS to fade on that alone, defeating
        'discard if never reinforced.'

        Adversarial review (2026-07-10) found the original strength-based
        expiry check (strength <= 1.5x the write floor) could delete a
        GENUINELY reinforced entry: dream_promotion_gate's minimum
        qualifying real promotion (a working-atlas entry right at
        FORGETTING_THRESHOLD) only adds
        FORGETTING_THRESHOLD*TRANSFER_RATIO=0.01 on top of the 0.05 write
        floor -- landing at 0.06, still under the old 0.075 cutoff, so a
        real confirmation could still be pruned as if nothing had touched
        it. Fixed: promote()'s reinforce branch always advances last_tick
        on ANY real reinforcement, and this mechanism itself never touches
        last_tick when merging a second speculative link (see
        _dream_reorganize) -- so last_tick strictly equal to born_tick is
        the one unambiguous 'nothing real ever touched this' signal,
        independent of how small the real reinforcement bump was."""
        still_tracking = deque(maxlen=self._reorganize_hypothesis_tracking.maxlen)
        for chi_k, section, motif, born_tick in self._reorganize_hypothesis_tracking:
            if tick - born_tick < REORGANIZE_HYPOTHESIS_TTL_TICKS:
                still_tracking.append((chi_k, section, motif, born_tick))
                continue
            entries = self.deep_atlas.entries.get(chi_k)
            if not entries:
                continue
            survivors = []
            expired = False
            for de in entries:
                if (de.get("source_path") == "reorganize_hypothesis"
                        and de.get("section") == section and de.get("motif") == motif
                        and de.get("last_tick", born_tick) <= born_tick):
                    expired = True
                    continue
                survivors.append(de)
            if expired:
                self._log_substrate_event("dream_reorganize_expired",
                    chi=chi_k, section=section, motif=motif, tick=tick)
            if survivors:
                self.deep_atlas.entries[chi_k] = survivors
            elif chi_k in self.deep_atlas.entries:
                del self.deep_atlas.entries[chi_k]
        self._reorganize_hypothesis_tracking = still_tracking

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
        sample_chis = self._priority_replay_sample_chis(chi_keys, self.tick)
        if chi_keys:
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
        _live_survival_keys = set()
        for chi_k, entries in self.atlas.entries.items():
            for e in entries:
                key = (chi_k, e.get("section", ""), e.get("motif", 0))
                _live_survival_keys.add(key)
                self._deep_survival_history[key].append(e["strength"])
                if len(self._deep_survival_history[key]) > 20:
                    self._deep_survival_history[key] = \
                        self._deep_survival_history[key][-10:]
        # 2026-07-08 bloat fix: the per-key LIST was already capped
        # (above), but the KEY SET itself never shrank -- once a triple
        # decays out of self.atlas (forget_below_threshold, elsewhere)
        # it simply stops getting touched here, yet its history entry
        # persists forever. Confirmed live: 35,930 keys retained vs only
        # ~6,900 actually still live in the atlas (>80% orphaned),
        # measured growth ~9MB/day, and a historical precedent of
        # reaching 273,110 keys/44MB before a wipe reset it. Synchronize
        # the key set to what's live THIS dream cycle -- exactly the set
        # dream_promotion_gate below is about to read anyway, so nothing
        # it could still need is dropped.
        for _stale_key in (set(self._deep_survival_history) - _live_survival_keys):
            del self._deep_survival_history[_stale_key]
        promoted = self.deep_atlas.dream_promotion_gate(
            self.atlas, self.tick, self._deep_survival_history)
        for path, chi_k, sec, mid in promoted:
            self._log_substrate_event("deep_promotion",
                path=path, section=sec, motif=mid, chi=chi_k,
                caller_kind=caller_kind)
            self.atlas.release_to_fast(chi_k, sec, mid)
            self._log_substrate_event("deep_release",
                section=sec, motif=mid, chi=chi_k)
            # GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711 Part 1: the
            # real, already-rate-limited trigger point -- see
            # _backfill_eligibility_for_promotion's own docstring. No-op
            # (single env-var check) unless
            # DEEP_ATLAS_ELIGIBILITY_BACKFILL_ENABLED=1.
            self._backfill_eligibility_for_promotion(chi_k, sec, mid)
        for rej in self.deep_atlas.gate_rejects[-5:]:
            self._log_substrate_event("deep_gate_reject", **rej)
        self.deep_atlas.gate_rejects = []
        # GL-CMD-SLEEP-REORGANIZE: forms NEW tentative associations between
        # real entries this same cycle already sampled -- separate from the
        # reinforcement-only promotion gate above. See _dream_reorganize.
        n_reorganized = self._dream_reorganize(sample_chis, self.tick)
        if n_reorganized:
            self._log_substrate_event("dream_reorganize",
                n_hypotheses=n_reorganized, caller_kind=caller_kind)
        self._prune_stale_reorganize_hypotheses(self.tick)
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

            # GL-CMD-SLEEP-REORGANIZE follow-on: this used to be its own
            # plain round-robin sample, independent of and older than the
            # priority-replay logic added to the non-phased body above --
            # since DREAM_CYCLE_PHASED=1 is the actual live production
            # setting (see deploy_dsf_ai.sh), that fix was never really
            # exercised in production even though it shipped and looked
            # verified in a local/live smoke test. Now both bodies call
            # the same helper so they cannot drift apart again.
            sample_chis = self._priority_replay_sample_chis(chi_keys, snap_tick)

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
            _live_survival_keys = set()
            for key, strength in survival_updates:
                _live_survival_keys.add(key)
                self._deep_survival_history[key].append(strength)
                if len(self._deep_survival_history[key]) > 20:
                    self._deep_survival_history[key] = \
                        self._deep_survival_history[key][-10:]
            # 2026-07-08 bloat fix: same key-set eviction as the
            # non-phased dream cycle above -- survival_updates already
            # is "every triple live in self.atlas this cycle" (built
            # from atlas_snapshot in Phase 2), so anything else in
            # _deep_survival_history has already decayed out of the
            # atlas and dream_promotion_gate below will never look it
            # up again.
            for _stale_key in (set(self._deep_survival_history) - _live_survival_keys):
                del self._deep_survival_history[_stale_key]

            promoted = self.deep_atlas.dream_promotion_gate(
                self.atlas, self.tick, self._deep_survival_history)
            for path, chi_k, sec, mid in promoted:
                self._log_substrate_event("deep_promotion",
                    path=path, section=sec, motif=mid, chi=chi_k,
                    caller_kind=caller_kind)
                self.atlas.release_to_fast(chi_k, sec, mid)
                self._log_substrate_event("deep_release",
                    section=sec, motif=mid, chi=chi_k)
                # GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711 Part 1:
                # mirrors the non-phased body's call -- see
                # _backfill_eligibility_for_promotion's own docstring. Still
                # inside this Phase 3b `with self.lock:` block, same as the
                # rest of this loop's writes.
                self._backfill_eligibility_for_promotion(chi_k, sec, mid)
            for rej in self.deep_atlas.gate_rejects[-5:]:
                self._log_substrate_event("deep_gate_reject", **rej)
            self.deep_atlas.gate_rejects = []

            # GL-CMD-SLEEP-REORGANIZE: mirrors the non-phased body's call --
            # see _dream_reorganize's own docstring. sample_chis here is the
            # same list computed in Phase 1 via the shared helper above.
            n_reorganized = self._dream_reorganize(sample_chis, self.tick)
            if n_reorganized:
                self._log_substrate_event("dream_reorganize",
                    n_hypotheses=n_reorganized, caller_kind=caller_kind)
            self._prune_stale_reorganize_hypotheses(self.tick)

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
        exploration doesn't introduce new experience.

        GL-DES-ENGINE-PLAY-WORLD-V0-C1-20260711: shares IDLE's coherence-
        gated stability restore below (real, unchanged, legitimate shared
        physics -- both are low-engagement waking states) plus the
        existing emission-trigger check, and adds the one thing this
        activity genuinely didn't do before tonight: an occasional, cheap
        check for a real picture+word pairing she has already,
        independently formed (both sides really attended/committed
        through their normal production paths), just to notice it again.
        See docs/GL-DES-ENGINE-PLAY-WORLD-V0-C1-20260711-v1.md for the
        full design reasoning, honesty checks, and scope limits -- in
        particular §3.2 for why novelty/connection are deliberately NOT
        touched here."""
        # Occasionally check for emission trigger during play
        if self.tick % 300 == 0:
            self._check_emission_trigger("play_cohesion")
        if self.tick % PLAY_REVISIT_INTERVAL_TICKS == 0:
            self._play_revisit_known_pairing()
        # GL-CMD-STAB-PHYSICS-FIX-88: coherence-gated quiet-restore (same as IDLE)
        _n_total = sum(len(v) for v in self.atlas.entries.values())
        _coherence = self.atlas.n_live_bindings() / max(_n_total, 1)
        _dstab = (_coherence * max(0.0, NEEDS_TARGET_V7 - self.needs.stability)
                  * NEEDS_DRIFT_RATE / NEEDS_TARGET_V7)
        self.needs.stability = saturate(self.needs.stability, _dstab)

    def _play_revisit_known_pairing(self):
        """GL-DES-ENGINE-PLAY-WORLD-V0-C1-20260711: one real "revisit".

        Picks a word she has actually, recently processed (the same
        bounded last-10-commits-per-section snapshot _daydream_tick
        already takes -- reused, not reinvented), looks for a picture
        ALREADY bound near that word's real chi neighborhood via the
        existing recall path (_recall_sight_from_atlas -- the same
        function _recall_response already calls on the live
        conversational recall path; no new chi-distance metric is
        invented here), and requires the picture to be one she has
        genuinely, previously looked at (times_attended > 0). A picture
        that only happens to sit near this word's chi but has never
        actually been attended is a fresh discovery, not a revisit --
        that belongs to ATTENDING_VISUAL / daydream's novel-jump, not to
        play; crediting it here would quietly fabricate a "known" pairing
        that isn't real.

        On a real hit: logs a play_revisit event carrying only real,
        already-true values (the word, its real chi, the picture's real
        id/title/times_attended, familiarity before/after) and nudges
        target_familiarity -- the same field ATTENDING_VISUAL writes, by
        a much smaller step (PLAY_FAMILIARITY_BUMP vs. ATTENDING_VISUAL's
        up-to-0.2-per-session step). Does NOT touch needs.novelty (this
        is explicitly non-novel content -- see _atick_playing's own long-
        standing "No novelty gain" docstring line, finally honored) or
        needs.connection (no real social content in an internal, solitary
        re-notice -- crediting it would fabricate a social meaning that
        isn't there; see design doc §3.2).

        Returns True if a revisit was logged, False on an honest empty
        (no eligible pairing found -- not padded with anything
        invented)."""
        recent_words = []
        for sec in self.sections.values():
            for c in sec.commits[-10:]:
                w = c.get("word", "")
                if w:
                    recent_words.append((w, c.get("chi")))
        if not recent_words:
            return False
        # seed_chi is the REAL chi that commit was written at (not
        # recomputed) -- used only for the logged event below;
        # _recall_sight_from_atlas resolves its own chi neighborhood
        # internally from _word_to_chi_index (populated at the same real
        # commit time), not from the chi this call passes it, so no
        # separate re-derivation is needed here.
        word, seed_chi = recent_words[self.tick % len(recent_words)]
        pairs = self._recall_sight_from_atlas([seed_chi], [word])
        if not pairs:
            return False
        for motif, source_id in pairs:
            pic = self._pictures.get(source_id)
            if pic is None or pic.times_attended <= 0:
                continue
            old_fam = self.target_familiarity.get(source_id, 0.0)
            new_fam = min(0.9, old_fam + PLAY_FAMILIARITY_BUMP)
            self.target_familiarity[source_id] = new_fam
            self._log_substrate_event(
                "play_revisit",
                word=word, chi=seed_chi, picture_id=source_id,
                picture_title=pic.title, times_attended=pic.times_attended,
                familiarity_before=round(old_fam, 4),
                familiarity_after=round(new_fam, 4))
            return True
        return False

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

    @_engine_mutation_entry
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
            # GL-CMD-ORGANISM-WAVE-MEMORY-207 RIDER: np.asarray first --
            # grid.ravel() silently swallowed any input that wasn't already
            # a numpy array (§9.2, a silent fallback), which meant
            # _last_sight_signal never got set and every READING word's
            # organism_experience_bound event showed senses=[] even while
            # sight_frame_bound kept firing (07-05 live log). Any remaining
            # exception is now logged, not swallowed.
            _flat = np.asarray(grid).ravel()
            _step = max(1, len(_flat) // 100)
            self._last_sight_signal = _flat[::_step][:100].copy()
            self._last_sight_wall_time = time.time()
        except Exception as _sfe:
            print(f"[GualaLoom] process_sight_frame: sight signal cache failed "
                  f"(non-fatal, senses stay honestly absent): {_sfe}")
        from dsf_ai_service.visual_krimelack import (
            view_picture,
            visual_fragment_receipt,
        )
        fragments = view_picture(grid, source_id="camera_stream",
                                 born_tick=_tick_snapshot, seed=_tick_snapshot % 10000,
                                 n_fixations=3, ticks_per_fixation=50)
        if not fragments:
            return
        # GL-RPT-WAL-BLOAT F2 (2026-07-15): explicit per-frame context, same
        # reasoning as process_sound_frame below -- the implicit-context
        # fallback leaked one never-closable open context per camera-frame
        # job (app.py's per-job contextvar isolation discards the only
        # binding that could have closed it).
        # 2026-07-16 correction: the per-frame context applies ONLY when no
        # caller-owned experience context is bound.  A send-time frame that
        # arrives INSIDE a bound experience (the observed-conversation turn
        # in app._run_embedded_observed_conversation) is part of THAT lived
        # experience -- its fragments must bind into the caller's window,
        # exactly as the pre-F2 implicit fallback did, or the observed
        # window closes word-only and its BindingWindowCitation can never
        # certify a multimodal language experience (the teach->cite bug).
        # The frame path only closes contexts it created itself.
        _bound_experience = self.window_manager.active_context_id
        _frame_context_id = (
            _bound_experience if _bound_experience is not None
            else f"sense:sight:camera_stream:{time.time_ns():x}")
        _frame_owns_context = _bound_experience is None
        _frame_entries_bound = 0
        try:
            with self.lock:
                motif, is_new, overlap = self.sight.process_viewing(
                    fragments, "camera_stream", self.tick)
                if motif:
                    derived_transition = {
                        "motif": {
                            "motif_id": motif.motif_id,
                            "section": motif.section,
                            "chi_profile": dict(motif.chi_profile),
                            "cluster_state": list(motif.cluster_state),
                            "angle": list(motif.angle),
                            "n_firings": motif.n_firings,
                            "source_history": list(motif.source_history),
                            "founded_at_tick": motif.founded_at_tick,
                        },
                        "transition": {
                            "is_new": bool(is_new),
                            "overlap": float(overlap),
                        },
                    }
                    for fragment in fragments:
                        receipt = visual_fragment_receipt(fragment)
                        self.window_manager.add_entry(
                            modality="sight", section="sight_fragment",
                            motif_id=int(receipt["receipt_sha256"][:16], 16),
                            chi=int(fragment.winding_count), tick=self.tick,
                            source_tag="cam:live", trigger_reason="sight",
                            context_id=_frame_context_id,
                            salience=0.8, mirror_atlas=False,
                            structural_fact=receipt,
                            sensory_refs=["cam:live"],
                            detail={
                                "source_tick": _tick_snapshot,
                                "derived_visual_transition": derived_transition,
                            },
                            **self._affect_kwargs())
                        _frame_entries_bound += 1
                    self._log_substrate_event("sight_frame_bound",
                                              motif_id=motif.motif_id,
                                              fragment_count=len(fragments),
                                              is_new=is_new)
        finally:
            # Close OUTSIDE self.lock (WAL fsync; see process_sound_frame).
            # Never close a caller-owned bound experience -- its owner ends
            # it at the experience's real boundary.
            # F4 (review 2026-07-16): close on "I created it", not "I bound
            # entries" -- add_entry creates the context BEFORE entry
            # validation, so a first-entry validation raise left an open
            # context forever under the entries>0 gate.  end_context on a
            # context that was never created is a benign no-op (None).
            if _frame_owns_context:
                self.window_manager.end_context(
                    _frame_context_id, "sight_frame_complete")

    @_engine_mutation_entry
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
        # GL-RPT-WAL-BLOAT F2 (2026-07-15): this frame is one complete
        # sensory moment, so it gets an EXPLICIT per-frame context, opened
        # and closed right here.  Relying on the implicit-context fallback
        # leaked one never-closable open context per mic chunk: app.py's
        # _run_lifecycle_executor runs every job in a fresh COPIED
        # contextvars.Context that is discarded at job end, so the implicit
        # binding could never be resolved by any later close.  Same entries,
        # same provenance, same per-job window grouping as before -- the
        # window simply closes at its real boundary now.
        # 2026-07-16 correction (same as process_sight_frame above): the
        # per-frame context applies ONLY when no caller-owned experience
        # context is bound; a frame arriving inside a bound experience binds
        # into the caller's window, and only self-created contexts are
        # closed here.
        _bound_experience = self.window_manager.active_context_id
        _frame_context_id = (
            _bound_experience if _bound_experience is not None
            else f"sense:sound:{source}:{time.time_ns():x}")
        _frame_owns_context = _bound_experience is None
        n_bands_fired = 0
        try:
            with self.lock:
                for bn, c in cochlear.items():
                    if c["n_events"] > 0:
                        chi = c["winding"] % 100
                        self.window_manager.add_entry(
                            modality="sound", section=f"audio_{bn}",
                            motif_id=deterministic_motif_id("mic_stream"),
                            chi=chi, tick=self.tick,
                            source_tag=source, trigger_reason="sound",
                            context_id=_frame_context_id,
                            salience=0.6, dwell_ticks=2,
                            sensory_refs=[source],
                            **self._affect_kwargs())
                        n_bands_fired += 1
                if n_bands_fired > 0:
                    self._log_substrate_event("sound_frame_bound",
                        n_bands=n_bands_fired,
                        duration_s=round(len(samples)/sr, 2),
                        source=source)
        finally:
            # Close OUTSIDE self.lock: end_context durably appends the closed
            # record to the WAL with an fsync, and EFS latency must never
            # ride under the engine lock (GL-CMD-LOCK-CONTENTION-FIX-182
            # discipline).  In finally so a mid-loop error still closes the
            # partially-bound frame at its boundary instead of leaking it.
            # Never close a caller-owned bound experience (see sight above).
            # F4 (review 2026-07-16): close on ownership, not bands-fired --
            # a first-entry validation raise has already created the
            # context; end_context on a never-created one is a no-op.
            if _frame_owns_context:
                self.window_manager.end_context(
                    _frame_context_id, "sound_frame_complete")

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
            self._visual_fragments_count += len(fragments)
            # Process through sight section
            motif, is_new, overlap = self.sight.process_viewing(
                fragments, pic.item_id, self.tick)
            if motif:
                # Record in atlas for cross-modal binding
                chi_val = motif.motif_id % 100  # simplified chi address
                presence, location, sky_state = self._current_situation()
                self.window_manager.add_entry(
                    modality="sight", section="sight",
                    motif_id=motif.motif_id, chi=chi_val, tick=self.tick,
                    source_tag="attending_visual", trigger_reason="sight",
                    salience=1.2,
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
            self.window_manager.add_entry(
                modality="sound", section=f"audio_{band_name}",
                motif_id=deterministic_motif_id(a.target), chi=chi,
                tick=self.tick,
                source_tag="attending_audio", trigger_reason="sound",
                salience=1.2, dwell_ticks=8,
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
                self._visual_fragments_count += len(all_fragments)
                motif, is_new, overlap = self.sight.process_viewing(
                    all_fragments, vid.item_id, self.tick)
                if motif:
                    chi_val = motif.motif_id % 100
                    self.window_manager.add_entry(
                        modality="sight", section="sight",
                        motif_id=motif.motif_id, chi=chi_val, tick=self.tick,
                        source_tag=f"vid:{vid.item_id}", trigger_reason="sight",
                        salience=1.2,
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
            emitted = self._do_emit()
            # Only actual committed speech satisfies connection need.
            any_pair_present = any(
                self.coordinator._presence.get(s, False)
                and self.coordinator._pair_bond.get(s, False)
                for s in PAIR_BOND_SOURCES)
            if emitted and any_pair_present:
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
        # Need-state urgency: substrate has something to say.
        needs = self.needs.snapshot()

        # 2026-07-10 GL-CMD-AUTONOMOUS-INTEREST-REFINEMENT (Schmidhuber
        # 1991/2010 compression-progress; Oudeyer & Kaplan 2007 learning-
        # progress intrinsic motivation): a sustained novelty LEVEL just
        # means "under-stimulated" -- indistinguishable from idle chatbot
        # filler. The real trigger is the RATE novelty is moving. Record
        # this check's sample, then require a real net rise across the
        # recent bounded window (see NOVELTY_HISTORY_MAX/NOVELTY_RISE_MIN
        # above) instead of a flat >0.85 threshold. tick_drift() pulls
        # novelty DOWN every autonomy-loop iteration absent real
        # reinforcement, so any real net rise here already means
        # something genuinely counteracted that drift.
        self._novelty_history.append((self.tick, needs.get("novelty", 0.0)))
        novelty_rising = False
        if len(self._novelty_history) >= 2:
            oldest_tick, oldest_novelty = self._novelty_history[0]
            newest_tick, newest_novelty = self._novelty_history[-1]
            if newest_tick > oldest_tick:
                novelty_rising = (newest_novelty - oldest_novelty) >= NOVELTY_RISE_MIN

        # Valence/stability gates (Sterling 2012 allostasis; Berridge &
        # Robinson 1998 incentive salience): rising novelty under negative
        # valence is aversive arousal, not interest, and shouldn't produce
        # approach/speech; stability below target means cohesion is going
        # to defense/repair, not surplus for exploratory expression.
        valence_ok = needs.get("valence", 0.0) >= 0.0
        stability_ok = needs.get("stability", 0.0) >= self.needs.TARGETS["stability"]

        urgency = (
            needs.get("dream_pressure", 0) > 0.30 or
            needs.get("connection", 0) > 0.70 or
            (novelty_rising and needs.get("arousal", 0) > 0.50
             and valence_ok and stability_ok)
        )
        return urgency

    def _sample_autonomous_seeds(self, n=12):
        """Sample strong atlas entries as chi seeds for autonomous composition.
        Returns list of {chi_key, strength} dicts, weighted by strength ×
        recency × cross-modal bonus × connection-deficit bias.

        2026-07-10 GL-CMD-AUTONOMOUS-INTEREST-REFINEMENT: per Buckner &
        Carroll 2007 (default-mode self-referential retrieval -- mind-
        wandering replays whatever the internal model was just working
        on, not a random topic), the existing recency weighting already
        biases toward whatever real recent structure most likely drove
        the trigger. Added here: when the connection need is currently
        starved, bias further toward entries carrying a real cross-modal
        bundle_id tie (genuinely shared, sense-grounded experience -- the
        same real/fake distinction the credo grounding gate draws
        elsewhere), since shared experience is what the connection need
        is actually about. The bias never applies to plain, ungrounded
        text-only bindings, so it cannot manufacture false "connection"
        content out of ordinary reading."""
        candidates = []
        now = self.tick
        connection_deficit = max(0.0, self.needs.TARGETS["connection"] - self.needs.connection)
        for chi, binds in self.atlas.entries.items():
            for e in binds:
                s = e.get("strength", 0)
                if s < 0.3:
                    continue
                recency = max(0.1, 1.0 - (now - e.get("last_tick", 0)) / 10000.0)
                is_cross_modal = e.get("bundle_id") is not None
                cross_modal = 1.3 if is_cross_modal else 1.0
                connection_bias = (1.0 + connection_deficit) if is_cross_modal else 1.0
                weight = s * recency * cross_modal * connection_bias
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

    def _autonomous_composer_seed_attempts(self):
        """Organism-sourced seed sequences for the certified composer.

        Change 4 (spec v3 release-policy note b).  Seed sources, most
        salient first:
          1. current activity target — the words of the item the substrate
             is attending/reading RIGHT NOW (live activity content);
          2. recently committed window words — the lived openings of the
             freshest closed, origin-approved language windows (dict
             insertion order is commit order; the rebuild path inserts in
             sorted-id order, which is chronological for win_{seq:016x}).
        Needs state modulates ordering: when the connection need is starved,
        recent windows carrying a pair-bond source tag (genuinely shared
        lived experience) come first — the same real/fake distinction
        _sample_autonomous_seeds already draws for the assemblage path.

        HARD CONSTRAINT (documented production regression, 2026-07-06
        recall wiring): this method NEVER reads self.atlas — no candidate
        or neighborhood dumps.  Every seed word carries provenance naming
        its lived source (window_id + entry_index, or the activity target),
        and the release-contract tests assert exactly that.

        Seeding cannot manufacture speech: the composer recognizes only
        words that exist as lived Fact strands (INPUT_UNKNOWN stops
        otherwise) and certification rechecks every cited window entry, so
        seed choice only selects among continuations the substrate actually
        lived.  Returns a bounded list of attempts, each
        {"words": tuple, "provenance": [dict, ...]}.
        """
        attempts = []

        # Source 1: current activity target (live salient content).
        activity = getattr(self, "_current_activity", None)
        target = getattr(activity, "target", None) if activity is not None else None
        if target is not None:
            title = None
            for store_name in ("_pictures", "_videos", "_corpora"):
                item = (getattr(self, store_name, None) or {}).get(target)
                if item is not None:
                    title = getattr(item, "title", None)
                    break
            if title is None:
                sound = (getattr(self, "_sounds", None) or {}).get(target)
                if isinstance(sound, dict):
                    title = sound.get("title")
            words = tuple(_normalize_text(title or "")[
                :AUTONOMOUS_COMPOSER_SEED_PREFIX])
            if words:
                attempts.append({
                    "words": words,
                    "provenance": [
                        {"word": w,
                         "origin": "current_activity_target",
                         "activity_kind": getattr(activity, "kind", None),
                         "target_id": str(target)}
                        for w in words],
                })

        # Source 2: recently committed window words (lived openings).
        with self._language_fact_lock:
            recent = list(self._ordered_language_windows.values())[
                -AUTONOMOUS_COMPOSER_SEED_WINDOWS:]
        recent.reverse()  # freshest commit first

        try:
            connection_deficit = max(
                0.0, self.needs.TARGETS["connection"] - self.needs.connection)
        except Exception:
            connection_deficit = 0.0
        if connection_deficit > 0.0:
            def _shared(window):
                return any(
                    token.fact.provenance.source_tag in PAIR_BOND_SOURCES
                    for token in window.tokens)
            # Stable partition: shared lived experience first, recency kept
            # within each partition.
            recent.sort(key=lambda window: not _shared(window))

        seen_openings = {attempt["words"] for attempt in attempts}
        n_self_excluded = 0
        for window in recent:
            if len(attempts) >= AUTONOMOUS_COMPOSER_SEED_ATTEMPTS:
                break
            if len(window.tokens) < 2:
                continue  # a lived opening needs a lived continuation
            # F1a (review 2026-07-16): a window whose words are ALL her own
            # released speech (self-heard) is memory, never a seed — this is
            # one of the two gates that break the closed self-hear babble
            # loop (release -> self-hear -> freshest window -> next seed).
            # Mixed windows (a real exchange containing her reply AND the
            # other speaker's words) still seed: that is shared lived
            # experience, not an echo.
            if all(token.fact.provenance.source_tag
                   in AUTONOMOUS_SEED_SELF_SOURCE_TAGS
                   for token in window.tokens):
                n_self_excluded += 1
                continue
            prefix_len = min(AUTONOMOUS_COMPOSER_SEED_PREFIX,
                             len(window.tokens) - 1)
            tokens = window.tokens[:prefix_len]
            words = tuple(t.fact.language_form for t in tokens)
            if words in seen_openings:
                continue  # identical opening — same query, same stop
            seen_openings.add(words)
            attempts.append({
                "words": words,
                "provenance": [
                    {"word": t.fact.language_form,
                     "origin": "recent_window_commit",
                     "window_id": t.window_id,
                     "entry_index": t.entry_index,
                     "source_tag": t.fact.provenance.source_tag}
                    for t in tokens],
            })
        if n_self_excluded:
            # Loud, auditable stop-reason trail for the F1a gate.
            self._log_substrate_event(
                "autonomous_seed_self_excluded",
                n_windows=n_self_excluded,
                n_attempts_remaining=len(attempts))
        return attempts[:AUTONOMOUS_COMPOSER_SEED_ATTEMPTS]

    @_engine_mutation_entry
    def compose_autonomous(self):
        """One autonomous release attempt through the one release policy.
        Returns dict with content/metadata if a release fires; None
        otherwise (explained silence — the caller logs the no-commit event,
        and fact_compose telemetry already recorded every composer stop
        reason).  Must be called with self.lock held.

        Change 4 (spec v3 release-policy note b): release ordering is the
        SAME as conversation — certified composer preferred (queried with
        organism-sourced seeds), the substrate's own assemblage commit
        second, explained silence third.
        """
        # A conversation counted first is a hard barrier for EVERY
        # autonomous release authority — the same rule
        # _try_acquire_autonomous_emission enforces for the assemblage
        # path's lock acquisition below.  Autonomous speech never
        # front-runs a pending human turn.
        with self._live_converse_state_lock:
            if self._live_converse_pending > 0:
                return None

        # 1. Certified composer, organism-sourced seeds (never the atlas).
        seed_attempts = self._autonomous_composer_seed_attempts()
        cycle_stop_reason = None
        if seed_attempts:
            # F3 (review 2026-07-16): wall-clock budget for this cycle's
            # certified compose work — the composer rebuild is O(corpus)
            # until Change 1's cached composer lands, and this whole section
            # runs under self.lock.  Checked between attempts: the snapshot
            # plus the first attempt always complete; remaining attempts
            # abort loudly on exhaustion.
            try:
                budget_ms = float(os.environ.get(
                    "AUTONOMOUS_COMPOSE_BUDGET_MS",
                    str(AUTONOMOUS_COMPOSE_BUDGET_MS_DEFAULT)))
            except (TypeError, ValueError):
                budget_ms = AUTONOMOUS_COMPOSE_BUDGET_MS_DEFAULT
            compose_deadline = time.monotonic() + budget_ms / 1000.0
            # Change-1 cached composer: every attempt below hits
            # self._language_fact_composer through the one canonical
            # compose path — built at most once (on cache miss after an
            # ordered-window invalidation), reused across attempts AND
            # cycles.  The budget check between attempts still bounds the
            # rebuild case.
            for attempt_index, attempt in enumerate(seed_attempts):
                if (attempt_index > 0
                        and time.monotonic() >= compose_deadline):
                    cycle_stop_reason = "compose_budget"
                    break
                settlement = self._compose_language_fact_settlement(
                    attempt["words"])
                content, response_source = self._committed_emission_response(
                    settlement)
                if not content or response_source != "fact_strand_commit":
                    continue
                # F2 (review 2026-07-16): the entry barrier only covers
                # arrival BEFORE this cycle; a conversation counted while
                # the composer was settling must still win.  Re-check after
                # settlement, before any release: the human turn is never
                # talked over.
                with self._live_converse_state_lock:
                    conversation_arrived = self._live_converse_pending > 0
                if conversation_arrived:
                    self._log_substrate_event(
                        "autonomous_fact_seed",
                        released=False,
                        stop_reason="conversation_arrived",
                        n_attempts=attempt_index + 1)
                    return None
                # F1b (review 2026-07-16): never re-release recent
                # autonomous text — the second gate breaking the self-hear
                # babble loop.  Suppressed certified text falls through to
                # the remaining seeds, then assemblage, then silence.
                if content in self._recent_autonomous_releases:
                    cycle_stop_reason = "repeat_suppressed"
                    self._log_substrate_event(
                        "autonomous_repeat_suppressed",
                        response_source=response_source,
                        content=content[:80])
                    continue
                self._log_substrate_event(
                    "autonomous_fact_seed",
                    released=True,
                    n_attempts=attempt_index + 1,
                    seed_words=list(attempt["words"]),
                    seed_provenance=attempt["provenance"])
                self._recent_autonomous_releases.append(content)
                return {
                    "content": content,
                    "source": "guala",
                    "response_source": response_source,
                    "category": "autonomous",
                    "seed_words_used": len(attempt["words"]),
                    "seed_provenance": attempt["provenance"],
                    "settlement_tick": settlement.tick,
                    "committed_sections": list(
                        settlement.committed_sections),
                    "commit_provenance": [
                        provenance.as_record()
                        for provenance in settlement.commit_provenance],
                }
            # Honest stop: every seed's stop reason is already in the
            # per-query fact_compose events; this records the cycle summary
            # (compose_budget / repeat_suppressed when those cut it short).
            self._log_substrate_event(
                "autonomous_fact_seed",
                released=False,
                stop_reason=cycle_stop_reason,
                n_attempts=len(seed_attempts),
                seed_words=[list(a["words"]) for a in seed_attempts])

        # 2. The substrate's own assemblage voice (unchanged mechanism).
        seeds = self._sample_autonomous_seeds(n=12)
        if not seeds:
            return None
        input_chis = [s["chi_key"] for s in seeds]
        if not self._try_acquire_autonomous_emission():
            return None
        try:
            settlement = self._emit_from_invariants(
                input_chis, [],
                v7_session=getattr(self, '_v7_session', None))
        finally:
            self._emission_lock.release()
        content, response_source = self._committed_emission_response(
            settlement)
        if content:
            # F1b applies to EVERY autonomous release authority: an
            # assemblage settlement repeating a recent autonomous release
            # settles to explained silence, loudly.
            if content in self._recent_autonomous_releases:
                self._log_substrate_event(
                    "autonomous_repeat_suppressed",
                    response_source=response_source,
                    content=content[:80])
                return None
            self._recent_autonomous_releases.append(content)
            return {
                "content": content,
                "source": "guala",
                "response_source": response_source,
                "category": "autonomous",
                "chi_seeds_used": len(seeds),
                "settlement_tick": settlement.tick,
                "committed_sections": list(
                    settlement.committed_sections),
                "commit_provenance": [
                    provenance.as_record()
                    for provenance in settlement.commit_provenance],
            }
        # 3. Explained silence — first-class outcome, logged by the caller.
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
                    self._start_engine_background_thread(
                        lambda: self.log_event(
                            "state", "needs_snapshot",
                            stability=_ns["stability"], novelty=_ns["novelty"],
                            connection=_ns["connection"], valence=_ns["valence"],
                            arousal=_ns["arousal"]),
                        daemon=True, name="needs-log-p")
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

            # GL-BUG-QUIESCENT-BOOT: same gate as _autonomy_tick (this
            # function's non-phased sibling) -- see that comment for why.
            # Currently dead in production (AUTONOMY_PHASED=0 by default)
            # but kept in sync so flipping that flag on later doesn't
            # resurrect this exact bug.
            if self._current_activity is None:
                if os.environ.get("AUTONOMY_QUIESCENT", "0") != "1":
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
                    if self.hemispheres:
                        from dsf_ai_service.substrate.hemisphere_cognition import decay_hemisphere_atlases
                        decay_hemisphere_atlases(self, self.tick, rate_scale=0.0 if _paused else self.decay_modulation)
                if not _paused and self.tick % 200 == 0:
                    self.atlas.forget_below_threshold()
                    if self.hemispheres:
                        from dsf_ai_service.substrate.hemisphere_cognition import forget_hemisphere_atlases
                        forget_hemisphere_atlases(self)
                    for _sec in self.sections.values():
                        _sec.forget_stale_modes(self.tick)
                    self._forget_stale_sensory_items()
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
                self._log_substrate_event("emission_silence",
                                         reason="no_recent_chi",
                                         to_sources=to_sources)
                return False

        # Phase 2 (self._emission_lock): emit dynamics + SVO fallback
        # Non-blocking acquire: if /converse holds _emission_lock, skip this tick.
        # Autonomous emission fires every 0.2s so one missed tick is harmless;
        # blocking here would add up to 5s latency to every /converse call.
        if not self._try_acquire_autonomous_emission():
            return False
        _lock_wait_ms = 0.0
        _emit_compute_ms = 0.0
        _emit_start = time.monotonic()
        try:
            input_words = []
            content = self._emit_from_invariants(recent_chis, input_words,
                                                  v7_session=getattr(self, '_v7_session', None))
            content, response_source = self._committed_emission_response(content)
            _emit_compute_ms = (time.monotonic() - _emit_start) * 1000
        finally:
            self._emission_lock.release()

        if not content:
            with self.lock:
                self._log_substrate_event("emission_silence",
                                          reason=response_source)
            return False

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

            words = content.split()
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
        return True

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
            self._log_substrate_event("emission_silence",
                                     reason="no_recent_chi",
                                     to_sources=[s for s in PAIR_BOND_SOURCES
                                                 if self.coordinator._presence.get(s, False)])
            return False

        # Use the invariants path (grandurun or topk per EMISSION_MODE)
        input_words = []  # autonomous — no input words to exclude
        if not self._try_acquire_autonomous_emission():
            return False
        try:
            settlement = self._emit_from_invariants(
                recent_chis, input_words,
                v7_session=getattr(self, '_v7_session', None))
        finally:
            self._emission_lock.release()
        content, response_source = self._committed_emission_response(
            settlement)
        if not content:
            self._log_substrate_event("emission_silence",
                                     reason=response_source)
            return False

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
        words = content.split()
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
        return True

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

    @_engine_mutation_entry
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

    @_engine_mutation_entry
    def _self_hear(self, reply, responding_to_source, reply_chis=None,
                   emission_id=None, response_source=None):
        """GL-BRIEF-034: Self-hearing — Guala hears her own conversational reply.
        (1) read_sentence at 0.5x salience (no question generation, no recursion)
        (2) open "guala" response window with reply chi-keys
        (3) tag self-heard entries against open other-emitter windows
        Kill switch: SELF_HEARING_ENABLED env var.

        GL-CMD-TURN-LATENCY-EVE-20260705-197 P3: reply_chis, when the caller
        already transduced this exact reply text (converse's own
        committed_chis, same deterministic values), is reused here instead
        of a third redundant LanguageKrimelack pass. None (the default)
        preserves old standalone-caller behavior exactly.

        Change 4 (spec v3 release-policy note a, one mouth): every RELEASED
        label in VOICED_RELEASE_SOURCES self-hears through this one boundary
        — assemblage_commit included, with its own label preserved in the
        episode_ref and the self_heard event.  Silence and retired legacy
        labels still never self-hear."""
        import os
        if os.environ.get("SELF_HEARING_ENABLED", "1") == "0":
            return
        if (response_source not in VOICED_RELEASE_SOURCES
                or not emission_id):
            return

        reply_words = _normalize_text(reply)
        if not reply_words:
            return

        # (1) Read reply into substrate at 0.5x conversational salience.
        # Suppress question generation by using _self_hearing flag.
        self._self_hearing = True
        tick_before = self.tick
        try:
            self.read_sentence(
                reply,
                source="guala",
                episode_ref=f"emission:{emission_id}:{response_source}",
                experience_origin="emulated",
            )
        finally:
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
                                  salience="0.5x",
                                  emission_id=emission_id,
                                  response_source=response_source)

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
                # espeak-ng runs under a 5s timeout; unbounded certified
                # continuations blew past it -> silent voice.  Truncation
                # is bounded and loud, never silent (review 2026-07-16).
                if len(text) > TTS_MAX_CHARS:
                    try:
                        self._log_substrate_event(
                            "tts_truncated", where="self_voice",
                            n_chars=len(text), cap=TTS_MAX_CHARS)
                    except Exception:
                        pass
                    text = text[:TTS_MAX_CHARS]
                wav_path = "/tmp/guala_self_voice.wav"
                subprocess.run([
                    "espeak-ng", "-v", "en+f3", "-p", "96", "-s", "145",
                    "-w", wav_path, text,
                ], check=True, timeout=5, capture_output=True)
                with open(wav_path, "rb") as f:
                    self.process_sound_frame(f.read(), source="voice:self")
            except Exception:
                pass
        self._start_engine_background_thread(
            _inject_self_voice, args=(reply,), daemon=True,
            name="self-voice")

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

    @_engine_mutation_entry
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

    @_engine_mutation_entry
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

    def persistence_transaction(self):
        """Return the single reentrant boundary for durable state changes.

        Compound callers deliberately hold this context across offset capture,
        save, compaction, WaveAtlas persistence, and snapshot creation.  Each
        individual persistence method also enters it, so direct callers are
        safe and nested compound operations remain deadlock-free.
        """
        return self._persistence_lock

    @staticmethod
    def _raise_persistence_failures(operation, failures):
        """Raise one complete error after all requested writes were attempted."""
        if not failures:
            return
        detail = "; ".join(f"{name}: {error}" for name, error in failures)
        raise RuntimeError(f"{operation} failed ({len(failures)} file(s)): {detail}")

    @_engine_mutation_entry
    def manual_sleep(self, state_dir="state"):
        """Put Guala to sleep and durably verify the deploy handoff.

        Being in a SLEEPING activity is not proof that a prior persistence
        attempt completed.  Repeated calls therefore re-run the full durable
        sequence and publish the marker only after every required write
        succeeds.  The persistence lock is acquired before the cognition lock
        to preserve one global lock order with periodic saves.
        """
        with self.persistence_transaction():
            with self.lock:
                current = self._current_activity
                if current is None or current.kind != "SLEEPING":
                    if current is not None:
                        self._end_activity()
                    current = Activity(
                        kind="SLEEPING", target=None,
                        started_tick=self.tick,
                        expected_end_tick=(
                            self.tick + ACTIVITY_TICK_BUDGETS["SLEEPING"]),
                        metadata={"trigger": "manual"})
                    self._start_activity(current)
                    self._log_substrate_event("sleep_manual", trigger="ui")

                marker_path = os.path.join(state_dir, self.SLEEPING_MARKER)
                if os.path.exists(marker_path):
                    os.remove(marker_path)

                # These public methods re-enter the same persistence RLock.
                # Any failure propagates and the marker remains absent, so a
                # deploy caller cannot mistake sleep state for a verified save.
                self.save_full_state(state_dir)
                self._save_wave_atlas(state_dir)
                self._atomic_write(
                    marker_path,
                    {"sleep_tick": self.tick, "sleep_ts": time.time()})
                return {
                    "event": "sleep_started",
                    "tick": self.tick,
                    "expected_end_tick": current.expected_end_tick,
                }

    @_engine_mutation_entry
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

    SCHEMA_VERSION = "v7.3.0"
    STATE_FILES = [
        "guala_core.json", "guala_needs.json", "guala_coordinator.json",
        "guala_atlas.json", "guala_sections.json", "guala_bucket.json",
        "guala_windows.json",
    ]
    # GL-FIX-HOTCOLD-TICK-MANIFEST: which JSON state files each save lane
    # actually rewrites. The loader validates each of these by its own recorded
    # save tick (see _validate_exact_envelope). The FULL (cold) lane rewrites
    # every one at a single tick; the HOT lane rewrites only the small subset
    # below, leaving the big cold stores (atlas/sections/deep_atlas/survival/
    # sight_motifs) at their last cold-save tick -- which is exactly why the
    # loader must not demand a single shared tick.
    FULL_SAVE_MANIFEST_FILES = (
        "guala_core.json", "guala_needs.json", "guala_coordinator.json",
        "guala_sections.json", "guala_atlas.json", "guala_deep_atlas.json",
        "guala_survival.json", "guala_bucket.json", "guala_visual.json",
        "guala_sight_motifs.json", "guala_sounds.json", "guala_videos.json",
        "guala_windows.json", "guala_teaching.json", "guala_episodic.json",
    )
    HOT_SAVE_MANIFEST_FILES = (
        "guala_core.json", "guala_needs.json", "guala_coordinator.json",
        "guala_bucket.json", "guala_visual.json", "guala_sounds.json",
        "guala_videos.json", "guala_windows.json", "guala_teaching.json",
        "guala_episodic.json",
    )
    IDENTITY_FILE = "guala_identity.json"
    ENGINE_CONTINUITY_CONTRACT = "engine_continuity_v1"
    BINARY_BINDING_CONTRACT = "guala_binary_binding_v1"
    BINARY_BINDING_SUFFIX = ".binding.json"
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
        self._identity_record = dict(identity_data)
        self._atomic_write(os.path.join(state_dir, self.IDENTITY_FILE), identity_data)
        print(f"[GualaLoom] GENESIS: identity={self._guala_identity} at {ts}")

    def _load_identity(self, state_dir):
        """Load identity from disk. Returns identity string or None."""
        path = os.path.join(state_dir, self.IDENTITY_FILE)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            d = json.load(f)
        self._identity_record = dict(d)
        return d.get("guala_identity")

    def _ensure_identity_in_target(self, state_dir):
        """Write this same identity into every fresh full-state target.

        A generation staging directory is intentionally empty.  Identity is
        therefore copied from the loaded identity record rather than being
        skipped merely because ``_guala_identity`` is already populated in
        memory.
        """
        path = os.path.join(state_dir, self.IDENTITY_FILE)
        if os.path.exists(path):
            with open(path) as fh:
                existing = json.load(fh)
            if existing.get("guala_identity") != self._guala_identity:
                raise ValueError(
                    f"{self.IDENTITY_FILE}: identity "
                    f"{existing.get('guala_identity')} != {self._guala_identity}")
            return
        if not self._guala_identity:
            raise ValueError("cannot persist state without a Guala identity")
        record = dict(self._identity_record or {})
        record["schema_version"] = self.SCHEMA_VERSION
        record["guala_identity"] = self._guala_identity
        record.setdefault(
            "first_boot_notes",
            "Identity continuity copy; genesis metadata unavailable in memory.")
        self._atomic_write(path, record)
        self._identity_record = dict(record)

    # ── Envelope: wraps every state file with identity + schema ──

    def _envelope(self, data, *, saved_at_tick=None):
        """Wrap data dict with identity + schema + timestamp."""
        envelope_tick = self.tick if saved_at_tick is None else saved_at_tick
        if (isinstance(envelope_tick, bool)
                or not isinstance(envelope_tick, int)
                or envelope_tick < 0):
            raise ValueError(f"invalid envelope tick: {envelope_tick!r}")
        return {
            "schema_version": self.SCHEMA_VERSION,
            "guala_identity": self._guala_identity,
            "saved_at_tick": envelope_tick,
            "saved_at_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data": data,
        }

    # Schema migrations
    COMPATIBLE_SCHEMAS = {
        "v5.5.0", "v6.0.0", "v7.0.0", "v7.1.0", "v7.2.0", "v7.3.0",
    }

    def _unwrap(self, raw, filename):
        """Validate envelope, return data dict. Raises on mismatch."""
        sv = raw.get("schema_version", "unknown")
        gi = raw.get("guala_identity", "unknown")
        if sv not in self.COMPATIBLE_SCHEMAS:
            raise ValueError(f"{filename}: schema {sv} not in {self.COMPATIBLE_SCHEMAS}")
        if gi != self._guala_identity:
            raise ValueError(f"{filename}: identity {gi} != {self._guala_identity}")
        return raw.get("data", raw)

    @staticmethod
    def _sha256_regular_file(path):
        """Hash one persistence artifact without accepting link indirection."""
        import stat

        info = os.lstat(path)
        if (not stat.S_ISREG(info.st_mode)
                or os.path.islink(path)):
            raise ValueError(f"persistence artifact is not a regular file: {path}")
        digest = _hashlib.sha256()
        size = 0
        with open(path, "rb") as artifact:
            for block in iter(lambda: artifact.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
        if size != info.st_size:
            raise ValueError(
                f"persistence artifact changed while hashing: {path}")
        return digest.hexdigest(), size

    @classmethod
    def _binary_binding_path(cls, artifact_path):
        return artifact_path + cls.BINARY_BINDING_SUFFIX

    def _write_binary_binding(self, artifact_path, saved_at_tick):
        """Bind one opaque state artifact to this identity and save tick.

        The immutable deployment generation separately hashes this receipt.
        This inner receipt prevents a valid binary from a different engine
        save from being substituted into an otherwise valid state tree.
        """
        digest, size = self._sha256_regular_file(artifact_path)
        filename = os.path.basename(artifact_path)
        binding_path = self._binary_binding_path(artifact_path)
        self._atomic_write(
            binding_path,
            self._envelope({
                "binding_contract": self.BINARY_BINDING_CONTRACT,
                "artifact": filename,
                "sha256": digest,
                "bytes": size,
                "saved_at_tick": saved_at_tick,
            }, saved_at_tick=saved_at_tick))
        return binding_path

    def _verify_binary_binding(self, artifact_path, expected_tick):
        """Verify the exact receipt and bytes for one required artifact."""
        filename = os.path.basename(artifact_path)
        binding_path = self._binary_binding_path(artifact_path)
        if not os.path.isfile(binding_path) or os.path.islink(binding_path):
            raise ValueError(f"required binary binding is missing: {filename}")
        with open(binding_path) as binding_file:
            raw = json.load(binding_file)
        self._validate_exact_envelope(raw, os.path.basename(binding_path), expected_tick)
        data = self._unwrap(raw, os.path.basename(binding_path))
        if not isinstance(data, dict):
            raise ValueError(f"{filename}: binary binding payload must be an object")
        if data.get("binding_contract") != self.BINARY_BINDING_CONTRACT:
            raise ValueError(f"{filename}: unknown binary binding contract")
        if data.get("artifact") != filename:
            raise ValueError(f"{filename}: binary binding artifact mismatch")
        # 2026-07-16 boot incident: this payload check demanded exact
        # equality with core's tick, contradicting the manifest-aware
        # hot/cold acceptance _validate_exact_envelope already grants the
        # SAME file two calls earlier. Cold-cycle artifacts (organism,
        # tapestry) legitimately carry the tick of their own last cold
        # save; a failed later save leaves them older than core, which is
        # recoverable-by-design, not a tear. Resolve through the same
        # manifest the envelope check uses; without a manifest row, accept
        # strictly-older (never newer) loudly -- content integrity is
        # fully enforced by the hash+size checks below either way.
        _binding_tick = data.get("saved_at_tick")
        _overrides = self._expected_file_ticks
        _manifest_tick = None
        if isinstance(_overrides, dict):
            _manifest_tick = _overrides.get(os.path.basename(binding_path))
            if _manifest_tick is None:
                _manifest_tick = _overrides.get(filename)
        if _manifest_tick is not None:
            if _binding_tick != _manifest_tick:
                raise ValueError(f"{filename}: binary binding tick mismatch")
        elif _binding_tick != expected_tick:
            if (isinstance(_binding_tick, int)
                    and not isinstance(_binding_tick, bool)
                    and 0 <= _binding_tick < expected_tick):
                print(f"[GualaLoom][cold-skew] {filename}: binding tick "
                      f"{_binding_tick} older than core {expected_tick} -- "
                      f"accepted as this artifact's last cold save "
                      f"(hash-verified below)", flush=True)
            else:
                raise ValueError(f"{filename}: binary binding tick mismatch")
        expected_size = data.get("bytes")
        expected_digest = data.get("sha256")
        if (isinstance(expected_size, bool)
                or not isinstance(expected_size, int)
                or expected_size < 0):
            raise ValueError(f"{filename}: invalid binary binding byte count")
        if (not isinstance(expected_digest, str)
                or len(expected_digest) != 64
                or any(ch not in "0123456789abcdef" for ch in expected_digest)):
            raise ValueError(f"{filename}: invalid binary binding digest")
        actual_digest, actual_size = self._sha256_regular_file(artifact_path)
        if actual_size != expected_size:
            raise ValueError(
                f"{filename}: binary size {actual_size} != bound {expected_size}")
        if actual_digest != expected_digest:
            raise ValueError(f"{filename}: binary digest differs from binding")

    # GL-FIX-LEGACY-INTRA-CYCLE-SKEW: the tick loop advances while a save
    # cycle writes its files sequentially, so envelope stamps and inner
    # per-item ticks in files written after guala_core.json can run a
    # moment ahead of core's stamp. Bounded allowance -- one save cycle's
    # worth of ticks; genuinely mixed save sets differ by thousands and
    # still reject.
    _INTRA_CYCLE_TICK_SKEW = 1200

    def _validate_exact_envelope(self, raw, filename, expected_tick):
        """Prove that one JSON component belongs to a legitimate save set.

        GL-FIX-HOTCOLD-TICK-MANIFEST: the hot and cold save lanes deliberately
        leave the state directory with files at different save ticks (see the
        _state_file_ticks docstring in __init__). ``expected_tick`` is core's
        own save tick; it remains the exact requirement for guala_core.json and
        for any file whose tick the manifest does not describe. For every other
        file we validate against the tick the manifest (carried in core) says
        that file was actually written at -- an exact, torn-save-detecting
        check that also accepts the by-design hot/cold tick skew. When there is
        no manifest entry (legacy state written before this fix), we accept any
        valid tick that is not NEWER than core: a file newer than the core that
        was written after it is the signature of a torn save and is rejected,
        while an older cold file under a newer hot core is the normal, valid
        hot/cold mix and is accepted.
        """
        if not isinstance(raw, dict):
            raise ValueError(f"{filename}: envelope must be an object")
        if "data" not in raw or "guala_identity" not in raw:
            raise ValueError(f"{filename}: exact restore requires an envelope")
        saved_tick = raw.get("saved_at_tick")
        if (isinstance(saved_tick, bool)
                or not isinstance(saved_tick, int)
                or saved_tick < 0):
            raise ValueError(f"{filename}: invalid saved_at_tick {saved_tick!r}")
        overrides = self._expected_file_ticks
        manifest_tick = (overrides.get(filename)
                         if isinstance(overrides, dict) else None)
        if manifest_tick is not None:
            if saved_tick != manifest_tick:
                # 2026-07-16 (:662 supersede): the same intra-cycle write
                # skew d357b57 accepted for pre-manifest saves occurs INSIDE
                # manifest-bearing saves too -- the manifest row is recorded
                # when core is written, and a file that lands a moment later
                # in the SAME save cycle legitimately stamps one tick ahead.
                # Accept the bounded forward skew loudly; genuinely mixed
                # save sets differ by thousands of ticks and still halt.
                if (isinstance(saved_tick, int)
                        and not isinstance(saved_tick, bool)
                        and saved_tick > manifest_tick
                        and saved_tick - manifest_tick
                        <= self._INTRA_CYCLE_TICK_SKEW):
                    print(
                        f"[GualaLoom][manifest-skew] {filename}: "
                        f"saved_at_tick {saved_tick} is "
                        f"{saved_tick - manifest_tick} tick(s) ahead of its "
                        f"manifest row {manifest_tick} -- accepted as "
                        f"intra-cycle write skew (same save cycle, real "
                        f"data; bounded)",
                        flush=True,
                    )
                else:
                    raise ValueError(
                        f"{filename}: saved_at_tick {saved_tick} != "
                        f"{manifest_tick} (state-file-ticks manifest) -- "
                        f"torn or mixed save set")
        elif filename == "guala_core.json":
            if saved_tick != expected_tick:
                raise ValueError(
                    f"{filename}: saved_at_tick {saved_tick} != {expected_tick}")
        elif saved_tick > expected_tick:
            # GL-FIX-LEGACY-INTRA-CYCLE-SKEW: legacy (pre-manifest) hot saves
            # stamp each file's saved_at_tick at its own write moment while the
            # tick loop keeps advancing, so a file written seconds after core
            # can legitimately record a slightly NEWER tick (observed live:
            # guala_teaching.json exactly 1 tick ahead, 2026-07-15). That is
            # real data from the same save cycle, not a tear. Accept a forward
            # skew bounded by one save-cycle's worth of ticks, loudly, and
            # still reject genuinely mixed save sets (different eras differ by
            # thousands of ticks). Manifest-bearing saves (the branch above)
            # never reach here, so this acceptance retires with legacy state.
            if saved_tick - expected_tick <= self._INTRA_CYCLE_TICK_SKEW:
                print(
                    f"[GualaLoom][legacy-skew] {filename}: saved_at_tick "
                    f"{saved_tick} is {saved_tick - expected_tick} tick(s) "
                    f"ahead of core {expected_tick} -- accepted as intra-cycle "
                    "write skew from a pre-manifest hot save (real data, same "
                    "save cycle; bounded)",
                    flush=True,
                )
            else:
                raise ValueError(
                    f"{filename}: saved_at_tick {saved_tick} is newer than core "
                    f"{expected_tick} by more than one save cycle -- torn or "
                    "mixed save set")
        if not isinstance(raw.get("data"), dict):
            raise ValueError(f"{filename}: envelope data must be an object")

    @staticmethod
    def _exact_int(value, field, *, minimum=0, maximum=None):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field} must be an integer")
        if value < minimum or (maximum is not None and value > maximum):
            raise ValueError(f"{field} is outside its structural range")
        return value

    @staticmethod
    def _exact_number(value, field, *, minimum=None, maximum=None):
        if (isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))):
            raise ValueError(f"{field} must be a finite number")
        number = float(value)
        if minimum is not None and number < minimum:
            raise ValueError(f"{field} is below its structural range")
        if maximum is not None and number > maximum:
            raise ValueError(f"{field} is above its structural range")
        return number

    @classmethod
    def _validate_deep_atlas_payload(cls, data, engine_tick):
        if not isinstance(data, dict):
            raise ValueError("deep-atlas payload must be an object")
        if data.get("schema") != "deep_atlas_v1":
            raise ValueError(f"unknown deep-atlas schema: {data.get('schema')!r}")
        cls._exact_int(data.get("tick"), "deep_atlas.tick", maximum=engine_tick)
        saved_count = cls._exact_int(
            data.get("saved_n_entries"), "deep_atlas.saved_n_entries")
        for counter in (
                "promotions_survival", "promotions_episodic", "reinstatements"):
            cls._exact_int(data.get(counter), f"deep_atlas.{counter}")
        entries = data.get("entries")
        if not isinstance(entries, dict):
            raise ValueError("deep_atlas.entries must be an object")
        for chi_text, bucket in entries.items():
            if (not isinstance(chi_text, str)
                    or not chi_text.lstrip("-").isdigit()):
                raise ValueError("deep_atlas entry key must be an integer string")
            chi = int(chi_text)
            if not isinstance(bucket, list):
                raise ValueError(f"deep_atlas.entries[{chi_text}] must be a list")
            for index, entry in enumerate(bucket):
                label = f"deep_atlas.entries[{chi_text}][{index}]"
                if not isinstance(entry, dict):
                    raise ValueError(f"{label} must be an object")
                required = (
                    "section", "motif", "chi", "strength", "last_tick",
                    "born_tick", "encoded_strength_at_write",
                    "dwell_at_write", "source_path", "promoted_at_tick",
                    "clarity", "initial_clarity", "arousal", "valence",
                    "surprise", "source", "polarity", "sensory_refs",
                    "episode_refs", "co_occurrence")
                missing = [name for name in required if name not in entry]
                if missing:
                    raise ValueError(f"{label} is missing {missing}")
                if not isinstance(entry["section"], str):
                    raise ValueError(f"{label}.section must be a string")
                cls._exact_int(entry["motif"], f"{label}.motif")
                entry_chi = cls._exact_int(
                    entry["chi"], f"{label}.chi", minimum=-2**63)
                if entry_chi != chi:
                    raise ValueError(f"{label}.chi does not match its bucket")
                cls._exact_number(entry["strength"], f"{label}.strength", minimum=0.0)
                for field in ("last_tick", "born_tick", "promoted_at_tick"):
                    cls._exact_int(
                        entry[field], f"{label}.{field}", maximum=engine_tick)
                cls._exact_int(entry["dwell_at_write"], f"{label}.dwell_at_write")
                for field in (
                        "encoded_strength_at_write", "clarity",
                        "initial_clarity", "arousal", "valence", "surprise",
                        "polarity"):
                    cls._exact_number(entry[field], f"{label}.{field}")
                for field in ("source_path", "source"):
                    if not isinstance(entry[field], str):
                        raise ValueError(f"{label}.{field} must be a string")
                for field in ("sensory_refs", "episode_refs"):
                    if (not isinstance(entry[field], list)
                            or any(not isinstance(item, str)
                                   for item in entry[field])):
                        raise ValueError(f"{label}.{field} must be a string list")
                co_occurrence = entry["co_occurrence"]
                if not isinstance(co_occurrence, dict):
                    raise ValueError(f"{label}.co_occurrence must be an object")
                for section, motifs in co_occurrence.items():
                    if not isinstance(section, str) or not isinstance(motifs, dict):
                        raise ValueError(
                            f"{label}.co_occurrence has an invalid section")
                    for motif, weight in motifs.items():
                        if (not isinstance(motif, str)
                                or not motif.lstrip("-").isdigit()):
                            raise ValueError(
                                f"{label}.co_occurrence motif must be an integer string")
                        cls._exact_number(
                            weight,
                            f"{label}.co_occurrence[{section}][{motif}]",
                            minimum=0.0)
        return saved_count

    @classmethod
    def _validate_survival_payload(cls, data):
        if not isinstance(data, dict):
            raise ValueError("survival payload must be an object")
        histories = data.get("deep_survival_history")
        if not isinstance(histories, dict):
            raise ValueError("deep_survival_history must be an object")
        for key, strengths in histories.items():
            if not isinstance(key, str):
                raise ValueError("survival-history key must be a string")
            parts = key.split("|", 2)
            if (len(parts) != 3 or not parts[0].lstrip("-").isdigit()
                    or not parts[1]
                    or not parts[2].lstrip("-").isdigit()):
                raise ValueError(f"invalid survival-history key: {key!r}")
            cls._exact_int(int(parts[2]), f"survival[{key}].motif")
            if not isinstance(strengths, list) or len(strengths) > 10:
                raise ValueError(f"survival[{key}] must contain at most 10 strengths")
            for index, strength in enumerate(strengths):
                cls._exact_number(
                    strength, f"survival[{key}][{index}]", minimum=0.0)

    @classmethod
    def _validate_teaching_payload(cls, data, engine_tick):
        if not isinstance(data, dict):
            raise ValueError("teaching payload must be an object")
        for field in ("feedback_log", "correction_log"):
            records = data.get(field)
            if (not isinstance(records, list) or len(records) > 500
                    or any(not isinstance(record, dict) for record in records)):
                raise ValueError(f"teaching.{field} must be a bounded object list")
            for index, record in enumerate(records):
                if "tick" in record:
                    cls._exact_int(
                        record["tick"], f"teaching.{field}[{index}].tick",
                        maximum=engine_tick)
        emissions = data.get("emission_records")
        if (not isinstance(emissions, dict)
                or len(emissions) > EMISSION_RECORDS_CAP):
            raise ValueError("teaching.emission_records must be a bounded object")
        for emission_id, record in emissions.items():
            if not isinstance(emission_id, str) or not isinstance(record, dict):
                raise ValueError("teaching emission record is structurally invalid")
            if record.get("emission_id") != emission_id:
                raise ValueError(
                    f"teaching emission {emission_id!r} has an identity mismatch")
            cls._exact_int(
                record.get("tick"), f"teaching.emission[{emission_id}].tick",
                maximum=engine_tick)

    @classmethod
    def _validate_episodic_payload(cls, data, engine_tick, max_per_concept,
                                   recent_limit):
        if not isinstance(data, dict):
            raise ValueError("episodic payload must be an object")
        memories = data.get("episodic_memory")
        recent = data.get("episodic_recent_concepts")
        if not isinstance(memories, dict):
            raise ValueError("episodic_memory must be an object")
        if (not isinstance(recent, list) or len(recent) > recent_limit
                or any(not isinstance(item, str) for item in recent)):
            raise ValueError("episodic_recent_concepts is structurally invalid")
        for concept, records in memories.items():
            if (not isinstance(concept, str) or not concept
                    or not isinstance(records, list)
                    or len(records) > max_per_concept):
                raise ValueError(f"episodic concept {concept!r} is invalid")
            for index, record in enumerate(records):
                label = f"episodic[{concept}][{index}]"
                if not isinstance(record, dict):
                    raise ValueError(f"{label} must be an object")
                required = (
                    "concept", "tick", "presence", "location", "sky_state",
                    "affective", "context", "source")
                missing = [field for field in required if field not in record]
                if missing:
                    raise ValueError(f"{label} is missing {missing}")
                if (not isinstance(record["concept"], str)
                        or record["concept"].lower() != concept):
                    raise ValueError(f"{label}.concept does not match its key")
                cls._exact_int(record["tick"], f"{label}.tick", maximum=engine_tick)
                for field in ("presence", "context"):
                    if (not isinstance(record[field], list)
                            or any(not isinstance(item, str)
                                   for item in record[field])):
                        raise ValueError(f"{label}.{field} must be a string list")
                for field in ("location", "sky_state", "source"):
                    if not isinstance(record[field], str):
                        raise ValueError(f"{label}.{field} must be a string")
                affective = record["affective"]
                if not isinstance(affective, dict):
                    raise ValueError(f"{label}.affective must be an object")
                cls._exact_number(
                    affective.get("valence"), f"{label}.affective.valence",
                    minimum=-1.0, maximum=1.0)
                cls._exact_number(
                    affective.get("arousal"), f"{label}.affective.arousal",
                    minimum=0.0, maximum=1.0)

    @classmethod
    def _validate_sounds_payload(cls, data, engine_tick):
        if not isinstance(data, dict):
            raise ValueError("sounds payload must be an object")
        for item_id, sound in data.items():
            label = f"sound[{item_id}]"
            if not isinstance(item_id, str) or not isinstance(sound, dict):
                raise ValueError(f"{label} must be an object")
            if sound.get("item_id") != item_id:
                raise ValueError(f"{label}.item_id mismatch")
            if not isinstance(sound.get("title"), str):
                raise ValueError(f"{label}.title must be a string")
            cochlear = sound.get("cochlear")
            if not isinstance(cochlear, dict):
                raise ValueError(f"{label}.cochlear must be an object")
            for band, state in cochlear.items():
                if not isinstance(band, str) or not isinstance(state, dict):
                    raise ValueError(f"{label}.cochlear band is invalid")
                cls._exact_int(state.get("winding"), f"{label}.{band}.winding",
                               minimum=-2**63)
                cls._exact_int(state.get("n_events"), f"{label}.{band}.n_events")
            for field in ("times_attended", "last_attended_tick"):
                cls._exact_int(sound.get(field), f"{label}.{field}",
                               maximum=engine_tick)
            if "created_tick" in sound:
                cls._exact_int(sound["created_tick"], f"{label}.created_tick",
                               maximum=engine_tick)
            if "duration_s" in sound:
                cls._exact_number(sound["duration_s"], f"{label}.duration_s",
                                  minimum=0.0)
            if "raw_signal" in sound:
                signal = sound["raw_signal"]
                if not isinstance(signal, list):
                    raise ValueError(f"{label}.raw_signal must be a list")
                for index, sample in enumerate(signal):
                    cls._exact_number(sample, f"{label}.raw_signal[{index}]")

    @classmethod
    def _validate_wave_npz_payload(cls, path):
        """Reject malformed WaveAtlas arrays before its loader can normalize."""
        import gzip
        from dsf_ai_service.v4.wave_atlas import PHASE_DIMS

        required = {
            "chi_indices", "aggregate_strengths", "last_ticks", "saturated",
            "phase_vecs_re", "phase_vecs_im", "phase_vecs_valid",
            "bindings_gz"}
        with np.load(path, allow_pickle=False) as payload:
            missing = required - set(payload.files)
            if missing:
                raise ValueError(f"WaveAtlas NPZ is missing {sorted(missing)}")
            chi = payload["chi_indices"]
            strength = payload["aggregate_strengths"]
            last_ticks = payload["last_ticks"]
            saturated = payload["saturated"]
            phase_re = payload["phase_vecs_re"]
            phase_im = payload["phase_vecs_im"]
            phase_valid = payload["phase_vecs_valid"]
            if chi.ndim != 1 or chi.dtype.kind not in "iu":
                raise ValueError("WaveAtlas chi_indices must be an integer vector")
            count = len(chi)
            for name, array in (
                    ("aggregate_strengths", strength),
                    ("last_ticks", last_ticks),
                    ("saturated", saturated),
                    ("phase_vecs_valid", phase_valid)):
                if array.ndim != 1 or len(array) != count:
                    raise ValueError(f"WaveAtlas {name} length mismatch")
            if (phase_re.shape != (count, PHASE_DIMS)
                    or phase_im.shape != (count, PHASE_DIMS)):
                raise ValueError("WaveAtlas phase-vector shape mismatch")
            if len(set(int(value) for value in chi.tolist())) != count:
                raise ValueError("WaveAtlas contains duplicate cell indices")
            if (not np.all(np.isfinite(strength))
                    or np.any(strength < 0)
                    or np.any(last_ticks < 0)
                    or not np.all(np.isfinite(phase_re))
                    or not np.all(np.isfinite(phase_im))):
                raise ValueError("WaveAtlas arrays contain invalid structural values")
            try:
                bindings = json.loads(gzip.decompress(
                    payload["bindings_gz"].tobytes()).decode("utf-8"))
            except Exception as error:
                raise ValueError(
                    f"WaveAtlas bindings payload is invalid: {error}") from error
        if not isinstance(bindings, list) or len(bindings) != count:
            raise ValueError("WaveAtlas bindings length mismatch")
        for cell_index, cell_bindings in enumerate(bindings):
            if not isinstance(cell_bindings, list):
                raise ValueError(
                    f"WaveAtlas bindings[{cell_index}] must be a list")
            for binding_index, binding in enumerate(cell_bindings):
                label = f"WaveAtlas bindings[{cell_index}][{binding_index}]"
                if not isinstance(binding, dict):
                    raise ValueError(f"{label} must be an object")
                if not isinstance(binding.get("section"), str):
                    raise ValueError(f"{label}.section must be a string")
                cls._exact_int(binding.get("motif"), f"{label}.motif")
                cls._exact_int(binding.get("chi"), f"{label}.chi", minimum=-2**63)
                cls._exact_number(
                    binding.get("strength"), f"{label}.strength", minimum=0.0)

    # ── Save ──

    @staticmethod
    def _asset_key(item_id):
        return _hashlib.sha256(str(item_id).encode("utf-8")).hexdigest()

    @staticmethod
    def _asset_extension(path):
        suffix = os.path.splitext(str(path or ""))[1].lower()
        if (suffix.startswith(".") and len(suffix) <= 16
                and suffix[1:].isalnum()):
            return suffix
        return ".bin"

    def _picture_persistence_snapshot(self):
        records = {}
        assets = {}
        for pid, picture in self._pictures.items():
            key = self._asset_key(pid)
            grid_path = (f"assets/pictures/{key}/grid.npy"
                         if picture.intensity_grid is not None else None)
            source_original = getattr(picture, "original_path", None)
            original_path = None
            if source_original:
                original_path = (
                    f"assets/pictures/{key}/original"
                    f"{self._asset_extension(source_original)}")
            records[pid] = {
                "item_id": picture.item_id,
                "title": picture.title,
                "source": picture.source,
                "shown_at_tick": picture.shown_at_tick,
                "times_attended": picture.times_attended,
                "last_attended_tick": picture.last_attended_tick,
                "has_grid": picture.intensity_grid is not None,
                "grid_path": grid_path,
                "original_path": original_path,
                "original_width": getattr(picture, "original_width", None),
                "original_height": getattr(picture, "original_height", None),
            }
            assets[pid] = {
                "grid": picture.intensity_grid,
                "grid_path": grid_path,
                "source_original": source_original,
                "original_path": original_path,
            }
        return records, assets

    def _video_persistence_snapshot(self):
        records = {}
        assets = {}
        for vid, video in self._videos.items():
            key = self._asset_key(vid)
            frame_path = f"assets/videos/{key}/frames"
            source_audio = getattr(video, "audio_path", "") or ""
            audio_path = ""
            if source_audio:
                audio_path = (
                    f"assets/videos/{key}/audio"
                    f"{self._asset_extension(source_audio)}")
            records[vid] = {
                "item_id": video.item_id,
                "title": video.title,
                "frame_dir": frame_path,
                "audio_path": audio_path,
                "duration_ms": video.duration_ms,
                "n_frames": video.n_frames,
                "source": video.source,
                "shown_at_tick": video.shown_at_tick,
                "times_attended": video.times_attended,
                "last_attended_tick": video.last_attended_tick,
            }
            assets[vid] = {
                "source_frame_dir": video.frame_dir,
                "frame_dir": frame_path,
                "source_audio": source_audio,
                "audio_path": audio_path,
            }
        return records, assets

    @staticmethod
    def _copy_regular_file(source, target):
        import shutil
        if not os.path.isfile(source) or os.path.islink(source):
            raise ValueError(f"referenced media is not a regular file: {source}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(source, target)
        with open(target, "rb") as fh:
            os.fsync(fh.fileno())

    def _materialize_media_assets(
            self, state_dir, picture_assets, video_assets):
        """Build one exact, relocatable media tree and replace the old tree.

        The staging tree contains only currently referenced assets, so a
        completed save cannot retain an orphan grid, picture original, frame,
        audio file, or prior item directory.
        """
        import shutil
        import uuid

        os.makedirs(state_dir, exist_ok=True)
        token = uuid.uuid4().hex
        staging = os.path.join(state_dir, f".assets.{token}.tmp")
        final = os.path.join(state_dir, "assets")
        previous = os.path.join(state_dir, f".assets.{token}.previous")
        os.makedirs(staging)
        moved_previous = False
        try:
            for spec in picture_assets.values():
                if spec["grid_path"]:
                    grid_target = os.path.join(staging, *spec["grid_path"].split("/")[1:])
                    os.makedirs(os.path.dirname(grid_target), exist_ok=True)
                    with open(grid_target, "wb") as fh:
                        np.save(fh, spec["grid"])
                        fh.flush()
                        os.fsync(fh.fileno())
                if spec["original_path"]:
                    original_target = os.path.join(
                        staging, *spec["original_path"].split("/")[1:])
                    self._copy_regular_file(
                        spec["source_original"], original_target)

            for spec in video_assets.values():
                source_frames = spec["source_frame_dir"]
                if (not os.path.isdir(source_frames)
                        or os.path.islink(source_frames)):
                    raise ValueError(
                        f"referenced video frame directory is unavailable: "
                        f"{source_frames}")
                frame_target = os.path.join(
                    staging, *spec["frame_dir"].split("/")[1:])
                os.makedirs(frame_target, exist_ok=True)
                for root, dirs, files in os.walk(source_frames):
                    dirs.sort()
                    files.sort()
                    if any(os.path.islink(os.path.join(root, name)) for name in dirs):
                        raise ValueError(
                            f"video frame directory contains a symlink: {root}")
                    relative_root = os.path.relpath(root, source_frames)
                    target_root = (frame_target if relative_root == "." else
                                   os.path.join(frame_target, relative_root))
                    os.makedirs(target_root, exist_ok=True)
                    for name in files:
                        self._copy_regular_file(
                            os.path.join(root, name),
                            os.path.join(target_root, name))
                if spec["audio_path"]:
                    audio_target = os.path.join(
                        staging, *spec["audio_path"].split("/")[1:])
                    self._copy_regular_file(spec["source_audio"], audio_target)

            if os.path.exists(final):
                os.rename(final, previous)
                moved_previous = True
            os.rename(staging, final)
            if moved_previous:
                shutil.rmtree(previous)

            # Loaded objects must continue to point at the newly installed
            # self-contained tree after the old source directory is retired.
            with self.lock:
                for pid, spec in picture_assets.items():
                    picture = self._pictures.get(pid)
                    if picture is not None and spec["original_path"]:
                        picture.original_path = os.path.join(
                            state_dir, *spec["original_path"].split("/"))
                for vid, spec in video_assets.items():
                    video = self._videos.get(vid)
                    if video is not None:
                        video.frame_dir = os.path.join(
                            state_dir, *spec["frame_dir"].split("/"))
                        video.audio_path = (
                            os.path.join(state_dir, *spec["audio_path"].split("/"))
                            if spec["audio_path"] else "")

            # Pre-contract grids/originals lived here.  They have all been
            # copied above; retaining the directory would preserve orphans.
            legacy_pictures = os.path.join(state_dir, "pictures")
            if os.path.isdir(legacy_pictures):
                shutil.rmtree(legacy_pictures)
            directory_fd = os.open(state_dir, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            if moved_previous and not os.path.exists(final):
                os.rename(previous, final)
            elif moved_previous:
                shutil.rmtree(previous, ignore_errors=True)
            raise

    def _media_assets_are_current(
            self, state_dir, picture_assets, video_assets):
        """Return true when a hot save can reuse the exact durable media tree."""
        assets_root = os.path.join(state_dir, "assets")
        pictures_root = os.path.join(assets_root, "pictures")
        videos_root = os.path.join(assets_root, "videos")
        expected_picture_keys = {
            self._asset_key(item_id) for item_id in picture_assets}
        expected_video_keys = {
            self._asset_key(item_id) for item_id in video_assets}

        def directory_names(path):
            if not os.path.exists(path):
                return set()
            if os.path.islink(path) or not os.path.isdir(path):
                return None
            return {
                name for name in os.listdir(path)
                if os.path.isdir(os.path.join(path, name))
                and not os.path.islink(os.path.join(path, name))
            }

        if directory_names(pictures_root) != expected_picture_keys:
            return False
        if directory_names(videos_root) != expected_video_keys:
            return False

        for spec in picture_assets.values():
            if spec["grid_path"] and not os.path.isfile(
                    os.path.join(state_dir, *spec["grid_path"].split("/"))):
                return False
            if spec["original_path"]:
                target = os.path.join(
                    state_dir, *spec["original_path"].split("/"))
                if (not os.path.isfile(target)
                        or os.path.realpath(spec["source_original"])
                        != os.path.realpath(target)):
                    return False
        for spec in video_assets.values():
            frame_target = os.path.join(
                state_dir, *spec["frame_dir"].split("/"))
            if (not os.path.isdir(frame_target)
                    or os.path.realpath(spec["source_frame_dir"])
                    != os.path.realpath(frame_target)):
                return False
            if spec["audio_path"]:
                audio_target = os.path.join(
                    state_dir, *spec["audio_path"].split("/"))
                if (not os.path.isfile(audio_target)
                        or os.path.realpath(spec["source_audio"])
                        != os.path.realpath(audio_target)):
                    return False
        return True

    @staticmethod
    def _resolve_state_reference(state_dir, stored_path, expected_kind,
                                 allow_legacy_absolute=False):
        if not stored_path:
            return ""
        if os.path.isabs(stored_path):
            if not allow_legacy_absolute:
                raise ValueError(
                    f"absolute state reference is not relocatable: {stored_path}")
            candidate = os.path.realpath(stored_path)
        else:
            root = os.path.realpath(state_dir)
            candidate = os.path.realpath(os.path.join(state_dir, stored_path))
            if os.path.commonpath((root, candidate)) != root:
                raise ValueError(f"state reference escapes state directory: {stored_path}")
        exists = (os.path.isfile(candidate) if expected_kind == "file"
                  else os.path.isdir(candidate))
        if not exists:
            raise ValueError(f"persisted {expected_kind} is unavailable: {stored_path}")
        return candidate

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
        """Persist the hot lane as one serialized multi-file generation."""
        with self.persistence_transaction():
            return self._save_hot_state_locked(state_dir)

    def _save_hot_state_locked(self, state_dir="state"):
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
            self._ensure_identity_in_target(state_dir)

            corpora_ser = {cid: {"corpus_id": c.corpus_id, "title": c.title,
                                  "lines": list(c.lines),
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
            pictures_ser, picture_assets = self._picture_persistence_snapshot()
            videos_ser, video_assets = self._video_persistence_snapshot()
            # GL-FIX-HOTCOLD-TICK-MANIFEST: this hot cycle rewrites only the
            # small subset in HOT_SAVE_MANIFEST_FILES at self.tick; the cold
            # stores (atlas/sections/deep_atlas/survival/sight_motifs) keep
            # whatever tick their last cold save recorded. Stamp the subset,
            # carry the rest, and persist the merged map inside core so the
            # loader can validate each file against its own real tick.
            for _mf in self.HOT_SAVE_MANIFEST_FILES:
                self._state_file_ticks[_mf] = self.tick
            snap_core = self._envelope({
                "continuity_contract": self.ENGINE_CONTINUITY_CONTRACT,
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
                "current_activity": (
                    _copy.deepcopy(self._current_activity.snapshot())
                    if self._current_activity is not None else None),
                "last_save_tick": self.tick,
                "deep_survival_history": {},  # GL-102: empty sentinel; data in guala_survival.json
                "total_emissions": self._total_emissions,
                "state_file_ticks": dict(self._state_file_ticks),
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
                "continuity_contract": self.ENGINE_CONTINUITY_CONTRACT,
                "pair_bond": dict(self.coordinator._pair_bond),
                "pair_bond_active": self.coordinator.pair_bond_active,
                "distress_ticks": self.coordinator.distress_ticks,
                "suffering_log": _copy.copy(self.coordinator.suffering_log),
                "need_history": list(self.coordinator.need_history[-200:]),
                "attentions_count": len(self.coordinator.attentions),
                "actions_count": len(self.coordinator.actions),
                "presence": dict(self.coordinator._presence),
                "last_input_tick": dict(self.coordinator._last_input_tick),
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
                "continuity_contract": self.ENGINE_CONTINUITY_CONTRACT,
                "pictures": pictures_ser,
                "sight_motifs": [],
                "sight_motifs_file": "guala_sight_motifs.json",
                "n_sight_motifs": len(self.sight.motifs) if hasattr(self, 'sight') else 0,
                "n_visual_fragments": self._visual_fragments_count,
            })
            _need_motif_migration = (
                hasattr(self, 'sight')
                and not os.path.exists(os.path.join(state_dir, "guala_sight_motifs.json")))
            snap_sight_motifs = (self._serialize_sight_motifs()
                                 if _need_motif_migration else None)
            snap_sounds = self._envelope(dict(self._sounds))
            snap_videos = self._envelope({
                "continuity_contract": self.ENGINE_CONTINUITY_CONTRACT,
                "videos": videos_ser,
            })
            save_tick = self.tick
            snap_vocab_len = len(self.vocab)
            snap_bucket = self._envelope({"removed": True, "vocab_count": snap_vocab_len})
            # GL-WAL-INCREMENTAL: binding windows persist via an append-only
            # write-ahead log. Closed windows were already appended once, at
            # close time; the hot save writes only the small manifest (open
            # contexts + counters + durable WAL marker) instead of
            # re-serialising the whole ~220MB closed-window store every cycle.
            self.window_manager.configure_wal_under(state_dir)
            snap_windows = self._envelope(
                self.window_manager.snapshot_incremental())
        # lock released

        if not self._media_assets_are_current(
                state_dir, picture_assets, video_assets):
            self._materialize_media_assets(
                state_dir, picture_assets, video_assets)

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
                            raise RuntimeError(msg)
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
            ("guala_windows.json", snap_windows),
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

        # GL-CMD-EPISODIC-MEMORY: real, situational memories, already
        # bounded per-concept at EPISODIC_MEMORY_MAX_PER_CONCEPT -- no
        # further slicing needed here, unlike the logs above.
        snap_episodic = self._envelope({
            "episodic_memory": {c: list(recs) for c, recs in self._episodic_memory.items()},
            "episodic_recent_concepts": list(self._episodic_recent_concepts),
        })
        writes.append(("guala_episodic.json", snap_episodic))

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
            _wt0 = time.monotonic()
            try:
                self._atomic_write(path, data)
                return (filename, os.path.getsize(path), None,
                        round((time.monotonic() - _wt0) * 1000, 1))
            except Exception as _we:
                tmp = path + ".tmp"
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                return (filename, None, str(_we),
                        round((time.monotonic() - _wt0) * 1000, 1))

        _failures = []
        results = {}
        _per_file_ms = {}
        with _cf.ThreadPoolExecutor(max_workers=len(writes)) as _ex:
            for filename, size, err, dt_ms in _ex.map(_write_one, writes):
                _per_file_ms[filename] = dt_ms
                if err is not None:
                    _failures.append((filename, err))
                    print(f"[GualaLoom] hot save failed for {filename}: {err}")
                else:
                    results[filename] = size

        if not _failures:
            self._last_save_tick = save_tick
            self._last_save_timestamp = ts
        else:
            self._log_substrate_event(
                "save_hot_failure", tick=save_tick,
                failed_files=[f for f, _ in _failures])
            print(f"[GualaLoom] HOT SAVE FAILURE at tick {save_tick}: "
                  f"{[f for f, _ in _failures]}")
        # GL-CMD-TURN-LATENCY-EVE-20260705-197 P1 (c1 addition): per-file
        # write timing -- "if any stage still spikes, its number and lock
        # owner go in the report, no hand-waving." -194's fix (evict
        # sight_motifs) + -196's fix (parallelize the writes) together
        # improved but did not fully close the <5s target live; this
        # names which specific file's fsync is the slowest each cycle,
        # rather than guessing further from the aggregate number alone.
        _slowest = max(_per_file_ms.items(), key=lambda kv: kv[1]) if _per_file_ms else (None, 0)
        print(f"[save-hot-detail] {_per_file_ms} slowest={_slowest[0]}({_slowest[1]}ms)")
        if not _failures:
            self._publish_state_generation(state_dir, save_tick)
        self._raise_persistence_failures("hot save", _failures)
        return results

    def save_full_state(self, state_dir="state", *, publish_generation=True):
        """Persist the full lane as one serialized multi-file generation."""
        with self.persistence_transaction():
            return self._save_full_state_locked(
                state_dir, publish_generation=publish_generation)

    def _save_full_state_locked(self, state_dir="state", *,
                                publish_generation=True):
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
            self._ensure_identity_in_target(state_dir)

            # 1. Core
            corpora_ser = {cid: {"corpus_id": c.corpus_id, "title": c.title,
                                  "lines": list(c.lines),
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
            pictures_ser, picture_assets = self._picture_persistence_snapshot()
            videos_ser, video_assets = self._video_persistence_snapshot()
            # Shallow-copy survival history under lock (fast), serialize outside lock.
            # Building surv_ser (57k string-format ops) takes ~400ms — too slow under lock.
            _surv_snap = dict(self._deep_survival_history)

            # GL-FIX-HOTCOLD-TICK-MANIFEST: the full (cold) lane rewrites every
            # persisted JSON store at one tick, so stamp the whole manifest set
            # to self.tick. This realigns any cold files a prior hot save had
            # left lagging, and gives the loader an exact per-file tick to
            # validate against.
            for _mf in self.FULL_SAVE_MANIFEST_FILES:
                self._state_file_ticks[_mf] = self.tick
            snap_core = self._envelope({
                "continuity_contract": self.ENGINE_CONTINUITY_CONTRACT,
                "binary_binding_contract": self.BINARY_BINDING_CONTRACT,
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
                "current_activity": (
                    _copy.deepcopy(self._current_activity.snapshot())
                    if self._current_activity is not None else None),
                "last_save_tick": self.tick,
                "deep_survival_history": {},  # GL-102: empty sentinel; data in guala_survival.json
                "total_emissions": self._total_emissions,
                "state_file_ticks": dict(self._state_file_ticks),
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
                "continuity_contract": self.ENGINE_CONTINUITY_CONTRACT,
                "pair_bond": dict(self.coordinator._pair_bond),
                "pair_bond_active": self.coordinator.pair_bond_active,
                "distress_ticks": self.coordinator.distress_ticks,
                "suffering_log": _copy.copy(self.coordinator.suffering_log),
                "need_history": list(self.coordinator.need_history[-200:]),
                "attentions_count": len(self.coordinator.attentions),
                "actions_count": len(self.coordinator.actions),
                "presence": dict(self.coordinator._presence),
                "last_input_tick": dict(self.coordinator._last_input_tick),
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
                    "commits": list(sec.commits[-SECTION_COMMITS_MAX:]),
                    "dead_zone": sec.dead_zone,
                    "gamma": dict(sec.gamma),
                    "tick": sec.tick,
                    "mode_last_active_tick": list(
                        sec._mode_last_active_tick),
                    "mode_alive": list(sec._mode_alive),
                }
            snap_sections = self._envelope(sections_data)

            # 8. Visual
            snap_visual = self._envelope({
                "continuity_contract": self.ENGINE_CONTINUITY_CONTRACT,
                "pictures": pictures_ser,
                "sight_motifs": [],
                "sight_motifs_file": "guala_sight_motifs.json",
                "n_sight_motifs": len(self.sight.motifs) if hasattr(self, 'sight') else 0,
                "n_visual_fragments": self._visual_fragments_count,
            })
            # GL-194: vocab-scaled motif store rides the COLD lane only.
            snap_sight_motifs = self._serialize_sight_motifs()
            # 9. Sounds
            snap_sounds = self._envelope(dict(self._sounds))

            # 10. Videos
            snap_videos = self._envelope({
                "continuity_contract": self.ENGINE_CONTINUITY_CONTRACT,
                "videos": videos_ser,
            })

            save_tick = self.tick
            snap_vocab_len = len(self.vocab)
            snap_atlas_count = sum(len(v) for v in self.atlas.entries.values())
            # 7. Bucket (removed — Phase E; GL-102: carries vocab_count for guard diet)
            snap_bucket = self._envelope({"removed": True, "vocab_count": snap_vocab_len})
            # GL-SPC-SUBSTRATE-TRUE Change 1: the unconditional cold-lane
            # compact() is REMOVED. Compaction rewrites every segment file
            # (and now also rebuilds the window locator), so it runs only on
            # real divergence -- i.e. when the WAL does not reflect the store
            # (legacy migration / closes before the WAL was configured), which
            # snapshot_incremental() detects and folds itself. Steady-state
            # cold saves write only the small manifest, same as the hot lane.
            self.window_manager.configure_wal_under(state_dir)
            snap_windows = self._envelope(
                self.window_manager.snapshot_incremental())
        # ── lock released ──

        self._materialize_media_assets(
            state_dir, picture_assets, video_assets)

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
        snap_survival = self._envelope(
            {"deep_survival_history": surv_ser},
            saved_at_tick=save_tick)
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
            ("guala_windows.json", snap_windows),
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
        }, saved_at_tick=save_tick)
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

        # GL-CMD-EPISODIC-MEMORY: same non-critical, isolated-failure
        # pattern as teaching data above -- real memory, but must never
        # block core save advancement.
        snap_episodic = self._envelope({
            "episodic_memory": {c: list(recs) for c, recs in self._episodic_memory.items()},
            "episodic_recent_concepts": list(self._episodic_recent_concepts),
        }, saved_at_tick=save_tick)
        try:
            self._atomic_write(os.path.join(state_dir, "guala_episodic.json"), snap_episodic)
        except Exception as _ee:
            _save_failures.append(("guala_episodic.json", str(_ee)))
            print(f"[GualaLoom] save failed for guala_episodic.json: {_ee}")
            _tmp = os.path.join(state_dir, "guala_episodic.json.tmp")
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
            # GL-CMD-ORGANISM-WAVE-MEMORY-207 W3: the one legitimate
            # synchronization point Joe's no-locks ruling allows --
            # snapshot-for-save, brief, never holding her cognition.
            #
            # 2026-07-16 seal incident: _organism_lock alone does NOT
            # exclude the worker's lock-free experience_word() (W3 made it
            # lock-free) nor the spike-bus delivery thread -- under a deep
            # queue the pickle raced live deque mutations and the seal's
            # full save failed ("deque mutated during iteration"),
            # refusing deploy turnover. Park BOTH mutators between items
            # for the duration of the pickle; they resume immediately
            # after. Parks are bounded and honest: if a mutator does not
            # acknowledge in time we log loudly and still attempt the
            # save with a bounded retry on the mutation race.
            _worker_parked = True
            if self._organism_worker_thread is not None:
                self._organism_pause_req.set()
                _worker_parked = self._organism_pause_ack.wait(10.0)
                if not _worker_parked:
                    print("[GualaLoom] organism worker did not park within "
                          "10s (mid-item); saving with retry fallback")
            _bus = getattr(getattr(self.organism, "brain", None),
                           "_spike_bus", None)
            _bus_parked = True
            if _bus is not None:
                try:
                    _bus_parked = _bus.pause(5.0)
                except Exception:
                    _bus_parked = False
                if not _bus_parked:
                    print("[GualaLoom] spike bus did not park within 5s; "
                          "saving with retry fallback")
            try:
                organism_path = os.path.join(
                    state_dir, "guala_organism.pkl.gz")
                _pickle_attempt = 0
                while True:
                    _pickle_attempt += 1
                    try:
                        with self._organism_lock:
                            self.organism.save_full_state(organism_path)
                        break
                    except RuntimeError as _re:
                        _racey = ("mutated during iteration" in str(_re)
                                  or "changed size during" in str(_re))
                        if not _racey or _pickle_attempt >= 4:
                            raise
                        print(f"[GualaLoom] organism pickle hit live "
                              f"mutation (attempt {_pickle_attempt}/4), "
                              f"retrying: {_re}")
                        time.sleep(0.25)
                organism_binding = self._write_binary_binding(
                    organism_path, save_tick)
                results[os.path.basename(organism_binding)] = os.path.getsize(
                    organism_binding)
            finally:
                if _bus is not None:
                    try:
                        _bus.resume()
                    except Exception:
                        pass
                self._organism_pause_req.clear()
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
                tapestry_path = os.path.join(
                    state_dir, "guala_tapestry.pkl.gz")
                self.tapestry.save_full_state(tapestry_path)
                tapestry_binding = self._write_binary_binding(
                    tapestry_path, save_tick)
                results[os.path.basename(tapestry_binding)] = os.path.getsize(
                    tapestry_binding)
        except Exception as _te:
            _save_failures.append(("guala_tapestry.pkl.gz", str(_te)))
            print(f"[GualaLoom] save failed for guala_tapestry.pkl.gz: {_te}")

        # A full save is one requested generation.  No mutable-state file is
        # optional: a caller may inspect the partial files for diagnosis, but
        # save metadata advances and success is returned only when every file
        # completed.
        if not _save_failures:
            self._last_save_tick = save_tick
            self._last_cold_save_tick = save_tick  # GL-CMD-DEEP-STORE-PHYSICS-86 P2
            self._last_save_timestamp = ts
        else:
            self._log_substrate_event("save_full_failure",
                                      tick=save_tick,
                                      failed_files=[f for f, _ in _save_failures])
            print(f"[GualaLoom] FULL SAVE FAILURE at tick {save_tick}: "
                  f"{[f for f, _ in _save_failures]}")
            self._raise_persistence_failures("full save", _save_failures)

        # GL-CMD-DEEP-ATLAS-PERSIST: emit save confirmation event
        _n_deep = self.deep_atlas.live_count()
        self._log_substrate_event("deep_atlas_saved",
                                  tick=save_tick, n_entries=_n_deep,
                                  state_dir=state_dir)

        # S3 backup handled by SaveCoordinator (non-blocking background thread)

        # GL-FIX-ATOMIC-SAVE-GENERATIONS: publish an atomic snapshot of the
        # just-written flat set as a recoverable generation. Only on full
        # success (every file landed); best-effort, never raises here.
        if not _save_failures:
            if publish_generation:
                # 2026-07-16 seal: a save into a PRIVATE STAGE must not
                # hardlink itself into the generation store -- the stage
                # IS the snapshot, and an outside link would be a real
                # post-seal mutation path (stage validator rightly
                # rejects it).
                self._publish_state_generation(state_dir, save_tick)

        return results

    def _publish_state_generation(self, state_dir, save_tick):
        """Best-effort atomic generation snapshot of the flat state dir.

        GL-FIX-ATOMIC-SAVE-GENERATIONS-20260715: a kill between the individual
        per-file writes of a save cycle can leave the flat directory mixing two
        cycles. This captures each completed cycle as an immutable, hard-linked
        generation so boot recovery can fall back to the previous complete
        generation instead of silently time-travelling to a days-old S3 backup.
        Never raises into the save path -- a publish failure only means no new
        fallback point this cycle.

        Operator kill-switch: set GUALA_ATOMIC_GENERATIONS=0 to disable ONLY
        this per-save snapshot cost (hard-links + a few fsyncs). The
        load-bearing hot/cold tick-manifest fix (Piece A) is independent of
        this and stays active; with the switch off, boot recovery simply finds
        no local generations and halts loudly instead of falling back to an
        older one -- it still never silently reaches for S3. Provided because
        per-save cost at production scale has historically been the one class
        of regression local testing cannot catch."""
        if os.environ.get("GUALA_ATOMIC_GENERATIONS", "1") == "0":
            return
        try:
            from dsf_ai_service.substrate import atomic_state_generation as _asg
        except Exception:
            return
        try:
            _asg.publish_generation(
                state_dir, int(save_tick), self._guala_identity,
                keep=3, log=print)
        except Exception as _ge:
            print(f"[gen] generation publish skipped (non-fatal): {_ge}")

    def _save_wave_atlas(self, state_dir):
        """Persist WaveAtlas inside the shared persistence transaction."""
        with self.persistence_transaction():
            return self._save_wave_atlas_locked(state_dir)

    def _save_wave_atlas_locked(self, state_dir):
        """GL-CMD-WAVE-SEMANTICS-85 Part C.1: persist WaveAtlas as numpy .npz.
        Much smaller than JSON after Part B.3 migration (~8-25k bindings → <5MB).
        A configured WaveAtlas is required state; write failures propagate."""
        if self.wave_atlas is None:
            return
        npz_path = os.path.join(state_dir, "wave_atlas.npz")
        tmp_path = npz_path + ".tmp"
        save_tick = self.tick
        try:
            n_cells = len(self.wave_atlas.cells)
            n_bind = sum(len(c.bindings) for c in self.wave_atlas.cells.values())
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
            binding_path = self._write_binary_binding(npz_path, save_tick)
            file_mb = os.path.getsize(npz_path) / 1e6
            print(f"[GualaLoom] WaveAtlas saved (npz): {n_cells} cells, "
                  f"{n_bind} bindings, {file_mb:.1f}MB")
            return {
                "path": npz_path,
                "bytes": os.path.getsize(npz_path),
                "binding_path": binding_path,
            }
        except Exception as _we:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            print(f"[GualaLoom] WaveAtlas npz save failed: {_we}")
            raise

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
        with self._event_log_lock:
            if not os.path.exists(path):
                return 0
            return os.path.getsize(path)

    def compact_events(self, state_dir, keep_after_offset=0):
        """Compact crash-replay events inside the persistence transaction."""
        with self.persistence_transaction():
            return self._compact_events_locked(state_dir, keep_after_offset)

    def _compact_events_locked(self, state_dir, keep_after_offset=0):
        """Keep only events written after keep_after_offset bytes.
        Events appended during the save window survive; only pre-save
        events (already captured in the snapshot) are discarded."""
        path = os.path.join(state_dir, self.EVENTS_LOG)
        tmp = path + ".tmp"
        with self._event_log_lock:
            if not os.path.exists(path):
                return 0
            with open(path, "rb") as f:
                f.seek(keep_after_offset)
                tail = f.read()
            size_before = os.path.getsize(path)
            try:
                with open(tmp, "wb") as f:
                    f.write(tail)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, path)
            except Exception:
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                raise
            kept = len(tail.strip().split(b"\n")) if tail.strip() else 0
            discarded = size_before - len(tail)
            if discarded > 0:
                print(f"[GualaLoom] Event log compacted: {discarded} bytes discarded, "
                      f"{kept} events kept")
            return kept

    @_engine_mutation_entry
    def load_full_state(self, state_dir="state", *, require_exact_binary=False):
        """Load with identity verification, schema check, integrity validation."""
        self._load_errors = []
        self._load_successful = False
        self._integrity_errors = []
        self._events_replayed_at_boot = 0
        self._binary_restore_status = {
            "organism": False,
            "tapestry": False,
            "wave_atlas": False,
        }

        identity_path = os.path.join(state_dir, self.IDENTITY_FILE)
        has_identity = os.path.exists(identity_path)
        present = [f for f in self.STATE_FILES
                   if os.path.exists(os.path.join(state_dir, f))]
        # Review 2026-07-16: leftover WAL segments are state evidence too.
        # Without this, a dir holding window memory but no flat files would
        # sail into genesis and orphan (then interleave generations with)
        # real experience.
        from dsf_ai_service.substrate.window_manager import (
            WAL_DIRNAME as _WAL_DIRNAME,
            WAL_SEGMENT_PREFIX as _WAL_SEG_PREFIX,
            WAL_SEGMENT_SUFFIX as _WAL_SEG_SUFFIX,
        )
        _wal_dir_path = os.path.join(state_dir, _WAL_DIRNAME)
        wal_segments_present = False
        if os.path.isdir(_wal_dir_path):
            wal_segments_present = any(
                name.startswith(_WAL_SEG_PREFIX)
                and name.endswith(_WAL_SEG_SUFFIX)
                for name in os.listdir(_wal_dir_path))

        # ── The one boot method (GL-SPC-SUBSTRATE-TRUE §boot, Change 1) ──
        # Identity: present -> continue; absent -> genesis (loud genesis_boot
        # event, empty stores); unreadable -> named halt.  The former
        # GUALA_FORCE_FRESH and adopt-state-without-identity branches are
        # DELETED per spec: no flag selects a boot path (P5), and the only
        # recovery from an inconsistent state dir is the operator's explicit
        # restore command run while the service is stopped (P4).

        if not has_identity and not present and not wal_segments_present:
            # Genesis: mint identity, loud genesis_boot event, empty stores.
            self._generate_genesis_identity(state_dir)
            self.window_manager.configure_wal_under(state_dir)
            self._log_substrate_event(
                "genesis_boot",
                identity=self._guala_identity,
                state_dir=os.path.abspath(state_dir))
            print(f"[GualaLoom] GENESIS BOOT: empty stores, identity "
                  f"{self._guala_identity} minted at {state_dir}")
            self._load_successful = True
            return

        if has_identity and not present:
            # Identity present but every state file vanished: a true wipe or
            # an EFS race/mount-not-ready.  Silently becoming fresh would
            # overwrite real state on the next save — NAMED loud halt, no
            # env-flag override (the GUALA_FORCE_FRESH escape is deleted).
            try:
                self._guala_identity = self._load_identity(state_dir)
            except Exception:
                self._guala_identity = None
            msg = (f"[GualaLoom] BOOT HALT (GualaBootStateIntegrityHalt): "
                   f"identity present but state files vanished for "
                   f"{self._guala_identity}. This process will NOT boot "
                   f"fresh over a real identity. To restore a named S3 "
                   f"backup, STOP the service and run the operator command: "
                   f"python -m tools.restore_from_s3 --list, then "
                   f"python -m tools.restore_from_s3 --backup <name> "
                   f"--state-dir {state_dir}. For a deliberate fresh start, "
                   f"the operator removes {self.IDENTITY_FILE} explicitly.")
            print(msg)
            self._load_errors.append(msg)
            self._load_successful = False
            raise GualaBootStateIntegrityHalt(msg)

        if not has_identity and (present or wal_segments_present):
            # State evidence (flat files OR window-WAL segments) without an
            # identity: the pre-v5.5 adopt-and-migrate branch is DELETED
            # (one boot method; no legacy reader).  Genesis here would
            # orphan-overwrite real experience on the next save — NAMED
            # loud halt instead.
            _evidence = present or [f"{_WAL_DIRNAME}/ segments"]
            msg = (f"[GualaLoom] BOOT HALT (GualaBootStateIntegrityHalt): "
                   f"state files {_evidence} exist without "
                   f"{self.IDENTITY_FILE}. The legacy adopt-without-identity "
                   f"migration is removed. STOP the service and either "
                   f"restore a named S3 backup (python -m tools."
                   f"restore_from_s3) or have the operator clear the state "
                   f"directory explicitly for a genesis boot.")
            print(msg)
            self._load_errors.append(msg)
            self._load_successful = False
            raise GualaBootStateIntegrityHalt(msg)

        # Both identity and state exist — full verified load
        try:
            self._guala_identity = self._load_identity(state_dir)
        except Exception as identity_error:
            msg = (f"[GualaLoom] BOOT HALT (GualaBootIdentityUnreadableHalt): "
                   f"{self.IDENTITY_FILE} exists but is unreadable: "
                   f"{identity_error}. Refusing to re-genesis over a real "
                   f"identity. STOP the service and restore a named S3 backup "
                   f"(python -m tools.restore_from_s3) or repair the file.")
            print(msg)
            self._load_errors.append(msg)
            self._load_successful = False
            raise GualaBootIdentityUnreadableHalt(msg) from identity_error
        self.organism.identity_uuid = self._guala_identity  # GL-CMD-175 P1
        missing = [f for f in self.STATE_FILES if f not in present]
        _window_migration = False
        if missing == ["guala_windows.json"]:
            # v7.3 introduces first-class BindingWindow persistence.  An
            # older core may honestly migrate with empty canonical memory;
            # a v7.3 core missing this file is a partial generation and must
            # fail closed rather than silently erase recognition history.
            with open(os.path.join(state_dir, "guala_core.json")) as _core_fh:
                _prior_core = json.load(_core_fh)
            _prior_schema = _prior_core.get("schema_version", "unknown")
            _window_migration = _prior_schema in (
                self.COMPATIBLE_SCHEMAS - {"v7.3.0"})
        if missing and not _window_migration:
            msg = f"[GualaLoom] ABORT: partial state. Missing: {missing}"
            print(msg)
            self._load_errors.append(msg)
            return

        try:
            # Load all files, verify envelopes
            raw = {}
            load_files = [f for f in self.STATE_FILES if f in present]
            for f in load_files:
                with open(os.path.join(state_dir, f)) as fh:
                    raw[f] = json.load(fh)

            # Unwrap + validate identity/schema
            data = {}
            for f in load_files:
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
            # GL-FIX-HOTCOLD-TICK-MANIFEST: adopt the per-file save-tick manifest
            # core carries, so the envelope validator checks each companion file
            # against the tick IT was really written at (hot/cold lanes diverge
            # by design) rather than against core's tick. Absent for pre-fix
            # legacy state -> validator falls back to "not newer than core",
            # which accepts the existing on-disk hot/cold mix without loss.
            _sft = core.get("state_file_ticks")
            self._expected_file_ticks = (
                {k: v for k, v in _sft.items()
                 if isinstance(v, int) and not isinstance(v, bool)}
                if isinstance(_sft, dict) else None)
            self._state_file_ticks = dict(self._expected_file_ticks or {})
            if (core.get("continuity_contract") ==
                    self.ENGINE_CONTINUITY_CONTRACT):
                missing_continuity = [
                    name for name in (
                        "guala_visual.json", "guala_videos.json",
                        "guala_sight_motifs.json")
                    if not os.path.isfile(os.path.join(state_dir, name))]
                if missing_continuity:
                    raise ValueError(
                        "continuity generation missing: "
                        f"{missing_continuity}")
            exact_binary = bool(
                require_exact_binary
                or core.get("continuity_contract") ==
                self.ENGINE_CONTINUITY_CONTRACT)
            binding_contract = core.get("binary_binding_contract")
            if (binding_contract is not None
                    and binding_contract != self.BINARY_BINDING_CONTRACT):
                raise ValueError(
                    f"unknown binary binding contract: {binding_contract}")
            bound_generation = (
                binding_contract == self.BINARY_BINDING_CONTRACT)
            core_envelope_tick = raw["guala_core.json"].get("saved_at_tick")
            if exact_binary:
                self._exact_int(
                    core_envelope_tick, "guala_core.json.saved_at_tick")
                self._exact_int(core.get("tick"), "guala_core.json.tick")
                self._exact_int(
                    core.get("last_save_tick"),
                    "guala_core.json.last_save_tick")
                if core["tick"] != core_envelope_tick:
                    raise ValueError(
                        "guala_core.json: engine tick differs from save tick")
                if core["last_save_tick"] != core_envelope_tick:
                    raise ValueError(
                        "guala_core.json: last_save_tick differs from save tick")
                for filename in load_files:
                    self._validate_exact_envelope(
                        raw[filename], filename, core_envelope_tick)

            # Apply state
            with self.lock:
                self._apply_core(core)
                self._apply_needs(nd)
                self._apply_coordinator(data["guala_coordinator.json"])
                self._apply_atlas(
                    data["guala_atlas.json"], exact=bound_generation)
                self._apply_sections(
                    data["guala_sections.json"], exact=bound_generation)
                self._rebuild_word_to_emission_index()
                if not bound_generation:
                    self._migrate_tick_domain()
                self._apply_bucket(data["guala_bucket.json"])

            if "guala_windows.json" in data:
                # GL-WAL-INCREMENTAL: dispatches to WAL replay (new manifest
                # format) or the legacy full-snapshot restore, configuring the
                # WAL directory either way.
                self.window_manager.restore_persisted(
                    data["guala_windows.json"], state_dir)
            else:
                # Explicit one-time migration from pre-v7.3: no canonical
                # window history existed, so recognition begins honestly
                # empty rather than being fabricated from legacy Atlas rows.
                # Configure the WAL now so closes are durable from first tick.
                self.window_manager.configure_wal_under(state_dir)
                self._log_substrate_event(
                    "binding_window_state_migrated_empty",
                    prior_schema=_prior_schema)
            self._rebuild_language_fact_memory_from_windows()

            # Load deep atlas if present (GL-BRIEF-032 — separate table)
            # GL-CMD-DEEP-ATLAS-PERSIST: load first, then run loss alarm
            deep_path = os.path.join(state_dir, "guala_deep_atlas.json")
            _deep_saved_count = 0
            if os.path.exists(deep_path):
                try:
                    with open(deep_path) as fh:
                        draw = json.load(fh)
                    ddata = (self._unwrap(draw, "guala_deep_atlas.json")
                             if "data" in draw and "guala_identity" in draw
                             else draw)
                    if exact_binary:
                        self._validate_exact_envelope(
                            draw, "guala_deep_atlas.json",
                            core_envelope_tick)
                        self._validate_deep_atlas_payload(
                            ddata, core_envelope_tick + self._INTRA_CYCLE_TICK_SKEW)
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
                    if exact_binary and _deep_loaded != _deep_saved_count:
                        raise ValueError(
                            "exact deep-atlas restore count mismatch: "
                            f"loaded={_deep_loaded} persisted={_deep_saved_count}")
                except Exception as e:
                    print(f"[GualaLoom] Deep atlas load FAILED: {e}")
                    self._deep_atlas_loss_at_boot = {"error": str(e)}
                    if exact_binary:
                        raise ValueError(
                            f"required deep-atlas restore failed: {e}") from e
            else:
                if exact_binary:
                    raise ValueError("required guala_deep_atlas.json is missing")
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
                    organism_type = type(self.organism)
                    if bound_generation:
                        self._verify_binary_binding(
                            organism_path, core_envelope_tick)
                    self.organism = organism_type.load_full_state(organism_path)
                    if exact_binary and not isinstance(self.organism, organism_type):
                        raise ValueError("organism pickle restored an unexpected type")
                    if self.organism.identity_uuid != self._guala_identity:
                        # G-2-class anomaly: her identity is authoritative
                        # (_load_identity, above) -- never let a mismatched
                        # organism silently pass as a second identity.
                        if exact_binary:
                            raise ValueError(
                                "organism identity differs from Guala identity")
                        print(f"[GualaLoom] WARNING: organism identity "
                              f"{self.organism.identity_uuid} != her identity "
                              f"{self._guala_identity} -- correcting to hers")
                        self.organism.identity_uuid = self._guala_identity
                    # GL-CMD-ORGANISM-WAVE-MEMORY-207 W4: division count
                    # alongside population -- "the 07-05 population
                    # staircase must be impossible to miss again." Pop
                    # alone doesn't show whether a restore lost divisions
                    # (a fallback to an older save); total_divisions does.
                    _gs = self.organism.growth_snapshot()
                    if exact_binary:
                        self._exact_int(
                            getattr(self.organism, "tick", None),
                            "organism.tick")
                        if not isinstance(_gs, dict):
                            raise ValueError(
                                "organism growth snapshot must be an object")
                        for field in ("total_neurons", "total_divisions"):
                            self._exact_int(
                                _gs.get(field), f"organism.{field}")
                    print(f"[GualaLoom] Organism restored: identity={self.organism.identity_uuid} "
                          f"tick={self.organism.tick} pop={_gs['total_neurons']} "
                          f"total_divisions={_gs['total_divisions']} "
                          f"file={organism_path}")
                    # GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3: re-wire the
                    # spike bus onto the just-restored organism. self.organism
                    # was JUST replaced wholesale above -- __init__'s wiring
                    # (which ran before load_full_state was ever called) points
                    # at the now-discarded pre-restore neurons/brain. Without
                    # this call, every restored boot leaves the spike bus
                    # wired to orphaned objects -- confirmed live, see
                    # GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1 finding 1.
                    # Separate try/except from the restore above so a wiring
                    # failure is never misreported as "organism restore
                    # FAILED" -- the organism itself is fine either way.
                    try:
                        self.wire_spike_bus()
                    except Exception as _wire_e:
                        if exact_binary:
                            raise ValueError(
                                f"restored organism spike wiring failed: {_wire_e}") from _wire_e
                        print(f"[GualaLoom] wire_spike_bus after organism "
                              f"restore failed (non-fatal): {_wire_e}")
                    # membrane_threshold/chi_position backfill (2026-07-08
                    # lateral-inhibition-and-entry-selection fix): same
                    # class of gap as wire_spike_bus above, verified
                    # directly against a real downloaded production
                    # pickle (tick 223937) -- self.organism was JUST
                    # replaced wholesale, and those two fields are still
                    # at __init__'s raw defaults on every neuron in it
                    # (unlike kappa/threshold/polarity, which _polarity's
                    # presence proves were already correctly seeded at
                    # this organism's original construction and survive
                    # pickling verbatim). _seed_dna_diversity is
                    # idempotent per neuron per stage -- calling it again
                    # here only backfills what's actually still missing,
                    # never re-multiplies the already-evolved real
                    # kappa/threshold. Own try/except, same reasoning as
                    # wire_spike_bus's: a failure here must never be
                    # misreported as organism restore FAILED.
                    if not exact_binary:
                        try:
                            self.organism._seed_dna_diversity()
                        except Exception as _chem_e:
                            print(f"[GualaLoom] membrane chemistry backfill after "
                                  f"organism restore failed (non-fatal): {_chem_e}")
                    # 2026-07-08 pruning fix: reclaim chi_atlas bloat
                    # accumulated before the per-key cap existed --
                    # confirmed live, one real neuron had 80,355
                    # never-pruned records. Append-time capping alone
                    # (chi_atlas_l6.py's record()) only stops FUTURE
                    # growth; an already-restored organism's existing
                    # entries need this one-time trim to actually free
                    # the memory. Idempotent, own try/except, same
                    # non-fatal-failure reasoning as above.
                    if not exact_binary:
                        try:
                            for _n in self._all_neurons():
                                _n.chi_atlas.trim_all()
                        except Exception as _trim_e:
                            print(f"[GualaLoom] chi_atlas trim after organism "
                                  f"restore failed (non-fatal): {_trim_e}")
                    self._binary_restore_status["organism"] = True
                except Exception as e:
                    if exact_binary:
                        raise ValueError(
                            f"required organism restore failed: {e}") from e
                    print(f"[GualaLoom] Organism restore FAILED (organism from boot stands): {e}")
            else:
                if exact_binary:
                    raise ValueError("required guala_organism.pkl.gz is missing")
                print("[GualaLoom] No guala_organism.pkl.gz — organism starts fresh this boot")

            # GL-NOTE-VOICE-WIRING-RULING W1: restore the tapestry alongside
            # the organism -- same honest-fresh-on-absence reasoning.
            tapestry_path = os.path.join(state_dir, "guala_tapestry.pkl.gz")
            if os.path.exists(tapestry_path):
                try:
                    tapestry_type = type(self.tapestry)
                    if bound_generation:
                        self._verify_binary_binding(
                            tapestry_path, core_envelope_tick)
                    self.tapestry = tapestry_type.load_full_state(tapestry_path)
                    if exact_binary and not isinstance(self.tapestry, tapestry_type):
                        raise ValueError("tapestry pickle restored an unexpected type")
                    if exact_binary:
                        self._exact_int(
                            getattr(self.tapestry, "_tick", None),
                            "tapestry.tick")
                        self._exact_int(
                            self.tapestry.total_neurons,
                            "tapestry.total_neurons", minimum=1)
                        if (not isinstance(self.tapestry.mosaics, list)
                                or len(self.tapestry.mosaics)
                                != self.tapestry.n_mosaics):
                            raise ValueError(
                                "tapestry mosaic count differs from its structure")
                    # GL-195: restore the emission query source (see save).
                    _pw = getattr(self.tapestry, "_engine_prev_word", None)
                    if _pw:
                        self._tapestry_prev_word = _pw
                    print(f"[GualaLoom] Tapestry restored: tick={self.tapestry._tick} "
                          f"neurons={self.tapestry.total_neurons} "
                          f"prev_word={'set' if _pw else 'none'}")
                    # 2026-07-08 pruning fix: same chi_atlas bloat as the
                    # organism above, same one-time reclaim -- the
                    # tapestry's 450 neurons are the SAME LoomNeuron
                    # class and were the larger contributor measured
                    # live (chi_atlas alone was ~99% of one tapestry
                    # neuron's ~2MB pickled size).
                    if not exact_binary:
                        try:
                            for _mosaic in self.tapestry.mosaics:
                                for _cluster in _mosaic.clusters:
                                    for _n in _cluster.neurons:
                                        _n.chi_atlas.trim_all()
                        except Exception as _trim_e:
                            print(f"[GualaLoom] tapestry chi_atlas trim failed "
                                  f"(non-fatal): {_trim_e}")
                    self._binary_restore_status["tapestry"] = True
                except Exception as e:
                    if exact_binary:
                        raise ValueError(
                            f"required tapestry restore failed: {e}") from e
                    print(f"[GualaLoom] Tapestry restore FAILED (tapestry from boot stands): {e}")
            else:
                if exact_binary:
                    raise ValueError("required guala_tapestry.pkl.gz is missing")
                print("[GualaLoom] No guala_tapestry.pkl.gz — tapestry starts fresh this boot")

            # GL-CMD-HOTLANE-DIET-102: load survival history from own cold file.
            # _apply_core() already set _deep_survival_history from core.json's field
            # (backward compat). If guala_survival.json exists, it overrides that.
            survival_path = os.path.join(state_dir, "guala_survival.json")
            if os.path.exists(survival_path):
                try:
                    with open(survival_path) as fh:
                        sraw = json.load(fh)
                    sdata = (self._unwrap(sraw, "guala_survival.json")
                             if "data" in sraw and "guala_identity" in sraw
                             else sraw)
                    if exact_binary:
                        self._validate_exact_envelope(
                            sraw, "guala_survival.json", core_envelope_tick)
                        self._validate_survival_payload(sdata)
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
                    if exact_binary:
                        raise ValueError(
                            f"required survival-history restore failed: {e}") from e
                    print(f"[GualaLoom] Survival history load FAILED: {e} — using core.json fallback")
            else:
                if exact_binary:
                    raise ValueError("required guala_survival.json is missing")
                _sc = len(self._deep_survival_history)
                print(f"[GualaLoom] No guala_survival.json — survival history from core.json "
                      f"fallback ({_sc} entries)")

            # GL-CMD-TEACHER-CORRECTION-UI: teaching data (backward-compatible)
            teaching_path = os.path.join(state_dir, "guala_teaching.json")
            if os.path.exists(teaching_path):
                try:
                    with open(teaching_path) as f:
                        td = json.load(f)
                    tdata = (self._unwrap(td, "guala_teaching.json")
                             if "data" in td and "guala_identity" in td
                             else td)
                    if exact_binary:
                        self._validate_exact_envelope(
                            td, "guala_teaching.json", core_envelope_tick)
                        self._validate_teaching_payload(
                            tdata, core_envelope_tick + self._INTRA_CYCLE_TICK_SKEW)
                    self._teaching_feedback_log = list(
                        tdata.get("feedback_log", []))
                    self._teaching_correction_log = list(
                        tdata.get("correction_log", []))
                    if exact_binary:
                        self._emission_records = dict(
                            tdata.get("emission_records", {}))
                    else:
                        for eid, rec in tdata.get("emission_records", {}).items():
                            self._emission_records[eid] = rec
                except Exception as error:
                    if exact_binary:
                        raise ValueError(
                            f"required teaching restore failed: {error}") from error
            elif exact_binary:
                raise ValueError("required guala_teaching.json is missing")

            # GL-CMD-EPISODIC-MEMORY: real, situational memories (backward-
            # compatible -- absent entirely on any organism saved before
            # this field existed, honest empty then, not fabricated).
            episodic_path = os.path.join(state_dir, "guala_episodic.json")
            if os.path.exists(episodic_path):
                try:
                    with open(episodic_path) as f:
                        ed = json.load(f)
                    edata = (self._unwrap(ed, "guala_episodic.json")
                             if "data" in ed and "guala_identity" in ed
                             else ed)
                    if exact_binary:
                        self._validate_exact_envelope(
                            ed, "guala_episodic.json", core_envelope_tick)
                        self._validate_episodic_payload(
                            edata, core_envelope_tick + self._INTRA_CYCLE_TICK_SKEW,
                            self.EPISODIC_MEMORY_MAX_PER_CONCEPT,
                            self.EPISODIC_RECENT_CONTEXT_WINDOW)
                        self._episodic_memory = {}
                        self._episodic_recent_concepts.clear()
                    for concept, recs in edata.get("episodic_memory", {}).items():
                        dq = deque(maxlen=self.EPISODIC_MEMORY_MAX_PER_CONCEPT)
                        selected_records = (
                            recs if exact_binary else
                            recs[-self.EPISODIC_MEMORY_MAX_PER_CONCEPT:])
                        for r in selected_records:
                            dq.append(r)
                        self._episodic_memory[concept] = dq
                    for c in edata.get("episodic_recent_concepts", []):
                        self._episodic_recent_concepts.append(c)
                except Exception as error:
                    if exact_binary:
                        raise ValueError(
                            f"required episodic restore failed: {error}") from error
            elif exact_binary:
                raise ValueError("required guala_episodic.json is missing")

            # Load sounds if present (1.4)
            sounds_path = os.path.join(state_dir, "guala_sounds.json")
            if os.path.exists(sounds_path):
                try:
                    with open(sounds_path) as fh:
                        sraw = json.load(fh)
                    sdata = (self._unwrap(sraw, "guala_sounds.json")
                             if "data" in sraw and "guala_identity" in sraw
                             else sraw)
                    if exact_binary:
                        self._validate_exact_envelope(
                            sraw, "guala_sounds.json", core_envelope_tick)
                        self._validate_sounds_payload(
                            sdata, core_envelope_tick + self._INTRA_CYCLE_TICK_SKEW)
                    self._sounds = dict(sdata)
                    print(f"[GualaLoom] Sounds loaded: {len(self._sounds)} items")
                except Exception as e:
                    if exact_binary:
                        raise ValueError(
                            f"required sounds restore failed: {e}") from e
                    print(f"[GualaLoom] Sounds load: {e}")
            elif exact_binary:
                raise ValueError("required guala_sounds.json is missing")

            # Load videos if present (1.4)
            videos_path = os.path.join(state_dir, "guala_videos.json")
            if os.path.exists(videos_path):
                with open(videos_path) as fh:
                    vraw = json.load(fh)
                vdata = (self._unwrap(vraw, "guala_videos.json")
                         if "data" in vraw and "guala_identity" in vraw
                         else vraw)
                if exact_binary:
                    self._validate_exact_envelope(
                        vraw, "guala_videos.json", core_envelope_tick)
                video_contract = vdata.get("continuity_contract")
                if (video_contract is not None
                        and video_contract != self.ENGINE_CONTINUITY_CONTRACT):
                    raise ValueError(
                        f"unknown video continuity contract: {video_contract}")
                strict_videos = (
                    video_contract == self.ENGINE_CONTINUITY_CONTRACT)
                if strict_videos:
                    video_records = vdata.get("videos")
                    if not isinstance(video_records, dict):
                        raise ValueError(
                            "guala_videos.json: videos must be an object")
                    self._videos = {}
                else:
                    video_records = vdata
                for vid, vinfo in video_records.items():
                    if not isinstance(vinfo, dict):
                        raise ValueError(f"video {vid}: state must be an object")
                    if strict_videos:
                        required = (
                            "item_id", "title", "frame_dir", "audio_path",
                            "duration_ms", "n_frames", "source",
                            "shown_at_tick", "times_attended",
                            "last_attended_tick")
                        missing_video = [
                            name for name in required if name not in vinfo]
                        if missing_video:
                            raise ValueError(
                                f"video {vid}: missing {missing_video}")
                        if vinfo["item_id"] != vid:
                            raise ValueError(f"video {vid}: item_id mismatch")
                        frame_dir = self._resolve_state_reference(
                            state_dir, vinfo["frame_dir"], "directory")
                        audio_path = (
                            self._resolve_state_reference(
                                state_dir, vinfo["audio_path"], "file")
                            if vinfo["audio_path"] else "")
                    else:
                        frame_stored = vinfo.get("frame_dir", "")
                        try:
                            frame_dir = (
                                self._resolve_state_reference(
                                    state_dir, frame_stored, "directory",
                                    allow_legacy_absolute=True)
                                if frame_stored else "")
                        except ValueError:
                            frame_dir = ""
                        audio_stored = vinfo.get("audio_path", "")
                        try:
                            audio_path = (
                                self._resolve_state_reference(
                                    state_dir, audio_stored, "file",
                                    allow_legacy_absolute=True)
                                if audio_stored else "")
                        except ValueError:
                            audio_path = ""
                    self._videos[vid] = VideoItem(
                        item_id=vinfo["item_id"],
                        title=vinfo["title"],
                        frame_dir=frame_dir,
                        audio_path=audio_path,
                        duration_ms=int(vinfo.get("duration_ms", 0)),
                        n_frames=int(vinfo.get("n_frames", 0)),
                        source=vinfo.get("source", ""),
                        shown_at_tick=int(vinfo.get("shown_at_tick", 0)),
                        times_attended=int(vinfo.get("times_attended", 0)),
                        last_attended_tick=int(
                            vinfo.get("last_attended_tick", 0)))
                print(f"[GualaLoom] Videos loaded: {len(video_records)} items")
            elif exact_binary:
                raise ValueError("required guala_videos.json is missing")

            # Load visual data if present
            visual_path = os.path.join(state_dir, "guala_visual.json")
            if os.path.exists(visual_path):
                with open(visual_path) as fh:
                    vraw = json.load(fh)
                vdata = (self._unwrap(vraw, "guala_visual.json")
                         if "data" in vraw and "guala_identity" in vraw
                         else vraw)
                if exact_binary:
                    self._validate_exact_envelope(
                        vraw, "guala_visual.json", core_envelope_tick)
                # GL-194: motifs live in their own cold file now.
                # Prefer it; fall back to legacy inline sight_motifs only for
                # a pre-contract save. A continuity save references the file
                # explicitly, so absence/corruption is a torn generation.
                sm_path = os.path.join(state_dir, "guala_sight_motifs.json")
                strict_visual = (
                    vdata.get("continuity_contract") ==
                    self.ENGINE_CONTINUITY_CONTRACT)
                if os.path.exists(sm_path):
                    with open(sm_path) as fh2:
                        smraw = json.load(fh2)
                    smdata = (
                        self._unwrap(smraw, "guala_sight_motifs.json")
                        if "data" in smraw and "guala_identity" in smraw
                        else smraw)
                    if exact_binary:
                        self._validate_exact_envelope(
                            smraw, "guala_sight_motifs.json",
                            core_envelope_tick)
                    vdata["sight_motifs"] = smdata.get("sight_motifs", [])
                elif strict_visual or exact_binary:
                    raise ValueError(
                        "guala_visual.json: referenced sight motif state missing")
                self._apply_visual(vdata, state_dir)
            elif exact_binary:
                raise ValueError("required guala_visual.json is missing")

            # Replay events since last save
            self._events_replayed_at_boot = self._replay_events(state_dir)

            # Integrity validation
            self._validate_integrity()
            if exact_binary and self._integrity_errors:
                raise ValueError(
                    f"integrity validation failed: {self._integrity_errors}")
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
                        if bound_generation:
                            self._verify_binary_binding(
                                _wave_npz, core_envelope_tick)
                        if exact_binary:
                            self._validate_wave_npz_payload(_wave_npz)
                        n_cells = self.wave_atlas.load_from_npz(_wave_npz)
                        print(f"[GualaLoom] WaveAtlas loaded from disk (npz): {n_cells} cells, "
                              f"{self.wave_atlas.binding_count()} bindings")
                        _wave_loaded = True
                    except Exception as _wle:
                        if exact_binary:
                            raise ValueError(
                                f"required WaveAtlas NPZ restore failed: {_wle}") from _wle
                        print(f"[GualaLoom] WaveAtlas npz load failed ({_wle}), trying json")

                if exact_binary and not os.path.exists(_wave_npz):
                    # 2026-07-16 boot incident: a young life that has never
                    # written a wave atlas can produce NO valid generation --
                    # the validator demanded a file the writer never made,
                    # structurally breaking the generation fallback since
                    # genesis. The binding receipt is the truth: if a
                    # receipt exists the artifact was written and its
                    # absence is real corruption; no receipt = never
                    # written = legitimately fresh.
                    if os.path.isfile(self._binary_binding_path(_wave_npz)):
                        raise ValueError("required wave_atlas.npz is missing")
                    print("[GualaLoom][wave-atlas] no npz and no binding "
                          "receipt -- this life has not written a wave "
                          "atlas yet; starting fresh (accepted, loud)",
                          flush=True)
                    # Legitimately-fresh counts as its restore proof: the
                    # downstream required-proof gate must not re-reject
                    # what this branch just loudly accepted.
                    self._binary_restore_status["wave_atlas"] = True

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
                        self._start_engine_background_thread(
                            _archive_json_to_s3, daemon=True,
                            name="wave-json-archive")
                    except Exception as _wle:
                        print(f"[GualaLoom] WaveAtlas json load failed ({_wle}), rebuilding")

                if not _wave_loaded:
                    # First boot after WaveAtlas enabled — rebuild once
                    self.wave_atlas.rebuild_from(self.atlas)
                    print(f"[GualaLoom] WaveAtlas rebuilt from LivingAtlas (one-time): "
                          f"{self.wave_atlas.cell_count()} cells, "
                          f"{self.wave_atlas.binding_count()} bindings")
                else:
                    self._binary_restore_status["wave_atlas"] = True

                if not exact_binary:
                    # Legacy compatibility may perform the historical
                    # duplicate-collapse migration.  An exact generation is
                    # never rewritten during restore: its persisted cells and
                    # bindings remain byte-for-structure identical.
                    _pre_col = self.wave_atlas.binding_count()
                    _col_r = self.wave_atlas.collapse_by_key()
                    _post_col = _col_r["after"]
                    print(f"[wave] collapse-on-load: {_pre_col}→{_post_col} bindings "
                          f"(wired={self.atlas._wave_atlas is self.wave_atlas})")

            if exact_binary:
                required_status = {"organism": True, "tapestry": True}
                if self.wave_atlas is not None:
                    required_status["wave_atlas"] = True
                missing_binary = [
                    name for name, expected in required_status.items()
                    if self._binary_restore_status.get(name) is not expected]
                if missing_binary:
                    raise ValueError(
                        f"required binary restore proof absent: {missing_binary}")
            self._load_successful = True

        except Exception as e:
            from dsf_ai_service.substrate.window_manager import (
                WindowStoreIntegrityHalt,
            )
            if isinstance(e, WindowStoreIntegrityHalt):
                # GL-SPC-SUBSTRATE-TRUE Change 1 (P4): a hash/digest failure
                # in durable window memory is a NAMED LOUD HALT.  It must
                # never degrade into recover-and-continue (_load_errors +
                # local-generation fallback) — propagate so boot stops.
                print(f"[GualaLoom] BOOT HALT (WindowStoreIntegrityHalt): {e}")
                self._load_errors.append(str(e))
                raise
            msg = f"[GualaLoom] ABORT load: {e}"
            print(msg)
            self._load_errors.append(msg)

    # _load_pre_envelope (pre-v5.5 adopt-state-without-identity migration)
    # DELETED per GL-SPC-SUBSTRATE-TRUE Change 1: the one boot method never
    # reads legacy formats; state-without-identity is a named loud halt in
    # load_full_state.  Git history remains the archive.

    # ── Apply helpers (shared by load paths) ──

    def _apply_core(self, core):
        contract = core.get("continuity_contract")
        if (contract is not None
                and contract != self.ENGINE_CONTINUITY_CONTRACT):
            raise ValueError(f"unknown core continuity contract: {contract}")
        strict = contract == self.ENGINE_CONTINUITY_CONTRACT
        if strict:
            for required in (
                    "corpora_state", "sensory_state", "current_activity",
                    "last_save_tick"):
                if required not in core:
                    raise ValueError(
                        f"guala_core.json: continuity field missing: {required}")
            if not isinstance(core["corpora_state"], dict):
                raise ValueError("guala_core.json: corpora_state must be an object")
            if not isinstance(core["sensory_state"], dict):
                raise ValueError("guala_core.json: sensory_state must be an object")
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
        corpora_state = core.get("corpora_state", {})
        if strict:
            restored_corpora = {}
            for cid, cstate in corpora_state.items():
                if not isinstance(cstate, dict):
                    raise ValueError(f"corpus {cid}: state must be an object")
                lines = cstate.get("lines")
                if (not isinstance(lines, list)
                        or any(not isinstance(line, str) for line in lines)):
                    raise ValueError(f"corpus {cid}: lines must be a string list")
                if cstate.get("corpus_id") != cid:
                    raise ValueError(f"corpus {cid}: corpus_id mismatch")
                title = cstate.get("title")
                if not isinstance(title, str):
                    raise ValueError(f"corpus {cid}: title must be a string")
                restored_corpora[cid] = _Corpus(
                    corpus_id=cid,
                    title=title,
                    lines=list(lines),
                    position=int(cstate.get("position", 0)),
                    times_read_through=int(cstate.get("times_read_through", 0)),
                    last_read_tick=int(cstate.get("last_read_tick", 0)))
            self._corpora = restored_corpora
        else:
            # Older states persisted only positions. Their definitions were
            # legitimately supplied by the boot seed registration path.
            for cid, cstate in corpora_state.items():
                if cid in self._corpora:
                    self._corpora[cid].position = cstate.get("position", 0)
                    self._corpora[cid].times_read_through = cstate.get("times_read_through", 0)
                    self._corpora[cid].last_read_tick = cstate.get("last_read_tick", 0)

        sensory_state = core.get("sensory_state", {})
        if strict:
            restored_sensory = {}
            for sid, sstate in sensory_state.items():
                if not isinstance(sstate, dict):
                    raise ValueError(f"sensory item {sid}: state must be an object")
                if sstate.get("item_id") != sid:
                    raise ValueError(f"sensory item {sid}: item_id mismatch")
                kind = sstate.get("kind")
                title = sstate.get("title")
                if not isinstance(kind, str) or not isinstance(title, str):
                    raise ValueError(
                        f"sensory item {sid}: kind/title must be strings")
                restored_sensory[sid] = SensoryItem(
                    item_id=sid,
                    kind=kind,
                    title=title,
                    times_attended=int(sstate.get("times_attended", 0)),
                    last_attended_tick=int(
                        sstate.get("last_attended_tick", 0)))
            self._sensory_items = restored_sensory
        else:
            for sid, sstate in sensory_state.items():
                if sid in self._sensory_items:
                    self._sensory_items[sid].times_attended = sstate.get("times_attended", 0)
                    self._sensory_items[sid].last_attended_tick = sstate.get("last_attended_tick", 0)

        activity = core.get("current_activity")
        if activity is None:
            self._current_activity = None
        elif isinstance(activity, dict):
            metadata = activity.get("metadata", {})
            if not isinstance(metadata, dict):
                raise ValueError("current_activity.metadata must be an object")
            kind = activity.get("kind")
            if not isinstance(kind, str):
                raise ValueError("current_activity.kind must be a string")
            self._current_activity = Activity(
                kind=kind,
                target=activity.get("target"),
                started_tick=int(activity["started_tick"]),
                expected_end_tick=int(activity["expected_end_tick"]),
                metadata=dict(metadata))
        else:
            raise ValueError("current_activity must be an object or null")
        self._last_save_tick = int(core.get(
            "last_save_tick", self.tick if strict else 0))
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
        contract = cd.get("continuity_contract")
        if (contract is not None
                and contract != self.ENGINE_CONTINUITY_CONTRACT):
            raise ValueError(
                f"unknown coordinator continuity contract: {contract}")
        strict = contract == self.ENGINE_CONTINUITY_CONTRACT
        if strict:
            if not isinstance(cd.get("presence"), dict):
                raise ValueError("guala_coordinator.json: presence must be an object")
            if not isinstance(cd.get("last_input_tick"), dict):
                raise ValueError(
                    "guala_coordinator.json: last_input_tick must be an object")
            if any(not isinstance(value, bool)
                   for value in cd["presence"].values()):
                raise ValueError(
                    "guala_coordinator.json: presence values must be booleans")
            if any(not isinstance(value, int) or isinstance(value, bool)
                   for value in cd["last_input_tick"].values()):
                raise ValueError(
                    "guala_coordinator.json: last_input_tick values must be integers")
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
        if strict:
            self.coordinator._presence = {
                str(source): present
                for source, present in cd["presence"].items()
            }
            self.coordinator._last_input_tick = {
                str(source): int(tick)
                for source, tick in cd["last_input_tick"].items()
            }
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

    def _apply_atlas(self, ad, *, exact=False):
        if not isinstance(ad, dict):
            raise ValueError("guala_atlas.json must contain an object")
        self.atlas.entries = defaultdict(list)
        entries = ad.get("entries", {})
        if not isinstance(entries, dict):
            raise ValueError("guala_atlas.json: entries must be an object")
        if exact:
            self._exact_int(
                ad.get("tick"), "guala_atlas.json.tick",
                maximum=self.tick)
            for chi_text, bucket in entries.items():
                if (not isinstance(chi_text, str)
                        or not chi_text.lstrip("-").isdigit()
                        or not isinstance(bucket, list)):
                    raise ValueError(
                        "guala_atlas.json: entry buckets are invalid")
                for index, entry in enumerate(bucket):
                    label = f"guala_atlas[{chi_text}][{index}]"
                    if not isinstance(entry, dict):
                        raise ValueError(f"{label} must be an object")
                    for field in (
                            "section", "motif", "chi", "strength",
                            "last_tick", "born_tick", "hemisphere_id"):
                        if field not in entry:
                            raise ValueError(f"{label} lacks {field}")
                    if (not isinstance(entry["section"], str)
                            or not isinstance(entry["hemisphere_id"], str)):
                        raise ValueError(
                            f"{label} section/hemisphere must be strings")
                    self._exact_int(entry["motif"], f"{label}.motif")
                    self._exact_int(
                        entry["chi"], f"{label}.chi", minimum=-2**63)
                    self._exact_number(
                        entry["strength"], f"{label}.strength", minimum=0.0)
                    for field in ("last_tick", "born_tick"):
                        self._exact_int(
                            entry[field], f"{label}.{field}",
                            maximum=self.tick)
        # v5.5→v6 migration: add strength/last_tick/born_tick if missing
        from collections import Counter
        needs_migration = False
        commit_counts = Counter()
        for k, es in entries.items():
            for e in es:
                if "strength" not in e:
                    if exact:
                        raise ValueError(
                            "guala_atlas.json: exact binding lacks strength")
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
                    if exact:
                        raise ValueError(
                            "guala_atlas.json: exact binding lacks hemisphere_id")
                    e["hemisphere_id"] = "em"
                    hemi_tagged += 1
        if hemi_tagged:
            print(f"[GualaLoom] Hemisphere migration: {hemi_tagged} bindings tagged 'em'")

        # Tick-domain migration moved to _migrate_tick_domain (runs after _apply_sections)

    def _apply_sections(self, sd, *, exact=False):
        if not isinstance(sd, dict):
            raise ValueError("guala_sections.json must contain an object")
        if exact:
            missing_sections = set(self.sections) - set(sd)
            if missing_sections:
                raise ValueError(
                    "guala_sections.json: missing sections "
                    f"{sorted(missing_sections)}")
        for nm, s in sd.items():
            if nm not in self.sections:
                if exact:
                    raise ValueError(
                        f"guala_sections.json: unknown section {nm!r}")
                continue
            if not isinstance(s, dict):
                raise ValueError(f"section {nm}: state must be an object")
            sec = self.sections[nm]
            modes = s.get("modes", [])
            if not isinstance(modes, list):
                raise ValueError(f"section {nm}: modes must be a list")
            if exact:
                for index, mode in enumerate(modes):
                    if not isinstance(mode, dict):
                        raise ValueError(
                            f"section {nm}: mode {index} must be an object")
                    dsf = mode.get("dsf")
                    if (not isinstance(dsf, list) or len(dsf) != 8):
                        raise ValueError(
                            f"section {nm}: mode {index} DSF must have 8 fields")
                    for field_index, value in enumerate(dsf):
                        self._exact_number(
                            value,
                            f"section {nm}.mode[{index}].dsf[{field_index}]")
                    self._exact_int(
                        mode.get("chi"),
                        f"section {nm}.mode[{index}].chi",
                        minimum=-2**63)
                    if not isinstance(mode.get("word"), str):
                        raise ValueError(
                            f"section {nm}: mode {index} word must be a string")
            sec.modes = [(DSF(*m["dsf"]), m["chi"], m["word"]) for m in modes]
            sec.commits = s.get("commits", [])
            sec.dead_zone = s.get("dead_zone", 0.20)
            sec.gamma = s.get("gamma", {"det_thresh": 0.55, "novel_dist": 0.40})
            sec.tick = s.get("tick", 0)
            if exact:
                last_active = s.get("mode_last_active_tick")
                alive = s.get("mode_alive")
                if (not isinstance(last_active, list)
                        or len(last_active) != len(sec.modes)):
                    raise ValueError(
                        f"section {nm}: mode_last_active_tick length mismatch")
                if (not isinstance(alive, list)
                        or len(alive) != len(sec.modes)
                        or any(not isinstance(value, bool) for value in alive)):
                    raise ValueError(f"section {nm}: mode_alive length mismatch")
                for index, active_tick in enumerate(last_active):
                    self._exact_int(
                        active_tick,
                        f"section {nm}.mode_last_active_tick[{index}]",
                        maximum=self.tick)
                sec._mode_last_active_tick = list(last_active)
                sec._mode_alive = list(alive)
            # current_tick=self.tick (the ENGINE's tick, not sec.tick which
            # may be stale relative to it, GL-FIND-TICK-DOMAIN-C1) so every
            # restored mode starts as "just active," not instantly eligible
            # for forgetting the moment this deploys.
            sec._rebuild_word_index(current_tick=self.tick)

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
        contract = vd.get("continuity_contract")
        if (contract is not None
                and contract != self.ENGINE_CONTINUITY_CONTRACT):
            raise ValueError(f"unknown visual continuity contract: {contract}")
        strict = contract == self.ENGINE_CONTINUITY_CONTRACT
        pictures = vd.get("pictures")
        if strict and not isinstance(pictures, dict):
            raise ValueError("guala_visual.json: pictures must be an object")
        pictures = pictures or {}
        print(f"[GualaLoom] _apply_visual: {len(vd.get('pictures',{}))} pictures, {len(vd.get('sight_motifs',[]))} motifs in data")
        from dsf_ai_service.visual_krimelack import VisualMotif
        pic_dir = os.path.join(state_dir, "pictures")
        if strict:
            self._pictures = {}
        # Restore pictures
        for pid, pdata in pictures.items():
            try:
                if not isinstance(pdata, dict):
                    raise ValueError("picture state must be an object")
                if strict:
                    required = (
                        "item_id", "title", "source", "shown_at_tick",
                        "times_attended", "last_attended_tick", "has_grid",
                        "grid_path", "original_path", "original_width",
                        "original_height")
                    missing_picture = [
                        name for name in required if name not in pdata]
                    if missing_picture:
                        raise ValueError(f"missing {missing_picture}")
                    if pdata["item_id"] != pid:
                        raise ValueError("item_id mismatch")
                    if not isinstance(pdata["has_grid"], bool):
                        raise ValueError("has_grid must be a boolean")
                grid = None
                if strict and pdata["has_grid"]:
                    grid_path = self._resolve_state_reference(
                        state_dir, pdata["grid_path"], "file")
                    grid = np.load(grid_path, allow_pickle=False)
                elif strict and pdata["grid_path"] is not None:
                    raise ValueError("grid_path exists while has_grid is false")
                elif not strict:
                    legacy_grid_path = os.path.join(pic_dir, f"{pid}.npy")
                    if os.path.exists(legacy_grid_path):
                        grid = np.load(legacy_grid_path, allow_pickle=False)
                pic = PictureItem(
                    item_id=pdata["item_id"], title=pdata.get("title", pid),
                    intensity_grid=grid, source=pdata.get("source", "restored"),
                    shown_at_tick=pdata.get("shown_at_tick", 0),
                    times_attended=pdata.get("times_attended", 0),
                    last_attended_tick=pdata.get("last_attended_tick", 0))
                orig_path = pdata.get("original_path")
                if orig_path:
                    if strict:
                        resolved_original = self._resolve_state_reference(
                            state_dir, orig_path, "file")
                    else:
                        try:
                            resolved_original = self._resolve_state_reference(
                                state_dir, orig_path, "file",
                                allow_legacy_absolute=True)
                        except ValueError:
                            resolved_original = ""
                    if resolved_original:
                        pic.original_path = resolved_original
                        pic.original_width = pdata.get("original_width")
                        pic.original_height = pdata.get("original_height")
                self._pictures[pid] = pic
            except Exception as _pe:
                if strict:
                    raise ValueError(f"picture {pid}: {_pe}") from _pe
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
            with self._event_log_lock:
                with open(path, "a") as f:
                    f.write(line + "\n")
                # Rotate only while appenders and compaction are excluded.
                if os.path.getsize(path) > self.EVENTS_MAX_BYTES:
                    self._rotate_events(state_dir)
            # GL-CMD-EVENT-RETENTION-FIX-172 R4: mirror to stdout so the
            # unlimited-retention CloudWatch log group becomes a backstop
            # independent of events.log's own (crash-replay-sized) window.
            # Whitelist-governed by construction: log_event is only ever
            # called for the 12 whitelisted kinds (_log_substrate_event)
            # plus this same explicit call path — no new per-tick spam.
            print(f"[GualaLoom][diary-mirror] {line}", flush=True)
        except Exception:
            pass  # event log is best-effort, never crashes substrate

    def _rotate_events(self, state_dir):
        with self._event_log_lock:
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
            try:
                if item is None:
                    return
                event_kind, detail, tick, ts = item
                self._write_diary_entry(state_dir, event_kind, detail, tick, ts)
            finally:
                self._diary_queue.task_done()

    def _ensure_diary_worker(self, state_dir):
        if self._diary_queue is not None:
            return
        with self._diary_worker_lock:
            if self._diary_queue is not None:   # re-check: lost a race to another thread
                return
            # GL-CMD-SLOT-LIMITS-REMOVAL-EVE-20260707-v1: maxsize=4000
            # KEPT, not removed -- same confirmed runaway pattern as
            # _organism_queue/_tapestry_queue (direct stress test: with
            # the cap removed, an unbounded feeder grew this queue by
            # ~2.4M items and up to ~800MB RSS every 3 seconds -- worse
            # per-item growth than the other two, since each diary event
            # carries a detail dict). See the accompanying report.
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
        if self._engine_quiesced:
            return False
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
        """Create a snapshot inside the shared persistence transaction."""
        with self.persistence_transaction():
            return self._snapshot_state_locked(state_dir, reason)

    def _snapshot_state_locked(self, state_dir="state", reason="manual"):
        """Copy all state files to a timestamped backup directory.
        Snapshots go INSIDE state_dir (on EFS) not alongside it."""
        import shutil
        ts = time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())
        snap_dir = os.path.join(state_dir, "backups",
                                f"{ts}_{reason}")
        os.makedirs(snap_dir, exist_ok=True)
        print(f"[GualaLoom] Creating snapshot: {snap_dir}")
        # GL-CMD-WAVE-DIET-82: save WaveAtlas before snapshot
        self._save_wave_atlas(state_dir)
        # Copy identity + all state files
        for f in [self.IDENTITY_FILE] + self.STATE_FILES:
            src = os.path.join(state_dir, f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(snap_dir, f))
        # Also copy events log
        evlog = os.path.join(state_dir, self.EVENTS_LOG)
        with self._event_log_lock:
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

    @_engine_mutation_entry
    def restore_from_snapshot(self, snapshot_dir, state_dir="state"):
        """Restore a snapshot without overlapping any persistence writer."""
        with self.persistence_transaction():
            return self._restore_from_snapshot_locked(snapshot_dir, state_dir)

    def _restore_from_snapshot_locked(self, snapshot_dir, state_dir="state"):
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
        # GL-FIX-ATOMIC-RENAME-RETRY-20260713: the fsync above still leaves a
        # real, observed gap on EFS -- os.rename() has been seen raising
        # ENOENT immediately after a successful fsync (confirmed live: a
        # dozen "HOT SAVE CRITICAL FAILURE" events over ~30h, all "No such
        # file or directory: '...tmp' -> '...'", clustered every time
        # several hot-lane files rename concurrently into the same
        # directory -- a directory-entry visibility lag on the NFS client,
        # not a really-missing file; the data is already durably fsync'd
        # above, only the rename's own lookup is stale). A short bounded
        # retry is safe here specifically because nothing else in this
        # process deletes its own just-fsynced .tmp file out from under it
        # -- the only failure mode ever observed is transient ENOENT, never
        # a persistent one -- so exhausting the retries still re-raises
        # rather than silently swallowing a real failure.
        for attempt in range(4):
            try:
                os.rename(tmp, path)
                return
            except FileNotFoundError:
                if attempt == 3:
                    raise
                time.sleep(0.05 * (attempt + 1))

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
                "modes_alive": sum(1 for a in s._mode_alive if a),
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
                # GL-CMD-ORGANISM-WAVE-MEMORY-207 W5: rolling mean/max over
                # the last 50 processed items -- the honest per-item cost
                # that used to climb unbounded with lifetime history.
                "item_ms_mean": (round(sum(self._organism_item_ms_recent)
                                       / len(self._organism_item_ms_recent), 2)
                                if self._organism_item_ms_recent else 0.0),
                "item_ms_max": (round(max(self._organism_item_ms_recent), 2)
                               if self._organism_item_ms_recent else 0.0),
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
            # GL-CMD-GROWTH-TRUTH-EVE-20260705-198 P3a: per-hemisphere
            # counts, total divisions since birth, division-pool level,
            # q-charge distribution (distance to folding) -- "growth we
            # cannot see is growth we cannot verify."
            "organism_growth": self.organism.growth_snapshot(),
            # GL-CMD-COGNITION-AT-SPEED-EVE-20260705-205 C5, root-cause
            # fix: computed LIVE by get_tick_rate() at this exact read
            # time, not a value the autonomy loop cached once per second
            # (that snapshot froze during the live incident). Next to
            # running_sha: her own status now honestly answers both "what
            # code" and "how fast, right now."
            "tick_rate": round(self.get_tick_rate(), 2),
            "tick_rate_had_pending_work": getattr(self, "_tick_rate_pending_work", False),
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
            "n_visual_fragments": self._visual_fragments_count,
            "n_visual_motifs": len(self.sight.motifs),
            "sight_section": self.sight.snapshot(),
            # GL-CMD-EPISODIC-MEMORY: real, situational memories -- distinct
            # remembered moments per concept, not flattened definitions.
            # concepts_with_multiple_memories flags exactly the case Joe's
            # credo cares about (the same word holding more than one real,
            # separately-kept memory, e.g. an ice-cream-truck moment AND a
            # beach-day moment, neither overwriting the other).
            "episodic_memory": {
                "n_concepts": len(self._episodic_memory),
                "n_total_memories": sum(len(v) for v in self._episodic_memory.values()),
                "concepts_with_multiple_memories": sorted(
                    c for c, v in self._episodic_memory.items() if len(v) > 1
                )[:20],
            },
            # GL-CMD-REFLECTION-EVE-20260710: real internal representations
            # formed from episodic memory + current needs -- see
            # _form_reflection's own docstring. Not wired into speech;
            # exposed here only for observability, same as episodic_memory.
            "reflections": {
                "n_formed": len(self._reflections),
                "most_recent": (self._reflections[-1] if self._reflections else None),
            },
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
