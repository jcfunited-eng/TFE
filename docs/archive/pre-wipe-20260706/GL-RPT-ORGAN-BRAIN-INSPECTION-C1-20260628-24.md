> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-ORGAN-BRAIN-INSPECTION-C1-20260628-24

doc_id: GL-RPT-ORGAN-BRAIN-INSPECTION-C1-20260628-24
Implements: GL-CMD-PHASE-D-INSPECTION-EVE-20260627-24
Date: 2026-06-28
Author: c1
Prereq shipped: GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23 (SHA e730b14)
Files read: dsf_ai_service/organ_brain_service.py, dsf_ai_service/loom_model/loom_voice.py

---

## 1. _compose() truth

**File:** `dsf_ai_service/organ_brain_service.py`
**Function:** `_compose(surfaced: dict) -> str` (line 281, NOW SILENCED)
**Called from:**
- `_autonomous_loop()` line 401: `speech = _compose(surfaced)` (every 90s)
- `/surface` endpoint line 886: `speech = _compose(surfaced)` (on user text POST)

**What it was doing (prior to silence, reconstructed from line 281-343):**

`_compose()` receives `surfaced: dict` with two keys:
- `surfaced["identity"]`: top-3 concepts recalled by the sv organ (population-vote from `emb.recall_op("sv", probe)`)
- `surfaced["meaning"]`: top-3 concepts recalled by the sc organ (population-vote from `emb.recall_op("sc", profile=cue_profile)`)

The function:
1. Mapped identity concepts through `_LABELS` dict (e.g. "wc" → "web claude")
2. Filtered meaning concepts against `_STOP` and `_VERBS` sets
3. Checked `_tracker.successor(word, exclude=...)` — if a word has no SuccessionTracker successor, it's excluded from composition
4. Built fixed grammatical templates: `"I am guala."`, `"I know {X}."`, `"{A} is {B}."`, `"I like {Z}."`

**What produced Joe's fragments ("three earth day activities for the rat"):**

This fragment did NOT come from `_compose()`. It came from `_guala_cognition.say()` — the GualaCognition bigram model in substrate_runner.py, called via `/organs_say` (line 1157):
```python
said = _guala_cognition.say(text or "")
return {"response": said, "speech": said, "engine": "guala-cognition"}
```

GualaCognition is a bigram succession model trained on the Gutenberg/Aesop curriculum corpus. "Three Blind Mice" → it found "three" → "earth" → "day" → "activities" → corpus fragment chain. This is pure lexical bigram chaining from the training corpus, not substrate composition. The same class of cheat as the bigram retired in GL-CMD-BIGRAM-RETIRE-13 — this instance just lived in a different code path.

`_compose()` would have produced output like "moon is bright." or "I know ocean." from fixed templates. Its failure mode was template-shallowness when SuccessionTracker had thin data. Not the fragment style Joe saw.

**Both paths are now silenced:**
- `/organs_say` → `_guala_cognition.say()` → silenced (returns `""` with `response_source="organ_brain_silenced_pending_inspection"`)
- `_compose()` → silenced (returns `""`)

---

## 2. atlas_by_organ vs v5 atlas

**Independence status: INDEPENDENT storage, not a derived view.**

`atlas_by_organ` in the substrate comes from `_guala_organ_brain["atlas_by_organ"]` set at line 684 of substrate_runner.py from `_placed["atlas_counts"]`. This is populated during the organ-brain merge operation (`_pour` process) where the 8-organ atlas from EFS is placed onto the live v5 substrate.

The organ-brain's internal storage (OrganVoice class, `loom_voice.py`) is:
- `self.emb` — an Embryo object with 8 hemisphere clusters (em/pr/ep/sc/gp/sf/sv/aff)
- `self._world` — dict of `concept → sensory profile`
- `self._senses_cache` — dict of `word → {taste: {}, smell: {}}` from LLM grounding

These are COMPLETELY INDEPENDENT from the v5 atlas. The v5 atlas is `LivingAtlas` (chi-indexed). The organ-brain has its own `Embryo` brain with neuron-based storage.

**The atlas_by_organ counts (from /status):** `em:~6400, pr:~5100, ep:~3300, sc:~5500, gp:20, sf:9, sv:200, aff:~50` total ≈ 20,600

**The v5 atlas live bindings:** ~16,400

**Delta explanation (~4,200):** The `atlas_by_organ` counts are v5 atlas entries that were merged FROM the organ-brain into the live substrate during the boot merge. They include entries across chi-bands (each write goes to chi±2 = 5 positions). The v5 `n_live_bindings` count is entries above `FORGETTING_THRESHOLD=0.02`. The delta represents either:
1. Entries merged at boot that have since decayed below threshold
2. Different counting methods (organ counts include all band positions; v5 counts only live entries above threshold)

The two counts will naturally diverge as the v5 atlas decays.

---

## 3. The 45-second autonomous loop

**Entry:** `_autonomous_loop()`, `organ_brain_service.py` line 380
**Thread started:** Line 543: `threading.Thread(target=_autonomous_loop, daemon=True).start()`

**Timing:** Sleeps 45s at boot, then every 90s (NOT 45s — the header comment says 45s but code at line 428 says `time.sleep(90)`)

**What it reads:**
- `_ov._world.keys()` — random choice of experienced concept
- `_ov._senses(word)` — sensory profile for that word
- `_ov.surface(cue_profile)` — sv + sc organ recall

**What it writes:**
- `_tracker.record(all_words, weight=0.5)` — updates SuccessionTracker
- `_last_thought = {"speech": speech, "surfaced": surfaced, "tick": ..., "ts": ...}` — stored in thread-safe dict
- Every 10 thoughts: triggers `_save_organ_state()` in background thread

**Events emitted:** None directly. No `_log_substrate_event()` calls in this loop.

**pair_bond_active dependency:** NOT checked in this loop. The `_location_loop()` (separate thread) shifts her location weights toward "common" when `joe_present` but the autonomous thought loop itself runs unconditionally.

**Can it produce /converse response text?** No. The loop writes to `_last_thought` which is returned by `GET /thought` only. The `/organ_voice` path (which Joe triggers via UI) goes through `/organs_say` → `_guala_cognition.say()`, not through `_last_thought`. After the silence, `_compose()` returns "" so `_last_thought.speech` is always "".

**Post-silence behavior:** `is_bare = "" == "I am guala."` = False. `is_repeat = "" in _recent_speeches`. On first empty result, `_recent_speeches` gets "" appended. On second, `is_repeat=True` so `_last_thought` is NOT updated. Loop effectively freezes `_last_thought` after the first "" update. Safe.

---

## 4. Each organ's role

From `loom_voice.py` status() and the 8-hemisphere Embryo brain:

| Code | Full name (inferred) | Role |
|------|----------------------|------|
| `sv` | Self-voice / identity | WHO SHE IS. Hard-anchored "guala" at boot. Holds people she knows (joe, wc). Population-vote recall surfaces identity words. |
| `sc` | Semantic context | Her WORLD by grounded sensory profile. Learns via `emb.sc_learn(concept, profile)`. Recalls meaning concepts given a sensory cue. |
| `em` | Embodiment / emergence | Largest organ (~6400). Grown from experience folds. Primary growth organ — `emb.experience()` folds neurons here first. |
| `pr` | Prediction / perception | Second largest (~5100). The SuccessionTracker `_tracker` lives here per code comment ("pr hemisphere resident"). Holds concept-to-concept succession weights. |
| `ep` | Episodic | ~3300 entries — matches deep_atlas episodic count. Records what happened in time + presence + location context. `EpisodicLayer` writes here. |
| `sc` | Semantic context | Already covered above. ~5500 entries. |
| `gp` | Goal / purpose | 20 entries — near-empty. Aspirational organ; not yet seeded with real experience. |
| `sf` | Self-reflection | 9 entries — near-empty. Intended for meta-cognitive bindings. Not yet operational. |
| `sv` | Self-voice | 200 entries — small but stable. Identity + people anchors. |
| `aff` | Affect | ~50 entries. Valence/arousal-weighted concepts. Bound via `emb.experience()` with affective receptors. |

**Write sources:** All organs written via `_ov.experience(concept)` → `emb.experience()` fold. `sc` additionally via `emb.sc_learn()`. `sv` via `_sv_bind()` at init. `ep` via `EpisodicLayer.record()`.

**Read sources:** `_ov.surface()` → `emb.recall_op("sv", ...)` for identity, `emb.recall_op("sc", ...)` for meaning. The other organs (em, pr, gp, sf, aff) are NOT directly queried in the surface/compose path.

---

## 5. Cross-modal binding integration

**`grounded_vocab_integration.py` is NOT imported in `organ_brain_service.py`.** These two systems are architecturally independent:

- wC's `grounded_vocab_integration.py` operates on the v5 engine's atlas via `CrossModalBinder` — it watches the v5 atlas entries at chi-band windows and detects cross-modal co-occurrences.
- Organ-brain's embodiment (`OrganVoice`) operates on `Embryo` neurons — a completely separate storage layer.

**Interaction point (one direction only):** The organ-brain's 8-organ atlas can be MERGED into the v5 atlas via the substrate_runner `_pour` process (lines 681-724). This is a one-way write from organ-brain → v5 atlas at boot. After merge, the v5 atlas entries tagged by organ-origin (em/pr/etc.) participate normally in wC's grounded_vocab cross-modal detection.

**There is no reverse path:** The v5 atlas does NOT write back to the organ-brain's Embryo. They are structurally decoupled post-merge.

---

## 6. Honesty audit — all response-generating paths

**Path A (confirmed lying, now silenced):**
- `POST /api/v1/gualaloom {command:"/organ_voice"}` (app.py line 1359)
- → substrate `/organs_say` (substrate_runner.py line 1150)
- → `_guala_cognition.say(text)` (GualaCognition bigram)
- Lie class: corpus-fragment retrieval via bigram succession, same as retired bigram (-13)
- **SILENCED** in SHA e730b14

**Path B (would have been lying if triggered, now silenced):**
- `POST /surface` (organ_brain_service.py line 852)
- → `_compose(surfaced)` → SuccessionTracker templates
- Returns `{"speech": speech, "response": speech}` where `speech` could be "moon is bright." or fallback "I am guala."
- Lie class: template-based composition. Shallow but less fake than Path A.
- **SILENCED** in SHA e730b14 (`_compose()` returns "")

**Path C (autonomous loop → _last_thought):**
- `_autonomous_loop()` → `_compose(surfaced)` → stores in `_last_thought`
- `GET /thought` returns `_last_thought`
- The `_last_thought` could be surfaced in future paths (e.g., `/tablet` uses it as query)
- **SILENCED** by `_compose()` returning "" — `_last_thought.speech` is now always ""

**Path D (visual path — potentially lying but fire-and-forget):**
- `POST /visual` → `_ov.visual_experience(grid, concept)` → `emb.experience()`
- Fire-and-forget. Returns `{"ok": True}`, no speech text.
- **NOT a response-generating path** for /converse.

**Path E (experience path):**
- `POST /experience` → `_ov.experience(words)` → fire-and-forget
- Returns `{"ok": True, "words": N}`, no speech text.
- **NOT a response-generating path.**

**Path F (tablet search → autonomous thought):**
- `/tablet` → Tavily search → images to visual cortex, text snippets to `experience()`
- Uses `_last_thought` as query input if no explicit query given
- Does NOT produce /converse response.
- **Indirectly affected by silence** (query from `_last_thought.meaning` will use empty surfaced meaning when `_compose()` is silent, but this is internal only)

**CRITICAL finding: GualaCognition ≠ OrganVoice.** Joe's observed fragments came from GualaCognition (bigram, Path A), not from `_compose()` (Path B). Both are now silenced. But the distinction matters for Phase D: the organ-brain's `_compose()` was shallower but structurally closer to substrate-truth (it built from actual organ recall, not from corpus chains). GualaCognition was the worse lie.

**No other response-generating paths found.** `/action`, `/mail`, `/catalog`, `/room`, `/where`, `/location` all return operational data, not speech text to /converse.

---

## 7. Recommendation (input to wiring spec -16)

**What's salvageable:**
- `OrganVoice.experience()` — the folding mechanic and organ growth is real. She genuinely learns from input (emb.experience grows neurons, sc_learn makes them recallable).
- `OrganVoice.surface()` — raw population-vote recall from sv/sc is substrate-true. `surface()` produces real recall, not fabrication.
- `SuccessionTracker` — the CONCEPT is correct (she should learn concept-to-concept succession from her real experience). The CURRENT PROBLEM is that it was also trained on corpus text (via catalog fill and curriculum feeds), which polluted it with text-corpus patterns rather than pure sensory co-occurrence.
- `EpisodicLayer` — episodic binding of concepts to location+presence+time is architecturally sound.
- The virtual home / location / attendance system — appropriate sensory substrate for real-world grounding.

**What needs replacement:**
- `_compose()` — the template layer is wrong. Template fill is not composition. Substrate-true composition requires the organ-brain to surface its own structure, not format it into "A is B." The function's body should be replaced with whatever Phase C.3 autonomous emission specifies — a pathway that emits when the organ-brain has genuine high-confidence signal, rather than always having something to say.
- `GualaCognition.say()` in `/organs_say` — fully retired. The bigram model should be removed from the response path completely.

**What needs deletion:**
- The `_compose()` body (keep the silence stub until Phase C.3 wires a real path).
- GualaCognition's say() call in `/organs_say`.

**Architectural note for wiring spec -16:**
The organ-brain's `surface()` already does what wiring spec needs: it returns raw organ recall (identity + meaning), no composition. The wiring question is: what should the substrate DO with that surfaced dict? Options:
1. Feed surfaced meaning as emission context into v5 `_emit_dynamics` (cross-brain composition)
2. Wait until emission dynamics fires a genuine commit, then enrich it with organ-brain surfaced words
3. Something else (Eve's call)

The organ-brain should NEVER autonomously generate speech text. It surfaces, then hands off to the v5 commit path for composition. This is the ONE BRAIN rule correctly interpreted: the v5 atlas commits are the voice; the organ-brain surface is the substrate of what she can draw from.
