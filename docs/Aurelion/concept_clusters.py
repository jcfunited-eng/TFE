# concept_clusters.py
# Aurelion v4 — Concept Clustering & Resonance Neighborhoods

import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.cluster import SpectralClustering
from primitive_sensory_pack import DIMS

def build_concept_matrix(learner):
    """Aggregate all learned tokens across modalities into a common space."""
    mods = list(DIMS.keys())
    max_dim = max(DIMS.values())
    concepts = sorted(
        {tok for m in learner.memory.values() for tok in m.keys()}
    )
    if not concepts:
        print("[No concepts learned yet]")
        return None, None, None

    mat = np.zeros((len(concepts), len(mods) * max_dim), dtype=np.float32)
    for i, tok in enumerate(concepts):
        vec_parts = []
        for mod in mods:
            v = learner.memory.get(mod, {}).get(tok)
            if v is None:
                v = np.zeros(DIMS[mod], dtype=np.float32)
            if v.shape[0] < max_dim:
                v = np.pad(v, (0, max_dim - v.shape[0]))
            vec_parts.append(v)
        vec = np.concatenate(vec_parts)
        mat[i] = vec / (np.linalg.norm(vec) + 1e-8)
    return concepts, mods, mat


def visualize_concept_space(learner, n_clusters=6):
    """Cluster all learned concepts and visualize their resonance neighborhoods."""
    concepts, mods, mat = build_concept_matrix(learner)
    if mat is None:
        return

    print(f"[INFO] Clustering {len(concepts)} learned concepts...")

    # Compute cosine similarity matrix
    sim = np.dot(mat, mat.T)
    sim = (sim + 1) / 2  # normalize to [0,1]

    # Cluster concepts
    clustering = SpectralClustering(
        n_clusters=min(n_clusters, len(concepts)//2 or 1),
        affinity="precomputed",
        assign_labels="discretize",
        random_state=42
    ).fit(sim)
    labels = clustering.labels_

    # 2D projection
    tsne = TSNE(n_components=2, metric="cosine", random_state=42, perplexity=10)
    coords = tsne.fit_transform(mat)

    # Plot
    plt.figure(figsize=(8, 6))
    scatter = plt.scatter(coords[:, 0], coords[:, 1], c=labels, cmap="tab10", s=60, alpha=0.9)
    for i, tok in enumerate(concepts):
        plt.text(coords[i, 0], coords[i, 1], tok, fontsize=8, alpha=0.75)
    plt.title("Aurelion — Concept Resonance Map")
    plt.xlabel("t-SNE dim 1")
    plt.ylabel("t-SNE dim 2")
    plt.tight_layout()
    plt.show()

    # Print neighborhoods
    print("\n=== Resonance Neighborhoods ===")
    for lbl in np.unique(labels):
        cluster_tokens = [concepts[i] for i in range(len(labels)) if labels[i] == lbl]
        print(f"Cluster {lbl}: {', '.join(cluster_tokens)}")

    # Compute nearest neighbors
    print("\n=== Nearest Neighbors (by Resonance) ===")
    for i, tok in enumerate(concepts):
        sims = sim[i]
        top_idx = np.argsort(sims)[::-1][1:6]
        neigh = [concepts[j] for j in top_idx]
        print(f"{tok:15s} → {', '.join(neigh)}")


def run_concept_clusters(learner):
    """Entry point to trigger concept clustering visualization."""
    visualize_concept_space(learner)
