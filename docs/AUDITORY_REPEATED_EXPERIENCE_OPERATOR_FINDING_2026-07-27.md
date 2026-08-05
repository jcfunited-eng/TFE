# Auditory repeated-experience operator finding — 2026-07-27

## Status

This is an evidence-backed operator proposal, not active architecture and not
a production hearing claim. No L0–L4 or runtime file was modified.

## Architecture honesty gate

1. Requested architecture: repeated source-disjoint physical experiences grow
   causal auditory structure from the joint pressure/phase D/M/R/U/C/P/B field;
   exact L6 locks or fissions it; unknown and overlapping sounds never force a
   word.
2. Current code reality: each auditory pressure or phase port traverses frozen
   L0–L4 independently. Auditory L5 pairs pressure and phase only within one
   cochlear channel. The existing complete phase-resonance graph is not
   executed by the live auditory path, and its optional result is retained by
   `auditory_recurrent_motif.py` only as a receipt rather than as sensory
   structure.
3. Conflict with the requested architecture: yes.
4. Mechanisms that must not be extended: q IDs, Krim/sign paths, transcript
   labels, compatibility vectors, whole-capture fingerprints, scalar scores,
   thresholds, time alignment, ML, and one-shot equality.
5. Single exact next item: implement the proposed cross-receptor operator as an
   isolated read-only probe over the existing physically distinct stereo seam
   before any kernel or live-runtime edit.
6. Field evaluation: the complete explicit D/M/R/U/C/P/B tuples on all
   pressure and phase ports remain authoritative.
7. Reduced structures and their losses: the exact order candidates discard
   magnitude and nonlocal temporal order; the exact ray candidate discards
   common positive scale and global temporal order; exact token sets discard
   multiplicity. None is authorized as hearing identity.

## Repeated-experience evidence

The corpus authority is `/tmp/mini_speech_commands.zip`, SHA-256
`49650f2341b26d886b46b3f4fb8fed59e30300b17550f1ee4a768b3106cf93a0`.
It supplies eight commands, eight globally source-disjoint speakers per
command, five reference speakers and three held-out speakers.

The first recurrence probe grows a token only when canonical L6 locks its
presence across the five causally grouped references. A token recurrent under
more than one causal grounding is retained as shared structure and removed
from identity authority.

Report:
`/tmp/guala_full_field_causal_recurrence_v1.json`

- report SHA-256:
  `4d5d901d24bfd23df090bf6bd937fb8718ac7861da3d2ca51fc8fd9b01bbb072`
- embedded authority:
  `bb5ff63689f97517e6081d2dc13514036ea82b97ee75eda117865fa7ca5f8192`
- complete 70-by-8 query-to-grounding matrices are retained
- all four candidates: reference 0/40, held-out 0/24, unknown rejection 2/2,
  overlapping ambiguity 0/4

The recurrence itself was real:

| Candidate | Recurrent | Shared after causal divergence | Grounding-specific |
|---|---:|---:|---:|
| component field order | 18,468 | 17,165 | 1,303 |
| neighborhood field order | 3,075 | 2,284 | 791 |
| full seven-field ray | 154 | 154 | 0 |
| raw full-field transition | 154 | 154 | 0 |

The reciprocal query relation was therefore too strict: it rejected every
source experience despite grown recurrence.

The second probe corrected that defect without a tolerance. Grounding-specific
recurrence must independently canonical-L6-lock inside the observation;
shared recurrence counts only as matching quiescence; observation-only
structure remains present but is not counted against the memory.

Report:
`/tmp/guala_full_field_causal_resonance_v1.json`

- report SHA-256:
  `c69a4485fbeeb069ad6f01e86af7a7155b922425476c3bfbd07e8c88efcfed83`
- embedded authority:
  `becaae481c5de96598a42b569d4d22f92e56f3471ef96f57ff15b5206af8396e`
- complete 70-by-8 query-to-grounding matrices are retained
- all four candidates: reference 0/40, held-out 0/24, unknown rejection 2/2,
  overlapping ambiguity 0/4

Directional recurrence recovered some source-specific structure but not a
speaker-independent word structure:

| Candidate | Expected source mean/max | Expected held-out mean/max | Wrong grounding mean/max |
|---|---:|---:|---:|
| component field order | 5.2 / 10 of 32 | 0.458 / 2 of 32 | 0.306 / 3 of 32 |
| neighborhood field order | 1.95 / 5 of 28 | 0 / 0 of 28 | 0.002 / 1 of 28 |
| full seven-field ray | 0 / 0 | 0 / 0 | 0 / 0 |
| raw full-field transition | 0 / 0 | 0 / 0 | 0 / 0 |

This falsifies the tested claim that repeated exposure alone can recover a
speaker-independent word relation from the current independent L4 port
outputs. It does not falsify deterministic learning.

## Ear-to-kernel loss localization

The independent bilateral non-flattening audit uses physically nonidentical
left and right PCM:

- one 960-sample PCM16 440 Hz source
- left/right causal delays 10/14 samples
- both attenuations exactly 1
- one transaction with left topology 0–31 and right topology 32–63

It compares the complete parsed trace content at every layer, not receipt IDs,
signs, scores, or token projections.

Measured left/right distinctions surviving:

| Layer | Distinct paired ports |
|---|---:|
| L0 | 32/32 |
| L1 | 32/32 |
| L2 | 16/32 |
| L3 | 14/32 |
| L4 | 14/32 |

All sixteen carrier-phase-advance pairs become equal at L2. Each is a
singleton gate, so independent per-port centering/density/normalization
produces identical CV=0, w=1, S, U, and regime despite different L1 values.
At L3, the two highest pressure-band pairs also become equal because each
port's CV norm is divided by that port's own maximum.

This is not proof that frozen per-port kernel physics is wrong. It proves that
bilateral and cross-channel relations cannot be delegated to independent
per-port normalization.

Authorities:

- `docs/HEARING_SCOPED_KERNEL_CHANGE_VALIDATION_GATE_V1.md`
- `tests/fixtures/auditory_bilateral_nonflattening_contract_v1.json`
- `tests/test_auditory_bilateral_nonflattening_contract.py`
- `tools/isolated_w1_physical_stereo_path.py`
- `tests/test_isolated_w1_physical_stereo_path.py`

## Existing unused physics

`dsf_ai_service/substrate/auditory_receptor_resonance_graph.py` already mounts
the complete sixteen-channel cumulative-phase graph: all 120 unordered
cross-channel edges, pressure-squared relevance, common causal grid, and
receipt authority.

`dsf_ai_service/glew_runtime/operators.py` already supplies the certified
gamma-squared cross-port resonance operator. Its `edge_facts` retain every
edge. Its scalar meet must not become sound or word identity.

The live full-field builder instead runs one L0–L4 trace per port.
`auditory_recurrent_motif.py` accepts an optional resonance confirmation but
only binds its edge facts into a receipt. They do not participate in receptor
experience growth or causal recurrence.

## Precise proposed operator

Name:
`AuditoryBilateralCrossReceptorResonanceTrajectory`

Layer:
auditory receptor governance immediately after the frozen independent L0–L4
ports and before auditory causal recurrence. This is an L5 sensory operator,
not a replacement for L0–L4.

Inputs:

1. one verified left and one verified right
   `AuditoryReceptorFullFieldEvent`;
2. all 32 cumulative-phase receptor streams in stable ear/channel order;
3. all 32 paired pressure streams with exact relevance `r = p²`;
4. every paired pressure/phase D/M/R/U/C/P/B tuple and source interval;
5. the complete mounted 32-vertex resonance graph;
6. one explicit pinned certified-operator precision authority;
7. one receipted common causal event grid derived from physical receptor event
   boundaries, never from a word label or favorable result.

Topology:
the complete unordered graph over 32 cumulative-phase receptors: 496 edges.
This contains 120 left-ear edges, 120 right-ear edges, and 256 cross-ear edges.
No edge may be selected, dropped, averaged, or reweighted after observing a
result.

Operation:

1. execute the existing certified gamma-squared operator on every required
   edge for each physically closed receptor event;
2. retain the complete ordered 496-edge fact set, including certified ball
   bounds and proved-zero-energy state;
3. bind that edge set to the simultaneous full 64-port L4 tuple support,
   pressure/cumulative-phase source receipts, ear/channel topology, B/C
   directions, and causal interval;
4. expose the ordered event sequence as a trajectory; do not replace it with
   the scalar graph meet;
5. allow repeated causally grounded trajectories to grow through exact L6:
   grounding-specific recurrence is non-null, recurrence shared across
   outcomes is quiescent, and divergent consequences fission the grounding;
6. return unknown when no complete causal memory locks and ambiguous when
   more than one locks. Never choose by a score.

Output:
an immutable `AuditoryBilateralResonanceTrajectory` containing:

- ordered event intervals;
- all 496 edge facts per event;
- all 64 ordered L4 component support roots;
- every original tuple/source authority root;
- left/right transport and calibration receipts;
- graph, operator, grid, and trajectory receipts;
- typed state `observed`, `unresolved`, or `resource_exhausted`.

Invariants:

- L0–L4 bytes and equations remain unchanged.
- Explicit D/M/R/U/C/P/B fields remain authoritative.
- Raw cumulative phase cannot be replaced by phase advance.
- Mono copied into two ears cannot claim bilateral separation.
- Missing ear, edge, common grid, source receipt, certified backend, or unique
  ball result is typed unresolved.
- A scalar resonance meet, rank, score, transcript, q ID, sign vector, or hash
  cannot become identity.
- Original evidence remains reachable through authenticated roots.

Cadence and resource bounds:

- execute once per physically closed receptor event, not per transcript or
  guessed word;
- at most 800 10 ms frames per eight-second capture under the existing
  receptor bound;
- exactly 496 edges per bilateral event;
- retain at most the existing bounded auditory memory authority: 64 causal
  kinds, four recent source-disjoint exemplars per kind, 4,000,000 relation
  cells, and 64 MB encoded state;
- on any bound exhaustion return `resource_exhausted`; never release a partial
  recognition.

Persistence:
persist trajectory receipts, recurrent/fission state, causal grounding
receipts, and bounded exemplar witness roots. Cold restore must reproduce the
same roots before the memory may recognize. The raw PCM ring may expire under
its existing bound; expiring PCM cannot erase the retained authenticated
source and tuple commitments.

## Required proof before implementation or deployment

The isolated operator must first pass all of these without a kernel edit:

1. nonidentical left/right input produces nonidentical cross-ear facts while
   identical mono ears are explicitly spatially unresolved;
2. five source-disjoint experiences grow a memory that uniquely recalls all
   three held-out speakers for each of eight commands;
3. unrelated tone experiences remain unknown;
4. physically distinct overlapping left/right voices retain two causal locks,
   not one forced label or zero;
5. gain and transport-boundary changes preserve the causal relation without
   padding, cropping, interpolation, or alignment;
6. all matrices, edge facts, tuple roots, receipts, and resource counts are
   emitted for independent verification.

If this probe fails, the failure must identify the earliest missing physical
relation before any change to frozen L0–L4.
