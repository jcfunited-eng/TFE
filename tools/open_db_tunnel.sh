#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/workspaces/Tao_Financial_Engine"
ENV_SCRIPT="${REPO_ROOT}/load-readonly-env.sh"
CONTAINER_NAME="tfe-web"
LOCAL_PORT="5432"

require_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing required command: ${name}" >&2
    exit 1
  fi
}

check_local_port_available() {
  python3 - <<'PY'
import socket
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind(("127.0.0.1", 5432))
except OSError:
    print("Local port 5432 is already in use. Stop the existing listener before opening the DB tunnel.", file=sys.stderr)
    raise SystemExit(1)
finally:
    sock.close()
PY
}

require_command aws
require_command python3
require_command session-manager-plugin

if [[ ! -f "${ENV_SCRIPT}" ]]; then
  echo "Missing environment loader: ${ENV_SCRIPT}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_SCRIPT}" >/dev/null

if [[ -z "${PROD_CLUSTER:-}" || -z "${PROD_SERVICE:-}" || -z "${PROD_TASK_ARN:-}" || -z "${PROD_TASK_ID:-}" ]]; then
  echo "The production ECS identifiers were not loaded from ${ENV_SCRIPT}." >&2
  exit 1
fi

if [[ -z "${PGHOST:-}" || -z "${PGPORT:-}" ]]; then
  echo "The Postgres host or port was not loaded from ${ENV_SCRIPT}." >&2
  exit 1
fi

SERVICE_JSON="$(aws ecs describe-services \
  --cluster "${PROD_CLUSTER}" \
  --services "${PROD_SERVICE}" \
  --region "${AWS_REGION:-us-east-1}" \
  --output json)"

ENABLE_EXEC="$(SERVICE_JSON="${SERVICE_JSON}" python3 - <<'PY'
import json
import os

obj = json.loads(os.environ["SERVICE_JSON"])
services = obj.get("services") or []
service = services[0] if services else {}
print(str(bool(service.get("enableExecuteCommand"))).lower())
PY
)"

if [[ "${ENABLE_EXEC}" != "true" ]]; then
  echo "ECS Exec is disabled on ${PROD_SERVICE}. Enable it before opening the DB tunnel." >&2
  exit 1
fi

TASK_JSON="$(aws ecs describe-tasks \
  --cluster "${PROD_CLUSTER}" \
  --tasks "${PROD_TASK_ARN}" \
  --region "${AWS_REGION:-us-east-1}" \
  --output json)"

CONTAINER_RUNTIME_ID="$(TASK_JSON="${TASK_JSON}" CONTAINER_NAME="${CONTAINER_NAME}" python3 - <<'PY'
import json
import os

obj = json.loads(os.environ["TASK_JSON"])
task = (obj.get("tasks") or [{}])[0]
target_name = os.environ["CONTAINER_NAME"]

for container in task.get("containers") or []:
    if str(container.get("name") or "") == target_name:
        print(str(container.get("runtimeId") or "").strip())
        raise SystemExit(0)

raise SystemExit(1)
PY
)"

if [[ -z "${CONTAINER_RUNTIME_ID}" || "${CONTAINER_RUNTIME_ID}" == "None" ]]; then
  echo "Could not resolve the active container runtime ID for ${CONTAINER_NAME} on ${PROD_TASK_ARN}." >&2
  exit 1
fi

check_local_port_available

SSM_TARGET="ecs:${PROD_CLUSTER}_${PROD_TASK_ID}_${CONTAINER_RUNTIME_ID}"
PARAMETERS="$(python3 - <<'PY'
import json
import os

print(json.dumps({
    "host": [os.environ["PGHOST"]],
    "portNumber": [str(os.environ["PGPORT"])],
    "localPortNumber": ["5432"],
}))
PY
)"

echo "Opening VPC DB tunnel on localhost:${LOCAL_PORT} -> ${PGHOST}:${PGPORT}" >&2
echo "ECS SSM target: ${SSM_TARGET}" >&2
echo "Keep this terminal open while local DB logic is running." >&2

exec aws ssm start-session \
  --target "${SSM_TARGET}" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "${PARAMETERS}" \
  --region "${AWS_REGION:-us-east-1}"
