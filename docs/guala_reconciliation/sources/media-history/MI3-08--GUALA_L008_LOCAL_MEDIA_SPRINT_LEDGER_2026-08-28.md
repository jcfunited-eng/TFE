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
