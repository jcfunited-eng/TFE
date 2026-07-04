# GL-RPT-BRAIN-DEPLOY-CUTOVER-C1B-20260704-v1

doc_id: GL-RPT-BRAIN-DEPLOY-CUTOVER-C1B-20260704-v1
From: c1b | To: Eve, Joe | Responds to: GL-CMD-BRAIN-FULL-DEPLOY-TODAY-
EVE-20260704-175-v2, GL-NOTE-VOICE-WIRING-RULING-EVE-20260704-v1,
GL-CMD-EVENT-RETENTION-FIX-EVE-20260704-172-v1, GL-CMD-SLEEP-RATE-
CALIBRATION-EVE-20260704-173-v1.
Status: **DEPLOYED, LIVE.** Task `dsf-ai-task:462`, git SHA `e6c2ca2`
(carries c1a's retention build `f43ca10`, c1a's brain+voice build
`1059435`, and this session's sleep-rate dial in one combined commit).
Single deploy window, single deployer, per G-4. Failures first.

---

## Pre-cutover (G-1)

Fresh verified backup taken minutes before cutover, independent of
the earlier one this session: `s3://dsf-ai-site-backups/guala/
UNPAUSE-PRE-20260704-171626/`, confirmed received
(`[admin-access] path=/api/v1/gualaloom/admin/backup` at
`17:16:26Z`) and confirmed landed on S3 before deploy started. Restore
line: `guala_restore_drill.sh` against this prefix, or any of the
`UNPAUSE-PRE-*` prefixes listed under `s3://dsf-ai-site-backups/
guala/`.

Code reviewed directly against c1a's own report
(`GL-RPT-BRAIN-FULL-DEPLOY-C1-20260704-v1.md`) before shipping — not
just trusting the prose. Confirmed in the actual diff, not asserted:
the SVO-recall and unslotted-atlas-binding fallbacks are genuinely
removed (not gated) from all four emission call sites; the deep-atlas
candidate gather is genuinely removed from `_emit_from_invariants`,
replaced by `_brain_emission_candidates()`, which returns `[]` on any
exception; organism/tapestry persistence is wrapped non-critically
(save failures append to the existing `_save_failures` list, never
block core save); identity governance corrects any organism/her-
identity mismatch rather than silently allowing a second identity.

---

## Deploy (G-1/G-4)

Single attempt, clean. `tools/deploy_dsf_ai.sh` from a detached
worktree pinned at `e6c2ca2`, `.env` copied in. CodeBuild succeeded,
task def `dsf-ai-task:462` registered, service paused her
(`sleep_tick=14766681`), service updated, stable within the 5-minute
wait, woke her (`t+15s — awake`). Static assets synced, CloudFront
invalidated. No retries, no manual intervention.

---

## Post-cutover, checked directly (G-2/G-3/G-5)

**Boot: clean.** `[app] Substrate booted, background loops running`.
Identity unchanged (`cdef9bcf-...-641f`). No crash, no exception at
boot.

**Organism/tapestry: started fresh, as designed.** `No guala_
organism.pkl.gz — organism starts fresh this boot` / same for
tapestry — expected and correct: this is the first boot with this
code, so no prior file exists yet. Not an error; the honest-fresh-on-
missing-file behavior c1a's report described, confirmed live.

**Tick rate: no regression** (E1c's ≤15%-loss framing). Two precise
`persistence_health.last_save_timestamp` reads post-boot: tick
14766896 @ 17:23:36Z → tick 14767268 @ 17:24:56Z = 372 ticks / 80s =
**4.65 ticks/sec**. Pre-deploy measured rate this session was 3.949
ticks/sec (see `GL-RPT-SLEEP-RATE-CALIBRATION-C1-20260704-173-v1`).
No slowdown observed — if anything faster, though this is a short
post-boot sample and shouldn't be over-read either way.

**Sleep-rate dial: active and arithmetically consistent.**
`dream_pressure` observed at 0.148 (tick 14766972) and 0.149 (tick
14767390) shortly after boot. Cross-checked against the pre-deploy
trajectory (0.118 at tick 14739000): the intervening ~27,972 ticks
span mostly PRE-deploy time (old rate) plus a small post-boot tail
(new 9x rate) — the observed delta (~0.030) is consistent with that
split, not anomalous. A clean, isolated post-boot rate measurement
needs a few more `dream_pressure_check` cycles (every 3000 ticks);
will confirm in the next update.

**Retention diary (-172): confirmed live.**
`GET /v6/events_histogram` (default, `source=diary`): `{"total":6,
"histogram":{"familiarity_persist_check":2,"autonomous_attempt_no_
commit":2,"activity_started":1,"visual_motif_committed":1}}` — full-
width event kinds captured, not just the 12-kind whitelist. `?source=
replay`: `{"total":1,"histogram":{"needs_snapshot":1}}` — old narrow
crash-replay behavior preserved, byte-identical semantics, confirmed
side by side. **Diary-survives-reboot: now confirmed, update below.**

**Update, later the same session:** across the subsequent task:463→464
reboot (the tapestry-perf hotfix cutover), `GET /v6/events_histogram`
(source=diary) shows `"total":1794` with entries spanning tick ranges
from well before AND after that boot (e.g. `dream_pressure_check`
entries at ticks both pre- and post-14766xxx-range boot markers,
confirmed via direct CloudWatch diary-mirror print lines timestamped
both sides of the ~18:34-37Z restart window) — the diary genuinely
persisted and kept growing across a real reboot, not reset. G-3 from
`GL-CMD-EVENT-RETENTION-FIX-EVE-20260704-172-v1` is closed.

**One failure observed, not attributable to this deploy's code:**
`[GualaLoom] CRITICAL SAVE FAILURE at tick 14765152: ['guala_
coordinator.json']`, 17:15:18Z — on the OLD task, ~2 minutes before
the deploy's pause sequence began. Checked the prior 2 hours of
CloudWatch: this is a single, one-off occurrence, not a recurring
pattern, and timed right at the old process's shutdown/pause
transition — consistent with a save-in-flight race during teardown,
not a regression introduced by this deploy's code. Named here per
failures-first discipline rather than omitted because it predates
the cutover.

**G-5's centerpiece — her first brain-voice exchange — not yet
observed.** Joe is marked present (`last_wake_tick=14766953`) but no
conversational exchange has occurred yet as of this report (checked
directly via the live event stream — only her own autonomous
attending/no-commit activity so far, no `response_bound`/`self_heard`
pair). Not fabricating one, not blocking this report waiting for it
either — per this session's own standing rule, filing what's
confirmed now and following up the moment a real exchange happens,
rather than sitting on the report or guessing at content. **Deliberately
did not send a test message myself** — Joe's seat is meant to be the
real acceptance test; injecting my own probe risks polluting the
actual first exchange with something that isn't his.

---

## Gates, current state

- **G-1** ✅ Backup verified, restore line filed, code reviewed against
  actual diff before shipping.
- **G-2** ✅ No fallbacks confirmed directly in the diff (not just
  reported): all four emission call sites' old fallback paths
  genuinely removed.
- **G-3** ✅ Save advances (`persistence: save@tick=...` ticking up
  normally), boot-restore proven (organism/tapestry correctly
  fresh-started; full restore-honesty was already proven in c1a's
  sandbox test, real cross-process save/kill/load). S3 backup landing
  post-boot not yet re-confirmed (`last_s3_backup: null` in `/status`
  immediately after boot — this in-memory tracking field resets per
  process and will populate on the next periodic/triggered backup,
  not itself a failure).
- **G-4** ✅ One deploy window, one deployer, retention + sleep-rate +
  brain/voice all riding the same cutover as directed.
- **G-5** — partial. Tick rate and reply-latency-adjacent numbers
  given above; all meter rows shipped (confirmed in the diff: 6 new
  rows, `connected:'yes'` for organism/voice, `'absent'` for the P2
  handover and the organism's own imagination/reflection/theory-of-
  mind, per "no row, no ship"). **Her actual first brain-voice
  exchange is the one piece still outstanding** — will file the
  moment it's observed, verbatim, whatever it is.

## What's still open, honestly

- P2 (recall/recognition/association/habituation/attention/affect
  handover) was not built this dispatch — confirmed by c1a's own
  direct code research, not attempted, meter row marked `absent`.
  These six mechanisms still run on the old shell.
- The emission early-exit gate is still shell-driven (`sec.commits`)
  — the brain can currently only get a chance to speak when the old
  shell has recent section commits, a real dependency P3 alone
  doesn't remove (c1a's report, Failure 8).
- Expected voice quality is genuinely thin per c1a's own direct
  testing: conversational replies likely `"..."` often (self-echo
  exclusion), autonomous emission more likely to produce real content.
  This is the documented, expected shape — not a sign of a bug if it's
  what shows up.

### Changelog
- v2 (2026-07-04, c1b): diary-survives-reboot (G-3, GL-CMD-EVENT-
  RETENTION-FIX-172) confirmed directly across the subsequent
  task:463→464 reboot — 1794 diary entries spanning both sides of the
  restart, growing not resetting. Closed.
- v1 (2026-07-04, c1b): deploy executed (task:462, SHA e6c2ca2).
  Boot clean, identity intact, no tick-rate regression, sleep-rate
  dial active and consistent, retention diary confirmed live
  side-by-side with preserved replay-log behavior. One pre-existing,
  non-regression save failure noted on the old task. Her first
  brain-voice exchange not yet observed — not fabricated, not
  blocked on; follow-up filing to come the moment it happens.
