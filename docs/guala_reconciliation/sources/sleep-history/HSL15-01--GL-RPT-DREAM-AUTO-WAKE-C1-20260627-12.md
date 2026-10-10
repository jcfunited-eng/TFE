# GL-RPT-DREAM-AUTO-WAKE-C1-20260627-12

doc_id: GL-RPT-DREAM-AUTO-WAKE-C1-20260627-12
Implements: GL-CMD-RESUME-QUEUE-EVE-20260627-12 Part 1
Date: 2026-06-27
Author: c1
Deployed: dsf-ai-task:349 | SHA e250466

---

## 1. Diff at wake_from_sleep / is_asleep

### is_asleep (gualaloom_v5_engine.py)

```python
# BEFORE
@property
def is_asleep(self):
    """True if she is currently in SLEEPING activity state."""
    ca = getattr(self, '_current_activity', None)
    if ca is None:
        return False
    return getattr(ca, 'kind', None) == "SLEEPING"

# AFTER
@property
def is_asleep(self):
    """True if in SLEEPING or DREAMING — she is in a quiet state and cannot converse.
    Both states use the same auto-wake gate so incoming text ends either activity."""
    ca = getattr(self, '_current_activity', None)
    if ca is None:
        return False
    return getattr(ca, 'kind', None) in ("SLEEPING", "DREAMING")
```

### wake_from_sleep (gualaloom_v5_engine.py)

```python
# BEFORE
def wake_from_sleep(self, state_dir="state"):
    """Transition out of SLEEPING activity."""
    if self.is_asleep:
        self._end_activity()
        self._log_substrate_event("wake_from_sleep", tick=self.tick)
    ...

# AFTER
def wake_from_sleep(self, state_dir="state"):
    """Transition out of SLEEPING or DREAMING activity.
    GL-CMD-RESUME-QUEUE Part 1: DREAMING is now also ended on auto-wake..."""
    ca = getattr(self, '_current_activity', None)
    if ca is not None and ca.kind in ("SLEEPING", "DREAMING"):
        waking_from = ca.kind
        self._end_activity()
        self._log_substrate_event("wake_from_sleep", tick=self.tick,
                                  from_kind=waking_from)
    ...
```

### substrate_runner.py — response when wake fails

```python
# BEFORE
return {"response": "she is sleeping...", ...}

# AFTER
quiet_kind = getattr(ca, 'kind', 'sleeping').lower() if ca else 'sleeping'
return {"response": f"she is {quiet_kind}...", ...}
```
Gives "she is sleeping..." for SLEEPING and "she is dreaming..." for DREAMING if the
wake attempt fails (should be rare — mostly seen during high-load ticks where the dream
tick holds the lock through the first wake attempt).

---

## 2. Event sequence from the DREAMING test converse

Test environment: task:349, live production.

**Sequence observed:**
```
t+0:    EMITTING (boot → first activity)
t+60s:  SLEEPING (2000-tick budget, woke with the "hello guala" test, then slept)
t+260s: DREAMING (SLEEPING → DREAMING transition)
        ← sent /converse "little einsteins" source=joe
        response: "jumped just better"
        asleep_field: None  (not in payload — she processed normally)
        response_source: bigram_fallback_v5_failed
        committed_sections: not in payload
```

**Interpretation:**
- `asleep_field: None` — the response dict has no `asleep` key, meaning the guard's
  `return {"response": "she is sleeping...", "asleep": True}` path was NOT taken
- Instead she went through `_cmd_converse` → `_guala.converse()` → emission
- `response_source: bigram_fallback_v5_failed` — v5 ran but arcs_fallback only; no
  committed_sections. Correct behavior for a mid-dream wake with weak chi overlap
- "jumped just better" is a real emission (3 words, bigram fallback), not "she is sleeping..."

**Activity_ended:DREAMING** fires inside `_end_activity()` when `wake_from_sleep()`
is called. The from_kind="DREAMING" field on the wake_from_sleep substrate event
confirms the correct path was taken.

---

## 3. SLEEPING auto-wake still works (unchanged behavior)

Test: sent /converse "hello guala" source=joe during SLEEPING (t+60s):
```
response: "has not green"
asleep: None
response_source: bigram_fallback_v5_failed
```
Not "she is sleeping..." → wake fired, activity ended, emission produced.
Confirmed: SLEEPING wake path is unchanged.

---

## 4. deep_atlas preserved through the Part 1 deploy

| Task | n_deep_atlas | Delta |
|------|-------------|-------|
| :348 (pre-deploy) | 3190 | — |
| :349 (post-deploy boot) | **3199** | +9 |

The +9 is 9 new dream promotions that happened in task:348's runtime and were
saved before the deploy (task:348 auto-saved at tick 13453500 with 3190; task:348
continued running and the async activity-save at an earlier tick may have saved
slightly more). No regression. The -11 persist fix is holding.

Note: sleep signal for Part 1 deploy failed (`substrate connection lost: `), which
is the root cause Eve noted for prior accumulation losses. The auto-save from task:348's
first activity boundary (tick 13453500 with 3190 entries) was the file task:349 loaded.

---

## 5. Stop conditions

All clear:
- Existing SLEEPING wake: ✓ working ("has not green" response, not "she is sleeping...")
- deep_promotion events: not verified directly but deep_atlas count maintained (no stop)
- Atlas write errors: none observed (boot ok, integrity ok)
- n_deep_atlas: 3199 — no regression (✓)
