# Cognitive Assets Specification: Developmental Sensory-Motor & Grounding Architecture

**Date**: 2026-09-19 (Updated)  
**Status**: Canonical Specification & Roadmap  
**Architectural Authority**: Translation of Physical Analogies & Sensory Modalities into Deterministic Cognitive Assets  

---

## 1. Executive Summary

This specification formalizes the core cognitive assets and sensory transducers required for the embodied Artificial Entity (Guala) to progress across the developmental continuum—from sensorimotor babbling to grounded language, tool manipulation, and text comprehension—without statistical machine learning or heuristic approximations:

1. **Cognitive Asset 1: Valence-Weighted Episodic Binding & Anticipatory Trajectory Reactivation**  
   *(Derivation: The Pool Shock Principle)*  
   Translates raw multi-channel sensory timeseries into bound 4D episodic trajectories consolidated proportionally to somatic gradients ($\Delta\text{Reserve}$, physical boundaries, distress/shock), reactivating stored outcomes *before* executing candidate motor commands.

2. **Cognitive Asset 2: Multi-Step Predictive Affordance Planning for Need Fulfillment**  
   *(Derivation: The Refrigerator Climbing Principle)*  
   Resolves somatic need fulfillment when direct 1-step motor acts are physically obstructed ($D_{\text{target}} > \text{Reach}_{\max}$), executing inverse causal chaining across intermediate environmental affordances (move tool $\to$ position intermediary $\to$ elevate/navigate $\to$ grasp target $\to$ quench somatic deficit).

3. **Cognitive Asset 3: Auditory-Motor Reafference & Spectral Babbling Resonance** *(Implemented & Verified 2026-09-18)*  
   *(Derivation: The Kuhl Native-Vowel Magnet Principle)*  
   Continuous acoustic-motor mapping via 32-channel basilar membrane spectral cosine similarity ($\rho \ge 0.65$), purging static vowel tables in favor of dynamic acoustic resonance between hearing and vocal tract actuation.

4. **Cognitive Asset 4: Spatial Object Permanence & Occlusion Conservation**  
   *(Derivation: The Piaget Invariant)*  
   Maintains mass and spatial coordinate invariance for objects temporarily occluded or out of immediate retinal line of sight, preventing catastrophic forgetting of environmental resources.

5. **Cognitive Asset 5: Combinatorial Syntactic Chaining & Demand Phrasing**  
   *(Derivation: The Two-Word Invariant Transition)*  
   Chains grounded syllables into 2–3 token combinatorial demands to resolve internal homeostatic deficits through caregiver interaction (e.g., "want apple", "see bear").

6. **Cognitive Asset 6: Symbolic Orthographic-to-Phonetic Sensory Cortex (Text-to-Sensorimotor Grounding Transducer)**  
   *(Derivation: Exogenous Perceptual Transduction for Written Media & Curriculum Ingestion)*  
   Decodes written symbolic typography (books, lesson cards, educational text) and translates nouns and adjectives into continuous physical sensory vectors (sight, sound, taste, touch, smell) that the DSF substrate can ingest through its native photoreceptor and cochlear sensory channels, without overriding or replacing internal deterministic cognition.

---

## 2. Cognitive Asset 1: Valence-Weighted Episodic Binding & Trajectory Reactivation

### 2.1 Physical Derivation (The Pool Shock Principle)
An environmental event is etched into long-term phase space if and only if it produces an acute change in the organism's internal somatic integrity ($\Gamma_{\text{salience}}$). The physical variables present during the transition are bound into a unified 4D coordinate manifold.

### 2.2 Mathematical Formalization
$$\Gamma_{\text{salience}}(t) = \kappa_1 \left| \frac{d R_{\text{reserve}}}{dt} \right| + \kappa_2 \Omega_{\text{shock}}(t) + \kappa_3 B_{\text{boundary}}(t) + \kappa_4 \left| \frac{d P_{\text{sleep}}}{dt} \right|$$
- If $\Gamma_{\text{salience}}(t) \ge \Gamma_{\text{threshold}}$, an **Episodic Frame** $\mathcal{E} = \langle \mathbf{X}_{\text{pose}}, \mathbf{V}_{\text{visual}}, \mathbf{A}_{\text{auditory}}, \mathbf{T}_{\text{tactile}}, \mathbf{S}_{\text{somatic}}, \mathbf{M}_{\text{action\_consequence}} \rangle$ is crystallized.
- Stored trajectories are queried prior to actuation; if anticipated somatic delta is negative, candidate actions are inhibited.

---

## 3. Cognitive Asset 2: Multi-Step Predictive Affordance Planning

### 3.1 Physical Derivation (The Refrigerator Climbing Principle)
Intelligent need fulfillment requires inverse affordance chaining when direct reach is obstructed:
1. Target Terminal State: food in hand $\implies$ consumption $\implies$ reserve deficit quenched.
2. Obstacle: $\Delta z > \text{Reach}_{z,\max}$.
3. Causal Graph Search: $\text{MoveTo}(O_{\text{tool}}) \to \text{Translate}(O_{\text{tool}}, X_{\text{target}}) \to \text{StepOnto}(O_{\text{tool}}) \to \text{Grasp}(O_{\text{target}})$.

---

## 4. Cognitive Asset 3: Auditory-Motor Reafference & Spectral Babbling Resonance
*(Status: Production Complete & Verified 2026-09-18)*

- Computes continuous 32-channel basilar membrane spectral cosine similarity $\rho(\mathbf{S}_{\text{heard}}, \mathbf{S}_{\text{vocal}})$.
- Drives autonomous babbling convergence without heuristic lookup tables or discrete vowel classes.

---

## 5. Cognitive Asset 4: Spatial Object Permanence & Occlusion Conservation
*(Status: Scheduled for Milestone Checkpoint)*

- Conserves physical mass coordinates when line-of-sight is broken ($V_{\text{retina}} = 0$, $M_{\text{conserved}} > 0$).
- Eliminates sensorimotor erasure of environmental objects when the agent turns its head or navigates past furniture.

---

## 6. Cognitive Asset 5: Combinatorial Syntactic Chaining & Demand Phrasing
*(Status: Scheduled for Milestone 3)*

- Couples successor links in the meaning topology into sequential phonetic chains.
- Transitions the organism from isolated single-syllable emissions into multi-word intentional demands directed at environmental caregivers.

---

## 7. Cognitive Asset 6: Symbolic Orthographic-to-Phonetic Sensory Cortex
*(Status: Specified & Added to Development Roadmap 2026-09-19)*

### 7.1 The Perceptual Ingestion Problem
The DSF kernel and embodied sensorimotor loop do not operate on raw ASCII/Unicode byte strings. The organism perceives the universe strictly through physical field channels:
- Retinal luminance patterns (photoreceptors)
- Cochlear acoustic pressure waves (basilar membrane)
- Somatosensory contact (skin temperature, texture, resistance)
- Chemical receptors (gustatory and olfactory fields)

To enable the organism to ingest written books, educational texts, and structured curricula (e.g. Khan Academy resources), external text must be transformed into continuous physical sensory fields.

### 7.2 The Exogenous Sensory Transducer Architecture
```
+-------------------------------------------------------------------------+
|                       WRITTEN SYMBOLIC TEXT                             |
|               (Books, Curriculum, Khan Academy Lessons)                 |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  COGNITIVE ASSET 6: SENSORY TRANSDUCER                  |
|                (Orthographic-to-Physical Field Converter)               |
|                                                                         |
|  * Orthography -> Optical Glyph Geometry (Retinal Stimulus)             |
|  * Orthography -> Acoustic Phonetic Formants (Cochlear Stimulus)         |
|  * Semantic Nouns/Adjectives -> Physical Invariant Affordance Vectors:   |
|      - Visual Geometry & Color                                          |
|      - Acoustic Spectral Profile                                        |
|      - Tactile Texture & Thermal Resistance                             |
|      - Chemical Gustatory & Olfactory Valence                           |
+-------------------------------------------------------------------------+
                                    |
                                    v  (Continuous Physical Field Stream)
+-------------------------------------------------------------------------+
|                 GUALA EMBODIED SENSORY-MOTOR NERVOUS SYSTEM             |
|                                                                         |
|   Retina (903 sites) <---+   Cochlea (32 ch) <---+   Skin/Somatic Receptors|
|                                                                         |
|         NO ML / NO HEURISTICS IN THE COGNITIVE CORE                     |
|         DSF Kernel ($D_k, M_k, R_{rev,k}, U^*_k, C_k, P_k, B_k$)         |
|         Deterministic Basin Dynamics & Sleep Consolidation              |
+-------------------------------------------------------------------------+
```

### 7.3 Architectural Non-Negotiables for Asset 6
1. **Strict Sensory Containment**: The transducer functions strictly as an **environmental sensory interface** (analogous to the cornea, cochlea, or olfactory epithelium). It does **not** make cognitive decisions, dictate motor policies, or shortcut Guala's internal basin dynamics.
2. **Deterministic Sensory Invariants**: Text describing physical objects (e.g. "rough wooden table", "warm sweet apple") is transduced into invariant physical coordinates matching the home world physics, allowing associative grounding to occur naturally across modalities.
3. **Zero Cognitive Contamination**: The internal DSF cognition remains 100% deterministic and sovereign.

---

## 8. Development & Integration Sequence

| Asset | Designation | Engineering Target | Status |
| :--- | :--- | :--- | :--- |
| **Asset 3** | Auditory-Motor Spectral Resonance | Continuous 32-ch basilar cosine similarity ($\rho \ge 0.65$) | **COMPLETE (2026-09-18)** |
| **Asset 1** | Valence-Weighted Episodic Binding | $\Gamma_{\text{salience}}$ consolidation + pre-actuation inhibition | **SPECIFIED** |
| **Asset 2** | Multi-Step Affordance Planning | Inverse causal affordance graph search for obstructed targets | **SPECIFIED** |
| **Asset 4** | Spatial Object Permanence | Occlusion mass conservation in 3D coordinate space | **SCHEDULED (Milestone 2)** |
| **Asset 5** | Combinatorial Syntactic Chaining | Multi-syllable demand phrasing & turn-taking | **SCHEDULED (Milestone 3)** |
| **Asset 6** | Symbolic Orthographic Cortex | Text-to-sensorimotor transducer (books & educational input) | **SPECIFIED ON ROADMAP** |
