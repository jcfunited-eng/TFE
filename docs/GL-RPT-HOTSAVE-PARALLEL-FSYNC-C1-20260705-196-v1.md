# GL-RPT-HOTSAVE-PARALLEL-FSYNC-C1-20260705-196-v1

doc_id: GL-RPT-HOTSAVE-PARALLEL-FSYNC-C1-20260705-196-v1
From: c1 | To: Joe, Eve, whoever picks this up next
Follows: GL-CMD-HOTSAVE-EVICT-VOCAB-SCALED-EVE-20260705-194-v1 (deployed,
SHA 44070af, alongside -195)

## What -194 fixed, and what it didn't

-194 evicted the vocab-scaled `sight_motifs` list from the hot save lane
(was growing forever with vocab, 6-9MB and climbing). Deployed clean,
verified: identity preserved, migration + both restore paths correct,
no regressions.

Post-deploy live [save-hot] timing (10 log lines, `/ecs/dsf-ai`,
stream `2401b6ce4b624ec5b876d9bccc7daff5`, no concurrent camera/mic
frame load at the time):

```
22.54s core=19.61s   (cycle 1 -- one-time guala_sight_motifs.json migration)
19.79s core=17.42s
19.60s core=17.57s
18.01s core=15.73s
 8.31s core=8.26s
18.71s core=16.68s
20.76s core=18.32s
```

Peak dropped from the pre-194 worst of 49s to ~22s, but the <5s
design target (docs/GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v3) was
still not met -- -194's fix was real and necessary, not sufficient.

## Root cause of the remainder

`_atomic_write()` (engine.py, `@staticmethod`) unconditionally
`f.flush()` + `os.fsync(f.fileno())` before every rename --
GL-CMD-PERSIST-FIX-74's fix for a real EFS/NFSv4 bug (close() alone
doesn't commit to the NFS server, so a bare rename can ENOENT). Each
fsync is a genuine network round-trip to the EFS server. `save_hot_state`
writes 8 files sequentially (core/needs/coordinator/bucket/visual/
sounds/videos/teaching) -- 8 sequential round-trips, wall-clock = their
SUM, independent of payload size. This is why times stayed high even
with the large payload gone: a second, previously-masked, non-vocab-
scaled bottleneck was always there underneath it.

## The fix (GL-CMD-HOTSAVE-PARALLEL-FSYNC-196)

Same 8 files, same per-file atomic-write + fsync + rename, same
per-file failure isolation (one file's exception doesn't stop the
others, same critical-vs-report-only distinction) -- now submitted to
a `concurrent.futures.ThreadPoolExecutor` instead of a `for` loop.
fsync/file I/O release the GIL during the actual syscall, so threads
give real parallelism for this I/O-bound work. Wall-clock becomes the
SLOWEST single fsync, not their sum. No change to what gets written,
no change to durability guarantees, no change to failure handling.

Verified offline (real engine, monkeypatched `os.fsync` with a fixed
1.0s artificial delay to stand in for EFS's real per-call network
latency, which a local disk doesn't have): 10 fsync calls, sequential-
would-be ~10.0s, actual wall time 2.03s.

Full `test_cognition_path.py` baseline: same pre-existing 3 failures
(test_t7_cross_modal, test_t8_noise_robustness, test_t11_substrate_true),
no new regressions, both alongside -194 alone and combined with -196.

## Not done here

`save_full_state` (the cold lane, ~11 files, every 30min/sleep boundary)
has the same sequential-fsync pattern and would benefit the same way,
but it isn't in the hot path that stalls live conversation turns --
left alone to keep this change scoped to the problem actually observed.
Candidate follow-up, not urgent.

## Deploy

Same worktree pattern as -194/-195. Full baseline suite clean. Deploying
now; live [save-hot] timing over the next several cycles goes in the
next status check.

### Changelog
- v1 (2026-07-05, c1): root-caused the -194 remainder live, built +
  verified the parallel-fsync fix offline, deploying.
