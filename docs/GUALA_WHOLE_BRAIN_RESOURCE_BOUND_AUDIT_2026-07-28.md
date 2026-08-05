# Guala whole-brain resource-bound audit — 2026-07-28

This is a source-and-test audit of the production candidate. It is not a live
deployment claim.

## Architecture honesty gate

- Requested architecture: repeated experience reinforces an always-wired,
  multimodal whole organism without creating a new neuron or edge merely
  because the same settlement occurred again.
- Current code reality: the newly mounted whole-organism owners have explicit
  record/topology and byte capacities. Neuron response histories roll.
  Reflection history previously copied every monitored owner snapshot into
  every retained reflection row.
- Conflict with requested architecture: the neuron population does not
  conflict; the reflection snapshot duplication did conflict with lean durable
  custody and has been removed in this candidate.
- Mechanisms not extended: the legacy teaching monolith, named sensory
  profiles, raw sound bodies, Chi/Atlas identity, scripted meaning, and reduced
  auditory compatibility identities.
- Single exact next item: deploy this candidate through the authenticated Guala
  deployment path, then verify the live storage-cutover authority and measure
  owner paths after repeated identical settlements.
- Field evaluation: full explicit `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`,
  `P_k`, and `B_k` custody remains authoritative. This audit introduces no
  reduced field approximation.

## Decisive results

`test_repeated_identical_settlement_has_constant_topology_and_storage` settles
the same six-sense experience eight times to fill the fixed response history,
then another 128 times. The result is exact:

- six neuron identities remain six;
- the complete six-neuron coupling topology remains 15 edges;
- every response history remains at its configured depth of four;
- the authenticated persisted bytes become and remain byte-identical; and
- no PCM, normalized signal, sample-array, or frame body is present in that
  persisted neuron state.

`test_large_owner_states_are_never_duplicated_into_reflection_history` gives
the reflection monitor seven owner snapshots of more than 1 MiB each and
settles 40 reflections. The retained history rolls at 16 records, remains
below 64 KiB in the test profile, and contains none of the owner bodies.
Reflection records now retain the exact SHA-256 and byte count for each
snapshot, not a hexadecimal copy of the snapshot.

The focused whole-brain resource suite passes: **39 tests passed**.

## Candidate hard capacities

The currently constructed whole-organism owners expose these byte refusal
limits:

| Owner | Hard encoded-state limit | Structural limit |
|---|---:|---|
| Whole-organism episode | 64 MiB | bounded episode records |
| Recovery | 4 MiB | current recovery state |
| Structural perturbation | 16 MiB | current structural state |
| Causal mosaic/tapestry | 64 MiB | 64 tapestries, 256 relations, 1,024 roots per tapestry |
| THING mosaic learning | 64 MiB | 256 records, 1,024 roots per record |
| Dream/wake/weave | 16 MiB | 64 dreams, 64 wake tests, 64 weaves, 16 transitions per dream |
| Neuron population | 64 MiB | 256 neurons, 32,640 edges, 1,024 tuples per neuron, 16 responses per neuron |
| Neurochemical placeholder | 16 MiB | unavailable owner; no invented flow |
| Recognition/attention | 16 MiB | 256 paths, 1,024 roots, 64 action and 64 inquiry relations |
| Other perspective | 8 MiB | 32 other bodies, 256 objects per body |
| Sensed consequence | 32 MiB | 64 records |
| Glyph curriculum | 8 MiB | 64 lessons |

Those twelve owner limits sum to **372 MiB**. The separately constructed
passive whole-organism THING learner has a 128 MiB limit, making the examined
whole-organism and passive-learning subtotal **500 MiB**. These are refusal
ceilings, not allocation targets. The reflection monitor, when mounted, has a
separate 64 MiB default refusal ceiling but no longer multiplies the bodies it
observes.

The whole teaching-state refusal calculation in
`guala_physical_runtime_core.py`, including additional bounded teaching
owners outside this census, is **1,363,281,924 bytes**. With full-field
prediction it is **1,396,836,356 bytes**, below the configured 2 GiB cold
generation protocol limit.

Neuron status now exposes neuron, edge, tuple-per-neuron, response-history,
and byte capacities. Reflection status exposes history and byte capacities.
The other mounted owner statuses already expose their current encoded byte
count and byte capacity.

## Production storage path findings

Owner-scoped persistence includes each newly mounted whole-organism state in a
separate authenticated owner group. The cold generation store retains
authenticated CURRENT plus one predecessor, with a third candidate permitted
only during an atomic transaction. The production profile uses a 2 GiB
per-generation refusal and the approved global physical write refusal is
exactly 5 GiB.

The candidate production writer now publishes content-addressed cold and hot
state under the same shared physical-byte authority. It does not start in ECS
with the retired flat/full-copy persistence mode. Every cold checkpoint runs
version-aware reachability reconciliation and reports the exact generation
UUIDs retained and retired. Ring-object replacement removes all prior S3
versions and delete markers rather than waiting for lifecycle expiration.

The Guala deploy script now refuses task-owner turnover until the newly
registered task definition proves the exact sealed writer command,
environment, 2 GiB generation limit, 5 GiB physical ceiling, required EFS
mount, and one-time recovery contract. After boot, it refuses completion
unless `/ready/guala` proves both content-addressed owners, their identical
5 GiB authority, executed version-aware reconciliation, sealed generation
custody, and retirement of the flat/full-copy producer.

The active persistent-writer census was reconciled to six actual authorities:
the process-lifetime EFS owner record, verified-generation materialization,
owner-scoped hot-state stage, ring persistence consumer, ring S3 recovery
replacement, and deployment seal/transaction metadata. Deleted or dormant
legacy modules are not represented as live writers.

The focused storage-cutover suite passes: **141 tests passed**. It covers
content addressing, authoritative cold and live-recovery stores, generation
retention/reconciliation, all-version ring replacement, the 5 GiB physical
refusal, persistent-writer inventory, ECS fail-closed behavior, and deploy
fail-closed behavior. Python compilation and shell syntax checks also pass.

## Remaining production verification

The checked-in July 28 custody census records that the observed live task used
the old producer. This candidate has not been deployed as part of this audit,
so no live claim is made. The remaining required proof is one authenticated
deployment through `tools/deploy_dsf_ai.sh` followed by the script's deep
`/ready/guala` verification against the new task owner.

No canonical L0-L4 file, runtime core, runtime wrapper, live state, or deployed
service was changed by this storage-cutover audit.
