# GUALA ONE-NEURON MATERIAL AND ANATOMY BINDING SPECIFICATION
**Concrete Physical Couplings, Species Transport Laws, and Canonical State Representation**

**Date:** 2026-10-01 UTC  
**Governing Authority:** §9 of `docs/GUALA_ONE_NEURON_PHYSICAL_PARAMETER_DOSSIER_2026-10-01.md` and §A14 of `docs/GUALA_ONE_NEURON_PHYSICAL_TRANSITION_CONTRACT_2026-10-01.md`  
**Target Anatomical Locus:** Primary Column 48 (Prefrontal Sheet), Layer 2/3 Supragranular Associative Microcircuit

---

## 1. Typed Reached Fabric Binding

### 1.1 Node Topology and Directed Spatial Ring
- **Node Ensemble:** $\mathcal{V} = \{v_0, v_1, v_2\}$, $M = 3$ nodes arranged in a cyclic spatial ring.
- **Oriented Edges:** $e_0 = (v_0 \to v_1)$, $e_1 = (v_1 \to v_2)$, $e_2 = (v_2 \to v_0)$.
- **Spatial Winding Number Invariant:**
  $$w = \frac{1}{2\pi} \sum_{a=0}^2 \operatorname{wrap}(\phi_{a+1} - \phi_a) \in \mathbb{Z}, \quad \phi_3 \equiv \phi_0.$$

### 1.2 Typed Incidence Matrix ($E_j$)
Every canonical structural field fact is preserved without dimensional reduction. For coordinate $q \in \{0: D, 1: M, 2: R_{\text{rev}}, 3: U^*, 4: C, 5: P, 6: B\}$, positional balanced ternary exponent $p \in \{-52, \dots, 52\}$, and digit $\tau_{qp} \in \{-1, 0, +1\}$:

- **Coordinate Torus Angle:** $\theta_q^* = \frac{2\pi q}{7} \in [0, 2\pi)$.
- **Directed Edge Difference Angle:**
  $$\theta_{ab, qp} = \phi_b - \phi_a - \frac{2\pi \tau_{qp}}{3} - \theta_q^*.$$
- **Coupling Stiffness with Positional Spectral Decay:**
  $$\kappa_{qp} = \kappa_0 \cdot 3^{-|p|/16}, \quad \kappa_0 = 10 \cdot k_B T \approx 4.282 \times 10^{-20}\,\text{J}.$$
- **Fact-Constraint Energy:**
  $$E_{\text{DSF}} = -\sum_{q=0}^6 \sum_p \kappa_{qp} \sum_{a \to b} \cos(\theta_{ab, qp}).$$
- **Paired Constraint Forces (Newton's Third Law / Zero Net Torque):**
  $$-\frac{\partial E_{ab, qp}}{\partial \phi_a} = +\kappa_{qp} \sin(\theta_{ab, qp}), \qquad -\frac{\partial E_{ab, qp}}{\partial \phi_b} = -\kappa_{qp} \sin(\theta_{ab, qp}).$$

### 1.3 Amplitude Dynamics and Damping
Complex amplitude $\psi_a = \sqrt{\rho_a} e^{i \phi_a}$:
- **Amplitude Rest Energy:** $U_\rho(\rho_a) = \frac{1}{2} k_\rho (\rho_a - \rho_0)^2$, with $\rho_0 = 1.0\,\text{J/m}^3$ and $k_\rho = 100\,k_B T / \rho_0^2$.
- **Damping Coefficients:** $\zeta_\rho = 1.0 \times 10^{-21}\,\text{J}\cdot\text{s/m}^3$, $\zeta_\phi = 1.0 \times 10^{-21}\,\text{J}\cdot\text{s}$.
- **Coupled Differential Equations:**
  $$\zeta_\rho \dot{\rho}_a = -k_\rho(\rho_a - \rho_0), \qquad \zeta_\phi \rho_a \dot{\phi}_a = -\frac{\partial E_{\text{DSF}}}{\partial \phi_a} - \sum_c \frac{\partial U_c}{\partial \phi_a}.$$
- **Initial Genesis State:** $\rho_a(0) = 1.0$, $\phi_0(0) = 0.0$, $\phi_1(0) = \frac{2\pi}{3}$, $\phi_2(0) = \frac{4\pi}{3}$ ($w = 1$).

---

## 2. Gate & Material Authority (Species Transport and Access Conductance)

### 2.1 Sector Allocation and Aperture-Access Conductance
The soma contains 4 ion channel sectors with access-resistance corrected continuum conductance:

$$g_{\text{single}, c}(y_c) = \frac{y_c}{R_{p0} + R_{a0} \sqrt{y_c}}, \quad G_c(y_c) = N_c \cdot g_{\text{single}, c}(y_c),$$
where $R_{p0} = \frac{\ell_c}{\sigma \pi a_0^2} = 4.2441 \times 10^9\,\Omega$, $R_{a0} = \frac{1}{2 \sigma a_0} = 6.6667 \times 10^8\,\Omega$ ($\ell_c = 5.0\,\text{nm}, a_0 = 0.50\,\text{nm}, \sigma = 1.50\,\text{S/m}$).

| Sector ($c$) | Species | Channel Count ($N_c$) | Resting Aperture ($y_{\text{rest}}$) | Single Pore $g(1)$ | Peak Sector $G_{\text{max}}$ | Single Pore $g(0.05)$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **0: Fast Excitatory** | $\text{Na}^+$ | $100$ | $0.05$ | $203.63\,\text{pS}$ | $20.363\,\text{nS}$ | $11.381\,\text{pS}$ |
| **1: Delayed Rectifier** | $\text{K}^+$ | $100$ | $0.05$ | $203.63\,\text{pS}$ | $20.363\,\text{nS}$ | $11.381\,\text{pS}$ |
| **2: Calcium / Plateau** | $\text{Ca}^{2+}$ | $20$ | $0.02$ | $203.63\,\text{pS}$ | $4.073\,\text{nS}$ | $4.552\,\text{pS}$ |
| **3: Passive Leak** | $\text{Cl}^-$ | $50$ | $0.10$ (fixed) | $203.63\,\text{pS}$ | $10.182\,\text{nS}$ | $22.762\,\text{pS}$ |

### 2.2 Gate Potential and Reciprocal Phase Coupling
For active sectors $c \in \{\text{Na}, \text{K}, \text{Ca}\}$:
- **Sector Gating Energy:**
  $$U_c(y_c) = N_c \left[ \frac{1}{2} k_{\text{barrier}} (y_c - y_{\text{rest}, c})^2 - q_c^{\text{gate}} V_m y_c - \sum_{a=0}^2 \Lambda_{ca} y_c \cos(\phi_a - \phi^*_{ca}) - \mu_c y_c \right].$$
- **Phase Offsets & Coupling Matrix:**
  - $\text{Na}^+$ coupled to Node 0: $\phi^*_{\text{Na}, 0} = 0.0$, $\Lambda_{\text{Na}, 0} = 5\,k_B T \approx 2.141 \times 10^{-20}\,\text{J}$, $\Lambda_{\text{Na}, 1} = \Lambda_{\text{Na}, 2} = 0$.
  - $\text{K}^+$ coupled to Node 1: $\phi^*_{\text{K}, 1} = \frac{2\pi}{3}$, $\Lambda_{\text{K}, 1} = 5\,k_B T$, $\Lambda_{\text{K}, 0} = \Lambda_{\text{K}, 2} = 0$.
  - $\text{Ca}^{2+}$ coupled to Node 2: $\phi^*_{\text{Ca}, 2} = \frac{4\pi}{3}$, $\Lambda_{\text{Ca}, 2} = 5\,k_B T$, $\Lambda_{\text{Ca}, 0} = \Lambda_{\text{Ca}, 1} = 0$.
- **Gating Dipole Charge:**
  $q_{\text{Na}}^{\text{gate}} = 4.0\,e_0$, $q_{\text{K}}^{\text{gate}} = 3.0\,e_0$, $q_{\text{Ca}}^{\text{gate}} = 2.0\,e_0$.
- **Coordinate Boundary Confinement Law:**
  $$0 \in N_c \zeta_c \dot{y}_c + \frac{\partial U_c}{\partial y_c} + N_{[0, 1]}(y_c).$$
- **Reciprocal Phase Force:**
  $$-\frac{\partial U_c}{\partial \phi_a} = -N_c \Lambda_{ca} y_c \sin(\phi_a - \phi^*_{ca}).$$

---

## 3. Retained Physical Contact Mechanics

The physical bridge between soma and dendritic arbor is governed by rate-independent material plasticity:

### 3.1 Dimensions and Elastic Stiffness
- Reference length: $L_{\text{ref}} = 1.0\,\mu\text{m} = 1.0 \times 10^{-6}\,\text{m}$.
- Reference cross-section: $r_{\text{spine}} = 0.10\,\mu\text{m} \implies A_{\text{ref}} = \pi r_{\text{spine}}^2 = 3.14159 \times 10^{-14}\,\text{m}^2$.
- Young's modulus: $E_{\text{mod}} = 1.0 \times 10^5\,\text{Pa}$ (Gittes et al., 1993).
- **Strain-Energy Stiffness [J]:**
  $$K_\epsilon = E_{\text{mod}} A_{\text{ref}} L_{\text{ref}} = (1.0 \times 10^5) (3.14159 \times 10^{-14}) (1.0 \times 10^{-6}) = 3.14159 \times 10^{-15}\,\text{J}.$$
- **Axial Spring Constant [N/m]:**
  $$k_{\text{axial}} = \frac{E_{\text{mod}} A_{\text{ref}}}{L_{\text{ref}}} = 3.14159 \times 10^{-3}\,\text{N/m}.$$
- **Yield Threshold Energy:**
  $$Y = K_\epsilon \cdot \epsilon_{\text{yield}} = 3.14159 \times 10^{-15} \times 0.05 = 1.5708 \times 10^{-16}\,\text{J} = 157.08\,\text{aJ}.$$

### 3.2 Plastic Yield Return Map and Conductance Bridge
For instantaneous displacement $x > 0$:
- Trial strain: $\epsilon_{\text{tr}} = x / \ell_n - 1$, Trial stress: $\Sigma_{\text{tr}} = K_\epsilon \epsilon_{\text{tr}}$.
- Yield condition: $f = |\Sigma_{\text{tr}}| - Y \le 0$.
- Plastic return:
  $$\ell_{n+1} = \begin{cases}
  \ell_n & \text{if } |\Sigma_{\text{tr}}| \le Y, \\
  x / (1 + s Y / K_\epsilon) & \text{if } |\Sigma_{\text{tr}}| > Y, \quad s = \operatorname{sign}(\Sigma_{\text{tr}}).
  \end{cases}$$
- Plastic dissipation: $D_{\text{pl}} = \frac{1}{2} K_\epsilon \left[ \epsilon_{\text{tr}}^2 - (Y / K_\epsilon)^2 \right] \ge 0$.
- Retained electrical conductance:
  $$g_{\text{contact}}(\ell) = \sigma_{\text{cytoplasm}} \frac{A_{\text{ref}}}{\ell}, \quad \sigma_{\text{cytoplasm}} = 0.50\,\text{S/m} \implies g_{\text{contact}}(L_{\text{ref}}) = 15.708\,\text{nS}.$$

---

## 4. Receiving and Chemical Boundary Closure

### 4.1 Compartment Charge and Capacitance
- Somatic capacitance: $C_{\text{mem}} = 12.56637\,\text{pF}$.
- Intracellular volume: $V_{\text{in}} = 4.18879\,\text{pL}$.
- Extracellular microdomain volume: $V_{\text{out}} = 1.04720\,\text{pL}$ ($\alpha = 0.20$).
- Fixed countercharges (guaranteeing Debye electroneutrality):
  $$Q_{\text{fixed, in}} = -57.391165\,\text{nC}, \quad Q_{\text{fixed, out}} = -4.330428\,\text{nC}.$$
- Free capacitive charge partition:
  $$Q_g(y) = \sum_c N_c q_c^{\text{gate}} y_c, \quad Q_f = C_{\text{mem}} V_m + Q_g(y).$$
  Reference integer net charge $Z_f = -5\,098\,073 \implies Q_{f, 0} = Z_f \cdot e_0 \approx -8.16814 \times 10^{-13}\,\text{C}$, yielding nominal $V_0 \approx -65.0000057\,\text{mV}$.

### 4.2 Dynamic Membrane Equation with Gating Current
$$C_{\text{mem}} \dot{V}_m = -\sum_{c \in \{\text{Na}, \text{K}, \text{Ca}, \text{Cl}\}} G_c(y_c) (V_m - E_c) - \sum_{j} g_{ij} (V_m - V_j) + I_{\text{active, in}} - \dot{Q}_g,$$
where $\dot{Q}_g = \sum_c N_c q_c^{\text{gate}} \dot{y}_c$, and $E_c = \frac{V_T}{z_c} \ln\left(\frac{N_{\text{out}, c} / V_{\text{out}}}{N_{\text{in}, c} / V_{\text{in}}}\right)$.

### 4.3 Stoichiometric Active Metabolic Pump
To maintain long-term concentration gradients against passive dissipation without artificial leak cancellation:
- Na/K-ATPase pump rate: $I_{\text{pump}}$ transfers $3\,\text{Na}^+$ outward and $2\,\text{K}^+$ inward per cycle:
  $$\Delta N_{\text{in, Na}} = -3 \cdot n_{\text{pump}}, \quad \Delta N_{\text{out, Na}} = +3 \cdot n_{\text{pump}},$$
  $$\Delta N_{\text{in, K}} = +2 \cdot n_{\text{pump}}, \quad \Delta N_{\text{out, K}} = -2 \cdot n_{\text{pump}}.$$
- Net pump current: $I_{\text{active, in}} = -e_0 \cdot \dot{n}_{\text{pump}}$.
- Metabolic chemical work consumed: $\dot{W}_{\text{ATP}} = \dot{n}_{\text{pump}} \Delta \mu_{\text{ATP}}$, with $\Delta \mu_{\text{ATP}} = 20\,k_B T \approx 8.56 \times 10^{-20}\,\text{J/cycle}$.

---

## 5. Executable Representation & Binary Checkpoint Schema

The canonical binary state record is **384 bytes**, strictly 8-byte aligned, validated by CRC-32:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ARCLOOM CANONICAL NEURON RECORD (384 B)                │
├─────────────────────┬────────┬────────┬─────────────────────────────────────┤
│ Field               │ Offset │ Length │ Description                         │
├─────────────────────┼────────┼────────┼─────────────────────────────────────┤
│ magic               │ 0      │ 8 B    │ b"GUA_P1N1"                         │
│ schema_version      │ 8      │ 4 B    │ u32 = 1                             │
│ flags               │ 12     │ 4 B    │ u32 = 0                             │
│ rho [3]             │ 16     │ 24 B   │ 3 × f64 amplitude state             │
│ phi [3]             │ 40     │ 24 B   │ 3 × f64 spatial ring phase [rad]    │
│ winding             │ 64     │ 8 B    │ i64 topological spatial winding     │
│ gate_y [4]          │ 72     │ 32 B   │ 4 × f64 sector aperture fractions   │
│ gate_ydot [4]       │ 104    │ 32 B   │ 4 × f64 aperture velocities         │
│ q_free              │ 136    │ 8 B    │ f64 net free capacitive charge [C]  │
│ c_mem               │ 144    │ 8 B    │ f64 somatic capacitance [F]         │
│ v_membrane          │ 152    │ 8 B    │ f64 membrane potential [V]          │
│ q_gating            │ 160    │ 8 B    │ f64 gating displacement charge [C]  │
│ n_in [4]            │ 168    │ 32 B   │ 4 × u64 intracellular ion counts    │
│ n_out [4]           │ 200    │ 32 B   │ 4 × u64 extracellular ion counts    │
│ r_carriers [4]      │ 232    │ 32 B   │ 4 × f64 fractional carrier rem.     │
│ spine_length        │ 264    │ 8 B    │ f64 current plastic length ℓ [m]    │
│ spine_disp_x        │ 272    │ 8 B    │ f64 instantaneous mechanical x [m]  │
│ k_epsilon           │ 280    │ 8 B    │ f64 strain-energy stiffness [J]     │
│ yield_threshold     │ 288    │ 8 B    │ f64 plastic yield energy Y [J]      │
│ cum_dissipated      │ 296    │ 8 B    │ f64 cumulative plastic work D_pl [J]│
│ w_metabolic         │ 304    │ 8 B    │ f64 cumulative ATP work [J]         │
│ q_joule             │ 312    │ 8 B    │ f64 cumulative thermal heat [J]     │
│ q_fixed_in          │ 320    │ 8 B    │ f64 fixed intracellular charge [C]  │
│ q_fixed_out         │ 328    │ 8 B    │ f64 fixed extracellular charge [C]  │
│ reserved            │ 336    │ 40 B   │ 5 × f64 reserved for contact fanout │
│ crc32               │ 376    │ 4 B    │ u32 CRC-32 checksum of bytes 0..375 │
│ pad                 │ 380    │ 4 B    │ 4 bytes zero padding to 384 B       │
└─────────────────────┴────────┴────────┴─────────────────────────────────────┘
```

### 5.1 Verification and Exact Serialization Properties
1. **Machine-Precision Conservation:** Every whole carrier crossing the membrane transfers from $N_{\text{in}}$ to $N_{\text{out}}$ with exact integer custody and remainder update ($|q_c n_c + q_c(r'_c - r_c) - J_c| = 0$).
2. **Cold Restart Invariant:** $\operatorname{decode}(\operatorname{encode}(S)) \equiv S$ bit-for-bit. Restored states advance identically under subsequent inputs.
3. **Fail-Closed Gate:** An unmounted state or invalid CRC refuses transition before mutating any substrate, motor, or checkpoint state.
