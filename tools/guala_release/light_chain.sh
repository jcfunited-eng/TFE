#!/usr/bin/env bash
# The release chain (C1, 2026-09-16), for A1 from here on: suites in the clean worktree,
# package, image, push, fresh capture, proof (feeding, home, ear, voice, cold restart exact,
# things and windows), controller dry-run, cutover at a true boundary (a lesson complete,
# then 40 s with no reading/music beginning), live check.
#   REV=<sha on c1/drive-organ> DECLARED=<declared things> bash tools/guala_release/light_chain.sh
#   FROM=suites|package|push|dry-run (where to start)   UNTIL=dry-run (prove and stage, hold the cutover)
#   GUALA_RELEASE_WORK (captures, logs, proof output; default /tmp/guala-release-work)
#   GUALA_RELEASE_TREE (a clean detached worktree of the repo; created if missing)
# Before: aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 418384447921.dkr.ecr.us-east-1.amazonaws.com
set -u
S=${GUALA_RELEASE_WORK:-/tmp/guala-release-work}; mkdir -p "$S"; export GUALA_RELEASE_WORK="$S"
W=${GUALA_RELEASE_TREE:-/tmp/guala-release-tree}
REPO=${GUALA_REPO:-/workspaces/Tao_Financial_Engine}
[ -e "$W/.git" ] || git -C "$REPO" worktree add --detach "$W" origin/c1/drive-organ
REV=${REV:?release revision}
LOG=/workspaces/Tao_Financial_Engine/guala_caretaker/caretaker.log
export AWS_PAGER=""
stamp() { date -u +%H:%M:%SZ; }

git -C $W fetch -q origin c1/drive-organ && git -C $W checkout -q --detach "$REV" && git -C $W log --oneline -1 | cut -c1-100 && git -C $W rev-parse HEAD > $S/light-release-sha.txt || { echo "CHECKOUT FAILED"; exit 1; }

FROM=${FROM:-suites}
if [ "$FROM" = suites ]; then
echo "=== suites in the clean worktree $(stamp) ==="
timeout 900 python3 -c "
import os, sys; os.chdir('$W'); sys.path.insert(0, '$W'); import pytest
sys.exit(pytest.main(['-q', '-p', 'no:cacheprovider', '--tb=short', 'tests/test_guala_home_renovation.py', 'tests/test_guala_world_light.py', 'tests/test_guala_home_world.py', 'tests/test_guala_world_sensorium.py', 'tests/test_guala_functional_organism.py', 'tests/test_guala_acoustic_gate.py']))" 2>&1 | grep -E "passed|failed|^FAILED" | cut -c1-200 | tee $S/light-suites.txt
grep -q " failed" $S/light-suites.txt && { echo "SUITES FAILED"; exit 1; }
fi

for st in package image push; do
  case "$FROM:$st" in push:package|push:image|dry-run:*) echo "=== $st skipped (FROM=$FROM) ==="; continue;; esac
  echo "=== $st $(stamp) ==="
  timeout 1500 bash $W/tools/guala_release/release_stage.sh $st > $S/stage-$st.log 2>&1 || { echo "STAGE $st FAILED"; tail -5 $S/stage-$st.log | cut -c1-200; exit 1; }
  tail -3 $S/stage-$st.log | cut -c1-160
done

if [ "$FROM" != dry-run ]; then
echo "=== capture 0916c $(stamp) ==="
NAME=pre S=$S timeout 500 bash $W/tools/guala_release/capture_cmd.sh 2>&1 | tee $S/capture-pre.log; grep -o '"tick": [0-9]*' $S/capture-pre.log | head -1 || true
test -s $S/live-capture-pre/current.zip || { echo "CAPTURE FAILED"; exit 1; }

echo "=== proof $(stamp) ==="
CAPTURE=$S/live-capture-pre/current.zip timeout 1500 bash $W/tools/guala_release/release_stage.sh proof > $S/stage-proof.log 2>&1
grep -E "container exit|feed_proof_error" $S/stage-proof.log | cut -c1-200
python3 - <<'EOF' || exit 1
import json, sys, os
D = int(os.environ.get("DECLARED", "52"))
S = os.environ["GUALA_RELEASE_WORK"]
v = json.load(open(f"{S}/proof-functional-out/verdict.json"))
wa = v.get("world_after") or {}; wc = v.get("world_post_cold") or {}
print("proof:", {k: v.get(k) for k in ("feed_pass","fed_ok","home_ok","doors_reached","ear_pass","voice_pass","cold_restart_exact","mean_seconds","worst_seconds","body_bytes_max","world_bytes_max","restore_seconds","cold_restore_seconds")})
print("world after:", {k: wa.get(k) for k in ("things","renovated","paint","windows","room")}, "| post cold:", {k: wc.get(k) for k in ("things","renovated","paint","windows")})
ok = v.get("feed_pass") and (wa.get("things") or 0) >= D and (wa.get("windows") or 0) >= 4 and (wc.get("things") or 0) >= D
print("proof verdict:", "pass" if ok else "FAIL"); sys.exit(0 if ok else 1)
EOF
fi

echo "=== dry-run $(stamp) ==="
BACKUP=$S/live-capture-pre/current.zip timeout 900 bash $W/tools/guala_release/cutover_stage.sh dry-run 2>&1 | tail -3 | cut -c1-200
grep -q "dry-run exit 0" $S/controller-dry-run-functional.log 2>/dev/null || grep -q '"mode": "--dry-run"' $S/controller-dry-run-functional.log || { echo "DRY-RUN NOT CLEAN"; tail -3 $S/controller-dry-run-functional.log | cut -c1-200; exit 1; }

if [ "${UNTIL:-}" = dry-run ]; then echo "=== staged through the proof and dry-run; the cutover is held $(stamp) ==="; exit 0; fi

echo "=== waiting for a true boundary $(stamp) ==="
deadline=$(( $(date -u +%s) + 2400 ))
while :; do
  n0=$(grep -c "complete; quiet until" $LOG)
  while [ "$(grep -c "complete; quiet until" $LOG)" -le "$n0" ] && [ "$(date -u +%s)" -lt "$deadline" ]; do sleep 5; done
  [ "$(date -u +%s)" -ge "$deadline" ] && { echo "boundary wait exhausted; last line: $(tail -1 $LOG | cut -c1-100)"; break; }
  sleep 40
  after=$(awk '/complete; quiet until/{buf=""; next} {buf=buf"\n"$0} END{print buf}' $LOG)
  if printf '%s' "$after" | grep -q "begins at tick"; then
    echo "$(stamp) a session began right after the boundary; waiting for the next"
    continue
  fi
  echo "$(stamp) boundary: $(tail -1 $LOG | cut -c1-100)"
  break
done

echo "=== cutover $(stamp) ==="
BACKUP=$S/live-capture-pre/current.zip timeout 1500 bash $W/tools/guala_release/cutover_stage.sh cutover 2>&1 | tail -4 | cut -c1-200

echo "=== live after $(stamp) ==="
sleep 45
NAME=post S=$S timeout 500 bash $W/tools/guala_release/capture_cmd.sh 2>&1 | tee $S/capture-post.log; grep -o '"tick": [0-9]*' $S/capture-post.log | head -1 || true
timeout 300 python3 - <<'EOF'
import sys, zipfile, json, base64, os, urllib.request
S = os.environ["GUALA_RELEASE_WORK"]
z = zipfile.ZipFile(f"{S}/live-capture-post/current.zip")
env = json.loads(z.read("world.json")); payload = json.loads(base64.b64decode(env["payload_base64"]))
inner = json.loads(base64.b64decode(payload["world_state_base64"])); state = json.loads(base64.b64decode(inner["payload_base64"])); w = state["world"]
print("LIVE WORLD: revision", w["revision"], "| things", len(w["objects"]), "| paint", sorted({r["reflectance_ppm"][0] for r in w["regions"]}), "| windows", sum(len(r.get("windows") or []) for r in w["regions"]), "| room", w["room_id"], "| migration receipt", "yes" if state.get("migration_receipt") else "no")
with urllib.request.urlopen("https://dsf-ai.com/api/v1/guala/observation", timeout=25) as r: o = json.load(r)
lo = o.get("last_occurrence") or {}
print("OBSERVATION: available", o.get("available"), "tick", o.get("live_tick"), "act", lo.get("her_act"), "room", (lo.get("embodiment") or {}).get("room_id"), "counts", lo.get("her_counts"), "seen", (lo.get("seen") or [])[:6])
EOF
echo "=== caretaker after ==="
ps -eo pid,etime,cmd | grep "[c]aretaker.py" | cut -c1-80
sleep 90; tail -2 $LOG | cut -c1-140
echo "=== chain done $(stamp) ==="
