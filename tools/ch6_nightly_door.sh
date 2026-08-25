#!/bin/bash
# ch6_nightly_door.sh — the readings door, end to end, every close.
# pool (kernel facts admit) -> fine scan of the pool -> dossiers ->
# headless readings (delta only, capped) -> stage under the rulebook
# -> publish. Every step fails closed: any death means nothing stages
# and the log says why. Called by ch4_spring_daily_runner.sh after
# the store refresh and population backfill.
cd "$(dirname "$0")/.." || exit 1
exec 9>artifacts/vtvr_observer/.ch6_door.lock
flock -n 9 || { echo "[ch6-door] another run holds the lock; exiting"; exit 1; }
set -a; source .env 2>/dev/null; set +a
LOG=artifacts/vtvr_observer/ch6_door.log
echo "[ch6-door] start $(date -u +%FT%TZ)" >> "$LOG"

python tools/ch6_pool.py >> "$LOG" 2>&1 || { echo "[ch6-door] POOL FAILED — nothing stages" >> "$LOG"; exit 1; }
LATEST=$(python -c "import pandas as pd; print(str(pd.read_parquet('ch4_live_store.parquet', columns=['Date'])['Date'].max())[:10])")
POOL="artifacts/ch6_harvest/door/pool_${LATEST}.json"
[ -f "$POOL" ] || { echo "[ch6-door] pool file missing — nothing stages" >> "$LOG"; exit 1; }

SCAN_SYMBOLS_FILE="$POOL" SCAN_DAYS=130 SCAN_KEEP=25 \
  python tools/ch6_month_scan.py 8 >> "$LOG" 2>&1 \
  || { echo "[ch6-door] FINE SCAN FAILED — nothing stages" >> "$LOG"; exit 1; }

CH6_FINE_LANES=artifacts/ch6_harvest/month_lanes \
  python tools/ch6_read_pool.py "$POOL" >> "$LOG" 2>&1 \
  || { echo "[ch6-door] READING PASS FAILED — nothing stages" >> "$LOG"; exit 1; }

python tools/ch6_stage_slate.py >> "$LOG" 2>&1 \
  || { echo "[ch6-door] STAGING FAILED — book untouched" >> "$LOG"; exit 1; }

python tools/publish_channel_books.py >> "$LOG" 2>&1

# CH2 holdings get their nightly long-view readings after the CH6 door
# (Joseph's exit law 2026-08-25). Failure holds every position — the
# production engine ignores a missing or stale verdict sheet.
python tools/ch2_holdings_read.py >> "$LOG" 2>&1 \
  || echo "[ch6-door] CH2 READING PASS FAILED — holdings keep current protections" >> "$LOG"

echo "[ch6-door] done $(date -u +%FT%TZ)" >> "$LOG"
