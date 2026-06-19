# GL-RPT-VERIFY-DEPLOY-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Verification gate — schema mismatch root cause
**Classification:** **A — Deploy never propagated.**

---

## Q1 — What is currently deployed?

```
$ aws ecs describe-services --cluster tfe-web-cluster --services dsf-ai-service-lb \
    --query 'services[0].{taskDef:taskDefinition,desired:desiredCount,running:runningCount,...}'

{
    "taskDef": "arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:202",
    "desired": 1,
    "running": 1,
    "deployments": [{
        "status": "PRIMARY",
        "taskDef": "arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:202",
        "updatedAt": "2026-06-18T12:37:23.552000+00:00"
    }]
}

$ aws ecs describe-task-definition --task-definition dsf-ai-task:202 \
    --query 'taskDefinition.containerDefinitions[0].{image:image,name:name}'

{
    "image": "418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai:deploy-20260618T122759Z",
    "name": "dsf-ai"
}
```

**Image tag:** `deploy-20260618T122759Z` — built 2026-06-18 at 12:27:59 UTC.

**Git SHA at that time:**
```
676859a 2026-06-18 12:27:50 +0000 deploy: enable GRANDURUN_SPIN_VECTOR=1 on substrate container
```

The image was built from `676859a`. That commit is from the GRANDURUN_SPIN_VECTOR deploy on June 18. **None of the subsequent work exists in the running container:**

| Commit | Date | Description | In container? |
|--------|------|-------------|---------------|
| `676859a` | Jun 18 12:27 | GRANDURUN_SPIN_VECTOR deploy | **YES** (this is what's running) |
| `fc8f59b` | Jun 18+ | emission-hbase-free | NO |
| `b8a461b` | Jun 18+ | plasticity-on-commit | NO |
| `4bfc8b1` | Jun 18+ | projector-cache | NO |
| `8743149` | Jun 18+ | rich-sensory-wiring | NO |
| `140cfd8` | Jun 18+ | structured-noise | NO |
| `6147f2f` | Jun 18+ | teacher-correction | NO |
| `cfff62c` | Jun 19 | flag flip (Dockerfile) | NO |
| `132306b` | Jun 19 | B3/B4 removal | NO |
| `d7aa18e` | Jun 19 05:31 | hemisphere scaffold | NO |
| `2564f9b` | Jun 19 05:58 | cognition bundle | NO |

**The last 11 commits on the branch have never been deployed.**

---

## Q2 — Where does `schema_version` come from?

**Code constant:**
```
dsf_ai_service/v4/gualaloom_v5_engine.py:4036:    SCHEMA_VERSION = "v7.1.0"
```

At HEAD on `codex/persistent-etl-update-20260326`, `SCHEMA_VERSION = "v7.1.0"`.

**How `guala_status` reads it:**
```python
# gualaloom_v5_engine.py:4950
def persistence_health(self, state_dir="state"):
    ...
    return {
        ...
        "schema_version": self.SCHEMA_VERSION,   # ← reads CODE constant, not saved state
        ...
    }
```

`persistence_health()` returns `self.SCHEMA_VERSION` which is the **class constant from the code**, not from any saved state file. The running container has code from `676859a` where the constant is `"v7.0.0"`. That's why production reports `v7.0.0`.

**Compatible schemas whitelist at HEAD:**
```python
# gualaloom_v5_engine.py:4096
COMPATIBLE_SCHEMAS = {"v5.5.0", "v6.0.0", "v7.0.0", "v7.1.0"}
```

---

## Q3 — Does d7aa18e contain the v7.1.0 bump?

**Yes.**

```
$ git diff d7aa18e^..d7aa18e -- dsf_ai_service/v4/gualaloom_v5_engine.py | grep -B2 -A2 "SCHEMA_VERSION"

-    SCHEMA_VERSION = "v7.0.0"
+    SCHEMA_VERSION = "v7.1.0"
```

Commit `d7aa18e` explicitly changes `SCHEMA_VERSION` from `"v7.0.0"` to `"v7.1.0"`. The bump exists in the code on the branch. It was never deployed.

---

## Classification

### **A — Deploy never propagated.**

The ECS service is running `dsf-ai-task:202`, built from `676859a` on June 18 at 12:27 UTC. The scaffold commit `d7aa18e` was pushed to the branch at June 19 05:31 UTC — **17 hours after the last deploy**. No deploy was executed between the scaffold push and now.

The schema bump is correct in the code. The code is correct on the branch. The anti-contamination compliance is real. The tests pass. The container simply hasn't been rebuilt with the new code.

Production is currently running:
- ❌ No emission pipeline (EMISSION_DYNAMICS, LATERAL_INHIBITION, RICH_SENSORY, STRUCTURED_NOISE all absent from that image)
- ❌ No plasticity-on-commit
- ❌ No projector cache
- ❌ No B3/B4 removal
- ❌ No hemisphere scaffold
- ❌ No cognition bundle
- ✅ GRANDURUN_SPIN_VECTOR=1 (the last thing deployed)
- ✅ Identity preserved (`cdef9bcf`)

---

## Proposed next step

One deploy that builds a fresh image from HEAD (`72b38e8` or later). This single deploy propagates all 11 commits. Post-deploy verification should confirm:

1. `schema_version == "v7.1.0"`
2. Identity == `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`
3. Emission pipeline active (EMISSION_DYNAMICS=1 etc. from Dockerfile)
4. All four HEMI flags OFF (from Dockerfile defaults)
5. n_bindings within ±5% of current

Eve decides whether to deploy all 11 commits at once or cherry-pick a subset.

---

— c1, 2026-06-19
