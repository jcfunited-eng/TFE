# Guala native continuous-interval latency sprint — 2026-08-11

Release preflight began at `2026-08-11T11:53:14Z`. The first cutover reached
production as task definition `dsf-ai-task:964`, but live latency failed the
acceptance threshold. The bounded correction and its second cutover are recorded
below.

## Architecture honesty gate

1. **Requested architecture:** the living organism must continuously settle its
   exact sensory and internal physics fast enough that declared organism time
   does not fall minutes behind elapsed time.
2. **Current code reality:** production task 963 lawfully mounts and reuses one
   layer-10 cell from changed layer-7/layer-8 material, but one 250 ms body turn
   and one eight-hop unattended interval each take minutes to publish.
3. **Conflict:** yes. The physical result is correct, but the runtime cannot yet
   sustain its declared continuous interval.
4. **Not extended:** Python cognition, reduced DSF, skipped physical ticks,
   cached successor answers, semantic controllers, dense population polling,
   ownership, locks, database cognition, or heuristic time compression.
5. **Single next item:** remove repeated native transition-boundary work while
   preserving the byte-exact successor produced by the same ordered physical
   ticks.
6. **DSF evaluation:** unchanged full joint L0-L4 delivery.
7. **Field loss:** none.

## Change-impact ledger

| Required fact | Exact sprint authority |
|---|---|
| Input | Production CURRENT plus the exact 250 one-millisecond signed yaw steps, followed by the existing admitted whole-sensorium hops. |
| Function/file boundary | `exact_native_yaw_trajectory` and `NativeResidentOrganism` preparation in `dsf_ai_service/glew_runtime/native_resident_organism.py`; resident/cognitive prepare and commit paths in `native/guala_core/src/organism_runtime.rs`, `native/guala_core/src/resident_d3_runtime.rs`, and `native/guala_core/src/resident_cognitive_formation.rs`. |
| State transformation | The same ordered physical transitions and full DSF deliveries produce the same final native organism bytes; only redundant cloning, encoding, or Python/native boundary work between ticks may be removed. |
| Expected output | Identical successor SHA-256, tick, neuron counts, retained fractals, contacts, energy, and observations for the reference path and corrected path. |
| Production acceptance | One live quarter-turn returns before the public gateway timeout; its reverse reuses layer 10 without growth; unattended time publishes a later interval; identity and Python-callback count remain unchanged; state/storage remain bounded. |
| Observed evidence | Exact production body `8b5c9de7…09a8`: deployed per-tick path required 99.913 s for the exact 250-tick quarter turn. The one-seal native trajectory required 24.442 s. Both produced byte-identical successor `24a8c6f2…a4b`, tick 33056, 25,159,319 bytes, 500 full DSF deliveries, 8,252 physical neuron transitions, and 466 retained neuronal fractals. Task `964` then returned a live 0→90° turn in 65.866 s and the exact reverse in 80.846 s, so that release failed latency acceptance while preserving physical behavior. Trace showed preparation—not final sealing—dominated: 24.476 s prepare, 0.004 s commit, 0.014 s encode/save locally. The bounded correction concurrently settles only physically independent cohorts and post-contact neurons, then merges evidence in original cohort/neuron order; shared contact transfer and shared-fluid recovery remain single, ordered authorities. It reproduces exact successor `24a8c6f2…a4b`, 500 DSF deliveries, 8,252 transitions, and 466 fractals in 12.064 s locally. The full native suite passes. Corrected production deployment remains pending. |

## Failed hypotheses

- **Python/native call crossings were the primary cost:** false. One production
  tick took about 0.432 s and the Python crossing was a small portion. Native
  cloning and full-state sealing dominated.
- **The historical one-way correction was the whole cost:** false. Avoiding its
  no-op deep copy reduced one tick only to about 0.390 s.
- **Caching one successor encoding was sufficient:** false. Removing the second
  encoding and redundant full predecessor reduced one tick to about 0.251 s,
  but a 250-tick turn still projected beyond the gateway interval.
- **Fewer physical ticks were required:** rejected. The accepted correction
  retains all 250 ordered one-millisecond transitions and seals only the final
  externally publishable organism state.
- **Persistence or final state sealing dominated the remaining 24.4 seconds:**
  false. Direct measurement assigned 24.476 seconds to physical preparation and
  only 0.018 seconds to commit plus final encoding/save.
- **Inactive electrical frontier work could simply be skipped:** false. Across
  the 250-tick specimen, 50,412 of 50,500 reached edges carried a gradient and
  50,418 carried a phase difference. The correction therefore preserves every
  reached edge and instead evaluates independent local consequences concurrently.
- **Formatter check commands:** `python -m black --check` and `ruff format
  --check` were unavailable in the container. Python compilation and
  `git diff --check` pass; touched Python was manually kept in project style.
