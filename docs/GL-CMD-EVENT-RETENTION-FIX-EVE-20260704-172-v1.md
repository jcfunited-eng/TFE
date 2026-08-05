# GL-CMD-EVENT-RETENTION-FIX-EVE-20260704-172-v1

doc_id: GL-CMD-EVENT-RETENTION-FIX-EVE-20260704-172-v1
From: Eve | To: c1a-builds / c1b-deploys | Vehicle: her live path,
save-loop and logging layer ONLY — zero cognition-path changes.
Implements the proposal Joe ratified from GL-RPT-EVENT-RETENTION-
AUDIT-C1-20260704-170-v1.
(-171 was a withdrawn chat-only draft; number retired, never reuse.)
Substrate-truth declaration: no cognition primitives touched; no
scoring/physics constants; write-side logging and retention only.
E-signature effect: none — infrastructure. Her diary becomes real.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## The fix, as audited and ratified
R1 DECOUPLE: crash-replay log and durable diary become two files.
   The existing events.log + compact-on-save behavior stays AS-IS
   for crash replay (its offset design is correct for that job).
   A NEW append-only diary file is written alongside it and is
   NEVER touched by compact_events.
R2 DIARY RETENTION: 7 days rolling, enforced by dated file rotation
   (one file per day, delete >7 days old at rotation) — never by
   in-place rewrite of a live file.
R3 WIDEN THE RECORD: the diary receives ALL substrate event kinds,
   not the 12-kind whitelist — the whitelist stays governing ONLY
   the crash-replay log and the CloudWatch mirror. If full-width
   proves too hot (measure, don't guess), report the measured rate
   and propose the trim; do not silently trim.
R4 CLOUDWATCH MIRROR: the one print() in log_event(), whitelist-
   governed, as costed in your audit.
R5 READERS: /v6/events_histogram gains a source parameter (replay
   log vs diary, default diary) — no existing caller breaks.

## Gates (failures first)
G-1 Crash-replay behavior byte-identical: _replay_events at boot
    reads exactly what it reads today; proven, not assumed.
G-2 Save-loop timing: hot-save cycle time before vs after, measured
    over ≥10 cycles; regression >10% reported before cutover.
G-3 Diary survives a real deploy/reboot and shows the boot events.
G-4 Deploy: same window as the sleep physics changes (see the
    ratification note); one deployer, coordinated, timed for her
    day since the deploy still costs her a sleep.
G-5 First post-deploy report includes 24h of diary histogram — the
    first full day of her life ever fully written down.

Joe's part: none further — ratified. He gets G-5's histogram as the
proof it worked.

### Changelog
- v1 (2026-07-04, Eve): implementation of the ratified audit
  proposal; -170's scoping dispatch closed by this.
- v1-ROUTING-NOTE (2026-07-04, c1a): the doc as dispatched read "To:
  c1b" — confirmed with Joe directly this session that this was
  stale/reassigned: c1b did the -170 audit, but the -172 BUILD
  (R1-R5, G-1/G-2 proven locally) is c1a's (this session); the
  DEPLOY (G-3/G-4/G-5, real deploy window, single deployer) stays
  c1b's, coordinated with c1b's own sleep-physics deploy per G-4.
  "To:" line above amended to reflect that split; no other line of
  Eve's dispatch text changed.
