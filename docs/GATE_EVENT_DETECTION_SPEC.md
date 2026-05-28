# Gate Event Detection Specification

**Version:** 1.0  
**Date:** May 28, 2026  
**Status:** DRAFT — Pending review  
**Author:** c1 (Claude Opus 4.6)  

---

## 1. The Problem

The Mar 26 filter picks MOMENTS, not stocks. A stock enters the "B_k expanding, no reversal, D_k positive, cognitive gates clear" state briefly — like a wave cresting. The filter catches that crest as it happens.

Production takes a single snapshot per refresh — one frame per stock. At any single moment, almost no stock is mid-crest. Both log and raw L0 produced zero signals on current snapshot data with the unchanged Mar 26 filter.

The quarantine backtest found 3,587 signals because it watched the full movie — every gate, every stock, 5 years. It caught every crest as it passed.

**The fix isn't tuning. It's changing what production records.** Production needs to watch each stock's gate sequence over time and fire when a stock enters the crest state.

## 2. What Is a Gate Event?

The L0-L4 kernel segments the price series into gates via the boundary operator D(t) > τ_D. Each gate is a contiguous structural region. At each gate boundary, the kernel emits a full DSF tuple:

(D_k, M_k, B_k, R_rev_k, U_star_k, C_k, P_k, R_k)

A **gate event** is the moment a new gate closes — a structural transition has completed. The tuple at that moment describes the structural state the stock just entered.

A **signal event** is a gate event where the full tuple satisfies the filter conditions (Mar 26 filter, 3WA crystallisation, or future filters).

## 3. Architecture

### 3.1 Current Pipeline (snapshot-only)

```
Refresh cycle:
  For each ticker:
    1. Fetch all bars
    2. Run L0-L4 kernel on full bar history
    3. Take LAST gate's DSF tuple
    4. Write one row to runtime_decisions_latest (overwrite)
    5. Write one row to runtime_decisions_history (append)
```

This captures the final state. It discards the history of gate transitions within the run.

### 3.2 Proposed Pipeline (event-emitting)

```
Refresh cycle:
  For each ticker:
    1. Fetch all bars (incremental — new bars since last refresh)
    2. Run L0-L4 kernel on full bar history
    3. For EACH gate in the sequence:
       a. Compute the full DSF tuple at this gate
       b. Compare to the previous gate's tuple (prev_B_k, prev_D_k, etc.)
       c. Check if this gate constitutes a signal event
       d. If YES: write to gate_events table
    4. Also write the LAST gate to runtime_decisions_latest (as before)
```

The key difference: step 3 emits per-gate events for the NEW gates since the last refresh. It does NOT reprocess all historical gates on every run.

### 3.3 Incremental Gate Detection

On each refresh, a stock may have 1-5 new daily bars since the last refresh. These new bars may produce 0-2 new gates (most days produce zero new gates — the stock stays within the current gate).

The event detector:
1. Loads the stock's previous gate count from the last refresh (stored in runtime_decisions_latest)
2. Runs the kernel on the full bar history
3. Compares the new gate count to the previous
4. If new gates formed: evaluates each NEW gate as a potential signal event
5. If no new gates: no events emitted

This is lightweight — most stocks on most days produce zero events.

## 4. Signal Event Definitions

### 4.1 Mar 26 Filter Event

A gate event is a Mar 26 signal if ALL of these are true at the COMPLETED gate:

1. D_k >= 0 (non-negative direction at this gate)
2. R_rev_k == 0 (no reversal at this gate)
3. B_k > prev_B_k (breathing expanded vs previous gate)
4. M_k >= 0 (non-negative momentum at this gate)
5. Close >= $5 (price at the gate boundary)
6. gate_count >= 10 (sufficient structural depth)
7. raw_x_m <= 0.50 (cognitive gate — early-cycle moment)
8. F_n <= 1.65 (cognitive load bounded)

All conditions use the COMPLETED gate's values. prev_B_k is the B_k of the immediately preceding gate (which also completed in the past). No forward-looking data.

### 4.2 3WA Crystallisation Event

A gate event is a 3WA Wave 1 signal if ALL of these are true:

1. bar_count <= 20 (new listing in first 20 gates)
2. s_n in [0.954, 0.969] (ordered structural regime at this gate)
3. |Δs_n| in [0.67, 0.72] (crystallisation magnitude vs previous gate)
4. SPY D_k = 1 at the same date (Wave 3 — market expanding)

All conditions use completed gate values and current SPY state.

### 4.3 Structural Exit Assessment Event

A gate event triggers a deterioration assessment if:

1. The stock has an open position in the trade ledger
2. The position is in the intermediate loss zone (-2% to -10%)
3. A new gate just formed (structural state changed)

This fires the horse/herd/topology assessment from the structural exit spec.

## 5. Lookahead Safety

### 5.1 What Must Be True

Every signal event must be detectable in real-time from COMPLETED bars only.

**Gate completion:** A gate closes when D(t) > τ_D at bar t. At that moment, bar t is the first bar of a NEW gate. The PREVIOUS gate [t_a, t-1] is now complete. All DSF fields for that previous gate are computed from bars [t_a, t-1] which are all in the past.

**prev_B_k:** This is B_k of the gate before the current one. Both gates are complete. No forward data.

**Cognitive scalars (F_n, raw_x_m):** The CV-1.0 integrator runs forward through the gate sequence. At gate k, F_n and raw_x_m depend only on gates 0 through k. No future gates.

**SPY D_k (for 3WA):** Queried at the current date. This is the market's structural state right now, not a prediction.

### 5.2 What Must NOT Happen

- Using the NEXT gate's values to determine if the current gate is a signal
- Using forward returns (Return_5d, Return_20d) in any filter condition
- Using the bar at position t+1 to compute any field at gate k
- Peeking at whether a gate transition will occur in the next refresh

### 5.3 Verification

For each signal event emitted, log:
- The gate boundary bar index and date
- The bar date of the most recent completed bar used in the computation
- Assert: signal_date <= most_recent_bar_date (signal is about the past, not the future)

## 6. Storage

### 6.1 New Table: gate_events

```sql
CREATE TABLE gate_events (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    event_type TEXT NOT NULL,         -- 'mar26_signal', '3wa_crystallisation', 'exit_assessment_trigger'
    gate_index INT,                   -- which gate in the sequence
    gate_date DATE NOT NULL,          -- date of the gate boundary bar
    snapshot_row_json JSONB,          -- full tuple at this gate
    prev_snapshot_row_json JSONB,     -- full tuple at previous gate (for B_k>prev_B_k etc)
    detected_at_utc TIMESTAMPTZ DEFAULT NOW(),
    run_id TEXT,
    kernel_sha TEXT,
    consumed BOOLEAN DEFAULT FALSE,   -- has the execution layer acted on this event?
    consumed_at_utc TIMESTAMPTZ
);
CREATE INDEX idx_ge_ticker_date ON gate_events(ticker, gate_date);
CREATE INDEX idx_ge_type_unconsumed ON gate_events(event_type, consumed) WHERE consumed = FALSE;
```

### 6.2 Event Consumption

The execution layer (CH2 strategist, entry timing watcher) reads from gate_events where consumed = FALSE. When it acts on an event (places an order), it marks consumed = TRUE.

This decouples detection from execution. Events can be detected during the refresh cycle and consumed during market hours.

## 7. How Existing Components Consume Events

### 7.1 CH2 Strategist

Currently: queries runtime_decisions_latest for Accumulate stocks with S_UF in [0.50, 0.75).

Proposed: queries gate_events for unconsumed mar26_signal events. The event's snapshot_row_json already contains all the fields CH2 needs (S_UF, D_k, price, etc.). The CH2 strategist applies its additional filters (market cap, epoch shield, weekend/holiday block) on top of the event.

### 7.2 Entry Timing Watcher

Currently: gets primed tickers from runtime_decisions_latest.

Proposed: gets primed tickers from unconsumed gate_events. Priority: 3wa_crystallisation events first, then mar26_signal events.

### 7.3 Sentinel Exit Assessment

Currently: checks runtime_decisions_latest for structural state changes.

Proposed: also checks gate_events for exit_assessment_trigger events on held positions. Fires the horse/herd/topology assessment.

## 8. Relationship to Existing Pipeline

### 8.1 runtime_decisions_latest — UNCHANGED

Still records one row per ticker with the latest kernel output. This feeds the screener, recommendations page, and other UI components that need current-state data.

### 8.2 runtime_decisions_history — UNCHANGED

Still appends one row per ticker per refresh. Provides the historical database for horse/herd lookups.

### 8.3 gate_events — NEW

Additive table. No existing tables are modified. The event detector runs AFTER the existing snapshot write, as a post-processing step. If the event detector fails, the existing pipeline is unaffected.

## 9. Implementation Plan

1. Create gate_events table in validation env and production
2. Build event detector as a post-processing step in the refresh pipeline
3. Test on validation env: run detector over stored bar history, verify Mar 26 filter produces signal volume consistent with quarantine (dozens per refresh, not thousands — because each refresh only has new gates from the last day)
4. Verify lookahead safety: every event's gate_date <= the latest bar date
5. Wire CH2 strategist to read from gate_events instead of (or in addition to) runtime_decisions_latest
6. Shadow-run: emit events but don't consume them for 1 week. Compare event volume and quality to existing CH2 signal generation
7. Cutover: CH2 reads from events. V3 basin still writes to runtime_decisions_latest for UI but is no longer the entry trigger.

## 10. Expected Signal Volume

On a typical day:
- Each stock has 1 new bar
- Most stocks: no new gate forms (bar stays within current gate)
- ~5-15% of stocks: a new gate forms (structural transition)
- Of those: ~1-5% pass the Mar 26 filter at the new gate
- Expected: **5-50 signal events per day** across the 10K universe

This is a dramatic reduction from V3 basin's 631 Accumulate signals, but each signal has the verified 64-65% WR structural backing.

## 11. What This Unifies

The gate event architecture unifies three previously separate concerns:

1. **Mar 26 filter** — fires on gate transitions where all 8 conditions are met
2. **3WA crystallisation** — fires on gate transitions in new listings with specific s_n/Δs_n signatures
3. **Structural exit assessment** — fires on gate transitions in held positions showing deterioration

All three are "structural transition detectors" consuming the same gate event stream. Build the event infrastructure once, all three plug in.

---

*This specification captures the architectural finding from May 28, 2026: the verified filters pick moments, not stocks. The production pipeline needs to watch film, not take photos. The event detector makes that possible without modifying the kernel or the existing snapshot pipeline.*
