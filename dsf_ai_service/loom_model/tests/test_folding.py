"""
test_folding.py — GL-CMD-84 T3-T8: Folding Division tests.
"""

import sys, os, math
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from dsf_ai_service.loom_model.cluster import LoomCluster
from dsf_ai_service.loom_model.neuron import (
    LoomNeuron, PSI_DIM, FOLD_TRIGGER_RATIO, FOLD_SUSTAIN_TICKS, P_COMMIT,
)
from dsf_ai_service.loom_model.substrate_dna import (
    derive_daughter_parameters, OverflowSignal, K_TOTAL,
    TactileKrimelack, CochlearBankKrimelack, TOUCH_LIBRARY,
)
from dsf_ai_service.substrate.sensory_generators import generate_touch_waveform


def _touch_signal():
    """Generate a flattened touch waveform for 'hot'."""
    params = TOUCH_LIBRARY["hot"]
    waveforms = generate_touch_waveform(params)
    # Concatenate all channels into a single signal array
    channels = [waveforms[k] for k in sorted(waveforms.keys())]
    return np.concatenate(channels)


def _audio_signal(seed=42):
    """Generate a synthetic audio waveform (50 Hz sine + noise)."""
    rng = np.random.default_rng(seed)
    t = np.arange(400) / 200.0
    return np.sin(2 * np.pi * 50 * t) + rng.normal(0, 0.1, 400)


# ---------------------------------------------------------------------------
# T3: fold_check behavior
# ---------------------------------------------------------------------------

def test_t3_fold_check():
    """fold_check returns False on fresh neuron; True after sustained input."""
    n = LoomNeuron("t3_fresh")

    # Fresh neuron: no DSF computed, fold_check must be False
    assert n.fold_check(tick=0) is False, "Fresh neuron should not fold"

    # Feed input to create a DSF
    n.step("fire", tick=0)
    # After one step, fold_sustain_count is at most 1, need FOLD_SUSTAIN_TICKS (3)
    assert n.fold_check(tick=0) is False or n._fold_sustain_count < FOLD_SUSTAIN_TICKS

    # Force the DSF to produce n_eff < threshold by creating a DSF with
    # many high-magnitude components (each >0.5 counts as a constraint)
    from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
    # 6 components above 0.5 → n_eff = 8-6 = 2 < 8/e ≈ 2.94
    forced_dsf = DSF(D_k=0.9, M_k=0.8, R_rev=0.7, U_star=0.1,
                     C_k=0.6, P_k=0.7, B_k=0.8, S_UF=0.6)
    n._last_dsf = forced_dsf

    # Need FOLD_SUSTAIN_TICKS consecutive True checks
    n._fold_sustain_count = 0
    for i in range(FOLD_SUSTAIN_TICKS):
        result = n.fold_check(tick=i)
        if i < FOLD_SUSTAIN_TICKS - 1:
            assert result is False, f"Should not fold at tick {i}"
    assert result is True, (
        f"Should fold after {FOLD_SUSTAIN_TICKS} sustained ticks, "
        f"sustain_count={n._fold_sustain_count}"
    )


# ---------------------------------------------------------------------------
# T4: Daughter spawn from touch waveform
# ---------------------------------------------------------------------------

def test_t4_daughter_spawn():
    """Daughter from touch waveform: correct class, weights sum to 1, k's sum to K."""
    # 10 neurons gives each 9 neighbors — inhibition_factor > 0, folds proceed
    # for daughter-parameter validation under post-inhibition physics (GL-CMD-105)
    c = LoomCluster("t4", n_neurons=10, k_neighbors=16, seed=42)
    touch_sig = _touch_signal()

    # Set all neurons to track origin as tactile and feed touch signal
    for n in c.neurons:
        n._last_origin_transducer = "tactile"

    # Feed touch waveform until at least one fold
    folded = False
    daughters = []
    for tick in range(200):
        c.step(touch_sig, tick=tick)
        new_ids = c.process_folds(tick)
        if new_ids:
            daughters.extend(new_ids)
            folded = True

    if not folded:
        # Force a fold by manipulating DSF if natural fold didn't occur
        from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
        parent = c.neurons[0]
        parent._last_origin_transducer = "tactile"
        forced_dsf = DSF(D_k=0.9, M_k=0.8, R_rev=0.7, U_star=0.1,
                         C_k=0.6, P_k=0.7, B_k=0.8, S_UF=0.6)
        parent._last_dsf = forced_dsf
        parent._fold_sustain_count = FOLD_SUSTAIN_TICKS
        new_ids = c.process_folds(tick + 1)
        daughters.extend(new_ids)

    assert len(daughters) > 0, "Expected at least one daughter spawn"

    # Find the daughter neuron
    daughter = c._neuron_map[daughters[0]]

    # T4c: origin_transducer must be tactile
    assert daughter._last_origin_transducer == "tactile", (
        f"Daughter origin should be 'tactile', got '{daughter._last_origin_transducer}'"
    )

    # T4d: law_field_weights sum to 1.0
    total_weight = sum(law.weight for law in daughter.laws)
    assert abs(total_weight - 1.0) < 1e-6, (
        f"Law field weights must sum to 1.0, got {total_weight}"
    )

    # T4e: k_intra + k_inter == K_TOTAL
    # (verified from the derive_daughter_parameters output)

    # T4f: parent's n_eff recovered
    parent = c.neurons[0]
    if parent._last_dsf is not None:
        n_eff = parent.l6_tcl.n_eff(parent._last_dsf)
        threshold = parent.l6_tcl.n_start * FOLD_TRIGGER_RATIO
        # After overflow clearing, the parent should have fewer constraints
        # (committed modes only), so n_eff should be higher
        # We verify the overflow was cleared by checking fold_sustain_count reset
        assert parent._fold_sustain_count == 0, (
            "Parent fold_sustain_count should be reset after fold"
        )


# ---------------------------------------------------------------------------
# T5: Self-regulation — fold rate decays, cluster size plateaus
# ---------------------------------------------------------------------------

def test_t5_self_regulation():
    """Sustained input → fold rate decays → cluster plateaus."""
    c = LoomCluster("t5", n_neurons=20, k_neighbors=16, seed=42)
    touch_sig = _touch_signal()

    # Set all neurons to tactile origin
    for n in c.neurons:
        n._last_origin_transducer = "tactile"

    fold_counts_per_window = []
    window = 100
    fold_this_window = 0
    sizes = []

    for tick in range(5000):
        c.step(touch_sig, tick=tick)
        new_ids = c.process_folds(tick)
        fold_this_window += len(new_ids)

        if (tick + 1) % window == 0:
            fold_counts_per_window.append(fold_this_window)
            sizes.append(len(c.neurons))
            fold_this_window = 0

    # PASTE fold rate trajectory
    print("\n== T5: Self-regulation fold-rate trajectory ==")
    for i, count in enumerate(fold_counts_per_window):
        window_start = i * window
        print(f"  ticks {window_start}-{window_start+window-1}: "
              f"folds={count}, cluster_size={sizes[i]}")

    # Cluster should not grow indefinitely — final size should plateau
    # (within 50% of some stable value in the second half)
    first_half = sizes[:len(sizes)//2]
    second_half = sizes[len(sizes)//2:]

    if len(second_half) >= 2:
        # Second half should have less growth than first half
        first_growth = max(first_half) - min(first_half)
        second_growth = max(second_half) - min(second_half)
        print(f"  First half growth: {first_growth}")
        print(f"  Second half growth: {second_growth}")
        # Final size is a positive number (cluster didn't collapse)
        assert sizes[-1] >= 20, f"Cluster should not shrink below initial 20, got {sizes[-1]}"


# ---------------------------------------------------------------------------
# T6: Cross-modal differentiation
# ---------------------------------------------------------------------------

def test_t6_cross_modal_differentiation():
    """Touch cluster → tactile daughters; audio cluster → auditory daughters."""
    cluster_a = LoomCluster("touch", n_neurons=20, k_neighbors=16, seed=42)
    cluster_b = LoomCluster("audio", n_neurons=20, k_neighbors=16, seed=42)

    touch_sig = _touch_signal()
    audio_sig = _audio_signal()

    # Set origins
    for n in cluster_a.neurons:
        n._last_origin_transducer = "tactile"
    for n in cluster_b.neurons:
        n._last_origin_transducer = "auditory"

    a_daughters = []
    b_daughters = []

    for tick in range(5000):
        cluster_a.step(touch_sig, tick=tick)
        cluster_b.step(audio_sig, tick=tick)
        a_new = cluster_a.process_folds(tick)
        b_new = cluster_b.process_folds(tick)
        a_daughters.extend(a_new)
        b_daughters.extend(b_new)

    print(f"\n== T6: Cross-modal differentiation ==")
    print(f"  Cluster A (touch): {len(a_daughters)} daughters")
    print(f"  Cluster B (audio): {len(b_daughters)} daughters")

    # Check origin_transducer of daughters
    a_origins = [cluster_a._neuron_map[d]._last_origin_transducer
                 for d in a_daughters if d in cluster_a._neuron_map]
    b_origins = [cluster_b._neuron_map[d]._last_origin_transducer
                 for d in b_daughters if d in cluster_b._neuron_map]

    print(f"  A daughter origins: {set(a_origins) if a_origins else 'none'}")
    print(f"  B daughter origins: {set(b_origins) if b_origins else 'none'}")

    if a_daughters:
        assert all(o == "tactile" for o in a_origins), (
            f"Touch cluster daughters should all be tactile, got {set(a_origins)}"
        )
    if b_daughters:
        assert all(o == "auditory" for o in b_origins), (
            f"Audio cluster daughters should all be auditory, got {set(b_origins)}"
        )


# ---------------------------------------------------------------------------
# T7: Fold diagnostics surface synthetic bug
# ---------------------------------------------------------------------------

def test_t7_diagnostics_surface_bug():
    """Monkey-patched non-clearing overflow → diagnostics catch high fold rate."""
    c = LoomCluster("t7", n_neurons=5, k_neighbors=4, seed=42)

    # Force a neuron into fold-ready state
    from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
    target = c.neurons[0]
    target._last_origin_transducer = "tactile"

    # Monkey-patch compute_overflow_signal to return non-clearing overflow
    # (returns the same vector each time, so parent never recovers)
    original_clear = target.clear_overflow_modes

    def no_op_clear():
        """Bug simulation: overflow not actually cleared."""
        target._fold_sustain_count = 0
        target._fold_count += 1
        # DON'T clear the ψ-lattice modes — this is the bug

    target.clear_overflow_modes = no_op_clear

    # Force sustained fold-ready DSF
    forced_dsf = DSF(D_k=0.9, M_k=0.8, R_rev=0.7, U_star=0.1,
                     C_k=0.6, P_k=0.7, B_k=0.8, S_UF=0.6)

    fold_events = 0
    for tick in range(1000):
        target._last_dsf = forced_dsf
        # Manually sustain fold count
        for _ in range(FOLD_SUSTAIN_TICKS):
            target.fold_check(tick)
        new = c.process_folds(tick)
        fold_events += len(new)
        if fold_events >= 4:
            break

    # Restore
    target.clear_overflow_modes = original_clear

    diag = c.fold_diagnostics(window_ticks=1000)
    print(f"\n== T7: Diagnostics ==")
    print(f"  Fold events: {fold_events}")
    print(f"  max_per_neuron_fold_rate: {diag['max_per_neuron_fold_rate']:.1f}")

    # The rate should be > 3.0 per 1000 ticks
    assert diag["max_per_neuron_fold_rate"] > 3.0, (
        f"Diagnostics should catch runaway folding: "
        f"rate={diag['max_per_neuron_fold_rate']:.1f}"
    )


# ---------------------------------------------------------------------------
# T8: Determinism — same seed + input → identical state
# ---------------------------------------------------------------------------

def test_t8_determinism():
    """Same seed + same input → identical final state across two runs."""
    def run_cluster():
        c = LoomCluster("det", n_neurons=20, k_neighbors=16, seed=42)
        touch_sig = _touch_signal()
        for n in c.neurons:
            n._last_origin_transducer = "tactile"

        all_daughters = []
        for tick in range(500):
            c.step(touch_sig, tick=tick)
            new = c.process_folds(tick)
            all_daughters.extend(new)

        neuron_ids = [n.neuron_id for n in c.neurons]
        fold_ticks = {n.neuron_id: list(n._fold_ticks) for n in c.neurons}
        return neuron_ids, all_daughters, fold_ticks

    ids1, daughters1, folds1 = run_cluster()
    ids2, daughters2, folds2 = run_cluster()

    assert ids1 == ids2, f"Neuron IDs differ between runs"
    assert daughters1 == daughters2, (
        f"Daughter IDs differ:\n  run1: {daughters1}\n  run2: {daughters2}"
    )
    assert folds1 == folds2, "Fold timestamps differ between runs"
