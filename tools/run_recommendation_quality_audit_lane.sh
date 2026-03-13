#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspaces/Tao_Financial_Engine"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$ROOT/backups/runtime/recommendation-quality-audit-probe-${TS}"
mkdir -p "$OUT_DIR"

set +e
python3 "$ROOT/tools/recommendation_quality_audit_lane.py" \
  --output-dir "$OUT_DIR" \
  > "$OUT_DIR/lane.stdout" \
  2> "$OUT_DIR/lane.stderr"
LANE_EXIT_CODE=$?
set -e

if [ "$LANE_EXIT_CODE" -ne 0 ]; then
  python3 - <<'PY' "$OUT_DIR" "$LANE_EXIT_CODE"
import datetime
import json
import os
import sys

out_dir = sys.argv[1]
runner_exit_code = int(sys.argv[2])
lane_summary = {
    "status": "error",
    "generated_at_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    "summary_json": os.path.join(out_dir, "summary.json"),
    "ranked_table_csv": os.path.join(out_dir, "ranked-table.csv"),
    "runner_exit_code": runner_exit_code,
    "failure_count": 1,
}
with open(os.path.join(out_dir, "lane-summary.json"), "w", encoding="utf-8") as fh:
    json.dump(lane_summary, fh, indent=2)
PY
  echo "$OUT_DIR"
  exit "$LANE_EXIT_CODE"
fi

if [ ! -f "$OUT_DIR/lane-summary.json" ]; then
  python3 - <<'PY' "$OUT_DIR"
import datetime
import json
import os
import sys

out_dir = sys.argv[1]
lane_summary = {
    "status": "error",
    "generated_at_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    "summary_json": os.path.join(out_dir, "summary.json"),
    "ranked_table_csv": os.path.join(out_dir, "ranked-table.csv"),
    "runner_exit_code": 1,
    "failure_count": 1,
    "reason": "lane_summary_missing",
}
with open(os.path.join(out_dir, "lane-summary.json"), "w", encoding="utf-8") as fh:
    json.dump(lane_summary, fh, indent=2)
PY
  echo "$OUT_DIR"
  exit 1
fi

echo "$OUT_DIR"
exit 0
