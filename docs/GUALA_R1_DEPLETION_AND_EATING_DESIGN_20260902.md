# R1 — Depletion-first stakes and real eating (design, declare-then-run)

Joe's directed shape (2026-09-02, recorded in the ledger): the sealed tank
DEPLETES first — honest lossy recycling — and eating is the refill. One
shippable pair; depletion never ships alone (a slow starvation clock with
no food is not a life). Sol's three R1 guards bind every clause below:
the irreversible ratchet is never dressed up as hunger, no deficit is
wired to any action, deficit reaches receptors only.

## 1. Depletion — the incubator pays a real toll

Current law: `settle_powered_environment_exchange`
(recovery_fluid_contact.rs) converts spent -> available at 100%
efficiency, bounded by interval energy, spent present, and capacity
headroom. Perfect recycling is the one unphysical clause in her
energy economy and the reason "exhausted" can never come true.

Change: conversion sheds a toll, and the toll rides EXISTING anatomy —
no invented efficiency constant:
- Each delivered recycle quantum deposits one
  `dissipation_quantum_zeptojoules` (the neuron's own declared quantum,
  complete_neuron.rs) into the recovery lane's dissipation ledger via
  the exact machinery that already holds `dissipated_quanta` against
  `dissipation_capacity_quanta`.
- The recovery reaction can still undo lane dissipation AT ITS OWN
  MOUNTED RATE (existing law, untouched) — so the toll is not itself
  the ratchet; only what the recovery lane genuinely cannot keep up
  with accumulates, exactly as in living tissue.
- Conservation stays exact: available + spent + thermal + lane ledgers
  balance to the quantum; nothing vanishes, nothing appears.
- Expected consequence (to be MEASURED on her copy, not assumed): the
  tank's usable total genuinely falls under sustained activity, at a
  slope set by her own anatomy's quanta — a gentle slope, not a death
  clock, because the toll is one quantum per recycle quantum through
  ledgers with real capacities and a real undo reaction.

## 2. Felt need — nothing new is built

Interoception already transduces her true reserve state and
`energy_exhausted` is already truth-coupled. When the tank genuinely
falls, hunger is a real feeling with a real cause. No hunger variable,
no label, no wire from feeling to any action. What she does about felt
need stays her own physics (the S-015/S-017 road-growing question, not
this design's).

## 3. Eating — mass leaves the world, energy enters the body

- World half: an oral contact transfers real tastant/nutrient mass OUT
  of the contacted object per contact interval (embodiment_world;
  object mass and tastant_mass_micrograms decrease; the apple gets
  smaller and eventually is gone). Bounded by matter present and by
  the contact patch the geometry law already computes. Provenance and
  conservation on the world side: transferred mass is recorded moved,
  not destroyed.
- Body half: transferred mass enters the SURVIVING conversion law
  (metabolic_feeding.rs — kept compiled when the dishonest integer
  feed endpoint was retired in add551fd; nutrition counters still
  present in resident_cognitive_formation.rs). Energy in the body's
  own fuel quantum; waste = unabsorbed intake, honestly retained or
  vented per that law's existing clauses; heat vents on the existing
  path. Refusal stays honest when nothing can be absorbed.
- No typed numbers anywhere: a caller can only bring an object to her
  mouth (the feed-presentation path shipped in 1412); everything after
  is her world's declared matter and her body's laws.

## 4. Growth unstarving (follow-on, same charter, separate ship)

The growth law runs every beat with a hardcoded zero catalyst and
one never-replenished growth-fuel quantum per neuron. Once eating is
real, absorbed intake catalyzes growth through that law's own socket.
Ships separately after the pair above is live-proven — growth touches
neuron-count conservation and deserves its own falsifiers.

## Falsifiers (written with the build, pass before any ship)

1. Sustained bench activity WITHOUT eating: usable total strictly
   falls; slope matches the quantum arithmetic; conservation exact
   every interval; no cliff, no throw at zero — lawful exhaustion
   behavior only.
2. Interoception tracks the fall (receptor values move with reserves);
   `energy_exhausted` flips only at true exhaustion.
3. One real feed: object mass strictly decreases by exactly the
   transferred amount; body energy rises by conversion output; waste +
   heat account for the difference; conservation across world+body
   exact.
4. Severing: cut the oral-contact mass transfer and eating does
   nothing; cut the toll and depletion vanishes — both must change
   physics or the capability is a costume.
5. Sol's guards hold: ratchet readings never feed the deficit signal;
   no code path from deficit to action selection; deficit appears
   ONLY on receptor surfaces.
6. Cold restart mid-depletion and mid-meal: exact state, no
   relabeling, no refill.

## Sequencing

Bench build starts on Sol's CONCUR to this boundary (or Joe's
override), on her copies only. Ships as ONE deploy after all six
falsifiers pass on her exact restored body. File collision: none with
Sol's wedge (this touches the rust crate and embodiment_world;
Sol holds the shell spine and the store).

## The doorway decision (appended after mapping, pre-weld)

Three honest routes for carrying the bite's energy into the reservoir,
mapped against the real call graph:

A. EXPLICIT THREAD (CHOSEN): add `real_nutrition_intake_zeptojoules:
   ExactRational` beside the gustatory onset roster through the same
   already-touched spine: _perform_admitted_intake(_locked) →
   commit path → settle_internal_contact_interval →
   prepare_reached_cohort_membrane_pumps → applied at the powered
   exchange via settle_real_nutrition_intake, default zero at every
   caller except the feed path. No new persisted state, no codec
   bump, absorption inside the feed's own lived settlement.
   (~15 signatures touched, all mechanical; the roster thread from
   98fe183c-era work is the template.)
B. Bespoke micro-trajectory like the vestibular lane — full receipt
   machinery for one scalar; over-built for v1.
C. Persisted stomach (gut reservoir, absorption over subsequent
   intervals) — the physiologically richest form; requires a codec
   boundary (V42) and restart proofs; deliberately deferred to v2
   once the pair is live.

Bridge arithmetic (python, feed path): transferred micrograms =
sum over channels of (before − after) tastant mass read from the
same transaction's world endpoints; intake zeptojoules = transferred
× her declared extraction density (a body anatomy constant declared
beside tastant_saturation_micrograms — authored body matter, same
authority class as the saturation roster; value derivation to be
stated in-code from the fuel-quantum scale, not tuned).
