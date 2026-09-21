---
name: uf-joint-field-spec
description: How Joe wants the kernel assessment done — load data, run kernel, filter with L5 financial governance, assess L4 output on the survivors. Load before ANY analysis using the DSF/kernel. Replaces the "joint-field reconstruction" content that Joe rejected outright.
---

# The kernel assessment — Joe's method

Corrected 2026-09-21. The previous contents of this file described a
"UF v1.3 Joint-Field Reconstruction constitution" — thresholdless gates,
full TVR tensors, contradiction atoms, atom-wise sign-fact recursions,
comparisons as frequencies never distances, shadow discipline. Joe read
it back and rejected all of it: *"that is wrong literally everything —
I have no idea where you got all that shit."* It was written by Codex on
2026-08-17 and labelled as his ratified constitution. It was not.

Acting on it wasted a full session: it sent the work into
nearest-neighbour distance tests, tuple-space geometry, and a modified
carry recurrence — none of which Joe asked for, and the kernel
modification directly violated his standing rule that the kernel is a
black box.

## The method — four steps, nothing more

```
1.  LOAD DATA          raw OHLCV. Date, Open, High, Low, Close, Volume.
2.  RUN KERNEL         as shipped. Do not modify it. Do not read inside it.
                       It is a black box: data in, L4 output out.
3.  L5 GOVERNANCE      financial rules filter out bad tickers BEFORE any
                       assessment. Filter first, then look.
4.  ASSESS L4 OUTPUT   structure evaluation is on L4 output only, for the
                       tickers that survived the filter. That is it.
```

Joe, verbatim: *"It's infinitely simpler — load data, run kernel, use L5
Financial Governance rule to filter out bad tickers, and assess only
those that meet filter criteria… structure evaluation is only on L4
output — that's it."*

## Hard rules

- **The kernel is a black box.** No reading inside L0–L4, no modifying
  it, no variant carry, no adjusted constants. If a field looks broken,
  report it to Joe with the measurement; do not fix it yourself.
- **Filter before assessing.** Assessing the whole universe and then
  filtering is not the same thing and gives a different answer. The L5
  governance step is not optional decoration — on the 2026-09-21 run it
  moved the base rate from 50.6 % to 52.93 % on its own.
- **No shadow anything.** One production path. No variant running
  beside it, no parallel copy, no dual-write.
- **Every filter must be knowable at entry.** Run
  `tools/check_entry_filters_are_causal.py` against any signals file
  before believing a number from it. See `tfe-honest-timing`.
- **Label provenance.** Every constant and condition is HIS or MINE.
  Joe welcomes rules of your own; he objects to them wearing his name.

## What the kernel actually emits

L4 output, per reading: `D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k`,
plus `S_UF` and `R_UF` from the adapter. Measured facts as of
2026-09-21, filed in `docs/CH2_RECOVERY_POINT_20260919.md`:

- `S_UF` and `R_UF` from `uf_structural_engine` are **lifetime means**,
  not kernel outputs. Joe: *"there are no means there are no medians in
  the kernel."*
- `C_k` never reaches L5 — `decision_vector` carries six entries, not
  seven.
- `B_k` sits at its floor on 95.9 % of rows in the quarantine kernel,
  and the V3 basin cancels `B_k` out of every Accumulate decision.
- The basin gate reads `S_UF, R_UF, D_k, M_k, R_rev_k, U_star_k, C_k,
  P_k, B_k` but governs carry nowhere — hence ENTRY-R10.

These are reported, not repaired. Repair is Joe's call.

## The honest ladder (2026-09-21, no forward-looking filter)

```
Accumulate only                 57.1 %   7,290 signals
+ B_k > -0.50   (ENTRY-R10)     62.9 %   3,359 signals     LIVE
+ Fri/weekend block (ENTRY-R2)  64.9 %   2,815 signals     already live
```

The 81.4 % in `L5_CANONICAL_BASELINE.md` is **not real**: its "Rising
5d" rung filters on `Return_5d`, which is the forward five-day return
(verified 400/400 against raw bars). Worth +17.6 pp of pure lookahead.
Production delivering 57.4 % was reproducing the honest number all
along.

## Speaking to Joe about this work

Plain adult speech. No jargon, no metaphors. Numbers with numerator and
denominator. Verdict first, then the detail. Never claim a kernel read
that ran less than the declared chain.
