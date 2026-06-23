# TFE FIX BRIEF — Exit-price / P&L write-path integrity

**Date:** 2026-06-23
**Author:** c1 (diagnostic), for Joe's review
**Status:** BRIEF ONLY — no implementation. Splits into 3 sequenced deploys after approval.
**Severity:** Canonical-integrity. 308 of 487 closed positions since Apr 7 (63%) carry NULL `p_l`. Every realized-P&L forensic to date measured through this blind spot. The ledger's recorded realized since Apr 7 (−$652.55) covers only 179 of 487 closes (37%).

---

## ROOT CAUSE (one sentence)

Exit-price acquisition is **per-call-site, best-effort, and time-coupled to a single ~2-second poll**; there is no single canonical exit-price source, three close paths fetch the price from the wrong place (expired DAY-TIF entry-order legs) or not at all, and `ledgerClose` will happily write `status='closed'` with NULL price/p_l — so when the best-effort fetch misses, the economics are lost permanently and silently.

The canonical record of what actually filled — `/v2/account/activities/FILL` — is **never consulted by any close path.** That is the fix.

---

## SCOPE A — Diagnostic completion (read-only) — DONE

Call-site map. Every path that marks a position `closed`, and how each handles exit price:

| # | Call site | exit_reason(s) written | Price passed? | Failure mode |
|---|---|---|---|---|
| 1 | `sentinel_monitor.mjs:455` — killPosition main close | ch2_exit_tau_exhaustion, ch2_catastrophic_floor, ch2_exit_dk_collapse, ch2_exit_structural_harvest, ch2_exit_trailing_profit, ch2_exit_acceleration_complete, sentinel_spy_flip, sentinel_max_drawdown, sentinel_calamity, structural_exit_cut_structural | YES — from single 2s poll (`:441-448`) | **(b)** price arrives later than the one poll. On miss, `:458` skips close and retries; works for fast/liquid fills, nulls on slow fills / after-hours / API lag |
| 2 | `sentinel_monitor.mjs:381` — idempotent retry close | same as #1 | YES — polls the pending exit order | Good path; only reached if the order is still queryable and filled on retry |
| 3 | `sentinel_monitor.mjs:329` — qty≤0 branch | `${reason}_bracket_exit` | **NO** — `ledgerClose` called with no price arg | **(a)** price is obtainable via a fill query, simply not fetched |
| 4 | `sentinel_monitor.mjs:356` — already-closed inside killPosition | `${reason}_bracket_exit` | Attempts ENTRY-order legs (`:346-352`) → ~always null | **(c)** wrong source — DAY-TIF entry legs expire/cancel and never carry the exit fill |
| 5 | `sentinel_monitor.mjs:751` — zombie-check fallback | `bracket_tp_sl_exit` (**a guess**) | Attempts ENTRY-order legs → null | **(c)** zombie; wrong source **and** invented reason. This is the 12 from the original forensic |
| 6 | `sentinel_monitor.mjs:992` — ch3 bracket path | `ch3_bracket_exit` | **NO** — no price arg | **(a)** no fetch at all → 55/55 NULL all-time |
| 7 | `circuit_breaker.mjs:152` — standalone 3% fuse | `circuit_breaker_3pct` | **NO** — direct UPDATE, sets `exit_filled_at` only, never price/p_l | **(a)** the sell-order fill is obtainable, never fetched |
| 8 | (admin) `financial_rules.mjs:324` ADMIN_EXIT_REASONS | stale_position_cleanup, manual_close_stale, manual_portfolio_reset | N/A — non-economic by design | **Excluded from scoring. NULL p_l is correct here — do NOT backfill these.** |

**Key findings:**
- Paths #3, #6, #7 never fetch price. Paths #4, #5 fetch from the **wrong source** (entry legs that expired under DAY TIF). Only #1/#2 fetch correctly, and #1 is time-coupled to one 2s poll.
- `ledgerClose` (`sentinel_monitor.mjs:241`) computes p_l correctly **when given a price** (guard `:245`). It is not the defect. The defect is upstream supply + the absence of a write-time invariant.
- `exit_filled_price` and `p_l` are **always NULL together** (`null_pl_but_have_exitpx = 0`) — confirming price never arrives, rather than p_l-calc failing on a present price.
- Improving over time (Apr 85% NULL → May 68% → Jun 28%) as liquid same-day fills increasingly catch the 2s poll — but never closed, and structurally fragile.

---

## SCOPE B — Forward fix (code change; requires Joe approval to deploy)

**B1. Single canonical exit-price source.** New helper (proposed `exit_fill.mjs`):
`async function resolveExitFillPrice({ ticker, shares, exitOrderId, sinceISO })` →
1. If `exitOrderId` known: poll `/v2/orders/{id}` with a **bounded retry** (e.g. 5× over ~10s) for `filled_avg_price`.
2. Fallback / primary for zombie cases: query `/v2/account/activities/FILL?...` for sell fills matching `ticker` + `qty` within a window around close time; return the (qty-weighted) fill price.
3. Return `{ price, source, confidence }` or `null`.

Every close path (#1, #3, #4, #5, #6, #7) routes through this before writing. Kills the wrong-source (entry-leg) logic at `:346-352` and `:738-748` entirely.

**B2. Stop inventing reasons.** The zombie fallback (`:751`) must NOT write `bracket_tp_sl_exit` as a guess. If the true exit can't be determined from a fill query, write `exit_reason='unknown_zombie_404'` + a `rationale_json` note. Never emit a structured strategy reason when the truth isn't known. (Same principle for the `${reason}_bracket_exit` suffix at #3/#4 — only append `_bracket_exit` if a fill query confirms a bracket leg actually filled.)

**B3. Write-time invariant.** `ledgerClose` refuses to write `status='closed'` unless **both** `exit_filled_price` AND `p_l` are populated (except the admin reasons in #8, which are explicitly non-economic). If the caller lacks both, the close **fails loudly** (throws / logs CRITICAL / leaves the row open for retry) rather than silently leaving NULLs.
- **Design subtlety (the main risk):** a sell that genuinely can't be priced *yet* must **defer and retry**, not hard-fail forever. The invariant pairs with a bounded-retry + deferred-close queue: position stays open, re-attempts next cycle, and only escalates to `unknown_zombie_404` after N cycles. Done wrong, this invariant could strand legitimately-closed positions as perpetually "open." This is where the design care goes.

**B4. circuit_breaker.mjs** routes its liquidation sells through the same `resolveExitFillPrice` + shared close, instead of the bare UPDATE at `:150-157`.

---

## SCOPE C — Historical backfill (one-time, after forward fix deploys)

Standalone script (pattern proven in this forensic — recovered 12/12 bracket exits cleanly):
1. Walk all closed rows since 2026-04-07 with NULL `p_l` **excluding ADMIN_EXIT_REASONS** (#8).
2. For each: query `/v2/account/activities/FILL` for sells matching `ticker`, `qty`, and a window around `exit_filled_at`.
3. **Unique match** → populate `exit_filled_price`, compute `p_l`, append `rationale_json` note `backfill_recovered` with source.
4. **Zero or multiple matches** → leave NULL, flag `backfill_unresolved` for manual review.
5. Report: recovered / unresolved / no-entry-price (unrecoverable) counts + net realized-P&L correction.

Runs **once, in production, AFTER the forward fix is live** (so the gap stops growing while history is reconciled). Excludes rows with no `entry_filled_price` (78 of 308 — can't compute p_l regardless).

---

## SCOPE D — Lessons-learned spec update (PROJECT_STATE §7.1, item 7)

> **Canonical record blind spot.** When the ledger write path silently fails to record exit price, every downstream forensic measures through the resulting blind spot. Symptoms: NULL economic fields on closed rows, zombie-check fallback labels, realized P&L computed over partial population. Effect: months of decisions made on incomplete data, masquerading as canonical. Future protections: write-time invariants that refuse incomplete economic records; query-time invariants that refuse to compute aggregate P&L from populations with NULL `p_l` rates above a threshold.

(Deploy 3 — appended after forward fix + backfill land. Drafted; not yet written to the file.)

---

## SEQUENCING

1. **Deploy 1 — forward fix (Scope B).** Stops the bleed. Behavioral validation: simulated multi-day daemon cycles with slow/after-hours fills to exercise the deferred-close retry and the invariant.
2. **Deploy 2 — backfill (Scope C).** Once. After a dry-run report Joe reviews. Reconciles history.
3. **Deploy 3 — spec update (Scope D).** Documents the pattern.

One change per deploy. No "while we're in here."
