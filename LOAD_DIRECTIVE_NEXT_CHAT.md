# Load Directive For Next Chat

Generated UTC: 2026-03-13T21:08:00Z
Workspace: `/workspaces/Tao_Financial_Engine`

## Read First
- `/workspaces/Tao_Financial_Engine/AGENTS.md`
- `/workspaces/Tao_Financial_Engine/PRODUCTION_EVALUATION_CONTRACT.md`
- `/workspaces/Tao_Financial_Engine/LOAD_DIRECTIVE_NEXT_CHAT.md`
- `/workspaces/Tao_Financial_Engine/readonly-production-verification-path.json`

## Permanent Production Rule
- Use `/workspaces/Tao_Financial_Engine/PRODUCTION_EVALUATION_CONTRACT.md` as the required production troubleshooting ladder.
- For every failed deploy or failed publish, classify the failure only after using that ladder in order.
- No guessing.

## Current Production Truth
- Production is still on ECS task definition `tfe-web-task:222`.
- The latest attempted emergency deploy did not reach ECS rollout.
- The latest attempted emergency deploy failed in AWS CodeBuild before a new image reached production.

## Current Known Build Failure
- Evidence directory: `/workspaces/Tao_Financial_Engine/backups/deploy-evidence-20260313T185239Z`
- Exact build summary: `/workspaces/Tao_Financial_Engine/backups/deploy-evidence-20260313T185239Z/codebuild-result.json`
- Exact build log: `/workspaces/Tao_Financial_Engine/backups/deploy-evidence-20260313T185239Z/codebuild-log-events.json`
- Exact status record: `/workspaces/Tao_Financial_Engine/backups/deploy-evidence-20260313T185239Z/emergency-deploy-status.json`
- Exact failure: CodeBuild docker build could not find `tfe_deploy_metadata.json` and `uf_structural_cache.json`.

## Current Repo Truth
- The deploy build-context contract fix is committed in repo history and must be used for the next deploy rerun.
- Before any new prod theory, verify whether the next deploy moved failure classification past `build failure`.

## First Action For Next Chat
- Start at step 1 of the production troubleshooting ladder:
  - verify ECS task definition and running task changed or did not change
- If ECS did not change:
  - inspect CodeBuild result and CodeBuild logs first
- If ECS changed:
  - inspect `runtime_refresh_runs` for the target `run_id`

## First Prompt For Next Chat
Load `/workspaces/Tao_Financial_Engine/PRODUCTION_EVALUATION_CONTRACT.md` and `/workspaces/Tao_Financial_Engine/LOAD_DIRECTIVE_NEXT_CHAT.md` first, then classify the next production failure as deploy failure, build failure, refresh failure, validation failure, publication failure, or serving failure only after following the ladder in order.
