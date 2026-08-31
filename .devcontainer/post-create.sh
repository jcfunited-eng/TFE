#!/usr/bin/env bash
set -euo pipefail

if [ -f /mnt/tfebackup/root-claude.json ] \
    && ! python3 -c 'import json,sys; sys.exit(0 if "projects" in json.load(open("/root/.claude.json")) else 1)' 2>/dev/null; then
    cp /mnt/tfebackup/root-claude.json /root/.claude.json
fi

workspace_root=/workspaces/Tao_Financial_Engine
native_manifest="${workspace_root}/native/guala_core/Cargo.toml"
native_build_dir=$(mktemp -d /tmp/guala-native-wheel-XXXXXX)
cleanup_native_build() {
    rm -rf -- "${native_build_dir}"
}
trap cleanup_native_build EXIT

maturin build \
    --release \
    --manifest-path "${native_manifest}" \
    --out "${native_build_dir}"

shopt -s nullglob
native_wheels=("${native_build_dir}"/*.whl)
if [ "${#native_wheels[@]}" -ne 1 ]; then
    echo "expected exactly one native Guala wheel" >&2
    exit 1
fi
pip install --no-cache-dir --force-reinstall "${native_wheels[0]}"
python3 -c 'import guala_core; print("native Guala core installed")'
