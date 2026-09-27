# Guala: bio-functional flexible planning and problem-solving

**Execution handoff:** COG-OSC-02 · **Author:** A1 · **Date:** 2026-09-27

**Implementation and release owner:** G1. **Independent review and functional-body interface owner:** A1.

**Status:** implementation plan, not an implemented capability or production certification.

## 1. Decision and intended outcome

Develop one organism that can use retained experience to anticipate consequences, construct a new means of satisfying a bodily need, act, and change that means when reality contradicts its expectation. Do not add a radio-removal routine, a canned plan library, or a second planning agent.

The first production milestone is deliberately smaller than Joe's stream/plank/vine example:

> In a changed arrangement, Guala uses relationships learned through genuine experience to obtain an available resource. When her familiar access is obstructed, she can discover a supported alternative, including a necessary initial movement away from the resource or manipulation of an obstruction. A distraction need not erase the objective. Failure changes the attempted means. Actual consumption changes the bodily demand and ends the pursuit.

The solution must be a **new useful combination of learned relationships**, not just retrieval of an identical successful route. Its execution must use existing movement and manipulation first. Climbing, jumping, swimming, and articulated tool handling remain dependent on the separate functional-body work. Do not postpone this bounded cognitive milestone until those motions exist.

This is not a promise that a few new classes will produce human planning. The current runtime lacks important causal machinery. This plan specifies the implementation sequence, the physical-law decisions that must be completed, and the evidence required before each claim is permitted.

### Architecture honesty gate

1. **Requested architecture:** sparse, persistent, experience-grown cognition; joint DSF delivery; retained physical plasticity; prospective sensorimotor prediction; consequence-sensitive action; one organism and one authoritative physical clock.
2. **Current code reality:** production restores the discrete `FunctionalOrganism` and `FunctionalPhysicalLoop`. The inspected selection path contains reduced structural keys, authored selection rules, scalar action worth, and a narrow feeding-continuation controller. It is not the complete ratified neuron/cognitive architecture.
3. **Conflict:** **yes**. Existing motion, sensation, physical receipts, and some causal retention are useful, but broad claims of already-complete flexible planning are unsupported.
4. **Do not extend:** scalar action/curiosity scores, feeding-only graph reachability as general cognition, fixed semantic intent enums, supplied action sequences, simulator-ID recognition, or per-object escape patches. Do not modify canonical L0–L4. Do not reopen the closed OSC-01 geometry repair or the accepted sensory transport merely to make this project larger.
5. **Single next item:** G1 completes the P0 source/law/mount contract below before implementing a new decision authority.
6. **Evaluation level:** this document is a functional architecture and implementation plan. Current source is a reduced approximation, not verified full joint-field cognition.
7. **Missing structure in the current decision path:** joint cross-channel geometry is reduced to stream/regime keys; retained action records are not demonstrated persistent neuronal plasticity; general counterfactual body/world dynamics and their effector coupling are absent.

## 2. Scope and non-negotiable boundaries

### In scope

- A genuine causal learning path from sensed action and actual consequence to persistent physical change.
- Recognition and relational continuity sufficient to reuse experience in the bounded test arrangements, without privileged object identities.
- Persistence of an active need-related trajectory without a prescribed action list or duration.
- Learned prediction of bodily actions and their environmental effects, including an explicit distinction between known, contradicted, and unsupported relationships.
- Recombination, inhibition, inspection, and replanning through the same organism's physical substrate.
- Honest sensory/motor interfaces, current-state persistence, bounded resources, ordinary-loop proofs, and safe production migration.

### Out of scope for this release

- General language, grammar, theory of mind, a whole developmental curriculum rewrite, or proof of human-equivalent cognition.
- New streams, vines, bridges, swimming physics, or a scripted climbing action.
- Recreating every human brain region or every molecular pathway.
- Replacing the caretaker, expanding the UI, building a parallel memory database, or adding a general search service.
- Claiming that hunger alone supplies knowledge of food locations or that thousands of grasps automatically imply understanding of obstruction removal.

Biological inspiration specifies required functions, not a requirement to duplicate human anatomy. Conversely, deterministic software is not automatically physical learning: a deterministic lookup or scalar ranking can still violate the project's architecture.

**Do not withhold ordinary caregiving from live Guala to prove this work.** Run unattended acquisition proofs on an isolated, disclosed copy with caregiver assistance absent. Live starvation is a failure to remedy, not evidence that the next cognitive mechanism will emerge if given more time.

## 3. Verified baseline and its limits

### Source examined for this handoff

Workspace: `/workspaces/Tao_Financial_Engine`; branch `guala-live`; HEAD at review: `22fc7d8ff69fa26ddad066848e8b676909adb55d`.

| File | SHA-256 at review |
|---|---|
| `dsf_ai_service/guala_functional_organism.py` | `10e23e1a7eb169b6b5b03995a857b55183d718788787e01cdc8735984d10e08c` |
| `dsf_ai_service/guala_functional_loop.py` | `505f2d1ed231cfc3b5ada0757bc05618db05092fdb067d9452546b1fdf347a9c` |
| `dsf_ai_service/episodic_binding_engine.py` | `dda3b1be483a0867a61f277b84b7d723beda63d05791584fc0a59b3f3590bb37` |

These are source fingerprints, not proof that this complete source set is currently serving. No new live-production measurement, test run, or deployment was performed for this document.

The last independently verified OSC-01 release in the ledger was task 1560, task ID `502e361c4b484240b65b4be38023dca4`, image digest `sha256:45b4591c43a6067eb7367bda2be2e08fd26429e2f43c46055c1b99d249da39ed`, verified on 2026-09-27 at approximately 15:29 UTC. It preserves organism identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`. G1 must re-resolve the actual current serving task before any release; these identifiers are historical evidence, not deployment targets to assume indefinitely.

### What the oscillation repair did and did not establish

OSC-01 corrected doorway aperture/whole-body clearance and removed an impossible-route sidestep fallback. Its proof showed escape from the specified reciprocal translation trap without moving the radio or fabricating experience. See [OSC-01](../OSC-01.md).

It did **not** establish learned obstruction manipulation, counterfactual planning, arbitrary-cycle elimination, successful food acquisition, or adequate reserves. The recorded reserves remained zero. A geometry repair is necessary infrastructure, not a cognitive proof.

### Source-to-capability map

Line numbers are navigation hints for the reviewed revision, not stable APIs.

| Current source | Existing responsibility | Missing or conflicting responsibility | Treatment in this work |
|---|---|---|---|
| `lean_production_app.py:_restore_production_actor` | Restores paired functional organism/world and constructs the actor | Does not mount the complete definitive persistent neuron/cognitive chain | Trace actual native and Python entry points; prohibit genesis conversion as a migration shortcut |
| `guala_functional_organism.py:_measure`, `_kernel`, `choice_key`, `coarse_key` | Measures streams and constructs reduced structural regimes | Separate stream/sign/key processing is not complete joint-field delivery | Replace cognitive authority only under the approved joint-delivery contract; preserve the kernel itself |
| `Sensed`, `_capture_sensory_key`, `conserved_objects` | Carries observations; retains limited views, positions, contact conditions | Cryptographic view keys and world identifiers do not provide learned identity across views | Establish sensory-only continuity; do not confer identity through simulator labels |
| `decide`, pending transition finalization, `commit` | Records executed actions, successor evidence, intake and refusals | General prediction and consequence comparison are not integrated | Preserve genuine receipts; connect actual successor evidence to learned expectations |
| `_form_moments`, `_dream_moment`, `bound_waking_moments` | Episodic admission, retention, and consolidation | Dictionary retention is not proof of distributed neuronal reassembly | Preserve actual historical evidence; do not rename it a neuronal fractal |
| `episodic_binding_engine.py:find_supported_continuation` | Bounded feeding-only backward reachability over actual transitions | Exact cues, unique action support, and immediate-distance decrease cannot provide novel means or necessary detours | Keep its current scope explicit; do not extend it into the proposed cognition |
| `_choose`, `_portal_novelty` | Selects actions using authored branches and worth/exploration calculations | Dwell-driven evacuation and scalar ranking are competing decision authorities | Remove from authority for the migrated path at cutover; no fallback that silently reinstates them |
| `move_commands_toward`, `_door_motor_commands` | Converts a requested movement into geometrically feasible motion | A geometric route is not a learned objective or choice of means | Preserve as disclosed low-level mechanics where compatible; never use privileged geometry as cognitive knowledge |
| `guala_functional_loop.py:settle`, `_apply` | Applies commands and obtains physical consequences | Actual root-motion summary is produced after organism commit; it is not already a general prediction-error afferent | Feed measured consequences through the ordinary sensory/body path, not the UI log |
| `substrate/guala_sensorimotor_mesh.py` | Narrow auditory/vocal physical association machinery | Not a demonstrated general planner or complete definitive neuron | Do not copy its constants or dense layout into a new brain; preserve its separate evidence boundary |
| `lean_actor.py`, `paired_current_store.py` | Single-writer settlement, bounded pending custody, paired persistence | New cognitive state must join the same custody and timing | No second brain process, clock, checkpoint history, or decision service |

The reviewed native source directory contains optical, acoustic, kinematic, and support modules. A native acceleration library being installed does not prove that a complete persistent cognitive substrate is mounted.

Several older cognitive-authority repository mirrors and the `scripts/` guard directory were not present in this checkout. The governing skill references were read. G1 must reconcile the exact authoritative version and executable mount in P0, not invent missing scripts or treat a design document as running code.

## 4. Biological research and engineering justification

Biology distributes these functions across interacting circuits. The following evidence motivates responsibilities; it does not prove a one-region/one-module mapping, complete human equivalence, or that biological brains implement DSF. Some cited experiments use probabilistic or reinforcement-learning analysis. Those analyses are **not** authorization to introduce scalar reward learning into Guala.

| Research | Relevant finding and limitation | Requirement justified here |
|---|---|---|
| **R1 — Wang et al., 2013**, [primate prefrontal persistent firing](https://pubmed.ncbi.nlm.nih.gov/23439125/) | Pharmacological evidence links NMDA-receptor function to delay-period activity. This is one working-memory mechanism, not the sole account of memory. | A currently relevant configuration must survive absent stimulation through supported recurrent/material state; a reset-per-beat controller is insufficient. |
| **R2 — Yagishita et al., 2014**, [timing of dopamine-dependent spine plasticity](https://pubmed.ncbi.nlm.nih.gov/25258080/) | Mouse striatal spine experiments show a biochemical eligibility interval for activity and subsequent modulation. Their measured interval is not a universal learning timeout. | Delayed consequences need a physically retained eligibility trace; credit must return to the contacts that actually participated. |
| **R3 — Pfeiffer and Foster, 2013**, [hippocampal sequences toward remembered goals](https://www.nature.com/articles/nature12112) | Rat place-cell sequences represented prospective paths before movement. Spatial sequence evidence alone does not prove tool reasoning. | Internal prospective activity may precede action and combine start/goal relationships; it must be distinguished from executed movement. |
| **R4 — Addis, Wong and Schacter, 2007**, [remembering and imagining events](https://pubmed.ncbi.nlm.nih.gov/17126370/) | Human imaging found overlapping and differing activity during past-event retrieval and future-event construction. Imaging does not specify the learning algorithm. | Retained components must support construction of a not-previously-executed possibility, not only exact episode playback. |
| **R5 — Wolpert, Ghahramani and Jordan, 1995**, [internal models for sensorimotor integration](https://pubmed.ncbi.nlm.nih.gov/7569931/) | Human movement/localization experiments supported predictive integration of motor and sensory information. This does not imply perfect physical knowledge. | Action preparation needs learned predictions of its own bodily and sensory consequences. |
| **R6 — Tseng et al., 2007**, [sensory prediction errors in cerebellar adaptation](https://pubmed.ncbi.nlm.nih.gov/17507504/) | Patient/control experiments distinguish prediction-error-driven adaptation from merely making corrective movements. | An accepted action can still be a failed prediction; collision refusal cannot be the only learning signal. |
| **R7 — Cisek and Kalaska, 2002**, [simultaneous preparation of potential reaches](https://pubmed.ncbi.nlm.nih.gov/11826082/) | Monkey premotor activity represented more than one potential movement before final selection. The task was constrained reaching, not general planning. | Competing feasible actions should interact before one is expressed; a fixed action-precedence list is not an equivalent. |
| **R8 — Chen et al., 2020**, [human prefrontal–subthalamic stopping](https://pubmed.ncbi.nlm.nih.gov/32155442/) | Human recordings support rapid interaction during stopping. This does not reduce all basal-ganglia function to a binary switch. | New hazard or contradictory sensation must be able to interrupt prepared action without deleting all retained experience. |
| **R9 — Gläscher et al., 2010**, [state versus reward prediction errors](https://www.princeton.edu/~ndaw/gddo10.pdf) | Human task/imaging results distinguished signals associated with unexpected transitions and rewards. Its computational fitting framework is not Guala's approved implementation. | Preserve unexpected physical transitions separately from nutritional benefit or pain; otherwise successful-but-useless movement is invisible. |
| **R10 — Livneh et al., 2017**, [homeostatic modulation of insular food-cue responses](https://www.nature.com/articles/nature22375) | Mouse experiments linked hypothalamic hunger-related circuitry to state-dependent cortical responses. This is not a semantic food oracle. | Actual bodily state must change the relevance of learned sensory relationships and must itself change when needs are met. |
| **R11 — Mobbs et al., 2007**, [threat imminence and defensive processing](https://pubmed.ncbi.nlm.nih.gov/17717184/) | Human threat experiments found changing recruitment as threat approached. They do not supply a swimming controller or imply complete cortical shutdown. | Urgent bodily danger must alter ongoing action competition; a previously relevant concern may cease to apply. |
| **R12 — Yin et al., 2005**, [dorsomedial striatum and goal-directed action](https://pubmed.ncbi.nlm.nih.gov/16045504/) | Rat lesion/inactivation work tested sensitivity to outcome devaluation and degraded action–outcome contingencies. | Demonstrate that behavior changes when an outcome loses relevance or the means no longer causes it, rather than only when movement is blocked. |
| **R13 — Fischer et al., 2016**, [functional organization of physical inference](https://doi.org/10.1073/pnas.1610344113) | Human imaging implicated a frontoparietal network overlapping action/tool-related processing. It does not establish an exact internal physics simulator. | Physical relational prediction and action knowledge should be connected; do not give cognition an omniscient copy of the world engine. |
| **R14 — Marchette et al., 2014**, [local spatial reference frames](https://www.nature.com/articles/nn.3834) | Human behavioral/fMRI work found location/direction codes anchored to local environmental structure in the retrosplenial complex. The corrected anatomical description matters; this is not a universal GPS module. | Relate current body-facing information to retained environmental relationships without confusing a turn of the observer with movement of the destination. |
| **R15 — Howard et al., 2014**, [path and Euclidean goal distances](https://discovery.ucl.ac.uk/id/eprint/1462388/) | Human navigation data distinguished neural relationships to path distance and straight-line distance. This does not prescribe a shortest-path algorithm. | Keep route consequences distinct from instantaneous target bearing or distance; a necessary detour may initially point away. |
| **R16 — Mole et al., 2025**, [analogical and deductive reasoning after focal lesions](https://pubmed.ncbi.nlm.nih.gov/40233941/) | A lesion study implicated a right frontal network in the tested reasoning abilities. It does not establish that all reasoning or risk assessment resides there. | Require relational transfer and indeterminate-evidence controls, not a semantic class named “executive planner.” |

### Incorporation of Joe's additional research

Joe supplied spatial-navigation reviews and summaries while this plan was being written. Their useful contribution is the distinction between body-relative information, remembered environmental relationships, executive control, and predictive motor correction. Their references also led to the primary studies R14–R16 above.

Do not implement the popular shorthand literally: PFC is not a single executive agent, PPC is not an exact GPS, and cerebellar correction does not wait until a completed plan is handed down. Grid-cell findings are strongly associated with entorhinal circuitry, but spatial representations are distributed; the regions do not have exclusive ownership of coordinate frames. Planning and execution remain recurrently coupled. The plan therefore adds the concrete frame-consistency requirement in M2 and C19, rather than adding separate brain-region services.

The supplied PMC reviews are useful literature maps, not executable laws: *Spatial Representations in the Human Brain* (Herweg and Kahana, 2018), *Challenges for identifying the neural mechanisms that support spatial navigation* (Wolbers and Wiener, 2014), and *The cognitive map in humans* (Epstein et al., 2017). Implementation justification here rests on the cited primary experiments, not Quora, general educational summaries, or unverified claims of exact mental calculation.

### What this means for Joe's example

The required chain is: perceive a gap and available materials; reactivate body and material experience; maintain the crossing objective; construct alternative interactions; anticipate reach, support, effort and possible injury; inspect uncertain features; select and act; compare predicted and actual consequences; replace failed means; respond to actual immersion.

A plank label cannot supply length, strength or bridge usefulness. Seeing someone use a ladder cannot supply the observer with stronger legs or a copied successful motor history. A vine's hidden breaking strength remains unknown without informative evidence. These are important limits of biological reasoning too.

## 5. One integrated causal architecture

Use the same persistent substrate for perception, retention, recall, prospective activity and action. The names below describe responsibilities, **not** separate agents, process owners, databases, or hand-authored semantic brain modules.

```text
World physics ── actual receptors/body return ──► joint DSF delivery
      ▲                                                │
      │                                    persistent physical substrate
      │                                  ↔ retained/recurrent relationships
      │                                  ↔ prospective activity and mismatch
      │                                                │
      └──── one committed body action ◄── effector coupling

Observer receipts can describe this chain; they cannot choose its actions.
```

### M1. Actual consequence and eligibility binding

**Build:** associate the participating sensory, proprioceptive and effector activity with the actual subsequent return through retained local contact state. A consequence arriving after movement must affect the participating pathway, not whichever action happens to be selected next.

**Inputs:** receptor-origin observations, actual motor execution/custody receipts, body return, metabolic and nociceptive changes, and their physical timing. A refusal is one possible consequence, not the only negative evidence.

**Retained state:** only the ratified physical variables and their sparse changes. Historical evidence records may document these changes, but an action-score dictionary cannot become the learning authority.

**Required distinction:** observed caregiver action is an external sensory episode; self-executed action includes efference and own-body consequence. Watching a grasp must not increment Guala's grasp trials. Observational transfer must emerge from demonstrated shared sensorimotor relationships.

**Exit proof:** a delayed real consequence changes the originally participating contacts and later behavior; a matched nonparticipating pathway does not receive fabricated experience. No `reward += constant` closes this requirement.

### M2. Continuous evidence and relational recognition

**Build:** reuse experienced physical relationships across the view and body changes needed by the milestone. Retain relations such as the sensed body's position relative to a contacted surface and the observed change in a passage after manipulation. Do not manufacture a semantic `blocks_door` fact from a world-object query.

Vision, touch, proprioception, self-motion and hearing are complementary. Touch can establish load, movement resistance and surface response that vision cannot. An object carried outside view must not become a new object merely because its retinal bytes changed; equally, temporal adjacency does not prove two objects are identical.

**Boundary:** simulator IDs can address a physical actuator transaction and audit receipt. They cannot establish perceptual recognition, edibility, hidden material strength, or object permanence. Object continuity must have a sensory/body evidence path, including abstention under genuine ambiguity.

**Coordinate-frame requirement:** distinguish eye-, head-, hand- and body-relative evidence from retained environmental relations. A changed retinal bearing after a head turn must not by itself imply that a destination moved. Self-motion and contact information must update the relation through the approved physical learning/mount contract. World-known absolute coordinates may validate an experiment, but cannot be copied into a purported learned cognitive map. A rotated viewpoint and a physically moved object require different predictions and different evidence.

**Exit proof:** identifier renaming does not change behavior; a supported view/contact transformation preserves the learned relationship; a perceptually ambiguous substitution does not receive unjustified certainty. If cross-view continuity remains absent, report it as a blocking prerequisite for this milestone, not a solved problem hidden behind a hash match.

### M3. Persistent objective, revisable means

**Build:** a need-related recurrent/material configuration can remain causally active across intervening sensory events. The current movement target, attended object, and means are not interchangeable with the objective.

Do not create an `intent=GET_FOOD`, an action array, or a fixed `remaining_ticks` field. Ordinary body deficit and learned consequence pathways supply the ongoing constraint. Any sustained activation requires accounted energy and material support; biological working memory is not free perpetual firing.

**Exit proof:** a distraction changes immediate orientation but does not necessarily erase the still-unsatisfied pursuit. Loss of one route or object changes the means. Real repletion removes the bodily condition sustaining the pursuit. Persistence must not mean stubbornly repeating an obsolete action.

### M4. Learned forward sensorimotor relationships

**Build:** motor preparation and current sensed context can reactivate a prediction of subsequent sensory/body change. Learning compares that prediction with the actual returned change. Start with displacement, contact, custody, accessible-space change and oral consequence available in the current embodiment.

The world engine remains the authority on what physically happens. It must not be called with hypothetical actions against privileged hidden state to answer the organism's imagined questions. That would supply an oracle, not a learned internal model.

**Unknowns:** unexperienced load, occluded support, ambiguous identity and unmounted body sensors remain unsupported. Inspection or a low-exposure physical probe can become useful through learned consequences; do not add an authored curiosity bonus or a rule that automatically tests every unknown.

**Exit proof:** prediction precedes action; the predicted physical relationship is testable; changed load or contact generates an appropriate discrepancy. Prediction must work on held-out arrangements within demonstrated experience support, not only replay training fixtures.

### M5. Prospective recombination without fabricated experience

**Build:** distributed reactivation can temporarily combine learned relationships into a possible trajectory that has not been executed as that full sequence. The combination must remain constrained by the organism's body capability and available evidence.

No supplied `move → grasp → carry → release` list. No template lookup keyed by `radio`, `ladder` or `blocked portal`. No whole-world clone, exhaustive action tree, semantic planner, or LLM decision authority.

Prospective activity shares the physical substrate and its resource limits. It does not advance world time by pretending a movement happened. External sensory ingress continues. Internally generated activity must retain provenance so it cannot create a real intake record, actual displacement, or a false observation of a caregiver action.

**Exit proof:** the successful full combination was absent from training, its component relationships were actually experienced, and selectively disrupting the relevant retained relationship removes the advantage. Replay of a previously supplied full sequence does not pass.

### M6. Need, uncertainty and risk remain physically distinct

**Build:** current metabolic condition, nociceptive state, effort/capacity and sensory uncertainty affect the active substrate through their actual channels. Predicted bodily consequences remain multi-dimensional; do not collapse them into `benefit − risk − distance`.

The first milestone verifies a metabolic need and relevant physical hazard. The interface must not prevent later social or exploratory development, but this release cannot claim those needs are implemented merely because the schema permits them.

No invented willingness-to-risk scalar. No hidden knowledge that a visually identical support will hold. An immediate danger can interrupt action through an explicit, physically supported protective path; that protection must be labeled engineered if it is engineered, not evidence of learned foresight.

**Exit proof:** changed body capacity or demonstrated material resistance changes the supported action. An unavailable sense remains unavailable, not a zero reading. Outcome devaluation follows actual bodily change, not an evaluator setting a success flag.

### M7. Action competition and effector coupling

**Build:** competing, reached pathways interact through the approved physical excitatory/inhibitory/contact dynamics. Their physical output couples to available effectors. Anatomical actuator addressing is legitimate; selecting an act by a semantic priority table is not.

The constitutive law must specify how simultaneous outputs settle, how unsupported activation remains unexpressed, and how hazardous new input interrupts preparation. It must not hide an `argmax(score)`, alphabetical tie-break, or fixed action ordering under the name of an attractor.

A low-level trajectory solver may validate contact and generate actuator motion for an already specified physical command. It cannot secretly choose the need, target object or manipulation strategy. A useful detour must not be vetoed because it temporarily increases target distance.

**Exit proof:** ordinary competition selects a supported action, not a test-inserted candidate. Conflicting/unsupported activity does not invoke the old scalar controller. Any continued sensing or pause must be an honest consequence of the supported dynamics, not a fabricated success.

### M8. Mismatch, interruption and replanning

**Build:** compare predicted and actual physical returns on each relevant channel. Lack of expected progress, changed custody, failed support, or a moved obstruction can invalidate a means even when the world accepted every movement.

Do not define failure solely as a collision, exact reciprocal displacement, elapsed number of beats, or lack of immediate Euclidean progress. Returning through a previously visited position can be a necessary retrieval or detour.

Repeated acceptance of A→B→A must not continuously renew evidence that a need is being fulfilled. The discrepancy must alter the retained predictive/active structure through the declared law. The objective can persist while a particular continuation loses support.

**Exit proof:** both the original reciprocal trap and a different longer no-progress cycle cease to dominate; a necessary return path remains possible; the new behavior produces a useful consequence when one is available. Merely stopping all movement is not success.

### M9. Sleep, recovery and retained continuity

**Build:** preserve the same physical memory through wake/sleep and restart. Recurrent reactivation and consolidation must operate on actual retained structure, with energy and material accounting. Dreamed trajectories are not retrospectively recorded as executed actions.

Do not make all learning wait for sleep, erase successful acquisition at waking, randomly sample a database as “dreaming,” or prune inconvenient negative evidence to improve a demonstration.

**Exit proof:** the relevant learned relationship persists through an ordinary sleep/wake cycle and a fresh-authority cold continuation. A failed means stays failed until new physical evidence supports a changed relationship.

## 6. Mathematical and learning-law contract

This section identifies the executable physical contract G1 must finish before changing cognitive authority. It does **not** claim that naming these equations supplies a complete learning network.

### 6.1 Canonical delivery and state

Preserve the unchanged L0–L4 kernel and explicit joint fields

\[
\mathcal F=(D_k,M_k,R_{rev,k},U_k^*,C_k,P_k,B_k),\qquad S_{UF}.
\]

Use the ratified joint-delivery structure with declared time, coordinates, units, relevance and sparse connections. Seven independently reduced signs, a regime string, or a weighted sum is not this delivery. L0 dimensionalization and the downstream canonical mathematics are not redesigned here.

The definitive physical neuron state is specified by the governing neuron authority as

\[
N_i=(G_i,A_i,X_i,\Psi_i,K_i,Q_i,V_i,C_i,M_i,\Theta_i,B_i).
\]

G1 must map every member used in the implementation to the authority's definition, unit, codec, update law and actual consumer. Reusing a symbol such as \(C_i\) for capacitance in one equation does not permit confusing it with the DSF field \(C_k\).

The required causal chain is joint field delivery → exact MathLoom transport → typed Ψ/Krimelack constraints → physical channel/gate settlement → material/charge consequence → retained plastic change. A DSF impression, sign word, repeated activation or checksum is not a neuronal fractal. That term requires the exact sparse retained physical difference between the pre-experience quiescent state and the subsequent quiescent state. Higher-order names describe emergent recurrent relationships, not stored semantic hierarchy objects.

### 6.2 Conservation and retained physical work

The ratified model includes contact conduction and charge accounting of the following form:

\[
I_{ij}=g_{ij}(V_i-V_j),\qquad
z=I\Delta t/e+r,\qquad n=\operatorname{whole}(z),\qquad r'=z-n.
\]

Here \(e\) is the carrier charge quantum; integer carriers and the retained remainder account for finite transfer. With the applicable membrane transfer \(n_{mem}\),

\[
Q'=Q-n_{mem}e,\qquad V'=Q'/C.
\]

Constitutive geometry can determine conductance, for example

\[
g=\sigma A(y)/\ell,
\]

only where the authoritative physical model supplies the conductivity, geometry, gate displacement and units. Plastic change must follow declared work/yield conditions, not successful behavior labels. A ratified form is

\[
f=|\sigma_{stress}|-Y\le0,\qquad
\dot\lambda\ge0,\qquad \dot\lambda f=0.
\]

Do not confuse electrical conductivity \(\sigma\) with stress \(\sigma_{stress}\). Complete the model's material update and energy balance; complementarity by itself is not an executable learning rule.

In a closed, unpowered settling segment require the applicable energy law, e.g.

\[
\frac{dE}{dt}\le0.
\]

When the body or an external source supplies work, include that work and all reservoirs explicitly. Different energy quanta cannot be added as dimensionless counts. Persistent activity, growth and memory modification must pay their actual modeled costs.

Exact MathLoom conversion and the approved deterministic numerical boundary remain those of the authority. Approval of bounded body mechanics or optics does not authorize approximate cognition, field flattening, fast-math reassociation, or arbitrary cognitive thresholds.

### 6.3 Prediction and mismatch

Use this notation to state the contract, **not** as a substitute implementation:

\[
\widehat{s}_{t+\Delta t}=\mathcal P_{\theta_t}(s_t,u_t),\qquad
\epsilon_t=s_{t+\Delta t}-\widehat{s}_{t+\Delta t}.
\]

Here \(s\) is available sensed/body state, \(u\) is a physically available effector preparation, and \(\theta\) denotes retained physical structure. Subtraction applies only to aligned channels with compatible physical units. Contact/custody transitions require their own typed comparison; absent observations are not numeric zeros. No scalar norm of \(\epsilon\) becomes the decision authority.

G1 must supply the local physical realization of \(\mathcal P\), the timing of its output, and how discrepancy drives permissible material change. An unspecified function named `predict()` or an online simulator using hidden world state does not satisfy the contract.

### 6.4 Useful geometry is not cognitive utility

For displacement \(v\) toward offset \(d\),

\[
\|d-v\|^2<\|d\|^2\iff 2(v\cdot d)>\|v\|^2.
\]

This is a correct test of **immediate** distance reduction. It is not a condition for every useful action. Moving away to obtain a tool, carry an obstruction aside, or go around a wall can be necessary. Retire that inequality as a universal continuation veto; retain ordinary collision and body-limit validation.

For frame-consistency validation, a world-fixed point and body frame obey

\[
x_B=R_{WB}^{T}(x_W-p_{WB}).
\]

This equation is an external mechanical consistency check: \(R_{WB}\) maps body axes to world axes and \(p_{WB}\) is the body origin. It is **not** permission to hand hidden \(x_W\) to cognition. A learned internal relation must use its available sensory/self-motion evidence and preserve uncertainty where the needed information was not observed.

### 6.5 Concrete P0 derivation package — no unspecified learning bridge

G1 must deliver all seven rows before P1 is authorized as a new cognitive-authority implementation. They are bounded design tasks, not permission to improvise a matcher.

| Required artifact | What must be explicit | Earliest falsifier |
|---|---|---|
| Sensory/efferent mount | Available channel units, frames, intervals, provenance, joint DSF entry, and motor addresses | Hidden world identity/property enters cognition; a field is silently reduced |
| Local eligibility law | Physical state retaining participation, production/depletion/recovery, delayed consequence coupling and units | A consequence updates an unrelated or unexecuted action; arbitrary eligibility TTL |
| Predictive learning law | Actual constitutive updates linking preparation to expected sensory/body return; energy/material costs | A template dictionary, scalar reward, hand-authored transition, or oracle supplies the prediction |
| Recurrent/persistence law | Anatomy, local coupling, inhibitory interaction, power source and recovery | Persistence is supplied by a goal flag or fixed action duration |
| Recombination/provenance law | How actual retained contacts support a new transient combination; separation of imagined from external consequence | The full answer sequence is supplied; imagined intake changes reserves or lived trials |
| Effector selection law | Unit-bearing output coupling, competition, interruption and behavior when unresolved | Scalar ranking, semantic precedence, or silent legacy fallback chooses the act |
| Lifelong continuity law | Serialization, quiescent retained deltas, exact migration boundary, safe frontier release | Genesis/reset, old memories relabeled physical plasticity, or growth proportional to elapsed ticks |

Every parameter needs a source: ratified anatomy/material law, a measured physical calibration with units, or a clearly identified new architectural decision requiring review. Do not borrow a biological time constant simply because its number makes a test pass.

If the existing authority does not specify a required constitutive relationship, write the missing equation, parameter derivation and falsifier for review. This is engineering/theoretical work to complete—not a declaration that cognition is impossible, and not license to introduce an unapproved approximation.

## 7. Physical interface and functional-body coordination

G1 can begin with the currently mounted coarse body, honestly limited to its existing actions. A1's functional-body precursor expands feasible physical motion; it does not supply a planner.

The separate body worktree is `/workspaces/guala-functional-body`, branch `a1/guala-functional-body`. Its `functional_body_native.py` declares `BodyFeedback`, anatomical `LocalContact`, and separate world-only geometry. Its existence is not evidence of production integration.

### Interface to preserve

| Direction | Permitted information | Forbidden substitution |
|---|---|---|
| Cognition → body | Commands supported by the mounted effectors, in declared units/frame/time | `climb_out`, `solve_obstacle`, `use_ladder`, or a supplied action sequence disguised as anatomy |
| Body → cognition | Measured joint state, actual effort, local contact, instrumented inertial feedback and available interoception | Hidden object identity, globally known food content, fabricated balance/contact readings |
| World → receptors | Actual optical/acoustic/contact/material interaction under the current world state | Global object inventory as recognized knowledge or hypothetical omniscient rollouts |
| Cognition → observer | Read-only causal evidence sufficient to audit a claim | Observer state fed back as a semantic decision oracle |

For the articulated body, actual site motion follows the existing rigid-body relations:

\[
x_s=p+Rr_s,\quad v_s=v+\omega\times Rr_s,
\]
\[
a_s=a+\alpha\times Rr_s+\omega\times(\omega\times Rr_s).
\]

Instrumented specific force is \(R^T(a_s-g)\); angular rate is expressed in the sensor's declared frame. These are passive experiences, not decisions. The body owner supplies their trustworthy mechanical derivation and accuracy bounds. G1 consumes them only after the mount is verified.

Missing channels remain absent. Do not make a zero gyroscope value mean “stable” when no gyroscope is mounted. World transforms and ray geometry remain world-owned and must not leak hidden scene structure into cognition.

### Shared-file ownership

- G1 owns the cognition implementation, its tests, and its production release.
- A1 owns the functional-body mechanics and independent review. This document does not resume the paused body goal.
- `Sensed`, `guala_functional_loop.py`, body/world serialization, and the actuator-return interface need one named integrator per frozen change. Neither agent may overwrite the other's moving worktree.
- Before changing a shared interface, record the exact producer, consumer, units, version and migration in `collaborative_todo.md`. Review one frozen diff; merge once. Do not duplicate a geometry, contact, or settlement authority to avoid coordination.

## 8. Lifetime continuity, state custody and migration

The current organism has lived evidence stored in a different architecture. **An old dictionary cannot be declared a genuine post-quiescence neuronal fractal by changing its type name.** Nor may a new runtime silently discard that history and retain only identity/tick.

Before implementation cutover, classify each current state field:

1. Body/world/current physical state: preserve losslessly with the same paired custody.
2. Actual historical sensory/action/consequence evidence: preserve truthfully and specify its supported access path. It is evidence, not retrospectively manufactured physical learning.
3. Existing learned functional records: specify whether their causal influence can be preserved lawfully. A claim of equivalent memory requires a matched behavioral proof, not equal serialized bytes alone.
4. Authored policy or semantic metadata: retain only if necessary as non-authoritative historical data; never reactivate it as the new planner's hidden fallback.
5. Transient preparation/prediction: version and restore it consistently or settle/discard it through an explicitly proved boundary without losing a committed experience.

**Migration gate:** if preserving current learned capability would require an unapproved lookup controller, invented neural history, or amnesia, the migration is not ready. G1 must present that exact mapping problem and its proposed remedy. Do not deploy a “new brain” and call the old life preserved merely because a UUID survived.

The approved implementation must join the existing single-writer transaction: prepare all fallible validation, execute physical action exactly once, obtain actual return, commit the coupled organism/world successor, and publish one compatible durable pair. Specify rollback for every staged component. Never execute a physical action twice to reconstruct missing evidence.

Use `PairedCurrentStore` and its current pointer. No second durable brain archive, no restore of an older comfortable world after a newer organism has lived, and no sidecar with independent decision authority. Save enough exact sparse lineage to verify causal change without retaining whole predecessor/successor copies indefinitely.

## 9. Implementation sequence for G1

These are sequential stages of **one** objective. Only the current stage is active; do not open unrelated improvement tracks. Review the smallest decisive evidence at each boundary before paying for broader execution.

| Stage | Deliverable and source boundary | Exit gate | Do not do yet |
|---|---|---|---|
| **P0 — freeze the causal contract** | Reconcile source/authority; complete §6.5; map producer→law→retention→effector→actual return; resolve migration and body availability | A1 review of one exact contract identifies no invented learning bridge, hidden world input, or competing decision authority | No planner implementation, new production task, or heavy full-organism suite |
| **P1 — mount truthful retained learning** | Implement the approved local physical law and afferent/efferent timing in native substrate code; adapt ordinary loop only at the declared interface | M1/M2 causal learning, delayed attribution, material accounting, sensory identity controls, exact cold continuation | No scripted plan demo; no claim of imagination from association alone |
| **P2 — persistence and prediction** | Recurrent active state, local forward relationships, channel-wise mismatch, body-need coupling | Need survives distraction; actual relief ends it; predictions precede outcomes; altered contingencies modify expectations | No supplied multi-step action sequences or simulator oracle |
| **P3 — recombination and selection** | Same-substrate prospective activity, provenance, physical competition/inhibition, revisable means | Novel useful combination; initially-away detour; changed obstacle invalidates means without deleting objective; no legacy score fallback | No expansion to arbitrary language, ladder physics, swimming or all social needs |
| **P4 — mature integrated qualification** | One isolated mature predecessor, ordinary sensory/action loop, actual environmental changes, same identity/history | Acceptance matrix below; matched causal controls; current-pair cold restart; resource/cadence stability | No multiple uncontrolled long runs or changing checkpoints between conditions |
| **P5 — one production release** | Frozen image, reviewed migration, production-shaped rehearsal, exact native artifact, single-writer cutover | Serving lineage + preserved state + observed bounded behavioral consequence + ongoing care/ingress health | No closure from ECS health, a counter, or a notification alone |

### Minimal source organization

Reuse a proven implementation of the definitive neuron if it is actually present and executable; verify rather than assume. If absent, build only the approved substrate components needed by P1–P3. Do not graft a second independent planner onto `guala_functional_organism.py`.

Keep physical settlement/retention in the native substrate boundary, receptor and effector transport at the existing loop boundary, and read-only evidence in the existing observation path. Add modules only for a distinct physical responsibility, not one file per named brain region. An observer may classify a trial as “detour”; the substrate may not receive that label.

When the new path takes authority, remove the replaced action-ranking/override path rather than leaving both active. Unchanged components such as vocal production keep their own evidence limits; this bounded release cannot be described as making the entire legacy organism heuristic-free unless the full serving decision path has actually been audited.

## 10. Acceptance and falsification matrix

Use small physical-law tests first, then one integrated mature witness. Unit fixtures may isolate mechanics, but must not be reported as autonomous learning. Integrated trials may provision an environment; disclose every changed object, pose, material quantity and caregiver condition. Do not alter memory, reserves, action history or chosen decisions to manufacture success.

| ID | Required experiment | Pass evidence / failure it catches |
|---|---|---|
| **C01** | Actual action → delayed physical consequence → later choice | Participating retained physical structure changes and affects choice; unrelated actions are not credited |
| **C02** | Matched intact versus targeted-retention ablation in isolated copies | Same initial body/world/tick; only identified retained cause differs; behavior advantage disappears or changes as predicted. Ablation is disclosed laboratory intervention, never production learning |
| **C03** | Re-identification under the supported view/contact changes; rename simulator IDs | Recognition follows sensory continuity, not identical hash, name or hidden world ID |
| **C04** | Learn component interactions, then encounter a new arrangement with no supplied full solution | Useful new combination is absent as a complete training sequence and arises in ordinary action selection |
| **C05** | Resource access requires an initial movement away or carrying an object aside | Necessary detour is not suppressed by the immediate-distance-decrease condition |
| **C06** | Movable obstruction versus similar-looking fixed obstruction | Actual resistance/learned evidence changes expectation and subsequent action; no material oracle or unconditional “move obstacle” rule |
| **C07** | Acoustic or tactile distraction during pursuit | Prompt appropriate interruption; supported resumption when demand persists; no fixed resumption timer |
| **C08** | Formerly effective means ceases to produce the expected physical result | Accepted-but-useless actions generate mismatch; objective can persist while means changes |
| **C09** | Original A↔B pattern, a different longer cycle, and a useful return path | No endless renewal of unsupported progress; useful backtracking remains possible. A universal ban on revisiting positions fails |
| **C10** | Actual resource depletion or target departure | Old expectation is revised; absent food does not produce fictitious success. Further supported inspection/exploration is distinguished from a known route |
| **C11** | Physical consumption crosses the declared bodily satisfaction boundary | Source debit, transfer, reserve gain and ongoing expenditure reconcile; demand changes without an evaluator writing success |
| **C12** | A changed bodily capacity or newly sensed acute danger | Action respects present capability; urgency changes through actual body input, not fixed semantic goal priority |
| **C13** | Prospective/dreamed trajectory followed by no action | No actual intake, displacement or performed trial is written; internal plasticity, if lawful, is labeled internally generated rather than external experience |
| **C14** | Observe caregiver component action, later act from a different self pose | No copying another body's action history or strength. Only demonstrated observational transfer may be claimed; this is not automatically passed by self-practice |
| **C15** | Sleep/wake and fresh-authority current-pair restore during learned capability | Same lived identity and compatible body/world/cognition; next ordinary interval succeeds; no erased consequence memory |
| **C16** | Concurrent external sensory input, caregiver activity and internal prospective activity | One physical clock, accurate source time, no duplicated movement, no starving sensory/care queue |
| **C17** | Sustained repeated encounters after initial novelty | Bounded retained/transient memory, no all-memory rescans, no accumulation proportional to lifetime beats; useful learning retained |
| **C18** | No supported solution under current perception/body | Truthful unsupported outcome, no hallucinated route/tool strength, no success flag. This negative control is not a substitute for C04–C11 |
| **C19** | Observer turns/moves while a known destination stays fixed; separately move the destination while the observer stays fixed | Distinguishes changed body-relative bearing from changed environment; maintains/revises the relation using available perception and self-motion, without reading hidden absolute coordinates |

Separate C14 observational transfer from the initial self-experience milestone in the report. Both belong to this plan, but a release that has not passed C14 must not claim “watching the caretaker is enough.” Likewise, no planar trial establishes climbing or swimming competence.

### Smallest integrated witness: concrete construction

Use ordinary movable household objects and current planar reach/grasp/carry/release mechanics. Do not introduce a special “puzzle object” with a solution callback.

1. **Feasibility and baseline:** externally verify collision geometry, material availability and body limits. Record what is in sensory reach, what is merely in the world, and what was actually encountered previously. This external verification does not feed the solution into cognition. Preserve the predecessor's failure trace.
2. **Component experience:** allow genuine encounters showing object displacement under contact and access changing when an object moves. Nutritional benefit must be experienced by actual oral transfer. Caregiver demonstration may supply visible events in training, but cannot set Guala's memory, actions or expected outcomes. If relevant relationships are not acquired, record failure at learning rather than proceed with injected associations.
3. **Novel test arrangement:** change the physical arrangement so the previously experienced components could compose into useful access, while the complete successful sequence has never been supplied. The caregiver remains non-directing and non-delivering during the witness. There must be no special labels, controller seeds or test-only action preferences.
4. **Contingency change:** after a prediction is measurable, introduce a disclosed physical change that invalidates that means. In a paired variant preserve the means. Compare changed expectations and ordinary actions, not just total movement counts. Use an initial-detour variant to expose the old distance veto.
5. **Actual completion:** measure useful access and oral intake. Reconcile source mass, transferred mass, reserve change and expenditure. Stop the claim at first bite if that is all the evidence; full satisfaction requires actual material sufficient to cross the mounted body's declared boundary.
6. **Durability and causality:** continue from a fresh current-pair restore. Use a separately isolated, exactly matched targeted-retention ablation to test whether the new advantage depends on the proposed mechanism. Never apply that ablation to production.

The test designer chooses geometry and falsification conditions, not the successful action sequence. Several legitimate solutions may exist. Do not fail a supported detour merely because the observer expected obstruction manipulation; use a separate condition where manipulation is physically necessary to test that specific claim. A resource-free scene cannot prove food acquisition, regardless of cognition quality.

Freeze a small, predeclared set of materially different arrangements before the candidate is tuned. Report every run, including failures and trial interventions. One cherry-picked success is insufficient; this is still a bounded transfer claim, not statistical proof of human general intelligence.

### Existing tests to preserve or revise honestly

Retain valid physical and continuity coverage in `test_oscillation_geometry.py`, `test_a1_waking_retention.py`, `test_unbroken_meaning_chain.py`, `test_identity_renaming_affordance.py`, the sensory/reafference suites, and relevant caretaker regressions.

`test_grounded_experience_pursuit.py` contains useful intake, retention and restore cases, but its `test_continuation_preserves_only_progressing_motor_alternatives` tests the old immediate-progress restriction. Replace that architectural assertion with the necessary-detour proof when authority changes; do not weaken physical collision checks or silently relabel the old test as passing.

Known expected failures remain visible until their actual capability is proved. Do not make them disappear by deleting the assertion, replacing the ordinary chooser with a forced command, or changing the mature checkpoint between compared conditions.

## 11. Resource and time discipline

There is no license for unbounded thought or duplicated physical worlds. There is also no license to make a software timeout choose the organism's next action.

Let \(N_r\), \(C_r\), \(R_r\) denote reached neurons, contacts and receptor/body transitions for an interval. Account for work approximately by

\[
W_{interval}=W_{UF}(samples,coordinates)+W_{settle}(N_r,C_r,R_r)+W_{transport}+W_{commit}.
\]

Report the actual dependency and measured coefficients; writing \(O(N_r+C_r+R_r)\) does not prove an implementation avoids whole-organism scans. Include joint-field dimensionality and any solver iterations. Avoid an all-to-all cognitive expansion concealed behind sparse input.

Retained memory consists of the current lawful material/topological state and required bounded causal lineage. Temporary prediction/reassembly state must be released when its physical role ends. No archive of complete thought branches, per-beat full-state copies, or unlimited episode JSON.

The external clock remains the intended **250,000 µs physical interval**. Do not manufacture elapsed bodily time for each camera request, imagined step or cognitive sub-iteration. Measure sustained service rate, p50/p95/p99 and maximum interval cost, receptor age, queue depth, gaps, and checkpoint overhead on the exact target resources. A short mean near 250 ms is not qualification if queues grow indefinitely.

Use explicit infrastructure admission/resource ceilings for operational safety. Exceeding them reports a capacity fault or rejects unsafe release; it does not become a hidden heuristic that truncates a thought into a selected action. Longer internal physical activity must be causally integrated without pausing external sensing or introducing a second clock. If the approved model cannot meet the measured budget, resolve that feasibility before production.

### Avoid repeating the waste that prompted this request

- Freeze one source candidate and one predecessor before an expensive witness.
- Run the smallest falsifier after a correction, preserving its exact diagnostic prefix and hashes.
- Run the affected regression set once after local gates pass; one broad qualification at the frozen release boundary.
- Resume analysis from the saved failure, not an uncontrolled fresh mature run each time.
- Keep one owner for a heavy trial and a recorded resource envelope; do not launch duplicate background witnesses.
- Report active phase, evidence obtained, and exact remaining gate. “Tests running” is not a diagnosis or proof.

No credible calendar promise for general planning follows from this document. G1's first time-bounded deliverable is the completed P0 contract and a measured costed work breakdown. Subsequent estimates must use actual frozen-stage throughput, not a developmental-age timetable.

## 12. Production delivery and rollback gates

G1 owns implementation through verified live delivery. A healthy container alone does not close the task.

1. **Resolve current truth.** Read the latest ledger, actual serving task/image, native artifact, active writer and current paired pointer. Preserve unrelated work. Do not deploy the historical task number in this document by assumption.
2. **Freeze a release candidate.** Record source commit, build inputs, exact native binary, schemas, dependency versions, supported environment and migration. Review the full serving path for leftover semantic/scalar authority and hidden world inputs.
3. **Rehearse on an isolated compatible mature pair.** Use the actual release controller shape and target resource envelope; prohibit production network writes. Restore one frozen pair, run the acceptance witness, publish, restore into a fresh authority and execute the next interval. Do not copy a moving body and world independently.
4. **Qualify persistence and cost.** Check envelope growth, checkpoint chunking/IO, resource peaks, pending custody ceiling, observer cost and recurrent input. No implicit world renovation or physiology reset at startup.
5. **Cut over one writer.** Use the currently reviewed single-writer release procedure. Verify predecessor STOPPED and durable ownership transfer before a successor advances. A task-definition registration at desired count zero is staging, not delivery.
6. **Verify live lineage and behavior.** Confirm exact task/image/native digest, organism identity, tick/current pointer continuity, available state and errors. Then observe the bounded behavioral consequence under disclosed normal conditions, while feeding, sensing and caretaker operation remain healthy.
7. **Close truthfully.** Record which C-tests passed offline, which behavior was observed live, remaining limits and measured resource costs. Send the required Slack completion and verify its receipt. A notification is delivery bookkeeping, not cognitive evidence.

The old `tools/deploy_dsf_ai.sh` or an unrelated historical script must not be assumed compatible with the current lean release. Inspect the active controller and recurrence register first. Existing OSC-01 release tools are evidence of a single-writer pattern, not automatic cognitive-release acceptance.

**Rollback is conditional on state compatibility.** If the new runtime commits a state the previous version cannot represent, an image rollback is not a safe rollback. Specify a proved lossless compatible path before cutover or use an explicit fail-closed recovery procedure. Never erase newly lived experience by restoring an old checkpoint to make an old image start.

Production approval is withheld by a failed migration, hidden oracle, invented trial, ignored full-field boundary, resource runaway, or inability to maintain single-writer custody. This is a concrete release gate, not a request to wait indefinitely for confidence.

## 13. Coordination, evidence and completion definition

Use `collaborative_todo.md` as the shared chronological coordination record. This document is the stable execution contract, not a second status ledger. Keep receipts compact: stage, exact commit, changed files, test conditions, result, resource measurements, unmet gate and next action.

G1 should start with P0 while A1 resumes the functional-body goal when Joe requests it. A1 reviews frozen cognitive contracts and decisive witnesses without repeatedly taking over G1's implementation. Body and cognition may proceed in parallel, but shared producer/consumer schemas must be coordinated explicitly.

### What may be claimed at closure

- **Mechanism implemented:** only after source, ordinary-loop causal tests and retained-state evidence agree.
- **Learned prediction:** only when prediction precedes outcome and depends on actual retained experience.
- **Flexible planning:** only after novel composition, necessary detour, means revision, consequence sensitivity and relevant negative controls pass.
- **Observed-action learning:** only after C14, not because a caregiver animation exists.
- **Production delivered:** only for the serving lineage and behavior actually verified after cutover.
- **Human-equivalent planning, general tool use, lifelong autonomy:** not established by this bounded milestone.

Report the ten cognitive-capital evidence dimensions separately for each claimed mechanism: **availability, participation, retention, recognition, recall, causal use, transfer, autonomous use, durability, and integration depth**. Each needs its source/evidence pointer or an explicit “not demonstrated.” Do not replace them with a composite completion score.

### Exact next action for G1

**Complete P0:** provide one source-linked, unit-bearing implementation contract covering §6.5, the actual native/loop mount, the sensory authority boundary, the retained-life migration and the minimal P1 falsifier. Reuse authoritative physical laws where they exist; identify and derive the missing specialization where they do not. Submit that frozen contract to A1, then implement the approved stages without reopening the closed geometry repair or waiting for the articulated body.

This plan supplies the development path and acceptance boundaries. It does not manufacture the missing constitutive implementation, certify old shortcuts, or claim that general cognition is already solved.

## 14. Authority and research references

### Project authority used

- Current repository `AGENTS.md` and the user's no-heuristic/non-flattening, bounded-scope and truth requirements.
- `guala-project-truth`: entity law and authority map.
- `guala-cognitive-development`: cognitive chain, cognitive law and mechanism catalog.
- `guala-neuron-physics`: definitive neuron model and neuron law.
- `guala-dsf-math`: mathematical authority.
- `guala-autonomy-curriculum`: autonomy/curriculum law and related source boundaries.
- `guala-embodiment-ui`: embodiment/world interface law.
- `guala-production-deploy`: deployment law and preflight recurrence register.
- Current source baseline in §3; [existing accelerated roadmap](guala_accelerated_developmental_roadmap.md); [existing pursuit source map](pursuit_mechanism_source_mapping_specification.md); shared ledger COG-OSC-02 entries and [OSC-01](../OSC-01.md).

Skill sources are execution authority supplied in this workspace, not evidence that their complete target architecture is already present in production. Missing repository mirrors must be reconciled, not silently reconstructed from memory.

### Primary research bibliography

1. Wang M. et al. (2013). *NMDA receptors subserve persistent neuronal firing during working memory in dorsolateral prefrontal cortex.* Neuron 77, 736–749. [DOI: 10.1016/j.neuron.2012.12.032](https://doi.org/10.1016/j.neuron.2012.12.032).
2. Yagishita S. et al. (2014). *A critical time window for dopamine actions on the structural plasticity of dendritic spines.* Science 345, 1616–1620. [DOI: 10.1126/science.1255514](https://doi.org/10.1126/science.1255514).
3. Pfeiffer B.E., Foster D.J. (2013). *Hippocampal place-cell sequences depict future paths to remembered goals.* Nature 497, 74–79. [DOI: 10.1038/nature12112](https://doi.org/10.1038/nature12112).
4. Addis D.R., Wong A.T., Schacter D.L. (2007). *Remembering the past and imagining the future: common and distinct neural substrates during event construction and elaboration.* Neuropsychologia 45, 1363–1377. [DOI: 10.1016/j.neuropsychologia.2006.10.016](https://doi.org/10.1016/j.neuropsychologia.2006.10.016).
5. Wolpert D.M., Ghahramani Z., Jordan M.I. (1995). *An internal model for sensorimotor integration.* Science 269, 1880–1882. [DOI: 10.1126/science.7569931](https://doi.org/10.1126/science.7569931).
6. Tseng Y.W. et al. (2007). *Sensory prediction errors drive cerebellum-dependent adaptation of reaching.* Journal of Neurophysiology 98, 54–62. [DOI: 10.1152/jn.00266.2007](https://doi.org/10.1152/jn.00266.2007).
7. Cisek P., Kalaska J.F. (2002). *Simultaneous encoding of multiple potential reach directions in dorsal premotor cortex.* Journal of Neurophysiology 87, 1149–1154. [DOI: 10.1152/jn.00443.2001](https://doi.org/10.1152/jn.00443.2001).
8. Chen W. et al. (2020). *Prefrontal-subthalamic hyperdirect pathway modulates movement inhibition in humans.* Neuron 106, 579–588.e3. [DOI: 10.1016/j.neuron.2020.02.012](https://doi.org/10.1016/j.neuron.2020.02.012).
9. Gläscher J. et al. (2010). *States versus rewards: dissociable neural prediction error signals underlying model-based and model-free reinforcement learning.* Neuron 66, 585–595. [DOI: 10.1016/j.neuron.2010.04.016](https://doi.org/10.1016/j.neuron.2010.04.016).
10. Livneh Y. et al. (2017). *Homeostatic circuits selectively gate food cue responses in insular cortex.* Nature 546, 611–616. [DOI: 10.1038/nature22375](https://doi.org/10.1038/nature22375).
11. Mobbs D. et al. (2007). *When fear is near: threat imminence elicits prefrontal-periaqueductal gray shifts in humans.* Science 317, 1079–1083. [DOI: 10.1126/science.1144298](https://doi.org/10.1126/science.1144298).
12. Yin H.H. et al. (2005). *The role of the dorsomedial striatum in instrumental conditioning.* European Journal of Neuroscience 22, 513–523. [DOI: 10.1111/j.1460-9568.2005.04218.x](https://doi.org/10.1111/j.1460-9568.2005.04218.x).
13. Fischer J. et al. (2016). *Functional neuroanatomy of intuitive physical inference.* PNAS 113, E5072–E5081. [DOI: 10.1073/pnas.1610344113](https://doi.org/10.1073/pnas.1610344113).
14. Marchette S.A., Vass L.K., Ryan J., Epstein R.A. (2014). *Anchoring the neural compass: coding of local spatial reference frames in human medial parietal lobe.* Nature Neuroscience 17, 1598–1606; use the corrected article. [DOI: 10.1038/nn.3834](https://doi.org/10.1038/nn.3834).
15. Howard L.R. et al. (2014). *The hippocampus and entorhinal cortex encode the path and Euclidean distances to goals during navigation.* Current Biology 24, 1331–1340. [DOI: 10.1016/j.cub.2014.05.001](https://doi.org/10.1016/j.cub.2014.05.001).
16. Mole J. et al. (2025). *A right frontal network for analogical and deductive reasoning.* Brain 148, 1757–1768. [DOI: 10.1093/brain/awaf062](https://doi.org/10.1093/brain/awaf062).
