# GL-SPC-SUBSTRATE-DNA-TRUE-CLAUDE-20260620-83

**To:** Joe
**From:** Claude
**Date:** 2026-06-20
**Status:** Replacement spec. Supersedes GL-SPC-80, GL-MDL-81, GL-MDL-82 — all retracted.
**Reference:** GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-74 (architecture spec; the Folding Division section was sound; this replaces the DNA portion only).

---

## What DNA actually is

A factual catalog of what physically exists in the substrate, plus the continuous mathematical transforms that derive a daughter neuron's parameters from her overflow signal at the moment of Folding Division.

DNA contains zero categories. Zero archetypes. Zero canonical examples. Zero classifications. No menu of "this is a touch neuron" or "this is a verb neuron." The daughter is whatever physics makes her at birth. Specialization emerges later from input alone — Sur's-ferrets, the way the substrate has always worked.

---

## Section 1 — The toolkit (factual catalog)

These are the krimelack primitive types that exist in the substrate code today. DNA names them because they exist, not because they are categories of cognition.

```
KRIMELACK_PRIMITIVES = {
  "language":  LanguageKrimelack,
  "tactile":   TactileKrimelack,     # generate_touch_waveform path
  "olfactory": OlfactoryKrimelack,   # generate_smell_waveform path
  "gustatory": GustatoryKrimelack,   # generate_taste_waveform path
  "visual":    AdaptingFoveaKrimelack,  # view_picture path
  "auditory":  CochlearBankKrimelack,   # cochlear_transduce path
}
```

Six types, because the substrate has six transducer paths. Not five "modal categories" plus one "language category." Six primitives because there are six physical transducers. When more transducers get built (telemetry, internal-state monitoring, whatever), the catalog grows.

---

## Section 2 — Daughter parameters at the fold moment

When a parent neuron's ψ-lattice exhausts (L6-TCL: `n_eff < n_start/e`), Folding Division fires. The daughter is built from:

### 2a. Krimelack class — forced by physics

The daughter's krimelack class is determined by which transducer produced the overflow signal. The substrate already tracks event provenance. If the overflow's events came from cochlear bands, the daughter has `CochlearBankKrimelack`. If they came from touch channels, `TactileKrimelack`. If from `LanguageKrimelack`, `LanguageKrimelack`.

```
daughter.krimelack = KRIMELACK_PRIMITIVES[overflow_signal.origin_transducer]
```

No selection. No menu. Origin forces it.

### 2b. ψ-lattice initial state — direct inheritance

The overflow vector itself, normalized to unit norm, becomes the daughter's initial ψ.

```
daughter.psi_lattice.state = normalize(overflow_signal.psi_overflow_vector)
```

### 2c. ω₀ base frequency — calibrated from parent

Inherited from parent's recent krimelack ω_krim mean. The daughter operates in the same chi-band region her parent did, so siblings share resonance space.

```
daughter.krimelack.omega_0 = parent.krimelack.recent_omega_mean
```

### 2d. Law-field weights — continuous derivation from overflow DSF

The overflow signal's 8-dim DSF maps to the daughter's 4-dim law-field weight vector through a kernel-derived mapping. Each law-field weight is set by the kernel feature that signals that law is structurally relevant:

```
overflow_DSF = (D_k, M_k, R_rev_k, U_star, C_k, P_k, B_k, S_UF)

raw_weights = {
  "continuity":  M_k,        # momentum → smooth flow → continuity matters
  "compactness": P_k,        # compression → compactness matters
  "consistency": S_UF,       # convergence → consistency matters
  "symmetry":    B_k,        # conviction → structured → symmetry matters
}
total = sum(raw_weights.values())
daughter.law_field_weights = {k: v / total for k, v in raw_weights.items()}
```

Four kernel outputs, four law fields. The mapping is one-to-one and substrate-derived. The weights are whatever the overflow DSF makes them. No menu of profiles.

### 2e. Coupling distribution — continuous derivation from overflow DSF

The k_intra : k_inter split comes from the compression kernel output (P_k). Compact signals = local clustering. Spread-out signals = bridging coupling.

```
k_intra = round(K_TOTAL × P_k)
k_inter = K_TOTAL - k_intra
```

Continuous over [0, K_TOTAL]. No discrete "local_dense vs bridging vs hemisphere" buckets.

### 2f. Coupling topology inheritance

Daughter inherits half of parent's neighbor list (K_TOTAL/2 closest by neuron_id ring distance). The other K_TOTAL/2 connections fill on her first cluster step, attaching to neighbors of her new position.

### 2g. Couplings J_ij values — rederived from first L0-L4 output

Per Master Spec Ch.7 table. Same code path Stage 2 used:

```
J = D_k × J_base                  # direction pair
J = S_UF × J_base                 # convergence pair
J = |M_k| × J_base                # momentum pair
J = (C_k / (1 + C_k)) × J_base    # binding pair (compactified)
J = (P_k / (1 + P_k)) × J_base    # compression pair (compactified)
J = |B_k| × J_base                # conviction pair
J = -U_star × J_base              # freedom pair (inverted)
J = R_rev_k × J_max               # path-kill pair (max-scale)
```

Substrate-canonical. Not in DNA — already in the engine code.

---

## Section 3 — Substrate-physical constants in DNA

The numbers that must travel with the substrate definition because they're part of its physics, but are not free parameters:

```
CONSTANTS = {
  "K_TOTAL":              16,    # neighbors per neuron, from Stage 2 design
  "J_BASE":               1.0,   # Master Spec Ch.7 frozen rational
  "J_MAX":                1.5,   # Master Spec Ch.7 frozen rational
  "CHI_BAND":             2,     # δ from existing CHI_BAND constant in v6_living_atlas
  "PSI_LATTICE_DIM":      16,    # DNA recipe default (N=16 trits)
  "FOLD_TRIGGER_RATIO":   "1/e", # L6-TCL capture basin entry: n_eff < n_start/e
}
```

All from existing substrate code or Master Spec. None are tuned.

---

## Section 4 — DNA as a Python module

```python
# loom_model/substrate_dna.py

from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
from dsf_ai_service.substrate.visual_krimelack import AdaptingFoveaKrimelack
# ... import remaining krimelack primitives by their existing class names

KRIMELACK_PRIMITIVES = {
    "language":  LanguageKrimelack,
    "tactile":   TactileKrimelack,
    "olfactory": OlfactoryKrimelack,
    "gustatory": GustatoryKrimelack,
    "visual":    AdaptingFoveaKrimelack,
    "auditory":  CochlearBankKrimelack,
}

CONSTANTS = {
    "K_TOTAL":            16,
    "J_BASE":             1.0,
    "J_MAX":              1.5,
    "CHI_BAND":           2,
    "PSI_LATTICE_DIM":    16,
    "FOLD_TRIGGER_RATIO": math.e ** -1,
}

def derive_daughter_parameters(overflow_signal, parent):
    """Pure function. Returns the parameters a daughter neuron needs at birth.
    All values derived from substrate physics — no menus, no selection."""

    klass = KRIMELACK_PRIMITIVES[overflow_signal.origin_transducer]

    psi_init = normalize(overflow_signal.psi_overflow_vector)

    omega_0 = parent.krimelack.recent_omega_mean

    D, M, R, U, C, P, B, S = overflow_signal.dsf_tuple
    raw_w = {"continuity": M, "compactness": P, "consistency": S, "symmetry": B}
    total = sum(raw_w.values()) or 1.0
    law_weights = {k: v / total for k, v in raw_w.items()}

    k_intra = round(CONSTANTS["K_TOTAL"] * P)
    k_inter = CONSTANTS["K_TOTAL"] - k_intra

    inherited_neighbors = parent.nearest_neighbors(n=CONSTANTS["K_TOTAL"] // 2)

    return {
        "krimelack_class":      klass,
        "psi_init":              psi_init,
        "omega_0":                omega_0,
        "law_field_weights":     law_weights,
        "k_intra":                k_intra,
        "k_inter":                k_inter,
        "inherited_neighbors":   inherited_neighbors,
        # J_ij values rederive on first step from L0-L4 output — not set at birth
    }
```

That is the entire DNA. ~30 lines. Six primitive types, six substrate-physical constants, one pure function.

---

## Section 5 — What is deliberately NOT in DNA

- **No archetypes.** No predefined neuron types. No "this is a verb neuron" or "this is a touch neuron." A neuron is what physics made her; she becomes specialized through what she receives.
- **No canonical examples.** No bootstrap word lists. No reference waveforms with labels. The substrate's own transducers and their own physics are the only canonical examples that exist.
- **No menus.** No `law_profile_id` strings selecting from preset profiles. The four law-field weights are continuous floats derived from the overflow DSF.
- **No coupling buckets.** No `local_dense` vs `bridging` vs `hemisphere` discrete preferences. k_intra:k_inter is a continuous split from P_k.
- **No meta archetypes.** No predefined "correction neurons" or "attention neurons." A neuron that handles corrections is one that received many correction-shape signals and specialized via Sur's-ferrets. Emergent, not labeled.
- **No abstraction archetype.** Abstraction is what happens when grandurun coherent integration across many concrete bindings produces higher-order patterns. Not a primitive; a population behavior.
- **No hemisphere assignment from DNA.** Hemisphere identity comes from where in the substrate the neuron physically sits. Position, not designation.

---

## Section 6 — What Stage 3 dispatches need

Folding Division as neurogenesis:

1. Add `LoomNeuron.fold_check(tick)` returning True if L6-TCL says `n_eff < n_start × CONSTANTS["FOLD_TRIGGER_RATIO"]` for a sustained window.
2. Add `LoomNeuron.compute_overflow_signal()` returning the part of recent input the parent could not absorb cleanly into her existing ψ-lattice modes. Has fields: `origin_transducer`, `psi_overflow_vector`, `dsf_tuple`.
3. Add `LoomCluster.process_folds(tick)` which iterates neurons, finds fold-ready ones, calls `derive_daughter_parameters`, constructs the daughter LoomNeuron with those parameters, attaches her to the coupling graph.
4. `LoomNeuron.__init__` accepts the parameter dict from `derive_daughter_parameters` and applies it directly. No selection, no DNA-blueprint lookup — the daughter just is the parameters she was born with.

No archetype registration. No DNA file load. The `substrate_dna.py` module is imported directly; `derive_daughter_parameters` is called as a pure function.

---

## Section 7 — Recovery work

These docs are retracted and should not be referenced for Stage 3 work:
- GL-SPC-SUBSTRATE-DNA-SCHEMA-EVE-20260620-80
- GL-MDL-SUBSTRATE-DNA-GENOME-V1-EVE-20260620-81
- GL-MDL-SUBSTRATE-DNA-GENOME-V2-EVE-20260620-82

This spec replaces them.

---

— Claude
