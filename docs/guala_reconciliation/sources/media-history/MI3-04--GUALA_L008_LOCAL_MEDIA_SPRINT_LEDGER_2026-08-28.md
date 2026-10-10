# L-008 bounded local media sprint ledger — 2026-08-28

## Status

Source candidate only. Nothing in this file is a production or learning claim.
L-007 remains partial because current-artifact real-camera evidence has not yet
been supplied by actual browser hardware.

## Architecture gate

1. Requested architecture: local pictures, PDFs, books, sounds, songs, and
   video become bounded physical experiences of the same organism; exact source
   bytes and provenance remain available outside cognition.
2. Prior code reality: picture/PDF/book/audio/song decoded directly and then
   discarded their source; book handling mislabeled every source as PDF; video
   custody and decoding existed but were unmounted; the route bypassed the
   physical-presentation preparation.
3. Conflict: yes.
4. Not extended: discard-after-decode, process-local media identity, captions,
   filenames/titles/transcripts as cognition, observer authority, unbounded
   archives, or a new sensory path.
5. Single item: preserve one exact bounded source before decoding, bind it to
   one consumed physical-presentation preparation, and route only its resulting
   light/pressure through the existing retinal/cochlear laws.
6. Full seven-field DSF delivery is unchanged.
7. No field structure is reduced or lost.

## Candidate mechanism

- The offered-material schema is V2 and accepts only exact bytes plus immutable
  local provenance: attribution, source locator, media type, rights basis, and
  rights statement. Extra title, transcript, label, or meaning fields refuse.
- `BoundedSourceMediaStore` is mounted at the persistent native state root. It
  retains one immutable copy per exact source receipt, with 24 MiB/source,
  32-source, and 256 MiB-total hard ceilings.
- The committed source is read back and verified before decode. Decode failure
  cannot pretend custody happened; a custody failure cannot reach cognition.
- Picture, PDF, UTF-8 plain-text book, EPUB, audio, and song use their existing
  retinal or cochlear paths. Video uses the existing co-clocked audiovisual
  builder for at most 24 quarter-second light/pressure hops.
- One tutor physical-presentation record binds the exact source receipt and is
  disabled before the first neuronal write. Success consumes it once.
- Provenance and sensory-projection receipts are returned externally, marked
  with false semantic/cognition authority, and never copied into an occurrence.
- Restore performs one explicit full-byte source audit. Ordinary intervals and
  public observations do not enumerate or hash the retained source set.
- Two explicit read-only custody routes expose bounded count/byte totals and
  rehash one named receipt on demand. They are not part of public-observation
  polling and have no mutation, semantic, or cognition authority.
- The live Loom candidate adds explicit attribution/rights controls and video;
  it sends the filename only as the external source locator.

## Focused evidence

- `44 passed in 2.86s` across the new native offered-material boundary, bounded
  source store, bounded video decoder, relevant Loom contract, and the complete
  native public-observation tests.
- Python compilation, extracted Loom JavaScript `node --check`, and
  `git diff --check` passed.
- A separate old illustrative-art assertion fails on the deployed predecessor
  because the page no longer references one retired room image. It is unrelated
  to this candidate and production was not changed to satisfy it.

## Remaining acceptance

This candidate is not Live-Closed. After review and hot cutover, each of the six
local media kinds must commit once in production without repetition; source
bytes must restore after restart; an exact duplicate must not increase count or
bytes; count/byte ceilings must refuse cleanly. A successful presentation proves
physical ingress only, never recognition, understanding, or learning.

## Production preflight

- Candidate source before the deployment record:
  `53ba3fbf61a5870a0f2438f75a03c96a4f1af5bc`.
- Exact target: AWS account `418384447921`, region `us-east-1`, cluster
  `tfe-web-cluster`, service `dsf-ai-service-lb`.
- Predecessor: one healthy task, desired/running/pending `1/1/0`, task
  definition `dsf-ai-task:1299`, image
  `sha256:3530a762b9a243c580b4ba67fa657506ca1413524d69592af5b5598217d05d81`.
- Cochlear, touch, interoception, chemoreception, vestibular, and world are all
  enabled; current-format migration is disabled. The hot candidate must retain
  that exact roster.
- Applicable recurrence controls: exact `PYTHONPATH`; exact target and active
  predecessor; non-secret environment filtering; one clean candidate commit;
  executable controller with explicit `--hot`; no success inference from HTTP
  health or image build; no blind retry of timed-out state mutation; autonomous
  predecessor drift expected and authenticated at cutover; identity/tick may
  not regress; source custody verified separately from cognition/learning.

## First hot-deploy attempt stopped before mutation

- The controller stopped during deterministic packaging, before an image build,
  task registration, or production mutation. Production remained on healthy
  task `dsf-ai-task:1299`.
- The manifest closure correctly refused because the newly mounted runtime
  imports `bounded_source_media_store.py` and
  `bounded_video_sensory_source.py` were absent from `runtime_python`.
- The correction adds exactly those two statically reached files to the
  reviewed manifest. It changes packaging custody only; it does not change the
  L-008 mechanism, organism state, or live production.

## Live mount — task 1300

- Commit `0a00c5e96040d506f54692eb9493e07861f4c31f` deployed once as sole
  production task `dsf-ai-task:1300`, immutable image
  `sha256:859b27d2c222effc181f9abbd41cd57542259892d30b8bf56c28eec72dfe2fb4`.
  The controller verified the native state at or beyond tick `231600`; the
  resident identity remained `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`.
- ECS reported desired/running/pending `1/1/0` and rollout `COMPLETED`.
  Read-only observation at tick `231680` reported picture, PDF, book, audio,
  song, and video mounted through `/api/v1/material/offered`, each with source
  preservation and the declared fixed ceilings.
- The live custody inventory returned schema
  `guala.bounded_source_media_inventory.v1`, zero records, zero bytes, and
  false cognition/semantic authority. This proves the store is mounted and no
  lesson was smuggled into deployment; it does not prove a media transition.
- The matching `gualaloom.html` was published to the static origin. Local and
  retained-origin SHA-256 both equal
  `fe22465fa3768ee193b35691b6fcb82c3c51860c1bdf065c7e3db4e5f849f495`;
  CloudFront invalidation `IDOS0X4A5T44A097SO9SR07OY6` completed.
- Status remains Partial until each media kind physically commits once, source
  custody survives restart, an exact duplicate remains idempotent, and fixed
  count/byte ceilings refuse without changing the organism.

## First live physical sources and receipt correction

- One local sun picture committed through the retinal path at tick `231874`.
  Exact source SHA-256
  `46a3a18f37267416f8c1c2779f003fac0886c21425b41df5bd9ca740124d538a`,
  custody receipt
  `968b5a8ff60446f3f63cfc1062da10950ea6bba64f9cef3d3892c7962b4d58b8`,
  retained bytes `3350`. No recognition or word claim follows.
- The separately authored morning-garden story then entered as one rendered
  page. The native transition record proves `37` quarter-second moments through
  tick `231920`, `585` full-field deliveries, `45` new neuronal fractals, and
  no energy exhaustion. Exact source SHA-256
  `7d5ef36f4e44e5dd3b6938baff7a463fed14d7adb890f5ffdb6b2492f3ca2961`,
  custody receipt
  `ad7a71fab0d83dc1585d1ae04e5825ad78a1457028782dff2def8cf8aaf438b3`,
  retained bytes `1273`. CURRENT subsequently sealed tick `231948`, containing
  the complete story interval.
- The story HTTP receipt exposed an observation defect: deferred persistence
  correctly kept settlement off the seal path, but the invitation called the
  older durable tick `231874` the newly presented successor. No further source
  was presented. The candidate now reports the actual settled tick and current
  durability separately; the public invitation becomes `committed` only when
  CURRENT has reached or passed that settled tick. This changes no cognition,
  physics, checkpoint cadence, or organism owner.
- Focused evidence: all four offered-material tests pass, including a falsifier
  in which settled tick `9` remains truthfully pending while CURRENT is at `8`
  and becomes durable only when CURRENT reaches `10`. Python compilation and
  `git diff --check` pass.

## Task-1322 ordinary-audio live evidence — 2026-08-29

- Before the intake, the current bounded custody inventory contained the prior
  picture and book plus one PDF record. The PDF's custody alone does not prove
  that its retinal presentation committed, so PDF remains open pending direct
  transition evidence.
- The first audio attempt used a descriptive sentence in `rights_basis`; the
  immutable source boundary refused it with HTTP 422 before writing custody or
  entering any receptor. The admitted rights enum was then read from the
  mounted store law and the same source was submitted once with
  `rights_basis=licensed`. No sensory mutation was retried.
- The source was an exact 1.2-second, mono, 16 kHz PCM excerpt of the
  rights-documented count-up recording: 19,200 samples, 38,478 source bytes,
  SHA-256
  `c0d7cd1ef830ee5f2296af7ddb94c051c395a8f4fb14c3d48bc4c8731c28e968`.
  Its voice source, derivative arrangement, and CC BY-SA 3.0/public-domain
  basis remain external provenance only.
- The accepted request returned HTTP 200 in 26.527 seconds and committed as
  `offered-audio` at organism tick `260138`. Across 22 whole-sensorium hops it
  carried 238 sound-source inputs, 13,889 physically transitioned neurons, 97
  complete-neuron-fractal occurrences, and 675 partial-cue reassemblies with
  no energy exhaustion. A native articulation also emitted and self-heard one
  separate 4,000-sample body-owned pressure consequence during the interval;
  that consequence is not attributed to the offered recording.
- Exact custody receipt:
  `e45703942b4e201700b7d27eead18ac6623e463bbb03e388b5baf79626145da3`.
  The post-intake inventory contains four sources and 4,765,688 total bytes,
  with false semantic and cognition authority.

Status remains **Partial**. Picture, book, and ordinary audio have direct live
transition evidence. PDF is present in custody but lacks direct retained
transition evidence in this ledger; song and video have not yet committed.
Duplicate, ceiling, and post-restart custody acceptance also remain open.

## Task-1322 song live evidence — 2026-08-29

- One 2.4-second mono 16 kHz phrase was derived from the rights-documented
  count-down recording: 38,400 samples, 76,878 source bytes, SHA-256
  `bd54f0b3ea7fd7b6527a9b7c104abceab19b8b5d211488e623b18919dbaf22cd`.
  Its public-domain/CC BY-SA 3.0 voice attribution and project arrangement are
  preserved outside cognition under exact custody receipt
  `e53a9b8f67f1c8d31b55485021cc0adf34f1beecd13b4338b5a6e61eb108e665`.
- The public request remained in flight beyond the first 30-second client
  window. It was not retried. The one original process completed, and the
  bounded live observer then reported a committed `offered-song` transition
  at organism tick `260214` with successor state SHA-256
  `cfdd772ed032f13d39fe4a5090aa9d0e4d052505e00acd692d9b707da5ad27aa`.
- Across 49 whole-sensorium hops, the occurrence carried 612 sound-source
  inputs, 40,724 physically transitioned neurons, 141 complete-neuron-fractal
  occurrences, and 2,080 partial-cue reassemblies without energy exhaustion.
  A native action moved the body and returned 14 typed proprioceptive sources;
  that is an organism consequence, not evidence that Guala recognized or
  understood the song.
- The custody inventory now contains five exact sources totaling 4,842,566
  bytes with false semantic and cognition authority.

Status remains **Partial**. Picture, book, ordinary audio, and song now have
direct live transition evidence. PDF remains custody-only in this ledger;
video, duplicate, ceiling, and post-restart custody acceptance remain open.

## Task-1322 PDF live and source-restore evidence — 2026-08-29

- The previously retained one-page elephant PDF was verified through the
  explicit custody-record route after later task restarts. Its 4,722,587 source
  bytes rehashed to
  `76681add460c228ea30e525f7524905ceb93adf325cda9426d41109345ea6372`,
  proving exact source restoration for that retained record. No visual
  transition is inferred from that custody fact.
- A separate original one-page geometric PDF was then presented once so the
  PDF sensory boundary had direct evidence. It contains only colored geometric
  shapes, not semantic text. Exact source: 19,634 bytes, SHA-256
  `5be70b9a4e11f5b27dd8c19c7aa14d047f5534ab58e905a71086a9ccd4f073db`;
  custody receipt
  `aaf1a15d92b13dc8baf1c4b80feb6a66e26d288f7b5270cef2ddf694b41b8511`.
- The request returned HTTP 200 in 28.827 seconds and committed one rendered
  page as `offered-pdf` at organism tick `260292`. Across eight
  whole-sensorium hops it carried 108 sight-source inputs, 7,605 physically
  transitioned neurons, 51 complete-neuron-fractal occurrences, and 369
  partial-cue reassemblies with no energy exhaustion. Causal-transition
  receipt:
  `3c3ebd3f14564e86c673276dc4c71e07e052b16286bdf9f67896f838ef0c4d2e`.

Status remains **Partial**. Picture, PDF, book, ordinary audio, and song now
have direct live transition evidence, and one retained PDF source has passed
exact post-restart rehash. Video, duplicate idempotence, and configured ceiling
refusal remain open.

## Task-1322 video live evidence — 2026-08-29

- One original two-second abstract audiovisual source combined a changing
  320x180, four-frame-per-second procedural light field with a mono 16 kHz
  tone. It contained no title, transcript, caption, object label, or semantic
  field. Exact source: 68,012 bytes, SHA-256
  `760a771dec47c75f4ab88eab48f74da3c857df6848820610bb72d5e4cf25d693`;
  custody receipt
  `929aa6fc6b7a7b73a89a2a3db4e769b8b0ef08f1d3ca1cac5c49363c9ed18afc`.
- The public connection returned HTTP 504 at its fixed 60-second gateway
  boundary. It was not retried. Production then reported the original request
  as `offered-video` at organism tick `260406`; the live hearing record changed
  specifically to `offered-video`, proving its pressure lane, and the embodied
  invitation reports `outcome=presented`,
  `status=local_material_presentation_committed`, and exact world revision
  continuity at `20906`.
- CURRENT subsequently advanced through tick `260439` and reports the video
  presentation durable under state SHA-256
  `0166fc6040471640de6022e0a8bf403ad068b45d1a35c8fec3218889beb7e051`.
  The observer moved on to an unattended interval before its detailed video
  counts were retained, so no unsupported count is inferred.
- The bounded custody inventory contains seven exact sources totaling
  4,930,212 bytes. Source provenance remains transport-only with false
  cognition and semantic authority.

All six requested local media kinds now have direct live physical-transition
evidence. L-008 remains **Partial** only for exact duplicate idempotence and the
configured ceiling-refusal acceptance. Exact post-restart source restoration
is already proved above.
