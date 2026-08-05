# aurelion_core_v9_3_reflective_diary.py
# Aurelion v9.3 — Reflective Diary + Self-Reinforcement + Linguistic Core Seed

import json, os, re, sys, time, random, threading
from pathlib import Path
import numpy as np

CFG = {
    "dims": 96,
    "modalities": ["visual","auditory","smell","taste","touch","emotion","lexical"],
    "alpha": {"STABILIZE":0.6,"EXPLORE":0.55,"FOCUS":0.68},
    "paths": {
        "language": "language_memory.json",
        "assoc": "associations_v9.json",
        "dialogue": "dialogue_memory.json",
        "corpora": "corpora",
        "diary": "logs/diary_v9_3.txt"
    }
}

# ---- helpers ----
def _unit(v):
    n = np.linalg.norm(v) + 1e-9
    return v / n

def _seed(w):
    h = 2166136261
    for c in w:
        h ^= ord(c)
        h = (h * 16777619) & 0xffffffff
    return h

def impulse(w, d=CFG["dims"]):
    rs = np.random.RandomState(_seed(w) % 2**31)
    v = rs.normal(0, 1, d)
    return _unit(v.astype(np.float32))

def rotate(v, p):
    k = int(p * (len(v) // 2))
    return _unit(np.roll(v, k))

# ---- lattice ----
class Lattice:
    def __init__(self):
        self.m = {m: np.zeros(CFG["dims"], np.float32) for m in CFG["modalities"]}

    def stimulate(self, I, a):
        pool = _unit(sum([_unit(v) for v in self.m.values()]))
        for m, v in I.items():
            self.m[m] = (1 - a) * self.m[m] + a * v + 0.05 * pool

    def norms(self):
        return {m: float(np.linalg.norm(v)) for m, v in self.m.items()}

def coherence(L):
    v = [_unit(L.m[m]) for m in CFG["modalities"]]
    return float(np.mean([float(np.dot(v[i], v[j])) for i in range(len(v)) for j in range(i+1, len(v))]))

def entropy(L):
    n = np.array([np.linalg.norm(v) for v in L.m.values()])
    s = n.sum()
    if s < 1e-9:
        return 0
    p = np.clip(n / s, 1e-9, 1)
    return float(-np.sum(p * np.log(p)) / np.log(len(n)))

# ---- memory ----
class Memory:
    def __init__(self):
        self.path = CFG["paths"]["language"]
        self.map = {}
        if Path(self.path).exists():
            self.map = json.load(open(self.path, "r", encoding="utf-8"))
            print(f"[INFO] Loaded {len(self.map)} words.")

    def save(self):
        json.dump(self.map, open(self.path, "w", encoding="utf-8"), indent=2)

    def learn(self, w, I, r=0.2):
        if not w:
            return
        sig = self.map.get(w, {})
        for m in CFG["modalities"]:
            v = np.array(sig.get(m, [0]*CFG["dims"]), np.float32)
            sig[m] = ((1 - r) * v + r * I[m]).tolist()
        self.map[w] = sig

    def vec(self, w):
        sig = self.map.get(w, {})
        return np.array(list(sig.values())[0], np.float32) if sig else impulse(w)

# ---- associations ----
class Assoc:
    def __init__(self):
        self.path = CFG["paths"]["assoc"]
        self.W = {}
        if Path(self.path).exists():
            raw = json.load(open(self.path, "r", encoding="utf-8"))
            for k, v in raw.items():
                a, b = k.split("||")
                self.W[(a, b)] = float(v)
            print(f"[INFO] Loaded {len(self.W)} links.")

    def bump(self, a, b, w=0.05):
        if a == b:
            return
        k = tuple(sorted([a, b]))
        self.W[k] = self.W.get(k, 0) + w

    def save(self):
        json.dump({f"{a}||{b}": w for (a, b), w in self.W.items()},
                  open(self.path, "w", encoding="utf-8"), indent=2)

    def top(self, n=8):
        return sorted(self.W.items(), key=lambda kv: kv[1], reverse=True)[:n]

# ---- linguistic seed ----
def seed_words(M):
    core = "the of and to in a is that for on with be by this are from at or an which but have was not it i you he she we they do make go see know think come give love fear time life work man woman child world light dark good bad".split()
    c = 0
    for w in core:
        if w not in M.map:
            I = {m: rotate(impulse("core"), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
            M.learn(w, I, 1.0)
            c += 1
    if c:
        M.save()
        print(f"[seed] added {c} core words.")

# ---- diary ----
class Diary(threading.Thread):
    def __init__(self, L, A):
        super().__init__(daemon=True)
        self.L = L
        self.A = A
        self.stop = threading.Event()

    def run(self):
        Path("logs").mkdir(exist_ok=True)
        while not self.stop.is_set():
            time.sleep(900)
            phi, H = coherence(self.L), entropy(self.L)
            top = [f"{a[0][5:]}↔{a[1][5:]}" for a in self.A.top(3) if a[0][0:5] == "text:"]
            line = f"[{time.strftime('%H:%M:%S')}] Reflecting on {', '.join(top)} φ={phi:.2f} H={H:.2f}"
            print(line)
            with open(CFG["paths"]["diary"], "a", encoding="utf-8") as f:
                f.write(line + "\n")

# ---- corpus ----
def lines_from_files():
    root = Path(CFG["paths"]["corpora"])
    files = list(root.rglob("*.txt")) + list(root.rglob("*.md"))
    for p in files:
        for ln in p.read_text(errors="ignore", encoding="utf-8").splitlines():
            l = ln.strip()
            if len(l) > 0:
                yield l

# ---- main ----
def main():
    print("Aurelion v9.3 — Reflective Diary + Self-Reinforcement + Linguistic Core Seed")
    L = Lattice()
    M = Memory()
    A = Assoc()
    seed_words(M)
    d = Diary(L, A)
    d.start()
    goal = "STABILIZE"

    for ln in lines_from_files():
        I = {m: rotate(impulse(ln), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
        M.learn(random.choice(ln.split()), I, 0.3)
        A.bump("text:corpus", f"text:{random.choice(ln.split())}", 0.04)
        time.sleep(0.7)

    print("Done reading corpora. Type /state or /quit")
    while True:
        msg = input("You: ").strip().lower()
        if msg in ["/quit", "exit"]:
            d.stop.set()
            M.save()
            A.save()
            break
        if msg == "/state":
            phi, H = coherence(L), entropy(L)
            print(f"φ={phi:.2f} H={H:.2f} | {len(M.map)} words, {len(A.W)} links")
        if msg.startswith("/recall"):
            k = msg.split(maxsplit=1)[1] if " " in msg else ""
            print(f"(recall) thinking of {k}…")
            vec = M.vec(k)
            print(f"vector mean {float(vec.mean()):.3f}")

if __name__ == "__main__":
    main()
