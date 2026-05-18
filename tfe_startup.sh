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
tfe_trigger_refresh() {
  # Sunday = universe + snapshot (discover new symbols)
  # All other days = snapshot only (incremental)
  local DAY_OF_WEEK
  DAY_OF_WEEK=$(date -u +%u)  # 1=Monday ... 7=Sunday
  local REFRESH_MODE="snapshot"
  if [ "${DAY_OF_WEEK}" -eq 7 ]; then
    REFRESH_MODE="universe_snapshot"
    echo "[REFRESH-DAEMON] Sunday — triggering Universe + Snapshot refresh at $(date -u '+%Y-%m-%dT%H:%M:%SZ')..."
  else
    echo "[REFRESH-DAEMON] Triggering Snapshot refresh at $(date -u '+%Y-%m-%dT%H:%M:%SZ')..."
  fi
  node -e "
    const http = require('http');
    const mode = '${REFRESH_MODE}';
    const body = JSON.stringify({action:'start',mode:mode,triggerSource:'scheduled'});
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
  " && echo "[REFRESH-DAEMON] Refresh triggered (mode=${REFRESH_MODE})." || echo "[REFRESH-DAEMON] Trigger failed."
}

tfe_refresh_daemon() {
  local SCHEDULED_HOUR=13
  local SCHEDULED_MINUTE=0

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

  # Catch-up check: if container started after the scheduled time and no
  # refresh ran today, fire immediately.  This prevents deploys or restarts
  # from causing missed refresh days.
  #
  # HOWEVER: if the S3 snapshot was restored and is fresh (< 18 hours old),
  # skip the catch-up.  Deploys should not trigger full rebuilds when the
  # data is already current.  The next scheduled refresh (13:00 UTC daily)
  # will update normally.
  NOW_H_INT=$((10#$(date -u +%H)))
  if [ "${NOW_H_INT}" -ge "${SCHEDULED_HOUR}" ]; then
    # First: check if the restored snapshot is fresh enough to skip rebuild
    SNAPSHOT_FRESH="NO"
    if [ -f /app/uf_snapshot.json ]; then
      SNAPSHOT_AGE_HOURS=$(python3 -c "
import os, time
try:
    mtime = os.path.getmtime('/app/uf_snapshot.json')
    age_hours = (time.time() - mtime) / 3600
    print(f'{age_hours:.1f}')
except Exception:
    print('999')
" 2>/dev/null || echo "999")
      echo "[REFRESH-DAEMON] Snapshot age: ${SNAPSHOT_AGE_HOURS} hours"
      # Fresh = less than 18 hours old (covers overnight + deploy next morning)
      IS_FRESH=$(python3 -c "print('YES' if float('${SNAPSHOT_AGE_HOURS}') < 18 else 'NO')" 2>/dev/null || echo "NO")
      if [ "${IS_FRESH}" = "YES" ]; then
        SNAPSHOT_FRESH="YES"
      fi
    fi

    if [ "${SNAPSHOT_FRESH}" = "YES" ]; then
      echo "[REFRESH-DAEMON] Snapshot is fresh (${SNAPSHOT_AGE_HOURS}h old). Skipping catch-up rebuild — next scheduled refresh at ${SCHEDULED_HOUR}:00 UTC."
    else
      # Snapshot is stale or missing — check DB as final fallback
      NEEDS_CATCHUP=$(node -e "
        const pg = require('pg');
        const pool = new pg.Pool({ssl:{rejectUnauthorized:false}});
        (async () => {
          try {
            const r = await pool.query(
              \"SELECT COUNT(*) as cnt FROM runtime_refresh_runs WHERE report_status = 'ok' AND completed_at >= (CURRENT_DATE AT TIME ZONE 'UTC')\"
            );
            const cnt = parseInt(r.rows[0]?.cnt ?? '0', 10);
            console.log(cnt > 0 ? 'NO' : 'YES');
          } catch (e) {
            console.log('YES');
          } finally {
            await pool.end();
          }
        })();
      " 2>/dev/null || echo "YES")

      if [ "${NEEDS_CATCHUP}" = "YES" ]; then
        echo "[REFRESH-DAEMON] Catch-up: snapshot stale/missing and no successful refresh today. Firing now."
        tfe_trigger_refresh
        sleep 90
      else
        echo "[REFRESH-DAEMON] Today's refresh already completed successfully. No catch-up needed."
      fi
    fi
  fi

  # Main scheduling loop
  local FIRED_TODAY=0
  while true; do
    NOW_H=$(date -u +%H)
    NOW_M=$(date -u +%M)
    NOW_H_INT=$((10#${NOW_H}))
    NOW_M_INT=$((10#${NOW_M}))

    # Reset fired flag at midnight
    if [ "${NOW_H_INT}" -eq 0 ] && [ "${NOW_M_INT}" -eq 0 ]; then
      FIRED_TODAY=0
    fi

    if [ "${NOW_H_INT}" -eq "${SCHEDULED_HOUR}" ] && [ "${NOW_M_INT}" -eq "${SCHEDULED_MINUTE}" ] && [ "${FIRED_TODAY}" -eq 0 ]; then
      tfe_trigger_refresh
      FIRED_TODAY=1
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

# Step 3c: Run fundamentals backfill on a recurring schedule.
# The backfill populates l5_fundamentals_normalized for Accumulate tickers.
# Runs every 3 hours to catch new tickers from each refresh cycle.
# Safe to overlap with refresh — it only reads runtime_decisions_latest
# and upserts fundamentals.
(
  sleep 180  # wait for Next.js + catch-up refresh to start
  while true; do
    echo "[TFE-BACKFILL] Starting fundamentals backfill..."
    cd /app
    PGSSLMODE=require python3 tools/backfill_accumulate_fundamentals.py 2>&1 \
      && echo "[TFE-BACKFILL] Backfill completed successfully." \
      || echo "[TFE-BACKFILL] Backfill failed (non-fatal)."
    sleep 10800  # 3 hours between runs
  done
) &
echo "[TFE-STARTUP] Fundamentals backfill daemon started (PID $!, first run in 3 min, then every 3h)."

# Step 4: Start Next.js (foreground — this is PID 1)
echo "[TFE-STARTUP] Starting Next.js..."
cd /app/web
exec npm run start -- -H 0.0.0.0 -p 3000
