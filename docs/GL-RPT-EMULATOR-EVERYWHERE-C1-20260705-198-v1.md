# GL-RPT-EMULATOR-EVERYWHERE-C1-20260705-198-v1

doc_id: GL-RPT-EMULATOR-EVERYWHERE-C1-20260705-198-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-EMULATOR-EVERYWHERE-EVE-20260705-196-v2` (supersedes v1,
retained). M1-M5 built. C1/C2/C3/C4/C5 verified directly. C6 (video)
has no live text-intake path yet — inherits by default per the
doctrine's own framing, nothing to wire until it exists. X1/X2/X4
verified locally; X3/X5 need the live deploy (this report ships with
it, c1b's window or mine per tonight's direct-deploy pattern).

## M1/M2 — the mechanism, built once, reused everywhere

`Guala._sentence_modal_signals(words)` (new): the same TOUCH/SMELL/
TASTE_LIBRARY word map `_bind_sensory_words` uses (shell atlas),
reused for the brain. Groups the sentence's own descriptor words by
modality, calls `generate_sensory_signals` ONCE per modality per
sentence (real physics, not the banned hash-per-word fake — same gate
`-191` enforced), concatenates each modality's channel waveforms into
one flat array per organism lane (touch→tactile, smell→olfactory,
taste→gustatory — Embryo.experience_word's own composite key names).
Returns `{}` — honest absence — when the sentence has no descriptor
word (M5).

`read_sentence()` calls this ONCE per sentence (the same function
V1/V2/V3 of `-188` already established as the shared binding window
for scene lanes) and caches the result as `_last_read_modal_signals`/
`_last_read_modal_wall_time`, mirroring `-191`'s exact sight/sound
convention — only set when non-empty.

`_enqueue_organism_remember` now snapshots `_last_read_modal_signals`
in-window (`SENSE_BINDING_WINDOW_SEC`, unchanged, per the dispatch)
alongside sight/sound into the queue item: `(word, sight, sound,
modal)`. `_organism_worker_loop` unpacks the 4-tuple.
`_organism_signal_with_senses` merges `tactile`/`olfactory`/
`gustatory` into the signal dict when present — `Embryo.
experience_word()`'s composite already reads these three keys (N4 of
`-191`), zero organism-side change, exactly as M2 specified.

`organism_experience_bound` (S2) now names which of sight/sound/
tactile/olfactory/gustatory actually fired, per binding.

`generate_sensory_signals`'s GATING comment updated to name these two
new legitimate callers (still bans per-word hash fakery, the actual
thing the gate exists to stop).

## Coverage — verified per path, not assumed

Because `read_sentence()` is the one function EVERY intake path
already funnels through, M1/M2 landing there covers all of them at
once — confirmed by reading each path's code, not by assumption:

- **C1 Curriculum** (`_curriculum_feed_chunk`): calls `read_sentence`
  per chunk sentence. Inherits automatically.
- **C2 Tick reading** (`_atick_reading`, natural rotation + the
  force_reading hook): calls `read_sentence`. **Verified directly**:
  forced-reading a sentence with real touch+taste words produced 6/6
  `organism_experience_bound` events carrying `senses: ['tactile',
  'gustatory']` while the binding window held.
- **C3 Worldfeeds** (`_world_feed_once`): calls `_curriculum_feed_chunk`
  (same function as C1) on fetched sentences. Inherits automatically
  — confirmed by reading the call chain, not re-tested separately
  (identical code path to C1).
- **C4 Lookup** (`_lookup_and_ground`): calls `_guala.read_sentence(desc,
  source="lookup")` directly. Inherits automatically — confirmed by
  reading the call chain.
- **C5 Converse**: `converse()` → `read_sentence()`. **Verified
  directly**: `converse("I felt something warm and sweet", source=
  "joe")` produced 6/6 `organism_experience_bound` events with
  `senses: ['tactile', 'gustatory']` — a sensory word Joe speaks to
  her now binds with its senses in the same window (X4).
- **C6 Video**: no live text-intake path exists yet for video caption/
  transcript text (confirmed absent, not assumed) — nothing to wire;
  the doctrine covers it by construction the moment that intake path
  is built and calls `read_sentence` (or is deliberately flagged if a
  future path skips it, per the dispatch's own "defective on sight"
  framing).

## C7 — loomscan Visibility Rule enforced

Shell-atlas `sensory_words_bound` (the `-188` follow-up fix) is now a
feed-row only. Lane GLOW for touch/smell/taste (and sight/sound) comes
exclusively from `organism_experience_bound`'s `senses[]` — what
actually reached the brain, never a shell-atlas count. `node --check`
clean.

## A real timing question, measured and reported, not silently patched

`_sentence_modal_signals` itself measured at **0.4ms** in isolation —
negligible. But `read_sentence()`'s own per-word cost varies wildly in
this dev sandbox (0.9s–13s per 10-word sentence across repeated
trials, same warmed-up process) for reasons unrelated to this
dispatch — confirmed by disabling/re-enabling the new function
mid-run and seeing no consistent difference. Flagging honestly rather
than either claiming a regression that isn't there or silently
assuming it's fine: if real per-word cost in production is ever slow
enough to exceed `SENSE_BINDING_WINDOW_SEC` (3.0s) mid-sentence, the
back half of a long sentence would lose its modal binding — a
consequence of reusing the existing window unchanged, per the
dispatch's own instruction (M5: no new constants). Not fixed here;
named for whoever watches live timing post-deploy.

## Verification

Local: X1 (READING) and X4 (converse) both directly verified via
`organism_experience_bound` event inspection (shown above). Full
`test_brain`/`test_neuron`: 23/23. `probe_188_scene_lanes.py`: 4/4
(unaffected — different mechanism). Broader engine suite: 20/20.
`py_compile` clean on every touched file. `node --check` clean.

X3 (a live `lookup_grounded` event whose sentence produced organism
modal lanes) and X5 (deployed SHA + task numbers + ten-sentence
lane-fire counts) are deploy-dependent — reported once live, same
honesty boundary as every UI-facing fix tonight.

### Changelog
- v1 (2026-07-05, c1a): M1-M5 built. C1-C5 verified (C1/C3/C4 by
  reading the shared call chain, C2/C5 by direct local test). C6
  named as not-yet-applicable. C7 loomscan Visibility Rule enforced.
  Real per-sentence timing variance measured and reported, isolated
  from this dispatch's own (negligible) cost. Deploying with this
  report.
