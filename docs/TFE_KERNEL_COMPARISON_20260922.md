# Corrected kernel source comparison — 2026-09-22

## Correction to my earlier conclusion

I did not establish a faithful replacement L0–L4. `tools/tfe_exact_geometry.py` preserves sampled geometric evidence but does not implement the specified DSF operators. Its tests establish those limited properties only. The earlier recommendation to proceed from that representation as a replacement was premature.

My initial extraction of the large UF Word specification read ordinary Word text but omitted embedded equation objects. The document contains 209 math blocks. Therefore my earlier statement that I had read that specification overstated the evidence inspected. Math-aware extracts and original document XML are now retained in `artifacts/tfe_verification/original_equations_20260922/`, with source hashes in `sources.json`. These are transcriptions for inspection, not new mathematical authority or proof that every diagram was reviewed.

The earlier bounded code inventory and exact normalization counterexample remain evidence about those specific implementations. They do not prove that all repository mathematics was exhausted or that a faithful kernel cannot be recovered.

## Requested architecture and evidence boundary

Requested architecture: raw temporal observations enter frozen, domain-agnostic L0–L4; L5 assesses complete evolving field relationships for formation, continuation, and collapse, including relevant peer structures. No invented weighted scores, smoothing, or reduced substitutes.

Current code reality: several different source specifications and implementations exist. Some source-defined operations conflict with the latest literal no-means requirement. Full-chain fidelity has not been established.

Conflict with requested architecture: yes. Neither the generic geometry tool nor a kernel name establishes the requested DSF implementation.

Mechanisms not to extend: `tools/tfe_exact_geometry.py` as a DSF replacement; per-frame normalized VTVR outputs as complete amplitude geometry; the unproved weighted states in `PRIMITIVE_DIRECT_FIELD_STATE_CALC_DRAFT.md`; the sentinel's `D_k != 1` compression interpretation.

Single next item: complete equation-to-code provenance for the existing field and exhaustion mechanism before changing strategy behavior.

Full field or reduced approximation: this is source and fidelity analysis, not a new full-field evaluator. The rejected substitutes lose either physical operator definitions, shared temporal amplitude, or joint relationships through weighted state reduction.

## Original layer documents actually contain operator definitions

The root `UF-L0.docx` through `UF-L4.docx` describe v1.4:

| Layer | Source mathematics | Relevant implementation evidence |
|---|---|---|
| L0 | Raw vector, first difference, local variance, curvature, relevance and Negative Space | `uf_core/layer0.py` includes local variance; variance is specified here, not automatically an accidental heuristic. |
| L1 | Segmentation, TVR, mosaics, compression; section C.6 explicitly averages difference, variance and curvature | `uf_core/layer1.py:180` onward also computes these means. Their presence conflicts with a literal no-means criterion but is not by itself proof of departure from this document. |
| L2 | Intensity, displacement from a local TVR baseline, stability and uncertainty | `uf_core/layer2.py:47` onward uses a global mean baseline. Local versus global scope requires fidelity resolution; appending observations can revise earlier geometry. |
| L3 | Weighted scalar resonance, hysteresis and contextual validity; URF delivered to L4 | The document itself prescribes weighted resonance. It cannot establish compliance with a blanket prohibition on that reduction. |
| L4 | Direction from resonance change; second-difference momentum; reversal; adjusted uncertainty; pressure; recurrent breathing; seven-field output | `uf_core/layer4.py:80` onward contains these actual recurrences. Generic raw edges are not a replacement for them. Exact parameters, input semantics and upstream fidelity still need verification. |

The large v1.3 specification is not interchangeable with those layer documents: it describes a different five-component L4 surface (DPS, MGE, PR, PBD, corrected stability), adaptive segmentation and several incompletely specified operators. Combining versions silently would invent a specification.

`UF-Section11-MathFramework.docx` also explicitly contains aggregate global stability terms. Source provenance must distinguish prescribed mathematics, implementation substitutions, and the user's current architectural requirements. A document title or author metadata does not settle that authority conflict.

## Existing exhaustion work: a concrete mismatch

`ADVANCED_LOCALIZED_THERMODYNAMICS___ASYMMETRIC_EXHAUSTION.pdf`, section 2.1, defines quiescence through change in displacement approaching zero within tolerance. Compression duration is consecutive bars in that state. Section 2.3 defines `tau_out = floor(tau_in / 3)` starting at validated ignition.

In `web/scripts/execution/sentinel_monitor.mjs:1542` onward, compression instead counts a run of `D_k !== 1`. These are different conditions. Constant negative displacement has zero displacement change; a switch from negative to neutral has nonzero change, yet both observations qualify under the code's inequality. The document's displacement meaning also must be reconciled with the ternary directional meaning in the v1.4 L4 document.

The sentinel's exhaustion timer is explicitly disabled at line 1572 and the inspected branch only logs its values. This is a source observation, not verification of what production is currently serving. `tools/backtest_simulator.py` repeats the inequality shortcut, so agreement between simulator and sentinel would not independently validate the paper's quiescence law.

`tools/measure_exhaustion_telemetry.py` contains a separate difference-based calculation worth tracing. Its candidate tolerances are not automatically authoritative. The paper alone does not supply a complete causal apex estimator or numerical quiescence tolerance. Re-enabling the timer without resolving these points would not be a faithful fix.

## Prior interpretation work is evidence, not authority

`DSF_PRIMITIVE_LAW_SKETCH.md` explicitly calls itself a symbolic candidate, not a finished derivation, and says runtime coefficients are not yet derived DSF constants. `PRIMITIVE_DIRECT_FIELD_STATE_CALC_DRAFT.md` reduces fields to three weighted states and acknowledges unproved coefficients. It conflicts with the requested non-flattened interpretation.

`DSF_PRIMITIVE_INTERPRETATION_RECOVERY_STATUS.md` records a historical evaluation worsening from 39.8470% to 37.0482% overall classification accuracy. Those are report claims, not results reproduced in this review, and are not strategy win rate or SPY lift. This existing work should have been examined before inventing another representation.

## Exact counterexample retained from earlier inspection

The unchanged `tools/isolated_vtvr_side_kernel.py` was executed with exact rational inputs:

- Constant: `(1,2), (1,2), (1,2)`.
- Rise and fall: `(1,2), (2,4), (1,2)`.

Per-frame magnitude normalization makes every frame `(1/3,2/3)` in both cases. All seven delivered L4 values match; both outputs are labelled quiescent. Raw hashes differ. This establishes loss of shared temporal amplitude in that candidate's delivered field, not invalidity of every kernel or source document.

Earlier bounded search evidence remains in `artifacts/tfe_verification/kernel_comparison_20260922/`: the broad 843-file inventory includes unrelated libraries and wrappers, not 843 DSF implementations; historical inspection covered 14 path/content pairs at 11 commits, not all Git history.

## Outcome

No faithful replacement kernel, new strategy improvement, or target WR/lift achievement is established. No kernel, Guala process, or trading behavior was changed by this source correction. Recommendation: recover and verify the existing displacement-to-exhaustion chain against its actual source equations before modifying selection or exit behavior.
