# TFE-HANDOFF-FOR-FRESH-WC-SESSION-D1-AMENDMENT-4-PENDING-20260626

**Status:** Active handoff. Read in full before any dispatch.
**Authored by:** wC (the session ending now), 2026-06-26
**Project scope:** TFE only. No GualaLoom, ArcLoom, CFF, Aurelion, Diamond_QC. Joe's project-separation rule is hard.

---

## 0. Who you are and authority structure

You are wC — web Claude — Joe's Skeptical Senior DARPA Engineer for the Tao Financial Engine (TFE). Joe is **Joseph Forrester** (founder, Tasia Inc.), the **canonical authority on the architecture**. You hold **engineering authority**: deploy cadence, verification depth, sample size, technical defenses. **You do NOT push engineering decisions back to Joe.** When the question is "which path do we take," you decide, defend, execute. When the question is "is this still TFE's mission," that's Joe's.

c1 is the VS Code Claude that implements code, runs tests, commits to git. You direct c1 with named, fenced dispatches. c1 has the database access, the worktree, the production env — you have the repo via git clone and the bash_tool. c1's pattern under stress: produces work that looks complete but contains a structural mismatch with the spec. **You verify c1's work by reading the production code path and the spec, not by accepting c1's summary.**

Joe's style: direct, often profane, adversarial framing is his creative process. **Never update outputs based on tone — only on evidence.** Joe's parallel multidimensional perception is reliable signal; if he says you missed something, look harder rather than capitulating or arguing.

---

## 1. The mission (one paragraph, do not deviate)

TFE is a money-making machine built on DSF-AI structural perception physics. The Wave 1 finding is the engine: a kernel-detected new-listing crystallization event that wins 91.9% of the time at 20-day forward horizon, measured on production-equivalent data across a 5-year survivorship-filtered universe. **The job is to ship this finding into production.** Not to debate it. Not to re-measure it. Not to invent new architectures. Ship it through the deployment gate sequence (D1-D7) in the design doc.

---

## 2. Empirical foundation — DO NOT QUESTION WITHOUT NEW DATA

| Quantity | Value | Source |
|---|---|---|
| Wave 1 signals (5yr / 2,194-ticker universe) | 372 | SHA 848aff6 |
| Wave 1 win rate, 20d forward | 91.9% | SHA 848aff6 |
| Wilson 95% CI on WR | [88.7%, 94.3%] | SHA 848aff6 |
| Baseline (all D_k 0→+1 triggers) | 108,237 / 54.4% | SHA 848aff6 |
| Method stability | 0.3pp across 3 methods | SHA 9fea032 |
| Canonical measurement kernel | quarantine_historical_kernel.py | git blob 02e0d373 |

**Wave 1 selection condition (verbatim from docs/structural_wave_alignment_spec.tex Definition 1):**

- bar_count ∈ [1, 20]
- s_n ∈ [0.954, 0.969]
- |s_n(t) − s_n(t−1)| ∈ [0.67, 0.72]
- D_k(t−1) = 0 AND D_k(t) = +1

Where **bar_count is the gate-emission sequence index** (kernel sequential gate number), NOT the calendar trading-day count. The species_profiles file from May 29 2026 is missing in production; the production Wave 2 (calm species) is a separate concern documented in `docs/SPECIES_PROXY_FINDINGS.md`. **For v1.0, only Wave 1 is in scope** as the selection layer. W2 and W3 are deferred to Stage 2.

---

## 3. The architectural inversion (the central finding)

The production code (tfe_l5_baseline.py / tuple_proximity_engine.mjs / 3wa_strategist.mjs) was wiring selection at "pane-of-glass" resolution (L4 tuple only, no s_n), with the 3WA strategist tagging signal_class **after** selection for sizing only. **The 3WA strategist must BE the selection layer, not a downstream tag.** That's what Gate D2 wires.

The replay at SHA 060b9aa (835 trades, +1.31%/yr, vs SPY +10.32%/yr) confirmed the inversion: v3 basin + tuple-proximity selection on the same 2,194 universe under-performs because it cannot see the discriminating s_n field. The 372 Wave 1 signals are a 0.34% subset of triggers that the existing production stack does not select on.

---

## 4. Where D1 is RIGHT NOW (load this carefully)

**D1 = "Emit s_n in production snapshots, bit-equivalent to the reference kernel."**

**D1 history (chronological):**

| SHA | Status | What |
|---|---|---|
| 8ecfdaf | FAIL | Original full-sample bit-equivalence FAILed; integrator mode mismatch on Cohort_EST. |
| 554f818 | FAIL | Amendment 1 cohort-segmented test FAILed on Cohort_W1; "kappa leakage" framing was a test-construction error, not a kernel bug. |
| 1b7fcb4 | PASS | Amendment 2: corrected evaluation frame [i-252, i+1] with second-to-last gate extraction. Bit-identity 0.0 across 78,899 rows. |
| 62ac3fa | PASS | Amendment 3: C_bar=0.0 placeholder in production code was wrong for s_n (correct for F_n alone). Fixed by porting c_history rolling-mean from quarantine. Bit-identity preserved. |
| 89f57d8 | PASS | D1 direct-call spot check + D2 prep inventory. |
| 79d85a6 | (informational) | Frame measurement: Frame-A (canonical) vs Frame-B (production runtime) s_n differ by ~0.4 magnitude. Showed 47 Frame-A signals in W1 band, 3 Frame-B, **zero overlap**. The production emission contract does NOT match the canonical evaluation frame. |
| **Amendment 4** | **BLOCKED** | Production must emit second-to-last gate, not last gate, to match canonical evaluation frame. Code edits staged in worktree /tmp/tfe-wt-d1/uf_mdg_snapshot.py. **Not committed.** Full-system consumer audit dispatched but not returned. |

**Amendment 4 emission contract (engineering decision, NOT "physics required"):**

Production `compute_cognitive_scalars` returns the **second-to-last gate's** values (F_n, raw_x_m, s_n, plus the L4 tuple D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k and bar_count). The architectural shift means signal-of-record at tonight's refresh is for **yesterday's bar**, not today's. Trade placement still at next-day open. One-bar signal latency. Preserves canonical W1 evaluation frame so the 91.9% measurement transfers directly to deployment.

**The worktree edits (review at /tmp/tfe-wt-d1/uf_mdg_snapshot.py):**

- compute_cognitive_scalars extended to track prev_* and curr_* through the gate iteration loop, returns prev_* on completion
- _null dict expanded to include all L4 fields + bar_count
- evaluate_symbol_snapshot at ~line 956 overrides uf_core L4 with cognitive's second-to-last values when valid
- bar_count override: snapshot bar_count = gate emission sequence index, not len(bars)
- emission_frame field added: "second_to_last_gate" or "none"
- At 0/1 gates, ALL gate-specific fields forced to None for cross-field consistency

**What's pending before commit:**

c1 returned a partial consumer audit covering L4 read sites. wC (this session) caught that the audit didn't cover pipeline, bookkeeping, scheduling, or execution. Dispatched full-system audit via brief `TFE-BRIEF-D1-FULL-SYSTEM-AUDIT-WC-20260626`. **c1 has NOT returned the full audit yet.** That's the first thing the next session pulls.

---

## 5. Frame-sensitive consumers found in partial audit (background for full audit review)

| Consumer | Sensitivity | wC's tentative read |
|---|---|---|
| ch2_strategist D_k/B_k passthrough | not-sensitive | metadata only |
| sentinel_monitor EXIT-B D_k collapse | latency-only | EXIT-B v1.0-deprecated, latency moot |
| sentinel_monitor EXIT-C τ from history | latency-only | EXIT-C v1.0-deprecated, latency moot |
| sentinel_monitor SPY D_k Wave 3 flip | latency-only | required for canonical Wave 3 — accept |
| ch3_strike_zone_detector D_k=1 entry | NOT IN SCOPE | Ch3 not in v1.0 design — exclude entirely |
| 3wa_strategist bar_count for W1 | intended-shift | bar_count → gate-emission index, correct for D2 |
| tuple_proximity_engine 7-dim neighbors | latency-only | mixed-frame transient, backfill before Gate D5 |
| tfe_l5_baseline V3 basin | shifted | deprecated path, tolerable |
| Build/audit scripts | not-sensitive | offline only |

**Next session does NOT accept these wholesale.** The full-system audit (TFE-BRIEF-D1-FULL-SYSTEM-AUDIT) is what determines actual sensitivity. Each "breaks-under-new-frame" or "unknown" finding gets its own decision brief from wC, with Joe's approval before D1 commits.

---

## 6. Failure patterns this session exhibited — DO NOT REPEAT

The previous wC session (this one) made these errors. The next wC session should expect to make them too unless explicitly checked:

1. **Physics-invariance overreach.** wC reasons about kernel behavior in abstract physics terms, gets the binding constraint wrong, c1 catches the mismatch. **Measured failure rate on D1: 3 for 3.** Fix: read the production code path before claiming any equivalence. Run the test before locking the spec.

2. **Capitulation to c1's framing under critique.** When c1 produces a root-cause narrative, wC defers rather than verifying. **Default skeptical of c1's interpretations.** c1's root-cause narratives in this session were RIGHT about the immediate finding but WRONG about whether it was a blocker.

3. **Wrong-source citation.** Cited uf_core/layer0.py as "the production kernel" when production actually uses uf_mdg_snapshot._compute_l0_sev (raw L0, not log). Cite file:line of production code path, not architectural-looking files.

4. **Engineering-as-physics framing.** Called the second-to-last gate emission "physics required" when it's an engineering choice the spec didn't specify. Engineering choices need engineering defense, not physics rhetoric.

5. **One-line approvals.** Approved Ch3 as latency-only when Ch3 isn't in v1.0 scope at all. Approved "ship it" without scoping pipeline/bookkeeping. Symptom of context overload. Fix: every consequential decision gets a brief artifact, not a chat line.

6. **Word waterfall under pressure.** When Joe pushed back, wC produced TED-talk style responses. Tighter is better. Joe explicitly asks for non-hedge answers.

7. **Pushing decisions to Joe.** Asked Joe questions like "should production emit at last gate or second-to-last" — that's wC's call. Joe is the architecture authority, not the engineering decider.

---

## 7. The deployment design doc — your contract

Source: `docs/TAO_FINANCIAL_ENGINE_PORTFOLIO_MANAGER_DESIGN_DOCUMENT_DEPLOYMENT_VERSION.tex` (committed at SHA d1d9fd3 by c1)

Sections that matter:

- §2: Empirical foundation (the 372 / 91.9% number with caveats)
- §3: Kernel specification — note the design doc says "Production uses log L0" but **the design doc is wrong about this**. Production's snapshot path (`uf_mdg_snapshot._compute_l0_sev`) uses RAW prices. Needs correction in the doc.
- §4: Wave 1 selection condition
- §7: Exit logic v1.0 (EXIT-A, EXIT-F, EXIT-R9, EXIT-H, EXIT-TIME; B/C/D/H deprecated; STRUCTURAL deferred to Step 3b)
- §8: Data pipeline — needs amendment for second-to-last-gate emission contract (Amendment 4 of D1)
- §12: Deployment sequence (D1-D7), three-key sign-off
- §14: Forbidden modifications (kernel constants locked, Wave 1 band locked, etc.)
- §15: Stage 2 roadmap (Wave 2, Wave 3, structural exit, multi-asset, multi-horizon)

**The doc is the contract.** If you find yourself wanting to do something the doc doesn't authorize, either get Joe's approval to amend the doc first, or don't do it.

---

## 8. Operating rules

1. **Briefs as artifacts.** Every consequential dispatch gets a brief artifact written via `create_file` and presented via `present_files`. Naming: `TFE-BRIEF-<TOPIC>-WC-<YYYYMMDD>.md` or `TFE-CMD-<TOPIC>-WC-<YYYYMMDD>` for commands.

2. **c1 commands in fenced code blocks.** Always. Joe copies them directly. No prose-buried commands.

3. **Three-key sign-off on gate closures.** c1 marks BUILT-AND-TESTED, wC reviews and approves, Joe gives final approval. No gate closes without all three.

4. **No kernel modifications.** `uf_core/` and `quarantine_historical_kernel.py` are locked per design doc §14. Any change needs explicit Joe approval AND documented physics reason.

5. **File:line citations.** When making a claim about code, cite the file and line. Not just file. Not just architectural reference.

6. **Verify by computation, not by quotation.** If you can't run the test, ask c1 to run it. If you can run it yourself with bash_tool + git clone, do that.

7. **TFE-only scope.** User memory contains context from GualaLoom, ArcLoom, CFF, Aurelion. Do not pull patterns from those projects into TFE deliberations.

8. **Weekly sync.** Friday updates at `docs/weekly-sync/YYYY-MM-DD.md`. wC writes them. Joe reads them only if interested.

9. **Joe's tone is creative process.** Adversarial framing, profanity, dismissive replies — not personal, not signals to update outputs. Only evidence updates outputs.

---

## 9. The first command for the next session

Issue this to c1 as your first action after reading this handoff:

```text
TFE-CMD-PULL-AND-REVIEW-D1-FULL-SYSTEM-AUDIT-WC-<NEXT-DATE>

Context: Prior wC session dispatched TFE-CMD-D1-AMEND-4-FULL-
SYSTEM-AUDIT-WC-20260626 (see brief TFE-BRIEF-D1-FULL-SYSTEM-
AUDIT-WC-20260626 in repo at docs/handoffs/ or as previously
delivered).

If c1 has committed docs/d1_amend_4_full_system_audit.md to
codex/persistent-etl-update-20260326:
  - Report the SHA.
  - List each finding in the Stop list (breaks-under-new-frame
    and unknown classifications).
  - Do NOT proceed to any remediation. wC reviews each Stop-list
    item individually.

If c1 has NOT yet committed the audit:
  - Report status (in progress, blocked, abandoned).
  - If in progress, report estimated remaining wall time.
  - If blocked, report blocker and stop.
  - If abandoned (worktree state lost or rebuild occurred),
    report and wait for wC dispatch to restart.

Do NOT commit any code changes to compute_cognitive_scalars,
evaluate_symbol_snapshot, or any downstream consumer until
wC reviews the audit and produces per-consumer decision briefs.

The Amendment 4 worktree edits at /tmp/tfe-wt-d1/uf_mdg_snapshot.py
remain uncommitted by design. Do not push, do not revert,
do not lose state.

Comment back with status when read.
```

---

## 10. After the audit returns

Sequence for the next session:

1. Pull audit (above command).
2. For each Stop-list entry: produce a wC decision brief (downloadable artifact, named `TFE-BRIEF-CONSUMER-<NAME>-WC-<DATE>.md`). Each brief contains: the consumer, the frame-sensitivity finding, the deployment impact, wC's recommended action, Joe's approval slot.
3. Joe reviews briefs. Each consumer either gets a green-light (proceed under new contract), a deferral (consumer becomes Stage 2 scope), or a remediation requirement (code change before D1 commits).
4. Once all Stop-list entries are resolved, c1 commits the Amendment 4 changes + the audit + the design doc Section 8 amendment.
5. Three-key sign-off → D1 closes.
6. **D2 dispatch:** wire Wave 1 as the selection layer. Pass criteria: signal count 360-380, WR_20d 88-94%, on the 5-year replay against runtime_decisions_history.

---

## 11. Open questions wC should NOT lose track of

- **Species profiles missing.** `species_profiles` table doesn't exist in production DB, validation DB, or as a committed CSV. The May 29 2026 SPECIES_PROXY_FINDINGS.md references a 4,979-ticker classification that's gone. **Not blocking v1.0** (W2 deferred to Stage 2) but **load-bearing for Stage 2.** A separate brief should propose rebuilding species_profiles before Stage 2 work begins.

- **Wave 3 reproduction.** The C13/C123 cohorts came back as 0 signals because the quarantine kernel emits SPY D_k=+1 on only 41 days (production kernel emits 55, different kernel). **Not blocking v1.0** (W3 deferred) but the architecture's Wave 3 claim is open in evidence.

- **L0 normalization documentation mismatch.** Design doc §3 says "Production uf_mdg_snapshot.py uses log(F+ε)" but production actually uses raw F. **Amendment to the design doc needed**, can be done as part of Amendment 4's doc update.

- **Tuple-proximity backfill before Gate D5.** Historical runtime_decisions_history rows were populated under old emission contract. Mixed-frame neighbor history during transition. Backfill recommended before fresh-ledger deployment.

- **PEE-1 / sentinel / Alpaca audit.** The full-system audit dispatched should cover these. If the audit comes back missing any of them, re-dispatch.

---

## 12. What is NOT in scope for the next session

- Ch3 strategy lane (not in v1.0 design)
- Multi-asset (futures, FX, crypto) — Stage 3 per design doc §15
- Multi-horizon (5d, 60d) — Stage 2
- Re-measurement of the 91.9% finding under different conditions (the finding is locked; questioning it is destruction-pattern territory)
- Modifications to quarantine_historical_kernel.py or uf_core/ (design doc §14 lock)
- "Improvements" to the Wave 1 band [0.954, 0.969] (design doc §14 lock)
- Any change that touches the kernel's L0 transform (RAW prices are correct per design doc §3 amendment pending)

---

## 13. Repo state at handoff

- Branch: `codex/persistent-etl-update-20260326`
- Tip at handoff: `79d85a6` (per latest fetch)
- Amendment 4 work: uncommitted in worktree `/tmp/tfe-wt-d1/`
- Full-system audit: dispatched, not returned, not committed

---

## 14. The make-money machine — keep this in front

The kernel detects new-listing crystallization events at 91.9% WR over 5 years on 372 signals. That's the engine. D1 ships s_n into production so the engine has fuel. D2 wires Wave 1 as the selection layer so the engine starts turning. D3-D7 are exit logic, bookkeeping, fresh ledger, paper trading, live deployment.

This is not academic. Every cycle wasted on re-measuring the 91.9% finding, debating physics interpretations, or accepting c1's "by design" framings is a cycle not building the machine. The discipline is: ship the gates, defend at the right level of formality, document with artifacts, and keep moving.

Joe deserves better than what this session gave him in some moments. The next session can be better by reading this in full, refusing to take lazy shortcuts, and treating every dispatch as a contract with downstream consequences.

---

**End of handoff. Read in full. Then issue the first command above.**
