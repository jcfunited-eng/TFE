# GL-BRIEF-graded-exogenous-salience-wC-20260610-031

**Author:** wC
**Date:** 2026-06-10
**Responds to:** docs/GL-FIND-test-persist-recapture-c1-20260610.md (commit 3977f12)
**Selected option:** A (refined) — graded exogenous salience
**Status:** Fix brief. c1 implements per the c1 command at the end. Substrate-primitive change → goes through this review before deploy.

---

## What this fixes

After the exogenous override attends a brand-new picture once, the picture
drops out of the override (`times_attended` is no longer 0) and falls back into
the endogenous needs-driven contest. Under novelty saturation
(`needs.novelty > 0.7`, currently 1.0), `sd["novelty"] = 0.7 - needs.novelty`
is negative, which **inverts** the familiarity discount: the most-familiar
picture (test_persist, fam 0.9) scores least-negative (+0.007) and wins every
contest; the least-familiar real photos (fam ~0.2) score most-negative (-0.014)
and never win. c1 traced and confirmed this; numbers in the FIND doc.

## The principle (why this is the override, not a new mechanism)

Last night's exogenous override encoded Joe's principle — "new anything is
novelty, nothing old should beat it" — as a **binary cliff**: `times_attended
== 0` → salience 1.0, everything else → endogenous needs. That cliff is the
bug. Biology's orienting response is not binary; it **decays with
familiarity**. A genuinely novel stimulus captures attention hard. A
merely-less-familiar one pulls proportionally less. A saturated-familiar one
pulls almost nothing. That is a graded curve.

This fix makes the override continuous:

- `times_attended == 0` → 1.0 (unchanged — genuinely-novel first exposure is a
  real reflexive capture spike; keep it).
- already-seen picture → `(1 - familiarity) * base_payoff`, computed
  **independently of the needs sign**.

Visual attention is an exogenous pathway, separate from endogenous homeostatic
drives, and it habituates. This is the same pathway completed, not a new organ.
It is expressible in the three primitive facts: familiarity is cohesion/entropy
on the picture binding; `(1 - familiarity)` is the greed-for-experience pull
toward what hasn't yet cohered. No dict, no rule, no heuristic compensator, no
ML.

## The change

In `dsf_ai_service/v4/gualaloom_v5_engine.py`, `_action_salience` (c1 quoted
lines ~1415-1470). **c1: confirm the exact surrounding code before editing — I
am working from your quoted structure, not a direct read of the file.**

At the point where ATTENDING_VISUAL salience is computed, BEFORE the
needs-driven `score = sd["novelty"] * nov_payoff + ...` line, insert the graded
exogenous path:

```python
if kind == "ATTENDING_VISUAL" and target in self._pictures:
    pic = self._pictures[target]
    # Genuinely-novel first exposure: reflexive orienting capture.
    if pic.times_attended == 0:
        return self.EXOGENOUS_NEW_SALIENCE  # 1.0, unchanged

    # Already-seen: graded exogenous salience. Decays with familiarity,
    # independent of the needs sign. This is the orienting response made
    # continuous (GL-BRIEF-graded-exogenous-salience-wC-20260610-031).
    fam = self.target_familiarity.get(target, 0.0)
    base_payoff = self.ACTIVITY_NOVELTY_PAYOFF["ATTENDING_VISUAL"]  # reuse existing constant, no new literal
    visual_score = (1.0 - fam) * base_payoff

    # Let the endogenous needs path still contribute when novelty is BELOW
    # target (sd positive): take the max so neither pathway is suppressed.
    needs_score = sd["novelty"] * (base_payoff * (1.0 - fam)) \
                  + sd["stability"] * stab_payoff \
                  + sd["connection"] * conn_payoff + 0.01
    return max(visual_score, needs_score)
```

### Implementation notes for c1

1. **Reuse the existing base-payoff constant.** Do not introduce a fresh `0.1`
   literal. The FIND doc references `ACTIVITY_NOVELTY_PAYOFF` (lines 85-89). Use
   whatever the existing ATTENDING_VISUAL base payoff constant is actually
   named. If the name differs from `ACTIVITY_NOVELTY_PAYOFF["ATTENDING_VISUAL"]`,
   use the real one and note it back to wC. No new tunables.
2. **Keep `max(visual_score, needs_score)`.** Under saturation (sd negative),
   `needs_score` is negative and `visual_score` wins. Under non-saturation (sd
   positive, novelty below target), `needs_score` can exceed `visual_score` and
   contributes normally. Graceful in both regimes; no zero-crossing
   discontinuity.
3. **Do not touch** familiarity rates, decay, novelty gain, the override
   constant, or anything in the dream/consolidation path. This is a
   contest-scoring change only.
4. **Do not extend this to non-visual activities.** The graded exogenous
   pathway is specific to picture attention, exactly as the binary override was.

## Expected behavior post-deploy

- A current contest (needs nov=1.0) scores: real photos `(1-0.2)*base ≈ 0.08`,
  test_persist `(1-0.9)*base ≈ 0.01`. Real photos win; test_persist loses but
  still beats IDLE.
- She cycles through the 9 real photos preferentially (least-familiar first).
- As each real photo habituates (fam climbs toward 0.9), its visual_score
  decays toward test_persist's, and eventually all pictures fall below
  needs-driven activity → she returns to reading. Entropy buries test_persist
  with no deletion. **This is the entropy test Joe explicitly chose.**

## Verification (c1 runs after deploy, reports, STOPS)

1. Deploy, capture task ID + commit hash.
2. Dump per-picture salience at one contest tick — confirm a real photo is the
   max, not test_persist.
3. Watch 10-15 minutes of ATTENDING_VISUAL events. Confirm real photos are
   being selected and test_persist is NOT winning.
4. Report which photos got attended and their familiarity movement.
5. STOP. wC evaluates before the Response Binding gate opens.

## Gate status (unchanged)

Response Binding stays BLOCKED until: (1) this fix is deployed and real photos
are winning contests, (2) atlas holds or grows across 2+ dream cycles
(Item 2 observation, in progress).
