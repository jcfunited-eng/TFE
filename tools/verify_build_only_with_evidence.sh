#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/workspaces/Tao_Financial_Engine"
cd "$REPO_ROOT"

REGION="us-east-1"
ACCOUNT_ID="418384447921"
ECR_REPO="tfe-web"
CODEBUILD_PROJECT="tfe-web-image-build"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
IMAGE_TAG="verify-${TS}"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
S3_ARCHIVE="s3://tfe-codebuild-src-418384447921-us-east-1/deploy/archive/tfe_codebuild_src-verify-${TS}.zip"
S3_ARCHIVE_NO_SCHEME="tfe-codebuild-src-418384447921-us-east-1/deploy/archive/tfe_codebuild_src-verify-${TS}.zip"
TMP_SRC_DIR="/tmp/tfe_codebuild_src_verify"
STAGE_DIR="${TMP_SRC_DIR}/stage_${TS}"
ZIP_PATH="${TMP_SRC_DIR}/source_${TS}.zip"
EVIDENCE_DIR="${REPO_ROOT}/backups/build-verify-evidence-${TS}"
MISSING_LIST="${EVIDENCE_DIR}/package-missing-sources.txt"
SOURCE_LIST="${EVIDENCE_DIR}/dockerfile-copy-sources.txt"

mkdir -p "$TMP_SRC_DIR" "$STAGE_DIR" "$EVIDENCE_DIR"

on_fail() {
  echo "BUILD_VERIFY_FAILED evidence_dir=${EVIDENCE_DIR}" >&2
}
trap on_fail ERR

aws sts get-caller-identity --output json >"${EVIDENCE_DIR}/caller-identity.json"

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
copied_entries=0
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
      copied_entries=$((copied_entries + 1))
    elif [ -f "$src" ]; then
      mkdir -p "$(dirname "$dst")"
      cp -a "$src" "$dst"
      copied_entries=$((copied_entries + 1))
    fi
  done
done <"$SOURCE_LIST"

if [ "$copied_entries" -eq 0 ]; then
  echo "Packaging failed: no sources copied." >&2
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
printf "source_patterns\t%s\ncopied_entries\t%s\nmissing_patterns\t%s\n" "$pattern_count" "$copied_entries" "$missing_count" >"${EVIDENCE_DIR}/package-summary.tsv"

aws s3 cp "$ZIP_PATH" "$S3_ARCHIVE" --region "$REGION" >"${EVIDENCE_DIR}/s3-archive-upload.txt"

aws codebuild start-build \
  --project-name "$CODEBUILD_PROJECT" \
  --region "$REGION" \
  --source-type-override S3 \
  --source-location-override "$S3_ARCHIVE_NO_SCHEME" \
  --environment-variables-override "name=IMAGE_URI,value=${IMAGE_URI},type=PLAINTEXT" \
  --output json >"${EVIDENCE_DIR}/codebuild-start.json"

BUILD_ID="$(jq -r '.build.id' "${EVIDENCE_DIR}/codebuild-start.json")"

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

aws ecr describe-images \
  --repository-name "$ECR_REPO" \
  --region "$REGION" \
  --image-ids imageTag="$IMAGE_TAG" \
  --output json >"${EVIDENCE_DIR}/image-post.json"

IMAGE_DIGEST="$(jq -r '.imageDetails[0].imageDigest // ""' "${EVIDENCE_DIR}/image-post.json")"

cat >"${EVIDENCE_DIR}/build-verify.env" <<ENV
TS=${TS}
IMAGE_TAG=${IMAGE_TAG}
IMAGE_URI=${IMAGE_URI}
IMAGE_DIGEST=${IMAGE_DIGEST}
S3_ARCHIVE=${S3_ARCHIVE}
ZIP_PATH=${ZIP_PATH}
BUILD_ID=${BUILD_ID}
NO_ECS_UPDATE=true
NO_SHARED_DEPLOY_POINTER_UPDATE=true
ENV

cat >"${EVIDENCE_DIR}/build-verify-report.tsv" <<TSV
key	value
verify_timestamp_utc	${TS}
image_tag	${IMAGE_TAG}
image_uri	${IMAGE_URI}
image_digest	${IMAGE_DIGEST}
codebuild_id	${BUILD_ID}
source_patterns	${pattern_count}
copied_entries	${copied_entries}
missing_patterns	${missing_count}
no_ecs_update	true
no_shared_deploy_pointer_update	true
TSV

echo "./backups/build-verify-evidence-${TS}" >"${REPO_ROOT}/backups/CURRENT_BUILD_VERIFY_EVIDENCE_POINTER.txt"

echo "BUILD_VERIFY_EVIDENCE_DIR=${EVIDENCE_DIR}"
echo "BUILD_ID=${BUILD_ID}"
echo "IMAGE_URI=${IMAGE_URI}"
echo "NO_ECS_UPDATE=true"
echo "NO_SHARED_DEPLOY_POINTER_UPDATE=true"
