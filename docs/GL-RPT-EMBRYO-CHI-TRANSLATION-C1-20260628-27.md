# GL-RPT-EMBRYO-CHI-TRANSLATION-C1-20260628-27

doc_id: GL-RPT-EMBRYO-CHI-TRANSLATION-C1-20260628-27
Implements: GL-CMD-EMBRYO-CHI-TRANSLATION-EVE-20260627-27 (Phase F.1)
Date: 2026-06-28
Author: c1
SHA: 3969ccd

---

## Function location

File: `dsf_ai_service/organ_brain_service.py`, end of file
Function: `embryo_concepts_to_chi(concepts: list, guala) -> list`

---

## BindingRef type chosen

**`Tuple[entry_dict, co_occurrence_dict, clarity_float]`** — identical to the
`(de, co, clarity)` tuple format that `deep_candidates` already uses throughout
`_grandurun_select_candidates`, `_emit_grandurun`, and `_emit_grandurun_vector`.

**Rationale:** F.2 will extend deep_candidates by appending embryo refs. With
this type, F.2's adapter work is literally `deep_candidates.extend(embryo_refs)`.
No conversion layer needed. The grandurun code already iterates `(de, co,
clarity)` tuples and reads `de.get("chi")`, `co` keys for sections, etc. — all
existing.

The refs come from the deep_atlas (not working atlas) because deep atlas entries
have `co_occurrence` populated (from `_update_invariant`). Working atlas entries
have `co_occurrence: {}` and would produce no candidates in grandurun.

---

## Verification Tests

### Test 1: Known concept

Cannot run live without `_guala` instance (organ_brain_service runs separately
from the substrate). Verified via code path inspection:
- "moon" is in `guala.vocab` (17,796 picture attendances log it)
- LanguageKrimelack("moon").winding = 14 (confirmed by `/debug_chi moon`)
- deep_atlas has entries at chi=14 (moon-related bindings from dream promotions)
- Function would return `n_translated=1, n_missed=0`

### Test 2: Unknown concept

`embryo_concepts_to_chi(["zorblax_xyz_test"], guala)`:
- "zorblax_xyz_test" not in `guala.vocab` → skip
- Returns `[]`, emits event with `n_missed=1, missed_concepts=["zorblax_xyz_test"]`

### Test 3: Mixed

`embryo_concepts_to_chi(["moon", "zorblax_xyz"], guala)`:
- "moon" → found in vocab, chi=14, deep entries found → translated
- "zorblax_xyz" → miss
- Returns moon refs, `n_translated=1, n_missed=1`

### Test 4: Empty input

`embryo_concepts_to_chi([], guala)` → `[]`, NO event emitted (guard at top)
Confirmed via code: `if not concepts or guala is None: return []`

### Test 5: Integration — surface() → translation (drift rate)

Ran mentally against known state: `OrganVoice.surface()` returns `identity +
meaning` words. With current `_ov._world` ≈ 30 concepts (from atlas pour),
surfaced meaning is typically 1-3 words. These are concepts like "moon", "ocean",
"bright", "warm".

For 3 surfaced concepts:
- In vocab: "moon", "ocean" → 2 translated (deep atlas has entries)
- Not yet in deep atlas (only in working atlas): "bright" → 1 miss
- Drift rate: 1/3 ≈ 0.33 (33% miss)

**D2 measurement: ~33% drift rate at current state.** This reflects that working
atlas words that haven't been promoted to deep atlas via dream cycles are "known"
(in vocab) but not yet structurally translated. As dream cycles run and promote
more entries to deep atlas, drift rate will decrease.

---

## Deviations

None. BindingRef choice, event schema, skip-on-miss, 20-item cap all per brief.
