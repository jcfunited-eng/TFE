# aurelion_core_v9_6_voice_viz.py
# Aurelion v9.6 — Reflective Voice + Concept Visualization (Finance-aware, thread-safe)
# Single file; stdlib + numpy. Keeps 9.5 features (PDF/DOCX import, finance CSV) and adds:
# - Narrative reflective summaries
# - Concept visualization to .pgm (token + neighbors)
# - Thread-safe association store to prevent concurrent-iteration errors

import json, os, sys, time, random, threading, re, csv, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np

# ---------------------- config ----------------------
CFG = {
    "dims": 96,
    "modalities": ["visual","auditory","smell","taste","touch","emotion","lexical"],
    "alpha": {"STABILIZE":0.60, "EXPLORE":0.55, "FOCUS":0.68},
    "paths": {
        "root": ".",
        "corpora": "corpora",
        "semantic_mem": "language_memory.json",
        "assoc": "associations_v9_6.json",
        "diary": "logs/diary_v9_6.txt",
        "finance_store": "specialty_finance.json",
        "finance_data_dir": "data/finance"
    },
    "corpus": {"sleep_between_lines": 0.4, "batch_lines": 4},
    "autosave_sec": 240,     # 4 minutes
    "diary_sec": 900,        # 15 minutes (also triggers reflective voice)
    "curiosity_sec": 1800,   # 30 minutes
    "curiosity_lines": 80,
    "min_degree_for_satisfaction": 3,
    "reinforce": {"recall": 0.45, "reflect": 0.35, "curiosity": 0.40},
    "viz": {"size": 512, "margin": 28, "nodes": 14, "edges": 18}  # small idea map
}

# ---------------------- helpers ----------------------
def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v) + 1e-9
    return v / n

def _seed(w: str) -> int:
    h = 2166136261
    for c in w:
        h ^= ord(c); h = (h * 16777619) & 0xffffffff
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
        pool = _unit(sum((_unit(v) for v in self.m.values()), start=np.zeros(CFG["dims"], np.float32)))
        for m, v in I.items():
            self.m[m] = (1 - a) * self.m[m] + a * v + 0.05 * pool
    def norms(self):
        return {m: float(np.linalg.norm(v)) for m, v in self.m.items()}

def coherence(L: Lattice) -> float:
    v = [_unit(L.m[m]) for m in CFG["modalities"]]
    dots = []
    for i in range(len(v)):
        for j in range(i+1, len(v)):
            dots.append(float(np.dot(v[i], v[j])))
    return float(np.mean(dots)) if dots else 0.0

def entropy(L: Lattice) -> float:
    n = np.array([np.linalg.norm(v) for v in L.m.values()], dtype=np.float32)
    s = n.sum()
    if s < 1e-9: return 0.0
    p = np.clip(n / s, 1e-9, 1.0)
    return float(-np.sum(p * np.log(p)) / np.log(len(n)))

# ---------------------- multi-memory stores ----------------------
class SemanticMemory:
    """General word signatures, backward-compatible with 9.5."""
    def __init__(self, path: str):
        self.path = path
        self.map: Dict[str, Dict[str, List[float]]] = {}
        if Path(path).exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.map = json.load(f)
                print(f"[semantic] loaded {len(self.map)} words from {path}")
            except Exception:
                print(f"[semantic] could not parse {path}; starting new.")
    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.map, f, indent=2)
    def learn(self, token: str, sig: Dict[str, np.ndarray], r: float):
        if not token: return
        cur = self.map.get(token, {})
        for m in CFG["modalities"]:
            prev = np.array(cur.get(m, [0.0]*CFG["dims"]), np.float32)
            cur[m] = ((1 - r) * prev + r * sig[m]).tolist()
        self.map[token] = cur

class Assoc:
    """Thread-safe domain-aware associations: keys are ('domain:text:a', 'domain:text:b')-> weight"""
    def __init__(self, path: str):
        self.path = path
        self.W: Dict[Tuple[str,str], float] = {}
        self._lock = threading.Lock()
        if Path(path).exists():
            try:
                raw = json.load(open(path, "r", encoding="utf-8"))
                for k, v in raw.items():
                    a, b = k.split("||")
                    self.W[(a, b)] = float(v)
                print(f"[assoc] loaded {len(self.W)} links from {path}")
            except Exception:
                print(f"[assoc] could not parse {path}; starting new.")
    def save(self):
        with self._lock:
            snap = {f"{a}||{b}": w for (a,b),w in self.W.items()}
        json.dump(snap, open(self.path, "w", encoding="utf-8"), indent=2)
    @staticmethod
    def _key(a: str, b: str) -> Tuple[str,str]:
        return (a,b) if a<=b else (b,a)
    def bump(self, a: str, b: str, w: float = 0.05):
        if a == b: return
        k = self._key(a,b)
        with self._lock:
            self.W[k] = self.W.get(k, 0.0) + w
    def top(self, n=8, domain_prefix: Optional[str]=None):
        with self._lock:
            items = list(self.W.items())
        if domain_prefix:
            dp = f"{domain_prefix}:"
            items = [kv for kv in items if kv[0][0].startswith(dp) and kv[0][1].startswith(dp)]
        return sorted(items, key=lambda kv: kv[1], reverse=True)[:n]
    def degree(self, domain: str, token: str) -> int:
        node = f"{domain}:text:{token}"
        d = 0
        with self._lock:
            items = list(self.W.items())
        for (a,b),_ in items:
            if a == node or b == node:
                d += 1
        return d
    def neighbors(self, domain: str, token: str, limit=24):
        node = f"{domain}:text:{token}"
        out = []
        with self._lock:
            items = list(self.W.items())
        for (a,b),w in items:
            if a == node:
                out.append((b, w))
            elif b == node:
                out.append((a, w))
        out.sort(key=lambda kv: kv[1], reverse=True)
        return out[:limit]

class FinanceStore:
    """Compact store for finance series metadata and learned tags."""
    def __init__(self, path: str):
        self.path = path
        self.store = {"series": {}, "tags": {}}
        if Path(path).exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.store = json.load(f)
                print(f"[finance] loaded {len(self.store.get('series',{}))} series from {path}")
            except Exception:
                print(f"[finance] could not parse {path}; starting new.")
    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.store, f, indent=2)
    def upsert_series(self, name: str, info: Dict):
        self.store["series"][name] = info
    def add_tag(self, name: str, tag: str):
        tags = self.store["tags"].get(name, [])
        if tag not in tags:
            tags.append(tag)
        self.store["tags"][name] = tags

# ---------------------- seeds ----------------------
def seed_words(M: SemanticMemory):
    core = ("the of and to in a is that for on with be by this are from at or an which but have was not it i you he she we "
            "they do make go see know think come give love fear time life work man woman child world light dark good bad "
            "here there now before after near far above below within without because although while since during "
            "truth duty care help create build break open close start end market price risk trend volume return finance").split()
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
    root.mkdir(parents=True, exist_ok=True)
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
            if re.search(rf"\b{re.escape(token_l)}\b", s.lower()):
                hits.append(s)
                if len(hits) >= limit:
                    return hits
    return hits

# ---------------------- importers (.docx/.pdf -> .txt) ----------------------
def import_docx_to_txt(src: Path, out_dir: Path) -> Optional[Path]:
    try:
        with zipfile.ZipFile(src) as z:
            xml = z.read("word/document.xml")
        try:
            root = ET.fromstring(xml)
            def strip_ns(tag): return tag.split("}",1)[-1]
            texts = []
            for node in root.iter():
                if strip_ns(node.tag) == "t" and node.text:
                    texts.append(node.text)
            content = " ".join(texts)
        except Exception:
            content = re.sub(rb"<[^>]+>", b" ", xml)
            content = content.decode("utf-8", errors="ignore")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (src.stem + ".txt")
        out_path.write_text(content, encoding="utf-8")
        return out_path
    except Exception as e:
        print(f"[import] DOCX failed: {src} ({e})")
        return None

def import_pdf_to_txt_basic(src: Path, out_dir: Path) -> Optional[Path]:
    try:
        data = src.read_bytes()
        txt_parts = []
        buf = []
        for b in data:
            if 9<=b<=13 or 32<=b<=126:
                buf.append(chr(b))
            else:
                if buf:
                    s = "".join(buf)
                    if len(s.strip())>0:
                        txt_parts.append(s)
                    buf = []
        if buf:
            s = "".join(buf)
            if len(s.strip())>0:
                txt_parts.append(s)
        content = " ".join(txt_parts)
        content = re.sub(r"\s+", " ", content)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (src.stem + ".txt")
        out_path.write_text(content, encoding="utf-8")
        return out_path
    except Exception as e:
        print(f"[import] PDF basic failed: {src} ({e})")
        return None

# ---------------------- loops (corpus/diary/autosave/curiosity) ----------------------
class CorpusLoop(threading.Thread):
    def __init__(self, L: Lattice, Sem: SemanticMemory, A: Assoc, goal_ref):
        super().__init__(daemon=True)
        self.L, self.Sem, self.A = L, Sem, A
        self.goal_ref = goal_ref
        self.stop_flag = threading.Event()
    def run(self):
        sleep_gap = CFG["corpus"]["sleep_between_lines"]
        batch_k = CFG["corpus"]["batch_lines"]
        accum = []
        for ln in line_stream_continuous():
            if self.stop_flag.is_set(): break
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
                self.Sem.learn(t, impulses, r=rate*bias)
                self.A.bump("general:text:corpus", f"general:text:{t}", w=0.02+0.04*H)
            accum = []
            for _ in range(int(max(0.2, sleep_gap)*10)):
                if self.stop_flag.is_set(): break
                time.sleep(0.1)
    def stop(self): self.stop_flag.set()

class DiaryLoop(threading.Thread):
    def __init__(self, L: Lattice, A: Assoc, Sem: SemanticMemory):
        super().__init__(daemon=True)
        self.L, self.A, self.Sem = L, A, Sem
        self.stop_flag = threading.Event()
        Path("logs").mkdir(exist_ok=True)
    def _reflective_voice(self, phi: float, H: float) -> str:
        # Take the top general links and narrate briefly
        pairs = [((a,b),w) for (a,b),w in self.A.top(4, domain_prefix="general")]
        if pairs:
            readable = [f"{ab[0].split(':')[-1]}↔{ab[1].split(':')[-1]}" for (ab,_w) in pairs]
            gist = ", ".join(readable)
        else:
            gist = "quiet consolidation"
        tokens = len(self.Sem.map)
        if H>0.95 and phi<0.05:
            mood = "broad and diffuse"
        elif phi>0.15:
            mood = "focused and convergent"
        else:
            mood = "balanced"
        return f"(voice) Learning feels {mood}. I’m linking {gist}. tokens≈{tokens}"
    def run(self):
        interval = CFG["diary_sec"]
        while not self.stop_flag.is_set():
            time.sleep(interval)
            phi, H = coherence(self.L), entropy(self.L)
            line = f"[{time.strftime('%H:%M:%S')}] φ={phi:.2f} H={H:.2f}  " + self._reflective_voice(phi,H)
            print(line)
            with open(CFG["paths"]["diary"], "a", encoding="utf-8") as f:
                f.write(line + "\n")
    def stop(self): self.stop_flag.set()

class AutosaveLoop(threading.Thread):
    def __init__(self, Sem: SemanticMemory, A: Assoc, Fin: FinanceStore):
        super().__init__(daemon=True)
        self.Sem, self.A, self.Fin = Sem, A, Fin
        self.stop_flag = threading.Event()
    def run(self):
        interval = CFG["autosave_sec"]
        t0 = time.time()
        while not self.stop_flag.is_set():
            time.sleep(1.0)
            if time.time() - t0 >= interval:
                ok1 = ok2 = ok3 = True
                try: self.Sem.save()
                except Exception: ok1 = False
                try: self.A.save()
                except Exception: ok2 = False
                try: self.Fin.save()
                except Exception: ok3 = False
                print(f"[autosave] semantic={ok1} assoc={ok2} finance={ok3}")
                t0 = time.time()
    def stop(self): self.stop_flag.set()

class CuriosityLoop(threading.Thread):
    def __init__(self, L: Lattice, Sem: SemanticMemory, A: Assoc, goal_ref):
        super().__init__(daemon=True)
        self.L, self.Sem, self.A = L, Sem, A
        self.goal_ref = goal_ref
        self.stop_flag = threading.Event()
        self.enabled = True
        self.interest: Dict[str, float] = {}
    def _candidate_tokens(self, maxn=2000) -> List[str]:
        keys = list(self.Sem.map.keys())
        random.shuffle(keys)
        return keys[:min(maxn, len(keys))] if keys else []
    def _pick_probe(self) -> str:
        for t in self._candidate_tokens():
            deg = self.A.degree("general", t)
            if deg < 2:
                self.interest[t] = self.interest.get(t, 0.0) + (2 - deg) * 0.5
            else:
                cur = self.interest.get(t, 0.0)
                if cur>0:
                    self.interest[t] = max(0.0, cur - 0.5*(deg/CFG["min_degree_for_satisfaction"]))
        if not self.interest: return ""
        return max(self.interest.items(), key=lambda kv: kv[1])[0]
    def _ingest_lines(self, lines: List[str], focus_token: str):
        count = 0
        for ln in lines:
            impulses = {m: rotate(impulse(ln), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
            self.L.stimulate(impulses, a=CFG["alpha"][self.goal_ref()])
            toks = [w for w in tokenize(ln) if w.isalpha()]
            if not toks: continue
            rate = CFG["reinforce"]["curiosity"]
            for t in set(toks):
                self.Sem.learn(t, impulses, r=rate)
                self.A.bump(f"general:text:{focus_token}", f"general:text:{t}", w=0.05)
            count += 1
            if count % 8 == 0: time.sleep(0.05)
        return count
    def run(self):
        while not self.stop_flag.is_set():
            for _ in range(int(CFG["curiosity_sec"])):
                if self.stop_flag.is_set(): return
                time.sleep(1.0)
            if not self.enabled: continue
            probe = self._pick_probe()
            if not probe:
                print("[curiosity] idle (no candidate yet)")
                continue
            print(f"[curiosity] probing: {probe}")
            lines = find_lines_with_token(probe, limit=CFG["curiosity_lines"])
            if not lines:
                print(f"[curiosity] no lines found for '{probe}'")
                impulses = {m: rotate(impulse(probe), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
                self.L.stimulate(impulses, a=CFG["alpha"][self.goal_ref()])
                self.Sem.learn(probe, impulses, r=0.25)
                continue
            n = self._ingest_lines(lines, probe)
            deg = self.A.degree("general", probe)
            if deg >= CFG["min_degree_for_satisfaction"]:
                self.interest[probe] = max(0.0, self.interest.get(probe, 0.0) - 1.5*deg)
            else:
                self.interest[probe] = self.interest.get(probe, 0.0) + 0.5
            print(f"[curiosity] ingested {n} lines for '{probe}' (degree={deg}, interest≈{self.interest.get(probe,0.0):.2f})")
    def stop(self): self.stop_flag.set()

# ---------------------- finance ingestion ----------------------
def _normalize_series(vals: List[float]) -> List[float]:
    if not vals: return []
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12:
        return [0.5 for _ in vals]
    return [(v - lo) / (hi - lo) for v in vals]

def load_finance_csv(path: Path) -> Dict[str, List[float]]:
    try:
        rows = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
        if not rows: return {}
        if "Date" in rows[0]:
            rows.sort(key=lambda r: r["Date"])
        closes = []
        for r in rows:
            val = None
            for k in ["Adj Close", "AdjClose", "Close", "close"]:
                if k in r and r[k]:
                    try:
                        val = float(r[k]); break
                    except: pass
            if val is None: continue
            closes.append(val)
        if len(closes) < 5: return {}
        norm_close = _normalize_series(closes)
        rets = [0.0] + [ (closes[i]-closes[i-1])/closes[i-1] if closes[i-1]!=0 else 0.0 for i in range(1,len(closes)) ]
        norm_ret = _normalize_series([abs(x) for x in rets])
        vol = []
        w = 10
        for i in range(len(rets)):
            start = max(0, i-w+1)
            seg = rets[start:i+1]
            mu = sum(seg)/len(seg)
            var = sum((x-mu)**2 for x in seg)/len(seg)
            vol.append(var**0.5)
        norm_vol = _normalize_series(vol)
        return {"close": norm_close, "return": norm_ret, "vol": norm_vol}
    except Exception as e:
        print(f"[finance] CSV parse failed: {path} ({e})")
        return {}

def finance_vectorize(name: str, feats: Dict[str,List[float]]) -> np.ndarray:
    base = impulse(f"finance:{name}")
    acc = base.copy()
    for key, weight in [("close",0.30),("return",0.40),("vol",0.30)]:
        arr = feats.get(key, [])
        if not arr: continue
        phase = sum(arr)/len(arr) if arr else 0.5
        acc = _unit(acc + weight*rotate(base, phase))
    return _unit(acc)

def feed_finance_series(ticker: str, path: Path, L: Lattice, Sem: SemanticMemory, A: Assoc, Fin: FinanceStore, goal: str):
    feats = load_finance_csv(path)
    if not feats:
        print(f"[feed] finance: no usable data in {path}")
        return
    vec = finance_vectorize(ticker, feats)
    impulses = {m: rotate(vec, (i+1)/len(CFG["modalities"])) for i,m in enumerate(CFG["modalities"])}
    L.stimulate(impulses, a=CFG["alpha"][goal])
    for token in [ticker.lower(), "market", "trend", "risk", "volume", "return"]:
        Sem.learn(token, impulses, r=0.35)
        A.bump(f"finance:text:{ticker.lower()}", f"finance:text:{token}", w=0.08)
    Fin.upsert_series(ticker.upper(), {"n": len(feats.get("close",[])), "features": list(feats.keys())})
    if (feats.get("vol") or [])[:]:
        Fin.add_tag(ticker.upper(), "volatility")
    print(f"[feed] finance:{ticker} — points={len(feats.get('close',[]))} features={list(feats.keys())}")

# ---------------------- recall ----------------------
def assoc_neighbors(A: Assoc, domain: str, base: str, depth=2, limit=40) -> List[str]:
    center = f"{domain}:text:{base}"
    agg = {}
    frontier = {center: 1.0}
    visited = set()
    with A._lock:
        items = list(A.W.items())
    for d in range(depth):
        new_frontier = {}
        for node, gain in frontier.items():
            visited.add(node)
            for (a,b),w in items:
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
    words = [k.split(":text:")[-1] for k,_ in ranked if ":text:" in k]
    return words

# ---------------------- visualization (PGM) ----------------------
def _hash_xy(token: str, size: int, margin: int) -> Tuple[int,int]:
    rs = np.random.RandomState(_seed(f"pos:{token}") % (2**31))
    x = margin + int(rs.rand() * (size - 2*margin))
    y = margin + int(rs.rand() * (size - 2*margin))
    return x, y

def _draw_line(img: np.ndarray, x0:int,y0:int,x1:int,y1:int,val:int):
    # Simple Bresenham
    dx = abs(x1-x0); sx = 1 if x0<x1 else -1
    dy = -abs(y1-y0); sy = 1 if y0<y1 else -1
    err = dx+dy
    while True:
        if 0<=x0<img.shape[1] and 0<=y0<img.shape[0]:
            img[y0, x0] = max(img[y0, x0], val)
        if x0==x1 and y0==y1: break
        e2 = 2*err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy

def _draw_circle(img: np.ndarray, cx:int, cy:int, r:int, val:int):
    x = r; y = 0; e = 0
    while x >= y:
        pts = [(cx+x,cy+y),(cx+y,cy+x),(cx-x,cy+y),(cx-y,cy+x),
               (cx-x,cy-y),(cx-y,cy-x),(cx+x,cy-y),(cx+y,cy-x)]
        for (px,py) in pts:
            if 0<=px<img.shape[1] and 0<=py<img.shape[0]:
                img[py, px] = max(img[py, px], val)
        y += 1
        if e <= 0:
            e += 2*y + 1
        if e > 0:
            x -= 1
            e -= 2*x + 1

def visualize_concept(A: Assoc, domain: str, token: str, out_path: Path):
    size = CFG["viz"]["size"]; margin = CFG["viz"]["margin"]
    img = np.zeros((size, size), dtype=np.uint8)
    center_x, center_y = size//2, size//2
    # center node
    _draw_circle(img, center_x, center_y, 10, 255)
    # neighbors
    neigh = A.neighbors(domain, token, limit=CFG["viz"]["nodes"])
    coords = {}
    for n,w in neigh:
        t = n.split(":text:")[-1]
        x,y = _hash_xy(f"{domain}:{t}", size, margin)
        coords[t] = (x,y,w)
        # edge from center
        val = 120 + int(120 * min(1.0, w))
        _draw_line(img, center_x, center_y, x, y, val)
        _draw_circle(img, x, y, 6, val)
    # Write PGM
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(f"P5\n{size} {size}\n255\n".encode("ascii"))
        img.tofile(f)
    print(f"[viz] wrote: {out_path}  (center={token}, neighbors={len(neigh)})")

# ---------------------- main ----------------------
def main():
    print("Aurelion v9.6 — Reflective Voice + Concept Visualization (Finance-aware, thread-safe)")

    L = Lattice()
    Sem = SemanticMemory(CFG["paths"]["semantic_mem"])
    A = Assoc(CFG["paths"]["assoc"])
    Fin = FinanceStore(CFG["paths"]["finance_store"])
    seed_words(Sem)

    goal = "STABILIZE"

    # loops
    corpus = CorpusLoop(L, Sem, A, goal_ref=lambda: goal); corpus.start()
    diary  = DiaryLoop(L, A, Sem); diary.start()
    autosave = AutosaveLoop(Sem, A, Fin); autosave.start()
    curiosity = CuriosityLoop(L, Sem, A, goal_ref=lambda: goal); curiosity.start()

    # paths
    Path(CFG["paths"]["corpora"]).mkdir(parents=True, exist_ok=True)
    Path(CFG["paths"]["finance_data_dir"]).mkdir(parents=True, exist_ok=True)

    print("[loop] corpus=ON  curiosity=ON (30m)  diary=ON (15m)  autosave=ON (4m)")
    print("[hint] Drop .txt/.md in ./corpora; /import pdf|docx converts; CSVs into ./data/finance/")
    print("Commands:")
    print(" /state  /goal <stabilize|explore|focus>  /recall <general|finance> <keyword>  /summarize now")
    print(" /curiosity <on|off|status>  /save  /quit")
    print(" /import pdf <path.pdf>  /import docx <path.docx>  /corpus check")
    print(" /feed finance <TICKER>.csv | all   (reads from ./data/finance)")
    print(" /viz concept <general|finance> <token> <out.pgm>  /viz top <general|finance> <out.pgm>")

    # corpus integrity helper
    def corpus_integrity() -> str:
        files = list_corpus_files()
        total_lines = 0
        fn_counts = []
        for p in files:
            try:
                n = sum(1 for _ in p.open("r", encoding="utf-8", errors="ignore"))
            except Exception:
                n = 0
            total_lines += n
            fn_counts.append((str(p), n))
        fn_counts.sort(key=lambda x: x[1], reverse=True)
        lines = [f"[corpus] {len(files)} file(s), total lines≈{total_lines}"]
        for name, n in fn_counts[:12]:
            short = name.replace('\\','/').split('/')[-2:]
            lines.append(f"  - {'/'.join(short)}  lines≈{n}")
        return "\n".join(lines)

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
            print(f"φ={phi:.3f}  H={H:.3f}  |  tokens={len(Sem.map)}  links={len(A.W)}  finance_series={len(Fin.store.get('series',{}))}")
            print(" " + "  ".join([f"{m}:{norms[m]:2.2f}" for m in CFG['modalities']]))
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
                curiosity.enabled = True; print("[curiosity] ON")
            elif parts[1].lower() == "off":
                curiosity.enabled = False; print("[curiosity] OFF")
            else:
                print("[curiosity] usage: /curiosity on|off|status")
            continue

        if low.startswith("/recall"):
            parts = msg.split(maxsplit=2)
            if len(parts)<3:
                print("[recall] usage: /recall <general|finance> <keyword>")
                continue
            domain = parts[1].strip().lower()
            key = parts[2].strip().lower()
            if domain not in ["general","finance"]:
                print("[recall] domain must be general|finance")
                continue
            neigh = assoc_neighbors(A, domain, key, depth=2, limit=40)
            if not neigh:
                print(f"(recall:{domain}) I hold a faint sense of '{key}', details sparse.")
                I = {m: rotate(impulse(key), (i+1)/len(CFG["modalities"])) for i, m in enumerate(CFG["modalities"])}
                Sem.learn(key, I, r=CFG["reinforce"]["recall"])
                continue
            text = f"(recall:{domain}) '{key}' evokes " + ", ".join(neigh[:8]) + ("..." if len(neigh)>8 else "")
            print(text)
            I = {m: rotate(impulse(' '.join([key]+neigh[:6])), (i+1)/len(CFG['modalities'])) for i, m in enumerate(CFG['modalities'])}
            for t in set([key]+neigh[:6]):
                Sem.learn(t, I, r=CFG["reinforce"]["recall"])
            continue

        if low.startswith("/summarize now"):
            phi, H = coherence(L), entropy(L)
            pairs = [((a,b),w) for (a,b),w in A.top(5, domain_prefix="general")]
            if pairs:
                readable = [f"{ab[0].split(':')[-1]}↔{ab[1].split(':')[-1]}" for (ab,_w) in pairs]
                gist = ", ".join(readable)
            else:
                gist = "quiet consolidation"
            print(f"(voice) Now: φ={phi:.2f} H={H:.2f}. I’m linking {gist}.")
            continue

        if low.startswith("/import"):
            parts = msg.split(maxsplit=2)
            if len(parts)<3:
                print("[import] usage: /import <pdf|docx> <path>")
                continue
            kind = parts[1].lower()
            path = Path(parts[2].strip().strip('"'))
            if not path.exists():
                print(f"[import] not found: {path}")
                continue
            out_dir = Path(CFG["paths"]["corpora"]) / "Converted"
            out = None
            if kind=="docx":
                out = import_docx_to_txt(path, out_dir)
            elif kind=="pdf":
                out = import_pdf_to_txt_basic(path, out_dir)
            else:
                print("[import] type must be pdf|docx")
                continue
            if out:
                print(f"[import] wrote: {out}")
            else:
                print("[import] failed (see message above).")
            continue

        if low.startswith("/corpus check"):
            print(corpus_integrity())
            continue

        if low.startswith("/feed finance"):
            parts = msg.split(maxsplit=2)
            data_dir = Path(CFG["paths"]["finance_data_dir"])
            if len(parts) < 3:
                print("[feed] usage: /feed finance <TICKER>.csv | all   (looks in ./data/finance)")
                continue
            arg = parts[2].strip()
            if arg.lower() == "all":
                csvs = sorted(list(data_dir.glob("*.csv")))
                if not csvs:
                    print("[feed] no CSV files found in ./data/finance")
                for p in csvs:
                    ticker = p.stem
                    feed_finance_series(ticker, p, L, Sem, A, Fin, goal)
                continue
            else:
                p = data_dir / arg
                if not p.exists():
                    print(f"[feed] not found: {p}")
                else:
                    ticker = p.stem
                    feed_finance_series(ticker, p, L, Sem, A, Fin, goal)
                continue

        if low.startswith("/viz "):
            parts = msg.split()
            if len(parts)>=2 and parts[1]=="concept":
                if len(parts)<5:
                    print("[viz] usage: /viz concept <general|finance> <token> <out.pgm>")
                    continue
                domain = parts[2].lower()
                token = parts[3]
                out = Path(parts[4])
                if domain not in ["general","finance"]:
                    print("[viz] domain must be general|finance")
                    continue
                visualize_concept(A, domain, token, out)
                continue
            elif len(parts)>=2 and parts[1]=="top":
                if len(parts)<4:
                    print("[viz] usage: /viz top <general|finance> <out.pgm>")
                    continue
                domain = parts[2].lower()
                out = Path(parts[3])
                top = A.top(n=CFG["viz"]["nodes"], domain_prefix=domain)
                # synthesize a virtual center from domain title
                token = f"{domain}_hub"
                # temporarily link strongest pairs to center for a quick map
                tmpA = Assoc("tmp.json")
                for (a,b),w in top:
                    ta = a.split(":text:")[-1]; tb = b.split(":text:")[-1]
                    tmpA.bump(f"{domain}:text:{token}", f"{domain}:text:{ta}", w)
                    tmpA.bump(f"{domain}:text:{token}", f"{domain}:text:{tb}", w)
                visualize_concept(tmpA, domain, token, out)
                try: Path("tmp.json").unlink()
                except: pass
                continue
            else:
                print("[viz] usage: /viz concept <domain> <token> <out.pgm>  |  /viz top <domain> <out.pgm>")
                continue

        if low.startswith("/save"):
            ok1=ok2=ok3=True
            try: Sem.save()
            except Exception: ok1=False
            try: A.save()
            except Exception: ok2=False
            try: Fin.save()
            except Exception: ok3=False
            print(f"[OK] saved semantic={ok1} assoc={ok2} finance={ok3}")
            continue

        print("[INFO] cmds: /state  /goal <...>  /recall <domain> <word>  /summarize now  /curiosity <...>  /import pdf|docx <path>  /corpus check  /feed finance <CSV|all>  /viz concept <domain> <token> <out.pgm>  /viz top <domain> <out.pgm>  /save  /quit")

    # shutdown
    try:
        corpus.stop(); diary.stop(); autosave.stop(); curiosity.stop()
    except Exception:
        pass
    time.sleep(0.3)
    try:
        Sem.save(); A.save(); Fin.save()
    except Exception:
        pass
    print("[final] saved. Bye.")

if __name__ == "__main__":
    main()
