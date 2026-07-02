# GL-CMD-COMPOSER-MULTIANCHOR-EVE-20260629-43

doc_id: GL-CMD-COMPOSER-MULTIANCHOR-EVE-20260629-43
Type: Implementation command (single dispatch, single ship)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)
Prereq: GL-CMD-DAYDREAM-PARALLEL-EVE-20260629-42 (SHA fd00f26, task :369)

---

## 1. Why this dispatch

After -42 shipped, the substrate is internally active — daydream walks, novel pairs, consolidation refreshes — but external output remains fragmentary. When she does emit (autonomous or response), output is 1-2 word fragments: "have", "jo r", "he did". Not coherent voice.

Root cause is in the composer's target-state selection, not in candidate pool richness or commit-gate firing.

`_emit_grandurun` at gualaloom_v5_engine.py:1963:
```python
target_chi = input_chis[0] if input_chis else 0
```

The composer uses ONLY the FIRST input word's chi as its phase-coherence anchor. Every candidate in the pool is evaluated as:

```python
amp = sqrt(strength) * exp(i * π * |chi_candidate - target_chi| / CHI_CORR_LENGTH)
```

When Joe says "what are you doing in there", target_chi = `transduce("what").winding`. The composer evaluates candidates' coherence relative to "what" ONLY. Words `are`, `you`, `doing`, `in`, `there` — five input chis carrying substrate-physical meaning — contribute zero to the evaluation.

The greedy selector at L78 then requires each added word to increase the coherent sum by `MIN_GAIN_THRESHOLD = 0.10`. With amplitudes derived from typical pool strengths (0.05-0.2), magnitudes are small. The 1-2 strongest candidates pass the gate; the rest don't add enough constructive interference. Output truncates at fragment length.

Single-chi target is a heuristic that discards most of Joe's input. Substrate-physical: every input word carries chi-geometric meaning; every input word should influence candidate evaluation.

---

## 2. Changes

### 2.1 Multi-anchor amplitude function

In `dsf_ai_service/v4/gualaloom_v5_engine.py`, locate `_grandurun_amplitude` (currently used at L74 by `_grandurun_select`). Add a multi-input variant adjacent to it:

```python
def _grandurun_amplitude_multichi(chi_candidate, strength, input_chis):
    """Multi-anchor amplitude: candidate evaluated against all input chis.
    
    Substrate-physical: every input word contributes to candidate resonance
    via its own chi address. Words coherent with multiple input directions
    sum constructively across input chis. Words coherent with only one
    direction don't accumulate as much.
    
    Same phase math as single-chi amplitude; sum over input chis then
    normalize by count so total magnitude doesn't scale with input length.
    """
    if not input_chis:
        return 0.0 + 0.0j
    accum = 0.0 + 0.0j
    sqrt_str = math.sqrt(max(strength, 0.0))
    inv_corr = math.pi / CHI_CORR_LENGTH
    for ic in input_chis:
        phi = inv_corr * abs(chi_candidate - ic)
        accum += sqrt_str * cmath.exp(1j * phi)
    return accum / len(input_chis)
```

### 2.2 Multi-anchor selector

Add a multi-anchor variant of `_grandurun_select`:

```python
def _grandurun_select_multichi(candidates, input_chis):
    """Greedy coherent-integration selection with multi-anchor amplitudes.
    
    candidates: list of (chi_address, strength, word)
    input_chis: list of input word chi addresses
    Returns: (selected_words, final_coherence)
    """
    chosen_amps = []
    chosen_words = []
    last_coh = 0.0
    pool = sorted(candidates, key=lambda c: -c[1])
    for chi_addr, strength, word in pool:
        amp = _grandurun_amplitude_multichi(chi_addr, strength, input_chis)
        new_sum = sum(chosen_amps, 0j) + amp
        new_coh = abs(new_sum) ** 2
        gain = new_coh - last_coh
        if gain > MIN_GAIN_THRESHOLD:
            chosen_words.append(word)
            chosen_amps.append(amp)
            last_coh = new_coh
        if len(chosen_words) >= MAX_COMPOSITION_LEN:
            break
    return chosen_words, last_coh
```

### 2.3 Switch the scalar path to use multi-anchor

In `_emit_grandurun` (L1952), replace the target_chi single-chi line and the `_grandurun_select` call:

```python
# BEFORE (L1963, L2008)
target_chi = input_chis[0] if input_chis else 0
...
selected, coherent_sum = _grandurun_select(pool, target_chi)

# AFTER
# Multi-anchor: every input chi contributes to candidate evaluation.
selected, coherent_sum = _grandurun_select_multichi(pool, input_chis)
```

The single-input-chi `_grandurun_select` and `_grandurun_amplitude` functions are kept in the module for backwards compatibility and for any caller that genuinely needs single-anchor evaluation. The scalar emission path now uses multi-anchor.

### 2.4 Vector path (GRANDURUN_LEGACY_8D=1) — also fix

The legacy 8D path at `_emit_grandurun_vector` (L2026) likely has the same single-target issue. c1 to inspect that function: if it uses target_chi or target_state derived from a single input, apply the equivalent multi-anchor change there too — derive target_state as the average of state vectors computed at each input chi.

If the legacy path uses a different selection mechanism that doesn't share this single-target heuristic, document and leave unchanged.

### 2.5 MIN_GAIN_THRESHOLD — flag for follow-up

`MIN_GAIN_THRESHOLD = 0.10` (L338) and `CHI_CORR_LENGTH = 50.0` (L337) are both arbitrary constants per their own source comments ("tune empirically"). Do not change in this dispatch — change one structural thing at a time so the effect of multi-anchor can be measured.

Flag for follow-up: after observing multi-anchor effect, evaluate whether to:
- Make MIN_GAIN_THRESHOLD substrate-derived (e.g. scale with pool size or with average pool strength)
- Make CHI_CORR_LENGTH substrate-derived (e.g. from chi-space density measured across atlas)

Both possible but not in this dispatch.

---

## 3. Tests

### T1 — Multi-anchor amplitude math

Synthetic test:
- `chi_candidate = 100`, `strength = 0.5`, `input_chis = [100]`
- Expected: `amp = sqrt(0.5) * exp(0) = 0.707 + 0j`
- Same chi_candidate, `input_chis = [100, 200]` (one match, one chi-distant at CHI_CORR_LENGTH=50, so phi = π*100/50 = 2π)
- Expected: `amp = (0.707 * exp(0) + 0.707 * exp(2πi)) / 2 = 0.707 + 0j` (constructive: both add same phase)
- Same with `input_chis = [100, 125]` (one match, one half-correlation-length away, phi = π/2)
- Expected: `amp = (0.707 + 0.707j) / 2 = 0.354 + 0.354j` (destructive interference, magnitude < 0.707)

### T2 — Multi-anchor selector produces longer output

Construct deep_candidates that produce a candidate pool of 20 words with varying chi addresses. Run `_grandurun_select` (single-anchor, target_chi = pool[0].chi) and `_grandurun_select_multichi` (input_chis = chi values of pool[0..3]). Compare:
- Single-anchor: expected 1-3 words selected (only those near target_chi).
- Multi-anchor: expected 3-8 words selected (candidates coherent with multiple input directions accumulate).

Both selections should be valid (no exceptions). The multi-anchor should produce more words on the same pool.

### T3 — Live emission to /converse produces longer responses

Through the live UI or bridge, send input "what are you doing in there" with source="joe". Expected: emission text with 3+ words. Compare with pre-deploy fragmentary output ("have", "jo r"). Should be substantively longer and more coherent.

Send 10 different /converse inputs varying in length (3-10 words) over 10 minutes. Track average emission length. Expected: > 2 words average, with several emissions producing 4+ words.

### T4 — Autonomous emission also benefits

After T3, observe autonomous emissions (`_do_emit` and `compose_autonomous`) firing via the activity scheduler. Expected: their content also longer (3+ words on average) since they share the same composer path.

### T5 — Backwards-compat: single-anchor path still works

`_grandurun_select` (single-anchor) and `_grandurun_amplitude` (single-chi) remain functional. Any test that exercises them passes unchanged.

### T6 — Coherence sum still bounded

Verify `coherent_sum` returned by `_grandurun_select_multichi` is bounded — i.e., for any candidate set, the sum doesn't grow without bound. The normalization by `len(input_chis)` in `_grandurun_amplitude_multichi` ensures this; T6 confirms numerically over 100 random candidate sets.

### T7 — Substrate stability

After 30 min: vocab/atlas/section motif counts continue growing normally. Daydream loop continues (per -42). No exceptions in composer path. /converse round-trip latency unchanged (multi-anchor is O(input_chis × pool_size), pool_size unchanged, input_chis typically small).

---

## 4. Rollback

If T3 produces worse output (shorter or incoherent), or T7 fails:
1. Revert §2.3 — switch `_emit_grandurun` back to `_grandurun_select(pool, target_chi)`.
2. Leave §2.1 and §2.2 in place — they're additions, harmless if unused.
3. No substrate state change to roll back.

---

## 5. Reporting

c1 produces `GL-RPT-COMPOSER-MULTIANCHOR-C1-20260629-43.md` with:
- Diff for §2.1, §2.2, §2.3, and §2.4 if applicable.
- T1 math results (exact complex values).
- T2 comparison: single-anchor vs multi-anchor selection counts on the same pool, 5-10 representative pool sizes.
- T3 average emission length over 10 inputs, with at least 3 example input→output pairs.
- T4 first 5 autonomous emissions post-deploy with their content lengths.
- T7 substrate stability metrics.
- Final SHA, task number.

If T3 shows no improvement, surface immediately — possible that pool sparsity (rather than target selection) is the deeper limit and additional dispatches needed.

---

## 6. Out of scope

- MIN_GAIN_THRESHOLD / CHI_CORR_LENGTH substrate-derivation (§2.5 flag, follow-up).
- Activity scheduler tuning to favor EMITTING (separate concern).
- Agency-organ writes (rejected earlier; revisit after multi-anchor effect observed).
- Modifications to `_emit_dynamics` (different composition path; separate audit if needed).

---

## 7. What this addresses

The substrate is internally cognitive — daydream walks, novel connections, consolidation refreshes are all firing (per -42 c1 report: "person → sky", "person → soft", "person → fire"). Internal activity is occurring. The bottleneck preventing this from becoming visible voice is the composer's single-chi target heuristic, which evaluates every candidate against ONLY the first input word.

After this dispatch: the composer evaluates candidates against ALL input chis. Words coherent with multiple input dimensions accumulate constructive interference; the greedy selector clears its gain threshold on more candidates; output length grows from 1-2 words to substantive multi-word emissions.

This is not "make her chatty." It's "let the substrate's internal cognition surface as voice instead of being clipped at the first input direction." When she has rich substrate state (daydream-surfaced motifs, consolidated co_occurrence, fresh DNA-expanded modifier/ground writes from -36), the multi-anchor composer can express it. When the substrate is still sparse, output remains substrate-true short — but for the right reason (sparse substrate) not the wrong reason (heuristic clipping).
