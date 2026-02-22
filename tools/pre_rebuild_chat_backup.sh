#!/usr/bin/env bash
set -euo pipefail

TS="$(date -u +%Y%m%dT%H%M%SZ)"
SRC="/root/.codex/sessions"
DEST_E="/mnt/tfebackup/CodexHome/session-safety-${TS}"
DEST_REPO="/workspaces/Tao_Financial_Engine/backups/codex-session-safety-${TS}"

if [ ! -d "$SRC" ]; then
  echo "ERROR: source sessions folder missing: $SRC"
  exit 1
fi

mkdir -p "$DEST_E" "$DEST_REPO"
cp -a "$SRC" "$DEST_E/"
cp -a "$SRC" "$DEST_REPO/"

COUNT="$(find "$SRC" -type f -name 'rollout-*.jsonl' | wc -l | tr -d ' ')"
LATEST="$(find "$SRC" -type f -name 'rollout-*.jsonl' | sort | tail -n 1)"

echo "SAFE_TO_REBUILD=YES"
echo "BACKUP_E_DRIVE=$DEST_E"
echo "BACKUP_REPO=$DEST_REPO"
echo "SESSION_FILES=$COUNT"
echo "LATEST_SESSION_FILE=$LATEST"
