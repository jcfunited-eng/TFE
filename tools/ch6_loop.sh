#!/bin/bash
# CH6 fast-harvest loop — 5-minute polling during market hours.
# sync new CH3 entries at 13:32 UTC, poll every 5 min 13:35-19:50,
# end-of-day sweep at 19:55 UTC (armed sales + time exits), page after each.
# Restart after container restart:
#   nohup bash tools/ch6_loop.sh > artifacts/vtvr_observer/ch6_runner.log 2>&1 &
cd "$(dirname "$0")/.." || exit 1
set -a; source .env 2>/dev/null; set +a
echo "[ch6-loop] started $(date -u +%FT%TZ) pid $$"
last_sync=""; last_sweep=""
while true; do
  h=$(date -u +%H); m=$(date -u +%M); dow=$(date -u +%u); d=$(date -u +%F)
  # sync is idempotent and cheap — run it every cycle so entries made
  # at any hour (the nightly hunt) are adopted promptly
  python tools/ch6_fast_harvest.py sync > /dev/null 2>&1
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
