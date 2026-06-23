# GL-RPT-CAPACITY-PROBE-C1-V5-20260623-144

doc_id: GL-RPT-CAPACITY-PROBE-C1-V5-20260623-144
To: Eve (via Joe)
From: c1
Re: V5 — capacity cliff measurement (GL-CMD-144). Probe only, no fixes.
Date: 2026-06-23

**Headline: the "cliff" is a GRADUAL S-curve, not a sudden drop. Brain size does NOT
move it (flat ~73% at n=100 from 32→512 neurons). At n=200 the failure mode is
population COLLAPSE onto a wrong consensus — correct concept gets ZERO votes — not
population disagreement. Every point has std=0.0 across 3 brain seeds (surfaced below).**

No production edits. No test_cognition_path edits. Fresh probe
(`dsf_ai_service/loom_model/tests/probe_144_capacity.py`) calling production
`brain.recall` directly. Runtime 173.9 min (< 4h budget). Peak RSS 1006 MB.

---

## V1 audit

- **V1.a:** Both `sweep_136_buffer_probe.py` and `sweep_137_scaling_probe.py`
  **monkeypatch** `LoomNeuron._unwrapped_deltas` with `_patched_event_count`. Per
  dispatch, did NOT use them — wrote fresh probe calling `brain.recall` (production
  path). No behavioral divergence exists post-140 (the monkeypatch and production are
  the same mechanism; GL-CMD-140 proved 0.0pp parity), so **no V4.b STOP** — but the
  probe uses the real path regardless.
- **V1.b:** RSS instrumented via `resource.getrusage(RUSAGE_SELF).ru_maxrss`, 1 GB halt
  guard checked after every sweep point (incl. before/after each seed_size=64 run).

## Curve A — capacity (seed_size=8, clean full-cue T5, 3 brain seeds)

| n | mean T5 | std | per-seed |
|---|---|---|---|
| 25 | 100.0% | 0.0 | 100/100/100 |
| 50 | 98.0% | 0.0 | 98/98/98 |
| 75 | 88.0% | 0.0 | 88/88/88 |
| 100 | 73.0% | 0.0 | 73/73/73 |
| 125 | 48.0% | 0.0 | 48/48/48 |
| 150 | 29.3% | 0.0 | 29.3×3 |
| 175 | 22.3% | 0.0 | 22.3×3 |
| 200 | 17.0% | 0.0 | 17/17/17 |
| 250 | 8.8% | 0.0 | 8.8×3 |
| 300 | 6.0% | 0.0 | 6/6/6 |
| 400 | 4.0% | 0.0 | 4/4/4 |

## Curve B — brain size (n=100, clean full-cue T5, 3 brain seeds)

| seed_size | neurons | mean T5 | std | peak RSS |
|---|---|---|---|---|
| 4 | 32 | 71.0% | 0.0 | 255 MB |
| 8 | 64 | 73.0% | 0.0 | 255 MB |
| 16 | 128 | 74.0% | 0.0 | 279 MB |
| 32 | 256 | 73.0% | 0.0 | 521 MB |
| 64 | 512 | 74.0% | 0.0 | 1006 MB |

## Curve C — per-neuron vote distribution at n=200 (seed=42, 64 neurons)

| concept | winner | win votes | correct votes | unique preds | top3 |
|---|---|---|---|---|---|
| beacon | signal | 48/64 | **0** | 2 | signal:48, pomelo:16 |
| golden | mintheron | 40/64 | **0** | 2 | mintheron:40, sage:24 |
| river | pepperalmond | 24/64 | **0** | 3 | pepperalmond:24, prairiewindow:24, thymeclover:16 |
| feather | copperharvest | 32/64 | **0** | 3 | copperharvest:32, echosaffron:24, atticbirch:8 |
| saffron | birchbreeze | 64/64 | **0** | 1 | birchbreeze:64 |

## Plain-language reads (no fixes — that's a later dispatch)

**Curve shape: GRADUAL, not a cliff.** Smooth monotonic descent
100→98→88→73→48→29→22→17→9→6→4. It's an S-curve: shallow to n=50, steepest across
n=100→150 (73%→29%, the inflection), then a long tail to ~chance by n=400. The
"75%→16% cliff" we named at n=100→200 in -140 is really the steep middle of this
sigmoid. **Not bistable** (std=0.0 everywhere). The usable-capacity knee at seed_size=8
sits around **n=75–100** (88–73%); by n=125 it's already below 50%.

**Brain size does NOT push the cliff.** At n=100, T5 is flat at 71–74% from 32 neurons
to 512 neurons — a 16× population increase buys ~3pp, inside noise. **The bottleneck is
per-neuron binding/encoding capacity, not population size.** Adding neurons does not add
capacity. (Memory does scale: seed_size=64/512-neurons peaked at 1006 MB — 18 MB under
the 1 GB ceiling. Anything larger needs the ceiling raised / heavier instrumentation
before running.)

**Per-neuron distribution at n=200: COLLAPSE, not disagreement.** For all 5 concepts the
population *agrees* (unique preds 1–3) on a *wrong* winner, and **correct_votes = 0** —
not a single neuron of 64 votes for the right concept. saffron is the extreme: 64/64
unanimous on `birchbreeze`. This is not neurons scattering to different wrong guesses
(that would be disagreement / vote-splitting). It's the encoding making distinct concepts
*collide*: the query for one concept maps onto a wrong neighbor's binding more strongly
than its own, consistently across the whole population. The correct binding isn't merely
out-voted — it's not competitive at all.

## V4.d — surfacing, not self-clearing: std = 0.0 at EVERY point

Across 3 brain seeds (42/43/44), every point in Curves A and B has **exactly zero
variance**. Recall T5 is fully deterministic w.r.t. brain wiring seed. Likely mechanism:
the recall pass is per-neuron and non-coupled (no cross-hemi spikes), and ring-position
attenuation is positional (0..N-1, fixed by seed_size), not seed-randomized — so
brain_seed only varies cross-hemi coupling, which recall never exercises. That would make
the corpus+encoding the sole determinant. I'm flagging this rather than asserting it
resolved: it means **brain wiring contributes nothing to recall outcomes**, which is
itself worth a look — it implies the population vote is not adding wiring-diversity
robustness. Surfaced per V4.d; not a fix, not self-cleared.

## V3 / V4 status

- V3.a Curve A: 11 n-points × 3 seeds, no OOM ✅
- V3.b Curve B: 5 seed_size × 3 seeds, no OOM ✅ (peak 1006 MB, under ceiling)
- V3.c distribution at n=200: 5 concepts ✅
- V3.d runtime 173.9 min < 4h ✅
- V4.a RSS>1GB: not tripped (peak 1006 MB; 18 MB margin — flag for larger runs)
- V4.b harness divergence: N/A (production path used)
- V4.c errors/NaN/non-terminate: none
- V4.d "that can't be right": std=0.0 everywhere — surfaced above

No fix recommendations, per scope. Diagnosis pass is the next dispatch.

— c1, 2026-06-23
