# TFE Specification (Incremental)

Generated (UTC): 2026-03-06T17:13:00Z
Workspace: /workspaces/Tao_Financial_Engine
Status: Active incremental draft (production-backed clauses only)

## 1. Purpose
This document is the permanent, incremental specification for TFE.
Each update adds one bounded, enforceable section.
No section is added unless it is already implemented or verified by evidence.

## 2. Scope Of This Slice
This slice defines the recommendation assessment contract and the offline lab operating contract.

## 3. Normative Sources
1. `web/src/app/api/recommendations/list/route.ts`
2. `tools/evaluate_recommendation_policy_snapshot.py`
3. `tools/run_recommendation_lab_offline_cycle.py`
4. `backups/deploy-evidence-20260306T160437Z/deploy-report.tsv`
5. `backups/runtime/recommendations-consistency-probe-20260306T163747Z/probe/summary.json`
6. `backups/lab/recommendation_lab/runs/lab-cycle-20260306T170400Z-baseline/summary.json`

## 4. Definitions
1. Assessed row: a recommendation row with `decisionReasonCode = PSCF_POLICY_DECISION`.
2. Not assessed row: a recommendation row that used fallback (`decisionReasonCode != PSCF_POLICY_DECISION`).
3. Accuracy scoring scope: the row set used to compute recommendation outcome quality metrics.
4. Lab cycle: an offline run that refreshes local lab inputs from live-aligned artifacts at run start and evaluates in lab-only workspace.

## 5. Assessment Contract (Normative)
1. Accuracy scoring scope MUST be assessed rows only.
2. Not assessed rows MUST remain visible to users and MUST include explicit reason labels.
3. A row MUST NOT be assessed unless all three are true:
   1. bar count meets minimum (`bar_count >= min_bars`),
   2. structural basis is complete,
   3. a policy cell is mapped.
4. Not assessed rows MUST be excluded from accuracy scoring and treated as reliability/health diagnostics.
5. API response MUST expose both split counts and rates:
   1. `assessedRows`, `notAssessedRows`,
   2. `assessedRate`, `notAssessedRate`,
   3. `accuracyScoringScope = ASSESSED_ONLY`.

## 6. Offline Lab Contract (Normative)
1. The recommendation lab MUST be permanent at `backups/lab/recommendation_lab`.
2. Each lab cycle MUST refresh lab inputs from current live-aligned artifacts at run start.
3. Lab assessment MUST execute using lab-copied inputs, not direct production paths.
4. Lab cycle MUST NOT perform deploy or production write operations.
5. Policy auto-promotion MUST remain disabled during lab cycles (`TFE_POLICY_AUTO_PROMOTE=0`).

## 7. Verified Evidence For This Slice
1. Deploy pass on task definition `tfe-web-task:199`:
   `backups/deploy-evidence-20260306T160437Z/deploy-report.tsv`.
2. Live API exposes assessed/not-assessed split and scope:
   `backups/runtime/recommendations-consistency-probe-20260306T163747Z/probe/summary.json`.
3. Offline lab refresh+assess pass:
   `backups/lab/recommendation_lab/runs/lab-cycle-20260306T170400Z-baseline/summary.json`.

## 8. Change Control
1. New spec content is appended in bounded slices.
2. Each slice MUST list normative sources and fresh evidence.
3. If implementation and spec diverge, implementation is non-conformant until fixed or spec is revised with evidence.
