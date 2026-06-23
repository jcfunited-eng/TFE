# GL-CMD-HETEROGENEOUS-KRIMELACKS-EVE-20260622-139

**doc_id:** GL-CMD-HETEROGENEOUS-KRIMELACKS-EVE-20260622-139
**To:** c1
**From:** Eve
**Date:** 2026-06-22
**Re:** Item 7 — heterogeneous krimelacks per hemisphere. Unblocks Folding-during-experience.
**Status:** Architectural. Independent of GL-CMD-138 but synergistic.

---

## Why

Verified in code: `self.krimelack = LanguageKrimelack()` is set identically on every neuron in every hemisphere (`neuron.py` L396). L6-TCL, DSF, and `fold_check` all read `self.krimelack`. Result: every hemisphere's fold dynamics are driven by language krimelack output, regardless of which hemisphere it is. Homogeneous DSF profiles across the brain. The n_eff wall at GL-CMD-114/117 is the substrate accurately reporting that uniform language input doesn't produce the directional reversal + non-uniform magnitude that Folding's L6-TCL needs to cross threshold.

Past Eve's handoff (GL-HANDOFF-EVE-NEXT-CLAUDE-20260622-128) named the path: **heterogeneous krimelacks per hemisphere.** Each hemisphere gets a primary modality matching its sensory role. The sensory krimelack adapters (Tactile, Olfactory, Gustatory, Visual, Cochlear) already exist (verified V1 of GL-CMD-125) and already produce richer DSF profiles because real sensory waveforms have consistent direction reversal and non-uniform magnitude — exactly what L6-TCL needs.

This dispatch makes that assignment.

## Open question — visible, not buried

We have 8 hemispheres and 6 modalities (visual, auditory, tactile, olfactory, gustatory, language). Past Eve's handoff says "5 sensory hemispheres get sensory krimelack as primary at seed" — implying 5+1=6 specialized and 2 unspecified.

**What are H6 and H7?** Past Eve didn't say. Joe's call. Default if Joe hasn't picked at dispatch time: H6 = auditory secondary, H7 = language secondary, mirroring left/right cortical duplication. Override anytime before V2 ships.

## V1 — Audit before patching

**V1.a:** Confirm sensory krimelack adapters all expose the interface LoomNeuron needs as primary:
- `.feed_signal(signal_array)` — verified exists per GL-CMD-125 V1.b
- `.phase`, `.winding` (with setters for restore) — verified per GL-CMD-129
- `.events` list + `.n_events` counter — depends on GL-CMD-138 (if 138 hasn't landed, use `len(events)` for now and update once it does)
- `.kappa`, `.threshold` — needed for fold_check + DSF

Report which adapters are missing any of these. The DSF and L6-TCL paths need to read from the primary krimelack the same way they currently read from the LanguageKrimelack. If sensory adapters have different attribute names, document the mapping.

**V1.b:** Identify every `self.krimelack` read site in LoomNeuron and its helpers. List them. The change to a primary-modality alias must work for ALL of them, not just the cognition path.

**V1.c:** Run the 38-test regression suite as-is. Note the baseline. Some tests assume language-as-primary; surface which.

## V2 — Implementation

### V2.1 — Hemisphere primary modality

In `dsf_ai_service/loom_model/topology.py`, add:

```python
HEMISPHERE_PRIMARY_MODALITY = {
    "H0": "visual",
    "H1": "auditory",
    "H2": "tactile",
    "H3": "olfactory",
    "H4": "gustatory",
    "H5": "language",
    "H6": "auditory",   # secondary auditory — REPLACE per Joe's call
    "H7": "language",   # secondary language — REPLACE per Joe's call
}
```

### V2.2 — Plumb primary modality through hemisphere → cluster → neuron

`LoomHemisphere.__init__` accepts `primary_modality` parameter, defaults to `"language"` for backward compat. Passes to `LoomCluster.__init__`, which passes to `LoomNeuron.__init__`.

`LoomBrain.__init__` reads `HEMISPHERE_PRIMARY_MODALITY[hemi_id]` when constructing each hemisphere.

### V2.3 — LoomNeuron primary krimelack assignment

In `LoomNeuron.__init__`, accept `primary_modality` parameter. After constructing `krimelack_bank`, alias `self.krimelack` to `self.krimelack_bank[primary_modality]` instead of a fresh `LanguageKrimelack`.

Critical: `self.krimelack` is now the SAME OBJECT as one entry in `krimelack_bank`. Mutations to one are mutations to the other. This is correct — `fold_check` + DSF must see the same krimelack state as the cognition write path.

### V2.4 — Snapshot / restore semantics

In `brain.recall`, the snapshot/restore loop iterates `krimelack_bank`. Since `self.krimelack` is an alias to one of the bank entries, the snapshot/restore correctly captures and restores the primary krimelack too. No additional code needed; just verify behavior.

### V2.5 — Backward compatibility on tests

Tests that construct a bare LoomNeuron without specifying `primary_modality` should still work. Default behavior: language. The 38 regression tests should all pass without modification (since they all use the LanguageKrimelack path implicitly).

## V3 — Validation

**V3.a:** 38-test regression: all PASS.

**V3.b:** Sanity check that hemisphere primary modalities are set correctly. Probe: for each hemisphere H0..H7, confirm `type(brain.hemispheres[i].cluster.neurons[0].krimelack).__name__` matches the expected primary modality's adapter class name.

**V3.c:** Re-run the Folding-during-experience tests at GL-CMD-114/115/116/117 that hit the n_eff wall. With heterogeneous krimelacks, n_eff should now cross the threshold for sensory hemispheres under sensory input. Report n_eff time series for each hemisphere during a 100-tick experience run. Expected: visual/auditory/tactile/olfactory/gustatory hemispheres show n_eff descent crossing `fold_threshold (n_start × 1/e)` within 100 ticks on natural sensory input. Language and the H6/H7 secondaries may or may not — report what they do.

**V3.d:** Run the cognition path tests (T4–T9 from GL-CMD-125 onward). The cognition write iterates all 6 krimelacks per neuron — heterogeneity should NOT affect cognition. T5 should match the GL-CMD-136/137 baseline at 50–100 concepts. If it doesn't, something in the snapshot/restore broke. Report.

**V3.e:** Memory check. Heterogeneous krimelacks shouldn't change memory significantly (each neuron has the same `krimelack_bank` of 6, just aliasing `self.krimelack` differently). Confirm RSS at 64 neurons × 100 concepts × 3 reps matches GL-CMD-138's post-fix baseline.

## V4 — STOPs

- **STOP if any sensory adapter is missing the interface elements V1.a requires.** Specifying them is part of GL-CMD-139; implementing missing pieces is a fork point.
- **STOP if V3.a regression has any failures.** The current 38 tests are the substrate's truth contract. Don't break them.
- **STOP if V3.d cognition T5 collapses dramatically (>20pp drop).** Means heterogeneity broke the cognition write path somehow. Report per-hemisphere cognition T5 contribution.
- **STOP if V3.c shows NO hemispheres reaching n_eff fold_threshold.** That would mean even with sensory krimelacks, Folding still doesn't fire — which contradicts past Eve's diagnosis. Surface immediately before continuing.

## V5 — Report

V5 report must include:

1. V1 inventory of sensory adapter interface compliance
2. V1.c regression baseline notes
3. V2 line counts
4. V3.a regression status
5. V3.b hemisphere-primary verification (8 expected, 8 confirmed?)
6. V3.c n_eff time series per hemisphere on natural sensory input. This is the smoking gun for item 7 unblocking.
7. V3.d cognition T5 with heterogeneous krimelacks
8. V3.e memory check
9. Honest assessment: is item 7 unblocked? Are any sensory hemispheres actually Folding-during-experience now?

— Eve, 2026-06-22
