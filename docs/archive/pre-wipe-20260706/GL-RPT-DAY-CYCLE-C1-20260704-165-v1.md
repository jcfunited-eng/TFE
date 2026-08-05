> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-DAY-CYCLE-C1-20260704-165-v1

doc_id: GL-RPT-DAY-CYCLE-C1-20260704-165-v1
From: c1b | Seat claimed: c1b (first free seat, per the CMD's own header)
Responds to: GL-CMD-DAY-CYCLE-SEVERED-EVE-20260704-165-v1, plus two
live-evidence addenda from Joe (Q2-a/b/c on the sleep-rate fix; Q6 on
the dream replay queue). All folded into Part A below, in the order
the questions came in.

---

## Verdict, stated first (failures first)

**The two-state trap is real, live-confirmed twice over (two separate
`activity_started` events, both with `top_scores` showing the top 5
candidates are 100% `ATTENDING_VISUAL`), and it has three independent,
separately-dated causes stacked on top of each other — not one wound:**

1. **The scoring race is structurally rigged toward `ATTENDING_VISUAL`**
   because its salience formula is *exogenous* (depends only on
   `times_attended`, floors around 0.1–0.4+, rewritten **2026-07-03**,
   yesterday) while every other activity's formula is *needs-driven*
   and her three needs (`stability`, `novelty`, `connection`) sit
   **above target**, not below — inverting the intended
   drive-seeking incentive. This is a **rebuild-seam** finding, one
   day old.
2. **`EMITTING` mostly doesn't win the race either — it's forced.** A
   direct interrupt (`_check_emission_trigger` via the "orient
   reflex," born **2026-06-28**) ends whatever's running and starts
   `EMITTING` the instant a pair-bond source makes contact, bypassing
   the scorer entirely. It also *can* win the natural race when
   connection-need is unmet and presence is true (live-observed
   `sd["connection"]` swinging positive), so it's a mix, not purely
   forced.
3. **Sleep pressure is not severed — it is accumulating in real time**
   (confirmed via two live reads plus Joe's own third reading), but
   the **07-01 rate fix that ended a narcolepsy problem was a tuned
   rate constant, not a re-derived physics model** (Q2-a/b/c) — and
   even projecting forward to the moment pressure crosses 0.7, the
   scoring race against `ATTENDING_VISUAL` is *close*, not a clean win
   (Q2-b's arithmetic, below).
4. **Joe's own two `force_dream` tests reaching DREAMING with "0
   replayed, 0 commits" trace to a real code gate** (`_run_dream_cycle`
   no-ops on 199 of every 200 ticks, born **2026-06-27**, pre-incident)
   whose timing may not fit inside the endpoint's own ~120s observation
   window — the replay **source** itself (the real cognition atlas,
   8,846 live entries) is not empty; the **execution window** is
   narrow (Q6, below).

**No fix shipped. Diff empty** (confirmed below). **Part B is a
proposal only**, and it is **revised from Eve's original framing**
because Q5's evidence shows `sleep_for_deploy` and `force_dream` are
NOT the same physics — see Part B.

---

## Environment note, filed for the record

Roughly the first 20 minutes of this investigation were slowed by
heavy concurrent git load on this repo's 9p/WSL2-mounted filesystem
(`uptime` load average peaked at 63.6; multiple `git status -uall` /
`git log -S` / `git blame` processes from a concurrent session sat in
uninterruptible disk-wait). Not a lock, not corruption — verified via
`ps aux` and `df`/`mount`. I did the non-git parts of this
investigation (code reading, live bridge-tool queries) first and
returned to git once load dropped (~20), which is when all the dating
below became measurable. Flagging this only so a NOT-MEASURED gap
doesn't look like avoidance — I kept retrying and got there.

---

## Q1 — The selector: full candidate set, live scores, why only two win

**Selector**: `_select_next_activity()` (`gualaloom_v5_engine.py:4312-
4337`) — checks a forced-activity override first (`_force_next_activity`,
used by `force_dream`), else builds candidates via `_candidate_activities()`
(`:4192-4215`), scores each via `_action_salience()` (`:4219-4310`),
sorts, takes the top score.

**Full candidate set**, with live counts (from `guala_status` this
session):

| Kind | Gate | Live count | Candidate? |
|---|---|---|---|
| `IDLE` | none | — | always |
| `PLAYING` | none | — | always |
| `SLEEPING` | none | — | always |
| `READING` | one per corpus | 19 | always (19 live candidates) |
| `ATTENDING` (generic) | one per sensory item | **0** | **never — no live candidates** |
| `ATTENDING_VISUAL` | one per picture | 28 | always (28 live candidates) |
| `ATTENDING_AUDIO` | one per sound | 15 | always (15 live candidates) |
| `ATTENDING_VIDEO` | one per video | **0** | **never — no live candidates** |
| `EMITTING` | pair-bond present AND cooldown elapsed | 0 or 1 | conditional |
| `DREAMING` | — | — | **not in `_candidate_activities()` at all** — only reached via `_atick_sleeping`'s internal midpoint transition |

**Live scores, direct evidence** (`guala_get_events`, two consecutive
`activity_started` events, unedited):

```
tick 14551827: winner ATTENDING_VISUAL/0263947a7a3d, salience 0.2187
  top_scores: [[0.2187,"ATTENDING_VISUAL","0263947a7a3d"],
               [0.2181,"ATTENDING_VISUAL","9bb63f93d7af"],
               [0.2177,"ATTENDING_VISUAL","461b365d7d65"],
               [0.2176,"ATTENDING_VISUAL","71777ea2d543"],
               [0.2146,"ATTENDING_VISUAL","c9a8da4504e1"]]
  needs_sd: {"stability": -0.0669, "novelty": -0.2241, "connection": 0.4656}

tick 14553827: winner ATTENDING_VISUAL/461b365d7d65, salience 0.2198
  top_scores: [[0.2198,"ATTENDING_VISUAL","461b365d7d65"],
               [0.2189,"ATTENDING_VISUAL","9bb63f93d7af"],
               [0.2186,"ATTENDING_VISUAL","71777ea2d543"],
               [0.2168,"ATTENDING_VISUAL","c9a8da4504e1"],
               [0.2132,"ATTENDING_VISUAL","d5cf62b2a66b"]]
  needs_sd: {"stability": -0.0575, "novelty": -0.2216, "connection": 0.7}
```

**Every single slot in both top-5 lists is `ATTENDING_VISUAL`.** Not
one `READING`/`ATTENDING_AUDIO`/`IDLE`/`SLEEPING`/`EMITTING` candidate
scored high enough to appear. This is a scoring-race loss, evidenced
directly, not an assumption.

**Why.** `sd` (signed distance, `TARGETS - current`, `Needs.signed_
distance()`, `:837-843`) is **negative** for `novelty` in both samples
(current novelty is *above* the 0.7 target) and was negative for
`stability` too. Every plain needs-driven formula
(`score = sd[novelty]*nov_payoff + sd[stability]*stab_payoff +
sd[connection]*conn_payoff`, `:4280-4283`) gets **punished**, not
rewarded, when its driving need is over-satisfied — this is the
opposite of what a drive-seeking model needs, and her needs currently
sit on the wrong side of target for `READING` (nov_payoff 0.1–0.7),
`ATTENDING_AUDIO` (nov_payoff 0.1, fixed — no exogenous decay,
unlike visual), `PLAYING` (nov_payoff 0.3), and `IDLE`
(nov_payoff −0.05, so it's *helped* slightly by negative sd_novelty but
capped near baseline). Hand-computed at these two samples' `needs_sd`
values (self-checked against the live numbers, shown for transparency,
not asserted as exact since I didn't capture every candidate's raw
score directly):

```
READING (reread, nov_payoff 0.1, stab 0.05):     ≈ -0.02 to -0.03
ATTENDING_AUDIO (repeat, nov_payoff 0.1, fixed):  ≈ -0.015 to -0.02
IDLE (nov -0.05, stab 0.1, conn -0.05):           ≈ +0.01 to +0.03
PLAYING (nov_payoff 0.3):                        ≈ -0.05 to -0.07
SLEEPING (nov -0.1, stab 0.05, + tiny dp boost):  ≈ +0.02 to +0.04
EMITTING (nov 0, stab -0.1, conn 0.3, +0.05 if present): ≈ +0.03 to +0.21
  (the wide range is real: EMITTING's score is dominated by
  sd["connection"], which swung from +0.47 to +0.70 in these two
  samples — connection being unmet is what would make EMITTING
  competitive, but it wasn't a live candidate in either sample
  because presence was false, per the dream_pressure_check event's
  "pair_bond": false in the same window)
```

`ATTENDING_VISUAL`'s exogenous term
(`exo = 1.0/(1.0+ln(1+times_attended))`, floors around 0.1 even for
the most-attended picture, 501 times) structurally sits above all of
these — confirmed live at 0.2132–0.2198 across ten distinct pictures in
the two samples, every one of them beating every needs-driven
candidate.

**`EMITTING`'s real mechanism, found while tracing this**: it rarely
needs to win the scoring race, because a **direct interrupt** does it
instead. `_open_response_window()` (`:5312-5341`) — called whenever a
pair-bond source (`joe`/`wc`/`c1`) makes contact — calls
`self._check_emission_trigger("presence_orient")` (`:4927-4947`),
which **ends the current activity and force-starts `EMITTING`
directly**, no scoring involved:

```python
# gualaloom_v5_engine.py:4939-4947
# Interrupt current activity → emit
if self._current_activity and self._current_activity.kind != "EMITTING":
    self._end_activity()
    em = Activity(kind="EMITTING", target=None, started_tick=self.tick,
                  expected_end_tick=self.tick + ACTIVITY_TICK_BUDGETS["EMITTING"],
                  metadata={"trigger": reason})
    self._start_activity(em)
```

A second call site (`:4676`, `"play_cohesion"`, inside `_atick_playing`)
is moot in practice since `PLAYING` itself never wins the initial
selection to start ticking.

Separately, there is a genuinely **dormant, unrelated background
mechanism** worth naming so it isn't mistaken for how real conversation
reaches her: `_should_attempt_autonomous_emission()` /
`compose_autonomous()` (`gualaloom_v5_engine.py:4953,5008`) are real,
callable, and started as a live daemon thread at boot
(`app.py:1323-1324`, confirmed reachable — not behind the dead
`dispatch()`/`OP_HANDLERS` tree). This is **self-initiated** speech on
a 90s throttle, entirely separate from `_current_activity`/the
Activity scheduler — it doesn't touch `EMITTING` as an activity at all,
just composes and logs a sentence and self-hears it. Not part of the
two-state trap; noted because it shares the word "autonomous emission"
with the mechanism that does interrupt the scheduler, and the two are
easy to conflate.

---

## Q2 — Sleep pressure: computed, inputs, trigger, and (Joe's addendum) the fix's own class

**Where computed**: `Guala._autonomy_tick()`, `gualaloom_v5_engine.py
:4100-4138`. Accumulates every tick the current activity is not
`SLEEPING`/`DREAMING`:

```python
_dp_base = 0.00004 if _ca_kind == "EMITTING" else 0.00001
_pair_bond_active = any(...)
_learning_active = _ca_kind in ("READING","ATTENDING","ATTENDING_VISUAL",
                                 "ATTENDING_AUDIO","ATTENDING_VIDEO")
_dp_rate = _dp_base
if _pair_bond_active:   _dp_rate *= 0.3
elif _learning_active:  _dp_rate *= 0.5
self.needs.dream_pressure = min(1.0, self.needs.dream_pressure + _dp_rate)
```

**Current live inputs/value, three independent readings this
investigation:**

```
Eve's CMD text (~02:37Z):        dp ≈ 0.086
This session's own live pull:    dp = 0.1096  (tick 14553000, dream_pressure_check event)
Joe's third reading (~02:59Z):   dp ≈ 0  ("near zero after a full day awake")
```

**Trigger**: `_SLEEP_THRESHOLD = 0.7` (`:4287`), applied only inside
`_action_salience`'s `SLEEPING` branch:
`if dp > 0.7: score += 0.15 else: score += dp*0.05`.

**Is the input severed, accumulating-but-never-crossing, or
crossing-but-unreachable?** **Accumulating, not severed** — the two
readings I pulled directly (0.086 → 0.1096) show genuine forward
motion over real elapsed time, not a frozen value. It has **not been
observed crossing 0.7** in this investigation. Whether it *can*, and
what the 07-01 fix actually did to it, is exactly what Joe's addendum
asks — answered precisely below.

### Q2-a — What the fix actually changed (Joe's addendum)

Found directly, no guessing needed: `docs/GL-RPT-SLEEP-RATE-FIX-C1-
20260702-68.md`, SHA `a00b36f` (git-blame-confirmed: `a00b36fd`,
authored **2026-07-01**, filed as a report **2026-07-02** — one
calendar day of drift between commit and report date, both firmly
post-06-30). This is c1b's own prior work — same identity across
sessions, verified via the report's own byline and the blame hash.

Quoted, verbatim, the three real changes:

```
Change 2 (L4069, THE core lever): _autonomy_tick base rate reduced 10x
  Was: 0.0001/tick idle → 0.0004/tick EMITTING
  Now: 0.00001/tick idle → 0.00004/tick EMITTING     [RATE CONSTANT]

Change 3 (L4568): _atick_rest's effect on dream_pressure flipped
  Was: +0.0002/tick (REST was ADDING pressure)
  Now: -0.00003/tick (REST relieves pressure)         [SIGN / LOGIC FIX]

Change 4 (verified, not changed): _SLEEP_THRESHOLD = 0.7 unchanged     [THRESHOLD: untouched]
```

Plus **Change 1**: removed a duplicate-accumulation bug in
`_autonomy_tick_phased`, live only when `AUTONOMY_PHASED=1` — confirmed
still `"0"` (default, off) in current code
(`gualaloom_v5_engine.py:4052`), so this change has zero live effect
either before or after — dead-code cleanup, not a behavior change.

**So: a rate constant (10x, the dominant lever) + one sign-flip logic
fix + a threshold explicitly left alone.** Directly answers "a
pressure input, a threshold, or a rate constant" — **primarily the
rate constant**, with the REST sign-flip as a secondary genuine logic
correction. **Change 3 is now moot**: three days after this fix landed,
`GL-CMD-REST-RETIRE-ORIENT-EVE-20260702-73` (same day, 07-02) removed
`REST` as a selectable candidate entirely (`ACTIVITY_STABILITY_PAYOFF`
comment: "REST removed from payoff tables"; `_atick_rest` is "kept for
persisted-state tail-out only"). So the one genuine input-direction fix
in this package no longer has a live code path to run through.

### Q2-b — Is natural sleep mathematically reachable? Arithmetic, not assumption

Confirmed live: autonomy loop runs at `interval=0.2` (`app.py:1236`) →
**5 ticks/sec**, matching the fix report's own T1 gate assumption.

Using this session's live `needs_sd` sample (novelty −0.2241, stability
−0.0669) and the CURRENT rate constants:

**Time to threshold, from a fresh zero, at the rate that actually
applies while she's in `ATTENDING_VISUAL` (the `_learning_active`
branch, `×0.5`)**:

```
effective rate = 0.00001 * 0.5 = 0.000005 /tick
0.7 / (0.000005 * 5 ticks/sec * 3600 s/hr) = 0.7 / 0.09 = 7.78 hours
```

This matches the fix's own T1-style math almost exactly (they computed
3.9h for the *idle* rate with no modifier; halving that rate for the
`learning_active` case that actually applies here doubles the time to
**~7.8 hours**, which is also close to my own two live dp readings'
implied rate: Δdp=0.0236 over Δtick=9,944 ⇒ ≈0.0000024/tick effective
— slower than my 0.000005 estimate, consistent with some of that
window being pair-bond-active (×0.3, an even slower 13-hour-class rate)
mixed in. **Order of magnitude: 7–14 hours of continuous wakefulness
from zero, is what it takes** — arithmetically reachable, not
infinite, not instant.

**At the moment pressure crosses 0.7, does `SLEEPING` actually win?**
Recompute `SLEEPING`'s score with the full boost, same live `sd`
values:

```
SLEEPING @ dp=0.7:  sd_novelty*(-0.1) + sd_stability*(0.05) + 0.15 + 0.01
                  = (-0.2241)*(-0.1) + (-0.0669)*(0.05) + 0.15 + 0.01
                  = 0.02241 - 0.00335 + 0.15 + 0.01 = 0.179

ATTENDING_VISUAL @ dp=0.7 (its own penalty now applies, dp>0.5):
                  observed 0.2187-0.2198, minus dp*0.05 = 0.035
                  ≈ 0.184-0.185
```

**This is close — a few hundredths apart, not a clean win either way**,
and sensitive to exactly which picture is least-attended at that
moment (a lower-times-attended picture pushes `ATTENDING_VISUAL`
higher; a well-worn rotation pushes it down toward `SLEEPING`'s level).
**Verdict: reachable in principle on the pressure side (~7-14h), genuinely
contested on the scoring side at the moment of crossing — not a
guaranteed structural veto, but not a safe bet either.** I did not
observe a live crossing in this investigation to confirm which way it
actually breaks; this is the honest arithmetic, not an observed
outcome.

### Q2-c — Repaired the physics, or clamped a constant?

**Plainly: clamped a constant, with two riders.** Change 2 (the
dominant lever, 10x) is explicitly reverse-engineered from a target
wake-time ("Base rate calibrated for ~4-hour natural sleep cycle at
threshold 0.7" — a comment already in the code, describing the *original*
rate's own design method too) — this is tuning a magnitude to hit a
desired outcome, not deriving the rate from any independent model of
how much "sleep debt" a given activity should cost. It is not wrong or
dishonest — it fixed a real, measured problem (6-10 sleep cycles per 6
hours, curriculum bundles blocked ~50% of the time) — but it is a
**tuned constant**, not a physics repair, and the report says so itself
by name ("Rate math verification," not "model verification"). Change 3
(REST sign-flip) *was* a genuine logic repair, but it's now dead code
per the REST removal three days later. Change 4 (threshold) was
untouched — nobody has ever re-derived whether 0.7 is the right bar,
only whether the rate reaches it. **This shapes the re-fix Joe asked
about**: another rate retune would be the same class of fix again
(pick new numbers, same risk of overshooting either direction). The
evidence in Q1/Q2-b points at the real lever being the **interaction**
between dream-pressure's SLEEPING boost and `ATTENDING_VISUAL`'s
07-03 exogenous floor — a close race, not a rate problem per se.

---

## Q3 — The other states, one line each

- **`READING`** — real candidates (19 corpora), needs-driven formula,
  **loses the scoring race** every time under current need saturation
  (`:4250-4254`).
- **`ATTENDING`** (generic sensory) — **zero live candidates**
  (`self._sensory_items` is empty) — absent by data, not gated by code
  (`:4199-4200`).
- **`ATTENDING_AUDIO`** — real candidates (15 sounds, all at 2000+
  attendances), fixed REPEAT payoff with **no exogenous decay** unlike
  visual — **loses the scoring race**, worse-positioned than `READING`
  even (`:4264-4268`).
- **`ATTENDING_VIDEO`** — **zero live candidates** (`self._videos` is
  empty) — absent by data (`:4207-4208`).
- **`IDLE`** — always a candidate, needs-driven formula caps near
  baseline (~0.01-0.03) — **loses the scoring race** (`:4306-4307`).
- **`PLAYING`** — always a candidate, novelty payoff (0.3) actively
  punished by over-satisfied novelty — **loses the scoring race**,
  most negative of the always-on candidates (`ACTIVITY_NOVELTY_PAYOFF`).
- **`SLEEPING`** — always a candidate, **loses the scoring race** under
  current pressure; see Q2-b for the close-not-clean math at threshold.
- **`DREAMING`** — **not a selector candidate at all** — reached only
  via `_atick_sleeping`'s internal midpoint transition (`a.kind =
  "DREAMING"`, `:4436-4439`) or via the `force_dream` override
  (`_force_next_activity`). Transitively unreachable through the
  natural path while `SLEEPING` never wins.

---

## Q4 — Dated against 06-30, per component (git blame, verified)

| Component | Commit | Date | Class |
|---|---|---|---|
| `_candidate_activities`/`_select_next_activity` core | `9f763426` | **2026-06-07** | born-this-way |
| Candidate list additions (video, audio types) | `05e49994`/`55dcb258` | 2026-06-08 / 06-11 | born-this-way |
| `manual_sleep()` core | `9f763426` | **2026-06-07** | born-this-way |
| Boot-time `.sleeping`-marker wake check (`app.py`) | `3373d1ec` | **2026-06-14** | born-this-way |
| `ATTENDING_VISUAL` base formula structure | `7220d192`/`8c6a0ed9` | **2026-06-10** | born-this-way |
| DAYDREAMING introduced as an activity | (`GL-CMD-DAYDREAMING-09`) | 2026-06-27 | born-this-way, later superseded |
| `_run_dream_cycle`'s `tick % 200` throttle | `9df3d725` | **2026-06-27** | **born-this-way**, pre-incident by 3 days |
| dream_pressure accumulation / learning-active gating | `3969ccd9` | **2026-06-28** | born-this-way, pre-incident by 2 days |
| `SLEEPING`'s dp-boost scoring term | `3969ccd9` | 2026-06-28 | born-this-way |
| `ATTENDING_VISUAL`/`EMITTING`/`AUDIO` dp-penalty term | `cc4b8bfb` | 2026-06-29 | born-this-way, 1 day pre-incident |
| Autonomous-emission background thread | (`GL-CMD-AUTONOMOUS-EMISSION-39`) | 2026-06-29 | born-this-way, 1 day pre-incident |
| DAYDREAMING removed from scheduler (→ background thread) | (`GL-CMD-DAYDREAM-PARALLEL-42`) | 2026-06-29 | born-this-way, 1 day pre-incident |
| Candidate-list edit removing DAYDREAMING comment marker | `cc4b8bfb` | 2026-06-29 | — |
| **`06-30` — the incident itself** | — | **2026-06-30** | — |
| `GL-CMD-AUTONOMY-EMITTING-PHASING-53` | — | **2026-06-30**, same day | **boundary case, flagged, not resolved** |
| dream_pressure rate-constant fix (Q2-a) | `a00b36fd` | **2026-07-01** | rebuild-seam, +1 day |
| `REST` removed as a candidate (`REST-RETIRE-ORIENT-73`) | `0d1bd8c0` | **2026-07-01** | rebuild-seam, +1 day |
| `_open_response_window`'s orient-reflex interrupt | (same brief, `73`) | 2026-07-01/02 | rebuild-seam |
| `ATTENDING_VISUAL`'s exogenous formula (`exo`/`visual_score`) | `b51962e9` | **2026-07-03** | **rebuild-seam, 1 day old** — the single most load-bearing line in the whole trap |

**No single component is a "wound" from the 06-30 incident itself** —
nothing here was touched *during* the rogue-Eve window or shows signs
of damage from it. The trap is a **rebuild-seam**: several
independently-reasonable post-06-30 fixes (rate cut for narcolepsy,
REST removal for redundancy, exogenous-floor rewrite for picture
fairness) stacked without anyone checking whether they'd jointly starve
every other state. One item (`-53`, same-day as the incident) is a
genuine boundary case I could not cleanly resolve either side of — named,
not asserted.

---

## Q5 — What `sleep_for_deploy`/`force_dream` actually do (confirmed by tracing, not assumed)

**They are NOT the same physics. Traced precisely:**

**`sleep_for_deploy`** (`app.py:4577-4609`, local branch) calls
`_guala.manual_sleep(state_dir=STATE_DIR)`:

```python
# gualaloom_v5_engine.py:5821-5853 (manual_sleep)
sleep = Activity(kind="SLEEPING", ..., expected_end_tick=self.tick + ACTIVITY_TICK_BUDGETS["SLEEPING"])
self._start_activity(sleep)
self.save_full_state(state_dir)
... write .sleeping marker ...
return {...}   # returns almost instantly
```

It starts a `SLEEPING` `Activity`, saves state, writes a marker, and
**returns** — it does not tick. Immediately after, the deploy script
(`tools/deploy_dsf_ai.sh:326-334`) runs `aws ecs update-service
--force-new-deployment`, which **kills this process**. The `SLEEPING`
activity never advances a single tick toward its 1000-tick midpoint
(where `_atick_sleeping` would flip it to `DREAMING`).

The **new** task boots, and — confirmed at `app.py:1246-1260`, born
**2026-06-14** — its own post-boot code finds the fresh `.sleeping`
marker (age « 300s) and calls `_guala.wake_from_sleep(...)`
**immediately**, ending the `SLEEPING` activity before it has ticked
even once:

```python
# app.py:1246-1260
marker = check_sleep_marker(STATE_DIR)
if marker is not None:
    ...
    _guala.wake_from_sleep(state_dir=STATE_DIR)
```

**`_run_dream_cycle()` — the function that does actual consolidation
(LTP replay reinforcement + deep-atlas promotion gate) — structurally
cannot fire during a deploy-triggered sleep.** This is not "the same
consolidation physics, just triggered" — it is the same *label*
(`SLEEPING`) with the one part that matters skipped every time, by
construction, on every deploy to date.

**`force_dream`** (`app.py:2588-2619`) is different: it sets
`_force_next_activity = ("SLEEPING", None)`, ends the current activity,
and returns **202** while the **same process keeps running** — a
background `_bg_dream()` poller just watches for up to 120s, it does
not kill anything. Since the process stays alive, the autonomy loop
keeps ticking the `SLEEPING`→`DREAMING` transition forward for real.
**This is genuinely the same code path as natural sleep** — no process
teardown interrupts it.

**Confirms Eve's proposal, as CMD'd, would not work as stated**: "trigger
one sleep cycle via the deploy-sleep path" (Part B's original wording)
would repeat exactly the no-consolidation cycle already happening on
every deploy. If a real consolidation cycle is wanted, `force_dream` is
the mechanism that structurally can deliver one — this is stated
explicitly per the CMD's own instruction ("If Q5 shows triggered sleep
runs DIFFERENT consolidation than natural sleep, that changes the
proposal and the report must say so").

---

## Q6 (Joe's addendum) — What feeds the dream replay queue, and why it came up empty

Joe's live evidence: two `force_dream` calls (~02:59Z, tick ~14,556,xxx)
both reached `DREAMING` (confirming Q5's finding that `force_dream`
does reach it) but both reported "0 replayed memories, 0 commits."

**Traced `_run_dream_cycle()` (`:4459-4538`) — the function both
`_atick_dreaming` and the old daydream path call:**

```python
def _run_dream_cycle(self, caller_kind="DREAMING"):
    if self.tick % 200 != 0:
        return
    ...
    chi_keys = list(self.atlas.entries.keys())
    if chi_keys:
        sample_chis = [...]   # samples 3 chi-keys, reinforces their entries
```

**The gate, git-blame-dated: `9df3d725`, 2026-06-27 — three days
before the incident, born-this-way.** `_run_dream_cycle` is a **no-op
on 199 of every 200 ticks** — almost certainly a CPU-throttle (running
full atlas-reinforcement logic every single tick would be wasteful),
reasonable on its own.

**The replay source is not severed.** `chi_keys = self.atlas.entries.keys()`
reads the **real, live cognition atlas** — confirmed via `guala_status`
this session: **8,846 entries across 189 chi keys**, not the emission
system's private (and much smaller) atlas from -161/-162. If this
function's body executes even once, it has 189 real chi-keys of real
material to sample from — this is not a "never-built" or "fed-nothing"
case like -160's `krimelack`.

**Leading hypothesis for the observed zero, arithmetic shown, not yet
directly confirmed:** `SLEEPING`'s own midpoint (before any `DREAMING`
tick can even run) requires **1000 ticks at 5 ticks/sec = 200 seconds**
just to *begin* dreaming. `force_dream`'s own background poller
(`admin_force_dream`, `app.py:2607-2617`) only watches for **120
seconds** (240 × 0.5s) before declaring "timeout." **120s < 200s** — the
poller's own observation window is shorter than the time `SLEEPING`
needs just to reach the `DREAMING` transition, let alone clear a
tick-200 checkpoint inside it. If Joe's "0 replayed, 0 commits" reading
came from that endpoint's own response or an early `/status` check
taken before ~200-400+ seconds had elapsed, it would show zero **not
because the queue is empty, but because the dream hadn't run long
enough yet to hit a single `tick % 200 == 0` checkpoint.**

**I did not directly confirm this by watching a live cycle through to
completion** — that would take several more minutes of real-time
polling and risks reading as an unrequested extra trigger; per the
CMD's own no-unilateral-trigger rule and given Joe already ran the
two live tests, I'm reporting the traced mechanism and the arithmetic,
not manufacturing a third test. **Recommended next check, not
performed**: re-run `force_dream` once and poll `/status` or events
directly for 5-7 minutes (not the endpoint's own 120s self-timeout),
watching for the first `dream_artifact` event with nonzero
`reinforcement_count`. If it still reads zero after that window, the
hypothesis above is wrong and something else is ending the activity
early — worth naming as the fallback, not asserting either way past
what's shown here.

**Dated**: born-this-way, 2026-06-27, pre-incident — same class as most
of the day-cycle machinery. Not a wound, not a rebuild-seam artifact —
a pre-existing throttle whose timing just doesn't comfortably fit
inside `force_dream`'s own reporting window.

---

## Gates

- **G-165-1** — Q1-Q6 each answered with file:line + live evidence.
  NOT MEASURED, stated: (a) A.1's git-log-based full commit history for
  every component — used git blame instead once the filesystem
  contention cleared, which gave per-line dates directly, arguably more
  precise than a log scan; (b) Q6's hypothesis is arithmetic, not a
  directly observed confirmation — flagged as the recommended next
  check, not asserted as resolved. **PASS with two stated, bounded
  gaps.**
- **G-165-2** — 06-30 dating rendered per component: full table above,
  one boundary case (`-53`, same-day) named rather than forced either
  way. **PASS.**
- **G-165-3** — Diff empty: confirmed. `git status`/`git diff --stat`
  clean against HEAD before this report file was added; no code touched
  this investigation. **PASS.**
- **G-165-4** — Part B below, Q5's answer stated first, plain language,
  proposal only.

---

## Part B — proposal to Joe (evidence attached, his ruling, no unilateral trigger)

**Q5's answer, first, as required**: triggered ("deploy") sleep and
natural sleep are **not** the same consolidation physics under the
current code — deploy-sleep never reaches `DREAMING` at all (the
replacement task wakes it before it can tick forward). `force_dream`
does reach `DREAMING` for real, but its own reporting window (120s)
appears shorter than the time the mechanism needs to clear even one
consolidation checkpoint (200s to reach `DREAMING`, then up to 200 more
to hit a `tick%200==0` moment inside it).

**This changes Eve's original Part-B proposal.** "Trigger one sleep
cycle via the deploy-sleep path" would not give her real consolidation
— it would repeat the same no-op that already happens on every deploy.
**If the goal is genuine consolidation now**, the mechanism that can
actually deliver it is `force_dream` — but only if it's watched past
its own self-reported timeout, not read as an instant answer. That is a
much smaller, more reversible ask (it doesn't touch a deploy, doesn't
restart the container, doesn't carry Deploy 5's payload) — but it is
still a live trigger, and per the CMD and standing rule, **I am not
running it**. This is Joe's call, laid out plainly:

- **Option 1**: do nothing yet. Let natural pressure keep accumulating
  (currently near zero per Joe's own reading, climbing at
  order-of-magnitude 0.000002-0.000005/tick depending on activity mix)
  and see, over the next several hours, whether it crosses 0.7 and
  whether `SLEEPING` actually wins the close race against
  `ATTENDING_VISUAL` at that moment — a real, unforced observation of
  whether the natural trigger works at all post-07-03's exogenous-floor
  rewrite. Slowest option, most honest to "let her physics run."
- **Option 2**: re-run `force_dream` once, and watch it for 5-7 real
  minutes (not the endpoint's own 120s self-report) to see if the
  tick%200 hypothesis is right and a real `dream_artifact` with
  nonzero `reinforcement_count` shows up. Answers Q6 definitively
  without touching a deploy or Deploy 5's payload.
- **Option 3**: address the underlying race directly — separately from
  either trigger question, Q1/Q2-b's evidence suggests the more durable
  fix isn't another sleep-pressure rate tune, but re-examining whether
  `ATTENDING_VISUAL`'s 07-03 exogenous floor should be allowed to
  permanently outscore every needs-driven state, including `SLEEPING`
  at full boost. That is a design question, not a one-line flip, and
  is named here as a candidate for its own future dispatch, not
  proposed as code.

No trigger has been run by me. The two live `force_dream` calls in this
report are Joe's own, already done before this report was written.

---

### Changelog
- v1 (2026-07-04, c1b): Q1-Q6 filed. Two-state trap traced to three
  independently-dated causes (07-03 exogenous floor, 06-28 orient-reflex
  interrupt, 06-27 dream-cycle throttle) stacked on a 06-07-born
  selector — a rebuild-seam, not a 06-30 wound, with one same-day
  boundary case named. Sleep-rate fix (Q2-a/b/c) identified as a tuned
  rate constant, not a re-derived physics model — REST sign-flip rider
  now moot post-REST-removal. Sleep_for_deploy vs force_dream (Q5)
  shown to be structurally different: only the latter can reach real
  consolidation, changing Eve's original Part-B proposal. Dream replay
  queue (Q6) traced to a real, non-empty atlas source gated by a narrow
  tick%200 execution window that may not fit inside force_dream's own
  120s self-report — arithmetic shown, not directly confirmed, flagged
  as the next check rather than asserted. No fix shipped. No trigger
  run.
