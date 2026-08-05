# resonance_visualizer.py
# Aurelion v4 — Cross-Modal Resonance Visualizer (Safe Projection)
# Displays relationships between modalities for a given concept.

import numpy as np
import matplotlib.pyplot as plt
from primitive_sensory_pack import DIMS

def visualize_cross_modal(concept: str, learner):
    """Compute and display a cross-modal resonance matrix for a learned concept."""
    concept = concept.lower().strip()
    mods = list(DIMS.keys())
    n = len(mods)
    data = np.zeros((n, n), dtype=np.float32)

    # Check if we have memory for this concept
    if not any(concept in m for m in learner.memory.values()):
        print(f"[No memory] '{concept}' not found in learner.")
        return

    # Gather modality vectors and normalize dimensions
    vecs = {}
    max_dim = max(DIMS.values())

    for mod in mods:
        if concept in learner.memory.get(mod, {}):
            v = learner.memory[mod][concept]
            # Normalize and pad to max_dim
            v = v / (np.linalg.norm(v) + 1e-8)
            if v.shape[0] < max_dim:
                v = np.pad(v, (0, max_dim - v.shape[0]), constant_values=0.0)
            vecs[mod] = v

    # Compute pairwise cosine similarities (resonance)
    for i, m1 in enumerate(mods):
        for j, m2 in enumerate(mods):
            if m1 in vecs and m2 in vecs:
                data[i, j] = float(np.dot(vecs[m1], vecs[m2]))
            else:
                data[i, j] = 0.0

    # --- Visualization ---
    plt.figure(figsize=(6, 5))
    im = plt.imshow(data, vmin=-1, vmax=1, cmap="viridis")
    plt.xticks(range(n), mods, rotation=45, ha="right")
    plt.yticks(range(n), mods)
    plt.title(f"Aurelion — Cross-Modal Resonance Map\n'{concept}'")
    plt.colorbar(im, label="Resonance (cosine similarity)")
    plt.tight_layout()
    plt.show()

    # --- Console summary ---
    print(f"\nCross-Modal Resonance for '{concept}':")
    for i, m1 in enumerate(mods):
        row = "  ".join(f"{data[i,j]:.2f}" for j in range(n))
        print(f"{m1:9s}: {row}")
