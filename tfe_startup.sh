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
# Fires daily at 13:00 UTC (9:00 AM ET) — after previous day's bars are fully settled
# and 30 min before market open, so PEE-1 orders are queued before 9:30 AM ET.
tfe_refresh_daemon() {
  local SCHEDULED_HOUR=13
  local SCHEDULED_MINUTE=0
  local BASE_URL="http://localhost:3000"
  local API_PATH="/api/admin/refresh"

  echo "[REFRESH-DAEMON] Started. Will trigger refresh daily at ${SCHEDULED_HOUR}:$(printf '%02d' ${SCHEDULED_MINUTE}) UTC."

  # Wait for Next.js to be ready, then verify HTTP trigger works
  sleep 30
  echo "[REFRESH-DAEMON] Verifying HTTP trigger connectivity..."
  node -e "
    const http = require('http');
    const req = http.request({hostname:'localhost',port:3000,path:'/api/health',method:'GET'},
      res => console.log('[REFRESH-DAEMON] Connectivity OK — HTTP '+res.statusCode));
    req.on('error', e => console.error('[REFRESH-DAEMON] Connectivity FAILED: '+e.message));
    req.end();
  " 2>&1 || true

  while true; do
    NOW_H=$(date -u +%H)
    NOW_M=$(date -u +%M)
    NOW_H_INT=$((10#${NOW_H}))
    NOW_M_INT=$((10#${NOW_M}))

    if [ "${NOW_H_INT}" -eq "${SCHEDULED_HOUR}" ] && [ "${NOW_M_INT}" -eq "${SCHEDULED_MINUTE}" ]; then
      echo "[REFRESH-DAEMON] Triggering scheduled refresh at $(date -u '+%Y-%m-%dT%H:%M:%SZ')..."
      node -e "
        const http = require('http');
        const body = JSON.stringify({action:'start',mode:'snapshot',triggerSource:'scheduled'});
        const req = http.request({
          hostname:'localhost', port:3000, path:'/api/admin/refresh',
          method:'POST',
          headers:{'Content-Type':'application/json','Content-Length':Buffer.byteLength(body),
                   'x-tfe-internal-refresh-token':process.env.TFE_INTERNAL_REFRESH_TOKEN||''}
        }, res => {
          let d=''; res.on('data',c=>d+=c);
          res.on('end',()=>{ console.log('[REFRESH-DAEMON] Response HTTP '+res.statusCode+': '+d.slice(0,200)); });
        });
        req.on('error', e => console.error('[REFRESH-DAEMON] Request error: '+e.message));
        req.write(body); req.end();
      " && echo "[REFRESH-DAEMON] Refresh triggered." || echo "[REFRESH-DAEMON] Trigger failed."
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
