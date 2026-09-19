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

# READING PASS OFF (Joseph 2026-09-01): graded against outcomes —
# 243 readings, picks moved identically to rejects. The study earned
# nothing; it spends nothing. Staging now takes the whole damaged
# pool under the rules alone, freshest damage first.

python tools/ch6_stage_slate.py >> "$LOG" 2>&1 \
  || { echo "[ch6-door] STAGING FAILED — book untouched" >> "$LOG"; exit 1; }

python tools/ch3_recovery_engine.py >> "$LOG" 2>&1 \
  || echo "[ch6-door] CH3 RECOVERY ENGINE FAILED — its book untouched" >> "$LOG"

python tools/publish_channel_books.py >> "$LOG" 2>&1

# CH2 HOLDINGS READING PASS OFF (Joseph 2026-09-19): "hundreds of these
# individual ticker assessments — they need to stop". The pass spawned one
# model session per held stock every night (six at a time, ~20 a night) and
# was the visible token burn in his history.
#
# What this removes: the DRIVE_DYING / DEAD verdicts of Joseph's exit law
# 2026-08-25. The production engine ignores a sheet older than four days and
# holds on a missing one, so after four days the sellers are the dead clock
# (>16 closed sessions more than 5% below entry with no heal), the 90-day
# wall, the -20% brake and the +20% ratchet floor. Turning it back on is
# this one line.
# python tools/ch2_holdings_read.py >> "$LOG" 2>&1 \
#   || echo "[ch6-door] CH2 READING PASS FAILED — holdings keep current protections" >> "$LOG"
echo "[ch6-door] CH2 reading pass OFF (Joseph 2026-09-19) — no per-ticker model sessions" >> "$LOG"

echo "[ch6-door] done $(date -u +%FT%TZ)" >> "$LOG"
