
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from rre_model import RRE, RREConfig
except Exception:
    @dataclass
    class RREConfig:
        ema_windows: List[int] = field(default_factory=lambda: [5, 20, 60])
        vol_lookback: int = 20
        vol_target: float = 0.01
        alpha: float = 0.6
        resonance_threshold: float = 0.2
        allow_short: bool = False
        max_drawdown_brake: float = 0.2
        default_costs_bps: float = 1.0
    class RRE:
        def __init__(self, config: RREConfig):
            self.cfg = config
        def _ema(self, arr, span):
            return pd.Series(arr).ewm(span=span, adjust=False).mean().to_numpy()
        def _transform(self, s: pd.Series) -> pd.DataFrame:
            df = pd.DataFrame(index=s.index.copy())
            df['price'] = s.astype(float)
            df['ret'] = df['price'].pct_change().fillna(0.0)
            for w in self.cfg.ema_windows:
                ema = self._ema(df['price'].to_numpy(), span=w)
                df[f'ema_{w}'] = ema
                df[f'slope_{w}'] = pd.Series(ema, index=df.index).diff().fillna(0.0)
            return df
        def _relational_coherence(self, df: pd.DataFrame) -> pd.Series:
            S = np.sign(df[[f'slope_{w}' for w in self.cfg.ema_windows]].to_numpy())
            pos = (S > 0).sum(axis=1); neg = (S < 0).sum(axis=1)
            nonzero = np.maximum(1, (S != 0).sum(axis=1))
            raw = (pos - neg) / nonzero
            all_agree = ((pos == nonzero) | (neg == nonzero)) & (nonzero > 1)
            raw = np.clip(raw + 0.15 * np.sign(raw) * all_agree.astype(float), -1.0, 1.0)
            return pd.Series(raw, index=df.index, name='phi_raw')
        def _feedback_memory(self, phi_raw: pd.Series) -> pd.Series:
            a = float(self.cfg.alpha)
            out = np.zeros_like(phi_raw.to_numpy(), dtype=float); prev = 0.0
            for i, v in enumerate(phi_raw.to_numpy()):
                out[i] = a * v + (1.0 - a) * prev; prev = out[i]
            return pd.Series(out, index=phi_raw.index, name='phi')
        def infer_phi_series(self, s: pd.Series) -> pd.DataFrame:
            df = self._transform(s); phi_raw = self._relational_coherence(df); phi = self._feedback_memory(phi_raw)
            return pd.DataFrame({'phi_raw': phi_raw, 'phi': phi}, index=df.index)

@dataclass
class EnergyEconomy:
    E: float = 1.0
    baseline: float = 0.0
    action_cost: float = 0.005
    growth_k: float = 0.2
    min_E: float = 0.0
    max_E: float = 5.0
    def step(self, dphi: float, action_intensity: float):
        cost = self.action_cost * abs(action_intensity)
        self.E += (dphi - self.baseline) - cost
        self.E = float(np.clip(self.E, self.min_E, self.max_E))
        G = max(0.0, self.E - 1.0) * self.growth_k
        return self.E, G

@dataclass
class EmotionState:
    love: float = 0.0
    passion: float = 0.0
    curiosity: float = 0.0
    fear: float = 0.0
    greed: float = 0.0
    empathy: float = 0.0

class EmotionEngine:
    def __init__(self, rng: Optional[np.random.RandomState] = None):
        self.rng = np.random.RandomState(42) if rng is None else rng
    def update(self, phi: float, dphi: float, E: float, peer_phi: Optional[float] = None) -> EmotionState:
        st = EmotionState()
        st.love      = max(0.0,  0.3 * phi)
        st.passion   = max(0.0,  abs(dphi))
        st.curiosity = float(np.clip(self.rng.normal(0, 0.05), -0.1, 0.1))
        st.fear      = max(0.0, -1.0 * min(0.0, dphi))
        st.greed     = max(0.0,  E - 1.0)
        st.empathy   = max(0.0, 0.3 * ((phi + (peer_phi if peer_phi is not None else phi)) / 2.0))
        return st

@dataclass
class GoalAttractor:
    name: str
    target_phi: float
    risk_aversion: float = 0.0
    exploration_bias: float = 0.0

class IntentResolver:
    def __init__(self, goals: List[GoalAttractor]):
        self.goals = goals
    def select(self, phi: float, E: float, emo: EmotionState) -> GoalAttractor:
        best, best_score = None, -1e9
        for g in self.goals:
            closeness = -abs(phi - g.target_phi)
            drive = emo.passion * (abs(g.target_phi - phi))
            safety = -emo.fear * g.risk_aversion + emo.curiosity * g.exploration_bias
            growth = emo.greed * g.target_phi
            score = closeness + 0.5*drive + 0.3*safety + 0.2*growth
            if score > best_score:
                best, best_score = g, score
        return best

class RRENode:
    def __init__(self, name: str, rre: Optional[RRE] = None, cfg: Optional[RREConfig] = None):
        self.name = name
        self.rre = rre if rre is not None else RRE(cfg if cfg is not None else RREConfig())
        self.energy = EnergyEconomy()
        self.emo_engine = EmotionEngine()
        self.last_phi = 0.0
    def step(self, signal: pd.Series, target: GoalAttractor, peer_phi: Optional[float] = None) -> Dict:
        phidf = self.rre.infer_phi_series(signal)
        phi = float(phidf['phi'].iloc[-1])
        dphi = phi - self.last_phi
        E, G = self.energy.step(dphi=dphi, action_intensity=abs(dphi))
        emo = self.emo_engine.update(phi=phi, dphi=dphi, E=E, peer_phi=peer_phi)
        alpha_mod = float(np.clip(0.6 + 0.2*emo.passion - 0.2*emo.fear, 0.2, 0.95))
        threshold_mod = float(np.clip(0.2 + 0.15*emo.fear - 0.1*emo.curiosity, 0.05, 0.6))
        self.last_phi = phi
        return dict(name=self.name, phi=phi, dphi=dphi, E=E, G=G,
                    emotions=emo.__dict__, alpha_mod=alpha_mod, threshold_mod=threshold_mod, goal=target.name)

class RRECluster:
    def __init__(self, nodes: List[RRENode], empathy_weight: float = 0.3):
        self.nodes = nodes
        self.empathy_weight = empathy_weight
    def step(self, signals: List[pd.Series], goals: List[GoalAttractor]) -> List[Dict]:
        peer_phis = []
        for n, sig in zip(self.nodes, signals):
            phidf = n.rre.infer_phi_series(sig)
            peer_phis.append(float(phidf['phi'].iloc[-1]))
        avg_phi = float(np.mean(peer_phis)) if peer_phis else 0.0
        out = []
        resolver = IntentResolver(goals)
        for i, node in enumerate(self.nodes):
            phidf = node.rre.infer_phi_series(signals[i])
            phi_i = float(phidf['phi'].iloc[-1])
            emo_i = node.emo_engine.update(phi=phi_i, dphi=phi_i-node.last_phi, E=node.energy.E, peer_phi=avg_phi)
            goal = resolver.select(phi=phi_i, E=node.energy.E, emo=emo_i)
            blended_peer_phi = (1 - self.empathy_weight) * phi_i + self.empathy_weight * avg_phi
            res = node.step(signal=signals[i], target=goal, peer_phi=blended_peer_phi)
            out.append(res)
        return out

def synth_signal(n=300, seed=7, regime_shifts: int = 3) -> pd.Series:
    rng = np.random.RandomState(seed)
    x = 100.0
    arr = []
    mu = 0.0; sigma = 0.01
    for t in range(n):
        if regime_shifts and t % (n // max(1, regime_shifts)) == 0:
            mu = rng.uniform(-0.001, 0.001)
            sigma = rng.uniform(0.003, 0.02)
        x *= (1.0 + rng.normal(mu, sigma))
        arr.append(x)
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.Series(arr, index=idx, name="price")

def run_demo(json_out: Optional[str] = None) -> List[Dict]:
    goals = [
        GoalAttractor("STABILIZE", target_phi=0.6, risk_aversion=0.7, exploration_bias=0.1),
        GoalAttractor("EXPLORE",   target_phi=0.3, risk_aversion=0.1, exploration_bias=0.8),
        GoalAttractor("GROW",      target_phi=0.9, risk_aversion=0.3, exploration_bias=0.4),
        GoalAttractor("PROTECT",   target_phi=0.5, risk_aversion=0.9, exploration_bias=0.0),
    ]
    nodes = [RRENode("A"), RRENode("B")]
    cluster = RRECluster(nodes, empathy_weight=0.35)
    sigA = synth_signal(n=300, seed=11, regime_shifts=4)
    sigB = synth_signal(n=300, seed=22, regime_shifts=5)
    res = cluster.step([sigA, sigB], goals)
    if json_out:
        import json
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
    return res

if __name__ == "__main__":
    out = run_demo()
    print(out)
