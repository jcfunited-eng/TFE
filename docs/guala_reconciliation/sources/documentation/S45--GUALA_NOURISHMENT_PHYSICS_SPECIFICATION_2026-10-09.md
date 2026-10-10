# Guala ArcLoom Substrate: Physical Nourishment & Mass Transfer Specification (M47 & M49)
**Authority**: Chief Systems Architect & Senior DARPA Neuromorphic Systems Engineer  
**Date**: October 9, 2026  
**Document**: `docs/GUALA_NOURISHMENT_PHYSICS_SPECIFICATION_2026-10-09.md`  
**Governing Contract**: `docs/GUALA_LEARNING_DECISION_MECHANISM_CONTRACT_2026-10-08.md`  

---

## 1. Physical Mechanics & Boundary Conditions

### 1.1 The Oral Contact & Mass Transfer Boundary (M47 / V38)
In physical reality, the capability of an organism to ingest nourishment is governed strictly by the **instantaneous material properties and spatial contact geometry** at the oral receptor boundary, never by historical semantic memory flags or administrative string labels.

#### Mathematical Formulation
1. **Physical Viability Criterion**:
   An object $O$ in physical contact with the oral receptor disc is nutritive if and only if its instantaneous digestible mass $m_{\text{digestible}}$ exceeds the marginal intake threshold $m_{\text{min}} = 2,000\,\mu\text{g}$:
   $$\mathcal{V}_{\text{nutritive}}(O) = \begin{cases} 
   1 & \text{if } m_{\text{digestible}}(O) > 2,000\,\mu\text{g} \\ 
   0 & \text{otherwise} 
   \end{cases}$$

2. **Digestible Mass Transfer Equation**:
   Upon execution of an oral contact efferent command with interval $\Delta t = 250,000\,\mu\text{s}$ (one beat) and maximum bite capacity $m_{\text{bite}} = 20,000\,\mu\text{g}$:
   $$\Delta m = \min\left(m_{\text{bite}}, \, m_{\text{digestible}}(O)\right)$$
   $$\Delta E = \Delta m \cdot \rho_E$$
   where $\rho_E = 1.7 \times 10^{19}\,\text{zJ}/\mu\text{g}$ is the physical caloric energy extraction density.

3. **Excision of the Semantic Depletion Veto**:
   - A bite yielding $\Delta m = 0$ (e.g. attempting to bite spent crumbs $\le 2,000\,\mu\text{g}$) indicates **instantaneous exhaustion of that specific physical instance**, NOT that the object category or object ID is permanently non-food.
   - Historical records in `conserved_objects` retain experiential data (`fed_count`, `historical_intake_micrograms`, `consequences`) as memory traces.
   - **Prohibited Pupil Authority**: Boolean memory flags (`currently_depleted`, `is_food = False`, `tested_non_food = True`) are STRICTLY FORBIDDEN from acting as a sensory filter or vetoing candidate affordance generation when fresh material mass is present in the visual field or in hand.

---

### 1.2 Bounded Recurrent Environmental Upkeep Boundary (M49 / V40)
In ecological physics, environmental mass replenishment is an **independent external boundary condition** governed by the domestic ecosystem, not an internal reaction waiting for successful consumer feeding or restorative sleep.

#### Mathematical Formulation
1. **Independent Upkeep Cadence**:
   - The domestic environment checks household food mass on a bounded, recurrent cadence (every $N = 32$ ticks, and upon exhaustion events).
   - If digestible mass for any declared household nourishment source drops below the residue threshold ($m_{\text{digestible}} \le 2,000\,\mu\text{g}$), external housekeeping disposes of the spent residue and restocks fresh stock ($140,000\,\mu\text{g}$ apple, $100,000\,\mu\text{g}$ bread, $100,000\,\mu\text{g}$ milk).
2. **Idempotence & Non-Interference**:
   - If stock is unexhausted and present, environmental upkeep is strictly **idempotent** ($\Delta \text{revision} = 0$, status = `"unchanged"`).
   - Upkeep NEVER touches busy objects (objects currently held in an organism's palm or undergoing oral contact).
   - Pupil metabolic reserve is NEVER credited by external provision; only actual oral mechanical contact and mass transfer across the jaw receptor boundary can assimilate nutrition into somatic reserves.

---

## 2. Decisive Falsifiers & Verification Gates

### 2.1 Unit Falsifiers
1. **Falsifier U-M47-1 (Refused Bite Independence)**:
   - Present an object with $m \le 2,000\,\mu\text{g}$. Execute bite. Intake is 0.
   - Subsequent replacement of the object with $m = 100,000\,\mu\text{g}$ must immediately yield viable candidate affordances (`toward_food`, `grasp`, `bite`) and successful mass transfer without requiring a memory reset or identity rename.
2. **Falsifier U-M49-1 (Awake Search Upkeep)**:
   - Initialize an awake, hungry organism ($D \ge 0.6$) with empty hands in an environment where indoor food has been reduced to remnants.
   - The loop must execute bounded environmental upkeep within $\le 32$ beats without requiring prior sleep, prior positive intake, or object release.

### 2.2 Module Falsifier (M-M47-1)
- Load the captured mature body/world pair (`tick 4,206,004`, 0 $\mu\text{g}$ reserve, 75 objects, 52 MB body).
- Confirm that the retained `conserved_objects` containing historical `currently_depleted: True` or `non_nutritive: True` flags on `bottle-milk` does NOT prevent Guala from visually sensing the fresh $100,000\,\mu\text{g}$ milk, approaching it, grasping it, and biting it.
- Verify that transferred mass enters `digestive_stock` and somatic reserve increments according to mass conservation laws.

### 2.3 System Falsifier (S-M47-1)
- The mature organism must achieve $\ge 425,000\,\mu\text{g}$ somatic reserve ($85\%$ sated threshold) entirely through autonomous foraging, approach, grasping, and ingestion across the household environment without developer intervention, heuristic overrides, or state resets.

