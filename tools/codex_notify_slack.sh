#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspaces/Tao_Financial_Engine"
RUNTIME_DIR="$ROOT/backups/runtime"
LOG_PATH="$RUNTIME_DIR/codex-notify.log"
SECRETS_PATH="$RUNTIME_DIR/notification-secrets.env"

mkdir -p "$RUNTIME_DIR"

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EVENT_JSON=""
if read -r -t 0.2 EVENT_JSON; then
  :
fi

WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
CHANNEL="${SLACK_CHANNEL:-}"
if [ -z "$WEBHOOK_URL" ] && [ -f "$SECRETS_PATH" ]; then
  # shellcheck disable=SC1090
  source "$SECRETS_PATH"
  WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
  CHANNEL="${SLACK_CHANNEL:-$CHANNEL}"
fi

# User requested pings in general channel.
if [ -z "$CHANNEL" ]; then
  CHANNEL="#general"
fi

if [ -z "$WEBHOOK_URL" ]; then
  printf 'codex_notify %s status=missing_slack_webhook channel=%s\n' "$TS" "$CHANNEL" >> "$LOG_PATH"
  exit 0
fi

MESSAGE="Codex task event at $TS on Tao_Financial_Engine"
if [ -n "$EVENT_JSON" ]; then
  MESSAGE="Codex event at $TS: ${EVENT_JSON}"
fi

PAYLOAD_WITH_CHANNEL="$(jq -cn --arg text "$MESSAGE" --arg channel "$CHANNEL" '{text:$text,channel:$channel}')"
RESP_WITH_CHANNEL="$(curl -sS -X POST -H 'Content-type: application/json' --data "$PAYLOAD_WITH_CHANNEL" "$WEBHOOK_URL" || true)"
if [ "$RESP_WITH_CHANNEL" = "ok" ]; then
  printf 'codex_notify %s status=slack_sent channel=%s\n' "$TS" "$CHANNEL" >> "$LOG_PATH"
  exit 0
fi

# Fallback in case webhook disallows channel override.
PAYLOAD_DEFAULT="$(jq -cn --arg text "$MESSAGE" '{text:$text}')"
RESP_DEFAULT="$(curl -sS -X POST -H 'Content-type: application/json' --data "$PAYLOAD_DEFAULT" "$WEBHOOK_URL" || true)"
if [ "$RESP_DEFAULT" = "ok" ]; then
  printf 'codex_notify %s status=slack_sent_default_channel channel=%s override_response=%s\n' "$TS" "$CHANNEL" "$RESP_WITH_CHANNEL" >> "$LOG_PATH"
  exit 0
fi

printf 'codex_notify %s status=slack_failed channel=%s override_response=%s default_response=%s\n' "$TS" "$CHANNEL" "${RESP_WITH_CHANNEL:-empty}" "${RESP_DEFAULT:-empty}" >> "$LOG_PATH"
exit 0
