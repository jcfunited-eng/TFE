# Guala D3 disjoint local-contact transition candidate

Date: 2026-08-03

Status: isolated and unmounted. This candidate verifies and settles already
observed disjoint physical contacts. It does not derive spatial geometry,
transport material into contact, or prove a complete biological reaction.

## Architecture honesty gate

1. **Requested architecture:** deterministic local reaction opportunity without
   a central allocator, identifier priority, score, or software owner.
2. **Current code reality:** a geometry observation names exact location,
   interval, predecessor index, and occupied reactant quantities. The candidate
   validates and canonicalizes that observation against an anatomy-bound state,
   rejects overlapping lanes, and derives the extent itself.
3. **Conflict:** no for settlement after a truthful geometry observation; yes
   for geometry, transport, shared-reservoir allocation, and organism wiring.
4. **Not extended:** reaction queues, first-wins order, equal-share rounding,
   random propensity, caller-supplied extents, hash identity, locks, databases,
   owners, ML, scores, and validation used as reaction dynamics.
5. **Single next item:** independently audit this pair before any mounting.
6. **Full field or reduced approximation:** neither; this candidate does not
   call or project DSF.
7. **Declared field loss:** not applicable.

## Exact predecessor binding

`BoundContactState` contains the complete species schema, exact interval, every
lane anatomy, current interval index, inventories, and remainders. Transition
does not accept a separate anatomy argument.

`DisjointContactOccupancy` borrows the exact predecessor from which it was
admitted. It cannot be passed to the transition with another state. The
occupancy is transient and is not serialized as independent authority.

The canonical state codec stores full structural content rather than trusting
a digest. A decoded state is reconstructed through the same schema,
conservation, width, capacity, and remainder admission laws.

## What “geometry-observed” means

An observation supplies:

- the complete physical lane location;
- the anatomy's exact interval and current interval index; and
- occupied quantities only for reactant species.

Admission scans every lane location, so incoming storage order does not choose
the successor. The matched lane is stored in canonical anatomy order. Two
observations reaching the same physical lane are rejected as unresolved
overlap; neither wins.

Anatomy admission requires lanes to be in strict structural location order.
Duplicate or permuted anatomy is refused, giving the full-state codec one
canonical lane representation without sorting or identifier priority.

The candidate verifies that occupied reactants exist in the predecessor and do
not exceed immutable contact limits. It does **not** prove that a camera,
transport law, diffusion law, membrane geometry, or collision mechanism
truthfully produced the observation. That upstream law must be implemented and
tested before mounting.

Different lanes are assumed to be distinct physical control volumes. This
candidate cannot detect that an incorrect upstream transport mechanism copied
one material quantum into two lanes. Whole-organism transport conservation
therefore remains unresolved.

## Transition

For each reached lane, the maximum eligible whole extent is the minimum of:

- each occupied reactant quantity divided by its consumption coefficient; and
- each destination's free capacity divided by its production coefficient.

The anatomy-bound fractional law settles that eligible extent with its retained
remainder. The integer stoichiometric relation then creates one successor. All
lanes read the same predecessor; products cannot feed another lane in the same
interval. Unreached lanes retain inventories and remainder unchanged. The
exact interval index advances once after all reached lanes succeed.

There is one reaction relation per physical lane in this candidate. It does not
solve several reactions competing inside one shared lane. Such a predecessor
must arrive as geometry-resolved disjoint sites, explicit later subintervals, a
single admitted multi-body relation, or no contact.

## Work and payload accounting

For successful admission and transition, the requirement reports separate
source-level counts for:

- two clock comparisons per observation;
- every observation-to-lane location comparison;
- state and occupancy species visits during admission;
- lane visits, state species/remainder copies, and extent-slot initialization;
- state reconstruction, occupancy validation, extent derivation, and successor
  species visits for every reached contact;
- one fractional settlement per contact; and
- one successor clock step.

It also reports the resident state, transient occupancy, transition, successor
anatomy, and canonical serialized payload sizes. These are exact structural
payload values, not measured machine instructions or a compiler stack bound.
There is no caller-provided runtime envelope pretending to prevent a stack
frame that already exists.

## Current falsification coverage

The strict isolated suite proves:

- two disjoint contacts settle from one immutable predecessor;
- reversing observation storage order produces the same successor;
- duplicate location contact is refused rather than prioritized;
- an alien location or interval index is refused;
- conservation and width are admitted before state creation;
- the declared successful-path work formula matches the implemented passes;
- the complete canonical codec reconstructs identical anatomy, state,
  remainder, and next successor;
- malformed structural codec identity is refused;
- 100,000 materially active intervals keep state width and work requirement
  constant; and
- no contact advances the exact clock without creating a reaction.

This does not prove spatial transport, biological coefficient derivation,
finite opposite reservoirs for open flux, global charge/material conservation,
target stack use, mounted persistence, neuron or synapse behavior, mosaic or
recall formation, cognition, DSF, D3 completion, deployment, or production.
