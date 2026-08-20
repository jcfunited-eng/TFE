#!/bin/bash
# CH6 fast-harvest loop — 5-minute polling during market hours.
# CH6 is its own channel: it runs its OWN entry scan after the close,
# polls for display 13:35-19:50, and sweeps at 19:55 UTC banking anything
# at +2% or better (Joseph's fast-cash law 2026-08-19). It never reads CH3's book.
# Restart after container restart:
#   nohup bash tools/ch6_loop.sh > artifacts/vtvr_observer/ch6_runner.log 2>&1 &
cd "$(dirname "$0")/.." || exit 1
# single-instance lock: a duplicate loop silently corrupts the book
# via last-writer-wins (Rule 11 finding 2026-08-19)
exec 9>artifacts/vtvr_observer/.ch6_loop.lock
flock -n 9 || { echo "[ch6-loop] another instance holds the lock; exiting"; exit 1; }
set -a; source .env 2>/dev/null; set +a
echo "[ch6-loop] started $(date -u +%FT%TZ) pid $$"
last_sweep=""; last_pmc=""
while true; do
  hm=$((10#$(date -u +%H%M)))
  if [ $hm -ge 1300 ] && [ $hm -le 1330 ] && [ "$last_pmc" != "$(date -u +%F)" ]; then
    last_pmc="$(date -u +%F)"
    python tools/ch_premarket_cut.py >> artifacts/vtvr_observer/ch6_runner.log 2>&1
  fi
  h=$(date -u +%H); m=$(date -u +%M); dow=$(date -u +%u); d=$(date -u +%F)
  # CH6's OWN entry scan. Guarded inside by the processed-day stamp, so
  # running it every cycle can never open a position twice.
  # hunt output goes to the log — a refused or crashing entry scan
  # must be visible, never discarded (Rule 11 finding 2026-08-19)
  python tools/ch6_fast_harvest.py hunt >> artifacts/vtvr_observer/ch6_runner.log 2>&1
  if [ "$dow" -le 5 ]; then
    if { [ "$h" -ge 14 ] || { [ "$h" = "13" ] && [ "$m" -ge 35 ]; }; } \
        && { [ "$h" -lt 19 ] || { [ "$h" = "19" ] && [ "$m" -lt 50 ]; }; }; then
      python tools/ch6_fast_harvest.py poll
      python tools/ch6_page.py artifacts/vtvr_observer/ch6_page.html
    fi
    if [ "$h" = "19" ] && [ "$m" -ge 55 ] && [ "$last_sweep" != "$d" ]; then
      python tools/ch6_fast_harvest.py sweep
      python tools/ch6_page.py artifacts/vtvr_observer/ch6_page.html
      last_sweep="$d"
    fi
  fi
  sleep 300
done
