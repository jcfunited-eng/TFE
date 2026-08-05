# GL-RPT-WAVE-DIET-C1-20260702-82

doc_id: GL-RPT-WAVE-DIET-C1-20260702-82
Date: 2026-07-02 (c1 session, task:446)
SHA: 8919f34 | Task: dsf-ai-task:446

---

## What shipped

**GL-CMD-WAVE-DIET-SAVE-UNBLOCK-EVE-20260702-82** — three parts:

**Part A** — WaveAtlas decoupled from 60s save cycle.
Removed inline WaveAtlas dump from `save_full_state`. Added
`_save_wave_atlas(state_dir)` using `_atomic_write` (fsync-disciplined).
Wired into: periodic save every 10th cycle (`save_count%10`), `manual_sleep`,
`snapshot_state`, SIGTERM handler.

**Part B** — Decay parity in `forget_below_threshold`
(`gualaloom_v6_living_atlas.py`). Collects `forgotten_keys` set during
LivingAtlas pruning. Removes matching WaveAtlas bindings via join key
`(section, motif, chi_original)`. Added `admin/compact_wave_atlas` endpoint
for one-time compaction of 990k orphaned bindings.

**Part C** — Event replay EMITTING budget clamp (`gualaloom_v5_engine.py`).
Fixed hardcoded `+2000` to `ACTIVITY_TICK_BUDGETS.get(kind, 2000)`.
EMITTING now gets 100-tick budget from replay instead of 2000 (33-min
lock-hold eliminated).

---

## T-gates

### T2a — last_save_tick advances within 5 min

**SAVE RUNS — REPORTING BUG MASKS IT.**

CloudWatch `/ecs/dsf-ai` verbatim:
```
[save] 729.70s
[save] 397.14s
```

Two periodic saves have completed (no `[save] error:` lines, no
`save_critical_failure` events in CloudWatch). `_guala._last_save_tick` IS
being advanced by `save_full_state` (line 6111).

Root cause of `last_save_tick=0` in `/status`: the status endpoint reads
from `save_coord.last_save_tick` (SaveCoordinator object, app.py:1755), not
from `_guala._last_save_tick`. `_periodic_v6_save` calls
`_guala.save_full_state()` directly (app.py:4116), bypassing
`SaveCoordinator.maybe_save()`. `save_coord.last_save_tick` is never updated
by this path → perpetually 0 in reporting.

The saves themselves are working. **State A: success lines exist → last_save_tick=0 is a REPORTING BUG.**

Save times are 729s and 397s — substantially above the 5-min spec even if
reporting were correct. Remaining bottleneck: `compact_events` on EFS
(fsync-disciplined os.replace on the event log after each save). Event log
size unknown; compaction duration tracks with log size. This is separate from
WaveAtlas (decoupled by -82 Part A).

### T2b — Long-EMITTING lock-hold confirmed cleared

**PASS.**

Activity history at tick 14089779:
```
EMITTING: count=35, total_ticks=3500
```
35 × 100 ticks = 3500 ✓. No 2000-tick EMITTING observed since boot.
Part C fix (ACTIVITY_TICK_BUDGETS.get) confirmed working.

### T2c — First hourly S3 backup fires

**NOT MEASURED.**

`_daily_s3_backup()` sleeps 86400s before first trigger. No hourly S3 trigger
exists — daily only. Manual backup `2026-07-02_13-40-10` present in
`last_s3_backup` field (triggered by guala_backup tool in prior session,
not by the scheduler).

### T7 — WaveAtlas before/after compact_wave_atlas

**NOT MEASURED — compact_wave_atlas endpoint not yet invoked.**

Pre-compaction state (from boot log, task:446):
```
WaveAtlas loaded from disk: 2011 cells, 990527 bindings
```

### T8 — Post-compaction converse total_ms < 45,000

**NOT MEASURED — compaction not run.**

### T9 — LivingAtlas counts untouched by compaction

**NOT MEASURED — compaction not run.**

LivingAtlas at tick 14089779 (pre-compaction reference):
```
atlas: 88 cross-modal / 8292 entries
total_strength: 812.94
n_live_bindings: 7679
n_chi_keys: 179
deep: 3742 entries str=3358.17
```

---

## -81 Step 0 evidence

Owed across two dispatches. CloudWatch `/ecs/dsf-ai` since task:446 boot
(4 hours ago):

No `[save] error:` lines in task:446. Prior task evidence in the -81 report
stands (task:432 verbatim `[Errno 2]` lines). The -82 fix (per-file isolation
+ fsync) eliminated those exceptions — confirmed by absence of error lines
and presence of success lines in task:446.

---

## Issues requiring follow-on dispatch

1. **last_save_tick REPORTING BUG**: `_periodic_v6_save` must update
   `save_coord.last_save_tick` after `_do_save_and_compact` returns, OR the
   status endpoint must read `_guala._last_save_tick` as fallback when
   `save_coord.last_save_tick == 0`. File: app.py:4112-4120 and app.py:1755.

2. **Save duration 729s/397s**: Likely `compact_events` on large EFS event
   log. `_do_save_and_compact` times both operations together (t0 before
   both, dt after both). Needs per-operation timing to isolate.

3. **compact_wave_atlas not invoked**: 990k orphaned bindings still in memory.
   Decay parity hook (Part B) will bound future growth but orphaned bindings
   from pre-82 remain.

---

End.
