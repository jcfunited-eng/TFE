> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF-C1-20260704-v2

doc_id: GL-HANDOFF-C1-20260704-v2
From: c1a | To: Eve, Joe, next-session-c1a
Session-end handoff. Two dispatches fully executed and filed this
session; nothing left mid-flight. Read this + memory before doing
anything new.

---

## What shipped this session (both filed and pushed to origin/guala-live)

**1. GL-CMD-SENSE-REPAIR** → `docs/GL-RPT-SENSE-REPAIR-C1-20260704-v1.md`
(commit `f6071f6`). Fixed three real bugs in the `event_count` observable
(`n_events` always 0 on three sensory adapters; unbounded event lists;
`recall()` not actually read-only) plus repaired a stale harness. Fresh
T5 went 4% → 72–95%. All four gates independently re-verified by a
5-agent adversarial workflow (not self-graded). Answered the follow-up
"too-good" check honestly: the 95% cell has 92% unanimity / only 8
distinct voter clusters — real but thin disagreement, not a hash.

**2. GL-CMD-C2-WHOLE-BRAIN-168-v3** → `docs/GL-RPT-GROWTH-CHART-C1-
20260704-v1.md` (commit `e9963ec`). Booted `Embryo` (committed 8-
hemisphere organism) on the real 30-sentence Peter Rabbit corpus, 3
compressed days + sleep/replay, all 15 `-103` mechanism gauges read off
ONE running organism. 11 measured, 4 honestly ABSENT (composition,
imagination, reflection, theory-of-mind). Ported `dsf_ai_service/
curriculum/sensory_catalog.py` + `catalog_atlas_reader.py` from the codex
branch (never merged before — this also unblocked `test_folding_engaged.py`,
which had been silently uncollectable). Added a backward-compatible
`observable` arg to `Embryo`.

Both: **model work only, zero live-path changes** — verified each time
(diff scope + independent review for #1; my own G-4 check for #2).
**Nothing was deployed.** No ECS task changed, no deploy script ran, the
`Embryo` instance raised in #2 was in-memory only and no longer exists —
confirmed explicitly to Joe mid-session.

---

## Open threads — NOT decided by me, need Eve/Joe's ruling

1. **Language-dimension saturation** (sense-repair report, Failure 2):
   `LanguageKrimelack` has no `n_events` of its own, falls back to
   `len(deque)`, saturates within ~4 taught words. Real, separate bug,
   NOT fixed — out of that dispatch's named scope (3 sensory adapters
   only).
2. **Embryo's pre-existing chemical-DNA RNG** (growth-chart report,
   Failure 9): `_seed_dna_diversity()` seeds kappa/threshold/aff_gain/
   polarity from `np.random.default_rng(1000+neuron_index)` — deterministic
   per neuron index, used for metabolic differentiation, not population-
   vote diversity. Flagged whether this falls under the neuron-identity
   STOP. Not touched, not decided.
3. **Folding discrepancy** (growth-chart report, Failure 1): the standard
   `LoomBrain`/`L6_TCL` n_eff folding stayed correctly blocked (flat 7.0,
   exactly as -168-v3's A5 predicted) — but `Embryo`'s OWN separate
   `_charge_and_fold` q-mechanism fired anyway, 64→120 neurons. This
   partially contradicts a literal reading of A5's "grows within seed
   capacity" text. Needs Eve/Joe to reconcile which folding pathway A5
   was actually describing.
4. **Sequence gauge (#9) is degenerate** — 100%/8-8-unanimous, confirmed
   via per-neuron check to be a collision-free-sentence artifact, not real
   population learning. A harder test sentence (real word repetition) is
   the obvious next step, not built.
5. **`test_folding_engaged.py` — only 3 of 10 tests actually run** (t1,
   t2, t8; the rest timed out at 280s in my one attempt and weren't
   retried). t1/t2 pass, t8 fails for the same pre-existing, unrelated
   `loom_model/__init__.py` partial-import reason already documented.
   t3–t7, t9, t10 are **unverified**, not assumed passing.
6. **Growth chart's own next steps**, per the CMD's own text ("Joe's
   part: none until the first growth chart"): the natural next dispatch
   is Eve/Joe reviewing the chart and issuing whatever comes next
   (ratify, redirect, or a -168-v4). Not mine to presume or start early.

---

## Repo state at handoff

Branch `guala-live`, my last pushed commit `e9963ec`. Note: `git log`
shows two concurrent commits from another session landed between my
Step-0 push and my final push (`0a6dc14` sleep-calibration,
`d813c32` — unrelated thread, not mine, not reviewed by me). Normal for
this shared repo; just be aware before assuming `HEAD` is only my work.

Standing rules unchanged, all in memory — Step-0-before-implementing,
FILED-means-pushed, no RNG in neuron identity, exp(1j·Δ) prohibited,
>95% anywhere triggers the too-good protocol, failures-first reporting.
Nothing in this session weakened or reinterpreted any of those.
