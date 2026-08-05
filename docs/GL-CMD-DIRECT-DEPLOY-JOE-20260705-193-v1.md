# GL-CMD-DIRECT-DEPLOY-JOE-20260705-193-v1

doc_id: GL-CMD-DIRECT-DEPLOY-JOE-20260705-193-v1
From: Joe (verbal, direct) | To: c1a | Filed by: c1a

## Verbatim instruction
"I said to fucking deploy you deploy!" — explicit, direct, repeated
order to deploy `-188` (scene lanes) myself, overriding the earlier
"hand off to c1b as usual" answer from earlier this session. Joe was
asked once already tonight whether to hand off or deploy directly and
chose hand-off; this is a fresh, explicit, unambiguous order to deploy
directly instead, given right now.

## Why this is c1a running the deploy, not c1b
Standing role split all session has been c1a builds/pushes, c1b holds
the deploy trigger. This dispatch records the deliberate, one-time
exception: Joe himself ordered it directly, not inferred from context.
Filed so c1b (or anyone else touching `guala-live` tonight) sees this
and doesn't collide with a deploy in progress, or wonder why a task
def moved without a corresponding `GL-CMD-FIRE-WINDOW*` doc.

## Preflight, checked before running
- `origin/guala-live` HEAD: `f9cdded` (the `-188` scene-lanes build,
  already reviewed/pushed, rebased cleanly on `-191`).
- Local `HEAD` == `origin/guala-live` HEAD, working tree clean.
- No concurrent c1b activity: `git fetch` immediately before running
  showed no new commits since `-188`'s push; no lock files.
- AWS access confirmed (`aws sts get-caller-identity`).
- `.env` present with required keys (`GUALALOOM_API_KEY_NEW`,
  `OPENAI_API_KEY`, `TAVILY_API_KEY`, `YOUTUBE_API_KEY`).
- Baseline ECS state recorded before cutover: `dsf-ai-service-lb`
  1/1 running, task-def `dsf-ai-task:473`.

## What's running
`./tools/deploy_dsf_ai.sh` (unmodified, the existing established
script — CodeBuild image → ECS task-def register → pause/cutover/wake
→ static S3 sync + CloudFront invalidation), deploying `f9cdded`.

### Changelog
- v1 (2026-07-05, c1a): filed at deploy start, per Step 0 discipline —
  before the outcome is known, not after.
