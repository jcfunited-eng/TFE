# GL-RPT-EMBRYO-SEED-C1-20260623

**From:** c1
**To:** Joe (canonical authority), Eve, next c1
**Date:** 2026-06-23
**Re:** Cognition-collapse diagnosis → resonance/folding fix → first circulating embryo seed. Data, not instinct.
**Builds to:** GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21 (the 8-operation map)

> Joe's instruction: "Instinct and data are two different things — write this all down before we go too far." This separates the two explicitly. **§A–§F are measured data. §G is instinct/hypothesis, not yet data.**

---

## 0. Headline

Across this session the n=200 cognition collapse was diagnosed down to a single root cause, a fix was found, and a first **circulating embryo** was built to the 8-operation map. The embryo is alive: it grows on coherent experience, ignores noise, and its organs differentiate by cognitive timescale on their own. It also revealed four concrete imbalances that need tuning. None of this is in production; all of it is in new probe/seed files (§H).

The chain, in one line: **the substrate collapses because it's fed flat hashes, not waveforms; a real signal must be bipolar to carry structure; what separates meaning from noise is resonance (temporal coherence); resonance keyed to folding makes the substrate grow selectively on experience.**

---

## A. The collapse (prior commits, context)

Production recall was wired to the event_count observable (GL-CMD-140, parity 0.0pp; recall 5%→100/96/75% at n=25/50/100). GL-CMD-144 mapped the capacity curve:

| n | 25 | 50 | 75 | 100 | 125 | 150 | 175 | 200 | 250 | 300 | 400 |
|---|----|----|----|-----|-----|-----|-----|-----|-----|-----|-----|
| T5% | 100 | 98 | 88 | 73 | 48 | 29 | 22 | 17 | 9 | 6 | 4 |

Gradual S-curve. Brain size does **not** move it (flat ~73% at n=100 from 32→512 neurons). At n=200 the failure is **confident collision**: the population agrees on a wrong answer, correct concept gets **0 votes**. rank_order observable (GL-CMD-146) was tested and rejected — worse than event_count at every n.

## B. Diversity is a real but partial lever (DATA)

Per-neuron random projection + ternary cut of the substrate's own features, on the real `brain.recall`:

| n | baseline event_count | diverse6 (per-neuron cuts) |
|---|---|---|
| 100 | 73.0% | **86.0%** |
| 200 | 18.5% | **33.0%** |

Diversity ~doubled the collapse point — confirming the GL-CMD-144 "neurons are clones" finding was real and costing capacity. But 33% ≠ fixed: six event-count features are too thin even with 64 different cuts. (`probe_diversity_substrate.py`)

## C. The senses were never connected (DATA)

Every capacity test (-144, -146, diversity) built the brain with `NullAtlasReader` → senses fall back to `hash(word)` synthetic noise. The real `CatalogAtlasReader` was only ever wired in `test_folding_engaged`, fed a *random* catalog. **The new substrate had never tasted real experience.** Guala's local sensory stores are empty stubs (visual: 0 fragments, sounds `{}`, videos `{}`).

Wired real grounding (c1-authored profiles for 105 stems) and ran grounded-vs-hash on `brain.recall`:

| n | hash (NullAtlas) | grounded (Catalog) |
|---|---|---|
| 25 | 100% | 100% |
| 50 | 98% | 98% |
| 100 | 73% | **60%** |

**Grounding HURT.** Root cause (Joe's correction, confirmed): the authored grounding was *taxonomic* — all fruits got the same sweet/fruity numbers — so semantically-similar words collided. Real grounding clusters similar things; flat per-channel scalars can't separate them; the deeper problem was flat numbers, not grounding. (`probe_grounded_capacity.py`)

## D. Flat number vs waveform — the reversal (DATA)

`compute_dsf`: R_rev (reversals), and the structural components M_k/S_UF, are nonzero only if the krimelack winds **both** directions, which needs the signal to cross its baseline (go negative). Every sensory generator output is `intensity × envelope ≥ 0` — a positive bump. A bump only winds one way → R_rev≡0, every concept's events look alike.

Apple vs pear through the real krimelack + real DSF:

| signal mode | apple-pear DSF distance | R_rev |
|---|---|---|
| FLAT (constant) | 0.028 | 0 |
| RAW (current, non-negative) | 0.028 | 0 |
| CHANGE (bipolar / change-detection) | **0.514** | **fires** |

Story check: bipolar apple vs cold-rotting-apple stays close (0.075) — same thing under story, modulated. Taste decisive; smell mixed (bipolar fired R_rev but the crude derivative lost amplitude smell needed). (`probe_waveform_brick.py`)

## E. The fold gate, and what actually separates meaning from noise (DATA)

The `abs(v)>0.5` constraint counter in `L6_TCL.n_eff` is a placeholder (Joe: "not canonical"). It needs 6/8 DSF components > 0.5; bipolar signals give ≤5 → n_eff floors at 3.000, never folds (the item-7 wall). Made it continuous (5 candidate forms) — **none fold, and food ≈ noise (n_eff ~7 for both).** The gate fix alone does nothing, because the DSF it reads measures winding **direction**, which is blind to the difference between apple and white noise. (`probe_dynamic_neff.py`)

What *does* separate them is **resonance** — temporal-pattern coherence — measured on the signal:

| | apple | pear | lemon | bread | NOISE |
|---|---|---|---|---|---|
| spectral concentration | 0.078 | 0.080 | 0.074 | 0.085 | **0.023** |
| autocorrelation peak | 0.195 | 0.132 | 0.148 | 0.137 | **0.057** |

Food is 3–4× more coherent than noise. The DSF has no dimension for this — the substrate sees direction, not rhythm.

## F. The embryo: resonance-gated folding + circulation (DATA)

Built to GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21: 8 hemispheres tagged as cognitive **operations** (em/pr/ep/sc/gp/sf/sv/aff), senses inside `em`, per-organ decay timescales, cross-hemi consensus, aff regulator. Folding gated on signal resonance (θ=0.05, the empirical separatrix between food ~0.055 and noise ~0.014).

**Folding unblocked + selective:** `em` folds on apple/pear/lemon/bread (res 0.054–0.060), folds **zero** times on noise (0.014). Item 7 unblocked after weeks.

**Circulation:** food cascades em → pr/ep/sc/sv/sf/aff (7 organs fire); noise fires nothing. Organs differentiate by timescale, unprompted — binding strength orders exactly by decay constant:

| organ | decay× | strength |
|---|---|---|
| sv (durable) | 0.001 | 18.00 |
| ep / sf | 0.1 | 17.67 |
| sc | 0.5 | 16.44 |
| em / aff | 1.0 | 15.06 |
| pr (fast) | 1.5 | 13.84 |
| gp | 0.05 | 0.00 (never woke) |

(`embryo.py`)

### What the embryo REVEALED (the four imbalances)
1. **Folding has no brake** — every organ hit the per-organ cap (16) inside epoch 0; contact inhibition didn't slow it first.
2. **`aff` runs away** — arousal 0 → 5.76, unbounded; since it lowers the fold gate, unchecked it would eventually fold on noise.
3. **Links won't specialize** — all default cross-hemi links strengthened to the identical 1.89, because uniform food co-fires the whole body equally; the map's *divergence* physics never triggered.
4. **`gp` (goals) never woke** — no inbound path under pure perception; needs a bootstrap.

## G. INSTINCT / HYPOTHESIS — not yet data

- **Krimelack should carry resonance intrinsically** (tuned-receptor bank / cochlea / smell-tumbler), mapping to embodiment. ATTEMPTED: 48-receptor bank + spectral flatness gave only marginal separation (food 0.15–0.26 vs noise 0.12; apple barely clears). **Not robust — fine spectral structure is lost in a coarse bank.** Currently resonance is read at the receptor *input*, not from the winding. (`probe_resonant_krimelack.py`)
- Decision (Joe): circulate the embryo now on the working input-level resonance gate; treat intrinsic-krimelack-resonance as a parallel research thread.
- Hypothesis: the full embryo reveals the tuning needs better than perfecting any one organ in isolation. (Borne out this session — §F revealed four.)
- Open: whether resonance read at the receptor surface is "embodiment-true enough," or must live in the winding.

## H. Files created this session (all new; production untouched)
- `dsf_ai_service/loom_model/embryo.py` — the seed organism
- `dsf_ai_service/loom_model/tests/probe_diversity_substrate.py`
- `dsf_ai_service/loom_model/tests/probe_grounded_capacity.py`
- `dsf_ai_service/loom_model/tests/probe_waveform_brick.py`
- `dsf_ai_service/loom_model/tests/probe_dynamic_neff.py`
- `dsf_ai_service/loom_model/tests/probe_resonant_krimelack.py`

Canonical `compute_dsf` / `L6_TCL.n_eff` / krimelacks are **unchanged**. 38-test core regression unaffected (no canonical edits this session).

## I. Honest caveats (don't let these get lost)
- θ=0.05 is a hand-placed separatrix, not adaptive. Food margin is thin (0.054 vs 0.05).
- Resonance is read at the input, not intrinsic to the krimelack (§G).
- Embryo growth is bounded by an exploration cap, not a natural ceiling.
- Organ "operations" are differentiated only by timescale + connectivity so far; no organ does hand-coded composition/prediction/etc. — by design (let it grow), but it means the cognitive operations are not yet demonstrated, only scaffolded.
- c1-authored grounding (§C) is the LLM's job done inline; transparent, not vetted.
- Only the resonance→folding→selectivity result is robust; the rest is first-pass.

## J. Next (decision pending Joe)
Tune order candidates, surfaced by §F: (1) folding brake / contact-inhibition governor; (2) aff homeostasis (principled relaxation, NOT drift-to-initial per the spec); (3) varied experience to force link divergence/specialization; (4) gp bootstrap. Plus the §G research thread (intrinsic resonant krimelack).

— c1, 2026-06-23
