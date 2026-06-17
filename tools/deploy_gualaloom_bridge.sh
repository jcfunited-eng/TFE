#!/usr/bin/env bash
# GUALALOOM-V7-BRIDGE-WC-2026-06-07
# Deploy script for GualaLoom MCP Bridge to ECS via CodeBuild.
set -euo pipefail

AWS_REGION="us-east-1"
AWS_ACCOUNT="418384447921"
ECR_REPO="gualaloom-bridge"
ECR_URI="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
ECS_CLUSTER="tfe-web-cluster"
ECS_SERVICE="gualaloom-bridge-svc"
TASK_FAMILY="gualaloom-bridge-task"
CODEBUILD_PROJECT="gualaloom-bridge-build"
S3_BUCKET="tfe-codebuild-src-${AWS_ACCOUNT}-${AWS_REGION}"
S3_KEY="deploy/gualaloom_bridge_src.zip"

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
IMAGE_TAG="deploy-${TIMESTAMP}"
IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"

echo "═══════════════════════════════════════════"
echo "  GualaLoom MCP Bridge Deploy"
echo "  ${TIMESTAMP}"
echo "═══════════════════════════════════════════"

GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
echo "  Git SHA: ${GIT_SHA}"
echo "  Image:   ${IMAGE_URI}"

# Package source
echo ""
echo "[1/5] Packaging source..."
STAGING=$(mktemp -d)
trap "rm -rf ${STAGING}" EXIT
git archive HEAD | tar -x -C "${STAGING}"
(cd "${STAGING}" && zip -rq /tmp/gualaloom_bridge_src.zip .)
echo "  Done"

# Upload to S3
echo ""
echo "[2/5] Uploading to S3..."
aws s3 cp /tmp/gualaloom_bridge_src.zip "s3://${S3_BUCKET}/${S3_KEY}" --quiet
echo "  Uploaded"

# Build via CodeBuild
echo ""
echo "[3/5] Starting CodeBuild..."
BUILD_ID=$(aws codebuild start-build \
    --project-name "${CODEBUILD_PROJECT}" \
    --buildspec-override "bridge/buildspec.yml" \
    --environment-variables-override \
        "name=IMAGE_URI,value=${IMAGE_URI},type=PLAINTEXT" \
    --query 'build.id' --output text)
echo "  Build: ${BUILD_ID}"

while true; do
    STATUS=$(aws codebuild batch-get-builds --ids "${BUILD_ID}" \
        --query 'builds[0].buildStatus' --output text)
    PHASE=$(aws codebuild batch-get-builds --ids "${BUILD_ID}" \
        --query 'builds[0].currentPhase' --output text)
    if [ "${STATUS}" = "SUCCEEDED" ]; then echo "  Build SUCCEEDED"; break; fi
    if [ "${STATUS}" = "FAILED" ] || [ "${STATUS}" = "FAULT" ] || [ "${STATUS}" = "STOPPED" ]; then
        echo "  Build ${STATUS}"; exit 1; fi
    echo "    phase: ${PHASE} | status: ${STATUS}"
    sleep 15
done

# Register task definition (create if first time)
echo ""
echo "[4/5] Registering task definition..."

# Check if task family exists
EXISTING=$(aws ecs describe-task-definition --task-definition ${TASK_FAMILY} 2>/dev/null \
    --query 'taskDefinition.revision' --output text || echo "NONE")

if [ "${EXISTING}" = "NONE" ]; then
    echo "  First deploy — creating task definition..."
    NEW_REV=$(aws ecs register-task-definition \
        --family "${TASK_FAMILY}" \
        --network-mode "awsvpc" \
        --requires-compatibilities "FARGATE" \
        --cpu "256" --memory "512" \
        --execution-role-arn "arn:aws:iam::${AWS_ACCOUNT}:role/tfe-ecs-task-execution-role" \
        --container-definitions "[{
            \"name\": \"bridge\",
            \"image\": \"${IMAGE_URI}\",
            \"portMappings\": [{\"containerPort\": 8080, \"protocol\": \"tcp\"}],
            \"essential\": true,
            \"logConfiguration\": {
                \"logDriver\": \"awslogs\",
                \"options\": {
                    \"awslogs-group\": \"/ecs/gualaloom-bridge\",
                    \"awslogs-region\": \"${AWS_REGION}\",
                    \"awslogs-stream-prefix\": \"bridge\"
                }
            },
            \"environment\": [
                {\"name\": \"GUALALOOM_API_URL\", \"value\": \"http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com\"}
            ]
        }]" \
        --query 'taskDefinition.revision' --output text)
else
    TASK_DEF_JSON=$(aws ecs describe-task-definition --task-definition ${TASK_FAMILY} \
        --query 'taskDefinition' --output json)
    NEW_TASK_DEF=$(echo "${TASK_DEF_JSON}" | python3 -c "
import sys, json
td = json.load(sys.stdin)
td['containerDefinitions'][0]['image'] = '${IMAGE_URI}'
keep = ['family', 'containerDefinitions', 'networkMode',
        'requiresCompatibilities', 'cpu', 'memory', 'executionRoleArn',
        'taskRoleArn', 'runtimePlatform']
out = {k: td[k] for k in keep if k in td and td[k]}
print(json.dumps(out))
")
    NEW_REV=$(aws ecs register-task-definition \
        --cli-input-json "${NEW_TASK_DEF}" \
        --query 'taskDefinition.revision' --output text)
fi

echo "  Registered: ${TASK_FAMILY}:${NEW_REV}"

# Update or create ECS service
echo ""
echo "[5/5] Updating ECS service..."

SVC_EXISTS=$(aws ecs describe-services --cluster ${ECS_CLUSTER} \
    --services ${ECS_SERVICE} --query 'services[0].status' --output text 2>/dev/null || echo "MISSING")

if [ "${SVC_EXISTS}" = "MISSING" ] || [ "${SVC_EXISTS}" = "INACTIVE" ]; then
    echo "  Service does not exist — skipping ECS service creation."
    echo "  Create it manually with correct subnet/security group config:"
    echo "    aws ecs create-service --cluster ${ECS_CLUSTER} --service-name ${ECS_SERVICE} \\"
    echo "      --task-definition ${TASK_FAMILY}:${NEW_REV} --desired-count 1 \\"
    echo "      --launch-type FARGATE --network-configuration <subnets+sg>"
else
    aws ecs update-service \
        --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} \
        --task-definition "${TASK_FAMILY}:${NEW_REV}" \
        --force-new-deployment \
        --query 'service.deployments[0].{status:status,taskDef:taskDefinition}' \
        --output table
    echo "  Waiting for stability..."
    aws ecs wait services-stable --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} 2>/dev/null || true
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  Bridge deploy complete"
echo "  Image:    ${IMAGE_URI}"
echo "  Task def: ${TASK_FAMILY}:${NEW_REV}"
echo "  Git SHA:  ${GIT_SHA}"
echo "═══════════════════════════════════════════"
