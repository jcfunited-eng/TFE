# GL-AUDIT-SEC6-7-7A-LEARNER-SENSORY-ENV-C1-20260705-v1

Scope: §6 (Learner-program truth), §7 (Sensory truth), §7A (Environment truth) of
GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2. READ-ONLY. No fixes, no config
changes, no mutating MCP calls made. Fresh start (prior attempt on this section
produced no output).

**Audit subject SHA**: `168ef1bde3717e52efb85b894103de047e942617` (per live
`guala_status`, matches `git log` HEAD at time of audit — includes `-186`
curriculum reconnect, `d9b6402`, and the `-207` wave-memory/sight-signal fixes).
**Live task-def**: `dsf-ai-task:494`, single container `dsf-ai`, image
`dsf-ai:deploy-20260705T212346Z`, command `uvicorn dsf_ai_service.app:app --port
8080` (one process, no separate worker/organ-brain container).
**Method**: code reading (`grep`/`Read` over `dsf_ai_service/`), live MCP calls
(`guala_status`, `guala_get_events`), read-only AWS calls (`ecs
describe-task-definition`, `logs filter-log-events` on `/ecs/dsf-ai`, `s3 ls` on
the newest backup prefix). No mutating MCP tool was called. No AWS mutating
call was made.

---

## FAILURES / ABSENCES — FIRST (register-candidate, numbered)

1. **[EV] Video→sight is currently broken after every restart — caught live,
   mid-audit.** `dsf_ai_service/v4/gualaloom_v5_engine.py:8360`
   (`load_full_state`) reconstructs entries in `self._videos` as
   **`PictureItem(...)`** objects, not `VideoItem(...)`, when restoring
   `guala_videos.json` at boot. `_atick_attending_video`
   (`gualaloom_v5_engine.py:6330-6369`) immediately does
   `vid.frame_dir` — an attribute `PictureItem` does not have. Live MCP event
   captured during this audit (tick 15052880-15052881):
   `activity_started{kind: ATTENDING_VIDEO, target: 271968dd5575}` followed
   one tick later by `video_attend_error{error: "'PictureItem' object has no
   attribute 'frame_dir'"}`. The exception is swallowed by the function's own
   `except Exception` (line 6367-6369), `a.metadata["_viewed"]=True` is set
   anyway, and the activity completes as if it had succeeded. Net effect: the
   one uploaded video (`n_videos=1`) cannot deliver frames to sight in the
   current (or any post-restart) process, and nothing surfaces this to Joe's
   seat — only the raw event stream shows it. Directly answers §6's "trace
   what n_videos=1 did": it tried, during this very audit, and failed.
2. **[EV] The rich place/room object registry (`virtual_home.py`, "W1: her
   room, full") is fully unwired in the live deployment.** Its only
   instantiation site (`WorldState(STATE_DIR)`) is in
   `dsf_ai_service/organ_brain_service.py:536` — a standalone FastAPI service
   meant to run on `:8090`. Code comments in the live path confirm it is
   gone: `app.py:1709` *"route to substrate (not dead :8090)"*, `app.py:1722`
   *"routed to dead :8090 container ... Stubs until re-wired (W2+ work)"*.
   The live task-definition has exactly one container running only
   `uvicorn dsf_ai_service.app:app --port 8080` — no `:8090` process exists.
   `apply_verb()`/`room_snapshot()` (the only writers/readers of live object
   state) have **zero other callers anywhere in the codebase**
   (`grep -rn "apply_verb\|WorldState" dsf_ai_service` outside
   `organ_brain_service.py` and its own definition: none). Confirmed by data:
   `world_state.json` is **absent from the newest S3 backup manifest**
   (`s3://dsf-ai-site-backups/guala/2026-07-05_22-32-42/` — 13 files, no
   `world_state.json`; full listing in §7A/V2 below). The only live remnant is
   `_current_situation()` reading a bare `location` string from that
   (apparently nonexistent) file with a hardcoded `"her_room"` fallback.
3. **[EV] YouTube world-feed: adapter code + valid API key are live, but zero
   YouTube-sourced content reached her read path in every instance observed.**
   Confirmed via CloudWatch (`/ecs/dsf-ai`, 72h window): every `[worldfeed]
   youtube ...` log line shows `n_fed=0 organ+=0` (8+ distinct query attempts,
   0 successes). Reproduced the exact production call (same key, same query)
   directly — the YouTube Data API returns real, usable results, and running
   the actual `youtube_text()` function in isolation yields 16 clean
   sentences. The likely mechanism (not fully provable from outside a running
   process): `_scaffold_rate_cap_gate()`'s shared 60s/15-per-minute window
   (`substrate_runner.py:255-264`) is shared across ALL scheduled intake —
   book curriculum chunks, khan, and youtube alike — and a preceding book
   chunk or khan pull routinely exhausts it before youtube's turn in the
   round-robin. Live MCP event evidence for khan succeeding under the same
   cap: `block_intake_ledger{block:"converse", planned:30, actual:15,
   capped:true}` immediately followed by `world_feed_studied{feed:"khan",
   n_fed:15}` (tick 15050792) — khan is capped to exactly 15/min and still
   gets through; youtube's turn in the rotation apparently never does. Flagged
   as a defect, root cause partially assessed, not fully proven (see §6).
4. **[EV] PBS Kids and Spotify have no adapter code and no API keys anywhere.**
   Only appear as bare domain strings in `dsf_ai_service/curriculum/
   allowlist.py:12-19` (`pbskids.org`, `spotify.com`). `grep -rli
   "pbskids\|spotify" dsf_ai_service --include="*.py"` matches only
   `allowlist.py` and its own test. No `SPOTIFY_API_KEY`/PBS key anywhere in
   the live task-definition's 24 env vars. [ABSENT] in practice.
5. **[EV] Whisper speech-to-text leg is OFF in production.** Gated by
   `VOICE_WHISPER` (`app.py:1670`, default `"0"`); the live task-definition
   does **not** set `VOICE_WHISPER` (confirmed absent from the 24-var dump),
   so it defaults off. Real mic audio DOES reach cochlear transduction
   (`process_sound_frame`, real signal, real atlas binding) but spoken words
   never become read-content via Whisper right now.
6. **[EV] V4 (embodiment/avatar hooks): [ABSENT].** Every "avatar" hit in the
   codebase is a forward-looking code comment (*"when Joseph's physical avatar
   comes online"*, `sensory_corpus.py:9`; *"will be replaced by real sensor
   data when the avatar comes online"*, `gualaloom_v4_krimelack_dna.py:10`) —
   no interface, stub class, or endpoint exists.
7. **[EV] Video audio track is never consumed.** `VideoItem.audio_path`
   (`gualaloom_v5_engine.py:726`, comment: *"stored for Phase 3"*) is written
   at upload (`app.py:3933`) but `grep -n "audio_path"` across the engine
   shows no reader anywhere. Video → hearing is [ABSENT] even when video →
   sight works.
8. **[EV] §11 instrumentation gaps — all four checked are [ABSENT]:** no
   `vitals` string anywhere in `dsf_ai_service` (daily vitals rollup absent);
   no `per_window`/`window_rollup`/`daily_rollup` instrumentation (one
   unrelated local-variable hit in a neuron-folding unit test, not
   instrumentation); no `affect_trace`/`promotion_lineage` artifact anywhere
   — affect values (`arousal`/`valence`/`surprise`/`need_pressure`) are
   attached to every individual atlas write via `_affect_kwargs()`
   (`gualaloom_v5_engine.py:1881-1889`), but there is no aggregating "trace"
   or lineage record built from them.
9. **[EV] "PLAY" is a config time-slice, not a protected block.**
   `_BLOCK_SHARES` (`substrate_runner.py:233-236`) gives `play` 15% of the
   1-hour cycle, but `_SUPPRESSED_BLOCKS = {"quiet","experience"}` does not
   include it, and no code anywhere gates or reserves activity selection
   specifically for `play` — the block's own docstring says it "Gates the
   MACHINE's scheduled pushes only ... Never touches her own activity
   selection." Effectively `play` behaves identically to `scaffold`/
   `converse` except in name; it protects nothing.
10. **Duplicate `[curriculum] autonomous study started` log lines** at
    near-identical timestamps were observed in CloudWatch — most likely
    ECS rolling-deploy overlap (two tasks briefly alive), not a live
    split-brain; `_gl_init()` has a proper idempotency guard
    (`app.py:1180-1182`) and the task-def confirms a single container/process.
    Flagged as [NOT MEASURED] with high confidence in the benign explanation
    — a genuine multi-process split-brain was not ruled out with certainty
    from outside the running container.

---

## §6 — LEARNER-PROGRAM TRUTH

### YouTube
- **[EV] Adapter exists**: `dsf_ai_service/loom_model/world_feeds.py:86-107`
  (`youtube_text()`), YouTube Data API v3 search, 10 rotating
  child-appropriate queries (`YOUTUBE_QUERIES`, lines 28-34).
- **[EV] Enabled in prod**: gated by `WORLD_FEEDS` (task-def value `1`,
  confirmed via `describe-task-definition`); wired into the live
  `CurriculumScheduler`'s `interleave_fns` at `app.py:1401-1420` (the live
  boot path — see "Curriculum scheduler wiring" below).
- **[EV] Key present and valid**: `YOUTUBE_API_KEY` is a literal env var on
  `dsf-ai-task:494` (plaintext in the task-def, also flagged separately in
  §2's audit as a security issue). Reproduced the exact production call
  read-only: returned 6 real video results (titles/descriptions). Running the
  actual `youtube_text()` function against it produced 16 clean sentences
  after `_clean_lines()` filtering — the adapter's own logic is not broken.
  This **updates/corrects** a standing memory note that YouTube/PBS/Spotify
  keys were absent — YouTube's key is present and functional.
- **[EV] Content NOT reaching her read path in practice**: CloudWatch
  (`/ecs/dsf-ai`, 72h) shows every observed `[worldfeed] youtube ...` line at
  `n_fed=0`. See failure item 3 above for the assessed cause (shared
  rate-cap contention with book-curriculum/khan pulls in the round-robin).
- **Filter rates**: `_clean_lines()` (`world_feeds.py:46-61`) drops
  boilerplate lines (subscribe/ads/etc. via `_BOILERPLATE` regex, line 36-43),
  lines <12 or >240 chars, and non-prose fragments; `_world_feed_once`
  additionally drops any sentence containing a word >20 chars
  (`substrate_runner.py:477`). None of this explains the observed 0-fed
  pattern (16 sentences survived filtering in the isolated repro above) — the
  rate-cap gate downstream is the more likely cause.
- **Modality**: text only. `youtube_text()` never touches video bytes/frames
  — it returns API search-result titles+descriptions as sentences, fed
  through the identical `read_sentence()` path as book curriculum
  (`_curriculum_feed_chunk`, `substrate_runner.py:267-324`). **No video frame
  or audio ever reaches sight/hearing via this feed** — confirmed by tracing
  `_world_feed_once` → `_curriculum_feed_chunk` → `read_sentence`/`read_word`;
  none of these call `process_sight_frame`/`process_sound_frame` or touch
  `VideoItem`/frame decode at all.

### Khan Academy
- **[EV] Adapter exists**: `world_feeds.py:64-83` (`khan_text()`), Tavily
  search restricted to `khanacademy.org` via `include_domains`.
- **[EV] Enabled + working**: `TAVILY_API_KEY` present and valid in the live
  task-def. CloudWatch confirms real successful fetches: `[worldfeed] khan
  'the sun moon and stars for children': n_fed=15 organ+=0` and `[worldfeed]
  khan 'story for young children about animals': n_fed=15 organ+=0`. Live MCP
  event captured this audit: `world_feed_studied{feed:"khan",
  query:"kindness and feelings for children", n_fed:15, organ_tokens:0}`
  (tick 15050792). **Khan content genuinely reaches her read path** — the
  only working "world feed" of the two implemented.
- **Modality**: text only, identical path to YouTube above (titles/snippets
  from Tavily search results, never touches sight/hearing).
- Note: `khan_text()` searches `khanacademy.org`, not `khanacademykids.com`
  (the domain actually listed in `allowlist.py`'s `ALLOWED_CORPUS_SOURCES`) —
  and neither `khan_text()` nor `youtube_text()` calls
  `allowlist.validate_source_url()` at all. The allowlist mechanism is only
  actually enforced for the one Gutenberg book-fetch path
  (`curriculum_scheduler.py:130-134`, `curriculum/adapters/gutenberg.py`).
  `allowlist.py`'s own docstring claim ("All 6 future adapters use this
  module") is **not true of the 2 adapters that exist** — worth a register
  line under §9's spec-vs-code gaps, noted here since it surfaced in this
  scope.

### PBS Kids
- **[ABSENT]**. Domain string only in `allowlist.py:15`
  (`"pbskids.org"`). No adapter file, no adapter class, no fetch function, no
  API key anywhere in the live env. `curriculum/adapters/` contains exactly
  one adapter: `gutenberg.py`.

### Spotify
- **[ABSENT]**. Domain string only in `allowlist.py:17` (`"spotify.com"`). No
  adapter code, no API key. Same disposition as PBS.

### Curriculum scheduler wiring (was dead-wired once, `-186` reconnected)
- **[EV] VERIFIED live-wired at the current SHA.** The live boot path is
  `app.py:_gl_init()` (called from ~17 route handlers as a defensive
  re-init, but idempotent — `if _guala is not None: return`, line 1181-1182).
  Inside it, `CurriculumScheduler` is instantiated and `.start()`ed
  unconditionally (`app.py:1401-1422`), **not** gated by
  `CURRICULUM_AUTOSTART` (that env var only gates a *different*, deliberately
  retired mechanism — the "65-A density engine" started at `app.py:1379`,
  which is a documented no-op given prod's `CURRICULUM_AUTOSTART=0`; the code
  comment at `app.py:1384-1400` explicitly distinguishes the two and confirms
  `substrate_runner.boot_substrate()` — which contains a second, near-
  identical copy of this wiring — has **zero callers** anywhere in the live
  process (verified: `grep -n "boot_substrate(" dsf_ai_service` — no call
  sites besides its own `def`). That second copy is dead, matching its own
  in-code comment.
- **[EV] Confirmed actively running**: CloudWatch shows recurring `[curriculum]
  autonomous study started: enabled=True books=10 chunk=30 interval=120s
  interleave=['worldfeed', 'lookup']` lines, and live events during this audit
  show real book progression: `curriculum_studied{book_id:16, title:"Peter
  Pan", offset:300, n_book_sentences:4506, book_complete:false}` (tick
  15052540) plus dozens of `organism_experience_bound` word-events matching
  Peter Pan's actual text ("mrs darling", "wendy", "breakfast", ...).
  Independently, `guala_status`'s `pair_bond.worldfeed` gauge was observed
  rising from `0.3` → `0.824` between two calls ~2 minutes apart during this
  audit — corroborating live worldfeed activity outside the log sample.

---

## §7 — SENSORY TRUTH, END TO END PER SENSE

### Sight (camera)
- **Source → transduction**: `POST /sight_frame` (`app.py:1575-1614`) decodes
  a base64 JPEG/PNG and calls `_guala.process_sight_frame(grid)`
  (`gualaloom_v5_engine.py:6117-6175`). Real subsampled pixel intensities
  (`np.asarray(grid).ravel()`, 100-sample subsample) are cached as
  `_last_sight_signal` with a wall-clock timestamp, and `view_picture()` +
  `sight.process_viewing()` produce a motif that is atlas-recorded and
  event-logged (`sight_frame_bound`).
- **[EV] The historical bug is fixed at the running SHA.** Code comment
  (`gualaloom_v5_engine.py:6144-6150`) documents the prior defect verbatim:
  *"grid.ravel() silently swallowed any input that wasn't already a numpy
  array ... which meant `_last_sight_signal` never got set and every READING
  word's `organism_experience_bound` event showed `senses=[]` even while
  `sight_frame_bound` kept firing (07-05 live log)."* `git blame` confirms the
  fix (`np.asarray(grid).ravel()`) landed in commit `0a0cda7` ("wave-cell
  BindingAtlas rewrite ... with both bug fixes applied"), an ancestor of the
  current running SHA `168ef1b`. **The fix is live.**
- **[EV] Binding window is real and narrow**: `SENSE_BINDING_WINDOW_SEC =
  3.0` (`gualaloom_v5_engine.py:485`) — a word only carries `has_sight=true`
  if a real camera frame arrived within the last 3 wall-clock seconds
  (`_enqueue_organism_remember`, lines 2983-2999).
- **[EV] organism tap — currently empty, and this is honest, not broken.**
  Every `organism_experience_bound` event pulled live during this audit (100+
  events across 3 separate `guala_get_events` calls, spanning ~2 minutes of
  real book-reading) showed `has_sight:false, has_sound:false, senses:[]`.
  Cross-checked against `guala_status.presence`: `joe`/`wc`/`c1` all
  `present:false` at the time. CloudWatch (24h window) shows **zero**
  `sight_frame_bound`, **zero** `sound_frame_bound`, and **zero**
  `cochlear-debug` log lines — i.e., no live camera/mic frames have been
  POSTed to her in at least the last 24 hours. `senses=[]` on every reading
  event is the *correct*, honest output of the fixed code when no one is
  streaming a camera — not a recurrence of the bug. `guala_status`'s
  `frame_backpressure.dropped` counters (`sight:91, sound:91`, `inflight:0`)
  show frames DID arrive at some earlier point (cumulative since an unknown
  reset), but not in the last 24h window checked.
- **UI seat**: `sight_frame_bound`/motif events are visible via the events
  endpoint/bridge; no dedicated "live camera preview" status field was found
  in `/status` beyond `frame_backpressure` counters.
- **Pictures (30) and video (1) are a separate, non-live-camera sight path**
  and work differently — see §6 and failure item 1 above (video is currently
  broken post-restart; pictures decode and attend correctly, including HEIC
  via `pillow_heif`, `app.py:3760`).

### Hearing (mic + Whisper leg)
- **[EV] Mic → cochlear transduction is real and live.** `POST /sound_frame`
  (`app.py:1617-1653`) decodes webm→wav and calls
  `_guala.process_sound_frame(wav)` (`gualaloom_v5_engine.py:6177-6244`) —
  real `cochlear_transduce()` DSP, real atlas binding per frequency band,
  `sound_frame_bound` event on any band firing.
- **[EV] Whisper leg (speech→words) is OFF in production.** Gated by
  `VOICE_WHISPER` (`app.py:1670`, default `"0"`), and **absent** from the
  24-variable live task-definition dump — confirmed off. When it was on
  historically, a since-removed mechanism (`GL-CMD-SEVER-MIC-WORD-LOOP-204`,
  documented at `app.py:1654-1665`) crudely classified raw mic energy into
  fixed words tagged as "Joe said this" — root-caused as a resonance loop and
  severed; the code comment explicitly confirms real cochlear hearing was
  untouched by that fix and Whisper (Part B) remains "untouched" but
  flag-gated off.
- Net: she hears raw ambient/mic sound as real signal (when a mic client is
  actively streaming — none was in the last 24h, same as sight), but spoken
  words are not currently converted into read content anywhere in prod.

### Her own voice (self-hear + tagging)
- **[EV] Fully real, two-channel, and live by default.**
  `_self_hear()` (`gualaloom_v5_engine.py:7128-7222`): (1) every reply word is
  re-read via `read_word(..., source="guala")` at reduced dwell, tagged so it
  never resonates as external input; (2) a real synthesized voice — `espeak-ng`
  generates an actual WAV of her reply — is fed through the same
  `process_sound_frame(..., source="voice:self")` real-audio path
  (`GL-CMD-SELFVOICE-TAGGING-152`), so her own voice is genuinely transduced
  as sound, not synthesized as a fake event. Both legs are governed by kill
  switches (`SELF_HEARING_ENABLED`, `SELF_VOICE_AUDIO_ENABLED`), **both
  default `"1"` and neither appears in the live task-def** → both **on** in
  production.

### Tactile / olfactory / gustatory (descriptor emulation)
- **[EV] Real, physics-based, not hashed placeholders.** `_bind_sensory_words`
  (`gualaloom_v5_engine.py:5684-5731`) and `_sentence_modal_signals`
  (`5738-`) both call `dsf_ai_service.substrate.sensory_generators
  .generate_sensory_signals()` — real TOUCH/SMELL/TASTE_LIBRARY channel
  waveforms, explicitly documented as "never the banned hash-per-word fake."
  A fixed lexicon maps descriptor words (soft/warm/sweet/etc., not
  enumerated in full here) to a modality; only matched words fire — "honest
  absence" (the code's own term) otherwise.
- **[EV] Wired into every intake path, including the tick-by-tick corpus
  READING path** — this was a live-seat gap Joe found and it was fixed:
  `_bind_sensory_words`'s own docstring (5685-5695) documents that the
  mechanism "was wired into the curriculum/lookup/bulk-load paths but never
  into `_atick_reading`" and was ported directly into the engine to close
  that gap. `sensory_words_bound` is the event to watch; none fired in the
  ~100 live reading events sampled this audit (the Peter Pan passages
  encountered — "forgot", "wendy", "breakfast", "skeleton leaves" — did not
  contain a lexicon-matched descriptor word in that window; consistent with
  "honest absence," not a wiring failure).

### Scene/story lanes (place, ambient, WHO)
- Covered fully under §7A/V1 below (same mechanism). WHO = live presence
  list (`coordinator._presence`, forwarded as the `presence` tuple element).

### Disposition of the claimed "sight-snapshot silent-failure defect"
**The originally-reported defect is fixed in the running SHA; what remains
live is honest, expected absence, not silent failure.** Evidence chain:
(1) the exact bug is documented verbatim in a code comment as historical
(`gualaloom_v5_engine.py:6144-6150`); (2) `git blame` places the fix
(`np.asarray`) in an ancestor commit (`0a0cda7`) of the running SHA; (3) the
`except Exception` at that call site (line 6155-6157) now explicitly *logs*
any residual failure with the comment "senses stay honestly absent" rather
than swallowing it; (4) `senses:[]` observed live on every reading event
during this audit is fully explained by **zero live camera/mic frames in the
last 24h** (CloudWatch: zero `sight_frame_bound`/`sound_frame_bound`/
`cochlear-debug` lines) and by the 3-second binding window — not by a
recurrence of the original swallow-bug. Register-worthy residual: there is no
`/status` indicator that distinguishes "no camera currently streaming" from
"camera streaming but binding failed," so an operator watching only `/status`
cannot tell the two apart without checking the event stream, as done here.

---

## §7A — ENVIRONMENT TRUTH: HER HOUSE, HER ROOMS, HER WORLD

### V1 — story lanes on bundles (place/ambient/participant tags)
**[EV] VERIFIED, mechanism proven, not anecdote.** `read_sentence()`
(`gualaloom_v5_engine.py:2255-2337`) is the single funnel point: *"every
intake path funnels through this one function (curriculum, corpus READING,
worldfeed, lookup, converse)"* (its own docstring, lines 2275-2277). When
`place`/`ambient` are not explicitly supplied it derives them once per
sentence via `scene_tags_from_words()` (`gualaloom_v4_krimelack_dna.py:443-
457`) against two fixed, hand-curated lexicons, `PLACE_WORDS` (50+ entries:
garden/wood/room/kitchen/nursery/shore/... , lines 397-420) and
`AMBIENT_WORDS` (40+ entries: rain/sunlight/wind/quiet/warm/dark/...,
lines 421-440) — "no scene invention, ever" (V2's own design rule, honored by
having no fallback path at all). Tags are forwarded to every `read_word()`
call for that sentence and cached at `self._last_place_tags`/
`_last_ambient_tags`, surfaced live via `/status`'s `scene_lanes` field.
**Which paths carry it**: curriculum, corpus READING, worldfeed, lookup,
converse — confirmed by the shared funnel. **Which don't**: any caller that
uses `read_word()` directly instead of `read_sentence()` bypasses tag
derivation entirely (place/ambient simply omitted, not guessed) — no such
direct callers were found in the intake paths audited.
**Live observation**: `guala_status.scene_lanes` showed `{"place": [],
"ambient": []}` at both audit timestamps — an honest empty result (the
Peter Pan passage in the window contained no lexicon word), not proof the
mechanism is broken.

### V2 — persistent place registry
**[EV] Split finding: rich object model exists in code; is unwired and
inert in the live deployment (see failure item 2).**
- The registry itself — `dsf_ai_service/virtual_home.py` — is real and
  detailed: a `ROOMS` dict (her_room fully built; hallway/library/tv_room/
  joe_room/wc_room/backyard/outside/kitchen/common as W2 stubs, "objects":
  []) and an `OBJECTS` dict of 12 real, stateful entities in her room —
  drapes, night_light, bed, blanket (mobile), pillow (mobile), toy_chest
  (contains music_box + bell), music_box, bell, mirror, desk, crayons,
  tablet — each with real states, verbs, and sensory-experience payloads
  (smell channels + words), meant to persist via `WorldState` to
  `world_state.json` on EFS.
- **But nothing in the live process calls `apply_verb()`, `room_snapshot()`,
  or constructs a `WorldState`, except the one instantiation inside
  `organ_brain_service.py` — which the code itself calls "dead: :8090
  container [removed]"** (`app.py:1709,1720,1722`). `world_state.json` is
  **not present** in the newest S3 backup file listing (13 files:
  `guala_atlas.json, guala_bucket.json, guala_coordinator.json,
  guala_core.json, guala_deep_atlas.json, guala_identity.json,
  guala_needs.json, guala_organism.pkl.gz, guala_sections.json,
  guala_sounds.json, guala_tapestry.pkl.gz, guala_videos.json,
  guala_visual.json` + a `pictures/` prefix — no `world_state.json`). The
  live `/room` command (`substrate_runner.py:1150-1166`) only ever reads that
  file (never writes/applies verbs) and fails to its exception path
  (`{"objects": {}, "sky": {}, "weather": "clear", "error": ...}`) when it is
  absent, as the backup evidence suggests it currently is.
- **Episodic `tracked_objects`** (a different, unrelated mechanism — content
  words from **converse turns**, not spatial objects) lives in
  `dsf_ai_service/substrate/hemisphere_cognition.py:228-279`
  (`ep.tracked_objects[word] = {chi, last_seen_tick, salience, source}`,
  populated by `ep_record_turn()` on every converse exchange, function words
  excluded). Its count is logged only inside `hemisphere_update` events
  (`hemisphere_cognition.py:576-594`), which require converse activity to
  fire. **[NOT MEASURED]**: no `hemisphere_update` event appeared in the ~150
  live events sampled this audit (no converse turns occurred in that window
  — `presence` was all-false throughout), so the current live count could not
  be read directly through the tools available to this audit (no
  file/EFS access, and the MCP bridge does not expose hemisphere internals).
  The mechanism is confirmed real and live-wired (imported and called from
  the main engine, `HEMI_EP_ENABLED` on by Docker-image default and not
  overridden off in the task-def); its *current* item-by-item contents are a
  register follow-up requiring either a converse turn during observation or
  direct state-file access neither available nor authorized here.

### V3 — interactive environment / world sim (process outside her own)
**[ABSENT] — no separate process exists.** `virtual_home.py`'s own docstring
states the ratified design plainly: *"World is substrate-side state. UI
renders it, doesn't own it."* (lines 5-6) — i.e. even by design it is meant
to live inside the same engine process, not externally. In the current
deployment it doesn't even do that live (see V2) — its only would-be host
process (`organ_brain_service.py` on `:8090`) has been removed from the task
definition (confirmed: `describe-task-definition` shows exactly one
container, one command, one port, `8080`). **"World v0 — a crib and a
backyard rendered to a 64×64 eye"**: no match for "crib" or "64x64" or
"World v0" anywhere in `dsf_ai_service` or `docs/` (`grep` clean across
both) — this appears to describe a different/earlier concept than what
actually exists (`virtual_home.py`'s "her room" object model, spec
`GL-MDL-WORLD-WC-20260612-02`). **[ABSENT]**, and the pre-audit phrasing
itself could not be matched to any artifact in the repository.

### V4 — embodiment hooks (avatar horizon)
**[ABSENT]**. See failure item 6. Only forward-looking comments exist; no
interface, stub, or endpoint.

### HEIC scene tags — six titles
**[EV] The six titles have already arrived and are live, not "waiting."**
`guala_status.pictures` lists exactly six `.HEIC` items right now: `Guala
Family.HEIC` (times_attended 14), `IMG_1962.HEIC` (7), `IMG_2121.HEIC` (11),
`IMG_2161.HEIC` (7), `IMG_2216.HEIC` (11), `IMG_6254.HEIC` (622 — clearly a
favorite). This **updates** the pre-audit framing ("shipped live and waiting
on six HEIC titles") — they are present and already being attended, not
pending. Upload path: `pillow_heif.register_heif_opener()` +
`Image.open()` (`app.py:3759-3769`) — real HEIC decode to a 64×64 grayscale
intensity grid, same as any other picture; genuine sight transduction when
`ATTENDING_VISUAL` selects one of them.
**What does NOT happen**: the upload path never feeds the filename/title
through `read_sentence()`/`scene_tags_from_words()` — titles are stored as
inert metadata (`title = _fname or item_id`, `app.py:3774`) only. So **if a
seventh tagged HEIC arrives today**, it will decode and become perceivable
via sight exactly like the existing six, but it will not, by itself,
populate `scene_lanes` — V1 tagging only fires from sentence text (captions,
book text, converse), never from picture/video metadata. Any place/ambient
tag for a photo would require a human- or caption-authored sentence about it
to pass through `read_sentence()` separately.

### Care-schedule enforcement (spec §8 daily-rhythm blocks)
**[EV] Real CONFIG the orchestrator obeys — not prose — with one caveat on
PLAY.** `_BLOCK_SHARES` (`substrate_runner.py:233-236`): `scaffold 0.25,
experience 0.25, play 0.15, converse 0.15, quiet 0.20` of a rotating
`BLOCK_CYCLE_SEC` (default 3600s, hot-readable). `_current_block()`
(lines 241-252) computes the live block from wall-clock phase.
`_SUPPRESSED_BLOCKS = {"quiet", "experience"}` (line 237) — during those two
blocks (45% of the cycle), **all scheduled machine intake (curriculum book
chunks, khan, youtube, lookup) is suppressed to zero, live-observed**: audit
event `block_intake_ledger{block:"quiet", planned:30, actual:0, capped:true,
reason:"suppressed"}` immediately followed by
`curriculum_studied{book_id:16, title:"Peter Pan", n_fed:0,
organ_tokens:0}` (tick 15052540) — direct proof the gate is real and firing,
not documentation-only. Docstring is explicit about scope: gates the
**machine's scheduled pushes only** — never converse, never her own
activity selection, never attending/emitting (`substrate_runner.py:230-232`).
**PLAY is not a protected block** in the sense of shielding a reserved
activity: it is simply not in `_SUPPRESSED_BLOCKS`, identical in effect to
`scaffold`/`converse` — nothing in the codebase gives `play` any distinct
behavior (no dedicated play-activity trigger, no interruption shielding).
See failure item 9.

### §11 instrumentation gaps
| Item | Status |
|---|---|
| Affect trace (per-write tagging) | **PARTIAL** — `_affect_kwargs()` attaches arousal/valence/surprise/need_pressure to every atlas write ([EV] `gualaloom_v5_engine.py:1881-1889`); no aggregated time-series/trace artifact exists |
| Promotion lineage | **[ABSENT]** — no string match anywhere in `dsf_ai_service` |
| Per-window rollup | **[ABSENT]** — no instrumentation match (one unrelated test-local variable name only) |
| Place/ambient tags | **VERIFIED** — see V1 above |
| Daily vitals rollup | **[ABSENT]** — no "vitals" string anywhere in `dsf_ai_service` |

---

## TIER-BY-TIER ENVIRONMENT STATUS TABLE (§7A)

| Tier | What it claims | Status | Evidence |
|---|---|---|---|
| V1 — story lanes (place/ambient/WHO on bundles) | Sentence-level scene tagging bound in-window across all intake | **VERIFIED** | `read_sentence()` single funnel (`gualaloom_v5_engine.py:2255-2337`); real fixed lexicons (`gualaloom_v4_krimelack_dna.py:397-457`); live `/status.scene_lanes` field (currently empty — honest, no match in window) |
| V2 — persistent place registry (room/objects) | Her room, bed, window, hallway etc. exist as durable entities | **CODE EXISTS, LIVE-WIRING ABSENT** | Rich model in `virtual_home.py`; only instantiation site is the removed `:8090` organ-brain container (`app.py:1709/1722`); `world_state.json` missing from newest S3 backup; zero other callers of `apply_verb`/`WorldState` in the codebase |
| V2b — episodic `tracked_objects` | Count/contents of concept-objects noticed | **MECHANISM VERIFIED LIVE, CURRENT COUNT NOT MEASURED** | `hemisphere_cognition.py:228-279`, fires on converse turns; no converse activity in this audit's observation window, so live count unreadable via available tools |
| V3 — interactive world sim (process outside her own) | A world running as its own process/simulation | **[ABSENT]** | `virtual_home.py`'s own docstring: "substrate-side state," not external, by design; sole candidate host process (`organ_brain_service.py`) removed from the task-def; no "crib"/"64x64"/"World v0" artifact found anywhere |
| V4 — embodiment hooks (avatar) | Interface stub toward a physical avatar | **[ABSENT]** | Only forward-looking code comments, no stub/class/endpoint |
| HEIC scene tags (six titles) | Lanes wired to receive Joe's six HEIC photos | **PICTURES LIVE; SCENE-LANE LINK ABSENT** | All six already present and attended (`guala_status.pictures`); real HEIC decode (`pillow_heif`); titles never flow through `scene_tags_from_words()` — no lane populated from picture metadata |
| Care-schedule (daily-rhythm blocks) | Config-enforced experience/scaffold/play/quiet/converse/sleep shares | **VERIFIED (except PLAY)** | `_BLOCK_SHARES`/`_current_block()`/`_SUPPRESSED_BLOCKS` (`substrate_runner.py:229-324`); live-observed suppression event this audit (`block_intake_ledger` + `curriculum_studied n_fed:0` during "quiet") |
| PLAY as protected block | Reserved, shielded activity window | **PARTIAL/ABSENT** — exists as a named 15% time-share only, no protective behavior coded | `substrate_runner.py:230-237` |
| §11 instrumentation: affect trace | Aggregated affect history | **PARTIAL** (per-write only, no trace artifact) | `gualaloom_v5_engine.py:1881-1889` |
| §11 instrumentation: promotion lineage | Traceable promotion history | **[ABSENT]** | no match repo-wide |
| §11 instrumentation: per-window rollup | Aggregated per-window metrics | **[ABSENT]** | no match repo-wide |
| §11 instrumentation: daily vitals rollup | Daily health/vitals summary | **[ABSENT]** | no "vitals" string repo-wide |

---

## Cross-cutting note for §9 (spec-vs-implementation gap table, out of this
scope's deliverable but surfaced here for continuity): `allowlist.py`'s claim
that "all 6 future adapters" use it for source validation is contradicted by
the 2 adapters that actually exist (khan/youtube bypass it entirely; only
gutenberg calls it) — worth a line in the consolidated gap table.
