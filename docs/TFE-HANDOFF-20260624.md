# TFE Session Handoff — 2026-06-24 (end of day)

**To:** next c1 instance
**From:** c1 (web Claude, this session)
**Branch:** `codex/persistent-etl-update-20260326`
**Origin tip:** `6cf5f82` (feat: full-universe Mode A wrapper)
**Date:** 2026-06-24

Read the context brief first: `docs/TFE-C1-CONTEXT-BRIEF-20260624.md`
(canonical recovery for TFE rules, recovery sequence, drain posture).
Everything below is **what this session added on top of that brief.**

---

## FIRST FIVE MINUTES

1. Confirm kill switch: `TFE_ENTRIES_HALTED='1'` on the live ECS task.
   Verify via `aws ecs describe-services --cluster tfe-web-cluster --services tfe-web-service-lb`,
   then `describe-task-definition` on the serving revision. Paste actual value — do not assume.

2. Drain is ongoing. 19 positions open. No entries. Do not advocate for switch-on.

3. The local validation env (`tfe_validation` Postgres) is populated and operational.
   The equivalence gate is built and ready to run — that is the primary open item.

---

## TFE DRAIN STATE

Kill switch: `TFE_ENTRIES_HALTED='1'` (verified this session against live ECS task `tfe-web-task:551`).

**Open positions (live ledger, as of session end):** 19 `status='filled'` rows.
Drain continues via EXIT-B / EXIT-C / EXIT-F. Winners running uncapped.

**Committed-but-undeployed migrations (both run on next deploy):**
- `web/scripts/execution/migrations/007_htbk_merger_ledger_correction.sql`
  (`61ad23f`) — closes HTBK phantom to `p_l=-0.67`. Guard: `AND exit_filled_at IS NULL`.
- `web/scripts/execution/migrations/008_htbk_orphan_row_neutralize.sql`
  (`8bdbbd3`) — neutralizes orphan row id=364 to `p_l=0` with `orphan_note`.
  Pre-deploy verify: no new HTBK rows since commit. Neither has hit the DB yet.

---

## AUDIT REGISTRY

File: `docs/TFE-AUDIT-FINDINGS-DRAIN-PERIOD-20260623.md`

| # | Summary | Disposition |
|---|---|---|
| F-001 | Canonical-record blind spot — 63% of closes have NULL `p_l` across 17 exit reasons | BLOCKS-FRESH-RUN |
| F-002 | `sentinel_exit_order_id` holds submit-intent, not fill-truth (47% wrong) | BLOCKS-FRESH-RUN |
| F-003 | Duplicate-row write paths — 35 groups, 134 rows, ~30% of population since Apr 7 | Code path: BLOCKS-FRESH-RUN |
| F-004 | Shared-branch deploy SHA misdirection | TAGGED, NO FIX |
| F-005 | HTBK phantom twin — 007+008 fix on next deploy | DEPLOY-BEFORE-ARCHIVE |
| F-006 | NULL `entry_order_id` on live rows — resolved, root cause = orphan_sync | RESOLVED |
| F-007 | `orphan_sync` ungated reconciliation writer — live producer of F-003 | (a) gate now; (b) BLOCKS-FRESH-RUN |
| F-008 | `runtime_decisions_history` lacks uniqueness on (ticker, generated_at_utc) | TAGGED, NO FIX |
| F-009 | Recurrent shared-branch tangling wC vs Codex sessions | BLOCKS-FRESH-RUN (procedural) |

**F-007a (highest priority live code issue):** `orphan_sync` has written 13+ new
duplicate rows during the drain; latest was 2026-06-22. The fix is **one labeled-block
guard** in `sentinel_monitor.mjs` around line 544. Approved mechanism (from the
pre-deploy verify that stopped the brief's `return;`):

```js
orphanSync: {
  if (process.env.TFE_ENTRIES_HALTED === '1') {
    console.log('[SENTINEL] orphan_sync skipped — kill switch on (F-007a)');
    break orphanSync;
  }
  try { ...existing adopt body unchanged... } catch (orphanErr) { ... }
}
```

`break orphanSync` skips only the orphan-adopt, continues to exit logic at line 614.
One file, one guard, one deploy. Brief was approved but deploy was not issued — issue it.

**F-001 fix brief:** `docs/TFE-BRIEF-EXIT-PL-WRITE-PATH-FIX-20260623.md`
Full diagnostic done. True corrected realized P&L since Jun 8 = **−$479.60**
(ledger records −$953.15, missing 12 recoverable exits mislabeled `bracket_tp_sl_exit`).
Systemic: 63% of all closes missing `p_l`. Brief is complete; implementation
has three sequenced deploys: forward fix → backfill → spec update.

---

## VALIDATION ENVIRONMENT — FULLY OPERATIONAL

**Local DB:** `tfe_validation` Postgres on `/var/run/postgresql`, user=postgres.

| Table | Rows | Source | Notes |
|---|---|---|---|
| `runtime_decisions_latest` | 11,050 | Mode B (V4B import) | **Pure Mode B — Mode A must not write here** |
| `runtime_decisions_history` | 2,511,891 (90d) | Mode B (V4B import) | Pure Mode B |
| `runtime_decisions_modea` | 5,732 | Mode A full-universe run | `kernel_sha=6cf5f82`, Accumulate=464, Hold=5,268 |
| `runtime_symbols` | 11,050 | Mode B | ✓ |
| `personal_trade_ledger` | 9,333 | Mode B | mirror of prod |
| `daily_bars` | 9,760,074 | Prod S3 export | 2021-04-12 → 2026-06-24, 11,085 symbols |

Mode A ran against **cached production bars** (same bars as Mode B) — the gate
therefore tests pure kernel determinism, not data drift.

**Import script:** `tools/validation_env_import.py` (V4B, re-runnable, ~3.5 min).
**Mode A runner:** `tools/validation_env_refresh.py` (writes to `modea` exclusively).
**Full-universe wrapper:** `tools/modea_full_universe_runner.py` (`PYTHONPATH=$(pwd)`,
stock universe only ~5.8K, uses cached bars, adaptive 429 backoff).
**Python deps (installed):** `pandas`, `numpy`, `psycopg2-binary`, `python-dotenv`,
`requests`, `yfinance`. Always run with `PYTHONPATH=/workspaces/Tao_Financial_Engine`.

---

## PRIMARY OPEN ITEM: RUN THE V2 EQUIVALENCE GATE

**File:** `tools/validation_env_check.py` (built this session).

```bash
export PGUSER=postgres
PYTHONPATH=/workspaces/Tao_Financial_Engine python3 tools/validation_env_check.py
```

**Path 1 (GATE):** `runtime_decisions_latest` (Mode B, 11,050 tickers) vs most-recent
`runtime_decisions_modea` row per ticker (Mode A, 5,732 tickers). Comparison set
= tickers in both = ~5,732. Passes at ≥99% within §5.1 tolerance bands:
- `D_k`, `R_rev_k`, `P_k`: exact match
- `M_k`, `B_k`, `S_UF`, `R_UF`, `U_star_k`, `C_k`: `abs(diff) ≤ 1e-9`
- `F_n`, `raw_x_m`: `abs(diff) ≤ 1e-6`

**Path 2 (diagnostic):** history (Mode B) vs modea (Mode A) joined on
(ticker, generated_at_utc). Expected: **zero pairs** by construction (unique index
on each table; they share no timestamps). Zero is correct, not a failure.

**If Path 1 PASSES:** validation env is online, equivalence is demonstrated,
Mar 26 wire-in is unblocked.
**If Path 1 FAILS:** the JSON report at `backups/validation_env_equivalence_report_<ts>.json`
lists worst-delta tickers and fields — real data, real finding.

---

## BRANCH / GIT STATE (F-009 active)

The Codex session is concurrently active on this branch. **Do not reset/rebase
the main checkout.** Kernel files are byte-identical between the main checkout
and origin tip anyway — no sync is needed.

**All wC commits this session used isolated worktrees** (per the F-009 workaround):
```bash
git fetch origin codex/persistent-etl-update-20260326
ORIGIN_TIP=$(git rev-parse origin/codex/persistent-etl-update-20260326)
git worktree add --detach /tmp/tfe-wt-<purpose> $ORIGIN_TIP
cd /tmp/tfe-wt-<purpose>
# edit / commit / push HEAD:codex/persistent-etl-update-20260326
git worktree remove /tmp/tfe-wt-<purpose>
```

The main checkout is currently on branch `guala-live` (Codex's branch), HEAD ≠ origin tip.
Do not stash/reset/rebase it. Verify kernel files match origin via
`git diff origin/codex/persistent-etl-update-20260326 -- uf_core/` before acting
on any "out of date kernel" concern.

---

## ORDERED WORK QUEUE

1. **Run the V2 gate** — 5 min. PASS unblocks the fresh-ledger path.
2. **Deploy F-007a** — one-line guard in `sentinel_monitor.mjs`, one deploy.
   Stops new duplicate rows during drain. Do this before the next daily cycle.
3. **Deploy 007+008** — HTBK cleanup. Next ECS deploy. Pre-verify no new HTBK rows.
4. **F-001 forward fix** — when drain is stable. Three deploys per brief.
5. **Drain monitoring** — 19 positions, no action. Report to Joe on request.

---

## CANONICAL SOURCES

- Trade record: `personal_trade_ledger` via `/admin-console/auditor`
- Live system state: ECS live task definition env vars (not source files)
- Code: `codex/persistent-etl-update-20260326` **on origin** (not local HEAD)
- Specs: `TFE_Lessons_Learned_v1.tex`, `TFE_Specification_v3.0.tex`
- Audit registry: `docs/TFE-AUDIT-FINDINGS-DRAIN-PERIOD-20260623.md`
- P&L fix brief: `docs/TFE-BRIEF-EXIT-PL-WRITE-PATH-FIX-20260623.md`
- Context brief (rules + history): `docs/TFE-C1-CONTEXT-BRIEF-20260624.md`

When canonical source is unreachable, **report that fact and stop**.
Do not substitute Alpaca for the audit table.
