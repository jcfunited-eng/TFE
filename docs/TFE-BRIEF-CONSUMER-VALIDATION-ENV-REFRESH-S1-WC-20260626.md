# TFE-BRIEF-CONSUMER-VALIDATION-ENV-REFRESH-S1-WC-20260626

**Consumer:** `tools/validation_env_refresh.py` → `run_kernel()` snap dict construction
**Stop-list ID:** S-1 (from `docs/d1_amend_4_full_system_audit.md`, commit 7db719d)
**Classification:** `breaks-under-new-frame`
**Brief author:** wC, 2026-06-26
**Approval slot (Joe):** ☐ green-light  ☐ remediate  ☐ defer to Stage 2

---

## 1. Finding (verified against committed code, not summary)

Production code post-Amendment-4 emits L4 tuple (D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k) + bar_count + F_n/raw_x_m/s_n from `compute_cognitive_scalars`, all in the second-to-last-gate frame. uf_core is locked (design doc §14), so `compute_uf_structural_state` continues to emit last-gate.

`tools/validation_env_refresh.py` `run_kernel()` builds its snap dict from THREE sources, in THREE frames:

| Snap field | Source line | Frame after Amendment 4 |
|---|---|---|
| `bar_count` | line 142: `len(bar_rows)` | **raw bar count** (third frame) |
| `D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k` | lines 149–155: `uf_state.level5.get(...)` | **last gate** |
| `prev_C_k, gate_count, active_gate_count, decision_vector` | lines 156–159: `uf_state.level5.get(...)` | **last gate** |
| `F_n, raw_x_m, s_n` | lines 160–162: `cognitive.get(...)` | **second-to-last gate** (shifted by Amendment 4) |
| `S_UF, R_UF, stability_score, max_dd, regime` | lines 144–148: `uf_state.level3/4.get(...)` | aggregate stats, frame-neutral |

c1's audit called out the L4 vs F_n/s_n mismatch. c1 mentioned bar_count in passing but did not surface that bar_count in this file comes from `len(bar_rows)` rather than from cognitive or uf_state — a third frame entirely.

## 2. Deployment impact

Validation env writes `runtime_decisions_modea`. D2 bit-equivalence test compares `runtime_decisions_modea` vs `runtime_decisions_history`. Post-Amendment-4:

- Production `runtime_decisions_history`: D_k, bar_count, s_n all second-to-last-gate (consistent single frame).
- Validation `runtime_decisions_modea`: D_k last-gate, bar_count raw, s_n second-to-last-gate (three frames).

**D2's bit-equivalence test will fail on every row** for D_k, bar_count, and any field that derives from them. The test will report disagreement even though both kernels are operating correctly — the disagreement is the frame mismatch, not a kernel divergence.

**Not a live trading break.** Production trading path is `latency-only` per the rest of the audit. The S-1 break is in the research/verification tool that gates D2.

## 3. wC's recommended action: **Option A — re-source L4 + bar_count from cognitive in validation_env_refresh.py**

Switch validation env's L4 reads from `uf_state.level5` to `cognitive` (which post-Amendment-4 returns the second-to-last-gate L4 tuple + bar_count per handoff §4):

```python
# tools/validation_env_refresh.py lines 142, 149–159 — REPLACE with:
"bar_count":   cognitive.get("bar_count"),
"D_k":         cognitive.get("D_k"),
"M_k":         cognitive.get("M_k"),
"R_rev_k":     cognitive.get("R_rev_k"),
"U_star_k":    cognitive.get("U_star_k"),
"C_k":         cognitive.get("C_k"),
"P_k":         cognitive.get("P_k"),
"B_k":         cognitive.get("B_k"),
"prev_C_k":    cognitive.get("prev_C_k"),
"gate_count":  cognitive.get("gate_count"),
"active_gate_count": cognitive.get("active_gate_count"),
"decision_vector":   cognitive.get("decision_vector"),
```

Leave lines 144–148 (`S_UF`, `R_UF`, `stability_score`, `max_dd`, `regime`) sourcing from `uf_state` — these are aggregate stats over the bar history, not gate-state values, so they are frame-neutral. Production keeps them on uf_core too (handoff §4: "evaluate_symbol_snapshot at ~line 956 overrides uf_core L4 with cognitive's second-to-last values when valid" — only L4 is overridden).

**Rationale:**
- D2 bit-equivalence test requires modea and production to be in the same frame.
- Production sources L4 + bar_count from cognitive post-Amendment-4.
- Therefore validation env must too. Identical source = identical frame = bit-equivalent.
- Option B (separate single-frame kernel path) adds code surface for no benefit if cognitive already returns everything.
- Option C (accept mixed-frame) means D2 cannot pass. Hard no.

## 4. Open verification before applying the fix

c1 has not yet shown wC the actual return-dict construction in the Amendment 4 worktree at `/tmp/tfe-wt-d1/uf_mdg_snapshot.py`. Three things must be confirmed by reading that file:

(V1) Does post-Amendment-4 `compute_cognitive_scalars` return all 12 fields listed in the patch above? Specifically: `bar_count`, `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`, `P_k`, `B_k`, `prev_C_k`, `gate_count`, `active_gate_count`, `decision_vector`.

(V2) What does the expanded `_null` dict at the top of `compute_cognitive_scalars` look like? All 12 fields must be present with `None` default for cross-field consistency at 0/1 gates (handoff §4: "At 0/1 gates, ALL gate-specific fields forced to None for cross-field consistency").

(V3) Are the return field names a string-exact match to the snap dict keys c1 currently uses (`D_k`, not `d_k`; `M_k`, not `m_k`; etc.)? Case must match.

If V1 surfaces any field that cognitive does NOT return, the snap dict will get `None` from `cognitive.get()` at that position. That's tolerable if production also gets `None` for that field — but if production keeps reading that field from `uf_state` while validation gets `None`, that's a NEW frame mismatch. So V1 needs explicit per-field confirmation, not just "yes mostly."

## 5. Dispatch to c1

After Joe approves this brief, dispatch the verification block below. Do NOT apply the fix until V1/V2/V3 return clean.

```text
TFE-CMD-S1-VERIFY-COGNITIVE-RETURN-DICT-WC-20260626

Show the actual lines from /tmp/tfe-wt-d1/uf_mdg_snapshot.py for:

(A) The expanded _null dict at the top of compute_cognitive_scalars
    (currently at ~line 382 in the committed version; will have moved
    in the worktree). Paste it verbatim.

(B) The return statement(s) of compute_cognitive_scalars in the
    worktree. Paste every return path, verbatim.

(C) Confirm for each of these 12 field names whether cognitive
    returns them: bar_count, D_k, M_k, R_rev_k, U_star_k, C_k, P_k,
    B_k, prev_C_k, gate_count, active_gate_count, decision_vector.
    For each: YES / NO / NOT-IN-WORKTREE. No commentary, just the
    list.

(D) Show evaluate_symbol_snapshot at ~line 956 of the worktree —
    the L4-override block. Paste verbatim. wC needs to confirm
    exactly which fields production overrides from cognitive vs
    leaves on uf_core.

Do NOT commit. Do NOT modify validation_env_refresh.py yet. Do NOT
apply the wC-proposed fix. This is a read-and-paste task only.
```

## 6. After verification: the actual fix dispatch

This dispatch is conditional on V1/V2/V3 all clean. Issue AFTER Joe approves and AFTER c1 confirms verification.

```text
TFE-CMD-S1-FIX-VALIDATION-ENV-REFRESH-WC-20260626

Apply Option A from TFE-BRIEF-CONSUMER-VALIDATION-ENV-REFRESH-S1-WC-20260626.

In /tmp/tfe-wt-d1/ (the Amendment 4 worktree, NOT the codex branch):

Edit tools/validation_env_refresh.py run_kernel() snap dict
construction (currently lines 139–163). Change the source for these
12 fields from uf_state to cognitive:

  bar_count, D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k,
  prev_C_k, gate_count, active_gate_count, decision_vector

Leave these on uf_state (unchanged):

  S_UF, R_UF, stability_score, max_dd, regime, price, ticker,
  asset_type, generated_at_utc

Do not modify any other file in this dispatch. Show wC the full
edited run_kernel() function and the resulting diff against the
current committed version BEFORE committing.

Once wC approves the diff, c1 commits to codex/persistent-etl-update-20260326
alongside the Amendment 4 worktree changes. Same commit, single
logical unit. Commit message:

  d1: Amendment 4 — production emits second-to-last gate;
  validation_env_refresh re-sourced to cognitive for frame consistency.
  Resolves audit S-1.
```

## 7. Joe approval block

To proceed with Option A as written:

- [ ] **Approved as written.** wC dispatches verification (Section 5), then fix (Section 6) on c1 confirmation.
- [ ] **Approved with modification.** Specify:
- [ ] **Reject — defer to Stage 2.** D2 gate then unblocks via a different path Joe specifies.
- [ ] **Reject — re-scope Amendment 4 entirely.** Specify path forward:

---

**End of brief.**
