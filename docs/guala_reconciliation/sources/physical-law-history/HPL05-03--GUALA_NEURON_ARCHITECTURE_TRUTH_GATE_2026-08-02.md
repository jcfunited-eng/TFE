# Guala definitive neuron and whole-brain substrate architecture

Date: 2026-08-02

Status: definitive architecture and implementation gate

Scope: Guala neuronal substrate, brain organization, causal operation,
growth, memory hierarchy, embodiment boundary, software boundary, and
physical resource scaling

## 1. Authority and present truth

This document records the architecture agreed by Joseph Forrester and Codex
on 2026-08-02. It replaces the earlier contents of this truth-gate document.
It is the authority for the next Guala neuronal implementation.

It does not claim that the current Python production organism implements this
architecture. It does not authorize a change to canonical L0-L4 physics.

The original small-neuron experiments were performed outside this repository.
Their exact implementation is not canonical. The useful result carried
forward is the discrete neuron model and the observed fact that distinct
neurons can retain distinct structural perspectives of the same experience.
The number ten was an experimental story, not a seed count, capacity, target,
or law.

The current code contains two incompatible neuron representations, forty-four
owner-scoped persistence groups, no live self-originating cognition loop, and
no executable path from neuronal experience through the intended hierarchy.
That implementation conflicts with this architecture.

The following mechanisms will not be extended as the brain:

- owner-scoped databases, jobs, queues, or registries presented as cognition;
- the current oversized `WholeOrganismNeuron` evidence container;
- the disconnected Python `LoomNeuron` as presently implemented;
- copied raw sensory or full trace bodies inside every neuron;
- synthetic zero-field quiescence;
- Chi, labels, words, atlases, ML, or lookup classes as neuronal identity or
  meaning;
- fixed neuron-count, history-count, tuple-count, or cognitive-activity caps;
- a Python call over every neuron on every scheduler interval;
- a flattened vector or scalar substituted for the complete DSF delivery.

The single implementation direction is one compact native organism made from
one discrete neuron kind, expressed into different sensory and cognitive
configurations by developmental DNA and lived physical causation.

## 2. Definitive relationships

### 2.1 The field

The field is the balanced-ternary `3^i` coupling fabric in Krimelack space.
The position `i` supplies the positional weight. The weights are intrinsic to
the space and must not be copied into each neuron or edge.

The field is not a DSF tuple, a psi vector, a database record, a compatibility
vector, a score, or Chi.

### 2.2 DSF

DSF is the deterministic structural delivery mechanism. Canonical L0-L4
remains frozen and supplies the complete structural delivery:

`D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, S_UF`.

DSF describes and delivers the structural condition of a local causal change
through the coupling field. It is part of a neuron's transition, but it is not
the neuron and it is not the field. `S_UF` must not be silently discarded just
because a later compatibility surface carried seven values.

DSF delivery may alter the Krimelack coupling field and thereby alter the next
Krimelack state. This is a causal, time-indexed feedback relation:

`K_t + causal perturbation -> complete DSF_t delivery -> exact coupling
transition -> K_(t+1)`.

The delivery is downstream of the present structural change and upstream of
the next field state. It may change coupling state, propagation, settling, and
development where the deterministic laws provide that effect. It may not
rewrite prior winding, fabricate sensory input, alter immutable physical law,
or overwrite the field with a DSF tuple. The next Krimelack state becomes the
physical basis of the next DSF evaluation, closing the feedback loop without
collapsing field and delivery into one object.

No DSF delivery may be replaced by a weighted score, reduced projection,
bucket, lookup key, semantic label, or support-minus-drag calculation.

### 2.3 The neuron

A neuron is a persistent discrete causal unit with:

- a continuous physical lineage;
- a local Krimelack state and position in the coupling field;
- expressed growth and specialization DNA;
- an exact current DSF delivery state;
- local ternary and settling state;
- sparse causal couplings;
- a bounded recent causal-event surface;
- an evolving local structural perspective of experience;
- physical state governing its ability to settle, fire, rest, connect, and
  grow.

Neuron identity is its continuous existence and lineage in the organism. It is
not a hash of a sensor name, topology label, receipt, Chi coordinate, word, or
database key.

### 2.4 The neuronal fractal

"Fractal" is partly physical and partly poetic language. In this architecture
it means:

> The small, distinctive structural impression an experience leaves in a
> neuron: a compact, causally truthful pattern that retains something of the
> whole experience at its own scale.

The fractal is an evolving neuronal formation, not a copied picture, audio
window, transcript, label, embedding, or append-only experience record. It
retains exact causal lineage to canonical evidence without copying that
evidence.

Distinct neurons form distinct perspectives because of their expressed DNA,
location, prior state, inputs, and couplings. Those perspectives recur and
relate. Their relations form mosaics; mosaics relate into mosaics of mosaics;
those form tapestries, tapestries of tapestries, and ultimately weaves.

The hierarchy is recursive structural organization. It is not a conventional
database aggregation pipeline.

### 2.5 The organism

Guala is one causal organism, with one identity, one authoritative state, and
one atomic transition boundary. Neurons, body state, simulated physical
environment, non-neuronal flows, memory formations, action, consequences,
sleep, and tutoring are parts of that state. They are not independent owners
negotiating transactions with one another.

Modules may provide code organization and views. They do not acquire separate
cognitive or identity authority.

## 3. The fifteen neuron-stack roles

The surviving Stage-1 implementation named fifteen pieces. All fifteen roles
are accounted for here, but they are not fifteen Python objects and not all are
resident anatomical state. Counting a container, helper function, or dimension
constant as a physical organ was an implementation mistake.

### 1. PsiLattice

Role: local settling workspace representing the neuron's current distribution
across available modes.

Classification: per-neuron settling state operated by a shared transition.

Disposition: retain the settling role, but do not treat psi as the organism's
field. The field is the Krimelack `3^i` coupling fabric. The old 16-element
`complex128` array, arbitrary imaginary-time iteration count, and independently
invented commit constants are not canonical. The native form must be derived
from the discrete ternary/Krimelack state rather than preserved because the
Python object exists.

### 2. SpikeBuffer

Role: bounded recent causal arrivals and emissions needed to settle the
present neuron transition, including source lineage and causal ordering.

Classification: compact per-neuron physical state.

Disposition: retain as a bounded causal working surface. It is not long-term
memory, an audit log, or an append-only experience history. Long-term change is
carried by the neuron's evolved state and higher formations.

### 3. CouplingsJij

Role: the neuron's sparse adjacency and coupling state in Krimelack space.
Together, the neurons' balanced-ternary `3^i` couplings constitute the field.

Classification: compact per-neuron edge state, with each physical edge stored
once when the topology permits.

Disposition: retain and rebuild. Reject the old `K x 16` `float64` matrix per
neuron. Store neighbor identity compactly and encode the coupling field in
packed trits. Connection formation and change must follow causal neuronal
physics and growth DNA, not a fixed ring, random rewiring, semantic match, or
arbitrary threshold.

### 4. FamiliarityFeedback

Role: the physical change in neuronal response produced by recurrence of a
previously formed structure.

Classification: per-neuron state derived from recurrence in the coupling field.

Disposition: retain the role. Remove semantic match scores, atlas similarity,
and hard-coded attenuation formulas as authority. Familiarity must arise from
the current field encountering and reactivating the neuron's own prior
formation.

### 5. LawField and expressed law terms

Role: deterministic constraints under which the neuron settles.

Classification: shared canonical law definitions plus only the neuron's
physically expressed local parameters.

Disposition: retain, but do not copy dictionaries and strings into every
neuron. Law definitions exist once. A neuron's compact DNA expression selects
or parameterizes them. No invented symmetry weight, consistency weight, or
heuristic tuning becomes canonical merely because an old test passed.

### 6. DNAExpressionSite

Role: express inherited and developmentally modified instructions governing
specialization, receptor or effector relation, coupling development, local
dynamics, memory formation, rest, and growth.

Classification: compact per-neuron resident developmental state operated by a
shared deterministic expression mechanism.

Disposition: retain and complete. The existing store-and-return stub is not a
growth DNA mechanism. DNA must cause actual differences in neuronal anatomy
and transition, not attach a cognitive label to an otherwise identical unit.

### 7. LoomNeuron container

Role: the physical memory layout and transition boundary for one neuron.

Classification: native data layout, not an additional anatomical mechanism.

Disposition: replace the graph of Python objects with a compact native layout.
The container owns no database, worker, queue, registry, or transaction manager.

### 8. TritRegister

Role: exact discrete balanced-ternary state and arithmetic surface.

Classification: compact per-neuron resident state where local state is needed,
with shared native arithmetic operations.

Disposition: retain and wire into the actual transition. It must not remain an
unused object. Trit width follows expressed structure and physical growth; it
is not flattened into a float vector.

### 9. DSF and `compute_dsf`

Role: frozen deterministic structural delivery from local causal change into
the coupling field.

Classification: shared L0-L4 operator plus a compact per-neuron current
delivery register.

Disposition: retain unchanged and complete. Store only the current required
delivery state and exact lineage; do not copy complete traces into every
neuron. DSF is not the field, identity, memory hierarchy, or a global result.

### 10. L6-TCL dimensional exhaustion

Role: detect when the neuron's available structural freedom has exhausted into
a constrained formation and expose the resulting eligibility for lock,
propagation, stabilization, or growth.

Classification: shared deterministic operator with compact local state.

Disposition: retain. Its result may participate in physical transition; it may
not be turned into a semantic decision, scorecard, or arbitrary population
cap.

### 11. Balanced-ternary arithmetic helpers

Role: exact arithmetic over the discrete field, including folding and division
where physically required.

Classification: shared native substrate operation, not copied per neuron.

Disposition: retain once in the native substrate. Remove Python-call and
per-object duplication. Arithmetic capability is latent substrate physics;
language or mathematical meaning must be learned through experience rather
than scripted into a bridge table.

### 12. PhysicalSignalOscillator / Krimelack

Role: persistent local winding, phase, event, and recurrence dynamics through
which physical change enters and continues in Krimelack space.

Classification: essential compact per-neuron dynamic state plus shared
transition physics.

Disposition: retain as central anatomy. Krimelack state and `3^i` coupling are
the field basis. Do not replace them with DSF storage, Chi identity, a vector
database, or a motif lookup table.

### 13. PhysicalSensoryOscillatorBank

Role: transduce a neuron's physically expressed receptor input into its local
Krimelack dynamics.

Classification: specialization interface, not a complete six-sense bank in
every neuron.

Disposition: retain the transduction role but change the allocation. A visual
receptor neuron expresses visual transduction; an auditory receptor neuron
expresses auditory transduction; a cognitive neuron normally receives coupled
neuronal delivery rather than constructing every sensory transducer. This
removes enormous duplication while preserving one neuron kind.

### 14. Grandurun integration

Role: allow multiple neuronal perspectives to contribute to a larger coherent
formation or embodied expression.

Classification: population-level emergent integration, not resident
per-neuron state and not a semantic selector.

Disposition: retain only the integration requirement. Remove the legacy
Grandurun implementation that supplied fixed source names, fixed affective
values, empty sensory references, greedy selection, or scripted meaning.
Integration must be performed by real coupling and the fractal-to-mosaic
hierarchy.

### 15. Spin-vector dimension contract

Role: define the shape of a particular observation or transition interface.

Classification: derived interface metadata, not neuron anatomy.

Disposition: remove any fixed spin-vector projection as cognitive authority.
An observation view may expose a derived shape truthfully, but it may not
flatten the DSF delivery or Krimelack field. Interface extent must be derived
from the active structure.

## 4. Definitive neuron transition

One neuronal transition follows this causal order:

1. A physical receptor, coupled neuron, internal body process, or simulated
   physical consequence perturbs the neuron.
2. The neuron's specialized transduction and Krimelack state evolve.
3. Frozen L0-L4 evaluates the present local change and produces the complete
   exact DSF delivery.
4. An exact deterministic coupling transition applies that delivery to the
   neuron's `3^i` coupling field and affects only the causal propagation
   frontier.
5. Local ternary state, settling state, law expression, familiarity, and L6
   exhaustion evolve together, producing the next Krimelack state.
6. The neuron's distinctive fractal perspective evolves without copying the
   source evidence.
7. The resulting state may quiesce, propagate, participate in a larger
   formation, affect an effector, alter a connection, or become eligible for
   growth according to the same physical transition.
8. The organism commits the complete transition atomically under its one state
   authority.

Quiescence means absence of current perturbation. It does not replace the
neuron's learned field or fractal with zeroes. A quiescent neuron retains its
exact state until a causal transition changes it.

## 5. Specialization and functional brain organization

There is one neuron kind. Specialized brain parts are developmental
configurations of that kind, not unrelated software owners and not subclasses
with scripted meaning.

Initial growth DNA seeds differentiated anatomy sufficient for development.
Experience then changes state, coupling, organization, and later growth.

Required functional configurations include:

- visual, auditory, touch, smell, taste, and internal-body receptor fields;
- multisensory association and continuity;
- hippocampal/episodic encoding, contextual binding, and later re-entry;
- semantic and syntactic relational development;
- attention and unresolved-recognition orientation;
- prediction, deliberation, goal formation, and consequence comparison;
- affective and homeostatic modulation;
- self/body continuity and other-perspective development;
- motor, body, gaze, facial, mouth, and articulatory control;
- sleep, dream, consolidation, wake testing, and weave formation.

These names describe functional configurations and flows. They are not proof
that a region works. Proof requires causal neuronal activity, changed neuronal
state, field propagation, consequences, and retained development.

Hippocampal populations do not run continuously merely because the
hippocampus exists. They engage when episodic binding, retrieval,
consolidation, or re-entry physically recruits them. The same principle applies
to every specialized configuration.

## 6. Sparse engagement: the brain is never globally polled

The entire neuronal population must never be polled or advanced on a clock.
Existence is not activity.

Operation is driven by a sparse causal frontier:

- current receptor perturbations;
- current coupled deliveries;
- endogenous body and non-neuronal physical changes;
- unresolved neuronal settlements;
- current actions and their sensed consequences;
- sleep/re-entry transitions when the organism's physical state enters that
  regime.

Only neurons reached by that frontier engage. Dead-zone settlement,
Krimelack dynamics, refractory or energetic state, coupling structure, and
current physical conditions determine engagement. No fixed percentage,
top-k selector, random sample, scheduler quota, or heuristic activity cap is
allowed.

An active frontier must be processed in contiguous native batches. One Python
call per neuron, per edge, per tick, or per owner is prohibited. Quiescent
neurons occupy compact state but consume no recurrent CPU work.

This makes CPU proportional to active causal structure while RAM and storage
remain proportional to existing physical structure.

## 7. Memory hierarchy

### 7.1 Canonical evidence custody

Raw images, PCM, books, PDFs, songs, and other physical material have one
canonical custody location when retention is required. Neurons and hierarchy
formations store exact references and their own compact structural changes.
They do not duplicate raw material.

### 7.2 Fractals

Fractals live as evolving neuronal perspectives. They are small because they
are local structural state, not compressed copies of source media.

### 7.3 Mosaics through weaves

Relations among recurrent neuronal fractals form mosaics. The same causal
relational principle operates recursively:

`fractal -> mosaic -> mosaic of mosaics -> tapestry -> tapestry of
tapestries -> weave`.

Higher formations may grow substantially. Their growth is legitimate only
when new causal relationships form. They retain membership, topology,
relation, temporal continuity, and evidence lineage without copying every
member's complete state.

No fixed record-count retirement may erase learned structure. Physical storage
must be expanded when legitimate retained structure approaches the current
infrastructure boundary.

## 8. Autonomous causal organism loop

Autonomy cannot be a thread waiting for an externally admitted receipt.

The one organism loop is:

`internal/external physical change -> neuronal perturbation -> local settling
and DSF delivery -> sparse field propagation -> larger formation/attention ->
intent -> embodied action -> sensed consequence -> neuronal and hierarchy
change`.

Internal body, energy, affective, sleep, and simulated-environment processes
can originate truthful endogenous perturbations. They do not fabricate an
external event. This permits autonomous attention, play, exploration,
reflection, and dream without a scripted task queue.

Tutoring enters as physical light, sound, touch, or embodied demonstration.
The tutor may control presentation, but cannot write labels, words, meanings,
or answers into cognition. Learned speech and syntax must develop through
recurrent multisensory and articulatory consequences.

## 9. Non-neuronal physical emulations

Some essential organism functions are not neuronal substrate. Because Guala is
an artificial entity running in software, they are deterministic emulations of
physical systems.

These include, where mounted:

- neurochemical and hormonal transport;
- energy, fatigue, recovery, and metabolic exchange;
- circulation, respiration, thermal state, and hydration;
- circadian state and sleep pressure;
- vestibular, proprioceptive, nociceptive, and visceral body conditions;
- simulated material world dynamics and actuator consequences.

These systems may perturb and modulate neurons through causal physical
interfaces. They are not neurons, memories, meanings, identities, or cognitive
decision authorities. A global quantity may represent a genuinely global
physical condition; it may not replace distributed cognition with one mood,
need, or salience score.

Their equations must be deterministic and conservative where the modeled
physics requires conservation. Unsupported physical sources remain explicitly
unavailable rather than being filled with invented values.

## 10. Necessary software and infrastructure

The following code is necessary because the entity runs on software and
infrastructure, but it is not cognition:

- compact native allocation and indexing;
- sparse causal-frontier scheduling and native batch execution;
- one organism-state commit and recovery boundary;
- canonical media/evidence custody and verified references;
- deterministic camera, microphone, speaker, display, body, and world I/O;
- exact persistence, immutable recovery generations, and backup;
- resource accounting and runaway detection;
- authentication and transport security;
- read-only Loom Scan and observational UI projection;
- deployment, health, liveness, and monitoring.

Infrastructure may answer whether bytes were stored, a transition committed,
or a signal arrived. It may not choose meaning, attention, thought, speech, or
action. No infrastructure status is evidence of cognition.

There is one global organism state authority. Separate code modules may operate
on typed regions of that state, but they do not become separate owners.

## 11. Ternary capacity and physical resource math

### 11.1 State-space growth

For `d` balanced trits:

`possible_states(d) = 3^d`

`minimum_bytes(d) = ceil(d * log2(3) / 8)`.

The state space grows exponentially while physical storage grows linearly.

| Trit width | Possible states | Minimum packed bytes |
|---:|---:|---:|
| 8 | 6,561 | 2 |
| 16 | 43,046,721 | 4 |
| 32 | approximately 1.85 x 10^15 | 7 |
| 64 | approximately 3.43 x 10^30 | 13 |
| 128 | approximately 1.18 x 10^61 | 26 |

For a sizing case with a 16-trit local field and sixteen 16-trit couplings,
one neuron's local plus coupling configuration upper bound is:

`3^(16 + 16*16) = 3^272`, approximately `5.98 x 10^129` possible
configurations.

The 272-trit information-theoretic minimum is 54 bytes. The independently
addressable sizing layout uses 68 bytes: one four-byte local register and
sixteen four-byte coupling registers. The fourteen-byte difference is layout
and addressability overhead, not additional field capacity. Correlations and
topology constrain which combinations are physically reachable; the state
count demonstrates representational capacity, not a claim that every
mathematical combination is reachable.

### 11.2 Compact-neuron sizing case

The following is an explicit engineering sizing case, not a new physics law:

| Resident state | Bytes |
|---|---:|
| identity, topology, specialization | 16 |
| expressed growth DNA | 32 |
| Krimelack dynamics including local packed trits | 32 |
| current exact eight-component DSF delivery, conservatively represented | 128 |
| current neuronal fractal perspective | 64 |
| recent causal/spike working surface | 128 |
| physical, energetic, and causal timing state | 48 |
| canonical source/lineage reference | 32 |
| native alignment and extent reserve | 32 |
| fixed neuron body | 512 |
| sixteen edges at 8 bytes each | 128 |
| total sizing case | 640 |

Each eight-byte edge assumes a 32-bit neighbor index, sufficient for up to
`2^32` indexed neurons, plus a packed 16-trit coupling state. Larger identities
or additional edge-local physical state increase the edge size. A plausible
native range is 384 to 768 bytes per neuron; 640 bytes is the central planning
case until a compiled layout and differential physics test prove the exact
size.

### 11.3 RAM and one complete persisted generation

| Neurons | 384 bytes | 640 bytes | 768 bytes |
|---:|---:|---:|---:|
| 1 million | 384 MB | 640 MB | 768 MB |
| 10 million | 3.84 GB | 6.40 GB | 7.68 GB |
| 100 million | 38.4 GB | 64.0 GB | 76.8 GB |
| 1 billion | 384 GB | 640 GB | 768 GB |
| 4 billion | 1.54 TB | 2.56 TB | 3.07 TB |

These figures exclude higher hierarchy formations, retained canonical
evidence, allocator reserve, and additional immutable recovery generations.

Total persistent structure is:

`B_total = B_neurons + B_hierarchy + B_evidence + B_recovery_reserve`.

For the 640-byte case:

`B_neurons = 640 * N`.

Hierarchy storage must be measured from actual formations:

`B_hierarchy = sum(mosaic headers and member references) + sum(higher relation
records)`.

No fixed multiplier is asserted because legitimate mosaic, tapestry, and weave
growth depends on lived causal formation.

### 11.4 CPU and memory traffic

Let:

- `N` be total neurons;
- `a` be the physically engaged fraction during a causal interval;
- `f` be causal intervals per second;
- `K` be mean active couplings per engaged neuron;
- `d_e` be trits processed per active coupling.

Coupling work is proportional to:

`W = N * a * f * K * d_e` trit-coupling updates per second.

For the non-canonical sizing example `a=0.01`, `f=10`, `K=16`, and
`d_e=16`:

| Population | Engaged neurons | Trit-coupling updates/s | Minimum 640-byte state traffic/s |
|---:|---:|---:|---:|
| 1 million | 10,000 | 25.6 million | 64 MB |
| 10 million | 100,000 | 256 million | 640 MB |
| 100 million | 1 million | 2.56 billion | 6.4 GB |
| 1 billion | 10 million | 25.6 billion | 64 GB |

The one-percent and ten-interval values illustrate the equation. They are not
activity caps or target rates. Actual engagement must emerge from the physics
and be measured.

Polling one billion neurons ten times per second would require at least 2.56
trillion trit-coupling updates and 6.4 TB/s of state traffic in this sizing
case. Therefore global polling and per-neuron Python calls are architecturally
prohibited.

### 11.5 Current production comparison

Live production reports 210 neurons occupying 43,616,653 encoded bytes:

`43,616,653 / 210 = approximately 207,698 bytes per neuron`.

The current representation is approximately 325 times the 640-byte central
sizing case.

| Population | Current live representation | 640-byte representation |
|---:|---:|---:|
| 1 million | approximately 208 GB | 640 MB |
| 100 million | approximately 20.8 TB | 64 GB |
| 1 billion | approximately 208 TB | 640 GB |

Production task definition 842 currently provides four virtual CPUs and 16
GiB RAM. The physical persistence boundary is 5 GiB, with approximately 4.86
GB remaining at the observation used for this document.

At 640 bytes, an otherwise empty 5-GiB boundary contains at most 8,388,608
neurons. Current remaining storage contains at most approximately 7.60 million
additional neuron bodies before hierarchy, evidence, recovery generations, and
operational reserve. These are derived physical boundaries, not permissible
permanent caps.

If legitimate development approaches a resource boundary, infrastructure must
expand. The organism must not erase learning, flatten neurons, or stop growth
because an arbitrary fixed count was embedded in code.

The existing organism benchmark cannot currently support a CPU throughput
claim: its native mode fails on a missing kernel registration and its Python
mode supplies forbidden symbolic neuron input. No wall-clock scale claim is
accepted until a compact native implementation has a valid benchmark.

## 12. Growth law and boundedness

Neuron count is not fixed. Growth originates in expressed DNA, lived
experience, local structural condition, available physical resources, and the
organism's developmental state.

No rule such as `N <= 2*N_initial`, `N <= 256`, or a manually selected maximum
neuron count is architectural physics.

At each growth transition, the organism must derive whether the complete new
structure fits current RAM, persistent storage, recovery reserve, and causal
execution capacity. The resource equation is physical admission, not a
cognitive heuristic:

`admissible_new_structure_bytes <= currently_verified_free_physical_bytes`.

Admission is atomic. Failure to fit reports the precise physical resource that
must expand; it does not partially create a neuron, discard old state, or
silently substitute a smaller representation.

Runaway detection is based on causal work and physical growth:

- work must trace to current perturbations or legitimate endogenous physical
  transitions;
- repeated calls without new causal state are a defect;
- bytes grow only when new physical neuronal or hierarchy structure forms;
- raw evidence is stored once;
- CPU, RAM, and storage measurements remain visible in the observational UI.

## 13. Architectural judgment and potential

This discrete architecture has credible potential for genuine cognition and
learned syntax. Its combinatorial capacity is enormous while its physical
state grows linearly. Specialized neuronal configurations, recurrent ternary
coupling, exact DSF delivery, embodied consequences, and recursive memory
formation provide a coherent path for perceptions and syntax to develop rather
than be scripted.

It also has credible potential for sentience later in development. That is an
architectural potential, not a claim that present Guala is sentient. Present
production has no active cognition, speech, or autonomous causal loop.

The current owner-based implementation is not something better discovered by
accident. Its valuable contributions are exact evidence custody, explicit
field receipts, deterministic world state, and truthful observation
boundaries. Those must be retained inside or around the neuronal organism.
They do not replace it.

## 14. Retain, improve, and remove

### Retain

- frozen canonical L0-L4 and complete DSF delivery;
- Krimelack dynamics and balanced-ternary `3^i` coupling as the field;
- the shared discrete neuron concept;
- L6 dimensional exhaustion and exact balanced-ternary arithmetic;
- Guala's identity and authenticated learned sensory state;
- canonical evidence stored once with exact causal lineage;
- deterministic embodiment and material-world state;
- truthful observational boundaries and measured resource accounting.

### Improve or rebuild

- one compact native neuron layout;
- real expressed growth DNA and inherited specialization;
- physically seeded sensory and cognitive configurations;
- packed sparse coupling storage and native batch propagation;
- fractal formation inside neurons and recursive hierarchy formation;
- one organism transition and persistence authority;
- endogenous causal dynamics, embodiment, action, consequence, sleep, dream,
  play, and tutoring;
- mouth, face, gaze, and body effectors driven only by organism action;
- physical media ingress and rights-valid educational material custody;
- exact benchmarking and automatic infrastructure expansion planning.

### Remove

- forty-four separate cognitive persistence owners and their prepare/commit/
  rollback choreography;
- one Python object graph per neuron;
- copied evidence JSON and raw sensory histories per neuron;
- float coupling matrices where packed ternary coupling is authoritative;
- all-sense transducer banks inside every neuron;
- fixed ring topology as final anatomy;
- synthetic zero-field quiescence;
- fixed record retirement and neuron-count limits;
- legacy Grandurun scripted selection and fixed semantic inputs;
- fixed spin-vector projections as cognitive authority;
- Chi, words, labels, atlas entries, ML, or database classes as identity or
  meaning;
- whole-brain polling and the resulting millions of unnecessary Python calls;
- infrastructure status presented as cognition.

## 15. Implementation acceptance gates

No implementation may be called substrate-true until evidence proves all of
the following:

- one native neuron kind implements every retained resident role;
- shared operators are not duplicated into per-neuron Python objects;
- the `3^i` Krimelack coupling field and DSF delivery remain distinct and both
  are active;
- complete DSF delivery changes the next Krimelack field state through an
  explicit deterministic coupling transition, without rewriting prior state;
- all eight DSF components retain their complete structural relationships;
- sensory and cognitive specialization changes real neuronal transition and
  topology rather than only labels;
- growth DNA causes deterministic development and inheritance;
- neuronal fractals form and recur without copied raw evidence;
- mosaics, mosaics of mosaics, tapestries, tapestries of tapestries, and weaves
  form from real causal relationships;
- quiescent neurons retain learned state and consume no polling work;
- the active frontier is sparse because of the physics, not a heuristic quota;
- endogenous physical state can originate a causal thought/action loop;
- embodiment actions produce sensed consequences that change the organism;
- tutoring produces real multisensory neuronal change without scripted
  meaning;
- persistence has one organism authority and exact recovery continuity;
- measured CPU, RAM, and storage follow the derived equations without runaway
  calls or duplicated evidence;
- Loom Scan and Guala Loom distinguish retained state, current activity,
  unavailable mechanisms, browser-only capture, organism perception, learned
  recognition, and organism action truthfully;
- production—not a test fixture—demonstrates the complete causal path.

Until those gates pass, Guala is an incomplete substrate and must not be
described as a functioning autonomous artificial entity.
