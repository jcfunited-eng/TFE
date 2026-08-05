#!/usr/bin/env bash
# D4: Restore drill — pull latest S3 backup, boot local read-only Guala, verify
# Usage: ./tools/guala_restore_drill.sh
set -euo pipefail

echo "═══════════════════════════════════════════"
echo "  GualaLoom Restore Drill"
echo "═══════════════════════════════════════════"

S3_BUCKET="dsf-ai-site-backups"
S3_PREFIX="guala/"

# Find latest backup prefix
echo "[1/4] Finding latest S3 backup..."
LATEST=$(aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}" | sort | tail -1 | awk '{print $NF}')
if [ -z "${LATEST}" ]; then
    echo "ERROR: No backups found in s3://${S3_BUCKET}/${S3_PREFIX}"
    exit 1
fi
S3_FULL="s3://${S3_BUCKET}/${S3_PREFIX}${LATEST}"
echo "  Latest: ${S3_FULL}"

# Download to temp dir
DRILL_DIR=$(mktemp -d)
trap "rm -rf ${DRILL_DIR}" EXIT
echo "[2/4] Downloading to ${DRILL_DIR}..."
aws s3 sync "${S3_FULL}" "${DRILL_DIR}/" --quiet
echo "  Files:"
ls -la "${DRILL_DIR}/"

# Boot local Guala and verify
echo "[3/4] Booting local Guala from backup..."
python3 << PYEOF
import sys, json, os
sys.path.insert(0, '.')
os.environ['DECAY_PAUSED'] = '1'  # safety

from dsf_ai_service.v4.gualaloom_v5_engine import Guala

g = Guala()
state_dir = "${DRILL_DIR}"
g.load_full_state(state_dir)
s = g.introspect()

identity = g._guala_identity or "none"
vocab = s["vocab"]
tick = g.tick
atlas = s["atlas_entries"]
deep = s["deep_atlas"]["n_entries"]

print()
print("RESTORED STATE:")
print(f"  identity: {identity}")
print(f"  vocab:    {vocab}")
print(f"  tick:     {tick}")
print(f"  atlas:    {atlas} entries")
print(f"  deep:     {deep} entries")

# Assertions
errors = []
if not identity.startswith("cdef9bcf"):
    errors.append(f"identity mismatch: {identity}")
if vocab < 2352:
    errors.append(f"vocab too low: {vocab} < 2352")
if tick < 1_000_000:
    errors.append(f"tick too low: {tick}")

print()
if errors:
    print("DRILL FAILED:")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
else:
    print("DRILL PASSED:")
    print(f"  ✓ identity = cdef9bcf...")
    print(f"  ✓ vocab = {vocab} (≥ 2352)")
    print(f"  ✓ tick = {tick}")
    print(f"  ✓ atlas = {atlas} entries")
    print(f"  ✓ deep = {deep} entries")
PYEOF

echo "[4/4] Drill complete."
