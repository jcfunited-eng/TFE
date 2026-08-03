---
name: tfe-honest-timing
description: MANDATORY audit discipline for any TFE money construction or backtest claim — reveal-bar timing, as-of-issue records, null tests. Use before building, measuring, or reporting ANY edge/harvest/book number.
---

# Honest timing — the reveal-bar discipline

Established 2026-07-31 (docs/CH4_LIVE_TIMING_AUDIT_20260731.md, all
addenda). Violating these rules produced +503-630%/decade mirages that
died under live timing. Every rule below is mandatory.

## The theorem
The v2 gate boundary at bar t needs bar t's data, and kappa(t) needs
bar t+1 — a gate ending at bar tb-1 is first KNOWABLE at the close of
bar tb (arguably tb+1). The predictable component of a gate's
displacement is concentrated in the reveal bar. Any fill priced before
the fact is knowable is a bench victory.

## Rules for any new construction
1. **State knowability for every fill**: at which bar close is each
   fact (boundary, class, record, herd state) actually knowable? Fill
   at-or-after that close, never `closes[tb-1]`.
2. **Records strictly as-of-issue**: a prediction may only use
   completions revealed BEFORE its own issue instant. Use the
   two-stream ledger pattern (tools/ch3_hourly_law.py) or day-rollover
   buffering (tools/ch4_herd_kgate_live.py replay()). Intraday issues
   join herd state with CH4_HERD_LAG=1 (prior day) — day-D herd state
   uses day-D closes.
3. **Null test before believing**: rerun the ledger with the completion
   object set to the TRADABLE displacement (CH3_TRADE_DISP=1 in
   tools/ch3_hourly_law.py). If the consistency spectrum equals the
   binomial null, there is nothing to trade regardless of law numbers.
4. **Declared constants, no sweeps**: every threshold declared once
   before measurement. Scanning variants and reporting the best is
   band-mining (12+ recurrences of this failure are on record).
5. **Books**: fresh $100k per calendar year, 10% slices, max 10 open,
   both polarities, per-year dollars reported. No costs modeled — say so.
6. **Cross-rung replication before any claim**: a construction selected
   on one stream must be applied BLIND to an independent rung
   (daily/hourly/m15 streams all exist). The herd K-gate edge moved
   10/11->6/11 positive years between two near-identical ledgers —
   treat small edges as implementation-sensitive.
7. **File everything**: results (including failures) go to
   artifacts/ch4_uf/*.json + an addendum in the audit doc, committed
   and pushed to origin. FILED = on-origin.

## Determinism requirements
Never use Python's builtin hash() for species ids (salted per process —
see the capacity-probe lesson). Use blake2b via the existing sp_id/hid
helpers. Any engine must pass: two identical runs -> identical decisions.
