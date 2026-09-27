# P0 review and corrective implementation contract

**A1 · 2026-09-27 · COG-OSC-02 / P0 · Documentation correction, not a release**

Reviewed artifact: `82d6cf26f:docs/GUALA_P0_BIOFUNCTIONAL_CAUSAL_CONTRACT_2026-09-27.md`,
SHA-256 `9430d8d70f08429a9100f8f9c6ca539f39151656651df30d4fcc9171f93497c6`.
Parent [implementation plan](GUALA_BIOFUNCTIONAL_PLANNING_IMPLEMENTATION_PLAN_2026-09-27.md)
SHA-256 `4fec055563795bf7a29cbdc883ea9f43586096742b0774468f16ff9f76b6e37e`.

## Verdict and authority gate

**Do not promote this P0 draft to P1 decision-authority implementation.** Its
boundaries are useful, but its seven headings are not seven completed
constitutive derivations. Several claims are mathematically false, several
inputs are not mounted, and the prediction/learning realization remains absent.
The corrections below replace those claims for this handoff. They do not claim
that the missing neuronal specialization has been implemented or derived.

- Requested architecture: the parent's sparse, persistent, experience-grown
  cognition through the definitive neuron and unchanged joint L0–L4 delivery.
- Current reality: the reviewed source remains the functional organism/loop.
  The P0 file describes future mechanisms, not active native cognition.
- Conflict with requested architecture: **yes**, including in P0 itself.
- Not extended: semantic participation switches, scalar consequence or support
  scores, borrowed ArcLoom potentials as Guala neuron law, arbitrary neural
  quotas, world-oracle prediction, or reset-and-replay migration.
- Single next item: G1 supplies the source-linked, unit-complete local-learning
  specialization described in §5; review it before implementing new authority.
- Evaluation: source and constitutive-contract review, not full-field execution.
  Existing reduced decision keys omit joint-field relationships; this review
  performs no neuronal transition and certifies no full-field cognitive result.

At review, the working P0 file was zero bytes and modified relative to the
commit. That concurrent change was preserved, not overwritten or attributed
to a particular author. This separate correction document is based on the
authenticated committed artifact. The empty working file is not a valid frozen
contract and must not be committed as the replacement.

## 1. Findings and necessary corrections

### P0-A1-01 — The source-linked mount contains invented or misidentified inputs

The following is source reality, not a request to enlarge sensory scope:

| Draft claim | Inspected producer / consumer reality | Corrected contract |
|---|---|---|
| 405 retinal sites plus focal crop; photon flux `[0,1]` | `guala_functional_loop.py` declares 27 legacy + 108 wide **sites**; 405 is their RGB-value count. Focal field is 160×120 sites. `Sensed.focal_luminance_u8` carries the existing quantized presentation; the loop supplies RGB focal values despite the historical name. | Preserve exact arrays, dimensions, gains, saturation provenance and source clock. Do not rename dimensionless byte intensity photon flux. Physical flux requires a separately specified calibrated conversion and units. |
| 32 cochlear channels **per ear**, in Pa | `guala_cochlea.py` declares 16 per ear, 32 total, 16 kHz PCM and 4,000 samples per hop. Its input normalization is `sample/32768.0`. | Document actual envelope construction, frame times and scaling. Signed PCM or normalized amplitude alone does not establish an SI pressure calibration. Do not invent Pa. |
| Native measured position/rate from 45 articulated axes | `BODY_AXES` has 45 declarations including eight tract-area entries. `body_axes` overlays head/eye/eyelid positions; this is not 45 measured force-driven joints or velocities. | Distinguish declared posture from measured mechanics. The separate functional-body candidate is not production-mounted or qualified. |
| Full contact force, shear and vestibular afferents in `Sensed` | Its declared channels include skin contact fraction and temperatures, not the draft's full normal/shear force and gyro channels. | Missing channels remain unavailable. Consume the body candidate's actual `BodyFeedback` only after joint producer/consumer integration is accepted. |
| Thermal flux in mK | mK is temperature, not heat flux. | Name temperature correctly. Heat transfer requires its own measured energy/rate/area and units. |
| Turn limit is 45,000 mdeg | `guala_functional_organism.py` currently declares `TURN_MILLIDEGREES = 60_000`. | Bind limits to the actual supported effector source, not a narrative value. This is not approval to change that source. |
| Command classes directly actuate native jaw/grip apertures | `GraspContactCommand` and `ReleaseHeldObjectCommand` carry duration only; `OralContactCommand` carries an object ID and duration. | Describe actual command semantics. Future neuronal output must use a body-local actuator/contact interface; world custody may resolve an object internally, but its ID must not become learned recognition. |

`Sensed.snapshot` currently carries world observation data, and the existing
organism reads coordinates and IDs from it. Merely drawing a receptor-only
arrow does not remove that exposure. The new cognitive boundary must enumerate
the exact permitted inputs and have no transitive access to the snapshot/world
inventory. Keep geometry needed for rendering, collision validation and custody
outside neuronal decision authority.

The body precursor's `LocalContact` is link-local position in metres, force in
newtons and couple in newton-metres; `BodyFeedback` carries only instrumented
sensors and anatomical contact surfaces. Do not substitute world-frame poses,
hidden contact identities, or an unavailable area/shear channel.

**Correction:** replace §2.2/§3.1 with this measured-availability distinction and
a producer → conversion → consumer call map. No new body channel is authorized
by this document. Cognition may start with existing lawful inputs; it must not
pretend the unmounted precursor is already available.

### P0-A1-02 — Joint DSF delivery is named, not specified

P0 lists seven fields and then bypasses the full bridge in its diagram. Its
claim that `k` is a 250-ms sample stride also conflates gate index and actor beat.

**Correction:** preserve the complete authoritative chain:

```text
unit-bearing physical evidence + source time + sparse mounted contacts
  -> derived joint UF coordinates and explicit joint relevance
  -> unchanged joint L0-L4, once per applicable joint occurrence
  -> shared complete result + local perspective
  -> exact MathLoom -> typed Psi/Krimelack constraints
  -> physical settlement -> gate -> conductance -> membrane/material return
  -> local retained plastic change
```

Provide the actual source entry points for each arrow, including UF coordinate
adapters for incompatible raw units and joint `r(t)`. A vector of raw pressure,
temperature and force cannot enter a Euclidean norm without that derivation.
Keep `S(UF)` separate from local L4. A tuple of seven latest values is not the
complete shared field result. The definitive-neuron skill supplies the
architecture; absent executable mount/adapters remain absent. Do not change
canonical kernel equations to fill this gap.

### P0-A1-03 — Eligibility is an underived scalar reinforcement rule

The draft assigns `tau_elig = 1.50 s`, `alpha_elig = 1.0`, a Boolean
`Pi_e(action,sensation)`, and `Delta ell = eta*z*Delta Phi`. It neither defines
the physical species/charge of `z`, nor derives those constants or the units
of `eta`. Nutritional energy, contact stress and vestibular shock cannot share
an untyped consequence intensity. This is not completed physical plasticity.

The cited experiment found a roughly 0.3–2-second dopamine-sensitive window in
the studied striatal-spine preparation; it does not derive Guala's 1.50-second
decay constant, tactile/metabolic transit, or six-beat clock window.
[Yagishita et al., 2014](https://pubmed.ncbi.nlm.nih.gov/25258080/).

**Correction:** participation must arise from the actual reached contact's
electrical/chemical/material changes. Specify its finite precursor, active and
recovery quantities; conserved transfers; local reaction/transport rates with
units; and how separately typed arriving consequences alter that contact.
Reuse mounted charge/carrier and finite-material laws where present. If a
specialization is missing, derive and review it; do not fill it with the Boolean
motor label or an arbitrary decay. No new coefficient is approved here.

Also correct the claim “unexecuted pathway implies zero plasticity.” A sensory
or internally active contact can physically change without an external motor
action. **An unexecuted action must not be recorded as an executed trial**;
that does not imply every participating sensory/prospective contact is frozen.
The negative control must be an otherwise matched, causally unreached contact,
not any neuron associated by the programmer with the losing action.

### P0-A1-04 — Predictor and plastic update are still unspecified; work has wrong units

`P_theta(s,u)` remains a function name. Complementarity constrains admissible
yield but does not determine the loading response, plastic multiplier, new
rest geometry, or predictor output. P0 supplies none of that realization.

The draft defines strain dimensionlessly and `sigma = partial E/partial strain`.
If `E` is energy in joules, this derivative has units **joules**, not pascals.
Multiplying its yield threshold by a reference-length increment gives J·m,
not plastic work. If `Y` were stress in Pa instead, Pa·m is still not joules.

**Correction:** specify work-conjugate coordinates before numerical updates.
For a length coordinate `ell [m]` and actual stored energy `U [J]`, its driving
generalized force is `F_pl = -partial U/partial ell [N]`, and dissipated power
from that coordinate is `F_pl * dot(ell) [W]`, subject to the derived material
law and sign condition. If using physical stress and plastic strain instead,
the power is volume × stress × plastic-strain rate. These are dimensional
accounting identities, **not a replacement constitutive law or chosen material**.
Apply the required chain rule to the definitive model's variables. Account for
stored-energy changes, incoming work, dissipation and chemical/material
reservoirs without charging the same expenditure twice.

For the predictor, identify the actual retained contacts, preparation inputs,
local transition equations, output transducers and their physical availability.
Record prediction before successor observation. Align corresponding channels
and time; absent evidence is not zero. Do not require every successful movement
to reduce error monotonically: success and prediction accuracy are different
measurements. Use matched retained-state and disconnected-coupling controls.
Below-yield mismatch need not produce plastic change; above-yield trial stress
must settle to an admissible updated state, not finish with `f > 0` while
claiming the yield invariant holds.

### P0-A1-05 — The imported attractor does not provide the claimed need termination

The cited `docs/dsf_ai_agnostic_overleaf/main.tex` places the sixth-degree
potential under **historical ArcLoom** dynamics and explicitly says the
coefficient family is explanatory, not newly chosen physical material. P0
incorrectly promotes it into the definitive Guala neuron.

There is also a direct counterexample to the proposed satiety argument.
Take its allowed uncoupled case, remove drive, and use

\[
V(x)=ax^6-bx^4+cx^2,\quad c=2b-3a,\quad a>0,\quad 3a/2<b<3a.
\]

Then

\[
V'(\pm1)=0,\qquad V''(\pm1)=8(3a-b)>0,
\quad V''(0)=4b-6a>0.
\]

Thus the nonzero stable minima **remain when drive is zero**. Turning off a
bias does not prove their collapse. Gradient descent does not guarantee one
minimum, distractor recovery, or a universal settling time. With changing
drive/couplings, the energy derivative additionally includes their supplied
work; the fixed-potential inequality alone is insufficient.

**Correction:** remove this potential as newly authorized neuron law and remove
the claimed automatic collapse. Use the definitive neuron's mounted recurrent
contacts, receptor/material availability, recovery and power balance. Derive
the actual bodily-to-local physical coupling. Prove persistence, interruption,
appropriate resumption and outcome devaluation from that same law. Keep
retained knowledge when a need is satisfied; cessation of current pursuit is
not deletion of the memory basin. Do not replace the false proof with a new
hand-picked polynomial or `deficit > 0.6` behavioral switch.

### P0-A1-06 — Differential equations do not make a score selector non-scalar

The proposed motor equation subtracts scalar risk from scalar support through
an unspecified activation function/gain. Calling `beta` a conductance does not
make `beta*A` a compatible current, voltage or activation. The draft does not
derive the couplings or thresholds. It does not guarantee a single winner:
identical paths under identical input/initial state remain identical under a
unique deterministic symmetric evolution. A 50-ms deadline cannot fix that.

**Correction:** implement competition only through mounted, unit-bearing local
contacts and finite reservoirs in the approved substrate. Physical asymmetry
must come from anatomy, state or experience, not list order or injected noise.
Derive the effector coupling and incompatible-command boundary. If competing
paths remain unresolved, do not fabricate a winner or claim `rest` is neuronal
quiescence. Specify what previously committed actuation physically continues,
ceases or dissipates under its existing body contract while sensing continues.

Remove immediate-distance reduction as a universal cognitive gate only when
the replacement authority is qualified; do not delete the live controller's
dependency in this documentation task. Necessary detours must pass ordinary
collision and body-limit validation. This does not authorize scalar support
ranking under another name.

### P0-A1-07 — Prospective activity needs actual dynamics and physical time

`F_recurrent(x_imagined,u_hat)` does not define recombination. A provenance flag
does not supply a physical mechanism that prevents hypothetical motor output.

**Correction:** identify which previously retained contacts participate, the
actual internal reactivation and inhibitory effector path, and the material
cost of that activity. Provenance records are external custody/evidence, not a
semantic selector inside the neuronal law. Imagined food must not debit a world
object, increase reserves or record a successful real action. However, thinking
itself occurs during the organism's real elapsed intervals and consumes
resources. It must not freeze the body/world clock. Hypothetical projection
steps neither manufacture extra physical ticks nor replace ongoing physical
time. No copied omniscient world, cloned brain, or supplied answer sequence.

### P0-A1-08 — Reset-and-replay is not a demonstrated memory-preserving migration

Initializing quiescent neurons and replaying assumed historical sensory pairs
does not preserve learned capability merely because the organism ID survives.
Existing counters/dictionary records are not complete recorded stimuli or
definitive neuronal state. The draft supplies no source inventory proving that
the proposed replay evidence exists. Nor is `last_refusal` intrinsically bogus:
an actual refusal can be genuine evidence even if its old selection rule is
wrong. Blanket cache deletion can erase useful history.

**Correction:** enumerate actual persisted fields and distinguish authentic
experience, derived selector caches, current physiology and unavailable state.
Preserve the original pair and historical evidence without relabeling it neural
plasticity. Demonstrate any lawful conversion on an isolated mature pair and
prove retained causal capabilities after fresh restore. An archive alone is
not functional recall. If exact conversion is unavailable, disclose the gap;
do not claim preserved learning, initialize it silently, or replay synthetic
stimuli reconstructed from labels. Any development/reconditioning phase needs
explicit provenance, resource/clock treatment and architectural approval before
cutover. No second live writer or silent fallback brain is authorized.

Quiescent fractals refer to complete-neuron pre-experience and next
post-experience quiescence, **not automatically a sleep/wake boundary or a
deployment event**. Migration is not itself proof of a new neuronal fractal.

### P0-A1-09 — Resource and frame assertions are stronger than their evidence

`N_r <= 2048`, `C_r <= 8192` and 50-ms settling are not derived from mounted
anatomy or measurements. Sparse per-pass cost does not imply that an entire
nonlinear settlement, integration, serialization and commit is linear or fits
250 ms. Physical time and CPU duration are different quantities.

**Correction:** remove these numbers as cognitive laws. Measure reached neurons,
contacts, reaction paths, solver work, native/transport/commit wall cost, peak
memory and retained bytes on the actual release shape. Derive operational
admission limits from that evidence. Operational failure stays outside physics:
no partial-state commit, invented rest/learning, dropped reached contact or
skipped real time reported as success. Long thought can span ordinary intervals
while the body continues; do not require every objective to settle in one beat.

The general frame relation in the draft is useful as a world-side test oracle:

\[
x_B=R_{WB}^{T}(x_W-p_{WB}).
\]

But `Delta retinal yaw = -Delta proprioceptive yaw` is a restricted pure-rotation
case, not general 3D motion. Eye/neck/body rotations compose; translation and
depth cause parallax. Gaze compensation and retinal quantization also matter.
A moving target can move along the viewing ray with unchanged bearing, and
occlusion can remove evidence. Therefore `epsilon_bearing = 0` does not prove
the target is stationary, nor does a nonzero residual uniquely prove target
motion rather than model error or unobserved self-motion.

**Correction:** distinguish (a) the ideal geometric test, with exact independent
world-side ground truth, from (b) the learned sensor-only prediction and its
producer-derived uncertainty. Include an unchanged-bearing moving-target
control and missing-evidence case. An unobservable distinction remains
indeterminate; do not solve it by leaking world poses or adding an arbitrary
similarity tolerance.

## 2. What remains valid and should be preserved

The separation of organism from environment, no hidden scene rollout, unchanged
L0–L4, typed actual-versus-prospective evidence, ordinary-loop consequence return,
single-writer persistence and body-worktree separation are the right boundaries.
Keep them. The need for delayed causal linkage, prediction, recurrent state and
competition is justified by the parent's research; the papers do not certify
these particular equations, constants, source mounts or migration.

No scalar variable is forbidden merely for being scalar: charge, temperature,
energy and conductance are lawful physical quantities. The objection is using
an underived scalar **utility/decision proxy** in place of the preserved physical
field and its actual material transitions.

## 3. Corrected disposition of the seven P0 rows

| Required row | Current disposition | Concrete completion evidence |
|---|---|---|
| Sensory/efferent mount | Source corrections supplied above; end-to-end neuronal mount missing | Exact producer/read path, units, frames, clocks, lawful coordinate/relevance adapters and compiled consumer; absent channels explicit |
| Eligibility | Underived draft rule withdrawn | Complete local finite-material/charge state, physical participation, rate/coupling derivations and conservation |
| Prediction | `P_theta` remains notation, not implementation | Actual sparse local transitions and output path; prediction preceding consequence; causal retained-state controls |
| Persistence | Borrowed potential and collapse claim rejected | Same-law persistence/interruption/devaluation with accounted power and retained knowledge |
| Recombination | Function name/provenance promise insufficient | Retained-contact reactivation, internal-only output inhibition, real time/material cost and novel-use witness |
| Effector selection | Scalar support/risk and deadline rule rejected | Unit-bearing competition/actuation, physical unresolved behavior and no order-based winner |
| Lifetime continuity | Reset/replay proposal not qualified | Actual field inventory, lawful transformation or explicit limitation, capability retention, fresh restore and compatible recovery |

## 4. Corrected minimal falsifiers — specify now, execute after law review

Use the parent's existing C-tests; do not add another large regression suite
before the constitutive law exists.

- **Local eligibility:** participating versus physically disconnected otherwise
  matched contacts; actual delayed consequence delivered through the mounted
  path; full material/energy accounting. Do not force nonzero plasticity below
  yield or use an action name as the eligibility source. Sensory-only activity
  must not be falsely counted as an executed motor trial.
- **Prediction:** capture a learned prediction before actuation, then compare
  actual successor channels. Test both collision refusal and successful but
  unexpected movement. Ablate only the relevant retained physical structure.
  Do not inject an expected 300-mm prediction or force stress above yield.
- **Persistence/termination:** bounded distraction, restored actual demand,
  outcome devaluation and learned memory reuse. Include the zero-bias stable
  minimum counterexample above to prevent reintroduction of the false proof.
- **Frame/observability:** independently vary observer rotation/translation,
  target motion and visibility; keep world ground truth out of the consumer.
  Distinguish mathematically observable cases from ambiguous ones.
- **Continuity/cost:** fresh paired restore of retained state, no imaginary
  physical consequence, no partial commit, measured reached-frontier resources.

## 5. Exact next G1 item and stop condition

**Complete one local-learning specialization packet, not a whole new planner.**
Use the corrected source map and the definitive-neuron equations to specify one
reached sensory/motor/contact path: anatomy and finite state, units, shared
field/perspective input, real local participation, material update/return map,
incoming/outgoing work, retained delta, prediction readout if supported, and
cold-restore representation. Every coefficient must point to a ratified material
specialization or a unit-bearing derivation submitted for review. A missing
coefficient or local transition must remain an explicit derivation task, not
be filled by `1.0`, six beats, `tanh`, or a citation alone.

Submit that bounded packet before executable P1 authority. Do not implement
the rejected P0 equations while awaiting review; do not wait for the articulated
body, redesign speech, or restart broad behavioral trials. Production and live
care remain unchanged. This is an engineering completion step, not a claim
that cognition is impossible and not a declaration that the seven rows are now
complete merely because this corrective document exists.

## 6. Verification and evidence limits

Review used current source definitions, the frozen commit, the parent plan's
§6.5, the definitive-neuron/cognitive-chain/DSF skill authorities and the primary
R2 research. The older cognitive-law repository mirrors remain absent in this
checkout; their skill-local authorities were read, not fabricated as files.

Source fingerprints rechecked during review:

| File | SHA-256 |
|---|---|
| `guala_functional_organism.py` | `10e23e1a7eb169b6b5b03995a857b55183d718788787e01cdc8735984d10e08c` |
| `guala_functional_loop.py` | `505f2d1ed231cfc3b5ada0757bc05618db05092fdb067d9452546b1fdf347a9c` |
| `guala_cochlea.py` | `89211d30601a6d70b373b4446f4bd1ce0361de089c640e81bd52f7a4de218aed` |
| `episodic_binding_engine.py` | `dda3b1be483a0867a61f277b84b7d723beda63d05791584fc0a59b3f3590bb37` |

No cognitive code, kernel, production image, live state, caregiver process,
body interface or test acceptance threshold was changed. No organism suite
was run for this review. The separate functional-body diagnostic already in
flight belongs to FB-01aj and provides no evidence of cognition. A1 returns to
that active body objective after this handoff; G1 retains cognition ownership.
