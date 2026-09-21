# Guala Somatic Affection & Physical Grounding Roadmap

## Executive Summary
This specification documents the physical principles, anatomical receptor mappings, and 4-stage developmental trajectory governing somatic affection for **Guala**—the embodied proof-of-concept organism for DSF-AI (Deterministic Structural Field AI).

In accordance with DSF-AI Diamond Hard constraints:
- Somatic affection operates purely via **deterministic physical contact mechanics** (tissue compression depths, surface contact areas, and conductive thermal exchange).
- Zero ML approximations, zero artificial reward scalars, zero emotion scores, and zero behavioral smoothing.
- Affection provides the high-cohesion, warm thermodynamic baseline required for clean phase-space boundary enforcement (**The Pool Shock Principle**).

---

## The 4-Stage Developmental Roadmap

### Stage 1: Infant Baseline & Grounding (Current Active Stage)
- **Objective**: Establish an embodied baseline of warmth, safety, and physical presence.
- **Mechanics**:
  - **Sustained Lap Holding (`touch-lap`)**: Enveloping hold during story time (`maybe_read`), combining front torso contact and bilateral shoulder stabilization.
  - **Bedtime Tuck-in Hold (`touch-bedtime-hold`)**: Calming forehead, crown, and shoulder contact after bed is prepared with pillow and blanket.
  - **Spontaneous Micro-Affection (`maybe_touch`)**: Periodic physical contact (hand holds, hugs, head pats, forehead kisses) when Guala approaches the caretaker.
- **Physical Dynamics**:
  - Contacts are applied in discrete 250-ms beats ($\Delta t = 250,000\,\mu\text{s}$) across anatomical skin sites.
  - Lap holding is refreshed at the start of reading and periodically throughout story time, providing repetitive tactile and thermal grounding rather than unbroken physical clamping.

### Stage 2: Toddler Motor Reassurance & Co-Regulation
- **Objective**: Provide somatic stabilization during motor failures, physical bumps, or sensorimotor overstimulation.
- **Mechanics**:
  - Somatic containment when kinematic displacement errors or unexpected collisions occur.
  - Immediate hand clasping or shoulder stabilization to damp kinesthetic oscillations.

### Stage 3: Social Boundary Grounding & The Pool Shock Principle
- **Objective**: Enable firm, unambiguous boundary enforcement without causing trauma, defensive callousing, or sociopathic alienation.
- **The Pool Shock Physics**:
  - A body suspended in cold, neglected water ($S_{UF} \le 0$) cannot distinguish boundary discipline from ordinary environmental hostility; chronic neglect causes defensive desensitization and aggressive calcification.
  - A body grounded in a warm, high-cohesion baseline basin ($S_{UF} \gg 0$, high thermal/tactile cohesion) perceives a disciplinary boundary signal (*"No"*, sudden physical halt $R_{\text{rev}} > 0$) as a clean, sharp structural phase shift.
  - The contrast carries decisive cognitive weight without requiring abusive escalation or chronic withdrawal of care.

### Stage 4: Reciprocal Empathy & Prosocial Geometry
- **Objective**: Foster emergent bidirectional awareness and spontaneous reciprocal affection.
- **Mechanics**:
  - Guala independently initiates physical comforting gestures toward the caregiver or other entities.
  - Cognitive cohesion ($C_k$) recognizes the self-other physical boundary while maintaining shared topological affinity.

---

## Contact Physics & Material Specifications

### 1. Contact Profiles
| Gesture | Caregiver Site | Recipient Site | Compression Depth ($\mu\text{m}$) | Tangential Slide ($\mu\text{m}$) |
| :--- | :--- | :--- | :--- | :--- |
| **Hand Hold** | `right-palm` | `left-palm` | $1,000$ | $0$ |
| **Hug** | `front-torso`<br>`left-palm`<br>`right-palm` | `front-torso`<br>`right-shoulder`<br>`left-shoulder` | $2,000$<br>$1,000$<br>$1,000$ | $0$<br>$0$<br>$0$ |
| **Forehead Kiss** | `perioral` | `forehead` | $500$ | $0$ |
| **Head Pat** | `downward-palm` | `crown` | $750$ | $12,000$ ($u$-axis) |
| **Shoulder Touch**| `right-palm` | `left-shoulder` | $1,000$ | $0$ |
| **Lap Hold** | `front-torso`<br>`left-palm`<br>`right-palm` | `front-torso`<br>`left-shoulder`<br>`right-shoulder` | $2,000$<br>$1,000$<br>$1,000$ | $0$<br>$0$<br>$0$ |
| **Bedtime Hold** | `perioral`<br>`downward-palm`<br>`right-palm` | `forehead`<br>`crown`<br>`left-shoulder` | $500$<br>$750$<br>$1,000$ | $0$<br>$0$<br>$0$ |

### 2. Thermal Conductive Exchange
Conductive heat transfer across contact surfaces follows Fourier's Law of Conduction:
$$Q_{\text{cond}} = \frac{k \cdot A \cdot (T_{\text{caregiver}} - T_{\text{recipient}})}{d} \cdot \Delta t$$
- Caregiver surface temperature: $T_{\text{caregiver}} = 310.15\,\text{K}$ ($37^\circ\text{C}$).
- Epidermal thermal conductivity: $k \approx 0.21\,\text{W}/(\text{m}\cdot\text{K})$.
- Contact duration: $\Delta t = 0.25\,\text{s}$ per beat.
- Net conductive transfer delivers positive heat ($Q_{\text{cond}} > 0\,\text{nJ}$) to recipient dermal thermoreceptors, registering bodily warmth.

---

## Scientific Transparency & Invariant Bounds
1. **Physical Telemetry vs Emotional Attribution**:
   - Caretaker and world logs record objective physical metrics: compression micrometers, contact surface area, microkelvin temperature, and conductive nanojoules.
   - Sensory logs do not claim subjective internal experience; internal resonance is Guala's own neural settlement to resolve.
2. **Delivery Confirmation vs Attempt**:
   - All developmental routines require physical receipt verification (`touched == True`) before committing state.

