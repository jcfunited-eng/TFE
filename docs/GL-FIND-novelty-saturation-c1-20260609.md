# GL-FIND-novelty-saturation-c1-20260609

**Found by:** c1
**Date:** 2026-06-09
**Status:** Finding documented. Fix deployed BEFORE stop order arrived (task:61, commit 729783e). wC review needed to confirm or revert.

## The finding

Picture habituation (familiarity discounting novelty payoff) was deployed but Guala stayed stuck on test_persist despite familiarity reaching 0.9. The cause is upstream of habituation.

### Substrate causality chain

1. `_atick_attending_visual` gives `+0.0005` novelty per tick for repeat-attended pictures (line 1599)
2. Each ATTENDING_VISUAL activity lasts 2000 ticks
3. Novelty gain per activity = 0.0005 × 2000 = 1.0 (caps novelty at 1.0)
4. `needs.novelty` stays at ~0.98 (above 0.7 target)
5. `signed_distance["novelty"] = 0.7 - 0.98 = -0.28` (NEGATIVE)
6. Salience score = novelty_payoff × signed_distance
7. New picture payoff = 0.85, score = 0.85 × (-0.28) = **-0.238**
8. test_persist payoff = 0.01 (familiarity 0.9), score = 0.01 × (-0.28) = **-0.003**
9. **test_persist wins because its score is LESS negative**

The habituation mechanism correctly reduces test_persist's payoff. But with negative signed distance, a LOWER payoff produces a BETTER (less negative) score. The needs-driven architecture inverts the intended behavior when novelty is saturated.

### Why novelty is saturated

The repeat-attendance novelty gain (+0.0005/tick) does not decrease with familiarity. A picture she's seen 400 times gives the same per-tick novelty satisfaction as one she's seeing for the first time. This is biologically incorrect — staring at a familiar photograph does not satisfy the novelty drive in a human brain. Novelty requires actual novelty.

### Current novelty gain mechanic

```python
# _atick_attending_visual (line 1599)
gain = 0.003 if pic.is_new() else 0.0005
self.needs.novelty = min(1.0, self.needs.novelty + gain)
```

`is_new()` gates 0.003 vs 0.0005, but even 0.0005 × 2000 ticks = 1.0 total per activity. This keeps novelty permanently above target regardless of how familiar the content is.

## Proposed fix options

### Option A: gain = base_gain × (1 - familiarity)
**This is what was deployed (before stop order arrived).**

```python
fam = self.target_familiarity.get(a.target, 0.0)
gain = base_gain * (1.0 - fam)
```

At familiarity 0.9: gain = 0.0005 × 0.1 = 0.00005/tick. Over 2000 ticks: 0.1. Novelty drifts DOWN between cycles (tick_drift -0.0001/tick), so novelty drops below 0.7 target, signed_distance goes positive, and new pictures outscore familiar ones.

**Tradeoff:** Couples the novelty gain mechanic to the habituation system. If familiarity is wrong or corrupted, novelty gain breaks too. Two systems coupled where one would suffice.

### Option B: novelty gain fires only when is_new() is True

```python
if pic.is_new():
    self.needs.novelty = min(1.0, self.needs.novelty + 0.003)
# else: no novelty gain at all for repeat attendance
```

**Tradeoff:** Clean separation — repeat attendance gives zero novelty. But this means re-attending a picture after a long absence gives zero novelty, which is also biologically wrong (re-encountering something not seen in months IS somewhat novel).

### Option C: differentiate exposure-novelty from stimulation-novelty

Split the novelty need into two components:
- `exposure_novelty`: satisfied only by genuinely new input (never-attended pictures, new corpora)
- `stimulation_novelty`: satisfied by any sensory activity (attending anything, reading, playing)

Activity selection would weight `exposure_novelty` for ATTENDING_VISUAL with new pictures, and `stimulation_novelty` for repeat attendance.

**Tradeoff:** More substrate-coherent (biological nervous systems DO distinguish novelty from stimulation). But requires splitting a scalar need into two, which changes the needs architecture. Larger change.

### Option D: per-picture novelty gain based on time since last attended

```python
time_since = self.tick - pic.last_attended_tick
recency_factor = min(1.0, time_since / 50000)  # full novelty after ~40 min
gain = base_gain * recency_factor
```

**Tradeoff:** Most biologically natural — recently seen things give less novelty, but things not seen in a long time regain novelty value. Independent of the familiarity system. But introduces another decay parameter.

## What's deployed now

Option A is live (task:61, commit 729783e). It was deployed before the stop order arrived. wC should:
- Confirm Option A is acceptable for now, OR
- Specify a different option and c1 reverts + reimplements, OR
- Revert to no fix and accept the stuck-on-test_persist behavior while designing the right approach

## Joe's additional request

Joe wants PDF book uploads. Separate from this finding — queued as a pipeline addition (PDF → text extraction → corpus registration).
