#!/usr/bin/env bash
# One continuity-only deployment path for the lean five-route Guala runtime.
# It never starts a rehearsal organism, migration shell, or legacy rollback.

set -euo pipefail

AWS_REGION="us-east-1"
AWS_ACCOUNT="418384447921"
ECR_REPOSITORY="dsf-ai"
ECR_URI="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"
ECS_CLUSTER="tfe-web-cluster"
ECS_SERVICE="dsf-ai-service-lb"
CODEBUILD_PROJECT="dsf-ai-image-build"
SOURCE_BUCKET="tfe-codebuild-src-${AWS_ACCOUNT}-${AWS_REGION}"
SOURCE_KEY="deploy/dsf_ai_codebuild_src.zip"
CONTROL_ORIGIN="https://dsf-ai.com"
ALB_DNS="dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
RELEASE_MANIFEST="deploy/guala_release_manifest.json"
EXPECTED_IDENTITY="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
DEPLOY_CONFIGURATION="maximumPercent=200,minimumHealthyPercent=0,deploymentCircuitBreaker={enable=true,rollback=false}"
SERVICE_WAIT_SECONDS="${SERVICE_WAIT_SECONDS:-2400}"
HTTP_WAIT_SECONDS="${HTTP_WAIT_SECONDS:-600}"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

if [ "$#" -ne 0 ]; then
    printf '%s\n' "Usage: ./tools/deploy_dsf_ai.sh" >&2
    printf 'ERROR: unknown argument: %s\n' "$1" >&2
    exit 2
fi
case "${SERVICE_WAIT_SECONDS}" in
    ''|*[!0-9]*) fail "service wait must be a positive integer" ;;
esac
case "${HTTP_WAIT_SECONDS}" in
    ''|*[!0-9]*) fail "HTTP wait must be a positive integer" ;;
esac
[ "${SERVICE_WAIT_SECONDS}" -gt 0 ] || fail "service wait must be positive"
[ "${HTTP_WAIT_SECONDS}" -gt 0 ] || fail "HTTP wait must be positive"
for command_name in aws curl date git python3; do
    command -v "${command_name}" >/dev/null 2>&1 \
        || fail "required command is unavailable: ${command_name}"
done

REPOSITORY_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) \
    || fail "run this command inside the reviewed repository"
cd "${REPOSITORY_ROOT}"
GIT_SHA=$(git rev-parse --verify HEAD)
[ -z "$(git status --porcelain=v1 --untracked-files=all)" ] \
    || fail "the reviewed release must be one clean Git commit"

STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
IMAGE_TAG="deploy-$(date -u +"%Y%m%dT%H%M%SZ")"
TAGGED_IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"
WORK_DIR=$(mktemp -d -t guala-lean-deploy.XXXXXXXX)
STAGE_DIR="${WORK_DIR}/stage"
ARCHIVE_PATH="${WORK_DIR}/guala-release.zip"
CUTOVER_ARMED=0

cleanup() {
    local exit_code=$?
    trap - EXIT INT TERM
    if [ "${exit_code}" -ne 0 ] && [ "${CUTOVER_ARMED}" = "1" ]; then
        printf '%s\n' "candidate failed after drain; leaving zero writers" >&2
        aws ecs update-service \
            --region "${AWS_REGION}" \
            --cluster "${ECS_CLUSTER}" \
            --service "${ECS_SERVICE}" \
            --desired-count 0 \
            --deployment-configuration "${DEPLOY_CONFIGURATION}" \
            >/dev/null 2>&1 || true
    fi
    if [ -d "${WORK_DIR}" ]; then
        rm -r -- "${WORK_DIR}"
    fi
    exit "${exit_code}"
}
trap cleanup EXIT INT TERM

service_json() {
    aws ecs describe-services \
        --region "${AWS_REGION}" \
        --cluster "${ECS_CLUSTER}" \
        --services "${ECS_SERVICE}" \
        --query 'services[0]' \
        --output json
}

running_tasks() {
    aws ecs list-tasks \
        --region "${AWS_REGION}" \
        --cluster "${ECS_CLUSTER}" \
        --service-name "${ECS_SERVICE}" \
        --desired-status RUNNING \
        --query 'taskArns' \
        --output text
}

wait_for_selected_service() {
    local expected_task_definition="$1"
    local expected_desired="$2"
    local deadline value
    deadline=$(($(date +%s) + SERVICE_WAIT_SECONDS))
    while true; do
        value=$(service_json)
        if printf '%s' "${value}" | \
            EXPECTED_TASK="${expected_task_definition}" \
            EXPECTED_DESIRED="${expected_desired}" python3 -c '
import json, os, sys
service = json.load(sys.stdin)
desired = int(os.environ["EXPECTED_DESIRED"])
counts = {
    "desiredCount": service.get("desiredCount"),
    "runningCount": service.get("runningCount"),
    "pendingCount": service.get("pendingCount"),
}
if service.get("status") != "ACTIVE":
    raise SystemExit(1)
if service.get("taskDefinition") != os.environ["EXPECTED_TASK"]:
    raise SystemExit(1)
if counts != {"desiredCount": desired, "runningCount": desired, "pendingCount": 0}:
    raise SystemExit(1)
deployments = service.get("deployments", [])
if (
    len(deployments) != 1
    or deployments[0].get("status") != "PRIMARY"
    or deployments[0].get("rolloutState") != "COMPLETED"
):
    raise SystemExit(1)
'; then
            return 0
        fi
        [ "$(date +%s)" -lt "${deadline}" ] \
            || fail "service did not settle on the selected task definition"
        sleep 5
    done
}

read_observation() {
    curl -fsS \
        --connect-to "dsf-ai.com:443:${ALB_DNS}:443" \
        --connect-timeout 10 \
        --max-time 30 \
        "${CONTROL_ORIGIN}/api/v1/guala/observation"
}

validate_observation() {
    local minimum_tick="${1:-}"
    EXPECTED_IDENTITY="${EXPECTED_IDENTITY}" \
    MINIMUM_TICK="${minimum_tick}" python3 -c '
import json, os, re, sys
value = json.load(sys.stdin)
if value.get("schema") != "guala.lean_actor_observation.v1":
    raise SystemExit("observation is not the lean actor schema")
if value.get("available") is not True:
    raise SystemExit("native actor is unavailable")
if value.get("identity") != os.environ["EXPECTED_IDENTITY"]:
    raise SystemExit("organism identity changed")
if value.get("checkpoint_error") is not None or value.get("cleanup_error") is not None:
    raise SystemExit("durable custody has failed")
live_tick = value.get("live_tick")
persisted_tick = value.get("persisted_tick")
if (
    isinstance(live_tick, bool)
    or not isinstance(live_tick, int)
    or isinstance(persisted_tick, bool)
    or not isinstance(persisted_tick, int)
    or persisted_tick < 0
    or live_tick < persisted_tick
):
    raise SystemExit("native clock or custody clock is invalid")
minimum = os.environ.get("MINIMUM_TICK", "")
if minimum and live_tick < int(minimum):
    raise SystemExit("candidate restored behind its predecessor")
for name in ("persisted_body_sha256", "persisted_world_sha256"):
    if re.fullmatch(r"[0-9a-f]{64}", value.get(name, "")) is None:
        raise SystemExit(f"{name} is absent")
print(live_tick)
'
}

wait_for_lean_http() {
    local deadline observation tick
    deadline=$(($(date +%s) + HTTP_WAIT_SECONDS))
    while true; do
        if curl -fsS \
            --connect-to "dsf-ai.com:443:${ALB_DNS}:443" \
            --connect-timeout 10 --max-time 30 \
            "${CONTROL_ORIGIN}/health" \
            | python3 -c '
import json, sys
if json.load(sys.stdin) != {"alive": True, "schema": "guala.lean_health.v1"}:
    raise SystemExit(1)
' >/dev/null 2>&1 \
        && curl -fsS \
            --connect-to "dsf-ai.com:443:${ALB_DNS}:443" \
            --connect-timeout 10 --max-time 30 \
            "${CONTROL_ORIGIN}/ready" \
            | python3 -c '
import json, sys
if json.load(sys.stdin) != {"ready": True}:
    raise SystemExit(1)
' >/dev/null 2>&1; then
            observation=$(read_observation) || observation=""
            if tick=$(printf '%s' "${observation}" \
                | validate_observation "${CUTOVER_TICK}"); then
                printf '%s\n' "${tick}"
                return 0
            fi
        fi
        [ "$(date +%s)" -lt "${deadline}" ] \
            || fail "candidate never exposed one ready lean native actor"
        sleep 3
    done
}

echo "[1/7] Resolving one exact live predecessor."
SOURCE_SERVICE_JSON=$(service_json)
SOURCE_TASK_DEFINITION=$(printf '%s' "${SOURCE_SERVICE_JSON}" | python3 -c '
import json, sys
service = json.load(sys.stdin)
counts = {key: service.get(key) for key in ("desiredCount", "runningCount", "pendingCount")}
if service.get("status") != "ACTIVE":
    raise SystemExit("production service is not active")
if counts != {"desiredCount": 1, "runningCount": 1, "pendingCount": 0}:
    raise SystemExit(f"production does not have one settled writer: {counts}")
deployments = service.get("deployments", [])
if (
    len(deployments) != 1
    or deployments[0].get("status") != "PRIMARY"
    or deployments[0].get("rolloutState") != "COMPLETED"
):
    raise SystemExit("production deployment authority is not singular")
task = service.get("taskDefinition")
if not isinstance(task, str) or "/dsf-ai-task:" not in task:
    raise SystemExit("production task definition is invalid")
print(task)
')
SOURCE_RUNNING_TASKS=$(running_tasks)
[ "$(printf '%s\n' "${SOURCE_RUNNING_TASKS}" | wc -w)" -eq 1 ] \
    || fail "production running-task identity is not singular"
SOURCE_RUNNING_TASK="${SOURCE_RUNNING_TASKS}"
PREDECESSOR_BODY=$(read_observation) \
    || fail "the living predecessor observation is unavailable"
PREDECESSOR_TICK=$(printf '%s' "${PREDECESSOR_BODY}" | validate_observation)

echo "[2/7] Packaging reviewed commit ${GIT_SHA}."
python3 tools/package_guala_release.py package \
    --source-root . \
    --manifest "${RELEASE_MANIFEST}" \
    --stage-dir "${STAGE_DIR}" \
    --zip-path "${ARCHIVE_PATH}" \
    >"${WORK_DIR}/package.json"
python3 tools/package_guala_release.py verify-context \
    --context "${STAGE_DIR}" >"${WORK_DIR}/context.json"
python3 tools/package_guala_release.py verify-archive \
    --archive "${ARCHIVE_PATH}" >"${WORK_DIR}/archive.json"
PACKAGED_GIT_SHA=$(python3 -c '
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["git_commit"])
' "${WORK_DIR}/context.json")
[ "${PACKAGED_GIT_SHA}" = "${GIT_SHA}" ] \
    || fail "packaged commit differs from reviewed HEAD"

echo "[3/7] Building one immutable lean image."
aws s3 cp "${ARCHIVE_PATH}" "s3://${SOURCE_BUCKET}/${SOURCE_KEY}" \
    --region "${AWS_REGION}" --only-show-errors
BUILD_ID=$(aws codebuild start-build \
    --region "${AWS_REGION}" \
    --project-name "${CODEBUILD_PROJECT}" \
    --environment-variables-override \
        "name=IMAGE_URI,value=${TAGGED_IMAGE_URI},type=PLAINTEXT" \
        "name=GIT_SHA,value=${GIT_SHA},type=PLAINTEXT" \
    --query 'build.id' --output text)
while true; do
    BUILD_STATUS=$(aws codebuild batch-get-builds \
        --region "${AWS_REGION}" --ids "${BUILD_ID}" \
        --query 'builds[0].buildStatus' --output text)
    case "${BUILD_STATUS}" in
        SUCCEEDED) break ;;
        FAILED|FAULT|STOPPED|TIMED_OUT) fail "CodeBuild ended ${BUILD_STATUS}" ;;
        *) printf '      CodeBuild: %s\n' "${BUILD_STATUS}"; sleep 10 ;;
    esac
done
IMAGE_DIGEST=$(aws ecr describe-images \
    --region "${AWS_REGION}" --repository-name "${ECR_REPOSITORY}" \
    --image-ids "imageTag=${IMAGE_TAG}" \
    --query 'imageDetails[0].imageDigest' --output text)
printf '%s' "${IMAGE_DIGEST}" | python3 -c '
import re, sys
if re.fullmatch(r"sha256:[0-9a-f]{64}", sys.stdin.read()) is None:
    raise SystemExit("built image has no immutable digest")
'
PINNED_IMAGE_URI="${ECR_URI}@${IMAGE_DIGEST}"
IMAGE_MANIFEST=""
for manifest_attempt in $(seq 1 30); do
    IMAGE_MANIFEST=$(aws ecr batch-get-image \
        --region "${AWS_REGION}" --repository-name "${ECR_REPOSITORY}" \
        --image-ids "imageDigest=${IMAGE_DIGEST}" \
        --query 'images[0].imageManifest' --output text)
    if [ -n "${IMAGE_MANIFEST}" ] && [ "${IMAGE_MANIFEST}" != "None" ]; then
        printf '%s' "${IMAGE_MANIFEST}" | python3 -c '
import json, sys
if not json.load(sys.stdin).get("schemaVersion"):
    raise SystemExit("registry manifest is invalid")
'
        break
    fi
    [ "${manifest_attempt}" -lt 30 ] \
        || fail "built digest did not become pullable from ECR"
    sleep 2
done

echo "[4/7] Registering the digest with only lean runtime settings."
BASE_TASK_JSON=$(aws ecs describe-task-definition \
    --region "${AWS_REGION}" --task-definition "${SOURCE_TASK_DEFINITION}" \
    --query taskDefinition --output json)
REGISTER_JSON=$(printf '%s' "${BASE_TASK_JSON}" \
    | PINNED_IMAGE_URI="${PINNED_IMAGE_URI}" python3 -c '
import json, os, pathlib, sys
source = json.load(sys.stdin)
allowed = (
    "family", "taskRoleArn", "executionRoleArn", "networkMode",
    "containerDefinitions", "volumes", "placementConstraints",
    "requiresCompatibilities", "cpu", "memory", "runtimePlatform",
    "ephemeralStorage", "pidMode", "ipcMode", "proxyConfiguration",
    "inferenceAccelerators",
)
target = {name: source[name] for name in allowed if name in source}
containers = target.get("containerDefinitions", [])
if len(containers) != 1 or containers[0].get("name") != "dsf-ai":
    raise SystemExit("task definition is not one dsf-ai container")
container = containers[0]
values = {item.get("name"): item.get("value") for item in container.get("environment", [])}
root = values.get("GUALA_PAIRED_ROOT")
if (
    not isinstance(root, str)
    or not root.startswith("/app/guala/")
    or ".." in pathlib.PurePosixPath(root).parts
):
    raise SystemExit("live paired CURRENT root is not on the persistent mount")
world_bytes = values.get("GUALA_MAX_WORLD_BYTES")
if not isinstance(world_bytes, str) or not world_bytes.isdigit() or int(world_bytes) <= 0:
    raise SystemExit("live world byte boundary is invalid")
container["image"] = os.environ["PINNED_IMAGE_URI"]
container.pop("command", None)
container["environment"] = [
    {"name": "GUALA_PAIRED_ROOT", "value": root},
    {"name": "GUALA_MAX_WORLD_BYTES", "value": world_bytes},
    {"name": "PYTHONUNBUFFERED", "value": "1"},
]
print(json.dumps(target, separators=(",", ":")))
')
CANDIDATE_TASK_DEFINITION=$(aws ecs register-task-definition \
    --region "${AWS_REGION}" --cli-input-json "${REGISTER_JSON}" \
    --query 'taskDefinition.taskDefinitionArn' --output text)
CANDIDATE_JSON=$(aws ecs describe-task-definition \
    --region "${AWS_REGION}" --task-definition "${CANDIDATE_TASK_DEFINITION}" \
    --query taskDefinition --output json)
printf '%s' "${CANDIDATE_JSON}" \
    | PINNED_IMAGE_URI="${PINNED_IMAGE_URI}" python3 -c '
import json, os, sys
task = json.load(sys.stdin)
containers = task.get("containerDefinitions", [])
if len(containers) != 1 or containers[0].get("name") != "dsf-ai":
    raise SystemExit("candidate has more than one runtime container")
container = containers[0]
if container.get("image") != os.environ["PINNED_IMAGE_URI"]:
    raise SystemExit("candidate image is not the immutable built digest")
if container.get("command") is not None:
    raise SystemExit("candidate overrides the reviewed lean entrypoint")
environment = {item.get("name"): item.get("value") for item in container.get("environment", [])}
if set(environment) != {"GUALA_PAIRED_ROOT", "GUALA_MAX_WORLD_BYTES", "PYTHONUNBUFFERED"}:
    raise SystemExit("candidate contains non-lean runtime environment")
if container.get("mountPoints") != [{
    "sourceVolume": "gualaloom-state",
    "containerPath": "/app/guala",
    "readOnly": False,
}]:
    raise SystemExit("candidate persistent mount changed")
volumes = task.get("volumes", [])
if len(volumes) != 1 or volumes[0].get("name") != "gualaloom-state":
    raise SystemExit("candidate persistent volume changed")
if volumes[0].get("efsVolumeConfiguration", {}).get("transitEncryption") != "ENABLED":
    raise SystemExit("candidate persistent transport is not encrypted")
for field in ("cpu", "memory"):
    value = task.get(field)
    if not isinstance(value, str) or not value.isdigit() or int(value) <= 0:
        raise SystemExit(f"candidate {field} boundary is invalid")
'

echo "[5/7] Draining the predecessor and starting exactly one candidate."
CURRENT_TASK_DEFINITION=$(service_json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("taskDefinition", ""))')
[ "${CURRENT_TASK_DEFINITION}" = "${SOURCE_TASK_DEFINITION}" ] \
    || fail "production task definition changed during the build"
CURRENT_RUNNING_TASKS=$(running_tasks)
[ "${CURRENT_RUNNING_TASKS}" = "${SOURCE_RUNNING_TASK}" ] \
    || fail "production writer changed during the build"
CUTOVER_BODY=$(read_observation) \
    || fail "the predecessor disappeared before cutover"
CUTOVER_TICK=$(printf '%s' "${CUTOVER_BODY}" | validate_observation)
CUTOVER_ARMED=1
aws ecs update-service \
    --region "${AWS_REGION}" --cluster "${ECS_CLUSTER}" \
    --service "${ECS_SERVICE}" --desired-count 0 \
    --deployment-configuration "${DEPLOY_CONFIGURATION}" >/dev/null
aws ecs wait tasks-stopped \
    --region "${AWS_REGION}" --cluster "${ECS_CLUSTER}" \
    --tasks "${SOURCE_RUNNING_TASK}"
aws ecs update-service \
    --region "${AWS_REGION}" --cluster "${ECS_CLUSTER}" \
    --service "${ECS_SERVICE}" \
    --task-definition "${CANDIDATE_TASK_DEFINITION}" \
    --desired-count 0 \
    --deployment-configuration "${DEPLOY_CONFIGURATION}" >/dev/null
wait_for_selected_service "${CANDIDATE_TASK_DEFINITION}" 0
aws ecs update-service \
    --region "${AWS_REGION}" --cluster "${ECS_CLUSTER}" \
    --service "${ECS_SERVICE}" --desired-count 1 \
    --deployment-configuration "${DEPLOY_CONFIGURATION}" >/dev/null
wait_for_selected_service "${CANDIDATE_TASK_DEFINITION}" 1

CANDIDATE_RUNNING_TASKS=$(running_tasks)
[ "$(printf '%s\n' "${CANDIDATE_RUNNING_TASKS}" | wc -w)" -eq 1 ] \
    || fail "candidate running-task identity is not singular"
CANDIDATE_RUNNING_TASK="${CANDIDATE_RUNNING_TASKS}"
TASK_HEALTH_DEADLINE=$(($(date +%s) + SERVICE_WAIT_SECONDS))
while true; do
    CANDIDATE_TASK_JSON=$(aws ecs describe-tasks \
        --region "${AWS_REGION}" --cluster "${ECS_CLUSTER}" \
        --tasks "${CANDIDATE_RUNNING_TASK}" --query 'tasks[0]' --output json)
    TASK_HEALTH_STATE=$(printf '%s' "${CANDIDATE_TASK_JSON}" \
        | EXPECTED_TASK="${CANDIDATE_TASK_DEFINITION}" \
          EXPECTED_DIGEST="${IMAGE_DIGEST}" python3 -c '
import json, os, sys
task = json.load(sys.stdin)
containers = task.get("containers", [])
if task.get("taskDefinitionArn") != os.environ["EXPECTED_TASK"]:
    raise SystemExit("running task definition differs from candidate")
if len(containers) != 1 or containers[0].get("imageDigest") != os.environ["EXPECTED_DIGEST"]:
    raise SystemExit("running image digest differs from built artifact")
if task.get("lastStatus") != "RUNNING":
    raise SystemExit("candidate task stopped before health propagation")
print("healthy" if task.get("healthStatus") == "HEALTHY" else "waiting")
')
    [ "${TASK_HEALTH_STATE}" = "healthy" ] && break
    [ "$(date +%s)" -lt "${TASK_HEALTH_DEADLINE}" ] \
        || fail "candidate task health did not become ready"
    sleep 3
done
CANDIDATE_TICK=$(wait_for_lean_http)
CUTOVER_ARMED=0
printf '      identity preserved; native tick %s -> %s\n' \
    "${CUTOVER_TICK}" "${CANDIDATE_TICK}"

echo "[6/7] Pinning only the live-verified digest as production-current."
aws ecr put-image \
    --region "${AWS_REGION}" --repository-name "${ECR_REPOSITORY}" \
    --image-tag production-current --image-manifest "${IMAGE_MANIFEST}" >/dev/null
PINNED_DIGEST=$(aws ecr describe-images \
    --region "${AWS_REGION}" --repository-name "${ECR_REPOSITORY}" \
    --image-ids imageTag=production-current \
    --query 'imageDetails[0].imageDigest' --output text)
[ "${PINNED_DIGEST}" = "${IMAGE_DIGEST}" ] \
    || fail "production-current does not identify the verified artifact"

FINISHED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "[7/7] Lean deployment complete."
STARTED_AT="${STARTED_AT}" FINISHED_AT="${FINISHED_AT}" \
GIT_SHA="${GIT_SHA}" TASK_DEFINITION="${CANDIDATE_TASK_DEFINITION}" \
IMAGE_DIGEST="${IMAGE_DIGEST}" TICK="${CANDIDATE_TICK}" python3 -c '
import json, os
print(json.dumps({
    "automatic_legacy_rollback": False,
    "finished_at": os.environ["FINISHED_AT"],
    "git_sha": os.environ["GIT_SHA"],
    "identity": "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1",
    "image_digest": os.environ["IMAGE_DIGEST"],
    "native_tick": int(os.environ["TICK"]),
    "schema": "guala.lean_deployment.v1",
    "started_at": os.environ["STARTED_AT"],
    "status": "deployed_live_verified",
    "task_definition": os.environ["TASK_DEFINITION"],
}, sort_keys=True))
'
