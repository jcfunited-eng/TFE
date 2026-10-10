# Guala speech V7 causal-impact contract

Date: 2026-09-01  
Authority: repair attempt 43 evidence through commit `d44b2325`  
Production baseline: task 1408, image digest
`sha256:102b44cdc91276fcf4bbae5e0436ed15ac5128808ac606f3eba58cce89f57e1a`  
Production mutation authorized by this document: **no**

## Mandatory architecture-honesty gate

1. **Requested architecture:** one bounded deterministic body-owned voice
   source. Applied motor work must create finite respiratory pressure; the
   nonlinear folds and the organism's existing tract must create pressure;
   exact emitted pressure must return through ordinary hearing. There is no
   prescribed waveform, renderer voice, phoneme table, meaning, ML, timer,
   exclusive speech lock, or simulated human mouth.
2. **Current code reality:** task 1408 has the exact hearing/self-hearing
   transport and a real eight-section tract, but its source is a struck
   transient. Production consequently emits pings, pops, and buzzes rather
   than a continuing voiced pressure source.
3. **Conflict with requested architecture:** yes. The current source converts
   a one-shot displacement into tube ringing and cannot sustain phonation.
4. **Mechanisms and files that will not be extended:** the struck three-surface
   source, hard-overwritten `impedance * delta-flow` tube entrance, passive
   lung-volume-as-work law, phase/countdown predecessors, Rayleigh/ringing
   candidates, arbitrary active windows, and the rejected dirty candidate in
   `virtual_articulated_body.rs`, `virtual_articulatory_body.rs`, and
   `organism_runtime.rs` will not be extended or packaged.
5. **Single exact next item:** replace the rejected source boundary in a clean
   worktree with the copied-body-proven finite pressure-flow work law, then run
   its complete local and copied-body falsification suite before packaging.
6. **Full field or reduced approximation:** no DSF field is evaluated or
   changed by this mechanism. L0--L4 and every explicit DSF field remain
   byte-identical and outside the edit boundary.
7. **Lost field structure:** none.

## Evidence-selected physical law

The candidate is fixed by the copied-body reports; implementation may not
retune it.

- sample rate: 16,000 Hz;
- lower/upper fold mass: 4,096 / 2,048;
- lower/upper damping: 16 / 16;
- lower/upper stiffness: 64 / 64;
- inter-fold coupling stiffness: 128;
- vertical rest-area gradient: 8 square-millimetre quanta;
- pressure-force divisor: 1;
- source/line impedance: 16 pressure quanta per flow quantum;
- tract: the resident eight body-owned area axes, unchanged;
- wall loss and mouth load: the existing deterministic tube laws, unchanged;
- selected motor-work rule: one applied glottal displacement carrier loads
  one `full_head * full_flow` work quantum for one 16-kHz sample;
- capacity: at most the 380-carrier glottal anatomical span times that work
  quantum; it fits a nonnegative i32;
- pressure fraction: `(400 - glottal_position) / 380`, multiplied by actual
  finite lung matter above its minimum;
- work debit: actual subglottal pressure head times actual outward flow;
- matter debit: actual outward flow only;
- antagonist unloading: applied motion toward maximum removes the matching
  work capacity; position 400 admits zero capacity and zero source pressure.

Stalled motor carriers load no work. Repeated drive at an anatomical stop
therefore cannot mint energy. Non-glottal motors load no work. A closed glottis
cannot radiate a voice; a maximum-open glottis has zero pressure recruitment.

## Simultaneous nonlinear source boundary

At the glottal end of the pressure-wave tract:

```text
p = p+ + p-
u = (p+ - p-) / Z
p = 2*p- + Z*u
p+ = p- + Z*u
```

The nonlinear two-area valve flow `u = F(subglottal_head - p, A_lower,
A_upper)` is monotone in candidate nonnegative integer flow. Each sample uses
a bounded bisection over `0..full_flow`, followed by a fixed six-point local
minimum check, to choose the closest representable integer junction. With the
declared anatomy, `full_flow` is 219 microlitres/sample, so the search bound is
fixed and independent of organism age, history, memory, world size, or input.

The outgoing wave is committed once after that solve. Current flow enters the
tract. The observed lip pressure is the difference of successive transmitted
lip pressures, the deterministic radiation boundary. The renderer receives
only those exact samples and may scale speaker playback; it may not synthesize,
smooth, pitch-correct, formant-correct, or label them.

Primary source-filter work requires glottal flow, tissue motion, and
supraglottal pressure to be solved as a coupled system rather than a one-way
source. The selected boundary is consistent with that physical requirement;
the copied-body range, not the citation, is its admission authority.

## Persistent state and exact migration

V7 keeps the body at 283 bytes. Its 88 acoustic bytes are exactly:

```text
right traveling pressure     8 x i32
left traveling pressure      8 x i32
lower/upper fold current      2 x i32
lower/upper fold previous     2 x i32
respiratory work remaining    1 x i32 (nonnegative)
previous transmitted lip p    1 x i32
```

No axis is added. No neuron, receptor ordinal, motor terminal, tract area,
lung field, or proprioceptive field moves.

The immutable tick-358454 copied body has identity
`1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1` and organism hash
`8dbd3974ce19779d33984f61ec546b25ac0d3cf6164a88350db14ce2f6f6a100`.
Reconstruction from all 45 published axes, lung 2,000,000, initialized
proprioception, and 88 zero acoustic bytes exactly reproduced its V6 body hash
`ecba74988b4a129958b243abca214b0ccddc07400bb314a9ff86b205c183344e`.

The V7 rest encoding changes only byte offset 9, the version's low byte. The
other 282 bytes are identical and produce V7 body hash
`6be379848fe6de43de3fddbfa5542d7494faf4b51d94fec36df7c476a2e089e5`.
Decode must validate V6 completely, consume its proven-rest acoustic values,
and construct V7 rest. A V6 body with any nonzero acoustic slot is refused;
it is not reinterpreted under the new law.

Mid-gesture V7 checkpoints preserve folds, work, tube, and prior lip pressure.
A cold restart must continue the same pressure consequence, not replay onset
and not reset to silence. This requires an explicit save/restart/continue
falsifier on a copied body before packaging.

## Runtime and self-hearing impact

The existing causal chain remains authoritative:

```text
native motor carriers
 -> typed glottal antagonist consequence
 -> body position plus bounded respiratory work
 -> coupled folds/flow/tract settlement
 -> exact signed-16 radiated pressure
 -> bounded InFlightAcousticConsequence
 -> byte-matched cochlear/body intake
 -> ordinary native sensory settlement
 -> one persisted successor
```

`InFlightAcousticConsequence` already refuses more than 480,000 samples,
requires four body trajectories of identical length, persists current-only,
matches the exact transported bytes before hearing, consumes prefixes, and
superposes overlapping physical pressures with checked signed-16 addition.
The speech repair does not add another queue, cache, history, owner, retry,
callback, or Python cognition path.

The existing `PendingCandidateExists` guard protects atomic predecessor /
successor ownership across every modality. It is not a speech lock and is not
expanded. Camera, microphone, world pressure, proprioception, and self-hearing
must continue to enter coexisting intervals; no lesson or voice-specific mutex
may serialize them.

## Resource impact and runaway exclusions

- Persistent body bytes: unchanged at 283.
- New variable-length resident state: zero.
- Acoustic arrays: two fixed eight-i32 arrays and six fixed i32 scalars.
- Per-sample source solve: bounded by the fixed 219-flow search domain.
- Output allocation: the existing exact interval-length pressure vector plus
  four equal body trajectories; no append beyond the admitted interval.
- In-flight encoded maximum: `12 + 480000 * 5 * 2 = 4,800,012` bytes.
- Overlap: replace-only prefix consumption and checked same-index
  superposition; never concatenated unconsumed history.
- Storage growth: body width unchanged; current-only in-flight consequence is
  bounded by the same 4,800,012-byte ceiling and disappears at exact rest.
- Observation: projections read committed state and do not advance, pause,
  lock, or retain organism data.
- Failure: arithmetic width, invalid migration, source substitution, sample
  overflow, or signed-pressure overflow aborts the candidate transition before
  successor commit. No catch-and-continue path is admissible.

The copied-body range executed 840 finite-work trajectories. All 840 reached
exact rest. No report or harness mutated production. AWS checks remained task
1408, 1/1/0, alarm OK, unchanged image, and memory below 4.87 percent.

## Exact source edit boundary

Only these source responsibilities are admitted:

1. `native/guala_core/src/virtual_articulated_body.rs`
   - replace V6 acoustic scalar semantics with the declared V7 layout;
   - add strict V6-rest-to-V7-rest decoding;
   - keep 45 axes and 283-byte width unchanged;
   - validate work nonnegative and no greater than posture capacity.
2. `native/guala_core/src/virtual_articulatory_body.rs`
   - replace the rejected struck source in full with the selected two-fold,
     finite-work, simultaneous-boundary law;
   - retain the existing tube, tract-area derivation, output/body trajectory
     interface, and signed-width refusal;
   - load/unload work only from applied glottal displacement consequences.
3. `native/guala_core/src/organism_runtime.rs`
   - no production logic change is expected;
   - only compile-contract or falsifier updates are permitted if the body state
     type changes require them;
   - in-flight ownership, superposition, persistence, and self-hearing are not
     to be redesigned.

Python transport, observation UI, renderer, curriculum, world, L0--L4, DSF,
neuron physics, learned sensory state, and production deployment files are
outside the implementation edit boundary.

## Required falsifiers before packaging

The implementation is rejected unless one test command proves all of the
following on the exact copied body and records every point:

- selected constants reproduce the harness waveform/state law exactly;
- near-minimum lung: zero admitted voice;
- neutral and full lungs: broad intermediate-posture voice across all seven
  declared outlets;
- glottis 20 and 400: zero admitted voice;
- jaw/lip/tract changes alter pressure without renderer shaping;
- a non-glottal motor cannot load respiratory work or start voice;
- stalled glottal carriers cannot load work;
- antagonist opening unloads work and returns exact rest;
- natural work exhaustion returns exact rest;
- pressure severing returns exact rest;
- 6--8 kHz energy guard rejects the old numerical mode;
- cold save/restart during a gesture continues the exact successor;
- exact emitted bytes enter ordinary self-hearing and are consumed once;
- simultaneous camera/mic/world/self-hearing sources remain coexisting;
- repeated gesture soak leaves resident bytes, RSS slope, saved bytes, in-flight
  sample count, and beat time bounded;
- pre/post copied-body files are byte-exact except the deliberately committed
  successor under test;
- AWS task, rollout, alarm, image, CPU, and memory snapshots bracket every run.

Recognizable humanlike vowel/consonant audio, learned articulation, a first
word, or conversation are later gates. A periodic source is necessary but is
not to be reported as any of them.

## Deployment and rollback boundary

Task 1408 cannot decode a V7 body. Therefore rollback may never point task
1408 at a V7 `CURRENT`. Immediately before cutover, the deploy pipeline must
capture and hash an immutable current V6 body generation. If V7 live proof
fails after a V7 save, rollback consists of both operations as one controlled
recovery: restore that exact V6 `CURRENT`, then restore task 1408. Starting the
old image first is prohibited.

The first live gesture is admitted only after copied-body implementation,
restart, self-hearing, resource soak, and rollback rehearsal all pass. The
first live result must be heard and classified by Joe. Pings, buzzes, pops,
carrier tones, or non-human squeals are failure even if internal physics and
self-hearing pass.

## Evidence hashes

- coupled-boundary harness/report:
  `0ce7a2d3d47bd1c3d05649df08fc5a92b2da9205d17eebdb8053c21c092df506` /
  `1966b9b81570280fd99fc3f00f146ff48e489f3a1da239f4dd1fc24730797d66`
- steady unlimited ceiling harness/report:
  `e0a2e60c4a694f50879abbce4e374351db28fcf4caa7f727133fa7583161de0f` /
  `1aa5a31db12c0423ce5f5e8df31a5310e5b162a81a215d5e9041fbff576a4d7a`
- finite-work corrected harness/report:
  `803ce56d00bc7ed43375e3046b18b170a2e351689610e1cb78a2ece331c1926b` /
  `1b08c32f5a38ad199503bb55be7f8da1790926697da8c87f9639f5c22a056f80`
- migration harness/report:
  `ca9415304faaacc3f43750e101cb73b9c98f58e2db7444bbe6787f405307d838` /
  `a18a6ac621dbe15c07c5c738c5f83080f38ab5ffd3a16245d5d0d3616c12f8e2`
- immutable copied-body source report:
  `9a0bb83bd74bbe27f94bb50733f619047c2be8ebb31a75553a54c4723233f9f8`

## Gate verdict

The causal-impact analysis and exact copied-production-body rest-migration
proof are complete for source implementation. They do **not** authorize
packaging, deployment, a voice claim, a phoneme claim, or a conversation
claim. Implementation begins only from a clean source worktree at this
contract commit; the rejected dirty investigation files remain quarantined.
