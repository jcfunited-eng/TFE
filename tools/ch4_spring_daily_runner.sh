#!/bin/bash
# Daily TFE source/reading chain. Each dependent step requires its predecessor
# to succeed; a failed refresh must never stage decisions from an old store.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

run_close_pass() {
  python tools/ch4_store_refresh.py || return
  python tools/ch3_supply_tail.py || return
  python tools/population_reading_backfill.py \
    artifacts/ch4_uf/population_universe_20260819.csv 8 || return
  CH4_STORE=ch4_live_store.parquet \
    CH4_HERD_EXPORT=artifacts/ch4_uf/herd_state_live.parquet \
    python tools/ch4_uf_spectrum_herd.py || return
  python tools/ch4_herd_kgate_live.py || return
  python tools/ch3_reveal_fade.py || return
  python tools/ch4_spring_page.py artifacts/vtvr_observer/ch4_page.html || return
  python tools/ch3_shadow_page.py artifacts/vtvr_observer/ch3_shadow_page.html || return
  python tools/ch6_perception_nightly.py || return
  # This child owns its own lock and log. It is reached only after all source
  # and reading stages above succeeded.
  nohup bash tools/ch6_nightly_door.sh >/dev/null 2>&1 &
}

# Sourcing defines the function for dependency-failure verification only.
if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  return 0
fi

exec 9>artifacts/vtvr_observer/.spring_runner.lock
flock -n 9 || { echo '[spring-runner] another instance holds the lock'; exit 1; }
set -a
if [[ -f .env ]]; then
  source .env || exit 1
fi
set +a
echo "[spring-runner] started $(date -u +%FT%TZ) pid $$"
while true; do
  date -u +%FT%TZ > artifacts/vtvr_observer/.hb_spring_runner
  now_h=$(date -u +%H)
  now_m=$(date -u +%M)
  dow=$(date -u +%u)
  if [[ "$dow" -le 5 && "$now_h" = '21' && "$now_m" -ge 10 && "$now_m" -lt 25 ]]; then
    echo "[spring-runner] close pass $(date -u +%FT%TZ)"
    if run_close_pass >> artifacts/vtvr_observer/spring_passes.log 2>&1; then
      echo "[spring-runner] close pass succeeded $(date -u +%FT%TZ)"
      sleep 3600 9>&-
    else
      status=$?
      echo "[spring-runner] close pass FAILED status=$status; downstream work refused" \
        | tee -a artifacts/vtvr_observer/spring_passes.log
    fi
  fi
  sleep 300 9>&-
done
