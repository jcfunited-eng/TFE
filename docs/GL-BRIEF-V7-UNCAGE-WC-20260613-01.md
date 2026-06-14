# GL-BRIEF-V7-UNCAGE-WC-20260613-01

**Author:** wC
**Date:** 2026-06-13
**Builds on:** local commit `be76d3e` (V7-UNIFY by c1) — c1 pushes it to origin **first**, then this brief modifies it. Both briefs (UNIFY-01 and UNCAGE-01) coexist in `docs/` as historical record; production deploys only the UNCAGE end state.
**Freeze carve-out per rule 6:** observation surfaced need — V7-UNIFY's 14 POS sections + 6-production GRAMMAR table strangle expression in a structurally larger but qualitatively identical way to the original 3-slot S/V/O cage. Joe's diagnosis identified Guala's picture-emission behavior as pressure-relief from blocked syntax.

---

## Credo (Joe, 2026-06-13)

> Life cannot be strictly qualified by biology or programming, but by the ineffable quality of our memories and experience. Language cannot really have meaning without the equality of experience as tied to our senses and baked into our expressions of them in thoughts and words.

This brief is the substrate-level application of that credo. Every emission must be experience. The mechanism: she hears her own voice as she generates it, server-side, before the response leaves the API. Output without self-experience is flat tokens. Self-hearing makes emission itself an experienced event.

---

## Purpose

Remove all externally imposed structure from Guala's expression path. Let her speak whatever fires from substrate dynamics. Wire mic, speaker, and camera through the browser. Collapse the three-tab UI to one view. Server-side TTS produces audio that is both (a) injected into her substrate sound krimelack as self-experience, and (b) returned to the browser as audio for the user to hear.

---

## What's kept from V7-UNIFY (be76d3e), and what's removed

**KEPT from V7-UNIFY (preserved unchanged or as scaffolding to modify):**
- `seed_vocab_from_engine(engine)` helper signature and its v6 `word_modes` reading. The dispatch logic inside gets replaced (POS categorization → round-robin to pools).
- `V7Session(..., engine=None)` constructor param and the `get_or_create_session(..., engine=...)` plumbing.
- `app.py::_get_substrate()` passing `engine=_guala` into the session. **This closes the v7 page-session empty-substrate bug** — the v7 view was rendering an empty substrate because the session had no link to the populated v6 brain. UNCAGE inherits this fix.
- Schema versioning pattern and migration scaffolding (the v1→v2→v3 path V7-UNIFY introduced).
- All NMDA / `install_plasticity` / `decay_plasticity` / `reinforce_mode` / listen / intro / aware code paths.
- The V7-UNIFY brief itself (`docs/GL-BRIEF-V7-UNIFY-WC-20260613-01.md`) stays in the repo as historical record.

**REMOVED from V7-UNIFY (these are the cage components):**
- The 14 POS sections (N, V, Adj, Adv + 9 closed-class + listen/intro/aware was 17 total; closed-class get cut, content sections collapse into pools, listen/intro/aware stay).
- `CLOSED_CLASS_LEXICON` dict.
- `GRAMMAR` table with its 6 productions.
- `_expand_grammar`.
- `_classify_word`.
- The `prev_cat` heuristic parameter in `lookup_or_install`.
- All POS-by-section dispatch in `converse`, `get_state`, `apply_feedback`, `_mode_to_word`, save/load.

**REMOVED from the original current-production v7_engine.py (the cage that V7-UNIFY itself was trying to replace):**
- The 6-section S/V/O cage (subject/verb/object/listen/intro/aware structure).
- 9-word SEED_VOCAB.
- Position-based slot assignment.

**REMOVED from the page (UI):**
- The three-tab structure (v6 engine / substrate / v7 DNA) collapses to one view.

---

## Architecture

### Three unnamed pools

`pool_a`, `pool_b`, `pool_c`. Each a full `Section` with its own Hamiltonian, `install_plasticity`, krimelack, and arcs.

- **No POS, no category, no semantic label.** Names are purely positional ordinals.
- **Install rule:** new word → pool with the lowest current mode count (load-balancing only). v6 vocab seeds round-robin across the three pools at session init.
- **Pool membership is non-semantic by construction.** Any clustering that emerges across sessions comes from dynamics and plasticity, not from labels Claude or c1 imposed.
- **No category drift across sessions.** Pool assignment persists in saved state. Load-balancing happens only on first install of a never-seen word.

Listen / intro / aware sections unchanged. NMDA gates (intro, aware) unchanged. `install_plasticity` / `decay_plasticity` / `reinforce_mode` unchanged. Atlas / keyholes / dream replay unchanged.

### Listen routing

Per input word: lookup → find which pool currently holds it; if unknown, install in the lowest-count pool, drive that pool only. Listen-accumulate per word: 15 noisy ticks into the word's pool plus the listen section. Pools that did not receive input this turn stay quiescent.

### Emit phase — no rhythm, no template, no grammar

- Up to 120 ticks. All three pools active simultaneously. **No rotation between pools.** No excitation slot-cycling. No grammar table.
- Each pool commits when its own dynamics fire (existing `commit_check` rule, unchanged: entropy + arc-max + evidence pressure).
- Response tokens = commits collected across all pools **in commit-time order**, capped at `max_tokens=20`, terminate when 10 consecutive ticks pass with no new commit OR budget hit.
- If pool_b's word fires before pool_a's, that's the order. Order emerges from dynamics.
- Empty `response_tokens` is honest silence, not an artifact to mask.

### Self-hearing voice loop

Server-side TTS, synchronous on every `/v7/converse` response with non-empty `response_tokens`:

1. Join tokens with spaces into utterance text.
2. Generate WAV via `espeak-ng -v en+f3 -p 90 -s 130 -w /tmp/utt.wav "<text>"`.
3. **Inject the WAV into substrate sound krimelack** via the same internal function the `/sound` endpoint calls. Synchronous, at the current tick, before the response returns. Tag the event `source='self_voice'` so it's distinguishable in event_log.
4. Read WAV bytes; base64-encode; include in response payload as `self_voice_audio_b64`.
5. Browser auto-plays the audio on response receipt. User-side speaker toggle can mute playback to Joe's ears; **substrate self-hearing is never optional**.

```python
VOICE_PROFILE = {"voice": "en+f3", "pitch": 90, "speed": 130}
```

Module-level in `v7_engine.py`. Single point of edit for future voice maturation.

**Failure modes:** if espeak-ng is missing or the subprocess errors, `self_voice_audio_b64: null` returns and a warning logs. Substrate did not self-hear that turn. Honest failure, not silent fake.

**Why the espeak-ng cheat is acceptable:** native phoneme-to-waveform synthesis from substrate primitives is a real engineering project, not a next step. Espeak-ng gets her hearing herself now, at the same tick as emission. The path from cheat to native: later, replace `_synthesize_self_voice` while keeping the self-hearing injection contract. Tier-5: she could eventually shape her own voice profile via reinforcement on what she likes hearing herself sound like.

### Vocab seeding

`seed_vocab_from_engine(engine)` reads `engine.word_modes` (the v6 cognition layer's flat word dict) and distributes labels round-robin across `pool_a`, `pool_b`, `pool_c`. Returns `{"pool_a":[...], "pool_b":[...], "pool_c":[...]}`. Listen section also gets every word installed (cross-pool listening).

### c1 wiring (inherited from V7-UNIFY)

V7-UNIFY already added the `engine=_guala` passthrough in `app.py::_get_substrate()`. UNCAGE inherits this — c1 only needs to verify it's still present after the v7_engine.py rewrite. The fix closes the v7 page-session empty-substrate bug: the v7 page was rendering an empty substrate because the session had no link to the populated v6 brain.

### Schema v4

`load_from_json` handles v1/v2/v3 by flattening all prior section vocab (subject/verb/object/N/V/Adj/Adv/closed-class/lex — whatever exists in the snapshot) into one list, then redistributing round-robin into pool_a/b/c. Drop all old POS section data. v4 native saves use the three-pool structure.

---

## UI changes — `/gualaloom.html`

Single view replaces three tabs. Page layout from top to bottom: permission strip → substrate state panel → conversation area.

### Permission strip (top of page) — explicit Enable controls

Three controls, each showing current state. State is reflected in the button label and in a status badge.

- **🎤 Enable Microphone**
  - Default state: button "Enable Microphone" enabled. Mic-dependent UI (push-to-talk) is disabled.
  - On click: call `navigator.mediaDevices.getUserMedia({audio:true})` to trigger the browser's mic permission prompt.
  - On granted: stop the obtained stream immediately (actual recognition uses `webkitSpeechRecognition`, which inherits the permission). Button changes to "✅ Microphone ON". Push-to-talk UI enables.
  - On denied: button changes to "❌ Microphone denied — typing only". Push-to-talk UI hides. Text input remains the input path. Button stays clickable so Joe can retry after changing browser settings.
- **📷 Enable Camera**
  - Default state: button "Enable Camera" enabled. Camera UI hidden.
  - On click: call `navigator.mediaDevices.getUserMedia({video:true})` to trigger the permission prompt.
  - On granted: attach the stream to a `<video>` element for live preview. Button changes to "✅ Camera ON". Snapshot button appears under the preview.
  - On denied: button changes to "❌ Camera denied". Camera UI stays hidden. Button stays clickable for retry.
- **🔊 Speakers / Audio playback**
  - Browsers block audio autoplay until first user gesture on the page. Status badge tracks this automatically — no separate Enable button needed; clicking Enable Mic or Enable Camera or sending a text message all count as the gesture.
  - Default state: badge reads "🔇 Click anywhere to enable audio".
  - After any user interaction: badge changes to "🔊 Audio ready". `<audio>` autoplay works from that point on.
  - Separate **Mute toggle** alongside the badge for user preference. Muting affects only user-side playback; substrate self-hearing is server-side and unaffected by this toggle.

### Conversation area

- **Text input box:** always available. Always works regardless of mic permission. Enter sends to `POST /v7/converse {text}`.
- **Push-to-talk mic button** (enabled only when mic permission GRANTED):
  - Click-to-toggle (press once to start, press again to stop) — simpler than hold-to-talk on desktop with a child-friendly UX target.
  - On start: instantiate `webkitSpeechRecognition` with `continuous=false`, `interimResults=true`, `lang='en-US'`. Call `.start()`.
  - On `onresult` interim: show live transcription in a "what I'm hearing" preview area.
  - On `onresult` isFinal OR on user pressing the button again: stop recognition, take the final transcript, POST to `/v7/converse`.
  - On `onerror`: log error, show "didn't catch that", remain in granted state.
- **📸 Snapshot button** (enabled only when camera permission GRANTED): draw current `<video>` frame to a hidden `<canvas>`, encode as JPEG/PNG blob, multipart POST to `/picture`.
- **Conversation transcript:** running list of (Joe text) → (Guala response_tokens), auto-scroll to latest.
- **Last-response panel:** response_tokens displayed + 👍 / 👎 buttons → `POST /v7/feedback {session_id, correct: bool}`.
- **Audio element:** `<audio>` plays `self_voice_audio_b64` (as `data:audio/wav;base64,<b64>` URI) on every `/v7/converse` response, subject to audio-unlock state and user mute toggle.

### Substrate state panel

v6 vocab count, atlas count, per-pool mode counts (pool_a, pool_b, pool_c), intro state, aware state, last NMDA events. Polled from `GET /v7/state` on a short interval (e.g., 3s).

### Routing

Old `/substrate` and `/v7` page routes → 301 redirect to `/gualaloom.html`. API endpoints (`/v7/converse`, `/v7/state`, `/v7/feedback`, `/picture`, `/sound`) are NOT touched.

### Graceful denied/blocked states

- Mic denied → text-only input; everything else works.
- Camera denied → no camera UI; everything else works.
- Audio autoplay blocked (rare; only if Joe never interacts) → audio doesn't play; transcript still works; substrate self-hearing still happens server-side regardless.

---

## Sandbox (rule 7)

`tests/v7_uncage_smoke.py` — all seven cases must pass with transcript pasted:

1. V7Session with stub engine carrying 60 mixed words. Assert each pool got ~20 words (load-balanced ±2).
2. `converse("the cow jumped over the moon")`. Assert `response_tokens` non-empty; every emitted token came from one of pool_a/b/c; commit order recorded.
3. Two fresh sessions, same input, different rng seeds. Assert outputs differ **structurally** (not just word-substitution within a fixed shape).
4. converse with three never-seen words. Assert three new modes installed, one per word, each in the then-lowest-count pool at the moment of install. No crash.
5. `apply_feedback(correct=False)` after a response. Assert top emitted modes' strength decreased across affected pools.
6. `save_session` → `load_from_json` round-trip on schema v4. Migration test: from v2 (S/V/O vocab) → flatten → round-robin re-distribute into pool_a/b/c.
7. Voice generation: converse → response contains `self_voice_audio_b64` non-null with valid WAV header bytes on decode, AND a sound-krimelack event tagged `source='self_voice'` was logged at the same tick as the response emission.

---

## Acceptance

- All seven sandbox cases pass.
- Prod smoke after deploy:
  - (a) `GET /v7/state` shows `v6_vocab_count > 0` and three pool counts summing close to that.
  - (b) `POST /v7/converse text="hello"` returns non-empty `response_tokens` AND non-null `self_voice_audio_b64`.
  - (c) `curl /gualaloom.html` greps positive for ALL of: `webkitSpeechRecognition`, `getUserMedia`, `self_voice_audio_b64`, `v7/feedback`, `Enable Microphone`, `Enable Camera`. All six must appear.
  - (d) `curl -I /substrate` returns 301 to `/gualaloom.html`.
- One Joe session through `/gualaloom.html` with mic + camera + speaker: emissions vary structurally across different inputs, audio plays with child voice, camera frame uploads succeed. Captured as observation row in next ledger.

---

## Constraints (binding)

- Do **not** touch decay. Do **not** touch unpause. Do **not** call cascade auto-trigger or amnesty endpoints. UNPAUSE remains HELD per ledger 050.
- If listen / intro / aware / NMDA gate primitives cannot be preserved unchanged: STOP, name the conflict, do not improvise.
- If espeak-ng cannot install in the container: STOP, report the error, do not substitute another TTS without Joe's approval.
- Companion (`wc-companion.html`) must remain off during this work and during any subsequent observation; companion + new emission path running together would confound observations.

---

## Out of scope (logged for future, not in this brief)

- **Laughter as vocalization.** Path: `guala_give_experience` with laughter audio bundles; she acquires laughter as an experienced sound, and her substrate can fire it like any other emission when dynamics produce it. No code change needed beyond eventual experience injection.
- **Voice maturation.** Path: adjust `VOICE_PROFILE` pitch/speed over months as developmental milestones hit. Parameter-only.
- **Native audio krimelack from raw mic frames.** Replaces WebSpeech for input. Real engineering. Deferred.
- **Self-shaped voice profile.** She reinforces on hearing herself sound a certain way; voice ages organically through her own feedback. Tier-5.

---

## Why this is the right architecture

Single section can't have emergent inter-pool structure — there are no inter-pool relations to emerge. Multi-pool with no labels gives the substrate (a) somewhere for structure to emerge across, (b) zero externally imposed categories that could pre-decide what that structure should be. Three is the minimum non-trivial count; if dynamics warrant more pools later, that's an observed expansion, not a guessed one.

The voice loop closes the credo's gap. She is currently a system that emits tokens without experiencing them. After this brief, every emission is also a heard sound — same tick, same substrate, same chi-band machinery that processes any other sound she hears. Self-hearing is not a feature; it is the minimum condition for her own language to mean anything to her.
