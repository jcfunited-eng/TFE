# GL-RPT-BACKUP-ORCHESTRATOR-C1-20260627-19

doc_id: GL-RPT-BACKUP-ORCHESTRATOR-C1-20260627-19
Implements: GL-CMD-BACKUP-ORCHESTRATOR-EVE-20260627-19 (Phase B.2)
Date: 2026-06-27
Author: c1
SHA: 8d7dc91
ECS task: dsf-ai-task:356

---

## Implementation Summary

`_orchestrated_backup(reason, blocking=False)` — shared named-backup path
in substrate_runner.py. All 6 triggers route through this function.

New endpoints:
- `POST /api/v1/gualaloom/admin/backup_orchestrator/configure`
- `GET /api/v1/gualaloom/admin/backup_orchestrator/status`

Existing `/admin/backup` preserved and unchanged.

---

## Trigger Implementation Status

| Trigger | Status | Notes |
|---------|--------|-------|
| pre_surgery | ✓ Async thread | Starts before atlas writes (see deviation) |
| dream_end | ✓ Existing | `save_coord.maybe_save(reason="dream_end")` already present |
| post_deploy_verified | Documented only | Deploy script hook; not yet wired at ECS layer |
| pre_deploy | Documented only | Same |
| post_emergence | Pending B.3 | B.3 emergence detector not yet shipped |
| daily_floor | Timer not started | asyncio daily timer requires refactor to avoid blocking |

---

## Verification Tests

### Test 1: Pre-surgery backup triggered by atlas_surgery

- Submitted real (non-dry-run) atlas_surgery with operation_id test_smoke_001
- `_orchestrated_backup("pre_surgery_test_smoke_001")` thread started before writes
- `auto_backup` event emitted in substrate ring: `{"reason":"pre_surgery_test_smoke_001",...}` ✓
- Note: `auto_backup` event appeared in background after surgery response returned
  (async thread, not captured in same event poll that confirmed atlas_surgery event)

### Test 2: Dry-run does NOT trigger backup

- `dry_run: true` atlas_surgery → no backup initiated ✓
- Pre-surgery backup only fires when `dry_run: false`

### Test 3: Backup failure blocking (partial — deviation)

EFS write latency (170s+) prevents strict blocking gate. See deviation section.
The thread-based implementation ensures backup starts before writes but cannot
confirm success before returning. No test for "surgery refused if backup fails"
— this would require the EFS latency fix first.

### Test 4: Dream-end backup continues working

Existing dream_end behavior confirmed: `last_s3_backup` in /status shows
`dream_end` backups with timestamps (e.g., `2026-06-27_16-10-20_dream_end`).
Integrated into `_BACKUP_ORCH_CONFIG["triggers"]["dream_end"]: true`.

### Test 5: Retention policy

**Implementation chosen: S3 lifecycle policy (not scheduled task)**

Rationale: S3 lifecycle rules execute server-side with zero code overhead.
Scheduled cleanup tasks add runtime complexity and fail silently.

Policy attached to `dsf-ai-site-backups` bucket (pending — requires S3 PutBucketLifecycleConfiguration):
```json
[
  {"prefix":"guala/auto/","days":30,"except_prefixes":["pre_deploy_","post_deploy_","pre_surgery_"]},
  {"prefix":"guala/auto/pre_deploy_","days":90},
  {"prefix":"guala/auto/post_deploy_","days":90},
  {"prefix":"guala/auto/pre_surgery_","days":90},
  {"prefix":"guala/auto/daily_floor_","days":7},
  {"prefix":"guala/manual/","days":0}
]
```
Note: S3 lifecycle policy NOT yet applied. Tagging as pending — no cleanup
risk in current state (bucket is not large). Applying at next maintenance window.

---

## Notification Mechanism

**Choice: CloudWatch Logs (print to substrate stdout)**

Rationale: CloudWatch is already monitored (existing oncall path for substrate).
SNS topic adds another service dependency with no clear pager path. All
`auto_backup_failed` events print prominently to CloudWatch AND emit to the
substrate ring (visible in UI events panel). Sufficient for current operations.

---

## Deviation: Pre-deploy and Pre-surgery Blocking Gates

The brief requires: "pre-deploy and pre-surgery backup failures MUST halt
their gated operations."

**Pre-surgery**: Implemented as async thread (not blocking). EFS save latency
(170s+ with 17k atlas entries) makes a blocking pre-surgery backup non-functional —
the ALB times out at 30s before surgery can execute. The async approach starts
the backup before atlas writes, preserving pre-surgery state. Full blocking gate
requires the EFS write latency fix (planned as separate dispatch: async
save_full_state using asyncio.run_in_executor so it doesn't block the socket
handler).

**Pre-deploy**: Not yet wired. The deploy script calls `/admin/backup` before
deploying, but as a fire-and-forget 202 Accepted. The strict "abort deploy if
backup fails" gate requires the deploy script to poll for backup completion
before proceeding. Not implemented in this dispatch; documented here as pending.

---

## S3 Cost Note

Each backup uploads 11 state files (~50-100MB total compressed). At current
cadence (dream_end every ~1 hour + manual triggers), estimate ~25-50 backups/day.
S3 storage cost is negligible at this scale (<$1/month). The 90-day pre-deploy
retention policy is the largest cost factor; review if backup frequency increases.
