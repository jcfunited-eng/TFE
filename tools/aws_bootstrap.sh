#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  tools/aws_bootstrap.sh --device <block-device> [options]

Required:
  --device <path>              EBS block device (example: /dev/nvme1n1)

Options:
  --mount-root <path>          Mount root (default: /data/tfe)
  --fs-type <ext4|xfs>         Filesystem type for initial format (default: ext4)
  --repo-source <path>         Optional source path to rsync into <mount-root>/repo
  --requirements-file <path>   Optional pip requirements file
  --skip-python-deps           Skip python dependency install
  --bootstrap-manifest <path>  Explicit output path for bootstrap manifest json
  --help                       Show this help
USAGE
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

DEVICE=""
MOUNT_ROOT="/data/tfe"
FS_TYPE="ext4"
REPO_SOURCE=""
REQUIREMENTS_FILE=""
SKIP_PY_DEPS=0
BOOTSTRAP_MANIFEST=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device)
      DEVICE="${2:-}"
      shift 2
      ;;
    --mount-root)
      MOUNT_ROOT="${2:-}"
      shift 2
      ;;
    --fs-type)
      FS_TYPE="${2:-}"
      shift 2
      ;;
    --repo-source)
      REPO_SOURCE="${2:-}"
      shift 2
      ;;
    --requirements-file)
      REQUIREMENTS_FILE="${2:-}"
      shift 2
      ;;
    --skip-python-deps)
      SKIP_PY_DEPS=1
      shift
      ;;
    --bootstrap-manifest)
      BOOTSTRAP_MANIFEST="${2:-}"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "unsupported_arg:$1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ "$(id -u)" -ne 0 ]]; then
  echo "must_run_as_root" >&2
  exit 2
fi

if [[ -z "$DEVICE" ]]; then
  echo "missing_required_arg:--device" >&2
  exit 2
fi
if [[ ! -b "$DEVICE" ]]; then
  echo "device_not_block:$DEVICE" >&2
  exit 2
fi
if [[ "$FS_TYPE" != "ext4" && "$FS_TYPE" != "xfs" ]]; then
  echo "unsupported_fs_type:$FS_TYPE" >&2
  exit 2
fi

install_packages() {
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y \
      ca-certificates curl jq tmux rsync git util-linux \
      e2fsprogs xfsprogs python3 python3-pip python3-venv awscli
    return 0
  fi

  if command -v dnf >/dev/null 2>&1; then
    dnf install -y \
      ca-certificates jq tmux rsync git util-linux \
      e2fsprogs xfsprogs python3 python3-pip awscli
    return 0
  fi

  if command -v yum >/dev/null 2>&1; then
    yum install -y \
      ca-certificates jq tmux rsync git util-linux \
      e2fsprogs xfsprogs python3 python3-pip awscli
    return 0
  fi

  echo "unsupported_package_manager" >&2
  return 1
}

install_packages

existing_type="$(blkid -o value -s TYPE "$DEVICE" 2>/dev/null || true)"
if [[ -z "$existing_type" ]]; then
  if [[ "$FS_TYPE" == "ext4" ]]; then
    mkfs.ext4 -F "$DEVICE"
  else
    mkfs.xfs -f "$DEVICE"
  fi
  existing_type="$FS_TYPE"
fi

mkdir -p "$MOUNT_ROOT"

UUID_VALUE="$(blkid -o value -s UUID "$DEVICE" 2>/dev/null || true)"
if [[ -z "$UUID_VALUE" ]]; then
  echo "uuid_not_found_for_device:$DEVICE" >&2
  exit 2
fi

FSTAB_LINE="UUID=${UUID_VALUE} ${MOUNT_ROOT} ${existing_type} defaults,nofail 0 2"
if ! grep -q "UUID=${UUID_VALUE}" /etc/fstab; then
  echo "$FSTAB_LINE" >> /etc/fstab
fi

if ! mountpoint -q "$MOUNT_ROOT"; then
  mount "$MOUNT_ROOT"
fi

mkdir -p "$MOUNT_ROOT/repo" "$MOUNT_ROOT/data" "$MOUNT_ROOT/logs" "$MOUNT_ROOT/runs" "$MOUNT_ROOT/tmp"

VENV_DIR="$MOUNT_ROOT/.venv"
PYTHON_BIN="python3"
PIP_BIN="python3 -m pip"
if [[ "$SKIP_PY_DEPS" -eq 0 ]]; then
  python3 -m venv "$VENV_DIR"
  PYTHON_BIN="$VENV_DIR/bin/python"
  PIP_BIN="$VENV_DIR/bin/pip"
fi

ENV_FILE="/etc/profile.d/tfe_env.sh"
cat > "$ENV_FILE" <<ENVEOF
export TFE_ROOT="${MOUNT_ROOT}"
export TFE_REPO_ROOT="${MOUNT_ROOT}/repo"
export TFE_DATA_ROOT="${MOUNT_ROOT}/data"
export TFE_LOG_ROOT="${MOUNT_ROOT}/logs"
export TFE_RUN_ROOT="${MOUNT_ROOT}/runs"
export TMPDIR="${MOUNT_ROOT}/tmp"
export TFE_VENV="${VENV_DIR}"
if [ -d "${VENV_DIR}" ]; then
  export VIRTUAL_ENV="${VENV_DIR}"
  case ":\$PATH:" in
    *":${VENV_DIR}/bin:"*) ;;
    *) export PATH="${VENV_DIR}/bin:\$PATH" ;;
  esac
fi
ENVEOF
chmod 0644 "$ENV_FILE"

export TFE_ROOT="$MOUNT_ROOT"
export TFE_REPO_ROOT="$MOUNT_ROOT/repo"
export TFE_DATA_ROOT="$MOUNT_ROOT/data"
export TFE_LOG_ROOT="$MOUNT_ROOT/logs"
export TFE_RUN_ROOT="$MOUNT_ROOT/runs"
export TMPDIR="$MOUNT_ROOT/tmp"
export TFE_VENV="$VENV_DIR"

if [[ -n "$REPO_SOURCE" ]]; then
  if [[ ! -d "$REPO_SOURCE" ]]; then
    echo "repo_source_not_found:$REPO_SOURCE" >&2
    exit 2
  fi
  rsync -a --delete "$REPO_SOURCE"/ "$MOUNT_ROOT/repo"/
fi

if [[ -z "$REQUIREMENTS_FILE" && -f "$MOUNT_ROOT/repo/requirements-aws.txt" ]]; then
  REQUIREMENTS_FILE="$MOUNT_ROOT/repo/requirements-aws.txt"
fi

if [[ "$SKIP_PY_DEPS" -eq 0 ]]; then
  "$PIP_BIN" install --upgrade pip wheel
  if [[ -n "$REQUIREMENTS_FILE" ]]; then
    if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
      echo "requirements_file_not_found:$REQUIREMENTS_FILE" >&2
      exit 2
    fi
    "$PIP_BIN" install -r "$REQUIREMENTS_FILE"
  else
    "$PIP_BIN" install numpy pandas requests python-dotenv
  fi
  PYTHON_BIN="$VENV_DIR/bin/python"
  PIP_BIN="$VENV_DIR/bin/pip"
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -z "$BOOTSTRAP_MANIFEST" ]]; then
  BOOTSTRAP_MANIFEST="$MOUNT_ROOT/logs/bootstrap_manifest_${TS}.json"
fi
mkdir -p "$(dirname "$BOOTSTRAP_MANIFEST")"

SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_HASH="$(sha256sum "$SCRIPT_PATH" | awk '{print $1}')"
DISK_BYTES="$(df -B1 --output=avail "$MOUNT_ROOT" | tail -n 1 | tr -d ' ')"
MEM_TOTAL_KB="$(awk '/MemTotal:/ {print $2}' /proc/meminfo | head -n 1)"
PYTHON_VERSION="$($PYTHON_BIN --version 2>/dev/null | awk '{print $2}')"
PIP_VERSION="$($PIP_BIN --version 2>/dev/null | awk '{print $2}')"
DF_H="$(df -h "$MOUNT_ROOT" | tail -n 1)"
FREE_H="$(free -h | tr '\n' ';')"

export BOOTSTRAP_MANIFEST SCRIPT_PATH SCRIPT_HASH DEVICE MOUNT_ROOT existing_type UUID_VALUE REPO_SOURCE REQUIREMENTS_FILE SKIP_PY_DEPS DISK_BYTES MEM_TOTAL_KB PYTHON_VERSION PIP_VERSION DF_H FREE_H TS PYTHON_BIN VENV_DIR

"$PYTHON_BIN" - <<'PY'
import importlib.metadata
import json
import os
from datetime import datetime, timezone
from pathlib import Path

manifest_path = Path(os.environ["BOOTSTRAP_MANIFEST"])

def pkg_version(name: str):
    try:
        return importlib.metadata.version(name)
    except Exception:
        return None

payload = {
    "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "analysis": "aws_bootstrap",
    "inputs": {
      "device": os.environ["DEVICE"],
      "mount_root": os.environ["MOUNT_ROOT"],
      "filesystem_type": os.environ["existing_type"],
      "uuid": os.environ["UUID_VALUE"],
      "repo_source": os.environ["REPO_SOURCE"] or None,
      "requirements_file": os.environ["REQUIREMENTS_FILE"] or None,
      "skip_python_deps": bool(int(os.environ["SKIP_PY_DEPS"])),
    },
    "environment": {
      "TFE_ROOT": os.environ["MOUNT_ROOT"],
      "TFE_REPO_ROOT": os.environ["MOUNT_ROOT"] + "/repo",
      "TFE_DATA_ROOT": os.environ["MOUNT_ROOT"] + "/data",
      "TFE_LOG_ROOT": os.environ["MOUNT_ROOT"] + "/logs",
      "TFE_RUN_ROOT": os.environ["MOUNT_ROOT"] + "/runs",
      "TMPDIR": os.environ["MOUNT_ROOT"] + "/tmp",
      "TFE_VENV": os.environ["VENV_DIR"],
    },
    "verifications": {
      "disk_available_bytes": int(float(os.environ["DISK_BYTES"])),
      "memory_total_kb": int(float(os.environ["MEM_TOTAL_KB"])),
      "python_bin": os.environ["PYTHON_BIN"],
      "python_version": os.environ["PYTHON_VERSION"] or None,
      "pip_version": os.environ["PIP_VERSION"] or None,
      "package_versions": {
        "numpy": pkg_version("numpy"),
        "pandas": pkg_version("pandas"),
        "requests": pkg_version("requests"),
        "python-dotenv": pkg_version("python-dotenv"),
      },
      "df_h_line": os.environ["DF_H"],
      "free_h": os.environ["FREE_H"],
    },
    "bootstrap_script": {
      "path": os.environ["SCRIPT_PATH"],
      "sha256": os.environ["SCRIPT_HASH"],
    },
    "outputs": {
      "manifest_json": str(manifest_path),
      "manifest_latest_json": str(manifest_path.parent / "bootstrap_manifest_latest.json"),
      "profile_env_file": "/etc/profile.d/tfe_env.sh",
      "created_directories": [
        os.environ["MOUNT_ROOT"] + "/repo",
        os.environ["MOUNT_ROOT"] + "/data",
        os.environ["MOUNT_ROOT"] + "/logs",
        os.environ["MOUNT_ROOT"] + "/runs",
        os.environ["MOUNT_ROOT"] + "/tmp",
      ],
    },
}

manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
latest = manifest_path.parent / "bootstrap_manifest_latest.json"
latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
PY

echo "$BOOTSTRAP_MANIFEST"
echo "$MOUNT_ROOT/logs/bootstrap_manifest_latest.json"
