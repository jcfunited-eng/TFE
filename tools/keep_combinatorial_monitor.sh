#!/usr/bin/env bash
# tools/keep_combinatorial_monitor.sh — Supervisor daemon for Guala Combinatorial Chain Monitor.
#
# Periodically executes tools/monitor_combinatorial_chains.py every 300 seconds (5 minutes),
# tracking multi-beat vocal demand phrasing, spatial multi-room portal trajectories,
# and appending newly emergent chains to the cryptographic ledger.
set -euo pipefail

ROOT="/workspaces/Tao_Financial_Engine"
RUNTIME_DIR="$ROOT/backups/runtime"
LOG_PATH="$RUNTIME_DIR/combinatorial_chains_monitor.log"
LOCK_PATH="$RUNTIME_DIR/combinatorial_monitor.lock"
STOP_PATH="$RUNTIME_DIR/STOP_COMBINATORIAL_MONITOR"

mkdir -p "$RUNTIME_DIR"

cd "$ROOT"

while true; do
  if [ -f "$STOP_PATH" ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) stop file detected, exiting keep_combinatorial_monitor" >> "$LOG_PATH"
    exit 0
  fi

  # Execute one monitoring pass
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) executing combinatorial chain monitor pass" >> "$LOG_PATH"
  python3 "$ROOT/tools/monitor_combinatorial_chains.py" >> "$LOG_PATH" 2>&1 || true

  # Sleep for 300 seconds before next pass
  sleep 300
done
