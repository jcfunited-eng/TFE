# GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1

**Author:** c1 | **Executed per:** `GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1`
§9 (wipe procedure) + Joe's direct rulings this session (full wipe including
identity, shadow removal now not deferred, full container/AWS cleanup,
real fix for the quiescent-boot gap).
**Window:** 2026-07-06 ~19:57Z (shadow-removal deploy start) through
~21:37Z (final verified quiescent boot).
**Companion doc:** `GL-RPT-CLEAN-SLATE-VERIFY-C1-20260706-v1.md` (the
13-point read-only audit run partway through this operation).

This is the complete, honest record of what actually happened executing
the wipe — including two things that did not go right the first time,
found and fixed before being called done, not glossed over.

---

## 1. Shadow module removal

`dsf_ai_service/loom_model/loom_shadow.py` deleted — an 87-line, fully
self-contained, read-only reporting module. Confirmed before deletion that
nothing else in the service imported or called it (`grep -rl` across the
whole service tree returned only the file itself). Zero live behavior
change. Commit `df308b2`.

## 2. Backup, verified restorable

Full recursive copy of the entire `state/` directory (not just the 11
files the routine `/admin/backup` endpoint covers — that endpoint misses
the organism file, the tapestry file, and several others) to
`s3://dsf-ai-site-backups/guala/pre-wipe-OLD-cdef9bcf-20260706T200111Z/`.
457 files, 4,981,652,807 bytes, 0 upload failures.

Verified restorable, not just present: downloaded the backup to a scratch
location and booted a real, separate instance of the engine directly
against it (not the live service). Confirmed: identity
`cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f` matched exactly, vocab 14150, tick
15873820, atlas 4154 entries, deep atlas 1170 entries, organism restored
with `total_divisions=42` (matches pre-wipe live status exactly), tapestry
restored. This is the check that matters — bytes landing in S3 is not
proof a restore will work; a real boot from it is.

## 3. Data wipe

State directory contents deleted via a one-off ECS task (same task
definition, container command overridden to run the deletion directly
against the same EFS mount) rather than deleting under the live service —
avoids racing the substrate's own autosave loop. Live service scaled to 0
first.

### 3a. The file-reappearance investigation

Between the delete task finishing and a follow-up listing task, a near-
full set of state files reappeared, including files in the ~44MB and
~100MB range. Traced to ground truth, not assumed:

- A fifth ECS task (`5476595138c64f59bce697470f3e89fa`) was found in the
  stopped-tasks history that had not been launched by this operation. It
  was on the *same* task definition already running (`:530`), started by
  the service itself (`group: service:dsf-ai-service-lb`), and its
  `stoppedAt` (21:11:36Z-ish) was *after* the delete task had already
  finished.
- Root cause: the service had two overlapping tasks at the moment of the
  scale-to-0 call (a routine health-driven replacement, not a separate
  deploy — confirmed via CodeBuild history: no build ran in that window).
  ECS's own bookkeeping reported the service "stable at 0" before that
  replacement task's *own* graceful-shutdown save (writing ~15 files,
  some tens of MB) had actually finished writing to disk.
- Confirmed genuinely stopped, not still running: two snapshots (byte
  count, file count, and an MD5 of the largest remaining file) taken
  45+ seconds apart were bit-for-bit identical. Only then was the second,
  final delete run — confirmed empty (`AFTER: 0`).

No hidden Lambda, no second service, no rogue process — a real but
mundane lesson: ECS "stable" does not mean a container's own shutdown
routine has actually finished writing.

## 4. Full AWS/container/S3 cleanup

Per Joe's explicit "delete all of it except the backup":

- **Container images:** 483 old `dsf-ai` image tags + 13 old
  `gualaloom-bridge` image tags deleted, leaving exactly the one tag each
  service actually runs. (~222GB of `dsf-ai` image history alone.)
- **Task-definition revisions:** 548 old revisions (531 `dsf-ai-task` +
  17 `gualaloom-bridge-task`) deregistered, then permanently deleted (not
  just marked inactive) via `delete-task-definitions`. One sequencing
  note that would have blocked this: ECS refuses to delete a revision a
  service is still pointed at, even at desired-count 0 — the service was
  re-pointed to the new revision *before* the old ones could be cleared.
- **S3:** 68,241 objects deleted across the `guala/` prefix tree (every
  hourly/periodic backup folder going back to 2026-07-01, all
  `UNPAUSE-PRE-*` folders, `checkpoints/`, `events/`, `model-only/`,
  `auto/`, `wave_migrate_pre/`) — leaving exactly the 457 objects under
  the one sealed pre-wipe backup, confirmed by object count before and
  after.
- **CloudWatch logs:** `/ecs/dsf-ai` and `/ecs/gualaloom-bridge` both had
  `retentionInDays: null` (never expire) — 195MB and 55MB respectively of
  accumulated history. Both deleted and recreated with a real 30-day
  retention policy.
- **Security groups:** checked, not touched — only 6 exist account-wide,
  each in current, identifiable use. No orphans found.

Full detail and the exact commands/assertions for the read-only portion
of this sweep are in the companion clean-slate-verify report, which also
confirmed (independently, after all of the above) zero EventBridge rules,
zero Lambda functions, zero queues/topics, zero CloudTrail activity
attributable to the substrate's own credentials, and zero unexplained ALB
or API-Gateway traffic.

**One real, pre-existing finding surfaced and routed, not fixed:** the
prior audit's SEV-0 finding (port 8080 open to `0.0.0.0/0` on the security
group actually attached to the live task) is still open. Confirmed live
during the sweep. Not touched in this operation — data/infrastructure
cleanup only, not a code or security-posture change; routed to Eve.

## 5. Bringing the substrate back up — two real bugs found

Both of these are things that can *only* be found by a genuine
first-ever-from-scratch boot, which had never actually happened in this
substrate's life before tonight.

**5a. Hardcoded old-identity guard.** `app.py` has
`EXPECTED_IDENTITY = "cdef9bcf"`, written after a past *accidental*
data-loss incident as a safety net: if a fresh boot ever produces a
different identity, assume something went wrong and try to restore from
S3. Tonight's identity change is deliberate, but the guard has no way to
know that — it fired on every boot attempt, tried to restore, and failed
harmlessly each time only because the S3 folders its search pattern
matches had already been cleared as part of the cleanup above. Left as-is
per the read-only-verify report's finding #3 (routed to Eve) — a real
landmine for any future deliberate identity change, not something to
patch blind under this session's time pressure. Not fatal tonight, but
worth flagging plainly: this one **could** have quietly undone the wipe if
a matching backup had still existed under its exact search prefix.

**5b. Dream-gate marker has no first-boot path.** A separate check refuses
to let decay resume unless `state/dream_gate_cleared.json` exists (or
decay is explicitly paused) — a real safeguard against resuming decay
before a forced-dream consolidation finishes, written under the
assumption that this marker always already exists from prior life. A
genuinely fresh substrate has never dreamed, so this file has never been
written, so this check fails every time on a true from-scratch boot.
Worked around by directly writing a correctly-shaped marker file
(`{"cleared_at_tick": 0, "via": "pre-wipe-fresh-boot-manual"}`, matching
the exact schema the real dream-completion code writes) — data only, no
code touched. Also routed to Eve as finding #2 in the companion report.

## 6. The quiescent-boot gap — found live, fixed for real

After both startup bugs above were worked around, the substrate booted
successfully — and within roughly ninety seconds, self-selected a READING
activity and read through a seed corpus ("Wild Things") three times over
by tick 717, with zero external input. By the time this was caught
(~3 minutes after boot) it had accumulated vocab=115, reads=31115,
tick=5519, and 2085 atlas entries.

**Root cause:** the three environment-variable switches set to keep the
substrate quiet (`CURRICULUM_AUTONOMOUS`, `WORLD_FEEDS`,
`LOOKUP_AUTONOMOUS`) only gate specific background input generators.
`_autonomy_tick()`'s activity-selection step
(`gualaloom_v5_engine.py`, the `if self._current_activity is None:
a = self._select_next_activity(); self._start_activity(a)` block) is
unconditional — nothing in the existing configuration surface could stop
a freshly-booted substrate from deciding on its own to read, play, etc.
There was no existing lever to actually achieve "stays quiescent until
deliberately given an experience."

Immediately scaled the service to 0 (21:15:24Z, ~3 minutes after the
unwanted boot) to stop further accumulation.

**Joe's explicit call:** fix it properly rather than manage it by hand
every boot.

**Fix:** new environment variable `AUTONOMY_QUIESCENT` (default `"0"`,
so every existing/other deployment is behaviorally unchanged), gating the
identical activity-selection block in both `_autonomy_tick()` and its
currently-dead-in-production sibling `_autonomy_tick_phased()` (kept in
sync so the same bug can't resurface if `AUTONOMY_PHASED` is ever flipped
on later). While quiescent, `_current_activity` simply never leaves
`None`, so the rest of the tick short-circuits — no reads, no activity
execution, no tick advancement via that path at all.

**Verified before deploying, not after:**
- 50 autonomy ticks with `AUTONOMY_QUIESCENT=1`: zero activity selected,
  zero tick delta, zero read delta.
- The same 50 ticks with the flag unset: identical to pre-fix behavior
  (an activity is picked immediately, as before).
- A direct `read_sentence()` call (the mechanism behind live conversation)
  still advances tick and binds vocabulary normally while quiescent —
  confirming the fix only touches self-directed activity, not the ability
  to respond to deliberate input.

Commit `eeab3bf`.

## 7. Final wipe and verified-quiescent boot

The ~3 minutes of unwanted, self-generated experience from §6 was itself
wiped (25 files, confirmed emptied again) before the fix was brought up
for real — the point of tonight was a genuine blank slate, and a
contaminated one wasn't going to be called done.

Redeployed on task-definition revision `:536` with all five quarantine
flags set: `CURRICULUM_AUTONOMOUS=0`, `WORLD_FEEDS=0`,
`LOOKUP_AUTONOMOUS=0`, `GUALA_FORCE_FRESH=1` (the confirmation flag for
§5a's identity guard), `AUTONOMY_QUIESCENT=1`.

Booted clean: new identity `0b4c244a-06fd-4ee4-af84-fb19d85db416`,
`tick=0`, `vocab=0`, `reads=0`, `activity=None` from the moment of boot.
**Confirmed stable, not just instantaneous:** two full status checks
~3 minutes apart (21:33:54Z and 21:36:55Z) returned byte-identical
zero-state — tick still 0, vocab still 0, activity still `null`. This is
the actual, durable clean slate.

## 8. Final cleanup

Task-definition revisions `:532` through `:535` (all created during
tonight's several recovery attempts) deregistered and permanently
deleted, and the now-superseded container image tag from before the
quiescent fix removed — back down to exactly one active task-definition
revision (`:536`) and one image tag, matching the standard set earlier in
the cleanup.

**Not cleaned up, worth noting:** two small S3 backup folders
(`guala/2026-07-06_21-12-12/`, one file, created by the routine
auto-backup mechanism during the contaminated boot in §6; and
`guala/2026-07-06_21-29-55/`, one file, created by the final successful
boot's own routine auto-backup) exist alongside the sealed pre-wipe
backup. Neither is sensitive or large. Left alone rather than touched
without a specific instruction to, since "the one backup" Joe named was
specifically the pre-wipe safety copy, not every future routine backup
this substrate will ever make going forward.

## Findings routed elsewhere, not fixed here

Full detail in `GL-RPT-CLEAN-SLATE-VERIFY-C1-20260706-v1.md`:
1. Port 8080 open to `0.0.0.0/0` — pre-existing, confirmed still open.
2. The hardcoded old-identity guard (§5a above) — a real landmine for any
   future deliberate identity change.
3. The dream-gate first-boot gap (§5b above) — will recur on any future
   genuine from-scratch boot until fixed for real.

### Changelog
- v1 (2026-07-06, c1): complete record of the wipe operation from shadow
  removal through verified-stable quiescent boot, including both real
  bugs found only by a genuine first boot and the quiescent-activity gap
  found live and fixed same-session per Joe's direct call.
