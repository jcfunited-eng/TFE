# TFE Handoff — c1 Session End 2026-07-01

**For:** Next c1 session  
**Branch:** `codex/persistent-etl-update-20260326`  
**Waiting on:** wC next dispatch (do not push or deploy without wC confirmation)  
**Project authority:** wC on TFE. Eve on Guala. These are separate projects — never cross-contaminate commits, branches, or context.

---

## CRITICAL: PROJECT SEPARATION RULE

You are working on **TFE only**. The workspace also has Guala project files. One Guala doc (`GL-RPT-BRIDGE-AUDIT-FIXES-C1-20260701-67.md`) accidentally landed on the TFE deploy branch this session and had to be rebased out. Before every commit, run:

```bash
git diff --name-only <parent_sha> HEAD
```

Any file starting with `GL-`, `guala`, `substrate`, `dsf_ai_service/`, or in `docs/GL-*` must NOT be in a TFE commit. If found, rebase it out before pushing.

---

## CURRENT BRANCH STATE

```
Branch: codex/persistent-etl-update-20260326
HEAD:   28f9f57  (LOCAL ONLY — not yet pushed to origin)
Parent: 784b194  (last pushed SHA — tfe-web-task:555 is deployed from this)
```

**28f9f57 is D4.6 — not pushed, not deployed.** Val-env fixture tests all passed (5/5). Waiting for wC confirmation to push.

### Branch history (recent):
```
28f9f57  d4.6: Fix CB-1 session-open equity + CB-2 silent liquidation write
784b194  d4.5: Fix bracket order-ID write-path (pushed, deployed tfe-web-task:555)
8520238  d4:   Fix killPosition asset_not_active reconcile
5439422  ops:  Raise runtime_postgres_sync ceiling to 1800s
f89f7aa  d3:   Add EXIT-TIME (20-day default close)
6038e30  d2:   Wire Wave 1 canonical selection in 3wa_strategist.mjs
9de8471  d1:   Amendment 4 — canonical evaluation frame
```

---

## WHAT D4.6 CHANGED (28f9f57)

**Files changed from 784b194:**
- `web/scripts/execution/circuit_breaker.mjs` — CB-1 + CB-2 fixes
- `web/scripts/execution/sentinel_monitor.mjs` — CB-1 fix
- `web/scripts/execution/tests/circuit_breaker_test.mjs` — new smoke test (20/20 pass)

**CB-1 fix:** Both `circuit_breaker.mjs` and `sentinel_monitor.mjs` used `vault_equity_at_signal` from ledger (today's earliest signal) as session-open equity reference. On quiet days (zero signals, which Wave 1 produces by design) this fell back to `equityNow` → drawdown=0 → breaker silently disabled. Fixed to use `Alpaca last_equity` (previous close) as reference in both files.

**CB-2 fix:** `liquidateAllPositions` in `circuit_breaker.mjs` had a bare `.catch(e => console.error(...))` on the ledger UPDATE. Extracted `closePositionInLedgerWithRetry()` using the D4.5 pattern: 3 attempts × 500ms backoff, `rationale_json` fallback breadcrumbs, CRITICAL log on both-fail.

**Val-env test results:**
- Test 1: Alpaca paper returns `last_equity=97815.50`, `equity=98716.65` — field present and valid
- Test 2: 99% threshold → `triggered: false` ✓, `equityOpen(last_equity)` tag in log ✓
- Test 3: 0.001% threshold on up-day → `triggered: false` (correct, negative drawdown) ✓
- Test 4: Quiet-day (zero ledger rows today) → `equityOpen=last_equity`, NOT `equityNow` ✓ (regression guard)
- Test 5: Static checks clean, import clean ✓

---

## OPEN PRODUCTION ISSUES (not fixed in 28f9f57)

### 1. `TFE_ENTRIES_HALTED=1` in task def — ENTRIES STILL BLOCKED

The ECS task definition `tfe-web-task:555` has `TFE_ENTRIES_HALTED=1` baked in as a container env var. This was set during the HTBK migration (commit `efdc3cd`, 2026-06-24) and has been in every task def since.

**Effect:** All automatic entries are halted. Auto-TFE toggle=ON in the UI but the yellow banner "Engine entries halted — manual orders still execute" will persist until this is cleared.

**Fix when wC approves:** Register new task def with `TFE_ENTRIES_HALTED` removed or set to `0`, then `aws ecs update-service --force-new-deployment`. No code change needed. Do NOT do this without explicit wC instruction.

### 2. CWAN + HTBK phantom re-adoption loop

Production DB has the following CWAN/HTBK state:
- CWAN: rows 8090 (closed, D4), 9350 (closed, phantom re-adoption fixed today)
- HTBK: rows 364 (closed, migration 008), 7532 (closed, migration 007), 9334 (closed, D4), 9351 (closed, phantom re-adoption fixed today)

**Root cause:** Alpaca paper account still holds phantom CWAN and HTBK positions (paper accounts don't auto-clear merged/lost positions). Every time the sentinel restarts, the orphan sync adopts them as new `filled` rows. They hit `killPosition`, get "not active", and `exit_blocked=true` is set.

**Current mitigation:** D4.5 changed the `exit_blocked` path to check if Alpaca position is 404 before blocking. But the ORPHAN ADOPTION (not killPosition) is what creates the new rows. The orphan sync in `runSentinel()` checks `/v2/positions` and inserts rows for any Alpaca position not in the ledger. This is the re-adoption path.

**Not yet fixed.** D4.7 or manual: either disable orphan adoption for known phantom tickers, or clear them from the Alpaca paper account.

### 3. 168 unrecoverable rows in personal_trade_ledger

From D4 F-001 backfill: 168 closed rows still have `p_l IS NULL` and `rationale_json->>'f001_backfill' = 'unrecoverable'`. These are bracket exits where Alpaca fill activity didn't match within 2h. The D4.5 fix prevents future recurrence. Past nulls stay as-is.

---

## PRODUCTION DB STATE (as of session end)

```
realized P&L: +$969.24 (post-D4 backfill, 154 rows recovered from Alpaca)
open positions: 0 (CWAN id=9350 and HTBK id=9351 re-adoption rows closed)
closed trades: 520
null p_l rows: 178 (168 unrecoverable + ~10 no exit timestamp)
```

**Note on portfolio page:** Page shows `REALIZED: $969.24`, `OPEN POSITIONS: 2` may still show until next page refresh after the most recent fixes propagated.

---

## RELEVANT DEPLOY FACTS

- Deploy command: `GIT_PAGER=cat bash /workspaces/Tao_Financial_Engine/tools/deploy_to_prod_with_evidence.sh`
- Prerequisites: node/npm, jq, zip, awscli all available; workspace on correct branch
- After container rebuild, often need: `apt-get update && apt-get install -y nodejs npm jq zip`
- Paper Alpaca keys are NOT in workspace `.env` — they're in ECS secrets. Use `aws secretsmanager get-secret-value --secret-id arn:aws:secretsmanager:us-east-1:418384447921:secret:tfe/market-data/prod-tnxubW`
- Local postgres for val-env: start with `pg_ctlcluster 17 main start`; DB name: `tfe_validation`

---

## FIRST COMMAND FOR NEXT c1

```
git -C /workspaces/Tao_Financial_Engine rev-parse HEAD
git -C /workspaces/Tao_Financial_Engine branch --show-current
git -C /workspaces/Tao_Financial_Engine log --oneline codex/persistent-etl-update-20260326 -5
git -C /workspaces/Tao_Financial_Engine diff --name-only 784b194 codex/persistent-etl-update-20260326
```

Expected:
- HEAD = 28f9f57 (if on deploy branch) 
- Branch = codex/persistent-etl-update-20260326
- Log shows d4.6 at top, d4.5 as parent
- Diff shows exactly 3 TFE files (no GL- or Guala files)

If any GL- files appear in the diff, stop and rebase them out before proceeding.

---

## WHAT NEXT c1 IS WAITING FOR

wC will issue one of:
1. **"Push 28f9f57"** — then push branch (do not deploy, kill switch stays on)
2. **Next dispatch (D4.7, D4.8, D4.9, or other)** — build on top of 28f9f57
3. **"Clear TFE_ENTRIES_HALTED"** — register new task def without that env var, update service

Do NOT push 28f9f57 or deploy to ECS until wC explicitly approves. Do NOT clear `TFE_ENTRIES_HALTED` without explicit instruction.

---

## KEY FILE LOCATIONS

```
Branch:          codex/persistent-etl-update-20260326
Pending commit:  28f9f57 (D4.6, local only)
Deployed:        tfe-web-task:555 from SHA 784b194 (D4.5)
CB code:         web/scripts/execution/circuit_breaker.mjs
Sentinel:        web/scripts/execution/sentinel_monitor.mjs
3WA Strategist:  web/scripts/execution/3wa_strategist.mjs
Smoke test:      web/scripts/execution/tests/circuit_breaker_test.mjs
Deploy script:   tools/deploy_to_prod_with_evidence.sh
Design doc:      docs/TAO_FINANCIAL_ENGINE_PORTFOLIO_MANAGER_DESIGN_DOCUMENT_DEPLOYMENT_VERSION.md
```
