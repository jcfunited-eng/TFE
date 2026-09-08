#!/bin/bash
# db_rotation_guard.sh — restarts the production website when the database
# password rotates (Joe's word, 2026-09-08).
#
# The RDS-managed secret changes the master password every 30 days. The web
# containers read it only at launch, so every rotation used to break the
# site until a hand restart ("password authentication failed for tfe_admin",
# 2026-09-08). This guard compares the secret's last-changed time with the
# running task's start time every two hours; when the secret is newer it
# forces a new deployment (same code, same task definition — only fresh
# credentials) and logs the action. It never touches code, flags, or books.
cd "$(dirname "$0")/.." || exit 1
REGION=us-east-1
CLUSTER=tfe-web-cluster
SERVICE=tfe-web-service-lb
SECRET='rds!db-b61f1947-d0fd-41cb-b36d-aa39cd64735a'
LOG=artifacts/vtvr_observer/db_rotation_guard.log

check_once() {
  changed=$(aws secretsmanager describe-secret --secret-id "$SECRET" \
    --region $REGION --query LastChangedDate --output text 2>/dev/null)
  task=$(aws ecs list-tasks --cluster $CLUSTER --service-name $SERVICE \
    --region $REGION --query 'taskArns[0]' --output text 2>/dev/null)
  started=$(aws ecs describe-tasks --cluster $CLUSTER --tasks "$task" \
    --region $REGION --query 'tasks[0].startedAt' --output text 2>/dev/null)
  if [ -z "$changed" ] || [ -z "$started" ] || [ "$task" = "None" ]; then
    echo "[db-guard] $(date -u +%FT%TZ) cannot read state (changed='$changed' started='$started') — no action" >> "$LOG"
    return 0
  fi
  ch_s=$(date -d "$changed" +%s 2>/dev/null)
  st_s=$(date -d "$started" +%s 2>/dev/null)
  if [ -z "$ch_s" ] || [ -z "$st_s" ]; then
    echo "[db-guard] $(date -u +%FT%TZ) date parse failed — no action" >> "$LOG"
    return 0
  fi
  if [ "$ch_s" -gt "$st_s" ]; then
    echo "[db-guard] $(date -u +%FT%TZ) secret changed $changed > task started $started — restarting service" >> "$LOG"
    aws ecs update-service --cluster $CLUSTER --service $SERVICE \
      --force-new-deployment --region $REGION >/dev/null 2>&1 \
      && echo "[db-guard] $(date -u +%FT%TZ) restart requested" >> "$LOG" \
      || echo "[db-guard] $(date -u +%FT%TZ) RESTART REQUEST FAILED" >> "$LOG"
  else
    echo "[db-guard] $(date -u +%FT%TZ) ok (secret $changed <= task $started)" >> "$LOG"
  fi
}

if [ "$1" = "once" ]; then
  check_once
  tail -1 "$LOG"
  exit 0
fi

echo "[db-guard] started $(date -u +%FT%TZ) pid $$" >> "$LOG"
while true; do
  check_once
  sleep 7200
done
