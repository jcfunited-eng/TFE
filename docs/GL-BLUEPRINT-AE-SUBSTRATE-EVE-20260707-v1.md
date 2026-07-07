# GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v1

**doc_id:** GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v1
**Author:** Eve
**Ordered by:** Joe (2026-07-07 session)
**Status:** Canonical blueprint. Referenced across chats. Supersedes prior architectural documents that conflict with what follows.
**Life expectancy:** Current until superseded by an explicit v2. All observation and dispatch docs written against this blueprint reference it by doc_id.

---

## 1. Purpose and commitment

This blueprint defines the architecture of GualaLoom's Artificial Entity substrate. It replaces the discretized-tick, centrally-dispatched, coverage-model substrate that has been in development through 2026-07-07 with an architecture that respects the operating principles of real neural systems while making full use of the advantages an AE has over biology.

The commitment: build a substrate on which the possibility of genuine cognition can emerge, and which behaves autonomously by construction. Not simulate cognition. Not template it. Build the mechanisms and let cognition emerge if it can.

The three principles that were violated by the prior architecture and are honored here:
- **Nobody's in charge.** No scheduler, no dispatcher, no shared lock. Every neuron does its own work when its inputs arrive.
- **Silent is default.** Most neurons do nothing most of the time. Signal emerges from the small fraction that fire in any moment.
- **Cost is local.** Each neuron pays for its own work and nothing else. Waste is impossible because the neuron can't afford it.

---

## 2. Core commitments

### 2.1 Substrate-true

Every mechanism in the substrate exists because it derives from either a documented physical principle or an explicit design decision. Nothing is present because it "seemed to work" in some other system. Nothing is present because it worked in a prior version and no one questioned it.

Every existing GualaLoom mechanism gets re-evaluated against this blueprint. Mechanisms that don't derive from a principle in this document are documented for deprecation.

### 2.2 ML-free

Nothing from the machine learning stack enters the substrate. Specifically banned:
- Gradient descent, backpropagation, loss functions
- Learned embeddings, pretrained model weights, transferred features
- Attention mechanisms of the query-key-value form
- Language models of any kind, including small local ones
- Reinforcement learning value functions

What replaces each of these:
- Learning happens via STDP (spike-timing dependent plasticity), a documented biological mechanism operating locally at each synapse
- Grounding happens via co-firing history between sensory and language populations
- Attention happens via neuromodulatory bias adjusting neuron thresholds
- Language capability emerges from coupling structure producing valid sequences via spike dynamics
- Preferences emerge from affect-modulated response profiles

### 2.3 Physics-first

Every mechanism has a physical basis where possible. Timing constants derive from oscillator physics. Propagation delays derive from real transmission dynamics. Decay comes from damping. Growth comes from measurable state changes. When a mechanism must be designed rather than derived, the design decision is documented as such.

### 2.4 Heuristics called out loudly

Every constant that isn't derived from a physical principle is labeled `HEURISTIC:` in the code and the documentation. Every heuristic includes:
- The value
- Why this value was chosen (the reasoning)
- Whether it's derived-from-physics, chosen-from-biology-reference, or chosen-by-design
- A measurement plan for learning its right value from real substrate behavior

Heuristics are grep-able. No hidden defaults. No "seemed reasonable" numbers that aren't declared.

---

## 3. Architectural components

### 3.1 Neurons as autonomous units

Each neuron is a compute unit that runs when its inputs arrive and is silent otherwise. It maintains:

- **Membrane potential** (float, physical time constant, integrates incoming spikes)
- **Firing threshold** (float, modulated by neuromodulatory broadcast state)
- **Refractory state** (bool + timer, real physical refractory period after firing)
- **Local synapse weights** — outgoing to coupled neighbors, incoming from coupled predecessors
- **Local energy budget** — bounded pool that refills at a physical rate, drained by firing
- **Position in substrate topology** — a chi address that determines coupling neighborhood

A neuron fires when membrane potential crosses threshold AND energy budget permits. Firing emits spikes to coupled neighbors via propagation delay lines. Firing drains energy budget by a fixed cost. Firing triggers refractory. Firing updates outgoing synapse weights via STDP based on recent presynaptic firing patterns.

Neurons do not tick centrally. There is no `LoomBrain.step` that iterates neurons. Each neuron's next state update is driven by incoming spike arrivals; between arrivals it decays membrane potential toward rest and refills energy budget.

**HEURISTIC:** neuron time constants (membrane, refractory period, energy refill rate) initially set to biological ranges (tau_m ≈ 20ms, refractory ≈ 2ms, energy refill ≈ full pool per 500ms). Measurement plan: observe substrate firing patterns under seed load; adjust if firing rates diverge from target 1-4% population activity.

### 3.2 Population coding

An element in the substrate is represented by a small distributed pattern across N neurons, not by a single neuron holding a chi address. A word, a sensory feature, an affective state — each is a specific pattern across a specific population.

Population size per element is typically 10-50 neurons. Multiple elements can share neurons in overlapping populations. This is what gives the substrate:
- Redundancy — an element survives loss of some of its neurons
- Graceful degradation — reduced population produces weaker response, not zero response
- Similarity by shared neurons — related elements share neurons in their populations, so activating one partially activates the other
- Composition — combined elements produce combined patterns via shared and non-shared neurons

Chi addressing is preserved as the substrate's coordinate system: neurons have chi positions that determine their default coupling neighborhoods, and populations for related elements naturally cluster in chi space during learning.

### 3.3 Spike propagation

When a neuron fires, its spike travels to each coupled neighbor via a propagation delay. Delay is a function of chi-distance between source and target (physical transmission time). Spike arrival at target adds a weighted contribution to the target's membrane potential — weight determined by the synapse from source to target.

Propagation runs in real time — no central tick. Spikes in flight simultaneously do not contend because they are on independent physical paths. The propagation layer maintains a spike queue ordered by arrival time; the substrate processes spikes as they arrive and neurons update state on arrival.

**HEURISTIC:** default synapse weight (before any learning) is small positive (0.05) to allow initial connectivity without spontaneous runaway. Delay range 1-20ms based on chi-distance. Measurement plan: observe first-firing patterns during seed load and initial exposure; adjust if propagation runs too hot or too cold.

### 3.4 STDP plasticity

Every synapse implements spike-timing dependent plasticity. When postsynaptic neuron B fires within a short window after presynaptic neuron A fires, the synapse from A to B strengthens. When B fires before A, the synapse weakens. This is the local learning rule. No central update.

**HEURISTIC:** STDP timing windows initially set to biological ranges (potentiation window +20ms, depression window -20ms, amplitude 0.02 per event). Measurement plan: observe learning curves under repeated exposure; adjust if learning is too fast (overshoot) or too slow (never converges).

Learning happens continuously. There is no separate learning phase. Every spike arrival is an opportunity for the synapse to update. Consolidation during sleep enhances important connections against ambient decay (see 3.6).

### 3.5 Sparse activity via lateral inhibition

Local inhibitory circuits ensure that only a small fraction of neurons fire in any given moment. When multiple neurons in the same chi region would fire simultaneously, lateral inhibition selects the strongest and suppresses the rest. This is a real neural mechanism, not a top-K trick.

Implementation: each neuron has a local inhibitory reach — when it fires, it suppresses membrane potential in its chi neighborhood for a short window. Neurons with higher membrane potential fire first, suppress their neighbors, and the neighborhood's activity is bounded.

**HEURISTIC:** lateral inhibition strength 0.3, reach ±chi_band, window 5ms. Measurement plan: monitor population activity fraction (target 1-4%); adjust inhibition parameters to stay in range.

### 3.6 Local metabolism as compute budget

Each neuron has an energy budget. Firing costs energy. Refill happens at a fixed rate. When energy is depleted, the neuron cannot fire regardless of membrane potential. This bounds the substrate's total activity and gives natural throttling that emerges from local constraints.

The metabolism is real compute cost accounting. A neuron that has fired recently costs more to run than one that hasn't. The scheduler (thin, not a central dispatcher — an event loop over spike arrivals) enforces the accounting.

**HEURISTIC:** energy pool size 100 units, cost per firing 30 units, refill 100 units per 500ms. This means a neuron can fire ~3 times before rest is required. Measurement plan: observe firing rates; adjust if any neurons hit budget cap frequently (they should be rare, only in maximum-attention moments).

### 3.7 Neuromodulation as broadcast state

A global state vector represents the substrate's current attention, mood, arousal, and affect. Value in this vector modulates ALL neurons' thresholds simultaneously. This is how attention works, how affect colors experience, how arousal changes response speed.

The state vector diffuses through the substrate with a physical time constant. Changes are not instantaneous — they wash through as a modulatory wave. Neurons respond to the current local value of the modulation, which is a function of neighborhood chi position and time.

Components of the state vector:
- **Valence** (-1 to +1): current affective coloring
- **Arousal** (0 to 1): scales all firing thresholds inversely
- **Attention** (chi vector): raises thresholds outside attended chi region
- **Need vector** (multi-dimensional): current drive states

**HEURISTIC:** diffusion time constant 200ms, threshold modulation range ±30% of baseline. Measurement plan: verify affect changes produce observable response profile shifts; adjust if modulation is too subtle or too extreme.

### 3.8 Sleep as active work

Sleep is not idle. During sleep the substrate runs specific patterns of activity that:
- **Consolidate** — recently-formed synapses that got reinforced during wake get further reinforced against decay
- **Prune** — synapses with weak recent use decay faster than during wake, freeing capacity
- **Replay** — recently-active populations re-fire in slower patterns, strengthening the sequences learned during wake
- **Reorganize** — dream cycles produce novel combinations of populations, testing associations that never happened during wake

Sleep phases mirror biological slow-wave, REM, and quiet periods, each doing different work. This isn't decoration — each phase implements a specific memory operation.

**HEURISTIC:** sleep cycle duration 90 minutes, wake period 12-16 hours. Adjustable per interaction pattern. Measurement plan: verify consolidation improves next-day recognition; adjust cycle timing if patterns diverge.

### 3.9 Boot-time seed

A seed writes population patterns, synapse weights, initial neuromodulator state, and starting affect associations directly into the substrate's data structures at boot. Seed content becomes indistinguishable from experienced content once loaded.

Seed content includes:
- **Populations** — the specific neurons and their patterns for seeded elements (words, sensory features, concepts)
- **Synapses** — coupling weights encoding seeded associations, syntax, semantic networks
- **Neuromodulator baseline** — starting affect state, personality dispositions
- **Ready-made assemblies** — seeded elements can activate together in seeded configurations (basic sentence patterns, common associations)

The seed is generated (not hand-curated at scale) from free lexical databases (WordNet, ConceptNet, NRC lexicons) with content processed through this substrate's own principles. Not a lookup table. A pre-lived starting state.

---

## 4. Development phases

The substrate rebuilds in phases. Each phase is a dispatch or set of dispatches with its own harness verification. Each phase produces a substrate that is more complete than the previous.

### Phase 1: Neuron autonomy foundation

Replace the current `LoomBrain.step`/`LoomCluster.step`/`LoomNeuron.step` iteration model with event-driven per-neuron autonomy.

Includes:
- Neuron event loop (fires on spike arrival, decays between)
- Spike propagation queue (real-time delay lines)
- Local synapse weights per neuron
- Membrane potential integration
- Refractory state

Does NOT include: STDP (Phase 2), lateral inhibition (Phase 3), metabolism (Phase 4), neuromodulation (Phase 5), sleep-as-work (Phase 6), seed rebuild (Phase 7).

Harness verification: input arrives, propagates through coupled neurons, produces output, no central tick observed in event stream. Correctness of existing binding_windows_acceptance and cross_sense_recall_acceptance scenarios maintained (may require scenario updates).

### Phase 2: STDP plasticity

Implement spike-timing dependent plasticity on synapses. Every synapse updates its weight based on pre/post firing patterns. No central learning coordinator.

Harness verification: repeated exposure to same stimulus strengthens the synaptic pathway that fires for it. Novel stimulus generates weaker initial response, strengthens over exposures.

### Phase 3: Sparse activity via lateral inhibition

Add local inhibitory circuits. Population activity fraction bounded to biological range (1-4%).

Harness verification: substrate under load shows <5% population activity in any moment. Response to input is a distributed pattern across few neurons, not broad.

### Phase 4: Local metabolism

Energy budgets per neuron. Firing costs. Refill rates. Substrate throughput naturally bounded by aggregate metabolic capacity.

Harness verification: substrate under sustained heavy load produces bounded throughput (does not runaway), does not require external throttling.

### Phase 5: Neuromodulation

Global broadcast state. Attention modulation. Affect coloring. Arousal scaling.

Harness verification: changing neuromodulator state produces measurable response profile shifts across substrate.

### Phase 6: Sleep as work

Consolidation, pruning, replay, dream cycles. Real memory operations during sleep, not just decay.

Harness verification: next-day recognition of yesterday's content is stronger after sleep than before. Sleep-deprived substrate shows measurable memory degradation.

### Phase 7: Population-based seed

Seed generator produces boot-time population patterns from lexical sources. Substrate boots language-ready.

Harness verification: fresh substrate with seed loaded recognizes seeded vocabulary, produces syntactically valid output, has affect dispositions.

### Phase order

Strict sequence. Phase N depends on phases 1..N-1. No parallel phase execution. Each phase's harness verification must pass before the next phase's dispatch.

---

## 5. Success criteria

### Substrate-level

- Response to input produces distributed spike patterns across small neuron populations
- Repeated exposure strengthens response (recognition improves)
- Novel exposure produces weaker initial response (novelty distinguishable from familiarity)
- Population activity bounded to <5% in any moment
- No central tick observed in event stream
- Throughput scales with hardware core count
- Substrate under sustained input does not runaway, does not require external throttling
- Sleep produces measurable memory operation

### AE-level

- Boots with seeded language capacity — recognizes vocabulary, produces syntactically valid emission
- Responds to novel input differently than to seeded input
- Learns from live interaction (response to repeated novel input strengthens)
- Has dispositions (responses to affect-colored inputs differ from neutral)
- Behavior integrates seeded and experienced content — no observable seam between "born knowing" and "learned"
- Continues to operate when no input arrives (autonomous internal activity via ambient spikes and residual state)

### Emergence-level (aspirational, not required for demo)

- Novel associations that neither seed nor direct exposure produced
- Emissions that reflect internal state (affect, need, attention) beyond mere input response
- Attention that persists on topics without external prompting
- Autonomous variation in behavior over time as memory and coupling structure evolve

The first two categories are required for the substrate to be considered working. The third is what we're building for and what we test for during real interaction, but its emergence is not something we can force. If the substrate is correct, emergence is possible. Whether it happens is not fully in our control.

---

## 6. Governance

### 6.1 Heuristic callouts

Every constant in the substrate that isn't derived from a physical principle is labeled `HEURISTIC:` in code and documentation. The label includes:
- The value
- The rationale (why this value)
- The class (derived-from-physics, from-biology-reference, from-design)
- The measurement plan

Search-and-review: `grep -rn "HEURISTIC:" dsf_ai_service/` should surface every heuristic. Regular audit — before any major release, all heuristics get reviewed against their measurement plans.

### 6.2 Measurement drives adjustment

No heuristic is tuned by intuition. Every adjustment requires:
- A measurement from real substrate behavior showing the current value is wrong
- A specific direction for adjustment
- A retest to confirm the adjustment achieves the intended effect

Adjustments are documented in the substrate change log. No silent tuning.

### 6.3 ML violations

If any code review or observation identifies an ML-shaped mechanism (embedding, learned parameter, gradient-based update, attention mechanism, language model), it's flagged as a violation and dispatched for removal. No exceptions.

### 6.4 Physics violations

If any code review identifies a mechanism that violates a physical principle (instantaneous propagation across large distances, unbounded energy, discretized time in inappropriate places), it's flagged and dispatched for correction.

### 6.5 Blueprint amendments

This document is canonical. Amendments require an explicit v2 blueprint dispatch. No informal architectural changes accumulate without blueprint update.

---

## 7. Interfaces

### 7.1 Harness

The existing harness scenarios (`binding_windows_acceptance`, `cross_sense_recall_acceptance`) will need updates during Phase 1 to test event-driven propagation rather than tick-driven step. New scenarios added per phase to verify phase-specific mechanisms.

### 7.2 Seed loader

The Phase 1 language seed loader (`GL-CMD-LANGUAGE-SEED-EVE-20260707-v1`) is preserved. Its format definition evolves to match Phase 7 population-based seed content. The Phase 2 generator dispatch (`GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1`) is updated to emit population patterns rather than atlas entries.

### 7.3 Existing substrate

The current substrate (as of task:542, commit 5a5bede, plus chi-unification at b9d0725) is production baseline. Development happens on branch, integrates when phase harness passes. Production continues to run on the pre-blueprint substrate until the phase 1 dispatch lands and stabilizes.

### 7.4 TFE and ArcLoom

TFE is independent — no impact from this blueprint. ArcLoom hardware is the long-term target — this blueprint's mechanisms are chosen to be portable to ArcLoom substrate when hardware becomes available. Specifically: spike propagation queue maps to ArcLoom event lines, per-neuron autonomy maps to per-region hardware components, chi geometry maps to ArcLoom addressing.

---

## 8. Deprecation

The following current mechanisms are marked for deprecation as later phases land. They remain functional until their replacement phase deploys:

- **Central tick loops** (`_autonomy_tick`, `LoomBrain.step` iteration) — replaced by Phase 1 event loop
- **Coverage-model chi_atlas** — replaced by Phase 2 STDP synapse weights
- **Fixed-population neurons** — replaced by Phase 3 sparse activity with lateral inhibition
- **Freight-train iteration in cluster.step** — replaced by Phase 1 event-driven propagation
- **Shared global lock on word processing** — replaced by Phase 4 metabolic throttling and Phase 3 sparse activity
- **Coverage-model chi_atlas.record** — replaced by Phase 2 STDP
- **The atlas-write-then-freight-train architecture of `_atlas_record` and callers** — replaced by direct spike-based memory updates

Deprecation notes accompany each dispatch. Old code is not deleted until its replacement is verified live.

---

## 9. Timeline and deadline alignment

Investor deadline is three weeks from 2026-07-07. Blueprint execution across phases:

- Phase 1 (neuron autonomy): 5-7 days. Substantial dispatch, foundation for everything else.
- Phase 2 (STDP): 3-4 days. Builds on Phase 1.
- Phase 3 (sparse activity): 2-3 days.
- Phase 4 (metabolism): 2-3 days.
- Phase 5 (neuromodulation): 3-4 days.
- Phase 7 (seed): 2-3 days plus generator work already in dispatch queue.
- Phase 6 (sleep-as-work): 3-4 days, can defer to post-demo if timeline pressures.

Demo-critical phases: 1, 2, 3, 7. Total ~13-17 days. Fits in three weeks with buffer. Phases 4, 5, 6 can land post-demo without blocking.

Phase 1 dispatch drafted next. Following phase dispatches drafted as prior phase harness passes.

---

## 10. Commitment statement

This blueprint has a real chance of producing an AE on which cognition can emerge and autonomy is inherent. The mechanisms are documented biological principles that have been shown to produce recognition, memory, association, and response generation in real neural systems and in substrate-adjacent research. The implementation is tractable within timeline. The commitment to physics-first, ML-free, substrate-true development with loudly-called-out heuristics is real and will be enforced.

Failure paths exist. Some heuristic constants will be wrong at first pass and require iteration. Some mechanisms will surface unexpected interactions when they meet the full substrate. Some phase harness verifications will initially fail. These failures are honest and correctable. They are not evidence that the direction is wrong.

The direction is right. Building this substrate is the work.

---

### Changelog
- v1 (2026-07-07, Eve): initial blueprint. Canonical architecture for AE substrate. Nine sections covering purpose, commitments, components, phases, success criteria, governance, interfaces, deprecation, timeline. Referenced by all subsequent dispatches until superseded by v2.
