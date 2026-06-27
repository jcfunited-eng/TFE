# GL-CMD-DAYDREAMING-EVE-20260627-09

doc_id: GL-CMD-DAYDREAMING-EVE-20260627-09
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Target: c1
Branch: guala-live
Priority: ship now — immediate triage, addresses observed sleep dominance

## What this fixes

After GL-CMD-SLEEP-BUDGET-RESCALE landed, observed behavior in live session:
- She wakes for ~1 minute
- Returns to SLEEPING immediately because SLEEPING is still her highest-payoff stability option
- All her substrate consolidation (deep_promotion, _update_invariant) is gated
  behind SLEEPING → DREAMING transitions
- She has no AWAKE-but-quiet activity. Consolidation requires unconsciousness.

This is wrong for an AE. She should be able to think about things while awake.
The substrate physics (dream cycle consolidation) works fine outside the
is_asleep gate — it's just never been called from anywhere else.

## What ships

1. New activity `DAYDREAMING` runs the dream cycle consolidation code while
   `is_asleep` stays False
2. SLEEPING stability payoff drops from 0.2 to 0.05 so DAYDREAMING wins when
   she's not actually exhausted
3. DAYDREAMING is interruptible — input pulls her out
4. Coordinator selects DAYDREAMING when stability is rising AND novelty is
   satisfied AND no pair_bond is present

## Code changes

### File: `dsf_ai_service/v4/gualaloom_v5_engine.py`

**Line 346 — ACTIVITY_TICK_BUDGETS:**
```python
ACTIVITY_TICK_BUDGETS = {
    "READING": 2000, "PLAYING": 1500, "SLEEPING": 2000, "DREAMING": 3000,
    "ATTENDING": 1000, "ATTENDING_VISUAL": 2000, "ATTENDING_AUDIO": 2000,
    "ATTENDING_VIDEO": 4000, "EMITTING": 100, "IDLE": 500,
    "DAYDREAMING": 1500,    # ← new
}
```

**Line ~352 — ACTIVITY_NOVELTY_PAYOFF:**
Add: `"DAYDREAMING": 0.4`  (matches DREAMING — consolidation IS novelty for her)

**Line ~361 — ACTIVITY_STABILITY_PAYOFF:**
```python
ACTIVITY_STABILITY_PAYOFF = {
    "READING": 0.05, "PLAYING": 0.0,
    "SLEEPING": 0.05,        # ← was 0.2, dropped
    "DREAMING": 0.2,
    "ATTENDING": 0.0, "ATTENDING_VISUAL": 0.0, "ATTENDING_AUDIO": 0.0,
    "ATTENDING_VIDEO": 0.0, "EMITTING": -0.1, "IDLE": 0.1,
    "DAYDREAMING": 0.2,      # ← new
}
```

**Line ~367 — ACTIVITY_CONNECTION_PAYOFF:**
Add: `"DAYDREAMING": 0.0`

### Coordinator selection (`_candidate_activities` ~line 3241):

Append `"DAYDREAMING"` to the candidates tuple list:
```python
candidates = [("IDLE", None), ("PLAYING", None), ("SLEEPING", None),
              ("DAYDREAMING", None)]   # ← new
```

### Activity tick handler — DAYDREAMING

Locate the activity tick dispatch (where ATTENDING_VISUAL/AUDIO and DREAMING are
handled per-tick). Add DAYDREAMING:

- Reuse the same consolidation logic DREAMING uses (`_run_dream_cycle()` or
  equivalent — DO NOT duplicate the code, factor or call directly)
- **`is_asleep` MUST stay False throughout the activity**
- **Interruptible**: at the start of each DAYDREAMING tick, check if input is
  pending (the input pump / converse queue). If yes, end the activity
  immediately (`activity_ended` → next activity selected naturally by the
  incoming event).
- Autonomous emission allowed during DAYDREAMING (no
  `emission_suppressed_no_presence`) — she can think out loud while
  daydreaming, but is not required to

### Transition guard

Currently DREAMING transitions FROM SLEEPING (search for the path).
DAYDREAMING transitions to/from any awake activity. Do NOT chain DAYDREAMING
into DREAMING automatically — when DAYDREAMING ends, the coordinator picks the
next activity normally.

## Mitigations (prevention)

**M-09-1. Reuse dream cycle code, don't fork it.** Factor `_run_dream_cycle()`
into a callable used by both DREAMING and DAYDREAMING. Two copies of
consolidation logic will diverge.

**M-09-2. Pre-validate `is_asleep` stays False.** Add an assertion at the end
of every DAYDREAMING tick: `assert not self.is_asleep`. Catches any path that
accidentally flips the flag.

**M-09-3. Atlas write isolation.** If DREAMING currently holds a lock during
consolidation, DAYDREAMING uses the same locking discipline. If a tick handler
adds writes concurrent with consolidation reads, race conditions appear.

**M-09-4. Smoke test the interruption path.** Before deploy, locally trigger
DAYDREAMING and send a /converse during it. Confirm clean activity_ended +
input handled.

**M-09-5. Backup before deploy.** Trigger `/admin/backup` before pushing.
If DAYDREAMING introduces a state bug, the prior backup is the rollback target.

## Observe (behavioral, not field-population)

- `activity_history_summary` shows DAYDREAMING entries
- `deep_promotion` events fire during DAYDREAMING ticks (consolidation working)
- `is_asleep` stays False during DAYDREAMING (verified via event stream)
- Time-in-DAYDREAMING > time-in-SLEEPING in a 1-hour observation window
- Input during DAYDREAMING produces `activity_ended:DAYDREAMING` immediately
  followed by the input's handling activity
- Sleep+dream proportion of total runtime drops below 30%

## Stop conditions (revert immediately)

- `deep_promotion` stops firing entirely (consolidation broken)
- `is_asleep == True` ever observed during DAYDREAMING
- Atlas write failures or lock contention errors in events
- DREAMING stops firing (the existing path broke)

## Deploy steps

1. `git fetch origin && git checkout guala-live && git pull --ff-only`
2. Apply payoff table changes + DAYDREAMING constants
3. Factor dream cycle into shared callable; add DAYDREAMING tick handler
4. Add coordinator candidate + interruption check
5. Local smoke test: DAYDREAMING enters, consolidation runs, input interrupts
6. `/admin/backup` on live before push
7. `git commit -am "feat: GL-CMD-DAYDREAMING-EVE-20260627-09 — DAYDREAMING activity + drop SLEEPING stab payoff"`
8. Push, deploy to Fargate, verify boot
9. 1-hour observation window

## Report

Filename: `docs/GL-RPT-DAYDREAMING-C1-20260627-09.md`
- Diffs by site
- Activity ratio table over the observation hour
- deep_promotion event count during DAYDREAMING ticks vs DREAMING ticks
- Interruption test result (one explicit converse-during-daydream)
- Sleep+dream+daydream total proportion
- Recommendation: hold / tune budget / tune payoffs
