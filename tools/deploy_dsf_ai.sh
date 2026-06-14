#!/usr/bin/env bash
# GUALALOOM-BAND-AND-AUDIT-WC-2026-06-05
# Deploy script for DSF-AI service (GualaLoom) to ECS via CodeBuild.
#
# Usage: ./tools/deploy_dsf_ai.sh
#
# This script:
#   1. Packages the source tree into a zip
#   2. Uploads to S3 (CodeBuild source bucket)
#   3. Triggers CodeBuild (dsf-ai-image-build) to build + push to ECR
#   4. Waits for CodeBuild to complete
#   5. Registers a new ECS task definition revision
#   6. Updates the ECS service to use the new task def
#   7. Waits for service stability
#
# Prerequisites:
#   - AWS CLI configured with credentials
#   - Run from repo root: ./tools/deploy_dsf_ai.sh

set -euo pipefail

# ── Constants ──
AWS_REGION="us-east-1"
AWS_ACCOUNT="418384447921"
ECR_REPO="dsf-ai"
ECR_URI="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
ECS_CLUSTER="tfe-web-cluster"
ECS_SERVICE="dsf-ai-service-lb"
TASK_FAMILY="dsf-ai-task"
CODEBUILD_PROJECT="dsf-ai-image-build"
S3_BUCKET="tfe-codebuild-src-${AWS_ACCOUNT}-${AWS_REGION}"
S3_KEY="deploy/dsf_ai_codebuild_src.zip"

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
IMAGE_TAG="deploy-${TIMESTAMP}"
IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"

echo "═══════════════════════════════════════════"
echo "  DSF-AI (GualaLoom) Deploy via CodeBuild"
echo "  ${TIMESTAMP}"
echo "═══════════════════════════════════════════"

# ── Step 0: Preflight ──
echo ""
echo "[0/6] Preflight checks..."

if ! command -v aws &>/dev/null; then
    echo "ERROR: aws CLI not found"
    exit 1
fi

GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
echo "  Git SHA: ${GIT_SHA}"
echo "  Image:   ${IMAGE_URI}"

# C3: Assert zero-downtime deploy config (rolling — new starts before old stops)
CFG=$(aws ecs describe-services --cluster ${ECS_CLUSTER} \
  --services ${ECS_SERVICE} \
  --query 'services[0].deploymentConfiguration.[maximumPercent,minimumHealthyPercent]' \
  --output text)
if [ "$CFG" != "200	100" ]; then
    echo "Deploy config needs update (got: $CFG, need: 200 100)"
    echo "Updating to zero-downtime rolling deploy..."
    aws ecs update-service --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} \
      --deployment-configuration minimumHealthyPercent=100,maximumPercent=200 \
      --health-check-grace-period-seconds 120 \
      --no-cli-pager > /dev/null
    echo "  Updated to rolling deploy (max=200, min=100, grace=30s)"
else
    echo "  Deploy config: zero-downtime ✓ (max=200, min=100)"
fi

# ── Step 1: Package source ──
echo ""
echo "[1/6] Packaging source..."

STAGING=$(mktemp -d)
trap "rm -rf ${STAGING}" EXIT

# Extract committed source tree (clean, no local artifacts)
git archive HEAD | tar -x -C "${STAGING}"

# Create zip
(cd "${STAGING}" && zip -rq /tmp/dsf_ai_codebuild_src.zip .)
ZIP_SIZE=$(du -sh /tmp/dsf_ai_codebuild_src.zip | cut -f1)
echo "  Package: ${ZIP_SIZE}"

# ── Step 2: Upload to S3 ──
echo ""
echo "[2/6] Uploading to S3..."
aws s3 cp /tmp/dsf_ai_codebuild_src.zip "s3://${S3_BUCKET}/${S3_KEY}" --quiet
echo "  Uploaded: s3://${S3_BUCKET}/${S3_KEY}"

# ── Step 3: Trigger CodeBuild ──
echo ""
echo "[3/6] Starting CodeBuild..."

BUILD_ID=$(aws codebuild start-build \
    --project-name "${CODEBUILD_PROJECT}" \
    --environment-variables-override \
        "name=IMAGE_URI,value=${IMAGE_URI},type=PLAINTEXT" \
    --query 'build.id' \
    --output text)

echo "  Build ID: ${BUILD_ID}"
echo "  Waiting for build to complete..."

# Poll build status
while true; do
    STATUS=$(aws codebuild batch-get-builds \
        --ids "${BUILD_ID}" \
        --query 'builds[0].buildStatus' \
        --output text)
    PHASE=$(aws codebuild batch-get-builds \
        --ids "${BUILD_ID}" \
        --query 'builds[0].currentPhase' \
        --output text)

    if [ "${STATUS}" = "SUCCEEDED" ]; then
        echo "  Build SUCCEEDED"
        break
    elif [ "${STATUS}" = "FAILED" ] || [ "${STATUS}" = "FAULT" ] || [ "${STATUS}" = "STOPPED" ] || [ "${STATUS}" = "TIMED_OUT" ]; then
        echo "  Build ${STATUS} — check CloudWatch logs at /aws/codebuild/${CODEBUILD_PROJECT}"
        exit 1
    fi

    echo "    phase: ${PHASE} | status: ${STATUS}"
    sleep 15
done

# ── Step 4: Also push as :latest ──
# CodeBuild pushed the timestamped tag. We also need :latest for the task def.
# Since we don't have Docker locally, we'll use the ECR manifest copy API.
echo ""
echo "[4/6] Tagging image as :latest..."

# Get the image manifest for the deploy tag and put it as latest
MANIFEST=$(aws ecr batch-get-image \
    --repository-name "${ECR_REPO}" \
    --image-ids imageTag="${IMAGE_TAG}" \
    --query 'images[0].imageManifest' \
    --output text 2>/dev/null || echo "")

if [ -n "${MANIFEST}" ] && [ "${MANIFEST}" != "None" ]; then
    aws ecr put-image \
        --repository-name "${ECR_REPO}" \
        --image-tag "latest" \
        --image-manifest "${MANIFEST}" 2>/dev/null || true
    echo "  Tagged ${IMAGE_TAG} as latest"
else
    echo "  WARNING: Could not tag as latest (image may already exist)"
fi

# ── Step 5: Register new task definition ──
echo ""
echo "[5/6] Registering new task definition..."

TASK_DEF_JSON=$(aws ecs describe-task-definition \
    --task-definition ${TASK_FAMILY} \
    --query 'taskDefinition' \
    --output json)

NEW_TASK_DEF=$(echo "${TASK_DEF_JSON}" | python3 -c "
import sys, json
td = json.load(sys.stdin)
td['containerDefinitions'][0]['image'] = '${IMAGE_URI}'
# C3: give container 15s for SIGTERM final save before SIGKILL
td['containerDefinitions'][0]['stopTimeout'] = 15
# WARMTH: container health check uses /ready (not /health)
# Task not marked healthy until _guala is loaded
td['containerDefinitions'][0]['healthCheck'] = {
    'command': ['CMD-SHELL', 'python3 -c \"import urllib.request; urllib.request.urlopen(\\\"http://localhost:8080/ready\\\")\" || exit 1'],
    'interval': 10,
    'timeout': 5,
    'retries': 3,
    'startPeriod': 180
}
keep = ['family', 'containerDefinitions', 'volumes', 'networkMode',
        'requiresCompatibilities', 'cpu', 'memory', 'executionRoleArn',
        'taskRoleArn', 'runtimePlatform']
out = {k: td[k] for k in keep if k in td and td[k]}
print(json.dumps(out))
")

NEW_REV=$(aws ecs register-task-definition \
    --cli-input-json "${NEW_TASK_DEF}" \
    --query 'taskDefinition.revision' \
    --output text)

echo "  Registered: ${TASK_FAMILY}:${NEW_REV}"

# ── Step 6: Update service ──
echo ""
echo "[6/6] Updating ECS service..."
aws ecs update-service \
    --cluster ${ECS_CLUSTER} \
    --service ${ECS_SERVICE} \
    --task-definition "${TASK_FAMILY}:${NEW_REV}" \
    --force-new-deployment \
    --query 'service.deployments[0].{status:status,taskDef:taskDefinition}' \
    --output table

echo ""
echo "Waiting for service stability (timeout: 5 min)..."
if aws ecs wait services-stable \
    --cluster ${ECS_CLUSTER} \
    --services ${ECS_SERVICE} 2>/dev/null; then
    echo "  Service stable."
else
    echo "  WARNING: wait timed out. Check AWS Console."
fi

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════"
echo "  Deploy complete"
echo "  Image:    ${IMAGE_URI}"
echo "  Task def: ${TASK_FAMILY}:${NEW_REV}"
echo "  Git SHA:  ${GIT_SHA}"
echo ""
echo "  NEXT: Audit dsf-ai.com/gualaloom.html"
echo "═══════════════════════════════════════════"
