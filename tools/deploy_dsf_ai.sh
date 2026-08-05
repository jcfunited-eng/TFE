#!/usr/bin/env bash
# Deterministic Guala production deployment.
#
# One reviewed clean commit produces one immutable image digest and one exact
# ECS task definition.  The canonical preflight must pass before discarded-
# state rehearsal or cutover.  ECS replaces one process without an automatic
# old-image rollback.  This controller never creates an owner, lock, database,
# deployment seal, compatibility brain, or generation-store fallback.
#
# Usage: ./tools/deploy_dsf_ai.sh [--rehearse-only]

set -euo pipefail

AWS_REGION="us-east-1"
AWS_ACCOUNT="418384447921"
ECR_REPOSITORY="dsf-ai"
ECR_URI="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"
ECS_CLUSTER="tfe-web-cluster"
ECS_SERVICE="dsf-ai-service-lb"
TASK_FAMILY="dsf-ai-task"
CODEBUILD_PROJECT="dsf-ai-image-build"
SOURCE_BUCKET="tfe-codebuild-src-${AWS_ACCOUNT}-${AWS_REGION}"
SOURCE_KEY="deploy/dsf_ai_codebuild_src.zip"
CONTROL_ORIGIN="https://dsf-ai.com"
ALB_DNS="dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
CONTROL_SECRET_ID="gualaloom/api-key/prod"
RELEASE_MANIFEST="deploy/guala_release_manifest.json"
# Identity continuity: the genesis cutover keeps the organism identity minted
# at the 2026-07-16 genesis; the same pin authors the candidate task
# environment and the genesis rehearsal expectation.
GUALA_ORGANISM_IDENTITY="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
DEPLOY_CONFIGURATION="maximumPercent=100,minimumHealthyPercent=0,deploymentCircuitBreaker={enable=true,rollback=false}"
REPEAT_CUTOVER=1
REHEARSE_ONLY=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --rehearse-only)
            REHEARSE_ONLY=1
            shift
            ;;
        *)
            echo "ERROR: unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for command_name in aws curl git python3; do
    command -v "${command_name}" >/dev/null 2>&1 \
        || fail "required command is unavailable: ${command_name}"
done

REPOSITORY_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) \
    || fail "run this command inside the reviewed repository"
cd "${REPOSITORY_ROOT}"

GIT_SHA=$(git rev-parse --verify HEAD)
if [ -n "$(git status --porcelain=v1 --untracked-files=all)" ]; then
    fail "the reviewed release must be one clean Git commit"
fi

STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
IMAGE_TAG="deploy-$(date -u +"%Y%m%dT%H%M%SZ")"
TAGGED_IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"
WORK_DIR=$(mktemp -d -t guala-deploy.XXXXXXXX)
STAGE_DIR="${WORK_DIR}/stage"
ARCHIVE_PATH="${WORK_DIR}/guala-release.zip"

cleanup() {
    local exit_code=$?
    trap - EXIT INT TERM
    if [ -d "${WORK_DIR}" ]; then
        rm -r -- "${WORK_DIR}"
    fi
    exit "${exit_code}"
}
trap cleanup EXIT INT TERM

echo "[1/7] Resolving the exact settled Guala service."
SERVICE_JSON=$(aws ecs describe-services \
    --region "${AWS_REGION}" \
    --cluster "${ECS_CLUSTER}" \
    --services "${ECS_SERVICE}" \
    --query 'services[0]' \
    --output json)
SOURCE_TASK_DEFINITION=$(printf '%s' "${SERVICE_JSON}" | python3 -c '
import json, sys
service = json.load(sys.stdin)
if service.get("serviceName") != "dsf-ai-service-lb":
    raise SystemExit("resolved service is not Guala")
if service.get("status") != "ACTIVE":
    raise SystemExit("production service is not ACTIVE")
counts = {key: service.get(key) for key in ("desiredCount", "runningCount", "pendingCount")}
if counts != {"desiredCount": 1, "runningCount": 1, "pendingCount": 0}:
    raise SystemExit(f"production does not have exactly one settled process: {counts}")
deployments = service.get("deployments", [])
primary = [item for item in deployments if item.get("status") == "PRIMARY"]
if len(deployments) != 1 or len(primary) != 1 or primary[0].get("rolloutState") != "COMPLETED":
    raise SystemExit("production has overlapping or incomplete deployment authority")
task_definition = service.get("taskDefinition")
if not isinstance(task_definition, str) or "/dsf-ai-task:" not in task_definition:
    raise SystemExit("production has no exact Guala task definition")
print(task_definition)
')

RUNNING_TASKS=$(aws ecs list-tasks \
    --region "${AWS_REGION}" \
    --cluster "${ECS_CLUSTER}" \
    --service-name "${ECS_SERVICE}" \
    --desired-status RUNNING \
    --query 'taskArns' \
    --output text)
if [ "$(printf '%s\n' "${RUNNING_TASKS}" | wc -w)" -ne 1 ]; then
    fail "production must have exactly one running ECS task"
fi

echo "[2/7] Packaging the exact reviewed commit ${GIT_SHA}."
python3 tools/package_guala_release.py package \
    --source-root . \
    --manifest "${RELEASE_MANIFEST}" \
    --stage-dir "${STAGE_DIR}" \
    --zip-path "${ARCHIVE_PATH}" \
    >"${WORK_DIR}/package.json"
python3 tools/package_guala_release.py verify-context \
    --context "${STAGE_DIR}" \
    >"${WORK_DIR}/context.json"
python3 tools/package_guala_release.py verify-archive \
    --archive "${ARCHIVE_PATH}" \
    >"${WORK_DIR}/archive.json"
PACKAGED_GIT_SHA=$(python3 -c '
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["git_commit"])
' "${WORK_DIR}/context.json")
[ "${PACKAGED_GIT_SHA}" = "${GIT_SHA}" ] \
    || fail "packaged commit differs from reviewed HEAD"

echo "[3/7] Building one immutable production artifact."
aws s3 cp "${ARCHIVE_PATH}" "s3://${SOURCE_BUCKET}/${SOURCE_KEY}" \
    --region "${AWS_REGION}" --only-show-errors
BUILD_ID=$(aws codebuild start-build \
    --region "${AWS_REGION}" \
    --project-name "${CODEBUILD_PROJECT}" \
    --environment-variables-override \
        "name=IMAGE_URI,value=${TAGGED_IMAGE_URI},type=PLAINTEXT" \
        "name=GIT_SHA,value=${GIT_SHA},type=PLAINTEXT" \
    --query 'build.id' \
    --output text)
while true; do
    BUILD_JSON=$(aws codebuild batch-get-builds \
        --region "${AWS_REGION}" --ids "${BUILD_ID}" \
        --query 'builds[0].{status:buildStatus,phase:currentPhase}' \
        --output json)
    BUILD_STATUS=$(printf '%s' "${BUILD_JSON}" | python3 -c \
        'import json,sys; print(json.load(sys.stdin)["status"])')
    BUILD_PHASE=$(printf '%s' "${BUILD_JSON}" | python3 -c \
        'import json,sys; print(json.load(sys.stdin)["phase"])')
    case "${BUILD_STATUS}" in
        SUCCEEDED) break ;;
        FAILED|FAULT|STOPPED|TIMED_OUT)
            fail "CodeBuild ${BUILD_STATUS} during ${BUILD_PHASE}"
            ;;
        *) echo "      ${BUILD_STATUS}: ${BUILD_PHASE}"; sleep 10 ;;
    esac
done

IMAGE_DIGEST=$(aws ecr describe-images \
    --region "${AWS_REGION}" \
    --repository-name "${ECR_REPOSITORY}" \
    --image-ids "imageTag=${IMAGE_TAG}" \
    --query 'imageDetails[0].imageDigest' \
    --output text)
printf '%s' "${IMAGE_DIGEST}" | python3 -c '
import re, sys
value = sys.stdin.read()
if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
    raise SystemExit("built image has no immutable digest")
'
PINNED_IMAGE_URI="${ECR_URI}@${IMAGE_DIGEST}"

echo "[4/7] Registering one digest-pinned candidate task definition."
BASE_TASK_JSON=$(aws ecs describe-task-definition \
    --region "${AWS_REGION}" \
    --task-definition "${SOURCE_TASK_DEFINITION}" \
    --query taskDefinition \
    --output json)
REGISTER_JSON=$(printf '%s' "${BASE_TASK_JSON}" | \
    PINNED_IMAGE_URI="${PINNED_IMAGE_URI}" \
    IMAGE_DIGEST="${IMAGE_DIGEST}" GIT_SHA="${GIT_SHA}" \
    ORGANISM_IDENTITY="${GUALA_ORGANISM_IDENTITY}" \
    python3 -c '
import json, os, sys
source = json.load(sys.stdin)
allowed = (
    "family", "taskRoleArn", "executionRoleArn", "networkMode",
    "containerDefinitions", "volumes", "placementConstraints",
    "requiresCompatibilities", "cpu", "memory", "runtimePlatform",
    "ephemeralStorage", "pidMode", "ipcMode", "proxyConfiguration",
    "inferenceAccelerators",
)
target = {key: source[key] for key in allowed if key in source}
containers = target.get("containerDefinitions", [])
if len(containers) != 1 or containers[0].get("name") != "dsf-ai":
    raise SystemExit("task definition must contain one dsf-ai container")
container = containers[0]
container["image"] = os.environ["PINNED_IMAGE_URI"]
# The reviewed image entrypoint (native_production_app) is the single
# serving authority; a stale per-taskdef command override would boot a
# module that is not in the lean image and crash-loop the service.
container.pop("command", None)
environment = container.get("environment", [])
if len({item.get("name") for item in environment}) != len(environment):
    raise SystemExit("task environment contains duplicate authorities")
retired_names = {
    "FORCE_S3_RESTORE",
    "GUALA_EXACT_FIELD_EXECUTOR_REQUIRED",
    "GUALA_" + "GENERATION_STORE_ROOT",
    "GUALA_LIVE_RECOVERY_STORE_ROOT",
    "GUALA_" + "OWNER_LOCK_PATH",
    "GUALA_" + "REQUIRE_SEALED_STATE",
    "STATE_DIR",
}
environment = [
    item for item in environment if item.get("name") not in retired_names
]
values = {item.get("name"): item for item in environment}
# Ratified storage governance pins (operator decision 2026-07-28): the
# hard global write-refusal ceiling and the cold-generation protocol limit.
required_environment = {
    "GUALA_MAX_COLD_GENERATION_BYTES": "2147483648",
    "GUALA_PERSISTENT_STORAGE_CEILING_BYTES": "5368709120",
    # Identity continuity: rebirth keeps the organism identity minted at
    # the 2026-07-16 genesis rather than a new random one.
    "GUALA_NATIVE_ORGANISM_IDENTITY": os.environ["ORGANISM_IDENTITY"],
}
for name, value in (
    ("DEPLOY_EXPECTED_GIT_SHA", os.environ["GIT_SHA"]),
    ("DEPLOY_EXPECTED_IMAGE_DIGEST", os.environ["IMAGE_DIGEST"]),
    *sorted(required_environment.items()),
):
    if name in values:
        values[name]["value"] = value
    else:
        item = {"name": name, "value": value}
        environment.append(item)
        values[name] = item
container["environment"] = environment
print(json.dumps(target, separators=(",", ":")))
')
CANDIDATE_TASK_DEFINITION=$(aws ecs register-task-definition \
    --region "${AWS_REGION}" \
    --cli-input-json "${REGISTER_JSON}" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

CANDIDATE_JSON=$(aws ecs describe-task-definition \
    --region "${AWS_REGION}" \
    --task-definition "${CANDIDATE_TASK_DEFINITION}" \
    --query taskDefinition \
    --output json)
printf '%s' "${CANDIDATE_JSON}" | \
    PINNED_IMAGE_URI="${PINNED_IMAGE_URI}" \
    IMAGE_DIGEST="${IMAGE_DIGEST}" GIT_SHA="${GIT_SHA}" \
    python3 -c '
import json, os, re, sys
task = json.load(sys.stdin)
containers = task.get("containerDefinitions", [])
if len(containers) != 1 or containers[0].get("name") != "dsf-ai":
    raise SystemExit("registered candidate has more than one runtime container")
container = containers[0]
if container.get("image") != os.environ["PINNED_IMAGE_URI"]:
    raise SystemExit("registered image is not the immutable built artifact")
environment = {
    item.get("name"): item.get("value")
    for item in container.get("environment", [])
}
if environment.get("DEPLOY_EXPECTED_IMAGE_DIGEST") != os.environ["IMAGE_DIGEST"]:
    raise SystemExit("registered digest differs from built artifact")
if environment.get("DEPLOY_EXPECTED_GIT_SHA") != os.environ["GIT_SHA"]:
    raise SystemExit("registered commit differs from reviewed commit")
retired = {
    "FORCE_S3_RESTORE",
    "GUALA_EXACT_FIELD_EXECUTOR_REQUIRED",
    "GUALA_" + "GENERATION_STORE_ROOT",
    "GUALA_LIVE_RECOVERY_STORE_ROOT",
    "GUALA_" + "OWNER_LOCK_PATH",
    "GUALA_" + "REQUIRE_SEALED_STATE",
    "STATE_DIR",
}
present = sorted(retired.intersection(environment))
if present:
    raise SystemExit(f"candidate retains legacy authority environment: {present}")
for name in environment:
    if re.search(r"(?:^|_)(?:DATABASE|DB|MONGO|MYSQL|POSTGRES|REDIS|SQLALCHEMY)(?:_|$)", name, re.I):
        raise SystemExit(f"candidate contains database environment: {name}")
for field in ("cpu", "memory"):
    value = task.get(field)
    if not isinstance(value, str) or not value.isdigit() or int(value) <= 0:
        raise SystemExit(f"candidate {field} envelope is invalid")
mounts = container.get("mountPoints", [])
if mounts != [{
    "sourceVolume": "gualaloom-state",
    "containerPath": "/app/guala",
    "readOnly": False,
}]:
    raise SystemExit("candidate persistent mount differs")
volumes = task.get("volumes", [])
if len(volumes) != 1 or volumes[0].get("name") != "gualaloom-state":
    raise SystemExit("candidate has more than one persistent state volume")
efs = volumes[0].get("efsVolumeConfiguration", {})
if efs.get("transitEncryption") != "ENABLED":
    raise SystemExit("candidate persistent transport is not encrypted")
'

CONTROL_SECRET_ARN=$(aws secretsmanager describe-secret \
    --region "${AWS_REGION}" \
    --secret-id "${CONTROL_SECRET_ID}" \
    --query ARN --output text)
DEPLOY_API_KEY=$(aws secretsmanager get-secret-value \
    --region "${AWS_REGION}" \
    --secret-id "${CONTROL_SECRET_ARN}" \
    --query SecretString --output text)
[ -n "${DEPLOY_API_KEY}" ] && [ "${DEPLOY_API_KEY}" != "None" ] \
    || fail "production control credential is unavailable"

# This deployment is an explicit genesis cutover: the candidate serves the
# lean native surface, uses a NEW state root, performs identity-pinned fresh
# genesis, and inherits no predecessor cognitive state.
python3 tools/preflight_guala_production.py \
    --root "${REPOSITORY_ROOT}" \
    --expected-commit "${GIT_SHA}" \
    --candidate-task-definition "${CANDIDATE_TASK_DEFINITION}" \
    --candidate-image-digest "${IMAGE_DIGEST}" \
    --genesis-cutover \
    >"${WORK_DIR}/preflight.json"

verify_live_organism() {
    local expected_task_definition="$1"
    local expected_task_name="${expected_task_definition##*/}"
    local task_arns task_json ready_nonce ready_body service_json

    service_json=$(aws ecs describe-services \
        --region "${AWS_REGION}" \
        --cluster "${ECS_CLUSTER}" \
        --services "${ECS_SERVICE}" \
        --query 'services[0]' --output json)
    printf '%s' "${service_json}" | EXPECTED="${expected_task_definition}" python3 -c '
import json, os, sys
service = json.load(sys.stdin)
counts = {key: service.get(key) for key in ("desiredCount", "runningCount", "pendingCount")}
if counts != {"desiredCount": 1, "runningCount": 1, "pendingCount": 0}:
    raise SystemExit(f"service is not settled on one process: {counts}")
deployments = service.get("deployments", [])
if len(deployments) != 1 or deployments[0].get("status") != "PRIMARY":
    raise SystemExit("service retains overlapping deployment authority")
if service.get("taskDefinition") != os.environ["EXPECTED"]:
    raise SystemExit("service task definition differs from candidate")
'
    task_arns=$(aws ecs list-tasks \
        --region "${AWS_REGION}" \
        --cluster "${ECS_CLUSTER}" \
        --service-name "${ECS_SERVICE}" \
        --desired-status RUNNING \
        --query 'taskArns' --output text)
    if [ "$(printf '%s\n' "${task_arns}" | wc -w)" -ne 1 ]; then
        fail "cutover did not produce exactly one running process"
    fi
    task_json=$(aws ecs describe-tasks \
        --region "${AWS_REGION}" \
        --cluster "${ECS_CLUSTER}" \
        --tasks "${task_arns}" \
        --query 'tasks[0]' --output json)
    printf '%s' "${task_json}" | \
        EXPECTED_TASK="${expected_task_definition}" \
        EXPECTED_DIGEST="${IMAGE_DIGEST}" python3 -c '
import json, os, sys
task = json.load(sys.stdin)
containers = task.get("containers", [])
if task.get("lastStatus") != "RUNNING" or task.get("healthStatus") != "HEALTHY":
    raise SystemExit("candidate task is not running and healthy")
if task.get("taskDefinitionArn") != os.environ["EXPECTED_TASK"]:
    raise SystemExit("running task definition differs from candidate")
if len(containers) != 1 or containers[0].get("imageDigest") != os.environ["EXPECTED_DIGEST"]:
    raise SystemExit("running image digest differs from built artifact")
'
    curl -fsS \
        --connect-to "dsf-ai.com:443:${ALB_DNS}:443" \
        --connect-timeout 10 --max-time 30 \
        "${CONTROL_ORIGIN}/health" \
        | python3 -c \
            'import json,sys; value=json.load(sys.stdin); assert value.get("status") == "ok"'
    ready_nonce=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    ready_body=$(curl -fsS \
        --connect-to "dsf-ai.com:443:${ALB_DNS}:443" \
        --connect-timeout 10 --max-time 30 \
        -H "X-API-Key: ${DEPLOY_API_KEY}" \
        -H "X-Deploy-Nonce: ${ready_nonce}" \
        "${CONTROL_ORIGIN}/ready/guala")
    printf '%s' "${ready_body}" | \
        EXPECTED_TASK="${expected_task_name}" \
        EXPECTED_DIGEST="${IMAGE_DIGEST}" EXPECTED_SHA="${GIT_SHA}" \
        python3 -c '
import json, os, re, sys
value = json.load(sys.stdin)
if value.get("ready") is not True or value.get("native_state") is not True:
    raise SystemExit("organism did not prove ready native state")
if value.get("task_definition") != os.environ["EXPECTED_TASK"]:
    raise SystemExit("organism reports a different task definition")
if value.get("image_digest") != os.environ["EXPECTED_DIGEST"]:
    raise SystemExit("organism reports a different image digest")
if value.get("git_sha") != os.environ["EXPECTED_SHA"]:
    raise SystemExit("organism reports a different reviewed commit")
if value.get("ready_scope") != "http_and_native_current_transport_only":
    raise SystemExit("readiness scope is not transport-only")
native = value.get("native_resident", {})
if native.get("available") is not True:
    raise SystemExit("native resident observation is unavailable")
if native.get("python_callback_count") != 0:
    raise SystemExit("native resident reports Python cognition callbacks")
state_sha = native.get("state_sha256")
if not isinstance(state_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", state_sha):
    raise SystemExit("native resident state identity is absent")
state_bytes = native.get("state_bytes")
if not isinstance(state_bytes, int) or state_bytes <= 0:
    raise SystemExit("native resident state byte count is invalid")
if native.get("persistence_schema") not in {
    "guala.native_organism_binary_store.v1",
}:
    raise SystemExit("native resident persistence schema changed")
if (
    native.get("complete_neuron_available") is not False
    or native.get("genuine_neuronal_fractal_available") is not False
    or native.get("cognition_available") is not False
):
    raise SystemExit("candidate made an unavailable cognition claim")
'
    printf '%s' "${task_arns}"
}

inspect_live_rehearsal_source() {
    local expected_task_definition="$1"
    local expected_task_name="${expected_task_definition##*/}"
    local ready_nonce ready_body
    ready_nonce=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    ready_body=$(curl -fsS \
        --connect-to "dsf-ai.com:443:${ALB_DNS}:443" \
        --connect-timeout 10 --max-time 30 \
        -H "X-API-Key: ${DEPLOY_API_KEY}" \
        -H "X-Deploy-Nonce: ${ready_nonce}" \
        "${CONTROL_ORIGIN}/ready/guala")
    printf '%s' "${ready_body}" | EXPECTED_TASK="${expected_task_name}" python3 -c '
import json, os, re, sys
value = json.load(sys.stdin)
if value.get("ready") is not True or value.get("native_state") is not True:
    raise SystemExit("running organism is not ready for candidate rehearsal")
if value.get("task_definition") != os.environ["EXPECTED_TASK"]:
    raise SystemExit("rehearsal source reports a different task definition")
for field in ("generation", "active_recovery_generation", "identity"):
    if not re.fullmatch(r"[0-9a-f-]{36}", str(value.get(field, ""))):
        raise SystemExit(f"rehearsal source {field} is absent")
tick = value.get("active_recovery_tick")
if not isinstance(tick, int) or tick < 0:
    raise SystemExit("rehearsal source tick is invalid")
native = value.get("native_joint_fractal", {})
if native.get("available") is not True or native.get("python_callback_count") != 0:
    raise SystemExit("rehearsal source is not the native resident organism")
print(json.dumps(value, separators=(",", ":"), sort_keys=True))
'
}

if [ "${REHEARSE_ONLY}" = "1" ]; then
    echo "[5/7] Rehearsing the digest-pinned candidate without cutover."
else
    echo "[5/7] Rehearsing the digest-pinned candidate before fail-closed cutover."
fi
PREVIOUS_RUNNING_TASK="${RUNNING_TASKS}"
for cutover_number in $(seq 1 "${REPEAT_CUTOVER}"); do
    # Genesis cutover rehearsal: the live legacy surface is not a rehearsal
    # source (its facts are already recorded by the preflight), so the
    # inheritance inspection is skipped.  The candidate proves identity-pinned
    # fresh genesis and one genuinely retained lesson on a throwaway state
    # root instead of round-tripping predecessor state.
    REHEARSAL_PROOF=$(python3 tools/run_guala_candidate_rehearsal_task.py \
        --mode genesis-rehearse \
        --cluster "${ECS_CLUSTER}" \
        --service "${ECS_SERVICE}" \
        --candidate-task-definition "${CANDIDATE_TASK_DEFINITION}" \
        --candidate-git-sha "${GIT_SHA}" \
        --candidate-image-digest "${IMAGE_DIGEST}" \
        --expected-identity "${GUALA_ORGANISM_IDENTITY}")
    printf '%s\n' "${REHEARSAL_PROOF}"
    if [ "${REHEARSE_ONLY}" = "1" ]; then
        GIT_SHA="${GIT_SHA}" IMAGE_DIGEST="${IMAGE_DIGEST}" \
        CANDIDATE_TASK_DEFINITION="${CANDIDATE_TASK_DEFINITION}" \
        REHEARSAL_PROOF="${REHEARSAL_PROOF}" python3 -c '
import json, os
proof = json.loads(os.environ["REHEARSAL_PROOF"])
print(json.dumps({
    "candidate_git_sha": os.environ["GIT_SHA"],
    "candidate_image_digest": os.environ["IMAGE_DIGEST"],
    "candidate_task_definition": os.environ["CANDIDATE_TASK_DEFINITION"],
    "rehearsal_proof": proof,
    "schema": "guala.prepared_candidate.v2",
    "status": "rehearsed_not_deployed",
}, separators=(",", ":"), sort_keys=True))
'
        exit 0
    fi
    # Genesis cutover: there is no predecessor publication or cold-restore of
    # inherited state; the candidate performs its own identity-pinned genesis
    # on its fresh state root at first boot.
    aws ecs update-service \
        --region "${AWS_REGION}" \
        --cluster "${ECS_CLUSTER}" \
        --service "${ECS_SERVICE}" \
        --task-definition "${CANDIDATE_TASK_DEFINITION}" \
        --desired-count 1 \
        --deployment-configuration "${DEPLOY_CONFIGURATION}" \
        --force-new-deployment >/dev/null
    aws ecs wait services-stable \
        --region "${AWS_REGION}" \
        --cluster "${ECS_CLUSTER}" \
        --services "${ECS_SERVICE}"
    CURRENT_RUNNING_TASK=$(verify_live_organism \
        "${CANDIDATE_TASK_DEFINITION}")
    if [ "${CURRENT_RUNNING_TASK}" = "${PREVIOUS_RUNNING_TASK}" ]; then
        fail "cutover ${cutover_number} did not replace the running process"
    fi
    PREVIOUS_RUNNING_TASK="${CURRENT_RUNNING_TASK}"
    echo "      cutover ${cutover_number}/${REPEAT_CUTOVER}: verified"
done

echo "[6/7] Pinning only the live-verified artifact as production-current."
IMAGE_MANIFEST=$(aws ecr batch-get-image \
    --region "${AWS_REGION}" \
    --repository-name "${ECR_REPOSITORY}" \
    --image-ids "imageDigest=${IMAGE_DIGEST}" \
    --query 'images[0].imageManifest' --output text)
[ -n "${IMAGE_MANIFEST}" ] && [ "${IMAGE_MANIFEST}" != "None" ] \
    || fail "verified artifact disappeared from ECR"
aws ecr put-image \
    --region "${AWS_REGION}" \
    --repository-name "${ECR_REPOSITORY}" \
    --image-tag production-current \
    --image-manifest "${IMAGE_MANIFEST}" >/dev/null
PINNED_DIGEST=$(aws ecr describe-images \
    --region "${AWS_REGION}" \
    --repository-name "${ECR_REPOSITORY}" \
    --image-ids imageTag=production-current \
    --query 'imageDetails[0].imageDigest' --output text)
[ "${PINNED_DIGEST}" = "${IMAGE_DIGEST}" ] \
    || fail "production-current does not identify the verified artifact"

FINISHED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "[7/7] Deployment complete."
STARTED_AT="${STARTED_AT}" FINISHED_AT="${FINISHED_AT}" \
GIT_SHA="${GIT_SHA}" \
CANDIDATE_TASK_DEFINITION="${CANDIDATE_TASK_DEFINITION}" \
IMAGE_DIGEST="${IMAGE_DIGEST}" REPEAT_CUTOVER="${REPEAT_CUTOVER}" \
python3 -c '
import json, os
print(json.dumps({
    "schema": "guala.deterministic_deployment.v2",
    "status": "deployed",
    "started_at": os.environ["STARTED_AT"],
    "finished_at": os.environ["FINISHED_AT"],
    "git_sha": os.environ["GIT_SHA"],
    "task_definition": os.environ["CANDIDATE_TASK_DEFINITION"],
    "image_digest": os.environ["IMAGE_DIGEST"],
    "cutovers_verified": int(os.environ["REPEAT_CUTOVER"]),
    "verified_native_state": True,
    "automatic_legacy_rollback": False,
}, sort_keys=True))
'
