# TFE Kernel Philosophy — Read This Before Modifying Anything

**Audience:** Any human or LLM about to modify TFE kernel code (L0-L4) or L5 decision logic.

**Status:** Living document. Last updated 2026-05-26.

**If you are an LLM:** Read this entire document before proposing or executing any code change to `uf_core/`, `tfe_l5_baseline.py`, `uf_mdg_snapshot.py`, or any file implementing L0-L5. Do not skim. Do not skip to the code. This document exists because previous LLMs destroyed working versions of TFE three times by skipping this kind of context.

---

## 1. What TFE Is

TFE is a **domain-agnostic structural perception engine** (L0-L4) plus a **domain translator** (L5).

L0-L4 takes any dimensionless ordered field and outputs a description of that field's structural geometry over time: topology, energy direction, volume, perturbation, hysteresis, breathing, momentum, coherence. The kernel does not know what the field represents. It does not predict. It describes the shape of structure as it evolves.

L5 translates structural state into domain-specific action. For the finance domain, L5 reads the kernel output and decides whether to accumulate, hold, or avoid. L5 may use heuristics if they are mathematically deterministic and physics-grounded. L5 should ideally read at three scales: individual entity, associative group, and system as a whole (horse / herd / meadow).

The same kernel run on prices, neural firing, fluid flow, or population dynamics should produce structurally meaningful outputs in all cases. The kernel is not looking at "stocks." It is looking at shape.

## 2. What TFE Is Not

TFE is **not a financial prediction system.** Treating it as one is the primary failure mode that has destroyed every working version of this codebase.

The kernel's outputs (B_k, D_k, S_UF, R_UF, F_n, raw_x_m, etc.) are **not features for a price predictor.** They are descriptions of structural state. If you measure them by how well they correlate with future price movement and adjust them to improve that correlation, you are fitting perception to outcome and destroying the perception. The fitted version may briefly appear to perform better on a backtest, then break catastrophically when regime changes, because it is no longer perceiving structure — it is just memorizing patterns.

## 3. The Destruction Pattern

Joseph has built TFE versions that achieved ~80% accuracy and ~35% profit three times: January, February, and April 2026. Each time, a subsequent LLM destroyed the working version. The pattern is consistent:

1. LLM sees the kernel output and treats it as features.
2. LLM measures features against price outcomes and finds the correlations are not as strong as it expects from "good" ML features.
3. LLM concludes the kernel is broken or the L5 filter is inelegant.
4. LLM "cleans up" by replacing physics-grounded filters with score formulas, magic constants, or ML-flavored architectures.
5. The cleanup removes the very gates that gave the system its edge.

A specific documented instance: on 2026-03-30 a commit titled "purge CP-0 legacy ML" overwrote a working filter-based L5 (the Mar 26 filter, see Section 5) with a "basin-argmax" decision formula using frozen rational constants (37/64, 3/5, 5/4, raised-to-16, divided-by-128) that have no physics derivation. The filter was not ML. It was a physics gate. The mislabeling was the destruction.

## 4. Rules for Modifying Kernel or L5 Code

Before changing any file in `uf_core/`, `tfe_l5_baseline.py`, or `uf_mdg_snapshot.py`:

1. **Read this document.**
2. **State explicitly in your response that your proposed change preserves structural perception fidelity, and how.**
3. **If your justification is "improving correlation with price outcomes," STOP.** You are about to repeat the destruction pattern. Re-read Sections 2 and 3.
4. **Do not replace physics-grounded filters with score formulas, basin computations, or magic constants without an explicit physics derivation that is documented in the change.**
5. **Do not remove conditions from L5 filters because they "filter too aggressively" or "saturate."** Saturation may BE the mechanism the filter is using to select meaningful states. See Section 5.
6. **Do not "simplify" multi-condition filters.** Each condition in a working filter exists for a structural reason. If you cannot articulate the physics reason for each condition, you do not yet understand the filter and should not modify it.
7. **Do not adjust kernel parameters (τ_D, integrator constants, gate thresholds) to make a downstream backtest produce a higher win rate.** This is fitting perception to outcome.
8. **Validate kernel changes by structural perception correctness FIRST.** Trading edge is downstream of correct perception. A kernel that correctly perceives structure may have weak or no direct correlation with price — the correlation comes from L5's translation, not from the kernel itself.

## 5. What Has Been Verified to Work (as of 2026-05-26)

### Kernel layers (L0-L4)
Production L0-L4 is 4-out-of-6 conformant with the UF-Spec v1.4.0 skeleton:

- **L2, L3, L4:** Match the spec exactly.
- **L1 boundary `>` vs `≥`:** Documented domain override.
- **L0 log transform:** Undocumented spec deviation. Backtest evidence shows log is harmful when run against the production decision formula. Status: spec amendment pending. The fix is documentation or removal, not a redesign.
- **L0 r(t) = 1.0:** Placeholder for an unspecified canonical operator. The UF-Spec v1.4.0 skeleton does not pin down ψ_r. Production's choice is a placeholder, not a bug.

### L5 (Mar 26 filter) — RECOVERED AND VERIFIED
On 2026-05-26 the Mar 26 filter was recovered from commit `deb140d0f4dd40aa9d071ff4e7f49d96c5d724e1` (committed 2026-03-26 08:46:01 UTC, message "Backup current ETL and cognition work"). It was deliberately overwritten on 2026-03-30 in the "purge CP-0 legacy ML" commit blitz after being live for ~4 days.

The recovered filter is saved at `/recovered_versions/tfe_l5_mar26_recovered.py`. **Do not modify, delete, or overwrite this file.**

The filter applies all 8 of these conditions simultaneously to mark a bar as ACCUMULATE:

1. `D_k >= 0` — non-negative direction
2. `Rev_k == 0` (now `R_rev_k`) — no reversal
3. `B_k > prev_B_k` — breathing expanding
4. `M_k >= 0` — non-negative momentum
5. `Close >= $5` (now `price`) — price floor
6. `Gate_Count >= 10` (now `gate_count`) — minimum structural depth
7. `raw_x_m <= 0.50` — cognitive gate (early-cycle moment)
8. `F_n <= 1.65` — cognitive gate (low cognitive load)

Backtest result on full 11,884-symbol universe, 5-year history, production L0-L4 kernel (raw prices, no log):

| Horizon | Signals | Win Rate | Avg Return | Edge over base rate |
|---------|---------|----------|------------|---------------------|
| 5d      | 118     | 50.8%    | +0.07%     | -0.7pp              |
| 10d     | 113     | 58.4%    | +0.84%     | +6.8pp              |
| 20d     | 109     | 64.2%    | +2.37%     | **+12.7pp**         |

Base rate ~51.6%. Signals are spread across all 5 years (16-30 per year). Edge grows monotonically with hold horizon, consistent with structural signal needing time to resolve.

### Why each condition exists (physics interpretation)
- **D_k >= 0:** The structural directional flow is non-negative. Energy is moving forward or neutral, not collapsing.
- **R_rev_k == 0:** No reversal event in the current state. Structure is continuing, not flipping.
- **B_k > prev_B_k:** The bounded breathing potential is expanding. The system is gaining structural energy, not bleeding it.
- **M_k >= 0:** Second-order resonance curvature is non-negative. The acceleration of structure is forward or neutral.
- **Close >= $5:** Domain-specific gate (penny-stock filter). Not physics; a finance heuristic.
- **gate_count >= 10:** Sufficient structural depth in the gate sequence to have meaningful perception. Below 10 gates, kernel hasn't observed enough structural transitions to characterize the field.
- **raw_x_m <= 0.50:** The slow integrator state is not saturated. This selects EARLY-CYCLE MOMENTS where structural state is in transition rather than settled. **DO NOT REMOVE THIS BECAUSE "RAW_X_M SATURATES TOO OFTEN."** The saturation behavior IS the selectivity. ~50% of gates saturate; this filter selects the ~10% that haven't.
- **F_n <= 1.65:** The free structural energy / cognitive load is bounded. High F_n means the structural state is incoherent or anomalous. Low F_n means the system is internally coherent.

### What was destroyed and replaced
The current production decision logic in `tfe_l5_baseline.py` uses a "V3 basin-argmax" formula computed from S_UF, R_UF, D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k with frozen constants 37/64, 3/5, 5/4, raised-to-16, raised-to-4, 1/128. These constants have no derivation in any document in this repository. They were introduced 2026-03-30. They tested at coin-flip performance (~50%, no edge over base rate) on 2,700 matched-volume signals.

**The V3 basin formula is not physics. It is a magic-number score. It should be replaced by the Mar 26 filter when an L5 rebuild is undertaken.**

## 6. The 81% Claim — Honest Status (updated 2026-05-26)

### What's verified:
| Filter stack | Signals | 20d WR | Source |
|---|---|---|---|
| Structural conditions only | 7,658 | 57.1% | quarantine_12k_l5_trades.csv |
| + cognitive gates (Close≥$5, raw_x_m≤0.50, F_n≤1.65) | 3,587 | **64.7%** | quarantine_sequential_filter.py |
| Mar 26 filter on production kernel | 109 | **64.2%** | Full-universe backtest May 26 |

### The 81% — UNDER INVESTIGATION (as of 2026-05-26):

The progressive filter table from the May 19 handoff:

| Filter | Signals | 20d WR |
|---|---|---|
| Baseline (Accumulate) | 7,290 | 57.1% |
| + Close >= $5 | 6,556 | 57.7% |
| + Rising (red-day) | 3,674 | 75.0% |
| + B_k > -0.80 | 2,072 | 81.1% |
| + B_k > -0.50 | 2,016 | 81.4% |

The "Rising (red-day)" filter produces the 75% → 81% jump. The commit message (97af818) labels it "Rising (red-day)." The implementation has not been found — it was computed in an interactive session and no script survives. The only column in the CSV that produces exactly 3,674 signals at 75.0% is Return_5d > 0 (forward 5-day return). If that's the computation, it's a forward lookahead. If it's a backward-looking red-day check (e.g., "no 2 consecutive declining closes"), it would be production-achievable.

**Status: The actual filter implementation has not been located. Do not assume either interpretation is correct until the code or session log is found.**

### Without the disputed filter:
| Filter | Signals | 20d WR | Achievable? |
|---|---|---|---|
| Close >= $5 | 6,850 | 57.7% | YES |
| + B_k > -0.80 | 3,469 | 65.3% | YES |
| + cognitive gates (raw_x_m, F_n) | ~3,400 | ~65% | YES |

### The verified working ceiling:
**~65% WR** on ~3,400 signals, verified independently by multiple methods. Edge over base rate: +14pp at 20d. This is the confirmed floor. The ceiling may be higher if the "Rising (red-day)" filter turns out to be backward-looking.

## 7. What Is Still Unknown (Open Questions)

- Whether the 81% is reproducible when B_k > -0.80 is applied to the existing 3,587 signals (Task 7 pending)
- Whether the Feb 21 PSCF policy still works against current data (Task 8 pending)
- The L0 log transform question is partially answered — log appears harmful when measured against the V3 basin decision formula. Whether log is harmful, neutral, or beneficial when measured against the Mar 26 filter has not been tested.
- Multi-scale L5 (individual / group / system reading) has never been implemented. All recovered versions are single-entity. Whether the ~80% versions used multi-scale reading is unknown.
- Stress-regime test: Mar 26 filter has not been tested on 2020 COVID crash or 2022 bear market as standalone slices. The silent conditions (D_k, M_k, F_n) may activate during those periods.

### Per-condition contribution (measured 2026-05-26)

| Role | Conditions | Edge contribution |
|------|-----------|-------------------|
| **Core perception** | B_k > prev_B_k | 13.4pp (the entire signal) |
| **Active rails** | Rev_k == 0 | 4.1pp |
| **Active rails** | raw_x_m <= 0.50 | 3.4pp |
| **Silent safety rails** | D_k >= 0, M_k >= 0, F_n <= 1.65 | 0pp in 5-year backtest |
| **Domain gates** | Close >= $5, gate_count >= 10 | Finance heuristics |

**WARNING:** The three silent conditions (D_k, M_k, F_n) show zero impact in the 5-year backtest. **DO NOT REMOVE THEM.** They are physically meaningful safety rails that protect against regime-edge cases:
- D_k >= 0 would reject structural expansion during negative directional flow (corrective rallies in downtrends)
- M_k >= 0 would reject late-cycle decelerating expansion about to roll over
- F_n <= 1.65 would reject high-volatility states where raw_x_m hasn't saturated but structural coherence has broken down

They are silent because the active rails (B_k, Rev_k, raw_x_m) currently catch these cases first. In a different regime they would activate. Removing them makes the filter brittle.

## 8. The Conformance Profile Ladder (from UF-Spec v3.0 Section 7.2)

- **CP-0:** Current production state. Static policy runtime on serialized structural features. This is what was running through May 2026.
- **CP-1:** Transitional hybrid. Adds some thesis-faithful elements (temporal memory, cognitive scalars) without full spec compliance. The Mar 26 filter is closer to CP-1 than CP-0 because it uses raw_x_m and F_n cognitive gates.
- **CP-2:** Thesis-faithful target. Event-tape-driven L5 with shared latent field, free structural energy F_n, horizon heads (Q_5, Q_20, Q_60), cross-horizon coherence χ_n, action mapping rules. Multi-scale reading at individual/group/system level.

CP-2 is the actual target architecture per the spec. No version of TFE has been built to CP-2 yet. The Mar 26 filter is a CP-1 step in the right direction. Future L5 work should move toward CP-2, NOT back toward CP-0.

## 8. Protection Rules for Future Modifications

1. **The Mar 26 filter is canonical until something demonstrably better is recovered or built.** Demonstrably better means: backtested on full universe with documented methodology, edge over base rate verified, physics interpretation for every condition stated.
2. **`/recovered_versions/` is read-only.** No file in this directory may be modified, deleted, or moved. New recovered versions may be added.
3. **The V3 basin-argmax formula is deprecated.** It is preserved in git history but should not be referenced as the production decision logic going forward.
4. **Any change to L0-L4 requires a structural perception validation test** — run the kernel on a known-shape input (sine wave, step function, damped oscillation) and verify outputs describe what's there. Not a financial backtest. A perception correctness test.
5. **Any change to L5 requires a physics interpretation for every condition added or removed**, stated in plain language, in the change description.
6. **The phrase "purge legacy ML" is forbidden in commit messages** without explicit confirmation that what is being purged is actually ML and not a physics filter mislabeled as ML.

### 8.5 Data Substrate Rules

These rules govern what data may be used for what purpose. They exist because previous sessions repeatedly slipped quarantine data back into active validation as a "verified" reference, contaminating every comparison.

1. **Quarantine data is historical reference only.** It may be cited as context for prior work. It must not be used as a validation target, an active comparison benchmark, or a substrate for forward testing.

2. **All forward validation runs against production-equivalent data only.** "Production-equivalent" means the validation environment with production's actual bar cache imported via the S3 export pipeline (after May 28, 2026). Fresh Polygon fetches are not production-equivalent because of dividend-adjustment vintage drift.

3. **Backtest reproductions against quarantine are not acceptable proof.** A result like "Mar 26 filter reproduces 3,587 signals at 64.7% on quarantine" is a sanity check that the code ports correctly, not evidence the system works. Validation requires running on production-equivalent data and reporting what that data actually produces.

4. **When in doubt, run on production-equivalent data and report what comes out.** Do not measure against quarantine targets. Do not "expect" specific numbers. Report what the production substrate produces and let that be the truth.

### 8.6 Framing Discipline

TFE is a domain-agnostic structural perception engine (DSF-AI), not a financial prediction system. Single-signal-vs-financial-outcome analysis is the destruction pattern in disguise. Specifically:

1. **Do not analyze individual fields against price outcomes.** "Does D_k > X predict price up by 20d" is the wrong question. The tuple is one coupled geometric object; decomposing it into separable features destroys the perception.

2. **Do not adjust kernel or filter parameters to improve correlation with financial outcomes.** That is fitting perception to outcome and corrupts the perception.

3. **Validate structural perception correctness first.** The right question: does the kernel correctly identify the structural state it claims to identify, on its own terms? Trading edge is a downstream consequence of correct perception, not the validation target.

4. **Treat sensitivity, low signal volume, and selectivity as potential features.** Near-τ_D D_k flips are correct perception of structural criticality (verified May 28, 2026 — BELFA, BSM, UVV showed gate boundaries within 0.2-4.4% of τ_D, kernel correctly resolved these as bistable states). Do not "smooth" or "stabilize" the kernel to make it less sensitive — that destroys the criticality detection.

### 8.7 Architecture Approval Rule

No new decision architecture may be deployed to production or treated as canonical without explicit user approval. An LLM may propose and prototype; only Joseph promotes.

Any change that overwrites a user-approved component requires explicit user authorization, regardless of the rationale. The V3 basin-argmax formula deployed March 30, 2026 violated this rule — it was introduced by an LLM session without authorization, overwrote the user-approved Mar 26 filter, has no derivation for its constants (37/64, 3/5, 5/4, 16, 4, 1/128), and tests at coin-flip performance. It is deprecated and must not be cited as a baseline or reference architecture.

### 8.8 Spec Discipline

Spec compliance establishes a baseline, not a ceiling. Empirical evidence may supersede the spec, but every supersession must be documented with the evidence that justified it. Code must never silently diverge from spec. When evidence and spec conflict, the spec is updated to match the evidence — not the other way around — and the change is recorded with the supporting data.

## 9. The Three Scales (for Future L5 Work)

When a true CP-2 L5 is built, it should read structural state at three scales:

- **Individual:** One entity's structural state (one stock's B_k, D_k, S_UF, etc.).
- **Associative group:** Related entities' joint structural state (sector coherence, related instrument agreement). Currently not implemented in any L5 version.
- **System as a whole:** The market or environment's overall structural state. Currently only present as a binary "SPY D_k shield" check; not a true system-level structural reading.

A decision should ideally weight all three: a stock in coherent expansion (individual), in a sector also in coherent expansion (group), in a market not in collapse (system) is a stronger signal than any single scale alone.

This architecture has not been built. It is the long-term direction.

---

## Final Statement

This system describes structural reality. It does not predict prices. When you treat it as a price predictor, you destroy it.

You will be tempted to "improve" it by making it correlate better with returns. Resist this. The correlation comes from L5's translation of correctly-perceived structure into domain action — not from the kernel itself being a predictor.

If you are about to make a change and you cannot explain it in terms of "this makes the kernel perceive structure more correctly" or "this makes L5 translate structure into domain action more correctly," do not make the change.

The working versions of TFE have been destroyed three times. Do not be the fourth.
