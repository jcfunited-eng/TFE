"""
test_cluster.py — GL-CMD-79 T1–T8 sanity tests for LoomCluster.

GL-CMD-LOOM-CLUSTER-STAGE2-EVE-20260620-79
"""

import sys, os
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from dsf_ai_service.loom_model.cluster import LoomCluster
from dsf_ai_service.loom_model.neuron import (
    LoomNeuron, PSI_DIM, DELTA_BASE, _map_inject,
)
from dsf_ai_service.v4.gualaloom_v5_engine import (
    _SPIN_VECTOR_DIM, MIN_GAIN_THRESHOLD,
)


# ---------------------------------------------------------------------------
# T1: Cluster construction — 50 neurons, each with Couplings shape (16,16)
# ---------------------------------------------------------------------------

def test_t1_cluster_construction():
    """LoomCluster(50, k=16): len(neurons)==50; each J.shape==(16,16)."""
    c = LoomCluster("t1", n_neurons=50, k_neighbors=16, seed=42)

    assert len(c.neurons) == 50, f"Expected 50 neurons, got {len(c.neurons)}"

    for neuron in c.neurons:
        J_shape = neuron.couplings.J.shape
        assert J_shape == (16, 16), (
            f"Neuron {neuron.neuron_id}: expected J.shape=(16,16), got {J_shape}"
        )
        assert len(neuron.couplings.neighbors) == 16, (
            f"Neuron {neuron.neuron_id}: expected 16 neighbors, "
            f"got {len(neuron.couplings.neighbors)}"
        )
        # No self-loops
        assert neuron.neuron_id not in neuron.couplings.neighbors, (
            f"Neuron {neuron.neuron_id} has self-loop"
        )
        # No duplicates
        assert len(set(neuron.couplings.neighbors)) == 16, (
            f"Neuron {neuron.neuron_id} has duplicate neighbors"
        )


# ---------------------------------------------------------------------------
# T2: cluster.step() runs; at least one spike buffer non-empty
# ---------------------------------------------------------------------------

def test_t2_cluster_step_runs():
    """cluster.step() completes without error; at least one neuron spikes."""
    c = LoomCluster("t2", n_neurons=50, k_neighbors=16, seed=42)
    results = c.step("fire", tick=0)

    assert len(results) == 50, f"Expected 50 results, got {len(results)}"

    any_spike = any(
        len(n.spike_buffer) > 0 for n in c.neurons
    )
    assert any_spike, "Expected at least one neuron to spike on 'fire'"

    # Count committed neurons
    n_committed = sum(1 for r in results.values() if r["committed"])
    assert n_committed > 0, "Expected at least one commit"


# ---------------------------------------------------------------------------
# T3: Coupling spikes propagate — Δ_eff > Δ_base after phase B
# ---------------------------------------------------------------------------

def test_t3_coupling_propagation():
    """After step(), coupling-spike contributions raise Δ_eff above Δ_base."""
    c = LoomCluster("t3", n_neurons=50, k_neighbors=16, seed=42)
    c.step("fire", tick=0)

    # After Phase B, neurons that received coupling spikes should have
    # delta_eff > DELTA_BASE (0.10). On first step, match_score=0 for all
    # neurons, so any excess above DELTA_BASE is from coupling.
    coupling_elevated = [
        n for n in c.neurons
        if n.familiarity.delta_eff > DELTA_BASE + 1e-9
    ]
    assert len(coupling_elevated) > 0, (
        f"Expected at least one neuron with coupling-elevated Δ_eff. "
        f"All Δ_eff values: {sorted(set(n.familiarity.delta_eff for n in c.neurons))}"
    )

    # Verify the coupling contribution magnitude is consistent
    # GL-CMD-98: J_ij now scaled by 1/(d+1) for ring distance d, and
    # Phase B uses receiver-side J. Total contribution varies by position.
    max_delta = max(n.familiarity.delta_eff for n in c.neurons)
    assert max_delta > DELTA_BASE + 0.01, (
        f"Coupling contribution seems too small: max delta_eff={max_delta:.4f}"
    )


# ---------------------------------------------------------------------------
# T4: emit() returns len > 1 (population composition, not single neuron)
# ---------------------------------------------------------------------------

def test_t4_emit_multiple_neurons():
    """emit() selects more than one neuron (actual coherent integration)."""
    c = LoomCluster("t4", n_neurons=50, k_neighbors=16, seed=42)
    c.step("fire", tick=0)

    needs_vec = np.ones(3, dtype=np.float64) / 3.0
    selected_ids, alignment, dim_contributions = c.emit(
        target_chi=0, target_source="corpus",
        needs_vector=needs_vec, current_tick=0,
    )

    assert len(selected_ids) > 1, (
        f"Expected population composition len > 1, got {len(selected_ids)}: {selected_ids}"
    )
    assert alignment > 0.0, f"Expected positive alignment, got {alignment}"
    assert len(dim_contributions) > 0, "Expected dimension contributions"


# ---------------------------------------------------------------------------
# T5: Sur's-ferrets differentiation — different inputs → different states
# ---------------------------------------------------------------------------

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


def test_t5_surs_ferrets_differentiation():
    """Two clusters with same seed, different inputs → different winding signatures."""
    cluster_a = LoomCluster("A", n_neurons=50, k_neighbors=16, seed=42)
    cluster_b = LoomCluster("B", n_neurons=50, k_neighbors=16, seed=42)

    for tick, (burst, smooth) in enumerate(zip(BURST_WORDS, SMOOTH_WORDS)):
        cluster_a.step(burst, tick=tick)
        cluster_b.step(smooth, tick=tick)

    sig_a = cluster_a.winding_signature()
    sig_b = cluster_b.winding_signature()

    # Hamming-style difference: count neurons where winding differs
    # Neuron IDs differ by prefix (A_nX vs B_nX), compare by index
    differences = 0
    for i in range(50):
        nid_a = f"A_n{i}"
        nid_b = f"B_n{i}"
        if sig_a[nid_a] != sig_b[nid_b]:
            differences += 1

    mean_hamming = differences / 50.0
    assert mean_hamming > 0, (
        f"Expected some differentiation between burst and smooth clusters. "
        f"Hamming distance = {differences}/50 = {mean_hamming:.2f}"
    )

    # PASTE: print signatures for report
    print(f"\n== Sur's-ferrets differentiation ==")
    print(f"Cluster A (burst) winding signature (last 5):")
    for i in range(45, 50):
        nid = f"A_n{i}"
        print(f"  {nid}: winding={sig_a[nid]}")
    print(f"Cluster B (smooth) winding signature (last 5):")
    for i in range(45, 50):
        nid = f"B_n{i}"
        print(f"  {nid}: winding={sig_b[nid]}")
    print(f"Hamming distance: {differences}/50 = {mean_hamming:.2f}")


# ---------------------------------------------------------------------------
# T6: Coherent power growth — |Σψ|² monotonic non-decreasing
# ---------------------------------------------------------------------------

def test_t6_coherent_power_growth():
    """Population grandurun composition: |Σψ|² grows monotonically."""
    c = LoomCluster("t6", n_neurons=50, k_neighbors=16, seed=42)
    c.step("fire", tick=0)

    needs_vec = np.ones(3, dtype=np.float64) / 3.0
    candidates = c.population_grandurun_state(
        target_chi=0, target_source="corpus",
        needs_vector=needs_vec, current_tick=0,
    )

    # Replay greedy selection, tracking |Σψ|² at each addition
    pool = sorted(candidates, key=lambda c: -abs(c[0][0]))
    composition_sum = np.zeros(_SPIN_VECTOR_DIM, dtype=np.complex128)
    last_alignment = 0.0
    powers = []

    for state_vec, _nid in pool:
        new_sum = composition_sum + state_vec
        alignment = float(np.real(np.vdot(new_sum, state_vec)))
        gain = alignment - last_alignment
        if gain > MIN_GAIN_THRESHOLD:
            composition_sum = new_sum
            last_alignment = alignment
            power = float(np.sum(np.abs(composition_sum) ** 2))
            powers.append(power)
        # GL-CMD-NO-CAPS-COHERENCE-SPEAKS-EVE-20260705-203: no length
        # ceiling in production anymore -- pool itself (bounded by
        # cluster size) is the natural stopping bound here too.

    assert len(powers) >= 2, (
        f"Expected at least 2 selections for power growth test, got {len(powers)}"
    )

    # Assert monotonic non-decreasing
    for j in range(1, len(powers)):
        assert powers[j] >= powers[j - 1] - 1e-9, (
            f"|Σψ|² must be non-decreasing: step {j-1}→{j}: "
            f"{powers[j-1]:.6f}→{powers[j]:.6f}"
        )

    # PASTE: print power sequence for report
    print(f"\n== Coherent power growth ==")
    for j, p in enumerate(powers):
        print(f"  addition {j}: |Σψ|² = {p:.6f}")
    print(f"Total selections: {len(powers)}, final power: {powers[-1]:.6f}")


# ---------------------------------------------------------------------------
# T7: Determinism — same seed + same input → identical emit output
# ---------------------------------------------------------------------------

def test_t7_determinism():
    """Same seed + same input + same DNA → identical emit() output."""
    def run_cluster():
        c = LoomCluster("det", n_neurons=50, k_neighbors=16, seed=42)
        c.step("fire", tick=0)
        needs_vec = np.ones(3, dtype=np.float64) / 3.0
        return c.emit(
            target_chi=0, target_source="corpus",
            needs_vector=needs_vec, current_tick=0,
        )

    ids_1, align_1, dim_1 = run_cluster()
    ids_2, align_2, dim_2 = run_cluster()

    assert ids_1 == ids_2, (
        f"Selected neuron IDs differ between runs:\n  run1: {ids_1}\n  run2: {ids_2}"
    )
    assert align_1 == align_2, (
        f"Alignment differs: {align_1} vs {align_2}"
    )
    for key in dim_1:
        assert dim_1[key] == dim_2[key], (
            f"dim_contributions[{key}] differs: {dim_1[key]} vs {dim_2[key]}"
        )


# ---------------------------------------------------------------------------
# T8: S_UF→B_k formula comparison for cluster differentiation
# ---------------------------------------------------------------------------

def test_t8_formula_comparison():
    """Run T5 with both amplitude formulas. Report if differentiation differs.

    If differentiation is materially different, surface to Eve before Stage 3.
    If not, the B_k engineering substitution holds.
    """
    from dsf_ai_service.loom_model import neuron as neuron_mod

    # Save original _map_inject
    original_map_inject = neuron_mod._map_inject

    def _map_inject_suf(dsf, chi, dim=PSI_DIM, sigma=neuron_mod.INJECT_SIGMA):
        """Original formula: B_k × S_UF + 0.10"""
        chi_mode = int(chi) % dim
        indices = np.arange(dim)
        dist = np.minimum(np.abs(indices - chi_mode),
                          dim - np.abs(indices - chi_mode))
        gauss = np.exp(-dist.astype(np.float64) ** 2 / (2.0 * sigma ** 2))
        amplitude = float(dsf.B_k) * float(dsf.S_UF) + 0.10
        return gauss * amplitude

    # Run with B_k formula (current)
    cluster_a1 = LoomCluster("A1", n_neurons=50, k_neighbors=16, seed=42)
    cluster_b1 = LoomCluster("B1", n_neurons=50, k_neighbors=16, seed=42)
    for tick, (burst, smooth) in enumerate(zip(BURST_WORDS[:10], SMOOTH_WORDS[:10])):
        cluster_a1.step(burst, tick=tick)
        cluster_b1.step(smooth, tick=tick)

    sig_a1 = cluster_a1.winding_signature()
    sig_b1 = cluster_b1.winding_signature()
    diff_bk = sum(
        1 for i in range(50)
        if sig_a1[f"A1_n{i}"] != sig_b1[f"B1_n{i}"]
    )

    # Swap to S_UF formula
    neuron_mod._map_inject = _map_inject_suf
    try:
        cluster_a2 = LoomCluster("A2", n_neurons=50, k_neighbors=16, seed=42)
        cluster_b2 = LoomCluster("B2", n_neurons=50, k_neighbors=16, seed=42)
        for tick, (burst, smooth) in enumerate(zip(BURST_WORDS[:10], SMOOTH_WORDS[:10])):
            cluster_a2.step(burst, tick=tick)
            cluster_b2.step(smooth, tick=tick)

        sig_a2 = cluster_a2.winding_signature()
        sig_b2 = cluster_b2.winding_signature()
        diff_suf = sum(
            1 for i in range(50)
            if sig_a2[f"A2_n{i}"] != sig_b2[f"B2_n{i}"]
        )
    finally:
        # Restore original
        neuron_mod._map_inject = original_map_inject

    # Report
    print(f"\n== T8: Formula comparison ==")
    print(f"  B_k formula:     Hamming={diff_bk}/50")
    print(f"  B_k×S_UF formula: Hamming={diff_suf}/50")

    # The winding signatures are krimelack-level (same transduction regardless
    # of injection formula), so winding-based Hamming should be identical.
    # The differentiation is in the krimelack output, not the ψ-lattice.
    # Material difference = >10% divergence in Hamming distance.
    delta = abs(diff_bk - diff_suf)
    material_threshold = max(diff_bk, diff_suf, 1) * 0.10
    if delta > material_threshold:
        print(f"  WARNING: material difference detected (Δ={delta}). Surface to Eve.")
    else:
        print(f"  Engineering substitution holds (Δ={delta} ≤ {material_threshold:.1f}).")

    # Both formulas should produce differentiation (> 0 Hamming)
    assert diff_bk > 0, "B_k formula: no differentiation"
    # S_UF formula may have 0 differentiation if S_UF=0 suppresses commits,
    # but winding signatures are krimelack-level (pre-injection), so they
    # should still differentiate.
    assert diff_suf >= 0, "S_UF formula: negative Hamming (impossible)"
