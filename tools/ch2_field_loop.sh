#!/usr/bin/env bash
# CH2 field governance — nightly trigger. Runs the field job INSIDE the
# production container (its own daily_bars, its own database) after the
# nightly refresh has synced the day's bars, and the filings sync once a week.
# Writes ch2_field_state / ch2_field_eligible; the next morning's CH2 entry
# pass reads them (FIELD-R1). Log: artifacts/vtvr_observer/ch2_field_loop.log
set -u
cd /workspaces/Tao_Financial_Engine
LOG=artifacts/vtvr_observer/ch2_field_loop.log
HB=artifacts/vtvr_observer/.hb_ch2_field
mkdir -p artifacts/vtvr_observer
task() { aws ecs list-tasks --cluster tfe-web-cluster --service-name tfe-web-service-lb --region us-east-1 --desired-status RUNNING --query 'taskArns[0]' --output text | awk -F/ '{print $NF}'; }
run_in_prod() { # $1 = command
  local t; t=$(task)
  timeout 1800 aws ecs execute-command --cluster tfe-web-cluster --task "$t" --container tfe-web --region us-east-1 --interactive --command "sh -c '$1'" 2>&1 | grep -v -E '^$|session'
}
last_slot=""
while true; do
  date +%s > "$HB"
  now_h=$(date -u +%H); now_m=$(date -u +%M); today=$(date -u +%F); dow=$(date -u +%u)
  # two runs a day: 01:15 UTC (after the nightly refresh has synced the session's bars) and
  # 12:30 UTC (a second chance before the 13:45 UTC entry pass). Each recomputes as of the
  # last bar in daily_bars; rerunning on the same bars rewrites the same state.
  slot=""
  if [ "$now_h" = "01" ] && [ "$((10#$now_m))" -ge 15 ]; then slot="$today-a"; fi
  if [ "$now_h" = "12" ] && [ "$((10#$now_m))" -ge 30 ]; then slot="$today-b"; fi
  if [ -n "$slot" ] && [ "$last_slot" != "$slot" ]; then
    echo "[$(date -u +%FT%TZ)] field job start ($slot)" >> "$LOG"
    if [ "$dow" = "6" ] && [ "$slot" = "$today-a" ]; then run_in_prod 'cd /app && nice -n 10 python3 tools/ch2_filings_sync.py > /tmp/fil.log 2>&1; tail -n 2 /tmp/fil.log' >> "$LOG" 2>&1; fi
    run_in_prod 'cd /app && nice -n 10 python3 tools/ch2_field_nightly_db.py > /tmp/fdb.log 2>&1; echo exit=$?; grep -E "as of|field_long|priority|bear|eligible_names|wrote|Traceback|Error" /tmp/fdb.log | head -12' >> "$LOG" 2>&1
    echo "[$(date -u +%FT%TZ)] field job end" >> "$LOG"
    last_slot="$slot"
  fi
  sleep 60
done
