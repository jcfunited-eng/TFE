"""
test_contact_inhibition.py — GL-CMD-105: Contact Inhibition tests.

Validates that fold rate is suppressed by neighbor saturation ratio,
preventing unbounded population growth during sustained experience.

Integration point: LoomCluster.process_folds() applies the inhibition gate
AFTER fold_check passes but BEFORE spawn. This preserves fold_check's
standalone behavior (Stage 3 backward compat) while damping population growth.
"""

import sys, os, math
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from dsf_ai_service.loom_model.cluster import LoomCluster
from dsf_ai_service.loom_model.neuron import (
    LoomNeuron, CouplingsJij, PSI_DIM, FOLD_TRIGGER_RATIO, FOLD_SUSTAIN_TICKS,
)
from dsf_ai_service.loom_model.substrate_dna import K_TOTAL
from dsf_ai_service.substrate.sensory_generators import generate_touch_waveform
from dsf_ai_service.loom_model.substrate_dna import TOUCH_LIBRARY


def _touch_signal():
    """Generate a flattened touch waveform for 'hot'."""
    params = TOUCH_LIBRARY["hot"]
    waveforms = generate_touch_waveform(params)
    channels = [waveforms[k] for k in sorted(waveforms.keys())]
    return np.concatenate(channels)


def _force_fold_dsf():
    """Return a DSF that produces n_eff < threshold (guaranteed fold trigger)."""
    from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
    # 6 components above 0.5 → n_eff = 8-6 = 2 < 8/e ≈ 2.94
    return DSF(D_k=0.9, M_k=0.8, R_rev=0.7, U_star=0.1,
               C_k=0.6, P_k=0.7, B_k=0.8, S_UF=0.6)


# ---------------------------------------------------------------------------
# T1: inhibition_factor monotonicity
# ---------------------------------------------------------------------------

def test_t1_inhibition_factor_monotonicity():
    """inhibition_factor = (1 - n/K)² is monotonically non-increasing."""
    factors = []
    for n in range(K_TOTAL + 1):
        saturation_ratio = n / K_TOTAL
        inhibition_factor = (1.0 - saturation_ratio) ** 2
        factors.append(inhibition_factor)

    print("\n== T1: inhibition_factor array ==")
    for i, f in enumerate(factors):
        print(f"  n_neighbors={i:2d}: inhibition_factor={f:.6f}")

    # Monotonically non-increasing
    for i in range(1, len(factors)):
        assert factors[i] <= factors[i - 1], (
            f"Not monotonic: factors[{i}]={factors[i]} > factors[{i-1}]={factors[i-1]}"
        )

    # Boundary values
    assert factors[0] == 1.0, f"factor(0) should be 1.0, got {factors[0]}"
    assert factors[K_TOTAL] == 0.0, f"factor(K_TOTAL) should be 0.0, got {factors[K_TOTAL]}"


# ---------------------------------------------------------------------------
# T2: fold suppression at saturation (via cluster.process_folds)
# ---------------------------------------------------------------------------

def test_t2_fold_suppression_at_saturation():
    """Cluster with all neurons at K_TOTAL neighbors — fold suppressed."""
    # 20-neuron cluster with k_neighbors=16 = K_TOTAL → all saturated
    c = LoomCluster("t2_sat", n_neurons=20, k_neighbors=K_TOTAL, seed=42)

    # Force all neurons into fold-ready state
    forced_dsf = _force_fold_dsf()
    for n in c.neurons:
        n._last_dsf = forced_dsf
        n._last_origin_transducer = "tactile"
        n._fold_sustain_count = FOLD_SUSTAIN_TICKS  # pre-load

    # Process folds — should all be inhibited
    new_ids = c.process_folds(tick=100)

    n_neighbors = len(c.neurons[0].couplings.neighbors)
    inhibition_factor = (1.0 - n_neighbors / K_TOTAL) ** 2

    print(f"\n== T2: Fold suppression at saturation ==")
    print(f"  n_neurons=20, k_neighbors={K_TOTAL}")
    print(f"  n_neighbors per neuron={n_neighbors}")
    print(f"  inhibition_factor={inhibition_factor:.6f}")
    print(f"  folds triggered={len(new_ids)}")
    print(f"  fold_triggered=False")

    assert len(new_ids) == 0, (
        f"No folds should occur at full saturation, got {len(new_ids)}"
    )


# ---------------------------------------------------------------------------
# T3: fold permitted at low neighbor count (via cluster.process_folds)
# ---------------------------------------------------------------------------

def test_t3_fold_permitted_at_low_neighbors():
    """Cluster with few neurons (< K_TOTAL+1) — folds proceed."""
    # 8-neuron cluster → each neuron has min(16, 7) = 7 neighbors
    c = LoomCluster("t3_low", n_neurons=8, k_neighbors=K_TOTAL, seed=42)

    # Force all neurons into fold-ready state
    forced_dsf = _force_fold_dsf()
    for n in c.neurons:
        n._last_dsf = forced_dsf
        n._last_origin_transducer = "tactile"
        n._fold_sustain_count = FOLD_SUSTAIN_TICKS

    new_ids = c.process_folds(tick=100)

    n_neighbors = len(c.neurons[0].couplings.neighbors)
    inhibition_factor = (1.0 - n_neighbors / K_TOTAL) ** 2
    n_eff = c.neurons[0].l6_tcl.n_eff(forced_dsf)
    threshold = c.neurons[0].l6_tcl.n_start * FOLD_TRIGGER_RATIO
    overflow_raw = threshold - n_eff
    overflow_eff = overflow_raw * inhibition_factor

    print(f"\n== T3: Fold permitted at low neighbors ==")
    print(f"  n_neurons=8, k_neighbors={K_TOTAL}")
    print(f"  actual n_neighbors per neuron={n_neighbors}")
    print(f"  inhibition_factor={inhibition_factor:.6f}")
    print(f"  overflow_raw={overflow_raw:.4f}, overflow_eff={overflow_eff:.4f}")
    print(f"  folds triggered={len(new_ids)}")
    print(f"  fold_triggered=True")

    assert len(new_ids) > 0, (
        f"Folds should occur with {n_neighbors} neighbors "
        f"(inhibition_factor={inhibition_factor:.4f}). overflow_eff={overflow_eff:.4f}"
    )


# ---------------------------------------------------------------------------
# T4: gradient between extremes
# ---------------------------------------------------------------------------

def test_t4_fold_rate_gradient():
    """Fold rate decreases monotonically with increasing cluster size (neighbor count)."""
    # Different cluster sizes → different neighbor counts
    cluster_sizes = [5, 9, 13, 17, 20]  # → neighbors: 4, 8, 12, 16, 16
    fold_counts = []

    for n_neurons in cluster_sizes:
        n_trials = 100
        fold_count = 0
        for trial in range(n_trials):
            c = LoomCluster(f"t4_{n_neurons}_{trial}", n_neurons=n_neurons,
                           k_neighbors=K_TOTAL, seed=trial)
            # Force fold-ready with noise
            from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
            rng = np.random.default_rng(seed=trial * 17 + n_neurons)
            noise = rng.uniform(-0.1, 0.1, 8)
            base = [0.9, 0.8, 0.7, 0.1, 0.6, 0.7, 0.8, 0.6]
            vals = [max(0.0, min(1.0, b + n)) for b, n in zip(base, noise)]
            dsf = DSF(D_k=vals[0], M_k=vals[1], R_rev=vals[2], U_star=vals[3],
                      C_k=vals[4], P_k=vals[5], B_k=vals[6], S_UF=vals[7])

            target = c.neurons[0]
            target._last_dsf = dsf
            target._last_origin_transducer = "tactile"
            target._fold_sustain_count = FOLD_SUSTAIN_TICKS

            new_ids = c.process_folds(tick=100)
            if new_ids:
                fold_count += 1

        fold_counts.append(fold_count / n_trials)

    print(f"\n== T4: Fold rate gradient ==")
    for n_neurons, rate in zip(cluster_sizes, fold_counts):
        n_nbrs = min(K_TOTAL, n_neurons - 1)
        print(f"  cluster_size={n_neurons:2d} (n_neighbors={n_nbrs:2d}): fold_rate={rate:.3f}")

    # Monotonically non-increasing
    for i in range(1, len(fold_counts)):
        assert fold_counts[i] <= fold_counts[i - 1], (
            f"Fold rate not monotonic: rate[size={cluster_sizes[i]}]={fold_counts[i]} > "
            f"rate[size={cluster_sizes[i-1]}]={fold_counts[i-1]}"
        )


# ---------------------------------------------------------------------------
# T5: population stability under sustained overflow
# ---------------------------------------------------------------------------

def test_t5_population_stability():
    """Sustained overflow-generating input → population stabilizes."""
    # Start with 10 neurons → each has 9 neighbors → inhibition_factor ≈ 0.19
    c = LoomCluster("t5ci", n_neurons=10, k_neighbors=K_TOTAL, seed=42)
    touch_sig = _touch_signal()

    # Set all neurons to tactile origin
    for n in c.neurons:
        n._last_origin_transducer = "tactile"

    populations = []
    for tick in range(500):
        c.step(touch_sig, tick=tick)
        c.process_folds(tick)
        if (tick + 1) % 50 == 0:
            populations.append(len(c.neurons))

    print(f"\n== T5: Population stability under sustained overflow ==")
    for i, pop in enumerate(populations):
        print(f"  tick {(i+1)*50:3d}: population={pop}")

    # Growth must stop or asymptote by tick 500
    if len(populations) >= 4:
        late_growth = populations[-1] - populations[-4]
        print(f"  Late growth (last 150 ticks): {late_growth}")
        still_growing = late_growth > 5
    else:
        still_growing = False

    if still_growing:
        # T6 STOP path
        print("  FAIL: population still growing at tick 500")
        print(f"  Final population: {populations[-1]}")
        pytest.fail(
            f"T5 FAIL: population still growing at tick 500 "
            f"(late_growth={late_growth}, final_pop={populations[-1]}). "
            f"Contact inhibition formula may need derivation from different "
            f"physics base. Do NOT tune exponent."
        )


# ---------------------------------------------------------------------------
# T7: substrate-true sanity
# ---------------------------------------------------------------------------

def test_t7_substrate_true_sanity():
    """No new constants, K_TOTAL referenced not redefined."""
    import inspect
    from dsf_ai_service.loom_model import cluster as cluster_mod

    # K_TOTAL is imported in cluster.py from substrate_dna
    source = inspect.getsource(cluster_mod)
    assert "from .substrate_dna import" in source and "K_TOTAL" in source, (
        "K_TOTAL must be imported from substrate_dna in cluster.py"
    )

    # No new constants defined
    assert "INHIBITION_" not in source, "No new INHIBITION_ constants allowed"
    assert "CONTACT_" not in source, "No new CONTACT_ constants allowed"

    # K_TOTAL matches substrate_dna value
    from dsf_ai_service.loom_model.substrate_dna import K_TOTAL as K_REF
    assert K_TOTAL == K_REF == 16

    # No per-neuron tuning for inhibition
    neuron_source = inspect.getsource(LoomNeuron)
    assert "inhibition_strength" not in neuron_source
    assert "inhibition_exponent" not in neuron_source

    print("\n== T7: substrate-true sanity ==")
    print(f"  K_TOTAL={K_TOTAL} (from substrate_dna, not redefined)")
    print(f"  No new constants, no per-neuron inhibition tuning")


# ---------------------------------------------------------------------------
# T8: backward compatibility
# ---------------------------------------------------------------------------

def test_t8_backward_compat():
    """fold_check itself is unchanged — only process_folds applies inhibition."""
    # Standalone neuron: fold_check still triggers regardless of neighbors
    neuron = LoomNeuron("t8_standalone")
    # Give it K_TOTAL neighbors
    neighbor_ids = [f"t8_nb_{i}" for i in range(K_TOTAL)]
    neuron.couplings = CouplingsJij(n_modes=PSI_DIM, neighbors=neighbor_ids)

    forced_dsf = _force_fold_dsf()
    neuron._last_dsf = forced_dsf

    # fold_check should still return True (no inhibition in fold_check)
    neuron._fold_sustain_count = 0
    fold_triggered = False
    for tick in range(FOLD_SUSTAIN_TICKS + 2):
        if neuron.fold_check(tick):
            fold_triggered = True
            break

    print(f"\n== T8: backward compat ==")
    print(f"  fold_check on saturated neuron: {fold_triggered}")
    print(f"  (fold_check has NO inhibition — it's applied at cluster level)")

    assert fold_triggered, (
        "fold_check must still trigger at full saturation — "
        "inhibition is applied in process_folds, not fold_check"
    )
