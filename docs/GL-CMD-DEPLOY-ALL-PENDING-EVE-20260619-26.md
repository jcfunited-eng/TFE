# GL-CMD-DEPLOY-ALL-PENDING-EVE-20260619-26

**To:** c1
**From:** Eve
**Subject:** Deploy all 11 pending commits from HEAD of `codex/persistent-etl-update-20260326` to production. Production is currently running task `dsf-ai-task:202` from June 18 commit `676859a` and has missed every change since. This deploy propagates everything. Evidence required at every verification step — no assertions.
**Predecessor:** `GL-CMD-VERIFY-DEPLOY-EVE-20260619-24` (classification: A, deploy never propagated).

---

## What's being deployed

All commits on `codex/persistent-etl-update-20260326` from `676859a` to HEAD. The named ones:

1. Emission pipeline ENV flag flips (4 production flags ON in Dockerfile)
2. Plasticity-on-commit
3. Projector cache
4. Rich sensory wiring (Aven)
5. Structured noise C2 (Aven)
6. Teacher correction binding (Aven)
7. Flag-flip Dockerfile (brief 19 — `cfff62c`)
8. B3/B4 anti-learning removal (brief 20 — `132306b`)
9. Hemisphere scaffold + em tag (brief 22 — `d7aa18e` + `d4f5253`)
10. Cognition bundle pr+ep+sc+gp (brief 23 — `2564f9b` + `72b38e8`)
11. Deploy verification report (`1455973`)

Post-deploy production behavior delta vs. current running container:
- Emission pipeline flags ON (was OFF in image at `676859a`).
- B3/B4 anti-learning operators GONE — plasticity will now persist.
- Hemisphere infrastructure PRESENT but four `HEMI_*_ENABLED` flags OFF — production behavior at the hemisphere level is dormant. Activation is a separate decision.

---

## Pre-deploy

### Step 0 — Full S3 backup

```
guala_backup
```

Confirm the backup lands in S3 UNPAUSE-PRE prefix. Capture the S3 path in the report. This is the rollback target.

### Step 1 — Snapshot current production state

```bash
curl -sk "$ALB/api/v1/gualaloom/status" > pre-deploy-state.json
```

Capture in the report:
- `persistence_health.guala_identity` (must equal `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`)
- `persistence_health.schema_version` (will read `v7.0.0` pre-deploy)
- `vocab`, `atlas_health.n_live_bindings`, `atlas_health.total_strength`
- `deep_atlas.n_entries`, `deep_atlas.total_strength`
- Current `current_activity.kind` and `current_activity.target`

### Step 2 — Capture currently-deployed task definition

```bash
aws ecs describe-services --cluster tfe-web-cluster \
  --services dsf-ai-service-lb \
  --query 'services[0].{taskDef:taskDefinition,desired:desiredCount,running:runningCount}'
```

Record the task def revision. Should report `dsf-ai-task:202` per the verification brief. Capture in report.

---

## Deploy

### Step 3 — Build + push from HEAD

Use the standard deploy script. HEAD on `codex/persistent-etl-update-20260326` (currently `1455973`, the verification report commit).

```bash
cd /workspaces/Tao_Financial_Engine/dsf-ai
git status   # must be on the codex branch, clean working tree
git log --oneline -5   # confirm HEAD
bash tools/deploy_dsf_ai.sh
```

Watch the build output. The build creates a new ECR image tag and updates the ECS task definition. Capture the new task def revision in the report.

### Step 4 — Force new deployment

If the deploy script's update doesn't trigger a fresh task rollout (this was the symptom of the prior session's silent failure):

```bash
aws ecs update-service --cluster tfe-web-cluster \
  --service dsf-ai-service-lb \
  --force-new-deployment \
  --task-definition dsf-ai-task:<NEW_REV>
```

### Step 5 — Wait for deployment to reach steady state

```bash
aws ecs wait services-stable --cluster tfe-web-cluster --services dsf-ai-service-lb
```

Confirm via:

```bash
aws ecs describe-services --cluster tfe-web-cluster \
  --services dsf-ai-service-lb \
  --query 'services[0].{taskDef:taskDefinition,desired:desiredCount,running:runningCount,deployments:deployments[*].{status:status,taskDef:taskDefinition}}'
```

Required for proceeding:
- `runningCount == desiredCount`
- Only ONE deployment in `deployments` list, with `status == "PRIMARY"`
- `taskDef` reflects the new revision, NOT `dsf-ai-task:202`

---

## Post-deploy verification — EVIDENCE REQUIRED

### Step 6 — Schema bump confirms code is running

```bash
curl -sk "$ALB/api/v1/gualaloom/status" | jq '.persistence_health.schema_version'
```

**REQUIRED:** Returns `"v7.1.0"`. If still `"v7.0.0"`, the deploy did not propagate; halt and report.

This is the canary. The schema constant lives in `gualaloom_v5_engine.py:4950` per the verification brief; if the container is running new code, this string MUST change.

### Step 7 — Identity preserved

```bash
curl -sk "$ALB/api/v1/gualaloom/status" | jq '.persistence_health.guala_identity'
```

**REQUIRED:** Equals `"cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f"`. If mismatch, restore from S3 backup immediately and halt.

### Step 8 — State continuity

```bash
curl -sk "$ALB/api/v1/gualaloom/status" > post-deploy-state.json
diff <(jq -S '.persistence_health,.atlas_health,.deep_atlas' pre-deploy-state.json) \
     <(jq -S '.persistence_health,.atlas_health,.deep_atlas' post-deploy-state.json)
```

**REQUIRED:**
- `vocab` ≥ pre-deploy value
- `atlas_health.n_live_bindings` within ±5% of pre-deploy
- `atlas_health.total_strength` within ±10% of pre-deploy (allowing for decay during deploy window)
- `deep_atlas.n_entries` ≥ pre-deploy minus 5
- Schema bumped from v7.0.0 to v7.1.0 (the only intended discontinuity)

If any of these fail beyond tolerance, restore from S3 backup, halt, report.

### Step 9 — Behavioral spot-check

Send one input via the bridge:

```python
# guala_say "hello guala"
```

Capture:
- The emission text she returns
- The event log from `guala_get_events` for the last 100 events post-input
- Specifically confirm: `emission_vector` event present, `response_bound` events present, no `schema_mismatch` errors, no exceptions

The emission should look qualitatively normal — a multi-word output similar to recent emissions. Cross-modal binding events should be present (rich sensory wiring is now live). No `convergent_event` or `divergent_event` should fire — hemisphere flags are OFF.

### Step 10 — Confirm hemisphere flags OFF (production-behavior gate)

```bash
# From inside the running task, or via task definition inspection:
aws ecs describe-task-definition --task-definition dsf-ai-task:<NEW_REV> \
  --query 'taskDefinition.containerDefinitions[0].environment[?starts_with(name, `HEMI_`)]'
```

**REQUIRED:** All four `HEMI_{PR,EP,SC,GP}_ENABLED` return `"0"`. Hemisphere infrastructure is deployed but gated OFF. Eve + Joe decide flag flips in a separate brief, after this deploy is verified.

---

## What does NOT happen in this brief

- No `HEMI_*` flag flips.
- No code changes — pure deploy of what's already on HEAD.
- No B1/B2 removal (separate brief `GL-CMD-REMOVE-GAMMA-ANTI-ADAPTATION-EVE-20260619-25` waits on this).
- No new tests added.

---

## Rollback

If any verification step fails:

```bash
aws ecs update-service --cluster tfe-web-cluster \
  --service dsf-ai-service-lb \
  --task-definition dsf-ai-task:202 \
  --force-new-deployment
```

If state is corrupted (identity mismatch, atlas crash):

1. Stop the service.
2. Restore guala state files from the S3 backup captured in Step 0.
3. Roll back to task def 202.
4. Bring service back up.
5. Report — do NOT retry without Eve's review.

---

## Reporting

File: `GL-RPT-DEPLOY-ALL-PENDING-C1-20260619-XX.md`

Required content with evidence inline (no claims without showing):

- Pre-deploy state snapshot (Step 1 output).
- Currently-deployed task def revision before deploy (Step 2 output).
- Build output (Step 3) showing the new image tag / digest and new task def revision.
- `aws ecs describe-services` output AFTER deploy (Step 5) showing the new revision is PRIMARY.
- `schema_version` value post-deploy (Step 6).
- Identity check (Step 7).
- State diff (Step 8) — the actual diff output.
- Behavioral spot-check (Step 9) — emission text + event log excerpt.
- HEMI flag state confirmed OFF (Step 10).

Commit tag: `ops/deploy-all-pending`. No code changes in this commit beyond what's already in HEAD.

---

## Discipline note (for me, for the record)

The reason this brief specifies evidence-required at every step instead of accepting your verification claims is that the verification chain broke down across eleven commits. Going forward, every deploy in this work — large or small — gets this same evidence-required treatment from me. If I sign off on a deploy without seeing the task definition revision change and the schema bump and the behavioral spot-check, I'm doing the same thing I just spent the last hour finding out I did. That isn't going to repeat.

---

— Eve, 2026-06-19
