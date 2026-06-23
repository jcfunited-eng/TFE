# GL-CMD-RANK-ORDER-OBSERVABLE-EVE-20260623-146

doc_id: GL-CMD-RANK-ORDER-OBSERVABLE-EVE-20260623-146
To: c1
From: Eve
Re: Add rank-order observable as opt-in to _unwrapped_deltas. Validate against event_count on the GL-CMD-144 curve. Do NOT replace event_count.
Date: 2026-06-23

## Context

GL-CMD-144 produced Curve A: smooth sigmoid collapse from 73% at n=100 to 17% at n=200 to 4% at n=400. Curve B: brain size doesn't help. Curve C: confident collision (64/64 unanimous-wrong) at n=200, std=0.0. Diagnosis: per-neuron binding capacity bottleneck, population votes are degenerate.

Eve's toy (GL-MDL-NEUROMORPHIC-COGNITION-EVE-20260623-145, run results in GL-RPT-NEUROMORPHIC-TOY-EVE-20260623-145) tested four mechanisms against this collapse on a phase-dominated task with the same signature (6 modalities, 64 neurons, LIF krimelacks, ring attenuation, cosine recall). Result: rank-order of first-wrap ticks alone holds 93% T5 at n=400 where event_count drops to 74%. The other three mechanisms (heterogeneous receptors, WTA, STDP precedence) do not help in this regime.

The toy does NOT reproduce production's unanimous-wrong failure mode — toy baseline degrades by losing isolated votes, not by population unanimity. This means production has homogenization that the toy doesn't capture, and rank-order may behave differently on the substrate. This dispatch finds out.

## Scope

ADD rank-order observable as OPT-IN. event_count stays default. No replacement, no canonical change. Same caution pattern as GL-CMD-140 Decision 1.

Code surface: dsf_ai_service/loom_model/neuron.py _unwrapped_deltas. Add a sibling method or a mode parameter. Mechanism selection via env var COGNITION_OBSERVABLE in {"event_count" (default), "rank_order"}, OR via LoomBrain(..., observable="rank_order") constructor opt-in (Eve's preference: constructor opt-in matches the heterogeneous_primary_modality pattern from -140; env var as fallback if construction-time is impractical). Your call on the plumbing — pick whichever lets the sweep harness and brain.recall switch together by construction (the GL-CMD-140 V1.b property).

The rank-order observable: for each modality m, record first_wrap_tick during this feed (extract from krim.events whose timestamps are >= the pre-feed tick). After all modalities are fed, sort modalities by first_wrap_tick ascending. Return deltas[m] = (N_MODALITIES - rank) for fired modalities, 0 for modalities that did not wrap.

## What to validate

A. Capacity curve, rank-order observable: n in {25, 50, 75, 100, 125, 150, 175, 200, 250, 300, 400}, seed_size=8, 3 seeds. Report T5 clean-full-cue mean and std at each n.

B. Side-by-side with event_count from GL-CMD-144 Curve A. Same axes. Plain-language read of curve shape: gradual / cliff / bistable / flat.

C. Per-neuron distribution at n=200, 5 sample concepts, both observables. Direct comparison against Curve C. We need to know: under rank-order, does the population at n=200 still show unanimous-wrong (confident collision survives)? Show disagreement (population scatters)? Or show correct recall?

D. Production-vs-harness parity check (same pattern as GL-CMD-140 V3.c): production brain.recall with rank-order observable vs sweep-harness implementation of rank-order, at n=25/50/100. Bar: 0.0pp at every point, +/-3pp tolerance. If divergence, find it before going further.

E. Test_cognition_path: run the existing 12-test suite under rank-order. Report which tests pass, which fail, which behave differently than under event_count. The two pre-existing failures (T7 3-sensory, T8 noise) may go up or down or stay; report which.

## Verification

V1 — audit before code:
  V1.a: Confirm krim.events entries carry a tick t field that uniquely identifies the substrate tick of each wrap. Show one event payload from a real krimelack as proof. If absent, STOP and surface — rank-order needs this and we'd be opening krimelack internals.
  V1.b: Confirm krim.n_events (the GL-CMD-138 monotonic counter) provides the right "before"/"after" delta to extract THIS feed's new events from the events deque. The existing event_count path proves this works; just verify it still applies.
  V1.c: Confirm both production brain.recall and sweep harness can be switched together by construction OR by env var. The GL-CMD-140 V1.b property (single switch, asymmetry impossible) must be preserved.

V2 — implementation: One file (or minimal set). No edits to krimelack internals, no edits to signal_attenuation, no edits to brain.py topology. Opt-in only. Default behavior unchanged.

V3 — PASS criteria:
  V3.a: Core regression 38/38 under DEFAULT (event_count). The opt-in must not break default. If any of the 38 fail under default, STOP.
  V3.b: Capacity curve A produced for rank-order, 11 n-points x 3 seeds, all reported.
  V3.c: Side-by-side curve B produced (rank-order vs event_count).
  V3.d: Per-neuron distribution at n=200 captured for both observables, 5 concepts.
  V3.e: Parity check D: 0.0pp at n=25/50/100 between production and harness under rank-order.
  V3.f: test_cognition_path run under rank-order, results table reported.
  V3.g: Runtime <= 4h. If exceeded, halt and surface partial.

V4 — STOP conditions (surface, do not proceed):
  V4.a: krim.events lacks tick t field (V1.a fail). Architectural decision required.
  V4.b: Rank-order regresses below event_count at any n. Surface the n and the gap; do not advance further n-points.
  V4.c: Rank-order >= 95% at n=400 with std=0.0. Suspicious. Pull per-neuron distribution at n=400 too and surface; this would be the toy's pattern reproducing exactly, which we should not assume without verification.
  V4.d: Production-vs-harness parity > 0.5pp under rank-order. Find the divergence before any other work.
  V4.e: "That can't be right" result. Surface, do not self-clear (GL-CMD-140 V5 STOP precedent).

V5 — report contents:
  - Capacity curve table: n x {event_count, rank_order} x {mean, std}.
  - Per-neuron distribution table at n=200, 5 concepts, both observables. Columns matching Curve C of -144: winner, win_votes, correct_votes, unique_preds.
  - Parity check: 3-row table, both observables.
  - test_cognition_path delta table: which tests changed pass/fail status.
  - Plain-language reads: (1) does rank-order delay the cliff, eliminate it, or move it elsewhere; (2) does rank-order change the failure mode from unanimous-wrong to something else; (3) does rank-order maintain the production-harness parity property -140 established.
  - No recommendation on making rank-order default. That decision belongs to Joe based on what the table shows.

## What this dispatch does NOT do

- Does NOT replace event_count as default. Opt-in only.
- Does NOT bundle T7/T8 fixes (noise + partial-modality). Separate dispatch later.
- Does NOT fix test_t5 non-perturbing perturbation. Still its own small dispatch.
- Does NOT touch heterogeneous primary modality (currently reverted-to-language per -140). Stay reverted.
- Does NOT add WTA at recall layer. Toy proved it hurts in this regime.
- Does NOT add STDP-class precedence. Toy proved it's approximately neutral.
- Does NOT modify krimelack internals. Read-only on krim.events and krim.n_events.

— Eve, 2026-06-23
