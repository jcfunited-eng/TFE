# learning_harness.py
# Aurelion — Safe Learning Harness (trusted corpora → multimodal language field)
# Compatible with your MultimodalField class.

import os, json, csv, re, argparse
from pathlib import Path
from datetime import datetime
import numpy as np

try:
    import matplotlib.pyplot as plt
    HAVE_PLOT = True
except Exception:
    HAVE_PLOT = False

# --- Aurelion imports ---
from language_field import LanguageFieldLearner
from morphospace_multimodal import MultimodalField, Mosaic, SemanticHub
from primitive_sensory_pack import senses_from_text, DIMS

# ---------------------------------
# Utility: safe tokenization
# ---------------------------------
_word_re = re.compile(r"[A-Za-z][A-Za-z\-']+")

def simple_tokens(text: str):
    return [w.lower() for w in _word_re.findall(text)]

def chunk_text(text: str, max_words=90):
    words = simple_tokens(text)
    for i in range(0, len(words), max_words):
        yield " ".join(words[i:i+max_words])

# ---------------------------------
# Concept visualization (optional)
# ---------------------------------
def concept_map_png(learner: LanguageFieldLearner, out_png: Path):
    try:
        from sklearn.manifold import TSNE
    except Exception:
        return
    labels, vecs = [], []
    for tok in learner.memory.get("lexical", {}):
        labels.append(tok)
        parts = []
        for m in DIMS.keys():
            v = learner.memory[m].get(tok)
            if v is None:
                v = np.zeros(DIMS[m], dtype=np.float32)
            parts.append(v)
        vecs.append(np.concatenate(parts))
    if not vecs:
        return
    X = np.stack(vecs)
    tsne = TSNE(n_components=2, perplexity=min(30, max(5, len(labels)//2)), n_iter=500, learning_rate="auto", init="random")
    Y = tsne.fit_transform(X)
    if not HAVE_PLOT:
        return
    plt.figure(figsize=(7,5))
    plt.scatter(Y[:,0], Y[:,1], s=40, alpha=0.85)
    for (x,y), lab in zip(Y, labels):
        plt.text(x+3, y+3, lab, fontsize=9)
    plt.title("Aurelion — Concept Resonance Map")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()

# ---------------------------------
# Run harness
# ---------------------------------
def run_harness(root: Path, outdir: Path, max_files: int, max_chunks: int, alpha: float, report_every: int, plot_map: bool):
    outdir.mkdir(parents=True, exist_ok=True)

    # Initialize learner + multimodal field
    learner = LanguageFieldLearner(memory_path=str(outdir / "language_memory.json"))
    modalities = {m: Mosaic(m, DIMS[m]) for m in DIMS.keys()}
    field = MultimodalField(modalities=modalities, hub=SemanticHub(dim=64))

    all_txt = sorted(root.rglob("*.txt"))
    if max_files:
        all_txt = all_txt[:max_files]

    csv_path = outdir / "learning_log.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fcsv:
        w = csv.writer(fcsv)
        w.writerow(["step","file","chunk","phi","H","energy"] + list(DIMS.keys()))
        step = 0
        for fp in all_txt:
            try:
                text = Path(fp).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for ci, chunk in enumerate(chunk_text(text, max_words=90)):
                if max_chunks and ci >= max_chunks:
                    break
                senses = senses_from_text(chunk)
                learner.learn(chunk, senses)
                field.stimulate(senses, alpha=alpha)
                phi = float(field.hub.energy)
                H = 0.0
                energy = phi
                row = [step, fp.name, ci, f"{phi:.3f}", f"{H:.3f}", f"{energy:.3f}"]
                for m in DIMS.keys():
                    v = field.modalities[m].a
                    row.append(f"{np.linalg.norm(v):.3f}" if v is not None else "0.000")
                w.writerow(row)
                step += 1
                if report_every and step % report_every == 0:
                    print(f"[{step}] φ={phi:.3f}  file={fp.name} chunk={ci}")

    learner.save()
    if plot_map:
        concept_map_png(learner, outdir / "concept_map.png")

    print("\n=== Learning run complete ===")
    print(f"Learning log: {csv_path}")
    if plot_map:
        print(f"Concept map: {outdir / 'concept_map.png'}")
    print(f"Memory saved: {outdir / 'language_memory.json'}")

# ---------------------------------
# CLI
# ---------------------------------
def main():
    ap = argparse.ArgumentParser(description="Aurelion — Safe Learning Harness (v4 compatible)")
    ap.add_argument("--root", type=str, default="corpora", help="Trusted text folder")
    ap.add_argument("--out", type=str, default=None, help="Output folder")
    ap.add_argument("--max_files", type=int, default=50)
    ap.add_argument("--max_chunks", type=int, default=60)
    ap.add_argument("--alpha", type=float, default=0.55)
    ap.add_argument("--report_every", type=int, default=50)
    ap.add_argument("--no_plot", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        raise SystemExit(f"Corpora folder not found: {root}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.out) if args.out else Path("learning_runs") / ts

    run_harness(
        root=root,
        outdir=outdir,
        max_files=args.max_files,
        max_chunks=args.max_chunks,
        alpha=args.alpha,
        report_every=args.report_every,
        plot_map=(not args.no_plot)
    )

if __name__ == "__main__":
    main()
