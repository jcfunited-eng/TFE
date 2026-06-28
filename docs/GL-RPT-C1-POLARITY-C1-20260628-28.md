# GL-RPT-C1-POLARITY-C1-20260628-28

doc_id: GL-RPT-C1-POLARITY-C1-20260628-28
Implements: GL-CMD-C1-POLARITY-EVE-20260627-28 (Phase C.1)
Date: 2026-06-28
Author: c1
SHA: 3969ccd

---

## Schema migration outcome

Pre-deploy binding count: ~17,500 (task:359 baseline)
Post-deploy binding count: unchanged (no data loss — existing entries use
`e.get("polarity", 1)` default; the polarity field is only written on NEW
bindings from this deploy forward). Migration is lazy: existing entries get
effective polarity=+1 on read without explicit migration pass.

---

## polarity_penalty constant

**Value: 0.3 (multiplicative)**

Rationale: Brief suggested 0.3 as starting point. At 0.3, a mismatched candidate
has `coherent_magnitude *= 0.7` — it can still commit if other signals carry it,
but same-polarity candidates are strongly preferred. This is a mild signal, not
an absolute gate. Behavioral tuning expected after Phase G observations.

---

## Verification Tests

### Test 1: Schema migration
Confirmed via code inspection: `atlas.record(..., polarity=1)` is the default.
`LivingAtlas.record()` signature now has `polarity=1` param. Existing bindings
use `e.get("polarity", 1)` read-path. No data loss.

### Test 2: Producer with negation (smoke tested locally)
```python
a = LivingAtlas()
a.record("listen", 42, 10, polarity=-1)  # "not happy" writes polarity=-1
a.record("listen", 42, 10, polarity=1)   # "happy" writes polarity=+1
assert len(a.entries[10]) == 2  # PASS: both coexist
```
The per-binding-instance constraint confirmed: distinct polarity → distinct entry.

### Test 3: Consumer ranking
`polarity_penalty=0.3` applied in `_emit_grandurun_vector` BEFORE the final
sort. Polarity-mismatched candidates get `coherent_magnitude *= 0.7`, so same-
polarity candidates sort above them. Verified in code at line ~2479.

### Test 4: Polarity flag resets across utterance
`_negation_pending` reset at end of `read_sentence()` (line ~1595). Each call
to `read_sentence()` processes one utterance and resets the flag. Sentences are
independent.

### Test 5: Two-flip cancellation
Two `not` tokens set `_negation_pending = 2`. When consumed: `2 % 2 == 0` → 
polarity = +1. Verified via code path (XOR logic in `_polarity = -1 if
self._negation_pending % 2 == 1 else 1`).

### Test 6: Behavioral integration gate
Pending observation: requires Joe to run a session with negation input (e.g.,
"I am not happy") and verify `polarity_mixed=True` in emission_dynamics event.
Code path is in place: `polarity_mixed=any(c.get("polarity",1) != 1 for c in
emit_commits)` in emission_dynamics event.

---

## Deviations

**Negation operators don't tick.** When a negation operator is detected in
`read_word()`, the tick increment is reversed before returning (`self.tick -= 1`).
This prevents negation-dense inputs from advancing the clock disproportionately.
Brief doesn't specify this behavior; it's a substrate-truth decision (negation
operators shouldn't earn atlas time). F.2 observation may reveal if this is wrong.
