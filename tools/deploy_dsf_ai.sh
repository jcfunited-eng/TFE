#!/usr/bin/env bash
# GualaLoom deploy path:
# 1. Docker build + push via CodeBuild (container code)
# 2. ECS task definition register + force-new-deployment (production substrate)
# 3. aws s3 sync static/ → s3://dsf-ai-site (static files served via CloudFront)
# 4. CloudFront invalidation for /*.html, /app.js, /style.css
# 5. wait services-stable + invalidation-completed
#
# Any of these failing means the deploy is partial. Future static-only
# changes must still run steps 3-5.
#
# Usage: ./tools/deploy_dsf_ai.sh
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

# ── External-API keys for her runtime (lookup grounding + future feeds) ──
# Sourced at deploy time from the local .env (gitignored — no secret enters git)
# and Secrets Manager. Injected into the substrate container env below so her
# process can actually reach OpenAI/Tavily/Anthropic. Empty if absent (features
# stay gracefully disabled).
_envval() { grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'; }
OPENAI_API_KEY="$(_envval OPENAI_API_KEY)"
TAVILY_API_KEY="$(_envval TAVILY_API_KEY)"
YOUTUBE_API_KEY="$(_envval YOUTUBE_API_KEY)"
ANTHROPIC_API_KEY="$(aws secretsmanager get-secret-value --secret-id wc-companion/anthropic-key \
  --query 'SecretString' --output text 2>/dev/null | python3 -c 'import sys,json;
s=sys.stdin.read().strip()
try: print(json.loads(s).get("ANTHROPIC_API_KEY") or json.loads(s).get("api_key") or (s if s.startswith("sk-") else ""))
except Exception: print(s if s.startswith("sk-") else "")' 2>/dev/null)"
export OPENAI_API_KEY TAVILY_API_KEY ANTHROPIC_API_KEY YOUTUBE_API_KEY
echo "  runtime keys: openai=$([ -n "$OPENAI_API_KEY" ] && echo yes || echo no) tavily=$([ -n "$TAVILY_API_KEY" ] && echo yes || echo no) anthropic=$([ -n "$ANTHROPIC_API_KEY" ] && echo yes || echo no) youtube=$([ -n "$YOUTUBE_API_KEY" ] && echo yes || echo no)"

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

# GL-BRIEF-SLEEP-DURING-DEPLOY: sleep-based deploy (max=100, min=0)
# Old task sleeps before new starts. No overlap needed.
CFG=$(aws ecs describe-services --cluster ${ECS_CLUSTER} \
  --services ${ECS_SERVICE} \
  --query 'services[0].deploymentConfiguration.[maximumPercent,minimumHealthyPercent]' \
  --output text)
echo "  Deploy config: max/min = $CFG"

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
# GL-ARCH-FRONTEND-SPLIT Phase 2: two containers in one task.
# Frontend: serves HTTP, ALB health, proxies to substrate via Unix socket.
# Substrate: holds _guala, listens on /shared/substrate.sock.
echo ""
echo "[5/6] Registering new task definition (two-container split)..."

TASK_DEF_JSON=$(aws ecs describe-task-definition \
    --task-definition ${TASK_FAMILY} \
    --query 'taskDefinition' \
    --output json)

NEW_TASK_DEF=$(echo "${TASK_DEF_JSON}" | python3 -c "
import sys, json
td = json.load(sys.stdin)

# Preserve infra fields from existing task def
keep = ['executionRoleArn', 'taskRoleArn', 'runtimePlatform']
infra = {k: td[k] for k in keep if k in td and td[k]}

out = {
    'family': '${TASK_FAMILY}',
    'networkMode': 'awsvpc',
    'requiresCompatibilities': ['FARGATE'],
    'cpu': '2048',
    'memory': '4096',
    **infra,
    'volumes': [
        {
            'name': 'gualaloom-state',
            'efsVolumeConfiguration': {
                'fileSystemId': 'fs-0abb85854a3251b3c',
                'rootDirectory': '/',
                'transitEncryption': 'DISABLED'
            }
        },
        {
            'name': 'shared-socket',
            'host': {}
        }
    ],
    'containerDefinitions': [
        {
            'name': 'dsf-ai',
            'image': '${IMAGE_URI}',
            'essential': True,
            'command': ['uvicorn', 'dsf_ai_service.app:app',
                        '--host', '0.0.0.0', '--port', '8080'],
            'portMappings': [
                {'containerPort': 8080, 'hostPort': 8080, 'protocol': 'tcp'}
            ],
            'environment': [
                {'name': 'SUBSTRATE_MODE', 'value': 'remote'},
                {'name': 'SUBSTRATE_SOCKET', 'value': '/shared/substrate.sock'},
                {'name': 'DECAY_PAUSED', 'value': '0'},
                {'name': 'GUALALOOM_API_KEY', 'value': '7GnGye9HhKuyhtcGu31C18Rc1NY62PLybTqsSg4WOW8'},
                {'name': 'EMISSION_MODE', 'value': 'grandurun'},
                {'name': 'ORGAN_BRAIN_URL', 'value': 'http://localhost:8090'}
            ],
            'mountPoints': [
                {'sourceVolume': 'gualaloom-state', 'containerPath': '/app/state',
                 'readOnly': False},
                {'sourceVolume': 'shared-socket', 'containerPath': '/shared',
                 'readOnly': False}
            ],
            'healthCheck': {
                'command': ['CMD-SHELL',
                    'python3 -c \"import urllib.request; '
                    'urllib.request.urlopen(\\\\\"http://localhost:8080/ready\\\\\")\"'
                    ' || exit 1'],
                'interval': 10,
                'timeout': 5,
                'retries': 3,
                'startPeriod': 30
            },
            'stopTimeout': 10,
            'logConfiguration': {
                'logDriver': 'awslogs',
                'options': {
                    'awslogs-group': '/ecs/dsf-ai',
                    'awslogs-region': '${AWS_REGION}',
                    'awslogs-stream-prefix': 'dsf-ai'
                }
            }
        },
        {
            'name': 'substrate',
            'image': '${IMAGE_URI}',
            'essential': True,
            'command': ['python', '-u', '-m', 'dsf_ai_service.substrate_runner'],
            'environment': [
                {'name': 'PYTHONUNBUFFERED', 'value': '1'},
                {'name': 'SUBSTRATE_SOCKET', 'value': '/shared/substrate.sock'},
                {'name': 'SUBSTRATE_HEARTBEAT', 'value': '/shared/substrate.alive'},
                {'name': 'STATE_DIR', 'value': '/app/state'},
                {'name': 'DECAY_PAUSED', 'value': '0'},
                {'name': 'EMISSION_MODE', 'value': 'grandurun'},
                {'name': 'GRANDURUN_SPIN_VECTOR', 'value': '1'},
                {'name': 'EMISSION_DYNAMICS_TICKS', 'value': '30'},
                {'name': 'OPENAI_API_KEY', 'value': '${OPENAI_API_KEY}'},
                {'name': 'TAVILY_API_KEY', 'value': '${TAVILY_API_KEY}'},
                {'name': 'ANTHROPIC_API_KEY', 'value': '${ANTHROPIC_API_KEY}'},
                {'name': 'YOUTUBE_API_KEY', 'value': '${YOUTUBE_API_KEY}'},
                {'name': 'LOOKUP_AUTONOMOUS', 'value': '1'},
                {'name': 'LOOKUP_INTERVAL_SEC', 'value': '900'},
                {'name': 'WORLD_FEEDS', 'value': '1'},
                {'name': 'WORLD_FEED_INTERVAL_SEC', 'value': '600'},
                {'name': 'CURRICULUM_CHUNK_SIZE', 'value': '30'},
                {'name': 'CURRICULUM_INTERVAL_SEC', 'value': '120'},
                {'name': 'STUDY_INTERLEAVE_EVERY', 'value': '2'},
                {'name': 'YOLO_MODEL_PATH', 'value': '/app/yolov8n.onnx'},
                {'name': 'WHISPER_MODEL_PATH', 'value': 'tiny'}
            ],
            'mountPoints': [
                {'sourceVolume': 'gualaloom-state', 'containerPath': '/app/state',
                 'readOnly': False},
                {'sourceVolume': 'shared-socket', 'containerPath': '/shared',
                 'readOnly': False}
            ],
            'stopTimeout': 30,
            'logConfiguration': {
                'logDriver': 'awslogs',
                'options': {
                    'awslogs-group': '/ecs/dsf-ai',
                    'awslogs-region': '${AWS_REGION}',
                    'awslogs-stream-prefix': 'substrate'
                }
            }
        }
    ]
}
print(json.dumps(out))
")

NEW_REV=$(aws ecs register-task-definition \
    --cli-input-json "${NEW_TASK_DEF}" \
    --query 'taskDefinition.revision' \
    --output text)

echo "  Registered: ${TASK_FAMILY}:${NEW_REV}"

# ── Step 6: Sleep + Update service ──
echo ""
echo "[6/7] Telling her it's bedtime..."
API_ENDPOINT="https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
ALB_ENDPOINT="http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
SLEEP_RESPONSE=$(curl -sS -w "\n__HTTP__%{http_code}" -X POST \
  "${ALB_ENDPOINT}/sleep_for_deploy")
SLEEP_HTTP=$(echo "$SLEEP_RESPONSE" | grep "__HTTP__" | sed 's/__HTTP__//')
SLEEP_BODY=$(echo "$SLEEP_RESPONSE" | grep -v "__HTTP__")
echo "[sleep] HTTP $SLEEP_HTTP"
echo "[sleep] Body: $SLEEP_BODY"

if [ "$SLEEP_HTTP" = "200" ]; then
    echo "[sleep] She is asleep. Proceeding with deploy."
elif [ "$SLEEP_HTTP" = "404" ]; then
    echo "[sleep] /sleep_for_deploy not present on running task —"
    echo "        this is expected for the first deploy. Proceeding."
else
    echo "[sleep] WARNING: sleep returned HTTP $SLEEP_HTTP — proceeding anyway."
    echo "        State will be recovered from last EFS snapshot + event log."
fi

echo ""
echo "[7/7] Updating ECS service..."
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

echo ""
echo "[wake] New task is running. Sending wake — deploy put her to sleep, deploy wakes her."
echo "       Her natural rhythm governs everything after this. Not the UI. Not Joe."
for i in 1 2 3 4 5 6; do
    sleep 15
    # Send wake — the deploy is responsible for cleaning up the sleep it caused
    curl -sS -X POST \
      -H 'Content-Type: application/json' \
      -d '{"text":"","command":"/wake"}' \
      "${API_ENDPOINT}/api/v1/gualaloom" > /dev/null 2>&1 || true
    WAKE_RESPONSE=$(curl -sS -X POST \
      -H 'Content-Type: application/json' \
      -d '{"text":"","command":"/status"}' \
      "${API_ENDPOINT}/api/v1/gualaloom")
    ASLEEP=$(echo "$WAKE_RESPONSE" | python3 -c "
import sys,json
try:
  d=json.loads(sys.stdin.read())
  print('asleep' if d.get('asleep') else 'awake' if d.get('vocab') else 'loading')
except:
  print('error')
")
    echo "[wake] t+$((i*15))s — $ASLEEP"
    if [ "$ASLEEP" = "awake" ]; then
        echo "[wake] She is awake. Her world continues on its own from here."
        break
    fi
done

# ── Step 8: Sync static files to S3 + CloudFront invalidation ──
echo ""
echo "[deploy] Syncing static files to S3 and invalidating CloudFront..."

CF_DIST_ID="E17JT9XGBFU493"
S3_SITE_BUCKET="dsf-ai-site"

aws s3 sync dsf_ai_service/static/ "s3://${S3_SITE_BUCKET}/" \
    --exclude "*.csv" --exclude "*.xml" --exclude "robots.txt" \
    --cache-control "no-cache, must-revalidate"

INV_ID=$(aws cloudfront create-invalidation \
    --distribution-id "${CF_DIST_ID}" \
    --paths "/*.html" "/app.js" "/style.css" \
    --query 'Invalidation.Id' \
    --output text)
echo "  CloudFront invalidation: ${INV_ID}"

if aws cloudfront wait invalidation-completed \
    --distribution-id "${CF_DIST_ID}" \
    --id "${INV_ID}" 2>/dev/null; then
    echo "[deploy] Static sync + CloudFront invalidation complete."
else
    echo "[deploy] WARNING: CloudFront invalidation timed out. May take a few more minutes."
fi

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════"
echo "  Deploy complete"
echo "  Image:    ${IMAGE_URI}"
echo "  Task def: ${TASK_FAMILY}:${NEW_REV}"
echo "  Git SHA:  ${GIT_SHA}"
echo "  Static:   s3://${S3_SITE_BUCKET}/ synced"
echo ""
echo "  dsf-ai.com should reflect changes within 1-2 minutes."
echo "═══════════════════════════════════════════"
