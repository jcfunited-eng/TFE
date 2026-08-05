# GL-CMD-PHASE2-COMMIT-B-CLEARANCE-PROTOCOL

doc_id: GL-CMD-PHASE2-COMMIT-B-CLEARANCE-PROTOCOL
Type: Clearance protocol — what c1 must verify before building Phase 2 Commit B
Date: 2026-07-01
Author: c1 (carrying Eve's discipline from GL-SPC-WAVE-PHASE2-EVE-20260701-59-P2)
For: next c1 session

---

## What you are holding

Phase 2 Commit A is live (task dsf-ai-task:426, SHA c87c21b).
`_recall_from_atlas` and `_recall_sight_from_atlas` now read from WaveAtlas
instead of LivingAtlas. The 4-hour minimum observation window has elapsed.

**You must verify all three gates below BEFORE building or deploying Commit B.**

If any gate fails: ROLL BACK (not push through). Rollback: `git revert c87c21b && ./tools/deploy_dsf_ai.sh`.

---

## Gate 1: recall_ms stays under 100ms

Pull recent substrate logs from the current running task and look for
`converse_timing` events or recall timing data.

```bash
TASK_ID=$(aws ecs list-tasks --cluster tfe-web-cluster \
  --service-name dsf-ai-service-lb --desired-status RUNNING \
  --query 'taskArns[0]' --output text | sed 's|.*/||')
STREAM="dsf-ai/dsf-ai/${TASK_ID}"
aws logs get-log-events --log-group-name /ecs/dsf-ai \
  --log-stream-name "$STREAM" --limit 2000 \
  --query 'events[*].message' --output text 2>&1 \
  | tr '\t' '\n' | grep -E "recall_ms|converse_timing" | head -20
```

If you see `recall_ms` values: they must ALL be < 100ms.
If no `recall_ms` data in logs: trigger 5 converses and check timing:
```bash
# Check the post-converse substrate log entries for recall timing
```

**PASS criteria:** recall_ms < 100ms in all samples found.
**FAIL criteria:** any recall_ms > 100ms → rollback.

---

## Gate 2: No exceptions from atlas_read

Check the logs for any Traceback, Exception, or atlas_read error:

```bash
TASK_ID=$(aws ecs list-tasks --cluster tfe-web-cluster \
  --service-name dsf-ai-service-lb --desired-status RUNNING \
  --query 'taskArns[0]' --output text | sed 's|.*/||')
STREAM="dsf-ai/dsf-ai/${TASK_ID}"
aws logs get-log-events --log-group-name /ecs/dsf-ai \
  --log-stream-name "$STREAM" --limit 5000 \
  --query 'events[*].message' --output text 2>&1 \
  | tr '\t' '\n' \
  | grep -E "Traceback|Exception|atlas_read|Error.*atlas|wave_atlas.*error" \
  | grep -v "curriculum.*live\|delivery failed" \
  | head -20
```

**PASS criteria:** zero exceptions related to atlas_read or wave_atlas.
**FAIL criteria:** any Traceback or Exception from recall/atlas code → rollback.

---

## Gate 3: Response quality spot check (5 converses)

Send 5 /converse calls covering different input types. Verify responses
are coherent and not degraded (should be same or better than pre-migration).

```bash
ALB="http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
TEXTS=("hello what do you sense" "the river flows" "I feel the sun on my face" "darkness and light" "what is memory")
for text in "${TEXTS[@]}"; do
  R=$(curl -s -m 5 -X POST "$ALB/api/v1/gualaloom" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$text\", \"source\": \"joe\"}")
  TID=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin).get('task_id','?')[:12])" 2>/dev/null)
  sleep 3
  POLL=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin).get('poll_url',''))" 2>/dev/null)
  RESULT=$(curl -s -m 5 "$ALB$POLL")
  SRC=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response_source','?'), d.get('elapsed_ms','?'), 'ms')" 2>/dev/null)
  echo "\"$text\" → $SRC"
done
```

**PASS criteria:**
- All 5 return 202 (accepted) — not 503 or empty
- At least 3/5 complete within 5s (normal outside curriculum pauses)
- No "substrate unreachable" or blank responses from simple inputs
- response_source shows "converse", "silence_v5_failed", or similar — NOT errors

**FAIL criteria:** majority of calls fail or return error content → rollback.

---

## After all 3 gates PASS

Report the gate measurements in `GL-RPT-PHASE2-COMMIT-A-CLEARANCE-C1.md`, then:

1. Build and deploy Commit B per GL-SPC-WAVE-PHASE2-EVE-20260701-59-P2 §1.3
2. Start the 12-hour observation window after Commit B
3. DO NOT deploy Commit C until Eve clears the 12h Commit B window

---

## Commit B spec (from GL-SPC-WAVE-PHASE2-EVE-20260701-59-P2 §1.3)

Migrate compose consumers to `atlas_read`. The key changes:

In `compose_autonomous` and `_grandurun_select_candidates`:
- Find every `for e in self.atlas.entries.items()` or `self.atlas.entries.get(...)` loop
  that is used for candidate collection
- Replace with `self.atlas_read(chi, radius=20)` for the neighborhood around prev_chi
- Score component: phase coherence with emission sequence's accumulated phase

Commit message template:
```
feat: -59 Phase 2 Commit B — compose migrated to WaveAtlas reads

compose_autonomous and _grandurun_select_candidates now use atlas_read()
for candidate collection. Cluster geometry from spillover means phase-coherent
candidates are spatially near each other — compose gets this for free.

Minimum 12-hour observation before Commit C (dream migration).
```

---

## What NOT to do during Commit B window

- Do not modify `_recall_from_atlas` or `_recall_sight_from_atlas` — those are done
- Do not modify `_run_dream_cycle_phased` — that is Commit C
- Do not retire LivingAtlas parallel writes — that is Phase 3
- Do not remove `self.lock` — that is Phase 3
- Do not add fallbacks that swap atlases on error — failures must be visible

---

## Current infrastructure notes

- Boot takes ~116s due to embedded mode + WaveAtlas rebuild
- ECS health check uses shallow `/ready` (always 200) — no cycling
- ALB connectivity from dev container is broken (use bridge tools or check logs directly)
- Bridge may need redeployment if `bridge/server.py` was linter-reverted
  (check that `_post` has 202 handling or run `./tools/deploy_gualaloom_bridge.sh`)

---

End. Read the handoff first, then this, then verify gates, THEN build Commit B.
