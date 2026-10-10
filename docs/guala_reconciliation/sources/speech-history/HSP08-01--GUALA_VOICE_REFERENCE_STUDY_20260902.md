# Voice reference study — complete, accepted (bench v22, 2026-09-02)

Author: Claude (experience lane). Status: ACCEPTED by Joe's ear, final
word "Yep that's it" on bench v22. Ground truth: the "Toy Vocal Organ"
artifact page, bench v22 — deterministic JS source-filter bench, browser
only, zero production contact. This document is the complete component
spec the organism-owned organ must hit, plus every failure mode found on
the way and how each was diagnosed.

Accepted board (all little-girl voice): ahh, ohh, eee, ay, uh-oh,
sss, shh, mmm, ma-ma, see, shoe.

## 1. Method: the ear as the instrument

Joe's one-word verdicts were treated as precise physical diagnoses and
each mapped to a mechanism. The full ladder:

| Verdict | Physical defect it named |
|---|---|
| "buzz" | valve never closed (no closed phase in the cycle) |
| "bad flute" | closure too smooth — excitation too weak |
| "toy keyboard synth" | stationary note — voices must MOVE |
| "old china man" | human at last; wrong age + contours read as lexical tones |
| "thrown up in the air" | CONTINUOUS pitch glide through the vowel = motion percept |
| "the dials did nothing" / "no change" ×3 | big glides masked every finer ingredient |
| "piano + kazoo" | dead spectrum + hard closure corner (all harmonics screaming) |
| "static mixed in" | breath injected as white noise instead of colored air |
| "boy side and scratchy" ×2 | pressed closure reads male; corner aliasing + comb-y room = scratch |
| "way far from a little girl" | scaled-adult throat is not a child throat |
| "who" (for mmm) | lips not really shut — murmur kept vowel shape |
| "only s and sh" (see/shoe) | REAL BUG: hiss amplitude reference 100× wrong |
| "shoooo" | demonstration-stretched timing; words must run at spoken length |

Process rules proven by this arc:
- When several real changes land as "no change", suspect a dominant
  masker or an untouched factory — and verify the LISTENING PATH first
  with exaggerated calibration pairs (low/high, still/waver,
  clean/breathy). Joe's path was clean; the recipe was the defect.
- One ingredient per button (layer test) turns a vague percept into a
  named mechanism in one listen.
- Bit-identical repeats read as a machine; every "say" must vary.

## 2. Frozen source recipe (the valve)

- Continuous phase-accumulator cycle. NEVER quantize periods to whole
  samples — the rounding is audible grit. Sample rate 32 kHz minimum;
  16 kHz aliases the closing edge (the "kazoo").
- Pulse shape: half-cosine rise; closing edge STEEP BUT SMOOTH-ENDED
  (raised-cosine fall). A hard corner folds ultrasonic energy back in
  OFF the harmonic ladder at child pitch. "The snap" (hard corner) from
  early iterations is WRONG — superseded.
- Little-girl setting: open quotient ~0.71, rise:fall asymmetry ~1.8.
  A pressed closure (low OQ, hard asym) reads MALE at any pitch.
- Spectral tilt: one-pole lowpass on the flow at ~1800 Hz (girl)
  before radiation. Radiation = first difference of flow.
- Micro-life: per-cycle jitter ~0.06%, shimmer ~0.45% (trace only),
  PLUS slow aperiodic drift ±0.8% (random targets every 0.22 s,
  cosine-eased). Sinusoidal vibrato reads as machinery.
- Loudness arc: peak ~45 ms after voicing onset, decay ~45% through
  the vowel, ~100 ms release. Constant loudness = piano. The arc
  anchors at the first VOICED sample (a leading hiss must not own the
  loud part).
- End of utterance: at most a whisper of alternating-cycle creak
  (girl fry ≤ 0.18, last 10%); more reads scratchy.

## 3. Frozen throat recipe (resonances)

- FIVE formants minimum. F4/F5 for the girl ≈ 4375/5625 Hz.
- Child formant VALUES from measured children (Peterson–Barney child
  data), then ×1.09 for the girl (shorter tract than a boy same age):
  /a/ 1030/1370/3170 · /o/ 580/1120/3350 · /i/ 370/3200/3730 ·
  /e(ay)/ 690/2610/3570→480/3000/3700 · /u/ 445/1150/3300→405/980/3260.
  Scaled-adult formants are NOT child formants.
- Child bandwidths WIDE and lossy: [180,160,260,340,400]. Adult-narrow
  bands ring metallic at high F0.
- Pitch law: median ~360–375 Hz; gentle −4.5% declination through the
  vowel body with a small extra ease in the final ~0.13 s UNDER the
  fade. Never a continuous slide (thrown-through-the-air percept);
  never a hard final drop (Mandarin falling-tone percept). Steps
  BETWEEN syllables are fine and natural.
- Throat pre-shaped before voicing begins (no onset glide from
  neutral); glides only between segments (~60 ms) — this same
  machinery gives diphthongs and the m→a break for free.
- Rounded vowels MOVE: /u/ keeps sinking (445/1150 → 405/980) as the
  lips round. A held /u/ shape is wrong.

## 4. Breath (aspiration)

- Colored air, not static: noise lowpassed ~1500 Hz before entering
  the throat, amplitude ×(0.25 + 0.75·valve openness) so it puffs
  with the cycle.
- Level must be MEASURED, not assumed: at first wiring it sat −24 dB
  under the voice (inaudible); audible breathiness needs ≈ −8 to
  −10 dB for "very breathy", a gentle presence for normal speech.

## 5. Consonants

- S: UNVOICED turbulence jet at the teeth on its OWN path (never
  through the vowel formant cascade): noise → one resonant band
  ~6.8 kHz (bw ~2 kHz), ~25 ms smooth air edges. Level ~0.5 of the
  measured voiced peak standalone, ~0.35 in-word.
- SH: same jet, wider and further back: band ~2.9 kHz (bw ~1.1 kHz).
  In-word fricatives must be SHORT (~110 ms): held length reads as an
  escaping-valve leak.
- M: voiced murmur with lips truly shut = a real lowpass (~600 Hz
  one-pole) over the m spans + gain ~0.42. Without the lowpass the
  murmur keeps vowel shape and reads as "who". Murmur formant targets
  280/1150/2400 feeding the normal glide machinery produce the m→a
  release naturally.
- Word timing at spoken length (shoe ≈ 0.42 s total). Demonstration
  stretching reads wrong even when every ingredient is right.

## 6. Presentation layer (matters more than expected)

- Per-say variation: each utterance gets its own seed, ±3.5% pitch,
  ±7% pace. Identical repeats = machine.
- A small room: sparse SOFT early reflections (8 taps 13–86 ms, gains
  0.13→0.017, wet lowpassed 3.2 kHz). Bone-dry output reads as a
  synthesizer; but hard/loud taps comb-filter into boxy scratch —
  the room must be gentle.

## 7. Bugs found (check for these in the organism organ path)

1. Amplitude-reference fallback: the voiced path legitimately runs at
   tiny internal amplitude; a "if voice < 0.01 assume 1.0" fallback
   injected hiss ~100× too loud and final normalization crushed the
   vowel to silence. Ear symptom: "see and shoe sound only like s and
   sh". Rule: reference measured scales, never assumed ones.
2. Loudness arc anchored at utterance start instead of voicing start
   starves any vowel that follows a consonant.
3. White (uncolored) noise anywhere in the voice path reads as radio
   static, and it also masquerades as "jitter/scratchiness" — cutting
   real jitter does nothing while it remains.

## 8. Organism translation notes

In the organism these numbers must ARISE from real mechanisms, not be
painted on: the breath drive lawfully supplies drift/jitter/shimmer
and aspiration; the room comes from the world model; per-say variation
comes from real state differences. The numbers above are the
ACCEPTANCE TARGET Joe's ear ratified, and the bench page (v22) is the
standing A/B instrument: play the organ's output next to the bench
button for the same utterance; Joe's ear is the final gate.

Ledger trail: faf1f33d (frozen v17 voice), 0562f0d5 (consonants +
found bug), 41c84868 (full-board acceptance).
