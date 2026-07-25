# Guala Bioequivalent Chemical Transduction Candidate v1.0

Status: proposed research candidate; not ratified  
Date: 2026-07-13  
Implementation authority: none  
Production status: not implemented or deployed  
Kernel status: frozen L0-L4 remains unchanged

## Architecture honesty gate

1. Requested architecture: sensory chemistry and field mechanics must jointly provide relevance, adaptation, recovery, and lived persistence for the Guala AE. The story emulator must be replaceable by embodied sensing.
2. Current code reality: no active, mass-conserving native transduction profile supplies GLEW relevance. Current sensory emulation uses predetermined curves, thresholds, clamps, resets, or arbitrary resource units.
3. Conflict with requested architecture: yes.
4. Mechanisms that must not be extended: the L0 `D/(D+tau_D)` diagnostic, static Hill/exponential descriptor waveforms, clamped visual adaptation, arbitrary neuron energy, NMDA Boolean gating, MapInject products, lookup relevance, or legacy compatibility fields.
5. Single exact next item: ratify the native-transduction receipt classes and the boundary to any common synthetic receiving chemistry.
6. Full field or reduced approximation: this document specifies upstream physical providers for the full field path; it is not a DSF reduction.
7. Structure lost by the current approximation: modality-specific receptor/channel state, messenger cascades, electrochemical gradients, tonic/phasic ports, depletion, recovery, polarity, energy, mass, and uncertainty.

## Correction to the earlier candidate

The earlier draft proposed one reversible receptor network for every signed lane:

\[
R+L\rightleftharpoons C\rightleftharpoons D.
\]

That network is defensible for some ligand-binding receiving systems. It is not the common biology of sight, hearing, touch, smell, and taste.

- Vision is photon-driven photopigment and cGMP chemistry.
- Hearing is force-gated mechanotransduction followed by ion flow and ribbon release.
- Touch contains several mechanoreceptor families and both direct-neurite and receptor-cell paths.
- Smell uses ligand-binding GPCR chemistry plus a longer-lived messenger/adaptation cascade.
- Sweet, bitter, and umami use GPCR pathways; sour and sodium taste use direct electrochemical channels.

The universal authority can therefore be a receipt contract and a deterministic reaction/channel engine. It cannot be one forced reaction topology.

## Common physical-receipt contract

Each mounted transducer must declare and hash:

- native physical states and their units;
- stoichiometric reactions or channel-state transitions;
- conserved pools and open reservoirs;
- external boundary fluxes and work sources;
- forward and reverse kinetic intervals with provenance;
- temperature, geometry, volume, activities, and membrane potential where applicable;
- initial state and persistent recovery state;
- every native output port and whether it is tonic or phasic;
- the exact physical coupler from a native output port to the GLEW input;
- interval validity, unknown, and failure rules.

No equilibrium lookup, fitted Hill curve, hard threshold, reset, per-window maximum normalization, or desired-language-result selector may replace this contract.

## Native sight receipt class

The minimum rod receipt includes:

1. photon isomerization of rhodopsin;
2. active rhodopsin activation of transducin and PDE6;
3. PDE6 hydrolysis of cGMP;
4. cGMP-gated channel closure and photocurrent change;
5. calcium-dependent recovery;
6. rhodopsin phosphorylation/arrestin quenching;
7. ribbon-synapse glutamate release as a separate output port.

The receipt must preserve photopigment, G-protein/PDE, cGMP, calcium, channel, photocurrent, and release states as distinct facts. Dark current and dark glutamate release are tonic; light produces a signed reduction and an adapted background state.

Research anchors, not emulator defaults:

- amphibian preparations reported approximately 120-150 transducin or PDE activations per active rhodopsin per second under the reported assay conditions;
- mouse active-rhodopsin deactivation was approximately 36-40 ms;
- rat rod time-to-peak changed from about 9.3 s at 5 degrees C to 0.15 s at 36 degrees C.

These values are species-, temperature-, preparation-, and state-specific. Rod values cannot be assigned to cones.

Primary sources:

- Leskov et al., https://www.sciencedirect.com/science/article/pii/S0896627300000635
- Gross and Burns, https://pmc.ncbi.nlm.nih.gov/articles/PMC2841010/
- Nymark et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC1474229/
- Native rod ribbon output, https://pmc.ncbi.nlm.nih.gov/articles/PMC7664508/

## Native hearing receipt class

The minimum cochlear receipt includes:

1. tip-link force and mechanical displacement;
2. TMC1/TMC2-containing mechanotransduction-channel state;
3. electrochemical cation current;
4. hair-cell membrane potential and calcium entry;
5. ribbon-vesicle pool, fusion, replenishment, and endocytosis;
6. afferent release flux as a separate output port.

The fast peak, adapted plateau, readily releasable vesicle pool, and sustained supply must remain distinguishable.

Research anchors, not defaults:

- rat cochlear hair-cell adaptation components were reported over approximately 0.1-5 ms, with larger-stimulus components over approximately 8-50 ms at 18-22 degrees C;
- mouse inner-hair-cell experiments reported a readily releasable pool near 280 vesicles, recovery components near 140 ms and 3 s, maximal supply near 1,200 vesicles/s, and endocytosis near 7.5 s under the reported preparations.

Primary sources:

- Peng et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC4111567/
- TMC1/TMC2 experiment, https://pmc.ncbi.nlm.nih.gov/articles/PMC3827726/
- Moser and Beutner, https://pmc.ncbi.nlm.nih.gov/articles/PMC15425/

## Native touch receipt classes

`touch` is not one transducer. At minimum, dynamic direct-afferent touch and static Merkel-cell-supported touch must remain distinct until a physical downstream circuit combines them.

A Merkel/afferent receipt includes:

1. force and tissue mechanics;
2. Piezo2 closed/open/inactivated channel population;
3. direct sensory-neurite current;
4. Merkel-cell current, membrane potential, calcium, and vesicle state;
5. separate dynamic and static native output ports.

Research anchors, not defaults:

- native mouse Merkel cells at 32 degrees C reported about -146 pA peak and -6 pA after 125 ms, with a membrane time constant near 70 ms;
- cultured mouse Merkel cells reported about 8 ms inactivation;
- heterologous human PIEZO2 at room temperature reported about 6.2 ms inactivation and 1.08 s recovery.

Primary sources:

- Woo et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC4039622/
- Maksimovic et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC4097312/
- Coste et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC3607045/
- Merkel serotonin evidence, https://pmc.ncbi.nlm.nih.gov/articles/PMC5027443/
- Merkel norepinephrine evidence, https://pmc.ncbi.nlm.nih.gov/articles/PMC6347413/

Meissner, Pacinian, Ruffini, nociceptive, thermal, and other paths require their own receipts. Their values may not be copied into a generic touch profile.

## Native olfactory receipt class

The minimum ligand-binding GPCR receipt distinguishes binding from activation:

\[
R+L\rightleftharpoons C,qquad
C\rightleftharpoons A,qquad
A\rightarrow D,qquad
D\rightarrow R+L.
\]

- \(C\) is bound receptor;
- \(A\) is signaling receptor;
- \(D\) is unavailable/desensitized receptor only where evidenced;
- \(R_T=R+C+A+D\) is the conserved receptor pool.

The receipt must additionally preserve G-protein, cyclic-nucleotide, channel, calcium, current, and adaptation states. Binding cannot equal signaling: frog olfactory work reported odorant dwell no longer than approximately 1 ms and a low probability that one binding event activates a G protein.

Room-temperature tiger-salamander experiments using a 1-second 300 micromolar cineole exposure reported approximately:

- 296 ms receptor-current delay;
- 589 ms rise;
- 702 ms current half-recovery;
- 4.15 s ciliary-calcium half-recovery;
- 5.6 s short-term-adaptation recovery.

These are experimental receipts, not production constants.

Primary sources:

- Bhandawat et al., https://pubmed.ncbi.nlm.nih.gov/15976304/
- Dawson et al., https://pubmed.ncbi.nlm.nih.gov/8381559/
- Leinders-Zufall et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC6793047/

## Native gustatory receipt classes

### Sweet, bitter, and umami

These use receptor/G-protein pathways with a downstream sequence including PLC-beta-2, IP3/calcium, TRPM5, depolarization, CALHM1/CALHM3, and ATP release. Receptor state, messenger state, channel state, and ATP-release flux remain separate.

Research anchors, not defaults:

- heterologous human TRPM5 at 21-25 degrees C reported seconds-scale rise and approximately 6.1-6.3 s inactivation constants at the reported calcium concentrations;
- native-like CALHM1/CALHM3 activation was reported near 10 ms, while CALHM1 alone exceeded 500 ms under the cited preparations;
- TRPM5 behavior changes strongly with temperature.

Primary sources:

- Zhang et al., https://pubmed.ncbi.nlm.nih.gov/12581520/
- Prawitt et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC299937/
- Ma et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC5934295/
- Talavera et al., https://www.nature.com/articles/nature04248

### Sour

Sour uses OTOP1 proton-channel/electrochemical physics rather than ligand-binding GPCR chemistry:

\[
O_{closed}\rightleftharpoons O_{open},qquad
J_H=g_OP_{open}\Delta\mu_H.
\]

The channel population is conserved; proton inventory follows membrane flux, buffering, and pump/exchanger balance.

Mouse OTOP1 in HEK-293 cells at pH 5.5 and -80 mV reported approximately 143 ms activation and 18.6 ms removal/deactivation. The paper did not state a universal temperature or authority for other preparations.

Primary sources:

- Chen et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC9348849/
- Teng et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC7299528/

### Sodium taste

Low-sodium mouse taste uses direct ENaC-mediated sodium flux:

\[
J_{Na}=g_{ENaC}P_{open}\Delta\mu_{Na}.
\]

Channel population and charge are conserved; sodium is open to saliva and pump reservoirs. Mouse ENaC evidence may not be generalized to human salt taste, and the cited knockout study does not establish a universal kinetic rate.

Primary source:

- Chandrashekar et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC2849629/

## Native-to-synthetic boundary

A common receiving chemistry is defensible only as an explicitly synthetic GLEW layer after native transduction:

`native modality physics -> certified native output port -> calibrated modality-specific coupler -> ledgered internal messenger parcels -> common synthetic receiver`

The coupler must preserve modality, sign relative to the native baseline, tonic/phasic identity, time, units, uncertainty, and provenance. It must not delete or replace native state.

A reversible synthetic receiver may use:

\[
R+L\rightleftharpoons C\rightleftharpoons D
\]

only after its artificial meaning is declared. Its kinetic values cannot be copied from the native biological research above.

## Relevance output conflict

No universal scalar chemical relevance operator has been ratified.

- receptor occupancy answers how much receptor structure is bound;
- active-receptor occupancy answers how much receptor structure is signaling;
- ion current answers how much electrochemical flow exists;
- vesicle-release flux answers what an afferent receives;
- messenger/adaptation state carries persistence after the initiating event ends.

These ports are physically different. They cannot be averaged, weighted, or dynamically selected to improve utterance behavior.

The current six-lane GLEW profile accepts one scalar waveform per sense. Real senses expose multiple ports and receptor classes. A sense profile must either prove one native downstream port as the authoritative lane input or the GLEW lane schema must be expanded without flattening. This is an explicit upstream blocker.

## Typed-language boundary

Unicode text is not a biological receptor or ligand. Typed v1 input may have an explicitly artificial, fully receipted interface boundary, or biological language experience may arrive through sight/sound with decoded text retained as annotation. No language-lane chemical relevance operator is ratified.

## Time, persistence, and Negative Space

- Native and synthetic transducer state persists across gates, sleep, restart, and recall.
- Sleep may evolve the same physical equations under declared boundary conditions; it may not reset state.
- Negative Space does not force chemistry or channel state to zero.
- A chemical or channel output is zero only when its certified enclosure proves zero.
- Missing or indeterminate state is `unknown`, never numeric zero or `not_applicable`.
- Physical time is local to each reaction/channel process and follows measured rates, activation barriers, concentrations, force, voltage, temperature, and geometry—not a ubiquitous timeout.

## Deterministic numerical authority

Mass-action and channel systems generally produce non-rational states. Certified interval evolution is required.

- FLINT/Arb is certified arithmetic, not a complete validated ODE solver.
- Nonlinear native chemistry requires a pinned interval Taylor/Lohner or equivalent validated integrator.
- State enclosures must preserve correlations and conservation laws.
- Nominal-value selection, midpoint substitution, clamping, and post-normalization are forbidden.
- An indeterminate proof is `unknown` with no mutation.

CAPD::DynSys remains a researched solver candidate: https://doi.org/10.1016/j.cnsns.2020.105578

## Recommendation

Ratify the common physical-receipt contract and the native modality receipt classes. Treat the reversible receptor network only as a declared synthetic receiving layer or a sense-specific ligand-receptor profile. Do not ratify one universal sensory topology or one universal scalar relevance port.

