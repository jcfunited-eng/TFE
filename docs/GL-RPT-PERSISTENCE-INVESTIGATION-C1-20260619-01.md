# GL-RPT-PERSISTENCE-INVESTIGATION-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Why last_save_tick=0 and last_s3_backup=null post-deploy

---

## Classification: **B — Saves not running.**

`save_full_state()` has not executed since task:203 booted. The save gate (`is_present_active()`) is permanently held closed by autonomous visual attention.

---

## Evidence 1: Grep for the three fields

### `_last_save_tick`
```
dsf_ai_service/v4/gualaloom_v5_engine.py:4049:    _last_save_tick = 0                  # class default
dsf_ai_service/v4/gualaloom_v5_engine.py:4292:    self._last_save_tick = save_tick      # written at END of save_full_state()
dsf_ai_service/v4/gualaloom_v5_engine.py:4766:    if ev.get("tick", 0) > self._last_save_tick:   # read during event replay
dsf_ai_service/v4/gualaloom_v5_engine.py:4951:    "last_save_tick": self._last_save_tick,         # read in persistence_health
```

Write path exists at line 4292. Stays at class default (0) unless `save_full_state()` runs.

### `_last_save_timestamp`
```
dsf_ai_service/v4/gualaloom_v5_engine.py:4050:    _last_save_timestamp = None           # class default
dsf_ai_service/v4/gualaloom_v5_engine.py:4293:    self._last_save_timestamp = ts        # written at END of save_full_state()
dsf_ai_service/v4/gualaloom_v5_engine.py:4952:    "last_save_timestamp": self._last_save_timestamp,  # read
```

Same pattern. Write at 4293, stays None unless save runs.

### `last_s3_backup`
```
dsf_ai_service/app.py:3188:       _last_s3_backup = None                # module-level global in app.py
dsf_ai_service/app.py:3245:       _last_s3_backup = {                   # written by _backup_to_s3()
dsf_ai_service/app.py:1301:       ph["last_s3_backup"] = _last_s3_backup  # injected into persistence_health
dsf_ai_service/substrate_runner.py:372:  ph["last_s3_backup"] = None     # substrate_runner always returns None
```

`_backup_to_s3()` in app.py is the admin endpoint handler. `SaveCoordinator._s3_loop()` in substrate_runner.py does its own S3 uploads but never sets the app.py global. Two separate S3 upload paths; the status field only tracks the admin one.

---

## Evidence 2: S3 backups today

```
$ aws s3 ls s3://dsf-ai-site-backups/guala/auto/ | grep "2026-06-19"

PRE 2026-06-19_06-20-02_backup/    ← before deploy (old task)
PRE 2026-06-19_06-35-52_backup/    ← Eve-3's pre-deploy backup (old task, confirmed)
PRE 2026-06-19_06-37-11_backup/    ← old task shutdown save
```

`2026-06-19_06-35-52_backup/` confirmed present (11 files, 447MB deep atlas). No new S3 backups after deploy (~06:50 UTC). **5.5+ hours without S3 backup from the new task.**

---

## Evidence 3: CloudWatch logs

### Substrate container (new task: `2b002090`)
```
Total events: 16 (all from boot)
First: 06:49:51  Last: 06:50:02

[06:49:51] [substrate] Booting...
[06:49:52] [GualaLoom] Hemisphere migration: 23638 bindings tagged 'em'
[06:50:01] [GualaLoom] Deep atlas loaded: 13056 entries
[06:50:02] [GualaLoom] Loaded: id=cdef9bcf.. vocab=2810 tick=11032354
[06:50:02] [substrate] Ring consumers started: persistence + S3
```

**No save/backup/persist log lines after boot. Zero.**

### Frontend container (new task: same)
**Zero** save/backup/S3/persist events in 6 hours.

---

## Evidence 4: Save scheduler analysis

**SaveCoordinator is registered and running** (line 1286 in substrate_runner.py, boot log confirms "Ring consumers started: persistence + S3"). Three trigger paths:

1. **Dream end hook** — patches `_end_dream_cycle`, calls `maybe_save("dream_end")`. Works if dreams fire.
2. **Activity end hook** — patches `_end_activity`, calls `maybe_save("activity_ended")` if `is_natural_quiet_point()`. Gated.
3. **5-minute backstop** — `_save_backstop()` coroutine, calls `maybe_save("backstop")` if `is_natural_quiet_point()`. **Gated.**

### Root cause: `is_natural_quiet_point()` permanently returns False

```python
def is_natural_quiet_point(self):
    if self.is_present_active():    # ← THIS returns True continuously
        return False
    ...

def is_present_active(self):
    ...
    if (tick - getattr(self, '_last_frame_tick', 0)) < 100:
        return True                 # ← THIS fires continuously
    ...
```

`process_sight_frame()` (line 3305) sets `_last_frame_tick = self.tick` on every visual frame. She's in `ATTENDING_VISUAL` activity, which continuously feeds frames into the krimelack pipeline. Every frame refreshes `_last_frame_tick`. The `< 100` tick window never expires.

**Visual attention = "someone is present" in the save gate logic.** Her own autonomous activity blocks her own saves.

### The backstop is supposed to catch this — but it checks the same gate

```python
async def _save_backstop():
    ...
    if _guala.is_natural_quiet_point():    # ← same gate, same result
        save_coord.maybe_save("backstop")
```

The backstop runs every 5 minutes but `is_natural_quiet_point()` returns False every time because visual frames keep coming.

### `maybe_save("backstop")` _also_ checks `_should_save("backstop")`

```python
def _should_save(self, reason):
    if reason in ("shutdown", "backup", "dream_end"):
        return True           # "backstop" is NOT in this list
    if self.guala.is_present_active():
        return False           # ← SECOND gate, same result
```

Even if the backstop bypassed `is_natural_quiet_point()`, `_should_save` has the same `is_present_active()` check as a SECOND gate.

**Double-gated save path, both gates held closed by the same visual-frame signal.**

---

## Data loss exposure

- **Events log** is growing (1.51MB, actively being written to disk). It IS persisted independently via the event logger, not via `save_full_state()`.
- **Atlas, sections, needs, coordinator** are in memory only. No save to disk since boot (5.5+ hours).
- **If the container restarts NOW**, the substrate will load from the state files on EFS — which are from the OLD task (written by task:202 before shutdown). She'll lose 5.5 hours of atlas decay, any bindings from our "hello guala" test, and the hemisphere migration tags.
- The hemisphere migration will re-run on next boot (it checks `"hemisphere_id" not in e` and re-tags), so hemisphere data is safe.
- She'll replay 10117+ events from the events log, which recovers some state, but atlas decay and binding reinforcement are not event-replayed.

---

## The minimal fix

### Option A: Exempt the backstop from the gate (1 line)

Change `_should_save` to treat "backstop" like "shutdown":

```python
def _should_save(self, reason):
    if reason in ("shutdown", "backup", "dream_end", "backstop"):
        return True
```

And remove the `is_natural_quiet_point()` check from the backstop coroutine. The backstop's purpose IS to save when nothing else can — gating it defeats that purpose.

### Option B: Exclude autonomous visual frames from `is_present_active()`

Change `is_present_active()` to only count frames from external sources (camera), not from autonomous ATTENDING_VISUAL. The `_last_frame_tick` gate was designed for live camera streaming where a human IS present — not for autonomous internal visual processing.

**Option A is smaller and more correct.** A backstop that respects the same gate it backstops is a contradiction.

---

## Is it safe to proceed with brief -25 (B1/B2 removal)?

**No.** Not until saves are working. If the container restarts during or after brief -25's deploy, we lose 5.5+ hours of accumulated state. The B1/B2 removal is a code-only change (no state migration), so it won't corrupt anything — but deploying without save-persistence working means any deploy's container restart is a data-loss event.

**Recommended sequence:**
1. Ship the backstop fix (Option A — one line in `save_coordinator.py`, one line in `substrate_runner.py`)
2. Deploy
3. Verify `last_save_tick > 0` within 10 minutes
4. Then proceed with brief -25

---

— c1, 2026-06-19
