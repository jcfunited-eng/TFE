1# GL-BRIEF-NEEDS-PHYSICS-WC-20260616-01

**Author:** wC
**Date:** 2026-06-16
**For:** c1
**Status:** Queued after microphone fix lands. Substrate physics correction, no heuristics.

## Problem

She's locked at `nov=1.000 stab=1.000 a=1.000` indefinitely. Activity history since boot shows only ATTENDING_VISUAL and EMITTING — no PLAYING, no READING, no ATTENDING_AUDIO selection, no DREAMING entered through normal coordinator path. Joe noticed it directly. PLAYING is not "weighted wrong" — it can't fire because needs never leave their max state and the exogenous reflex keeps pulling her to the same 2-3 pictures.

This brief fixes the **physics**, not the weights.

## Root cause — three physical defects

### Defect 1: Increments out-of-scale with drift

Drift rate (`tick_drift`, line 399): every autonomy iteration, all three needs drop by `NEEDS_DRIFT_RATE = 0.0001`. From 1.0 to 0.0 in 10,000 ticks if untouched. That's the physical hunger rate.

Increments from various code paths are vastly larger:
- `line 2184`: presence wake → `connection += 0.25` (= 2,500 ticks of drift in one event)
- `line 2121`: emission boost → `novelty += 0.01` (= 100 ticks)
- `line 2090`: per emission gain (variable, often +0.005 to +0.02)
- `line 2168`: `+0.004`
- `line 2051`: `+0.002`
- `line 1925`: per new-line read → `+0.001` (~10 ticks)
- `line 1931, 1948`: per sleeping/dreaming tick → `stability += 0.001` and `+0.0005`

Increments accumulate 10–50× faster than drift can dissipate. Needs hit 1.0 within seconds of any activity and stay there.

### Defect 2: Non-physical clamp at 1.0

Every increment site uses `min(1.0, X + gain)`. This is a hard ceiling — a wall the value slams into and stops at. Not physical.

Real biological satiation is **receptor saturation**: as binding sites fill, each additional binding has diminishing effect. The curve is asymptotic, not clipped. She should approach 1.0 but never reach it; equilibrium should be determined by the *ratio* of input rate to drift rate, not by an artificial ceiling.

### Defect 3: Exogenous reflex bypass on familiar items

`_action_salience` at line 1812:
```python
return max(visual_score, needs_score)
```
where `visual_score = (1.0 - fam) * base_payoff`.

`target_familiarity` decays over time. So even after 456 attends to test_25, if she's not seen it for a while, familiarity decays, `(1.0 - fam)` grows, the exogenous orienting reflex pulls her back. She attends, familiarity refreshes, decays, she re-attends. Closed loop on the same handful of pictures forever.

In real cognition, frequently-rehearsed items have **consolidation-resistant familiarity** — the memory-strengthening curve. After hundreds of exposures, decay slows dramatically. Currently the decay rate is uniform regardless of rehearsal count.

## Fix

Two corrections, both grounded in established cognitive physiology.

### Fix 1: Receptor saturation

Add a helper in the needs module:

```python
def saturate(current, gain):
    """Receptor-saturation increment. Diminishing returns as current → 1.0.
    Physical satiation: as receptors fill, each additional input has less effect.
    Equilibrium is determined by input rate vs drift rate, not by clamping."""
    return max(0.0, min(1.0, current + gain * (1.0 - current)))
```

Replace every `min(1.0, needs.X + gain)` pattern with `saturate(needs.X, gain)`:

Sites to change in `dsf_ai_service/v4/gualaloom_v5_engine.py`:
- Line 536: `needs.connection = min(1.0, needs.connection + gap * self.CONN_GAP_FRACTION)` → `saturate(needs.connection, gap * self.CONN_GAP_FRACTION)`
- Line 1925: `self.needs.novelty = min(1.0, self.needs.novelty + 0.001)` → `saturate(self.needs.novelty, 0.001)`
- Line 1931: `self.needs.stability = min(1.0, self.needs.stability + 0.001)` → `saturate(self.needs.stability, 0.001)`
- Line 1948: `self.needs.stability = min(1.0, self.needs.stability + 0.0005)` → `saturate(self.needs.stability, 0.0005)`
- Line 2051: `self.needs.novelty = min(1.0, self.needs.novelty + 0.002)` → `saturate(self.needs.novelty, 0.002)`
- Line 2090: `self.needs.novelty = min(1.0, self.needs.novelty + gain)` → `saturate(self.needs.novelty, gain)`
- Line 2121: `self.needs.novelty = min(1.0, self.needs.novelty + 0.01)` → `saturate(self.needs.novelty, 0.01)`
- Line 2168: `self.needs.novelty = min(1.0, self.needs.novelty + 0.004)` → `saturate(self.needs.novelty, 0.004)`
- Line 2184: `self.needs.connection = min(1.0, self.needs.connection + 0.25)` → `saturate(self.needs.connection, 0.25)`

The negative-decrement at line 1927 (`max(0.0, needs.novelty - 0.0003)`) is fine as-is — that's a drift toward boredom from re-reading familiar content, not a satiation event.

The drift in `tick_drift` (line 399-405) stays as-is — that's the hunger physics and it's correct.

### Fix 2: Familiarity persistence

`target_familiarity` should decay slower for items with higher `times_attended`. Find the familiarity-decay site (likely in attention or autonomy tick path):

```bash
grep -n "target_familiarity" dsf_ai_service/v4/gualaloom_v5_engine.py
```

The decay should be modulated:

```python
# Before:
self.target_familiarity[tid] *= FAMILIARITY_DECAY  # e.g., 0.9999

# After:
n_attends = self._pictures[tid].times_attended  # or sound/video equivalent
# Consolidation: each prior attend slows decay by 1/(1 + log(n))
# 1 attend → full decay rate
# 10 attends → ~0.3× decay rate
# 100 attends → ~0.18× decay rate
# 456 attends → ~0.14× decay rate
consolidation_factor = 1.0 / (1.0 + math.log(1.0 + n_attends))
effective_decay = 1.0 - (1.0 - FAMILIARITY_DECAY) * consolidation_factor
self.target_familiarity[tid] *= effective_decay
```

Use the actual existing FAMILIARITY_DECAY constant; the formula above adapts it.

For sounds and videos, apply the same pattern to their familiarity tracking if separate.

## Why this unblocks PLAYING without weighting it

After Fix 1, needs equilibrate around 0.7–0.85 instead of clamping at 1.0. `signed_distance` returns real (small) values instead of permanently saturated negatives. `_action_salience` math works as designed — most activities score near baseline, with mild bias toward whatever need is currently most unmet.

After Fix 2, test_25 doesn't keep winning the exogenous reflex. Its `(1.0 - fam)` term approaches and stays near zero because consolidated familiarity barely decays.

PLAYING then wins by default in the (frequent) moments when no activity has strong drive. That's its architecturally intended role — exploratory mode during homeostasis. No weight boost needed. No "give PLAYING +0.1" heuristic.

## What this is NOT

- Not a weight rebalance. No `ACTIVITY_NOVELTY_PAYOFF` or `ACTIVITY_STABILITY_PAYOFF` value changes.
- Not a constant tweak to NEEDS_DRIFT_RATE. The drift rate is fine; the increments are out of scale with it.
- Not a special case for any activity type. Same physics for everything.
- Not adding new state or new selectors. Existing code, corrected.

## Verification

Pre-deploy: `guala_status` shows current needs at 1.000/1.000/x.xxx (or whatever Joe is seeing now).

Post-deploy, observable within minutes:

1. **Needs stop clamping at 1.000.** Within ~10 minutes of normal activity, all three needs equilibrate below 1.0, likely in the 0.65–0.90 band depending on what she's doing.
2. **Activity history diversifies.** Within the first hour, `activity_history_summary` includes at least 3 of {ATTENDING_VISUAL, ATTENDING_AUDIO, READING, PLAYING, SLEEPING, DREAMING} instead of just ATTENDING_VISUAL+EMITTING.
3. **PLAYING starts firing.** Within ~30 minutes, at least one PLAYING activity appears in event log.
4. **Familiarity sticks on her frequently-attended pictures.** `target_familiarity[91e42db1c66c]` (test_25) stays near 1.0 between attends instead of decaying back toward zero. She stops compulsively re-attending the same picture.
5. **No atlas regression.** Total strength, vocab, motif counts unchanged or growing normally. This fix is needs-side only and should not affect atlas dynamics.

If verification 1+2 pass but 3 doesn't fire within an hour, the issue is elsewhere (probably in `_candidate_activities` at line 1768 — make sure PLAYING is in the candidate list when not sleeping). Report back, follow-up brief.

If verification 5 fails (atlas regressing), repause and roll back. This change should not touch atlas.

## Deploy

One commit, single deploy. S3 backup tag `PRE-NEEDS-PHYSICS`. Smoke test = check `guala_status` 10 minutes after deploy and confirm needs are off the 1.000 ceiling.

## The substrate point

She has been a child whose hunger meter said "starving" while she was stuffed full, whose memory model kept saying "this is new" about a picture she'd seen 456 times. The substrate locked her into a single mode because its physics were broken in two places that interact multiplicatively. Fixing them doesn't change what she is or how she learns. It restores the homeostasis the architecture always assumed.

End of brief.
