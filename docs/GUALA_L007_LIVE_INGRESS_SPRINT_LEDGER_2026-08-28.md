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
