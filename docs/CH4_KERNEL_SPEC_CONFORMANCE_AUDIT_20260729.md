# CH4 Kernel Conformance Audit — code vs UF-Spec v1.3.0 and merged TFE spec (2026-07-29)

Demanded by Joe after the parity audit was (correctly) rejected as
insufficient: parity proved my engine matches the preserved lineage
implementation bit-for-bit; it proved NOTHING about whether that lineage
matches the specification. This is the clause-by-clause review of the
kernel semantics the CH4 engine currently executes (`quarantine` lineage,
imported verbatim) against (a) the original UF-Spec v1.3.0 (docx, §§2–7,
§11 formal framework) and (b) the merged TFE spec (ch05/ch06).

Verdicts: **CONFORMANT** / **DEVIATION** (different form than the cited
spec) / **FLATTENED** (structure or information the spec preserves is
collapsed) / **MISSING** (mechanism absent). "Original" = v1.3.0;
"merged" = TFE ch05/ch06.

## L0 — field + SEV

| # | Clause | Spec | Code | Verdict |
|---|---|---|---|---|
| 1 | Normalization (orig §2.4, F̄=S(L(F)), log/variance-stabilized, scale-invariant; SEV rules §2.3 "invariant under monotonic scaling") | dimensionless field | **raw dollar prices** (RAW mode) | **DEVIATION — root of the observed scale pathology** (gate-per-bar on high-priced names, dead gates on low-priced). The in-repo `uf_core` L0 applies log and even documents this as "Corrected"; the lineage kernel never adopted it. My LOG variant applies it but was declared secondary. |
| 2 | SEV six-tuple (merged ch05; orig §11.1) | (F, ΔF, σ, κ, r, N) | all six present | CONFORMANT |
| 3 | σ, κ forms (merged ch05) | window variance; second difference w/ endpoint rule | exact | CONFORMANT |
| 4 | Relevance r(t) (orig: "domain relevance"; lineage docs name the R axis = attention/volume) | graded domain relevance | `psi_r` = binary 1.0/0.5 step (close > 10-bar mean); **no volume/attention input anywhere** | **FLATTENED** — two-level step, and the original's fourth input axis (R = attention) is absent from the entire adapter (close-only input, acknowledged in merged ch05) |
| 5 | Negative space N(t) (merged ch05) | 3-condition quiet flag | exact | CONFORMANT (orig §2.5 source-classification NSSC: MISSING, single-modality domain — low impact) |

## L1 — gates + mosaic

| # | Clause | Spec | Code | Verdict |
|---|---|---|---|---|
| 6 | Boundary operator (orig §11.2) | D(t)=‖SEV(t)−SEV(t−1)‖ (vector norm over the tuple), **adaptive** τ(t)=τ₀+α·Var(SEV[t−w:t]), boundary also on N-flip | scalar weighted sum α₁\|ΔF\|+α₂σ+α₃κ, **fixed** τ_D=0.20, no N-flip boundary | **DEVIATION** from original (merged ch05 itself adopted the scalar-sum + fixed-τ form; code follows merged). The original's adaptive threshold is the design's own answer to price-scale dependence — finding #1's cure lives here. |
| 7 | TVR (merged ch05: T,V,R integrals) | 3-vector | exact | CONFORMANT to merged (orig §3.2 5-component fingerprint incl. σ_k, Curv_k — reduced by the merged spec itself) |
| 8 | Multi-lattice projections, C_k, δ_g (merged ch05) | as specified | exact | CONFORMANT |
| 9 | Lattice-consensus down-weighting (orig §3.3, K_max), compression/expansion CED (§3.4), drift correction δ_g-as-operator (§3.6) | required in original | none present (C_k measured only; δ_g measured only) | **MISSING** (also absent from merged spec) |

## L2 — interpretive layer

| # | Clause | Spec | Code | Verdict |
|---|---|---|---|---|
| 10 | **Contrast vector** (orig §4.2, §11.4: CV_k = TVR_k − mean(TVR over neighboring gates)) | same-unit subtraction — contrast of a gate against its local field | CV_k = TVR_k − μ_k where μ_k = means of (ΔF, σ, κ) **inside the same gate** | **DEFECT — dimensionally incoherent**: subtracts (mean-ΔF, mean-σ, mean-κ) from (T bars, V field-units, R relevance-sum). Apples minus oranges feeds ‖CV‖ into resonance term 2 and into ψ. The merged spec's own formula (CV=TVR−μ) inherited this; the original is well-defined. **Highest-priority physics fix.** |
| 11 | Interpretive weight w_k (orig §4.1: f(TVR,CV,S,Reg,M), monotone in S) | structural weight | w = V/V_max (volume share of the largest gate) | **FLATTENED** — depends on V only; monotonicity-in-S constraint unmet; whole-history V_max also makes it non-local |
| 12 | Structural score S_k (orig §4.3: g(σ_k, Curv_k, R_k)) | built from gate variance, curvature, relevance | 1/(1+C+δ_g) | **DEVIATION** — uses neither σ, curvature, nor relevance |
| 13 | Regimes (orig §4.4: stable/transitional/volatile/chaotic) | 4 classes | C>1 ? TRANSITIONAL : STABLE | **FLATTENED 4→2** (`uf_core` has the 4-way χ/ψ classifier; lineage kernel does not) |
| 14 | Anomaly suppression IAS (orig §4.5: down-weight w ← β·w) | graded damping | binary block via g_k | DEVIATION (binary vs graded) |

## L3 — resonance

| # | Clause | Spec | Code | Verdict |
|---|---|---|---|---|
| 15 | Resonance functional (merged ch05 5-term λ form) | as specified | exact | CONFORMANT to merged |
| 16 | Hysteresis, admissibility g, URF (merged) | as specified | exact | CONFORMANT |
| 17 | Cluster coherence C(𝒢), temporal anchors, contextual gating (orig §5.2–5.5); cross-core fusion (merged ch06) | cross-structure resonance | **single-symbol only; none of it** | **MISSING** — the field never sees another ticker; every cross-structure mechanism of both specs is absent |

## L4 — decision dynamics

| # | Clause | Spec | Code | Verdict |
|---|---|---|---|---|
| 18 | D/M/Rev/U*/P/B recursions (merged ch05) | as specified | exact | CONFORMANT to merged (orig §6 DPS sigmoid surface / PBD / BCSV / breathing modulation are a different formalization the merged spec replaced — documented evolution, not silent) |

## L5 — governance

| # | Clause | Spec | Code | Verdict |
|---|---|---|---|---|
| 19 | Event tape minimum types (merged ch06: 7+ types) | gate, regime, resonance-reversal, negative-space onset/release, stability crossing, collapse, rule events | 3 of 7 (gate close, regime change, resonance reversal) | **FLATTENED** — negative-space and stability/collapse events never enter the tape |
| 20 | Validation plane S(UF), R(UF), GSS, DSS, DSF-Stability (orig §11.9–11.10; merged ch06 inputs + hard blockers) | computed, gating emissions | **stubbed constant 1.0** (`s_uf_default`) | **MISSING/STUBBED** — the entire stability/robustness input to governance is a constant; hard blockers can never fire |
| 21 | Γ structural inconsistency (merged ch06: λ_U·U†+λ_C·C†+λ_N·N†+λ_X·X†−λ_ρ·ρ) | 5 pressure terms | Γ = 0.5(u + (1−ρ)) | **FLATTENED** — negative-space pressure, divergence pressure, cross-scale inconsistency dropped |
| 22 | RMM bands, a_n, z_n, surprise, F_n, Q_h readouts (merged ch06) | as specified | exact (d_z=3 degenerate basis — legal "fixed versioned" choice) | CONFORMANT |
| 23 | χ coherence (merged ch06 graded formula) | χ ∈ [0,1] | binary sign-agreement | DEVIATION (coarser) |
| 24 | Action mapping + N_persist + cooldown (merged ch06) | full mapping + soft rules | full mapping present (built this session); N_persist/cooldown = lineage-realized none | PARTIAL — declared |
| 25 | Multi-core quorum/disagreement (merged ch06) | fusion + quorum | single core, degenerate mode | MISSING (degenerate mode is legal if audit-logged — now logged here) |

## Summary

The engine is a **faithful copy of a kernel that is itself non-conformant
in specific, enumerable ways**. The five findings that matter most, in
priority order:

1. **CV dimensional incoherence** (#10) — a real physics defect at the
   heart of L2/L3; the original defines it correctly.
2. **No field normalization** (#1) + **fixed scalar boundary instead of
   adaptive ‖ΔSEV‖ threshold** (#6) — together the entire scale
   pathology observed in evaluation.
3. **Validation plane stubbed to 1.0** (#20) — ch06 governance runs with
   its stability senses disconnected.
4. **Relevance axis flattened to a binary step; attention/volume axis
   absent** (#4) — the original four-axis input reduced to one.
5. **Regimes 4→2, event tape 3/7, Γ pressures dropped** (#13, #19, #21)
   — interpretive and governance information discarded.

None of these were introduced this session; all are inherited from the
preserved lineage and, in several cases, from the merged spec's own
formalization. My error was declaring the kernel "faithful" on parity
alone — parity to the lineage ≠ conformance to the spec. A conformant v2
realization (fixes 1–5, each cited to its clause, no free parameters
beyond declared spec constants) is the concrete next build, pending
approval.
