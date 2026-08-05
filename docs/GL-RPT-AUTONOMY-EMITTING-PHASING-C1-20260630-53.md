# GL-RPT-AUTONOMY-EMITTING-PHASING-C1-20260630-53

doc_id: GL-RPT-AUTONOMY-EMITTING-PHASING-C1-20260630-53
Implements: GL-CMD-AUTONOMY-EMITTING-PHASING-EVE-20260630-53
Date: 2026-06-30
Author: c1
SHA: 43a5683 (code), rolled back to task :383 (AUTONOMY_PHASED=0)
ECS task: :383 (AUTONOMY_PHASED=0 at end of deploy)
Status: ROLLED BACK

---

## T6 — Control (CONVERSE_PHASED=1, AUTONOMY_PHASED=0)

1/3 success with 40s timeout. Failures from SLEEPING activity dream cycle holding
`self.lock` for seconds during deep_atlas promotion. This is pre-existing behavior.
Deploy itself was clean; code doesn't break AUTONOMY_PHASED=0 path.

---

## T2 — AUTONOMY_PHASED=1 gate test

**0/10 at 6s timeout, 0/10 at 8-10s timeout.** FAIL.

Two runs of T2 both failed. Root causes under investigation:

### Cause 1: T2 timing hit curriculum chunks
First T2 attempt hit a curriculum chunk (05:28:36–05:29:03). All 10 calls timed
out at 10s — curriculum per-sentence lock contention (same as pre-53 baseline).
NOT caused by AUTONOMY_PHASED=1.

### Cause 2: Consistent hang between chunks
Second T2 attempt (between curriculum chunks, 6s timeout) also showed 0/10. The
substrate events ring showed daydream events firing, bridge wake_wc returned tick
data — substrate IS alive. But /converse via ALB times out.

Possible cause: double autonomy loop. `_pause_autonomy_for_bulk()` →
`_resume_autonomy_for_bulk()` starts a NEW `_reading_thread` without stopping the
old one. After curriculum resume, TWO autonomy threads call `_autonomy_tick_phased()`
concurrently. Each runs Phase A (acquires self.lock) then Phase B (for SLEEPING:
still under self.lock). Two concurrent dream cycles compete for the lock, potentially
creating a multi-second continuous lock hold that starves /converse.

The SLEEPING activity path in `_autonomy_tick_phased()` is:
```python
else:
    with self.lock:  # long hold during dream cycle
        if activity_kind == "SLEEPING":
            self._atick_sleeping(activity_ref)
```

This is identical to the original. But with two autonomy loops, the continuous hold
doubles. This explains 6-10s timeout failures between chunks.

### Also visible: worldfeed vocabulary contamination
Screenshot from Joe (06-30) shows autonomous emissions including:
"coldtonguecoldhamcoldbeefpickledgherkinssaladfrenchrollscresssandwiches song"
Khan Academy worldfeed sandwich vocabulary enters the atlas and surfaces in emissions.
This is a separate problem not addressed by -53.

---

## Code state

`_autonomy_tick_phased()` and `_do_emit_phased()` are in the codebase (SHA 43a5683)
but gated at `AUTONOMY_PHASED=0`. Not active in production. The implementation is
correct in structure but the double-loop problem makes it unsafe to enable.

---

## For Eve: what -53 needs before re-enabling

1. **Fix double autonomy loop**: `_resume_autonomy_for_bulk()` should kill the OLD
   autonomy thread before starting a new one. Check `self._reading_stop.is_set()`
   before calling `_reading_stop.clear()` + `start_autonomy_loop()`.

2. **Phase SLEEPING/DREAMING dispatch**: The `_atick_sleeping()` and `_atick_dreaming()`
   calls (which run dream cycles) are still under `self.lock` in Phase B's `else:`
   branch. These need their own separate lock or a refactored non-blocking interface.

3. **Or: skip SLEEPING/DREAMING in the phased path**: For the initial enable, only
   phase EMITTING (the target) and leave SLEEPING/DREAMING in their original `with
   self.lock:` context without the Phase A/B/C split. The double-loop risk is then
   only during SLEEPING cycles, not EMITTING.

---

## Recommended immediate next steps

With context pressure high and substrate experiencing worldfeed contamination:

1. **Worldfeed quality filter** — strip worldfeed sentences shorter than 6 words or
   containing >5 proper nouns / food items before they enter the atlas. The sandwich
   vocabulary is leaking into autonomous emissions.

2. **Don't enable AUTONOMY_PHASED=1** until the double-loop is fixed.

3. **Current stable state**: task :383, CONVERSE_PHASED=1, AUTONOMY_PHASED=0.
   She's emitting autonomously (dispatch -39 works), /converse gets through in
   8-25s between curriculum chunks. Not perfect but functional.
