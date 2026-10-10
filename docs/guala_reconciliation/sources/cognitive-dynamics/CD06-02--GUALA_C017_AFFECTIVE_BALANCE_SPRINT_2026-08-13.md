# C-017 Body/Fluid/Association Affective-Balance Sprint

Date: 2026-08-13

## Frozen item and production baseline

- Active delivery-ledger item: **C-017** — prove body/fluid/association
  trajectories influence affect and emotional balance without named emotion
  variables.
- **C-016 is Live-Closed and is not reopened.** Its public-production baseline
  is task `dsf-ai-task:1015`, commit
  `5cd50950aebf45ee90903a163bee02e24640da1f`, image
  `sha256:b19e2679d7b2ffa3e0886b1dbd12d7ca45b949b65cb283da8e3534682daff477`,
  organism identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`, and tested-event
  state receipt
  `085a9a7af40fe84602b56f053fcf9d6907472c2d5b3d3138cdd9c74ec4242e74`.
- The public observer currently exposes three reached layer-10 cells and exact
  live layer-7/layer-10 and layer-8/layer-10 carrier transfers, but it does not
  expose the layer-10 cell's local recovery-fluid settlement or prove a
  perturbation-to-recovery trajectory. C-017 therefore remains open.

## Architecture honesty gate

1. **Requested architecture:** exact association, body, and localized fluid
   trajectories must jointly alter one physical affective-reach cell and show
   its bounded recovery/adaptation, without a named emotion, valence, reward,
   need score, or scripted response.
2. **Current code reality:** layer 7 is mounted association geography, layer 8
   is mounted local body-regulation geography, and layer 10 is the sparse
   physical junction grown from their coincident prior change. The one-neuron
   layer-10 cohort already runs the ordinary local membrane-gradient pump when
   reached, but its exact pump consequence is discarded at the internal
   contact boundary.
3. **Conflict:** yes. The physical path is runtime-reachable, but the decisive
   local fluid/recovery consequence is not carried to observation, so live
   influence and balance cannot yet be proved.
4. **Not extended:** named emotion fields, affect/valence scores, reward or
   need tables, Python choice logic, aggregate body bookkeeping, semantic
   labels, database/owner/lock state, whole-brain polling, reduced DSF, or a
   second emotion subsystem.
5. **Single exact item:** retain one bounded transient observation of an
   existing layer-10 cell's exact local pump and sparse layer-7/layer-8 contact
   consequences, then expose that same trajectory read-only in public
   production.
6. **DSF scope:** every reached neuron continues to receive the unchanged full
   joint L0-L4 result with explicit `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`,
   `P_k`, and `B_k`.
7. **Field loss:** none. The new evidence references downstream physical state
   only and neither copies nor reduces DSF.

## Durable change-impact ledger

| Boundary | Exact value |
|---|---|
| Input | One ordinary authenticated native trajectory in which current sparse propagation reaches a pre-existing layer-10 cell through its mounted layer-7 association contact and layer-8 body-regulation contact. |
| Physical producer | `settle_internal_contact_interval` in `native/guala_core/src/resident_cognitive_formation.rs`, using the existing one-neuron intrinsic cohort, `settle_reached_cohort_membrane_pumps`, and `settle_sparse_electrical_transfers`. |
| Existing state transformations | Exact local fluid/environment exchange powers the existing membrane-gradient pump; exact whole carriers move across the layer-7/layer-10 and layer-8/layer-10 contacts; the same complete neuron settles the unchanged shared field and retains only its ordinary current physical state. |
| Missing boundary | The internal-contact code currently discards the per-cohort membrane-pump observation and carries only aggregate body-receptor perturbation plus contact routes. It therefore cannot prove that localized fluid recovery acted on the same layer-10 cell reached by body and association trajectories. |
| Expected output | One bounded transient trajectory names the exact layer-10 lineage/place, exact association and body contact transfers, predecessor/pumped/successor membrane charge, and exact local recovery exchange. It reports physical influence and recovery/adaptation only; it assigns no emotion or preference. |
| Invariants | No new neuron, contact, persistent field, codec, schema magic, owner, lock, history, score, or semantic state. Existing current organism bytes remain the only cognitive authority. Work is linear in the already-selected sparse frontier. |
| Public acceptance | The public production observer shows one exact layer-10 trajectory with both physical association and body influence, nonzero localized recovery/pump consequence on that same cell, exact before/after physical quantities, `named_emotion_authority=false`, `score_authority=false`, and zero Python cognition callbacks. |
| Cold/resource acceptance | The same predecessor and trajectory reproduce the same observation byte-for-byte; current state cold-restores exactly; one process remains healthy; no persistent-byte growth is caused by observation; work/calls remain proportional to the reached frontier. |
| Evidence level | Source trace complete; live C-016 predecessor closed; C-017 implementation, candidate proof, rehearsal, and public production acceptance not yet complete. |

## Translation-boundary preflight

The required evidence path is:

`settle_reached_cohort_membrane_pumps`
`-> settle_internal_contact_interval`
`-> CognitiveFormationObservation`
`-> RuntimeObservation / trajectory aggregation`
`-> PyO3 projection`
`-> ResidentPrepareEvidence`
`-> native production transaction aggregation`
`-> read-only public observation`.

Before the first test, every constructor, getter, protocol, dataclass,
validator, mock, cold probe, rehearsal assertion, and public consumer on this
path must be enumerated. No downstream boundary may default, aggregate away,
rename without an explicit mapping, or reconstruct the local physical facts
from a weaker proxy.

### Exact bounded observation shape

For each reached layer-10 cell, the native interval may emit one transient
record containing only:

- the cell's stable lineage and declared layer/topology place;
- the earliest canonical nonzero layer-7 contact transfer in that interval;
- the earliest canonical nonzero layer-8 contact transfer in that interval;
- exact separated membrane charge immediately before and after the already
  mounted local membrane-gradient settlement;
- exact separated membrane charge after the same interval's contact/neuron
  settlement;
- exact passive returned carriers, active pumped carriers, remaining separated
  carriers, and actual membrane-gradient work;
- exact local powered-environment energy delivery and heat export; and
- the cognitive ordinal of each physical event.

The transaction observer may merge these facts only by identical neuron
lineage. It retains at most one association influence, one body influence, and
the first later nonzero gradient settlement for that same cell. Recovery is
not claimed unless its ordinal is strictly later than both retained contact
influences. This bounded merge is read-only evidence; it changes and persists
nothing in the organism.

### Constructor and consumer census before first compile

| Boundary | Exact constructors/consumers requiring an explicit field mapping |
|---|---|
| Local physical producer | `settle_reached_cohort_membrane_pumps` and `settle_internal_contact_interval` in `native/guala_core/src/reached_neuron_cohort.rs` and `native/guala_core/src/resident_cognitive_formation.rs`. |
| Cognitive observation | Both `CognitiveFormationObservation` constructors in `resident_cognitive_formation.rs`; the test-only constructor in `physical_cognitive_capital.rs`; the ordinary internal-contact early returns and final return. |
| Native trajectory aggregation | `NativeResidentOrganismRuntime::prepare_vestibular_trajectory` in `organism_runtime.rs`; it must bounded-merge later interval evidence rather than copy only interval one. |
| Runtime observation | `RuntimeObservation` plus `make_restored_observation`, `make_step_observation`, and `make_authored_contact_observation` in `organism_runtime.rs`. Restored/contact-growth observations carry no transient trajectory. |
| PyO3 | Both `NativeResidentOrganismObservation` and `NativeResidentOrganismPrepare` getters plus the exact projection helper in `organism_runtime.rs`. |
| Python boundary | `NativeResidentObservationView`, `ResidentPrepareEvidence`, `_observation_signature`, and `NativeResidentOrganism._prepare` validation/construction in `dsf_ai_service/glew_runtime/native_resident_organism.py`. |
| Production transaction | `_commit_admitted_hop`, `_commit_vestibular_tick`, `_commit_vestibular_trajectory`, `_perform_admitted_intake_locked`, and its bounded cross-hop merge in `dsf_ai_service/native_production_app.py`. |
| Public observer | One read-only `affective_balance` section in the public observation record and `/api/v1/guala/native-observation`. No UI change is part of C-017. |
| Replay/test consumers | `dsf_ai_service/cold_restore_probe.py`, native observation mocks in `tests/test_native_resident_organism_boundary.py`, and public-observation mocks/tests. Exact field presence is required where the real interface is impersonated. |

### Acceptance-evidence field map

| Required fact | Producer | Native observation | FFI/Python | Public surface |
|---|---|---|---|---|
| Same layer-10 cell | mounted lineage plus `DeclaredNeuronPlace` | bounded trajectory lineage/place | canonical 32-hex lineage plus integer layer/topology | `affective_balance.trajectory.neuron_*` |
| Association influence | exact nonzero layer-7/layer-10 settled contact transfer | timed directed transfer | exact sender/receiver/bond/carrier integer | `association_influence` |
| Body influence | exact nonzero layer-8/layer-10 settled contact transfer | timed directed transfer | exact sender/receiver/bond/carrier integer | `body_influence` |
| Local recovery | one-neuron layer-10 cohort's existing gradient settlement | timed exact charge/work/environment record | exact signed integers and rational numerator/denominator pairs | `localized_gradient_settlement` |
| Causal order | `source_generation` | event ordinals | exact native integers | recovery ordinal must exceed both influence ordinals |
| No semantic authority | absence from physics plus observer constants | no named-emotion/score fields | no Python decision callback | explicit false authority flags |

### Applicable recurrence preflight

| ID | Applicability and earliest check |
|---|---|
| RF-001 | Required: exact worktree first on `PYTHONPATH`; print loaded Python module paths. |
| RF-002 | Required: resolve live task-definition environment before candidate imports. |
| RF-003 | Required: rebuild candidate native wheel and print loaded binary provenance. |
| RF-004 | Required: run the same C-017 path from pristine and authenticated restored bodies. |
| RF-005 | Required: field map above must reach the public record without defaults or aggregate substitution. |
| RF-007 | Required: resolve controller and interpreter shape before deployment timing starts. |
| RF-010 | Required: compare in-process successor to persisted `CURRENT`, cold start it, and advance once. |
| RF-011 | Required: expose one bounded trajectory, never raw neuron/frontier bodies. |
| RF-012 | Required: public exact C-017 behavior, not health/HTTP 200, is the closure test. |
| RF-013 | Required: format only touched files and inspect changed-file set immediately. |
| RF-014 | Required: enumerate and update native-interface mocks before broad tests. |
| RF-015 | Required: use the no-virtualenv wheel build/install path when applicable. |
| RF-016 | Required: C-017/ledger/diff/task-1015 baseline must agree before packaging. |
| RF-017 | Required: the constructor/consumer census above must be complete before compilation. |
| RF-018 | Required: ordinary multi-hop intake must preserve evidence emitted before its final hop. |
| RF-019 | Required: rehearsal assertions must map to C-017, not demand a prior transient witness. |
| RF-020 | Required: live layer-7, layer-8, and layer-10 physical participation, not mounted counts, must be shown. |
| RF-021 | Required: acceptance inspects the exact successor caused by the declared input. |
| RF-024 | Required: resolve every intended test path/name immediately before invocation. |
| RF-027 | Required: bind the first complete trajectory and replay its immediate predecessor/input. |
| RF-028 | Required: ordinary multi-interval and multi-hop aggregation must retain later decisive evidence. |
| RF-030 | Required: signatures, equality projections, and controller shapes include the new field. |
| RF-031 | Required: every filtered test must report a nonzero executed-test count. |
| RF-032 | Required: record tool working directory and resolve every path before invocation. |
| RF-033 | Required: re-enumerate AWS account/region/cluster/service/task before release. |
| RF-034 | Required: C-016's transient witness is reported but is not a C-017 rehearsal requirement. |
| RF-035 | Required: live acceptance input must be ordinary live-sized organism/environment input. |

## Lifecycle matrix

| Branch | Required result |
|---|---|
| Existing layer-10 cell reached by body and association contacts | Observe exact local trajectory; do not grow another cell or contact. |
| Existing layer-10 cell reached by only one side | Do not call it a C-017 affective-balance trajectory. |
| Local pump has no physical exchange | Preserve the contact facts but leave C-017 recovery evidence unavailable. |
| Repeated equivalent trajectory | Reuse the same cell and contacts; bounded observation may be replaced, but organism state gains no observation history. |
| Cold-restored current body | Same input reproduces the exact observation and successor. |

## Failed-hypothesis register

1. **Rejected:** layer-10 existence proves emotional balance. It proves only
   mounted developmental geography.
2. **Rejected:** global body-energy totals prove local affective recovery. They
   merge separately retained cohorts and cannot identify the affected cell.
3. **Rejected:** a named emotion, valence sign, reward value, or observer label
   can stand in for the physical trajectory.
4. **Rejected:** any layer-10 electrical transfer alone proves fluid influence.
   The exact localized pump/recovery consequence must be carried from its real
   producer.
5. **Rejected:** powered-environment energy delivery is identical to actual
   membrane-gradient recovery work. The environment may deliver capacity that
   the pump does not consume; the actual `pump_work` returned by the existing
   local transport law must cross the observation boundary separately.
6. **Command-path failure, no state change:** two initial root-validation
   attempts invoked `scripts/require-guala-root.sh` from repositories where the
   relative path did not exist. `rg --files` located the authoritative script
   at `/root/.codex/skills/guala-project-truth/scripts/require-guala-root.sh`,
   which then validated this exact worktree and HEAD. This is RF-032 evidence;
   no compile, test, code, or production mutation occurred.
7. **Command-path failure, no test executed:** bare `pytest` did not include
   this exact worktree on Python's import path, so collection refused before
   any test ran. The identical focused suite was rerun with `PYTHONPATH=.` and
   executed 41 tests successfully. This is RF-001/RF-031 evidence and caused
   no organism, persistence, or production change.

## Live completion boundary

C-017 becomes **Live-Closed** only after the immutable release is deployed and
the public production endpoint directly exposes the complete exact trajectory
above on the continuing organism, with exact cold replay, bounded resources,
one healthy process, and zero Python cognition callbacks. Local tests,
candidate tasks, deployment success, or HTTP 200 do not close it.

## Current evidence (not live closure)

- Rust source compiles against the current native crate.
- The native library suite executed 427 tests: 424 passed and 3 explicitly
  retired tests were ignored.
- The exact boundary, bounded-merge, public-projection, replay-probe, and
  controller-facing Python suites executed 68 tests successfully.
- A release-mode CPython 3.11 wheel was built, installed into an isolated
  target, and loaded from that exact target; its prepare interface exposes the
  new trajectory field.
- No persistent schema, neuron state, DSF field, organism identity, contact,
  or developmental population was added or changed by this observation path.
- C-017 is **not Live-Closed**. Immutable image rehearsal, production cutover,
  and direct public-production behavior remain pending.
