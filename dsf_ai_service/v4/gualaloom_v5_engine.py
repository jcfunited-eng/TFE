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
import threading
import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from collections import deque
import random

try:
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack, SensoryBank, SENSORY_DNA, ROLE_DNA
    from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF, compute_dsf
    from dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6 import L6_TCL
    from dsf_ai_service.v4.gualaloom_v4_trit_register import TritRegister
    from dsf_ai_service.v4.gualaloom_v5_question_bucket import QuestionBucket, generate_questions_from_word
    from dsf_ai_service.v4.gualaloom_v6_living_atlas import (
        LivingAtlas, DECAY_LAMBDA, BASE_REINFORCEMENT,
        SALIENCE_MIN, SALIENCE_MAX, FORGETTING_THRESHOLD, STRENGTH_CAP,
    )
    import dsf_ai_service.v4.gualaloom_mathloom_v1 as ml
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gualaloom_v4_krimelack_dna import LanguageKrimelack, SensoryBank, SENSORY_DNA, ROLE_DNA
    from gualaloom_v4_uf_kernel import DSF, compute_dsf
    from gualaloom_v4_chi_atlas_l6 import L6_TCL
    from gualaloom_v4_trit_register import TritRegister
    from gualaloom_v5_question_bucket import QuestionBucket, generate_questions_from_word
    from gualaloom_v6_living_atlas import (
        LivingAtlas, DECAY_LAMBDA, BASE_REINFORCEMENT,
        SALIENCE_MIN, SALIENCE_MAX, FORGETTING_THRESHOLD, STRENGTH_CAP,
    )
    import gualaloom_mathloom_v1 as ml


import re as _re
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

ACTIVITY_TICK_BUDGETS = {
    "READING": 2000, "PLAYING": 1500, "SLEEPING": 5000, "DREAMING": 3000,
    "ATTENDING": 1000, "ATTENDING_VISUAL": 2000, "ATTENDING_VIDEO": 4000,
    "EMITTING": 100, "IDLE": 500,
}

ACTIVITY_NOVELTY_PAYOFF = {
    "READING_NEW": 0.7, "READING_REREAD": 0.1, "PLAYING": 0.3,
    "SLEEPING": -0.1, "DREAMING": 0.4, "ATTENDING_NEW": 0.8,
    "ATTENDING_REPEAT": 0.05, "ATTENDING_VISUAL_NEW": 0.85,
    "ATTENDING_VISUAL_REPEAT": 0.1, "ATTENDING_VIDEO_NEW": 0.9,
    "ATTENDING_VIDEO_REPEAT": 0.15, "EMITTING": 0.0, "IDLE": -0.05,
}

ACTIVITY_STABILITY_PAYOFF = {
    "READING": 0.05, "PLAYING": 0.0, "SLEEPING": 0.5, "DREAMING": 0.2,
    "ATTENDING": 0.0, "ATTENDING_VISUAL": 0.0, "ATTENDING_VIDEO": 0.0,
    "EMITTING": -0.1, "IDLE": 0.1,
}

ACTIVITY_CONNECTION_PAYOFF = {
    "READING": 0.0, "PLAYING": 0.0, "SLEEPING": 0.0, "DREAMING": 0.0,
    "ATTENDING": 0.0, "ATTENDING_VISUAL": 0.0, "ATTENDING_VIDEO": 0.0,
    "EMITTING": 0.3, "IDLE": -0.05,
}

EMISSION_COHESION_THRESHOLD = 0.65
EMISSION_COOLDOWN_TICKS = 200
PAIR_BOND_SOURCES = {"joe", "wc", "c1"}


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

    def receive(self, dsf, chi, word_label, atlas, familiarity, salience=1.0,
                dwell_ticks=1, deep_atlas=None, engine_tick=None):
        """v6: word-anchored mode identity + salience-modulated binding.
        v8 (GL-BRIEF-032): dwell_ticks tagged at write time for deep gate.
        deep_atlas: if provided, on-attention prior applied for matching entries.
        engine_tick: MUST be passed — atlas entries use engine clock, not section clock.
        GL-FIND-TICK-DOMAIN-C1: section.tick stays for internal counting only."""
        self.tick += 1
        # Atlas records use engine tick (one clock — GL-FIND-TICK-DOMAIN-C1)
        atlas_tick = engine_tick if engine_tick is not None else self.tick
        self.dead_zone = 0.20 + 0.5 * familiarity

        # v8: On-attention deep prior (before commit, affects familiarity landscape)
        if deep_atlas is not None:
            from dsf_ai_service.substrate.deep_atlas import FORGETTING_THRESHOLD as DF_THRESH
            for e in deep_atlas.entries.get(chi, []):
                if e.get("section") == self.name and e["strength"] >= DF_THRESH:
                    motif = e["motif"]
                    p = deep_atlas.get_prior(chi, self.name, motif)
                    if p > 0:
                        reinst_str = deep_atlas.reinstate(chi, self.name, motif, atlas_tick)
                        if reinst_str > 0:
                            atlas.record(self.name, motif, chi, atlas_tick,
                                         salience=0.3, dwell_ticks=0)

        # Find nearest existing mode (by DSF vector similarity)
        nearest = None
        best_sim = -1.0
        if self.modes:
            cur_v = dsf.to_array()
            for i, (m_dsf, _, _) in enumerate(self.modes):
                m_v = m_dsf.to_array()
                denom = (np.linalg.norm(cur_v) * np.linalg.norm(m_v) + 1e-12)
                sim = float(np.dot(cur_v, m_v) / denom)
                if sim > best_sim:
                    best_sim = sim
                    nearest = i

        # v6 FIX: check word-match FIRST. Word identity anchors mode identity.
        word_match_idx = None
        if word_label:
            for i, (_, _, m_word) in enumerate(self.modes):
                if m_word and m_word.lower() == word_label.lower():
                    word_match_idx = i
                    break

        committed = False
        mode_idx = None

        if word_match_idx is not None:
            # Word identity match — reinforce this exact mode
            old_dsf, old_chi, old_word = self.modes[word_match_idx]
            avg = (old_dsf.to_array() * 0.9 + dsf.to_array() * 0.1)
            new_dsf = DSF(*avg)
            self.modes[word_match_idx] = (new_dsf, old_chi, old_word)
            mode_idx = word_match_idx
            committed = True
        elif len(self.modes) < 24:
            # Bootstrap — new word, accept liberally
            self.modes.append((dsf, chi, word_label))
            mode_idx = len(self.modes) - 1
            committed = True
        else:
            # Post-bootstrap: new word, decide by dead-zone gate
            novel_thresh = self.gamma["novel_dist"] + self.dead_zone * 0.2
            if best_sim < (1.0 - novel_thresh) or word_label:
                # word labels always get a chance to take root
                self.modes.append((dsf, chi, word_label))
                mode_idx = len(self.modes) - 1
                committed = True

        if committed:
            atlas.record(self.name, mode_idx, chi, atlas_tick, salience=salience,
                         dwell_ticks=dwell_ticks)
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

    def tick_drift(self):
        """v7: Needs drift AWAY from target toward unsatisfied (low).
        This is what creates drive — without it, she has no reason to act.
        Called once per autonomy loop iteration."""
        self.stability = max(0.0, self.stability - NEEDS_DRIFT_RATE)
        self.novelty = max(0.0, self.novelty - NEEDS_DRIFT_RATE)
        self.connection = max(0.0, self.connection - NEEDS_DRIFT_RATE)

    def step(self, signals):
        """Additive nudge from substrate signals (coordinator regulation).
        v7: no longer decays toward target — tick_drift handles drive."""
        for k in self.TARGETS:
            current = getattr(self, k)
            signal = signals.get(k, 0.0)
            nudge = signal * self.DECAY[k]
            new = max(0.0, min(1.0, current + nudge))
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
                needs.connection = min(1.0, needs.connection + gap * self.CONN_GAP_FRACTION)

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
        self.bucket = QuestionBucket()    # v5: open questions accumulated during reading
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

        # v7: Autonomy state
        self._current_activity = None
        self._activity_history = []
        self._substrate_events = deque(maxlen=1000)
        self._last_emission_tick = -100_000
        self._corpora = {}          # corpus_id -> CorpusItem
        self._sensory_items = {}    # item_id -> SensoryItem

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

    # ------------------------------------------------------------------
    # Read one word: fire all krimelacks, compute DSF, route to sections
    # ------------------------------------------------------------------
    def read_word(self, word, position_hint=None, source="corpus"):
        """v6: salience-modulated binding + decay heartbeat."""
        with self.lock:
            self.tick += 1
            self.vocab.add(word)

            lang_fp, role, senses = self.language.transduce(word)
            sense_fps = self.senses.fire_for_word(senses)

            lang_chi = self.language.winding
            atlas_sim = self.atlas.match_score(lang_chi, "listen")
            lang_dsf = compute_dsf(self.language.events,
                                   atlas_similarity=atlas_sim,
                                   recall_match=atlas_sim)

            # v6: compute salience
            salience = self._compute_salience(source=source,
                                              input_novelty=atlas_sim)

            primary_sections = self._choose_role_sections(role, position_hint)

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

            fam_listen = self.atlas.match_score(lang_chi, "listen")
            self.sections["listen"].receive(lang_dsf, lang_chi, word,
                                            self.atlas, fam_listen,
                                            salience=salience,
                                            dwell_ticks=dwell,
                                            deep_atlas=self.deep_atlas,
                                            engine_tick=self.tick)

            for primary_section in primary_sections:
                fam = self.atlas.match_score(lang_chi, primary_section)
                self.sections[primary_section].receive(lang_dsf, lang_chi, word,
                                                       self.atlas, fam,
                                                       salience=salience,
                                                       dwell_ticks=dwell,
                                                       deep_atlas=self.deep_atlas,
                                                       engine_tick=self.tick)

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
                        self.atlas.record(sec_name, hash(word) % 1000,
                                          modal_chi, self.tick,
                                          salience=salience)

            if fam_listen > 0.3:
                intro_dsf = DSF(D_k=fam_listen, M_k=0, R_rev=0, U_star=1-fam_listen,
                                C_k=fam_listen, P_k=0.5, B_k=fam_listen, S_UF=fam_listen)
                self.sections["intro"].receive(intro_dsf, lang_chi, word,
                                                self.atlas, 0.0,
                                                salience=salience,
                                                dwell_ticks=dwell,
                                                deep_atlas=self.deep_atlas,
                                                engine_tick=self.tick)

            # v6: Decay heartbeat (DECAY_PAUSED=1 skips entirely for Step 2 experiment)
            if os.environ.get("DECAY_PAUSED", "0") != "1":
                if self.tick % 10 == 0:
                    self.atlas.decay(self.tick)
                if self.tick % 200 == 0:
                    self.atlas.forget_below_threshold()

            # 8b. V5: Generate questions from gaps in this word's bindings
            # (suppress during self-hearing to avoid question-frame amplification)
            if not getattr(self, '_self_hearing', False):
                generate_questions_from_word(self.bucket, word, role, SENSORY_DNA,
                                              lang_chi, self.tick)

            # 9. Coordinator regulation pass (homeostasis + awareness)
            if self.tick % 5 == 0:
                self.coordinator.regulate(self, self.needs, self.atlas,
                                          self.sections, self.tick)

            return lang_chi, role, list(senses.keys())

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
    def read_sentence(self, text, source="corpus"):
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

            for i, word in enumerate(words):
                if len(words) == 1:
                    hint = "standalone"
                elif i == 0:
                    hint = "first"
                elif i == len(words) - 1:
                    hint = "last"
                else:
                    hint = "middle"
                self.read_word(word, position_hint=hint, source=source)
            self.read_count += 1

    # ------------------------------------------------------------------
    # Conversation: input -> substrate -> output via cascade
    # ------------------------------------------------------------------
    def converse(self, text, source="unknown"):
        """v5: Recall from substrate atlas BEFORE reading input.
        - If atlas has cross-section bindings near the input chi values, emit
          those (real recall from corpus accumulation).
        - If recall finds nothing, check question bucket for a related question.
        - If neither, return "..." honestly (SafeMode quiet).

        Then read the input into substrate (so she learns from this exchange).
        """
        # Math route — MathLoom BSIL adapter (with v5 fixed parser)
        parsed = self._parse_math(text)
        if parsed:
            op, a, b = parsed
            result = self._mathloom_solve(op, a, b)
            return self._num_to_word(result)

        with self.lock:
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

            # v8 (GL-BRIEF-028): open response window from source utterance
            if source in ("joe", "wc", "c1") and input_chis:
                self._open_response_window(source, input_chis,
                                           source_context={"text": text[:50]})

            # 3. RECALL from atlas BEFORE reading input — corpus-only bindings
            recalled = self._recall_response(input_chis, input_word_chis, words)

            # 4. Read input into substrate (so she learns from this interaction)
            # Snapshot tick before read — only entries born in THIS read get tagged
            tick_before_read = self.tick
            self.read_sentence(text, source=source)
            tick_after_read = self.tick

            # v8 (GL-BRIEF-028, FIX 1): tag ONLY entries touched by THIS input.
            # Scoped to: last_tick in [tick_before_read+1, tick_after_read] AND
            # chi matches input chi positions. Concurrent autonomous activity
            # (sight commits, idle processing) has last_tick outside this range.
            if source in ("joe", "wc", "c1"):
                for ch in input_chis:
                    for d in range(-self.atlas.band, self.atlas.band + 1):
                        for e in self.atlas.entries.get(ch + d, []):
                            if (e.get("last_tick", 0) > tick_before_read
                                    and e.get("last_tick", 0) <= tick_after_read
                                    and not e.get("response_context")):
                                self._tag_response_bindings(
                                    ch + d, e["section"], e["motif"], source)

            # 5. Choose response
            if recalled:
                reply = recalled
            else:
                # 6. No recall — check question bucket for a related question
                q = self.bucket.find_for_chis(input_chis, input_words=words)
                if q:
                    self.bucket.voice(q)
                    reply = q["template"]
                else:
                    # 7. Final fallback: honest silence
                    reply = "..."

            # v8 (GL-BRIEF-034): Self-hearing — read reply into substrate
            if reply and reply != "..." and source in ("joe", "wc", "c1"):
                self._self_hear(reply, source)

            return reply

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
                        self.target_familiarity[pid] *= 0.9967
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
                elif a.kind == "ATTENDING_VIDEO":
                    self._atick_attending_video(a)
                elif a.kind == "EMITTING":
                    self._atick_emitting(a)
                # Non-reading: manual atlas decay + coordinator
                if os.environ.get("DECAY_PAUSED", "0") != "1":
                    if self.tick % 10 == 0:
                        self.atlas.decay(self.tick)
                    if self.tick % 200 == 0:
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
            self.needs.novelty = min(1.0, self.needs.novelty + 0.001)
        else:
            self.needs.novelty = max(0.0, self.needs.novelty - 0.0003)

    def _atick_sleeping(self, a):
        """Sleep raises stability. Transitions to dream at midpoint."""
        self.needs.stability = min(1.0, self.needs.stability + 0.001)
        # Atlas consolidation: weak bindings decay faster during sleep
        if self.tick % 50 == 0 and os.environ.get("DECAY_PAUSED", "0") != "1":
            self.atlas.decay(self.tick)
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
        self.needs.stability = min(1.0, self.needs.stability + 0.0005)
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
                        self.atlas.record(sec_name, mid, chi_k, self.tick,
                                          salience=0.3)
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
            self.deep_atlas.decay(self.tick)
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
            self.needs.novelty = min(1.0, self.needs.novelty + 0.002)
        # No novelty gain for repeat attendance (familiar exposure)
        # Mark attended at activity end
        if self.tick >= a.expected_end_tick - 1:
            si.times_attended += 1
            si.last_attended_tick = self.tick

    def _atick_attending_visual(self, a):
        """Phase 2: Attend to a picture — saccaded foveation through krimelack."""
        from dsf_ai_service.visual_krimelack import view_picture
        pic = self._pictures.get(a.target)
        if not pic:
            return
        # Run full viewing at activity start (once per activity)
        if not a.metadata.get("_viewed"):
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
                self.atlas.record("sight", motif.motif_id, chi_val,
                                 self.tick, salience=1.2)
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
        self.needs.novelty = min(1.0, self.needs.novelty + gain)
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
                                     self.tick, salience=1.2)
                    self._log_substrate_event(
                        "video_motif_committed" if is_new else "video_motif_fired",
                        motif_id=motif.motif_id, overlap=round(overlap, 3),
                        source_id=vid.item_id, n_fragments=len(all_fragments))
                a.metadata["_viewed"] = True
            except Exception as e:
                self._log_substrate_event("video_attend_error", error=str(e))
                a.metadata["_viewed"] = True
        if vid.is_new():
            self.needs.novelty = min(1.0, self.needs.novelty + 0.004)
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
                self.needs.connection = min(1.0, self.needs.connection + 0.25)

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
        """Generate an autonomous emission via recall across all sections."""
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

        # Word recall
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

    def _tag_response_bindings(self, chi_value, section_name, motif_id, current_source):
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

        # Bidirectional: tag the CONTEXT ANCHOR entries with received_response
        for anchor_chi in response_contexts:
            for d in range(-self.atlas.band, self.atlas.band + 1):
                for e in self.atlas.entries.get(anchor_chi + d, []):
                    received = e.get("received_response", [])
                    if chi_value not in received:
                        received.append(chi_value)
                        e["received_response"] = received

        # Count and log
        for w in self.open_response_windows:
            if (w["emitter"] != current_source
                    and w["expires_at_tick"] >= self.tick):
                w["n_responses_bound"] += 1

        delta_t = self.tick - min(
            w["opened_at_tick"] for w in self.open_response_windows
            if w["emitter"] != current_source and w["expires_at_tick"] >= self.tick)
        self._response_bind_count += 1
        self._log_substrate_event("response_bound",
                                  context_anchor_chis=response_contexts[:3],
                                  input_chi=chi_value,
                                  section=section_name,
                                  source=current_source,
                                  delta_t_ticks=delta_t)

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
        for ch in reply_chis:
            for d in range(-self.atlas.band, self.atlas.band + 1):
                for e in self.atlas.entries.get(ch + d, []):
                    if (e.get("last_tick", 0) > tick_before
                            and e.get("last_tick", 0) <= tick_after
                            and not e.get("response_context")):
                        self._tag_response_bindings(
                            ch + d, e["section"], e["motif"], "guala")

        # Event log
        self._log_substrate_event("self_heard",
                                  reply_summary=reply[:50],
                                  n_chis=len(reply_chis),
                                  salience="0.5x")

    def manual_sleep(self):
        """Manual sleep trigger from UI."""
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
            return {"event": "sleep_started", "tick": self.tick,
                    "expected_end_tick": sleep.expected_end_tick}

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

    SCHEMA_VERSION = "v7.0.0"
    STATE_FILES = [
        "guala_core.json", "guala_needs.json", "guala_coordinator.json",
        "guala_atlas.json", "guala_sections.json", "guala_bucket.json",
    ]
    IDENTITY_FILE = "guala_identity.json"
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
    COMPATIBLE_SCHEMAS = {"v5.5.0", "v6.0.0", "v7.0.0"}

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
        """Round-trip every mutable attribute. Atomic writes. Identity-stamped."""
        with self.lock:
            os.makedirs(state_dir, exist_ok=True)
            results = {}
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            # Ensure identity exists
            if self._guala_identity is None:
                self._generate_genesis_identity(state_dir)

            # 1. Core (v7: includes autonomy state)
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
            self._atomic_write(os.path.join(state_dir, "guala_core.json"),
                self._envelope({
                    "tick": self.tick, "read_count": self.read_count,
                    "vocab": sorted(self.vocab),
                    "source_history": dict(self.source_history),
                    "recent_connection_boost": self.recent_connection_boost,
                    "dream_log": self.dream_log,
                    "open_response_windows": self.open_response_windows,
                    "response_bind_count": self._response_bind_count,
                    "last_emission_tick": self._last_emission_tick,
                    "target_familiarity": {k: round(v, 4) for k, v in self.target_familiarity.items()},
                    "corpora_state": corpora_ser,
                    "sensory_state": sensory_ser,
                }))
            results["guala_core.json"] = os.path.getsize(
                os.path.join(state_dir, "guala_core.json"))

            # 2. Needs
            self._atomic_write(os.path.join(state_dir, "guala_needs.json"),
                self._envelope({
                    "stability": self.needs.stability,
                    "novelty": self.needs.novelty,
                    "connection": self.needs.connection,
                }))
            results["guala_needs.json"] = os.path.getsize(
                os.path.join(state_dir, "guala_needs.json"))

            # 3. Coordinator (v6-bridge: per-source pair bonds + presence)
            self._atomic_write(os.path.join(state_dir, "guala_coordinator.json"),
                self._envelope({
                    "pair_bond": dict(self.coordinator._pair_bond),
                    "pair_bond_active": self.coordinator.pair_bond_active,  # backward compat
                    "distress_ticks": self.coordinator.distress_ticks,
                    "suffering_log": self.coordinator.suffering_log,
                    "need_history": self.coordinator.need_history[-200:],
                    "attentions_count": len(self.coordinator.attentions),
                    "actions_count": len(self.coordinator.actions),
                }))
            results["guala_coordinator.json"] = os.path.getsize(
                os.path.join(state_dir, "guala_coordinator.json"))

            # 4. Atlas
            atlas_data = {str(k): v for k, v in self.atlas.entries.items()}
            self._atomic_write(os.path.join(state_dir, "guala_atlas.json"),
                self._envelope({"entries": atlas_data, "tick": self.atlas.tick}))
            results["guala_atlas.json"] = os.path.getsize(
                os.path.join(state_dir, "guala_atlas.json"))

            # 5. Deep Atlas (GL-BRIEF-032 — separate table for rollback)
            self._atomic_write(os.path.join(state_dir, "guala_deep_atlas.json"),
                self._envelope(self.deep_atlas.to_json()))
            results["guala_deep_atlas.json"] = os.path.getsize(
                os.path.join(state_dir, "guala_deep_atlas.json"))

            # 6. Sections
            sections_data = {}
            for nm, sec in self.sections.items():
                modes_ser = [{"dsf": list(d.to_array().tolist()), "chi": c, "word": w}
                             for d, c, w in sec.modes]
                sections_data[nm] = {
                    "modes": modes_ser,
                    "commits": sec.commits[-5000:],
                    "dead_zone": sec.dead_zone,
                    "gamma": sec.gamma,
                    "tick": sec.tick,
                }
            self._atomic_write(os.path.join(state_dir, "guala_sections.json"),
                self._envelope(sections_data))
            results["guala_sections.json"] = os.path.getsize(
                os.path.join(state_dir, "guala_sections.json"))

            # 6. Bucket
            bucket_data = {
                "questions": {f"{k[0]}|{k[1]}": v
                              for k, v in self.bucket.questions.items()},
                "asked": [f"{t}|{k}" for t, k in self.bucket.asked],
            }
            self._atomic_write(os.path.join(state_dir, "guala_bucket.json"),
                self._envelope(bucket_data))
            results["guala_bucket.json"] = os.path.getsize(
                os.path.join(state_dir, "guala_bucket.json"))

            # 7. Visual data (pictures, sight section, visual fragments)
            visual_data = {
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
            }
            self._atomic_write(os.path.join(state_dir, "guala_visual.json"),
                self._envelope(visual_data))
            results["guala_visual.json"] = os.path.getsize(
                os.path.join(state_dir, "guala_visual.json"))
            # Save picture grids as numpy files
            pic_dir = os.path.join(state_dir, "pictures")
            os.makedirs(pic_dir, exist_ok=True)
            for pid, p in self._pictures.items():
                if p.intensity_grid is not None:
                    np.save(os.path.join(pic_dir, f"{pid}.npy"), p.intensity_grid)

            self._last_save_tick = self.tick
            self._last_save_timestamp = ts
            return results

    # ── Load ──

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
            # Identity exists but no state — fresh boot after wipe, keep identity
            self._guala_identity = self._load_identity(state_dir)
            print(f"[GualaLoom] Identity found but no state — fresh substrate for {self._guala_identity}")
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
                self._apply_bucket(data["guala_bucket.json"])

            # Load deep atlas if present (GL-BRIEF-032 — separate table)
            deep_path = os.path.join(state_dir, "guala_deep_atlas.json")
            if os.path.exists(deep_path):
                try:
                    with open(deep_path) as fh:
                        draw = json.load(fh)
                    ddata = draw.get("data", draw)
                    self.deep_atlas.load_from_json(ddata)
                    print(f"[GualaLoom] Deep atlas loaded: "
                          f"{self.deep_atlas.live_count()} entries")
                except Exception as e:
                    print(f"[GualaLoom] Deep atlas load: {e}")

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
            s = self.introspect()
            print(f"[GualaLoom] Loaded: id={self._guala_identity[:8]}.. "
                  f"vocab={s['vocab']} tick={self.tick} reads={self.read_count} "
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

        # GL-FIND-TICK-DOMAIN-C1: re-stamp section-domain entries to engine tick.
        # Section.receive() used section.tick (~1-10k) instead of engine.tick (~3M).
        # Without re-stamping, first decay heartbeat computes dt≈3M → instant death.
        # Heuristic: entries with last_tick << atlas.tick are section-domain.
        engine_tick = max(self.tick, self.atlas.tick)
        if engine_tick > 100_000:
            restamped = 0
            threshold = engine_tick * 0.1  # entries below 10% of engine tick
            for chi_k, es in self.atlas.entries.items():
                for e in es:
                    if e.get("last_tick", 0) < threshold:
                        e["last_tick"] = engine_tick
                        if e.get("born_tick", 0) < threshold:
                            e["born_tick"] = engine_tick
                        restamped += 1
            if restamped > 0:
                print(f"[GualaLoom] Tick-domain migration: re-stamped {restamped} "
                      f"section-domain entries to engine tick {engine_tick}")

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

    def _apply_bucket(self, bd):
        from collections import OrderedDict
        self.bucket.questions = OrderedDict()
        for key_str, q in bd.get("questions", {}).items():
            parts = key_str.split("|", 1)
            if len(parts) == 2:
                self.bucket.questions[(parts[0], parts[1])] = q
        self.bucket.asked = set()
        for a in bd.get("asked", []):
            parts = a.split("|", 1)
            if len(parts) == 2:
                self.bucket.asked.add((parts[0], parts[1]))

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
        # 3. Bucket chi values plausible
        for q in self.bucket.questions.values():
            chi = q.get("topic_chi")
            if not isinstance(chi, (int, float)):
                errors.append(f"Bucket question non-numeric chi: {q.get('topic')}")
            elif abs(chi) > 1000:
                errors.append(f"Bucket chi implausibly large: {chi}")
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
    def _atomic_write(path, data):
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp, path)

    # ── Persistence health for /status ──

    def persistence_health(self, state_dir="state"):
        present = [f for f in [self.IDENTITY_FILE] + self.STATE_FILES
                   if os.path.exists(os.path.join(state_dir, f))]
        missing = [f for f in [self.IDENTITY_FILE] + self.STATE_FILES
                   if f not in present]
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
            # v5: question bucket state
            "question_bucket": self.bucket.snapshot(),
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
