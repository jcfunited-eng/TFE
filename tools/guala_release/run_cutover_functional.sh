#!/usr/bin/env bash
# Feeding release: controller dry-run, cutover, page publish, caretaker restart — in that
# order, each gated on the previous. Run only after the container proof verdict feed_pass=true.
set -euo pipefail
export AWS_PAGER=""
S=/tmp/claude-0/-workspaces-Tao-Financial-Engine/31887e43-e4d7-4bda-9b45-055ce99d3aa8/scratchpad
W=/tmp/guala-vision-c1
STAGE=${1:?stage: dry-run|cutover|page|caretaker}
DIGEST=$(cat "$S/digest.txt"); BACKUP=${BACKUP:-$S/live-capture-0914e/current.zip}
cd "$W"
test -z "$(git status --porcelain=v1 --untracked-files=all)" || { echo "worktree not clean"; exit 1; }
test "$(git rev-parse HEAD)" = "$(cat "$S/release-sha.txt")" || { echo "HEAD is not the release revision"; exit 1; }
case "$STAGE" in
  dry-run)
    python3 -c "import json;v=json.load(open('$S/proof-functional-out/verdict.json'));assert v.get('feed_pass') is True, v;print('proof verdict: pass')"
    timeout 900 bash tools/deploy_dsf_ai.sh --dry-run "$DIGEST" "$BACKUP" > "$S/controller-dry-run-functional.log" 2>&1; EXIT=$?
    echo "dry-run exit $EXIT"; cut -c1-500 "$S/controller-dry-run-functional.log" | tail -n 6; exit $EXIT
    ;;
  cutover)
    grep -q "dry-run exit 0" "$S/controller-dry-run-functional.log" 2>/dev/null || grep -q '"mode": "--dry-run"' "$S/controller-dry-run-functional.log" || { echo "no passing dry-run on record"; exit 1; }
    timeout 1500 bash tools/deploy_dsf_ai.sh --cutover "$DIGEST" "$BACKUP" > "$S/controller-cutover-functional.log" 2>&1; EXIT=$?
    echo "cutover exit $EXIT"; cut -c1-700 "$S/controller-cutover-functional.log" | tail -n 8; exit $EXIT
    ;;
  page)
    LOCAL=$(sha256sum dsf_ai_service/static/gualaloom.html | cut -d' ' -f1)
    STAMP=$(date -u +%Y%m%dT%H%M%SZ); aws s3 cp s3://dsf-ai-site/gualaloom.html "s3://dsf-ai-site-backups/static-page-backups/gualaloom-$STAMP.html" --only-show-errors && echo "page backed up: gualaloom-$STAMP.html"
    STAMP=$(date -u +%Y%m%dT%H%M%SZ); aws s3 cp s3://dsf-ai-site/gualaloom.html "s3://dsf-ai-site-backups/static-page-backups/gualaloom-$STAMP.html" --only-show-errors && echo "page backed up: gualaloom-$STAMP.html"
    aws s3 cp dsf_ai_service/static/gualaloom.html s3://dsf-ai-site/gualaloom.html --content-type "text/html; charset=utf-8" --cache-control "no-cache,max-age=0,must-revalidate" --only-show-errors
    INV=$(aws cloudfront create-invalidation --distribution-id E17JT9XGBFU493 --paths "/gualaloom.html" --query 'Invalidation.Id' --output text); echo "invalidation: $INV"
    aws cloudfront wait invalidation-completed --distribution-id E17JT9XGBFU493 --id "$INV"; echo "invalidation completed"
    SERVED=$(curl -s "https://dsf-ai.com/gualaloom.html?nocache=$(date +%s)" | sha256sum | cut -d' ' -f1)
    echo "served sha256: $SERVED"; [ "$SERVED" = "$LOCAL" ] && echo "LIVE PAGE == COMMITTED PAGE" || { echo "MISMATCH"; exit 1; }
    ;;
  caretaker)
    C=/workspaces/Tao_Financial_Engine/guala_caretaker
    OLD=$(pgrep -f "python3 caretaker.py" | head -1 || true); echo "old caretaker pid: ${OLD:-none}"
    touch "$C/STOP"; for i in $(seq 1 30); do pgrep -f "python3 caretaker.py" >/dev/null || break; sleep 5; done
    pgrep -f "python3 caretaker.py" >/dev/null && { echo "caretaker still running; sending TERM"; pkill -TERM -f "python3 caretaker.py"; sleep 5; }
    rm -f "$C/STOP"
    cd "$C" && nohup python3 caretaker.py >> caretaker.out 2>&1 &
    sleep 3; echo "new caretaker pid: $(pgrep -f 'python3 caretaker.py' | head -1)"; tail -3 "$C/caretaker.log"
    ;;
esac
