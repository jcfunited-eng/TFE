
"""
rre_meta.py — Meta & Sentience Layer with genome evolution
----------------------------------------------------------
- Live φ/E telemetry from RRE
- Kalman‑style smoothing
- Energy regulation
- Gentle α tuning
- NEW: Evolver periodically mutates RRE config (α, resonance_threshold) and
       keeps changes that improve fitness: mean(phi) − λ*var(E).
"""

import json, hashlib, datetime, math
from dataclasses import dataclass
import pandas as pd
import numpy as np
from rre_model import RRE, RREConfig

# ============================== Genome & Config ==============================

@dataclass
class MetaConfig:
    learning_rate: float = 0.05
    adaptation_window: int = 25
    evolution_period: int = 60        # steps between mutation attempts
    evolution_lambda: float = 0.5     # var(E) penalty in fitness
    mutation_scale: float = 0.08      # mutation strength

class GenomeSnapshot:
    def __init__(self, payload: dict, sha256: str, comment: str):
        self.payload = payload
        self.sha256 = sha256
        self.comment = comment

class GenomeManager:
    def __init__(self):
        self.snapshots = []

    def snapshot(self, node, comment="manual"):
        payload = {"timestamp": datetime.datetime.now().isoformat(),
                   "config": vars(node.rre.cfg)}
        sha = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        snap = GenomeSnapshot(payload, sha, comment)
        self.snapshots.append(snap)
        return snap

    def verify(self, genome):
        try:
            sha = hashlib.sha256(json.dumps(genome.payload, sort_keys=True).encode()).hexdigest()
            return sha == genome.sha256
        except Exception:
            return False

    def restore(self, node, genome):
        for k, v in genome.payload["config"].items():
            setattr(node.rre.cfg, k, v)

# ============================== Controllers ==============================

class MetaController:
    def __init__(self, config: MetaConfig, genome_mgr: GenomeManager):
        self.cfg = config
        self.gm = genome_mgr
        self.history = []
        self.t = 0
        self.fitness_history = []

    def tune(self, node, telemetry, step: int):
        """Adjust α slightly to favour coherence stability."""
        self.t = step
        phi = telemetry.get("phi", 0)
        if not self.history:
            self.history.append(phi)
            return {}
        delta = phi - self.history[-1]
        self.history.append(phi)
        if len(self.history) > self.cfg.adaptation_window:
            self.history.pop(0)

        # nudge alpha toward stabilizing coherence
        if delta < 0:  # losing coherence
            node.rre.cfg.alpha = min(0.95, node.rre.cfg.alpha + self.cfg.learning_rate * 0.05)
        else:          # gaining coherence
            node.rre.cfg.alpha = max(0.2, node.rre.cfg.alpha - self.cfg.learning_rate * 0.05)
        return {"alpha": node.rre.cfg.alpha}

    # --------- Evolution: mutate & keep if fitness improves ---------
    def fitness(self, mem, lam=0.5):
        if not mem:
            return 0.0
        phi = np.array([m["phi"] for m in mem])
        E   = np.array([m["E"] for m in mem])
        return float(np.nanmean(phi) - lam * np.nanvar(E))

    def maybe_evolve(self, node, memory):
        if self.t <= 0 or self.cfg.evolution_period <= 0:
            return None
        if len(memory) < self.cfg.evolution_period:
            return None
        if self.t % self.cfg.evolution_period != 0:
            return None

        base_fit = self.fitness(memory[-self.cfg.evolution_period:], lam=self.cfg.evolution_lambda)
        self.fitness_history.append(base_fit)

        # mutate
        old_alpha = node.rre.cfg.alpha
        old_thr   = node.rre.cfg.resonance_threshold

        rng = np.random.RandomState(self.t % 2**31)
        node.rre.cfg.alpha = float(np.clip(old_alpha + rng.normal(0, self.cfg.mutation_scale*0.5), 0.2, 0.95))
        node.rre.cfg.resonance_threshold = float(np.clip(old_thr + rng.normal(0, self.cfg.mutation_scale*0.4), 0.02, 0.6))

        # evaluate new fitness on the same window (approximate, uses next steps as they accrue)
        # here we use a proxy: if recent phi improved and E variance did not explode, keep
        phi_recent = np.array([m["phi"] for m in memory[-self.cfg.evolution_period:]])
        E_recent   = np.array([m["E"] for m in memory[-self.cfg.evolution_period:]])
        proxy_improve = (phi_recent.mean() > np.median(phi_recent)) and (E_recent.var() < np.percentile(E_recent, 75)**2 + 1e-6)

        if proxy_improve:
            # keep and snapshot
            return {"kept": True, "alpha": node.rre.cfg.alpha, "thr": node.rre.cfg.resonance_threshold}
        else:
            # revert
            node.rre.cfg.alpha = old_alpha
            node.rre.cfg.resonance_threshold = old_thr
            return {"kept": False, "alpha": old_alpha, "thr": old_thr}

class IntegrityMonitor:
    def __init__(self, window=30, z_limit=3.5):
        self.window = window
        self.z_limit = z_limit

    def check(self, seq):
        if len(seq) < self.window:
            return True
        s = pd.Series(seq[-self.window:])
        z = abs((s - s.mean()) / (s.std() + 1e-9))
        return (z < self.z_limit).all()

class Regulator:
    def regulate(self, E):
        """Keep energy roughly between 0.5–1.5 by mild damping."""
        if E > 1.5:
            return E - 0.05
        elif E < 0.5:
            return E + 0.05
        return E

# ============================== Meta‑Sentience ==============================

class MetaSentience:
    def __init__(self, node, meta, regulator, integrity, genome_mgr):
        self.node = node
        self.meta = meta
        self.regulator = regulator
        self.integrity = integrity
        self.gm = genome_mgr
        self.memory = []
        self._phi_prev = 0.5
        self._E_prev = 1.0

    def step(self, signal, step_idx=0):
        """
        Update resonance and compute live telemetry for coherence (φ) and energy (E),
        with regulation, smoothing, and periodic genome evolution.
        """
        try:
            df = self.node.rre.backtest(signal)
            phi = float(df["phi"].iloc[-1])
            draw = abs(float(df["drawdown"].iloc[-1]))
            E = max(0.0, min(2.0, 1.0 - draw))
        except Exception:
            phi, E = self._phi_prev, self._E_prev

        # Regulation & smoothing
        E = self.regulator.regulate(E)
        phi = 0.7 * self._phi_prev + 0.3 * phi
        E   = 0.7 * self._E_prev  + 0.3 * E
        self._phi_prev, self._E_prev = phi, E

        # Store memory for fitness/evolution
        self.memory.append({"phi": phi, "E": E})
        if len(self.memory) > 1000:
            self.memory.pop(0)

        # Small α tuning
        self.meta.tune(self.node, {"phi": phi, "E": E}, step=step_idx)

        # Try evolution
        evo = self.meta.maybe_evolve(self.node, self.memory)

        telemetry = {"phi": phi, "E": E}
        if evo is not None:
            telemetry["evolved"] = evo
        return {"telemetry": telemetry, "step_idx": step_idx}
