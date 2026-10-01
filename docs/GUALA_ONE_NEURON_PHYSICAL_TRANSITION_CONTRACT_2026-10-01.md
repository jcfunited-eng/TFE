# Guala: Canonical One-Neuron Phase-Gate Physical Transition Contract

**Execution Stage:** Stage P1-A / Neuromorphic Substrate Integration  
**Author:** G1 / Chief Systems Architect & Senior DARPA Neuromorphic Systems Engineer  
**Date:** 2026-10-01 UTC  
**Target Specifications:** §§5–10 of `docs/GUALA_P0_LOCAL_LEARNING_A1_CORRECTED_2026-09-27.md` and Astra Twelfth-Pass Architecture Handoff (`docs/A1_ARCLOOM_TWELFTH_PASS_CORRECTION_2026-10-01.md:183-223`).  
**Status:** Canonical Executable Contract for One Reached Neuron in Primary Column 48 (Layer 2/3).

---

## 1. Mandatory Architecture Honesty Gate

1. **Requested Architecture:**
   Mounting the canonical One-Neuron Phase $\to$ Gate $\to$ Conductance Physical Transition Operator (`NeuronPhaseGateTransition`) into Primary Column 48 Layer 2/3 of `ModularSubstrate64D` (`native/guala_core/src/cortical_column.rs`) under canonical neuron physics (§§5–10 of `docs/GUALA_P0_LOCAL_LEARNING_A1_CORRECTED_2026-09-27.md` and `docs/A1_ARCLOOM_TWELFTH_PASS_CORRECTION_2026-10-01.md:183-223`).
   Causal transduction sequence:
   $$\text{complete typed UF result} + S_{UF} \to \text{exact positional MathLoom constraints } \tau(q,p) \to \text{persistent } \Psi = (\rho, \phi) \text{ & Krimelack winding } K \to \text{gate coordinate } y_c \in [0, 1] \text{ under physical potential } U_c \to \text{pore conductance } g_c = \sigma_c A_c(y_c) / \ell_c \to \text{ionic current } I_c = g_c (V_m - E_c) \to \text{exact carrier custody } |q_c n_c + q_c(r' - r) - J_c| < 10^{-25} \to \text{pore current injection into Column 48 Layer 2/3} \to \text{inter-column plastic propagation}.$$

2. **Current Code Reality:**
   Commit `d089718c4` implemented and mathematically verified `NeuronPhaseGateTransition` in `native/guala_core/src/constitutive.rs` with 7 passing unit tests (57/57 native tests passing). In `native/guala_core/src/cortical_column.rs`, Column 48 does not yet mount this transition operator instance, and `ModularSubstrate64D.step()` retains fail-closed refusal containment on `continuous_joint_field_present` to preserve Capability A10 boundary containment and pass `test_mathloom_a10_boundary.py` without mutating state.

3. **Conflict with Requested Architecture:**
   **Yes**. The operator exists in `constitutive.rs` but is not yet mounted into the Column 48 microcircuit in `cortical_column.rs`, and the formal executable contract document for this physical transition has not yet been committed to `docs/`.

4. **What Exact Mechanism or Files Will Not Be Extended:**
   - Will NOT extend `.take(N)` digit truncation, scalar scorecards, harmonic series shortcuts, or ML approximations.
   - Will NOT extend direct field-to-motor shortcuts (e.g. bypassing the laminar microcircuit to zero motor stride).
   - Canonical L0–L4 kernel remains frozen and untouched.
   - Will NOT modify `tests/test_mathloom_a10_boundary.py` or prematurely declare full-field Capability A10 certified without independent audit.

5. **The Single Exact Next Item:**
   Mount `NeuronPhaseGateTransition` on Column 48 Layer 2/3 in `native/guala_core/src/cortical_column.rs`, expose `step_mounted_canonical_neuron` and state inspection in Rust and PyO3, deliver this governing executable contract document (`docs/GUALA_ONE_NEURON_PHYSICAL_TRANSITION_CONTRACT_2026-10-01.md`), and verify with native and Python causal tests.

6. **Evaluation Level:**
   Full continuous field ($D_k, M_k, R_{\text{rev},k}, U^*_k, C_k, P_k, B_k$) and $S_{UF}$.

7. **Structure Loss in Reduced Model:**
   None — evaluating all 8 continuous field dimensions without digit truncation or lossy dimensional reduction.

---

## 2. Producer's Complete Field & Positional Participation (§5)

### 2.1 Complete Structural Field Ingress
The upstream DSF L0–L4 kernel delivers the exact joint structural tensor at each macroscopic step $k$:
$$\mathcal{F} = \left( D_k, M_k, R_{\text{rev},k}, U^*_k, C_k, P_k, B_k \right) \in \mathbb{R}^7, \quad S_{UF} \in \mathbb{R}$$
where:
- $D_k$: Structural displacement tensor.
- $M_k$: Structural momentum / directional velocity.
- $R_{\text{rev},k}$: Structural reversal risk / kill-switch boundary indicator.
- $U^*_k$: Structural uncertainty field.
- $C_k$: Cohesion field / manifold compactness.
- $P_k$: Somatic pressure manifold.
- $B_k$: Somatic breathing basin capacity.
- $S_{UF}$: Universal stability metric ($S_{UF} \le 0$ indicates fatal structural collapse).

### 2.2 Exact MathLoom Rational Balanced-Ternary Decomposition
Every binary64 floating-point field component $x \in \mathcal{F} \cup \{S_{UF}\}$ is decomposed via MathLoom into exact integer numerator $N$ and power-of-two denominator $D = 2^E$, represented as signed balanced-ternary digit streams:
$$N = \sum_{p=0}^{P-1} \tau_p^{(N)} 3^p, \quad D = \sum_{q=0}^{Q-1} \tau_q^{(D)} 3^q, \quad \tau_p^{(N)}, \tau_q^{(D)} \in \{-1, 0, 1\}$$
- **Zero Truncation Rule:** Arbitrary truncation (such as `.take(N)`) is strictly prohibited. Every non-zero positional trit across numerator and denominator participates in the physical phase gradient force.
- **Positional Significance vs. Energy:** The positional place value $3^p$ is algebraic significance, not energy. Coupling energy is governed strictly by the material constant $\kappa_{\text{base}}$.

---

## 3. Persistent Phase, Topological Winding & Gate Dynamics (§§5–6)

### 3.1 Cosine Potential Well & Gradient Force
For each participating balanced-ternary digit $\tau_{qp} \in \{-1, 0, 1\}$, the physical phase constraint potential energy on the reached neuron is:
$$E_{qp}(\phi) = -\kappa_{\text{base}} \cos\left( \phi - \frac{2\pi \tau_{qp}}{3} \right)$$
The corresponding gradient torque/force acting on the continuous phase coordinate $\phi$ is:
$$F_\phi = -\sum_{qp} \frac{\partial E_{qp}}{\partial \phi} = -\sum_{qp} \kappa_{\text{base}} \sin\left( \phi - \frac{2\pi \tau_{qp}}{3} \right)$$

### 3.2 Persistent Phase Integration & Krimelack Winding ($K$)
The phase angle $\phi$ evolves under viscous damping $\gamma$ in continuous time:
$$\dot{\phi} = \frac{1}{\gamma} F_\phi$$
Over a discrete simulation sub-interval $\Delta t$:
$$\Delta \phi = \left(\frac{F_\phi}{\gamma}\right) \Delta t, \quad \phi_{\text{raw}} = \phi_n + \Delta \phi$$
The phase is strictly mapped into the fundamental circle $[-\pi, \pi)$ with topological winding count $K \in \mathbb{Z}$:
$$\phi_{n+1} = \operatorname{wrap}_{[-\pi, \pi)}(\phi_{\text{raw}}), \quad K_{n+1} = K_n + \Delta K$$
- **Persistence Invariant:** Both $\phi$ and $K$ are retained in persistent state memory across cycles; they are never reset at cycle boundaries.

### 3.3 Dimensionless Gate Coordinate Relaxation ($y_c$)
The physical channel gate coordinate $y_c \in [0.0, 1.0]$ relaxes mechanically toward its phase-dictated equilibrium aperture $y^*(\phi)$:
$$y^*(\phi) = \frac{1}{2}\left(1 + \cos\phi\right) \in [0.0, 1.0]$$
The gate relaxes with characteristic mechanical relaxation time constant $\tau_g$:
$$\dot{y}_c = \frac{1}{\tau_g}\left(y^*(\phi) - y_c\right)$$
Discretized with unconditional stability:
$$y_{c, n+1} = \operatorname{clamp}_{[0, 1]}\left( y_{c, n} + \frac{\Delta t}{\tau_g} \left( y^*(\phi_{n+1}) - y_{c, n} \right) \right)$$

---

## 4. Material Pore Conductance, Ionic Current & Charge Custody (§§5–6)

### 4.1 Pore Aperture & Sourced Material Conductance
The reached neuron's physical channel pore possesses:
- **Maximum Open Aperture Area:** $A_{\text{max}} = 2.0 \times 10^{-17}\ \text{m}^2$ (equivalent circular radius $r \approx 2.52\ \text{nm}$).
- **Pore Length (Membrane Thickness):** $\ell_c = 5.0 \times 10^{-9}\ \text{m}$ ($5.0\ \text{nm}$).
- **Electrolyte Specific Conductivity:** $\sigma_c = 1.5\ \text{S/m}$ (physiological saline / Ringer solution).

Instantaneous pore aperture area and material conductance evaluate as:
$$A_c(y_c) = A_{\text{max}} \cdot y_c \quad [\text{m}^2]$$
$$g_c = \frac{\sigma_c A_c(y_c)}{\ell_c} = \frac{\sigma_c A_{\text{max}}}{\ell_c} y_c \quad [\text{S}]$$
- Peak open pore conductance:
  $$g_{\text{max}} = \frac{1.5 \cdot 2.0 \times 10^{-17}}{5.0 \times 10^{-9}} = 6.0 \times 10^{-9}\ \text{S} = 6.0\ \text{nS}$$
- Unit validation: $[\text{S/m}] \cdot [\text{m}^2] / [\text{m}] = \text{S}$. Zero dimensional inconsistency.

### 4.2 Nernst Driving Potential & Ionic Pore Current
The membrane voltage $V_m$ is determined by instantaneous stored capacitive charge:
$$V_m = \frac{Q_m}{C_{\text{mem}}}$$
where $C_{\text{mem}} = 1.0 \times 10^{-12}\ \text{F}$ ($1.0\ \text{pF}$ cell capacitance).  
The reversal potential for the excitatory channel is $E_c = +0.050\ \text{V}$ ($+50\ \text{mV}$ sodium-like equilibrium).  
The instantaneous ionic current through the pore is:
$$I_c = g_c \left( V_m - E_c \right) \quad [\text{A}]$$
Over time step $\Delta t$, continuous transported charge is:
$$J_c = I_c \Delta t \quad [\text{C}]$$

### 4.3 Exact Carrier Settlement & Remainder Custody
Individual charge carriers have discrete valence $z_c = +1$, corresponding to signed elementary charge:
$$q_c = z_c \cdot e_0 = 1.602176634 \times 10^{-19}\ \text{C}$$
The non-integer continuous transport $J_c$ is resolved with signed sub-carrier remainder custody:
$$z_c = r_{c, n} + \frac{J_c}{q_c}$$
$$n_c = \operatorname{trunc}(z_c) \in \mathbb{Z} \quad (\text{discrete integer carrier count})$$
$$r_{c, n+1} = z_c - n_c \in (-1.0, 1.0) \quad (\text{exact sub-carrier fractional remainder})$$
- **Exact Remainder Identity:**
  $$\left| q_c n_c + q_c (r_{c, n+1} - r_{c, n}) - J_c \right| < 10^{-25}\ \text{C}$$
  Subcarrier history is never rounded away or lost to floating-point truncation.

### 4.4 Thermodynamic Invariance ($\dot{E} \le 0$)
The electrical energy stored in the postsynaptic membrane capacitor is:
$$E_{\text{cap}} = \frac{1}{2} C_{\text{mem}} V_m^2 = \frac{Q_m^2}{2 C_{\text{mem}}} \quad [\text{J}]$$
Under zero external drive ($\tau_{qp} = 0$), capacitor discharge through the pore satisfies:
$$\Delta E_{\text{cap}} \le 0 \quad (\dot{E} \le 0)$$
guaranteeing strict physical energy dissipation without synthetic amplification.

---

## 5. Column 48 Cortical Microcircuit Mounting & Synaptic Propagation (§§5, 7)

### 5.1 Anatomical Location & Laminar Ingress
- **Primary Column:** Column 48 (Prefrontal / Structural Invariant Sheet, Column ID 48 of 64).
- **Target Laminar Layer:** Layer 2/3 Supragranular Associative Lattice (`v_23[0]`).
- **Current Injection:** The physical pore current $I_c$ [A] enters the Layer 2/3 pyramidal dendrite:
  $$I_{\text{inj}} = I_c \cdot 10^9 \quad [\text{nA}]$$
  $$v_{23}[0]_{n+1} = v_{23}[0]_n + I_{\text{inj}}$$

### 5.2 Microcircuit Laminar Flow & Inter-Column Plasticity
Upon injection of $I_{\text{inj}}$:
1. Column 48 executes vertical laminar flow: predictive reafference cancellation in Layer 4, lateral competition in Layer 2/3, infragranular motor pyramidal output in Layer 5, and efference copy in Layer 6.
2. Settled Layer 2/3 and Layer 5 excitations propagate along directional fasciculi:
   - Fasciculus $48 \to \text{Motor Cortex}$ (Columns 40..47)
   - Fasciculus $48 \to \text{Somatosensory Sheet}$ (Columns 16..23)
3. Physical contact stress $\sigma = g_{\text{target}} - g_{\text{plastic}}$ undergoes irreversible von Mises yield deformation if and only if $|\sigma| > Y$.

---

## 6. Sourced Material & Anatomical Parameter Table

| Symbol | Description | Physical SI Value | Provenance & Rationale |
|---|---|---|---|
| $\kappa_{\text{base}}$ | Base phase constraint coupling | $1.0 \times 10^{-18}\ \text{J/rad}$ | Thermal energy scale ($\approx 240\ k_B T$ at $300\ \text{K}$) |
| $\gamma$ | Phase viscous damping coefficient | $1.0 \times 10^{-15}\ \text{J}\cdot\text{s/rad}^2$ | Viscous torque damping in lipid bilayer |
| $\sigma_c$ | Electrolyte specific conductivity | $1.5\ \text{S/m}$ | Standard physiological extracellular Ringer fluid |
| $A_{\text{max}}$ | Maximum pore aperture area | $2.0 \times 10^{-17}\ \text{m}^2$ | Circular pore radius $r \approx 2.52\ \text{nm}$ |
| $\ell_c$ | Pore channel path length | $5.0 \times 10^{-9}\ \text{m}$ | Neuronal cell lipid bilayer membrane thickness |
| $\tau_g$ | Gate mechanical relaxation time | $1.0 \times 10^{-3}\ \text{s}$ ($1.0\ \text{ms}$) | Sub-millisecond conformational channel gating |
| $E_c$ | Reversal / Nernst potential | $+0.050\ \text{V}$ ($+50\ \text{mV}$) | Excitatory $\text{Na}^+$ reversal potential |
| $C_{\text{mem}}$ | Postsynaptic membrane capacitance | $1.0 \times 10^{-12}\ \text{F}$ ($1.0\ \text{pF}$) | Standard single-spine membrane patch capacitance |
| $z_c$ | Carrier charge valence | $+1$ | Monovalent cation ($\text{Na}^+ / \text{K}^+$) |
| $e_0$ | Elementary charge magnitude | $1.602176634 \times 10^{-19}\ \text{C}$ | Exact CODATA 2018 fundamental constant |
| $N_{\text{res}}$ | Initial carrier reservoir capacity | $1.0 \times 10^8$ carriers | Bounded finite intracellular ionic pool |

---

## 7. Fail-Closed Lossless Binary State Continuation

The complete physical state of the mounted neuron is serialized to a 148-byte binary record:
- **Magic Bytes:** `b"GUALA_NG"` (8 bytes)
- **Schema Version:** `1` (`0x00000001` LE, 4 bytes)
- **Config Block:** $\kappa_{\text{base}}, \gamma, \sigma_c, A_{\text{max}}, \ell_c, \tau_g, E_c$ (f64 LE), $z_c$ (i32 LE) (60 bytes)
- **State Block:** $\phi, \rho$ (f64 LE), $K$ (i64 LE), $y_c$ (f64 LE) (32 bytes)
- **Carrier Block:** $Q_m, C_{\text{mem}}$ (f64 LE), $N_{\text{res}}$ (u64 LE), $r_c$ (f64 LE) (32 bytes)
- **Integrity:** CRC-32 IEEE 802.3 checksum across payload (4 bytes)
- **Total Serialized Size:** Exactly 148 bytes.

Restoration requires bit-exact CRC validation. Any corrupted or truncated payload fails closed without altering the recipient state. Identical input sequences starting from restored states yield bit-identical trajectories.
