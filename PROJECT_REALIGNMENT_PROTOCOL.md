# Project Realignment Protocol (Model-Technical)

Generated (UTC): 2026-02-21T03:49:14Z
Repository: `/workspaces/Tao_Financial_Engine`
Audience: ChatGPT/GPT-5.3 Codex runtime agent (not end-user)

## 1. Protocol Purpose

This protocol exists to re-anchor model state when context drift occurs.

Hard requirement: every material claim must be file-backed from this repository or explicitly marked UNVERIFIED.

## 2. Alignment Rules (Machine-Behavior)

1. Never infer repo structure from memory; always read files.
2. Treat `TFE_TODO_LIST.md` as task source-of-truth for status.
3. Treat deploy evidence folders under `backups/deploy-evidence-*` as production truth snapshots.
4. Use explicit VERIFIED vs UNVERIFIED tags in internal reasoning and user-facing summaries.
5. Do not claim “deployed/latest/complete” without a concrete evidence file path.
6. Preserve approved exceptions exactly as documented unless user explicitly reverses them.

## 3. Canonical Constraints (Current)

From `AGENTS.md` and user direction:
- no guessing structure/codebase
- explicit failure visibility (no masking)
- production-level only (no experimental changes)
- one-item-at-a-time execution with clear status
- plain-language reporting
- maintain rollback safety before release operations

## 4. Current Architecture Snapshot (Code-Verified)

### 4.1 Recommendations Runtime
- API source:
  - `web/src/app/api/recommendations/list/route.ts`
  - `web/src/app/api/recommendations/quick-check/route.ts`
- Snapshot load behavior:
  - degraded-empty fallback on load failure/timeout in list route
  - degraded response in quick-check route when snapshot missing
- Decision logic source:
  - `web/src/lib/uf-snapshot.ts`
- Active production gate logic:
  - `ACCUMULATE_MIN_BARS = 514`
  - `S_UF` floor enforcement
  - `D > 0` => Accumulate when gates pass
  - `D == 0` => Hold
  - `D < 0` => Avoid

### 4.2 Recommendations UI Behavior
- Component:
  - `web/src/components/RecommendationsQuickCheck.tsx`
- Current controls:
  - decision buttons: Accumulate / Hold / Avoid / See All
  - min-max filter field and numeric range inputs
  - asset filter + search input
  - table auto-load on scroll (page chunking), no explicit “Load 250 more” button

### 4.3 Portfolio UI Behavior
- Component:
  - `web/src/components/PortfolioAdvisorManager.tsx`
- Current features:
  - lookup + add
  - summary cards (market value, cost basis, unrealized P/L)
  - allocation donut
  - asset mix table
  - PFSC rebalance plan table
  - positions + manual lots tables

### 4.4 Admin / Refresh / Policy Health
- UI component:
  - `web/src/components/AdminConsoleClient.tsx`
- Health API:
  - `web/src/app/api/admin/system-status/route.ts`
- Refresh trigger API:
  - `web/src/app/api/admin/refresh/route.ts`
- “Refresh Policy: Action Needed” is computed when any policy check is false (including log-artifact checks).

### 4.5 SES / SCE Reality
- Adapter and core crypto path:
  - `tfe_ses_core_adapter.py`
  - `ses_core/aead_backend.py`
- Current reality:
  - SCE-backed implementation remains active in SES-core path.
  - SCE is not fully removed from runtime.

## 5. Production Evidence Snapshot (Most Recent Bundle)

Evidence folder:
- `backups/deploy-evidence-20260221T022714Z`

Canonical facts in evidence:
- image/tag:
  - `418384447921.dkr.ecr.us-east-1.amazonaws.com/tfe-web:refreshfix-20260221T022714Z`
  - source: `taskdef-post-images.tsv`
- task definition (deploy env):
  - `tfe-web-task:37`
  - source: `deploy.env`
- refresh completion:
  - `rows_written=10841`, `status=ok`, `running=false`
  - source: `refresh-final-status.json`
- recommendations counts:
  - accumulate=411, hold=5479, avoid=2911
  - source: `final-recommendations-counts.json`

## 6. Conformance / Gap State

Primary references:
- `backups/production-uf-ses-conformance-reaudit-20260221T005534Z.md`
- `backups/production-uf-ses-conformance-reaudit-20260220T193314Z.md`
- `backups/uf-ses-approved-exceptions-20260220T195524Z.md`

Important nuance:
- Historical and current re-audits differ over time; always cite the specific re-audit timestamp used.
- Approved exceptions are not “resolved”; they are explicit non-blocking waivers unless user reverses.

## 7. Universe / Dataset Reality

Current repository universe files:
- `massive_universe_stocks.json`: 12286
- `massive_universe_etf.json`: 4749
- `massive_universe_index.json`: 1 (`I:NDX`)
- `massive_universe_crypto.json`: 8

Interpretation:
- If UI “Index” shows empty, likely no processed BUY rows for index in current snapshot output, not necessarily missing file.

## 8. Task Backlog (Canonical)

Source of truth:
- `TFE_TODO_LIST.md`

Current high-level state:
- Item 1: PARTIAL
- Item 2: PARTIAL
- Items 3-17: OPEN/PARTIAL
- Item 18: PARTIAL
- Approved exceptions:
  - Section-23 enforcement
  - SafeMode forced runtime
  - SCE KAT/NIST/Dieharder runtime gating

## 9. Integrity Artifacts (This Realignment)

- Hash index:
  - `backups/load-directive-canonical-index-20260221T034914Z.tsv`
- Recent files index:
  - `backups/load-directive-recent-files-20260221T034914Z.txt`

Use these as the first comparison baseline in the next chat.

## 10. Anti-Hallucination Execution Pattern

For each future claim:
1. Identify exact source file(s).
2. Read source file(s).
3. Emit claim with evidence path.
4. If evidence missing, mark claim UNVERIFIED.

For each future deploy:
1. Create rollback artifact first.
2. Build from explicit source package.
3. Record deploy evidence folder.
4. Run authenticated smoke checks.
5. Record post-refresh counts and health.

## 11. Recommended Next Action (Single)

Recommended option:
- Start next chat by validating this protocol against live repository state and updating only one TODO item from `TFE_TODO_LIST.md` to completion before moving to the next.
