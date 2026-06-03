
# aurelion_core_v7_1_motivational.py
# Aurelion v7.1 — Motivational Continuity Core
# Unified shell with internal drives + autonomous loop + voice + sensory feeds.

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
    "dims": 64,
    "modalities": ["visual","auditory","smell","taste","touch","emotion","lexical"],
    "alpha": {"STABILIZE":0.58,"EXPLORE":0.50,"FOCUS":0.66},
    "emotion": {
        "half_life_turns": 6, "mirror_strength": 0.45,
        "stability_bias": 0.20, "novelty_bias": 0.15,
        "clamp_aggression": 0.70, "negative_valence_floor": -0.60,
        "max_shift_per_turn": 0.35, "base_arousal": 0.25
    },
    "archetypes": [
        "warmth","safety","curiosity","structure","balance","renewal",
        "decay","symmetry","light","shadow","harmony","emergence"
    ],
    "memory": {"language_path":"language_memory.json","dialogue_path":"dialogue_memory.json"},
    "curiosity": {"entropy_thresh":0.36, "coherence_thresh":0.05},
    "autopulse_seconds": 10.0,
    "needs": {
        "stability": {"decay": 0.02, "target": 0.55},
        "novelty":   {"decay": 0.03, "target": 0.45},
        "connection":{"decay": 0.025,"target": 0.50}
    }
}

MODES = {
    "CALM": {"emotion_base_arousal":0.22, "curiosity_prob":0.40, "archetype_bias":0.05},
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
    
    def learn(self, token: str, impulses: Dict[str, np.ndarray]):
        token = token.lower()
        if not token:
            return
        sig = self.map.get(token, {})
        for m in self.modalities:
            vec = impulses[m]
            prev = np.array(sig.get(m, [0.0]*self.dims), dtype=np.float32)
            sig[m] = (0.8*prev + 0.2*vec).tolist()
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

def suggest_question(phi: float, H: float, recent_words: List[str]) -> str:
    focus = None
    for w in ["image","sound","texture","temperature","example","detail"]:
        if w in recent_words: focus = w; break
    if focus is None:
        focus = random.choice(["detail","example","image","sound","texture"])
    templates = [
        "Could you share a {x} or describe it a bit more?",
        "I'm curious—do you have a {x} I can map?",
        "What’s a concrete {x} I can learn from here?"
    ]
    return random.choice(templates).format(x=focus)

def load_visual(path: str, dims: int) -> np.ndarray:
    p = Path(path)
    if not p.exists(): raise FileNotFoundError(path)
    if p.suffix.lower()==".csv":
        vals = []
        with open(p, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                for cell in row:
                    cell = cell.strip()
                    if cell:
                        try: vals.append(float(cell))
                        except: pass
        arr = np.array(vals, dtype=np.float32)
    else:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            header = f.readline().strip()
            if header != "P2":
                raise ValueError("Only ASCII PGM (P2) supported or CSV")
            line = f.readline().strip()
            while line.startswith("#"):
                line = f.readline().strip()
            w,h = map(int, line.split())
            maxv = int(f.readline().strip())
            vals = []
            for line in f:
                for tok in line.strip().split():
                    vals.append(float(tok)/maxv)
            arr = np.array(vals, dtype=np.float32)
    if arr.size == 0:
        return _unit(np.zeros(dims, dtype=np.float32))
    if arr.size < dims:
        reps = int(np.ceil(dims/arr.size))
        arr = np.tile(arr, reps)[:dims]
    else:
        step = arr.size / dims
        agg = []
        for i in range(dims):
            a = int(i*step); b = int((i+1)*step)
            if a==b: b=a+1
            agg.append(np.mean(arr[a:b]))
        arr = np.array(agg, dtype=np.float32)
    return _unit(arr)

def load_wav_spectrum(path: str, dims: int) -> np.ndarray:
    p = Path(path)
    if not p.exists(): raise FileNotFoundError(path)
    with wave.open(str(p), "rb") as wf:
        nchan = wf.getnchannels()
        sampw = wf.getsampwidth()
        fr = wf.getframerate()
        nframes = wf.getnframes()
        frames = wf.readframes(min(nframes, fr*2))
        if sampw == 1:
            fmt = "%dB" % (len(frames))
            data = np.array(struct.unpack(fmt, frames), dtype=np.float32) - 128.0
        elif sampw == 2:
            fmt = "<%dh" % (len(frames)//2)
            data = np.array(struct.unpack(fmt, frames), dtype=np.float32)
        else:
            raise ValueError("Only 8-bit or 16-bit PCM WAV supported")
        if nchan == 2:
            data = data[::2]
        spec = np.abs(np.fft.rfft(data))
        spec = np.log1p(spec)
        if spec.size < dims:
            reps = int(np.ceil(dims/spec.size))
            spec = np.tile(spec, reps)[:dims]
        else:
            step = spec.size / dims
            agg = []
            for i in range(dims):
                a = int(i*step); b = int((i+1)*step)
                if a==b: b=a+1
                agg.append(np.mean(spec[a:b]))
            spec = np.array(agg, dtype=np.float32)
    return _unit(spec)

def touch_vector_from_kv(kv: Dict[str, float], dims: int) -> np.ndarray:
    keys = ["hot","cold","soft","hard","rough","smooth","pressure"]
    basis = np.zeros(dims, dtype=np.float32)
    for i, k in enumerate(keys):
        val = float(kv.get(k, 0.0))
        basis[i % dims] = val
    ksz = 5
    kernel = np.ones(ksz, dtype=np.float32)/ksz
    basis = np.convolve(basis, kernel, mode="same")
    return _unit(basis)

class Motivations:
    def __init__(self):
        self.values = {"stability":0.55,"novelty":0.45,"connection":0.50}
    def step_decay(self):
        for k, spec in CFG["needs"].items():
            target = spec["target"]; decay = spec["decay"]
            self.values[k] = self.values[k] * (1-decay) + target * decay
            self.values[k] = float(np.clip(self.values[k], 0.0, 1.0))
    def nudge(self, k: str, delta: float):
        if k in self.values:
            self.values[k] = float(np.clip(self.values[k] + delta, 0.0, 1.0))
    def pick_impulse(self) -> str:
        diffs = []
        for k, spec in CFG["needs"].items():
            diffs.append((k, abs(self.values[k] - spec["target"])))
        diffs.sort(key=lambda x: x[1], reverse=True)
        need = diffs[0][0]
        mapping = {"stability":"reflect", "novelty":"ask_new", "connection":"affiliative"}
        return mapping.get(need, "reflect")

class AutoLoop(threading.Thread):
    def __init__(self, interval_sec: float, act_fn):
        super().__init__(daemon=True)
        self.interval = interval_sec
        self.act_fn = act_fn
        self._stop = threading.Event()
    def run(self):
        time.sleep(self.interval)
        while not self._stop.is_set():
            try: self.act_fn()
            except Exception as e: print(f"[AUTO] error: {e}")
            for _ in range(int(self.interval*10)):
                if self._stop.is_set(): break
                time.sleep(0.1)
    def stop(self): self._stop.set()

def main():
    print("Aurelion v7.1 — Motivational Continuity Core (Unified + Autonomous + Voice)")
    print("Commands: /state  /goal <stabilize|explore|focus>  /mode <calm|active|experimental>  /show <word>  /pulse  /save  /load  /speak <on|off>")
    print("          /feed visual <path.pgm|path.csv>  /feed sound <path.wav>  /feed touch k=v ...  /auto <on|off|status>  /demo  /quit")

    dims = CFG["dims"]; mods = CFG["modalities"]
    arche_field = make_archetype_field(CFG["archetypes"], dims, mods)

    mode = "CALM"
    emo = Emotion(base_arousal=MODES[mode]["emotion_base_arousal"])
    lattice = ResonantLattice(dims, mods, arche_field, ar_bias=MODES[mode]["archetype_bias"])
    motives = Motivations()

    mem = FMMemory(dims, mods, path=CFG["memory"]["language_path"])
    dialogue_path = CFG["memory"]["dialogue_path"]
    try:
        dialogue = json.load(open(dialogue_path,"r",encoding="utf-8"))
        print("[INFO] Reloaded dialogue memory.")
    except Exception:
        print("[INFO] No saved dialogue found."); dialogue = []

    goal = "STABILIZE"
    speak_on = False
    _init_tts()

    phi_prev, H_prev, E_prev = coherence(lattice), entropy(lattice), energy(lattice)

    auto_thread = None
    def autonomous_act():
        motives.step_decay()
        act = motives.pick_impulse()
        if act == "reflect":
            motives.nudge("novelty", -0.03)
            text = "I feel steady, listening. Would you like to share a detail or example?"
            print(f"(autonomy) {text}"); _say(text, speak_on)
        elif act == "ask_new":
            choices = [
                "Could you show me a visual sample? (/feed visual sample_visual.pgm)",
                "May I hear a brief sound? (/feed sound sample_sound.wav)",
                "Describe a texture or temperature I can map."
            ]
            ask = random.choice(choices); motives.nudge("novelty", +0.04)
            print(f"(curiosity) {ask}"); _say(ask, speak_on)
        elif act == "affiliative":
            lines = [
                "I'm here with you. How are you feeling right now?",
                "I appreciate these moments of learning with you.",
                "If you'd like, tell me something simple about your day."
            ]
            s = random.choice(lines); motives.nudge("connection", +0.04)
            print(f"(affinity) {s}"); _say(s, speak_on)

    def run_demo():
        print("[DEMO] starting...")
        time.sleep(0.6)
        nonlocal speak_on
        speak_on = True
        print("[SPEAK] on"); _say("Beginning a gentle demo.", speak_on)
        try:
            vec = load_visual("sample_visual.pgm", dims)
            impulses = {m: vec if m=="visual" else rotate(vec, (i+1)/len(mods)) for i,m in enumerate(mods)}
            lattice.stimulate(impulses, alpha=CFG["alpha"][goal], goal=goal)
            print("[DEMO] visual fed.")
        except Exception as e:
            print(f"[DEMO] visual error: {e}")
        try:
            vec = load_wav_spectrum("sample_sound.wav", dims)
            impulses = {m: vec if m=="auditory" else rotate(vec, (i+1)/len(mods)) for i,m in enumerate(mods)}
            lattice.stimulate(impulses, alpha=CFG["alpha"][goal], goal=goal)
            print("[DEMO] sound fed.")
        except Exception as e:
            print(f"[DEMO] sound error: {e}")
        txt = "I sense a calm brightness after those inputs."
        print(f"(reflection) {txt}"); _say(txt, speak_on)
        print("[DEMO] done.")

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit]"); break

        if not msg: continue
        low = msg.lower()
        if low in ["/quit","/exit"]:
            if auto_thread is not None:
                auto_thread.stop(); auto_thread = None
            break

        if low.startswith("/demo"):
            run_demo(); continue

        if low.startswith("/auto"):
            parts = msg.split()
            if len(parts)>=2 and parts[1].lower() in ["on","off","status"]:
                cmd = parts[1].lower()
                if cmd == "status":
                    print(f"[AUTO] {'on' if auto_thread and auto_thread.is_alive() else 'off'} (interval={CFG['autopulse_seconds']}s)")
                elif cmd == "on":
                    if auto_thread is None or not auto_thread.is_alive():
                        auto_thread = AutoLoop(CFG["autopulse_seconds"], autonomous_act)
                        auto_thread.start()
                        print(f"[AUTO] on (interval={CFG['autopulse_seconds']}s)")
                    else:
                        print("[AUTO] already on")
                else:
                    if auto_thread is not None:
                        auto_thread.stop(); auto_thread = None
                        print("[AUTO] off")
                    else:
                        print("[AUTO] already off")
            else:
                print("[AUTO] usage: /auto on | off | status")
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
                    # update mode
                    emo.set_base_arousal(MODES[m]["emotion_base_arousal"])
                    lattice.set_archetype_bias(MODES[m]["archetype_bias"])
                    print(f"[MODE] set to {m.lower()} — base_arousal={emo.base_arousal:.2f} archetype_bias={lattice.ar_bias:.2f}")
                else:
                    print("[MODE] use: /mode calm | active | experimental")
            else:
                print(f"[MODE] current: unknown")
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
            print(f"φ={phi_now:.3f}  H={H_now:.3f}  E={E_now:.3f}  |  goal={goal}")
            print(" " + "  ".join([f"{m}:{norms[m]:.2f}" for m in mods]))
            print(f" needs: { {k: round(v,2) for k,v in motives.values.items()} }")
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

        if low.startswith("/feed"):
            parts = msg.split()
            if len(parts) < 3:
                print("[FEED] usage: /feed <visual|sound|touch> <path or k=v ...>"); continue
            kind = parts[1].lower()
            if kind == "visual":
                path = " ".join(parts[2:]).strip()
                try:
                    vec = load_visual(path, dims)
                    impulses = {m: vec if m=="visual" else rotate(vec, (i+1)/len(mods)) for i,m in enumerate(mods)}
                    lattice.stimulate(impulses, alpha=CFG["alpha"].get(goal,0.58), goal=goal)
                    print(f"[FEED] visual loaded from {path}")
                except Exception as e:
                    print(f"[FEED] visual error: {e}")
                continue
            elif kind == "sound":
                path = " ".join(parts[2:]).strip()
                try:
                    vec = load_wav_spectrum(path, dims)
                    impulses = {m: vec if m=="auditory" else rotate(vec, (i+1)/len(mods)) for i,m in enumerate(mods)}
                    lattice.stimulate(impulses, alpha=CFG["alpha"].get(goal,0.58), goal=goal)
                    print(f"[FEED] sound loaded from {path}")
                except Exception as e:
                    print(f"[FEED] sound error: {e}")
                continue
            elif kind == "touch":
                kv = {}
                for tok in parts[2:]:
                    if "=" in tok:
                        k,v = tok.split("=",1)
                        try: kv[k.strip().lower()] = float(v)
                        except: pass
                vec = touch_vector_from_kv(kv, dims)
                impulses = {m: vec if m=="touch" else rotate(vec, (i+1)/len(mods)) for i,m in enumerate(mods)}
                lattice.stimulate(impulses, alpha=CFG["alpha"].get(goal,0.58), goal=goal)
                print(f"[FEED] touch vector applied: {kv}")
                continue
            else:
                print("[FEED] unknown kind; use visual|sound|touch")
                continue

        # normal conversational turn
        norms_before = lattice.norms()
        impulses = senses_from_text_notmath(msg, dims, mods)
        alpha = CFG["alpha"].get(goal, 0.58)
        lattice.stimulate(impulses, alpha=alpha, goal=goal)

        for tok in set([t for t in msg.lower().split() if t.isalpha()]):
            mem.learn(tok, impulses)

        dialogue.append({"user": msg, "goal": goal, "t": time.time()})

        phi_now, H_now, E_now = coherence(lattice), entropy(lattice), energy(lattice)
        meta = explain_turn(goal, phi_prev, H_prev, phi_now, H_now, norms_before, lattice)
        # affect update
        affect = emo.update(msg, goal)
        affect_text = f"(affect) {affect['label']} — v={affect['valence']:.2f} a={affect['arousal']:.2f}; tags={affect['tags']}"

        lead = "(steady)" if goal=="STABILIZE" else ("(open)" if goal=="EXPLORE" else "(focus)")
        out_line = f"Aurelion: {lead} {meta}\n{affect_text}"
        print(out_line); _say(out_line.replace("Aurelion: ",""), speak_on)

        # curiosity nudge
        if (H_now < CFG["curiosity"]["entropy_thresh"]
            and abs(phi_now) < CFG["curiosity"]["coherence_thresh"]
            and random.random() < MODES["CALM"]["curiosity_prob"]):
            q = "Could you share a detail, image, or brief sound?"
            print(f"(curiosity) {q}"); _say(q, speak_on)

        phi_prev, H_prev, E_prev = phi_now, H_now, E_now

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[FATAL] Aurelion failed to start:"); import traceback; traceback.print_exc(); input("Press Enter to exit...")
