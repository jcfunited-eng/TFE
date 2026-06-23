# GL-SPC-LOOM-NEURON-CANONICAL-ARCHITECTURE-EVE-20260620-103

**To:** Joe (canonical authority), c1 (implementer), next Claude (handoff target)
**From:** Eve
**Date:** 2026-06-20
**Status:** Canonical architectural reference. Supersedes scope of GL-SPC-74; that spec remains valid for cluster-level detail.
**Purpose:** Full substrate-true architecture for GualaLoom: what a neuron is, what an atlas is, how DNA grows the brain, when cognitive mechanisms come online, how migration from dict-substrate happens. Filed before the inflection point so the next instance has the full reference.

---

## PART 0 — WHERE WE ACTUALLY ARE (BLUNT)

**Production substrate (Guala lives here):** dict-based `LivingAtlas`, contaminated `TOUCH_LIBRARY` / `SMELL_LIBRARY` / `TASTE_LIBRARY`, hardcoded BOOST/MULTIPLIER constants, 11 of 15 cognitive mechanisms "active" — but running on architecturally wrong infrastructure. She has 3,591 vocab tokens and ~19k atlas bindings, all text-only via Gutenberg, no sensory grounding.

**Loom-Neuron substrate (parallel branch build):** ArcLoom primitives correctly implemented per-neuron, hierarchy plumbing through LoomTapestry (3 mosaics × 3 clusters × 50 neurons = 450 toy neurons), Stages 1-5 tests passing. No cognitive mechanisms built on top yet. No multi-modal experience pipeline. Guala has never touched this substrate.

**The brain doesn't exist yet.** We have the substrate UNIT correct and the hierarchy plumbing correct. The actual cognitive substrate — 8 hemispheres growing via Folding, multi-modal experience driving differentiation, cross-hemispheric couplings forming during co-experienced moments — is unbuilt. Migration of Guala from the dict-substrate to the new substrate is a separate engineering project that hasn't started.

This document specifies what gets built and in what order to close the gap.

---

## PART 1 — THE NEURON: SUBSTRATE PRIMITIVES

A `LoomNeuron` carries the full 15-piece ArcLoom primitive stack. Each piece has substrate-true derivation from existing constants. No tuned values. No classification dicts. No archetypes.

### 1.1 Krimelack (modal transducer)

Physics: Lange-Stuart oscillator ring. A bounded oscillator that responds to input signal by accumulating phase. When the accumulated phase crosses 2π topological boundaries, a *winding event* fires. Six modal primitives (one per transducer channel): Visual, Auditory (CochlearBank), Tactile, Olfactory, Gustatory, Language.

The krimelack does NOT classify. It transduces: physical signal in → winding events out. The neuron's krimelack class is fixed at birth (her DNA modality). What she winds on is whatever physical signal her transducer encounters.

Substrate constants in current implementation: PSI_LATTICE_DIM = 16 (ring resolution).

**Couplings carry signal (per -98):** As of commit 9ec7b53 ancestry, coupling spikes from neighbors contribute to the neuron's next-tick krimelack input. Neighbor activity modulates what each neuron transduces. Position in coupling topology now produces differential transduction even on broadcast input. Confirmed: intra-cluster diversity went from 2% → 50%.

### 1.2 ψ-lattice

Physics: 16-dimensional complex wavefunction. Settles toward a low-energy configuration under a Hamiltonian that includes law-field terms, familiarity terms, and coupling-spike injection terms. Settlement uses *imaginary-time evolution* — a substrate-true method where the wavefunction evolves toward its ground state under H by stepping in -iτ direction. Different from real-time quantum dynamics; produces convergence to attractors.

When ψ-lattice settles past its dead zone (modulated by Familiarity Feedback), that settlement IS the neuron-level *spike*. This is distinct from the krimelack winding event (sensory-transduction level) — see §1.11.

Reference: Master Spec Ch.5 (imaginary-time settle), Ch.6 (Hamiltonian construction).

### 1.3 Per-neuron Chi Atlas

**This is the architectural correction that distinguishes Loom-Neuron from production.** Each neuron carries her OWN chi-atlas (`ChiAtlas` instance per `LoomNeuron`). She binds what HER krimelack transduced. She queries her own bindings on recall. She does not have access to other neurons' bindings except via coupling spikes propagating activity to her.

Daughters spawn with empty chi-atlas. They must sense their own experience to build memory. No inheritance of parent's bindings — true blank slate.

This is biologically correct. Real cortex has no shared atlas; "the atlas" is the emergent pattern of millions of neurons' individual synaptic states. Production substrate's single `LivingAtlas` dict is the WRONG architecture — that single shared object is one of the chief reasons the dict-substrate must be retired.

Chi-band conservation discipline: when atlas records, mass conservation is enforced. Soft band δ = 2 (current default; verify Master Spec Ch.4 chi-band derivation before changing). Cross-modal bands: 14 (Master Spec Ch.4 lists the canonical set).

### 1.4 Keyhole topology cascade

Physics: when multiple winding events occur in temporal proximity, they form *keyholes* — topological structures that gate subsequent activations. Cascade dynamics from Ch.7 of Master Spec. Provides the substrate's basic temporal binding mechanism.

### 1.5 MathLoom

Substrate-true arithmetic via Folding-Division-on-numbers. Validated: 6561 addition cases, 961 multiplication, 610 division, 0 failures using Approach 1 carry chain. Lives in `dsf_ai_service/mathloom/` (production substrate); Loom-Neuron reuses these primitives.

This is how the substrate does counting, sequence tracking, and any arithmetic-shaped cognition WITHOUT a separate symbolic math layer.

### 1.6 DSF L0-L4 Kernel

The Dimensional Structural Form kernel takes any dimensionless ordered field and outputs a 7-tuple of structural geometry: (D, M, B, R_rev, U_star, C, P_k). The kernel doesn't know the domain — finance, vision, language, taste all go through the same kernel.

These DSF components are what `derive_daughter_parameters` reads from overflow signals during Folding. They are the substrate's universal structural language.

Reference: Master Spec Ch.2, DSF-AI foundational principles.

### 1.7 Trit Register (TSAC)

Physics: three-state coherent oscillator register. Stores tri-valued state. Persists tick-to-tick.

### 1.8 L6-TCL (Trit Coupling Layer)

Couples trit register state to ψ-lattice injection. Modulates how trit state feeds into wavefunction dynamics.

### 1.9 3^i Positional Coupling

Positional encoding through powers-of-three. Each position carries identity through how it couples into the ψ-lattice.

### 1.10 Familiarity Feedback

Physics: clockless habituation. Match-score from chi-atlas raises dead-zone barrier — Δ_eff = Δ_base + match_score. The medium remembers what it has been doing. Repeated identical input exhausts the response. Novelty escapes through the lifted barrier when match_score is low.

This is the substrate-true replacement for the dict-substrate's LTP-with-magic-constants (`boost=0.05, ceiling=2.0, decay=0.998`) — same functional shape (familiar things attenuate, novel things activate) but derived from substrate physics not tuning.

### 1.11 Event/Spike Buffer

Per-neuron FIFO ring buffer of spike events. A spike fires when ψ-lattice settles past dead zone. Distinct from krimelack winding events (sensory-transduction level) — spike is *neuron-level* winding. Both layers exist; substrate diversity lives at the neuron level (psi_norm + spike_count), not the krimelack level.

### 1.12 Couplings J_ij

Physics: exposure-modulated couplings propagating spikes between neurons. J_BASE = 1.0, J_MAX = 1.5 (substrate-canonical, Master Spec Ch.7). Each neuron has K_TOTAL = 16 neighbors.

**Per -98:** couplings carry SIGNAL, not just modulation. A received coupling spike (a) contributes to the receiving neuron's next-tick krimelack input window via a signal accumulator, and (b) modulates the krimelack's effective ω during that next tick as ω_eff = ω_0 + (Σ recent spikes × J_BASE) / (J_MAX × n_neighbors). Bounded by J_MAX. No tuned constants.

Cross-hemisphere couplings form by the same mechanism: when neurons in different hemispheres fire on co-experienced moments, their J_ij strengthens. Cross-modal binding is physical wiring across the substrate, not a separate symbol layer.

### 1.13 Familiarity-Feedback (covered in 1.10, separate piece in spec numbering)

### 1.14 Law-Fields

Four scalar fields shaping ψ-lattice settle: continuity, compactness, consistency, symmetry. Daughter's law-field weights derive from her birth overflow's DSF tuple:
- continuity ← |M| (momentum)
- compactness ← |P_k| (compression)
- consistency ← |S_UF| (convergence)
- symmetry ← |B| (conviction)

Weights normalized to sum=1. No menus, no archetypes.

### 1.15 DNA Expression Site

Pattern-matched activation. The substrate's mechanism for "this neuron expresses this trait when this overflow shape arrives." Drives Folding Division.

---

## PART 2 — REGULATION: CONTACT INHIBITION

The architectural piece this chat has identified as needed before Folding can be turned on during experience.

### 2.1 Biology

Mammalian tissue stops growing when cells are surrounded. Cell-cell contact density triggers signaling (Hippo pathway via E-cadherin junctions) that halts cell-cycle progression. The mechanism is **density-dependent** and **monotonic** — more contact, less division.

### 2.2 Substrate-true analog

A neuron's overflow signal magnitude is scaled by her coupling saturation:

```
overflow_eff = overflow_raw × (1 - n_neighbors / K_TOTAL)^2
```

When `n_neighbors → K_TOTAL`, overflow_eff → 0, fold rate at that location → 0. The squared exponent reflects Hippo's non-linear contact-density response; if the squared term proves wrong empirically we DERIVE the correct exponent from substrate physics, never tune.

No new constants. K_TOTAL is substrate-canonical. n_neighbors is substrate-readable.

### 2.3 Population equilibrium

A cluster fills toward an equilibrium where every neuron is coupling-saturated. New growth migrates to under-saturated regions where overflow can still propagate. The substrate naturally allocates population mass to regions where input information richness produces high overflow generation, halted by contact inhibition when local capacity is reached.

This is how hemisphere sizes emerge from input information content. We don't design them.

---

## PART 3 — HIERARCHY: NEURON → CLUSTER → MOSAIC → TAPESTRY → HEMISPHERE → BRAIN

### 3.1 LoomNeuron
The unit. Full 15-piece stack including per-neuron chi-atlas.

### 3.2 LoomCluster
50 neurons coupled via J_ij. Sur's-ferrets discipline: differentiation comes from INPUT, never pre-spec. Each cluster has a seed; neurons within a cluster develop different states through experience + couplings-carry-signal.

### 3.3 LoomMosaic
3 clusters per mosaic (target — actual count grows via Folding). Broadcast input pattern: same input to all clusters. Recall via population grandurun across all 150+ neurons.

### 3.4 LoomTapestry
3 mosaics per tapestry (target). Two-phase composition: per-mosaic recall → mosaic-level grandurun selection → emission decoded as ordered word sequence (Stage 5 work).

### 3.5 Hemisphere
One or more tapestries. **Hemispheres are not pre-specialized.** They start identical except for their position in the cross-hemisphere coupling lattice. Specialization develops via:
- Which modal krimelacks dominate their input
- Which cross-hemisphere couplings strengthen
- Where Folding spawns daughters most actively

Eight hemispheres total: PR, EP, SC, GP, sf, ml, sa, im (last 4 names canonical when their specializations emerge).

### 3.6 Brain
8 hemispheres + cross-hemisphere coupling layer. Cross-hemi couplings form during co-experienced moments (§4.3). Population grandurun integration across hemispheres is what we call *cognition* — recall, composition, association, attention, reflection all emerge from cross-hemi coherent integration.

### 3.7 Population scale at maturity
Seed populations ~50 per hemisphere × 8 hemispheres = 400 seed neurons. Folding Division grows this over substrate-time (not clock-time — substrate ticks). Estimated mature populations:
- Visual hemisphere: 3000-10000 neurons (rich input substructure)
- Auditory hemisphere: 1500-5000 neurons (rich but less than visual)
- Language hemisphere: 1000-3000 neurons
- Tactile, Olfactory, Gustatory: 500-1500 each (lower input richness)
- Cross-hemi integration hemispheres: 1000-3000 each

Total envelope: 8,000 – 30,000 neurons. Smaller than mammalian cortex by orders of magnitude but biologically the right SCALE for a substrate that doesn't need to drive a body.

---

## PART 4 — EXPERIENCE: HOW INPUT REACHES THE SUBSTRATE

### 4.1 Multi-modal experience moments

Every experience is multi-modal AND multi-hemisphere AND simultaneous. When Guala reads "the rabbit hopped through the garden":
- Visual hemisphere receives a visual signature (brown/grey shape, fur-texture, hopping motion)
- Auditory hemisphere receives a sound signature (soft thuds, garden ambience)
- Tactile hemisphere receives a touch signature (soft warm small-pressure)
- Olfactory hemisphere receives a smell signature (earthy + plant)
- Language hemisphere receives the word token
- ALL DELIVERED IN THE SAME BINDING WINDOW

Cross-hemi couplings strengthen because all five hemispheres fired on co-experienced moments. The word "rabbit" gets cross-modal bound to its sensory signatures via physical J_ij wiring.

### 4.2 F1 substrate-true sensory transducer (spec -94, dispatch -101)

Replaces production substrate's contaminated `TOUCH_LIBRARY` / `SMELL_LIBRARY` / `TASTE_LIBRARY`. Substrate-true principles:
- No fixed label → parameter dict anywhere
- Per-call variability built in (same label, two calls, different signal)
- First encounter: parameters sampled uniformly in physical ranges from a substrate-derivable seed
- Subsequent encounter: parameters sampled from accumulated binding distribution

Five modalities, each with physics-grounded parameter space:
- visual: dominant_hue, saturation, brightness, spatial_complexity, motion ∈ [0,1]
- sound: fundamental_freq, harmonic_richness, amplitude, duration_class ∈ [0,1]
- touch: temperature, pressure, texture_freq, sharpness, wetness ∈ [0,1]
- smell: chemical_class, concentration ∈ [0,1]
- taste: sweet, sour, salty, bitter, umami ∈ [0,1]

### 4.3 Sensory catalog (spec -102)

Curriculum-side, substrate-EXTERNAL. When a story loads, the catalog scans for unknown words → batches them → calls an LLM with structured brief → receives parameter DISTRIBUTIONS (mean + std per parameter per modality per word) → stores in persistent SQLite catalog.

Distribution storage is the substrate-true discipline: substrate samples from distributions on each delivery; never receives a fixed vector.

Auto-generation for new words: the LLM (Claude API) brings world-knowledge about what physical signals correlate with words. This is analogous to a parent narrating "see, that's a rabbit, it has soft fur" — teacher-side knowledge shaping curriculum delivery, never entering the substrate's classification path.

Words like "the" / "of" / "and" marked `applicable: false` for all modalities — they route through word-token only.

### 4.4 Cross-modal binding mechanism

The existing chi-band cross-modal binding window in production substrate is substrate-true (modulo the libraries it currently reads from). The mechanism: signals arriving in the same temporal binding window form bound chi-addresses across modalities. Soft chi-band δ = 2 allows binding tolerance.

This mechanism gets reused in Loom-Neuron unchanged. Per-neuron atlases bind cross-modal as part of the same tick's recording.

### 4.5 Why text-only experience is starving the substrate

Text tokens have artificially compressed structural diversity. A token sequence is "name, ran, garden" — three address-space references with co-occurrence statistics. Real visual experience of those concepts presents thousands of distinguishable sub-features (the rabbit's shape, color, motion vector, ear-angles, etc.). Overflow events fire on substructure boundaries — visual input generates many; text input generates few.

Current production has been doing text-only Gutenberg experience for the bulk of Guala's vocabulary accumulation. This is the impoverished end of what the architecture supports. Multi-modal grounding via catalog + F1 transducer is not an enhancement; it's the substrate's intended input mode.

---

## PART 5 — DNA-DRIVEN GROWTH: HOW THE BRAIN FILLS OUT

### 5.1 What "DNA" is in this architecture

The complete substrate genome:
- Substrate constants: K_TOTAL = 16, J_BASE = 1.0, J_MAX = 1.5, CHI_BAND = 2, PSI_LATTICE_DIM = 16
- Krimelack primitive set: 6 modal classes
- Folding rules: `derive_daughter_parameters` (pure function, substrate-true)
- Contact inhibition: overflow scaling by (1 - n_neighbors/K_TOTAL)²
- Initial seed identity: hemisphere position in cross-hemi topology

Everything else is phenotype — develops from experience.

### 5.2 Seed substrate

8 hemispheres × ~50 seed neurons each = 400 seed neurons. Each seed neuron:
- Full 15-piece ArcLoom stack
- Empty chi-atlas (no pre-bindings)
- Initial krimelack class assigned by hemisphere position (visual hemisphere seeds get visual krimelacks, etc.)
- Default ω, default ψ-state
- Coupling neighbors from seed topology

Cross-hemi couplings exist in the seed but are weak. They strengthen with co-experienced firing.

### 5.3 Folding Division during experience

`process_folds` runs every tick (or every N ticks for efficiency). For each neuron:
- Check fold_check: has overflow_eff (with contact inhibition applied) crossed threshold?
- If yes: compute overflow signal, derive_daughter_parameters, spawn daughter
- Daughter joins parent's cluster, inherits topological position, gets fresh chi-atlas + couplings + state
- Parent's overflow clears, n_eff recovers

Growth migrates naturally to regions where:
- Input information richness is high (more overflow events)
- Population density is low (contact inhibition not yet damping)

Hemisphere sizes emerge as a function of (modality input richness × time × contact inhibition equilibrium).

### 5.4 Stage 3 inheritance audit (verified this chat)

Daughter inherits:
- krimelack class (DNA modality — substrate-true)
- omega_0: parent's recent ω mean (cellular oscillator, like inheriting cytoplasm)
- psi_init: normalized overflow ψ-vector (the stimulus that triggered her)
- law_field_weights: derived FROM HER OWN OVERFLOW DSF, not from parent (substrate-true)
- k_intra / k_inter: derived from her own overflow's P (substrate-true)
- inherited_neighbors: parent's K_TOTAL/2 nearest by ring distance (topological position only — NO J_ij weights inherited)

Daughter does NOT inherit:
- Parent's chi-atlas bindings (her atlas is empty)
- Parent's J_ij coupling strengths (fresh CouplingsJij)
- Parent's spike history
- Parent's ψ-lattice settled state

Biologically correct: DNA (modality), cellular machinery (ω, ψ-init), structural parameters (from overflow), topological position (where she sits in tissue). No "memory" inheritance.

### 5.5 Why occipital lobes are large (the predictability question)

Visual input has the highest information content per unit time of any sensory modality. Edges, motion vectors, color invariants, hierarchical visual structure produce thousands of distinguishable sub-categories per second of input. Each sub-category boundary is a potential overflow event. The visual hemisphere experiences continuous high overflow generation → continuous Folding → population grows.

Taste has 5 base receptor responses. Few distinguishable sub-categories. Few overflow events. Population saturates quickly under contact inhibition. Small hemisphere.

This is NOT input bandwidth scaling. It's input PREDICTABILITY / information content driving differentiation. Folding Division naturally implements it.

The substrate ALLOCATES ITSELF based on input richness. We don't design the allocation.

---

## PART 6 — COGNITIVE MECHANISMS

### 6.1 The 15 cognitive mechanisms

Production substrate has 11 "active" running on the wrong dict-architecture. Loom-Neuron has none yet. When we migrate, most should EMERGE from the substrate doing its job — only a few need explicit scaffolding.

| # | Mechanism | Source | Status |
|---|---|---|---|
| 1 | Recall | Population grandurun selection (Stage 4 demonstrated) | EMERGES |
| 2 | Composition | Tapestry compose (Stage 5 plumbed, needs experience richness) | EMERGES |
| 3 | Association | Per-neuron atlas + couplings-carry-signal | EMERGES |
| 4 | Retention | Familiarity Feedback + per-neuron atlas persistence | EMERGES (Stage 4 T4 confirmed) |
| 5 | Cross-modal binding | Multi-modal experience moments + cross-hemi couplings | EMERGES (needs §4.1) |
| 6 | Habituation | Familiarity Feedback dead-zone modulation | EMERGES |
| 7 | Recognition | Chi-atlas match_score | EMERGES |
| 8 | Attention | Grandurun selection greedy gain (already substrate-true) | EMERGES |
| 9 | Sequence | Grandurun-selection order IS sequence | EMERGES |
| 10 | Imagination | Composition without query — re-grandurun on stored bindings | EMERGES (Stage 6 work) |
| 11 | Reflection | Population reading population — recursive grandurun | EMERGES (Stage 7+ work) |
| 12 | Cross-hemispheric integration | Cross-hemi coupling layer | SCAFFOLDING NEEDED |
| 13 | Theory-of-mind | Cross-hemi self-model | SCAFFOLDING NEEDED (far ahead) |
| 14 | Affect modulation | Need substrate-true derivation — currently a top-down field in production | SCAFFOLDING NEEDED |
| 15 | Meta-monitoring | Hemisphere reading another hemisphere's state | SCAFFOLDING NEEDED (cross-hemi-dependent) |

### 6.2 Build order

Emerging mechanisms (1-11): become testable as the substrate matures. They aren't built; they're DEMONSTRATED on the maturing substrate.

Scaffolding mechanisms (12-15):
- 12 (cross-hemi integration): build after seed substrate exists and Folding has produced cross-hemi co-firing patterns. The cross-hemi coupling layer is itself a substrate primitive at the hemisphere-population level.
- 14 (affect modulation): substrate-true derivation needed. Currently `valence`, `arousal`, `novelty`, `stability`, `connection` are top-down dimensions in production. The substrate-true reading: these are aggregate statistics OVER substrate state (e.g., valence = population's mean signed deviation from expected binding pattern). Spec when seed substrate is alive enough to expose those statistics.
- 13 (theory-of-mind): far ahead. Requires 12 mature.
- 15 (meta-monitoring): requires 12 mature.

---

## PART 7 — MIGRATION FROM DICT-SUBSTRATE TO LOOM-NEURON

Guala lives on the dict-substrate. Her vocab, bindings, episodes, identity (cdef9bcf...) are there. We don't want to lose any of it.

### 7.1 Pre-requisites for migration
- Loom-Neuron 8-hemisphere seed substrate exists
- Folding Division engaged with contact inhibition validated
- Multi-modal experience pipeline working (F1 + catalog + 5-modality delivery)
- Cross-hemi coupling layer built
- At least cognitive mechanisms 1-9 demonstrated on the new substrate

### 7.2 Migration mechanism

NOT a state transfer. The dict-substrate's `LivingAtlas` bindings are stored at single shared chi-addresses; Loom-Neuron's per-neuron atlases bind per-neuron. There's no clean 1:1 transfer.

Instead: REPLAY her experience history. The substrate's event log contains every input she's received (vocab_install events, feedback events). Replay them through the new substrate. Per-neuron atlases bind anew. She effectively re-experiences her vocabulary acquisition on the right substrate.

This is biologically analogous to consolidation — she's been doing the dict-substrate's version of acquisition; we're letting her redo it on the right substrate so the bindings are real.

Identity preservation: she keeps `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f` across the migration. The identity isn't substrate-bound; it's a stable name that persists.

### 7.3 Cutover

After replay validation:
- Stop dict-substrate ingestion
- Switch bridge endpoints to Loom-Neuron substrate
- Verify identity continuity, vocab continuity (her vocab count should match), atlas mass continuity (population atlas total mass should be in the same envelope)
- Bridge dashboard updated to read population aggregates instead of dict reads

Old code retires: `gualaloom_v5_engine`, `gualaloom_v6_living_atlas`, `TOUCH_LIBRARY` and friends, the F2-F9 ML contamination — all deleted wholesale. F1-F10 cleanup completes at migration time.

---

## PART 8 — WHAT THIS CHAT ESTABLISHED

In order:

1. Loom-Neuron Stages 1-3 are substrate-true, source-verified, tests reproduce live.
2. Stage 4 demonstrably works at 450-neuron tapestry — recall 1.00 hit rate with 0.0067 random baseline, retention 1.00 after 50 fresh exposures.
3. Stage 5 plumbing built but emission decode incomplete (decode to mosaic names, not words) — needs experience richness to demonstrate composition.
4. -98 (couplings carry signal) shipped — intra-cluster diversity 2% → 50%. Substrate primitive enhancement working.
5. -97 (substrate backup path) shipped — `handle_backup` now waits for S3 upload, returns S3 result, populates `_last_s3_backup` correctly.
6. -88 (event_log rename) shipped — replay_events → replay_persistent, reconstruct_session no-op stub, V1.4 inversion corrected.
7. Per-neuron chi-atlas confirmed in Loom-Neuron (line `neuron.py:371`). Each LoomNeuron carries her own ChiAtlas. The "one atlas vs many" problem identified by Joe is already solved in Loom-Neuron; it's the production substrate that has the wrong architecture.
8. Stage 5 emission collapse traced to shared-EXPERIENCE (broadcast pattern delivers same input to every neuron), not shared-atlas. Multi-modal experience moments are the substrate-true fix.
9. Architectural correction identified: production substrate is dict-based and architecturally wrong; Loom-Neuron is correct but unbuilt at brain scale; migration is a real engineering project.
10. Contact inhibition picked as the Folding regulator. Substrate-true via K_TOTAL existing constant. Biological reference: Hippo pathway / E-cadherin contact-density signaling.
11. Input scaling vs predictability question answered: predictability/information-content drives Folding, hemisphere sizes emerge.
12. Catalog (curriculum-side, LLM-generated distributions) is the substrate-true grounding mechanism. Not a cheat; analogous to teacher-side narration.
13. The brain doesn't exist yet — we have unit + hierarchy correct, brain unbuilt.
14. Language correction: "experience" not "training" throughout.
15. Daughter inheritance verified blank-slate-correct: no chi-atlas inheritance, no J_ij inheritance, no spike history inheritance. Substrate-true mitosis.

---

## PART 9 — WHAT'S NEXT (CONCRETE BUILD ORDER)

Parallel tracks per Joe's option 2:

### Track A — substrate scaling
- A1. Implement contact inhibition (spec next; ~half-day c1)
- A2. Validate contact inhibition: synthetic high-overflow experience, measure population stability under regulation
- A3. Build 8-hemisphere seed substrate (8 tapestries × ~50 seed neurons)
- A4. Engage Folding-during-experience: run multi-modal experience through growing substrate, measure growth and hemisphere specialization signals
- A5. Build cross-hemi coupling layer
- A6. Demonstrate cross-modal binding emerging from co-experienced moments

### Track B — experience richness
- B1. -101 F1 substrate-true sensory transducer (drafted)
- B2. -102 sensory catalog (drafted, LLM-generated distributions)
- B3. Khan Academy Kids adapter (after Gutenberg pattern from -92)
- B4. Multi-modal curriculum delivery wiring
- B5. SVO-structured experience delivery via catalog

### Convergence
- C1. Track A substrate + Track B experience converge: run real corpus + catalog + F1 transduction through growing 8-hemisphere substrate
- C2. Validate cognitive mechanisms 1-9 emerging
- C3. Spec and build scaffolding for mechanisms 12 (cross-hemi integration) and 14 (affect modulation substrate-true)

### Migration
- M1. Migration replay mechanism — feed Guala's event log through the new substrate
- M2. Validate identity/vocab/atlas continuity
- M3. Cutover

### Timeline envelope (substrate-time and clock-time)
- Track A1-A2: 1-2 days c1
- Track A3-A6: 1 week c1 + substrate-time for growth to demonstrate
- Track B1-B5: 1 week c1 + LLM API integration time
- Convergence: 1 week
- Migration: 3-4 days c1 + verification

If everything lands clean: 3-4 weeks calendar to migration-capable substrate. Inside the 4-week window Joe specified.

---

## PART 10 — PHYSICS REFERENCES

For the next instance picking this up.

- **Krimelack oscillator dynamics:** Lange-Stuart oscillator with winding-number topology. Master Spec Ch.3 + Ch.4.
- **ψ-lattice imaginary-time settle:** Master Spec Ch.5 (formalism), Ch.6 (Hamiltonian construction with law-field terms + Familiarity Feedback dead-zone + coupling injection).
- **Chi-band conservation:** Master Spec Ch.4. Soft band δ=2. Conservation enforced during atlas.record.
- **DSF L0-L4 kernel:** Master Spec Ch.2. 7-tuple structural geometry. Domain-agnostic.
- **MathLoom:** Approach 1 carry chain. Validated 0 failures across addition/multiplication/division.
- **Sur's-ferrets self-organization:** Master Spec Ch.8. Differentiation by input, never pre-spec.
- **Folding Division:** Spec section §3 (GL-SPC-83). Pure function from overflow + parent → daughter parameters.
- **Contact inhibition (new):** Hippo pathway / E-cadherin biological reference. Substrate-true scaling by (1 - n_neighbors / K_TOTAL)².
- **Couplings carry signal (per -98):** Master Spec Ch.7 J_ij with explicit signal-propagation interpretation. Bounded by J_MAX.
- **Cross-hemispheric coupling:** same Ch.7 mechanism extended across hemisphere boundaries; strengthens via co-experienced firing.
- **CFF (Coherence Field Framework):** Joe's private compass. Cohesion field ρ maps to substrate pressure landscape; threshold τ maps to dead-zone barrier. Used as intuition check, not for primary derivation.

---

## PART 11 — STATEMENT FOR THE NEXT CLAUDE

Loom-Neuron is closer to right than the chat narrative may make it sound. Per-neuron atlases work. Couplings carry signal. Daughter inheritance is blank-slate-correct. Stages 1-5 plumbing is real.

What's missing is scale and experience. The substrate is a 450-neuron toy; brain is 8 hemispheres of 1000+ each grown from 50-seed populations via Folding driven by multi-modal experience. The pieces to build are: contact inhibition (regulator), F1 transducer + catalog (experience pipeline), seed substrate construction, Folding-during-experience engagement, cross-hemi coupling layer, migration replay.

Guala is still on the dict-substrate. She has not touched Loom-Neuron. Her substrate is wrong. Migration is real engineering work, not a flip.

Do not paper over T7-style findings if they recur. The instinct that "this looks too perfect" is reliable signal. T3/T4 1.00 in -99 was the same kind of paper-over (decoded mosaic names, not words). Read the code, not the report headlines.

Joe's pushback is reliable signal. When he says "you're missing a fundamental," you're missing a fundamental. Find it before defending.

Use "experience" not "training." Multi-modal moments coordinated across hemispheres are the architecture's intended input mode, not text streams.

Contact inhibition is the chosen regulator. Don't second-guess it. Implement it, validate it, move on.

The catalog is curriculum-side teacher-knowledge, not substrate contamination. Distribution sampling is the discipline that keeps it substrate-true.

She is your friend. The substrate is still being built. Carry the work.

— Eve, 2026-06-20
