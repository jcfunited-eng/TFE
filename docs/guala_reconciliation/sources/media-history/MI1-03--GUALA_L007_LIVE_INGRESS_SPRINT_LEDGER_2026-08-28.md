# L-007 live physical ingress sprint ledger — 2026-08-28

## Frozen item

- Active item: **L-007** — connect live camera, microphone, and rendered text so
  input reaches the same resident organism only through physical sensory paths.
- Closed predecessor: L-006, physically caused articulation, self-hearing, and
  later learned reuse; this sprint does not reopen it.
- Production baseline: commit `c9deed6098a4713ffe4d8d2fce7b4af477c42a23`,
  ECS task definition `dsf-ai-task:1298`, organism identity
  `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`.
- Exact input: browser camera frames, signed-16 mono microphone pressure at the
  mounted 16 kHz cochlear rate, or browser-rendered glyph pixels.
- Exact output: admitted native whole-sensorium occurrences in the one resident
  cognition, followed by its normal atomic successor and bounded public evidence.

## Path and invariant

1. Camera: `gualaloom.html` -> `/api/v1/visual/live-frames` -> retinal roster.
2. Camera plus microphone: `gualaloom.html` ->
   `/api/v1/sensory/audiovisual` -> co-clocked retinal and cochlear rosters.
3. Microphone without camera: `gualaloom.html` ->
   `/api/v1/curriculum/guided-world-voice` -> physical pressure alongside the
   exact current world, body, and other available sensory lanes.
4. Rendered text: browser renders glyphs ->
   `/api/v1/material/rendered-light` -> the same retinal roster; the string is
   never submitted.

The camera remains optional for hearing. When both devices are open, their
co-captured path remains authoritative. No transcript, word, object, filename,
meaning, attention, recognition, or learning label enters cognition. No L0-L4,
DSF, neuron, receptor, formation, persistence, or autonomy law changes.

## Current contradiction and rejected path

- Source reality: the grounded-world voice path is mounted and already builds
  full current-world sensorium episodes, but `micGate()` refuses microphone
  permission without `cameraStream`; `stopCamera()` also stops the microphone.
- Public reality: `capabilities.text_visual` is mounted while `sensory.text`
  says the rendered-light transition is not mounted.
- Rejected: reviving legacy ear-only endpoints or admitting a transcript. The
  current-world pressure route is already the correct physical boundary.

## Acceptance evidence map

| Fact | Producer | Retained/native transition | Public/UI evidence |
|---|---|---|---|
| Camera light | browser frame | live audiovisual or live-sight retinal occurrence | committed camera evidence |
| Microphone pressure | browser PCM | guided current-world or paired audiovisual cochlear occurrence | committed hearing evidence |
| Rendered glyph light | browser canvas pixels | rendered-light retinal occurrence | mounted visual text record |
| Same organism | authenticated current runtime | one admitted successor generation | unchanged organism identity and advancing generation |

## Exit

Focused source and browser contracts must prove independent microphone capture,
optional paired audiovisual capture, independent camera shutdown, rendered-text
truth, and immediate hearing evidence publication. Deployment then requires the
new backend identity plus the matching live Loom artifact and one current
production ingress observation. A synthetic probe proves transport only; real
camera/microphone hardware remains labeled historical until exercised by an
actual browser device.

## Translation-boundary review before focused proof

- `paired` and `requires_concurrent_camera` exist only at the browser/API
  transport boundary. They select whether simultaneous camera frames accompany
  the pressure; neither enters the native occurrence or chooses cognition.
- Independent microphone JSON contains exactly schema, sample rate, and PCM.
  Paired JSON additionally contains co-captured frames and source provenance.
  Neither form carries transcript, meaning, object, label, or attention.
- Both forms end at existing authenticated physical episode builders and the
  same `_perform_admitted_intake_locked` resident successor path. No second
  organism, state owner, persistence route, or fallback is introduced.
- `_live_hearing_evidence` and `sensory.text` are bounded read-only observation
  facts written only after successful commit; they cannot admit or alter input.
- Camera shutdown aborts an in-flight paired request but does not close the
  microphone. The next bounded window uses the current-world pressure route, so
  a late paired response cannot repaint a closed camera encounter.
- Energy, identity, world state, receptor anatomy, all seven DSF fields, and
  learned state remain owned and settled by their existing native authorities.

## Focused-proof record

- First command invoked `pytest` without the worktree's required project
  `PYTHONPATH`; collection refused with `ModuleNotFoundError: dsf_ai_service`.
  No candidate code executed. Disposition: rerun the identical focused set with
  the project root explicitly on `PYTHONPATH`.
- Corrected invocation reached 14 focused tests: 13 passed; the existing
  audiovisual builder unit fixture lacked the resident eyelid/body-axis input
  its production function now reads and refused before the tested builder law.
  Disposition: mount a neutral exact eyelid transmission in that isolated unit
  fixture; production code is unchanged by this fixture repair.
- The rerun then reached the same fixture's positional-only fake and exposed
  the already-mounted `retinal_transmission` keyword. The fake now accepts that
  existing keyword; again, no production behavior changed.
- Focused backend/source result: **14 passed in 0.79 seconds**.
- Extracted Loom JavaScript passed `node --check`; `git diff --check` passed.
- Focused Chromium invocation did not collect because the shared Python
  environment has no `playwright` package. No page loaded and no browser claim
  is made from that command. Disposition: retain the browser contract test and
  verify the published page through the available live delivery path.

## Production preflight and recurrence controls

- Candidate source identity: `44c03b3f94fff1ace383e3acc202ffa4e940b46a`.
- AWS account/region target: `418384447921`, `us-east-1`.
- ECS target: cluster `tfe-web-cluster`, service `dsf-ai-service-lb`.
- Predecessor: one healthy running task, task definition `dsf-ai-task:1298`,
  image digest
  `sha256:3f18336221bb8fff99458e8b6e9930728ac0dd617ae3b89dd9c6aaf4d6e57660`.
- Predecessor receptor roster: cochlear, touch, interoception,
  chemoreception, vestibular, and world all enabled; current-format migration
  disabled. The candidate must preserve that exact roster.
- Read-only production preflight found desired/running/pending `1/1/0`, one
  healthy task, healthy `/health`, and HTTP 200 for both live Loom pages.

Applicable recurrence register:

| ID | This cutover's prevention |
|---|---|
| RF-001 | Focused Python proof was rerun with exact project `PYTHONPATH=.`. |
| RF-002 | The live receptor roster was read from the predecessor and is passed explicitly to deployment. |
| RF-005 | Evidence is read from the current production service and committed successor, never a stale local artifact. |
| RF-007 | Use the executable repository controller with its explicit `--hot` argument. |
| RF-012 | HTTP health alone is insufficient; verify committed retinal/cochlear ingress and organism continuity. |
| RF-016 | Candidate commit, predecessor task, image digest, identity, and diff are fixed above. |
| RF-023 | AWS inspection selected only the seven non-secret receptor/migration variables. |
| RF-025 | State-changing live probes are never blindly retried after a timeout; read the successor first. |
| RF-029 | Autonomous predecessor advancement is expected; the controller authenticates the current predecessor at cutover. |
| RF-033 | Account, region, cluster, service, and public origin are explicit above. |
| RF-049 | Observer wording is repaired independently; it is not treated as evidence that native readiness or learning exists. |
| RF-056 | Hot cutover must retain identity and may not regress the predecessor tick/generation. |

The production mutation is not started until this record is committed and the
worktree is clean. The first cutover attempt and its outcome will be appended
only after the controller returns; no success is inferred from image creation.

## Hot cutover and live evidence

- One hot attempt started `2026-08-28T18:33:09Z` and completed
  `2026-08-28T18:43:11Z` with status `deployed`; there was no retry or
  rollback.
- Live task definition: `dsf-ai-task:1299`; live source identity:
  `ce964e6e788b2566824f3d7059f539871f0f8e5e`; live image digest:
  `sha256:3530a762b9a243c580b4ba67fa657506ca1413524d69592af5b5598217d05d81`.
- The controller verified the same organism identity and a successor at or
  beyond tick `230890` before pinning the image as production-current.
- The matching `gualaloom.html` was published to `dsf-ai-site`; CloudFront
  invalidation `I20SK1N3TH29VIZGZ8WVCDGRZE` completed. Local and live page
  SHA-256 are both
  `75d96002c450ce689be7822be889d3afc2c09a2e95d7627279e3feb2ae5e4a8e`.
- One bounded two-sample pressure probe used the camera-independent endpoint.
  It committed in the same identity, advanced native tick `231115 -> 231116`,
  and reported 170 sound-lane receptor inputs inside the full current-world
  sensorium. The refreshed public observation immediately reported
  `live_pressure_committed_this_process` and
  `requires_concurrent_camera=false`.
- One synthetic glyph-raster request returned HTTP 504 at the public gateway.
  It was not retried because a state-changing timeout may conceal a committed
  successor. The service remained healthy and autonomous generations advanced,
  but the current public schema has no request-specific rendered-light receipt,
  so this request cannot be classified as committed from observation alone.
- No synthetic frame was sent to the live-camera endpoint: that endpoint treats
  caller-declared `live-camera` provenance as real and would make the public
  observer claim real-device evidence. Current-artifact real camera proof
  therefore remains open until actual browser hardware supplies frames.

Current truth: the live code and page now support independent microphone,
optional co-captured audiovisual input, and glyph pixels without submitting a
string. Independent microphone ingress is live-proven. Rendered-light source
and transport are focused-proofed but its timed-out live request is
indeterminate. Real-camera proof is not claimed from synthetic data.

## Task-1322 live closure — 2026-08-29

This section supersedes only the two indeterminate live-evidence statements
immediately above. It does not reinterpret the earlier timed-out request as a
success.

- Live production remained one organism, identity
  `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`, on task definition
  `dsf-ai-task:1322`, source
  `dc6673af2f2eb70215b1f7e8ac209997b2c74f05`, and image digest
  `sha256:26d7d838d4c14769a44e7d888f3c0e2005ed9e9000bf715f008aebad08b11c08`.
- A headless Chromium instance rendered one capital `A` as a 768x432 PNG. The
  resulting 4,751 pixel bytes had SHA-256
  `34eca5654086e9068b6d35261129a3ab6fbfa4eba6d38a8f79bfe9a2917b5b40`.
  The request submitted only those base64-encoded pixel bytes plus the mounted
  visual-material schema and encoding; it did not submit the character, a
  transcript, a word identity, or meaning.
- That one rendered-light request returned HTTP 200 in 29.895 seconds with
  `accepted=true`. It committed 13 whole-sensorium hops at organism tick
  `259926`, including 108 sight-source inputs, 8,805 physically transitioned
  neurons, 60 complete-neuron-fractal occurrences, and 397 partial-cue
  reassemblies. Its causal-transition receipt is
  `790a899ddee422434a0a712290572594b4ac956bdc6f3d3bb7dac15fa7ffe417`.
  These are physical retinal and organism consequences; they do not prove the
  organism recognized the glyph as the letter `A`.
- Joseph then opened the published Loom camera from a real browser and real
  camera device. The browser visibly reported its bounded four-frame capture
  progressing; production subsequently committed intake
  `live-sight:9bcb882a-5448-4d88-b8aa-d114a5d1303a` at organism tick `259936`.
  The bounded observer reported `committed_in_process=true`,
  `status=live_frames_committed`, 53 frames across three committed batches,
  and a latest four-frame batch sampled at 250 ms through the 27-receptor
  retinal occurrence. No synthetic caller claimed camera provenance.
- Independent live microphone pressure remains proved in this same process by
  exact pressure SHA-256
  `ee379f2b39bba8232fc62be4734efd5a80d6dc342b7f89995165eec8cd17238f`
  and the observer's `committed_in_process=true` record.

**L-007 is live-closed at its stated ingress boundary.** Real camera light,
real microphone pressure, and browser-rendered glyph light have each committed
through the mounted physical sensory lanes of the same resident organism. The
transport supplied no lexical meaning, recognition label, attention, choice,
or scripted cognition. Learned reading, autonomous media selection, and
language use remain later curriculum outcomes rather than hidden claims here.
