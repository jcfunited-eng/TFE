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
# Usage: ./tools/deploy_dsf_ai.sh [--force-s3-restore]
#   --force-s3-restore  Inject FORCE_S3_RESTORE=1 for THIS deploy only.
#                       Boot will download from most-recent S3 backup before
#                       loading EFS state. Remove the flag for all subsequent
#                       deploys — one-time flags must never live in default config.
#
# Prerequisites:
#   - AWS CLI configured with credentials
#   - Run from repo root: ./tools/deploy_dsf_ai.sh

set -euo pipefail

# Parse optional flags
FORCE_S3_RESTORE_FLAG=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --force-s3-restore)
            FORCE_S3_RESTORE_FLAG="yes"
            echo "[deploy] --force-s3-restore: FORCE_S3_RESTORE=1 will be injected for this deploy only."
            shift
            ;;
        *)
            echo "ERROR: unknown deployment argument: $1"
            exit 1
            ;;
    esac
done

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
TASK_SECURITY_GROUP="sg-057566437ba8d4b48"
ALB_SECURITY_GROUP="sg-0c9ff138eba21a6fa"
ALB_DNS="dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
CONTROL_ORIGIN="https://dsf-ai.com"
DEPLOY_CONFIG="maximumPercent=100,minimumHealthyPercent=0,deploymentCircuitBreaker={enable=true,rollback=true}"

# Required runtime secrets must exist in AWS before deployment.  External-model
# lookup is retired: OpenAI is neither required nor injected.  YouTube is an
# optional world feed and remains explicitly disabled when its key is absent.
# There is no .env/plaintext fallback for the required credentials.
GUALALOOM_SECRET_ID="gualaloom/api-key/prod"
TAVILY_SECRET_ID="tfe/tavily/prod"
ANTHROPIC_SECRET_ID="wc-companion/anthropic-key"

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

for required_command in aws curl git python3 tar zip; do
    if ! command -v "${required_command}" &>/dev/null; then
        echo "ERROR: required command not found: ${required_command}"
        exit 1
    fi
done

if ! GIT_SHA=$(git rev-parse --verify HEAD 2>/dev/null); then
    echo "ERROR: repository has no deployable HEAD commit"
    exit 1
fi

# One release is one reviewed commit.  This includes untracked files: silently
# omitting a new module is just as dangerous as silently omitting a modification.
if [ -n "$(git status --porcelain=v1 --untracked-files=all)" ]; then
    echo "ERROR: working tree is dirty or has untracked files; refusing to deploy"
    echo "       Commit the complete reviewed release before packaging."
    git status --short
    exit 1
fi

require_secret_arn() {
    local secret_id="$1"
    local secret_arn
    if ! secret_arn=$(aws secretsmanager describe-secret \
        --secret-id "${secret_id}" --query ARN --output text); then
        echo "ERROR: required Secrets Manager secret is absent or unreadable: ${secret_id}" >&2
        return 1
    fi
    if [ -z "${secret_arn}" ] || [ "${secret_arn}" = "None" ]; then
        echo "ERROR: required Secrets Manager secret has no ARN: ${secret_id}" >&2
        return 1
    fi
    printf '%s' "${secret_arn}"
}

GUALALOOM_SECRET_ARN=$(require_secret_arn "${GUALALOOM_SECRET_ID}") || exit 1
TAVILY_SECRET_ARN=$(require_secret_arn "${TAVILY_SECRET_ID}") || exit 1
ANTHROPIC_SECRET_ARN=$(require_secret_arn "${ANTHROPIC_SECRET_ID}") || exit 1
export GUALALOOM_SECRET_ARN TAVILY_SECRET_ARN ANTHROPIC_SECRET_ARN

# The deploy control credential is held only in this process and sent only over
# verified TLS.  It is never copied into task-definition environment plaintext.
if ! DEPLOY_API_KEY=$(aws secretsmanager get-secret-value \
    --secret-id "${GUALALOOM_SECRET_ARN}" --query SecretString --output text); then
    echo "ERROR: deploy control credential could not be read"
    exit 1
fi
if [ -z "${DEPLOY_API_KEY}" ] || [ "${DEPLOY_API_KEY}" = "None" ]; then
    echo "ERROR: deploy control credential is empty"
    exit 1
fi
DEPLOY_NONCE=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

TASK_DEF_JSON=$(aws ecs describe-task-definition \
    --task-definition "${TASK_FAMILY}" \
    --query taskDefinition --output json)
EXECUTION_ROLE_ARN=$(printf '%s' "${TASK_DEF_JSON}" | python3 -c '
import json, sys
value = json.load(sys.stdin).get("executionRoleArn")
if not value:
    raise SystemExit("task definition has no executionRoleArn")
print(value)
')

# ECS resolves `secrets.valueFrom` with the execution role.  Registering a task
# that cannot read every referenced secret would only move the failure to boot.
SECRET_ACCESS=$(aws iam simulate-principal-policy \
    --policy-source-arn "${EXECUTION_ROLE_ARN}" \
    --action-names secretsmanager:GetSecretValue \
    --resource-arns "${GUALALOOM_SECRET_ARN}" "${TAVILY_SECRET_ARN}" \
        "${ANTHROPIC_SECRET_ARN}" \
    --query 'EvaluationResults[].EvalDecision' --output text)
if ! SECRET_ACCESS="${SECRET_ACCESS}" python3 -c '
import os
decisions = os.environ["SECRET_ACCESS"].split()
if len(decisions) != 3 or any(value != "allowed" for value in decisions):
    raise SystemExit(1)
'; then
    echo "ERROR: ECS execution role lacks GetSecretValue on every runtime secret"
    echo "       role: ${EXECUTION_ROLE_ARN}"
    exit 1
fi

OLD_TASKS_TEXT=$(aws ecs list-tasks --cluster "${ECS_CLUSTER}" \
    --service-name "${ECS_SERVICE}" --desired-status RUNNING \
    --query 'taskArns' --output text)
read -r -a OLD_TASK_ARNS <<< "${OLD_TASKS_TEXT}"
if [ "${#OLD_TASK_ARNS[@]}" -ne 1 ] || [ "${OLD_TASK_ARNS[0]}" = "None" ]; then
    echo "ERROR: expected exactly one current state owner, found ${#OLD_TASK_ARNS[@]}"
    exit 1
fi
OLD_TASK_ARN="${OLD_TASK_ARNS[0]}"
OLD_TASK_JSON=$(aws ecs describe-tasks \
    --cluster "${ECS_CLUSTER}" --tasks "${OLD_TASK_ARN}" \
    --query 'tasks[0]' --output json)
if ! OLD_OWNER_IDENTITY=$(printf '%s' "${OLD_TASK_JSON}" | python3 -c '
import json, re, sys
task = json.load(sys.stdin)
containers = task.get("containers", [])
task_definition = task.get("taskDefinitionArn")
if task.get("lastStatus") != "RUNNING":
    raise SystemExit("current owner is not RUNNING")
if not isinstance(task_definition, str) or not task_definition:
    raise SystemExit("current owner has no task definition")
if len(containers) != 1:
    raise SystemExit("current owner does not have exactly one container")
image_digest = containers[0].get("imageDigest")
if not isinstance(image_digest, str) or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", image_digest):
    raise SystemExit("current owner has no exact image digest")
print(task_definition, image_digest, sep="\t")
'); then
    echo "ERROR: current state owner identity could not be proven"
    exit 1
fi
IFS=$'\t' read -r OLD_TASK_DEFINITION_ARN OLD_IMAGE_DIGEST <<< "${OLD_OWNER_IDENTITY}"
OLD_SEALED_BOOT=$(aws ecs describe-task-definition \
    --task-definition "${OLD_TASK_DEFINITION_ARN}" \
    --query "taskDefinition.containerDefinitions[?name=='dsf-ai'].environment[]" \
    --output json | python3 -c '
import json, sys
items = json.load(sys.stdin)
values = {item.get("name"): item.get("value") for item in items}
print("1" if values.get("GUALA_REQUIRE_SEALED_STATE") == "1" else "0")
')
if [ "${OLD_SEALED_BOOT}" != "1" ]; then
    # A transitional owner may have the complete authenticated generation
    # sealer while not yet having booted from a sealed generation itself.
    # Admit that one-way cutover only when the live process proves the exact
    # seal endpoint is mounted.  The later nonce-bound seal/read-back remains
    # the hard state gate; failure there occurs before the old owner stops.
    LEGACY_OPENAPI=$(curl -sS \
        --connect-to "dsf-ai.com:443:${ALB_DNS}:443" \
        --connect-timeout 10 --max-time 30 \
        "${CONTROL_ORIGIN}/openapi.json")
    if ! printf '%s' "${LEGACY_OPENAPI}" | python3 -c '
import json, sys
paths = json.load(sys.stdin).get("paths", {})
route = paths.get("/sleep_for_deploy", {})
if "post" not in route:
    raise SystemExit("live owner has no authenticated generation-seal endpoint")
'; then
        echo "ERROR: current production owner cannot create the first sealed generation"
        echo "       Production remains online and untouched."
        exit 1
    fi
    echo "[generation] Live transitional owner proved the authenticated seal endpoint."
fi

# Remove direct internet access to port 8080 and retain only ALB-to-task ingress.
TASK_SG_JSON=$(aws ec2 describe-security-groups --group-ids "${TASK_SECURITY_GROUP}" \
    --query 'SecurityGroups[0]' --output json)
if TASK_SG_JSON="${TASK_SG_JSON}" python3 -c '
import json, os
sg = json.loads(os.environ["TASK_SG_JSON"])
for rule in sg.get("IpPermissions", []):
    if rule.get("IpProtocol") == "tcp" and rule.get("FromPort") <= 8080 <= rule.get("ToPort"):
        if any(item.get("CidrIp") == "0.0.0.0/0" for item in rule.get("IpRanges", [])):
            raise SystemExit(0)
raise SystemExit(1)
'; then
    aws ec2 revoke-security-group-ingress --group-id "${TASK_SECURITY_GROUP}" \
        --protocol tcp --port 8080 --cidr 0.0.0.0/0
fi

TASK_SG_JSON=$(aws ec2 describe-security-groups --group-ids "${TASK_SECURITY_GROUP}" \
    --query 'SecurityGroups[0]' --output json)
if ! TASK_SG_JSON="${TASK_SG_JSON}" ALB_SECURITY_GROUP="${ALB_SECURITY_GROUP}" python3 -c '
import json, os
sg = json.loads(os.environ["TASK_SG_JSON"])
alb = os.environ["ALB_SECURITY_GROUP"]
allowed = False
for rule in sg.get("IpPermissions", []):
    if rule.get("IpProtocol") != "tcp" or not (rule.get("FromPort") <= 8080 <= rule.get("ToPort")):
        continue
    if rule.get("IpRanges") or rule.get("Ipv6Ranges"):
        raise SystemExit("task port 8080 still has CIDR ingress")
    if any(item.get("GroupId") == alb for item in rule.get("UserIdGroupPairs", [])):
        allowed = True
if not allowed:
    raise SystemExit("task port 8080 is not restricted to the ALB security group")
'; then
    echo "ERROR: task security group is not ALB-only on port 8080"
    exit 1
fi

echo "  Git SHA: ${GIT_SHA}"
echo "  Image:   ${IMAGE_URI}"
echo "  Old owner: ${OLD_TASK_ARN}"

# ── Step 1: Package source ──
echo ""
echo "[1/6] Packaging source..."

DEPLOY_WORK_DIR=$(mktemp -d)
STAGING="${DEPLOY_WORK_DIR}/source"
ARCHIVE_ZIP="${DEPLOY_WORK_DIR}/dsf_ai_codebuild_src.zip"
mkdir -p "${STAGING}"
OWNER_FAIL_CLOSED=0

fail_closed_owner_cleanup() {
    local cleanup_failed=0
    local family_tasks_text=""
    local task_arn=""
    local final_service_json=""
    local FAMILY_REMAINING=""

    echo "[turnover] Failure after handoff began; enforcing zero state owners."
    if ! aws ecs update-service --cluster "${ECS_CLUSTER}" \
        --service "${ECS_SERVICE}" --desired-count 0 \
        --deployment-configuration "${DEPLOY_CONFIG}"; then
        echo "ERROR: fail-closed cleanup could not set desired count to zero"
        cleanup_failed=1
    fi
    if ! aws ecs wait services-stable --cluster "${ECS_CLUSTER}" \
        --services "${ECS_SERVICE}"; then
        echo "ERROR: fail-closed cleanup could not prove service stability at zero"
        cleanup_failed=1
    fi

    # Catch any untracked family task as well.  At this point the old owner is
    # retired and service desired count is zero, so every RUNNING-family task is
    # an unauthorized standalone owner and must be stopped explicitly.
    if family_tasks_text=$(aws ecs list-tasks --cluster "${ECS_CLUSTER}" \
        --family "${TASK_FAMILY}" --desired-status RUNNING \
        --query 'taskArns' --output text); then
        for task_arn in ${family_tasks_text}; do
            if [ "${task_arn}" = "None" ]; then
                continue
            fi
            if ! aws ecs stop-task --cluster "${ECS_CLUSTER}" \
                --task "${task_arn}" \
                --reason "Fail-closed Guala deployment family cleanup"; then
                echo "ERROR: fail-closed cleanup could not stop family task ${task_arn}"
                cleanup_failed=1
                continue
            fi
            if ! aws ecs wait tasks-stopped --cluster "${ECS_CLUSTER}" \
                --tasks "${task_arn}"; then
                echo "ERROR: fail-closed cleanup could not prove family task STOPPED: ${task_arn}"
                cleanup_failed=1
            fi
        done
    else
        echo "ERROR: fail-closed cleanup could not enumerate task-family owners"
        cleanup_failed=1
    fi

    if final_service_json=$(aws ecs describe-services --cluster "${ECS_CLUSTER}" \
        --services "${ECS_SERVICE}" --query 'services[0]' --output json); then
        if ! printf '%s' "${final_service_json}" | python3 -c '
import json, sys
service = json.load(sys.stdin)
counts = {name: service.get(name) for name in (
    "desiredCount", "runningCount", "pendingCount")}
if counts != {"desiredCount": 0, "runningCount": 0, "pendingCount": 0}:
    raise SystemExit("service ownership counts are not all zero: " + str(counts))
'; then
            echo "ERROR: fail-closed service ownership proof is not zero"
            cleanup_failed=1
        fi
    else
        echo "ERROR: fail-closed cleanup could not inspect final service counts"
        cleanup_failed=1
    fi
    if FAMILY_REMAINING=$(aws ecs list-tasks --cluster "${ECS_CLUSTER}" \
        --family "${TASK_FAMILY}" --desired-status RUNNING \
        --query 'length(taskArns)' --output text); then
        if [ "${FAMILY_REMAINING}" != "0" ]; then
            echo "ERROR: fail-closed cleanup left ${FAMILY_REMAINING} RUNNING-family task(s)"
            cleanup_failed=1
        fi
    else
        echo "ERROR: fail-closed cleanup could not prove the task family empty"
        cleanup_failed=1
    fi
    return "${cleanup_failed}"
}

deployment_exit_cleanup() {
    local exit_code=$?
    local final_code="${exit_code}"
    trap - EXIT
    if [ "${OWNER_FAIL_CLOSED}" = "1" ] && [ "${exit_code}" != "0" ]; then
        if ! fail_closed_owner_cleanup; then
            echo "ERROR: fail-closed owner cleanup did not complete exactly"
            final_code=1
        fi
    fi
    if ! rm -rf "${DEPLOY_WORK_DIR}"; then
        echo "ERROR: local deployment staging cleanup failed: ${DEPLOY_WORK_DIR}"
        final_code=1
    fi
    exit "${final_code}"
}
trap deployment_exit_cleanup EXIT

# Extract the exact reviewed commit.  This directory is authoritative for both
# the image source and the static assets published after readiness verification.
git archive "${GIT_SHA}" | tar -x -C "${STAGING}"

# Create zip
(cd "${STAGING}" && zip -rq "${ARCHIVE_ZIP}" .)
ZIP_SIZE=$(du -sh "${ARCHIVE_ZIP}" | cut -f1)
echo "  Package: ${ZIP_SIZE}"

# ── Step 2: Upload to S3 ──
echo ""
echo "[2/6] Uploading to S3..."
aws s3 cp "${ARCHIVE_ZIP}" "s3://${S3_BUCKET}/${S3_KEY}" --quiet
echo "  Uploaded: s3://${S3_BUCKET}/${S3_KEY}"

# ── Step 3: Trigger CodeBuild ──
echo ""
echo "[3/6] Starting CodeBuild..."

BUILD_ID=$(aws codebuild start-build \
    --project-name "${CODEBUILD_PROJECT}" \
    --environment-variables-override \
        "name=IMAGE_URI,value=${IMAGE_URI},type=PLAINTEXT" \
        "name=GIT_SHA,value=${GIT_SHA},type=PLAINTEXT" \
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

EXPECTED_IMAGE_DIGEST=$(aws ecr describe-images \
    --repository-name "${ECR_REPO}" --image-ids imageTag="${IMAGE_TAG}" \
    --query 'imageDetails[0].imageDigest' --output text)
if ! EXPECTED_IMAGE_DIGEST="${EXPECTED_IMAGE_DIGEST}" python3 -c '
import os, re
if not re.fullmatch(r"sha256:[0-9a-f]{64}", os.environ["EXPECTED_IMAGE_DIGEST"]):
    raise SystemExit(1)
'; then
    echo "ERROR: built image has no valid immutable digest"
    exit 1
fi
echo "  Image digest: ${EXPECTED_IMAGE_DIGEST}"

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
    --output text) || {
    echo "ERROR: failed to read ECR manifest for ${IMAGE_TAG}; latest was not tagged"
    exit 1
}

if [ -n "${MANIFEST}" ] && [ "${MANIFEST}" != "None" ]; then
    if ! aws ecr put-image \
        --repository-name "${ECR_REPO}" \
        --image-tag "latest" \
        --image-manifest "${MANIFEST}"; then
        echo "ERROR: failed to tag ${IMAGE_TAG} as latest"
        exit 1
    fi
    echo "  Tagged ${IMAGE_TAG} as latest"
else
    echo "ERROR: ECR returned no manifest for ${IMAGE_TAG}; latest was not tagged"
    exit 1
fi

# ── Step 5: Register new task definition ──
echo ""
echo "[5/6] Registering new task definition..."

# GL-CMD-81: inject FORCE_S3_RESTORE only when --force-s3-restore flag was passed
if [ "${FORCE_S3_RESTORE_FLAG}" = "yes" ]; then
  export _FORCE_S3_RESTORE_INJECT=1
fi

NEW_TASK_DEF=$(echo "${TASK_DEF_JSON}" | python3 -c "
import sys, json, os
td = json.load(sys.stdin)

# Preserve infra fields from existing task def
keep = ['executionRoleArn', 'taskRoleArn', 'runtimePlatform', 'cpu', 'memory']
infra = {k: td[k] for k in keep if k in td and td[k]}

# GL-INCIDENT-DEPLOY-SCRIPT-MEMORY-UNDERSIZE-EVE-20260708-v1: cpu/memory
# used to be hardcoded here (2048/4096 -- stale from an early version of
# this script, long since outgrown), requiring a manual post-register
# patch-task-def step every deploy (see prior session precedent: task
# def revision 547 patched to 548 for correct cpu/memory, 4096/16384).
# That manual step was missed on 2026-07-08's Phase 1 deploy attempt --
# the resulting under-provisioned task (2048/4096, a quarter of the real
# 4096/16384 requirement) OOM-killed ~48-53s after boot on EVERY attempt,
# masquerading as a code-level regression until traced back here. Fixed
# by inheriting cpu/memory from whatever's actually currently deployed
# (via the keep list, above) instead of a hardcoded default that can go
# stale -- self-correcting from here on, no more manual patch step needed.
out = {
    'family': '${TASK_FAMILY}',
    'networkMode': 'awsvpc',
    'requiresCompatibilities': ['FARGATE'],
    **infra,
    'volumes': [
        {
            'name': 'gualaloom-state',
            'efsVolumeConfiguration': {
                'fileSystemId': 'fs-0abb85854a3251b3c',
                'rootDirectory': '/',
                'transitEncryption': 'ENABLED'
            }
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
                {'name': 'SUBSTRATE_MODE', 'value': 'embedded'},
                {'name': 'SUBSTRATE_HEARTBEAT', 'value': '/app/guala/substrate.alive'},
                {'name': 'STATE_DIR', 'value': '/app/guala/active'},
                {'name': 'GUALA_GENERATION_STORE_ROOT', 'value': '/app/guala/sealed'},
                {'name': 'GUALA_OWNER_LOCK_PATH', 'value': '/app/guala/.guala-owner.lock'},
                {'name': 'GUALA_REQUIRE_SEALED_STATE', 'value': '1'},
                {'name': 'DECAY_PAUSED', 'value': '0'},
                {'name': 'EMISSION_MODE', 'value': 'grandurun'},
                {'name': 'ORGAN_BRAIN_URL', 'value': 'http://localhost:8090'},
                {'name': 'PYTHONUNBUFFERED', 'value': '1'},
                {'name': 'GRANDURUN_SPIN_VECTOR', 'value': '1'},
                {'name': 'EMISSION_DYNAMICS', 'value': '1'},
                {'name': 'DEPLOY_EXPECTED_GIT_SHA', 'value': '${GIT_SHA}'},
                {'name': 'DEPLOY_EXPECTED_IMAGE_DIGEST', 'value': '${EXPECTED_IMAGE_DIGEST}'},
                {'name': 'WORLD_FEEDS', 'value': '1'},
                {'name': 'WORLD_FEED_INTERVAL_SEC', 'value': '600'},
                {'name': 'CURRICULUM_CHUNK_SIZE', 'value': '30'},
                {'name': 'CURRICULUM_INTERVAL_SEC', 'value': '120'},
                {'name': 'STUDY_INTERLEAVE_EVERY', 'value': '2'},
                {'name': 'CURRICULUM_AUTOSTART', 'value': '0'},  # GL-CMD-109: 65-A retired
                {'name': 'CURRICULUM_SEED_PATH', 'value': '/app/tools/curriculum_seed.json'},
                {'name': 'CURRICULUM_ORCHESTRATOR_INTERVAL_SEC', 'value': '5'},
                {'name': 'CURRICULUM_SUBSTRATE_URL', 'value': 'http://localhost:8080'},
                {'name': 'CONVERSE_PHASED', 'value': '1'},
                {'name': 'AUTONOMY_PHASED', 'value': '0'},
                {'name': 'DREAM_CYCLE_PHASED', 'value': '1'},
                {'name': 'EMISSION_DYNAMICS_TICKS', 'value': '80'},  # GL-CMD-87: 40→80
                {'name': 'WAVE_ATLAS_ENABLED', 'value': '1'},
                # GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2: dual-
                # write/dual-read Phase 1. RECALL_BACKEND=legacy is the
                # code's own default when unset, set explicitly here so
                # it's visible in infra config. Shadow mode was briefly
                # enabled 2026-07-12 and reverted the same night on Joe's
                # direct order -- no parallel/side systems running, one
                # system only. Do not re-enable without his explicit
                # instruction.
                {'name': 'RECALL_BACKEND', 'value': 'legacy'},
                # 2026-07-12: graduating the two safest of five same-night
                # kill-switched loom_model features, per a dedicated real
                # investigation (docs/GL-RPT-INERT-FEATURES-GRADUATION-
                # PLAN-CODEX-20260712-v1) that ranked all five by risk.
                # Both ship with real concurrency-stress tests and both
                # re-pass the existing cascade regression test with the
                # flag on. Neither can affect real speech/memory today --
                # RECALL_BACKEND=legacy above means loom_model doesn't
                # drive her real voice yet, so the only real risk is a
                # crash/corruption in the shadow subsystem, which is
                # exactly what these tests targeted. Homeostatic scaling
                # only ever reduces an over-saturated neuron's synapse
                # weights (same direction as STDP depression, away from
                # the saturation that caused the 2026-07-08 cascade).
                # Entry-neuron broadening is capped by a structural (not
                # tuned) ceiling -- any subset of one 8-neuron hemisphere
                # clique as entries can never exceed that hemisphere's own
                # 12.5% injection breadth, half the 25%-of-population
                # threshold that caused the entry-neuron over-injection
                # incident this fix's own commit documents. Energy-limit
                # and mood-broadcast stay OFF -- the graduation plan's own
                # ordering says sequence energy-limit in after these two
                # are observed, not alongside them. Vocabulary-seeding
                # stays OFF -- it only ever teaches a disposable practice
                # copy, not her real saved memory, so enabling it
                # wouldn't do anything real yet.
                {'name': 'HOMEOSTATIC_SCALING_ENABLED', 'value': '1'},
                {'name': 'ENTRY_NEURON_BROADEN_ENABLED', 'value': '1'},
                # 2026-07-12: GL-FIX-KEYHOLE-CONTENT-COUPLING. Real reply
                # generation (assemblage.py, /converse path, unrelated to
                # the loom_model/RECALL_BACKEND shadow subsystem above)
                # currently produces mostly one-word/empty replies because
                # its six per-role sections settle independently and only
                # borrow a commit-threshold discount from each other
                # (the existing "keyhole" mechanism) -- never real content.
                # docs/ArcLoom_Master_Specification_v5_0.tex Ch.3 prescribes
                # phase-coupled sections settling toward one coherent field;
                # a full single-field rewrite is out of scope for one
                # night's work, so this is a first, conservative step: a
                # sender's committed word becomes a bounded, auto-expiring
                # Hamiltonian goal in the receiver, reusing the exact
                # goal-injection machinery hear_speaker() already uses
                # safely in production (goal_op_for_template +
                # standing_goals) -- not new Hamiltonian-term code. Kept
                # directional (matching the existing acyclic keyhole chain,
                # not bidirectional) to avoid same-turn 2-cycle oscillation.
                # Verified: off-by-default is a true no-op, injected
                # operators are Hermitian/bounded, standing_goals never
                # grows past the existing 5-tick expiry window under
                # sustained pressure, a 300-tick zero-input stress run
                # shows no self-sustaining cascade (same detection method
                # as the 2026-07-08 STDP-cascade regression writeup), and
                # the full existing assemblage test suite (gamma
                # persistence, chi-bucket, mode-cap) still passes unchanged
                # -- see dsf_ai_service/substrate/test_keyhole_content_coupling.py.
                # Real end-to-end efficacy (does this raise the live
                # commit rate) is an observe-after-deploy question, same as
                # every other flag graduated tonight -- watch for it.
                # Revert by setting this back to '0' and redeploying.
                {'name': 'KEYHOLE_CONTENT_COUPLING_ENABLED', 'value': '1'},
                # 2026-07-09: this template previously left
                # EVENT_DRIVEN_SUBSTRATE UNSET (defaults to 1 in code) on
                # the theory it was only meant to be overridden for
                # rollback. That silently discarded a real emergency kill
                # switch on the very next normal deploy (this script
                # regenerates the whole container definition from
                # scratch), re-arming a ~3800Hz runaway-neuron spike-bus-
                # bleed incident's root mechanism with no explicit
                # decision by anyone. Caught within ~20 minutes via
                # /debug/stdp_state, reverted, and kept off (task-def
                # revisions 571-572) while the real root cause was
                # investigated.
                #
                # That investigation found the original diagnosis
                # (unbounded neuron-to-neuron cascade, no lateral
                # inhibition) was itself wrong: commit 712578f (2026-07-08,
                # predates tonight) traced 99.4% of firing to direct
                # external injection, not propagation -- entry-neuron
                # selection was falling back to a 16-neuron random sample
                # on every word instead of the intended 1-neuron chi
                # match. That commit fixed the real cause (16->1 entry
                # neurons per word, verified against a real downloaded
                # production pickle) and wired real chemistry-based
                # lateral inhibition (~20% inhibitory population split,
                # signed outgoing spikes) as a second, independent layer
                # -- test_lateral_inhibition_cascade.py's
                # test_real_polarity_fix_stops_the_cascade proves zero
                # post-input fires on the real seeded population. Commit
                # 56453a3 (2026-07-09) then fixed a separate STDP
                # learning-bootstrap deadlock, and this session added a
                # third layer, a fire-rate circuit breaker, purely as
                # backstop insurance.
                #
                # None of this had been tried live since 712578f landed --
                # it sat verified-offline only. This session ran a
                # deliberate, watched ~20-minute live trial on task-def
                # revision 573 (not an accident this time): spike bus
                # enabled, fire_rate_window_metrics stayed at 0 runaway
                # neurons / 0 breaker trips throughout, CPU held flat
                # 21-34%, spike count grew linearly (46->177->545), no
                # sign of the original incident's pattern. Passed. Set
                # back to the code's real default (1) here, durably, so a
                # normal deploy no longer contradicts a manually-verified
                # live state. If this ever needs reverting again, do it
                # exactly like the 2026-07-08/09 incidents: task-def env
                # override to 0, pause/update-service/wake, verify via
                # /debug/stdp_state, then fix this file so the revert
                # survives the next deploy too.
                {'name': 'EVENT_DRIVEN_SUBSTRATE', 'value': '1'},
                # GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711: kill
                # switch for wiring DeepAtlas.strength into real-speech
                # eligibility, so text-only vocabulary (e.g. "ocean") can
                # earn the right to be spoken through real repeated
                # exposure surviving real dream-cycle consolidation --
                # never a shortcut, never fabricated. Enabled 2026-07-11
                # for live validation per Joe's explicit go-ahead, after
                # independent line-by-line review confirmed every write
                # path is additive-only (an eligible word can never become
                # ineligible) and every signal traces to real committed
                # data (never fabricated). Effect is gradual by design --
                # requires real dream cycles to actually promote entries,
                # not instant. If this ever needs reverting, do it exactly
                # like the EVENT_DRIVEN_SUBSTRATE precedent above: task-def
                # env override to 0, pause/update-service/wake, then fix
                # this file so the revert survives the next deploy too.
                {'name': 'DEEP_ATLAS_ELIGIBILITY_BACKFILL_ENABLED', 'value': '1'}
            ] + ([{'name': 'FORCE_S3_RESTORE', 'value': '1'}] if os.environ.get('_FORCE_S3_RESTORE_INJECT') == '1' else []),
            'secrets': [
                {'name': 'GUALALOOM_API_KEY',
                 'valueFrom': os.environ['GUALALOOM_SECRET_ARN']},
                {'name': 'TAVILY_API_KEY',
                 'valueFrom': os.environ['TAVILY_SECRET_ARN'] + ':TAVILY_API_KEY::'},
                {'name': 'ANTHROPIC_API_KEY',
                 'valueFrom': os.environ['ANTHROPIC_SECRET_ARN']},
            ],
            'mountPoints': [
                {'sourceVolume': 'gualaloom-state', 'containerPath': '/app/guala',
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
                'startPeriod': 300
            },
            # Fargate's documented hard maximum is 120 seconds.  The sealed
            # deploy handoff must make shutdown save-free; this is only a
            # bounded thread/process-exit allowance, never persistence time.
            'stopTimeout': 120,
            'logConfiguration': {
                'logDriver': 'awslogs',
                'options': {
                    'awslogs-group': '/ecs/dsf-ai',
                    'awslogs-region': '${AWS_REGION}',
                    'awslogs-stream-prefix': 'dsf-ai'
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

# ── Step 6: Authenticated seal + single-owner turnover ──
echo ""
echo "[6/7] Requesting authenticated sealed-generation handoff..."

aws efs put-backup-policy --file-system-id fs-0abb85854a3251b3c \
    --backup-policy Status=ENABLED >/dev/null
EFS_BACKUP_POLICY=""
for _backup_attempt in $(seq 1 12); do
    EFS_BACKUP_POLICY=$(aws efs describe-backup-policy \
        --file-system-id fs-0abb85854a3251b3c \
        --query 'BackupPolicy.Status' --output text)
    if [ "${EFS_BACKUP_POLICY}" = "ENABLED" ]; then
        break
    fi
    sleep 5
done
if [ "${EFS_BACKUP_POLICY}" != "ENABLED" ]; then
    echo "ERROR: EFS automatic backup policy is not enabled"
    exit 1
fi
echo "[recovery] EFS automatic backup policy verified enabled."

# GL-FIX-S3-LIFECYCLE-SELF-HEAL-20260713: the AbortIncompleteMultipartUpload
# rule on the backups bucket (added after the 2026-07-06 incident where 272
# incomplete multipart uploads silently cost ~264GB) was found silently gone
# twice since (2026-07-12, 2026-07-13). S3's PutBucketLifecycleConfiguration
# always replaces the entire rule set, so any other actor's lifecycle PUT
# (nothing in this repo makes one -- some external/manual call did) wipes it
# with no error and nothing in these logs. This deploy already runs many
# times a day, so re-asserting the one rule this depends on every run means
# it can never stay missing "silently" for more than a few hours. Get-merge-
# put by fixed rule ID: only this one rule is ever asserted present, so any
# OTHER rule anyone else adds to this bucket is never touched or clobbered.
echo ""
echo "[recovery] Verifying S3 backup-bucket multipart-abort safety rule..."
S3_BACKUP_BUCKET="dsf-ai-site-backups"
REQUIRED_RULE_ID="guala-abort-incomplete-multipart-1d"
CURRENT_LIFECYCLE_JSON=$(aws s3api get-bucket-lifecycle-configuration \
    --bucket "${S3_BACKUP_BUCKET}" --query 'Rules' --output json 2>/dev/null || echo '[]')
MERGED_LIFECYCLE_JSON=$(CURRENT_LIFECYCLE_JSON="${CURRENT_LIFECYCLE_JSON}" \
    REQUIRED_RULE_ID="${REQUIRED_RULE_ID}" python3 -c '
import json, os
rules = json.loads(os.environ["CURRENT_LIFECYCLE_JSON"]) or []
rule_id = os.environ["REQUIRED_RULE_ID"]
if not any(r.get("ID") == rule_id for r in rules):
    rules.append({
        "ID": rule_id,
        "Filter": {},
        "Status": "Enabled",
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
    })
print(json.dumps({"Rules": rules}))
')
LIFECYCLE_TMP=$(mktemp)
printf '%s' "${MERGED_LIFECYCLE_JSON}" > "${LIFECYCLE_TMP}"
aws s3api put-bucket-lifecycle-configuration \
    --bucket "${S3_BACKUP_BUCKET}" \
    --lifecycle-configuration "file://${LIFECYCLE_TMP}"
rm -f "${LIFECYCLE_TMP}"
echo "[recovery] S3 backup-bucket multipart-abort rule verified present (rule id: ${REQUIRED_RULE_ID})."

# URL host remains dsf-ai.com so certificate/SNI verification is real; curl
# connects that origin directly to the ALB rather than the static CloudFront DNS.
CONTROL_CONNECT=(--connect-to "dsf-ai.com:443:${ALB_DNS}:443")

# Image construction can take long enough for the service to change underneath
# the preflight observation.  Re-prove the exact same sole owner immediately
# before the first handoff request; a different ARN, task definition, image, or
# service/family count aborts without touching the runtime.
CURRENT_SERVICE_JSON=$(aws ecs describe-services --cluster "${ECS_CLUSTER}" \
    --services "${ECS_SERVICE}" --query 'services[0]' --output json)
CURRENT_SERVICE_TASKS_TEXT=$(aws ecs list-tasks --cluster "${ECS_CLUSTER}" \
    --service-name "${ECS_SERVICE}" --desired-status RUNNING \
    --query 'taskArns' --output text)
CURRENT_FAMILY_TASKS_TEXT=$(aws ecs list-tasks --cluster "${ECS_CLUSTER}" \
    --family "${TASK_FAMILY}" --desired-status RUNNING \
    --query 'taskArns' --output text)
CURRENT_OLD_TASK_JSON=$(aws ecs describe-tasks --cluster "${ECS_CLUSTER}" \
    --tasks "${OLD_TASK_ARN}" --query 'tasks[0]' --output json)
if ! CURRENT_SERVICE_JSON="${CURRENT_SERVICE_JSON}" \
    CURRENT_SERVICE_TASKS_TEXT="${CURRENT_SERVICE_TASKS_TEXT}" \
    CURRENT_FAMILY_TASKS_TEXT="${CURRENT_FAMILY_TASKS_TEXT}" \
    CURRENT_OLD_TASK_JSON="${CURRENT_OLD_TASK_JSON}" \
    OLD_TASK_ARN="${OLD_TASK_ARN}" \
    OLD_TASK_DEFINITION_ARN="${OLD_TASK_DEFINITION_ARN}" \
    OLD_IMAGE_DIGEST="${OLD_IMAGE_DIGEST}" python3 -c '
import json, os
service = json.loads(os.environ["CURRENT_SERVICE_JSON"])
service_tasks = os.environ["CURRENT_SERVICE_TASKS_TEXT"].split()
family_tasks = os.environ["CURRENT_FAMILY_TASKS_TEXT"].split()
old_arn = os.environ["OLD_TASK_ARN"]
if service_tasks != [old_arn] or family_tasks != [old_arn]:
    raise SystemExit("the captured task is no longer the sole family/service owner")
counts = {name: service.get(name) for name in (
    "desiredCount", "runningCount", "pendingCount")}
if counts != {"desiredCount": 1, "runningCount": 1, "pendingCount": 0}:
    raise SystemExit("service ownership counts changed: " + str(counts))
if service.get("taskDefinition") != os.environ["OLD_TASK_DEFINITION_ARN"]:
    raise SystemExit("service task definition changed")
task = json.loads(os.environ["CURRENT_OLD_TASK_JSON"])
if task.get("taskArn") != old_arn or task.get("lastStatus") != "RUNNING":
    raise SystemExit("captured owner is no longer RUNNING")
if task.get("taskDefinitionArn") != os.environ["OLD_TASK_DEFINITION_ARN"]:
    raise SystemExit("captured owner task definition changed")
containers = task.get("containers", [])
if len(containers) != 1 or containers[0].get("imageDigest") != os.environ["OLD_IMAGE_DIGEST"]:
    raise SystemExit("captured owner image digest changed")
'; then
    echo "ERROR: the original sole owner changed during build; refusing handoff"
    exit 1
fi
echo "[turnover] Original sole owner re-proven immediately before handoff."

# Re-prove the captured task directly before the irreversible seal request.
FINAL_OLD_SERVICE_JSON=$(aws ecs describe-services --cluster "${ECS_CLUSTER}" \
    --services "${ECS_SERVICE}" --query 'services[0]' --output json)
FINAL_OLD_FAMILY_TASKS=$(aws ecs list-tasks --cluster "${ECS_CLUSTER}" \
    --family "${TASK_FAMILY}" --desired-status RUNNING \
    --query 'taskArns' --output text)
FINAL_OLD_TASK_JSON=$(aws ecs describe-tasks --cluster "${ECS_CLUSTER}" \
    --tasks "${OLD_TASK_ARN}" --query 'tasks[0]' --output json)
if ! FINAL_OLD_SERVICE_JSON="${FINAL_OLD_SERVICE_JSON}" \
    FINAL_OLD_FAMILY_TASKS="${FINAL_OLD_FAMILY_TASKS}" \
    FINAL_OLD_TASK_JSON="${FINAL_OLD_TASK_JSON}" OLD_TASK_ARN="${OLD_TASK_ARN}" \
    OLD_TASK_DEFINITION_ARN="${OLD_TASK_DEFINITION_ARN}" \
    OLD_IMAGE_DIGEST="${OLD_IMAGE_DIGEST}" python3 -c '
import json, os
old_arn = os.environ["OLD_TASK_ARN"]
if os.environ["FINAL_OLD_FAMILY_TASKS"].split() != [old_arn]:
    raise SystemExit("captured task is no longer the sole family owner")
service = json.loads(os.environ["FINAL_OLD_SERVICE_JSON"])
counts = {name: service.get(name) for name in (
    "desiredCount", "runningCount", "pendingCount")}
if counts != {"desiredCount": 1, "runningCount": 1, "pendingCount": 0}:
    raise SystemExit("service ownership counts changed immediately before handoff")
if service.get("taskDefinition") != os.environ["OLD_TASK_DEFINITION_ARN"]:
    raise SystemExit("service task definition changed immediately before handoff")
task = json.loads(os.environ["FINAL_OLD_TASK_JSON"])
containers = task.get("containers", [])
if (task.get("taskArn") != old_arn or task.get("lastStatus") != "RUNNING"
        or task.get("taskDefinitionArn") != os.environ["OLD_TASK_DEFINITION_ARN"]
        or len(containers) != 1
        or containers[0].get("imageDigest") != os.environ["OLD_IMAGE_DIGEST"]):
    raise SystemExit("captured task identity changed immediately before handoff")
'; then
    echo "ERROR: original sole owner changed immediately before handoff"
    exit 1
fi
echo "[turnover] Original sole owner re-proven directly before the seal request."
# From the first authenticated sleep/seal request onward, a failed or timed-out
# controller cannot know whether the runtime crossed its irreversible boundary.
# The composite EXIT trap therefore retires every possible owner on any failure.
OWNER_FAIL_CLOSED=1
if ! SLEEP_RESPONSE=$(curl -sS "${CONTROL_CONNECT[@]}" \
    --connect-timeout 10 --max-time 900 -w "\n__HTTP__%{http_code}" \
    -X POST -H 'Content-Type: application/json' \
    -H "X-API-Key: ${DEPLOY_API_KEY}" \
    -H "X-Deploy-Nonce: ${DEPLOY_NONCE}" \
    -d "{\"deploy_nonce\":\"${DEPLOY_NONCE}\"}" \
    "${CONTROL_ORIGIN}/sleep_for_deploy"); then
    echo "ERROR: authenticated deploy seal request failed"
    exit 1
fi
SLEEP_HTTP=$(printf '%s\n' "${SLEEP_RESPONSE}" | awk -F__HTTP__ '/__HTTP__/{print $2}')
SLEEP_BODY=$(printf '%s\n' "${SLEEP_RESPONSE}" | awk '!/__HTTP__/')
if [ "${SLEEP_HTTP}" != "200" ]; then
    echo "ERROR: deploy seal returned HTTP ${SLEEP_HTTP}; refusing turnover"
    exit 1
fi

if ! SEAL_PROOF=$(printf '%s' "${SLEEP_BODY}" | DEPLOY_NONCE="${DEPLOY_NONCE}" python3 -c '
import json, os, re, sys
value = json.load(sys.stdin)
generation = value.get("generation")
identity = value.get("identity")
manifest = value.get("manifest_sha256")
if value.get("ok") is not True or value.get("state") != "SEALED":
    raise SystemExit("quiesce response is not SEALED")
if value.get("deploy_nonce") != os.environ["DEPLOY_NONCE"]:
    raise SystemExit("quiesce nonce mismatch")
if not isinstance(generation, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,160}", generation):
    raise SystemExit("invalid sealed generation")
if not isinstance(identity, str) or not identity:
    raise SystemExit("missing sealed identity")
if not isinstance(manifest, str) or not re.fullmatch(r"[0-9a-f]{64}", manifest):
    raise SystemExit("invalid manifest SHA-256")
print(generation, identity, manifest, sep="\t")
'); then
    echo "ERROR: deploy seal did not return nonce-bound generation proof"
    exit 1
fi
IFS=$'\t' read -r SEALED_GENERATION SEALED_IDENTITY SEALED_MANIFEST <<< "${SEAL_PROOF}"
echo "[seal] generation=${SEALED_GENERATION} identity=${SEALED_IDENTITY:0:8} manifest=${SEALED_MANIFEST:0:12}..."

echo "[turnover] Scaling service to zero before any new owner may start..."
aws ecs update-service --cluster "${ECS_CLUSTER}" --service "${ECS_SERVICE}" \
    --desired-count 0 --deployment-configuration "${DEPLOY_CONFIG}" \
    --query 'service.{desired:desiredCount,deploy:deploymentConfiguration}' --output json
aws ecs wait services-stable --cluster "${ECS_CLUSTER}" --services "${ECS_SERVICE}"
aws ecs wait tasks-stopped --cluster "${ECS_CLUSTER}" --tasks "${OLD_TASK_ARN}"
OLD_STATUS=$(aws ecs describe-tasks --cluster "${ECS_CLUSTER}" --tasks "${OLD_TASK_ARN}" \
    --query 'tasks[0].lastStatus' --output text)
if [ "${OLD_STATUS}" != "STOPPED" ]; then
    echo "ERROR: prior state owner is not STOPPED: ${OLD_STATUS}"
    exit 1
fi
REMAINING_TASKS=$(aws ecs list-tasks --cluster "${ECS_CLUSTER}" \
    --service-name "${ECS_SERVICE}" --desired-status RUNNING \
    --query 'length(taskArns)' --output text)
if [ "${REMAINING_TASKS}" != "0" ]; then
    echo "ERROR: running task remains after owner retirement"
    exit 1
fi
echo "[turnover] Old owner STOPPED; new owner start is now permitted."

echo ""
echo "[7/7] Starting exactly one new owner..."
aws ecs update-service --cluster "${ECS_CLUSTER}" --service "${ECS_SERVICE}" \
    --desired-count 1 --task-definition "${TASK_FAMILY}:${NEW_REV}" \
    --deployment-configuration "${DEPLOY_CONFIG}" --force-new-deployment \
    --query 'service.deployments[0].{status:status,taskDef:taskDefinition}' --output table
if ! aws ecs wait services-stable --cluster "${ECS_CLUSTER}" --services "${ECS_SERVICE}"; then
    echo "ERROR: ECS service did not stabilize; circuit-breaker rollback is authoritative"
    exit 1
fi

NEW_TASKS_TEXT=$(aws ecs list-tasks --cluster "${ECS_CLUSTER}" \
    --service-name "${ECS_SERVICE}" --desired-status RUNNING \
    --query 'taskArns' --output text)
read -r -a NEW_TASK_ARNS <<< "${NEW_TASKS_TEXT}"
if [ "${#NEW_TASK_ARNS[@]}" -ne 1 ] || [ "${NEW_TASK_ARNS[0]}" = "None" ]; then
    echo "ERROR: expected exactly one new owner, found ${#NEW_TASK_ARNS[@]}"
    exit 1
fi
NEW_TASK_ARN="${NEW_TASK_ARNS[0]}"
if [ "${NEW_TASK_ARN}" = "${OLD_TASK_ARN}" ]; then
    echo "ERROR: ECS returned the retired task as the new owner"
    exit 1
fi
NEW_TASK_JSON=$(aws ecs describe-tasks --cluster "${ECS_CLUSTER}" --tasks "${NEW_TASK_ARN}" \
    --query 'tasks[0]' --output json)
if ! NEW_TASK_JSON="${NEW_TASK_JSON}" EXPECTED_TASK_DEFINITION="${TASK_FAMILY}:${NEW_REV}" \
    EXPECTED_IMAGE_DIGEST="${EXPECTED_IMAGE_DIGEST}" python3 -c '
import json, os
task = json.loads(os.environ["NEW_TASK_JSON"])
if task.get("lastStatus") != "RUNNING":
    raise SystemExit("new task is not RUNNING")
if not task.get("taskDefinitionArn", "").endswith("/" + os.environ["EXPECTED_TASK_DEFINITION"]):
    raise SystemExit("task-definition mismatch")
containers = task.get("containers", [])
if len(containers) != 1 or containers[0].get("imageDigest") != os.environ["EXPECTED_IMAGE_DIGEST"]:
    raise SystemExit("image-digest mismatch")
'; then
    echo "ERROR: new ECS owner does not match expected task definition and image digest"
    exit 1
fi

echo "[ready] Waiting for authenticated deep generation/build proof..."
READINESS_VERIFIED=0
EXPECTED_TASK_DEFINITION="${TASK_FAMILY}:${NEW_REV}"
for i in $(seq 1 90); do
    if READY_CALL=$(curl -sS "${CONTROL_CONNECT[@]}" \
        --connect-timeout 5 --max-time 20 -w "\n__HTTP__%{http_code}" \
        -H "X-API-Key: ${DEPLOY_API_KEY}" \
        -H "X-Deploy-Nonce: ${DEPLOY_NONCE}" \
        "${CONTROL_ORIGIN}/ready/guala"); then
        READY_HTTP=$(printf '%s\n' "${READY_CALL}" | awk -F__HTTP__ '/__HTTP__/{print $2}')
        READY_BODY=$(printf '%s\n' "${READY_CALL}" | awk '!/__HTTP__/')
        if [ "${READY_HTTP}" = "200" ] && printf '%s' "${READY_BODY}" | \
            GIT_SHA="${GIT_SHA}" SEALED_GENERATION="${SEALED_GENERATION}" \
            SEALED_IDENTITY="${SEALED_IDENTITY}" SEALED_MANIFEST="${SEALED_MANIFEST}" \
            EXPECTED_TASK_DEFINITION="${EXPECTED_TASK_DEFINITION}" \
            EXPECTED_IMAGE_DIGEST="${EXPECTED_IMAGE_DIGEST}" python3 -c '
import json, os, sys
value = json.load(sys.stdin)
checks = {
    "ready": value.get("ready") is True,
    "owner": value.get("owner") is True,
    "git_sha": value.get("git_sha") == os.environ["GIT_SHA"],
    "generation": value.get("generation") == os.environ["SEALED_GENERATION"],
    "identity": value.get("identity") == os.environ["SEALED_IDENTITY"],
    "manifest": value.get("manifest_sha256") == os.environ["SEALED_MANIFEST"],
    "task_definition": value.get("task_definition") == os.environ["EXPECTED_TASK_DEFINITION"],
    "image_digest": value.get("image_digest") == os.environ["EXPECTED_IMAGE_DIGEST"],
}
if not all(checks.values()):
    raise SystemExit("deep-readiness mismatch: " + ",".join(k for k, ok in checks.items() if not ok))
'; then
            READINESS_VERIFIED=1
            break
        fi
    fi
    echo "[ready] attempt ${i}/90: exact deep proof not yet available"
    sleep 10
done
if [ "${READINESS_VERIFIED}" != "1" ]; then
    echo "ERROR: new owner never proved exact build and sealed generation readiness"
    exit 1
fi

echo "[wake] Deep readiness verified; waking the new owner."
AWAKE_VERIFIED=0
for i in $(seq 1 12); do
    if WAKE_CALL=$(curl -sS "${CONTROL_CONNECT[@]}" \
        --connect-timeout 5 --max-time 30 -w "\n__HTTP__%{http_code}" -X POST \
        -H 'Content-Type: application/json' -H "X-API-Key: ${DEPLOY_API_KEY}" \
        -H "X-Deploy-Nonce: ${DEPLOY_NONCE}" \
        -d '{"text":"","command":"/wake"}' \
        "${CONTROL_ORIGIN}/api/v1/gualaloom"); then
        WAKE_HTTP=$(printf '%s\n' "${WAKE_CALL}" | awk -F__HTTP__ '/__HTTP__/{print $2}')
        if [ "${WAKE_HTTP}" = "200" ]; then
            if STATUS_CALL=$(curl -sS "${CONTROL_CONNECT[@]}" \
                --connect-timeout 5 --max-time 30 -w "\n__HTTP__%{http_code}" -X POST \
                -H 'Content-Type: application/json' -H "X-API-Key: ${DEPLOY_API_KEY}" \
                -H "X-Deploy-Nonce: ${DEPLOY_NONCE}" \
                -d '{"text":"","command":"/status"}' \
                "${CONTROL_ORIGIN}/api/v1/gualaloom"); then
                STATUS_HTTP=$(printf '%s\n' "${STATUS_CALL}" | awk -F__HTTP__ '/__HTTP__/{print $2}')
                STATUS_BODY=$(printf '%s\n' "${STATUS_CALL}" | awk '!/__HTTP__/')
                if [ "${STATUS_HTTP}" = "200" ] && printf '%s' "${STATUS_BODY}" | python3 -c '
import json, sys
value = json.load(sys.stdin)
if value.get("asleep") is not False:
    raise SystemExit(1)
'; then
                    AWAKE_VERIFIED=1
                    break
                fi
            fi
        fi
    fi
    echo "[wake] attempt ${i}/12: awake state not yet proven"
    sleep 10
done
if [ "${AWAKE_VERIFIED}" != "1" ]; then
    echo "ERROR: new owner did not prove awake state"
    exit 1
fi

FINAL_SERVICE_JSON=$(aws ecs describe-services --cluster "${ECS_CLUSTER}" \
    --services "${ECS_SERVICE}" --query 'services[0]' --output json)
if ! FINAL_SERVICE_JSON="${FINAL_SERVICE_JSON}" EXPECTED_TASK_DEFINITION="${EXPECTED_TASK_DEFINITION}" python3 -c '
import json, os
service = json.loads(os.environ["FINAL_SERVICE_JSON"])
config = service.get("deploymentConfiguration", {})
breaker = config.get("deploymentCircuitBreaker", {})
if config.get("maximumPercent") != 100 or config.get("minimumHealthyPercent") != 0:
    raise SystemExit("unsafe deployment percentages")
if breaker.get("enable") is not True or breaker.get("rollback") is not True:
    raise SystemExit("rollback circuit breaker is not armed")
if service.get("desiredCount") != 1 or service.get("runningCount") != 1:
    raise SystemExit("service does not have exactly one owner")
if not service.get("taskDefinition", "").endswith("/" + os.environ["EXPECTED_TASK_DEFINITION"]):
    raise SystemExit("service task definition mismatch")
'; then
    echo "ERROR: final service ownership/deployment configuration is not exact"
    exit 1
fi
OWNER_FAIL_CLOSED=0

# ── Step 8: Sync static files to S3 + CloudFront invalidation ──
echo ""
echo "[deploy] Syncing static files to S3 and invalidating CloudFront..."

CF_DIST_ID="E17JT9XGBFU493"
S3_SITE_BUCKET="dsf-ai-site"

aws s3 sync "${STAGING}/dsf_ai_service/static/" "s3://${S3_SITE_BUCKET}/" \
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
    --id "${INV_ID}"; then
    echo "[deploy] Static sync + CloudFront invalidation complete."
else
    echo "ERROR: CloudFront invalidation did not complete within the waiter timeout"
    exit 1
fi

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════"
echo "  Deploy complete"
echo "  Image:    ${IMAGE_URI}"
echo "  Task def: ${TASK_FAMILY}:${NEW_REV}"
echo "  Git SHA:  ${GIT_SHA}"
echo "  Static:   s3://${S3_SITE_BUCKET}/ from ${GIT_SHA} archive"
echo ""
echo "  dsf-ai.com should reflect changes within 1-2 minutes."
echo "═══════════════════════════════════════════"
