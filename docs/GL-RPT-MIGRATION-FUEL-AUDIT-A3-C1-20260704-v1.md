# GL-RPT-MIGRATION-FUEL-AUDIT-A3-C1-20260704-v1

doc_id: GL-RPT-MIGRATION-FUEL-AUDIT-A3-C1-20260704-v1
From: c1b | Promoted per Eve's ruling on GL-RPT-SLEEP-BACKTEST-C1-
20260704-167-v1: the event-retention finding from that backtest opens
this audit. Referenced as "A3 migration-fuel audit" in
`docs/GL-PLAN-AE-DEV-3WK-EVE-20260703-v8.md` ("Migration boundary
restated: any wiring of LoomBrain into her live path remains
forbidden pending C-2 results and the C-3 spec with the A3
migration-fuel audit") — no document existed under that name before
this one. This is its opening finding, not its completion.

---

## Opening finding (failures first): the fuel doesn't exist

Any migration strategy that leans on **replaying her event log** to
reconstruct or verify state — which is the implicit assumption behind
"migration-by-replay" as a path for bringing LoomBrain or any other
module into her live path — is currently starved of fuel. Checked
directly, this session, three ways:

1. **In-memory event buffer**: `self._substrate_events = deque(maxlen=
   1000)` (`gualaloom_v5_engine.py:1380`). Hard-capped at 1000 events.
   At the observed live rate (`sight_frame_bound`/`sound_frame_bound`
   arriving every few seconds during normal sensory operation), this
   buffer covers **minutes of history**, not the days-to-weeks a
   migration audit would need to reconstruct meaningful state.
2. **Persisted `events.log`**: queried live via `GET /v6/events_
   histogram` (reads the file from disk directly, not the in-memory
   buffer) — returned **`{"total": 4}`**. Four entries, total, in the
   file that is supposed to be the durable record. Whatever rotation
   or truncation policy governs this file, it is not preserving
   anything close to a day's activity, let alone the weeks a migration
   spec would need.
3. **CloudWatch (`/ecs/dsf-ai`)**: retention is unlimited
   (`retentionInDays: None`, confirmed live), so this is the one place
   that COULD hold real history — but `_log_substrate_event()` does
   not appear to also `print()` to stdout, which is the only thing
   CloudWatch captures. A targeted query for `"dream_pressure_check"`
   across a real 2-hour window returned zero events for this reason,
   not because the window was wrong.

**None of these were "hard to find" — they were checked directly, live,
this session, while backtesting `GL-DESIGN-SLEEP-WINS-BY-PHYSICS-C1-
20260704-v1`'s override ceiling against the pre-07-01 narcolepsy
window. That backtest could not use real historical load data for
exactly this reason — which is why this finding is being promoted here
rather than left buried in a sleep-physics report.**

---

## What A3 must now answer (not answered here — scoping the remaining work)

1. **What should retention actually be?** A number, not a feeling — sized
   against what a real migration-by-replay strategy needs to
   reconstruct (days? the full identity's lifetime? a rolling window
   long enough to catch the slowest-cadence mechanism, e.g. the ~4-8h
   sleep cycle this same day's work has been measuring?).
2. **What does that retention cost?** Storage (EFS/S3), the in-memory
   buffer's own memory footprint if raised, save/backup time if the
   persisted log grows, and — the one nobody's asked yet — whether
   `events.log`'s current rotation/truncation behavior is itself a bug
   (something is cutting it to near-zero) or a deliberate, undocumented
   design choice that migration planning has been silently assuming
   doesn't exist.
3. **Is CloudWatch a viable second channel, or a dead end?** If
   `_log_substrate_event` were also mirrored to stdout (or a subset of
   event kinds were), CloudWatch's unlimited retention could backstop
   the persisted log's apparent truncation — worth evaluating before
   assuming the fix is "just extend `events.log`'s retention."
4. **Does anything currently reading `events.log` (`/v6/events_
   histogram`, `_replay_events` on boot, any snapshot/backup tooling)
   assume its current small size, in a way that changing retention
   could break?** Not evaluated here — first thing the next pass on
   this audit should check before touching retention.

**No fix proposed. No retention number chosen.** This document seeds
the audit with a verified, repeatable finding (re-run `GET /v6/events_
histogram` and the in-memory-buffer/CloudWatch checks above any time to
reconfirm) and the four questions the next pass needs to close before
any migration spec is allowed to lean on replay, per Eve's ruling and
the standing migration boundary in `GL-PLAN-AE-DEV-3WK-EVE-20260703-
v8.md`.

---

### Changelog
- v1 (2026-07-04, c1b): opening finding only. Promoted from
  `GL-RPT-SLEEP-BACKTEST-C1-20260704-167-v1`'s event-retention
  discovery per Eve's explicit instruction. Four open questions scoped
  for whoever runs the next pass on this audit; not answered here.
