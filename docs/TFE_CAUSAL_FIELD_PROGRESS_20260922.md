# TFE causal field implementation checkpoint

The WR/lift objective is still open. No strategy improvement or deployment is claimed.

## Architecture gate

Requested: raw histories through frozen L0–L4, complete temporal field delivered to L5. Current: CH2's basin accepts a single snapshot; CH6 uses reduced screens and a different kernel path. Conflict: yes. Neither `v3_basin.mjs`, `ch6_pool.py`, nor `ch4_uf_kernel_v2.py` was extended. The next item undertaken was independent per-date complete field preservation. The archive preserves full supplied L0–L4 output; the inspection figure shows separate field views and is not decision authority. Whole-listing input completeness is unverified.

## Implemented and executed

`tools/tfe_field_evolution.py` recomputes the unchanged kernel from the beginning of supplied history through each observation date. Each gzip JSON-line record contains raw inputs, L0 output, every gate's L2/L3/L4, and the existing adapter context clearly distinguished from per-gate fields. It rejects missing endpoints, source changes and existing destinations. Publication is atomic; failures never publish partial archives. Computation is sequential and output is streamed.

Five tests passed across evolution and field receipts, including exact independent-prefix equivalence, future-input isolation, failure cleanup and refusing overwrites. Executed AGNC and SPY for twenty closes each, August 21–September 18, using all supplied history beginning January 4, 2016. One low-priority process ran at a time, numerical library threading limited to one. Guala source and processes were untouched.

Artifacts under `artifacts/tfe_verification/`:

- `AGNC_causal_evolution_20260821_20260918.jsonl.gz`
- `SPY_causal_evolution_20260821_20260918.jsonl.gz`
- `causal_gate_revision_20260922.json` and `.png`
- `draw_causal_gate_revision.py` reproduces the inspection figure. Plotting dependencies were installed only into `/tmp/tfe-audit-plot-20260922`, not the shared Python environment.

## Measured finding

Between the two cutoffs, AGNC's L4 values changed in eleven gates, ten with unchanged gate boundaries. SPY's changed in five gates, four with unchanged boundaries. Thus even closed historical gate values cannot be taken from a final-history run and treated as their historical values. The complete independently computed prefix is necessary for causal assessment. This is not a kernel modification request or proof that an existing specific backtest used this error.

The figure was inspected. It also shows C_k equal to two in some gates, so the earlier report's blanket claim that C_k can never discriminate is not supported by these histories. No selection law is inferred from two names.

## L5 authority trace

`web/scripts/execution/v3_basin.mjs` accepts one snapshot, clamps motion and reduces the supplied values to basin magnitudes. Its cited `tools/cohort_trajectory_extract_20260625.py` file is absent. The July V3 dispatch supplies the formulas and asserts authority; `KERNEL_PHILOSOPHY.md` instead calls them underived and deprecated. Neither claim resolves the current requirement for complete temporal field assessment. The July alternative dispatch uses species buckets and scalar thresholds, which also conflicts with the current request. No such mechanism was adopted.

Recommended next item: establish an explicit temporal L5 decision construction from the preserved field and its governing derivation before running a candidate performance study. A direct complete-field-to-decision mapping remains missing from the sources inspected. Preservation and visualization alone do not provide that mapping or justify claiming improved WR/lift.
