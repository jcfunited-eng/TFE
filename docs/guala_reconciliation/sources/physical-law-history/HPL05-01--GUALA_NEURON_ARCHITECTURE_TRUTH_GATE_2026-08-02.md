# Guala neuron architecture truth gate — 2026-08-02

## Status

This document is an implementation gate, not a claim that the neuron
architecture is complete.  It records the live code and production evidence
that must be reconciled before another neuron implementation is accepted.

The referenced `GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-74` specification is not
present in the repository.  The surviving Stage-1 report is evidence of an
isolated test implementation, not sufficient authority for a final neuron
design.

## Requested architecture

Guala must grow from a small immature substrate toward a potentially enormous
population of neurons.  The seven canonical fields
`D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k` participate throughout that substrate;
they are not one scalar or one seven-field result for an entire experience.

Compactness may come from retaining immutable evidence once and using exact
causal references.  It must not come from collapsing distinct field material,
neurons, occurrences, or learned relationships into a score, class, lookup
key, compatibility vector, or fixed-size history.

The relationship between a canonical L4 field tuple and a neuron has not yet
been recovered from an authoritative design.  No implementation may invent
that relationship.

## Current code reality: two incompatible neuron species

### Older `LoomNeuron`

Source: `dsf_ai_service/loom_model/neuron.py`.

This Python object contains the mechanisms named by the surviving 15-piece
Stage-1 report: a psi lattice, spike buffer, couplings, familiarity feedback,
law fields, DNA expression site, trit register, DSF computation, L6-TCL,
balanced-ternary helpers, a physical oscillator, a sensory oscillator bank,
Grandurun projection, and spin-vector dimensional constants.  The report also
counts the `LoomNeuron` container itself as one of the fifteen.

Later additions include membrane/refractory state, a spike-bus surface, STDP
weights and timing history, metabolic energy, firing controls, folding/division
state, and mood modulation.

Evidence conflicts:

- several of the named fifteen are imported functions or constants rather than
  per-neuron physical state;
- the trit register and sensory oscillator bank are constructed but are not
  used by the neuron transition path;
- the spike-bus and mood surfaces have no mounted production call site;
- the neuron recomputes an older floating-point DSF from its latest local event
  window and overwrites `_last_dsf`;
- daughter construction reduces selected DSF values into normalized law
  weights and a connection count;
- it does not consume the canonical native full-field bank;
- the original report used a literal string stimulus and a retired Chi atlas,
  and explicitly stated that it had no production substrate import or deploy.

### Newer `WholeOrganismNeuron`

Source: `dsf_ai_service/substrate/whole_organism_neuron_population.py`.

This frozen Python record contains:

- a conventionally derived neuron identifier;
- receptor mechanism, sense, sensor, substream, topology and coordinates;
- exact ordered seven-field tuples with source spans and receipts;
- source, transduction, custody, kernel-basin and boundary receipts;
- copied complete L0-L4 trace JSON and last perturbed evidence JSON;
- a retained response trajectory;
- current local receptor activation;
- signed topology-only causal couplings.

Evidence conflicts:

- it contains none of the older neuron's psi, trit, oscillator, L6, membrane,
  spike, plasticity, metabolism, or folding mechanisms;
- identity is a hash of manifest/mechanism/sense/sensor/substream/topology, not
  a demonstrated causal consequence of the substrate physics;
- edges are current receptor-neighbor records rather than learned field-bearing
  connection dynamics;
- quiescence replaces current exact field values with synthetic zero values;
- response history is truncated to a fixed count;
- complete evidence and trace JSON is copied into many neuron/response records;
- prepare/commit/rollback is controlled by a separate Python owner.

The separate `AuditoryMotifNeuron` is a third, reduced representation.  It
stores qualitative peak relations and strength rather than the complete
seven-field body.  It cannot be treated as the same authoritative neuron.

## Live production evidence

Read-only observation source:
`https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com/api/v1/gualaloom/observation`.

Observed organism tick: `23723830`.

- neuron count: `210`;
- neuron state bytes: `43,616,653`;
- mean encoded bytes per reported neuron: approximately `207,698`;
- topology edges: `902`;
- reported neuron capacity: `369`;
- reported state capacity: `67,108,864` bytes;
- response-history capacity: `16`;
- tuple-per-neuron capacity: `1,024`;
- division/growth: unavailable, reason `no_authenticated_division_law`;
- cognition activity: unavailable, reason
  `no_scheduler_activity_observed`;
- causal action-cycle perceptions/intents/executions/outcomes: all `0`;
- completed glyph lessons: `0`;
- autonomous driver completed count: `27`, but no corresponding causal
  action-cycle evidence exists.

These figures prove that the immature population is already bulky while its
claimed cognitive and growth mechanisms are disconnected.

## Mechanisms that must not be extended

- the Python `LoomNeuron` transition as the final neuron;
- topology strings/hashes as unquestioned neuronal identity physics;
- synthetic zero-field quiescence;
- fixed cognitive history, neuron, edge, or tuple caps;
- copied full evidence/trace JSON per neuron and response;
- reduced daughter law-weight or connection-count projections as full-field
  inheritance;
- separate owner mutation, job, queue, registry, or database logic presented
  as neuronal cognition;
- auditory qualitative motif records presented as the full neuron;
- Chi, Atlas, words, labels, semantic classes, or ML as identity or meaning.

## Recommended architecture decision

Use one native neuronal kind, not parallel cognitive and receptor species.
Sensory specialization should be a physically mounted interface of that
neuronal kind, while non-sensory neurons remain possible without fabricated
receptor evidence.  The fifteen named mechanisms must first be classified as
one of:

1. durable per-neuron physical state;
2. shared substrate operation applied to a neuron;
3. population/organism mechanism rather than a neuron part;
4. rejected legacy or heuristic mechanism.

This classification is not yet approved physics.  It is the recommended next
architecture decision because directly merging the two current Python classes
would preserve both wrong designs and duplicate their state.

## Required proof before implementation

The neuron invariant must state, without guessing:

- what causes a neuron to exist and remain continuous;
- how the complete DSF field participates in a neuron without flattening;
- which of the fifteen named mechanisms are actual neuron state;
- how connections form and change causally;
- how a neuron becomes quiescent without falsifying its last learned state;
- what creates a daughter neuron without heuristic thresholds or arbitrary
  population caps;
- which evidence is transient, which exact body is retained once, and which
  causal references are stored by neurons and experiences;
- how persistent byte growth is derived from actual new physical structure;
- how one native organism transition advances neurons, mosaics, tapestries,
  weaves, embodiment, needs, attention, action, consequence, play, dream and
  tutoring together.

No neuron implementation or migration can pass until this invariant is
explicit and the current two-species conflict is resolved.
