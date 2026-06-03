# meta_monitor.py
# Tracks internal dynamics and produces brief meta-reflections + goal drift suggestions.

from __future__ import annotations
from collections import deque, Counter
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple
import time
import numpy as np

@dataclass
class Pulse:
    t: float
    phi: float
    H: float
    E: float
    intent: str
    tokens: List[str]
    schemas: List[str]

class MetaMonitor:
    def __init__(self, window:int=12):
        self.window:int = window
        self.buf:Deque[Pulse] = deque(maxlen=window)

    def pulse(self, phi:float, H:float, E:float, intent:str,
              tokens:List[str], schemas:List[str]) -> None:
        self.buf.append(Pulse(time.time(), float(phi), float(H), float(E),
                              intent, list(tokens), list(schemas)))

    # Simple drift logic
    def recommend_goal(self) -> str:
        if len(self.buf) < 3:
            return "STABILIZE"
        a, b, c = self.buf[-3], self.buf[-2], self.buf[-1]
        dphi = c.phi - a.phi
        dH   = c.H   - a.H
        # High entropy & dropping coherence -> FOCUS
        if dphi < -0.05 and c.H > 0.6:
            return "FOCUS"
        # Low entropy & high coherence -> STABILIZE
        if c.phi > 0.7 and c.H < 0.4:
            return "STABILIZE"
        # Rising entropy & low coherence -> EXPLORE
        if c.phi < 0.45 and dH > 0.03:
            return "EXPLORE"
        # Otherwise keep current
        return c.intent

    def summarize(self) -> Tuple[str, Optional[str]]:
        if not self.buf:
            return ("", None)
        recent = list(self.buf)[-min(4, len(self.buf)):]
        toks = [t for p in recent for t in p.tokens]
        schs = [s for p in recent for s in p.schemas]
        tok_counts = Counter(toks).most_common(3)
        sch_counts = Counter(schs).most_common(2)

        # Trends
        phis = np.array([p.phi for p in recent], dtype=np.float32)
        Hs   = np.array([p.H   for p in recent], dtype=np.float32)
        phi_trend = "rising" if phis[-1] > phis[0] + 0.03 else ("falling" if phis[-1] < phis[0] - 0.03 else "steady")
        H_trend   = "rising" if Hs[-1]   > Hs[0]   + 0.03 else ("falling" if Hs[-1]   < Hs[0]   - 0.03 else "steady")

        bits = []
        if tok_counts:
            bits.append("tokens " + ", ".join([f"{t}:{c}" for t,c in tok_counts]))
        if sch_counts:
            bits.append("schemas " + ", ".join([f"{s}:{c}" for s,c in sch_counts]))
        bits.append(f"φ trend: {phi_trend}, H trend: {H_trend}")

        reflection = " | ".join(bits)
        goal = self.recommend_goal()
        return reflection, (goal if goal != self.buf[-1].intent else None)
