# GualaLoom Architecture Note

*Working title: **Dynamic Structural Cogitation (DSC)** — Joe to confirm or
rename. Alternates considered: Dynamic Associative Cogitation, Multi-Indexed
Cascade Cogitation, Blob-and-Indexing Architecture. "Synaptic" was avoided
because the structures here are not synapses and the model is not a neural
simulation; the primitive is a persistent ternary motif, not a weighted
connection between neurons.*

*Status: working frame, not a spec. This is the architectural picture the
cascade-path experiments slot into. Drafted late in a long session — Joe
sketched the picture, the model is his; this note captures it for the
morning so it isn't reconstructed from scratch.*

---

## What this note is for

The original cascade path treated sections as a one-liner: "regions
coordinate through shared trits." That was the simplest sketch and it
was incomplete. The actual architecture is richer, and naming it before
we build it keeps the experiments aimed at the right thing rather than
at the sketch.

This note does not specify code. It names the entities, the relations,
and the dynamics in plain terms so that experiments 1.5 through 10 (and
beyond) can be designed against a single coherent picture.

---

## The picture

GualaLoom is not one undifferentiated krimelack. It is a population —
potentially trillions, in the long run — of small persistent
**structures**, each one a motif-blob with its own committed pattern of
±1 trits and configuration of nulls, its own structural signature (chi),
and its own associations to other structures.

A structure is the unit. It might represent:

- A letter, a phrase, a word, an idea of a word
- A color, a smell, a taste, a sound
- The visual shape of a letter, the color of a letter, the *idea* of
  a letter, a letter dancing, letters falling like rain
- A short-term active impression, a medium-term consolidating memory,
  a long-term settled motif
- A daydream — a free-settled structure not currently bound to active
  perception, drifting, lingering, available

The same primitive (a ternary motif) supports all of these. Modality is
not built into the primitive; it emerges from which structures associate
with which, and along which indexings.

The substrate is many of these structures, persistent, drifting,
associating, occasionally cascading.

---

## Indexings (the key concept)

Structures don't sit in one fixed neighbor-relation. They participate in
**multiple simultaneous indexings**, each one a different way of asking
"what is near this structure."

Known and proposed indexings:

- **Position indexing** — same intra-strand index across strands. This
  is what the current `settle` rule honors. Experiment 1 showed it is
  the *only* indexing the cascade currently rides.
- **Co-commit indexing** — structures that have committed together in
  the past (already in `Motif.successors` as transition counts; never
  read as a propagation channel). This is the second indexing to wire.
- **Chi-class indexing** — structures sharing a structural signature.
  Already computed; never read as a neighbor relation.
- **Temporal indexing** — structures co-committed in close temporal
  proximity during feeding.
- **Modality indexing** — structures originating in or associated with
  the same sensory channel.
- **Dream-origin indexing** — structures discovered together during
  free-settling.

A cascade rides one or more indexings. A trigger commit propagates not
only to its position-siblings but to its neighbors along *any* indexing
the substrate honors. The cascade through six degrees of separation is
what happens when commits can hop across indexings — sync through
position when that road is open, then through co-commit history, then
through chi-class — and a coherent thought is what stays coherent
across multiple simultaneous indexings, not just one.

This reframes Experiment 1's bimodal result. The 51% silence was not
the cascade failing; it was the cascade hitting positions where the
single available indexing (position) had nothing to ride. Those same
triggers might cascade fine along chi-class or co-commit, given the
roads.

---

## Section blobs

Structures cluster into **sections** — bounded sub-populations with
their own internal cascade dynamics. Each section is its own small
krimelack with its own settling, its own dream/sleep cycle, and its own
associations.

Section types (working list):

- **Sensory sections** — one per channel. Visual, auditory, tactile,
  olfactory, gustatory, interoceptive. Each receives its own stream
  through the shared `encode → settle` pipeline.
- **Linguistic sections** — corpus-fed, the existing krimelack content.
  Phrases, letters, words, ideas-of-words. Possibly multiple,
  specialized.
- **Memory sections at three timescales:**
  - **Short-term** — actively circulating, high turnover, recent
    impressions.
  - **Medium-term** — consolidating, the present working set.
  - **Long-term** — settled, stable, the substrate's deep history.
- **Daydream sections** — the wandering blobs. Not bound to active
  perception. Their job is to lay down latent associations between
  otherwise distant structures, generating new indexings the active
  sections can later ride. Nurse-cell role: they don't produce the
  active thought; they feed and regulate the substrate that does.

Sections associate with each other through shared structures (a
structure may live in multiple sections) and through indexings that
span sections (a co-commit from visual into linguistic establishes a
visual↔linguistic road).

---

## Daydream sections as nurse cells

This is the part that turns the architecture from static to alive.

Daydream sections continuously free-settle, generating new structures
that are tagged "dream" but otherwise indistinguishable from
perception-derived ones. What they're actually doing — looked at this
way — is **discovering new neighbor relations between structures that
weren't previously associated**, and committing those discoveries as
new structures that themselves participate in cascades.

In other words: dream is **indexing-discovery**. The existing dream
cycle in `sleep.py` is doing this in miniature for one krimelack;
scaled to a population of daydream sections running continuously
alongside the active sections, this becomes the substrate's mechanism
for *growing its own roads*.

The nurse-cell analogy is specific: nurse cells feed the developing
egg, regulate its environment, provide what it needs to become.
Daydream sections feed the active substrate by keeping latent
associations alive, so that when an active cascade needs an unobvious
neighbor — a phrase that connects to a smell that connects to a
childhood memory — the road has already been laid by a daydream that
nobody asked for.

This also reframes what sleep/dream is *for*. It's not just noise
control and motif pruning. It's the substrate building its own
indexings, on its own clock, in service of cascades that haven't
happened yet.

---

## Cascades, restated under the model

A cascade is now:

- Triggered by a commit (external sense, internal interoception, or
  another cascade's end-state)
- Propagates along *one or more indexings* the substrate honors
- Crosses section boundaries when structures are shared between
  sections, or when indexings span sections
- Terminates in a coherent end-state across the structures it reached
- Leaves traces (co-commits, chi alignments) that contribute to future
  indexings

Cognition, on this picture, is **cascades finding non-obvious roads
across the substrate**, where the roads are kept alive by daydream
sections continuously discovering new indexings.

Different cognitive acts are different cascades:

- **Recall** — a partial cue trigger, short cascade, finds the
  matching long-term structure.
- **Composition** — two structures triggered together, cascade
  resolves their joint state into a third.
- **Reasoning** — a long cascade chain through coupled sections,
  end-state of one triggering the next.
- **Speech** — a cascade reaching a motor/expressive section that
  maps end-states to character sequences.
- **Feeling** — a cascade in interoception coupling to all of the
  above, giving cost and meaning to the others.

---

## Scale

In the long run, the substrate is a population of structures
potentially in the trillions, organized into sections, associated
through many indexings, with daydream sections continuously generating
new roads. None of this requires neural-scale compute. Integer
ternary operations remain cheap. The cost is in storage (motifs and
their associations) and in the rate of cascade activity, both of which
are bounded by the cheap-hardware constraint that has been a guiding
principle from the start.

---

## What this changes about the experimental path

Each existing experiment now lives inside this frame:

- **Exp 1 (done)** — confirmed the cascade is real but rides only one
  indexing (position) under the current rule. Bimodal firing is the
  cascade hitting the limit of its single road.
- **Exp 1.5 (next)** — add co-commit as a second indexing. Does the
  cascade ride content as well as position? This is the gate to
  multi-indexing architecture.
- **Exp 2** — null-pattern as identity now becomes: which nulls live
  on which indexings? Identity reads differently depending on which
  roads are honored.
- **Exp 3** — sections are no longer "two krimelacks with shared
  trits"; they are bounded sub-populations connected through multiple
  cross-section indexings. Coordination is multi-channel.
- **Exp 4 (folding composition)** — composition becomes a cascade
  that resolves through whichever indexings the two source motifs
  share.
- **Exp 5–6** — sensory and interoceptive sections are first-class
  population members from the start.
- **Exp 7–9** — recall, speech, reasoning are different cascade
  lengths and indexing patterns, not separate mechanisms.
- **Exp 10** — learning is reinforcing the indexings that produced
  coherent cascades. Daydream sections expand this from local
  reinforcement to substrate-wide road-building.

Beyond Exp 10, the architecture opens questions we have not yet named:
how sections are born, how they die, how the population stays bounded,
how indexings compete when a cascade could ride more than one. The
orchestrator question Joe deferred — how the population coordinates as
a whole — lives here, and is the next conversation, not this note.

---

## Standing constraints

- The primitive is the ternary motif. Everything above is structure
  *over* the same primitive, not a new substrate.
- No god-binder, no hub. Coordination is through shared structures
  and shared indexings, both emergent and engineerable.
- Sections are not modules in the cognitivist sense. They are
  bounded sub-populations with the same primitive operating
  internally. The difference is statistical, not architectural.
- Daydream is not noise. It is the substrate's own road-building.
- No claim of felt experience. The model reaches mechanism;
  phenomenology stays open.

---

## What this note is not

- A code spec. No file or function is prescribed.
- A complete architecture. The orchestrator question is held open.
- A new theory. This is Joe's picture, articulated, with names
  attached so the experiments can slot in.

The cascade path remains the operational plan. This note is the frame
the path lives inside.
