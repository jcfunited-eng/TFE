#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_CREDS_FILE="/root/.codex/prod-verification/access-key.json"
ROLE_ARN="arn:aws:iam::418384447921:role/CodexProdVerificationReadOnlyRole"
SESSION_NAME="codex-prod-readonly"

if [[ ! -f "$BOOTSTRAP_CREDS_FILE" ]]; then
  echo "Missing bootstrap access key file: $BOOTSTRAP_CREDS_FILE" >&2
  return 1 2>/dev/null || exit 1
fi

export BOOTSTRAP_JSON="$(cat "$BOOTSTRAP_CREDS_FILE")"
export AWS_ACCESS_KEY_ID="$(python3 -c 'import json,os; print(json.loads(os.environ["BOOTSTRAP_JSON"])["AccessKey"]["AccessKeyId"])')"
export AWS_SECRET_ACCESS_KEY="$(python3 -c 'import json,os; print(json.loads(os.environ["BOOTSTRAP_JSON"])["AccessKey"]["SecretAccessKey"])')"
unset AWS_SESSION_TOKEN
export AWS_DEFAULT_REGION="us-east-1"
export AWS_REGION="us-east-1"

export ASSUME_JSON="$(aws sts assume-role --role-arn "$ROLE_ARN" --role-session-name "$SESSION_NAME" --region us-east-1)"
export AWS_ACCESS_KEY_ID="$(python3 -c 'import json,os; print(json.loads(os.environ["ASSUME_JSON"])["Credentials"]["AccessKeyId"])')"
export AWS_SECRET_ACCESS_KEY="$(python3 -c 'import json,os; print(json.loads(os.environ["ASSUME_JSON"])["Credentials"]["SecretAccessKey"])')"
export AWS_SESSION_TOKEN="$(python3 -c 'import json,os; print(json.loads(os.environ["ASSUME_JSON"])["Credentials"]["SessionToken"])')"

export PROD_CLUSTER="tfe-web-cluster"
export PROD_SERVICE="tfe-web-service-lb"
export PROD_TASKDEF_ARN="$(aws ecs describe-services --cluster "$PROD_CLUSTER" --services "$PROD_SERVICE" --region us-east-1 --query 'services[0].taskDefinition' --output text)"
export PROD_TASK_ARN="$(aws ecs list-tasks --cluster "$PROD_CLUSTER" --service-name "$PROD_SERVICE" --desired-status RUNNING --region us-east-1 --query 'taskArns[0]' --output text)"
export PROD_TASK_ID="${PROD_TASK_ARN##*/}"
export PROD_IMAGE_URI="$(aws ecs describe-task-definition --task-definition "$PROD_TASKDEF_ARN" --region us-east-1 --query 'taskDefinition.containerDefinitions[0].image' --output text)"
export PROD_IMAGE_TAG="${PROD_IMAGE_URI##*:}"
export PROD_IMAGE_DIGEST="$(aws ecr describe-images --repository-name tfe-web --image-ids imageTag="$PROD_IMAGE_TAG" --region us-east-1 --query 'imageDetails[0].imageDigest' --output text)"
export PROD_SOURCE_DEPLOY_PATH_S3="s3://tfe-codebuild-src-418384447921-us-east-1/deploy/tfe_codebuild_src.zip"
export PROD_SOURCE_ARCHIVE_S3="s3://tfe-codebuild-src-418384447921-us-east-1/deploy/archive/tfe_codebuild_src-${PROD_IMAGE_TAG#manual-}.zip"
aws s3api head-object --bucket tfe-codebuild-src-418384447921-us-east-1 --key "deploy/archive/tfe_codebuild_src-${PROD_IMAGE_TAG#manual-}.zip" --region us-east-1 >/dev/null
export PROD_LOCAL_REPO="/workspaces/Tao_Financial_Engine"
export PROD_TASKDEF_JSON="$(aws ecs describe-task-definition --task-definition "$PROD_TASKDEF_ARN" --region us-east-1 --output json)"
export TFE_RUNTIME_DB_SECRET_ARN="$(python3 -c 'import json,os; data=json.loads(os.environ["PROD_TASKDEF_JSON"]); container=((data.get("taskDefinition") or {}).get("containerDefinitions") or [{}])[0]; env_map={item.get("name"): item.get("value") for item in (container.get("environment") or []) if item.get("name")}; secret_map={item.get("name"): item.get("valueFrom") for item in (container.get("secrets") or []) if item.get("name")}; value=str(env_map.get("TFE_RUNTIME_DB_SECRET_ARN") or secret_map.get("PGPASSWORD") or "").strip(); suffixes=(":password::", ":username::"); print(next((value[:-len(s)] for s in suffixes if value.endswith(s)), value))')"

export PG_SECRET_JSON="$(aws secretsmanager get-secret-value --secret-id 'tfe/codex/prod/postgres-readonly' --region us-east-1 --query SecretString --output text)"
export PGHOST="$(python3 -c 'import json,os; print(json.loads(os.environ["PG_SECRET_JSON"])["host"])')"
export PGPORT="$(python3 -c 'import json,os; print(json.loads(os.environ["PG_SECRET_JSON"])["port"])')"
export PGDATABASE="$(python3 -c 'import json,os; print(json.loads(os.environ["PG_SECRET_JSON"])["dbname"])')"
export PGUSER="$(python3 -c 'import json,os; print(json.loads(os.environ["PG_SECRET_JSON"])["username"])')"
export PGPASSWORD="$(python3 -c 'import json,os; print(json.loads(os.environ["PG_SECRET_JSON"])["password"])')"
export TFE_DB_SSL_REJECT_UNAUTHORIZED="true"
export NODE_EXTRA_CA_CERTS="/workspaces/Tao_Financial_Engine/certs/rds-global-bundle.pem"

unset BOOTSTRAP_JSON
unset ASSUME_JSON
unset PG_SECRET_JSON
unset PROD_TASKDEF_JSON

echo "Loaded Codex production read-only verification env." >&2
