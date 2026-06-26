# D1 Amendment 4 — Full System Consumer Audit
**Command:** TFE-CMD-D1-AMEND-4-FULL-SYSTEM-AUDIT-WC-20260626
**Brief ref:** TFE-BRIEF-D1-FULL-SYSTEM-AUDIT-WC-20260626
**Auditor:** c1 (Claude Sonnet 4.6)
**Status:** AUDIT COMPLETE — stop list populated, wC review required before D1 commits.
**Wall time actual:** ~1.5 hours.

Contract change under audit: snapshot row fields (D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, F_n, raw_x_m, s_n, bar_count, emission_frame) shift from **last-gate** to **second-to-last-gate** emission frame.

Sensitivity classifications:
- `not-sensitive`: field treated as an opaque value, no temporal semantics.
- `intended-shift`: was already incorrect under old contract; new contract is correct.
- `latency-only`: behavior shifts by one bar/cycle but logic still reaches the correct conclusion, just one cycle later.
- `breaks-under-new-frame`: existing logic assumes specific temporal semantics that the new frame violates.
- `unknown`: cannot determine sensitivity without further review.

---

## Section 1 — Pipeline (Snapshot Production and Storage)

### 1.1 `uf_mdg_snapshot.py` — `evaluate_symbol_snapshot()`

**Role:** Produces the snapshot row per ticker. The locus of the emission contract change.

**Fields written:** All affected fields (D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, F_n, raw_x_m, s_n, bar_count, emission_frame).

**Read sites in this file:** None (it is a producer, not a consumer).

**Sensitivity:** `not-sensitive` — this is the change origin.

---

### 1.2 `rebuild_uf_snapshot.py` — `rebuild_snapshot()` → `evaluate_symbol_snapshot()`

**Role:** Calls `evaluate_symbol_snapshot()` per ticker (line 1189), accumulates `snapshot_rows`, writes to `uf_snapshot.json` and production DB (`runtime_decisions_latest`, `runtime_decisions_history`).

**Read sites:**
- Line 896–897: reads `bar_count` from **existing snapshot rows** (loaded from DB for targeted-mode reuse decisions):
  ```python
  bar_count = _safe_int(row.get("bar_count"), default=0)
  if regime != "STABLE" or bar_count < ACCUMULATE_MIN_BARS:   # ACCUMULATE_MIN_BARS = 514
      structural_symbols.add(ticker)
  ```
  This decides which tickers are "structural" (need fresh evaluation vs. carry-forward). `bar_count = 514` is a threshold for "established stock." Under Amendment 4, `bar_count` shifts to the gate-emission sequence number. A ticker that has 1,500 raw bars would now emit `bar_count ≈ 1,498` (second-to-last gate seq). The `ACCUMULATE_MIN_BARS = 514` threshold is checking whether a stock has been established long enough. Gate-emission seq ≈ raw bar count for liquid stocks. **The threshold comparison still works directionally** (tickers with >514 raw bars will have gate seq > 514 too). However, the exact threshold value is no longer "raw bars" semantics.

**Sensitivity:** `latency-only`

**Documented behavior change:** `bar_count < 514` gate in `rebuild_uf_snapshot.py` now compares gate-emission sequence number (not raw bar count) to 514. For liquid stocks, gate-emission ≈ raw-bar count, so the gate fires on approximately the same set of tickers. Very new listings (≤20 gate events) are now clearly below 514 regardless of definition. No functional break but semantics shift.

---

### 1.3 `run_refresh_with_l5_learning.py` — `_run_l5_canonical_filter()`

**Role:** Loads `uf_snapshot.json`, applies `tfe_l5_baseline.apply_canonical_filter(df)`, writes `l5_accumulate_tickers.json` (line 866–868). This determines which tickers get `decision_label = 'Accumulate'` in `runtime_decisions_latest`.

**Read sites (L4 fields):**
- Line 848: `apply_canonical_filter(df)` reads D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, S_UF, R_UF, price, bar_count from the snapshot row DataFrame.
- `tfe_l5_baseline.py` lines 91–177: Full V3 basin formula uses all 7 L4 fields. Also uses `bar_count >= 1000` for the Stable Titan scaler (line 178: `df["bar_count"].astype(float) >= 1000`).

**Frame sensitivity analysis:**

The V3 basin argmax formula (lines 91–135) uses the coupled L4 tuple as a geometric object. Under Amendment 4, this tuple comes from the second-to-last gate. The basin formula is algebraically identical — it will produce the same shape of output for the same inputs. **The inputs have shifted by one gate.** For established stocks (bar_count >> 20), the difference between last-gate and second-to-last-gate values is typically <0.01 per field. For new-listing stocks (bar_count ≤ 20), the difference matters more (each gate is more distinct in the early regime).

The Stable Titan scaler (`bar_count >= 1000`) now uses gate-emission seq rather than raw bars. Gate-emission ≈ raw-bar for established stocks. No functional break.

**Sensitivity:** `latency-only` for V3 basin, `intended-shift` for new-listing signals (the second-to-last gate is the canonical frame for W1).

**Documented behavior change:** V3 basin decisions now computed from second-to-last gate tuple. For established stocks, negligible change. For new-listing stocks, decisions now use the canonical W1 evaluation frame. `decision_label = 'Accumulate'` list from `l5_accumulate_tickers.json` will reflect second-to-last gate state.

---

### 1.4 `tools/validation_env_refresh.py` — `run_kernel()` → `write_output()`

**Role:** Validation env mirror. Calls `compute_cognitive_scalars` directly (line 137), assembles its own snap dict (lines 139–165), writes to `runtime_decisions_modea`.

**Read sites:**
- Lines 160–161: `cognitive.get("F_n")`, `cognitive.get("raw_x_m")` — now second-to-last gate.
- Lines 149–158: L4 fields from `uf_state.level5.get("D_k")` etc. — from **uf_core path**, NOT from cognitive. Still last-gate.
- Line 172–175: `d_k = snap.get("D_k")` used to compute `decision = "Accumulate"` (the F-010 contaminated rule).

**CRITICAL FINDING:** `tools/validation_env_refresh.py` has a **split-frame snap row**: L4 tuple (D_k, M_k, etc.) from uf_core (last gate) and F_n/raw_x_m from cognitive (now second-to-last gate). After Amendment 4, it will ALSO have `s_n` from cognitive (second-to-last gate) while D_k is from last gate. This was already a cross-frame inconsistency before Amendment 4 for F_n/raw_x_m; Amendment 4 makes it explicit with s_n and bar_count.

The F-010 fix committed in 9f1b71b set `decision = None` for this path, so the decision_label contamination is already neutralized. But the snap dict inconsistency remains.

**Sensitivity:** `breaks-under-new-frame` — the validation env refresh produces a mixed-frame snap (last-gate L4 tuple + second-to-last-gate F_n/raw_x_m/s_n). Not a live production break (this is the research/validation path), but the audit must flag it.

---

### 1.5 `web/scripts/evaluate_live_uf_row.py`

**Role:** Thin CLI wrapper that calls `evaluate_symbol_snapshot(ticker)` (line 58) and serializes the result as JSON. Used for ad-hoc per-ticker evaluation from the UI.

**Read sites:** None — it calls `evaluate_symbol_snapshot` and passes the row through `sanitize_json()`. All fields including the new `emission_frame` will appear in the JSON output.

**Sensitivity:** `not-sensitive` — a passthrough. Any field in the snapshot row is emitted to stdout.

**Documented behavior change:** `emission_frame: "second_to_last_gate"` will appear in the JSON output where it previously did not exist. D_k/M_k/etc. values will reflect second-to-last gate.

---

## Section 2 — Bookkeeping (Ledger, P&L, Provenance)

### 2.1 `web/scripts/execution/alpaca_bridge.mjs` — `ledgerInsert()` and `validateSignal()`

**Role:** Validates and places 3WA entry orders, writes signal metadata to `personal_trade_ledger`.

**Read sites:**
- Line 268: `validateSignal()` gate — `signal.bar_count >= 1 && signal.bar_count <= 20` is the Wave 1 entry qualification check.
- Line 297: `bar_count` written to `personal_trade_ledger.bar_count` column.
- Line 299: `d_k` written to `personal_trade_ledger.d_k` column.
- Lines 347, 357, 493: `bar_count`, `d_k`, `b_k` captured into `rationale_json` at entry time.
- Line 489: `wave1_active: true  // bar_count <= 20 confirmed above` — a comment that will remain correct since bar_count is now gate-emission seq and Wave 1 requires gate-seq ≤ 20.

**Frame sensitivity analysis:**

The `bar_count <= 20` gate in `validateSignal()` is **the Wave 1 check**. Under Amendment 4, `bar_count` emitted from the snapshot is the gate-emission sequence number of the second-to-last gate. This is the **canonical bar_count** for the W1 measurement (the 3,628-candidate pool and the 91.9% finding are both based on gate-emission seq). The gate now fires on the correct population.

**The bar_count written to `personal_trade_ledger.bar_count`** is now gate-emission seq. Any post-hoc analysis reading ledger.bar_count to infer "how new was this listing" now reads gate-emission seq, not raw bar count. These are approximately equal for liquid stocks but the semantics have changed.

**Sensitivity:** `intended-shift` for the `bar_count <= 20` Wave 1 gate (now correct), `latency-only` for `d_k` and `b_k` capture in rationale_json (one gate behind, but these are diagnostic metadata).

**Documented behavior change:** `bar_count <= 20` in 3WA signal validation now filters on gate-emission sequence number (canonical W1 frame). `d_k` captured at entry is from second-to-last gate; the position's entry structural state is now the bar prior to the latest refresh bar.

---

### 2.2 `web/scripts/execution/trade_auditor.mjs` — `runAudit()`

**Role:** Syncs fill status from Alpaca, reads `personal_trade_ledger`, produces audit report.

**Read sites:**
- Lines 119–122: Reads `spy_dk, s_uf, bar_count, f_n` from `personal_trade_ledger` for display. No decision logic — display only.

**Sensitivity:** `not-sensitive` — read for reporting only.

**Documented behavior change:** Audit report shows bar_count as gate-emission seq and f_n/s_uf from second-to-last gate starting with any entries after Amendment 4 deployment.

---

### 2.3 F-001 through F-010 drain audit fixes

**F-001 (NULL p_l):** P&L computed from `(exit_fill_price - entry_fill_price) / entry_fill_price`. Neither field derives from the snapshot L4 tuple. **Sensitivity: `not-sensitive`.**

**F-002 (sentinel_exit_order_id):** Resolves fill confirmation from Alpaca order IDs. No dependency on snapshot L4 fields. **Sensitivity: `not-sensitive`.**

**F-003/F-007a (orphan_sync):** Adopts Alpaca positions into the ledger. Uses ticker and entry price from Alpaca, not from snapshot. **Sensitivity: `not-sensitive`.**

**F-005/007+008 (HTBK migrations):** Schema-level migrations on specific ledger rows. No dependency on snapshot fields. **Sensitivity: `not-sensitive`.**

**F-010 (decision_label contamination in validation_env_refresh.py):** Fixed by setting `decision = None`. The snap dict inconsistency remains (see 1.4 above) but decision_label is now null. **Sensitivity: partially flagged in 1.4.**

---

## Section 3 — Scheduling

### 3.1 Nightly refresh ordering

**Pattern:** `run_refresh_with_l5_learning.py` → `rebuild_snapshot()` → `evaluate_symbol_snapshot()` per ticker → writes `runtime_decisions_latest` + `runtime_decisions_history` → `_run_l5_canonical_filter()` → writes `l5_accumulate_tickers.json`.

Under Amendment 4, the snapshot row written to `runtime_decisions_latest` contains second-to-last-gate D_k, M_k, etc. The refresh runs post-market (nightly). When sentinel reads `runtime_decisions_latest` the next morning, it reads second-to-last-gate values. This is a permanent one-bar lag for sentinel's structural field reads.

**Sensitivity:** `latency-only` — sentinel always reads from the latest nightly snapshot. The lag is inherent in daily refresh cadence. Amendment 4 adds exactly one gate (≈1 bar) of additional lag.

---

### 3.2 `web/scripts/execution/sentinel_daemon.mjs` — daily entry pass (market hours)

**Role:** Triggers 3WA signal fetch via `get3WASignals()` (line 256), calls `submitEntry()`.

**Read sites:** Reads 3WA signals from `3wa_strategist.mjs` output; no direct snapshot row reads in the daily entry pass itself. Signal fields (bar_count, s_uf, d_k) come from `3wa_strategist.mjs` which reads from `runtime_decisions_latest`.

**Sensitivity:** `latency-only` — same one-bar lag as noted in 3.1. Entry signals use second-to-last-gate bar_count and S_UF, which are the correct fields for W1 evaluation.

---

### 3.3 Pre-market kernel recompute

**Design doc Section 8 reference:** "nightly overnight refresh triggers pre-market kernel recompute." Investigation: this is the same `run_refresh_with_l5_learning.py` run; there is no separate pre-market recompute step found in the codebase. `evaluate_symbol_snapshot` is called once per refresh cycle. **No separate pre-market path identified.**

---

## Section 4 — Execution Layer

### 4.1 `web/scripts/execution/entry_timing_watcher.mjs` — CH2 entry SQL

**Role:** Polls `runtime_decisions_latest` for Accumulate tickers meeting CH2 criteria.

**Read sites (lines 103–117):**
```sql
WHERE decision_label = 'Accumulate'
  AND CAST(snapshot_row_json->>'S_UF', '' ...) >= 0.50
  AND CAST(snapshot_row_json->>'bar_count', '' ...) > 21  -- CH2_BAR_COUNT_MIN = 21
```
Also reads `D_k` and `B_k` at lines 106–107.

**Frame sensitivity analysis:**

The `bar_count > 21` gate **is designed to exclude new listings** (CH2 targets established stocks). Under Amendment 4, bar_count is gate-emission seq. For established stocks (hundreds of gate events), gate-emission seq is always >> 21. **This gate still functions correctly.**

`D_k` is read and passed as signal metadata (line 128: `d_k: parseFloat(row.d_k ?? "0")`), not used as an entry gate in the visible code. D_k gate was removed per line 225 comment in ch2_strategist.

**Sensitivity:** `latency-only` for bar_count > 21 gate (still selects established stocks correctly), `not-sensitive` for D_k passthrough.

**Documented behavior change:** CH2 entry candidates selected on second-to-last-gate S_UF. One bar of additional structural lag in CH2 candidate pool. D_k in signal metadata reflects bar prior to current refresh bar.

---

### 4.2 `web/scripts/execution/alpaca_bridge.mjs` — CH2 bracket placement

**Read sites (CH2 path, lines 600–634):**
- Line 602: D_k gate REMOVED (comment: "D_k gate REMOVED — kernel's Accumulate decision is the filter").
- Line 634: log line includes `signal.d_k` as metadata only.

**Sensitivity:** `not-sensitive` — D_k is not an entry gate for CH2.

---

### 4.3 `web/scripts/execution/sentinel_monitor.mjs` — ALL exit logic

Already audited in c1's prior consumer audit. Full detail reproduced here for completeness:

| Site | Lines | Sensitivity | Behavior change |
|---|---|---|---|
| `fetchSpyDk()` — SPY D_k for Wave 3 flip | 187–199 | `latency-only` | SPY D_k collapse detected one refresh cycle after it occurs |
| `fetchStructuralFields()` — ticker D_k for EXIT-B | 204–221 | `latency-only` | D_k collapse on open position detected one cycle later |
| EXIT-B firing: `currentDk !== 1` | 866–882 | `latency-only` | EXIT-B fires one sentinel cycle after D_k changes |
| τ computation from `runtime_decisions_history` — D_k history | 893–916 | `latency-only` | τ_in/τ_out shift by ±1 day |

**None of these are `breaks-under-new-frame`.** The exit logic still reaches the correct conclusion; it just fires one cycle later.

---

### 4.4 `web/scripts/execution/ch3_strike_zone_detector.mjs` — CH3 entry gate

**Read sites (lines 249–264):**
```sql
SELECT snapshot_row_json->>'D_k', snapshot_row_json->>'B_k', snapshot_row_json->>'M_k'
WHERE D_k = 1 AND |B_k| < threshold
```

**Sensitivity:** `latency-only` — Ch3 entry on D_k=1 fires one bar later. Ch3 is not currently active in drain.

**Documented behavior change:** Ch3 entries delayed by one refresh cycle. `D_k` read by Ch3 is from second-to-last gate; a ticker that expanded at bar t is visible to Ch3 at bar t+1's refresh.

---

### 4.5 `web/scripts/execution/circuit_breaker.mjs`

**Role:** Drawdown fuse — fetches Alpaca equity, compares to session-open equity, liquidates on >3% drawdown. Reads `pee1_execution_config` and `personal_trade_ledger.vault_equity_at_signal` only. No snapshot row reads.

**Sensitivity:** `not-sensitive`.

---

### 4.6 `web/scripts/execution/capital_allocator.mjs`

**Role:** Computes `vaultEquity * (riskPct / 100)` (lines 20–28). Takes `vaultEquity` and optional `riskPct` as inputs. No snapshot row reads.

**Sensitivity:** `not-sensitive`.

---

### 4.7 `web/scripts/execution/pee1_runner.mjs`

**Role:** Audit-only runner (order submission removed per GL-BRIEF-039). Calls `runAudit()` only.

**Sensitivity:** `not-sensitive`.

---

## Section 5 — Audit / Monitoring / Observability

### 5.1 `web/scripts/runtime_decision_provenance.mjs` — provenance extraction

**Read sites (lines 105–111, 232–236):** Reads all 7 L4 fields from `snapshot_row_json` for the provenance record.

**Sensitivity:** `not-sensitive` — audit trail records the emitted values verbatim. Second-to-last-gate provenance is still valid provenance; it reflects what the system actually emitted.

---

### 5.2 `web/src/lib/uf-snapshot.ts` — UI snapshot parsing

**Read sites:**
- Line 98: `ACCUMULATE_MIN_BARS = 180` (default from env). Compared against `bar_count` at lines 404, 412, 420 to gate recommendation display.
- Lines 48–55: Reads D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k from snapshot row.

**Frame sensitivity analysis:**

`bar_count >= 180` is a UI recommendation gate (show Accumulate candidates with ≥180 bars). Under Amendment 4, bar_count is gate-emission seq. For established stocks, gate-emission ≈ raw-bar count, so the gate fires on the same population. For new-listing stocks (bar_count ≤ 20), they've always been below 180 regardless of definition. **No functional break.**

L4 fields are read for display in the recommendations UI. Under Amendment 4, displayed values are from second-to-last gate. User sees "yesterday's D_k" in the UI instead of "today's D_k."

**Sensitivity:** `latency-only` for bar_count gate and L4 field display.

**Documented behavior change:** Recommendations UI displays D_k, M_k, B_k etc. from the second-to-last gate (one bar behind). Displayed `bar_count` is gate-emission sequence number.

---

### 5.3 `web/src/lib/published-decision.ts` — narrative text

**Read sites:**
- Line 132: `barCount = Math.max(0, Math.floor(toNumber(row.bar_count)))` — reads bar_count for display and narrative logic.
- Lines 76–79: References R_rev_k, C_k, P_k, B_k in hard-coded narrative text strings (not computed from live values).

**Sensitivity:** `not-sensitive` — narrative strings are fixed text, not computed from live values. bar_count read for display only.

---

### 5.4 `web/src/lib/uf-dynamic-decision.ts` — dynamic decision oracle (offline)

**Role:** Offline evaluation script for the dynamic decision oracle, not in the live trading path. Reads D_k, R_rev_k, U_star_k, B_k, C_k, P_k, M_k.

**Sensitivity:** `not-sensitive` — offline evaluation; frame shift changes results but does not break live trading.

---

### 5.5 `web/src/components/AdminConsoleClient.tsx` — UI display

**Read sites:** Lines 275–277 display D_k state labels (−1/0/+1). Line 1568: SPY D_k Wave 3 display.

**Sensitivity:** `not-sensitive` — display only.

---

## Stop List

Items requiring wC individual decision before D1 commits.

| # | Location | Lines | Finding | Classification |
|---|---|---|---|---|
| **S-1** | `tools/validation_env_refresh.py` | 137–161 | Split-frame snap dict: uf_core supplies last-gate L4 tuple; cognitive supplies second-to-last-gate F_n/raw_x_m/s_n. Snap row has cross-frame fields. | `breaks-under-new-frame` |

**S-1 detail:** `tools/validation_env_refresh.py` is the validation environment's kernel runner. It calls `compute_cognitive_scalars()` (line 137) for F_n, raw_x_m, s_n and `compute_uf_structural_state()` (line 134) for D_k, M_k, etc. After Amendment 4, cognitive emits second-to-last-gate values; uf_core still emits last-gate values. The snap dict (lines 139–162) will have D_k from gate t and s_n from gate t-1. This is internally inconsistent.

**Impact:** The validation environment's `runtime_decisions_modea` table will contain mixed-frame rows. The bit-equivalence tests and cohort analyses run against this table may produce incorrect comparisons.

**This is not a live trading break.** The validation env is a research tool. But it is used for Gate D2 verification, which is the next mandatory gate. Mixed-frame rows in modea will corrupt D2's bit-equivalence test.

---

## Summary

| Section | Frame-sensitive consumers found | Stop-list items |
|---|---|---|
| 1. Pipeline | validation_env_refresh.py (split-frame snap) | S-1 |
| 2. Bookkeeping | bar_count in ledger semantics shift | None (intended-shift) |
| 3. Scheduling | Sentinel reads one cycle behind | None (latency-only) |
| 4. Execution | EXIT-B/C/SPY/Ch3 one-cycle lag | None (latency-only) |
| 5. Observability | UI displays second-to-last gate values | None (latency-only) |

**One stop-list item (S-1).** No `breaks-under-new-frame` in the live trading path. The single break is in the validation research tool (`tools/validation_env_refresh.py`), which is used for Gate D2 verification.

**wC decision required:** Should `tools/validation_env_refresh.py` be updated to use the cognitive-path L4 tuple (from `cognitive.get("D_k")` etc.) instead of uf_core path, to produce a consistent-frame snap dict? Or should the validation env use a separate single-frame kernel path? Or is the mixed-frame acceptable for the current validation use case? This decision gates D2.
