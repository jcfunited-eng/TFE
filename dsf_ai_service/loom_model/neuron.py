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

    def __init__(self, n_modes: int = PSI_DIM):
        self.n_modes = n_modes
        self.neighbors: List[str] = []      # neuron_ids of connected neighbors
        self.J = np.zeros((0, n_modes), dtype=np.float64)  # shape (K, n_modes)

    def update_from_dsf(self, dsf: DSF) -> None:
        """Update J_ij from L0-L4 DSF outputs. Stage 1: no-op (K=0).

        Stage 2 formula per Master Spec Ch.7:
          direction:   J = D_k  * J_BASE
          convergence: J = S_UF * J_BASE
          momentum:    J = |M_k| * J_BASE
          binding:     J = C_k/(1+C_k) * J_BASE
          compression: J = P_k/(1+P_k) * J_BASE
          conviction:  J = |B_k| * J_BASE
          freedom:     J = -U_star * J_BASE
          path_kill:   J = R_rev * J_MAX
        """
        if len(self.neighbors) == 0:
            return  # K=0, nothing to update

    def fire_spikes(self, intensity: float, tick: int) -> None:
        """Fire J_ij weighted spikes to neighbors. Stage 1: no-op (K=0)."""
        if len(self.neighbors) == 0:
            return


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

    def __init__(self, neuron_id: str, dna_blueprint: Optional[Any] = None):
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
        else:
            self.krimelack.reset()
            self.krimelack.feed(list(input_signal))
            _senses = {}

        events = list(self.krimelack.events)
        self._last_events = events

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
