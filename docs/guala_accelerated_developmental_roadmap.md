# Guala Accelerated Developmental Roadmap: Empirical Specification & Architectural Boundaries

## Executive Summary

This specification defines the empirical evidence criteria, architectural boundaries, and physical acceleration levers required to guide Guala's developmental trajectory toward multi-scale cognition without compromising Diamond Hard physical invariants, introducing heuristic smoothing, or relying on scripted facades.

This document replaces ungrounded calendar and equation promises with measurable behavioral evidence bars. Production remains governed by the canonical physical loop; all speed harnesses and hierarchical stack fixtures are explicitly quarantined as test-only evaluation apparatuses.

---

## 1. Grounded Developmental Evidence Criteria

In Deterministic Structural Field AI (DSF-AI), the L0–L4 structural kernel ($D_k, S_{UF}, M_k, R_{rev,k}, U^*_k, C_k, P_k, B_k$) dimensionalizes continuous-time sensory-motor interaction into deterministic geometry. 

Crucially, kernel metrics do not by themselves establish high-level cognition or language:
- Positive structural stability ($S_{UF} > 0$) indicates Lyapunov stability of the field; it does **not** by itself establish grammatical composition, semantic liking, or social intent.
- Pressure exceeding breathing ($P_k > B_k$) indicates metabolic or structural tension; it does **not** by itself establish wanting or teleological demand without derived sensorimotor grounding and behavioral evidence.

Linguistic and cognitive milestones are defined strictly as **behavioral acceptance criteria** requiring demonstrated physical consequence, not programmer-supplied action lists or canned syllable sequences:

| Target Milestone | Phenomenological Description | Grounded Physical Evidence Requirement | Baseline Horizon |
| :--- | :--- | :--- | :--- |
| **First-Person Teleological Demand** | "I want [X]" / vocal demand | Measured metabolic tension + physical focal orientation + motor reach toward target + reciprocal sound emission contingent on target state. | Month 3 – 6 |
| **Affective Basin Valuation** | "I like [X]" / selective preference | Measured stability contrast across entities + repeatable approach bias toward preferred physical entity + persistence across repeated encounters. | Month 6 – 9 |
| **Cooperative Joint Affordance** | "Let's Play" / shared activity | Mutual gaze alignment + contingent give-and-take physical manipulation with caregiver + social interaction initiation. | Month 9 – 12 |
| **Prescriptive Deontic Guidance** | "You should [X]" / normative cue | Observed modeling of external agent state + corrective vocal/gestural directive contingent on external agent trajectory. | Month 18 – 24 |

---

## 2. The Four Acceleration Levers: Calibrated & Grounded

Developmental acceleration cannot be achieved by substituting scripted shims for physical cognition. The four levers are defined under strict empirical constraints:

### Lever 1: Headless Simulation Overclocking ($\Delta t_{\text{sim}} \ll \Delta t_{\text{wall}}$)
- **Objective**: Maximize valid sensorimotor experience per wall-clock hour.
- **Correction & Invariant**: 
  - Compiling or running in headless mode does not establish a $10\times$–$50\times$ speedup without verified, whole-loop measurement that includes full physical settlement, observation rendering, and state persistence.
  - Compressing wall-clock time does not automatically produce cognitive development. Simulated time is merely an execution metric; developmental progression must be proven by demonstrated behavioral competence at each milestone.

### Lever 2: Simulation-to-Body Transfer (Sim-to-Real)
- **Objective**: Preserve learned structural memory and identity across virtual and embodied physical substrates.
- **Correction & Invariant**:
  - Memory persistence across substrates cannot be established merely by copying state tensors or databases.
  - Physical embodiment introduces real-world latency, acoustic distortion, sensor noise, calibration drift, and compliant actuator dynamics. Valid transfer requires calibrated coordinate transformations and demonstrated reuse of learned behavioral policies on physical hardware.

### Lever 3: Multimodal Contingency & Environmental Richness
- **Objective**: Provide structured, responsive, multimodal interaction across visual, acoustic, and somatic sensory lanes.
- **Correction & Invariant**:
  - The objective is **not** to "eliminate every quiet interval." Forcing continuous external stimulation is biologically and computationally ungrounded; developing organisms require quiet periods for memory consolidation, self-initiated exploratory behavior, motor babbling, and physical rest.
  - Sensory flux must be contingent and interactive: more information volume is not automatically usable learning. Richness is measured by contingency and feedback, not brute sensory bombardment.

### Lever 4: Multi-Timescale Activity & Experience-Grown Persistence
- **Objective**: Enable sustained goal-directed activity with rapid interruption and reality-governed adaptation.
- **Correction & Invariant**:
  - **Quarantine of Scripted Stack**: The intent stack (`dsf_ai_service/guala_hierarchical_stack.py`) with hardcoded syllable pairs (`"dah0"`, `"bah1"`) and enum labels (`TELEOLOGICAL_DEMAND`) is a scripted test fixture. It does not evaluate the 7-field kernel and will **never** be activated as Guala's production cognitive authority.
  - **Single Clock with Retained State**: A single canonical clock ($\Delta t = 250\,\text{ms}$) does not preclude macroscopic intention. Twenty consecutive $250\,\text{ms}$ updates sustain 5 seconds of coherent behavior provided the organism retains physical state across beats. Multiple separate loops do not supply learning, meaning, or syntax automatically.
  - **Unified Organism Architecture**: One organism with multiple causal timescales:
    1. *Retained Experience*: Past interactions establish persistent attractor relationships in state memory.
    2. *Active Persistence*: Ongoing pursuits persist through these retained relationships across canonical ticks without needing global re-initialization.
    3. *Prompt Interruption*: Fast cutaneous, acoustic, or obstacle collision signals interrupt or redirect the active trajectory immediately.
    4. *Consequence Feedback*: Physical environmental outcomes (e.g. food reached, obstacle blocked, object removed) reinforce, adjust, or terminate the pursuit.

---

## 3. Infrastructure Scaling Boundaries (Measurable Engineering Metrics)

Arbitrary tick counts (such as "100,000 ticks") do not define physical boundaries. Infrastructure transitions are governed strictly by measurable latency and memory thresholds:

1. **State Persistence Latency**: Disk/S3 serialization must not exceed an allowable fraction of the canonical tick budget ($< 50\,\text{ms}$ of $250\,\text{ms}$). If memory growth causes serialization pauses that breach continuous-time execution, binary state storage or incremental delta persistence must be deployed.
2. **Bounded Memory Allocation**: All runtime histories, sensory buffers, and transaction logs must adhere to $O(1)$ hard capacity bounds (ring buffers), preventing unbounded RAM growth.
3. **Equivalence Verification**: Any compilation or native core acceleration must be verified byte-for-byte or trajectory-for-trajectory against reference dynamics to prevent ML approximations or floating-point drift.

---

## 4. The Focused Empirical Next Milestone: Experience-Grown Pursuit

Before any multi-word syntax or advanced cognitive layers are considered, the architecture must satisfy a single, bounded empirical acceptance milestone:

> ### The Pursuit Milestone (Acceptance Criterion)
> **Demonstrate one experience-grown pursuit that survives a distraction, resumes when appropriate, and stops or changes when its real consequence changes—without a supplied action list, semantic intent label, or forced duration.**

### Required Concrete Mechanism Connections

The pursuit milestone is an acceptance criterion, not an executable learning law. Calling a record an "attractor basin" does not substitute for connecting actual state to action. To satisfy this criterion without heuristic shims or semantic labels, the implementation must explicitly specify and connect five physical mechanisms to source code:

1. **Retained State**: What exact physical state representations (in body state, spatial memory, or organism drives) are retained and preserved across consecutive ticks.
2. **Update Law**: The deterministic mathematical law governing how sensory experience and somatic outcomes update this retained state.
3. **Action Influence**: How this retained state biases the physical motor action choices during each canonical step.
4. **Interruption & Resumption**: How an unexpected sensory event (e.g. tactile shock, loud acoustic event, or physical barrier) preempts current motor execution, and what rule determines whether the retained pursuit resumes or terminates once the distraction ends.
5. **Consequence-Driven Termination**: How the verified physical outcome (e.g. goal attainment, target displacement, or metabolic satiation) alters or clears the retained state, ensuring behavior remains locked to physical reality rather than open-loop script execution.
