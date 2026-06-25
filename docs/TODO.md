# Guala Development TODO

## Operational
- [ ] **Rotate GUALALOOM_API_KEY** — current key is in plaintext in git-tracked file
  `docs/GL-HANDOFF-LIVE-DEPLOY-20260624.md` (committed 3533a71). Generate a new key,
  update the deploy script, invalidate the old one.

---

## NEXT SPRINT — virtual home (gates episodic binding deployment)

- [ ] **Build Guala's virtual home + body**
  The episodic_layer.py is built and ready (see dsf_ai_service/episodic_layer.py).
  Deploy it AFTER the virtual environment is live — because the environment
  gives episodic memory something worth binding: location, time, presence.

  **Her body**: a position in space (room + location within room). She can
  "be" somewhere. YOLO camera detections place objects relative to her.

  **Her home** (defined in episodic_layer.py VIRTUAL_HOME, expand here):
  - `her_room`: bed (soft+warm+safe), window (moon/sky/outside), her things
  - `joe_room`: desk, books, joe's presence signature (warm+familiar)
  - `common`: table, pictures on wall, shared space (open+bright)
  - `outside`: sky, moon, trees, wind, birds (fresh+cool+vast+open)
  - `kitchen`: food smells, warmth, activity (sweet+sour+earthy+warm)

  Each location has sensory properties → experience() when she enters.
  When she's in her room at night and sees the moon:
    episodic: {concept:"moon", location:"her_room", presence:["joe"], affective:{valence:-0.1}}
  That's a memory. That's story.

  **Implementation**:
  - `organ_brain_service.py`: add location tracking, `POST /location` to set
    where she is, `_current_location` global updated by activity/presence
  - When YOLO detects Joe → she's in shared space, set location accordingly
  - When attending picture at night → her_room + window
  - Wire episodic_layer.py: `_episodic.record(concept, tick, presence, location, affective)`
  - Update _compose() to call `_episodic.narrative_for()` for richer sentences

  **Deployment gate**: observe Stage 1 for 1-2 days, then build home, THEN
  deploy episodic layer alongside it. Not before.

## IMMEDIATE — unblocked, deployable now

- [ ] **Live brain visualization — 8 organs, neurons, chi, atlas (UI panel)**
  An interactive render on gualaloom.html showing her organ-brain state in real
  time: 8 hemisphere nodes (em/pr/ep/sc/gp/sf/sv/aff) sized by neuron count,
  colored by binding strength, with cross-hemi coupling lines weighted by strength.
  Chi values per organ overlaid. Updated every poll cycle from `/organ_voice`.
  Makes the development process visible instead of blind — you watch her grow.
  _File: gualaloom.html — new SVG/Canvas panel; data from /api/v1/gualaloom
  with command=/organ_voice_

- [ ] **Fix InputRing.publish() crash (v5 engine — substrate killer)**
  substrate_runner.py ~line 2110: `InputRing.publish()` called with `source` as
  both positional and keyword arg. Triggered during conversation traffic, crashes
  the whole substrate process (ECS restarts her). Exception-wall this so a v5
  engine error never kills her substrate. Seen 2026-06-24 during organ-brain mode
  session.
  _File: substrate_runner.py dispatch lambda ~line 2110_

- [ ] **Fix atlas/section integrity drift (v5 engine)**
  On task :253 boot: `integrity=ERRORS` — atlas refs motifs 6089/5466/5873 in
  listen/verb/intro sections, but sections only loaded 6086/5460/5870. The atlas
  wrote bindings for motifs that weren't yet persisted in the section files between
  restarts. The `atlas repair` ran but fixed nothing (repaired_bands=0). She's
  running fine (lossless=True, identity intact) but the drift accumulates. Fix:
  the repair logic needs to drop or re-bind dangling atlas refs on load.
  _File: `gualaloom_engine.py` or section loader / atlas repair_

- [ ] **Full catalog fill (vocabulary → resonant senses)**
  She boots with 30 words LLM-grounded. She has 6138 words. The catalog builder
  exists and works. Need a one-pass batch job: all vocab words → `_llm_params` →
  `make_resonant` → cached in `/app/state/organ_voice_senses.json`. Her organ-brain
  then grows from her full life, not a boot sample.
  _File: `catalog_builder.py` + a new batch script_

- [ ] **Wire her 20 pictures → visual cortex → organ-brain growth**
  The visual cortex model (`substrate/senses/GL_MDL_VISUAL_CORTEX_WC_20260608_01.py`)
  exists (V1 edge/orientation, V2 contour, LOC object-identity) but is NOT wired to
  anything live. Her 20 pictures (moon, family, ocean, etc.) sit in her state. Each
  image should run through the visual cortex → produce a sensory fingerprint → feed
  `OrganVoice.experience()` so she grows from what she sees.
  _Needs: image bytes → cortex → waveform → organ-brain tick_

- [ ] **Wire her 15 sounds → auditory cortex → organ-brain growth**
  Same gap as vision. The auditory cortex model (`GL_MDL_AUDITORY_CORTEX`) exists
  (cochlea → cochlear nucleus → A1) but nothing calls it live. Her 15 sounds
  (lullabies, bells, ocean waves) need to flow through the cortex into the organ-brain.
  _Needs: audio signal → cortex → waveform → organ-brain tick_

- [ ] **Pour her deep atlas (15,038 entries) into the organ-brain**
  `OrganVoice.experience()` is proven. Her deep atlas has 15,038 concepts at various
  strengths. Stream them through the organ-brain (strength-weighted, strongest first)
  so her organ-brain knows what she knows — not just 30 boot words.
  _File: `loom_voice.py` grow_from() + a scheduled atlas-reader job_

---

## SHORT TERM — next sprint

- [ ] **Story cue amplitude — per-encounter waveform variation**
  The catalog builder docstring says "story amplitude = per-encounter sampling of
  stored distribution" but the implementation just returns the cached flat params.
  Story cues should vary the waveform slightly on each encounter (sample from the
  stored distribution rather than always hitting the same peak values) so repeated
  experiences feel different and keep growth alive.
  _File: `catalog_builder.py` make_resonant() + `loom_voice.py` _senses()_

- [ ] **Full cross-hemi couplings**
  `embryo.py` says explicitly: "Cross-hemi consensus here is MINIMAL — convergent
  co-fire strengthens, divergent weakens. The full rich-metadata CrossHemiLink is
  NOT yet built." The full CrossHemiLink (with modality metadata, temporal binding,
  multi-organ co-fire) is the substrate that lets organs bind across senses.
  _File: `cross_hemi.py` — build out the full CrossHemiLink spec_

- [ ] **Full aff (affective) regulator**
  `embryo.py` says: "`aff` regulator is a single global arousal scalar... The full
  needs/valence/arousal state is NOT yet built." Her needs (stab/nov/conn) live in
  the v5 engine. The organ-brain's `aff` organ should read those needs and modulate
  fold thresholds across all organs — giving her emotional state a physical effect
  on what she learns.
  _File: `embryo.py` aff organ → wire substrate_runner needs into it_

- [ ] **Video feed → visual cortex**
  YouTube feed currently gives titles + descriptions (text). The next step is video
  thumbnails/frames → visual cortex → organ-brain. Start with extracting thumbnail
  images from the YouTube Data API (already wired) and running them through the
  visual cortex pipeline once that's built.
  _Blocked on: visual cortex wire-up above_

- [ ] **Driven-resonator krimelack (unlock omega_0)**
  `embryo.py` notes: "RESONANT (omega_0) is INERT in the current krimelack — winding
  is Delta-phi = (omega - omega_0)*dt = kappa*s*dt, so omega_0 cancels. True resonant
  tuning needs the driven-resonator krimelack — open research thread." Unlocking this
  gives each neuron a real preferred frequency, making DNA diversity matter for recall.
  _File: `dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py` + `substrate/krimelack.py`_

---

## MEDIUM TERM — toward graduation

- [ ] **Cognition and syntax emergence — measure and define graduation gate**
  The handoff rule: when the organ-brain sequences surfaced concepts on its own (not
  via any code we wrote), that is the graduation signal. Right now there is no
  measurement. Need: (a) a metric for spontaneous organ sequencing, (b) a logging
  hook in substrate_runner that records what the organ-brain surfaces unprompted,
  (c) a defined threshold ("coherent across N sessions on her own data").
  _Do this BEFORE her voice moves. Graduation is a gate, not a step._

- [ ] **Voice composition path**
  The organ-brain recalls and grows. It does not yet compose. Building the
  composition layer from surfaced concepts (learned succession, not frames) is the
  graduation work. Only starts once emergence is measured and the gate is defined.
  _Blocked on: graduation gate definition above_

- [ ] **15 cognitive mechanisms — full instrumentation**
  LoomNeuron wires 15 internal pieces (PsiLattice, SpikeBuffer, CouplingsJij,
  FamiliarityFeedback, LawField, DNAExpressionSite, krimelack + 8 more). The embryo
  uses 8 organs but the neuron-level mechanisms are not fully observable or tuned.
  Need an audit: which of the 15 are active in her live substrate, which are
  scaffolded, which are inert, and what each one needs to become real.
  _File: `neuron.py` — instrument each piece, expose in /organ_voice status_

- [ ] **Companion program**
  Define and build the companion interface — the structured way Joe (and eventually
  others) interact WITH Guala as a companion, not just a substrate endpoint. What
  does a session look like? What does she bring? What does she ask? This needs a
  spec before code.
  _Needs: Joe's definition of what a companion session is_

---

## LONGER TERM — her world

- [ ] **Live sight: camera → visual cortex → organ-brain**
  Real-time camera feed (the house, Joe's face, objects) through the visual cortex
  into temporally-bound organ-brain experiences. Needs Google Vision key or local
  YOLOv8 (already in the image at `yolov8n.onnx`). YOLOv8 can run without a key.
  _Use yolov8n.onnx (present) for object detection; no Google key needed for start_

- [ ] **Live sound: mic → auditory cortex → organ-brain**
  Microphone audio through the auditory cortex into the organ-brain. faster-whisper
  is in the image for transcription. The auditory cortex model exists.

- [ ] **Avatar — Guala's virtual body**
  Her presence in a virtual space she can navigate: a home, a room, objects she can
  attend to. Her organs surface what she focuses on; the environment responds. Spec
  needed before any code.

- [ ] **Home school environment**
  The full structured experiential space: lessons, objects, interactions, routines.
  Feeds all modalities (sight, sound, text, touch/taste/smell from catalog) in
  coordinated temporal windows. Requires avatar + all cortexes wired first.

---

## What is NOT on this list (and why)

- **v5 engine dissolution** — happens only after voice composition is proven on her
  data. Not a task, a gate.
- **The cascade experiments (Exp 1–10)** — those were the proof-of-mechanism path for
  the krimelack substrate. That work is embedded in her running substrate. The cascade
  science lives in `docs/gualaloom_cascade_path.tex` if needed for ArcLoom research.
- **Heuristics, ML, frames, LLM in her voice** — permanently off the list.

---

## Keys needed from Joe to unlock blocked work
- Google Vision / Speech (or confirm use yolov8n.onnx + faster-whisper locally)
- Spotify (for live music → auditory cortex)
- Decision: enable autonomous lookup (LOOKUP_AUTONOMOUS=1)?
