#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/workspaces/Tao_Financial_Engine"
ENV_SCRIPT="${REPO_ROOT}/load-readonly-env.sh"
SECRET_RESOLVER="${REPO_ROOT}/web/scripts/resolve_runtime_db_secret.py"
SYNC_SCRIPT="${REPO_ROOT}/web/scripts/sync_runtime_postgres_impl.mjs"

require_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing required command: ${name}" >&2
    exit 1
  fi
}

require_command aws
require_command python3
require_command node

if [[ ! -f "${ENV_SCRIPT}" ]]; then
  echo "Missing environment loader: ${ENV_SCRIPT}" >&2
  exit 1
fi

if [[ ! -f "${SECRET_RESOLVER}" ]]; then
  echo "Missing runtime DB secret resolver: ${SECRET_RESOLVER}" >&2
  exit 1
fi

if [[ ! -f "${SYNC_SCRIPT}" ]]; then
  echo "Missing sync script: ${SYNC_SCRIPT}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_SCRIPT}" >/dev/null

if [[ -z "${TFE_RUNTIME_DB_SECRET_ARN:-}" || "${TFE_RUNTIME_DB_SECRET_ARN}" == "None" ]]; then
  echo "The runtime DB secret ARN was not loaded from ${ENV_SCRIPT}." >&2
  exit 1
fi

SECRET_JSON="$(python3 "${SECRET_RESOLVER}" "${TFE_RUNTIME_DB_SECRET_ARN}")"

export PGUSER="$(SECRET_JSON="${SECRET_JSON}" python3 - <<'PY'
import json
import os
print(json.loads(os.environ["SECRET_JSON"])["username"])
PY
)"

export PGPASSWORD="$(SECRET_JSON="${SECRET_JSON}" python3 - <<'PY'
import json
import os
print(json.loads(os.environ["SECRET_JSON"])["password"])
PY
)"

export PGHOST="localhost"
export PGPORT="5432"
export TFE_DB_HOST="${PGHOST}"
export TFE_DB_PORT="${PGPORT}"
export TFE_DB_USER="${PGUSER}"
export TFE_DB_PASSWORD="${PGPASSWORD}"
export TFE_WORKSPACE_ROOT="${REPO_ROOT}"

# The tunnel terminates on localhost, so certificate hostname validation against the
# remote RDS hostname would fail unless this local-only override is applied.
export TFE_DB_SSL_REJECT_UNAUTHORIZED="false"

echo "Running local runtime sync through localhost:${PGPORT}. Open the DB tunnel first in another terminal." >&2

cd "${REPO_ROOT}"
exec node "${SYNC_SCRIPT}"
