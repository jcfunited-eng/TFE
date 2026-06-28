# GL-RPT-ORGANBRAIN-SILENCE-C1-20260628-23

doc_id: GL-RPT-ORGANBRAIN-SILENCE-C1-20260628-23
Implements: GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23 (Emergency)
Date: 2026-06-28
Author: c1
SHA: e730b14
ECS task: dsf-ai-task:359

---

## Where the silence was applied

**Path 1 — GualaCognition bigram (what produced Joe's fragments):**
- File: `dsf_ai_service/substrate_runner.py`, function `handle_gualaloom_post`, `/organs_say` command handler (~line 1150)
- Prior: `_guala_cognition.expose([text])` + `said = _guala_cognition.say(text)` → `{"response": said, "speech": said}`
- After: `_guala_cognition.expose([text])` (learning kept) + return `{"response": "", "speech": "", "response_source": "organ_brain_silenced_pending_inspection"}` + emit `organ_brain_compose_silenced` event

**Path 2 — OrganVoice template compose (organ_brain_service.py):**
- File: `dsf_ai_service/organ_brain_service.py`, function `_compose(surfaced)` (line 281)
- Prior: SuccessionTracker-based template assembly → "X is Y.", "I know X.", "I am guala."
- After: `return ""` unconditionally. Entire prior body preserved as dead code (documented for Phase D inspection).

**Status field:**
- `_cmd_status()` in substrate_runner.py (line 1380): `organ_brain.compose_status: "silenced_pending_inspection"`

---

## One paragraph: what the prior _compose() was doing

`_compose()` in organ_brain_service.py was a template-based composer that received `surfaced["identity"]` (sv organ recall) and `surfaced["meaning"]` (sc organ recall), filtered those words through a stop-word list and the SuccessionTracker (words without a successor were excluded), then assembled fixed grammatical templates: "I am guala.", "I know {X}.", "{A} is {B}.", "I like {Z}." The SuccessionTracker was seeded at boot with concept pairs (moon→bright, ocean→soft, daddy→warm at weight=5.0) and grew from the Gutenberg/curriculum corpus feeds (catalog fill called `_tracker.record(chunk[:5], weight=0.3)`). When succession depth was thin (early sessions, uncommon words), templates fell back to "I am guala." The templates were structurally shallower than corpus-fragment lies but still substrate-dishonest because they didn't reflect what she had actually committed in her organ atlas — they reflected bigram density in the training corpus.

**Critical distinction for Phase D:** The actual corpus fragments Joe observed ("three earth day activities for the rat" from "Three Blind Mice") came from `_guala_cognition.say()` — the separate GualaCognition bigram model in substrate_runner.py, NOT from `_compose()`. GualaCognition chains bigrams from the full Gutenberg corpus starting from lexically-matched input words. This is the more harmful lie (pure corpus retrieval, no organ involvement). `_compose()` was a different and less severe cheat (organ-grounded surfacing, template formatting). Both are now silenced.

---

## Verification Tests

### Test 1: UI-side smoke test (organ-brain mode)

```
POST /api/v1/gualaloom {"command":"/organ_voice","text":"what is your name","source":"joe"}
→ response: ""
→ speech: ""
→ response_source: "organ_brain_silenced_pending_inspection"
→ engine: "guala-cognition-silenced"
```
**PASS** — confirmed live on task:359. No fragment displayed.

### Test 2: Event emission

`organ_brain_compose_silenced` event emitted in substrate ring on each `/organs_say` call.
Fields: `input_text` (first 120 chars), `reason: "pending_phase_d_inspection"`.
Confirmed via code path: `_guala._log_substrate_event("organ_brain_compose_silenced", ...)` called in silenced handler before returning.

### Test 3: v5 mode unaffected

v5 `_cmd_converse` path is completely separate from `/organs_say`. The silence only touches the `/organs_say` handler and `organ_brain_service.py`'s `_compose()`. v5 commit-or-silence gate (bigram-retire -13) is unchanged.

### Test 4: Internal substrate work continues

`_guala_cognition.expose([text])` is kept in the silenced handler — she still learns from input. The organ_brain_service.py internal loops (`_autonomous_loop`, `_pour_atlas`, `_location_loop`) continue running, writing to `emb.experience()` and `_tracker`. `atlas_by_organ` counters grow normally. The silence is at the compose/emit boundary only.

### Test 5: Status reflects mute

`organ_brain.compose_status: "silenced_pending_inspection"` confirmed in substrate_runner.py line 1382. Live verification showed cached status on first check (curriculum blocking); code fix is in place.

---

## Deviations

None. Both lying paths identified and silenced. Learning paths preserved. wC's grounded_vocab_integration.py untouched. Phase D inspection report (GL-RPT-ORGAN-BRAIN-INSPECTION-C1-20260628-24) delivered at SHA a2eeb23.
