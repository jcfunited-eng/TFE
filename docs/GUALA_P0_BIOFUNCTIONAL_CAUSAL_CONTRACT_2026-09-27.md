# Guala: P0 Bio-Functional Causal Learning, Prediction, Persistence, and Migration Contract

**Execution Stage:** COG-OSC-02 / Stage P0 · **Author:** G1 · **Date:** 2026-09-27  
**Parent Document:** [docs/GUALA_BIOFUNCTIONAL_PLANNING_IMPLEMENTATION_PLAN_2026-09-27.md](GUALA_BIOFUNCTIONAL_PLANNING_IMPLEMENTATION_PLAN_2026-09-27.md)  
**Status:** Frozen Constitutive Contract for Independent Review (A1 / Joe) prior to Stage P1 implementation.

---

## 1. Mandatory Architecture Honesty Gate

1. **Requested Architecture:** Sparse, persistent, experience-grown cognition built upon the canonical L0–L4 kernel and definitive physical neuron physics ($N_i$). Operates through joint DSF delivery, local charge/carrier conservation, local yield-based plastic deformation, predictive sensorimotor coupling, competition without scalar scorecards, and single-writer paired persistence under one 250,000 µs physical interval clock.
2. **Current Code Reality:** Production operates on discrete `FunctionalOrganism` and `FunctionalPhysicalLoop` (`guala_functional_organism.py`, `guala_functional_loop.py`). Action selection currently combines reduced structural regime keys, authored override rules (such as barren basin exhaustion), heuristic scalar worth calculations, and an immediate-distance decrease veto in episodic continuation.
3. **Conflict with Requested Architecture:** **Yes**. Broad claims of flexible bio-functional planning are unsupported by the existing controller.
4. **What Exact Mechanism or Files Will Not Be Extended:**
   - Will NOT extend authored behavioral override branches (`guala_functional_organism.py:_choose`).
   - Will NOT extend scalar worth, curiosity bonuses, or argmax action precedence.
   - Will NOT extend immediate-distance decrease vetoes ($2(v \cdot d) > \|v\|^2$) as universal action gates.
   - Will NOT extend simulator-ID recognition, global scene queries, or hidden coordinate oracles.
   - Will NOT introduce ML approximations, backpropagation, soft attention matrices, or probabilistic smoothing.
   - Canonical L0–L4 kernel remains frozen and untouched.
5. **The Single Exact Next Item:** Deliver this frozen P0 contract detailing all seven constitutive derivation rows of §6.5, the source/loop mount, the lifetime migration map, and the minimal P1 falsifiers. Obtain independent review before writing P1 native decision authority.
6. **Evaluation Level:** Functional architecture and constitutive physical contract.
7. **Missing Structure in Current Decision Path:** Joint cross-channel field geometry is collapsed into coarse discrete strings; prediction is absent; local physical eligibility and yield plasticity are replaced by dictionary counters; prospective multi-step assembly without external execution does not exist.

---

## 2. Source-Linked Mount & Boundary Architecture

### 2.1 Authoritative Loop & Substrate Boundaries

The cognitive architecture interfaces with the physical universe strictly at the boundary of `FunctionalPhysicalLoop` and the native embodiment runtime:

```text
[ Physical World Environment ]
              │ (Receptors: Photons, Acoustic Pressure, Skin Thermal/Shear, Proprioception)
              ▼
    [ Sensory Ingress: Sensed ]
              │
              │  (Receptor conversions in declared physical units; zero hidden world IDs)
              ▼
    [ Joint DSF Delivery: L0–L4 Kernel ]
              │
              │  F_k = (D_k, M_k, R_rev,k, U*_k, C_k, P_k, B_k), S_UF
              ▼
    [ Definitive Neuron Substrate: N_i ]
         ├── Local Oscillator Dynamics (rho_a, phi_a, w)
         ├── Channel Gate Transport & Charge Conservation (Q_i, V_i, I_c, n_c)
         ├── Local Eligibility Traces (z_e)
         ├── Predictive Sensorimotor Mapping (P_theta)
         └── Prospective Recombination & Effector Competition
              │
              │ (One committed body command per 250,000 µs beat)
              ▼
    [ Effector Execution: PreparePortCommand ]
              │
              ▼
[ Physical Return: Actual Kinematic Displacement, Contact Normal/Shear, Oral Mass Transfer ]
```

### 2.2 Sensed Channel Units, Frames, and Provenance

Every incoming afferent to cognition is bound to declared physical units and sensor-local reference frames:

| Channel | Sensor / Mount | Physical Unit | Reference Frame | Provenance & Limits |
|---|---|---|---|---|
| **Retinal Luminance** | 405-site retinal array + 160×120 focal crop | Normalized photon flux $[0.0, 1.0]$ | Eye-relative spherical projection $(u, v)$ | Direct optical projection; no bounding boxes, no object IDs. |
| **Acoustic Pressure** | Bilateral cochlea (32 channels per ear) | Acoustic pressure amplitude (Pa), 16-bit PCM | Ear canal acoustic port | Bandpass cochlear filterbank; zero semantic text injection. |
| **Tactile Contact** | Palmar / plantar / skin surface patches | Normal force (mN), contact area ($\mu\text{m}^2$), shear vector $(\mu\text{m})$ | Body-surface local tangent coordinates | Real somatosensory contact; zero external proximity oracle. |
| **Thermal Flux** | Surface thermocouples | Temperature (mK) | Body-surface site | Conductive heat exchange; ambient reference. |
| **Proprioception** | 45 articulated native body axes | Position ($\mu\text{m}$ / $\text{mdeg}$), velocity ($\mu\text{m/s}$ / $\text{mdeg/s}$) | Joint-relative axis ordinal | Intrinsic strain/encoder readings; zero world-frame coordinate access. |
| **Vestibular Balance** | Otolith / semicircular canal proxy | Specific force ($R^T(a_s - g)$, $\text{mm/s}^2$), angular rate ($\text{mdeg/s}$) | Head-fixed coordinate frame | Passive inertial mechanics; zero absolute orientation cheat. |
| **Interoception** | Metabolic deficit, thermal load, sleep pressure | Dimensionless ratios $[0.0, 1.0]$, reserve deficit ($\mu\text{g}$) | Organism visceral core | Internal metabolic reservoir state; non-negotiable bodily demand. |

---

## 3. The Seven Constitutive Derivations (§6.5 Package)

### 3.1 Sensory & Efferent Mount

The substrate receives the canonical joint DSF field $\mathcal{F}$ alongside raw receptor vectors:
$$\mathcal{F} = (D_k, M_k, R_{rev,k}, U_k^*, C_k, P_k, B_k), \quad S_{UF}$$
where $k$ indexes the temporal sample stride at $\Delta t = 250{,}000\ \mu\text{s}$.

Effector outputs couple directly to available physical commands:
- **Locomotion:** One planar stride vector $u_{trans} = (dx, dy)$ in body-relative coordinates ($\text{mm}$, bounded by $|u| \le \text{STEP\_MM} = 300\ \text{mm}$) and heading adjustment $u_{yaw} = d\theta$ ($\text{mdeg}$, bounded by $|d\theta| \le \text{TURN\_MILLIDEGREES} = 45{,}000\ \text{mdeg}$).
- **Prehension:** `GraspContactCommand`, `ReleaseHeldObjectCommand` acting on native grip apertures ($0$ to $90{,}000\ \mu\text{m}$).
- **Oral Ingestion:** `OralContactCommand` activating the jaw axis ($0$ to $40{,}000\ \mu\text{m}$).
- **Phonation:** `SyllablePCM` driving glottal and supraglottal airway tracts.

**Falsifier:** If any simulator UUID, object class string, global room coordinate $(x_W, y_W)$, or reduced scalar score enters the substrate decision layer, the mount is falsified.

---

### 3.2 Local Eligibility Law

Delayed physical consequences (e.g., metabolic energy absorbed seconds after swallowing, or spatial clearance opened after moving an obstruction) must bind strictly to the pathways that causally participated in the action.

Each physical contact/synapse $e = (i, j)$ maintains a local biochemical/charge eligibility trace $z_e(t)$:
$$\dot{z}_e(t) = -\frac{z_e(t)}{\tau_{elig}} + \alpha_{elig} \cdot \Pi_e(u(t), s(t))$$
where:
- $\tau_{elig} = 1.50\ \text{s}$ ($6$ beats of $250\ \text{ms}$), derived from the metabolic and tactile transit window ($R2$, Yagishita et al., 2014).
- $\Pi_e(u, s) = 1$ if pathway $e$ contributed to the active motor actuation $u(t)$ under sensory context $s(t)$, else $0$.
- $\alpha_{elig} = 1.0$.

When an actual physical consequence arrives at time $t + \delta$ with intensity $\Delta \Phi_{consequence}$ (e.g., real ingested energy $\Delta E_{nutr} > 0$, nociceptive shear stress $\sigma_{noc} > 0$, or vestibular shock), the plastic change on pathway $e$ is:
$$\Delta \ell_e = \eta \cdot z_e(t + \delta) \cdot \Delta \Phi_{consequence}$$
where $\eta$ is the constitutive compliance.

**Invariance:**
- Non-participating pathways have $z_e = 0$; their plastic state remains strictly invariant ($\Delta \ell_e = 0$).
- If no action was executed, $\Pi_e = 0 \implies z_e \to 0$.
- Eligibility is an intrinsic decaying physical variable, not an arbitrary list of timeout callbacks.

**Falsifier:** If an action executed at $t$ receives plastic reinforcement from an outcome at $t + \delta$ when $z_e(t + \delta) = 0$, or if an unexecuted action receives non-zero credit, the implementation is rejected.

---

### 3.3 Predictive Learning Law (Forward Internal Model)

Motor preparation generates a prospective prediction of bodily and sensory return prior to execution:
$$\widehat{s}_{t+\Delta t} = \mathcal{P}_{\theta_t}(s_t, u_t)$$
where $\theta_t$ represents the retained physical synaptic conductances and geometry of the network.

The physical prediction discrepancy vector is:
$$\epsilon_t = s_{t+\Delta t} - \widehat{s}_{t+\Delta t}$$
evaluated strictly channel-by-channel across aligned dimensions with matching physical units:
$$\epsilon_t = \left( \epsilon_{disp}\ [\text{mm}],\ \epsilon_{contact}\ [\text{mN}],\ \epsilon_{kin}\ [\text{mdeg}],\ \epsilon_{ret}\ [\text{flux}],\ \epsilon_{nutr}\ [\mu\text{g}] \right)$$

#### Constitutive Yield & Plasticity Update
In accordance with the ratified material plasticity form (`main.tex:1210-1216`):
$$\varepsilon_e = \frac{x_e - \ell_e}{\ell_e}$$
$$\sigma_e = \frac{\partial E_i}{\partial \varepsilon_e}$$
$$f_e = |\sigma_e| - Y_e \le 0$$
$$\dot{\lambda}_e \ge 0, \quad \dot{\lambda}_e f_e = 0$$
$$\dot{\ell}_e = \dot{\lambda}_e \operatorname{sign}(\sigma_e)$$
where:
- $\varepsilon_e$ is the mechanical/charge strain on synapse/contact $e$.
- $\sigma_e$ is the stress tensor component.
- $Y_e$ is the physical yield stress of the structural connection.
- $\dot{\lambda}_e$ is the plastic multiplier, activated only when stress reaches the yield boundary ($f_e = 0$).
- $\ell_e$ is the plastic reference length (retained structural memory).

Energy expenditure for plastic remodeling is directly debited from the cell metabolic reservoir:
$$\Delta E_{plastic} = \sum_e Y_e \cdot |\dot{\ell}_e| \cdot \Delta t$$

**Falsifier:** If predictions are generated by inspecting the world engine, or if an action succeeds in moving without reducing discrepancy on subsequent trials, or if memory changes without metabolic work ($\Delta E_{plastic} = 0$), the implementation is invalid.

---

### 3.4 Recurrent Persistence Law (Objective Continuity)

An active objective (e.g., resolving a metabolic deficit of $400{,}000\ \mu\text{g}$ under high hunger) must remain active across sensory distractions without relying on artificial string flags (`intent="GET_FOOD"`) or loop-level counters.

#### Multistable Attractor Mechanics
The definitive neuron state vector $N_i$ incorporates local nonlinear potentials:
$$V(x_i) = a x_i^6 - b x_i^4 + c x_i^2$$
with the certified tri-stable parameters (`main.tex:1250-1253`):
$$a > 0, \quad \frac{3}{2}a < b < 3a, \quad c = 2b - 3a$$
producing stable potential minima at $x_i \in \{0, \pm 1\}$.

The total recurrent energy of the assembly is:
$$E(x) = \sum_i V(x_i) - \sum_{i < j} W_{ij} x_i x_j - \sum_i b_i^{drive} x_i$$
where $b_i^{drive}$ is proportional to the unfulfilled interoceptive need (e.g., metabolic deficit ratio $\Delta_{need}$).

#### Damped Gradient Flow & Relaxation
Under unforced conditions, the recurrent state relaxes via dissipative gradient dynamics:
$$\dot{x} = -G \nabla_x E(x), \quad G = G^T \succeq 0$$
$$\dot{E} = -(\nabla_x E)^T G (\nabla_x E) \le 0$$

- **Persistence across Distraction:** A brief sensory transient (e.g., sudden acoustic transient $I_{sound}$) perturbs state $x$, but because $b_i^{drive}$ remains elevated by persistent metabolic deficit, the system's potential well maintains the active basin. The trajectory returns to the attractor once the transient subsides ($R1$, Wang et al., 2013).
- **Repletion Termination:** When food matter is ingested and absorbed, $b_i^{drive} \to 0$. The minimum at $x_i \ne 0$ destabilizes, collapsing the attractor and naturally ending pursuit without an evaluator setting a boolean flag ($R10$, Livneh et al., 2017).

**Falsifier:** If an objective vanishes while metabolic deficit remains $> 0.6$ simply because an auditory event occurred, or if pursuit persists after real satiety ($\text{deficit} = 0$), the persistence law is falsified.

---

### 3.5 Recombination & Provenance Law

Flexible planning requires assembling novel action trajectories that the organism has never executed as a monolithic sequence ($R4$, Addis et al., 2007; $R3$, Pfeiffer & Foster, 2013).

#### Prospective Substrate Dynamics
Prospective recombination occurs in the exact same physical substrate $N_i$ using sub-threshold activation:
$$x^{imagined}(t + \tau) = \mathcal{F}_{recurrent}\left( x^{imagined}(t), \widehat{u} \right)$$
subject to strict **Provenance Isolation**:
$$\text{ProvenanceFlag} = \begin{cases} \text{ACTUAL}, & \text{driven by physical receptor afferents} \\ \text{PROSPECTIVE}, & \text{internally reactivated via sub-threshold dynamics} \end{cases}$$

#### Non-Negotiable Provenance Invariants:
1. **Zero External Efference:** Sub-threshold prospective states ($\text{PROSPECTIVE}$) do NOT generate `PreparePortCommand` calls to the world engine.
2. **Zero Ingestion/Kinematic Side-Effects:** Prospective traversal does not debit world food mass, does not advance live organism tick, and does not alter physical coordinates.
3. **No Omniscient World Rollout:** Prospective projection utilizes only internal model $\mathcal{P}_\theta$, never calling `world.step()` on hidden state.
4. **Relational Component Reuse:** If Guala has experienced:
   - Object contact displacing an obstruction $A \implies \text{clearance}(A)$, and
   - Doorway crossing leading to resource $B \implies \text{food}(B)$,
   the prospective assembly can link $\text{clearance}(A) \to \text{food}(B)$ without ever having executed the joint chain in training.

**Falsifier:** If a prospective rollout modifies `organism.live_organism_tick`, credits physical nutrition micrograms to the body, or requires a hardcoded sequence template, it is strictly rejected.

---

### 3.6 Effector Selection & Competition Law

Multiple feasible affordances (e.g., approach doorway, turn away to clear obstacle, grasp nearby object) compete physically in the premotor field ($R7$, Cisek & Kalaska, 2002).

#### Mutual Inhibition Dynamics
Let $A_k$ represent the activation of motor candidate pathway $k$:
$$\tau_m \dot{A}_k = -A_k + f\left( S_k^{support} - \sum_{j \ne k} \beta_{kj} A_j - \Gamma_{risk} \right)$$
where:
- $S_k^{support}$ is the afferent support driven by the predictive forward model and active objective.
- $\beta_{kj} > 0$ is the lateral inhibitory cross-coupling conductance between mutually exclusive physical actions (e.g., stepping forward vs. turning right).
- $\Gamma_{risk}$ is immediate nociceptive or physical barrier inhibition ($R8$, Chen et al., 2020; $R11$, Mobbs et al., 2007).
- $f(v) = \max(0, \tanh(v))$ is the positive threshold activation.

#### Winner-Take-All Settlement
The competition settles to a single dominant pathway $k^*$ satisfying:
$$A_{k^*} > \Theta_{exec} \quad \text{and} \quad A_j < \Theta_{inhibit} \quad (\forall j \ne k^*)$$
within a bounded settling window $\le 50\ \text{ms}$. The winning pathway couples directly to the actuator command payload.

#### Removal of Distance Veto
The legacy condition $2(v \cdot d) > \|v\|^2$ that vetoed any movement increasing Euclidean distance to the final goal is **retired**. Affordance support $S_k^{support}$ evaluates predicted multi-step outcome support, permitting an initial step away from the goal to maneuver around an impenetrable obstruction ($R15$, Howard et al., 2014).

**Falsifier:** If actions are chosen by an `argmax` over scalar scores, or if an alphabetical/index tie-breaker determines the act, or if a necessary detour is suppressed solely because initial displacement increases target distance, the selection law fails.

---

### 3.7 Lifelong Continuity & Migration Law

The live organism identity (`1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`) at tick 2,628,000+ has lived continuous developmental experience. A new cognitive deployment must preserve lived history without amnesia or retroactive falsification.

#### State Classification & Migration Schema

| Current State Component (`FunctionalOrganism`) | Physical Status | Migration Protocol |
|---|---|---|
| `live_organism_tick`, `identity` | Immutable Core | Preserved byte-exact. |
| `body_axes`, `posture`, `held_object_id` | Physical State | Preserved byte-exact in paired snapshot. |
| `world` (geometry, objects, perches) | Conserved Physical World | Preserved byte-exact in paired snapshot. |
| `acts`, `learned`, `act_totals` (historical counts) | Empirical History | Retained in read-only evidence store for audit and continuity; marked as pre-migrated historical evidence. |
| `N_i` Neuronal Plastic Topology | Plastic Substrate | Initialized from quiescent pre-experience state, conditioned lawfully by replay of validated historical sensory-consequence pairs during preflight rehearsal; zero arbitrary random weights. |
| `last_refusal`, `room_dwell_beats` | Legacy Heuristic Cache | Discarded cleanly at cutover; superseded by native predictive mismatch $\epsilon_t$ and lateral competition. |

#### Quiescent Retained Fractal
Across any sleep/wake boundary or migration cutover, the retained plastic delta is:
$$\mathfrak{F}_i(E) = \operatorname{SparseExact}\left[ \Theta_i^{ret}(q^+) - \Theta_i^{ret}(q^-) \right]$$
where $q^-, q^+$ represent pre- and post-consolidation quiescence states (`main.tex:1220-1223`).

**Falsifier:** If cutover resets live organism tick, erases physical body custody, or synthesizes fake neural weights not derived from genuine lived sensorimotor history, migration is aborted.

---

## 4. Coordinate Frame Consistency & Relational Mapping

In accordance with research requirement $R14$ (Marchette et al., 2014) and acceptance test **C19**:

Cognition must strictly distinguish between **observer self-rotation** and **destination movement**:
$$x_B = R_{WB}^T (x_W - p_{WB})$$
- When Guala rotates in place: $p_{WB}$ is invariant, $R_{WB}$ rotates by $\Delta \theta$. The eye-relative retinal bearing to an object shifts by $-\Delta \theta$, while proprioception records $\Delta \theta_{neck/body} = +\Delta \theta$. The internal forward model predicts this exact shift: $\widehat{\Delta \theta}_{retina} = -\Delta \theta_{proprio}$. The residual error $\epsilon_{bearing} = 0$, confirming the external destination remained stationary.
- When an external object moves while Guala stands still: $\Delta \theta_{proprio} = 0$, but retinal bearing shifts. Here $\epsilon_{bearing} \ne 0$, driving plastic update that the environmental relation has changed.

Under no circumstances is world-frame absolute coordinate $x_W$ leaked to cognition.

---

## 5. Execution Complexity & Resource Discipline

All computation must strictly execute within the hard **250,000 µs** physical interval:

$$W_{interval} = W_{UF}(\text{kernel}) + W_{settle}(N_r, C_r) + W_{pred}(\mathcal{P}) + W_{commit} \le 250{,}000\ \mu\text{s}$$

1. **Active Receptive Horizon ($N_r$):** The number of active neural units evaluated per beat is bounded by sparse topology: $N_r \le 2{,}048$.
2. **Channel Contacts ($C_r$):** Bounded by sparse anatomical fan-out: $C_r \le 8{,}192$.
3. **Settlement Budget:** Damped gradient flow and lateral competition must converge within $\le 50\ \text{ms}$ ($50{,}000\ \mu\text{s}$). If unconverged, the system emits `rest` (quiescent settling), preventing runaway loops.
4. **Zero Full-Memory Rescans:** No $O(N_{total}^2)$ or $O(T_{lifetime})$ history iteration across the tick continuum. All updates are strictly local $O(N_r + C_r)$.

---

## 6. Minimal P1 Falsification Suite

Before progressing to multi-step planning (P2/P3), Stage P1 must execute and pass these minimal physical-law tests:

1. **`test_p1_local_eligibility_coupling`:**
   - Execute motor action $u_1$ at $t_0$. Action $u_2$ remains unexecuted.
   - Deliver real metabolic consequence $\Delta E$ at $t_0 + 1.0\ \text{s}$.
   - **Pass Criteria:** Participating pathway for $u_1$ shows plastic yield $\Delta \ell_1 \ne 0$. Unexecuted pathway $u_2$ shows $\Delta \ell_2 \equiv 0$.
2. **`test_p1_predictive_mismatch_yield`:**
   - Train forward expectation $\mathcal{P}_\theta(s, u_{step}) \to \Delta x = 300\ \text{mm}$.
   - Place rigid obstacle in path so actual return is $\Delta x = 0\ \text{mm}$.
   - **Pass Criteria:** Discrepancy $\epsilon_{disp} = -300\ \text{mm}$ generates stress $\sigma > Y$, causing plastic adaptation. World collision rejection is not the sole signal; prediction mismatch directly updates expectation.
3. **`test_p1_frame_invariance_turn_vs_move` (C19):**
   - Condition A: Rotate body $+45^\circ$ in place. Verify destination relation is preserved without reading world coordinates.
   - Condition B: Object moves $+45^\circ$ while body remains still. Verify destination relation is updated.

---

## 7. Next Actions & Stage Gates

1. **P0 Contract Completion (Current):** Frozen for A1 and Joe independent audit.
2. **Stage P1 Authorization:** Upon A1 concurrence that no heuristics, ML shims, or hidden oracles exist in this contract, implement native P1 constitutive laws.
3. **Strict Non-Interference:** Do not touch the functional body worktree (`/workspaces/guala-functional-body`). All cognitive substrate code develops within `/workspaces/Tao_Financial_Engine`.
