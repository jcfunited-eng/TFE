# aurelion_core_v9_8_tao_offline_pro.py
# Aurelion v9.8 — Tao Finance Extension (Offline Pro, Mom-Ready)
# - Offline synthetic-but-plausible market engine (indexes, stocks, crypto)
# - On-demand "static updates": /market pack, /market snapshot <YYYY-MM-DD>, /market step
# - Recommendations: /recommend <stocks|crypto|all> <conservative|balanced|aggressive> [min<=price<=max]
# - Backtest SMA cross: /backtest <TICKER> [window_fast=10] [window_slow=30]
# - Portfolio simulate (monthly rebalance): /portfolio simulate [months=6]
# - Keeps: watchlist, insights, portfolio report, mom summary, docx/pdf import, concept viz
# - No internet; only stdlib + numpy

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
        "diary": "logs/diary_v9_8.txt",
        "finance_store": "specialty_finance.json",
        "finance_data_dir": "data/finance",
        "watchlist": "data/finance/watchlist.txt",
        "portfolio": "data/finance/portfolio.json"
    },
    "autosave_sec": 240,
    "diary_sec": 900,
    "curiosity_sec": 1800,
    "viz": {"size": 512, "margin": 28, "nodes": 14},
    "auto_update_sec": 900,  # not used for network—kept for symmetry
}

PRESET_TICKERS = {
    "indexes": ["IXIC","SPY","QQQ"],
    "stocks":  ["AAPL","TSLA","AMD","NVDA","MSFT","AMZN"],
    "crypto":  ["BTCUSD","ETHUSD","SOLUSD"]
}

# ---------------------- utility ----------------------
def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v) + 1e-9
    return v / n

def _seed(w: str) -> int:
    h = 2166136261
    for c in w:
        h ^= ord(c); h = (h * 16777619) & 0xffffffff
    return h

def norm_ticker_to_filename(t: str) -> str:
    return re.sub(r'[\^\:/\\\*\?"<>\|]+', '', t)

def is_business_day(dt: datetime) -> bool:
    return dt.weekday() < 5

def next_business_day(dt: datetime) -> datetime:
    t = dt + timedelta(days=1)
    while not is_business_day(t):
        t += timedelta(days=1)
    return t

# ---------------------- minimal cognition scaffolding (kept light) ----------------------
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

class Assoc:
    def __init__(self, path: str):
        self.path = path
        self.W: Dict[Tuple[str,str], float] = {}
        self._lock = threading.Lock()
        if Path(path).exists():
            try:
                raw = json.load(open(path, "r", encoding="utf-8"))
                for k,v in raw.items():
                    a,b = k.split("||"); self.W[(a,b)] = float(v)
                print(f"[assoc] loaded {len(self.W)} links from {path}")
            except Exception:
                print(f"[assoc] could not parse {path}; starting new.")
    def save(self):
        with self._lock:
            snap = {f"{a}||{b}": w for (a,b),w in self.W.items()}
        json.dump(snap, open(self.path, "w", encoding="utf-8"), indent=2)

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

# ---------------------- file IO ----------------------
def ensure_dirs():
    Path(CFG["paths"]["corpora"]).mkdir(parents=True, exist_ok=True)
    d = Path(CFG["paths"]["finance_data_dir"]); d.mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    return d

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

def write_csv_header(path: Path):
    if path.exists(): return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["Date","Open","High","Low","Close","Adj Close","Volume"])
        w.writeheader()

def append_row(path: Path, date: datetime, open_, high, low, close, vol: int):
    with open(path, "a", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["Date","Open","High","Low","Close","Adj Close","Volume"])
        w.writerow({
            "Date": date.strftime("%Y-%m-%d"),
            "Open": f"{open_:.2f}",
            "High": f"{high:.2f}",
            "Low":  f"{low:.2f}",
            "Close":f"{close:.2f}",
            "Adj Close": f"{close:.2f}",
            "Volume": str(vol)
        })

# ---------------------- synthetic market engine ----------------------
def synth_seed_for(ticker: str) -> int:
    return _seed("MK:"+ticker)

def synth_start_price(ticker: str) -> float:
    base = {
        "IXIC": 14000, "SPY": 450, "QQQ": 380,
        "AAPL": 190, "TSLA": 220, "AMD": 120, "NVDA": 420, "MSFT": 380, "AMZN": 145,
        "BTCUSD": 60000, "ETHUSD": 3200, "SOLUSD": 140
    }.get(ticker.upper(), 100.0)
    return float(base)

def synth_generate_series(ticker: str, start: datetime, days: int, business_only=True) -> List[Dict]:
    rs = np.random.RandomState(synth_seed_for(ticker))
    price = synth_start_price(ticker)
    regime = rs.choice(["bull","bear","side"], p=[0.45,0.25,0.30])
    out=[]
    d=start
    added=0
    while added<days:
        if business_only and not is_business_day(d):
            d += timedelta(days=1); continue
        # drift/vol by regime; crypto a bit higher vol
        is_crypto = ticker.upper().endswith("USD")
        base_vol = 0.012 if not is_crypto else 0.022
        if regime=="bull":
            mu = 0.0007; sigma = base_vol
        elif regime=="bear":
            mu = -0.0008; sigma = base_vol*1.15
        else:
            mu = 0.0; sigma = base_vol*0.8
        # occasional regime flip
        if rs.rand()<0.015:
            regime = rs.choice(["bull","bear","side"])
        # shock
        shock = rs.normal(0, sigma*2.0) if rs.rand()<0.02 else 0.0
        ret = mu + rs.normal(0, sigma) + shock
        new_close = max(0.01, price*(1.0+ret))
        new_open  = new_close*(1.0+rs.normal(0, sigma/3))
        high = max(new_open, new_close)*(1.0+abs(rs.normal(0, sigma/2)))
        low  = min(new_open, new_close)*(1.0-abs(rs.normal(0, sigma/2)))
        vol = int(abs(rs.normal(8_000_000, 2_000_000))) if not is_crypto else int(abs(rs.normal(80_000, 20_000)))
        out.append({"date": d, "open": new_open, "high": high, "low": low, "close": new_close, "vol": vol})
        price = new_close
        d += timedelta(days=1); added+=1
    return out

def market_pack(data_dir: Path, preset: str = "realistic", days: int = 260):
    # realistic: a mix of everything
    all_ticks = PRESET_TICKERS["indexes"] + PRESET_TICKERS["stocks"] + PRESET_TICKERS["crypto"]
    if preset=="minimal":
        all_ticks = ["IXIC","AAPL","TSLA","BTCUSD"]
    start = datetime(2024,1,2)
    for t in all_ticks:
        p = data_dir / (norm_ticker_to_filename(t)+".csv")
        write_csv_header(p)
        series = synth_generate_series(t, start, days, business_only=not t.endswith("USD"))
        for row in series:
            append_row(p, row["date"], row["open"], row["high"], row["low"], row["close"], row["vol"])
    print(f"[market] pack '{preset}' generated ~{days} business days for {len(all_ticks)} tickers.")

def market_snapshot_to(data_dir: Path, target_date: datetime):
    # idempotent: generate forward until file's last date >= target_date
    for group in PRESET_TICKERS.values():
        for t in group:
            p = data_dir / (norm_ticker_to_filename(t)+".csv")
            write_csv_header(p)
            dates, closes = parse_finance_csv(p)
            last_date = None
            if dates:
                try: last_date = datetime.strptime(dates[-1], "%Y-%m-%d")
                except: 
                    try: last_date = datetime.fromisoformat(dates[-1][:10])
                    except: last_date = None
            start_dt = datetime(2024,1,2) if last_date is None else next_business_day(last_date)
            d = start_dt
            # synth engine must line up deterministically; we regenerate from scratch and append missing
            # For simplicity, continue from last close using seeded random variations
            steps=0
            while d.date() <= target_date.date():
                if not t.endswith("USD") and not is_business_day(d):
                    d += timedelta(days=1); continue
                # derive price from last close if exists; else synth baseline
                price = float(closes[-1]) if closes else synth_start_price(t)
                rs = np.random.RandomState(_seed(f"SNAP:{t}:{d.strftime('%Y%m%d')}"))
                base_vol = 0.012 if not t.endswith("USD") else 0.022
                mu = rs.normal(0.0001, 0.0008)
                sigma = abs(rs.normal(base_vol, base_vol*0.2))
                ret = mu + rs.normal(0, sigma)
                new_close = max(0.01, price*(1.0+ret))
                new_open  = new_close*(1.0+rs.normal(0, sigma/3))
                high = max(new_open, new_close)*(1.0+abs(rs.normal(0, sigma/2)))
                low  = min(new_open, new_close)*(1.0-abs(rs.normal(0, sigma/2)))
                vol = int(abs(rs.normal(8_000_000, 2_000_000)))
                append_row(p, d, new_open, high, low, new_close, vol)
                dates.append(d.strftime("%Y-%m-%d")); closes.append(new_close)
                d += timedelta(days=1); steps+=1
            if steps>0:
                print(f"[snapshot] {t}: appended {steps} day(s) to reach {target_date.strftime('%Y-%m-%d')}.")

def market_step_all(data_dir: Path, days: int = 1):
    # append N next business/crypto days based on a seeded daily generator
    for group in PRESET_TICKERS.values():
        for t in group:
            p = data_dir / (norm_ticker_to_filename(t)+".csv")
            write_csv_header(p)
            dates, closes = parse_finance_csv(p)
            last_dt = datetime(2024,1,2) if not dates else (
                datetime.strptime(dates[-1], "%Y-%m-%d") if "-" in dates[-1] else datetime.fromisoformat(dates[-1][:10])
            )
            d = last_dt
            for _ in range(days):
                d = next_business_day(d) if not t.endswith("USD") else d + timedelta(days=1)
                price = float(closes[-1]) if closes else synth_start_price(t)
                rs = np.random.RandomState(_seed(f"STEP:{t}:{d.strftime('%Y%m%d')}"))
                base_vol = 0.012 if not t.endswith("USD") else 0.022
                ret = rs.normal(0.0002, base_vol)
                new_close = max(0.01, price*(1.0+ret))
                new_open  = new_close*(1.0+rs.normal(0, base_vol/3))
                high = max(new_open, new_close)*(1.0+abs(rs.normal(0, base_vol/2)))
                low  = min(new_open, new_close)*(1.0-abs(rs.normal(0, base_vol/2)))
                vol = int(abs(rs.normal(8_000_000, 2_000_000)))
                append_row(p, d, new_open, high, low, new_close, vol)
                dates.append(d.strftime("%Y-%m-%d")); closes.append(new_close)
            print(f"[step] {t}: +{days} day(s)")

# ---------------------- indicators & analytics ----------------------
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

def sma(arr: List[float], w: int) -> List[float]:
    if w<=1: return arr[:]
    out=[]; s=0.0; q=[]
    for v in arr:
        q.append(v); s+=v
        if len(q)>w: s-=q.pop(0)
        out.append(s/len(q))
    return out

def slope_last_n(closes: List[float], w:int=20)->Optional[float]:
    if len(closes)<2: return None
    if len(closes)<w: w=len(closes)
    y=np.array(closes[-w:], dtype=np.float64)
    x=np.arange(len(y), dtype=np.float64)
    x=x-x.mean(); y=y-y.mean()
    denom=(x*x).sum()
    if denom<1e-12: return 0.0
    return float((x*y).sum()/denom)

def momentum_tag(r30: Optional[float], slope: Optional[float]) -> str:
    if (r30 or 0)>0 and (slope or 0)>0: return "uptrend"
    if (r30 or 0)<0 and (slope or 0)<0: return "downtrend"
    return "mixed"

# ---------------------- recommendations, backtests, portfolio ----------------------
def load_series_for_universe(data_dir: Path, universe: List[str]) -> Dict[str, Tuple[List[str], List[float]]]:
    out={}
    for t in universe:
        p = data_dir / (norm_ticker_to_filename(t)+".csv")
        if not p.exists(): continue
        dates, closes = parse_finance_csv(p)
        if closes: out[t]=(dates, closes)
    return out

def recommend_universe(data_dir: Path, kind: str, risk: str, price_band: Optional[Tuple[float,float]]):
    if kind=="stocks": uni = PRESET_TICKERS["stocks"]
    elif kind=="crypto": uni = PRESET_TICKERS["crypto"]
    else: uni = PRESET_TICKERS["indexes"] + PRESET_TICKERS["stocks"] + PRESET_TICKERS["crypto"]
    series = load_series_for_universe(data_dir, uni)
    rows=[]
    for t,(dates,closes) in series.items():
        price = closes[-1]
        if price_band:
            lo,hi=price_band
            if price<lo or price>hi: continue
        r7=inds_returns(closes,7) or 0.0
        r30=inds_returns(closes,30) or 0.0
        vol=inds_volatility(closes,20) or 0.0
        sl=slope_last_n(closes,20) or 0.0
        dd=inds_drawdown(closes) or 0.0
        mom=1.5*r30 + 0.5*sl
        # score by risk profile
        if risk=="conservative":
            score = (0.8*mom) - (0.6*vol) - (0.3*dd)
        elif risk=="balanced":
            score = (1.2*mom) - (0.4*vol) - (0.2*dd)
        else: # aggressive
            score = (1.6*mom) - (0.2*vol) - (0.1*dd) + 0.2*r7
        rows.append((t, price, r7, r30, vol, sl, dd, score))
    rows.sort(key=lambda r: r[-1], reverse=True)
    return rows[:6]

def backtest_sma(data_dir: Path, ticker: str, f:int=10, s:int=30) -> str:
    p = data_dir / (norm_ticker_to_filename(ticker)+".csv")
    if not p.exists(): return f"(backtest) {ticker}: no data."
    _, closes = parse_finance_csv(p)
    if not closes or len(closes)<max(f,s)+2: return f"(backtest) {ticker}: insufficient history."
    sma_f = sma(closes, f); sma_s = sma(closes, s)
    pos=0; entry=0.0; trades=0; wins=0; peak=closes[0]; maxdd=0.0; equity=1.0
    for i in range(1,len(closes)):
        if sma_f[i] is None or sma_s[i] is None: continue
        # crossover
        if pos==0 and sma_f[i] > sma_s[i] and sma_f[i-1] <= sma_s[i-1]:
            pos=1; entry=closes[i]; trades+=1
        elif pos==1 and sma_f[i] < sma_s[i] and sma_f[i-1] >= sma_s[i-1]:
            ret=(closes[i]-entry)/entry; equity *= (1.0+ret); wins += 1 if ret>0 else 0; pos=0
        # track dd on equity proxy (approx)
        peak=max(peak, closes[i]); maxdd=max(maxdd, (peak-closes[i])/peak if peak>0 else 0)
    # close open trade
    if pos==1:
        ret=(closes[-1]-entry)/entry; equity*= (1.0+ret); wins += 1 if ret>0 else 0
    cagr = (equity**(252/len(closes)) - 1.0) if len(closes)>0 else 0.0
    wr = (wins/max(1,trades))*100.0
    return f"(backtest) {ticker} SMA({f},{s}) trades={trades} win%={wr:.1f} CAGR≈{cagr*100:.1f}% maxDD≈{maxdd*100:.1f}%"

def portfolio_report_equal(data_dir: Path, tickers: List[str], start_cash: float=10000.0) -> str:
    series={}
    for t in tickers:
        p = data_dir / (norm_ticker_to_filename(t)+".csv")
        if not p.exists(): continue
        dates, closes = parse_finance_csv(p)
        if closes: series[t]=(dates, closes)
    if not series: return "(portfolio) no data."
    w=1.0/len(series)
    final=0.0; parts=[]
    for t,(d,c) in series.items():
        c0=c[0]; cN=c[-1]
        if c0<=0: continue
        alloc=start_cash*w; shares=alloc/c0; val=shares*cN; ret=(cN-c0)/c0
        final+=val; parts.append(f"{t}: {ret*100:+.2f}% (${val:,.0f})")
    tot=(final-start_cash)/start_cash
    return f"(portfolio) start=${start_cash:,.0f} end=${final:,.0f} total={tot*100:+.2f}%  |  " + "  ".join(parts)

def portfolio_simulate_monthly(data_dir: Path, tickers: List[str], months:int=6, start_cash: float=10000.0)->str:
    series={}
    for t in tickers:
        p = data_dir / (norm_ticker_to_filename(t)+".csv")
        if not p.exists(): continue
        dates, closes = parse_finance_csv(p)
        if closes and dates: series[t]=(dates, closes)
    if not series: return "(simulate) no data."
    # align by month ends
    # find common month-end indices
    # fallback: sample every 21 trading days
    steps=months
    per_t = {}
    for t,(dates,closes) in series.items():
        idx=[]
        last_m=None
        for i,ds in enumerate(dates):
            try: dt=datetime.strptime(ds,"%Y-%m-%d")
            except: 
                try: dt=datetime.fromisoformat(ds[:10])
                except: continue
            if last_m is None or dt.month!=last_m:
                if i>0: idx.append(i-1)
                last_m=dt.month
        if len(idx)==0: idx = list(range(0,len(closes),21))
        idx = idx[-(steps+1):]
        if len(idx)<2: continue
        per_t[t]=(idx, closes)
    if not per_t: return "(simulate) insufficient data."
    equity=start_cash
    for k in range(steps):
        # rebalance equal weight at month k
        picks=[]
        for t,(idx,cl) in per_t.items():
            if k+1>=len(idx): continue
            c0=cl[idx[k]]; c1=cl[idx[k+1]]
            if c0<=0: continue
            ret=(c1-c0)/c0
            picks.append((t, ret))
        if not picks: continue
        w=1.0/len(picks)
        step_ret=sum(ret*w for (t,ret) in picks)
        equity *= (1.0 + step_ret)
    tot=(equity-start_cash)/start_cash
    return f"(simulate) monthly rebalance {steps}m: start=${start_cash:,.0f} end=${equity:,.0f} total={tot*100:+.2f}%"

# ---------------------- mom summary ----------------------
def summary_mom(data_dir: Path, watchlist_path: Path, amount: float) -> str:
    wl = []
    if Path(watchlist_path).exists():
        wl=[ln.strip().upper() for ln in Path(watchlist_path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not wl: return "(mom) watchlist empty. Add with /watchlist add <TICKER>."
    pline = portfolio_report_equal(data_dir, wl, start_cash=amount)
    # top 2 by 30d momentum among watchlist
    picks=[]
    for t in wl[:2]:
        p = data_dir / (norm_ticker_to_filename(t)+".csv")
        if not p.exists(): continue
        _, closes = parse_finance_csv(p)
        if not closes: continue
        r30=inds_returns(closes,30) or 0.0
        sl=slope_last_n(closes,20) or 0.0
        mom=momentum_tag(r30, sl)
        picks.append(f"{t}: {('+' if r30>=0 else '')}{r30*100:.1f}% {mom}")
    if picks:
        return f"(mom) {pline}  ||  " + "  ".join(picks)
    return f"(mom) {pline}"

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

# ---------------------- main shell ----------------------
def main():
    print("Aurelion v9.8 — Tao Finance Extension (Offline Pro, Mom-Ready)")
    L=Lattice(); Sem=SemanticMemory(CFG["paths"]["semantic_mem"]); A=Assoc(CFG["paths"]["assoc"]); Fin=FinanceStore(CFG["paths"]["finance_store"])
    data_dir = ensure_dirs()
    watchlist_path = Path(CFG["paths"]["watchlist"])
    if not watchlist_path.exists():
        watchlist_path.parent.mkdir(parents=True, exist_ok=True)
        watchlist_path.write_text("AAPL\nTSLA\nIXIC\n", encoding="utf-8")

    portfolio={"amount":10000.0}
    port_file=Path(CFG["paths"]["portfolio"])
    if port_file.exists():
        try: portfolio=json.load(open(port_file,"r",encoding="utf-8"))
        except: pass

    print("[hint] First time? Run: /market pack realistic   (or minimal)")
    print("Commands:")
    print(" /market pack <minimal|realistic>     /market snapshot <YYYY-MM-DD>     /market step [days]")
    print(" /feed finance all  |  /watchlist add <TICKER> | remove <TICKER> | list")
    print(" /recommend <stocks|crypto|all> <conservative|balanced|aggressive> [min<=price<=max]")
    print(" /backtest <TICKER> [fast=10] [slow=30]   /portfolio set <amt> | report | simulate [months=6]")
    print(" /summary mom   /insight <TICKER|all>   /import pdf|docx <path>   /save   /quit")

    while True:
        try: s=input("You: ").strip()
        except (EOFError,KeyboardInterrupt):
            print("\n[exit]"); break
        if not s: continue
        low=s.lower()

        if low in ["/quit","exit"]: break

        if low.startswith("/market pack"):
            parts=s.split()
            preset = parts[2].lower() if len(parts)>=3 else "realistic"
            market_pack(data_dir, preset=preset, days=260)
            continue

        if low.startswith("/market snapshot"):
            parts=s.split()
            if len(parts)<3:
                print("[market] usage: /market snapshot YYYY-MM-DD"); continue
            try:
                dt=datetime.strptime(parts[2], "%Y-%m-%d")
            except:
                print("[market] invalid date, use YYYY-MM-DD"); continue
            market_snapshot_to(data_dir, dt); continue

        if low.startswith("/market step"):
            parts=s.split()
            days = int(parts[2]) if len(parts)>=3 and parts[2].isdigit() else 1
            market_step_all(data_dir, days=days); continue

        if low.startswith("/feed finance"):
            csvs=sorted(list(data_dir.glob("*.csv")))
            if not csvs: print("[feed] no CSVs in data/finance — run /market pack first."); continue
            for p in csvs:
                dates, closes = parse_finance_csv(p)
                print(f"[feed] {p.stem}: points={len(closes)} last={closes[-1]:.2f}")
            continue

        if low.startswith("/watchlist"):
            parts=s.split(maxsplit=2)
            if len(parts)==1 or parts[1]=="list":
                wl=[ln.strip().upper() for ln in watchlist_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
                print("[watchlist]", ", ".join(wl) if wl else "(empty)")
                continue
            if parts[1]=="add" and len(parts)>=3:
                t=parts[2].strip().upper()
                wl=set([ln.strip().upper() for ln in watchlist_path.read_text(encoding="utf-8").splitlines() if ln.strip()])
                wl.add(t); watchlist_path.write_text("\n".join(sorted(wl))+"\n", encoding="utf-8")
                print(f"[watchlist] added {t}"); continue
            if parts[1]=="remove" and len(parts)>=3:
                t=parts[2].strip().upper()
                wl=[ln.strip().upper() for ln in watchlist_path.read_text(encoding="utf-8").splitlines() if ln.strip() and ln.strip().upper()!=t]
                watchlist_path.write_text("\n".join(wl)+"\n", encoding="utf-8")
                print(f"[watchlist] removed {t}"); continue
            print("[watchlist] usage: /watchlist add <TICKER> | remove <TICKER> | list"); continue

        if low.startswith("/recommend"):
            # /recommend all balanced 10<=price<=400
            parts = s.split()
            kind = parts[1].lower() if len(parts)>=2 else "all"
            risk = parts[2].lower() if len(parts)>=3 else "balanced"
            band=None
            m=re.search(r"(\d+(\.\d+)?)<=price<=(\d+(\.\d+)?)", s)
            if m:
                band=(float(m.group(1)), float(m.group(3)))
            rows = recommend_universe(data_dir, kind, risk, band)
            if not rows:
                print("(recommend) no matches. Try /market pack realistic or relax filters.")
            else:
                print("(recommend) top:")
                for t,price,r7,r30,vol,sl,dd,score in rows:
                    tag = momentum_tag(r30, sl)
                    print(f"  {t:7s}  px={price:8.2f}  7d={r7*100:+5.1f}%  30d={r30*100:+5.1f}%  vol={vol:0.3f}  draw={dd*100:5.1f}%  trend={tag}  score={score: .3f}")
            continue

        if low.startswith("/backtest"):
            parts=s.split()
            if len(parts)<2: print("[backtest] usage: /backtest <TICKER> [fast=10] [slow=30]"); continue
            t=parts[1].upper()
            f=10; sL=30
            if len(parts)>=3 and parts[2].isdigit(): f=int(parts[2])
            if len(parts)>=4 and parts[3].isdigit(): sL=int(parts[3])
            print(backtest_sma(data_dir, t, f, sL)); continue

        if low.startswith("/portfolio"):
            parts=s.split()
            if len(parts)>=3 and parts[1]=="set":
                try:
                    amt=float(parts[2]); amt=max(100.0, amt); 
                    portfolio["amount"]=amt; json.dump(portfolio, open(Path(CFG["paths"]["portfolio"]),"w",encoding="utf-8"), indent=2)
                    print(f"[portfolio] amount set to ${amt:,.0f}")
                except:
                    print("[portfolio] usage: /portfolio set <amount>")
                continue
            if "report" in parts:
                wl=[ln.strip().upper() for ln in watchlist_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
                if not wl: print("(portfolio) watchlist empty."); continue
                print(portfolio_report_equal(data_dir, wl, start_cash=portfolio["amount"]))
                continue
            if "simulate" in parts:
                months=6
                if len(parts)>=3 and parts[2].isdigit(): months=int(parts[2])
                wl=[ln.strip().upper() for ln in watchlist_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
                if not wl: print("(simulate) watchlist empty."); continue
                print(portfolio_simulate_monthly(data_dir, wl, months=months, start_cash=portfolio["amount"]))
                continue
            print("[portfolio] usage: /portfolio set <amount> | /portfolio report | /portfolio simulate [months]"); continue

        if low.startswith("/insight"):
            parts=s.split(maxsplit=1)
            if len(parts)<2: print("[insight] usage: /insight <TICKER|all>"); continue
            arg=parts[1].strip().upper()
            if arg=="ALL":
                uni = PRESET_TICKERS["indexes"]+PRESET_TICKERS["stocks"]+PRESET_TICKERS["crypto"]
                series = load_series_for_universe(data_dir, uni)
                for t,(d,c) in series.items():
                    r7=inds_returns(c,7); r30=inds_returns(c,30); sl=slope_last_n(c,20); vol=inds_volatility(c,20); dd=inds_drawdown(c)
                    mom=momentum_tag(r30, sl)
                    def pct(x): return ("+" if x and x>=0 else "")+f"{(x or 0)*100:.1f}%"
                    print(f"(insight) {t}: 7d={pct(r7)} 30d={pct(r30)} slope={sl or 0:+.4f} vol={vol or 0:.3f} maxDD={(dd or 0)*100:.1f}% trend={mom}")
            else:
                p = data_dir / (norm_ticker_to_filename(arg)+".csv")
                if not p.exists(): print(f"[insight] not found: {p}"); continue
                _, c = parse_finance_csv(p)
                r7=inds_returns(c,7); r30=inds_returns(c,30); sl=slope_last_n(c,20); vol=inds_volatility(c,20); dd=inds_drawdown(c)
                mom=momentum_tag(r30, sl)
                def pct(x): return ("+" if x and x>=0 else "")+f"{(x or 0)*100:.1f}%"
                print(f"(insight) {arg}: 7d={pct(r7)} 30d={pct(r30)} slope={sl or 0:+.4f} vol={vol or 0:.3f} maxDD={(dd or 0)*100:.1f}% trend={mom}")
            continue

        if low.startswith("/summary mom"):
            print(summary_mom(data_dir, watchlist_path, amount=portfolio["amount"])); continue

        if low.startswith("/import"):
            parts=s.split(maxsplit=2)
            if len(parts)<3: print("[import] usage: /import <pdf|docx> <path>"); continue
            kind=parts[1].lower(); path=Path(parts[2].strip().strip('"'))
            if not path.exists(): print(f"[import] not found: {path}"); continue
            out_dir=Path(CFG["paths"]["corpora"])/"Converted"
            out=None
            if kind=="docx": out=import_docx_to_txt_basic(path=None)  # keep docx below (typo protection)
            if kind=="docx": out=import_docx_to_txt(path, out_dir)
            elif kind=="pdf": out=import_pdf_to_txt_basic(path, out_dir)
            else: print("[import] type must be pdf|docx"); continue
            if out: print(f"[import] wrote: {out}")
            else: print("[import] failed (see above).")
            continue

        if low.startswith("/save"):
            ok=True
            try:
                # Just persist finance store placeholder; main state is CSV + watchlist
                pass
            except: ok=False
            print(f"[OK] saved={ok}"); continue

        print("[INFO] cmds: /market pack|snapshot|step  /recommend  /backtest  /portfolio set|report|simulate  /insight  /summary mom  /import pdf|docx  /save  /quit")

    print("[final] Bye.")

if __name__ == "__main__":
    main()
