# GL-CMD-DNA-EXPANSION-EVE-20260629-36

doc_id: GL-CMD-DNA-EXPANSION-EVE-20260629-36
Type: Implementation command (single dispatch, single ship)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)
Implements: DNA expansion from GL-MFST-HANDOFF-EVE-20260628 §4 item 2
Prereq: GL-CMD-BIGRAM-DELETE-EVE-20260629-34 shipped (perceptual paths route to v5 atlas). Can ship in parallel with GL-CMD-GROUNDED-PROMOTION-EVE-20260629-35.
Evidence base: GL-RPT-SECTION-ASSIGNMENT-C1-20260628 (24 ROLE_DNA modifiers, 31 SENSORY_DNA entries are the current write set for modifier+ground sections)

---

## 1. Why this dispatch

Per the section assignment report: a word writes to the **modifier section** of v5 atlas only if it appears verbatim in `ROLE_DNA` with value `"modifier"`. A word writes to the **ground section** only if it appears in `SENSORY_DNA` with a non-empty sensory profile. Current size:

- `ROLE_DNA` modifier-class: 24 words (warm, cold, hot, wet, dry, loud, quiet, bright, dark, sweet, sour, soft, hard, blue, green, white, small, great, little, exact, true, fast, slow, good)
- `SENSORY_DNA`: 31 entries (nature objects, basic qualities, foods)

Common modifier-class words she hears regularly — "happy", "sad", "tired", "sleepy", "kind", "gentle", "big", "tiny", "red", "yellow", "black", "old", "new", "scary", "lovely" — never write to her modifier section regardless of frequency. Common sensory-rich nouns — "night", "day", "ocean", "shore", "bed", "mommy", "daddy", "dog", "cat" — never write to her ground section.

This dispatch expands both tables to roughly 4× their current size. The lists are hand-curated common-word-frequency-ordered for an English-speaking child's environment. The expansion is structurally what was always intended; the original 24+31 were placeholders.

Sensory profiles use the same scale and modalities as the existing 31 entries (sight, sound, smell, taste, touch in [0, 1]).

---

## 2. ROLE_DNA expansion

In `dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py`, add the following entries to the existing `ROLE_DNA` dict. Group by semantic category for readability. Existing entries unchanged.

### 2.1 Modifier-class additions (~80 new entries)

```python
# colors
"red": "modifier", "yellow": "modifier", "orange": "modifier",
"purple": "modifier", "pink": "modifier", "black": "modifier",
"brown": "modifier", "gray": "modifier", "gold": "modifier",
"silver": "modifier",
# size + shape
"big": "modifier", "tiny": "modifier", "large": "modifier",
"huge": "modifier", "tall": "modifier", "long": "modifier",
"wide": "modifier", "narrow": "modifier", "deep": "modifier",
"shallow": "modifier", "thick": "modifier", "thin": "modifier",
"round": "modifier", "flat": "modifier",
# temperature (extends warm/cold/hot)
"cool": "modifier", "freezing": "modifier", "boiling": "modifier",
# age + freshness
"new": "modifier", "old": "modifier", "young": "modifier",
"fresh": "modifier", "stale": "modifier",
# texture
"smooth": "modifier", "rough": "modifier", "sticky": "modifier",
"slippery": "modifier", "fuzzy": "modifier", "prickly": "modifier",
"sharp": "modifier", "dull": "modifier",
# weight + density
"heavy": "modifier", "full": "modifier", "empty": "modifier",
# motion
"still": "modifier", "busy": "modifier", "calm": "modifier",
"wild": "modifier", "gentle": "modifier", "fierce": "modifier",
# emotion + affect
"happy": "modifier", "sad": "modifier", "angry": "modifier",
"mad": "modifier", "scared": "modifier", "excited": "modifier",
"surprised": "modifier", "proud": "modifier", "shy": "modifier",
"brave": "modifier", "mean": "modifier", "kind": "modifier",
"nice": "modifier", "bitter": "modifier",
# state
"tired": "modifier", "sleepy": "modifier", "hungry": "modifier",
"thirsty": "modifier", "lonely": "modifier", "sick": "modifier",
"well": "modifier", "healthy": "modifier", "alive": "modifier",
"awake": "modifier", "asleep": "modifier",
# aesthetic + value
"pretty": "modifier", "ugly": "modifier", "beautiful": "modifier",
"lovely": "modifier", "cute": "modifier", "perfect": "modifier",
"bad": "modifier", "best": "modifier", "real": "modifier",
"safe": "modifier", "easy": "modifier", "simple": "modifier",
"fun": "modifier", "scary": "modifier", "boring": "modifier",
"clean": "modifier", "dirty": "modifier", "strong": "modifier",
"weak": "modifier",
```

Total new modifiers: ~85. Combined with existing 24, gives ~109 modifier-class entries.

### 2.2 Subject-class additions (~30 new entries — common nouns kids point at)

These don't strictly unblock modifier/ground but they improve subject-section routing for common nouns currently routing without role priors. Keep for completeness:

```python
# domestic
"home": "subject", "room": "subject", "bed": "subject",
"door": "subject", "window": "subject", "book": "subject",
"toy": "subject", "ball": "subject", "lamp": "subject",
# people
"mommy": "subject", "daddy": "subject", "baby": "subject",
"friend": "subject",
# animals
"dog": "subject", "cat": "subject", "fish": "subject",
"bear": "subject", "horse": "subject", "cow": "subject",
"sheep": "subject", "pig": "subject", "duck": "subject",
"chicken": "subject", "mouse": "subject", "rabbit": "subject",
# nature
"night": "subject", "day": "subject", "ocean": "subject",
"beach": "subject", "grass": "subject", "snow": "subject",
"river": "subject", "lake": "subject",
```

### 2.3 Verb-class additions (~12 new entries)

```python
"go": "verb", "come": "verb", "stay": "verb", "stop": "verb",
"play": "verb", "sleep": "verb", "wake": "verb", "eat": "verb",
"drink": "verb", "walk": "verb", "run": "verb", "sing": "verb",
"dance": "verb", "cry": "verb", "laugh": "verb", "love": "verb",
"like": "verb", "want": "verb", "need": "verb", "know": "verb",
"want": "verb", "say": "verb", "do": "verb",
```

(De-dup any that already exist in the file; "do", "say", "want" if present should not be added twice.)

### 2.4 Object-class additions (~6 new entries)

```python
"hand": "object", "foot": "object", "eye": "object",
"ear": "object", "nose": "object", "mouth": "object",
"hair": "object", "skin": "object",
```

---

## 3. SENSORY_DNA expansion

In the same file, add the following entries to the `SENSORY_DNA` dict. Existing 31 entries unchanged. Sensory profile values are calibrated to be consistent with the existing entries (e.g. moon's `sight=0.40` is dim-but-visible; salt's `taste=0.90` is intense single-modality).

### 3.1 Nature additions

```python
"night":   {"sight": 0.10, "sound": 0.20},
"day":     {"sight": 0.95},
"morning": {"sight": 0.75},
"evening": {"sight": 0.40},
"ocean":   {"sight": 0.85, "sound": 0.70, "touch": 0.60, "smell": 0.55, "taste": 0.50},
"sea":     {"sight": 0.85, "sound": 0.70, "touch": 0.60, "smell": 0.55, "taste": 0.50},
"beach":   {"sight": 0.75, "touch": 0.60, "smell": 0.45, "sound": 0.55},
"shore":   {"sight": 0.70, "touch": 0.55, "sound": 0.50},
"sand":    {"sight": 0.55, "touch": 0.65},
"mud":     {"sight": 0.40, "touch": 0.70, "smell": 0.45},
"dirt":    {"sight": 0.45, "touch": 0.55, "smell": 0.40},
"grass":   {"sight": 0.70, "touch": 0.55, "smell": 0.50},
"snow":    {"sight": 0.95, "touch": 0.10},
"river":   {"sight": 0.75, "sound": 0.60, "touch": 0.40},
"lake":    {"sight": 0.80, "sound": 0.30},
"pond":    {"sight": 0.65, "sound": 0.25},
"rock":    {"sight": 0.55, "touch": 0.80},
```

### 3.2 Domestic / objects additions

```python
"home":    {"sight": 0.75, "smell": 0.40},
"room":    {"sight": 0.70},
"bed":     {"sight": 0.55, "touch": 0.80},
"pillow":  {"sight": 0.55, "touch": 0.85},
"blanket": {"sight": 0.55, "touch": 0.85},
"floor":   {"sight": 0.45, "touch": 0.60},
"wall":    {"sight": 0.50, "touch": 0.55},
"door":    {"sight": 0.70, "sound": 0.45, "touch": 0.60},
"window":  {"sight": 0.85, "touch": 0.55},
"lamp":    {"sight": 0.85, "touch": 0.50},
"light":   {"sight": 0.95},
"dark":    {"sight": 0.10},
"book":    {"sight": 0.65, "touch": 0.50, "smell": 0.30},
"toy":     {"sight": 0.85, "touch": 0.65},
"ball":    {"sight": 0.85, "touch": 0.70, "sound": 0.45},
```

### 3.3 Body parts additions

```python
"hand":    {"sight": 0.85, "touch": 0.95},
"foot":    {"sight": 0.65, "touch": 0.85},
"eye":     {"sight": 0.55, "touch": 0.30},
"ear":     {"sight": 0.45, "sound": 0.80, "touch": 0.40},
"nose":    {"sight": 0.45, "smell": 0.95, "touch": 0.40},
"mouth":   {"sight": 0.60, "taste": 0.90, "touch": 0.55},
"hair":    {"sight": 0.75, "touch": 0.85, "smell": 0.40},
"skin":    {"sight": 0.65, "touch": 0.95, "smell": 0.30},
```

### 3.4 People / animals additions

```python
"mommy":   {"sight": 0.95, "sound": 0.85, "touch": 0.90, "smell": 0.70},
"daddy":   {"sight": 0.95, "sound": 0.85, "touch": 0.90, "smell": 0.70},
"baby":    {"sight": 0.85, "sound": 0.75, "touch": 0.85, "smell": 0.65},
"friend":  {"sight": 0.85, "sound": 0.65, "touch": 0.70},
"dog":     {"sight": 0.90, "sound": 0.85, "touch": 0.85, "smell": 0.55},
"cat":     {"sight": 0.85, "sound": 0.70, "touch": 0.95},
"fish":    {"sight": 0.75, "touch": 0.45, "smell": 0.55},
"bear":    {"sight": 0.95, "sound": 0.65, "touch": 0.85},
"horse":   {"sight": 0.95, "sound": 0.75, "touch": 0.85, "smell": 0.55},
"cow":     {"sight": 0.95, "sound": 0.85, "smell": 0.55},
"sheep":   {"sight": 0.85, "sound": 0.75, "touch": 0.85},
"pig":     {"sight": 0.85, "sound": 0.85, "smell": 0.65},
"duck":    {"sight": 0.75, "sound": 0.80, "touch": 0.65},
"chicken": {"sight": 0.75, "sound": 0.70},
"mouse":   {"sight": 0.55, "sound": 0.45, "touch": 0.50},
"rabbit":  {"sight": 0.85, "touch": 0.85},
```

### 3.5 Food additions

```python
"cake":    {"sight": 0.85, "smell": 0.90, "taste": 0.95, "touch": 0.55},
"cookie":  {"sight": 0.85, "smell": 0.85, "taste": 0.95, "touch": 0.65},
"candy":   {"sight": 0.85, "smell": 0.70, "taste": 0.95},
"juice":   {"sight": 0.80, "smell": 0.65, "taste": 0.85},
"soup":    {"sight": 0.65, "smell": 0.75, "taste": 0.80, "touch": 0.55},
"rice":    {"sight": 0.65, "taste": 0.65, "touch": 0.55},
"cheese":  {"sight": 0.75, "smell": 0.85, "taste": 0.85, "touch": 0.60},
"egg":     {"sight": 0.85, "smell": 0.50, "taste": 0.70, "touch": 0.55},
"butter":  {"sight": 0.75, "smell": 0.60, "taste": 0.75, "touch": 0.70},
"honey":   {"sight": 0.80, "smell": 0.85, "taste": 0.95, "touch": 0.70},
"banana":  {"sight": 0.85, "smell": 0.65, "taste": 0.80, "touch": 0.55},
"orange":  {"sight": 0.85, "smell": 0.85, "taste": 0.85, "touch": 0.55},
```

### 3.6 Sound-rich additions

```python
"bell":    {"sight": 0.55, "sound": 0.90, "touch": 0.55},
"drum":    {"sight": 0.65, "sound": 0.95, "touch": 0.55},
"music":   {"sound": 0.95},
"song":    {"sound": 0.90},
"voice":   {"sound": 0.85},
```

### 3.7 New qualities aligned with ROLE_DNA additions

These are modifiers that also have sensory groundings, so they exist in both tables:

```python
"smooth":  {"touch": 0.30},
"rough":   {"touch": 0.70},
"sticky":  {"touch": 0.85},
"fuzzy":   {"touch": 0.65, "sight": 0.40},
"sharp":   {"touch": 0.85},
"heavy":   {"touch": 0.75},
"cool":    {"touch": 0.30},
"thick":   {"touch": 0.55, "sight": 0.45},
"thin":    {"touch": 0.30, "sight": 0.40},
"red":     {"sight": 0.90},
"yellow":  {"sight": 0.85},
"black":   {"sight": 0.10},
"big":     {"sight": 0.70},
"tiny":    {"sight": 0.30},
```

---

## 4. Total counts after dispatch

| Table | Before | Added | After |
|-------|--------|-------|-------|
| ROLE_DNA modifier | 24 | ~85 | ~109 |
| ROLE_DNA subject | ~24 | ~33 | ~57 |
| ROLE_DNA verb | ~28 | ~20 | ~48 |
| ROLE_DNA object | ~19 | ~8 | ~27 |
| SENSORY_DNA | 31 | ~80 | ~111 |

---

## 5. Tests

### V1 — Dict load and access

After dispatch ships and substrate restarts, exercise via the bridge or test harness:
- `ROLE_DNA["happy"] == "modifier"`
- `ROLE_DNA["bed"] == "subject"`
- `SENSORY_DNA["mommy"]` returns a dict with sight/sound/touch/smell keys
- `SENSORY_DNA["night"]` returns a dict with sight/sound keys

### V2 — Section routing trace via /listen

Send via bridge (or /listen endpoint): "my mommy is kind". Expected after dispatch:
- "my" → listen + positional
- "mommy" → listen + positional + ground (was: only listen+positional)
- "is" → listen + positional
- "kind" → listen + positional + modifier (was: only listen+positional)

Inspect atlas section motif counts before/after the write. `modifier` and `ground` should both increment.

Repeat with: "the dog is happy and the cake is sweet".
Expected: dog → ground; happy → modifier; cake → ground; sweet → modifier+ground (sweet already in both before).

### V3 — Modifier/ground motif growth measured

Record `section_motifs` for `modifier` and `ground` before dispatch (currently 24 and 33 per /status). Drive 20 sentences containing newly-added words via /listen. After: motif counts for modifier and ground should both grow to reflect the new words now able to write.

### V4 — Cross-table consistency

For each word that appears in BOTH new ROLE_DNA modifier AND new SENSORY_DNA (e.g. "smooth", "rough", "red", "yellow", "big", "tiny", "heavy", "cool"), confirm both writes happen on a single /listen pass — modifier section gets a motif, ground section gets a motif.

### V5 — Substrate stability

After dispatch ships, monitor 30 minutes for unexpected errors, save/load issues, vocab growth anomalies.

### V6 — Combined with -35 (if -35 already shipped)

If -35 is in production: send a sight_frame containing labels that match expanded ROLE_DNA / SENSORY_DNA words ("dog", "cat", "ball" — common YOLO classes). After a dream cycle, deep_atlas should have entries from at least some of those labels (Path B via grounded promotion + section-routable via expanded DNA).

---

## 6. Out of scope (intentionally)

- The hand-curated lists are first-pass. They prioritize common-English-environment words a child encounters. Future expansion (regional words, specific domains, additional languages) is separate work.
- The substrate-true direction is **learned section assignment** (let the substrate discover modifier/ground class through co-occurrence rather than hardcoded dict). That is months-of-refactor and not in scope here. This dispatch is the unblock-now hack with a known shape; it does not replace the long-term substrate-true direction.
- No changes to `_choose_role_sections`, `_read_word`, or `read_sentence` logic. All wiring downstream of the DNA dicts is unchanged.
- No changes to encoding formula or gate. That is -35.

---

## 7. Rollback

If V5 fails or vocab growth shows pathological behavior (unexpected section motif explosion, save/load failures):

1. Re-pause autonomy via bridge.
2. Revert the dispatch commit.
3. Redeploy.

State migration is not needed; pre-dispatch entries are unaffected by adding new entries to the DNA dicts.

---

## 8. Reporting

c1 produces `GL-RPT-DNA-EXPANSION-C1-20260629-36.md` with:

- Final word counts per category in each dict (sanity check no typos / silent duplicates).
- Result of each V1-V6 test.
- Pre/post motif counts for modifier and ground sections after a representative traffic window.
- Any words that c1 noticed Eve should add or remove based on substrate behavior observation.
- Final SHA and ECS task number.
