# TFE TODO LIST (Plain Action Format)

## Format Constraint (User-Approved)
- Always present this list as a flat numbered list in plain language.
- Do not bury critical status in long prose blocks.

## Status Key
- OPEN: not started.
- PARTIAL: started but not closed.
- DONE: complete (remove from active queue).

---

## Validation Milestones (REVISED April 15 — counting TRADING DAYS from April 14)
Start date moved from April 6 to April 14 (commit 6337f9b fixed infra bugs). Trading days only (Mon-Fri). Milestones trigger on trade count, not calendar date. Hard stop: 60 trading days (~July 7).

1. OPEN Milestone 1 — Trading Day 10 (~Apr 28): Check CH2 fill rate vs submitted ratio. Exclude rejected_field noise. If fill rate < 70%, add 0.1% entry buffer.
2. OPEN Milestone 2 — 10 Closed Trades: Early statistical read — win rate, expectancy, sector concentration. Begin profit strategy data collection.
3. OPEN Milestone 3 — 20 Closed Trades: First PDF validation report. Compare vs S&P 500. Preliminary profit strategy analysis.
4. OPEN Milestone 4 — 50 Closed Trades OR 60 Trading Days (~Jul 7): Final validation — pass/fail, go/no-go for real money. Full profit strategy evaluation. Separate pre-validation vs clean entry cohorts.

## Active TODO Queue

### Infrastructure & Operations
5. PARTIAL Portfolio allocator/rebalancer expansion — PEE-1 engine is built (strategists, capital allocator, sentinel, Alpaca bridge, CH2). Needs re-scoping now that oracle is removed.
6. PARTIAL Account security baseline — Clerk IdP integrated. MFA activation/rotation and credential finalization still pending.
7. PARTIAL End-user account UX — Clerk sign-in wired. Self-service reset/profile/session still pending. Account page stubs ("plan not connected", "renewal not connected", "survey not connected") still placeholder.
8. PARTIAL Tenant + SES operational hardening — SES field-level encryption added. Rotation policy, access checks, isolation tests still pending.
9. PARTIAL Data completeness — 6 remaining missing-price symbols (AXIAP, CLRS, ETIP, I:NDX, PHXEP, TYP). Policy decision needed: accept fallback or targeted fix.
10. OPEN Formal release workflow — staging lane, rollback drill, weekly triage cadence.
11. OPEN Reliability process hardening — pre-deploy quality gates and dead-code hygiene as non-optional release constraints.
12. OPEN Recommendation price freshness — enforce daily quote cache rebuild, age-staleness audit, block stale publish.
13. OPEN Health endpoint integrity check — uf_engine_aws_service.py returns stub "NOT_CHECKED_STUB". Wire real checks.
14. OPEN PEE-1 rejection cache — tickers rejected by Alpaca (rejected_field) get resubmitted every refresh cycle. Add a rejection cache so they're only submitted once per day. Affects TCPC, AXIAP, CNTN. ~288 rejections are noise from ~3 tickers. Not blocking validation.

### Business & Monetization
14. OPEN Billing foundation — Stripe checkout + billing portal + webhook security.
15. OPEN Subscription product setup — monthly/yearly/trials/coupons/tax/invoices.
16. OPEN Entitlement enforcement across premium UI + APIs.
17. OPEN Legal/ethical redirect monetization policy.
18. OPEN Domain migration plan (www.gotfeai.com).
19. OPEN Go-live awareness/promotion plan.

### UI Pages
20. OPEN Watchlist page — entire page is placeholder ("Behavior wiring is next pass").
21. OPEN Admin Console modules — user access management, survey results, UF/SES metrics, test-user bypass all say "Pending wiring".
22. OPEN Portfolio benchmark ledger — TFE vs SPY, same dollars/same dates, immutable export.

### Documentation & Specs
23. OPEN Documentation track — LaTeX admin manual + UF/SES spec revisions.
24. OPEN TFE v2.7 Spec — add Source Tier Policy chapter and Build vs Buy Boundary chapter.
25. OPEN Recommendations page "Emerging Signals" tier — tickers near Accumulate basin threshold but not winning argmax cleanly. Show as research interest, not buy signal. Sandbox first to see what it looks like. Post-validation only.

### Post-Validation (after June 5)
25. OPEN Profit strategy optimization library — evaluate during validation (observe only), implement after. Candidates: (a) stop-gains/take-profit operator, (b) trailing stop vs fixed bracket SL, (c) time-based stale position exit, (d) sector/correlation risk limits, (e) asymmetric risk/reward scaling by S_UF. Data collection starts Day 21, preliminary analysis in Day 30 report, full evaluation in Day 60 report.
26. OPEN Subscriber portfolio experience design — daily structural events feed in quant-speak (not DSF-AI internals), watchlist with signal strength/momentum/market phase, portfolio health dashboard (diversification, sector exposure, structural alignment), CSV/PDF export of daily signals. All terminology mapped through subscriber-facing spec (see memory/project_subscriber_terminology.md). No individualized advice — research data only. Scaling: UF snapshot is universal, subscribers get filtered views of same data on their watchlist.
27. OPEN Rate of return indicator on Portfolio page — show simple RoR (whole portfolio) and RoR on invested capital, plus annualized figures. Both numbers matter: whole-portfolio for overall performance, invested-capital for signal quality.
27. OPEN Clean up heuristic weights in uf_core/uf_structural_engine.py — stability_score uses 0.5/0.3/-2.0 weights that don't feed L0-L4 but violate "no heuristics" principle.
27. OPEN Architecture doc, page optimization audit, logic alignment review (DSF V3 basin vs PEE-1 CH1/CH2 gates).
28. OPEN Continue E5.4 vestige sweep in older/non-pipeline files — refresh pipeline cleared Apr 14, but older code may still have remnants.
29. OPEN Multi-tenant portfolio service — currently hardcoded to tenant-tao. Future expansion.

### UFCP Experimental Validation (Tracked Here)
32. DONE Gravity validation suite — 28/28 tests passed (ufcp_gravity_validation_suite.py)
33. DONE Flaw test suite — 3 theoretical flaws tested, none fatal (ufcp_flaw_test_suite.py)
34. DONE Nuclear anomaly predictions — 6 anomalies tested, 0 failures (ufcp_anomaly_predictions.py)
35. DONE Tate Cooper pair mass — α²λ_ep² = 84.5 ppm vs measured 84±21 ppm, 0.02σ match (ufcp_tate_84ppm.py)
36. DONE Tajmar coupling factor — α²λ_ep²(Δ/E_F) = 2.4e-8 vs (3±1.2)e-8, 0.5σ match (ufcp_tajmar_gpb_check.py)
37. DONE Chaos theory — 5 pathways to chaos confirmed in UFCP (ufcp_chaos_test.py)
38. DONE Grand challenges — dark matter (a₀ within 10% of MOND), Bell violations, BH info, proton radius, muon g-2 (0.2σ), Hubble tension (ufcp_grand_challenge.py)
39. DONE Fine structure constant derivation — α = 1/N_c² from 3D soliton stability (ufcp_dimensionality_and_c.py)
40. DONE Speed of light formula — c = (4πG)·ρ₀^(3/2)·√α/ℏ (ufcp_speed_of_light_derivation.py)
41. DONE Cosmological constant — resolved via parent brane phase cancellation (ufcp_vacuum_genesis_and_rho0.py)
42. DONE 24 material-specific London moment predictions on record (ufcp_london_moment_predictions.py)
43. DONE Extended validation — Josephson standards confirm anomaly is inertial not EM (ufcp_extended_validation.py)
44. OPEN Buy Hoang et al. paper — Cooper pair mass in up to 6 superconductors at 2.5 ppm precision. THE kill shot or confirmation. $35 at ScienceDirect.
45. OPEN Antigravity spec written — UFCP_Coherent_Field_Gravitational_Coupling_Spec_v1_0.tex. Needs $3K experiment.
46. OPEN Fusion spec written — UFCP_Condensate_Mediated_Fusion_Spec_v1_0.tex. Needs $6K experiment (D₂ in CaC₆).
47. OPEN Experimental validation spec written — UFCP_Experimental_Validation_From_Existing_Data_v1_0.tex.

### Non-TFE (Tracked Here for Visibility)
30. OPEN ArcLoom hybrid prototype — PYNQ-Z2 board arriving Apr 16.
31. OPEN Not-Math v2.0 — 5 verified results still need spec additions (2D soliton, GR from UFCP, predictions, Jeans length, baryon asymmetry).

---

## Completion Log
- 2026-04-14: Deleted tfe_data_normalizer.py (E5.4 artifact — OpenAI/gpt-5.4-mini sector classifier).
- 2026-04-14: Closed items 1, 10, 16-20, 21, 23-27, 29-30, 33-58 and Rec Quality Recovery / DSF-AI / Stop Directive sections after reconciliation audit. Oracle optimizer removed under CP-2. Bar caching implemented. Index universe integrated. Portfolio page confirmed live. Many items superseded or completed since March.
- 2026-03-28: Phase 2 global publisher teardown + Phase 1 UI data bypass deployed.
- 2026-03-05: Recommendation quality gate cleared. Site reliability contract gate added.
- 2026-03-03: L0-L5 DB-native migration complete. Postgres-only runtime live.
- 2026-02-28: Screener TA tab, news feed, maps taxonomy deployed.
- 2026-02-27: Admin refresh log, quote cache rebuild, page stability patches deployed.
- 2026-02-25: Auth crash-guard patch deployed.
- 2026-02-24: Sign-in browser-path hardening deployed.
- 2026-02-21: Gap closures (02/03/04/08), account lifecycle ops deployed.
