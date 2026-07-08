"""
neuron.py — LoomNeuron: full 15-piece per-neuron stack (Stage 1, K=0).

GL-CMD-LOOM-NEURON-STAGE1-EVE-20260620-78
Reference spec: GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-74

Pieces assembled here:
  NEW (this file):
    1.  PsiLattice           — 16-dim complex ψ-lattice with imaginary-time settle
    2.  SpikeBuffer          — ring buffer depth 16 (tick, intensity, source_id)
    3.  CouplingsJij         — J_ij matrix, K=0 Stage 1, shape (0, 16)
    4.  FamiliarityFeedback  — Δ_eff = Δ_base + match_score
    5.  LawField + laws list — per-neuron constraint bundle
    6.  DNAExpressionSite    — Stage 1 stub (load/express round-trip)
    7.  LoomNeuron           — main class wiring all 15 pieces

  REUSED (imported from validated primitives):
    8.  TritRegister         — dsf_ai_service/v4/gualaloom_v4_trit_register.py
    9.  DSF + compute_dsf    — dsf_ai_service/v4/gualaloom_v4_uf_kernel.py
    10. L6_TCL + ChiAtlas    — dsf_ai_service/v4/gualaloom_v4_chi_atlas_l6.py
    11. bt_div + friends     — dsf_ai_service/v4/gualaloom_mathloom_v1.py
    12. LanguageKrimelack    — dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py
    13. SensoryBank          — dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py
    14. _grandurun_state     — dsf_ai_service/v4/gualaloom_v5_engine.py
    15. _SPIN_VECTOR_DIM     — dsf_ai_service/v4/gualaloom_v5_engine.py

NO writes to production atlas. NO engine side effects. NO ECS/S3/deploy.
"""

import math
import sys
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Reused primitives — import paths only, no reimplementation
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dsf_ai_service.v4.gualaloom_v4_trit_register import TritRegister
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF, compute_dsf
from dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6 import L6_TCL, ChiAtlas
from dsf_ai_service.v4.gualaloom_mathloom_v1 import (
    bt_div, bt_to_int, int_to_bt,
)
from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import (
    LanguageKrimelack, SensoryBank,
)
from dsf_ai_service.v4.gualaloom_v5_engine import (
    _grandurun_state, _SPIN_VECTOR_DIM, _SPIN_DIM_NAMES,
)

# ---------------------------------------------------------------------------
# Frozen rational constants (per spec)
# ---------------------------------------------------------------------------
PSI_DIM = 16          # ψ-lattice dimension (matches Spike Buffer depth)
DET_COMMIT = 0.40     # conviction threshold for commit detection
P_COMMIT = 0.40       # max-mode probability threshold for commit detection
J_BASE = 1.0          # base coupling scale
J_MAX = 1.5           # max coupling scale
DELTA_BASE = 0.10     # base dead-zone for FamiliarityFeedback
SETTLE_STEPS = 30     # imaginary-time evolution steps

# --- GL-CMD-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-EVE-20260707-v1 additions ---
# HEURISTIC: EMISSION_THRESHOLD not defined here (that's dispatch item 5,
# not built this dispatch -- see halt report). DEFAULT_DELAY_MS/
# MAX_CHI_DISTANCE below support _compute_propagation_delay_ms(), which is
# built but not wired to anything live.
DEFAULT_DELAY_MS = 1.0     # HEURISTIC: fallback when chi_position is unknown
                            # (always, in Phase 1 -- see chi_position note in
                            # __init__). Class: from-design (arbitrary
                            # placeholder, not measured).
MAX_CHI_DISTANCE = 262144   # matches tools/wave_constants.py N_CELLS -- the
                            # wave-atlas chi space, used ONLY as a
                            # normalization denominator for the delay
                            # heuristic below; LoomNeuron itself has no chi
                            # coordinate today (see chi_position note).

# --- GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v1 additions (STDP) ---
# All HEURISTIC per blueprint v2 SS3.4, values as specified in the dispatch
# (none tuned by c1). Class: from-biology-reference (standard STDP timing
# ranges). Measurement plan (shared across all seven, per dispatch): observe
# learning curves under repeated exposure (this dispatch's own protocol
# step 6); adjust if learning is too fast (overshoot, response saturates
# before 20 reps) or too slow (never converges, no latency drop by rep 20).
STDP_WINDOW_MS = 40.0             # presynaptic-fire history retention window
STDP_POTENTIATION_WINDOW_MS = 20.0  # pre-before-post window that strengthens
STDP_POTENTIATION_AMPLITUDE = 0.02
STDP_TAU_MS = 20.0                 # shared exponential falloff, both directions
STDP_DEPRESSION_WINDOW_MS = 20.0   # post-before-pre window that weakens
STDP_DEPRESSION_AMPLITUDE = 0.015
MAX_SYNAPSE_WEIGHT = 5.0
MIN_SYNAPSE_WEIGHT = 0.0
STDP_DEFAULT_SYNAPSE_WEIGHT = 0.05  # weight for a not-yet-potentiated synapse

# Reserved source_id prefix for non-synaptic (external) spike sources --
# direct word/cue injection from LoomBrain.step or recall's cue injection,
# as opposed to a real neuron-to-neuron spike. STDP only applies to real
# synapses: there's no connection to learn on for an external stimulus.
# Real neuron ids are always f"{cluster_id}_n{i}" (e.g. "H3_n17", see
# cluster.py/brain.py) -- none start with "_", so this is a safe,
# non-colliding convention, not a new ID scheme.
EXTERNAL_SOURCE_PREFIX = "_"

SETTLE_EPS = 0.25     # imaginary-time step size
INJECT_SIGMA = 1.0    # Gaussian width (modes) for MapInject localization
FOLD_TRIGGER_RATIO = math.exp(-1)  # 1/e — from L6-TCL physics (Master Spec Ch.11)
FOLD_SUSTAIN_TICKS = 3             # consecutive ticks at n_eff < threshold for fold
OMEGA_HISTORY_LEN = 32             # rolling window for recent_omega_mean
N_MODALITIES = 6                   # GL-CMD-131: modality count for attenuation


def signal_attenuation(ring_pos: int, ring_N: int, modality_index: int) -> float:
    """Per-(neuron, modality) signal attenuation in [0.3, 1.0].

    Deterministic from ring position. Each modality's pattern is rotated
    by 60° of ring position so each neuron has a unique 6-tuple.
    Floor at 0.3 prevents degenerate neurons.
    """
    A_MIN = 0.3
    A_RANGE = 1.0 - A_MIN
    return A_MIN + A_RANGE * (0.5 + 0.5 * math.cos(
        2.0 * math.pi * (ring_pos / ring_N + modality_index / N_MODALITIES)
    ))


def _snapshot_single_krim(krim):
    """GL-CMD-EVENT-COUNT-KRIMELACK-STATE-209: snapshot one krimelack's
    mutable oscillator state, same fields/adapter handling as brain.py's
    LoomBrain.recall() already uses for its own (read-side) snapshot --
    this is the write-side twin, used by _unwrapped_deltas to make a
    non-language modality's event_count delta a stable function of the
    fed signal alone, not of whatever an earlier, different concept's
    teaching left the krimelack sitting at."""
    target = getattr(krim, '_inner', krim)
    outer_mirror = None
    if target is not krim:
        outer_mirror = (
            krim,
            krim.events.copy() if hasattr(krim, 'events') else None,
            int(krim.winding) if hasattr(krim, 'winding') else None,
        )
    return (
        target,
        float(target.phase) if hasattr(target, 'phase') else None,
        float(target.t) if hasattr(target, 't') else None,
        int(target.winding) if hasattr(target, 'winding') else None,
        int(target.n_events) if hasattr(target, 'n_events') else None,
        target.events.copy() if hasattr(target, 'events') else None,
        outer_mirror,
    )


def _restore_single_krim(snap):
    """Inverse of _snapshot_single_krim."""
    target, phase, t, winding, n_events, events, outer_mirror = snap
    if phase is not None:
        target.phase = phase
    if t is not None:
        target.t = t
    if winding is not None:
        target.winding = winding
    if n_events is not None:
        target.n_events = n_events
    if events is not None:
        target.events = events
    if outer_mirror is not None:
        krim_outer, outer_events, outer_winding = outer_mirror
        if outer_events is not None:
            krim_outer.events = outer_events
        if outer_winding is not None:
            krim_outer.winding = outer_winding


# ---------------------------------------------------------------------------
# Piece 1: ψ-lattice — 16-dim complex with imaginary-time settle
# ---------------------------------------------------------------------------

class PsiLattice:
    """
    16-dim complex ψ-lattice.

    State: ψ ∈ ℂ¹⁶, normalized, ψ_n = √ρ_n · e^(iφ_n).
    Settle: imaginary-time evolution under H = H_laws + H_injection.
    Commit detection: max_i p_i ≥ P_COMMIT AND Det_k ≥ DET_COMMIT
      where Det_k = B_k (conviction) from the L0-L4 DSF.
    """

    DIM = PSI_DIM

    def __init__(self):
        # Uniform superposition initial state
        self.psi = np.ones(self.DIM, dtype=np.complex128) / math.sqrt(self.DIM)

    def probabilities(self) -> np.ndarray:
        """Return mode probabilities p_i = |ψ_i|²."""
        return np.abs(self.psi) ** 2

    def settle(self,
               injection_vector: np.ndarray,
               law_fields: List[Tuple[float, str]],
               n_steps: int = SETTLE_STEPS,
               eps: float = SETTLE_EPS) -> np.ndarray:
        """Evolve ψ under Hermitian Hamiltonian to energy minimum.

        H = H_laws + H_injection (rank-1 external field).

        Args:
            injection_vector: real (DIM,) localized excitation from MapInject
            law_fields:       [(weight, family), ...] — constraint terms
            n_steps:          imaginary-time steps
            eps:              step size

        Returns the settled ψ (same reference as self.psi).
        """
        psi = self.psi.copy()
        DIM = self.DIM

        # Build Hamiltonian H: DIM×DIM Hermitian
        H = np.zeros((DIM, DIM), dtype=np.complex128)

        # Law-field diagonal terms
        for weight, family in law_fields:
            if family == "symmetry.basic":
                # Symmetry: penalize deviation from uniform amplitude.
                # Diagonal correction: H[i,i] -= weight * p_i
                # (drives amplitude toward uniform = minimum symmetry energy)
                for i in range(DIM):
                    H[i, i] -= weight * (abs(psi[i]) ** 2)
            elif family == "consistency.basic":
                # Consistency: favor modes already active in prior state.
                # H[i,i] -= weight * p_i_prior (prior ψ = current psi before settle)
                for i in range(DIM):
                    H[i, i] -= weight * (abs(psi[i]) ** 2)

        # Injection term: H_inj = -inj_norm * |v><v| (rank-1, Hermitian)
        # This drives ψ toward the injection direction (ground state = v).
        inj_norm = float(np.linalg.norm(injection_vector))
        if inj_norm > 1e-9:
            v = injection_vector.astype(np.complex128) / inj_norm
            H -= inj_norm * np.outer(v, v.conj())

        # Imaginary-time evolution: ψ ← (I - ε·H)·ψ, renormalize each step
        for _ in range(n_steps):
            psi = psi - eps * (H @ psi)
            norm = float(np.linalg.norm(psi))
            if norm < 1e-12:
                # Reset to uniform if numerical collapse
                psi = np.ones(DIM, dtype=np.complex128) / math.sqrt(DIM)
            else:
                psi /= norm

        self.psi = psi
        return psi

    def committed(self, dsf: DSF) -> bool:
        """Commit detection: max_i p_i ≥ P_COMMIT AND B_k ≥ DET_COMMIT."""
        p_max = float(np.max(self.probabilities()))
        det_k = float(dsf.B_k)  # conviction from L0-L4 DSF
        return p_max >= P_COMMIT and det_k >= DET_COMMIT


# ---------------------------------------------------------------------------
# Piece 2: Event/Spike Buffer — ring buffer, depth 16
# ---------------------------------------------------------------------------

class SpikeBuffer:
    """FIFO ring buffer for spike events.

    Each entry: (tick, intensity, source_neuron_id_or_None).
    Depth = PSI_DIM = 16. Oldest entry evicted when full.
    """

    DEPTH = PSI_DIM

    def __init__(self):
        self._buf: List[Tuple[int, float, Optional[str]]] = []

    def append(self, tick: int, intensity: float,
               source_id: Optional[str] = None) -> None:
        """Append spike; evict oldest if at capacity."""
        if len(self._buf) >= self.DEPTH:
            self._buf.pop(0)
        self._buf.append((tick, intensity, source_id))

    def read(self) -> List[Tuple[int, float, Optional[str]]]:
        """Return copy of buffer (oldest first)."""
        return list(self._buf)

    def __len__(self) -> int:
        return len(self._buf)


# ---------------------------------------------------------------------------
# Piece 3: Couplings J_ij — per-neuron coupling matrix, K=0 Stage 1
# ---------------------------------------------------------------------------

class CouplingsJij:
    """J_ij coupling matrix for connections to neighbor neurons.

    Stage 1: K=0, no neighbors. Matrix shape (0, PSI_DIM).
    Stage 2: K=16 neighbors populated; J derived from L0-L4 DSF per
             Master Spec Ch.7 table (J = D_k·J_base, S_UF·J_base, etc.).

    J_base = 1.0, J_max = 1.5 (frozen rational constants).
    """

    def __init__(self, n_modes: int = PSI_DIM,
                 neighbors: Optional[List[str]] = None,
                 ring_distances: Optional[List[int]] = None):
        self.n_modes = n_modes
        self.neighbors: List[str] = neighbors if neighbors is not None else []
        self.ring_distances: List[int] = ring_distances or [1] * len(self.neighbors)
        K = len(self.neighbors)
        # Stage 1 (K=0): shape (0, n_modes). Stage 2 (K=16): shape (16, n_modes).
        # Initial values: J_BASE scaled by inverse ring distance (1/(d+1)).
        # GL-CMD-98: ring distance breaks initial symmetry — each neuron has
        # different J_ij values because its neighbors are at different positions.
        self.J = np.zeros((K, n_modes), dtype=np.float64)
        for i in range(K):
            d = self.ring_distances[i]
            self.J[i] = J_BASE / (d + 1)

    def update_from_dsf(self, dsf: DSF) -> None:
        """Update J_ij from L0-L4 DSF outputs.

        Per Master Spec Ch.7 table — 8 coupling values from DSF, repeated
        2× to fill PSI_DIM=16 modes. GL-CMD-98: each neighbor row is scaled
        by inverse ring distance 1/(d+1) — topology-derived, not a tuned
        constant.
        """
        if len(self.neighbors) == 0 or dsf is None:
            return
        diag = dsf.coupling_matrix_diag(J_base=J_BASE, J_max=J_MAX)
        values = np.array(list(diag.values()), dtype=np.float64)  # 8 vals
        row = np.repeat(values, 2)  # 16 modes
        for i in range(len(self.neighbors)):
            d = self.ring_distances[i]
            self.J[i] = row / (d + 1)

    def fire_spikes(self, intensity: float, tick: int) -> None:
        """Fire J_ij weighted spikes to neighbors. Stage 1: no-op (K=0).
        Stage 2: cluster handles propagation via LoomCluster.step Phase B."""
        pass


# ---------------------------------------------------------------------------
# Piece 4: Familiarity Feedback Register
# ---------------------------------------------------------------------------

class FamiliarityFeedback:
    """Dead-zone habituation register.

    Δ_eff = Δ_base + match_score
    match_score rises as chi atlas accumulates entries from repeated input.
    Spike intensity: base * max(0, 1 - Δ_eff)
    """

    def __init__(self, delta_base: float = DELTA_BASE):
        self.delta_base = delta_base
        self.match_score = 0.0
        self.delta_eff = delta_base

    def update(self, match_score: float) -> None:
        """Update effective dead-zone from Krimelack recall match_score."""
        self.match_score = float(match_score)
        self.delta_eff = self.delta_base + self.match_score

    def attenuate(self, base_intensity: float) -> float:
        """Apply dead-zone multiplication to spike intensity.
        Returns 0 when Δ_eff >= 1 (fully habituated)."""
        return base_intensity * max(0.0, 1.0 - self.delta_eff)


# ---------------------------------------------------------------------------
# Piece 5: Law-Fields constraint bundle
# ---------------------------------------------------------------------------

@dataclass
class LawField:
    """Single law constraint for the ψ-lattice Hamiltonian."""
    law_id: str
    weight: float
    family: str
    params: Dict[str, Any] = field(default_factory=dict)
    bounds: Dict[str, Any] = field(default_factory=dict)


DEFAULT_LAWS: List[LawField] = [
    LawField(law_id="symmetry.basic",    weight=0.25, family="symmetry.basic"),
    LawField(law_id="consistency.basic", weight=0.25, family="consistency.basic"),
]


# ---------------------------------------------------------------------------
# Piece 6: DNA Expression Site (Stage 1: stub)
# ---------------------------------------------------------------------------

class DNAExpressionSite:
    """DNA expression interface.

    Stage 1: load() stores blueprint unchanged; express() returns it.
    Stage 3: Folding Division drives neurogenesis from blueprint.
    """

    def __init__(self):
        self._blueprint: Optional[Any] = None

    def load(self, dna_blueprint: Any) -> Any:
        """Load blueprint. Returns it unchanged (Stage 1 no-op)."""
        self._blueprint = dna_blueprint
        return dna_blueprint

    def express(self) -> Optional[Any]:
        """Return the loaded blueprint."""
        return self._blueprint


# ---------------------------------------------------------------------------
# Internal: MapInject — DSF + chi → 16-dim injection vector
# ---------------------------------------------------------------------------

def _map_inject(dsf: DSF, chi: int, dim: int = PSI_DIM,
                sigma: float = INJECT_SIGMA) -> np.ndarray:
    """MapInject: project chi address + DSF into DIM-dim injection vector.

    Gaussian peak at (chi mod dim), amplitude from DSF conviction × convergence.
    Gaussian wraps around the ring (shortest-arc distance).

    Args:
        dsf:   8D structural field from L0-L4 kernel
        chi:   winding-number chi address of the input signal
        dim:   ψ-lattice dimension
        sigma: Gaussian width in mode units

    Returns real (dim,) injection vector.
    """
    chi_mode = int(chi) % dim
    indices = np.arange(dim)
    # Wrap-around distance on ring
    dist = np.minimum(np.abs(indices - chi_mode), dim - np.abs(indices - chi_mode))
    gauss = np.exp(-dist.astype(np.float64) ** 2 / (2.0 * sigma ** 2))
    # Amplitude: conviction (B_k) + floor.
    # Not multiplied by S_UF: S_UF can be zero when U_star=1 (burst signals like
    # "fire" have non-uniform event timing → high freedom → S_UF=0), but the
    # krimelack IS still winding directionally (B_k is the correct gate).
    amplitude = float(dsf.B_k) + 0.10
    return gauss * amplitude


# ---------------------------------------------------------------------------
# Piece 7: LoomNeuron — main class wiring all 15 pieces
# ---------------------------------------------------------------------------

class LoomNeuron:
    """Full per-neuron stack (Stage 1, K=0 single-neuron isolation).

    Assembles all 15 pieces. step() executes one substrate cycle.
    get_grandurun_state() returns the 7D complex128 spin-vector via the
    existing _grandurun_state primitive (no reimplementation).
    """

    def __init__(self, neuron_id: str, dna_blueprint: Optional[Any] = None,
                 birth_params: Optional[Dict[str, Any]] = None,
                 primary_modality: str = "language",
                 observable: str = "event_count"):
        self.neuron_id = neuron_id
        self.primary_modality = primary_modality
        # GL-CMD-146: cognition observable, opt-in. "event_count" (default,
        # GL-CMD-140) or "rank_order" (first-wrap timing). Read in _unwrapped_deltas.
        self.observable = observable

        # --- NEW pieces (1-6) ---
        self.psi_lattice = PsiLattice()           # 1. ψ-lattice
        self.spike_buffer = SpikeBuffer()         # 2. Event/Spike Buffer
        self.couplings = CouplingsJij()           # 3. Couplings J_ij
        self.familiarity = FamiliarityFeedback()  # 4. Familiarity Feedback
        self.laws: List[LawField] = list(DEFAULT_LAWS)  # 5. Law-Fields
        self.dna_site = DNAExpressionSite()       # 6. DNA Expression Site
        if dna_blueprint is not None:
            self.dna_site.load(dna_blueprint)

        # --- REUSED primitives (8-15) ---
        self.trit_register = TritRegister(PSI_DIM, parity_K=0)   # 8. TSAC
        # 9. DSF / compute_dsf — used as module-level functions
        self.l6_tcl = L6_TCL()                                    # 10. L6-TCL
        self.chi_atlas = ChiAtlas()                               # 10b. ChiAtlas
        # 11. bt_div / bt_to_int / int_to_bt — module-level, no state

        # 12. Krimelack — GL-CMD-139: primary modality from hemisphere topology
        from .substrate_dna import KRIMELACK_PRIMITIVES
        krim_class = KRIMELACK_PRIMITIVES.get(primary_modality, LanguageKrimelack)
        self.krimelack = krim_class()                             # 12. Krimelack

        self.sensory_bank = SensoryBank()                         # 13. SensoryBank
        # 14. _grandurun_state — used as module-level function
        # 15. _SPIN_VECTOR_DIM — constant

        # GL-CMD-125: multi-krimelack bank for cognition path
        from .binding_atlas import BindingAtlas
        self.krimelack_bank: Dict[str, Any] = {}
        for modality_name, mk_class in KRIMELACK_PRIMITIVES.items():
            if modality_name == primary_modality:
                self.krimelack_bank[modality_name] = self.krimelack
            else:
                self.krimelack_bank[modality_name] = mk_class()
        self.binding_atlas = BindingAtlas()

        # Internal state
        self._last_dsf: Optional[DSF] = None
        self._last_commit_chi: int = 0
        self._last_events: List[Dict] = []
        self._tick: int = 0
        self._last_commit_intensity: float = 0.0

        # Coupling spike accumulators (consumed by next step())
        self._coupling_injection = np.zeros(PSI_DIM, dtype=np.float64)
        self._coupling_modulation_delta: float = 0.0

        # GL-CMD-98: coupling signal accumulator — affects krimelack transduction
        self._coupling_signal_accum: List[float] = []  # spike intensities from neighbors
        self._coupling_omega_shift: float = 0.0        # ω modulation for next tick
        self._positional_phase_offset: float = 0.0     # ring position → krimelack phase

        # Stage 3: fold tracking
        self._fold_sustain_count: int = 0          # consecutive ticks at fold threshold
        self._fold_count: int = 0                  # total folds from this neuron
        self._fold_ticks: List[int] = []           # ticks where folds occurred
        self._last_origin_transducer: str = "language"  # origin tracking
        self._omega_history: List[float] = []      # rolling ω mean window

        # --- GL-CMD-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-EVE-20260707-v1 ---
        # Additive membrane-potential / spike-bus fields (blueprint SS3.1,
        # SS3.3). NOT wired into step() or any existing call path -- see
        # GL-RPT-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-C1-20260707-v1.md for
        # why (halted before the LoomBrain.step/LoomCluster.step rewiring
        # that would connect these to production). receive_spike()/_fire()
        # are usable in isolation today; they do not run unless something
        # calls them.
        self.membrane_potential: float = 0.0
        self.membrane_rest: float = 0.0
        self.membrane_threshold: float = 1.0
        # HEURISTIC: tau_m_ms=20.0 -- biological range for cortical
        # pyramidal neurons (blueprint SS3.1). Class: from-biology-reference.
        # Measurement plan: adjust if firing rates diverge from the 1-4%
        # population-activity target once Phase 3 (lateral inhibition)
        # makes that target enforceable.
        self.tau_m_ms: float = 20.0
        # HEURISTIC: refractory_period_ms=2.0 -- biological absolute
        # refractory period (blueprint SS3.1). Class: from-biology-reference.
        # Measurement plan: verify no neuron fires faster than 500Hz
        # sustained; adjust if observed.
        self.refractory_period_ms: float = 2.0
        self.last_update_time_s: float = 0.0
        self.refractory_until_s: float = 0.0
        self._neuron_lock: threading.Lock = threading.Lock()
        # Chi position for propagation-delay computation (blueprint SS3.3).
        # NOT populated anywhere in Phase 1 -- no per-neuron static chi
        # coordinate exists in the current architecture (chi is associated
        # with committed EVENTS via chi_atlas, not with neuron identity).
        # _compute_propagation_delay_ms() falls back to DEFAULT_DELAY_MS
        # while this is None. Flagged in the Phase 1 report as an open
        # question -- where would a real value come from?
        self.chi_position: Optional[int] = None
        # Set via set_spike_bus() if/when this neuron is wired to a
        # SpikeBus. None by default so _fire() and existing constructors
        # (cluster.py, brain.py, embryo.py all construct LoomNeuron without
        # a bus argument) are unaffected.
        self._spike_bus = None

        # --- GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v1: STDP state ---
        # source_neuron_id -> [(fire_time_s, spike_weight), ...], pruned to
        # STDP_WINDOW_MS on every receive_spike(). External (non-synaptic)
        # sources -- id starts with EXTERNAL_SOURCE_PREFIX -- are never
        # recorded here; STDP only applies to learnable neuron-to-neuron
        # synapses.
        self._recent_presynaptic_fires: Dict[str, List[Tuple[float, float]]] = {}
        # source_neuron_id -> learned incoming synapse weight. Absent key
        # means STDP_DEFAULT_SYNAPSE_WEIGHT (not yet potentiated/depressed).
        # This is what receive_spike() actually scales a real (non-external)
        # spike's contribution by -- couplings.J (read by
        # _get_outgoing_synapses) stays the static Phase-1 OUTGOING weight
        # a sender emits with; this dict is the dynamic, per-neuron,
        # LEARNED weight the receiver applies. Standard split for a
        # per-neuron (not shared-matrix) STDP implementation.
        self._incoming_synapse_weights: Dict[str, float] = {}
        self._last_fire_time_s: float = 0.0
        # Called as fn(word, neuron_id) from _on_fire_bookkeeping when this
        # neuron fires as a direct entry point for a word injection (see
        # set_word_firing_callback). None by default -- existing/other
        # neurons are unaffected.
        self._word_firing_callback = None

        # Apply birth_params if this is a daughter neuron
        if birth_params is not None:
            self._apply_birth_params(birth_params)

    # --- GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v3: pickle round-trip ---
    # save_full_state()/load_full_state() (embryo.py) pickle this object
    # graph wholesale. Without these hooks, two problems: (1) threading.Lock
    # is not picklable in CPython, so __getstate__ must exclude it or
    # save_full_state() raises TypeError the moment a neuron actually has
    # one; (2) pickle.load() reconstructs __dict__ directly and NEVER calls
    # __init__, so a pickle written before a Phase 1 v2 field existed on
    # this class restores an object permanently missing it -- confirmed
    # live in production, see GL-RPT-STDP-INTROSPECTION-C1-20260707-v1 and
    # GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1 findings.

    def __getstate__(self):
        """Exclude unpicklable / runtime-only fields from the pickle.

        _neuron_lock: threading.Lock, not picklable.
        _spike_bus: runtime reference, re-wired at boot by Guala.wire_spike_bus().
        _word_firing_callback: bound method into Guala -- pickling it would
            drag the entire Guala object graph into this one neuron's state.
        """
        state = self.__dict__.copy()
        state.pop('_neuron_lock', None)
        state.pop('_spike_bus', None)
        state.pop('_word_firing_callback', None)
        return state

    def __setstate__(self, state):
        """Restore __dict__, recreate the lock, backfill any Phase 1 v2
        field missing from an older pickle at its real __init__ default.

        Field defaults below are mirrored from __init__ above them in
        this same file -- verified against the live source, not guessed
        (two defaults were caught wrong in an earlier draft of this fix:
        _last_fire_time_s must be 0.0 not None, _recent_presynaptic_fires
        must be {} not [] -- both would crash on first use if wrong).
        """
        self.__dict__.update(state)
        self._neuron_lock = threading.Lock()

        # PHASE_1_V2_BACKFILL -- keep in sync with __init__ above.
        if not hasattr(self, 'membrane_potential'):
            self.membrane_potential = 0.0
        if not hasattr(self, 'membrane_rest'):
            self.membrane_rest = 0.0
        if not hasattr(self, 'membrane_threshold'):
            self.membrane_threshold = 1.0
        if not hasattr(self, 'tau_m_ms'):
            self.tau_m_ms = 20.0
        if not hasattr(self, 'refractory_period_ms'):
            self.refractory_period_ms = 2.0
        if not hasattr(self, 'last_update_time_s'):
            self.last_update_time_s = 0.0
        if not hasattr(self, 'refractory_until_s'):
            self.refractory_until_s = 0.0
        if not hasattr(self, 'chi_position'):
            self.chi_position = None
        if not hasattr(self, '_recent_presynaptic_fires'):
            self._recent_presynaptic_fires = {}
        if not hasattr(self, '_incoming_synapse_weights'):
            self._incoming_synapse_weights = {}
        if not hasattr(self, '_last_fire_time_s'):
            self._last_fire_time_s = 0.0
        # Unlike LoomBrain.step() (which reads _spike_bus via a defensive
        # getattr), _fire() and _on_fire_bookkeeping() access
        # self._spike_bus / self._word_firing_callback directly -- an
        # absent (not None) attribute would raise AttributeError the
        # first time this neuron fires, before Guala.wire_spike_bus() has
        # a chance to run. Backfill to None (the real __init__ default)
        # explicitly, not left absent. wire_spike_bus() overwrites both
        # with the real bus/callback shortly after restore in production.
        if not hasattr(self, '_spike_bus'):
            self._spike_bus = None
        if not hasattr(self, '_word_firing_callback'):
            self._word_firing_callback = None

    # ------------------------------------------------------------------
    # Commit c1's parked neuron-side Phase 1 work per GL-CMD-BLUEPRINT-
    # PHASE-1-MERGED-EVE-20260707-v2 preamble ("What's preserved from c1's
    # parked work"). Event-driven spike handling + STDP synapse plasticity
    # (blueprint v2 SS3.1, SS3.3, SS3.4).
    #
    # History: the original NEURON-AUTONOMY dispatch (event-driven firing
    # alone, no STDP) was halted -- receive_spike/_fire had no path to
    # anything that produces recognition/memory. The MERGED-v1 dispatch
    # added STDP but assumed emission/recall/chi_atlas worked differently
    # than they actually do (7 design errors found by dependency audit,
    # see MERGED-v2's "Why v2 exists"). This neuron-side half (this
    # section) was correct in both v1 and v2 and is unchanged between
    # them -- what changes in v2 is how the engine (gualaloom_v5_engine.py)
    # wires it in: dual-write/dual-read via RECALL_BACKEND, not a
    # wholesale replacement of the legacy binding_atlas path. See
    # GL-RPT-BLUEPRINT-PHASE-1-MERGED-C1-20260707-v2.md for the full
    # verification protocol.
    # ------------------------------------------------------------------

    def set_spike_bus(self, spike_bus) -> None:
        """Wire this neuron to a SpikeBus for outgoing spike emission on
        fire. Optional -- _fire() works (skips emission) with no bus set,
        so this method existing doesn't change behavior for any neuron
        nothing calls it on."""
        self._spike_bus = spike_bus

    def set_word_firing_callback(self, callback) -> None:
        """callback(word: str, neuron_id: str) -> None, invoked when this
        neuron fires as a direct entry point for a word injection (spike
        source is external -- id starts with EXTERNAL_SOURCE_PREFIX -- and
        carries metadata["word"]). Used by Guala to build
        _word_neuron_map/_neuron_word_map (dispatch item 4). Optional --
        None by default, so untouched neurons are unaffected."""
        self._word_firing_callback = callback

    def _prune_presynaptic_history(self, source_id: str, now: float) -> None:
        history = self._recent_presynaptic_fires.get(source_id)
        if not history:
            return
        cutoff = now - STDP_WINDOW_MS / 1000.0
        pruned = [(t, w) for t, w in history if t >= cutoff]
        if pruned:
            self._recent_presynaptic_fires[source_id] = pruned
        else:
            del self._recent_presynaptic_fires[source_id]

    def receive_spike(self, spike) -> None:
        """Called by a SpikeBus when a spike arrives at this neuron.

        Updates membrane potential based on time since last update, adds
        the spike's weighted contribution (scaled by the learned STDP
        incoming-synapse weight for real neuron-to-neuron spikes; used
        raw for external/injection spikes -- see EXTERNAL_SOURCE_PREFIX),
        checks threshold, fires if crossed and not refractory.
        Thread-safe -- spike arrivals are concurrent from the bus's
        delivery thread and (potentially) other callers.
        """
        is_external = spike.source_neuron_id.startswith(EXTERNAL_SOURCE_PREFIX)

        with self._neuron_lock:
            now = time.monotonic()
            dt_ms = (now - self.last_update_time_s) * 1000.0
            if dt_ms > 0:
                decay = math.exp(-dt_ms / self.tau_m_ms)
                self.membrane_potential = (
                    self.membrane_rest
                    + (self.membrane_potential - self.membrane_rest) * decay
                )

            if is_external:
                contribution = spike.weight
            else:
                # STDP-only path: record presynaptic fire history (pruned
                # to STDP_WINDOW_MS) for potentiation on our own next
                # fire, and scale the contribution by our learned
                # incoming weight for this specific source.
                self._recent_presynaptic_fires.setdefault(spike.source_neuron_id, []).append(
                    (now, spike.weight))
                self._prune_presynaptic_history(spike.source_neuron_id, now)
                synapse_weight = self._incoming_synapse_weights.get(
                    spike.source_neuron_id, STDP_DEFAULT_SYNAPSE_WEIGHT)
                contribution = spike.weight * synapse_weight

            self.membrane_potential += contribution
            self.last_update_time_s = now

            if now < self.refractory_until_s:
                return  # absorbed but no firing

            if self.membrane_potential >= self.membrane_threshold:
                self._fire(now, triggering_spike=spike)

    def _apply_stdp_potentiation(self, now: float) -> None:
        """Pre-before-post: for every source that sent us a spike within
        STDP_POTENTIATION_WINDOW_MS of firing now, strengthen that
        source's incoming synapse weight. Caller holds self._neuron_lock."""
        for source_id, history in self._recent_presynaptic_fires.items():
            if not history:
                continue
            last_fire_time = history[-1][0]
            dt_ms = (now - last_fire_time) * 1000.0
            if 0 <= dt_ms <= STDP_POTENTIATION_WINDOW_MS:
                delta = STDP_POTENTIATION_AMPLITUDE * math.exp(-dt_ms / STDP_TAU_MS)
                current = self._incoming_synapse_weights.get(
                    source_id, STDP_DEFAULT_SYNAPSE_WEIGHT)
                self._incoming_synapse_weights[source_id] = min(
                    current + delta, MAX_SYNAPSE_WEIGHT)

    def _receive_upstream_fire_notification(self, source_id: str, source_fire_time: float) -> None:
        """Post-before-pre depression: source_id just fired at
        source_fire_time. If WE fired shortly before that (within
        STDP_DEPRESSION_WINDOW_MS), our firing wasn't caused by that
        source -- weaken source_id's incoming synapse weight onto us.
        Called directly (synchronous bookkeeping call, not a delayed
        spike-bus injection) by the source neuron's _notify_downstream_
        of_fire, so it needs its own lock scope."""
        with self._neuron_lock:
            if self._last_fire_time_s <= 0:
                return
            dt_ms = (source_fire_time - self._last_fire_time_s) * 1000.0
            if 0 <= dt_ms <= STDP_DEPRESSION_WINDOW_MS:
                delta = STDP_DEPRESSION_AMPLITUDE * math.exp(-dt_ms / STDP_TAU_MS)
                current = self._incoming_synapse_weights.get(
                    source_id, STDP_DEFAULT_SYNAPSE_WEIGHT)
                self._incoming_synapse_weights[source_id] = max(
                    current - delta, MIN_SYNAPSE_WEIGHT)

    def _notify_downstream_of_fire(self, now: float) -> None:
        """Synchronously inform each coupled downstream neuron that we
        just fired, so it can apply STDP depression if it fired first.
        Separate from the delayed spike-bus emission in _fire() -- this
        is bookkeeping, not signal propagation, so it isn't subject to
        propagation delay."""
        registry = getattr(self._spike_bus, "_neuron_registry", None) if self._spike_bus else None
        if registry is None:
            return
        for target_id, _weight in self._get_outgoing_synapses():
            if target_id == self.neuron_id:
                # Defensive: a self-loop would re-acquire our own
                # non-reentrant _neuron_lock via _receive_upstream_fire_
                # notification and hang the spike bus's single delivery
                # thread forever. Ring topology shouldn't produce
                # self-loops, but this is cheap insurance against a
                # deadlock class the dispatch explicitly calls out
                # (halt condition 3, prior dispatch).
                continue
            target = registry.get(target_id)
            if target is not None:
                target._receive_upstream_fire_notification(self.neuron_id, now)

    def _fire(self, now: float, triggering_spike=None) -> None:
        """Neuron fires: apply STDP potentiation from recent presynaptic
        history, reset membrane, set refractory, emit spikes to all
        coupled neighbors via the spike bus (if one is set) with computed
        delays, notify downstream neurons synchronously for depression
        bookkeeping. Caller holds self._neuron_lock."""
        self._apply_stdp_potentiation(now)

        self.membrane_potential = self.membrane_rest
        self.refractory_until_s = now + self.refractory_period_ms / 1000.0
        self._last_fire_time_s = now

        if self._spike_bus is not None:
            for target_id, weight in self._get_outgoing_synapses():
                delay_ms = self._compute_propagation_delay_ms(target_id)
                self._spike_bus.inject(
                    target_id=target_id,
                    source_id=self.neuron_id,
                    weight=weight,
                    arrival_delay_ms=delay_ms,
                )
            self._notify_downstream_of_fire(now)

        word = None
        if triggering_spike is not None and triggering_spike.source_neuron_id.startswith(
                EXTERNAL_SOURCE_PREFIX):
            word = triggering_spike.metadata.get("word")

        self._on_fire_bookkeeping(now, word=word)

    def _compute_propagation_delay_ms(self, target_id: str) -> float:
        """Delay is a function of chi-distance between source and target.

        HEURISTIC: linear scaling with chi-distance, 1-20ms range
        (blueprint SS3.3). Class: from-design (chi-distance stands in for
        physical distance since the substrate has no literal physical
        positions). Measurement plan: verify propagation patterns produce
        realistic spike-timing distributions once wired; adjust if
        temporal binding fails.

        Currently always returns DEFAULT_DELAY_MS: self.chi_position is
        None for every neuron in Phase 1 (see __init__ note) since no
        per-neuron static chi coordinate exists in the current
        architecture. Real chi-distance scaling activates once that gap
        is resolved.
        """
        if self.chi_position is None:
            return DEFAULT_DELAY_MS
        registry = getattr(self._spike_bus, "_neuron_registry", None) if self._spike_bus else None
        target = registry.get(target_id) if registry is not None else None
        if target is None or getattr(target, "chi_position", None) is None:
            return DEFAULT_DELAY_MS
        chi_distance = abs(self.chi_position - target.chi_position)
        delay = 1.0 + (chi_distance / MAX_CHI_DISTANCE) * 19.0
        return delay

    def _get_outgoing_synapses(self):
        """Read current outgoing coupling weights from CouplingsJij.

        Phase 1: static weights from the existing coupling structure.
        Phase 2 (NOT this dispatch) will make weights dynamic via STDP.

        Adapted from the dispatch's reference implementation to match
        CouplingsJij's real shape: .neighbors is List[str] of neuron_id
        strings (not neuron objects -- no per-neuron object references to
        neighbors exist), and .J[j_index] is a PSI_DIM=16-element vector
        (one weight per ψ-mode), not a scalar. Reduced to a scalar via
        the SAME convention LoomCluster.step's Phase B already uses
        (float(np.mean(...))) -- mechanical adaptation to real shapes,
        not a new design decision.
        """
        synapses = []
        for j_index, target_id in enumerate(self.couplings.neighbors):
            if j_index >= self.couplings.J.shape[0]:
                continue
            weight = float(np.mean(self.couplings.J[j_index]))
            if weight != 0.0:
                synapses.append((target_id, weight))
        return synapses

    def _on_fire_bookkeeping(self, now: float, word: Optional[str] = None) -> None:
        """Records the fire event.

        GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v1 item 5: chi_atlas
        continues to be WRITTEN for observability only -- nothing reads it
        anymore once emission/recall are migrated to membrane state (see
        gualaloom_v5_engine.py changes; confirmed via grep in the Phase 1
        report). Its exact content is therefore not load-bearing, but it's
        still real (not fabricated) data: motif_id is the word if this
        fire was a direct entry-point injection for one, else the
        neuron's own id (still identifies which neuron fired, when).
        chi_value uses self.chi_position if ever populated, else 0 -- a
        placeholder, honestly labeled as such rather than a fabricated
        dominant_mode (the prior dispatch's concern about NOT inventing
        fake data still applies; the difference here is the value is
        explicitly documented as not read by anything, not passed off as
        meaningful).

        word is also forwarded to the word-neuron population map (dispatch
        item 4) via _word_firing_callback, if this fire was a direct
        entry-point injection for a word (see EXTERNAL_SOURCE_PREFIX
        handling in _fire). This IS load-bearing -- it's what
        _select_entry_neurons and recall's cue lookup read.
        """
        motif_id = word if word is not None else self.neuron_id
        chi_value = self.chi_position if self.chi_position is not None else 0
        self.chi_atlas.record("neuron", motif_id, chi_value, tick=None)

        if word is not None and self._word_firing_callback is not None:
            self._word_firing_callback(word, self.neuron_id)

    # ------------------------------------------------------------------
    # step — one substrate cycle
    # ------------------------------------------------------------------

    def step(self, input_signal, tick: int, input_chi: Optional[int] = None) -> Dict:
        """Execute one substrate cycle.

        Args:
            input_signal: str word OR array-like raw signal
            tick:         current substrate tick

        Returns status dict with committed, n_eff, dsf, spike_count,
                match_score, delta_eff.
        """
        self._tick = tick

        # a. Krimelack transduces input_signal → events
        # GL-CMD-98: compute omega_override from coupling signal accumulator.
        # ω_eff = ω_0 + Σ(spike_intensities) × J_BASE / J_MAX
        # Bounded by J_MAX (no new constant). Each spike contributes
        # proportionally to its J-weighted intensity. Clears after consumption.
        omega_override = None
        if self._coupling_signal_accum:
            omega_shift = sum(self._coupling_signal_accum) * J_BASE / J_MAX
            omega_override = self.krimelack.omega_0 + omega_shift
            self._coupling_signal_accum = []

        # GL-CMD-117: krimelack state persists across ticks (no reset).
        # Track monotonic event count to extract THIS tick's events only.
        # GL-CMD-138: use n_events counter (deque may evict old entries).
        # GL-CMD-139: active_krim tracks whichever krimelack was actually fed.
        active_krim = self.krimelack  # default: primary krimelack
        n_events_before = active_krim.n_events if hasattr(active_krim, 'n_events') else len(active_krim.events)

        _is_lang = isinstance(self.krimelack, LanguageKrimelack)
        if isinstance(input_signal, str) and _is_lang:
            _fp, _role, _senses = self.krimelack.transduce(
                input_signal, omega_override=omega_override,
                phase_offset=self._positional_phase_offset,
                no_reset=True)
            self._last_origin_transducer = "language"
        elif isinstance(input_signal, str) and not _is_lang:
            # Non-language primary krimelack cannot transduce words;
            # route through language krimelack in bank for DSF events
            lang_krim = self.krimelack_bank.get("language")
            if lang_krim is not None:
                active_krim = lang_krim
                n_events_before = active_krim.n_events if hasattr(active_krim, 'n_events') else len(active_krim.events)
                lang_krim.transduce(
                    input_signal, omega_override=omega_override,
                    phase_offset=self._positional_phase_offset,
                    no_reset=True)
            self._last_origin_transducer = "language"
            _senses = {}
        else:
            if omega_override is not None:
                saved = self.krimelack.omega_0
                self.krimelack.omega_0 = omega_override
            if hasattr(self.krimelack, 'feed_signal'):
                self.krimelack.feed_signal(list(input_signal))
            else:
                self.krimelack.feed(list(input_signal))
            if omega_override is not None:
                self.krimelack.omega_0 = saved
            _senses = {}

        # DSF from THIS tick's events only (winding state persists, DSF reflects current signal)
        # GL-CMD-138: slice by count of new events from bounded deque tail
        n_events_after = active_krim.n_events if hasattr(active_krim, 'n_events') else len(active_krim.events)
        new_event_count = n_events_after - n_events_before
        events = list(active_krim.events)[-new_event_count:] if new_event_count > 0 else []
        self._last_events = events

        # Track ω history for recent_omega_mean
        if events:
            _kappa = getattr(active_krim, 'kappa',
                     getattr(getattr(active_krim, '_inner', None),
                             'kappa', 0.0))
            omega_recent = active_krim.omega_0 + _kappa * abs(
                sum(e["s"] for e in events) / len(events)
            )
        else:
            omega_recent = active_krim.omega_0
        self._omega_history.append(omega_recent)
        if len(self._omega_history) > OMEGA_HISTORY_LEN:
            self._omega_history.pop(0)

        # chi address = absolute winding number, mod PSI_DIM
        chi = abs(self.krimelack.winding)

        # b. Familiarity Feedback: match_score from chi atlas, update Δ_eff
        match_score = self.chi_atlas.match_score(self._last_commit_chi, "neuron")
        self.familiarity.update(match_score)

        # c. L0-L4 UF kernel: compute 8D DSF from events
        dsf = compute_dsf(events, atlas_similarity=match_score)
        self._last_dsf = dsf

        # MapInject: chi + DSF → 16-dim injection vector
        inj = _map_inject(dsf, chi)

        # Add deferred coupling injection from previous step's Phase B
        inj = inj + self._coupling_injection
        self._coupling_injection = np.zeros(PSI_DIM, dtype=np.float64)

        # ψ-lattice settles under Hamiltonian
        law_params = [(law.weight, law.family) for law in self.laws]
        self.psi_lattice.settle(inj, law_params)

        # d. L6-TCL: compute n_eff from DSF
        n_eff = self.l6_tcl.n_eff(dsf)

        # e. Commit detection
        committed = self.psi_lattice.committed(dsf)

        if committed:
            # Dominant mode chi = argmax of ψ probabilities. Preserved
            # unchanged for psi_lattice internal bookkeeping (base_intensity
            # below still indexes probs by dominant_mode) -- GL-CMD-CHI-
            # UNIFICATION-EVE-20260707-v3 does not touch this computation.
            probs = self.psi_lattice.probabilities()
            dominant_mode = int(np.argmax(probs))

            # chi_atlas now stores the UPSTREAM chi (the same krimelack-
            # derived chi callers compute for the wave atlas), not
            # dominant_mode -- so match_score(input_chi, ...) at line 588
            # (next tick, querying self._last_commit_chi) can actually land
            # in the same numeric range real callers pass as input_chi.
            # input_chi=None (legacy callsite, backward compat): fall back
            # to dominant_mode, exactly the v2/prior behavior, so non-
            # migrated callers are unaffected.
            _chi_for_atlas = input_chi if input_chi is not None else dominant_mode
            self._last_commit_chi = _chi_for_atlas

            # Record in chi atlas for familiarity tracking
            self.chi_atlas.record("neuron", _chi_for_atlas, dominant_mode, tick)

            # f. Spike: base intensity = dominant mode probability
            base_intensity = float(probs[dominant_mode])
            spike_intensity = self.familiarity.attenuate(base_intensity)
            self._last_commit_intensity = spike_intensity

            self.spike_buffer.append(tick, spike_intensity, None)

            # Fire J_ij spikes to neighbors (no-op K=0)
            self.couplings.fire_spikes(spike_intensity, tick)

        # g. Update couplings from new DSF (no-op K=0)
        self.couplings.update_from_dsf(dsf)

        return {
            "committed": committed,
            "n_eff": n_eff,
            "dsf": dsf,
            "spike_count": len(self.spike_buffer),
            "match_score": match_score,
            "delta_eff": self.familiarity.delta_eff,
        }

    # ------------------------------------------------------------------
    # receive_coupling_spike — modulation from a neighbor (Stage 2)
    # ------------------------------------------------------------------

    def receive_coupling_spike(self, neuron_id_from: str,
                                J_weight: float,
                                source_dsf: DSF,
                                tick: int) -> None:
        """Receive coupling spike from a neighbor neuron.

        Immediate effect:  familiarity.delta_eff += J_weight × 0.05
        Deferred effect:   injection vector += unit_inj × J_weight
                           (consumed by next step()'s ψ-lattice settle)

        Args:
            neuron_id_from: the spiking neighbor's id
            J_weight:       coupling weight from spiking neuron's J matrix
            source_dsf:     the spiking neighbor's DSF state
            tick:           current substrate tick
        """
        # Immediate: raise familiarity dead-zone
        self.familiarity.delta_eff += J_weight * 0.05
        self._coupling_modulation_delta += J_weight * 0.05

        # Deferred: accumulate injection direction from source DSF
        arr = source_dsf.to_array()         # 8D
        inj_dir = np.repeat(arr, 2)         # 16D (matches ψ-lattice dim)
        norm = float(np.linalg.norm(inj_dir))
        if norm > 1e-9:
            self._coupling_injection += (inj_dir / norm) * J_weight

        # GL-CMD-98: coupling signal accumulator — affects NEXT krimelack transduction.
        # The spike intensity modulates what the receiving neuron transduces,
        # not just how the ψ-lattice settles. Bounded by J_MAX (no new constant).
        spike_contribution = min(J_weight * float(source_dsf.B_k), J_MAX)
        self._coupling_signal_accum.append(spike_contribution)

    # ------------------------------------------------------------------
    # Stage 3: Folding Division support
    # ------------------------------------------------------------------

    def _apply_birth_params(self, bp: Dict[str, Any]) -> None:
        """Apply birth parameters from derive_daughter_parameters.

        Called once at construction for daughter neurons.
        """
        # ψ-lattice initial state from overflow
        if "psi_init" in bp:
            psi = np.asarray(bp["psi_init"], dtype=np.complex128)
            norm = float(np.linalg.norm(psi))
            if norm > 1e-12:
                self.psi_lattice.psi = psi / norm

        # Krimelack ω₀ inheritance — use origin transducer's class (GL-CMD-139)
        if "omega_0" in bp:
            from .substrate_dna import KRIMELACK_PRIMITIVES
            origin = bp.get("origin_transducer", self.primary_modality)
            krim_cls = bp.get("krimelack_class",
                              KRIMELACK_PRIMITIVES.get(origin, LanguageKrimelack))
            self.krimelack = krim_cls()
            self.krimelack.omega_0 = float(bp["omega_0"])
            # Re-alias in krimelack_bank so bank[origin] == self.krimelack
            self.krimelack_bank[origin] = self.krimelack

        # Law-field weights from overflow DSF
        if "law_field_weights" in bp:
            lfw = bp["law_field_weights"]
            self.laws = [
                LawField(law_id="continuity",  weight=lfw.get("continuity", 0.25),
                         family="consistency.basic"),
                LawField(law_id="compactness",  weight=lfw.get("compactness", 0.25),
                         family="symmetry.basic"),
                LawField(law_id="consistency",  weight=lfw.get("consistency", 0.25),
                         family="consistency.basic"),
                LawField(law_id="symmetry",     weight=lfw.get("symmetry", 0.25),
                         family="symmetry.basic"),
            ]

        # Origin transducer tracking
        if "origin_transducer" in bp:
            self._last_origin_transducer = bp["origin_transducer"]

    @property
    def last_input_word(self) -> Optional[str]:
        """GL-CMD-99: last word transduced by this neuron's krimelack."""
        return getattr(self.krimelack, 'last_input_word', None)

    @property
    def recent_omega_mean(self) -> float:
        """Rolling mean of krimelack ω_krim over last OMEGA_HISTORY_LEN ticks."""
        if not self._omega_history:
            return self.krimelack.omega_0
        return sum(self._omega_history) / len(self._omega_history)

    def nearest_neighbors(self, k: int) -> List[str]:
        """Return k nearest neighbors by ring position (from couplings list)."""
        return list(self.couplings.neighbors[:k])

    def fold_check(self, tick: int) -> bool:
        """Check if this neuron should fold (Folding Division trigger).

        Returns True when L6-TCL reports n_eff < n_start * FOLD_TRIGGER_RATIO
        for FOLD_SUSTAIN_TICKS consecutive ticks.
        """
        if self._last_dsf is None:
            return False

        n_eff = self.l6_tcl.n_eff(self._last_dsf)
        threshold = self.l6_tcl.n_start * FOLD_TRIGGER_RATIO

        if n_eff < threshold:
            self._fold_sustain_count += 1
        else:
            self._fold_sustain_count = 0

        return self._fold_sustain_count >= FOLD_SUSTAIN_TICKS

    def compute_overflow_signal(self):
        """Compute the overflow signal for Folding Division.

        The overflow is the residual ψ-component that does NOT project
        onto any committed mode (modes above P_COMMIT probability).
        This is standard linear algebra: projection onto the complement.

        Returns an OverflowSignal (imported at call time to avoid circular).
        """
        from .substrate_dna import OverflowSignal

        psi = self.psi_lattice.psi.copy()
        probs = self.psi_lattice.probabilities()

        # Identify committed modes (above P_COMMIT)
        committed_mask = probs >= P_COMMIT

        # Overflow = ψ projected onto the complement of committed modes
        overflow = psi.copy()
        overflow[committed_mask] = 0.0

        # Compute DSF from overflow's event structure
        if self._last_events:
            dsf = compute_dsf(self._last_events,
                              atlas_similarity=self.familiarity.match_score)
        else:
            dsf = compute_dsf([])

        dsf_tuple = (dsf.D_k, dsf.M_k, dsf.R_rev, dsf.U_star,
                     dsf.C_k, dsf.P_k, dsf.B_k, dsf.S_UF)

        return OverflowSignal(
            origin_transducer=self._last_origin_transducer,
            psi_overflow_vector=overflow,
            dsf_tuple=dsf_tuple,
            events=list(self._last_events),
        )

    def clear_overflow_modes(self) -> None:
        """Clear the overflow modes from ψ-lattice after a fold.

        Zeroes uncommitted modes and renormalizes. This allows n_eff
        to recover above the fold threshold.
        """
        probs = self.psi_lattice.probabilities()
        committed_mask = probs >= P_COMMIT

        psi = self.psi_lattice.psi.copy()
        psi[~committed_mask] = 0.0
        norm = float(np.linalg.norm(psi))
        if norm > 1e-12:
            self.psi_lattice.psi = psi / norm
        else:
            # All modes were uncommitted — reset to uniform
            self.psi_lattice.psi = (
                np.ones(PSI_DIM, dtype=np.complex128) / math.sqrt(PSI_DIM)
            )

        # Reset fold sustain counter
        self._fold_sustain_count = 0
        self._fold_count += 1

    # ------------------------------------------------------------------
    # Cognition path — multi-modal binding (GL-CMD-125)
    # ------------------------------------------------------------------

    def experience_moment(self, concept: str,
                          multi_modal_signals: Dict[str, Any],
                          tick: int,
                          precomputed_lanes: Dict[str, Any] = None) -> None:
        """Cognition write — substrate-true multi-modal binding.

        Feeds each modality's signal through its krimelack (no reset),
        reads phase, builds 7-dim state vector, records to BindingAtlas.

        precomputed_lanes: see encode_state -- optional population-loop
        optimization, passed through unchanged.
        """
        state_vec = self.encode_state(multi_modal_signals, precomputed_lanes)
        self.binding_atlas.record(concept, state_vec, tick)

    def encode_state(self, multi_modal_signals: Dict[str, Any],
                      precomputed_lanes: Dict[str, Any] = None):
        """Per-neuron state for binding/recall. Switched by self.observable:
        - "resonant_spectral" (GL-CMD capacity solve): returns a Dict[str, np.ndarray]
          of PER-LANE balanced-ternary chi sub-vectors, one per present array-valued
          modality. GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-207: previously this
          concatenated every present modality's spectrum into ONE vector before
          projecting -- correct for a full cue (lifts n=200 recall from ~18% to
          100%) but broken BY CONSTRUCTION for a partial cue, because the
          concatenation's width (and therefore the projection matrix) depends on
          HOW MANY modalities happen to be present. A 3-lane query landed in a
          projection space unrelated to the 6-lane one it was taught in (T7:
          measured 0% at 3 lanes vs 100% at 5, the "5" case only working by
          accident since language never contributed a lane either way). Fix:
          project each lane SEPARATELY through its own per-(neuron, modality)
          fixed matrix -- a lane's shape depends only on N_RECEPTORS, never on
          which other lanes are present -- so any subset of lanes is directly,
          honestly comparable to the matching lanes of a richer teach-time
          binding (BindingAtlas does the masked, lane-normalized match).
        - else (event_count default / rank_order): R⁶ grandurun vector from
          _unwrapped_deltas (the GL-CMD-140 path), unchanged.

        GL-FIX-POPULATION-LANE-RECOMPUTE (2026-07-06): lane_features(multi_modal_
        signals) does not depend on this neuron at all (it's the raw per-modality
        resonant spectrum of the SIGNAL, shared by every neuron in the population
        vote). Every population-loop caller (remember()/recall_fast/recall_op)
        computes it once and passes it in as precomputed_lanes -- a caller that
        still calls encode_state() directly with no lanes (e.g. a single-neuron
        caller, or a test) is unaffected, since this recomputes lane_features
        exactly as before when precomputed_lanes is None. Only the SHARED,
        neuron-independent input is hoisted; the per-(neuron, modality) projection
        and ternary_chi below are still computed per-neuron, unchanged."""
        from .grandurun import grandurun_state
        if getattr(self, "observable", "event_count") == "resonant_spectral":
            from . import resonant_chi as rc
            lanes = precomputed_lanes if precomputed_lanes is not None else rc.lane_features(multi_modal_signals)
            if not hasattr(self, "_lane_P"):
                self._lane_P = {}
            chi_lanes = {}
            for m, feat in lanes.items():
                key = (self.neuron_id, m)
                if key not in self._lane_P:
                    self._lane_P[key] = rc.neuron_projection(key, len(feat))
                chi_lanes[m] = rc.ternary_chi(feat, self._lane_P[key])
            return chi_lanes
        return grandurun_state(self._unwrapped_deltas(multi_modal_signals))

    def _unwrapped_deltas(self, multi_modal_signals: Dict[str, Any]) -> Dict[str, float]:
        """Per-modality event_count observable with per-neuron attenuation.

        GL-CMD-140: wired in verbatim from the sweep_137 harness mechanism
        that achieved 67% T5 at n=100 (vs the GL-CMD-133/134 phase/winding
        delta-rate path, which scored ~5% in production and is now deleted).
        Symmetric — the same path runs at training write (experience_moment)
        and recall query (brain.recall). The observable is the count of new
        krimelack events per modality (from the GL-CMD-138 n_events counter),
        attenuated per (neuron, modality) by ring position (GL-CMD-131).

        GL-CMD-146: observable is opt-in. Default "event_count" (count of new
        krimelack events per modality). "rank_order" instead ranks modalities by
        first-wrap timing (earliest wrap = highest strength), carrying the
        time-to-first-spike information that event counts discard. The FEED side
        is identical for both — only the returned observable differs. Selected by
        self.observable, so training-write and recall-query switch together.

        GL-CMD-EVENT-COUNT-KRIMELACK-STATE-209: non-language modalities are
        snapshotted before feed_signal() and restored immediately after --
        found live, testing cross-sense recall against the real production
        observable (event_count): teaching concept B right after concept A
        feeds B's signal into the SAME no-reset krimelack A already
        advanced, so B's stored delta is "new events given wherever A left
        the phase," not a stable function of B's own waveform. Two
        concepts' deltas were therefore incomparable, and whichever
        happened to produce the largest magnitude dominated cosine
        matching for every query regardless of content (verified: bell
        taught fresh -> delta 576; cat taught right after -> delta 1381;
        cat's larger delta won every subsequent query including bell's
        own). Language is deliberately excluded -- its no-reset
        cumulative "how many words has she heard" design is intentional
        and separately proven (-177/-178), and it commits its own event
        count read (`ev1`) before this reset would apply anyway. Same
        snapshot/restore idiom brain.py's recall() already uses for its
        own (read-side) protection; this is the equivalent write-side fix
        -- recall() had it, experience_moment() (via this method) didn't.
        """
        from .grandurun import MODALITIES

        observable = getattr(self, 'observable', 'event_count')
        rpos = getattr(self, 'ring_pos', 0)
        rN = getattr(self, 'ring_N', 1)
        deltas = {}
        first_wraps = {}  # modality -> relative first-wrap time (rank_order only)
        for i, m in enumerate(MODALITIES):
            signal = multi_modal_signals.get(m)
            krim = self.krimelack_bank.get(m)
            if signal is None or krim is None:
                deltas[m] = 0.0
                continue
            att = signal_attenuation(rpos, rN, i)
            ev0 = krim.n_events if hasattr(krim, 'n_events') else len(krim.events)
            # Pre-feed krimelack time, so this feed's first-wrap timing is
            # measured RELATIVE to feed start (krim.t is cumulative across the
            # no-reset feeds for oscillator krimelacks; 0 for reset-type adapters
            # whose events restart per feed).
            t_pre = self._krim_time(krim) if observable == "rank_order" else 0.0
            _pre_state = None if m == "language" else _snapshot_single_krim(krim)
            if m == "language":
                krim.transduce(signal, no_reset=True, omega_override=2.0 * att)
            elif hasattr(krim, 'feed_signal'):
                sig = list(signal) if not isinstance(signal, list) else signal
                sig_att = [s * att for s in sig]
                krim.feed_signal(sig_att)
            ev1 = krim.n_events if hasattr(krim, 'n_events') else len(krim.events)
            new_count = ev1 - ev0
            if observable == "rank_order":
                if new_count > 0:
                    # Must read krim.events for the new-event slice BEFORE
                    # restoring below -- the restore reverts krim.events to
                    # its pre-feed contents.
                    new_events = list(krim.events)[-new_count:]
                    first_wraps[m] = float(new_events[0].get("t", 0.0)) - t_pre
                # modalities that did not wrap are omitted -> strength 0 below
            else:
                deltas[m] = float(new_count)
            if _pre_state is not None:
                _restore_single_krim(_pre_state)

        if observable == "rank_order":
            n_mod = len(MODALITIES)
            deltas = {m: 0.0 for m in MODALITIES}
            # earliest first-wrap gets the highest strength (n_mod - rank)
            for rank, (m, _t) in enumerate(
                    sorted(first_wraps.items(), key=lambda kv: kv[1])):
                deltas[m] = float(n_mod - rank)
        return deltas

    @staticmethod
    def _krim_time(krim) -> float:
        """Current cumulative krimelack time (feed-start reference for rank_order).
        Oscillator krimelacks expose .t (directly or via ._inner); reset-type
        adapters (visual/cochlear) restart events per feed, so 0.0 is correct."""
        if hasattr(krim, "t"):
            return float(krim.t)
        inner = getattr(krim, "_inner", None)
        if inner is not None and hasattr(inner, "t"):
            return float(inner.t)
        return 0.0

    # ------------------------------------------------------------------
    # get_grandurun_state — 7D complex128 spin-vector
    # ------------------------------------------------------------------

    def get_grandurun_state(self,
                            target_chi: int,
                            target_source: str,
                            needs_vector,
                            current_tick: int) -> np.ndarray:
        """Return 7D complex128 state vector for this neuron's current binding.

        Delegates to the validated _grandurun_state primitive.
        The binding dict is built from the neuron's current committed state.

        Args:
            target_chi:    reference chi for resonance calculation
            target_source: reference source label (e.g. "corpus")
            needs_vector:  3-element real array [arousal_w, valence_w, surprise_w]
            current_tick:  current substrate tick

        Returns 7-element complex128 array (_SPIN_VECTOR_DIM = 7).
        """
        probs = self.psi_lattice.probabilities()
        strength = float(np.max(probs))

        binding = {
            "chi":         self._last_commit_chi,
            "strength":    strength,
            "source":      "corpus",
            "arousal":     0.5,
            "valence":     0.5,
            "surprise":    0.5,
            "sensory_refs": [],
            "last_tick":   float(self._tick),
            "polarity":    1.0,
        }
        return _grandurun_state(
            binding, target_chi, target_source,
            needs_vector, current_tick,
        )
