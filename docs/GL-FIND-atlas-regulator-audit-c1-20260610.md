# GL-FIND-atlas-regulator-audit-c1-20260610

**Found by:** c1
**Date:** 2026-06-10
**Status:** Investigation only. No changes made.

---

## 1. ATLAS DECAY PATH

**Implementation:** `gualaloom_v6_living_atlas.py` class `LivingAtlas`

**Decay function:** `LivingAtlas.decay()` (line 121-136)
```python
e["strength"] *= math.exp(-DECAY_LAMBDA * dt)
```
where `dt = current_tick - e["last_tick"]`.

**Constant:** `DECAY_LAMBDA = 0.0001` per tick (line 41). Was 0.001, reduced 10x in commit `2e4d4fa`.

**Where called — THREE sites, all continuous:**

| Site | File:line | When | Frequency |
|------|-----------|------|-----------|
| During `read_word()` | gualaloom_v5_engine.py:878-879 | Every READING tick | Every 10 ticks |
| During ALL non-reading activities | gualaloom_v5_engine.py:1381-1382 | Every non-reading tick (SLEEPING, DREAMING, PLAYING, ATTENDING_*, EMITTING, IDLE) | Every 10 ticks |
| During SLEEPING specifically | gualaloom_v5_engine.py:1546-1547 | Additional decay during sleep pre-dream | Every 50 ticks |

**Decay is CONTINUOUS.** It runs every 10 ticks regardless of activity. During SLEEPING it runs at BOTH the 10-tick general rate AND the 50-tick sleep-specific rate. During DREAMING it runs at the 10-tick general rate (lines 1381-1382 fire after `_atick_dreaming` returns — same autonomy loop iteration).

**Prune function:** `LivingAtlas.forget_below_threshold()` (line 138-149)
- Removes entries with `strength < FORGETTING_THRESHOLD`
- Called every 200 ticks in the same two sites as decay (lines 881, 1383-1384)

**Key implication:** Decay runs DURING dreaming, simultaneously with dream reinforcement. Each dream artifact (every 200 ticks) reinforces 3-7 entries, but decay runs on ALL entries every 10 ticks. Between dream artifacts (200 ticks apart), decay fires 20 times on every entry. At `DECAY_LAMBDA = 0.0001` and `dt=10` per call, each decay call multiplies strength by `exp(-0.001) ≈ 0.999`. Over 20 calls: `0.999^20 ≈ 0.980`. So ~2% of each entry's strength decays between dream reinforcements.

---

## 2. REINFORCEMENT PATH (dream consolidation)

**Function:** `_atick_dreaming()` at gualaloom_v5_engine.py:1554-1601

**Fires:** Every 200 ticks during DREAMING phase (line 1559: `if self.tick % 200 == 0`)

**Reinforcement call:** `self.atlas.record(sec_name, mid, chi_k, self.tick, salience=0.3)` (line 1577-1578)

**Reinforcement amount:** `BASE_REINFORCEMENT * salience = 0.05 * 0.3 = 0.015` per entry per dream artifact. Capped at `STRENGTH_CAP = 1.0`.

**Entries reinforced per artifact:** 3-7 (observed range from production events). Depends on how many entries exist at the 3 sampled chi keys.

**Sampling rule (CRITICAL):**
```python
chi_keys = list(self.atlas.entries.keys())
sample_chis = [chi_keys[i % len(chi_keys)]
               for i in range(self.tick % max(1, len(chi_keys)),
                              min(self.tick % max(1, len(chi_keys)) + 3, len(chi_keys)))]
```
This is a **tick-modulated sequential window of 3 consecutive chi keys** from the atlas entries dict. It is NOT random, NOT strength-weighted. It walks through the chi-key list deterministically based on `self.tick % len(chi_keys)`.

**Effect:** The same 3 chi keys get sampled every ~`len(chi_keys)` dream artifacts (when the tick modulo wraps around). With ~25-35 chi keys in the atlas, the full atlas gets one pass every ~8-12 dream artifacts. Each dream cycle has ~13 artifacts (2500 ticks / 200 = 12.5). So roughly one full pass per dream cycle — every entry gets reinforced approximately once per dream.

**NOT the test_persist lottery wC suspected.** The sampling is sequential, not strength-weighted. test_persist appeared in dreams because its sight motif bindings happened to occupy chi keys that fell in the sampling window during that cycle's tick offset. The correction (real photos winning waking contests → getting atlas bindings → appearing in dream sampling) worked because the sequential walk now passes through chi keys with real-photo bindings.

---

## 3. NEW-ENTRY BIRTH STRENGTH

When `LivingAtlas.record()` creates a NEW entry (line 111-119):
```python
"strength": min(STRENGTH_CAP, impulse)
```
where `impulse = BASE_REINFORCEMENT * salience = 0.05 * salience`.

| Context | Salience | Birth strength |
|---------|----------|---------------|
| Corpus reading | 0.5 (typical) | 0.025 |
| Pair-bond input | 1.6 | 0.08 |
| Dream reinforcement | 0.3 | 0.015 |
| Visual attendance | 1.2 | 0.06 |
| Sound upload | 1.2 | 0.06 |

New entries are born WEAK. A corpus-read entry starts at 0.025 — just above the prune threshold of 0.02. One missed decay cycle could kill it before it gets reinforced.

---

## 4. PRUNE THRESHOLD

**Constant:** `FORGETTING_THRESHOLD = 0.02` (line 51)

**Function:** `LivingAtlas.forget_below_threshold()` (line 138-149)
```python
survivors = [e for e in self.entries[chi_k]
             if e["strength"] >= FORGETTING_THRESHOLD]
```

**Where called:** Every 200 ticks, same sites as decay (lines 881, 1383-1384).

**Implication:** A new entry born at 0.025 (corpus read) has a margin of only 0.005 above the prune threshold. At `DECAY_LAMBDA = 0.0001`, it takes `dt = ln(0.025/0.02) / 0.0001 ≈ 2231 ticks` (~112 seconds) without reinforcement to decay below threshold and get pruned. That's about one ATTENDING_VISUAL activity cycle (2000 ticks). If the entry isn't re-encountered within ~2 minutes, it dies.

---

## 5. EXISTING NORMALIZATION OR CAP

**Per-entry cap:** `STRENGTH_CAP = 1.0` (line 57). Individual entries cannot exceed 1.0. This is a local cap, not a global one.

**Global normalization:** **NONE.** There is no function, constant, or code path that:
- Measures total atlas strength and scales all entries proportionally
- Limits the number of entries globally
- Redistributes strength from strong entries to weak ones
- Sets a target total strength and adjusts toward it
- Applies any form of synaptic homeostasis / global downscaling

**wC's hypothesis confirmed: there is no governor on total atlas strength.** The system is open-loop — decay pulls everything toward zero, reinforcement pushes sampled entries up, and the balance is determined entirely by the ratio of decay rate to reinforcement rate, with no feedback from the aggregate.

---

## 6. HOOK POINT for global downscale

**Location:** Inside `_atick_dreaming()` at gualaloom_v5_engine.py:1554-1601.

**Exact insertion point:** After line 1601 (the `_log_substrate_event("dream_artifact", ...)` call) and before the function returns. This is the point where:
- All reinforcement for this artifact cycle is complete
- `post_strength` has been measured
- The event has been logged
- The function is about to return to the autonomy loop (which will run decay on the next tick)

**Region:** Lines 1601-1602 (between the log call and the blank line before `_atick_playing`):
```python
            self._log_substrate_event("dream_artifact", ...)
            # ← HOOK POINT: global downscale pass would go here
            #    All reinforcement done, post_strength measured, event logged.
            #    Next tick will run decay. A downscale here would adjust
            #    total strength toward a target BEFORE decay runs again.

    def _atick_playing(self, a):
```

**Alternative hook:** At the DREAM → POST-DREAM transition (when the DREAMING activity budget expires and `_end_activity()` fires). This would run once per dream cycle rather than per-artifact. Location: the activity budget check at line 1389-1391 (`if self.tick >= a.expected_end_tick`), or inside `_end_activity()` with an activity-kind check.

---

## Summary for wC

| Question | Finding |
|----------|---------|
| Decay | Continuous, every 10 ticks, `exp(-0.0001 * dt)`. ALSO runs during dream simultaneously with reinforcement. |
| Reinforcement | Dream: +0.015 per entry, 3-7 entries per artifact, every 200 ticks. Sequential sampling, NOT strength-weighted. |
| Birth strength | 0.015-0.08 depending on salience. Corpus reads: 0.025 (barely above prune). |
| Prune | Below 0.02, every 200 ticks. New corpus entries have ~112s to get reinforced before death. |
| Normalization | **NONE.** No global cap, no target total, no downscaling, no redistribution. Open-loop confirmed. |
| Hook point | After dream artifact reinforcement + logging, before function return. Line 1601-1602 region. |
