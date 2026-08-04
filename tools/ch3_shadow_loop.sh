#!/bin/bash
# CH3 page keeper: regenerates the shadow page with live marks every
# 30 min during market hours. The reveal-fade engine runs NIGHTLY from
# ch4_spring_daily_runner.sh (5-session holds; never flattened intraday).
# Restart: nohup bash tools/ch3_shadow_loop.sh > artifacts/vtvr_observer/ch3_shadow_runner.log 2>&1 &
cd "$(dirname "$0")/.." || exit 1
set -a; source .env 2>/dev/null; set +a
echo "[ch3-shadow] started $(date -u +%FT%TZ) pid $$"
while true; do
  h=$(date -u +%H); dow=$(date -u +%u)
  if [ "$dow" -le 5 ] && [ "$h" -ge 13 ] && [ "$h" -lt 21 ]; then
    python tools/ch3_shadow_page.py artifacts/vtvr_observer/ch3_shadow_page.html >> artifacts/vtvr_observer/ch3_shadow_passes.log 2>&1
  fi
  sleep 1800
done
