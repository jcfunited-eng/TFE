# GL-RPT-CHI-BAND-CONSERVATION-SUBSTRATE-TRUE-DEPLOY-C1-20260620-01

Ref: GL-CMD-CHI-BAND-MASS-CONSERVATION-EVE-20260620-70-rev02
Phase: Deploy + Verification
Status: COMPLETE — task:228 serving

---

## DEPLOY CHAIN

| Task | Commit | Description |
|------|--------|-------------|
| :226 | ce1784e + 5bbe689 | Conservation + substrate-true rev 02 (initial) |
| :227 | bd870a1 | Fix: O(n²) blowup in thumbs-up — filter to emission words |
| :228 | 8ce0a92 | Fix: skip non-language sections (sight/sound) in thumbs-up filter |

Final production: **dsf-ai-task:228**, git SHA=8ce0a92

---

## V2 — IDENTITY TRIPLE

| Check | Value |
|-------|-------|
| Identity | cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f |
| Schema | v7.2.0 |
| Vocab | 2822 |
| Load | boot=ok, load_successful_at_boot=true |
| Integrity errors | Atlas refs motif 9076 in verb (has 2451) × 6 — pre-existing, not introduced |

---

## V3 — BEHAVIORAL VERIFICATION

### V3.a — Atlas repair (conservation deploy)
```
[substrate] Atlas repair: {
  'repaired_bands': 26,
  'repaired_bindings': 14838,
  'total_strength_before': 14207.24,
  'total_strength_after': 9693.95,
  'baseline_used': 0.51
}
```
repair_pass() fired at boot, rescaled 14,838 saturated bindings across 26 chi-keys.
**PASS** — repair_pass() ran, confirmed in CloudWatch substrate stream.

### V3.b — Atlas distribution post-repair
Pre-repair (task:224):
```
0.9-1.0: 12721   ← heavily saturated
0.5-0.7:   389
```
Post-repair (task:226 boot):
```
0.9-1.0: 2148   ← saturation broken
0.5-0.7: 9285   ← middle range dominant
0.7-0.9: 1344
```
**PASS** — bimodal saturation collapsed.

### V3.c — Sum conservation (strength delta)
Before: total_strength=9683.96, n_bindings=25089
After 1 converse call + decay: total_strength=9681.47, n_bindings=25135 (delta=-2.49)
**PASS** — delta is slightly negative (decay removes more than new bindings add). Conservation holds.

### V3.d — Teacher correction thumbs-up (substrate-true path)

| Check | Result |
|-------|--------|
| HTTP | 200 ✓ |
| n_affected | 154 (vs 2645 pre-fix — sight section excluded) ✓ |
| Sections | listen/intro/verb/object/subject only (no sight/sound) ✓ |
| Timeout | <1s (O(n²) fix confirmed) ✓ |
| emission_id format | `11392676_9_3` (tick_firstchi_ncommitted) — substrate fingerprint ✓ |

**PASS** — thumbs-up via atlas.record() with word filter working correctly.

### V3.e — Converse emission
response='v four gone', emission_id=11392676_9_3 ✓
Emission pipeline working with valence-modulated cross-modal cm.

---

## BUGS FOUND AND FIXED DURING DEPLOY

### Bug 1: O(n²) thumbs-up timeout (task:226→:227)
**Root cause:** atlas.record() now runs conservation pass (iterates all entries at chi).
Original thumbs-up reinforced ALL bindings in chi neighborhood — no word filter.
With conservation: 3 words × 5 addresses × ~250 bindings × conservation pass = ~1M ops > 30s timeout.

**Fix:** Filter thumbs-up to emission words only (same filter as thumbs-down).
`if not wl or wl.lower() not in _emission_words_set: continue`

### Bug 2: Non-language section fallthrough (task:227→:228)
**Root cause:** Filter `if sec and motif < len(sec.modes):` when sec is None (sight/sound sections
not in self.sections dict) fell through without skipping — all visual bindings reinforced.
Result: n_affected=2645, all sight section.

**Fix:** Add `else: continue` to explicitly skip non-language sections.

---

## WHAT IS IN PRODUCTION (task:228, schema v7.2.0)

### Conservation (GL-CMD-70)
- `LivingAtlas.record()`: captures actual_delta, redistributes to band-neighbors proportionally
- `repair_pass()`: one-time renormalization at boot, BASELINE=0.51
- Ran at task:226 boot: repaired_bands=26, repaired_bindings=14838, strength 14207→9694

### Substrate-true teacher correction rev 02 (GL-CMD-66/70)
- **Cross-modal cm**: `cm = strength * max(0.0, 1.0 + valence)` — valence modulates selection
- **Negative valence floor**: -1.0 (not 0.0) — negative bindings suppressed via cm formula
- **Thumbs-up**: atlas.record() with source-derived salience + positive valence signal
  - Filtered to emission words in language sections only
  - Goes through conservation; reinforcement_count, last_tick via atlas.record()
- **Thumbs-down**: direct write with source-derived delta (BASE_REINFORCEMENT × source_w × pair_bond)
  - joe/wc: delta = 0.05 × 1.6 × 1.2 = 0.096
- **episode_refs back-reference**: replaces teaching_correction_for tag
- **Removed**: TEACHER_VALENCE_DELTA=0.30, TEACHER_INPUT_SALIENCE_MULTIPLIER=1.5
- **Removed**: ×0.1/×2.0 teaching influence block from _rich_sensory_candidates
- **Removed**: teaching_correction/teaching_correction_for fields from candidate dicts
- **EMISSION_RECORDS_TICK_WINDOW=469_443**: slow-decay-derived window replaces count-only cap
- **emission_id**: substrate fingerprint `tick_firstchi_ncommitted` (not md5)

### Known issues (unchanged from prior deploys)
1. /sleep_for_deploy returns 500 — manual force-deploy workaround used for all 3 tasks
2. last_s3_backup always null — cosmetic
3. integrity_errors: Atlas refs motif 9076 in verb (has 2451) — pre-existing cofire_bind OOB

— c1
