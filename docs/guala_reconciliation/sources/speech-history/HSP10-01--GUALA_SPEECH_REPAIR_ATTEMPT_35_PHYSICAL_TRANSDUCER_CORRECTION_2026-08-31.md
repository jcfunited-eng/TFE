# Guala speech repair attempt 35 — physical transducer correction

Status: **causal correction complete before expanded implementation; production
task 1402 untouched**

## Why attempt 34 implementation invocation 1 is rejected

Attempt 34's analysis and exact copied-production-body proof remain valid, but
its first unbuilt source invocation is rejected. It wrote three recurrence
coefficients that were selected as approximate frequencies rather than derived
from declared body mass, stiffness and damping. It also projected transducer
velocity through fields named `breath flow`. Those two facts violate the pure
physics and truthful-observation boundaries even if the code could make sound.
The invocation was stopped before build, test, package, body migration or
deployment. It supplies no passing evidence.

## Corrected causal mechanism

The minimum emitter is three independently mounted acoustic surfaces. Each
surface persists only current and preceding displacement. All three use:

- mass `m = 4096` exact mass quanta;
- viscous damping `c = 1` exact force quantum per velocity quantum; and
- stiffness `k = 64`, `256`, or `1024` exact force quanta per displacement
  quantum.

For each 16 kHz physical sample, the declared central-difference settlement is

```text
x[n+1] = trunc_toward_zero(
    ((2m - k) * x[n] - m * x[n-1]) / (m + c)
)
```

This is the integer settlement of `m*x'' + c*x' + k*x = 0`; the three
frequencies are consequences of three physical stiffness scales, not direct
oscillator coefficients. The common mass, damping and factor-four stiffness
spacing are fixed developmental anatomy. They are not fitted to a word,
speaker, corpus, tutor sample, target frequency path, or desired waveform.

One accepted layer-13 efferent carrier gives one bounded momentum quantum to
each surface. The surface velocities add as source pressure and enter the
already-resident lossy tube. Current sparse vocal-body motor action may change
the resident tube geometry. With no new efferent work, viscous loss plus exact
integer truncation reaches zero; there is no phase, duration, scheduler or
run-until-quiet owner. One source interval advances exactly its real sample
count and retains only six signed coordinates plus the already-resident tube
pressure.

The emitter does not choose meaning. Talking still requires current native
formation/contact activity to prepare typed vocal motors over multiple causal
intervals, cause distinct pressure trajectories, hear those exact bytes, and
retain useful recurrence. A fixed reflex ring is acoustic capability only.

## Energy and stability boundary

For each surface, `m > 0`, `c > 0`, and `0 < k < 4m`; therefore the undamped
central-difference poles are inside the explicit stability interval and
positive damping contracts them. Input is capped at the exact eight carriers
already admitted by the resident efferent boundary. Checked 64-bit products
and checked 32-bit coordinates refuse arithmetic overflow. Emitted pressure is
the change in persisted displacement, never an independently manufactured
amplitude. The copied-body gate must measure stored mechanical energy plus
radiated/dissipated energy against causing released work before release; this
paragraph is the falsifiable law, not evidence that the row passed.

## Truthful sensory projection

The four existing body-mechanoreceptor sites retain their meanings and learned
addresses: respiratory flow, glottal configuration, oral aperture and perioral
deformation. The synthetic transducer is not relabelled as one of them.
Respiratory flow is exactly zero for this emitter; the other three existing
body coordinates continue to report their actual resident values. The exact
emitted pressure still reaches both ordinary cochleae and the participant
speaker. This slice exposes transducer peak surface velocity as a separately
named observation value; it does not inject a new sensory receptor or alter
learned sensory state. Direct transducer proprioception is therefore absent in
this minimum body. Self-hearing remains the cognition-relevant feedback.

## Revised exact impact surface

The following production files may change, and no others, before another
impact amendment:

1. `native/guala_core/src/virtual_articulated_body.rs` — V6 retirement of the
   invalid phase/countdown and persistence of six surface coordinates.
2. `native/guala_core/src/virtual_articulatory_body.rs` — declared physical
   surface settlement and pressure coupling.
3. `native/guala_core/src/organism_runtime.rs` — truthfully named native
   projection only; in-flight custody and hearing law remain unchanged.
4. `dsf_ai_service/glew_runtime/native_resident_organism.py` — truthfully named
   immutable evidence field validation only.
5. `dsf_ai_service/native_production_app.py` — truthfully named observer and
   transport projection only; no cognition or sound generation.
6. Directly connected tests and repair ledgers.

`resident_cognitive_formation.rs` does not change in this emitter slice. The
existing dedicated layer-13 identity, exact carrier/work settlement, motor
preparation provenance, formations, contacts, neurons, L0-L4, all seven DSF
fields, MathLoom, Psi/Krimelack, cochlear transduction, world authority,
persistence identity, and speaker byte custody remain unchanged.

## Copied-production-body authority retained

Attempt 34's fresh private clone
`guala_speech_impact_proof_356896_20260831` remains the sole candidate proof
body. It was cloned from read-only volume
`guala_glottal_proof_356896_IGGkvC`, exact task-1402 image digest
`sha256:f6cacca867283e1b3f32657e86964938350c9b425ee00cf36ec3d57522f21904`,
identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`, tick `356896`, and raw state
SHA-256
`fff0b81a0f4136560505eea30136b47805b80cbe22b8a63b41585fdc17a6572f`.
The rejected source invocation never ran against or wrote that clone. All rows
in attempt 34's mandatory falsification matrix remain mandatory. No unit or
synthetic result may substitute for the migrated copy, exact self-hearing,
cold restart, rest, learned control, blind audibility, first learned utterance,
conversation and bounded-resource rows.

## Architecture honesty gate

1. **Requested architecture:** organism-owned bounded acoustic action, shared
   pressure, same-ear self-hearing, learned correction and eventual talking,
   without reconstructing a human mouth.
2. **Current code reality:** task 1402 hears and self-hears exact pressure but
   its endogenous source is the rejected fixed buzz; the local unbuilt
   prototype is also rejected for underived constants and false labels.
3. **Conflict:** yes, until this physical transducer and learned control pass
   the complete copied-body matrix.
4. **Not extended:** the 160/16,000 program, human fold reconstruction,
   antagonist suppression, target PCM, TTS, phoneme/word tables, input-analysis
   vocoding, observer control, semantic labels, or L0-L4.
5. **Single next item:** replace the rejected unbuilt recurrence with this
   declared physical law and run focused falsification before touching the
   copied body.
6. **DSF evaluation:** the unchanged full explicit seven-field path remains
   authoritative.
7. **Lost field structure:** none.

