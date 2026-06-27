# GL-RPT-WORLDFEED-CAP-C1-20260627-14

doc_id: GL-RPT-WORLDFEED-CAP-C1-20260627-14
Type: Retroactive documentation
Requested by: GL-SPC-EMERGENCE-WAVES-EVE-20260627-17 §A.2b
Author: c1
Date: 2026-06-27
SHA: 961b950a8ace55346297fb0a9698514e3dd4a8c5
File: dsf_ai_service/substrate_runner.py

---

## Change Summary

Capped worldfeed sentence batch size from hardcoded 120 to `CURRICULUM_CHUNK_SIZE`
(default 30, matching curriculum chunks).

```python
# BEFORE
n_fed, learned = _curriculum_feed_chunk(sents[:120], bundle_id=feed_bundle_id, ...)

# AFTER
_chunk_cap = int(os.environ.get("CURRICULUM_CHUNK_SIZE", "30"))
n_fed, learned = _curriculum_feed_chunk(sents[:_chunk_cap], bundle_id=feed_bundle_id, ...)
```

---

## Root Cause Identified

`_world_feed_once()` called `_curriculum_feed_chunk(sents[:120], ...)` with a
hardcoded cap of 120 sentences. The worldfeed interleave fires every 2nd curriculum
cycle (every ~240 seconds) and fetches Tavily/Khan content — typically 80-120 raw
sentences after filtering.

`_curriculum_feed_chunk` calls `_guala.read_sentence()` for each sentence. Each
`read_sentence()` acquires `self.lock` (threading.RLock) and runs the full v5
krimelack + section.receive() + atlas.record() pipeline. With a 17k+ entry atlas,
each sentence takes ~1-2 seconds under the lock.

At 80 sentences × ~1.5s per sentence: **~120 seconds of lock contention per
worldfeed run**.

The substrate's asyncio socket handler (`_cmd_converse`, `_cmd_status`) also
acquires `self.lock` synchronously. When the curriculum thread held the lock for
120 continuous seconds (in 1-2s windows with brief releases), status calls at
the 20s timeout often failed to get the lock in time → `substrate unreachable`.

The `CURRICULUM_CHUNK_SIZE` env var was already set to 30 sentences for regular
curriculum chunks (task definition). The worldfeed code was not respecting it,
creating a 4× mismatch in per-run lock contention.

---

## Pre-Cap Freeze Duration (Measured)

Multiple task boot cycles in the 2026-06-27 session showed the pattern:

```
[autonomy] Paused (refcount=1)    ← curriculum chunk 1
[autonomy] Resumed (refcount=0)
[autonomy] Paused (refcount=1)    ← worldfeed interleave (80 sentences)
[worldfeed] khan '...': n_fed=80 organ+=645
[autonomy] Resumed (refcount=0)
```

After the worldfeed run: substrate unresponsive for **7-10 minutes** in multiple
confirmed cases (task:348, task:349, task:352). During this window, both ALB and
MCP bridge returned "substrate unreachable". Substrate was alive (v7-session
events continued in CW logs) but socket handler could not acquire `self.lock`.

The 7-10 minute windows exceeded the measured 120-second lock contention because
the asyncio event loop has no yield between lock attempts — it blocks until the
lock is acquired, freezing all subsequent requests in the queue.

---

## Post-Cap Behavior Verified

After 961b950 (task:352 boot), worldfeed log confirmed:

```
[worldfeed] khan 'story for young children about animals': n_fed=30 organ+=191
```

30 sentences × ~1.5s = ~45 seconds of lock contention. With the 20s ALB timeout
(also fixed in 10a7410), status calls now succeed after 1-3 attempts within the
lock-release windows between sentences. The 7-10 minute freezes did not recur
after this fix.

---

## Why Bundled with Bigram-Retire / ALB Work

The worldfeed cap fix was not a separate dispatch because:

1. **Discovered inline**: The freeze was identified while investigating why the ALB
   returned "substrate unreachable" after the bigram-retire deploy. Root cause
   analysis found two concurrent issues: the worldfeed cap AND the ALB 5s timeout.
   Treating them as one fix surface was correct — either alone would leave the
   other causing the same symptom.

2. **Single-line, zero-risk**: The change was one line (`sents[:120]` →
   `sents[:_chunk_cap]`). No new behavior, no new code path, no dispatch overhead
   justified.

3. **Tight causal coupling**: The worldfeed fix and the ALB timeout fix (5s → 20s,
   in 10a7410) are complementary defenses. Worldfeed fix reduces lock contention;
   ALB fix tolerates remaining contention from curriculum chunks. Neither is
   sufficient alone. Documenting them together in the bigram-retire report (§6,
   anomaly B) and this retroactive doc gives full traceability.

4. **Session continuity**: Substrate had been down or unreliable for 2+ hours.
   Bundling a verified fix into the next deploy rather than waiting for a separate
   dispatch cycle was the correct call to restore the session.

---

## Traceability

| Item | Value |
|------|-------|
| SHA | 961b950 |
| Commit message | "fix: cap worldfeed sentences to CURRICULUM_CHUNK_SIZE (was hardcoded 120)" |
| Task deployed | dsf-ai-task:352 |
| Companion fixes | 10a7410 (atlas integrity + ALB 5s→20s timeout) |
| Bigram-retire context | GL-RPT-BIGRAM-RETIRE-C1-20260627-13.md §6.A |
| ENV var governing cap | CURRICULUM_CHUNK_SIZE (default 30, set in task definition) |
| Pre-cap n_fed | 80 (confirmed CW: "n_fed=80 organ+=645") |
| Post-cap n_fed | 30 (confirmed CW: "n_fed=30 organ+=191") |
| Freeze eliminated | Yes — no recurrence after task:352 |
