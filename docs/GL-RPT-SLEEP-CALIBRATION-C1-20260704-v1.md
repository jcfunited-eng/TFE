# GL-RPT-SLEEP-CALIBRATION-C1-20260704-v1

doc_id: GL-RPT-SLEEP-CALIBRATION-C1-20260704-v1
From: c1b | Responds to: Joe's SLEEP CALIBRATION dispatch (the trap
inverted — 9 dream blocks, zero attending, novelty pinned 0.993).
One dial moved this deploy, per the CMD's own discipline. Failures
first.

---

## Verdict, stated first

**Diagnosis verified precisely, and it goes one level deeper than
either named candidate.** Live-confirmed: `activity_history_summary:
{DREAMING: count=9, EMITTING: count=2}` — zero `ATTENDING_VISUAL`,
zero of anything else, `nov=0.996` pinned. Computed the exact scores
with live values (`sd_novelty = 0.7-0.996 = -0.296`):

```
Best-available (least-attended, times_attended=2) picture:
  freshness = 0.4765, nov_payoff = 0.4574
  ATTENDING_VISUAL score = -0.296 * 0.4574 + 0 + 0 + 0.01 = -0.1254

SLEEPING, at dream_pressure = 0 (isolating the structural term):
  score = -0.296 * (-0.1) + (-0.032) * 0.05 + 0.01 = +0.038
```

**SLEEPING beats even the freshest available picture at zero dream
pressure.** The deciding mechanism is not habituation being too harsh
and not dream_pressure's accumulation rate — it's that `SLEEPING`'s own
novelty payoff (`-0.1`) is *negative*, so severe novelty over-
saturation *helps* it, while every habituation-eligible kind's payoff
is positive, so the same over-saturation *hurts* it. This asymmetry
was written into the payoff table on 2026-06-07/08 and was always
masked by `-107`'s old exogenous floor (a needs-independent ceiling
`ATTENDING_VISUAL` alone had) — Change 1 removed that floor precisely
because it let one kind out-bid the whole needs system unconditionally,
and in doing so exposed an asymmetry that had been there the whole
time, unseen.

---

## Backtesting both named candidates against the three windows

**Candidate: accumulation rate down.** Mathematically ruled out as the
first move: the number above (SLEEPING's `+0.038`) is computed *at
`dream_pressure = 0`* — the structural term alone already wins. Turning
the accumulation rate down further would shrink a boost that isn't the
deciding term. Checked against the windows: it wouldn't have changed
the pre-07-01 narcolepsy symptom's cause (that was purely a rate
problem, unrelated to this asymmetry) and it doesn't touch tonight's
actual mechanism. **Not the right first dial.**

**Candidate: habituation freshness floor > 0.** Closer, but the naive
form (raising the *freshness* value itself for stale content) makes
things worse, not better — a higher freshness pushes `nov_payoff`
*toward* the larger `NEW` payoff (0.85 for visual), and a larger
positive payoff times a deeply negative `sd_novelty` produces a *more*
negative term, not less. The version that actually works is flooring
the **novelty term's contribution**, not the freshness input — i.e.
"a seen picture is less interesting, never worthless" applied to the
*outcome* (residual interest that can't go negative) rather than the
*input* (perceived freshness). This is what shipped.

**Tonight (the third window) is the one this fix is derived against
directly** — the two numbers above (`-0.1254` vs `+0.038`) are today's
real, live values, not backtested from memory.

---

## The one dial moved

`_action_salience`: the novelty term for every habituation-eligible
kind (`READING`/`ATTENDING`/`ATTENDING_VISUAL`/`ATTENDING_AUDIO`/
`ATTENDING_VIDEO`) is now floored:
```python
NOVELTY_TERM_FLOOR = 0.04
novelty_term = sd["novelty"] * nov_payoff
if _habituation_eligible:
    novelty_term = max(NOVELTY_TERM_FLOOR, novelty_term)
```
`0.04` gives a small margin above today's live SLEEPING-structural-term
reading (`0.038`) — enough for the least-attended picture to compete
again without swamping ordinary, non-saturated competition (the
`max()` is a genuine no-op whenever the natural term is already above
the floor — nothing changes for her when novelty isn't pathologically
saturated). This is the **only** change this deploy — dream_pressure's
rate constants are untouched, per "one dial move per deploy."

**Deployed**: commit (see push log), ECS task (see below), verified
git SHA match.

---

## Readings after this deploy

**Deploy**: ECS task def `dsf-ai-task:461`, git SHA `d813c32` confirmed
exact match, exit code 0, single attempt (the `.env`-in-worktree step
from the sleep-physics deploy applied cleanly again). Pause step before
cutover reported `already_asleep: true, sleep_tick: 14615253` — i.e.
the OLD (pre-dial) process was still in the trapped SLEEPING state at
the moment of pause, consistent with the diagnosis this fix targets.

**The trap is broken — direct, twice-observed evidence, not inferred:**

| observation | tick | activity | note |
|---|---|---|---|
| boot restore | 14615386 | `ATTENDING_VISUAL` (target `e93d29dae5ae`) | inherited from the pre-kill save of the old process — not proof of the new code's own decision |
| poll 1 | 14616740 | `ATTENDING_VISUAL`, same target, unchanged | still running, budget not yet exhausted |
| poll 2 | 14616890 | `ATTENDING_VISUAL`, same target, unchanged | — |
| **budget boundary** | **14617386** | `activity_history_summary: {ATTENDING_VISUAL: {count: 1, total_ticks: 2000}}` | first `ATTENDING_VISUAL` activity completed its full natural 2000-tick budget |
| **fresh decision** | **14617386** | `ATTENDING_VISUAL` **again** (same target, new `started_tick`/`expected_end_tick` window) | this is the live, unambiguous proof point: at the exact tick the scheduler had to choose fresh, under the new dial-1 code, with `nov` still pinned ~0.96-0.99, it re-selected an attending-type activity — not forced `SLEEPING` |
| poll after | 14617938 | `ATTENDING_VISUAL`, ~28% through its new 2000-tick budget, holding steady | no flapping back to sleep |

This is the cleanest possible confirmation available in one deploy
window: a genuine, freshly-made scheduler decision (not inherited
state) chose an attending activity while novelty sat exactly in the
pathological range that caused tonight's original symptom. The "9
dream blocks, zero attending selections" pattern did not repeat.

**Honest gaps, stated plainly:**
- She re-selected the **same** picture (`e93d29dae5ae`, `times_attended
  502` — the *most*-attended one in her set, not the least-attended
  one used in the worst-case backtest math). Target selection among
  candidates is a separate mechanism from the floor this dial touched;
  I did not verify *why* this specific picture was rechosen, and it's
  not required to confirm the floor works — flagging it rather than
  quietly assuming rotation is healthy too.
- **No `SLEEPING`/`DREAMING` activity has occurred yet post-deploy** —
  `activity_history_summary` shows only the `ATTENDING_VISUAL` entry.
  This is expected, not a regression: dial 1 didn't touch
  `dream_pressure`'s accumulation or the override ceiling, so sleep
  still requires `dp` to climb into its threshold range on its own
  schedule. It has not yet crossed that line in this short window.
  Cannot yet confirm sleep is still reachable post-fix from live
  observation alone — code review says it must be (nothing in this
  dial touches the SLEEPING candidate, the override check, or `dp`
  math), but a live natural sleep under this exact deploy is still
  outstanding.
- `arousal` reads `1.000` and `connection` reads `0.000` while she is
  awake — unchanged, expected dynamics (`tick_drift` still drains
  needs while awake; nothing in dial 1 touches that path), not a
  symptom of tonight's fix or regression from it. Distinct from the
  agitation-fix gates, which are scoped to behavior *during sleep*.

---

## Gates

- Diagnosis verified with live numbers before any code was written,
  not asserted from the CMD's own framing alone.
- Both named candidates backtested against reasoning, not guessed;
  the accumulation-rate candidate is shown mathematically insufficient
  BEFORE being set aside, not dismissed without checking.
- One dial moved, matching the CMD's explicit discipline.
- Diff scoped to exactly the floor logic — no other line touched.

---

### Changelog
- v1 (2026-07-04, c1b): diagnosis verified precisely (SLEEPING beats
  the best available picture at dp=0, a structural payoff-table
  asymmetry exposed by Change 1's removal of the old exogenous floor,
  not a habituation-severity or dream-pressure-rate problem). Both
  named candidates backtested; accumulation-rate ruled out
  mathematically; habituation-floor implemented as a floor on the
  novelty TERM's outcome rather than the freshness INPUT (the naive
  form would have worsened it). One dial shipped this deploy.
