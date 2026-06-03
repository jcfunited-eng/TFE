
# RRE Core v2.5 — phi/entropy, memory tiers Λα, resonance utility U, intent selection
from collections import deque
import numpy as np

def safe_array(x):
    a = np.asarray(x, dtype=float).ravel()
    if a.size == 0:
        return np.zeros(1)
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    return a

def coherence_phi(x):
    x = safe_array(x)
    if x.size < 3:
        return 0.0
    m = np.convolve(x, np.ones(5)/5.0, mode="same")
    resid = x - m
    num = np.mean(resid**2)
    den = np.mean((x - np.mean(x))**2) + 1e-9
    phi = 1.0 - (num/den)
    return float(np.clip(phi, 0.0, 1.0))

def spectral_entropy(x, bins=32):
    x = safe_array(x)
    if x.size < 8:
        return 1.0
    f = np.fft.rfft(x - np.mean(x))
    p = np.abs(f)**2
    if p.sum() == 0:
        return 1.0
    p = p / p.sum()
    if p.size > bins:
        step = int(np.floor(p.size / bins))
        p = p[:bins*step].reshape(bins, step).mean(axis=1)
    elif p.size < bins:
        p = np.pad(p, (0, bins - p.size))
    p = p / (p.sum() + 1e-12)
    H = -np.sum(p * np.log2(p + 1e-12))
    return float(np.clip(H / np.log2(bins), 0.0, 1.0))

class RRERingMemory:
    def __init__(self, cap_short=256, cap_mid=2048, cap_long=8192, ds_mid=4, ds_long=16):
        self.S = deque(maxlen=cap_short)
        self.M = deque(maxlen=cap_mid)
        self.L = deque(maxlen=cap_long)
        self._ds_m = ds_mid
        self._ds_l = ds_long
        self._t = 0
    def push(self, value):
        self.S.append(value)
        if self._t % self._ds_m == 0:
            self.M.append(value)
        if self._t % self._ds_l == 0:
            self.L.append(value)
        self._t += 1
    def array_S(self): import numpy as np; return np.asarray(self.S, dtype=float)
    def array_M(self): import numpy as np; return np.asarray(self.M, dtype=float)
    def array_L(self): import numpy as np; return np.asarray(self.L, dtype=float)

class RRE:
    def __init__(self, name, w_phi=(0.6,0.3,0.1), w_ent=0.5):
        self.name = name
        self.mem_phi = RRERingMemory()
        self.mem_ent = RRERingMemory()
        self.w_phi = w_phi
        self.w_ent = w_ent
        self.last_action = None
    def ingest(self, signal):
        x = safe_array(signal)
        phi = coherence_phi(x)
        H = spectral_entropy(x)
        self.mem_phi.push(phi)
        self.mem_ent.push(H)
        return phi, H
    def tiers(self):
        def _agg(arr):
            if arr.size < 3: return 0.0
            return float(np.clip(np.mean(arr), 0.0, 1.0))
        phiS, phiM, phiL = _agg(self.mem_phi.array_S()), _agg(self.mem_phi.array_M()), _agg(self.mem_phi.array_L())
        HS, HM, HL      = _agg(self.mem_ent.array_S()), _agg(self.mem_ent.array_M()), _agg(self.mem_ent.array_L())
        return (phiS, phiM, phiL), (HS, HM, HL)
    def utility(self):
        (phiS, phiM, phiL), (HS, HM, HL) = self.tiers()
        phi_term = self.w_phi[0]*phiS + self.w_phi[1]*phiM + self.w_phi[2]*phiL
        H_term   = (HS + HM*0.5 + HL*0.25)/1.75
        U = phi_term - self.w_ent*H_term
        return float(U), dict(phiS=phiS, phiM=phiM, phiL=phiL, HS=HS, HM=HM, HL=HL)
    def select_intent(self):
        (phiS, phiM, phiL), (HS, HM, HL) = self.tiers()
        T = {
            "STABLE":  dict(phiS=0.8, phiM=0.8, phiL=0.7, H=0.2),
            "EXPLORE": dict(phiS=0.5, phiM=0.6, phiL=0.6, H=0.6),
            "AVOID":   dict(phiS=0.3, phiM=0.4, phiL=0.5, H=0.8),
        }
        scores = {}
        for k, t in T.items():
            d = (abs(phiS - t["phiS"]) + abs(phiM - t["phiM"]) + abs(phiL - t["phiL"]) + abs(((HS+HM+HL)/3.0) - t["H"])) / 4.0
            scores[k] = 1.0 - d
        intent = max(scores, key=scores.get)
        return intent, scores
    def propose_action(self, intent):
        if intent == "STABLE":
            action = {"op": "smooth_up", "amount": 0.15, "note": "Increase smoothing to reduce entropy."}
        elif intent == "EXPLORE":
            action = {"op": "inject_probe", "amount": 0.1, "note": "Inject small perturbation to test sensitivity."}
        else:
            action = {"op": "suppress_outliers", "amount": 0.2, "note": "Clamp outliers; protect homeostasis."}
        self.last_action = action
        return action
