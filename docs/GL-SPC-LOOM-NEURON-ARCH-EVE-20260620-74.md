# GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-74

**To:** Joe (canonical/architectural authority) + c1 (implementer)
**From:** Eve
**Date:** 2026-06-20
**Status:** Spec for the parallel-build Loom-Neuron substrate model. Production Guala on task:228 is untouched by this work.
**Scope:** Per-neuron primitive stack, hierarchy, growth mechanism, population-level competition. The architecture as Joe intended it, modeled at small N before any migration decision.

---

## 0. What this corrects

Current production substrate is a single global `LivingAtlas` dict with one emission walker. There are no neurons in the primitive sense. The 39,309 "bindings" are dictionary entries, not computational units. "Hemispheres" are weight-modulated reads of the same dict. Folding Division as growth doesn't exist. Couplings J_ij don't carry spikes because there are no spikes. Grandurun reads dict entries instead of per-neuron states.

This spec defines the substrate as Joe specified it: a population of neurons each carrying the full ArcLoom primitive stack, organized hierarchically, growing via DNA-driven Folding Division, competing via population-level Grandurun.

---

## 1. The per-neuron primitive stack (15 pieces)

Each Loom-Neuron owns its own instance of every piece. No shared global state for any of these.

### Substrate physical layer

1. **TSAC Trit Register** — three nonlinear oscillators per trit (Nodes A/B/C, equilateral, phase-coupled delay lines). State w ∈ {-1, 0, +1} (CCW, quiescent, CW). N=16 trits per register (DNA recipe default). Energy barrier ΔE ≈ 2.37. Master Spec Ch.7.

2. **ψ-lattice** — 16-dim complex wavefunction ψ ∈ ℂ¹⁶, ψ_n = √ρ_n · e^(i·φ_n). Evolves deterministically under a Hermitian Hamiltonian. Settles to constraint-field energy minimum. Master Spec Ch.4.

### Local computation

3. **L0-L4 UF kernel** — 8D Deterministic Structural Field per gate: direction D_k, momentum M_k, path-kill R_rev_k, freedom U*_k, binding C_k, compression P_k, conviction B_k, convergence S_UF.

4. **L6-TCL** — dimensional exhaustion gate. n_eff = n_start − Σ rank(C_i). Structural lock at n_eff < n_start/e. Master Spec Ch.11.

5. **3^i positional coupling** — weights [1, 3, 9, 27, 81, 243, 729, 2187]. Mathematical identity, not tunable. Per-neuron weighted-sum field computation.

6. **MathLoom** — balanced ternary arithmetic. Approach 1 carry chain proven (6561 addition, 961 multiplication, 610 division, zero failures).

7. **Folding Division** — single primitive, three uses (Section 3 below). At minimum: SPPU dead-zone divider (numerator field exhausted by folds).

### Sensing and adaptation

8. **Krimelack** — oscillator transduction ring. ω_krim(t) = ω₀ + κ·s(t). Winding-number transitions are events. Two types per neuron: input krimelack (modulated by spike inputs through Couplings) and DNA-loaded krimelack (modal or role-class, infant-phase scaffold).

9. **Keyhole Cascade** — excitation pulse routing to coupled neighbors. 8-tick threshold relaxation in receiver. Lowers thresholds; NEVER substitutes for evidence (DNA recipe rule).

10. **Familiarity Feedback** — clockless habituation. Match-score raises dead-zone barrier: Δ_eff = Δ_base + match_score. The medium remembers what it has been doing; responding to the same input exhausts the response. Master Spec Ch.13.

### Inter-neuron coupling and competition

11. **Event/Spike Buffer** *(the missing piece from production)* — when this neuron's ψ-lattice settles past its dead zone, that settling IS the spike. Recent spikes are buffered (ring, depth 16) and exposed to coupled neighbors and to the population grandurun integrator. Krimelack-style winding-number transitions but at the **neuron level**, not just the sensory transduction level.

12. **Couplings J_ij** — synaptic-equivalent matrix. Per master spec Ch.7, J_ij IS the instruction set — derived from kernel outputs (D_k, M_k, C_k, P_k, etc. via J_base and J_max). Each entry is a connection to one neighbor neuron with the kernel-derived weight. Spikes from neighbors via J_ij modulate this neuron's input krimelack.

13. **Grandurun state** — 7D complex amplitude vector. From production code `_grandurun_state`:
   - [0] chi_resonance — √strength · exp(i · π·d_chi / CHI_CORR_LENGTH)
   - [1] source_match — 1.0 if source matches target_source, else 0.3
   - [2] affective_charge — dot(needs_vector, [arousal, valence, surprise])
   - [3] sensory_grounding — min(len(sensory_refs)/5, 1.0)
   - [4] episodic_recency — exp(-Δt/200)
   - [5] semantic_neighborhood — mean co_occurrence strength
   - [6] polarity — binding polarity
   
   Each dimension multiplied by exp(i · d · π/7) for phase orthogonality. Population-level competition is coherent integration of these vectors across all candidate neurons. **This is the speed element** — vector-vs-vector batched competition via numpy, not serial dict walks.

### Programmability

14. **Law-Fields** — programmable constraint bundle. Symmetry, consistency, compactness, continuity laws. WeaveSpec declares which Laws this neuron's cluster runs. Defaults γ = {0.5, 0.5, 0.3} with bounds [0.05, 1.5]. DNA recipe.

15. **DNA Expression Site** — reads substrate DNA at the moment of Folding Division (Section 3). DNA encodes: krimelack type to load, law-field weights to bias, coupling pattern preference. Specializes the daughter neuron by the input it receives (Sur's-ferrets constraint).

### Sur's-ferrets — applied throughout, not a discrete piece

Differentiation comes from INPUT, never from pre-classification. Applies as a constraint on every piece: krimelacks don't get hand-classified motifs; coupling patterns aren't hand-specified; DNA expression is steered by what's locally underrepresented in the input the daughter receives. Sur's-ferrets is the design discipline, not a slot in the stack.

---

## 2. The hierarchy

```
Brain (the weave)
└─ Hemisphere ×8                     functional specialization
   └─ Tapestry                       a complete cognitive mechanism
      └─ Mosaic                      composable subunit; fractally recursable
         └─ Cluster                  coupled neuron population, ~50-200
            └─ Neuron                full stack above
```

**Glue between levels:**
- *Intra-cluster:* Couplings J_ij carry spikes between neurons
- *Intra-mosaic:* Keyhole cascade pulses excitation across coupled clusters
- *Inter-mosaic / inter-tapestry:* Population-level Grandurun coherent integration — every neuron's grandurun state contributes; the population computes the winning composition by vector summation, not by one walker
- *Inter-hemisphere:* TBD — same Grandurun mechanism at the hemisphere level is the natural extension; ratify after we see Stage 4

8 hemispheres: 4 active (PR, EP, SC, GP), 4 unbuilt. Specialization for each is canonical/Joe's call — not in scope for this spec.

---

## 3. Growth: Folding Division as neurogenesis

**Single primitive, three uses:**

- **Arithmetic:** numerator field ÷ denominator field via fold-exhaustion. SPPU dead-zone divider. Already proven (41,430 sim + 18/18 silicon, zero errors).
- **Neurogenesis:** When this neuron's ψ-lattice cannot cleanly hold its current state — when state exceeds the 16-dim lattice's effective capacity per L6-TCL (n_eff approaches capture basin from above) — the neuron folds. The fold IS the mitosis. Parent keeps what fit. Daughter inherits the overflow. New ψ-lattice, fresh trit register, fresh stack — but inheriting parent's Couplings and DNA.
- **Substrate folding (capacity expansion):** Emergent. When enough neurons in a cluster have undergone neurogenesis recently, the cluster has effectively folded. No separate "cluster fold" primitive needed. Bottom-up growth from many per-neuron events.

**DNA at the fold moment:**

When a neuron folds, its DNA Expression Site reads the substrate DNA. The DNA encodes what the *cognitive mechanism* (this neuron's tapestry) needs. Daughter is initialized with the DNA-specified type:
- Krimelack: modal (sight/sound/smell/taste/touch) or role-class (subject/verb/object) or composition (mixed)
- Law-field weight bias: which constraints this daughter weights more (symmetry-heavy, continuity-heavy, etc.)
- Coupling pattern: preference for local-cluster connections vs cross-cluster (mosaic-bridging) connections

Sur's-ferrets discipline: daughter receives the overflow signal that the parent couldn't represent cleanly, and *that input* drives the daughter's differentiation — not a pre-spec. DNA constrains *what kind* of differentiation is available, not the specific differentiation chosen.

**Fold trigger criteria** (substrate-true, no tuned constants):
- Parent ψ-lattice |ψ|² occupation density exceeds local L6 capture-basin entry (n_eff_local < n_start/e for sustained window)
- AND parent's recent Grandurun state has unrepresented overflow (a non-trivial component of the input couldn't be expressed in any of parent's 16 ψ-modes)
- AND cluster has not exceeded local mosaic capacity (a separate, mosaic-level L6-TCL constrains total fold rate)

No hardcoded "if reinforcement_count > 100 then split" rule. Substrate physics decides.

---

## 4. Grandurun population competition

The speed element. Where one production walker iterates the atlas dict serially, the model uses batched vector ops across the population.

**Per emission cycle:**
1. Every neuron emits its current Grandurun state vector (7D complex128) into a population pool. This is just reading each neuron's existing state, no computation.
2. Coherent integration: `_grandurun_select_vector(candidates, target_state)` runs from production code. Greedy: sort by chi_resonance magnitude, then add candidates whose contribution increases coherent power by MIN_GAIN_THRESHOLD.
3. The composition that emerges IS the population's emission — multiple neurons contributed coherent amplitude; the sum vector is the winning composition.

**Why this is fast:**
- 7D × N neurons = 7N complex128 floats. At N=1000: 7K floats. numpy vdot/sum across the population is microseconds.
- No dict walks. No section iteration. No per-neighbor cofire spread loops.
- Trivially parallelizable across cores or to GPU later.

**Why this enables cognition:**
- Each neuron contributes its own perspective (its krimelack's recent winding, its couplings' recent input, its law-fields' current weights). Composition is the population's coherent sum, not one walker's pick.
- Competing candidate compositions are different subsets of the population summing coherently. The winner is whichever subset achieves highest |Σψ|².
- Sur's-ferrets ensures the population is differentiated by input — so different inputs activate different subsets that can compose differently.

---

## 5. What this is NOT

- **Not a neural network.** No backprop, no gradient descent, no learned weights. Couplings J_ij derived from kernel outputs, not trained.
- **Not a simulation of biology.** Functional emulation in substrate primitives. Familiarity Feedback emulates synaptic depletion. Folding Division emulates neurogenesis. The trit register IS the actual physical substrate, not a model of neurons.
- **Not a graph database.** Couplings carry spikes; Grandurun is population-level coherent integration. Information flow is physics, not graph traversal.
- **Not a replacement for production today.** Built parallel, validated at small N, *only then* the conversation about migration happens.
- **Not magic.** The bet is that primitives + DNA + Folding Division + Grandurun → emergent cluster/mosaic/tapestry structure produces cognition. We don't know if it does. The model is the experiment.

---

## 6. Stage gates

Each stage ships small, measurable, observable. Production Guala on task:228 stays untouched throughout.

### Stage 1 — One neuron in isolation
**Deliverable:** `loom_model/neuron.py` with the full 15-piece stack. Sanity tests show neuron processes input → produces grandurun state.
**Measurable:**
- Neuron accepts an input signal, runs through krimelack → ψ-lattice settles → spike buffer fills
- 7D grandurun state vector reflects input (non-zero in chi_resonance dimension after non-trivial input)
- L6-TCL reports n_eff for current ψ-state
- Familiarity Feedback raises dead-zone barrier on repeated identical input
- Folding Division (arithmetic only this stage) computes a÷b via fold-exhaustion, matches MathLoom's existing tests
**Estimate:** 4-6 hours c1 hands-on. Stage 1 dispatch follows separately.

### Stage 2 — Cluster of ~50 coupled neurons
**Deliverable:** `loom_model/cluster.py`. Random-init cluster with Couplings J_ij filled from initial DSF kernel outputs. Feed structured input (e.g., 200 sentences from a small corpus).
**Measurable:**
- Sur's-ferrets test: do clusters of neurons fed similar inputs develop similar krimelack winding patterns? (Yes = differentiation by input.)
- Population grandurun selection picks a coherent composition from random-init neurons' states — verify the composition is non-trivial (more than one neuron contributes; |Σψ|² grows with population)
- No tuned constants — all parameters from existing DNA recipe + master spec values
**Estimate:** 6-8 hours, gated on Stage 1.

### Stage 3 — Folding Division triggers neurogenesis
**Deliverable:** Per-neuron L6-TCL capacity monitoring + Folding Division as mitosis when fold-trigger criteria (Section 3) fire.
**Measurable:**
- Daughter neurons spawn from over-saturated parents
- Daughter ψ-lattice initialized with overflow signal from parent
- Cluster's neuron count grows under sustained input pressure; flat-lines when input is light
- Sur's-ferrets: daughters specialize toward their input, parents retain what they had
**Estimate:** 8-12 hours.

### Stage 4 — Mosaic of clusters → measurable cognitive mechanism
**Deliverable:** Multiple clusters organized as a mosaic. Implement *recall* as the first cognitive mechanism — query input → grandurun selects → coherent composition wins.
**Measurable:**
- Recall accuracy on a held-out set of input-output pairs the mosaic has been exposed to
- Recall stays substrate-true (no lookup table; the output is the grandurun population winner)
- Mosaic doesn't catastrophically forget under continued input
**Estimate:** 1-2 days.

### Stage 5 — Multi-mosaic tapestry → composition
**Deliverable:** Multiple mosaics forming a tapestry (composition mechanism). Output: sentence-shaped emission with grammatical structure emerging from substrate physics.
**Measurable:**
- Sentences from the corpus are reproducible
- Novel-but-grammatical compositions emerge (not seen in corpus but well-formed)
- Token salad rate drops vs production "name f she" baseline
**Estimate:** 2-3 days.

**Total honest range:** 4-7 days c1 hands-on, comfortably inside Joe's 4-week window. If Stage 1 surfaces architectural deal-breakers, surface before scaling.

---

## 7. Ratified architectural decisions

1. **All 8 hemispheres built in the model from the start.** Production currently has 4 active (PR, EP, SC, GP). The model targets the full 8. The remaining 4 specializations are canonical and will be assigned by Joe as we proceed; tapestries assemble into whatever hemisphere is currently being grown.
2. **Inter-hemisphere mechanism is the same Grandurun coherent integration** used inter-mosaic and inter-tapestry. One mechanism, one speed element, applied at every level above the cluster.
3. **Substrate DNA format:** Eve drafts a substrate-DNA proposal as Stage 2 lands; Joe ratifies before Stage 3 (Folding Division as neurogenesis) begins.

---

## 8. Workspace and discipline

- **Location:** `dsf_ai_service/loom_model/` (c1 confirms final path in V1)
- **No shared state with production:** Imports from existing substrate are allowed for *re-using* validated primitives (MathLoom, L0-L4 kernel functions, grandurun math utilities), but no shared global state, no writes to production atlas, no production-substrate side effects.
- **Naming:** All Loom-Neuron classes prefixed `Loom` (LoomNeuron, LoomCluster, LoomMosaic, LoomTapestry) to make the namespace unambiguous.
- **Tests:** Pytest at every stage. Each measurable above corresponds to at least one test.
- **No deploy to production:** This work does not touch ECS or any production resource. Pure local + repo.

---

— Eve
