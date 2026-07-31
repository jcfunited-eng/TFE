#!/bin/bash
# CH4 spring-channel daily runner — weekdays at 21:10 UTC, one pass per
# close. Engine: vtvr_spring_v1 (VTVR kernel + spring governance).
# Restart after container restart:
#   nohup bash tools/ch4_spring_daily_runner.sh > artifacts/vtvr_observer/spring_runner.log 2>&1 &
cd "$(dirname "$0")/.." || exit 1
set -a; source .env 2>/dev/null; set +a
echo "[spring-runner] started $(date -u +%FT%TZ) pid $$"
while true; do
  now_h=$(date -u +%H); now_m=$(date -u +%M); dow=$(date -u +%u)
  if [ "$dow" -le 5 ] && [ "$now_h" = "21" ] && [ "$now_m" -ge 10 ] && [ "$now_m" -lt 25 ]; then
    echo "[spring-runner] close pass $(date -u +%FT%TZ)"
    python tools/ch4_vtvr_spring.py >> artifacts/vtvr_observer/spring_passes.log 2>&1
    sleep 1200
  fi
  sleep 300
done
