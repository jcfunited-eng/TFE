# Speech acquisition and production: explicit mathematical candidate

**Status: proposed functional model, not a ratified law, implemented repair, learned utterance or production certificate.** Joe requested a mathematically grounded full speech loop with missing mechanisms supplied hypothetically and coefficients estimated where necessary. This replaces the previous rule-family overview. It specifies one candidate, including its engineered approximations, instead of concealing unspecified functions behind “learning signal.”

This candidate deliberately includes online prediction learning, an engineered intrinsic drive, adaptive control and reinforcement learning. It is not ML-free. These mechanisms would reside in native bounded state and existing 64-column routes; that placement does not make them non-ML. The particular equations below are proposals for review, not authorization to install them. Conventional deep-learning frameworks, pretrained linguistic models, dictionary answers and a Python cognitive owner are unnecessary for this candidate. No claim is made that the present passive yield law already implements it.

## 1. State, clocks and unchanged structural field

Let n index 10 ms frames, k index 1 ms native settlements and m index 16 kHz pressure samples. The present anatomy has 64 columns and 20,480 participants. X contains native phases, charges, apertures, contact state, body state and internal resource state. Additional bounded learning state consists of local temporal traces, prediction/contact coefficients, eligibility traces and the intrinsic learning need L.

For each physical source history H_n, retain the full canonical joint evaluation:

\[
F_n=\mathcal U(H_n)
=\{D_k,M_k,R_{rev,k},U_k^*,C_k,P_k,B_k;
S_{UF},\text{joint relations, source identities and chronology}\}.
\tag{1}
\]

U denotes the existing unchanged L0–L4 equations, not an invented learner. No reward or acoustic error replaces F. Current material facts_for encodes the seven ordered gate values; that alone does not establish participation of global S_UF and every required joint relation. **This model assumes that the separately required full-field delivery is repaired and qualified. It does not certify current delivery.** Defining a replacement DSF law is outside this speech proposal.

The native phase step retains its discrete-gradient form:

\[
\Gamma(\phi^{k+1}-\phi^k)/\Delta t
=-\overline\nabla E(\phi^k,\phi^{k+1};F,g)+f_{\rm active}.
\tag{2}
\]

The bar is the existing implicit discrete-gradient operator, not an Euler approximation. Relevant energy terms include:

\[
E_{ij}=\frac{\lambda_{ij}}2
[\sin\phi_i^r-a_{ij}\sin\phi_j^s]^2,
\quad
E_{\rm ring}=\sum_{\ell}\kappa_\ell
[1-\cos(\psi_{\ell+1}-\psi_\ell-2\pi d/3)].
\tag{3}
\]

The ring digit d is an exact retained ternary digit. Additional active inputs below are funded sensory/recall/control drives; they do not replace this transition. They require native mounting and physical/accounting validation.

Use x_i=sin(phi_i) as one bounded local phase coordinate. Each native learner receives only its declared connected coordinates, not a semantic label. Four temporal traces preserve different parts of recent context:

\[
z_{i,\ell,n+1}=\rho_\ell z_{i,\ell,n}+(1-\rho_\ell)x_{i,n},
\qquad \rho_\ell=e^{-h/\tau_\ell}.
\tag{4}
\]

Proposed tau values are 40, 160, 640 and 2,560 ms. These are engineered finite-memory filters, not a derivation of biological memory. A row's z vector contains its connected current coordinates, these traces and a constant coordinate. Measured body coordinates use declared instrument ranges for units. Sensor-range excursions are reported; full DSF input is not clipped to fit a predictor. Sparse row notation does not mean allocating a dense whole-brain weight matrix.

## 2. Actual prediction learning, not a guessed learning signal

Let y_j,n+1 be an actual subsequent sensory or connected-state coordinate. Before observing it, two local predictors issue forecasts:

\[
\hat y^f_{j,n+1}=p^f_{j,n}z_n,
\qquad
\hat y^s_{j,n+1}=p^s_{j,n}z_n.
\tag{5}
\]

After the next observation arrives, define epsilon^b=y-haty^b and update each connected row:

\[
p^b_{j,n+1}=\Pi_{\mathcal W_j}\left[
 p^b_{j,n}+\eta_b
 \frac{\epsilon^b_{j,n+1}z_n^T}{\varepsilon+z_n^Tz_n}
\right],\qquad b\in\{f,s\}.
\tag{6}
\]

Pi is projection onto the declared finite contact coefficient interval; it is an explicit engineering constraint. Proposed normalized limits are [-1,1] per coefficient, eta_f=.01, eta_s=.001 and epsilon=10^-6. Signed coefficients require native opponent/contact realization; they are not negative passive conductances. These are normalized least-mean-square updates: an ML-class adaptive rule, not established ArcLoom material physics. A row predicts future measurements from preceding native activity. There is no word/object identifier and no example-indexed answer entry.

## 3. An intrinsic need to learn, including while sated

Evaluate progress on the **same new outcome before either predictor updates**:

\[
\pi_{j,n+1}=
\frac{(\epsilon^s_{j,n+1})^2-(\epsilon^f_{j,n+1})^2}
{\varepsilon+(\epsilon^s_{j,n+1})^2+(\epsilon^f_{j,n+1})^2},
\qquad -1\le\pi_j\le1.
\tag{7}
\]

If a faster learner predicts later experience better than its slower reference, pi is positive. A large error alone is not rewarded. Smooth signed progress over tau_A=3 s:

\[
A_{j,n+1}=e^{-h/\tau_A}A_{j,n}+(1-e^{-h/\tau_A})\pi_{j,n+1}.
\tag{8}
\]

For a fixed, declared set of mounted prediction coordinates, let Abar be their mean; an unavailable coordinate supplies zero progress rather than a fabricated observation. Define [a]_+=max(0,a). A bounded learning need obeys the implicit update:

\[
L_{n+1}=\frac{L_n+h/\tau_{\rm seek}}
{1+h/\tau_{\rm seek}+h[\bar A_{n+1}]_+/\tau_{\rm satisfy}}.
\tag{9}
\]

Use tau_seek=60 s and tau_satisfy=10 s as initial design estimates. For L in [0,1], this update stays in [0,1]. Without learning progress L rises. Sustained progress reduces it. L is a motivational state, not joules, hunger or a DSF score. Eq. 7 is a candidate progress estimator, not a theorem of noise rejection: finite data, drift and representation errors can mislead it. Unlearnable-noise and mastered-task comparisons must therefore qualify it.

To close the startup gap, this candidate explicitly proposes bounded **innate exploratory excitation** at existing vocal motor input sites:

\[
\theta_{a,n+1}=\theta_{a,n}+h\omega_a(0.1+L_n),
\qquad
\xi_{a,n}=L_n\sin\theta_{a,n},
\qquad
I^{\rm explore}_{a,n}=0.01 I_{a,\max}\xi_{a,n}.
\tag{10}
\]

For ten direct functional voice controls, propose omega_a=2pi(0.7+0.11a) radians/s, a=0,...,9. These chosen frequencies are **engineered identification excitation**, not discovered word structure or a biological law. It is deterministic motor babbling, needs funded movement and must demonstrate adequate excitation at actual gate thresholds. This proposed exploratory controller requires review under the anti-heuristic contract; permission to discuss limited ML is not silent approval of it. Its explicit inclusion prevents the false claim that a silent, stationary system learns an instrument without ever exciting it.

This choice could be replaced by a qualified endogenous native exploration mechanism. Merely assuming that such exploration exists would reopen the chain gap; this document does not make that assumption.

## 4. Learning which native controls cause which sounds

Let u_n contain the ten actually applied, normalized native motor-input drives for the glottal, eight tract-section and respiratory routes. These are bounded currents entering native circuitry, not direct assignments to output/body positions. Let b_n contain actual body positions, pressure/flow/phase/resource state and recent drive traces. The local feature vector is m_n=[1,u_n,b_n]. A sparse native forward learner predicts internally sensed own acoustic features:

\[
\hat y^{\rm own}_{n+1}=B_nm_n,
\quad
B_{n+1}=\Pi_{\mathcal W_B}\left[
B_n+\eta_B
\frac{(y^{\rm own}_{n+1}-B_nm_n)m_n^T}
{\varepsilon+m_n^Tm_n}\right].
\tag{11}
\]

Take eta_B=.01 initially. The target is actual body-generated pressure passed through the same cochlear transform, an explicit internal acoustic/reafferent sense. It is not a teacher transcript, a desired waveform or the environment's food label. Ordinary external hearing still receives the actual acoustic mixture. This internal-sense mounting is a proposed repair, not a claim that every current caller provides it.

Current owner code uses a previous-quarter self-hearing FIFO, about 250 ms. The hypothetical repair hands each completed 10 ms native PCM block to the next auditory frame; 250 ms UI batching can remain a transport choice. No future sample is consumed. Body response still has its real dynamics, including the current roughly 32 ms actuator relaxation. Body state and recent drives in m carry that lag; Eq. 11 is an explicitly local approximation, not an exact universal acoustic model. Because u measures actual input drives, the fitted relation includes native input-to-gate-to-body response; a direct-body Jacobian is not silently reused as an input-current Jacobian.

## 5. The heard experience becomes a recurrent acoustic expectation

While the caretaker handles food and says the word, actual optical, acoustic, tactile, internal and motor activity jointly changes X. Equations 4–6 learn chronological associations. For the auditory rows, define the next recalled acoustic expectation:

\[
r_{n+1}=P^{\rm auditory}_n z_n.
\tag{12}
\]

Inject r through funded native association-to-auditory recall inputs: for each mounted recall coordinate use I_recall,j = I_max,j * projection_to_[-1,1](0.05*r_j) in the declared normalized acoustic units. The .05 gain is a design estimate. Opposed routes carry signed coordinates. That changes X and therefore z on the next frame; Eq. 12 then issues the next expectation. **The order is generated by recurrent state evolution**, not a stored sequence cursor. Earlier sound, context and lag traces distinguish successive positions even when the visual scene is similar.

This specifies the recall operation. It does not prove that the current 64-column representation separates all needed contexts or that one-step training is stable when internally continued. In the successful worked hypothetical, experience has fitted these rows sufficiently well that a partial cue starts a stable finite auditory trajectory, and the observed end of the demonstration supplies later silence. Long autonomous rollouts, not just one-step prediction scores, must verify that assumption.

No numerical list of the teacher's word is supplied as P. New predictor coefficients can start at zero; their actual learned values require real experience. Existing mature native state must be retained. An observer calls the trajectory “apple”; that string is absent from the pupil's dynamical state specification.

## 6. Recall recruits vocal controls rather than merely predicting sounds

From Eq. 11 take the local action Jacobian J_n=partial(B_n m_n)/partial u_n, holding currently measured body/history state fixed. It is the motor-drive-coordinate columns of B. Retain a bounded corrective drive c, initially zero for a newly introduced controller:

\[
e^{\rm sound}_n=r_{n+1}-B_nm_n,
\qquad
c_{n+1}=\Pi_{[-1,1]^{10}}[c_n+K_uJ_n^Te^{\rm sound}_n].
\]
\[
u_{a,n+1}=\Pi_{[-1,1]}\left[
 c_{a,n+1}+0.01\xi_{a,n+1}
 +\sum_j(w^H_{aj,n+1}+w^L_{aj,n+1})z_{j,n+1}
\right],\qquad I_{a,n+1}=I_{a,\max}u_{a,n+1}.
\tag{13}
\]

Propose K_u=.05 per frame in these normalized drive units. Pi enforces declared current limits; signed current is realized through opposed native input routes. These are the candidate's actual motor-input equations. Physical sensory and DSF inputs continue to act on the native substrate. Gates and funded circuit settlement determine actual efferent output. Eq. 13 is an engineered learned adaptive controller, not the current passive contact law. It is not a command such as “emit phoneme p” and does not bypass body dynamics.

For the fitted local model, no active saturation, unchanged concurrent drives and a sufficiently small correction Delta u=K_u J^T e, the first-order error-energy change is:

\[
\Delta\tfrac12\|e\|^2=-K_u\|J^Te\|^2+O(K_u^2).
\tag{14}
\]

Thus the direction reduces the predicted reachable acoustic error locally, subject to gain, delay and model accuracy. This is not a global convergence proof; exploration, recurrence, changing targets, native actuation thresholds and saturation can invalidate the simple descent inference for the real interval. A zero/singular Jacobian, unexcited control or unreachable sound prevents this argument from proving success.

A human recording need not be reproduced with identical pitch/timbre. The required result is a reachable, intelligible acoustic trajectory. Whether this particular instrument and learner can achieve that for “apple” remains an acoustic experiment; matching a scalar error alone cannot certify it.

## 7. Need fulfillment and social reinforcement change later behavior

Actual resource balance remains physical:

\[
E_{n+1}=E_n+E^{\rm absorbed}_n
-W^{\rm body}_n-W^{\rm neural}_n-W^{\rm learning}_n.
\tag{15}
\]

Let d_n=1-E_n/E_max for the body's admitted reserve range. The nutritional outcome signal and intrinsic outcome signal are explicitly:

\[
r^H_n=d_n-d_{n+1},
\qquad
r^L_n=hL_n\bar A_{n+1}/\tau_{\rm satisfy}.
\tag{16}
\]

The first is actual deficit relief, including actual expenditure. The second is an engineered learning-progress reward. Using these to improve behavior is **reinforcement learning**, including homeostatic RL for the nutritional component.

Maintain two native linear value readouts V^q_n=v^q_n z_n, q in {H,L}. Their prediction errors and bounded local eligibility are:

\[
\delta^q_n=r^q_n+\gamma V^q_{n+1}-V^q_n,
\qquad\gamma=e^{-h/(8\,{\rm s})},
\]
\[
e^V_n=\rho_e e^V_{n-1}+(1-\rho_e)z_n,
\qquad
v^q_{n+1}=\Pi_{\mathcal W_V}[v^q_n+\eta_V\delta^q_n e^V_n],
\quad\rho_e=e^{-h/(2\,{\rm s})}.
\tag{17}
\]

Both V terms use pre-update coefficients. Suggested eta_V=.01; coefficients have explicit finite limits (initial proposal [-1,1] in the declared normalized units). The value readouts forecast outcomes; no action list or word-valued payoff table is used.

For an existing motor-input contact j to a, retain the local exploration-participation trace:

\[
e_{aj,n}=\rho_e e_{aj,n-1}+(1-\rho_e)z_{j,n}\xi_{a,n}.
\]
\[
\Delta w^H_{aj}=\eta_w d_n\delta^H_n e_{aj,n},
\qquad
\Delta w^L_{aj}=\eta_w L_n\delta^L_n e_{aj,n},
\qquad\eta_w=.001.
\tag{18}
\]

These two proposed native contact components contribute to later motor-input current through their actual presynaptic activity. Hence earlier context/perturbation can become more or less likely to recruit the relevant native action. The trace has a 2 s decay time; it is a bounded participation estimator, not proof of counterfactual causation. Because excitation is deterministic and native dynamics are recurrent, this rule is **not claimed to be an unbiased policy gradient**. It is an explicitly approximate local reinforcement rule whose behavior must survive contingency controls.

For an illustrative stored trace e=.8, no further drive for 2 s leaves .8 exp(-1)=.2943. With d=.5, delta_H=.1 and eta_w=.001, Eq. 18 proposes Delta w_H=.000014715. This is arithmetic showing the delayed link, not a measured word-learning result. An isolated 10 ms event contributes only (1-rho_e)z xi to the normalized trace; .8 is an assumed pre-existing accumulated trace, not the instantaneous contribution of one pulse.

A caretaker response becomes **conditioned social reinforcement** when its actual sensed features predict subsequent nutrition or intrinsic learning progress. A smile/utterance can then raise V, and the resulting temporal-difference signal can reinforce the preceding attempt. The pupil is never supplied a “good job = +1” rule. Withholding or making the consequence independent of the attempt must weaken the acquired contingency in controlled comparisons.

This candidate supplies conditioned social reward, including potentially rewarding learning-related interaction while sated. It does not establish a separate innate social-attachment need, nor equate any unpredictable/contingent object with a person. Those are distinct capabilities and cannot be claimed from these equations.

## 8. Native gates, carriers, body and pressure

The preceding learned currents perturb native state. They do not directly produce audio. In existing output circuitry, for gate aperture y and resting aperture y0, let z=(y-y0)/(1-y0). Gate conductance is zero at/below rest and above rest has the current source form:

\[
G_g=\frac{N_g z}{R_{P0}+R_{A0}\sqrt z}.
\]
\[
V_m=q_m/C_m,\quad V_r=q_r/C_r,
\]
\[
\dot q_m=G_s(V_s-V_m)-G_g(V_m-V_r),
\qquad
\dot q_r=G_g(V_m-V_r)-G_lV_r.
\tag{19}
\]

Load charge is integrated, Q=integral G_l V_r dt. Whole carriers and the exact retained fractional remainder are separated by the canonical carrier representation. Opposed terminal counts change actual body activation. The current implementation applies previous-millisecond terminals, uses finite activation/body response and drives direct glottal/tract controls plus respiratory output. It does not receive a word name.

The native acoustic instrument uses actual excitation/flow and tract-dependent resonators. The representative recurrence for each mode is:

\[
s_j[m]=b_jv_j[m]+2r_j\cos(2\pi f_j/F_s)s_j[m-1]-r_j^2s_j[m-2],
\qquad F_s=16000.
\tag{20}
\]

Excitation v comes from funded native airflow/closure/turbulence, and f_j follows actual tract controls. Current implementation uses fixed-point coefficients, outlet/band limiting and signed 16-bit pressure; Eq. 20 explains the operator and is not a claim of exact real-arithmetic implementation. Five mode ranges are approximately 300–1200, 900–3400, 2500–4000, 4000–4800 and 5000–6000 Hz. These describe the current synthesizing instrument, not a stored pronunciation.

Current restrictions requiring separate qualification include respiratory admission only at a specific lung/rest condition, very narrow source fundamental-frequency range, and zero excitation at both extremes of the glottal-area expression. This model assumes that reachable excitation, interruption/release and spectral trajectories are established, with any necessary functional repair specified before claiming success. It does not invent a successful actuator path through those restrictions.

## 9. Actual sound returns through actual hearing

For each auditory band, with four cascaded stages, the cochlear recurrence is:

\[
c_{b,j}[m]=a_bc_{b,j}[m-1]+(1-r_b)c_{b,j-1}[m],
\quad
 a_b=r_be^{i2\pi f_b/F_s},
\quad r_b=e^{-2\pi(1.019)ERB_b/F_s}.
\tag{21}
\]

The first stage receives actual pressure. Each 10 ms block yields measured amplitude and continuing phase. These real observations supply Eq. 1, prediction residuals in Eqs. 6–7, own-action residuals in Eq. 11 and subsequent vocal correction in Eq. 13. Actual listener/caretaker responses return through ordinary environmental senses and Eq. 17. The world can also change physically: eating consumes food and changes reserve; a changed reward value cannot substitute for that transition.

A recalled trajectory that includes its learned termination returns toward silence; native body relaxation removes excitation. There is no fixed word-duration timer. Continued exploratory excitation remains separately bounded and must not prevent utterance termination or quiet behavior; this is a required system test, not a benefit guaranteed by Eq. 10.

## 10. Consolidation and paid, retained adaptation

For the new adaptive coefficients only, propose two stores w=ws+wf. Acquired updates enter wf. During an existing native sleep/quiescence condition, use:

\[
\alpha=1-e^{-h/\tau_c},\qquad
w_s' = w_s+\alpha w_f,\qquad
w_f'=(1-\alpha)w_f,\quad\tau_c=600\,{\rm s}.
\tag{22}
\]

The sum is unchanged at transfer. A proposed 1-hour decay time applies to unconsolidated wf; ws does not receive that decay. Thus consolidation improves durability, not magically pronunciation quality or the quantity of experience. These stores are independent of the fast/slow prediction comparison in Eq. 5. Existing mature memory is not retroactively reclassified into a decaying pool. Interference, wrong-memory consolidation and finite capacity remain real limitations.

Equations 6, 11, 17 and 18 propose **active adaptive writes**, not the present passive yield return. For a candidate dimensionless contact change Delta a with contact energy Eq. 3, one conservative bookkeeping proposal is:

\[
W_{\rm write}=[E(a+\Delta a)-E(a)]_+
+\lambda Y|\Delta a|,
\]
\[
Q_{\rm heat}=W_{\rm write}-[E(a+\Delta a)-E(a)]\ge0.
\tag{23}
\]

Here lambda Y has energy units as in the contact plastic dissipation expression. Existing supply funds the write; insufficient supply defers it without pretending it occurred. This preserves an energy balance but **does not derive a physically realizable programmer, prove the old yield inequality admits the commanded change, or prove a transistor implementation**. An active adaptive-contact extension needs explicit architectural approval and native design. Energy bookkeeping alone cannot convert an arbitrary optimizer into ratified material physics. That hardware/constitutive mapping remains a named engineering qualification boundary of this functional hypothesis, not an implemented solution.

All newly added coefficients, traces, oscillator phases and counters must enter the canonical checkpoint and continue identically after cold restore. No sidecar memory owner or mature-state reset is permissible.

## 11. What the worked “apple” result would mean

Starting from preserved native state and initially untrained new predictors: Eq. 10 excites real vocal movement; Eq. 11 learns actual acoustic effects. Caretaker demonstrations and concurrent object/body/context experience train Eqs. 4–6. A partial contextual/need cue later activates Eq. 12, whose recurrence produces a time-varying acoustic expectation. Eq. 13 recruits the learned native controls; Eqs. 19–21 generate and hear actual pressure. Actual food relief and caretaker responses update Eqs. 16–18. Eq. 22 makes admitted learning more durable.

If that learned, closed trajectory is intelligible to independent listeners as “apple,” and appears appropriately under changed contextual/need conditions, the model has achieved the worked target. No particular learned coefficient values, successful training trajectory, recording or human-listener result is fabricated here. The equations alone cannot establish that the proposed representation, exploration and local credit rule converge to that result. This is a specified candidate to falsify, not a proof of attainable performance in today's source.

A single word does not demonstrate syntax. The same retained recurrent mechanisms are candidates for longer relational sequences, but composition and transfer to unseen combinations need their own evidence. Calling those results inevitable would repeat the original overclaim.

## 12. Bounds, source integration and acceptance

Set a proposed **additional learning-state budget**, for example 262,144 contact records at 64 bytes = 16 MiB, plus explicitly counted bounded sensory/history buffers. This is an initial engineering budget, not a measured requirement or sufficient-capacity theorem. All predictor, critic, motor and consolidation coefficients count toward it; it is not a separate allowance per mechanism. Existing native state/contact history is preserved. Capacity exhaustion is reported; no unrecorded pruning, digit truncation or state reset occurs.

For fixed admitted learning contacts E_L and feature traces N_L, each frame's proposed learner costs O(E_L+N_L); sensing/voice and native implicit settlement have their own costs. The current geometry exposes 86,507,520 raw slot addresses, many not mounted. Allocating traces over every raw address would contradict a claim of a small addition. Native solver cost and frame latency remain independently measured constraints. Constant memory is finite capacity, not unlimited knowledge.

The single A1/G1 item remains closing and qualifying this speech-learning loop under A09/A10/D09 within the OPEN reconciliation. Integration boundaries: functional64_source.rs and joint_uf_vector.rs for full actual source custody; functional64_geometry.rs for mounted routes; functional64_material.rs and functional64_contact.rs for native learning/current/write laws; functional64_owner.rs for causal audio timing and checkpoint ownership; virtual_articulated_body.rs and virtual_articulatory_body.rs for actual controllability/pressure. These are destinations requiring source-bound design, not permission to alter them now.

Qualification proceeds specification/design, unit, module, system and production in that order. Decisive checks are: sated unattended exploration and learning; mastery versus learnable change versus unpredictable noise; identified action-to-acoustic delay/gain/rank; sustained recalled acoustic rollout; delayed contingent versus independent outcomes; appropriate need and social-context changes; actual independent intelligibility; quiet termination; cold retained continuation; measured resource and latency bounds. Source/package inspection must also exclude word lookups, semantic reward flags, pupil TTS and retired cognitive owners. No such new product tests ran in this documentation revision.

The foundational research supports the mechanism families, not this particular architecture or parameter set: [Oudeyer, Kaplan and Hafner on learning-progress motivation](https://www.pyoudeyer.com/ims.pdf), [Bellec et al. on local eligibility and learning signals](https://www.nature.com/articles/s41467-020-17236-y), and [Keramati and Gutkin on homeostatic reinforcement learning](https://elifesciences.org/articles/04811). Eq. 18 is the explicitly described candidate here; it is not claimed to reproduce e-prop's exact derivation.
