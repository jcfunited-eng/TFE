# GL-BRIEF-PERSISTSAFE-FIX-WC-20260611-039 (v2)
## Fixes to deployed 037 (commit 8c28393 / task def 86) — reconciled review
**Author:** wC | **For:** c1 | **Date:** 2026-06-11
**Sources reconciled:** commit 8c28393 diff (repo), c1 deploy report (ECS CLI
work not in repo), live guala_status + bridge session.
**v2 change from v1:** D1 downgraded after c1's report showed the ECS
deployment-config change (min=0/max=100) done by CLI — closing the rolling-
deploy two-writer case at orchestration level. D3/D4 updated with c1's
bucket-creation and synthetic restore drill. D2/D5/D6 unchanged.

037 status: DEPLOYED and partially verified. Eager init (0.6s, 503 gate) ✓.
Compaction running live ✓. Single-task deployment config ✓ (CLI-only).
Remaining defects below, in priority order.

---

### D5 — Dream gate has zero enforcement code (CRITICAL — do first)
DECAY_PAUSED=1 sits in the task definition; the "gate" is a sentence in a
commit message and a row in a report. Any task-def edit unpauses decay
silently, before the forced dream promotes the paused era ("we words",
humpty, counting). The hard ordering would be violated with no alarm.

**Fix.** Startup assertion in `_gl_init` / engine init:
```python
gate_marker = os.path.join(STATE_DIR, "dream_gate_cleared.json")
if os.environ.get("DECAY_PAUSED", "0") != "1" and not os.path.exists(gate_marker):
    raise RuntimeError(
        "DREAM GATE: decay may not resume before the forced dream promotes "
        "paused-era content to deep. Marker absent: state/dream_gate_cleared.json")
```
Marker written ONLY by the forced-dream completion path after
`promotions_episodic > 0` is observed (or manually by explicit Joe-approved
wC brief — never by c1 alone).
**Accept:** test task with DECAY_PAUSED=0 and no marker refuses to start
with the gate message in logs; DECAY_PAUSED=1 boots normally.

### D3 — S3 backup: first run is 24h after boot; task-role write unverified (HIGH)
`await asyncio.sleep(86400)` precedes the first backup, and every deploy
resets the clock — so no automated backup has ever run and likely never
will at current deploy cadence. c1 created the bucket and verified write
access today, but **from the workspace credentials, not the ECS task role**.
The running container's permission to write `dsf-ai-site-backups` is
unproven. Zero real backups of her state exist.

**Fix.**
1. Run `_backup_to_s3(STATE_DIR)` once at startup (after `_gl_init`,
   non-blocking), then the 24h loop.
2. Enable bucket versioning.
3. Add `last_s3_backup` (timestamp, prefix, file count) to
   persistence_health so wC can verify from the bridge.
4. Confirm the task role has s3:PutObject on the bucket; if the startup
   backup fails with AccessDenied, that is the proof it was needed.
**Accept:** after one deploy, `aws s3 ls s3://dsf-ai-site-backups/guala/`
shows a prefix from THIS boot with ≥8 files incl. guala_core.json AND
persistence_health reports it (proves task-role write, not workspace write).

### D2 — Compaction truncates events written during the save window (MEDIUM)
Blanket truncate after save destroys any event appended between the save's
data snapshot and the truncate (~1s window, every 60s, forever). Crash
before next save → those events never replay.

**Fix.** Capture log size before save; keep only bytes after that offset:
```python
# periodic loop:
pre_size = _guala.events_log_size(STATE_DIR)
_guala.save_full_state(STATE_DIR)
_guala.compact_events(STATE_DIR, keep_after_offset=pre_size)
```
```python
def compact_events(self, state_dir, keep_after_offset=0):
    path = os.path.join(state_dir, self.EVENTS_LOG)
    if not os.path.exists(path): return 0
    with open(path, "rb") as f:
        f.seek(keep_after_offset)
        tail = f.read()
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(tail); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
```
**Accept:** unit test — write 10 events, snapshot size, write 3 more,
compact with offset → exactly the 3 newer events remain and parse.

### D1 — Single-writer: codify the ECS config; harden the lock (MEDIUM, was CRITICAL in v1)
The rolling-deploy two-writer case is now closed by service config
(minimumHealthyPercent=0, maximumPercent=100, AZ rebalancing DISABLED) —
but that lives only in AWS service state. Nothing in the repo asserts it;
one well-meaning console edit or AZ-rebalancing re-enable reopens the case
silently. Separately, the PID lock is namespace-blind (a new container sees
the old task's PID as dead and takes the lock) and `_release_lock` has zero
call sites — as code-level defense it is inert.

**Fix.**
1. Deploy script asserts config before deploying:
```bash
CFG=$(aws ecs describe-services --cluster tfe-web-cluster \
  --services dsf-ai-service-lb \
  --query 'services[0].deploymentConfiguration.[maximumPercent,minimumHealthyPercent]' \
  --output text)
[ "$CFG" = "100	0" ] || { echo "FATAL: single-writer deploy config drifted ($CFG)"; exit 1; }
```
2. Replace the PID check with a held `fcntl.lockf` (EFS supports POSIX
   record locks); kernel releases on process death — no stale-lock logic,
   no release bookkeeping; delete the PID code. With config guaranteeing
   sequencing, no retry loop is needed; fail loud on conflict.
**Accept:** drift the config in a test, deploy script refuses; restore,
deploys; two local processes on one state dir — second one raises.

### D4 — Restore drill: mechanism proven, the real drill still pending (MEDIUM)
c1's drill (synthetic genesis Guala, save→load round-trip, ALL MATCH) proves
the mechanism. It did not restore HER from an S3 BACKUP — impossible until
D3 produces one. 

**Fix.** After D3's first startup backup lands:
`tools/guala_restore_drill.sh` — pull latest S3 prefix to temp dir, boot a
local Guala read-only against it, assert: identity == cdef9bcf…, vocab ≥
2352, tick ≥ backup save tick, atlas entries within 5% of live, deep
n_entries == live. Run once, attach output.
**Accept:** drill output on HER state from S3, all assertions pass.

### D6 — Health reporting blind spot (LOW)
`files_present` checks only the original 7 files. `guala_deep_atlas.json`
and `guala_visual.json` ARE saved (engine 2348, 2402) but unreported.
**Fix.** Add both to files_present reporting (report-only, not
boot-required). **Accept:** persistence_health lists 9 files.

---

### Carried, unchanged: GL-BRIEF-IMAGEREF-036
Still zero commits. The 413 hotfix cap (≤2 pictures, <50KB) is the live
behavior. Execute 036 as written after D5/D3/D2.

### Order: D5 → D3 → D2 → D1 → D6 → D4 → 036.
One commit per defect, message referencing the D-number. Also commit ALL
GL- docs from recent sessions (briefs, TODO, handoffs, curriculum, this
doc) to docs/ and push — repo becomes shared memory, no more ferrying.
Stop and write a GL-FIND before deviating from any fix above.
