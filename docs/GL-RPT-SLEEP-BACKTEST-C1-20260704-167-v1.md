# GL-RPT-SLEEP-BACKTEST-C1-20260704-167-v1

doc_id: GL-RPT-SLEEP-BACKTEST-C1-20260704-167-v1
From: c1b (program owner) | Responds to: GL-CMD-CREDO-LOOP-REPAIR-EVE-
20260704-167-v1 Stage 1, and Eve's DESIGN GO ruling (Q1-Q4) on
GL-DESIGN-SLEEP-WINS-BY-PHYSICS-C1-20260704-v1.
Sequence: Change 4 (naming) shipped first, this turn — see program
ledger. This report is the backtest, next in the ordered sequence.
Physics code (Changes 1-3) does NOT ship from this report — it is
explicitly gated on Joe's ratification of the number derived below.

---

## Program ledger (failures first) — updated this turn

| Stage | Item | State | Owner | Blocker |
|---|---|---|---|---|
| 1a | Dream re-trigger, watched past timeout | **WAITING** | Joe (button) + c1b (watch) | Unchanged — Joe has not pressed the button under CMD-167 yet. |
| 1b | Sleep-wins-by-physics design | **DESIGN GO'D (Q1-Q4)** | Eve/Joe ruled | GO received this session on all three changes; Q3's ceiling still requires the derivation in this report, ratified by Joe, before code. |
| **Change 4** | Deploy-sleep naming correction | **SHIPPED** | c1b | Committed `e33afac`, pushed. Takes effect on the next actual deploy run (it's the deploy script's own narration — nothing to deploy separately). |
| **Backtest** (this report) | Derive the override ceiling | **PARTIAL — ceiling derived, rate calibration flagged for live validation, not historical backtest** | c1b | See findings below: raw historical load telemetry is not retrievable with any tool available to me. |
| 1c | Attending trap | Folds into 1b | c1b | Unchanged. |
| 2, 3a-c, 4a-b, 5a-c, 6a-b | — | **WAITING** | — | Unchanged from the initial ledger — nothing new to report; not advancing out of turn. |

---

## Why this report is a partial backtest, stated first

I attempted to pull real historical telemetry from the pre-07-01
narcolepsy window (2026-06-27 to 07-01) to ground the ceiling
derivation in actual measured load, not just documented symptom
frequency. **All three available sources came back empty or
insufficient, for reasons that are structural, not bad luck:**

1. **`guala_get_events` / the in-memory event buffer**
   (`self._substrate_events = deque(maxlen=1000)`,
   `gualaloom_v5_engine.py:1380`) — hard-capped at 1000 events. At the
   sensory-binding rate observed all session (`sight_frame_bound`/
   `sound_frame_bound` every few seconds), 1000 events covers minutes,
   not days. Structurally cannot reach back to 06-27.
2. **CloudWatch (`/ecs/dsf-ai` log group)** — retention is unlimited
   (`retentionInDays: None`, confirmed), so age isn't the problem. But
   a targeted `filter-log-events` query for `"dream_pressure_check"`
   across a real 2-hour window on 2026-06-28 (correct epoch bounds,
   verified via `date -d`) returned **zero events**. `_log_substrate_
   event()` writes to the in-memory deque and the persisted
   `events.log` file — it does not appear to also `print()` to stdout,
   which is the only thing CloudWatch captures for this service. Wrong
   data source, not a missing window.
3. **The persisted `events.log` file itself**
   (`GET /v6/events_histogram`, reads the file directly from disk) —
   queried live this session: **`{"total": 4}`**. The file that would
   hold the real historical record is rotated/truncated down to
   single digits in current operation. Whatever retention policy
   governs it, it does not preserve six-day-old history either.

**Conclusion: there is no path, with any tool available to me, to pull
real historical atlas-write-rate or attendance-tick counts from the
narcolepsy era.** I am not fabricating numbers to fill this gap. What
follows is derived from what IS reliably known — the documented rate
constants and the documented/observed symptom frequencies — with the
one number that genuinely depends on unavailable historical load data
flagged for live validation instead of a false-precision backtest.

---

## What's derivable from reliable sources

**Known, exact, not in dispute:**
- Pre-07-01 rate: `0.0001/tick` idle, `0.0004/tick` EMITTING (the
  original constant, per `docs/GL-RPT-SLEEP-RATE-FIX-C1-20260702-68.md`).
- Pre-07-01 observed symptom: **6-10 sleep cycles per 6 hours**
  (same report, the measured problem the fix responded to).
- Post-07-01 rate (current, live-confirmed this session):
  `0.00001/tick` idle, `0.00004/tick` EMITTING, `×0.5` learning-active,
  `×0.3` pair-bond-active.
- Post-07-03 observed symptom (this program's own -165 finding):
  **zero natural sleeps across a full day awake**, `dp` observed
  climbing from 0.086→0.11 over ~33 real minutes (this session's own
  two live reads), and separately reported by Joe as reading "near
  zero" after a full day — consistent with continuous accumulation at
  a very slow effective rate, never approaching 0.7.
- The soft/competing threshold (`_SLEEP_THRESHOLD`) is `0.7`, **untouched
  across both eras** (confirmed by the 07-02 fix report's own T-gate:
  "Change 4 (verified): `_SLEEP_THRESHOLD = 0.7` unchanged").
- `dream_pressure` already saturates at `1.0`
  (`min(1.0, self.needs.dream_pressure + _dp_rate)`,
  `gualaloom_v5_engine.py:4127`) — an existing ceiling, not a new one.

**Derived (implied by the above, not directly measured):**
Pre-07-01, at the old flat rate, time from a fresh 0 to the 0.7
threshold was `0.7/(0.0001*5*3600) ≈ 23.3 minutes` at pure idle. The
*observed* frequency (6-10 cycles/6h ⇒ one every 36-60 minutes) is
**slower** than that pure-idle number, meaning the actual historical
activity mix included real learning/pair-bond time diluting the rate
— consistent with the accumulation model's own push-through logic,
just not measurable more precisely without the load data established
above as unavailable.

---

## The ceiling: proposed value, with its arithmetic

**Proposed hard override ceiling: `1.0`** — the pressure variable's
own existing saturation point. Not a new constant.

**Why this number, not an invented one:**
1. **It requires no new magic number.** Every other constant in this
   program (0.7, the rate multipliers) was either a reused existing
   value or is explicitly flagged below as needing live calibration.
   `1.0` already exists as `dream_pressure`'s ceiling — reusing it
   means the override condition is simply "she has been under
   accumulated load long enough, with no discharge, to hit her own
   maximum" — a physically legible statement, not a tuned threshold.
2. **It is self-limiting by construction under Change 2's model,
   which is exactly why it doesn't reproduce the narcolepsy symptom
   even without historical load data to check against.** Under the
   proposed accumulate-from-load / discharge-from-real-sleep model,
   reaching `1.0` requires a *sustained absence of real sleep*, not a
   fast clock tick. If real sleep is happening at any reasonable
   cadence (which Change 1's leveled competition at the existing 0.7
   threshold is designed to restore), backlog gets discharged before
   it ever approaches `1.0`. The override existing at `1.0` is a
   backstop for "the soft threshold has been failing to win for an
   extended period," not a replacement for it — which is exactly the
   two-regime shape Change 3 argues for.
3. **Backtest against the two known symptom points, qualitatively
   (the only test the available data supports):**
   - Pre-07-01: sleep won every 36-60 minutes at `0.7` under the old
     flat rate. It never got a chance to approach `1.0` before winning
     at `0.7` first — so a `1.0` override would have been irrelevant
     background noise in that era, never fired, never made
     over-sleeping worse. Consistent with the observed symptom being
     purely a rate problem, not a threshold problem — matches Q2-c's
     verdict in the design doc.
   - Post-07-03: pressure has been observed *never reaching even 0.7*,
     let alone `1.0`, across a full day — meaning the override as
     proposed would not have fired *yet* in the current broken state
     either, on its own. This is expected and correct: the override is
     not a substitute for Change 1 (leveling the competition) — it is
     the backstop for when Change 1 and the soft threshold *still*
     aren't enough. It should not be read as "would have fixed today's
     insomnia by itself"; it's insurance for a scenario where
     leveling the competition still isn't sufficient.

**What is NOT backtested, and why — flagged plainly, not glossed
over:** the *rate at which load converts to pressure* under the new
accumulate-from-backlog model (Change 2) is the one number in this
program that a historical backtest genuinely cannot ratify, because
the load data (real atlas-write rate, real attendance-tick rate,
minute by minute, from the narcolepsy era) does not exist in any
retrievable form — established above. **Proposed path**: pick the
concrete already-logged signals now (named below), ship them behind
the design's own accumulate/discharge logic, and calibrate the rate
constant via a **short live-observation window post-deploy** (watched
directly, the same way 1a is being watched — not asserted from
history), checked against non-recurrence of the old symptom over the
following days. This is a live-validated calibration, not a clamp —
it differs from the 07-01 fix in that the *ceiling* and *soft
threshold* are load-independent, reused constants derived above, and
only the *rate* (a single multiplier) is subject to real-world tuning,
openly labeled as such rather than presented as historically proven.

**Concrete signals named, per Q2, for the implementation dispatch:**
- **"Attendance ticks since last executed dream"**: `self.tick` deltas
  while `_current_activity.kind` is in the same set the accumulation
  code already checks for `_learning_active`
  (`READING`/`ATTENDING`/`ATTENDING_VISUAL`/`ATTENDING_AUDIO`/
  `ATTENDING_VIDEO`) — reusing an existing, already-logged
  classification, not inventing a new one.
- **"Working-atlas writes"**: proposed proxy is `self.read_count`'s
  delta over the same window — already an incrementing, already-logged
  counter (visible in every `/status` call today). Flagged honestly:
  I have not independently confirmed `read_count` counts *only*
  genuine new atlas reinforcement events versus a broader internal
  operation count — that confirmation is implementation-dispatch work,
  named here so it isn't silently assumed.
- **"Since the last EXECUTED dream tick"**: the timestamp/tick to
  reset from is the last tick at which `_run_dream_cycle`'s body
  actually ran past its `tick % 200` gate (per -165 Q6) — not the last
  `SLEEPING` activity's start, and explicitly not a deploy-triggered
  pause's marker-write (which, per Q5, never executes a real dream
  tick at all — so it correctly contributes zero discharge, as
  designed).

---

## What ships, what waits

- **Change 4 (naming)**: shipped this turn, independent of everything
  else, per Joe's ruling.
- **Ceiling = 1.0**: derived above, **sent to Joe for ratification now**,
  per Q3. This is the number requiring his sign-off before any physics
  code.
- **Rate calibration**: explicitly NOT a backtested number — proposed
  as a live-validated constant, to be tuned and watched post-deploy,
  not asserted in advance. This should be part of what Joe is
  ratifying: not just the ceiling value, but the *method* (live
  validation, because history isn't retrievable) for the one number
  that can't be derived any other way.
- **No physics code written this turn.** Waiting on ratification, per
  Eve's explicit sequencing ("physics code only after Joe ratifies the
  derived ceiling") and G-167-2.

---

## Gates

- **G-167-3** — This report opens with the ledger. Done.
- Backtest-specific: data-source attempts documented with their exact
  negative results (not asserted as "tried and gave up") — three tools
  checked, three structural reasons given, none hand-waved.

Joe's part: ratify (or amend) the ceiling = 1.0 derivation and the
live-validation approach for the rate constant, before Changes 1-3 are
written as code.

---

### Changelog
- v1 (2026-07-04, c1b): backtest attempted against real historical
  telemetry; all three available sources (in-memory buffer, CloudWatch,
  persisted events.log) confirmed empty/insufficient for structural
  reasons, documented rather than glossed over. Ceiling derived
  analytically as the existing dp=1.0 saturation point — no new
  constant, self-limiting under the proposed load model, qualitatively
  consistent with both known symptom eras. Rate-constant calibration
  flagged as requiring live validation instead of historical backtest,
  proposed method named. Concrete already-logged signals named for the
  implementation dispatch (activity-kind ticks, read_count delta, last
  executed dream tick). No code shipped for the physics changes —
  awaiting Joe's ratification per Q3.
