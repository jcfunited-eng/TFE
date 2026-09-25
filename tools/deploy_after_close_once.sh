#!/bin/bash
# One-shot, DETACHED deploy timer — Claude 2026-09-25.
# Why: a Claude-session background job dies with the session (the 09-24
# deploy of the freshness fixes never ran for exactly that reason). Launch
# this with setsid/nohup and it runs on its own: sleeps until 20:05 UTC
# (after the close — the rolling deploy overlaps two containers, and the
# daemon has no instance lock), skips if the live build already carries
# HEAD, refuses if HEAD lacks the fixes it is meant to ship, then runs the
# evidence deploy with entries enabled and prints the trade switch.
#
#   setsid nohup bash tools/deploy_after_close_once.sh </dev/null >/dev/null 2>&1 & disown
#   log: artifacts/vtvr_observer/deploy_after_close.log
cd "$(dirname "$0")/.." || exit 1
mkdir -p artifacts/vtvr_observer
exec >>artifacts/vtvr_observer/deploy_after_close.log 2>&1
set -a; source .env 2>/dev/null; set +a

REQUIRED_FILE="${DEPLOY_REQUIRED_FILE:-docs/CH2_READING_FRESHNESS_20260924.md}"
REQUIRED_TOKEN="${DEPLOY_REQUIRED_TOKEN:-advisoryValidationCheck}"
REQUIRED_IN="${DEPLOY_REQUIRED_IN:-web/scripts/run_validation_gate_v1_impl.mjs}"

target=$(TZ=UTC date -d "20:05" +%s); now=$(date +%s); s=$((target-now)); [ "$s" -lt 0 ] && s=0
echo "[deploy-timer] $(date -u +%FT%TZ) pid $$ sleeping ${s}s until 20:05 UTC; HEAD=$(git rev-parse --short HEAD)"
sleep "$s"

HEAD=$(git rev-parse HEAD)
LIVE=$(aws ecs describe-task-definition --task-definition tfe-web-task \
  --query "taskDefinition.containerDefinitions[0].environment[?name=='TFE_GIT_COMMIT_SHA'].value | [0]" --output text 2>/dev/null)
if [ "$LIVE" = "$HEAD" ]; then
  echo "[deploy-timer] live build already carries HEAD $HEAD — nothing to do"; exit 0
fi
if ! git cat-file -e "HEAD:$REQUIRED_FILE" 2>/dev/null \
   || ! git show "HEAD:$REQUIRED_IN" | grep -q "$REQUIRED_TOKEN"; then
  echo "[deploy-timer] GUARD: HEAD $HEAD lacks the required fixes — not deploying"; exit 3
fi

echo "[deploy-timer] deploy start $(date -u +%FT%TZ) HEAD=$HEAD live=$LIVE"
PATH=/opt/node22/bin:$PATH TFE_ENTRIES_HALTED=0 nice -n 15 bash tools/deploy_to_prod_with_evidence.sh
rc=$?
echo "[deploy-timer] DEPLOY EXIT $rc at $(date -u +%FT%TZ)"
aws ecs describe-task-definition --task-definition tfe-web-task \
  --query "taskDefinition.containerDefinitions[0].environment[?name=='TFE_ENTRIES_HALTED' || name=='TFE_GIT_COMMIT_SHA'].[name,value]" --output text
aws ecs describe-services --cluster tfe-web-cluster --services tfe-web-service-lb \
  --query 'services[0].deployments[?status==`PRIMARY`].[taskDefinition,rolloutState]' --output text
