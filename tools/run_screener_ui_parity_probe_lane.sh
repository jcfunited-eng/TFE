#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspaces/Tao_Financial_Engine"
BASE_URL="${TFE_BASE_URL:-https://taofinancialengine.com}"
CLUSTER="${TFE_ECS_CLUSTER:-tfe-web-cluster}"
SERVICE="${TFE_ECS_SERVICE:-tfe-web-service-lb}"
REGION="${AWS_REGION:-us-east-1}"

TS="$(date -u +%Y%m%d%H%M%S)"
OUT_DIR="$ROOT/backups/runtime/screener-ui-parity-probe-${TS}Z"
mkdir -p "$OUT_DIR"

# Important: auth path lowercases username input in-app; temp users must be lowercase.
USERNAME="codex_screener_ui_${TS}"
PASSWORD="codexprobe_${TS}"

PASSWORD_HASH="$(python3 - <<'PY' "$PASSWORD"
import base64
import hashlib
import secrets
import sys

pw = sys.argv[1].encode('utf-8')
salt = secrets.token_bytes(16)
digest = hashlib.pbkdf2_hmac('sha256', pw, salt, 210000)
enc = lambda b: base64.urlsafe_b64encode(b).decode('ascii')
print(f"pbkdf2_sha256$210000${enc(salt)}${enc(digest)}")
PY
)"

CREATE_COMMAND_JSON="$(python3 - <<'PY' "$USERNAME" "$PASSWORD_HASH"
import json
import sys

username = sys.argv[1]
password_hash = sys.argv[2]
cmd = f"""set -euo pipefail
cat >/tmp/codex_create_user.sql <<'SQL'
INSERT INTO tfe_users (username,password_hash,role,is_active,is_test_user,access_expires_at,created_at)
VALUES ('{username}','{password_hash}','admin',TRUE,TRUE,NOW() + interval '1 day',NOW())
ON CONFLICT (username) DO UPDATE
SET password_hash=EXCLUDED.password_hash,
    role=EXCLUDED.role,
    is_active=TRUE,
    is_test_user=TRUE,
    access_expires_at=EXCLUDED.access_expires_at;
SQL
psql -v ON_ERROR_STOP=1 -X -w -f /tmp/codex_create_user.sql
echo '{{"status":"pass","pass":true,"username":"{username}","action":"created"}}'"""
print(json.dumps(["bash", "-lc", cmd]))
PY
)"

python3 "$ROOT/tools/run_validation_gate_v1_in_ecs_network.py" \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --region "$REGION" \
  --command-json "$CREATE_COMMAND_JSON" \
  > "$OUT_DIR/user-create.json"

set +e
node "$ROOT/web/scripts/screener_ui_parity_probe.mjs" \
  --baseUrl "$BASE_URL" \
  --username "$USERNAME" \
  --password "$PASSWORD" \
  --outDir "$OUT_DIR" \
  > "$OUT_DIR/check.stdout" 2> "$OUT_DIR/check.stderr"
PROBE_EXIT_CODE=$?
set -e

DELETE_COMMAND_JSON="$(python3 - <<'PY' "$USERNAME"
import json
import sys

username = sys.argv[1]
cmd = f"""set -euo pipefail
cat >/tmp/codex_delete_user.sql <<'SQL'
DELETE FROM tfe_users WHERE username='{username}';
SQL
psql -v ON_ERROR_STOP=1 -X -w -f /tmp/codex_delete_user.sql
echo '{{"status":"pass","pass":true,"username":"{username}","action":"deleted"}}'"""
print(json.dumps(["bash", "-lc", cmd]))
PY
)"

python3 "$ROOT/tools/run_validation_gate_v1_in_ecs_network.py" \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --region "$REGION" \
  --command-json "$DELETE_COMMAND_JSON" \
  > "$OUT_DIR/user-delete.json"

python3 - <<'PY' "$OUT_DIR" "$PROBE_EXIT_CODE"
import datetime
import json
import os
import sys

out_dir = sys.argv[1]
probe_exit_code = int(sys.argv[2])
check_summary_path = os.path.join(out_dir, 'check-summary.json')
status = 'error'
screenshots = {}

if os.path.exists(check_summary_path):
    with open(check_summary_path, 'r', encoding='utf-8') as fh:
        check_summary = json.load(fh)
    status = str(check_summary.get('status') or 'unknown')
    screenshots = check_summary.get('screenshots') or {}

lane_summary = {
    'generated_at_utc': datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
    'status': status if probe_exit_code == 0 else ('error' if status == 'running' else status),
    'probe_exit_code': probe_exit_code,
    'check_summary_path': check_summary_path,
    'screenshots': screenshots,
}

with open(os.path.join(out_dir, 'lane-summary.json'), 'w', encoding='utf-8') as fh:
    json.dump(lane_summary, fh, indent=2)

print(out_dir)
PY
