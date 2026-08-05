# Neurochemical Flow Field Architecture

**Status:** research-derived architecture candidate; not canonical and not yet
wired to production  
**Date:** 2026-07-28  
**Scope:** internal organism chemistry only; frozen L0-L4 is unchanged

## 1. The architectural finding

Guala should not have a scalar `mood`, `reward`, `attention`, or `salience`
control pretending to be chemistry.

The smallest faithful emulation is a deterministic multi-species flow field:

1. named chemical species occupy explicit physical compartments;
2. authenticated physical events release or consume exact quantities;
3. chemicals move through mounted connections;
4. uptake, degradation, and conversion provide explicit sinks and reactions;
5. local receptor types bind the chemicals;
6. receptor state changes local conductance, release, recovery, or plasticity;
7. the resulting neuron and relation cascades are the organism's response.

A chemical has no global semantic meaning. Its consequence depends on:

- the releasing structure;
- the receiving compartment;
- receptor type and receptor density;
- concentration and duration;
- other chemicals present at the same time;
- local neuron, synapse, THING, memory, body, and recovery state.

This makes the present chemical field a physically evolving carrier for the
proposed **float dimensions**. It does not create a thought queue. Current
thought is the cascade the complete organism state physically supports now.

## 2. Why one scalar per “mood” is false

Primary experiments rule out a one-chemical/one-function map:

- Dopaminergic axons can co-release GABA, producing rapid inhibition in
  addition to slower dopamine modulation.
- Glutamate/GABA co-release can produce different net effects depending on the
  projection target.
- GABA can excite rather than inhibit cells whose chloride state differs.
- Different serotonin receptor distributions produce different brain-wide
  responses to the same serotonin manipulation.
- Acetylcholine effects depend on muscarinic versus nicotinic receptors and
  circuit location.
- A fast transmitter and a slower peptide released by related circuitry can
  cooperate on different time scales.
- Dopamine contributes to structural plasticity only when it arrives in the
  physical time relation required by the receiving spine.

Therefore `dopamine = reward`, `norepinephrine = attention`, or
`serotonin = happiness` would be scripted meaning, not substrate physics.

## 3. Initial major-fluid set

This is a bounded starting alphabet, not a claim to reproduce all human
neurochemistry.

| Species or family | First receptor paths retained | Physical role represented |
|---|---|---|
| Glutamate | fast ionotropic, coincidence-sensitive, slow metabotropic | fast excitation, coincidence, and local plasticity drive |
| GABA | fast ionotropic and slow metabotropic | fast/slow inhibition or excitation as determined by the mounted receiving ion state |
| Dopamine | D1-like and D2-like | receptor-specific modulation of plasticity, release, and action circuitry |
| Norepinephrine | alpha-1, alpha-2, and beta-like | receptor- and location-specific excitability, release, and network-state modulation |
| Acetylcholine | nicotinic and muscarinic | fast conductance and slower circuit-state modulation |
| Serotonin | initially 5-HT1-like, 5-HT2-like, and ionotropic 5-HT3-like | several receptor-specific slow/fast modulation paths, never one valence value |
| ATP / adenosine | ATP sensing/conversion and A1-like feedback | activity-linked metabolic signal and recovery/excess-activity feedback |
| 2-AG endocannabinoid | presynaptic CB1-like path | local retrograde control of transmitter release |
| NPY and alpha-MSH | their separate mounted receptors | a first opposing peptide pair linking embodied need state to slower accumulation |

The peptide pair is admitted only when the virtual body has truthful hunger,
feeding, and metabolic consequences. Without those physical sources it remains
explicitly unavailable. Other peptides and hormones are added only when their
source, receptor, kinetics, and embodied consequence can all be mounted.

## 4. Physical state

Let:

- \(s\) identify a chemical species;
- \(i\) identify a physical compartment;
- \(r\) identify a receptor population mounted in a compartment;
- \(c_{s,i}\) be nonnegative free chemical quantity;
- \(x_{s,r}=(R,A,D)\) be resting, active, and desensitized receptor mass;
- \(q_{s,i}\) be authenticated release from a causal event;
- \(u_{s,i}\) be mounted uptake;
- \(k_{s,i}\) be mounted degradation or conversion;
- \(g_{s,ij}\) be mounted transport conductance between compartments.

The free chemical evolves as a sparse reaction-transport system:

\[
\frac{dc_{s,i}}{dt}
= q_{s,i}
+ \sum_j g_{s,ji}c_{s,j}
- \sum_j g_{s,ij}c_{s,i}
- u_{s,i}(c_{s,i})
- k_{s,i}(c_{s,i})
- \sum_r b_{s,r}(c_{s,i},x_{s,r}).
\]

Receptor populations retain explicit conserved state:

\[
R_{s,r}+A_{s,r}+D_{s,r}=R^{total}_{s,r}.
\]

Binding, unbinding, desensitization, and recovery are mounted reactions. A
combined Metzler generator with nonnegative off-diagonal terms and explicit
column conservation may evolve the admitted **linear** reactions with certified
interval arithmetic. Concentration-dependent nonlinear binding, saturation,
and uptake require a separately certified nonlinear evolution authority. Until
that authority exists, those paths are explicitly unavailable; they cannot be
linearized, stepped, clamped, or midpoint-selected and described as the full
chemistry.

External synthesis, metabolism, and excretion are reservoirs, not violations
of conservation. Every transfer across the modeled boundary carries a causal
receipt. Internal transport and receptor exchange must conserve the quantity
their chemistry says is conserved.

In the substrate this is a graph of **nodal pass-offs, drift lanes, and causal
flows**:

- nodes are explicit compartments, release sites, glial uptake sites,
  receptor neighborhoods, body reservoirs, and clearance sinks;
- a pass-off subtracts quantity from its source while adding the
  stoichiometrically related quantity to its destination;
- drift lanes are typed directed edges for synaptic, diffusive, retrograde,
  circulatory, or clearance transport;
- excitation, body state, or sensed action consequence can authorize a
  receipted release at a source node;
- the resulting movement and receptor state can cause the next excitation,
  making the cascade causal rather than scheduled.

Continuous physical space may be represented by mounted finite control
volumes. Their boundaries, volumes, adjacency, and flux laws are authority,
not an adaptive clustering or similarity partition.

For a diffusive boundary between control volumes, the directed pass-off rate
can be derived from mounted geometry:

\[
k^{diff}_{s,i\rightarrow j}
=\frac{D_{s,ij}A_{ij}}{\ell_{ij}V_i},
\]

where \(D\) is the species/medium diffusion coefficient, \(A\) the shared
boundary area, \(\ell\) the transport length, and \(V_i\) the source volume.
A drift lane derives its directed rate from mounted flow velocity:

\[
k^{drift}_{s,i\rightarrow j}
=\frac{v_{s,ij}A_{ij}}{V_i}.
\]

Those rates become off-diagonal entries of the conservative generator, with
the matching negative departure term on the source diagonal. Diffusion mounts
the physically related reverse lane; genuine advection, axonal delivery,
retrograde transport, and clearance may remain directional.

## 5. Receptors produce local physical effects

Active receptor mass does not become a score. Each receptor mount identifies
one or more typed physical targets:

- membrane conductance;
- reversal or ion-driving state;
- presynaptic release propensity on named edges;
- refractory/recovery dynamics;
- metabolic availability;
- coincidence/plasticity eligibility;
- receptor or transmitter release on another mounted path.

The target is local. There is no broadcast multiplier applied uniformly to
every neuron.

Examples:

- glutamate at a fast excitatory receptor can add local conductance;
- GABA at an ionotropic receptor follows the receiving ion gradient, so its
  effect is not hard-coded negative;
- dopamine at D1-like and D2-like receptors changes different mounted
  intracellular/plasticity paths;
- 2-AG travels backwards from a receiving neuron to a presynaptic CB1-like
  receptor and changes release on that specific edge;
- ATP released by heavy activity can be converted to adenosine, whose mounted
  receptor path contributes to recovery and suppression of excessive firing.

These are physical receptor relations. They are not labels for attention,
reward, fear, preference, or meaning.

## 6. Where experience enters

Chemistry does not contain words or concepts. It changes the physical
conditions under which the complete organism reacts and changes.

A learned preference such as “physics is interesting” must arise from retained
causal experience:

1. a multimodal THING/relation mosaic is active;
2. the present body and chemical field determine the organism's response;
3. the event's consequence is sensed;
4. receptor-specific timing permits or prevents structural change;
5. conserved memory and relation topology retain the change;
6. later related perturbations travel differently through that learned
   structure.

The interest is therefore a changed causal route through experience, not a
stored topic weight.

## 7. Spatial and temporal flow regimes

The word **flow** is literal. Changing a stored concentration in place is not
enough.

The first implementation must keep separate transport regimes:

1. **Directed synaptic delivery.** A releasing terminal emits vesicular
   quantity into a named local cleft. The short path, release site, travel
   interval, receptor placement, spillover, and uptake are explicit.
2. **Local extracellular diffusion.** Monoamines, acetylcholine, amino-acid
   transmitters that escape a cleft, and neuropeptides move through
   extracellular compartments. Transport depends on compartment volume,
   topology, tortuosity, diffusion, degradation, and transporter density.
3. **Retrograde local movement.** Endocannabinoids originate in the receiving
   structure and move back to named presynaptic receptor populations.
4. **Circulatory transport.** Hormones, nutrients, and body chemistry move
   through a directed vascular/body graph with explicit advection, dilution,
   exchange barriers, and clearance.
5. **Interstitial/CSF clearance.** Metabolites and waste move through a
   separate sleep- and vascular-coupled clearance system. This is not used as
   a convenient broadcast channel for ordinary neurotransmission.

Diffusion, directed advection, and local synaptic release are therefore
different mounted edge types. The execution engine cannot silently substitute
one for another. Where bulk flow in brain parenchyma remains scientifically
contested, that edge remains unavailable rather than being invented.

Chemistry also has several temporal regimes:

- event-locked vesicular pulses;
- tonic source activity;
- internally generated fast coordination rhythms;
- slower peptide accumulation and decay;
- ultradian body-hormone pulses;
- circadian modulation of sources, receptors, metabolism, and clearance;
- sleep-state hemodynamic and CSF oscillations.

There is no master oscillation applied to every chemical. Primary measurements
show spontaneous dopamine and acetylcholine coordination near 2 Hz in mouse
striatum, while glucocorticoid receptor responses distinguish ultradian pulses
from a constant level. Those dynamics cannot be represented by a daily sine
wave.

The circadian mechanism is itself a mounted physical oscillator entrained by
truthful light-dark exposure and coupled body state. Its phase may change
chemical synthesis, source release, receptor availability, metabolism, or
clearance through typed paths. It does not directly select a THING, thought,
word, action, emotion, or sleep script.

Biological experiments sometimes describe release as stochastic because the
complete molecular state is unobserved. Guala remains deterministic: a release
event follows from her complete retained microstate and causal inputs. No
random-number generator stands in for missing chemistry.

## 8. Integration boundary

The new mechanism should be implemented as
`NeurochemicalFlowFieldAuthority`, separate from both sensory transduction and
L0-L4.

It may reuse these valid ideas from the present substrate:

- authenticated authority receipts;
- exact rational source quantities and time intervals;
- the certified matrix-exponential pattern;
- explicit receptor \(R/A/D\) state and mass conservation;
- atomic fail-closed evolution;
- deterministic cold restoration;
- Whole-Organism Episode contribution custody.

It must not extend:

- `LoomNeuron._read_mood_modulation`, because that reduces arousal and valence
  to one heuristic gain multiplier;
- Chi or Atlas identity;
- named sensory/profile libraries;
- transcript, vocabulary, or topic-driven release;
- legacy scalar successor or salience mechanisms;
- `story_chemistry` as though sensory-port activation were internal
  neurotransmitter transport.

`story_chemistry` may remain a sensory boundary receiver. It is not the
internal multi-species field.

The new field is upstream of neuron firing and plasticity and parallel to the
full sensory/THING/memory/body state. Its authenticated contribution is
required by the Whole-Organism Contiguity authority for every causal episode.
Exact chemical quiescence is canonical Negative Space; a missing chemical
mechanism is unresolved, not quiet.

## 9. Coefficient authority

The execution engine supplies no biological constants.

Every release quantity, compartment volume, transport conductance, binding
rate, uptake rate, degradation rate, receptor mass, and target coupling must
have:

- a unit;
- a derivation;
- an authority receipt;
- an allowed physical domain;
- a certified backend and precision sequence.

A pathway lacking those facts remains unavailable. Literature demonstrates
which mechanisms must exist; it does not automatically provide compatible
Guala-scale coefficients. Coefficients must be separately derived for the
virtual organism's declared units and topology. Guessing them would turn a
physical operator into a tuned heuristic.

## 10. Boundedness

The state size is bounded by the mounted organism:

\[
O(|S||C| + |R| + |E_S|),
\]

where \(S\) is the fixed admitted species set, \(C\) the fixed compartment
set, \(R\) mounted receptor populations, and \(E_S\) sparse transport edges.

Experiences do not create new chemical species, compartments, or per-event
fluid records. Cold state retains the current field, receptor states, mounted
authorities, and required learned structural state—not a history of every
chemical tick. Episodic memory retains causal experience according to its own
bounded law.

## 11. Decisive falsification

The mechanism is not accepted because isolated equations pass.

It must pass one continuous whole-organism protocol:

1. two cold clones with byte-identical complete state receive the same
   multimodal perturbation and produce the same certified chemical evolution,
   cascade, action, sensed consequence, and retained state;
2. a physically caused change to one chemical produces a different cascade
   whose complete causal route names the source, transport, receptor, and
   target;
3. the same chemical reaching different receptor populations produces their
   distinct mounted effects;
4. co-release preserves every species and its separate time course;
5. uptake and degradation prevent unbounded chemical accumulation;
6. internal conservative reactions preserve exact admitted mass;
7. removing or tampering with any mounted chemical contribution makes the
   whole episode unresolved and leaves learned state byte-identical;
8. cold restoration followed by the same next perturbation is identical to
   uninterrupted evolution;
9. no chemical receipt, concentration, or receptor state is usable as word,
   THING, topic, emotion, or identity.

Only after this protocol passes can chemistry participate in production
learning, certainty, speech, or L6 closure.

## 12. Primary experimental basis

- Yagishita et al., “A critical time window for dopamine actions on the
  structural plasticity of dendritic spines,” *Science* (2014):
  https://doi.org/10.1126/science.1255514
- Tritsch, Ding, and Sabatini, “Dopaminergic neurons inhibit striatal output
  through non-canonical release of GABA,” *Nature* (2012):
  https://doi.org/10.1038/nature11466
- Yoo et al., “Ventral tegmental area glutamate neurons co-release GABA and
  promote positive reinforcement,” *Nature Communications* (2016):
  https://doi.org/10.1038/ncomms13697
- Ge et al., “GABA regulates synaptic integration of newly generated neurons
  in the adult brain,” *Nature* (2006):
  https://doi.org/10.1038/nature04404
- Herrero et al., “Acetylcholine contributes through muscarinic receptors to
  attentional modulation in V1,” *Nature* (2008):
  https://doi.org/10.1038/nature07141
- Salvan et al., “Serotonin regulation of behavior via large-scale
  neuromodulation of serotonin receptor networks,” *Nature Neuroscience*
  (2023): https://doi.org/10.1038/s41593-022-01213-3
- Michaluk, Heller, and Rusakov, “Rapid recycling of glutamate transporters on
  the astroglial surface,” *eLife* (2021):
  https://doi.org/10.7554/eLife.64714
- Soden, Yee, and Zweifel, “Circuit coordination of opposing neuropeptide and
  neurotransmitter signals,” *Nature* (2023):
  https://doi.org/10.1038/s41586-023-06246-7
- “Stochastic neuropeptide signals compete to calibrate the rate of
  satiation,” *Nature* (2025):
  https://doi.org/10.1038/s41586-024-08164-8
- Badimon et al., “Negative feedback control of neuronal activity by
  microglia,” *Nature* (2020):
  https://doi.org/10.1038/s41586-020-2777-8
- Wilson and Nicoll, “Endogenous cannabinoids mediate retrograde signalling at
  hippocampal synapses,” *Nature* (2001):
  https://doi.org/10.1038/35069076
- Krok et al., “Intrinsic dopamine and acetylcholine dynamics in the striatum
  of mice,” *Nature* (2023):
  https://doi.org/10.1038/s41586-023-05995-9
- Stavreva et al., “Ultradian hormone stimulation induces glucocorticoid
  receptor-mediated pulses of gene transcription,” *Nature Cell Biology*
  (2009): https://doi.org/10.1038/ncb1922
- Fultz et al., “Coupled electrophysiological, hemodynamic, and cerebrospinal
  fluid oscillations in human sleep,” *Science* (2019):
  https://doi.org/10.1126/science.aax5440
- Xie et al., “Sleep drives metabolite clearance from the adult brain,”
  *Science* (2013): https://doi.org/10.1126/science.1241224
- Dong et al., “Unlocking opioid neuropeptide dynamics with genetically
  encoded biosensors,” *Nature Neuroscience* (2024):
  https://doi.org/10.1038/s41593-024-01697-1

These experiments establish the structural requirements above. They do not
ratify Guala's numerical coefficients.
