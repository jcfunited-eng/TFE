#!/usr/bin/env bash
set -euo pipefail

STATUS_FILE="/workspaces/Tao_Financial_Engine/backups/deploy-gate-status-$(date -u +%Y%m%dT%H%M%SZ).txt"

{
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "aws_bin=$(command -v aws || echo missing)"
  echo "jq_bin=$(command -v jq || echo missing)"
  echo "zip_bin=$(command -v zip || echo missing)"

  if [ -r /root/.aws/credentials ] || [ -r /root/.aws/config ]; then
    echo "aws_mount_status=present"
  else
    echo "aws_mount_status=missing"
  fi

  if aws sts get-caller-identity --output json >/tmp/tfe_sts_identity.json 2>/tmp/tfe_sts_error.log; then
    echo "sts_status=ok"
    echo "sts_identity_file=/tmp/tfe_sts_identity.json"
  else
    echo "sts_status=fail"
    echo "sts_error=$(tr '\n' ' ' </tmp/tfe_sts_error.log)"
  fi

  if aws codebuild batch-get-projects --names tfe-web-image-build --region us-east-1 --output json >/tmp/tfe_codebuild_access.json 2>/tmp/tfe_codebuild_error.log; then
    echo "codebuild_access=ok"
    echo "codebuild_access_file=/tmp/tfe_codebuild_access.json"
  else
    echo "codebuild_access=fail"
    echo "codebuild_error=$(tr '\n' ' ' </tmp/tfe_codebuild_error.log)"
  fi

  if aws ecs describe-services --cluster tfe-web-cluster --services tfe-web-service-lb --region us-east-1 --output json >/tmp/tfe_ecs_access.json 2>/tmp/tfe_ecs_error.log; then
    echo "ecs_access=ok"
    echo "ecs_access_file=/tmp/tfe_ecs_access.json"
  else
    echo "ecs_access=fail"
    echo "ecs_error=$(tr '\n' ' ' </tmp/tfe_ecs_error.log)"
  fi
} | tee "$STATUS_FILE"

echo "status_file=$STATUS_FILE"
