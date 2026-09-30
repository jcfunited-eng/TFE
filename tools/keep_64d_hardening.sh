#!/usr/bin/env bash
# ==============================================================================
# tools/keep_64d_hardening.sh
# 
# Persistent supervisor daemon for continuous 64-column cortical array hardening.
# Ensures continuous experience delivery and plastic deformation across the
# multi-day window leading up to hardware delivery.
# ==============================================================================

cd "$(dirname "$0")/.." || exit 1
mkdir -p backups/runtime

LOCKFILE="backups/runtime/.lock_64d"
STOPFILE="backups/runtime/STOP_64D"

echo "[*] Supervisor initialized for 64-Column Cortical Array Hardening Daemon."

while true; do
    if [ -f "$STOPFILE" ]; then
        echo "[*] Stop flag ($STOPFILE) detected. Terminating supervisor."
        exit 0
    fi

    # Ensure single instance holds lock
    exec 200>"$LOCKFILE"
    if flock -n 200; then
        echo "[*] Launching run_64d_continuous_hardening.py at $(date -u +%Y-%m-%dT%H:%M:%SZ)..."
        python3 tools/run_64d_continuous_hardening.py >> backups/runtime/guala_64d_hardening.out 2>&1
        echo "[*] Hardening loop terminated at $(date -u +%Y-%m-%dT%H:%M:%SZ). Restarting in 5s..."
        sleep 5
    else
        echo "[*] Another instance holds lock. Sleeping 30s..."
        sleep 30
    fi
done
