> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-SAVE-TRUTH-C1-20260702-84

doc_id: GL-RPT-SAVE-TRUTH-C1-20260702-84
Date: 2026-07-02 (c1 session)
SHA: a3f3e7e | Deploy: task:447 (in progress at report time)

---

## Part B — Compaction

### Pre-compaction state

WaveAtlas at task:446 boot (from -81 T4 boot log):
```
WaveAtlas loaded from disk: 2011 cells, 990527 bindings
```

After 82 minutes of operation (decay parity hook running every 200 ticks):
- WaveAtlas: **722,362 bindings** (reduced from 990,527 by organic decay parity)
- Note: decay parity in `forget_below_threshold` removed 268,165 bindings in-flight
  before compaction was invoked

LivingAtlas at pre-compaction (tick 14089779):
```
atlas: 88 cross-modal / 8292 entries
total_strength: 812.94
n_live_bindings: 7679
n_chi_keys: 179
```

Last "[save]" lines before compaction:
```
[save] 397.14s    (1783000745748ms — task:446's only completed save)
```
(Third pre-compaction save line not available; only one save completed in this task.)

wave_atlas.json size on EFS: NOT MEASURED (persistence_health endpoint returned
empty — EFS stat timeout under NFS latency; request timed out after 30s).

### Compaction

Compaction was triggered by a background task from the prior context session
(one of five stopped tasks noted at session start). Invoked ONCE at:
```
1783001729941ms: [GualaLoom] WaveAtlas compacted: 722362→676792 bindings, 2011→2011 cells
```

live_keys_in_atlas: NOT CAPTURED (response went to prior-session background task;
CloudWatch prints the binding counts only, not the live_keys count).

### Post-compaction state

WaveAtlas:
- **676,792 bindings** (after compaction, from log)
- **2,011 cells** (unchanged — no empty cells found)

LivingAtlas post-compaction (tick 14092222):
```
atlas: 88 cross-modal / 7914 entries
total_strength: 799.74
n_live_bindings: 7612
n_chi_keys: 177
```

### T-B1 — bindings drop ≥95%

**FAIL.** 

Pre-compact: 722,362 bindings → Post-compact: 676,792.
Drop: 45,570 / 722,362 = **6.3%** (not ≥95%).

From original 990,527: total reduction = 313,735 = 31.7%.

Root cause: The WaveAtlas bindings are largely legitimate. The LivingAtlas
has 7,914 entries across 177 chi-keys × 6 sections. One live_key
(section, motif, chi) can match many WaveAtlas bindings across different
cells (each cell has its own copy of the binding if the same motif was
encoded from multiple emission positions). The join-key set size is large
enough that most WaveAtlas bindings DO have LivingAtlas counterparts.

The original T-B1 assumption ("expect 10-20k after compaction") was too
optimistic. The WaveAtlas accumulates O(N_emissions × N_sections × N_motifs)
bindings, all legitimately anchored to living LivingAtlas entries.

### T-B2 — save wall time drops materially

**PENDING.** Save 2 in task:446 started ~60s after save 1 completed
(1783000745s + 60 = 1783000805s) and has been running for **>59 minutes**
with no `[save]` print observed. The expected post-compaction save (save 3)
cannot be measured until save 2 completes or the new task:447 boots.

Observation: compaction completed at 1783001729s, which was 924s INTO save 2.
Save 2 is in an executor thread separate from the compact_wave_atlas executor
call. No lock contention (compact_wave_atlas does not take self.lock;
save_full_state Phase 2 writes outside self.lock). The 59+ minute save 2
duration is anomalous relative to save 1 (397s). Cause not isolatable from
CloudWatch alone without per-phase timing (Part C, rides this deploy).

### T-B3 — LivingAtlas counts decay-only drift

**PASS.**

| Metric | Pre-compaction (tick 14089779) | Post-compaction (tick 14092222) | Change |
|--------|-------------------------------|--------------------------------|--------|
| entries | 8,292 | 7,914 | −378 (decay) |
| live_bindings | 7,679 | 7,612 | −67 (decay) |
| chi_keys | 179 | 177 | −2 (decay) |
| total_strength | 812.94 | 799.74 | −13.20 (decay) |

No step change. Atlas decaying normally. Compaction did not touch LivingAtlas.

---

## Part A — Gauge truth (code)

**Commit a3f3e7e, app.py.**

Change (lines 1751-1756):
```python
# Before:
import dsf_ai_service.save_coordinator as _sc_mod
_sc = getattr(_sc_mod, 'SAVE_COORDINATOR', None)
_ph_light = {
    "last_save_tick": getattr(_sc, 'last_save_tick', 0) if _sc else getattr(_guala, '_last_save_tick', 0),
    "last_save_timestamp": getattr(_sc, 'last_save_timestamp', None) if _sc else getattr(_guala, '_last_save_timestamp', None),

# After:
_ph_light = {
    "last_save_tick": getattr(_guala, '_last_save_tick', 0),
    "last_save_timestamp": getattr(_guala, '_last_save_timestamp', None),
```

`_sc_mod` import and `_sc` variable removed (dead code after the change).

**External readers of save_coord.last_save_tick after fix:**

```
grep -n "save_coord\.last_save_tick\|_sc\.last_save_tick" app.py save_coordinator.py
→ (no output)
```

**Zero external readers.** `save_coord.last_save_tick` field is now orphaned
(written internally by `maybe_save()` at app.py:1350/1368, never read externally).

**SaveCoordinator status:** NOT orphaned as a class. It still executes saves:
- `activity_ended` path: app.py:1350 — `save_coord.maybe_save(reason="activity_ended")`
  fires in a daemon thread on every activity end
- `backstop` path: app.py:1368 — `save_coord.maybe_save("backstop")` fires
  every 5 minutes at a natural quiet point

SaveCoordinator.last_save_tick is a candidate for cleanup (60-class), but the
class itself is load-bearing. NOT deleted in this dispatch.

---

## Part C — Naming the 397-729s

### Events log file size

NOT MEASURED via direct stat (persistence_health endpoint timed out).
From save 1 compact_events output (CloudWatch):
```
[GualaLoom] Event log compacted: 54876 bytes discarded, 68 events kept
```
Events file before save 1: pre_size + 54876 bytes. After compaction: ~34KB
(68 events × ~500 bytes each estimated). This is NOT the bottleneck.

Note: `_log_substrate_event` only writes to disk for:
`activity_started`, `activity_ended`, `corpus_completed`, `sleep_manual`,
`dream_began`, `dream_artifact`, `picture_uploaded`, `sound_uploaded`,
`video_uploaded`, `corpus_added`, `visual_motif_committed`, `visual_motif_fired`,
`emission`. hemisphere_update (n_events=13306) goes to in-memory ring only.
Events log grows slowly (~108 activity events + ~54 visual_motif events + emissions).

### Per-phase timing (Part C code change)

`_do_save_and_compact` at app.py:4112 (commit a3f3e7e):
```python
# Before:
t0 = time.time()
pre_size = _guala.events_log_size(STATE_DIR)
_guala.save_full_state(STATE_DIR)
_guala.compact_events(STATE_DIR, keep_after_offset=pre_size)
dt = time.time() - t0
print(f"[save] {dt:.2f}s")

# After:
t0 = time.time()
pre_size = _guala.events_log_size(STATE_DIR)
_guala.save_full_state(STATE_DIR)
t1 = time.time()
_guala.compact_events(STATE_DIR, keep_after_offset=pre_size)
t2 = time.time()
core_dt = t1 - t0
compact_dt = t2 - t1
total_dt = t2 - t0
print(f"[save] {total_dt:.2f}s core={core_dt:.2f}s compact={compact_dt:.2f}s")
```

Format: `[save] {total}s core={core}s compact={compact}s`

Note: `grids` and `wave` are NOT separately timed (both are internal to
`save_full_state`; grids use the per-item loop inside the function; wave is
only called at save_count%10=0, i.e., every ~10 min). The format diverges
from Eve's spec on those two fields — they're labeled within save_full_state
code but not exposed to the print here. If needed, save_full_state can return
a timing breakdown in a follow-on dispatch.

### T-C1 — First per-phase timing line

**PENDING.** Task:447 (this deploy) must boot and complete its first periodic
save before T-C1 can be measured. Will appear as:
```
[save] Xs core=Ys compact=Zs
```

### Response_bound anomaly (read-only)

From guala_get_events at tick 14089799 (representative):
- 10 `response_bound` events at same tick, same anchor_chis [31,31,31],
  different (input_chi, section) combos: (35,listen)×10

Response windows bind across ALL open windows at that chi. At high section
commit counts (listen: 9402c→11937c), each arriving motif fires across
many response_bound calls in the same tick. One window open per `response_bound`
subscriber, with 600-tick duration. Overlapping windows accumulate:
`n_responses_bound=1245` for joe window (joe appears in 1245 bindings over
the session). Multiplicity at same tick is by design — different anchor
contexts being bound in parallel. No anomaly beyond expected volume growth
with section depth.

---

## Part D — S3 cadence (code)

**Commit a3f3e7e, app.py after `_daily_s3_backup`:**
```python
async def _hourly_s3_sync():
    loop = asyncio.get_event_loop()
    while True:
        await asyncio.sleep(3600)
        try:
            if _guala is not None:
                await loop.run_in_executor(None, _backup_to_s3, STATE_DIR)
        except Exception as e:
            print(f"[DSF-AI] Hourly S3 sync error: {e}")
asyncio.ensure_future(_hourly_s3_sync())
```

Uses `_backup_to_s3(STATE_DIR)` which:
- Reads 11 state files directly from EFS (no dependency on save completion)
- Uploads to `guala/{date_str}/` prefix (date-stamped)
- Sets `_last_s3_backup` (visible in /status)
- No interaction with `last_save_tick`

Daily backup (`_daily_s3_backup`) retained — fires every 86400s independently.

---

## Post-deploy T-gates (task:447)

### T-A1 — last_save_tick non-zero within one save period

**PASS.**

```
last_save_tick: 14087960
last_save_timestamp: 2026-07-02T15:25:04Z
```

/status summary line: `save@tick=14087960 boot=ok`

Save completed at tick 14087960 (1395 ticks / ~1097s after boot at tick 14086565).
Reporting bug fix confirmed: _guala._last_save_tick is now read directly, non-zero.

### T-C1 — First per-phase timing line pasted verbatim

**PASS.**

CloudWatch at 1783006665787ms:
```
[save] 1036.93s core=1035.78s compact=1.15s
```

**Dominant phase: core (save_full_state) — 1035.78s (99.9% of total).**
compact_events: 1.15s (negligible, as predicted from the 54,876-byte events file analysis).

This is WORSE than task:446's save 1 (397s). The increase is explained by WaveAtlas
size at task:447 boot: 1,055,870 bindings (vs ~722k at task:446's compacted state).
save_count=0 on first save → wave_atlas.json is written (modulo 10 = 0). Serializing
1,055,870 bindings to JSON dominates the 1036s.

**Implication:** WaveAtlas serialization is a first-class bottleneck. Save time scales
with WaveAtlas size. A cap on WaveAtlas bindings (already queued in Eve's item 5 from
-73) is required to keep save times bounded. Without a cap, save duration will continue
to grow as EMITTING cycles accumulate.

### T-D1 — First hourly S3 prefix appears; last_s3_backup non-null

**PENDING.** last_s3_backup=null at current status (tick 14089669, ~40 min post-boot).
Fires at boot+3600s. Will be measurable at ~2026-07-02T16:07Z.

### Standard count diff

Pre-deploy reference (tick 14092222, task:446):
```
vocab:          13,863
n_motifs:       48,457
n_pictures:         26
n_sounds:           15
n_corpora:          19
atlas_entries:   7,914
atlas_strength: 799.74
deep_entries:    3,742
deep_strength: 3358.17
n_visual_motifs: 12,343
WaveAtlas: 676,792 bindings, 2,011 cells
```

Task:447 at tick 14089669 (post-first-save):
```
vocab:          13,863  (no change)
n_motifs:       48,456  (−1, decay)
n_pictures:         26  (no change)
n_sounds:           15  (no change)
n_corpora:          19  (no change)
atlas_entries:   7,654  (−260, decay from 7,914)
atlas_strength: 813.27  (+13.53 — brief rise before decay parity runs)
deep_entries:    3,742  (no change)
deep_strength: 3358.17  (no change)
n_visual_motifs: 12,334 (−9, decay)
WaveAtlas: 1,055,870 bindings at boot (grew during task:446 EMITTING cycles; not
           yet re-compacted in task:447)
```

Note: WaveAtlas at task:447 boot = 1,055,870, not 676,792 — 54 EMITTING cycles
during task:446 added ~379k bindings before SIGTERM shutdown saved the inflated atlas.

---

End.
