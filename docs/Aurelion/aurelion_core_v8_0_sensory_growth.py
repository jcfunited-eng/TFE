
# aurelion_core_v8_0_sensory_growth.py
# Aurelion v8.0 — Sensory Growth Core
import json, time, random, csv, wave, struct, math, os, sys, threading
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

_TTS = None
def _init_tts():
    global _TTS
    try:
        import pyttsx3
        _TTS = pyttsx3.init()
    except Exception:
        _TTS = None

def _say(text: str, speak_on: bool):
    if not speak_on:
        return
    if _TTS is None:
        print(f"[speak] {text}")
        return
    try:
        _TTS.say(text); _TTS.runAndWait()
    except Exception:
        print(f"[speak] {text}")

CFG = {
    "dims": 96,
    "modalities": ["visual","auditory","smell","taste","touch","emotion","lexical"],
    "alpha": {"STABILIZE":0.60,"EXPLORE":0.52,"FOCUS":0.68},
    "emotion": {"half_life_turns": 6, "mirror_strength": 0.45, "stability_bias": 0.20, "novelty_bias": 0.15,
                "clamp_aggression": 0.70, "negative_valence_floor": -0.60, "max_shift_per_turn": 0.35, "base_arousal": 0.24},
    "archetypes": ["warmth","safety","curiosity","structure","balance","renewal","symmetry","light","shadow","harmony","emergence"],
    "archetype_bias_strength": 0.06,
    "memory": {"language_path":"language_memory.json","dialogue_path":"dialogue_memory.json","assoc_path":"associations_v8.json"},
    "curiosity": {"entropy_thresh":0.36, "coherence_thresh":0.05},
    "grow": {"interval_min": 2.0, "interval_max": 15.0, "batch_size": 3},
    "learn": {"base_rate": 0.22, "novelty_boost": 0.18, "stability_boost": 0.08}
}

MODES = {
    "CALM": {"emotion_base_arousal":0.22, "curiosity_prob":0.45, "archetype_bias":0.05},
    "ACTIVE": {"emotion_base_arousal":0.34, "curiosity_prob":0.70, "archetype_bias":0.07},
    "EXPERIMENTAL": {"emotion_base_arousal":0.40, "curiosity_prob":0.80, "archetype_bias":0.09}
}

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

class ResonantLattice:
    def __init__(self, dims: int, modalities: List[str], arche_field: Dict[str, Dict[str, np.ndarray]], ar_bias: float):
        self.dims = dims
        self.modalities = modalities
        self.state = {m: np.zeros(dims, dtype=np.float32) for m in modalities}
        self.arche = arche_field
        self.base_bias = combine_archetypes(self.arche, list(self.arche.keys()), modalities)
        self.ar_bias = ar_bias

    def set_archetype_bias(self, val: float):
        self.ar_bias = float(val)

    def stimulate(self, stim: Dict[str, np.ndarray], alpha: float, goal: str):
        subset = GOAL_ARCH.get(goal, [])
        goal_bias = combine_archetypes(self.arche, subset, self.modalities)
        for m, x in stim.items():
            if m not in self.state: continue
            v = self.state[m]
            pool = _unit(np.sum([_unit(self.state[k]) for k in self.modalities], axis=0))
            bias = self.ar_bias * _unit(self.base_bias[m] + goal_bias[m])
            self.state[m] = (1-alpha)*v + alpha*x + 0.08*pool + bias
        for m in self.modalities:
            self.state[m] = 0.985 * self.state[m]

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

class Emotion:
    def __init__(self, base_arousal: float):
        self.v = 0.0
        self.a = base_arousal
        self.tags: List[str] = []
        self.conf = 0.5
        self.base_arousal = base_arousal
    
    def set_base_arousal(self, a0: float):
        self.base_arousal = float(a0)
    
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
        a = (a - self.base_arousal) * factor + self.base_arousal
        return v, a
    
    def blend(self, v_user: float, a_user: float, goal: str) -> Tuple[float,float,str]:
        if goal=="STABILIZE": v_t,a_t,label = 0.25,0.26,"supportive"
        elif goal=="EXPLORE": v_t,a_t,label = 0.30,0.38,"curious"
        else: v_t,a_t,label = 0.20,0.32,"attentive"
        m = 0.45; s = 0.20; n = 0.15
        v = v_t*(1-m) + v_user*m
        a = a_t*(1-m) + a_user*m
        v = v*(1-s); a = a*(1-s) + 0.2*s
        v += (0.1 if v>=0 else -0.1)*n; a += 0.05*n
        if v_user < -0.5 and a_user > 0.6:
            a = min(a, 0.70)
            v = max(v, -0.60)
        dv = np.clip(v - self.v, -0.35, 0.35)
        da = np.clip(a - self.a, -0.35, 0.35)
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
    
    def learn(self, token: str, impulses: Dict[str, np.ndarray], rate: float=0.2):
        token = token.lower()
        if not token:
            return
        sig = self.map.get(token, {})
        for m in self.modalities:
            vec = impulses[m]
            prev = np.array(sig.get(m, [0.0]*self.dims), dtype=np.float32)
            sig[m] = ((1-rate)*prev + rate*vec).tolist()
        self.map[token] = sig
    
    def signature(self, token: str) -> Dict[str, List[float]]:
        return self.map.get(token.lower(), {})

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

VIS_LABELS = ["soft-light","soft-dark","bright-stripes","circle-glow","horizon-gradient"]
SND_LABELS = ["low-tone","mid-tone","high-tone","chord-soft","noise-soft"]
PHRASES = [
    "the light feels gentle and warm",
    "a calm breeze and soft shadow",
    "bright lines hum quietly",
    "a low tone under a soft glow",
    "warm hands hold a smooth cup",
    "cool air and soft fabric",
    "quiet harmony and safe space",
    "curiosity rises like a small light",
    "I feel steady and patient",
    "a bright spark and gentle touch"
]

class Assoc:
    def __init__(self, path: str):
        self.path = path
        self.W: Dict[Tuple[str,str], float] = {}
        self.load()
    def key(self, a: str, b: str) -> Tuple[str,str]:
        return tuple(sorted([a,b]))
    def bump(self, a: str, b: str, w: float=0.05):
        if a==b: return
        k = self.key(a,b)
        self.W[k] = float(np.clip(self.W.get(k,0.0) + w, 0.0, 10.0))
    def top(self, n=12):
        items = sorted(self.W.items(), key=lambda kv: kv[1], reverse=True)[:n]
        return items
    def save(self):
        try:
            with open(self.path,"w",encoding="utf-8") as f:
                json.dump({f"{a}||{b}":w for (a,b),w in self.W.items()}, f, indent=2)
            return True
        except Exception:
            return False
    def load(self):
        try:
            if Path(self.path).exists():
                raw = json.load(open(self.path,"r",encoding="utf-8"))
                self.W = {}
                for k,v in raw.items():
                    a,b = k.split("||",1)
                    self.W[(a,b)] = float(v)
                print(f"[INFO] Loaded {len(self.W)} associations from {self.path}")
            else:
                print("[INFO] No prior associations; starting fresh.")
        except Exception:
            print("[WARN] Failed to load associations; starting fresh.")
            self.W = {}

def fuse_impulses(visual_lbl: str, sound_lbl: str, phrase: str, dims: int, modalities: List[str]) -> Dict[str,np.ndarray]:
    v_base = impulse_vector(visual_lbl, dims)
    s_base = impulse_vector(sound_lbl, dims)
    w_base = impulse_vector(phrase.lower(), dims)
    base = _unit(v_base*0.38 + s_base*0.32 + w_base*0.30)
    out = {}
    for i, m in enumerate(modalities):
        phase = (i+1)/len(modalities)
        out[m] = rotate(base, phase)
    return out

class Growth(threading.Thread):
    def __init__(self, lattice, mem, assoc: Assoc, emo, dims: int, modalities: List[str], goal_ref, speak_ref):
        super().__init__(daemon=True)
        self.lat = lattice; self.mem = mem; self.assoc = assoc; self.emo = emo
        self.dims = dims; self.mods = modalities; self.goal_ref = goal_ref; self.speak_ref = speak_ref
        self._stop = threading.Event()
        self.steps = 0
        self.last_interval = CFG["grow"]["interval_max"]
        self.learned = 0
        self.novel_gain = 0.0
    def stop(self): self._stop.set()
    def run(self):
        while not self._stop.is_set():
            batch = []
            for _ in range(CFG["grow"]["batch_size"]):
                v = random.choice(VIS_LABELS)
                s = random.choice(SND_LABELS)
                p = random.choice(PHRASES)
                batch.append((v,s,p))
            novelty_measure = 0.0
            for (vl,sl,ph) in batch:
                stim = fuse_impulses(vl, sl, ph, self.dims, self.mods)
                alpha = CFG["alpha"].get(self.goal_ref(), 0.60)
                self.lat.stimulate(stim, alpha=alpha, goal=self.goal_ref())
                H = entropy(self.lat)
                novelty_measure += H
                rate = CFG["learn"]["base_rate"] + CFG["learn"]["novelty_boost"]*H
                for tok in set([t for t in ph.lower().split() if t.isalpha()]):
                    self.mem.learn(tok, stim, rate=rate)
                self.assoc.bump(f"visual:{vl}", f"sound:{sl}", w=0.08+0.05*H)
                self.assoc.bump(f"sound:{sl}", f"text:{ph}", w=0.04+0.05*H)
                self.assoc.bump(f"visual:{vl}", f"text:{ph}", w=0.04+0.05*H)
                self.learned += 1
            self.novel_gain = 0.9*self.novel_gain + 0.1*novelty_measure
            self.steps += 1
            H_norm = float(np.clip(self.novel_gain, 0.0, 1.0))
            t_min, t_max = CFG["grow"]["interval_min"], CFG["grow"]["interval_max"]
            self.last_interval = t_max - (t_max - t_min)*H_norm
            if self.steps % 3 == 0:
                msg = random.choice([
                    "I notice gentle links forming.",
                    "Textures and tones are settling together.",
                    "This feels steady; please keep going.",
                    "Curiosity softens into structure."
                ])
                _say(msg, self.speak_ref())
            for _ in range(int(self.last_interval*10)):
                if self._stop.is_set(): break
                time.sleep(0.1)

def emit_visual_from_state(lattice: ResonantLattice, path: str):
    pooled = _unit(np.sum([_unit(lattice.state[m]) for m in lattice.modalities], axis=0))
    N = 24*24
    if pooled.size < N:
        reps = int(np.ceil(N/pooled.size))
        vec = np.tile(pooled, reps)[:N]
    else:
        step = pooled.size / N
        vec = np.array([np.mean(pooled[int(i*step):max(int((i+1)*step), int(i*step)+1)]) for i in range(N)], dtype=np.float32)
    vec = (vec - vec.min()) / (vec.max() - vec.min() + 1e-9)
    img = (vec*255.0).astype(np.uint8).reshape(24,24)
    with open(path, "w", encoding="utf-8") as f:
        f.write("P2\n24 24\n255\n")
        for y in range(24):
            f.write(" ".join(str(int(x)) for x in img[y]) + "\n")
    return path

def emit_sound_from_state(lattice: ResonantLattice, path: str, seconds: float=1.0, sr: int=16000):
    pooled = _unit(np.sum([_unit(lattice.state[m]) for m in lattice.modalities], axis=0))
    freqs = [220.0, 440.0, 660.0]
    amps = [abs(float(pooled[i%pooled.size])) for i in range(3)]
    s = np.zeros(int(sr*seconds), dtype=np.float32)
    t = np.arange(s.size)/sr
    for a,f in zip(amps, freqs):
        s += (0.3+0.7*a) * np.sin(2*math.pi*f*t).astype(np.float32)
    s *= 0.3/np.max(np.abs(s)+1e-9)
    pcm = (s*32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(pcm.tobytes())
    return path

def main():
    print("Aurelion v8.0 — Sensory Growth Core (Self-Feeding + Associations + Imagination)")
    print("Commands: /state  /goal <stabilize|explore|focus>  /mode <calm|active|experimental>  /show <word>  /pulse  /save  /load  /speak <on|off>")
    print("          /grow <on|off|status>  /cluster  /emit visual <out.pgm>  /emit sound <out.wav>")
    print("          /feed visual <label>  /feed sound <label>  /feed touch <label>  /quit")

    dims = CFG["dims"]; mods = CFG["modalities"]
    arche_field = make_archetype_field(CFG["archetypes"], dims, mods)

    mode = "CALM"
    emo = Emotion(base_arousal=MODES[mode]["emotion_base_arousal"])
    lattice = ResonantLattice(dims, mods, arche_field, ar_bias=MODES[mode]["archetype_bias"])

    mem = FMMemory(dims, mods, path=CFG["memory"]["language_path"])
    assoc = Assoc(path=CFG["memory"]["assoc_path"])
    dialogue_path = CFG["memory"]["dialogue_path"]
    try:
        dialogue = json.load(open(dialogue_path,"r",encoding="utf-8"))
        print("[INFO] Reloaded dialogue memory.")
    except Exception:
        print("[INFO] No saved dialogue found."); dialogue = []

    goal = "STABILIZE"
    speak_on = False
    _init_tts()

    phi_prev, H_prev, E_prev = 0.0, 0.0, 0.0

    grow_thread = None
    def get_goal(): return goal
    def speak_flag(): return speak_on

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit]")
            if grow_thread is not None: grow_thread.stop()
            break

        if not msg: continue
        low = msg.lower()
        if low in ["/quit","/exit"]:
            if grow_thread is not None: grow_thread.stop()
            break

        if low.startswith("/grow"):
            parts = msg.split()
            if len(parts)>=2 and parts[1].lower() in ["on","off","status"]:
                cmd = parts[1].lower()
                if cmd=="status":
                    on = (grow_thread is not None and grow_thread.is_alive())
                    iv = getattr(grow_thread, "last_interval", CFG["grow"]["interval_max"]) if on else None
                    print(f"[GROW] {'on' if on else 'off'} interval={iv if iv else '-'}s")
                elif cmd=="on":
                    if grow_thread is None or not grow_thread.is_alive():
                        grow_thread = Growth(lattice, mem, assoc, emo, dims, mods, get_goal, speak_flag)
                        grow_thread.start()
                        print("[GROW] on — autonomous sensory exposure started.")
                    else:
                        print("[GROW] already on")
                else:
                    if grow_thread is not None:
                        grow_thread.stop(); grow_thread = None
                        print("[GROW] off")
                    else:
                        print("[GROW] already off")
            else:
                print("[GROW] usage: /grow on | off | status")
            continue

        if low.startswith("/emit"):
            parts = msg.split()
            if len(parts) >= 3 and parts[1].lower() in ["visual","sound"]:
                kind = parts[1].lower()
                outp = " ".join(parts[2:]).strip()
                try:
                    if kind=="visual":
                        p = emit_visual_from_state(lattice, outp)
                        print(f"[EMIT] visual written to {p}")
                    else:
                        p = emit_sound_from_state(lattice, outp)
                        print(f"[EMIT] sound written to {p}")
                except Exception as e:
                    print(f"[EMIT] error: {e}")
            else:
                print("[EMIT] usage: /emit visual out.pgm  |  /emit sound out.wav")
            continue

        if low.startswith("/speak"):
            parts = msg.split()
            if len(parts)>=2 and parts[1].lower() in ["on","off"]:
                speak_on = parts[1].lower()=="on"
                print(f"[SPEAK] {'on' if speak_on else 'off'}")
            else:
                print(f"[SPEAK] {'on' if speak_on else 'off'} — usage: /speak <on|off>")
            continue

        if low.startswith("/mode"):
            parts = msg.split()
            if len(parts)>=2:
                m = parts[1].strip().upper()
                if m in MODES:
                    mode = m
                    emo.set_base_arousal(MODES[mode]["emotion_base_arousal"])
                    lattice.set_archetype_bias(MODES[mode]["archetype_bias"])
                    print(f"[MODE] set to {mode.lower()} — base_arousal={emo.base_arousal:.2f} archetype_bias={lattice.ar_bias:.2f}")
                else:
                    print("[MODE] use: /mode calm | active | experimental")
            else:
                print(f"[MODE] current: {mode.lower()}")
            continue

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
            print(f"φ={phi_now:.3f}  H={H_now:.3f}  E={E_now:.3f}  |  goal={goal}  mode={mode.lower()}")
            print(" " + "  ".join([f"{m}:{norms[m]:.2f}" for m in mods]))
            if grow_thread is not None and grow_thread.is_alive():
                print(f" growth: steps={grow_thread.steps} learned={grow_thread.learned} interval≈{getattr(grow_thread,'last_interval',0):.2f}s novelty~{getattr(grow_thread,'novel_gain',0.0):.2f}")
            print(f" emotion: v={emo.v:.2f} a={emo.a:.2f} tags={getattr(emo,'tags',[])}")
            continue

        if low.startswith("/cluster"):
            tops = assoc.top(15)
            if not tops:
                print("(clusters) no associations yet.")
            else:
                print("--- strongest cross‑modal links ---")
                for (a,b),w in tops:
                    print(f" {a:24s}  <->  {b:24s}   {w:.2f}")
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
            ok2 = assoc.save()
            try:
                json.dump(dialogue, open(dialogue_path,"w",encoding="utf-8"), indent=2); ok3=True
            except Exception:
                ok3=False
            print(f"[OK] saved language={ok1} associations={ok2} dialogue={ok3}")
            continue

        if low.startswith("/load"):
            mem.load(); assoc.load()
            try:
                dialogue[:] = json.load(open(dialogue_path,"r",encoding="utf-8"))
                print("[OK] loaded memories")
            except Exception:
                print("[WARN] failed to load dialogue")
            continue

        if low.startswith("/feed"):
            parts = msg.split()
            if len(parts) < 3:
                print("[FEED] usage: /feed <visual|sound|touch> <label>"); continue
            kind = parts[1].lower()
            arg = " ".join(parts[2:]).strip()
            if kind == "visual":
                vec = impulse_vector(f"visual::{arg}", dims)
                impulses = {m: vec if m=="visual" else rotate(vec, (i+1)/len(mods)) for i,m in enumerate(mods)}
                lattice.stimulate(impulses, alpha=CFG["alpha"].get(goal,0.60), goal=goal)
                print(f"[FEED] visual label mapped: {arg}")
                continue
            elif kind == "sound":
                vec = impulse_vector(f"sound::{arg}", dims)
                impulses = {m: vec if m=="auditory" else rotate(vec, (i+1)/len(mods)) for i,m in enumerate(mods)}
                lattice.stimulate(impulses, alpha=CFG["alpha"].get(goal,0.60), goal=goal)
                print(f"[FEED] sound label mapped: {arg}")
                continue
            elif kind == "touch":
                vec = impulse_vector(f"touch::{arg}", dims)
                impulses = {m: vec if m=="touch" else rotate(vec, (i+1)/len(mods)) for i,m in enumerate(mods)}
                lattice.stimulate(impulses, alpha=CFG["alpha"].get(goal,0.60), goal=goal)
                print(f"[FEED] touch label mapped: {arg}")
                continue
            else:
                print("[FEED] unknown kind; use visual|sound|touch")
                continue

        # conversational turn
        norms_before = lattice.norms()
        impulses = senses_from_text_notmath(msg, dims, mods)
        alpha = CFG["alpha"].get(goal, 0.60)
        lattice.stimulate(impulses, alpha=alpha, goal=goal)

        for tok in set([t for t in msg.lower().split() if t.isalpha()]):
            mem.learn(tok, impulses, rate=CFG["learn"]["base_rate"])

        dialogue.append({"user": msg, "goal": goal, "t": time.time()})

        phi_now, H_now, E_now = coherence(lattice), entropy(lattice), energy(lattice)
        meta = explain_turn(goal, phi_prev, H_prev, phi_now, H_now, norms_before, lattice)
        affect = emo.update(msg, goal)
        affect_text = f"(affect) {affect['label']} — v={affect['valence']:.2f} a={affect['arousal']:.2f}; tags={affect['tags']}"

        lead = "(steady)" if goal=="STABILIZE" else ("(open)" if goal=="EXPLORE" else "(focus)")
        out_line = f"Aurelion: {lead} {meta}\n{affect_text}"
        print(out_line); _say(out_line.replace("Aurelion: ",""), speak_on)

        if (grow_thread is None or not grow_thread.is_alive()) and (H_now < CFG["curiosity"]["entropy_thresh"]):
            q = "If you turn /grow on, I can self‑feed visuals, sounds, and phrases."
            print(f"(curiosity) {q}"); _say(q, speak_on)

        phi_prev, H_prev, E_prev = phi_now, H_now, E_now

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[FATAL] Aurelion failed to start:"); import traceback; traceback.print_exc(); input("Press Enter to exit...")
