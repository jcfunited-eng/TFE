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
ACCEPTANCE_SNAPSHOT_PATH="${TFE_ACCEPTANCE_SNAPSHOT_PATH:-uf_snapshot.json}"
ACCEPTANCE_POLICY_PATH="${TFE_ACCEPTANCE_POLICY_PATH:-pscf_policy_runtime.json}"
ACCEPTANCE_MIN_MAPPED_ROWS="${TFE_ACCEPTANCE_MIN_MAPPED_ROWS:-1}"
STRICT_GATE_MIN_CACHE_POSITIVE_RATIO="${TFE_STRICT_GATE_MIN_CACHE_POSITIVE_RATIO:-0.995}"
STRICT_GATE_MAX_CACHE_MISSING="${TFE_STRICT_GATE_MAX_CACHE_MISSING:-25}"
STRICT_GATE_VALIDATION_MODE="${TFE_DEPLOY_VALIDATION_MODE:-auto}"
STRICT_GATE_VALIDATION_ECS_TIMEOUT_SECONDS="${TFE_DEPLOY_VALIDATION_ECS_TIMEOUT_SECONDS:-300}"
STRICT_GATE_ESLINT_TIMEOUT_SECONDS="${TFE_STRICT_GATE_ESLINT_TIMEOUT_SECONDS:-300}"
STRICT_GATE_ESLINT_ENABLED="${TFE_STRICT_GATE_ESLINT_ENABLED:-1}"
STRICT_GATE_WEB_BUILD_ENABLED="${TFE_STRICT_GATE_WEB_BUILD_ENABLED:-1}"
DEPLOY_COPY_TIMEOUT_SECONDS="${TFE_DEPLOY_COPY_TIMEOUT_SECONDS:-240}"
STRICT_GATE_SITE_RELIABILITY_ENABLED="${TFE_STRICT_GATE_SITE_RELIABILITY_ENABLED:-1}"

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

TS="$(date -u +%Y%m%dT%H%M%SZ)"
TS_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
GIT_COMMIT_SHA="$(resolve_git_commit_sha)"
IMAGE_TAG="manual-${TS}"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
SCREENER_FILTER_SOURCE_BASE_URL="${TFE_SCREENER_FILTER_SOURCE_BASE_URL:-}"
S3_ARCHIVE="s3://tfe-codebuild-src-418384447921-us-east-1/deploy/archive/tfe_codebuild_src-${TS}.zip"
TMP_SRC_DIR="/tmp/tfe_codebuild_src"
ARCHIVE_EXTRACT_DIR="${TMP_SRC_DIR}/archive_${TS}"
STAGE_DIR="${TMP_SRC_DIR}/stage_${TS}"
ZIP_PATH="${TMP_SRC_DIR}/source_${TS}.zip"
EVIDENCE_DIR="${REPO_ROOT}/backups/deploy-evidence-${TS}"
MISSING_LIST="${EVIDENCE_DIR}/package-missing-sources.txt"
SOURCE_LIST="${EVIDENCE_DIR}/dockerfile-copy-sources.txt"
PACKAGE_PROGRESS_LOG="${EVIDENCE_DIR}/package-progress.log"
DEPLOY_METADATA_STAGE_PATH="${STAGE_DIR}/tfe_deploy_metadata.json"
DEPLOY_METADATA_EVIDENCE_PATH="${EVIDENCE_DIR}/source-traceability-metadata.json"
DIRTY_DEPLOY_INPUTS_PATH="${EVIDENCE_DIR}/deploy-relevant-dirty-tracked.txt"
UNTRACKED_DEPLOY_INPUTS_PATH="${EVIDENCE_DIR}/deploy-relevant-untracked.txt"
STAGED_BUILD_CONTEXT_VERIFY_PATH="${EVIDENCE_DIR}/staged-build-context-verification.json"

mkdir -p "$TMP_SRC_DIR" "$ARCHIVE_EXTRACT_DIR" "$STAGE_DIR" "$EVIDENCE_DIR"

# Prevent overlapping deploy-gate executions from racing each other.
DEPLOY_LOCK_FILE="/tmp/tfe-deploy-to-prod.lock"
exec 9>"${DEPLOY_LOCK_FILE}"
if ! flock -n 9; then
  echo "Strict gate failed: another deploy_to_prod_with_evidence.sh execution is already running." >&2
  exit 1
fi

# Keep transient packaging cache bounded.
find "$TMP_SRC_DIR" -mindepth 1 -maxdepth 1 -type d -name "stage_*" -mtime +2 -exec rm -rf {} + 2>/dev/null || true
find "$TMP_SRC_DIR" -mindepth 1 -maxdepth 1 -type d -name "archive_*" -mtime +2 -exec rm -rf {} + 2>/dev/null || true
find "$TMP_SRC_DIR" -maxdepth 1 -type f -name "source_*.zip" -mtime +2 -delete 2>/dev/null || true

on_fail() {
  echo "DEPLOY_FAILED evidence_dir=${EVIDENCE_DIR}" >&2
}
trap on_fail ERR

# Acceptance gate: block deployment if recommendation logic regresses to
# non-policy decisioning.
ACCEPTANCE_GATE_REPORT="${EVIDENCE_DIR}/recommendation-acceptance-gate.json"
python3 tools/evaluate_recommendation_policy_snapshot.py \
  --snapshot "${ACCEPTANCE_SNAPSHOT_PATH}" \
  --policy "${ACCEPTANCE_POLICY_PATH}" \
  --strict-conformance \
  --min-mapped-rows "${ACCEPTANCE_MIN_MAPPED_ROWS}" \
  --json-out "${ACCEPTANCE_GATE_REPORT}"

ACCEPTANCE_MAPPED_ROWS="$(jq -r '.mapped_rows' "${ACCEPTANCE_GATE_REPORT}")"
ACCEPTANCE_MISMATCH_COUNT="$(jq -r '.mapped_decision_mismatch_count' "${ACCEPTANCE_GATE_REPORT}")"
ACCEPTANCE_STRICT_PASS="$(jq -r '.strict.pass' "${ACCEPTANCE_GATE_REPORT}")"

if [ "${ACCEPTANCE_STRICT_PASS}" != "true" ] || [ "${ACCEPTANCE_MISMATCH_COUNT}" != "0" ]; then
  echo "Recommendation correction acceptance gate failed." >&2
  exit 1
fi

# Strict reliability gates (mandatory before cloud build/deploy).
TS_LOG_TSC="${EVIDENCE_DIR}/strict-gate-tsc.log"
TS_LOG_ESLINT="${EVIDENCE_DIR}/strict-gate-eslint.log"
TS_LOG_BUILD="${EVIDENCE_DIR}/strict-gate-web-build.log"
CACHE_GATE_REPORT="${EVIDENCE_DIR}/strict-gate-cache-coverage.json"
VALIDATION_GATE_STDOUT="${EVIDENCE_DIR}/strict-gate-validation.stdout.json"
VALIDATION_GATE_STDERR="${EVIDENCE_DIR}/strict-gate-validation.stderr.log"
VALIDATION_GATE_ECS_STDOUT="${EVIDENCE_DIR}/strict-gate-validation-ecs.stdout.json"
VALIDATION_GATE_ECS_STDERR="${EVIDENCE_DIR}/strict-gate-validation-ecs.stderr.log"
SITE_RELIABILITY_GATE_REPORT="${EVIDENCE_DIR}/strict-gate-site-reliability.json"
SITE_RELIABILITY_GATE_STDOUT="${EVIDENCE_DIR}/strict-gate-site-reliability.stdout.log"
SITE_RELIABILITY_GATE_STDERR="${EVIDENCE_DIR}/strict-gate-site-reliability.stderr.log"
VALIDATION_BOOTSTRAP_ALLOW="${TFE_VALIDATION_GATE_BOOTSTRAP_ALLOW:-0}"
STRICT_GATE_VALIDATION_RESULT="pass"
STRICT_GATE_VALIDATION_REASON=""
STRICT_GATE_VALIDATION_PATH="local"
STRICT_GATE_ESLINT_RESULT="pass"
STRICT_GATE_WEB_BUILD_RESULT="pass"
STRICT_GATE_SITE_RELIABILITY_RESULT="disabled"
STRICT_GATE_SITE_RELIABILITY_REASON="disabled_by_env"

run_eslint_gate_with_timeout() {
  local timeout_seconds="${STRICT_GATE_ESLINT_TIMEOUT_SECONDS}"
  local lint_diag_log="${EVIDENCE_DIR}/strict-gate-eslint-timeout-diagnostics.log"
  rm -f "${lint_diag_log}"

  if (cd "${REPO_ROOT}/web" && timeout "${timeout_seconds}s" npx eslint src/app src/components src/lib >"${TS_LOG_ESLINT}" 2>&1); then
    return 0
  fi

  local eslint_exit=$?
  if [ "${eslint_exit}" -eq 124 ]; then
    {
      echo "timeout_seconds=${timeout_seconds}"
      date -u +"timeout_at_utc=%Y-%m-%dT%H:%M:%SZ"
      echo "process_snapshot_begin"
      ps -eo pid,ppid,etimes,pcpu,pmem,stat,cmd | rg "eslint src/app src/components src/lib|node .*eslint|npx eslint" || true
      echo "process_snapshot_end"
    } >"${lint_diag_log}"
    echo "Strict gate failed: ESLint timed out after ${timeout_seconds}s." >&2
    return 124
  fi

  return "${eslint_exit}"
}

echo "Strict gate: TypeScript noEmit"
if ! (cd "${REPO_ROOT}/web" && npx tsc --noEmit >"${TS_LOG_TSC}" 2>&1); then
  echo "Strict gate failed: TypeScript check." >&2
  tail -n 200 "${TS_LOG_TSC}" >&2 || true
  exit 1
fi

echo "Strict gate: ESLint (src/app + src/components + src/lib)"
if [ "${STRICT_GATE_ESLINT_ENABLED}" = "1" ]; then
  if ps -eo stat,cmd | awk '$1 ~ /^D/ && $0 ~ /node \/workspaces\/Tao_Financial_Engine\/web\/node_modules\/.bin\/eslint/ {found=1} END {exit(found ? 0 : 1)}'; then
    echo "Strict gate failed: detected lingering D-state eslint process before lint gate; aborting fail-fast." >&2
    exit 1
  fi

  run_eslint_gate_with_timeout
  ESLINT_EXIT_CODE=$?
  if [ "${ESLINT_EXIT_CODE}" -ne 0 ]; then
    if [ "${ESLINT_EXIT_CODE}" -eq 124 ]; then
      echo "Strict gate failed: ESLint timeout fail-stop." >&2
    else
      echo "Strict gate failed: ESLint." >&2
    fi
    tail -n 200 "${TS_LOG_ESLINT}" >&2 || true
    exit 1
  fi
else
  STRICT_GATE_ESLINT_RESULT="skip"
  echo "Strict gate: ESLint skipped because TFE_STRICT_GATE_ESLINT_ENABLED=0" >&2
  cat >"${TS_LOG_ESLINT}" <<'LOG'
eslint gate skipped because TFE_STRICT_GATE_ESLINT_ENABLED=0
LOG
fi

echo "Strict gate: Web production build"
if [ "${STRICT_GATE_WEB_BUILD_ENABLED}" = "1" ]; then
  if ! (cd "${REPO_ROOT}/web" && npm run build >"${TS_LOG_BUILD}" 2>&1); then
    echo "Strict gate failed: web build." >&2
    tail -n 200 "${TS_LOG_BUILD}" >&2 || true
    exit 1
  fi
else
  STRICT_GATE_WEB_BUILD_RESULT="skip"
  echo "Strict gate: Web production build skipped because TFE_STRICT_GATE_WEB_BUILD_ENABLED=0" >&2
  cat >"${TS_LOG_BUILD}" <<'LOG'
web build gate skipped because TFE_STRICT_GATE_WEB_BUILD_ENABLED=0
LOG
fi

echo "Strict gate: Quote-cache coverage threshold"
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

LOCAL_VALIDATION_OK=0
LOCAL_VALIDATION_ERROR=""

run_local_validation_gate() {
  if ! (cd "${REPO_ROOT}" && node web/scripts/run_validation_gate_v1.mjs >"${VALIDATION_GATE_STDOUT}" 2>"${VALIDATION_GATE_STDERR}"); then
    LOCAL_VALIDATION_ERROR="$(tail -n 1 "${VALIDATION_GATE_STDERR}" 2>/dev/null || true)"
    return 1
  fi

  local status
  status="$(jq -r '.status // empty' "${REPO_ROOT}/validation-report-v1.json" 2>/dev/null || true)"
  if [ "${status}" != "pass" ]; then
    LOCAL_VALIDATION_ERROR="validation-report-v1.json status is not pass. status=${status:-missing}"
    return 1
  fi

  LOCAL_VALIDATION_OK=1
  return 0
}

run_ecs_validation_gate() {
  (cd "${REPO_ROOT}" && python3 tools/run_validation_gate_v1_in_ecs_network.py \
    --cluster "${CLUSTER}" \
    --service "${SERVICE}" \
    --region "${REGION}" \
    --timeout-seconds "${STRICT_GATE_VALIDATION_ECS_TIMEOUT_SECONDS}" \
    >"${VALIDATION_GATE_ECS_STDOUT}" 2>"${VALIDATION_GATE_ECS_STDERR}")
}

echo "Strict gate: Runtime validation gate mode=${STRICT_GATE_VALIDATION_MODE}"

if [ "${STRICT_GATE_VALIDATION_MODE}" = "local" ] || [ "${STRICT_GATE_VALIDATION_MODE}" = "auto" ]; then
  if run_local_validation_gate; then
    STRICT_GATE_VALIDATION_PATH="local"
  elif [ "${STRICT_GATE_VALIDATION_MODE}" = "local" ]; then
    if [ "${VALIDATION_BOOTSTRAP_ALLOW}" = "1" ]; then
      STRICT_GATE_VALIDATION_RESULT="bootstrap-skip"
      STRICT_GATE_VALIDATION_REASON="${LOCAL_VALIDATION_ERROR:-local_validation_failed}"
      echo "Strict gate warning: local runtime validation failed but bootstrap override is enabled." >&2
      tail -n 50 "${VALIDATION_GATE_STDERR}" >&2 || true
    else
      echo "Strict gate failed: runtime validation gate." >&2
      echo "${LOCAL_VALIDATION_ERROR}" >&2
      tail -n 200 "${VALIDATION_GATE_STDERR}" >&2 || true
      exit 1
    fi
  fi
fi

if [ "${STRICT_GATE_VALIDATION_MODE}" = "ecs" ] || { [ "${STRICT_GATE_VALIDATION_MODE}" = "auto" ] && [ "${LOCAL_VALIDATION_OK}" != "1" ]; }; then
  if [ "${STRICT_GATE_VALIDATION_MODE}" = "auto" ] && [ "${LOCAL_VALIDATION_OK}" != "1" ]; then
    echo "Strict gate: local validation failed; retrying in ECS network context."
  fi

  if run_ecs_validation_gate; then
    ECS_STATUS="$(jq -r '.status // empty' "${VALIDATION_GATE_ECS_STDOUT}" 2>/dev/null || true)"
    if [ "${ECS_STATUS}" = "pass" ]; then
      STRICT_GATE_VALIDATION_PATH="ecs"
      if [ "${LOCAL_VALIDATION_OK}" != "1" ] && [ -n "${LOCAL_VALIDATION_ERROR}" ]; then
        STRICT_GATE_VALIDATION_REASON="local_failed_then_ecs_pass:${LOCAL_VALIDATION_ERROR}"
      fi
      STRICT_GATE_VALIDATION_RESULT="pass"
    else
      if [ "${VALIDATION_BOOTSTRAP_ALLOW}" = "1" ]; then
        STRICT_GATE_VALIDATION_RESULT="bootstrap-skip"
        STRICT_GATE_VALIDATION_REASON="ecs_validation_status=${ECS_STATUS:-missing}"
        echo "Strict gate warning: ECS runtime validation non-pass but bootstrap override is enabled." >&2
        cat "${VALIDATION_GATE_ECS_STDOUT}" >&2 || true
      else
        echo "Strict gate failed: ECS runtime validation returned non-pass status." >&2
        cat "${VALIDATION_GATE_ECS_STDOUT}" >&2 || true
        exit 1
      fi
    fi
  else
    if [ "${VALIDATION_BOOTSTRAP_ALLOW}" = "1" ]; then
      STRICT_GATE_VALIDATION_RESULT="bootstrap-skip"
      STRICT_GATE_VALIDATION_REASON="ecs_validation_command_failed"
      echo "Strict gate warning: ECS runtime validation command failed but bootstrap override is enabled." >&2
      tail -n 100 "${VALIDATION_GATE_ECS_STDERR}" >&2 || true
    else
      echo "Strict gate failed: ECS runtime validation command failed." >&2
      tail -n 200 "${VALIDATION_GATE_ECS_STDERR}" >&2 || true
      exit 1
    fi
  fi
fi

echo "Strict gate: Site reliability contract (recommendations + screener + portfolio)"
if [ "${STRICT_GATE_SITE_RELIABILITY_ENABLED}" = "1" ]; then
  if (cd "${REPO_ROOT}" && tools/run_site_reliability_contract_gate.sh \
    --output-json "${SITE_RELIABILITY_GATE_REPORT}" \
    >"${SITE_RELIABILITY_GATE_STDOUT}" 2>"${SITE_RELIABILITY_GATE_STDERR}"); then
    STRICT_GATE_SITE_RELIABILITY_RESULT="pass"
    STRICT_GATE_SITE_RELIABILITY_REASON="all_required_site_probe_lanes_passed"
  else
    STRICT_GATE_SITE_RELIABILITY_RESULT="fail"
    STRICT_GATE_SITE_RELIABILITY_REASON="one_or_more_required_site_probe_lanes_failed"
    echo "Strict gate failed: site reliability contract gate." >&2
    cat "${SITE_RELIABILITY_GATE_REPORT}" >&2 || true
    tail -n 200 "${SITE_RELIABILITY_GATE_STDERR}" >&2 || true
    exit 1
  fi
else
  cat >"${SITE_RELIABILITY_GATE_REPORT}" <<JSON
{
  "generated_at_utc": "${TS}",
  "status": "skip",
  "pass": true,
  "reason": "disabled_by_env",
  "required_lanes": ["recommendations", "screener", "portfolio"]
}
JSON
fi

# Rollback-safe pre-state capture
aws sts get-caller-identity --output json >"${EVIDENCE_DIR}/caller-identity.json"
aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --region "$REGION" --output json >"${EVIDENCE_DIR}/ecs-service-pre.json"
aws ecs describe-task-definition --task-definition "$TASK_FAMILY" --region "$REGION" --output json >"${EVIDENCE_DIR}/taskdef-current.json"

# Build source patterns directly from Dockerfile COPY directives (excluding --from stages).
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

: >"$DIRTY_DEPLOY_INPUTS_PATH"
: >"$UNTRACKED_DEPLOY_INPUTS_PATH"
mapfile -t DEPLOY_SOURCE_PATTERNS <"$SOURCE_LIST"

if ! git -C "$REPO_ROOT" diff --name-only HEAD -- "${DEPLOY_SOURCE_PATTERNS[@]}" >"$DIRTY_DEPLOY_INPUTS_PATH"; then
  echo "Deployment failed: unable to diff deploy-relevant tracked files against HEAD." >&2
  exit 1
fi
git -C "$REPO_ROOT" ls-files --others --exclude-standard -- "${DEPLOY_SOURCE_PATTERNS[@]}" >"$UNTRACKED_DEPLOY_INPUTS_PATH"

if [ -s "$DIRTY_DEPLOY_INPUTS_PATH" ] || [ -s "$UNTRACKED_DEPLOY_INPUTS_PATH" ]; then
  echo "Deployment failed: deploy-relevant workspace files do not match HEAD. Commit the deploy package first." >&2
  if [ -s "$DIRTY_DEPLOY_INPUTS_PATH" ]; then
    echo "Tracked deploy-relevant differences:" >&2
    sed -n '1,200p' "$DIRTY_DEPLOY_INPUTS_PATH" >&2
  fi
  if [ -s "$UNTRACKED_DEPLOY_INPUTS_PATH" ]; then
    echo "Untracked deploy-relevant files:" >&2
    sed -n '1,200p' "$UNTRACKED_DEPLOY_INPUTS_PATH" >&2
  fi
  exit 1
fi

rm -rf "$ARCHIVE_EXTRACT_DIR"/*
git -C "$REPO_ROOT" archive --format=tar HEAD | tar -xf - -C "$ARCHIVE_EXTRACT_DIR"

shopt -s nullglob dotglob

: >"$MISSING_LIST"
: >"$PACKAGE_PROGRESS_LOG"
pattern_count=0
copied_count=0
missing_count=0

while IFS= read -r pattern; do
  pattern="${pattern#./}"
  [ -z "$pattern" ] && continue
  pattern_count=$((pattern_count + 1))

  matches=("$ARCHIVE_EXTRACT_DIR"/$pattern)
  if [ "${#matches[@]}" -eq 0 ]; then
    echo "$pattern" >>"$MISSING_LIST"
    missing_count=$((missing_count + 1))
    continue
  fi

  for src in "${matches[@]}"; do
    rel="${src#${ARCHIVE_EXTRACT_DIR}/}"
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

# Upload source archive and deploy pointer zip
aws s3 cp "$ZIP_PATH" "$S3_ARCHIVE" --region "$REGION" >"${EVIDENCE_DIR}/s3-archive-upload.txt"
aws s3 cp "$ZIP_PATH" "$S3_DEPLOY" --region "$REGION" >"${EVIDENCE_DIR}/s3-deploy-upload.txt"

# Start CodeBuild image build
aws codebuild start-build \
  --project-name "$CODEBUILD_PROJECT" \
  --region "$REGION" \
  --environment-variables-override "name=IMAGE_URI,value=${IMAGE_URI},type=PLAINTEXT" "name=TFE_GIT_COMMIT_SHA,value=${GIT_COMMIT_SHA},type=PLAINTEXT" \
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

# Register new task definition with new image and deployment provenance env.
jq \
  --arg IMAGE "$IMAGE_URI" \
  --arg FILTER_SOURCE "$SCREENER_FILTER_SOURCE_BASE_URL" \
  --arg GIT_COMMIT_SHA "$GIT_COMMIT_SHA" \
  --arg SOURCE_ARCHIVE "$S3_ARCHIVE" \
  --arg SOURCE_DEPLOY "$S3_DEPLOY" \
  --arg DEPLOY_IMAGE_TAG "$IMAGE_TAG" \
  --arg DEPLOY_IMAGE_URI "$IMAGE_URI" \
  --arg DEPLOY_TS "$TS_ISO" \
  '.taskDefinition
  | del(.taskDefinitionArn,.revision,.status,.requiresAttributes,.compatibilities,.registeredAt,.registeredBy)
  | .containerDefinitions[0].image = $IMAGE
  | .containerDefinitions[0].environment = (
      (.containerDefinitions[0].environment // [])
      | map(select(
          .name != "TFE_GIT_COMMIT_SHA"
          and .name != "TFE_SOURCE_ARCHIVE_S3"
          and .name != "TFE_SOURCE_DEPLOY_S3"
          and .name != "TFE_DEPLOY_IMAGE_TAG"
          and .name != "TFE_DEPLOY_IMAGE_URI"
          and .name != "TFE_DEPLOY_TIMESTAMP_UTC"
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
      | . + (if ($FILTER_SOURCE | length) > 0 then
          [{name: "TFE_SCREENER_FILTER_SOURCE_BASE_URL", value: $FILTER_SOURCE}]
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
ENV

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
recommendation_acceptance_gate	true
recommendation_acceptance_mapped_rows	${ACCEPTANCE_MAPPED_ROWS}
recommendation_acceptance_mismatch_count	${ACCEPTANCE_MISMATCH_COUNT}
recommendation_acceptance_report	${ACCEPTANCE_GATE_REPORT}
strict_gate_typescript	pass
strict_gate_eslint_enabled	${STRICT_GATE_ESLINT_ENABLED}
strict_gate_eslint	${STRICT_GATE_ESLINT_RESULT}
strict_gate_web_build_enabled	${STRICT_GATE_WEB_BUILD_ENABLED}
strict_gate_web_build	${STRICT_GATE_WEB_BUILD_RESULT}
strict_gate_cache_coverage_report	${CACHE_GATE_REPORT}
strict_gate_cache_min_ratio	${STRICT_GATE_MIN_CACHE_POSITIVE_RATIO}
strict_gate_cache_max_missing	${STRICT_GATE_MAX_CACHE_MISSING}
strict_gate_runtime_validation_mode	${STRICT_GATE_VALIDATION_MODE}
strict_gate_runtime_validation_path	${STRICT_GATE_VALIDATION_PATH}
strict_gate_runtime_validation	${STRICT_GATE_VALIDATION_RESULT}
strict_gate_runtime_validation_reason	${STRICT_GATE_VALIDATION_REASON}
strict_gate_site_reliability_enabled	${STRICT_GATE_SITE_RELIABILITY_ENABLED}
strict_gate_site_reliability	${STRICT_GATE_SITE_RELIABILITY_RESULT}
strict_gate_site_reliability_reason	${STRICT_GATE_SITE_RELIABILITY_REASON}
strict_gate_site_reliability_report	${SITE_RELIABILITY_GATE_REPORT}
TSV

echo "./backups/deploy-evidence-${TS}" >"${REPO_ROOT}/backups/CURRENT_DEPLOY_EVIDENCE_POINTER.txt"

echo "DEPLOY_EVIDENCE_DIR=${EVIDENCE_DIR}"
echo "GIT_COMMIT_SHA=${GIT_COMMIT_SHA}"
echo "BUILD_ID=${BUILD_ID}"
echo "NEW_TASKDEF=${NEW_TASKDEF}"
echo "POST_IMAGE=${POST_IMAGE}"
