# Guala speech repair attempt 48 — organism-owned pitch and gesture control

Date: 2026-09-05

Status: causal-impact analysis complete; the test-only candidate and the
production body-axis implementation have independently passed copied-body
falsification. Production remains unchanged on task 1429. Nothing in this
record claims normal speech, singing, a word, or deployment.

## Architecture honesty gate

1. **Requested architecture:** one bounded deterministic vocal body capable of
   ordinary learned speech and singing. Breath supplies finite work; vocal
   tissue supplies a controllable periodic source; independent physical tract
   coordinates shape that source; the organism hears the exact pressure it
   emitted. Motor magnitude and timing must arise from settled organism state,
   not a sound, phoneme, word, note, or developer-authored trajectory.
2. **Current code reality:** attempt 47 removed the fixed-one-carrier learned
   motor split and proved dynamic source-work transduction through real copied
   motor cells, typed body terminals, finite respiration, pressure, and all 32
   cochlear receptors. The body has one glottal-aperture axis and eight tract
   area axes, but the valve frequency is fixed by two material constants at
   352..376 Hz. No organism-owned coordinate can change vocal-fold tension or
   fundamental frequency. The copied body also has learned routes to only two
   of its 26 present vocal terminals and no retained multi-posture gesture.
3. **Conflict with requested architecture:** yes. A material-fixed narrow
   fundamental can make the accepted Mama-A test-control sound, but it cannot
   carry ordinary intonation or melody. Independent pitch control and learned
   ordered gesture retention are absent.
4. **Mechanisms that will not be extended:** the retired task-1054 broad motor
   fan-out; the deleted fixed-one-carrier conversion; a target-frequency,
   phoneme, syllable, word, melody, or motor-pose table; TTS; a prerecorded or
   scripted trajectory; shell timing as organism state; a second language
   system; observer-selected output; a reduced DSF score; or an unlimited-air
   production source.
5. **Single exact next item:** use the existing immutable task-1429 body only
   as the physical predecessor in a test-only tension-range harness. Sweep one
   declared local tension coordinate through a bounded material law and prove
   that actual emitted fundamental frequency varies continuously and
   monotonically while pressure remains finite, zero respiratory work is
   silent, tract postures remain spectrally distinct, repeated runs are exact,
   and encode/decode leaves the copied body byte-identical. No production body
   field is added until this falsifier passes.
6. **DSF evaluation:** the complete joint seven-field L0-L4 result remains
   authoritative and unchanged. This work is downstream body mechanics and
   does not modify, project, or approximate DSF.
7. **Reduced-field loss:** none.

## What attempt 47 settled

The user correctly identified two related historical defects: a learned motor
event was flattened to one carrier, and task 1054 had previously demonstrated
variable internally caused motor discharge. The part of task 1054 that must be
restored is dynamic physical magnitude, not its old anatomy.

Attempt 47 now derives each learned motor preparation from the current founding
transition's released work and the mounted learned contact's conductance. The
motor's own gate accepts, retains, dissipates, and later discharges that work.
The exact copied body proved different event latencies and discharge rates,
exact conservation, severed/exhausted silence, typed vocal tissue movement,
finite respiratory work, emitted pressure, self-hearing, and cold continuation.

The old task-1054 topology cannot be copied back. Later audit established that
its broad coincidence growth had accumulated about 96,686 invalid
ordering-to-motor contacts and produced 144-terminal fan-out. Those contacts
were removed deliberately. The present sparse law grows one exact motor route
only from that terminal's lived proprioceptive consequence. Reintroducing the
fan-out would manufacture action identity and repeat a recorded failure.

## The newly isolated source defect

`virtual_articulatory_body.rs` currently computes valve rate solely from:

- `SPECTRAL_ORGAN_MATERIAL.valve_rate_floor_hz = 352`;
- `SPECTRAL_ORGAN_MATERIAL.valve_rate_ceiling_hz = 376`; and
- the fraction of finite respiratory work remaining.

Jaw, lips, glottal aperture, and eight tract sections change airflow and
resonance. None changes the source tissue's natural frequency. The organ
therefore has filter control but no independent pitch control.

That separation is not optional ornament. Human phonation changes fundamental
frequency principally through vocal-fold length, strain, and stiffness, while
the supralaryngeal tract shapes formants and timbre. The tract can interact with
the source but does not replace source control. Primary references used only to
establish this physical division are:

- Chhetri et al., *Neuromuscular control of fundamental frequency and glottal
  posture at phonation onset*,
  https://pmc.ncbi.nlm.nih.gov/articles/PMC3292611/;
- Zhang et al., *Influence and interactions of laryngeal adductors and
  cricothyroid muscles on fundamental frequency and glottal posture control*,
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4188037/; and
- Wolfe et al., *Vocal tract resonances in speech, singing, and playing musical
  instruments*, https://pmc.ncbi.nlm.nih.gov/articles/PMC2689615/.

The present 352..376-Hz band overlaps published four-year-old sustained-voice
values, but its 24-Hz span is not a motor range. A preschool voice study reports
age-four normal reference intervals spanning roughly 267..375 Hz for boys and
286..355 Hz for girls; this is population evidence, not a target table:
https://pmc.ncbi.nlm.nih.gov/articles/PMC9442076/.

## Candidate mechanism to falsify before implementation

The smallest non-flattened mechanism is one appended physical coordinate,
`vocal_fold_longitudinal_tension`, with one antagonist motor pair and ordinary
position/load proprioception. It is independent of `glottal_aperture`:

- glottal aperture governs airway opening and closure;
- longitudinal tension governs the valve tissue's natural frequency;
- respiratory work governs whether oscillation exists and how much flow is
  available; and
- the eight tract areas govern the lossy resonant filter.

The source rate must be derived from a declared mass-and-tension relation, not
interpolated between named notes. For the falsifier, a fixed virtual fold mass
and bounded tension range produce frequency proportional to the exact integer
square root of tension. The present accepted neutral source band remains the
neutral material point. No floating-point state, tuning table, musical scale,
or requested sound enters the organ.

The production form is not authorized by this document. The copied-body range
must first locate a multi-point region in which:

- increasing tension increases measured fundamental frequency;
- adjacent tension values do not collapse to one fixed rate;
- identical tension and predecessor state reproduce identical raw pressure;
- at least three materially separated pitches retain audible bounded pressure;
- changing tract posture at the same tension changes the pressure spectrum but
  not the tension coordinate;
- zero respiratory work yields exact silence at every tension;
- minimum and maximum tension cannot overflow, clip, or retain unbounded state;
- a severed tension motor can contribute no tension movement; and
- the exact copied body remains byte-identical because the harness has no
  production schema authority.

Failure of monotonicity, loss of exactness, one-point-only success, or pressure
outside the existing audio width rejects the candidate. A pleasant sound is
not enough to pass it.

## Complete causal impact if the falsifier passes

### Persistent body schema

The new coordinate would append after the eight existing tract sections so all
45 existing axis ordinals and all 90 existing terminal identities remain
unchanged. Body axes would become 46 and antagonist terminals 92. Body version
8 could no longer describe the successor, so a one-way version-9 decoder must:

- read every version-8 coordinate and all 90 retained activation values
  unchanged;
- append neutral tension and two zero activation values;
- preserve lung volume, acoustic state, proprioceptive initialization, and all
  existing positions exactly; and
- force one ordinary complete-body proprioceptive observation only so the new
  anatomy can develop without replaying or erasing old sensation.

The migration must be proven against the exact task-1429 bytes and must preserve
the whole organism identity, all neurons, all existing contacts, all full DSF
state, learned sensory state, world, tick, and current-only recovery authority.
Cold encode/decode of the migrated body must be exact.

### Fixed neuronal anatomy and topology

Two new physical terminals imply two new body position receptors, two load
receptors, their layer-6 local integration cells, layer-8 regulation cells, and
layer-12 motor cells. They append in the already-reserved added-body topology;
no old receptor, regulator, motor, or lineage address may move. The existing
mounting law—not a speech-specific shortcut—must create them on first reached
proprioception. The 112,677,154-byte copied organism must prove the append does
not collide with any resident place or lineage.

No learned L11-to-new-L12 route is preinstalled. Such a route may grow only
after real tension movement returns through the ordinary proprioceptive path in
the same causal episode as reached ordering/affective anatomy. This means the
organ gains a controllable body degree of freedom, not an authored pitch skill.

### Motor physics

The new terminal pair uses the same fixed-capacity antagonist tissue law as all
other articulated axes. Attempt 47's learned-work transducer supplies dynamic
physical preparation when and only when a real learned route later exists.
The fixed-one-carrier rule remains deleted. Existing glottal and tract motors
must be bit-for-bit behaviorally unchanged.

### Acoustic source

`advance_spectral_organ` would read the persisted tension coordinate alongside
glottal area and tract areas. Tension changes the valve-cycle rate through the
declared mass/tension law. It cannot create respiratory work, pressure, valve
conductance, or sound by itself. Work exhaustion still stops cycling; existing
loss still returns the acoustic state to exact rest; lung depletion and passive
return remain unchanged.

### Self-hearing and cognition

The pressure samples remain the only acoustic consequence. They traverse the
same room propagation and exact 32-site cochlea used for external and self
sound. No pitch label or note is sent to cognition. The organism may learn the
relation only through co-occurring tension proprioception, emitted pressure,
and later experience.

### Observation and UI

Read-only body observation must report the new axis, its two terminals, and the
exact L12 learned-work lineage when one exists. The articulation receipt must
continue to identify actual causal motor discharges and raw pressure. It must
not call a pitch, note, syllable, or word by name. Observer state remains
process-local, bounded, replace-only, and never enters the organism.

### Runtime, persistence, and resource bounds

The steady per-body cost is exactly one signed coordinate plus two bounded
activation counters, with a fixed number of new mounted cells and contacts.
Per-interval work remains a fixed 46-axis scan already scheduled for later shell
cleanup; no history, pitch queue, waveform cache, or per-word structure is
added. The migration changes fixed body width and every enclosing envelope size
calculation, decoder branch, rehearsal expectation, and resource declaration
that currently names 45 axes or 90 terminals. A cold restart and current-only
store round trip are mandatory.

AWS pre/post checks must show one healthy production task, no pending or stopped
replacement, completed rollout, all Guala alarms OK, no memory/call/storage
cascade, and no orphan local harness. The harness itself runs networkless,
read-only except for one bounded report, with explicit CPU/RAM limits.

### Normal speech and singing boundary

Passing pitch control is necessary but not sufficient. The complete vocal
mechanism also requires ordered, overlapping motor gestures: breath, source
tension/aperture, and tract movement must unfold together. The retained repair
history resolves how that timing is represented and must govern this work.

Attempt 38 withdrew the proposal for a new retained sequence level. The
canonical progression law already provides bounded physical ordering: exact
directed sparse transfers continue across adjacent frontiers, later physical
paths can recur over retained formation routes, layer-11 ordering transfers
prepare exact layer-12 motors, and sustained tissue motion overlaps later
frontiers. The three predecessor frontiers expire; no ordered-member array,
word trajectory, or sequence database is permitted or needed.

The remaining proof is therefore not authorization to invent a sequence
subsystem. It is to show that the enlarged organ remains reachable through
that existing sparse ordering law and can sustain one gesture while a later
one begins. Nothing in candidate 48 may claim a sentence, singing, or even
organism-produced Mama-A until that causal loop is proven on the copied body
and then live.

## Exact next verdict

Run the tension-range falsifier on the immutable task-1429 body. If it passes,
record its raw-pressure hashes, measured fundamental frequencies, pressure and
resource bounds, zero-work controls, and exact cold/body hashes here before any
production schema edit. If it fails, retain the failure and do not migrate the
body.

## Candidate 48A — copied-production-body tension range passed

The test-only source law was compiled only into the native library test and
run twice independently against the immutable task-1429 tick-434112 envelope.
The production service and store were never opened for writing. Both reports
are byte-identical, 5,810 bytes, SHA-256
`f1018d899099d667afd5835de58288898b76d598d633c2f182f42278f7484844`.

The exact copied articulated body encoded to SHA-256
`06a02a9dbadfef1d266b1a2aa70897c4184513f18a8e817dbcc8e08a71d1dd49`
inside the probe and cold-round-tripped exactly. Eight real finite respiratory
carriers drove the unchanged valve and tract. The fixed-mass square-root
relation produced this measured range:

| Tension quanta | Measured fundamental | Absolute pressure peak | Nonzero samples | Raw-pressure SHA-256 |
|---:|---:|---:|---:|---|
| 64 | 185.000 Hz | 271 | 15,943 | `19cc5c3e8111e96c14e2b1d4da8ce5954a7454a00c223e65f123e2c64cdfcc09` |
| 144 | 277.000 Hz | 358 | 15,980 | `cc33cb23a587c5db4cd628ff7c50574617ca30997c4b2a90410e65d6c1d7c5d0` |
| 256 | 370.000 Hz | 429 | 15,989 | `899bd643b60309fb6c042445cefebc8dc59b20099ec315bf74bc019c149e35e3` |
| 400 | 462.000 Hz | 426 | 15,981 | `28d17deb489688474416a56f013544efdf144d02c6a40770515a1a7356c0420b` |
| 576 | 554.207 Hz | 311 | 15,973 | `ddae7937e204756c399dff8826070ad752afb22994c89c16814edafbd8cfae8e` |
| 784 | 647.000 Hz | 243 | 15,972 | `22ae33858def96d7791cb553cfd93751ec25b48138287a12770330317efdacae` |
| 1,024 | 739.000 Hz | 227 | 15,953 | `53fefae7093c387a66a7697b022abeacf37cc11c72fde9e878287d87bde8d520` |

Every adjacent point increased source frequency. Every same-input repetition
produced the same pressure and successor body. Zero respiratory work produced
exact silence and the unchanged predecessor at all seven tension values.
Changing only copied tract section 0 by 100 square millimetres changed the raw
pressure while leaving the measured source frequency equal. No pressure
clipped the signed 16-bit audio boundary.

## Candidate 48B — persisted production tension axis passed on the copy

The candidate law was then implemented as body version 9 with one appended
`vocal_fold_longitudinal_tension` coordinate and its ordinary antagonist pair.
This is no longer a material override in the harness: the production acoustic
function reads the coordinate from the migrated articulated body itself. The
version-8 decoder preserves all 45 prior axes, all 90 prior antagonist
activation values, lung air, and acoustic state; it appends neutral tension and
two zero activations and requests one complete proprioceptive observation of
the enlarged anatomy. Unit falsifiers prove that migration and current-format
cold round trip exactly.

The exact task-1429 envelope was decoded through that version-8-to-version-9
path and exercised twice independently. The two 6,078-byte reports are
byte-identical, SHA-256
`80d81ad20954ef928b33de4f8e1c317923a3b2d8c84b4c4b6710e4940910cd5c`.
The migrated production body SHA-256 is
`28d92543422ac46224d818765ad64a779dde116d1ed9dd11753550b683d7e7bb` and
its current-format encode/decode round trip is exact. The seven measured
frequencies and pressure hashes remain exactly those in Candidate 48A. All
same-input repetitions, zero-work silence controls, and same-pitch/different-
tract controls passed.

The receptor geography was separately falsified: both new position/load
receptors map to unique appended layer-6 integration and layer-8 regulation
places, and no version-8 tract or root place moves. Focused results at this
gate are 23/23 articulated-body tests, 19/19 active articulatory-acoustic tests
(two explicitly ignored historical probes), and the dedicated cognitive-
topology test. These results close pitch control only. Existing sparse ordering
must now be falsified against the enlarged body before any speech claim or
deploy; no new sequence mechanism is authorized.

The first invocation with Cargo's `python-extension` feature is rejected as an
invocation error: extension-module linkage deliberately omits libpython and
cannot link a Rust test executable. It executed no candidate and changed no
body. The corrected fully qualified `--lib` invocation first proved the exact
test existed, then both bounded runs passed `1/1` with 608 tests filtered.

Pre- and post-run AWS checks both showed task definition 1429, one running,
zero pending, completed rollout, and all five Guala alarms `OK`. No Cargo,
probe, or native test process survived. The harness was bounded to two CPUs,
6 GiB virtual memory, and fifteen minutes; each warmed proof completed in less
than one second.

Artifact paths:

- `/tmp/guala-speech1429-sequence.dpHRJX/candidate48-pitch-tension-range.json`;
- `/tmp/guala-speech1429-sequence.dpHRJX/candidate48-pitch-tension-range-repeat.json`.

Verdict: the physical source mechanism passes its copied-body falsifier. This
authorizes implementation of the appended tension axis and its ordinary fixed
receptor/regulator/motor anatomy. It does not authorize a speech or singing
claim; existing organism-owned ordered gesture remains separately unproved on
the enlarged body.
