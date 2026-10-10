# Reconstructive memory — research foundation

Date: 2026-08-05
Status: **RESEARCH ONLY. Nothing implemented. Nothing committed. No production change.**
Tree studied (read-only): `/tmp/guala-production-15a7dca9`, HEAD `615110cb` plus the
uncommitted stimulus-boundary working tree.
Charge: Joseph Forrester, 2026-08-05 — *research before design.*

> "Immutable anything is not true... there is a moment in time that is preserved
> that has fragments of truth but the memory is not immutable — I have to THINK
> about it to reconstruct the moment, and it's a process of things that have been
> reinforced over and over experiences, or the conscious act of remembering...
> unknown uncertainty to certainty to uncertainty."

## What this document is, and what it is not

It is the evidence base the owner required *before* design: a full reading of the
in-tree IRF spec, and an external review of established memory science, with the
owner's three claims adjudicated against both.

It is **not** a design. `docs/GUALA_RECONSTRUCTIVE_MEMORY_DESIGN_STUDY_2026-08-05.md`
(same date, in-tree) already proposes laws R1–R5. This document deliberately does
not restate that design. Where the research bears on it, §6 says so explicitly and
marks each finding **CONFIRMS**, **EXTENDS**, or **CHALLENGES**. Two findings
challenge it. That is the point of doing research after a design study rather than
only before one.

It is also not a code audit, but every substrate line cited below was opened and
verified in this session rather than inherited.

---

## 1. The charge, decomposed into three testable claims

The owner's statement contains three separable claims. They are not equally well
supported and they should not be ratified as one package.

| # | Claim | Testable form |
|---|---|---|
| **C1** | Memory preserves **fragments** of truth, not the moment | What persists is partial and structural, not a complete record of the episode |
| **C2** | Remembering is a **reconstructive process** — conscious effort re-deriving the moment — strengthened by reinforcement across repeated experience *and* across recall | Recall is computation over fragments plus prior structure, not readout; and the act of recall itself alters and strengthens what is stored |
| **C3** | Memory follows **uncertainty → certainty → uncertainty** | Confidence/precision about a remembered episode rises then falls, and the fall is intrinsic rather than caused by damage |

C1 and C2 are settled science. C3 is supported but the owner's phrasing needs one
correction, given in §4.3.

---

## 2. Source 1 — the IRF spec, read in full

`Information_Resonance_Fields_and_Premonition__Like_Inference_in_High__Dimensional_Histories__A_Theoretical_Framework.pdf`
(10 pp., pdfTeX, 2025-12-18). Read completely, all sections plus glossary.

### 2.1 What authority this paper can carry

The paper self-labels as a **"(Speculative Concept Paper)"** on its title page, and
§9 states its own limits without hedging: *"No concrete, physically grounded
definition of the IRF or its dynamics is provided; the field is treated
phenomenologically"*, and *"for engineering applications, the IRF is approximated
by data-driven modes; the 'premonition' aspect becomes 'early pattern detection'
rather than anything nonlocal."*

This is decisive for how the paper may be used here. **The IRF supplies shape, never
authority.** No substrate law may be justified by "the IRF says so." What the paper
legitimately provides is a vocabulary and a set of formal objects for talking about
memory as modes-and-amplitudes rather than records-and-lookups — and §7 of the paper
explicitly invites exactly that reuse ("even if no literal IRF exists, this framework
inspires design principles").

### 2.2 Complete formal inventory

| Object | Definition (paper's own notation) | Section |
|---|---|---|
| History space | `Ω` with prior measure `µ₀`, `∫Ω dµ₀(ω) = 1`; in a deterministic universe `µ₀` represents *the agent's ignorance*, not the world's randomness | §2.1 |
| Event / feature vector | `φ(Eᵢ) = (tᵢ, xᵢ, actorsᵢ, typeᵢ, affectᵢ, …) ∈ ℝᵈ`; **time is one coordinate among many**, not a privileged axis | §2.2 |
| Conscious states | ordinal sequence `C = {C₁, C₂, …}`; *"the index n denotes order of experience, not necessarily clock time"*; representational vector `vₙ ∈ ℝᵏ` | §2.3 |
| The field | `M(x,t) = M_ret(x,t) + M_adv(x,t)`, sourced by events via `J(x,t)`, with retarded and advanced Green's functions and coupling `α ≪ 1`; `α = 0` recovers standard causality | §3.1 |
| Epochal eigenmodes | `M(x,t) = Σᵢ Aᵢ(t) Φᵢ(x,t)`; each `Φᵢ` is a spatiotemporal pattern correlated with a *family* of events (an "epoch") | §3.2 |
| Untethered potentials | before outcomes fix, several `Aᵢ(t)` are non-negligible; *"as constraints accumulate, one amplitude tends to dominate"* | §3.2, glossary |
| Agent–field coupling | `uₙ = H[M(x_agent(tₙ), tₙ)] ∈ ℝᵏ`; `vₙ = F(vₙ₋₁, uₙ, bodyₙ, sensoryₙ)` | §4.1 |
| Resonance indicator | `Sₙ ∈ {0,1}`; in resonance `uₙ ≈ Σᵢ βᵢ Aᵢ(tₙ) ψᵢ`, and when one mode dominates (`\|A_k\| ≫ \|A_j\| ∀j≠k`) the state aligns: **`vₙ ≈ γψ_k + noise`** | §4.2 |
| Mixed-time content | `vₙ ≈ Σ_{Eⱼ∈E_k} w_{n,j} φ(Eⱼ)` — one internal experience integrating events from multiple times | §4.3 |
| Bayesian layer | `µₙ(ω) = P(ω \| D₁…Dₙ)`, update `µₙ(ω) ∝ µₙ₋₁(ω) Lₙ(Dₙ\|ω)` | §5.1 |
| Determinism index | `Dₙ = 1 − H(µₙ)/H(µ₀)`; information gain `ΔHₙ = H(µₙ₋₁) − H(µₙ)` | §5.2 |
| Non-separable modes | `Ψ(t) = Σᵢ Aᵢ(t) Φᵢ^entangled(t)` — joint configurations across subsystems that do not factorize | §6.1 |
| Temporal decay of correlation | `C(t) ≈ C₀ e^{−\|t−t*\|/τ}` — **build-up, peak at `t*`, fade** | §6.2 |
| Resonance score (engineering) | `Rᵢ(t) = f(Âᵢ(t), Ȧ̂ᵢ(t), context)`; predict when `\|Â_k(t)\|` is large **and** `\|Â_k\|/Σⱼ\|Âⱼ\| ≈ 1` | §7.1–7.2 |
| Entropic flip | transition from diffuse to sharply peaked outcome distribution; a major drop in `H(µₙ)` and rise in `Dₙ` | glossary |
| Negative space | *"the informational contribution of absences or non-occurrences … which still constrain the set of possible histories"* — represented as constraints on `Ω` influencing the evolution of `Aᵢ(t)` | glossary |
| Near-associated data | signals not obviously causal precursors but structurally linked to the same epochal pattern | glossary |

### 2.3 The seven IRF concepts that apply to substrate memory

1. **Priors over histories, not records of history.** `µ₀` is explicitly an
   *ignorance* measure over whole histories. The memory-relevant reading: what a
   system holds is a distribution over what could have happened, narrowed by
   evidence — not a copy of what did.
2. **Modes, not records.** `Φᵢ` is a *pattern spanning a family of events*, not one
   event's data. A store of eigenmodes is categorically a different object from a
   store of snapshots, and cannot be converted into one.
3. **Amplitudes as untethered potential.** `Aᵢ(t)` is time-dependent and plural. The
   memory reading of "several `Aᵢ` non-negligible, converging as constraints
   accumulate" is: *multiple candidate reconstructions coexist and are narrowed by
   the cue*, not one stored answer retrieved.
4. **Recall as a resonance episode.** `vₙ ≈ γψ_k + noise` is the single most
   directly applicable line in the paper. The remembered content is the agent's
   state *aligned with* a mode, scaled by `γ`, plus noise — **an alignment event,
   not a readout**. There is no copy operation anywhere in the formalism.
5. **Determinism index as an information-gain cycle.** `Dₙ = 1 − H(µₙ)/H(µ₀)` gives
   uncertainty → certainty a scalar shape without requiring a stored confidence.
   The narrowing is a property of the candidate set, not a number attached to a
   memory.
6. **Temporal decay of correlation as build-up/peak/fade.** §6.2's `C(t)` is
   explicitly three-phase and explicitly peaks at `t*` *before* the outcome is
   realized, then fades after. This is C3's shape stated in the paper's own terms.
7. **Negative space.** Non-occurrences constrain `Ω`. In a memory setting this is
   the near-miss: the candidate reconstructions that were partially engaged and did
   not complete. They carry information about the discrimination even though nothing
   was admitted.

### 2.4 What must be refused from the IRF

This is the most important negative finding of §2, and it should be recorded before
anyone reuses the paper's vocabulary.

- **The advanced Green's function `G_adv` and any `α > 0` must be refused
  outright.** The retrocausal channel is the paper's speculative core, is
  unvalidated by construction (§9), and has no substrate correlate. Importing it
  would mean an organism whose memory is influenced by events that have not
  occurred — which in an implementation can only be fabricated. **Adopt the mode /
  amplitude / determinism-index formalism at `α = 0`.** The paper itself says
  `α = 0` recovers standard causality and that the engineering version reduces to
  early pattern detection.
- **"Premonition" has no place in a memory law.** §7's honest restatement is
  "detect when the data collectively align with a known epochal eigenmode." That is
  recognition. Naming it anything stronger would be an overclaim of exactly the
  type §7.4 warns against ("avoid overclaiming certainty when amplitudes are still
  diffuse").
- **`Aᵢ(t)` must not be imported as a stored scalar.** In the paper it is a field
  coefficient derived from the field's own decomposition. A stored per-memory
  strength number is not that object, and would additionally violate the
  non-flattened cognitive capital law already ratified in-tree.

### 2.5 The paper's own validation strategy, which is directly reusable

§8 proposes three tests. Two of them transfer to substrate memory almost unchanged
and are better falsification templates than anything invented fresh:

- **§8.1 information-gain analysis** — log predictions before outcomes with
  timestamps and confidence; look for rare, outlier high-information-gain episodes
  against a base-rate model. Substrate form: log candidate-set size before cue,
  during recurrence, and after admission, and require the narrowing to be real
  rather than assumed.
- **§8.2 epoch clustering** — check whether hits cluster into a small number of
  recurring eigen-scenarios *rather than being uniformly random*. Substrate form:
  do admitted originals cluster into a few recurring formations, or does every
  encounter mint a new one? This is a cheap, decisive test of whether an ensemble
  is behaving as modes or as a snapshot list.
- **§8.3 simulation with known hidden modes** — build a world whose modes are known
  and test whether mode-detection beats conventional prediction at early detection.

---

## 3. Source 2 — established memory science

### 3.1 Reconstructive recall (Bartlett; schema; false memory)

Bartlett's *Remembering* (1932) drew on memory distortions to refute the idea that
remembering is literal reproduction, arguing instead that remembering "is an
imaginative reconstruction or construction" depending on **schema**. The modern
statement (Roediger & DeSoto) is blunt: **errors — false memories — constitute the
prime evidence for reconstructive processes**, arising from inference at encoding,
information received after the event, and the perspective taken at retrieval.

The mechanism is gap-filling: in the absence of complete information the system
fills gaps using prior knowledge to make the memory coherent. Schacter's adaptive
constructive processes account frames this as a *feature*, not a defect: the same
machinery that reconstructs the past constructs simulated futures, and the errors
are the price of that flexibility.

**Bearing on C1/C2:** direct and dispositive. If memory were a stored record,
schema-consistent distortion would have no mechanism.

### 3.2 Consolidation and reconsolidation — nature's own non-immutability

The core result: reactivating a consolidated memory returns it to a **transiently
labile state**, during which it can be weakened, strengthened, or updated, and from
which it must be re-stabilized (reconsolidation) to persist. The consequence stated
in the literature's own words: *"the next time the memory is activated the version
stored during the last retrieval, rather than the version stored after the original
experience, is called up."* Memories are reactivated and reconsolidated in repeated
rounds of cellular processing.

**Molecular requirements** (from the Frontiers 2023 boundary-conditions review):

- **Destabilization** depends on transient internalization of calcium-impermeable
  **AMPA receptors**, permitting postsynaptic calcium influx.
- **CaMKII** signalling follows the calcium influx and regulates proteasome
  phosphorylation.
- **Protein degradation** (proteasome) is required for destabilization —
  destabilization is an *active, energy-consuming* process, not a passive
  loosening.
- **Protein synthesis** is required for re-stabilization.
- The **lability window is time-limited**, measured in hours.

**Boundary conditions — and this is where the received summary is incomplete.**
The reconsolidation window is **two-sided**, not one-sided:

1. **Prediction error is necessary but not sufficient.** A reminder that perfectly
   matches expectation does not destabilize. Prediction error demarcates the
   transition from mere retrieval, to reconsolidation, to new learning (Sevenster,
   Beckers & Kindt 2014).
2. **Too much mismatch triggers new learning instead of updating.** The review is
   explicit: *"prediction error alone doesn't guarantee reconsolidation; excessive
   mismatch between acquisition and retrieval may instead trigger new learning
   similar to extinction."*
3. **Reactivation dose is a separate boundary from prediction error.** Brief
   exposure (4 CS presentations) engages reconsolidation; extensive exposure (40 CS)
   produces extinction — described as *"the crucial variable that drives the
   behavioral and neurobiological differences."* This is a duration/count boundary
   that is **not** the same variable as mismatch magnitude.
4. **Strength and age raise the threshold.** Destabilizing stronger fear memories
   requires greater degrees of prediction error; older and better-learned memories
   resist. Weak or incompletely consolidated memories may show impaired
   *consolidation* rather than true reconsolidation disruption — an important
   confound.
5. **Circuit-level shift.** Brief retrieval engages excitatory BLA processes;
   extended reactivation increasingly recruits the mPFC→BLA pathway, raising BLA
   GABAergic tone and shifting toward extinction.

**Behavioural signature that distinguishes the two outcomes:**
reconsolidation-modified memories are *not* susceptible to relapse; extinction-based
change is susceptible to spontaneous recovery, renewal, and reinstatement. This is
the field's own discriminating test and it is worth copying: a system claiming to
have *updated* a memory rather than *added a competing one* should show no
spontaneous return of the old behaviour.

**Bearing on C2:** this is C2 in the neuroscience's own vocabulary — remembering
re-writes. It is also the specific literature that refutes immutability as a
biological principle.

### 3.3 The engram — fragments, index, pattern completion, silence

**Fragments and distribution.** Engrams are formed in CA3 in a **sparse and
distributed** manner, facilitated by sparse activations from dentate gyrus. What is
laid down is a distributed pattern across a small selected population, not a
localized record.

**Index, not content.** Hippocampal memory indexing theory: the hippocampal trace
serves as an **index** for a cortical representation; the primary hippocampal
function is to *reinstate* the cortical activity pattern present at encoding. Once
the index is established, **a partial input suffices** to reactivate the complete
hippocampal representation, which reinstates the cortical pattern and produces the
sense of recall (Teyler & DiScenna; Tanaka & McHugh 2018; Goode et al. 2020). The
memory is therefore not *in* the index — the index is a pointer that triggers a
reconstruction elsewhere.

**Pattern completion.** CA3's extensive recurrent architecture supports
auto-associative attractor dynamics enabling pattern completion during recollection:
a degraded cue is amplified toward the stored representation. Recent work (bioRxiv
2024/2025) shows global inhibition is insufficient to model this — **heterosynaptic
plasticity at excitatory→inhibitory synapses** lets inhibitory neurons associate
with specific assemblies and *selectively suppress competing engrams* at retrieval,
substantially improving recall stability and accuracy. **Competition between
candidate memories is part of the retrieval mechanism, not an artefact.**

**Silent engrams — storage and retrievability are separable.** Under
protein-synthesis-inhibitor-induced retrograde amnesia, memories cannot be recalled
by natural cues but *are* fully recoverable by direct optogenetic activation of
engram cells, persisting at least 8 days (Ryan et al. 2015; Roy et al. 2017 PNAS).
The dissociation is mechanistically specific: **engram-cell-to-engram-cell
connectivity carries the stored information; engram-synapse strengthening carries
retrievability.** "Forgotten" frequently means unreachable, not erased.

**Bearing on C1:** dispositive. What persists is a sparse distributed pattern plus
a pointer, and it can persist in a form that cannot currently be reached.

### 3.4 Systems consolidation, replay, gistification, trace transformation

**Replay and schema formation.** Systems consolidation during sleep is an active
process embedded in global synaptic downscaling; repeated hippocampal replay during
slow-wave sleep drives gradual transformation and integration in neocortex.
Critically, **overlapping** replay of multiple related memories drives abstraction
of shared components — *gist* — forming new cognitive schemata (Lewis & Durrant
2011).

**Replay is generative, not a tape.** Internally generated hippocampal sequences
extend well beyond previous experience: shortcut sequences between experienced
trajectories, trajectories through regions seen but never explored, sequences
implied by learned abstract structure, and preplay of novel environments. The
literature's framing is that the hippocampal formation acts as a **hierarchical
generative model** and that these sequences are *generative replay* — resampling of
fictive experience — rather than playback from a buffer.

**Gistification.** Details fade with time while the central gist is preserved and
*strengthened*; wake recall and offline consolidation interact to transform memories,
strengthening semantic information over perceptual detail. The finding that matters
most here: **recalling memories frequently speeds this transformation up**
(Birmingham 2021). Recall is not neutral maintenance — it accelerates the loss of
detail and the consolidation of gist.

**Trace transformation theory** (Nadel & Moscovitch; Sekeres, Winocur & Moscovitch):
with age and experience, detailed context-specific episodic traces are transformed
into variants lacking detail and context specificity but retaining gist and
schematic features; the two forms can co-exist. **Each retrieval re-encodes the
memory along with the new context of retrieval**, so multiple traces accumulate and
neocortex extracts their similarities into generalized semantic memory.

**Bearing on C1 and C3:** what survives is schematic, and the survival is produced
*by* repeated recall. This is the mechanism that makes C3's second uncertainty
inevitable rather than pathological.

### 3.5 Generative-model accounts — recall as construction, formalized

**Complementary Learning Systems**: a fast hippocampal learner and a slow neocortical
learner, with replay letting neocortex learn from hippocampal activity by
integrating related experiences into existing semantic networks.

**Spens & Burgess, *A generative model of memory construction and consolidation*
(Nature Human Behaviour, 2024)** is the most directly applicable computational work
found, and it is absent from the in-tree design study. The model:

- Hippocampus encodes episodic memories via an auto-associative network binding
  coarse/conceptual with fine/sensory detail.
- Neocortex is a **variational autoencoder**: an encoder mapping sensory experience
  to latent variables (entorhinal, mPFC, anterolateral temporal cortex), and a
  **decoder that reconstructs experience from conceptual representations**.
- **Replay trains the generative model.** Hippocampal replay in fast-forward during
  rest and sleep lets the neocortical network minimize prediction error and update
  its generative model of the world.
- **Recall is generation, not retrieval.** In the authors' own words: *"Remembering
  involves imagining the past based on concepts, combining some stored details with
  our expectations about what happened."*
- **Distortion increases with consolidation.** As memories integrate into the
  generative model they become more useful for inference *and more distorted* —
  unique detail is sacrificed to schema assimilation. The model reproduces
  schema-based distortions including boundary extension, plus effects of memory age
  and hippocampal lesions.
- **Memory and imagination share the substrate** — the same constructive circuitry.

**Bearing on C2:** this is C2 formalized and simulated. It also supplies a result
that no other source states as sharply: **the degradation of episodic detail is a
monotone consequence of consolidation itself**, not an additional decay process.

### 3.6 Reinforcement by recall — the testing effect

The owner's claim that memory is strengthened by "the conscious act of remembering"
is one of the most robust findings in the field.

- **Retrieval practice strengthens more than restudy.** When practice involves
  recall, the benefit is generally greater than restudy (Roediger & Karpicke).
- **The mechanism is that retrieval changes the trace it touches** — increasing
  elaboration and multiplying retrieval routes, thereby raising the probability of
  future successful retrieval. Note the shape: what improves is *reachability by
  more paths*, not fidelity of a record.
- **Neural correlate:** relative to restudy, retrieval practice produces stronger
  and more differentiated target representations in medial prefrontal cortex, and
  facilitates memory *updating* (eLife 2020).
- **Retrieval-induced forgetting:** the same act that strengthens retrieved material
  impairs later recall of related non-retrieved material — more pronounced at short
  delays than long. Strengthening is competitive and has a cost paid by neighbours.

**Bearing on C2:** direct support, with a refinement the owner's phrasing does not
contain — recall strengthens *accessibility*, and does so **at the expense of
competitors and at the expense of detail** (§3.4). It is not free.

### 3.7 Where the science is contested

Recorded so that no design leans on citation authority it does not have.

- **Reconsolidation replication.** A 2022 *Scientific Reports* study found no
  reconsolidation effect in single prediction-error groups and failed to replicate;
  the review literature notes *"failures to replicate in both humans and rats"*
  regarding reactivation-extinction procedures, and that human evidence "remains
  controversial." The dominant explanation is that boundary conditions were not
  respected — which is itself a reason to treat the boundary conditions (§3.2) as
  the load-bearing part rather than the phenomenon.
- **Consolidation theory is unsettled.** Standard consolidation theory, multiple
  trace theory, and trace transformation theory remain in active competition
  (Moscovitch & Nadel 2021). The *transformation* claim is better supported than any
  specific account of hippocampal disengagement.
- **Silent engrams rest on optogenetic reactivation**, an intervention with no
  natural analogue; the storage/retrievability dissociation is well demonstrated but
  its generality beyond fear conditioning in mice is not established.

---

## 4. The three claims adjudicated

### 4.1 C1 — "fragments of truth" — **SUPPORTED**

Every line of evidence converges: sparse distributed engrams (§3.3), index-not-content
(§3.3), gistification (§3.4), trace transformation (§3.4), latent-variable
compression in the generative account (§3.5).

The precise form the research supports is stronger than the owner stated it:

> What persists is (a) a **permanent structural residue** — connectivity — plus
> (b) a **reachability** that is separately maintained and separately lost, plus
> (c) a **prior/schema** that supplies everything (a) and (b) do not.

The engram result (§3.3) makes (a) and (b) doubly dissociable, and the generative
result (§3.5) makes (c) load-bearing rather than decorative. A store that keeps a
complete verbatim snapshot is not a lossy memory — it is a categorically different
object.

### 4.2 C2 — "remembering is a reconstructive process" — **SUPPORTED, strongly**

Bartlett (§3.1) establishes it behaviourally; pattern completion (§3.3) supplies the
circuit; the generative model (§3.5) supplies the computation; reconsolidation (§3.2)
supplies the re-storage; the testing effect (§3.6) supplies the strengthening the
owner named.

The IRF's `vₙ ≈ γψ_k + noise` is the same statement in field language: the
remembered content *is* the state's alignment with a mode, never a copy of a record.

Two refinements the charge does not contain, both from the research:

- **Reconstruction is competitive.** Selective inhibition suppresses competing
  engrams during retrieval (§3.3), and retrieval-induced forgetting shows the
  suppression has lasting cost (§3.6). Reconstruction is not "assemble the fragments"
  — it is "one candidate wins against others."
- **Re-storage is conditional, not automatic.** §3.2's boundary conditions mean most
  recalls do *not* destabilize. A model in which every recall rewrites is as wrong as
  one in which none does.

### 4.3 C3 — "uncertainty → certainty → uncertainty" — **SUPPORTED, with one correction**

The arc is real and each leg has a mechanism:

| Leg | Mechanism | Source |
|---|---|---|
| Initial uncertainty | the new trace is labile, protein-synthesis-dependent, not yet consolidated; allocation is still competitive | §3.2, §3.3 |
| → certainty | consolidation, replay, retrieval practice; accessibility and gist both strengthen; the candidate set narrows to one | §3.4, §3.6 |
| → uncertainty | each retrieval re-opens lability; gistification strips detail; transformation makes the trace schematic; schema distortion *increases* with consolidation | §3.2, §3.4, §3.5 |

The IRF's `C(t) ≈ C₀ e^{−|t−t*|/τ}` (§6.2) — build-up, peak, fade — is the same
three-phase shape, and the determinism index `Dₙ = 1 − H(µₙ)/H(µ₀)` gives the middle
leg a scalar reading that requires no stored confidence value.

**The correction: it is a spiral, not a cycle.** The word "cycle" implies return to
the starting state. The research says the terminal uncertainty is *categorically
different* from the initial one:

- Initial uncertainty is **uncertainty about which trace will be laid down at all** —
  allocation is unresolved, the trace is destructible.
- Terminal uncertainty is **uncertainty about detail within a trace whose gist has
  become stronger and more confidently held than it ever was at encoding**.

This distinction is not pedantic; it is the one that decides what an implementation
must measure. Gistification and trace transformation both say that as detail
uncertainty rises, *schematic* certainty rises with it — and the eyewitness
literature notes confidence may not track accuracy at all through this phase. A
design that models C3 as a single scalar returning to its starting value will model
the wrong thing. **Two quantities move, in opposite directions.**

---

## 5. Correspondence: charge ↔ IRF ↔ science ↔ substrate

Substrate line numbers verified in this session against
`/tmp/guala-production-15a7dca9/native/guala_core/src/`.

| Charge element | IRF object | Memory science | Existing substrate mechanism |
|---|---|---|---|
| fragments of truth | `Φᵢ` spans an event family; negative space constrains `Ω` | sparse distributed engram; index-not-content; gist | retained fractals + bond structure in `ResidentExperienceEvidence`; hippocampal index |
| conscious effort re-deriving | `vₙ ≈ γψ_k + noise`; resonance episode `Sₙ=1` | CA3 pattern completion from partial cue | `admit_physical_mosaic` (`physical_mosaic.rs:143`) — current must reach **and change every member**; `is_proper_partial_cue` (`resident_cognitive_formation.rs:2423`) |
| reinforced by repeated experience | amplitudes `Aᵢ(t)` accumulate constraint | consolidation; overlapping replay builds schema | `classify_temporal_reassembly` (`:268`), `mosaics_share_active_bond` (`:317`) — counts over the append-only chain |
| reinforced by the act of recall | — (paper has no recall-strengthens term) | **testing effect**; retrieval re-encodes with new context | *absent* — recognition emits an episode but does not alter the reference |
| not immutable | `Aᵢ(t)` time-dependent | **reconsolidation** | *absent* — single write at `:2061`, fork at `:1938` never re-enters the writer |
| uncertainty → certainty | `Dₙ = 1 − H(µₙ)/H(µ₀)`; entropic flip | candidate competition resolved by selective inhibition | candidate narrowing is real and enumerable, but not currently observed or logged |
| → uncertainty | `C(t)` fade after `t*` | gistification; transformation; distortion rises with consolidation | *absent* — verified: the only `decay` token in 79 `.rs` files is `optical_receptor_work.rs:103` documenting that decay was deliberately **not** built |

Three gaps, all in the same place: **the reference is written once and never
re-derived.** The reconstruction machinery is the strongest part of the tree; the
memory law around it is the weak part.

---

## 6. Findings that bear on the in-tree design study

`GUALA_RECONSTRUCTIVE_MEMORY_DESIGN_STUDY_2026-08-05.md` §2 cites six science
findings (a)–(f). This research confirms four, extends one, and challenges two of
the design's conclusions.

**F1 — CONFIRMS the study's core diagnosis.** Verified independently: the single
write site is `resident_cognitive_formation.rs:2061`; the dispatcher at `:1938`
routes to the recurrence path forever once `retained_experience.is_some()`; no path
sets it back to `None`. The claim "real decay exists nowhere" is confirmed by an
independent sweep. The study's identification of the frozen reference as the sole
defect is sound.

**F2 — CHALLENGES R2's binary prediction-error gate.** The study proposes R2: fire
re-grounding **iff** `!already_formed` (the byte-equality test at `:2164`, verified).
That is a *binary* prediction-error signal. The literature (§3.2) says the boundary
is **two-sided and graded**:

- below threshold → no destabilization (the study has this);
- above an *upper* bound → **new learning, not updating** (the study does not have
  this);
- and the threshold itself **rises with the memory's strength and age**.

Under a binary gate, a wildly novel mosaic — one sharing almost nothing with the
retained original — re-grounds the reference just as readily as a near-match. The
science says that case should form a *new* trace and leave the old one intact. This
is not a small refinement: it is the difference between updating a memory and
overwriting it with a different one, and the study's §9 Q2 ("replace, do not union")
compounds the exposure, because replacement plus an unbounded upper edge means one
anomalous encounter can destroy a well-established reference.

The substrate already computes the raw material for a graded signal —
`mosaics_share_active_bond` (`:317`) gives shared-bond overlap between mosaics, and
`classify_temporal_reassembly` (`:268`) gives prior-occurrence counts that scale with
memory age. Whether those can supply a two-sided boundary **without inventing a
constant** is an open design question (§7), not something this research settles.

**F3 — CHALLENGES the framing that the ensemble is only plurality.** The study's R3
treats multiple retained originals as the IRF's mode decomposition — correct as far
as it goes. But §3.4 supplies a second function the study does not claim:
**overlapping replay of related traces is the mechanism that builds schema/gist.**
An ensemble of originals sharing bonds is not merely several candidates; it is the
substrate's only available route to a *gist* — the thing §3.4 and §3.5 both say is
what actually survives.

This reframes the study's §9 Q2 dilemma. It posed two options — replace the masks,
or union them — and rejected union because references would become monotonically
permissive. The research suggests a third reading: **the plurality is where
generalization should live, and the individual reference should stay specific.**
Replace-within-an-original plus an ensemble that accumulates related originals gives
both specificity and gist without a permissive union. This is a research
observation, not a design; it is offered because §9 Q2 is flagged in the study as its
least obvious choice.

**F4 — EXTENDS (c), the silent-engram finding, with the mechanism.** The study cites
Ryan/Roy correctly. The mechanistic detail matters for R5: the dissociation is
**engram-cell-to-engram-cell connectivity carries the information; engram-synapse
strengthening carries retrievability**. That is precisely the study's two-tier split
(permanent geometry vs. re-earnable reachability), and it means R5 is not an analogy
— it is the same partition biology uses. R5 is the best-supported of the five laws.

**F5 — CONFIRMS R3's derived-amplitude choice from an angle the study did not use.**
The testing effect (§3.6) says recall strengthens *by multiplying retrieval routes*,
not by incrementing a stored strength. A count over the append-only episode chain is
therefore not merely a doctrinal workaround for the no-stored-scores rule — it is a
closer model of the biology than a stored weight would be. Retrieval-induced
forgetting (§3.6) adds that strengthening is competitive and costs neighbours, which
the study's design does not currently represent anywhere.

**F6 — a research finding neither the study nor the charge contains.** §3.5's
generative-model result is that **schema distortion increases monotonically with
consolidation**. The study's §4 claims the release of certainty is "the arithmetic
consequence of memory being reconstructive" and needs no decay term. The research
supports that claim and supplies a second, independent source of the same release:
*integration itself*. If an ensemble accumulates and generalizes (F3), detail
certainty falls without any decay law and without re-grounding. This strengthens the
study's central theoretical claim while showing it has two mechanisms rather than
one — and it means the study's P5 test should distinguish which mechanism produced
the release, or it will pass for the wrong reason.

---

## 7. What this research does not settle

1. **Whether a graded, two-sided prediction-error boundary (F2) can be derived from
   existing quantities without authoring a constant.** The doctrine forbids invented
   constants; the science forbids a binary gate. Whether both can be satisfied at
   once is unresolved and is the single most important open question.
2. **What the substrate's analogue of "reactivation dose" is.** §3.2 shows exposure
   count (4 vs 40 CS) is a boundary variable independent of mismatch magnitude.
   Nothing in the surveyed substrate mechanisms obviously corresponds to it.
3. **Whether gist can exist in a substrate with no similarity metric.** All
   comparison in the tree is exact — `sparse_physical_state_delta` returns `None` iff
   bit-identical. Gist in the literature is an *abstraction over near-matches*.
   Whether shared-bond overlap is a sufficient substitute for graded similarity is
   untested.
4. **Whether the two opposing quantities of C3 (§4.3) are both observable.** Detail
   uncertainty rising while schematic certainty rises is the correct model; whether
   the substrate can report both without a stored score is unknown.
5. **Whether reconsolidation's replication problems (§3.7) matter here.** The
   failures are in human fear-conditioning paradigms with contested boundary
   conditions. Whether that weakens the case for building on reconsolidation, or
   merely warns about the boundary conditions, is a judgement call that should be
   made explicitly rather than by omission.
6. **The relative ordering of the two release mechanisms in F6.** Not researched.

---

## 8. Constraints any design must respect (recorded, not proposed)

Verified in-tree; these bound the solution space and are stated here so no design
argues past them.

- **Doctrine.** No invented constants; truth-coupling (never report a state the
  physics did not produce); no semantic labels in the cognition path; bounded
  resident state; one system — no shadow store, no dual-write, no parallel recall
  backend; lean substrate — every ship states its bound.
- **Immutable custody stays immutable.** `hippocampal_directory_cold_store.rs:13`:
  *"This store never mutates or deletes an object."* Re-publication requires byte
  equality. Nothing in this research argues for changing that — §3.2's lability
  applies to the *reference*, and the science offers no analogue at all to a
  falsifiable receipt of what actually happened. The distinction the design study
  draws (receipts immutable, references not) is the correct resolution of the
  owner's charge, and this research supports it.
- **Byte ceilings.** Approved persistent storage ceiling 5 GiB
  (`dsf_ai_service/app.py`); fail-closed physical byte authority that never prunes or
  evicts, only admits or refuses with a capacity receipt; derived organism envelope
  with **no semantic count used as a growth cap**; exactly two generations on disk.
  An ensemble (R3) or any re-grounding scheme (R1) must live inside a derived
  envelope, and any capacity law must evict by physics rather than by recency.
- **No decay term exists to build on.** The tree has no `tau`, no half-life, no
  wall-clock forgetting anywhere; the one `decay` token documents its deliberate
  absence. Every reduction in the tree is fuel-gated reversal, exact conserving
  handoff, one-shot boundary closure, consumption-on-use, or solver scratch.

---

## 9. Summary

The owner's rejection of immutable memory is **correct on the science**, and more
strongly than the charge claims.

- **C1 (fragments)** — supported. What persists is permanent connectivity plus
  separately-maintained reachability plus a schema that supplies the rest. The
  storage/retrievability dissociation is doubly dissociable in the engram
  literature.
- **C2 (reconstruction, reinforced by experience and by recall)** — supported by
  five independent literatures. Two refinements: reconstruction is *competitive*,
  and re-storage is *conditional*, not automatic. A design that rewrites on every
  recall is wrong in a way the field has already documented.
- **C3 (uncertainty → certainty → uncertainty)** — supported, with the correction
  that it is a **spiral, not a cycle**: detail certainty falls while schematic
  certainty rises. Two quantities move in opposite directions, and modelling it as
  one scalar returning to its start will measure the wrong thing.

From the IRF: adopt the mode/amplitude decomposition, the resonance-as-alignment
reading of recall (`vₙ ≈ γψ_k + noise`), the determinism index as candidate-set
narrowing, the build-up/peak/fade shape, and negative space. **Refuse the advanced
Green's function and any `α > 0`** — the paper's speculative core has no substrate
correlate and could only be fabricated. The paper is self-labelled speculative and
supplies shape, never authority.

Bearing on the design already in the tree: its diagnosis is confirmed
independently; R5 is the best-supported law and matches the biology's own partition;
R3's derived-count amplitudes are a closer model than stored weights would be. Two
challenges stand: **R2's binary prediction-error gate is one-sided where the science
is two-sided and graded**, and the plurality of R3 is probably the substrate's only
route to gist — which reopens §9 Q2 on better terms than the two options it posed.

---

## Sources

**External science** — reconsolidation and its boundaries:
- [Memory retrieval, reconsolidation, and extinction: exploring the boundary conditions of post-conditioning cue exposure (Frontiers in Synaptic Neuroscience, 2023)](https://www.frontiersin.org/journals/synaptic-neuroscience/articles/10.3389/fnsyn.2023.1146665/full)
- [Prediction error demarcates the transition from retrieval, to reconsolidation, to new learning (Sevenster, Beckers & Kindt, Learning & Memory 2014)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4201815/)
- [The fate of memory: reconsolidation and the case of prediction error (Fernández, Boccia & Pedreira)](https://pubmed.ncbi.nlm.nih.gov/27287939/)
- [Destabilizing different strengths of fear memories requires different degrees of prediction error during retrieval](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7820768/)
- [Demarcating the boundary conditions of memory reconsolidation: an unsuccessful replication (Scientific Reports 2022)](https://www.nature.com/articles/s41598-022-06119-5)
- [Memory reconsolidation (Current Biology)](https://www.cell.com/current-biology/fulltext/S0960-9822(13)00771-9)
- [Reconsolidation: maintaining memory relevance](https://pubmed.ncbi.nlm.nih.gov/19640595/)

**External science** — engram, index, pattern completion:
- [Silent memory engrams as the basis for retrograde amnesia (Roy et al., PNAS 2017)](https://www.pnas.org/content/114/46/E9972)
- [Engram cells retain memory under retrograde amnesia (Ryan et al., Science 2015)](https://www.science.org/doi/10.1126/science.aaa5542)
- [The hippocampal engram as a memory index (Tanaka & McHugh 2018)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6287299/)
- [An integrated index: engrams, place cells, and hippocampal memory (Neuron 2020)](https://www.cell.com/neuron/fulltext/S0896-6273(20)30528-6)
- [The mechanisms for pattern completion and pattern separation in the hippocampus](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3812781/)
- [Selective inhibition in CA3: a mechanism for stable pattern completion through heterosynaptic plasticity (bioRxiv)](https://www.biorxiv.org/content/10.1101/2024.08.16.608240v2.full)

**External science** — reconstruction, consolidation, transformation, generative models:
- [Reconstructive memory, psychology of (Roediger & DeSoto)](http://psychnet.wustl.edu/memory/wp-content/uploads/2018/04/BC_Roediger-DeSoto-in-press-1.pdf)
- [Adaptive constructive processes and the future of memory (Schacter)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3815569/)
- [A generative model of memory construction and consolidation (Spens & Burgess, Nature Human Behaviour 2024)](https://www.nature.com/articles/s41562-023-01799-z) — [authors' summary](https://communities.springernature.com/posts/a-generative-model-of-memory-construction-and-consolidation), [UCL Discovery record](https://discovery.ucl.ac.uk/id/eprint/10186145/)
- [Mechanisms of systems memory consolidation during sleep (Nature Neuroscience 2019)](https://www.nature.com/articles/s41593-019-0467-3)
- [Overlapping memory replay during sleep builds cognitive schemata (Lewis & Durrant, TiCS 2011)](https://www.sciencedirect.com/science/article/abs/pii/S1364661311001094)
- [The hippocampal formation as a hierarchical generative model supporting generative replay and continual learning](https://www.sciencedirect.com/science/article/abs/pii/S0301008222001150)
- [Generative emergence of non-local representations in the hippocampus](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12391462/)
- [Memory details fade over time, with only the main gist preserved (Birmingham 2021)](https://www.birmingham.ac.uk/news-archive/2021/memory-details-fade-over-time-with-only-the-main-gist-preserved)
- [Systems consolidation, transformation and reorganization: MTT, TTT and their competitors (Moscovitch & Nadel)](https://www.researchgate.net/publication/351476848_Systems_consolidation_transformation_and_reorganization_Multiple_Trace_Theory_Trace_Transformation_Theory_and_their_Competitors)
- [Memory formation and long-term retention: convergence towards a transformation account](https://pubmed.ncbi.nlm.nih.gov/20430044/)

**External science** — reinforcement by recall:
- [Retrieval practice facilitates memory updating by enhancing and differentiating mPFC representations (eLife 2020)](https://elifesciences.org/articles/57023)
- [Neural correlates of long-term memory enhancement following retrieval practice](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7889502/)
- [When does retrieval induce forgetting and when does it induce facilitation?](https://www.sciencedirect.com/science/article/abs/pii/S0749596X09000461)
- [Finding retrieval-induced forgetting in recognition tests: a case for baseline memory strength](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4179646/)

**In-repo:**
- `Information_Resonance_Fields_and_Premonition__Like_Inference_in_High__Dimensional_Histories__A_Theoretical_Framework.pdf` — read in full, 10 pp.; §§2–9 and glossary.
- `docs/GUALA_RECONSTRUCTIVE_MEMORY_DESIGN_STUDY_2026-08-05.md`
- `docs/GUALA_STIMULUS_BOUNDARY_RETENTION_RATIFICATION_2026-08-05.md`
- `docs/GUALA_D3_PHYSICAL_MOSAIC_RECALL_CAPITAL_SPINE_2026-08-04.md`
- `native/guala_core/src/resident_cognitive_formation.rs` (`:268`, `:317`, `:1938`,
  `:2061`, `:2164`, `:2423`), `physical_mosaic.rs:143`,
  `optical_receptor_work.rs:103`, `hippocampal_directory_cold_store.rs:13`.
