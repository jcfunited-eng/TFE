# GL-FIND-test-persist-recapture-c1-20260610

**Found by:** c1
**Date:** 2026-06-10
**Status:** Finding documented. No fix deployed. wC writes fix brief.

## The finding

After the exogenous novelty override attended all 9 new pictures
(each now at times_attended >= 2), test_persist recaptured all
subsequent ATTENDING_VISUAL selections. Familiarity 0.9 on
test_persist, 0.20-0.31 on real photos. test_persist wins every
contest.

## Root cause (same as GL-FIND-novelty-saturation but for the contest)

The salience formula is:

```
score = sd["novelty"] * nov_payoff + sd["stability"] * stab_payoff + sd["connection"] * conn_payoff + 0.01
```

Where `sd["novelty"] = 0.7 - needs.novelty`. When `needs.novelty > 0.7` (which is almost always — currently 1.0), sd is NEGATIVE.

With negative sd, the familiarity discount INVERTS:
- test_persist: fam=0.9 → nov_payoff = 0.1 × 0.1 = 0.01 → score = -0.3 × 0.01 + 0.01 = **+0.007**
- real photo: fam=0.2 → nov_payoff = 0.1 × 0.8 = 0.08 → score = -0.3 × 0.08 + 0.01 = **-0.014**

test_persist's score is positive (+0.007). Real photos are negative (-0.014). test_persist wins by having the LOWEST novelty payoff, which produces the least-negative (actually positive) score.

The habituation system is correctly reducing test_persist's payoff. But the needs-driven scoring inverts the effect when novelty is saturated.

## Per-picture salience at a recent contest (needs: nov=1.0, stab=1.0, conn=0.0)

| Picture | fam | nov_payoff | score |
|---------|-----|-----------|-------|
| test_persist | 0.90 | 0.010 | +0.007 |
| img_2216 | 0.20 | 0.080 | -0.014 |
| ocean | 0.20 | 0.080 | -0.014 |
| color_sky_test | 0.20 | 0.080 | -0.014 |
| (all 8 others) | 0.20 | 0.080 | -0.014 |

Also: IDLE = -0.040, READING = -0.035, SLEEPING = -0.110. test_persist beats everything.

## Tie-break bias

All 9 real pictures score identically (-0.014). Python's stable sort preserves dict insertion order for ties. But this is moot — they never reach the tie-break because test_persist wins outright.

## Is familiarity discount applied in the contest?

YES (line 1446-1447 of gualaloom_v5_engine.py). `nov_payoff = base_payoff * (1.0 - familiarity)`. The discount is correctly computed and correctly applied. The problem is the multiplication by negative signed_distance.

## Fix options

### Option A: Absolute-value familiarity contest

For ATTENDING_VISUAL, compute familiarity score independently of needs:

```python
if kind == "ATTENDING_VISUAL" and target in self._pictures:
    pic = self._pictures[target]
    if pic.times_attended == 0:
        return self.EXOGENOUS_NEW_SALIENCE
    fam = self.target_familiarity.get(target, 0.0)
    # Lower familiarity = higher score, independent of needs
    visual_score = (1.0 - fam) * 0.1  # scale to reasonable range
    return max(visual_score, standard_needs_score)
```

**Tradeoff:** Decouples visual attention from needs entirely. She'd attend pictures even when novelty is saturated. Biologically: visual attention IS somewhat needs-independent (you look at things even when not seeking novelty). But it bypasses the needs architecture for one activity type.

### Option B: Minimum familiarity floor for post-override pictures

After exogenous override fires (times_attended goes from 0 to 1+), set familiarity to a floor that makes the picture competitive:

```python
# In _atick_attending_visual after attendance:
if pic.times_attended == 1:  # just transitioned from new to seen
    self.target_familiarity[target] = 0.05  # very low familiarity
```

**Tradeoff:** Hacky. Sets an arbitrary floor that happens to make the math work under current needs conditions. If needs conditions change, the floor may need re-tuning.

### Option C: Separate visual-salience contest from needs-driven contest

Run two parallel contests:
1. Needs-driven: current system, picks READING/SLEEPING/EMITTING/etc.
2. Visual-salience: among ATTENDING_VISUAL candidates only, pick the least-familiar picture.

Then compare the winners: if visual winner has familiarity < threshold, it wins overall.

**Tradeoff:** Clean separation of visual attention from needs. But adds complexity — two contest mechanisms with a meta-arbitration layer.

### Option D: Invert the signed-distance effect for visual familiarity

When computing ATTENDING_VISUAL salience, use `abs(sd["novelty"])` instead of `sd["novelty"]`:

```python
# For ATTENDING_VISUAL only:
score = abs(sd["novelty"]) * nov_payoff * (1 - familiarity) + baseline
```

**Tradeoff:** Least-familiar picture always gets the highest visual score, regardless of whether novelty is above or below target. This means she attends pictures when she "shouldn't" (novelty above target), but the familiarity ordering is always correct. Biologically defensible: curiosity about less-familiar things is always positive, never punished.

## What's NOT a fix

- Adjusting familiarity rates or decay: The habituation mechanism is working correctly. The familiarity values are right. The problem is how they interact with signed_distance.
- Adjusting novelty gain: The novelty discipline fix was correct for its purpose (reducing novelty pumping). The issue is that novelty stays above target because of reading, and fixing that further would suppress reading-driven learning.
- Adding more pictures: More pictures at the same familiarity would all tie and lose to test_persist equally.

## Files referenced

- `dsf_ai_service/v4/gualaloom_v5_engine.py` lines 1415-1470 (_action_salience)
- Constants: ACTIVITY_NOVELTY_PAYOFF (lines 85-89), NEEDS_TARGET_V7 (line 75)
