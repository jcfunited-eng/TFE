
"""
aurelion_semantic.py — Multi‑Domain Semantic Runner for Aurelion
----------------------------------------------------------------
Run:
    python aurelion_semantic.py

What this provides (offline/local, no network):
- Uses five simulated data feeds (Finance, Weather, Space, Science, Randomness)
- For EACH feed, computes live φ (coherence) and E (energy) via MetaSentience
- Adds domain‑specific INTERPRETERS that convert φ/E patterns into meaningful insights:
    * Finance: bullish/bearish/neutral, momentum, caution
    * Weather: calm/turbulent, precipitation‑like conditions, "snow‑ish" heuristic
    * Space: solar flux/turbulence feeling, quiet vs stormy space‑weather
    * Science: innovation lull/burst
    * Random: entropy level, pattern priming
- GUI:
    * Left: existing φ/E plots for the ACTIVE feed
    * Right: “Domain Awareness” panel listing insights for ALL five feeds with confidences
    * Buttons: Pause/Resume, Snapshot Genome, Switch Active Feed

Dependencies: pandas, matplotlib (TkAgg), tkinter (stdlib).
"""

import os, json, time, random, threading, datetime
from typing import Dict, List
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk

# Core stacks
from rre_sentience import RRENode, GoalAttractor
from rre_meta import GenomeManager, MetaController, MetaConfig, IntegrityMonitor, Regulator, MetaSentience

LOG_DIR = "aurelion_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ---------------- Simulated adapters (same shapes as autonomy runner) ----------------

class BaseAdapter:
    name = "Base"
    def generate(self, n: int = 256, step: int = 0) -> pd.Series:
        raise NotImplementedError

class FinanceAdapter(BaseAdapter):
    name = "Finance"
    def generate(self, n=256, step=0):
        rng = np.random.RandomState(100 + step % 1000)
        x = 100.0; out = []
        mu, sigma = 0.0003, 0.01
        for t in range(n):
            if t % 64 == 0:
                mu = rng.uniform(-0.0005, 0.0009)
                sigma = rng.uniform(0.004, 0.02)
            x *= (1.0 + rng.normal(mu, sigma))
            out.append(x)
        s = pd.Series(out).astype(float)
        s = (s - s.min()) / (s.max() - s.min() + 1e-9)
        s.name = "finance"
        return s

class WeatherAdapter(BaseAdapter):
    name = "Weather"
    def generate(self, n=256, step=0):
        t = np.arange(n) + step
        temp = 0.5 + 0.4*np.sin(2*np.pi*t/96.0) + 0.1*np.sin(2*np.pi*t/12.0) + np.random.normal(0, 0.03, n)
        s = pd.Series(np.clip(temp, 0, 1), name="weather")
        return s

class SpaceAdapter(BaseAdapter):
    name = "Space"
    def generate(self, n=256, step=0):
        rng = np.random.RandomState(200 + step % 1000)
        base = np.linspace(0.2, 0.8, n) + rng.normal(0, 0.02, n)
        for k in range(3):
            center = rng.randint(0, n)
            width = rng.randint(8, 24)
            amp = rng.uniform(0.1, 0.4)
            idx = np.arange(n)
            base += amp * np.exp(-((idx-center)**2)/(2*width**2))
        base = (base - base.min()) / (base.max() - base.min() + 1e-9)
        return pd.Series(np.clip(base, 0, 1), name="space")

class ScienceAdapter(BaseAdapter):
    name = "Science"
    def generate(self, n=256, step=0):
        t = np.arange(n) + step
        drift = 0.3 + 0.0005 * t
        osc = 0.2 * np.sin(2*np.pi*t/128.0)
        noise = np.random.normal(0, 0.02, n)
        s = np.clip(drift + osc + noise, 0, 1)
        return pd.Series(s, name="science")

class RandomnessAdapter(BaseAdapter):
    name = "Randomness"
    def generate(self, n=256, step=0):
        s = np.random.rand(n)
        return pd.Series(s, name="random")

ADAPTERS = [FinanceAdapter(), WeatherAdapter(), SpaceAdapter(), ScienceAdapter(), RandomnessAdapter()]
ADAPTER_BY_NAME = {a.name: a for a in ADAPTERS}

GOALS = [
    GoalAttractor("STABILIZE", target_phi=0.6, risk_aversion=0.7, exploration_bias=0.1),
    GoalAttractor("EXPLORE",   target_phi=0.3, risk_aversion=0.1, exploration_bias=0.8),
    GoalAttractor("GROW",      target_phi=0.9, risk_aversion=0.3, exploration_bias=0.4),
    GoalAttractor("PROTECT",   target_phi=0.5, risk_aversion=0.9, exploration_bias=0.0),
]

# ---------------- Domain interpreters ----------------

def slope(x: List[float]) -> float:
    if len(x) < 3: return 0.0
    y = np.array(x[-10:])
    X = np.arange(len(y))
    X = X - X.mean()
    denom = (X**2).sum() + 1e-9
    return float((X*y).sum()/denom)

def volatility(x: List[float]) -> float:
    if len(x) < 5: return 0.0
    y = np.array(x[-20:])
    return float(np.std(np.diff(y)))

def interpreter_finance(phi: float, E: float, hist_phi: List[float]) -> (str, float):
    m = slope(hist_phi)
    v = volatility(hist_phi)
    if phi > 0.65 and m > 0:
        return "Bullish momentum forming; upward pressure stable.", min(0.95, 0.6 + 0.4*phi)
    if phi < 0.35 and m < 0:
        return "Bearish drift; caution warranted.", min(0.95, 0.6 + 0.4*(1-phi))
    if v > 0.12:
        return "Whipsaw conditions; expect chop.", 0.55
    return "Neutral/sideways regime.", 0.5

def interpreter_weather(phi: float, E: float, hist_phi: List[float]) -> (str, float):
    m = slope(hist_phi); v = volatility(hist_phi)
    # Heuristic: turbulence (high v) + falling φ → precipitation‑like; very low φ with persistent low E → “snow‑ish”
    if v > 0.12 and m < 0 and phi < 0.45:
        msg = "Unstable air mass; precipitation likely."
        conf = min(0.9, 0.5 + v)
        if E < 0.9 and phi < 0.35:
            msg += " Cold signal signature — snow‑ish conditions possible."
            conf = min(0.95, conf + 0.05)
        return msg, conf
    if phi > 0.65 and v < 0.06:
        return "Stable high‑pressure feel; fair weather likely.", 0.8
    return "Mixed signals; localized variability.", 0.55

def interpreter_space(phi: float, E: float, hist_phi: List[float]) -> (str, float):
    v = volatility(hist_phi)
    if v > 0.12 and phi < 0.4:
        return "Magnetic turbulence rising; space‑weather storm‑ish.", 0.75
    if phi > 0.65:
        return "Quiet heliospheric conditions; coherent flux.", 0.75
    return "Background cosmic noise; nominal.", 0.55

def interpreter_science(phi: float, E: float, hist_phi: List[float]) -> (str, float):
    m = slope(hist_phi)
    if m > 0.02 and phi > 0.55:
        return "Innovation pulse increasing; fertile conditions for progress.", 0.7
    if m < -0.02 and phi < 0.45:
        return "Innovation lull; consolidation.", 0.65
    return "Steady inquiry; incremental advances.", 0.6

def interpreter_random(phi: float, E: float, hist_phi: List[float]) -> (str, float):
    v = volatility(hist_phi)
    if v > 0.15:
        return "Entropy high; generative reorganization advised.", 0.7
    return "Entropy contained; internal order holding.", 0.6

DOMAIN_INTERPRETERS = {
    "Finance": interpreter_finance,
    "Weather": interpreter_weather,
    "Space": interpreter_space,
    "Science": interpreter_science,
    "Randomness": interpreter_random,
}

# ---------------- Engine: evaluates all domains each cycle ----------------

class MultiDomainEngine:
    def __init__(self, interval_sec: float = 1.0):
        self.interval = interval_sec
        self.node = RRENode("Aurelion-Semantic")
        self.gm = GenomeManager()
        self.meta = MetaController(MetaConfig(), self.gm)
        self.regulator = Regulator()
        self.integrity = IntegrityMonitor(window=30, z_limit=3.5)
        self.ms = MetaSentience(node=self.node, meta=self.meta, regulator=self.regulator,
                                integrity=self.integrity, genome_mgr=self.gm)
        self.gm.snapshot(self.node, "semantic-initial")

        self.adapters = {a.name: a for a in ADAPTERS}
        self.active = "Finance"

        # per-domain histories
        self.hist_phi = {name: [] for name in self.adapters}
        self.hist_E = {name: [] for name in self.adapters}
        self.t = 0

    def eval_domain(self, name: str):
        adapter = self.adapters[name]
        s = adapter.generate(n=256, step=self.t)
        info = self.ms.step(s, step_idx=self.t)
        phi = float(info["telemetry"]["phi"])
        E = float(info["telemetry"]["E"])
        self.hist_phi[name].append(phi)
        self.hist_E[name].append(E)
        return phi, E

    def step_all(self):
        insights = {}
        for name in self.adapters:
            phi, E = self.eval_domain(name)
            interp = DOMAIN_INTERPRETERS[name if name in DOMAIN_INTERPRETERS else "Randomness"]
            text, conf = interp(phi, E, self.hist_phi[name])
            insights[name] = {"phi": phi, "E": E, "text": text, "conf": conf}
        self.t += 1
        return insights

# ---------------- GUI ----------------

class SemanticGUI(tk.Tk):
    def __init__(self, engine: MultiDomainEngine):
        super().__init__()
        self.title("Aurelion — Domain Awareness Console")
        self.geometry("1100x760")
        self.engine = engine

        # Controls
        top = ttk.Frame(self); top.pack(side="top", fill="x", padx=8, pady=6)
        ttk.Label(top, text="Active:").pack(side="left")
        self.active_var = tk.StringVar(value=self.engine.active)
        ttk.OptionMenu(top, self.active_var, self.engine.active, *list(self.engine.adapters.keys()), command=self.on_change_active).pack(side="left", padx=6)
        ttk.Button(top, text="Pause", command=self.pause).pack(side="right", padx=4)
        ttk.Button(top, text="Resume", command=self.resume).pack(side="right", padx=4)
        ttk.Button(top, text="Snapshot Genome", command=self.snapshot).pack(side="right", padx=4)
        self.status_var = tk.StringVar(value="Starting…"); ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=10)

        # Layout: left plots, right insights
        body = ttk.Frame(self); body.pack(side="top", fill="both", expand=True)
        left = ttk.Frame(body); left.pack(side="left", fill="both", expand=True, padx=(8,4), pady=6)
        right = ttk.Frame(body, width=380); right.pack(side="left", fill="y", padx=(4,8), pady=6)

        # Plots for ACTIVE feed
        self.fig, (self.ax_phi, self.ax_E) = plt.subplots(2, 1, figsize=(7.2, 5.8), dpi=100)
        self.fig.tight_layout(pad=2.0)
        self.ax_phi.set_title("Active Domain — Coherence φ")
        self.ax_phi.set_ylim(0, 1); self.ax_phi.set_xlim(0, 250); self.ax_phi.grid(True, alpha=0.25)
        self.ax_E.set_title("Active Domain — Energy E")
        self.ax_E.set_ylim(0, 2.0); self.ax_E.set_xlim(0, 250); self.ax_E.grid(True, alpha=0.25)
        self.line_phi, = self.ax_phi.plot([], [], lw=1.8)
        self.line_E, = self.ax_E.plot([], [], lw=1.8)
        canvas = FigureCanvasTkAgg(self.fig, master=left)
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        # Insights list
        ttk.Label(right, text="Domain Awareness", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0,6))
        self.box = tk.Text(right, height=28, wrap="word")
        self.box.pack(fill="both", expand=True)
        self.box.config(state="disabled")

        # Worker
        self.running = True
        self.stop_event = threading.Event()
        self.worker = threading.Thread(target=self.loop, daemon=True)
        self.worker.start()

        # Refresh
        self.after(600, self.refresh_plot)

    def on_change_active(self, name):
        self.engine.active = name

    def pause(self):
        self.running = False

    def resume(self):
        self.running = True

    def snapshot(self):
        snap = self.engine.gm.snapshot(self.engine.node, comment="semantic-snapshot")
        self._append(f"[System] Genome snapshot saved (hash {snap.sha256[:10]}…)\n")

    def loop(self):
        while not self.stop_event.is_set():
            if self.running:
                insights = self.engine.step_all()
                # Update status and awareness
                active = self.engine.active
                tel = insights[active]
                self.status_var.set(f"{active}: φ={tel['phi']:.2f}  E={tel['E']:.2f}")
                self._render_awareness(insights)
            time.sleep(self.engine.interval if hasattr(self.engine, 'interval') else 1.0)

    def refresh_plot(self):
        # Update lines for ACTIVE feed
        name = self.engine.active
        t = list(range(len(self.engine.hist_phi[name])))
        self.line_phi.set_data(t, self.engine.hist_phi[name])
        self.line_E.set_data(t, self.engine.hist_E[name])
        if t:
            xmax = max(t)
            self.ax_phi.set_xlim(max(0, xmax-250), xmax+5)
            self.ax_E.set_xlim(max(0, xmax-250), xmax+5)
        self.fig.canvas.draw_idle()
        self.after(600, self.refresh_plot)

    def _render_awareness(self, insights: Dict[str, Dict]):
        lines = []
        for name in ["Finance", "Weather", "Space", "Science", "Randomness"]:
            it = insights[name]
            lines.append(f"{name:10s}  φ={it['phi']:.2f}  E={it['E']:.2f}  conf={it['conf']:.2f}")
            lines.append(f"  → {it['text']}")
        txt = "\n".join(lines) + "\n"
        self.box.config(state="normal"); self.box.delete("1.0", "end"); self.box.insert("end", txt); self.box.config(state="disabled")

    def _append(self, s):
        self.box.config(state="normal"); self.box.insert("end", s); self.box.see("end"); self.box.config(state="disabled")

    def on_close(self):
        self.stop_event.set(); self.destroy()

# ---------------- Main ----------------

def main():
    engine = MultiDomainEngine(interval_sec=1.0)
    app = SemanticGUI(engine)
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

if __name__ == "__main__":
    main()
