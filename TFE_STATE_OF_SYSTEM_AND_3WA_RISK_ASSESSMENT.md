# TFE State-of-System and 3WA Implementation Risk Assessment

Generated: May 27, 2026 | Task :505 (commit 5c27c5a) | Branch: codex/persistent-etl-update-20260326

---

## SECTION 1: WHAT IS LIVE RIGHT NOW

### 1.1 Entry Signal Generation

The production Accumulate/Hold/Avoid decision is computed by **`web/scripts/runtime_decision_provenance.mjs`** (JavaScript), NOT by `tfe_l5_baseline.py` (Python). The V3 basin-argmax formula runs in JS and writes to PostgreSQL via `sync_runtime_postgres_impl.mjs`.

**Decision formula:** V3 basin-argmax with frozen rational constants (37/64, 3/5, 5/4, 16, 4, 1/128) plus Stable Titan Scaler override (D_k=0, S_UF≥0.85, bar_count≥1000, price≥$10 → Accumulate).

**CH2 entry filter chain** (`web/scripts/execution/ch2_strategist.mjs`):

| Gate | Condition | Source |
|---|---|---|
| 1 | decision_label = 'Accumulate' | runtime_decisions_latest (V3 basin) |
| 2 | S_UF in [0.50, 0.75) | snapshot_row_json |
| 3 | bar_count > 20 | snapshot_row_json |
| 4 | market_cap >= $500M | l5_fundamentals_normalized |
| 5 | NOT weekend (Fri/Sat/Sun) | UTC day check |
| 6 | NOT market holiday | market_calendar.mjs (computed NYSE) |
| 7 | Epoch Resonance Shield passes | g32_state.json aggregate D_k |
| 8 | No existing open position for ticker | personal_trade_ledger |
| 9 | Sector NOT epoch-adverse | g32_state.json sector pressure |

**CH3 entry filter chain** (`web/scripts/execution/ch3_scalp_strategist.mjs`):

| Gate | Condition | Source |
|---|---|---|
| 0 | Market hours (13:30-20:00 UTC) + NOT holiday | market_calendar.mjs |
| 1 | Daily CH3 loss < $1,000 | personal_trade_ledger |
| 2 | CH3 pool remaining > 0 | $5K total - losses |
| 3 | Available pool > $500 | pool - invested |
| 4 | Epoch Resonance Shield passes | same as CH2 |
| 5 | decision_label = 'Accumulate' | runtime_decisions_latest |
| 6 | bar_count > 20 | snapshot_row_json |
| 7 | price >= $1 | snapshot_row_json |
| 8 | NOT index or forex | ticker prefix check |
| 9 | Sector NOT epoch-adverse | g32_state.json |
| 10 | No open position (any channel) | personal_trade_ledger |
| 11 | Not traded today by CH3 | personal_trade_ledger |
| 12 | No loss on ticker in last 7d | personal_trade_ledger |

**Entry timing** (`web/scripts/execution/entry_timing_watcher.mjs`): fires every 5 min during market hours. Gets primed tickers (top 50 by S_UF). Checks real-time Polygon volume: normalized volume >= 1.0x required. Routes S_UF >= 0.75 to CH3, rest to CH2. Max 3 entries per run.

**Status:** Modified version. V3 basin is the canonical version from Mar 30; Stable Titan added Apr 27. The Mar 26 filter-based L5 is in `/recovered_versions/` but NOT active in production.

### 1.2 Exit Logic

All exits in `web/scripts/execution/sentinel_monitor.mjs`. Last modified: May 26.

| Exit Rule | Trigger | Blocked by MIN_HOLD? | Channel | Status |
|---|---|---|---|---|
| EXIT-F | Loss >= -10% (CH2) or -1% (CH3) | NO (always fires, but market hours only, skip day-0) | ALL | Verified working |
| EXIT-A | S_UF >= 0.75 | NO (winning exit) | CH2 | Verified working |
| EXIT-B | D_k != 1 | YES (if losing, age < 7d) | CH2 | Verified working |
| EXIT-D | Trailing profit floor hit (gain dropped from max) | NO (winning exit) | CH2 | Verified working |
| EXIT-H | Past midpoint of tau_out AND gain >= 5% | NO (winning exit) | CH2 | Verified working |
| EXIT-C | Position age > tau_out | YES (if losing, age < 7d) | CH2 | Verified working |
| EXIT-R9 | 7-day minimum hold on all losing exits | N/A (this IS the guard) | CH2, Ch1 | Verified working |
| SPY flip | SPY D_k != 1 → kill Ch1 positions | YES (if losing, age < 7d) | Ch1 only | Verified working |
| CH3 stale grab | age >= 1d AND P&L > 0.5% | NO | CH3 | Verified working |
| CH3 fuel exhausted | EXHAUSTED fuel AND age >= 1d AND P&L > -1% | NO | CH3 | Verified working |
| Calamity | R_rev_k > 0 | NO | Ch1/legacy | Verified working |
| Zombie | bar_count > 10 | NO | Ch1/legacy | Verified working |

### 1.3 Infrastructure

| Component | File | Last Modified | Status |
|---|---|---|---|
| Sentinel daemon | sentinel_daemon.mjs | May 26 | Verified — polls every 5 min, holiday-aware |
| Orphan adoption | sentinel_monitor.mjs | May 21 | Verified — DB-persisted 15-min kill cooldown |
| Phantom cleanup | sentinel_monitor.mjs | May 20 | Verified — 30-min grace period |
| Holiday calendar | market_calendar.mjs | May 26 | Verified — computed NYSE, permanent |
| Market hours gate | sentinel_monitor.mjs | May 20 | Verified — EXIT-F restricted to 13:30-20:00 UTC |
| Kill cooldown | sentinel_monitor.mjs | May 21 | Verified — DB-persisted, cross-process |

### 1.4 Kernel State

Production L0-L4 runs in Python (`uf_core/`) called by `uf_mdg_snapshot.py` during refresh.

| Layer | File | Implementation | Spec Conformant? |
|---|---|---|---|
| L0 | uf_core/layer0.py | log(F + eps) normalization | NO — spec says raw F |
| L0 r(t) | uf_core/layer0.py | r(t) = 1.0 (placeholder) | UNKNOWN — spec undefined |
| L1 | uf_core/layer1.py | D(t) > tau_D (strict) | Documented override |
| L2 | uf_core/layer2.py | Gamma-weighted composite | YES |
| L3 | uf_core/layer3.py | Resonance functional | YES |
| L4 | uf_core/layer4.py | DSF with clamped U* | YES |

Parameters: All frozen since Feb 2026. Zero changes. See KERNEL_PHILOSOPHY.md Section 5.

CP-2 cognitive scalars (F_n, raw_x_m) computed by `uf_mdg_snapshot.py` on raw prices with max_bars=252. These are stored in snapshot_row_json but NOT used by any entry or exit logic (cognitive gate removed Apr 27).

### 1.5 L5 State

**What is ACTUALLY running:** V3 basin-argmax in `runtime_decision_provenance.mjs` (JavaScript). This is the file that writes Accumulate/Hold/Avoid to the database. The Python `tfe_l5_baseline.py` is NOT in the production execution path — it's a research/audit tool.

**The Mar 26 filter-based L5** is in `/recovered_versions/tfe_l5_mar26_recovered.py`. It is NOT active. It has never been wired into the production execution path.

**The V3 basin-argmax** was introduced Mar 30 and has been the sole production decision formula since. It has zero edge over base rate (verified May 26 backtest).

---

## SECTION 2: WHAT CHANGED IN THE LAST 7 WEEKS

### Reverse chronological (since April 7, first trades)

| Date | SHA | Change | Category | Still Active? |
|---|---|---|---|---|
| May 26 | e42989d | Computed NYSE holiday calendar (permanent) | [INFRA] | YES |
| May 26 | be1f499 | Market holiday calendar — block trading on holidays | [INFRA] | YES (superseded by e42989d) |
| May 21 | 49c8d6a | Cross-process kill cooldown — persist to DB | [BUG FIX] | YES |
| May 20 | b74f560 | EXIT-R9: 7-day minimum hold on losing exits | [SIGNAL] | YES |
| May 20 | f52cdda | 3 sentinel bugs: orphan loop, stale EXIT-F, phantom grace | [BUG FIX] | YES |
| May 19 | 03352c2 | EXIT-R7 day-0 loss protection + 3WA SL to -10% | [SIGNAL] | YES (superseded by EXIT-R9) |
| May 19 | 1a6f758 | Revert B_k/F_n entry gates | [REVERT] | YES |
| May 19 | 97af818 | B_k/F_n entry gates deployed | [SIGNAL] | NO (reverted same day) |
| May 19 | 385377d | Revert energy gate | [REVERT] | YES |
| May 19 | 0e3150f | Energy gate (expansion_days) | [SIGNAL] | NO (reverted same day) |
| May 19 | 64eecd8 | Red-day filter + financial rules library | [SIGNAL] | YES (ENTRY-R1) |
| May 19 | 4595942 | Revert entry pricing to 1.001x | [REVERT] | YES |
| May 19 | 7154d1b | Exclude manual_portfolio_reset from scoring | [INFRA] | YES |
| May 19 | f71661b | Entry timing, orphan sync, Friday block, scoring fixes | [BUG FIX] | YES |
| May 14 | caeb68e | CH2 sizing $925→$2500, min 5% bracket width | [SIGNAL] | YES |
| May 14 | 4824ea7 | CH2 market_cap COALESCE fix | [BUG FIX] | YES |
| May 13 | 006aba6 | CH2 market_cap filter uses both tables | [BUG FIX] | YES |
| May 13 | c66d605 | CH2 improved diagnostic | [INFRA] | YES |
| May 13 | 01ff823 | CH2 candidate filter step counts diagnostic | [INFRA] | YES |
| May 12 | 245701e | L5 epoch governance | [SIGNAL] | YES |
| May 12 | bb0590a | **Remove D_k=1 gate from CH2 entry** | **[PURGE]** | **YES — unfixed regression** |
| May 11 | 110a3bf | CH3 brackets +3%/-1.5% → +1.5%/-1% | [SIGNAL] | YES |
| May 11 | 9411745 | CH3 fuel gauge fix | [BUG FIX] | YES |
| May 8 | 9dcd172 | Kill cancels ALL open orders before selling | [BUG FIX] | YES |
| May 6 | 4c5d69b | Sentinel adopts orphan Alpaca positions | [BUG FIX] | YES |
| May 6 | b8ba7c9 | EXIT-H age fallback for no-tau positions | [SIGNAL] | YES |
| May 6 | 1ed52a5 | CH3 drops D_k gate + crypto stripped | [PURGE] | YES |
| May 7 | 7aa433b | EXIT-F catastrophic floor | [SIGNAL] | YES |
| May 7 | 178e812 | CH3 rewrite as Accumulate pullback grab | [SIGNAL] | YES |
| May 5 | 0fb13dd | Tau from DB at runtime | [INFRA] | YES |
| May 5 | bf20773 | Persist maxGainCache to disk | [BUG FIX] | YES |
| May 5 | 83af83a | Backfill failure loop + entry timing never firing | [BUG FIX] | YES |
| May 5 | a4fbe19 | CH3 Accumulate-only + 7d loser cooldown + EXIT-H | [SIGNAL] | YES |
| May 5 | 23b7585-4a5950f | Sentinel crashes (missing columns) | [BUG FIX] | YES |
| May 5 | 19b4cde | CH3 was buying Avoid stocks | [BUG FIX] | YES |
| May 5 | 9e49772 | CH2 stop loss ATR→-10% catastrophic | [SIGNAL] | YES |
| May 5 | 529c404 | 27 zombie positions — bracket exits never synced | [BUG FIX] | YES |
| May 4 | f4008c9 | Momentum-aware trailing exit (tau energy ratio) | [SIGNAL] | YES |
| May 4 | 6d0054c | Trailing exit was dead — DB has no current_price | [BUG FIX] | YES |
| May 3 | db1e62e | CH3 fires every 5min + up to 3 signals/run | [SIGNAL] | YES |
| May 1 | e05e923 | CH3 crash fix | [BUG FIX] | YES |
| May 1 | cb8f2a1 | CH2 market cap floor $500M + trailing profit exit | [SIGNAL] | YES |
| Apr 30 | 1300791 | ESM import fix in CH2/CH3 | [BUG FIX] | YES |
| Apr 30 | 6fe480b | Aggregate D_k shield replaces SPY-only | [SIGNAL] | YES |
| Apr 29 | a37a6b5 | Dynamic tau_in at CH2 entry | [SIGNAL] | YES |
| Apr 29 | d98b7ca | Epoch Resonance Shield in CH2 + CH3 | [SIGNAL] | YES |
| Apr 29 | a7b6c36 | Tau_out bar-level + backfill | [SIGNAL] | YES |
| Apr 29 | 324a509 | CH2 exhaustion timer (tau_out) | [SIGNAL] | YES |
| Apr 28 | 10c7281 | CH3 deceleration exit | [SIGNAL] | NO (replaced) |
| Apr 28 | ceaac13 | IS_PAPER undefined + CH3 market hours | [BUG FIX] | YES |
| Apr 28 | 36cd07d | CH3 spike hunter | [SIGNAL] | YES (base of current CH3) |
| Apr 28 | 2e6ce19 | CH3 rebuilt as structural hunter | [SIGNAL] | YES |
| Apr 28 | 1868aeb | **CH2 regime gate REMOVED** | **[PURGE]** | **YES** |
| Apr 28 | cc60169 | Titan scaler in runtime_decision_provenance | [SIGNAL] | YES |
| Apr 27 | 47fd6a9 | L5 stable titan scaler | [SIGNAL] | YES |
| Apr 27 | e002f20 | **Remove cognitive gate (was killing 99.99%)** | **[PURGE]** | **YES** |
| Apr 23-27 | various | CH3 development (strike zone, fuel gauge, pool) | [SIGNAL] | YES |
| Apr 14 | 6337f9b | Provenance PK fix + timezone-naive bar cache | [BUG FIX] | YES |

### Flagged [PURGE] changes that overwrote verified logic:

1. **bb0590a (May 12)**: Removed D_k=1 gate from CH2 entry. Commit says "trust the kernel." This unblocked 49 stocks without directional alignment. The quarantine data shows all 7,658 primitive trades had D_k=1 — removing this gate admits signals the kernel never flagged as Accumulate in the validated dataset.

2. **e002f20 (Apr 27)**: Removed cognitive gate (F_n <= 1.65, raw_x_m <= 0.50). Commit says "killing 99.99% of Accumulate decisions." The saturation was because production uses log-normalized L0, which changes F_n/raw_x_m distributions. The gate was not broken; it was miscalibrated for the production kernel.

3. **1868aeb (Apr 28)**: Removed TRANSITIONAL-only regime restriction from CH2. Commit cites "validation finding" that regime doesn't improve edge. This was based on V3 basin output which has no edge — the regime may matter with a different L5 formula.

---

## SECTION 3: 3WA IMPLEMENTATION — EXACT CHANGES REQUIRED

### 3.1 New Files to Create

| File | Contents | Additive? |
|---|---|---|
| `web/scripts/execution/species_profiles.mjs` | JS module: loads species profiles from DB, exposes `isCalm(ticker)` | YES — new file |
| `web/scripts/execution/wave_detector.mjs` | JS module: evaluates Wave 1 (crystallisation) + Wave 2 (calm) + Wave 3 (SPY) conditions per signal | YES — new file |

### 3.2 Existing Files to Modify

| File | Function | Change | Additive or Invasive? |
|---|---|---|---|
| `web/scripts/execution/sentinel_monitor.mjs` | `runSentinel()` | Add SPY D_k to the return value (already queried at line 191, just needs to be available downstream) | ADDITIVE — exposes existing data |
| `web/scripts/execution/ch2_strategist.mjs` | Signal output | Add `signal_class: '3WA'` tag to qualifying signals (post-selection, does not change selection) | ADDITIVE — tags after selection, no filter change |
| `web/scripts/execution/entry_timing_watcher.mjs` | Primed ticker processing | Optionally prioritize 3WA-tagged signals (sort order only) | ADDITIVE — sort priority, no filter change |
| `uf_mdg_snapshot.py` | `compute_cognitive_scalars()` or snapshot builder | Export s_n to snapshot_row_json (currently not exported) | ADDITIVE — new field in existing JSON |
| `web/src/app/api/recommendations/list/route.ts` | Signal classification | Already has 3WA classification based on bar_count + SPY D_k. Would need to add species check and crystallisation check. | ADDITIVE — enriches existing classification |

### 3.3 New Database Tables

| Table | Schema | Refresh |
|---|---|---|
| `species_profiles` | `ticker TEXT PRIMARY KEY, delta_bar DOUBLE PRECISION, classification TEXT, field_used TEXT, computed_at TIMESTAMPTZ, n_bars INT` | Weekly batch (species are slow-moving) |

No changes to existing tables. The `runtime_decisions_latest` and `runtime_decisions_history` schemas are unchanged.

### 3.4 Snapshot Pipeline Changes

| Change | Where | Impact |
|---|---|---|
| Export `s_n` to `snapshot_row_json` | `uf_mdg_snapshot.py` snapshot builder | ADDITIVE — one new field in the JSON blob. s_n is already computed by `compute_uf_structural_state()` in the L4 output. It just needs to be included in the snapshot export. |

Currently `s_n` (structural entropy) is computed by the quarantine kernel but NOT by the production kernel. Production computes S_UF and R_UF from stability metrics but does not directly expose the per-gate `s_n` value. Computing s_n in production requires accessing the resonance results from L3 — this is available inside `compute_uf_structural_state()` but not currently extracted.

**This is the one non-trivial pipeline change.** It requires modifying `uf_structural_engine.py` to extract and return the per-gate s_n from L3 resonance results.

### 3.5 Admin Console / API Surface Changes

| Change | Where | Impact |
|---|---|---|
| Show 3WA signal count | Recommendations page summary cards | ADDITIVE |
| Show species classification per ticker | Analysis popup | ADDITIVE |
| Show Wave 1/2/3 status per signal | Recommendations API `signalClass` field | ADDITIVE — field already exists, logic enriched |

### 3.6 Tests Required

| Test | What it verifies | Priority |
|---|---|---|
| Species profiles match quarantine reference | Calm/active classification on known tickers | P0 — before deploy |
| Wave 1 crystallisation detection matches spec thresholds | s_n in [0.954, 0.969], |Δs_n| in [0.67, 0.72] | P0 |
| 3WA signal count on quarantine data matches ~75 | Full pipeline validation | P0 |
| s_n extraction from production kernel | New field appears in snapshot_row_json | P0 |
| No regression on existing Accumulate signals | V3 basin decisions unchanged | P0 |
| Admin/API shows 3WA badge correctly | UI verification | P1 |

---

## SECTION 4: RISK ASSESSMENT

### 4.1 Worst Case if 3WA Goes Wrong

The 3WA implementation is additive — it TAGS signals, it does not FILTER them. If 3WA detection is wrong (false positive or false negative), the worst outcome is:
- A signal is tagged '3WA' when it shouldn't be → subscriber sees incorrect confidence level on Recommendations page. No trading impact unless the entry logic prioritizes 3WA signals.
- A signal is NOT tagged '3WA' when it should be → missed opportunity for high-confidence label. No trading impact.

If the implementation also PRIORITIZES 3WA signals in entry timing (Section 3.2, entry_timing_watcher sort order), the worst case is that a non-crystallisation signal displaces a better signal in the per-run entry queue. This is bounded by MAX_ENTRIES_PER_RUN = 3.

The one invasive change is s_n extraction from the kernel (Section 3.4). If this breaks the snapshot pipeline, the entire refresh cycle fails. **Mitigation: the s_n extraction should be wrapped in try/except with fallback to null.**

### 4.2 Can 3WA Be Parallel Without Modifying Existing Logic?

**Yes.** The implementation can be structured as:
1. Species profiles: standalone weekly batch. Writes to a new table. Reads only from runtime_decisions_history. No writes to existing tables.
2. Wave detector: standalone post-processing module. Reads from snapshot_row_json + species_profiles + SPY D_k (already computed). Writes a tag to signal output. Does not modify any existing signal logic.
3. s_n extraction: the only change that touches the kernel output path. Can be gated behind a feature flag (`EXPORT_S_N=true`) and default to null when off.

### 4.3 Rollback Path

1. Species profiles: delete the `species_profiles` table. No other system depends on it.
2. Wave detector: remove the module import and tag assignment from ch2_strategist. One-line change.
3. s_n extraction: revert the change in uf_structural_engine.py. Set `EXPORT_S_N=false`.
4. Signal class: already has fallback — `classifySignal()` returns 'standard' by default. Removing the 3WA enrichment just means everything is 'standard'.

### 4.4 Cost of NOT Implementing 3WA

The system is currently operating with the V3 basin decision formula, which has no edge over base rate (verified May 26). The actual production edge comes from the CH2 filters (S_UF band, market cap, epoch shield) applied on top of basin decisions.

Without 3WA:
- No ability to identify high-confidence signals (84.5% WR) from the signal stream
- All Accumulate signals treated equally regardless of structural quality
- The Recommendations page cannot distinguish between 50% WR signals and 84% WR signals
- The subscription value proposition is weaker ("filtered list" vs "curated with conviction levels")

The 3WA signals fire only during SPY structural expansion on new listings. As of today, SPY D_k = -1 (not expanding), so 3WA would produce zero signals right now. The value is future-facing — when SPY next enters structural expansion, the system would be ready to identify crystallisation events.

### 4.5 Higher-Priority Issues to Address First

| Issue | Priority | Reasoning |
|---|---|---|
| **V3 basin has no edge** — production decision formula is coin-flip | HIGH | The Mar 26 filter or a new L5 should replace V3 basin. But this is a major change with its own risk. 3WA does not depend on which L5 formula is active. |
| **D_k=1 gate removed** (bb0590a) | MEDIUM | The quarantine data shows all primitive trades had D_k=1. Re-enabling this gate is a one-line change but would reduce signal volume. |
| **L0 log transform** | LOW (for 3WA) | 3WA uses s_n and Δs_n which come from L3 resonance, not directly from L0. The log/raw question affects L0→L1 gate boundaries but its effect on L3 s_n is indirect. |
| **EXIT-R9 unvalidated** | MEDIUM | The 7-day hold has been live since May 20. Only 5 trading days of data. No validation yet on whether it improves realized WR. |
| **Polygon VX endpoint sunset** | LOW (deadline Jun 22) | Fundamentals endpoint migration. Does not affect 3WA. |

3WA implementation does NOT depend on resolving any of these. It is additive and parallel. However, the V3 basin question (no edge) is the most impactful open issue for overall system performance.

### 4.6 Protections Against Future Destruction

The destruction pattern (Section 2, KERNEL_PHILOSOPHY.md Section 3) requires specific protections:

1. **3WA spec is already in the repo** (`docs/structural_wave_alignment_spec.tex`, 729 lines). Any future LLM that tries to "simplify" or "purge" it would need to explicitly override a documented physics spec. This is stronger protection than the Mar 26 filter had (which was just a .py file with no spec document).

2. **KERNEL_PHILOSOPHY.md** now documents the destruction pattern explicitly and names "purge legacy ML" as a forbidden commit message pattern.

3. **The species profiles table is independently valuable** — even if the 3WA detection logic is modified, the species classification (calm/volatile) is useful metadata for any future signal quality assessment.

4. **Recommended additional protection:** The 3WA implementation should include a unit test that verifies: given the quarantine governed states parquet and the 7,658 primitive trades, the Wave 1+3 detection produces 371 signals at 84.6% WR. This test becomes a regression gate — any change that fails it triggers a review.

5. **The implementation should be labeled clearly in code comments as "3WA: Three-Wave Alignment, docs/structural_wave_alignment_spec.tex"** with a reference to the spec. Not just internal variable names.

---

*End of assessment. No documentation has been updated. No code has been changed. This is a read-only inventory.*
