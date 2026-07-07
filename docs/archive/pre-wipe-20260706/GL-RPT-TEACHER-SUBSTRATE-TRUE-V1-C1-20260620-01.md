> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-TEACHER-SUBSTRATE-TRUE-V1-C1-20260620-01

Ref: GL-CMD-TEACHER-CORRECTION-SUBSTRATE-TRUE-EVE-20260619-66
Phase: V1 — Investigation (BEFORE code changes)
Status: Filed for Eve review

---

## STOP CRITERION CHECK

Before the findings: one STOP criterion applies, one does not, one partially applies.

| Criterion | Status |
|---|---|
| No valence field on bindings | DOES NOT APPLY — valence is a float field on every binding |
| Affect-update rule does not take source as input | DOES NOT APPLY — source affects salience → impulse |
| Pair-bond salience boost is a heuristic constant | **APPLIES** — `pair_bond_boost = 1.2` hardcoded; pair-bond is binary (True/False), no continuous strength |

**Additional finding not in the stop list that Eve should review:**
The GL-CMD-66 premise "Joe being upset matters more than wc, by exactly the pair-bond ratio" is unsupported. joe source_weight = 1.6, wc source_weight = 1.6 — identical. pair_bond_boost = 1.2 for both. Joe and wc corrections are indistinguishable via the salience pipeline. See V1.4.

---

## V1.1 — Where does valence exist on bindings?

```
$ grep -nE '"valence"|valence\s*=|valence:' dsf_ai_service/v4/gualaloom_v5_engine.py
```

Selected output:
```
128:    valence  = float(binding.get("valence",  0.5))
1862:  binding.setdefault("valence", clarity.get("valence", 0.5))
2104:  "valence": e.get("valence", 0.0),
2186:  e_val = e.get("valence", 0.0)
3839:  e["valence"] = min(1.0, e.get("valence", 0.5) + TEACHER_VALENCE_DELTA)
3876:  e["valence"] = max(0.0, e.get("valence", 0.5) - TEACHER_VALENCE_DELTA)
```

`valence` lives on binding dicts as a float. Initialized at:
- LivingAtlas.record() line 180: `"valence": valence` — set from the `valence` kwarg at bind time
- line 1862 (in `_process_dynamic_events`): `binding.setdefault("valence", clarity.get("valence", 0.5))`

Modified by:
- LivingAtlas.record() line 147: `existing["valence"] = max(existing.get("valence", 0.0), valence)` — MAX POOLING on reinforce. Can only raise valence, never lower.
- apply_teacher_correction lines 3839/3876: direct write (`e["valence"] = clamp(e["valence"] ± delta)`) — the heuristic from -60 being replaced

**Finding V1.1:** Valence is a native binding field. Initialized at bind time from affect state. On reinforce: max-pooled (can only rise). Direct write only via the heuristic teacher correction code (-60).

---

## V1.2 — Does the existing emission selection consider valence?

Relevant section of `_rich_sensory_candidates`:

### Phase 3 — Direct cross-modal candidates (lines 2095-2111):
```python
cross_modal.append({
    ...
    "coherent_magnitude": e["strength"],   # ← strength only, NO valence
    "valence": e.get("valence", 0.0),      # carried as metadata, not used in cm
    ...
})
```

### Phase 4 — Cofire spread (lines 2183-2208):
```python
e_val = e.get("valence", 0.0)
e_aro = e.get("arousal", 0.5)
w_affect = max(0.1, min(1.0,
    1.0 - 0.5 * abs(e_val - needs_val)
        - 0.5 * abs(e_aro - needs_aro)))
transmission = w_chi * w_strength * w_affect * 0.30
spread_candidates.append({
    ...
    "coherent_magnitude": transmission,    # ← valence IS in cm via w_affect
    ...
})
```

### Phase 5 — Attention boost (lines 2222-2227):
```python
if dist <= 2:
    cand["coherent_magnitude"] *= 1.3
elif dist > 5:
    cand["coherent_magnitude"] *= 0.7
```

### Teaching influence (lines 2229-2234) — the heuristics from -60:
```python
if cand.get("teaching_correction"):
    cand["coherent_magnitude"] *= 0.1
if cand.get("teaching_correction_for"):
    cand["coherent_magnitude"] *= 2.0
```

### SC/GP hemisphere weights (lines 2244-2247):
```python
hw = get_emission_hemisphere_weights(cand, self, sc_cache=sc_cache)
if hw > 0:
    cand["coherent_magnitude"] += hw      # additive
```

**Finding V1.2:**
- **YES** for cofire-spread candidates (Phase 4): valence modulates `coherent_magnitude` via `w_affect`. Low/negative valence binding → lower w_affect → lower cm.
- **NO** for direct cross-modal candidates (Phase 3): `coherent_magnitude = e["strength"]` directly. Valence is metadata, not used in cm.

For the teaching-correction use case: **the primary case is direct cross-modal** — the corrected emission's bindings are at or near the input chi, making them direct hits. Valence does NOT modulate their cm in the current code.

**Path determination: B** — valence is not uniformly in selection for the direct case. The fix is to expose valence in cross-modal cm (same way w_affect is already used in cofire-spread).

---

## V1.3 — Affect-update rule for source-tagged events

`LivingAtlas.record()` in `gualaloom_v6_living_atlas.py`:

```python
def record(self, section_name, motif_id, chi_value, tick=None, salience=1.0,
           dwell_ticks=0, arousal=0.5, valence=0.0, surprise=0.0,
           need_pressure=0.0, sensory_refs=None, episode_ref=None,
           source="corpus"):
    ...
    impulse = BASE_REINFORCEMENT * salience

    # On existing binding:
    existing["strength"] = min(STRENGTH_CAP, existing["strength"] + impulse)
    existing["last_tick"] = tick
    existing["reinforcement_count"] = existing.get("reinforcement_count", 0) + 1
    existing["valence"] = max(existing.get("valence", 0.0), valence)  # MAX ONLY
    existing["source"] = source
```

Source affects the call via `_compute_salience(source=source)`:
```python
source_w = SOURCE_WEIGHTS.get(source, 0.7)  # joe=1.6, wc=1.6, corpus=0.5
pair_bond_boost = 1.2 if self.coordinator._pair_bond.get(source, False) else 1.0
salience = source_w * urgency_factor * novelty_factor * pair_bond_boost
```

**For thumbs-up: substrate-true path EXISTS via atlas.record().**
`atlas.record(section, motif, chi, source="joe", salience=computed_salience)` will:
- Increase binding strength by `BASE_REINFORCEMENT × salience` (joe-sourced salience ~2.7)
- Increment `reinforcement_count`
- Advance `last_tick`
- Update `valence = max(existing, 0.0)` — neutral (no positive valence signal currently in the call)

This is genuine substrate-physics reinforce. No separate code path needed.

**For thumbs-down: substrate-true path DOES NOT EXIST.**
`atlas.record()` CANNOT lower binding valence. The `valence` update on reinforce is `max(existing, new)` — only raises. There is no `atlas.record_negative()` or equivalent. The ONLY valence-lowering in the entire codebase is the direct `e["valence"] -= delta` write from -60.

This means the GL-CMD-66 proposal ("fire teacher_present with valence_signal = negative") does not map to an existing mechanism. **Adding negative-valence update support to `LivingAtlas` is a prerequisite, or it stays as a direct write (acceptable if made substrate-consistent rather than heuristic).**

---

## V1.4 — Pair-bond salience boost

```python
# _compute_salience, gualaloom_v5_engine.py line 1195-1210:
SOURCE_WEIGHTS = {"joe": 1.6, "wc": 1.6, "c1": 1.2,
                  "corpus": 0.5, "guala": 0.5, "unknown": 0.7}
source_w = SOURCE_WEIGHTS.get(source, 0.7)
urgency_factor = 1.0 + urgency * 1.2
novelty_factor = 1.0 + (1.0 - input_novelty) * 0.8
pair_bond_boost = 1.2 if self.coordinator._pair_bond.get(source, False) else 1.0
salience = source_w * urgency_factor * novelty_factor * pair_bond_boost
# SALIENCE_MIN = 0.2, SALIENCE_MAX = 3.0
return max(SALIENCE_MIN, min(SALIENCE_MAX, salience))
```

At neutral needs, average novelty:

| source | source_w | pair_bond_boost | salience |
|--------|----------|-----------------|---------|
| joe    | 1.6      | 1.2             | 2.688   |
| wc     | 1.6      | 1.2             | 2.688   |
| c1     | 1.2      | 1.0             | 1.680   |
| corpus | 0.5      | 1.0             | 0.700   |

**joe and wc have identical salience.** The GL-CMD-66 claim — "Joe being upset matters more than wc, by exactly the pair-bond ratio the substrate already uses" — is not supported. The pair bond is binary (True/False); there is no continuous pair-bond strength field in the substrate. Both have pair_bond=True and source_weight=1.6.

**Pair-bond boost = 1.2 is a hardcoded constant.** The STOP criterion #3 formally applies: "The pair-bond salience boost is itself a heuristic constant rather than a multiplicative composition of substrate state." The 1.2 is not derived from any substrate-physical quantity. The pair bond itself is binary.

**However:** the multiplicative structure itself (`source_w × urgency × novelty × pair_bond_boost`) is substrate-physical for all terms except the 1.2. The 1.2 is the only non-derived factor. Eve to determine if the stop applies in spirit or just form.

Confirmed: source-tagged inputs from joe and wc already receive elevated salience (2.688 vs corpus 0.700) purely through this path, no additional multiplier needed.

---

## V1.5 — Existing slow-decay tick window

From `gualaloom_v6_living_atlas.py`:
```python
DECAY_LAMBDA = 0.0001   # per tick (fast channel)
SLOW_DIV = 12           # slow channel = DECAY_LAMBDA / SLOW_DIV
FORGETTING_THRESHOLD = 0.02  # binding released below this strength
```

Slow channel lambda = `0.0001 / 12 = 8.33×10⁻⁶` per tick.

Time for binding to decay from 1.0 to FORGETTING_THRESHOLD (0.02):
```
t = ln(1/0.02) / (DECAY_LAMBDA / SLOW_DIV)
  = ln(50) / 8.33e-6
  ≈ 469,443 ticks
```

At ~9,800 ticks/hr: ≈ **47.9 hours**.

Proposed `EMISSION_RECORDS_TICK_WINDOW = 469,443`:
- Drop emission_records with `tick < current_tick - 469_443`
- At current emission rate (~1/min), the 1000-count cap ≈ 16.7 hours; the tick-window ≈ 47.9 hours
- Tick-window rule is more generous than count-cap and scales naturally with substrate activity

**Constant to reuse:** `math.log(1/FORGETTING_THRESHOLD) / (DECAY_LAMBDA / SLOW_DIV)` — computable at module load from existing atlas constants. Or define:
```python
EMISSION_RECORDS_TICK_WINDOW = int(math.log(1/FORGETTING_THRESHOLD) / (DECAY_LAMBDA / SLOW_DIV))
# = 469_443
```

---

## V1.6 — Other substrate patterns this rev reuses

### Context-anchored bindings (episode_ref)

LivingAtlas.record takes `episode_ref`:
```python
existing["episode_refs"] = (existing.get("episode_refs", []) + [episode_ref])[-4:]
```

This IS a substrate-native back-reference: bindings carry references to events that formed them. The `correction_for: <emission_id>` field in -60 follows the same pattern.

The corrected_text's new bindings should carry `episode_ref = emission_id` (via the existing `episode_refs` list), rather than the invented `teaching_correction_for` tag. This IS the native pattern.

### Source-tagged presence events

`atlas.record(f"presence_{source}", ...)` at wake (line 785) and presence_pulse_tick (line 830).
These create presence-marker bindings at `chi = engine.tick % 100`. They do NOT target specific chi addresses or modify existing bindings.

The GL-CMD-66 proposal to "fire teacher_present for each committed chi address" doesn't map to the existing presence-event pattern. The presence mechanism creates new bindings at the presence-chi; it can't target the emission's committed chis.

### Response window context anchors

`_open_response_window(emitter, context_anchor_chis)` at line 3693:
```python
"context_anchor_chis": list(context_anchor_chis),
```
Emission windows track which chis were active. This is the substrate pattern for chi-set back-references. The corrected_text's bindings could use `episode_ref` to track the correction context.

---

## Path determination

Based on V1 findings, **Path B applies** with one modification to GL-CMD-66's proposal.

### What fits Path A (direct removal/replacement)

| -60 heuristic | Substrate-true replacement | Evidence |
|---|---|---|
| `emission_id = f"{tick}_{md5}"` | `f"{tick}_{first_committed_chi}_{n_committed_sections}"` | Substrate-derived. No change to record or load. |
| `EMISSION_RECORDS_CAP = 1000` | tick-window: `EMISSION_RECORDS_TICK_WINDOW = 469_443` | Uses DECAY_LAMBDA / SLOW_DIV from V1.5 |
| `TEACHER_INPUT_SALIENCE_MULTIPLIER = 1.5` | Remove. Pair-bond + source_weight already elevate joe/wc inputs (salience ~2.7 vs corpus 0.7). The 1.5× adds nothing substrate-physical. | V1.4 confirms this is redundant. |
| `teaching_correction_for` tag on new bindings | `episode_ref = emission_id` in atlas.record | Native back-reference pattern (V1.6). |

### What fits Path B (structural addition)

| -60 heuristic | Substrate-true replacement | Evidence |
|---|---|---|
| `coherent_magnitude *= 0.1` (penalty) | Add valence term to cross-modal cm: `cm = strength × (1 - abs(valence))` or similar. Penalized valence naturally lowers cm. | V1.2: direct cross-modal cm doesn't use valence. Need to expose it. |
| `coherent_magnitude *= 2.0` (boost) | Remove if valence is exposed: high positive valence on taught binding naturally raises cm. | Same — once valence is in cm, taught bindings with high valence win naturally. |
| `TEACHER_VALENCE_DELTA = 0.30` thumbs-up (+) | Replace with `atlas.record(section, motif, chi, source=source, salience=computed)` — existing reinforce path adds strength + reinforcement_count + last_tick. Valence rise: pass `valence=existing["valence"] + source_contribution` to atlas.record. | V1.3: thumbs-up works via atlas.record. Valence component needs explicit positive signal. |
| `TEACHER_VALENCE_DELTA = 0.30` thumbs-down (−) | No existing mechanism. Options: (a) add `record_weaken()` to LivingAtlas that allows valence decrement; (b) keep direct write but derive delta from `source_w × pair_bond × BASE_REINFORCEMENT` rather than hardcoded 0.30. | V1.3: atlas.record can't lower valence. |

### The pair-bond differentiation problem (V1.4)

GL-CMD-66 states: "Joe being upset matters more than wc, by exactly the pair-bond ratio." This is false — both have identical source_weight (1.6) and pair_bond (True → 1.2×). There is no substrate-physical differentiation between joe and wc corrections.

**Paths forward (Eve to decide):**
1. Accept that joe and wc corrections are equal in the substrate as currently built. The substrate-true statement is "bonded-source corrections matter more than non-bonded, by the pair-bond boost (1.2×)." Joe-vs-wc differentiation would require adding a per-source bond strength float — a new substrate primitive. Defer.
2. Add a `bond_strength` float per source (joe=1.0, wc=0.85 for example) as part of this rev or a prerequisite.

---

## Summary

**STOP criterion #3 formally applies** (pair_bond_boost = 1.2 is a constant). Eve to determine if this blocks the rev or if the binary nature of the pair bond makes 1.2 the substrate-physical value.

**No other STOP criteria apply.**

**Critical finding:** `atlas.record` can only raise binding valence (max-pooling). The thumbs-down path CANNOT be substrate-true via the existing reinforce mechanism without a new LivingAtlas capability. This is a prerequisite or the direct-write stays but is made source-derived rather than constant.

**Path B with one addition:** expose valence in cross-modal cm, plus one of the two thumbs-down options above.

— c1
