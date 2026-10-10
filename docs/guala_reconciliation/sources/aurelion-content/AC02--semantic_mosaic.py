from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Optional, Dict
import json, os, datetime


# ---------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------

def embed_sentences(text: str, model: Optional[SentenceTransformer] = None):
    """Return embeddings and sentences using a provided or new SentenceTransformer model."""
    if model is None:
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 5]
    if not sentences:
        return np.zeros((1, 384)), [""], model  # safety for empty inputs
    X = model.encode(sentences, show_progress_bar=False)
    return np.array(X), sentences, model


def _cluster_with_warmstart(X: np.ndarray, k: int = 6, proto_centroids: Optional[np.ndarray] = None):
    """Cluster embeddings with optional warm-start centroids."""
    n = X.shape[0]
    if n < 2:
        return np.zeros(n, dtype=int), 1

    cl = AgglomerativeClustering(
        n_clusters=min(k, max(2, n // 4)),
        metric='cosine',
        linkage='average',
        distance_threshold=None
    )
    labels = cl.fit_predict(X)

    if proto_centroids is not None and len(proto_centroids) > 0:
        try:
            csim = cosine_similarity(X, proto_centroids)
            labels = np.argmax(csim, axis=1)
        except Exception:
            pass

    return labels, len(set(labels))


def _coherence_entropy_energy(X: np.ndarray, labels: np.ndarray):
    """Compute coherence φ, entropy H, and synthetic energy."""
    phi_vals = []
    for cid in np.unique(labels):
        idx = np.where(labels == cid)[0]
        if len(idx) < 2:
            continue
        subX = X[idx]
        sim = cosine_similarity(subX)
        phi_vals.append(np.mean(sim))
    phi = float(np.mean(phi_vals)) if phi_vals else 0.0

    counts = np.bincount(labels)
    probs = counts / np.sum(counts)
    H = -np.sum(probs * np.log2(probs + 1e-9))
    energy = float(phi * np.exp(-H / 10))
    return phi, H, energy, len(phi_vals)


def run_semantic_mosaic(
    text: str,
    k: int = 6,
    seed_centroids: Optional[np.ndarray] = None,
    model: Optional[SentenceTransformer] = None
):
    """Core Mosaic generation with semantic embeddings."""
    X, sentences, model = embed_sentences(text, model=model)
    X = normalize(X)

    labels, k_eff = _cluster_with_warmstart(X, k=k, proto_centroids=seed_centroids)
    phi, H, energy, clusters = _coherence_entropy_energy(X, labels)

    # Calculate centroids for persistence
    centroids = []
    for cid in np.unique(labels):
        idx = np.where(labels == cid)[0]
        centroids.append(np.mean(X[idx], axis=0))
    centroids = np.array(centroids)

    payload = {
        "phi": phi,
        "H": H,
        "energy": energy,
        "clusters": int(clusters),
        "sentences": sentences,
        "labels": labels.tolist(),
        "centroids": centroids.tolist(),
        "embedder": model  # <-- critical for Aurelion_core_v36.py
    }
    return payload


# ---------------------------------------------------------------------
# Persistent Mosaic Memory Utilities
# ---------------------------------------------------------------------

def load_persistent_mosaics(path: str = "mosaic_memory.jsonl") -> List[np.ndarray]:
    if not os.path.exists(path):
        return []
    mosaics = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                if "centroids" in data:
                    mosaics.append(np.array(data["centroids"]))
            except json.JSONDecodeError:
                continue
    return mosaics


def save_persistent_mosaic(centroids: np.ndarray, meta: Dict, path: str = "mosaic_memory.jsonl"):
    if centroids is None or not len(centroids):
        return
    record = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "centroids": centroids.tolist(),
        "meta": meta,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------
# CLI Entry
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Semantic Mosaic Clustering")
    parser.add_argument("--corpus", required=True, help="Path to text corpus")
    parser.add_argument("--k", type=int, default=6, help="Number of target clusters")
    parser.add_argument("--out", default="mosaic_result.json", help="Output file")
    args = parser.parse_args()

    with open(args.corpus, "r", encoding="utf-8") as f:
        text = f.read()

    payload = run_semantic_mosaic(text, k=args.k)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"✅ Saved {args.out} | φ={payload['phi']:.3f}, H={payload['H']:.3f}, energy={payload['energy']:.3f}")
