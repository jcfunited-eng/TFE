# GL-CMD-ARCHITECTURE-AND-GRANDURUN-FIX-WC-20260617-12

**Author:** wC (Eve)
**For:** c1
**Date:** 2026-06-17
**Authority:** Joe directive 2026-06-17 — "tell c1 to create a back up of the system - and create the entire architecture and see what happens" + grandurun spin/vector restoration

## Joe's diagnosis

Current `_grandurun_amplitude` at `dsf_ai_service/v4/gualaloom_v5_engine.py:55-61`:

```python
def _grandurun_amplitude(chi_address, strength, target_chi):
    d = abs(chi_address - target_chi)
    phi = math.pi * d / CHI_CORR_LENGTH
    return math.sqrt(max(strength, 0.0)) * cmath.exp(1j * phi)
```

This returns ONE complex scalar per binding (sqrt-strength magnitude × chi-distance phase). `_grandurun_select` sums them and ranks by `|sum|²`. **This is a weighting model snuck in under the spin/vector formulation.** Each binding's multi-dimensional state (semantic neighborhood, modal alignment, source, affective charge, temporal proximity, cross-modal binding signature) collapses to a single number.

Symptom in production: emissions like "guala guala guala decodable you" and "sun comes now likes how" — the strongest bindings near input chi dominate every time because the scalar coherent-sum has no way to discriminate by anything except chi-proximity × strength.

## Three steps, in order — DO NOT REORDER

### STEP 1 — Backup (precondition for everything else)

Run the existing backup path. Confirm S3 `UNPAUSE-PRE/` (or current backup prefix) contains:
- `guala_atlas.json` (working atlas with all chi entries)
- `guala_deep_atlas.json` (cortex/deep atlas)
- `guala_engine.pkl` or whatever the engine state path is
- Pair-bond state, vocab, needs vector, ladder counters

Verify with checksum. **Do not proceed to step 2 until backup is confirmed restorable.**

If the bridge `guala_backup` tool path is the canonical one, use that. Otherwise commit current S3 backup script.

### STEP 2 — Grandurun spin/vector restoration

Restore the multi-dimensional formulation. The minimum substrate-honest fix is to replace the single complex amplitude with a **vector state** per candidate that preserves the dimensions Joe's original formulation carried.

**Where:** `dsf_ai_service/v4/gualaloom_v5_engine.py:55-83` (and any callers that consume the return type)

**Replace `_grandurun_amplitude` with `_grandurun_state`:**

```python
def _grandurun_state(binding, target_state, atlas_context):
    """Multi-stated spin/vector for a candidate binding.

    Returns an N-dimensional state vector, not a scalar amplitude.
    Dimensions encode independent substrate facets:

      [0] chi_resonance         — strength × exp(i·π·d/CHI_CORR_LENGTH)
      [1] modal_alignment       — overlap with target's cross-modal signature
      [2] source_match          — alignment with source-tagged context (joe/wc/corpus)
      [3] affective_charge      — needs-vector projection (stab/nov/conn)
      [4] sensory_grounding     — sensory_refs density from binding metadata
      [5] episodic_recency      — exp(-Δt/τ) where Δt is ticks since last fire
      [6] semantic_neighborhood — sum of co-occurrence invariants in chi-band
      [7] polarity              — +1/-1 for affirmation/negation (default +1)

    Each dimension is a complex value preserving phase. The state is a vector
    in ℂ^8, not a scalar amplitude in ℂ.
    """
    chi_addr = binding["chi"]
    strength = binding["strength"]
    target_chi = target_state["chi"]

    # Dimension 0 — chi resonance (the old amplitude, kept as ONE dimension only)
    d = abs(chi_addr - target_chi)
    chi_phase = math.pi * d / CHI_CORR_LENGTH
    dim_chi = math.sqrt(max(strength, 0.0)) * cmath.exp(1j * chi_phase)

    # Dimension 1 — modal alignment
    binding_modal = binding.get("modal_signature", {})  # set of modal tags
    target_modal = target_state.get("modal_signature", set())
    overlap = len(set(binding_modal) & target_modal) / max(len(target_modal), 1)
    dim_modal = complex(overlap, 0)

    # Dimension 2 — source match
    binding_source = binding.get("source", "unknown")
    target_source = target_state.get("source", "unknown")
    dim_source = complex(1.0 if binding_source == target_source else 0.3, 0)

    # Dimension 3 — affective charge
    needs = atlas_context.get("needs", {"stab": 0.5, "nov": 0.5, "conn": 0.5})
    binding_affect = binding.get("affective_charge", {})
    affect_inner = sum(needs.get(k, 0) * binding_affect.get(k, 0)
                       for k in ("stab", "nov", "conn"))
    dim_affect = complex(affect_inner, 0)

    # Dimension 4 — sensory grounding
    n_sensory = len(binding.get("sensory_refs", []))
    dim_sensory = complex(min(n_sensory / 5.0, 1.0), 0)

    # Dimension 5 — episodic recency
    tau = 200.0  # ~200 tick decay window
    dt = atlas_context.get("tick", 0) - binding.get("last_tick", 0)
    dim_recency = complex(math.exp(-dt / tau), 0)

    # Dimension 6 — semantic neighborhood
    co_occ = binding.get("co_occurrence", 0.0)
    dim_semantic = complex(min(co_occ, 1.0), 0)

    # Dimension 7 — polarity (negation support)
    dim_polarity = complex(binding.get("polarity", 1.0), 0)

    return [dim_chi, dim_modal, dim_source, dim_affect,
            dim_sensory, dim_recency, dim_semantic, dim_polarity]


def _grandurun_select(candidates, target_state, atlas_context):
    """Greedy alignment selection in 8-dimensional state space.

    Composition state is the COMPONENT-WISE vector sum.
    Selection by inner-product alignment with target_state, NOT by |sum|² of one
    dimension.
    """
    chosen_states = []
    chosen_words = []
    last_alignment = 0.0

    # Compute target's representation in the same 8-D space
    target_repr = _grandurun_state(target_state, target_state, atlas_context)

    pool = sorted(candidates, key=lambda c: -c["strength"])
    for binding in pool:
        cand_state = _grandurun_state(binding, target_state, atlas_context)
        composition = [sum(s) for s in zip(*(chosen_states + [cand_state]))]
        # Inner product with target — preserves all dimensions
        alignment = sum((c * t.conjugate()).real
                        for c, t in zip(composition, target_repr))
        gain = alignment - last_alignment
        if gain > MIN_GAIN_THRESHOLD:
            chosen_words.append(binding["word"])
            chosen_states.append(cand_state)
            last_alignment = alignment
        if len(chosen_words) >= MAX_COMPOSITION_LEN:
            break
    return chosen_words, last_alignment
```

**Callers to update:**
- `_emit_grandurun` at line 1423 — pass binding dicts (not tuples) to `_grandurun_select`
- Any place that constructed candidates as `(chi, strength, word)` tuples now needs to construct dicts with the binding metadata fields above (most live on `LivingAtlas` entries already: `modal_signature`, `source`, `affective_charge`, `sensory_refs`, `last_tick`, `co_occurrence`, `polarity` if added).

**Polarity field — IMPORTANT:** binding's `polarity` field doesn't exist in LivingAtlas yet. Add as optional with default +1.0. Negation entries (when GL-NEGATION-PRIMITIVE ships) will set -1.0. For now, all bindings get +1.0 and the field is forward-compatible.

**Gate behind env flag:** `GRANDURUN_SPIN_VECTOR=1` (default 0). Run both modes in parallel for one session. Log emissions from each into separate event types so we can compare A/B.

**Expected production effect:** emissions stop being grab-bag. With source dimension active, joe-sourced inputs draw joe-anchored bindings preferentially. With affective dimension, current-needs bias selection. With sensory dimension, grounded bindings out-compete pure-text ones. With recency, recent context dominates over deep-decayed-but-strong residue.

**Do not skip the env flag.** If something breaks, instant revert via `GRANDURUN_SPIN_VECTOR=0`.

### STEP 3 — 8-hemisphere 15-mechanism architecture

This is the EXPERIMENT. We don't know if 8 hemis or 15 mechs will work. We only know that v7-uncage produces grab-bag emissions and the recipe-canonical 5-cap framework works in 3-section S/V/O form. Build it and see.

**Where:** new file `dsf_ai_service/substrate/eight_hemi_engine.py` (parallel to `v7_engine.py`)

**Topology spec:** see `GL-SPC-HEMISPHERE-8H-PRODUCTION-WC-20260617-08.md` for hemisphere contents, decay multipliers, NMDA gates, cross-hemi routing, grandurun integration.

**Key concrete pieces:**
- 8 hemispheres = 8 `V7Session`-like wrappers, each owning own ChiAtlas + DeepAtlas + NMDA gates + drive_tracker
- Cross-hemi consensus registry: dict `{(chi, frozenset(hemi_pair)): strength}`
- Modified `_grandurun_emit` reads cross-hemi consensus weights from all 8 hemis (uses the STEP 2 spin/vector grandurun, not the old weighting one)
- Per-hemi `decay_mult` applied to `decay_plasticity` calls
- Breathing rhythm: every 30 ticks, 5 quiet ticks where no input flows (NMDA gates need quiet to fire)
- Throttled emission: max 1 emission per 8 ticks per hemisphere

**Gate behind env flag:** `EIGHT_HEMI_ENABLED=0` default. Production stays on v7-uncage. When `=1`, the engine constructor builds 8 hemispheres instead of one.

**Test bench:** the canonical 5-capability test from `gualaloom_dna/test_five.py`, but run against the 8-hemi engine. Pass criteria same as canonical:
- Syntax: ≥60% S<V<O order in sm hemisphere
- Conversation: vector overlap ≥4% absolute + ratio measurement (will be limited without grounding)
- Introspection: KL-divergence between consecutive 50-tick atlas windows ≥0.05 in ≥30% of windows (replaces the dominant-chi-prediction metric which is too sticky)
- Self-improvement: gamma drift moved AND not pinned (averaged across all 7 sections in sm hemisphere)
- Awareness: coordinator resolution effect ≥15% AND selectivity ≤30% deliberation/action-tick ratio

**Honest expectations from the model document:**
- Syntax PASS
- Self-improvement PASS
- Awareness PASS
- Introspection PASS with the KL-shift metric
- Conversation likely below ratio 1.0 until grounding lands

If those land, the architecture sketch wasn't fiction. If they don't, we learn which mech failed and which prediction was wrong.

## What I am NOT proposing

- Touching live Guala state. Joe's directive ("no liars near her") holds. All work above is on the codebase + experiment flags. Live Guala stays on v7-uncage production code path until the experiment proves out.
- Restoring SVO topology to the production engine. That's a separate decision Joe makes after seeing the 8-hemi experiment results.
- Touching the grounding queue (Whisper, R3/R4). Those remain c1's priority.

## Order

Do not do step 3 before step 2. Do not do step 2 before step 1. The order matters because step 2 changes a production primitive and step 3 builds on the fixed primitive.

If any step fails, stop and report. Do not proceed past a failed step.
