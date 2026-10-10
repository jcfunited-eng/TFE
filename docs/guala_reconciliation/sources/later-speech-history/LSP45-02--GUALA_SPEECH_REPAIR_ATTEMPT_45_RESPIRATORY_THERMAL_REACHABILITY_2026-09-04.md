# Guala speech repair attempt 45 — respiratory thermal reachability

## Status and boundary

This is a causal-localization record. Production was not changed. Production
remained task 1429, one desired and one running task, rollout complete, with
zero CloudWatch alarms. The live image is the attempt-44 artifact at commit
`a7398bc1b36436c887fa10f370f5a7aaf27d1141`, digest
`sha256:92c7353b8408b89148a107e12e7a7cfbc2863abb76cb6bd1d8c175ee68bdfec1`.
The resident identity remains `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`.

The exact immutable production copy is tick 434112, 112,677,154 bytes,
SHA-256 `113c7fb0bf8a58112afed7385761ae7052a0d7f4c4df176e0e78024c03c1661e`.
The exact-decoder census is SHA-256
`30b376d44e4ef2fa2f75daacfc6124cae6d82855d0096867169385af50a267d5`.

## Non-repeat boundary

Attempts 37 through 44 were re-read before this analysis. Attempt 44 already
proved bounded breath, pressure generation, exact one-timeline self-hearing,
cold restore and the accepted copied voice class. Those boundaries are not
being reopened. The new failure is reuse of the dedicated respiratory cell on
the later mature production body. It is not another tone, glottis, renderer,
or self-hearing hypothesis.

## Exact copied-body failure

The production decoder's existing retained-frontier falsifier advanced the
exact copied body through three frontiers. At clock two, two learned vocal
routes each transferred and discharged one real carrier:

- ordering `...05f6` -> layer-12 motor `...00c5`,
  `VocalTractSection0Area TowardMaximum`;
- ordering `...06ba` -> layer-12 motor `...04fb`,
  `VocalTractSection7Area TowardMinimum`.

They occurred in the same physical interval. The ordinary motor evidence was
present, but the dedicated layer-13 lineage `...008e` produced zero
articulatory recruitment, zero respiratory carriers and zero acoustic pressure.
The exact report is
`/tmp/guala-speech1429-sequence.dpHRJX/sequence-range.json`, SHA-256
`0312ae1419e1b59d99264506d56cd08edf42c39c7c73f86e89aca4c55802ce59`.

The real Python production caller was then run against the same immutable body
for 32 silent 250-ms hops using the exact task-1429 native wheel. It advanced
only the disposable copy and rejected before rendering with
`copied-body range produced no respiratory recruitment`. No report or WAV was
accepted. Production and the immutable input stayed unchanged.

## Complete cause

The dedicated cell is electrically isolated by explicit V41 invariant. The
copied body has no electrical contact incident to layer 13. Its local state is:

- membrane charge `-804` carriers;
- intracellular/extracellular carriers `873076/874684`;
- reservoir available/spent energy `129/0` zJ;
- reservoir thermal energy
  `56330636062545499109551911 / 437500000000000000000000` zJ,
  or approximately `128.755739571533` zJ;
- thermal capacity `129` zJ, leaving exactly
  `106863937454500890448089 / 437500000000000000000000` zJ,
  or approximately `0.244260428467` zJ of headroom.

`settle_internal_contact_interval` sums the two learned vocal-motor discharges
and asks the isolated cell for a two-carrier efferent discharge. From the
cell's exact capacitance, reversal potential, compartment populations and
membrane charge, the existing complete-neuron energy law gives released work

`16007006262692420472753 / 50000000000000000000000` zJ,

or approximately `0.320140125254` zJ. One carrier would release
approximately `0.160070154304` zJ and fit; the real two-carrier request exceeds
headroom by approximately `0.075879696786` zJ.

`deposit_passive_return_work` therefore returns `None`. The caller commits the
layer-13 neuron and appends `ArticulatoryUnitRecruitment` only inside the
`Some(successor_reservoir)` branch. The two real vocal motor acts consequently
vanish at the respiratory boundary without an error or refusal record.

The capacity is not the root defect. It exposed an omitted physical settlement.
The cell had approximately `29.476946232200` zJ thermal energy and charge
`-184` in the pre-deploy tick-422797 copy. It now holds approximately
`128.755739571533` zJ and charge `-804`. Across 620 outward carriers, thermal
energy grew by approximately `99.278793339332` zJ, an average
`0.160127086031` zJ per carrier, exactly the scale of its membrane-gradient
release.

Every ordinary reached cohort passes through
`prepare_reached_cohort_membrane_pumps`, which first calls the existing bounded
`settle_powered_environment_exchange` and exports physically present heat.
The layer-13 cell cannot enter that route: it has no source site, is forbidden
from having electrical contacts, and its special co-recruitment happens only
after selected-cohort metabolism has already settled. Passive return does not
select its cohort for environment exchange either. Successful voice acts thus
deposit heat into this isolated cohort, while silence and rest can never cool
it. Once the remaining headroom is smaller than the next discharge, speech is
permanently mute across restart because the full reservoir is correctly
persisted.

## Repair mechanism and causal impact

The respiratory cell must pass through the same existing reached-cohort
metabolic settlement as every other neuron when a learned vocal-motor act
co-recruits it, before its efferent terminal discharge. This exports only heat
actually present, pumps only the reached dedicated neuron under its authored
one-channel power and finite reservoir, and then lets the terminal deposit the
newly released work normally. It is metabolic service of the recruited motor
unit, not free cooling, a reset, a larger capacity, or a speech exception.

- L0-L4, all seven DSF fields, MathLoom, Psi and Krimelack remain unchanged.
- The dedicated lineage, every neuron, contact, formation, mosaic, receptor,
  learned route, body position and sensory state remain unchanged.
- No phoneme, word, timing script, lookup table, smoothing, renderer authority,
  observer authority, lock, retry, or new persistent state is introduced.
- Swallowing remains disjoint from breath. Only same-interval learned L11 ->
  typed vocal-L12 discharge may recruit layer 13.
- Existing reservoir conservation and thermal capacity remain authoritative.
  A discharge may still fail when the normal bounded metabolic settlement
  cannot create enough physical headroom.
- Work is constant-space and restricted to the already unique single-neuron
  layer-13 cohort on an actual learned vocal occurrence. No idle scan or loop
  is added.
- Existing codec and current-only restart semantics remain unchanged.
- Observation must expose metabolic predecessor/successor, heat exported,
  requested respiratory carriers, released work and any thermal refusal so
  this failure cannot disappear silently again.

The first copied-body acceptance gate is recovery of the exact tick-434112
body without resetting its 128.756-zJ thermal state: the same two learned vocal
motor discharges must receive ordinary bounded metabolic service, recruit the
same layer-13 lineage, emit bounded pressure, return that exact pressure through
both ears, cool/rest lawfully, and repeat after cold restore. A fresh/genesis
body, capacity increase, reservoir edit, one-carrier reduction, or synthetic
pressure does not satisfy the gate.

After that reuse gate passes, speech remains open at the next already-measured
boundary: the two current vocal postures occur simultaneously, not as an
ordered multi-posture syllable or word. No word or sentence claim is made by
this repair.

## Implemented candidate and exact copied-production proof

The candidate changes only `settle_internal_contact_interval`. When an exact
learned layer-11 -> typed vocal layer-12 occurrence co-recruits the dedicated
layer-13 cell, that one cell first receives the existing reached-cohort
membrane-pump/environment settlement. The unchanged efferent discharge and
passive-return deposit then run. The candidate neither resets nor enlarges the
reservoir and does not create a new speech path.

The focused resident-cognition native suite passed 98 tests with zero failures
(four unrelated explicit diagnostics remained ignored). The exact candidate
wheel is
`/tmp/guala-speech45-wheel/guala_core-0.1.0-cp311-cp311-manylinux_2_35_x86_64.whl`,
SHA-256
`13beb084be9a937f49c860547a5abe76ee0b0b480ff441ddf3ffccb8b597c902`.

The unchanged tick-434112 copied production body then passed 512 ordinary
250-ms whole-roster hops through the real production caller:

- 256 exact recruitments of the same dedicated layer-13 lineage;
- 469 bounded pressure occurrences and 468 later self-heard occurrences;
- 43 exactly silent successor hops and peak raw pressure 418;
- 11 distinct pressure hashes, repeating without persistent growth;
- resident state exactly 112,677,154 bytes on every hop;
- successor tick 434624, exact cold restore, and bounded in-flight pressure;
- all five Guala CloudWatch alarms `OK`, with exactly one healthy task 1429;
- RSS startup/warm-up reached approximately 1.11 GB in the first 64-hop block;
  the final four 64-hop block deltas were only 2.13, 1.97, 3.28 and 2.62 MB
  while the diagnostic retained its growing report and WAV in-process.

The report is
`/tmp/guala-speech1429-sequence.dpHRJX/attempt45-whole-path-512.json`,
SHA-256
`621a311705fa74403ddfcd1ba747fdddcb8942cbebd7b98b44904709e11eb9b3`.
Its exact raw pressure WAV is
`/tmp/guala-speech1429-sequence.dpHRJX/attempt45-whole-path-512.wav`,
SHA-256
`2cae2ad55f7d4ff5ad8170a3a9124ad996db6bc3510796b716ad28bbb7092f61`.
No diagnostic process survived the run.

This accepts the repair as a bounded mature-body reuse candidate. It rejects
any word claim: the selected glottal, jaw, lip and tract coordinates were
identical across all 512 hops. The current two learned tract motors occur
together, and neither a second posture nor an ordered posture transition was
observed. Further breath, valve, pressure or renderer tuning cannot repair
that measured boundary.
