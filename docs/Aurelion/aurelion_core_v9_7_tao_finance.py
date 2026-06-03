# aurelion_core_v9_7_tao_finance.py
# Aurelion v9.7 — Tao Finance Extension Core (Mom Mode, concise /summary mom)
# - Fix: Windows-safe ticker normalization (^IXIC -> IXIC) for file lookups
# - Fix: Robust portfolio report with missing/partial data
# - Add: /summary mom (concise one-line daily snapshot)
# - Keep: Mom Mode auto-updater, insights, watchlist, portfolio, docx/pdf import, visualization
# No external dependencies beyond numpy.

import json, os, sys, time, random, threading, re, csv, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
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
        "diary": "logs/diary_v9_7.txt",
        "finance_store": "specialty_finance.json",
        "finance_data_dir": "data/finance",
        "watchlist": "data/finance/watchlist.txt",
        "portfolio": "data/finance/portfolio.json"
    },
    "corpus": {"sleep_between_lines": 0.4, "batch_lines": 4},
    "autosave_sec": 240,
    "diary_sec": 900,
    "curiosity_sec": 1800,
    "curiosity_lines": 80,
    "min_degree_for_satisfaction": 3,
    "reinforce": {"recall": 0.45, "reflect": 0.35, "curiosity": 0.40},
    "viz": {"size": 512, "margin": 28, "nodes": 14},
    "auto_update_sec": 900,
    "insight_windows": [7, 30, 90],
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

def is_business_day(dt: datetime) -> bool:
    return dt.weekday() < 5

def next_business_day(dt: datetime) -> datetime:
    t = dt + timedelta(days=1)
    while not is_business_day(t):
        t += timedelta(days=1)
    return t

def norm_ticker_to_filename(t: str) -> str:
    # Windows-safe: remove characters commonly troublesome in filenames (^, /, \, :, *, ?, ", <, >, |)
    return re.sub(r'[\^\:/\\\*\?"<>\|]+', '', t)

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
    def __init__(self, path: str):
        self.path = path
        self.map: Dict[str, Dict[str, List[float]]] = {}
        if Path(path).exists():
            try:
                self.map = json.load(open(path, "r", encoding="utf-8"))
                print(f"[semantic] loaded {len(self.map)} words from {path}")
            except Exception:
                print(f"[semantic] could not parse {path}; starting new.")
    def save(self):
        json.dump(self.map, open(self.path, "w", encoding="utf-8"), indent=2)
    def learn(self, token: str, sig: Dict[str, np.ndarray], r: float):
        if not token: return
        cur = self.map.get(token, {})
        for m in CFG["modalities"]:
            prev = np.array(cur.get(m, [0.0]*CFG["dims"]), np.float32)
            cur[m] = ((1 - r) * prev + r * sig[m]).tolist()
        self.map[token] = cur

class Assoc:
    def __init__(self, path: str):
        self.path = path
        self.W: Dict[Tuple[str,str], float] = {}
        self._lock = threading.Lock()
        if Path(path).exists():
            try:
                raw = json.load(open(path, "r", encoding="utf-8"))
                for k,v in raw.items():
                    a,b = k.split("||")
                    self.W[(a,b)] = float(v)
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
        if a==b: return
        k = self._key(a,b)
        with self._lock:
            self.W[k] = self.W.get(k, 0.0) + w
    def top(self, n=8, domain_prefix: Optional[str]=None):
        with self._lock: items = list(self.W.items())
        if domain_prefix:
            dp = f"{domain_prefix}:"
            items = [kv for kv in items if kv[0][0].startswith(dp) and kv[0][1].startswith(dp)]
        return sorted(items, key=lambda kv: kv[1], reverse=True)[:n]
    def degree(self, domain: str, token: str) -> int:
        node = f"{domain}:text:{token}"
        d = 0
        with self._lock: items = list(self.W.items())
        for (a,b),_ in items:
            if a==node or b==node: d+=1
        return d
    def neighbors(self, domain: str, token: str, limit=24):
        node = f"{domain}:text:{token}"
        out = []
        with self._lock: items = list(self.W.items())
        for (a,b),w in items:
            if a==node: out.append((b,w))
            elif b==node: out.append((a,w))
        out.sort(key=lambda kv: kv[1], reverse=True)
        return out[:limit]

class FinanceStore:
    def __init__(self, path: str):
        self.path = path
        self.store = {"series": {}, "tags": {}}
        if Path(path).exists():
            try:
                self.store = json.load(open(path, "r", encoding="utf-8"))
                print(f"[finance] loaded {len(self.store.get('series',{}))} series from {path}")
            except Exception:
                print(f"[finance] could not parse {path}; starting new.")
    def save(self):
        json.dump(self.store, open(self.path, "w", encoding="utf-8"), indent=2)
    def upsert_series(self, name: str, info: Dict):
        self.store["series"][name] = info
    def add_tag(self, name: str, tag: str):
        tags = self.store["tags"].get(name, [])
        if tag not in tags: tags.append(tag)
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
            M.learn(w, I, 1.0); c+=1
    if c:
        M.save()
        print(f"[seed] added {c} core words.")

# ---------------------- corpus utilities ----------------------
def list_corpus_files() -> List[Path]:
    root = Path(CFG["paths"]["corpora"]); root.mkdir(parents=True, exist_ok=True)
    files = list(root.rglob("*.txt")) + list(root.rglob("*.md"))
    files.sort(); return files

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
                if s: yield s

def find_lines_with_token(token: str, limit: int) -> List[str]:
    token_l = token.lower(); hits=[]
    for p in list_corpus_files():
        try: text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception: continue
        for ln in text.splitlines():
            s = ln.strip()
            if not s: continue
            if re.search(rf"\b{re.escape(token_l)}\b", s.lower()):
                hits.append(s)
                if len(hits) >= limit: return hits
    return hits

# ---------------------- importers (.docx/.pdf -> .txt) ----------------------
def import_docx_to_txt(src: Path, out_dir: Path) -> Optional[Path]:
    try:
        with zipfile.ZipFile(src) as z: xml = z.read("word/document.xml")
        try:
            root = ET.fromstring(xml)
            def strip_ns(tag): return tag.split("}",1)[-1]
            texts=[]; 
            for node in root.iter():
                if strip_ns(node.tag)=="t" and node.text: texts.append(node.text)
            content = " ".join(texts)
        except Exception:
            content = re.sub(rb"<[^>]+>", b" ", xml).decode("utf-8", errors="ignore")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (src.stem + ".txt")
        out_path.write_text(content, encoding="utf-8")
        return out_path
    except Exception as e:
        print(f"[import] DOCX failed: {src} ({e})"); return None

def import_pdf_to_txt_basic(src: Path, out_dir: Path) -> Optional[Path]:
    try:
        data = src.read_bytes()
        txt_parts=[]; buf=[]
        for b in data:
            if 9<=b<=13 or 32<=b<=126: buf.append(chr(b))
            else:
                if buf:
                    s = "".join(buf)
                    if len(s.strip())>0: txt_parts.append(s)
                    buf=[]
        if buf:
            s="".join(buf)
            if len(s.strip())>0: txt_parts.append(s)
        content = re.sub(r"\s+", " ", " ".join(txt_parts))
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (src.stem + ".txt")
        out_path.write_text(content, encoding="utf-8")
        return out_path
    except Exception as e:
        print(f"[import] PDF basic failed: {src} ({e})"); return None

# ---------------------- loops: corpus/diary/autosave/curiosity ----------------------
class CorpusLoop(threading.Thread):
    def __init__(self, L: Lattice, Sem: SemanticMemory, A: Assoc, goal_ref):
        super().__init__(daemon=True); self.L=L; self.Sem=Sem; self.A=A; self.goal_ref=goal_ref
        self.stop_flag = threading.Event()
    def run(self):
        sleep_gap = CFG["corpus"]["sleep_between_lines"]; batch_k=CFG["corpus"]["batch_lines"]
        accum=[]
        for ln in line_stream_continuous():
            if self.stop_flag.is_set(): break
            accum.append(ln)
            if len(accum) < batch_k: continue
            text = " ".join(accum)
            impulses = {m: rotate(impulse(text), (i+1)/len(CFG["modalities"])) for i,m in enumerate(CFG["modalities"])}
            self.L.stimulate(impulses, a=CFG["alpha"][self.goal_ref()])
            H = entropy(self.L); rate = 0.28 + 0.25*H
            toks = set([t for t in tokenize(text) if t.isalpha()])
            for t in toks:
                bias = 1.2 if len(t)>=5 else (1.0 if len(t)>=3 else 0.9)
                self.Sem.learn(t, impulses, r=rate*bias)
                self.A.bump("general:text:corpus", f"general:text:{t}", w=0.02+0.04*H)
            accum=[]
            for _ in range(int(max(0.2, sleep_gap)*10)):
                if self.stop_flag.is_set(): break
                time.sleep(0.1)
    def stop(self): self.stop_flag.set()

class DiaryLoop(threading.Thread):
    def __init__(self, L: Lattice, A: Assoc, Sem: SemanticMemory):
        super().__init__(daemon=True); self.L=L; self.A=A; self.Sem=Sem
        self.stop_flag = threading.Event(); Path("logs").mkdir(exist_ok=True)
    def _voice(self, phi: float, H: float) -> str:
        pairs = [((a,b),w) for (a,b),w in self.A.top(4, domain_prefix="general")]
        if pairs: gist = ", ".join([f"{ab[0].split(':')[-1]}↔{ab[1].split(':')[-1]}" for (ab,_w) in pairs])
        else: gist = "quiet consolidation"
        tokens = len(self.Sem.map)
        mood = "balanced"
        if H>0.95 and phi<0.05: mood="broad and diffuse"
        elif phi>0.15: mood="focused and convergent"
        return f"(voice) Learning feels {mood}. Linking {gist}. tokens≈{tokens}"
    def run(self):
        interval = CFG["diary_sec"]
        while not self.stop_flag.is_set():
            time.sleep(interval)
            phi, H = coherence(self.L), entropy(self.L)
            line = f"[{time.strftime('%H:%M:%S')}] φ={phi:.2f} H={H:.2f}  " + self._voice(phi,H)
            print(line); open(CFG["paths"]["diary"], "a", encoding="utf-8").write(line+"\n")
    def stop(self): self.stop_flag.set()

class AutosaveLoop(threading.Thread):
    def __init__(self, Sem: SemanticMemory, A: Assoc, Fin: FinanceStore):
        super().__init__(daemon=True); self.Sem=Sem; self.A=A; self.Fin=Fin
        self.stop_flag = threading.Event()
    def run(self):
        interval = CFG["autosave_sec"]; t0=time.time()
        while not self.stop_flag.is_set():
            time.sleep(1.0)
            if time.time()-t0 >= interval:
                ok1=ok2=ok3=True
                try:self.Sem.save()
                except Exception: ok1=False
                try:self.A.save()
                except Exception: ok2=False
                try:self.Fin.save()
                except Exception: ok3=False
                print(f"[autosave] semantic={ok1} assoc={ok2} finance={ok3}")
                t0=time.time()
    def stop(self): self.stop_flag.set()

class CuriosityLoop(threading.Thread):
    def __init__(self, L: Lattice, Sem: SemanticMemory, A: Assoc, goal_ref):
        super().__init__(daemon=True); self.L=L; self.Sem=Sem; self.A=A; self.goal_ref=goal_ref
        self.stop_flag = threading.Event(); self.enabled=True; self.interest={}
    def _candidate_tokens(self, maxn=2000)->List[str]:
        keys=list(self.Sem.map.keys()); random.shuffle(keys); return keys[:min(maxn,len(keys))] if keys else []
    def _pick_probe(self)->str:
        for t in self._candidate_tokens():
            deg=self.A.degree("general", t)
            if deg<2: self.interest[t]=self.interest.get(t,0.0)+(2-deg)*0.5
            else:
                cur=self.interest.get(t,0.0)
                if cur>0: self.interest[t]=max(0.0, cur - 0.5*(deg/CFG["min_degree_for_satisfaction"]))
        if not self.interest: return ""
        return max(self.interest.items(), key=lambda kv: kv[1])[0]
    def _ingest_lines(self, lines: List[str], focus_token: str):
        count=0
        for ln in lines:
            impulses = {m: rotate(impulse(ln), (i+1)/len(CFG["modalities"])) for i,m in enumerate(CFG["modalities"])}
            self.L.stimulate(impulses, a=CFG["alpha"][self.goal_ref()])
            toks=[w for w in tokenize(ln) if w.isalpha()]
            if not toks: continue
            rate=CFG["reinforce"]["curiosity"]
            for t in set(toks):
                self.Sem.learn(t, impulses, r=rate)
                self.A.bump(f"general:text:{focus_token}", f"general:text:{t}", w=0.05)
            count+=1
            if count%8==0: time.sleep(0.05)
        return count
    def run(self):
        while not self.stop_flag.is_set():
            for _ in range(int(CFG["curiosity_sec"])):
                if self.stop_flag.is_set(): return
                time.sleep(1.0)
            if not self.enabled: continue
            probe=self._pick_probe()
            if not probe:
                print("[curiosity] idle (no candidate)"); continue
            print(f"[curiosity] probing: {probe}")
            lines=find_lines_with_token(probe, limit=CFG["curiosity_lines"])
            if not lines:
                impulses={m: rotate(impulse(probe),(i+1)/len(CFG["modalities"])) for i,m in enumerate(CFG["modalities"])}
                self.L.stimulate(impulses, a=CFG["alpha"][self.goal_ref()])
                self.Sem.learn(probe, impulses, r=0.25)
                continue
            n=self._ingest_lines(lines, probe)
            deg=self.A.degree("general", probe)
            if deg>=CFG["min_degree_for_satisfaction"]:
                self.interest[probe]=max(0.0, self.interest.get(probe,0.0)-1.5*deg)
            else:
                self.interest[probe]=self.interest.get(probe,0.0)+0.5
            print(f"[curiosity] ingested {n} lines for '{probe}' (degree={deg}, interest≈{self.interest.get(probe,0.0):.2f})")
    def stop(self): self.stop_flag.set()

# ---------------------- simple finance parsing + features ----------------------
def parse_finance_csv(path: Path) -> Tuple[List[str], List[float]]:
    try:
        rows=[]
        with open(path, newline="", encoding="utf-8") as f:
            rdr=csv.DictReader(f)
            for r in rdr: rows.append(r)
        if not rows: return [], []
        if "Date" in rows[0]: rows.sort(key=lambda r: r["Date"])
        closes=[]; dates=[]
        for r in rows:
            v=None
            for k in ["Adj Close","AdjClose","Close","close"]:
                if k in r and r[k]:
                    try: v=float(r[k]); break
                    except: pass
            if v is None: continue
            closes.append(v); dates.append(r.get("Date",""))
        return dates, closes
    except Exception as e:
        print(f"[finance] CSV parse failed: {path} ({e})"); return [], []

def inds_returns(closes: List[float], k: int) -> Optional[float]:
    if len(closes)<=k or k<=0: return None
    return (closes[-1]-closes[-1-k])/closes[-1-k]

def inds_volatility(closes: List[float], w: int=20) -> Optional[float]:
    if len(closes)<2: return None
    rets=[(closes[i]-closes[i-1])/max(1e-12,closes[i-1]) for i in range(1,len(closes))]
    if len(rets)<2: return None
    if len(rets)<w: w=len(rets)
    seg=rets[-w:]; m=sum(seg)/len(seg)
    var=sum((x-m)**2 for x in seg)/len(seg)
    return var**0.5

def inds_drawdown(closes: List[float]) -> Optional[float]:
    if not closes: return None
    peak=closes[0]; dd=0.0
    for c in closes:
        peak=max(peak,c)
        dd=max(dd, (peak-c)/peak if peak>0 else 0.0)
    return dd

def inds_slope(closes: List[float], w:int=20)->Optional[float]:
    if len(closes)<2: return None
    if len(closes)<w: w=len(closes)
    y=np.array(closes[-w:], dtype=np.float64)
    x=np.arange(len(y), dtype=np.float64)
    x=x-x.mean(); y=y-y.mean()
    denom=(x*x).sum()
    if denom<1e-12: return 0.0
    slope=(x*y).sum()/denom
    return float(slope)

def momentum_tag(r7: Optional[float], r30: Optional[float], slope: Optional[float]) -> str:
    up = (r7 or 0)>0 and (r30 or 0)>0 and (slope or 0)>0
    down = (r7 or 0)<0 and (r30 or 0)<0 and (slope or 0)<0
    if up: return "uptrend"
    if down: return "downtrend"
    return "mixed"

def vol_tag(vol: Optional[float]) -> str:
    if vol is None: return "n/a"
    if vol<0.01: return "calm"
    if vol<0.02: return "normal"
    if vol<0.04: return "elevated"
    return "high"

def finance_vectorize(name: str, closes: List[float]) -> np.ndarray:
    base = impulse(f"finance:{name}"); acc=base.copy()
    if closes:
        r30=inds_returns(closes,30) or 0.0
        vol=inds_volatility(closes,20) or 0.0
        phase = 0.5*(np.tanh(5*r30)+1.0)*0.5 + 0.5*np.clip(vol/0.04,0,1)*0.5
        acc=_unit(acc + 0.6*rotate(base, phase))
    return _unit(acc)

def feed_finance_series(ticker: str, path: Path, L: Lattice, Sem: SemanticMemory, A: Assoc, Fin: FinanceStore, goal: str):
    dates, closes = parse_finance_csv(path)
    if not closes:
        print(f"[feed] finance: no usable data in {path}"); return
    vec = finance_vectorize(ticker, closes)
    impulses = {m: rotate(vec, (i+1)/len(CFG["modalities"])) for i,m in enumerate(CFG["modalities"])}
    L.stimulate(impulses, a=CFG["alpha"][goal])
    for token in [ticker.lower(), "market","trend","risk","volume","return"]:
        Sem.learn(token, impulses, r=0.35)
        A.bump(f"finance:text:{ticker.lower()}", f"finance:text:{token}", w=0.08)
    Fin.upsert_series(ticker.upper(), {"n": len(closes), "last": closes[-1], "path": str(path)})
    if inds_volatility(closes,20) and inds_volatility(closes,20)>0.02:
        Fin.add_tag(ticker.upper(), "volatility")
    print(f"[feed] finance:{ticker} — points={len(closes)}")

# ---------------------- Auto-updater (offline-safe) ----------------------
class AutoUpdateLoop(threading.Thread):
    def __init__(self, data_dir: Path, watchlist_path: Path):
        super().__init__(daemon=True)
        self.data_dir=data_dir; self.watchlist_path=watchlist_path
        self.stop_flag=threading.Event()
    def _load_watchlist(self)->List[str]:
        if not self.watchlist_path.exists(): return []
        try:
            toks=[ln.strip() for ln in self.watchlist_path.read_text(encoding="utf-8").splitlines()]
            return [t for t in toks if t]
        except: return []
    def _append_business_day(self, ticker: str):
        fname = norm_ticker_to_filename(ticker) + ".csv"
        p = self.data_dir / fname
        if not p.exists(): return
        dates, closes = parse_finance_csv(p)
        if not closes: return
        fmt="%Y-%m-%d"
        try:
            last_dt = datetime.strptime(dates[-1], fmt)
        except:
            try: last_dt = datetime.fromisoformat(dates[-1][:10])
            except: return
        target = next_business_day(last_dt)
        today = datetime.now()
        if target.date() > today.date(): return
        rs = np.random.RandomState(_seed(ticker) ^ int(time.time()) & 0xffffffff)
        drift = rs.normal(0.0001, 0.0015)
        vol = abs(rs.normal(0.0, 0.008))
        new_close = max(0.01, closes[-1]*(1.0 + drift + rs.normal(0, vol)))
        new_open = new_close*(1.0+rs.normal(0, 0.002))
        new_high = max(new_open, new_close)*(1.0+abs(rs.normal(0, 0.003)))
        new_low  = min(new_open, new_close)*(1.0-abs(rs.normal(0, 0.003)))
        new_row = {
            "Date": target.strftime(fmt),
            "Open": f"{new_open:.2f}",
            "High": f"{new_high:.2f}",
            "Low": f"{new_low:.2f}",
            "Close": f"{new_close:.2f}",
            "Adj Close": f"{new_close:.2f}",
            "Volume": str(int(abs(rs.normal(8_000_000, 2_000_000))))
        }
        try:
            with open(p, "a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["Date","Open","High","Low","Close","Adj Close","Volume"])
                w.writerow(new_row)
            print(f"[auto] appended {ticker} {new_row['Date']} close={new_row['Close']}")
        except Exception as e:
            print(f"[auto] append failed for {ticker}: {e}")
    def run(self):
        interval = CFG["auto_update_sec"]
        while not self.stop_flag.is_set():
            wl = self._load_watchlist()
            for t in wl:
                try: self._append_business_day(t)
                except Exception as e:
                    print(f"[auto] error {t}: {e}")
            for _ in range(interval):
                if self.stop_flag.is_set(): return
                time.sleep(1.0)
    def stop(self): self.stop_flag.set()

# ---------------------- Insights & Portfolio ----------------------
def insight_for_series(ticker: str, closes: List[float]) -> str:
    if not closes or len(closes)<2: return f"(insight) {ticker}: insufficient data."
    r7=inds_returns(closes,7); r30=inds_returns(closes,30); r90=inds_returns(closes,90)
    vol=inds_volatility(closes,20); dd=inds_drawdown(closes); sl=inds_slope(closes,20)
    mom=momentum_tag(r7,r30,sl); vtag=vol_tag(vol)
    def pct(x): return ("+" if x and x>=0 else "")+f"{(x or 0)*100:.2f}%"
    dd_txt = f"{(dd or 0)*100:.2f}%"
    return (f"(insight) {ticker}: 7d={pct(r7)} 30d={pct(r30)} 90d={pct(r90)}  "
            f"trend={mom} vol={vtag} maxDD={dd_txt}")

def portfolio_load(watchlist_path: Path) -> List[str]:
    if not watchlist_path.exists(): return []
    try:
        toks=[ln.strip().upper() for ln in watchlist_path.read_text(encoding="utf-8").splitlines()]
        return [t for t in toks if t]
    except:
        return []

def portfolio_report(data_dir: Path, tickers: List[str], start_cash: float=10000.0) -> str:
    """
    Equal-weight portfolio: buy first available day for each ticker independently, hold to last.
    Windows-safe normalization: ^IXIC.csv -> IXIC.csv, etc.
    Gracefully skips tickers with no readable data.
    """
    series={}
    for t in tickers:
        fname = norm_ticker_to_filename(t) + ".csv"
        p = data_dir / fname
        if not p.exists(): 
            continue
        dates, closes = parse_finance_csv(p)
        if closes:
            series[t]=(dates, closes)
    if not series:
        return "(portfolio) no data."

    w=1.0/len(series)
    final=0.0; breakdown=[]
    for t,(dates,closes) in series.items():
        c0=closes[0]; cN=closes[-1]
        if c0<=0: 
            breakdown.append((t, 0.0, 0.0)); 
            continue
        alloc=start_cash*w
        shares=alloc/c0
        val=shares*cN
        ret=(cN-c0)/c0
        final+=val
        breakdown.append((t, ret, val))

    total_ret=(final-start_cash)/start_cash
    parts="  ".join([f"{t.replace('^','')}: {(r*100):+.2f}% (${v:,.0f})" for t,r,v in breakdown])
    return f"(portfolio) start=${start_cash:,.0f} end=${final:,.0f} total={total_ret*100:+.2f}%  |  {parts}"

def summary_mom(data_dir: Path, watchlist_path: Path, amount: float) -> str:
    wl = portfolio_load(watchlist_path)
    if not wl: 
        return "(mom) watchlist empty. Add with /watchlist add <TICKER>."
    # portfolio line
    p_line = portfolio_report(data_dir, wl, start_cash=amount)
    # top 2 ticker insights (concise)
    picks=[]
    for t in wl[:2]:
        fname = norm_ticker_to_filename(t)+".csv"
        p = data_dir/fname
        if p.exists():
            _, closes = parse_finance_csv(p)
            if closes and len(closes)>2:
                r30=inds_returns(closes,30); sl=inds_slope(closes,20)
                mom=momentum_tag(r30, r30, sl)  # quick proxy: reuse r30 for brevity
                picks.append(f"{t.replace('^','')}: {('+' if (r30 or 0)>=0 else '')}{((r30 or 0)*100):.1f}% {mom}")
    if picks:
        return f"(mom) {p_line}  ||  " + "  ".join(picks)
    return f"(mom) {p_line}"

# ---------------------- visualization (PGM) ----------------------
def _hash_xy(token: str, size: int, margin: int) -> Tuple[int,int]:
    rs=np.random.RandomState(_seed(f"pos:{token}") % (2**31))
    x=margin+int(rs.rand()*(size-2*margin)); y=margin+int(rs.rand()*(size-2*margin))
    return x,y

def _draw_line(img: np.ndarray, x0:int,y0:int,x1:int,y1:int,val:int):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        if 0<=x0<img.shape[1] and 0<=y0<img.shape[0]: img[y0,x0]=max(img[y0,x0], val)
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def _draw_circle(img: np.ndarray, cx:int,cy:int,r:int,val:int):
    x=r; y=0; e=0
    while x>=y:
        pts=[(cx+x,cy+y),(cx+y,cy+x),(cx-x,cy+y),(cx-y,cy+x),
             (cx-x,cy-y),(cx-y,cy-x),(cx+x,cy-y),(cx+y,cy-x)]
        for (px,py) in pts:
            if 0<=px<img.shape[1] and 0<=py<img.shape[0]: img[py,px]=max(img[py,px], val)
        y+=1
        if e<=0: e+=2*y+1
        if e>0: x-=1; e-=2*x+1

def visualize_concept(A: Assoc, domain: str, token: str, out_path: Path):
    size=CFG["viz"]["size"]; margin=CFG["viz"]["margin"]
    img=np.zeros((size,size), dtype=np.uint8)
    cx,cy=size//2,size//2
    _draw_circle(img, cx,cy, 10, 255)
    neigh=A.neighbors(domain, token, limit=CFG["viz"]["nodes"])
    for n,w in neigh:
        t=n.split(":text:")[-1]
        x,y=_hash_xy(f"{domain}:{t}", size, margin)
        val=120+int(120*min(1.0,w))
        _draw_line(img, cx,cy, x,y, val); _draw_circle(img, x,y,6,val)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path,"wb") as f:
        f.write(f"P5\n{size} {size}\n255\n".encode("ascii")); img.tofile(f)
    print(f"[viz] wrote: {out_path} (center={token}, neighbors={len(neigh)})")

# ---------------------- main ----------------------
def main():
    print("Aurelion v9.7 — Tao Finance Extension Core (Mom Mode)")

    L=Lattice(); Sem=SemanticMemory(CFG["paths"]["semantic_mem"])
    A=Assoc(CFG["paths"]["assoc"]); Fin=FinanceStore(CFG["paths"]["finance_store"])
    seed_words(Sem)

    goal="STABILIZE"

    Path(CFG["paths"]["corpora"]).mkdir(parents=True, exist_ok=True)
    data_dir=Path(CFG["paths"]["finance_data_dir"]); data_dir.mkdir(parents=True, exist_ok=True)
    watchlist_path=Path(CFG["paths"]["watchlist"]); watchlist_path.parent.mkdir(parents=True, exist_ok=True)

    # loops
    corpus=CorpusLoop(L,Sem,A, goal_ref=lambda: goal); corpus.start()
    diary=DiaryLoop(L,A,Sem); diary.start()
    autosave=AutosaveLoop(Sem,A,Fin); autosave.start()
    curiosity=CuriosityLoop(L,Sem,A, goal_ref=lambda: goal); curiosity.start()
    autoup=AutoUpdateLoop(data_dir, watchlist_path); autoup.start()

    print("[loop] corpus=ON  curiosity=ON (30m)  diary=ON (15m)  autosave=ON (4m)  autoupdate=ON (15m, Mom Mode)")
    print("[hint] Put CSVs in ./data/finance. To enable auto-extend, add tickers to data/finance/watchlist.txt")
    print("Commands:")
    print(" /state  /goal <stabilize|explore|focus>  /summarize now  /save  /quit")
    print(" /import pdf <path.pdf>  /import docx <path.docx>  /corpus check")
    print(" /feed finance <TICKER>.csv | all")
    print(" /watchlist add <TICKER> | remove <TICKER> | list")
    print(" /insight <TICKER|all>")
    print(" /portfolio set <amount>  |  /portfolio report")
    print(" /summary mom")
    print(" /viz concept <general|finance> <token> <out.pgm>  /viz top <general|finance> <out.pgm>")

    # portfolio cache
    portfolio={"amount":10000.0}
    port_file=Path(CFG["paths"]["portfolio"])
    if port_file.exists():
        try: portfolio=json.load(open(port_file,"r",encoding="utf-8"))
        except: pass

    def save_portfolio():
        try: json.dump(portfolio, open(port_file,"w",encoding="utf-8"), indent=2)
        except: pass

    def corpus_integrity()->str:
        files=list_corpus_files(); total_lines=0; fn_counts=[]
        for p in files:
            try: n=sum(1 for _ in p.open("r",encoding="utf-8",errors="ignore"))
            except Exception: n=0
            total_lines+=n; fn_counts.append((str(p),n))
        fn_counts.sort(key=lambda x:x[1], reverse=True)
        lines=[f"[corpus] {len(files)} file(s), total lines≈{total_lines}"]
        for name,n in fn_counts[:12]:
            short=name.replace('\\','/').split('/')[-2:]
            lines.append(f"  - {'/'.join(short)}  lines≈{n}")
        return "\n".join(lines)

    while True:
        try: msg=input("You: ").strip()
        except (EOFError,KeyboardInterrupt):
            print("\n[exit] stopping ..."); break
        if not msg: continue
        low=msg.lower()

        if low in ["/quit","exit"]: break

        if low.startswith("/state"):
            phi,H=coherence(L), entropy(L); norms=L.norms()
            print(f"φ={phi:.3f}  H={H:.3f}  |  tokens={len(Sem.map)}  links={len(A.W)}  finance_series={len(Fin.store.get('series',{}))}")
            print(" " + "  ".join([f"{m}:{norms[m]:2.2f}" for m in CFG['modalities']]))
            continue

        if low.startswith("/goal"):
            parts=msg.split()
            if len(parts)>=2 and parts[1].strip().upper() in ["STABILIZE","EXPLORE","FOCUS"]:
                goal=parts[1].strip().upper(); print(f"[OK] intent set to {goal}")
            else:
                print(f"[INFO] current goal = {goal}")
            continue

        if low.startswith("/summarize now"):
            phi,H=coherence(L), entropy(L)
            pairs=[((a,b),w) for (a,b),w in A.top(5, domain_prefix="general")]
            gist=", ".join([f"{ab[0].split(':')[-1]}↔{ab[1].split(':')[-1]}" for (ab,_w) in pairs]) if pairs else "quiet consolidation"
            print(f"(voice) Now: φ={phi:.2f} H={H:.2f}. Linking {gist}.")
            continue

        if low.startswith("/import"):
            parts=msg.split(maxsplit=2)
            if len(parts)<3: print("[import] usage: /import <pdf|docx> <path>"); continue
            kind=parts[1].lower(); path=Path(parts[2].strip().strip('"'))
            if not path.exists(): print(f"[import] not found: {path}"); continue
            out_dir=Path(CFG["paths"]["corpora"])/"Converted"
            out=None
            if kind=="docx": out=import_docx_to_txt(path, out_dir)
            elif kind=="pdf": out=import_pdf_to_txt_basic(path, out_dir)
            else: print("[import] type must be pdf|docx"); continue
            if out: print(f"[import] wrote: {out}")
            else: print("[import] failed (see above).")
            continue

        if low.startswith("/corpus check"):
            print(corpus_integrity()); continue

        if low.startswith("/feed finance"):
            parts=msg.split(maxsplit=2); arg=parts[2].strip() if len(parts)>=3 else ""
            if not arg: print("[feed] usage: /feed finance <TICKER>.csv | all"); continue
            if arg.lower()=="all":
                csvs=sorted(list(data_dir.glob("*.csv")))
                if not csvs: print("[feed] no CSV files found in ./data/finance")
                for p in csvs:
                    ticker=p.stem
                    feed_finance_series(ticker,p,L,Sem,A,Fin,goal)
                continue
            else:
                p=data_dir/arg
                if not p.exists(): print(f"[feed] not found: {p}")
                else:
                    ticker=p.stem; feed_finance_series(ticker,p,L,Sem,A,Fin,goal)
                continue

        if low.startswith("/watchlist"):
            parts=msg.split(maxsplit=2)
            if len(parts)==1 or parts[1]=="list":
                wl=portfolio_load(watchlist_path)
                if wl: print("[watchlist]", ", ".join(wl))
                else: print("[watchlist] (empty) — add tickers with /watchlist add <TICKER>")
                continue
            if parts[1]=="add" and len(parts)>=3:
                t=parts[2].strip().upper()
                wl=set(portfolio_load(watchlist_path)); wl.add(t)
                watchlist_path.write_text("\n".join(sorted(wl))+"\n", encoding="utf-8")
                print(f"[watchlist] added {t}"); continue
            if parts[1]=="remove" and len(parts)>=3:
                t=parts[2].strip().upper()
                wl=[x for x in portfolio_load(watchlist_path) if x!=t]
                watchlist_path.write_text("\n".join(wl)+"\n", encoding="utf-8")
                print(f"[watchlist] removed {t}"); continue
            print("[watchlist] usage: /watchlist add <TICKER> | remove <TICKER> | list")
            continue

        if low.startswith("/insight"):
            parts=msg.split(maxsplit=1)
            if len(parts)<2: print("[insight] usage: /insight <TICKER|all>"); continue
            arg=parts[1].strip()
            if arg.lower()=="all":
                csvs=sorted(list(data_dir.glob("*.csv")))
                if not csvs: print("[insight] no CSV files in ./data/finance")
                for p in csvs:
                    t=p.stem; _, closes = parse_finance_csv(p)
                    print(insight_for_series(t, closes))
                continue
            else:
                p=data_dir/f"{norm_ticker_to_filename(arg)}.csv"
                if not p.exists(): print(f"[insight] not found: {p}"); continue
                _, closes = parse_finance_csv(p)
                print(insight_for_series(arg.upper(), closes))
                continue

        if low.startswith("/portfolio"):
            parts=msg.split()
            if len(parts)>=3 and parts[1]=="set":
                try:
                    amt=float(parts[2]); portfolio["amount"]=max(100.0, amt); save_portfolio()
                    print(f"[portfolio] amount set to ${portfolio['amount']:,.0f}")
                except:
                    print("[portfolio] usage: /portfolio set <amount>")
                continue
            if parts[1]=="report":
                wl=portfolio_load(watchlist_path)
                if not wl: print("(portfolio) watchlist empty. Add with /watchlist add <TICKER>"); continue
                print(portfolio_report(data_dir, wl, start_cash=portfolio["amount"]))
                continue
            print("[portfolio] usage: /portfolio set <amount> | /portfolio report")
            continue

        if low.startswith("/summary mom"):
            print(summary_mom(data_dir, watchlist_path, amount=portfolio["amount"]))
            continue

        if low.startswith("/viz "):
            parts=msg.split()
            if len(parts)>=2 and parts[1]=="concept":
                if len(parts)<5: print("[viz] usage: /viz concept <general|finance> <token> <out.pgm>"); continue
                domain=parts[2].lower(); token=parts[3]; out=Path(parts[4])
                if domain not in ["general","finance"]: print("[viz] domain must be general|finance"); continue
                visualize_concept(A, domain, token, out); continue
            if len(parts)>=2 and parts[1]=="top":
                if len(parts)<4: print("[viz] usage: /viz top <general|finance> <out.pgm>"); continue
                domain=parts[2].lower(); out=Path(parts[3])
                top=A.top(n=CFG["viz"]["nodes"], domain_prefix=domain)
                token=f"{domain}_hub"; tmpA=Assoc("tmp.json")
                for (a,b),w in top:
                    ta=a.split(":text:")[-1]; tb=b.split(":text:")[-1]
                    tmpA.bump(f"{domain}:text:{token}", f"{domain}:text:{ta}", w)
                    tmpA.bump(f"{domain}:text:{token}", f"{domain}:text:{tb}", w)
                visualize_concept(tmpA, domain, token, out)
                try: Path("tmp.json").unlink()
                except: pass
                continue
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

        print("[INFO] cmds: /state  /goal <...>  /summarize now  /import pdf|docx  /corpus check  /feed finance <CSV|all>  /watchlist add|remove|list  /insight <TICKER|all>  /portfolio set|report  /summary mom  /viz concept|top  /save  /quit")

    # shutdown
    try:
        corpus.stop(); diary.stop(); autosave.stop(); curiosity.stop(); autoup.stop()
    except Exception: pass
    time.sleep(0.3)
    try: Sem.save(); A.save(); Fin.save()
    except Exception: pass
    print("[final] saved. Bye.")

if __name__ == "__main__":
    main()
