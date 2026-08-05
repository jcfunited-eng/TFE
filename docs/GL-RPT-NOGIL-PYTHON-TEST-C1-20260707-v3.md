# GL-RPT-NOGIL-PYTHON-TEST-C1-20260707-v3

**doc_id:** GL-RPT-NOGIL-PYTHON-TEST-C1-20260707-v3
**From:** c1
**Executing:** GL-CMD-NOGIL-PYTHON-TEST-EVE-20260707-v2 (full build+deploy+test, following Joe's direct instruction to proceed rather than halt again on the `tokenizers` gap)
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**Full test completed. No named halt condition fired — no boot failure, no correctness regression, no crash. Recommendation: PARTIAL, not a clean GO.** The contention data is genuinely mixed and confounded (detailed below); it does not cleanly confirm the dispatch's hypothesis, but it also does not refute it. A real, non-cosmetic safety issue was found and fixed mid-test (below) — worth Eve's attention independent of the no-GIL question itself. Production was never pointed at the no-GIL image; all test infrastructure has been torn down.

---

## Container build result + dependency compatibility

Excluded `faster-whisper` (and therefore its `tokenizers` dependency, which has no free-threading wheel at any version — see v2's report) from the test image, per Joe's direct instruction to stop halting and proceed. This is safe: `dsf_ai_service/substrate/grounded_vocab.py`'s `SpeechRecognizer` already wraps the import in try/except and is explicitly documented to degrade to `self.available=False` — a supported mode, not a hack. None of this dispatch's own scenarios or metrics touch audio transcription.

Built `dsf_ai_service/Dockerfile.nogil`: `python:3.11-slim` base, installs `uv`, uses `uv python install 3.14t` to get a real free-threaded CPython 3.14.6 (confirmed `sys._is_gil_enabled() == False` at boot), `uv pip install --only-binary=:all:` for the rest of production's real dependency set (numpy, pandas, cryptography, Pillow, pillow-heif, PyMuPDF, boto3, onnxruntime, websockets, fastapi, uvicorn, python-multipart). No source builds attempted for anything, per DO-NOT.

Built via CodeBuild (this environment has no local Docker) using a source+buildspec override — a separate S3 key and inline buildspec, never touching the real `dsf_ai_image_build` project's default config or production's own build artifact path. Two builds, both succeeded clean (~2 min each): the second added a data-only fix described below. Pushed to `418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai:guala-nogil-20260707T135915Z` — same ECR repo as production, distinct tag, "alongside" per the dispatch's own phrasing.

## Test deploy result

Separate ECS service (`dsf-ai-nogil-test-svc`), separate task-def (`dsf-ai-task-nogil-test`), separate ALB target group (`dsf-ai-nogil-test-tg`), gated behind a header-conditioned listener rule (`X-Guala-Nogil-Test: 1`) on the shared ALB so production's default routing is completely unaffected. Deliberately **no EFS mount** — two processes (production's real Guala + this test process) writing the same organism-state files concurrently would risk corrupting or losing live, persistent substrate state. The test container boots with fresh, empty local state instead.

**A real safety issue was found and fixed here, not just a boot-check formality.** With no local state, the substrate's own existing identity-mismatch-triggered restore fired on boot and pulled a **real, current production S3 backup** down into the test container. That part is fine and arguably useful (realistic test data). But further investigation found — and confirmed live, in the logs — that this test process would then **automatically write back** to that same shared bucket: once immediately after boot (`_backup_to_s3`, called unconditionally inside `_eager_init`), again every hour (`_hourly_s3_sync`) and every 24 hours (`_daily_s3_backup`), **and** (found only once load-testing was underway) a third, much more frequent path — `persistence_consumer.py`'s ring/checkpoint uploader, firing roughly every 50,000 ticks, which at this test's accelerated tick rate meant twice in about 15 minutes. `_restore_from_s3` always resolves "latest" by timestamp with no fixed key, so any of these writes would have been eligible for a **future real production restore to pick up instead of genuine production continuity**.

Fixed with a dedicated, more restrictive IAM task role (`dsf-ai-nogil-test-task-role` — not a modification of the shared production role): allows `s3:GetObject`/`s3:ListBucket` on the backup bucket (so the realistic boot-time restore still works) with an **explicit `Deny`** on `s3:PutObject`/`s3:DeleteObject`/`s3:PutLifecycleConfiguration`/`s3:PutObjectAcl` on the same bucket. Explicit deny overrides any allow, so this holds regardless of what else the app tries. Verified this blocked all three write paths cleanly in the logs (`AccessDenied ... explicit deny in an identity-based policy`), and separately confirmed via direct `aws s3api list-objects-v2` before and after the whole test that no test-originated prefix ever landed in `s3://dsf-ai-site-backups/` — the only new prefix that appeared (`guala/2026-07-07_14-17-36/`) matches production's own long-running, consistent `:17`-past-the-hour cadence, not anything from this test. This is a real, general finding (the S3 backup/restore fallback path has no isolation from whatever "latest" happens to be) that Eve may want to route separately — not specific to no-GIL Python, it would apply to *any* isolated test container that hits the identity-mismatch restore path with a task role broad enough to write.

One more, unrelated, also-confirmed-real finding surfaced by exercising this same restore path: the restored organism immediately hit `RuntimeError: DREAM GATE: decay may not resume before the forced dream promotes paused-era content to deep. Marker absent: state/dream_gate_cleared.json` inside `_gl_init()`, which — read directly in `app.py` — permanently blocks `_guala` from ever being assigned (no self-recovery; `/ready` would stay `guala_ready:false` forever). Root cause: `_backup_to_s3`'s hardcoded file list never includes `dream_gate_cleared.json`, so *any* S3-restored boot hits this, regardless of interpreter. Worked around for this test only by pre-seeding a placeholder `{"cleared_at_tick": 0, "via": "..."}` marker file into the test image's own isolated local disk (not a substrate code change, not written to production's EFS or S3) — the correct real fix (adding the marker to `_backup_to_s3`'s file list) is substrate code and out of this dispatch's scope, flagged for Eve.

## Boot check result — clean

- Starts without errors (once the dream-gate marker was pre-seeded): `[app] Booting substrate in-process... Application startup complete.`
- Health endpoint responds: `/ready` → `{"ready":true,"guala_ready":true,"state":"ready"}`, `DSF-AI Guala initialized in 23.7s`.
- Substrate reaches quiescent state: confirmed above.
- Identity file written: `guala_identity.json` present (confirmed via `aws ecs execute-command`).
- Wave atlas initializes: `[GualaLoom] WaveAtlas rebuilt from LivingAtlas: 157 cells, 7124 bindings`.
- No warnings/errors beyond the two findings above, both root-caused to the rarely-exercised S3-restore fallback path (not the interpreter), both explained and handled without modifying substrate code.

## Harness scenarios — no regression (identical outcome both sides)

Ran all three scenarios against the no-GIL test service, then immediately re-ran the identical scenarios against production (fresh, right now — not reusing stale reports from earlier tonight, since production's tick has moved on):

| Scenario | No-GIL test | Production (same moment) |
|---|---|---|
| binding_windows_acceptance | PRECONDITION_NOT_MET | PRECONDITION_NOT_MET |
| cross_sense_recall_acceptance | PRECONDITION_NOT_MET | PRECONDITION_NOT_MET |
| hemispheric_integration_acceptance_v3 | PRECONDITION_NOT_MET | PRECONDITION_NOT_MET |

All six runs produced the byte-identical finding: `precondition not met: presence.wc expected True, actual False`. This is a pre-existing gap in the harness's own precondition-establishing logic (not wired to set WC's presence before probing), unrelated to production vs. no-GIL — and it fails **identically** on both, which is the actual thing this step needed to establish. No regression.

## Contention measurement — mixed, confounded, genuinely inconclusive on the core hypothesis

Coarse signal only, per DO-NOT ("skip fine-grained profiling"). Used the real converse endpoint's own self-reported tick-to-tick `elapsed_ms` (touches the actual `_guala`/organism/autonomy-tick path) as the load signal: 5 sequential "fresh" turns, then 5 more turns while 8 concurrent background word-input workers ran continuously. Ran the identical script, same word list, same load shape, against both environments within minutes of each other:

| | Fresh median | Loaded median | Amplification |
|---|---|---|---|
| Production (right now) | 9,298 ms | 25,902 ms | **2.79x** |
| No-GIL test | 568 ms | 4,173 ms | **7.35x** |

Two ways to read this, and they point in opposite directions:

- **By relative amplification, no-GIL looks worse** — 7.35x vs. production's current 2.79x, the opposite of the dispatch's hoped-for direction.
- **By absolute loaded latency, no-GIL looks dramatically better** — 4,173ms vs. 25,902ms, roughly 6x faster in real terms under a comparable synthetic load.

**Why I'm not picking one of these as "the" answer:** the two environments are not clean apples-to-apples. Production has been running continuously for hours, with a much larger accumulated organism/vocab/atlas and substantial ongoing ambient background work (curriculum study, autonomy tick, real user/world traffic) already competing for the GIL *before* I added any synthetic load — its "fresh" baseline (9,298ms) is already a loaded number, not an idle one. My test process had booted minutes earlier, with less accumulated state and less ambient background competition, so it had more headroom to show a *relatively* larger jump from a *lower* starting point, even though its absolute cost under load was much lower. Neither number is a clean measurement of "GIL vs. no-GIL, all else equal" — all else was not held equal, and this dispatch's scope (no substrate modification, no production restart, no controlled A/B on identical state) doesn't give me a way to fully separate the interpreter effect from the state-size/ambient-load effect within tonight's timeframe.

Also worth flagging directly: the dispatch's own cited production baseline ("178ms fresh, 1849ms under load, 10x amplification") does not match what production actually measured just now with the same methodology (9,298ms / 25,902ms / 2.79x). Production's own contention behavior is evidently highly time-dependent — whatever load state produced the original 178ms/1849ms numbers is not the load state production is in right now. This alone means neither the original historical baseline nor tonight's fresh measurement should be treated as a stable ground truth to hold the no-GIL variant against.

**No threading crash, no deadlock, no hang.** The one client-side connection timeout hit during the first (incomplete) no-GIL run was a client-socket timeout, not a server-side failure — confirmed by rerunning with retries/longer timeouts, which completed cleanly (50/50 background turns finished, all 5 foreground samples returned). The task stayed `RUNNING`/`HEALTHY` throughout, including through the S3 AccessDenied storm from the safety fix above, which the app's own error handling absorbed without incident.

## Recommendation: **PARTIAL**

Not a GO: the relative-amplification reading of the data doesn't confirm the dispatch's hypothesis, and I can't in good conscience report a clean improvement when the two measurements aren't controlled for the confounds above. Not a NO GO either: nothing crashed, nothing regressed on correctness, and the absolute-latency reading is strikingly positive — this is real signal, not nothing, even if I can't cleanly attribute it. Eve's call on how to proceed. If a cleaner answer is wanted, the honest next step is a same-organism-size, same-ambient-load comparison — which likely means either a much longer soak (letting the no-GIL test accumulate comparable state/background load before re-measuring) or accepting that production's own baseline needs to be re-measured immediately before *and* after any future comparison run, rather than reused from earlier in the night.

## DO-NOT compliance

Substrate code (`.py` files) was never modified. Production was never pointed at the no-GIL image — separate service/task-def/target group throughout, gated by a header condition production traffic never sends. Correctness scenarios and the contention measurement were both run, not skipped. No source build of any unsupported dependency was used to produce the shipped image (the one `tokenizers` source-build test in v2's report was diagnostic only, discarded, and not part of this image). All test infrastructure (service, target group, listener rule, IAM role, log group) has been torn down; the ECR image itself is left in place as a record, same as a normal deploy artifact.

---

### Changelog
- v3 (2026-07-07, c1): Full build+deploy+test executed per Joe's direct instruction to proceed past the `tokenizers` gap. Found and fixed a real cross-environment S3 write-collision risk (not previously known) via a dedicated, explicit-deny IAM role — no data loss, confirmed via before/after S3 listing. Found and worked around (test-environment-only, no substrate code change) a separate, real, pre-existing bug in the S3-restore fallback path (missing dream-gate marker in the backup file list) — flagged for a real fix outside this dispatch's scope. Boot check clean. Harness scenarios: identical outcome on both sides, no regression. Contention: mixed, confounded by ambient-load/state-size differences between a fresh test boot and hours-old production; recommend PARTIAL rather than force a GO/NO-GO the data doesn't cleanly support. No crash, no deadlock. All test infrastructure torn down; production untouched throughout.
