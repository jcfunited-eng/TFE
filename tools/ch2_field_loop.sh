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
last_day=""
while true; do
  date +%s > "$HB"
  now_h=$(date -u +%H); now_m=$(date -u +%M); today=$(date -u +%F); dow=$(date -u +%u)
  # 23:30–23:59 UTC on weekdays, once a day: the refresh has run (21:00 UTC) and bars are synced
  if [ "$dow" -le 5 ] && [ "$now_h" = "23" ] && [ "$((10#$now_m))" -ge 30 ] && [ "$last_day" != "$today" ]; then
    echo "[$(date -u +%FT%TZ)] field job start" >> "$LOG"
    if [ "$dow" = "5" ]; then run_in_prod 'cd /app && nice -n 10 python3 tools/ch2_filings_sync.py > /tmp/fil.log 2>&1; tail -n 2 /tmp/fil.log' >> "$LOG" 2>&1; fi
    run_in_prod 'cd /app && nice -n 10 python3 tools/ch2_field_nightly_db.py > /tmp/fdb.log 2>&1; echo exit=$?; grep -E "as of|field_long|priority|bear|eligible_names|wrote|Traceback|Error" /tmp/fdb.log | head -12' >> "$LOG" 2>&1
    echo "[$(date -u +%FT%TZ)] field job end" >> "$LOG"
    last_day="$today"
  fi
  sleep 60
done
