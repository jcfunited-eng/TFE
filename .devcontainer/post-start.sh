#!/bin/bash
# Runs on EVERY container start (devcontainer postStartCommand), not only on
# creation: bring the workspace's long-running loops back. Each loop holds its
# own single-instance lock or is guarded here by a /proc scan (pgrep is not
# always present), so calling this repeatedly is safe.
#
# Why this exists (Joseph 2026-09-15, "can you fix that fragility"): the CH2
# nightly reading that banks winners (tools/ch4_spring_daily_runner.sh ->
# tools/ch6_nightly_door.sh -> tools/ch2_holdings_read.py) died with every
# container restart; its verdict sheet is ignored after four days, after
# which only the dead clock, the 90-day wall and the -20% brake could sell.
cd /workspaces/Tao_Financial_Engine || exit 1
mkdir -p artifacts/vtvr_observer

is_up() {
  local needle="$1" p c
  for p in /proc/[0-9]*; do
    c=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null) || continue
    case "$c" in *"$needle"*) [[ "$c" == *sleep* ]] || return 0;; esac
  done
  return 1
}

start_loop() {
  local script="$1" log="$2"
  if is_up "$script"; then
    echo "[post-start] up: $script"
  else
    setsid nohup bash "$script" >> "$log" 2>&1 < /dev/null &
    disown
    echo "[post-start] started: $script (pid $!)"
  fi
}

start_loop tools/ch4_spring_daily_runner.sh        artifacts/vtvr_observer/ch4_spring_runner.log
start_loop tools/ch6_loop.sh                       artifacts/vtvr_observer/ch6_runner.log
start_loop tools/ch3_shadow_loop.sh                artifacts/vtvr_observer/ch3_shadow_loop.log
start_loop tools/channel_book_publication_loop.sh  artifacts/vtvr_observer/channel_book_publication.log
start_loop tools/db_rotation_guard.sh              artifacts/vtvr_observer/db_rotation_guard.log
# 2026-09-23: the loops die every few days, not only on container start
# (ch6_loop.sh restarted seven times 08-31..09-23). The watchdog re-runs this
# script every five minutes; it is also started here, and it also runs on
# every editor attach (devcontainer postAttachCommand) as a second trigger.
start_loop tools/loops_watchdog.sh                 artifacts/vtvr_observer/loops_watchdog.log
if [ "${POST_START_FROM_WATCHDOG:-0}" != "1" ]; then
  date -u +%FT%TZ > artifacts/vtvr_observer/.post_start_last_run
fi
