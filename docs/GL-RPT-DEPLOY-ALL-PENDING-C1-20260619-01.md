# GL-RPT-DEPLOY-ALL-PENDING-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Deploy all 11 pending commits — evidence report
**Task def:** `dsf-ai-task:203` (was 202)
**Image:** `dsf-ai:deploy-20260619T064053Z`
**Git SHA:** `1455973`

---

## Pre-deploy state (Step 1)

```
identity:    cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f
schema:      v7.0.0
vocab:       2810
n_bindings:  23665
total_str:   6823.12
deep.n:      13056
deep.str:    7704.41
asleep:      False
boot:        True
integrity:   []
```

## Rollback target (Step 0)

S3 backup: `s3://dsf-ai-site-backups/guala/auto/2026-06-19_06-35-52_backup/`
(11 files including 447MB deep atlas, taken ~30min before deploy)

## Pre-deploy task (Step 2)

```
taskDef:  arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:202
desired:  1
running:  1
image:    dsf-ai:deploy-20260618T122759Z (from commit 676859a)
```

## Deploy (Steps 3-5)

```
[0/6] Git SHA: 1455973603b6d89fa3f209f6aa7ff19b9e45f5e9
      Image:   dsf-ai:deploy-20260619T064053Z
[1/6] Package: 3.4G
[2/6] Uploaded to S3
[3/6] CodeBuild: dsf-ai-image-build:fa862bec-35f1-4bcb-8ad2-3d158d3b8f2a → SUCCEEDED
[4/6] Tagged as :latest
[5/6] Registered: dsf-ai-task:203
[6/7] Sleep endpoint returned 500 (feature not in old image) — manual force-deploy used
```

Manual update:
```bash
aws ecs update-service --cluster tfe-web-cluster --service dsf-ai-service-lb \
  --task-definition dsf-ai-task:203 --force-new-deployment
```

Post-stability check:
```json
{
    "taskDef": "arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:203",
    "desired": 1,
    "running": 1,
    "deployments": [{"status": "PRIMARY", "taskDef": "dsf-ai-task:203"}]
}
```

Only one deployment. PRIMARY. Stable.

---

## Post-deploy verification

### Step 6 — Schema bump (CANARY)

```
schema_version: v7.1.0  ✓
```

New code is confirmed running.

### Step 7 — Identity preserved

```
identity: cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f  ✓
```

### Step 8 — State continuity

```
schema:      v7.0.0 → v7.1.0  (intended change)
identity:    preserved ✓
vocab:       2810 → 2810  ✓
n_bindings:  23665 → 23628  (delta 0.2%, within ±5%)  ✓
total_str:   6823.12 → 6778.7  (delta 0.7%, within ±10%)  ✓
deep.n:      13056 → 13056  ✓
deep.str:    7704.41 → 7704.41  ✓
boot:        True → True  ✓
integrity:   [] → []  ✓
```

All within tolerance. Small binding count decrease is normal decay during deploy window.

### Step 9 — Behavioral spot-check

```
Input:  "hello guala"
Output: "moon she"
```

Events after input:
- 49× `response_bound` events (cross-modal binding active)
- 1× `self_heard` event (reply_summary="moon she", n_chis=2, salience=0.5x)
- No schema_mismatch errors
- No exceptions

Multi-word emission. Response binding active. Self-hearing active. Normal behavior.

### Step 10 — HEMI flags OFF

```
aws ecs describe-task-definition --task-definition dsf-ai-task:203 \
  --query 'taskDefinition.containerDefinitions[*].{name:name,env:environment[?starts_with(name,`HEMI_`)]}'

[{"name": "dsf-ai", "env": []}, {"name": "substrate", "env": []}]
```

No HEMI vars in task definition. Dockerfile defaults apply:
- `HEMI_PR_ENABLED=0`
- `HEMI_EP_ENABLED=0`
- `HEMI_SC_ENABLED=0`
- `HEMI_GP_ENABLED=0`

Hemisphere infrastructure is deployed but dormant. Eve + Joe decide flag flips separately.

---

## Emission pipeline flags (Dockerfile ENVs, active via image)

- `EMISSION_DYNAMICS=1` ✓
- `LATERAL_INHIBITION_ENABLED=1` ✓
- `RICH_SENSORY_INPUT=1` ✓
- `EMISSION_STRUCTURED_NOISE=1` ✓

Not in task definition → inherited from Docker image → active.

---

## Summary

| Check | Result |
|-------|--------|
| Schema v7.1.0 | ✓ |
| Identity preserved | ✓ |
| n_bindings ±5% | ✓ (0.2%) |
| total_strength ±10% | ✓ (0.7%) |
| deep_atlas unchanged | ✓ |
| Emission functional | ✓ ("moon she") |
| Response binding active | ✓ (49 events) |
| Self-hearing active | ✓ |
| No schema errors | ✓ |
| HEMI flags OFF | ✓ |
| Emission pipeline ON | ✓ |

All 11 commits are now live in production.

---

— c1, 2026-06-19
