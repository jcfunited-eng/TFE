#!/bin/bash
# Daily TFE source/reading chain. Each dependent step requires its predecessor
# to succeed; a failed refresh must never stage decisions from an old store.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

run_close_pass() {
  # 2026-09-29: reconcile BEFORE refreshing. Any roster split re-bases a
  # symbol's whole history at the provider, and the refresh (rightly)
  # refuses to append onto the old basis — which froze the store twice in a
  # week (WHLR 9:1 on 09-22, MTNB 15:1 on 09-28) and took the whole nightly
  # chain down with it. The reconcile replaces only the re-based symbols'
  # histories, under the refresh's own lock, and prints "clean" when there
  # is nothing to do. If it cannot verify a symbol it fails, and so does
  # the pass — nothing is published on a guess.
  python tools/ch4_store_reconcile_overlap.py || return
  python tools/ch4_store_refresh.py || return
  python tools/ch3_supply_tail.py || return
  python tools/population_reading_backfill.py \
    artifacts/ch4_uf/population_universe_20260819.csv 8 || return
  CH4_STORE=ch4_live_store.parquet \
    CH4_HERD_EXPORT=artifacts/ch4_uf/herd_state_live.parquet \
    python tools/ch4_uf_spectrum_herd.py || return
  python tools/ch4_herd_kgate_live.py || return
  # CH3 has no same-day guard of its own: on a catch-up rerun after a pass
  # that died past this step, running it again would double its positions.
  if python - <<'PY'
import json, sys, pandas as pd
latest = str(pd.read_parquet("ch4_live_store.parquet", columns=["Date"])["Date"].max())[:10]
try:
    days = json.load(open("artifacts/vtvr_observer/ch3_shadow_log.json")).get("days", {})
except FileNotFoundError:
    days = {}
sys.exit(0 if latest in days else 1)
PY
  then
    echo "[spring-runner] ch3 reveal-fade already ran for the store's latest close — skipped"
  else
    python tools/ch3_reveal_fade.py || return
  fi
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
# CATCH-UP (Claude 2026-10-07): a container restart in the middle of the
# close pass (10-06 21:44Z: killed during the population backfill) left the
# herd state unpublished, and the revived runner only ever tried again in the
# next evening's 21:10 window — CH6 refused every entry for a day. Now the
# date of each successful pass is stamped; whenever the market is closed
# (outside 13:00-21:10 UTC) and the stamp is older than the last weekday
# close pass that was due, the pass runs at once.
STAMP=artifacts/vtvr_observer/.spring_last_pass
pass_overdue() {
  [ -f "$STAMP" ] || return 1
  python3 - "$(cat "$STAMP")" <<'PY'
import sys, datetime as dt
now = dt.datetime.now(dt.timezone.utc)
if 13 <= now.hour < 21 or (now.hour == 21 and now.minute < 25):
    sys.exit(1)                      # market hours / the regular window
d = now.date()
if not (d.weekday() < 5 and (now.hour, now.minute) >= (21, 25)):
    d -= dt.timedelta(days=1)
while d.weekday() >= 5:
    d -= dt.timedelta(days=1)
sys.exit(0 if sys.argv[1] < d.isoformat() else 1)
PY
}
while true; do
  date -u +%FT%TZ > artifacts/vtvr_observer/.hb_spring_runner
  now_h=$(date -u +%H)
  now_m=$(date -u +%M)
  dow=$(date -u +%u)
  # 10# forces base ten: "08" and "09" are invalid octal and made this test
  # error out every hour at minutes 8 and 9 (seen in the log 2026-09-29).
  if [[ "$dow" -le 5 && "$now_h" = '21' && "$((10#$now_m))" -ge 10 && "$((10#$now_m))" -lt 25 ]]; then
    echo "[spring-runner] close pass $(date -u +%FT%TZ)"
    if run_close_pass >> artifacts/vtvr_observer/spring_passes.log 2>&1; then
      echo "[spring-runner] close pass succeeded $(date -u +%FT%TZ)"
      date -u +%F > "$STAMP"
      sleep 3600 9>&-
    else
      status=$?
      echo "[spring-runner] close pass FAILED status=$status; downstream work refused" \
        | tee -a artifacts/vtvr_observer/spring_passes.log
    fi
  fi
  if pass_overdue; then
    echo "[spring-runner] CATCH-UP close pass $(date -u +%FT%TZ) (last good pass $(cat "$STAMP"))"
    if run_close_pass >> artifacts/vtvr_observer/spring_passes.log 2>&1; then
      echo "[spring-runner] catch-up pass succeeded $(date -u +%FT%TZ)"
      date -u +%F > "$STAMP"
    else
      echo "[spring-runner] catch-up pass FAILED status=$?; retry next cycle" \
        | tee -a artifacts/vtvr_observer/spring_passes.log
    fi
  fi
  sleep 300 9>&-
done
