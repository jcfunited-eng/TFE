> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-AUDIT-SEC1-RUNTIME-TRUTH-C1-20260705-v1

doc_id: GL-AUDIT-SEC1-RUNTIME-TRUTH-C1-20260705-v1
Part of: GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2, §1 (Runtime truth)
Author: c1 | Freeze in effect — read-only, no fixes applied.

## Summary (failures/absences first)

- **[EV] Zero CloudWatch alarms exist in the entire AWS account.** `aws cloudwatch describe-alarms` returns `MetricAlarms: []`. Directly confirms the dispatch's pre-audit claim that the 07-05 outage fired no alarm — there was nothing to fire.
- **[EV] Deploys are 100% manual, root-initiated, no CI trigger.** CodeBuild project `dsf-ai-image-build` has `triggers: null` (no webhook/source-trigger). The two most recent builds both show `"initiator": "root"`. There is no automated pipeline from a git push to a deploy — someone runs a build by hand every time, and 10 such manual builds landed today (2026-07-05) between 16:09 and 21:23 UTC alone.
- **[EV] Production secrets are plaintext in the task-definition** (see §2 for full detail) — repeated here because it's a runtime-config fact: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, `YOUTUBE_API_KEY`, `GUALALOOM_API_KEY` are literal values in `dsf-ai-task:494`'s `environment` block, not `secrets`/`valueFrom` references to Secrets Manager or SSM. Retained across all 494 historical revisions of this family.

## Running SHA vs origin tip (First Act #1/#2)

- **[EV]** `guala_status` reports `running_sha: 168ef1bde3717e52efb85b894103de047e942617`. This matches `dsf-ai-task:494`'s deployed image `dsf-ai:deploy-20260705T212346Z`.
- **[EV]** `git diff 168ef1b origin/guala-live --stat` (as of this audit's Step 0 commit `a9dff78`): exactly 4 files changed, 776 insertions, **zero code files** — all four are `docs/*.md` (the c1a handoff + this audit's own charter/dispatch filings). Register finding #1: **no code drift** between running SHA and origin tip; the gap is entirely this audit's own paper trail.

## ECS task definition (`dsf-ai-task:494`) — full env inventory

- **[EV]** Family: `dsf-ai-task`, revision 494 (494 total revisions ever registered in this family — i.e. a new revision every deploy, none reused).
- **[EV]** cpu=2048 (2 vCPU), memory=4096 (4GB), Fargate, platform 1.4.0.
- **[EV]** Container image: `418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai:deploy-20260705T212346Z`, digest `sha256:e7b8a7ec...` (last of 10 same-day pushes, see Image Lineage below).
- **[EV]** Command: `uvicorn dsf_ai_service.app:app --host 0.0.0.0 --port 8080`.
- **[EV]** Health check: `GET /ready` via urllib, interval 10s, timeout 5s, retries 3, startPeriod 300s. **Caveat found during shadow verification (§8 baseline notes): `/ready` returning HTTP 200 only means the process is up — it does NOT mean the substrate finished loading.** The endpoint's own body carries a separate `guala_ready` boolean that ECS's health check does not inspect. A container can be "ECS HEALTHY" for many minutes while `guala_ready` is still false. This is a real gap between ECS's notion of healthy and the app's own notion of ready.
- **[EV]** taskRoleArn=`dsf-ai-task-role`, executionRoleArn=`tfe-ecs-task-execution-role` (see §2 IAM detail).
- **[EV]** Single EFS volume `gualaloom-state` → filesystem `fs-0abb85854a3251b3c`, `rootDirectory: "/"` (the entire filesystem, not access-point-scoped) mounted read-write at `/app/state`.
- **[EV]** 32 environment variables total (not 27 — see reconciliation below): `GUALALOOM_API_KEY`(secret), `CURRICULUM_INTERVAL_SEC=120`, `EMISSION_DYNAMICS=1`, `WHISPER_MODEL_PATH=tiny`, `STATE_DIR=/app/state`, `WORLD_FEEDS=1`, `ANTHROPIC_API_KEY`(secret), `CURRICULUM_ORCHESTRATOR_INTERVAL_SEC=5`, `CURRICULUM_SUBSTRATE_URL=http://localhost:8080`, `CURRICULUM_SEED_PATH=/app/tools/curriculum_seed.json`, `DECAY_PAUSED=0`, `CURRICULUM_CHUNK_SIZE=30`, `CONVERSE_PHASED=1`, `GRANDURUN_SPIN_VECTOR=1`, `WAVE_ATLAS_ENABLED=1`, `AUTONOMY_PHASED=0`, `EMISSION_DYNAMICS_TICKS=80`, `TAVILY_API_KEY`(secret), `EMISSION_MODE=grandurun`, `SUBSTRATE_HEARTBEAT=/app/state/substrate.alive`, `YOUTUBE_API_KEY`(secret), `CURRICULUM_AUTOSTART=0`, `YOLO_MODEL_PATH=/app/yolov8n.onnx`, `PYTHONUNBUFFERED=1`, `SUBSTRATE_MODE=embedded`, `WORLD_FEED_INTERVAL_SEC=600`, `LOOKUP_INTERVAL_SEC=900`, `DREAM_CYCLE_PHASED=1`, `OPENAI_API_KEY`(secret), `LOOKUP_AUTONOMOUS=1`, `ORGAN_BRAIN_URL=http://localhost:8090`, `STUDY_INTERLEAVE_EVERY=2`.
- **[EV]** The six load-bearing flags the dispatch named are all confirmed with real values: `CONVERSE_PHASED=1`, `EMISSION_DYNAMICS=1`, `EMISSION_MODE=grandurun`, `AUTONOMY_PHASED=0`, `WAVE_ATLAS_ENABLED=1`, `GRANDURUN_SPIN_VECTOR=1`. Notably **`AUTONOMY_PHASED=0`** and **`CURRICULUM_AUTOSTART=0`** — autonomy and curriculum autostart are both OFF in production right now; whatever they gate in code (§4 is checking) is dead in prod today regardless of what any doc claims about "autonomous learning deployed."
- **Reconciliation with pre-audit claim of "27 env flags":** 32 total env vars exist; not all 32 are boolean/mode flags that gate code branches — some are plain config (paths, intervals, API keys). §4's code-truth pass is doing the precise count of how many actually gate an `if os.environ`/`os.getenv` branch; this section only confirms the raw inventory and real values.

## Image lineage (ECR)

- **[EV]** 10 images pushed to `dsf-ai` ECR repo today (2026-07-05), all same day, roughly 10-70 minutes apart, from `deploy-20260705T160907Z` through `deploy-20260705T212346Z` (currently running). Image size grew steadily from ~564.97GB... **note: `imageSizeInBytes` reported by ECR is ~565,000,000 (≈565MB), not GB — flagging in case a reader misreads the raw byte count.** Size crept from 564,970,686 to 564,995,399 bytes across the 10 pushes (~25KB growth per deploy — consistent with small code changes, not a bloat problem).
- **[EV]** This cadence (10 manual deploys in ~5 hours) directly corroborates c1a's handoff narrative of repeated crash→fix→redeploy cycles tonight, and independently corroborates it via a completely different data source (ECR push history) rather than trusting the handoff's prose alone.

## Restart / uptime history (ECS service events, last ~30 events available via the API)

- **[EV]** In the available event window (roughly the last 30-40 minutes before this audit began), the `dsf-ai-service-lb` service shows: 1 task replaced due to failed container health checks, 2 more tasks replaced "due to an unhealthy status," and multiple deploy-completion/steady-state cycles — consistent with today's redeploy churn.
- **[NOT MEASURED / LIMITATION]** ECS `describe-services` only returns a bounded recent event window (observed ~30 events ≈ tens of minutes), not a full 7-day history as the dispatch requests. Full 7-day restart history would require either CloudWatch Events/EventBridge history (not checked this pass) or the CloudWatch log group `/ecs/dsf-ai` itself (188MB stored, retention **null = never expires**) — flagging as a §2 follow-up rather than fabricating a 7-day count from a 30-minute sample.
- **[EV]** Confirmed via a separate signal: `/aws/codebuild/dsf-ai-image-build` and the ECR push timestamps together give a real deploy-frequency proxy for today, cross-checked against the service event churn above — they agree in timing.

### Changelog
- v1 (2026-07-05, c1): initial §1 filing. Zero code drift vs origin confirmed; manual/root-only deploy pipeline confirmed; zero CloudWatch alarms confirmed; `/ready` vs `guala_ready` health-check gap discovered during shadow verification.
