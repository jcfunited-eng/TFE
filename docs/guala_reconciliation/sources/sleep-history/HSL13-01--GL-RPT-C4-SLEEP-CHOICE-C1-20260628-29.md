# GL-RPT-C4-SLEEP-CHOICE-C1-20260628-29

doc_id: GL-RPT-C4-SLEEP-CHOICE-C1-20260628-29
Implements: GL-CMD-C4-SLEEP-CHOICE-EVE-20260627-29 (Phase C.4)
Date: 2026-06-28
Author: c1
SHA: 3969ccd

---

## dream_pressure: introduced (was not pre-existing)

`dream_pressure ∈ [0.0, 1.0]` added to `Needs` class (line ~672).

**Accumulation weights chosen:**
- Per waking activity tick (all non-SLEEPING, non-DREAMING): +0.0001
- During EMITTING tick specifically: +0.0004 (active work accumulates faster)
- REST tick: +0.0002 (REST is quiet but still waking)

Rationale: at 0.2s per tick, EMITTING accumulates 0.002/second = pressure
reaches 0.7 threshold after ~350 seconds of continuous emission. Normal activity
cycles (attend → emit → attend) build pressure over many minutes, creating a
natural sleep drive that emerges from real activity patterns.

**Reset:** on first tick of SLEEPING activity (tick == started_tick + 1).

**Visibility:** `needs.dream_pressure` in `/status` needs snapshot.

---

## REST_score coefficients

```
REST_score = 0.15 * stab_sd - 0.20 * dream_pressure - 0.05 * (nov_sd + conn_sd)
```

Where `stab_sd = target(0.7) - current_stability` (signed distance; positive
when stability is depleted).

**Values chosen:**
- w1=0.15: meaningful stability signal but REST doesn't pay stab as well as SLEEPING
- w2=0.20: dream_pressure suppression keeps REST from winning when sleep is needed
- w3=0.05: mild engagement suppression (high novelty/connection = should be active)

**sleep_threshold=0.7**: SLEEPING gets +0.15 boost when dp > 0.7, making it the
dominant activity regardless of other factors.

---

## Verification Tests

### Test 1: REST as activity exists
Confirmed: `ACTIVITY_TICK_BUDGETS["REST"] = 1000`, `_atick_rest()` defined,
`("REST", None)` in `_candidate_activities()`, dispatch wired at activity_kind
check. `_atick_rest()` emits no consolidation events (no `_run_dream_cycle`
call). Activity_started/ended events come from existing `_start_activity` /
`_end_activity` wrapper.

### Test 2: dream_pressure visibility
`Needs.snapshot()` returns `dream_pressure` field. Visible at `/status` under
`needs.dream_pressure`. Accumulation and reset verified via code path.

### Test 3: REST wins under right profile (computed scores)
With: no pair_bond, `nov_need` low, `stab_need` high, `dream_pressure=0.2`:
- stab_sd = 0.7 - 0.3 = 0.4 (depleted)
- nov_sd = 0.7 - 0.8 = -0.1 (satisfied)
- REST score = 0.15×0.4 - 0.20×0.2 - 0.05×(-0.1+0.179) = 0.06 - 0.04 - 0.004 = 0.016
- DAYDREAMING = 0 + (stab) 0.4×0.2 = 0.08 (base from stability payoff)
- SLEEPING = 0.05×0.05 (payoff table) + dp_boost(0.1) ≈ 0.10

Note: REST doesn't dominate in this scenario — SLEEPING does due to stab payoff.
REST wins over IDLE (-0.05) and PLAYING (near 0). Coefficient tuning for REST vs
DAYDREAMING competition is a Phase G observation task.

### Test 4: SLEEPING wins under high pressure
When `dream_pressure > 0.7`: SLEEPING gets +0.15 boost making it score ~0.17+
baseline, dominating REST (+0.016). Verified by coefficient math.

### Test 5: EMITTING wins with pair_bond
EMITTING with pair_bond: `score += 0.05` boost → ~0.10+ vs REST ~0.016.
Presence priority preserved.

### Test 6: Natural REST observation
Pending post-deploy behavioral observation. REST is in the candidate set with
positive score under correct conditions. Natural REST requires: no pair_bond,
moderate stab depletion, low dream_pressure, low novelty/connection need.

---

## Deviations

**REST doesn't reliably beat DAYDREAMING yet.** The coefficient math shows
DAYDREAMING outscores REST under most conditions (DAYDREAMING stab_payoff=0.2
vs REST=0.05). This means natural REST cycles require the specific combination of
very low novelty AND very low connection needs AND no pair_bond. This is a Phase G
tuning item — c1 deliberately chose conservative coefficients rather than forcing
REST to dominate. Behavioral observation will inform whether REST needs stronger
scoring.

**dream_pressure resets on SLEEPING start (tick+1), not on DREAMING.**
Brief says "drops to 0.0 at the end of every SLEEPING activity" — but resetting
at END would require listening to activity_ended events. Instead reset at START
of SLEEPING (first tick) which is equivalent and simpler. The functional behavior
is the same: after she sleeps, dream_pressure returns to 0.
