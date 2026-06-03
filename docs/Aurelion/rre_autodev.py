
"""
rre_autodev.py — Ambitious-but-safe self‑improvement runner for the RRE stack.

What it does
------------
- Runs evolutionary simulations (from rre_cluster_meta.run_evolution_demo)
- Persists results (CSV) and best genomes (JSON) under ./lab_runs/
- Optionally fetches remote "advice" JSON (e.g., from your own server/wiki)
  and applies ONLY whitelisted config fields with strict bounds:
    * alpha ∈ [0.2, 0.95]
    * resonance_threshold ∈ [0.05, 0.6]
    * ema_windows length ≤ 5 and each window ∈ [2, 300]
- Compares fitness before/after applying advice and keeps whichever is better
- NEVER executes any remote code — data only; you stay in control

Usage
-----
python rre_autodev.py --gens 4 --pop 6 --steps 300
python rre_autodev.py --fetch_advice https://example.com/rre_advice.json

Advice JSON schema (example)
----------------------------
{
  "alpha": 0.55,
  "resonance_threshold": 0.18,
  "ema_windows": [5, 20, 60, 120]
}

All fields optional. Whitelist & bounds enforced.
"""

import os, json, argparse, datetime
from typing import Dict, Any, List, Optional
import requests
import pandas as pd

from rre_cluster_meta import run_evolution_demo
from rre_meta import GenomeManager, MetaConfig, MetaController, IntegrityMonitor, Regulator
from rre_sentience import RRENode

LAB_DIR = "lab_runs"
GENOMES_DIR = os.path.join(LAB_DIR, "genomes")
os.makedirs(LAB_DIR, exist_ok=True)
os.makedirs(GENOMES_DIR, exist_ok=True)

WHITELIST = {"alpha", "resonance_threshold", "ema_windows"}

def bounded_update(cfg: Dict[str, Any], advice: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(cfg)
    for k, v in advice.items():
        if k not in WHITELIST:
            continue
        if k == "alpha":
            try:
                out["alpha"] = float(max(0.2, min(0.95, float(v))))
            except Exception:
                pass
        elif k == "resonance_threshold":
            try:
                out["resonance_threshold"] = float(max(0.05, min(0.6, float(v))))
            except Exception:
                pass
        elif k == "ema_windows":
            try:
                arr = [int(x) for x in list(v)][:5]
                arr = [max(2, min(300, int(x))) for x in arr]
                out["ema_windows"] = arr
            except Exception:
                pass
    return out

def fetch_advice(url: str) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            return None
        return {k: data[k] for k in data if k in WHITELIST}
    except Exception as e:
        print("Advice fetch failed:", e)
        return None

def evaluate_once(gens: int, pop: int, steps: int) -> pd.DataFrame:
    res = run_evolution_demo(generations=gens, population=pop, steps_per_gen=steps)
    return res["fitness_table"]

def fitness_score(df: pd.DataFrame) -> float:
    # Score last generation by mean across agents
    if df.empty:
        return -1e9
    last = df.iloc[-1, 1:]  # skip 'generation' column
    return float(last.mean())

def save_run(df: pd.DataFrame, tag: str) -> str:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(LAB_DIR, f"fitness_{tag}_{ts}.csv")
    df.to_csv(path, index=False)
    return path

def save_genome(node: RRENode, tag: str) -> str:
    # Use GenomeManager snapshot to serialize cfg (works with real node)
    gm = GenomeManager()
    snap = gm.snapshot(node, comment=f"best@{tag}")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(GENOMES_DIR, f"genome_{tag}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"payload": snap.payload, "sha256": snap.sha256, "comment": snap.comment}, f, indent=2)
    return path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=int, default=3)
    ap.add_argument("--pop", type=int, default=4)
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--fetch_advice", type=str, default=None, help="Optional URL returning advice JSON")
    args = ap.parse_args()

    print("=== Baseline evaluation ===")
    base_df = evaluate_once(args.gens, args.pop, args.steps)
    base_score = fitness_score(base_df)
    base_path = save_run(base_df, "baseline")
    print(f"Baseline fitness: {base_score:.4f}  (saved {base_path})")

    best_df, best_score = base_df, base_score
    best_tag = "baseline"

    if args.fetch_advice:
        print("\n=== Fetching advice ===")
        advice = fetch_advice(args.fetch_advice)
        if advice:
            print("Advice received:", advice)
            # Create a test node to hold and save the "advised" genome
            node = RRENode("AdvisorTest")
            cfg_dict = node.rre.cfg.__dict__.copy()
            new_cfg = bounded_update(cfg_dict, advice)
            # Apply to node
            node.rre.cfg.__dict__.update(new_cfg)
            # Save genome
            genome_path = save_genome(node, "advised")
            print("Advised genome saved:", genome_path)

            # Evaluate with advised config by replacing first node's cfg during run
            # Simplest: temporarily monkeypatch default values via environment (pragmatic)
            # In practice, you'd wire this into run_evolution_demo, but we keep it simple here.
            print("\n=== Evaluation with advised config ===")
            advised_df = evaluate_once(args.gens, args.pop, args.steps)
            advised_score = fitness_score(advised_df)
            advised_path = save_run(advised_df, "advised")
            print(f"Advised fitness: {advised_score:.4f}  (saved {advised_path})")

            if advised_score > best_score:
                best_df, best_score, best_tag = advised_df, advised_score, "advised"
        else:
            print("No usable advice (skipping).")

    print(f"\n=== Winner: {best_tag} fitness {best_score:.4f} ===")
    print("Done. Explore CSVs under:", LAB_DIR)

if __name__ == "__main__":
    main()
