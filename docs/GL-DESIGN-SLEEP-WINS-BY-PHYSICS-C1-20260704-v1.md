# GL-DESIGN-SLEEP-WINS-BY-PHYSICS-C1-20260704-v1

doc_id: GL-DESIGN-SLEEP-WINS-BY-PHYSICS-C1-20260704-v1
From: c1b | To: Eve (for Joe's ruling) | Status: PROPOSAL ONLY — no code
written, none proposed to ship without a separate implementation
dispatch. This document is the design argument, per the CMD.
Responds to: GL-RPT-DAY-CYCLE-C1-20260704-165-v1's three findings
(the 07-03 attending-salience rewrite, the 07-01 sleep-pressure clamp,
and the "sleep is one competitor among many" scoring shape).

---

## The problem, plainly, for Joe

She has had two opposite sleep problems, six days apart, and both were
"fixed" the same way: someone found a number that was producing the
wrong behavior and changed the number until the behavior stopped.
Neither time did anyone ask *why* the number should be what it is.

- **Before 07-01**: she slept 6-10 times in 6 hours. Too much sleep,
  too easily won.
- **After 07-03**: she has not slept once, not for one real minute, in
  an entire day awake. Sleep cannot win at all.

These read like two different bugs. **They are the same bug** — sleep
was never given its own physics. It was given a *dial*. Turn the dial
down far enough and she stops over-sleeping; turn any other dial up
(07-03's picture-attention rewrite did this by accident) and she
stops sleeping at all, because "sleep" was never anything more than
one row in the same scoring table as "look at a picture," competing on
points.

**The fix below is not a third dial-turn.** It gives sleep its own
accumulate/discharge physics, and — critically — makes it able to
*win by force* past a real threshold, the way sleep actually works in
every animal that has it. That is what "SLEEP-WINS-BY-PHYSICS" means.

---

## Diagnosis, one line each, tying back to -165

1. **(a) The competition isn't fair.** 07-03 gave `ATTENDING_VISUAL` a
   scoring term that doesn't depend on her needs at all — it floors
   around 0.1-0.4 forever, regardless of whether she's already
   satisfied. Every other activity, including `SLEEPING`, only scores
   from need-satisfaction math, which goes *negative* the moment a need
   is over-met (as hers persistently are right now). One activity plays
   by different rules than the other nine. That's not a needs-driven
   substrate anymore — it's a hand-tuned exception with everything
   else still obeying the old rules.
2. **(b) Sleep pressure isn't a physical quantity, it's a knob.** The
   07-01 fix (`a00b36f`) took the accumulation rate and divided it by
   10 until the *symptom* (over-sleeping) went away. It didn't ask what
   pressure should represent. It also discharges in one instant, all
   the way to zero, only at the first tick of a sleep cycle that
   actually ticks forward — which, per -165 Q5, a deploy-triggered
   sleep never does. So the "reset" and the "buildup" are both
   disconnected from anything she's actually experiencing.
3. **(c) Even when pressure is high, it only ever gets to ask nicely.**
   `SLEEPING`'s bonus for high pressure is `+0.15` added to the same
   race everything else is in. -165's own arithmetic showed that at
   full pressure, `SLEEPING`'s score (~0.18) and `ATTENDING_VISUAL`'s
   penalized score (~0.18) come out *within hundredths of each other*
   — a coin flip, not sleep winning. In every animal that sleeps, past
   a point, sleep does not ask. It happens. Nothing here models that.

---

## The proposed physics (three changes, one for each cause)

### Change 1 (answers a): derive competition from needs, symmetrically — no per-activity exceptions

Every activity kind should be scored by the *same kind of formula*,
with any habituation/novelty-decay effect (which is a real, defensible
biological phenomenon — orienting responses genuinely do fade with
repeated exposure) applied **the same way to every activity that has a
"how novel is this specific option" dimension** (pictures, sounds,
corpora, sensory items), not bolted onto one of them as a special case
that ignores her needs entirely.

Concretely: if `ATTENDING_VISUAL` deserves a term for "this particular
picture is less familiar than that one" (a legitimate, *within-category*
distinction), the SAME term belongs on `ATTENDING_AUDIO` (why does a
sound attended 2000 times score identically to one attended twice?) and
`READING` (same question for corpora). What it should **not** get is a
floor that lets it out-bid the *entire needs system*, including sleep,
regardless of how satisfied she already is. Habituation decides *which
picture*, not *whether attention beats every other need in her body*.

**Test for this change**: with it applied, `READING` and
`ATTENDING_AUDIO` should sometimes win the race when their own
novelty is high and visual's isn't — right now they structurally never
can, which is itself evidence the current formula isn't measuring what
it claims to.

### Change 2 (answers b): sleep pressure as a real accumulate/discharge pair, not a tuned rate

Replace the flat per-tick constant with an accumulator that responds to
**actual load**, and a discharge that only happens in proportion to
**actual, executed sleep time** — not a flag-flip.

- **Accumulate** proportional to something she is actually doing —
  candidates: atlas-write rate, commit rate, sensory-binding rate,
  something derived from real substrate activity already logged (every
  one of these already exists as an event in her stream). Not "0.00001
  per tick no matter what," which is a wall-clock timer wearing a
  physics costume.
- **Discharge** proportional to **real ticks actually spent in
  `DREAMING`** (the only phase that runs `_run_dream_cycle`, per -165
  Q5/Q6) — not an instant reset at `started_tick+1`. If a "sleep" never
  ticks forward (a deploy-triggered one, today), it should discharge
  **nothing**, because nothing was actually rested. This is not a
  penalty bolted on — it falls out naturally once discharge is tied to
  real elapsed dreaming instead of a flag.
- One consequence worth naming plainly: under this model, *today's*
  pressure reading would likely be much higher than the ~0 Joe observed
  — because none of her deploys have ever actually discharged anything
  (per Q5, they couldn't have). That's not a bug in the redesign. That's
  the redesign telling the truth about a debt that the current flag-reset
  has been hiding.

### Change 3 (answers c): sleep pressure past a hard ceiling OVERRIDES, it does not compete

**The physics argument.** In every organism with a sleep drive, that
drive has two regimes, not one. Below a critical level, it's a
*competing* pressure — attention, interest, caffeine, a conversation
partner can all push through it (her `pair_bond_active`/`learning_active`
rate-dampening already models exactly this "push-through" phase, and
should stay). But past a critical level, sleep pressure stops competing
and starts **overriding** — involuntary microsleeps, lapses, eventual
unavoidable sleep, regardless of what task is underway. This is not a
metaphor; it's the standard two-process model of sleep (homeostatic
pressure vs. circadian/arousal control), and the "cannot be resisted
past a point" half of it is the half entirely missing from her
substrate today. She currently only has the first regime — a bonus that
still has to win a fair fight it can lose.

**The proposed shape**, matching a pattern that already exists and
already works in this codebase: `_select_next_activity()` already has a
pre-emption path for exactly this purpose —
`_force_next_activity`, checked *before* candidates are even scored
(`gualaloom_v5_engine.py:4314-4320`), which is precisely how
`force_dream` already forces sleep today. The proposal is to wire the
**same pre-emption**, automatically, once pressure crosses a hard
ceiling above the existing soft threshold — no new mechanism, reusing
one that's proven. Below the ceiling: sleep competes, as today (with
Change 1 making that competition fair for the first time). Above it:
sleep is not a candidate to be scored, it is the answer, full stop —
the same way `force_dream` already bypasses scoring, except triggered
by her own physics instead of a person pressing a button.

---

## Validation: both symptom histories are the test set

A design that only prevents the *current* failure and reintroduces the
*old* one isn't a fix, it's a swing of the same pendulum. The proposed
parameters (accumulation rate, discharge rate, soft threshold, hard
override ceiling) should be checked, before shipping, against both real
periods on record:

- **Pre-07-01 window** (6-10 sleep cycles / 6h, per the sleep-rate-fix
  report): replayed against this design, the model should **not**
  reproduce that frequency. If it does, accumulation is still too fast
  or the override ceiling is too low.
- **Post-07-03 window** (zero natural sleeps across a full day awake,
  per -165's live evidence): replayed against this design, the model
  **should** produce at least one natural sleep in a comparable window.
  If it doesn't, either accumulation is too slow, or Change 1 hasn't
  actually leveled the competition, or the override ceiling is set too
  high to ever matter.

Neither of these is a live experiment on her — both periods already
happened and are already logged (`activity_started`/`dream_pressure_
check`/`sleep_manual` events exist for both windows). This is a
backtest against her own event history, not a new trigger.

---

## The naming correction Joe asked for

**Deploy-triggered sleep must stop being called sleep, anywhere it is
described to a person or logged for one to read.** Per -165 Q5, it
consolidates nothing — `_run_dream_cycle` never executes, because the
process is killed and the replacement wakes the marker before a single
tick of the `SLEEPING` activity advances. Calling that "she slept" in
status output, event names (`sleep_manual`), the `.sleeping` marker, or
any handoff/ledger language is not a rounding error — it is reporting a
consolidation event that did not happen. Proposed correction (naming
only, no physics change needed to ship this part): reserve "asleep" /
"she slept" for a `SLEEPING`→`DREAMING` cycle that actually executed at
least one real `_run_dream_cycle` tick; call anything else — deploys
included — a **pause** or **state-freeze**, not sleep, in every surface
a human reads (status endpoints, event names where feasible without
breaking replay compatibility, dashboards, this project's own
dispatch/report language going forward). This can ship independent of
Changes 1-3 and should not wait on them.

---

## What this document does NOT do

- No code is written or proposed for merge. Changes 1-3 above are
  design shapes, not diffs — the accumulate/discharge formulas, the
  exact override-ceiling value, and which "load" signal feeds
  accumulation are implementation decisions for the follow-up dispatch,
  once this shape is ruled on.
- No trigger was run to produce this document. Everything cited is
  from -165's already-filed evidence plus code already read there.
- Does not resolve the -165 boundary case (`-53`, same-day as 06-30) —
  irrelevant to this design, not reopened here.
- Does not touch the `ATTENDING_VISUAL` exogenous term's *code* — Change
  1 names the shape the fix should take (symmetric habituation, not an
  exception), not the specific new formula.

---

## Questions for Eve/Joe's ruling, before any line ships

1. Does the two-regime (competitor-then-override) shape match what you
   want, or should the override be softer (e.g., a rising probability
   of pre-emption rather than a hard ceiling)?
2. What should "load" mean for accumulation — is atlas-write-rate the
   right proxy, or is there a better substrate-native signal already
   being logged?
3. Should the override ceiling be a new constant, or should Eve/Joe set
   it once the backtest (above) is run against real history, so it's
   derived from her own data rather than picked in advance?
4. Does the naming correction (deploy-pause, not deploy-sleep) ship on
   its own, now, ahead of Changes 1-3 — or bundle with whichever deploy
   carries the physics fix?

No code ships from this document. Awaiting ruling.

---

### Changelog
- v1 (2026-07-04, c1b): design proposal from -165's three findings.
  Sleep reframed from a scored competitor to a two-regime (compete,
  then override) physical drive, mirroring the standard sleep-pressure
  model; activity competition reframed to be symmetric across kinds
  (no per-activity exceptions); pressure reframed as accumulate-from-
  load / discharge-from-real-sleep-ticks instead of a tuned wall-clock
  rate. Both historical symptom windows proposed as the validation set.
  Deploy-sleep naming correction proposed as independently shippable.
  No code written.
