#!/bin/bash
# Workspace loops watchdog — every five minutes, bring back any loop that
# has died. It reuses .devcontainer/post-start.sh (one list of loops, one
# /proc liveness check), so there is nothing to keep in sync here.
#
# Why (Claude 2026-09-23, receipts in docs/CH2_ENTRY_POOL_20260923.md and
# the CH6 book): tools/ch6_loop.sh was restarted SEVEN times between
# 2026-08-31 and 2026-09-23 — it dies every few days, not only on container
# restart, and postStartCommand only fires on a container start. While it
# was dead 2026-09-02..09-10, twenty CH6 positions ran past their 5-session
# clock; closing them on the clock would have been worth +$487 against a
# book that stands at -$512. The rules were right; they were not running.
#
# Start (post-start.sh does this on every container start / editor attach):
#   setsid nohup bash tools/loops_watchdog.sh >> artifacts/vtvr_observer/loops_watchdog.log 2>&1 &
cd "$(dirname "$0")/.." || exit 1
mkdir -p artifacts/vtvr_observer
exec 9>artifacts/vtvr_observer/.loops_watchdog.lock
flock -n 9 || { echo "[watchdog] another instance holds the lock; exiting"; exit 0; }
echo "[watchdog] started $(date -u +%FT%TZ) pid $$"

STALE_MIN=30

while true; do
  date -u +%FT%TZ > artifacts/vtvr_observer/.hb_loops_watchdog
  # relaunch whatever is down; "up:" lines are noise, everything else is kept
  POST_START_FROM_WATCHDOG=1 bash .devcontainer/post-start.sh 2>&1 \
    | grep -v "^\[post-start\] up: " \
    | sed "s/^/[watchdog $(date -u +%FT%TZ)] /"
  # a loop that is up but not beating is hung, not alive — say so, loudly.
  # (only loops that write a heartbeat can be judged this way)
  now=$(date +%s)
  for hb in artifacts/vtvr_observer/.hb_ch6_loop artifacts/vtvr_observer/.hb_spring_runner; do
    [ -f "$hb" ] || continue
    then=$(date -d "$(cat "$hb")" +%s 2>/dev/null) || continue
    age=$(( (now - then) / 60 ))
    if [ "$age" -gt "$STALE_MIN" ]; then
      echo "[watchdog $(date -u +%FT%TZ)] STALE HEARTBEAT ${hb##*/} — ${age} minutes old; the loop is up but not beating"
    fi
  done
  sleep 300 9>&-
done
