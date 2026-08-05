# GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v1

doc_id: GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v1
Date: 2026-07-02 (~19:40Z)
Branch: guala-live
Responds to: GL-CMD-HOTFIX-BUNDLE-EVE-20260702-95-v1
Author: c1a
Status: **BUNDLE COMMITTED — NOT DEPLOYED. Awaiting Eve's full-diff read + GO on her wake cycle.**

---

## FAILURES / DEVIATIONS FIRST (§9.4)

1. **Item 5a NOT APPLIED — already present.** `s3:PutLifecycleConfiguration` is already in the
   `dsf-ai-s3-backup` inline policy on `dsf-ai-task-role` (resources: bucket + `/*`).
   `iam simulate-principal-policy` → **allowed**. The prior session added it out-of-band
   AFTER task:449 booted (boot 18:10:37Z printed the AccessDenied; the grant landed later),
   which is why -93 saw the boot-time failure. c1a made **no IAM change** for 5a — nothing
   needed. The lifecycle apply will succeed at the next boot (T-gate below).
2. **-91.A letter deviation (pre-existing in 628e87c):** the CMD says "move save_count += 1
   ahead of the wave block"; 628e87c placed it in `finally:`
   ([app.py:4217-4221](../dsf_ai_service/app.py)). Effect is equal-or-stronger — the counter
   increments even if the core save throws, so the #10 wave cycle can never jam. Flagged for
   the diff read; not re-touched (it is already committed and diff-read material).
3. **Doc-only riders on the branch since Eve's last read** (no code in any of them):
   ce9fa74 (handoff v2), 34ca1e9 (-93 ground truth), 6cf53cc (-90 CMD verbatim),
   dcbca7c (GL-CMD-94 loom-scan proto — committed by another session, not c1a),
   8f4a383 (-95 CMD verbatim), 7dec62a (-86 CMD verbatim, record-keeping only — **no -86
   implementation rides**). "Nothing else rides" holds for code: the only code commits in
   the bundle are the four listed below.
4. **Orphan npz tmp artifacts on EFS:** every ENOENT failure actually wrote the atlas bytes
   to `state/wave_atlas.npz.tmp.npz` (numpy appended `.npz` — see forensic). At least one
   such orphan likely sits on EFS. Not cleaned (read-only toward her state; not in mandate).
5. **ssmmessages: staged, NOT applied** per CMD — awaiting Joe's approval in chat.
   Staged policy: [GL-IAM-STAGED-SSMMESSAGES-20260702.json](GL-IAM-STAGED-SSMMESSAGES-20260702.json).

---

## BUNDLE (code commits, in order)

| SHA | Item | Content |
|-----|------|---------|
| 842b1db | 1 | wave_atlas.py — to_npz takes file object (numpy path-string `.npz` append bug), load_from_dict, collapse_by_key. Rides as-is, already diff-read. |
| 628e87c | 2 | -91.A — `_save_wave_atlas` wrapped at all five call sites; save_count in `finally`; snapshot copy-loop and SIGTERM `sys.exit(0)` protected. Rides as-is. |
| 3c7ca94 | 3 | -90 attend-mark — `times_attended += 1` + `last_attended_tick` moved to the `_viewed` first-tick block, [gualaloom_v5_engine.py:4713-4719](../dsf_ai_service/v4/gualaloom_v5_engine.py#L4713-L4719); familiarity stays at session end (:4726-4736). |
| cdbb46d | 4 | Build identity — deploy_dsf_ai.sh passes GIT_SHA to CodeBuild → buildspec `--build-arg` → Dockerfile `LABEL org.opencontainers.image.revision` + `/BUILD_INFO` → app.py startup prints `[build] git_sha=… built=…` first in the boot banner. |

Item 2 verification detail (all five sites confirmed at HEAD, exact log string
`[wave] save failed (non-fatal):` at each):
app.py:2943 (migrate endpoint) · app.py:4120 (SIGTERM handler; `sys.exit(0)` reached
regardless) · app.py:4192 (periodic `_do_save_and_compact`) · engine:5733
(sleep_for_deploy; `.sleeping` marker write survives) · engine:6843 (snapshot_state;
copy loop survives).

All three touched Python modules compile at HEAD (`py_compile` OK); `bash -n` OK on the
deploy script; buildspec YAML parses.

---

## ITEM 5 — IAM PRE-DEPLOY

- **5a `s3:PutLifecycleConfiguration`:** already granted (see Failures #1). Verified
  `allowed` by simulation against `arn:aws:s3:::dsf-ai-site-backups`. No change made.
- **5b ssmmessages (ECS exec):** staged in
  [GL-IAM-STAGED-SSMMESSAGES-20260702.json](GL-IAM-STAGED-SSMMESSAGES-20260702.json)
  (CreateControlChannel / CreateDataChannel / OpenControlChannel / OpenDataChannel on `*`,
  as inline policy `dsf-ai-ecs-exec`). **NOT applied.** Applies only after Joe approves in chat.

---

## FORENSIC — THE 19:11:29 / 19:11:31 npz ENOENTs (record-keeping)

Verbatim log lines (stream `dsf-ai/dsf-ai/e48b873c…`, with immediate neighbors):

```
19:11:26.854 | [GualaLoom] Event log compacted: 1870 bytes discarded, 6 events kept
19:11:29.286 | [GualaLoom] WaveAtlas npz save failed (non-fatal): [Errno 2] No such file or directory: 'state/wave_atlas.npz.tmp'
19:11:29.286 | [save] 94.04s core=88.30s grids=2.28s wave=2.43s compact=3.31s
19:11:30.106 | [GualaLoom] Creating snapshot: state/backups/2026-07-02_19-11-29_periodic
19:11:31.754 | [GualaLoom] WaveAtlas npz save failed (non-fatal): [Errno 2] No such file or directory: 'state/wave_atlas.npz.tmp'
```

**Callers, named:**
- **19:11:29 — `_do_save_and_compact(write_wave=True)`** (app.py periodic save, the
  save_count % 10 == 0 wave cycle). Same function then prints the `[save] … wave=2.43s` line.
- **19:11:31 — `snapshot_state(reason="periodic")`** (engine:6843) — the `do_wave` branch
  takes a snapshot right after the save, and snapshot_state calls `_save_wave_atlas` again.
  Its `Creating snapshot:` print at 19:11:30 sits between the two ENOENTs.

**Why `[save]` prints did not stop (the real mechanism, vs. the jam model):** in the
deployed code (e31f40f), `_save_wave_atlas` has an **internal** try/except around the whole
npz sequence — `except Exception: print("[GualaLoom] WaveAtlas npz save failed (non-fatal)")`.
The exception never propagates to any caller, so the periodic loop, its `[save]` print, and
the snapshot all continue. There was never a jam at this site; the -91.A call-site wrappers
are a second containment layer, not the thing that kept saves printing today.

**Root mechanism of the ENOENT itself:** deployed `to_npz(path)` hands the path STRING
`state/wave_atlas.npz.tmp` to `np.savez_compressed`, and numpy appends `.npz` to any path
not ending in `.npz` — the bytes actually land in `state/wave_atlas.npz.tmp.npz`. The
follow-up `open(tmp_path, "rb")` for the -74 fsync discipline then raises ENOENT on
`state/wave_atlas.npz.tmp`. Exactly the bug 842b1db fixes (file object instead of path
string). The 18:16:10 ENOENT (migrate endpoint) is the same mechanism, third caller.

---

## RUNBOOK NOTE (from -91.D, acknowledged)

During this deploy the OLD task's shutdown wave-save will throw this same ENOENT once.
Before the swap: verify the final core save landed (save gauge + S3 hourly).
`.sleeping` marker absence is expected this once.

---

## T-GATES (all post-deploy, all PENDING)

| Gate | Condition |
|------|-----------|
| Boot identity | boot banner `[build] git_sha=…` == guala-live HEAD at deploy |
| Lifecycle | `_apply_s3_lifecycle` succeeds at boot (perm now verified `allowed`) |
| npz exists | `wave_atlas.npz` EXISTS on EFS after first do_wave save AND loads on next boot |
| npz timing | `[save]` shows `wave=Xs` on the #10 cycle |
| npz clean | zero npz ENOENTs in 2h |
| -90 gauge | a HEIC `times_attended` increments on the FIRST tick of the next ATTENDING_VISUAL |
| Count-diff | post-restart count-diff filed (standing rule) |

---

## STATE

Bundle complete and committed on guala-live. c1a is **STOPPED**: no deploy, no further
code. Next step is Eve's — full diff read, then GO; deploy runs sleep_for_deploy on her
wake cycle only (one deploy for this dispatch, per protocol rule 1).

---

## ADDENDUM (post-report, same session — Joe approvals + push order)

1. **ssmmessages APPLIED** (deviation 5 closed). Joe approved in chat. Inline policy
   `dsf-ai-ecs-exec` put on `dsf-ai-task-role` (the four ssmmessages channel actions,
   Resource `*`, exactly as staged). Verified: policy listed on role; simulation
   `allowed` for CreateControlChannel + OpenDataChannel. Caveat: the RUNNING :449 task's
   ExecuteCommandAgent registered at boot without these perms — exec against :449 may
   stay TargetNotConnected until the Deploy-1 task swap; it will work on the new task.
2. **Runbook addition (deviation 4):** after the first post-deploy npz save is verified
   good (`[GualaLoom] WaveAtlas saved (npz)` line + `wave_atlas.npz` present on EFS),
   delete the orphan `state/wave_atlas.npz.tmp.npz` file(s).
3. **Standing rule (effective 2026-07-02):** a report may say FILED only when the commit
   is on origin. Local-only commits are stated as LOCAL-ONLY.

End report.
