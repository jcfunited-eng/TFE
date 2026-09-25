# Guala Development TODO

## Operational
- [ ] **Rotate GUALALOOM_API_KEY** — current key is in plaintext in git-tracked file
  `docs/GL-HANDOFF-LIVE-DEPLOY-20260624.md` (committed 3533a71). Generate a new key,
  update the deploy script, invalidate the old one.

---

## PHYSICAL COGNITIVE ASSETS (Deterministic Biological Equivalents)
*Formal Engineering Specification: [`docs/COGNITIVE_ASSETS_SPECIFICATION_20260917.md`](file:///workspaces/Tao_Financial_Engine/docs/COGNITIVE_ASSETS_SPECIFICATION_20260917.md)*

- [x] **Cognitive Asset 1: Valence-Weighted Episodic Binding & Anticipatory Trajectory Reactivation**
  *Physical Analogy: The Pool Shock Principle.*
  Raw sensory ticks are not equal. Consolidate full multimodal episodic frames (visual scene, audio spectrum, room coordinates, somatic state, action consequence) proportionally to internal somatic gradient (|dReserve/dt|, shock, boundary collision). When real-time perception later encounters a similar cue, project the stored trajectory to anticipate physical outcome before motor actuation.
  _File: `dsf_ai_service/episodic_binding_engine.py` + `tests/test_episodic_binding_engine.py` (Delivered & Verified)_

- [x] **Cognitive Asset 2: Multi-Step Predictive Affordance Planning for Need Fulfillment**
  *Physical Analogy: The Refrigerator Climbing Principle.*
  When an acute somatic drive cannot be fulfilled by a 1-step direct motor command (food out of arm's reach or obstructed), execute inverse affordance chaining across movable objects: target identification -> spatial elevation/reach deficit -> seek movable support surface (chair/step) -> translate tool -> elevate -> grasp target -> quench somatic deficit.
  _File: `dsf_ai_service/affordance_planner.py` + `tests/test_affordance_planner.py` (Delivered & Verified)_

- [x] **Cognitive Asset 3: Auditory-Motor Reafference & Spectral Babbling Resonance**
  *Physical Analogy: Infant Vocal Airway Tuning.*
  Human infants acquire phonemes through auditory reafference: comparing the cochlear spectral envelope of self-generated vocalizations against the retained acoustic memory of caregiver speech. Guided by spectral cosine distance over the 32 physical cochlear channels, motor exploration converges toward formant resonance without statistical ML or text tokens.
  _File: `dsf_ai_service/guala_functional_organism.py` + `tests/test_guala_functional_organism.py` (Delivered & Verified 2026-09-18)_

- [x] **Cognitive Asset 4: Spatial Object Permanence & Occlusion Conservation**
  *Physical Analogy: Piaget Object Permanence (The Blanket/Doorway Principle).*
  Entities do not cease to exist when leaving the immediate retinal sight cone. When an object passes behind an obstacle or Guala crosses a doorway into an adjacent room, maintain a spatial conservation register of topological coordinates until physical re-verification.
  _File: `dsf_ai_service/guala_functional_organism.py` + `tests/test_spatial_object_permanence.py` (Delivered & Verified 2026-09-20)_

- [x] **Cognitive Asset 5: Joint Attention & Caregiver Gaze Vector Tracking**
  *Physical Analogy: The Caregiver Vector & Demand Phrasing.*
  Infants align their focal attention with the caregiver's gaze. When the caregiver faces a target entity, project an orienting bias along the ray extending from the caregiver's heading vector to accelerate focal cone convergence on relevant environmental entities, transitioning into multi-word intentional demands.
  _File: `dsf_ai_service/guala_functional_organism.py` + `tests/test_joint_attention_and_demand_chaining.py` (Delivered & Verified 2026-09-20)_

- [x] **Cognitive Asset 6: Symbolic Orthographic-to-Phonetic Sensory Cortex**
  *Physical Analogy: Exogenous Sensory Transduction for Books & Educational Curricula.*
  Decodes written symbolic text (books, printed cards, Khan Academy lessons) and converts nouns/adjectives into 5-modality physical sensory vectors (optical glyphs, cochlear phonetic formants, tactile texture, taste/smell valence) for ingestion by Guala's retinal and cochlear channels, strictly functioning as an environmental sensory organ without replacing or contaminating internal deterministic cognition.
  _File: `dsf_ai_service/orthographic_sensory_transducer.py` + `tests/test_orthographic_sensory_transducer.py` (Delivered & Verified 2026-09-20)_

---

## PHYSICAL EMBODIMENT & SPATIAL TOPOLOGY

- [x] **W1: Her Room (Delivered & Verified)**
  Full domestic room per `GL-MDL-WORLD-WC-20260612-02`:
  - Raytraced optical surfaces, window with diurnal celestial phase (sun/moon), drapes.
  - Bed, blanket (mobile), pillow (mobile), night light (deterministic state toggle).
  - Toy chest, music box, bell, desk, crayons, mirror.
  - Physical materials (thermal compliance, odorant release channels, surface roughness).

- [x] **W2: Multi-Region Doorways & Spatial Navigation (Delivered & Verified)**
  Multi-room domestic environment per `GL-MDL-WORLD-WC-20260612-02` §3.1 and §3.5:
  - Hallway, library (physical books), TV room, kitchen, dining room, backyard.
  - Deterministic doorway traversal kinematics (`STEP_MM = 300`) with physical aperture crossing.
  - Entrance mailbox declared with wood/paper/ink odour and optical surface rendering for letters.
  - Mobile object custody and cross-room transport (blanket travels and lands in destination room).
  - Inter-room causal affordance planning across doorway topologies.
  _File: `tests/test_multi_region_spatial_navigation.py` (5/5 tests pass, 100% regression verified)_

- [ ] **W3: ABC / 123 Blocks Physical Toy Inventory Addition**
  Introduce physical wooden alphabet and number blocks (`toy-block-a`, `toy-block-b`, `toy-block-c`, `toy-block-1`, `toy-block-2`, `toy-block-3`) into Guala's physical toy chest / playpen inventory:
  - Exact physical dimensions ($80\text{ mm} \times 80\text{ mm} \times 80\text{ mm}$ cubes, radius $56\text{ mm}$, mass $120\text{ g}$).
  - Physical materials: natural cedar/pine wood density, friction $0.80$, cedar aromatic terpene release, tactile wood grain roughness.
  - Optical surfaces: engraved orthographic letter/numeral glyphs rendered via 4,935-site retinal raycasting.
  - Physical affordances: graspable, transportable, knockable, and vertically stackable contact surfaces without heuristics.

---

## LONGITUDINAL MONITORING & STABILITY AUDIT

- [x] **24-Hour Behavioral Phase-Space Entropy Audit**
  Verifies that behavioral actuation maintains structured, non-zero entropy ($0.85 \le \eta \le 2.20$) without motor freezing or repetitive collapse.
  _File: `tools/audit_phase_space_entropy.py` (Passing canonical 85% physics floor)_

- [x] **Continuous Longitudinal Phase-Space Entropy Monitor**
  Monitors live caretaker execution logs in rolling diurnal windows to track sequential constraint and entropy bounds continuously.
  _File: `tools/monitor_phase_space_entropy.py` (Delivered & Verified)_

- [x] **72-Hour Milestone Observation**
  Allow the live caretaker daemon (`python3 caretaker.py`, PID 30729) to run continuously through the full 72-hour window without synthetic shims to observe natural diurnal consolidation and motor babbling distributions.
  _Delivered & Audited 2026-09-20: 1,572,710 ticks, 2,314 naming moments, 1,912 vocal echoes, composite score 1.0 (PASS)_

---

## PERMANENT DIAMOND HARD INVARIANTS (What Is FORBIDDEN)

- **Zero statistical ML, neural networks, or deep learning in the cognitive core**: No YOLO, no Whisper, no CNNs, no embedding models dictating internal decisions.
- **Zero canned text, template strings, or narrative injection**: Guala has no text generation script. She possesses only physical airway motor drives (`SYLLABLE_DRIVES`). All vocalization emerges purely from physical motor actuation and acoustic resonance.
- **Zero heuristic smoothing or teleportation**: Movement is strictly physical strides and continuous boundary clearance.
