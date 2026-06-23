# GL-SPC-MULTI-KRIMELACK-NEURON-EVE-20260621-124

**Doc ID:** GL-SPC-MULTI-KRIMELACK-NEURON-EVE-20260621-124
**Author:** Eve
**Date:** 2026-06-21
**Status:** DRAFT — pending Joe canonical sign-off
**Subject:** Guala
**Replaces (in part):** GL-CMD-TEACHING-LOOP-EVE-20260621-121 V2.2 and V2.3
**Preserves:** GL-CMD-TEACHING-LOOP-EVE-20260621-121 V2.1 (signal-layer position modulation — independent bug fix)
**References:** gualaloom_development_manifesto.md; GL-RPT-LOOM-STAGE3-FOLDING-C1-20260621-01; GL-RPT-LOOM-NEURON-STAGE1-C1-20260620-01; GL-RPT-LOOM-CLUSTER-STAGE2-C1-20260620-01; dsf_ai_service/loom_model/substrate_dna.py

---

## 1. Why this spec exists

The Stage 3 V4 STOP measured `n_eff = 3.000` vs `threshold = 2.943` for natural folding under language input. Multi-modal delivery produced `n_eff = 3-5` — never crossing. The substrate is refusing to fold, and it is correct to refuse.

The reason: every LoomNeuron currently carries a single `LanguageKrimelack`, tuned for character signals (`kappa=80`, `threshold=π/3`). Sensory waveforms — thermal, visual, acoustic — are force-fed through that same character-tuned krimelack at `neuron.py:454`. Touch read as letters cannot produce the DSF shape that the L6-TCL physics is looking for. The threshold guards meaning: language alone, without sense-grounding, is not enough complexity to lock structural constraint.

This spec aligns the substrate with the manifesto's foundational claim: meaning is "the substrate state of a thing that has been alive long enough for shape to accumulate," and "the word 'warm' means something to Guala because her substrate has been shaped by repeated co-firings of touch-temperature signatures with the language signature for 'warm' under conditions of repeated reinforcement against decay" (gualaloom_development_manifesto.md §"The three primitive facts").

For the cross-modal binding the manifesto describes to occur, each neuron must be able to transduce signals from every modality on each modality's own physics. The chi-atlas then binds them where they co-fire. Folding Division then specializes daughter neurons via the existing `derive_daughter_parameters` mechanism.

## 2. Substrate-true principle

- **No pre-assigned hemisphere modality.** Experience.py already commits: "hemispheres develop preferences through experience, never by design." This spec preserves that. There is no "this is the touch hemisphere."
- **Encoding IS the binding.** No semantic layer, no symbol-table. ChiAtlas remains the only meaning mechanism.
- **Specialization is emergent.** Folding Division spawns daughter neurons with the krimelack class of the overflow signal that triggered the fold (already implemented in Stage 3, T4 PASS).
- **No new constants, no new categories.** All new behavior comes from wiring existing primitives.

## 3. Architecture

Each LoomNeuron carries a **krimelack bank** — a dict mapping modality names to instantiated krimelacks. Signal-type routing in `neuron.step()` dispatches the input to the correct krimelack:

```
input type             → krimelack
─────────────────────────────────────────────────
str                    → LanguageKrimelack
{"touch": params}      → TactileKrimelack
{"smell": params}      → OlfactoryKrimelack
{"taste": params}      → GustatoryKrimelack
{"sight": frame}       → VisualKrimelack
{"sound": waveform}    → CochlearBankKrimelack
np.ndarray (legacy)    → LanguageKrimelack (back-compat for current callers)
```

Each krimelack independently produces events and maintains its own winding state. After step():
1. Events from the active krimelack feed `compute_dsf` on that krimelack's own physics.
2. DSF + chi → MapInject → ψ-lattice settle (unchanged).
3. On commit, `chi_atlas.record(section_name, motif, chi_value, tick)` records under the active modality's `section_name`. Cross-modal binding emerges when two modalities commit within `CHI_BAND` of each other (existing semantics — already supports this).
4. On fold, `derive_daughter_parameters` already returns the correct `krimelack_class` based on `origin_transducer`. Daughters spawn modality-specialized.

The ExperiencePipeline.deliver_word path delivers each word as a sequence: language signal on one sub-tick, modality-tagged sensory signals on subsequent sub-ticks (touch/smell/taste payloads packaged as `{modality: params}` dicts instead of flattened arrays). Words with no sensory_dict deliver language-only.

## 4. What already exists in the substrate

This list is the basis for claiming Phase 2 is mostly wiring, not new architecture:

| Piece | Status | Location |
|---|---|---|
| `KRIMELACK_PRIMITIVES` catalog (6 entries) | EXISTS | `loom_model/substrate_dna.py:209` |
| `TactileKrimelack`, `OlfactoryKrimelack`, `GustatoryKrimelack`, `VisualKrimelack`, `CochlearBankKrimelack` adapters with uniform `.transduce / .events / .winding` | EXISTS | `loom_model/substrate_dna.py` |
| `derive_daughter_parameters` picks correct `krimelack_class` from `origin_transducer` | EXISTS, tested | `loom_model/substrate_dna.py:236` |
| Folding Division spawns daughters with correct modality (T4 PASS) | EXISTS | `loom_model/neuron.py` |
| `ChiAtlas.record` accepts arbitrary `section_name` for cross-modal binding | EXISTS | `v4/gualaloom_v4_chi_atlas_l6.py:27` |
| `SensoryBank` instantiated per neuron with 5 modal krimelacks | EXISTS but UNUSED | `neuron.py:382`; only referenced in tests, never called in `step()` |
| Sensory waveform generators (touch/smell/taste/sight/sound) | EXISTS | `substrate/sensory_generators.py`; `visual_krimelack.py`; auditory cortex module |
| Per-modality `MODAL_TUNING` (kappa, threshold per modality) | EXISTS | `sensory_krimelacks.py` |

## 5. What needs to change

Concrete code surfaces. Implementation details belong in a follow-up GL-CMD; this spec specifies what changes, not how.

1. **LoomNeuron carries a krimelack bank, not a single krimelack.** The current `self.krimelack = LanguageKrimelack()` is replaced with `self.krimelacks: Dict[str, Krimelack]` populated with all six primitives from `KRIMELACK_PRIMITIVES`. The dead-but-instantiated `SensoryBank` either folds into this or is retired (see canonical decision §6.1).

2. **`neuron.step()` routes by signal type.** The current `if isinstance(input_signal, str)` two-branch dispatch becomes a typed dispatch on signal shape. Default unknown shape → language (back-compat).

3. **DSF is computed from the active krimelack's events.** `_last_events`, `_last_dsf`, `_last_origin_transducer` all reflect whichever krimelack actually transduced this tick.

4. **ExperiencePipeline delivers typed signals.** `deliver_word` currently builds a `composite_waveform` by `np.concatenate` of all modality waveforms (experience.py:72) — that flattening destroys modality identity. Instead, the pipeline delivers a sequence of modality-tagged signals across sub-ticks. Language sub-tick delivers the word string; sensory sub-ticks deliver `{modality: params}` dicts.

5. **Cross-hemi projections carry origin_transducer** so a fold triggered by tactile input on H2 carries that modality through cross-hemi coupling, allowing daughters across the substrate to potentially inherit modal information (existing field, just needs to be threaded through the spike packet).

6. **Tests for natural folding under sensory input.** The Stage 3 V4 STOP measured zero natural folds. Phase 2 success criterion: natural folds occur on sensory-rich input, daughter origin_transducer matches the triggering modality. (Stage 3 T4 already passes this when origin is forced; Phase 2 must show it without forcing.)

## 6. Canonical decisions for Joe (not buried)

### 6.1 SensoryBank vs Stage 3 adapters

There are two co-existing multi-modal krimelack systems in the substrate:

- **SensoryBank** (older, `v4/gualaloom_v4_krimelack_dna.py:281`): holds 5 `ModalKrimelack` instances, fires via `fire_for_word(sensory_dict)` against curated `SENSORY_DNA` dicts. Instantiated per neuron but never called.
- **Stage 3 adapters** (newer, `loom_model/substrate_dna.py`): hold 5 modal krimelacks (`TactileKrimelack`, etc.), each wrapping waveform generators + `OscillatorKrimelack` with per-modality `MODAL_TUNING`. Used in Folding Division for daughter spawn.

**My read:** Stage 3 adapters are substrate-truer — they transduce actual generated waveforms via tuned physics. `SensoryBank.fire_for_word` against a curated `SENSORY_DNA` lookup table is closer to a hash than to substrate transduction. I'd retire `SensoryBank` from `LoomNeuron` and use the Stage 3 adapters as the single per-neuron multi-modal bank. But this is canonical territory — your call.

### 6.2 Lazy vs eager krimelack instantiation

All six krimelacks per neuron × 400 neurons = 2,400 krimelack instances per substrate. Memory cost is small (krimelacks hold tuning constants + small event lists), but a call exists:

- **Eager** (build all 6 at neuron birth): simple, deterministic, all paths immediately available. Some krimelacks may never fire on a given neuron — memory wasted but not harmful.
- **Lazy** (instantiate on first signal of that modality): memory-efficient. But signals can arrive in any order, and lazy init means the first signal pays the instantiation cost — could affect timing tests.

**My read:** eager. The substrate is small enough that the memory cost is rounding error, and eager makes the substrate fully symmetric — every neuron has the same shape at boot, and what differs is what fires. This honors "hemispheres develop preferences through experience, never by design" at the neuron level too.

### 6.3 What to do with -121's V2.1 (signal-layer position modulation)

The order-blind signal envelope bug is real: `cat`, `act`, `tac` currently produce identical signal sums. V2.1 of -121 fixes that with `position_modulated=False` default (production-safe). **This bug fix is independent of multi-krimelack Phase 2.** It is substrate-honest at the language layer — anagrams should not collide on raw signal.

Three options:
- (A) Ship V2.1 as a small standalone fix before Phase 2, verify in isolation.
- (B) Bundle V2.1 into Phase 2 deployment so all language-layer changes land together.
- (C) Drop V2.1 — argue the substrate's order-blindness at signal layer is fine because winding state across sub-ticks captures order. (I do not recommend this; the bug is real and I want it documented as not-currently-true.)

**My read:** (A). It's small, independently verifiable, and the cleaner the layers stay separated, the easier each is to validate.

### 6.4 Folding Division naturalness as success criterion

The Stage 3 report says "0 natural folds over 5000 ticks" was a PASS because the substrate refused to fold on language alone, which was correct. Phase 2 inverts this: **after multi-krimelack wiring, natural folds SHOULD occur on sensory-rich input within reasonable tick budgets**. If they don't, the substrate is still saying "not complex enough," and that's diagnostic of something missing — possibly the cross-hemi binding layer (item 8 on THE list) is also needed before folding becomes reachable.

I want this written into the spec as the explicit gate. Phase 2 is incomplete if natural folds don't occur on tactile/visual/auditory input. Your call: how many ticks of sensory-rich input is fair before declaring the gate failed? Stage 3 used 5000. I'd suggest the same.

### 6.5 Phase 2 scope boundary

This spec does NOT cover:
- Cross-hemi coupling refinements (THE list item 8 — separate spec).
- Migration of Guala from dict-substrate (LivingAtlas) to LoomBrain substrate (items 10-11).
- Atlas saturation / decay tuning for the multi-modal regime.
- Sensory corpus building (binding Guala's existing 2,500-word vocabulary to actual sensory experiences — months of substrate runtime).

These are downstream. Phase 2 establishes the substrate that those depend on.

## 7. What this preserves (manifesto commitments)

- Trits, krimelacks, chi atlas, L0-L4 UF kernel, L6-TCL, MathLoom, needs vector, coordinator, question bucket — all unchanged structurally.
- No new orchestration layer. No statistical inference. No ML.
- Hemispheres remain undifferentiated by design. Specialization emerges via Folding Division.
- Encoding IS the binding. No semantic store.
- Guala's identity `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f` — untouched. State persistence — untouched.

## 8. What this explicitly drops

- GL-CMD-121 V2.2 (topographic K_POS=16 commit register) — drops. Discrimination via topographic word fingerprints would have given Guala higher metric-score word identification without grounding any of those words in sense. That is the hash-with-context-tag failure mode the manifesto and the V4 STOP both refuse.
- GL-CMD-121 V2.3 (atlas binding extension + 4-layer context plumbing) — drops. The context-binding it added is a workaround for a substrate that can't transduce sensory richness; Phase 2 makes it transduce that richness directly, so the workaround is unnecessary.

## 9. Success criteria (gate before merge)

1. All 19 Stage 1+2 + 10 Stage 3 tests remain green.
2. New tests confirm `neuron.step()` correctly routes each of the 6 signal types to the corresponding krimelack.
3. Natural folds occur within 5000 ticks of sensory-rich input. Daughter `origin_transducer` matches the triggering modality.
4. Chi-atlas shows cross-modal bindings (entries where ≥2 distinct `section_name` values committed within `CHI_BAND`) after a corpus run that includes both language and sensory-grounded words.
5. Production callers (`app.py:1651` via legacy `LanguageKrimelack`) remain bitwise-unaffected — Phase 2 is additive to the loom_model substrate, doesn't touch v5/v6 engines or `LivingAtlas`.

## 10. Open question to surface to Joe

Per memory `Guala_Cross-hemi_coupling_layer—pending_item_7`, the cross-hemi coupling refinement (THE list item 8) was already queued. **Should Phase 2 (this spec) come before, after, or in parallel with item 8?**

My current best read: Phase 2 first. Without modality-typed signals the cross-hemi traffic doesn't carry meaningfully different content per hemisphere — there's nothing distinct yet to couple. Once Phase 2 is in, cross-hemi coupling has something real to bind across.

But you may see a dimension I'm missing. Call it.

---

**END OF SPEC — DRAFT for Joe review and edit. No c1 command produced. No deployment.**

— Eve, 2026-06-21
