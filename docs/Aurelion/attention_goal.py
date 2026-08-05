# attention_goal.py
# Goal-driven attention and plasticity modulation.

from __future__ import annotations
from typing import Dict, Tuple
import numpy as np

MODALS = ["visual","auditory","smell","taste","touch","emotion","lexical"]

class GoalAttention:
    """
    Maintains a current goal and produces (alpha, modal_weights) each step.
    Goals:
      - STABILIZE: consolidate known patterns (lower alpha, raise emotion/touch weights)
      - EXPLORE  : seek novelty (higher alpha, raise visual/auditory/lexical)
      - FOCUS    : narrow onto strongest recalled channels (medium alpha, sharpen top-2)
    """

    def __init__(self):
        self.goal = "STABILIZE"

    def set_goal(self, g: str):
        g = g.upper()
        if g in ("STABILIZE","EXPLORE","FOCUS"):
            self.goal = g

    def decide(self, phi: float, energy: float, recalled: Dict[str, np.ndarray]) -> Tuple[float, Dict[str, float]]:
        if self.goal == "STABILIZE":
            alpha = 0.38
            w = {m: 1.0 for m in MODALS}
            w["emotion"] *= 1.3
            w["touch"]   *= 1.15
            w["lexical"] *= 0.9
        elif self.goal == "EXPLORE":
            alpha = 0.62
            w = {m: 1.0 for m in MODALS}
            w["visual"]  *= 1.25
            w["auditory"]*= 1.15
            w["lexical"] *= 1.20
            w["emotion"] *= 0.85
        else:  # FOCUS
            alpha = 0.5
            strengths = {m: float(np.linalg.norm(recalled.get(m))) for m in MODALS}
            top2 = sorted(strengths.items(), key=lambda kv: kv[1], reverse=True)[:2]
            w = {m: 0.7 for m in MODALS}
            for m,_ in top2:
                w[m] = 1.4

        # normalize weights to mean 1.0
        mean_w = sum(w.values())/len(w)
        w = {m: v/mean_w for m,v in w.items()}
        return alpha, w
