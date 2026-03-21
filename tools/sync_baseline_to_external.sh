#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="/workspaces/Tao_Financial_Engine"
LOG_PATH="${REPO_ROOT}/backups/external-sync-last.log"
{
  echo "timestamp_utc=$(date -u +%Y%m%dT%H%M%SZ)"
  if [ ! -d "/mnt/tfebackup" ]; then
    echo "status=mount_not_available"
    exit 0
  fi

  POINTER_PATH="${REPO_ROOT}/backups/CURRENT_BASELINE_POINTER.txt"
  if [ ! -f "${POINTER_PATH}" ]; then
    echo "status=baseline_pointer_missing"
    exit 1
  fi

  SRC_REL="$(sed -n '1p' "${POINTER_PATH}" | tr -d '\r')"
  SRC_PATH="${REPO_ROOT}/${SRC_REL#./}"
  if [ ! -d "${SRC_PATH}" ]; then
    echo "status=baseline_path_missing"
    echo "baseline_path=${SRC_PATH}"
    exit 1
  fi

  DEST_ROOT="/mnt/tfebackup/TFE_Baselines"
  mkdir -p "${DEST_ROOT}"
  DEST_PATH="${DEST_ROOT}/$(basename "${SRC_PATH}")"
  if [ -e "${DEST_PATH}" ]; then
    DEST_PATH="${DEST_ROOT}/$(basename "${SRC_PATH}")-copy-$(date -u +%Y%m%dT%H%M%SZ)"
  fi

  cp -a "${SRC_PATH}" "${DEST_PATH}"

  if [ -f "${DEST_PATH}/checksums.sha256" ]; then
    (
      cd "${REPO_ROOT}"
      sha256sum -c "${DEST_PATH}/checksums.sha256" >/dev/null
    )
    echo "checksums=ok"
  else
    echo "checksums=missing"
  fi

  if [ -f "${DEST_PATH}/tarball.sha256" ]; then
    (
      cd "${REPO_ROOT}"
      sha256sum -c "${DEST_PATH}/tarball.sha256" >/dev/null
    )
    echo "tarball_checksum=ok"
  else
    echo "tarball_checksum=missing"
  fi

  echo "status=copied"
  echo "source=${SRC_PATH}"
  echo "destination=${DEST_PATH}"
} >"${LOG_PATH}" 2>&1
