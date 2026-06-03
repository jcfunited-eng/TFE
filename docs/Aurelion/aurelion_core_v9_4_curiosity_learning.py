# aurelion_core_v9_4_curiosity_learning.py
# Aurelion v9.4 — Curiosity / Knowledge-Seeking Core (Continuous Growth)

import json, os, sys, time, random, threading, re
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

# ---------------------- config ----------------------
CFG = {
    "dims": 96,
    "modalities": ["visual","auditory","smell","taste","touch","emotion","lexical"],
    "alpha": {"STABILIZE":0.60, "EXPLORE":0.55, "FOCUS":0.68},
    "paths": {
        "language": "language_memory.json",
        "assoc": "associations_v9.json",
        "corpora": "corpora",
        "diary": "logs/diary_v9_4.txt"
    },
    "corpus": {"sleep_between_lines": 0.5, "batch_lines": 3},
    "autosave_sec": 240,     # 4 minutes
    "diary_sec": 900,        # 15 minutes
    "curiosity_sec": 1800,   # 30 minutes per curiosity cycle
    "curiosity_lines": 80,   # max lines to ingest per curiosity probe
    "min_degree_for_satisfaction": 3,  # if a token has >=3 links, curiosity decays fast
    "reinforce": {"recall": 0.45, "reflect": 0.35, "curiosity": 0.40}
}

# ---------------------- helpers ----------------------
def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v) + 1e-9
    return v / n

def _seed(w: str) -> int:
    h = 2166136261
    for c in w:
        h ^= ord(c)
        h = (h * 16777619) & 0xffffffff
    return h

def impulse(w: str, d: int = CFG["dims"]) -> np.ndarray:
    rs = np.random.RandomState(_seed(w) % (2**31))
    v = rs.normal(0, 1, d)
    return _unit(v.astype(np.float32))

def rotate(v: np.ndarray, p: float) -> np.ndarray:
    k = int(p * (len(v) // 2))
    return _unit(np.roll(v, k))

def tokenize(text: str) -> List[str]:
    return [w.strip(".,!?;:()[]\"'").lower() for w in text.split() if w.strip()]

# ---------------------- lattice ----------------------
class Lattice:
    def __init__(self):
        self.m = {m: np.zeros(CFG["dims"], np.float32) for m in CFG["modalities"]}

    def stimulate(self, I: Dict[str, np.ndarray], a: float):
        pool = _unit(sum([_unit(v) for v in self.m.values()]))
        for m, v in I.items():
            self.m[m] = (1 - a) * self.m[m] + a * v + 0.05 * pool

    def norms(self):
        return {m: float(np.linalg.norm(v)) for m, v in self.m.items()}

def coherence(L: Lattice) -> float:
    v = [_unit(L.m[m]) for m in CFG["modalities"]]
    if len(v) < 2:
        return 0.0
    dots = []
    for i in range(len(v)):
        for j in range(i+1, len(v)):
            dots.append(float(np.dot(v[i], v[j])))
    return float(np.mean(dots)) if dots else 0.0

def entropy(L: Lattice) -> float:
    n = np.array([np.linalg.norm(v) for v in L.m.values()], dtype=np.float32)
    s = n.sum()
    if s < 1e-9:
        return 0.0
    p = np.clip(n / s, 1e-9, 1.0)
    return float(-np.sum(p * np.log(p)) / np.log(len(n)))

# ---------------------- memory ----------------------
class Memory:
    def __init__(self):
        self.path = CFG["paths"]["language"]
        self.map: Dict[str, Dict[str, List[float]]] = {}
        if Path(self.path).exists():
            self.map = json.load(open(self.path, "r", encoding="utf-8"))
            print(f"[INFO] Loaded {len(self.map)} words.")

    def save(self):
        json.dump(self.map, open(self.path, "w", encoding="utf-8"), indent=2)

    def learn(self, w: str, I: Dict[str, np.ndarray], r: float = 0.2):
        if not w:
            return
        sig = self.map.get(w, {})
        for m in CFG["modalities"]:
            prev = np.array(sig.get(m, [0.0]*CFG["dims"]), np.float32)
            sig[m] = ((1 - r) * prev + r * I[m]).tolist()
        self.map[w] = sig

    def signature(self, w: str) -> Dict[str, List[float]]:
        return self.map.get(w, {})

# ---------------------- associations ----------------------
class Assoc:
    def __init__(self):
        self.path = CFG["paths"]["assoc"]
        self.W: Dict[tuple, float] = {}
        if Path(self.path).exists():
            raw = json.load(open(self.path, "r", encoding="utf-8"))
            for k, v in raw.items():
                a, b = k.split("||")
                self.W[(a, b)] = float(v)
            print(f"[INFO] Loaded {len(self.W)} links.")

    def _key(self, a: str, b: str):
        return tuple(sorted([a, b]))

    def bump(self, a: str, b: str, w: float = 0.05):
        if a == b:
            return
        k = self._key(a, b)
        self.W[k] = self.W.get(k, 0.0) + w

    def save(self):
        json.dump({f"{a}||{b}": w for (a, b), w in self.W.items()},
                  open(self.path, "w", encoding="utf-8"), indent=2)

    def top(self, n=8):
        return sorted(self.W.items(), key=lambda kv: kv[1], reverse=True)[:n]

    def degree(self, token: str) -> int:
        node = f"text:{token}"
        d = 0
        for (a,b),_ in self.W.items():
            if a == node or b == node:
                d += 1
        return d

# ---------------------- seeds ----------------------
def seed_words(M: Memory):
    core = ("the of and to in a is that for on with be by this are from at or an which but have was not it i you he she we "
            "they do make go see know think come give love fear time life work man woman child world light dark good bad "
            "here there now before after near far above below within without because although while since during "
            "truth duty care help create build break open close start end").split()
    c = 0
    base = impulse("linguistic_core")
    for w in core:
        if w not in M.map:
            I = {m: rotate(base, (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
            M.learn(w, I, 1.0)
            c += 1
    if c:
        M.save()
        print(f"[seed] added {c} core words.")

# ---------------------- corpus utilities ----------------------
def list_corpus_files() -> List[Path]:
    root = Path(CFG["paths"]["corpora"])
    if not root.exists():
        try:
            root.mkdir(parents=True, exist_ok=True)
            print(f"[corpus] Created folder: {root}")
        except Exception as e:
            print(f"[corpus] WARN cannot create {root}: {e}")
    files = list(root.rglob("*.txt")) + list(root.rglob("*.md"))
    files.sort()
    return files

def line_stream_continuous():
    files = list_corpus_files()
    if not files:
        while True:
            yield "quiet harmony and safe space"
    while True:
        for p in files:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for ln in text.splitlines():
                s = ln.strip()
                if s:
                    yield s
        # loop again

def find_lines_with_token(token: str, limit: int) -> List[str]:
    token_l = token.lower()
    hits: List[str] = []
    for p in list_corpus_files():
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for ln in text.splitlines():
            s = ln.strip()
            if not s:
                continue
            # simple word-boundary-ish check
            if re.search(rf"\b{re.escape(token_l)}\b", s.lower()):
                hits.append(s)
                if len(hits) >= limit:
                    return hits
    return hits

# ---------------------- loops ----------------------
class CorpusLoop(threading.Thread):
    def __init__(self, L: Lattice, M: Memory, A: Assoc, goal_ref):
        super().__init__(daemon=True)
        self.L, self.M, self.A = L, M, A
        self.goal_ref = goal_ref
        self.stop_flag = threading.Event()

    def run(self):
        sleep_gap = CFG["corpus"]["sleep_between_lines"]
        batch_k = CFG["corpus"]["batch_lines"]
        accum = []
        for ln in line_stream_continuous():
            if self.stop_flag.is_set():
                break
            accum.append(ln)
            if len(accum) < batch_k:
                continue
            text = " ".join(accum)
            impulses = {m: rotate(impulse(text), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
            self.L.stimulate(impulses, a=CFG["alpha"][self.goal_ref()])
            H = entropy(self.L)
            rate = 0.28 + 0.25*H
            toks = set([t for t in tokenize(text) if t.isalpha()])
            for t in toks:
                bias = 1.2 if len(t) >= 5 else (1.0 if len(t) >= 3 else 0.9)
                self.M.learn(t, impulses, r=rate*bias)
                self.A.bump("text:corpus", f"text:{t}", w=0.02+0.04*H)
            accum = []
            # soft pause
            for _ in range(int(max(0.2, sleep_gap)*10)):
                if self.stop_flag.is_set():
                    break
                time.sleep(0.1)

    def stop(self): self.stop_flag.set()

class DiaryLoop(threading.Thread):
    def __init__(self, L: Lattice, A: Assoc):
        super().__init__(daemon=True)
        self.L, self.A = L, A
        self.stop_flag = threading.Event()
        Path("logs").mkdir(exist_ok=True)

    def run(self):
        interval = CFG["diary_sec"]
        while not self.stop_flag.is_set():
            time.sleep(interval)
            phi, H = coherence(self.L), entropy(self.L)
            pairs = [((a,b),w) for (a,b),w in self.A.top(4) if a.startswith("text:") and b.startswith("text:")]
            pretty = ", ".join([f"{a[0][5:]}↔{a[1][5:]}" for a,_ in pairs])
            line = f"[{time.strftime('%H:%M:%S')}] Reflecting on {pretty} φ={phi:.2f} H={H:.2f}"
            print(line)
            with open(CFG["paths"]["diary"], "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def stop(self): self.stop_flag.set()

class AutosaveLoop(threading.Thread):
    def __init__(self, M: Memory, A: Assoc):
        super().__init__(daemon=True)
        self.M, self.A = M, A
        self.stop_flag = threading.Event()

    def run(self):
        interval = CFG["autosave_sec"]
        t0 = time.time()
        while not self.stop_flag.is_set():
            time.sleep(1.0)
            if time.time() - t0 >= interval:
                ok1 = True; ok2 = True
                try: self.M.save()
                except Exception: ok1 = False
                try: self.A.save()
                except Exception: ok2 = False
                print(f"[autosave] language={ok1} associations={ok2}")
                t0 = time.time()

    def stop(self): self.stop_flag.set()

# ---------------------- curiosity ----------------------
class CuriosityLoop(threading.Thread):
    """
    Gap detector + inquiry + targeted ingestion.
    Picks tokens with low association degree and hunts lines containing them.
    """
    def __init__(self, L: Lattice, M: Memory, A: Assoc, goal_ref):
        super().__init__(daemon=True)
        self.L, self.M, self.A = L, M, A
        self.goal_ref = goal_ref
        self.stop_flag = threading.Event()
        self.enabled = True
        self.interest: Dict[str, float] = {}  # token -> interest score

    def _candidate_tokens(self, maxn=2000) -> List[str]:
        # sample from memory map to avoid scanning everything
        keys = list(self.M.map.keys())
        if not keys: return []
        random.shuffle(keys)
        return keys[:min(maxn, len(keys))]

    def _pick_probe(self) -> str:
        # raise interest for low-degree tokens
        for t in self._candidate_tokens():
            deg = self.A.degree(t)
            if deg < 2:
                self.interest[t] = self.interest.get(t, 0.0) + (2 - deg) * 0.5
            else:
                # decay curiosity when well connected
                cur = self.interest.get(t, 0.0)
                if cur > 0:
                    self.interest[t] = max(0.0, cur - 0.5*(deg/CFG["min_degree_for_satisfaction"]))
        if not self.interest:
            return ""
        # pick the highest-interest token
        t = max(self.interest.items(), key=lambda kv: kv[1])[0]
        return t

    def _ingest_lines(self, lines: List[str], focus_token: str):
        if not lines: return 0
        count = 0
        for ln in lines:
            impulses = {m: rotate(impulse(ln), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
            self.L.stimulate(impulses, a=CFG["alpha"][self.goal_ref()])
            toks = [w for w in tokenize(ln) if w.isalpha()]
            if not toks: 
                continue
            rate = CFG["reinforce"]["curiosity"]
            for t in set(toks):
                self.M.learn(t, impulses, r=rate)
                self.A.bump(f"text:{focus_token}", f"text:{t}", w=0.05)
            count += 1
            if count % 8 == 0: time.sleep(0.05)  # tiny breath
        return count

    def run(self):
        while not self.stop_flag.is_set():
            # wait for cycle
            for _ in range(int(CFG["curiosity_sec"])):
                if self.stop_flag.is_set(): 
                    return
                time.sleep(1.0)
            if not self.enabled:
                continue
            probe = self._pick_probe()
            if not probe:
                print("[curiosity] idle (no candidate yet)")
                continue
            print(f"[curiosity] probing: {probe}")
            # fetch lines that contain the probe term
            lines = find_lines_with_token(probe, limit=CFG["curiosity_lines"])
            if not lines:
                print(f"[curiosity] nothing found in corpora for '{probe}'")
                # small synthetic nudge so token isn't starved
                impulses = {m: rotate(impulse(probe), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
                self.L.stimulate(impulses, a=CFG["alpha"][self.goal_ref()])
                self.M.learn(probe, impulses, r=0.25)
                continue
            n = self._ingest_lines(lines, probe)
            # satisfaction: reduce interest if degree is now adequate
            deg = self.A.degree(probe)
            if deg >= CFG["min_degree_for_satisfaction"]:
                self.interest[probe] = max(0.0, self.interest.get(probe, 0.0) - 1.5*deg)
            else:
                self.interest[probe] = self.interest.get(probe, 0.0) + 0.5  # still curious
            print(f"[curiosity] ingested {n} lines for '{probe}' (degree={deg}, interest≈{self.interest.get(probe,0.0):.2f})")

    def stop(self): self.stop_flag.set()

# ---------------------- recall utils ----------------------
def assoc_neighbors(A: Assoc, base: str, depth=2, limit=40) -> List[str]:
    center = f"text:{base}"
    agg = {}
    frontier = {center: 1.0}
    visited = set()
    for d in range(depth):
        new_frontier = {}
        for node, gain in frontier.items():
            visited.add(node)
            for (a,b),w in A.W.items():
                if a == node or b == node:
                    m = b if a == node else a
                    if m in visited: 
                        continue
                    score = gain * (w / (1.0 + d))
                    agg[m] = agg.get(m, 0.0) + score
                    new_frontier[m] = max(new_frontier.get(m, 0.0), score)
        frontier = new_frontier
        if len(agg) >= limit:
            break
    ranked = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
    words = [k[5:] for k,_ in ranked if k.startswith("text:")]
    return words

# ---------------------- main ----------------------
def main():
    print("Aurelion v9.4 — Curiosity / Knowledge-Seeking Core (Continuous Growth)")
    L = Lattice()
    M = Memory()
    A = Assoc()
    seed_words(M)

    goal = "STABILIZE"

    corpus = CorpusLoop(L, M, A, goal_ref=lambda: goal); corpus.start()
    diary  = DiaryLoop(L, A); diary.start()
    autosave = AutosaveLoop(M, A); autosave.start()
    curiosity = CuriosityLoop(L, M, A, goal_ref=lambda: goal); curiosity.start()

    print("[loop] corpus=ON  curiosity=ON (30m cycles)  diary=ON (15m)  autosave=ON (4m)")
    print("[hint] Add .txt/.md files to ./corpora anytime; curiosity will probe low-degree concepts.")
    print("Commands: /state  /goal <stabilize|explore|focus>  /recall <keyword>  /curiosity <on|off|status>  /save  /quit")

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit] stopping ...")
            break
        if not msg:
            continue
        low = msg.lower()

        if low in ["/quit","exit"]:
            break

        if low.startswith("/state"):
            phi, H = coherence(L), entropy(L)
            norms = L.norms()
            print(f"φ={phi:.3f}  H={H:.3f}  |  tokens={len(M.map)}  links={len(A.W)}  curiosity={'ON' if curiosity.enabled else 'OFF'}")
            print(" " + "  ".join([f"{m}:{norms[m]:.2f}" for m in CFG['modalities']]))
            continue

        if low.startswith("/goal"):
            parts = msg.split()
            if len(parts)>=2 and parts[1].strip().upper() in ["STABILIZE","EXPLORE","FOCUS"]:
                goal = parts[1].strip().upper()
                print(f"[OK] intent set to {goal}")
            else:
                print(f"[INFO] current goal = {goal}")
            continue

        if low.startswith("/curiosity"):
            parts = msg.split()
            if len(parts) == 1 or parts[1].lower() == "status":
                status = "ON" if curiosity.enabled else "OFF"
                print(f"[curiosity] {status}  next cycle ≈ {CFG['curiosity_sec']}s")
            elif parts[1].lower() == "on":
                curiosity.enabled = True
                print("[curiosity] ON")
            elif parts[1].lower() == "off":
                curiosity.enabled = False
                print("[curiosity] OFF")
            else:
                print("[curiosity] usage: /curiosity on|off|status")
            continue

        if low.startswith("/recall"):
            parts = msg.split(maxsplit=1)
            if len(parts) < 2:
                print("[recall] usage: /recall <keyword>")
                continue
            key = parts[1].strip().lower()
            neigh = assoc_neighbors(A, key, depth=2, limit=40)
            if not neigh:
                print(f"(recall) I hold a faint sense of '{key}', but details are sparse.")
                # small reinforcement nudge
                I = {m: rotate(impulse(key), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
                M.learn(key, I, r=CFG["reinforce"]["recall"])
                continue
            text = f"(recall) '{key}' returns as balanced. I remember themes like " + ", ".join(neigh[:6]) + ("..." if len(neigh)>6 else "")
            print(text)
            # reinforce recall neighborhood
            I = {m: rotate(impulse(" ".join([key]+neigh[:6])), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
            for t in set([key]+neigh[:6]):
                M.learn(t, I, r=CFG["reinforce"]["recall"])
            continue

        if low.startswith("/save"):
            ok1 = ok2 = True
            try: M.save()
            except Exception as e: ok1=False
            try: A.save()
            except Exception as e: ok2=False
            print(f"[OK] saved language={ok1} associations={ok2}")
            continue

        print("[INFO] commands: /state  /goal <stabilize|explore|focus>  /recall <keyword>  /curiosity <on|off|status>  /save  /quit")

    # shutdown
    try:
        corpus.stop(); diary.stop(); autosave.stop(); curiosity.stop()
    except Exception:
        pass
    time.sleep(0.3)
    try:
        M.save(); A.save()
    except Exception:
        pass
    print("[final] saved. Bye.")

if __name__ == "__main__":
    main()
