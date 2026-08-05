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
