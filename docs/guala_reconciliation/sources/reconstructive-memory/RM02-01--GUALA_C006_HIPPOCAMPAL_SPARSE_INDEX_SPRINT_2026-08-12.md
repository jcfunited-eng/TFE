# C-006 Hippocampal Sparse-Index Sprint

Date: 2026-08-12

## Frozen item and production baseline

- Active delivery-ledger item: **C-006** — prove hippocampal structures act as
  bounded sparse indexes into distributed retained structure and do not store
  or return an answer.
- Immediate predecessor: **C-005**, closed live on task 991. This sprint does
  not reopen C-005.
- Reviewed baseline commit: `4c68b151219a117bd4492cbe952889d67934bfe8`.
- Production baseline: task definition `dsf-ai-task:991`, image
  `sha256:786c937d0cb5479148e22090de05715324fa2f3d2eaa366ac16cd677451b2068`,
  identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`, one desired/running
  healthy process, zero pending tasks, 4096 CPU units, and 16,384 MiB.
- Read-only task-991 body at tick 53,727: 43,384,300 bytes, SHA-256
  `df064e948e1e02078d56b034608e91a1c3780f74f2805ae003a623bd119ae71a`.
  It contains 224 reached neurons, four layer-9 neurons, two retained mosaics,
  and zero Python cognition callbacks.

## Architecture honesty gate

1. **Requested architecture:** hippocampal neurons provide bounded sparse
   physical routes into distributed retained formations. The distributed
   whole-neuron states and bonds remain memory; no hippocampal record stores
   or returns an answer.
2. **Current code reality:** each newly admitted mosaic already mounts one
   intrinsic layer-9 neuron with sparse electrical contacts to that mosaic's
   real members. Contact settlement advances only one physical boundary per
   interval, but its seed law incorrectly treats every nonzero separated
   membrane charge as a fresh signal. On the authenticated task-991 body this
   makes almost the entire reached brain active on every interval. The
   separately persisted `GLHST01` hippocampal checkpoint is an inert 74-byte
   compatibility body; its former archive and navigator are retired.
3. **Conflict:** yes. The physical index topology exists in production, but no
   exact live observation yet proves a cue reaches layer 9 and a later causal
   interval reaches distributed retained members through that same route.
4. **Not extended:** `ResidentHippocampalIndex`, the retired cold archive,
   `hippocampal_reference_page`, `navigate_hippocampal`, delivery addresses,
   content-addressed answer retrieval, Python recall modules, hierarchy or
   parent objects, counters, databases, owners, locks, semantic labels,
   full-population scans, or reduced DSF.
5. **Single exact item:** make the existing route physically sparse by seeding
   the current admitted cause and carrying only a newly reached intrinsic
   layer-9 lineage for one later interval; then expose and live-prove cue ->
   layer-9 -> distributed-member traversal without creating a persistent route
   history or answer object.
6. **DSF scope:** C-006 neither evaluates nor reduces DSF. Existing reached
   neurons continue receiving unchanged full joint seven-field DSF.
7. **Field loss:** none. No DSF field is copied, averaged, compressed, scored,
   or replaced.

## Exact input, function path, state transformations, and output

Input: one ordinary admitted whole-organism occurrence over the authenticated
task-991 predecessor, including exact external cue lineages, predecessor
membrane/carrier state, retained formation members, and sparse contact state.

Path:

1. `resident_cognitive_formation.rs::prepare_typed_admitted_transition_from_owned`
   admits the occurrence and identifies its real reached receptor lineages.
2. `settle_internal_contact_interval` derives its current seed frontier from
   the admitted cause. Absolute nonzero membrane charge and retained contact
   phase are not fresh activity: a living neuron may hold both at rest.
3. `one_interval_electrical_frontier` advances that frontier across exactly
   one contact boundary; it never computes graph closure.
4. Existing sparse contact settlement transfers finite carriers and changes
   membrane state. Only a newly reached intrinsic layer-9 cell can carry that
   exact route into one later interval, where its existing sparse contacts can
   reach the distributed members. An arbitrary changed endpoint is never
   promoted into a transitive graph walk.
5. `mount_new_recurrent_retention` remains admission-only: one layer-9 cell is
   mounted once for a newly retained mosaic and connected only to its actual
   members. Recurrence must not mount another cell.
6. A transient observation will report only exact formation receipt, layer-9
   lineage, cue/member lineages, active stable bonds, and causal interval. It
   observes settled physics and cannot drive cognition or persist an answer.

Expected output: a live multi-interval occurrence contains an exact inbound
member-to-layer-9 transfer and a later exact layer-9-to-other-member transfer
for the same retained formation. The organism body holds only its normal
neuron/contact successor. No route history, answer, semantic key, page, or
archive record is added.

## Acceptance-evidence map

| Required fact | Exact producer | Retained authority | Live proof |
|---|---|---|---|
| Layer-9 route belongs to one formation | admitted mosaic members plus mounted sparse contacts | existing neuron/contact anatomy | receipt, layer-9 lineage, and exact member bonds agree |
| Cue reaches layer 9 | nonzero settled transfer on a cue-member/layer-9 contact | successor neuron/contact state | exact inbound occurrence at tick N |
| Route reaches a distributed member later | retained layer-9 physical state seeds a later one-hop interval | later successor neuron/contact state | exact outbound occurrence at tick N+k to a non-cue member |
| No stored answer | source, codec, and API audit | distributed formation only | no new persistent field; navigator still refuses |
| Bounded growth | one layer-9 cell only at new mosaic admission | sparse reached frontier | recurrence changes no layer-9 count and no unexplained bytes |
| Continuity | current-only publication and cold restore | byte-exact organism envelope | one process, same identity, zero Python callbacks |

## Lifecycle matrix

| Branch | Required result |
|---|---|
| No retained mosaic | no route observation and no layer-9 growth |
| New mosaic admitted | exactly one new layer-9 route connected to its actual members |
| Existing mosaic recurs | reuse existing layer-9 route; no new layer-9 cell |
| Cue-member contact moves no carrier or phase | no claimed route traversal |
| Cue reaches layer 9 but no later member transition occurs | inbound evidence only; C-006 remains unproved |
| Later layer-9/member transfer occurs | exact outbound evidence linked to the same formation and layer-9 lineage |
| Cold restore | exact topology/state restored; next ordinary transition behaves identically |

## Translation-boundary review

- Upstream authority is exact lineage, layer, contact endpoint, signed physical
  transfer, retained formation receipt, and causal tick. Counts and Booleans
  cannot replace these fields.
- Every `CognitiveFormationObservation` constructor, PyO3 projection, Python
  wrapper, per-hop carrier, admitted-experience accumulator, public schema, and
  test mock must be enumerated before compilation under RF-017.
- Earlier-hop inbound evidence must survive a quiet final hop under RF-018.
- Observation remains read-only and transient. Authentication, transport, and
  HTTP do not participate in the physical transition.

## Durable preflight recurrence register

| ID | C-006 application |
|---|---|
| RF-001 | Load the exact candidate worktree/module and print provenance. |
| RF-002 | Export the exact task-991 feature environment before import. |
| RF-003 | Rebuild and load the exact candidate native wheel. |
| RF-004 | Run first-use controls and the authenticated live predecessor. |
| RF-005 | Prove native-to-public route evidence before broad tests. |
| RF-006 | Check envelope, fabric, and logical resource ordering. |
| RF-007 | Resolve controller/interpreter/tools before starting deployment time. |
| RF-008 | Save each disposable committed interval; restart at first refusal. |
| RF-009 | Reject aggregate counts as route authority. |
| RF-010 | Compare committed body with `CURRENT`, cold restart, and advance once. |
| RF-011 | Return bounded references, never complete neuron bodies. |
| RF-012 | Direct live route evidence is mandatory; health cannot close C-006. |
| RF-013 | Check the sprint diff before inherited global formatting drift. |
| RF-014 | Update every mock carrying the changed observation schema. |
| RF-015 | Build the release wheel through the prescribed no-venv path. |
| RF-016 | Freeze C-006, task 991, identity, body, and complete candidate diff. |
| RF-017 | Enumerate every native/PyO3/Python/API constructor and consumer first. |
| RF-018 | Preserve exact earlier-hop route evidence across the whole occurrence. |
| RF-019 | Rehearse the exact C-006 sparse-index acceptance branch before the immutable build; do not require motor discharge formerly supplied only by rejected resting-charge flooding. |

## Failed hypotheses retained against rediscovery

- The retired hippocampal archive is not the index and must not be revived.
- A receipt or content address is correlation evidence, not memory or recall.
- Four live layer-9 cells do not by themselves prove four answers or four
  memories; their exact contacts and admission lineage must be reconciled.
- Static topology proves a route exists, not that a live cue traversed it.
- One-hop frontier selection must not be replaced by transitive graph closure.
- Falsified on the exact task-991 body: treating every nonzero separated
  membrane charge as a seed selected 221--223 of 224 reached neurons and 759--
  760 active bonds per ordinary vestibular interval, including all 97
  layer-9/member contacts. That is whole-reached-brain activation, not a
  bounded hippocampal route, and cannot be accepted as C-006 evidence.
- Falsified on the same exact task-991 body: retaining every changed lineage
  and every endpoint of an active bond merely delayed that global activation.
  It expanded 17 -> 81 -> 184 -> 222 transitioned neurons in four ordinary
  vestibular ticks.  The persisted causal frontier must contain only newly
  reached intrinsic layer-9 recipients whose neuron or incident contact
  changed in the current interval; arbitrary non-index recipients cannot be
  promoted into a transitive graph walk, and the predecessor seed itself is
  not a perpetual source.

## Production acceptance

C-006 closes only when one immutable reviewed release is live and directly
shows cue -> layer-9 -> distributed-member physical traversal for one retained
formation across causal intervals; recurrence creates no additional layer-9
cell; the retired navigator still refuses; cold restore is exact; one bounded
process remains healthy; state growth is absent or physically explained; and
Python cognition callbacks remain zero. Local tests or topology inspection
alone cannot close C-006.

## Current local evidence

- Frozen release native module:
  `/tmp/c006-release-site.QjfpyZ/guala_core/__init__.py`.
- The authenticated task-991 body at tick 53,727 cold-restored unchanged. One
  vestibular cue interval moved 17 neurons over 25 active bonds and carried one
  exact member-to-layer-9 bond. The next interval moved 43 neurons over 76
  bonds and the same layer-9 lineage reached all 27 exact members of retained
  formation receipt `10f72d227550a26955e7a257bc17c410f5d959a7f4c67cb8130734c7031be91b`.
- The route lineage was
  `474c4e4c494e4531000000000000008a`; its inbound member was
  `474c4e4c494e4531000000000000005c`. The later set of layer-9 bond endpoints
  equalled the formation's complete 27-member set exactly.
- Twelve alternating intervals remained bounded at 17/43 transitioned neurons
  and 25/76 active bonds rather than expanding to 222 neurons and 760 bonds.
- Layer-9 count remained four; two committed intervals reduced the encoded
  body from 43,384,300 to 43,384,272 bytes; the V19 successor cold-restored
  byte-exact; the retired navigator refused; Python callbacks remained zero.
- Focused Python boundary tests pass 25/25. The native suite exposed and
  removed three obsolete expectations: V18 fixed-length bytes, promotion of
  nonzero resting charge as new receptor activity, and manufacture of motor or
  articulatory cells from that false activity. The final native suite passes
  407/407 with 13 intentionally ignored and zero failed. The frozen release-
  wheel rehearsal repeated all 12 bounded intervals and exact cold restore.
- Deployment attempt 1 built immutable image
  `sha256:0d478168d958bf098940a6460fbfbf15d68f981da2d0349f09ebadfb290566c2`
  and candidate task definition `dsf-ai-task:992`, then failed safely in the
  discarded-state cold-restore rehearsal before cutover. Production remained
  unchanged on task 991. The stale rehearsal required a motor discharge that
  had previously been manufactured by the rejected whole-brain resting-charge
  flood; it did not test C-006's sparse-index acceptance path.
- RF-019 now requires the exact sprint rehearsal before immutable build. The
  corrected candidate rehearsal on the authenticated task-991 body observes
  one inbound member-to-layer-9 bond, the same layer-9 lineage reaching the
  formation's exact 27 members on the next interval, unchanged layer-9 count,
  a 28-byte reduction, distinct successor SHA-256, exact successor cold
  restore, and zero Python callbacks. It does not claim motor action.
- Deployment attempt 2 ran from 13:47:01 through 14:05:33 UTC (18 minutes 32
  seconds) and completed one verified cutover to task definition 993, commit
  `b803f1a000d262b9ab4789e90e0e1582410ea803`, and image
  `sha256:666c19d27b3948e0b5a561b88dc754ff8c296ebb8ee9b0eb0798c832ebca37b4`.
  ECS reached steady state with one running process and zero pending tasks.
- Direct authenticated readiness after cutover showed the same organism
  identity, production tick 54,695, 224 reached neurons, four layer-9 neurons,
  two retained formations, available energy, and zero Python callbacks.
- A post-cutover disposable production proof then loaded task 993's current
  read-only body at tick 54,711 and observed one exact inbound layer-9 bond
  moving 17 neurons, followed by the same index lineage reaching all 27 exact
  formation members while 43 neurons moved. Layer-9 count stayed four; the
  successor was 36 bytes smaller, had distinct SHA-256
  `bfac3bcf68b6ab42930ef7783ddba481aa682d02b239d188bcfb033e9a8aed69`,
  and cold-restored exactly. The proof receipt is
  `ac72216f3b8a37a4b617e009c2ec9506a3b02ce5d22314eb6ebe5ff08142ac0e`.
  The source mount was read-only and the disposable successor was not
  published into the primary organism.
