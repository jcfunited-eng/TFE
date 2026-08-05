> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-AUDIT-SEC4-CODE-TRUTH-C1-20260705-v1

doc_id: GL-AUDIT-SEC4-CODE-TRUTH-C1-20260705-v1
Scope: §4 ("Code truth at the running SHA") of
GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2. Read-only. No production
code, config, or behavior was changed. All work performed inside the
isolated worktree `audit-c1-210-gl` (branch `worktree-audit-c1-210-gl`,
rooted on `guala-live`).

**Audited SHA**: `168ef1bde3717e52efb85b894103de047e942617` — confirmed
[EV] identical in application code to this worktree's HEAD
(`a9dff78`): `git diff --stat 168ef1b..a9dff78` shows only 4 added files,
all under `docs/`, 0 changes under `dsf_ai_service/` or `tools/`.

**Generator script**: `tools/audit/sec4_code_truth.py` (found pre-existing
from a prior killed attempt; reviewed, judged sound, reused as-is — no
edits). Re-run any subcommand with `python3 tools/audit/sec4_code_truth.py
<env|deadcode|stubs|todo|exceptpass|constants|all> --root <dir>`. Per audit
law 0.2, every raw list below was produced by this script or by a
supplementary grep documented inline (the script has known blind spots,
noted where they mattered — see §2 and §1).

---

## SUMMARY (failures / absences first)

1. **Confirmed instance of "recent fix landed in dead code."** Commit
   `6d15797` (2026-07-05 06:14:18, "apply P2/P3 to the dormant non-phased
   converse() fallback too") patches the *non-phased* body of
   `Guala.converse()` in `gualaloom_v5_engine.py` (lines ~2386-2469).
   Production sets `CONVERSE_PHASED=1`, and line 2364 unconditionally
   returns via `_converse_phased(...)` whenever that flag is `"1"` — so
   the code `6d15797` touched **never executes in production**. The fix
   is not wrong, it is simply inert; it only matters if `CONVERSE_PHASED`
   is ever flipped back to `0`. [EV]
2. **A four-part cognition subsystem is wired live but entirely inert.**
   `_converse_phased` (the live path) calls `run_hemisphere_updates()`
   every turn (`gualaloom_v5_engine.py:2742`), but all four hemisphere
   flags (`HEMI_PR_ENABLED`, `HEMI_EP_ENABLED`, `HEMI_SC_ENABLED`,
   `HEMI_GP_ENABLED`) default to `"0"` and none appear in production's
   env — so every sub-block inside `run_hemisphere_updates` is skipped,
   every turn, silently. Substantial feature work (commits `2564f9b`,
   `54a55b2`, `fad6264`, `9801ecd`, 2026-06-19) built and instrumented
   this and it has produced zero live effect since. [EV]
3. **Two whole functions plus their env vars are 100% dead**, and this
   was already partially self-documented by the team two days before this
   audit. `substrate_runner.boot_substrate()` and
   `start_background_loops()` have **zero callers** anywhere in
   `dsf_ai_service` (confirmed by direct grep). `app.py`'s own comment
   (lines 1383-1391) says so explicitly, citing
   `GL-RPT-FLOOD-HUNT-C1-20260703-156-v1`. A consequence not previously
   flagged: `_start_lookup_loop()` and `_start_world_feed_loop()` (also
   dead, since nothing in the live boot path calls them) are the *only*
   readers of `LOOKUP_INTERVAL_SEC` and `WORLD_FEED_INTERVAL_SEC` — both
   **explicitly set in the production task-definition** (900 and 600
   respectively) but **currently inert**; real world-feed/lookup cadence
   in production is instead governed by `STUDY_INTERLEAVE_EVERY=2` via
   `CurriculumScheduler.interleave_fns`, wired inline in `app.py`. [EV]
4. **One live, externally-reachable endpoint is permanently broken in
   the current deployment mode.** `GET
   /api/v1/curriculum/corpus_status/{corpus_id}` (`app.py:4370`) always
   returns HTTP 501 "not implemented for local mode" because
   `_is_remote()` (`app.py:215`) is `SUBSTRATE_MODE == "remote"`, and
   production's `SUBSTRATE_MODE=embedded`. [EV]
5. **Test suite, final: 134 collected + 1 uncollectable → 6 failed, 128
   passed, 1 collection error, 967.30s (16m07s) wall time.** Of the 3
   named known failures, only 2 reproduce. `test_t7_cross_modal` **now
   PASSES** (contradicts the pre-audit claim — likely fixed by 07-03's
   `e672331`, "fix: T7 partial-cue crash"). `test_t8_noise_robustness`
   **FAILS** (noise-0.30 accuracy 8.0%, floor is ≥45.0%).
   `test_t11_substrate_true` **FAILS** (stale architectural invariant,
   not a regression — see §7.1). **4 NEW failures not named in the
   dispatch**, two of them touching save reliability directly:
   - `test_autonomous_emission.py` fails to even **collect**
     (`ImportError: cannot import name 'SEED_VOCAB'` — dead since
     2026-06-14, 3+ weeks, see §7).
   - `test_folding_engaged.py::test_t3_corpus_growth` — **zero of 8
     hemispheres grew** across 242 delivered words in an isolated
     pipeline ("Folding not operating during experience").
   - `test_folding_engaged.py::test_t8_substrate_true` — same stale-
     invariant class as `test_t11_substrate_true`.
   - `test_save_hooks.py::test_should_save_bypass_includes_
     activity_ended_and_backstop` — `_should_save('activity_ended')`
     returns `False`, expected `True`. **Worth escalating**: this is
     the exact bypass list a prior incident depended on (memory:
     "EFS rename race silently dropped saves... last_save_tick=0 at
     boot means saves broken").
   - `test_save_hooks.py::test_s3_enqueue_rate_limit_releases_
     after_interval` — after simulating 601s elapsed, the rate limiter
     was expected to release and re-enqueue (1→2 calls) but stayed at
     1. Same file/subsystem as the previous failure.
   See §7 for full detail and captured assertion text on every failure.
6. **Pre-audit numbers**: 65 endpoints ✓ exact match. 34 except:pass ✓
   exact match, but only under a specific narrow scope (see §5) — the
   real total across the whole service is 90. 27 env flags does **not**
   hold — 32 vars are genuinely set in prod (matching the dispatch
   author's own recount) and 65 distinct names are read in code. 24
   constants could not be exactly reproduced under any obvious scope —
   candidates range from 22 to 62 depending on file scope; likely a
   hand-curated subjective list, not a mechanically reproducible number.
   3 stub markers ✓ matches after removing 2 docstring-only mentions
   from the raw 5 regex hits. 14 state files: **not measured** in this
   section (belongs to §3, EFS/state truth, out of §4's scope).

---

## 1. Env-gated reachability map

**Method** [EV]: `python3 tools/audit/sec4_code_truth.py env --root
dsf_ai_service` greps every `os.environ.get(...)` / `os.getenv(...)` /
`os.environ[...]` / `os.environ.setdefault(...)` call site on a single
line. Result: **200 call sites, 65 distinct env var names** in
`dsf_ai_service`. Full raw list is reproducible by that command; excerpts
below.

**Known method gap** (found by manual follow-up, not by the script):
the script only matches calls where the quoted var name is on the *same
physical line* as `os.environ.get(`. Three production-set vars are read
via a call that spans multiple lines or goes through a wrapper, and were
**missed** by the mechanical scan:
- `WHISPER_MODEL_PATH`, `YOLO_MODEL_PATH` —
  `dsf_ai_service/substrate/grounded_vocab_integration.py:22-25`, the
  `os.environ.get(\n    "NAME", default)` call wraps onto a second line.
- `CURRICULUM_INTERVAL_SEC` — `dsf_ai_service/loom_model/
  curriculum_scheduler.py:76`, read via a local `_env_int("CURRICULUM_
  INTERVAL_SEC", 180)` helper, not a direct `os.environ.get(...)` call.

Found by: `grep -rn "CURRICULUM_INTERVAL_SEC\|WHISPER_MODEL_PATH\|
YOLO_MODEL_PATH" --include="*.py" --include="*.sh" .` [EV]

`PYTHONUNBUFFERED` (set in prod) is never read via `os.environ` in this
code at all — expected, it's a CPython interpreter flag consumed before
the interpreter starts, not an application-level gate. Not a defect.

**Net result**: of the 32 vars actually set in production (28 config/
flag vars + 4 API keys, per the ground-truth task-def), all 32 are
consumed by the application in some form except `PYTHONUNBUFFERED`
(interpreter-level, as above). No prod env var is a pure orphan — but
(per finding #3 above) two of them, `LOOKUP_INTERVAL_SEC` and
`WORLD_FEED_INTERVAL_SEC`, are read only inside functions that are never
called, so they are consumed-but-inert.

### 1.1 The six claimed "load-bearing" flags — individually resolved

| Flag | Prod value | Gate site | Resolution |
|---|---|---|---|
| `CONVERSE_PHASED` | `1` | `gualaloom_v5_engine.py:2364` `if os.environ.get("CONVERSE_PHASED","0")=="1": return self._converse_phased(...)` | **LIVE**: `_converse_phased` (lines 2550+). Default-branch (single-lock body, lines 2386-2469) is **DEAD** — see Summary #1. [EV] |
| `EMISSION_DYNAMICS` | `1` | `gualaloom_v5_engine.py:3134` `if os.environ.get("EMISSION_DYNAMICS","0")=="1" and mode=="grandurun":` | **LIVE** (both conjuncts true: `EMISSION_MODE=grandurun` too). [EV] |
| `EMISSION_MODE` | `grandurun` | `gualaloom_v5_engine.py:3126` `mode = mode_override or os.environ.get("EMISSION_MODE","topk")` | **LIVE=grandurun**; default `"topk"` path is DEAD in prod (never taken since the var is explicitly set). [EV] |
| `AUTONOMY_PHASED` | `0` | `gualaloom_v5_engine.py:5122` `if os.environ.get("AUTONOMY_PHASED","0")=="1":` | Explicit `0` matches the coded default. Phased-autonomy branch is **DEAD**; legacy (non-phased) autonomy path is **LIVE**. Not obviously a bug — no comment marks this deliberate the way `CURRICULUM_AUTOSTART`'s is, so flagged for Eve/Joe's routing rather than asserted intentional. [EV] |
| `WAVE_ATLAS_ENABLED` | `1` | `gualaloom_v5_engine.py:1492` `if os.environ.get("WAVE_ATLAS_ENABLED")=="1":` (no string default; `None` if unset) | **LIVE**: `WaveAtlas` instantiated, `atlas._wave_atlas` set. [EV] |
| `GRANDURUN_SPIN_VECTOR` | `1` | `gualaloom_v5_engine.py:3247-3249` (see below) | **LIVE, and subtly aliased** — see 1.2. [EV] |

### 1.2 `GRANDURUN_SPIN_VECTOR` / `GRANDURUN_LEGACY_8D` — a gotcha worth flagging

```python
# gualaloom_v5_engine.py:3247-3249
use_legacy_8d = _os.environ.get("GRANDURUN_LEGACY_8D",
                 _os.environ.get("GRANDURUN_SPIN_VECTOR", "0")) == "1"
```
The comment above this reads: *"GL-CMD-DYNAMICS-EMISSION-RESTORATION:
renamed from GRANDURUN_SPIN_VECTOR"* — implying `GRANDURUN_LEGACY_8D` is
the new, primary name and `GRANDURUN_SPIN_VECTOR` is a deprecated
alias. In fact the **fallback chain runs the other way**: Python
evaluates the inner `.get("GRANDURUN_SPIN_VECTOR", "0")` first regardless
of whether `GRANDURUN_LEGACY_8D` is set, so **setting only
`GRANDURUN_SPIN_VECTOR=1` (as production does) still fully activates the
"legacy" path** — `GRANDURUN_LEGACY_8D` unset means its own `.get()`
returns the already-computed fallback string, which is `"1"`. Net:
`use_legacy_8d = True` in production right now, so `_emit_grandurun_vector`
(the 8D vector path) is **LIVE**, not the newer scalar/multi-anchor path
the surrounding comments (`GL-CMD-COMPOSER-MULTIANCHOR-43`) imply is
primary. **Good news**: the memory-recorded perf fix
("grandurun_semantic_neighborhood_fixed", task `:324`) targeted
`_emit_grandurun_vector` directly — it landed in the branch that is
actually live. Not a dead-code case, but the naming/comment is
misleading enough that a future engineer could set `GRANDURUN_LEGACY_8D=0`
expecting to kill the vector path and be surprised it's still active via
the `SPIN_VECTOR` fallback. [EV]

### 1.3 Full flag table (all 65 distinct names read in `dsf_ai_service`)

Legend: **Set-Live** = explicitly set in prod, gates/feeds a live branch.
**Set-Inert** = explicitly set in prod but the reading code path is dead
(see #3). **Default-On** = not set in prod, coded default enables the
feature. **Default-Off** = not set in prod, coded default disables the
feature. **Config** = not a boolean gate, a plain value (path/URL/int).

| Var | Prod? | Default | Class | Note |
|---|---|---|---|---|
| DECAY_PAUSED | `0` | `"0"` | Set-Live | 23 read sites; "not paused" branch live everywhere |
| CONVERSE_PHASED | `1` | `"0"` | Set-Live | §1.1 |
| EMISSION_DYNAMICS | `1` | `"0"` | Set-Live | §1.1 |
| EMISSION_MODE | `grandurun` | `"topk"` | Set-Live | §1.1 |
| EMISSION_DYNAMICS_TICKS | `80` | `"80"` | Config | matches default, explicit anyway |
| GRANDURUN_SPIN_VECTOR | `1` | `"0"` | Set-Live | §1.2 |
| WAVE_ATLAS_ENABLED | `1` | unset→off | Set-Live | §1.1 |
| AUTONOMY_PHASED | `0` | `"0"` | Set-Inert-by-design? | §1.1, phased branch dead |
| WORLD_FEEDS | `1` | `"1"` | Set-Live | gates `_world_feed_once` inclusion in curriculum interleave |
| LOOKUP_AUTONOMOUS | `1` | `"0"` | Set-Live | gates `_lookup_once` inclusion in curriculum interleave |
| DREAM_CYCLE_PHASED | `1` | `"0"` | Set-Live | 3 sites in gualaloom_v5_engine.py |
| STUDY_INTERLEAVE_EVERY | `2` | `"3"` | Config | overrides default |
| WORLD_FEED_INTERVAL_SEC | `600` | `"600"` | **Set-Inert** | only read inside dead `_start_world_feed_loop` (Summary #3) |
| LOOKUP_INTERVAL_SEC | `900` | `"600"` | **Set-Inert** | only read inside dead `_start_lookup_loop` (Summary #3) |
| CURRICULUM_AUTOSTART | `0` | `"0"` | Set-Inert-by-design | explicitly retired per `GL-CMD-DENSITY-RETIRE-109`, comment confirms |
| CURRICULUM_ORCHESTRATOR_INTERVAL_SEC | `5` | `"5"` | Config | feeds the (retired/off) 65-A orchestrator only |
| CURRICULUM_SEED_PATH | `/app/tools/curriculum_seed.json` | same | Config | ditto |
| CURRICULUM_SUBSTRATE_URL | `http://localhost:8080` | same | Config | ditto |
| CURRICULUM_CHUNK_SIZE | `30` | `"30"` | Config | live, feeds `_curriculum_feed_chunk` chunk cap |
| CURRICULUM_INTERVAL_SEC | `120` | `180` | Config | live, `CurriculumScheduler.interval_sec` (§1, method-gap var) |
| SUBSTRATE_MODE | `embedded` | `"embedded"` | Set-Live | gates `_is_remote()`, see §4 stub finding |
| SUBSTRATE_HEARTBEAT | `/app/state/substrate.alive` | `/shared/...` | Config | |
| STATE_DIR | `/app/state` | `/mnt/efs/guala` | Config | overridden explicitly |
| ORGAN_BRAIN_URL | `http://localhost:8090` | same | Config | matches default |
| WHISPER_MODEL_PATH | `tiny` | `/app/models/whisper-tiny` | Config | **method-gap var** (§1); note prod value `"tiny"` doesn't look like a path — see below |
| YOLO_MODEL_PATH | `/app/yolov8n.onnx` | `/app/models/yolov8n.onnx` | Config | **method-gap var** (§1) |
| GUALALOOM_API_KEY | (secret) | `""` | Config/auth | bearer-token check, not a feature flag |
| ANTHROPIC_API_KEY / OPENAI_API_KEY / TAVILY_API_KEY / YOUTUBE_API_KEY | (secrets, present) | unset | Set-Live (presence-gated) | e.g. `organ_brain_service.py:835` skips Tavily lookup if key absent; prod has it |
| PYTHONUNBUFFERED | `1` | n/a | Config (interpreter) | not read by app code, expected |
| LATERAL_INHIBITION_ENABLED | unset | `"0"` | **Default-Off** | `assemblage.py:270,287(and),310` — mode-mode competition energy penalty OFF |
| RICH_SENSORY_INPUT | unset | `"0"` | **Default-Off** | `gualaloom_v5_engine.py:3916` — emission Stage-1 candidate selection uses plain `_grandurun_select_candidates`, not `_rich_sensory_candidates` |
| DEEP_ATLAS_ENABLED | unset | `"1"` (`!= "0"`) | Default-On | `deep_atlas.py:39` |
| DEEP_PRIOR_ENABLED | unset | `"1"` (`!= "0"`) | Default-On | `deep_atlas.py:42` |
| HEMI_PR_ENABLED | unset | `"0"` | **Default-Off** | Summary #2 |
| HEMI_EP_ENABLED | unset | `"0"` | **Default-Off** | Summary #2 |
| HEMI_SC_ENABLED | unset | `"0"` | **Default-Off** | Summary #2 |
| HEMI_GP_ENABLED | unset | `"0"` | **Default-Off** | Summary #2 |
| GRANDURUN_LEGACY_8D | unset | see §1.2 | Set-Live (via fallback) | §1.2 |
| EMISSION_STRUCTURED_NOISE | unset | `"0"` | **Default-Off** | `assemblage.py:287` — introducing commit `140cfd8` self-tagged `[C2 FAIL]` |
| SELF_HEARING_ENABLED | unset | `"1"` (`=="0"` disables) | Default-On | `gualaloom_v5_engine.py:7141` |
| SELF_VOICE_AUDIO_ENABLED | unset | `"1"` (`=="0"` disables) | Default-On | `gualaloom_v5_engine.py:7207` |
| META_DECAY_ENABLED | unset | `"1"` (`!= "0"`) | Default-On | `gualaloom_v6_living_atlas.py:68` |
| VOICE_WHISPER | unset | `"0"` | Default-Off | `app.py:1670` — gates STT-derived text override for `joe_voice` source specifically |
| GUALA_GROWTH_LAW_LEGACY | unset | off | Default-Off (correct) | `embryo.py:448` — new experience-funded growth law is what's live, matches 07-05 feature work |
| GUALA_FORCE_SAVE | unset | off (guard triggers) | Config/safety | override switch for vocab-regression abort guard, correctly off |
| GUALA_FORCE_FRESH | unset | off (guard triggers) | Config/safety | override for "identity present but state vanished" abort, correctly off |
| GUALA_STATE_DIR | unset | `/app/state` | Config | used only by `organ_brain_service.py`; happens to match `STATE_DIR`'s prod value by coincidence of defaults — **two different var names for the same directory in two files**, worth a register line even though currently harmless |
| ORGAN_BRAIN_FULL_BOOT | unset | `"0"` | Default-Off | |
| ORGAN_BRAIN_RSS_LIMIT_MB | unset | `900` | Config | RSS circuit-breaker threshold, see §5 judgement |
| GUALA_S3_BACKUP_BUCKET / GUALA_S3_BACKUP_PREFIX | unset | `dsf-ai-site-backups` / `guala/auto` | Config | |
| GUALA_TZ_OFFSET | unset | `-5` | Config | |
| SLOW_DIV_OVERRIDE / DECAY_LAMBDA_OVERRIDE | unset | `0` (falsy, no override) | Config/safety | |
| GRANDURUN_TOPK | unset | `200` | Config | |
| EMISSION_WALL_BUDGET_S | unset | `1.5` | Config | |
| SCAFFOLD_RATE_CAP_PER_MIN | unset | `15` | Config | live, feeds `_scaffold_rate_cap_gate`, called from the live `_curriculum_feed_chunk` |
| BLOCK_CYCLE_SEC | unset | `3600` | Config | live, feeds `_current_block()`, called from the live `_curriculum_feed_chunk` (§1.4) |
| FORCE_S3_RESTORE | unset | off | Config/ops | manual override, boot-time |
| GIT_SHA | unset in this list (set separately as build metadata) | `"unknown"` | Config | informational, `/status` field |
| PYTHONHASHSEED | unset here | n/a | Config | only read by `whole_brain_168v3.py` test tool, warns if not pinned to `0` (memory note: capacity-probe reproducibility) |
| DSF_AI_SES_ROOT_KEY | unset | `dsf-ai-ses-root-key-v1-CHANGE-IN-PROD` | Config/secret | `kernel_runner.py:35` — **default literally says CHANGE-IN-PROD and it hasn't been**; flagged for the defects register, not fixed here |
| LOOKUP_MODEL | unset | `gpt-4o-mini` | Config | |
| COGNITION_OBSERVABLE | unset | falls through to code default | Config | `brain.py:52` |
| CURRICULUM_AUTONOMOUS | unset | `"1"` (enabled) | Default-On | `curriculum_scheduler.py:74`, separate from `CURRICULUM_AUTOSTART` (65-A, retired) — this is the book-curriculum's own enable switch, on by default |
| SUBSTRATE_SOCKET | unset | `/shared/substrate.sock` | Config | only relevant if `SUBSTRATE_MODE=remote`, which prod is not |

### 1.4 Cross-check: is the block-schedule gate (BLOCK_CYCLE_SEC) actually reachable?

Yes — verified by direct grep this audit: `_curriculum_feed_chunk` (the
function the live `CurriculumScheduler` actually calls, per `app.py`'s
`_gl_init()`) calls `_current_block()` at line 276 and
`_scaffold_rate_cap_gate()` at line 285. `_current_block()` reads
`BLOCK_CYCLE_SEC`. So this gate — despite living in the same file
(`substrate_runner.py`) as the confirmed-dead `boot_substrate()` — is
reachable through the live path, because `_curriculum_feed_chunk` is a
plain function object referenced independently from both places. This
matches the 07-03 self-report's own partial verdict ("G-151-1/5 PASS")
and the subsequent 07-05 B3 reconnect fix (`cac6684`). [EV]

### 1.5 External reachability: app.py's 65 routes vs the live 38-route API Gateway

**Method** [EV, read-only AWS query — `aws apigatewayv2 get-routes` /
`get-integrations`, both read-only, no state changed]:

```
aws apigatewayv2 get-apis --region us-east-1 --query "Items[?ApiId=='3d6toi0gw0']"
aws apigatewayv2 get-routes --api-id 3d6toi0gw0 --region us-east-1 --max-results 200
aws apigatewayv2 get-integrations --api-id 3d6toi0gw0 --region us-east-1
```

Confirmed **exactly 38 routes** on `3d6toi0gw0` (`dsf-ai-api`, HTTP API
type), matching the dispatch's ground truth exactly. Of the 38: 35 are
explicit paths, all with `HTTP_PROXY` integrations pointing directly at
`http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com<same-path>`
(i.e., a 1:1 passthrough to the ALB — confirmed by diffing every
integration's `IntegrationUri` against its `RouteKey`, all 35 match
exactly). One (`ANY /mcp`) also proxies to the same ALB but on the
`/mcp` path, which the ALB itself then routes to the **separate**
`gualaloom-bridge-svc` ECS service (per the dispatch's own ground
truth, not independently re-derived here). One (`POST /wc-relay`) is
`AWS_PROXY` to Lambda `wc-companion-relay`. One (`$default` catch-all
for anything unmatched) is `AWS_PROXY` to Lambda `dsf-ai-api` (same
name as the API itself — a Lambda, not the same as the ECS service).

**Diffing the 35 explicit ALB-backed routes against app.py's 65
`@app.*` decorators** (`grep -oE
"^@app\.(get|post|put|delete|patch|websocket)\(\"[^\"]+\""
dsf_ai_service/app.py`): all 35 external routes match an app.py route
exactly, path and method — **zero orphaned API Gateway routes** (nothing
externally exposed that doesn't exist in the code). The remaining
**30 of the 65 app.py routes have no explicit API Gateway entry**,
including `GET /health`, `GET /ready`, `GET /ready/guala`, `GET
/gualaloom` (the HTML page), `GET /` (root), all 4 `/api/v1/cluster*`
routes, the `websocket /events_stream` route, both teacher-feedback
routes, and 8 of the `/api/v1/gualaloom/admin/*` routes (e.g.
`atlas_surgery`, `compact_wave_atlas`, `migrate_wave_atlas`,
`restore_from_s3_prefix`, `force_reading`, `backfill_picture_titles`,
`backfill_sound_captions`, `backup_orchestrator/configure`).

**What this does and doesn't prove**: these 30 routes are not
*directly* proxied to the ALB by API Gateway, but they **may still be
reachable** through the `$default` catch-all, which goes to Lambda
`dsf-ai-api` — if that Lambda itself forwards arbitrary unmatched paths
to the ALB (a common HTTP-API-behind-Lambda pattern), all 30 would still
be externally reachable, just through one extra hop this section did
not trace. Confirming that requires reading the Lambda's own source
(`aws lambda get-function --function-name dsf-ai-api`), which is an AWS
resource outside `dsf_ai_service/`'s code and belongs more naturally to
§2 (AWS truth) or §5 (interface truth) — **not done here**, flagged
as the boundary of this section's evidence rather than asserted either
way. What **is** confirmed: the "65 endpoints" and "38 routes" are both
correct, simultaneously, because they're counting different things —
"65" is every FastAPI handler in the code, "38" is the distinct
API-Gateway-level route entries (which collapse admin/ops/health
surfaces behind one catch-all rather than listing each explicitly).
Neither number is wrong; treating them as needing to match would be the
actual error.

---

## 2. Dead-code inventory beyond env flags

**Method** [EV]: `python3 tools/audit/sec4_code_truth.py deadcode --root
dsf_ai_service` — AST-walks every top-level `def`/`class`, then does a
whole-repo `\bname\b` text count. A name with exactly 1 occurrence
(the definition itself) is a candidate. Raw result: **103 candidates**
out of 1738 top-level defs/classes scanned.

**Known false-positive class, found and filtered this audit**: 39 of
the 103 raw candidates are FastAPI route handlers (e.g.
`admin_amnesty`, `substrate_hear_word`, `gualaloom_events`) — they're
"called" by the ASGI framework via the `@app.get/post(...)` decorator,
never by direct name reference, so the script's own documented
limitation ("does not resolve... decorators registering by name")
applies exactly. Cross-checked by extracting all 65 `@app.*` decorated
function names and diffing against the candidate list:
`grep -c "^@app\.\(get\|post\|put\|delete\|patch\|websocket\)("
dsf_ai_service/app.py` → 65; 39 of those 65 also appear in the raw
dead-code list. **Filtered candidate count: 64.** [EV]

The remaining 64 still carry the script's other documented blind spots
(dynamic dispatch via `getattr`, string-built names, differently-aliased
imports) — this is a grep-based signal, not a call-graph, and should be
read as "worth a human look," not "proven dead." Two were spot-checked
and confirmed as **true positives**, one important enough to detail:

- **`substrate_runner.start_background_loops()` (line 3350) and
  `substrate_runner.boot_substrate()` (line 553): CONFIRMED dead**, zero
  callers anywhere in `dsf_ai_service` (`grep -rn
  "start_background_loops\|boot_substrate(" dsf_ai_service --include=
  "*.py"` returns only the two definitions and one docstring reference).
  This is not a new finding — `app.py:1383-1391`'s own comment already
  says so, citing a 07-03 report. What **is** new this audit: neither
  does `start_background_loops()` call `_start_lookup_loop()` /
  `_start_world_feed_loop()` (also both on the 64-candidate list) —
  meaning those two are independently, doubly dead. See Summary #3 for
  the env-var consequence.
- **`loom_model/loom_shadow.py:16 loom_shadow_status`**: CONFIRMED dead
  by cross-reference with prior team memory ("loom_shadow 404 — not
  deployed"), consistent with zero callers found here.
- `loom_model/embryo.py:586,590 gp_set_goal`/`gp_drive`: plausible true
  positives — these are goals-hemisphere (GP) methods, and `HEMI_
  GP_ENABLED` is off in prod (§1), so even if something called them
  today it would be exercising a cold path; not fully chased to rule out
  a differently-named caller.
- The remaining ~61 candidates were **not** individually verified this
  pass (would require per-symbol call-graph tracing beyond a grep
  budget) — listed for the record, method limits stated per audit law
  0.3. Full list reproducible via the command above; representative
  sample:
  `dsf_ai_service/organ_brain_service.py:722 attend_object`,
  `dsf_ai_service/organ_brain_service.py:802 mail_send`,
  `dsf_ai_service/organ_brain_service.py:824 mail_get`,
  `dsf_ai_service/organ_brain_service.py:832 tablet_search`,
  `dsf_ai_service/v4/gualaloom_v5_engine.py:4416 _emit_unslotted`,
  `dsf_ai_service/v4/gualaloom_v5_engine.py:9028 restore_from_snapshot`,
  `dsf_ai_service/v4/wave_atlas.py:150 read_near`,
  `dsf_ai_service/v4/wave_atlas.py:349 subdivision_count`.

**A whole dead module, found by tracing the constants duplication (see
§6)**: `dsf_ai_service/substrate/GL_MDL_COGNITION_WC_20260608_02.py`
("v2" of a parallel deep-multimodal-cognition engine) has **zero
importers anywhere in the live tree** —
`grep -rn "GL_MDL_COGNITION_WC_20260608_02" --include="*.py" .` finds
only the file itself. Its sibling,
`GL_MDL_MULTIMODAL_DEEP_WC_20260608_03.py` ("v3"), **is** live —
imported lazily by `app.py:3960` inside `_init_substrate()`, itself
called from the live (if obscure) endpoints `POST /substrate/hear_word`
and `POST /substrate/feed_senses`. This is an entirely separate,
parallel toy cognition engine from the main Guala organism
(`gualaloom_v5_engine.py`/`converse()`), reachable only through those
two endpoints. `GL_MDL_PRIMITIVES_WC_20260608_01.py` and
`GL_MDL_COMPOSITION_WC_20260608_01.py` are transitively live through
that same chain (`install_word()` → `TextProcessor`). [EV]

---

## 3. Unimplemented / stub functions

**Method** [EV]: `python3 tools/audit/sec4_code_truth.py stubs --root
dsf_ai_service` — regex for `NotImplementedError`, `#\s*STUB`,
`#\s*stub`, "not implemented", bare `NotImplemented`. Raw hits: **5**.

| File:line | Text | Disposition |
|---|---|---|
| `app.py:4376` | `raise HTTPException(status_code=501, detail="not implemented for local mode")` | **Real, live-reachable stub.** Inside `corpus_status` (`GET /api/v1/curriculum/corpus_status/{corpus_id}`), gated by `if _is_remote():` (`SUBSTRATE_MODE=="remote"`). Prod's `SUBSTRATE_MODE=embedded` → `_is_remote()` is always False → this endpoint **always 501s in production**. Confirmed one of the 65 externally-defined routes; not confirmed whether it's on the 38-route external API-Gateway surface (would need the AWS-side route list to cross-check — flagged for whoever holds that, not re-derived here). |
| `brain.py:273` | docstring: "...Raises NotImplementedError rather than silently guessing..." | Not a stub itself — a docstring describing the design intent of the two `raise` sites below it. |
| `brain.py:333` | `raise NotImplementedError(f"recall_fast: modality {m!r} krimelack is ...")` | Real guard-rail, not an incomplete feature — deliberately refuses to guess outside `LanguageKrimelack`'s proven scope. **Currently unreachable in production**: `Embryo` defaults `observable="resonant_spectral"`, and `recall_fast()` early-returns via `_recall_fast_resonant_spectral()` (line ~331) before ever reaching this vectorized general-modality code (self-documented in the same docstring, citing `GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-207`). |
| `brain.py:396` | `raise NotImplementedError(f"recall_fast: modality {m!r} krimelack is ... with no ._inner OscillatorKrimelack ...")` | Same as above — guard-rail, same reachability caveat. |
| `v4/gualaloom_v5_engine.py:4488` | docstring: "...raises NotImplementedError for a live visual/auditory signal — recall() is the general..." | Not a stub itself — explains why the new (07-05) `_recall_from_organism_auditory` deliberately calls `Embryo.recall()` instead of `recall_fast()`. |

**Reconciliation**: 5 raw regex hits, but only **1** is an actual
executed-at-runtime incomplete-feature stub (`app.py:4376`); 2 are real
`raise NotImplementedError` guard-rails (defensible scope fences, not
"unfinished work," and currently cold given production's observable
default); 2 are docstring prose that merely *mention* the pattern. If
the pre-audit "3 stub markers" meant "3 places where code can actually
raise/return not-implemented at runtime," that's `app.py:4376` +
`brain.py:333` + `brain.py:396` = **3, exact match**. [EV]

---

## 4. Repo-wide TODO / FIXME / XXX sweep (comments only)

**Method** [EV]: `python3 tools/audit/sec4_code_truth.py todo --root .`
(catches `.py` only) plus a supplementary `grep -rnE` across `.py .js .ts
.tsx .jsx .sh .html .yml .yaml .css`, both excluding `.git`,
`node_modules`, and the audit script's own file (which contains the
regex pattern as a string literal — 3 false-positive self-matches
excluded).

**Guala-relevant hits (dsf_ai_service): exactly 1.**

| File:line | Comment |
|---|---|
| `dsf_ai_service/substrate/deep_atlas.py:112` | `"polarity": 1.0,  # TODO: derive polarity from sentiment when grounded text pipeline available` |

Zero `FIXME`, zero `XXX` anywhere in `dsf_ai_service`.

**Out-of-scope hits, reported for completeness of the "repo-wide" ask
but NOT part of Guala's TODO ledger** (per the project-separation rule —
this is unrelated TFE/physics-hardware code, not Guala):

| File:line | Comment |
|---|---|
| `docs/weak_measurement_host_software.py:156` | `# [TODO: Apply MW pulse of specified duration]` |
| `docs/weak_measurement_host_software.py:157` | `# [TODO: Measure fluorescence]` |
| `docs/weak_measurement_host_software.py:186` | `# [TODO: Initialize to |+1⟩, wait, measure fluorescence]` |
| `docs/weak_measurement_host_software.py:219` | `# [TODO: Apply CPMG sequence, measure visibility]` |
| `docs/weak_measurement_host_software.py:320` | `# [TODO: Rotate to basis, measure weak value]` |

This feeds §9's consolidated ledger with **1** real Guala code-comment
TODO (`deep_atlas.py:112`).

---

## 5. `except:` / `except Exception:` immediately followed by `pass`

**Method** [EV]: `python3 tools/audit/sec4_code_truth.py exceptpass
--root dsf_ai_service` — finds every `except[...]:` whose next non-blank
line is a bare `pass` at greater indent. Raw total: **90**, across 10
files:

| File | Count |
|---|---|
| `v4/gualaloom_v5_engine.py` | 26 |
| `substrate_runner.py` | 23 |
| `app.py` | 18 |
| `organ_brain_service.py` | 9 |
| `loom_model/loom_voice.py` | 6 |
| `virtual_home.py` | 2 |
| `substrate_client.py` | 2 |
| `episodic_layer.py` | 2 |
| `substrate/v7_engine.py` | 1 |
| `loom_model/lookup_grounding.py` | 1 |

**Reconciliation with the claimed "34 in cognition files"**: if
"cognition files" = `loom_model/*.py` + `v4/gualaloom_v5_engine.py` +
`substrate/v7_engine.py` (i.e., the core engine, excluding the API
layer `app.py`, the boot/orchestration layer `substrate_runner.py`, the
separate `organ_brain_service.py`, and small support files), the count
is `7 + 26 + 1 = 34` — **exact match**. This means the pre-audit "34" is
real but represents only **38% of the true total (34/90)** — a
legitimate number under a narrow, undocumented scope, easy to
mistake for "the whole service's except:pass count." Flagging this
explicitly since the dispatch's own §0.3 warns against inheriting
scope assumptions.

### 5.1 The 34 "cognition files" sites — individually judged

| File:line | Context (one line) | Judgement |
|---|---|---|
| `loom_model/lookup_grounding.py:44` | reading `.env` file for a fallback `OPENAI_API_KEY` | Defensible — best-effort local-dev fallback, prod uses the real env var |
| `loom_model/loom_voice.py:46` | load JSON sense-cache from disk | Defensible — cache miss just means recompute, no data loss |
| `loom_model/loom_voice.py:56` | write JSON sense-cache to disk | Defensible — best-effort persistence of a cache, not source-of-truth state |
| `loom_model/loom_voice.py:86` | after filling cache entries, `_save_cache()` | Defensible — same cache, same reasoning |
| `loom_model/loom_voice.py:102` | `self.emb.sc_learn(concept, profile)` | **Borderline** — swallows any learning-write failure with no log line; if `sc_learn` throws, that concept silently never gets recorded and no operator signal exists |
| `loom_model/loom_voice.py:149` | `experience()` + `sc_learn()` combo (folds → grows) | **Borderline**, same reasoning as above — a failed fold is invisible |
| `loom_model/loom_voice.py:188` | `experience()` for a visual concept | **Borderline**, same reasoning |
| `substrate/v7_engine.py:750` | `os.remove(snapshot_path)` cleanup after a discarded bad snapshot | Defensible — best-effort tempfile cleanup, `OSError`-scoped not blanket `Exception` |
| `v4/gualaloom_v5_engine.py:1178` | `engine.log_event("state","presence_timeout",...)` | Defensible — telemetry-only, must not break the caller |
| `v4/gualaloom_v5_engine.py:1273` | `guala.log_event("state","suffering_recovery",...)` | Defensible — telemetry-only |
| `v4/gualaloom_v5_engine.py:1924` | load `world_state.json` for `location` | Defensible — falls through to a sane default (`"her_room"`) on failure |
| `v4/gualaloom_v5_engine.py:1931` | `_sky_fn()` for `sky_period` | Defensible — falls through to `"day"` default |
| `v4/gualaloom_v5_engine.py:2674` | `_log_substrate_event("converse_emission_lock",...)` | Defensible — telemetry-only |
| `v4/gualaloom_v5_engine.py:2744` | `run_hemisphere_updates(...)` call | Defensible in isolation ("hemisphere failures must not break converse", per the adjacent comment) — but see Summary #2: since all 4 HEMI flags are off, this can never actually throw a *meaningful* error today; the guard is dormant, not tested |
| `v4/gualaloom_v5_engine.py:2794` | `q.put_nowait(None)` on a shutdown queue | Defensible — best-effort worker-thread shutdown signal |
| `v4/gualaloom_v5_engine.py:2841` | after a separate `except _queue.Full: pass`, catches other errors on tapestry enqueue | Defensible — non-critical background enqueue |
| `v4/gualaloom_v5_engine.py:3002` | after `except _queue.Full:` (counted), catches other errors on organism enqueue | Defensible — same pattern |
| `v4/gualaloom_v5_engine.py:3026` | organism enqueue, second call site | Defensible — same pattern |
| `v4/gualaloom_v5_engine.py:3821` | `get_emission_hemisphere_weights(cand,...)` | Same dormant-guard caveat as 2744 |
| `v4/gualaloom_v5_engine.py:4816` | spawn a daemon thread to log an event | Defensible — telemetry-only |
| `v4/gualaloom_v5_engine.py:4840` | `self._daydream_tick()` inside a `while` loop | **Borderline** — a persistently-failing daydream tick would spin silently forever with no operator signal; loop itself keeps running so it's not fatal, but is unobservable |
| `v4/gualaloom_v5_engine.py:5158` | spawn thread to log "needs" telemetry | Defensible — telemetry-only |
| `v4/gualaloom_v5_engine.py:5649` | write + fsync a "cleared_at_tick" marker file | Defensible — best-effort marker, not primary state |
| `v4/gualaloom_v5_engine.py:5679` | building a taste/smell word map from library dicts | Defensible — cosmetic vocabulary lookup |
| `v4/gualaloom_v5_engine.py:6222` | cache last sound signal + wall time | Defensible — best-effort caching for later binding |
| `v4/gualaloom_v5_engine.py:6517` | spawn thread to log "needs" telemetry (2nd site) | Defensible — telemetry-only |
| `v4/gualaloom_v5_engine.py:6662` | `_log_substrate_event("autonomy_emission_lock",...)` | Defensible — telemetry-only |
| `v4/gualaloom_v5_engine.py:7219` | feed generated self-voice WAV into `process_sound_frame` | **Borderline** — if espeak or the sound pipeline fails, self-voice tagging silently never happens with no error surfaced; matters for the self-hearing feature's correctness, invisible to an operator |
| `v4/gualaloom_v5_engine.py:7656` | `os.remove(tmp)` tempfile cleanup | Defensible — `OSError`-scoped |
| `v4/gualaloom_v5_engine.py:7912` | `os.remove(_tmp)` tempfile cleanup (2nd site) | Defensible — `OSError`-scoped |
| `v4/gualaloom_v5_engine.py:7936` | `os.remove(guala_teaching.json.tmp)` cleanup | Defensible — `OSError`-scoped |
| `v4/gualaloom_v5_engine.py:8337` | restoring teaching feedback/correction logs from saved state | **Borderline** — a corrupt/partial teaching-log restore is swallowed with no log line; operator would want to know teaching history didn't restore |
| `v4/gualaloom_v5_engine.py:8938` | after `except _queue.Full: pass`, diary enqueue | Defensible — same non-critical background pattern |
| `v4/gualaloom_v5_engine.py:8962` | `os.remove(...)` diary-file retention cleanup | Defensible — `OSError`-scoped |

Of the 34: **26 defensible** (telemetry/best-effort/cleanup with sane
fallback), **6 borderline** (silently swallow a failure an operator
would plausibly want surfaced: `loom_voice.py:102,149,188`,
`gualaloom_v5_engine.py:4840,7219,8337`), **2 currently-dormant guards**
whose real behavior is untested because the code path they guard never
throws in prod today (`2744`, `3821`, tied to Summary #2). None of the
34 looked like it was hiding a currently-active production bug.

### 5.2 The other 56 sites (app.py 18, substrate_runner.py 23,
organ_brain_service.py 9, virtual_home.py 2, substrate_client.py 2,
episodic_layer.py 2) — grouped judgement

All 56 were read for context (not reproduced verbatim here for length);
patterns fall into a small number of buckets, each judged once:

- **Optional-import fallback** (`app.py:32,3761` — `pillow_heif`):
  Defensible.
- **Best-effort telemetry / event logging** (majority of
  `substrate_runner.py`'s 23 and several of `app.py`'s 18 — e.g.
  `app.py:3574,3626,3641` SSE/WebSocket stream best-effort send,
  `substrate_runner.py:282,322,353,379,490,2814,2913` — all
  `_log_substrate_event` calls): Defensible, matches the pattern from
  §5.1.
- **"Save session after responding" best-effort** (`app.py:4126,4158,
  4429,4635,4637`, `substrate_runner.py:1047,1064,1093`): Defensible —
  response already went out; a failed post-hoc save is a durability
  concern for §3 (state truth), not a silently-wrong-answer concern
  here, though it does mean a save failure here produces **zero
  operator signal**, which is worth a register line cross-referenced to
  §3's save-durability findings (memory: "last_save_tick=0 at boot
  means saves broken" was a real prior incident of exactly this class).
- **`OSError`-scoped tempfile/job cleanup** (`app.py` job-gc,
  `substrate_runner.py` various): Defensible.
- **RSS circuit-breaker watchdog** (`organ_brain_service.py:214`):
  **Borderline** — see full context in-report above; a failure inside
  the watchdog's own check is swallowed with no log line, meaning a
  broken circuit-breaker would never announce itself. The watchdog
  loop itself continues (next 60s tick), so it self-heals for
  transient errors, but a *persistent* failure mode is invisible.
- **Best-effort v7↔multimodal bridge relay** (`app.py:4034,4120`,
  `organ_brain_service.py:869,911,964`): Defensible — explicitly
  optional cross-system enrichment, documented as such in-line.
- **Word-list/vocab scan from cache** (`organ_brain_service.py:635,650`):
  Defensible — cosmetic.
- **Room-transition attempt** (`organ_brain_service.py:526`): Defensible
  — best-effort environment-state update, not core cognition.
- **Concept-drift/translation telemetry** (`organ_brain_service.py:1061`,
  `substrate_runner.py:2814`): Defensible — telemetry-only.
- **Connection close on shutdown** (`substrate_client.py:112,123`):
  Defensible — best-effort socket teardown.
- **Episodic-memory load/save** (`episodic_layer.py:71,79`): Defensible
  — same cache-not-source-of-truth reasoning as `loom_voice.py`.
- **Virtual-home object/weather load/save** (`virtual_home.py:454,468`):
  Defensible — same reasoning.

**Total judgement across all 90**: 0 found to be actively hiding a
currently-reproducing production bug; ~8 (across both groups) are
"borderline" in the sense that a real failure there would currently be
invisible to an operator, which is exactly the failure mode the
dispatch is worried about in the abstract, even though none was caught
in the act this audit.

---

## 6. Module-level constants — physics vs. tuned vs. unclear

**Method** [EV]: `python3 tools/audit/sec4_code_truth.py constants
--root dsf_ai_service` — matches `^[A-Z][A-Z0-9_]{2,}\s*=` at column 0
(module scope only). Raw total: **354** across all of
`dsf_ai_service`; **84** of those have a pure numeric-literal RHS
(the rest are dicts/lists/strings/env-derived). Restricting to files
that are plausibly "substrate/cognition engine" (`substrate/*.py` minus
its own `test_*.py`, `v4/gualaloom_v{4,5,6}*.py`,
`loom_model/substrate_dna.py`, `visual_krimelack.py`, `sensory_
krimelacks.py`, `loom_model/topology.py`, `loom_model/grandurun.py`)
and excluding probe/sweep/test harnesses under `loom_model/tests/`:
**62 numeric-literal constants.**

**Reconciliation**: no scope tested reproduces exactly "24." Candidates
range from ~22 (only the 3 `GL_MDL_*_WC_20260608_*.py` files) to 62 (all
core engine files) depending what counts as "engine." This strongly
suggests the pre-audit "24" was a **hand-curated subjective shortlist**
of the most load-bearing constants, not a mechanically-defined set —
worth recording as a correction: this number is **not reproducible by
grep** and should not be treated as an audit-grade count going forward
unless the original curator's exact list is recovered.

### 6.1 Representative classification (most-cited / most load-bearing)

| File:line | Constant = value | Class | Evidence |
|---|---|---|---|
| `loom_model/substrate_dna.py:47` | `FOLD_TRIGGER_RATIO = math.exp(-1)` | **PHYSICS** | In-line comment: "1/e from L6-TCL physics (Ch.11)" — cites a specific derivation chapter |
| `loom_model/substrate_dna.py:42-46` | `K_TOTAL=16, J_BASE=1.0, J_MAX=1.5, CHI_BAND=2, PSI_LATTICE_DIM=16` | **PHYSICS (spec-cited)** | File header: "Constants — all from existing substrate code or Master Spec" — traceable to a named spec, not ad hoc, though the spec document itself wasn't re-verified this pass |
| `visual_krimelack.py:17-20` | `OMEGA_0=5.0, KAPPA_MAX=50.0, WINDING_PHASE=2π, DT=0.02` | **PHYSICS (self-labeled)** | Section header literally: "Constants (modeling-validated)" |
| `visual_krimelack.py:22` | `COFIRE_OVERLAP_THRESHOLD = 0.85` | **TUNED (self-labeled)** | In-line comment: "tunable — type-vs-instance discrimination" |
| `visual_krimelack.py:23` | `G32_FIRING_THRESHOLD = 0.55` | **UNCLEAR/PHYSICS-adjacent** | In-line comment: "cosine on angle (from synthesis model)" — references a model but not a first-principles derivation |
| `visual_krimelack.py:24-25` | `GATE_INERTIA=0.6, COUPLING_STRENGTH=0.15` | **UNCLEAR** | No comment in this file; no derivation found |
| `substrate/deep_atlas.py:19-20` | `FORGETTING_THRESHOLD=0.02, STRENGTH_CAP=1.0` | **TUNED** | Same values duplicated verbatim in 3 other files (see 6.2); `deep_atlas.py:106-111` derives `_CO_PRUNE_THRESH = FORGETTING_THRESHOLD**2` with an explicit comment showing the algebra — the *derivation* is real, but its base (`FORGETTING_THRESHOLD` itself) has no cited physical law, just an empirically-chosen decay floor |
| `substrate/GL_MDL_COGNITION_WC_20260608_02.py:31-51` (dead file, §2) | `BASE_REINFORCEMENT, DECAY_LAMBDA, FORGETTING_THRESHOLD, STRENGTH_CAP, ACT_DECAY, CASCADE_GAIN, COHESION_THRESHOLD, EMISSION_REFRACTORY, LATERAL_INHIBITION, PERCEPTION_BOOST, COFIRE_WINDOW_TICKS, INTRO_PERIOD, COORDINATOR_PERIOD` | **TUNED** | File's own docstring: "Decay-balance: **tuned** to allow accumulation while preventing runaway" — explicit self-classification |
| `substrate/assemblage.py:24-31` | `N=16, DT=0.1, EVOLVE_STEPS=6, DET_COMMIT=0.40, P_COMMIT=0.40, BOOTSTRAP_MAX=8, MODE_DECAY_TICKS=80, SELF_EVO_PERIOD=40` | **PHYSICS-mechanism / TUNED-value** | `DT`/`EVOLVE_STEPS` feed a genuine Crank-Nicolson unitary integrator (`H_total`/`step`/`evolve`, lines ~290-320: `A = I + 1j*H*DT/2; B = I - 1j*H*DT/2; psi = solve(A, B@psi)`) — the *method* is real physics (Schrödinger-like unitary evolution), but the specific values of `DT`/`EVOLVE_STEPS`/the commit thresholds have no derivation comment in this file — classified TUNED for the values, PHYSICS for the surrounding math |
| `substrate/hemisphere_cognition.py:33-58` | `CONSENSUS_GAIN=0.05, DIVERGENCE_DECAY=0.95, CROSS_HEMI_BASELINE_DECAY=0.0008, EP_BIND_GAIN=0.10, NEGATION_DECREMENT=0.05, SC_EMISSION_WEIGHT=0.30, GP_EMISSION_BIAS=0.50` | **UNCLEAR** | No derivation/citation comments found near these declarations; and per §1, all four hemispheres these feed are off in production, so these are currently non-operative values regardless of classification |
| `v4/gualaloom_v5_engine.py:595-659` | `EMISSION_COHESION_THRESHOLD=0.65, EMISSION_COOLDOWN_TICKS=200, DP_RATE_MULTIPLIER=9.0, EMISSION_RECORDS_CAP=1000, RECOGNITION_EVERY_N_WORDS=3, SENSE_BINDING_WINDOW_SEC=3.0` | **TUNED** | No physics citation; performance/behavior tuning knobs for the live emission engine |

**Duplication finding** (§2 cross-reference): `FORGETTING_THRESHOLD`,
`STRENGTH_CAP`, `EMISSION_REFRACTORY`, `LATERAL_INHIBITION`,
`PERCEPTION_BOOST`, `COFIRE_WINDOW_TICKS` are each defined
independently (copy-pasted, not imported from one source) in 2-4 of:
`deep_atlas.py`, `gualaloom_v6_living_atlas.py`,
`GL_MDL_COGNITION_WC_20260608_02.py` (dead), `GL_MDL_MULTIMODAL_
DEEP_WC_20260608_03.py` (live, separate engine). Some have already
drifted between copies: `PERCEPTION_BOOST` is `0.85` in the "_02" file
vs `0.95` in "_03"; `COFIRE_WINDOW_TICKS` is `5` vs `6`. Not a bug in
either individual file, but a maintainability hazard — a future tuning
change to one copy silently won't propagate to the other engine.

---

## 7. Test suite run

**Location** [EV]: tests exist in 5 places:
`dsf_ai_service/loom_model/tests/` (11 files), `dsf_ai_service/
substrate/*.py` (14 `test_*.py` files), `dsf_ai_service/tests/`
(1 file, `test_gutenberg_adapter.py`), plus 3 top-level orphan files
(`test_fetcher_acn.py`, `test_pristine_cognition.py`,
`test_raw_sector.py`) and `tests/` (2 files:
`test_autonomy_drive.py`, `test_visual_phase2.py`). This report covers
the first three (the ones under `dsf_ai_service/`, matching the
dispatch's "likely pytest under dsf_ai_service/ or tests/" guidance and
containing the 3 named tests); the top-level orphans and `tests/` were
not run this pass (flagged, not measured — see note at end of section).

**Collection**: `pytest dsf_ai_service/loom_model/tests dsf_ai_service/
substrate dsf_ai_service/tests --collect-only -q` → **134 tests
collected, 1 collection ERROR**:
```
ERROR collecting dsf_ai_service/substrate/test_autonomous_emission.py
ImportError: cannot import name 'SEED_VOCAB' from
'dsf_ai_service.substrate.v7_engine'
```
This is a **NEW finding**, not among the 3 named. The whole file cannot
even be collected, so none of its tests run at all (count unknown until
the import is fixed — out of scope to fix under the freeze).

**Precisely dated** [EV]: `git log -S"SEED_VOCAB" --oneline -- dsf_ai_
service/substrate/v7_engine.py` shows `SEED_VOCAB` (and `SKIP_WORDS`)
were deliberately deleted in commit `66f01f8`
("V7-FULL-UNCAGE: cage removal + 503 guards + UI merge",
**2026-06-14 03:11:46**) — the commit message says outright: "Part A:
delete SEED_VOCAB constant and all toy fallbacks from v7_engine.py."
`test_autonomous_emission.py` was never updated to match. **This test
file has been uncollectable for 3+ weeks**, silently, since nothing in
CI or the dev workflow appears to run `--collect-only` and fail loudly
on it.

### 7.1 The 3 named known failures — individually confirmed

Run: `pytest dsf_ai_service/loom_model/tests/test_cognition_path.py -v`
→ **2 failed, 11 passed in 297.44s**:

- **`test_t7_cross_modal` — PASSED.** Contradicts the pre-audit claim.
  Consistent with 07-03 commit `e672331` ("fix: T7 partial-cue crash --
  key resonant_spectral's per-neuron projection by feature dim"),
  which post-dates whenever the "3 known failures" list was drawn up.
  **Correction to carry forward: this is no longer a known failure.**
- **`test_t8_noise_robustness` — FAILED**, confirmed:
  `assert acc_03 >= 45.0` → actual `8.0%` (noise σ=0.30). At σ=0.50 and
  0.80, accuracy is 4.0% and 2.0% respectively — this isn't a
  borderline miss, recall degrades to near-chance under any noise.
- **`test_t11_substrate_true` — FAILED**, confirmed, but the nature of
  the failure is a stale invariant, not a code regression: the test
  asserts zero `loom_model` imports from `app.py`/
  `substrate_runner.py` (an old "substrate must never depend on
  loom_model" architectural rule), but production now legitimately
  imports `CurriculumScheduler`, `guala_migration`, `lookup_grounding`,
  and `world_feeds` from `loom_model` in both files — all real,
  currently-shipping features (curriculum study, autonomous
  lookup/world-feed). The assertion needs updating to reflect the
  current, intentional architecture, or the architecture note needs
  updating to say why these specific imports are exempt.

### 7.2 Full-suite result

The full run is I/O- and CPU-heavy (numpy physics simulations) — a
single file (`test_cognition_path.py`, 13 tests) alone took ~5 minutes,
and the slowest 3 individual tests each took 2-2.5 minutes
(`test_t9_linear_scaling` 132s, `test_t6_cross_modal_differentiation`
129s, `test_t4_growth_saturation` 119s, per pytest's own
`--durations=15` report). A first attempt was killed by a 580s
`timeout`; a second attempt with a 1800s cap completed.

**Final command and result** [EV]:
```
pytest dsf_ai_service/loom_model/tests dsf_ai_service/substrate \
  dsf_ai_service/tests --continue-on-collection-errors -q --durations=15
...
6 failed, 128 passed, 30 warnings, 1 error in 967.30s (0:16:07)
```

**All 6 failures + 1 collection error, in full:**

| # | Test | Named in dispatch? | Assertion / error |
|---|---|---|---|
| 1 | `test_cognition_path.py::test_t8_noise_robustness` | Yes | `assert acc_03 >= 45.0` → actual `8.0%` (see §7.1) |
| 2 | `test_cognition_path.py::test_t11_substrate_true` | Yes | Stale "no loom_model imports from app.py/substrate_runner.py" invariant (see §7.1) |
| 3 | `test_folding_engaged.py::test_t3_corpus_growth` | **NEW** | `pytest.fail("T3 FAIL: zero hemispheres grew. Folding not operating during experience. Surface: fold_check or contact inhibition blocking all folds.")` — all 8 hemispheres held flat at seed population (8 neurons each) across 242 delivered words of a Peter Rabbit excerpt in this test's isolated pipeline |
| 4 | `test_folding_engaged.py::test_t8_substrate_true` | **NEW** | Same stale-invariant class as #2: asserts zero `loom_model` imports from `app.py`/`substrate_runner.py`; fails on the same 6 real, live import lines (`guala_migration`, `curriculum_scheduler`, `lookup_grounding`, `world_feeds`) |
| 5 | `test_save_hooks.py::test_should_save_bypass_includes_activity_ended_and_backstop` | **NEW** | `assert sc._should_save(reason) is True` for `reason="activity_ended"` → actual `False`. All of `shutdown`/`backup`/`dream_end` presumably passed (loop stopped at the first failure); `activity_ended` specifically no longer bypasses `_should_save`'s normal gating in `SaveCoordinator` |
| 6 | `test_save_hooks.py::test_s3_enqueue_rate_limit_releases_after_interval` | **NEW** | After manually setting `sc._last_s3_enqueue_wall = time.monotonic() - 601` (simulating 601s elapsed against a presumed 600s rate-limit window) and calling `maybe_save("activity_ended")` again, `queue_s3.call_count` stayed at `1`, expected `2` — the rate-limit release-after-interval path did not re-arm |
| — | `test_autonomous_emission.py` (collection error) | No (but the dispatch's 3 named ones live in files adjacent to this) | `ImportError: cannot import name 'SEED_VOCAB'` — dead since 2026-06-14 (see above) |

**Read with care, not alarm, on #5/#6**: both are in
`dsf_ai_service/substrate/test_save_hooks.py`, exercising
`dsf_ai_service/save_coordinator.py`'s `SaveCoordinator` class against
a `MagicMock()` Guala object — these are **unit tests against mocked
state**, not a live save-durability probe against production. They are
still worth escalating precisely because save-durability has a live
incident history (memory: EFS rename race silently dropped saves,
`last_save_tick=0` at boot). Whether `_should_save`'s bypass-list
behavior or the S3 rate-limiter's interval-release logic have
regressed in a way that affects the real, running `SaveCoordinator` —
versus the tests themselves having drifted from an intentional behavior
change — was **not adjudicated this pass**; that requires reading
`save_coordinator.py`'s current `_should_save`/rate-limit implementation
against each test's expectation line-by-line, which is a §3 (state
truth) / defects-register task, not re-derived here. Recorded as a
register-worthy finding, disposition owed.

**Not run this pass** (flagged, not measured, per audit law 0.3): the 3
top-level orphan files (`test_fetcher_acn.py`, `test_pristine_
cognition.py`, `test_raw_sector.py`) and the 2 files under `tests/`
(`test_autonomy_drive.py`, `test_visual_phase2.py`) — these live outside
`dsf_ai_service/` and were out of this run's chosen scope; re-run
command: `pytest test_fetcher_acn.py test_pristine_cognition.py
test_raw_sector.py tests/ -v` if a future pass needs them.

---

## RECONCILIATION: pre-audit numbers vs. this audit

| Claim | Pre-audit | This audit | Verdict |
|---|---|---|---|
| Env flags gating code paths | 27 | 65 distinct names read; 32 actually set in prod; ~34-37 code-only defaults not set in prod | **Does not hold.** The dispatch author's own recount (32 total env vars in the live task-def, noted in this dispatch's ground-truth section) already superseded "27"; the code reads far more names than either number, because most flags have a coded default and are readable whether or not prod sets them. "27" appears to undercount even the prod-set list. |
| except:pass in cognition files | 34 | 90 total in `dsf_ai_service`; **exactly 34** if "cognition files" = `loom_model/*.py` + `gualaloom_v5_engine.py` + `v7_engine.py` | **Holds, narrow scope only.** True but represents 38% of the real total; risk of being misquoted as "the whole service's count." |
| Module-level constants physics-vs-tuned | 24 | 354 total module ALL_CAPS constants; 84 pure-numeric; 62 in core-engine-scoped files (excluding tests) | **Does not reproduce under any tested scope.** Likely a hand-picked shortlist; flagged as not mechanically re-derivable — future audits should either recover the original list or replace "24" with an explicitly-scoped, script-generated number. |
| HTTP endpoints | 65 | 65 (`@app.get/post/put/delete/websocket` decorators in `app.py`, zero duplicate paths) | **Exact match.** [EV] Reconciled against the live API Gateway (below) — 65 in code ≠ 38 externally, and that's expected/correct, not a discrepancy. |
| Engine state files | 14 | Not measured | **Out of §4 scope** — belongs to §3 (EFS/state truth). Not re-derived here to avoid asserting on borrowed evidence. |
| Stub markers | 3 | 5 raw regex hits; 3 are real runtime-reachable not-implemented sites (`app.py:4376`, `brain.py:333`, `brain.py:396`); 2 are docstring mentions | **Holds, with the correct sub-classification made explicit** — the "3" only works if docstring mentions are excluded, which was not obvious from the raw regex. |
| 2 fixes landed in dead code (07-05) | claimed, unnamed | **1 concrete instance found and fully traced**: commit `6d15797`'s fix to the non-phased `converse()` fallback, dead because `CONVERSE_PHASED=1` in prod (Summary #1). A second specific instance was not conclusively identified within this section's grep-based budget — the whole hemisphere-cognition subsystem (Summary #2) and the `boot_substrate()`/`start_background_loops()` family (Summary #3) are broader, older (06-19 and self-reported 07-03) dead-code findings of the same *class*, but not literally "a fix that landed 07-05." Recommend Eve/Joe treat "1 confirmed, 1 not found" rather than assume both are accounted for. |
| "1 template-dict reference" | claimed | **Not conclusively resolved, best candidate identified.** Traced the phrase to `docs/GL-SPC-EXPERIENCE-FIRST-20260702-v2.md` §9.1/§9.3: the spec's canonical-primitive registry explicitly prohibits "template slotting" / "string-template composition" as a substitute for the real syntax mechanism ("keyhole topology cascade + emission dynamics commits"), and §9.3 calls for a weekly grep-audit for exactly this signature. The closest in-repo match is `dsf_ai_service/substrate/assemblage.py:64` `goal_op_for_template(target)` plus its caller `hear_speaker(self, utterance_template_vector, ...)` (line 503) — but this is a **vector**, not a dict (a Hamiltonian goal-operator built from an utterance's chi-vector, used to bias a Section's standing goals), and its only call site is `dsf_ai_service/substrate/gl_bridge.py:31`, itself only reachable through the same obscure `/substrate/hear_word` → `_get_bridge(v7_session)` chain identified in §2 — **not** the main `converse()` engine. It does not obviously match "dict." No literal `TEMPLATE = {...}` dict construct was found anywhere in `dsf_ai_service` (`grep -rn "template.*=.*{" -i` returns nothing). Flagged as genuinely unresolved — needs the originating report (not present in this worktree's `docs/`) identified by Eve/Joe rather than guessed further. |

---

## Method limits (stated once, apply throughout)

- The env/deadcode/stubs/todo/exceptpass/constants scripts are
  line-and-regex based, not an AST-scoped or call-graph tool. Multi-line
  calls, wrapper functions, dynamic dispatch (`getattr`), and
  differently-aliased imports can hide or fake both env-reads and
  "dead" code. Every place this mattered concretely was called out
  above with a manual follow-up grep.
- "LIVE"/"DEAD" resolution is based on static reading of the gating
  `if`/`return` structure plus confirmed production env values — not a
  live trace of the running process. Where a finding was load-bearing
  (Summary #1-#4), the call chain was read end-to-end by hand to
  confirm, not just pattern-matched.
- The constants classification (§6) is inherently judgment-based; PHYSICS
  vs TUNED labels above are backed by an in-repo comment/citation where
  one exists, and marked UNCLEAR where none was found — no external
  physics reference was independently verified against the Master Spec
  document itself this pass.
