# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, csv, datetime
from pathlib import Path

from semantic_mosaic import run_semantic_mosaic
from intent_field import IntentField
from memory_ring import MemoryRing

def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def domain_from_path(p: Path) -> str:
    name = p.stem.lower()
    if any(k in name for k in ("fin", "sec", "market", "stock", "nasdaq", "sp500")):
        return "finance"
    if any(k in name for k in ("weather", "noaa", "forecast", "meteo", "storm")):
        return "weather"
    if any(k in name for k in ("nasa", "esa", "space", "mission", "science", "paper")):
        return "science"
    if "neutral" in name or "baseline" in name:
        return "neutral"
    return name

def main():
    ap = argparse.ArgumentParser(description="Aurelion v3.5 — Semantic Batch Cognition")
    ap.add_argument("--batch", required=True, help="Folder containing .txt corpora")
    ap.add_argument("--k", type=int, default=6, help="target clusters per corpus")
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
    csv_path = outdir / f"cognition_semantic_{ts}.csv"

    print("\nAurelion v3.5 — Semantic Cognitive Batch\n" + "="*76)
    print(f"{'domain':12} {'\u03d5':>6} {'H':>6} {'energy':>7}  {'intent':10}  tokens / meta-mosaic tokens")

    for p in files:
        text = load_text(p)
        payload = run_semantic_mosaic(text, k=args.k)

        dom = domain_from_path(p)
        phi = payload["phi"]; H = payload["H"]; energy = payload["energy"]
        decision = intent.decide(phi, H, energy)

        memory.append({
            "domain": dom, "phi": phi, "H": H, "energy": energy,
            "intent": decision.intent, "tokens": payload.get("tokens", [])
        })

        meta_tokens = []
        if payload.get("meta_mosaics"):
            meta_tokens = payload["meta_mosaics"][0].get("tokens", [])[:8]

        print(f"{dom:12} {phi:6.3f} {H:6.3f} {energy:7.3f}  "
              f"{decision.intent:10}  {', '.join(payload.get('tokens', [])[:6])} "
              f"| {'; '.join(meta_tokens)}")

        rows.append({
            "file": str(p.name),
            "domain": dom,
            "phi": phi,
            "H": H,
            "energy": energy,
            "intent": decision.intent,
            "reason": decision.reason,
            "tokens": " ".join(payload.get("tokens", [])),
            "meta_tokens": " ".join(meta_tokens)
        })

    snap = memory.snapshot()
    print("\nMemory snapshot:", snap)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file","domain","phi","H","energy","intent","reason","tokens","meta_tokens"])
        w.writeheader()
        w.writerows(rows)

    print(f"\nSaved batch summary: {csv_path}")

if __name__ == "__main__":
    main()
