# GL-RPT-INVESTIGATE-S3-BACKUP-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Why last_s3_backup = null despite automatic local saves working

---

## Classification: **Confirmed reason-gate cause.**

`queue_s3()` is gated by a reason list that does not include `"activity_ended"` or `"backstop"`. After the save-hooks fix, all automatic saves fire with those two reasons. Local persistence works; S3 uploads never enqueue.

---

## Evidence 1 — Code at production SHA (3480ddf)

```
$ curl -s ".../3480ddf/dsf_ai_service/save_coordinator.py" | sed -n '43,60p'

    def maybe_save(self, reason="presence_quiet"):
        """Non-blocking save if conditions are right. Returns quickly."""
        with self._lock:
            if not self._should_save(reason):
                return False
            self.last_save_tick = self.guala.tick
            self.last_save_wall = time.monotonic()
        try:
            self.guala.save_full_state(self.state_dir)
            if self.s3_bucket and reason in ("backup", "shutdown",
                                              "dream_end", "presence_quiet"):
                self.queue_s3(self.state_dir, self.guala.tick, reason)
            return True
        except Exception as e:
            log.error("[save] failed: %s", e)
            return False
```

Line 53: `reason in ("backup", "shutdown", "dream_end", "presence_quiet")`. The two reasons that now fire (`"activity_ended"`, `"backstop"`) are absent.

---

## Evidence 2 — CloudWatch logs (zero S3 activity)

```
substrate/substrate/2b002090b0a240739ddbfba850a02838: 0 [s3] events
substrate/substrate/6ac53ff0e6c94954809c18fc5167f7c0: 0 [s3] events
dsf-ai/dsf-ai/6ac53ff0e6c94954809c18fc5167f7c0: 0 [s3] events
dsf-ai/dsf-ai/2b002090b0a240739ddbfba850a02838: 0 [s3] events
```

Zero `[s3]` log lines across ALL container streams for the entire lifetime of task:204. `queue_s3` has never been called. The S3 upload thread is alive but idle (blocked on `self.s3_queue.get()` with an empty queue).

---

## Evidence 3 — S3 thread status

`GUALA_S3_BACKUP_BUCKET` is NOT in the task definition env vars. However, the code defaults to `"dsf-ai-site-backups"` at `substrate_runner.py:1285`:

```python
s3_bucket = os.environ.get("GUALA_S3_BACKUP_BUCKET", "dsf-ai-site-backups")
```

So `s3_bucket` is set, `SaveCoordinator.__init__` started the S3 thread, and the boot log confirms `"Ring consumers started: persistence + S3"`. The thread is alive; nothing is being enqueued to it.

---

## Evidence 4 — S3 backup inventory for today

```
$ aws s3 ls s3://dsf-ai-site-backups/guala/auto/ | grep "2026-06-19"

PRE 2026-06-19_06-20-02_backup/   ← old task (pre-deploy)
PRE 2026-06-19_06-35-52_backup/   ← Eve-3's pre-deploy backup (confirmed)
PRE 2026-06-19_06-37-11_backup/   ← old task shutdown
PRE 2026-06-19_14-25-49_backup/   ← task:203 shutdown save (manual)
```

Eve-3's backup at `06-35-52` exists. No backups from task:204's lifetime (post ~14:50 UTC). Current rollback floor is `14-25-49` (task:203 shutdown save, ~45 minutes old).

---

## Evidence 5 — A/B/C recommendation

**Recommend Option B: rate-limited S3 enqueue.**

Rationale: Option A (every autosave → S3) would produce ~100 backups/day at 11 state files each. S3 storage is cheap but the listing noise is real — `aws s3 ls` becomes a wall of timestamps, and the `_s3_loop` thread would be uploading ~450MB of deep_atlas JSON every 12 minutes (deep_atlas alone is ~200MB compressed). That's ~3.6GB/day of S3 transfer for marginal benefit over Option B.

Option C (separate periodic schedule) adds a second timer to reason about and test. It solves the same problem as B with more moving parts.

Option B adds one check to `queue_s3`: skip if `time.monotonic() - self._last_s3_enqueue < S3_MIN_INTERVAL` (proposed: 600 seconds / 10 minutes). This gives ~6 S3 backups/hour (144/day), each capturing a clean post-save state. Local saves remain frequent (every activity transition + 5-min backstop). S3 backs up at a sustainable rate. One variable, one check, no new scheduler.

The fix is one line in `queue_s3` plus adding `"activity_ended"` and `"backstop"` to the reason gate on line 53. Three lines total.

---

— c1, 2026-06-19
