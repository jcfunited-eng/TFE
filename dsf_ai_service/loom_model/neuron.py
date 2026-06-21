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
SETTLE_EPS = 0.25     # imaginary-time step size
INJECT_SIGMA = 1.0    # Gaussian width (modes) for MapInject localization
FOLD_TRIGGER_RATIO = math.exp(-1)  # 1/e — from L6-TCL physics (Master Spec Ch.11)
FOLD_SUSTAIN_TICKS = 3             # consecutive ticks at n_eff < threshold for fold
OMEGA_HISTORY_LEN = 32             # rolling window for recent_omega_mean


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
                 neighbors: Optional[List[str]] = None):
        self.n_modes = n_modes
        self.neighbors: List[str] = neighbors if neighbors is not None else []
        K = len(self.neighbors)
        # Stage 1 (K=0): shape (0, n_modes). Stage 2 (K=16): shape (16, n_modes).
        # Initial values: J_BASE across all entries (refined on first step).
        self.J = np.full((K, n_modes), J_BASE, dtype=np.float64)

    def update_from_dsf(self, dsf: DSF) -> None:
        """Update J_ij from L0-L4 DSF outputs.

        Per Master Spec Ch.7 table — 8 coupling values from DSF, repeated
        2× to fill PSI_DIM=16 modes. Each neighbor row gets the same
        per-neuron coupling profile (differentiation comes from which
        neurons are neighbors, not per-neighbor tuning at Stage 2).
        """
        if len(self.neighbors) == 0 or dsf is None:
            return
        diag = dsf.coupling_matrix_diag(J_base=J_BASE, J_max=J_MAX)
        values = np.array(list(diag.values()), dtype=np.float64)  # 8 vals
        row = np.repeat(values, 2)  # 16 modes
        for i in range(len(self.neighbors)):
            self.J[i] = row

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
                 birth_params: Optional[Dict[str, Any]] = None):
        self.neuron_id = neuron_id

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
        self.krimelack = LanguageKrimelack()                      # 12. Krimelack
        self.sensory_bank = SensoryBank()                         # 13. SensoryBank
        # 14. _grandurun_state — used as module-level function
        # 15. _SPIN_VECTOR_DIM — constant

        # Internal state
        self._last_dsf: Optional[DSF] = None
        self._last_commit_chi: int = 0
        self._last_events: List[Dict] = []
        self._tick: int = 0
        self._last_commit_intensity: float = 0.0

        # Coupling spike accumulators (consumed by next step())
        self._coupling_injection = np.zeros(PSI_DIM, dtype=np.float64)
        self._coupling_modulation_delta: float = 0.0

        # Stage 3: fold tracking
        self._fold_sustain_count: int = 0          # consecutive ticks at fold threshold
        self._fold_count: int = 0                  # total folds from this neuron
        self._fold_ticks: List[int] = []           # ticks where folds occurred
        self._last_origin_transducer: str = "language"  # origin tracking
        self._omega_history: List[float] = []      # rolling ω mean window

        # Apply birth_params if this is a daughter neuron
        if birth_params is not None:
            self._apply_birth_params(birth_params)

    # ------------------------------------------------------------------
    # step — one substrate cycle
    # ------------------------------------------------------------------

    def step(self, input_signal, tick: int) -> Dict:
        """Execute one substrate cycle.

        Args:
            input_signal: str word OR array-like raw signal
            tick:         current substrate tick

        Returns status dict with committed, n_eff, dsf, spike_count,
                match_score, delta_eff.
        """
        self._tick = tick

        # a. Krimelack transduces input_signal → events
        if isinstance(input_signal, str):
            _fp, _role, _senses = self.krimelack.transduce(input_signal)
            self._last_origin_transducer = "language"
        else:
            self.krimelack.reset()
            self.krimelack.feed(list(input_signal))
            _senses = {}
            # Origin stays as previously set (touch/audio/etc via birth_params)

        events = list(self.krimelack.events)
        self._last_events = events

        # Track ω history for recent_omega_mean
        if events:
            omega_recent = self.krimelack.omega_0 + self.krimelack.kappa * abs(
                sum(e["s"] for e in events) / len(events)
            )
        else:
            omega_recent = self.krimelack.omega_0
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
            # Dominant mode chi = argmax of ψ probabilities
            probs = self.psi_lattice.probabilities()
            dominant_mode = int(np.argmax(probs))
            self._last_commit_chi = dominant_mode

            # Record in chi atlas for familiarity tracking
            self.chi_atlas.record("neuron", dominant_mode, dominant_mode, tick)

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

        # Krimelack ω₀ inheritance
        if "omega_0" in bp:
            self.krimelack = LanguageKrimelack()
            self.krimelack.omega_0 = float(bp["omega_0"])

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
