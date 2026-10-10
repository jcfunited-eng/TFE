# GL-BRIEF-V7-UI-REPAIR-WC-20260613-01

**Author:** wC
**Date:** 2026-06-13
**Builds on:** UNCAGE deploy at code SHA `3f8f35c`, task `dsf-ai-task:114` (current production). Both prior briefs (UNIFY-01, UNCAGE-01) and v7_engine.py three-pool substrate STAY. This brief is a UI patch only — `v7_engine.py` is correct and is not touched.
**Freeze carve-out per rule 6:** observation surfaced need — live page test (Joe, 2026-06-13 21:02 CT) showed eight specific failures in the post-UNCAGE UI that block the "merge all three tabs" goal that was specified in UNCAGE-01.

---

## What's broken (live audit findings)

1. **NMDA gates panel hardcoded to old POS section names.** `gualaloom.html` line 234: `for(const gn of ['intro','aware','subject','verb','object'])`. The three-pool engine has no `subject`/`verb`/`object` sections. Panel shows "subject: idle, verb: idle, object: idle" forever — false signal.
2. **Picture upload broken (404).** Current UI POSTs multipart to `/api/v1/gualaloom/upload/picture`. The REST endpoint exists in FastAPI (line 2275) but API Gateway only routes `/api/v1/gualaloom` (per the original af78f56 fix). All uploads must go through the chat endpoint using the command pattern: JSON `{text: "<base64>", command: "/addpicture:<filename>"}`.
3. **No upload bar.** Old UI had 📖 book, 📕 PDF, 🖼 picture, 🔊 sound, 🎥 video, 🎁 experience. Current UI has only the camera snapshot button. The "merge all three tabs" goal explicitly required preserving the upload features from the multimodal substrate tab.
4. **No experience bundle modal.** The 🎁 multi-sense modal (caption + image + sound + touch + smell + taste multi-select tags) used the `/bundle:<name>` command and is completely missing. This is the credo's primary mechanism for tying experience to words.
5. **No visual motif display in chat.** When Guala's v6 engine emits a picture (`visual_motif_committed` event with picture payload), the old UI rendered an `<img>` inline in the transcript. Current UI ignores the `pictures` array on chat responses. Joe can see motif events fire in the right sidebar but cannot see what she's drawing/thinking.
6. **Camera preview blocks transcript text.** Currently positioned `position:fixed; bottom:60px; right:320px` which overlaps the chat area. Joe's recent messages get obscured by his own face.
7. **No v6 stats line.** Old header showed one-line `vocab: N · motifs: M · atlas: A · sounds: S · pics: P`. Current UI has these scattered/hidden in the right sidebar with some values not rendered.
8. **Dual-endpoint dispatch ignores v6 responses.** Line 209: `fetch('/api/v1/gualaloom', ...).catch(()=>{})` fires the v6 chat in parallel but discards everything it returns — including `pictures`, `motifs`, and any text response. The v6 engine is being driven but its outputs are dropped.

---

## What stays (working — do not touch)

- Permission strip (Enable Microphone, Enable Camera, Audio ready badge, Mute toggle). All four working per screenshot.
- Mic button + push-to-talk + webkitSpeechRecognition path.
- `<audio>` element auto-play of `self_voice_audio_b64`.
- Dual dispatch on text send: `/v7/converse` (v7 substrate + voice) AND `/api/v1/gualaloom` (v6 engine + visual motifs). KEEP both. v7 generates her voice; v6 generates her visual thoughts. Both belong to her.
- Event stream polling from `/api/v1/gualaloom` with command `/events`.
- `pollV7State` polling `/v7/state` every 3s.
- Background replay every 10s.
- Session id management and "new session" button.
- The right-side state panel structure (substrate / pools / intro-aware / NMDA gates / events) — only the NMDA gates and stat values need fixing.

---

## Repair plan — UI changes only

### Fix 1: NMDA gates panel uses real section names

Replace line 234 hardcoded loop. The actual gates that exist are `intro` and `aware`. Per-pool commit activity is not an NMDA gate; it's a per-pool commit counter. New panel:

- **NMDA gates section:** loops only `['intro', 'aware']`. Shows fired/blocked/idle from `nmda_events`.
- **Pool activity section** (new, below NMDA gates): loops `['pool_a', 'pool_b', 'pool_c']`. Shows recent commit count per pool from `mode_strengths` or per-pool commit counts (use whatever `/v7/state` returns). Idle if no commits in the last 60s.

### Fix 2: Picture upload uses chat-command pattern

The camera snapshot button currently does multipart POST to the wrong URL. Rewrite the snapshot handler to:

1. Canvas → blob (JPEG, quality 0.85).
2. FileReader → base64 string (strip `data:image/jpeg;base64,` prefix).
3. POST to `/api/v1/gualaloom` with JSON `{text: "<base64>", command: "/addpicture:snapshot_<timestamp>.jpg"}`.
4. Render server response in chat as system message; if response includes `pictures`, render them inline (see Fix 5).

### Fix 3: Restore upload bar (5 file types + experience)

Add an upload bar above the input row. Six buttons:

- 📖 **book** — accepts `.txt, .md, text/plain`. Read as text. POST to `/api/v1/gualaloom` with `{text: "<plain text>", command: "/addbook:<filename>"}`.
- 📕 **PDF** — accepts `.pdf, application/pdf`. Read as base64 (data URL, strip prefix). POST `{text: "<base64>", command: "/addpdf:<filename>"}`.
- 🖼 **picture** — accepts `image/*`. Read as base64. POST `{text: "<base64>", command: "/addpicture:<filename>"}`.
- 🔊 **sound** — accepts `audio/*`. Max 6MB client-side guard. Read as base64. POST `{text: "<base64>", command: "/addsound:<filename>"}`.
- 🎥 **video** — accepts `video/*`. Client-side message "video upload: pipeline not yet wired" (matches old UI behavior; no backend chat-command path exists for video).
- 🎁 **experience** — opens the experience bundle modal (Fix 4).

All uploads add a system message to the transcript ("uploading X: filename..."), display response, and trigger `pollV7State` after completion.

### Fix 4: Restore experience bundle modal

Modal triggered by 🎁 button. Fields:

- **Caption** (text) — what is this thing called.
- **🖼 Picture** (file, image/\*).
- **🔊 Sound** (file, audio/\*, 6MB guard).
- **🤚 Feels like** (multi-select): warm, cool, cold, hot, soft, hard, smooth, rough, wet, dry, sharp, fuzzy, heavy, light, squishy, bumpy.
- **👃 Smells like** (multi-select): fresh, floral, sweet, earthy, smoky, salty, fruity, woody, clean, rain, grass, ocean.
- **👅 Tastes like** (multi-select): sweet, sour, salty, bitter, savory, spicy, creamy, tangy.
- **Cancel** / **Give her this** buttons.

On submit: build bundle object `{caption, image_b64, sound_b64, touch:[...], smell:[...], taste:[...]}`. Require at least one field filled. POST to `/api/v1/gualaloom` with `{text: JSON.stringify(bundle), command: "/bundle:<caption-or-name>"}`. Show "(creating experience '<name>': <lanes>)" in chat. Render response.

### Fix 5: Visual motif display in chat

When dual-dispatch fires `/api/v1/gualaloom`, capture the response. If it has `pictures: [...]`:

- For each picture: if `p.data` (inline base64), render `<img src="data:image/...;base64,<data>" style="max-width:240px;border-radius:6px"> <span class="title">${p.title}</span>` as an emission-class message in the transcript.
- If only `p.item_id`, render a placeholder "loading {title}..." then POST to `/api/v1/gualaloom` with `{text: "", command: "/picture <item_id>"}` to fetch the thumbnail base64, then swap the placeholder.

Apply this same picture-rendering logic for upload responses (Fix 3) and bundle responses (Fix 4) — they can also return pictures (e.g., when an uploaded picture triggers Guala to "recall" similar pictures).

### Fix 6: Camera preview repositioning

Move `<video id="cam-preview">` out of `position:fixed` overlay. Make it a small inline element in the upload bar area when active, e.g., 80×60 px next to the snapshot button. Visible only when camera permission GRANTED. The fixed-position approach was overlapping the chat area.

### Fix 7: v6 stats one-line header

Add a one-line stats strip below the header showing live counts: `vocab: ${vocab} · motifs: ${motifs} · atlas: ${atlas} · sounds: ${sounds} · pics: ${pics}`. Source values from `/v7/state` (vocab, atlas) plus the v6 stats fetched alongside (the old UI used `/api/v1/gualaloom` with command `/status` which returns `n_motifs`, `n_sounds`, `n_pictures`). Add a `/status` poll alongside `pollV7State` every 3s.

### Fix 8: Dual-dispatch captures v6 response

Line 209 currently: `fetch('/api/v1/gualaloom', ...).catch(()=>{})`. Replace with: capture the v6 response, render its `response` text as an emission-class message (Guala's v6 word output, parallel to v7 voice output), render any `pictures` per Fix 5, and refresh stats.

---

## Sandbox (rule 7) — manual browser test list

Run on prod after deploy. Joe pastes results.

1. **Load `/gualaloom.html`** — page loads, no JS errors in console. Permission strip shows three buttons. Upload bar shows six buttons. Mic button and snapshot button present.
2. **Enable Mic + Camera** — both go GRANTED. Camera preview appears inline (NOT overlapping chat).
3. **Send text "hello daddy moon"** — v7 response appears with voice. v6 response appears as emission-class message. NMDA panel shows only intro + aware (NOT subject/verb/object). Pool activity panel shows pool_a/b/c counts.
4. **📖 Upload a small .txt book file** — "(uploading book: filename)" appears, then response. v6 vocab count in stats line increments.
5. **🖼 Upload a picture file** — "(uploading picture: filename)" appears. Response renders inline picture in chat (if v6 returned one).
6. **🔊 Upload a sound file (<6MB)** — "(uploading sound: ...)" appears. Stats line `sounds:` count increments.
7. **🎁 Experience bundle** — modal opens. Fill caption "test_apple", attach picture, select touch=smooth + smell=fresh + taste=sweet. Submit. Modal closes. "(creating experience 'test_apple': word + sight + ...)" appears. Stats line updates.
8. **📸 Camera snapshot** — captures frame, posts via /addpicture:snapshot_*.jpg, response shows in chat with optional picture inline.
9. **Visual motif emission** — after sufficient interaction, if v6 emits a picture in a response, it renders inline in the transcript (max-width 240px).
10. **Stats line** — vocab/motifs/atlas/sounds/pics all show numeric values (not "?" or blank).

---

## Acceptance

- All 10 sandbox cases pass.
- `curl /gualaloom.html` greps positive for ALL: `Enable Microphone`, `Enable Camera`, `addbook`, `addpicture`, `addsound`, `addpdf`, `bundle-modal`, `/bundle:`, `pool_a`, `pool_b`, `pool_c`, `webkitSpeechRecognition`, `getUserMedia`, `self_voice_audio_b64`. Greps **negative** for: `'subject'`, `'verb'`, `'object'` (no hardcoded POS section names anywhere in the JS).
- Joe live test: types, uploads picture, gives experience, hears her voice, sees her motifs render in transcript, camera preview doesn't block messages.

---

## Out of scope (logged for later)

- **Engine init race (`v6_vocab_count=0` when session created during _guala load).** c1 flagged in deploy report; not new. Separate brief. Workaround: once Joe uses the experience bundle modal a few times, pools get seeded via vocabulary growth regardless of the race.
- **Video upload pipeline.** No `/addvideo:` chat command exists in backend. Placeholder message matches old UI.
- **Native audio krimelack from raw mic frames.** Still deferred per UNCAGE-01.
- **Decay / UNPAUSE.** Still HELD per ledger 050.

---

## Constraints (binding)

- Do NOT modify `dsf_ai_service/substrate/v7_engine.py`. UI patch only.
- Do NOT modify `dsf_ai_service/app.py` — all required endpoints already exist.
- Do NOT modify Dockerfile.
- Do NOT touch decay. Do NOT touch unpause. UNPAUSE remains HELD.
- Companion (`wc-companion.html`) remains off.
- If a fix requires changes outside `dsf_ai_service/static/gualaloom.html`: STOP, name the conflict.
