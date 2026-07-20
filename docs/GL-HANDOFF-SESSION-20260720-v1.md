# GL-HANDOFF-SESSION-20260720-v1

Session handoff, overnight 2026-07-19 → morning 2026-07-20. Written at Joe's
request at ~08:00 local time when he needed to step away. Everything below is
either (a) verified live/shipped, or (b) explicitly marked as diagnosed-but-
not-fixed. Nothing in this doc should be read as "done" unless it says so.

## Live state as of this handoff

- HEAD: `e8f5f2886388c4c12160ff4ede03cf85d71efd52` — "fix(boot): checkpoint
  fast restore + eliminate the window store's duplicate chi index"
- Running task definition: `dsf-ai-task:698` on cluster `tfe-web-cluster`,
  service `dsf-ai-service-lb` — 1/1 running, 0 pending, stable.
- **`dsf_ai_service/substrate/window_manager.py` has an UNCOMMITTED change on
  disk right now** — the streaming rewrite of `_write_wal_checkpoint_locked`
  (see item 3 below). Do not lose this; it's tested but not yet in git.

## Shipped and verified this session

1. Voice-reply-door (`GL-FIX-VOICE-REPLY-DOOR-20260720`): recognized speech
   now triggers a real `converse()` reply instead of only updating
   memory/presence via `read_sentence()`. Live-confirmed via real
   `[voice-reply] ...s response_source=... committed=True` log lines.
2. Cognition meter rewritten to show only genuinely live-checked rows
   (`COGMETER_ROWS`), with the old ~25-row audit set moved into a collapsed
   `COGMETER_AUDIT_ARCHIVE` details panel, never presented as current state.
3. Boot checkpoint fast-path + chi-index elimination (commit `e8f5f28`):
   `LivingAtlas.window_ids_for_chis()` replaces the window store's own
   duplicate `_chi_index`; `RecallEngine` now requires an `atlas` and routes
   exclusively through it; boot restore passes `populate_chi_index=False`.
   Verified via 65+ targeted tests + full regression diff against baseline
   (see "Regression diff" below) — zero new failures caused by this change.
4. `dsf-ai.com` stale-frontend gap fixed: discovered mid-session that
   `dsf-ai.com`/`www.dsf-ai.com` are served from a **separate S3 + CloudFront
   deployment** (bucket `dsf-ai-site`, distribution `E17JT9XGBFU493`),
   completely disconnected from the ECS backend. A normal backend deploy
   never touches it. `gualaloom.html` was 2 days stale there. Fixed by
   `aws s3 cp` + CloudFront invalidation; verified live on the real domain.
   **Any future static-asset change must repeat this sync — see full writeup
   in Claude's memory file `guala-dual-frontend-deployment-paths-20260720`.**
5. EFS storage cost alarm (`guala-efs-storage-runaway`): root-caused to
   orphaned `generations/` backup snapshots from the crash-loop (not the
   chi-index work itself), ~19GB freed by deleting 2 confirmed-oversized,
   non-current generations. Alarm confirmed back to `OK` at 2026-07-20T12:20:28Z.
6. OOM crash-loop (pre-existing, proven via CloudWatch cross-boot comparison,
   not caused by tonight's code): mitigated with a memory/CPU bump to
   `dsf-ai-task:698` (40GB/8vCPU). Stable for hours since.

### Regression diff (truly_final_regression_20260720.txt vs base_failed_sorted2.txt)

Raw suite: 152 failed, 903 passed, 105 errors — looks alarming out of context
but 252 of 256 baseline failures are pre-existing, dominated by
`tests/glew_runtime/*` (246 of 256), a separate, already-known-broken
subsystem unrelated to tonight's work. Actual diff:

- 5 "new" failures — all pre-existing/unrelated, confirmed to fail identically
  on a `git stash`-reverted baseline: 3x
  `dsf_ai_service/tests/test_give_experience_cross_modal_recall.py`, 2x
  `dsf_ai_service/tests/test_teacher_correction_gateway_routing.py`.
- 4 tests flipped failing→passing, **unexplained, not investigated**:
  `tests/glew_runtime/test_genesis.py::test_old_proposed_full_profile_is_rejected_before_mutation`,
  `tests/glew_runtime/test_language_weave_profile.py::test_profile_names_governing_spec`,
  `tests/glew_runtime/test_language_weave_profile.py::test_prohibitions_list_matches_governing_spec_section_6`,
  `tests/test_emission_wall_budget_retime.py::test_1_default_budget_is_3s_not_1point5s`.
  Don't assume these are actually fixed — could be flaky/order-dependent.

## OPEN — diagnosed but NOT fixed, needs next session's attention

### 1. `/sound_frame` intermittent gateway-timeout (found 08:00 this morning, NOT fixed)

**Symptom Joe reported**: voice produces no responses, "hearing likes to fail
from time to time," browser shows `raw sound failed: Unexpected token '<',
"<html> <h"... is not valid JSON`.

**Root cause, evidence-backed**: the frontend calls `POST
https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com/sound_frame` (HTTP
API Gateway `dsf-ai-api`, id `3d6toi0gw0`, fronting the ECS backend). AWS
HTTP APIs have a **hard, non-configurable 30-second maximum integration
timeout**. CloudWatch `IntegrationLatency` for this API shows repeated spikes
pinned almost exactly at the ceiling in the last hour (`2026-07-20T12:12:00Z`
→ `30001` ms, `12:17:00Z` → `29710` ms, `12:22:00Z` → `24243` ms), correlated
with `5XXError` counts in the same windows (1, 4, 3, 2, 4 per 5-min bucket —
intermittent, not constant, matching Joe's "from time to time").

Meanwhile the backend's own STT wait, `_speech_result_wall_timeout()` in
`app.py:224`, resolves to **90 seconds** (`3.0 × SPEECH_WORKER_REQUEST_TIMEOUT_S`,
default 30s env var). That 90s "belt-and-braces" timeout was clearly designed
to let a wedged STT worker degrade gracefully to a typed
`SpeechRecognitionUnavailable` JSON response — but API Gateway kills the
connection at 30s, **before the backend's own graceful path ever gets to
run**, and returns its own timeout response instead. That's the HTML/non-JSON
body the frontend's `.json()` call chokes on.

Direct endpoint probes at the time of writing were healthy (`/sound_frame`
with a garbage payload returned clean JSON in ~200ms; `/health` clean JSON) —
this is a real but intermittent condition, triggered when actual transcription
(or queueing behind it — worth checking `_run_lifecycle_executor`'s and
`_speech_recognition_executor`'s worker-pool sizes for a compounding-backlog
angle, not yet checked) crosses ~30s.

**Not fixed, on purpose** — this needs a clear-headed look, not an 8am
guess, per this session's own established discipline on production timeout/
memory changes. Smallest, lowest-risk candidate fix identified but NOT
applied: tighten `SPEECH_WORKER_REQUEST_TIMEOUT_S` (or the 3x multiplier in
`_speech_result_wall_timeout()`) so the backend's own typed-unavailable path
wins the race under ~28s, comfortably inside API Gateway's 30s wall — turns a
raw HTML gateway timeout into the clean, already-handled
`spoken_word_recognition.status == "error"` UI path. This does not address
*why* transcription is occasionally slow — only makes the failure mode honest
instead of broken. Worth checking current ECS CPU/memory pressure and
`_run_lifecycle_executor`/`_speech_recognition_executor` pool sizes as the
next diagnostic step before touching the timeout value.

### 2. Speech transcription accuracy (~87% per Joe's own estimate)

Not investigated this session — flagged by Joe directly on 2026-07-20. This
is a model/quality tuning question (Whisper config, audio chunking, or
similar), not a bug with a clear repro. Needs its own investigation, separate
from the timeout issue above.

### 3. Checkpoint-write streaming memory fix — tested, NOT deployed

`_write_wal_checkpoint_locked` in `window_manager.py` was rewritten to stream
every field directly to the file handle (no full-copy intermediates) after
the original implementation contributed to a real production OOM during
`/debug/wal_compact`. Verified against the full existing test suite (10/10 in
`tests/test_wal_boot_checkpoint_fast_path.py`) plus new standalone scale
tests at N=50,000 and N=300,000 records (N=300,000: 457.5MB peak delta,
bounded, not runaway). **This change is sitting uncommitted on disk in
`dsf_ai_service/substrate/window_manager.py` right now.** Do not run
`/debug/wal_compact` against production again until this is committed,
deployed, and re-validated live — that was an explicit promise made to Joe
this session.

### 4. `generations/` backup auto-pruning — not investigated

The EFS alarm (item 5 above) was caused in part by atomic-state backup
snapshots under `/app/guala/active/generations/` accumulating during the
crash-loop with no apparent auto-pruning. Not yet confirmed whether pruning
ever happens in normal (non-crash-loop) operation. If it doesn't, this exact
disk/cost problem can recur on any future crash-loop. Worth a real look.

## Process note for whoever picks this up

Tonight included one real process failure worth not repeating: verifying a
frontend fix against the ALB DNS name directly instead of `dsf-ai.com` (the
domain actually used), which produced a confident but wrong "it's fixed"
report. Always verify against the exact real domain/URL, not a substitute
endpoint that happens to be easier to reach. See memory file
`guala-dual-frontend-deployment-paths-20260720` for the full architecture
gotcha.
