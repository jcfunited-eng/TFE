#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspaces/Tao_Financial_Engine"
BASE_URL="${TFE_BASE_URL:-https://taofinancialengine.com}"
CLUSTER="${TFE_ECS_CLUSTER:-tfe-web-cluster}"
SERVICE="${TFE_ECS_SERVICE:-tfe-web-service-lb}"
REGION="${AWS_REGION:-us-east-1}"

RECO_NONREGRESSION_ENABLED="${TFE_RECO_NONREGRESSION_ENABLED:-1}"
RECO_MAX_COVERAGE_DROP="${TFE_RECO_MAX_COVERAGE_DROP:-0.0}"
RECO_MAX_FALLBACK_RISE="${TFE_RECO_MAX_FALLBACK_RISE:-0.0}"

RECO_QUALITY_NONREGRESSION_ENABLED="${TFE_RECO_QUALITY_NONREGRESSION_ENABLED:-1}"
RECO_QUALITY_MAX_H5_DROP="${TFE_RECO_QUALITY_MAX_H5_DROP:-0.0}"
RECO_QUALITY_MAX_H20_DROP="${TFE_RECO_QUALITY_MAX_H20_DROP:-0.0}"
RECO_QUALITY_MAX_H60_DROP="${TFE_RECO_QUALITY_MAX_H60_DROP:-0.0}"
RECO_QUALITY_MAX_AVG_DROP="${TFE_RECO_QUALITY_MAX_AVG_DROP:-0.0}"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR_DEFAULT="$ROOT/backups/runtime/site-reliability-contract-gate-${TS}"
OUT_DIR="$OUT_DIR_DEFAULT"
OUTPUT_JSON=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --out-dir)
      if [ "$#" -lt 2 ]; then
        echo "missing value for --out-dir" >&2
        exit 2
      fi
      OUT_DIR="$2"
      shift 2
      ;;
    --output-json)
      if [ "$#" -lt 2 ]; then
        echo "missing value for --output-json" >&2
        exit 2
      fi
      OUTPUT_JSON="$2"
      shift 2
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$OUT_DIR"

run_lane() {
  local lane_name="$1"
  local script_path="$2"
  local result_path="$OUT_DIR/${lane_name}.result.json"
  local stdout_log="$OUT_DIR/${lane_name}.stdout.log"
  local stderr_log="$OUT_DIR/${lane_name}.stderr.log"

  set +e
  TFE_BASE_URL="$BASE_URL" TFE_ECS_CLUSTER="$CLUSTER" TFE_ECS_SERVICE="$SERVICE" AWS_REGION="$REGION" \
    "$script_path" >"$stdout_log" 2>"$stderr_log"
  local runner_exit_code=$?
  set -e

  local lane_dir=""
  if [ -s "$stdout_log" ]; then
    lane_dir="$(tail -n 1 "$stdout_log" | tr -d '\r')"
  fi

  local lane_summary_path=""
  local lane_status="error"
  local probe_exit_code=""
  local failure_count=""

  if [ -n "$lane_dir" ] && [ -f "$lane_dir/lane-summary.json" ]; then
    lane_summary_path="$lane_dir/lane-summary.json"
    lane_status="$(jq -r '.status // "error"' "$lane_summary_path")"
    probe_exit_code="$(jq -r '.probe_exit_code // empty' "$lane_summary_path")"
    failure_count="$(jq -r '.failure_count // empty' "$lane_summary_path")"
  fi

  python3 - <<'PY' "$result_path" "$lane_name" "$script_path" "$runner_exit_code" "$lane_dir" "$lane_summary_path" "$lane_status" "$probe_exit_code" "$failure_count" "$stdout_log" "$stderr_log"
import json
import sys

result_path = sys.argv[1]
lane_name = sys.argv[2]
script_path = sys.argv[3]
runner_exit_code = int(sys.argv[4])
lane_dir = sys.argv[5]
lane_summary_path = sys.argv[6]
lane_status = sys.argv[7]
probe_exit_code_raw = sys.argv[8]
failure_count_raw = sys.argv[9]
stdout_log = sys.argv[10]
stderr_log = sys.argv[11]

probe_exit_code = None
if probe_exit_code_raw not in ("", "null", "None"):
    try:
        probe_exit_code = int(float(probe_exit_code_raw))
    except Exception:
        probe_exit_code = None

failure_count = None
if failure_count_raw not in ("", "null", "None"):
    try:
        failure_count = int(float(failure_count_raw))
    except Exception:
        failure_count = None

lane_pass = (
    runner_exit_code == 0
    and lane_status == "pass"
    and (probe_exit_code is None or probe_exit_code == 0)
)

payload = {
    "lane": lane_name,
    "script": script_path,
    "runner_exit_code": runner_exit_code,
    "lane_dir": lane_dir,
    "lane_summary_path": lane_summary_path,
    "lane_status": lane_status,
    "probe_exit_code": probe_exit_code,
    "failure_count": failure_count,
    "stdout_log": stdout_log,
    "stderr_log": stderr_log,
    "pass": bool(lane_pass),
}

with open(result_path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2)
PY
}

run_recommendations_nonregression_gate() {
  local recommendations_result_path="$OUT_DIR/recommendations.result.json"
  local result_path="$OUT_DIR/recommendations_nonregression.result.json"

  python3 - <<'PY' "$ROOT" "$recommendations_result_path" "$result_path" "$RECO_NONREGRESSION_ENABLED" "$RECO_MAX_COVERAGE_DROP" "$RECO_MAX_FALLBACK_RISE"
import datetime
import glob
import json
import os
import sys
from typing import Any, Dict

root = sys.argv[1]
recommendations_result_path = sys.argv[2]
result_path = sys.argv[3]
enabled_raw = str(sys.argv[4]).strip()
max_coverage_drop = float(sys.argv[5])
max_fallback_rise = float(sys.argv[6])

enabled = enabled_raw not in {"0", "false", "False", "no", "NO", "off", "OFF"}

def utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

def extract_probe_metrics(summary_path: str) -> Dict[str, Any]:
    payload = load_json(summary_path)
    parsed = payload["details"]["recommendations_api"]["parsed"]
    health = parsed["recommendationHealth"]
    return {
        "coverage_rate": float(health["coverageRate"]),
        "fallback_rate": float(health["fallbackRate"]),
        "insufficient_bars_rows": int(health["insufficientBarsRows"]),
        "unmapped_rows": int(health["unmappedRows"]),
        "policy_mapped_rows": int(health["policyMappedRows"]),
        "run_id": str(parsed.get("run_id", "")),
        "generated_at_utc": str(parsed.get("generated_at_utc", "")),
        "probe_summary_path": summary_path,
    }

result = {
    "lane": "recommendations_nonregression",
    "generated_at_utc": utc_now(),
    "enabled": bool(enabled),
    "pass": False,
    "reason": "uninitialized",
    "max_coverage_drop": float(max_coverage_drop),
    "max_fallback_rise": float(max_fallback_rise),
    "current": None,
    "previous": None,
    "delta": None,
}

if not os.path.isfile(recommendations_result_path):
    result["reason"] = "recommendations_result_missing"
else:
    rec_result = load_json(recommendations_result_path)
    if not bool(enabled):
        result["pass"] = True
        result["reason"] = "nonregression_gate_disabled"
    elif not bool(rec_result.get("pass", False)):
        result["reason"] = "recommendations_lane_failed"
    else:
        current_lane_dir = str(rec_result.get("lane_dir", "")).strip()
        if not current_lane_dir:
            result["reason"] = "recommendations_lane_dir_missing"
        else:
            current_probe_summary = os.path.join(current_lane_dir, "probe", "summary.json")
            if not os.path.isfile(current_probe_summary):
                result["reason"] = "current_probe_summary_missing"
            else:
                current_metrics = extract_probe_metrics(current_probe_summary)
                result["current"] = current_metrics

                prev_probe_summary = ""
                pattern = os.path.join(root, "backups", "runtime", "recommendations-consistency-probe-*")
                for candidate in sorted(glob.glob(pattern), reverse=True):
                    if os.path.abspath(candidate) == os.path.abspath(current_lane_dir):
                        continue
                    lane_summary = os.path.join(candidate, "lane-summary.json")
                    probe_summary = os.path.join(candidate, "probe", "summary.json")
                    if not os.path.isfile(probe_summary):
                        continue
                    if os.path.isfile(lane_summary):
                        try:
                            lane_payload = load_json(lane_summary)
                        except Exception:
                            continue
                        if str(lane_payload.get("status", "")) != "pass":
                            continue
                    prev_probe_summary = probe_summary
                    break

                if not prev_probe_summary:
                    result["pass"] = True
                    result["reason"] = "no_previous_probe_baseline"
                else:
                    previous_metrics = extract_probe_metrics(prev_probe_summary)
                    result["previous"] = previous_metrics

                    delta_coverage = float(current_metrics["coverage_rate"] - previous_metrics["coverage_rate"])
                    delta_fallback = float(current_metrics["fallback_rate"] - previous_metrics["fallback_rate"])
                    delta_insufficient = int(
                        current_metrics["insufficient_bars_rows"] - previous_metrics["insufficient_bars_rows"]
                    )
                    delta_unmapped = int(current_metrics["unmapped_rows"] - previous_metrics["unmapped_rows"])

                    coverage_nonregression = bool(delta_coverage >= -max_coverage_drop)
                    fallback_nonregression = bool(delta_fallback <= max_fallback_rise)
                    improved = bool(delta_coverage > 0.0 or delta_fallback < 0.0)

                    result["delta"] = {
                        "coverage_rate": delta_coverage,
                        "fallback_rate": delta_fallback,
                        "insufficient_bars_rows": delta_insufficient,
                        "unmapped_rows": delta_unmapped,
                    }
                    result["checks"] = {
                        "coverage_nonregression": coverage_nonregression,
                        "fallback_nonregression": fallback_nonregression,
                        "improved": improved,
                    }

                    if coverage_nonregression and fallback_nonregression:
                        result["pass"] = True
                        result["reason"] = "nonregression_pass"
                    else:
                        result["pass"] = False
                        result["reason"] = "nonregression_failed"

with open(result_path, "w", encoding="utf-8") as fh:
    json.dump(result, fh, indent=2)
PY
}

run_recommendations_quality_nonregression_gate() {
  local quality_result_path="$OUT_DIR/recommendations_quality.result.json"
  local result_path="$OUT_DIR/recommendations_quality_nonregression.result.json"

  python3 - <<'PY' "$ROOT" "$quality_result_path" "$result_path" "$RECO_QUALITY_NONREGRESSION_ENABLED" "$RECO_QUALITY_MAX_H5_DROP" "$RECO_QUALITY_MAX_H20_DROP" "$RECO_QUALITY_MAX_H60_DROP" "$RECO_QUALITY_MAX_AVG_DROP"
import datetime
import glob
import json
import os
import sys
from typing import Any, Dict

root = sys.argv[1]
quality_result_path = sys.argv[2]
result_path = sys.argv[3]
enabled_raw = str(sys.argv[4]).strip()
max_h5_drop = float(sys.argv[5])
max_h20_drop = float(sys.argv[6])
max_h60_drop = float(sys.argv[7])
max_avg_drop = float(sys.argv[8])

enabled = enabled_raw not in {"0", "false", "False", "no", "NO", "off", "OFF"}

def utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)

def extract_quality_metrics(summary_path: str) -> Dict[str, Any]:
    payload = load_json(summary_path)
    winner = payload.get("winner")
    if not isinstance(winner, dict):
        raise RuntimeError("winner_missing")
    by_horizon = winner.get("horizon_outcome_over_index_pct")
    if not isinstance(by_horizon, dict):
        raise RuntimeError("horizon_outcome_missing")
    return {
        "h5": float(by_horizon.get("5", 0.0)),
        "h20": float(by_horizon.get("20", 0.0)),
        "h60": float(by_horizon.get("60", 0.0)),
        "avg_outcome_over_index_pct": float(winner.get("avg_outcome_over_index_pct", 0.0)),
        "quality_summary_path": summary_path,
        "generated_at_utc": str(payload.get("generated_at_utc", "")),
        "variant_name": str(winner.get("variant_name", "")),
        "source_mode": str(winner.get("source_mode", "")),
        "eval_mode": str(winner.get("eval_mode", "")),
        "min_bars": int(winner.get("min_bars", 0)),
    }

result = {
    "lane": "recommendations_quality_nonregression",
    "generated_at_utc": utc_now(),
    "enabled": bool(enabled),
    "pass": False,
    "reason": "uninitialized",
    "max_drop": {
        "h5": float(max_h5_drop),
        "h20": float(max_h20_drop),
        "h60": float(max_h60_drop),
        "avg_outcome_over_index_pct": float(max_avg_drop),
    },
    "current": None,
    "previous": None,
    "delta": None,
}

if not os.path.isfile(quality_result_path):
    result["reason"] = "recommendations_quality_result_missing"
else:
    quality_result = load_json(quality_result_path)
    if not bool(enabled):
        result["pass"] = True
        result["reason"] = "quality_nonregression_gate_disabled"
    elif not bool(quality_result.get("pass", False)):
        result["reason"] = "recommendations_quality_lane_failed"
    else:
        current_lane_dir = str(quality_result.get("lane_dir", "")).strip()
        if not current_lane_dir:
            result["reason"] = "recommendations_quality_lane_dir_missing"
        else:
            current_summary = os.path.join(current_lane_dir, "lane-summary.json")
            if not os.path.isfile(current_summary):
                result["reason"] = "current_quality_summary_missing"
            else:
                try:
                    current_metrics = extract_quality_metrics(current_summary)
                except Exception:
                    result["reason"] = "current_quality_summary_invalid"
                else:
                    result["current"] = current_metrics

                    prev_summary = ""
                    patterns = [
                        os.path.join(root, "backups", "runtime", "recommendation-quality-audit-probe-*"),
                        os.path.join(root, "backups", "runtime", "recommendation-quality-audit-lane-*"),
                    ]
                    previous_candidates = []
                    for pattern in patterns:
                        previous_candidates.extend(glob.glob(pattern))
                    for candidate in sorted(set(previous_candidates), reverse=True):
                        if os.path.abspath(candidate) == os.path.abspath(current_lane_dir):
                            continue
                        lane_summary = os.path.join(candidate, "lane-summary.json")
                        if not os.path.isfile(lane_summary):
                            continue
                        try:
                            lane_payload = load_json(lane_summary)
                        except Exception:
                            continue
                        if str(lane_payload.get("status", "")) != "pass":
                            continue
                        if not isinstance(lane_payload.get("winner"), dict):
                            continue
                        prev_summary = lane_summary
                        break

                    if not prev_summary:
                        result["pass"] = True
                        result["reason"] = "no_previous_quality_baseline"
                    else:
                        try:
                            previous_metrics = extract_quality_metrics(prev_summary)
                        except Exception:
                            result["reason"] = "previous_quality_summary_invalid"
                        else:
                            result["previous"] = previous_metrics

                            delta_h5 = float(current_metrics["h5"] - previous_metrics["h5"])
                            delta_h20 = float(current_metrics["h20"] - previous_metrics["h20"])
                            delta_h60 = float(current_metrics["h60"] - previous_metrics["h60"])
                            delta_avg = float(
                                current_metrics["avg_outcome_over_index_pct"]
                                - previous_metrics["avg_outcome_over_index_pct"]
                            )

                            h5_nonregression = bool(delta_h5 >= -max_h5_drop)
                            h20_nonregression = bool(delta_h20 >= -max_h20_drop)
                            h60_nonregression = bool(delta_h60 >= -max_h60_drop)
                            avg_nonregression = bool(delta_avg >= -max_avg_drop)
                            improved = bool(delta_h5 > 0.0 or delta_h20 > 0.0 or delta_h60 > 0.0 or delta_avg > 0.0)

                            result["delta"] = {
                                "h5": delta_h5,
                                "h20": delta_h20,
                                "h60": delta_h60,
                                "avg_outcome_over_index_pct": delta_avg,
                            }
                            result["checks"] = {
                                "h5_nonregression": h5_nonregression,
                                "h20_nonregression": h20_nonregression,
                                "h60_nonregression": h60_nonregression,
                                "avg_nonregression": avg_nonregression,
                                "improved": improved,
                            }

                            if h5_nonregression and h20_nonregression and h60_nonregression and avg_nonregression:
                                result["pass"] = True
                                result["reason"] = "nonregression_pass"
                            else:
                                result["pass"] = False
                                result["reason"] = "nonregression_failed"

with open(result_path, "w", encoding="utf-8") as fh:
    json.dump(result, fh, indent=2)
PY
}

run_lane "recommendations" "$ROOT/tools/run_recommendations_consistency_probe_lane.sh"
run_lane "screener" "$ROOT/tools/run_screener_ui_parity_probe_lane.sh"
run_lane "portfolio" "$ROOT/tools/run_portfolio_advisor_confidence_probe_lane.sh"
run_lane "recommendations_quality" "$ROOT/tools/run_recommendation_quality_audit_lane.sh"
run_recommendations_nonregression_gate
run_recommendations_quality_nonregression_gate

SUMMARY_PATH="$OUT_DIR/summary.json"
python3 - <<'PY' "$OUT_DIR" "$SUMMARY_PATH" "$RECO_NONREGRESSION_ENABLED" "$RECO_QUALITY_NONREGRESSION_ENABLED"
import datetime
import glob
import json
import os
import sys

out_dir = sys.argv[1]
summary_path = sys.argv[2]
nonregression_enabled_raw = str(sys.argv[3]).strip()
quality_nonregression_enabled_raw = str(sys.argv[4]).strip()
nonregression_enabled = nonregression_enabled_raw not in {"0", "false", "False", "no", "NO", "off", "OFF"}
quality_nonregression_enabled = quality_nonregression_enabled_raw not in {"0", "false", "False", "no", "NO", "off", "OFF"}

results = []
for path in sorted(glob.glob(os.path.join(out_dir, "*.result.json"))):
    with open(path, "r", encoding="utf-8") as fh:
        results.append(json.load(fh))

required_lanes = ["recommendations", "screener", "portfolio", "recommendations_quality"]
if nonregression_enabled:
    required_lanes.append("recommendations_nonregression")
if quality_nonregression_enabled:
    required_lanes.append("recommendations_quality_nonregression")

result_by_lane = {str(r.get("lane", "")): r for r in results}
failures = []
for lane in required_lanes:
    lane_payload = result_by_lane.get(lane)
    if lane_payload is None or not bool(lane_payload.get("pass", False)):
        failures.append(lane)

overall_pass = len(failures) == 0

summary = {
    "generated_at_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    "status": "pass" if overall_pass else "fail",
    "required_lanes": required_lanes,
    "results": results,
    "failure_lanes": failures,
    "pass": overall_pass,
}

with open(summary_path, "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)

print(summary_path)
PY

if [ -n "$OUTPUT_JSON" ]; then
  mkdir -p "$(dirname "$OUTPUT_JSON")"
  cp "$SUMMARY_PATH" "$OUTPUT_JSON"
fi

cat "$SUMMARY_PATH"
if [ "$(jq -r '.pass' "$SUMMARY_PATH")" != "true" ]; then
  exit 1
fi

exit 0
