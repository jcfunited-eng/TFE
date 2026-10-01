# GUALA ONE-NEURON PHYSICAL PARAMETER DOSSIER (STAGE P1-A/A15 RECONCILIATION)
**Authoritative Biophysical Provenance, Artificial-Material Specifications, and Conserved Continuum Laws**

**Date:** 2026-10-01 UTC  
**Revision:** A15-P1 Consolidated Reconciliation  
**Governing Contract:**
- `docs/GUALA_ONE_NEURON_PHYSICAL_TRANSITION_CONTRACT_2026-10-01.md` (§§A14, A15)
- `docs/GUALA_P0_LOCAL_LEARNING_A1_CORRECTED_2026-09-27.md` (§§5–10)
- `collaborative_todo.md` (A15 fifteenth-pass audit review, line 29426)

---

## 1. Thermodynamic Reference State & Physical Constants

All biophysical kinetics and electrochemical potentials are evaluated at standard physiological temperature for mammalian neocortex using exact CODATA 2018 SI definitions.

| Constant | Symbol | Value | SI Units | Classification | Source / Authority |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Elementary Charge** | $e_0$ | $1.602\,176\,634 \times 10^{-19}$ | $\text{C}$ | **[EXACT SI]** | CODATA 2018 |
| **Boltzmann Constant** | $k_B$ | $1.380\,649 \times 10^{-23}$ | $\text{J} \cdot \text{K}^{-1}$ | **[EXACT SI]** | CODATA 2018 |
| **Avogadro Constant** | $N_A$ | $6.022\,140\,76 \times 10^{23}$ | $\text{mol}^{-1}$ | **[EXACT SI]** | CODATA 2018 |
| **Physiological Temperature** | $T$ | $310.15$ | $\text{K}$ | **[STANDARD]** | $37.0^\circ\text{C}$ Core Neocortical Norm |
| **Thermal Voltage** | $V_T = \frac{k_B T}{e_0}$ | $0.026\,726\,659$ | $\text{V}$ | **[DERIVED]** | $\frac{1.380649 \times 10^{-23} \times 310.15}{1.602176634 \times 10^{-19}}$ ($26.7267\,\text{mV}$) |
| **Vacuum Permittivity** | $\varepsilon_0$ | $8.854\,187\,8128 \times 10^{-12}$ | $\text{F} \cdot \text{m}^{-1}$ | **[EXACT SI]** | CODATA 2018 |

---

## 2. Anatomical Geometry & Reconciled Extracellular Volume Fraction (A15-01)

The single-neuron model represents a **Prefrontal Column 48 Layer 2/3 Pyramidal Soma** embedded in a finite neocortical interstitial microdomain.

```
          Extracellular Microdomain (V_out = 1.0472 pL, α = 0.20)
  ════════════════════════════════════════════════════════════════
    ▲ [Na+]_out = 145 mM       ▲ [Ca2+]_out = 2.0 mM
    │                          │
  ──┴───────────────┬──────────┴───────────────┬──────────────────
    Pore Length ℓ_c │  Pore Area A_c(y)        │ Lipid Bilayer
    5.0 nm          │  0 to 7.854e-17 m²       │ C_mem = 12.566 pF
  ──┬───────────────┴──────────┬───────────────┴──────────────────
    │                          │
    ▼ [K+]_in = 140 mM         ▼ [Na+]_in = 12 mM
  ════════════════════════════════════════════════════════════════
           Intracellular Soma (V_in = 4.1888 pL, V_0 = -65 mV)
```

### 2.1 Somatic Dimensions & Bilayer Capacitance
- **Soma Morphology [PROPOSED - ARTIFICIAL MATERIAL]:** Idealized spherical soma of radius $r_{\text{soma}} = 10.0\,\mu\text{m} = 1.0 \times 10^{-5}\,\text{m}$ (typical mammalian Layer 2/3 pyramidal soma: Stuart & Spruston, 1998).
- **Somatic Surface Area [DERIVED]:**
  $$A_{\text{mem}} = 4 \pi r_{\text{soma}}^2 = 4 \pi (1.0 \times 10^{-5}\,\text{m})^2 \approx 1.256\,637\,0614 \times 10^{-9}\,\text{m}^2 = 1256.64\,\mu\text{m}^2.$$
- **Specific Membrane Capacitance [MEASURED - BIOLOGICAL]:**
  $$c_m = 0.010\,\text{F} \cdot \text{m}^{-2} = 1.0\,\mu\text{F} \cdot \text{cm}^{-2}$$
  *(Consensus measurement for biological lipid bilayers: Cole, 1968; Hille, 2001).*
- **Derived Membrane Capacitance [DERIVED]:**
  $$C_{\text{mem}} = c_m \cdot A_{\text{mem}} = 0.010\,\text{F/m}^2 \times 1.256\,637\,0614 \times 10^{-9}\,\text{m}^2 = 1.256\,637\,0614 \times 10^{-11}\,\text{F} \approx 12.566\,\text{pF}.$$
- **Initial Electrostatic State at Declared Initial Potential $V_0 = -65.0\,\text{mV}$ [DERIVED]:**
  $$Q_{\text{cap}, 0} = C_{\text{mem}} \cdot V_0 = 1.256\,637\,0614 \times 10^{-11}\,\text{F} \times (-0.0650\,\text{V}) = -8.168\,140\,899 \times 10^{-13}\,\text{C} = -0.816814\,\text{pC}.$$
  $$E_{\text{cap}, 0} = \frac{1}{2} C_{\text{mem}} V_0^2 = \frac{1}{2} (1.256\,637\,0614 \times 10^{-11}) (-0.0650)^2 \approx 2.654\,645\,792 \times 10^{-14}\,\text{J} = 26.546\,\text{fJ}.$$

### 2.2 Reconciled Extracellular Volume Fraction (Nicholson & Phillips, 1981)
- **Intracellular Somatic Volume [DERIVED]:**
  $$V_{\text{in}} = \frac{4}{3} \pi r_{\text{soma}}^3 = \frac{4}{3} \pi (1.0 \times 10^{-5}\,\text{m})^3 \approx 4.188\,790\,2048 \times 10^{-15}\,\text{m}^3 = 4.18879\,\text{pL}.$$
- **Extracellular Volume Fraction Formulation [MEASURED / DERIVED]:**
  By biological definition, the tissue extracellular volume fraction is $\alpha = \frac{V_{\text{out}}}{V_{\text{in}} + V_{\text{out}}} = 0.20$ (Nicholson & Phillips, 1981; Nicholson & Syková, 1998).
  The associated microdomain volume is therefore:
  $$V_{\text{out}} = \frac{\alpha}{1 - \alpha} V_{\text{in}} = \frac{0.20}{0.80} V_{\text{in}} = \frac{1}{4} V_{\text{in}} = 1.047\,197\,5512 \times 10^{-15}\,\text{m}^3 = 1.04720\,\text{pL}.$$
  *(Total model microdomain volume $V_{\text{tot}} = V_{\text{in}} + V_{\text{out}} = 5.235\,987\,756 \times 10^{-15}\,\text{m}^3 = 5.23599\,\text{pL}$.)*

---

## 3. Finite Chemical Species, Reconciled Populations, and Initial Charge Inventory (A15-01, A15-02)

### 3.1 Deterministic Integer Genesis Convention & Dynamic Nernst Reversals
Concentrations represent the thermodynamic limit $c = N / (V N_A)$. Deterministic integer populations are initialized as $N = \operatorname{round}(c \cdot V \cdot N_A)$. Reversal potentials derive dynamically from the admitted integer counts:
$$E_c = \frac{V_T}{z_c} \ln\left(\frac{N_{\text{out}, c} / V_{\text{out}}}{N_{\text{in}, c} / V_{\text{in}}}\right).$$

| Species ($c$) | Valence ($z_c$) | Resting $[c]_{\text{out}}$ | Resting $[c]_{\text{in}}$ | Admitted Integer $N_{\text{out}}$ | Admitted Integer $N_{\text{in}}$ | Dynamic Nernst Potential ($E_c$) | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Sodium ($\text{Na}^+$)** | $+1$ | $145.0\,\text{mM}$ | $12.0\,\text{mM}$ | $91\,442\,380\,324$ | $30\,270\,581\,073$ | **$+66.5982\,\text{mV}$** | Measured conc. / Derived counts |
| **Potassium ($\text{K}^+$)** | $+1$ | $4.0\,\text{mM}$ | $140.0\,\text{mM}$ | $2\,522\,548\,423$ | $353\,156\,779\,183$ | **$-95.0226\,\text{mV}$** | Measured conc. / Derived counts |
| **Calcium ($\text{Ca}^{2+}$)** | $+2$ | $2.0\,\text{mM}$ | $100.0\,\text{nM}$ | $1\,261\,274\,211$ | $252\,255$ | **$+132.3436\,\text{mV}$** | Unbuffered free pool model |
| **Chloride ($\text{Cl}^-$)** | $-1$ | $110.0\,\text{mM}$ | $10.0\,\text{mM}$ | $69\,370\,081\,625$ | $25\,225\,484\,227$ | **$-64.0877\,\text{mV}$** | Measured conc. / Derived counts |

### 3.2 Closed Charge Accounting & Fixed Macromolecular Countercharge (A15-02)
Mobile ions in solution do not exist in an electrical vacuum. Intracellular and extracellular bulk electrolytes satisfy Debye electroneutrality in the bulk ($< 1\,\text{nm}$ Debye length), with net capacitive charge $Q_{\text{cap}}$ distributed strictly across the bilayer:

1. **Total Intracellular Mobile Ion Charge [DERIVED]:**
   $$Q_{\text{mobile, in}} = e_0 \sum_{c} z_c N_{\text{in}, c} = e_0 (N_{\text{in,Na}} + N_{\text{in,K}} + 2 N_{\text{in,Ca}} - N_{\text{in,Cl}}) \approx +5.739\,034\,8434 \times 10^{-8}\,\text{C} \approx +57.39\,\text{nC}.$$
2. **Total Extracellular Mobile Ion Charge [DERIVED]:**
   $$Q_{\text{mobile, out}} = e_0 \sum_{c} z_c N_{\text{out}, c} = e_0 (N_{\text{out,Na}} + N_{\text{out,K}} + 2 N_{\text{out,Ca}} - N_{\text{out,Cl}}) \approx +4.331\,244\,759 \times 10^{-9}\,\text{C} \approx +4.331\,\text{nC}.$$
3. **Immobile Macromolecular Countercharge [PROPOSED - ARTIFICIAL MATERIAL]:**
   Intracellular impermeant proteins, nucleic acids, and organic anions provide fixed negative charge:
   $$Q_{\text{fixed, in}} = Q_{\text{cap}, 0} - Q_{\text{mobile, in}} = -8.168\,141 \times 10^{-13}\,\text{C} - 5.739\,035 \times 10^{-8}\,\text{C} \approx -5.739\,116\,525 \times 10^{-8}\,\text{C}.$$
   Extracellular matrix proteoglycans provide fixed countercharge:
   $$Q_{\text{fixed, out}} = -Q_{\text{cap}, 0} - Q_{\text{mobile, out}} = +8.168\,141 \times 10^{-13}\,\text{C} - 4.331\,245 \times 10^{-9}\,\text{C} \approx -4.330\,428 \times 10^{-9}\,\text{C}.$$
4. **Conservation Invariant:**
   Net global charge $Q_{\text{total}} = (Q_{\text{mobile, in}} + Q_{\text{fixed, in}}) + (Q_{\text{mobile, out}} + Q_{\text{fixed, out}}) \equiv 0.0\,\text{C}$.
   Net capacitive charge across dielectric bilayer: $Q_{\text{cap}} = Q_{\text{mobile, in}} + Q_{\text{fixed, in}} = -0.816814\,\text{pC} \implies V_m = Q_{\text{cap}} / C_{\text{mem}} = -65.0\,\text{mV}$.

### 3.3 Exact Carrier Custody & Floating-Point Residual Distinction (A15-02)
For outward-positive ionic current $I_c = g_c (V_m - E_c)$ and integrated transport $J_c = \int_{t_n}^{t_{n+1}} I_c dt$:
- Dimensionless quotient: $\xi_c = r_c + \frac{J_c}{q_c}$, with carrier charge $q_c = z_c e_0$.
- Integer transported ions: $n_c = \operatorname{trunc}(\xi_c)$, with updated subcarrier remainder $r'_c = \xi_c - n_c \in (-1, 1)$.
- Exact Reservoir Population Update:
  $$N_{\text{in}, c}' = N_{\text{in}, c} - n_c, \quad N_{\text{out}, c}' = N_{\text{out}, c} + n_c.$$
- **Arithmetic Invariant:**
  In exact mathematical algebra, $q_c n_c + q_c (r'_c - r_c) \equiv J_c$.
  In binary64 floating-point evaluation, roundoff residual is tracked explicitly:
  $$\varepsilon_{\text{roundoff}} = \left| q_c n_c + q_c (r'_c - r_c) - J_c \right| < 10^{-20}\,\text{C}.$$

---

## 4. Nanoscale Pore Geometry & Cylindrical Conductance Model (A15-03)

### 4.1 Cylindrical Pore Approximation vs Biological Protein Selectivity
- **Model Classification:** [PROPOSED - ARTIFICIAL MATERIAL CONTINUUM MODEL]. This is a macroscopic cylindrical continuum pore model used to establish physical dimensions and SI scaling; it does not claim microscopic atomistic equivalence to biological potassium or sodium selectivity filters.
- **Pore Nanoscale Geometry [PROPOSED]:**
  - Length (dielectric bilayer core): $\ell_c = 5.0\,\text{nm} = 5.0 \times 10^{-9}\,\text{m}$ (White & Wimley, 1999).
  - Pore radius: $a = 0.50\,\text{nm} = 5.0 \times 10^{-10}\,\text{m} \implies A_{\text{single}} = \pi a^2 = 7.85398 \times 10^{-19}\,\text{m}^2$.
- **Saline Bulk Conductivity [MEASURED]:** $\sigma = 1.50\,\text{S/m}$ at $310.15\,\text{K}$ (Robinson & Stokes, 1959).
- **Access Resistance Formulation [DERIVED - Sahu & Zwolak, 2018]:**
  Accounting for convergent access resistance at both pore mouths in a homogeneous continuum:
  $$R_{\text{access, total}} = 2 \times R_{\text{access, side}} = 2 \times \frac{1}{4 \sigma a} = \frac{1}{2 \sigma a} = \frac{1}{2 (1.50) (5.0 \times 10^{-10})} \approx 6.6667 \times 10^8\,\Omega.$$
  $$R_{\text{pore, internal}} = \frac{\ell_c}{\sigma \pi a^2} = \frac{5.0 \times 10^{-9}}{(1.50) (7.85398 \times 10^{-19})} \approx 4.2441 \times 10^9\,\Omega.$$
  $$R_{\text{total}} = R_{\text{pore, internal}} + R_{\text{access, total}} \approx 4.9108 \times 10^9\,\Omega \implies g_{\text{single}} = \frac{1}{R_{\text{total}}} \approx 2.0363 \times 10^{-10}\,\text{S} = 203.63\,\text{pS}.$$
  *(Without access resistance, internal pore conductance alone is $g_{\text{pore}} = 235.62\,\text{pS}$.)*
- **Sector Channel Density [PROPOSED - ARTIFICIAL MATERIAL]:**
  $N_{\text{channels}} = 100$ channels per sector $\implies$ peak sector conductance:
  $$g_{\text{max}} = 100 \times g_{\text{single}} \approx 20.363\,\text{nS} \quad (\text{or } 23.562\,\text{nS for internal-only boundary}).$$

---

## 5. Coupled Gate Mechanics, Gating Current, and Energy Closure (A15-04)

### 5.1 Definition of Gate Coordinate $y_c$
- **Aperture Meaning [PROPOSED]:** $y_c \in [0, 1]$ represents the **continuous fraction of open pore area** for sector channel ensemble $c$ ($A_c(y_c) = y_c A_{\text{max}}$).
- **Sector Conductance:** $g_c(y_c) = y_c g_{\text{max}}$.

### 5.2 Physical Gate Energy & Coordinate Constraints
- **Gate Energy Function $U_c(y)$ [PROPOSED - ARTIFICIAL MATERIAL]:**
  $$U_c(y_c) = \frac{1}{2} k_{\text{barrier}} (y_c - y_{\text{rest}})^2 - q_c^{\text{gate}} V_m y_c - \sum_{a=0}^2 \Lambda_{ca} y_c \cos(\phi_a - \phi^*_{ca}) - \mu_c y_c \quad [\text{Joules}].$$
- **Boundary Confinement Law [A15-04]:**
  To guarantee $0 \le y_c \le 1$ without unphysical after-step clipping, gate evolution is governed by subdifferential inclusion on the admissible interval $K = [0, 1]$:
  $$0 \in \zeta_c \dot{y}_c + \partial_{y_c} U_c(y_c) + N_{[0, 1]}(y_c),$$
  where $N_{[0, 1]}(y_c)$ is the normal cone of outward constraint forces at the boundaries $y_c = 0$ and $y_c = 1$.
- **Parameter Provenance:**
  - $y_{\text{rest}} = 0.05$ [PROPOSED baseline unforced rest].
  - Barrier stiffness: $k_{\text{barrier}} = 50\,k_B T \approx 2.141 \times 10^{-19}\,\text{J}$ [PROPOSED].
  - Hydrodynamic drag: $\zeta_c = 1.0 \times 10^{-21}\,\text{J} \cdot \text{s} \implies$ relaxation time $\tau_{\text{gate}} = \zeta_c / k_{\text{barrier}} \approx 4.671\,\text{ms}$ [PROPOSED].
  - Phase coupling: $\Lambda_{ca} = 5\,k_B T \approx 2.141 \times 10^{-20}\,\text{J}$ [PROPOSED].
  - Chemical bias: $\mu_c = 0.0\,\text{J}$ [PROPOSED unshifted reference].
  - Gate displacement charge: $q_c^{\text{gate}} = 4.0\,e_0 \approx 6.4087 \times 10^{-19}\,\text{C}$ per channel [PROPOSED electromechanical dipole].

### 5.3 Gating Charge Displacement & Coupled Membrane Equation
Voltage-sensitive gating physically moves sensor charge through the membrane dielectric, creating gating displacement current:
$$Q_g(y) = \sum_c N_c^{\text{channel}} q_c^{\text{gate}} y_c.$$
The total free charge on the membrane capacitor is $Q_f = C_{\text{mem}} V_m + Q_g(y)$.
The coupled differential equation of motion for membrane potential is:
$$C_{\text{mem}} \dot{V}_m = -\sum_c I_c(V_m, y_c) + I_{\text{syn}} + I_{\text{active, in}} - \dot{Q}_g,$$
where $\dot{Q}_g = \sum_c N_c^{\text{channel}} q_c^{\text{gate}} \dot{y}_c$.
- **Declared Initial State vs Resting Equilibrium:**
  $V_0 = -65.0\,\text{mV}$ is the **declared initial potential**. Under arbitrary open fractions $y_c$, net ionic current is non-zero ($\sum I_c \ne 0$). Maintenance of steady state requires active metabolic pump current $I_{\text{active, in}} = \sum_c I_c(V_0, y_0)$, accounting for metabolic ATP work: $\dot{W}_{\text{metabolic}} = I_{\text{active}} \Delta \mu_{\text{ATP}} / e_0$.

---

## 6. Typed Structural Field Coupling & Spatial Ring Topology (A15-05)

### 6.1 Preservation of Typed Fact Incidence
The 3-node spatial ring ($a \in \{0, 1, 2\}$, cyclic $a = 3 \equiv 0$) is a local spatial winding primitive. It does **not** collapse the 7 structural field coordinates onto an untyped scalar drive.

For each canonical UF/DSF fact $\tau_{qp} \in \{-1, 0, 1\}$ characterized by:
- Structural coordinate family: $q \in \{D, M, R_{\text{rev}}, U^*, C, P, B\}$
- Rational ternary positional significance: $p \in \mathbb{Z}$
- Numerator/denominator provenance: $(n_q, d_q)$
- Locality and source timestamp $t_k$:

The interaction energy is evaluated over the spatial ring:
$$E_{qp}^{DSF} = -\kappa_{qp} \sum_{a=0}^{2} \cos\left(\phi_{a+1} - \phi_a - \frac{2\pi \tau_{qp}}{3}\right).$$
- **Paired Invariant Forces (Zero Internal Net Torque):**
  $$F_a = -\frac{\partial E_{ab}}{\partial \phi_a} = +\kappa_{qp} \sin(\theta_{ab}), \qquad F_b = -\frac{\partial E_{ab}}{\partial \phi_b} = -\kappa_{qp} \sin(\theta_{ab}).$$
- **Amplitude and Phase Dynamics [P0 / A14]:**
  $$\zeta_{\rho, a} \dot{\rho}_a = -\frac{\partial E}{\partial \rho_a} + P_a^{\text{ext}}, \qquad \zeta_{\phi, a} \rho_a \dot{\phi}_a = -\frac{\partial E}{\partial \phi_a} + \tau_a^{\text{ext}}.$$
- **Coupling Energy Scale [PROPOSED]:** $\kappa_0 = 10\,k_B T \approx 4.282 \times 10^{-20}\,\text{J}$ (macromolecular hydrogen bond energy scale).

### 6.2 Contact Mechanics & Material Plasticity Return Map
Spine contact conductance is governed by genuine mechanical displacement $x$ and rate-independent plastic yield:
- Contact elastic stiffness: $K = E_{\text{mod}} A_{\text{ref}} / L_{\text{ref}}$ (Units: Joules [J]).
- Strain: $\epsilon = x / \ell_n - 1$, Elastic stress force: $\Sigma = K \epsilon$.
- Yield condition: $f = |\Sigma| - Y \le 0$.
- Admissible plastic return:
  $$\ell_{n+1} = \begin{cases}
  \ell_n & \text{if } |\Sigma_{\text{tr}}| \le Y, \\
  x / (1 + s Y / K) & \text{if } |\Sigma_{\text{tr}}| > Y, \quad s = \operatorname{sign}(\Sigma_{\text{tr}}).
  \end{cases}$$
- Plastic dissipation: $D_{\text{pl}} = \frac{1}{2} K \left[ \epsilon_{\text{tr}}^2 - (Y/K)^2 \right] \ge 0$.

---

## 7. Column 48 Layer 2/3 Receiving Compartment Integration (A15-06)

### 7.1 Elimination of Semantic Trit Thresholds
- **Defect Removed:** The previous authored mapping "$-75\,\text{mV} \implies \text{Invariant Refusal}$" is completely withdrawn. Membrane potential does not possess semantic cognitive authority.
- **Physical Electrical Inter-Column Contacts:**
  Prefrontal Column 48 Layer 2/3 communicates with adjacent cortical columns strictly through physical contact conductances $g_{ij}$:
  $$I_{ij} = g_{ij} (V_i - V_j), \quad J_{ij} = \int_{t_n}^{t_{n+1}} I_{ij} dt, \quad \Delta Q_i = -J_{ij}, \quad \Delta Q_j = +J_{ij}.$$
  Total charge across participating columns is conserved: $\sum_k \Delta Q_k = 0$.
- **Efferent Observation:** Voltage $V_{23}$ may be recorded by downstream observers, but motor decoding is driven by settled pyramidal L5 physical conductances, not arbitrary software threshold comparators.

---

## 8. Consolidated Master Parameter Matrix (A15-P1)

```
                    CONSOLIDATED PHYSICAL PARAMETER MATRIX
┌─────────────────────────┬──────────────┬─────────────────────────────┬──────────────────────────────┬────────────────────────┐
│ Parameter               │ Symbol       │ Value & Units               │ Classification               │ Authority / Citation   │
├─────────────────────────┼──────────────┼─────────────────────────────┼──────────────────────────────┼────────────────────────┤
│ Specific Capacitance    │ c_m          │ 0.010 F/m² (1.0 µF/cm²)     │ [MEASURED - BIOLOGICAL]      │ Cole (1968), Hille     │
│ Soma Radius             │ r_soma       │ 10.0 µm                     │ [PROPOSED - ARTIFICIAL MAT.] │ L2/3 Pyramidal Soma    │
│ Somatic Area            │ A_mem        │ 1.2566e-9 m²                │ [DERIVED - CONTINUUM]        │ 4 * π * r_soma²        │
│ Membrane Capacitance    │ C_mem        │ 12.566 pF                   │ [DERIVED - CONTINUUM]        │ c_m * A_mem            │
│ Initial Net Charge      │ Q_cap,0      │ -0.8168 pC                  │ [DERIVED - CONTINUUM]        │ C_mem * V_0 (-65 mV)   │
│ Initial Stored Energy   │ E_cap,0      │ 26.55 fJ                    │ [DERIVED - CONTINUUM]        │ 1/2 * C_mem * V_0²     │
│ Intracellular Volume    │ V_in         │ 4.1888 pL                   │ [DERIVED - CONTINUUM]        │ 4/3 * π * r_soma³      │
│ Extracellular Vol. Frac.│ α            │ 0.20                        │ [MEASURED - BIOLOGICAL]      │ Nicholson & Phillips   │
│ Extracellular Volume    │ V_out        │ 1.0472 pL                   │ [DERIVED - RECONCILED]       │ α / (1 - α) * V_in     │
│ Pore Length             │ ℓ_c          │ 5.0 nm                      │ [MEASURED - BIOLOGICAL]      │ White & Wimley (1999)  │
│ Saline Conductivity     │ σ            │ 1.50 S/m                    │ [MEASURED - BIOLOGICAL]      │ Robinson & Stokes 1959 │
│ Pore Radius             │ a            │ 0.50 nm                     │ [PROPOSED - ARTIFICIAL MAT.] │ Cylindrical pore model │
│ Single Channel Conduct. │ g_single     │ 203.6 pS (with access R)    │ [DERIVED - Sahu & Zwolak]    │ 1 / (R_pore + R_access)│
│ Sector Peak Conductance │ g_max        │ 20.36 nS                    │ [PROPOSED - ARTIFICIAL MAT.] │ 100 channels / sector  │
│ Sodium Reversal         │ E_Na         │ +66.60 mV                   │ [DERIVED - NERNST]           │ 145 mM / 12 mM         │
│ Potassium Reversal      │ E_K          │ -95.02 mV                   │ [DERIVED - NERNST]           │ 4 mM / 140 mM          │
│ Calcium Reversal        │ E_Ca         │ +132.34 mV                  │ [DERIVED - NERNST]           │ 2 mM / 100 nM free     │
│ Chloride Reversal       │ E_Cl         │ -64.09 mV                   │ [DERIVED - NERNST]           │ 110 mM / 10 mM         │
│ Fixed Intracellular Q   │ Q_fixed,in   │ -57.391 nC                  │ [DERIVED - DEBYE NEUTRALITY] │ Q_cap,0 - Q_mobile,in  │
│ Fixed Extracellular Q   │ Q_fixed,out  │ -4.330 nC                   │ [DERIVED - DEBYE NEUTRALITY] │ -Q_cap,0 - Q_mobile,out│
│ Gating Sensor Charge    │ q_gate       │ 6.4087e-19 C (4 e_0)        │ [PROPOSED - ARTIFICIAL MAT.] │ Electromechanical S4   │
│ Barrier Stiffness       │ k_barrier    │ 2.141e-19 J (50 k_B T)      │ [PROPOSED - ARTIFICIAL MAT.] │ Harmonic gate potential│
│ Gate Relaxation Time    │ τ_gate       │ 4.671 ms                    │ [DERIVED - CONTINUUM]        │ ζ_gate / k_barrier     │
│ Phase Ring Coupling     │ κ_0          │ 4.282e-20 J (10 k_B T)      │ [PROPOSED - ARTIFICIAL MAT.] │ Macromolecular H-bond  │
└─────────────────────────┴──────────────┴─────────────────────────────┴──────────────────────────────┴────────────────────────┘
```
