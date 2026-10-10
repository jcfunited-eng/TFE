# GL-SPC-MOMENT-LEVEL2-C1-20260915-v1 — Level 2: the moment (a heard sound bound to what her senses held at that beat)

Type: SPECIFICATION DRAFT for A1's co-draft and Joe's word (C1, 2026-09-15). Nothing here is built. Every number is measured or declared once. It follows Level 1 (the ear's gate, in her as 1495; the eye's gaze law and figure, in her as 1496 to 1498) and precedes Level 3 (what followed a moment, by count).

## 1. What a moment is

The tuple of what her senses hold at the beat a sound event closes: the event's key, and the exact discrete state of her other senses at that beat. Two moments are the same moment or they are not; nothing is compared by distance. A moment is counted each time it recurs. This is the "fractile of the moment made exact": the word "apple" heard while the apple is in her hand and its taste on her tongue is one moment; the same word heard while she holds the bear is another.

## 2. What her senses give at a beat, measured (2026-09-15)

- **Ear** (Level 1, in her): the key of the sound event that closed on this beat; none on other beats. The same recording gives the same key; two words give two keys (measured, ledger).
- **Hand**: the thing she holds has a declared material in her world (compliance, roughness, surface temperature). Her touch_texture stream is the material's compliance and roughness over full scale, averaged; touch_warmth is its temperature against her own skin over her receptors' span. In eighths these are exact per thing and distinct: apple texture 1, toy bear 4, bowl 0 (from the world's declared materials: 120,000/15, 800,000/300, 30,000/8); warmth 2 to 3 for room-temperature things, lower for a cold cup, higher for the lamp. Her hand tells the apple from the bear where her eye today cannot.
- **Mouth**: taste_residue, the residue of what she took in, decaying each beat; in eighths, zero when nothing was eaten recently.
- **Hunger**: her reserve deficit, in eighths.
- **Eye** (Level 1, in her as measured): the key of the figure under her gaze, today "a dark disc" or "a bright disc" (every thing in her world is a sphere without looks); joins the tuple as it is, and gains meaning when things have looks (world content, Joe's word).
- **Skin**: whether another body touched her this beat (the caregiver's touch), as its fraction in eighths.

## 3. The law (declared once)

- A **moment** is formed only on a beat on which a sound event closes (the beat the word ends). Its key is the SHA-256 (16 hex) of the tuple: (sound_event key, held thing's touch: texture eighths and warmth eighths or "none", taste eighths, hunger eighths, skin eighths, sight figure key or "none").
- **Stored**: `moments`: key → [count, last tick]; capacity 256, the least recently met leaves (her day law, as events and figures). Nothing else: no text, no similarity, no window over beats (that is Level 3).
- **Cost**: one hash on the beats a sound event closes; nothing on other beats. **Size**: at most 256 entries of a key and two integers, about 10 KB, declared.

## 4. What it does not do

It does not answer, choose, or value; her acts stay chosen from her record as today. It does not say what a word means: meaning is what followed a moment, by count, which is Level 3. It does not bind on beats with no sound: a thing held in silence is her hand's business, not a moment (a declared choice; A1 may argue for touch-onset moments too, measured).

## 5. Bars (measured before release)

1. The same recording of "apple" heard twice while she holds the apple (its taste residue and hunger the same in eighths) gives one moment key, met twice.
2. The same recording heard while she holds the bear gives a different key.
3. A beat with no sound event closing forms no moment; the store is bounded at 256 with recency; restore byte-exact; cost nothing measurable.
4. On her live body, over a day of the caretaker's naming while handing things ("apple" with the apple presented, "bear" with the bear): moments recur (count 2 or more) for the named things, reported as measured.

## 6. A1's co-draft

(For A1: touch-onset moments yes or no; the eighths grain for taste, hunger and skin; whether the caregiver's touch belongs in the tuple; the Level 3 window.)
