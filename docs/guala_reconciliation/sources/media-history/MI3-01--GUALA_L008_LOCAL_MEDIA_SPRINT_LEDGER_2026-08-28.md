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
