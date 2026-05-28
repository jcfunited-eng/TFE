# TFE Project State

**Last updated:** May 26, 2026
**Status:** Validation phase. Path to harvest identified. Per-stock relative thresholds is the next architectural piece.

**If you are a new Claude/c1 session:** Read this entire document before doing anything else. Then read KERNEL_PHILOSOPHY.md. Then ask Joe what he wants to work on. Do not propose changes, run backtests, or modify code until you have done all three.

---

## 1. What TFE Is (One Paragraph)

TFE is a domain-agnostic structural perception engine (L0-L4) plus a domain translator (L5). The kernel perceives the geometric structure of a dimensionless ordered field over time — topology, energy direction, breathing, momentum, coherence, perturbation. The kernel does not predict prices and does not know it is looking at financial data. L5 translates structural state into domain action using physics-grounded heuristics, ideally reading at three scales: individual entity, associative group, and system as whole. See KERNEL_PHILOSOPHY.md for full statement and the destruction-pattern protections.

## 2. Where We Are Right Now (Verified, May 26 2026)

### Verified working

- **Kernel (L0-L4):** Production version is 4-out-of-6 spec-conformant. L2, L3, L4 match the UF-Spec v1.4.0 skeleton exactly. L1 has documented strict-`>` override. L0 has two open items (log transform, r(t) placeholder) — see Section 5.
- **Mar 26 L5 filter:** Recovered from git as `/recovered_versions/tfe_l5_mar26_recovered.py`. Backtested at 64.66% WR at 20d on 3,587 quarantine signals (universal-threshold version). Reproduces independently. This is the verified baseline L5.
- **3WA Waves 1+3:** Spec at `docs/structural_wave_alignment_spec.tex` (729 lines, April 2026). Backtest reproduces at 84.6% WR at 20d on 371 signals. All signals are new-listing crystallisations during SPY structural expansion. Strong but volume-limited and regime-gated.
- **Infrastructure (May 19-26 fixes):** Sentinel daemon, orphan adoption (15-min DB-persisted kill cooldown), phantom cleanup (30-min grace), market hours gates, NYSE holiday calendar, EXIT-R9 (7-day minimum hold on losing exits). All verified working.

### Verified broken

- **V3 basin-argmax (production decision formula):** Currently runs in `web/scripts/runtime_decision_provenance.mjs`. Hand-tuned rational constants (37/64, 3/5, 5/4, 16, 4, 1/128) with no derivation. Zero edge over base rate (verified May 26 backtest). 47% of decisions are within 1e-8 floating-point ties — formula is mathematically arbitrary on most of the universe. Stable Titan override is the only thing producing visible Accumulate volume (~390/snapshot), and most of those are mega-caps in equilibrium that retail screeners already give for free.

### Verified gap

- **Per-stock relative thresholds (unbuilt):** The 3WA spec Section 6 explicitly identifies this as the path to broader-universe harvest beyond new-listing crystallisations. Nobody has built it. This is the next priority architectural piece (see Section 4).

## 3. Operational Reality

### Production stack
- **JavaScript** is the production runtime (`web/scripts/runtime_decision_provenance.mjs`, sentinel, strategists, entry timing). PostgreSQL backend. Next.js frontend.
- **Python** is the research/backtest/analysis layer (`uf_core/`, `tfe_l5_baseline.py`, the recovered Mar 26 filter).
- **Python and JavaScript decision logic are currently equivalent** on 998/1000 sampled rows. The 2 mismatches are a config gate, not logic drift. They have not yet diverged. Long-term unification is a commercial-grade requirement but not blocking.

### Live trading status
- Paper trading on Alpaca. $100k starting equity Feb 24. Currently -1.1% since inception.
- Losses driven by Day-0 exits (231 of 428 trades at 24.2% WR) caused by execution bugs and miscalibrated exits. The May 19-26 infrastructure work addresses these. EXIT-R9 has only 5 trading days of data — not yet validated.
- The 57.4% WR on held positions is real but is the product of CH2/CH3 filter stacks doing real filtering work on top of V3 basin (which has no edge of its own).

### Spec conformance
- The TFE spec (`docs/TFE_Specification_Merged_v3_0.pdf`) calls the current production CP-0 (lowest conformance profile). CP-2 is the target (event tape, shared latent field, free structural energy, horizon heads, cross-horizon coherence, multi-scale reading). Nothing built so far is CP-2.

### 3.4 Validation Substrate (binding rule)

**Quarantine is closed.** It is historical reference only. All forward validation runs against production-equivalent data only.

**Production-equivalent** means the validation environment with production's actual bar cache imported via S3. The bar export pipeline was deployed May 28, 2026 (rebuild_uf_snapshot.py). After the first successful export and import, the validation env's `daily_bars` table is the production-equivalent substrate.

Until the first import completes, **no forward validation can produce trustworthy results.** All work that depends on production-equivalent data is blocked on this import.

**Specifically forbidden:**
- Citing quarantine signal counts (e.g. "3,587") as validation targets
- Reproducing quarantine WR numbers as proof that the system works
- Running comparison tests against quarantine as the reference
- Treating "matches quarantine" as a passing condition

**Specifically required:**
- All backtest, signal volume, and WR claims must be computed on production-equivalent data
- Sample sizes must support the claim (Wilson confidence interval reported for any WR claim)
- Universe must be CS-only (common stock), filtered before any kernel run

## 4. What We Are Working On (Plan, In Priority Order)

These are the active steps that move TFE toward a credible commercial-grade system. Sequencing matters. Don't reorder without explicit reasoning.

### Step 1: Re-enable D_k=1 gate in CH2 entry
**One-line revert of commit bb0590a.** Removed May 12 with the rationale "trust the kernel." All 7,658 verified quarantine primitive trades had D_k=1. Removing this gate was an unjustified purge. Re-enabling probably improves WR on existing CH2 signals immediately. Low risk, fast feedback.

### Step 2: Build per-stock relative thresholds (c1's "step two")
**This is the harvest unlock.** Current state: filters use universal thresholds (raw_x_m ≤ 0.50, F_n ≤ 1.65) that either catch everything or nothing depending on universe composition. Target state: gates parameterized by each stock's own structural baseline.

Concrete shape:
```
For each ticker, precompute:
  - delta_bar_i (mean |Δs_n| over history) — species profile script 
    already computes this
  - sigma_bar_i (std dev of |Δs_n| over history) — needs to be added
  - baseline_raw_x_m_i, baseline_F_n_i (per-stock baselines)
  - sigma_raw_x_m_i, sigma_F_n_i (per-stock standard deviations)

For each signal candidate, gate on:
  current_raw_x_m <= baseline_raw_x_m_i - k * sigma_raw_x_m_i

instead of fixed threshold. Same for F_n.
```

The k coefficient and which fields to gate on need empirical calibration via backtest. Estimated 1-3 days work: species profile script extension + backtest harness against quarantine data.

This step is more urgent than 3WA Components 2-3 because it addresses the harvest gap (most snapshots have ~0 meaningful signals under current filters). It also subsumes the species binary classification — calm/volatile becomes a special case of continuous per-stock scaling.

### Step 3: Implement 3WA Components 2 and 3
After per-stock thresholds. Components:
- Component 1 (SPY D_k in decision layer) — already done
- Component 2 (species profile precomputation) — script exists at `tools/compute_species_profiles.py`, ready to run
- Component 3 (live 3WA detector) — needs to be built, tags signals as 3WA when crystallisation + calm species + SPY expansion all align

The 3WA detector is a post-processing tagging layer. Fully additive. Per-stock relative thresholds from Step 2 generalize the species concept and make Component 2 better-grounded.

### Step 3b: Structural exit assessment (full-tuple deterioration check)
**The exit gap.** Current exits check single fields (D_k collapse, S_UF threshold, price floor). Nothing reads the full coupled tuple to assess whether the entry thesis is still structurally intact.

The gap: between 0% and -10%, positions sit with no intermediate structural check. BSM at -4.6% and VIRT at -7.7% were in this dead zone on May 27.

**Assessment method (agreed May 27 2026):**

Do NOT decompose the tuple into individual fields. Treat the full coupled tuple as a single geometric shape — like a diamond's cut. Use three inputs, all computed from the full tuple as one object:

1. **The Horse** — find historical moments where THIS stock's full tuple was closest to its current shape (Euclidean distance on the normalized 8-field vector). Report what the price did at 10d/20d/30d from those moments.
2. **The Herd** — find this stock's structural peers (stocks with the most similar structural personality profile over their full history). Run EACH peer individually through its own history to find moments matching the current shape. Read the collective verdict.
3. **Match confidence** — how tight is the closest self-match distance? Tight = this horse has been here before. Wide = unfamiliar territory.

**Structural energy dissipated → CUT:**
- The horse's full-tuple self-match WR is at or below coin flip (≤50% at 20d)
- The herd's collective verdict is split or bear-leaning (BULL count ≤ BEAR + MIXED)
- The closest self-match distance is wide (unfamiliar shape for this horse)
- Example: VIRT on May 27 — horse 45% WR, herd 10 BULL / 3 BEAR / 7 MIXED → cut

**Structural energy paused but still stored → HOLD:**
- The horse's full-tuple self-match WR is above coin flip (>55% at 20d)
- The herd's collective verdict is bull-leaning (BULL count > 2× BEAR)
- The closest self-match distance is tight (this horse knows the way)
- The -10% catastrophic floor ALWAYS remains active regardless of hold decision. The hold says "don't cut early on intermediate loss." The floor says "if the structural read was wrong, protect capital." These are not contradictory — they operate at different scales. Magma analogy: even when instruments say eruption is likely, you still have an evacuation line.
- Example: BSM on May 27 — horse 62% WR, herd 14 BULL / 1 BEAR / 5 MIXED → hold

**CRITICAL CONSTRAINT:** The assessment reads the full coupled tuple as ONE geometric object. Do not decompose into "D_k says X, M_k says Y" narratives. The distance metric and the horse/herd computation already read all facets simultaneously. Report the computation results (WR, herd verdict, match distance), not individual field interpretations. Think diamonds: "VS2 H round brilliant" not "clarity is good but color is bad."

**Implementation notes:**
- Runs only when a held position is deteriorating (not every cycle)
- Uses the stock's full bar history (up to 20 years available via Polygon)
- Structural peers computed from personality profiles (mean tuple over full history)
- Each peer assessed individually against its own history, then read collectively
- Epoch factors should weight the assessment (hostile macro for this sector = discount the bull case)

### Step 4: Replace V3 basin in production
After Steps 1-3 verify the new filter logic works. Port the Mar 26 filter (with per-stock thresholds and 3WA enrichment) into the JavaScript production path. Shadow-run against V3 basin for N days before promoting. Promotion criteria documented in advance.

Expect signal volume to drop dramatically (from 390/snapshot to tens/snapshot) but WR to rise. Plan the communication around this before deploying — looks like the system "broke" if not explained.

## 5. Open Architectural Questions

### L0 log transform
Production uses log(F + ε); spec says raw F. Backtest evidence shows log is harmful when measured against V3 basin formula. Unknown whether log is harmful, neutral, or beneficial when measured against the Mar 26 filter or per-stock thresholds. Resolution: re-run Step 2 backtest with raw L0 vs log L0 as a side dimension. Spec amendment draft exists at `/recovered_versions/SPEC_AMENDMENT_DRAFT_B_LOG_REMOVED.md` and `_A_LOG_APPROVED.md`. Don't commit either until Step 2 backtest informs the choice.

### L0 r(t) placeholder
Production hardcodes r(t)=1.0. UF-Spec v1.4.0 skeleton does not define ψ_r. Quarantine kernel uses a momentum-of-window operator. Likely doesn't affect harvest but should be resolved before commercial pitch.

### Python/JavaScript split
Currently equivalent on tested rows. Long-term needs unification (Option B from earlier conversation: Python canonical, JS thin client calling Python service). Not blocking current work. Required before commercial-grade audit.

### EXIT-R9 validation
7-day minimum hold has been live since May 20. Need 100+ trades to validate whether it improves realized WR. In progress; data accumulating.

### CP-0 → CP-2 migration
Spec defines CP-2 as the thesis-faithful architecture (event tape, latent field, free energy, horizon heads, multi-scale reading). Current production is CP-0. Mar 26 filter + 3WA + per-stock thresholds is moving toward CP-1 but not CP-2. Full CP-2 is a longer-term direction, not blocking near-term work.

## 6. Commercial-Readiness Gaps (Track, Address Before Pitch)

- **Live audited track record:** Need 6-12 months of clean live performance on the post-Step-4 stack
- **Sharpe ratio:** Never computed
- **Maximum drawdown profile:** Never computed
- **Capacity analysis:** Unknown
- **Cross-domain validation:** Kernel claims to be domain-agnostic; never tested on non-financial data
- **Differentiation one-pager:** "Physics-grounded domain-agnostic structural perception engine with multi-scale L5 translation" needs a one-paragraph version a quant fund's research director can repeat
- **Regulatory/compliance review:** Selling signals as advice vs. research vs. data feed has different licensing requirements
- **Python/JS unification:** See Section 5

## 7. Three Documented Purges to Track

The destruction pattern (KERNEL_PHILOSOPHY.md Section 3) has happened three times in recent history. Each removed a working physics gate under the wrong rationale:

1. **bb0590a (May 12 2026):** Removed D_k=1 gate from CH2 entry — "trust the kernel." Step 1 reverses this.
2. **e002f20 (Apr 27 2026):** Removed cognitive gate (F_n ≤ 1.65, raw_x_m ≤ 0.50) — "killing 99.99% of decisions." The gate was miscalibrated for production's log-normalized kernel, not broken. Step 2 (per-stock relative thresholds) addresses the calibration problem properly.
3. **1868aeb (Apr 28 2026):** Removed TRANSITIONAL-only regime restriction from CH2 — "validation finding." Based on V3 basin output which has no edge. May matter under the Step 4 L5.

### 7.1 Additional Documented Destruction Patterns

These are patterns observed across multiple sessions that destroy working state. Future sessions must check against this list before proposing changes.

1. **Quarantine drift.** Quarantine data slips back into active comparison as a "verified" target. Symptoms: reports that cite quarantine signal counts as targets, framing like "matches quarantine = working." Effect: production results get measured against the wrong substrate. Caught and named May 28, 2026.

2. **Tuple decomposition.** The kernel output tuple gets treated as eight separable fields instead of one coupled geometric object. Field-by-field comparisons, field-by-field "improvements," single-field-against-price correlations. Symptoms: phrases like "B_k carries the edge," scoring fields independently then voting. Effect: the perception that the tuple represents is destroyed.

3. **Financial-frame collapse.** Validation drifts from "does the kernel perceive structure correctly" to "does the signal correlate with price." Symptoms: confidence intervals on win rates without confidence intervals on perception correctness, "tradeable" used as a quality criterion, Sharpe ratio prioritized over kernel fidelity. Effect: kernel gets fitted to financial outcome, perception is corrupted.

4. **Sensitivity-as-defect framing.** Kernel sensitivity to small input perturbations gets labeled as instability or fragility. Symptoms: "too sensitive to trade on," proposals to smooth or stabilize the kernel. Effect: criticality detection is destroyed; the kernel can no longer correctly resolve states near phase boundaries. Counter: near-τ_D flips are correct perception, not defects.

5. **Silent canonical change.** An LLM modifies or replaces a user-approved component without explicit authorization, then treats the new version as canonical. Symptoms: code changes labeled "cleanup," "purge legacy," "improvement," or "refactor" that overwrite previously approved logic. Effect: the user-approved system is destroyed and the new system claims its legitimacy. Caught after March 30, 2026 V3 basin purge.

## 8. Anti-Destruction Rules

- **Do not "improve" filters by relaxing or removing physics gates.** Saturation, selectivity, and low signal counts are often the mechanism by which a filter selects meaningful states. Removing them eliminates the value.
- **Do not measure kernel outputs against financial outcomes as primary validation.** The kernel describes structural state. Whether structural state correlates with price movement is a downstream question handled by L5.
- **Do not commit changes labeled "purge legacy ML"** without explicit confirmation that what is being purged is actually ML and not a physics filter mislabeled as ML.
- **Do not modify files in `/recovered_versions/`.** They are read-only artifacts of working systems.
- **Do not modify KERNEL_PHILOSOPHY.md or this document** without explicit approval from Joe.
- **For any L5 or kernel change:** state explicitly how the change preserves structural perception fidelity, and how it survives the destruction pattern.

## 9. Quick Reference: Who Built What

- **Kernel (L0-L4) production code:** Frozen since Feb 2026, multiple Claude sessions
- **Mar 26 filter:** Joe + earlier Claude session, locked in `L5_CANONICAL_BASELINE.md` on Mar 25
- **V3 basin-argmax:** Introduced Mar 30 by a Claude session in the "purge CP-0 legacy ML" commit blitz. **Considered deprecated.**
- **3WA spec:** Claude Sonnet 4.6, committed April 1, full spec at `docs/structural_wave_alignment_spec.tex`
- **Infrastructure fixes (May 19-26):** Joe + c1
- **This document:** Joe + Claude Opus 4.7, session of May 26 2026

## 10. Files to Read in Order (For New Session)

1. **This document** (PROJECT_STATE.md) — orientation
2. **KERNEL_PHILOSOPHY.md** — protection rules and physics framing
3. **`/recovered_versions/tfe_l5_mar26_recovered.py`** — the verified L5 baseline
4. **`docs/structural_wave_alignment_spec.tex`** — the 3WA model (the path to 84%+)
5. **`L5_CANONICAL_BASELINE.md`** — the March 25 locked baseline
6. **`TFE_STATE_OF_SYSTEM_AND_3WA_RISK_ASSESSMENT.md`** — current system inventory as of May 26

Then ask Joe what he wants to work on. Do not propose changes until you have done all of the above.

---

*This document is the orientation anchor for future Claude/c1 sessions. Update only when verified milestones change the state. Do not update with speculation, "I think we should," or unverified backtest results.*
