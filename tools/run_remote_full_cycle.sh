#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  tools/run_remote_full_cycle.sh [options]

Options:
  --repo-root <path>           Repo root (default: /data/tfe/repo)
  --data-root <path>           Data root (default: /data/tfe/data)
  --runs-root <path>           Runs root (default: /data/tfe/runs)
  --run-id <timestamp>         Reuse a run id (for resume)
  --horizons <csv>             Horizons list (default: 5,20,60)
  --approval-note <text>       Approval note for generation stage
  --force-rowtrace             Force regenerate fresh row-trace
  --force-temporal-dataset     Force rebuild temporal dataset
  --help                       Show this help
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

REPO_ROOT="/data/tfe/repo"
DATA_ROOT="/data/tfe/data"
RUNS_ROOT="/data/tfe/runs"
RUN_ID=""
HORIZONS="5,20,60"
APPROVAL_NOTE="aws_remote_full_cycle"
FORCE_ROWTRACE=0
FORCE_TEMPORAL_DATASET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      REPO_ROOT="${2:-}"
      shift 2
      ;;
    --data-root)
      DATA_ROOT="${2:-}"
      shift 2
      ;;
    --runs-root)
      RUNS_ROOT="${2:-}"
      shift 2
      ;;
    --run-id)
      RUN_ID="${2:-}"
      shift 2
      ;;
    --horizons)
      HORIZONS="${2:-}"
      shift 2
      ;;
    --approval-note)
      APPROVAL_NOTE="${2:-}"
      shift 2
      ;;
    --force-rowtrace)
      FORCE_ROWTRACE=1
      shift
      ;;
    --force-temporal-dataset)
      FORCE_TEMPORAL_DATASET=1
      shift
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "unsupported_arg:$1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$RUN_ID" ]]; then
  RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
fi

if [[ ! -d "$REPO_ROOT" ]]; then
  echo "repo_root_not_found:$REPO_ROOT" >&2
  exit 2
fi

CURRENT_INPUTS="$DATA_ROOT/current_inputs"
RUN_DIR="$RUNS_ROOT/$RUN_ID"
STAGES_DIR="$RUN_DIR/stages"
CHECKPOINT_ROOT="$RUN_DIR/checkpoints"
mkdir -p "$CURRENT_INPUTS" "$RUN_DIR" "$STAGES_DIR" "$CHECKPOINT_ROOT"

export TMPDIR="$DATA_ROOT/tmp"
mkdir -p "$TMPDIR"

FRESH_ROWTRACE_CSV="$CURRENT_INPUTS/fresh_temporal_rowtrace_latest.csv"
FRESH_ROWTRACE_MANIFEST="$CURRENT_INPUTS/fresh_temporal_rowtrace_manifest_latest.json"
FRESH_ROWTRACE_CONFLICTS="$CURRENT_INPUTS/fresh_temporal_rowtrace_conflicts_latest.csv"

TEMPORAL_DATASET_CSV="$CURRENT_INPUTS/temporal_policy_dataset_latest.csv"
TEMPORAL_DATASET_MANIFEST="$CURRENT_INPUTS/temporal_policy_dataset_manifest_latest.json"
TEMPORAL_DATASET_HASH_MANIFEST="$CURRENT_INPUTS/temporal_policy_dataset_hash_manifest_latest.json"

AUDIT_REPORT_LATEST="$CURRENT_INPUTS/temporal_dataset_audit_latest.json"

EVAL_H5_REPORT="$CURRENT_INPUTS/temporal_walkforward_eval_h5_latest.json"
EVAL_H20_REPORT="$CURRENT_INPUTS/temporal_walkforward_eval_h20_latest.json"
EVAL_H60_REPORT="$CURRENT_INPUTS/temporal_walkforward_eval_h60_latest.json"
MERGED_EVAL_REPORT_LATEST="$CURRENT_INPUTS/temporal_walkforward_eval_latest.json"

STAGE_LOSS_REPORT_LATEST="$CURRENT_INPUTS/temporal_stage_loss_latest.json"
AWS_RUN_MANIFEST_LATEST="$CURRENT_INPUTS/aws_run_manifest_latest.json"

RUN_START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "$RUN_START_ISO" > "$RUN_DIR/STARTED"

json_get() {
  local file="$1"
  shift
  python3 - "$file" "$@" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
keys = sys.argv[2:]
if not path.exists():
    print("")
    raise SystemExit(0)
obj = json.loads(path.read_text(encoding="utf-8"))
for key in keys:
    if isinstance(obj, dict) and key in obj:
        obj = obj[key]
    else:
        print("")
        raise SystemExit(0)
if obj is None:
    print("")
elif isinstance(obj, (dict, list)):
    print(json.dumps(obj, sort_keys=True))
else:
    print(obj)
PY
}

sha256_file() {
  local p="$1"
  if [[ ! -f "$p" ]]; then
    echo ""
    return 0
  fi
  sha256sum "$p" | awk '{print $1}'
}

write_stage_manifest() {
  local stage_dir="$1"
  local stage_name="$2"
  local status="$3"
  local reason="$4"
  local started_at="$5"
  local ended_at="$6"
  local return_code="$7"
  local command_json="$8"

  STAGE_DIR="$stage_dir" \
  STAGE_NAME="$stage_name" \
  STAGE_STATUS="$status" \
  STAGE_REASON="$reason" \
  STAGE_STARTED="$started_at" \
  STAGE_ENDED="$ended_at" \
  STAGE_RC="$return_code" \
  STAGE_CMD_JSON="$command_json" \
  python3 - <<'PY'
import json
import os
from pathlib import Path

stage_dir = Path(os.environ["STAGE_DIR"])
payload = {
    "stage_name": os.environ["STAGE_NAME"],
    "status": os.environ["STAGE_STATUS"],
    "reason": os.environ["STAGE_REASON"] or None,
    "started_at_utc": os.environ["STAGE_STARTED"],
    "ended_at_utc": os.environ["STAGE_ENDED"],
    "return_code": int(os.environ["STAGE_RC"]),
    "stdout_log": str(stage_dir / "stdout.log"),
    "stderr_log": str(stage_dir / "stderr.log"),
    "return_code_file": str(stage_dir / "return_code.txt"),
    "command": json.loads(os.environ["STAGE_CMD_JSON"]),
}
(stage_dir / "stage_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
}

stage_is_complete() {
  local stage_dir="$1"
  if [[ -f "$stage_dir/return_code.txt" && -f "$stage_dir/ENDED" ]]; then
    local rc
    rc="$(cat "$stage_dir/return_code.txt" 2>/dev/null || true)"
    if [[ "$rc" == "0" ]]; then
      return 0
    fi
  fi
  return 1
}

run_stage() {
  local stage_name="$1"
  local description="$2"
  shift 2
  local cmd=("$@")

  local stage_dir="$STAGES_DIR/$stage_name"
  mkdir -p "$stage_dir"

  if stage_is_complete "$stage_dir"; then
    echo "stage_already_complete:$stage_name"
    return 0
  fi

  local started_at
  local ended_at
  local rc
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "$started_at" > "$stage_dir/STARTED"

  printf '%q ' "${cmd[@]}" > "$stage_dir/command.sh"
  printf '\n' >> "$stage_dir/command.sh"

  set +e
  "${cmd[@]}" > "$stage_dir/stdout.log" 2> "$stage_dir/stderr.log"
  rc=$?
  set -e

  ended_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "$ended_at" > "$stage_dir/ENDED"
  echo "$rc" > "$stage_dir/return_code.txt"

  local cmd_json
  cmd_json="$(python3 - "${cmd[@]}" <<'PY'
import json
import sys
print(json.dumps(sys.argv[1:]))
PY
)"

  local status="completed"
  local reason=""
  if [[ "$rc" -ne 0 ]]; then
    status="failed"
    reason="$description"
  fi

  write_stage_manifest "$stage_dir" "$stage_name" "$status" "$reason" "$started_at" "$ended_at" "$rc" "$cmd_json"

  if [[ "$rc" -ne 0 ]]; then
    echo "stage_failed:$stage_name" >&2
    return "$rc"
  fi
  return 0
}

mark_stage_skipped() {
  local stage_name="$1"
  local reason="$2"
  local stage_dir="$STAGES_DIR/$stage_name"
  mkdir -p "$stage_dir"

  if stage_is_complete "$stage_dir"; then
    return 0
  fi

  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "$ts" > "$stage_dir/STARTED"
  echo "$ts" > "$stage_dir/ENDED"
  echo "0" > "$stage_dir/return_code.txt"
  : > "$stage_dir/stdout.log"
  : > "$stage_dir/stderr.log"

  local cmd_json='[]'
  write_stage_manifest "$stage_dir" "$stage_name" "skipped" "$reason" "$ts" "$ts" "0" "$cmd_json"
}

rowtrace_hash_manifest_ok() {
  if [[ ! -f "$FRESH_ROWTRACE_CSV" || ! -f "$FRESH_ROWTRACE_MANIFEST" ]]; then
    return 1
  fi
  local expected actual
  expected="$(json_get "$FRESH_ROWTRACE_MANIFEST" outputs fresh_temporal_rowtrace_csv_sha256)"
  if [[ -z "$expected" ]]; then
    return 1
  fi
  actual="$(sha256_file "$FRESH_ROWTRACE_CSV")"
  [[ "$expected" == "$actual" ]]
}

write_temporal_dataset_hash_manifest() {
  local rowtrace_sha
  local dataset_sha
  rowtrace_sha="$(sha256_file "$FRESH_ROWTRACE_CSV")"
  dataset_sha="$(sha256_file "$TEMPORAL_DATASET_CSV")"

  ROWTRACE_SHA="$rowtrace_sha" \
  DATASET_SHA="$dataset_sha" \
  ROWTRACE_PATH="$FRESH_ROWTRACE_CSV" \
  DATASET_PATH="$TEMPORAL_DATASET_CSV" \
  TEMPORAL_MANIFEST_PATH="$TEMPORAL_DATASET_MANIFEST" \
  HASH_MANIFEST_PATH="$TEMPORAL_DATASET_HASH_MANIFEST" \
  python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

payload = {
    "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "analysis": "temporal_policy_dataset_hash_manifest",
    "inputs": {
        "rowtrace_csv": os.environ["ROWTRACE_PATH"],
        "rowtrace_sha256": os.environ["ROWTRACE_SHA"],
        "temporal_manifest_path": os.environ["TEMPORAL_MANIFEST_PATH"],
    },
    "outputs": {
        "temporal_dataset_csv": os.environ["DATASET_PATH"],
        "temporal_dataset_sha256": os.environ["DATASET_SHA"],
        "temporal_dataset_size_bytes": int(Path(os.environ["DATASET_PATH"]).stat().st_size),
    },
}
path = Path(os.environ["HASH_MANIFEST_PATH"])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY
}

temporal_dataset_hash_manifest_ok() {
  if [[ ! -f "$TEMPORAL_DATASET_CSV" || ! -f "$TEMPORAL_DATASET_MANIFEST" || ! -f "$TEMPORAL_DATASET_HASH_MANIFEST" ]]; then
    return 1
  fi

  local hash_rowtrace expected_rowtrace
  local expected_dataset actual_dataset

  hash_rowtrace="$(json_get "$TEMPORAL_DATASET_HASH_MANIFEST" inputs rowtrace_sha256)"
  expected_rowtrace="$(sha256_file "$FRESH_ROWTRACE_CSV")"
  if [[ -z "$hash_rowtrace" || "$hash_rowtrace" != "$expected_rowtrace" ]]; then
    return 1
  fi

  expected_dataset="$(json_get "$TEMPORAL_DATASET_HASH_MANIFEST" outputs temporal_dataset_sha256)"
  actual_dataset="$(sha256_file "$TEMPORAL_DATASET_CSV")"
  if [[ -z "$expected_dataset" || "$expected_dataset" != "$actual_dataset" ]]; then
    return 1
  fi

  return 0
}

# Stage 1: fresh row-trace generation only if needed.
if [[ "$FORCE_ROWTRACE" -eq 1 ]]; then
  echo "forcing_stage_01_rowtrace"
  run_stage "01_rowtrace" "fresh_rowtrace_generation" \
    python3 "$REPO_ROOT/tools/regenerate_fresh_temporal_rowtrace_from_raw.py" \
      --execute \
      --approval-note "$APPROVAL_NOTE" \
      --out-csv "$FRESH_ROWTRACE_CSV" \
      --out-manifest "$FRESH_ROWTRACE_MANIFEST" \
      --report-out "$STAGES_DIR/01_rowtrace/fresh_temporal_rowtrace_manifest.json"
else
  if rowtrace_hash_manifest_ok; then
    mark_stage_skipped "01_rowtrace" "existing_rowtrace_matches_manifest_hash"
  else
    run_stage "01_rowtrace" "fresh_rowtrace_generation" \
      python3 "$REPO_ROOT/tools/regenerate_fresh_temporal_rowtrace_from_raw.py" \
        --execute \
        --approval-note "$APPROVAL_NOTE" \
        --out-csv "$FRESH_ROWTRACE_CSV" \
        --out-manifest "$FRESH_ROWTRACE_MANIFEST" \
        --report-out "$STAGES_DIR/01_rowtrace/fresh_temporal_rowtrace_manifest.json"
  fi
fi

if [[ ! -f "$FRESH_ROWTRACE_CSV" || ! -f "$FRESH_ROWTRACE_MANIFEST" ]]; then
  echo "rowtrace_outputs_missing_after_stage_01" >&2
  exit 2
fi

# Stage 2: temporal dataset build.
if [[ "$FORCE_TEMPORAL_DATASET" -eq 1 ]]; then
  echo "forcing_stage_02_temporal_dataset"
  run_stage "02_temporal_dataset" "temporal_dataset_build" \
    python3 "$REPO_ROOT/tools/build_temporal_policy_dataset.py" \
      --row-trace "$FRESH_ROWTRACE_CSV" \
      --out-csv "$TEMPORAL_DATASET_CSV" \
      --out-manifest "$TEMPORAL_DATASET_MANIFEST" \
      --report-out "$STAGES_DIR/02_temporal_dataset/temporal_policy_dataset_manifest.json"
  write_temporal_dataset_hash_manifest
else
  if temporal_dataset_hash_manifest_ok; then
    mark_stage_skipped "02_temporal_dataset" "existing_temporal_dataset_matches_manifest_hashes"
  else
    run_stage "02_temporal_dataset" "temporal_dataset_build" \
      python3 "$REPO_ROOT/tools/build_temporal_policy_dataset.py" \
        --row-trace "$FRESH_ROWTRACE_CSV" \
        --out-csv "$TEMPORAL_DATASET_CSV" \
        --out-manifest "$TEMPORAL_DATASET_MANIFEST" \
        --report-out "$STAGES_DIR/02_temporal_dataset/temporal_policy_dataset_manifest.json"
    write_temporal_dataset_hash_manifest
  fi
fi

if [[ ! -f "$TEMPORAL_DATASET_CSV" || ! -f "$TEMPORAL_DATASET_MANIFEST" ]]; then
  echo "temporal_dataset_outputs_missing_after_stage_02" >&2
  exit 2
fi

# Stage 3: audit.
run_stage "03_audit" "temporal_dataset_audit" \
  python3 "$REPO_ROOT/tools/audit_temporal_dataset.py" \
    --row-trace "$FRESH_ROWTRACE_CSV" \
    --conflicts-csv "$FRESH_ROWTRACE_CONFLICTS" \
    --report-latest "$AUDIT_REPORT_LATEST" \
    --report-out "$STAGES_DIR/03_audit/temporal_dataset_audit.json"

# Stage 4: eval h5.
run_stage "04_eval_h5" "temporal_walkforward_eval_h5" \
  python3 "$REPO_ROOT/tools/eval_temporal_walkforward.py" \
    --temporal-dataset "$TEMPORAL_DATASET_CSV" \
    --horizons 5 \
    --checkpoint-dir "$CHECKPOINT_ROOT/h5" \
    --resume-from-checkpoint \
    --report-latest "$EVAL_H5_REPORT" \
    --report-out "$EVAL_H5_REPORT"

# Stage 5: eval h20.
run_stage "05_eval_h20" "temporal_walkforward_eval_h20" \
  python3 "$REPO_ROOT/tools/eval_temporal_walkforward.py" \
    --temporal-dataset "$TEMPORAL_DATASET_CSV" \
    --horizons 20 \
    --checkpoint-dir "$CHECKPOINT_ROOT/h20" \
    --resume-from-checkpoint \
    --report-latest "$EVAL_H20_REPORT" \
    --report-out "$EVAL_H20_REPORT"

# Stage 6: eval h60.
run_stage "06_eval_h60" "temporal_walkforward_eval_h60" \
  python3 "$REPO_ROOT/tools/eval_temporal_walkforward.py" \
    --temporal-dataset "$TEMPORAL_DATASET_CSV" \
    --horizons 60 \
    --checkpoint-dir "$CHECKPOINT_ROOT/h60" \
    --resume-from-checkpoint \
    --report-latest "$EVAL_H60_REPORT" \
    --report-out "$EVAL_H60_REPORT"

# Stage 7: merge horizon reports.
run_stage "07_merge_horizons" "merge_horizon_reports" \
  python3 "$REPO_ROOT/tools/merge_temporal_walkforward_horizons.py" \
    --h5-report "$EVAL_H5_REPORT" \
    --h20-report "$EVAL_H20_REPORT" \
    --h60-report "$EVAL_H60_REPORT" \
    --horizons "$HORIZONS" \
    --report-latest "$MERGED_EVAL_REPORT_LATEST" \
    --report-out "$RUN_DIR/temporal_walkforward_eval_merged_${RUN_ID}.json"

# Stage 8: stage-loss accounting.
run_stage "08_stage_loss" "temporal_stage_loss_accounting" \
  python3 "$REPO_ROOT/tools/temporal_stage_loss_accounting.py" \
    --rowtrace-csv "$FRESH_ROWTRACE_CSV" \
    --rowtrace-manifest "$FRESH_ROWTRACE_MANIFEST" \
    --temporal-dataset-csv "$TEMPORAL_DATASET_CSV" \
    --temporal-manifest "$TEMPORAL_DATASET_MANIFEST" \
    --audit-report "$AUDIT_REPORT_LATEST" \
    --eval-report "$MERGED_EVAL_REPORT_LATEST" \
    --horizons "$HORIZONS" \
    --report-latest "$STAGE_LOSS_REPORT_LATEST" \
    --report-out "$RUN_DIR/temporal_stage_loss_${RUN_ID}.json"

# Stage 9: AWS run manifest.
run_stage "09_aws_run_manifest" "aws_run_manifest" \
  python3 "$REPO_ROOT/tools/build_aws_run_manifest.py" \
    --repo-root "$REPO_ROOT" \
    --data-mount "$(dirname "$DATA_ROOT")" \
    --run-root "$RUN_DIR" \
    --run-timestamp "$RUN_ID" \
    --horizons "$HORIZONS" \
    --rowtrace-manifest "$FRESH_ROWTRACE_MANIFEST" \
    --temporal-manifest "$TEMPORAL_DATASET_MANIFEST" \
    --audit-report "$AUDIT_REPORT_LATEST" \
    --eval-report "$MERGED_EVAL_REPORT_LATEST" \
    --stage-loss-report "$STAGE_LOSS_REPORT_LATEST" \
    --bootstrap-manifest "$(dirname "$DATA_ROOT")/logs/bootstrap_manifest_latest.json" \
    --report-latest "$AWS_RUN_MANIFEST_LATEST" \
    --report-out "$RUN_DIR/aws_run_manifest_${RUN_ID}.json"

RUN_END_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "$RUN_END_ISO" > "$RUN_DIR/ENDED"

RUN_DIR="$RUN_DIR" RUN_ID="$RUN_ID" RUN_START_ISO="$RUN_START_ISO" RUN_END_ISO="$RUN_END_ISO" \
python3 - <<'PY'
import json
import os
from pathlib import Path

run_dir = Path(os.environ["RUN_DIR"])
stages_dir = run_dir / "stages"
summary = {
    "run_id": os.environ["RUN_ID"],
    "started_at_utc": os.environ["RUN_START_ISO"],
    "ended_at_utc": os.environ["RUN_END_ISO"],
    "stages": {},
}
for stage_path in sorted(stages_dir.glob("*/stage_manifest.json")):
    payload = json.loads(stage_path.read_text(encoding="utf-8"))
    summary["stages"][payload.get("stage_name", stage_path.parent.name)] = {
        "status": payload.get("status"),
        "return_code": payload.get("return_code"),
        "reason": payload.get("reason"),
    }
(run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
PY

echo "$RUN_DIR"
echo "$RUN_DIR/run_summary.json"
