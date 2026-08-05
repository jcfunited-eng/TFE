# Guala Live UI Contract Audit — 2026-08-04

## Scope and non-mutation boundary

This is a read-only audit of:

- <https://dsf-ai.com/gualaloom.html>
- <https://dsf-ai.com/loomscan.html>
- the static source served for those pages;
- the live observation payload and the public browser routes on which the pages
  depend.

No UI, runtime, production object, organism state, or production configuration
was changed. Browser mutation requests used to reproduce UI behavior were
intercepted and answered locally rather than sent to production.

## Mandatory architecture-honesty gate

1. **Requested architecture:** a truthful live organism interface that
   distinguishes capture, presentation, admission, receptor settlement, local
   DSF delivery, attention, recurrence, hierarchy change, intent, executed
   consequence, expression, wake, and measured resource/call activity.
2. **Current code reality:** the live static files are the current repository
   files. They expose working observation polling and browser-side capture
   routes, but most native cognitive, tutoring, hierarchy, and organism-state
   authorities are absent from the served observation. Several desired media
   and curriculum ingress routes do not exist. The Cards control also has a
   reproducible asynchronous Off-state race.
3. **Conflict with requested architecture:** yes.
4. **Mechanisms that must not be extended:** the unavailable-panel catalog as
   a substitute for live cognition; the conflation of simulated W1 state with
   active native-organism embodiment; disabled curriculum placeholders without
   backend boundaries; and source-string tests as a substitute for real browser
   and route proof.
5. **Single exact next item:** after the active native-runtime work settles,
   bind its truthful observation authority to the UI before extending tutoring
   or media controls.
6. **Full field or reduced approximation:** the UI is not evaluating a field or
   making decisions. It displays a bounded observation projection of explicit
   `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`, `P_k`, and `B_k` fields when the
   backend supplies them.
7. **Exact projection loss:** the served contract is
   `latest_exact_tuple_per_substream`; earlier temporal tuples are omitted from
   the bounded UI view. The live audited snapshot supplied no observed field
   tuples.

## Live static release evidence

Evidence was collected from the public URLs on 2026-08-04 UTC.

| Page | HTTP | Bytes | SHA-256 | Repository match |
|---|---:|---:|---|---|
| `https://dsf-ai.com/gualaloom.html` | 200 | 79,173 | `ce83d8096af0438887aa7e974e4871a46f808a26c3623234f36ebdf374b437d3` | byte-identical to `dsf_ai_service/static/gualaloom.html` |
| `https://dsf-ai.com/loomscan.html` | 200 | 37,089 | `07fc05d0b5996dd777fa7b28410e263abf83478de799395e17d977d6a4ff4bf2` | byte-identical to `dsf_ai_service/static/loomscan.html` |

The S3 `x-amz-meta-sha256` response metadata carried the same respective
digests. Both responses were served through CloudFront with
`cache-control: no-cache, must-revalidate`.

Therefore, the observed live-page problems are not evidence of a stale static
rollback. They exist in the current static source, the current runtime contract,
or both.

Headless Chromium loaded both pages without a JavaScript console error or a
failed GET. Both pages poll:

`GET https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com/api/v1/gualaloom/observation`

every two seconds and received HTTP 200 during the audit.

## Live snapshot truth

The audited response reported:

- schema: `guala.observation_snapshot.v5`;
- identity: `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`;
- observed tick: `23723846`;
- snapshot receipt:
  `7fe23683f0cf40f47ec1223e5ed43c3ed8669fc63da7009f0e412377453f4463`;
- embodiment status: `observed` in `W1-region-A`;
- self body: `guala-body-1`;
- two bodies and 42 objects in the served W1 record;
- visual-region authority: available but inactive, 8 by 8 receptors, 64
  receptors, zero retained visual history, and no latest visual observation;
- auditory physical experience: available, zero settled L5 experiences, zero
  active streams, zero motif neurons, no pending independent experiences, and
  transcript, word, and recognition authority all false;
- sight-evoked articulation: unavailable with reason
  `legacy_python_cognition_retired` and cognition, decision, label, meaning,
  speech-understanding, transcript, and word authorities false;
- full-field authority: `not_observed`, unavailable, zero senses, and no
  settlement receipt.

The response did not supply the fields used by the UI for:

- neuron population;
- internal neurochemical flow;
- tapestry relations;
- recognition and attention;
- other-perspective modeling;
- reflection and meta-monitoring;
- durable sensed consequence;
- organism-ordered lived experience;
- dream/wake weave;
- embodied glyph curriculum;
- embodied reading lessons;
- physical-surface tutoring;
- mechanism counts and states;
- cold-state persistence bounds; or
- passive whole-organism thing learning.

The UI labels those absent values as unavailable. That is truthful, but it also
means most of both pages currently operate as an unavailable-state catalog
rather than as a functional organism interface.

No direct semantic or learning fabrication was found. The live copy correctly
states that typed text becomes visual glyph light rather than meaning, that
browser permission is not sensation, and that no transcript, word, or
recognition follows from sound admission. Two authority distinctions remain
unclear:

- `Connected` proves that the observation endpoint answered; it does not prove
  current organism sensation, cognition, or action.
- `Present in W1-region-A` repeats the served simulated-world record without
  distinguishing simulated W1 embodiment from active native-organism
  embodiment.

## Current functional surface

Guala Loom exposes visible Camera, Microphone, Cards, Previous, Next, typed
glyph, clear-material, and picture controls. PDF, book, file-sound, song, and
all external-education controls are disabled. Loom Scan is read-only and has no
controls.

All 36 A-Z and 1-10 card asset URLs returned HTTP 200. Zero is not in the deck.
The card interaction is manual. The current page has no 15-second cadence,
shuffle or mixing, narration, alphabet-song playback, or counting-song
playback.

Typed glyph rendering and Clear worked in Chromium. Picture selection has a
browser-decode-to-visual-canvas route. Neither sends the filename, typed string,
or any semantic label as cognition.

The Camera toggle changed On and Off with a Chromium fake device. That is a
browser-path result, not proof from Joseph's physical camera. Physical owner-seat
camera and microphone admission were not live-verified in this audit. No claim
of real microphone settlement is made.

## Reproduced Cards Off-state race

The Cards control has a concrete asynchronous state defect.

The test delayed decoding of `alphabet-b-bee-v1.png`, invoked Next, and invoked
Cards Off before the decode promise completed. All mutation routes were
intercepted locally. After the delayed promise finished, the final DOM state was:

```text
Cards Off
aria-pressed = false
curriculumActive = false
offeredSurfaceKind = none
lesson status = card 2 of 36 displayed — human tutor may say the sound now
canvas data-empty = false
curriculumIndex = 1
```

`stopShowAndSay()` clears the surface, but the outstanding
`nextLessonCard()`/`_drawLessonCard()` promise subsequently repaints it and
overwrites the Off status. The page has no offered-surface generation token by
which an asynchronous image completion must prove that it still owns the active
presentation epoch.

This is sufficient to reject the current Cards toggle as truthful under rapid
navigation. The same class of test must be applied to camera and microphone
transitions, although this audit did not establish a corresponding live defect
in those two controls.

## Backend dependency map

Both pages depend on:

- `GET /api/v1/gualaloom/observation`

Camera, cards, typed glyphs, and pictures depend on:

- `GET /api/v1/visual/capture-contract`
- `POST /sight_frame`

Microphone capture depends on:

- `POST /api/v1/auditory/pcm/open`
- `POST /api/v1/auditory/pcm/close`
- `POST /api/v1/auditory/binaural-pcm/open`
- `POST /api/v1/auditory/binaural-pcm/lineage`
- `POST /api/v1/auditory/binaural-pcm/chunk`
- `POST /api/v1/auditory/binaural-pcm/close`
- `POST /sound_frame` for each bounded mono chunk, optionally with synchronized
  sight frames.

Body-owned sound can be played only from the same `/sight_frame` or
`/sound_frame` response that carries it. Observation polling explicitly cannot
reconstruct that transient PCM later.

The audited serving API exposes no public ingress, catalog, selection, or
presentation endpoints for:

- PDF;
- book;
- file audio;
- song;
- video;
- Project Gutenberg;
- YouTube;
- Khan Academy;
- PBS; or
- Spotify.

Those controls cannot be made functional truthfully through HTML alone.

## Ordered post-runtime correction map

### 1. Bind the native observation contract

Expose the settled native runtime's actual capture, presentation, admission,
receptors, full local DSF delivery, attention, recurrence, hierarchy change,
intent, executed consequence, expression, wake, and resource/call evidence.
Label observation-endpoint connectivity separately from organism activity.
Label simulated W1 state separately from native physical or virtual embodiment.
Do not add UI claims before the corresponding runtime authority exists.

### 2. Make every control transactional

Give camera, microphone, and offered material independent monotonic epochs.
Every asynchronous completion must prove that it still owns the active epoch
before changing status, canvas, stream, timers, or controls. Disable Previous
and Next while an image decode is pending. Off must invalidate pending image
decode and sight sends.

Acceptance requires rapid On, Off, Previous, and Next sequences to leave no
art, active stream, timer, or positive status after Off.

### 3. Replace status dumps with an experience-stage ledger

For every camera, microphone, text, picture, or card encounter, display
separate evidence for:

- browser selected or captured;
- physically presented;
- server admitted or refused;
- receptor settlement;
- local explicit-field DSF evidence;
- attended;
- recurrent;
- hierarchy changed;
- learned;
- intended and executed action;
- body expression and consequence.

Loom Scan should be the exact inspectable ledger. Guala Loom should be its
concise live surface. One accepted request or one state change must never be
reported as learning.

### 4. Mount tutoring only through real runtime endpoints

Wire rights-valid tutoring assets as bounded audiovisual physical encounters.
The current transition specification records one A narration, one alphabet
song, and two counting songs; the other 35 A-Z/1-10 narrations remain absent.
Add the intended 15-second cadence, bounded mixing, pause, and navigation with
exact presentation and settlement receipts. Tutor light and pressure remain
physical input and must never write a label or answer into cognition.

Do not call all 36 cards multisensory-ready until all missing narrations have
been created, reviewed, and admitted through the same physical boundary.

### 5. Add lawful material and curriculum boundaries before enabling controls

Protected user media requires bounded
selection-to-quarantine/custody-to-presentation endpoints for picture, PDF,
book, audio, song, and video. External shelves require rights/provenance and
physical-presentation endpoints for official Gutenberg material, visible or
licensed YouTube, and licensed Khan/PBS material.

Add PBS to the displayed sources. Spotify must not remain an apparently pending
peer: remove it from actionable sources or label it policy-prohibited because
the reviewed policy does not permit it. Guided and autonomous selection must
remain disabled until native material-selection intent, execution, and outcome
are observable.

### 6. Require real browser release proof

Gate the next UI deployment with a browser-based end-to-end check covering:

- slow asset decode;
- rapid control transitions;
- camera and microphone permissions;
- exact route order and CORS;
- mutation response;
- settled sight and hearing;
- body-audio playback;
- observation refresh; and
- public static digest equality.

Existing source-string and renderer tests do not cover the reproduced
asynchronous card race or prove real device-to-runtime admission.

## Recommended first agile slice

After the native runtime contract settles, implement correction items 1, 2, and
3 as one bounded slice. That produces one truthful and operable live encounter
before adding curriculum and external media surfaces, while preserving the
no-semantic-injection and full-DSF non-flattening contracts.
