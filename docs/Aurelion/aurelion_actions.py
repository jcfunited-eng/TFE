
"""
aurelion_actions.py — Action Layer for Aurelion
-----------------------------------------------
Generates plain‑language recommendations per domain using thresholds over φ/E
and interpreter classification.
Run:
    python aurelion_actions.py
"""

import time, threading
from typing import Dict
import tkinter as tk
from tkinter import ttk
from aurelion_live import MultiDomainEngine  # uses the coupled live engine

def decide_actions(insights: Dict[str, Dict], ticker: str, query: str):
    actions = []

    # Finance
    fin = insights["Finance"]
    if "Bullish momentum" in fin["text"] and fin["phi"] > 0.6:
        actions.append(f"[Finance] Consider trend‑follow LONG on {ticker} (pilot size). Confidence {fin['conf']:.0%}.")
    elif "Bearish drift" in fin["text"] and fin["phi"] < 0.4:
        actions.append(f"[Finance] Consider reducing risk or hedging {ticker}. Confidence {fin['conf']:.0%}.")
    elif "Whipsaw" in fin["text"]:
        actions.append("[Finance] Whipsaw regime — stand aside or trade smaller size.")

    # Weather
    wea = insights["Weather"]
    if "precipitation likely" in wea["text"]:
        if "snow‑ish" in wea["text"]:
            actions.append("[Weather] Prepare for snow‑like conditions (layers, traction).")
        else:
            actions.append("[Weather] Carry an umbrella / rain gear.")
    elif "fair weather likely" in wea["text"]:
        actions.append("[Weather] Fair weather window — outdoor tasks favored.")

    # Space
    spa = insights["Space"]
    if "storm‑ish" in spa["text"]:
        actions.append("[Space] Geomagnetic turbulence — satellite/GNSS disruptions possible.")

    # Science
    sci = insights["Science"]
    if "Innovation pulse increasing" in sci["text"]:
        actions.append(f"[Science] Surge in {query} publications — consider a quick literature scan.")

    # Randomness
    rnd = insights["Randomness"]
    if "Entropy high" in rnd["text"]:
        actions.append("[System] High entropy — defer irreversible decisions until coherence improves.")

    if not actions:
        actions.append("No strong actions. Monitor and wait for higher‑confidence signals.")
    return actions

class ActionsGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Aurelion — Action Layer")
        self.geometry("900x600")
        self.engine = MultiDomainEngine(interval_sec=2.0)

        top = ttk.Frame(self); top.pack(side="top", fill="x", padx=8, pady=6)
        ttk.Label(top, text="Ticker:").pack(side="left")
        self.ticker_var = tk.StringVar(value="^IXIC")
        tk.Entry(top, textvariable=self.ticker_var, width=10).pack(side="left")
        ttk.Button(top, text="Set", command=self.set_ticker).pack(side="left", padx=4)

        ttk.Label(top, text="Science query:").pack(side="left", padx=(10,2))
        self.query_var = tk.StringVar(value="artificial intelligence")
        tk.Entry(top, textvariable=self.query_var, width=24).pack(side="left")
        ttk.Button(top, text="Set", command=self.set_query).pack(side="left", padx=4)

        self.box = tk.Text(self, height=25, wrap="word"); self.box.pack(fill="both", expand=True, padx=8, pady=6)
        self.box.config(state="disabled")

        self.running = True
        self.after(1000, self.loop)

    def set_ticker(self):
        t = self.ticker_var.get().strip()
        self.engine.set_ticker(t)

    def set_query(self):
        q = self.query_var.get().strip()
        self.engine.set_query(q)

    def loop(self):
        insights = self.engine.step_all()
        recs = decide_actions(insights, self.ticker_var.get().strip(), self.query_var.get().strip())
        txt = "Live Recommendations:\n\n" + "\n".join(f"• {r}" for r in recs) + "\n\nDetails:\n"
        for name, it in insights.items():
            txt += f"- {name}: φ={it['phi']:.2f} E={it['E']:.2f} [{it['conf']:.0%}] — {it['text']}\n"
        self.box.config(state="normal"); self.box.delete("1.0", "end"); self.box.insert("end", txt); self.box.config(state="disabled")
        if self.running:
            self.after(2000, self.loop)

def main():
    app = ActionsGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
