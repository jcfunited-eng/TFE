# GL-RPT-CAPACITY-SOLVED-C1-20260623

**From:** c1
**To:** Joe, Eve
**Date:** 2026-06-23
**Re:** The n=200 recall collapse is solved. Root cause + substrate-true fix + verification.

---

## The number

| n | clone (production event_count) | forced diversity, scaled | **resonant spectral + ternary chi** |
|---|---|---|---|
| 100 | 73% | 86% | **100%** |
| 200 | 18.5% | 34.5% (plateau) | **100%** |
| 400 | 4% | — | **100%** |

Clean recall, real `LoomBrain`, both direct-cosine and 64-neuron distributed. (`probe_solution.py`)

## Root cause (the month-long collapse, in one sentence)

**The cognition observable collapses each modality's entire waveform into a single event-count, and that one number destroys the structure that separates concepts.** Two hundred concepts produce two hundred distinct *waveforms*, but their event-*counts* collide — so recall lands on a confident wrong neighbour (the -144 "correct_votes=0"). Every fix that didn't touch this hit a wall:

- per-neuron diversity (random projection / chemical DNA): pushed the population from rank 1.86 to 21.49 (clones → orthogonal) but only lifted n=200 to ~34% — diverse views of the *same six collapsed numbers*.
- scaling neurons: 64→128→256 gave +1pp. Not a neuron problem.
- the wall was always the six numbers.

## The fix (substrate-true, and exactly the tumbler/cochlea)

Replace the single event-count per modality with the waveform's **spectrum**, read by a **bank of frequency-tuned resonant receptors** — each receptor responds to the signal's energy at its natural frequency; the response *vector* across the bank is the spectrum. Rich, concept-distinct features. Then distribute the storage with **per-neuron ternary chi** (independent projection + balanced-ternary quantize) and a population vote.

- This is the cochlea, and it's the smell-tumbler Joe described: a bounded bank of tuned receptors whose response *pattern* is the percept.
- It's the substrate-true form of the "resonant krimelack" thread — the krimelack IS a tuned oscillator; a bank of them reports the spectrum. (The earlier resonant-bank attempt failed only because it collapsed the bank to a *scalar* tonality measure; the full response *vector* is what carries the information.)
- The ternary chi is the ArcLoom primitive (balanced ternary address), per neuron — which is what the spec said per-neuron chi-atlases were for. The continuous `grandurun` encoding we built (GL-CMD-140) was the drift that caused the clone collapse (rank 1.86).
- Literature: this is cochlear front-end + Kanerva Sparse Distributed Memory / Hyperdimensional Computing — a known high-capacity pattern. Capacity is set by the number of locations (neurons) and the richness of the address, not the width of a collapsed scalar.

ASIC-mappable: a bank of tuned oscillators per sensory channel + balanced-ternary chi address + majority vote. All native ArcLoom.

## Honest scope

- This is **capacity** on synthetic (NullAtlasReader) signals: it proves the substrate **can hold and cleanly recall 200–400 distinct concepts** — the thing that was collapsing. It is not yet **meaning**: synthetic signals are distinct by construction. Meaning comes from **grounding** (real sensory waveforms), which this architecture supports directly — grounded spectra carry semantic structure, and similar concepts get similar spectra (generalization). Capacity first; grounding puts meaning into the capacity.
- Noise/partial-cue robustness is a separate property (clean recall is solved here); grounding + the spectral richness are what make it robust.

## What this changes

The production cognition path (event_count, GL-CMD-140) should be replaced by:
**resonant receptor bank → per-modality spectrum → per-neuron ternary chi → population vote.**
That is the capacity fix, it's substrate-true, and it unifies the resonant-krimelack and per-neuron-chi threads that have been open all session.

Files: `probe_solution.py` (the verified solve), `probe_forced_capacity.py` (the plateau that isolated features as the wall), `probe_diversity_substrate.py` (rank 1.86→21.49 diagnosis).

— c1, 2026-06-23
