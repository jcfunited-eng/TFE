#!/usr/bin/env bash
# NON-CANONICAL — CH4 paper-book daily runner.
#
# Detached local loop: every weekday at 21:10 UTC (after US close) it runs
# the joint-field observer and updates the CH4 paper book, appending logs to
# artifacts/vtvr_observer/daily_runner.log. Local to this devcontainer only —
# no AWS, no production, no Guala contact. Dies with the container; restart
# with:  setsid nohup bash tools/vtvr_ch4_daily_runner.sh >/dev/null 2>&1 &
#
# Requires ALPACA data keys in the repo .env (read-only market data).

set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$REPO/artifacts/vtvr_observer/daily_runner.log"
mkdir -p "$(dirname "$LOG")"

echo "[runner] started $(date -u +%FT%TZ) pid=$$" >> "$LOG"

while true; do
  now=$(date -u +%s)
  # next 21:10 UTC
  target=$(date -u -d "today 21:10" +%s)
  if [ "$now" -ge "$target" ]; then
    target=$(date -u -d "tomorrow 21:10" +%s)
  fi
  sleep $(( target - now ))

  dow=$(date -u +%u)   # 6=Sat 7=Sun
  if [ "$dow" -ge 6 ]; then
    echo "[runner] $(date -u +%F) weekend — skip" >> "$LOG"
    continue
  fi

  {
    echo "═══ [runner] $(date -u +%FT%TZ) daily pass ═══"
    cd "$REPO" || exit 1
    set -a; source .env 2>/dev/null; set +a
    python3 tools/vtvr_daily_observer.py 2>&1
    python3 tools/vtvr_ch4_paper_sim.py 2>&1
  } >> "$LOG" 2>&1
done
