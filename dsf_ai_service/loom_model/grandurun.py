"""
grandurun.py — Per-binding state vector for cognition path.

Per GL-SPC-COGNITION-PATH-EVE-20260622-124 §2.1.

7-dim complex state vector encoding multi-modal phase fingerprint.
Recall via complex inner product. No quantization, no heuristics.
"""

import math, cmath
import numpy as np
from typing import Dict, Tuple, List, Optional

STATE_DIM = 7
N_PHASE_DIMS = 6
MODALITIES = ["visual", "auditory", "tactile", "olfactory", "gustatory", "language"]

assert N_PHASE_DIMS == len(MODALITIES)
assert STATE_DIM == N_PHASE_DIMS + 1


def grandurun_state(phases: Dict[str, float], polarity: float = 1.0) -> np.ndarray:
    """Build a 7-dim complex state vector from per-modality phases.

    Args:
        phases: {modality_name: phase_radians} for all 6 modalities.
                Missing modalities default to 0 (no contribution after exp).
        polarity: +1.0 for positive bindings (substrate-canonical default).

    Returns:
        ndarray of shape (7,) dtype complex128.
    """
    vec = np.zeros(STATE_DIM, dtype=np.complex128)
    for i, m in enumerate(MODALITIES):
        phase = phases.get(m, 0.0)
        vec[i] = cmath.exp(1j * phase)
    vec[STATE_DIM - 1] = complex(polarity, 0.0)
    return vec


def recall_best(target_vec: np.ndarray,
                atlas_matrix: np.ndarray,
                atlas_concepts: List[str]) -> Tuple[Optional[str], float]:
    """Vectorized max-inner-product search across an atlas.

    Args:
        target_vec: query state vector, shape (7,) complex128
        atlas_matrix: stacked binding state vectors, shape (N_bindings, 7) complex128
        atlas_concepts: list of length N_bindings with concept labels

    Returns:
        (best_concept, best_score) where best_score = max |<target, binding>|
    """
    if atlas_matrix.shape[0] == 0:
        return None, 0.0
    inners = np.abs(atlas_matrix @ np.conj(target_vec))
    best_idx = int(np.argmax(inners))
    return atlas_concepts[best_idx], float(inners[best_idx])
