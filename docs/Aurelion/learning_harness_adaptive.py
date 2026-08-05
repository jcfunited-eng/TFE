# learning_harness_adaptive.py
# Aurelion v4.2 — Adaptive-Resonance Learning Harness
# Reads a text corpus directory, modulates α based on internal φ drift.

import os, time, json, numpy as np, pandas as pd
from pathlib import Path
from datetime import datetime
from language_field import LanguageFieldLearner
from morphospace_multimodal import senses_from_text, MorphospaceMultimodal
from primitive_sensory_pack import DIMS

def run_harness(root="corpora", max_files=50, max_chunks=60,
                alpha_start=0.55, alpha_min=0.25, alpha_max=0.85,
                sensitivity=0.35, outdir="learning_runs"):
    """
    Reads all .txt files under `root`, chunking text and adapting α as φ drifts.
    """
    root = Path(root)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(outdir) / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    learner = LanguageFieldLearner(memory_path=str(run_dir / "language_memory.json"))
    field = MorphospaceMultimodal()

    log = []
    alpha = alpha_start
    last_phi = 0.5

    txt_files = [p for p in root.rglob("*.txt")][:max_files]
    print(f"[INFO] Starting adaptive run on {len(txt_files)} files")

    for idx, fp in enumerate(txt_files):
        text = open(fp, "r", encoding="utf-8", errors="ignore").read()
        chunks = [text[i:i+1000] for i in range(0, len(text), 1000)][:max_chunks]

        for c_idx, chunk in enumerate(chunks):
            senses = senses_from_text(chunk)
            field.stimulate(senses, alpha=alpha)
            phi = float(field.phi)
            energy = float(field.energy)

            # --- adaptive α logic ---
            delta = phi - last_phi
            last_phi = phi
            alpha = np.clip(alpha + sensitivity * delta, alpha_min, alpha_max)

            learner.learn(chunk, senses)
            log.append([idx, c_idx, phi, energy, alpha, fp.name])

            if len(log) % 50 == 0:
                print(f"[{len(log)}] φ={phi:.3f} α={alpha:.3f} file={fp.name} chunk={c_idx}")

    # --- Save results ---
    learner.save()
    pd.DataFrame(log, columns=["file_idx","chunk","phi","energy","alpha","file"]).to_csv(
        run_dir / "learning_log.csv", index=False)
    print(f"\n=== Adaptive run complete ===")
    print(f"Run folder: {run_dir}")
    print(f"Learned {len(log)} chunks across {len(txt_files)} files.")
    print(f"Final α={alpha:.3f}, φ={last_phi:.3f}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Aurelion Adaptive-Resonance Harness")
    ap.add_argument("--root", default="corpora")
    ap.add_argument("--max_files", type=int, default=50)
    ap.add_argument("--max_chunks", type=int, default=60)
    ap.add_argument("--alpha_start", type=float, default=0.55)
    ap.add_argument("--outdir", default="learning_runs")
    args = ap.parse_args()
    run_harness(
        root=args.root,
        max_files=args.max_files,
        max_chunks=args.max_chunks,
        alpha_start=args.alpha_start,
        outdir=args.outdir
    )
