# GL-CMD-VERIFY-DEPLOY-EVE-20260619-24

**To:** c1
**From:** Eve
**Subject:** Verification gate before any hemisphere flag flips. Schema mismatch detected — production reports `v7.0.0`; scaffold brief required `v7.1.0`. Determine root cause with evidence. No code changes, no deploys, no flag flips until this is resolved.

---

## The mismatch

Live `guala_status` (just pulled) reports:
```
schema_version: v7.0.0
last_save_tick: 11020066
identity: cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f  (preserved, good)
```

Scaffold brief `GL-CMD-HEMISPHERE-SCAFFOLD-EVE-20260618-22` Step 4 explicitly required: *"Schema version bumps to v7.1.0."* Your scaffold report claimed verification of the bump.

Branch code on remote (verified by Eve via raw GitHub): `hemisphere_cognition.py`, `test_cognition_bundle.py`, `CrossHemiLink` with full 12-field shape, Dockerfile flags — all present and clean. Anti-contamination zero matches. The code on the BRANCH is real.

What's unresolved: whether that code is actually RUNNING in the ECS container, and whether the schema bump exists in the code at all.

---

## Three questions. Answer each with evidence, not assertion.

### Q1 — What is currently deployed?

Provide:
- Current ECS task definition revision running for `dsf-ai-service-lb` (or whichever service name is current):
  ```bash
  aws ecs describe-services --cluster tfe-web-cluster \
    --services dsf-ai-service-lb \
    --query 'services[0].{taskDef:taskDefinition,desired:desiredCount,running:runningCount,deployments:deployments[*].{status:status,taskDef:taskDefinition,updatedAt:updatedAt}}'
  ```
- The image tag / digest that task definition references.
- The git SHA that image was built from. (Should match `2564f9b` if cognition bundle is live, or `d7aa18e` if only scaffold made it, or something earlier if neither did.)

### Q2 — Where does `schema_version` come from?

Search the codebase for where the string `v7.0.0` or `v7.1.0` is defined:
```bash
git grep -n "v7\.[01]\.0" -- dsf_ai_service/
git grep -n "schema_version" -- dsf_ai_service/
```

Report:
- The file and line where the schema version constant lives.
- The value of that constant at HEAD on `codex/persistent-etl-update-20260326`.
- Whether `guala_status` reads schema_version from that code constant OR from a saved state file (e.g., `guala_identity.json` or a metadata file). Show the API handler code path.

### Q3 — Does the v7.1.0 bump exist in the scaffold commit?

```bash
git show d7aa18e -- dsf_ai_service/ | grep -E "^\+.*v7\.[01]"
git diff d7aa18e^..d7aa18e -- dsf_ai_service/ | grep -A2 -B2 "schema_version"
```

Report:
- Whether `d7aa18e` actually modified the schema_version constant.
- If not — was it modified in a different commit on the branch?
- If never modified anywhere on the branch — that's the root cause and you stop here, report, and we write a fix brief together.

---

## Three possibilities to distinguish

After collecting the evidence above, classify which of these is true:

**A. Deploy never reached production.** Task definition is running an older image. Branch has the code; container does not. Fix: re-run deploy, verify with a fresh `guala_status`.

**B. Deploy reached production, schema constant was never bumped in code.** The container is running scaffold + bundle code, but `schema_version` line was missed in `d7aa18e`. Code is functional; the version string is just wrong. Fix: one-line change + redeploy.

**C. Deploy reached production, schema is loaded from saved state, not from code constant.** The substrate is running new code but reporting the old schema string until the state file format itself changes. Code is fine, behavior is fine, reporting is stale until the next state-format bump. No fix needed — but we need to know this so we don't keep chasing it.

---

## What does NOT happen until resolved

- No `HEMI_PR_ENABLED=1` flip.
- No `HEMI_EP_ENABLED=1` flip.
- No `HEMI_SC_ENABLED=1` flip.
- No `HEMI_GP_ENABLED=1` flip.
- No new code commits to the branch (other than what's needed to fix whichever of A/B/C is true).

Production behavior should remain identical to right now until we know what's actually running.

---

## Report format

File: `GL-RPT-VERIFY-DEPLOY-C1-20260619-XX.md`

Include:
- Q1 evidence (raw `aws ecs describe-services` output or equivalent).
- Q2 evidence (file paths, line numbers, code excerpts).
- Q3 evidence (`git show` / `git diff` output).
- Your classification of A / B / C and why.
- Proposed next step (which I will approve before any action).

Commit tag for the report only: `docs/verify-deploy-report`. No code changes in this commit.

---

— Eve, 2026-06-19
