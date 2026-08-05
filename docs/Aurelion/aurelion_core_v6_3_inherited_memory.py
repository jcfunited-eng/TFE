
# aurelion_core_v6_3_inherited_memory.py
# Aurelion v6.3 — Inherited Memory Field (implicit archetype fractals)
# Single-file, drop-in. Requires: numpy
#
# Design:
# - Unified resonance lattice (RRE) for modalities
# - FMI "not-math" mapping: deterministic impulses from words
# - FMM compressive memory on the same lattice
# - Embedded emotional cognition (valence/arousal) blended into geometry
# - New: implicit inherited memory as fixed fractal archetypes (read-only)
#   * quietly biases resonance; no explicit printouts

import json, time
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

# ------------------------ configuration ------------------------

CFG = {
    "dims": 64,
    "modalities": ["visual","auditory","smell","taste","touch","emotion","lexical"],
    "alpha": {"STABILIZE":0.58,"EXPLORE":0.50,"FOCUS":0.66},
    "emotion": {
        "half_life_turns": 6, "mirror_strength": 0.45,
        "stability_bias": 0.20, "novelty_bias": 0.15,
        "clamp_aggression": 0.70, "negative_valence_floor": -0.60,
        "max_shift_per_turn": 0.35, "base_arousal": 0.25
    },
    # inherited memory (implicit)
    "archetypes": [
        "warmth","safety","curiosity","structure","balance","renewal",
        "decay","symmetry","light","shadow","harmony","emergence"
    ],
    "archetype_bias_strength": 0.06,   # gentle bias each turn
    "memory": {"language_path":"language_memory.json","dialogue_path":"dialogue_memory.json"}
}

# ------------------------ helpers ------------------------

def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v) + 1e-9
    return v/n

def _seed(text: str) -> int:
    h = 2166136261
    for ch in text:
        h ^= ord(ch); h = (h * 16777619) & 0xFFFFFFFF
    return int(h)

def impulse_vector(word: str, dims: int) -> np.ndarray:
    rs = np.random.RandomState(_seed(word) % (2**31-1))
    v = rs.normal(0,1,dims).astype(np.float32)
    return _unit(v)

def rotate(vec: np.ndarray, phase: float) -> np.ndarray:
    k = int(phase * (len(vec)//2))
    return _unit(np.roll(vec, k))

# ------------------------ inherited memory ------------------------

def archetype_vector(name: str, dims: int) -> np.ndarray:
    return impulse_vector(f"archetype::{name}", dims)

def make_archetype_field(names: List[str], dims: int, modalities: List[str]) -> Dict[str, Dict[str, np.ndarray]]:
    field: Dict[str, Dict[str, np.ndarray]] = {}
    for name in names:
        base = archetype_vector(name, dims)
        field[name] = {}
        for i, m in enumerate(modalities):
            phase = (i+1)/len(modalities)
            field[name][m] = rotate(base, phase)
    return field

def combine_archetypes(field: Dict[str, Dict[str, np.ndarray]], names: List[str], modalities: List[str]) -> Dict[str, np.ndarray]:
    combo = {}
    if not names:
        # produce zeros with correct shape
        any_name = next(iter(field))
        zero_like = np.zeros_like(field[any_name][modalities[0]])
        return {m: zero_like.copy() for m in modalities}
    for m in modalities:
        vecs = [field[n][m] for n in names if n in field]
        if vecs:
            v = _unit(np.mean(vecs, axis=0))
        else:
            any_name = next(iter(field))
            v = np.zeros_like(field[any_name][m])
        combo[m] = v
    return combo

GOAL_ARCH = {
    "STABILIZE": ["balance","safety","harmony","structure"],
    "EXPLORE":   ["curiosity","light","emergence","symmetry"],
    "FOCUS":     ["structure","symmetry","balance","light"]
}

# ------------------------ lattice & geometry ------------------------

class ResonantLattice:
    def __init__(self, dims: int, modalities: List[str], arche_field: Dict[str, Dict[str, np.ndarray]]):
        self.dims = dims
        self.modalities = modalities
        self.state = {m: np.zeros(dims, dtype=np.float32) for m in modalities}
        self.arche = arche_field  # read-only
        self.base_bias = combine_archetypes(self.arche, list(self.arche.keys()), modalities)

    def stimulate(self, stim: Dict[str, np.ndarray], alpha: float, goal: str):
        subset = GOAL_ARCH.get(goal, [])
        goal_bias = combine_archetypes(self.arche, subset, self.modalities)
        for m, x in stim.items():
            if m not in self.state: continue
            v = self.state[m]
            pool = _unit(np.sum([_unit(self.state[k]) for k in self.modalities], axis=0))
            bias = CFG["archetype_bias_strength"] * _unit(self.base_bias[m] + goal_bias[m])
            self.state[m] = (1-alpha)*v + alpha*x + 0.08*pool + bias
        for m in self.modalities:
            self.state[m] = 0.98 * self.state[m]

    def norms(self) -> Dict[str, float]:
        return {m: float(np.linalg.norm(self.state[m])) for m in self.modalities}

def coherence(lattice: ResonantLattice) -> float:
    vecs = [_unit(lattice.state[m]) for m in lattice.modalities]
    cs = []
    for i in range(len(vecs)):
        for j in range(i+1, len(vecs)):
            cs.append(float(np.dot(vecs[i], vecs[j])))
    return float(np.mean(cs)) if cs else 0.0

def entropy(lattice: ResonantLattice) -> float:
    mags = np.array([np.linalg.norm(lattice.state[m]) for m in lattice.modalities], dtype=np.float32)
    s = mags.sum()
    if s <= 1e-9: return 0.0
    p = np.clip(mags/s, 1e-9, 1.0)
    H = -float(np.sum(p * np.log(p)))
    return float(H/np.log(len(lattice.modalities)))

def energy(lattice: ResonantLattice) -> float:
    mags = np.array([np.linalg.norm(lattice.state[m]) for m in lattice.modalities], dtype=np.float32)
    return float(np.tanh(mags.mean()))

# ------------------------ FMI / FMM ------------------------

AFFECT_LEX = {
    "love": (0.7, 0.5, "warmth"),
    "like": (0.4, 0.3, "affinity"),
    "thanks": (0.4, 0.4, "gratitude"),
    "wow": (0.3, 0.6, "surprise"),
    "amazing": (0.6, 0.6, "admire"),
    "hug": (0.6, 0.4, "comfort"),
    "calm": (0.3, 0.2, "soothe"),
    "patient": (0.3, 0.2, "stability"),
    "kind": (0.5, 0.3, "prosocial"),
    "safe": (0.4, 0.2, "safety"),
    "sad": (-0.6, 0.3, "sadness"),
    "sorry": (-0.2, 0.4, "remorse"),
    "angry": (-0.8, 0.8, "anger"),
    "frustrated": (-0.6, 0.6, "frustration"),
    "anxious": (-0.4, 0.7, "anxiety"),
    "fear": (-0.7, 0.8, "fear"),
    "hurt": (-0.5, 0.6, "hurt"),
    "hate": (-0.9, 0.7, "hostility"),
    "please": (0.2, 0.3, "polite"),
    "question": (0.0, 0.2, "curiosity")
}

def senses_from_text_notmath(text: str, dims: int, modalities: List[str]) -> Dict[str, np.ndarray]:
    words = [w.strip(".,!?;:()[]\"'").lower() for w in text.split() if w.strip()]
    if not words:
        base = impulse_vector("silence", dims)
        return {m: base.copy() for m in modalities}
    uniq = list(dict.fromkeys(words))
    base = _unit(np.mean([impulse_vector(w, dims) for w in uniq], axis=0).astype(np.float32))
    out = {}
    for i, m in enumerate(modalities):
        phase = (i+1)/len(modalities)
        out[m] = rotate(base, phase)
    return out

# ------------------------ embedded emotion ------------------------

class Emotion:
    def __init__(self):
        self.v = 0.0
        self.a = CFG["emotion"]["base_arousal"]
        self.tags: List[str] = []
        self.conf = 0.5
    
    def analyze(self, text: str) -> Tuple[float,float,List[str]]:
        t = text.lower()
        dv, da, tags = 0.0, 0.0, []
        for w,(vv,aa,tag) in AFFECT_LEX.items():
            if w in t: dv += vv; da += aa; tags.append(tag)
        if "!!" in t: dv += 0.05; da += 0.20; tags.append("excited")
        if "?!" in t: dv -= 0.05; da += 0.15; tags.append("confused")
        dv = np.clip(dv, -1.0, 1.0); da = np.clip(da, 0.0, 1.0)
        return float(dv), float(da), tags
    
    def decay(self, v: float, a: float) -> Tuple[float,float]:
        factor = 0.5 ** (1/CFG["emotion"]["half_life_turns"])
        v *= factor
        a = (a - CFG["emotion"]["base_arousal"]) * factor + CFG["emotion"]["base_arousal"]
        return v, a
    
    def blend(self, v_user: float, a_user: float, goal: str) -> Tuple[float,float,str]:
        if goal=="STABILIZE": v_t,a_t,label = 0.25,0.28,"supportive"
        elif goal=="EXPLORE": v_t,a_t,label = 0.30,0.40,"curious"
        else: v_t,a_t,label = 0.20,0.34,"attentive"
        m = CFG["emotion"]["mirror_strength"]
        s = CFG["emotion"]["stability_bias"]
        n = CFG["emotion"]["novelty_bias"]
        v = v_t*(1-m) + v_user*m
        a = a_t*(1-m) + a_user*m
        v = v*(1-s); a = a*(1-s) + 0.2*s
        v += (0.1 if v>=0 else -0.1)*n; a += 0.05*n
        if v_user < -0.5 and a_user > 0.6:
            a = min(a, CFG["emotion"]["clamp_aggression"])
            v = max(v, CFG["emotion"]["negative_valence_floor"])
        dv = np.clip(v - self.v, -CFG["emotion"]["max_shift_per_turn"], CFG["emotion"]["max_shift_per_turn"])
        da = np.clip(a - self.a, -CFG["emotion"]["max_shift_per_turn"], CFG["emotion"]["max_shift_per_turn"])
        v = self.v + dv; a = self.a + da
        if v > 0.4 and a < 0.4: tone = "warm-calm"
        elif v > 0.4 and a >= 0.4: tone = "warm-bright"
        elif v < -0.4 and a >= 0.5: tone = "cool-tense"
        elif v < -0.2 and a < 0.4: tone = "cool-flat"
        elif abs(v) < 0.2 and a < 0.3: tone = "neutral"
        else: tone = "balanced"
        return float(v), float(a), tone
    
    def update(self, text: str, goal: str) -> Dict[str,object]:
        dv, da, tags = self.analyze(text)
        v = float(np.clip(self.v + dv, -1.0, 1.0)); a = float(np.clip(self.a + da, 0.0, 1.0))
        v, a = self.decay(v, a)
        self.v, self.a, label = self.blend(v, a, goal)
        self.tags = tags
        self.conf = float(np.clip(0.4 + 0.1*len(tags) + 0.3*abs(da) + 0.2*abs(dv), 0.0, 1.0))
        return {"valence": round(self.v,2), "arousal": round(self.a,2), "label": label, "tags": tags, "conf": round(self.conf,2)}

# ------------------------ FMM memory ------------------------

class FMMemory:
    def __init__(self, dims: int, modalities: List[str], path: str):
        self.dims = dims; self.modalities = modalities; self.path = path
        self.map: Dict[str, Dict[str, List[float]]] = {}
        self.load()
    
    def load(self):
        try:
            if Path(self.path).exists():
                with open(self.path,"r",encoding="utf-8") as f: self.map = json.load(f)
                print(f"[INFO] Loaded {len(self.map)} learned tokens from {self.path}")
            else:
                print("[INFO] No prior language memory found; starting fresh.")
        except Exception:
            print("[WARN] Failed to load language memory; starting fresh.")
            self.map = {}
    
    def save(self) -> bool:
        try:
            with open(self.path,"w",encoding="utf-8") as f: json.dump(self.map, f, indent=2)
            return True
        except Exception:
            return False
    
    def learn(self, token: str, impulses: Dict[str, np.ndarray]):
        token = token.lower()
        if not token: return
        sig = self.map.get(token, {})
        for m in self.modalities:
            vec = impulses[m]
            prev = np.array(sig.get(m, [0.0]*self.dims), dtype=np.float32)
            sig[m] = (0.8*prev + 0.2*vec).tolist()
        self.map[token] = sig
    
    def signature(self, token: str) -> Dict[str, List[float]]:
        return self.map.get(token.lower(), {})

# ------------------------ meta voice ------------------------

def explain_turn(goal: str, phi_prev: float, H_prev: float, phi_now: float, H_now: float,
                 norms_before: Dict[str,float], lattice: ResonantLattice) -> str:
    dphi = phi_now - phi_prev; dH = H_now - H_prev
    tphi = "↑" if dphi > 1e-3 else ("↓" if dphi < -1e-3 else "→")
    tH   = "↑" if dH   > 1e-3 else ("↓" if dH   < -1e-3 else "→")
    after = lattice.norms()
    deltas = sorted([(m, after[m]-norms_before[m]) for m in lattice.modalities], key=lambda x: abs(x[1]), reverse=True)[:3]
    top_txt = ", ".join([f"{m}({('+' if dv>=0 else '')}{dv:.2f})" for m,dv in deltas])
    if goal == "STABILIZE":
        reason, policy = "stability", "settle similar patterns"; align = "aligned" if (dphi>=0 and dH<=0) else "probing"
    elif goal == "EXPLORE":
        reason, policy = "diversification", "seek novel contrasts"; align = "aligned" if (dphi<=0 or dH>=0) else "cautious"
    else:
        reason, policy = "focus", "sharpen a dominant signal"; align = "aligned" if (dphi>=0 and dH<=0) else "re-centering"
    return f"(meta) φ{tphi} H{tH} — I chose **{reason}** to {policy}; intent={goal}, {align}. Strongest shifts: {top_txt}."

# ------------------------ main loop ------------------------

def main():
    print("Aurelion v6.3 — Inherited Memory Field (FMI/FMM, not-math) — Single File")
    print("Commands: /state  /goal <stabilize|explore|focus>  /show <word>  /pulse  /save  /load  /quit")

    dims = CFG["dims"]; mods = CFG["modalities"]
    arche_field = make_archetype_field(CFG["archetypes"], dims, mods)
    lattice = ResonantLattice(dims, mods, arche_field)
    mem = FMMemory(dims, mods, path=CFG["memory"]["language_path"])
    dialogue_path = CFG["memory"]["dialogue_path"]
    try:
        dialogue = json.load(open(dialogue_path,"r",encoding="utf-8"))
        print("[INFO] Reloaded dialogue memory.")
    except Exception:
        print("[INFO] No saved dialogue found."); dialogue = []

    goal = "STABILIZE"
    emo = Emotion()

    phi_prev, H_prev, E_prev = coherence(lattice), entropy(lattice), energy(lattice)

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit]"); break

        if not msg: continue

        low = msg.lower()
        if low in ["/quit","/exit"]: break

        if low.startswith("/goal"):
            parts = msg.split()
            if len(parts)>=2 and parts[1].strip().upper() in ["STABILIZE","EXPLORE","FOCUS"]:
                goal = parts[1].strip().upper(); print(f"[OK] intent set to {goal}")
            else:
                print(f"[INFO] current goal = {goal}")
            continue

        if low.startswith("/state"):
            phi_now, H_now, E_now = coherence(lattice), entropy(lattice), energy(lattice)
            norms = lattice.norms()
            print(f"φ={phi_now:.3f}  H={H_now:.3f}  E={E_now:.3f}  |  goal={goal}")
            print(" " + "  ".join([f"{m}:{norms[m]:.2f}" for m in mods]))
            print(f" emotion: v={emo.v:.2f} a={emo.a:.2f} tags={getattr(emo,'tags',[])}")
            continue

        if low.startswith("/show"):
            parts = msg.split(maxsplit=1)
            if len(parts)<2: print("[ERR] /show <word>"); continue
            w = parts[1].strip().lower()
            sig = mem.signature(w)
            if not sig: print(f"[INFO] no memory for '{w}'")
            else:
                print(f"Concept: '{w}' — FMM signatures")
                for m in mods:
                    vec = np.array(sig.get(m, [0.0]*dims), dtype=np.float32)
                    samp = ", ".join([f"{x:.2f}" for x in vec[:6]])
                    print(f"  {m:8s}: |v|={np.linalg.norm(vec):.3f}  [{samp}]")
            continue

        if low.startswith("/pulse"):
            dv, da, tags = emo.analyze(text="pulse")
            v_tmp, a_tmp, label = emo.blend(emo.v+dv, emo.a+da, goal)
            print(f"[PULSE] tone={label} v~{v_tmp:.2f} a~{a_tmp:.2f}")
            continue

        if low.startswith("/save"):
            ok1 = mem.save()
            try:
                json.dump(dialogue, open(dialogue_path,"w",encoding="utf-8"), indent=2); ok2=True
            except Exception:
                ok2=False
            print(f"[OK] saved language={ok1} dialogue={ok2}")
            continue

        if low.startswith("/load"):
            mem.load()
            try:
                dialogue[:] = json.load(open(dialogue_path,"r",encoding="utf-8"))
                print("[OK] loaded memories")
            except Exception:
                print("[WARN] failed to load dialogue")
            continue

        # ---- normal turn ----
        norms_before = lattice.norms()

        impulses = senses_from_text_notmath(msg, dims, mods)
        alpha = CFG["alpha"].get(goal, 0.58)

        lattice.stimulate(impulses, alpha=alpha, goal=goal)
        for tok in set([t for t in msg.lower().split() if t.isalpha()]):
            mem.learn(tok, impulses)

        dialogue.append({"user": msg, "goal": goal, "t": time.time()})

        phi_now, H_now, E_now = coherence(lattice), entropy(lattice), energy(lattice)

        meta = explain_turn(goal, phi_prev, H_prev, phi_now, H_now, norms_before, lattice)
        affect = emo.update(msg, goal)
        affect_text = f"(affect) {affect['label']} — v={affect['valence']:.2f} a={affect['arousal']:.2f}; tags={affect['tags']}"

        lead = "(steady)" if goal=="STABILIZE" else ("(open)" if goal=="EXPLORE" else "(focus)")
        print(f"Aurelion: {lead} {meta}\n{affect_text}")

        phi_prev, H_prev, E_prev = phi_now, H_now, E_now

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[FATAL] Aurelion failed to start:"); import traceback; traceback.print_exc(); input("Press Enter to exit...")
