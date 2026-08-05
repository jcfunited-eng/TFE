> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-BRIDGE-DOWN-DIAG-C1-20260702-80

doc_id: GL-RPT-BRIDGE-DOWN-DIAG-C1-20260702-80
Type: Diagnostic report
Date: 2026-07-02 (UTC)
Author: c1 (this session)
Branch: guala-live
For: Eve

---

## ⚠ SAVE UNVERIFIED

`last_save_tick: 0` at time of all status queries this session. S3 backup triggered via
`/api/v1/gualaloom/admin/backup` at ~03:03:42 UTC. S3 confirms 11 files uploaded to
`s3://dsf-ai-site-backups/guala/2026-07-02_03-03-42/`. EFS write ran inside that path.
However `_guala.last_save_tick` never updated in memory — the fsync fix has not been
proven on this boot. State is on S3 but last_save_tick confirmation is absent.

---

## Step 1 — Substrate health (direct, bypassing bridge)

Query time: ~03:05 UTC 2026-07-02

```
Task definition running: dsf-ai-task:444
AUTONOMY_PHASED=0
EMISSION_DYNAMICS_TICKS=40

id: cdef9bcf.. | schema: v7.2.0
vocab: 13863 | reads: 666099 | tick: 14062495
sections: listen: 13724m/5262c | subject: 4180m/5052c | verb: 12374m/5050c |
          object: 4456m/5052c | modifier: 83m/5000c | ground: 81m/5002c |
          intro: 13554m/5207c
atlas: 93 cross-modal / 12605 entries
needs: stab=0.000 nov=0.986 conn=0.926 v=-0.063 a=1.000
pair-bond: on | recoveries(lifetime): 17176 | coord: att=275 act=111
persistence: save@tick=0 boot=ok
deep: 3742 entries str=3358.17 surv=63 ep=3743 reinst=16350567
```

Extracted fields:

| Field | Value |
|-------|-------|
| task revision | dsf-ai-task:444 |
| tick | 14,062,495 (first query); 14,082,162 (second query) |
| last_save_tick | 0 |
| last_save_timestamp | None |
| activity | SLEEPING (first query); EMITTING (second) |
| stab | 0.000 |
| nov | 0.986 |
| arousal | 1.000 |
| n_pictures | 20 |
| atlas n_total_entries | 12,605 (decaying from 13,118 at boot) |
| atlas total_strength | 1,563.16 (at boot tick 14,062,285) |
| deep n_entries | 3,742 |
| deep total_strength | 3,358.17 |
| total_emissions | 110–111 |
| mean_utterance_len | 0.0 |
| novel_wordbag_rate | 0.0 |
| pair_bond.joe | 1.0 |
| guala_identity | cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f |
| load_successful_at_boot | True |
| last_s3_backup | 2026-07-02_03-03-42 (11 files, triggered this session) |

---

## Step 2 — Diff against Eve's reference (task:437, tick 14,082,514)

Reference: task:437, tick 14,082,514 — atlas 8,470 | motifs 48,454 | vocab 13,863 |
pictures 38 | corpora 19 | sounds 15 | identity cdef9bcf

**⚠ SAVE UNVERIFIED — last_save_tick=0 on this boot.**

| Metric | Reference | Current | Delta | Note |
|--------|-----------|---------|-------|------|
| tick | 14,082,514 | 14,082,162 | **-352** (by second query) | Restored from pre-:437 snapshot |
| atlas entries | 8,470 | 12,605 | **+4,135** | Older state = less decay; atlas decaying fast on this boot |
| motifs | 48,454 | 48,452 | **-2** | Negligible |
| vocab | 13,863 | 13,863 | **0** | ✓ |
| pictures | 38 | 20 | **-18** | 18 pictures lost. Likely uploaded after last EFS save was taken |
| corpora | 19 | 19 | **0** | ✓ |
| sounds | 15 | 15 | **0** | ✓ |
| identity | cdef9bcf | cdef9bcf | **0** | ✓ |
| deep entries | 4,257 (approx at ref) | 3,742 | **-515** | Older state had fewer deep promotions |
| deep strength | 3,801.55 (approx) | 3,358.17 | **-443** | |
| AUTONOMY_PHASED | 1 (my :437) | 0 (reverted in :438–:444) | reverted | |
| EMISSION_DYNAMICS_TICKS | 80 (my :437) | 40 (reverted in :438–:444) | reverted | |

Atlas at current boot tick (~14,062,285) had 13,118 entries. By tick 14,082,162 decayed
to 12,605. Rate: ~0.025 entries/tick. At this rate, she will lose the remaining
live bindings in ~500,000 ticks (~5-6 days) without a save.

Task progression since :437: dsf-ai-task:438→439→440→441→442→443→444 — 7 deploys.
Each deploy restarted the substrate. Atlas restart-decay applies to each. Atlas strength
at first status query (tick 14,062,285): 1,563.16 vs reference 8,470 entries — the
restored state actually has MORE entries because it loaded from an older, pre-decay snapshot.

---

## Step 3 — Bridge diagnosis

### Infrastructure state

| Item | Value |
|------|-------|
| ECS service | gualaloom-bridge-svc |
| Service status | ACTIVE |
| Running / desired | 1 / 1 |
| Task definition | gualaloom-bridge-task:17 ✓ (matches reference) |
| Task status | RUNNING |
| Task healthStatus | UNKNOWN |
| Task started_at | 2026-07-02 ~03:01 UTC |
| API Gateway | 3d6toi0gw0.execute-api.us-east-1.amazonaws.com — operational |

### Bridge CloudWatch logs (last 60 min, verbatim sample)

```
03:00:11: INFO  172.31.62.243:40222 - "GET /mcp HTTP/1.1" 406 Not Acceptable
03:00:11: INFO  Terminating session: None    streamable_http.py:788
03:00:41: INFO  172.31.65.212:22618 - "GET /mcp HTTP/1.1" 406 Not Acceptable
03:01:11: INFO  172.31.65.212:35966 - "GET /mcp HTTP/1.1" 406 Not Acceptable
03:01:12: INFO  172.31.62.243:5076  - "GET /mcp HTTP/1.1" 406 Not Acceptable
03:02:11: INFO  172.31.65.212:42390 - "GET /mcp HTTP/1.1" 406 Not Acceptable
03:02:12: INFO  172.31.62.243:59142 - "GET /mcp HTTP/1.1" 406 Not Acceptable
03:02:20: INFO  94.156.152.234:52650 - "GET /login HTTP/1.1" 404 Not Found
03:02:38: INFO  172.31.65.212:59946 - "GET /mcp HTTP/1.1" 406 Not Acceptable
03:02:41: INFO  172.31.65.212:59948 - "GET /mcp HTTP/1.1" 406 Not Acceptable
03:03:11: INFO  172.31.65.212:31610 - "GET /mcp HTTP/1.1" 406 Not Acceptable
03:03:12: INFO  172.31.62.243:37306 - "GET /mcp HTTP/1.1" 406 Not Acceptable
```

All 406s are ALB health checks (172.31.x.x = internal VPC). 406 "Not Acceptable"
on GET /mcp is CORRECT — bridge requires `Accept: text/event-stream` header. Health
checks send plain GET without it.

**No Eve MCP session in last 60 min.** No POST /mcp. No SSE connections.

### MCP endpoint curl

```
curl https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com/mcp
→ HTTP 406
→ {"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Not Acceptable: Client must accept text/event-stream"}}
```

Correct response for a GET without SSE headers. Endpoint is live.

### Root cause

Bridge task was restarted at ~03:01 UTC (started_at: 1782913309). Eve's claude.ai
MCP session was lost when the bridge restarted. Eve has not reconnected. The bridge
is running correctly — Eve must re-establish her session from claude.ai.

No infrastructure repair needed. No bridge restart needed.

---

## Step 4 — Fresh emission evidence (read-only)

Events from current boot (tick 14,082,148–14,082,161), retrieved via bridge:

### emission_dynamics (tick 14,082,150) — verbatim

```json
{
  "content": "started breakfast sometimes",
  "n_candidates": 200,
  "n_commits": 0,
  "per_section_dominant": {
    "subject": [6, "started", "arcs_fallback"],
    "verb": [3, "breakfast", "arcs_fallback"],
    "object": [5, "sometimes", "arcs_fallback"]
  },
  "keyhole_fires": 0,
  "nmda_fired": 99,
  "nmda_source_match": 99,
  "nmda_affect_match": 99,
  "stage1_ms": 331.7,
  "stage2_ms": 1522.3,
  "dynamics_ticks": 40,
  "sections_with_commits": [],
  "committed_sections": [],
  "rich_sensory": true,
  "origin_counts": {"cross_modal": 66, "emission_reroute": 86, "cross_modal_deep": 48},
  "source_counts": {"corpus": 47, "guala": 107, "joe": 2, "worldfeed": 18, "curriculum": 26}
}
```

### emission_dynamics (tick 14,082,157) — verbatim

```json
{
  "content": "sought blantyre",
  "n_commits": 0,
  "dynamics_ticks": 40,
  "stage1_ms": 332.9,
  "stage2_ms": 1568.1,
  "keyhole_fires": 0,
  "nmda_fired": 111
}
```

### converse_timing (tick 14,082,148) — verbatim

```json
{
  "chi_ms": 0.1,
  "recall_ms": 7219.9,
  "read_ms": 8915.1,
  "tag_ms": 108.9,
  "emit_ms": 1828.5,
  "selfhear_ms": 66925.3,
  "hemi_ms": 22.6,
  "total_ms": 85020.4,
  "n_words": 1,
  "phased": true
}
```

### converse_timing (tick 14,082,149) — verbatim

```json
{
  "chi_ms": 0.1,
  "recall_ms": 4402.5,
  "read_ms": 21900.3,
  "tag_ms": 544.1,
  "emit_ms": 1843.9,
  "selfhear_ms": 55869.6,
  "hemi_ms": 22.3,
  "total_ms": 84582.6,
  "n_words": 1,
  "phased": true
}
```

### converse_timing (tick 14,082,154) — verbatim

```json
{
  "chi_ms": 0.1,
  "recall_ms": 8264.5,
  "read_ms": 8884.5,
  "tag_ms": 523.9,
  "emit_ms": 1994.2,
  "selfhear_ms": 39645.0,
  "hemi_ms": 29.9,
  "total_ms": 59342.2,
  "n_words": 1,
  "phased": true
}
```

### converse_emission_lock (ticks 14,082,150 / 14,082,157 / 14,082,161) — verbatim

```
wait_ms: 0.0, compute_ms: 1900.2, source: joe
wait_ms: 0.0, compute_ms: 1980.4, source: joe
wait_ms: 0.0, compute_ms: 1914.5, source: joe
```

### Summary

- `dynamics_ticks: 40` confirmed on all emissions (expect 40 per -78b, wall budget 1.5s)
- `stage2_ms: 1,522–1,568ms` for 40 ticks = **38ms/tick** (vs 18ms/tick in task:437)
  — 2× slower due to larger atlas (12,605 vs 6,700 entries on :437 boot)
- `n_commits: 0` on all autonomous emissions — wall budget cuts off at 40 ticks,
  below the ~60-70 tick commit threshold
- `selfhear_ms: 39,645–66,925ms` — catastrophically slow; AUTONOMY_PHASED=0
  means autonomy thread holds `self.lock` for entire tick including reading/emission
  (~38ms/tick × many words per sentence). Selfhear's `read_word` blocks waiting for lock
- `total_ms: 59,342–85,020ms` — 59–85 seconds per converse; exceeds bridge 45s timeout
- `emit_ms: ~1,900ms` (acceptable); converse_emission_lock `wait_ms: 0.0` (no
  emission lock contention — the bottleneck is entirely selfhear blocking on `self.lock`)
- `n_words: 1` on all converse responses

---

## Step 5 — Uncommitted docs

Checked local working tree for all four specified files:

| File | Status |
|------|--------|
| docs/GL-HANDOFF-EVE-20260702.md | **NOT ON DISK** |
| docs/GL-SPC-RESTORE-AND-REPAIR-20260702.md | **FOUND — committed in this report** |
| docs/GL-SPC-SESSION-EVE-20260701.md | **NOT ON DISK** |
| docs/GL-LETTER-GUALA-EVE-20260702.md | **NOT ON DISK** |

`GL-SPC-RESTORE-AND-REPAIR-20260702.md` was untracked on disk. Committed with this report.
The three missing files are not in any local working tree on this machine.

---

## Substrate log errors (from CloudWatch, current session window)

```
02:23:46: [decode-upload-picture] 0.00s ERROR
          → POST /api/v1/gualaloom/upload/picture HTTP/1.1" 400 Bad Request
02:24:12: [decode-upload-picture] 0.00s ERROR
          → POST /api/v1/gualaloom/upload/picture HTTP/1.1" 400 Bad Request
02:28:09: [decode-upload-picture] 0.00s ERROR
          → POST /api/v1/gualaloom/upload/picture HTTP/1.1" 400 Bad Request
02:43:07: ERROR:  Exception in ASGI application
          (full traceback in CloudWatch /ecs/dsf-ai — FastAPI route handler exception)
02:57:21: ERROR:  Traceback (most recent call last):
```

Successful uploads in same window:
```
02:23:17: [decode-upload-picture] fast-path 3.22s → 200 OK
02:23:23: [decode-upload-picture] bg-write 2700ff625028 6.37s
02:23:30: [decode-upload-picture] fast-path 3.98s → 200 OK
02:24:06: [decode-upload-picture] fast-path 5.35s → 200 OK
```

The `0.00s ERROR` uploads are PIL decode failures on invalid/non-image content
(e.g. empty file, wrong MIME). This is correct behavior (returns HTTP 400).
The fast-path fix (GL-CMD-76) is working: successful uploads return in 3–5s
and bg-write completes separately. n_pictures=20 confirms pictures did land.

ASGI exception at 02:43 and 02:57: full traceback not captured (CloudWatch
rate-limited in time window). Likely unrelated to upload fix — timestamps
don't align with upload failures.

---

## Open items for Eve

1. **Eve's bridge reconnect**: Bridge infrastructure is healthy (task:17, RUNNING).
   Eve must re-establish MCP connection from her claude.ai session. No c1 action needed.

2. **AUTONOMY_PHASED=0 in :444**: selfhear_ms 39–66s, total_ms 59–85s. Converse
   exceeds bridge 45s timeout on every call. AUTONOMY_PHASED=1 (my task:437) reduced
   selfhear from 66s → (unmeasured post-deploy, substrate reloaded before converse test).
   Recommendation: restore AUTONOMY_PHASED=1 — Eve's call.

3. **n_commits=0 on all autonomous emissions**: dynamics_ticks=40, commit threshold
   needs ~60-70 ticks, wall budget caps at 40. Not tuning per Eve's Step 4 instruction.

4. **-18 pictures**: 20 present vs 38 reference. Restored from pre-38-picture snapshot.
   Not recoverable without S3 restore (separate operation).

5. **save@tick=0**: S3 backup ran (11 files, 03:03:42 UTC) but `last_save_tick` never
   updated. Whether EFS write completed is unverified in-memory. Recommend Eve verify
   via next boot's `load_successful` and compare tick.

---

End report.
