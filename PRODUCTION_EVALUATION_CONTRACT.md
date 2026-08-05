# Production Evaluation Contract

Purpose: keep one exact production troubleshooting method in repo history so production claims do not drift.

## Mandatory Read Order
- `/workspaces/Tao_Financial_Engine/AGENTS.md`
- `/workspaces/Tao_Financial_Engine/PRODUCTION_EVALUATION_CONTRACT.md`
- `/workspaces/Tao_Financial_Engine/LOAD_DIRECTIVE_NEXT_CHAT.md`
- `/workspaces/Tao_Financial_Engine/readonly-production-verification-path.json`

## Production Troubleshooting Ladder
For every failed deploy or failed publish, use this order and do not skip ahead:

1. Verify whether the ECS task definition and the running task changed or did not change.
2. If ECS did not change, inspect CodeBuild result and CodeBuild logs first.
3. If ECS changed, inspect `runtime_refresh_runs` for the target `run_id`.
4. Inspect the validation report for the same `run_id`.
5. Inspect the active publication pointer and publication ids.
6. Only then inspect authenticated production routes.

## Required Failure Classification
Every production failure must be classified as exactly one of:
- deploy failure
- build failure
- refresh failure
- validation failure
- publication failure
- serving failure

## Classification Rules
- If ECS task definition and running task did not change, the failure is either `deploy failure` or `build failure`.
- If ECS did not change and CodeBuild failed, classify it as `build failure`.
- If ECS did not change and deployment stopped before build handoff, classify it as `deploy failure`.
- If ECS changed and `runtime_refresh_runs` terminal state is error or incomplete, classify it as `refresh failure`.
- If refresh completed but validation did not pass, classify it as `validation failure`.
- If validation passed but active publication pointer or publication ids are missing, invalid, or inconsistent, classify it as `publication failure`.
- If publication state is valid but authenticated production routes do not serve the same canonical publication state, classify it as `serving failure`.

## Claim Rules
- Do not claim prod changed unless ECS task definition or running task changed.
- Do not claim prod fixed unless post-deploy evidence exists for the same deployed image.
- Do not claim publication success from route behavior alone.
- Do not inspect routes before deployment, build, refresh, validation, and publication state are known.

## Permanent Rule
- No guessing.
- When production is involved, this file is the default repo contract for evaluation and troubleshooting.
