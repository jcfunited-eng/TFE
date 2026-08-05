# Guala Production Storage Runaway Incident — 2026-07-27

## Requested architecture

Persistent bytes must arise from retained substrate experience, learned
sensory state, exact transactional recovery, and small authenticated
observational receipts. Unchanged cognition must not be copied merely because
a new generation is published. No learned state may be evicted to satisfy a
capacity limit.

## Production evidence

The live ECS task was
`2d8160bf5bde454c8bcce2d8d63be5ac` in cluster
`tfe-web-cluster`, task definition `dsf-ai-task:762`. The EFS state root was
`/app/guala`. The S3 recovery bucket was `dsf-ai-site-backups`.

Before cleanup, EFS contained 2,552,774,656 bytes:

- active flat state: approximately 629 MB;
- legacy recovery `guala_deep_atlas.v2.json`: 592,021,779 bytes;
- two full sealed generations: approximately 631 MB each;
- three explicitly rejected or incompatible live-recovery trees:
  approximately 43.6 MB;
- the valid live-recovery store: approximately 26.9 MB.

The 288,645,120-byte `guala_organism.sgr` had the same SHA-256 in
the active tree and both sealed generations, but all three had distinct
inodes and link counts of one. Two redundant physical copies therefore
consumed 577,290,240 bytes without representing additional cognition.

The organism contained only 106 Loom neurons, but its SQLite graph contained
1,732,485 nodes and 6,649,778 edges. It included 707,113 ndarray nodes;
706,538 repeated the same float64-six-value structural metadata. The 106
large numeric buffers occupied 41,091,072 raw bytes and compressed
losslessly to 1,532,534 bytes in a read-only census.

The active deep atlas reported 72,268 entries. Its encoded columnar body was
repeated between active state and the current sealed generation. The
592,021,779-byte recovery file was an older `deep_atlas_v2` artifact with
51,572 entries and was not referenced by current production code. It remains
preserved pending authenticated containment proof.

S3 version enumeration exposed the principal runaway:

- 5,275 generation object versions totaling 37,555,015,671 bytes;
- only 185 latest generation objects totaling 1,260,250,898 bytes;
- 5,090 noncurrent generation versions totaling 36,294,764,773 bytes;
- 5,090 deletion markers.

Other Guala prefixes contained another 6,713,933,144 bytes of noncurrent
versions, chiefly legacy event bodies. Those bytes were logically deleted but
remained physically retained by S3 versioning.

## Root causes

1. Every generation uploaded full payload bodies beneath a generation UUID.
2. Local immutable generations stored separate physical files even when
   payload bytes were identical.
3. Generation-specific JSON envelopes prevented content reuse for otherwise
   unchanged JSON payloads.
4. S3 reconciliation created delete markers but did not permanently delete
   the superseded object versions.
5. The lifecycle policy retained noncurrent Guala versions for seven days.
6. The lifecycle policy also expired current generation objects after seven
   days, risking loss of valid unchanged learned state.
7. The general structural-graph encoding expanded repeated ndarray metadata,
   dictionaries, and edges far beyond the retained numeric payload.
8. Rejected and incompatible live-recovery trees remained indefinitely at the
   EFS root.

These are persistence and representation failures. They are not learning.

## Actions completed

All mutations used exact bucket prefixes or exact EFS paths and were followed
by a fresh census.

- Permanently deleted 5,090 noncurrent generation versions and 5,090
  generation deletion markers.
- Permanently deleted another 184 noncurrent Guala versions and 170 deletion
  markers outside the generation prefix.
- Reclaimed 43,008,697,917 bytes of unreachable S3 object versions.
- Retained and reverified every latest visible Guala S3 object: 4,876 objects
  totaling 3,022,493,231 bytes.
- Retained all 185 latest current-generation objects totaling
  1,260,250,898 bytes.
- Removed the three exact rejected/incompatible EFS recovery trees. They were
  not authoritative and are not recoverable.
- Reduced live EFS usage to 2,509,664,256 bytes without removing the active
  tree, valid live recovery, sealed current generation, sealed predecessor, or
  legacy recovery artifact.
- Changed the live S3 lifecycle so current generation objects no longer
  expire by age.
- Changed noncurrent generation, event, and checkpoint retention to one day
  as an emergency transition backstop.

## Required producer replacement

Cleanup is not completion. The full-copy writer must be retired.

The replacement contract is:

- payload and chunk bodies are addressed by SHA-256, locally and remotely;
- unchanged bodies are stored and uploaded once;
- generation identity and tick live in authenticated manifests, not copied
  payload envelopes;
- a small mutation writes only changed chunks and a new manifest;
- retained manifests are the sole reachability roots;
- garbage collection removes only objects unreachable from every retained or
  in-flight authenticated manifest;
- cold save and restore materialize private transient trees only;
- successful publish or restore leaves zero permanent full active
  compatibility copy and zero orphan temporary tree;
- explicit hot state and compact HMAC observation receipts may remain active;
- every full D/M/R/U/C/P/B field, neuron, alias, and learned sensory value
  restores exactly;
- legacy flat generations remain readable solely for authenticated migration;
- remote generation UUID prefixes no longer receive copied payload bodies;
- sustained save, play, sensing, and learning tests measure authoritative
  growth, transient high-water bytes, orphan count, and write amplification.

The structural graph also requires a versioned compact codec for exact ndarray
payload compression and repeated-metadata/edge columnarization. That codec is
a persistence representation change only; it must not change L0-L4, neuron
state, DSF fields, graph aliases, or restored values.

## Preserved pending classification

The older dated S3 snapshots, `guala/auto/`, and the EFS
`recovery/guala_deep_atlas.v2.json` remain read-only. They may contain
historical entity state or migration evidence. They will not be deleted until
the current authenticated state or a migration archive proves exact
containment. They are not active architecture.
