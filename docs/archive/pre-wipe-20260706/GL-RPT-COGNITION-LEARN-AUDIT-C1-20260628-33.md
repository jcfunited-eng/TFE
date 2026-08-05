> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-COGNITION-LEARN-AUDIT-C1-20260628-33

doc_id: GL-RPT-COGNITION-LEARN-AUDIT-C1-20260628-33
Implements: GL-CMD-COGNITION-LEARN-AUDIT-EVE-20260628-33
Date: 2026-06-28
Author: c1
SHA: read-only (4e65002 baseline)
Files read: substrate_runner.py, loom_model/loom_cognition.py

---

## What GualaCognition.expose() actually builds

`expose(sentences: List[str])` trains a bigram word-succession model:
- `self.trans[word_a][word_b] += 1` — pairwise co-occurrence counts
- `self.starts[first_word] += 1` — sentence-opener frequency
- `self.vocab.update(words)` — set of seen words

**No other state.** This is a pure bigram frequency table. There is no embedding,
no chi, no atlas binding, no sensory grounding. The only consumer of this state is
`say()` (silenced) via `compose()`. `self.vocab` is also read at lines 2101/2121
for instrumentation (corpus load stats: `organ_vocab_before`/`after`). That
instrumentation is not load-bearing — removing `expose()` calls would just make
those counters zero.

---

## Call sites

### Site 1 — Curriculum + Worldfeed (line 350 in `_curriculum_feed_chunk`)

**Source data:** `sent` — one sentence from a Gutenberg/Aesop book (curriculum) or
a Tavily/Khan web feed (worldfeed). Examples: "The fox saw the grapes and wanted
them." / "Animals need water to survive."

**Current behavior:** `_cognition_learn(sent)` → `_guala_cognition.expose([clean_sentence])`.
Trains bigram on every sentence from the 10-book curriculum and all worldfeed content.

**v5 atlas behavior:** YES — `_guala.read_sentence(sent, source=event_type, ...)` is
called in the SAME loop iteration, BEFORE `_cognition_learn`. The sentence already
goes to v5 atlas. `_cognition_learn` is a second parallel write to the bigram.

**Substrate-true alternative:** `_cognition_learn` call can be deleted. v5 atlas
write via `read_sentence()` already handles all curriculum input correctly with full
section routing, episode binding, and sensory grounding.

**Downstream consumer:** none. Bigram `trans`/`starts`/`vocab` — no functional
reader after `say()` silenced.

**Disposition: DELETE the `_cognition_learn(sent)` call.**

---

### Site 2 — Lookup grounding (line 385 in `_lookup_and_ground`)

**Source data:** `desc` — one OpenAI-generated child-safe description sentence.
Example: "A whale is a very large mammal that lives in the ocean."

**Current behavior:** `_cognition_learn(desc)` → trains bigram with one LLM-generated
description sentence.

**v5 atlas behavior:** YES — `_guala.read_sentence(desc, source="lookup")` called
immediately before on line 384. Same sentence goes to v5 atlas first.

**Substrate-true alternative:** Delete `_cognition_learn(desc)`. v5 atlas already
receives this.

**Downstream consumer:** none.

**Disposition: DELETE.**

---

### Site 3 — Sight recognition InputRing drain (line 911)

**Source data:** `_scene = " ".join(b.get("word","") for b in bindings)` — space-joined
YOLO class labels from camera frame. Example: "person cat clock" (from Little Einsteins
episode; wC's `process_sight_with_recognition` ran YOLO). Typically 1-9 single words.

**Current behavior:** `_cognition_learn(_scene)` → trains bigram on YOLO label sequences.
Example: "person cat clock" updates `trans["person"]["cat"] += 1`, etc.

**v5 atlas behavior:** NO — the sight frame writes to v5 atlas via
`_guala.process_sight_frame(grid)` (line 904, krimelack chi via visual cortex) and via
`process_sight_with_recognition` (line 906-908, wC's grounded vocab path that writes
chi bindings to atlas). The YOLO LABELS as TEXT are NOT written to v5 atlas here.
The labels are what wC's `grounded_vocab_integration.py` writes into the atlas via
its own chi-keyed path. `_cognition_learn` here is the ONLY bigram training call;
there is no separate `read_sentence()` for these labels.

**Substrate-true alternative:** The label string should go to v5 via `_guala.read_sentence(
_scene, source="sight")` for proper section routing (YOLO labels are nouns → subject
section). This would give them atlas bindings with sensory context (ATTENDING_VISUAL
episode, cross-modal with sight section entries from `process_sight_frame`).

**Downstream consumer:** none (bigram state only).

**Disposition: REPLACE `_cognition_learn(_scene)` with `_guala.read_sentence(_scene, source="sight")`.**
Note: do not do both (no bigram train + v5 atlas write). Eve to confirm.

---

### Site 4 — Sound recognition: sensory words (line 927)

**Source data:** `_heard = _audio_to_sensory_words(audio_bytes)` — list of sensory
quality words derived from FFT analysis of raw audio. Examples: `["soft", "smooth",
"moving", "rising"]` (confirmed from live log). These are NOT transcribed speech —
they are FFT-derived sensory descriptors (energy/timbre/rhythm/melody).

**Current behavior:** `_cognition_learn(" ".join(_heard))` → trains bigram on FFT
quality sequences. Example: "soft smooth moving rising" updates bigram pairs.

**v5 atlas behavior:** NO — `_guala.process_sound_frame(audio_bytes)` on line 924
writes to atlas via cochlear krimelack (chi addresses per frequency band), NOT via
text sections. The sensory word string `_heard` is NOT written to v5 text atlas.

**Substrate-true alternative:** `_guala.read_sentence(" ".join(_heard), source="sound")`
would give these sensory words atlas bindings in the text sections (listen, modifier,
ground). These are modifier-class words (bright, soft, warm are in ROLE_DNA as
"modifier"); they would write to modifier+listen sections per the section routing. This
binds the auditory sensory experience to the text atlas in the same tick window as the
cochlear atlas writes — potentially creating cross-modal links wC's binder could detect.

**Downstream consumer:** none (bigram state only).

**Disposition: REPLACE with `_guala.read_sentence(" ".join(_heard), source="sound")`.**

---

### Site 5 — Sound recognition: Whisper transcription (line 937)

**Source data:** `_spoken = " ".join(w.get("word","") for w in _words if w.get("word"))`
— Whisper ASR transcription of audio. Example: "little einsteins rocket go" or
"the whale has hiccups". Full natural-language sentences from ambient speech/media.

**Current behavior:** `_cognition_learn(_spoken)` → trains bigram on transcribed speech.

**v5 atlas behavior:** NO — `process_sound_with_recognition` (wC's path) writes chi
bindings via the grounded vocab integration, but the transcribed TEXT string is NOT
separately sent to `_guala.read_sentence()` here. The bigram training is the only
text-atlas-equivalent path for Whisper transcriptions that come through the InputRing
sound_window path. (Compare: UI Whisper VTT sends `/listen` separately — but the
InputRing sound_window path processes DIRECT audio input that doesn't go through the
UI browser).

**Substrate-true alternative:** `_guala.read_sentence(_spoken, source="ambient")` would
write transcribed speech to v5 text atlas. This is the closest to what `/listen` does
for UI-originated Whisper transcriptions. SOURCE="ambient" is currently "unknown"
weight (0.7) — Eve may want to decide whether transcribed media speech should be
treated differently from Joe's direct speech.

**Downstream consumer:** none (bigram state only).

**Disposition: REPLACE with `_guala.read_sentence(_spoken, source="ambient")`
if the source of this audio is the ambient environment (show playing); or
`source="joe"` if it's Joe speaking. Eve to confirm source semantics.**

---

### Site 6 — v7_converse handler (lines 999, 1004 in `handle_v7_converse`)

**Source data:**
- Line 999: `text` — the user's input to the v7 session (free-form speech or text)
- Lines 1001-1004: the v7 session's `reply` field (the system's generated reply)

**Current behavior:** Trains bigram on both the human input AND the v7 engine's reply.
Note: this is the v7 SESSION handler, not the standard `_cmd_converse` path. It calls
`session.converse(text)` which is a different path from `_guala.converse()`.

**v5 atlas behavior:** UNKNOWN for this path — `session.converse()` uses the v7 session
engine, not the main `_guala.converse()`. Whether it writes to v5 atlas depends on
the v7 session implementation. This path is separate from the standard converse path.

**Downstream consumer:** none (bigram state only).

**Disposition: UNCLEAR — requires v7 session architecture knowledge. Flag for Eve.
If v7 session does write v5 atlas, these `_cognition_learn` calls are redundant
duplicates. If v7 session does NOT write v5 atlas, then there's a larger question of
whether v7 path should feed v5 at all.**

---

### Site 7 — Teacher correction (lines 2039, 2041 in `handle_teacher_correction`)

**Source data:**
- Line 2039: `corrected_text` — the correction Joe provides (e.g., "I want to say
  the moon is bright" as correction for a wrong emission)
- Line 2041: `story` — an optional narrative string accompanying the correction

**Current behavior:** Trains bigram on the CORRECT form Joe provides. This is labeled
as "supervised signal" in the comment: "organ-brain learns the CORRECT phrasing."

**v5 atlas behavior:** YES — `_guala.apply_teacher_correction(...)` is called earlier
in the handler and writes the correction through the v5 atlas binding path
(binding-level reinforcement/correction). The text also goes to v5 via
`_guala.read_sentence(corrected_text, ...)` inside `apply_teacher_correction`. The
bigram training is a secondary path layered on top of v5 atlas correction.

**Substrate-true alternative:** AMBIGUOUS. Teacher correction text is the highest-signal
input (Joe is deliberately teaching her the right phrase). There's an argument for
both:
- KEEP: correction text trains bigram for succession quality — but bigram is silenced,
  so this is training a mute model
- DELETE: v5 atlas correction path already handles this substratefully

**Downstream consumer:** none (bigram state only; `say()` silenced).

**Disposition: DELETE both `_cognition_learn` calls. v5 atlas correction
(`apply_teacher_correction`) already handles this. Teaching the silenced bigram
the right form is pointless until the bigram is re-evaluated for a voice role.**

---

### Site 8 — Corpus/PDF load (line 2106 in `_do_corpus_load`)

**Source data:** `sent` — one sentence from a manually uploaded PDF or corpus file.
Example: book chapter sentences from whatever Joe uploads.

**Current behavior:** `_cognition_learn(sent)` trains bigram on uploaded corpus text.

**v5 atlas behavior:** YES — `_guala.read_sentence(sent, source="corpus")` is called
on line 2105, immediately before. Duplicate pattern same as curriculum (Site 1).

**Downstream consumer:** `organ_vocab_before`/`organ_vocab_after` at lines 2101/2121
read `_guala_cognition.vocab` for logging. This is instrumentation only — the count
is logged but not used for any substrate-truth decision.

**Disposition: DELETE `_cognition_learn(sent)`. Fix the instrumentation (lines
2101/2121) to read `len(_guala.vocab)` instead if a vocab-growth metric is needed.**

---

### Site 9 — handle_sight_frame (line 2383)

**Source data:** Same as Site 3 — YOLO class labels from `process_sight_with_recognition`.
This is the DIRECT call handler (not InputRing drain) called when the frontend
explicitly POSTs a sight_frame.

**Current behavior, v5 atlas behavior, substrate-true alternative, consumer:**
Identical to Site 3.

**Disposition: Same as Site 3 — REPLACE with `read_sentence(source="sight")`.**

---

### Site 10 — handle_sound_frame (line 2414)

**Source data:** Same as Site 5 — Whisper transcription from the direct sound_frame
handler (not InputRing drain).

**Current behavior, v5 atlas behavior, substrate-true alternative, consumer:**
Identical to Site 5.

**Disposition: Same as Site 5 — REPLACE with `read_sentence(source="ambient")`.**

---

## Summary disposition table

| Site | Location | Data | v5 atlas write? | Disposition |
|------|----------|------|----------------|-------------|
| 1 | `_curriculum_feed_chunk` line 350 | Gutenberg/Aesop/Khan sentences | YES (read_sentence before) | DELETE |
| 2 | `_lookup_and_ground` line 385 | LLM description sentence | YES (read_sentence before) | DELETE |
| 3 | InputRing sight drain line 911 | YOLO labels ("person cat clock") | NO | REPLACE with read_sentence(source="sight") |
| 4 | InputRing sound drain line 927 | FFT sensory words ("soft smooth") | NO | REPLACE with read_sentence(source="sound") |
| 5 | InputRing sound drain line 937 | Whisper transcription | NO | REPLACE with read_sentence(source="ambient") |
| 6 | v7_converse line 999/1004 | User input + v7 reply | UNCLEAR | FLAG for Eve |
| 7 | teacher_correction lines 2039/2041 | Correction text + story | YES (apply_teacher_correction) | DELETE |
| 8 | `_do_corpus_load` line 2106 | PDF/corpus sentences | YES (read_sentence before) | DELETE |
| 9 | `handle_sight_frame` line 2383 | YOLO labels (direct path) | NO | REPLACE with read_sentence(source="sight") |
| 10 | `handle_sound_frame` line 2414 | Whisper transcription (direct) | NO | REPLACE with read_sentence(source="ambient") |

---

## Consumers of bigram state (other than say())

1. `_guala_cognition.vocab` at lines 2101, 2121 — instrumentation for corpus load
   stats (`organ_vocab_before`/`after`). Not load-bearing. Can be replaced with
   `len(_guala.vocab)` if a growth metric is needed.
2. Boot at line 804: `len(_guala_cognition.vocab)` and `_guala_cognition.say('the moon')`
   printed to log on startup. Diagnostic only.

**There is NO functional downstream consumer of the bigram's transition table (`trans`)
beyond `say()` (silenced) and `compose()` (only callable from `say()`).** The entire
bigram model is a training-artifact with no live consumer post-silence.

---

## Eve's predictions: confirmed or refuted

- **Curriculum → DELETE**: CONFIRMED. `read_sentence()` already called before `_cognition_learn`.
- **Worldfeed → DELETE**: CONFIRMED. Same `_curriculum_feed_chunk` path.
- **Sight (YOLO) → v5 atlas via read_sentence**: CONFIRMED — but flag: these are
  noun labels, not sentences. `read_sentence("person cat clock")` would treat each
  as a positional word. Eve should confirm whether standalone YOLO labels should
  route as a sentence or via a different mechanism.
- **Sound (Whisper) → v5 via read_sentence**: CONFIRMED. Source semantics ("ambient"
  vs "joe") is Eve's call.
- **Teacher correction → AMBIGUOUS**: Eve predicted "depends on code." Answer: v5
  atlas correction already handles this substratefully. Bigram training is redundant.
  Disposition: DELETE.
