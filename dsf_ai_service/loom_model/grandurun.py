"""
grandurun.py — Per-binding state vector for cognition path.

GL-CMD-133: R⁶ Δ-space encoding with cosine similarity.
Replaces exp(1j·Δ) complex encoding from -125/-129.

6-dim real vector of per-modality unwrapped phase deltas.
Recall via L2-normalized cosine similarity. No wraparound artifacts.
"""

import numpy as np
from typing import Dict, Tuple, List, Optional

STATE_DIM = 6
MODALITIES = ["visual", "auditory", "tactile", "olfactory", "gustatory", "language"]

assert STATE_DIM == len(MODALITIES)


def grandurun_state(deltas: Dict[str, float]) -> np.ndarray:
    """Build R⁶ Δ-vector from per-modality unwrapped phase deltas."""
    vec = np.zeros(STATE_DIM, dtype=np.float64)
    for i, m in enumerate(MODALITIES):
        vec[i] = float(deltas.get(m, 0.0))
    return vec


def recall_best(target_vec: np.ndarray,
                atlas_matrix: np.ndarray,
                atlas_concepts: List[str]) -> Tuple[Optional[str], float]:
    """Cosine similarity in R⁶. Returns (best_concept, best_cosine)."""
    if atlas_matrix.shape[0] == 0:
        return None, 0.0
    t_norm = np.linalg.norm(target_vec)
    if t_norm < 1e-12:
        return None, 0.0
    t_hat = target_vec / t_norm
    a_norms = np.linalg.norm(atlas_matrix, axis=1)
    valid = a_norms > 1e-12
    if not valid.any():
        return None, 0.0
    cos = np.zeros(atlas_matrix.shape[0])
    cos[valid] = (atlas_matrix[valid] @ t_hat) / a_norms[valid]
    best_idx = int(np.argmax(cos))
    return atlas_concepts[best_idx], float(cos[best_idx])
