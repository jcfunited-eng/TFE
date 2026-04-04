#!/bin/bash
# tfe_startup.sh — TFE container startup script
# Runs before Next.js: restores snapshot from S3, clears stale DB state.

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

# Step 3: Start Next.js (foreground — this is PID 1)
echo "[TFE-STARTUP] Starting Next.js..."
cd /app/web
exec npm run start -- -H 0.0.0.0 -p 3000
