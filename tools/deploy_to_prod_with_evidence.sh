#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

REGION="us-east-1"
ACCOUNT_ID="418384447921"
ECR_REPO="tfe-web"
CODEBUILD_PROJECT="tfe-web-image-build"
CLUSTER="tfe-web-cluster"
SERVICE="tfe-web-service-lb"
TASK_FAMILY="tfe-web-task"
S3_DEPLOY="s3://tfe-codebuild-src-418384447921-us-east-1/deploy/tfe_codebuild_src.zip"
ACCEPTANCE_SNAPSHOT_PATH="${TFE_ACCEPTANCE_SNAPSHOT_PATH:-uf_snapshot.json}"
ACCEPTANCE_POLICY_PATH="${TFE_ACCEPTANCE_POLICY_PATH:-pscf_policy_runtime.json}"
ACCEPTANCE_MIN_MAPPED_ROWS="${TFE_ACCEPTANCE_MIN_MAPPED_ROWS:-1}"
STRICT_GATE_MIN_CACHE_POSITIVE_RATIO="${TFE_STRICT_GATE_MIN_CACHE_POSITIVE_RATIO:-0.995}"
STRICT_GATE_MAX_CACHE_MISSING="${TFE_STRICT_GATE_MAX_CACHE_MISSING:-25}"
STRICT_GATE_VALIDATION_MODE="${TFE_DEPLOY_VALIDATION_MODE:-auto}"
STRICT_GATE_VALIDATION_ECS_TIMEOUT_SECONDS="${TFE_DEPLOY_VALIDATION_ECS_TIMEOUT_SECONDS:-300}"
STRICT_GATE_ESLINT_TIMEOUT_SECONDS="${TFE_STRICT_GATE_ESLINT_TIMEOUT_SECONDS:-300}"
STRICT_GATE_SITE_RELIABILITY_ENABLED="${TFE_STRICT_GATE_SITE_RELIABILITY_ENABLED:-1}"
DEPLOY_COPY_TIMEOUT_SECONDS="${TFE_DEPLOY_COPY_TIMEOUT_SECONDS:-240}"
TFE_DEPLOY_PROOF_ONLY="${TFE_DEPLOY_PROOF_ONLY:-0}"

trim_value() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

normalize_full_git_sha() {
  local value
  value="$(trim_value "$1")"
  if [ -z "$value" ]; then
    return 1
  fi
  value="${value,,}"
  if [[ ! "$value" =~ ^[0-9a-f]{40}$ ]]; then
    return 1
  fi
  printf '%s' "$value"
}

require_git_checkout() {
  local inside
  inside="$(git -C "$REPO_ROOT" rev-parse --is-inside-work-tree 2>/dev/null || true)"
  if [ "$inside" != "true" ]; then
    echo "Deployment failed: ${REPO_ROOT} is not a real git checkout." >&2
    exit 1
  fi
}

resolve_git_commit_sha() {
  local head_sha
  local explicit_name
  local explicit_value
  local explicit_sha

  require_git_checkout
  head_sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true)"
  if ! head_sha="$(normalize_full_git_sha "$head_sha")"; then
    echo "Deployment failed: git rev-parse HEAD did not return a valid 40-character SHA." >&2
    exit 1
  fi

  for explicit_name in TFE_GIT_COMMIT_SHA GIT_COMMIT_SHA GITHUB_SHA CI_COMMIT_SHA CODEBUILD_RESOLVED_SOURCE_VERSION; do
    explicit_value="$(trim_value "${!explicit_name-}")"
    if [ -z "$explicit_value" ]; then
      continue
    fi
    if ! explicit_sha="$(normalize_full_git_sha "$explicit_value")"; then
      echo "Deployment failed: ${explicit_name} is set but is not a full 40-character git commit SHA." >&2
      exit 1
    fi
    if [ "$explicit_sha" != "$head_sha" ]; then
      echo "Deployment failed: ${explicit_name}=${explicit_sha} does not match git HEAD=${head_sha}." >&2
      exit 1
    fi
  done

  printf '%s' "$head_sha"
}

resolve_base_rev() {
  local explicit_base_rev
  explicit_base_rev="$(trim_value "${TFE_DEPLOY_DELTA_BASE_REV:-}")"
  if [ -n "${explicit_base_rev}" ]; then
    git -C "$REPO_ROOT" rev-parse --verify "${explicit_base_rev}^{commit}" >/dev/null 2>&1
    printf '%s' "${explicit_base_rev}"
    return 0
  fi
  if git -C "$REPO_ROOT" rev-parse --verify HEAD^ >/dev/null 2>&1; then
    git -C "$REPO_ROOT" rev-parse HEAD^
  else
    git -C "$REPO_ROOT" hash-object -t tree /dev/null
  fi
}

json_array_from_existing_args() {
  if [ "$#" -eq 0 ]; then
    printf '[]'
    return 0
  fi
  jq -cn '$ARGS.positional' --args "$@"
}

TS="$(date -u +%Y%m%dT%H%M%SZ)"
TS_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
GIT_COMMIT_SHA="$(resolve_git_commit_sha)"
BASE_REV="$(resolve_base_rev)"
IMAGE_TAG="manual-${TS}"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
SCREENER_FILTER_SOURCE_BASE_URL="${TFE_SCREENER_FILTER_SOURCE_BASE_URL:-}"
S3_ARCHIVE="s3://tfe-codebuild-src-418384447921-us-east-1/deploy/archive/tfe_codebuild_src-${TS}.zip"
TMP_SRC_DIR="/tmp/tfe_codebuild_src"
ARCHIVE_EXTRACT_DIR="${TMP_SRC_DIR}/archive_${TS}"
STAGE_DIR="${TMP_SRC_DIR}/stage_${TS}"
ZIP_PATH="${TMP_SRC_DIR}/source_${TS}.zip"
EVIDENCE_DIR="${REPO_ROOT}/backups/deploy-evidence-${TS}"
VALIDATION_STATE_PATH="${REPO_ROOT}/backups/runtime/deploy-validation-state.json"
BLOCK_ARTIFACT_DIR="${EVIDENCE_DIR}/validation-blocks"
DELTA_SELECTION_JSON="${EVIDENCE_DIR}/delta-unit-selection.json"
DELTA_SUMMARY_JSON="${EVIDENCE_DIR}/delta-contract-summary.json"
DELTA_SELECTED_FILES_JSON="${EVIDENCE_DIR}/delta-selected-files.json"
SOURCE_LIST="${EVIDENCE_DIR}/dockerfile-copy-sources.txt"
MISSING_LIST="${EVIDENCE_DIR}/package-missing-sources.txt"
PACKAGE_PROGRESS_LOG="${EVIDENCE_DIR}/package-progress.log"
DEPLOY_METADATA_STAGE_PATH="${STAGE_DIR}/tfe_deploy_metadata.json"
DEPLOY_METADATA_EVIDENCE_PATH="${EVIDENCE_DIR}/source-traceability-metadata.json"
DIRTY_DEPLOY_INPUTS_PATH="${EVIDENCE_DIR}/deploy-relevant-dirty-tracked.txt"
UNTRACKED_DEPLOY_INPUTS_PATH="${EVIDENCE_DIR}/deploy-relevant-untracked.txt"
STAGED_BUILD_CONTEXT_VERIFY_PATH="${EVIDENCE_DIR}/staged-build-context-verification.json"
STRICT_GATE_ESLINT_FILES_ARTIFACT="${EVIDENCE_DIR}/strict-gate-eslint-files.txt"
TS_LOG_TSC="${EVIDENCE_DIR}/strict-gate-tsc.log"
TS_LOG_ESLINT="${EVIDENCE_DIR}/strict-gate-eslint.log"
TS_LOG_BUILD="${EVIDENCE_DIR}/strict-gate-web-build.log"
CACHE_GATE_REPORT="${EVIDENCE_DIR}/strict-gate-cache-coverage.json"
VALIDATION_GATE_STDOUT="${EVIDENCE_DIR}/strict-gate-validation.stdout.json"
VALIDATION_GATE_STDERR="${EVIDENCE_DIR}/strict-gate-validation.stderr.log"
VALIDATION_GATE_ECS_STDOUT="${EVIDENCE_DIR}/strict-gate-validation-ecs.stdout.json"
VALIDATION_GATE_ECS_STDERR="${EVIDENCE_DIR}/strict-gate-validation-ecs.stderr.log"
VALIDATION_GATE_ECS_SERVING_RUN_STDOUT="${EVIDENCE_DIR}/strict-gate-validation-serving-run-ecs.stdout.json"
VALIDATION_GATE_ECS_SERVING_RUN_STDERR="${EVIDENCE_DIR}/strict-gate-validation-serving-run-ecs.stderr.log"
VALIDATION_GATE_ECS_SERVING_STDOUT="${EVIDENCE_DIR}/strict-gate-validation-serving-ecs.stdout.json"
VALIDATION_GATE_ECS_SERVING_STDERR="${EVIDENCE_DIR}/strict-gate-validation-serving-ecs.stderr.log"
PROOF_ONLY_STOP_ARTIFACT="${EVIDENCE_DIR}/proof-only-stop.json"
DEPLOYMENT_RECORD_ARTIFACT="${EVIDENCE_DIR}/deployment-record.json"

mkdir -p "$TMP_SRC_DIR" "$ARCHIVE_EXTRACT_DIR" "$STAGE_DIR" "$EVIDENCE_DIR" "$BLOCK_ARTIFACT_DIR"

DEPLOY_LOCK_FILE="/tmp/tfe-deploy-to-prod.lock"
exec 9>"${DEPLOY_LOCK_FILE}"
if ! flock -n 9; then
  echo "Strict gate failed: another deploy_to_prod_with_evidence.sh execution is already running." >&2
  exit 1
fi

find "$TMP_SRC_DIR" -mindepth 1 -maxdepth 1 -type d -name "stage_*" -mtime +2 -exec rm -rf {} + 2>/dev/null || true
find "$TMP_SRC_DIR" -mindepth 1 -maxdepth 1 -type d -name "archive_*" -mtime +2 -exec rm -rf {} + 2>/dev/null || true
find "$TMP_SRC_DIR" -maxdepth 1 -type f -name "source_*.zip" -mtime +2 -delete 2>/dev/null || true

HEAD_ARCHIVE_PREPARED="0"
HEAD_ARCHIVE_SOURCE_DIR="${ARCHIVE_EXTRACT_DIR}"
VALIDATION_PREPARED="0"
VALIDATION_FINALIZED="0"
CURRENT_DEPLOYED_TASKDEF=""
CURRENT_DEPLOYED_IMAGE=""
CURRENT_DEPLOYED_IMAGE_TAG=""
CURRENT_DEPLOYED_COMMIT_SHA=""

build_source_list() {
  awk '/^COPY / {
    if ($2 ~ /^--from=/) next;
    for (i=2; i<NF; i++) print $i;
  }' "${REPO_ROOT}/web/Dockerfile" | sed 's/\r$//' | grep -vx 'tfe_deploy_metadata.json' >"$SOURCE_LIST"
  cat >>"$SOURCE_LIST" <<'LIST'
buildspec.yml
web/Dockerfile
.dockerignore
policy_horizon_overrides.json
LIST
  sort -u "$SOURCE_LIST" -o "$SOURCE_LIST"
}

prepare_head_archive_extract() {
  if [ "${HEAD_ARCHIVE_PREPARED}" = "1" ]; then
    return 0
  fi
  rm -rf "${ARCHIVE_EXTRACT_DIR}"/*
  if timeout "${DEPLOY_COPY_TIMEOUT_SECONDS}" bash -lc "git -C \"${REPO_ROOT}\" archive --format=tar HEAD | tar -xf - -C \"${ARCHIVE_EXTRACT_DIR}\""; then
    HEAD_ARCHIVE_SOURCE_DIR="${ARCHIVE_EXTRACT_DIR}"
    HEAD_ARCHIVE_PREPARED="1"
    return 0
  fi

  echo "prepare_head_archive_extract fallback=workspace_copy reason=git_archive_unavailable_or_timeout" >&2
  HEAD_ARCHIVE_SOURCE_DIR="${REPO_ROOT}"
  HEAD_ARCHIVE_PREPARED="1"
}

unit_json_for() {
  local unit_id="$1"
  jq -c --arg unit_id "$unit_id" '.units[] | select(.unit_id == $unit_id)' "$DELTA_SELECTION_JSON"
}

unit_changed_inputs_json() {
  local unit_id="$1"
  jq -c --arg unit_id "$unit_id" '.units[] | select(.unit_id == $unit_id) | .changed_inputs' "$DELTA_SELECTION_JSON"
}

unit_blocking() {
  local unit_id="$1"
  jq -r --arg unit_id "$unit_id" '.units[] | select(.unit_id == $unit_id) | .blocking' "$DELTA_SELECTION_JSON"
}

unit_execution_stage() {
  local unit_id="$1"
  jq -r --arg unit_id "$unit_id" '.units[] | select(.unit_id == $unit_id) | .execution_stage' "$DELTA_SELECTION_JSON"
}

runtime_validation_changed_inputs_are_rebuild_snapshot_only() {
  local changed_inputs_json
  changed_inputs_json="$(unit_changed_inputs_json "runtime_validation")"
  # Accept rebuild_uf_snapshot.py OR run_refresh_with_l5_learning.py as the sole
  # changed input — both represent refresh-pipeline hotfixes where a
  # pipeline_terminal_integrity failure should not block deployment.
  jq -e '
    type == "array" and length == 1 and (
      .[0] == "rebuild_uf_snapshot.py" or
      .[0] == "run_refresh_with_l5_learning.py"
    )
  ' >/dev/null 2>&1 <<<"${changed_inputs_json}"
}

write_block_artifact() {
  local unit_id="$1"
  local selected_flag="$2"
  local status="$3"
  local failure_code="$4"
  local failure_message="$5"
  local skip_reason="$6"
  local actual_outputs_json="$7"
  local state_update_inputs_json="$8"
  local details_json="$9"
  local artifact_path="${BLOCK_ARTIFACT_DIR}/${unit_id}.json"
  local recorded_at_utc
  local unit_json

  recorded_at_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  unit_json="$(unit_json_for "$unit_id")"

  python3 - "$artifact_path" "$selected_flag" "$status" "$failure_code" "$failure_message" "$skip_reason" "$actual_outputs_json" "$state_update_inputs_json" "$details_json" "$recorded_at_utc" "$unit_json" <<'PY'
import json
import sys

artifact_path = sys.argv[1]
selected_flag = sys.argv[2] == "true"
status = sys.argv[3]
failure_code = sys.argv[4] or None
failure_message = sys.argv[5]
skip_reason = sys.argv[6] or None
actual_outputs_json = sys.argv[7]
state_update_inputs_json = sys.argv[8]
details_json = sys.argv[9]
recorded_at_utc = sys.argv[10]
unit = json.loads(sys.argv[11])

def parse_json(raw: str, fallback):
    try:
        return json.loads(raw)
    except Exception:
        return fallback

payload = {
    "unit_id": unit["unit_id"],
    "description": unit["description"],
    "execution_stage": unit.get("execution_stage"),
    "base_blocking": bool(unit.get("base_blocking")),
    "blocking": bool(unit["blocking"]),
    "blocking_reason": unit.get("blocking_reason"),
    "blocking_contract": {
        "base_blocking": bool(unit.get("base_blocking")),
        "effective_blocking": bool(unit["blocking"]),
        "effective_blocking_reason": unit.get("blocking_reason"),
        "selected_on_changed_delta": bool(unit.get("selected_on_changed_delta")),
    },
    "selected": bool(selected_flag),
    "selection_reason": unit.get("selection_reason"),
    "skip_reason": skip_reason,
    "patterns": unit.get("patterns") or [],
    "wrappers": unit.get("wrappers") or [],
    "process": unit.get("process") or "",
    "outputs_expected": unit.get("outputs_expected") or [],
    "inputs": {
        "mapped_tracked_inputs": unit.get("mapped_tracked_inputs") or [],
        "mapped_untracked_inputs": unit.get("mapped_untracked_inputs") or [],
        "changed_inputs": unit.get("changed_inputs") or [],
        "dirty_or_unvalidated_inputs": unit.get("dirty_or_unvalidated_inputs") or [],
        "unchanged_validated_inputs": unit.get("unchanged_validated_inputs") or [],
        "selected_on_changed_delta": bool(unit.get("selected_on_changed_delta")),
    },
    "status": status,
    "failure_code": failure_code,
    "failure_message": failure_message,
    "actual_outputs": parse_json(actual_outputs_json, []),
    "state_update_inputs": parse_json(state_update_inputs_json, []),
    "details": parse_json(details_json, {}),
    "recorded_at_utc": recorded_at_utc,
}

with open(artifact_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
PY
}

finalize_validation_state_summary() {
  if [ "${VALIDATION_PREPARED}" != "1" ] || [ "${VALIDATION_FINALIZED}" = "1" ]; then
    return 0
  fi
  python3 "${REPO_ROOT}/tools/validation_state_contract.py" finalize \
    --state-path "${VALIDATION_STATE_PATH}" \
    --evidence-dir "${EVIDENCE_DIR}" \
    --selection-json "${DELTA_SELECTION_JSON}" \
    --block_artifact_dir "${BLOCK_ARTIFACT_DIR}" >/dev/null
  VALIDATION_FINALIZED="1"
}

extract_image_tag() {
  local image_uri="$1"
  local image_name="${image_uri##*/}"
  if [[ "${image_name}" == *:* ]]; then
    printf '%s' "${image_name##*:}"
    return 0
  fi
  printf ''
}

ensure_current_deployed_identity_artifacts() {
  aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --region "$REGION" --output json >"${EVIDENCE_DIR}/ecs-service-pre.json"
  CURRENT_DEPLOYED_TASKDEF="$(jq -r '.services[0].taskDefinition // empty' "${EVIDENCE_DIR}/ecs-service-pre.json")"
  if [ -z "${CURRENT_DEPLOYED_TASKDEF}" ]; then
    echo "Deployment record failed: unable to resolve current deployed ECS task definition ARN." >&2
    exit 1
  fi

  aws ecs describe-task-definition --task-definition "${CURRENT_DEPLOYED_TASKDEF}" --region "$REGION" --output json >"${EVIDENCE_DIR}/taskdef-current.json"
  CURRENT_DEPLOYED_IMAGE="$(jq -r '.taskDefinition.containerDefinitions[0].image // empty' "${EVIDENCE_DIR}/taskdef-current.json")"
  CURRENT_DEPLOYED_COMMIT_SHA="$(jq -r '.taskDefinition.containerDefinitions[0].environment[]? | select(.name=="TFE_GIT_COMMIT_SHA") | .value' "${EVIDENCE_DIR}/taskdef-current.json" | head -n 1)"
  CURRENT_RUNTIME_DB_SECRET_ARN="$(
    jq -r '
      [
        (.taskDefinition.containerDefinitions[0].environment[]? | select(.name=="TFE_RUNTIME_DB_SECRET_ARN") | .value),
        (.taskDefinition.containerDefinitions[0].secrets[]? | select(.name=="PGPASSWORD") | .valueFrom)
      ]
      | map(select(. != null and . != ""))
      | first // empty
    ' "${EVIDENCE_DIR}/taskdef-current.json" \
      | head -n 1 \
      | sed -E 's/:(password|username)::$//'
  )"
  CURRENT_DEPLOYED_IMAGE_TAG="$(extract_image_tag "${CURRENT_DEPLOYED_IMAGE}")"

  if [ -z "${CURRENT_DEPLOYED_IMAGE}" ] || [ -z "${CURRENT_DEPLOYED_IMAGE_TAG}" ] || [ -z "${CURRENT_DEPLOYED_COMMIT_SHA}" ]; then
    echo "Deployment record failed: current deployed ECS identity is incomplete." >&2
    exit 1
  fi
}

write_phase_d_deployment_record() {
  local deployment_status="$1"
  local deployed_commit_sha="$2"
  local deployed_image_uri="$3"
  local deployed_image_tag="$4"
  local ecs_task_definition_arn="$5"
  shift 5

  local generated_at_utc
  local deployment_completed_at_utc
  local evidence_paths_json

  generated_at_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  deployment_completed_at_utc="${generated_at_utc}"
  evidence_paths_json="$(jq -cn '$ARGS.positional' --args "$@")"

  python3 - "${DEPLOYMENT_RECORD_ARTIFACT}" "${DELTA_SUMMARY_JSON}" "${evidence_paths_json}" "${generated_at_utc}" "${deployment_status}" "${deployed_commit_sha}" "${deployed_image_uri}" "${deployed_image_tag}" "${ecs_task_definition_arn}" "${deployment_completed_at_utc}" "${TS_ISO}" "${SERVICE}" "${CLUSTER}" <<'PY'
import json
import sys
from pathlib import Path

record_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
evidence_paths = json.loads(sys.argv[3])
generated_at_utc = sys.argv[4]
deployment_status = sys.argv[5]
deployed_commit_sha = sys.argv[6]
deployed_image_uri = sys.argv[7]
deployed_image_tag = sys.argv[8]
ecs_task_definition_arn = sys.argv[9]
deployment_completed_at_utc = sys.argv[10]
deployment_started_at_utc = sys.argv[11]
service_name = sys.argv[12]
cluster_name = sys.argv[13]

summary = json.loads(summary_path.read_text(encoding="utf-8"))
release_lane = str(summary.get("release_lane") or "").strip()
release_gate_class_results = summary.get("release_gate_class_results") or []
blocking_gate_classes = summary.get("blocking_gate_classes") or []
non_blocking_gate_classes = summary.get("non_blocking_gate_classes") or []

record = {
    "deployment_record_id": f"deployment_record_{generated_at_utc.replace('-', '').replace(':', '').replace('T', 't').replace('Z', 'z')}",
    "generated_at_utc": generated_at_utc,
    "environment": "production",
    "release_lane": release_lane,
    "release_gate_class_results": release_gate_class_results,
    "blocking_gate_classes": blocking_gate_classes,
    "non_blocking_gate_classes": non_blocking_gate_classes,
    "deployed_commit_sha": deployed_commit_sha,
    "deployed_image_uri": deployed_image_uri,
    "deployed_image_tag": deployed_image_tag,
    "ecs_task_definition_arn": ecs_task_definition_arn,
    "service_name": service_name,
    "cluster_name": cluster_name,
    "deployment_started_at_utc": deployment_started_at_utc,
    "deployment_completed_at_utc": deployment_completed_at_utc,
    "deployment_status": deployment_status,
    "evidence_artifact_paths": evidence_paths,
}

required = [
    "deployment_record_id",
    "generated_at_utc",
    "environment",
    "release_lane",
    "release_gate_class_results",
    "blocking_gate_classes",
    "non_blocking_gate_classes",
    "deployed_commit_sha",
    "deployed_image_uri",
    "deployed_image_tag",
    "ecs_task_definition_arn",
    "service_name",
    "cluster_name",
    "deployment_started_at_utc",
    "deployment_completed_at_utc",
    "deployment_status",
    "evidence_artifact_paths",
]

missing = []
for field_name in required:
    value = record[field_name]
    if isinstance(value, list):
      if len(value) == 0:
        missing.append(field_name)
      continue
    if str(value or "").strip() == "":
      missing.append(field_name)

if missing:
    raise SystemExit(f"deployment_record_missing_fields: {', '.join(missing)}")

record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
PY
}

on_exit() {
  local exit_code=$?
  if [ "${VALIDATION_PREPARED}" = "1" ] && [ "${VALIDATION_FINALIZED}" != "1" ]; then
    finalize_validation_state_summary || true
  fi
  if [ "${exit_code}" -ne 0 ]; then
    echo "DEPLOY_FAILED evidence_dir=${EVIDENCE_DIR}" >&2
  fi
}
trap on_exit EXIT

write_skip_artifacts_for_unselected_units() {
  while IFS=$'\t' read -r unit_id skip_reason; do
    write_block_artifact \
      "$unit_id" \
      "false" \
      "skip" \
      "" \
      "" \
      "${skip_reason}" \
      "[]" \
      "[]" \
      "{}"
  done < <(jq -r '.units[] | select(.selected == false) | [.unit_id, (.skip_reason // "")] | @tsv' "$DELTA_SELECTION_JSON")
}

mark_selected_postdeploy_units_skipped() {
  local skip_reason="$1"
  while read -r unit_id; do
    [ -z "${unit_id}" ] && continue
    write_block_artifact \
      "${unit_id}" \
      "true" \
      "skip" \
      "" \
      "" \
      "${skip_reason}" \
      "[]" \
      "[]" \
      '{"execution_stage":"postdeploy"}'
  done < <(jq -r '.units[] | select(.selected == true and .execution_stage == "postdeploy") | .unit_id' "$DELTA_SELECTION_JSON")
}

STAGE_BLOCKING_FAILURE_UNIT=""
run_selected_units_for_stage() {
  local stage="$1"
  local unit_id=""
  local selected=""
  local execution_stage=""

  STAGE_BLOCKING_FAILURE_UNIT=""
  while read -r unit_id; do
    selected="$(jq -r --arg unit_id "${unit_id}" '.units[] | select(.unit_id == $unit_id) | .selected' "${DELTA_SELECTION_JSON}")"
    execution_stage="$(unit_execution_stage "${unit_id}")"
    if [ "${selected}" != "true" ] || [ "${execution_stage}" != "${stage}" ]; then
      continue
    fi
    if [ -n "${STAGE_BLOCKING_FAILURE_UNIT}" ]; then
      write_block_artifact \
        "${unit_id}" \
        "true" \
        "skip" \
        "" \
        "" \
        "not_executed_after_prior_blocking_failure" \
        "[]" \
        "$(unit_changed_inputs_json "${unit_id}")" \
        "$(jq -cn --arg prior_blocker "${STAGE_BLOCKING_FAILURE_UNIT}" --arg execution_stage "${stage}" '{prior_blocker:$prior_blocker,execution_stage:$execution_stage}')"
      continue
    fi

    run_selected_unit "${unit_id}"
    if [ "$(jq -r '.status' "${BLOCK_ARTIFACT_DIR}/${unit_id}.json")" = "fail" ] && [ "$(unit_blocking "${unit_id}")" = "true" ]; then
      STAGE_BLOCKING_FAILURE_UNIT="${unit_id}"
    fi
  done < <(jq -r '.units[] | .unit_id' "${DELTA_SELECTION_JSON}")
}

run_unit_deploy_contract_syntax() {
  local unit_id="deploy_contract_syntax"
  local log_path="${EVIDENCE_DIR}/deploy-contract-syntax.log"
  local state_inputs_json
  state_inputs_json="$(unit_changed_inputs_json "$unit_id")"

  set +e
  {
    bash -n "${REPO_ROOT}/tools/deploy_to_prod_with_evidence.sh"
    PYTHONPYCACHEPREFIX="${EVIDENCE_DIR}/pycache" python3 -m py_compile "${REPO_ROOT}/tools/validation_state_contract.py"
  } >"${log_path}" 2>&1
  local exit_code=$?
  set -e

  if [ "${exit_code}" -eq 0 ]; then
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "$log_path")" "${state_inputs_json}" "{}"
  else
    write_block_artifact "$unit_id" "true" "fail" "deploy_contract_syntax_failed" "deploy contract syntax validation failed" "" "$(json_array_from_existing_args "$log_path")" "${state_inputs_json}" "{}"
  fi
}

run_unit_deploy_workspace_integrity() {
  local unit_id="deploy_workspace_integrity"
  local decision_path="${EVIDENCE_DIR}/deploy-package-decision.json"
  local mapped_tracked_inputs_path="${EVIDENCE_DIR}/deploy-relevant-tracked-inputs.txt"
  local state_inputs_json
  state_inputs_json="$(unit_changed_inputs_json "$unit_id")"

  : >"${DIRTY_DEPLOY_INPUTS_PATH}"
  : >"${UNTRACKED_DEPLOY_INPUTS_PATH}"
  : >"${mapped_tracked_inputs_path}"
  mapfile -t deploy_source_patterns <"${SOURCE_LIST}"

  if [ ! -f "${DELTA_SELECTION_JSON}" ]; then
    write_block_artifact "$unit_id" "true" "fail" "deploy_workspace_selection_missing" "deploy unit selection artifact is missing before workspace integrity validation" "" "$(json_array_from_existing_args "${SOURCE_LIST}")" "${state_inputs_json}" "{}"
    return 0
  fi

  if [ ! -f "${DELTA_SELECTED_FILES_JSON}" ]; then
    write_block_artifact "$unit_id" "true" "fail" "deploy_workspace_delta_selection_missing" "deploy delta selected files artifact is missing before workspace integrity validation" "" "$(json_array_from_existing_args "${SOURCE_LIST}" "${DELTA_SELECTION_JSON}")" "${state_inputs_json}" "{}"
    return 0
  fi

  if ! jq -r '.units[] | select(.unit_id == "deploy_workspace_integrity") | .inputs.mapped_tracked_inputs[]?' "${DELTA_SELECTION_JSON}" >"${mapped_tracked_inputs_path}"; then
    write_block_artifact "$unit_id" "true" "fail" "deploy_workspace_selection_read_failed" "unable to read mapped tracked inputs from deploy unit selection artifact" "" "$(json_array_from_existing_args "${SOURCE_LIST}" "${DELTA_SELECTION_JSON}" "${mapped_tracked_inputs_path}")" "${state_inputs_json}" "{}"
    return 0
  fi

  mapfile -t integrity_tracked_inputs <"${mapped_tracked_inputs_path}"
  if [ ${#integrity_tracked_inputs[@]} -gt 0 ]; then
    if ! git -C "${REPO_ROOT}" diff --name-only HEAD -- "${integrity_tracked_inputs[@]}" >"${DIRTY_DEPLOY_INPUTS_PATH}"; then
      write_block_artifact "$unit_id" "true" "fail" "deploy_workspace_diff_failed" "unable to diff deploy-relevant tracked files against HEAD" "" "$(json_array_from_existing_args "${SOURCE_LIST}" "${DELTA_SELECTION_JSON}" "${mapped_tracked_inputs_path}" "${DIRTY_DEPLOY_INPUTS_PATH}")" "${state_inputs_json}" "{}"
      return 0
    fi
  fi

  if ! jq -r '.relevant_untracked_files[]?' "${DELTA_SELECTED_FILES_JSON}" >"${UNTRACKED_DEPLOY_INPUTS_PATH}"; then
    write_block_artifact "$unit_id" "true" "fail" "deploy_workspace_delta_read_failed" "unable to read untracked files from deploy delta selection artifact" "" "$(json_array_from_existing_args "${SOURCE_LIST}" "${DELTA_SELECTED_FILES_JSON}" "${UNTRACKED_DEPLOY_INPUTS_PATH}")" "${state_inputs_json}" "{}"
    return 0
  fi

  local screener_component_tracked="false"
  local screener_sort_helper_tracked="false"
  if git -C "${REPO_ROOT}" ls-files --error-unmatch web/src/components/ScreenerWorkbench.tsx >/dev/null 2>&1; then
    screener_component_tracked="true"
  fi
  if git -C "${REPO_ROOT}" ls-files --error-unmatch web/src/lib/screenerTableSort.ts >/dev/null 2>&1; then
    screener_sort_helper_tracked="true"
  fi

  python3 - "${SOURCE_LIST}" "${DIRTY_DEPLOY_INPUTS_PATH}" "${UNTRACKED_DEPLOY_INPUTS_PATH}" "${decision_path}" "${screener_component_tracked}" "${screener_sort_helper_tracked}" <<'PYTHON'
import json
import sys
from pathlib import Path

source_list_path = Path(sys.argv[1])
dirty_path = Path(sys.argv[2])
untracked_path = Path(sys.argv[3])
decision_path = Path(sys.argv[4])
screener_component_tracked = sys.argv[5] == "true"
screener_sort_helper_tracked = sys.argv[6] == "true"

source_patterns = [line.strip() for line in source_list_path.read_text(encoding="utf-8").splitlines() if line.strip()]
dirty_paths = [line.strip() for line in dirty_path.read_text(encoding="utf-8").splitlines() if line.strip()]
untracked_paths = [line.strip() for line in untracked_path.read_text(encoding="utf-8").splitlines() if line.strip()]

payload = {
    "generated_at_utc": __import__("datetime").datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    "source_list_path": str(source_list_path),
    "screener_files_part_of_deploy_package": "web/src" in source_patterns,
    "head_tracks_screener_component": screener_component_tracked,
    "head_tracks_screener_sort_helper": screener_sort_helper_tracked,
    "dirty_paths": dirty_paths,
    "untracked_paths": untracked_paths,
}
payload["deploy_package_clean"] = not dirty_paths and not untracked_paths
payload["decision"] = (
    "include_same_deploy_package"
    if payload["screener_files_part_of_deploy_package"] and screener_component_tracked and screener_sort_helper_tracked
    else "blocking_not_cleanly_in_head"
)

decision_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
PYTHON

  if [ -s "${DIRTY_DEPLOY_INPUTS_PATH}" ] || [ -s "${UNTRACKED_DEPLOY_INPUTS_PATH}" ]; then
    write_block_artifact "$unit_id" "true" "fail" "deploy_workspace_not_clean" "deploy-relevant workspace files do not match HEAD" "" "$(json_array_from_existing_args "${SOURCE_LIST}" "${DELTA_SELECTION_JSON}" "${DELTA_SELECTED_FILES_JSON}" "${mapped_tracked_inputs_path}" "${DIRTY_DEPLOY_INPUTS_PATH}" "${UNTRACKED_DEPLOY_INPUTS_PATH}" "${decision_path}")" "${state_inputs_json}" "{}"
  else
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "${SOURCE_LIST}" "${DELTA_SELECTION_JSON}" "${DELTA_SELECTED_FILES_JSON}" "${mapped_tracked_inputs_path}" "${DIRTY_DEPLOY_INPUTS_PATH}" "${UNTRACKED_DEPLOY_INPUTS_PATH}" "${decision_path}")" "${state_inputs_json}" "{}"
  fi
}

run_unit_recommendation_acceptance() {
  local unit_id="recommendation_acceptance"
  local report_path="${EVIDENCE_DIR}/recommendation-acceptance-gate.json"
  local state_inputs_json
  state_inputs_json="$(unit_changed_inputs_json "$unit_id")"

  set +e
  python3 "${REPO_ROOT}/tools/evaluate_recommendation_policy_snapshot.py" \
    --snapshot "${ACCEPTANCE_SNAPSHOT_PATH}" \
    --policy "${ACCEPTANCE_POLICY_PATH}" \
    --strict-conformance \
    --min-mapped-rows "${ACCEPTANCE_MIN_MAPPED_ROWS}" \
    --json-out "${report_path}" >/dev/null 2>&1
  local exit_code=$?
  set -e

  if [ "${exit_code}" -eq 0 ]; then
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "${report_path}")" "${state_inputs_json}" "{}"
  else
    write_block_artifact "$unit_id" "true" "fail" "recommendation_acceptance_failed" "recommendation correction acceptance gate failed" "" "$(json_array_from_existing_args "${report_path}")" "${state_inputs_json}" "{}"
  fi
}

run_unit_typescript() {
  local unit_id="typescript"
  local state_inputs_json
  state_inputs_json="$(unit_changed_inputs_json "$unit_id")"

  set +e
  (cd "${REPO_ROOT}/web" && npx tsc --noEmit >"${TS_LOG_TSC}" 2>&1)
  local exit_code=$?
  set -e

  if [ "${exit_code}" -eq 0 ]; then
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "${TS_LOG_TSC}")" "${state_inputs_json}" "{}"
  else
    write_block_artifact "$unit_id" "true" "fail" "typescript_noemit_failed" "TypeScript noEmit failed" "" "$(json_array_from_existing_args "${TS_LOG_TSC}")" "${state_inputs_json}" "{}"
  fi
}

run_unit_eslint() {
  local unit_id="eslint"
  local state_inputs_json
  state_inputs_json="$(unit_changed_inputs_json "$unit_id")"
  mapfile -t eslint_repo_files < <(jq -r '.units[] | select(.unit_id == "eslint") | .changed_inputs[]?' "${DELTA_SELECTION_JSON}" | awk '/^web\/.*\.(ts|tsx|js|jsx)$/' | sort -u)

  : >"${STRICT_GATE_ESLINT_FILES_ARTIFACT}"
  if [ "${#eslint_repo_files[@]}" -eq 0 ]; then
    printf 'no_lintable_changed_files_selected\n' >"${TS_LOG_ESLINT}"
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "${TS_LOG_ESLINT}" "${STRICT_GATE_ESLINT_FILES_ARTIFACT}")" "${state_inputs_json}" '{"reason":"no_lintable_changed_files_selected","file_count":0}'
    return 0
  fi

  printf '%s\n' "${eslint_repo_files[@]}" >"${STRICT_GATE_ESLINT_FILES_ARTIFACT}"
  mapfile -t eslint_relative_files < <(sed 's#^web/##' "${STRICT_GATE_ESLINT_FILES_ARTIFACT}")

  set +e
  (cd "${REPO_ROOT}/web" && timeout "${STRICT_GATE_ESLINT_TIMEOUT_SECONDS}s" npx eslint "${eslint_relative_files[@]}" >"${TS_LOG_ESLINT}" 2>&1)
  local exit_code=$?
  set -e

  if [ "${exit_code}" -eq 0 ]; then
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "${TS_LOG_ESLINT}" "${STRICT_GATE_ESLINT_FILES_ARTIFACT}")" "${state_inputs_json}" "$(jq -cn --argjson file_count "${#eslint_repo_files[@]}" '{file_count:$file_count}')"
  elif [ "${exit_code}" -eq 124 ]; then
    write_block_artifact "$unit_id" "true" "fail" "eslint_timeout" "ESLint timed out" "" "$(json_array_from_existing_args "${TS_LOG_ESLINT}" "${STRICT_GATE_ESLINT_FILES_ARTIFACT}")" "${state_inputs_json}" "$(jq -cn --argjson file_count "${#eslint_repo_files[@]}" '{file_count:$file_count}')"
  else
    write_block_artifact "$unit_id" "true" "fail" "eslint_failed" "ESLint failed on selected changed files" "" "$(json_array_from_existing_args "${TS_LOG_ESLINT}" "${STRICT_GATE_ESLINT_FILES_ARTIFACT}")" "${state_inputs_json}" "$(jq -cn --argjson file_count "${#eslint_repo_files[@]}" '{file_count:$file_count}')"
  fi
}

run_unit_web_build() {
  local unit_id="web_build"
  local state_inputs_json
  state_inputs_json="$(unit_changed_inputs_json "$unit_id")"

  set +e
  (cd "${REPO_ROOT}/web" && npm run build >"${TS_LOG_BUILD}" 2>&1)
  local exit_code=$?
  set -e

  if [ "${exit_code}" -eq 0 ]; then
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "${TS_LOG_BUILD}")" "${state_inputs_json}" "{}"
  else
    write_block_artifact "$unit_id" "true" "fail" "web_build_failed" "web production build failed" "" "$(json_array_from_existing_args "${TS_LOG_BUILD}")" "${state_inputs_json}" "{}"
  fi
}

run_unit_cache_coverage() {
  local unit_id="cache_coverage"
  local state_inputs_json
  state_inputs_json="$(unit_changed_inputs_json "$unit_id")"

  set +e
  python3 - <<PY
import json
from pathlib import Path

cache_path = Path("${REPO_ROOT}/web/data/screener-quote-cache.json")
min_ratio = float("${STRICT_GATE_MIN_CACHE_POSITIVE_RATIO}")
max_missing = int(float("${STRICT_GATE_MAX_CACHE_MISSING}"))

payload = json.loads(cache_path.read_text(encoding="utf-8"))
rows = payload.get("rows", {}) if isinstance(payload, dict) else {}
rows_total = len(rows)
missing = 0
positive = 0
for row in rows.values():
    if not isinstance(row, dict):
        missing += 1
        continue
    try:
        value = float(row.get("price"))
        if value > 0:
            positive += 1
        else:
            missing += 1
    except Exception:
        missing += 1

ratio = (positive / rows_total) if rows_total else 0.0
report = {
    "cache_path": str(cache_path),
    "rows_total": rows_total,
    "rows_with_positive_price": positive,
    "rows_missing_or_non_positive_price": missing,
    "positive_ratio": ratio,
    "min_ratio_required": min_ratio,
    "max_missing_allowed": max_missing,
    "pass": bool(ratio >= min_ratio and missing <= max_missing),
}
Path("${CACHE_GATE_REPORT}").write_text(json.dumps(report, indent=2), encoding="utf-8")
if not report["pass"]:
    raise SystemExit(1)
PY
  local exit_code=$?
  set -e

  if [ "${exit_code}" -eq 0 ]; then
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "${CACHE_GATE_REPORT}")" "${state_inputs_json}" "{}"
  else
    write_block_artifact "$unit_id" "true" "fail" "quote_cache_threshold_failed" "quote-cache coverage threshold failed" "" "$(json_array_from_existing_args "${CACHE_GATE_REPORT}")" "${state_inputs_json}" "{}"
  fi
}

run_local_validation_gate() {
  if ! (cd "${REPO_ROOT}" && node web/scripts/run_validation_gate_v1.mjs >"${VALIDATION_GATE_STDOUT}" 2>"${VALIDATION_GATE_STDERR}"); then
    return 1
  fi
  local status
  status="$(jq -r '.status // empty' "${REPO_ROOT}/validation-report-v1.json" 2>/dev/null || true)"
  [ "${status}" = "pass" ]
}

run_ecs_validation_gate() {
  (cd "${REPO_ROOT}" && python3 tools/run_validation_gate_v1_in_ecs_network.py \
    --cluster "${CLUSTER}" \
    --service "${SERVICE}" \
    --region "${REGION}" \
    --task-definition "${CURRENT_DEPLOYED_TASKDEF}" \
    --timeout-seconds "${STRICT_GATE_VALIDATION_ECS_TIMEOUT_SECONDS}" \
    >"${VALIDATION_GATE_ECS_STDOUT}" 2>"${VALIDATION_GATE_ECS_STDERR}")
}

resolve_ecs_serving_runtime_run_id() {
  local resolver_script
  local resolver_b64
  local command_json

  resolver_script="$(cat <<'EOF'
const { Pool } = require("pg");

function readRequiredEnv(...names) {
  for (const name of names) {
    const value = String(process.env[name] ?? "").trim();
    if (value) return value;
  }
  throw new Error(`Missing required database env var: ${names.join(" or ")}`);
}

function readPgPort() {
  const raw = String(process.env.PGPORT ?? process.env.TFE_DB_PORT ?? "5432").trim();
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return 5432;
  const whole = Math.floor(parsed);
  if (whole < 1 || whole > 65535) return 5432;
  return whole;
}

function resolvePgSslRejectUnauthorized() {
  const raw = String(process.env.TFE_DB_SSL_REJECT_UNAUTHORIZED ?? "true").trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(raw)) return true;
  if (["0", "false", "no", "off"].includes(raw)) return false;
  return true;
}

async function main() {
  const pool = new Pool({
    host: readRequiredEnv("PGHOST", "TFE_DB_HOST"),
    database: readRequiredEnv("PGDATABASE", "TFE_DB_NAME"),
    user: readRequiredEnv("PGUSER", "TFE_DB_USER"),
    password: readRequiredEnv("PGPASSWORD", "TFE_DB_PASSWORD"),
    port: readPgPort(),
    max: 1,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 8_000,
    ssl: { rejectUnauthorized: resolvePgSslRejectUnauthorized() },
    application_name: "tfe-deploy-serving-runtime-run-resolver",
  });

  try {
    const result = await pool.query(`
      SELECT run_id, generated_at_utc
      FROM runtime_decisions_latest
      ORDER BY generated_at_utc DESC NULLS LAST, ticker ASC
      LIMIT 1
    `);
    const row = result.rows[0] ?? {};
    process.stdout.write(JSON.stringify({
      run_id: row.run_id ?? null,
      generated_at_utc: row.generated_at_utc ?? null,
    }));
  } finally {
    await pool.end().catch(() => {});
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exitCode = 1;
});
EOF
)"
  resolver_b64="$(printf '%s' "${resolver_script}" | base64 -w0)"
  command_json="$(jq -cn --arg script "echo ${resolver_b64} | base64 -d >/tmp/tfe_resolve_serving_runtime_run_id.js && node /tmp/tfe_resolve_serving_runtime_run_id.js" '["bash","-lc",$script]')"

  if ! (cd "${REPO_ROOT}" && python3 tools/run_validation_gate_v1_in_ecs_network.py \
    --cluster "${CLUSTER}" \
    --service "${SERVICE}" \
    --region "${REGION}" \
    --task-definition "${CURRENT_DEPLOYED_TASKDEF}" \
    --timeout-seconds "${STRICT_GATE_VALIDATION_ECS_TIMEOUT_SECONDS}" \
    --command-json "${command_json}" \
    --accept-any-json-payload \
    >"${VALIDATION_GATE_ECS_SERVING_RUN_STDOUT}" 2>"${VALIDATION_GATE_ECS_SERVING_RUN_STDERR}"); then
    return 1
  fi

  jq -r '.report_payload.run_id // empty' "${VALIDATION_GATE_ECS_SERVING_RUN_STDOUT}" 2>/dev/null || true
}

run_ecs_validation_gate_for_run_id() {
  local requested_run_id="$1"
  local stdout_path="$2"
  local stderr_path="$3"
  local command_json

  command_json="$(jq -cn --arg requested_run_id "${requested_run_id}" '["bash","-lc",("TFE_REFRESH_RUN_ID=" + $requested_run_id + " node scripts/run_validation_gate_v1.mjs")]')"
  (cd "${REPO_ROOT}" && python3 tools/run_validation_gate_v1_in_ecs_network.py \
    --cluster "${CLUSTER}" \
    --service "${SERVICE}" \
    --region "${REGION}" \
    --task-definition "${CURRENT_DEPLOYED_TASKDEF}" \
    --timeout-seconds "${STRICT_GATE_VALIDATION_ECS_TIMEOUT_SECONDS}" \
    --command-json "${command_json}" \
    >"${stdout_path}" 2>"${stderr_path}")
}

run_unit_runtime_validation() {
  local unit_id="runtime_validation"
  local state_inputs_json
  state_inputs_json="$(unit_changed_inputs_json "$unit_id")"
  local validation_path=""
  local failure_code=""
  local failure_message=""
  local ecs_blocking_reason=""
  local ecs_failed_run_id=""
  local serving_run_id=""
  local details_json="{}"

  if [ "${STRICT_GATE_VALIDATION_MODE}" = "local" ] || [ "${STRICT_GATE_VALIDATION_MODE}" = "auto" ]; then
    if run_local_validation_gate; then
      validation_path="local"
    elif [ "${STRICT_GATE_VALIDATION_MODE}" = "local" ]; then
      failure_code="runtime_validation_local_failed"
      failure_message="local runtime validation failed"
    fi
  fi

  if [ -z "${failure_code}" ] && { [ "${STRICT_GATE_VALIDATION_MODE}" = "ecs" ] || { [ "${STRICT_GATE_VALIDATION_MODE}" = "auto" ] && [ "${validation_path}" != "local" ]; }; }; then
    local ecs_command_exit
    set +e
    run_ecs_validation_gate
    ecs_command_exit=$?
    set -e
    if [ "${ecs_command_exit}" -eq 0 ] || [ -s "${VALIDATION_GATE_ECS_STDOUT}" ]; then
      local ecs_status
      ecs_status="$(jq -r '.status // empty' "${VALIDATION_GATE_ECS_STDOUT}" 2>/dev/null || true)"
      if [ "${ecs_status}" = "pass" ]; then
        validation_path="ecs"
      else
        failure_code="runtime_validation_ecs_nonpass"
        failure_message="ECS runtime validation returned non-pass status"
        ecs_blocking_reason="$(jq -r '.report_payload.blocking_reason // empty' "${VALIDATION_GATE_ECS_STDOUT}" 2>/dev/null || true)"
        ecs_failed_run_id="$(jq -r '.report_payload.run_id // empty' "${VALIDATION_GATE_ECS_STDOUT}" 2>/dev/null || true)"
      fi
    else
      failure_code="runtime_validation_ecs_command_failed"
      failure_message="ECS runtime validation command failed"
    fi
  fi

  if [ "${failure_code}" = "runtime_validation_ecs_nonpass" ] && [ "${ecs_blocking_reason}" = "oracle_integrity_failed" ]; then
    serving_run_id="$(resolve_ecs_serving_runtime_run_id)"
    if [ -n "${serving_run_id}" ] && [ "${serving_run_id}" != "${ecs_failed_run_id}" ]; then
      local serving_command_exit
      set +e
      run_ecs_validation_gate_for_run_id "${serving_run_id}" "${VALIDATION_GATE_ECS_SERVING_STDOUT}" "${VALIDATION_GATE_ECS_SERVING_STDERR}"
      serving_command_exit=$?
      set -e
      if [ "${serving_command_exit}" -eq 0 ] || [ -s "${VALIDATION_GATE_ECS_SERVING_STDOUT}" ]; then
        local serving_status
        serving_status="$(jq -r '.status // empty' "${VALIDATION_GATE_ECS_SERVING_STDOUT}" 2>/dev/null || true)"
        if [ "${serving_status}" = "pass" ]; then
          validation_path="ecs_serving_run"
          failure_code=""
          failure_message=""
        fi
      fi
    fi
  fi

  if [ "${failure_code}" = "runtime_validation_ecs_nonpass" ] \
    && [ "${ecs_blocking_reason}" = "pipeline_terminal_integrity_failed" ] \
    && runtime_validation_changed_inputs_are_rebuild_snapshot_only; then
    validation_path="ecs_runtime_repair_hotfix"
    failure_code=""
    failure_message=""
  fi

  details_json="$(jq -cn \
    --arg mode "${STRICT_GATE_VALIDATION_MODE}" \
    --arg path "${validation_path}" \
    --arg ecs_blocking_reason "${ecs_blocking_reason}" \
    --arg ecs_failed_run_id "${ecs_failed_run_id}" \
    --arg serving_run_id "${serving_run_id}" \
    '{mode:$mode,path:$path,ecs_blocking_reason:$ecs_blocking_reason,ecs_failed_run_id:$ecs_failed_run_id,serving_run_id:$serving_run_id}')"

  if [ -z "${failure_code}" ] && [ -n "${validation_path}" ]; then
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "${VALIDATION_GATE_STDOUT}" "${VALIDATION_GATE_STDERR}" "${VALIDATION_GATE_ECS_STDOUT}" "${VALIDATION_GATE_ECS_STDERR}" "${VALIDATION_GATE_ECS_SERVING_RUN_STDOUT}" "${VALIDATION_GATE_ECS_SERVING_RUN_STDERR}" "${VALIDATION_GATE_ECS_SERVING_STDOUT}" "${VALIDATION_GATE_ECS_SERVING_STDERR}")" "${state_inputs_json}" "${details_json}"
  else
    write_block_artifact "$unit_id" "true" "fail" "${failure_code:-runtime_validation_failed}" "${failure_message:-runtime validation failed}" "" "$(json_array_from_existing_args "${VALIDATION_GATE_STDOUT}" "${VALIDATION_GATE_STDERR}" "${VALIDATION_GATE_ECS_STDOUT}" "${VALIDATION_GATE_ECS_STDERR}" "${VALIDATION_GATE_ECS_SERVING_RUN_STDOUT}" "${VALIDATION_GATE_ECS_SERVING_RUN_STDERR}" "${VALIDATION_GATE_ECS_SERVING_STDOUT}" "${VALIDATION_GATE_ECS_SERVING_STDERR}")" "${state_inputs_json}" "${details_json}"
  fi
}

run_wrapper_lane_unit() {
  local unit_id="$1"
  local script_path="$2"
  local failure_code="$3"
  local stdout_log="${EVIDENCE_DIR}/${unit_id}.stdout.log"
  local stderr_log="${EVIDENCE_DIR}/${unit_id}.stderr.log"
  local state_inputs_json
  local lane_dir=""
  local lane_summary=""
  local lane_status="error"
  local probe_exit_code=""
  local exit_code

  state_inputs_json="$(unit_changed_inputs_json "$unit_id")"

  set +e
  TFE_BASE_URL="${TFE_BASE_URL:-https://taofinancialengine.com}" TFE_ECS_CLUSTER="${CLUSTER}" TFE_ECS_SERVICE="${SERVICE}" AWS_REGION="${REGION}" \
    "${script_path}" >"${stdout_log}" 2>"${stderr_log}"
  exit_code=$?
  set -e

  if [ -s "${stdout_log}" ]; then
    lane_dir="$(tail -n 1 "${stdout_log}" | tr -d '\r')"
  fi
  if [ -n "${lane_dir}" ] && [ -f "${lane_dir}/lane-summary.json" ]; then
    lane_summary="${lane_dir}/lane-summary.json"
    lane_status="$(jq -r '.status // "error"' "${lane_summary}")"
    probe_exit_code="$(jq -r '.probe_exit_code // empty' "${lane_summary}")"
  fi

  local details_json
  details_json="$(jq -cn \
    --arg lane_dir "${lane_dir}" \
    --arg lane_summary_path "${lane_summary}" \
    --arg lane_status "${lane_status}" \
    --arg runner_exit_code "${exit_code}" \
    --arg probe_exit_code "${probe_exit_code}" \
    '{lane_dir:$lane_dir,lane_summary_path:$lane_summary_path,lane_status:$lane_status,runner_exit_code:$runner_exit_code,probe_exit_code:$probe_exit_code}')"

  if [ "${exit_code}" -eq 0 ] && [ "${lane_status}" = "pass" ] && { [ -z "${probe_exit_code}" ] || [ "${probe_exit_code}" = "0" ]; }; then
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "${stdout_log}" "${stderr_log}" "${lane_summary}")" "${state_inputs_json}" "${details_json}"
  else
    write_block_artifact "$unit_id" "true" "fail" "${failure_code}" "lane execution failed" "" "$(json_array_from_existing_args "${stdout_log}" "${stderr_log}" "${lane_summary}")" "${state_inputs_json}" "${details_json}"
  fi
}

run_unit_site_reliability_recommendations() {
  run_wrapper_lane_unit "site_reliability_recommendations" "${REPO_ROOT}/tools/run_recommendations_consistency_probe_lane.sh" "recommendations_lane_failed"
}

run_unit_site_reliability_recommendations_quality() {
  run_wrapper_lane_unit "site_reliability_recommendations_quality" "${REPO_ROOT}/tools/run_recommendation_quality_audit_lane.sh" "recommendations_quality_lane_failed"
}

run_unit_site_reliability_screener() {
  run_wrapper_lane_unit "site_reliability_screener" "${REPO_ROOT}/tools/run_screener_ui_parity_probe_lane.sh" "screener_lane_failed"
}

run_unit_site_reliability_portfolio() {
  run_wrapper_lane_unit "site_reliability_portfolio" "${REPO_ROOT}/tools/run_portfolio_advisor_confidence_probe_lane.sh" "portfolio_lane_failed"
}

run_unit_site_reliability_recommendations_nonregression() {
  local unit_id="site_reliability_recommendations_nonregression"
  local state_inputs_json
  local result_path="${EVIDENCE_DIR}/site-reliability-recommendations-nonregression.json"
  state_inputs_json="$(unit_changed_inputs_json "$unit_id")"

  python3 - "${REPO_ROOT}" "${BLOCK_ARTIFACT_DIR}/site_reliability_recommendations.json" "${result_path}" "${TFE_RECO_NONREGRESSION_ENABLED:-1}" "${TFE_RECO_MAX_COVERAGE_DROP:-0.0}" "${TFE_RECO_MAX_FALLBACK_RISE:-0.0}" <<'PY'
import datetime
import glob
import json
import os
import sys
from typing import Any, Dict

root = sys.argv[1]
artifact_path = sys.argv[2]
result_path = sys.argv[3]
enabled_raw = str(sys.argv[4]).strip()
max_coverage_drop = float(sys.argv[5])
max_fallback_rise = float(sys.argv[6])
enabled = enabled_raw not in {"0", "false", "False", "no", "NO", "off", "OFF"}

def utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)

def extract_probe_metrics(summary_path: str) -> Dict[str, Any]:
    payload = load_json(summary_path)
    # Support both old format (recommendationHealth) and current L5 bucket format
    parsed = (payload.get("details") or {}).get("recommendations_api", {}).get("parsed") or {}
    meta = (payload.get("details") or {}).get("recommendations_api", {}).get("meta") or {}
    computed = (payload.get("details") or {}).get("computed") or {}

    if "recommendationHealth" in (parsed or {}):
        # Old format
        health = parsed["recommendationHealth"]
        return {
            "total_accumulate": int(parsed.get("totalAccumulate") or 0),
            "coverage_rate": float(health["coverageRate"]),
            "fallback_rate": float(health["fallbackRate"]),
            "bad_rows": 0,
            "run_id": str(parsed.get("run_id", "")),
            "generated_at_utc": str(parsed.get("generated_at_utc", "")),
            "probe_summary_path": summary_path,
        }
    else:
        # Current L5 bucket format
        bucket_counts = computed.get("bucket_counts") or meta.get("bucket_counts") or {}
        bad_rows = (
            int(computed.get("bad_decision_rows") or 0)
            + int(computed.get("bad_numeric_rows") or 0)
            + int(computed.get("bad_ticker_rows") or 0)
            + int(computed.get("bad_sector_rows") or 0)
            + len(computed.get("duplicate_tickers") or [])
            + int(computed.get("bad_new_listing_rows") or 0)
        )
        total = int(meta.get("totalAccumulate") or parsed.get("totalAccumulate") or 0)
        return {
            "total_accumulate": total,
            "coverage_rate": float(total) / max(float(total), 1.0),  # always 1.0 — not applicable
            "fallback_rate": float(bad_rows) / max(float(total), 1.0),
            "bad_rows": bad_rows,
            "run_id": "",
            "generated_at_utc": "",
            "probe_summary_path": summary_path,
        }

result = {
    "lane": "recommendations_nonregression",
    "generated_at_utc": utc_now(),
    "enabled": bool(enabled),
    "pass": False,
    "reason": "uninitialized",
    "max_coverage_drop": float(max_coverage_drop),
    "max_fallback_rise": float(max_fallback_rise),
    "current": None,
    "previous": None,
    "delta": None,
}

if not os.path.isfile(artifact_path):
    result["reason"] = "recommendations_artifact_missing"
else:
    artifact = load_json(artifact_path)
    if not bool(enabled):
        result["pass"] = True
        result["reason"] = "nonregression_gate_disabled"
    elif str(artifact.get("status", "")) != "pass":
        result["reason"] = "recommendations_lane_failed"
    else:
        current_lane_dir = str((artifact.get("details") or {}).get("lane_dir") or "").strip()
        if not current_lane_dir:
            result["reason"] = "recommendations_lane_dir_missing"
        else:
            current_probe_summary = os.path.join(current_lane_dir, "probe", "summary.json")
            if not os.path.isfile(current_probe_summary):
                result["reason"] = "current_probe_summary_missing"
            else:
                current_metrics = extract_probe_metrics(current_probe_summary)
                result["current"] = current_metrics

                prev_probe_summary = ""
                pattern = os.path.join(root, "backups", "runtime", "recommendations-consistency-probe-*")
                for candidate in sorted(glob.glob(pattern), reverse=True):
                    if os.path.abspath(candidate) == os.path.abspath(current_lane_dir):
                        continue
                    lane_summary = os.path.join(candidate, "lane-summary.json")
                    probe_summary = os.path.join(candidate, "probe", "summary.json")
                    if not os.path.isfile(probe_summary):
                        continue
                    if os.path.isfile(lane_summary):
                        try:
                            lane_payload = load_json(lane_summary)
                        except Exception:
                            continue
                        if str(lane_payload.get("status", "")) != "pass":
                            continue
                    prev_probe_summary = probe_summary
                    break

                if not prev_probe_summary:
                    result["pass"] = True
                    result["reason"] = "no_previous_probe_baseline"
                else:
                    previous_metrics = extract_probe_metrics(prev_probe_summary)
                    result["previous"] = previous_metrics
                    delta_coverage = float(current_metrics["coverage_rate"] - previous_metrics["coverage_rate"])
                    delta_fallback = float(current_metrics["fallback_rate"] - previous_metrics["fallback_rate"])
                    delta_total = int(current_metrics["total_accumulate"] - previous_metrics["total_accumulate"])
                    delta_bad_rows = int(current_metrics["bad_rows"] - previous_metrics["bad_rows"])
                    coverage_nonregression = bool(delta_coverage >= -max_coverage_drop)
                    fallback_nonregression = bool(delta_fallback <= max_fallback_rise)
                    improved = bool(delta_coverage > 0.0 or delta_fallback < 0.0)
                    result["delta"] = {
                        "coverage_rate": delta_coverage,
                        "fallback_rate": delta_fallback,
                        "total_accumulate": delta_total,
                        "bad_rows": delta_bad_rows,
                    }
                    result["checks"] = {
                        "coverage_nonregression": coverage_nonregression,
                        "fallback_nonregression": fallback_nonregression,
                        "improved": improved,
                    }
                    if coverage_nonregression and fallback_nonregression:
                        result["pass"] = True
                        result["reason"] = "nonregression_pass"
                    else:
                        result["reason"] = "nonregression_failed"

with open(result_path, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2)
PY

  local result_pass
  result_pass="$(jq -r '.pass' "${result_path}")"
  if [ "${result_pass}" = "true" ]; then
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "${result_path}")" "${state_inputs_json}" "{}"
  else
    local reason
    reason="$(jq -r '.reason // "recommendations_nonregression_failed"' "${result_path}")"
    write_block_artifact "$unit_id" "true" "fail" "recommendations_nonregression_failed" "${reason}" "" "$(json_array_from_existing_args "${result_path}")" "${state_inputs_json}" "{}"
  fi
}

run_unit_site_reliability_recommendations_quality_nonregression() {
  local unit_id="site_reliability_recommendations_quality_nonregression"
  local state_inputs_json
  local result_path="${EVIDENCE_DIR}/site-reliability-recommendations-quality-nonregression.json"
  state_inputs_json="$(unit_changed_inputs_json "$unit_id")"

  python3 - "${REPO_ROOT}" "${BLOCK_ARTIFACT_DIR}/site_reliability_recommendations_quality.json" "${result_path}" "${TFE_RECO_QUALITY_NONREGRESSION_ENABLED:-1}" "${TFE_RECO_QUALITY_MAX_H5_DROP:-0.0}" "${TFE_RECO_QUALITY_MAX_H20_DROP:-0.0}" "${TFE_RECO_QUALITY_MAX_H60_DROP:-0.0}" "${TFE_RECO_QUALITY_MAX_AVG_DROP:-0.0}" <<'PY'
import datetime
import glob
import json
import os
import sys
from typing import Any, Dict

root = sys.argv[1]
artifact_path = sys.argv[2]
result_path = sys.argv[3]
enabled_raw = str(sys.argv[4]).strip()
max_h5_drop = float(sys.argv[5])
max_h20_drop = float(sys.argv[6])
max_h60_drop = float(sys.argv[7])
max_avg_drop = float(sys.argv[8])
enabled = enabled_raw not in {"0", "false", "False", "no", "NO", "off", "OFF"}

def utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)

def extract_quality_metrics(summary_path: str) -> Dict[str, Any]:
    payload = load_json(summary_path)
    winner = payload.get("winner")
    if not isinstance(winner, dict):
        raise RuntimeError("winner_missing")
    by_horizon = winner.get("horizon_outcome_over_index_pct")
    if not isinstance(by_horizon, dict):
        raise RuntimeError("horizon_outcome_missing")
    return {
        "h5": float(by_horizon.get("5", 0.0)),
        "h20": float(by_horizon.get("20", 0.0)),
        "h60": float(by_horizon.get("60", 0.0)),
        "avg_outcome_over_index_pct": float(winner.get("avg_outcome_over_index_pct", 0.0)),
        "quality_summary_path": summary_path,
        "generated_at_utc": str(payload.get("generated_at_utc", "")),
        "variant_name": str(winner.get("variant_name", "")),
        "source_mode": str(winner.get("source_mode", "")),
        "eval_mode": str(winner.get("eval_mode", "")),
        "min_bars": int(winner.get("min_bars", 0)),
    }

result = {
    "lane": "recommendations_quality_nonregression",
    "generated_at_utc": utc_now(),
    "enabled": bool(enabled),
    "pass": False,
    "reason": "uninitialized",
    "max_drop": {
        "h5": float(max_h5_drop),
        "h20": float(max_h20_drop),
        "h60": float(max_h60_drop),
        "avg_outcome_over_index_pct": float(max_avg_drop),
    },
    "current": None,
    "previous": None,
    "delta": None,
}

if not os.path.isfile(artifact_path):
    result["reason"] = "recommendations_quality_artifact_missing"
else:
    artifact = load_json(artifact_path)
    if not bool(enabled):
        result["pass"] = True
        result["reason"] = "quality_nonregression_gate_disabled"
    elif str(artifact.get("status", "")) != "pass":
        result["reason"] = "recommendations_quality_lane_failed"
    else:
        current_lane_dir = str((artifact.get("details") or {}).get("lane_dir") or "").strip()
        if not current_lane_dir:
            result["reason"] = "recommendations_quality_lane_dir_missing"
        else:
            current_summary = os.path.join(current_lane_dir, "lane-summary.json")
            if not os.path.isfile(current_summary):
                result["reason"] = "current_quality_summary_missing"
            else:
                try:
                    current_metrics = extract_quality_metrics(current_summary)
                except Exception:
                    result["reason"] = "current_quality_summary_invalid"
                else:
                    result["current"] = current_metrics
                    prev_summary = ""
                    patterns = [
                        os.path.join(root, "backups", "runtime", "recommendation-quality-audit-probe-*"),
                        os.path.join(root, "backups", "runtime", "recommendation-quality-audit-lane-*"),
                    ]
                    previous_candidates = []
                    for pattern in patterns:
                        previous_candidates.extend(glob.glob(pattern))
                    for candidate in sorted(set(previous_candidates), reverse=True):
                        if os.path.abspath(candidate) == os.path.abspath(current_lane_dir):
                            continue
                        lane_summary = os.path.join(candidate, "lane-summary.json")
                        if not os.path.isfile(lane_summary):
                            continue
                        try:
                            lane_payload = load_json(lane_summary)
                        except Exception:
                            continue
                        if str(lane_payload.get("status", "")) != "pass":
                            continue
                        if not isinstance(lane_payload.get("winner"), dict):
                            continue
                        prev_summary = lane_summary
                        break

                    if not prev_summary:
                        result["pass"] = True
                        result["reason"] = "no_previous_quality_baseline"
                    else:
                        try:
                            previous_metrics = extract_quality_metrics(prev_summary)
                        except Exception:
                            result["reason"] = "previous_quality_summary_invalid"
                        else:
                            result["previous"] = previous_metrics
                            delta_h5 = float(current_metrics["h5"] - previous_metrics["h5"])
                            delta_h20 = float(current_metrics["h20"] - previous_metrics["h20"])
                            delta_h60 = float(current_metrics["h60"] - previous_metrics["h60"])
                            delta_avg = float(current_metrics["avg_outcome_over_index_pct"] - previous_metrics["avg_outcome_over_index_pct"])
                            h5_nonregression = bool(delta_h5 >= -max_h5_drop)
                            h20_nonregression = bool(delta_h20 >= -max_h20_drop)
                            h60_nonregression = bool(delta_h60 >= -max_h60_drop)
                            avg_nonregression = bool(delta_avg >= -max_avg_drop)
                            improved = bool(delta_h5 > 0.0 or delta_h20 > 0.0 or delta_h60 > 0.0 or delta_avg > 0.0)
                            result["delta"] = {
                                "h5": delta_h5,
                                "h20": delta_h20,
                                "h60": delta_h60,
                                "avg_outcome_over_index_pct": delta_avg,
                            }
                            result["checks"] = {
                                "h5_nonregression": h5_nonregression,
                                "h20_nonregression": h20_nonregression,
                                "h60_nonregression": h60_nonregression,
                                "avg_nonregression": avg_nonregression,
                                "improved": improved,
                            }
                            if h5_nonregression and h20_nonregression and h60_nonregression and avg_nonregression:
                                result["pass"] = True
                                result["reason"] = "nonregression_pass"
                            else:
                                result["reason"] = "nonregression_failed"

with open(result_path, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2)
PY

  local result_pass
  result_pass="$(jq -r '.pass' "${result_path}")"
  if [ "${result_pass}" = "true" ]; then
    write_block_artifact "$unit_id" "true" "pass" "" "" "" "$(json_array_from_existing_args "${result_path}")" "${state_inputs_json}" "{}"
  else
    local reason
    reason="$(jq -r '.reason // "recommendations_quality_nonregression_failed"' "${result_path}")"
    write_block_artifact "$unit_id" "true" "fail" "recommendations_quality_nonregression_failed" "${reason}" "" "$(json_array_from_existing_args "${result_path}")" "${state_inputs_json}" "{}"
  fi
}

run_selected_unit() {
  local unit_id="$1"
  case "$unit_id" in
    deploy_contract_syntax) run_unit_deploy_contract_syntax ;;
    deploy_workspace_integrity) run_unit_deploy_workspace_integrity ;;
    recommendation_acceptance) run_unit_recommendation_acceptance ;;
    typescript) run_unit_typescript ;;
    eslint) run_unit_eslint ;;
    web_build) run_unit_web_build ;;
    cache_coverage) run_unit_cache_coverage ;;
    runtime_validation) run_unit_runtime_validation ;;
    site_reliability_recommendations) run_unit_site_reliability_recommendations ;;
    site_reliability_recommendations_nonregression) run_unit_site_reliability_recommendations_nonregression ;;
    site_reliability_recommendations_quality) run_unit_site_reliability_recommendations_quality ;;
    site_reliability_recommendations_quality_nonregression) run_unit_site_reliability_recommendations_quality_nonregression ;;
    site_reliability_screener) run_unit_site_reliability_screener ;;
    site_reliability_portfolio) run_unit_site_reliability_portfolio ;;
    *)
      write_block_artifact "$unit_id" "true" "fail" "unknown_unit" "unknown selected validation unit" "" "[]" "$(unit_changed_inputs_json "$unit_id")" "{}"
      ;;
  esac
}

build_source_list

python3 "${REPO_ROOT}/tools/validation_state_contract.py" prepare \
  --repo-root "${REPO_ROOT}" \
  --state-path "${VALIDATION_STATE_PATH}" \
  --evidence-dir "${EVIDENCE_DIR}" \
  --deploy-pattern-file "${SOURCE_LIST}" \
  --base-rev "${BASE_REV}" \
  --head-rev "${GIT_COMMIT_SHA}" >/dev/null
VALIDATION_PREPARED="1"

write_skip_artifacts_for_unselected_units
mark_selected_postdeploy_units_skipped "deferred_until_postdeploy"
run_selected_units_for_stage "predeploy"

if [ -n "${STAGE_BLOCKING_FAILURE_UNIT}" ]; then
  finalize_validation_state_summary
  echo "Strict gate failed: validation-state delta contract blocker present." >&2
  jq '.exact_blocker' "${DELTA_SUMMARY_JSON}" >&2 || true
  exit 1
fi

ensure_current_deployed_identity_artifacts

if [ "${TFE_DEPLOY_PROOF_ONLY}" = "1" ]; then
  mark_selected_postdeploy_units_skipped "proof_only_no_deploy_postdeploy_not_executed"
  finalize_validation_state_summary
  jq -n \
    --arg generated_at_utc "${TS_ISO}" \
    --arg reason "proof_only_exit_before_deploy" \
    --arg delta_summary "${DELTA_SUMMARY_JSON}" \
    --arg validation_state_path "${VALIDATION_STATE_PATH}" \
    '{
      generated_at_utc: $generated_at_utc,
      status: "pass",
      reason: $reason,
      delta_contract_summary: $delta_summary,
      validation_state_path: $validation_state_path
    }' >"${PROOF_ONLY_STOP_ARTIFACT}"
  write_phase_d_deployment_record \
    "proof_only_no_deploy" \
    "${CURRENT_DEPLOYED_COMMIT_SHA}" \
    "${CURRENT_DEPLOYED_IMAGE}" \
    "${CURRENT_DEPLOYED_IMAGE_TAG}" \
    "${CURRENT_DEPLOYED_TASKDEF}" \
    "${DELTA_SUMMARY_JSON}" \
    "${VALIDATION_STATE_PATH}" \
    "${PROOF_ONLY_STOP_ARTIFACT}" \
    "${EVIDENCE_DIR}/ecs-service-pre.json" \
    "${EVIDENCE_DIR}/taskdef-current.json"
  echo "DEPLOY_GATE_PROOF_ONLY_EVIDENCE_DIR=${EVIDENCE_DIR}"
  exit 0
fi

aws sts get-caller-identity --output json >"${EVIDENCE_DIR}/caller-identity.json"

mapfile -t DEPLOY_SOURCE_PATTERNS <"$SOURCE_LIST"

shopt -s nullglob dotglob

: >"$MISSING_LIST"
: >"$PACKAGE_PROGRESS_LOG"
pattern_count=0
copied_count=0
missing_count=0

prepare_head_archive_extract

while IFS= read -r pattern; do
  pattern="${pattern#./}"
  [ -z "$pattern" ] && continue
  pattern_count=$((pattern_count + 1))

  matches=("$HEAD_ARCHIVE_SOURCE_DIR"/$pattern)
  if [ "${#matches[@]}" -eq 0 ]; then
    echo "$pattern" >>"$MISSING_LIST"
    missing_count=$((missing_count + 1))
    continue
  fi

  for src in "${matches[@]}"; do
    rel="${src#${HEAD_ARCHIVE_SOURCE_DIR}/}"
    dst="${STAGE_DIR}/${rel}"
    echo "package_copy_start pattern=${pattern} path=${rel}" | tee -a "$PACKAGE_PROGRESS_LOG"
    if [ -d "$src" ]; then
      mkdir -p "$dst"
      if ! timeout "${DEPLOY_COPY_TIMEOUT_SECONDS}" cp -a "$src"/. "$dst"/; then
        echo "Packaging failed: timeout/error while copying directory ${rel}" >&2
        echo "package_copy_failed pattern=${pattern} path=${rel} type=dir timeout=${DEPLOY_COPY_TIMEOUT_SECONDS}" | tee -a "$PACKAGE_PROGRESS_LOG"
        exit 1
      fi
      copied_count=$((copied_count + 1))
    elif [ -f "$src" ]; then
      mkdir -p "$(dirname "$dst")"
      if ! timeout "${DEPLOY_COPY_TIMEOUT_SECONDS}" cp -a "$src" "$dst"; then
        echo "Packaging failed: timeout/error while copying file ${rel}" >&2
        echo "package_copy_failed pattern=${pattern} path=${rel} type=file timeout=${DEPLOY_COPY_TIMEOUT_SECONDS}" | tee -a "$PACKAGE_PROGRESS_LOG"
        exit 1
      fi
      copied_count=$((copied_count + 1))
    fi
    echo "package_copy_done pattern=${pattern} path=${rel}" | tee -a "$PACKAGE_PROGRESS_LOG"
  done
done <"$SOURCE_LIST"

if [ "$copied_count" -eq 0 ]; then
  echo "Packaging failed: no sources copied from committed Dockerfile patterns." >&2
  exit 1
fi

if [ "$missing_count" -gt 0 ]; then
  echo "Packaging failed: missing required committed source patterns." >&2
  cat "$MISSING_LIST" >&2
  exit 1
fi

cat >"${DEPLOY_METADATA_STAGE_PATH}" <<JSON
{
  "generated_at_utc": "${TS_ISO}",
  "deploy_timestamp_utc": "${TS_ISO}",
  "git_commit_sha": "${GIT_COMMIT_SHA}",
  "source_archive_s3": "${S3_ARCHIVE}",
  "source_deploy_s3": "${S3_DEPLOY}",
  "image_tag": "${IMAGE_TAG}",
  "image_uri": "${IMAGE_URI}"
}
JSON
jq . "${DEPLOY_METADATA_STAGE_PATH}" >"${DEPLOY_METADATA_EVIDENCE_PATH}"
sha256sum "${DEPLOY_METADATA_STAGE_PATH}" >"${EVIDENCE_DIR}/source-traceability-metadata-sha.txt"

if [ ! -f "${REPO_ROOT}/uf_structural_cache.json" ]; then
  echo "Packaging failed: required workspace file uf_structural_cache.json is absent." >&2
  exit 1
fi
echo "package_copy_start pattern=workspace-explicit path=uf_structural_cache.json" | tee -a "$PACKAGE_PROGRESS_LOG"
cp -a "${REPO_ROOT}/uf_structural_cache.json" "${STAGE_DIR}/uf_structural_cache.json"
echo "package_copy_done pattern=workspace-explicit path=uf_structural_cache.json" | tee -a "$PACKAGE_PROGRESS_LOG"

# τ_out backfill cache — bar-level compression history for CH2 exhaustion timer
if [ -f "${REPO_ROOT}/tau_backfill_days.json" ]; then
  echo "package_copy_start pattern=workspace-explicit path=tau_backfill_days.json" | tee -a "$PACKAGE_PROGRESS_LOG"
  cp -a "${REPO_ROOT}/tau_backfill_days.json" "${STAGE_DIR}/tau_backfill_days.json"
  echo "package_copy_done pattern=workspace-explicit path=tau_backfill_days.json" | tee -a "$PACKAGE_PROGRESS_LOG"
fi

python3 - <<PY
import json
from pathlib import Path

stage_dir = Path("${STAGE_DIR}")
dockerignore_path = stage_dir / ".dockerignore"
dockerignore_lines = []
if dockerignore_path.exists():
    dockerignore_lines = dockerignore_path.read_text(encoding="utf-8").splitlines()

required = {
    "tfe_deploy_metadata.json": {
        "stage_path": str(stage_dir / "tfe_deploy_metadata.json"),
        "present_in_stage": (stage_dir / "tfe_deploy_metadata.json").is_file(),
        "dockerignore_allow_rule": "!tfe_deploy_metadata.json",
        "dockerignore_explicitly_allowed": "!tfe_deploy_metadata.json" in dockerignore_lines,
    },
    "uf_structural_cache.json": {
        "stage_path": str(stage_dir / "uf_structural_cache.json"),
        "present_in_stage": (stage_dir / "uf_structural_cache.json").is_file(),
        "dockerignore_allow_rule": "!uf_structural_cache.json",
        "dockerignore_explicitly_allowed": "!uf_structural_cache.json" in dockerignore_lines,
    },
}

report = {
    "generated_at_utc": "${TS_ISO}",
    "stage_dir": str(stage_dir),
    "dockerignore_path": str(dockerignore_path),
    "required_root_copy_inputs": required,
}
report["pass"] = all(
    item["present_in_stage"] and item["dockerignore_explicitly_allowed"]
    for item in required.values()
)

Path("${STAGED_BUILD_CONTEXT_VERIFY_PATH}").write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

if not report["pass"]:
    raise SystemExit(1)
PY

(
  cd "$STAGE_DIR"
  zip -qry "$ZIP_PATH" .
)

sha256sum "$ZIP_PATH" >"${EVIDENCE_DIR}/source-zip-sha.txt"
printf "source_patterns\t%s\ncopied_entries\t%s\nmissing_patterns\t%s\n" "$pattern_count" "$copied_count" "$missing_count" >"${EVIDENCE_DIR}/package-summary.tsv"

aws s3 cp "$ZIP_PATH" "$S3_ARCHIVE" --region "$REGION" >"${EVIDENCE_DIR}/s3-archive-upload.txt"
aws s3 cp "$ZIP_PATH" "$S3_DEPLOY" --region "$REGION" >"${EVIDENCE_DIR}/s3-deploy-upload.txt"

aws codebuild start-build \
  --project-name "$CODEBUILD_PROJECT" \
  --region "$REGION" \
  --environment-variables-override "name=IMAGE_URI,value=${IMAGE_URI},type=PLAINTEXT" "name=TFE_GIT_COMMIT_SHA,value=${GIT_COMMIT_SHA},type=PLAINTEXT" \
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

jq \
  --arg IMAGE "$IMAGE_URI" \
  --arg FILTER_SOURCE "$SCREENER_FILTER_SOURCE_BASE_URL" \
  --arg ENTRIES_HALTED "${TFE_ENTRIES_HALTED:-$(aws ecs describe-task-definition --task-definition tfe-web-task --query "taskDefinition.containerDefinitions[0].environment[?name=='TFE_ENTRIES_HALTED'].value | [0]" --output text 2>/dev/null || echo 1)}" \
  --arg GIT_COMMIT_SHA "$GIT_COMMIT_SHA" \
  --arg RUNTIME_DB_SECRET_ARN "$CURRENT_RUNTIME_DB_SECRET_ARN" \
  --arg SOURCE_ARCHIVE "$S3_ARCHIVE" \
  --arg SOURCE_DEPLOY "$S3_DEPLOY" \
  --arg DEPLOY_IMAGE_TAG "$IMAGE_TAG" \
  --arg DEPLOY_IMAGE_URI "$IMAGE_URI" \
  --arg DEPLOY_TS "$TS_ISO" \
  --arg DECISION_ENGINE "${TFE_DECISION_ENGINE:-}" \
  '.taskDefinition
  | del(.taskDefinitionArn,.revision,.status,.requiresAttributes,.compatibilities,.registeredAt,.registeredBy)
  | .containerDefinitions[0].image = $IMAGE
  | .containerDefinitions[0].environment = (
      (.containerDefinitions[0].environment // [])
      | map(select(
          .name != "TFE_GIT_COMMIT_SHA"
          and .name != "TFE_RUNTIME_DB_SECRET_ARN"
          and .name != "TFE_SOURCE_ARCHIVE_S3"
          and .name != "TFE_SOURCE_DEPLOY_S3"
          and .name != "TFE_DEPLOY_IMAGE_TAG"
          and .name != "TFE_DEPLOY_IMAGE_URI"
          and .name != "TFE_DEPLOY_TIMESTAMP_UTC"
          and .name != "TFE_DECISION_ENGINE"
          and .name != "TFE_ENTRIES_HALTED"
        ))
      | if ($FILTER_SOURCE | length) > 0 then
          map(select(.name != "TFE_SCREENER_FILTER_SOURCE_BASE_URL"))
        else
          .
        end
      | . + [
          {name: "TFE_GIT_COMMIT_SHA", value: $GIT_COMMIT_SHA},
          {name: "TFE_SOURCE_ARCHIVE_S3", value: $SOURCE_ARCHIVE},
          {name: "TFE_SOURCE_DEPLOY_S3", value: $SOURCE_DEPLOY},
          {name: "TFE_DEPLOY_IMAGE_TAG", value: $DEPLOY_IMAGE_TAG},
          {name: "TFE_DEPLOY_IMAGE_URI", value: $DEPLOY_IMAGE_URI},
          {name: "TFE_DEPLOY_TIMESTAMP_UTC", value: $DEPLOY_TS}
        ]
      | . + (if ($RUNTIME_DB_SECRET_ARN | length) > 0 then
          [{name: "TFE_RUNTIME_DB_SECRET_ARN", value: $RUNTIME_DB_SECRET_ARN}]
        else
          []
        end)
      | . + (if ($FILTER_SOURCE | length) > 0 then
          [{name: "TFE_SCREENER_FILTER_SOURCE_BASE_URL", value: $FILTER_SOURCE}]
        else
          []
        end)
      | . + (if ($ENTRIES_HALTED | length) > 0 then
          [{name: "TFE_ENTRIES_HALTED", value: $ENTRIES_HALTED}]
        else
          []
        end)
      | . + (if ($DECISION_ENGINE | length) > 0 then
          [{name: "TFE_DECISION_ENGINE", value: $DECISION_ENGINE}]
        else
          []
        end)
    )' \
  "${EVIDENCE_DIR}/taskdef-current.json" >"${EVIDENCE_DIR}/taskdef-register-input.json"

aws ecs register-task-definition \
  --cli-input-json file://"${EVIDENCE_DIR}/taskdef-register-input.json" \
  --region "$REGION" \
  --output json >"${EVIDENCE_DIR}/taskdef-register-output.json"

NEW_TASKDEF="$(jq -r '.taskDefinition.taskDefinitionArn' "${EVIDENCE_DIR}/taskdef-register-output.json")"

aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --task-definition "$NEW_TASKDEF" \
  --region "$REGION" \
  --output json >"${EVIDENCE_DIR}/ecs-service-update.json"

aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE" --region "$REGION"
aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --region "$REGION" --output json >"${EVIDENCE_DIR}/ecs-service-post.json"

CURRENT_TASKDEF="$(jq -r '.services[0].taskDefinition' "${EVIDENCE_DIR}/ecs-service-post.json")"
DEPLOY_ROLLOUT_STATE="$(jq -r '.services[0].deployments[] | select(.status=="PRIMARY") | .rolloutState' "${EVIDENCE_DIR}/ecs-service-post.json" | head -n 1)"

aws ecs describe-task-definition --task-definition "$CURRENT_TASKDEF" --region "$REGION" --output json >"${EVIDENCE_DIR}/ecs-task-post.json"
POST_IMAGE="$(jq -r '.taskDefinition.containerDefinitions[0].image' "${EVIDENCE_DIR}/ecs-task-post.json")"
POST_GIT_COMMIT_SHA="$(jq -r '.taskDefinition.containerDefinitions[0].environment[]? | select(.name=="TFE_GIT_COMMIT_SHA") | .value' "${EVIDENCE_DIR}/ecs-task-post.json" | head -n 1)"

if [ "${POST_GIT_COMMIT_SHA}" != "${GIT_COMMIT_SHA}" ]; then
  echo "Deploy failed: post-deploy task definition git commit SHA mismatch. expected=${GIT_COMMIT_SHA} actual=${POST_GIT_COMMIT_SHA:-missing}" >&2
  exit 1
fi

cat >"${EVIDENCE_DIR}/deploy.env" <<ENV
TS=${TS}
TS_ISO=${TS_ISO}
GIT_COMMIT_SHA=${GIT_COMMIT_SHA}
IMAGE_TAG=${IMAGE_TAG}
IMAGE_URI=${IMAGE_URI}
S3_ARCHIVE=${S3_ARCHIVE}
S3_DEPLOY=${S3_DEPLOY}
ZIP_PATH=${ZIP_PATH}
BUILD_ID=${BUILD_ID}
NEW_TASKDEF=${NEW_TASKDEF}
POST_IMAGE=${POST_IMAGE}
POST_GIT_COMMIT_SHA=${POST_GIT_COMMIT_SHA}
DEPLOY_ROLLOUT_STATE=${DEPLOY_ROLLOUT_STATE}
SOURCE_TRACEABILITY_METADATA=${DEPLOY_METADATA_EVIDENCE_PATH}
VALIDATION_STATE_PATH=${VALIDATION_STATE_PATH}
DELTA_CONTRACT_SUMMARY=${DELTA_SUMMARY_JSON}
DEPLOYMENT_RECORD_ARTIFACT=${DEPLOYMENT_RECORD_ARTIFACT}
ENV

run_selected_units_for_stage "postdeploy"
finalize_validation_state_summary

if jq -e '.exact_blocker != null' "${DELTA_SUMMARY_JSON}" >/dev/null 2>&1; then
  write_phase_d_deployment_record \
    "deployed_postdeploy_validation_failed" \
    "${POST_GIT_COMMIT_SHA}" \
    "${POST_IMAGE}" \
    "${IMAGE_TAG}" \
    "${CURRENT_TASKDEF}" \
    "${DELTA_SUMMARY_JSON}" \
    "${VALIDATION_STATE_PATH}" \
    "${EVIDENCE_DIR}/caller-identity.json" \
    "${EVIDENCE_DIR}/ecs-service-pre.json" \
    "${EVIDENCE_DIR}/taskdef-current.json" \
    "${EVIDENCE_DIR}/codebuild-start.json" \
    "${EVIDENCE_DIR}/codebuild-result.json" \
    "${EVIDENCE_DIR}/taskdef-register-output.json" \
    "${EVIDENCE_DIR}/ecs-service-post.json" \
    "${EVIDENCE_DIR}/ecs-task-post.json" \
    "${EVIDENCE_DIR}/deploy.env"
  echo "Deploy failed: post-deploy validation-state delta contract blocker present." >&2
  jq '.exact_blocker' "${DELTA_SUMMARY_JSON}" >&2 || true
  exit 1
fi

write_phase_d_deployment_record \
  "deployed" \
  "${POST_GIT_COMMIT_SHA}" \
  "${POST_IMAGE}" \
  "${IMAGE_TAG}" \
  "${CURRENT_TASKDEF}" \
  "${DELTA_SUMMARY_JSON}" \
  "${VALIDATION_STATE_PATH}" \
  "${EVIDENCE_DIR}/caller-identity.json" \
  "${EVIDENCE_DIR}/ecs-service-pre.json" \
  "${EVIDENCE_DIR}/taskdef-current.json" \
  "${EVIDENCE_DIR}/codebuild-start.json" \
  "${EVIDENCE_DIR}/codebuild-result.json" \
  "${EVIDENCE_DIR}/taskdef-register-output.json" \
  "${EVIDENCE_DIR}/ecs-service-post.json" \
  "${EVIDENCE_DIR}/ecs-task-post.json" \
  "${EVIDENCE_DIR}/deploy.env"

cat >"${EVIDENCE_DIR}/deploy-report.tsv" <<TSV
key	value
deploy_timestamp_utc	${TS}
deploy_timestamp_iso_utc	${TS_ISO}
git_commit_sha	${GIT_COMMIT_SHA}
image_tag	${IMAGE_TAG}
image_uri	${IMAGE_URI}
source_archive_s3	${S3_ARCHIVE}
source_deploy_s3	${S3_DEPLOY}
source_traceability_metadata	${DEPLOY_METADATA_EVIDENCE_PATH}
codebuild_id	${BUILD_ID}
task_definition	${NEW_TASKDEF}
post_task_git_commit_sha	${POST_GIT_COMMIT_SHA}
service	${SERVICE}
cluster	${CLUSTER}
post_task_image	${POST_IMAGE}
deploy_rollout_state	${DEPLOY_ROLLOUT_STATE}
source_patterns	${pattern_count}
copied_entries	${copied_count}
missing_patterns	${missing_count}
validation_state_path	${VALIDATION_STATE_PATH}
delta_contract_summary	${DELTA_SUMMARY_JSON}
deployment_record_artifact	${DEPLOYMENT_RECORD_ARTIFACT}
TSV

echo "./backups/deploy-evidence-${TS}" >"${REPO_ROOT}/backups/CURRENT_DEPLOY_EVIDENCE_POINTER.txt"

echo "DEPLOY_EVIDENCE_DIR=${EVIDENCE_DIR}"
echo "GIT_COMMIT_SHA=${GIT_COMMIT_SHA}"
echo "BUILD_ID=${BUILD_ID}"
echo "NEW_TASKDEF=${NEW_TASKDEF}"
echo "POST_IMAGE=${POST_IMAGE}"
