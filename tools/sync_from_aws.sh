#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  tools/sync_from_aws.sh --remote-host <host> --remote-user <user> [options]

Required:
  --remote-host <host>         EC2 host or SSH alias
  --remote-user <user>         Remote Linux user

Options:
  --remote-root <path>         Remote TFE root (default: /data/tfe)
  --repo-root <path>           Local repo root (default: current repo)
  --run-id <timestamp>         Pull one run directory from /runs/<run-id>
  --all-runs                   Pull all run directories
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

REMOTE_HOST=""
REMOTE_USER=""
REMOTE_ROOT="/data/tfe"
RUN_ID=""
ALL_RUNS=0
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
    --run-id)
      RUN_ID="${2:-}"
      shift 2
      ;;
    --all-runs)
      ALL_RUNS=1
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

REMOTE_TARGET="${REMOTE_USER}@${REMOTE_HOST}"
LOCAL_AWS_SYNC_ROOT="$REPO_ROOT/backups/lab/recommendation_lab/aws_sync"
LOCAL_CURRENT_INPUTS="$REPO_ROOT/backups/lab/recommendation_lab/current_inputs"
mkdir -p "$LOCAL_AWS_SYNC_ROOT/logs" "$LOCAL_AWS_SYNC_ROOT/runs" "$LOCAL_CURRENT_INPUTS"

RSYNC_BASE=(rsync -az --partial --inplace --human-readable --info=stats2,progress2)
if [[ "$DRY_RUN" -eq 1 ]]; then
  RSYNC_BASE+=(--dry-run)
fi

# Pull latest manifests/reports from remote current_inputs.
"${RSYNC_BASE[@]}" \
  --include "*/" \
  --include "*_latest.json" \
  --exclude "*" \
  "$REMOTE_TARGET:$REMOTE_ROOT/data/current_inputs/" "$LOCAL_CURRENT_INPUTS/"

# Pull full logs directory.
"${RSYNC_BASE[@]}" "$REMOTE_TARGET:$REMOTE_ROOT/logs/" "$LOCAL_AWS_SYNC_ROOT/logs/"

if [[ "$ALL_RUNS" -eq 1 ]]; then
  "${RSYNC_BASE[@]}" "$REMOTE_TARGET:$REMOTE_ROOT/runs/" "$LOCAL_AWS_SYNC_ROOT/runs/"
elif [[ -n "$RUN_ID" ]]; then
  "${RSYNC_BASE[@]}" "$REMOTE_TARGET:$REMOTE_ROOT/runs/$RUN_ID/" "$LOCAL_AWS_SYNC_ROOT/runs/$RUN_ID/"
fi

echo "sync_from_aws_complete"
