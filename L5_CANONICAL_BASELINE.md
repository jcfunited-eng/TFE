> # ⚠ CORRECTED 2026-09-21 — THE HEADLINE NUMBER IS LOOKAHEAD
>
> The 64.66 % below, and the 81.4 % ladder quoted from this document in
> `web/scripts/execution/financial_rules.mjs`, are **not achievable**.
>
> **Two independent contaminations:**
>
> 1. **Forward-return filter.** The ladder's "Rising 5d (not falling)" rung is
>    `Return_5d > 0`, and `Return_5d` in `quarantine_12k_l5_trades.csv` is the
>    **forward** five-day return — verified **400/400** against the raw bars.
>    It selects rows whose price rose *after* entry, then scores what happened
>    after that. Worth **+17.6 pp**. Every rung above it inherits it.
>
> 2. **Warm-up artefact.** The 64.66 % Layer-1+2+3 figure fires on the kernel's
>    initialisation state: median signal position is **bar 1** of a symbol's
>    history, 95 % of signals sit at position ≤ 18, and `prev_B_k = -0.050000`
>    exactly (the init constant) at those rows. Half the signals land in 2021.
>    The rule **loses** in 2022 (−10.8 pp) and 2026 (−8.5 pp).
>
> **The honest ladder, no forward-looking filter anywhere:**
>
> ```
> Accumulate only                       57.1 %   7,290 signals
> + B_k > -0.50      (ENTRY-R10)        62.9 %   3,359 signals   LIVE
> + weekend/holiday  (ENTRY-R2)         64.9 %   2,815 signals   already live
> ```
>
> Production ran **57.4 %** on 428 live Alpaca trades against a 57.1 %
> baseline — it was reproducing the honest number all along. The gap that sent
> months of work hunting an exit bug did not exist.
>
> Check any signals file before believing it:
> `python3 tools/check_entry_filters_are_causal.py <file.csv>`
>
> Current state: `docs/CH2_STATE_20260921.md`. Detail:
> `docs/CH2_RECOVERY_POINT_20260919.md` §22.
>
> Kept below as the historical record. **Do not use these numbers.**

# L5 Canonical Baseline

Date locked: 2026-03-25 UTC

Context:
This baseline was locked after the sequential cognitive filtering run over the 12k quarantine universe produced the first materially improved governance-assisted result without flattening the primitive into a score-driven rule search.

Baseline metrics:
- Total signals: 3587
- 20-day win rate: 64.66%
- 20-day average return: 1.25%

Canonical baseline layers:

Layer 1: Primitive Geometric Eye
- `D_k >= 0`
- `Rev_k == 0`
- `B_k > prev_B_k`
- `M_k >= 0`

Layer 2: Common Sense Reality
- `Close >= 5.0`
- `Gate_Count >= 10`

Layer 3: Cognitive Restraint / Exhaustion & Chaos
- `raw_x_m <= 0.50`
- `F_n <= 1.65`

Canonical baseline rule:
- A row survives the canonical baseline only if it passes all three layers.

Implementation contract:
- This baseline is deterministic.
- This baseline uses strict fixed constants.
- This baseline does not use machine learning.
- This baseline does not use dynamic thresholding.
- This baseline does not use heuristic score optimization.

Architectural honesty:
- This is the locked baseline for the current L5 quarantine lane.
- This is not full governed L5.
- This does not yet include fundamentals.
- This does not yet include epochs.

Next work boundary:
- Future work may add later L5 layers above this baseline.
- Future work must not silently alter these baseline constants.
