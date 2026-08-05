## Global Constants

- `NO_EXPERIMENTAL_CODE=true`
- `FULL_FILE_REPLACEMENT_ONLY=true`

## Document Status

- This is a living infrastructure reference.
- Update it only from verified code, verified shell commands, verified file existence, or verified AWS evidence.
- If a future item cannot be verified, mark it plainly instead of guessing.

## Production Deployment

- Primary deployment wrapper path:
  - `/workspaces/Tao_Financial_Engine/tools/deploy_to_prod_with_evidence.sh`
- Verified non-interactive execution command:
  - `GIT_PAGER=cat bash /workspaces/Tao_Financial_Engine/tools/deploy_to_prod_with_evidence.sh`
- Verified supporting shell:
  - `/usr/bin/bash`
- Verified deployment source rule:
  - The wrapper deploys the current checked-out `HEAD`.
- Verified branch-name gate in the wrapper:
  - None found in the code.
- Verified commit gate in the wrapper:
  - `HEAD` must resolve to a valid 40-character git SHA.
- Verified delta-base rule in the wrapper:
  - Base revision defaults to `HEAD^`.
  - Override variable: `TFE_DEPLOY_DELTA_BASE_REV`

## Deployment Evidence

- Evidence directory pattern:
  - `/workspaces/Tao_Financial_Engine/backups/deploy-evidence-<UTCSTAMP>`
- Verified success artifacts:
  - `codebuild-start.json`
  - `codebuild-result.json`
  - `codebuild-poll.log`
  - `taskdef-register-input.json`
  - `taskdef-register-output.json`
  - `ecs-service-update.json`
  - `ecs-service-post.json`
  - `deploy-report.tsv`
- Verified latest successful deploy at time of this update:
  - Evidence dir: `/workspaces/Tao_Financial_Engine/backups/deploy-evidence-20260330T062631Z`
  - Commit: `a60e095360f2634b8731e81315cecf6b7c436530`
  - ECS task definition: `tfe-web-task:294`

## Deployment Hang Lessons

- Verified pager lesson:
  - `GIT_PAGER=cat` is the safe deploy invocation.
  - In this workspace, the pager override is still required even when it is not the only blocker.
- Verified real blocker 1:
  - `tools/validation_state_contract.py` used a full-repo `git ls-files -m`.
  - In this workspace, that call can hang.
  - Verified fix:
    - scope dirty checks to deploy-relevant tracked paths only.
  - Verified commit:
    - `414dcb6 fix: scope deploy validation dirty scan to deploy inputs`
- Verified real blocker 2:
  - `tools/deploy_to_prod_with_evidence.sh` used a very large `git diff --name-only HEAD -- <deploy patterns...>` call.
  - In this workspace, that call can hang.
  - Verified fix:
    - `deploy_workspace_integrity` now reads exact tracked inputs from `delta-unit-selection.json`
    - it diffs only those tracked paths against `HEAD`
    - it reads true untracked paths from `delta-selected-files.json`
  - Verified commits:
    - `94149e2 fix: stop deploy workspace integrity git diff hang`
    - `3031cb3 fix: scope deploy workspace integrity to exact tracked inputs`
- Verified unsafe deployment checks in this workspace:
  - whole-repo `git ls-files -m`
  - giant deploy-pattern `git diff --name-only HEAD -- ...`

## Database Utilities

- Core sync engine file path:
  - `/workspaces/Tao_Financial_Engine/web/scripts/sync_runtime_postgres_impl.mjs`
- Verified runtime wrapper path for the sync engine:
  - `/workspaces/Tao_Financial_Engine/web/scripts/sync_runtime_postgres.mjs`
- Verified execution command used from the workspace root:
  - `cd /workspaces/Tao_Financial_Engine && node web/scripts/sync_runtime_postgres.mjs`
- Verified runtime binaries:
  - `node=/usr/bin/node`
  - `python3=/usr/local/bin/python3`
- Verified direct production DB query command shape from the workspace:
  - `source /workspaces/Tao_Financial_Engine/load-readonly-env.sh >/dev/null 2>&1 && psql "$PGDATABASE" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -Atqc "<sql>"`
- Verified direct production DB failure mode from this workspace:
  - `psql: error: connection to server at "tfe-prod-postgres.c6vogauo4y6b.us-east-1.rds.amazonaws.com" (172.31.3.76), port 5432 failed: Connection refused`
- Verified network truth for that failure:
  - the env loader resolves the correct host values
  - the broken bridge is the direct TCP path from this workspace to the private RDS socket
  - this workspace can reach AWS control plane but not that private Postgres listener directly
- Verified production DB fallback path when direct `psql` refuses:
  - run the SQL inside the ECS service network with `/workspaces/Tao_Financial_Engine/tools/run_validation_gate_v1_in_ecs_network.py`
- Verified ECS-network DB query command pattern:
  - `python3 /workspaces/Tao_Financial_Engine/tools/run_validation_gate_v1_in_ecs_network.py --cluster tfe-web-cluster --service tfe-web-service-lb --region us-east-1 --timeout-seconds 300 --accept-any-json-payload --command-json '<json command>'`
- Verified use case:
  - use the ECS-network runner for production Postgres count checks and write operations when a local direct socket test returns `Connection refused`

## Database Utilities: Speed Lane 1 - VPC Tunnel

- Purpose:
  - bypass the CodeBuild deploy-to-test cycle for database and L5 math verification from this local workspace
- Verified prerequisite:
  - ECS Exec is enabled on `tfe-web-service-lb`
  - `enableExecuteCommand=true`
- Verified local prerequisites:
  - `aws=/usr/bin/aws`
  - `session-manager-plugin=/usr/local/bin/session-manager-plugin`
- Verified tunnel opener path:
  - `/workspaces/Tao_Financial_Engine/tools/open_db_tunnel.sh`
- Verified local sync wrapper path:
  - `/workspaces/Tao_Financial_Engine/tools/run_local_sync_via_tunnel.sh`
- Verified tunnel opener behavior from code:
  - sources `/workspaces/Tao_Financial_Engine/load-readonly-env.sh`
  - resolves the active ECS task runtime ID for container `tfe-web`
  - constructs the Session Manager target as `ecs:<cluster>_<task-id>_<container-runtime-id>`
  - opens `AWS-StartPortForwardingSessionToRemoteHost`
  - forwards local `5432` to remote `$PGHOST:$PGPORT`
- Verified local sync wrapper behavior from code:
  - sources `/workspaces/Tao_Financial_Engine/load-readonly-env.sh`
  - resolves write credentials from `TFE_RUNTIME_DB_SECRET_ARN`
  - overrides `PGHOST=localhost`
  - overrides `PGPORT=5432`
  - runs `node /workspaces/Tao_Financial_Engine/web/scripts/sync_runtime_postgres_impl.mjs`
- Verified tunnel command:
  - `bash /workspaces/Tao_Financial_Engine/tools/open_db_tunnel.sh`
- Verified local sync command:
  - `bash /workspaces/Tao_Financial_Engine/tools/run_local_sync_via_tunnel.sh`
- Verified operational rule:
  - keep the tunnel terminal open while the local sync wrapper runs in a second terminal
- Verified TLS caveat from code:
  - the local sync wrapper sets `TFE_DB_SSL_REJECT_UNAUTHORIZED=false`
  - reason: the tunnel endpoint is `localhost`, so strict certificate hostname verification against the remote RDS hostname would fail
- Verification status:
  - script creation and shell syntax verified
  - local tunnel execution and local sync execution have not yet been run under this directive

## ECS Sync Artifact Truth

- Verified runtime container layout:
  - repo root: `/app`
  - web app root: `/app/web`
  - service runtime working directory defaults to `/app/web`
- Verified manual sync blocker:
  - `node /app/web/scripts/sync_runtime_postgres.mjs` fails if `/app/uf_snapshot.json` does not already exist
  - exact failure:
    - `Snapshot file not found: /app/uf_snapshot.json`
- Verified image artifact truth:
  - `/app/web/data/screener-quote-cache.json` is baked into the image
  - `/app/uf_snapshot.json` is not baked into the image
  - `/app/uf_snapshot.ses.json` was not present in the one-off task inspection
- Verified targeted rebuild cwd rule inside ECS:
  - do not run `python3 /app/rebuild_uf_snapshot.py --targeted-refresh` from `/app/web`
  - from `/app/web`, the targeted selector path breaks with:
    - `targeted_selector_script_missing:/app/web/web/scripts/read_runtime_selector_rows.mjs`
  - verified safe command:
    - `bash -lc "cd /app && python3 /app/rebuild_uf_snapshot.py --targeted-refresh"`
- Verified one-off ECS filesystem truth:
  - files written in one ECS probe task are lost when that task stops
  - therefore rebuild and sync must run inside the same one-off ECS task when sync depends on the freshly written snapshot artifact
- Verified safe combined ECS repair command:
  - `bash -lc "cd /app && python3 /app/rebuild_uf_snapshot.py --targeted-refresh && node /app/web/scripts/sync_runtime_postgres.mjs"`

## Post-Deploy Data Verification

- Verified rule:
  - a deploy is not enough for this class of runtime data fix
  - the deployed image must also produce a fresh runtime sync result and a live DB count proof
- Verified scoping rule:
  - do not trust whole-table counts in `runtime_decision_provenance_latest` as proof for a fresh repair run
  - the production proof query must be filtered to the latest `run_id`
- Verified ECS-network verification method:
  - run a one-off ECS task
  - resolve the runtime DB secret inside that task
  - run `psql` there, not from the local workspace
- Verified live proof command shape:
  - use `/app/web/scripts/resolve_runtime_db_secret.py` inside the ECS task to export `PGUSER` and `PGPASSWORD`
  - then run `psql "$PGDATABASE" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -Atqc "<sql>"`
- Verified latest live case-immunity repair proof:
  - synced run id: `manual-2026-03-30T05:04:42.700Z`
  - `Accumulate=2630`
  - `Avoid=0`
  - `Hold=3565`
  - `PSCF_FALLBACK_CELL_UNMAPPED=16`
  - `PSCF_FALLBACK_INSUFFICIENT_BARS=1463`
- Verified latest GEMINI primitive deploy proof:
  - deploy evidence dir: `/workspaces/Tao_Financial_Engine/backups/deploy-evidence-20260330T062631Z`
  - deployed task definition: `tfe-web-task:294`
  - combined ECS rebuild+sync task exit: `0`
  - rebuild rows written: `6194`
  - sync inserted rows:
    - `runtime_decisions_latest=6194`
    - `runtime_decision_provenance_latest=6194`
  - latest synced run id: `manual-2026-03-30T07:00:39.936Z`
  - run-scoped decision counts:
    - `Accumulate=0`
    - `Avoid=6194`
    - `Hold=0`
  - run-scoped provenance counts:
    - `PSCF_FALLBACK_CELL_UNMAPPED=0`
    - `GEMINI_MISSING_REQUIRED_FIELDS=2019`
  - important truth:
    - the deployment succeeded
    - the live data outcome did not
    - the case-immunity repair removed `CELL_UNMAPPED`, but the new deterministic GEMINI gate still produced an all-`Avoid` run
- Verified delta from prior broken state:
  - previous `PSCF_FALLBACK_CELL_UNMAPPED=9568`
  - repaired run `PSCF_FALLBACK_CELL_UNMAPPED=16`

## Environment Specs

- Local workspace root:
  - `/workspaces/Tao_Financial_Engine`
- AWS region:
  - `us-east-1`
- AWS account id:
  - `418384447921`
- ECS cluster:
  - `tfe-web-cluster`
- ECS service:
  - `tfe-web-service-lb`
- ECS task family:
  - `tfe-web-task`
- ECR repository:
  - `tfe-web`
- CodeBuild project:
  - `tfe-web-image-build`
- GitHub remote:
  - `https://github.com/jcfunited-eng/TFE.git`
- Verified remote default branch:
  - `origin/main`
- Verified local branch present for that default line:
  - `main`

## Secret Locations

- Verified workspace env file:
  - `/workspaces/Tao_Financial_Engine/.env`
- Verified workspace credential loaders:
  - `/workspaces/Tao_Financial_Engine/load-readonly-env.sh`
  - `/workspaces/Tao_Financial_Engine/load-refresh-approval-env.sh`
- Verified host credential loaders:
  - `/root/.codex/prod-verification/load-readonly-env.sh`
  - `/root/.codex/prod-verification/load-refresh-approval-env.sh`
- Verified host bootstrap credential store:
  - `/root/.codex/prod-verification/access-key.json`
- Verified CA bundle used for runtime DB TLS:
  - `/workspaces/Tao_Financial_Engine/certs/rds-global-bundle.pem`
- Verified Slack notification secret file path:
  - `/workspaces/Tao_Financial_Engine/backups/runtime/notification-secrets.env`
- `web/.env` status:
  - Absent in the workspace at audit time.
- `web/.env.local` status:
  - Absent in the workspace at audit time.
- Secret values:
  - Not recorded in this file by design.

## Build Pipeline

- Verified type-check command used in the pre-deploy phase:
  - `cd /workspaces/Tao_Financial_Engine/web && npx tsc --noEmit`
- Verified manual build command used in the pre-deploy phase:
  - `cd /workspaces/Tao_Financial_Engine/web && npm run build`
- Verified package build script:
  - `build=next build`
- Verified frontend tool binaries:
  - `npm=/usr/bin/npm`
  - `npx=/usr/bin/npx`

## Completion Notification

- Verified Slack notification script:
  - `/workspaces/Tao_Financial_Engine/tools/codex_notify_slack.sh`
- Verified notification command pattern:
  - `printf '%s\n' '<message>' | /workspaces/Tao_Financial_Engine/tools/codex_notify_slack.sh`
- Verified notification result log:
  - `/workspaces/Tao_Financial_Engine/backups/runtime/codex-notify.log`
- Verified completion rule:
  - deployment work is not complete until the Slack send result has been checked in the log
