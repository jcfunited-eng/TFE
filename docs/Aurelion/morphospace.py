
# morphospace.py
from __future__ import annotations
import math, json, os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import numpy as np
rng = np.random.default_rng(42)

def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v) + 1e-9
    return v / n

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / ((np.linalg.norm(a) + 1e-9)*(np.linalg.norm(b)+1e-9)))

@dataclass
class MosaicNode:
    id: int
    v: np.ndarray
    goal: np.ndarray
    energy: float = 0.5
    age: int = 0
    domain: str = "associator"
    neighbors: List[int] = field(default_factory=list)

    def tick(self):
        self.age += 1
        self.energy = max(0.0, self.energy - 0.002)

class Morphospace:
    def __init__(self, dim: int=128, grid: Tuple[int,int]=(8,8), seed: int=42):
        self.dim = dim
        self.W, self.H = grid
        self.rng = np.random.default_rng(seed)
        self.nodes: Dict[int, MosaicNode] = {}
        self.regions: Dict[int,str] = {}
        self.coupling = None
        self.step_n = 0
        self.history = {"phi":[], "energy":[], "entropy":[]}
        self._build_grid()
        self._seed_starter_memory()

    def _build_grid(self):
        for y in range(self.H):
            for x in range(self.W):
                nid = y*self.W + x
                v = self.rng.normal(0, 1.0, size=(self.dim,))
                v = _unit(v)
                goal = self.rng.normal(0, 1.0, size=(self.dim,))
                goal = _unit(goal)
                if x < self.W//2 and y < self.H//2:  region = "core"
                elif x >= self.W//2 and y < self.H//2: region = "interface"
                elif x < self.W//2 and y >= self.H//2: region = "regulator"
                else: region = "associator"
                node = MosaicNode(id=nid, v=v, goal=goal, energy=0.5, age=0, domain=region)
                self.nodes[nid] = node
                self.regions[nid] = region

        for y in range(self.H):
            for x in range(self.W):
                i = y*self.W + x
                neigh = []
                if x>0: neigh.append(y*self.W + (x-1))
                if x<self.W-1: neigh.append(y*self.W + (x+1))
                if y>0: neigh.append((y-1)*self.W + x)
                if y<self.H-1: neigh.append((y+1)*self.W + x)
                self.nodes[i].neighbors = neigh

        N = self.W*self.H
        C = np.zeros((N,N), dtype=float)
        for i in range(N):
            for j in self.nodes[i].neighbors:
                base = 0.20
                ri, rj = self.regions[i], self.regions[j]
                if ri == rj: base += 0.15
                if (ri, rj) in [("core","interface"),("interface","core")]:
                    base += 0.05
                if (ri, rj) in [("interface","associator"),("associator","interface")]:
                    base += 0.06
                if (ri, rj) in [("regulator","associator"),("associator","regulator")]:
                    base += 0.04
                if (ri, rj) in [("core","regulator"),("regulator","core")]:
                    base += 0.03
                C[i,j] = base
        self.coupling = C

    def _seed_starter_memory(self):
        seeds = {
            "validation_quality": ["validation","quality","iq","oq","pq","requirements","risk","assurance"],
            "coherence_energy": ["resonance","coherence","energy","entropy","stability","growth","goal"],
            "space_mission": ["mission","trajectory","lander","surface","navigation","systems"],
            "weather_dynamics": ["front","pressure","storm","wind","temperature","humidity"]
        }
        def word_vec(w: str) -> np.ndarray:
            h = abs(hash(w)) % (10**9)
            v = np.random.default_rng(h).normal(0, 1.0, size=(self.dim,))
            return _unit(v)

        assoc_nodes = [i for i,r in self.regions.items() if r=="associator"]
        for k, words in seeds.items():
            if not assoc_nodes: break
            nid = assoc_nodes.pop(0)
            vec = np.zeros((self.dim,), dtype=float)
            for w in words:
                vec += word_vec(w)
            self.nodes[nid].v = _unit(vec)
            self.nodes[nid].goal = _unit(0.5*self.nodes[nid].goal + 0.5*vec)
            self.nodes[nid].energy = 0.62

    def phi(self) -> float:
        sims = []
        for i, n in self.nodes.items():
            if not n.neighbors: continue
            m = np.mean([self.nodes[j].v for j in n.neighbors], axis=0)
            sims.append(cosine(n.v, m))
        return float(np.clip(np.mean(sims) if sims else 0.0, 0.0, 1.0))

    def entropy(self) -> float:
        X = np.stack([n.v for n in self.nodes.values()], axis=0)
        try:
            s = np.linalg.svd(X, compute_uv=False)
            p = s / (np.sum(s)+1e-9)
            H = -np.sum(p * np.log(p+1e-12))
            H = H / np.log(len(s)+1e-9)
            return float(np.clip(H, 0.0, 1.0))
        except Exception:
            return 0.0

    def energy_mean(self) -> float:
        return float(np.mean([n.energy for n in self.nodes.values()]))

    def step(self,
             alpha_align: float=0.12,
             beta_goal: float=0.06,
             gamma_plastic: float=0.05,
             sigma_noise: float=0.01,
             theta_energy_gain: float=0.04,
             stimulus: Optional[np.ndarray]=None):
        region_align = {"core": 1.10, "interface": 0.95, "regulator": 1.00, "associator": 1.05}
        region_goal  = {"core": 0.90, "interface": 0.90, "regulator": 0.80, "associator": 1.15}
        region_noise = {"core": 0.8, "interface": 1.1, "regulator": 0.6, "associator": 1.0}

        newV = {}
        for i, n in self.nodes.items():
            neigh = n.neighbors
            m = np.mean([self.nodes[j].v for j in neigh], axis=0) if neigh else np.zeros((self.dim,))
            a = alpha_align * region_align[n.domain]
            b = beta_goal * region_goal[n.domain]
            g = gamma_plastic
            z = sigma_noise * region_noise[n.domain]

            v = n.v + a * m + b * n.goal
            n.goal = _unit((1.0-g)*n.goal + g*m)
            if stimulus is not None and n.domain in ("interface","associator"):
                v += 0.08 * stimulus
            field = np.zeros((self.dim,))
            for j in neigh:
                field += self.coupling[i,j] * self.nodes[j].v
            v += 0.02 * field
            v += z * np.random.normal(0,1.0,size=(self.dim,))
            newV[i] = _unit(v)

        for i, n in self.nodes.items():
            n.v = newV[i]
            n.tick()

        phi = self.phi()
        H = self.entropy()
        E = self.energy_mean()
        for i, n in self.nodes.items():
            if self.regions[i] == "core":
                n.energy = min(1.0, n.energy + theta_energy_gain*(phi))
            elif self.regions[i] == "regulator":
                n.energy = min(1.0, n.energy + 0.5*theta_energy_gain*(1.0 - H))

        self.step_n += 1
        self.history["phi"].append(phi)
        self.history["entropy"].append(H)
        self.history["energy"].append(E)
        return {"phi":phi, "entropy":H, "energy":E}
