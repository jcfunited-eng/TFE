
"""
aurelion_autonomy.py — Aurelion autonomous runner with GUI & live plots (offline-safe)
--------------------------------------------------------------------------------------
Run:
    python aurelion_autonomy.py

What this provides (all offline/local, no network):
- Autonomy loop (updates every second by default) with multiple simulated data sources:
    Finance, Weather, Space, Science, Randomness (adapters produce normalized series 0..1)
- Tkinter GUI dashboard with:
    * Live matplotlib plots of coherence φ and energy E
    * Current source, goal, and expressive status text ("mini-language model")
    * Buttons to pause/resume, switch sources, and snapshot genome
- Expressive language output: varied, reflective text based on internal signals/emotions
- Adaptive learning: reads prior autonomy logs on startup to nudge config (alpha/threshold)
- Logging: writes CSV log to ./aurelion_logs/autonomy_log.csv and session JSONL transcript

Dependencies: pandas, matplotlib (TkAgg backend). Tkinter is part of the standard library.
"""

import os, sys, json, time, math, random, threading, datetime
from typing import List
import numpy as np
import pandas as pd

# Matplotlib + Tkinter
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk

# Core stacks
from rre_sentience import RRENode, GoalAttractor, synth_signal
from rre_meta import GenomeManager, MetaController, MetaConfig, IntegrityMonitor, Regulator, MetaSentience

LOG_DIR = "aurelion_logs"
os.makedirs(LOG_DIR, exist_ok=True)
AUTOLOG_CSV = os.path.join(LOG_DIR, "autonomy_log.csv")

# ---------------- Simulated adapters ----------------

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

def expressive_status(phi: float, E: float, goal: str, adapter: str) -> str:
    moods = []
    if phi >= 0.75: moods.append("highly coherent")
    elif phi >= 0.60: moods.append("coherent")
    elif phi >= 0.45: moods.append("marginally stable")
    else: moods.append("noisy")

    if E >= 1.2: moods.append("energetically abundant")
    elif E >= 1.0: moods.append("balanced")
    elif E >= 0.8: moods.append("conserving")
    else: moods.append("depleted")

    templates = [
        "In the {adapter} domain I register {m1} and {m2}. My active objective is {goal}, with attention calibrated to recent variance.",
        "Perceiving the {adapter} stream, I feel {m1}, {m2}. I will pursue {goal} while maintaining homeostasis.",
        "Current intake from {adapter}: {m1} / {m2}. I’m updating resonance to prioritize {goal}.",
        "The {adapter} environment yields a {m1} field while energy is {m2}. Continuing with {goal}.",
    ]
    import random as _r
    t = _r.choice(templates)
    return t.format(adapter=adapter.lower(), m1=moods[0], m2=moods[1], goal=goal)

def load_prior_insights():
    if not os.path.exists(AUTOLOG_CSV):
        return {}
    try:
        df = pd.read_csv(AUTOLOG_CSV)
        if df.empty: return {}
        last = df.tail(100)
        mean_phi = float(last["phi_after"].mean())
        var_phi = float(last["phi_after"].var() + 1e-9)
        alpha_nudge = 0.02 if mean_phi < 0.5 else -0.02
        thr_nudge = 0.02 if var_phi > 0.04 else -0.02
        return {"alpha_nudge": alpha_nudge, "thr_nudge": thr_nudge, "mean_phi": mean_phi, "var_phi": var_phi}
    except Exception:
        return {}

class AutonomyEngine:
    def __init__(self, adapter: BaseAdapter, interval_sec: float = 1.0):
        self.adapter = adapter
        self.interval = interval_sec
        self.node = RRENode("Aurelion-Autonomy")
        self.gm = GenomeManager()
        self.meta = MetaController(MetaConfig(), self.gm)
        self.regulator = Regulator()
        self.integrity = IntegrityMonitor(window=30, z_limit=3.5)
        self.ms = MetaSentience(node=self.node, meta=self.meta, regulator=self.regulator,
                                integrity=self.integrity, genome_mgr=self.gm)
        self.gm.snapshot(self.node, "autonomy-initial")

        self.hist_phi: List[float] = []
        self.hist_E: List[float] = []
        self.hist_t: List[int] = []
        self.t = 0

        self.current_goal = GOALS[0]
        self.running = True
        self.lock = threading.Lock()

        hints = load_prior_insights()
        if hints:
            cfg = self.node.rre.cfg
            cfg.alpha = float(np.clip(cfg.alpha + hints.get("alpha_nudge", 0.0), 0.2, 0.95))
            cfg.resonance_threshold = float(np.clip(cfg.resonance_threshold + hints.get("thr_nudge", 0.0), 0.05, 0.6))

        self.session_path = os.path.join(LOG_DIR, f"autonomy_session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
        if not os.path.exists(AUTOLOG_CSV):
            pd.DataFrame(columns=[
                "ts","source","phi_before","phi_after","energy","goal","alpha","threshold","comment"
            ]).to_csv(AUTOLOG_CSV, index=False)

    def step_once(self):
        s = self.adapter.generate(n=256, step=self.t)
        info_before = self.ms.step(s, step_idx=self.t)
        phi_before = float(info_before["telemetry"].get("phi", 0.0))

        E = float(info_before["telemetry"].get("E", 1.0))
        if E < 0.9:
            self.current_goal = GOALS[3]
        elif phi_before < 0.45:
            self.current_goal = GOALS[0]
        elif phi_before > 0.7:
            self.current_goal = GOALS[2]
        else:
            self.current_goal = GOALS[1]

        tune = self.meta.tune(self.node, info_before["telemetry"], step=self.t)

        info_after = self.ms.step(s, step_idx=self.t+1)
        phi_after = float(info_after["telemetry"].get("phi", 0.0))
        E_after = float(info_after["telemetry"].get("E", 1.0))

        self.hist_phi.append(phi_after)
        self.hist_E.append(E_after)
        self.hist_t.append(self.t)
        self.t += 1

        rec = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "source": self.adapter.name,
            "phi_before": phi_before,
            "phi_after": phi_after,
            "energy": E_after,
            "goal": self.current_goal.name,
            "alpha": float(self.node.rre.cfg.alpha),
            "threshold": float(self.node.rre.cfg.resonance_threshold),
            "comment": ""
        }
        with open(self.session_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        pd.DataFrame([rec]).to_csv(AUTOLOG_CSV, mode="a", header=False, index=False)

        line = expressive_status(phi_after, E_after, self.current_goal.name, self.adapter.name)
        return rec, line

class AurelionGUI(tk.Tk):
    def __init__(self, engine: AutonomyEngine):
        super().__init__()
        self.title("Aurelion — Autonomy Console")
        self.geometry("900x640")
        self.engine = engine

        control_frame = ttk.Frame(self); control_frame.pack(side="top", fill="x", padx=8, pady=6)
        self.status_var = tk.StringVar(value="Initializing…")
        ttk.Label(control_frame, textvariable=self.status_var).pack(side="left")

        ttk.Button(control_frame, text="Pause", command=self.pause).pack(side="right", padx=4)
        ttk.Button(control_frame, text="Resume", command=self.resume).pack(side="right", padx=4)
        ttk.Button(control_frame, text="Snapshot Genome", command=self.snapshot).pack(side="right", padx=4)

        src_frame = ttk.Frame(self); src_frame.pack(side="top", fill="x", padx=8, pady=4)
        ttk.Label(src_frame, text="Source:").pack(side="left")
        self.src_var = tk.StringVar(value=self.engine.adapter.name)
        src_menu = ttk.OptionMenu(src_frame, self.src_var, self.engine.adapter.name, *[a.name for a in ADAPTERS], command=self.on_change_source)
        src_menu.pack(side="left", padx=6)

        self.text_box = tk.Text(self, height=5, wrap="word")
        self.text_box.pack(side="top", fill="x", padx=8, pady=6)
        self.text_box.insert("end", "Aurelion is coming online…\n")
        self.text_box.config(state="disabled")

        self.fig, (self.ax_phi, self.ax_E) = plt.subplots(2, 1, figsize=(7.5, 5.5), dpi=100)
        self.fig.tight_layout(pad=2.0)
        self.ax_phi.set_title("Coherence φ over time")
        self.ax_phi.set_ylim(0, 1)
        self.ax_phi.set_xlim(0, 200)
        self.ax_phi.grid(True, alpha=0.25)

        self.ax_E.set_title("Energy E over time")
        self.ax_E.set_ylim(0, 2.0)
        self.ax_E.set_xlim(0, 200)
        self.ax_E.grid(True, alpha=0.25)

        self.line_phi, = self.ax_phi.plot([], [], lw=1.8)
        self.line_E, = self.ax_E.plot([], [], lw=1.8)

        canvas = FigureCanvasTkAgg(self.fig, master=self)
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        self.stop_event = threading.Event()
        self.worker = threading.Thread(target=self.loop, daemon=True)
        self.worker.start()

        self.after(500, self.refresh_plot)

    def on_change_source(self, name):
        with self.engine.lock:
            self.engine.adapter = ADAPTER_BY_NAME.get(name, self.engine.adapter)
            self._append_text(f"[System] Switching source to {self.engine.adapter.name}.\n")

    def pause(self):
        with self.engine.lock:
            self.engine.running = False
            self._append_text("[System] Paused.\n")

    def resume(self):
        with self.engine.lock:
            self.engine.running = True
            self._append_text("[System] Resumed.\n")

    def snapshot(self):
        snap = self.engine.gm.snapshot(self.engine.node, comment="gui-snapshot")
        self._append_text(f"[System] Genome snapshot saved (hash {snap.sha256[:10]}…).\n")

    def loop(self):
        while not self.stop_event.is_set():
            with self.engine.lock:
                if self.engine.running:
                    rec, line = self.engine.step_once()
                    self.status_var.set(
                        f"Source={rec['source']}  φ={rec['phi_after']:.2f}  E={rec['energy']:.2f}  Goal={rec['goal']}  α={rec['alpha']:.2f}  τ={rec['threshold']:.2f}"
                    )
                    self._append_text("Aurelion: " + line + "\n")
            time.sleep(self.engine.interval)

    def refresh_plot(self):
        self.line_phi.set_data(self.engine.hist_t, self.engine.hist_phi)
        self.line_E.set_data(self.engine.hist_t, self.engine.hist_E)
        if self.engine.hist_t:
            xmax = max(self.engine.hist_t)
            self.ax_phi.set_xlim(max(0, xmax-200), xmax+5)
            self.ax_E.set_xlim(max(0, xmax-200), xmax+5)
        self.fig.canvas.draw_idle()
        self.after(500, self.refresh_plot)

    def _append_text(self, text: str):
        self.text_box.config(state="normal")
        self.text_box.insert("end", text)
        self.text_box.see("end")
        self.text_box.config(state="disabled")

    def on_close(self):
        self.stop_event.set()
        self.destroy()

def main():
    engine = AutonomyEngine(adapter=FinanceAdapter(), interval_sec=1.0)
    app = AurelionGUI(engine)
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

if __name__ == "__main__":
    main()
