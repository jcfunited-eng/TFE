#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/workspaces/Tao_Financial_Engine"
cd "$REPO_ROOT"

REGION="us-east-1"
ACCOUNT_ID="418384447921"
ECR_REPO="tfe-web"
CODEBUILD_PROJECT="tfe-web-image-build"
CLUSTER="tfe-web-cluster"
SERVICE="tfe-web-service-lb"
TASK_FAMILY="tfe-web-task"
S3_DEPLOY="s3://tfe-codebuild-src-418384447921-us-east-1/deploy/tfe_codebuild_src.zip"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
IMAGE_TAG="manual-${TS}"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
S3_ARCHIVE="s3://tfe-codebuild-src-418384447921-us-east-1/deploy/archive/tfe_codebuild_src-${TS}.zip"
TMP_SRC_DIR="/tmp/tfe_codebuild_src"
STAGE_DIR="${TMP_SRC_DIR}/stage_${TS}"
ZIP_PATH="${TMP_SRC_DIR}/source_${TS}.zip"
EVIDENCE_DIR="${REPO_ROOT}/backups/deploy-evidence-${TS}"
MISSING_LIST="${EVIDENCE_DIR}/package-missing-sources.txt"
SOURCE_LIST="${EVIDENCE_DIR}/dockerfile-copy-sources.txt"

mkdir -p "$TMP_SRC_DIR" "$STAGE_DIR" "$EVIDENCE_DIR"

on_fail() {
  echo "DEPLOY_FAILED evidence_dir=${EVIDENCE_DIR}" >&2
}
trap on_fail ERR

# Rollback-safe pre-state capture
aws sts get-caller-identity --output json >"${EVIDENCE_DIR}/caller-identity.json"
aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --region "$REGION" --output json >"${EVIDENCE_DIR}/ecs-service-pre.json"
aws ecs describe-task-definition --task-definition "$TASK_FAMILY" --region "$REGION" --output json >"${EVIDENCE_DIR}/taskdef-current.json"

# Build source patterns directly from Dockerfile COPY directives (excluding --from stages).
awk '/^COPY / {
  if ($2 ~ /^--from=/) next;
  for (i=2; i<NF; i++) print $i;
}' "${REPO_ROOT}/web/Dockerfile" | sed 's/\r$//' >"$SOURCE_LIST"
cat >>"$SOURCE_LIST" <<'LIST'
buildspec.yml
web/Dockerfile
.dockerignore
LIST
sort -u "$SOURCE_LIST" -o "$SOURCE_LIST"

shopt -s nullglob dotglob

: >"$MISSING_LIST"
pattern_count=0
copied_count=0
missing_count=0

while IFS= read -r pattern; do
  pattern="${pattern#./}"
  [ -z "$pattern" ] && continue
  pattern_count=$((pattern_count + 1))

  matches=("$REPO_ROOT"/$pattern)
  if [ "${#matches[@]}" -eq 0 ]; then
    echo "$pattern" >>"$MISSING_LIST"
    missing_count=$((missing_count + 1))
    continue
  fi

  for src in "${matches[@]}"; do
    rel="${src#${REPO_ROOT}/}"
    dst="${STAGE_DIR}/${rel}"
    if [ -d "$src" ]; then
      mkdir -p "$dst"
      cp -a "$src"/. "$dst"/
      copied_count=$((copied_count + 1))
    elif [ -f "$src" ]; then
      mkdir -p "$(dirname "$dst")"
      cp -a "$src" "$dst"
      copied_count=$((copied_count + 1))
    fi
  done
done <"$SOURCE_LIST"

if [ "$copied_count" -eq 0 ]; then
  echo "Packaging failed: no sources copied from Dockerfile patterns." >&2
  exit 1
fi

if [ "$missing_count" -gt 0 ]; then
  echo "Packaging failed: missing required source patterns." >&2
  cat "$MISSING_LIST" >&2
  exit 1
fi

(
  cd "$STAGE_DIR"
  zip -qry "$ZIP_PATH" .
)

sha256sum "$ZIP_PATH" >"${EVIDENCE_DIR}/source-zip-sha.txt"
printf "source_patterns\t%s\ncopied_entries\t%s\nmissing_patterns\t%s\n" "$pattern_count" "$copied_count" "$missing_count" >"${EVIDENCE_DIR}/package-summary.tsv"

# Upload source archive and deploy pointer zip
aws s3 cp "$ZIP_PATH" "$S3_ARCHIVE" --region "$REGION" >"${EVIDENCE_DIR}/s3-archive-upload.txt"
aws s3 cp "$ZIP_PATH" "$S3_DEPLOY" --region "$REGION" >"${EVIDENCE_DIR}/s3-deploy-upload.txt"

# Start CodeBuild image build
aws codebuild start-build \
  --project-name "$CODEBUILD_PROJECT" \
  --region "$REGION" \
  --environment-variables-override "name=IMAGE_URI,value=${IMAGE_URI},type=PLAINTEXT" \
  --output json >"${EVIDENCE_DIR}/codebuild-start.json"

BUILD_ID="$(jq -r '.build.id' "${EVIDENCE_DIR}/codebuild-start.json")"

# Poll build completion
: >"${EVIDENCE_DIR}/codebuild-poll.log"
for attempt in $(seq 1 180); do
  aws codebuild batch-get-builds --ids "$BUILD_ID" --region "$REGION" --output json >"${EVIDENCE_DIR}/codebuild-result.json"
  STATUS="$(jq -r '.builds[0].buildStatus' "${EVIDENCE_DIR}/codebuild-result.json")"
  PHASE="$(jq -r '.builds[0].currentPhase' "${EVIDENCE_DIR}/codebuild-result.json")"
  echo "attempt=${attempt} status=${STATUS} phase=${PHASE}" >>"${EVIDENCE_DIR}/codebuild-poll.log"
  if [ "$STATUS" = "SUCCEEDED" ]; then
    break
  fi
  if [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "FAULT" ] || [ "$STATUS" = "TIMED_OUT" ] || [ "$STATUS" = "STOPPED" ]; then
    echo "CodeBuild ended in failure status: $STATUS" >&2
    exit 1
  fi
  sleep 5
done

FINAL_STATUS="$(jq -r '.builds[0].buildStatus' "${EVIDENCE_DIR}/codebuild-result.json")"
if [ "$FINAL_STATUS" != "SUCCEEDED" ]; then
  echo "CodeBuild did not complete in allowed polling window." >&2
  exit 1
fi

# Register new task definition with new image
jq --arg IMAGE "$IMAGE_URI" '.taskDefinition
  | del(.taskDefinitionArn,.revision,.status,.requiresAttributes,.compatibilities,.registeredAt,.registeredBy)
  | .containerDefinitions[0].image=$IMAGE' \
  "${EVIDENCE_DIR}/taskdef-current.json" >"${EVIDENCE_DIR}/taskdef-register-input.json"

aws ecs register-task-definition \
  --cli-input-json file://"${EVIDENCE_DIR}/taskdef-register-input.json" \
  --region "$REGION" \
  --output json >"${EVIDENCE_DIR}/taskdef-register-output.json"

NEW_TASKDEF="$(jq -r '.taskDefinition.taskDefinitionArn' "${EVIDENCE_DIR}/taskdef-register-output.json")"

# Update ECS service
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --task-definition "$NEW_TASKDEF" \
  --region "$REGION" \
  --output json >"${EVIDENCE_DIR}/ecs-service-update.json"

# Wait for steady state
aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE" --region "$REGION"
aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --region "$REGION" --output json >"${EVIDENCE_DIR}/ecs-service-post.json"

CURRENT_TASKDEF="$(jq -r '.services[0].taskDefinition' "${EVIDENCE_DIR}/ecs-service-post.json")"
DEPLOY_ROLLOUT_STATE="$(jq -r '.services[0].deployments[] | select(.status=="PRIMARY") | .rolloutState' "${EVIDENCE_DIR}/ecs-service-post.json" | head -n 1)"

aws ecs describe-task-definition --task-definition "$CURRENT_TASKDEF" --region "$REGION" --output json >"${EVIDENCE_DIR}/ecs-task-post.json"
POST_IMAGE="$(jq -r '.taskDefinition.containerDefinitions[0].image' "${EVIDENCE_DIR}/ecs-task-post.json")"

cat >"${EVIDENCE_DIR}/deploy.env" <<ENV
TS=${TS}
IMAGE_TAG=${IMAGE_TAG}
IMAGE_URI=${IMAGE_URI}
S3_ARCHIVE=${S3_ARCHIVE}
S3_DEPLOY=${S3_DEPLOY}
ZIP_PATH=${ZIP_PATH}
BUILD_ID=${BUILD_ID}
NEW_TASKDEF=${NEW_TASKDEF}
POST_IMAGE=${POST_IMAGE}
DEPLOY_ROLLOUT_STATE=${DEPLOY_ROLLOUT_STATE}
ENV

cat >"${EVIDENCE_DIR}/deploy-report.tsv" <<TSV
key	value
deploy_timestamp_utc	${TS}
image_tag	${IMAGE_TAG}
image_uri	${IMAGE_URI}
codebuild_id	${BUILD_ID}
task_definition	${NEW_TASKDEF}
service	${SERVICE}
cluster	${CLUSTER}
post_task_image	${POST_IMAGE}
deploy_rollout_state	${DEPLOY_ROLLOUT_STATE}
source_patterns	${pattern_count}
copied_entries	${copied_count}
missing_patterns	${missing_count}
TSV

echo "./backups/deploy-evidence-${TS}" >"${REPO_ROOT}/backups/CURRENT_DEPLOY_EVIDENCE_POINTER.txt"

echo "DEPLOY_EVIDENCE_DIR=${EVIDENCE_DIR}"
echo "BUILD_ID=${BUILD_ID}"
echo "NEW_TASKDEF=${NEW_TASKDEF}"
echo "POST_IMAGE=${POST_IMAGE}"
