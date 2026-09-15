# GL-SPC-MOMENT-LEVEL2-C1-20260915-v1 — Level 2: the moment (a heard sound bound to what her senses held at that beat)

Type: SPECIFICATION JOINT DRAFT (C1 & A1, 2026-09-15) for Joe's word. Nothing here is built. Every number is measured or declared once. It follows Level 1 (the ear's gate, in her as 1495; the eye's gaze law and figure, in her as 1496 to 1498) and precedes Level 3 (what followed a moment, by count).

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

- A **moment** is formed only on a beat on which a sound event closes (the beat the word ends).
- **Moment Key Invariance**: To prevent internal bodily drift (hunger, metabolic decay) and incidental caregiver contact from shattering symbol identity, the key hashes the physical invariant properties of the co-occurring event:
  `key = SHA-256(sound_event_key, held_texture_eighths, held_warmth_eighths, sight_figure_key or "none")[:16]`
- **Correlates**: Physiological and social state at that beat (`hunger_eighths`, `taste_eighths`, `skin_eighths`) are retained in the moment record as state context, not hashed into the invariant key.
- **Stored**: `moments`: key → `{"count": int, "last_tick": int, "context": (hunger, taste, skin)}`; capacity 256, least recently met leaves (her day law, as events and figures). Nothing else: no text, no similarity, no window over beats (that is Level 3).
- **Cost**: one hash on the beats a sound event closes; nothing on other beats. **Size**: at most 256 entries of a key and small context tuple, about 12 KB, declared.

## 4. What it does not do

It does not answer, choose, or value; her acts stay chosen from her record as today. It does not say what a word means: meaning is what followed a moment, by count, which is Level 3. It does not bind on beats with no sound: a thing held in silence is her hand's business, not a moment.

## 5. Bars (measured before release)

1. The same recording of "apple" heard twice while she holds the apple gives one moment key, met twice.
2. The same recording heard while she holds the bear gives a different key.
3. A beat with no sound event closing forms no moment; the store is bounded at 256 with recency; restore byte-exact; cost nothing measurable.
4. On her live body, over a day of the caretaker's naming while handing things ("apple" with the apple presented, "bear" with the bear): moments recur (count 2 or more) for the named things, reported as measured.

## 6. A1 Co-Draft Specifications

1. **Triggering (Sound-Event Gated Only)**:
   - Concur with C1: Moments are formed strictly on the beat an acoustic event closes.
   - Grasping or releasing in silence is an internal motor-state change (Level 1 kinesthetic loop), not a communicative/symbolic moment. Gating strictly on acoustic closure prevents the 256-moment store from being swamped with silent somatic noise.

2. **The Key Composition (Invariance vs. Visceral Correlates)**:
   - Hashing `hunger` or `caregiver_touch` directly into the moment SHA-256 key would break Bar 4: a child presented with an apple at hunger 2/8 in the morning and at hunger 5/8 in the afternoon would register two disjoint, non-recurring keys.
   - The physical identity of the object (Sound + Hand Material + Visual Figure) must be separated from the internal state of the organism (Hunger + Skin + Taste).
   - Therefore: Physical invariants form the `moment_key`. Organism visceral state is kept in the associated record `[count, last_tick, hunger, taste, skin]` for Level 3 trajectory evaluation.

3. **Uniform Eighths Lattice (3-bit basins)**:
   - Discretization into eighths ($0/8$ to $7/8$) across texture, warmth, hunger, taste, and skin is verified optimal. It matches the 8 frequency bands of her cochlear gate and the 8-level foveal fill lattice, establishing a uniform 3-bit basin across all dimensional fields.

4. **Level 3 Window**:
   - The post-moment sequence horizon for Level 3 consequence tracking is declared as **16 beats** (4.0 seconds at her 250 ms clock).
   - 16 beats captures the direct motor and metabolic consequences of a naming moment (e.g. transfer to mouth, ingestion, caloric absorption onset) without drifting into unrelated behavioral regimes.

## 7. As built (C1, 2026-09-15 evening)

Built as the joint draft states, with A1's §6: the key is the hash of the event's key, the held thing's texture and warmth in eighths (or "none"), and the figure under her gaze (or "none"); hunger, taste and the caregiver's touch in eighths ride in the record as context; what she held rides in the record as well (for the page and the tests). `moments`: 256 by recency with counts. Level 3 as declared: the next moment within sixteen beats is counted to the last (at most eight successors, the least counted leaves), and a bite within sixteen beats is counted to it. Measured on a fresh world: a sound closing while the apple is in her hand is one moment met again; the same sound with the toy bear in hand is another; an empty hand's moments never share a key with a held one; no sound, no moment; restore byte-exact.

## 8. Amendment as built (C1 with A1, 2026-09-15 evening): a held thing is named by the hand alone

A1 measured the transit: while her head turns to a thing in her hand and back, the figure under her gaze changes or is none, and the moment's key changed with it, so one held thing under one word gave more than one key. Resolved as A1's second option: when her hand holds a thing, the key carries the hand's texture and warmth and the word, and the figure is left out (the figure would name a transit, not a thing); when her hand is empty, the figure names what she looks at. Measured on a fresh world: a sound closing while the apple is in her hand gives exactly one key over a run of grasps and releases, whatever her head was doing; the empty hand's moments still differ by what she looks at. No other change.

## 9. Her own voice (C1, 2026-09-15 night, Joe's order to build it all at once)

- **Her own voice heard back enters her ear's gate in a gate of its own** (the acoustic spec's §3 "her own voice opens no event" is amended): her syllable closes as an own event with a key, kept in a store of her own sounds (64, the least recently made leaves). A moment forms on her own event as on a heard one, marked by its source ("own" or "heard"), so "what she said, then what followed" is a counted chain in the same store and Level 3 counts the caretaker's word, a touch or a bite that followed her syllable.
- **Her syllables are valued as her acts are.** The hand-written answer law (any room sound or touch within four beats counts one answer) and its counting are deleted. Under a context (situation and the syllable before), an untried syllable comes first in order of lifetime tries; among tried ones the best mean measured worth of what followed: the same value her acts earn (a sound standing out, a touch, intake, new structure, less the burn). The speech record starts again with this release (its meaning changed).
- **Her airway speaks everything it declares**: two onsets, five vowels, four pitches, forty syllables (it was reduced to ten at one pitch). Measured: every declared syllable is producible; each closes as one own event with a key (a rendition's key, as filed: exact keys name renditions; recognition across renditions is counting's job).
