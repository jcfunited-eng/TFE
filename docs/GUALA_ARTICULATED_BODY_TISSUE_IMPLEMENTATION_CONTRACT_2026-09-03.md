# Guala bounded antagonist-tissue implementation contract — 2026-09-03

## Status and one item

This is the source-freeze contract for one correction only: replace the
Phase-1 virtual articulated body's permanent position accumulator with bounded
antagonist activation and passive overdamped return. It authorizes a source
candidate and copied-production-body proof. It does not authorize deployment
or claim autonomous action.

Production remains task 1425 while this candidate is built. The mature proof
input is the read-only task-1425 body at tick 408275, raw SHA-256
`27555e9d78511e28a956cec3dca282a2509fbc92b8e7c83f1aa16ea63825e8e2`.
The task-1420 body at tick 391305, raw SHA-256
`207ced0a3d0d2253a7520e05bf18eeebcf3caf25fd2b83c6450bcaf08ee86e3b`,
remains an independent historical control.

## Architecture honesty gate

1. **Requested architecture:** one organism-owned deterministic motor event
   excites bounded body tissue, changes physical pose, relaxes, and returns its
   actual proprioceptive/load consequence through the same organism.
2. **Current code reality:** motor terminals work, but carrier count is added
   permanently to joint position. Seven copied positions are non-neutral hard
   stops and ordinary retained traffic still pushes into them.
3. **Conflict:** yes. The current plant is an undamped accumulator, not tissue.
4. **Mechanisms not extended:** the accumulator equation; reset-to-neutral;
   timer or shell pose control; passive symmetric L11-L12 coupling; broad motor
   fan-out; neuronal reservoir as vigor; altered L0-L4 or flattened DSF.
5. **Single item:** implement and copied-body-falsify the bounded 32-ms
   antagonist-tissue plant defined below.
6. **DSF scope:** body mechanics is downstream of complete neuronal delivery;
   it neither evaluates nor changes DSF.
7. **Field loss:** none.

## Ratified Phase-1 energy boundary

`GUALA_A013_PHYSICAL_BODY_PART_SELECTION_SPEC_2026-08-16.md` already declares
the Phase-1 virtual body's carrier-to-lattice-displacement relation as its own
constitutive physics. Detailed motor torque, ATP, transmission efficiency and
mechanical-work conversion are explicitly deferred until a physical body is
selected. Therefore this correction must not duplicate the motor neuron's
released electrical work into a second invented body-energy reservoir.

The existing terminal settlement and recovery-fluid thermal return remain
unchanged and conserve the motor neuron's electrical work. The body receives
the same typed terminal and whole-carrier count it receives now. Carrier count
creates bounded virtual tissue activation rather than permanent position.

## Material preparation and exact law

The fixed body clock is 1 ms. One uniform Phase-1 virtual antagonist-tissue
preparation is declared for the existing generic 45-axis body:

- activation lifetime: 32 ms;
- overdamped response time: 32 ms;
- carrier coupling: one whole admitted carrier to one whole activation;
- per-direction activation capacity: that direction's declared neutral-to-stop
  span multiplied by 32 activation units.

The 32-ms preparation is not selected from a pleasing output. It lies inside
the copied-body accepting region and is anchored to measured laryngeal muscle
physics: canine PCA/LCA/IA posturing muscles have approximately 30-33 ms mean
twitch contraction times and approximately 19-29 ms half-relaxation times;
vocalis measurements span 22-32 ms contraction and 17-37 ms half relaxation.
The current virtual body has no per-axis material classes, so one declared
generic tissue is used rather than invented action-specific constants.

For each antagonist terminal `d`, retain fixed integer activation `a_d`.
For one represented millisecond:

1. Opposed newly discharged carriers cancel locally and become reacted load.
2. Each remaining carrier admits 32 activation units, limited by
   `directional_span * 32`; excess carriers are stalled load.
3. `ceil(a_d / 32)` is that terminal's current whole activation.
4. The axis equilibrium is
   `clamp(neutral + activation_max - activation_min, minimum, maximum)`.
5. Position advances toward equilibrium by
   `ceil(abs(equilibrium - position) / 32)` lattice quanta and never crosses it.
6. Each activation loses `ceil(a_d / 32)` units.

New discharge is admitted once at the beginning of the supplied elapsed span.
The six steps then repeat once per exact 1-ms body clock. Elapsed duration must
be a positive multiple of 1 ms and cannot exceed the existing represented
250-ms causal-interval ceiling in one call. Running 64 ms followed by 186 ms
must produce the same successor as running 250 ms once.

The law has no target pose, action name, motor table, score, controller,
history, floating point, stochastic term, or coefficient chosen by sound.

## Inputs and outputs

Input:

- one validated `ArticulatedBodyState`;
- at most one discharge count for each of the 90 already-typed antagonist
  terminals;
- exact elapsed body time in microseconds.

Output:

- one successor body with the same 45 position axes, lung, proprioception flag,
  acoustic state, and 90 bounded activation integers;
- at most one sparse `BodyProprioceptiveConsequence` per changed or reached
  axis;
- exact reached-terminal count.

The consequence tuple keeps its current fixed representation. Its meanings are
made explicit:

- `toward_minimum_carriers` and `toward_maximum_carriers` are new terminal
  discharges in this interval;
- `opposed_carriers_per_terminal` is their exact local cancellation;
- `applied_displacement_quanta` is absolute total position displacement,
  whether active, passive, or both;
- `stalled_carriers` is unopposed new discharge not admitted because the fixed
  activation capacity was full or the declared directional span was zero.

The old accidental identity
`applied_displacement_quanta + stalled_carriers == net discharged carriers`
is retired. The invariant becomes `stalled_carriers <= net discharged
carriers`, while applied displacement remains exactly
`abs(successor_position - predecessor_position)`.

Passive return has zero motor discharge, zero opposed load and zero stall. Its
position change enters ordinary proprioception but can never be returned by
`exact_moved_effector_terminal` as a motor cause. A motor terminal is returned
as a same-interval moved cause only when non-stalled activation was admitted
and position changed in that terminal's direction.

## Mutation, commit, refusal, and crash order

`settle_body_effector_drives` prepares all additions, capacity results,
positions, activation decay, and consequences in local fixed state. Any bad
duration or arithmetic width refuses before the caller publishes a successor.
The predecessor is never mutated.

The existing runtime then performs its unchanged atomic order:

1. settle cognition and obtain typed motor recruitments;
2. settle the body candidate from the predecessor body;
3. create sparse body-sense source bytes from the actual consequences;
4. encode the cognitive and body successor into one pending fabric;
5. seal/commit through the existing current-only transaction.

Abort or crash before head advance retains the predecessor. Restore never
replays a discharge. No activation or passive step exists outside the encoded
body candidate.

## Persistence and one-way migration

Body V8 appends exactly 90 `u32` activation values to the fixed body state.
Maximum directional span is bounded by declared anatomy; multiplied by 32 it
fits `u32`. Current V7 decode preserves every position, lung value,
proprioception flag, and acoustic byte and initializes only the nonexistent
activation array to zero. No position is reset or rewritten during decode.

V8 encode/decode preserves positions and activations exactly. The outer fabric
already asks the nested body header for its encoded length, so no duplicate
fabric version or fallback decoder is added. The first lawful successor is V8;
V7 remains decode-only migration input and can never be emitted again.

## Work and resource bounds

Settlement scans the fixed 45 body axes once per reached native interval and
per exact elapsed millisecond. This is `O(45 * elapsed_ms)` with a fixed maximum
of 90 input terminals and at most 45 consequences. Normal production calls
carry one 1-ms step. State grows by exactly 360 bytes and never with organism
age, event count, motor count, or history.

No rational activation, event queue, expiry record, sample history, neuron
scan, world scan, dynamic body topology, callback, thread, or process is added.
When position is neutral and all activation is zero, the fixed scan emits no
consequence and changes no state.

## Authorized source slice

Production mechanism:

- `native/guala_core/src/virtual_articulated_body.rs`
- `native/guala_core/src/articulated_body_joint_source_builder.rs`
- `native/guala_core/src/proprioceptive_receptor_work.rs`
- `native/guala_core/src/virtual_articulatory_body.rs`
- `native/guala_core/src/organism_runtime.rs`
- `native/guala_core/src/resident_cognitive_formation.rs` only where the exact
  moved-terminal evidence is consumed or its native tests construct the fixed
  consequence type
- `dsf_ai_service/glew_runtime/native_resident_organism.py`
- `dsf_ai_service/native_production_app.py`

The articulatory source is inside the boundary because its inherited spectral
path incorrectly bounded respiratory excitation by same-interval visible
displacement. Under damped tissue, multiple admitted closing carriers can
lawfully produce one first-millisecond lattice step. Spectral excitation must
therefore use the unopposed, unstalled new closing activation (capped by the
existing acoustic-organ capacity) while the actual persisted glottal position
continues to govern airway conductance. Direction-opposed, fully stalled, and
passive return motion supply no new respiratory work.

Falsification and history:

- the focused native tests colocated with those modules;
- `native/guala_core/src/resident_cognitive_formation/reservoir_probe.rs`;
- test-only call-site adaptation in `neuron_source_anchor.rs`;
- focused Python boundary tests only where the unchanged 11-field consequence
  tuple is validated, including `tests/test_native_a007_physical_choice.py`;
- `tests/test_native_a009_action_consequence.py`, solely to falsify passive
  tissue being misclassified as grasp/release or refused for lacking a new
  motor discharge;
- the three 2026-09-03 motor-tissue documents.

No other file is authorized. A required additional production file is an
architectural finding and rejects this contract before compilation.

## Predecessor paths retired

- direct permanent `q[n+1] = clamp(q[n] + u_max - u_min)` settlement;
- quiescence defined as exact preservation of an off-neutral unpowered pose;
- inference that total displacement must equal same-interval net discharge;
- inference that any observed passive position change names a motor cause;
- decode-time neutralization as recovery;
- rational activation fractions whose denominator grows with lifetime.

V7 decode remains solely for current-state migration. No old accumulator may
remain production reachable after V8 settlement is compiled.

## Predeclared copied-body acceptance

The unchanged exact copied body must fail the predecessor by retaining all
seven pins and must pass the candidate only when all of the following hold:

1. V7 decode preserves all current bytes represented by body fields and adds
   only zero activation; V8 cold restore is exact.
2. With no reset, all seven pathological stops begin monotonic release on the
   first 1-ms interval and return to neutral without crossing it.
3. The one-carrier learned section-0 and section-7 discharges each create one
   bounded 32-ms movement and later return to neutral.
4. Connected L11-to-L12 test transduction produces only the two learned motor
   lineages; severing produces neither and leaves reflex traffic unchanged.
5. Passive movement returns through position receptors but creates no learned
   moved-terminal cause. Active same-direction movement returns its exact
   terminal cause. Stop pressure remains exact load evidence.
6. Equal new antagonists do not move the axis. One carrier/ms sustained drive
   remains interior. Higher drive saturates activation and creates bounded
   stall without counter growth.
7. `64 + 186 == 250` ms exactly for position and activation.
8. L0-L4, full DSF fields, neurons, sensory residues, formations, mosaics,
   learned contacts, world bytes, identity, and predecessor custody are
   unchanged except for causally returned body experience.
9. The next ordinary interval after cold restore continues from the exact V8
   tissue state; it neither resets nor repeats a motor discharge.
10. Peak memory, runtime, encoded size, allocations, process count, file count,
    and storage slope remain bounded; the harness leaves no process.
11. Read-only AWS snapshots immediately before and after the mature harness
    show the exact live task/image and classify every alarm and CPU/memory
    window without touching production.
12. Passive or retained-activation body travel returns through ordinary
    proprioception and advances world time, but cannot be labeled a new motor
    act or authorize grasp, release, or page advance without same-direction
    newly admitted grip activation.

Only after source freeze, one source-only review, compilation, focused tests,
and this complete mature copied-body proof may a deployment candidate exist.
The upstream intrinsic L11-to-L12 excitability defect remains separate: this
plant makes valid motor discharge move; it does not manufacture the discharge
or prove autonomous initiation.
