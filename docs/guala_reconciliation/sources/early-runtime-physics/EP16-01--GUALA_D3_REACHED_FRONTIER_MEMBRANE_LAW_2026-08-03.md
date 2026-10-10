# D3 Reached-Frontier Membrane Law

Status: implemented native law. This document describes the production path in
`runtime_position_gated_membrane_network.rs`; it is not a future-state claim.

## Physical transition boundary

An ordinary membrane transition evaluates the exact topology-addressed
candidate contacts carried by the predecessor state. It does not scan the
network to rediscover activity. The next candidate set is the sorted union of
contacts incident to:

1. endpoints whose charge changed through an exact nonzero membrane transfer;
2. neurons whose exact K projection/anatomy changed in the same cause; and
3. endpoints changed by an admitted external charge cause.

The initial admitted state has no predecessor reach history, so every admitted
contact is an explicit first-settlement candidate exactly once. This is
topology admission, not an inferred active cap. A settled quiescent contact is
not carried forward unless an endpoint charge or K state later changes.

The exact passive transfer calculation remains the shared position-gated law.
Only its topology view is compacted to the addressed candidate contacts and
their endpoints. No coefficient, threshold, heuristic pruning, score, ML,
owner, lock, or arbitrary capacity is introduced.

## Reached participant law

The canonical reached lineage set is the sorted union of:

- authenticated current receptor/body/endogenous source participants;
- neurons with an exact same-cause K projection/anatomy change; and
- endpoints of exact nonzero membrane transfers.

Each lineage entry carries those three cause classes independently. An active
gate with zero transfer is not a reached participant. A transfer-only endpoint
is sealed physical propagation evidence, not a fabricated current DSF/neuron
success. It may become an endogenous coupled temporal source in a later
generation, after which the full L0-L4 delivery path must run before mosaic
eligibility.

## Persistent state

Topology admission creates one immutable base state body and one exact topology
index body. Successor generations retain those bodies by content address.
Changed node values are inserted into a persistent, path-compressed Patricia
tree keyed by topology node index. An update creates only the changed leaf and
the branch path to the new root; inactive subtrees remain shared by `Arc` and by
their immutable receipts.

The generation checkpoint contains only:

- topology index authority;
- immutable base-state authority;
- current Patricia override-root authority;
- exact tick and total charge; and
- sorted next-candidate contact identities.

It never serializes every inactive neuron or a vector of zero edge transfers.

## Cold truth checks

`inspect_runtime_membrane_checkpoint` verifies the checkpoint authority,
topology and base objects, every Patricia page reachable from the override root,
every override entry, exact charge bounds and total charge, and every candidate
contact.

`inspect_reached_runtime_membrane_transition` additionally verifies every
reached entry, source category, K-change evidence body, nonzero-transfer
evidence body, endpoint topology, and exact equality between per-lineage
transfer membership and the sealed transfer records. Missing, substituted,
tampered, unordered, zero, or unreachable evidence is refused.

## Resource truth

Every reached transition reports exact work derived from the physical frontier:
candidate contacts evaluated, compact nodes loaded, nonzero transfers, changed
nodes path-copied, immutable pages created, and next-frontier contacts. The
production report records zero for full-network node and edge polling because
the production transition has no such path. Growth is proportional to exact
causal reach and changed Patricia paths; there is no heuristic active cap.

## Deleted mechanisms

The former runtime-sized whole-network `transition`, `transition_sparse`, full
state transition encoder, v1 full-scan inspector, and separately admitted
legacy restore path were physically deleted. There is no compatibility shim or
test-only callable copy of those mechanisms.
