
# RRE Cluster Emulator v2.5 — 5 nodes, phi coupling via simple gating
import numpy as np
from collections import defaultdict
from rre_core import RRE

class SignalGen:
    def __init__(self, kind, seed=0):
        self.kind = kind
        self.rng = np.random.default_rng(seed)
    def sample(self, n=256):
        r = self.rng
        if self.kind == "finance":
            base = r.normal(0, 0.01, size=n).cumsum()
            return base + 0.2*r.standard_normal(n)
        if self.kind == "text":
            lam = np.clip(r.normal(6, 2, size=n), 0.5, 12.0)
            return r.poisson(lam) - lam
        if self.kind == "sensor":
            drift = r.normal(0, 0.01, size=n).cumsum()
            noise = r.normal(0, 0.1, size=n)
            return drift + noise
        if self.kind == "audio":
            t = np.linspace(0, 1, n)
            sig = np.sin(2*np.pi*5*t) + 0.5*np.sin(2*np.pi*11*t)
            return sig + 0.2*r.standard_normal(n)
        if self.kind == "random":
            return r.standard_normal(n)
        return r.standard_normal(n)

class RRECluster:
    def __init__(self):
        self.nodes = {
            "finance": (RRE("finance"), SignalGen("finance", seed=1)),
            "text":    (RRE("text"),    SignalGen("text", seed=2)),
            "sensor":  (RRE("sensor"),  SignalGen("sensor", seed=3)),
            "audio":   (RRE("audio"),   SignalGen("audio", seed=4)),
            "random":  (RRE("random"),  SignalGen("random", seed=5)),
        }
        self.coupling = defaultdict(lambda: defaultdict(float))
        for a in self.nodes:
            for b in self.nodes:
                if a != b:
                    self.coupling[a][b] = 0.05

    def step(self, n=256, params=None):
        results = {}
        phis = {}
        for name, (rre, gen) in self.nodes.items():
            x = gen.sample(n=n)
            if params and name in params:
                op = params[name].get("op")
                amt = float(params[name].get("amount", 0.1))
                if op == "smooth_up":
                    k = max(3, int(amt*10))
                    x = np.convolve(x, np.ones(k)/k, mode="same")
                elif op == "inject_probe":
                    t = np.linspace(0, 2*np.pi, x.size)
                    x = x + amt*np.sin(3*t)
                elif op == "suppress_outliers":
                    lim = np.percentile(np.abs(x), 90) * (1.0-0.5*amt)
                    x = np.clip(x, -lim, lim)
            phi, H = rre.ingest(x)
            results[name] = dict(phi=phi, H=H)
            phis[name] = phi
        influence = {}
        for a in self.nodes:
            delta = 0.0; better = 0
            for b in self.nodes:
                if a == b: continue
                if phis[b] > phis[a]:
                    delta += self.coupling[a][b]*(phis[b]-phis[a]); better += 1
            influence[a] = delta if better>0 else 0.0
            results[a]["influence"] = influence[a]
        return results
