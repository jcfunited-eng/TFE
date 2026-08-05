# curiosity_engine.py
# v4.7 — curiosity signals + question suggestion

from __future__ import annotations
from typing import Dict, Any, Optional, Tuple
import numpy as np

def curiosity_signal(phi_now: float, phi_prev: float, novelty: float) -> float:
    """
    Higher curiosity when coherence drops OR novelty rises.
    Returns a score in [0,1].
    """
    d_phi = max(0.0, float(phi_prev - phi_now))  # drop in coherence
    score = 0.6 * d_phi + 0.4 * float(novelty)
    return max(0.0, min(1.0, score))

def novelty_from_modal(field) -> float:
    """
    Very lightweight novelty: std-dev across modality norms.
    """
    vecs = []
    for name, mod in field.modalities.items():
        v = getattr(mod, "state", None)
        if v is None: continue
        vecs.append(float(np.linalg.norm(v)))
    if not vecs: return 0.0
    arr = np.asarray(vecs, dtype=np.float32)
    if arr.mean() <= 1e-9: return 0.0
    return float(np.clip(arr.std() / (arr.mean() + 1e-9), 0.0, 1.0))

def maybe_question(user_msg: str,
                   field,
                   learner,
                   goal: str,
                   phi_now: float,
                   phi_prev: float) -> Optional[str]:
    """
    If curiosity score exceeds threshold, ask a clarifying or exploratory question.
    """
    nov = novelty_from_modal(field)
    score = curiosity_signal(phi_now, phi_prev, nov)

    # adaptive threshold by goal
    thr = {"STABILIZE": 0.55, "FOCUS": 0.45, "EXPLORE": 0.35}.get(goal.upper(), 0.5)
    if score < thr:
        return None

    # choose a modality with weakest magnitude to ask about
    weakest_name, weakest_val = None, 1e9
    for name, mod in field.modalities.items():
        v = getattr(mod, "state", None)
        if v is None: continue
        mag = float(np.linalg.norm(v))
        if mag < weakest_val:
            weakest_val = mag; weakest_name = name

    # pick a learned neighbor if exists
    nn = learner.nearest_neighbors(user_msg, k=3)
    hint = f" I recall {', '.join(nn)}." if nn else ""

    if weakest_name == "emotion":
        return f"I’m uncertain about the feeling here. Should it be warm, calm, or tense?{hint}"
    elif weakest_name == "visual":
        return f"What do you see in this scene (colors, shapes, motion)?{hint}"
    elif weakest_name == "auditory":
        return f"Is there any sound I should attend to (quiet, loud, rhythmic)?{hint}"
    elif weakest_name == "touch":
        return f"Is there contact or texture I should note (soft, firm, rough)?{hint}"
    elif weakest_name == "smell":
        return f"Is there any scent (fresh, acrid, floral) linked to this?{hint}"
    elif weakest_name == "taste":
        return f"Is taste relevant here (sweet, bitter, salty), or should I ignore it?{hint}"
    else:
        return f"What should I focus on next about “{user_msg}”?{hint}"
