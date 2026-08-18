#!/bin/bash
# TFE container startup and process supervisor.
# EventBridge is the sole refresh scheduling authority.

set -euo pipefail

readonly APP_ROOT="/app"
readonly HEARTBEAT_PATH="/tmp/tfe_process_health.json"
readonly HEARTBEAT_INTERVAL_SECONDS=10

sentinel_pid=""
backfill_pid=""
next_pid=""
shutting_down=0

process_alive() {
  local pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

write_heartbeat() {
  local temporary="${HEARTBEAT_PATH}.$$"
  local generated_at
  local sentinel_alive=false
  local backfill_alive=false
  local next_alive=false

  generated_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if process_alive "$sentinel_pid"; then sentinel_alive=true; fi
  if process_alive "$backfill_pid"; then backfill_alive=true; fi
  if process_alive "$next_pid"; then next_alive=true; fi

  printf '{"schema":"tfe.process-health.v1","generated_at_utc":"%s","processes":{"next":{"pid":%s,"alive":%s},"sentinel":{"pid":%s,"alive":%s},"fundamentals_backfill":{"pid":%s,"alive":%s}}}\n' \
    "$generated_at" "$next_pid" "$next_alive" "$sentinel_pid" "$sentinel_alive" \
    "$backfill_pid" "$backfill_alive" > "$temporary"
  mv "$temporary" "$HEARTBEAT_PATH"
}

stop_children() {
  local pid
  for pid in "$next_pid" "$sentinel_pid" "$backfill_pid"; do
    if process_alive "$pid"; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done
  for pid in "$next_pid" "$sentinel_pid" "$backfill_pid"; do
    if [ -n "$pid" ]; then
      wait "$pid" 2>/dev/null || true
    fi
  done
  rm -f "$HEARTBEAT_PATH"
}

shutdown() {
  if [ "$shutting_down" -eq 1 ]; then return; fi
  shutting_down=1
  trap - TERM INT
  echo "[TFE-SUPERVISOR] Shutdown requested; stopping all essential processes."
  stop_children
  exit 0
}

run_backfill_loop() {
  sleep 180
  while true; do
    echo "[TFE-BACKFILL] Starting fundamentals backfill..."
    cd "$APP_ROOT"
    if PGSSLMODE=require python3 tools/backfill_accumulate_fundamentals.py; then
      echo "[TFE-BACKFILL] Backfill completed."
    else
      echo "[TFE-BACKFILL] Backfill failed; the supervised loop remains alive for the next scheduled attempt."
    fi
    sleep 10800
  done
}

trap shutdown TERM INT

echo "[TFE-STARTUP] ============================================"
echo "[TFE-STARTUP] TFE container starting"
echo "[TFE-STARTUP] ============================================"

cd "$APP_ROOT"
echo "[TFE-STARTUP] Restoring one verified UF snapshot generation..."
python3 tfe_snapshot_restore.py

echo "[TFE-STARTUP] Hardening local secret-file permissions..."
if [ ! -f "$APP_ROOT/tfe_session_secret.bin" ]; then
  node -e "require('fs').writeFileSync('/app/tfe_session_secret.bin', require('crypto').randomBytes(32), {mode: 0o600})"
fi
for secret_file in "$APP_ROOT/tfe_session_secret.bin" "$APP_ROOT/tfe_root_key.bin" "$APP_ROOT/tfe_users.json"; do
  if [ -f "$secret_file" ]; then
    chmod 600 "$secret_file"
  fi
done

echo "[TFE-STARTUP] Clearing stale refresh state..."
PGSSLMODE=require node "$APP_ROOT/web/scripts/clear_stale_refresh_state.mjs"

echo "[TFE-STARTUP] Refresh scheduling is external. EventBridge is the only scheduled trigger authority."

PGSSLMODE=require node "$APP_ROOT/web/scripts/execution/sentinel_daemon.mjs" &
sentinel_pid=$!
echo "[TFE-STARTUP] Sentinel daemon started (PID ${sentinel_pid})."

run_backfill_loop &
backfill_pid=$!
echo "[TFE-STARTUP] Fundamentals backfill loop started (PID ${backfill_pid})."

(
  cd "$APP_ROOT/web"
  exec npm run start -- -H 0.0.0.0 -p 3000
) &
next_pid=$!
echo "[TFE-STARTUP] Next.js started (PID ${next_pid})."

while true; do
  write_heartbeat
  if ! process_alive "$next_pid"; then
    failed_process="Next.js"
    break
  fi
  if ! process_alive "$sentinel_pid"; then
    failed_process="sentinel"
    break
  fi
  if ! process_alive "$backfill_pid"; then
    failed_process="fundamentals backfill loop"
    break
  fi
  sleep "$HEARTBEAT_INTERVAL_SECONDS" &
  wait $! || true
done

echo "[TFE-SUPERVISOR] Essential process exited: ${failed_process}. Terminating container so ECS can replace it."
shutting_down=1
trap - TERM INT
stop_children
exit 1
