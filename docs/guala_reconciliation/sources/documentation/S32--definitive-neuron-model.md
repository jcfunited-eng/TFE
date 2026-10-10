# Definitive Guala neuron model

Status: ratified by Joseph Forrester on 2026-08-04. This is the sole canonical
Guala neuron architecture for future design, implementation, review, testing,
deployment, and production claims. It defines the architecture and equation
forms; it does not claim that current source or production implements them.

## Contents

1. Authority and supersession
2. One-neuron definition
3. Complete causal flow
4. Physical inputs
5. Complete UF/DSF delivery
6. MathLoom and balanced ternary
7. Unified Krimelack/Psi fabric
8. Law fields
9. Krimelack-to-membrane bridge
10. Membrane, material, fluid, and sparse coupling physics
11. Depletion, recovery, plasticity, DNA, and familiarity
12. L6 observation
13. Exact neuronal fractal
14. Fractal-to-mosaic boundary
15. Resource law
16. Historical-component disposition
17. Implementation and proof order

## 1. Authority and supersession

Use this model without reconstructing, simplifying, or blending it with older
neuron designs. Preserve unchanged L0-L4 and every explicit typed DSF field.
Classify implementation separately from architecture.

This model permanently rejects:

- a DSF tuple, local perspective, sign/null trits, recurrence counts, or a
  receipt being called a neuronal fractal;
- Grandurun cosine/nearest-match cognition;
- semantic spin-vector dimensions such as source match, semantic neighborhood,
  affective score, or Chi resonance;
- fixed sixteen-dimensional Psi as universal neuron law;
- scalar familiarity feedback or match-score dead zones;
- direct algebraic Krimelack-to-Krimelack transfer;
- Krimelack winding directly becoming voltage, current, energy, or an ion;
- seven independent DSF oscillators, scalar DSF sums, or cross-field carry;
- semantic law fields, scripted goals, static meanings, ML, and random wiring;
- count-only mosaic admission; and
- owner, lock, database, validation, receipt, persistence, UI, or deployment
  machinery inside the pure neuronal physics transition.

Earlier unresolved-Krimelack documents remain implementation-history evidence,
not authority to recreate a different architecture. This model ratifies the
functional equation forms. Every material coefficient, unit, anatomy, and DNA
specialization still requires a physical derivation before executable use.

## 2. One-neuron definition

A Guala neuron is one persistent local physical unit:

\[
\mathcal N_i=(G_i,A_i,X_i,\Psi_i,K_i,Q_i,V_i,\mathcal C_i,
\mathcal M_i,\Theta_i,\mathcal B_i).
\]

- \(G_i\): growth and specialization DNA.
- \(A_i\): mounted anatomy, position, topology, material parameters, and units.
- \(X_i\): receptor, synaptic, body, and fluid input state.
- \(\Psi_i\): local amplitude/phase settling lattice.
- \(K_i\): typed Krimelack balanced-ternary phase/winding state.
- \(Q_i,V_i\): membrane charge and potential.
- \(\mathcal C_i\): channel, receptor, gate, and conductance state.
- \(\mathcal M_i\): finite ions, chemicals, vesicles, nutrients, and metabolic
  material.
- \(\Theta_i\): persistent plastic physical structure.
- \(\mathcal B_i\): bounded recent physical arrivals and emissions.

Neuron identity is continuous physical lineage. It is not a field coordinate,
hash, receipt, tuple, label, word, Chi address, database row, or owner.

At first physical reach, a declared resting neuron remains that same neuron.
Its lineage, organism-relative place, capacitance, and existing physical state
cross the receptor boundary unchanged; only anatomy and material physically
reached at that location may be expressed. Reducing the cell to a lineage
ordinal and rebuilding a replacement receptor neuron is forbidden. If a
receptor requires a distinct energy lattice absent from developmental resting
anatomy, leave the resting cell unclaimed until that anatomy is physically
authored; do not claim and discard it.

`LoomNeuron` may be an implementation container for this state. It is not a
sixteenth physical mechanism and has no independent cognitive authority.

## 3. Complete causal flow

```text
physical receptor/body/fluid/synaptic state
  -> exact local temporal source
  -> complete unchanged UF L0-L4 joint DSF delivery
  -> exact MathLoom balanced-ternary representation
  -> typed Krimelack/Psi topological constraints
  -> local energy settlement
  -> physical gate displacement and conductance
  -> membrane charge/potential consequence
  -> finite electrical/chemical/material emission
  -> depletion, recovery, plasticity, and DNA expression
  -> sparse persistent neuronal fractal
  -> future receptor/body/fluid/synaptic state
```

Nothing may skip from DSF to a word, meaning, action, mosaic, answer, or
cognitive-capital claim. Neighbour influence must traverse physical membrane,
channel, synapse, body, or fluid state and become lawful future evidence.

## 4. Physical inputs

One reached neuron receives only locality-resolved physical quantities:

\[
\mathcal I_i(t)=\{x_{ia}(t),g_{ic}(t),E_{ic}(t),n_{is}(t),c_{im}(t),
T_i(t),\Delta t\}.
\]

These may include receptor deformation, photons or virtual-light irradiance,
pressure, temperature, chemical concentration, incoming conductances, reversal
potentials, transported material, body/fluid state, temperature, and the exact
causal interval. Every quantity requires a unit and mounted location. Missing
quantities are unavailable, never zero-filled or replaced by a score.

Preserve the source observation clock and the neuron's reached local physical
interval as separate coordinates. UF and a receptor adapter may integrate an
observation over its exact source time domain; that total observation duration
must not silently become one long membrane-solver step. The organism supplies
the reached local settlement interval from mounted time anatomy. Conversely,
the local interval must not rewrite, shorten, or fabricate the source clock or
its integrated physical work.

Sensory oscillator banks exist only in neurons whose DNA and anatomy mount the
applicable receptor mechanics. Ordinary internal neurons receive electrical,
chemical, body, and fluid perturbations; they do not pretend to have every
sense.

## 5. Complete UF/DSF delivery

### One complete joint input

For one simultaneous occurrence use:

\[
\mathcal J=(T,\mathcal V,\mathcal G,F,r,\mathcal E).
\]

- \(T\) is the strictly ordered causal time domain.
- \(\mathcal V\) is the set of typed mounted vertices retaining physical
  quantity, original units, position, availability, and source lineage.
- \(\mathcal G\) is declared physical grouping metadata; it never normalizes
  away magnitude.
- \(F:T\rightarrow\mathbb R^{|\mathcal V|}\) is one simultaneous vector field
  supplied by derived receptor/domain adapters.
- \(r(t)\) is lawful exact source relevance. It is never inferred from energy,
  attention, a semantic label, a score, or a learned model.
- \(\mathcal E(t)\) is the sparse set of mounted physical contacts and exact
  typed contact state. Never generate a complete all-to-all graph.

Raw quantities with incompatible dimensions never enter one Euclidean norm.
Each receptor adapter must supply its derived UF coordinate law while retaining
original unit-bearing physical evidence by reference. A missing adapter makes
that coordinate unavailable; it is never zero-filled.

Evaluate unchanged UF v1.4 exactly once over the complete vector \(F\). Never
run an independent kernel per vertex and never invent componentwise L4
operators.

### L0: sequential evidence and Negative Space

\[
\Delta F(t)=F(t)-F(t-\Delta t)
\]

\[
\sigma(t)=\frac1W\sum_{j=0}^{W-1}
\|F(t-j\Delta t)-\bar F_W(t)\|^2
\]

\[
\kappa(t)=\|F(t+\Delta t)-2F(t)+F(t-\Delta t)\|
\]

\[
N(t)=\begin{cases}
1,&\sigma<\sigma_{min}\land\|\Delta F\|<\delta_{min}
\land\kappa<\kappa_{min}\\
0,&\text{otherwise}
\end{cases}
\]

\[
SEV(t)=(F,\Delta F,\sigma,\kappa,r,N).
\]

### L1: gates and multi-lattice projection

\[
\mathcal D(t)=\alpha_1\|\Delta F\|+\alpha_2\sigma+\alpha_3\kappa.
\]

Use the canonical boundary \(\mathcal D(t)\ge\tau_D\). For gate
\(G_k=[t_a,t_b]\):

\[
T_k=t_b-t_a
\]

\[
V_k=\int_{t_a}^{t_b}
(\beta_1\|\Delta F\|+\beta_2\sigma+\beta_3\kappa)dt
\]

\[
R_k=\int_{t_a}^{t_b}r(t)dt,\qquad TVR_k=(T_k,V_k,R_k)
\]

\[
P_\ell(G_k)=
\left(\left\lfloor\frac{T_k}{h_1^\ell}\right\rfloor,
\left\lfloor\frac{V_k}{h_2^\ell}\right\rfloor,
\left\lfloor\frac{R_k}{h_3^\ell}\right\rfloor\right)
\]

\[
C_k=|\{P_1,\ldots,P_L\}|,\qquad
\delta_g=\|\mu_k-\mu_{k-1}\|.
\]

Reserve \(C_k\) exclusively for this canonical multi-lattice divergence.
Physical contact state is \(\mathcal E\), not \(C_k\) and not an eighth DSF
coordinate. “UF mosaic projection” is not a cognitive mosaic.

### L2: internal structural field

\[
CV_k=TVR_k-\mu_k
\]

\[
S_k=\gamma_1w_k+\gamma_2\frac{\|CV_k\|}{\|CV\|_{max}}
+\gamma_3\frac1{1+C_k}
\]

\[
U_k=\lambda_1\frac{C_k-1}{L-1}
+\lambda_2\frac{\delta_g}{\delta_{max}}+\lambda_3N(G_k)
\]

\[
IAS_k=1\iff U_k>U_{max},\qquad
ISF_k=(w_k,CV_k,S_k,Reg_k,U_k,IAS_k).
\]

### L3: resonance

\[
\mathbf R_k=\left(w_k,\frac{\|CV_k\|}{\|CV\|_{max}},S_k,
\frac1{1+C_k},1-U_k\right)
\]

\[
R(k)=\frac1Z\left(\lambda_1w_k+
\lambda_2\frac{\|CV_k\|}{\|CV\|_{max}}+\lambda_3S_k+
\lambda_4\frac1{1+C_k}+\lambda_5(1-U_k)\right)
\]

\[
Hyst_k=1\iff |R(k)-R(k-1)|>h_{max}
\]

\[
g_k=1\iff U_k\le U_{max}\land IAS_k=0\land Hyst_k=0,
\qquad URF_k=g_kR(k).
\]

### L4: seven explicit canonical fields

All L4 temporal differences consume the same gated \(URF\) predecessor chain:

\[
\Delta R_k=URF_k-URF_{k-1}
\]

\[
D_k=\begin{cases}
+1,&\Delta R_k>\epsilon_D\\
0,&|\Delta R_k|\le\epsilon_D\\
-1,&\Delta R_k<-\epsilon_D
\end{cases}
\]

\[
M_k=URF_k-2URF_{k-1}+URF_{k-2}
\]

\[
R_{rev,k}=1\iff D_kD_{k-1}<0
\]

\[
U_k^*=U_k+\eta_HHyst_k+\eta_I IAS_k
\]

\[
P_k=|D_k-D_{k-1}|
\]

\[
B_k=\operatorname{bound}
[B_{k-1}+\xi(1-U_k^*)\Delta R_k-\chi U_k^*].
\]

\[
DSF_k=(D_k,M_k,R_{rev,k},U_k^*,C_k,P_k,B_k).
\]

The seven explicit fields are one shared gate-level result. They are not the
whole joint result, a compatibility vector, or a neuronal fractal.

### Shared complete result and local neuron perspective

Store the complete result once:

\[
\mathcal K_k=(SEV|_{G_k},TVR_k,P_\ell,C_k,ISF_k,R(k),URF_k,
DSF_k,\mathcal V,\mathcal E|_{G_k}).
\]

For reached neuron \(i\) mounted at vertex \(v_i\):

\[
\pi_{i,k}=(ref\ \mathcal K_k,v_i,SEV_{v_i}|_{G_k},
incident_{\mathcal E}(v_i),ref\ DSF_k).
\]

Every reached neuron receives the same complete-field reference plus distinct
local source component, anatomy, physical state, and incident contacts. The
union of perspectives must reconstruct the declared reached vertices and
sparse topology. Never copy the complete field body into every neuron.

### Deterministic numerical constitution

UF norms generally produce irrational reals. Execute the frozen operator order
with specified IEEE-754 binary64 operations, fixed reduction order, no
reassociation, no fast-math, and no architecture-dependent reduction. Preserve
each produced binary64 value by its exact 64-bit representation, convert that
finite value to its exact rational numerator/denominator for MathLoom, and do
no later sign reduction, scalar sum, or rounding. This is exact retention of
the actual deterministic finite result; it is not a claim that binary64 equals
the mathematical irrational real.

### Global UF stability remains separate

\[
S(UF)=\lambda_c Coh+\lambda_h(1-H_s)+
\lambda_b(1-Var(B))+\lambda_u(1-\bar U)+
\lambda_d(1-Drift(T)).
\]

\[
R(UF)=1-\frac1K\sum_{j=1}^{K}|S(UF)-S(UF^{(j)})|.
\]

Use the ratified \(+Coh\) direction. \(S(UF)\) is not an eighth neuronal DSF
coordinate and no financial proxy may substitute for it.

## 6. MathLoom and balanced ternary

Preserve every rational fact \(x=n/d\) exactly:

\[
n=\sum_{p=0}^{P_n}t_p3^p,\qquad
d=\sum_{p=0}^{P_d}u_p3^p,
\qquad t_p,u_p\in\{-1,0,+1\}.
\]

Keep numerator, denominator, field family, topology, time, and locality
separate. Permit no rounding to sign, cross-field carry, scalar sum,
compatibility cell, semantic address, or hash-as-memory. \(3^p\) determines
exact positional significance only; it is not energy or importance.

## 7. Unified Krimelack/Psi fabric

Krimelack is the typed topological winding state of the same local oscillator
fabric represented by Psi. It is not a database or a second memory system.

For oscillator node \(a\):

\[
\psi_a=\sqrt{\rho_a}e^{i\phi_a}.
\]

A mounted three-node ring realizes a trit:

\[
w=\frac1{2\pi}\sum_{a=0}^{2}
wrap(\phi_{a+1}-\phi_a),\qquad \phi_3=\phi_0.
\]

- \(w=0\): \(\phi_A=\phi_B=\phi_C\).
- \(w=+1\): successive phase difference \(+2\pi/3\).
- \(w=-1\): successive phase difference \(-2\pi/3\).

Each exact typed MathLoom trit \(\tau_{qp}\) supplies a boundary constraint:

\[
E^{DSF}_{qp}=-\kappa_{qp}
\sum_{a\rightarrow b}
\cos\left(\phi_b-\phi_a-\frac{2\pi\tau_{qp}}3\right).
\]

Here \(q\) is the typed DSF fact and \(p\) its balanced-ternary position.
\(\kappa_{qp}\) is mounted material coupling energy derived from anatomy; it
is not computed from the DSF magnitude.

The complete local energy is:

\[
E_i=E_i^{material}+E_i^{DSF}+E_i^{law}+E_i^{contact}+E_i^{plastic}.
\]

Deterministic dissipative settlement is:

\[
\zeta_{\rho,a}\dot\rho_a=-\frac{\partial E_i}{\partial\rho_a}
+P_a^{physical}
\]

\[
\zeta_{\phi,a}\rho_a\dot\phi_a=-\frac{\partial E_i}{\partial\phi_a}
+\tau_a^{physical}.
\]

Without incoming physical power:

\[
\frac{dE_i}{dt}=-\sum_a
(\zeta_{\rho,a}\dot\rho_a^2+
\zeta_{\phi,a}\rho_a\dot\phi_a^2)\le0.
\]

This supplies deterministic settling and excludes free-energy recurrence. DNA
and mounted anatomy derive lattice size; sixteen is not a universal constant.

## 8. Law fields

A law field is a physical constraint-energy term:

\[
E_i^{law}=\sum_\ell U_\ell(\Psi_i,A_i,G_i).
\]

It may encode anatomical boundaries, material stiffness, phase adjacency,
channel mounting, conservation surfaces, and developmental geometry. It may
not encode developer-authored goals, words, meanings, preferences, action
scripts, safety overrides, labels, or scores.

## 9. Krimelack-to-membrane bridge

Krimelack winding never directly becomes voltage, current, energy, or an ion.
Each affected channel has a physical gate coordinate \(y_c\):

\[
U_c(y_c)=U_{0,c}(y_c)-q_cV_iy_c
-\sum_a\Lambda_{ca}y_c\cos(\phi_a-\phi^*_{ca})-\mu_cy_c.
\]

\[
\zeta_c\dot y_c=-\frac{\partial U_c}{\partial y_c}.
\]

Gate aperture geometry determines conductance:

\[
g_c=\frac{\sigma_cA_c(y_c)}{\ell_c}.
\]

Therefore the only authorized direction is:

```text
complete DSF -> exact ternary constraint -> phase settlement
  -> physical gate displacement -> conductance -> current
```

Derive \(U_0,q,\Lambda,\phi^*,\mu,\zeta,\sigma,A,\ell\) from mounted
virtual material, anatomy, DNA, and declared units. An underived value makes
that specialized path unavailable; it does not authorize a magic constant.

## 10. Membrane, material, fluid, and sparse coupling physics

For reached conductive path \(c\):

\[
I_c=g_c(V_i-E_c).
\]

Preserve fractional carrier remainder exactly:

\[
z_c=I_c\Delta t/e+r_c,\qquad
n_c=whole(z_c),\qquad r'_c=z_c-n_c.
\]

With reached active electrogenic transport \(n_{active}\):

\[
n_{membrane}=\sum_cn_c+n_{active},\qquad
Q'_i=Q_i-n_{membrane}e,\qquad
V'_i=Q'_i/C_i.
\]

Do not store a desired resting voltage. Rest emerges from conductances,
reversal potentials, charge, capacitance, pumps, and material state.

For chemical species \(s\) in compartment \(m\):

\[
\frac{dc_{s,m}}{dt}=q_{s,m}+\sum_jg_{s,jm}c_{s,j}
-\sum_jg_{s,mj}c_{s,m}-u_{s,m}(c_{s,m})-k_{s,m}(c_{s,m})
-\sum_rb_{s,r}(c_{s,m},x_{s,r}).
\]

Conserve receptor material:

\[
R_{s,r}+A_{s,r}+D_{s,r}=R^{total}_{s,r}.
\]

Derive sparse transport from mounted geometry:

\[
k^{diff}_{s,m\rightarrow j}=\frac{D_{s,mj}A_{mj}}{\ell_{mj}V_m},
\qquad
k^{drift}_{s,m\rightarrow j}=\frac{v_{s,mj}A_{mj}}{V_m}.
\]

Electrical neighbours interact through physical contact:

\[
I_{ij}^{gap}=g_{ij}(V_i-V_j).
\]

Axial propagation follows:

\[
C_m\frac{\partial V}{\partial t}=-\sum_cg_c(V-E_c)
+\frac{a}{2R_i}\frac{\partial^2V}{\partial x^2}+I_{external}.
\]

Chemical terminals conserve finite vesicle/material state:

\[
N'_{ready}=N_{ready}-N_{released}
\]

\[
N'_{cleft}=N_{cleft}+N_{released}-N_{uptake}-N_{degraded}.
\]

Fan-out divides or consumes finite physical quantity; it cannot duplicate an
emission freely. Changed neighbour membrane, receptor, body, or fluid state
becomes future evidence for that neighbour's unchanged L0-L4.

## 11. Depletion, recovery, plasticity, DNA, and familiarity

Refractory behaviour follows physical unavailability: inactive channels,
altered ion gradients, depleted vesicles, consumed ATP/material, receptor
desensitization, waste, and temperature. Recovery follows mounted reverse
reactions, pumps, diffusion, synthesis, circulation, nutrition, rest, and
sleep. It is not an arbitrary timer or firing cap.

For plastic element \(e\):

\[
\varepsilon_e=(x_e-\ell_e)/\ell_e,
\qquad
\sigma_e=\partial E_i/\partial\varepsilon_e.
\]

\[
f_e=|\sigma_e|-Y_e,qquad
f_e\le0,\quad \dot\lambda_e\ge0,\quad \dot\lambda_ef_e=0.
\]

\[
\dot\ell_e=\dot\lambda_e\,sign(\sigma_e).
\]

Elastic activity relaxes away; yielded plastic change persists. Chemical
plasticity and DNA expression use explicit conserved reaction networks. DNA
defines possible anatomy, specialization, expression, repair, and growth; it
does not issue semantic construction commands.

Familiarity is not stored as a score. It is the changed physical response
caused by retained deformation, resource state, receptor state, coupling
geometry, and recurrence.

## 12. L6 observation

L6 is a read-only joint-field topological observation. It does not modify DSF,
select meaning, force firing, create memory, or act as a neuron controller.

For the reached field's independent constraint operators:

\[
n_{eff}=n_{start}-rank\begin{pmatrix}C_1\\C_2\\\vdots\\C_m\end{pmatrix}.
\]

\[
\tau=1-
\frac{\Gamma(n_{start}/2+1)}{\Gamma(n_{eff}/2+1)}
\pi^{(n_{eff}-n_{start})/2}.
\]

Structural lock is geometrically possible only when:

\[
n_{eff}<n_{start}/e
\]

and the canonical active-manifold confinement condition also holds. Do not
replace rank with field-value thresholds or count arbitrary nonzero fields.

## 13. Exact neuronal fractal

Let \(q^-\) be the neuron's quiescent persistent state before an experience,
\(q^+\) its next post-experience quiescent persistent state, and
\(\Theta_i^{ret}\) its retained plastic state. Then:

\[
\boxed{\mathfrak F_i(E)=SparseExact[
\Theta_i^{ret}(q^+)-\Theta_i^{ret}(q^-)]}.
\]

The retained state may include exact changes to plastic Psi/Krimelack resting
geometry, persistent winding configuration, coupling rest geometry, channel or
receptor material, synaptic/terminal structure, persistent chemical/plastic
state, and DNA expression/developmental structure.

The pure transition emits only physical results:

\[
(\Delta\Theta_i^{ret}, electrical\ emissions, chemical\ emissions,
material\ consumption).
\]

After the physics boundary, minimal organism custody may bind neuron lineage,
causal interval, one reference to the complete joint DSF field and local
perspective, the exact sparse persistent delta, and physical emissions. Never
copy the complete field body into each fractal.

If \(\Theta_i^{ret}(q^+)=\Theta_i^{ret}(q^-)\), then
\(\mathfrak F_i(E)=0\). The neuron may have been active without retaining an
impression. A spike, DSF delivery, trit word, transient phase response,
recurrence count, or receipt alone is never a neuronal fractal.

## 14. Fractal-to-mosaic boundary

A cognitive mosaic may first become possible with at least three nonzero
fractals from three distinct neurons, but count never admits it. Also require:

- one shared or causally connected occurrence;
- physical/topological connectedness;
- retained rather than transient change;
- later collective recurrence or recognition;
- preservation of every neuron's distinct perspective; and
- exact bounded lineage and resource proof.

One episode may recruit sight, hearing, touch, smell, taste, vestibular,
proprioceptive, interoceptive, body, fluid-modulated, affective, and motor
neurons together. No modality is the master.

## 15. Resource law

Advance only the reached causal frontier:

\[
Work(E)=O(|N_E|+|C_E|+|R_E|),
\]

where \(N_E\) is reached neurons, \(C_E\) reached contacts, and \(R_E\)
reached reaction/channel paths.

Persistent neuron size is:

\[
Storage(\mathcal N_i)=O(|\Psi_i|+|K_i|+|\mathcal C_i|+
|\mathcal M_i|+|\Theta_i|+deg(i)).
\]

It does not grow with elapsed time or observation count. Physical DNA growth
may create new anatomy only from available material, causal developmental
state, and measured platform resources. Store current causal physical state,
not append-only tick or event history. Never poll the whole brain when the
causal frontier is known.

## 16. Historical-component disposition

- **Psi lattice:** retain; derive dimension from DNA/anatomy.
- **Spike buffer:** retain as bounded transient arrivals/emissions; derive its
  horizon from physical propagation and recovery, not a fixed depth of sixteen.
- **Couplings \(J_{ij}\):** represent as mounted electrical, chemical,
  mechanical, and material contacts with physical units.
- **Familiarity feedback:** remove as a scalar module; familiarity emerges.
- **Law fields:** retain only as physical constraint-energy terms.
- **DNA expression:** retain as causal developmental chemistry and geometry.
- **LoomNeuron:** software container only.
- **Trit register:** retain as physical winding readout.
- **DSF kernel:** retain unchanged as the complete structural delivery.
- **L6:** retain as read-only joint-field topology observation.
- **Balanced-ternary mathematics:** retain exactly.
- **Krimelack oscillator:** retain as typed winding state of the Psi fabric.
- **Sensory oscillator bank:** retain only where receptor anatomy mounts it.
- **Grandurun:** remove and prohibit resurrection.
- **Semantic spin-vector dimensions:** remove and prohibit resurrection.

## 17. Implementation and proof order

1. Replace or bypass false DSF-fractal constructors and prohibit their use by
   mosaics, recall, hierarchy, learning, or cognitive capital.
2. Implement one complete neuron genesis and exact quiescence with derived
   anatomy, units, and fixed current-state residency.
3. Implement the full DSF -> MathLoom -> typed phase constraint -> Psi/Krimelack
   settlement -> gate -> conductance -> membrane/material transition.
4. Implement physical depletion, recovery, plasticity, DNA expression, and the
   post-quiescence sparse fractal delta.
5. Prove one neuron under quiescence, one perturbation, opposition, persistence,
   recovery, cold restore, and long recurrence without age-dependent growth.
6. Prove three neurons with one sparse physical contact, conserved fan-in/out,
   distinct fractals, recurrence, and no automatic mosaic by count.
7. Prove four neurons with synchronous predecessor generation, bounded cycles,
   partial-cue reach, exact restart, and resource accounting.
8. Only then admit mosaics and higher cognition, mount the whole organism,
   rehearse the exact artifact, deploy, and live-verify.

Every proof must audit the pure physics path for owners, locks, databases,
digests, receipts, serializers, validation loops, Python callbacks, semantic
labels, dense scans, and hidden fallbacks. Such infrastructure may exist only
outside the neuronal transition where minimally required for I/O or atomic
current-state custody.
