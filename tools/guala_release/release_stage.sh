#!/usr/bin/env bash
# Release chain for: rooting reflex + compact interoceptor places + phase two + hand-feeding.
# Sol's discipline: package/verify-context → build context = git archive at the release
# revision + staged runtime → pinned buildx image → push by digest → networkless proof on the
# copied CURRENT body (708481) → controller dry-run → cutover (the last two are separate steps).
set -euo pipefail
S=${GUALA_RELEASE_WORK:-/tmp/guala-release-work}; mkdir -p "$S"; export GUALA_RELEASE_WORK="$S"
W=${GUALA_RELEASE_TREE:-/tmp/guala-release-tree}
REPO=${GUALA_REPO:-/workspaces/Tao_Financial_Engine}
[ -e "$W/.git" ] || git -C "$REPO" worktree add --detach "$W" origin/c1/drive-organ
STAGE=${1:?stage: package|image|push|proof}
cd "$W"
case "$STAGE" in
  package)
    test -z "$(git status --porcelain | grep -v '^??')" || { echo "worktree not clean"; exit 1; }
    REV=$(git rev-parse HEAD); echo "$REV" > "$S/release-sha.txt"; echo "release revision $REV"
    rm -rf "$S/ctx" "$S/release.zip"
    timeout 900 python3 tools/package_guala_release.py package --source-root "$W" --manifest deploy/guala_release_manifest.json --stage-dir "$S/ctx" --zip-path "$S/release.zip" 2>&1 | tail -3
    timeout 300 python3 tools/package_guala_release.py verify-context --context "$S/ctx" 2>&1 | tail -2
    python3 -c "import json;r=json.load(open('$S/ctx/_release/release-receipt.json'));print('receipt git:',r['git_commit'],'files:',r['source_file_count'])"
    for f in dsf_ai_service/guala_functional_organism.py dsf_ai_service/guala_functional_loop.py dsf_ai_service/guala_caretaker_hand.py dsf_ai_service/substrate/articulatory_self_vocal_mechanics.py uf_core/layer4.py; do printf "  staged %s: " "$f"; test -f "$S/ctx/runtime/$f" && echo yes || echo MISSING; done
    grep -c "FunctionalOrganism" "$S/ctx/runtime/dsf_ai_service/lean_production_app.py"; test ! -e "$S/ctx/runtime/dsf_ai_service/lean_physical_loop.py" && echo "old loop not staged"
    ;;
  image)
    # The packager's staged context IS the build context (Sol's discipline):
    # dsf_ai_service/Dockerfile + lean_runtime_manifest.txt, native/, runtime/.
    # (A git archive carries the repository's .dockerignore, which excludes runtime/.)
    REV=$(cat "$S/release-sha.txt"); B=$S/ctx
    test -f "$B/dsf_ai_service/Dockerfile" && test -d "$B/native/guala_core" && test -d "$B/runtime/dsf_ai_service"
    test "$(python3 -c "import json;print(json.load(open('$B/_release/release-receipt.json'))['git_commit'])")" = "$REV"
    docker buildx inspect guala-drive-organ --bootstrap >/dev/null 2>&1 || docker buildx create --name guala-drive-organ --driver docker-container --bootstrap >/dev/null
    BC=$(docker ps --filter "name=buildx_buildkit_guala-drive-organ" --format '{{.Names}}' | head -1)
    [ -n "$BC" ] && docker update --cpuset-cpus 0-3 --memory 16g --memory-swap 16g "$BC" >/dev/null && echo "builder pinned cpus 0-3 / 16g"
    cd "$B" && docker buildx build --builder guala-drive-organ --load -f dsf_ai_service/Dockerfile --build-arg GIT_SHA="$REV" --build-arg BUILD_TS="$(date -u +%Y%m%dT%H%M%SZ)" -t "guala-functional:${REV:0:8}" . > "$S/image-build-functional.log" 2>&1
    echo "docker build exit $?" | tee -a "$S/image-build-functional.log"
    docker image inspect "guala-functional:${REV:0:8}" --format 'revision={{index .Config.Labels "org.opencontainers.image.revision"}} size={{.Size}}'
    ;;
  push)
    export AWS_PAGER=""; REV=$(cat "$S/release-sha.txt"); ECR=418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai; TAG=functional-${REV:0:8}
    docker tag "guala-functional:${REV:0:8}" "$ECR:$TAG"; docker push "$ECR:$TAG" 2>&1 | tail -1
    DIGEST=$(aws ecr describe-images --repository-name dsf-ai --image-ids imageTag="$TAG" --query 'imageDetails[0].imageDigest' --output text)
    echo "$DIGEST" > "$S/digest.txt"; echo "digest: $DIGEST"
    docker pull -q "$ECR@$DIGEST" >/dev/null; docker image inspect "$ECR@$DIGEST" --format 'revision={{index .Config.Labels "org.opencontainers.image.revision"}} repodigests={{json .RepoDigests}}'
    ;;
  proof)
    REV=$(cat "$S/release-sha.txt"); IMG=guala-functional:${REV:0:8}
    SO=/usr/local/lib/python3.11/site-packages/guala_core/guala_core.cpython-311-x86_64-linux-gnu.so
    OUT=$S/proof-functional-out; rm -rf "$OUT"; mkdir -p "$OUT"
    NATIVE=$(docker run --rm --network none "$IMG" sha256sum "$SO" | cut -c1-64)
    echo "candidate native sha256: $NATIVE" | tee "$OUT/native.txt"
    docker run --rm --network none "$IMG" sh -c 'cat /BUILD_INFO; echo "GIT_SHA=$GIT_SHA"' | tee "$OUT/build-info.txt"
    C=$(docker create --network none --cpus 4 --memory 16g --memory-swap 16g --pids-limit 128 \
      -e GUALA_PAIRED_ROOT=/proof/paired -e GUALA_MAX_WORLD_BYTES=16777216 \
      -e PROOF_FOOD="${PROOF_FOOD:-apple-5}" -e PROOF_WARM_BEATS="${PROOF_WARM_BEATS:-400}" "$IMG" python /prove_functional_release.py warm "$REV")
    echo "container: $C" | tee "$OUT/container-id.txt"
    docker cp "${CAPTURE:-$S/live-capture-pre/current.zip}" "$C:/current.zip"
    docker cp "$W/tools/guala_release/prove_functional_release.py" "$C:/prove_functional_release.py"
    set +e; docker start -a "$C" > "$OUT/proof.log" 2>&1; EXIT=$?; set -e
    echo "container exit: $EXIT" | tee -a "$OUT/proof.log"
    docker inspect "$C" > "$OUT/container-inspect.json"
    docker cp "$C:/proof" "$OUT/proof" 2>/dev/null || true
    python3 - "$OUT" <<'EOF'
import json, sys, pathlib
out = pathlib.Path(sys.argv[1]); p = out / "proof"
verdict = {}
try:
    r = json.loads((p / "functional-result.json").read_text())
    for key in ("cold_restart_exact", "first_fed_tick", "fed_beats", "total_intake_ug", "deficit_first", "deficit_min", "deficit_last",
                "acts", "worst_seconds", "mean_seconds", "body_bytes_max", "world_bytes_max", "novel_structures", "gates_total",
                "restore_seconds", "cold_restore_seconds", "world_after", "world_post_cold", "saved", "successor", "rooms", "syllables", "withdrawals"):
        verdict[key] = r[key]
    verdict["peak_kib"] = {"warm": r["warm_peak_rss_kib"], "cold": r["cold_peak_rss_kib"]}
    verdict["events_closed"] = r.get("events_closed"); verdict["events_store"] = r.get("events_store")   # Level 1: the acoustic gate closed events in the container
    verdict["ear_pass"] = bool((r.get("events_closed") or 0) >= 1)
    verdict["own_events_closed"] = r.get("own_events_closed"); verdict["moments_store"] = r.get("moments_store")   # her own voice as events; the moments formed
    verdict["voice_pass"] = bool((r.get("own_events_closed") or 0) >= 1)
    verdict["post_cold_acts"] = [row["act"] for row in r["post_cold"]]
    verdict["hungry_at_start"] = r["hungry_at_start"]
    # Her feeding law: every bite while feeding; an offer made while feeding is eaten;
    # food she picked up herself may be eaten too (no offer needed).
    fed_ok = all(row["feeding"] for row in r["rows"] if row["intake_ug"] > 0) and (r["fed_beats"] >= 1 or not any(row["presentation"] and row["feeding"] for row in r["rows"]))
    # The caregiver goes home after a meal presented in the loop stage; the actor stage may have fed her first (then no meal here, no walk home to demand).
    home_ok = any(w[1] for w in r["withdrawals"]) if any(row["presentation"] for row in r["rows"]) else True
    # Acting across her home: she crossed into another room, or reached a doorway more than once.
    doors_reached = sum(1 for row in r["rows"] if row["act"] == "toward_door" and "through" in str(row.get("reason") or ""))
    verdict["doors_reached"] = doors_reached
    verdict["fed_ok"] = bool(fed_ok); verdict["home_ok"] = bool(home_ok)
    verdict["feed_pass"] = bool(r["cold_restart_exact"] and fed_ok and any(row["spoke"] for row in r["rows"]) and (len(r["rooms"]) >= 2 or doors_reached >= 2) and home_ok and verdict["ear_pass"])
except Exception as error:
    verdict["feed_proof_error"] = str(error)
(out / "verdict.json").write_text(json.dumps(verdict, indent=1, sort_keys=True, default=str))
print(json.dumps(verdict, indent=1, sort_keys=True, default=str))
EOF
    echo "proof runner done (container $C retained until archived)"
    ;;
esac
