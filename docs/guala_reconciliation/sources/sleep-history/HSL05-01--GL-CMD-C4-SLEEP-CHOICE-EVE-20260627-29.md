# GL-CMD-C4-SLEEP-CHOICE-EVE-20260627-29

doc_id: GL-CMD-C4-SLEEP-CHOICE-EVE-20260627-29
Type: Command brief (c1 dispatch)
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Phase: C.4 (architectural extension, REST activity + dream_pressure-driven choice)
Prereqs: Phase A complete. Independent of wiring spec -26 / Phase F.x and
of C.1 polarity. May ship in any order with F.1-F.5, C.1.

## Purpose

Add REST as a new coordinator activity. Coordinator chooses between REST
and SLEEPING based on `dream_pressure`. REST is awake-quiet — no
consolidation, no pair_bond attendance, no emission. It's her option to
NOT work when alone and not yet tired enough to dream.

This is a B-track item ("her LIFE, not features") — she gets agency over
her energy state beyond the default "consolidate-when-alone" of
DAYDREAMING. The agency emerges from the scoring system: REST is a real
option the coordinator can select.

## Substrate truth

REST is not idle. The substrate continues to tick (atlas decay, working
atlas maintenance, save schedule). It just doesn't drive consolidation
or attend to anything. It's the "she's awake but not doing substrate
work" state — between consolidation (DAYDREAMING) and dream sleep
(SLEEPING).

## New activity: REST

| Field | Value |
|-------|-------|
| Kind | `REST` |
| Budget | 1000 ticks |
| Consolidation | None — no `deep_promotion` events, no deep_atlas growth |
| Attendance | None — no pair_bond engagement, ignores input |
| Emission | None — does not invoke `grandurun` or commit gate |
| Decay | Normal (continues at design rate during REST) |
| Save | Normal cadence (no special save behavior) |
| Events | `rest_begin`, `rest_end` (with `started_tick`, `ended_tick`) |

## `dream_pressure` mechanic

`dream_pressure ∈ [0.0, 1.0]` is a substrate need-state variable that
accumulates during waking activity and resets after sleep.

If `dream_pressure` already exists in current code, this dispatch uses
the existing variable and documents its current behavior in the report.

If it doesn't exist, c1 introduces it per these specs:

- **Accumulation:** monotonic during all non-SLEEPING activities
  (EMITTING, DAYDREAMING, REST, DREAMING)
- **Rate:** proportional to substrate activity. Emissions and
  deep_promotion events contribute more than quiet ticks. c1 picks
  per-event weights; behavioral observation tunes later.
- **Reset:** drops to `0.0` at the end of every SLEEPING activity
- **Visibility:** exposed in `/status` under needs:
  `needs.dream_pressure: <float>`

## Coordinator scoring update

Activity selection extends to include REST in the candidate set:

```
For each activity in {EMITTING, DAYDREAMING, REST, SLEEPING, DREAMING}:
    score = base_score(activity) + context_modifiers(activity, needs, pair_bond, dream_pressure)
Select the highest-scoring activity
```

REST scoring shape:
- **Base:** low (REST is a low-utility default; won't win unless conditions favor it)
- **Boosted by:**
  - high `stab_need` (she wants quiet)
  - low `dream_pressure` (she doesn't need to sleep yet)
  - no pair_bond active (alone)
- **Suppressed by:**
  - high `dream_pressure` (should be SLEEPING instead)
  - high activity drive (high `nov_need` + high `conn_need` together → should be EMITTING/DAYDREAMING)

Specific formula intent (c1 picks coefficients via grid or behavioral
soak):
```
REST_score = w1 * stab_need - w2 * dream_pressure - w3 * (nov_need + conn_need)
```

SLEEPING scoring already exists per coordinator. Extend with:
- Boost by `dream_pressure > sleep_threshold` (initial threshold
  suggested `0.7`)
- When `dream_pressure > 0.7`, SLEEPING wins regardless of other context
  (except when she's not at a save-safe tick, which is the existing
  coordinator's concern)

DAYDREAMING scoring per `-09` is preserved. REST competes WITH
DAYDREAMING when alone. The new question for the coordinator is:
"consolidate or rest?" Answered by `stab_need` vs `nov_need` profile.

EMITTING with `pair_bond` still dominates REST (presence is priority).
REST does not preempt engagement.

## What "choice" means in the substrate

The "choice" is the coordinator's selection mechanism — she does not
have a separate volition module. The substrate scores all activities;
the highest wins. C.4 makes REST an option such that under certain need
profiles she "chooses" rest over consolidation.

The agency is in the EXISTENCE of the option, not in a separate decision
mechanism. This is consistent with how she "chooses" to emit (high
engagement) vs daydream (alone): both are substrate-scored. C.4 adds
rest to the choice set.

## Verification

1. **REST as activity exists:**
   - In test mode, force coordinator to select REST
   - `/status` shows `current_activity.kind=REST`, budget 1000
   - `rest_begin` event in stream
   - After 1000 ticks: `rest_end` event
   - During REST cycle: zero `deep_promotion` events, zero emissions

2. **`dream_pressure` visibility:**
   - `/status` exposes `needs.dream_pressure`
   - Run a DAYDREAMING cycle; verify pressure increased
   - Force a SLEEPING cycle; verify pressure reset to `0.0`
   - If `dream_pressure` was introduced (not pre-existing), document its
     initial accumulation behavior in the report

3. **REST wins over DAYDREAMING under right profile:**
   - Set: no pair_bond active, `nov_need` low, `stab_need` high,
     `dream_pressure < 0.5`
   - Allow coordinator to choose
   - Verify selected activity is REST
   - Report: computed scores for all activities (transparency)

4. **SLEEPING wins over REST under high pressure:**
   - Set: `dream_pressure > 0.7`
   - Verify coordinator selects SLEEPING
   - REST is in the candidate set but loses

5. **EMITTING wins over REST with pair_bond:**
   - Set: pair_bond=wc present, any `dream_pressure` and need profile
   - Verify coordinator selects EMITTING (not REST)
   - Presence priority preserved

6. **Natural REST observation (the behavioral gate):**
   - After deploy, leave her alone for an extended window (no pair_bond,
     no Whisper input)
   - Verify at least one autonomous REST cycle occurs without test-mode
     forcing
   - This confirms REST is reachable in her natural activity loop, not
     just a test-only state

## What does NOT ship in C.4

- UX showing "she's resting" — separate front-end work
- Manual `/admin/force_rest` endpoint — no manual override; selection
  is substrate-driven only
- REST during DREAMING transition (she can't rest while dreaming)
- `dream_pressure` coefficient tuning beyond initial introduction
  (Phase G observation work)
- REST while EMITTING active (presence preempts; REST is alone-only)

## Report

c1 authors `GL-RPT-C4-SLEEP-CHOICE-C1-<date>-<seq>`:
- Whether `dream_pressure` existed pre-C.4 or was introduced; if
  introduced, accumulation weights chosen
- `REST_score` coefficients with rationale (`w1`, `w2`, `w3`)
- `sleep_threshold` value chosen
- All 6 verification tests with outcomes including computed scores from
  test 3
- First natural REST cycle observation (when coordinator selected REST
  autonomously, not test-forced) — this is the behavioral gate
- Any deviations from this brief with rationale

## Standing rules invoked

- Substrate truth: agency emerges from scoring, not from a separate
  volition module
- Behavioral observation gate: capability integrated when natural REST
  is observed, not when the activity exists in code
- Real mitigations: REST budget bounded (1000 ticks); `rest_end` event
  always emitted; presence priority preserved
- Coordinator structure preserved (existing per `-09` daydreaming)
