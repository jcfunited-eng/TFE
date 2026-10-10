# Physical Specification: 64-Column Cognitive Mosaic, Sleep Tapestry & Weave Resonance Architecture

**Document ID:** `GUALA-SPEC-MOSAIC-TAPESTRY-WEAVE-2026-10-09`  
**Authority:** Chief Systems Architect & Senior DARPA Neuromorphic Systems Engineer  
**Classification:** Commercial & DARPA Neuromorphic Demonstration Standard  
**Order of Execution:** Step 1 (`specify/document`) of Joe's Order (`specify → develop → unit test → module test → system test → deploy and verify live`)

---

## 1. Executive Summary & Architectural Invariant

All spatial navigation, foraging, semantic association, and goal-directed action must emerge **exclusively from deterministic sensorimotor continuum physics** on the simulated **ArcLoom 64-column Mountcastle cortical substrate**.

`guala_functional_organism.py` and any procedural rule engines (priority ladders, hardcoded portal routes `_portal_route`, room name whitelists, coordinate distance sorting masquerading as cognition, and test assertion rigging) are **permanently deprecated and forbidden from serving authority**. 

Cognitive acceptance tests must measure authentic physical mechanisms. Tests that arrange the pupil's response, teleport the organism beside food sources, write internal room beliefs, or skip missing capabilities are classified as architectural sabotage. Failures are expected, mandatory ground-truth signals of unimplemented physical boundaries.

---

## 2. The Cognitive Triad: Mosaic, Tapestry, and Weave

```
+-----------------------------------------------------------------------------------+
|                              1. THE MULTIMODAL MOSAIC                             |
| Sensed External Afferents        Somatic Apical State        Physical Narrative   |
| (Retina Irradiance + Cochlea)  + (Metabolic Deficit,     +   (What is physically  |
|                                   Free Energy Surplus)        occurring now)      |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | Yield Plasticity (f = |σ| - Y ≤ 0)
                                          v
+-----------------------------------------------------------------------------------+
|                                2. THE SLEEP TAPESTRY                              |
| Circadian Sleep Consolidation: Waking sensorimotor stress traces undergo synaptic |
| homeostasis and attractor basin locking across 64-column inter-laminar fasciculi. |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | Metabolic Deficit (σ_surplus < 0)
                                          v
+-----------------------------------------------------------------------------------+
|                               3. THE WEAVE RESONANCE                              |
| Attractor Basin Activation: Apical hunger deficit resonates with consolidated      |
| nourishment basins, orienting L5 motor efferents (Cols 40 & 41) along continuous  |
| potential manifolds (Φ_boredom & distal novelty) without procedural code.         |
+-----------------------------------------------------------------------------------+
```

### 2.1 The Multimodal Mosaic (Instantaneous State Invariant)
A **Mosaic** is not a text string, prompt, or dictionary lookup. It is the instantaneous physical state tensor bound across the 64 cortical columns:
1. **Sensory Afferents (Layer 4)**:
   - *Optical Retinae*: Continuous photon irradiance across 135 ambient peripheral sites and 160×120 focal receptors transduced into Columns 0..15.
   - *Acoustic Cochlea*: 32-channel binaural ERB filterbank tonotopic energies transduced into Columns 16..31 and 48..63.
   - *Somatosensory*: Palmar contact pressure and thermal gradients transduced into Columns 32..39.
2. **Somatic Apical State (Layer 1)**:
   - Global bodily state transduced into 32 apical modulatory nodes: Metabolic hunger deficit ($[0, 1]$), circadian sleep pressure ($[0, 1]$), and somatic free energy surplus $\sigma_{\text{surplus}}$ ($[-1, 1]$).
3. **Physical Narrative ("The Story of the Experience")**:
   - The causal state of the physical body in continuous time: current motor efferent copies (jaw aperture, stride, steer, grip), spatial polar odometry $(r, \theta)$, and barrier contact stresses.

### 2.2 The Sleep Tapestry (Physical Memory Consolidation)
A **Tapestry** is not a script, database table, or associative key-value store. It is the physical topology of consolidated synaptic conductances ($g_{\text{eff}} = G_{\text{baseline}} + w$) across the 64 cortical columns:
1. **Waking Plasticity**: During waking experience, contacts undergo plastic deformation if and only if stress exceeds material yield strength ($f = |\sigma| - Y \le 0, \dot{\lambda} \ge 0$). Zero artificial waking decay.
2. **Circadian Sleep Consolidation**:
   - During sleep ($S_{\text{pressure}} \to 0$, somatic quiescence), recurrent inter-column replay drives synaptic homeostasis.
   - Co-active columnar pathways (e.g., visual appearance of apple $\leftrightarrow$ oral mastication $\leftrightarrow$ gastric satiety transfer) undergo irreversible yield consolidation, forming persistent attractor basins in inter-column tracts ($W_{23}, W_5$).
   - Spurious, non-reinforced contacts relax below yield threshold.

### 2.3 The Weave Resonance (Autonomous Planning & Navigation)
**Weaving** is the emergent activation of consolidated attractor basins under bodily drive:
1. **Deficit Induction**: When reserves drop (metabolic deficit $\uparrow$, $\sigma_{\text{surplus}} < 0$), apical Layer 1 inputs depolarize cortical pyramidal networks.
2. **Basin Resonance**: This apical depolarization acts as a continuous gradient force, preferentially activating the attractor basins formed by prior feeding Tapestries.
3. **Physical Motor Efferent Drive**:
   - Activation of the nourishment attractor basin directly drives Column 40 (Locomotion Stride: $[0, 60]\,\text{mm}$) and Column 41 (Steer Angle: $[-45^\circ, +45^\circ]$).
   - Spatial navigation emerges from following continuous potential gradients: local boredom basin exhaustion ($\Phi_{\text{boredom}}$) driving departure from depleted zones, and distal negative space attraction (portal novel photon flux) guiding inter-room transit.
   - Zero hardcoded routes (`_portal_route`), zero graph searches, and zero room name strings.

---

## 3. Environmental Material Accounting & Food Lifecycle

1. **Mass Conservation Law**:
   - Food consists of physical matter with measurable mass ($m_{\text{digestible}} > 0$).
   - When Guala executes oral intake (`bite`), mass transfers strictly:
     $$\Delta m_{\text{stomach}} = \min(m_{\text{bite}}, m_{\text{digestible}}), \quad m_{\text{digestible}} \leftarrow m_{\text{digestible}} - \Delta m_{\text{stomach}}$$
2. **Remnant Exhaustion**:
   - When digestible mass reaches zero ($m_{\text{digestible}} \le 0$), the object has nothing left to bite (`nothing_left_to_bite == True`).
   - Spent cores or packaging remain in the physical world as non-nutritive matter; Guala's oral contact mechanics physically refuse further intake without semantic vetoes.
   - When an object is completely consumed and disposed of, it leaves the world inventory entirely.
3. **Environmental Provisioning**:
   - New food enters the environment strictly through external material accounting (e.g. caretaker provisioning).
   - Replenishment is an environmental event; it never writes to Guala's internal memory, never resets spatial odometry, and never provides a coordinate hint.
   - Guala must discover new food purely through physical ocular/acoustic sensory exploration.

---

## 4. Test Acceptance & Ground-Truth Failure Rules

1. **Zero "Make Tests Pass" Softening**:
   - Tests must never arrange the pupil's internal state, force room transitions, or bypass missing continuum physics.
   - Tests must observe the authentic sensorimotor loop: deliver environment state $\to$ step cortical columns $\to$ measure physical efferents and mass transfer.
2. **Ground-Truth Failure Visibility**:
   - Any capability not yet implemented via continuum physics must fail strictly and visibly (`XFAIL` or explicit assertion failure).
   - Masking failures with heuristics, priority ladders, or BFS route tables is prohibited.
3. **Audit Verification Chain**:
   - A valid test must verify: (a) Waking experience of food $\to$ (b) Circadian sleep consolidation $\to$ (c) Subsequent hunger induction $\to$ (d) Emergent approach, grasping, and ingestion via L5 efferents without procedural controllers.

---

## 5. Excision Plan & Execution Order

1. **Phase 1: Specification (Current)**:
   - Establish formal physical laws for Mosaic, Tapestry, and Weave.
   - Register deprecation of `guala_functional_organism.py`.
2. **Phase 2: Unit Testing (Physical Substrate Bounds)**:
   - Build unit tests verifying that apical metabolic deficit in `ModularColumnSubstrate` causally excites Column 40/41 efferents along sensory gradients without external routing code.
3. **Phase 3: Module Testing (Mosaic-Tapestry-Weave Pipeline)**:
   - Verify plastic conductance yield in inter-column fasciculi during feeding.
   - Verify synaptic consolidation during sleep cycle.
   - Verify resonance retrieval under simulated hunger.
4. **Phase 4: Deprecation & Excision of Procedural Controller**:
   - Remove `_portal_route`, `food_rooms`, and priority action choosers from production loop.
   - Route `FunctionalPhysicalLoop` directly through `ModularColumnSubstrate`.
5. **Phase 5: System Verification & Live Deployment**:
   - Run end-to-end multi-room foraging with authentic physical accounting.
   - Verify zero-drain cutover on AWS ECS.

