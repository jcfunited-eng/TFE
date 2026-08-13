#!/bin/bash
# CH4 daily runner — weekdays at 21:10 UTC, one pass per close.
# Engine: herd_kgate_v1 (herd-conditioned species, K=3 gate exits).
# Nightly sequence: store refresh -> herd state export -> engine -> page.
# Restart after container restart:
#   nohup bash tools/ch4_spring_daily_runner.sh > artifacts/vtvr_observer/ch4_spring_runner.log 2>&1 &
cd "$(dirname "$0")/.." || exit 1
set -a; source .env 2>/dev/null; set +a
echo "[spring-runner] started $(date -u +%FT%TZ) pid $$"
while true; do
  now_h=$(date -u +%H); now_m=$(date -u +%M); dow=$(date -u +%u)
  if [ "$dow" -le 5 ] && [ "$now_h" = "21" ] && [ "$now_m" -ge 10 ] && [ "$now_m" -lt 25 ]; then
    echo "[spring-runner] close pass $(date -u +%FT%TZ)"
    {
      python tools/ch4_store_refresh.py
      python tools/ch3_supply_tail.py
      CH4_STORE=ch4_live_store.parquet \
        CH4_HERD_EXPORT=artifacts/ch4_uf/herd_state_live.parquet \
        python tools/ch4_uf_spectrum_herd.py
      python tools/ch4_herd_kgate_live.py
      python tools/ch3_reveal_fade.py
      python tools/ch4_spring_page.py artifacts/vtvr_observer/ch4_page.html
      python tools/ch3_shadow_page.py artifacts/vtvr_observer/ch3_shadow_page.html
    } >> artifacts/vtvr_observer/spring_passes.log 2>&1
    echo "[spring-runner] close pass done $(date -u +%FT%TZ)"
    sleep 3600
  fi
  sleep 300
done
