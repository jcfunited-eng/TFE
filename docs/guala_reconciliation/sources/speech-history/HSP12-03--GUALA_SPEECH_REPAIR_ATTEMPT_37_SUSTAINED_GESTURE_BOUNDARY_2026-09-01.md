# Guala speech repair attempt 37 — sustained-gesture boundary

Status: **timing and transport causal-impact analysis complete; copied-production
predecessor eligibility proved; candidate copied-body proof, source edit, build,
package, deployment, and live writer remain unauthorized**

Stable item: `SPEECH-37-ATOMIC-SUSTAINED-GESTURE`

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
the settlement-fixed base after its repeated long flat resource proof and cold
restore. The quarantined `9f7460c0` lineage is evidence only and may not be
cherry-picked.

## Architecture decision

The accepted separation is:

1. Native cognition produces sparse typed motor-change events, not acoustic
   samples.
2. Each event changes bounded persistent acoustic tissue state once.
3. Exact tissue mechanics continue across the existing body clock without a
   repeated command, duration counter, target waveform, or phoneme program.
4. A later motor event may alter or release a gesture while prior stored work
   is still unfolding.
5. A dumb renderer exposes the resulting pressure; the same exact pressure
   returns once through the ordinary cochleae.
6. A learned vocal chain advances at gesture boundaries. The renderer's
   16-kHz samples are physical consequence, not thousands of cognitive links.

This does not introduce a stored sequence object. A later gesture may be
caused by the proprioceptive and self-heard consequence of an earlier gesture
through the same retained phase/contact paths used by every learned action.
That is a general procedural path, not a speech program. A word claim still
requires later partial-cue continuation, reuse, and meaning evidence.

## Locked source facts

- The native mechanical clock is 1 ms. The 250 ms microphone/audio hop is a
  transport batch, not the organism's actuator law.
- `ArticulatedBodyState` already persists body state across intervals and cold
  restart.
- `MotorUnitRecruitment` already carries one exact mounted
  `BodyEffectorTerminal`, antagonist direction, outward whole carriers, and
  physical preparation transfers. That typed event is the correct possible
  acoustic-body input. A separate layer-13 speech permission is not required
  to establish that a real vocal motor moved real tissue.
- The current acoustic body instead receives only aggregated layer-13
  recruitments. That loses the typed vocal terminal before acoustic actuation.
- The quarantined `9f7460c0` candidate proves only that finite mass/damping/
  stiffness state can ring, decay, reach exact rest, and survive restart. It
  is rejected as speech because it sums all recruitments and applies the same
  impulse to all three surfaces; distinct topology produces identical control.
- `NativeJointSourceEpisode` retains exact normalized source trajectories and
  its authority receipt, but not the complete pre-cochlear 16-kHz PCM body.
  Once an episode has been built, exact raw pressure superposition cannot be
  recovered from its decimated legacy ports or nonlinear cochlear envelopes.
- The current gammatone implementation already has a bounded streaming entry
  point. The production builder uses the zero-state whole-capture entry point.
  Any hop-by-hop composition must carry the same bounded filter state across
  the hops of that one intake or it would introduce a new false reset.
- The voice lineage multiplied the leaking neuron-settlement path through
  17-hop self-hearing feedback. Even after the underlying per-call deposit is
  repaired, that call multiplier is prohibited from returning.

## Exact cause of the 17-hop multiplier

The multiplier is not an unavoidable cost of hearing and is not caused merely
by having 16-kHz PCM:

1. `_perform_admitted_intake_locked` first calls
   `_admit_in_flight_acoustic_consequence`, before the primary world intake.
2. That function expands the entire pending pressure span into successive
   `_mono_pcm_hop_episodes` and advances all of them through
   `advance_in_flight_self_hearing_unsealed`.
3. Native code clears the old pending consequence, advances cognition and the
   vocal body once for every self-hearing episode, and installs pressure
   emitted during those advances as another pending consequence.
4. The later primary-world advance carries that new pending sound without
   consuming it. `InFlightAcousticConsequence::followed_by` concatenates any
   further emission behind it.
5. The next intake therefore hears a longer time-appended backlog. On the
   rejected fixed-phonation body, hearing renewed vocal discharge and the
   system reached the measured steady 17-hop/49.4-second regime.

The pressure vector itself is capped. The failure is repeated advancement and
chronological append, not unbounded vector cardinality.

## Exact one-timeline acoustic law

The accepted path must perform these operations for each ordinary physical
interval:

1. Hold at most one bounded current pressure-arrival field, never an event
   history.
2. Consume the portion that physically reaches the ears in this interval.
3. Add signed self-pressure and signed external/world/microphone pressure
   sample-by-sample on their common 16-kHz clock using a wider integer
   intermediate.
4. Refuse an out-of-range sum. Clipping, normalization, gain reduction, or
   silent replacement would change the physical pressure and is forbidden.
5. Run the existing pre-receptor cochlear mechanics once on that composed
   pressure and build one whole-roster joint episode containing the rest of
   the simultaneous world/body state.
6. Advance cognition and the articulated/acoustic body once for that interval.
7. Shift any lawful unconsumed arrival tail and superpose newly radiated
   pressure at the same future sample positions. Do not append it later in
   time. Refuse if the declared finite propagation horizon would be exceeded.
8. Atomically install that one bounded successor arrival field while consuming
   the authenticated predecessor.

This corrects an earlier over-strict draft of this attempt. Source inspection
proved that valid intervals can have different lengths, including 1 ms body
consequences and 250 ms whole-sensorium hops. Refusing every new emission while
an older tail exists would make lawful overlapping waves impossible. The
correct physical rule is bounded sample-aligned superposition of overlapping
future pressure, never `followed_by` chronological concatenation.

## Why two coexisting source episodes are not enough

Passing self-sound and external sound as two coexisting
`NativeJointSourceEpisode` values would still be false. Each episode would run
its own acoustic receptor work. Pressure waves add before the ear's nonlinear
band-envelope calculation; separate band energies lose their interference
terms. The raw signed pressures must therefore be composed before `_pcm_hops`
and `_cochlear_hops`, then appear in one acoustic part of one whole-roster
episode.

## Required transport custody

The current public intake builders create immutable episodes before or inside
the transition lock. Exact composition requires a bounded transport plan that
retains each hop's raw external PCM until the lock is held. Under that lock:

- read one cardinality-consistent native pending pressure/body state;
- compose the raw pressure for the next hop;
- advance the intake-scoped streaming cochlear state;
- create the one whole-roster episode from that composed pressure;
- invoke a specialized native advance that authenticates the exact pending
  bytes, consumed sample count, supplied raw-pressure bodies, and episode;
- atomically consume/shift the predecessor and install the superposed
  successor; and
- release all raw hop and filter scratch after the intake.

Python remains bounded pre-receptor transport only. It does not select a
gesture, motor, word, duration, frequency, meaning, or next action. Native
cognition and the typed body remain the sole causes.

## Complete caller impact census

Every path below ultimately enters `_perform_admitted_intake_locked` and must
use the same per-hop acoustic composition boundary. No path may retain the old
pre-drain as a compatibility fallback.

| Intake family | Current acoustic source | Required treatment |
|---|---|---|
| unattended persistent world | authored silence | compose pending self-pressure with silence before the whole-roster hop |
| live camera only | authored silence | same; camera continues on the shared clock |
| live camera plus microphone | raw 16-kHz capture | compose exact microphone and self-pressure before both ear paths |
| grounded world voice | raw 16-kHz tutor pressure | preserve world light/contact/chemistry and compose per hop |
| mono audio/local offered audio | raw 16-kHz pressure | compose per hop and carry intake-local cochlear state |
| card lessons and spoken card lessons | signed or live tutor pressure | compose without altering card light, touch, taste, smell, or presentation authority |
| songs and audiovisual local material | raw pressure plus synchronized visual trajectories | compose without changing sample-to-frame alignment |
| silent visual, rendered light, Gutenberg pages | authored silence | self-pressure replaces only acoustic silence; all other fields remain unchanged |
| participant/world/body action consequence | authored silence on its exact duration | consume the matching arrival prefix and preserve the exact 1-ms or declared action clock |
| vestibular/root trajectories | exact 1-ms subintervals | they may not run a second acoustic-body advance beside the same world time; interval composition must include their elapsed clock |
| action/consequence re-entry and body proprioception | body source plus world source | preserve coexisting body evidence while advancing the acoustic body once |

The existing episode builders cannot be left as opaque prebuilt inputs where
self-pressure may exist, because their raw pressure has already been lost.

## Native state and persistence impact

- `InFlightAcousticConsequence` remains bounded current physical state.
- `followed_by` is removed from the active path and its time-append tests become
  rejection/superposition tests.
- The successor carries one pressure-arrival field plus its exact mechanical
  trajectories and source-clock/horizon authority; it never contains a list
  of utterances or interval records.
- Decode accepts only the declared current format. A one-way migration must
  reject an old time-concatenated span that cannot be interpreted without
  guessing. No old backlog may be truncated or replayed.
- A cold restore with an unconsumed arrival reproduces the identical next
  composed pressure. A cold restore after consumption cannot hear it again.
- Full neuron, contact, formation, body, learned sensory, and complete
  seven-field DSF state remain unchanged. L0-L4 and MathLoom/Krimelack code are
  outside the edit boundary.

## Resource and call bound

For an intake with `H` physically authored hops and a reached frontier
`N + C + R`:

`native cognitive/body advances = H`, never `H + self_hearing_backlog_hops`.

Persistent acoustic storage is one finite propagation field bounded by its
declared sample horizon and four mechanical channels. Scratch storage is one
raw external hop, one composed hop, one cochlear streaming state, and one
source episode. It is replaced per hop and released at intake end. No retained
quantity grows with organism age, number of prior utterances, or observation
count.

Proof must report authored hop count, native advance count, renderer sample
count, receptor gate count, neuron-settlement count, peak/current RSS, CPU,
envelope bytes, and durable bytes. Equality of authored hops and native
advances is a hard invariant.

## Copied-production predecessor proof — complete

The exact task-1400 raw body copied read-only at
`/tmp/guala-task1400-probe.ufs40Q/in/current.glorun` was verified as:

- raw SHA-256
  `e4c2b4f0400d8f81d02a125cd96fe291837ce45f7bd4c959ffcba924ff0043c4`;
- `107,627,298` bytes;
- organism identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`;
- tick `352577`; and
- no pending acoustic source tick, pressure bytes, or body bytes.

It restored read-only with the exact final V40 wheel at
`/tmp/guala-l006-v40-final-wheel.LFH2pt/`, wheel SHA-256
`dad5a766f836956f4e7f6fead1f812bb6e0bacf74be657fed69adf7a7d8590b3`.
The restored state SHA-256 matched the raw body exactly.

The earlier wheel at `/tmp/guala-l006-v40-wheel.XH9MKV/`, SHA-256
`6ff24ae76cf273b0478270c8ea5c5a71ab0cb45affc098a87c1543d65cc61bdc`,
refused the same body with `resident neuron lineage authority is absent`.
That attempt is not evidence and must not be retried. This proves that a wheel
named V40 is not sufficient; the exact final artifact is mandatory.

Because the authenticated predecessor contains no pending sound, a future
one-way acoustic-state migration need not erase, reinterpret, or replay live
pressure on this exact body. This is predecessor eligibility only.

## Candidate copied-production proof — still required before source coding

No accepted candidate exists, so the user-required end-to-end copied-body proof
is not complete and source coding remains blocked. The proof must use the
newest clean-base clone and show, in one continuous run:

1. exact identity/state restore and byte-idempotent migration;
2. one real typed vocal motor event changes only its physically connected
   acoustic tissue coordinate;
3. a second distinct typed motor path produces a distinct tissue trajectory
   and spectrum;
4. sustained pressure continues from stored work after motor severing, then
   reaches exact rest with no manufactured command;
5. simultaneous external and self-pressure produce the exact accepted signed
   sample sum and one cochlear field;
6. one authored physical hop causes exactly one cognitive/body advance;
7. the pressure is heard by both mounted ears exactly once;
8. cold restart before hearing preserves it, and cold restart after hearing
   does not replay it;
9. subsequent gesture causation comes only from retained physical paths and
   sensed consequence, never a list, target, timer, label, or observer; and
10. CPU, RSS, envelope bytes, contacts, and durable bytes remain flat beyond
    every failed resource window.

## Prohibited extensions

Do not extend or reintroduce:

- the fixed 160/16,000 buzzer;
- the human glottis, tongue, mouth, or vocal-tract reconstruction;
- `9f7460c0`'s scalar all-surfaces impulse;
- the special layer-13 cell as a software permission to make sound;
- sample-by-sample waveform history as cognition or sequence memory;
- a recursive drain-until-quiet self-hearing loop;
- in-flight chronological pressure concatenation;
- separate self/external cochlear episodes called simultaneous;
- phoneme, word, target-frequency, or target-waveform tables;
- Python action, timing, cognition, or meaning authority;
- a source episode rebuilt from decimated or band-envelope data after its raw
  PCM was discarded; or
- any bare task-1400 or voice-lineage source before Claude's certified clean
  settlement base exists.

## Exact falsifiers required before deployment

1. Sever motor input after one launch: only already-stored finite work may
   continue; it must decay to exact rest and never create another command.
2. Apply two different typed motor paths: persisted tissue trajectories and
   radiated spectra must differ. Topology-insensitive equality is failure.
3. Reverse or discontinuously cue the learned order: it must not replay the
   forward motor sequence.
4. Repeat the same learned path: retained physical structure and state bytes
   remain bounded rather than growing once per exposure.
5. Consume one pressure consequence: it enters both ordinary cochleae exactly
   once; restart neither erases an unconsumed consequence nor replays a
   consumed one.
6. Present simultaneous external and self-pressure: the admitted cochlear
   field equals the exact declared signed-pressure composition, and cognition
   and body advance only once.
7. Exercise every intake family in the caller census with and without pending
   self-pressure; no compatibility pre-drain remains reachable.
8. Compare authored hops, native advances, renderer samples, receptor gates,
   neuron-settlement calls, RSS, CPU, state bytes, and durable bytes; no value
   grows recursively with self-hearing or organism age.
9. Cold restore during an active gesture preserves identity, all existing
   neurons, contacts, formations, full seven-field DSF state, learned sensory
   state, tissue state, and finite pressure-arrival state exactly.

## Single next item

Obtain Claude's certified settlement-fixed clean base and newest authenticated
body clone, then execute the candidate copied-production proof above. Under
Joseph's gate, no speech source edit begins before that exact proof can be
completed from already-authorized candidate mechanics; if no such accepted
candidate exists, the gate remains closed rather than weakening the proof.
