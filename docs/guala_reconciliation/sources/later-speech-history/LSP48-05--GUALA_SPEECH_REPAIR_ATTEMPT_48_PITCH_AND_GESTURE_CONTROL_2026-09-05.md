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

## Candidate 48C — exact current production pair and ordinary-life reach

The first immutable task-1429 capture at tick 434112 contained the organism but
not its exact associated world generation. It was therefore insufficient for
the standing copied-production-body gate and was not used as deployment proof.
Several read-only capture invocations then failed without changing production:

- `/app/guala/native-organism` was rejected after the task definition proved
  the live root is `/app/guala/native-organism-gen5`;
- fetching the association and its world in separate calls lost a generation
  to the bounded world garbage collector;
- a tar/base64 terminal transfer was truncated;
- the first streamed transfer lost 1,435 characters; and
- a locally reconstructed pair without the retained predecessor was correctly
  refused by current-only recovery as
  `native organism retained predecessor is absent`.

These are observer/harness invocation failures, not candidate failures. They
must not be retried as if they were unexplored hypotheses. The corrected
read-only observer held current, predecessor, association, and world together
in bounded process memory and streamed them without writing to the organism.
It captured this complete exact pair at tick 469814:

- organism identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`;
- current raw receipt
  `9db4d05cb4d3de3a99aef5129596c4ea82dc5552d7f00eea0c934d7673d79df1`,
  112,836,426 raw bytes;
- current stored SHA-256
  `9cb4342f4c6d3f847033a66b91468f4fd96b3f0e860bac33d6cb9bf0b71eaf58`;
- predecessor receipt
  `a938927554035ba378c77c1eb2a5508ac09337fe316f263efb807fd83d29f447`;
- predecessor stored SHA-256
  `bab21d99de186789e68e59e97b779ee1feb591762bd98322d487ad42e0886b35`;
  and
- associated world SHA-256
  `613fc6737b83fcaaa037d3686bbe7db80ca9396b0a07ed2ae7b3c42d4e6c2d9a`.

The candidate started privately from those exact bytes with the exact live
sense and world flags. Version-9 migration produced successor receipt
`836ad4305b2ff57e7ad73743c1521c7f3da1c034848c65c04ad50af5db0f7fec`
at the unchanged tick and identity. It preserved the associated world hash,
all 1914 completed neurons, 194815 resting neurons, and zero Python callbacks.
The 46-axis body contained neutral tension `[256, 64, 256, 1024]` and encoded
to body SHA-256
`28d92543422ac46224d818765ad64a779dde116d1ed9dd11753550b683d7e7bb`.
A second fresh cold startup produced the same successor receipt, body hash,
world hash, tick, and identity.

Thirty-two ordinary `_attempt_unattended_interval` calls—not a diagnostic
motor helper or authored trajectory—then established both the working path and
the remaining failure. Nine intervals carried real vocal motor bindings. Ten
distinct learned-work strengths from 1 through 82 whole carriers moved tract
sections 0, 1, 2, 3, 6, and 7. Sixteen distinct 4,000-sample pressure waves
returned through self-hearing. The final organism was tick 469879, 113,538,041
bytes, receipt
`00eb83e84fd550216f27eb367df12e0e59fd453de2d697f751ce845072cba878`.
Thus the variable-strength learned motor -> tissue -> breath pressure ->
self-hearing chain works under ordinary whole-sensorium life.

The tension coordinate remained exactly 256 in every interval and no tension
motor binding occurred. Native settlement took 1,718.0 to 2,412.8 ms per
represented 250-ms interval (mean 1,920.84375 ms); that already-known shell
timing defect remains outside this narrow pitch-reach correction.

Artifacts:

- `/tmp/guala-speech1429-complete-9db4d05cb4d3` — exact captured pair at
  receipt `9db4d05c...`; a later private startup moved this local directory's
  `CURRENT` and garbage-collected its predecessor, so the directory itself is
  not described as immutable. The retained compact `9db4d05c...` generation
  remains byte-exact and is the source used by every Candidate 48C/48D proof;
- `/tmp/guala-speech1429-sequence.dpHRJX/candidate48-ordinary-32.json` —
  ordinary interval report, SHA-256
  `cd5d02735a9ce8f17c1b04f2592abedebb954a6c54b9635eddd2652d19baa23c`;
- `/tmp/guala-speech1429-sequence.dpHRJX/candidate48-ordinary-32-post.glorun`
  — exact final raw body; and
- `/tmp/guala-speech1429-sequence.dpHRJX/candidate48-ordinary-32-census.json`
  — initial/final native contact census.

## Candidate 48D — exact tension-reach cause and bounded correction

The census closes the cause. On the post-run body, tension position receptors
mounted at topology indices 196 and 197. Their two layer-8 regulation cells
`...10d5` and `...10e3` each contact exactly one new layer-12 motor,
`...0517` and `...0525`. Neither motor has a layer-11 ordering contact. The
whole organism grew one other L11->L12 contact during the run, proving the
general growth law was active; it did not reach either tension motor.

The source cause is equally exact. A complete body admission sets the existing
one-shot `initial_vocal_tract_calibration` boundary. Both the caller and
`exact_initial_vocal_tract_calibration_regulations` then restrict that boundary
to `is_vocal_tract_section()`. The eight older tract-area axes receive their
first physical calibration, explaining their ordinary movement above. The new
longitudinal-tension axis is already classified by fixed anatomy as a vocal
articulator but is excluded from that calibration in both places. With no
initial movement, no tension consequence can participate in the existing
ordering-to-motor developmental law. That is a circular developmental
deadlock introduced by appending the axis without enlarging the already
ratified new-vocal-body calibration class.

The bounded correction is to classify longitudinal tension alongside the
eight tract sections for this one complete-body admission. It must not include
limbs, face, glottal closure, sparse later pose, or any requested sound. It
adds no phoneme, pitch target, trajectory, score, lookup table, timer, random
drive, sequence object, or persistent field. The complete-source predicate
still makes it one-shot. Actual carrier imbalance between the two ordinary
antagonist paths determines whether and how the tissue moves; the correction
does not choose a direction or strength.

The correction passes only if the same exact production pair proves all of
the following over a range rather than a one-off:

- ordinary whole-sensorium life binds and moves at least one tension motor;
- more than one organism-owned tension position and pressure consequence are
  observed;
- variable motor work, conservation, limits, breath exhaustion, and severed
  silence remain exact;
- non-vocal axes and ordinary later tonic pose cannot use the calibration;
- the prior tract movements and self-hearing remain present;
- cold restart is exact; and
- CPU, RAM, encoded size, contact count, and retained frontier counts remain
  bounded with no surviving harness process.

Failure of ordinary tension movement rejects this correction. It must not be
replaced by a test-authored posture or a preinstalled learned L11 route.

## Candidate 48D rejection — classification was necessary but not sufficient

The proposed classification-only correction was applied on the private branch
and rejected before deployment. On the exact copied production generation, the
complete body admission reached both tension motor paths, resolved one permitted
layer-8 regulation for each, and identified each regulation as a fresh causal
seed. Nevertheless, the exact directed-transfer list into both tension motors
was empty. The tension coordinate remained exactly 256 and produced no binding.

A deliberately non-production diagnostic then retained that same permission
after the first source frontier and allowed the older causal-seed set in place
of the fresh-only set. Four ordinary whole-sensorium attempts still produced no
whole-carrier transfer and no tension movement. This rejects the hypothesis
that same-interval provenance or the three-frontier permission window is the
whole cause. That diagnostic relaxation is not a repair and is prohibited from
commit or deployment.

The before/after native census names the physical reason. The newly grown
tension paths are complete:

- position receptors: layer 5 lineages `...0b14` and `...0b22`;
- integration cells: layer 6 lineages `...2cef` and `...2cfd`;
- regulation cells: layer 8 lineages `...10d5` and `...10e3`; and
- motors: layer 12 lineages `...0517` and `...0525`.

Each new layer-5 and layer-8 cell held only 12 separated elementary carriers;
both layer-6 cells and both motors held zero. The three serial contacts advanced
only `3/20498`, `-3/48197`, and `3/48197` of one carrier on the minimum path
(and the corresponding `3/20701`, `-3/48508`, and `3/48508` on the maximum
path). Transition-work phase stayed exactly zero. No contact reached one whole
carrier, so no motor discharge existed for the body or renderer to use.

Four explicitly repeated complete 92-terminal body observations were then run
on another private exact copy. Every observation was admitted, but all 92
receptors were physically unchanged, receptor changing-count was zero, tension
bindings and consequences remained empty, and tension stayed exactly 256. This
rejects a missed-second-observation/bootstrap hypothesis: repeating an unchanged
pose cannot create physical work.

The first repeated-body invocation through the Python evidence validator was
also rejected because an articulatory continuation lacked what that validator
considered an exact causing vocal motor. The native candidate was discarded.
The repeat experiment was rerun through the same native prepare/commit methods
while bypassing only that process-local Python evidence conversion; it then
completed and produced the zero-change result above. This is a separate shell
validator defect, not the cause of the idle tension route.

Current causal verdict: the appended tension route is not blocked by missing
anatomy, scheduling permission, ECS, persistence, or the acoustic renderer. It
is a newly grown native sensorimotor route with no physical initiating work:
unchanged position provides no receptor work; the new motor has no learned
layer-11 contact; and without a first motor discharge there is no moved-body
consequence from which that contact can develop. Existing vocal axes work
because their older layer-8 and layer-12 cells already carry substantial lived
membrane separation; copying that learned state into the new route would be an
identity/meaning violation and is rejected.

Deployment history at this gate: no image build, task definition, rehearsal,
cutover, or hot deploy was attempted. Production remains task 1429. The next
repair must supply a bounded organism-owned physical initiation mechanism for
new motor anatomy without a phoneme, posture, requested sound, copied learned
charge, random command, or shell-authored act, and must first pass the same
exact copied-production-body range and severing controls.
