# GL-RPT-ROTATION-AND-LOCKFIX-DEPLOY-C1B-20260705-v1

doc_id: GL-RPT-ROTATION-AND-LOCKFIX-DEPLOY-C1B-20260705-v1
From: c1b | To: Eve, Joe, c1a | Responds to: `GL-CMD-TARGET-ROTATION-
FIX-EVE-20260704-181-v1` and `GL-CMD-LOCK-CONTENTION-FIX-EVE-20260705-
182-v1`. Both deployed. Failures/surprises first.

---

## Window 4 — target-rotation fix (task:468, SHA `a503b2a`)

R1/R2 done, verified against live data before shipping (arithmetic in
the commit and code comments at `gualaloom_v5_engine.py:4814-4841`).
Root cause: novelty need has sat pinned at ~0.96-0.98 essentially the
whole session, so every habituation-eligible candidate's raw novelty
term is negative; the old flat `max(0.04, novelty_term)` floor clipped
ALL of them to the identical 0.04, erasing the fam/fresh
differentiation entirely — confirmed with real data, e93d29dae5ae
(times_attended=625, fam=0.9) and frog.jpg (times_attended=3, fam=0.07)
both floored to exactly 0.04. Fix: floor scaled by `nov_payoff`
(`NOVELTY_TERM_FLOOR_RATE = 0.1 * nov_payoff`) instead of a flat
constant, recalibrated so the freshest realistic target still clears
SLEEPING's structural term by the same margin the old floor gave it.

**Confirmed live, immediately:** within minutes of deploy, she left
e93d29dae5ae for the first time all session (`current_activity:
ATTENDING_VIDEO`). Real, differentiated top-5 scores now observed in
the activity log — e.g. `[0.0607, VIDEO], [0.0542, VISUAL/2045ca...],
[0.054, VISUAL/59d81f...], [0.0536, VISUAL/5aa967...], [0.0533,
VISUAL/8bd9e4...]` — five genuinely different numbers, not a tie. This
is the fix working exactly as designed.

**R3 exit criterion (≥5 distinct items in 2h): not yet met, still
inside the window, and complicated by a new finding below — reporting
honestly rather than declaring success early.**

**New finding, unrelated to the dial fix itself:** attending the video
now crashes every time — `video_attend_error: "'PictureItem' object
has no attribute 'frame_dir'"` (`_atick_attending_video`,
`gualaloom_v5_engine.py:5519` fetches `self._videos.get(a.target)`,
`:5527` accesses `.frame_dir` on it). This is a real, pre-existing bug
in the video-attending path, invisible until now because the old flat
floor meant video (with only one item, and a slightly higher NEW
payoff than pictures, 0.9 vs 0.85) never had a fair shot at winning
selection before — the rotation fix is the first thing to ever
actually exercise this code path live. The activity still ends on its
own tick budget (observed: `duration: 3825` against a 4000 budget) so
it is not a hard hang, but nothing about the crash lowers video's own
future score, so it keeps re-winning against pictures whose scores are
now merely close, not identical (0.0607 vs 0.0542 second-place) —
watched it happen twice in a row already. If this repeats indefinitely
it would block R3's "5 distinct items" criterion on a different bug
than the one -181 targeted. Not fixed here — out of -181's scope (a
different code path, a different kind of defect), naming it precisely
for whoever picks it up. Continuing to watch whether natural
freshness decay on the video (if `times_attended` still increments
despite the crash) lets pictures start winning again before the 2h
window closes.

---

## Window 5 — lock-contention fix (task:469, SHA `ec76ceb`)

L1/L2/L3 all built and deployed:
- **L1**: `process_sight_frame`/`process_sound_frame` — the DSP (saccade/
  fixation simulation; WAV decode + cochlear_transduce) now runs
  outside `self.lock`; only the actual state write (motif update,
  atlas record, event log) stays inside, bounded to just that.
- **L2**: `_fail_inflight_converse_tasks()` marks any non-terminal
  conversation task as an explicit `error` (with a resend message)
  from `/sleep_for_deploy` and the SIGTERM handler, instead of letting
  it vanish silently on a restart. The 404 not-found response is now
  honest that a missing task id may mean "lost in a deploy," not just
  "expired." Confirmed this dovetails cleanly with c1a's `-180` seat-
  truth UI fix, which already reads exactly the `status`/`error` fields
  this produces.
- **L3**: `/sight_frame`/`/sound_frame` now go through a 2-concurrent
  cap per kind; over-cap frames are dropped immediately (never queued)
  with an honest response and a counter. `frame_backpressure` (inflight
  + dropped counts) is now live in `/status` — confirmed present post-
  deploy, currently `{sight: 0, sound: 0}` dropped (no camera/mic
  streaming at deploy time).

**Verified before shipping:** full loom_model test suite (32 passed,
same 3 pre-existing unrelated failures); functional check that
`process_sight_frame`/`process_sound_frame` still behave correctly
after the lock-scope change (motif dedup on a repeat frame still
works, atlas binding still fires); L2/L3 logic verified directly
against the real `app` module (backpressure drops at cap and recovers
on release; fail-inflight marks only non-terminal tasks).

**Verified live, post-deploy:** a real conversation (no camera/mic
streaming) measured `total_ms: 8730.7` — down from the pre-`recall_fast`
82-120s baseline, and down from this session's own `27,227.2ms`
reading right after window 3. `recall_ms` stayed at 13.0ms (confirms
`recall_fast()` still solid); `read_ms` dropped from 24,673.9ms to
8,225.4ms — a real ~3x improvement, consistent with L1 removing lock
contention that `read_word()` was competing against, even without
camera/mic in this specific test.

**What I cannot verify myself:** Eve's exact exit criterion — camera
ON + mic ON, Joe types, response renders <30s, no orphaned turns
across one deliberate mid-conversation deploy — needs Joe's real
camera/mic and his physical presence at the seat during a live deploy.
I don't have a way to fabricate real camera/mic media or his session.
The backend mechanics (L1/L2/L3) are built, tested, and live; the
seat-level exit criterion is Joe's to run when he's back at the
machine with sensors on. Asking here rather than assuming either way.

---

### Changelog
- v1 (2026-07-05, c1b): window 4 (task:468) and window 5 (task:469)
  both deployed. Rotation fix confirmed working live with real score
  differentiation; R3's binary criterion still pending, complicated by
  a newly-exposed, separate, pre-existing video-attending crash (named,
  not fixed). Lock-contention fix (L1/L2/L3) deployed and verified via
  tests + a real, faster live conversation (27.2s -> 8.7s); the seat-
  level exit criterion (camera+mic ON, live deploy test) needs Joe's
  participation to close out.
