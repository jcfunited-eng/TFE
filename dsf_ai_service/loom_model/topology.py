"""
topology.py — Committed hemisphere topology constants.

GL-CMD-113 V2.1, per GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-103 Part 3.

Watts-Strogatz N=8, K=4, p=0.2, seed=42. Baked as constant — never regenerated.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Committed topology — do NOT regenerate
# ---------------------------------------------------------------------------

HEMISPHERE_ADJACENCY = np.array([
    # H0 H1 H2 H3 H4 H5 H6 H7
    [0, 1, 1, 0, 0, 0, 1, 1],  # H0: connects to H1, H2, H6, H7
    [1, 0, 0, 1, 1, 0, 0, 0],  # H1: connects to H0, H3, H4
    [1, 0, 0, 1, 1, 0, 0, 0],  # H2: connects to H0, H3, H4
    [0, 1, 1, 0, 1, 1, 1, 0],  # H3: connects to H1, H2, H4, H5, H6  (hub deg 5)
    [0, 1, 1, 1, 0, 0, 1, 1],  # H4: connects to H1, H2, H3, H6, H7  (hub deg 5)
    [0, 0, 0, 1, 0, 0, 1, 1],  # H5: connects to H3, H6, H7
    [1, 0, 0, 1, 1, 1, 0, 1],  # H6: connects to H0, H3, H4, H5, H7  (hub deg 5)
    [1, 0, 0, 0, 1, 1, 1, 0],  # H7: connects to H0, H4, H5, H6
], dtype=np.int32)

N_HEMISPHERES = 8

# ---------------------------------------------------------------------------
# Substrate constants for cross-hemisphere coupling
# ---------------------------------------------------------------------------

K_INTERHEMI = 2                      # cross-hemi coupling budget per projection neuron
PROJECTION_NEURONS_PER_HEMI = 3      # designated projection neurons at seed (3×2=6 ≥ deg-5 hubs)
CROSS_HEMI_INITIAL_STRENGTH = 0.5    # multiplier on J_BASE for initial cross-hemi weight
SEED_SIZE_PER_HEMISPHERE = 8         # K_TOTAL // 2 — substrate-derived, not magic number


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------

def validate_adjacency(matrix: np.ndarray):
    """Validate the adjacency matrix at boot. Returns topology metrics.

    Checks: symmetric, zero diagonal, all nodes connected.
    Returns dict with clustering_coefficient, avg_shortest_path, degrees.
    """
    N = matrix.shape[0]
    assert matrix.shape == (N, N), f"Expected square matrix, got {matrix.shape}"
    assert np.all(matrix == matrix.T), "Adjacency matrix must be symmetric"
    assert np.all(np.diag(matrix) == 0), "Diagonal must be zero (no self-loops)"

    # Degrees
    degrees = matrix.sum(axis=1).tolist()

    # Shortest paths via BFS
    def _bfs_distances(start):
        visited = {start: 0}
        queue = [start]
        while queue:
            node = queue.pop(0)
            for neighbor in range(N):
                if matrix[node, neighbor] and neighbor not in visited:
                    visited[neighbor] = visited[node] + 1
                    queue.append(neighbor)
        return visited

    all_dists = {}
    for i in range(N):
        all_dists[i] = _bfs_distances(i)

    # Check all connected
    for i in range(N):
        assert len(all_dists[i]) == N, f"Node {i} cannot reach all nodes"

    # Average shortest path
    total_path = sum(
        all_dists[i][j] for i in range(N) for j in range(N) if i != j
    )
    avg_path = total_path / (N * (N - 1))

    # Clustering coefficient (fraction of neighbor pairs that are connected)
    clustering = []
    for i in range(N):
        neighbors = [j for j in range(N) if matrix[i, j]]
        k = len(neighbors)
        if k < 2:
            clustering.append(0.0)
            continue
        connected_pairs = sum(
            1 for a in range(len(neighbors))
            for b in range(a + 1, len(neighbors))
            if matrix[neighbors[a], neighbors[b]]
        )
        possible_pairs = k * (k - 1) / 2
        clustering.append(connected_pairs / possible_pairs)
    avg_clustering = sum(clustering) / N

    return {
        "degrees": degrees,
        "clustering_coefficient": round(avg_clustering, 4),
        "avg_shortest_path": round(avg_path, 4),
        "n_edges": int(matrix.sum()) // 2,
        "per_node_clustering": [round(c, 4) for c in clustering],
    }
