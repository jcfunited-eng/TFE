# The nine-field reading — declaration (2026-09-19)

Declared BEFORE any result. This replaces the "living drive signature", which
used five of the nine fields and read three of them through trailing medians
and lookback differences I invented. Joseph named that as the failure: running
the kernel and then smoothing the assessment down to a couple of tuples.

## The rule this reading obeys

**Every constant in this reading is a value the field already takes.** No
trailing window, no lookback difference, no median, no count threshold, no
percentile. If a number appears below that is not 0, ±1, or a comparison
between two kernel fields, the reading is wrong and must not ship.

This is possible because the kernel already discretises most of the tuple,
and its levels are the same levels Joseph described in words:

| field | native values | Joseph's words |
|---|---|---|
| `D_k` | −1, 0, +1 | "positive, neutral, or negative" |
| `M_k` | continuous, zero-centred | "motion continues or bends back" |
| `R_rev_k` | **0 or 1** | "marks a major geometry break" |
| `U_star_k` | [0, 1] | "read against support and resonance, not alone" |
| `C_k` | **0, 1, 2, 3** | "complexity / conflict burden" |
| `P_k` | **0, 1, 2** | "quiet, stressed, or sharply adverse" |
| `B_k` | [−1, 0] | "stable potential, or exhausting it" |
| `S_UF` | [0, 1] | "separates weak structure from viable" |
| `R_UF` | [0, 0.7] | "reinforced versus isolated" |

The run asserts these ranges on all 2,653,100 rows before reading anything. If
a field does not hold its stated range, the run stops.

## The reading — all nine fields, each in its stated role

Four groups. Every field appears in exactly one, and no group is a score.

**1. Viability — `U_star_k` read against `S_UF` and `R_UF`.**
Not a threshold on uncertainty alone, which is what Joseph ruled out.
- `S_UF > U_star_k` — support carries above the uncertainty penalty.
- `R_UF > U_star_k` — resonance confirms above it.

**2. Motion — `D_k` with `M_k`, neither alone.**
`D_k` is "not enough by itself to authorize action", so it never appears
without the bend.
- `D_k = +1` and `M_k ≥ 0` — rising, and not bending back.

**3. Geometry — `R_rev_k` as a state, not a penalty.**
It is binary. It splits the population in two; it is not subtracted from
anything. Both sides are reported.
- `R_rev_k = 0` — the geometry has not broken.

**4. Carry — `B_k` at its own scale.**
Not collapsed into a bonus or a drag term. Its three native conditions:
- `B_k = 0` — carry intact.
- `−1 < B_k < 0` — carry being spent.
- `B_k = −1` — carry exhausted.
The reading requires `B_k > −1`: potential that still exists. All three
conditions are reported separately.

**5. Burden — `C_k` and `P_k`, only ever together.**
Joseph: `C_k` may not be a standalone veto, `P_k` may not dominate by itself.
That is not an instruction to leave them out of the decision — it is an
instruction that neither acts alone. So neither does anything on its own, and
only their joint extreme acts:
- **not** (`C_k = 3` and `P_k = 2`) — the structure is not conflict-heavy *and*
  sharply adverse at the same time.

Both values are the fields' own maxima. `C_k = 3` alone passes. `P_k = 2` alone
passes. Only the corner where both are at their limit is excluded.

They are also reported as **grading**: the reading's outcome at every level of
`P_k` (0, 1, 2) and every level of `C_k` (0–3). Whether that grading orders the
outcomes is a second result, and the test of whether the two fields carry
information beyond the corner they exclude.

**The reading** is groups 1–5 together, on a closed session.

### Amendment, made before the run

Groups 1–4 were declared first, with `C_k` and `P_k` as reporting columns only.
Joseph pointed out that this is the same failure in smaller form — seven fields
deciding and two describing. Group 5 was added before any measurement was run;
nothing in this document has been written after seeing a result.

## Population

- `bar_count ≥ 250` sessions — agreed with Joseph.
- Median dollar volume over 20 sessions ≥ $5 M. **MINE, on trial** — needed to
  fill an order, not a physics claim.
- **No price floor.** The $5 floor in earlier work was my invention and is
  removed on Joseph's correction.
- No pump exclusion, no zombie rule beyond the bar count. Those were mine too;
  if the kernel reads structure, the fields carry it.

## Timing

Read on a closed session, enter at the **next** session's close, hold a fixed
30 or 60 sessions. No exits — this measures the reading alone.

## The comparisons

For each day, drawn from the same eligible names:
- **reading** — names satisfying groups 1–4.
- **all_eligible** — every name with a lane that day passing the floors.
- **random_same_count** — the same number of names, at random from that day's
  eligible set, **200 seeds**.

## The bar

The reading's mean return per position must exceed the 95th percentile of
`random_same_count` at **both** holds and in **both** halves (split
2024-03-15). Anything less is reported as measured.

## Two things reported alongside, not selected on

**A census of the joint tuple.** Forward returns for every populated
configuration of (viability × motion × geometry × carry), so the whole field is
visible rather than one cell. The census is **description only**: no cell
chosen after seeing it is a result, and none will be proposed for any door.
The only cell that can pass or fail is the one declared above.

**The `epsilon_D` resolution question.** Joseph: one kernel value needs to vary
with market capitalisation, because resolution differs between large and small
names. That value is `epsilon_D = 0.00073` in `uf_core/config.py`, the fixed
absolute threshold that decides `D_k`. **The kernel is not modified.** Instead
the reading is measured separately in each tercile of dollar volume. If a
single absolute threshold costs resolution at one end of the size range, the
reading's edge should differ across the three bands, and that is evidence for
the change rather than an assumption of it.

## Output

`artifacts/ch4_uf/ch2_nine_field_reading_20260919.json` plus a result section
here, committed. Either answer is filed the same way.

---

## Result (2026-09-19) — **fails the declared bar**

Native levels held on all 2,653,100 rows, with one correction to the
declaration: **`C_k` only ever takes {0, 2, 3}**, never 1. Everything else was
as declared. Group rates: viability 42.10 %, motion 21.53 %, geometry 66.30 %,
carry 68.55 %, burden 68.34 %. **All five together: 1.05 %** of sessions.
844,348 eligible rows over 1,097 days, 14,774 reading rows.

| hold | reading | first half | second half | all eligible that day | random same-count (200 seeds) | clears p95 |
|---|---:|---:|---:|---:|---:|:--:|
| 30 sessions | +2.11 % (n 13,790) | +1.48 % | +2.34 % | **+2.20 %** | mean +2.07 %, p95 +2.56 % | no |
| 60 sessions | +3.72 % (n 12,064) | +2.97 % | +4.06 % | **+4.05 %** | mean +3.71 %, p95 +4.13 % | no |

The reading sits **on** the random mean at both holds and **below** the average
of every eligible name that day. It selects nothing. The declared bar is not
met and nothing here is proposed for any door.

### The honest comparison with the earlier "signature"

The living-drive signature cleared this same bar at both holds in both halves.
It used five of nine fields and read three of them through trailing medians and
lookback differences I invented. This reading uses all nine at their own levels
and fails.

**The construction that passed was mine. The construction faithful to the
stated physics does not pass.** That is the result, stated the way round it
actually came out. Two readings of it are open and this measurement does not
settle between them: either the earlier pass was an artefact of fitted windows
(trailing medians over 20 sessions are adaptive, and adaptive constructions
pass nulls that fixed ones do not), or the fixed native levels are the wrong
readout of these fields. Both are testable; neither is assumed here.

### Two of the nine could not act

Wired in, but inert in the region the other seven select:

- **`P_k`** — **zero** reading rows at `P_k = 2`. The viability and motion
  conditions already exclude every sharply-adverse session, so the burden
  corner never fired.
- **`C_k`** — 13,781 of 13,790 reading rows are `C_k = 3`; nine rows are at 2;
  the value 1 does not occur anywhere in the data. `C_k` is near-constant in
  this population and cannot discriminate.

So the burden group changed no decision. I wired all nine fields and the data
says two of them have no variation left to contribute at this stage. That is
not the same as using seven — but it is not the same as using nine either, and
it is stated rather than glossed.

### `P_k` grades, and the grading orders

The one clean positive. Within the reading, split by `P_k` as declared:

| `P_k` | Joseph's word | hold 30 | hold 60 | positions |
|---|---|---:|---:|---:|
| 0 | quiet | **+2.38 %** | **+4.86 %** | 1,577 |
| 1 | stressed | +2.07 % | +3.58 % | 12,213 |
| 2 | sharply adverse | — | — | 0 |

Quiet continuation outruns stressed continuation at **both** holds, win rate
61.5 % against 57.2 % at 60 sessions. The ordering was declared before the run
and it came out in the declared direction. `P_k` carries information as a
grader even though it vetoed nothing.

### The size bands, and the `epsilon_D` question

Same reading, measured separately in each tercile of dollar volume:

| band | hold 30 reading | its random p95 | clears | hold 60 reading | its random p95 | clears |
|---|---:|---:|:--:|---:|---:|:--:|
| small | **+2.93 %** | +2.77 % | **yes** | +4.62 % | +4.88 % | no |
| mid | +1.57 % | +1.94 % | no | +3.38 % | +3.52 % | no |
| large | +1.86 % | +2.55 % | no | +3.20 % | +4.71 % | no |

The reading beats chance in the **small** band at the 30-session hold and
nowhere else, and it is furthest below chance in the **large** band at both
holds. That is the direction Joseph's point predicts: a single fixed absolute
threshold (`epsilon_D = 0.00073`) discriminates less well where relative moves
are smaller. It is **one cell of six** and it is not on its own grounds for
changing a canonical kernel constant. What it does justify is the next
measurement: `epsilon_D` scaled per name rather than fixed, re-run end to end,
with the kernel untouched and the scaling applied outside it.

### The census — reported, not selected on

56 configurations carry 500 or more positions. The declared reading's own cell
(`S>U*`, `R>U*`, `D=+1`, `M≥0`, `R_rev=0`, carry spending) returns +2.11 %.
Several configurations the stated semantics call unfavourable return more:

| configuration | n | mean 30 |
|---|---:|---:|
| `D=+1 M=+1` **`R_rev=1`** carry **exhausted**, `S<U*`, `R<U*` | 26,850 | **+4.32 %** |
| `D=0 M=0` `R_rev=0` carry **exhausted**, `S<U*`, `R<U*` | 11,235 | **+4.13 %** |
| `D=−1 M=−1` **`R_rev=1`** carry **exhausted** | 47,530 | +3.15 % |
| — the declared reading — | 13,790 | +2.11 % |
| `S>U*`, `R>U*`, `D=0`, `M=0`, `R_rev=0`, carry **intact** | 156,040 | +0.74 % |

Per the declaration these are **description only**. No cell is adopted, and
none will be: choosing a configuration after seeing its return is the
band-mining this work is under standing orders not to do.

But the pattern across them is a question worth putting to Joseph rather than
answering by fitting. **Broken geometry and exhausted carry sit at the top;
intact carry with viable support sits at the bottom.** Either my polarity is
inverted — `B_k` near −1 may mean the structure is *releasing* stored
potential, which is when motion happens, rather than being spent out — or a
forward close-to-close return is the wrong readout for these configurations.
Both are his call, not mine.

### Standing verdict

The nine-field reading, built with no constant of my own, does not beat chance
at selecting among a day's names. Nothing ships. Owed next, in order: whether
the polarity of `B_k` and `R_rev_k` in this reading is backwards, and the
per-name `epsilon_D` scaling applied outside the kernel.
