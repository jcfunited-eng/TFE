#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  tools/sync_to_aws.sh --remote-host <host> --remote-user <user> [options]

Required:
  --remote-host <host>         EC2 host or SSH alias
  --remote-user <user>         Remote Linux user

Options:
  --remote-root <path>         Remote TFE root (default: /data/tfe)
  --repo-root <path>           Local repo root (default: current repo)
  --inputs-root <path>         Local current_inputs root
  --include-temporal-dataset   Copy temporal_policy_dataset_latest.csv
  --dry-run                    Show rsync actions without writing
  --help                       Show this help
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INPUTS_ROOT_DEFAULT="$REPO_ROOT/backups/lab/recommendation_lab/current_inputs"

REMOTE_HOST=""
REMOTE_USER=""
REMOTE_ROOT="/data/tfe"
INPUTS_ROOT="$INPUTS_ROOT_DEFAULT"
INCLUDE_TEMPORAL_DATASET=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote-host)
      REMOTE_HOST="${2:-}"
      shift 2
      ;;
    --remote-user)
      REMOTE_USER="${2:-}"
      shift 2
      ;;
    --remote-root)
      REMOTE_ROOT="${2:-}"
      shift 2
      ;;
    --repo-root)
      REPO_ROOT="$(cd "${2:-}" && pwd)"
      shift 2
      ;;
    --inputs-root)
      INPUTS_ROOT="${2:-}"
      shift 2
      ;;
    --include-temporal-dataset)
      INCLUDE_TEMPORAL_DATASET=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
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

if [[ -z "$REMOTE_HOST" || -z "$REMOTE_USER" ]]; then
  echo "missing_required_remote_args" >&2
  usage
  exit 2
fi

if [[ ! -d "$REPO_ROOT" ]]; then
  echo "repo_root_not_found:$REPO_ROOT" >&2
  exit 2
fi
if [[ ! -d "$INPUTS_ROOT" ]]; then
  echo "inputs_root_not_found:$INPUTS_ROOT" >&2
  exit 2
fi

REMOTE_TARGET="${REMOTE_USER}@${REMOTE_HOST}"
RSYNC_BASE=(rsync -az --partial --inplace --human-readable --info=stats2,progress2)
if [[ "$DRY_RUN" -eq 1 ]]; then
  RSYNC_BASE+=(--dry-run)
fi

ssh "$REMOTE_TARGET" "mkdir -p '$REMOTE_ROOT/repo' '$REMOTE_ROOT/data/current_inputs' '$REMOTE_ROOT/logs' '$REMOTE_ROOT/runs'"

# Sync source code repo only (large data dirs excluded).
"${RSYNC_BASE[@]}" \
  --delete \
  --exclude ".git/" \
  --exclude "backups/***" \
  --exclude "data/***" \
  --exclude "market_data/***" \
  --exclude "__pycache__/" \
  --exclude ".dev_pydeps*/" \
  --exclude "web/.next/***" \
  --exclude "web/node_modules/***" \
  --exclude "*.log" \
  "$REPO_ROOT/" "$REMOTE_TARGET:$REMOTE_ROOT/repo/"

# Sync all latest JSON manifests from current_inputs.
"${RSYNC_BASE[@]}" \
  --include "*/" \
  --include "*_latest.json" \
  --exclude "*" \
  "$INPUTS_ROOT/" "$REMOTE_TARGET:$REMOTE_ROOT/data/current_inputs/"

# Sync fresh row-trace and conflicts (if present).
for file_name in \
  "fresh_temporal_rowtrace_latest.csv" \
  "fresh_temporal_rowtrace_conflicts_latest.csv"; do
  local_path="$INPUTS_ROOT/$file_name"
  if [[ -f "$local_path" ]]; then
    "${RSYNC_BASE[@]}" "$local_path" "$REMOTE_TARGET:$REMOTE_ROOT/data/current_inputs/$file_name"
  fi
done

if [[ "$INCLUDE_TEMPORAL_DATASET" -eq 1 ]]; then
  dataset_path="$INPUTS_ROOT/temporal_policy_dataset_latest.csv"
  if [[ ! -f "$dataset_path" ]]; then
    echo "temporal_dataset_not_found:$dataset_path" >&2
    exit 2
  fi
  "${RSYNC_BASE[@]}" "$dataset_path" "$REMOTE_TARGET:$REMOTE_ROOT/data/current_inputs/temporal_policy_dataset_latest.csv"
fi

echo "sync_to_aws_complete"
