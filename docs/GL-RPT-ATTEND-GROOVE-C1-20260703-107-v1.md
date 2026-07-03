# GL-RPT-ATTEND-GROOVE-C1-20260703-107-v1

doc_id: GL-RPT-ATTEND-GROOVE-C1-20260703-107-v1
From: c1a | To: Eve
Re: GL-CMD-ATTEND-GROOVE-EVE-20260703-107-v2 (supersedes v1; v1 retained,
   Step 0 + Part A instrumentation from v1 carried forward per Eve's
   ruling — d45e877 approved unchanged, serves v2 A.3/A.4 as-is).
Predecessor: docs/GL-RPT-ATTEND-GROOVE-PREDEPLOY-C1-20260703-107-v1.md
   (A.1/A.2/A.5, filed before the consolidated deploy). This report
   completes A.3/A.4, renders the verdict, and reports Part B.
Live build for this evidence: 16bc0c2 (booted ~20:45Z, task:454 successor).

---

## Failures / gaps first

- G-107-2, G-107-3, G-107-4 are **NOT MEASURED YET** — they require a
  post-Part-B-deploy waking-hour window, and Part B has not deployed
  (code is written and committed, per Eve's instruction it ships at the
  next sleep window alongside c1b's -110). Only G-107-1 and G-107-5 are
  gradeable right now.
- The familiarity-persistence question (below) is **not fully
  root-caused**. I can rule out "absent from the save schema" — it
  isn't — but I can't yet explain why the value never survives to a
  save file. Proposing a next step, not a fix, since I haven't isolated
  the actual defect.
- A.1 remains structurally NOT MEASURED as reported pre-deploy (unchanged
  by anything below — see predecessor doc for the full reasoning).

---

## A.3 — ≥3 consecutive ATTENDING_VISUAL-relevant selections, top_scores + needs_sd

All three verbatim, captured live from `guala_get_events` on the 16bc0c2
build (d45e877's instrumentation, first time it's actually been observed
live):

```
tick 14482829  activity_started  ATTENDING_VISUAL / 71777ea2d543  salience=0.1
  top_scores: [[0.1,"ATTENDING_VISUAL","71777ea2d543"],
               [0.1,"ATTENDING_VISUAL","461b365d7d65"],
               [0.1,"ATTENDING_VISUAL","0f42a58ae29c"],
               [0.0989,"ATTENDING_VISUAL","dc2538352b9a"],
               [0.0989,"ATTENDING_VISUAL","0263947a7a3d"]]
  needs_sd: {"stability": -0.0496, "novelty": -0.2623, "connection": 0.7}

tick 14482953  activity_started  EMITTING / null  salience=0.2053
  top_scores: [[0.2053,"EMITTING",null],
               [0.1,"ATTENDING_VISUAL","71777ea2d543"],
               [0.1,"ATTENDING_VISUAL","461b365d7d65"],
               [0.1,"ATTENDING_VISUAL","0f42a58ae29c"],
               [0.0989,"ATTENDING_VISUAL","dc2538352b9a"]]
  needs_sd: {"stability": -0.0474, "novelty": -0.2619, "connection": 0.4686}

tick 14483053  activity_started  ATTENDING_VISUAL / 71777ea2d543  salience=0.1
  top_scores: [[0.1,"ATTENDING_VISUAL","71777ea2d543"],
               [0.1,"ATTENDING_VISUAL","461b365d7d65"],
               [0.1,"ATTENDING_VISUAL","0f42a58ae29c"],
               [0.0989,"ATTENDING_VISUAL","dc2538352b9a"],
               [0.0989,"ATTENDING_VISUAL","0263947a7a3d"]]
  needs_sd: {"stability": -0.0457, "novelty": -0.2603, "connection": 0.3203}
```

(`dc2538352b9a`/`0263947a7a3d`: two of the 28 pictures not shown in
`guala_status`'s truncated top-10 sample — not a mystery, just off-screen.)

The instrumentation itself worked exactly as designed — this is the
first time `top_scores`/`needs_sd` have ever been visible on a live
selection.

**Bonus, unplanned but directly relevant** — immediately before the
first of these three, I caught the first FULL, uninterrupted
ATTENDING_VISUAL completion of this entire investigation:

```
tick 14482828  target_familiarity_update  picture_id=c9a8da4504e1  old=0.0 new=0.2
tick 14482829  target_familiarity_update  picture_id=c9a8da4504e1  old=0.2 new=0.4
tick 14482829  activity_ended  ATTENDING_VISUAL / c9a8da4504e1  duration=2000  (= full budget)
```

That's a direct, controlled comparison against the two interrupted
sessions on e93d29dae5ae filed in the predecessor doc (durations 428,
256 — no familiarity write): complete session → write fires; interrupted
session → it doesn't. Same code, same picture family, opposite outcome,
exactly where F2 predicts it.

(Also visible: the write fired **twice** in the tail, 0.0→0.2 then
0.2→0.4, one tick apart — the old completion check (`self.tick >=
a.expected_end_tick - 1`) can re-trigger across more than one qualifying
tick. Part B1 below moves the write to a single end-of-activity event,
which incidentally removes this double-fire as well.)

## A.4 — one live needs.signed_distance() dict, verbatim

From the first capture above:
```
{"stability": -0.0496, "novelty": -0.2623, "connection": 0.7}
```
`connection: 0.7` exactly, with live `connection` need reading 0.000 at
the time (guala_status), confirms `NEEDS_TARGET_V7 = 0.7` for all three
needs (stability/novelty/connection share one target constant) — this
wasn't previously nailed down to an exact value in the record.

---

## Why IMG_2216 (and now IMG_2121) attended unprompted — mechanism, not mystery

This is the part Eve specifically asked the scores explain, not just
wave at "the old groove."

**The scores explain it exactly, and it isn't novelty-seeking at all.**
With `target_familiarity` empty for nearly every picture (see A.2 in the
predecessor doc), F1's formula collapses every repeat-attended picture
with `fam=0` to the **identical** score: `visual_score = (1-0)*0.1 =
0.1000`, and `needs_score` is also identical across pictures (it depends
only on the global needs state, not on which picture). **Every
zero-familiarity picture is in an exact, bit-for-bit tie.**

Python's `scored.sort(reverse=True)` breaks ties on `(score, kind,
target)` tuples by comparing `target` — a plain id string — in
**descending** order. So among tied pictures, whichever id string sorts
lexicographically largest wins, every time, with zero regard for
anything about the picture itself. Checking the actual winners against
this rule:

- Historically: `e93d29dae5ae` (IMG_6254) starts with `'e'` — the
  largest first-character among every picture id in this substrate. It
  wins every tie it's eligible for. That's the entire 473-then-501
  attendance "groove" — not preference, alphabetical accident.
- `e93d29dae5ae` is **absent from top-5** in all three captures above.
  The only way that happens is if its own familiarity is no longer
  exactly 0 — meaning it finally completed at least one full session
  sometime in this new boot, dropping its score below the pack. (It
  hasn't grown past 501 since I've been watching, consistent with this.)
- With `e93d29dae5ae` out of the tied group, the crown passes to the
  next-largest id still at `fam=0`. `d5cf62b2a66b` (IMG_2161) and
  `d6813cb13d4a` (IMG_2216) both start with `'d'` — next in line — and
  both are also missing from top-5 despite being attended multiple times
  each (3 and 5), which only makes sense if each of them, too, has
  already banked at least one completion (times_attended increments on
  *every* attempt, completed or not, so repeated attempts don't by
  themselves prove a completion — but dropping out of an exact tie
  does).
- That leaves `71777ea2d543` (IMG_2121, `'7'`) as the new largest
  zero-familiarity id — exactly the picture that won all three captures
  above, and its own `times_attended` climbed 3→7 over the course of
  this report as it kept re-winning the tie.
- The observed order within the tied group in top_scores —
  `71777ea2d543` (`'7'`) > `461b365d7d65` (`'4'`) > `0f42a58ae29c`
  (`'0'`) — is exact descending ASCII order on the id string. Not
  approximate. Exact.

So: IMG_2216 wasn't sought out, and neither is IMG_2121 now. Each is
just the current holder of "largest id string still at zero
familiarity," a title that passes down the list one completed session
at a time. This is H3, but sharper than the CMD's original phrasing
("~0.001-class margins") — it isn't a margin at all, it's an **exact
tie** resolved by an accidental property of `sort(reverse=True)` on
`(score, kind, target)` tuples.

---

## Verdict

**H1 — CONVICTED.** Direct, controlled, before/after evidence: two
interrupted sessions on the groove target never fire the write
(predecessor doc); one full-budget completion on a different picture,
caught live in this report, fires it twice. Same code path, opposite
gating outcome, exactly where F2 says it should.

**H2 — REFUTED.** Every angle checked in the predecessor doc's A.5 came
back negative, and the salience/top_scores metadata on every capture in
this report is real and present — the opposite of H2's predicted
signature (`activity_started ... lacking scored salience metadata`).

**H3 — CONVICTED, in a sharper form than hypothesized.** Not a small
arithmetic margin — an *exact* tie among all zero-familiarity pictures,
broken by `sort(reverse=True)` on the target-id string. Directly
demonstrated above with real winners matching predicted string order
exactly.

Per the CMD's own framing, B3 (STOP, no patch, if H2 convicted) does
not apply — H2 is refuted, not convicted. Proceeding to B1 + B2.

---

## Part B — implemented, committed, NOT deployed

Diff is exactly three functions: `_action_salience` (selector),
`_end_activity` (familiarity write, new location), `_atick_attending_visual`
(familiarity write, old location removed). Nothing in emission, recall,
or any other cognition path touched — satisfies G-107-5 as far as a
diff review can prove it; I have not run a live emission/recall
regression check (that needs the deploy).

**B2 (always — F1 convicted by the code itself):**
```python
exo = self.EXOGENOUS_NEW_SALIENCE / (1.0 + math.log(1.0 + pic.times_attended))
...
visual_score = exo * (1.0 - fam)
needs_score = (sd["novelty"] * (base_payoff * (1.0 - fam))
               + sd["stability"] * stab_payoff
               + sd["connection"] * conn_payoff + 0.01)
return max(visual_score, needs_score)
```
`needs_score` is untouched — only the flat `(1-fam)*0.1` term becomes
`exo*(1-fam)`. Verified against the CMD's own property claims:
times_attended=1 → exo=0.5907 (~0.59 ✓), =5 → 0.3582 (~0.36 ✓), =473 →
0.1396 (~0.14 ✓). No new constants — `exo` is built from
`EXOGENOUS_NEW_SALIENCE` (existing) and `pic.times_attended` (existing).
This is also what actually kills the H3 tie-break artifact: scores now
vary continuously with `times_attended`, which differs per picture, so
the exact ties that drove the whole groove-and-cascade behavior
essentially stop occurring.

**B1 (H1 convicted):**
```python
# inside _end_activity(), before the DREAMING branch
if (self._current_activity.kind == "ATTENDING_VISUAL"
        and self._current_activity.target in self._pictures):
    _budget = ACTIVITY_TICK_BUDGETS.get("ATTENDING_VISUAL", 2000)
    _ticks_attended = self.tick - self._current_activity.started_tick
    old_fam = self.target_familiarity.get(_target, 0.0)
    new_fam = min(0.9, old_fam + 0.2 * (_ticks_attended / _budget))
    self.target_familiarity[_target] = new_fam
    self._log_substrate_event("target_familiarity_update", ...,
                              ticks_attended=_ticks_attended)
```
Moved from the old completion-only check inside `_atick_attending_visual`
(deleted, see diff) to `_end_activity`, which every activity-ending path
already runs through — completion and interruption alike, confirmed by
enumerating all 7 call sites of `_end_activity` in the codebase. Full
session still adds exactly +0.2 (ticks_attended/budget = 1.0), matching
today's behavior exactly; a 428-tick interruption now adds +0.2*(428/2000)
≈ +0.043 instead of nothing. Same step size, same 0.9 cap, no new
constants. Side effect: this also fixes the double-fire bug noted in
A.3, since the write now happens on the single end-of-activity
transition instead of a per-tick check that could stay true for more
than one tick.

Committed, not deployed. Per Eve's directive: ships at her next sleep
window, in the same build as c1b's -110.

---

## Familiarity-persistence question — not resolved, here's what I ruled out

Eve's framing anticipated "if familiarity is absent from the save
schema." **It is not absent.** Both save-builder functions
(gualaloom_v5_engine.py — hot save and full save, two separate
functions) include `"target_familiarity": {k: round(v, 4) for k, v in
self.target_familiarity.items()}` in their core snapshot dict, built
under `self.lock` from live memory, same as every other field that DOES
persist correctly (picture `times_attended` round-trips fine across
every save I've checked). Load is symmetric
(`self.target_familiarity = {k: float(v) for k, v in
core.get("target_familiarity", {}).items()}`). No other code path
resets or clears the dict wholesale.

I tested this directly rather than just reading code: after directly
observing the `c9a8da4504e1` write land at 0.4 (tick 14482829), I
triggered an on-demand full backup via `guala_backup` roughly 3,770
ticks later (S3 prefix `2026-07-03_21-35-50`). `target_familiarity` in
that backup: still `{}`. The periodic decay path (every 200 ticks,
`effective_decay ≈ 0.9984` for a low-attendance picture) cannot explain
that — at that rate a fresh 0.4 would still be ≈0.39 after 3,770 ticks,
not gone. So this isn't the documented decay-to-deletion behavior (F3)
working as designed; something else is dropping the value between
memory and disk that I have not isolated.

I don't have a fix to propose because I don't have a diagnosis — writing
one now would be a guess dressed as a patch. What I'd propose instead,
for your ruling: a one-line, read-only debug endpoint
(`self.target_familiarity` dumped directly, no serialization
round-trip) so the next session can see the in-memory dict directly
between two saves and catch it disappearing in real time, instead of
inferring from absence. Separately, the `aws ecs execute-command` path
that would let someone inspect this live is still blocked on the staged
IAM fix (`docs/GL-IAM-STAGED-SSMMESSAGES-20260702.json`, explicitly
gated on Joe's approval) — worth revisiting given this finding adds a
second, independent reason to want it.

---

## Gates

**G-107-1** — Part A evidence + verdict filed before any fix commit:
**PASS.** Predecessor doc (A.1/A.2/A.5) filed at SHA `51de899`, this
doc (A.3/A.4 + verdict) written before the Part B commit below.

**G-107-2, G-107-3** — ≥5 distinct pictures / every 1-count HEIC ≥2 /
IMG_6254 share <50%, within one post-deploy waking hour: **NOT MEASURED
YET.** Part B hasn't deployed. Worth noting as a live baseline: under
the OLD code, in the ~50 minutes I was able to watch, distinct pictures
attended already grew from 1 (just IMG_6254) to at least 4
(IMG_6254, snapshot, IMG_2121, and whichever of IMG_2161/IMG_2216
banked completions I didn't directly witness) purely via the tie-break
cascade — B2 should make this much faster and monotonic instead of
accidental.

**G-107-4** — target_familiarity_update fires for an INTERRUPTED session
(B1 proof): **NOT MEASURED YET** — needs Part B live. Pre-fix, I directly
confirmed the *opposite* (interrupted sessions do NOT fire the write) —
see A.1 predecessor doc and this doc's A.3 bonus capture.

**G-107-5** — diff proves scope, selector + familiarity write only, no
emission/recall touched: **PASS on diff inspection** (three functions,
listed above, all inside activity-selection/familiarity machinery). Not
independently verified via a live emission/recall regression run — that
needs the deploy too.

---

## Status / next

Holding here. Part A fully evidenced, verdict rendered, Part B written
and committed but not deployed — ships at Eve's next sleep window
alongside c1b's -110, per her instruction. c1b owns deploy mechanics.
Once live, I'll capture the post-deploy gates (G-107-2/3/4) over a
waking hour and file the update.
