#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${1:-${REPO_ROOT}/dsf_ai_service/static}"
GIT_SHA="${2:-$(git -C "${REPO_ROOT}" rev-parse HEAD)}"
AWS_REGION="${AWS_REGION:-us-east-1}"
S3_SITE_BUCKET="${DSF_AI_SITE_BUCKET:-dsf-ai-site}"
CF_DIST_ID="${DSF_AI_CLOUDFRONT_DISTRIBUTION_ID:-E17JT9XGBFU493}"
PUBLISH_MODE="${DSF_AI_STATIC_PUBLISH_MODE:-apply}"

if [[ ! "${GIT_SHA}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Static publication refused: Git identity must be a full lowercase SHA." >&2
  exit 1
fi
if [ ! -d "${SOURCE_DIR}" ]; then
  echo "Static publication refused: source directory is missing: ${SOURCE_DIR}" >&2
  exit 1
fi
for required in index.html app.js style.css legal.html robots.txt sitemap.xml; do
  if [ ! -f "${SOURCE_DIR}/${required}" ]; then
    echo "Static publication refused: required source is missing: ${required}" >&2
    exit 1
  fi
done

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT
MANIFEST_PATH="${WORK_DIR}/site-manifest.json"
OBJECT_LIST_PATH="${WORK_DIR}/objects.tsv"
RECEIPT_DIR="${REPO_ROOT}/backups"
PUBLISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RECEIPT_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RECEIPT_PATH="${RECEIPT_DIR}/dsf-ai-static-publication-${RECEIPT_STAMP}.json"
mkdir -p "${RECEIPT_DIR}"

python3 - "${SOURCE_DIR}" "${GIT_SHA}" "${MANIFEST_PATH}" "${OBJECT_LIST_PATH}" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

source = Path(sys.argv[1]).resolve()
git_sha = sys.argv[2]
manifest_path = Path(sys.argv[3])
object_list_path = Path(sys.argv[4])
root_objects = {"index.html", "robots.txt", "sitemap.xml"}
objects = []

for path in sorted(item for item in source.rglob("*") if item.is_file()):
    relative = path.relative_to(source).as_posix()
    key = relative if relative in root_objects else f"static/{relative}"
    payload = path.read_bytes()
    objects.append({
        "source": relative,
        "s3_key": key,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    })

manifest = {
    "schema": "dsf-ai-static-publication-manifest-v1",
    "git_commit_sha": git_sha,
    "object_count": len(objects),
    "objects": objects,
}
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
with object_list_path.open("w", encoding="utf-8") as stream:
    for item in objects:
        stream.write(f"{item['source']}\t{item['s3_key']}\t{item['bytes']}\t{item['sha256']}\n")
PY

if [ "${PUBLISH_MODE}" = "dry-run" ]; then
  python3 -m json.tool "${MANIFEST_PATH}"
  exit 0
fi
if [ "${PUBLISH_MODE}" != "apply" ]; then
  echo "Static publication refused: DSF_AI_STATIC_PUBLISH_MODE must be apply or dry-run." >&2
  exit 1
fi

aws s3 sync "${SOURCE_DIR}/" "s3://${S3_SITE_BUCKET}/static/" \
  --region "${AWS_REGION}" \
  --delete \
  --exclude "index.html" \
  --exclude "robots.txt" \
  --exclude "sitemap.xml" \
  --cache-control "no-cache, must-revalidate"

for root_object in index.html robots.txt sitemap.xml; do
  aws s3 cp "${SOURCE_DIR}/${root_object}" "s3://${S3_SITE_BUCKET}/${root_object}" \
    --region "${AWS_REGION}" \
    --cache-control "no-cache, must-revalidate" \
    --only-show-errors
done

aws s3 cp "${MANIFEST_PATH}" "s3://${S3_SITE_BUCKET}/static/site-manifest.json" \
  --region "${AWS_REGION}" \
  --cache-control "no-cache, must-revalidate" \
  --content-type "application/json" \
  --only-show-errors

while IFS=$'\t' read -r source_name s3_key expected_bytes expected_sha; do
  received_path="${WORK_DIR}/received"
  aws s3 cp "s3://${S3_SITE_BUCKET}/${s3_key}" "${received_path}" \
    --region "${AWS_REGION}" \
    --only-show-errors
  actual_bytes="$(wc -c < "${received_path}" | tr -d ' ')"
  actual_sha="$(sha256sum "${received_path}" | awk '{print $1}')"
  if [ "${actual_bytes}" != "${expected_bytes}" ] || [ "${actual_sha}" != "${expected_sha}" ]; then
    echo "Static publication receipt failed: ${source_name} -> ${s3_key}" >&2
    exit 1
  fi
done < "${OBJECT_LIST_PATH}"

INVALIDATION_ID="$(aws cloudfront create-invalidation \
  --distribution-id "${CF_DIST_ID}" \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)"
aws cloudfront wait invalidation-completed \
  --distribution-id "${CF_DIST_ID}" \
  --id "${INVALIDATION_ID}"

python3 - "${MANIFEST_PATH}" "${RECEIPT_PATH}" "${PUBLISHED_AT}" "${INVALIDATION_ID}" "${S3_SITE_BUCKET}" <<'PY'
import json
from pathlib import Path
import sys

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
receipt = {
    "schema": "dsf-ai-static-publication-receipt-v1",
    "published_at_utc": sys.argv[3],
    "bucket": sys.argv[5],
    "manifest_key": "static/site-manifest.json",
    "cloudfront_invalidation_id": sys.argv[4],
    "verified_object_count": manifest["object_count"],
    "git_commit_sha": manifest["git_commit_sha"],
}
Path(sys.argv[2]).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(receipt, sort_keys=True))
PY
