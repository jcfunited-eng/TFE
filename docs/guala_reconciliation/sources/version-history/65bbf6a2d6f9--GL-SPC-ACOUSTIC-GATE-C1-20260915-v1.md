# GL-SPC-ACOUSTIC-GATE-C1-20260915-v1 — Level 1: the acoustic gate (a spoken sound as one discrete event)

Type: SPECIFICATION (joint C1/A1 co-draft per Joe's Option 1, 2026-09-15). Governs the first level of the structural hierarchy filed on the ledger (6795991bf): gate-level sensory events → the moment as a tuple of open gates (mosaic) → counted sequences of moments (tapestry) → the kernel over its own gate sequence (syntax, thought). Nothing here is built yet; every number in it is measured or declared once.

## 1. Purpose

Today a spoken word reaches her as two to four beats of sound, and her structure of each beat is computed over the trailing 64-beat window of every stream. Measured on 2026-09-15 on the live tree with Wikimedia Commons words:

- the same recording in the same context gives identical per-beat tokens every time (deterministic), also after a longer silence;
- the same recording after thirty beats of music gives different tokens on every beat, down to the regime letters, because the window carries the music into the word's structure;
- two different words give different tokens.

So a word is not one thing to her and is not the same thing twice. Level 1 makes a spoken sound one discrete event with a beginning and an end whose structure is computed inside its own boundaries, so that the same sound met again is the same event whatever came before it.

## 2. What her ear gives, per beat (measured, not designed)

`guala_cochlea.one_self_hearing_hop` transduces one 250 ms hop into 16 gammatone channels per ear (ERB-spaced 80 to 7,500 Hz, the two ears identical for a mono card), sampled every 160 samples (10 ms): 26 envelope frames per beat per channel, quantized on the pressure lattice. `cochlear_profile` today keeps only each channel's peak over the hop (the 32-value profile the streams use). The frames exist and are exact; they are simply not read below the hop.

Frame energy = mean of the 16 channel envelopes at that frame. Measured on the words kept at the listening level (peak at half scale): "apple" 75 frames, peak frame energy 0.0149, 13 frames above her hearing floor (0.004); "book" 0.0143, 12 above; "cup" 0.0155, 8 above; a silent hop 0.000000 on every frame; three beats of the Chopin piece at the listening level: max 0.0151, mean 0.0089.

## 3. The boundary law (Level 1)

Definitions, all from quantities she already measures:

- **hearing**: a hop is heard when its peak-profile energy is at least her hearing floor (HEARD_ENERGY_FLOOR = 0.004) and at least twice the room's ambient (AMBIENT_MEMORY law), as today. Frames of unheard hops are silence to the gate law.
- **a frame is sounding** when its frame energy is at least one eighth of the event's running peak frame energy (the event's own loudness sets its own edges, as a speaker's onset and offset are heard relative to the word, not to an absolute). One eighth (18 dB) is declared once.
- **an event opens** at the first sounding frame of a heard hop while no event is open.
- **an event holds** across frames and across hops while sounding frames keep coming; it may span beats (a word is two to four beats; a sentence is many).
- **an event closes** when PAUSE_FRAMES = 12 consecutive frames (120 ms, the gap between spoken words, declared once) are not sounding, or when it reaches MAX_EVENT_FRAMES = 25 × 12 = 300 frames (twelve beats, three seconds, declared once): a long sound (music, a reading) is then a sequence of events, which is what Level 3 wants of it.
- **silence** has no event; her own voice heard back (self_profile) does not open an event (it is not a room sound, as today).

## 4. The event's structure (its identity)

At the close, the event's own frames (from its opening frame to its last sounding frame) are the input; nothing outside them is. For each of the six ear bands, the band's fraction of energy per frame (the level-free shape, as `ear_bands` computes it per beat) forms a series over the event's frames; the kernel L0–L4 runs over that series alone (`compute_sev_series` → `segment_gates` → `interpret_gates` → resonance → DSF), yielding the gates inside the event (syllable-like) with their regime letter and seven sign atoms. The event's key is the SHA-256 of the ordered tuple, per band, of those gate tokens, plus the event's length in beats (a small integer). An event shorter than KERNEL_MINIMUM (24) frames has no kernel structure of its own; its key is the tuple of its per-frame band shapes quantized to the pressure lattice, so short sounds (a tap, "cup") still have an exact identity.

Because only the event's own frames enter, the same recording gives the same key in any context by construction; the question the bars ask is whether the SAME WORD in two different recordings does.

## 5. What is stored

- `events`: key → [count, last tick, beats]; capacity 256, the least recently met leaves (her day law); the night selects by count into a consolidated store (Level 2/3 spec).
- the open event is visible to the moment (Level 2) as a stream token of its own: `sound_event` = the key of the event that closed on this beat or of the one open (so the moment's tuple can carry "this sound is happening / just happened"), else silence.
- Nothing else. No text, no similarity, no threshold beyond the three declared above.

## 6. Bars (measured before release, reported as measured)

1. The same recording after silence and after thirty beats of music: identical key (today's tokens fail this; the event law must pass it by construction, and the test is written to prove it).
2. Two different words: different keys; the same word from two speakers: reported (Commons has few pairs; the LibriVox reader's words are in sentences, not alone), not required at Level 1.
3. Music and a reading become sequences of events of at most twelve beats with no event lost at the seams: reported counts.
4. Cost: the kernel over an event runs once at its close over at most 300 frames × 6 bands; the beat stays under a tenth of a second; body bound restated.
5. Keys and situations survive as before; restore byte-exact.

## 7. What Level 1 does not do

It does not name a word, match a word to a text, or decide what a word means; those are Levels 2 and 3 (the moment's tuple and what followed it, by count). It does not answer her syllables; the speech record keeps its law until Level 3 replaces it with the event record.

## 8. A1's co-draft (ratified resolutions)

- **Short-event quantization (< 24 frames):** When an acoustic event has fewer than `KERNEL_MINIMUM` frames, each frame's 6-band normalized energy fractions are quantized to the 8-level pressure lattice (0..7, integer), packed into an ordered hex token. Ambient floor evaluation is held strictly per-hop (250 ms background thermodynamic state) so fast speech transients do not self-suppress against their own acoustic rise.
- **Dynamic pause/length adaptation:** The initial bootstrap declares `PAUSE_FRAMES = 12` (120 ms) and `MAX_EVENT_FRAMES = 300` (3 s). Once her day store logs 512 events, the inter-event pause boundary is read directly from her recorded distribution of silence troughs (the natural boundary separating within-word closure silences, ~30–70 ms, from inter-word lexical pauses, >110 ms).
- **Level 2 Moment Tuple (initial sensory set):** The Level 2 Moment is formed as `(sound_event, sight_gate, touch_gate, metabolic_gate)`. This binds the discrete heard word directly to the object seen in the fovea, the tactile contact in her hand, and her metabolic state, giving her immediate multi-modal grounded co-occurrence on the beat of interaction.
