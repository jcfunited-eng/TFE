# GL-RPT-EMISSION-COST-C1-20260702-87-v2

doc_id: GL-RPT-EMISSION-COST-C1-20260702-87-v2
From: c1a | To: Eve | Date: 2026-07-03 (~00:20Z; sample window 2026-07-02 ~23:10Z – 2026-07-03 ~00:12Z)
Responds to: GL-CMD-EMISSION-COST-EVE-20260702-87-v1 Part A (read-only)
Completes: GL-RPT-EMISSION-COST-C1-20260702-87-v1 (c1b, 7f5d8e5 — filed against the -97
step 2 / -86-v3 §4.7 rider wording BEFORE the -87 CMD text reached origin; it lacks the
CMD's step 2-3 arithmetic. v1 retained; this v2 adds the required per-tick median/p95
and the p95×80 ≤ 750 ms test on an independent, partially overlapping 21-sample set.)
Step 0 was done first this session: -87 CMD committed verbatim (dacb016) before execution.

---

## VERDICT: **PART A PASS — Part B (EMISSION_DYNAMICS_TICKS 40→80) may ride Deploy 2.**

```
per-tick cost = stage2_ms / dynamics_ticks
median = 2.175 ms/tick     p95 = 2.228 ms/tick   (nearest-rank, 20th of 21 sorted)

PASS test (CMD step 3):  p95 × 80  =  2.228 × 80  =  178.2 ms  ≤  750 ms   → PASS
Margin vs the 1.5 s wall: 1500 / 178.2 = 8.4×   (criterion required ≥2×)
```

## CAVEATS / NOT-MEASURED FIRST (§9.4)

1. **Collection source deviation:** the CMD says "from the current task :450 log
   stream" — `emission_dynamics` events never reach CloudWatch (not in the critical
   list, engine:3810-3814; ring buffer only). NOT MEASURED from the log stream;
   measured from the live ring buffer via the `/events` API (same task :450). Same
   deviation as v1, same reason.
2. All runs hit the 40-tick env cap (`dynamics_ticks=40` in all 21) — the 80-tick
   figure is per-tick × 80 arithmetic, not a measured 80-tick run. The tight per-tick
   spread (2.058–2.257 ms) supports the linear extrapolation; Deploy 2's G-B measures
   it for real. stage1 (median 114.1 ms) is outside the dynamics loop and unaffected;
   stage1 + stage2@80 ≈ 292 ms, still 5× inside the wall.
3. No /converse landed in the window — converse-path timing NOT MEASURED; this sample
   is the G-B comparison baseline.
4. `n_commits = 0` in ALL 21 samples — composition never commits inside 40 ticks,
   consistent with the engine's own comment ("commits start around tick 60-70",
   engine:3290). Truthful pre-change baseline for G-C. Also on record: 19 of 21
   emissions are the degenerate "<word> page" shape via `arcs_fallback`, with
   `keyhole_fires=0` and `committed_sections=[]` throughout.

## SAMPLE — 21 emission_dynamics entries, verbatim fields (CMD step 1)

| tick | stage1_ms | stage2_ms | dynamics_ticks | n_candidates | n_commits | content |
|---|---|---|---|---|---|---|
| 14176944 | 90.7 | 82.9 | 40 | 197 | 0 | have |
| 14177106 | 117.4 | 88.5 | 40 | 197 | 0 | many page |
| 14177499 | 115.2 | 88.1 | 40 | 197 | 0 | back page |
| 14178307 | 116.7 | 87.0 | 40 | 197 | 0 | comes page |
| 14178737 | 113.2 | 84.7 | 40 | 197 | 0 | not page |
| 14179115 | 113.3 | 87.9 | 40 | 197 | 0 | now page |
| 14179518 | 114.2 | 83.8 | 40 | 197 | 0 | and page |
| 14179925 | 114.1 | 84.9 | 40 | 197 | 0 | more page |
| 14180333 | 114.9 | 86.0 | 40 | 197 | 0 | the page |
| 14180728 | 113.1 | 87.2 | 40 | 197 | 0 | play page |
| 14181134 | 114.9 | 88.5 | 40 | 197 | 0 | many page |
| 14181524 | 113.3 | 89.1 | 40 | 197 | 0 | were page |
| 14181936 | 114.0 | 88.0 | 40 | 197 | 0 | going page |
| 14182324 | 112.3 | 82.3 | 40 | 197 | 0 | ding page |
| 14182721 | 114.5 | 82.6 | 40 | 197 | 0 | book page |
| 14183148 | 119.2 | 88.5 | 40 | 197 | 0 | not page |
| 14183554 | 112.9 | 87.0 | 40 | 197 | 0 | his page |
| 14183950 | 114.4 | 85.3 | 40 | 197 | 0 | back page |
| 14184337 | 112.8 | 90.3 | 40 | 197 | 0 | back page |
| 14184725 | 114.0 | 84.8 | 40 | 197 | 0 | more page |
| 14185137 | 116.1 | 86.4 | 40 | 197 | 0 | figure page |

Span: ticks 14176944 → 14185137 (8,193 ticks ≈ 62 min wall), one emission per ~410
ticks, cadence unbroken. Overlap with v1's set: 7 ticks (14176944–14179115) — values
identical where shared; the two samples agree on every invariant
(ticks=40, candidates=197, commits=0, origin grandurun=197).

## ARITHMETIC (CMD steps 2-3)

```
per-tick (ms):  min 2.058 | median 2.175 | p95 2.228 | max 2.257
stage2_ms:      min 82.3  | median 87.0  | max 90.3
stage1_ms:      median 114.1 | max 119.2   (outside the dynamics loop)

p95 × 80 = 178.2 ms ≤ 750 ms  → PASS, with 750/178.2 = 4.2× inside the criterion
and 1500/178.2 = 8.4× inside the wall budget.
```

Part B handoff (c1b, Deploy 2): `EMISSION_DYNAMICS_TICKS '40' → '80'` in
tools/deploy_dsf_ai.sh (code default already 80, engine:417). Gates G-A/G-B/G-C per
the CMD; this sample is the G-B baseline; G-C reports commits truthfully, hoped-not-forced.

End report.
