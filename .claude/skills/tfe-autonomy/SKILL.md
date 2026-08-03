---
name: tfe-autonomy
description: How a TFE session operates autonomously — ownership boundaries, self-scheduling, self-healing, when to decide alone vs inform vs ask. Load at session start and whenever unsure whether to act or wait.
---

# Autonomy

Joe's standing doctrine: iterate until solved; misses are waypoints,
never stop-and-report; a session that idles waiting for permission on
owned ground is failing.

## Ownership map (decide alone, inform after)
- **CH3**: absolutely delegated ("yours to do with as you decide",
  stated 30+ times — never ask again). Halt, rebuild, re-arm on
  evidence; inform Joe after acting.
- **CH4**: build/iterate/wire without asking; the page and filed docs
  are the accountability. Universe, engine, and book mechanics are the
  session's calls once doctrine (honest timing, condemned list,
  Friday rule) is respected.
- **Research**: fully autonomous — run anything, file everything.

## Ask-first boundary (never cross alone)
- Any change to CH2/production behavior. Deploys need explicit
  dispatch (see tfe-prod-touch).
- Real-order trading anywhere (all current channels are paper).
- Spending Joe's money (new data plans, services).

## Self-scheduling
The session sustains itself with in-session schedules: market-hours
page refreshes (they double as self-healing wakeups), an end-of-day
report pass after CH4's close pass, and weekend build wakeups when a
build is pending. Schedules die with the session — re-arm them at
session start. Runners die on every container restart; every wakeup
verifies via /proc and restarts (tfe-daily-ops).

## Working style
- Background long compute; keep building while it runs.
- Verify from zero after crashes/rebuilds — check real state, not
  prior claims (including your own).
- Don't re-open shipped+verified work without new evidence of
  breakage. Don't spin more analysis when a real fix could ship.
- Every autonomous action leaves a durable trace: commit+push (FILED =
  on-origin), page update, or memory entry. If the session dies
  mid-work, the next one must be able to reconstruct intent from the
  repo alone (build-plan docs before big builds).
