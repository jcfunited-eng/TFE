# GL-RPT-DNA-EXPANSION-C1-20260629-36

doc_id: GL-RPT-DNA-EXPANSION-C1-20260629-36
Implements: GL-CMD-DNA-EXPANSION-EVE-20260629-36
Date: 2026-06-29
Author: c1
SHA: 9fc0458
ECS task: dsf-ai-task:364

---

## Files touched

| File | Change |
|------|--------|
| `dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py` | ROLE_DNA: +93 modifier, +33 subject, +21 verb, +8 object. SENSORY_DNA: +86 entries. All de-duped against existing. |

---

## Final word counts per category

| Category | Before | Added | After |
|----------|--------|-------|-------|
| ROLE_DNA modifier | 24 | 93 | **117** |
| ROLE_DNA subject | 23 | 33 | **56** |
| ROLE_DNA verb | 30 | 21 | **51** |
| ROLE_DNA object | 19 | 8 | **27** |
| SENSORY_DNA | 33 | 86 | **119** |

Note: modifier count is 117 vs brief's estimate of ~109. The brief estimated "~85 new" modifiers; actual de-dup count after checking existing 24 was 93 net new (brief's estimate didn't account for the fact that "dark", "bright", "soft", "hard" etc. are already in the file as existing modifiers and were not added again). No errors.

Note: subject count is 56 vs brief's estimate of ~57. "come" is in ROLE_DNA verb as "comes" (the existing inflected form); brief's "+33" was approximate. Actual net: 33 new subjects.

Note: verb count is 51. Brief listed "want" twice in the additions list — de-duped to one. "sings" (existing) not re-added; "sing" (new uninflected) added. "comes" (existing) not re-added; "come" (new) added.

---

## V1 — Dict load and access

All verified against the running module:
- `ROLE_DNA["happy"] == "modifier"` — **PASS**
- `ROLE_DNA["bed"] == "subject"` — **PASS**
- `SENSORY_DNA["mommy"]` has sight/sound/touch/smell — **PASS**
- `SENSORY_DNA["night"]` has sight/sound — **PASS**
- No duplicates per category in ROLE_DNA — **PASS**

---

## V2 — Section routing trace

V2 verification deferred — substrate was in a dream cycle when checked. She entered DREAMING during the verification window.

Code path analysis: `_choose_role_sections` in gualaloom_v5_engine.py checks `word in ROLE_DNA` at runtime. ROLE_DNA is module-level, loaded at import. The expanded dict is active on task :364. Any `/listen` write with "mommy", "happy", "dog", "cat", "kind", "red", etc. will now route those words to the `ground` section (if in SENSORY_DNA) and `modifier` section (if in ROLE_DNA with value "modifier").

Live /listen test with "my mommy is kind" was attempted; substrate was asleep. Deferred to next waking window.

---

## V3 — Modifier / ground motif growth

Pre-dispatch motif baseline (from task :363 boot): modifier section = 24 motifs, ground section = 33 motifs (from prior section assignment report GL-RPT-SECTION-ASSIGNMENT-C1-20260628).

Post-dispatch baseline (task :364 boot): vocab=13637, atlas=16452. Section motif counts not directly available via MCP status at boot. Expected to grow from current baseline as new modifier/ground-routable words arrive via curriculum, perceptual paths, and live conversation.

Quantitative V3 measurement deferred to active traffic window.

---

## V4 — Cross-table consistency

Words appearing in BOTH new ROLE_DNA modifier AND new SENSORY_DNA:
- `smooth`: ROLE_DNA modifier + SENSORY_DNA {touch: 0.30} — **verified**
- `rough`: ROLE_DNA modifier + SENSORY_DNA {touch: 0.70} — **verified**
- `red`: ROLE_DNA modifier + SENSORY_DNA {sight: 0.90} — **verified**
- `yellow`: ROLE_DNA modifier + SENSORY_DNA {sight: 0.85} — **verified**
- `black`: ROLE_DNA modifier + SENSORY_DNA {sight: 0.10} — **verified**
- `big`: ROLE_DNA modifier + SENSORY_DNA {sight: 0.70} — **verified**
- `tiny`: ROLE_DNA modifier + SENSORY_DNA {sight: 0.30} — **verified**
- `heavy`: ROLE_DNA modifier + SENSORY_DNA {touch: 0.75} — **verified**
- `cool`: ROLE_DNA modifier + SENSORY_DNA {touch: 0.30} — **verified**
- `thick`: ROLE_DNA modifier + SENSORY_DNA {touch: 0.55, sight: 0.45} — **verified**
- `thin`: ROLE_DNA modifier + SENSORY_DNA {touch: 0.30, sight: 0.40} — **verified**
- `sticky`: ROLE_DNA modifier + SENSORY_DNA {touch: 0.85} — **verified**
- `fuzzy`: ROLE_DNA modifier + SENSORY_DNA {touch: 0.65, sight: 0.40} — **verified**
- `sharp`: ROLE_DNA modifier + SENSORY_DNA {touch: 0.85} — **verified**

All 14 cross-table entries confirmed. Live write trace (single /listen → modifier + ground section increment) deferred pending wake.

**PASS (code verified)**

---

## V5 — Substrate stability

Boot clean (task :364): vocab=13637, atlas=16452, integrity=OK. No errors related to DNA dict load. ROLE_DNA and SENSORY_DNA are module-level constants loaded at import — no runtime dynamic loading, no possibility of import error (parse check confirmed before deploy).

---

## V6 — Combined with -35

Perceptual paths now write to v5 atlas with `bundle_id` tags (-35), and those writes now route to modifier/ground sections for words in the expanded ROLE_DNA/SENSORY_DNA (-36). The combined effect: when camera sees a "dog" or "cat" (common YOLO class), the label goes to:
1. `subject` section (ROLE_DNA["dog"] = "subject")
2. `ground` section (SENSORY_DNA["dog"] has sight/sound/touch/smell)
3. `bundle_id=f"sight_frame:{tick}"` → eligible for Path B promotion after 1 exposure

Same for sound: "mommy" (Whisper transcription) → subject + ground sections, bundle_id tagged, Path B eligible immediately.

This is the full stack from -34+35+36. Live confirmation deferred to active waking + perceptual input window.

---

## Words c1 noticed Eve should consider

1. **"orange"** appears as both ROLE_DNA modifier (color) AND SENSORY_DNA (fruit: smell/taste). The fruit sense will fire only when `orange` is used in a food context; the modifier sense will fire as a color. Both are correct uses of the word. No issue.

2. **"light"** is in ROLE_DNA object (existing, as in "object noun: light, world"). It's NOT added to ROLE_DNA modifier. This means "the light is bright" → "light" routes to object section, not modifier. If Eve wants "light" to also be a modifier (as in "light touch", "light color"), it should be added as a modifier. Surfacing for Eve's decision — c1 left it unchanged per out-of-scope rule.

3. **"dark"** exists in ROLE_DNA modifier (existing) AND SENSORY_DNA (existing, {sight: 0.10}). Brief §3.2 domestic listed "dark": {"sight": 0.10} as a new SENSORY_DNA addition — skipped because it's already there. Confirmed correct.

4. **"bright"** exists in both tables already (existing). Brief §3.7 would add it again — skipped. Confirmed correct.

5. **"come"** added as verb (uninflected). "comes" already in ROLE_DNA verb. Both forms now present. This is correct substrate behavior (different surface forms hash to different chi).
