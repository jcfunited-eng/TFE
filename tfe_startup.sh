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

# Harden secret file permissions to owner-only (600).
# tfe_session_secret.bin is created here if missing (Clerk is primary auth
# but the legacy TFE session key must exist for the security posture check).
echo "[TFE-STARTUP] Hardening secret file permissions..."
if [ ! -f /app/tfe_session_secret.bin ]; then
  node -e "require('fs').writeFileSync('/app/tfe_session_secret.bin', require('crypto').randomBytes(32), {mode: 0o600})" \
    && echo "[TFE-STARTUP] Created /app/tfe_session_secret.bin" \
    || echo "[TFE-STARTUP] Failed to create tfe_session_secret.bin (non-fatal)"
fi
for secret_file in /app/tfe_session_secret.bin /app/tfe_root_key.bin /app/tfe_users.json; do
  if [ -f "$secret_file" ]; then
    chmod 600 "$secret_file" && echo "[TFE-STARTUP] Hardened: $secret_file" || echo "[TFE-STARTUP] chmod failed (non-fatal): $secret_file"
  fi
done

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

# Step 3b: Start sentinel daemon — syncs Alpaca fills to DB every 5 min during market hours
PGSSLMODE=require node /app/web/scripts/execution/sentinel_daemon.mjs &
echo "[TFE-STARTUP] Sentinel daemon started (PID $!)."

# Step 4: Start Next.js (foreground — this is PID 1)
echo "[TFE-STARTUP] Starting Next.js..."
cd /app/web
exec npm run start -- -H 0.0.0.0 -p 3000
