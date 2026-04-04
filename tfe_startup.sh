#!/bin/bash
# tfe_startup.sh — TFE container startup script
# Runs before Next.js: restores snapshot from S3, clears stale DB state,
# starts scheduled refresh daemon.

set -euo pipefail

echo "[TFE-STARTUP] ============================================"
echo "[TFE-STARTUP] TFE container starting up"
echo "[TFE-STARTUP] ============================================"

# Step 1: Restore snapshot from S3 (fast — seconds, not minutes)
echo "[TFE-STARTUP] Restoring UF snapshot from S3..."
cd /app
python3 tfe_snapshot_restore.py || echo "[TFE-STARTUP] Snapshot restore non-fatal failure — continuing."

# Step 2: Clear any stale running=true refresh state from previous container
echo "[TFE-STARTUP] Clearing stale refresh state..."
PGSSLMODE=require node /app/web/scripts/clear_stale_refresh_state.mjs || echo "[TFE-STARTUP] Stale state clear non-fatal failure — continuing."

# Step 3: Start scheduled refresh daemon in background
# Fires daily at 12:15 UTC via the internal refresh API (targeted_pfsc mode).
tfe_refresh_daemon() {
  local SCHEDULED_HOUR=12
  local SCHEDULED_MINUTE=15
  local BASE_URL="http://localhost:3000"
  local API_PATH="/api/admin/refresh"

  echo "[REFRESH-DAEMON] Started. Will trigger refresh daily at ${SCHEDULED_HOUR}:$(printf '%02d' ${SCHEDULED_MINUTE}) UTC."

  # Wait for Next.js to be ready before first potential trigger
  sleep 30

  while true; do
    NOW_H=$(date -u +%H)
    NOW_M=$(date -u +%M)
    NOW_H_INT=$((10#${NOW_H}))
    NOW_M_INT=$((10#${NOW_M}))

    if [ "${NOW_H_INT}" -eq "${SCHEDULED_HOUR}" ] && [ "${NOW_M_INT}" -eq "${SCHEDULED_MINUTE}" ]; then
      echo "[REFRESH-DAEMON] Triggering scheduled refresh at $(date -u '+%Y-%m-%dT%H:%M:%SZ')..."
      curl -sf -X POST "${BASE_URL}${API_PATH}" \
        -H "Content-Type: application/json" \
        -H "x-tfe-internal-refresh-token: ${TFE_INTERNAL_REFRESH_TOKEN:-}" \
        -d '{"action":"start","mode":"snapshot","triggerSource":"scheduled"}' \
        -o /tmp/refresh-daemon-response.json 2>/tmp/refresh-daemon-curl.log \
        && echo "[REFRESH-DAEMON] Refresh triggered. Response: $(cat /tmp/refresh-daemon-response.json | head -c 200)" \
        || echo "[REFRESH-DAEMON] Trigger failed — see /tmp/refresh-daemon-curl.log"
      # Sleep 90s to avoid double-firing within the same minute
      sleep 90
    fi

    sleep 55
  done
}

tfe_refresh_daemon &
echo "[TFE-STARTUP] Refresh daemon started (PID $!)."

# Step 4: Start Next.js (foreground — this is PID 1)
echo "[TFE-STARTUP] Starting Next.js..."
cd /app/web
exec npm run start -- -H 0.0.0.0 -p 3000
