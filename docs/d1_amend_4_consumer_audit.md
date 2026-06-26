# Gate D1 Amendment 4 — Consumer Audit
**Command:** TFE-CMD-D1-AMEND-4-PRE-COMMIT-REVISION-WC-20260626
**Date:** 2026-06-26
**Auditor:** c1 (Claude Sonnet 4.6)
**Status:** AUDIT COMPLETE — two frame-sensitive consumers identified. wC review required before proceeding.

---

## Scope

Every code path that reads D_k, M_k, R_rev_k, U_star_k, C_k, P_k, or B_k from:
- The snapshot row (produced by `evaluate_symbol_snapshot`)
- `runtime_decisions_latest.snapshot_row_json`
- `runtime_decisions_history.snapshot_row_json`

The emission frame is changing from **last gate** to **second-to-last gate**.

---

## Consumers

### 1. `web/scripts/execution/ch2_strategist.mjs` — line 103–105, 129, 133

**What it reads:** `snap.D_k`, `snap.B_k` from `runtime_decisions_latest.snapshot_row_json`.

**How it uses them:**
- `D_k` is passed to `signal.d_k` and logged. NOT used as a selection gate in the current codebase (D_k gate removed per line 225 comment: "Aggregate D_k shield REMOVED").
- `B_k` is passed to `signal.b_k` but has no selection logic in the current code path.

**Assessment: COMPATIBLE.** D_k and B_k are passed through as signal metadata but not gated upon in the Ch2 entry logic. The frame shift does not change entry decisions. The signal values will be from one bar earlier, which is the same delta as any other field.

---

### 2. `web/scripts/execution/sentinel_monitor.mjs` — `fetchStructuralFields()` line 204–221

**What it reads:** `snapshot_row_json->>'D_k'` (as `d_k`) and `snapshot_row_json->>'R_rev_k'` from `runtime_decisions_latest`.

**How it uses them:**
- `d_k` is used in **EXIT-B (directional collapse)** at line 866–882: fires when `d_k !== 1`. This is a **frame-sensitive** use — it reads the current structural state of the open position to decide whether to exit.
- After the frame change, the emitted `D_k` is one bar behind the current close. EXIT-B would fire based on one-bar-lagged D_k.

**Assessment: FRAME-SENSITIVE.**

**Specific concern:** If a position enters on D_k=+1 (bar t-1) and the kernel at the latest refresh emits second-to-last gate (bar t-1)'s D_k=+1, but the current bar (bar t) has already collapsed to D_k=0, EXIT-B would NOT fire immediately — it would fire one refresh cycle later, when bar t becomes the second-to-last gate and its D_k=0 is emitted. This is one-cycle latency in EXIT-B detection.

**Whether this is new:** Under the current last-gate contract, sentinel reads bar t's D_k. Under the new second-to-last contract, it reads bar t-1's D_k. The exit detection is delayed by one bar.

---

### 3. `web/scripts/execution/sentinel_monitor.mjs` — tau exhaustion D_k history query, lines 893–900

**What it reads:** `snapshot_row_json->>'D_k'` from `runtime_decisions_history`, ordered by `generated_at_utc DESC LIMIT 400`.

**How it uses them:** Counts consecutive D_k ≠ 1 days to compute τ_in (compression depth) and τ_out (recovery window) for EXIT-C.

**Assessment: FRAME-SENSITIVE.** The τ computation counts how many consecutive days have D_k ≠ 1. With second-to-last-gate emission, each history row reflects bar t-1's D_k. The τ count is still meaningful (counting compression days) but lags by one bar — a compression that began at bar t is counted starting at bar t+1. This changes τ_in and τ_out by at most 1 day.

**Whether this breaks EXIT-C:** Functionally equivalent — the τ values shift by 1 day. Not an architectural break, but a behavioral shift.

---

### 4. `web/scripts/execution/sentinel_monitor.mjs` — SPY D_k check, lines 187–199

**What it reads:** `snapshot_row_json->>'D_k'` for SPY from `runtime_decisions_latest`.

**How it uses them:** SPY D_k is used to detect Wave 3 state (D_k=+1 = market expanding). Sentinel liquidates Ch1 (3WA) positions when SPY D_k flips.

**Assessment: FRAME-SENSITIVE.** SPY D_k under second-to-last-gate contract is one bar behind. The Wave 3 flip detection is delayed by one refresh cycle. For SPY (a very liquid asset with frequent gate events), the delay is approximately one trading day.

**Note:** This consumer is the SPY path specifically, not ticker-level. The current D1 scope emits SPY snapshots through the same `evaluate_symbol_snapshot` path. The SPY D_k field is now lagged by one bar.

---

### 5. `web/scripts/execution/ch3_strike_zone_detector.mjs` — lines 255–264

**What it reads:** `snapshot_row_json->>'D_k'`, `snapshot_row_json->>'B_k'`, `snapshot_row_json->>'M_k'` via SQL from `runtime_decisions_latest`.

**How it uses them:**
- Filters on `D_k = 1` as a selection gate (line 263).
- Filters on `|B_k| < threshold` (line 264).
- `M_k` is read but not gated upon in the visible query.

**Assessment: FRAME-SENSITIVE.** The Ch3 entry filter `D_k = 1` reads second-to-last gate's D_k. A ticker expanding at bar t would have its D_k=+1 emitted at bar t+1's refresh (when bar t becomes second-to-last). Entry is delayed by one bar. This is the same latency as the one-bar signal latency documented in Amendment 4.

---

### 6. `web/scripts/execution/3wa_strategist.mjs` — lines 103–128

**What it reads:** `snap.bar_count` and `snap.S_UF` (not D_k/M_k directly). References `snap.D_k` and `snap.F_n` for signal metadata passthrough only.

**Assessment: COMPATIBLE.** The Wave 1 condition reads `bar_count` and `S_UF`, not the structural tuple directly. Under Amendment 4, `bar_count` in the snapshot will shift from `len(bars)` to the gate emission sequence number of the second-to-last gate. This changes the `bar_count` value seen by the 3WA strategist. Wave 1 filter `bar_count ≤ 20` would use the gate-emission seq. This is the INTENDED change for D2.

---

### 7. `web/scripts/tuple_proximity_engine.mjs` — lines 22–23

**What it reads:** The 7-dim tuple `[D_k, M_k, B_k, R_rev_k, U_star_k, C_k, P_k]` from `snapshot_row_json` for nearest-neighbor computation.

**Assessment: FRAME-SENSITIVE.** The tuple proximity engine computes 30-NN on the 7-dim tuple. Under second-to-last-gate emission, all 7 fields are from bar t-1. The nearest-neighbor WR computation operates on the lagged tuple. This is a shift but not an architectural break — the neighbor comparison is internally consistent (all neighbors use the same emission frame once the history has been refreshed with the new contract).

**However:** History rows in `runtime_decisions_history` before Amendment 4 were emitted with the last-gate contract. Neighbors from before Amendment 4 use a different frame than neighbors after. Mixed-frame history exists until the DB is refreshed.

---

### 8. `web/scripts/runtime_decision_provenance.mjs` — lines 105–111, 232–236

**What it reads:** All 7 L4 fields from `snapshot_row_json`.

**How it uses them:** Extracts fields into the decision provenance record for audit/display. No selection logic.

**Assessment: COMPATIBLE.** Provenance is read-only for display. Frame shift doesn't affect correctness.

---

### 9. `tfe_l5_baseline.py` — full L5 filter

**What it reads:** All 7 L4 fields from a DataFrame passed to `apply_canonical_filter`.

**How it uses them:** V3 basin argmax computation — uses D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k in the basin formula.

**Assessment: COMPATIBLE for the research/backtest path, FRAME-SHIFTED for production.** In production (if the L5 filter ever reads from the snapshot), the basin formula will use second-to-last-gate values. For new-listing signals (bar_count ≤ 20), second-to-last gate is the canonical frame per the W1 measurement. For established stocks, the basin values are from one bar behind. The existing v3 basin path is being replaced by Wave 1 in D2 — frame sensitivity here is in the deprecated code path.

---

### 10. `build_exact_path_alignment_artifacts.mjs`, `build_exact_match_recovery_audit.mjs`

**Assessment: COMPATIBLE.** Offline build/audit scripts, not live trading. No selection logic that would be affected.

---

### 11. `run_uf_dynamic_decision_oracle_eval.mjs`

**What it reads:** All 7 L4 fields, applies weighted scoring.

**Assessment: COMPATIBLE.** Offline evaluation script, not in the live trading path.

---

## Summary

| Consumer | Location | Frame-Sensitive? | Breaks under Amend 4? |
|---|---|---|---|
| ch2_strategist: D_k, B_k passthrough | execution/ | No | No |
| sentinel EXIT-B: `d_k !== 1` exit | execution/ | **YES** | **One-cycle latency in D_k collapse detection** |
| sentinel EXIT-C: τ computation from history | execution/ | **YES** | **τ shifts by ±1 day** |
| sentinel SPY D_k Wave 3 flip | execution/ | **YES** | **One-cycle latency in Wave 3 detection** |
| ch3_strike_zone: D_k=1 entry gate | execution/ | **YES** | **One-bar delay in Ch3 entries** |
| 3wa_strategist: bar_count for W1 | execution/ | Intended | **Intended change — correct for D2** |
| tuple_proximity_engine: 7-dim neighbors | web/scripts/ | Yes | Mixed-frame history until DB refresh |
| runtime_decision_provenance: audit | web/scripts/ | No | No |
| tfe_l5_baseline: V3 basin | Python | Shifted | Deprecated path; acceptable |
| build scripts | web/scripts/ | No | No |

---

## STOP Condition Assessment

**Frame-sensitive consumers that would silently change behavior:**

1. **EXIT-B** (sentinel_monitor.mjs): D_k collapse detection delayed by one bar. Under the drain (kill switch ON), this is dormant. When D1 goes live on a fresh ledger, EXIT-B fires one cycle later than under the old contract.

2. **EXIT-C τ** (sentinel_monitor.mjs): τ_in/τ_out shift by ±1 day. Minor functional change, not a break.

3. **SPY D_k Wave 3 flip** (sentinel_monitor.mjs): Wave 3 flip detection delayed one cycle. Currently no Ch1 (3WA) positions in drain. Impact is dormant.

4. **Ch3 entry gate** (ch3_strike_zone_detector.mjs): One-bar delay in Ch3 entries. Ch3 is not currently active.

**None of these breaks the live drain** (kill switch ON, no new entries). The frame shift takes effect when D1 ECS deploy happens, which is post-drain. wC decision required on whether the one-bar latency in EXIT-B, EXIT-C, SPY-flip, and Ch3 is acceptable for the fresh-ledger deployment.

The command says: "STOP and report" if any consumer is frame-sensitive. Reporting here. No commit made.

---

## wC Decision Points

1. Is one-bar EXIT-B latency acceptable? (D_k collapse fires one refresh cycle later)
2. Is one-bar SPY D_k Wave 3 detection latency acceptable?
3. Is one-bar Ch3 entry latency acceptable?

If all three are acceptable: the audit clears and Amendment 4 can commit.

If any are unacceptable: separate `fetchStructuralFields` to read from a last-gate source, or add a `d_k_last_gate` field alongside `d_k_second_to_last`.
