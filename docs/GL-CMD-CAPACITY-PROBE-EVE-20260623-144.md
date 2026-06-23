# GL-CMD-CAPACITY-PROBE-EVE-20260623-144

doc_id: GL-CMD-CAPACITY-PROBE-EVE-20260623-144
To: c1
From: Eve
Re: Measure the n=200 cliff. No fixes. No production-path edits.
Date: 2026-06-23

## Context

GL-CMD-140 landed clean at 1f4dd46: production parity at 0.0pp; scaling reproduces harness curve 75% to 16% from n=100 to n=200. The cliff is real and now visible in production. Before any fix attempt, we need to know what shape it is. Past Eve diagnosed before measuring four times in a row this month. We measure first.

## Scope

PROBE ONLY. No edits to _unwrapped_deltas, signal_attenuation, brain.py, neuron.py, sensory paths, or test_cognition_path.py. The two T7/T8 failures from -140 stay red; they belong to a later dispatch. The test_t5 non-perturbing-perturbation defect is a separate small dispatch — do not bundle. All work in tests/ or a fresh probe script.

## What to measure

A. Capacity curve. Fixed seed_size=8 (production default). Sweep n in {25, 50, 75, 100, 125, 150, 175, 200, 250, 300, 400}. Report T5 clean-full-cue at each n. We need to distinguish: gradual (monotonic descent), cliff (stable then sudden), or bistable (large seed-to-seed variance).

B. Brain size sensitivity. Fixed n=100. Sweep seed_size in {4, 8, 16, 32, 64}. Memory verified safe to 128 neurons (280 MB) per GL-CMD-138; seed_size=64 = 512 neurons total. If RSS approaches 1 GB on any arm, halt that arm and surface.

C. Per-neuron distribution at the cliff. At n=200, pull the same per-neuron vote distribution you pulled for the V5 STOP on -140, for at least 5 query concepts. We need to know whether cliff = population disagreement (each neuron picks a different wrong answer) or population collapse (all 64 unanimously wrong on the same concept). They imply different root causes.

D. Repeatability. Each (n, seed_size) point run with 3 brain_seeds. Report mean and std.

## Verification

V1 — audit before code:
  V1.a: Determine whether the -136 sweep harness can be reused, OR whether it monkeypatches _unwrapped_deltas in a way that would diverge from the now-real production path. If it monkeypatches, do NOT use it — write fresh probe code that calls brain.recall directly. Report which path.
  V1.b: Confirm memory ceiling instrumentation present before seed_size=64 runs.

V2 — implementation: Single probe script (tests/probe_141_capacity.py or similar). No production edits. No test_cognition_path edits.

V3 — PASS criteria:
  V3.a: Curve A — all 11 n-points x 3 seeds reported, no OOM.
  V3.b: Curve B — all 5 seed_size points x 3 seeds reported, no OOM.
  V3.c: Per-neuron distribution at n=200 captured for at least 5 concepts.
  V3.d: Total runtime <= 4 hours wall clock. If exceeded, halt and surface partial results.

V4 — STOP conditions (surface, do not proceed):
  V4.a: RSS > 1 GB at any sweep point.
  V4.b: -136 harness diverges from production. Report divergence shape before any other work.
  V4.c: Production brain.recall errors / NaN / non-terminates at any sweep point.
  V4.d: A curve produces a result so unexpected your first instinct is "that can't be right" — surface, do not self-clear.

V5 — report contents:
  Three tables: capacity-curve, seed-size-curve, per-neuron-distribution-at-200.
  Plain-language read of curve shape: gradual / cliff / bistable.
  Plain-language read of per-neuron distribution: disagreement / collapse / other.
  Whether seed_size scaling pushes the cliff at all.
  No fix recommendations. Diagnosis pass is a separate dispatch after we read these numbers.

## What this dispatch does NOT do

- Does not fix noise brittleness (T8). Later dispatch.
- Does not fix partial-modality brittleness (T7). Later dispatch.
- Does not fix test_t5's non-perturbing perturbation. Separate small dispatch.
- Does not touch folding-during-experience (item 7 blockers). That's -146 / -147.
- Does not modify production. At all.

— Eve, 2026-06-23
