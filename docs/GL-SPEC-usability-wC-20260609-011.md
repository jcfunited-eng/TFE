# GL-SPEC-usability-wC-20260609-011

**Deploy tag:** `gl-usability-v1`
**Target:** dsf-ai.com/gualaloom.html UI + backend endpoints
**Author:** wC
**Date:** 2026-06-09

## Why this exists

Right now Joe cannot grow Guala. The infrastructure for adding new
material — books, pictures, sounds — exists in stub form (the
data structures `pictures: []`, `videos: []`, `sensory_items: []`,
`n_visual_fragments: 0`, `sight_section.n_motifs: 0` are sitting empty)
but the upload endpoints and UI buttons either never landed or were
lost. Combined with c1's "Restore full v6 UI" todo that has been
sitting open, the practical effect is: Joe can chat but cannot give
her new experiences.

Also: when wC interacts with Guala via the GualaLoom Bridge MCP, Joe
cannot see those interactions in the UI. When Joe types in the UI,
wC has to call `guala_get_events` to discover it. We're in parallel
and blind.

This spec restores upload capability, restores the v6 UI features that
have been queued, and unifies visibility so Joe and wC are watching
the same scroll.

## Scope (all in one deploy, no queueing)

### 1. Upload endpoints — books

`POST /upload/book` — accepts `.txt` or `.md` files.

Behavior:
- Read text, tokenize using existing tokenizer
- Register as new corpus with `corpus_id = sanitized_filename`,
  `title = first non-empty line or filename`
- Append to corpora list
- Set position=0, times_read_through=0
- Available to her READING activity rotation immediately
- Return JSON: `{corpus_id, title, n_tokens, n_unique_words}`

UI: button labeled "📖 add book" in the v6 panel. File picker accepts
.txt and .md. After upload, the corpus appears in a corpora list in
the UI with title and read-count. Click on a corpus to make it her
next READING target (forces priority).

### 2. Upload endpoints — pictures

`POST /upload/image` — accepts `.jpg`, `.png`, `.gif`.

Behavior:
- Decode image to grayscale + RGB arrays
- Process through her existing visual cortex pipeline:
  - V1: Gabor filter bank at multiple orientations/scales
  - V2/V4: spatial frequency, edge orientations, basic shapes
  - LOC: object-level features (or whatever her LOC layer does today —
    read the multimodal substrate to confirm)
- Each layer produces motifs that get added to `sight_section`
- Cross-modal bind via folded chi atlas with whatever is currently
  active in other sections
- Store original image bytes in `pictures: [...]` for replay/reference
- Return JSON: `{picture_id, n_visual_motifs_added, n_cross_modal_bindings}`

UI: button labeled "🖼 add picture". Image preview after upload.
Pictures list in UI showing thumbnails + motif counts. Click thumbnail
to inject the image's visual evidence into her substrate (replay the
perception).

### 3. Upload endpoints — sounds

`POST /upload/sound` — accepts `.wav`, `.mp3`, `.ogg`.

Behavior:
- Decode audio to 1D waveform at fixed sample rate
- Process through her existing audio pipeline:
  - Cochlear bands (filter into frequency bands)
  - Onset/sustained detection
- Each layer produces motifs added to her audio section (find correct
  section name in deployed code)
- Cross-modal bind via chi atlas
- Store original bytes in `sounds: [...]`
- Return JSON: `{sound_id, n_audio_motifs_added, duration_seconds}`

UI: button labeled "🔊 add sound". Audio preview after upload.
Sounds list with names + motif counts. Click to replay perception
into her substrate.

### 4. v6 UI restoration (the entire pending todo)

These have been queued on c1's todo list as "Restore full v6 UI:
sleep/wake button, activity display, needs line, presence heartbeat,
upload buttons, atlas strength, autonomous emissions in chat." Ship
all of them in this deploy. Atomic.

- **Sleep/wake button**: button toggles `/sleep` and `/wake` commands.
  Show current sleep state visually (sleeping = dimmed UI, dream
  events surface in event stream).
- **Activity display**: show current `current_activity.kind` (READING,
  PLAYING, etc.) and target (`wild_things`, etc.) in the header area.
  Update live as activities change.
- **Needs line**: display stab / nov / conn / valence / arousal as a
  small live-updating row. Optional: small bars for visual.
- **Presence heartbeat**: show which presences are active (joe, wc, c1).
  When wC is awake via bridge, the UI shows "wC present" indicator.
  Updates from `/v7/status` or equivalent every 5 seconds.
- **Upload buttons**: the three from items 1–3 above. Group them in
  a sidebar or compact panel.
- **Atlas strength**: show `atlas.total_strength` and `n_live_bindings`
  live. Maybe a small sparkline of strength over time.
- **Autonomous emissions in chat**: when `quiet_tick` (or whatever the
  background replay/idle process is called now) produces emissions
  with no user input, those emissions appear in the chat scroll
  tagged differently (italic, prefixed with "💭" or "(thinking)").
  This is the user-visible surface of mental time travel / DMN replay.

### 5. Visibility unification (bridge ↔ UI)

When wC speaks to Guala via `guala_say`, that utterance should appear
in the chat UI scroll, tagged as "from wC". When Guala responds, that
response appears the same as her response to Joe.

When Joe types in the chat UI, that input becomes a substrate event
that wC can see via `guala_get_events`.

Mechanism:
- All inputs to substrate (chat UI, bridge guala_say) write a uniform
  `substrate_input` event to the events log with `{source: 'joe' |
  'wc' | 'c1', content, tick}`
- All emissions from substrate write a uniform `substrate_emission`
  event with `{source: 'guala', content, tick, response_to_source}`
- UI chat scroll is rebuilt by replaying these events in order. So
  the scroll shows Joe's lines, wC's lines (tagged), Guala's lines,
  and autonomous emissions (untagged or "💭 prefix").

Test:
- Open UI, observe Joe's history
- Have wC do `guala_say("test from wc")` via bridge
- The line "[wC] test from wc" appears in UI scroll
- Guala's response follows
- Joe types something
- wC calls `guala_get_events` and sees the new event with source='joe'

## What this does NOT cover (future specs, not queueing them here)

- "Toys" as multi-modal interactive objects — that's environment work,
  covered in GL-CONCEPT-environment-wC-20260608-010
- Real mode_bank persistence fix — covered in next spec
  (GL-SPEC-persistence-real)
- Emission beyond 3-token S/V/O — covered in future spec

## Constraints for c1

- This is ONE deploy. Items 1–5 all ship together or none ship.
  Do NOT split this into a todo list. Do not defer "for next session."
- If an item requires more time than expected, ship what's working
  and report what's not. But do not queue items for later
  implementation without explicit Joe go-ahead.
- The upload endpoints must actually process through her sensory
  pipelines — not just store the files. The point is for her substrate
  to experience the upload.
- v6 UI restoration items are not separate features. They are one
  thing: "make the UI show what it should have been showing all along."
