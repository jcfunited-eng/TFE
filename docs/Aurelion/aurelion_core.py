# -*- coding: utf-8 -*-
"""
aurelion_core.py — Batch cognition loop (Multi-Corpus + Intent + Memory)

Usage:
    python aurelion_core.py --batch "C:\\path\\to\\corpora_folder"

The folder may contain .txt files for any domains (finance, weather, science, etc.).
For each file:
  • Run Mosaic (from mosaic_cluster.py)
  • Summarize metrics
  • Decide intent (intent_field.py)
  • Append to memory rings (memory_ring.py)
  • Print a compact comparison table
  • Save CSV summary: cognition_reports/cognition_YYYYMMDD_HHMMSS.csv
"""

from __future__ import annotations
import argparse, csv, datetime
from pathlib import Path

from mosaic_cluster import load_corpus, discover_mosaics
from intent_field import IntentField
from memory_ring import MemoryRing

def summarize_payload(payload: dict) -> dict:
    """Return a compact summary of the mosaic run."""
    if payload.get("status") != "ok":
        return {"ok": False, "phi": 0.0, "H": 0.0, "energy": 0.0, "tokens": []}

    clusters = payload.get("clusters", [])
    if not clusters:
        return {"ok": True, "phi": payload.get("recent_phi_mean",0.0),
                "H": payload.get("recent_H_mean",1.0), "energy": 0.0, "tokens": []}

    # Use top cluster for tokens, compute energy mean across clusters
    top = clusters[0]
    e_mean = sum(c.get("energy",0.0) for c in clusters)/len(clusters)
    tokens = top.get("tokens", [])[:10]
    return {
        "ok": True,
        "phi": float(payload.get("recent_phi_mean", 0.0)),
        "H":   float(payload.get("recent_H_mean",   0.0)),
        "energy": float(e_mean),
        "tokens": tokens
    }

def domain_from_path(p: Path) -> str:
    # Try to infer a domain from filename keywords; fallback to stem
    name = p.stem.lower()
    if any(k in name for k in ("fin", "sec", "market", "stock", "nasdaq", "sp500")):
        return "finance"
    if any(k in name for k in ("weather", "noaa", "forecast", "meteo", "storm")):
        return "weather"
    if any(k in name for k in ("nasa", "esa", "space", "mission", "science", "paper")):
        return "science"
    return name

def main():
    ap = argparse.ArgumentParser(description="Aurelion Core — Multi-Corpus Cognition")
    ap.add_argument("--batch", required=True, help="Folder containing .txt corpora")
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--window", type=int, default=256)
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--min_cluster", type=int, default=3)
    ap.add_argument("--top_terms", type=int, default=600)
    args = ap.parse_args()

    folder = Path(args.batch)
    files = sorted([p for p in folder.glob("*.txt") if p.is_file()])
    if not files:
        print("No .txt files found in the batch folder.")
        return

    intent = IntentField()
    memory = MemoryRing()
    rows = []
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path("cognition_reports")
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / f"cognition_{ts}.csv"

    print("\nAurelion — Cognitive Batch\n" + "="*72)
    print(f"{'domain':12} {'φ':>6} {'H':>6} {'energy':>7}  {'intent':10}  tokens")

    for p in files:
        text = load_corpus(str(p))
        payload = discover_mosaics(
            text=text,
            steps=args.steps,
            window=args.window,
            top_terms=args.top_terms,
            k=args.k,
            min_cluster=args.min_cluster
        )
        summary = summarize_payload(payload)
        dom = domain_from_path(p)

        # Decide intent from metrics
        decision = intent.decide(summary["phi"], summary["H"], summary["energy"])

        # Persist to memory
        memory.append({
            "domain": dom,
            "phi": summary["phi"],
            "H": summary["H"],
            "energy": summary["energy"],
            "intent": decision.intent,
            "tokens": summary["tokens"]
        })

        print(f"{dom:12} {summary['phi']:6.3f} {summary['H']:6.3f} {summary['energy']:7.3f}  "
              f"{decision.intent:10}  {', '.join(summary['tokens'])}")

        rows.append({
            "file": str(p.name),
            "domain": dom,
            "phi": round(summary["phi"], 4),
            "H": round(summary["H"], 4),
            "energy": round(summary["energy"], 4),
            "intent": decision.intent,
            "reason": decision.reason,
            "tokens": " ".join(summary["tokens"])
        })

    # Memory snapshot for quick health check
    snap = memory.snapshot()
    print("\nMemory snapshot:", snap)

    # Save CSV summary
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file","domain","phi","H","energy","intent","reason","tokens"])
        w.writeheader()
        w.writerows(rows)

    print(f"\nSaved batch summary: {csv_path}")

if __name__ == "__main__":
    main()
