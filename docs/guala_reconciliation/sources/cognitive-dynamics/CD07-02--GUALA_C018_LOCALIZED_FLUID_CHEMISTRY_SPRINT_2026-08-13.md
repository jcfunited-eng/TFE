# C-018 Localized Fluid-Chemistry Sprint

Date: 2026-08-13

## Frozen item and production baseline

- Active delivery-ledger item: **C-018** — prove fluid-brain transport and
  localized chemistry influence only physically connected neurons and remain
  conserved and bounded.
- **C-017 is Live-Closed and is not reopened.** Its public-production baseline
  is task `dsf-ai-task:1016`, commit
  `7add36a227d1aec46dd58912312501d7bcd04549`, image
  `sha256:f4891ce2b0c977f4216c087ce82169620ecee823f679b7d54d7be4d4f722a855`,
  and organism identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`.
- This sprint continues from C-017. It does not reopen any closed item and does
  not advance to C-019.

## Architecture honesty gate

1. **Requested architecture:** one bounded sparse fluid mechanism moves finite
   energy/material only through mounted local neuron contacts; only neurons in
   the physically reached frontier may change; source, destination, carrier,
   and energy changes remain exactly conserved.
2. **Current code reality:** the native organism already retains one exact
   recovery-fluid reservoir per reached cohort, a recovery-fluid contact for
   every neuron recovery lane, finite intracellular/extracellular carrier
   partitions, exact membrane-gradient work, and exact pump settlement only
   over supplied reached-neuron indices. The active observation collapses
   distinct local settlements into one cohort total and therefore cannot prove
   which mounted target changed or that unreached members remained outside
   the mutable sparse write boundary.
3. **Conflict:** yes at the evidence boundary. The local transition exists,
   but its current aggregate projection is insufficient to Live-Close C-018.
4. **Not extended:** the excluded Python neurochemical modules; unratified
   named species or coefficients; scalar mood, reward, need, readiness, or
   salience; global broadcast; semantic chemistry; owners; locks; databases;
   Python cognition; dense population scans; or reduced DSF.
5. **Single exact item:** preserve one exact bounded per-neuron fluid/contact
   settlement witness through the existing native-to-public observation path,
   and prove active cells outside the reached frontier plus the unreached
   developmental population remain outside the mutable pump boundary.
6. **DSF scope:** every reached neuron continues to receive unchanged full
   joint L0-L4 with explicit `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`,
   `P_k`, and `B_k`.
7. **Field loss:** none. C-018 observes downstream material state and does not
   copy, score, flatten, or replace DSF.

## Durable change-impact ledger

| Boundary | Exact value |
|---|---|
| Input | One ordinary native interval whose already-derived sparse physical frontier supplies a strictly increasing list of reached neuron indices; the same organism state carries active cells outside that frontier and its unreached developmental population. |
| Producer | `complete_neuron.rs::pump_contact_power_zeptojoules_per_microsecond`; `metabolic_feeding.rs::settle_membrane_gradient_transport`; `recovery_fluid_contact.rs::settle_powered_environment_exchange`; `reached_neuron_cohort.rs::settle_reached_cohort_membrane_pumps`. |
| Existing physical state | Stable neuron lineage/place; finite intracellular/extracellular carriers; exact membrane charge and phase; one finite cohort recovery reservoir with available, spent, and thermal energy; exact elapsed interval; anatomy-derived pump-contact power. |
| State transformation | Environment exchange moves only existing spent energy back to available capacity and removes only existing heat. Each reached neuron then moves whole carriers locally; active uphill work debits available and credits spent by the same exact rational amount, while passive downhill work credits thermal by the exact released amount. The transition writes only explicitly reached indices, so active cells outside the frontier and the shared quiescent developmental population remain outside the mutable pump boundary without a second whole-organism scan. |
| Missing boundary | `ReachedCohortMetabolicObservation` retains only sums. It loses target identity, per-target predecessor/successor reservoir state, per-target carrier partition, and the direct sparse-write-boundary evidence that unreached members were not mutable targets. |
| Expected output | A bounded transient record names one reached neuron lineage/place and its exact local pre/post carrier, charge, reservoir, work, interval, and contact-power facts. It separately reports reached, changed, active cells outside the sparse write boundary, developmental resting cells outside that boundary, and changed-unreached count. |
| Invariants | No new persistent state or codec; no neuron/contact growth; no chemistry labels; no ordering score; no observer data enters cognition; total carrier material is unchanged; each pump-work reservoir delta balances exactly; work remains linear in the already-reached frontier. |
| Public acceptance | Public production exposes one ordinary `localized_fluid_chemistry` witness with a mounted neuron target, nonzero local transfer, exact conservation, `changed_unreached_neuron_count=0`, bounded record count, advancing organism time, continuing identity, and zero Python cognition callbacks. |
| Live-Closed meaning | Only direct observation of that exact behavior at `https://dsf-ai.com/api/v1/guala/native-observation` closes C-018. Local tests, a candidate image, ECS health, or HTTP 200 do not. |

## Translation-boundary and acceptance-evidence map

| Required fact | Physical producer | Native observation | FFI/Python | Public surface |
|---|---|---|---|---|
| Exact target | reached index plus stable cohort lineage/place | per-neuron local settlement | canonical lineage and integer place | `localized_fluid_chemistry.target` |
| Mounted local capacity | neuron anatomy and exact interval | pump-contact power and interval | exact rational plus integer time | `contact` |
| Carrier conservation | neuron carrier partition before/after | both exact compartment pairs and signed moved carriers | integers | `carrier_material` |
| Energy conservation | reservoir before/after plus pump work | exact available/spent/thermal rational triples and work | numerator/denominator pairs | `reservoir_energy` |
| Locality | reached indices, active predecessor/successor cells outside the frontier, and immutable developmental-resting authority | reached count, changed target count, unchanged active/developmental counts, changed-unreached count | integers | `contact` plus `locality_conserved` |
| Boundedness | one record per changed member in the reached frontier, bounded merge for public evidence | native vector length and work counts | bounded tuple | one retained tested-event witness |
| No semantic authority | absence from physics | no label/reward/decision field | no Python cognition callback | explicit false authority flags |

The complete boundary path is:

`settle_reached_cohort_membrane_pumps`
`-> settle_internal_contact_interval`
`-> CognitiveFormationObservation`
`-> RuntimeObservation and bounded trajectory aggregation`
`-> PyO3 projection`
`-> ResidentPrepareEvidence`
`-> native production transaction aggregation`
`-> read-only public observation`.

Before compilation, every constructor, getter, equality/signature projection,
mock, cold-replay probe, controller assertion, and public consumer on this path
must carry the exact fields rather than defaulting or rebuilding them from a
cohort aggregate.

## Lifecycle matrix

| Branch | Required result |
|---|---|
| One reached member with other active cells outside its frontier | Only explicitly reached indices enter the mutable pump path; active cells outside the frontier remain outside that write boundary. |
| Active frontier temporarily includes every materialized cell | The exact unreached developmental-resting population remains unchanged and is reported separately; it is not materialized or scanned per cell. |
| Several reached members | Each changed target has its own exact record; totals equal the exact sum without losing local facts. |
| Reached member with no deliverable transfer | No false changed-target witness. |
| Repeated interval | New bounded transient evidence may replace prior observation; no observation history enters organism state. |
| Cold-restored predecessor | The same input produces byte-identical successor state and observation. |

## Applicable recurrence preflight

| ID | Earliest deterministic check for C-018 |
|---|---|
| RF-001 | Bind `PYTHONPATH` to this exact worktree and print loaded module paths. |
| RF-002 | Resolve task-1016 environment before process-fixed imports or predecessor probes. |
| RF-003 | Rebuild the native extension and print loaded candidate binary provenance. |
| RF-004 | Run pristine and authenticated restored-state branches. |
| RF-005 | Reconcile every field in the evidence map before packaging. |
| RF-007 | Resolve the controller file and interpreter command before the deployment clock. |
| RF-010 | Compare in-process successor with persisted `CURRENT`, cold-start it, then advance one ordinary interval. |
| RF-011 | Public evidence is one bounded witness, never raw cohort/neuron bodies. |
| RF-012 | Closure requires the exact public behavior, not health or HTTP success. |
| RF-013 | Format only touched files and inspect the changed-file set immediately. |
| RF-014 | Enumerate native-interface mocks before broad tests. |
| RF-015 | Use the repository's no-virtualenv wheel path where applicable. |
| RF-016 | C-018, this ledger, candidate diff, and task-1016 baseline must agree. |
| RF-017 | Complete the constructor/consumer census before compilation. |
| RF-018 | Ordinary multi-hop aggregation must not drop an earlier decisive witness. |
| RF-019 | Rehearsal assertions must test C-018 rather than a stale downstream effect. |
| RF-020 | Prove actual target participation, not mounted counts or specialization labels. |
| RF-021 | Acceptance observes the exact successor caused by the declared input. |
| RF-024 | Resolve each intended test name before invoking it. |
| RF-027 | Bind and replay the immediate predecessor/input for the first complete witness. |
| RF-028 | Multi-interval aggregation retains the decisive later witness without unbounded history. |
| RF-030 | Update signatures, equality projections, and controller shapes with the new field. |
| RF-031 | Every filtered test must execute a nonzero test count. |
| RF-032 | Record the exact worktree and resolve every path before invocation. |
| RF-033 | Re-enumerate AWS account, region, cluster, service, task, and image before release. |
| RF-035 | Live acceptance uses the ordinary live-sized organism/environment path. |

## Failed and rejected paths

1. **Rejected:** revive the old Python neurochemical system. It is excluded
   from the current release and would create a second cognitive authority.
2. **Rejected:** call cohort energy totals localized chemistry. They merge
   separately targeted transitions and cannot prove locality.
3. **Rejected:** introduce dopamine, serotonin, GABA, or any other named
   species and coefficients from the research-candidate document. Their exact
   production chemistry remains unratified.
4. **Rejected:** add another stored gradient scalar. The finite carrier
   partition plus authored reversal potential already constitutes the retained
   generic chemical-gradient material.
5. **Rejected:** use a one-neuron cohort alone as locality proof. The live
   witness must also carry either an active cell outside the sparse reached
   write boundary or the developmental-resting population outside that
   boundary, with the two counts reported separately.
6. **Missing authority document:** the neuron skill names
   `GUALA_PHASE1_ENERGY_BOUNDARY_DECISION_2026-08-10.md` and
   `GUALA_EXACT_BODY_ENERGY_SPRINT_LEDGER_2026-08-10.md`; neither exists in
   this validated worktree. Their contents will not be guessed or silently
   reconstructed.

## Current evidence level

C-018 is **Live-Closed**.

- The complete native library suite passed: 414 tests passed, zero failed, and
  13 explicitly retired tests were ignored.
- The focused native/Python observation boundary passed 53 tests.
- The first discarded candidate rehearsal correctly stopped before cutover
  because fixed-width subtraction could not represent the difference between
  two valid live reservoir rationals. No production state changed. The
  observation-only conservation check was corrected to use exact widened
  integer-rational equality; neuron state, physics, DSF, and persistence were
  unchanged.
- The corrected discarded rehearsal cold-restored live tick 71,150 and
  reproduced one localized fluid witness exactly, receipt
  `1bf8287f425cd6db63c6d3807746c651edeb929119357ad7df77c603a8a639f4`,
  with zero Python cognition callbacks.
- Public production task `dsf-ai-task:1018` runs commit
  `b9d85da31e48d54aff5389d0a49155aedeaa9572` and image
  `sha256:09116ddafe48cd71955e78d28b9afd8316c40645babea683557a44f90719ee15`.
- The public endpoint exposed `localized_contact_conserved`: one reached
  layer-0 neuron moved one carrier through its active gradient pump; carrier
  material and reservoir energy reconciled exactly; 27 neurons were reached,
  3 changed, 2 active neurons and 196,505 developmental-resting neurons stayed
  outside the sparse write boundary, and zero unreached neurons changed.
- Public production advanced from tick 71,240 to 71,249, preserved identity
  `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`, and reported zero Python cognition
  callbacks. ECS showed one completed PRIMARY deployment, desired/running
  1/1, pending 0, and no stopped service task after cutover.
