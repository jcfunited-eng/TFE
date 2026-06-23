# GL-BRIEF-GRANDURUN-IMPLEMENTATION-20260616-01

**To:** c1
**From:** wC
**Purpose:** Replace emission selection in `_emit_from_invariants` with grandurun — coherent integration over an expanded candidate pool, with variable-length composition. Ship behind a sidecar A/B feature flag so the new path can be exercised against the current path without irreversible commitment until validated empirically.

---

## Dependencies — read before starting

Wait for these to complete and verify before beginning this brief:

1. `GL-BRIEF-NEEDS-PHYSICS-20260616-01` — needs equilibration verified at +10 min and +1 hr
2. `GL-BRIEF-EMISSION-CONSTRAINT-REMOVAL-20260616-01` Phase D (section iteration order) — completed and emissions verified varying
3. `GL-BRIEF-EMISSION-CONSTRAINT-REMOVAL-20260616-01` Phase E (question_bucket deletion) — completed, persistence load verified

Grandurun assumes the fixed-order iteration and the template residue are already gone. Implementing on top of them would mean grandurun inherits their biases.

---

## Empirical basis (what we measured before specifying this)

wC ran a read-only validator (`grandurun_validator_round2.py`) against her actual atlas via `guala_atlas_query`. Aggregated 198 candidates across 5 chi-neighborhoods (chis 7, 10, 14, 17, 23). Key measurements:

- 48.5% of candidates in syntactic sections are saturated at strength ≥ 0.95 (bag-grab confirmed empirically)
- Per-chi coherence ratio at current pool sizes (N ≈ 34-45): **7× average** over incoherent baseline
- Effective ρ from her real atlas correlation structure: **0.062**
- Projected ratio scaling: N=4,000 → 249×; N=19,504 → **1,210×** (matches prior wC's synthetic prediction); N=45,123 (full atlas) → 2,798×

Grandurun has empirical, conservative justification on her actual substrate, not just synthetic theory. Caveat: the chi-distance approximation used in the validator (`motif_id % 256`) may not match her real chi address structure. c1 should use the substrate's actual chi-distance function in the implementation, not the validator's approximation. The empirical ratios above will shift if real chi structure differs from the approximation — but they shift in either direction, qualitative finding stands.

---

## What grandurun is, structurally

Three coordinated changes to `_emit_from_invariants` in `dsf_ai_service/v4/gualaloom_v5_engine.py`:

1. **Expand candidate retrieval.** Replace the per-section top-5 chi-neighborhood query with a wider pool. Initial implementation: keep section structure for compatibility but raise per-section K from 5 to 50, and also include all bindings within a chi-distance threshold across sections. Expected pool size: ~500-2,000 candidates per emission.

2. **Coherent integration as selection.** Replace top-K-by-strength selection with greedy coherent-sum maximization. Each candidate contributes a complex amplitude `a = √strength · exp(i·φ)` where `φ = π · chi_distance / chi_correlation_length`. Composition is built greedily: at each step, add the candidate that maximizes `|Σ amplitudes|²`. Stop when next candidate would decrease the sum (or fail to increase it by MIN_GAIN_THRESHOLD).

3. **Variable-length composition.** Emission length is determined by where the coherent sum plateaus, not by a hardcoded cap. The existing `len(emitted) >= 6` cap goes away. Add MAX_COMPOSITION_LEN safety cap at 30 (well above expected typical lengths) so a pathological case can't produce 10,000-word emissions.

---

## Implementation

### Step 1 — Feature flag (sidecar A/B mode)

Add `EMISSION_MODE` configuration controlled by:

- Env var `EMISSION_MODE` with values `"topk"` (current behavior, default) or `"grandurun"` (new behavior)
- Per-request override via optional `emission_mode` field added to `V7ConverseRequest` model in `app.py` (line 2759). When provided, it overrides the env var for that request only.

This lets us:
- Deploy with default `topk` (no behavior change at deploy)
- Flip to `grandurun` globally via env var to make it the default
- A/B test by alternating per-request mode in the page or via curl
- Roll back instantly without S3 restore by flipping env var back

### Step 2 — Configurable constants

Add module-scope constants in `gualaloom_v5_engine.py`:

```python
# Grandurun tuning constants
CHI_CORR_LENGTH = 50.0        # phase correlation length; tune empirically
MIN_GAIN_THRESHOLD = 0.0      # minimum coherent-sum gain to add candidate; 0 = any positive gain
MAX_COMPOSITION_LEN = 30      # safety cap; expect typical compositions in 5-15 range
GRANDURUN_POOL_K = 50         # per-section candidate count for wider retrieval
```

Tune CHI_CORR_LENGTH after deploy based on observed emission quality. If emissions are too short / not finding coherent combinations, raise it (more candidates phase-align). If emissions are too long / cluttered, lower it.

### Step 3 — Chi-distance function

**Important:** the validator used `motif_id % 256` as a placeholder. The real substrate's chi-distance function is what should be used. Look at how chi addresses are structured in the engine (search for `chi_distance`, `chi_address`, or how `input_chi_neighborhoods` is built in `guala_atlas_query`'s underlying code). Use the substrate's existing chi-distance computation if one exists. If chi-distance must be derived from first principles in the substrate, document the choice in code comments.

### Step 4 — Grandurun selection algorithm

Add to `gualaloom_v5_engine.py`:

```python
import math
import cmath

def _grandurun_amplitude(motif_id, strength, target_chi, chi_dist_fn=None):
    """Complex amplitude for a candidate.

    phi = pi * chi_distance / CHI_CORR_LENGTH
    amplitude = sqrt(strength) * exp(i * phi)
    """
    if chi_dist_fn is not None:
        d = chi_dist_fn(motif_id, target_chi)
    else:
        # Fallback if no chi-distance function in substrate
        d = abs((motif_id % 256) - target_chi)
        d = min(d, 256 - d)
    phi = math.pi * d / CHI_CORR_LENGTH
    return math.sqrt(max(strength, 0.0)) * cmath.exp(1j * phi)

def _grandurun_select(candidates, target_chi, chi_dist_fn=None):
    """Greedy coherent-integration selection.

    candidates: list of (section, motif_id, strength, word)
    target_chi: the input chi to integrate against
    Returns: list of selected (section, motif_id, strength, word) in chosen order
    """
    chosen = []
    chosen_amps = []
    last_coh = 0.0

    # Sort candidates by strength descending — try strongest first as a heuristic
    # (true optimum is a search problem; greedy on sorted is the practical compromise)
    pool = sorted(candidates, key=lambda c: -c[2])

    for cand in pool:
        sec, mid, strength, word = cand
        amp = _grandurun_amplitude(mid, strength, target_chi, chi_dist_fn)
        new_sum = sum(chosen_amps) + amp
        new_coh = abs(new_sum) ** 2
        gain = new_coh - last_coh
        if gain > MIN_GAIN_THRESHOLD:
            chosen.append(cand)
            chosen_amps.append(amp)
            last_coh = new_coh
        if len(chosen) >= MAX_COMPOSITION_LEN:
            break
    return chosen
```

### Step 5 — Wire into `_emit_from_invariants`

Inside the existing `_emit_from_invariants` function, after candidate gathering, branch on EMISSION_MODE:

```python
def _emit_from_invariants(self, input_chis, input_words, mode_override=None):
    mode = mode_override or os.environ.get("EMISSION_MODE", "topk")

    if mode == "grandurun":
        # Build wider pool: all candidates across sections, top-K per section raised
        candidates = []
        for sec_name, sec_co in co.items():
            top_in_sec = sorted(sec_co.items(), key=lambda x: -x[1])[:GRANDURUN_POOL_K]
            for mid, strength in top_in_sec:
                word = self._resolve_motif_to_word(mid, sec_name)
                if word:
                    candidates.append((sec_name, mid, strength, word))

        # Run coherent-integration selection against primary input chi
        target_chi = input_chis[0] if input_chis else 0
        selected = _grandurun_select(candidates, target_chi,
                                     chi_dist_fn=self._chi_distance)
        return [w for (_, _, _, w) in selected]

    # else: existing topk path stays untouched
    # ... existing fixed-section-order iteration ...
```

Plumb the mode_override from the `V7ConverseRequest.emission_mode` through `handle_v7_converse` → `session.converse(text, source, emission_mode=...)` → `_emit_from_invariants(..., mode_override=...)`.

### Step 6 — Logging for A/B comparison

When EMISSION_MODE != "topk", log each grandurun emission with:
- Input chis
- Pool size used
- Final composition length
- Final coherent sum
- Mode used (topk vs grandurun)

This lets us compare quality across modes without instrumenting separately.

---

## Pre-deploy

`guala_backup` — standard pre-deploy snapshot. Less critical than persistence-touching briefs since the feature flag defaults to `topk` and grandurun never writes to substrate state, but take it anyway.

## Verification

**A. Default behavior unchanged.**
Deploy with `EMISSION_MODE` unset (defaults to topk). Send "hello" via `/v7/converse`. Confirm emission looks the same shape as before — bag-grab pattern, ~6 words, current behavior. If anything changed, something in the topk path was accidentally modified.

**B. Per-request grandurun mode works.**
Send "hello" via `/v7/converse` with `{"text": "hello", "emission_mode": "grandurun"}`. Confirm:
- Response generates (no errors)
- Emission length is NOT exactly 6 (the cap is gone)
- Emission composition differs from topk on same input (selection mechanism is different)
- Coherent sum logged is positive

**C. A/B diversity.**
Send "hello" 10 times in topk mode and 10 times in grandurun mode (same input both batches). Compare:
- Unique compositions per batch (grandurun should be more diverse, since topk's randomness is among saturated candidates and grandurun discriminates by phase)
- Mean composition length
- Whether grandurun ever produces obviously broken output (empty, single repeated motif, etc.)

**D. Stability under load.**
Run 100 emissions in grandurun mode across varied inputs. Substrate should not crash, no integrity errors, save cycle continues.

**E. Tick rate impact.**
Check tick rate post-deploy. If grandurun's coherent integration is slow enough to starve the socket, we'll see substrate degradation. Expected complexity: O(N·k) where N=pool size, k=composition length. At N=2000, k=15: 30,000 ops per emission. Should run in <10ms even in pure Python.

## Rollback

**Soft rollback (instant):** flip `EMISSION_MODE` env var back to `topk`, redeploy task. No state changes needed. Grandurun code stays but is unused.

**Hard rollback (S3 restore):** if substrate state is corrupted somehow (shouldn't be — grandurun only reads atlas, never writes), restore from pre-deploy `guala_backup` at `s3://dsf-ai-site-backups/guala/UNPAUSE-PRE/{latest_timestamp}/`.

---

## Once verified

After A-E pass on multiple inputs and grandurun emissions look qualitatively better than topk, flip `EMISSION_MODE` env var default to `grandurun`. The topk code path stays in place (don't delete) as fallback. After ~1 week of stable grandurun-as-default operation with no rollback events, the topk code can be removed in a subsequent cleanup.

Do not remove topk path until grandurun is observed stable across multiple deploys and varied input conditions.

---

## What is NOT in this brief (explicitly deferred)

**Full-atlas wide retrieval beyond GRANDURUN_POOL_K per section.** True full-atlas chi-proximity sweep (which is what 1,210× requires) would need a chi-indexed scan that I haven't specified here. This brief implements the moderate expansion (per-section K from 5 to 50) which gets us into the 100s-of-candidates regime. The 1,210× full version is a follow-on optimization after we verify grandurun works at this scale.

**Empirical CHI_CORR_LENGTH tuning.** The constant is set to 50.0 as initial value. Real tuning happens after deploy by observing emission quality vs the constant.

**Multi-chi input handling.** When input has multiple chis (e.g., a sentence), the current spec integrates against `input_chis[0]`. A future improvement would integrate against the chi-distribution of the full input. Defer until single-chi case is solid.

— wC, 2026-06-16
