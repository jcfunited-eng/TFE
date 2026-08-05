"""
test_couplings_carry.py — GL-CMD-98 T1–T7: couplings carry signal tests.

Verifies that coupling spikes affect krimelack transduction (not just
ψ-lattice injection), breaking the T7 diversity ceiling.
"""

import sys, os
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from dsf_ai_service.loom_model.cluster import LoomCluster
from dsf_ai_service.loom_model.mosaic import LoomMosaic
from dsf_ai_service.loom_model.tapestry import LoomTapestry
from dsf_ai_service.loom_model.neuron import LoomNeuron, PSI_DIM, J_BASE, J_MAX

BURST_WORDS = [
    "fire", "crash", "shock", "burst", "snap",
    "crack", "blast", "strike", "thrust", "jolt",
    "spark", "flash", "smash", "whip", "split",
    "chop", "kick", "punch", "stomp", "clash",
]

SMOOTH_WORDS = [
    "morning", "ocean", "balloon", "moonlight", "evening",
    "aurora", "meadow", "lullaby", "harmony", "serenity",
    "willow", "shadow", "yellow", "rainbow", "hollow",
    "moonrise", "starlight", "daylight", "silence", "breeze",
]

MIXED = BURST_WORDS[:25] + SMOOTH_WORDS[:25] if len(BURST_WORDS) >= 25 else BURST_WORDS + SMOOTH_WORDS


# ---------------------------------------------------------------------------
# T1: Diversity ≥30% after 50 ticks of cluster exposure
# ---------------------------------------------------------------------------

def test_t1_diversity_ceiling_breaks():
    """After 50 ticks, neuron_diversity_signature shows ≥30% distinct tuples."""
    c = LoomCluster("t1", n_neurons=50, k_neighbors=16, seed=42)

    words = BURST_WORDS + SMOOTH_WORDS
    for tick in range(50):
        word = words[tick % len(words)]
        c.step(word, tick=tick)

    # Measure diversity via (spike_count, winding, delta_eff)
    # GL-CMD-98: psi_norm is always 1.0 (normalized), spike_count caps at
    # SpikeBuffer.DEPTH. Winding and delta_eff are the substrate properties
    # that diverge under coupling-carried signal.
    sigs = {}
    for neuron in c.neurons:
        spike_count = len(neuron.spike_buffer)
        winding = neuron.krimelack.winding
        delta_eff = round(neuron.familiarity.delta_eff, 4)
        sigs[neuron.neuron_id] = (spike_count, winding, delta_eff)

    unique = len(set(sigs.values()))
    total = len(sigs)
    diversity = unique / total * 100

    print(f"\n== T1: Diversity ceiling ==")
    print(f"  Unique (spike_count, winding, delta_eff): {unique}/{total} = {diversity:.0f}%")
    sample = sorted(set(sigs.values()))[:5]
    print(f"  Sample tuples: {sample}")

    assert diversity >= 30, (
        f"Diversity {diversity:.0f}% < 30% — coupling signal fix didn't break ceiling"
    )


# ---------------------------------------------------------------------------
# T2: Isolated neuron (k=0) matches pre-change baseline
# ---------------------------------------------------------------------------

def test_t2_isolated_backward_compat():
    """Neuron with zero neighbors behaves identically to Stage 1 isolated case."""
    n = LoomNeuron("isolated")
    # No neighbors — coupling accumulators stay empty
    assert len(n.couplings.neighbors) == 0

    result = n.step("fire", tick=0)
    assert result["committed"]  # same as Stage 1 T3

    # No coupling signal accumulated
    assert n._coupling_signal_pending is False
    assert n._coupling_signal_sum == 0.0
    assert n._coupling_omega_shift == 0.0


# ---------------------------------------------------------------------------
# T3: Two neurons, NO shared neighbors, same input → identical state
# ---------------------------------------------------------------------------

def test_t3_no_neighbors_identical():
    """Two isolated neurons with same input show identical state."""
    n1 = LoomNeuron("a")
    n2 = LoomNeuron("b")

    n1.step("fire", tick=0)
    n2.step("fire", tick=0)

    assert n1.krimelack.winding == n2.krimelack.winding
    assert np.allclose(n1.psi_lattice.psi, n2.psi_lattice.psi)
    assert len(n1.spike_buffer) == len(n2.spike_buffer)


# ---------------------------------------------------------------------------
# T4: Two neurons with DIFFERENT neighbor sets diverge
# ---------------------------------------------------------------------------

def test_t4_different_neighbors_diverge():
    """Different coupling topology → different state after same input."""
    c = LoomCluster("t4", n_neurons=20, k_neighbors=8, seed=42)

    # Feed several words so coupling spikes accumulate
    for tick in range(10):
        c.step(BURST_WORDS[tick % len(BURST_WORDS)], tick=tick)

    # Pick two neurons with different neighbor sets
    n0 = c.neurons[0]
    n10 = c.neurons[10]
    assert set(n0.couplings.neighbors) != set(n10.couplings.neighbors)

    # Their states should differ because different coupling neighborhoods
    # produced different omega_override values on transduction
    w0 = n0.krimelack.winding
    w10 = n10.krimelack.winding
    psi0 = n0.psi_lattice.psi
    psi10 = n10.psi_lattice.psi

    # At least one of winding or psi should differ
    winding_differs = (w0 != w10)
    psi_differs = not np.allclose(psi0, psi10)

    print(f"\n== T4: Neighbor-driven divergence ==")
    print(f"  n0  winding={w0}, psi_norm={float(np.linalg.norm(psi0)):.6f}")
    print(f"  n10 winding={w10}, psi_norm={float(np.linalg.norm(psi10)):.6f}")
    print(f"  Winding differs: {winding_differs}, Psi differs: {psi_differs}")

    assert winding_differs or psi_differs, (
        "Neurons with different neighbor sets should diverge"
    )


# ---------------------------------------------------------------------------
# T5: Inter-cluster Sur's-ferrets still works
# ---------------------------------------------------------------------------

def test_t5_surs_ferrets_preserved():
    """Burst vs smooth clusters still separate (Stage 2 T5 equivalent)."""
    cluster_a = LoomCluster("A", n_neurons=50, k_neighbors=16, seed=42)
    cluster_b = LoomCluster("B", n_neurons=50, k_neighbors=16, seed=42)

    for tick, (burst, smooth) in enumerate(zip(BURST_WORDS, SMOOTH_WORDS)):
        cluster_a.step(burst, tick=tick)
        cluster_b.step(smooth, tick=tick)

    sig_a = cluster_a.winding_signature()
    sig_b = cluster_b.winding_signature()

    differences = sum(
        1 for i in range(50)
        if sig_a[f"A_n{i}"] != sig_b[f"B_n{i}"]
    )
    hamming = differences / 50

    print(f"\n== T5: Sur's-ferrets ==")
    print(f"  Hamming: {differences}/50 = {hamming:.2f}")
    assert hamming > 0, "Burst vs smooth should still separate"


# ---------------------------------------------------------------------------
# T6: Stage 4 mosaic recall still works
# ---------------------------------------------------------------------------

def test_t6_mosaic_recall_preserved():
    """Mosaic recall hit rate preserved after coupling change."""
    m = LoomMosaic("t6", n_clusters=3, neurons_per_cluster=50,
                   k_neighbors=16, seed=42)

    TRAINING_PAIRS = [
        ("fire", "spark"), ("crash", "blast"), ("shock", "jolt"),
        ("burst", "snap"), ("crack", "smash"), ("morning", "aurora"),
        ("ocean", "moonlight"), ("balloon", "rainbow"),
    ]
    for a, b in TRAINING_PAIRS:
        m.expose(a, b)

    queries = ["fire", "crash", "ocean", "morning", "burst"]
    hits = sum(1 for q in queries if m.recall(q) is not None)
    hit_rate = hits / len(queries)

    print(f"\n== T6: Mosaic recall ==")
    print(f"  Hit rate: {hits}/{len(queries)} = {hit_rate:.2f}")
    assert hit_rate >= 0.7, f"Hit rate {hit_rate:.2f} < 0.7 — recall regressed"


# ---------------------------------------------------------------------------
# T7: Stage 5 tapestry compose still returns non-None
# ---------------------------------------------------------------------------

def test_t7_tapestry_compose_preserved():
    """Tapestry compose still produces non-None emissions."""
    PETER = [
        "once upon a time there were four little rabbits",
        "they lived with their mother in a sand bank",
        "but do not go into mr mcgregor garden",
        "peter was most dreadfully frightened",
        "he rushed all over the garden",
    ]

    t = LoomTapestry("t7", n_mosaics=3, mosaic_kwargs={
        "n_clusters": 2, "neurons_per_cluster": 20, "k_neighbors": 8,
    }, seed=42)
    t.expose_corpus(PETER)

    result = t.compose("peter")
    print(f"\n== T7: Tapestry compose ==")
    print(f"  compose('peter') → {result}")
    assert result is not None, "Tapestry compose should return non-None after exposure"
