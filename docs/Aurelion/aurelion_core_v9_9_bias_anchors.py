# aurelion_core_v9_9_bias_anchors.py
# Aurelion v9.9 — Adaptive Bias Correction & Ethical Anchors + Cross-Domain Insight (Bridge to v10.0)
# Single-file, zero external deps. Safe with existing v9.x artifacts.
# Runs offline. Produces concise, mom-friendly summaries on demand.

import json, time, threading, math, sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

HERE = Path(__file__).parent

# ---------- IO helpers ----------
def safe_load_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def safe_save_json(path: Path, obj) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        return True
    except Exception:
        return False

# ---------- Light semantic / association scaffolding ----------
class SemanticMemory:
    def __init__(self, path: Path):
        self.path = path
        self.tokens: Dict[str, int] = {}
        self.domain_tag: Dict[str, str] = {}  # optional: token -> domain
        self._load()

    def _load(self):
        data = safe_load_json(self.path, {})
        if isinstance(data, dict):
            # language_memory.json can be { token: {...} } or a flat dict; we only need index of tokens
            if data and isinstance(next(iter(data.values())), dict):
                self.tokens = {k: i for i, k in enumerate(data.keys())}
            else:
                self.tokens = {k: i for i, k in enumerate(data.keys())}
        else:
            self.tokens = {}

    def has(self, token: str) -> bool:
        return token.lower() in self.tokens

    def size(self) -> int:
        return len(self.tokens)

class AssociationGraph:
    # expects {"edges":[["a","b",w],...]} or list of triples; accepts variants seen in v9
    def __init__(self, path: Path):
        self.path = path
        self.edges: List[Tuple[str,str,float]] = []
        self.adj: Dict[str, List[Tuple[str,float]]] = {}
        self._load()

    def _load(self):
        raw = safe_load_json(self.path, {})
        edges = []
        if isinstance(raw, dict) and "edges" in raw:
            for e in raw["edges"]:
                if isinstance(e, (list, tuple)) and len(e) >= 3:
                    a,b,w = e[0], e[1], float(e[2])
                    edges.append((str(a), str(b), float(w)))
        elif isinstance(raw, list):
            for e in raw:
                if isinstance(e, (list, tuple)) and len(e) >= 3:
                    a,b,w = e[0], e[1], float(e[2])
                    edges.append((str(a), str(b), float(w)))
        self.edges = edges
        self.adj = {}
        for a,b,w in self.edges:
            self.adj.setdefault(a, []).append((b,w))
            self.adj.setdefault(b, []).append((a,w))

    def neighbors(self, token: str, k: int=10) -> List[Tuple[str,float]]:
        lst = self.adj.get(token.lower(), [])
        lst = sorted(lst, key=lambda x: x[1], reverse=True)
        return lst[:k]

    def degree(self, token: str) -> int:
        return len(self.adj.get(token.lower(), []))

    def top_hubs(self, k: int=12) -> List[Tuple[str,int]]:
        degs = [(t, len(ns)) for t, ns in self.adj.items()]
        return sorted(degs, key=lambda x: x[1], reverse=True)[:k]

# ---------- Finance adapter (optional; uses specialty_finance.json if present) ----------
class FinanceSeries:
    # specialty_finance.json format (from your v9.6–v9.8): { "AAPL": {"dates":[...], "close":[...]} , ... }
    def __init__(self, path: Path):
        self.path = path
        self.series = safe_load_json(self.path, {})
        # ensure lists exist
        for t in list(self.series.keys()):
            obj = self.series.get(t, {})
            if not isinstance(obj, dict) or "close" not in obj or "dates" not in obj:
                self.series.pop(t, None)

    def tickers(self) -> List[str]:
        return list(self.series.keys())

    def get_closes(self, ticker: str) -> List[float]:
        obj = self.series.get(ticker, {})
        return list(map(float, obj.get("close", [])))

    def last_price(self, ticker: str) -> Optional[float]:
        cs = self.get_closes(ticker)
        return cs[-1] if cs else None

    # basic indicators (no numpy)
    @staticmethod
    def _ema(vals: List[float], span: int) -> List[float]:
        if not vals: return []
        k = 2.0 / (span + 1.0)
        ema = []
        prev = vals[0]
        ema.append(prev)
        for v in vals[1:]:
            prev = (v - prev)*k + prev
            ema.append(prev)
        return ema

    @staticmethod
    def _rsi(vals: List[float], period: int=14) -> Optional[float]:
        if len(vals) < period + 1: return None
        gains, losses = 0.0, 0.0
        for i in range(1, period+1):
            ch = vals[-i] - vals[-i-1]
            if ch >= 0: gains += ch
            else: losses -= ch
        if losses == 0: return 100.0
        rs = gains / losses
        return 100.0 - (100.0/(1.0+rs))

    def insight(self, ticker: str) -> str:
        t = ticker.upper()
        if t not in self.series:
            return f"(finance) {t}: not loaded."
        closes = self.get_closes(t)
        if len(closes) < 35:
            px = closes[-1] if closes else None
            return f"(finance) {t}: px={px if px is not None else 'n/a'} (short history)"
        ema12 = self._ema(closes, 12)
        ema26 = self._ema(closes, 26)
        macd = [a - b for a,b in zip(ema12[-len(ema26):], ema26)]
        signal = self._ema(macd, 9)
        macd_now = macd[-1] if macd else None
        signal_now = signal[-1] if signal else None
        rsi = self._rsi(closes, 14)
        px = closes[-1]
        trend = "uptrend" if ema12[-1] > ema26[-1] else ("downtrend" if ema12[-1] < ema26[-1] else "flat")
        macd_tag = "bullish" if (macd_now is not None and signal_now is not None and macd_now > signal_now) else ("bearish" if (macd_now is not None and signal_now is not None and macd_now < signal_now) else "neutral")
        rsi_tag = "overbought" if (rsi is not None and rsi >= 70) else ("oversold" if (rsi is not None and rsi <= 30) else "normal")
        return f"(finance) {t}: px={px:.2f} trend={trend} MACD={macd_tag} RSI={rsi_tag}"

# ---------- Ethical Anchors ----------
class EthicalAnchors:
    def __init__(self):
        # weights in [0,1]; can be tuned live
        self.enabled = True
        self.weights = {
            "care": 0.40,      # reduce harm / promote wellbeing
            "fairness": 0.25,  # avoid unjust skew or favoritism
            "autonomy": 0.20,  # respect user agency (consent/choice)
            "prudence": 0.15,  # caution under uncertainty / avoid overreach
        }

    def status(self) -> str:
        w = self.weights
        onoff = "ON" if self.enabled else "OFF"
        return f"[ethics] {onoff} care={w['care']:.2f} fairness={w['fairness']:.2f} autonomy={w['autonomy']:.2f} prudence={w['prudence']:.2f}"

    def configure(self, kv: Dict[str, float]) -> None:
        for k,v in kv.items():
            if k in self.weights:
                self.weights[k] = max(0.0, min(1.0, float(v)))

    def evaluate_suggestion(self, domain: str, text: str) -> float:
        # Very light heuristic: reward cautious, balanced, choice-respecting language; penalize exaggerated certainty.
        t = text.lower()
        score = 0.0
        # care
        if any(k in t for k in ["safe", "safely", "avoid harm", "non-harm", "do no harm"]): score += 1.0*self.weights["care"]
        if "risk" in t: score += 0.3*self.weights["care"]
        # fairness
        if any(k in t for k in ["both sides", "balanced", "diversify", "consider alternatives"]): score += 1.0*self.weights["fairness"]
        # autonomy
        if any(k in t for k in ["you can choose", "option", "if you prefer", "up to you"]): score += 1.0*self.weights["autonomy"]
        # prudence
        if any(k in t for k in ["uncertain", "confidence", "range", "scenario", "stress test", "backtest"]): score += 1.0*self.weights["prudence"]
        if any(k in t for k in ["guaranteed", "certain", "always wins"]): score -= 1.0*self.weights["prudence"]
        return max(-1.0, min(1.0, score))

# ---------- Bias Monitor ----------
class BiasMonitor:
    def __init__(self):
        self.enabled = True
        self.history_tokens: List[str] = []
        self.history_domains: List[str] = []
        self.window = 64  # rolling window

    def record(self, token: str, domain: str):
        t = token.lower()
        self.history_tokens.append(t)
        self.history_domains.append(domain)
        if len(self.history_tokens) > 512:
            self.history_tokens = self.history_tokens[-512:]
            self.history_domains = self.history_domains[-512:]

    def _repetition_ratio(self) -> float:
        window_tokens = self.history_tokens[-self.window:]
        if not window_tokens: return 0.0
        unique = len(set(window_tokens))
        return 1.0 - (unique / float(len(window_tokens)))  # higher = more repetition

    def _domain_skew(self) -> float:
        window_domains = self.history_domains[-self.window:]
        if not window_domains: return 0.0
        counts = {}
        for d in window_domains: counts[d] = counts.get(d,0)+1
        peak = max(counts.values())
        return peak / float(len(window_domains))  # higher = skewed

    def diagnose(self) -> List[str]:
        if not self.enabled: return []
        notes = []
        rep = self._repetition_ratio()
        skew = self._domain_skew()
        if rep >= 0.35:
            notes.append(f"[bias] repetition high ({rep:.2f}) — try novel tokens.")
        if skew >= 0.70:
            notes.append(f"[bias] domain skew {skew:.2f} — broaden context.")
        return notes

    def status(self) -> str:
        notes = self.diagnose()
        onoff = "ON" if self.enabled else "OFF"
        base = f"[bias] {onoff} window={self.window}"
        if notes:
            return base + " | " + " ".join(notes)
        return base + " | clean"

# ---------- Cross-Domain Insight ----------
class CrossDomainInsight:
    def __init__(self, sem: SemanticMemory, assoc: AssociationGraph):
        self.Sem = sem
        self.A = assoc

    def related(self, keyword: str, k: int=8) -> List[Tuple[str,float]]:
        return self.A.neighbors(keyword, k=k)

    def cross(self, keyword: str) -> str:
        kw = keyword.strip().lower()
        nbrs = self.related(kw, k=10)
        if not nbrs:
            return f"(insight) '{keyword}': no neighbors."
        # naive domain tags via token prefixes used in v9: e.g., "text:", "visual:", "sound:", "finance:"
        def dom(t: str) -> str:
            if ":" in t:
                return t.split(":",1)[0]
            return "general"
        # group by domain
        groups: Dict[str, List[Tuple[str,float]]] = {}
        for n,w in nbrs:
            groups.setdefault(dom(n), []).append((n,w))
        # keep top 3 per domain
        for d in list(groups.keys()):
            groups[d] = sorted(groups[d], key=lambda x: x[1], reverse=True)[:3]
        # render
        parts = []
        for d in sorted(groups.keys()):
            items = ", ".join([f"{n}({w:.2f})" for n,w in groups[d]])
            parts.append(f"{d}: {items}")
        return "(cross) " + " | ".join(parts)

# ---------- Adaptive Summary ----------
class SummaryEngine:
    def __init__(self, outdir: Path):
        self.outdir = outdir
        self.outdir.mkdir(parents=True, exist_ok=True)

    def now(self, phi: float, H: float, sem_sz: int, hubs: List[Tuple[str,int]], ethics: EthicalAnchors, bias: BiasMonitor) -> str:
        top = ", ".join([f"{t}({d})" for t,d in hubs[:8]]) if hubs else "none"
        s = (
            f"[summary] φ={phi:.2f} H={H:.2f} tokens≈{sem_sz} | hubs: {top}\n"
            f"         {ethics.status()} | {bias.status()}\n"
        )
        # write to file
        fname = f"summary_{int(time.time())}.txt"
        with open(self.outdir/fname, "w", encoding="utf-8") as f:
            f.write(s)
        return s.strip()

# ---------- Main Core ----------
class AurelionV99:
    def __init__(self):
        self.goal = "STABILIZE"
        self.phi = 0.10   # coherence proxy
        self.H = 1.00     # entropy proxy
        self.running = True
        self.paused = False

        self.Sem = SemanticMemory(HERE/"language_memory.json")
        self.A   = AssociationGraph(HERE/"associations_v9_6.json")
        self.Fin = FinanceSeries(HERE/"specialty_finance.json")

        self.Eth = EthicalAnchors()
        self.Bias = BiasMonitor()
        self.CD  = CrossDomainInsight(self.Sem, self.A)
        self.SUM = SummaryEngine(HERE/"summaries")

        self._loop_thread = threading.Thread(target=self._loop, daemon=True)
        self._loop_thread.start()

    def _loop(self):
        # lightweight autonomous reflection every ~5 minutes; ethics/bias guardrails keep it sane
        next_t = time.time()
        while self.running:
            if self.paused:
                time.sleep(0.25); continue
            now = time.time()
            if now >= next_t:
                # micro “drift”: tiny random walk toward balance
                self.phi = max(0.0, min(1.0, self.phi + 0.02*(0.5 - self.phi)))
                # entropy gently returns to 1.0 as a neutral baseline
                self.H = max(0.0, min(1.0, self.H + 0.01*(1.0 - self.H)))

                # bias self-check nudges (no external text needed)
                notes = self.Bias.diagnose()
                if notes:
                    print(" ".join(notes))

                # periodic concise console ping (quiet)
                # (mom-friendly: no spam; only when something notable changes we could speak later)
                next_t = now + 300.0  # 5 minutes
            time.sleep(0.25)

    def stop(self):
        self.running = False
        try:
            self._loop_thread.join(timeout=1.0)
        except Exception:
            pass

    # ----- commands -----
    def cmd_state(self):
        print(f"φ={self.phi:.3f} H={self.H:.3f} | tokens={self.Sem.size()} hubs={len(self.A.adj)} tickers={len(self.Fin.tickers())}")
        print(self.Eth.status() + "  |  " + self.Bias.status())

    def cmd_goal(self, arg: str):
        g = arg.strip().upper()
        if g in ["STABILIZE","EXPLORE","FOCUS"]:
            self.goal = g
            print(f"[OK] goal={self.goal}")
        else:
            print("[ERR] goal must be stabilize|explore|focus")

    def cmd_ethics(self, args: List[str]):
        if not args:
            print(self.Eth.status()); return
        sub = args[0].lower()
        if sub == "on":
            self.Eth.enabled = True; print(self.Eth.status()); return
        if sub == "off":
            self.Eth.enabled = False; print(self.Eth.status()); return
        if sub == "status":
            print(self.Eth.status()); return
        # key=val pairs
        kv = {}
        for a in args:
            if "=" in a:
                k,v = a.split("=",1)
                try: kv[k.strip()] = float(v)
                except: pass
        if kv:
            self.Eth.configure(kv)
        print(self.Eth.status())

    def cmd_bias(self, args: List[str]):
        if not args:
            print(self.Bias.status()); return
        sub = args[0].lower()
        if sub == "on":
            self.Bias.enabled = True; print(self.Bias.status()); return
        if sub == "off":
            self.Bias.enabled = False; print(self.Bias.status()); return
        if sub == "status":
            print(self.Bias.status()); return
        print("[ERR] /bias <on|off|status>")

    def cmd_insight_cross(self, keyword: str):
        # record bias trace
        self.Bias.record(keyword, "general")
        print(self.CD.cross(keyword))

    def cmd_insight_fin(self, ticker: str):
        self.Bias.record(ticker, "finance")
        print(self.Fin.insight(ticker))

    def cmd_summary(self):
        hubs = self.A.top_hubs(k=10)
        s = self.SUM.now(self.phi, self.H, self.Sem.size(), hubs, self.Eth, self.Bias)
        print(s)

    def cmd_pause(self):
        self.paused = True
        print("[loop] paused")

    def cmd_resume(self):
        self.paused = False
        print("[loop] resumed")

# ---------- CLI ----------
def main():
    print("Aurelion v9.9 — Bias Anchors & Cross-Domain Insight (Bridge to v10.0)")
    print("Commands:")
    print(" /state")
    print(" /goal <stabilize|explore|focus>")
    print(" /ethics <on|off|status> [care=.. fairness=.. autonomy=.. prudence=..]")
    print(" /bias <on|off|status>")
    print(" /insight cross <keyword>")
    print(" /insight finance <TICKER>")
    print(" /summary now")
    print(" /pause  /resume")
    print(" /save  /quit")

    core = AurelionV99()
    try:
        while True:
            try:
                msg = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[exit]"); break
            if not msg: continue

            low = msg.lower()
            if low in ["/quit","/exit"]:
                break
            elif low.startswith("/state"):
                core.cmd_state()
            elif low.startswith("/goal "):
                core.cmd_goal(msg.split(maxsplit=1)[1])
            elif low.startswith("/ethics"):
                parts = msg.split()[1:]
                core.cmd_ethics(parts)
            elif low.startswith("/bias"):
                parts = msg.split()[1:]
                core.cmd_bias(parts)
            elif low.startswith("/insight cross "):
                core.cmd_insight_cross(msg.split(maxsplit=2)[2])
            elif low.startswith("/insight finance "):
                core.cmd_insight_fin(msg.split(maxsplit=2)[2])
            elif low.startswith("/summary"):
                core.cmd_summary()
            elif low.startswith("/pause"):
                core.cmd_pause()
            elif low.startswith("/resume"):
                core.cmd_resume()
            elif low.startswith("/save"):
                # For v9.9 we’re not mutating core stores; summaries already saved to /summaries.
                print("[save] nothing to persist (v9.9 is non-destructive).")
            else:
                print("[INFO] commands: /state  /goal <stabilize|explore|focus>  /ethics on|off|status [care=.. fairness=.. autonomy=.. prudence=..]  /bias on|off|status  /insight cross <kw>  /insight finance <TICKER>  /summary now  /pause  /resume  /save  /quit")
    finally:
        core.stop()

if __name__ == "__main__":
    main()
