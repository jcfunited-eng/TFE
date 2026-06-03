# aurelion_core_v9_3a_reflective_diary_continuous.py
# Aurelion v9.3a — Reflective Diary + Self-Reinforcement + Linguistic Core Seed (Continuous Growth)

import json, os, re, sys, time, random, threading
from pathlib import Path
from typing import List, Dict
import numpy as np

CFG = {
    "dims": 96,
    "modalities": ["visual","auditory","smell","taste","touch","emotion","lexical"],
    "alpha": {"STABILIZE":0.60, "EXPLORE":0.55, "FOCUS":0.68},
    "paths": {
        "language": "language_memory.json",
        "assoc": "associations_v9.json",
        "dialogue": "dialogue_memory.json",
        "corpora": "corpora",
        "diary": "logs/diary_v9_3.txt"
    },
    "corpus": {"sleep_between_lines": 0.5, "batch_lines": 3},
    "autosave_sec": 240,           # 4 minutes
    "diary_sec": 900,              # 15 minutes
    "reflect_lines": 2,            # per reflection burst
    "reinforce": {"recall": 0.45, "reflect": 0.35}
}

# ---------------- helpers ----------------
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

# ---------------- lattice ----------------
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

# ---------------- memory ----------------
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

# ---------------- associations ----------------
class Assoc:
    def __init__(self):
        self.path = CFG["paths"]["assoc"]
        self.W: Dict[tuple, float] = {}
        self.delta: List[tuple] = []  # (a,b,new_w,delta)
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
        old = self.W.get(k, 0.0)
        new = old + w
        self.W[k] = new
        self.delta.append((k[0], k[1], new, new - old))
        if len(self.delta) > 5000:
            self.delta = self.delta[-5000:]

    def pop_recent(self, k=40):
        if not self.delta:
            return []
        out = self.delta[-k:]
        return out

    def save(self):
        json.dump({f"{a}||{b}": w for (a, b), w in self.W.items()},
                  open(self.path, "w", encoding="utf-8"), indent=2)

    def top(self, n=8):
        return sorted(self.W.items(), key=lambda kv: kv[1], reverse=True)[:n]

# ---------------- linguistic core seed ----------------
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

# ---------------- continuous corpus loop ----------------
class CorpusLoop(threading.Thread):
    def __init__(self, L: Lattice, M: Memory, A: Assoc, goal_ref):
        super().__init__(daemon=True)
        self.L, self.M, self.A = L, M, A
        self.goal_ref = goal_ref
        self.stop_flag = threading.Event()

    def _files(self) -> List[Path]:
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

    def _line_iter(self):
        files = self._files()
        if not files:
            while not self.stop_flag.is_set():
                yield "quiet harmony and safe space"
        while not self.stop_flag.is_set():
            for p in files:
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                for ln in text.splitlines():
                    s = ln.strip()
                    if s:
                        yield s
            # loop again (continuous)

    def run(self):
        sleep_gap = CFG["corpus"]["sleep_between_lines"]
        batch_k = CFG["corpus"]["batch_lines"]
        accum = []
        for ln in self._line_iter():
            if self.stop_flag.is_set():
                break
            accum.append(ln)
            if len(accum) < batch_k:
                continue
            # process small batch
            text = " ".join(accum)
            impulses = {m: rotate(impulse(text), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
            self.L.stimulate(impulses, a=CFG["alpha"][self.goal_ref()])
            H = entropy(self.L)
            rate = 0.28 + 0.25*H  # adaptive
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

    def stop(self):
        self.stop_flag.set()

# ---------------- diary ----------------
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
            pairs = [((a, b), w) for (a, b), w in self.A.top(4) if a.startswith("text:") and b.startswith("text:")]
            pretty = ", ".join([f"{a[0][5:]}↔{a[1][5:]}" for a, _ in pairs])
            line = f"[{time.strftime('%H:%M:%S')}] Reflecting on {pretty} φ={phi:.2f} H={H:.2f}"
            print(line)
            with open(CFG["paths"]["diary"], "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def stop(self):
        self.stop_flag.set()

# ---------------- autosave ----------------
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

    def stop(self):
        self.stop_flag.set()

# ---------------- recall + reinforcement ----------------
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

def reinforce(M: Memory, A: Assoc, terms: List[str], how="recall"):
    if not terms:
        return
    rate = CFG["reinforce"]["recall"] if how == "recall" else CFG["reinforce"]["reflect"]
    text = " ".join(terms)
    I = {m: rotate(impulse(text), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
    for t in set(terms):
        M.learn(t, I, r=rate)
    # pairwise association bumps
    uniq = list(dict.fromkeys([t for t in terms if t]))
    for i in range(len(uniq)):
        for j in range(i+1, len(uniq)):
            A.bump(f"text:{uniq[i]}", f"text:{uniq[j]}", w=0.06 if how=="recall" else 0.04)

# ---------------- main shell ----------------
def main():
    print("Aurelion v9.3a — Reflective Diary + Self-Reinforcement + Linguistic Core Seed (Continuous Growth)")
    L = Lattice()
    M = Memory()
    A = Assoc()
    seed_words(M)

    goal = "STABILIZE"

    # background loops
    corpus = CorpusLoop(L, M, A, goal_ref=lambda: goal); corpus.start()
    diary  = DiaryLoop(L, A); diary.start()
    autosave = AutosaveLoop(M, A); autosave.start()

    print("[loop] corpus=ON (continuous)  diary=ON (15m)  autosave=ON (4m)")
    print("[hint] Put .txt or .md files into ./corpora — it will keep reading forever.")
    print("Commands: /state  /goal <stabilize|explore|focus>  /recall <keyword>  /save  /quit")

    # REPL
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
            print(f"φ={phi:.3f}  H={H:.3f}  |  tokens={len(M.map)}  links={len(A.W)}")
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

        if low.startswith("/recall"):
            parts = msg.split(maxsplit=1)
            if len(parts) < 2:
                print("[recall] usage: /recall <keyword>")
                continue
            key = parts[1].strip().lower()
            neigh = assoc_neighbors(A, key, depth=2, limit=40)
            if not neigh:
                print(f"(recall) I hold a faint sense of '{key}', but details are sparse.")
                reinforce(M, A, [key], how="recall")
                continue
            feel = "balanced"
            text = f"(recall) '{key}' returns as {feel}. I remember themes like " + ", ".join(neigh[:6]) + ("..." if len(neigh)>6 else "")
            print(text)
            reinforce(M, A, [key] + neigh[:6], how="recall")
            continue

        if low.startswith("/save"):
            try: M.save(); A.save(); print("[OK] saved.")
            except Exception as e: print(f"[ERR] save: {e}")
            continue

        print("[INFO] commands: /state  /goal <stabilize|explore|focus>  /recall <keyword>  /save  /quit")

    # shutdown
    try:
        corpus.stop(); diary.stop(); autosave.stop()
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
