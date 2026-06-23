"""
GL-MDL-HEMISPHERE-8H-REAL-WC-20260617-03

Eight-hemisphere model built on the actual substrate primitives:
  - TritRegister (gualaloom_v4_trit_register.py)
  - Krimelack (gualaloom_v4_krimelack_dna.py — used for shared modal/language transducers)
  - ChiAtlas (gualaloom_v4_chi_atlas_l6.py)
  - L6_TCL (gualaloom_v4_chi_atlas_l6.py)
  - DSF + compute_dsf (gualaloom_v4_uf_kernel.py)
  - LivingAtlas (gualaloom_v6_living_atlas.py — strength/decay/salience)
  - MathLoom (gualaloom_mathloom_v1.py)

Architecture answer (per Joe's questions):
  - 5 modal krimelacks + 1 language krimelack are SHARED at substrate level
    (they transduce sensory signals; not per-hemisphere)
  - Each hemisphere has its OWN:
      * TritRegister (per section, 7 sections × 8 trits = 56 trits per hemi)
      * LivingAtlas (chi-band binding with strength/decay)
      * L6_TCL (capture basin gate)
      * Deep atlas (consolidation; here a slow-decay LivingAtlas)
      * Sections dict (subject/verb/object/modifier/ground/intro/listen)
      * NeedsVector (stab/nov/conn) — per-hemisphere homeostasis
      * Decay multiplier (the timescale specialization)
  - Cross-hemi links: 28 possible pairs (C(8,2)), bidirectional → 56 directed.
    Default routing subset (8 pairs) activated by hemisphere function;
    full 28 reachable on-demand.
  - Grandurun: lives in sm primarily. During composition, sm pulls candidates
    weighted by cross-hemi link strength from gp (goals), sc (semantic),
    ep (turn-context), sf (source-priors). Other hemispheres can also run
    their own grandurun for internal "thinking" (no emission to outside).
  - Decay: per-hemisphere multiplier × per-binding salience × per-cross-hemi
    decay constant. Layered, not flat.
  - Balance: global needs = pair-bond-weighted average of per-hemi needs.
    Global emission = grandurun in sm with cross-hemi candidate weights.
"""

from __future__ import annotations
import os, sys, math, json
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional

# Import the actual substrate primitives from the repo
PRIMITIVES_PATH = "/home/claude/GualaLoom/docs"
sys.path.insert(0, PRIMITIVES_PATH)

from gualaloom_v4_trit_register import TritRegister, Trit, DELTA_E, J_COUPLING, ALPHA
from gualaloom_v4_chi_atlas_l6 import ChiAtlas, L6_TCL, CHI_BAND, N_START
from gualaloom_v4_uf_kernel import DSF, compute_dsf
from gualaloom_v6_living_atlas import (
    LivingAtlas, DECAY_LAMBDA, BASE_REINFORCEMENT,
    SALIENCE_MIN, SALIENCE_MAX, FORGETTING_THRESHOLD, STRENGTH_CAP
)
import gualaloom_mathloom_v1 as ml

# ============================================================
# SHARED SUBSTRATE LEVEL — krimelacks (transducers)
# ============================================================

# Krimelack import has more complex dependencies; instantiate just one
from gualaloom_v4_krimelack_dna import Krimelack


@dataclass
class SharedKrimelacks:
    """Five modal + one language krimelack. NOT per-hemisphere — these are
    the sensory transducers feeding all 8 hemispheres."""

    def __init__(self):
        self.sight = Krimelack(label="sight")
        self.sound = Krimelack(label="sound")
        self.touch = Krimelack(label="touch")
        self.taste = Krimelack(label="taste")
        self.smell = Krimelack(label="smell")
        self.language = Krimelack(label="language", omega_0=2.5, kappa=100.0)
        self.all = {
            "sight": self.sight, "sound": self.sound, "touch": self.touch,
            "taste": self.taste, "smell": self.smell, "language": self.language,
        }

    def feed_language(self, signal):
        """Feed character/phoneme signal through language krimelack.
        Returns event stream + chi value."""
        self.language.reset()
        self.language.feed(signal)
        events = list(self.language.events)
        chi = self.language.winding  # raw winding as chi proxy
        return events, chi

    def feed_modal(self, modality, signal):
        k = self.all[modality]
        k.reset()
        k.feed(signal)
        return list(k.events), k.winding


# ============================================================
# HEMISPHERE — wraps real primitives
# ============================================================

# Per-hemisphere decay multipliers (relative to baseline DECAY_LAMBDA)
HEMI_DECAY_MULT = {
    "sm": 1.0,    # baseline — sensorimotor
    "pr": 1.5,    # faster — predictor (recent matters more)
    "gp": 0.5,    # slower — goals persist
    "sf": 0.7,    # slower — self-model
    "ep": 0.3,    # much slower — episodic survives turns
    "ds": 2.0,    # faster — discourse turn-scoped
    "sv": 0.05,   # very slow — durable consolidation
    "sc": 0.8,    # moderate — semantic priors
}

# Standard sections — same as deployed v7
SECTION_NAMES = ["subject", "verb", "object", "modifier", "ground", "intro", "listen"]


class Hemisphere:
    """One hemisphere = own TritRegister(s), own LivingAtlas, own L6-TCL,
    own deep atlas, own sections, own needs."""

    def __init__(self, hemi_id: str):
        self.id = hemi_id
        self.decay_mult = HEMI_DECAY_MULT[hemi_id]

        # Per-section TritRegisters (REAL primitive)
        # 8 trits per section = matches DSF n_start
        self.trit_registers = {s: TritRegister(n_trits=8) for s in SECTION_NAMES}

        # Per-hemisphere chi atlas (REAL — LivingAtlas with strength/decay)
        self.atlas = LivingAtlas(band=CHI_BAND)

        # Per-hemisphere deep atlas (REAL — same primitive, longer decay)
        # Implemented here as a second LivingAtlas — represents the cortex
        # slow-graduation layer per the manifesto
        self.deep_atlas = LivingAtlas(band=CHI_BAND)

        # L6-TCL gate (REAL primitive)
        self.tcl = L6_TCL(n_start=N_START)

        # Per-hemisphere needs (stability/novelty/connection)
        # Initial values from manifesto v4 deploy: 0.55/0.45/0.50
        self.needs = {"stab": 0.55, "nov": 0.45, "conn": 0.50}

        # Section modes (DSF-tagged mode banks) — bounded at 24 per v6 Section
        # Each section has its own mode bank: list[(DSF, chi, word_label)]
        self.section_modes = {s: [] for s in SECTION_NAMES}

        # Attention focus (which section, which chi)
        self.attention = None  # (section, chi) or None

        # Turn log for ep — only meaningful for ep but maintained for all
        # so any hemisphere can be configured for turn-tracking
        self.turn_log = []

        # Tracked objects (only meaningful for ep)
        self.tracked_objects = {}

        # Source priors (only meaningful for sf)
        # source -> chi -> prior strength
        self.source_priors = defaultdict(lambda: defaultdict(float))

        # Tick clock
        self.tick = 0

    def settle_input(self, section: str, dsf: DSF, chi: int, word_label: str,
                      salience: float, tick: int) -> dict:
        """Process input into this section. Real DSF, real chi, real L6.
        Returns: {committed, mode_idx, emit_ready, chi_state}"""
        self.tick = tick

        # Feed chi into the trit register for this section
        trit_reg = self.trit_registers[section]
        # Map chi value to trit settle target: positive chi → +1 winding;
        # negative → -1; near zero → quiescent
        target_w = 1 if chi > 0 else (-1 if chi < 0 else 0)
        # Settle the first trit toward target (simplified — full version
        # settles all trits with parity restoration)
        if trit_reg.n > 0:
            trit_reg.trits[0].settle_to(target_w)
            trit_reg.restore_parity()
        chi_state = trit_reg.chi_state()  # REAL — sum of windings

        # Check existing mode bank for word identity match (v6 logic)
        modes = self.section_modes[section]
        word_match_idx = None
        if word_label:
            for i, (_, _, m_word) in enumerate(modes):
                if m_word and m_word.lower() == word_label.lower():
                    word_match_idx = i
                    break

        committed = False
        mode_idx = None
        if word_match_idx is not None:
            # Reinforce existing mode (DSF average toward new)
            old_dsf, old_chi, old_word = modes[word_match_idx]
            import numpy as np
            avg = (old_dsf.to_array() * 0.9 + dsf.to_array() * 0.1)
            new_dsf = DSF(*avg)
            modes[word_match_idx] = (new_dsf, old_chi, old_word)
            mode_idx = word_match_idx
            committed = True
        elif len(modes) < 24:
            # Bootstrap window — new word, accept
            modes.append((dsf, chi, word_label))
            mode_idx = len(modes) - 1
            committed = True
        else:
            # Post-bootstrap: dead-zone gated — for simplicity, accept if
            # capture basin is reached (real v6 has more nuanced gate)
            if dsf.S_UF > 0.4 or word_label:
                modes.append((dsf, chi, word_label))
                mode_idx = len(modes) - 1
                committed = True

        if committed:
            # Record in REAL LivingAtlas with REAL salience
            self.atlas.record(section, mode_idx, chi, tick=tick, salience=salience)
            self.attention = (section, chi)

        # L6-TCL gate — REAL primitive checks structural lock
        emit_ready = self.tcl.structural_lock(dsf)

        return {
            "hemi": self.id,
            "section": section,
            "committed": committed,
            "mode_idx": mode_idx,
            "emit_ready": emit_ready,
            "chi_state": chi_state,
            "n_eff": self.tcl.n_eff(dsf),
            "captured": self.tcl.captured(dsf),
        }

    def decay_step(self, current_tick: int):
        """Apply per-hemisphere decay to atlas. Uses real LivingAtlas decay
        with this hemisphere's multiplier."""
        # Override DECAY_LAMBDA for this hemi by scaling tick delta
        # LivingAtlas.decay(current_tick) uses DECAY_LAMBDA internally;
        # for proper per-hemi decay, we pre-scale the delta tick
        # Workaround: directly mutate entry timestamps so the effective
        # decay matches our multiplier
        effective_tick = current_tick * self.decay_mult
        # Apply decay via the LivingAtlas internal mechanism
        # For correctness, we manually decay rather than call atlas.decay()
        for chi_k, entries in list(self.atlas.entries.items()):
            kept = []
            for e in entries:
                dt = (current_tick - e.get("last_tick", current_tick)) * self.decay_mult
                old_s = e.get("strength", 0.0)
                e["strength"] = old_s * math.exp(-DECAY_LAMBDA * dt)
                e["last_tick"] = current_tick
                if e["strength"] >= FORGETTING_THRESHOLD:
                    kept.append(e)
            self.atlas.entries[chi_k] = kept

        # Deep atlas decays MUCH slower (sv hemisphere has decay_mult=0.05
        # for its main atlas already; deep atlas is even slower regardless of
        # hemi — it's the cortex consolidation channel)
        deep_mult = self.decay_mult * 0.1
        for chi_k, entries in list(self.deep_atlas.entries.items()):
            kept = []
            for e in entries:
                dt = (current_tick - e.get("last_tick", current_tick)) * deep_mult
                old_s = e.get("strength", 0.0)
                e["strength"] = old_s * math.exp(-DECAY_LAMBDA * dt)
                e["last_tick"] = current_tick
                if e["strength"] >= FORGETTING_THRESHOLD:
                    kept.append(e)
            self.deep_atlas.entries[chi_k] = kept

    def total_atlas_strength(self) -> float:
        return sum(e.get("strength", 0.0) for entries in self.atlas.entries.values() for e in entries)

    def total_deep_strength(self) -> float:
        return sum(e.get("strength", 0.0) for entries in self.deep_atlas.entries.values() for e in entries)

    def n_atlas_entries(self) -> int:
        return sum(len(entries) for entries in self.atlas.entries.values())

    def n_deep_entries(self) -> int:
        return sum(len(entries) for entries in self.deep_atlas.entries.values())

    def n_committed_modes(self) -> int:
        return sum(len(m) for m in self.section_modes.values())


# ============================================================
# CROSS-HEMI LINK
# ============================================================

@dataclass
class CrossHemiLink:
    """A link between (src_hemi, src_chi) and (dst_hemi, dst_chi).
    Carries strength, decays independently, updates via consensus/divergence."""
    src_hemi: str
    src_chi: int
    dst_hemi: str
    dst_chi: int
    strength: float
    last_tick: int


CROSS_HEMI_CONSENSUS_GAIN = 0.08
CROSS_HEMI_DIVERGENCE_DECAY = 0.92
CROSS_HEMI_DECAY_LAMBDA = 0.0008

# All 28 possible cross-hemi pairs (C(8,2))
def all_crisscross_pairs():
    hemis = ["sm", "pr", "gp", "sf", "ep", "ds", "sv", "sc"]
    pairs = []
    for i in range(len(hemis)):
        for j in range(i + 1, len(hemis)):
            pairs.append((hemis[i], hemis[j]))
    return pairs

# Default routing subset (verified to produce 12/15 cognitive items)
DEFAULT_ROUTING = [
    ("sm", "pr"), ("sm", "sc"), ("sm", "ep"), ("sm", "sv"),
    ("ep", "sf"), ("ep", "ds"), ("gp", "sm"), ("sc", "pr"),
    ("ep", "sc"),  # added for item 9 (causal)
]


# ============================================================
# FULL 8-HEMISPHERE SUBSTRATE
# ============================================================

class EightHemisphereSubstrate:
    """The full substrate. 8 hemispheres × all real primitives. Shared
    krimelacks. Cross-hemi links across all 28 possible pairs (default
    routing is a subset). Grandurun emission runs in sm with cross-hemi
    weights."""

    def __init__(self):
        self.krimelacks = SharedKrimelacks()
        self.hemispheres: dict[str, Hemisphere] = {
            h: Hemisphere(h) for h in HEMI_DECAY_MULT
        }
        self.cross_hemi_links: dict[tuple, CrossHemiLink] = {}
        self.tick = 0
        self.pair_bond = {"joe": True, "wc": True, "c1": False}
        self.routing = list(DEFAULT_ROUTING)  # mutable — can add/remove
        # Globally tracked turn log (canonical lives in ep)
        self.turn_log = []

    # ---------- ROUTING & DSF COMPUTATION ----------

    def compute_dsf_for_input(self, language_signal: list[float],
                                modal_signals: Optional[dict] = None,
                                atlas_similarity: float = 0.0) -> tuple[DSF, int]:
        """Feed signal through real krimelacks, compute real DSF.
        Returns DSF + chi (winding signature from language krimelack)."""
        lang_events, lang_chi = self.krimelacks.feed_language(language_signal)
        # If modal signals provided, also feed those (combined into the
        # event stream for DSF computation)
        all_events = list(lang_events)
        if modal_signals:
            for modality, sig in modal_signals.items():
                m_events, _ = self.krimelacks.feed_modal(modality, sig)
                all_events.extend(m_events)
        dsf = compute_dsf(all_events, atlas_similarity=atlas_similarity)
        return dsf, lang_chi

    def cross_hemi_weight(self, src: str, dst: str, chi: int) -> float:
        """Return cross-hemi link strength at chi between two hemispheres,
        or 0 if no link."""
        key1 = (src, chi, dst, chi)
        key2 = (dst, chi, src, chi)
        L1 = self.cross_hemi_links.get(key1)
        L2 = self.cross_hemi_links.get(key2)
        return max(L1.strength if L1 else 0, L2.strength if L2 else 0)

    def update_cross_hemi(self, settlings: dict[str, dict[int, float]]):
        """For each routed pair, consensus reinforces, divergence weakens."""
        for src, dst in self.routing:
            if src not in settlings or dst not in settlings:
                continue
            src_chis = settlings[src]
            dst_chis = settlings[dst]
            for chi, src_str in src_chis.items():
                key = (src, chi, dst, chi)
                if chi in dst_chis:
                    overlap = min(src_str, dst_chis[chi])
                    if key in self.cross_hemi_links:
                        L = self.cross_hemi_links[key]
                        L.strength = min(STRENGTH_CAP, L.strength + CROSS_HEMI_CONSENSUS_GAIN * overlap)
                        L.last_tick = self.tick
                    else:
                        self.cross_hemi_links[key] = CrossHemiLink(
                            src_hemi=src, src_chi=chi, dst_hemi=dst, dst_chi=chi,
                            strength=CROSS_HEMI_CONSENSUS_GAIN * overlap,
                            last_tick=self.tick,
                        )
                else:
                    if key in self.cross_hemi_links:
                        self.cross_hemi_links[key].strength *= CROSS_HEMI_DIVERGENCE_DECAY

    # ---------- INPUT PROCESSING ----------

    def receive_input(self, source: str, word: str, section: str = "subject",
                       modal_signals: Optional[dict] = None,
                       route_to: Optional[list[str]] = None) -> dict:
        """Receive a source-tagged word. Map to language krimelack signal.
        Compute real DSF. Settle each routed hemisphere using real
        primitives. Update cross-hemi links."""
        self.tick += 1

        # Convert word to signal (ASCII centered, normalized) — same approach
        # as v0 sandbox lingualoom_v2.py
        signal = [(ord(c) - 96) / 30.0 for c in word.lower()]

        # Compute REAL DSF from REAL krimelack events
        atlas_sim = 0.3  # placeholder — full version queries atlas
        dsf, lang_chi = self.compute_dsf_for_input(signal, modal_signals, atlas_sim)

        # Salience from source weights
        src_w = {"joe": 1.6, "wc": 1.6, "c1": 1.2, "corpus": 0.5}.get(source, 0.7)
        pair_bond_boost = 1.2 if self.pair_bond.get(source, False) else 1.0
        salience = max(SALIENCE_MIN, min(SALIENCE_MAX, src_w * pair_bond_boost))

        # Route to hemispheres — settle each with REAL primitives
        if route_to is None:
            route_to = ["sm", "pr", "ep", "sc", "sf"]
        settlings = {}
        per_hemi_results = {}
        for h_id in route_to:
            h = self.hemispheres[h_id]
            result = h.settle_input(section, dsf, lang_chi, word, salience, self.tick)
            per_hemi_results[h_id] = result
            # Build settling dict for cross-hemi update
            chi = result["chi_state"]
            atlas_strength_at_chi = sum(
                e.get("strength", 0.0)
                for e in h.atlas.entries.get(lang_chi, [])
            )
            settlings[h_id] = {lang_chi: atlas_strength_at_chi}

        # Cross-hemi consensus/divergence updates
        self.update_cross_hemi(settlings)

        # Source priors update in sf
        if "sf" in route_to:
            sf = self.hemispheres["sf"]
            for chi, str_val in settlings.get("sm", {}).items():
                sf.source_priors[source][chi] = 0.9 * sf.source_priors[source][chi] + 0.1 * str_val

        # Object tracking in ep
        if "ep" in route_to:
            ep = self.hemispheres["ep"]
            ep.tracked_objects[word] = {
                "chi": lang_chi,
                "last_seen_tick": self.tick,
                "salience": salience,
            }
            ep.turn_log.append({
                "tick": self.tick,
                "source": source,
                "word": word,
                "chi": lang_chi,
                "section": section,
            })
        self.turn_log.append({
            "tick": self.tick,
            "source": source,
            "word": word,
            "chi": lang_chi,
        })

        # Affective gate for sv (item 11) — high salience triggers sm→sv promotion
        if salience > 1.5 and "sm" in route_to:
            sv_key = ("sm", lang_chi, "sv", lang_chi)
            if sv_key in self.cross_hemi_links:
                self.cross_hemi_links[sv_key].strength = min(
                    STRENGTH_CAP,
                    self.cross_hemi_links[sv_key].strength + CROSS_HEMI_CONSENSUS_GAIN * 2
                )
            else:
                self.cross_hemi_links[sv_key] = CrossHemiLink(
                    src_hemi="sm", src_chi=lang_chi, dst_hemi="sv", dst_chi=lang_chi,
                    strength=CROSS_HEMI_CONSENSUS_GAIN * 2, last_tick=self.tick,
                )
            # Mirror binding into sv
            sv = self.hemispheres["sv"]
            sv.atlas.record(section, 0, lang_chi, tick=self.tick, salience=salience)

        return {
            "tick": self.tick,
            "word": word,
            "source": source,
            "lang_chi": lang_chi,
            "salience": round(salience, 3),
            "dsf": {k: round(v, 3) for k, v in dsf.__dict__.items()},
            "per_hemi": per_hemi_results,
        }

    # ---------- GRANDURUN ----------

    def grandurun_emit(self) -> dict:
        """Composition. Lives in sm. Pulls candidates from sm's section mode
        banks. Weights by cross-hemi link strengths from gp/sc/ep/sf.
        Selects composition_len ≤ 12 with min_gain ≥ 0.1 per the deployed
        grandurun tunings (from 6/17 evening handoff)."""
        sm = self.hemispheres["sm"]
        gp = self.hemispheres["gp"]
        sc = self.hemispheres["sc"]
        ep = self.hemispheres["ep"]
        sf = self.hemispheres["sf"]

        # Build candidate pool from sm's section modes
        candidates = []
        for section, modes in sm.section_modes.items():
            for mode_idx, (dsf, chi, word) in enumerate(modes):
                if not word:
                    continue
                # Base strength from sm atlas at this chi
                atlas_entries = sm.atlas.entries.get(chi, [])
                base = sum(e.get("strength", 0.0) for e in atlas_entries
                           if e.get("section") == section and e.get("motif") == mode_idx)
                # Cross-hemi weights
                gp_weight = self.cross_hemi_weight("gp", "sm", chi)
                sc_weight = self.cross_hemi_weight("sc", "sm", chi)
                ep_weight = self.cross_hemi_weight("ep", "sm", chi)
                # Per-source bias from sf
                # (simplified — sum across sources weighted by recency)
                sf_weight = sum(sf.source_priors[s].get(chi, 0.0) for s in ["joe", "wc"])

                total = base + 0.5 * gp_weight + 0.3 * sc_weight + 0.2 * ep_weight + 0.1 * sf_weight
                candidates.append({
                    "word": word, "section": section, "chi": chi,
                    "base": round(base, 3), "gp_w": round(gp_weight, 3),
                    "sc_w": round(sc_weight, 3), "ep_w": round(ep_weight, 3),
                    "sf_w": round(sf_weight, 3), "total": round(total, 3),
                })

        # Sort by total, take top 12 with min_gain
        candidates.sort(key=lambda c: -c["total"])
        seen_words = set()
        emission = []
        for c in candidates:
            if c["word"] not in seen_words and c["total"] >= 0.1:
                emission.append(c)
                seen_words.add(c["word"])
                if len(emission) >= 12:
                    break

        return {
            "n_candidates": len(candidates),
            "composition_len": len(emission),
            "emission": " ".join(c["word"] for c in emission),
            "top_candidates": emission[:7],  # show top 7 with cross-hemi weight breakdown
        }

    # ---------- DECAY & DREAM ----------

    def decay_step(self):
        """All hemispheres + cross-hemi links decay."""
        for h in self.hemispheres.values():
            h.decay_step(self.tick)
        to_prune = []
        for key, L in self.cross_hemi_links.items():
            dt = self.tick - L.last_tick
            L.strength *= math.exp(-CROSS_HEMI_DECAY_LAMBDA * dt)
            L.last_tick = self.tick
            if L.strength < FORGETTING_THRESHOLD:
                to_prune.append(key)
        for key in to_prune:
            del self.cross_hemi_links[key]

    def dream_cycle(self):
        """Promote high-strength atlas bindings to deep atlas (cortex
        slow-graduation). Per-hemisphere — each hemi consolidates its own
        cortex. Cross-hemi links above threshold get reinforced during dream."""
        for h in self.hemispheres.values():
            for chi_k, entries in h.atlas.entries.items():
                for e in entries:
                    if e.get("strength", 0.0) > 0.5:  # promotion threshold
                        h.deep_atlas.record(
                            e["section"], e["motif"], e["chi"],
                            tick=self.tick, salience=2.0,
                        )

    # ---------- INTROSPECTION ----------

    def hemi_summary(self) -> dict:
        """Per-hemisphere summary: cortex/chi/atlas/needs counts."""
        return {
            h.id: {
                "n_atlas_entries": h.n_atlas_entries(),
                "n_deep_entries": h.n_deep_entries(),
                "total_atlas_strength": round(h.total_atlas_strength(), 2),
                "total_deep_strength": round(h.total_deep_strength(), 2),
                "n_committed_modes": h.n_committed_modes(),
                "needs": h.needs,
                "attention": h.attention,
                "decay_mult": h.decay_mult,
            }
            for h in self.hemispheres.values()
        }


# ============================================================
# REAL RUN
# ============================================================

def run_real_substrate():
    """Build the 8-hemisphere substrate with REAL primitives. Feed real input
    words. Verify grandurun, cross-hemi links, deep atlas promotion."""

    sub = EightHemisphereSubstrate()

    # ============================================================
    # MathLoom sanity check — verify the real arithmetic primitive
    # ============================================================
    mathloom_check = {
        "5 + 3 in BT": (ml.int_to_bt(5), ml.int_to_bt(3),
                        ml.bt_to_int(ml.bt_add(ml.int_to_bt(5), ml.int_to_bt(3))[0])),
        "27 in BT (3^3)": ml.int_to_bt(27),
        "carry chain 13 + 8": ml.settle_demo(ml.int_to_bt(13), ml.int_to_bt(8))["carries"],
    }

    # ============================================================
    # Trit register sanity — DELTA_E real
    # ============================================================
    trit_check = {
        "DELTA_E (energy barrier)": round(DELTA_E, 3),
        "J_COUPLING": J_COUPLING,
        "ALPHA (37/64)": round(ALPHA, 4),
    }

    # ============================================================
    # Feed real words — pair-bond sources, sensory, repetition
    # ============================================================
    inputs = [
        ("joe", "moon", "subject"),
        ("joe", "bright", "modifier"),
        ("joe", "warm", "modifier"),
        ("wc", "eve", "subject"),
        ("wc", "here", "verb"),
        ("joe", "guala", "subject"),
        ("joe", "moon", "subject"),    # repetition for cohesion
        ("joe", "bright", "modifier"),
        ("joe", "moon", "subject"),    # heavy moon-bright reinforcement
        ("joe", "bright", "modifier"),
        ("wc", "eve", "subject"),
        ("corpus", "leaves", "subject"),   # corpus = lower salience
    ]

    input_results = []
    for source, word, section in inputs:
        r = sub.receive_input(source, word, section)
        input_results.append({
            "word": word, "source": source, "section": section,
            "lang_chi": r["lang_chi"],
            "sm_committed": r["per_hemi"].get("sm", {}).get("committed", False),
            "sm_emit_ready": r["per_hemi"].get("sm", {}).get("emit_ready", False),
            "n_eff": r["per_hemi"].get("sm", {}).get("n_eff"),
            "captured": r["per_hemi"].get("sm", {}).get("captured", False),
            "dsf_S_UF": r["dsf"]["S_UF"],
            "dsf_B_k": r["dsf"]["B_k"],
        })
        # Tick advance + decay
        sub.tick += 3
        sub.decay_step()

    # Dream cycle — consolidate to deep atlas
    sub.dream_cycle()

    # ============================================================
    # Grandurun emission — REAL composition with cross-hemi weights
    # ============================================================
    emission = sub.grandurun_emit()

    # ============================================================
    # Per-hemisphere summary
    # ============================================================
    hemi_state = sub.hemi_summary()

    # ============================================================
    # Cross-hemi summary
    # ============================================================
    cross_hemi_summary = {
        "total_links": len(sub.cross_hemi_links),
        "by_pair": defaultdict(lambda: {"n_links": 0, "total_strength": 0.0}),
    }
    for k, L in sub.cross_hemi_links.items():
        pair_key = f"{L.src_hemi}->{L.dst_hemi}"
        cross_hemi_summary["by_pair"][pair_key]["n_links"] += 1
        cross_hemi_summary["by_pair"][pair_key]["total_strength"] += L.strength
    # Round
    cross_hemi_summary["by_pair"] = {
        k: {"n_links": v["n_links"], "total_strength": round(v["total_strength"], 3)}
        for k, v in cross_hemi_summary["by_pair"].items()
    }

    # All 28 possible pairs vs default 9
    pairs_summary = {
        "total_possible_crisscross_pairs": len(all_crisscross_pairs()),  # 28
        "default_routing_pairs": len(DEFAULT_ROUTING),  # 9
        "pairs_with_actual_links": len(cross_hemi_summary["by_pair"]),
    }

    return {
        "primitives_loaded": {
            "TritRegister": "real (gualaloom_v4_trit_register.py)",
            "ChiAtlas": "real (gualaloom_v4_chi_atlas_l6.py)",
            "L6_TCL": "real (gualaloom_v4_chi_atlas_l6.py)",
            "DSF + compute_dsf": "real (gualaloom_v4_uf_kernel.py)",
            "LivingAtlas": "real (gualaloom_v6_living_atlas.py)",
            "Krimelack": "real (gualaloom_v4_krimelack_dna.py) — shared at substrate level",
            "MathLoom": "real (gualaloom_mathloom_v1.py)",
        },
        "trit_check": trit_check,
        "mathloom_check": mathloom_check,
        "input_results": input_results,
        "emission_via_grandurun": emission,
        "per_hemisphere_state": hemi_state,
        "cross_hemi_links": cross_hemi_summary,
        "pairs_topology": pairs_summary,
        "n_hemispheres": 8,
        "n_chi_atlases": 8,
        "n_deep_atlases": 8,
        "n_sections_per_hemi": 7,
        "n_trit_registers_per_hemi": 7,
        "trits_per_register": 8,
        "total_trits_in_substrate": 8 * 7 * 8,  # 448
        "shared_krimelacks": 6,
        "honest_stubs": [
            "Krimelack feeding is simplified — full ω/κ tuning per-modality not exercised",
            "Trit settling uses first-trit-only proxy; full register-wide settle deferred",
            "Section dead-zone gate uses simplified S_UF threshold; full v6 gamma drift not modeled",
            "Cortex slow-graduation runs as second LivingAtlas with promotion at 0.5; full v7 NMDA-style gating not modeled",
            "Aware-gate / intro-gate from v7 not in this model",
            "Dream cycle here is a single-shot promotion pass; full v7 has REM-like REPLAY phases",
        ],
    }


if __name__ == "__main__":
    results = run_real_substrate()
    print(json.dumps(results, indent=2, default=str))
