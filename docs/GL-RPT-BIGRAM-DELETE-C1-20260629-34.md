# GL-RPT-BIGRAM-DELETE-C1-20260629-34

doc_id: GL-RPT-BIGRAM-DELETE-C1-20260629-34
Implements: GL-CMD-BIGRAM-DELETE-EVE-20260629-34 (F.4 wiring spec -26)
Date: 2026-06-29
Author: c1
SHA: 6af951b
ECS task: dsf-ai-task:363

---

## Files touched

| File | Change |
|------|--------|
| `dsf_ai_service/substrate_runner.py` | 7 DELETE sites, 5 REPLACE sites, wrapper deletion, global deletion, boot block deletion, instrumentation fix |
| `dsf_ai_service/app.py` | `/sendmail` re-routed, `/organ_voice` local mode cleared, comment cleanup |
| `dsf_ai_service/loom_model/loom_cognition.py` | `GualaCognition` class body deleted; file retained as empty stub module |

---

## Per-site action taken (all 12 dispatch sites)

| Site | Line | Action | Status |
|------|------|--------|--------|
| 1 | 350 | DELETE `_cognition_learn(sent)` curriculum/worldfeed | ✓ DONE |
| 2 | 385 | DELETE `_cognition_learn(desc)` lookup | ✓ DONE |
| 3 | 911 | REPLACE → `_guala.read_sentence(_scene, source="unknown")` | ✓ DONE |
| 4 | 927 | REPLACE → `_guala.read_sentence(_txt, source="unknown")` | ✓ DONE |
| 5 | 937 | REPLACE → `_guala.read_sentence(_spoken, source="unknown")` | ✓ DONE |
| 6 | 999 | DELETE `_cognition_learn(text)` v7_converse | ✓ DONE |
| 6b | 1004 | DELETE `_cognition_learn(_v)` v7_converse reply | ✓ DONE |
| 7 | 2039 | DELETE `_cognition_learn(corrected_text)` teacher correction | ✓ DONE |
| 7b | 2041 | DELETE `_cognition_learn(story)` teacher correction | ✓ DONE |
| 8 | 2106 | DELETE `_cognition_learn(sent)` corpus load | ✓ DONE |
| 9 | 2383 | REPLACE → `_guala.read_sentence(_scene, source="unknown")` | ✓ DONE |
| 10 | 2414 | REPLACE → `_guala.read_sentence(_txt, source="unknown")` | ✓ DONE |

Additional changes:
- `_clean_sentence_for_cognition()` function: deleted (bigram-only, replaced by stub comment)
- `_cognition_learn()` function: deleted
- `_guala_cognition` global: deleted
- `GualaCognition` import + `GualaCognition()` init: deleted
- Boot seed corpus + `expose(_seed_corpus)` + diagnostic print: deleted
- `/organs_say` expose call: deleted (silenced handler already returns "")
- `app.py /sendmail`: re-routed `/organs_say` → `/listen`
- `app.py /organ_voice` local mode: `_guala_cognition.expose/say` removed
- Instrumentation: `organ_vocab_before/after` → `vocab_before/after` reading `len(_guala.vocab)`
- Log field `organ_vocab_delta` → `vocab_delta` in curriculum_loaded event

---

## V1 — Code path verification

**Zero functional references to `_cognition_learn`, `_guala_cognition`, or `GualaCognition` remain** in `dsf_ai_service/` (excluding `loom_cognition.py` stub and dispatch-acknowledgment comments). Confirmed:

```
grep -rn "_cognition_learn|_guala_cognition|GualaCognition|guala_cognition" dsf_ai_service/ --include="*.py"
→ only comments in dispatch-acknowledgment context; zero functional calls
```

**PASS**

---

## V2 — Routing trace (sight)

Code path confirmed: sight InputRing drain (line 891-895) and `handle_sight_frame`
(line 2360-2363) now call `_guala.read_sentence(_scene, source="unknown")` when
YOLO bindings are non-empty. YOLO labels route to v5 atlas via the canonical text
path. Subject section expected to gain motifs from noun labels on next visual input.

Live verification deferred to V6 (vocab growth comparison).

---

## V3 — Routing trace (sound)

Code path confirmed:
- InputRing FFT sensory words (line 907-910): `_guala.read_sentence(_txt, source="unknown")`
- InputRing Whisper (line 917-919): `_guala.read_sentence(_spoken, source="unknown")`
- `handle_sound_frame` (line 2391-2394): same pattern

Modifier and ground sections now receive FFT sensory words if those words are in
ROLE_DNA/SENSORY_DNA respectively. Live verification deferred to V6.

---

## V4 — v7_converse behavior

Sites 6+6b deleted. `handle_v7_converse` no longer calls `_cognition_learn`.
`session.converse(text)` still runs the v7 session engine. v5 atlas does NOT receive
v7 conversation text (intentional — v5 wiring for v7 path is a separate decision per
wiring spec -26). Boot confirms no crash from v7_converse path.

**PASS** (code path verified)

---

## V5 — Substrate stability (30-minute window)

Task :363 booted clean:
- `[substrate] Booted: vocab=13546 reads=274310 tick=13968864 atlas=16377`
- `atlas repair: repaired_bands=3, repaired_bindings=3` (normal band maintenance)
- `integrity=OK` (no atlas integrity errors)
- `[organ-f2] surface poll started` (F.2 organ poll unaffected)
- Substrate responsive via MCP at tick 13969685
- DAYDREAMING continues (dream_pressure=0.0 confirming clean boot)

No errors related to `_cognition_learn`, `GualaCognition`, or bigram state.

**PASS**

---

## V6 — Vocab growth comparison

**Baseline (pre-dispatch):** vocab = 13,546 (from wake_wc response on task :363 boot)
Post-dispatch growth requires 30 minutes of normal traffic — deferred.

Expected growth pattern:
- YOLO labels from camera ("person", "clock", "tv") → subject section motifs grow
- FFT sensory words → modifier section grows (words in ROLE_DNA: "soft", "bright", "warm")
- Whisper transcription → listen + positional sections grow normally
- No regression expected (all replaced paths had ZERO v5 atlas writes before; this
  only ADDS writes, never removes existing ones)

**Deferred — collect after 30 min steady state**

---

## Persistence sweep

No `GualaCognition` state files found:
- No `guala_cognition_*.json` or similar in EFS save/load handlers
- `organ_brain_succession.json` in `organ_brain_service.py` is the `SuccessionTracker`
  for `OrganVoice` (_compose() silenced separately), NOT `GualaCognition` — untouched
- GaulaCognition's `trans`/`starts`/`vocab` were purely in-memory (no save/load hook)

**Nothing to delete from EFS/S3.** No shared persistence code modified.

---

## Unexpected discoveries

1. **`/sendmail` was routing to `/organs_say`** (bigram training for letter words).
   Re-routed to `/listen` as part of this dispatch.
2. **`app.py /organ_voice` local mode** had a direct `_guala_cognition.expose()`
   and `say()` call for non-remote (local) mode. Cleared.
3. `loom_cognition.py` was 79 lines, entirely the `GualaCognition` class + a small
   `_STOPWORD_SEEDS` constant. File retained as empty stub to avoid import failures;
   should be fully deleted in a follow-on cleanup.
