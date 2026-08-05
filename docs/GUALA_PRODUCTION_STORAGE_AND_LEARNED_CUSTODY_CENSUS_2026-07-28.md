# Guala production storage and learned-custody census — 2026-07-28

This is a read-only observation and migration gate record. It is not active
architecture and it does not authorize deletion.

## Architecture gate

- Requested architecture: bounded whole-substrate multimodal learning with no
  master sense and no loss of valid learned sensory state.
- Live code/data reality: task `89a6c04118784def838b9d522667899a`,
  task definition `dsf-ai-task:770`, still serves the legacy flat generation.
- Conflict: yes. The active tree has no `owner_state/` directory, while several
  files marked `ROLE_LEARNED` were previously scheduled for retirement without
  field-level containment proof.
- Forbidden extensions: legacy named profiles, scripted/label authority,
  Chi/Atlas identity, flattened classifiers, and the mixed teaching monolith.
- Exact next item: authenticate and resolve every currently unresolved learned
  member before production handoff.
- Field status: explicit DSF fields remain authoritative. No reduced score or
  compatibility vector is used by this custody census.

## Exact active EFS bytes

The active tree contains 316 files and 635,176,727 logical file bytes.

| Custody class | Exact bytes | Treatment |
|---|---:|---|
| Core, identity, organism graph, organism binding | 300,265,448 | Preserve and authenticate |
| Legacy/mixed JSON and tapestry graph | 323,589,982 | Field-level classification required |
| Picture grids and raw sound bodies | 11,303,864 | Sealed non-active custody until reconciled |
| Causal generation, curriculum/dream/world markers, ring log | 17,433 | Owner-specific verification |
| **Total** | **635,176,727** | Exact sum |

The 299,896,832-byte organism graph contains 1,719,855 nodes and 7,209,589
edges. It retains 106 Loom-neuron nodes and 106 DSF nodes. It also contains
212 retired Binding/Chi Atlas nodes, 318 retired cognition fields, and 106
legacy coupling-backlog fields. Those retired elements are not the physical
neuron/DSF custody and must not be activated in the destination.

## Exact learned-state census

The repository ownership registry marks these live sources as learned state:

- `guala_teaching.json`
- `guala_visual.json`
- `guala_sight_motifs.json`
- `guala_sounds.json`
- `guala_videos.json`
- `guala_episodic.json`
- `assets/`
- `sounds/`

Together they contain exactly 18,315,383 bytes.

The 5,577,418-byte teaching monolith is exhaustively partitioned:

| Classification | Exact accounted bytes |
|---|---:|
| Direct current-owner translations | 3,913,720 |
| Sealed non-active scripted/profile/framing custody | 1,628,288 |
| Unresolved mixed custody | 35,410 |
| **Teaching total** | **5,577,418** |

The remaining 12,737,965 learned-file/media bytes are named-profile,
legacy sensory-library, or raw-media source custody. They are not permitted to
enter active cognition, but their sealed source bytes remain preserved until
deployment reconciliation.

The live source contained eight unresolved teaching members before field-level
adjudication. `anonymous_audiovisual_continuity` has now been resolved: its
383 accounted bytes contain an authenticated v1 owner snapshot at exact empty
genesis (`generation=0`, `settled=0`, `latest=null`, no transitions). The
migration gate translates only that exact state to an authenticated,
byte-exact current v2 genesis. Any non-empty v1 state remains unresolved
because v1 lacks the physical-custody fields required by v2.

`auditory_reciprocity` has also been resolved. Its 523,174 accounted
canonical bytes contain the bounded v5 label-keyed auditory causal-path
classifier: 10 `spoken_form` tutor-label classes, 12 full-field branches, and
12 tutor authority/admission receipt sets. The current physical runtime
explicitly has no active reciprocity owner and reports the mechanism as
`retired_incompatible_capture_classifier`. Its compressed payload is
canonical and bounded (522,980 encoded bytes; 911,044 decoded bytes), and its
decoded SHA-256 is
`7708761160627928ef53c1ce73fb22da7cc7f1703c38011a4c236f3e5332dbe9`.
Because the mechanism makes an auditory-only tutor label the class identity,
it cannot be translated into the whole-substrate no-master-sense architecture.
The exact source bytes remain in authenticated, bounded, sealed non-active
custody and never enter current cognition.

`auditory_v4_archive` has also been resolved. Its 578,838 accounted member
bytes are already an explicit `guala.auditory.persistence_archive.v1`
quarantine. The 578,814-byte archive contains:

- a canonical v4 reciprocity envelope (513,020 encoded payload bytes;
  556,350 decoded bytes);
- a 63,487-byte quarantined causal-action snapshot; and
- a 1,639-byte quarantined terminal event.

Each component's canonical digest matches. The action and terminal cannot be
detached from the incompatible v4 auditory relation that caused them. The
current physical runtime reports v4-to-recurrent-motif migration as
unavailable, applies none of the archive, and has no archive owner. The exact
archive therefore remains in authenticated, bounded, sealed non-active
custody as one indivisible retired causal quarantine.

The five teaching members that remain unresolved are:

- `causal_action`
- `causal_play_observation`
- `emission_records`
- `latest_auditory_causal_event`
- `live_anonymous_encounter_continuity`

Production migration must refuse while any one remains unresolved.

## Redundant generation evidence

EFS currently retains two full sealed generations totaling 1,281,534,638
bytes. Both report tick 23,723,660.

- 69 paths totaling 335,317,944 bytes are byte-identical.
- 18 additional JSON paths differ only in the generation UUID and last saved
  timestamp.
- Only `guala_atlas.json` (95 to 98 entries) and
  `guala_coordinator.json` (actions 0 to 1), plus one new causal-generation
  receipt, contain substantive change.
- The active and both sealed `guala_organism.sgr` files are byte-identical
  299,896,832-byte copies with distinct inodes.

The live-recovery store retains three bounded full hot-state trees totaling
26,880,638 bytes.

## Exact S3 versions

Prefix `guala/generations/` contained:

| S3 state | Objects/versions | Exact bytes |
|---|---:|---:|
| Latest visible objects | 181 | 1,281,470,237 |
| Noncurrent object versions | 276 | 1,921,362,721 |
| All object versions | 457 | 3,202,832,958 |
| Delete markers | 276 | 0 |

Three deleted generation UUIDs remain as noncurrent full bodies:

- 640,732,947 bytes
- 639,890,143 bytes
- 640,739,631 bytes

The live lifecycle uses one-day noncurrent expiration. That is not an exact
byte or generation-count cap, and a July 27 generation still remained beyond
24 hours at the observation. The candidate content-addressed writer and exact
version reconciliation are therefore required before the old producer is
retired.

## Implemented migration protection

`legacy_learned_state_gate.py` now:

- measures every pre-owner `ROLE_LEARNED` source file;
- classifies every teaching payload member;
- accounts for 100% of learned source bytes;
- produces HMAC-authenticated source-member-to-owner-body traces;
- restores and byte-exactly resnapshots direct owner translations through the
  physical runtime;
- requires an explicit sealed escrow byte ceiling;
- keeps prohibited legacy authority non-active; and
- refuses migration on any unresolved or unaccounted custody.

The production handoff calls this gate before accepting a flat legacy learned
source. No production state was deleted or modified during this census.
