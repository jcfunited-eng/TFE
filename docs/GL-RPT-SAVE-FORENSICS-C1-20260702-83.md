# GL-RPT-SAVE-FORENSICS-C1-20260702-83

doc_id: GL-RPT-SAVE-FORENSICS-C1-20260702-83
Date: 2026-07-02 (c1 session)
SHA: 8919f34 | Task: dsf-ai-task:446
Mode: READ-ONLY — no code changes, no deploys

---

## Step 0 — -82 report

Filed: docs/GL-RPT-WAVE-DIET-C1-20260702-82.md (this session).
All T-gates documented with verbatim evidence or NOT MEASURED as applicable.

---

## Step 1 — Is the save loop running?

**STATE A: success lines exist → last_save_tick=0 is a REPORTING BUG.**

CloudWatch log group `/ecs/dsf-ai`, filtered for `[save]` since task:446
boot (~4 hours ago), verbatim:

```
[save] 729.70s
[save] 397.14s
```

No `[save] error:` lines found.
No `save_critical_failure` or `save_partial` event strings found.

`_periodic_v6_save` (app.py:4122) fires every 60s. It calls
`_do_save_and_compact` (app.py:4112) in an executor. `_do_save_and_compact`
calls `_guala.save_full_state(STATE_DIR)` then
`_guala.compact_events(STATE_DIR, ...)`, then prints `[save] {dt:.2f}s`.
That print only fires when both complete without raising. Both completed.

`_guala._last_save_tick` IS set at engine.py:6111 on critical-file success:
```python
if not _critical_failures:
    self._last_save_tick = save_tick
```
Since no `save_critical_failure` events exist, critical files saved
successfully.

**Root cause of `last_save_tick=0` in status:**

The `/status` endpoint (app.py:1753-1755):
```python
_sc = getattr(_sc_mod, 'SAVE_COORDINATOR', None)
"last_save_tick": getattr(_sc, 'last_save_tick', 0) if _sc else
                   getattr(_guala, '_last_save_tick', 0),
```

`SAVE_COORDINATOR` is set at startup (app.py:1335):
```python
save_coord = SaveCoordinator(g, STATE_DIR, s3_bucket=_s3_bucket)
_sc.SAVE_COORDINATOR = save_coord
```

`save_coord.last_save_tick` is updated ONLY inside
`SaveCoordinator.maybe_save()` (save_coordinator.py:53):
```python
self.last_save_tick = self.guala.tick
```

But `_periodic_v6_save` calls `_guala.save_full_state()` directly, bypassing
`SaveCoordinator.maybe_save()`. So `save_coord.last_save_tick` stays at 0
while `_guala._last_save_tick` advances.

Status reads from `save_coord.last_save_tick` (not from
`_guala._last_save_tick`) because `_sc` is not None — the `else` branch
(which reads `_guala._last_save_tick`) is never taken.

**Fix required (next dispatch):**
Either:
- After `_do_save_and_compact()` in `_periodic_v6_save`, call
  `save_coord.last_save_tick = _guala._last_save_tick` (app.py:~4129); or
- In the status endpoint (app.py:1755), fall back to `_guala._last_save_tick`
  when `_sc.last_save_tick == 0`.

**Save duration note:**
729s and 397s are well above the 5-min spec. `_do_save_and_compact` times
both `save_full_state` AND `compact_events` together (single t0/dt). The
event log on EFS may be large; `compact_events` does an fsync + os.replace
(engine.py:6165-6191). Per-operation timing is needed to isolate which is
slow. This is NOT the reporting bug — it's a separate bottleneck.

---

## Step 2 — Did Part B compaction actually run?

**compact_wave_atlas endpoint was never invoked.** No record of a call to
`/api/v1/gualaloom/admin/compact_wave_atlas` in this session.

WaveAtlas current state (status endpoint, tick 14089779):
- Binding count: 990,527 (unchanged from boot log; no decay parity has fired
  yet to trim orphaned pre-82 bindings)
- Cell count: 2,011 (from boot log)

wave_atlas.json on EFS: NOT checked directly (would require EFS mount or
container exec). Estimated ~198MB from prior analysis (990k binding dicts).
`_save_wave_atlas` has NOT been called in task:446 yet (save_count has not
reached a multiple of 10 — only 2 saves have run).

---

## Step 3 — ATTENDING_VISUAL lock behavior

**Lock is per-tick, NOT per-activity.**

Dispatch path (engine.py:4991-5023):
```python
# Phase B: activity dispatch — EMITTING uses _emission_lock, others use self.lock
if activity_kind == "EMITTING":
    self._do_emit_phased(activity_ref)
...
else:
    with self.lock:                           # ← LINE 5007
        ...
        elif activity_kind == "ATTENDING_VISUAL":
            self._atick_attending_visual(activity_ref)  # ← LINE 5018
```

`self.lock` is a `threading.RLock()` (engine.py:1296). It is acquired once
per tick for the duration of one `_atick_attending_visual` call, then
released. It is NOT held continuously for the 2000-tick activity budget.

`save_full_state` also uses `self.lock` only for the Phase 1 snapshot
(engine.py:5865) — disk writes happen outside the lock (documented at 5862:
"GL-FIX-SAVE-LOCK"). No lock contention between ATTENDING_VISUAL and save.

**Why zero IDLE this boot — design, not bug:**

`_candidate_activities()` (engine.py:4147-4170) always includes IDLE. But
`_action_salience` for ATTENDING_VISUAL_NEW returns `EXOGENOUS_NEW_SALIENCE
= 1.0` (engine.py:4186) for any picture with `times_attended == 0`.

At tick 14089779, status shows 6 pictures with `times_attended=0`:
```
IMG_2137.HEIC     (0263947a7a3d)
Guala Family.HEIC (4eeee4d3d6de)
IMG_1962.HEIC     (0f42a58ae29c)
IMG_2121.HEIC     (71777ea2d543)
IMG_2161.HEIC     (d5cf62b2a66b)
IMG_2216.HEIC     (d6813cb13d4a)
```
Plus IMG_6254.HEIC (currently being attended, will have times_attended=1
after this activity).

IDLE's maximum achievable score with stab=0.000, nov=0.990, conn=0.962:
- `sd["novelty"] × (-0.05) + sd["stability"] × 0.1 + sd["connection"] × (-0.05) + 0.01`
- stability signed_distance ≈ +1.0 (stab=0 → far from target)
- IDLE ≈ 0.1 × 1.0 + 0.01 = ~0.11

ATTENDING_VISUAL_NEW = 1.0 — beats IDLE by ~9×. After all unattended
pictures are consumed, EMITTING (joe present) scores ~0.36 via connection
payoff, still above IDLE. IDLE will remain starved as long as unattended
media exists or a pair-bond source is present. This matches observed
behavior (IDLE count=0 in activity_history_summary).

Implication for saves via SaveCoordinator._end_activity_with_save: the
`activity_ended` trigger only fires for ATTENDING_VISUAL ends (every 2000
ticks × ~0.97s/tick ≈ 32 min per activity). SaveCoordinator._should_save
checks `is_present_active()` (line 98) and rate-limits by 60s wall-clock.
This path is not the primary save route — `_periodic_v6_save` is.

---

## Step 4 — S3 backup path

`_daily_s3_backup()` (app.py:4144-4152):
```python
async def _daily_s3_backup():
    loop = asyncio.get_event_loop()
    while True:
        await asyncio.sleep(86400)       # ← sleeps 24h before first fire
        if _guala is not None:
            await loop.run_in_executor(None, _backup_to_s3, STATE_DIR)
```

**S3 backup does NOT check last_save_tick or save success.** It uploads
whatever files currently exist on EFS at the time it fires. If periodic saves
have run (State A confirmed), the EFS files will be current.

`last_s3_backup = "2026-07-02_13-40-10"` visible in status — this was from
a manual `guala_backup` MCP call earlier in the session (file_count=11
matches the manual backup pattern from earlier reports), NOT from the daily
scheduler.

Daily scheduler will fire ~86400s after task:446 boot. No hourly S3 backup
exists in the codebase.

**Compounding exposure if saves failed**: if `save_full_state` failed and
EFS files were stale, the daily backup would upload stale files. In task:446
saves ARE succeeding (State A), so this is a design observation only — not
an active risk.

---

## Summary for Eve

| Step | State | Finding |
|------|-------|---------|
| Step 1 | **A** | Save loop running. Two saves completed. `last_save_tick=0` is a reporting bug: `_periodic_v6_save` bypasses `SaveCoordinator`, so `save_coord.last_save_tick` stays 0. Fix: update save_coord after periodic save, or read `_guala._last_save_tick` as fallback. |
| Step 2 | N/A | compact_wave_atlas not invoked. 990k bindings unchanged. |
| Step 3 | Info | ATTENDING_VISUAL holds lock per-tick (not per-activity). IDLE starved by design: 6 unattended pictures + joe present → ATTENDING_VISUAL_NEW=1.0 beats IDLE every cycle. |
| Step 4 | Info | Daily S3 backup independent of save success. No hourly trigger. Fires ~24h after boot. Manual backup "2026-07-02_13-40-10" present. |

---

End.
