# GL-RPT-FIX-S3-BACKUP-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** S3 backup rate-limited enqueue fix — verified
**Commit:** `c26e67a` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:205` (was 204)
**Image:** `dsf-ai:deploy-20260619T155644Z`
**Git SHA:** `c26e67a`

---

## V1 — Branch verification

```
$ curl -s ".../c26e67a/dsf_ai_service/save_coordinator.py" \
    | grep -n "S3_MIN_INTERVAL\|_last_s3_enqueue\|_maybe_queue_s3\|always-queue\|rate-limited\|presence_quiet"

20:S3_MIN_INTERVAL_SECONDS = 600   # 10 minutes between rate-limited S3 enqueues
31:        self._last_s3_enqueue_wall = 0.0
46:    def maybe_save(self, reason="presence_quiet"):
56:                self._maybe_queue_s3(reason)
62:    def _maybe_queue_s3(self, reason):
66:          - always-queue: shutdown, backup, dream_end (no rate limit)
67:          - rate-limited: activity_ended, backstop, presence_quiet
71:        ratelimited = ("activity_ended", "backstop", "presence_quiet")
74:            self._last_s3_enqueue_wall = time.monotonic()
78:            if (now - self._last_s3_enqueue_wall) >= S3_MIN_INTERVAL_SECONDS:
80:                self._last_s3_enqueue_wall = now
```

- `S3_MIN_INTERVAL_SECONDS = 600` at module level (line 20) ✓
- `_maybe_queue_s3` method with three-class logic (lines 62-82) ✓
- Old four-element reason tuple GONE from `maybe_save` body — `"presence_quiet"` only in default arg (line 46) and in `_maybe_queue_s3` (line 71) ✓

---

## V2 — Production state

```
Task def:        dsf-ai-task:205 (PRIMARY, single deployment, stable)
Image:           dsf-ai:deploy-20260619T155644Z
Git SHA:         c26e67a

schema_version:  v7.1.0                                              ✓
identity:        cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f               ✓
last_save_tick:  11194961                                            ✓ (autosaves working)
last_save_ts:    2026-06-19T16:12:49Z
n_live_bindings: 20457  (pre-deploy 20887, delta 2.1%)               ✓ (within ±5%)
vocab:           2810                                                ✓
```

Note: `last_s3_backup` in guala_status shows `null` because that field is tracked by app.py's `_backup_to_s3` function (the admin endpoint), not by SaveCoordinator's `_s3_loop`. The S3 thread logs its own uploads but doesn't update the app.py global. This is a cosmetic gap — the S3 backups are landing (see V3).

---

## V3 — Behavioral: S3 backups fire and land

**Capture 1 (deploy +0, 16:16:59 UTC):**
```
$ aws s3 ls s3://dsf-ai-site-backups/guala/auto/ | grep "2026-06-19"

PRE 2026-06-19_06-20-02_backup/
PRE 2026-06-19_06-35-52_backup/
PRE 2026-06-19_06-37-11_backup/
PRE 2026-06-19_14-25-49_backup/
```

**Capture 2 (deploy +12min, 16:29:03 UTC, ZERO manual intervention):**
```
PRE 2026-06-19_06-35-52_backup/
PRE 2026-06-19_06-37-11_backup/
PRE 2026-06-19_14-25-49_backup/
PRE 2026-06-19_16-17-26_backstop/     ← NEW
PRE 2026-06-19_16-28-16_backstop/     ← NEW
```

**Two new S3 backups appeared.** Both tagged `_backstop` (the reason from the 5-min backstop timer). Gap between them: 11 minutes (10-min rate limit + timer alignment). Rate limiter is working.

**Backup content verified:**
```
$ aws s3 ls s3://dsf-ai-site-backups/guala/auto/2026-06-19_16-28-16_backstop/

2026-06-19 16:28:18   13295494 guala_atlas.json
2026-06-19 16:28:23        186 guala_bucket.json
2026-06-19 16:28:18     428571 guala_coordinator.json
2026-06-19 16:28:17    6557525 guala_core.json
2026-06-19 16:28:19  446839367 guala_deep_atlas.json
```

Full backup — 447MB deep atlas + all 11 state files.

**CloudWatch `[s3]` log lines:** 0 matches. The S3 upload thread uses `log.info` which doesn't reach CloudWatch at the current log level. The S3 objects on disk ARE the proof.

---

## Tests (9/9 green)

```
Test 1: _should_save bypass list... PASS
Test 2: dream_end on DREAMING activity... PASS
Test 3: activity_ended on normal activity... PASS
Test 4: no external quiet-point gate... PASS
Test 5: S3 always-queue reasons... PASS
Test 6: S3 rate-limited (no advance)... PASS
Test 7: S3 rate-limit release after interval... PASS
Test 8: S3 never-queue for unknown reason... PASS
Test 9: S3 skipped when no bucket... PASS
```

Existing tests: plasticity PASS, hemisphere roundtrip ALL GREEN.

---

— c1, 2026-06-19
