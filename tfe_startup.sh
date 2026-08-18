#!/bin/bash
# TFE container startup. EventBridge is the sole refresh scheduling authority.

set -euo pipefail

echo "[TFE-STARTUP] ============================================"
echo "[TFE-STARTUP] TFE container starting"
echo "[TFE-STARTUP] ============================================"

cd /app
echo "[TFE-STARTUP] Restoring one verified UF snapshot generation..."
python3 tfe_snapshot_restore.py

echo "[TFE-STARTUP] Hardening local secret-file permissions..."
if [ ! -f /app/tfe_session_secret.bin ]; then
  node -e "require('fs').writeFileSync('/app/tfe_session_secret.bin', require('crypto').randomBytes(32), {mode: 0o600})"
fi
for secret_file in /app/tfe_session_secret.bin /app/tfe_root_key.bin /app/tfe_users.json; do
  if [ -f "$secret_file" ]; then
    chmod 600 "$secret_file"
  fi
done

echo "[TFE-STARTUP] Clearing stale refresh state..."
PGSSLMODE=require node /app/web/scripts/clear_stale_refresh_state.mjs

echo "[TFE-STARTUP] Refresh scheduling is external. EventBridge is the only scheduled trigger authority."

PGSSLMODE=require node /app/web/scripts/execution/sentinel_daemon.mjs &
sentinel_pid=$!
echo "[TFE-STARTUP] Sentinel daemon started (PID ${sentinel_pid})."

(
  sleep 180
  while true; do
    echo "[TFE-BACKFILL] Starting fundamentals backfill..."
    cd /app
    if PGSSLMODE=require python3 tools/backfill_accumulate_fundamentals.py; then
      echo "[TFE-BACKFILL] Backfill completed."
    else
      echo "[TFE-BACKFILL] Backfill failed; next attempt remains scheduled."
    fi
    sleep 10800
  done
) &
backfill_pid=$!
echo "[TFE-STARTUP] Fundamentals backfill started (PID ${backfill_pid})."

echo "[TFE-STARTUP] Starting Next.js..."
cd /app/web
exec npm run start -- -H 0.0.0.0 -p 3000
