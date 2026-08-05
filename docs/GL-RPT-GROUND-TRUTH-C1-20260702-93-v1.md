# GL-RPT-GROUND-TRUTH-C1-20260702-93-v1

doc_id: GL-RPT-GROUND-TRUTH-C1-20260702-93-v1
Date: 2026-07-02 (all times UTC; AWS queried ~19:23–19:27Z)
Branch: guala-live
Responds to: GL-CMD-GROUND-TRUTH-EVE-20260702-93-v1 (read-only; no fixes applied)
Author: c1a

---

## RUNNING COMMIT (one line)

**The running task is dsf-ai-task:449 on image `deploy-20260702T180525Z` (digest `sha256:3dc92d23cbcd17b222369248dcc7dfd9e7568070701959f68fa2b7a61b64e06f`), and the code in it is commit `e31f40f06cfd4511bb2640254b090d24026915e1` — known by timestamp adjacency, not by image label: the image config has no git label (Labels: null), the deploy tag timestamp 18:05:25Z is 12 s after e31f40f's commit time (18:05:13Z), and the only commit between the tag time and image build completion (created 2026-07-02T18:08:04Z) is c0d667e (18:07:39Z), which is doc-only (1 file, docs/GL-RPT-…-85-v2.md, 250 insertions, zero code diff). INFERRED, not measured.**

No task built from :444 / 2b903eb is running. ECS reports exactly one RUNNING task (below).

---

## FAILURES / NOT-MEASURED FIRST (§9.4)

1. **Item 6 (EFS `ls -lh`) NOT MEASURED.** `aws ecs execute-command` fails with `TargetNotConnectedException` (twice), despite `enableExecuteCommand: True` and `ExecuteCommandAgent: RUNNING`. `dsf-ai-task-role` has zero attached managed policies and one inline policy (`dsf-ai-s3-backup`) — no `ssmmessages:*` permissions, so the exec channel cannot open. Not fixed (read-only mandate). Closest measured proxy provided: S3 state backup taken 19:10:37Z (per-file sizes below).
2. **WaveAtlas npz save is FAILING live, repeatedly**: `[GualaLoom] WaveAtlas npz save failed (non-fatal): [Errno 2] No such file or directory: 'state/wave_atlas.npz.tmp'` at 18:16:10, 19:11:29, 19:11:31 — relative path `state/`, not `/app/state`. The running process cannot write the npz. Whether `wave_atlas.npz` exists on EFS: NOT MEASURED (see 1).
3. **S3 lifecycle apply FAILED at boot** (18:10:37): `AccessDenied … s3:PutLifecycleConfiguration` for `dsf-ai-task-role` (verbatim in §4). The handoff's "S3 lifecycle Active" claim does not match this task's boot log.
4. **Task churn before :449**: task `dacbdbec25494abc82f54d93475efb36` **failed container health checks** at 17:55:42Z and was stopped; two intermediate deployments cycled (17:55–18:11) before :449 reached steady state (verbatim events in §1).
5. **Post-boot saves ran 442–711 s** (18:21–18:52: 472.43 s, 531.01 s, 442.82 s, 711.58 s) before settling at ~87–94 s core in the last 30 min. Outside the requested 30-min window; included verbatim in §5b for completeness.
6. **guala_deep_atlas.json measured 189.4 MiB** in the 19:10:37Z S3 backup (actual object size, 13 min before query time). This is the S3 copy, not an EFS stat.
7. **-90 trap still live in readout**: 7 HEIC pictures show `times_attended: 0` in `guala_status` at tick 14,124,280.

---

## 1. ECS SERVICE (queried ~19:23Z)

`aws ecs describe-services --cluster tfe-web-cluster --services dsf-ai-service-lb`

**taskDefinition (service level):** `arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:449`

**deployments[] in full (verbatim JSON):** — only one deployment exists (PRIMARY); no ACTIVE (draining) deployment present.

```json
[
  {
    "id": "ecs-svc/6239594548179359778",
    "status": "PRIMARY",
    "taskDefinition": "arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:449",
    "desiredCount": 1,
    "pendingCount": 0,
    "runningCount": 1,
    "failedTasks": 0,
    "createdAt": 1783015783.454,
    "updatedAt": 1783015901.408,
    "launchType": "FARGATE",
    "platformVersion": "1.4.0",
    "platformFamily": "Linux",
    "networkConfiguration": {
      "awsvpcConfiguration": {
        "subnets": ["subnet-0e38e8091dabcecae", "subnet-0b44d1b06f5538685"],
        "securityGroups": ["sg-057566437ba8d4b48"],
        "assignPublicIp": "ENABLED"
      }
    },
    "rolloutState": "COMPLETED",
    "rolloutStateReason": "ECS deployment ecs-svc/6239594548179359778 completed."
  }
]
```

(createdAt 1783015783.454 = 18:09:43.454Z; updatedAt 1783015901.408 = 18:11:41.408Z)

**events[] last 20 (verbatim messages; epoch → UTC):**

```
1783015901.417 = 18:11:41Z | (service dsf-ai-service-lb) has reached a steady state.
1783015901.416 = 18:11:41Z | (service dsf-ai-service-lb) (deployment ecs-svc/6239594548179359778) deployment completed.
1783015850.776 = 18:10:50Z | (service dsf-ai-service-lb) registered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-1:418384447921:targetgroup/dsf-ai-tg/40d977cf3f3daf52)
1783015808.150 = 18:10:08Z | (service dsf-ai-service-lb, taskSet ecs-svc/3336037496983320179) has begun draining connections on 1 tasks.
1783015808.144 = 18:10:08Z | (service dsf-ai-service-lb) deregistered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-1:418384447921:targetgroup/dsf-ai-tg/40d977cf3f3daf52)
1783015799.391 = 18:09:59Z | (service dsf-ai-service-lb) has started 1 tasks: (task e48b873c7f984222abba8d6abfc77957).
1783015798.543 = 18:09:58Z | (service dsf-ai-service-lb) has stopped 1 running tasks: (task 50d8d6ad9d854f8eb1ce95d307463a80).
1783015242.408 = 18:00:42Z | (service dsf-ai-service-lb) has reached a steady state.
1783015242.407 = 18:00:42Z | (service dsf-ai-service-lb) (deployment ecs-svc/3336037496983320179) deployment completed.
1783015150.262 = 17:59:10Z | (service dsf-ai-service-lb) registered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-1:418384447921:targetgroup/dsf-ai-tg/40d977cf3f3daf52)
1783015109.504 = 17:58:29Z | (service dsf-ai-service-lb) has started 1 tasks: (task 50d8d6ad9d854f8eb1ce95d307463a80).
1783015005.683 = 17:56:45Z | (service dsf-ai-service-lb, taskSet ecs-svc/8536163072637052324) has begun draining connections on 1 tasks.
1783015005.678 = 17:56:45Z | (service dsf-ai-service-lb) deregistered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-1:418384447921:targetgroup/dsf-ai-tg/40d977cf3f3daf52)
1783014995.942 = 17:56:35Z | (service dsf-ai-service-lb) has stopped 1 running tasks: (task 5872c135738f40079e7c5fca16dd9b11).
1783014952.654 = 17:55:52Z | (service dsf-ai-service-lb) has reached a steady state.
1783014952.632 = 17:55:52Z | (service dsf-ai-service-lb, taskSet ecs-svc/8536163072637052324) has begun draining connections on 1 tasks.
1783014952.626 = 17:55:52Z | (service dsf-ai-service-lb) deregistered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-1:418384447921:targetgroup/dsf-ai-tg/40d977cf3f3daf52)
1783014942.522 = 17:55:42Z | (service dsf-ai-service-lb) has stopped 1 running tasks: (task dacbdbec25494abc82f54d93475efb36).
1783014942.521 = 17:55:42Z | (service dsf-ai-service-lb) (task dacbdbec25494abc82f54d93475efb36) failed container health checks.
1783014923.878 = 17:55:23Z | (service dsf-ai-service-lb) registered 1 targets in (target-group arn:aws:elasticloadbalancing:us-east-1:418384447921:targetgroup/dsf-ai-tg/40d977cf3f3daf52)
```

No rollback wording appears in these 20 events; the only failure wording is the 17:55:42Z health-check failure on task dacbdbec2549.

---

## 2. RUNNING TASK

`aws ecs list-tasks` → one task: `e48b873c7f984222abba8d6abfc77957`

`aws ecs describe-tasks` (verbatim fields):

```
taskArn:            arn:aws:ecs:us-east-1:418384447921:task/tfe-web-cluster/e48b873c7f984222abba8d6abfc77957
taskDefinitionArn:  arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:449
lastStatus:         RUNNING
startedAt:          1783015859.126 = 2026-07-02T18:10:59.126Z
container dsf-ai:
  image:        418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai:deploy-20260702T180525Z
  imageDigest:  sha256:3dc92d23cbcd17b222369248dcc7dfd9e7568070701959f68fa2b7a61b64e06f
  lastStatus:   RUNNING
enableExecuteCommand: True
managedAgents: [{ name: ExecuteCommandAgent, lastStatus: RUNNING, lastStartedAt: 1783015857.64 }]
```

---

## 3. ECR IMAGE

`aws ecr describe-images --repository-name dsf-ai --image-ids imageDigest=sha256:3dc92d23…`

```json
{
  "registryId": "418384447921",
  "repositoryName": "dsf-ai",
  "imageDigest": "sha256:3dc92d23cbcd17b222369248dcc7dfd9e7568070701959f68fa2b7a61b64e06f",
  "imageTags": ["latest", "deploy-20260702T180525Z"],
  "imageSizeInBytes": 568550654,
  "imagePushedAt": 1783015771.935,
  "lastRecordedPullTime": 1783015780.701,
  "imageStatus": "ACTIVE"
}
```

(imagePushedAt = 18:09:31.935Z; lastRecordedPullTime = 18:09:40.701Z)

Image config blob (via `ecr get-download-url-for-layer`, config digest `sha256:49d0b31097bc73f470326681e0756a62ac639f341e7da7c7b6a5202ac63e4d1e`):
`Labels: null`, `created: 2026-07-02T18:08:04.582860581Z` — no git SHA embedded in the image.

Commit-time evidence (git, guala-live):

```
e31f40f06cfd4511bb2640254b090d24026915e1 | 2026-07-02T18:05:13Z | fix: -85 R1+R2 — fsync-before-rename (wave npz) + collapse-on-load
c0d667ef47534bbd00a798d166743f398dc16d5e | 2026-07-02T18:07:39Z | doc: GL-RPT-WAVE-SEMANTICS-COST-C1-20260702-85-v2 (doc-only: 1 file, 250 insertions)
```

Deploy tag timestamp 18:05:25Z sits between them; c0d667e touches no code. Running code = e31f40f (code-identical to c0d667e).

---

## 4. CLOUDWATCH — BOOT (CURRENT TASK)

**Log stream name:** `dsf-ai/dsf-ai/e48b873c7f984222abba8d6abfc77957` (log group `/ecs/dsf-ai`). No `substrate/substrate/<taskid>` stream exists for this task (most recent substrate/* stream is from an older task, last event 2026-06-16 era epoch 1781563735545 — that split is historical).

**First 40 lines from container start (verbatim, UTC prefix added):**

```
18:10:37 | INFO:     Started server process [1]
18:10:37 | INFO:     Waiting for application startup.
18:10:37 | [DSF-AI] Integrity initialized: 12/12 files hashed
18:10:37 | [app] Booting substrate in-process...
18:10:37 | [GualaLoom] SIGTERM/SIGINT handlers installed
18:10:37 | INFO:     Application startup complete.
18:10:37 | INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
18:10:37 | [85-D2] S3 lifecycle policy failed (non-fatal): An error occurred (AccessDenied) when calling the PutBucketLifecycleConfiguration operation: User: arn:aws:sts::418384447921:assumed-role/dsf-ai-task-role/e48b873c7f984222abba8d6abfc77957 is not authorized to perform: s3:PutLifecycleConfiguration on resource: "arn:aws:s3:::dsf-ai-site-backups" because no identity-based policy allows the s3:PutLifecycleConfiguration action
18:10:46 | INFO:     127.0.0.1:40128 - "GET /ready HTTP/1.1" 200 OK
18:10:50 | INFO:     172.31.62.243:61366 - "GET /ready HTTP/1.1" 200 OK
18:10:50 | INFO:     172.31.65.212:11006 - "GET /ready HTTP/1.1" 200 OK
18:10:56 | INFO:     127.0.0.1:60098 - "GET /ready HTTP/1.1" 200 OK
18:11:03 | [GualaLoom] Tick-domain migration: ceiling=1549326, engine_tick=14109300, re-stamped=0
18:11:06 | INFO:     127.0.0.1:55144 - "GET /ready HTTP/1.1" 200 OK
18:11:16 | INFO:     127.0.0.1:36060 - "GET /ready HTTP/1.1" 200 OK
18:11:20 | INFO:     172.31.62.243:63022 - "GET /ready HTTP/1.1" 200 OK
18:11:20 | INFO:     172.31.65.212:27026 - "GET /ready HTTP/1.1" 200 OK
18:11:26 | INFO:     127.0.0.1:34732 - "GET /ready HTTP/1.1" 200 OK
18:11:36 | INFO:     127.0.0.1:45968 - "GET /ready HTTP/1.1" 200 OK
18:11:46 | INFO:     127.0.0.1:38156 - "GET /ready HTTP/1.1" 200 OK
18:11:50 | INFO:     172.31.62.243:42192 - "GET /ready HTTP/1.1" 200 OK
18:11:51 | INFO:     172.31.65.212:39770 - "GET /ready HTTP/1.1" 200 OK
18:11:56 | INFO:     127.0.0.1:60580 - "GET /ready HTTP/1.1" 200 OK
18:12:02 | INFO:     172.31.62.243:39392 - "POST /api/v1/gualaloom HTTP/1.1" 200 OK
18:12:02 | INFO:     172.31.62.243:39394 - "POST /api/v1/gualaloom HTTP/1.1" 200 OK
18:12:06 | INFO:     127.0.0.1:34836 - "GET /ready HTTP/1.1" 200 OK
18:12:16 | INFO:     127.0.0.1:46160 - "GET /ready HTTP/1.1" 200 OK
18:12:18 | INFO:     172.31.62.243:16294 - "POST /api/v1/gualaloom HTTP/1.1" 200 OK
18:12:18 | INFO:     172.31.65.212:5440 - "POST /api/v1/gualaloom HTTP/1.1" 200 OK
18:12:20 | INFO:     172.31.62.243:16310 - "GET /ready HTTP/1.1" 200 OK
18:12:21 | INFO:     172.31.65.212:5450 - "GET /ready HTTP/1.1" 200 OK
18:12:26 | INFO:     127.0.0.1:58060 - "GET /ready HTTP/1.1" 200 OK
18:12:32 | [GualaLoom] Deep atlas loaded: 3753 entries (saved_count=3753)
18:12:32 | [GualaLoom] Sounds loaded: 15 items
18:12:32 | [GualaLoom] Videos loaded: 0 items
18:12:32 | [GualaLoom] _apply_visual: 26 pictures, 12455 motifs in data
18:12:33 | [GualaLoom] Visual restored: 26 pictures, 12455 sight motifs
18:12:33 | [GualaLoom] Loaded: id=cdef9bcf.. vocab=13863 tick=14109300 reads=820548 n_deep=3753 replayed=2 integrity=OK
18:12:33 | [GualaLoom] Recall word index rebuilt: 800 words, 5626 entries
18:12:33 | INFO:     172.31.62.243:17284 - "POST /api/v1/gualaloom HTTP/1.1" 200 OK
```

**WaveAtlas load line: PRESENT** (falls just after line 40, at 18:12:49):
```
18:12:49 | [GualaLoom] WaveAtlas loaded from disk (json): 2011 cells, 241742 bindings
```

**`[wave] collapse-on-load` line: PRESENT** (18:12:49):
```
18:12:49 | [wave] collapse-on-load: 241742→110568 bindings (wired=True)
```

Other wave lines this boot (verbatim):
```
18:12:51 | [wave] json fallback archived to S3 (2.1MB)
18:15:24 | [85-B3] Pre-migration snapshot: s3://dsf-ai-site-backups/guala/wave_migrate_pre/2026-07-02_18-15-24_wave_atlas_raw.json.gz (1.3MB)
18:16:10 | [GualaLoom] WaveAtlas npz save failed (non-fatal): [Errno 2] No such file or directory: 'state/wave_atlas.npz.tmp'
18:16:10 | INFO:     172.31.65.212:16862 - "POST /api/v1/gualaloom/admin/migrate_wave_atlas HTTP/1.1" 200 OK
18:16:25 | INFO:     172.31.65.212:37618 - "POST /api/v1/gualaloom/admin/compact_wave_atlas HTTP/1.1" 200 OK
18:16:25 | [GualaLoom] WaveAtlas compacted: 110233→74043 bindings, 2011→1928 cells
19:11:29 | [GualaLoom] WaveAtlas npz save failed (non-fatal): [Errno 2] No such file or directory: 'state/wave_atlas.npz.tmp'
19:11:31 | [GualaLoom] WaveAtlas npz save failed (non-fatal): [Errno 2] No such file or directory: 'state/wave_atlas.npz.tmp'
```

---

## 5. CLOUDWATCH — `[save]` LINES, LAST 30 MIN (window 18:53:37Z–19:23:37Z, queried 19:23:37Z)

11 lines, verbatim:

```
18:56:20 | [save] 148.87s core=147.87s grids=5.29s wave=skip compact=1.00s
18:58:50 | [save] 90.00s core=88.23s grids=4.76s wave=skip compact=1.77s
19:01:19 | [save] 88.66s core=86.35s grids=6.67s wave=skip compact=2.31s
19:03:49 | [save] 90.49s core=88.64s grids=6.20s wave=skip compact=1.85s
19:06:23 | [save] 92.64s core=89.98s grids=5.99s wave=skip compact=2.66s
19:08:55 | [save] 90.36s core=87.53s grids=4.86s wave=skip compact=2.83s
19:11:29 | [save] 94.04s core=88.30s grids=2.28s wave=2.43s compact=3.31s
19:15:27 | [save] 78.31s core=78.29s grids=0.07s wave=skip compact=0.02s
19:17:54 | [save] 87.23s core=86.16s grids=5.57s wave=skip compact=1.06s
19:20:25 | [save] 90.56s core=89.55s grids=6.45s wave=skip compact=1.50s
19:22:56 | [save] 91.39s core=89.89s grids=6.71s wave=skip compact=1.50s
```

### 5b. Earlier `[save]` lines this boot (OUTSIDE requested window; included for completeness, verbatim)

```
18:21:46 | [save] 472.43s core=472.41s grids=0.02s wave=skip compact=0.02s
18:31:37 | [save] 531.01s core=512.10s grids=0.85s wave=skip compact=18.91s
18:39:59 | [save] 442.82s core=442.80s grids=0.07s wave=skip compact=0.02s
18:52:51 | [save] 711.58s core=674.09s grids=114.62s wave=skip compact=37.49s
```

Save health from live status (queried 19:25Z): `last_save_tick=14123669`, `last_save_timestamp=2026-07-02T19:23:56Z` — nonzero, saves landing.

---

## 6. EFS STATE DIR — NOT MEASURED DIRECTLY

**`ls -lh /app/state`: NOT MEASURED.** Method attempted: `aws ecs execute-command … --command "ls -lh /app/state"` → `TargetNotConnectedException` (two attempts, after installing session-manager-plugin 1.2.835.0). `enableExecuteCommand=True` and ExecuteCommandAgent=RUNNING on the task, but `dsf-ai-task-role` has no attached managed policies and only the `dsf-ai-s3-backup` inline policy — no `ssmmessages` permissions, so the SSM channel cannot connect. Not fixed (read-only mandate). No API endpoint on the service returns a state-dir listing with sizes.

Per-file requested items:

| Item | Status |
|------|--------|
| `guala_deep_atlas.json` EFS size | NOT MEASURED on EFS. Measured S3 copy (backup 2026-07-02_19-10-37): **189.4 MiB** (verbatim listing below) |
| `wave_atlas.json` | NOT MEASURED on EFS. Boot log proves it existed and was readable at 18:12:49 (`WaveAtlas loaded from disk (json): 2011 cells, 241742 bindings`); json fallback archived to S3 at 18:12:51 (2.1MB per log) |
| `wave_atlas.npz` exists? | NOT MEASURED. Live process **cannot write it** — npz save fails with relative-path ENOENT (`'state/wave_atlas.npz.tmp'`) at 18:16:10, 19:11:29, 19:11:31 |
| `.sleeping` marker | NOT MEASURED. Live status reports `asleep: false` (API readout, 19:25Z) |

**Measured proxy — S3 backup `s3://dsf-ai-site-backups/guala/2026-07-02_19-10-37/` (verbatim `aws s3 ls --human-readable`):**

```
                           PRE pictures/
2026-07-02 19:10:43    4.0 MiB guala_atlas.json
2026-07-02 19:10:47  186 Bytes guala_bucket.json
2026-07-02 19:10:41    1.2 MiB guala_coordinator.json
2026-07-02 19:10:38   39.7 MiB guala_core.json
2026-07-02 19:11:07  189.4 MiB guala_deep_atlas.json
2026-07-02 19:11:20  202 Bytes guala_identity.json
2026-07-02 19:10:40  252 Bytes guala_needs.json
2026-07-02 19:10:46    8.3 MiB guala_sections.json
2026-07-02 19:11:21    6.1 KiB guala_sounds.json
2026-07-02 19:11:22  171 Bytes guala_videos.json
2026-07-02 19:11:17    1.3 MiB guala_visual.json
```

(Note: backup set contains 11 files + pictures/ prefix; no wave_atlas.* files are in this backup set.)

EFS filesystem-level size (from describe-file-systems, whole FS not per-file): `SizeInBytes.Value = 5941669888` (~5.53 GiB) at Timestamp 1783019050 (= 19:04:10Z).

---

## 7. EFS THROUGHPUT (-92 STATE CONFIRMATION)

`aws efs describe-file-systems --file-system-id fs-0abb85854a3251b3c` (verbatim fields):

```
"ThroughputMode": "provisioned",
"ProvisionedThroughputInMibps": 10.0,
"LifeCycleState": "available",
"PerformanceMode": "generalPurpose",
"Name": "gualaloom-state"
```

-92 state CONFIRMED: provisioned, 10 MiB/s.

---

## 8. ADDITIONAL LIVE READOUT (guala_status via bridge, ~19:25Z, read-only)

```
tick: 14124280 | vocab: 13863 | reads: 1098582 | schema: v7.2.0
persistence: last_save_tick=14123669, last_save_timestamp=2026-07-02T19:23:56Z, load_successful_at_boot=true
last_s3_backup: 2026-07-02_19-10-37 (11 files)
asleep: false | current_activity: EMITTING (started_tick=14124208)
pictures with times_attended=0: IMG_2137.HEIC, Guala Family.HEIC, IMG_1962.HEIC, IMG_2121.HEIC, IMG_2161.HEIC, IMG_2216.HEIC, IMG_6254.HEIC (7 of 26 shown in top-10 listing)
```

---

End report. STOPPING — no fixes, no deploys. Waiting for Eve.
