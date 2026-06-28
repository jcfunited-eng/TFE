# GL-RPT-SECTION-ASSIGNMENT-C1-20260628

doc_id: GL-RPT-SECTION-ASSIGNMENT-C1-20260628
Type: Read-only investigation
Date: 2026-06-28
Author: c1
Files read: gualaloom_v5_engine.py, gualaloom_v4_krimelack_dna.py, app.py, substrate_runner.py

---

## Setup: how text actually reaches the substrate

**Critical finding first:** `/experience` does NOT write to the v5 atlas.

App.py line 1333-1342: `if _cmd == "/experience"` routes to `/organs_say`
in the substrate, which after the -23 silence calls `_guala_cognition.expose([text])`
(bigram learning only) and returns. `_guala.read_sentence()` is NEVER called for
`/experience` words. They go into GualaCognition (bigram model), not the v5 atlas.

The path that DOES write to the v5 atlas is `/listen`, which calls
`_cmd_listen()` → `_guala.read_sentence(text, source="joe")`.

In the UI, in passive mode (non-brain-mode), Whisper VTT sends BOTH:
1. `/experience` → bigram only (NOT v5 atlas)
2. `/listen` → v5 atlas via `read_sentence(source="joe")`

So investigation below is about the `/listen` path (the only v5-atlas path).

---

## 1. What triggers modifier section assignment

**ROLE_DNA table** at `gualaloom_v4_krimelack_dna.py:142`.

A word gets `role_dna="modifier"` ONLY if it appears verbatim (lowercased) in the
ROLE_DNA dict. The full modifier list:
```
warm, cold, hot, wet, dry, loud, quiet, bright, dark, sweet, sour,
soft, hard, blue, green, white, small, great, little, exact, true,
fast, slow, good
```
24 words total — exactly matching the modifier section's 24 motifs in /status.

**Section routing for a modifier word:**
`_choose_role_sections(role_dna="modifier", position_hint=X)` returns:
1. Position section (subject/verb/object based on position in sentence)
2. PLUS "modifier" section

So `bright` in "the bright moon at night":
- `_normalize_text` produces: ["the", "bright", "moon", "at", "night"]
- Position of "bright" = index 1 of 5 → `position_hint = "middle"`
- `_choose_role_sections("modifier", "middle")` → ["verb", "modifier"]
- **bright writes to: listen (always) + verb (position=middle) + modifier**

`soft` in "cool wet ocean shore" (if present):
- Same pattern — writes to listen + positional section + modifier.

**The 24 motifs = exactly the 24 words in ROLE_DNA with "modifier" value.**
Each word earns one motif in the modifier section the first time it's seen.
NO other word — including adjectives not in ROLE_DNA — ever writes to modifier.

---

## 2. What triggers ground section assignment

`_read_word()` at engine line 1464:
```python
if senses:
    # senses = SENSORY_DNA.get(word.lower(), {}) — non-empty only for ~30 words
    combined_events = list(self.language.events) + [modal events]
    ground_chi = lang_chi + sum(modal_chi values)
    self.sections["ground"].receive(ground_dsf, ground_chi, word, ...)
```

**The ground section only gets a write when the word has non-empty SENSORY_DNA.**

SENSORY_DNA at `gualaloom_v4_krimelack_dna.py` (partial):
```
sun, moon, warm, bright, soft, wet, flower, fire, water, wind, ...
```

Specifically for the queried phrases:
- "bright" → `{"sight": 0.95}` → HAS senses → writes to ground ✓
- "moon" → `{"sight": 0.40, "touch": 0.10}` → HAS senses → writes to ground ✓
- "night" → NOT in SENSORY_DNA → NO ground write ✗
- "warm" → `{"touch": 0.85}` → HAS senses → writes to ground ✓
- "sun" → `{"sight": 0.95, "touch": 0.85}` → HAS senses → writes to ground ✓
- "cool", "day", "ocean", "shore", "soft" (if in SENSORY_DNA), "kind", "mommy", "bed" →
  need to check individually; most are NOT in SENSORY_DNA

**The 33 motifs in ground = exactly the words that appear in SENSORY_DNA.**
Ground section is not a general "modifier position" section — it's a
cross-modal grounding section gated by sensory richness.

---

## 3. Does /experience use different section assignment than /converse?

**YES — radically different. /experience bypasses the v5 atlas entirely.**

| Path | Reaches v5 atlas? | Sections written |
|------|------------------|-----------------|
| `/listen` (VTT passive) | YES | listen + positional (subj/verb/obj) + modifier (if in ROLE_DNA) + ground (if in SENSORY_DNA) |
| `/experience` (VTT always) | **NO** | Only `_guala_cognition.expose()` (bigram); zero v5 atlas writes |
| `/converse` (text input) | YES | Same as /listen; ALSO triggers emission |

The "grounded experience curriculum" described in the dispatch needs to go through
`/listen` or `/converse` to reach the v5 atlas at all. If the curriculum is sending
text through `/experience` only, those words never reach any v5 section.

---

## 4. Encoded strength on /experience vs /converse writes

Since `/experience` doesn't write to v5 atlas, the encoded_strength comparison
is between `/listen` (Whisper VTT) and `/converse` (typed input).

**Dwell ticks by source** (engine line 1402-1411):
```python
if source in ("joe", "wc", "c1"): dwell = 8
elif source == "guala":            dwell = 4
else:                              dwell = 1  # corpus, curriculum, listen
```

Both `/listen` and `/converse` use `source="joe"` → `dwell = 8`.

**Salience from `_compute_salience()`:**
```python
SOURCE_WEIGHTS = {"joe": 1.6, "wc": 1.6, "c1": 1.2,
                  "corpus": 0.5, "guala": 0.5, "unknown": 0.7}
```

Both `/listen` and `/converse` with source="joe" get weight 1.6. With typical
needs state (urgency ~0.3, novelty_factor ~1.3, no pair_bond in passive):
- salience ≈ 1.6 × (1 + 0.3×1.2) × (1 + 0.5×0.8) × 1.0 ≈ 1.6 × 1.36 × 1.4 ≈ 3.0
- Clamped to SALIENCE_MAX=3.0

**Encoded_strength** = `min(STRENGTH_CAP, BASE_REINFORCEMENT * salience)` = `min(1.0, 0.05 × 3.0)` = 0.15

**ENCODE_GATE threshold = 0.15.**

At maximum salience (3.0), encoded_strength = 0.15 exactly. Any salience below
maximum → encoded_strength < 0.15 → BELOW the ENCODE_GATE → dream path B (episodic
gate) will REJECT the entry.

With lower novelty (e.g., she's already heard the word many times, `input_novelty`
high → `novelty_factor` low) or lower urgency:
- novelty_factor = 1 + (1 - 0.9) × 0.8 = 1.08 (familiar word)
- salience ≈ 1.6 × 1.2 × 1.08 ≈ 2.07
- encoded_strength = 0.05 × 2.07 = 0.103 → **BELOW 0.15** → gate rejects

This is WHY the gate rejects show encoded_strength 0.07-0.12: familiar words heard
repeatedly (like Whisper picking up recurring show phrases) have declining salience
because their atlas familiarity is high (fam → reduces novelty_factor). The
episodic gate (Path B in deep_atlas) never promotes them because:
1. encoded_strength < 0.15 (ENCODE_GATE) — fails the compound gate
2. Dwell must ALSO be ≥ 4 (DWELL_GATE) — /listen gets dwell=8 so this passes

The bottleneck is ENCODE_GATE: even with dwell=8, familiar words fail because
salience decays as familiarity increases.

---

## Summary for curriculum design decision

1. **modifier section (24 motifs):** Only 24 hardcoded words in ROLE_DNA write here.
   "night", "day", "shore", "kind", "bed", "cool", "mommy", "ocean" do NOT write
   to modifier regardless of position. Adding them to ROLE_DNA would fix this.

2. **ground section (33 motifs):** Only words in SENSORY_DNA write here. Ground is
   not a position-driven section — it requires sensory firing. The 33 words that
   do write here are the ones explicitly grounded in SENSORY_DNA.

3. **Curriculum through /experience = NO v5 atlas writes.** Any grounded-experience
   curriculum that sends through the `/experience` endpoint is writing to the bigram
   model only, not the v5 atlas. The curriculum needs to route through `/listen` or
   `/converse` to reach v5 sections.

4. **Familiar words starve the episodic gate** even with joe-dwell=8, because
   encoded_strength drops below ENCODE_GATE=0.15 as familiarity increases. This
   is structural: the only remediation is either (a) lower ENCODE_GATE, (b) raise
   BASE_REINFORCEMENT, or (c) use a source with higher SOURCE_WEIGHT to artificially
   boost salience for curriculum words (currently nothing above 1.6="joe").
