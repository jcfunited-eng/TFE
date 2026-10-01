# Guala one-neuron physical parameter dossier — A15-P1 corrected binding contract

Date: 2026-10-01 UTC. Revision: A1 direct correction of G1 commit 3297966f8.

**Status: corrected proposal, not a mounted or fully parameterized neuron.**
This document closes the identifiable algebra/accounting defects together.
It does not ratify unspecified material coefficients, authorize a new numerical
approximation, unlock full-field step_cycle, or close A10/A11.

Governing references:

- [A14 transition contract](GUALA_ONE_NEURON_PHYSICAL_TRANSITION_CONTRACT_2026-10-01.md), especially A14-01 through A14-05.
- [Corrected P0 physical law](GUALA_P0_LOCAL_LEARNING_A1_CORRECTED_2026-09-27.md), §§5–10.
- Shared ledger: A15-P1 review and this revision's correction receipt.

## 1. Scope, provenance and parameter ownership

Requested: one coherent physical connection from unchanged joint DSF through
typed phase constraints, gates and conserved current to a receiving compartment.
No new cognition, biological anatomy reconstruction, or semantic voltage rule.

Evidence: document equations and arithmetic only. Native code, tests and the
standalone archive remain frozen. This is a **reduced lumped-compartment
proposal**, not evidence of full-field execution. Spherical soma geometry,
ideal activities, unbuffered free calcium and continuum pore mechanics omit
biological morphology, microscopic selectivity, buffering and spatial chemistry.
A data carrier preserving field values does not prove their physical coupling.

Exact SI constants are e=1.602176634e-19 C, kB=1.380649e-23 J/K and
NA=6.02214076e23 mol^-1. The selected temperature T=310.15 K is a proposed
boundary condition, not an exact biological constant. VT=kBT/e is therefore
approximately 26.7266591125 mV.
[NIST constants](https://physics.nist.gov/cuu/pdf/all.pdf).

The following are G1's **proposed virtual-material inputs**, not measurements
of the running substrate or universal biological constants:

| Quantity | Proposed value | Role |
| --- | --- | --- |
| Soma radius r | 10 micrometres | Spherical compartment geometry |
| Specific capacitance cm | 0.010 F/m² | Homogeneous membrane material |
| Extracellular fraction alpha | 0.20 | Chosen local volume allocation |
| Preparation potential Vprep | -65 mV | Charged initial condition, never a voltage clamp |
| Pore length l and maximum radius a0 | 5 nm; 0.50 nm | Cylindrical pore benchmark |
| Benchmark conductivity sigma | 1.50 S/m | Homogeneous bulk reference, not every species' conductivity |
| Channels per sector m_c | 100 | Proposed finite anatomical population |
| Single-channel gate charge qg,c | 4e | Proposed displacement sensor, not ionic valence |
| Single-channel gate stiffness k_c | 50 kBT | Harmonic aperture material |
| Single-channel gate drag zeta_c | 1e-21 J s | Proposed dissipative coefficient |
| Single-channel phase coupling Lambda_ca | 5 kBT | Proposed coupling energy |
| Undriven elastic aperture yrest,c; initial y0,c | 0.05; 0.05 | Distinct rest-coordinate and preparation roles |
| Chemical gate bias mu_c | 0 J | Explicitly absent chemical gate drive in this reference proposal |
| Phase coupling scale kappa0 | 10 kBT | Proposed material scale; not a derived H-bond measurement |

Bibliographic motivation does not approve these values. A measured value needs
a specific material, measurement conditions, source location and uncertainty;
a design value needs explicit material/anatomy derivation and ratification.
Remove the previous unused vacuum-permittivity entry: it was incorrectly called
exact SI and is not used by any equation here. Do not substitute these nominal
inputs for the missing species, topology and contact bindings in §9.

## 2. Geometry, integer inventories and initial electrical state

### 2.1 Conditional continuum calculations

\[
A=4\pi r^2,\quad C_{\rm mem}=c_m A,\quad
V_{\rm in}=4\pi r^3/3,\quad
V_{\rm out}=\frac{\alpha}{1-\alpha}V_{\rm in}.
\]

At the proposed inputs: A=1.2566370614e-9 m²,
Cmem=12.5663706144 pF, Vin=4.1887902048 pL and
Vout=1.0471975512 pL. Alpha is a fraction of total volume, not of Vin.
Applying a tissue fraction to one soma is a proposed allocation, not a
measurement of its accessible extracellular space.
[Nicholson & Phillips, 1981](https://pubmed.ncbi.nlm.nih.gov/7338810/).

### 2.2 Proposed finite initial species

Use the following literal integer populations as the reference material
inventory. Nominal concentrations explain their preparation; actual
concentrations are always N/(V NA), not independently retained target values.
Nearest-integer rounding of nominal c V NA uses ties-to-even; no rounding
occurs repeatedly during an experience.

| Species | Valence z_c | Nominal out/in | N_out | N_in | Initial E_c, mV (rounded) |
| --- | ---: | --- | ---: | ---: | ---: |
| Na | +1 | 145/12 mM | 91442380324 | 30270581073 | +66.598213272 |
| K | +1 | 4/140 mM | 2522548423 | 353156779183 | -95.022575663 |
| Ca | +2 | 2 mM/100 nM | 1261274211 | 252255 | +132.343559561 |
| Cl | -1 | 110/10 mM | 69370081625 | 25225484227 | -64.087729544 |

For strictly positive populations, the ideal-activity reference law is
\[
E_c=\frac{k_BT}{z_ce}\ln
 \frac{N_{\rm out,c}/V_{\rm out}}{N_{\rm in,c}/V_{\rm in}}.
\]
General nonideal activities would replace concentration ratios; no such
activity model is claimed here. The calcium inventory is an explicitly
unbuffered free pool, not total biological cellular calcium.

### 2.3 One charge partition, including the gates

Use Q_f for net free compartment charge and Q_cap for dielectric capacitor
charge. They differ when voltage sensors move:
\[
Q_g(y)=\sum_c m_c q^g_c y_c,\qquad
Q_{\rm cap}=Q_f-Q_g,\qquad V=Q_{\rm cap}/C_{\rm mem}.
\]
The outside compartment has the opposite Q_f. Gating polarization is internal
charge displacement, not creation of ions or an additional global charge.

The exact mobile charge counts from the table are:
\[
Z_{\rm mobile,in}=358202380539,\quad
Z_{\rm mobile,out}=27117395544,\quad Q_{\rm mobile,b}=eZ_{\rm mobile,b}.
\]
Thus Qmobile,in is approximately +57.3903484343 nC and Qmobile,out is
**+4.34468575155 nC**, not the submitted +4.331244759 nC.

To avoid simultaneously demanding non-integral net ionic charge and an exact
target voltage, the reference preparation specifies:
\[
Z_{f,0}=\operatorname{round}_{even}
 [(C_{\rm mem}V_{\rm prep}+Q_g(y_0))/e],\quad Q_{f,0}=eZ_{f,0},
\]
\[
Z_{\rm fixed,in}=Z_{f,0}-Z_{\rm mobile,in},\qquad
Z_{\rm fixed,out}=-Z_{f,0}-Z_{\rm mobile,out}.
\]
For the four proposed 100-channel sectors at y0=0.05, Qg,0=80e,
Zf,0=-5098073, Zfixed,in=-358207478612 and Zfixed,out=-27112297471.
These are **proposed immobile virtual charge inventories**, not counterions
inferred from a Debye-length assertion. They are fixed after genesis and
cannot be recomputed to maintain a preferred voltage.

The resulting actual initial voltage is approximately -65.0000056804 mV;
Qcap,0=-8.168141613157002e-13 C. Derive stored energy from this actual state,
Ecap,0=Qcap,0²/(2Cmem), not from a separately imposed -65 mV.
The reference geometry/constant representation must be fixed before executable
genesis; printed decimals are not substitutes for canonical parameter bits.
Global free charge is exactly zero because
Zmobile,in+Zfixed,in+Zmobile,out+Zfixed,out=0.

## 3. Transport, finite chemistry and energy accounting

For outward-positive ionic current, q_c=z_c e:
\[
I_c=g_c(V-E_c),\quad J_c=\int I_c\,dt,\quad
\xi_c=r_c+J_c/q_c,\quad n_c=\operatorname{trunc}\xi_c,\quad r'_c=\xi_c-n_c,
\]
\[
q_cn_c+q_c(r'_c-r_c)=J_c,\quad
N'_{\rm in,c}=N_{\rm in,c}-n_c,\quad
N'_{\rm out,c}=N_{\rm out,c}+n_c.
\]
Keep whole counts and the admitted charge/remainder representation exact.
Remove the invented 1e-20 C roundoff allowance. Numerical integration error in
J and exact custody of its admitted finite value are different issues; this
document approves no solver or tolerance. A remainder is not another whole ion.

After all actual incoming/outgoing transfers:
\[
Q'_f=Q_f-\sum_c q_cn_c+\Delta Q_{\rm contact,in}
+\Delta Q_{\rm active,in},\quad
V'=(Q'_f-Q_g(y'))/C_{\rm mem}.
\]
Every contact/active term must have a debit/credit at its physical endpoints;
do not also settle the same transfer as an independent ionic current.

No negative population, oversubscribed shared source, clipped material,
manufactured concentration floor or discarded remainder is admissible.
The positive-population Nernst/Ohmic law above is undefined at depletion.
Its current implementation boundary must refuse before mutation if no approved
depletion transport law applies. This is an unavailable capability, not a claim
that an actual depleted material would stop evolving. A depletion-safe law is
still a required material binding, not permission to invent epsilon ions.

Finite reservoirs supply chemical free energy. A compatible ideal-solution
reference expression (n_ref is a number density) is
\[
F_{\rm chem}=k_BT\sum_{b,c}N_{b,c}
 [\ln(N_{b,c}/(V_b n_{\rm ref}))-1],
\]
with the continuous 0 ln 0 limit for energy and any declared species standard/
binding terms included. A finite ion transfer uses the finite energy change,
not blindly I*E*dt with a reversal held fixed while the reservoir changes.

For fixed capacitance,
\[
\Delta H_{\rm elec}=
\frac{(Q'_f-Q_g(y'))^2-(Q_f-Q_g(y))^2}{2C_{\rm mem}}.
\]
Complete accounting remains the A14 law:
\[
\Delta(E_{\rm elec}+E_{\rm phase}+U_{\rm gate,nonel}
+U_{\rm elastic}+E_{\rm chemical}+E_{\rm kinetic})
=W_{\rm in}-W_{\rm out}-Q_{\rm heat,out}.
\]
Use a declared isothermal heat boundary if T is held fixed; omit neither
dissipated heat nor work from changing field constraints. Energy is counted
once, including fixed-charge preparation and gate/phase reaction.

**No voltage-holding pump is specified.** Withdraw
Iactive,in=sum I_c(V0,y0) and the unqualified Iactive*Delta_mu_ATP/e formula.
A charged passive component may relax; that is not a failed test.
A future mounted pump requires reaction stoichiometry, finite reactants/products,
kinetics and electrochemical work. For reaction extent nu_dot_r:
\[
\dot N_s=\sum_r S_{sr}\dot\nu_r,\quad
I_{\rm active,in}=e\sum_{s,r}z_s S_{{\rm in},s,r}\dot\nu_r,\quad
P_{\rm chem}=-\sum_r\Delta G_r\dot\nu_r .
\]
Units and sign depend on declared reaction orientation. No such pump may be
synthesized solely to cancel leakage. Explicitly pump-free component cases
are not full metabolic recovery or a complete autonomous neuron.

## 4. Pore boundary: one geometry, one aperture law

The submitted homogeneous bulk-cylinder benchmark is conditional, not a
species-selective biological channel:
\[
R_{p0}=l/(\sigma\pi a_0^2),\quad R_{a0}=1/(2\sigma a_0).
\]
At the proposed values, Rp0 approximately 4.244131816e9 ohm and
Ra0 approximately 6.666666667e8 ohm. At full aperture,
gpore=235.619449 pS and gwith-access=203.632872 pS.

Hall access resistance assumes a particular homogeneous, symmetric bath
boundary. It is not derived for this model's finite asymmetric reservoirs.
[Sahu & Zwolak, equation 1 and limitations](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=923881).
Keep it a conditional benchmark unless the actual boundary satisfies those
assumptions or has its own derived access law. Adding its value to a table
does not supply the missing species-selective transport.

For the proposed **continuously changing circular area**, A(y)=y*pi*a0²,
so a(y)=a0*sqrt(y). Therefore, for that access benchmark:
\[
g_c(y)=
\begin{cases}
m_c/[R_{p0,c}/y+R_{a0,c}/\sqrt y],&0<y\le1,\\
0,&y=0.
\end{cases}
\]
It is not y*gmax. At y=0.05 the benchmark per-pore conductance is
11.381217721 pS rather than the linear formula's 10.181643612 pS.
For an explicitly internal-pore-only voltage boundary, Ra is absent and
g_c(y)=m_c*sigma_c*pi*a0,c²*y/l_c; bath drops belong elsewhere.

The two boundaries are not interchangeable runtime options. The mounted
material must specify one complete boundary and species transport law.
Do not assign the complete saline bulk conductivity independently to every
ion species. Species conductivity/permeability and depletion behavior remain
required inputs (§9); no generic Na/K/Ca/Cl fallback is approved.

## 5. Reciprocal gate mechanics without double-counted electrical energy

All k_c, zeta_c, Lambda_ca and qg,c below are **per channel**.
A sector has m_c identical gates with a common continuous aperture y_c:
this is a declared reduced coordinate, not a probability or n_open/m_c.

Separate the non-electrical gate potential from capacitor energy:
\[
u_c(y,\phi)=\tfrac12 k_c(y-y_{\rm rest,c})^2
-\sum_a\Lambda_{ca}y\cos(\phi_a-\phi^*_{ca})-\mu_c y,
\]
\[
H=\frac{(Q_f-Q_g(y))^2}{2C_{\rm mem}}+
\sum_c m_c u_c+E_{\rm phase}+E_{\rm contact}+E_{\rm plastic}+E_{\rm chem}.
\]
Do not add a second -m_c*qg,c*V*y term to H: its gate force is already
obtained by differentiating the electrical energy at fixed Q_f.

For the explicitly proposed ideal hard aperture stops:
\[
0\in m_c\zeta_c\dot y_c+\partial_{y_c}H+
N_{[0,1]}(y_c).
\]
The interior form, divided by m_c, is
\[
\zeta_c\dot y_c=-k_c(y_c-y_{\rm rest,c})+q^g_cV+
\sum_a\Lambda_{ca}\cos(\phi_a-\phi^*_{ca})+\mu_c .
\]
At y=0 or 1 the normal-cone reaction enforces the material stop, not an
after-step clipping algorithm. It does not supply the numerical solver.
The phase receives the reciprocal force
\[
-\partial_{\phi_a}\sum_c m_c u_c
=-\sum_c m_c\Lambda_{ca}y_c\sin(\phi_a-\phi^*_{ca}).
\]
Aggregate energy, drag, charge and conductance all use the same m_c.

The continuum charge-balance identity is
\[
C_{\rm mem}\dot V=-\sum_c I_c+I_{\rm contact,in}
+I_{\rm active,in}-\dot Q_g .
\]
Actual whole-carrier publication follows §3; do not update Q_f a second time
from this continuum identity.

For fixed voltage/phases, the unconstrained gate stationary point is
\[
y_{\rm eq}=y_{\rm rest}+
[q^gV+\sum_a\Lambda_{ca}\cos(\phi_a-\phi^*_{ca})+\mu_c]/k_c.
\]
Consequently yrest=0.05 is not a claimed coupled resting equilibrium.
zeta_c/k_c approximately 4.670624 ms is an isolated frozen-drive timescale,
not permission for one 50-ms explicit Euler step. Physical rest, coupled
stability and solver accuracy still require the completed binding.

## 6. Typed field incidence, phase fabric and retained mechanics

Retain the complete shared UF result and each reached neuron's local
perspective exactly as A14-01 specifies. A field family, numeric role,
numerator/denominator, ternary position, sign/signed-zero evidence, source
lineage/time and physical locality remain distinct. S(UF) stays separate.

Name a complete typed digit j and its **supplied anatomical edge incidence**
E_j within the mounted fabric. Then
\[
E_{\rm DSF}=-\sum_j\kappa_j\sum_{(a,b)\in E_j}
\cos(\phi_b-\phi_a-2\pi\tau_j/3).
\]
The paired endpoint forces are +kappa_j*sin(theta_ab) and
-kappa_j*sin(theta_ab). A local three-node ring can realize spatial winding;
it is not the universal entire fabric. Typing a record does not prevent
physical flattening if every type is then assigned the same nodes and forces.
No automatic ring allocation, alphabetical wiring, shared untyped overwrite,
seven-oscillator substitute or 3^p-to-drive scaling is approved.

Use the existing complete energy and local settlement:
\[
\zeta_{\rho,a}\dot\rho_a=-\partial_{\rho_a}E+P_a,\qquad
\zeta_{\phi,a}\rho_a\dot\phi_a=-\partial_{\phi_a}E+\tau_a.
\]
Anatomical incidence, amplitude energy/boundary, damping, gate offsets and
contact coupling still require actual material data. Writing this equation
does not supply those data. A changing imposed constraint carries work.

For the already accepted P0 strain-energy element, correct the dimensional
mistake in G1's revision:
\[
k_{\rm axial}=E_{\rm mod}A_{\rm ref}/L_{\rm ref}\ [N/m],\qquad
K_\epsilon=E_{\rm mod}A_{\rm ref}L_{\rm ref}
=k_{\rm axial}L_{\rm ref}^2\ [J].
\]
Use K_epsilon, not k_axial, in
\[
\epsilon=x/l-1,\quad U=\tfrac12K_\epsilon\epsilon^2,\quad
\Sigma=K_\epsilon\epsilon,\quad f=|\Sigma|-Y,\quad 0<Y<K_\epsilon.
\]
At fixed actual mechanical x>0:
\[
l'=\begin{cases}
l,&|\Sigma_{\rm tr}|\le Y,\\
x/(1+sY/K_\epsilon),&|\Sigma_{\rm tr}|>Y,\quad s=\operatorname{sign}\Sigma_{\rm tr}.
\end{cases}
\]
The plastic branch dissipates
Dpl=K_epsilon[epsilon_tr²-(Y/K_epsilon)²]/2 >= 0.
This is the prior P0 law, not a new material model. Changing-x work, actual
contact geometry and the returned length's conductance consequence must be
accounted for; do not invent x from DSF magnitude or activation products.

## 7. Receiving current, persistence and evidence

The proposed Column 48 receiver must have its own physically mounted
capacitance, charge, gates and reservoirs. A label does not mount a compartment.

For a mounted electrical contact:
\[
I_{ij}=g_{ij}(V_i-V_j),\quad J_{ij}=\int I_{ij}dt,\quad
\Delta Q_{f,i}=-J_{ij},\quad\Delta Q_{f,j}=+J_{ij}
\]
at the continuum accounting level, with actual carrier custody and species
endpoints specified once. Fan-out cannot duplicate charge. A chemical
synapse instead uses finite release/receptor/post-synaptic mechanics.

There is no voltage-to-refusal, voltage-to-word or threshold-to-cognition
table. Receiving current is the next physical output to prove.
**No claim is made that the existing L5 motor decoder already implements
this proposed law.** Complete neuron-to-world motor authority remains A10/A11
work, not something authorized by these equations.

Preserve the A14 atomic successor, single state owner, explicit schema/version
and full cold-next-step identity. Persist every causal remainder, gate,
phase, ion inventory, fixed charge, contact and material state; no implicit
genesis on restore, sidecar state, partial publication or all-population work.
Work scales with physically reached nodes/contacts, not elapsed history.

## 8. Corrections completed in this revision

- Kept the corrected volume definition and recomputed values from literal ions.
- Corrected extracellular charge; included gate polarization in initial charge;
  supplied one exact-integer proposed preparation without a voltage reset.
- Replaced unsupported measured/universal claims with proposed material inputs.
- Removed the unapproved roundoff allowance and voltage-holding pump.
- Made aperture geometry consistent with the chosen electrical boundary.
- Made gate energy, sensor charge, drag and phase reaction share sector scaling.
- Restored the correct joule-valued strain stiffness and existing return map.
- Removed mounted/full-field/motor-success claims and made typed incidence explicit.
- Preserved every runtime/test gate. These are document corrections, not a
  physiological validation or implemented-neuron acceptance.

## 9. One remaining binding deliverable — no new architecture or review ladder

G1's next item is **one concrete material/anatomy binding for the existing
corrected law**, not another paraphrase of this dossier. Do not guess defaults.

| Required binding | Actual missing input | Consumer / consequence |
| --- | --- | --- |
| Typed reached fabric | Nodes, E_j incidence, amplitude energy/bounds, phase/amplitude damping and initial state | Exact MathLoom facts -> material phase/gate response |
| Gate/material authority | Derivation/ratification of proposed coefficients and phase offsets; species-specific aperture/transport and depletion law | Gate -> conserved ionic transfer and dissipation |
| Retained physical contact | Modulus, reference geometry, yield, actual x coupling and conductivity | Experience -> retained length/conductance change |
| Receiving and chemical boundary | Source/receiver compartments, contacts, finite thermochemistry; pump/reaction law only if mounted | Real current, depletion/recovery, no invented energy |
| Executable representation | Frozen parameter representation, coupled settlement/error law, complete canonical state and bounded resource plan | Determinism, no silent approximation, cold restart |

These are the previously required A14/A15 bindings, not added biological detail.
Concrete audit corrections are made; **numerical material ratification remains
unavailable until these inputs exist**. Do not claim all six capabilities
closed merely because the six document headings were rewritten.

Acceptance after binding: one authentic full-input -> typed material -> gate ->
source-debited receiving-current path, with real retained change if yielded,
subsequent response, finite accounting, severed/unforced behavior and identical
ordinary cold successor. Support it with focused falsification, not another
broad rerun of unchanged tests or an artificially forced motor answer.
