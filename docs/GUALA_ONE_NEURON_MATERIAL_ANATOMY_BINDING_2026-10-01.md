# Guala one-neuron material/anatomy binding — corrected implementation boundary

Date: 2026-10-01 UTC. A1 correction of G1 commit faf725921.
Governing authority: [parameter dossier](GUALA_ONE_NEURON_PHYSICAL_PARAMETER_DOSSIER_2026-10-01.md)
and [A14 transition contract](GUALA_ONE_NEURON_PHYSICAL_TRANSITION_CONTRACT_2026-10-01.md).

**Disposition: the submitted concrete binding is NOT ratified.**
This revision replaces its incorrect equations, arithmetic and closure claims.
It is not a mounted neuron, a biological calibration, a complete numerical
solver or authorization to unlock A10/A11. Native source and capability tests
remain unchanged. The original proposal remains available in git.

## 1. Scope and architecture gate

Requested architecture: one persistent neuron receiving the unchanged complete
joint field, exact typed MathLoom constraints, reciprocal physical phase/gate
coupling, conserved membrane/material transfer, retained physical plasticity,
and complete ordinary cold restoration.

Current source reality: native MathLoom retains finite binary64 facts exactly;
ModularSubstrate64D::step_cycle explicitly refuses the missing typed material
operator. The new binding was a document only. The unchanged native/Python
tests cannot validate equations that they do not execute.

Conflict: **yes**. The submitted common ring flattens typed constraints, its
finite ternary expansion is not the existing exact codec, several coefficients
lack a material derivation, and its active transport and checkpoint are incomplete.

Not extended: the +/-52 cutoff; positional decay; field-name angles; arbitrary
phase-to-current activation; unfunded pumps; the claimed complete 384-byte
record; or manufactured passing witnesses.

Single next item: establish one complete, explicitly sourced or explicitly
approved artificial material binding, then implement that same binding through
the existing one-neuron boundary. Do not ask for another review of unchanged
legacy test totals.

Evaluation here is **reduced component mathematics and source inspection**.
The proposed lumped soma/pore/contact model omits spatial chemistry and detailed
morphology. No continuous full joint-field neuronal execution is demonstrated.

## 2. Typed fabric: exact correction and decisive falsification

The submitted representation used p=-52..52 and one three-node ring for every
fact, with theta_q=2*pi*q/7 and kappa_qp=kappa0*3^(-abs(p)/16).
It is rejected for three independent reasons:

- A finite sum of integer trits times powers of three cannot represent 1/2
  exactly. Its reduced denominator divides a power of three. Numerator and
  denominator therefore must be retained separately, as MathLoom already does.
- The smallest positive binary64 value is 1/2^1074. Its denominator needs
  **679 balanced-ternary digits**, positions 0..678; 52 binary mantissa bits
  are not a ternary-position bound.
- For the same q, interchange tau_(q,+1)=1,tau_(q,-1)=0 with
  tau_(q,+1)=0,tau_(q,-1)=1. The proposed coefficients are equal at +1 and -1.
  Its entire energy and every phase derivative are identical, although the
  represented values would be 3 and 1/3. This is an exact alias, not a
  numerical-tolerance objection.

More generally, the common-ring energy factors through the weighted phasor
\[
 Z=\sum_{q,p}\kappa_{qp}
       \exp[-i(2\pi\tau_{qp}/3+\theta_q)],\qquad
 E=-\sum_{a\to b}\operatorname{Re}
       [\exp(i(\phi_b-\phi_a))Z].
\]
Field-name angles do not make this a lossless physical incidence map.

**Correction:** use the existing exact rational codec, preserving numeric role,
field family, numerator/denominator, position, signed-zero evidence, source
time, locality and shared field reference. For typed fact j, the A14 law is
\[
 E_j=-\sum_{(a,b)\in\mathcal E_j}\kappa_{j,ab}
 \cos(\phi_b-\phi_a-2\pi\tau_j/3).
\]
The actual mounted incidence set \(\mathcal E_j\) and material energies
\(\kappa_{j,ab}\) must be explicit anatomy, not functions of field magnitude,
field ordinal or digit significance. Positional \(3^p\) remains representation,
not stiffness. Retain zero digits and type information at the boundary;
do not silently coalesce distinct constraints.

For each admitted physical edge, with theta as its argument:
\[
 F_{\phi_a}=+\kappa\sin\theta,\qquad
 F_{\phi_b}=-\kappa\sin\theta .
\]
These paired forces were correct in the submission; keep them. Their zero
internal sum does not repair a lossy input map.

Do not invent a fixed number of rings or an all-to-all graph here. DNA/anatomy
must provide the sparse reached incidence and its size. Keep the complete
shared UF result once, with each neuron's local perspective and incident
contacts. Seven scalar fields plus S(UF), alone, are not that complete result.
S(UF) remains separate, not an eighth neuronal coordinate or an execution gate.

## 3. Amplitude units and one reciprocal energy

For the submitted choice [rho]=J/m^3 and energy E in joules:
\[
 [k_\rho]=m^6/J,\quad
 [\zeta_\rho]=m^6\,s/J,\quad [\zeta_\phi]=m^3\,s.
\]
These follow from
\[
 \zeta_\rho\dot\rho=-\partial_\rho E,\qquad
 \zeta_\phi\rho\dot\phi=-\partial_\phi E.
\]
The submitted J s/m^3 and J s values are dimensionally incompatible.
**Do not keep their numerical values with new unit labels.** A dimensionless
rho convention would instead permit drag units J s, but requires an explicitly
declared material normalization. No such normalization is ratified here.

For fixed capacitance and net free compartment charge Qf, use the dossier's
single closed-system electrical energy:
\[
 Q_g=\sum_c m_c q_c^g y_c,\quad
 V=(Q_f-Q_g)/C,\quad
 H_{\rm elec}=(Q_f-Q_g)^2/(2C).
\]
Define non-electrical single-gate energy
\[
 U_{c,\rm nonel}
 =\tfrac12 k_c(y_c-y_{r,c})^2
 -\sum_a\Lambda_{ca}y_c\cos(\phi_a-\phi^*_{ca})-\mu_c y_c .
\]
Then
\[
 H=H_{\rm elec}+E_{\rm fabric}+\sum_c m_cU_{c,\rm nonel}
   +U_{\rm contact}+F_{\rm chem},
\]
\[
 0\in m_c\zeta_c\dot y_c+\partial_{y_c}H+N_{[0,1]}(y_c),
\quad
 -\partial_{\phi_a}(m_cU_{c,\rm nonel})
 =-m_c\Lambda_{ca}y_c\sin(\phi_a-\phi^*_{ca}).
\]
The voltage force \(m_cq_c^gV\) already follows by differentiating H_elec.
Do not add -VQg a second time. A prescribed-voltage energy uses a different
external-work boundary; it is not interchangeable with this closed system.

Gate populations, charges, offsets, coupling, stiffness, drag and chemical bias
must refer to one immutable material definition. The dossier's earlier
four-equal-sector proposal and G1's new heterogeneous proposal are distinct,
unratified anatomies. Neither is a measured cortical cell; labels such as
“fast excitatory” or “delayed rectifier” do not establish their dynamics.

## 4. Conductance and genesis: corrected conditional numbers

The cylindrical homogeneous-bath reference remains
\[
 R_{p0}=\ell/(\sigma\pi a_0^2),\quad R_{a0}=1/(2\sigma a_0),
\quad g(y)=\frac{y}{R_{p0}+R_{a0}\sqrt y},\quad g(0)=0.
\]
At ell=5 nm, a0=0.50 nm, sigma=1.50 S/m:

| Aperture y | Single-pore g(y), pS |
| ---: | ---: |
| 0.02 | 4.609980952 |
| 0.05 | 11.381217721 |
| 0.10 | 22.446939398 |
| 1.00 | 203.632872245 |

The submitted calcium/chloride numbers were wrong and the column was
mislabelled g(0.05). Multiply by channel count once for a sector.
This bulk access-resistance benchmark does not derive ion selectivity,
subnanometre pore chemistry, unequal-bath access resistance, or a
depletion-safe species transport law. Do not mount the same saline
conductivity as four independently calibrated species conductivities.

For G1's changed counts (Na,K,Ca,Cl)=(100,100,20,50), aperture preparation
(.05,.05,.02,.10), gate charges (4e,3e,2e,0):
\[
 Q_{g,0}=(20+15+0.8)e=35.8e,
\]
not the dossier's earlier equal-sector 80e. Keep the distinction explicit.

With the dossier's literal finite ion inventories, geometry-derived C, and
Vprep=-65 mV, the conditional compatible integer genesis is
\[
 Z_{f,0}=\operatorname{round}_{even}
 [(CV_{\rm prep}+Q_{g,0})/e]=-5098117,
\]
\[
 Z_{\rm fixed,in}=-358207478656,\qquad
 Z_{\rm fixed,out}=-27112297427.
\]
Hence the approximate fixed charges are -57.39116524267 nC and
-4.343868943160 nC, and actual V0 is -65.0000031305 mV.
Use the exact counts and declared executable constant representation, not
printed rounded voltages as independent state. Reusing old Zf=-5098073 with
the new gates instead gives approximately -64.9994421430 mV.

The submitted rounded fixed charges, combined with the dossier's mobile
inventories, leave **+1.3441185829464461e-11 C** net charge, not zero.
Neither the charge balance nor a “Debye electroneutrality” label proves a
resolved spatial electrostatic model. Fixed charges remain fixed after
preparation; never adjust them every beat to maintain a desired voltage.

These calculations repair consistency **conditional on that proposed anatomy**.
They do not select it over the earlier proposal or authorize its installation.

## 5. Contact and receiving closure: keep the law, remove unsupported claims

For the submitted reference geometry, the dimensional relations are correct:
\[
 K_\epsilon=E_{\rm mod}A_{\rm ref}L_{\rm ref}\ [J],\quad
 k_{\rm axial}=E_{\rm mod}A_{\rm ref}/L_{\rm ref}\ [N/m].
\]
If E_mod=100 kPa, r=0.10 micrometres and Lref=1 micrometre, these are
3.14159e-15 J and 3.14159e-3 N/m. But that material modulus is NOT established
by the cited Gittes paper for a spine neck. The paper measures filament bending
rigidity; its actin isotropic estimate is about 2.6 GPa, not 100 kPa.
Do not replace 100 kPa with 2.6 GPa either: an isolated filament is not a
composite spine neck.
[Gittes et al., 1993](https://doi.org/10.1083/jcb.120.4.923).

Likewise, choosing a five-percent yield strain gives Y=0.05 K algebraically;
it does not derive that yield strain from the material.

Keep the accepted fixed-actual-length return law:
\[
 \epsilon_{\rm tr}=x/\ell_n-1,\quad \Sigma_{\rm tr}=K\epsilon_{\rm tr},
\quad
 \ell'=
 \begin{cases}
 \ell_n,&|\Sigma_{\rm tr}|\le Y,\\
 x/(1+sY/K),&|\Sigma_{\rm tr}|>Y,\ s=\operatorname{sign}\Sigma_{\rm tr}.
 \end{cases}
\]
On the plastic branch only,
\[
 D_{\rm pl}=\tfrac12 K[\epsilon_{\rm tr}^2-(Y/K)^2]\ge0;
\]
on the elastic branch D_pl=0. Require x>0, K>0 and 0<Y<K.

What remains missing is a physical source and evolution law for actual length
x, its applied work, and a constitutive mapping from actual/retained geometry
to electrical path area and length. In the submitted law, ell is a stress-free
rest length; it is not automatically the current conducting length.
The general electrical law is g=sigma*A_actual/L_actual. Equating L_actual
to ell requires a declared mechanical state, not a relabelling shortcut.
At the undeformed reference geometry, sigma=0.50 S/m would yield 15.708 nS;
that conditional arithmetic was correct.

For a reached electrical connection i->j:
\[
 I_{ij}=g_{ij}(V_i-V_j),\quad
 \Delta Q_i=-J_{ij},\quad\Delta Q_j=+J_{ij}.
\]
Both endpoints must participate and conserve the transferred quantity.
The ledger's additional C_spine=1 pF is absent from the binding and lacks a
receiving geometry/state derivation. Do not introduce it as a silent default.

## 6. Finite transport, recovery and work

Use exact signed carrier custody from A14:
\[
 \xi_c=r_c+J_c/(z_ce),\quad n_c=\operatorname{trunc}\xi_c,\quad
 r'_c=\xi_c-n_c,\quad
 z_ce[n_c+r'_c-r_c]=J_c.
\]
Finite counts settle with equal/opposite endpoints; no negative reservoir,
oversubscribed fan-out, implicit source or discarded remainder is allowed.
Numerical error in the integrated current and exact custody of its admitted
finite value are different obligations. Four f64 remainder slots do not prove
the exact rational identity.

The Na/K pump's 3-out/2-in stoichiometry was correct. The submission did not
define a rate, finite ATP/ADP/Pi inventories, reaction remainder or lawful
electrochemical drive. A cumulative work counter is not a fuel reservoir.

For a future admitted forward extent n:
\[
 \Delta(N_{\rm Na,in},N_{\rm Na,out},N_{\rm K,in},N_{\rm K,out})
 =(-3n,+3n,+2n,-2n),
\]
\[
 \Delta(N_{\rm ATP},N_{\rm ADP},N_{\rm Pi})=(-n,+n,+n),
\quad\Delta Q_{\rm in}=-ne,\quad\Delta Q_{\rm out}=+ne,
\]
\[
 n\le\min(\lfloor N_{\rm Na,in}/3\rfloor,
          \lfloor N_{\rm K,out}/2\rfloor,N_{\rm ATP}).
\]
This bound is NOT a kinetic law. Finite reactant/product free energy must fund
the actual electrical/chemical/material energy change and dissipation.
A fixed 20 kBT/cycle without those inventories does not establish recovery.

Withdraw the claim that the specified pump maintains the gradients. An
unpowered passive component can relax; it cannot be sold as a complete
recovering neuron. Retain the explicit unavailable recovery boundary until its
material binding exists. Do not add a voltage-holding pump or cancellation rule.

All phase-boundary changes, gate motion, contact deformation, chemical transfers
and external forcing enter the same work balance:
\[
 \Delta H_{\rm complete}=W_{\rm in}-W_{\rm out}-Q_{\rm heat,out}.
\]
A fixed temperature requires a declared heat boundary. No solver, timestep
tolerance or approximation for this coupled neuronal system is approved here;
prior body/optics numerical approvals do not apply to it.

## 7. Complete custody, not a guessed byte budget

The proposed table's offsets do add up to 384 bytes. That arithmetic is not
the defect. Its content does not cover the complete causal successor:

- No actual typed incidence/anatomy identity and full-field/local-perspective
  custody; no variable reached fabric or contact topology.
- No receiving endpoint state or pump/reactant/product/remainder state.
- Inexact f64 carrier remainder proposed as exact rational custody.
- Independently stored V, Qg and Qf can disagree; gate velocity and winding
  are derived for the stated overdamped model unless separately justified.
- “Reserved” bytes are not implemented fan-out. CRC does not establish
  physiological validity, field completeness or successor equivalence.

Correction: use one versioned, length-framed canonical state containing each
independent physical state once, plus bounded immutable-anatomy and shared-field
references. Restore must resolve those references from the same canonical
custody, without optional sidecars or silently regenerated anatomy. Recompute
derived values; reject inconsistent redundant encodings and noncanonical
padding. Include a solver's causal state if its approved method requires it.

The size is derived from the mounted anatomy and exact numeric representation:
\[
 S=S_{\rm framing}+S_{\rm anatomy\ references}
 +S_{\rm reached\ fabric}+S_{\rm gates}+S_{\rm reservoirs}
 +S_{\rm contacts}+S_{\rm exact\ remainders}+S_{\rm physical\ boundaries}.
\]
Bound each term by admitted material/anatomy, not by elapsed observations.
No fixed total byte count can be certified before those terms are defined.
Exact remainder arithmetic must have a derived finite representation bound;
do not replace it with an unbounded append-only or growing arbitrary-history
store.

Both codec and transition identities remain required:
\[
 decode(encode(S))=S,\quad
 T(decode(encode(S)),u)=T(S,u).
\]
Compute all fallible successor work before atomic publication. Every refusal
must leave the predecessor unchanged. No automatic genesis on missing mandatory
state. A10/A11 remain open until these executable obligations are actually met.

## 8. Source impact and bounded completion route

| Incoming authority / evidence | Affected existing source or consumer | Required correction / non-impact |
| --- | --- | --- |
| Full UF result and local perspective | native/guala_core/src/cortical_column.rs: consume_continuous_joint_field, step_cycle | Preserve complete shared authority and mount typed material transition; the current eight-value carrier alone is not full local anatomy. Keep refusal until available. |
| Exact finite canonical field bits | native/guala_core/src/mathloom.rs: MathLoomRationalField | Reuse exact numerator/denominator codec and its derived bound; no +/-52 cutoff or positional force weights. No kernel change. |
| Mounted material/genesis | Future one-neuron state; current constitutive.rs components | One roster, derived units, one free charge, finite species and reciprocal energy. Existing numerical component is explicitly unmounted, not an exact neuron. |
| Actual contact geometry and finite chemistry | coupled_synapse.rs and future physical receiving path | Component fixtures do not supply the missing field-to-material law. Do not promote fixture provenance or fixed reversals to production evidence. |
| Complete successor | cortical_column.rs ordinary persistence path | Same authoritative current state, complete restart, no sidecar or partial 384-byte claim. |
| Executable causal witness | tests/test_mathloom_a10_boundary.py; tests/test_arcloom_causal_action_witness.py | Preserve strict open markers; test the actual mounted chain and ordinary restore, not manually selected motor outputs. |
| Accepted artifact only | arcloom_demonstrator/ and its release archive | Do not package a new “complete” release or change live production from this document. |

**What is now corrected:** field-alias explanation and exact representation
contract; amplitude units; reciprocal energy convention; nonlinear pore
arithmetic; changed-roster charge accounting; unsupported material attribution;
plastic-versus-actual geometry distinction; unfunded-pump and incomplete-codec
claims. No native closure is claimed.

**What cannot be manufactured by an audit:** the actual sparse material
incidence, sourced coupling/drag/gate material, species-selective transport,
mechanical loading and receiver, and finite recovery chemistry. The architecture
supplies their equation forms, not their calibrated values.

The one remaining design decision is the material authority: a deliberately
designed artificial reference material, explicitly approved as such, or a
specific measured biological preparation. Neither may be mislabeled as the
other. With that settled, implement one end-to-end neuron and its complete
cold successor; do not add more anatomy, cognition, columns or production
features. Passing legacy suites and another sign-off request are not substitutes.
