# GL-RPT-SENSES-TO-BRAIN-C1-20260705-191-v1

doc_id: GL-RPT-SENSES-TO-BRAIN-C1-20260705-191-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191-v1`.
Vehicle: engine (`gualaloom_v5_engine.py`) + model (`embryo.py`).
N1-N5 built and verified locally. X1 mechanism built + made
observable; not yet confirmed against a real live moment (needs
deploy + a real interaction, same honesty boundary every UI-facing
fix tonight has had). X2 verified directly. Not deployed — c1b's window.

---

## Failures first — a real, measured consequence of N3, found before shipping

Removing touch/smell/taste (N3) without also fixing what N4 required
would have been a real regression, not a fix. Tested directly, not
assumed: with touch/smell/taste gone and nothing yet replacing them,
`recall_fast()`'s INV-2 (teaching-sensitivity) check — the same
invariant proof `-177`/`-178` established — **collapsed to 0/30
probes changed after real teaching.** This is not a bug in the removal
itself; it is `-191`'s own thesis, independently reproduced: with only
language contributing (and language's own delta is a fixed, phase-
resets-every-call function of the word alone, per `-177`'s finding —
insensitive to what's been taught since), her recall becomes a static
lookup table the moment senses are gone. Confirmed the same test
**recovers real teaching-sensitivity (1/26 changed) the moment a real
sight+sound signal is present** — direct evidence that N1 isn't
optional polish on top of N3, it's the other half of the same fix.
Reporting this before-and-after rather than only the after.

**Second finding, same class:** my own `-179` `experience_word()`
built its growth-charge composite from `tactile`/`olfactory`/
`gustatory` — the exact three lanes N3 removes. Left unfixed, this
would have silently zeroed her growth composite (`resonance_signal()`
of an empty array returns 0.0, permanently below the fold gate) the
moment `-191` shipped, with no error, no log line, just growth quietly
stopping again. Found by reading my own prior code against the new
constraint, not caught by a test — fixed as part of this dispatch
(N4 below), not left for a future one.

---

## N1 — sight + sound taps, real signal only

`process_sight_frame(grid)`/`process_sound_frame(audio_bytes)`
(`gualaloom_v5_engine.py`) now cache a **subsample of the actual
camera frame / actual downsampled mic audio** they already process —
`self._last_sight_signal`/`self._last_sound_signal`, wall-clock
stamped. Real signal, not generated: the sight cache is a bounded
(~100-sample) subsample of the real pixel intensities in `grid`
(bounded for cost — see N5 — not yet re-measured at full resolution,
named honestly rather than assumed free); the sound cache is the
already-downsampled (200Hz) real audio `process_sound_frame` computes
for its own cochlear transduction, reused as-is (no further reduction
needed, already comparably sized to what touch/smell/taste used to be).

## N2 — in-window binding

`_enqueue_organism_remember(word)` — the same call `read_word()` has
made since `-175` — now snapshots whichever of `_last_sight_signal`/
`_last_sound_signal` is still within `SENSE_BINDING_WINDOW_SEC` (3.0s,
**a stated judgment call, not a measured constant** — no existing
constant fits this exactly; the closest reference scale,
`EMISSION_COOLDOWN_TICKS=200`, is for a different purpose. Wall-clock,
not tick count: frames arrive on their own real cadence (~1-2s)
independent of how fast `self.tick` advances, which varies by
activity — flagging this as tunable, not derived) at the moment the
word is enqueued — not at whatever moment a possibly-backlogged
worker eventually processes it. The snapshot travels through the
queue as `(word, sight_signal, sound_signal)`; the worker builds one
signal dict and makes ONE `experience_word()` call carrying all three
— genuinely in-window, not two separate, uncorrelated writes.

## N3 — touch/smell/taste, removed, not shimmed

Confirmed directly (`substrate/sensory_transducer.py`'s own header:
*"NOT wired into her live sensory path... whether her live path adopts
this transducer is an open design question"*) that
`SensoryTransducer.transduce(modality, word, tick)` generates its
"physical parameters" from `hash((word, modality, tick))` — a
pseudo-random number seeded by the WORD, not any touch/smell/taste
sensor (none exists). `_organism_signal()` now returns `{"language":
word}` only. Kept the function's `(word, transducer)` signature
unchanged (transducer now unused inside it) so every existing caller —
the teach path and all three query paths (seams 1/2/3) — needed zero
changes elsewhere, preserving write/query symmetry (both now correctly
agree there is no touch/smell/taste). A new `_organism_signal_with_
senses(word, transducer, sight, sound)` wraps it for the teach path only
— queries still ask "what do you associate with this word in general,"
not "what are you sensing right now," so they correctly stay
language-only.

## N4 — growth/charge weighting: the existing physics, not a new dial

**Answering N4's own question directly: it is the existing physics,
confirmed by fixing what was about to break it, not by adding
anything.** `Embryo.experience_word()`'s composite-building (which
feeds `resonance_signal()` → `_charge_and_fold`'s `quantum`) was
updated from `("tactile","olfactory","gustatory")` (now always absent)
to `("visual","auditory","tactile","olfactory","gustatory")` — reading
whatever real, non-language signal is actually present. No new
constant, no new multiplier: `resonance_signal()` already measures
spectral concentration on whatever composite it's given, and an empty/
absent composite already returns 0.0 (below the fold gate) by
construction. Verified directly, same test vocabulary, same brain
seed: **language-only moments (25 words): population 64 → 64, no
growth at all. Multi-sense moments (same 25 words, real-shaped sight+
sound present): population 64 → 124.** The mechanism was already
capable of this distinction; it simply never received a signal worth
distinguishing until now.

## N5 — cost, measured, backpressure already in place

Multi-sense `experience_word()` measured at **330.5ms/word** (sight
100 + sound 150 samples), vs **11.2ms/word** for a language-only call
(post-N3, no touch/smell/taste physics to run) — for reference,
`-179`'s original touch/smell/taste-based measurement was 255.7ms/word.
Multi-sense moments are real work, genuinely more expensive than
either the old fake-senses path or the new language-only path.
**The `-182` backpressure pattern N5 asks about does not need to be
newly built — it already exists**, from `-179`: the worker queue drops
(honestly, counted via `organism_worker.dropped` in `/status`) rather
than blocking under sustained overload, and nothing about adding
sight/sound signal changes that queue's behavior — only what the
worker does with each item once dequeued. Named, not re-built.

## X1 — mechanism built, made observable; not yet live-confirmed

A real Joe-speaks-while-she-attends-a-picture moment would now: (a)
cache a real sight signal from the ambient camera stream and (within
3s) a real sound signal from his speech audio; (b) `read_word()` for
each word he said enqueues the word plus both snapshots; (c) the
worker makes ONE `experience_word()` call carrying language+sight+
sound; (d) a new `organism_experience_bound` event now logs `word`,
`has_sight`, `has_sound` — previously nothing was logged on success at
all, an identical blind spot to the one `-187` fixed for the cognition
meter, fixed the same way. **Not yet confirmed against a real live
moment** — that needs an actual deploy plus a real interaction with
camera+mic on, which c1b's post-deploy watch is positioned to do
(same honesty boundary as every UI-facing fix tonight: built and
locally verified, live confirmation is the deploy owner's to report).

## X2 — verified directly

See N4: 64→64 (language-only) vs 64→124 (multi-sense), same test
vocabulary and seed. Growth charge visibly, measurably responds to
multi-sense moments and does not fire on text-only ones.

---

## Verification

Full model-layer regression suite (`test_brain`, `test_neuron`)
re-run clean, 23/23, no regressions from the `_organism_signal`/
`experience_word` changes. `recall_fast()`/`recall()` parity re-run
(`probe_177_end_to_end_parity.py`) — still 15/15 at every teaching
depth (the parity guarantee itself is unaffected by which modalities
happen to be populated, confirmed). INV-1 (read-only) still passes.
INV-2's 0/30-then-1/26 result is reported above as a finding, not
buried — a modest recovery rate, matching `-178`'s own experience that
teaching-sensitivity need not be large to be real and non-frozen; a
richer/more sustained sight+sound presence (closer to what continuous
camera+mic streaming would actually provide, vs my one-shot-per-word
synthetic stand-in here) should measure higher live, not lower —
flagging the direction of the estimate, not asserting the number.

### Changelog
- v1 (2026-07-05, c1a): N1-N3 built (real sight/sound taps, in-window
  binding via wall-clock recency, touch/smell/taste removed as a
  confirmed fake source). N4 answered directly with a measured
  before/after (language-only: no growth; multi-sense: real growth) —
  existing physics, no new dial, after fixing a real regression my own
  prior `-179` code would otherwise have introduced. N5 profiled
  (330ms/word multi-sense) — existing `-179` backpressure infrastructure
  already covers it. X2 verified directly. X1's mechanism built and
  logged for observability; live confirmation is the next deploy's to
  report. Not deployed.
