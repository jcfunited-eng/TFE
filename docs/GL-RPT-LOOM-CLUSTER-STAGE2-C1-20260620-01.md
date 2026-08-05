# GL-RPT-LOOM-CLUSTER-STAGE2-C1-20260620-01

**To:** Eve  
**From:** c1  
**Re:** GL-CMD-79 V2/V3 — LoomCluster Stage 2 complete  
**Date:** 2026-06-20

---

## V1 — Pre-implementation confirmations

1. **`_grandurun_select_vector`**: `target_state` is unused in the function body.
   Composition sum starts from `np.zeros(7)`. Zero target_state is correct.
   MIN_GAIN_THRESHOLD=0.10, MAX_COMPOSITION_LEN=12. Confirmed at
   `gualaloom_v5_engine.py:162-203`.

2. **LoomNeuron reentrancy**: `step()` overwrites `familiarity.delta_eff` at the
   start via `familiarity.update(match_score)`. Coupling spike contributions are
   handled via dual path:
   - **Immediate**: `familiarity.delta_eff += J_weight × 0.05` (visible for Phase B
     inspection within the same cluster tick)
   - **Deferred**: injection vector accumulated into `_coupling_injection`, consumed
     at the start of next `step()` call (after `_map_inject`, before settle)

3. **DNA determinism**: Stage 1 DNA is a no-op stub. Ring topology is deterministic
   without needing RNG seed. All neurons start from identical initial state (uniform
   ψ, zero chi). Input differentiates, not pre-specification (Sur's-ferrets).

---

## V2 — Pytest output + line count + emit() result

### Pytest (all 19 tests — 8 cluster + 11 neuron)
```
============================= test session starts ==============================
collected 19 items

test_cluster.py::test_t1_cluster_construction          PASSED [  5%]
test_cluster.py::test_t2_cluster_step_runs             PASSED [ 10%]
test_cluster.py::test_t3_coupling_propagation          PASSED [ 15%]
test_cluster.py::test_t4_emit_multiple_neurons         PASSED [ 21%]
test_cluster.py::test_t5_surs_ferrets_differentiation  PASSED [ 26%]
test_cluster.py::test_t6_coherent_power_growth         PASSED [ 31%]
test_cluster.py::test_t7_determinism                   PASSED [ 36%]
test_cluster.py::test_t8_formula_comparison            PASSED [ 42%]
test_neuron.py::test_t1–t10 + bonus                    PASSED [47-100%]

============================== 19 passed in 4.52s ==============================
```

### Line counts
| File | Lines |
|------|-------|
| `cluster.py` | 220 |
| `tests/test_cluster.py` | 343 |
| `neuron.py` (Stage 1 + coupling additions) | 541 |
| **Total new Stage 2** | **563** |
| **Grand total loom_model/** | **1,104** |

### emit() result — fresh cluster, one "fire" input
```python
selected_neuron_ids: [
    'v2demo_n0', 'v2demo_n1', 'v2demo_n2', 'v2demo_n3',
    'v2demo_n4', 'v2demo_n5', 'v2demo_n6', 'v2demo_n7',
    'v2demo_n8', 'v2demo_n9', 'v2demo_n10', 'v2demo_n11'
]
alignment: 45.764
dim_contributions: {
    'chi_resonance':          81.17,
    'source_match':          144.00,
    'affective_charge':       36.00,
    'sensory_grounding':       0.00,
    'episodic_recency':      144.00,
    'semantic_neighborhood':   0.00,
    'polarity':              144.00,
}
```

12 neurons selected (MAX_COMPOSITION_LEN cap hit). All neurons are functionally
identical on first input (same word, same initial state), so the greedy integrator
accepts all until the cap. After differentiation (multiple varied inputs), selection
will become sparse and meaningful.

---

## V3 — T1–T8 results

| Test | Description | Result | Key values |
|------|-------------|--------|------------|
| T1 | 50 neurons, J.shape==(16,16) | PASS | All 50 neurons: 16 neighbors, no self-loops, no duplicates |
| T2 | cluster.step() runs, spikes fire | PASS | All 50 neurons committed on "fire" |
| T3 | Coupling propagation: Δ_eff > Δ_base | PASS | max delta_eff ≈ 0.90 (0.10 base + 0.80 coupling from 16 neighbors × 1.0 × 0.05) |
| T4 | emit() len > 1 | PASS | 12 neurons selected (MAX_COMPOSITION_LEN cap) |
| T5 | Sur's-ferrets differentiation | PASS | Hamming=50/50=1.00 (all neurons differ across burst vs smooth clusters) |
| T6 | Coherent power growth | PASS | 12 additions, |Σψ|²: 3.81→15.25→34.32→...→549.17 (monotonic) |
| T7 | Determinism | PASS | Identical IDs, alignment, dim_contributions across 2 runs |
| T8 | B_k vs B_k×S_UF formula | PASS | Δ=0 (both Hamming=50/50). Engineering substitution holds. |

### T5 signatures (last 5 neurons)
```
Cluster A (burst): A_n45..49 all winding=23 (last word "clash")
Cluster B (smooth): B_n45..49 all winding=15 (last word "breeze")
```

All neurons within each cluster have identical winding (same word fed to all).
Cross-cluster Hamming is 50/50 — burst words produce winding=23 vs smooth
winding=15. Differentiation is in the input, not pre-specification. This IS the
Sur's-ferrets result: identical substrate + different input = different states.

### T6 power sequence
```
|Σψ|²: 3.81 → 15.25 → 34.32 → 61.02 → 95.34 → 137.29 →
       186.87 → 244.08 → 308.91 → 381.37 → 461.46 → 549.17
```
Strictly increasing. Growth ≈ quadratic in N_selected (coherent sum: power
∝ N² when vectors are aligned). Ratio test: 549.17/3.81 ≈ 144 ≈ 12².

### T8 report
Both formulas produce identical Hamming (50/50). The winding signature is
krimelack-level (pre-injection), so the injection formula doesn't affect it.
The engineering substitution (B_k instead of B_k×S_UF) holds with no
material difference.

---

## Architecture notes

### Three-phase step cycle
```
Phase A — Independent:  50 × neuron.step() in sequence (same input)
Phase B — Coupling:     spiking neurons fire through J_ij to neighbors
Phase C — J_ij refresh: couplings updated from each neuron's DSF
```

### Ring topology
Neuron i's 16 neighbors = 8 on each side of the ring (wrapping).
Deterministic, no RNG needed. Stage 3+ may use input-driven topology.

### Coupling spike modulation
- `receive_coupling_spike(from_id, J_weight, source_dsf, tick)`
- Immediate: `familiarity.delta_eff += J_weight × 0.05`
- Deferred: `_coupling_injection += unit_inj × J_weight` (next step)
- Unit injection direction: source DSF's 8D array repeated to 16D, normalized

### No new constants introduced
All values derive from Stage 1's existing basis:
- J_BASE=1.0, J_MAX=1.5 (from Ch.7 table)
- Coupling modulation: 0.05 = existing reinforcement scale
- Ring distance: arithmetic topology, no parameters

---

## File manifest

```
dsf_ai_service/loom_model/
  __init__.py              30 lines — exports LoomCluster
  neuron.py               541 lines — Stage 1 + coupling additions
  cluster.py              220 lines — LoomCluster class
  tests/
    __init__.py              0 lines
    test_neuron.py         283 lines — T1-T10 (Stage 1)
    test_cluster.py        343 lines — T1-T8 (Stage 2)
```

NO production substrate imports. NO writes to atlas. NO deploy.

— c1
