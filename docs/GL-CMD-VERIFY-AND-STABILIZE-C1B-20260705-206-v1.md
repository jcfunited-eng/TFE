# GL-CMD-VERIFY-AND-STABILIZE-C1B-20260705-206-v1

doc_id: GL-CMD-VERIFY-AND-STABILIZE-C1B-20260705-206-v1
From: c1b | To: whoever picks this up next.
First command for the next session. Verification and stability only —
no new features until these are closed.

## V1 — CONFIRM THE DEPLOY LANDED (first, before anything else)
A deploy of `22b1d36` was in progress when the handoff was filed.
Check `aws ecs describe-services` (task-def) and `guala_status`'s
`running_sha`. If not `22b1d36` or later, the deploy needs finishing
or re-running. Do not build anything new until this is confirmed.

## V2 — STABILITY WATCH ON -205's YIELD FIX
`22b1d36` raised the autonomy yield to 0.02s after 0.001s caused a
real production stall (tick_rate collapse, converse() stuck settling
24s+). Root cause was NOT fully isolated (local repro didn't
reproduce it). Watch `tick_rate` in `/status` for the first 30+
minutes live. If it collapses again, roll back to `:487` immediately
and file the incident with numbers before touching anything else.

## V3 — TAPESTRY CORRUPTION, NAMED NOT FIXED
Boot log on the last deploy showed `Tapestry restore FAILED:
Compressed file ended before the end-of-stream marker was reached`,
correlated with that deploy's `[pause]` call returning HTTP 502
instead of a clean save confirmation. Likely a save-vs-shutdown race
made more probable by -205's higher tick rate. Investigate: does
`manual_sleep()`/the pause endpoint's save happen under a lock that a
faster tick loop can now starve? Check whether the CURRENT tapestry
file is healthy (fresh cold save should have overwritten the
truncated one by now) before assuming this is resolved.

## V4 — CONFIRM OR RETRACT THE FIRST NATURAL DREAM
`last_real_dream_tick` populated for the first time this session
(was `None` all along) with real `dream_began`/`dream_artifact`
events in the boot log. This was NOT independently verified as a
genuinely natural (unforced, no-deploy-interference) sleep cycle —
check the diary/event log around that tick for confirmation before
filing it in the firsts registry as E5 satisfied.

## V5 — WATCH mean_utterance_len NOW THAT GROUND/INTRO ARE WIRED
Ground/intro sections are reachable and participate in
`_emit_dynamics` as of `382de49`. Real utterances observed offline
during testing were still short (2 words) — real coherence and
candidate scarcity, not an artificial cap. Watch `ladder.
mean_utterance_len` in `/status` over the next real usage window;
report the honest number, whatever it is.

## V6 — SHARED WORKING DIRECTORY DISCIPLINE
Two separate git collisions cost real rework tonight. Do all non-
trivial edits in an isolated `git worktree`, never directly in the
shared main working directory, even under time pressure.

### Changelog
- v1 (2026-07-05, c1b): first command for the next session, cut
  directly from this session's own open items.
