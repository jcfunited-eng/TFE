# GL-BRIEF-METADECAY-WC-20260610-033
## Two-Speed Metaplastic Decay — Working Atlas Time-Constant Fix

**Author:** wC | **Date:** 2026-06-10 | **Status:** Stage 1 (harness) authorized; Stage 2 (prod) gated on Stage 1 GL-FIND
**Inputs:** wC model (metaplastic/model.py, P0–P5 runs), GL-BRIEF-032 (deep atlas, deployed task:67/68), observed prod decay (atlas 25.16 → 1.73 over ~5h; 2/~40 session items promoted at first dream)
**Risk class:** HIGHER than 032 — this MODIFIES the existing working-atlas decay path, not additive. Hence harness stage is mandatory and prod gets an instant-revert switch.

---

## 1. Problem

Working atlas decay is a single global heuristic: DECAY_LAMBDA=0.0005 per
10 ticks ≈ 12-minute strength half-life. Not derived from anything — a knob
tuned for early demos. Consequence in prod: an entire session of high-dwell
learning decays to near-zero before the next dream; the deep atlas can only
promote the rare survivor (observed: 2). The decay rate is doing two jobs:
noise washout (needs FAST) and learning retention (needs SLOW). One constant
cannot do both.

## 2. Design (wC model results, prod-calibrated constants)

Three changes to LivingAtlas decay; deep atlas untouched.

**A. Dwell-gated two-speed baseline.** At encoding:
   - dwell_ticks < 4  → lam_base = DECAY_LAMBDA (fast channel, 12-min HL; junk self-cleans)
   - dwell_ticks >= 4 → lam_base = DECAY_LAMBDA / SLOW_DIV (slow channel; SLOW_DIV=12, ~2.3h HL)
   Same discriminator already validated for the deep Path B gate. Model: insensitive across SLOW_DIV 4–48.

**B. Metaplastic slowdown.** Per-entry effective rate:
   lam_eff = lam_base / (1 + K * reinforcement_count), K=2.0.
   Each reinforcement (attention, dream top-half boost) increments the count.
   Memories earn their persistence.

**C. Post-promotion release.** When an entry is promoted to deep (either path),
   its working copy reverts to the fast channel (lam_base = DECAY_LAMBDA,
   reinforcement_count = 0). Deep holds permanence; on-attention prior (032)
   reinstates on cue; working stays lean.

**Explicitly NOT in this brief:** waking micro-replay. Modeled, works, but
retention holds without it (80/80 promoted, replay off) and naive selection
showed full lock-in pathology. Deferred as future enrichment brief.

## 3. Model evidence (scalar, prod constants — primitive test, not capability)

| Design | S1 alive at dream (6h gap) | Promoted | Noise alive | Working size |
|---|---|---|---|---|
| Prod (global 0.0005) | 0/40 | 0/40 | 0 | 40 |
| Clamp only (global /12) | 40/40 | 40/40 | **21** | 101 |
| Two-speed + metaplastic | 40/40 | 40/40 | 0–1 | ~80 |
| 5-day, no release | 400/400 | 400/400 | 1 | **311 (unbounded)** |
| **5-day, full design** | **400/400** | **400/400** | **0** | **4** |

Gaps tested 3h–24h: 40/40 at all. Day-1 content fully retained in deep at day 5.

## 4. Stage 1 — c1 harness validation (REQUIRED before prod)

Extend test_deep_atlas_harness.py (real code paths, no reimplementation):
1. Reproduce baseline: session-load of high-dwell entries decays below
   threshold within ~6h sim under current global lambda; ≤ a few promote.
2. Implement A/B/C in harness only. Re-run the FIND-02 population set
   (TRUE/EPISODIC/NOISE incl. realistic cofire noise with the 0.82 tail) plus
   the multi-day timeline. Measure: retention to dream, promotion counts,
   noise washout, working size over 5 sim-days, and — new, harness-only-visible —
   chi-band/overlap interaction (does per-entry lambda distort match_score or
   band membership?).
3. Sweep SLOW_DIV {4,12,24,48} and K {1,2,4} against real strength
   distributions; report operating window.
4. File GL-FIND-METADECAY-C1 and STOP. No prod code. wC reviews, then Stage 2.

## 5. Stage 2 — prod deploy (gated on clean Stage 1)

- Implementation per A/B/C. Entries store lam_base and reinforcement_count
  (persisted; entries lacking fields default to legacy global lambda —
  backward compatible, existing memories unaffected until touched).
- Kill switch: META_DECAY_ENABLED env var. False = every entry decays at
  global DECAY_LAMBDA exactly as today (single code branch, instant revert,
  no redeploy).
- Instrumentation: decay_channel field visible in atlas health
  (n_fast/n_slow/n_released), plus release events at dream
  (deep_release {entry, lam reverted}).
- Rollback: switch off; no schema removal needed (extra fields inert).
- Observation: same protocol as 032 — wC via bridge tools across sessions/
  dreams; the acceptance signal is a full session's learning surviving to the
  next dream and promoting in bulk, with noise washout and working size both
  holding. Joe's browser is the bar.

## 6. Failure modes to avoid

- Harness pass ≠ capability; Stage 1 success means the decay logic holds in
  real code, nothing more.
- No silent tuning: SLOW_DIV=12, K=2.0, DWELL_GATE=4 ship as specified;
  retuning only from observed prod distributions via a new brief.
- Any interaction found with match_score, chi neighborhoods, dream replay, or
  novelty override = stop and GL-FIND before proceeding.

## 7. Queue after this

GL-BRIEF-tokenization fix (input punctuation segmentation, per
GL-FIND-INPUT-TOKENIZATION-C1-20260610) — held at Joe's request until decay
work is in flight. Micro-replay / daydreaming enrichment — future, separate.

---
*wC model source: /home/claude/metaplastic/model.py (P0–P5).*
