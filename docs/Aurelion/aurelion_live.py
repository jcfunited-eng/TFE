
# Aurelion Live v2.5 — Experiment-first UI (Actionables & Log)
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime
from rre_experiments import run_experiment

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Aurelion — Experiments (v2.5)")
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self.root); top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(top, text="RRE Experiment Runner", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)

        ctrl = ttk.Frame(self.root); ctrl.pack(fill=tk.X, padx=8)
        ttk.Label(ctrl, text="Steps:").pack(side=tk.LEFT); 
        self.steps = ttk.Entry(ctrl, width=6); self.steps.insert(0, "90"); self.steps.pack(side=tk.LEFT, padx=(4,12))
        ttk.Label(ctrl, text="Window n:").pack(side=tk.LEFT); 
        self.n = ttk.Entry(ctrl, width=6); self.n.insert(0, "256"); self.n.pack(side=tk.LEFT, padx=(4,12))
        ttk.Label(ctrl, text="Perturb every:").pack(side=tk.LEFT); 
        self.per = ttk.Entry(ctrl, width=6); self.per.insert(0, "15"); self.per.pack(side=tk.LEFT, padx=(4,12))

        self.btn = ttk.Button(ctrl, text="Run Experiment", command=self.launch)
        self.btn.pack(side=tk.LEFT, padx=(6,0))

        main = ttk.Frame(self.root); main.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        left = ttk.Frame(main); left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right = ttk.Frame(main, width=380); right.pack(side=tk.LEFT, fill=tk.Y, padx=(8,0))

        ttk.Label(left, text="Actionables", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.act = tk.Text(left, height=10, wrap=tk.WORD)
        self.act.pack(fill=tk.BOTH, expand=True)
        ttk.Label(left, text="Experiment Log (paths shown at end)", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(6,0))
        self.log = tk.Text(left, height=16, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)

        ttk.Label(right, text="Discovered Licenses", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.lic = tk.Text(right, height=10, wrap=tk.WORD); self.lic.pack(fill=tk.BOTH, expand=True)
        ttk.Label(right, text="Status", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(6,0))
        self.status = tk.Text(right, height=8, wrap=tk.WORD); self.status.pack(fill=tk.BOTH, expand=True)

        self._log("Ready. Set parameters and click Run.")

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{ts}] {msg}\n"); self.log.see(tk.END)

    def _act(self, msg):
        self.act.insert(tk.END, f"• {msg}\n"); self.act.see(tk.END)

    def _lic(self, pairs):
        self.lic.delete("1.0", tk.END)
        if not pairs:
            self.lic.insert(tk.END, "(none)\n")
            return
        for (a,b),conf in sorted(pairs.items(), key=lambda kv: kv[1], reverse=True):
            if conf > 0.6:
                self.lic.insert(tk.END, f"{a} ↔ {b}  conf≈{conf:.2f}\n")

    def launch(self):
        try:
            steps = int(self.steps.get()); n = int(self.n.get()); per = int(self.per.get())
        except Exception:
            messagebox.showerror("Error","Steps, n, and Perturb must be integers."); return
        self.btn.config(state=tk.DISABLED)
        self._log(f"Launching experiment: steps={steps}, n={n}, perturb_every={per}")
        threading.Thread(target=self._runner, args=(steps,n,per), daemon=True).start()

    def _runner(self, steps, n, per):
        out = run_experiment(steps=steps, n=n, perturb_every=per)
        self._log(f"CSV: {out['csv']}")
        self._log(f"Figure: {out['png']}")
        self._log(f"Report: {out['report']}")
        self._lic(out.get("licenses", {}))
        self.act.delete("1.0", tk.END)
        self._act("If φ dips <0.2 repeatedly → auto-increase smoothing (STABILIZE).")
        self._act("If φ remains flat + low entropy → inject probe (EXPLORE).")
        if out.get("licenses"):
            self._act("Replicate the strongest provisional coupling in a longer run to confirm.")
        self.btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
