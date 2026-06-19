"""
Cognitive Assemblage - DNA build.
Fixes from prior run + primitives for syntax, conversation, introspection,
self-improvement, awareness.

Fixes:
- Novel-mode spawn (single-mode collapse fix)
- Resolution-effect metric for coordinator (rubber-stamping fix)

New primitives:
- Section role specialization (subject/verb/object-like configurations)
- Conversation interface (external speaker)
- Awareness signal (deliberation vs routing)
- Multi-scale coherence monitor
"""

import os
import numpy as np
from dataclasses import dataclass, field
from collections import defaultdict, deque
from typing import Optional

# ---------- constants ----------
N = 16
DT = 0.1
EVOLVE_STEPS = 6
DET_COMMIT = 0.40
P_COMMIT = 0.40
BOOTSTRAP_MAX = 8
MODE_DECAY_TICKS = 80
SELF_EVO_PERIOD = 40
GAMMA_DEFAULTS = {"symmetry": 0.5, "consistency": 0.5, "compactness": 0.3}
GAMMA_BOUNDS = (0.05, 1.5)

# ---------- helpers ----------
def random_hermitian(n, rng, scale=1.0):
    A = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
    H = (A + A.conj().T) / 2
    e = np.linalg.eigvalsh(H)
    s = max(abs(e).max(), 1e-9)
    return scale * H / s

def normalize(v):
    nrm = np.linalg.norm(v)
    return v if nrm < 1e-12 else v / nrm

def random_unit_complex(n, rng):
    v = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    return normalize(v)

def chi_of(psi):
    amps = np.abs(psi)
    thresh = (1 / np.sqrt(len(psi))) * 0.85
    committed = amps > thresh
    V = int(committed.sum())
    E = 0
    for i in range(len(psi) - 1):
        if committed[i] and committed[i + 1]:
            E += 1
    if committed[0] and committed[-1]:
        E += 1
    return V - E

def goal_op_for_template(target):
    target = normalize(target)
    return -np.outer(target, target.conj())


# ---------- Lateral inhibition (GL-CMD-LATERAL-INHIBITION-EVE-20260618-04) ----------
def lateral_inhibition_operator(arcs, mode_bank, lambda_inhib=1.0,
                                projector_cache=None):
    """Hartline-style lateral inhibition as a Hamiltonian term.

    H_lateral = Σ_{i ≠ leader} λ·(arc_leader − arc_i)·|m_i⟩⟨m_i|

    Positive coefficient on |m_i⟩⟨m_i| → energy penalty for psi aligned
    with non-leading modes → symmetry breaks via positive feedback.

    GL-CMD-PROJECTOR-CACHE: if projector_cache (list of N×N matrices) is
    provided and correctly sized, uses pre-computed |m_i⟩⟨m_i| instead
    of recomputing np.outer per call.
    """
    if len(arcs) < 2:
        return np.zeros((N, N), dtype=complex)
    leader_idx = int(np.argmax(arcs))
    leader_arc = float(arcs[leader_idx])
    H_lat = np.zeros((N, N), dtype=complex)
    use_cache = (projector_cache is not None
                 and len(projector_cache) == len(mode_bank))
    for i, m_i in enumerate(mode_bank):
        if i == leader_idx:
            continue
        gap = leader_arc - float(arcs[i])
        if gap <= 0:
            continue
        P_i = projector_cache[i] if use_cache else np.outer(m_i, np.conj(m_i))
        H_lat = H_lat + (lambda_inhib * gap) * P_i
    return H_lat


# ---------- Structured emission noise (GL-CMD-STRUCTURED-NOISE-EVE-20260618-13) ----------
import math as _math

def structured_emission_noise(section, tick, needs_novelty,
                              candidate_mode_ids, epsilon=0.05,
                              omega=2 * _math.pi / 100):
    """Biological structured noise — small, slow, novelty-modulated,
    candidate-subspace-aligned.

    Replaces strict-zero H_base on emission sections with a tiny
    oscillation in the candidate subspace. High novelty → more
    exploration; low novelty → more consistent.
    """
    if not candidate_mode_ids or not section.mode_bank:
        return np.zeros((N, N), dtype=complex)
    f_novelty = 0.5 + 1.0 * needs_novelty
    phase = _math.cos(omega * tick)
    magnitude = epsilon * f_novelty * phase
    if abs(magnitude) < 1e-6:
        return np.zeros((N, N), dtype=complex)
    # Structured basis: sum of candidate projectors (candidate subspace)
    basis = np.zeros((N, N), dtype=complex)
    for mid in candidate_mode_ids:
        if mid < len(section.mode_bank):
            m = section.mode_bank[mid]
            if (len(section._projector_cache) == len(section.mode_bank)
                    and isinstance(section._projector_cache, list)):
                basis += section._projector_cache[mid]
            else:
                basis += np.outer(m, np.conj(m))
    nrm = np.linalg.norm(basis)
    if nrm > 1e-9:
        basis = basis / nrm * N  # normalize for stable magnitude
    return magnitude * basis


# ---------- Hemisphere types (GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21) ----------

@dataclass
class CrossHemiLink:
    """Multi-dimensional binding between atlas entries in different hemispheres.
    Carries the same metadata grandurun candidates carry (per the GRANDURUN-
    METADATA-PIPELINE pattern), plus consensus_phase for tracking convergent/
    divergent settling history.

    Phase 0: type definition only. No code creates or updates instances.
    GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21.
    """
    src_chi: int
    src_hemi: str
    dst_chi: int
    dst_hemi: str
    strength: float
    source: str = "corpus"
    arousal: float = 0.5
    valence: float = 0.0
    surprise: float = 0.0
    polarity: float = 1.0
    consensus_phase: float = 0.0
    last_tick: int = 0

    def to_dict(self):
        return {
            "src_chi": self.src_chi, "src_hemi": self.src_hemi,
            "dst_chi": self.dst_chi, "dst_hemi": self.dst_hemi,
            "strength": self.strength, "source": self.source,
            "arousal": self.arousal, "valence": self.valence,
            "surprise": self.surprise, "polarity": self.polarity,
            "consensus_phase": self.consensus_phase, "last_tick": self.last_tick,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


class HemisphereCoordinator:
    """Sub-coordinator scoped to a single hemisphere_id.

    Phase 0: instantiated only for hemisphere_id='em'. Wraps the existing
    global coordinator's behavior — no new logic. Future phases instantiate
    additional HemisphereCoordinators for each hemisphere added.

    GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21.
    """

    # Decay multipliers from spec — derived from cognitive timescale anchoring,
    # not tuned to produce target behavior. Baseline DECAY_LAMBDA=0.001/tick
    # gives half-life ≈700 ticks for em (one working-memory moment).
    DECAY_MULTIPLIERS = {
        "em": 1.0, "pr": 1.5, "ep": 0.1, "sc": 0.5,
        "gp": 0.05, "sf": 0.1, "sv": 0.001, "aff": 1.0,
    }

    def __init__(self, hemisphere_id, needs=None):
        self.hemisphere_id = hemisphere_id
        self.needs = needs  # Phase 0: em.needs = global needs by identity
        self.decay_multiplier = self.DECAY_MULTIPLIERS.get(hemisphere_id, 1.0)


# ---------- Section ----------
@dataclass
class Section:
    name: str
    rng: np.random.Generator
    role: str = "general"  # "general", "subject_like", "verb_like", "object_like", "intro", "grounded"
    H_base: np.ndarray = field(init=False)
    psi: np.ndarray = field(init=False)
    mode_bank: list = field(default_factory=list)
    mode_last_used: list = field(default_factory=list)
    mode_strength: list = field(default_factory=list)  # salience per mode
    krimelack: list = field(default_factory=list)
    law_fields: dict = field(default_factory=dict)
    gamma: dict = field(default_factory=dict)
    goals: list = field(default_factory=list)
    standing_goals: list = field(default_factory=list)  # external speaker only
    det_commit: float = DET_COMMIT
    p_commit: float = P_COMMIT
    bootstrap_used: int = 0
    map_inject: np.ndarray = field(default=None)
    # Handoff excitation: tick-relative commit threshold relaxation
    excitation_expires_at: int = 0
    excitation_strength: float = 0.0
    # Awareness instrumentation
    last_arc_top_id: int = -1
    arc_top_history: list = field(default_factory=list)

    out_of_range_streak: dict = field(default_factory=lambda: {"entropy": 0, "coherence": 0, "greed": 0})
    _projector_cache: list = field(default_factory=list)
    _cached_H_lateral: object = field(default=None, repr=False)
    # GL-CMD-STRUCTURED-NOISE: emission noise context
    _use_structured_noise: bool = False
    _noise_needs_novelty: float = 0.5
    _noise_candidate_ids: list = field(default_factory=list)

    def __post_init__(self):
        self.H_base = random_hermitian(N, self.rng, scale=0.6)
        self.psi = normalize(random_unit_complex(N, self.rng) * 0.3
                             + normalize(np.ones(N, dtype=complex)) * 0.7)
        self.law_fields = {
            "symmetry":    random_hermitian(N, self.rng, scale=0.5),
            "consistency": random_hermitian(N, self.rng, scale=0.5),
            "compactness": np.diag(np.linspace(-1, 1, N)).astype(complex) * 0.5,
        }
        self.gamma = dict(GAMMA_DEFAULTS)

    # B2 gamma_homeostasis REMOVED — GL-CMD-REMOVE-GAMMA-ANTI-ADAPTATION-EVE-20260619-25
    # B1 _initial_gamma + GAMMA_DRIFT REMOVED — same brief

    def effective_det_commit(self, current_tick):
        """Excitation pulse lowers commit threshold."""
        if current_tick < self.excitation_expires_at:
            return max(0.10, self.det_commit - self.excitation_strength)
        return self.det_commit

    def effective_p_commit(self, current_tick):
        if current_tick < self.excitation_expires_at:
            return max(0.20, self.p_commit - self.excitation_strength * 0.5)
        return self.p_commit

    def H_total(self):
        H = self.H_base.copy()
        for name, L in self.law_fields.items():
            H = H + self.gamma[name] * L
        for (gn, op, eta, source) in self.goals:
            H = H + eta * op
        for (gn, op, eta, source) in self.standing_goals:
            H = H + eta * op
        # GL-CMD-LATERAL-INHIBITION: mode-mode competition via energy penalty
        if os.environ.get("LATERAL_INHIBITION_ENABLED", "0") == "1":
            if len(self.mode_bank) >= 2:
                if self._cached_H_lateral is not None:
                    # GL-CMD-PROJECTOR-CACHE: reuse per-tick cached result
                    H = H + self._cached_H_lateral
                else:
                    # Rebuild projector list if out of sync
                    if len(self._projector_cache) != len(self.mode_bank):
                        self._projector_cache = [
                            np.outer(m, np.conj(m)) for m in self.mode_bank
                        ]
                    H_lat = lateral_inhibition_operator(
                        self.arcs(), self.mode_bank,
                        projector_cache=self._projector_cache)
                    H = H + H_lat
        # GL-CMD-STRUCTURED-NOISE: exploratory oscillation on emission sections
        if (self._use_structured_noise
                and os.environ.get("EMISSION_STRUCTURED_NOISE", "0") == "1"):
            H_noise = structured_emission_noise(
                self, getattr(self, '_noise_tick', 0),
                self._noise_needs_novelty, self._noise_candidate_ids)
            H = H + H_noise
        return H

    def step(self, J=None):
        H = self.H_total()
        I = np.eye(N, dtype=complex)
        A = I + 1j * H * DT / 2
        B = I - 1j * H * DT / 2
        try:
            self.psi = np.linalg.solve(A, B @ self.psi)
        except np.linalg.LinAlgError:
            pass
        if J is not None and np.linalg.norm(J) > 0:
            self.psi = self.psi + J * DT
        self.psi = normalize(self.psi)

    def evolve(self, J=None, steps=EVOLVE_STEPS):
        # GL-CMD-PROJECTOR-CACHE: compute H_lateral once per evolve call
        # (once per tick), reuse across all EVOLVE_STEPS sub-steps.
        if (os.environ.get("LATERAL_INHIBITION_ENABLED", "0") == "1"
                and len(self.mode_bank) >= 2):
            if len(self._projector_cache) != len(self.mode_bank):
                self._projector_cache = [
                    np.outer(m, np.conj(m)) for m in self.mode_bank
                ]
            self._cached_H_lateral = lateral_inhibition_operator(
                self.arcs(), self.mode_bank,
                projector_cache=self._projector_cache)
        for i in range(steps):
            self.step(J=J if i == 0 else None)  # evidence on first substep only
        self._cached_H_lateral = None  # clear after evolve

    def arcs(self):
        if not self.mode_bank:
            return np.array([])
        return np.array([np.abs(np.vdot(m, self.psi)) ** 2 for m in self.mode_bank])

    def entropy_det(self):
        a = self.arcs()
        if len(a) == 0 or a.sum() < 1e-12:
            return 0.0, 0.0
        p = a / a.sum()
        p_nz = p[p > 1e-12]
        H_k = -float(np.sum(p_nz * np.log(p_nz)))
        H_0 = np.log(len(self.mode_bank)) if len(self.mode_bank) > 1 else 1.0
        Det_k = 1.0 - H_k / max(H_0, 1e-9)
        return H_k, Det_k

    def commit_check(self, evidence_pressure=0.0, current_tick=0):
        a = self.arcs()
        if len(self.mode_bank) < 2 or a.sum() < 1e-9:
            if self.bootstrap_used < BOOTSTRAP_MAX and evidence_pressure > 0.20:
                return True, "bootstrap"
            return False, None
        # Sections need genuine evidence pressure to commit.
        # Excitation does NOT substitute for evidence - it only lowers thresholds.
        if evidence_pressure < 0.15:
            return False, None
        p = a / a.sum()
        p_max = float(p.max())
        H_k, Det_k = self.entropy_det()
        max_overlap = float(a.max())
        novel_thresh = 0.30 / (1.0 + 0.05 * max(0, len(self.mode_bank) - 5))
        # GL-CMD-LATERAL-INHIBITION: suppress novel_mode during emission settling
        if not getattr(self, '_suppress_novel_mode', False):
            if max_overlap < novel_thresh and evidence_pressure > 0.25:
                return True, "novel_mode"
        det_th = self.effective_det_commit(current_tick)
        p_th = self.effective_p_commit(current_tick)
        if Det_k >= det_th and p_max >= p_th:
            return True, "entropic_flip"
        return False, None

    def commit(self, tick, reason):
        state = self.psi.copy()
        c = chi_of(state)
        a = self.arcs()
        mode_id = -1
        if reason in ("bootstrap", "novel_mode"):
            new_mode = normalize(state.copy())
            self.mode_bank.append(new_mode)
            self.mode_last_used.append(tick)
            self.mode_strength.append(1.5)  # fresh modes start above baseline
            # GL-CMD-PROJECTOR-CACHE: invalidate (will rebuild on next H_total)
            self._projector_cache = []
            mode_id = len(self.mode_bank) - 1
            if reason == "bootstrap":
                self.bootstrap_used += 1
        else:
            p = a / a.sum() if a.sum() > 0 else a
            mode_id = int(p.argmax())
            # Option B: NO vector blending. mode_bank vectors stay immutable.
            # Reinforce salience instead (direction and salience are separate).
            while len(self.mode_strength) <= mode_id:
                self.mode_strength.append(1.0)
            self.mode_strength[mode_id] = min(2.5,
                self.mode_strength[mode_id] + 0.02)
            self.mode_last_used[mode_id] = tick
        # Salience: arc magnitude + novelty bonus (spec Item 3.1)
        arc_mag = float(a[mode_id]) if mode_id >= 0 and mode_id < len(a) else 0.0
        recent_fires = [k for k in self.krimelack[-50:] if k.get("mode_id") == mode_id]
        novelty_bonus = 0.3 if len(recent_fires) == 0 else 0.0
        salience = min(1.0, arc_mag + novelty_bonus)
        self.krimelack.append({"state": state, "chi": c, "tick": tick,
                               "mode_id": mode_id, "reason": reason,
                               "salience": salience})
        # arc-top history for resolution-effect metric
        if len(a) > 0:
            top = int(a.argmax())
            self.arc_top_history.append((tick, top))
            self.last_arc_top_id = top
        return c, mode_id, state

    # B3 homeostasis_pull REMOVED — GL-CMD-REMOVE-HOMEOSTATIC-DECAY-EVE-20260618-20
    # B4 decay_modes REMOVED — GL-CMD-REMOVE-HOMEOSTATIC-DECAY-EVE-20260618-20
    # B7 snapshot_initial_modes REMOVED (orphan) — same brief

    def three_axis(self):
        a = self.arcs()
        if len(a) > 0 and a.sum() > 0:
            p = a / a.sum()
            p_nz = p[p > 1e-12]
            ent = float(-np.sum(p_nz * np.log(p_nz)))
            ent_norm = ent / max(np.log(len(a)), 1e-9) if len(a) > 1 else 0.0
            greed = float((a / a.sum()).max())
        else:
            ent_norm = 0.0
            greed = 0.0
        amps = np.abs(self.psi)
        coh = float(np.linalg.norm(amps - np.mean(amps)))
        coh_norm = min(1.0, coh / 1.0)
        return {"entropy": ent_norm, "coherence": coh_norm, "greed": greed}


# ---------- Atlas ----------
class ChiAtlas:
    def __init__(self):
        self.entries = defaultdict(list)
        self.merges = []
        self.deferrals = []
        self.requested_keyholes = []

    def add_claim(self, chi, section_name, mode_id, tick):
        # Check for existing claim from same (section, mode_id) — reinforce instead of duplicate
        for e in self.entries[chi]:
            if e["section"] == section_name and e["mode_id"] == mode_id:
                e["strength"] = min(2.0, e.get("strength", 1.0) + 0.1)
                e["tick"] = tick
                return
        self.entries[chi].append({"section": section_name, "mode_id": mode_id,
                                   "tick": tick, "strength": 1.0})

    def conflicts(self):
        out = []
        for chi, claims in self.entries.items():
            sections = {c["section"] for c in claims}
            if len(sections) > 1:
                out.append((chi, claims))
        return out

    def density(self):
        if not self.entries:
            return 0.0
        ds = []
        for chi, claims in self.entries.items():
            ds.append(len({c["section"] for c in claims}))
        return float(np.mean(ds))


# ---------- System ----------
class System:
    def __init__(self, sections, rng):
        self.sections = {s.name: s for s in sections}
        self.atlas = ChiAtlas()
        self.tick = 0
        self.keyholes = []
        self.pending_goals = defaultdict(list)
        self.coordinator_fires = []
        self.deferred_conflicts = {}
        self.rng = rng
        self.system_log = defaultdict(list)
        self.section_self_evo_log = defaultdict(list)
        self.intro_krimelack = []
        self.intro_section = None
        # Awareness instrumentation
        self.deliberation_ticks = []
        self.routing_ticks = []
        self.coordinator_actions_log = []
        # External speaker (for conversation)
        self.external_speaker_buffer = deque(maxlen=20)
        self.grounding_section = None
        # Coherence-feedback (for conversation): track match rate between own utterances
        # and partner's recent utterances. Used to adapt heard-speaker goal strength.
        self.utterance_match_log = deque(maxlen=30)  # 1 = matched, 0 = didn't
        self.heard_speaker_strength = 0.70  # adaptive, stronger baseline
        # GL-SPC-HEMISPHERE-ARCH: hemisphere coordinators (Phase 0: em only)
        self.hemispheres = {}
        self.cross_hemi_links = []  # list of CrossHemiLink (empty at Phase 0)

    def add_keyhole(self, sender, chi_lo, chi_hi, receiver, goal_strength=0.4):
        self.keyholes.append({"sender": sender, "chi_lo": chi_lo, "chi_hi": chi_hi,
                              "receiver": receiver, "goal_strength": goal_strength})

    def project_into(self, section, evidence):
        if section.map_inject is None or evidence is None:
            return None
        J = section.map_inject @ evidence
        nrm = np.linalg.norm(J)
        if nrm > 0:
            J = J * min(1.0, 0.5 / nrm) * 0.5  # original 0.25 cap
        return J

    def hear_speaker(self, utterance_template_vector, target_section_name, speak_section_name=None):
        """External speaker says something.
        - Becomes a goal in target (listen) section
        - Also becomes a goal in speak section (so response is biased to same template)
        - Seeds a mode in listener's bank if no similar mode exists
        """
        target = normalize(utterance_template_vector)
        op = goal_op_for_template(target)
        sec = self.sections[target_section_name]
        sec.standing_goals.append((f"heard_t{self.tick}", op, self.heard_speaker_strength, "external"))
        self.external_speaker_buffer.append({"tick": self.tick, "vec": target.copy()})
        # Also bias the speak section toward responding on the same template - STRONG
        if speak_section_name and speak_section_name in self.sections:
            sp = self.sections[speak_section_name]
            sp.standing_goals.append((f"heard_t{self.tick}", op, 1.0, "external"))
        # Seed mode in listener if novel
        if sec.mode_bank:
            overlaps = [np.abs(np.vdot(m, target))**2 for m in sec.mode_bank]
            if max(overlaps) < 0.40:
                sec.mode_bank.append(target.copy())
                sec.mode_last_used.append(self.tick)
                sec.mode_strength.append(1.0)
                sec._projector_cache = []  # invalidate
        else:
            sec.mode_bank.append(target.copy())
            sec.mode_last_used.append(self.tick)
            sec.mode_strength.append(1.0)

    def record_utterance_match(self, matched: bool):
        """Track utterance match rate, adapt heard-speaker strength."""
        self.utterance_match_log.append(1 if matched else 0)
        if len(self.utterance_match_log) >= 8:
            recent_rate = sum(self.utterance_match_log) / len(self.utterance_match_log)
            # Wider range: 0.30 (high match, light touch) to 1.10 (low match, force alignment)
            target = 0.30 + (1.10 - 0.30) * (1.0 - recent_rate)
            self.heard_speaker_strength = 0.85 * self.heard_speaker_strength + 0.15 * target

    def expire_standing_goals(self, heard_lifetime=35, handoff_lifetime=5, coord_lifetime=3):
        for sec in self.sections.values():
            kept = []
            for g in sec.standing_goals:
                gn = g[0]
                if gn.startswith("heard_t"):
                    age = self.tick - int(gn.split("_t")[1])
                    if age < heard_lifetime:
                        kept.append(g)
                elif gn.startswith("coord_displace_t"):
                    age = self.tick - int(gn.split("_t")[1])
                    if age < coord_lifetime:
                        kept.append(g)
                elif gn.startswith("hf_") and "_t" in gn:
                    try:
                        t_str = gn.rsplit("_t", 1)[1]
                        age = self.tick - int(t_str)
                        if age < handoff_lifetime:
                            kept.append(g)
                    except (ValueError, IndexError):
                        kept.append(g)
                else:
                    kept.append(g)
            sec.standing_goals = kept

    def tick_once(self, evidence_per_section, enable_self_evo=False,
                  coordinator_on=False, introspection_on=False, allow_rewiring=False):
        self.tick += 1
        # Snapshot arc-tops before evolution this tick (current arcs, not last committed)
        prev_arc_tops = {}
        for nm, sec in self.sections.items():
            a = sec.arcs()
            prev_arc_tops[nm] = int(a.argmax()) if len(a) > 0 else -1

        commits_this_tick = []
        for name, sec in self.sections.items():
            ev = evidence_per_section.get(name, None)
            J = self.project_into(sec, ev) if ev is not None else None
            evidence_pressure = float(np.linalg.norm(J)) if J is not None else 0.0
            for g in self.pending_goals.get(name, []):
                sec.goals.append(g)
            _, det_before = sec.entropy_det()
            # Check commit BEFORE evolution — if psi is already aligned
            # with a mode (e.g. after priming), commit it before the
            # Hamiltonian rotates it away.
            do_commit, reason = sec.commit_check(evidence_pressure=evidence_pressure,
                                                  current_tick=self.tick)
            if not do_commit:
                # Only evolve if we didn't commit — evolution happens
                # between commits, not through them
                sec.evolve(J=J)
                # Re-check after evolution in case evidence pushed past threshold
                do_commit, reason = sec.commit_check(evidence_pressure=evidence_pressure,
                                                      current_tick=self.tick)
            committed_info = None
            if do_commit:
                chi, mode_id, state = sec.commit(self.tick, reason)
                self.atlas.add_claim(chi, name, mode_id, self.tick)
                committed_info = {"section": name, "chi": chi, "mode_id": mode_id,
                                   "reason": reason,
                                   "det_before": det_before,
                                   "det_after": sec.entropy_det()[1]}
                commits_this_tick.append(committed_info)
            sec.goals = [g for g in sec.goals if g[3] == "permanent"]
        self.pending_goals.clear()

        # Keyhole handoffs - EXCITATION PULSES (not content goals)
        # Sender's commit fires a temporary commit-threshold relaxation in receiver.
        # Receiver decides WHAT to commit based on its OWN evidence + state.
        # This is the corrected handoff mechanism.
        for c in commits_this_tick:
            sender = c["section"]
            chi = c["chi"]
            det_rose = c["det_after"] > c["det_before"] + 0.01
            if not det_rose and c["reason"] == "entropic_flip":
                self.system_log["weak_commits"].append((self.tick, sender, chi))
                continue
            if c["reason"] in ("bootstrap", "novel_mode"):
                continue
            for kh in self.keyholes:
                if kh["sender"] != sender:
                    continue
                if kh["chi_lo"] <= chi <= kh["chi_hi"]:
                    receiver = kh["receiver"]
                    rec_sec = self.sections[receiver]
                    # Set excitation in receiver
                    rec_sec.excitation_expires_at = self.tick + 8  # ~one phase
                    rec_sec.excitation_strength = kh["goal_strength"]

        # Coordinator
        coordinator_fired_this_tick = False
        if coordinator_on:
            conflicts = self.atlas.conflicts()
            unresolved = []
            for (chi, claims) in conflicts:
                key = (chi, frozenset(c["section"] for c in claims))
                if key in self.deferred_conflicts and self.deferred_conflicts[key] > self.tick:
                    continue
                unresolved.append((chi, claims))
            for (chi, claims) in unresolved:
                sec_names = {c["section"] for c in claims}
                self.coordinator_fires.append({"tick": self.tick, "chi": chi,
                                                "n_claims": len(claims),
                                                "sections": list(sec_names)})
                coordinator_fired_this_tick = True
                connected = any(kh["sender"] in sec_names and kh["receiver"] in sec_names
                                for kh in self.keyholes)
                if connected:
                    self.atlas.merges.append({"tick": self.tick, "chi": chi,
                                               "sections": list(sec_names)})
                    self.deferred_conflicts[(chi, frozenset(sec_names))] = self.tick + 30
                    # Strong displacement: inject orthogonal kick into conflicting sections' psi
                    for sn in sec_names:
                        if sn in self.sections:
                            sec_obj = self.sections[sn]
                            kick = random_unit_complex(N, self.rng) * 0.45
                            sec_obj.psi = normalize(sec_obj.psi + kick)
                            sec_obj.excitation_expires_at = max(sec_obj.excitation_expires_at,
                                                                  self.tick - 1)
                    self.coordinator_actions_log.append({"tick": self.tick, "action": "merge",
                                                          "sections": list(sec_names)})
                else:
                    if allow_rewiring:
                        sec_list = list(sec_names)
                        shared = 0
                        for c2, ent in self.atlas.entries.items():
                            secs2 = {e["section"] for e in ent}
                            if set(sec_list).issubset(secs2):
                                shared += 1
                        if shared >= 2:
                            self.atlas.requested_keyholes.append({"tick": self.tick,
                                                                   "sections": sec_list, "chi": chi})
                            a, b = sec_list[0], sec_list[1]
                            self.add_keyhole(a, chi - 1, chi + 1, b, 0.3)
                            self.add_keyhole(b, chi - 1, chi + 1, a, 0.3)
                            self.coordinator_actions_log.append({"tick": self.tick, "action": "rewire",
                                                                  "sections": list(sec_names)})
                    self.atlas.deferrals.append({"tick": self.tick, "chi": chi,
                                                  "sections": list(sec_names)})
                    self.deferred_conflicts[(chi, frozenset(sec_names))] = self.tick + 20

        # Awareness instrumentation: deliberation vs routing
        if coordinator_fired_this_tick:
            self.deliberation_ticks.append(self.tick)
        elif commits_this_tick:
            self.routing_ticks.append(self.tick)

        # Introspection
        if introspection_on and self.intro_section is not None:
            snap = self._atlas_snapshot()
            self.intro_section.evolve(J=snap)
            do_commit, reason = self.intro_section.commit_check(evidence_pressure=float(np.linalg.norm(snap)))
            if do_commit:
                chi, mode_id, state = self.intro_section.commit(self.tick, reason)
                self.intro_krimelack.append({"state": state, "chi": chi, "tick": self.tick,
                                              "mode_id": mode_id, "reason": reason,
                                              "atlas_snapshot": snap.copy()})

        if self.tick % 20 == 0:
            # (2) Keyhole strength decay
            for kh in self.keyholes:
                kh["goal_strength"] = kh["goal_strength"] * 0.999

            # (3) Atlas binding strength decay — salience-based, not age-based
            for chi_k in list(self.atlas.entries.keys()):
                for e in self.atlas.entries[chi_k]:
                    e["strength"] = e.get("strength", 1.0) * 0.999
                # Remove only claims with near-zero strength
                self.atlas.entries[chi_k] = [
                    e for e in self.atlas.entries[chi_k]
                    if e.get("strength", 0) > 0.01
                ]
                if not self.atlas.entries[chi_k]:
                    del self.atlas.entries[chi_k]

            # (4) Coordinator logs — cap to prevent unbounded growth
            if len(self.coordinator_fires) > 200:
                self.coordinator_fires = self.coordinator_fires[-100:]
            if len(self.coordinator_actions_log) > 200:
                self.coordinator_actions_log = self.coordinator_actions_log[-100:]
            if len(self.deliberation_ticks) > 200:
                self.deliberation_ticks = self.deliberation_ticks[-100:]
            if len(self.routing_ticks) > 200:
                self.routing_ticks = self.routing_ticks[-100:]
            # System log — cap each list
            for k in list(self.system_log.keys()):
                if len(self.system_log[k]) > 500:
                    self.system_log[k] = self.system_log[k][-200:]

        # Self-evolution with gamma drift-toward-default
        # Conservative: require persistent out-of-range and use moderate learning rate
        if enable_self_evo and self.tick % SELF_EVO_PERIOD == 0:
            for sec in self.sections.values():
                ax = sec.three_axis()
                sec.out_of_range_streak["entropy"] = sec.out_of_range_streak["entropy"] + 1 if ax["entropy"] < 0.3 else 0
                sec.out_of_range_streak["coherence"] = sec.out_of_range_streak["coherence"] + 1 if ax["coherence"] < 0.3 else 0
                sec.out_of_range_streak["greed"] = sec.out_of_range_streak["greed"] + 1 if ax["greed"] > 0.7 else 0
                eta = 0.04
                dgamma = {"symmetry": 0.0, "consistency": 0.0, "compactness": 0.0}
                if sec.out_of_range_streak["entropy"] >= 2:
                    dgamma["symmetry"] -= eta
                    dgamma["consistency"] -= eta
                if sec.out_of_range_streak["coherence"] >= 2:
                    dgamma["consistency"] += eta
                if sec.out_of_range_streak["greed"] >= 2:
                    dgamma["compactness"] += eta
                for k, dv in dgamma.items():
                    sec.gamma[k] = float(np.clip(sec.gamma[k] + dv, *GAMMA_BOUNDS))
                self.section_self_evo_log[sec.name].append({
                    "tick": self.tick, "three_axis": ax, "gamma": dict(sec.gamma)})

        # Resolution-effect: did arc-tops in conflict sections change after a coordinator action?
        # (Measured by looking at arc-tops BEFORE the action vs after.
        # Arc-top updates happen on commits. The displacement kick gives some psi rotation
        # which alters arcs immediately — record the pre-action arcs vs current arcs.)
        if coordinator_fired_this_tick and self.coordinator_actions_log:
            last_action = self.coordinator_actions_log[-1]
            if last_action["tick"] == self.tick:
                # Record arc-tops AFTER for sections involved
                # We compare against arc *snapshots* taken pre-action (prev_arc_tops captured at start of tick)
                arc_changes = 0
                for nm in last_action["sections"]:
                    if nm not in self.sections:
                        continue
                    sec_obj = self.sections[nm]
                    if len(sec_obj.mode_bank) == 0:
                        continue
                    current_arcs = sec_obj.arcs()
                    current_top = int(current_arcs.argmax()) if len(current_arcs) > 0 else -1
                    if current_top != prev_arc_tops.get(nm, -1):
                        arc_changes += 1
                last_action["arc_changes"] = arc_changes
                last_action["arc_targets"] = len(last_action["sections"])

        # Expire standing goals
        self.expire_standing_goals()

        # Log
        self.system_log["tick"].append(self.tick)
        self.system_log["n_commits"].append(len(commits_this_tick))
        self.system_log["atlas_size"].append(sum(len(v) for v in self.atlas.entries.values()))
        self.system_log["atlas_chi_classes"].append(len(self.atlas.entries))
        self.system_log["atlas_density"].append(self.atlas.density())
        self.system_log["n_conflicts"].append(len(self.atlas.conflicts()))
        self.system_log["coordinator_fired"].append(1 if coordinator_fired_this_tick else 0)
        all_ax = [s.three_axis() for s in self.sections.values()]
        for k in ("entropy", "coherence", "greed"):
            self.system_log[f"system_{k}"].append(float(np.mean([a[k] for a in all_ax])))

        # Binding-intensity salience bonus (spec Item 3.1)
        if len(commits_this_tick) >= 2:
            bonus = min(0.4, 0.1 * (len(commits_this_tick) - 1))
            for c in commits_this_tick:
                sec_name = c["section"]
                sec = self.sections[sec_name]
                if sec.krimelack:
                    last = sec.krimelack[-1]
                    last["salience"] = min(1.0, last.get("salience", 0.0) + bonus)

        return commits_this_tick

    def replay_tick(self, rng=None, max_replay=2):
        """Quiet-time replay: sample from each section's krimelack
        weighted by salience * recency, re-project as evidence.
        This is substrate-native DMN / mental time travel (spec Item 3.2)."""
        if rng is None:
            rng = np.random.default_rng()
        replayed = []
        for sec_name, section in self.sections.items():
            if len(section.krimelack) == 0:
                continue
            recency_lambda = 0.002
            weights = np.array([
                k.get("salience", 0.5) * np.exp(-recency_lambda * (self.tick - k["tick"]))
                for k in section.krimelack
            ])
            if weights.sum() <= 0:
                continue
            weights = weights / weights.sum()
            n_sample = min(max_replay, len(section.krimelack))
            indices = rng.choice(len(section.krimelack), size=n_sample,
                                 replace=False, p=weights)
            for idx in indices:
                entry = section.krimelack[idx]
                J = self.project_into(section, entry["state"])
                if J is not None:
                    section.evolve(J=J)
                replayed.append((sec_name, entry.get("chi", 0),
                                 entry.get("mode_id", -1), entry.get("tick", 0)))
        # Let evolution settle with the replayed evidence
        commits = self.tick_once({}, enable_self_evo=True,
                                  coordinator_on=True, introspection_on=True,
                                  allow_rewiring=True)
        return {"replayed": replayed, "commits": commits}

    def _atlas_snapshot(self):
        """Compress current atlas + section three-axis into a complex N-vector for introspection."""
        v = np.zeros(N, dtype=complex)
        # Atlas component: chi values weighted by section diversity
        section_to_idx = {nm: i % N for i, nm in enumerate(sorted(self.sections.keys()))}
        for chi, claims in self.atlas.entries.items():
            # Each claim contributes at index = (chi + section_idx) mod N
            for c in claims[-5:]:  # last 5 claims weighted most
                sec_idx = section_to_idx.get(c["section"], 0)
                idx = (chi + sec_idx) % N
                v[idx] += np.exp(1j * (chi / N) * 2 * np.pi)
        # Three-axis component: encode each section's current state
        for nm, sec in self.sections.items():
            ax = sec.three_axis()
            sec_idx = section_to_idx[nm]
            v[sec_idx] += ax["entropy"] * np.exp(1j * 0.5 * np.pi)
            v[(sec_idx + 1) % N] += ax["coherence"] * np.exp(1j * 1.0 * np.pi)
            v[(sec_idx + 2) % N] += ax["greed"] * np.exp(1j * 1.5 * np.pi)
        if np.linalg.norm(v) > 0:
            v = normalize(v)
        return v

    def coordinator_resolution_effect(self):
        """How often did coordinator actions actually change arc-tops?"""
        actions_with_change = [a for a in self.coordinator_actions_log if a.get("arc_changes", 0) > 0]
        if not self.coordinator_actions_log:
            return 0.0
        return len(actions_with_change) / len(self.coordinator_actions_log)
