#!/bin/bash
# CH3 shadow hunter loop: cycles every 15 min during market hours,
# grades at 20:05 UTC. Restart: nohup bash tools/ch3_shadow_loop.sh > artifacts/vtvr_observer/ch3_shadow_runner.log 2>&1 &
cd "$(dirname "$0")/.." || exit 1
set -a; source .env 2>/dev/null; set +a
echo "[ch3-shadow] started $(date -u +%FT%TZ) pid $$"
while true; do
  h=$(date -u +%H); m=$(date -u +%M); dow=$(date -u +%u)
  if [ "$dow" -le 5 ]; then
    if [ "$h" -ge 13 ] && [ "$h" -lt 20 ]; then
      if [ "$h" -gt 13 ] || [ "$m" -ge 35 ]; then
        python tools/ch3_shadow_hunter.py cycle >> artifacts/vtvr_observer/ch3_shadow_passes.log 2>&1
      fi
    fi
    if [ "$h" = "20" ] && [ "$m" -ge 5 ] && [ "$m" -lt 20 ]; then
      python tools/ch3_shadow_hunter.py close >> artifacts/vtvr_observer/ch3_shadow_passes.log 2>&1
      sleep 900
    fi
  fi
  sleep 900
done
