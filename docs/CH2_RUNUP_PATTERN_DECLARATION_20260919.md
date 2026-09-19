# What the whole kernel does before a rise — declaration (2026-09-19)

Declared BEFORE the dense lanes finished building and BEFORE anything was
looked at. Provenance: **Joseph**, verbatim instruction —

> "you look for the favorable structures i.e. the price peaks... you look for
> what was happening with the kernel (the whole kernel) leading up to the price
> peak - find the pattern then bob's your uncle you know when to buy - look at
> the down slopes to see what the whole kernel was doing and boom you know when
> to sell and like I said apply the common sense investment rules and filter
> and you have a money making machine"

Every previous CH2 measurement declared a rule and tested it. This one does the
opposite and looks first, which is what was asked for.

## Why the input had to be rebuilt

The production lane export covers a **median of 13 %** of a body's sessions —
CH2 calls the kernel once per ticker per day only for names its scheduler
touched. Worse, the kernel emits roughly **8 tuples per 1,200 bars**: it
segments the series into gates and reports one tuple per structural event, not
one per day. A "daily reading" is the same still-open tuple re-reported.

`tools/ch2_dense_kernel_lanes.py` runs the canonical production entry point
once per bar per body on the prefix up to that bar. Prefix runs are required
and a single full-series run is forbidden: the chain is **not prefix-stable**
(at a fixed index, `M_k` moves by 1.7e-2, `U_star_k` by 1.6e-3 and `B_k` by
6.6e-4 when later bars are appended). Reading a full-series run would be
reading the future. The kernel is not modified and not reimplemented.

Sample: **3,000 bodies**, blake2b-seeded, every bar of their available history
after a 250-bar warmup.

## The split — fixed here, before any looking

Two cuts, both applied. Nothing is looked at outside the discovery cell.

- **Bodies**: the 3,000 sampled are split 50/50 by a blake2b hash of the
  ticker into `DISCOVERY_BODIES` and `VALIDATION_BODIES`.
- **Time**: sessions before **2023-01-01** are `DISCOVERY_YEARS`; from
  2023-01-01 on are `VALIDATION_YEARS`.

The pattern is found **only** in DISCOVERY_BODIES ∩ DISCOVERY_YEARS. It is then
written into this document verbatim and frozen. It is then run **once** on each
of the three held-out cells. If it is edited after a held-out number is seen,
the edit and the number are both recorded here and the result is void.

## Labelling the rises and the down slopes

Price peaks are Joseph's unit and a price definition is used for them, openly.
A zigzag with a **15 % retracement threshold** marks alternating troughs and
peaks. An **advance** is trough→peak of at least **+25 %**; a **decline** is
peak→trough of at least **−15 %**.

- **BUY sessions** — inside an advance, any session from which the remaining
  path to the peak still gains **≥ 15 %**. "You could still have bought here."
- **SELL sessions** — inside a decline, any session from which the remaining
  path to the trough still loses **≥ 10 %**.
- **ORDINARY** — every other session.

Labels are allowed to use the future. That is what a label is. **The rule may
use only the causal tuple**, and the causal tuple is the only thing fed to it.

## What "the whole kernel" means here

The unit is the tuple in the kernel's **own clock**, not a calendar window.
Consecutive distinct tuples are the kernel's own steps, so the pattern unit is
a **transition**: the previous distinct tuple's configuration and the current
one. That captures "leading up to" without inventing a lookback length.

A configuration is the joint native reading of all nine fields — no field
excluded, no field collapsed into a score:

`S_UF > U_star_k` | `R_UF > U_star_k` | `D_k ∈ {−1,0,+1}` | `sign(M_k)` |
`R_rev_k ∈ {0,1}` | `B_k` at its own levels (0 intact / spending / −1 exhausted)
| `C_k` level | `P_k` level

## Finding the pattern

In DISCOVERY only: for every transition observed at least **200 times**, the
enrichment `P(BUY | transition) / P(BUY)` and the same for SELL. Transitions
with enrichment above 1 form the buy pattern and the sell pattern. Selection
happens here and only here, and everything selected is frozen before any
held-out cell is touched.

## Joseph's common-sense filters, applied as filters and labelled as his

- no body with fewer than 250 sessions of history (zombie) — **his**;
- no entry after a pump: price up more than 50 % over the preceding 20
  sessions — the rule is **his**, the 50 %/20-session numbers are **mine**;
- **no dollar-volume floor.** An earlier draft of this document listed a $5 M
  median-dollar-volume floor under Joseph's filters. That floor was mine and
  he never said it. Removed, and the measurement re-run without it.
- exits are the sell pattern, so gains are not left to slip and a body is left
  before it goes bad.

## The bar

On each held-out cell, positions opened by the buy pattern and closed by the
sell pattern must beat, per position, the 95th percentile of a matched-timing
null drawn **inside the same body** — same count, same holding lengths, start
dates drawn only from sessions where a real entry was possible. **200 seeds.**

Failing on any held-out cell is a failure and is reported as one.

## Output

`artifacts/ch4_uf/ch2_runup_pattern_20260919.json`, the frozen pattern written
into this document, and a result section. Either answer is filed the same way.

---

## Result (2026-09-19) — **fails every cell, including in-sample**

Reported from the run **without** the dollar-volume floor, after Joseph's
correction that the floor was mine. The run with the floor is kept at
`ch2_runup_pattern_20260919_with_liqfloor.json`; **it reaches the same verdict
on every cell**, so the floor changes nothing here.

1,521,359 lane rows mapped to a fill bar; **1,503,632** pass Joseph's filters
(zombie and pump only). **284,932 BUY sessions and 335,248 SELL sessions** — a
quarter of all sessions are days from which the remaining climb still paid
15 %. Discovery cell: 60,587 rows (23.8 % BUY, 40.1 % SELL). 191 distinct joint
configurations occur; 42 reach the 200-observation support floor.

| pattern | cell | n | mean | win | hold | matched-timing null p95 | beats |
|---|---|---:|---:|---:|---:|---:|:--:|
| configuration | discovery (in-sample) | 9,126 | −0.15 % | 44.9 % | 26 | +3.44 % | no |
| configuration | held-out bodies, same years | 8,311 | −0.25 % | 45.6 % | 27 | +3.36 % | no |
| configuration | held-out years, same bodies | 70,874 | +0.56 % | 50.1 % | 11 | +0.80 % | no |
| configuration | held out both ways | 68,328 | +0.60 % | 50.3 % | 11 | +0.93 % | no |
| transition | discovery (in-sample) | 2,638 | +6.39 % | 45.3 % | 150 | +14.14 % | no |
| transition | held-out bodies, same years | 2,573 | +5.70 % | 45.3 % | 142 | +14.39 % | no |
| transition | held-out years, same bodies | 23,332 | +1.98 % | 47.4 % | 36 | +3.23 % | no |
| transition | held out both ways | 22,967 | +2.20 % | 47.8 % | 35 | +3.19 % | no |

One null **mean** printed as +1980.68 % in the last row. That is a real
artefact of removing the floor: a handful of micro-cap bodies return thousands
of percent from a random start, and they drag the mean. Every pass/fail
decision uses the **p95**, which is stable at +3.19 %, so the verdict is
unaffected. Noted rather than quietly dropped.

**It fails in-sample.** That is not a finding about the kernel — it is a defect
in my construction, and it is recorded as mine. The declaration selected every
unit with enrichment above 1.0, which took **17 of the 27** configurations with
support. A rule that fires on two thirds of all configurations selects nothing.
The declaration never fixed a sensible selection threshold and it should have.

### The pattern that is actually there

Enrichment `P(label | configuration) / P(label)`, discovery cell only, all nine
fields shown jointly.

**Before rises** (base 23.8 %):

| enrichment | n | the whole kernel, at that moment |
|---:|---:|---|
| **1.55×** | 370 | `S>U*` `R>U*` `D=+1` `M` bending back `R_rev=0` **carry spending** `C=3` `P=0` |
| 1.24× | 288 | `S>U*` `R>U*` `D=−1` `M+` `R_rev=0` **carry spending** `C=3` `P=0` |
| 1.23× | 279 | `S>U*` `R<U*` `D=+1` `M+` `R_rev=1` carry exhausted `C=3` `P=2` |
| 1.21× | 768 | `S<U*` `R<U*` `D=+1` `M−` `R_rev=0` **carry spending** `C=3` `P=0` |
| 1.20× | 806 | `S>U*` `R>U*` `D=+1` `M+` `R_rev=1` **carry spending** `C=3` `P=2` |
| 1.19× | 431 | `S>U*` `R<U*` `D=−1` `M+` `R_rev=0` **carry spending** `C=3` `P=0` |

**Before falls** (base 40.1 %):

| enrichment | n | the whole kernel, at that moment |
|---:|---:|---|
| 1.41× | 521 | **`S<U*` `R<U*`** `D=−1` `M−` `R_rev=0` **carry exhausted** `C=3` `P=0` |
| 1.33× | 404 | **`S<U*` `R<U*`** `D=+1` `M+` `R_rev=0` **carry exhausted** `C=3` `P=1` |
| 1.28× | 501 | **`S<U*` `R<U*`** `D=+1` `M−` `R_rev=0` **carry exhausted** `C=3` `P=0` |
| 1.28× | 482 | **`S<U*` `R<U*`** `D=−1` `M+` `R_rev=0` **carry exhausted** `C=3` `P=0` |
| 1.24× | 2,769 | **`S<U*` `R<U*`** `D=−1` `M−` `R_rev=1` **carry exhausted** `C=3` `P=2` |
| 1.23× | 613 | **`S<U*` `R<U*`** `D=0` `M+` `R_rev=0` **carry exhausted** `C=3` `P=1` |

**Two readings hold their direction, and both are Joseph's stated semantics.**

1. **`B_k` — carry.** Five of the six strongest rise-states are *carry
   spending*; **six of six** fall-states are *carry exhausted*. Structural
   carry being spent accompanies a rise; carry exhausted accompanies a decline.
2. **`U_star_k` read against `S_UF` and `R_UF`.** **Six of six** fall-states
   have support **and** resonance *both* beneath the uncertainty penalty. The
   rise-states are mixed. "Read against support and resonance, not alone" marks
   the down side cleanly.

**Nothing else holds.** The rise-states contain `D=+1` and `D=−1`, `M` rising
and bending back, `R_rev=0` and `R_rev=1`, support above and below uncertainty.
Direction, bend and geometry point both ways ahead of the same outcome. On the
fall side `D` and `M` are equally mixed — `D=−1` and `D=+1` both appear at high
enrichment. Either those fields do not mark run-ups and declines at all, or the
static joint configuration is the wrong shape to read them in.

### The size of the effect, stated plainly

23.8 % of sessions are already ones from which the remaining climb paid 15 %.
The single most informative joint state of the whole kernel raises that to
**36.9 %**, on 370 observations. On the fall side, 40.1 % becomes 56.6 %. That
is the ceiling this data supports — not a door, and not a money machine.

### What was too thin, for the record

Discovery held 60,587 rows because the lane export begins 2021-09 and the
declared time split at 2023-01-01 leaves 16 months, halved again by the body
split. Only 42 of 191 configurations cleared 200 observations. A denser input —
the kernel run daily over full histories rather than the 13 % the production
scheduler happened to touch — is what this measurement actually needed.

### Standing verdict

Nothing ships. The run-up pattern, found by looking rather than guessing, does
not beat random timing inside the same body on any cell. The one durable
observation is `B_k`: spending during rises, exhausted during declines.
