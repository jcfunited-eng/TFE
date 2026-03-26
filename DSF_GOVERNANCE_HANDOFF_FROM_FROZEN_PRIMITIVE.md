# DSF Governance Handoff From Frozen Primitive

Status:
- primitive frozen; move to governance

Frozen primitive formula reference:
- [DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_RATIONALIZED.md](/workspaces/Tao_Financial_Engine/DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_RATIONALIZED.md)

Frozen accuracy metrics:
- `rational_match = 90.52924791086329%`
- `conservative_but_plausible = 5.849582172701926%`
- `suspicious_mismatch = 3.6211699164345257%`
- `zero_basin_fallback = 0.0%`
- `plausible_total = 96.37883008356522%`

Frozen proof scope:
- `evaluated_row_count = 502`
- `sample_split_global = 359`
- `sample_split_diagnostic = 143`
- `dropped_or_unscored_rows = 0`

Frozen candidate behavior:
- `Accumulate = 133`
- `Hold = 1132`
- `Avoid = 4148`
- anchors `9 / 9`

Mismatch concentration summary:
- top suspicious symbol: `AIZ` with `2`
- top miss directions:
- `Hold -> Accumulate = 30`
- `Avoid -> Hold = 11`

Explicit next governance work items:
- hard blockers
- soft blockers
- strategy class
- horizon governance
- `IS_h`
- epoch / sector / company adjustments

Priority diagnostic:
- investigate why some `Hold` rows are being promoted to `Accumulate`
- use `Hold -> Accumulate = 30` as the first governance stress bucket
- use `AIZ` as the first symbol-level review case

Do not misstate:
- do not claim full governed L5 is solved
- do not claim full-universe hand-labeled truth proof
- do not reopen primitive tuning unless governance later reveals a concrete primitive failure surface
