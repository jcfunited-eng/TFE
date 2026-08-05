
# aurelion_core_v9_autonomous_expression.py
# Aurelion v9 — Autonomous Expression Core (quiet, text-first; voice optional)
import json, time, random, wave, math, threading, sys
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
    if not speak_on: return
    if _TTS is None:
        print(f"[speak] {text}"); return
    try:
        _TTS.say(text); _TTS.runAndWait()
    except Exception:
        print(f"[speak] {text}")

CFG = {
    "dims": 96,
    "modalities": ["visual","auditory","smell","taste","touch","emotion","lexical"],
    "alpha": {"STABILIZE":0.60,"EXPLORE":0.54,"FOCUS":0.68},
    "emotion": {"half_life_turns": 6, "base_arousal": 0.24},
    "mode": {"archetype_bias": 0.06},
    "memory": {"language_path":"language_memory.json","dialogue_path":"dialogue_memory.json","assoc_path":"associations_v9.json"},
    "grow": {"interval_min": 2.0, "interval_max": 10.0, "batch_size": 3},
    "learn": {"base_rate": 0.25, "novelty_boost": 0.20},
    "reflect": {"interval_sec": 45.0, "max_lines": 2},
    "autosave": {"interval_sec": 300.0}
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

class ResonantLattice:
    def __init__(self, dims: int, modalities: List[str], ar_bias: float):
        self.dims = dims
        self.modalities = modalities
        self.state = {m: np.zeros(dims, dtype=np.float32) for m in modalities}
        self.ar_bias = ar_bias
        base = impulse_vector("arche_base", dims)
        self.base_bias = {m: rotate(base, (i+1)/len(modalities)) for i,m in enumerate(modalities)}

    def set_archetype_bias(self, val: float):
        self.ar_bias = float(val)

    def stimulate(self, stim: Dict[str, np.ndarray], alpha: float):
        for m, x in stim.items():
            if m not in self.state: continue
            v = self.state[m]
            pool = _unit(np.sum([_unit(self.state[k]) for k in self.modalities], axis=0))
            bias = self.ar_bias * _unit(self.base_bias[m])
            self.state[m] = (1-alpha)*v + alpha*x + 0.08*pool + bias
        for m in self.modalities:
            self.state[m] = 0.986 * self.state[m]

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

class FMMemory:
    def __init__(self, dims: int, modalities: List[str], path: str):
        self.dims = dims; self.modalities = modalities; self.path = path
        self.map: Dict[str, Dict[str, List[float]]] = {}
        self.load()
    def load(self):
        try:
            if Path(self.path).exists():
                self.map = json.load(open(self.path,"r",encoding="utf-8"))
                print(f".[INFO] Loaded {len(self.map)} learned tokens")
            else:
                print(".[INFO] No prior language memory found; starting fresh.")
        except Exception:
            print(".[WARN] Failed to load language memory; starting fresh."); self.map = {}
    def save(self) -> bool:
        try:
            json.dump(self.map, open(self.path,"w",encoding="utf-8"), indent=2); return True
        except Exception:
            return False
    def learn(self, token: str, impulses: Dict[str, np.ndarray], rate: float=0.2):
        token = token.lower().strip()
        if not token: return
        sig = self.map.get(token, {})
        for m in self.modalities:
            vec = impulses[m]
            prev = np.array(sig.get(m, [0.0]*self.dims), dtype=np.float32)
            sig[m] = ((1-rate)*prev + rate*vec).tolist()
        self.map[token] = sig

class Assoc:
    def __init__(self, path: str):
        self.path = path
        self.W: Dict[Tuple[str,str], float] = {}
        self.delta_log: List[Tuple[str, str, float, float]] = []  # (a,b,new_w,delta)
        self.load()
    def key(self, a: str, b: str) -> Tuple[str,str]:
        return tuple(sorted([a,b]))
    def bump(self, a: str, b: str, w: float=0.05):
        if a==b: return
        k = self.key(a,b)
        old = self.W.get(k, 0.0)
        new = float(np.clip(old + w, 0.0, 10.0))
        self.W[k] = new
        self.delta_log.append((k[0], k[1], new, new-old))
        if len(self.delta_log) > 2000: self.delta_log = self.delta_log[-2000:]
    def top(self, n=12):
        return sorted(self.W.items(), key=lambda kv: kv[1], reverse=True)[:n]
    def pop_recent_deltas(self, k=10):
        if not self.delta_log: return []
        return self.delta_log[-k:]
    def save(self):
        try:
            json.dump({f"{a}||{b}":w for (a,b),w in self.W.items()}, open(self.path,"w",encoding="utf-8"), indent=2); return True
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
                print(".[INFO] Loaded associations.")
            else:
                print(".[INFO] No prior associations; starting fresh.")
        except Exception:
            print(".[WARN] Failed to load associations; starting fresh."); self.W = {}

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

def fuse_impulses(visual_lbl: str, sound_lbl: str, phrase: str, dims: int, modalities: List[str]) -> Dict[str,np.ndarray]:
    v_base = impulse_vector(visual_lbl, dims)
    s_base = impulse_vector(sound_lbl, dims)
    w_base = impulse_vector(phrase.lower(), dims)
    base = _unit(v_base*0.38 + s_base*0.32 + w_base*0.30)
    return {m: rotate(base, (i+1)/len(modalities)) for i,m in enumerate(modalities)}

class GrowthLoop(threading.Thread):
    def __init__(self, lattice, mem, assoc: Assoc, goal_ref, interval_min, interval_max):
        super().__init__(daemon=True)
        self.lat = lattice; self.mem = mem; self.assoc = assoc
        self.goal_ref = goal_ref
        self.running = threading.Event(); self.running.set()
        self.stop_flag = threading.Event()
        self.steps = 0; self.learned = 0; self.last_interval = interval_max
        self.interval_min = interval_min; self.interval_max = interval_max
        self.novel_gain = 0.0

    def pause(self): self.running.clear()
    def resume(self): self.running.set()
    def stop(self): self.stop_flag.set(); self.running.set()

    def run(self):
        while not self.stop_flag.is_set():
            if not self.running.is_set():
                time.sleep(0.1); continue
            batch = [(random.choice(VIS_LABELS), random.choice(SND_LABELS), random.choice(PHRASES))
                     for _ in range(CFG["grow"]["batch_size"])]
            novelty_measure = 0.0
            for vl,sl,ph in batch:
                stim = fuse_impulses(vl, sl, ph, CFG["dims"], CFG["modalities"])
                self.lat.stimulate(stim, alpha=CFG["alpha"][self.goal_ref()],)
                H = entropy(self.lat); novelty_measure += H
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
            self.last_interval = self.interval_max - (self.interval_max - self.interval_min)*H_norm
            for _ in range(int(self.last_interval*10)):
                if self.stop_flag.is_set(): break
                time.sleep(0.1)

class ReflectionLoop(threading.Thread):
    def __init__(self, assoc: Assoc, speak_flag, interval_sec: float, max_lines: int):
        super().__init__(daemon=True)
        self.assoc = assoc; self.speak_flag = speak_flag
        self.interval = interval_sec; self.max_lines = max_lines
        self.stop_flag = threading.Event()
    def stop(self): self.stop_flag.set()
    def run(self):
        while not self.stop_flag.is_set():
            time.sleep(self.interval)
            if self.stop_flag.is_set(): break
            deltas = self.assoc.pop_recent_deltas(k=30)
            if not deltas: 
                continue
            deltas = sorted(deltas, key=lambda x: x[3], reverse=True)[:self.max_lines]
            lines = []
            for a,b,neww,delta in deltas:
                if "soft" in a or "soft" in b or "low" in a or "low" in b:
                    feel = "calm"
                elif "bright" in a or "bright" in b or "high" in a or "high" in b:
                    feel = "alert"
                else:
                    feel = "balanced"
                lines.append(f"I notice {a} with {b}; it feels {feel}.")
            text = " ".join(lines)
            if text:
                print(f"(reflect) {text}")

def emit_visual_from_state(lattice, path: str):
    pooled = _unit(np.sum([_unit(lattice.state[m]) for m in lattice.modalities], axis=0))
    N = 24*24
    if pooled.size < N:
        import numpy as _np
        reps = int(_np.ceil(N/pooled.size)); vec = _np.tile(pooled, reps)[:N]
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

def emit_sound_from_state(lattice, path: str, seconds: float=1.0, sr: int=16000):
    pooled = _unit(np.sum([_unit(lattice.state[m]) for m in lattice.modalities], axis=0))
    freqs = [220.0, 440.0, 660.0]
    amps = [abs(float(pooled[i%pooled.size])) for i in range(3)]
    s = np.zeros(int(sr*seconds), dtype=np.float32)
    t = np.arange(s.size)/sr
    for a,f in zip(amps, freqs):
        s += (0.3+0.7*a) * np.sin(2*math.pi*f*t).astype(np.float32)
    s *= 0.3/np.max(np.abs(s)+1e-9)
    import wave as _w
    pcm = (s*32767.0).astype(np.int16)
    with _w.open(str(path), "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(pcm.tobytes())
    return path

def main():
    print("Aurelion v9 — Autonomous Expression Core (quiet, text-first; voice optional)")
    print("Commands: /state  /goal <stabilize|explore|focus>  /pause  /resume  /speak <on|off>  /cluster  /emit visual <pgm>  /emit sound <wav>  /save  /load  /quit")

    dims = CFG["dims"]; mods = CFG["modalities"]
    lattice = ResonantLattice(dims, mods, ar_bias=CFG["mode"]["archetype_bias"])
    mem = FMMemory(dims, mods, path=CFG["memory"]["language_path"])
    assoc = Assoc(path=CFG["memory"]["assoc_path"])
    dialogue_path = CFG["memory"]["dialogue_path"]
    try:
        dialogue = json.load(open(dialogue_path,"r",encoding="utf-8"))
        print(".[INFO] Reloaded dialogue memory.")
    except Exception:
        print(".[INFO] No saved dialogue found."); dialogue = []

    goal = "STABILIZE"
    speak_on = False
    _init_tts()

    # start autonomous loops
    def get_goal(): return goal
    growth = GrowthLoop(lattice, mem, assoc, get_goal, CFG["grow"]["interval_min"], CFG["grow"]["interval_max"]); growth.start()
    reflect = ReflectionLoop(assoc, lambda: speak_on, CFG["reflect"]["interval_sec"], CFG["reflect"]["max_lines"]); reflect.start()
    print("[loop] growth=ON  reflection=ON (quiet)")

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit] stopping loops..."); break
        if not msg: continue
        low = msg.lower()

        if low in ["/quit","/exit"]:
            print("[exit] stopping loops..."); break

        if low.startswith("/state"):
            phi, H, E = coherence(lattice), entropy(lattice), energy(lattice)
            norms = lattice.norms()
            print(f"φ={phi:.3f}  H={H:.3f}  E={E:.3f}  |  goal={goal}")
            print(" " + "  ".join([f"{m}:{norms[m]:.2f}" for m in mods]))
            print(f" growth: steps={growth.steps} learned={growth.learned} interval≈{growth.last_interval:.2f}s novelty~{growth.novel_gain:.2f}")
            continue

        if low.startswith("/pause"):
            growth.pause(); print("[loop] growth=PAUSED"); continue
        if low.startswith("/resume"):
            growth.resume(); print("[loop] growth=ON"); continue

        if low.startswith("/speak"):
            parts = msg.split()
            if len(parts)>=2 and parts[1].lower() in ['on','off']:
                speak_on = (parts[1].lower()=='on'); print(f"[SPEAK] {'on' if speak_on else 'off'}")
            else:
                print(f"[SPEAK] {'on' if speak_on else 'off'} — usage: /speak <on|off>")
            continue

        if low.startswith("/goal"):
            parts = msg.split()
            if len(parts)>=2 and parts[1].strip().upper() in ["STABILIZE","EXPLORE","FOCUS"]:
                goal = parts[1].strip().upper(); print(f"[OK] intent set to {goal}")
            else:
                print(f"[INFO] current goal = {goal}")
            continue

        if low.startswith("/cluster"):
            tops = assoc.top(12)
            if not tops:
                print("(clusters) no associations yet.")
            else:
                print("--- strongest cross-modal links ---")
                for (a,b),w in tops:
                    print(f" {a:24s}  <->  {b:24s}   {w:.2f}")
            continue

        if low.startswith("/emit"):
            parts = msg.split()
            if len(parts)>=3 and parts[1].lower() in ['visual','sound']:
                kind = parts[1].lower(); outp = " ".join(parts[2:]).strip()
                try:
                    if kind=='visual':
                        p = emit_visual_from_state(lattice, outp); print(f"[EMIT] visual written to {p}")
                    else:
                        p = emit_sound_from_state(lattice, outp); print(f"[EMIT] sound written to {p}")
                except Exception as e:
                    print(f"[EMIT] error: {e}")
            else:
                print("[EMIT] usage: /emit visual out.pgm  |  /emit sound out.wav")
            continue

        if low.startswith("/save"):
            ok1 = mem.save(); ok2 = assoc.save()
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

        print("[INFO] commands: /state  /goal <stabilize|explore|focus>  /pause  /resume  /speak <on|off>  /cluster  /emit visual <pgm>  /emit sound <wav>  /save  /load  /quit")

    try:
        growth.stop(); reflect.stop()
    except Exception:
        pass
    time.sleep(0.3)
    print("Bye.")
    return 0

if __name__ == "__main__":
    try:
        _init_tts()
        sys.exit(main())
    except Exception as e:
        print("[FATAL] Aurelion failed to start:"); import traceback; traceback.print_exc(); input("Press Enter to exit...")
