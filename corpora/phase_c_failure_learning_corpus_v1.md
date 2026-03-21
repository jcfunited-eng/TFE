# Phase C Failure Learning Corpus v1

Generated: 2026-03-16 UTC
Status: accepted failure-family memory for the Phase C cycle that ended in success

## Purpose

This file records the exact failures that happened during the accepted Phase C production deploy-proof cycle so they are not retold as vague “it took a long time” complaints later.

The final cycle succeeded.

This file records what still went wrong during the proof process.

## Accepted Success Anchor

Accepted final proof:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-proof-20260316T041214Z.json`

This means:

- Phase C passed live
- the failures below are process/harness failures around the proof cycle, not successful contradictions of the final Phase C result

## Failure Registry

### Failure 1: false live-request blocker

Artifact:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-blocker-20260316T041214Z-continuation.json`

Exact bad blocker:

- `snapshot_request_did_not_dispatch_cutover_orchestrator`

Why it was false:

- corrected response body already showed:
  - `dispatchPath=step1_orchestrator`
  - `legacyRunnerDispatched=false`
  - `result.runId=3597430d-4d08-49d8-b76e-8a4d639cdc4a`

Root cause:

- proof parser froze a blocker from stale field extraction instead of re-reading the actual response body first

Prevention rule:

- blocker classification from HTTP response must always check the raw corrected response body before freezing a blocker artifact

### Failure 2: live proof SQL schema mismatch

Evidence directory:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-cycle-20260316T041214Z`

Exact fault:

- live SQL selected `requested_at` from `runtime_refresh_runs`
- that column does not exist on the live schema in use

Impact:

- authority evidence capture failed before JSON extraction even mattered

Prevention rule:

- live evidence queries must be schema-checked or generated from current table definitions before use

### Failure 3: interactive ECS output corruption

Evidence:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-cycle-20260316T041214Z/live-authority.execute.stdout.txt`

Exact fault:

- interactive ECS `execute-command` paged and wrapped the JSON payload

Impact:

- JSON extraction from stdout became unreliable

Prevention rule:

- do not treat raw interactive ECS stdout as clean JSON transport

### Failure 4: bad recovery assumption on non-interactive ECS mode

Evidence:

- `/workspaces/Tao_Financial_Engine/backups/runtime/phase-c-prod-deploy-cycle-20260316T041214Z/live-authority.noninteractive.stderr.txt`

Exact fault:

- non-interactive mode was attempted
- ECS returned `Interactive is the only mode supported currently.`

Impact:

- one more recovery branch was spent on an unsupported transport mode

Prevention rule:

- validate transport constraints before choosing the next evidence-capture method

### Failure 5: proof-harness salvage loop risk

Observed pattern:

- deploy already real
- core publication path may already be fine
- hours can then be spent repairing evidence capture instead of testing the intended boundary

Why it matters:

- this can look like more system failure than actually exists
- it can also hide real publication failures if the harness keeps mutating

Prevention rule:

- once the deployed revision is real, classify every new stop as either:
  - system boundary failure
  - proof-harness failure
  and never blur the two

## Exact Lessons

1. A successful final proof does not erase the need to document the failures inside the proof process.
2. Proof-harness faults must be recorded as their own failure family.
3. The evaluator must not confuse evidence-capture breakage with production-core breakage.
4. Long proof salvage loops should be treated as a process smell even when the final artifact is valid.

## Handoff Rule

This failure-learning corpus should be read together with:

- `/workspaces/Tao_Financial_Engine/corpora/production_shell_control_corpus_v2.md`

when planning any work after accepted Phase C closure.
