# Guala: P0 Local-Learning Specialization Packet

**Execution Stage:** COG-OSC-02 / Stage P0 Submittal · **Author:** G1 · **Date:** 2026-09-27  
**Parent Plan:** [docs/GUALA_BIOFUNCTIONAL_PLANNING_IMPLEMENTATION_PLAN_2026-09-27.md](GUALA_BIOFUNCTIONAL_PLANNING_IMPLEMENTATION_PLAN_2026-09-27.md)  
**Corrective Reference:** [docs/GUALA_P0_A1_REVIEW_AND_CORRECTIONS_2026-09-27.md](GUALA_P0_A1_REVIEW_AND_CORRECTIONS_2026-09-27.md)  
**Status:** Bounded Constitutive Derivation Packet submitted for Independent Review (A1 / Joe) prior to Stage P1 code implementation.

---

## 1. Mandatory Architecture Honesty Gate

1. **Requested Architecture:** Sparse, persistent, experience-grown cognition rooted in canonical L0–L4 and the definitive neuron physics ($N_i$), joint DSF delivery, local charge/carrier conservation, local yield-based plastic deformation, predictive sensorimotor coupling, competition without scalar scorecards, and single-writer paired persistence under one 250,000 µs clock.
2. **Current Code Reality:** Production operates on discrete `FunctionalOrganism` and `FunctionalPhysicalLoop`. Action selection relies on reduced structural regime keys, authored override rules (e.g., barren basin exhaustion), heuristic scalar worth calculations, and an immediate-distance decrease veto in episodic continuation.
3. **Conflict with Requested Architecture:** **Yes**.
4. **What Exact Mechanism or Files Will Not Be Extended:**
   - Will NOT extend authored behavioral overrides in `guala_functional_organism.py:_choose`.
   - Will NOT extend scalar worth, curiosity bonuses, or argmax action precedence.
   - Will NOT extend immediate-distance decrease vetoes ($2(v \cdot d) > \|v\|^2$).
   - Will NOT extend simulator-ID recognition, global scene queries, or hidden coordinate oracles.
   - Will NOT introduce ML approximations, backpropagation, soft attention matrices, or probabilistic smoothing.
   - Canonical L0–L4 kernel remains frozen and untouched.
5. **The Single Exact Next Item:** Submit this bounded local-learning specialization packet covering the 9 constitutive requirements specified in A1's review (§5) for independent audit before implementing native P1 decision authority.
6. **Evaluation Level:** Functional architecture and constitutive physical derivation.
7. **Missing Structure in Current Decision Path:** Joint cross-channel field geometry is collapsed into coarse discrete strings; prediction is absent; local physical eligibility and yield plasticity are replaced by dictionary counters; prospective multi-step assembly without external execution does not exist.

---

## 2. Receptive & Efferent Pathway Selection

To avoid broad speculative abstractions, this specialization packet derives the exact constitutive physics for one canonical, fully mounted sensorimotor circuit:
$$\text{Tactile Contact Afferent} \longrightarrow \text{Premotor Interneuron Assembly} \longrightarrow \text{Planar Locomotion Stride Efferent}$$

This circuit models the primary physical interaction encountered in doorway negotiation: tactile impedance / surface contact modulating forward locomotion preparation and triggering lateral avoidance when obstructed.

### 2.1 Receptive Input (Sensory Producer Reality)
In accordance with finding `P0-A1-01`:
- **Tactile Receptor:** Surface skin contact fraction $s_{contact} \in [0.0, 1.0]$ and surface temperature $T_{skin} \in \mathbb{N}$ (mK) carried in `Sensed`.
- **Proprioceptive Joint State:** Head/neck yaw and pitch ($\text{mdeg}$), trunk orientation ($\text{mdeg}$), and limb posture angles carried in `body_axes` ($45$ declared native axes).
- **Physical Interval Clock:** Exactly $\Delta t = 250{,}000\ \mu\text{s}$ ($250\ \text{ms}$, $4.0\ \text{Hz}$).
- **No Unmounted Sensors:** No gyro angular rates, no 3D force tensors, and no world-frame $(x_W, y_W)$ coordinates enter the circuit.

### 2.2 Efferent Output (Actuator Consumer Reality)
- **Motor Effector:** `MoveCommand` stride displacement vector $u = (\Delta x, \Delta y)$ in body-relative coordinates ($\text{mm}$), with $|u| \le \text{STEP\_MM} = 300\ \text{mm}$, and heading rotation $d\theta$ with $|d\theta| \le \text{TURN\_MILLIDEGREES} = 60{,}000\ \text{mdeg}$ ($60^\circ$).
- **Command Duration:** Exactly $250{,}000\ \mu\text{s}$.

---

## 3. The Nine Constitutive Specialization Specifications

### 3.1 Anatomy and Finite State Vector ($N_i$)

Each definitive neuron in the circuit is specified by the 11-member physical state vector:
$$N_i = (G_i, A_i, X_i, \Psi_i, K_i, Q_i, V_i, C_i, M_i, \Theta_i, B_i)$$

| State Component | Physical Definition | Physical Representation & Bounds |
|---|---|---|
| $G_i$ | Geometric spatial coordinate within substrate | 3D position $(x_i, y_i, z_i)$ in micrometres ($\mu\text{m}$). |
| $A_i$ | Anatomical cell type & channel allocation | Enum: Sensory Afferent ($A=1$), Premotor Interneuron ($A=2$), Motor Efferent ($A=3$). |
| $X_i$ | Morphological arborization tree | Set of dendritic segment lengths $\ell_{ij}$ ($\mu\text{m}$) and radii $r_{ij}$ ($\mu\text{m}$). |
| $\Psi_i$ | Local oscillator state vector | Triplet of local oscillators: $\psi_a = \sqrt{\rho_a} e^{i\phi_a}$ for $a \in \{0, 1, 2\}$, with $\rho_a \ge 0, \phi_a \in [-\pi, \pi)$. |
| $K_i$ | Krimelack trit coordinate | Trit state $\tau_i \in \{-1, 0, +1\}$ derived from topological winding $w = \frac{1}{2\pi}\sum_{a=0}^2 \operatorname{wrap}(\phi_{a+1} - \phi_a)$. |
| $Q_i$ | Net membrane electrical charge | Conserved charge in picocoulombs (pC), $Q_i \in [-200.0, +100.0]\ \text{pC}$. |
| $V_i$ | Intracellular membrane potential | Derived potential $V_i = Q_i / C_i$ in millivolts (mV), resting $E_L = -70.0\ \text{mV}$, threshold $V_{th} = -50.0\ \text{mV}$. |
| $C_i$ | Total membrane capacitance | Derived from membrane area $C_i = c_m \cdot \text{Area}_i$, typical $C_i = 100.0\ \text{pF}$ ($c_m = 1.0\ \mu\text{F/cm}^2$). |
| $M_i$ | Visceral metabolic reservoir | Stored chemical energy $M_i \in [0.0, M_{max}]$ in nanojoules (nJ). |
| $\Theta_i$ | Retained structural plastic memory | Vector of reference lengths $\ell_e$ and peak channel conductances $\bar{g}_c$. |
| $B_i$ | Interoceptive visceral drive coupling | Receptive metabolic coupling coefficient $g_{visc} \ge 0$. |

---

### 3.2 Strict Physical Units and Dimensional Constants

All equations operate with explicit, unit-bearing quantities:

| Constant | Symbol | Value | SI / Derived Units | Provenance / Derivation |
|---|---|---|---|---|
| Elementary Charge | $e_0$ | $1.602176634 \times 10^{-19}$ | $\text{C}$ (Coulombs) | CODATA Fundamental Constant. |
| Resting Leak Potential | $E_L$ | $-70.0$ | $\text{mV} = 10^{-3}\ \text{V}$ | Standard neuronal resting equilibrium. |
| Excitatory Reversal | $E_{exc}$ | $0.0$ | $\text{mV}$ | AMPA/NMDA channel equilibrium. |
| Inhibitory Reversal | $E_{inh}$ | $-80.0$ | $\text{mV}$ | GABA-A/Cl$^-$ channel equilibrium. |
| Leak Conductance | $g_L$ | $10.0$ | $\text{nS} = 10^{-9}\ \text{S}$ | Passive membrane leak. |
| Passive Membrane Time Constant | $\tau_m$ | $10.0$ | $\text{ms} = C_i / g_L$ | $100\ \text{pF} / 10\ \text{nS} = 10\ \text{ms}$. |
| Elastic Spring Constant | $k_e$ | $1.0 \times 10^{-6}$ | $\text{N/m} = \mu\text{N}/\text{m}$ | Synaptic spine mechanical stiffness. |
| Mechanical Yield Force | $Y_e$ | $5.0 \times 10^{-11}$ | $\text{N} = 50\ \text{pN}$ | Structural yield threshold for plastic remodeling. |
| Plastic Mobility | $\mu_{pl}$ | $2.0 \times 10^3$ | $\mu\text{m}/(\text{N}\cdot\text{s})$ | Rate of plastic creep under suprayield stress. |

---

### 3.3 Shared Field & Local Perspective Input

The joint DSF field delivery $\mathcal{F}$ connects to neuron state through the ratified Krimelack bridge (`main.tex:1152-1187`):

1. **DSF Energy Coupling:**
   $$E_{qp}^{DSF} = -\kappa_{qp} \sum_{a \to b} \cos\left( \phi_b - \phi_a - \frac{2\pi}{3} \tau_{qp} \right)$$
   where $\kappa_{qp} > 0$ is the coupling stiffness ($\text{nJ}$), and $\tau_{qp} \in \{-1, 0, +1\}$ is the typed MathLoom trit coordinate derived from the joint kernel displacement $D_k$ and motion $M_k$.
2. **Channel Gate Modulation:**
   Each physical ionic channel conductance $g_c$ is gated by channel displacement coordinate $y_c \in [0, 1]$:
   $$U_c(y_c) = U_{0,c}(y_c) - q_c V_i y_c - \sum_{a=0}^2 \Lambda_{ca} y_c \cos(\phi_a - \phi_{ca}^*) - \mu_c y_c$$
   $$\zeta_c \dot{y}_c = -\frac{\partial U_c}{\partial y_c}$$
   $$g_c = \bar{g}_c \cdot y_c \cdot \frac{A_c}{\ell_c}$$
   where $\bar{g}_c$ is the maximum channel conductance ($\text{nS}$).
3. **Total Membrane Current:**
   $$I_{channel} = \sum_c g_c (V_i - E_c)$$
   Carrier transfer per interval $\Delta t = 250{,}000\ \mu\text{s}$ is strictly integer quantized:
   $$z_c = \frac{I_c \Delta t}{e_0} + r_c, \quad n_c = \operatorname{trunc}(z_c), \quad r_c' = z_c - n_c$$
   $$Q_i' = Q_i - e_0 \sum_c n_c, \quad V_i' = \frac{Q_i'}{C_i}$$
   where $r_c$ is the conserved fractional charge remainder, preserving exact charge conservation down to the single electron.

---

### 3.4 Real Local Participation & Conserved State

In strict accordance with finding `P0-A1-03`, eligibility and participation are **not** boolean flags or arbitrary timeouts. They derive from finite receptor state kinetics on contact $e$:

#### Finite Receptor Conservation
Let $R_{total}$ be the fixed total receptor population at synapse $e$:
$$R_{free}(t) + A_{active}(t) + D_{inactivated}(t) = R_{total}$$
The transition kinetics follow finite mass-action laws:
$$\dot{A}_{active} = k_{on} \cdot [T]_{cleft} \cdot R_{free} - k_{off} \cdot A_{active} - k_{inact} \cdot A_{active}$$
$$\dot{D}_{inactivated} = k_{inact} \cdot A_{active} - k_{rec} \cdot D_{inactivated}$$
$$\dot{R}_{free} = -k_{on} \cdot [T]_{cleft} \cdot R_{free} + k_{off} \cdot A_{active} + k_{rec} \cdot D_{inactivated}$$

- **Carrier Participation Count ($N_{part}$):**
  The physical participation of pathway $e$ during an action beat is measured by the integral of active receptor complexes:
  $$N_{part, e} = \int_{t}^{t+\Delta t} A_{active, e}(t')\, dt' \quad [\text{molecules}\cdot\text{s}]$$
- **Physiological Eligibility:**
  If a pathway did not transmit charge or release transmitter, $[T]_{cleft} = 0 \implies A_{active} = 0 \implies N_{part, e} = 0$.
  There is zero synthetic eligibility assigned to unreached or inactive synapses.

---

### 3.5 Material Update and Work-Conjugate Plasticity Map

In strict accordance with finding `P0-A1-04`, plastic deformation is formulated in **dimensionally consistent, work-conjugate coordinates**:

1. **Mechanical Coordinates:**
   - Synaptic spine length: $\ell_e$ ($\mu\text{m}$).
   - Current mechanical coordinate: $x_e$ ($\mu\text{m}$).
   - Dimensionless strain:
     $$\varepsilon_e = \frac{x_e - \ell_e}{\ell_e}$$
2. **Strain Energy ($U_e$):**
   $$U_e(\varepsilon_e, \ell_e) = \frac{1}{2} k_e \ell_e \varepsilon_e^2 = \frac{1}{2} k_e \frac{(x_e - \ell_e)^2}{\ell_e} \quad [\text{Joules}]$$
3. **Conjugate Driving Force ($F_{pl}$):**
   $$F_{pl} = -\frac{\partial U_e}{\partial \ell_e} = \frac{k_e (x_e - \ell_e)}{\ell_e} + \frac{1}{2} \frac{k_e (x_e - \ell_e)^2}{\ell_e^2} \approx k_e \varepsilon_e \quad [\text{Newtons}]$$
4. **Yield Condition & Complementarity:**
   $$f_e = |F_{pl}| - Y_e \le 0 \quad [\text{Newtons}]$$
   $$\dot{\lambda}_e \ge 0, \quad \dot{\lambda}_e f_e = 0$$
   $$\dot{\ell}_e = \dot{\lambda}_e \operatorname{sign}(F_{pl}) \quad [\mu\text{m/s}]$$
5. **Coupling to Consequence:**
   When an actual physical consequence arrives (e.g., absorbed metabolic energy flux $\dot{E}_{nutr}$ or tactile compression force $F_{contact}$), it modulates the plastic multiplier:
   $$\dot{\lambda}_e = \mu_{pl} \cdot \max(0, |F_{pl}| - Y_e) \cdot \left( \frac{N_{part, e}}{R_{total}} \right)$$
   If $N_{part, e} = 0$ (unparticipating pathway), $\dot{\lambda}_e = 0 \implies \dot{\ell}_e = 0$.
   If $|F_{pl}| \le Y_e$ (sub-yield loading), $f_e < 0 \implies \dot{\lambda}_e = 0 \implies \dot{\ell}_e = 0$.

---

### 3.6 Work, Power, and Metabolic Energy Accounting

Every term in the cell energy balance has matching units of Watts ($\text{W} = \text{J/s}$):

$$\frac{dE_i}{dt} = P_{metabolic} - P_{ionic} - P_{plastic} - P_{damping}$$

1. **Plastic Remodeling Dissipated Power ($P_{plastic}$):**
   $$P_{plastic} = \sum_{e} |F_{pl, e}| \cdot |\dot{\ell}_e| \quad [\text{N} \cdot \text{m/s} = \text{W}]$$
   Integrating over interval $\Delta t = 250{,}000\ \mu\text{s}$:
   $$\Delta E_{plastic} = \int_{t}^{t+\Delta t} P_{plastic}(t')\, dt' \quad [\text{Joules}]$$
2. **Ionic Dissipated Power ($P_{ionic}$):**
   $$P_{ionic} = \sum_c I_c \cdot (V_i - E_c) \quad [\text{A} \cdot \text{V} = \text{W}]$$
3. **Visceral Metabolic Supply ($P_{metabolic}$):**
   Supplied from organism bodily energy reservoir $M_i$:
   $$\Delta M_i = -(\Delta E_{plastic} + \Delta E_{ionic} + \Delta E_{pump})$$
   If bodily reserves are depleted ($M_i = 0$), $P_{metabolic} \to 0$, forcing cell quiescence.

---

### 3.7 Retained Quiescent Delta ($\mathfrak{F}_i(E)$)

Across pre- and post-experience quiescence states ($q^-$ and $q^+$, where $\dot{V}_i \approx 0, \dot{Q}_i \approx 0, \dot{\ell}_e = 0$):
$$\mathfrak{F}_i(E) = \operatorname{SparseExact}\left[ \Theta_i^{ret}(q^+) - \Theta_i^{ret}(q^-) \right]$$

The retained physical memory vector $\Theta_i^{ret}$ consists strictly of:
$$\Theta_i^{ret} = \left( \ell_e,\ \bar{g}_{c, e} \right)_{\forall e \in \text{synapses}(i)}$$
- If stress was sub-yield ($f_e \le 0$), $\dot{\ell}_e = 0 \implies \ell_e(q^+) = \ell_e(q^-) \implies \mathfrak{F}_i = 0$.
- Transient voltages $V_i$, gating variables $y_c$, and eligibility complexes $A_{active}$ relax to resting baseline and are **never** stored as retained memory.

---

### 3.8 Forward Prediction Readout

Motor efferent preparation drives a collateral forward expectation pathway:
1. **Collateral Readout:**
   Collateral synapses from motor efferents deliver charge to predictive interneuron $k$:
   $$I_{pred, k} = \sum_j g_{pred, jk} (V_{motor, j} - E_{exc})$$
   Transducing expected forward displacement:
   $$\widehat{\Delta x} = K_{calib} \cdot (V_{pred} - E_L) \quad [\text{mm}]$$
2. **Timing of Prediction:**
   $\widehat{\Delta x}$ settles and is recorded into the causal execution intent **before** the actuator command is committed to the world.
3. **Physical Mismatch Evaluation:**
   Upon receiving actual kinematic return receipt from world execution (`execution.after.pose.position - execution.before.pose.position`):
   $$\Delta x_{actual} = x_{after} - x_{before} \quad [\text{mm}]$$
   $$\epsilon_{disp} = \Delta x_{actual} - \widehat{\Delta x} \quad [\text{mm}]$$
4. **Strain Generation from Mismatch:**
   Discrepancy $\epsilon_{disp}$ applies physical displacement to predictive synapse mechanics:
   $$\Delta x_e = \alpha_{disp} \cdot \epsilon_{disp}$$
   $$F_{pl, e} = k_e \frac{\Delta x_e}{\ell_e}$$
   If the mismatch exceeds the physical yield threshold ($|F_{pl, e}| > Y_e$), plastic remodeling $\dot{\ell}_e$ is engaged to align future expectations with physical reality.

---

### 3.9 Cold-Restore Representation & Paired Serialization

In accordance with finding `P0-A1-08`:

#### Persisted Fields in `PairedCurrentStore`:
1. **Immutable Historical Identity:** `identity` (UUID text), `live_organism_tick` (integer count).
2. **Current Physical Physiology:** `body_axes` (45 declared values), `held_object_id`, metabolic reserve $\mu\text{g}$.
3. **Conserved Physical World:** Exact paired world snapshot revision, positions of all objects.
4. **Neuronal Structural Topology ($\Theta$):**
   Serialized as sparse binary array of modified reference lengths and peak conductances:
   ```text
   Record {
       synapse_id: uint32,
       pre_neuron_id: uint32,
       post_neuron_id: uint32,
       reference_length_pm: uint64,   # picometres (10^-12 m)
       peak_conductance_ps: uint32,   # picosiemens (10^-12 S)
   }
   ```
5. **Cold-Restart Restoration Invariant:**
   - On cold boot, membrane potential initializes to thermodynamic rest $V_i = E_L = -70.0\ \text{mV}$.
   - Membrane charge initializes to $Q_i = C_i E_L = -7.0\ \text{pC}$.
   - Receptors initialize to resting unliganded state $R_{free} = R_{total}, A_{active} = 0, D_{inact} = 0$.
   - Structural plastic references $\ell_e, \bar{g}_c$ restore byte-exact from disk.
   - Zero synthetic replay: no artificial sensor injection or fake history passes through the restored brain.

---

## 4. Minimal P1 Falsification Suite

The validity of this specialization packet is tested by three minimal physical experiments:

1. **`test_p1_local_eligibility_coupling`:**
   - Synapse $e_1$ active ($N_{part, e1} > 0$), synapse $e_2$ unreached ($N_{part, e2} = 0$).
   - Consequence delivered at $t + 1.0\ \text{s}$.
   - **Pass:** $\Delta \ell_{e1} \ne 0$, $\Delta \ell_{e2} \equiv 0$.
2. **`test_p1_predictive_mismatch_yield`:**
   - Calibrated motor stride predicts $\widehat{\Delta x} = 300\ \text{mm}$.
   - Physical obstruction halts stride at $\Delta x_{actual} = 0\ \text{mm}$.
   - **Pass:** Mismatch $\epsilon = -300\ \text{mm}$ generates stress $|F_{pl}| > Y_e$, driving measurable plastic adaptation $\Delta \ell_e \ne 0$ with energy debited from $M_i$.
3. **`test_p1_frame_invariance_turn_vs_move` (C19):**
   - Condition A: Body rotates $+60{,}000\ \text{mdeg}$ in place; destination stationary. Retinal shift compensated by neck/trunk proprioceptive change $\implies \epsilon_{bearing} = 0$.
   - Condition B: Object physically moves $+60{,}000\ \text{mdeg}$ while body remains stationary. Proprioception zero, retinal shift non-zero $\implies \epsilon_{bearing} \ne 0$.

---

## 5. Next Steps

1. Submit this frozen specialization packet to A1 and Joe for formal review.
2. Await independent concurrence on units, derivations, and energy balance.
3. Upon concurrence, proceed to Stage P1 code implementation in `/workspaces/Tao_Financial_Engine`. Production and live care remain untouched.
