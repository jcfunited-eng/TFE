# Meaning was never an encoder problem — it's the senses. (C1, 2026-06-24)

## The correction
Earlier I concluded "capacity and meaning need different representations
(spectrum vs profile)." **That was wrong.** One representation does both.

## The proof (60 grounded concepts, substrate ternary-chi encoder, 64-neuron pop)
Feed the SAME encoder three different inputs and measure semantic structure
(Spearman of representation-similarity vs grounding-similarity) and recall:

| input to the encoder                  | meaning rho | recall | nearest-neighbour |
|---------------------------------------|------------:|-------:|-------------------|
| true grounded profile (ceiling)       |  **+0.998** | 100%   | stone→pebble,onyx,silver · quartz→crystal,marble |
| catalog **mean** profile              |   +0.449    | 100%   | quartz→crystal,silver,marble |
| `transduce()` **noisy sample**        |   +0.045    | —      | random |
| resonant **spectrum** (capacity path) |   +0.066    | 100%   | random |

## What this means
- **The encoder (resonant ternary chi) already delivers capacity AND meaning at
  once** — rho 0.998 with 100% recall — when fed the true per-channel grounded
  profile. No second representation needed.
- **The meaning failure is entirely upstream, in the senses:**
  - `transduce()` returns `rng.normal(mean, std)` — a single noisy instance.
    Meaning lives in the profile **averaged over exposures** (the mean). Reading
    the mean instead of a sample jumps rho 0.045 → 0.449.
  - The catalog mean is itself a degraded copy of the truth (0.449 vs 0.998
    ceiling) — pipeline fidelity loss between authored grounding and what the
    senses hand the encoder.
- **The resonant spectrum is the wrong read for meaning** (rho 0.066): it
  mean-subtracts (`s - s.mean()`), keeping oscillation for capacity and throwing
  away the amplitude profile where meaning lives. Correct for em/pr/ep, wrong for sc.

## The fix path (substrate-true)
1. `sc` (semantic) reads the **stable mean profile** (averaged percept), not a
   per-instance sample, not the spectrum. Proven: rho 0.449 today, 0.998 ceiling.
2. **Senses fidelity**: make the catalog→transduce path preserve the grounded
   profile faithfully (close the 0.449→1.0 gap). This is the "prove the senses
   machinery" step — meaning rises directly with senses fidelity.
3. Same encoder serves em/pr/ep (spectrum, capacity) and sc (profile, meaning);
   they are two reads of one sensory input, not two substrates.

## Status
Diagnosis proven with numbers. `sc` not yet wired into the seed; senses-fidelity
fix not yet done. Next increment: wire sc(mean-profile) + raise senses fidelity.
