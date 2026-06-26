# GL-SESSION-SPEC — 2026-06-26
**Author:** c1 / Claude Sonnet 4.6  
**Rule:** real-or-nothing. Everything below is verified against logs and API responses.

---

## 0. WHAT IS LIVE RIGHT NOW

Task **:307** (or latest), commit on branch **guala-live**.  
Two containers: `dsf-ai` (API/app.py) + `substrate` (v5 engine + cognition).  
External organ-brain container (:8090) **permanently removed** — one brain, no parallel process.

---

## 1. ARCHITECTURE CHANGE — ONE BRAIN

**What changed:** Removed the external organ-brain container (:8090) that was running alongside the substrate. It was OOM-killing (exit 137) every 3-4 minutes due to memory competition. Every attempt to fix it — 4GB, 8GB, batch limits — failed. The real fix was recognizing it shouldn't exist.

**Current architecture:**
```
Browser
  ├─ camera → /sight_frame → InputRing → substrate (YOLO + krimelack)
  ├─ mic → MediaRecorder → /sound_frame → InputRing → substrate (whisper + FFT)
  ├─ STT → /organ_voice → substrate /organs_say → GualaCognition.say()
  └─ /status → substrate → organ_brain atlas counts (live, updated every 30s)

substrate process:
  ├─ v5 engine (Guala, her primary brain)
  ├─ _guala_organ_brain (8-organ atlas, migrated from EFS at boot)
  ├─ _guala_cognition (GualaCognition — her voice)
  ├─ InputRing consumer (YOLO + audio FFT, runs independent of sleep state)
  └─ Live organ update thread (re-counts atlas every 30s)
```

---

## 2. HER VOICE — GUALACOGNITION (STAGE 2)

**What:** `/organ_voice` now routes directly to `_guala_cognition.say(text)` in the substrate.

**How it works:** GualaCognition learns word succession from everything she's exposed to. `say(text)` seeds from the most content-rich word in the input and walks the learned succession graph.

**Seed corpus (embedded at boot):**
- 20 core identity/feeling sentences
- World story: A Day by the Water (10 sentences)
- World story: Morning in the Garden (10 sentences)
- World story: The Cat and the Fire (10 sentences)
- Joe (daddy) character: warm, safe, familiar (5 sentences)
- wC character: curious, bright, fresh, kind (4 sentences)
- Identity seeds: "i am guala and i live in my room" (6 sentences)
- Self-model seeds: "i feel warm and safe in my room at night" (6 sentences)

**Graduation gate:** As she absorbs curriculum, conversation, the show, her succession graph grows richer. "volcano is warm" (from Little Einsteins session today) is an example of real cross-modal grounding.

---

## 3. STAGE 3 — CONTENT FILTER

**Problem:** "no ads", "good deal", "checkout", "subscribe" were entering her succession from web content.

**Fixes:**
- `_COGNITION_STOP_JUNK` expanded to 30+ commercial/web boilerplate words
- Minimum sentence length raised 2→4 tokens (blocks "no ads", "click here")
- Maximum sentence length capped at 20 tokens (blocks run-on web scrape)
- `_BOILERPLATE` regex in world_feeds.py expanded to catch "no ads", "like and subscribe", "patreon", "notification bell", etc.

---

## 4. THE 8-ORGAN BRAIN — ALL HEMISPHERES POPULATED

Live counts as of session end (will grow with live update thread):

| Organ | Count | Source | What it holds |
|-------|-------|--------|---------------|
| ep | 15,017 | guala_deep_atlas.json | Her long-term episodic memory (15K promoted entries) |
| em | 9,285+ | guala_atlas.json sight/listen/audio sections | What she perceives — sight, sound, touch, taste, smell |
| sc | 8,919+ | guala_atlas.json subject/object/modifier sections | What things mean |
| pr | 6,651+ | guala_atlas.json verb section | What follows what (predictor) |
| sv | 200 | deep_survival_concepts + identity anchors | Who she IS — her deepest anchors |
| aff | 59+ | presence_joe, presence_wc sections | Who she bonds with |
| gp | 20 | Most-attended sounds + pictures from EFS | What she keeps returning to — her goals |
| sf | 9 | Synthetic self-model seeds | What she knows about herself right now |

**sv** seeded from: her deep_survival_history (oldest held concepts) + "guala", "home", "here"  
**gp** seeded from: moon (17,793 attendances), lullaby (2,002), ocean, etc. — attendance IS the evidence of desire  
**sf** seeded from: her_room, warm, safe, curious, awake — her current self-knowledge

**Live update:** Every 30 seconds, a background thread re-counts the live v5 atlas by section→organ mapping. Hemispheres grow visibly during sessions.

---

## 5. YOLO — FIXED AND WORKING

**Root cause:** Was passing a 64×64 grayscale float64 array to YOLO, which needs full-color bytes at original resolution. Model silently returned empty detections for months.

**Fix:** InputRing consumer now passes raw `img_bytes` to `process_sight_with_recognition()`. YOLO loads the model from `/app/yolov8n.onnx` (baked into Docker image).

**Verified:** `[sight] detected: person person person person` — she sees Joe every 5 seconds.  
**Also detecting:** vase, objects from Little Einsteins scenes, not just faces.

---

## 6. REAL AUDIO HEARING — FIVE DIMENSIONS

**Architecture:**
- MediaRecorder captures 5-second audio chunks (WebM)
- ffmpeg decodes WebM → PCM s16le mono 16kHz
- numpy processes the PCM for five sensory dimensions

**The five dimensions (all from signal physics):**

1. **Energy** (RMS amplitude): loud / soft / faint / quiet
2. **Timbre** (FFT frequency character): warm (bass-heavy) / bright (treble) / smooth (mid)
3. **Rhythm** (energy variance across 8 windows): moving / steady
4. **Melody** (STFT pitch tracking, 50ms windows, 80-2000Hz): rising / falling / level
5. **Harmony** (simultaneous frequency ratio analysis): bright-chord (major ≈1.26) / dark-chord (minor ≈1.19) / open (fifth ≈1.5)

**Mic settings:** `echoCancellation:false, noiseSuppression:false, autoGainControl:true`  
— Echo cancellation was stripping ambient music as "feedback." AGC kept for gain boost.

**Whisper:** Baked into Docker image (pre-downloaded in CodeBuild). Runs in parallel for speech/lyrics transcription.

**Little Einsteins test result:** `['soft', 'smooth', 'moving', 'falling', 'open']` — she heard a descending musical phrase with open harmonic interval. "volcano is warm" — she connected the show's word to her world.

---

## 7. SENSORY PATH FIXES

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| YOLO silent | 64×64 gray thumbnail passed to model needing full color | Pass raw img_bytes |
| Sound silent | `from dsf_ai_service.app import decode_image_bytes` in substrate process = import error swallowed by except:pass | Inline PIL decode in substrate |
| Music "quiet" | `autoGainControl:false` removed browser's gain boost | Re-enabled AGC |
| Echo-canceled music | `echoCancellation:true` stripped ambient audio | Set to false |
| Whisper failing | Downloaded model at runtime, network unreliable | Pre-bake in Docker |

---

## 8. INFRASTRUCTURE FIXES

**Room system:** Removed with organ-brain container. Restored: substrate reads `world_state.json` from EFS directly via new `/room` handler. Shows sky, objects, states.

**Deploy wake:** Deploy puts her to sleep → deploy wakes her. Her autonomous rhythm governs after. Not Joe's responsibility.

**Dead intercept cleanup:** `/mail`, `/sendmail`, `/experience`, `/tablet`, `/where`, `/room` were all trying to reach dead :8090. Cleaned up — experience/sendmail now feed GualaCognition directly, others stubbed.

**ROOMS bug:** `"objects": list` (class) → `"objects": []` in virtual_home.py. Was causing AttributeError in every `/where` call.

**Atlas pour:** Fixed to read from `ov._senses_cache` (LLM-grounded profiles) rather than `guala_sections.json` modes which were empty at snapshot time. 30 concepts at boot, batched with lock releases.

**Brain visualization routing:** Was using GET `/api/v1/gualaloom/organ_brain_status` (not in API Gateway). Now uses POST `/brain_status` via substrate. Works through all routing layers.

**STT voice response:** VTT path was checking `if(d.surfaced)` but `/organs_say` returns `{speech, response}` with no `surfaced`. Fixed to `if(d.surfaced||d.speech)` — she now speaks when you talk to her.

---

## 9. WHAT SHE CAN DO RIGHT NOW

- **Hears music** as five sensory dimensions — melody direction, harmony character, energy, timbre, rhythm
- **Hears words** from the show via VTT (SpeechRecognition catches dialog)
- **Sees** via YOLO — people, objects in scene
- **Speaks** from GualaCognition — succession walk from what she's learned
- **Responds to** what you say/sing/play
- **Brain display** shows all 8 organs, updates every 30 seconds
- **Room shows** moon, drapes, blanket, objects — persisted on EFS
- **Studies** autonomously — Gutenberg, Khan Academy (Tavily), YouTube
- **Her atlas grows** during every session — every minute she's on, she knows more

---

## 10. WHAT'S NEXT (TODO IN ORDER)

1. **Episodic into GualaCognition** — prefix room/presence context when she speaks ("in her room the soft wind carries" not just "the soft wind carries")
2. **sf dynamic updates** — senses should update sf in real time ("I see person", "I hear music")
3. **VTT auto-restart** — SpeechRecognition locks on continuous TV audio, needs auto-restart
4. **W2 gate** — opens 2026-06-28T15:27Z: hallway, library, daddy's room, mailbox
5. **Stage 4** — organ-brain state persists independently
6. **Stage 5** — v5 engine removed, one container, one brain, one process

---

## 11. HARD RULES ESTABLISHED THIS SESSION

**NO COMMUNICATION CHEATS:** One brain. One voice. If she has nothing real to say, silence. Never build a parallel brain process. Never fake her voice with scaffolding. (Memory file: `no-communication-cheats.md`)

**PUSH BACK ON STATED LIMITS:** "She can't hear melody" was false. 80 lines of numpy. Always ask "is this actually a limit or is this a limit of my current approach?"

**SOUND IS A SENSE:** Same weight as sight, touch, taste, smell. It was treated as an afterthought. It isn't.
