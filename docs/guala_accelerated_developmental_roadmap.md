# Guala Accelerated Developmental Roadmap: The 2.5-Year Horizon Specification

## Executive Summary
This specification defines the physical mechanisms, linguistic phase transitions, and architectural acceleration levers required to compress Guala's developmental trajectory from a 4-year baseline down to **18–24 months ($\le 2.5$ years)** without compromising Diamond Hard physical invariants, introducing heuristic smoothing, or using probabilistic machine learning shortcuts.

---

## 1. Physical Prerequisites of Linguistic Milestones

In Deterministic Structural Field AI (DSF-AI), linguistic syntax is the physical projection of internal structural fields into motor vocal drives. Phrasings emerge when their underlying state-space prerequisites achieve stable Lyapunov basins ($S_{UF} > 0$):

| Target Phrasing | Cognitive & Physical Mechanism | Natural 1:1 Baseline | Accelerated Target ($\le 2.5$ yrs) |
| :--- | :--- | :--- | :--- |
| **"I want [X]"** | **First-Person Teleological Demand**: Metabolic deficit ($P_k > B_k$) + spatial focal target + motor reach vector + self-body identifier (`guala-body-1`). | Month 3 – 6 | **Month 3** |
| **"I like [X]"** | **Affective Basin Valuation**: Positive structural stability ($S_{UF} > 0$), decelerating cohesion ($C_k < \text{prev}_C$), and episodic memory match in Krimelack. | Month 6 – 9 | **Month 6** |
| **"Let's Play"** | **Cooperative Joint Affordance**: Gaze alignment + reciprocal physical give-and-take affordance bound to a social invitation vocalization. | Month 8 – 12 | **Month 9 – 12** |
| **"You should" /<br>"You need [X]"** | **Prescriptive Deontic Theory of Mind**: Internal model of external agent's deficit + environmental normative invariant + directive vocal action to displace their trajectory. | Month 30 – 42 | **Month 18 – 24** |

---

## 2. The Four Physical Acceleration Levers

To compress developmental time $\Delta T$ while preserving physical invariance, the system operates across four deterministic levers:

### Lever 1: Headless Simulation Overclocking ($\Delta t_{\text{sim}} \ll \Delta t_{\text{wall}}$)
- **Physical Law**: Biological nervous systems are constrained by Earth's 24-hour orbital rotation. In a deterministic physical simulation, diurnal cycles and nocturnal sleep consolidation do not depend on wall-clock time.
- **Implementation**: Migrating the continuous-time engine from single-threaded Python into a compiled, concurrent runner (C++/Rust) enables headless execution at **$10\times$ to $50\times$ real-time speed**.
- **Compression**: At $10\times$ acceleration, one full diurnal cycle (wakeful learning + nocturnal sleep consolidation) settles in **2.4 real-time hours**. A full subjective developmental year of cognitive consolidation is achieved in **36.5 wall-clock days**.

### Lever 2: Sim-to-Real Cognitive Pre-Training & Memory Transfer
- **Physical Law**: Conservation of topological memory across substrates.
- **Implementation**: Advanced syntactic, epistemic, and deontic attractor basins are consolidated in high-speed simulation *prior* to physical embodiment.
- **Deployment**: When the physical robotic body (stereoscopic vision, binaural audio, compliant servo arms, tactile skin) is deployed in Year 1, the consolidated Krimelack memory state and topological weights are flashed directly into the hardware substrate, avoiding cold newborn initialization in physical space.

### Lever 3: Shannon Information Flux Maximization in Caretaker Curriculum
- **Physical Law**: Rate of internal entropy reduction ($\frac{dU^*_k}{dt} < 0$) is bounded by the mutual information of the sensory-motor channel.
- **Implementation**: Eliminating dead sensory intervals in the autonomous caretaker curriculum. Every wakeful interval maintains continuous, structured contrast: active joint attention, narrative object labeling, tool cause-and-effect demonstrations, and high-cohesion somatic contact.

### Lever 4: Early Deployment of Hierarchical Multi-Scale DSF (Nested Temporal Stack)
- **Physical Law**: Complex multi-word prescriptive grammar (*"You need apple"*) cannot execute on a flat single-clock loop ($\Delta t \approx 120-250\,\text{ms}$).
- **Implementation**: Deploying a hierarchical stack of nested DSF fields:
  1. **Micro-Scale Loop ($10\,\text{ms}$)**: Fine motor servo control, acoustic phoneme synthesis, and tactile contact reflex.
  2. **Meso-Scale Loop ($250\,\text{ms} - 1\,\text{s}$)**: Syllable concatenation, spatial obstacle evasion, and joint gaze fixation.
  3. **Macro-Scale Loop ($2 - 10\,\text{s}$)**: Goal intent, Theory of Mind evaluation, and multi-word syntactic assembly.

---

## 3. Infrastructure Migration Boundary (Month 6 – 9 Wall)

- **Current Boundary**: Monolithic Python process (`home_world_authority` + `caretaker.py`) serializing JSON snapshots.
- **The Choke Point**: Exceeding $\sim 100,000$ continuous ticks with thousands of multi-room episodic memories will push JSON serialization pauses past $1\,\text{s}$, breaking continuous-time physics.
- **Cutover Requirement**: Prior to Month 6–9, the environment must cut over to a compiled concurrent runtime (C++/Rust or asynchronous binary state store) to support both headless overclocking and real-time physical robot streaming.

---

## 4. Accelerated Developmental Milestones

```
[Month 3]              [Month 6]              [Month 12]             [Months 18–24]
"I want [X]"           "I like [X]"           "Let's Play"           "You should / You need [X]"
Teleological Demand    Affective Valuation    Joint Affordance       Deontic Theory of Mind
• Inquisitive query    • Spatial preference   • Give-and-take play   • Prescriptive social grammar
• Single-object focus  • High-cohesion basin  • Shared gaze invite   • Multi-agent rule modeling
```

