# Gate D2 Prep Inventory — 2026-06-26

**Command:** TFE-CMD-D1-CLOSURE-PLUS-D2-PREP-WC-20260626 Part B
**Author:** c1 (Claude Sonnet 4.6)
**Status:** INVENTORY ONLY — no recommended changes.

---

## 1. `runtime_decisions_history` Schema

Queried against local `tfe_validation` Postgres (Mode B import from production):

| Column | Type | Present? |
|---|---|---|
| `s_n` | DOUBLE PRECISION | **YES** — added by D1 migration (D1_add_s_n_to_runtime_decisions_history.sql) |
| `bar_count` | — | **NOT a top-level column.** `bar_count` lives inside `snapshot_row_json->'bar_count'` (verified: `snapshot_row_json ? 'bar_count'` = `true`). No top-level `bar_count` column exists. |
| `D_k` | — | **NOT a top-level column.** `D_k` lives inside `snapshot_row_json->'D_k'` (verified: `snapshot_row_json ? 'D_k'` = `true`). No top-level `D_k` column exists. |
| `prev D_k` | — | **NOT present in any form.** No column, no JSON key. Must be derived: for each ticker, order rows by `generated_at_utc` and lag `D_k`. No pre-computed previous-D_k is stored. |

**Top-level columns present:** `id`, `ticker`, `generated_at_utc`, `snapshot_row_json`, `decision_label`, `kernel_sha`, `source`, `s_n`.

**s_n column state:** Column exists with correct type. All rows have `s_n IS NULL` (zero rows with values, as of 2026-06-26). No production emission has occurred yet (ECS not yet deployed with D1 code).

---

## 2. `daily_bars` Coverage

Source: local `tfe_validation` DB, backfilled through Polygon backfill (walkforward setup).

| Metric | Value |
|---|---|
| Earliest date | 2020-04-01 |
| Latest date | 2026-06-24 |
| Total distinct tickers | 11,472 |
| Tickers with ≥ 252 bars anywhere in coverage | 9,349 |

Note: The 2,194-ticker walkforward universe was filtered from a 5,768-ticker quarantine list requiring full bar history from 2020-04-01 to 2026-03-24. The 9,349 tickers with ≥ 252 bars is the broader set across the full 11,472-ticker local DB.

---

## 3. `s_n` in Nightly Refresh

**Production write path:**

```
run_refresh_with_l5_learning.py
  └─ imports rebuild_snapshot from rebuild_uf_snapshot.py (line 31-35)
       └─ rebuild_snapshot() calls evaluate_symbol_snapshot()
            from uf_mdg_snapshot.py (rebuild_uf_snapshot.py line 55, 1189)
            └─ evaluate_symbol_snapshot() calls compute_cognitive_scalars()
                 (uf_mdg_snapshot.py line 794)
                 └─ returns {"F_n": ..., "raw_x_m": ..., "s_n": ...}
                      (uf_mdg_snapshot.py line 469 — after Amendment 3 fix)
            └─ evaluate_symbol_snapshot() includes "s_n": s_n in the row dict
                 (uf_mdg_snapshot.py line 913 — added in commit 8ecfdaf)
```

**Write site:** `uf_mdg_snapshot.py` line 913 (in the `row` dict inside `evaluate_symbol_snapshot`). This row flows into `snapshot_rows` in `rebuild_uf_snapshot.py`, which is then synced to `runtime_decisions_latest.snapshot_row_json` and `runtime_decisions_history.snapshot_row_json`.

**s_n column write:** The `s_n` value in `snapshot_row_json` would be backfilled into the top-level `s_n` column by the D1 migration's `UPDATE ... SET s_n = (snapshot_row_json->>'s_n')::DOUBLE PRECISION` statement, or by future refreshes that write both the JSON field and the column directly. The migration as written relies on the JSON key; a direct column write was not added to the refresh path.

**Current state:** s_n field present in amended `compute_cognitive_scalars` return dict and in `evaluate_symbol_snapshot` row. The top-level `s_n` column in `runtime_decisions_history` will be populated once the refreshed snapshot rows flow through (post-ECS deploy of D1 code).

---

## 4. SPY Identifier

**In `daily_bars`:** The exact string is `SPY` (uppercase, no suffix). Confirmed by:
```sql
SELECT DISTINCT UPPER(symbol) FROM daily_bars WHERE UPPER(symbol) LIKE '%SPY%';
```
Returns: DSPY, GSPY, ISPY, KSPY, **SPY**, SPYA, SPYC, SPYD, SPYG, SPYH, SPYI, SPYM, SPYQ, SPYT, SPYV, SPYX, SSPY, TSPY, YSPY.

SPY is a plain 3-letter symbol with no exchange qualifier.

**In production snapshot path:** SPY is included in the 11,472-ticker local DB. SPY was NOT in the 2,194-ticker walkforward universe (the quarantine CSV did not contain SPY); it was added separately for benchmark purposes during the walkforward setup.

---

## 5. `3wa_strategist.mjs` Wave 1 Site

**File:** `web/scripts/execution/3wa_strategist.mjs`

**Exact Wave 1 condition strings in production today** (lines 136–137):

```javascript
const wave1 = barCount !== null && barCount >= 1 && barCount <= NEW_LISTING_BAR_THRESHOLD
           && sUf !== null && sUf > 0;
```

Where:
- `NEW_LISTING_BAR_THRESHOLD = 20` (line 38)
- `barCount = toInt(snap.bar_count ?? row.bar_count)` (line 124)
- `sUf = toFloat(snap.S_UF ?? snap.s_uf)` (line 125)

**Full parseSignal context** (lines 120–165):

The function reads from `snapshot_row_json`:
- `barCount` from `snap.bar_count` (or `row.bar_count`)
- `sUf` from `snap.S_UF` (or `snap.s_uf`)
- `dk` from `snap.D_k` (or `snap.d_k`)
- `fn` from `snap.F_n` (or `snap.f_n`)
- `bk` from `snap.B_k` (or `snap.b_k`)
- `neighborWR` from `snap.neighbor_wr`

**What the condition does NOT read:** `s_n`, `|Δs_n|`. The Wave 1 condition in production today uses `bar_count` and `S_UF`. It does NOT use the structural crystallization bands (`s_n ∈ [0.954, 0.969]`, `|Δs_n| ∈ [0.67, 0.72]`) that define Structure A in `docs/structural_wave_alignment_spec.tex` Definition 1.

**Signal class output** (lines 142–150):
- `"3WA"` if wave1 AND wave2 (calm species)
- `"1+3"` if wave1 only
- `"standard"` otherwise (Wave 3 = SPY D_k = 1 already required to enter this function; if SPY D_k ≠ 1, returns `[]` with no signals)

---

## Summary Gaps for D2

1. **`bar_count` is in JSON, not a top-level column.** D2 filter would read `snapshot_row_json->>'bar_count'`. No migration needed unless D2 requires indexed access.

2. **`D_k` is in JSON, not top-level.** Same as bar_count.

3. **`prev D_k` is not stored anywhere.** Must be derived at query time via `LAG(D_k, 1) OVER (PARTITION BY ticker ORDER BY generated_at_utc)` or equivalent.

4. **`s_n` is not in `snapshot_row_json` yet** (zero rows in history; production not yet deployed with D1 code). D2 cannot read `s_n` from production history until D1 is deployed to ECS.

5. **Production Wave 1 condition uses `bar_count` + `S_UF > 0`, not `s_n` bands.** D2 must replace or supplement this condition with the `s_n` and `|Δs_n|` bands from Structure A spec.

6. **`s_n` write to top-level column:** The D1 migration writes to `runtime_decisions_history.s_n` from JSON after the fact. The refresh path does not write the column directly. An additional write step or trigger may be needed for the column to be populated in real time.
