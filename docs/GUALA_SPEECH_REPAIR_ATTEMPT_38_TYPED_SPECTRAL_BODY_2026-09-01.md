# Guala speech repair attempt 38 — typed spectral body on task 1404

Status: **complete causal-impact analysis and exact copied-production-body
predecessor/current-candidate proof; production untouched; source implementation
not yet begun**

Stable item: `SPEECH-38-TYPED-SPECTRAL-BODY`

## Binding starting point

- Production task: `1404`, healthy.
- Exact source commit: `72442428407eb41a6d0417672469376d054750da`.
- Image digest:
  `sha256:d282afbbda0ae78270687c324c765cfcabd96b0ed97146aeea982404838f5a91`.
- Source SHA-256:
  `fc9a08911f0bc491191d35af308ca364878e72c3265ee1ef2f8ee060d651105f`.
- Native extension SHA-256:
  `2b68e8d23739b683c310ceb9653b121c8711602386bb2a67648f66dddf00cf68`.
- The task-1404 memory repair and copied-body soak/cold-restore proof are the
  clean source boundary. Neither bare task 1400 nor any quarantined voice
  lineage is a permissible base.

This attempt preserves L0-L4, all seven DSF fields, MathLoom/Krimelack, every
resident neuron, every accepted contact and formation, learned sensory state,
identity and persistent articulated body. It adds no ML, speech model, TTS,
phoneme table, word table, target waveform, scripted meaning or action label.

## Repair-history exclusions

This attempt does not retry:

- the fixed 160/16,000 buzzer;
- antagonist subtraction that stalled respiration;
- the human glottis/tongue/mouth reconstruction;
- attempt 34's unbuilt frequency coefficients;
- the topology-insensitive all-surfaces impulse;
- layer 13 as a software permission to make sound;
- recursive drain-until-quiet self-hearing;
- chronological `followed_by` pressure backlog;
- two separately transduced sound episodes falsely called simultaneous;
- a stored phoneme/word/sequence program; or
- any task-1401/voice-lineage artifact.

## Exact copied-production-body custody proof

Production was read only and was not paused. The newest captured body was copied
to:

`s3://dsf-ai-site-backups/guala/proofs/speech-task1404-tick-358454-20260901/`

The immutable receipt is:

- identity: `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`;
- tick: `358454`;
- state SHA-256:
  `8dbd3974ce19779d33984f61ec546b25ac0d3cf6164a88350db14ce2f6f6a100`;
- predecessor SHA-256:
  `9d0391fa4f7774a9454cb232bf3239c1941ae3c9d04677523f31677c16fac32e`;
- 32 files, 16,652,078 bytes; and
- manifest SHA-256:
  `3283fa5c2552ef859f488be8f5b5199dc90d5289d13c1bb7b6250f9cdc15e3c7`.

All 32 object hashes matched after download, after Docker-volume copy and after
the read-only restore. The exact task-1404 image cold-restored tick 358454 with
the same identity/state SHA, 1,812 neurons, 153 retained mosaics and zero Python
neuron callbacks. The body SHA was
`ecba74988...`; RSS was 522,056 KiB with zero swap. The read-only process exited
0 without OOM and all 32 hashes remained unchanged.

Two tooling failures are retained so they are not repeated:

1. A multiline shell-embedded snapshot program failed with `SyntaxError`
   before reading or writing state. The corrected snapshot used a single
   statement.
2. A Docker bind-mount copy saw the daemon's empty bind namespace and copied
   zero files. The container never ran. `docker cp`/named-volume custody then
   copied all 32 files and verified every hash.

## Copied-body current-candidate falsification

A second named volume was copied from the verified immutable volume and all 32
hashes matched before execution. It ran the exact task-1404 image with no
network, a read-only container root, a 6 GiB RAM ceiling, four CPUs and only the
copied body volume writable. This was a disposable copied-body experiment;
production remained untouched.

The copy advanced autonomously from tick 358454 through tick 358532 and exited
0, not OOM. At the final observation it used 639.8 MiB of 6 GiB. It naturally
produced multiple distinct typed layer-12 vocal motor events, including:

- jaw opening toward maximum, lineage
  `474c4e4c494e453100000000000002cb`, 3 carriers, with 3 applied displacement
  quanta;
- lip width toward minimum, lineage
  `474c4e4c494e453100000000000002e7`, 11-12 carriers;
- lip width toward maximum, lineage
  `474c4e4c494e453100000000000002f5`, 5 carriers;
- perioral displacement in both antagonist directions, distinct lineages and
  carrier counts; and
- glottal aperture toward maximum, lineage
  `474c4e4c494e4531000000000000032d`, 7 carriers.

Every event carried its actual terminal, direction, lineage, carriers,
preparation and ordinary proprioceptive return. The body state changed and the
observer truthfully reported native articulated action. The articulation
boundary nevertheless stayed `not_mounted` throughout because no layer-13
discharge occurred.

This is decisive predecessor/current-candidate evidence:

1. The mature organism already produces varied autonomous vocal-body motor
   gestures. Speech is not blocked on a new semantic sequence object.
2. The current software discards those gestures at the acoustic boundary.
3. The only admitted trigger is a glottal-toward-minimum special case. The
   observed glottal-toward-maximum event and every jaw/lip/perioral event are
   excluded even though they are real motor work.
4. The current scalar candidate therefore fails on the exact copied production
   body before any source edit. It must not be tuned or retried.

## Exact current-source cause

### `resident_cognitive_formation.rs`

`MotorUnitRecruitment` already carries the authoritative layer-12 motor
lineage, typed `BodyEffectorTerminal`, antagonist direction, outward whole
carriers, exact afferent ancestry and physical preparation transfers.

After those real events settle, a separate block manually co-recruits one
electrically isolated layer-13 cell only when the event is glottal aperture
toward minimum and is prepared by layer 11 or its exact layer-8 path. The cell
spends independent carriers. That software coordination is the rejected
permission gate.

### `virtual_articulatory_body.rs`

The acoustic body receives only `(topology_index, carriers)` from layer 13,
sums all carriers, caps them at eight and applies the identical impulse to all
three persisted surfaces. Topology is ignored. The three different stiffnesses
can ring and decay, but distinct motor gestures cannot command distinct tissue
coordinates. The result is a buzz, not a controllable developmental voice.

### `organism_runtime.rs`

The same transition separately settles typed layer-12 events into the 45-axis
body, producing exact signed displacement and proprioception, then discards
that typed information at the acoustic call and supplies only the scalar
layer-13 aggregate.

The runtime persists one bounded in-flight pressure/body field, but
`followed_by` concatenates new emission after old emission in time. The
specialized self-hearing advance consumes one pending field separately from
the primary world interval.

### `native_production_app.py`

Every intake pre-drains the pending sound through
`_admit_in_flight_acoustic_consequence`, expands it into cochlear hops and
advances cognition once per hop before advancing the primary world input. A
vocal consequence created while hearing becomes another pending field, and
later emission is appended. This produced the measured 17-hop/49.4-second
feedback regime and multiplied the now-repaired settlement leak.

External raw PCM is currently discarded once a `NativeJointSourceEpisode` is
built. Its decimated legacy ear values and nonlinear cochlear envelopes cannot
reconstruct exact pressure. Therefore exact self/external interference cannot
be repaired after episode construction.

## Accepted minimal spectral-body mechanism

The repair uses the existing three finite persisted acoustic surfaces as a
developmental spectral body, not as a human mouth:

1. The only actuator authority is an already-settled typed layer-12 vocal motor
   event.
2. Acoustic coupling uses the actual signed **applied body displacement**, not
   requested carriers. A motor stalled at an anatomical stop emits no new
   acoustic work.
3. Three fixed body attachments address three distinct persisted surfaces:
   glottal aperture, jaw opening and lip width. Antagonist direction supplies
   sign. These are body coordinates, not sound/phoneme identities. The other
   existing vocal axes continue to shape the shared bounded tube; they do not
   become hidden sound selectors.
4. The already-declared finite motor-to-surface displacement quantum supplies
   the coupling scale. No fitted gain, target pitch or frequency table is
   introduced.
5. Surface mass, stiffness, damping and tube loss continue the gesture from
   stored work after motor input ends and return it to exact rest. A later real
   motor event may alter a still-moving surface.
6. The layer-13 neuron and all its physical state remain preserved, but the
   manual co-recruitment block is removed from the active voice path. It is not
   deleted, relabelled or used as permission.
7. Renderer output is only the pressure produced by those mechanics. Human
   speaker amplification, if used, never changes the pressure heard by the
   organism.

This mechanism spends motor work once. The body displacement and radiated
pressure are two consequences of the same settled event, not two independently
energized actuators.

Primary research supports the scope without becoming design authority:
Remez et al. showed intelligible speech information can be carried by three
time-varying sinusoids (Science 1981, DOI `10.1126/science.7233191`), and
Shannon et al. showed high recognition from a few dynamically modulated
spectral bands (Science 1995, DOI `10.1126/science.270.5234.303`). These results
support a small dynamic spectral body; they do not install phonemes, meanings
or a promised first word.

## One-timeline self-hearing mechanism

Every physical hop becomes one explicit bounded `WholeRosterHopPlan` retained
only for the current intake. It holds the raw external signed PCM and the exact
non-acoustic sensory trajectories needed to build that hop. Under the existing
transition lock, and before cochlear construction:

1. Read and authenticate at most one native pending self-pressure field.
2. Signed-add its current prefix to the external pressure sample by sample in a
   wider integer.
3. Refuse overflow; never clip, normalize, smooth or substitute silence.
4. Run `_pcm_hops`/the existing cochlear mechanics once on the composed
   pressure.
5. Build one whole-roster episode with unchanged sight, touch, chemistry,
   proprioception and world authority.
6. Use the existing authenticated native consume operation to advance
   cognition/body once and consume the predecessor field atomically.
7. Persist only the newly emitted bounded future pressure field. No
   chronological backlog survives and no recursive pre-drain is reachable.
8. Replace and release the hop plan/filter scratch during this intake; nothing
   grows with organism age or utterance count.

Multi-hop lessons are advanced hop by hop without sealing between hops, so a
pressure caused in one physical hop can reach the ears in the next hop rather
than waiting behind the entire lesson. Coexisting sources inside one hop remain
coexisting. The hard invariant is:

`native cognitive/body advances == authored physical hops`.

## Complete causal impact and edit boundary

Only four production files are in the implementation boundary:

1. `native/guala_core/src/resident_cognitive_formation.rs` — stop manual
   layer-13 co-recruitment while preserving the neuron/state and typed layer-12
   evidence.
2. `native/guala_core/src/virtual_articulatory_body.rs` — couple exact applied
   vocal-body displacement to its fixed acoustic surface and retain bounded
   mechanics.
3. `native/guala_core/src/organism_runtime.rs` — pass the settled body
   consequences, eliminate chronological append from the active path and keep
   authenticated one-field custody.
4. `dsf_ai_service/native_production_app.py` — retain bounded raw hop plans,
   compose pressure before one cochlear pass and remove the pre-drain from all
   intake families.

No Python-to-neuron wrapper signature needs to change: the existing in-flight
getters and authenticated consume call are sufficient. No persistence format,
body axis, neuron, formation, DSF, L0-L4, world law or observer authority is
changed.

All current intake families are affected at the common hop boundary: unattended
world, live camera, camera+mic, grounded tutor voice, card/spoken-card, songs,
offered audio/audiovisual, rendered light, Gutenberg pages, participant/world
actions, vestibular/root motion and returned body consequences. There is no
compatibility route that may retain pre-drain behavior.

## Audit findings that materially help speech

The shell/world audit does not supply a speaking mechanism, but four findings
matter to speech delivery:

1. Sixteen retained action receipts can make a passive world beat cost 282.3
   ms against a 250 ms budget and rewrite about 1.76 MB every beat. That breaks
   real-time hearing/gesture cadence and must be corrected before a speech
   production release.
2. Duplicate retinal, touch, smell, validation and full-world encoding work
   lengthens every sensory hop. It is latency work after the causal voice is
   proven, not a reason to alter voice physics.
3. The pressure-audio cache is count-bounded but must also be byte-bounded
   before speech can produce varying spans.
4. Roughly 28,000 lines of old Python auditory machinery are outside the live
   transduction closure. Speech must use the mounted Rust cochleae and must not
   build on or revive those files.

The crash-orphan persistence wedge is a release blocker because it can freeze
CURRENT and permit unsaved lived state to accumulate. It is not folded into
the speech algorithm. Broad dead-code removal, crypto/helper consolidation and
base64 cleanup follow speech and measured latency repairs; mixing them into the
causal speech change would obscure proof and rollback.

## Mandatory falsifiers before deployment

1. On a newest exact copied body, two naturally occurring typed vocal motors
   must drive different persisted surfaces and yield different spectra.
2. A stalled motor must produce no new acoustic impulse.
3. Sever all motor input after one launch: only stored work may continue, then
   exact rest; no new command or carrier spend.
4. Simultaneous external+self pressure must equal the exact signed sample sum
   before the one cochlear field. Overflow must refuse.
5. One authored hop must cause one native cognition/body advance and one
   cochlear admission, including every intake family.
6. Both mounted ears must hear the exact pressure once. Restart before hearing
   preserves it; restart after hearing never replays it.
7. Removing renderer exposure must not alter self-hearing; severing organism
   motor output must leave silence/rest, never canned speech.
8. Identity, 1,812 neurons, accepted contacts/formations, 153 starting mosaics,
   full seven-field DSF state and learned sensory state must survive byte-exact
   migration/restart checks.
9. Long copied-body and cold-restart soaks must keep RSS, CPU, trace count,
   envelope bytes, world bytes, cache bytes and durable writes bounded beyond
   every prior failure window.
10. No phoneme/word/meaning claim is allowed. Success is controllable varied
    pressure plus ordinary self-hearing. Conversation/first-word evidence must
    later arise from lived tutor interaction and be observed, not declared.

## Single exact next item

Implement the four-file typed spectral-body and one-timeline boundary on this
task-1404 worktree, then run every falsifier above against a fresh clone of the
immutable tick-358454 body before any package or deployment action.

## Implementation discovery — wrapper impact correction

The first current-wheel copied-body run disproved the four-file/no-wrapper
claim before any package or deployment. At tick 358455 the primary unattended
world hop produced real pressure and an ordinary autonomous body action. The
action's returned world/body sources are a second authored physical interval
and must remain coexisting. The existing authenticated self-hearing wrapper
can consume pending pressure only as an ordered trajectory; using it would
turn simultaneous action-consequence sources into false time order. Calling
the ordinary coexisting advance is also correctly refused while self-pressure
is pending.

Therefore the causal boundary is **five** production files, not four. The
fifth is
`dsf_ai_service/glew_runtime/native_resident_organism.py`: it must transport
one explicit `coexisting` boolean through the already-authenticated pending
pressure consume call and validate the same native evidence. Native runtime
uses that boolean only to choose its existing simultaneous-source settlement;
it does not select sound, motor, meaning or cognition. The app supplies true
only for the already-declared coexisting action-consequence interval. No new
method, fallback or second advance is introduced.

The copied-body refusal is retained as a successful falsifier: the candidate
advanced only the disposable clone, refused before seal/publication, and then
repeated exact tick 358455 from its durable predecessor. It exposed the missing
caller impact instead of stalling production. Implementation cannot proceed
honestly without this wrapper correction.

The corrected wrapper then exposed the exact clock mismatch instead of
silently stretching it: `_pcm_hops` lawfully pads every acoustic occurrence to
the mounted 250 ms hop, while the action consequence still declared only the
two instants 0 and 1 ms. Thus a pending 250 ms self-pressure field cannot be
composed into that episode without changing its source clock. The accepted
repair is not to slow the action. Its world transition remains at exactly
1 ms, but its complete post-action sensorium covers the ordinary 250 ms hop:
the before value is retained at 0, the exact successor begins at 1 ms, and the
successor world/body values remain physically present through the rest of the
hop. Raw pressure keeps all 4,000 samples and the 1 ms transition instant is an
additional retained index. This is the same distinction already used for a
fast gesture inside a longer acoustic observation window; it changes neither
the action duration nor its displacement.

## Copied-body falsifiers after the clock correction

Two more refusals were preserved rather than routed around:

1. The first full-hop action build supplied the four displacement coordinates
   as if they were one time trajectory. The mounted source correctly refused
   the changed anatomy. The corrected source keeps four typed coordinates;
   each carries its exact 1 ms movement followed by zero displacement through
   the remainder of the sensorium. Position-like world, optical, chemical and
   thermal successor values remain held after 1 ms; displacement does not.
2. The next copy proved that one 250 ms world sensorium and its exact 1 ms
   proprioceptive sources cannot be declared as equal-duration sources. They
   are instead nested events from the same causal boundary: the motor and
   proprioceptive change completes at 1 ms, while its successor sensorium
   remains present to 250 ms. Native coexistence now settles that set once and
   derives articulatory tissue duration from the longest source. It does not
   repeat the short source, stretch its samples, or create a second cognitive
   turn.

That native settlement then succeeded, but the Python evidence validator still
expected one causal interval per supplied source even in explicit coexistence.
The organism correctly reported one. The wrapper now expects one only when its
authenticated `coexisting_sources` value is true. The failed copy returned to
the exact durable predecessor before the corrected run.

Fresh copy 6 then advanced continuously from tick 358454 through tick 358678
without an intake refusal. Each observed intake used one primary transition and
one coexisting action-consequence transition; the latter consumed the exact
4,000-sample in-flight pressure inside the complete sensorium. RSS remained in
the 1.3 GiB band during this short causal run. This is functional evidence, not
the required long resource soak or restart proof.

The run also caught an observer lie: articulation was assembled before its
coexisting action consequence and therefore published zero self-hearing counts
under a "committed" status. Observation now requires an exact emitted-pressure
SHA/sample-count match, complete consumption, zero remaining tail, and ingress
through all mounted ear ports before it may say self-hearing committed. Aggregate
coexisting neuron changes are labelled aggregate; they are not mislabelled as
sound-only neurons.

## Sequence-law correction after reading the retained history

The initial claim that a new retained sequence level must be added before
speech was incomplete and is withdrawn.  The canonical progression law
forbids an ordered-member array or sequence database, and the closed C-011 and
C-012 sprints already delivered the organism's bounded physical ordering law:

- exact directed sparse transfers may continue across adjacent frontiers;
- a later physical path may recur over the same retained formation route;
- layer-11 ordering transfers are already the only learned preparation that
  can discharge a typed layer-12 motor; and
- the three predecessor frontiers expire rather than accumulating history.

That is sufficient machinery for successive vocal gestures to unfold across
successive lived intervals while persistent tissue motion overlaps them.  It
does not prove that a word has been learned, but it removes the alleged need
for a speech-specific sequence store.  Python causal-motor traces remain
read-only observation and are not promoted into cognition.  No new formation,
tapestry, word, phoneme, grammar, or sequence object will be introduced by
this repair.
