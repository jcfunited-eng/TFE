# GUALA ONE-NEURON PHYSICAL PARAMETER DOSSIER (STAGE P1-A/A14)
**Authoritative Biophysical Provenance, Compartment Dimensions, and Conserved Continuum Laws**

**Date:** 2026-10-01 UTC  
**Governing Specifications:**
- `docs/GUALA_ONE_NEURON_PHYSICAL_TRANSITION_CONTRACT_2026-10-01.md` (§A14)
- `docs/GUALA_P0_LOCAL_LEARNING_A1_CORRECTED_2026-09-27.md` (§§5–10)
- `native/guala_core/src/constitutive.rs` & `native/guala_core/src/coupled_synapse.rs`

---

## 1. Thermodynamic Reference State & Physical Invariants

All biophysical kinetics and electrochemical potentials are evaluated at standard physiological temperature for mammalian neocortex.

| Constant | Symbol | Value | SI Units | Provenance / Authority |
| :--- | :--- | :--- | :--- | :--- |
| **Elementary Charge** | $e_0$ | $1.602\,176\,634 \times 10^{-19}$ | $\text{C}$ | CODATA 2018 (Exact SI definition) |
| **Boltzmann Constant** | $k_B$ | $1.380\,649 \times 10^{-23}$ | $\text{J} \cdot \text{K}^{-1}$ | CODATA 2018 (Exact SI definition) |
| **Avogadro Constant** | $N_A$ | $6.022\,140\,76 \times 10^{23}$ | $\text{mol}^{-1}$ | CODATA 2018 (Exact SI definition) |
| **Physiological Temperature** | $T$ | $310.15$ | $\text{K}$ | $37.0^\circ\text{C}$ Core Neocortical Norm |
| **Thermal Voltage** | $V_T = \frac{k_B T}{e_0}$ | $0.026\,724$ | $\text{V}$ | Derived: $\frac{1.380649 \times 10^{-23} \times 310.15}{1.602176634 \times 10^{-19}}$ ($26.724\,\text{mV}$) |
| **Vacuum Permittivity** | $\varepsilon_0$ | $8.854\,187\,8128 \times 10^{-12}$ | $\text{F} \cdot \text{m}^{-1}$ | CODATA 2018 |

---

## 2. Anatomical Locus & Compartmental Geometry (Prefrontal Column 48 Layer 2/3)

The mounted neuron is instantiated in **Primary Column 48 (Prefrontal Cortical Sheet)**, Layer 2/3 Supragranular Associative Microcircuit.

```
          Extracellular Microdomain (V_out ≈ 0.838 pL)
  ════════════════════════════════════════════════════════════════
    ▲ [Na+]_out = 145 mM       ▲ [Ca2+]_out = 2.0 mM
    │                          │
  ──┴───────────────┬──────────┴───────────────┬──────────────────
    Pore Length ℓ_c │  Pore Area A_c(y)        │ Lipid Bilayer
    5.0 nm          │  0 to 7.854e-17 m²       │ C_mem = 12.57 pF
  ──┬───────────────┴──────────┬───────────────┴──────────────────
    │                          │
    ▼ [K+]_in = 140 mM         ▼ [Na+]_in = 12 mM
  ════════════════════════════════════════════════════════════════
           Intracellular Soma (V_in ≈ 4.189 pL, V_m = -65 mV)
```

### 2.1 Somatic Surface Area and Capacitance
- **Cell Type:** Layer 2/3 regular-spiking pyramidal neuron soma.
- **Somatic Radius:** $r_{\text{soma}} = 10.0\ \mu\text{m} = 1.0 \times 10^{-5}\ \text{m}$ (Hille, 2001; Stuart & Spruston, 1998).
- **Somatic Surface Area:**
  $$A_{\text{mem}} = 4 \pi r_{\text{soma}}^2 = 4 \pi (1.0 \times 10^{-5}\ \text{m})^2 \approx 1.256\,637 \times 10^{-9}\ \text{m}^2 = 1256.64\ \mu\text{m}^2.$$
- **Specific Membrane Capacitance:**
  $$c_m = 0.010\ \text{F} \cdot \text{m}^{-2} = 1.0\ \mu\text{F} \cdot \text{cm}^{-2}$$
  *(Authoritative consensus measurement for biological lipid bilayers: Cole, 1968; Hille, 2001).*
- **Derived Membrane Capacitance:**
  $$C_{\text{mem}} = c_m \cdot A_{\text{mem}} = 0.010\ \text{F/m}^2 \times 1.256\,637 \times 10^{-9}\ \text{m}^2 = 1.256\,637 \times 10^{-11}\ \text{F} \approx 12.57\ \text{pF}.$$
- **Initial Resting Membrane State:**
  - Resting Potential: $V_0 = -65.0\ \text{mV} = -0.0650\ \text{V}$.
  - Initial Net Charge (derived directly from $Q = C_{\text{mem}} V$):
    $$Q_0 = C_{\text{mem}} \cdot V_0 = 1.256\,637 \times 10^{-11}\ \text{F} \times (-0.0650\ \text{V}) = -8.168\,14 \times 10^{-13}\ \text{C} = -0.8168\ \text{pC}.$$
  - Initial Stored Electrostatic Energy:
    $$E_{\text{cap}, 0} = \frac{Q_0^2}{2 C_{\text{mem}}} = \frac{1}{2} C_{\text{mem}} V_0^2 = \frac{1}{2} (1.256\,637 \times 10^{-11}) (-0.0650)^2 \approx 2.6547 \times 10^{-14}\ \text{J} = 26.55\ \text{fJ}.$$

### 2.2 Compartment Volumes and Finite Reservoir Ion Populations
- **Intracellular Volume:**
  $$V_{\text{in}} = \frac{4}{3} \pi r_{\text{soma}}^3 = \frac{4}{3} \pi (1.0 \times 10^{-5}\ \text{m})^3 \approx 4.188\,79 \times 10^{-15}\ \text{m}^3 = 4.1888\ \text{pL}.$$
- **Extracellular Perisomatic Cleft Volume:**
  Neocortical interstitial volume fraction $\alpha \approx 0.20$ (Nicholson & Syková, 1998):
  $$V_{\text{out}} = 0.20 \cdot V_{\text{in}} \approx 8.377\,58 \times 10^{-16}\ \text{m}^3 = 0.8378\ \text{pL}.$$

---

## 3. Finite Chemical Species, Nernst Reversals, and Reservoir Inventory

Reversal potentials are **not** fixed voltage sources; they are dynamic logarithmic functions of finite concentrations:
$$E_c = \frac{k_B T}{z_c e_0} \ln\left(\frac{c_{\text{out}}}{c_{\text{in}}}\right) = \frac{V_T}{z_c} \ln\left(\frac{N_{\text{out}} / V_{\text{out}}}{N_{\text{in}} / V_{\text{in}}}\right).$$

| Species ($c$) | Valence ($z_c$) | Resting $[c]_{\text{out}}$ | Resting $[c]_{\text{in}}$ | Initial $N_{\text{out}}$ (ions) | Initial $N_{\text{in}}$ (ions) | Nernst Potential ($E_c$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Sodium ($\text{Na}^+$)** | $+1$ | $145.0\ \text{mM}$ | $12.0\ \text{mM}$ | $7.315 \times 10^{10}$ | $3.027 \times 10^{10}$ | **$+66.60\ \text{mV}$** |
| **Potassium ($\text{K}^+$)** | $+1$ | $4.0\ \text{mM}$ | $140.0\ \text{mM}$ | $2.018 \times 10^{9}$ | $3.532 \times 10^{11}$ | **$-94.99\ \text{mV}$** |
| **Calcium ($\text{Ca}^{2+}$)** | $+2$ | $2.0\ \text{mM}$ | $100.0\ \text{nM}$ | $1.009 \times 10^{9}$ | $2.523 \times 10^{5}$ | **$+132.33\ \text{mV}$** |
| **Chloride ($\text{Cl}^-$)** | $-1$ | $110.0\ \text{mM}$ | $10.0\ \text{mM}$ | $5.549 \times 10^{10}$ | $2.523 \times 10^{10}$ | **$-64.08\ \text{mV}$** |

### 3.1 Exact Carrier Remainder Settlement (§A14-03)
For each channel species $c$ with ion charge $q_c = z_c e_0$:
1. Continuous charge transported over time $\Delta t$:
   $$J_c = \int_{t_n}^{t_{n+1}} I_c(t)\,dt = \int_{t_n}^{t_{n+1}} g_c(t) (V_m(t) - E_c(t))\,dt.$$
2. Carrier quotient and integer quantization:
   $$\xi_c = r_c + \frac{J_c}{q_c}, \quad n_c = \operatorname{trunc}(\xi_c), \quad r'_c = \xi_c - n_c.$$
3. Identity invariant (must hold to machine precision):
   $$\left| q_c n_c + q_c (r'_c - r_c) - J_c \right| = 0.$$
4. Equal/opposite reservoir mutation:
   $$N_{\text{in}, c}' = N_{\text{in}, c} - n_c, \quad N_{\text{out}, c}' = N_{\text{out}, c} + n_c.$$
5. Net membrane charge and voltage update:
   $$Q'_{i} = Q_i - \sum_c q_c n_c - Q_{\text{active}}, \quad V'_{i} = \frac{Q'_i}{C_{\text{mem}}}.$$

---

## 4. Pore Nanoscale Geometry and Physical Conductance

Conductance is derived from electrolyte conductivity $\sigma_c$ and pore physical dimensions ($A_c, \ell_c$):
$$g_c(y_c) = \frac{\sigma_c A_c(y_c)}{\ell_c}.$$

- **Pore Length (Lipid Bilayer Hydrophobic Core Thickness):**
  $$\ell_c = 5.0\ \text{nm} = 5.0 \times 10^{-9}\ \text{m}$$
  *(Authoritative structural measurement of mammalian lipid bilayer: Hille, 2001; White & Wimley, 1999).*
- **Electrolyte Conductivity in Aqueous Pore:**
  $$\sigma_c = 1.50\ \text{S} \cdot \text{m}^{-1}$$
  *(Standard physiological saline conductivity at 310.15 K: Robinson & Stokes, 1959; Hille, 2001).*
- **Single Channel Pore Radius:** $r_{\text{pore}} = 0.50\ \text{nm} = 5.0 \times 10^{-10}\ \text{m}$.
  $$A_{\text{single}} = \pi r_{\text{pore}}^2 = 7.85398 \times 10^{-19}\ \text{m}^2.$$
- **Single Channel Conductance:**
  $$g_{\text{single}} = \frac{1.50\ \text{S/m} \times 7.85398 \times 10^{-19}\ \text{m}^2}{5.0 \times 10^{-9}\ \text{m}} = 2.3562 \times 10^{-10}\ \text{S} = 235.62\ \text{pS}.$$
- **Channel Population per Sector ($N_{\text{channel}} = 100$):**
  - Maximum Pore Cross-Section: $A_{\text{max}} = 100 \times A_{\text{single}} \approx 7.85398 \times 10^{-17}\ \text{m}^2$.
  - Peak Sector Conductance:
    $$g_{\text{max}} = \frac{\sigma_c A_{\text{max}}}{\ell_c} = 100 \times 235.62\ \text{pS} \approx 23.562\ \text{nS} = 2.3562 \times 10^{-8}\ \text{S}.$$
  - Dynamic Aperture Modulation:
    $$A_c(y_c) = y_c A_{\text{max}} \implies g_c(y_c) = y_c g_{\text{max}}, \quad y_c \in [0, 1].$$

---

## 5. Three-Node Spatial Ring Topology & Paired Phase Constraint Force

The mounted spatial fabric comprises a 3-node spatial ring $a \in \{0, 1, 2\}$ with periodic closure $\phi_3 \equiv \phi_0$.

```
                 Node 0 (ϕ_0, ρ_0)
                     ▲       │
                    /         \
          e_2      /           \  e_0
                  /             ▼
          Node 2 (ϕ_2, ρ_2) ◄─── Node 1 (ϕ_1, ρ_1)
                         e_1
```

- **Ring Spatial Winding:**
  $$w = \frac{1}{2\pi} \sum_{a=0}^{2} \operatorname{wrap}(\phi_{a+1} - \phi_a) \in \mathbb{Z}.$$
- **Directed Edge Phase Differences:**
  $$\theta_{01} = \phi_1 - \phi_0 - \frac{2\pi \tau_{qp}}{3}, \quad \theta_{12} = \phi_2 - \phi_1 - \frac{2\pi \tau_{qp}}{3}, \quad \theta_{20} = \phi_0 - \phi_2 - \frac{2\pi \tau_{qp}}{3}.$$
- **Fact-Constraint Energy:**
  $$E_{qp}^{DSF} = -\kappa_{qp} \sum_{a \to b} \cos(\theta_{ab}).$$
- **Paired Invariant Forces (Zero Net Internal Torque):**
  $$F_a = -\frac{\partial E_{ab}}{\partial \phi_a} = +\kappa_{qp} \sin(\theta_{ab}), \qquad F_b = -\frac{\partial E_{ab}}{\partial \phi_b} = -\kappa_{qp} \sin(\theta_{ab}).$$
- **Physical Coupling Scale $\kappa$:**
  Anchor to thermal molecular scale $k_B T \approx 4.282 \times 10^{-21}\ \text{J}$.
  $$\kappa_0 = 10 \cdot k_B T = 4.282 \times 10^{-20}\ \text{J}.$$

---

## 6. Physical Gate Dynamics & Reciprocal Reaction Potential ($U_c$)

Gate state $y_c \in [0, 1]$ represents the fraction of active channel opening.

- **Gate Potential Function:**
  $$U_c(y) = \frac{1}{2} k_{\text{barrier}} (y - y_{\text{rest}})^2 - q_c^{\text{gate}} V_m y - \sum_{a=0}^2 \Lambda_{ca} y \cos(\phi_a - \phi^*_{ca}) - \mu_c y.$$
- **Physical Gate Parameters:**
  - Rest aperture: $y_{\text{rest}} = 0.05$ (5% baseline open probability).
  - Barrier elastic stiffness: $k_{\text{barrier}} = 50 \cdot k_B T \approx 2.141 \times 10^{-19}\ \text{J}$.
  - Equivalent gating dipole charge: $q_c^{\text{gate}} = 4.0 \cdot e_0 \approx 6.4087 \times 10^{-19}\ \text{C}$ (S4 voltage-sensor charge: Armstrong, 1981; Bezanilla, 2000).
  - Phase-gate coupling constant: $\Lambda_{ca} = 5 \cdot k_B T \approx 2.141 \times 10^{-20}\ \text{J}$.
  - Gate hydrodynamic friction: $\zeta_c = 1.0 \times 10^{-21}\ \text{J} \cdot \text{s}$.
- **Equations of Motion:**
  $$\zeta_c \dot{y}_c = -k_{\text{barrier}}(y_c - y_{\text{rest}}) + q_c^{\text{gate}} V_m + \sum_{a=0}^2 \Lambda_{ca} \cos(\phi_a - \phi^*_{ca}) + \mu_c.$$
- **Reciprocal Force onto Spatial Phase Node $a$:**
  $$-\frac{\partial U_c}{\partial \phi_a} = -\Lambda_{ca} y_c \sin(\phi_a - \phi^*_{ca}).$$

---

## 7. Column 48 Layer 2/3 Receiving Compartment Integration

Rather than injecting dimensionless scalars into $v_{23}$ array slots, the prefrontal microcircuit receives physical ionic current:

1. **Current Summation:**
   $$I_{\text{tot}} = I_{\text{Na}} + I_{\text{K}} + I_{\text{Ca}} + I_{\text{Cl}} = \sum_c g_c(y_c) (V_{23} - E_c).$$
2. **Capacitive Membrane Update:**
   $$C_{\text{mem}} \frac{dV_{23}}{dt} = -I_{\text{tot}} + I_{\text{synaptic}}.$$
3. **Discrete Trit Efferent Generation:**
   Somatic action potential generation occurs via physiological threshold voltage:
   $$\text{Trit Output} = \begin{cases}
   +1 & \text{if } V_{23} \ge V_{\text{thresh}} = -45.0\ \text{mV} \quad (\text{Action Potential Firing}), \\
   0 & \text{if } -75.0\ \text{mV} < V_{23} < -45.0\ \text{mV} \quad (\text{Subthreshold Integration}), \\
   -1 & \text{if } V_{23} \le -75.0\ \text{mV} \quad (\text{Hyperpolarized Invariant Refusal}).
   \end{cases}$$
4. **No Dimensionless Multipliers:** Zero $10^9$ factors, zero arbitrary sigmoid scalers, zero manual node-block overrides.

---

## 8. Summary of Mandatory Parameter Provenance

```
                     MANDATORY PHYSICAL PARAMETER MATRIX
┌───────────────────────┬────────────┬─────────────────────────────┬──────────────────────────────┐
│ Parameter             │ Symbol     │ Value & Units               │ Authority / Citation         │
├───────────────────────┼────────────┼─────────────────────────────┼──────────────────────────────┤
│ Somatic Capacitance   │ C_mem      │ 12.566 pF                   │ Hille (2001), Cole (1968)    │
│ Specific Capacitance  │ c_m        │ 0.010 F/m²                  │ Biological lipid bilayer     │
│ Intracellular Volume  │ V_in       │ 4.189 pL                    │ Pyramidal soma r = 10 µm     │
│ Extracellular Volume  │ V_out      │ 0.838 pL                    │ Nicholson & Syková (1998)    │
│ Pore Length           │ ℓ_c        │ 5.0 nm                      │ Hydrophobic core thickness   │
│ Electrolyte Cond.     │ σ_c        │ 1.50 S/m                    │ Saline at 310.15 K           │
│ Peak Sector Conduct.  │ g_max      │ 23.56 nS                    │ 100 channels per sector      │
│ Sodium Reversal       │ E_Na       │ +66.60 mV                   │ Nernst: 145 mM / 12 mM       │
│ Potassium Reversal    │ E_K        │ -94.99 mV                   │ Nernst: 4 mM / 140 mM        │
│ Calcium Reversal      │ E_Ca       │ +132.33 mV                  │ Nernst: 2 mM / 100 nM        │
│ Phase Ring Coupling   │ κ_0        │ 4.282e-20 J (10 k_B T)      │ Macromolecular H-bond        │
│ Gating Charge         │ q_gate     │ 6.4087e-19 C (4 e_0)        │ Armstrong (1981) S4 domain   │
│ Spiking Threshold     │ V_thresh   │ -45.0 mV                    │ Regular spiking neocortical  │
└───────────────────────┴────────────┴─────────────────────────────┴──────────────────────────────┘
```
