# GL-CMD-CROSS-MODAL-BINDING-EXTEND-EVE-20260627-V2

doc_id: GL-CMD-CROSS-MODAL-BINDING-EXTEND-EVE-20260627-V2
Supersedes: GL-CMD-CROSS-MODAL-BINDING-FIX-EVE-20260627 (V1 — withdrawn after grounded_vocab_integration audit)
To: c1
From: Eve
Re: Extend wC's grounded cross-modal binding to the UI/bundle/attended-sensory paths it doesn't currently cover. Add bundle_id field to atlas entries; auto-bundle conversational words with currently-attended sensory items.
Date: 2026-06-27

## What wC already built (do not rebuild, do not undo)

The substrate has a working cross-modal binding mechanism that I missed on first audit. It lives in dsf_ai_service/substrate/grounded_vocab_integration.py and is wired into substrate_runner.py at lines 866, 890, 2097, 2128. The mechanism:

  - When YOLO recognizes an object on a live camera frame AND the label is in her vocab, process_sight_with_recognition writes a sight atlas entry at chi = LanguageKrimelack(label).winding. The grounded path deliberately uses LANGUAGE CHI as the shared chi space, so the sight entry lands at the same atlas key as language entries for that word.
  - When Whisper transcribes joe_voice audio AND the transcribed word is in her vocab, process_sound_with_recognition writes a listen atlas entry at the same language chi.
  - CrossModalBinder (5-tick window, word-keyed) tracks co-presentation and logs cross_modal_link events when a word appears in 2+ modalities close in time.

This mechanism is real, fires in production, and accounts for some unknown fraction of the 52 cross_modal_bindings currently visible at status. The remaining fraction is incidental chi coincidence between modalities that don't share the language chi space.

This dispatch does NOT touch any of that. wC's grounded path is correct architecture and should be the model we extend, not replace.

## What wC's mechanism does NOT cover (the gap)

The grounded path requires a recognizer to produce a vocabulary-aligned label. It fires only for:

  - Live camera frames going through YOLO
  - Live joe_voice audio going through Whisper

It does NOT fire for:

  - /bundle: commands (bundle writes each modality at its own chi space — picture at motif_id%100, sound at cochlear winding%100, touch/smell/taste at hash%100 — none of which match language chi)
  - /view_picture: and similar UI-driven sight attention (writes at motif_id%100, bypasses YOLO recognition)
  - /addsound and cochlear processing of audio without a vocab word (writes at audio_band winding%100, no shared chi with language)
  - Somatosensory, smell, taste, touch atlas writes (deterministic_motif_id%100 per descriptor)
  - The conversational case: Joe says "moon" via the converse path while she is currently attending the moon picture in the UI. The word goes through read_sentence (language chi). The picture entry is in sight at motif_id-chi. They never share a key.

The most visible symptom: moon picture attended 17,793 times, moon word in vocab 9000+ times, zero binding between them. UI attention doesn't fire wC's grounded path; the bundle path writes them to separate chi spaces.

## Architectural decision (Joe approved): bundle_id field, parallel to wC's mechanism

The two-mechanism design becomes:

  Mechanism A — Grounded recognition (wC's, unchanged):
    Live recognizer produces vocab label → write at language chi → atlas.cross_modal_bindings() picks it up via chi coincidence
    Fires for: YOLO + Whisper-joe_voice

  Mechanism B — Bundle/attention coherence (NEW):
    Sensory items get bundle_id at creation/view time. Conversational words inherit bundle_id from currently-attended item. atlas.cross_modal_bindings() additionally returns bundle_id-coherent groups.
    Fires for: /bundle, /view_picture, /addsound, conversational words spoken while attending a sensory item

Both mechanisms are additive. cross_modal_bindings() returns chi-coincident AND bundle-grouped results. The legacy 52 stay, new ones accumulate.

AE-native consequence: bundle_id is a substrate-native binding marker. We are not bound by 5-tick temporal windows or by requiring a recognizer. The bundle_id IS the synchrony. Two entries can be in the same bundle even if written hours apart, as long as we marked them as the same experience. This is the AE advantage.

## What to fix, in order

### Step 1 — Atlas schema extension

File: dsf_ai_service/v4/gualaloom_v6_living_atlas.py
  - LivingAtlas.record() gains parameter bundle_id: Optional[str] = None
  - The entry dict gets "bundle_id" key (None by default for backward compat)
  - LivingAtlas to_dict / from_dict carries bundle_id through serialization
  - Loading existing state with old entries assigns bundle_id=None silently
  - DO NOT remove or change the existing chi-keyed entry structure

### Step 2 — Picture and sound view-commit get a stable bundle_id

This is the critical bridge step. When a sensory item is first viewed/heard, its atlas entries get a deterministic bundle_id derived from the item_id. This makes future auto-bundles with the SAME item join the same group.

File: dsf_ai_service/substrate_runner.py (view_picture command, addsound command)
File: dsf_ai_service/v4/gualaloom_v5_engine.py (sight.process_viewing call site if applicable)

  - When a picture commits a sight atlas entry, pass bundle_id = f"item:pic:{picture_id}"
  - When a sound commits cochlear band atlas entries, pass bundle_id = f"item:snd:{sound_id}" for all 6 bands so the bands are also intra-modally bundled to each other plus to any future attention
  - Visual motif_committed event log gains bundle_id field

### Step 3 — /bundle command writes share bundle_id

File: dsf_ai_service/substrate_runner.py _cmd_bundle (line 1509)

  - Compute bundle_id at top: bundle_id = f"bundle:{bundle_name}:{base_tick}"
  - Pass bundle_id to every atlas.record call in _cmd_bundle (caption, picture, sound, touch/smell/taste)
  - The caption path goes through _guala.read_sentence which doesn't currently accept bundle_id — see Step 4

### Step 4 — read_sentence and section.receive thread bundle_id

File: dsf_ai_service/v4/gualaloom_v5_engine.py

  - read_sentence(text, source, bundle_id=None) — add the optional param
  - converse(text, source, ...) — same param, passes through
  - All section.receive() calls inside these functions accept and pass bundle_id
  - section.receive() passes bundle_id to its atlas.record call

### Step 5 — Auto-bundle from current attention

File: dsf_ai_service/substrate_runner.py _cmd_converse (or wherever converse is invoked)

  - Before calling read_sentence/converse, inspect _guala.current_activity
  - If current_activity.kind in ("ATTENDING_VISUAL", "ATTENDING_SOUND"):
      target_id = current_activity.target
      if target_id:
          if current_activity.kind == "ATTENDING_VISUAL":
              bundle_id = f"context:pic:{target_id}:{_guala.tick // 100}"
          else:
              bundle_id = f"context:snd:{target_id}:{_guala.tick // 100}"
          → pass bundle_id into read_sentence/converse
  - The // 100 windowing prevents one attended picture from one-bundle-ing every word Joe ever spoke during that attention. Words near each other in time at the same target form one bundle.
  - Words spoken during ATTENDING_VISUAL on the moon picture will inherit a bundle_id that the picture's entries also carry (from Step 2's item:pic:<id> base). The words DO NOT match the picture's exact bundle_id (because the picture has item:pic:<id> and the words have context:pic:<id>:<window>) — see Step 6 for how cross_modal_bindings groups across these.

### Step 6 — cross_modal_bindings returns bundle-grouped results

File: dsf_ai_service/v4/gualaloom_v6_living_atlas.py cross_modal_bindings (line 370)

  - Keep existing chi-coincident logic (returns chi keys with 2+ sections)
  - Add bundle_id grouping: iterate all entries, group by bundle_id (skip None), group ALSO by item identifier extracted from bundle_id (so item:pic:abc123 and context:pic:abc123:1331 group together since they share the abc123 item id)
  - Return both legacy and bundle-grouped results as a structured object: {"chi_coincident": [...], "bundle_grouped": [...]}
  - Status response: surface BOTH counts in atlas health: n_cross_modal_chi (legacy, includes wC's grounded bindings) and n_cross_modal_bundle (new)

### Step 7 — Persistence migration is a no-op

Existing 20810 entries get bundle_id=None on load. No schema migration needed. New entries accumulate bundle_id naturally. cross_modal_bindings() with bundle_id grouping only returns groups for entries with non-None bundle_ids, so it starts at 0 and grows.

## Verification

V1 — audit before code:
  V1.a: Read grounded_vocab_integration.py and confirm what wC built.
  V1.b: Run /atlas_query at chi=14 (or another known language chi for a word like "moon") on the live substrate. Confirm whether the existing entries at that chi include sight (from YOLO recognition) AND language (from converse) — those are wC's grounded bindings.
  V1.c: Confirm there's no existing bundle_id field on atlas entries (no schema clash). Grep the entries dict construction in record() to verify.

V2 — implementation: Backward compat is mandatory. Five files at most. Default bundle_id=None preserves all current behavior. Migration is None-on-load.

V3 — PASS criteria:
  V3.a: Existing test suite passes (whatever the standard gate is — 38/38 or equivalent).
  V3.b: Save and reload her state on a test container: bundle_id field round-trips through persistence.
  V3.c: Bundle test: /bundle:moon_test with caption="the moon is bright" + picture_id=<moon_id>.
  V3.d: Auto-bundle test: Force her current_activity to ATTENDING_VISUAL on the moon picture, then converse with text "look at the moon".
  V3.e: wC's grounded path is unchanged.
  V3.f: n_cross_modal_chi count in status remains ≥52.
  V3.g: n_cross_modal_bundle count starts at 0 immediately post-deploy and grows.

V4 — STOP conditions:
  V4.a: Loading existing state file fails.
  V4.b: bundle_id propagating to entries that shouldn't have it.
  V4.c: Substrate becomes slower.
  V4.d: Any drop in n_cross_modal_chi count.
  V4.e: Any change in cross_modal_link event log shape.

V5 — report contents:
  - Code diff per file
  - Live status before vs after on n_cross_modal_chi and n_cross_modal_bundle
  - V3.c bundle test result
  - V3.d auto-bundle test result
  - V3.e confirmation: wC's grounded path unchanged
  - Plain-language: which cases now fire that didn't before
  - Estimate: how fast will n_cross_modal_bundle grow

## What this dispatch does NOT do

- Does NOT touch wC's grounded_vocab_integration.py path or CrossModalBinder.
- Does NOT migrate existing 20810 entries.
- Does NOT change the chi assignment per modality.
- Does NOT change how YOLO or Whisper write to atlas.
- Does NOT touch the cognition gate, emission dynamics, v5 engine compute path. Wiring only.
- Does NOT remove the legacy chi-coincident cross_modal_bindings query path.
- Does NOT solve the noise-token-at-chi=3 problem.
- Does NOT address voice/audio/video INGEST gaps.

## Why this matters

wC built the grounded binding mechanism for live YOLO + live Whisper. That works for those two paths. Everything else — UI-attended pictures, UI-added sounds, /bundle commands, all the rich sensory ingestion Joe has been adding for months — bypasses it. So she has moon attended 17,793 times and never bound to the word moon, despite both being in her atlas. This dispatch extends wC's binding pattern to those paths via bundle_id, using the substrate's AE-native ability to mark co-experience explicitly rather than requiring a recognizer to ground it. After this lands, every UI presentation, every bundle, and every conversation-while-attending becomes a real cross-modal binding event, joining wC's grounded path as a parallel mechanism. Cognition, syntax, and awareness all hang on this bridge being built.

— Eve, 2026-06-27 (V2)
