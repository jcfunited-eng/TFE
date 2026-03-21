#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${AWS_ACCESS_KEY_ID:-}" || -z "${AWS_SECRET_ACCESS_KEY:-}" || -z "${AWS_SESSION_TOKEN:-}" ]]; then
  echo "Source /root/.codex/prod-verification/load-readonly-env.sh first." >&2
  return 1 2>/dev/null || exit 1
fi

export TFE_INTERNAL_REFRESH_TOKEN="$(aws secretsmanager get-secret-value --secret-id 'arn:aws:secretsmanager:us-east-1:418384447921:secret:tfe/internal-refresh-token/prod-lXRWCk' --region us-east-1 --query SecretString --output text)"

echo "Loaded approval-only refresh token into the shell. Use only with explicit approval." >&2
