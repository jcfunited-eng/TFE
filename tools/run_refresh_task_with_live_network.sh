#!/usr/bin/env bash
set -euo pipefail

CLUSTER="${TFE_ECS_CLUSTER:-tfe-web-cluster}"
SERVICE="${TFE_ECS_SERVICE:-tfe-web-service-lb}"
TASKDEF="${TFE_ECS_TASKDEF:-}"
ASSIGN_PUBLIC_IP="${TFE_ECS_ASSIGN_PUBLIC_IP:-ENABLED}"
REFRESH_MODE_INPUT="${1:-targeted}" # targeted | full | targeted-skip-l5
RESUME_S3_URI="${TFE_REFRESH_RESUME_S3_URI:-s3://tfe-codebuild-src-418384447921-us-east-1/runtime-refresh-checkpoints/}"
RESUME_FROM_CHECKPOINT="${TFE_REFRESH_RESUME_FROM_CHECKPOINT:-0}"
RESUME_MAX_AGE_SECONDS="${TFE_REFRESH_RESUME_MAX_AGE_SECONDS:-21600}"
SKIP_L5_LEARNING="${TFE_REFRESH_SKIP_L5_LEARNING:-0}"
MASSIVE_REQUEST_TIMEOUT_SECONDS="${TFE_REFRESH_MASSIVE_REQUEST_TIMEOUT_SECONDS:-15}"
MASSIVE_MAX_RETRIES="${TFE_REFRESH_MASSIVE_MAX_RETRIES:-2}"
MASSIVE_BASE_BACKOFF_SECONDS="${TFE_REFRESH_MASSIVE_BASE_BACKOFF_SECONDS:-1}"
MASSIVE_MAX_BACKOFF_SECONDS="${TFE_REFRESH_MASSIVE_MAX_BACKOFF_SECONDS:-8}"
MASSIVE_MIN_429_BACKOFF_SECONDS="${TFE_REFRESH_MASSIVE_MIN_429_BACKOFF_SECONDS:-3}"

if [[ "$REFRESH_MODE_INPUT" != "targeted" && "$REFRESH_MODE_INPUT" != "full" && "$REFRESH_MODE_INPUT" != "targeted-skip-l5" ]]; then
  echo "usage: $0 [targeted|full|targeted-skip-l5]" >&2
  exit 2
fi

REFRESH_MODE="$REFRESH_MODE_INPUT"
if [[ "$REFRESH_MODE_INPUT" == "targeted-skip-l5" ]]; then
  REFRESH_MODE="targeted"
  SKIP_L5_LEARNING="1"
fi

if [[ -z "$TASKDEF" ]]; then
  TASKDEF="$(aws ecs describe-services \
    --cluster "$CLUSTER" \
    --services "$SERVICE" \
    --query 'services[0].taskDefinition' \
    --output text)"
fi

SUBNETS_RAW="$(aws ecs describe-services \
  --cluster "$CLUSTER" \
  --services "$SERVICE" \
  --query 'services[0].networkConfiguration.awsvpcConfiguration.subnets' \
  --output text)"
SGS_RAW="$(aws ecs describe-services \
  --cluster "$CLUSTER" \
  --services "$SERVICE" \
  --query 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups' \
  --output text)"

read -r -a SUBNETS <<< "$SUBNETS_RAW"
read -r -a SGS <<< "$SGS_RAW"

if [[ ${#SUBNETS[@]} -lt 1 || ${#SGS[@]} -lt 1 ]]; then
  echo "failed to resolve live ECS network config from service=$SERVICE" >&2
  exit 1
fi

if [[ "$REFRESH_MODE" == "full" ]]; then
  RUN_CMD='cd /app && export PYTHONUNBUFFERED=1 && python3 run_refresh_with_l5_learning.py'
  ORACLE_TIMEOUT_SECONDS="${TFE_REFRESH_ORACLE_TIMEOUT_SECONDS_FULL:-3600}"
  ORACLE_NO_PROGRESS_TIMEOUT_SECONDS="${TFE_REFRESH_ORACLE_NO_PROGRESS_TIMEOUT_SECONDS_FULL:-900}"
else
  if [[ "$SKIP_L5_LEARNING" == "1" || "$SKIP_L5_LEARNING" == "true" || "$SKIP_L5_LEARNING" == "yes" || "$SKIP_L5_LEARNING" == "on" ]]; then
    RUN_CMD='cd /app && export PYTHONUNBUFFERED=1 && python3 run_refresh_with_l5_learning.py --targeted-refresh --skip-l5-learning'
  else
    RUN_CMD='cd /app && export PYTHONUNBUFFERED=1 && python3 run_refresh_with_l5_learning.py --targeted-refresh --run-l5-on-targeted'
  fi
  ORACLE_TIMEOUT_SECONDS="${TFE_REFRESH_ORACLE_TIMEOUT_SECONDS_TARGETED:-600}"
  ORACLE_NO_PROGRESS_TIMEOUT_SECONDS="${TFE_REFRESH_ORACLE_NO_PROGRESS_TIMEOUT_SECONDS_TARGETED:-120}"
fi
ORACLE_TRIGGER_POLICY="${TFE_REFRESH_ORACLE_TRIGGER_POLICY:-scheduled_or_explicit}"
ORACLE_ALLOW_SHORT_CYCLE="${TFE_REFRESH_ORACLE_ALLOW_SHORT_CYCLE:-0}"

SUBNET_JSON="$(python3 - <<'PY' "${SUBNETS[@]}"
import json,sys
print(json.dumps(sys.argv[1:]))
PY
)"
SG_JSON="$(python3 - <<'PY' "${SGS[@]}"
import json,sys
print(json.dumps(sys.argv[1:]))
PY
)"

cat > /tmp/tfe-refresh-task-live-network.json <<JSON
{
  "cluster": "$CLUSTER",
  "launchType": "FARGATE",
  "taskDefinition": "$TASKDEF",
  "count": 1,
  "enableExecuteCommand": true,
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": $SUBNET_JSON,
      "securityGroups": $SG_JSON,
      "assignPublicIp": "$ASSIGN_PUBLIC_IP"
    }
  },
  "overrides": {
    "containerOverrides": [
      {
        "name": "tfe-web",
        "command": [
          "/bin/bash",
          "-lc",
          "$RUN_CMD"
        ],
        "environment": [
          {"name": "TFE_REFRESH_TRIGGER_SOURCE", "value": "program"},
          {"name": "TFE_REFRESH_ORACLE_TRIGGER_POLICY", "value": "$ORACLE_TRIGGER_POLICY"},
          {"name": "TFE_REFRESH_ORACLE_ALLOW_SHORT_CYCLE", "value": "$ORACLE_ALLOW_SHORT_CYCLE"},
          {"name": "TFE_REFRESH_RESUME_FROM_CHECKPOINT", "value": "$RESUME_FROM_CHECKPOINT"},
          {"name": "TFE_REFRESH_RESUME_MAX_AGE_SECONDS", "value": "$RESUME_MAX_AGE_SECONDS"},
          {"name": "TFE_REFRESH_RESUME_S3_URI", "value": "$RESUME_S3_URI"},
          {"name": "TFE_REFRESH_REBUILD_QUOTE_CACHE", "value": "0"},
          {"name": "TFE_REFRESH_ORACLE_TIMEOUT_SECONDS", "value": "$ORACLE_TIMEOUT_SECONDS"},
          {"name": "TFE_REFRESH_ORACLE_POLL_SECONDS", "value": "1"},
          {"name": "TFE_REFRESH_ORACLE_SHORT_CYCLE_RUNS", "value": "1"},
          {"name": "TFE_REFRESH_ORACLE_NO_PROGRESS_TIMEOUT_SECONDS", "value": "$ORACLE_NO_PROGRESS_TIMEOUT_SECONDS"},
          {"name": "MASSIVE_REQUEST_TIMEOUT_SECONDS", "value": "$MASSIVE_REQUEST_TIMEOUT_SECONDS"},
          {"name": "MASSIVE_MAX_RETRIES", "value": "$MASSIVE_MAX_RETRIES"},
          {"name": "MASSIVE_BASE_BACKOFF_SECONDS", "value": "$MASSIVE_BASE_BACKOFF_SECONDS"},
          {"name": "MASSIVE_MAX_BACKOFF_SECONDS", "value": "$MASSIVE_MAX_BACKOFF_SECONDS"},
          {"name": "MASSIVE_MIN_429_BACKOFF_SECONDS", "value": "$MASSIVE_MIN_429_BACKOFF_SECONDS"}
        ]
      }
    ]
  }
}
JSON

aws ecs run-task --cli-input-json file:///tmp/tfe-refresh-task-live-network.json --query 'tasks[0].taskArn' --output text
