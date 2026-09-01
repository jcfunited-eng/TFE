# Guala speech repair attempt 37 — sustained-gesture boundary

Status: **causal analysis in progress; no source edit, build, copied-body
migration, package, deployment, or live writer is authorized**

## Why this is a new attempt

Attempt 36 locked the already-falsified buzz, scalar three-surface drive,
human-mouth reconstruction, antagonist subtraction, false self-hearing, and
absence of learned ordered vocal control. This attempt does not retry any of
them. It evaluates Joseph's narrower physical proposal: one sparse native
motor event launches or alters a sustained acoustic-body gesture, while the
body's own persisted mass, damping, stored work, and recovery carry that
gesture between later motor events.

Claude's memory incident remains a binding source gate. Task 1400 is the last
survivable base, not a clean base. Speech implementation must begin only from
the settlement-fixed base after its long flat resource proof and cold restore.

## Architecture decision under analysis

The proposed separation is:

1. Native cognition learns and replays only ordered **motor-change events**.
2. Each event changes bounded persistent acoustic tissue state once.
3. Exact tissue mechanics continue across the existing body clock without a
   repeated command, duration counter, target waveform, or phoneme program.
4. A later motor event may alter or release a gesture while prior stored work
   is still unfolding.
5. A dumb renderer exposes the resulting pressure; the same exact pressure
   returns once through the ordinary cochleae.

This keeps sequence learning general. The missing sequence law need not store
waveform samples, prescribed mouth poses, or a speech-only program. It retains
only the same kind of ordered action transitions required for play and other
learned skills.

## Source facts already established

- The native mechanical clock is 1 ms. The 250 ms microphone/audio hop is a
  transport batch, not the organism's actuator law.
- `ArticulatedBodyState` already persists body state across intervals and cold
  restart.
- The quarantined `9f7460c0` candidate proves that finite mass/damping/
  stiffness state can ring, decay, reach exact rest, and survive restart
  without a phase clock or fixed utterance duration.
- That candidate is still rejected as speech: it sums all recruitments and
  applies the same impulse to all three surfaces, so distinct topology cannot
  produce distinct spectral control.
- Its transport can place exact 16 kHz pressure and four sample-by-sample body
  trajectories into the next whole-sensorium episode. Those renderer samples
  must not be mistaken for thousands of learned sequence links or independent
  cognition commands.
- The voice lineage multiplied the leaking neuron-settlement path through
  17-hop self-hearing feedback. Even after Claude repairs the underlying
  approximately 700-byte-per-call deposit, that multiplier is prohibited from
  returning in speech or environment work.

## Exact call-level cause of the hop multiplier

The multiplier is not an unavoidable cost of hearing and is not caused merely
by having 16 kHz PCM:

1. `_perform_admitted_intake_locked` calls
   `_admit_in_flight_acoustic_consequence` **before** it advances the primary
   world intake.
2. `_admit_in_flight_acoustic_consequence` expands the entire pending pressure
   span into successive 250 ms `_mono_pcm_hop_episodes` and passes all of them
   through `advance_in_flight_self_hearing_unsealed`.
3. The native method consumes the old pending consequence, advances the vocal
   body once for every resulting episode, and installs all pressure emitted
   during those advances as a new pending consequence.
4. The later primary-world advance does not consume that new pending sound.
   `advance_admitted_intervals_unsealed` carries it forward and
   `InFlightAcousticConsequence::followed_by` concatenates any further body
   emission behind it.
5. The next intake therefore hears the concatenated backlog as more causal
   hops. On the rejected fixed-phonation body, hearing renewed motor discharge,
   so the backlog became the measured steady 17-hop feedback regime.

This is a synchronization defect, not a reason to accelerate the neuronal or
body interval law. Finite gesture mechanics remove the fixed self-renewal, but
they do not by themselves make concatenating unheard physical intervals
truthful. A legitimately babbling organism could otherwise recreate the same
backlog.

## Required acoustic interval invariant

The accepted transport must enforce one physical timeline:

- the prior interval's emitted pressure is heard during the next ordinary
  whole-sensorium/world interval;
- the acoustic body advances once for that interval, not once for self-hearing
  and again for the same world time;
- consumption of the predecessor consequence and installation of the newly
  emitted successor are one native transition;
- the successor is bounded to that one physical interval;
- producing a successor while an earlier consequence remains unconsumed is a
  synchronization failure and must refuse; it must neither append the two in
  time nor silently replace/erase either one; and
- self-pressure and simultaneous external pressure require an exact physical
  coexistence/superposition proof before implementation. Two sequential
  episodes cannot be called simultaneous hearing.

`InFlightAcousticConsequence::followed_by` therefore cannot remain on the
accepted speech path. Its append semantics are the direct backlog mechanism.

## Accepted consequence

Joseph's sustained-gesture proposal clears the false requirement that an
ordered learned chain advance at the acoustic sample rate. A word-sized act can
be a sparse order of gesture launches, alterations, and releases while the
physical body fills the intervals continuously. The interval law does not need
to be accelerated or replaced.

This is not yet implementation clearance. The following remain unproved:

- independently controllable spectral tissue axes rather than one scalar
  impulse;
- a general retained ordered-action path that replays distinct motor events;
- exact timing custody for a second gesture while the first remains active;
- exact same-interval coexistence of self-pressure and microphone/world
  pressure;
- bounded native proprioception without promoting every renderer sample into a
  separate causal settlement event; and
- a copied newest production body showing a flat resource line beyond every
  failed window.

## Prohibited extensions

Do not extend or reintroduce:

- the fixed 160/16,000 buzzer;
- the human glottis, tongue, mouth, or vocal-tract reconstruction;
- `9f7460c0`'s scalar all-surfaces impulse;
- sample-by-sample waveform history as cognition or sequence memory;
- a recursive drain-until-quiet self-hearing loop;
- in-flight pressure concatenation across world intervals;
- phoneme, word, target-frequency, or target-waveform tables;
- Python action, timing, cognition, or meaning authority; or
- any bare task-1400 or voice-lineage source before Claude's certified clean
  settlement base exists.

## Exact causal falsifiers required before code

1. Sever motor input after one launch: only already-stored finite work may
   continue; it must decay to exact rest and never create another command.
2. Apply two different typed motor paths: persisted tissue trajectories and
   radiated spectra must differ. Topology-insensitive equality is failure.
3. Reverse or discontinuously cue the learned order: it must not replay the
   forward motor sequence.
4. Repeat the same learned path: retained sequence structure and state bytes
   must remain bounded and idempotent rather than growing once per exposure.
5. Consume one emitted pressure consequence: it must enter both ordinary
   cochleae exactly once; restart must neither erase an unconsumed consequence
   nor replay a consumed one.
6. Present simultaneous external and self-pressure: the admitted cochlear field
   must equal the exact declared acoustic coexistence law, and the body and
   cognition must advance only one shared interval.
7. Compare renderer sample count, receptor gate count, neuron-settlement call
   count, RSS, CPU, and persisted bytes. None may grow recursively with
   self-hearing or accumulate per lived beat.
8. Cold restore during an active gesture: identity, all existing neurons,
   contacts, formations, full seven-field DSF state, learned sensory state,
   tissue state, and the remaining finite pressure consequence must be exact.

## Single next item

Prove the exact same-interval acoustic coexistence boundary using the mounted
whole-sensorium source format: how predecessor self-pressure and simultaneous
microphone/world pressure become one truthful cochlear field while the native
runtime authenticates exact once-only consumption and advances cognition/body
once. No implementation follows until that proof and Claude's clean-base
certificate both exist.
