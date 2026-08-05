
# RRE Experiments v2.5 — multimodal runs, perturbations, auto-licensing, logging
import csv, os, datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from rre_cluster import RRECluster

LOG_DIR = "experiments_logs"
os.makedirs(LOG_DIR, exist_ok=True)

def rolling_corr(a, b, w=64):
    a = np.asarray(a); b = np.asarray(b)
    n = min(a.size, b.size)
    if n < w: return 0.0
    A = pd.Series(a[-n:]).rolling(w).mean()
    B = pd.Series(b[-n:]).rolling(w).mean()
    c = A.corr(B)
    return float(0.0 if np.isnan(c) else c)

def run_experiment(steps=60, n=256, perturb_every=15, seed=None):
    rng = np.random.default_rng(seed)
    cluster = RRECluster()
    phihist = {k: [] for k in cluster.nodes}
    Hhist = {k: [] for k in cluster.nodes}
    actions = []
    lic = {}
    restab_clock = {k: None for k in cluster.nodes}
    start = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(LOG_DIR, f"experiment_{start}.csv")
    png_path = os.path.join(LOG_DIR, f"experiment_{start}.png")
    rpt_path = os.path.join(LOG_DIR, f"experiment_{start}_report.txt")
    last_perturb_t = -999

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["t"]
        for k in cluster.nodes:
            header += [f"{k}_phi", f"{k}_H"]
        header += ["action_node", "action_op", "action_amount", "note"]
        w.writerow(header)

        for t in range(steps):
            params = {}
            for name, (rre, _) in cluster.nodes.items():
                intent, _ = rre.select_intent()
                action = rre.propose_action(intent)
                params[name] = action
            if t - last_perturb_t >= perturb_every:
                target = rng.choice(list(cluster.nodes.keys()))
                params[target] = {"op": "inject_probe", "amount": 0.4, "note": "experiment_probe"}
                last_perturb_t = t
            res = cluster.step(n=n, params=params)
            row = [t]
            for k in cluster.nodes:
                phihist[k].append(res[k]["phi"]); Hhist[k].append(res[k]["H"])
                row += [res[k]["phi"], res[k]["H"]]
                if restab_clock[k] is None and res[k]["phi"] < 0.2:
                    restab_clock[k] = t
                if restab_clock[k] is not None and res[k]["phi"] > 0.5:
                    rest_time = t - restab_clock[k]
                    actions.append((t, k, {"op":"restabilized","amount":rest_time,"note":"auto"}))
                    restab_clock[k] = None
            a_node, a_op, a_amt, a_note = "", "", "", ""
            if actions:
                a_t, a_node, a = actions[-1]
                a_op = a.get("op",""); a_amt = a.get("amount",""); a_note = a.get("note","")
            row += [a_node, a_op, a_amt, a_note]
            w.writerow(row)

            keys = list(cluster.nodes.keys())
            for i in range(len(keys)):
                for j in range(i+1, len(keys)):
                    ki, kj = keys[i], keys[j]
                    c = rolling_corr(phihist[ki], phihist[kj], w=32)
                    key = (ki, kj)
                    conf = lic.get(key, 0.0)
                    conf = 0.9*conf + 0.1*max(0.0, c)
                    lic[key] = max(0.0, min(0.999, conf))

    fig, axes = plt.subplots(2, 1, figsize=(9,6), dpi=110)
    for k, series in phihist.items():
        axes[0].plot(series, label=f"{k}")
    axes[0].set_title("φ over time"); axes[0].set_ylim(0,1); axes[0].legend(loc="lower right", ncol=3, fontsize=8)
    for k, series in Hhist.items():
        axes[1].plot(series, label=f"{k}")
    axes[1].set_title("Entropy over time"); axes[1].set_ylim(0,1); axes[1].legend(loc="lower right", ncol=3, fontsize=8)
    fig.tight_layout(); fig.savefig(png_path)

    with open(rpt_path, "w", encoding="utf-8") as f:
        top = sorted(((k, v) for k,v in lic.items()), key=lambda kv: kv[1], reverse=True)[:3]
        f.write("Aurelion — Experiment Self-Report\n")
        f.write(f"Start: {start}\nSteps: {steps}\n\n")
        f.write("What I tried:\n - Periodic perturbations to probe sensitivity.\n - Intent-driven micro-actions per node.\n\n")
        f.write("What I learned:\n")
        if top and top[0][1] > 0.6:
            for (a,b),conf in top:
                f.write(f" - Provisional coupling between {a} and {b} with confidence ~{conf:.2f}.\n")
        else:
            f.write(" - No strong, stable couplings discovered yet.\n")
        f.write("\nWhat I'll try next:\n - Adjust smoothing and probe amplitude to refine sensitivity.\n")
        f.write(" - Extend runs and memory tiers for more persistent structure.\n")

    return dict(csv=csv_path, png=png_path, report=rpt_path, licenses=lic)
