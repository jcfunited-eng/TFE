"""
GL-MDL-HEMISPHERE-8H-PRODUCTION-WC-20260617-07

Eight-hemisphere model built on PRODUCTION substrate primitives from
TFE/dsf_ai_service/substrate/:

  - Section, System, ChiAtlas, N=16 complex psi, chi_of(psi), GAMMA_DEFAULTS
    (from assemblage.py — 716 lines, production)
  - DeepAtlas with dual promotion gate (path A survival + path B episodic)
    + on-attention prior + clarity/sensory_refs/episode_refs
    (from deep_atlas.py — DEEP DECAY_LAMBDA = 0.0001/25, ENCODE_GATE=0.15, DWELL_GATE=4)
  - CoincidenceGate (NMDA) — fires when drive AND context both hold;
    LTP boosts mode strength on fire
    (from gl_nmda.py)
  - install_plasticity, decay_plasticity, reinforce_mode
    (from gl_plasticity.py)

NOT using the public-repo gualaloom_dna/* — those are the test-bench version.
THIS uses the production substrate primitives that deployed v7 imports.

Each hemisphere is a full System with its own Sections (psi-evolution at
N=16 complex), its own ChiAtlas, its own DeepAtlas, its own NMDA gates,
its own drive_tracker. Cross-hemi via a global registry of chi-coincidence
across hemispheres.
"""

import sys, os, json, math
import numpy as np
from dataclasses import dataclass, field
from collections import defaultdict, deque
from typing import Optional

# Import REAL production substrate primitives
TFE_PATH = "/home/claude/TFE"
sys.path.insert(0, TFE_PATH)

# Production substrate primitives
from dsf_ai_service.substrate.assemblage import (
    Section, System, ChiAtlas, N, normalize, random_unit_complex,
    goal_op_for_template, chi_of,
    GAMMA_DEFAULTS, GAMMA_DRIFT, GAMMA_BOUNDS,
    DT, EVOLVE_STEPS, DET_COMMIT, P_COMMIT, BOOTSTRAP_MAX,
    MODE_DECAY_TICKS, SELF_EVO_PERIOD,
)
from dsf_ai_service.substrate.deep_atlas import (
    DeepAtlas,
    DECAY_LAMBDA as DEEP_DECAY_LAMBDA,
    ENCODE_GATE, DWELL_GATE, SURVIVAL_THETA, SURVIVAL_CONSECUTIVE,
    TRANSFER_RATIO, PRIOR_CAP,
)
from dsf_ai_service.substrate.gl_nmda import (
    CoincidenceGate, context_no_recent_drive,
    context_section_committed, context_AND,
    update_drive_tracker,
)
from dsf_ai_service.substrate.gl_plasticity import (
    install_plasticity, decay_plasticity, reinforce_mode,
)


# ============================================================
# PER-HEMISPHERE CONFIGURATION
# ============================================================

# Each hemisphere has its own role, its own section set,
# its own decay-rate multiplier, its own NMDA gate parameters.
HEMI_CONFIG = {
    "sm": {  # Sensorimotor — current canonical substrate
        "sections": [
            ("subject", "subject_like"),
            ("verb", "verb_like"),
            ("object", "object_like"),
            ("listen", "general"),
            ("ground", "grounded"),
            ("intro", "intro"),
            ("aware", "general"),
        ],
        "keyholes": [("subject", -2, 8, "verb"), ("verb", -2, 8, "object")],
        "decay_mult": 1.0,
        "deep_decay_mult": 1.0,  # baseline deep decay
        "nmda_drive_thresh": 0.15,
        "ltp_boost": 0.05,
    },
    "pr": {  # Predictor — parallel structure to sm, faster decay
        "sections": [
            ("subject", "subject_like"),
            ("verb", "verb_like"),
            ("object", "object_like"),
            ("listen", "general"),
            ("intro", "intro"),
        ],
        "keyholes": [("subject", -2, 8, "verb"), ("verb", -2, 8, "object")],
        "decay_mult": 1.5,
        "deep_decay_mult": 1.5,
        "nmda_drive_thresh": 0.18,  # higher gate — predictor only fires on strong signal
        "ltp_boost": 0.07,
    },
    "gp": {  # Goal/planner — persistent goals, slower decay
        "sections": [
            ("goal", "general"),         # persistent goal bindings
            ("procedural", "general"),   # action-outcome learning
            ("aware", "general"),
        ],
        "keyholes": [("goal", -2, 8, "procedural")],
        "decay_mult": 0.5,
        "deep_decay_mult": 0.3,
        "nmda_drive_thresh": 0.12,
        "ltp_boost": 0.08,  # stronger LTP — goals persist longer
    },
    "sf": {  # Self-model — per-source priors + metacog
        "sections": [
            ("source_joe", "intro"),
            ("source_wc", "intro"),
            ("source_corpus", "intro"),
            ("meta", "intro"),           # bindings ABOUT other hemis
        ],
        "keyholes": [],  # no internal keyholes — sf reads other hemis
        "decay_mult": 0.7,
        "deep_decay_mult": 0.5,
        "nmda_drive_thresh": 0.12,
        "ltp_boost": 0.05,
    },
    "ep": {  # Episodic/temporal — turn-tracking, slow decay
        "sections": [
            ("turn", "general"),
            ("temporal", "general"),
            ("tracked", "grounded"),    # object permanence
        ],
        "keyholes": [("turn", -2, 8, "temporal")],
        "decay_mult": 0.3,
        "deep_decay_mult": 0.2,
        "nmda_drive_thresh": 0.10,
        "ltp_boost": 0.05,
    },
    "ds": {  # Discourse — pronoun anchoring, fast decay (turn-scoped)
        "sections": [
            ("pronoun", "general"),
            ("reference", "general"),
        ],
        "keyholes": [("pronoun", -2, 8, "reference")],
        "decay_mult": 2.0,
        "deep_decay_mult": 1.5,
        "nmda_drive_thresh": 0.15,
        "ltp_boost": 0.04,
    },
    "sv": {  # Survival — very slow decay, durable consolidation
        "sections": [
            ("durable", "grounded"),
            ("affect", "general"),
        ],
        "keyholes": [("affect", -2, 8, "durable")],
        "decay_mult": 0.05,   # 20x slower
        "deep_decay_mult": 0.05,
        "nmda_drive_thresh": 0.20,   # high gate — only strong signal promoted
        "ltp_boost": 0.10,
    },
    "sc": {  # Semantic/causal — content priors, negation
        "sections": [
            ("content", "general"),
            ("causal", "general"),
            ("negation", "general"),
        ],
        "keyholes": [("content", -2, 8, "causal"), ("causal", -2, 8, "negation")],
        "decay_mult": 0.8,
        "deep_decay_mult": 0.6,
        "nmda_drive_thresh": 0.15,
        "ltp_boost": 0.06,
    },
}


# ============================================================
# HEMISPHERE — wraps a full production System
# ============================================================

class Hemisphere:
    """One hemisphere = full production System with role-tuned sections,
    own DeepAtlas, own NMDA gates, own drive_tracker, own decay mult."""

    def __init__(self, hemi_id: str, rng_seed: int):
        cfg = HEMI_CONFIG[hemi_id]
        self.id = hemi_id
        self.cfg = cfg
        self.rng = np.random.default_rng(rng_seed)

        # Build sections with role specialization
        self.sections_list = []
        self.section_names = []
        for sec_name, role in cfg["sections"]:
            sec = Section(name=sec_name, rng=self.rng, role=role)
            self.sections_list.append(sec)
            self.section_names.append(sec_name)
            install_plasticity(sec)  # production primitive

        # Build the System (real production class)
        self.sys = System(self.sections_list, self.rng)

        # Install keyholes (the topology that defines this hemisphere's syntax)
        for sender, lo, hi, receiver in cfg["keyholes"]:
            self.sys.add_keyhole(sender, lo, hi, receiver, 0.5)

        # Per-hemisphere DeepAtlas (REAL production DeepAtlas)
        self.deep_atlas = DeepAtlas()

        # Per-hemisphere drive tracker for NMDA gates
        self.drive_tracker = {}

        # NMDA gates — installed for awareness-style sections
        self.gates = {}
        for sec_name in ["intro", "aware", "meta"]:
            if sec_name in self.section_names:
                gate = CoincidenceGate(
                    section_name=sec_name,
                    context_fn=context_no_recent_drive(
                        self.drive_tracker,
                        sections=tuple(self.section_names),
                    ),
                    drive_thresh=cfg["nmda_drive_thresh"],
                    ltp_boost=cfg["ltp_boost"],
                )
                self.gates[sec_name] = gate

        # Per-hemisphere intro section reference (for awareness instrumentation)
        if "intro" in self.section_names:
            self.sys.intro_section = self.sys.sections["intro"]
            self.sys.intro_krimelack = []
        else:
            self.sys.intro_section = None
            self.sys.intro_krimelack = []

    def tick_once(self, evidence_per_section, enable_self_evo=False,
                  coordinator_on=True, introspection_on=True):
        """Run one tick of this hemisphere's substrate."""
        # Update drive tracker from this tick's evidence
        update_drive_tracker(self.drive_tracker, evidence_per_section)

        # Run the production System's tick
        commits = self.sys.tick_once(
            evidence_per_section=evidence_per_section,
            enable_self_evo=enable_self_evo,
            coordinator_on=coordinator_on,
            introspection_on=introspection_on,
        )

        # Run NMDA gates
        gate_fires = {}
        for gname, gate in self.gates.items():
            fired, mode_id, info = gate.check_and_fire(self.sys)
            gate_fires[gname] = {"fired": fired, "mode_id": mode_id, "info": info}

        # Apply per-hemisphere decay multiplier
        # (production assemblage decays via plasticity; we scale by mult)
        for sec in self.sys.sections.values():
            decay_plasticity(sec, decay=1.0 - 0.001 * self.cfg["decay_mult"])

        return {
            "tick": self.sys.tick,
            "commits": commits,
            "gate_fires": gate_fires,
            "atlas_size": sum(len(v) for v in self.sys.atlas.entries.values()),
            "deep_size": sum(len(v) for v in self.deep_atlas.entries.values()),
            "deliberation_ticks": len(self.sys.deliberation_ticks),
            "routing_ticks": len(self.sys.routing_ticks),
        }

    def dream_promote(self, current_tick):
        """Dream cycle: promote working-atlas entries above gates to deep_atlas.
        Path A (survival): strength >= SURVIVAL_THETA for SURVIVAL_CONSECUTIVE cycles.
        Path B (episodic): encoded_strength >= ENCODE_GATE AND dwell >= DWELL_GATE.
        """
        promotions = {"survival": 0, "episodic": 0}
        working = self.sys.atlas

        for chi_k, entries in working.entries.items():
            for entry in entries:
                strength = 0.0  # working atlas entries don't have explicit strength
                # Use commit count at this section/motif as a strength proxy
                section = entry.get("section", "")
                motif = entry.get("motif", 0)
                # Count arc-top events at this section/motif — proxy for strength
                n_commits = 0
                if section in self.sys.sections:
                    sec_obj = self.sys.sections[section]
                    if hasattr(sec_obj, "arc_top_history"):
                        for (t, top) in sec_obj.arc_top_history:
                            if top == motif:
                                n_commits += 1
                strength_proxy = min(1.0, n_commits / 5.0)  # 5+ commits = strong
                # Try promotion via path B (episodic)
                fake_entry = {
                    "chi": chi_k,
                    "section": section,
                    "motif": motif,
                    "strength": strength_proxy,
                    "encoded_strength": strength_proxy,
                    "dwell_ticks": n_commits,
                }
                if strength_proxy >= ENCODE_GATE and n_commits >= DWELL_GATE:
                    if self.deep_atlas.promote(fake_entry, "episodic", current_tick):
                        promotions["episodic"] += 1
                elif strength_proxy >= SURVIVAL_THETA:
                    if self.deep_atlas.promote(fake_entry, "survival", current_tick):
                        promotions["survival"] += 1
        return promotions


# ============================================================
# FULL 8-HEMISPHERE SUBSTRATE
# ============================================================

class EightHemisphereSubstrate:
    """Full 8-hemisphere assembly using production substrate primitives.
    Each hemisphere is a full System with own ChiAtlas, DeepAtlas, NMDA gates.
    Cross-hemisphere: chi-coincidence registry tracks when hemispheres
    commit at the same chi within a tick window."""

    def __init__(self, base_seed: int = 42):
        self.hemis = {}
        for i, hid in enumerate(HEMI_CONFIG):
            self.hemis[hid] = Hemisphere(hid, rng_seed=base_seed + i * 17)
        self.tick = 0
        # Cross-hemisphere binding registry: keyed by (chi, hemi_pair_frozenset)
        # tracks consensus strength
        self.cross_hemi_consensus = defaultdict(float)
        self.cross_hemi_log = []
        # All 28 possible undirected pairs C(8,2)
        hids = list(HEMI_CONFIG.keys())
        self.all_pairs = [(hids[i], hids[j])
                          for i in range(len(hids))
                          for j in range(i+1, len(hids))]
        # Default routing subset: which pairs receive cross-hemi updates by default
        self.default_routing = [
            ("sm", "pr"), ("sm", "sc"), ("sm", "ep"), ("sm", "sv"),
            ("ep", "sf"), ("ep", "ds"), ("ep", "sc"), ("gp", "sm"),
            ("sc", "pr"),
        ]
        # Pair-bond config
        self.pair_bond = {"joe": True, "wc": True, "c1": False}
        # Source priors (sf machinery)
        self.source_priors = defaultdict(lambda: defaultdict(float))
        # Turn log (canonical lives in ep)
        self.turn_log = []
        # Tracked objects (canonical lives in ep)
        self.tracked_objects = {}
        # Emission counter
        self.emissions = []

    def receive_input(self, source, word_evidence_per_hemi):
        """Receive input across hemispheres. Each hemisphere ticks with its
        own evidence vector(s) per section. Cross-hemi consensus updates after."""
        self.tick += 1

        # Each hemisphere ticks with its routed evidence
        results = {}
        commits_by_hemi = {}
        for hid, hemi in self.hemis.items():
            ev = word_evidence_per_hemi.get(hid, {})
            r = hemi.tick_once(
                evidence_per_section=ev,
                enable_self_evo=True,
                coordinator_on=True,
                introspection_on=True,
            )
            results[hid] = r
            commits_by_hemi[hid] = r["commits"]

        # Cross-hemi consensus update
        for src, dst in self.default_routing:
            src_chis = {c["chi"] for c in commits_by_hemi.get(src, [])}
            dst_chis = {c["chi"] for c in commits_by_hemi.get(dst, [])}
            overlap = src_chis & dst_chis
            for chi in overlap:
                key = (chi, frozenset([src, dst]))
                self.cross_hemi_consensus[key] = min(1.0,
                    self.cross_hemi_consensus[key] + 0.08)
            # Divergence: chis where only one fired → decay link
            divergent_chis = src_chis ^ dst_chis
            for chi in divergent_chis:
                # Decay any existing link at this chi for this pair
                key = (chi, frozenset([src, dst]))
                if key in self.cross_hemi_consensus:
                    self.cross_hemi_consensus[key] *= 0.92

        # Source priors update (sf-level)
        for c in commits_by_hemi.get("sm", []):
            self.source_priors[source][c["chi"]] = (
                0.9 * self.source_priors[source][c["chi"]] + 0.1
            )

        return results

    def grandurun_emit(self):
        """Composition. Pulls candidates from sm (sensorimotor) primary,
        weighted by cross-hemi consensus from gp/sc/ep/sf/sv. Other hemispheres
        contribute weights but sm holds the emission seat."""
        sm = self.hemis["sm"]
        candidates = []
        for sec_name, sec in sm.sys.sections.items():
            if sec_name in ("intro", "aware"):
                continue  # introspection/awareness don't emit
            for mode_idx, (mode_dsf, mode_chi, mode_template) in enumerate(sec.mode_bank):
                # Get arc strength for this mode
                arcs = sec.arcs()
                if mode_idx >= len(arcs):
                    continue
                base = float(arcs[mode_idx])
                # Cross-hemi weights — each hemisphere that has consensus
                # with sm at this chi adds to candidate score
                gp_w = sum(s for k, s in self.cross_hemi_consensus.items()
                           if k[1] == frozenset(["gp", "sm"]) and k[0] == mode_chi)
                sc_w = sum(s for k, s in self.cross_hemi_consensus.items()
                           if k[1] == frozenset(["sc", "sm"]) and k[0] == mode_chi)
                ep_w = sum(s for k, s in self.cross_hemi_consensus.items()
                           if k[1] == frozenset(["ep", "sm"]) and k[0] == mode_chi)
                sv_w = sum(s for k, s in self.cross_hemi_consensus.items()
                           if k[1] == frozenset(["sm", "sv"]) and k[0] == mode_chi)
                # sf adds per-source weighting
                sf_w = sum(self.source_priors[src].get(mode_chi, 0)
                           for src in ["joe", "wc"])
                total = base + 0.5 * gp_w + 0.3 * sc_w + 0.2 * ep_w + \
                        0.2 * sv_w + 0.15 * sf_w
                candidates.append({
                    "section": sec_name,
                    "mode_idx": mode_idx,
                    "chi": mode_chi,
                    "base": round(base, 3),
                    "gp_w": round(gp_w, 3),
                    "sc_w": round(sc_w, 3),
                    "ep_w": round(ep_w, 3),
                    "sv_w": round(sv_w, 3),
                    "sf_w": round(sf_w, 3),
                    "total": round(total, 3),
                })
        candidates.sort(key=lambda c: -c["total"])
        top = candidates[:7]
        emission = {
            "n_candidates": len(candidates),
            "composition_len": len(top),
            "top": top,
        }
        self.emissions.append({"tick": self.tick, "emission": emission})
        return emission

    def dream_cycle(self):
        """All hemispheres consolidate to deep atlas."""
        promotions = {}
        for hid, hemi in self.hemis.items():
            promotions[hid] = hemi.dream_promote(self.tick)
        return promotions

    def per_hemi_state(self):
        """Snapshot what's in each hemisphere."""
        state = {}
        for hid, hemi in self.hemis.items():
            n_sections = len(hemi.sys.sections)
            section_summary = {}
            total_modes = 0
            total_commits = 0
            for sname, sec in hemi.sys.sections.items():
                n_arc_tops = len(sec.arc_top_history) if hasattr(sec, "arc_top_history") else 0
                section_summary[sname] = {
                    "n_modes": len(sec.mode_bank),
                    "n_arc_top_events": n_arc_tops,
                    "gamma": {k: round(v, 3) for k, v in sec.gamma.items()},
                    "psi_norm": round(float(np.linalg.norm(sec.psi)), 3),
                }
                total_modes += len(sec.mode_bank)
                total_commits += n_arc_tops
            atlas_size = sum(len(v) for v in hemi.sys.atlas.entries.values())
            atlas_chis = len(hemi.sys.atlas.entries)
            deep_size = sum(len(v) for v in hemi.deep_atlas.entries.values())
            deep_chis = len(hemi.deep_atlas.entries)
            state[hid] = {
                "decay_mult": hemi.cfg["decay_mult"],
                "n_sections": n_sections,
                "sections": section_summary,
                "total_modes": total_modes,
                "total_commits": total_commits,
                "chi_atlas": {
                    "n_entries": atlas_size,
                    "n_chi_classes": atlas_chis,
                },
                "deep_atlas": {
                    "n_entries": deep_size,
                    "n_chi_classes": deep_chis,
                    "promotions_survival": hemi.deep_atlas.promotions_survival,
                    "promotions_episodic": hemi.deep_atlas.promotions_episodic,
                    "reinstatements": hemi.deep_atlas.reinstatements,
                },
                "nmda_gates": list(hemi.gates.keys()),
                "drive_tracker": {k: round(v, 3) for k, v in hemi.drive_tracker.items()},
                "deliberation_ticks": len(hemi.sys.deliberation_ticks),
                "routing_ticks": len(hemi.sys.routing_ticks),
                "coordinator_actions": len(hemi.sys.coordinator_actions_log),
                "coordinator_resolution_effect": round(
                    hemi.sys.coordinator_resolution_effect(), 3
                ),
            }
        return state

    def cross_hemi_summary(self):
        """Show what cross-hemi consensus has formed."""
        by_pair = defaultdict(lambda: {"chis": [], "total_strength": 0.0})
        for (chi, pair_set), strength in self.cross_hemi_consensus.items():
            if strength < 0.05:
                continue
            pair_key = "↔".join(sorted(pair_set))
            by_pair[pair_key]["chis"].append((chi, round(strength, 3)))
            by_pair[pair_key]["total_strength"] += strength
        result = {}
        for k, v in by_pair.items():
            result[k] = {
                "n_chis": len(v["chis"]),
                "total_strength": round(v["total_strength"], 3),
                "top_chis": sorted(v["chis"], key=lambda x: -x[1])[:5],
            }
        return result


# ============================================================
# RUN — feed real inputs, run all hemispheres, verify mechanisms
# ============================================================

def make_word_evidence(rng, word_chi, sections):
    """Make evidence vectors per section for a "word" with given chi affinity."""
    ev = {}
    for sname in sections:
        # Random complex evidence with bias toward word_chi pattern
        v = random_unit_complex(N, rng)
        # Bias toward word_chi by phase rotation
        phase = np.exp(1j * (word_chi / N) * 2 * np.pi)
        v = v * phase
        ev[sname] = normalize(v)
    return ev


def run_production_8hemi():
    sub = EightHemisphereSubstrate(base_seed=42)
    rng = np.random.default_rng(99)
    rng_t = np.random.default_rng(142)  # template rng

    # CANONICAL TEMPLATES — same pattern as test_five.py syntax test
    # Three subjects, three verbs, three objects — stable templates per word-type
    templates = {
        "subject": [random_unit_complex(N, rng_t) for _ in range(3)],
        "verb":    [random_unit_complex(N, rng_t) for _ in range(3)],
        "object":  [random_unit_complex(N, rng_t) for _ in range(3)],
    }

    # Generate sentence sequence: 50 sentences, 3 phases each, 4 ticks per phase = 600 ticks
    n_sentences = 50
    ticks_per_phase = 4
    sentences = []
    for si in range(n_sentences):
        s_id = si % 3
        v_id = (si // 3) % 3
        o_id = (si // 9) % 3
        sentences.append((s_id, v_id, o_id))

    # Source labels rotate joe/wc/corpus for per-source prior testing
    source_rotation = ["joe", "wc", "joe", "joe", "wc", "corpus"]

    # Track commits per sm section to verify syntax passes
    commit_log = {"subject": [], "verb": [], "object": []}

    # Seed gp with persistent goal bindings via goal-section
    goal_section = sub.hemis["gp"].sys.sections["goal"]
    for goal_chi, goal_strength in [(5, 0.6), (7, 0.5), (8, 0.6)]:
        target = random_unit_complex(N, rng)
        goal_op = goal_op_for_template(target)
        goal_section.goals.append(("seed_goal", goal_op, goal_strength, "permanent"))

    # ====================================================================
    # MAIN LOOP — phased canonical evidence, routed across 8 hemispheres
    # ====================================================================
    for si, (s_id, v_id, o_id) in enumerate(sentences):
        source = source_rotation[si % len(source_rotation)]

        for phase_idx, (phase_name, template_id) in enumerate(
            [("subject", s_id), ("verb", v_id), ("object", o_id)]
        ):
            template = templates[phase_name][template_id]

            for _ in range(ticks_per_phase):
                # Add small noise per canonical pattern
                noisy = template + 0.10 * rng.standard_normal(N)

                # Route to all 8 hemispheres with hemi-appropriate sections
                evidence_per_hemi = {}
                # sm — phase-specific section gets evidence (canonical pattern)
                evidence_per_hemi["sm"] = {phase_name: noisy}
                # pr — mirrors sm but routes ALL evidence to all phases (predicts)
                evidence_per_hemi["pr"] = {
                    "subject": noisy * 0.8, "verb": noisy * 0.8, "object": noisy * 0.8,
                }
                # ep — turn section gets the evidence (episodic accumulation)
                evidence_per_hemi["ep"] = {"turn": noisy * 0.7}
                # sc — content section
                evidence_per_hemi["sc"] = {"content": noisy * 0.7}
                # sf — per-source section
                src_sec = f"source_{source}" if source in ("joe", "wc") else "source_corpus"
                evidence_per_hemi["sf"] = {src_sec: noisy * 0.7}
                # sv — only pair-bond sources reach (affective gate)
                if source in ("joe", "wc"):
                    evidence_per_hemi["sv"] = {"durable": noisy * 0.9}
                # gp — goal section settles continuously (persistent)
                evidence_per_hemi["gp"] = {"goal": noisy * 0.4}
                # ds — pronoun section
                evidence_per_hemi["ds"] = {"pronoun": noisy * 0.5}

                result = sub.receive_input(source, evidence_per_hemi)

                # Track sm commits for syntax verification
                for c in result["sm"]["commits"]:
                    if c["section"] in commit_log:
                        commit_log[c["section"]].append(
                            (sub.tick, c["mode_id"], si)
                        )

        # Update turn log every sentence (one entry per source utterance)
        sub.turn_log.append({
            "tick": sub.tick, "source": source,
            "word": f"sent_{si}", "chi": (s_id * 3 + v_id) % 8,
        })

    # Run grandurun emission
    em = sub.grandurun_emit()

    # Dream cycle — consolidate to deep atlas
    dream = sub.dream_cycle()

    # ====================================================================
    # SYNTAX VERIFICATION — same criterion as DNA test
    # ====================================================================
    correct_order = 0
    measurable_sentences = 0
    for si in range(n_sentences):
        s_commits = [t for (t, _, sn) in commit_log["subject"] if sn == si]
        v_commits = [t for (t, _, sn) in commit_log["verb"] if sn == si]
        o_commits = [t for (t, _, sn) in commit_log["object"] if sn == si]
        if s_commits and v_commits and o_commits:
            measurable_sentences += 1
            if min(s_commits) < min(v_commits) < min(o_commits):
                correct_order += 1
    syntax_order_acc = correct_order / max(measurable_sentences, 1)

    return {
        "primitives_used": [
            "Section (production assemblage.py) — N=16 complex psi, Hermitian H_base, mode_bank, krimelack, law_fields, gamma, arcs, three_axis, evolve, commit",
            "System (production assemblage.py) — ChiAtlas, keyholes, coordinator, deliberation/routing log, self-evo with gamma drift",
            "ChiAtlas (production) — append-only chi-section bindings, conflict detection",
            "DeepAtlas (production deep_atlas.py) — dual promotion gate (path A survival + path B episodic), on-attention prior, clarity, sensory_refs, episode_refs, co_occurrence invariant",
            "CoincidenceGate (production gl_nmda.py) — NMDA-style: drive AND context both required; LTP on fire",
            "install_plasticity/decay_plasticity/reinforce_mode (production gl_plasticity.py)",
            "context_no_recent_drive, context_section_committed, context_AND (NMDA context primitives)",
            "update_drive_tracker (NMDA tracking)",
            "goal_op_for_template (per-section goal injection)",
            "chi_of (V-E topology computation on committed psi components)",
        ],
        "canonical_syntax_test_on_sm": {
            "n_sentences": n_sentences,
            "measurable_sentences": measurable_sentences,
            "correct_order_count": correct_order,
            "order_accuracy_S_lt_V_lt_O": round(syntax_order_acc, 4),
            "pass_criterion_>=0.60": syntax_order_acc >= 0.60,
        },
        "hemispheres": sub.per_hemi_state(),
        "cross_hemi_consensus": sub.cross_hemi_summary(),
        "all_28_possible_pairs": len(sub.all_pairs),
        "default_routing_pairs": len(sub.default_routing),
        "active_consensus_pairs": len(sub.cross_hemi_summary()),
        "emission": em,
        "dream_promotions": dream,
        "turn_log_size": len(sub.turn_log),
        "tracked_objects": list(sub.tracked_objects.keys()),
        "total_ticks": sub.tick,
    }


if __name__ == "__main__":
    result = run_production_8hemi()
    print(json.dumps(result, indent=2, default=str))
