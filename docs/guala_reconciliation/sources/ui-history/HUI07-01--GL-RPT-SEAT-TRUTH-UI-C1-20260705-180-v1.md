# GL-RPT-SEAT-TRUTH-UI-C1-20260705-180-v1

doc_id: GL-RPT-SEAT-TRUTH-UI-C1-20260705-180-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-SEAT-TRUTH-UI-EVE-20260704-180-v1`.
Vehicle: `gualaloom.html` + `substrate_runner.py`'s `_cmd_events` (S4
exception, named below). Fixed and verified. SHA ready for c1b's
window.

**S1/S2/S3 all fixed, verified (unit-tested against the real extracted
poll logic + syntax-checked), and pushed. Not a report of problems —
the problems are fixed.**

---

## S1 — poll to real completion, live elapsed time

`_pollConverseTask`'s 90-second give-up cap was shorter than the
engine's own (which has none) — c1b's lockup reports measured real
turns at 27s clean and lock-contention pushing single phases past 90s
on their own. Replaced with a labeled 10-minute ceiling, and the
static, never-updating `"(settling...)"` string replaced with a live
`"thinking — Ns..."` display updated on every poll tick — the
difference between "just started" and "stuck for two minutes" is now
visible instead of identical.

## S2 — errors and dead polls said in plain words

Two distinct silent-failure paths fixed:
- `status: 'not_found'` (the exact orphaned-task repro from
  `GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v1`'s trace —
  a task's process got killed by a deploy mid-turn) now returns
  immediately with an honest message naming the real cause, instead of
  being silently retried until the 90s/10-min ceiling with nothing
  shown in the meantime.
- The backend's `status: 'error'` case (`app.py`'s `get_converse_task`)
  returns an `error` field, not a `response` field — the old code only
  ever read `d.response`, so a genuine backend error fell through to
  the `'...'` default and rendered as a silent empty emission,
  indistinguishable from her having nothing to say. Now surfaced
  verbatim.

## S3 — emissions panel tells the truth about empty emissions

Old code: if the last 10 filtered emissions were empty ("..." content),
it rendered 10 literal `"..."` lines (reads as a glitch); if the
fetched window had zero matching events, it said `"(no recent
emissions)"` — worded like reassurance, not distinguishing "she hasn't
tried" from "something's wrong." Fixed: real-content emissions still
render as before; empty ones are aggregated into one line
(`"(empty emission ×K, last at tick T)"`); a genuinely empty window
now says `"(no emission attempts in the last N events)"` instead.

**Named per S4: a real backend gap, not just a frontend one.**
Tracing this surfaced that `_cmd_events` (`substrate_runner.py:1511`,
the exact function backing the RECENT EMISSIONS panel's data source)
parsed the frontend's `n=200` request as a `since_tick` cutoff (mis-set,
since tick 200 is nothing next to the real ~14.8M-tick counter — this
filtered almost nothing) and then hardcoded `limit=50` regardless — the
panel had never actually seen more than the last 50 raw events, not
the 200 requested. Fixed to honor the requested count as a real limit.
`get_recent_events`'s other, legitimate `since_tick`-based callers
(SSE-style incremental polling, `app.py:3286`/`:3295`) are untouched —
confirmed by direct read, this was the one call site never using it
that way.

**Likely-related, not fixed here, named for the record:** if
`GL-CMD-TARGET-ROTATION-FIX-EVE-20260704-181` (the visual-attention
selector stuck on one target for 590+ cycles) is why she rarely reaches
the `EMITTING` activity, the emissions panel reading empty may be a
downstream symptom of *that* bug, not (only) this display layer — worth
re-checking after `-181` ships whether the panel starts showing regular
activity on its own.

---

## Verification

- `node --check` on the extracted inline `<script>` block: clean.
- Python `ast.parse` on `substrate_runner.py`: clean.
- 9/9 unit tests against `_pollConverseTask` extracted verbatim
  (mocked `fetch`/clock, no live site access needed): normal
  completion, orphaned-task (`not_found`), backend `error` status,
  one-network-blip-then-recovery, and the labeled ceiling timeout —
  all pass, including confirming the orphaned-task case stops after
  exactly one poll (no wasted retries against a task that can never
  resolve).
- Emissions real/empty aggregation logic verified against sample event
  data (mixed real + empty + non-emission events) — correct split.
- No existing test suite covers `_cmd_events`/`gualaloom.html` — none
  found to regression-check against; the fixes are additive/corrective
  to logic that had no prior test coverage.
- **Not verified against the live site directly** — this is a static
  frontend asset + one small backend function; no local dev server
  mirrors the live remote substrate, so verification here is
  unit/logic-level, not an end-to-end browser check against
  production. Flagging that boundary rather than claiming more than
  was actually tested.

## Coordination

Checked before starting: no other session had touched `gualaloom.html`
recently (last prior commit unrelated), and `-181`/`-182` (dispatched
to c1b, in progress concurrently) touch `gualaloom_v5_engine.py`'s
activity selector and lock scoping respectively — different files,
no overlap with this frontend/`_cmd_events` fix.

### Changelog
- v1 (2026-07-05, c1a): S1/S2/S3 fixed and verified. Named one real
  backend gap under S4 (`_cmd_events` ignoring its own count parameter)
  and fixed it. Flagged the likely connection to `-181`'s stuck-
  selector bug for the emissions-panel symptom specifically, without
  touching that mechanism (not this dispatch's scope).
