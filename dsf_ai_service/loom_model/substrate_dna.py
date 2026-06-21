"""
substrate_dna.py — Substrate DNA toolkit catalog + derive_daughter_parameters.

GL-CMD-LOOM-STAGE3-FOLDING-CLAUDE-20260620-84
Reference: GL-SPC-SUBSTRATE-DNA-TRUE-CLAUDE-20260620-83

Factual catalog of the 6 transducer primitives that exist in the substrate.
Pure-function derivation of daughter neuron parameters from overflow signal.

NO categories. NO archetypes. NO classification. The daughter is whatever
physics makes her at the fold moment.

Adapter classes: thin wrappers around existing transduction code to provide
a uniform .transduce(signal) / .events / .winding interface.
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Existing transducer imports
# ---------------------------------------------------------------------------
from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
from dsf_ai_service.sensory_krimelacks import (
    OscillatorKrimelack, MODAL_TUNING, sensory_dict_to_signal,
)
from dsf_ai_service.visual_krimelack import AdaptingFoveaKrimelack, DT as VIS_DT
from dsf_ai_service.substrate.senses.GL_MDL_AUDITORY_CORTEX_WC_20260608_01 import (
    cochlear_transduce, COCHLEAR_BANDS,
)
from dsf_ai_service.substrate.sensory_generators import (
    generate_touch_waveform, generate_smell_waveform, generate_taste_waveform,
    transduce_sensory_signals, TOUCH_LIBRARY,
)
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import compute_dsf

# ---------------------------------------------------------------------------
# Constants — all from existing substrate code or Master Spec
# ---------------------------------------------------------------------------
K_TOTAL = 16
J_BASE = 1.0
J_MAX = 1.5
CHI_BAND = 2
PSI_LATTICE_DIM = 16
FOLD_TRIGGER_RATIO = math.exp(-1)  # 1/e from L6-TCL physics (Ch.11)


# ---------------------------------------------------------------------------
# Adapter classes — uniform .transduce(signal) / .events / .winding interface
# ---------------------------------------------------------------------------

class TactileKrimelack:
    """Adapter: touch waveform → OscillatorKrimelack transduction.

    .transduce(params_dict) runs generate_touch_waveform + feeds all channels
    through a touch-tuned OscillatorKrimelack, collecting merged events.
    """

    def __init__(self, omega_0=None):
        tuning = MODAL_TUNING["touch"]
        self.omega_0 = omega_0 if omega_0 is not None else tuning["omega_0"]
        self._tuning = {**tuning, "omega_0": self.omega_0}
        self.events = []
        self.winding = 0

    def reset(self):
        self.events = []
        self.winding = 0

    def transduce(self, signal):
        """Transduce touch params dict or raw signal array.

        If dict: generate_touch_waveform → feed all channels.
        If array-like: feed directly as single channel.
        """
        self.reset()
        osc = OscillatorKrimelack(**self._tuning)
        if isinstance(signal, dict):
            waveforms = generate_touch_waveform(signal)
            for _channel, wave in sorted(waveforms.items()):
                osc.feed_signal(wave)
        else:
            osc.feed_signal(list(signal))
        self.events = list(osc.events)
        self.winding = osc.winding
        return self.events


class OlfactoryKrimelack:
    """Adapter: smell params → OscillatorKrimelack transduction."""

    def __init__(self, omega_0=None):
        tuning = MODAL_TUNING["smell"]
        self.omega_0 = omega_0 if omega_0 is not None else tuning["omega_0"]
        self._tuning = {**tuning, "omega_0": self.omega_0}
        self.events = []
        self.winding = 0

    def reset(self):
        self.events = []
        self.winding = 0

    def transduce(self, signal):
        self.reset()
        osc = OscillatorKrimelack(**self._tuning)
        if isinstance(signal, dict):
            waveforms = generate_smell_waveform(signal)
            for _channel, wave in sorted(waveforms.items()):
                osc.feed_signal(wave)
        else:
            osc.feed_signal(list(signal))
        self.events = list(osc.events)
        self.winding = osc.winding
        return self.events


class GustatoryKrimelack:
    """Adapter: taste params → OscillatorKrimelack transduction."""

    def __init__(self, omega_0=None):
        tuning = MODAL_TUNING["taste"]
        self.omega_0 = omega_0 if omega_0 is not None else tuning["omega_0"]
        self._tuning = {**tuning, "omega_0": self.omega_0}
        self.events = []
        self.winding = 0

    def reset(self):
        self.events = []
        self.winding = 0

    def transduce(self, signal):
        self.reset()
        osc = OscillatorKrimelack(**self._tuning)
        if isinstance(signal, dict):
            waveforms = generate_taste_waveform(signal)
            for _channel, wave in sorted(waveforms.items()):
                osc.feed_signal(wave)
        else:
            osc.feed_signal(list(signal))
        self.events = list(osc.events)
        self.winding = osc.winding
        return self.events


class VisualKrimelack:
    """Adapter: wraps AdaptingFoveaKrimelack with .transduce/.events/.winding."""

    def __init__(self, omega_0=None):
        self.omega_0 = omega_0 if omega_0 is not None else 5.0
        self._fovea = AdaptingFoveaKrimelack(omega_0=self.omega_0)
        self.events = []
        self.winding = 0

    def reset(self):
        self._fovea = AdaptingFoveaKrimelack(omega_0=self.omega_0)
        self.events = []
        self.winding = 0

    def transduce(self, signal):
        """Signal: 1D array of intensity values or 2D image (flattened)."""
        self.reset()
        arr = np.asarray(signal, dtype=np.float64).ravel()
        for i, intensity in enumerate(arr):
            t = float(i) * VIS_DT
            self._fovea.tick(float(intensity), t)
        # AdaptingFoveaKrimelack stores events as plain timestamps
        self.events = [
            {"t": t_ev, "dw": +1, "s": 1.0}
            for t_ev in self._fovea.events
        ]
        self.winding = self._fovea.winding_count
        return self.events


class CochlearBankKrimelack:
    """Adapter: wraps cochlear_transduce with .transduce/.events/.winding."""

    def __init__(self, omega_0=None):
        self.omega_0 = omega_0 if omega_0 is not None else 2.0
        self.events = []
        self.winding = 0

    def reset(self):
        self.events = []
        self.winding = 0

    def transduce(self, signal):
        """Signal: 1D audio waveform array."""
        self.reset()
        arr = np.asarray(signal, dtype=np.float64)
        cochlear = cochlear_transduce(arr)
        total_winding = 0
        all_events = []
        for _band_name, band_data in sorted(cochlear.items()):
            total_winding += band_data["winding"]
            all_events.extend(band_data["events"])
        all_events.sort(key=lambda e: e["t"])
        self.events = all_events
        self.winding = total_winding
        return self.events


# ---------------------------------------------------------------------------
# KRIMELACK_PRIMITIVES — factual catalog of the 6 transducer paths
# ---------------------------------------------------------------------------

KRIMELACK_PRIMITIVES = {
    "language":  LanguageKrimelack,
    "tactile":   TactileKrimelack,
    "olfactory": OlfactoryKrimelack,
    "gustatory": GustatoryKrimelack,
    "visual":    VisualKrimelack,
    "auditory":  CochlearBankKrimelack,
}


# ---------------------------------------------------------------------------
# OverflowSignal — what the fold moment produces
# ---------------------------------------------------------------------------

@dataclass
class OverflowSignal:
    """The state captured at the moment of Folding Division."""
    origin_transducer: str            # key into KRIMELACK_PRIMITIVES
    psi_overflow_vector: np.ndarray   # residual ψ not absorbed by committed modes
    dsf_tuple: tuple                  # (D, M, R_rev, U_star, C, P, B, S_UF)
    events: List[Dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# derive_daughter_parameters — pure function, no hidden state
# ---------------------------------------------------------------------------

def derive_daughter_parameters(overflow_signal: OverflowSignal,
                                parent) -> Dict[str, Any]:
    """Derive all daughter neuron parameters from the overflow signal and parent.

    Pure function: same inputs → identical outputs. No randomness.

    Returns dict with:
        krimelack_class:      class from KRIMELACK_PRIMITIVES
        psi_init:             normalized overflow ψ-vector
        omega_0:              parent's recent krimelack ω mean
        law_field_weights:    {continuity, compactness, consistency, symmetry}
        k_intra:              round(K_TOTAL × P)
        k_inter:              K_TOTAL - k_intra
        inherited_neighbors:  parent's K_TOTAL//2 nearest neighbors
    """
    origin = overflow_signal.origin_transducer
    krimelack_cls = KRIMELACK_PRIMITIVES.get(origin, LanguageKrimelack)

    # ψ initial state: normalized overflow vector
    psi_vec = overflow_signal.psi_overflow_vector.copy()
    norm = float(np.linalg.norm(psi_vec))
    if norm > 1e-12:
        psi_init = psi_vec / norm
    else:
        psi_init = np.ones(PSI_LATTICE_DIM, dtype=np.complex128) / math.sqrt(PSI_LATTICE_DIM)

    # ω₀ from parent's recent krimelack mean
    omega_0 = parent.recent_omega_mean

    # Law-field weights from overflow DSF (Section 2d of GL-SPC-83)
    D, M, R_rev, U_star, C, P, B, S_UF = overflow_signal.dsf_tuple
    raw_weights = {
        "continuity":  abs(float(M)),      # momentum → continuity
        "compactness": abs(float(P)),      # compression → compactness
        "consistency": abs(float(S_UF)),   # convergence → consistency
        "symmetry":    abs(float(B)),      # conviction → symmetry
    }
    total = sum(raw_weights.values())
    if total < 1e-12:
        law_field_weights = {k: 0.25 for k in raw_weights}
    else:
        law_field_weights = {k: v / total for k, v in raw_weights.items()}

    # Coupling distribution from P_k (Section 2e of GL-SPC-83)
    k_intra = round(K_TOTAL * abs(float(P)))
    k_intra = max(0, min(K_TOTAL, k_intra))
    k_inter = K_TOTAL - k_intra

    # Inherited neighbors: K_TOTAL//2 nearest by ring distance
    inherited_neighbors = parent.nearest_neighbors(K_TOTAL // 2)

    return {
        "krimelack_class": krimelack_cls,
        "psi_init": psi_init,
        "omega_0": omega_0,
        "law_field_weights": law_field_weights,
        "k_intra": k_intra,
        "k_inter": k_inter,
        "inherited_neighbors": inherited_neighbors,
        "origin_transducer": origin,
    }
