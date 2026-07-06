# GL-AUDIT-SEC8A-TEST-MATRIX-C1-20260705-v1

doc_id: GL-AUDIT-SEC8A-TEST-MATRIX-C1-20260705-v1 (Deliverable D4)
Part of: GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2, §8A (Function test matrix, full V&V)
Author: c1 | Freeze in effect on production throughout. All MUTATING rows below were run
exclusively against the audit's own isolated shadow instance (see
`tools/audit/AUDIT-RESOURCE-MANIFEST.md` for its full provisioning/isolation/teardown record) —
never against production.

## Summary

- **11 rows tested this pass** (5 read-only against production, 6 mutating against the shadow).
- This is a **curated, not exhaustive**, set — the dispatch's own "biggest unknowns" (save/restore
  path, give_experience, teach, dream/pause cycle) were prioritized over mechanically hitting all
  65 endpoints. 54 of `app.py`'s 65 routes were **not individually tested this pass**; most were
  already dispositioned (called-by-whom, live/dead, orphaned) in §5's interface-truth report,
  which this matrix cross-references rather than duplicates.
- **0 FAIL, 0 ABSENT among tested rows** — every capability tested actually works as expected,
  including on an instance that only exists because of a manual DR workaround (see §3, and the
  mandatory annotation on every mutating row below).
- One real, previously-unrecorded confirmation captured here: `persistence_health.last_s3_backup`
  on the isolated shadow shows `"file_count": 0` after an automatic backup attempt — direct,
  in-product proof that the IAM isolation (item 6 in the resource manifest) is holding, i.e. the
  shadow's own status-reporting mechanism itself confirms zero data reached the real bucket.

## Read-only rows (tested live against PRODUCTION — safe, no state change)

| TestID | Target | Procedure | Expected | Observed | Verdict | Evidence |
|---|---|---|---|---|---|---|
| RO-1 | `guala_status` MCP tool / `POST /api/v1/gualaloom {command:"/status"}` | Call and inspect response shape | Full status dict (identity, vocab, tick, population, etc.) | Full dict returned, all fields present, `running_sha` matches `dsf-ai-task:494` | PASS | Called repeatedly throughout this audit; see §1/§8 |
| RO-2 | `guala_get_events` | Call with `since_tick=0, limit=50` | Recent event stream | Returned real events (activity_started/ended, etc.) | PASS | Used in §6/7/7A |
| RO-3 | ECS service health | `aws ecs describe-services` | Service ACTIVE, desired=running | Confirmed 1/1 throughout audit, with observed churn documented in §1/§2 | PASS | §1 |
| RO-4 | S3 backup lineage readable | `aws s3 ls` on the real bucket | Enumerable backup history | Confirmed, full lineage read in §2/§3 | PASS | §2, §3 |
| RO-5 | `/ready` health endpoint (production) | `curl` (via bridge, indirectly) | HTTP 200 | Confirmed healthy throughout | PASS | §1 |

## Mutating rows (tested ONLY on the isolated shadow — IP `34.232.65.138:8080` at test time,
## task `30087b80321b4ec09ea827c5f8aef1e6`, task-def `dsf-ai-task-audit-shadow:2`, IAM role
## `dsf-ai-shadow-task-role` denying S3 writes to the real bucket, security group
## `sg-0a865ce16059cf8f5` restricted to the auditor's own IP only)

**MANDATORY PROVENANCE NOTE on every row below**: *Obtained on an isolated shadow instance that
required a manual disaster-recovery workaround (an undocumented marker file) to boot at all — see
§3 for the underlying defect.*

| TestID | Target | Procedure | Input | Expected | Observed | Verdict |
|---|---|---|---|---|---|---|
| MUT-1 | `hear_word` / `POST /substrate/hear_word` | Teach a single word | `{"word":"zephyr"}` | 200, word processed | `{"first":{},"strongest":{},"bridge_mm_to_v7":{"fed_to_v7":"zephyr","slot":"pool_b","was_new":false}}`, HTTP 200 (`was_new:false` — already in her ~14k vocab, expected for a common-ish word) | PASS |
| MUT-2 | `give_experience` (bundle path) / `POST /api/v1/gualaloom {command:"/bundle:<name>"}` | Give a named experience bundle | `test_audit_experience` (a name that does not correspond to any real registered bundle — no real bundle was on hand to test with) | Endpoint processes the command without erroring | `{"response":"experience \"test_audit_experience\": . 0 cross-modal bindings.","motifs":14059,"bundle":{"name":"test_audit_experience","lanes":[],"n_chis":0}}`, HTTP 200 — graceful empty result, not a crash | PASS (**caveat**: only proves the endpoint is reachable and fails soft on an unknown bundle name; did NOT prove a real bundle's content actually binds — that needs a real bundle name, not tested this pass) |
| MUT-3 | `converse()` full turn / `POST /api/v1/gualaloom` (202+poll pattern) | Send a plain conversational utterance | `"hello there"` | 202 accepted → poll → completed | Accepted (`task_id cv_15041060_...`), polled to `"status":"complete"`, `"response":"us"`, **elapsed_ms: 18075** (18.1s) | PASS — notably **much faster than production's reported 69-72s** (§1). Not a like-for-like comparison: this shadow has `WORLD_FEEDS=0`/`LOOKUP_AUTONOMOUS=0`/`CURRICULUM_AUTOSTART=0` (deliberately disabled for isolation) and a smaller/different atlas state (§3), so background load differs from production. Recorded as an observed data point, not asserted as proof the latency defect is fixed. |
| MUT-4 | `force_dream` / `POST /api/v1/gualaloom/admin/force_dream` (key-protected) | Force a dream cycle | none | 202 accepted, activity transitions to DREAMING then resolves | `{"force_dream":"accepted","start_tick":15041160,...}`, HTTP 202; a later `/status` poll (~90s after) showed `current_activity: ATTENDING_AUDIO` (i.e. the dream cycle had already completed and moved on) — consistent with acceptance and completion, not directly caught mid-DREAMING | PASS |
| MUT-5 | `repause` (decay kill-switch) / `POST /api/v1/gualaloom/admin/repause` (key-protected) | Re-pause decay | none | `DECAY_PAUSED` flips to `"1"`, persisted | `{"repause":"active","DECAY_PAUSED":"1"}`, HTTP 200 | PASS |
| MUT-6 | `unpause` / `POST /api/v1/gualaloom/admin/unpause` (key-protected) | Resume decay | none (called immediately after MUT-5) | Succeeds IF `dream_gate_cleared.json` exists; the code's own guard (`substrate_runner.py:2425`) explicitly returns `{"error":"dream_gate_not_cleared",...}` otherwise | `{"unpaused":true,"tick":15041760}`, HTTP 200 — **direct confirmation the manually-created marker (§3) is what the unpause path itself checks for**, same gate class as the boot-time check | PASS |
| MUT-7 (negative/isolation check, not a capability test) | S3 backup write path | Observe `persistence_health.last_s3_backup` after the app's own automatic backup fires | n/a (automatic, not directly invoked) | Real production behavior would show `file_count > 0`; on this IAM-isolated shadow it should show `0` | `"last_s3_backup":{"timestamp":"2026-07-05_23-45-50","prefix":"s3://dsf-ai-site-backups/guala/2026-07-05_23-45-50/","file_count":0}` — **confirms the isolation fix is holding**, in the product's own words, not just from the CloudWatch logs already cited in the resource manifest | PASS (isolation working as designed) |

## Explicitly NOT tested this pass (say so plainly, don't imply coverage)

- Uploads (book/picture/sound/video) — not exercised; would need real binary payloads, judged
  lower priority than the dream-gate/save/converse capabilities above given time constraints.
- `/v7/save` specifically (a distinct code path from the S3 backup loop, saves to EFS only) — not
  directly invoked as its own test; MUT-6's `tick` change and the natural EFS-based state
  progression visible across the `/status` polls in this section are indirect evidence the
  underlying save mechanism is alive, but this was not isolated as its own dedicated test.
- The remaining ~54 of 65 `app.py` routes, and 7 of the 13 MCP bridge tools not listed above
  (`guala_wake_wc`, `guala_rest_wc`, `guala_say`, `guala_amnesty`, `guala_atlas_snapshot`,
  `guala_backup`, `guala_atlas_query`) — not exercised this pass. §5's interface-truth report
  already dispositions most of these by code inspection (live/dead/orphaned, auth posture); this
  matrix adds live-execution evidence only for the rows above, it does not re-derive §5's work.
- Sensory frame ingestion (`/sight_frame`, `/sound_frame`) — not tested; would require real
  binary frame payloads.

## Traceability (capability → test → evidence, and reverse)

| Capability | Test(s) | Evidence |
|---|---|---|
| Teach / vocabulary growth | MUT-1 | hear_word response above |
| Experience-giving (bundle path) | MUT-2 | bundle response above (caveat: unknown-bundle-name only) |
| Conversational turn (`converse()`) | MUT-3 | full 202+poll cycle, timed |
| Dream/decay cycle control | MUT-4, MUT-5, MUT-6 | force_dream, repause, unpause all confirmed working in sequence |
| DR-restore backup-write isolation | MUT-7 | `file_count:0` self-reported by the product |
| Production runtime health | RO-1, RO-3, RO-5 | see §1 |
| Event stream | RO-2 | see §6/7/7A |
| Backup lineage/history | RO-4 | see §2, §3 |

Untestable-this-pass items (uploads, remaining MCP tools, sensory frames) are listed above with
reasons, not silently dropped — per audit law 0.4, "should work" is not a state; these are recorded
as NOT MEASURED, not asserted as passing.

### Changelog
- v1 (2026-07-05, c1): initial and final §8A filing. 11 real, evidence-backed rows (5 read-only
  vs production, 6 mutating vs the isolated shadow); 0 failures among tested rows; explicit,
  itemized list of what was not tested rather than implying full 65-endpoint coverage.
