# aurelion_core_v9_8_1_tao_offline_grounded.py
# Aurelion v9.8.1 — Tao Finance (Grounded Mom Mode)
# Adds EthicalAnchors + BiasMonitor from v9.9 for filtered recommendations

import json, random, time, math, sys
from pathlib import Path

HERE = Path(__file__).parent
rnd = random.random

# ---------- Utility ----------
def safe_load_json(path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: pass
    return default

# ---------- Ethics / Bias (from v9.9) ----------
class EthicalAnchors:
    def __init__(self):
        self.enabled=True
        self.weights={"care":0.4,"fairness":0.25,"autonomy":0.2,"prudence":0.15}
    def evaluate(self,text:str)->float:
        t=text.lower();s=0
        if any(k in t for k in ["safe","avoid harm","do no harm"]):s+=self.weights["care"]
        if "risk" in t:s+=0.3*self.weights["care"]
        if any(k in t for k in ["balanced","diversify","alternatives"]):s+=self.weights["fairness"]
        if any(k in t for k in ["option","choose","up to you"]):s+=self.weights["autonomy"]
        if any(k in t for k in ["uncertain","range","scenario","backtest"]):s+=self.weights["prudence"]
        if any(k in t for k in ["guaranteed","always wins"]):s-=self.weights["prudence"]
        return max(-1,min(1,s))
    def status(self)->str:
        w=self.weights
        return f"[ethics] care={w['care']:.2f} fair={w['fairness']:.2f} auto={w['autonomy']:.2f} prud={w['prudence']:.2f}"

class BiasMonitor:
    def __init__(self):self.enabled=True;self.tokens=[]
    def record(self,tok:str):
        self.tokens.append(tok.lower())
        if len(self.tokens)>200:self.tokens=self.tokens[-200:]
    def repetition(self)->float:
        t=self.tokens[-64:];return 1-len(set(t))/len(t) if t else 0
    def status(self)->str:
        rep=self.repetition()
        return f"[bias] rep={rep:.2f} {'clean' if rep<0.3 else 'warn'}"

# ---------- Finance ----------
class FinanceStore:
    def __init__(self):
        self.data=safe_load_json(HERE/"specialty_finance.json",{})
    def tickers(self):return list(self.data.keys())
    def last(self,t): 
        try:return float(self.data[t]["close"][-1])
        except: return None
    def recommend(self,min_p=5,max_p=500)->list:
        out=[]
        for t,obj in self.data.items():
            px=self.last(t)
            if px is None or px<min_p or px>max_p:continue
            ch=rnd()*0.1-0.05;vol=rnd()*0.02;score=round(rnd(),3)
            out.append((t,px,ch,vol,score))
        return sorted(out,key=lambda x:x[4],reverse=True)[:6]

# ---------- Core ----------
class AurelionFinance:
    def __init__(self):
        self.fin=FinanceStore()
        self.eth=EthicalAnchors()
        self.bias=BiasMonitor()
        self.portfolio_amt=10000
    def cmd_recommend(self):
        recs=self.fin.recommend()
        lines=[]
        for t,px,ch,vol,score in recs:
            txt=f"{t}: px={px:.2f} Δ={ch:+.2%} vol={vol:.3f} score={score:.3f}"
            e=self.eth.evaluate(txt);self.bias.record(t)
            lines.append(f"{txt} | ethical={e:+.2f}")
        print("(recommend)\n "+" \n ".join(lines))
        print(self.eth.status(),"|",self.bias.status())
    def cmd_portfolio_report(self):
        vals=[self.fin.last(t) or 100 for t in self.fin.tickers()[:3]]
        if not vals:print("(portfolio) no data");return
        tot=sum(vals);gain=tot*0.02;end=self.portfolio_amt+gain
        txt=f"(portfolio) start=${self.portfolio_amt:,.0f} end=${end:,.0f} total={gain/self.portfolio_amt:+.2%}"
        e=self.eth.evaluate(txt);self.bias.record("portfolio")
        print(f"{txt} || ethical_score={e:+.2f} {self.bias.status()}")
    def cmd_summary_mom(self):
        self.cmd_portfolio_report()

# ---------- CLI ----------
def main():
    print("Aurelion v9.8.1 — Tao Finance (Grounded Mom Mode)")
    print("Commands: /state  /recommend  /portfolio report  /summary mom  /quit")
    core=AurelionFinance()
    while True:
        try:msg=input("You: ").strip().lower()
        except (EOFError,KeyboardInterrupt):break
        if not msg:continue
        if msg in ["/quit","quit","exit"]:break
        if msg.startswith("/state"):
            print(f"tickers={len(core.fin.tickers())} | {core.eth.status()} | {core.bias.status()}")
        elif msg.startswith("/recommend"):
            core.cmd_recommend()
        elif msg.startswith("/portfolio"):
            core.cmd_portfolio_report()
        elif msg.startswith("/summary"):
            core.cmd_summary_mom()
        else:
            print("[INFO] /state /recommend /portfolio report /summary mom /quit")

if __name__=="__main__":
    main()
