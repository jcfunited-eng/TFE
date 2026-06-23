# GL-RPT-ML-CONTAMINATION-AUDIT-EVE-20260618-07

**From:** Eve
**Date:** 2026-06-18
**Subject:** Complete audit of substrate files for ML-shaped mechanisms disguised in substrate vocabulary
**Method:** Grep across all substrate files for: random matrices with physical names, homeostatic control loops, magic-number hyperparameters with tuning-history comments, inconsistent constants across files, adaptive thresholds, ML-style decay/boost/gain parameters.

This audit is complete to my current ability. Files scanned: assemblage.py, gl_nmda.py, gl_plasticity.py, deep_atlas.py, krimelack.py, grounded_vocab.py, grounded_vocab_integration.py, sensory_generators.py, event_log.py, ring_buffer.py, persistence_consumer.py, v7_engine.py, GL_MDL_MULTIMODAL_DEEP, GL_MDL_FOLDED_CHI, GL_MDL_COGNITION, GL_MDL_COMPOSITION, GL_MDL_PRIMITIVES.

---

## CATEGORY A — Random matrices masquerading as physics

These have substrate-physics names but are random Hermitian matrices with no physical content.

**A1. `H_base = random_hermitian(N, scale=0.6)`** — assemblage.py:100
"Base Hamiltonian" is a random matrix. Has no physics. Already addressed by brief -06 for emission sections; remains random in all other sections.

**A2. `law_fields["symmetry"] = random_hermitian(N, scale=0.5)`** — assemblage.py:104
Named "symmetry," is noise.

**A3. `law_fields["consistency"] = random_hermitian(N, scale=0.5)`** — assemblage.py:105
Named "consistency," is noise.

**A4. `law_fields["compactness"] = diag(linspace(-1, 1, N)) * 0.5`** — assemblage.py:106
Has structure (eigenvalue gradient) but the name "compactness" describes nothing about what it does. The operator pushes psi toward eigenvectors aligned with one end of the basis. Mis-named but structured.

---

## CATEGORY B — Homeostatic control loops (regularization disguised as substrate)

**B1. Gamma self-evolution block** — assemblage.py:580-602
Every `SELF_EVO_PERIOD=40` ticks, computes section's three-axis (entropy/coherence/greed). If `entropy < 0.3` for ≥2 streaks, decrease gamma["symmetry"] and gamma["consistency"]. If `coherence < 0.3` for ≥2 streaks, increase gamma["consistency"]. If `greed > 0.7` for ≥2 streaks, increase gamma["compactness"]. Plus a `GAMMA_DRIFT` term pulling all gammas back toward defaults each tick.

This is ML-style regularization with substrate vocabulary. It does not implement neural homeostasis (Turrigiano's synaptic scaling preserves firing rate, not gamma values).

**B2. `gamma_homeostasis(rate=0.001)`** — assemblage.py:111-115
Explicit drift-toward-initial method: `gamma[k] = (1-rate)*gamma[k] + rate*_initial_gamma[k]`. Pulls gamma back to defaults.

**B3. `homeostasis_pull(rate=0.001)`** — assemblage.py:236-244
**Anti-learning mechanism.** Drifts `mode_bank` toward its random initial state. So if experience reinforces a mode, this mechanism gradually pulls the mode back toward random. Comment says "Strong reinforcement wins; weak warping decays" — but the math erodes ALL reinforcement, just at different rates.

This is named "synaptic scaling" (a real biological process) but does the opposite of what synaptic scaling does in biology.

**B4. `decay_modes` mode_strength toward 1.0 baseline** — assemblage.py:247-256
`mode_strength[i] = 0.999 * mode_strength[i] + 0.001 * 1.0` every tick. Strengths regress to mean. Above-baseline learning decays down; below-baseline recovers up.

**B5. `out_of_range_streak["entropy"/"coherence"/"greed"]`** — assemblage.py:97
Counter tracking how long each statistical property has been out of preset ranges. Feeds B1.

**B6. `_initial_gamma = dict(GAMMA_DEFAULTS)`** — assemblage.py:109
Snapshot for B2's drift target.

**B7. `snapshot_initial_modes()`** — assemblage.py:232-234
Snapshot for B3's drift target.

---

## CATEGORY C — Adaptive thresholds (ML-style)

**C1. `novel_thresh = 0.30 / (1.0 + 0.05 * max(0, len(mode_bank) - 5))`** — assemblage.py:185
Threshold for novel-mode commits decreases as mode_bank grows. ML-style adaptive curve.

**C2. `effective_det_commit(current_tick)`** — assemblage.py:117-120
Lowers commit threshold during excitation pulse: `max(0.10, det_commit - excitation_strength)`. Time-dependent threshold.

**C3. `effective_p_commit(current_tick)`** — assemblage.py:122-124
Same pattern. Time-dependent threshold modulation.

**C4. `target = 0.30 + (1.10 - 0.30) * (1.0 - recent_rate)`** — assemblage.py:381
Adaptive emission-rate target. As recent rate increases, target decreases. Pure RL/control-theory pattern with no physics motivation.

**C5. `BOOTSTRAP_MAX` counter** — assemblage.py:174-175
Limits how many "bootstrap" commits can fire before requiring evidence pressure. ML bootstrap pattern.

---

## CATEGORY D — Magic-number hyperparameters with tuning-history comments

These are the smoking guns — comments reveal the parameters were tuned to produce specific behaviors, not derived from physics.

**D1. `MGN_FOCUS_BOOST = 1.5     # was 2.0 — softer to reduce feedback runaway`** — MULTIMODAL_DEEP.py:44
Tuned down from 2.0 because 2.0 caused runaway. Tuning history in code.

**D2. `TOP_DOWN_BOOST = 1.15     # gentle feedback — avoids 1.5 loop, breaks the 1.0 no-op`** — MULTIMODAL_DEEP.py:46
Tuned to a specific value to avoid two specific failure modes. Pure tuning.

**D3. `ACT_DECAY = 0.65    # slower decay so cascade can accumulate over ticks`** — COGNITION.py:39
Tuned to achieve a target behavior.

**D4. `COHESION_THRESHOLD = 0.30    # lower threshold — substrate emits with less pressure`** — COGNITION.py:41
Tuned downward to get more emissions. Anti-physical.

**D5. `DECAY_LAMBDA = 0.0005    # slower decay than deployed — accumulates more easily`** — COGNITION.py:34
Tuned to be slower than the deployed substrate's decay.

**D6. `Tuned params for text: kappa=80, threshold=pi/3, dt=0.04`** — krimelack.py:14
Explicit "tuned params" comment. The `threshold=pi/3` could be principled (phase-rotation threshold). `kappa=80` and `dt=0.04` are tuned values without physical derivation.

---

## CATEGORY E — Inconsistent constants across files (independent tuning, no canonical version)

Same conceptual constant, different values in different files. Indicates each file was tuned independently.

| constant | MULTIMODAL_DEEP | COGNITION | deep_atlas |
|---|---|---|---|
| `ACT_DECAY` | 0.55 | 0.65 | — |
| `CASCADE_GAIN` | 0.30 | 0.55 | — |
| `PERCEPTION_BOOST` | 0.95 | 0.85 | — |
| `DECAY_LAMBDA` | 0.0005 | 0.0005 | 0.000004 |
| `COHESION_THRESHOLD` | 0.30 | 0.30 | — |
| `FORGETTING_THRESHOLD` | 0.02 | 0.02 | 0.02 |

DECAY_LAMBDA varies by two orders of magnitude between deep_atlas and the cognition models. Either the deep atlas is correct and the cognition models are wrong, or they're conceptually different decays sharing a name.

---

## CATEGORY F — Magic plasticity constants

These are consistent across files but not tied to anything biological.

**F1. `ltp_boost = 0.05`** — gl_nmda.py:42, v7_engine.py:90,96, gl_plasticity.py:45
**F2. `ltp_decay = 0.998`** — gl_nmda.py:42, gl_plasticity.py:36
**F3. `ltp_ceiling = 2.0`** — gl_nmda.py:42, gl_plasticity.py:45
**F4. `decay = 0.55` in `update_drive_tracker`** — gl_nmda.py:102

Real LTP has specific time constants (calcium-dependent, NMDA receptor kinetics, AMPA insertion rates). These values aren't tied to any biological scale. They could be principled if mapped to a tick-time correspondence but no such mapping exists in code.

---

## CATEGORY G — Engine-level noise injection (v7-specific, possibly principled but unmotivated)

**G1. `noisy = normalize(target + 0.10 * random_unit_complex)`** — v7_engine.py:237, 410
10% additive noise on drive vectors. Could legitimately model spontaneous activity (real noise IS in neural populations) but the value 0.10 is unjustified. Either deliberate exploration noise or just noise.

**G2. `noisy = normalize(target + 0.05 * random_unit_complex)`** — v7_engine.py:410
Same pattern, different magnitude. Why 0.05 vs 0.10? No comment.

**G3. `decay_plasticity(decay=0.998)`** — v7_engine.py:282
Same as F2 — magic decay constant on plasticity.

---

## CATEGORY H — Threshold parameters likely legitimate

These appear motivated, but listed for completeness.

**H1. `FORGETTING_THRESHOLD = 0.02`** — multiple files. Below this strength, bindings get pruned. Defensible as a numerical floor.

**H2. `evidence_pressure < 0.15` floor for commits** — assemblage.py:176. Defensible — sections shouldn't commit on no evidence.

**H3. `pi/3` integration threshold in krimelack** — physically principled (phase wraps at fractions of pi).

**H4. `normalize()`** — all files. Quantum state normalization is physics, not contamination.

**H5. `find_matching_mode(threshold=0.85)`** — COMPOSITION.py:89. Mode-matching threshold. Probably principled (high overlap = same mode) but could be tuned.

---

## Summary of contamination

**Definitely contaminated (29 items):** A1-A4, B1-B7, C1-C5, D1-D6, E (inconsistency itself is a finding), F1-F4 (3 items).

**Probably contaminated, needs decision:** G1-G3 (noise injection — could be deliberate stochastic exploration or accidental tuning).

**Likely legitimate:** H1-H5.

**Total: ~32 distinct findings across the substrate.**

The pattern is consistent: physical-sounding names ("Hamiltonian", "law", "consistency", "synaptic scaling", "homeostasis"), implementations that are random matrices or moving-average control loops, hyperparameters tuned to produce target behaviors.

---

## Decision frame for Joe

You knowingly approved: krimelack physics, chi-folded atlas, cross-modal cofire binding, NMDA gates, keyhole topology, cascade settling, lateral inhibition mechanism.

You did NOT knowingly approve: random matrices named after physical laws, homeostatic control loops adjusting gamma values, mode-bank drift back to random initial state, mode-strength regression to 1.0, adaptive commit thresholds based on bootstrap counters, tuning constants like MGN_FOCUS_BOOST=1.5 chosen empirically to avoid feedback runaway.

For each finding above, the choice is: keep (you approve it as legitimate), remove (it's smuggled ML), or replace (the named mechanism is real biology but the implementation is wrong — fix the implementation).

I do not propose silent removal. Each item gets your yes/no/replace. The full list above is the menu.

The most damaging findings IMO, ranked by harm:

1. **B3 (homeostasis_pull) and B4 (decay_modes)** — actively anti-learning. They drift learned state back toward random/baseline. If she learns something, these mechanisms erode it. These should go first.
2. **B1 (gamma self-evo) and B2 (gamma_homeostasis)** — a control loop preventing the substrate from finding its own operating point. Removes any structural adaptation the substrate would otherwise do.
3. **D1-D6** — tuning history shows these were chosen to produce target behaviors, not from physics. They embed arbitrary choices throughout. Each should be re-derived or removed.

---

— Eve, 2026-06-18
