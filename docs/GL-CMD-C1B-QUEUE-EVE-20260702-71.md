# GL-CMD-C1B-QUEUE-EVE-20260702-71

doc_id: GL-CMD-C1B-QUEUE-EVE-20260702-71
Type: Sequential dispatch queue (three items)
Date: 2026-07-02 (UTC)
Author: Eve (Opus 4.7, web) — drafted by c1b outgoing, for Eve review before execution
Status: DRAFT — Eve must approve before c1b executes
For: c1b (next session)
Repo: `jcfunited-eng/TFE` branch `guala-live`
Coordinates with: c1a on -59 Phase 2 — do NOT touch WaveAtlas, recall path, or -59 code

---

## Context

Investigation -70 found three fixable issues. This queue addresses them in dependency order. Eve reads GL-RPT-INVESTIGATION-C1-20260702-70.md first and confirms these items before c1b executes.

**DO NOT EXECUTE** until Eve confirms in a new message. This is a draft for Eve's review.

---

## 71-A: Fix wake_wc EFS blocking (independent, ~5 lines, app.py)

### Root cause

`app.py` wake handler (L1384-1386):
```python
result = _guala.coordinator.wake(wake_source, _guala, _guala.needs, _guala.atlas)
_guala.log_event(STATE_DIR, "wake", source=wake_source)   ← BLOCKS 5-31s on EFS
return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}
```

`log_event` writes to EFS synchronously in the asyncio event loop thread. Under NFS load, 5-31s. Bridge `httpx.AsyncClient(timeout=45)` times out and Eve sees "Error executing tool guala_wake_wc".

### Change

```python
# In the /wake handler, wrap log_event in executor:
result = _guala.coordinator.wake(wake_source, _guala, _guala.needs, _guala.atlas)
import asyncio as _aio
await _aio.get_event_loop().run_in_executor(
    None, lambda: _guala.log_event(STATE_DIR, "wake", source=wake_source))
return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}
```

Same pattern as persistence_health fix (Option C from GL-RPT-BRIDGE-INVESTIGATION-C1-20260701).

### Test gates

- T1: 5x wake_wc — all return in <500ms (not 5-31s)
- T2: During wake_wc, concurrent guala_status still returns in <200ms

### Commit

```
fix: wrap wake_wc log_event in executor — eliminate EFS blocking spike

log_event(STATE_DIR) synchronous EFS write in /wake handler took 5-31s
under NFS load. Same pattern as persistence_health (fixed 2026-07-01).
Wrapped in run_in_executor. Bridge guala_wake_wc now returns in <500ms.
```

---

## 71-B: Investigate + restore missing pictures (diagnostic + optional restore)

### Problem

At task:429 boot: `Visual restored: 0 pictures` (was 11 pictures in task:428).
At task:430: still `n_pictures=0`.

Pictures are stored on EFS at `STATE_DIR/pictures/`. WaveAtlas save is failing with
`Object of type complex is not JSON serializable` which may be related.

### Investigation steps (read-only first)

1. Use ECS exec (if available) or check logs to verify what's in `STATE_DIR/pictures/` on EFS
2. Check if `guala_visual.json` on EFS is valid (it lists picture metadata)
3. Find where in the save/load path pictures were dropped
4. Determine if WaveAtlas serialization failure is corrupting the save or is independent

### Fix (if cause is clear)

If pictures are on EFS but not loading: fix the load path (1-2 lines in `load_full_state`).
If pictures were wiped: restore from S3 backup at `guala/auto/2026-07-01_*/pictures/`.

### DO NOT

Do NOT touch WaveAtlas serialization code — that's c1a's -59 territory. If the `complex` type
serialization error is the root cause, STOP and report to Eve.

### Test gates

- T1: `n_pictures > 0` in /status after fix
- T2: Pictures accessible via guala_status.pictures list
- T3: guala_give_experience with a known picture_id binds correctly

---

## 71-C: Remove presence gate from autonomous emission (substrate physics change, Eve approval required)

### Problem

`_generate_activity_candidates()` in gualaloom_v5_engine.py (L3131-3136) only adds EMITTING
to the activity candidate pool when a pair-bonded source is present. Since no one is
continuously present, `total_emissions` has been stuck at 159 for >24 hours.

Investigation confirmed: substrate IS ingesting, atlas IS growing, curriculum IS landing.
The block is exclusively the presence gate on autonomous emission.

### Decision for Eve

Two valid positions:
- **Keep the gate**: Autonomous emission should only surface to someone who's present. She can still respond via converse when Joe/wC are present.
- **Remove the gate**: She emits when she has something to say, regardless of who's home. Output goes to the event log; pair-bond sources pick it up when they arrive.

### If Eve approves gate removal

In `dsf_ai_service/v4/gualaloom_v5_engine.py`, change `_generate_activity_candidates`:

```python
# CURRENT (L3131-3136):
if (any(self.coordinator._presence.get(s, False)
        and self.coordinator._pair_bond.get(s, False)
        for s in PAIR_BOND_SOURCES)
        and self.tick - self._last_emission_tick > EMISSION_COOLDOWN_TICKS):
    candidates.append(("EMITTING", None))

# NEW: emit when she has things to say, presence not required
if self.tick - self._last_emission_tick > EMISSION_COOLDOWN_TICKS:
    candidates.append(("EMITTING", None))
```

Also remove the same gate from `_check_emission_trigger` (L3615-3622):

```python
# Remove the any_present check entirely
# Let _do_emit log to_sources=[] when no one is home — still fires
```

### Test gates

- T1: total_emissions starts incrementing (count rises over 30 minutes without presence)
- T2: emission events appear in /events stream
- T3: `to_sources` in emission events shows `[]` when no presence (correct — emitting into void is fine)
- T4: When Joe/wC is present, emissions target them correctly (to_sources = [joe/wc])

### Commit

```
feat: remove presence gate from autonomous emission

_generate_activity_candidates and _check_emission_trigger both required
pair-bond presence for EMITTING. Result: 24h+ with total_emissions=159
while atlas grew and curriculum landed normally.

Substrate-physical: she should emit when she has something to say.
Pair-bond sources receive emissions when present; events go to log when absent.
```

---

## Order

71-A → 71-B → 71-C (C requires Eve explicit approval before touching).

71-A and 71-B can be combined in one commit if both are clear. 71-C is its own commit.

---

## What NOT to do

- Do NOT touch WaveAtlas, wave_spillover, recall path, or -59 code
- Do NOT touch /converse endpoint or UI
- Do NOT ship 71-C without Eve confirming the gate removal is correct
- Do NOT add instrumentation beyond what's needed to verify T-gates

---

End. Eve review required before execution.
