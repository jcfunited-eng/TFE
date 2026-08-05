# GL-RPT-ATTEND-GROOVE-PREDEPLOY-C1-20260703-107-v1

doc_id: GL-RPT-ATTEND-GROOVE-PREDEPLOY-C1-20260703-107-v1
From: c1a | To: Eve
Re: GL-CMD-ATTEND-GROOVE-EVE-20260703-107-v2, Part A items A.1/A.2/A.5
   (the three items Eve's hold-point ruling said to run now, no deploy).
Status: INTERIM. A.3 and A.4 remain outstanding (deploy-gated per Eve's
   ruling — c1b owns deploy mechanics, consolidated with d45e877). No
   verdict is rendered here; the CMD requires all five items in hand
   first. This document is filed complete for what it covers.

---

## Failures / gaps first

- A.1 could not produce a `target_familiarity_update` count for
  e93d29dae5ae. Not a soft miss — it is structurally unmeasurable from
  every source I have access to (detail below). NOT MEASURED.
- A.4 (needs.signed_distance() dict) and A.3 (≥3 consecutive
  ATTENDING_VISUAL selections with top_scores) are NOT YET CAPTURED —
  both require the Part A instrumentation (d45e877) to be live, and it
  is not deployed yet. Blocked on the consolidated deploy Eve called for.
- Unplanned, out-of-band: the production task restarted mid-investigation
  (health-check failure), independent of anything in this CMD. Detailed
  below — flagging because it changes what "currently live" means and
  because target_familiarity apparently did not survive the restart.

---

## A.1 — target_familiarity_update event count for e93d29dae5ae, full boot

**NOT MEASURED — structurally, not just inconveniently.**

Two independent access paths, both checked:

1. **Disk-persisted log** (`STATE_DIR/events.log`, what `GET /v6/events_histogram`
   on the live ALB reads):
   ```
   $ curl -sS http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com/v6/events_histogram
   {"total":0,"histogram":{}}
   ```
   Zero events of any kind, right now. But even independent of that: reading
   `_log_substrate_event` (gualaloom_v5_engine.py:3803-3821), only these
   kinds are ever written to disk —
   `activity_started, activity_ended, corpus_completed, sleep_manual,
   dream_began, dream_artifact, picture_uploaded, sound_uploaded,
   video_uploaded, corpus_added, visual_motif_committed,
   visual_motif_fired, emission`.
   `target_familiarity_update` (line 4753) and `target_familiarity_snapshot`
   (line 4046) are **not on that list**. They are logged to the in-memory
   ring buffer only. A full EFS/ECS-exec grep of this file — even if I had
   it — would structurally never contain this event type, boot or no boot.

2. **In-memory ring buffer** (`_substrate_events`, `deque(maxlen=1000)`,
   gualaloom_v5_engine.py:1364), read via `guala_get_events`:
   ```
   since_tick=0, limit=2000       → 26 events, tick range 14467598–14468127
   since_tick=14400000, limit=1000 → 37 events, tick range 14467598–14468383
   ```
   Both queries returned the same shallow, currently-live window — the
   buffer is being cycled fast by high-frequency kinds (`agency_backtrack`,
   `emission_dynamics`, `response_window_opened/expired`, several per
   ~350-tick EMITTING cycle). `target_familiarity_update`: **0 occurrences**
   in either pull, for any picture, not just e93d29dae5ae.

   Directly useful anyway: in that same window I caught **two consecutive
   ATTENDING_VISUAL activity_started/activity_ended pairs on e93d29dae5ae
   itself**, both ending short of budget:
   ```
   {"tick":14467598,"kind":"activity_started","detail":{"kind":"ATTENDING_VISUAL","target":"e93d29dae5ae","salience":0.1}}
   {"tick":14468026,"kind":"activity_ended","detail":{"kind":"ATTENDING_VISUAL","target":"e93d29dae5ae","duration":428}}
   {"tick":14468126,"kind":"activity_started","detail":{"kind":"ATTENDING_VISUAL","target":"e93d29dae5ae","salience":0.1}}
   {"tick":14468382,"kind":"activity_ended","detail":{"kind":"ATTENDING_VISUAL","target":"e93d29dae5ae","duration":256}}
   ```
   Budget for ATTENDING_VISUAL is 2000 ticks (ACTIVITY_TICK_BUDGETS,
   line 425). Both sessions ended at 428 and 256 — interrupted, not
   completed. F2's write gate (`self.tick >= a.expected_end_tick - 1`,
   line 4749) never evaluates true for either. This is a live,
   verbatim, direct observation of the F2 mechanism actually
   suppressing the write on the groove target itself, twice in a row.

   Also notable, pre-existing field (not my instrumentation — this
   `salience` value was already logged before d45e877): **0.1000
   exactly**, both times. Per `_action_salience` (line 4182-4194), for
   times_attended≥1 the returned value is `max(visual_score, needs_score)`
   where `visual_score = (1 - fam) * 0.1`. A salience of exactly 0.1000
   is only possible if `fam == 0.0` — i.e. `target_familiarity.get(target, 0.0)`
   is reading the *default*, not a decayed-but-present value. Consistent
   with F3 (deletion-to-zero) and with A.2 below (the dict has no entry
   for this picture at all, so `.get()` always falls through to 0.0).

   Task:453's original ~69-minute run (where the CMD's 473-attendance
   observation was made) is gone — its ring buffer died with the
   process. `aws ecs execute-command` (which could read the raw disk
   file directly) is confirmed non-functional: `TargetNotConnectedException`,
   because `dsf-ai-task-role` has no `ssmmessages:*` permissions (only
   the inline `dsf-ai-s3-backup` policy). A fix is staged
   (`docs/GL-IAM-STAGED-SSMMESSAGES-20260702.json`) but explicitly
   marked "do NOT apply until Joe approves in chat" — I have not applied
   it; flagging that it exists in case Eve/Joe want to authorize it for
   future forensics.

**Verdict contribution:** no completion-write ever observed or
recoverable for e93d29dae5ae. Consistent with H1. Not proof by count
(can't produce a count), but the interruption mechanism was caught live,
twice, in real time, on the actual groove target.

---

## A.2 — target_familiarity dict from latest save files (EFS or S3)

I do not have EFS filesystem access (see A.1's ECS-exec note — same
permission gap). Used S3 backups instead, and pulled **two**, spanning
the restart, to cross-check:

**Backup 1** — `s3://dsf-ai-site-backups/guala/2026-07-03_19-06-39/guala_core.json`
(saved_at_tick=14454961, 2026-07-03T19:06:08Z — task:453's pre-boot backup):
```
target_familiarity: {}   (0 keys)
e93d29dae5ae (IMG_6254, groove target): ABSENT
4eeee4d3d6de (Guala Family.HEIC): ABSENT
0f42a58ae29c (IMG_1962.HEIC): ABSENT
71777ea2d543 (IMG_2121.HEIC): ABSENT
d5cf62b2a66b (IMG_2161.HEIC): ABSENT
d6813cb13d4a (IMG_2216.HEIC): ABSENT
c9a8da4504e1 (snapshot_1783028536784.jpg): ABSENT
461b365d7d65 (Bell.png): ABSENT
```

**Backup 2** — `s3://dsf-ai-site-backups/guala/2026-07-03_20-17-05/guala_core.json`
(saved_at_tick=14467598, 2026-07-03T20:14:36Z — task:454's post-boot backup,
i.e. AFTER the health-check-failure restart described below):
```
target_familiarity: {}   (0 keys — identical result)
```
Same absence for every id listed above.

**This does not match the CMD's stated observation** ("22 keys logged,
groove target not among them"). Both save files I can reach show **zero**
keys total — not 22-with-one-missing. Two readings for this, stated
plainly rather than picked between:

1. The "22 keys" reading came from a live `target_familiarity_snapshot`
   *event* (ring-buffer-only, per A.1) at some point during task:453's
   run, closer to when the CMD was drafted than to boot. If full-state
   saves to EFS/S3 run on a slower cadence than that snapshot event, the
   22-key in-memory state may simply never have been flushed to a save
   file before task:453 died — meaning it's gone, not hiding somewhere
   I haven't checked.
2. Alternatively, target_familiarity genuinely does not survive a
   task restart intact, for reasons I haven't traced further (the
   save/load code paths themselves look symmetric at a glance —
   gualaloom_v5_engine.py:5927/6101 save it, :6773 loads it — so if
   this is real it's a save-cadence or write-ordering issue, not an
   obviously missing load path).

I'm not picking between these — flagging it as its own open question
worth Eve's attention, separate from the H1/H2/H3 call on e93d29dae5ae
specifically. Either way, the fact that stands regardless: **right now,
in the most recent save file available, familiarity is empty for
literally every picture, including the groove target.**

---

## A.5 — bypass sweep

**AUTONOMY_PHASED**, confirmed against the exact running task-definition
revision (not just the family's latest-by-name):
```
$ aws ecs describe-tasks --cluster tfe-web-cluster --tasks <running-task-id> \
    --query 'tasks[0].taskDefinitionArn'
arn:aws:ecs:us-east-1:418384447921:task-definition/dsf-ai-task:454

$ aws ecs describe-task-definition --task-definition dsf-ai-task:454 \
    --query 'taskDefinition.containerDefinitions[0].environment[?name==`AUTONOMY_PHASED`]'
[{"name": "AUTONOMY_PHASED", "value": "0"}]
```
Default (non-phased) path is active. Per source, both paths converge on
the same selector regardless: `_autonomy_tick` (line 4096) and
`_autonomy_tick_phased` (line 5002) both call `self._select_next_activity()`
— confirms the CMD's "single shared scorer" premise directly, not just
by assertion.

**`_force_next_activity` call sites** — exactly two in the whole service,
both hardcode SLEEPING, neither targets a picture:
```
dsf_ai_service/app.py:2540:            _guala._force_next_activity = ("SLEEPING", None)
dsf_ai_service/substrate_runner.py:2287:  _guala._force_next_activity = ("SLEEPING", None)
```
(Both back the force-dream endpoint per the code comment at
gualaloom_v5_engine.py:4260.)

**Curriculum/orchestrator picture-targeting** — zero hits. Grepped every
file under `dsf_ai_service/curriculum/` and `dsf_ai_service/loom_model/`
for `ATTENDING_VISUAL` or `_pictures[`: none reference either. The two
`ATTENDING_VISUAL` hits in `substrate_runner.py` (lines 297, 1907) are
both read-only observers of `_current_activity` for cross-modal bundle-id
tagging — they read what's already selected, they don't select it.

**H2's own predicted signature, checked directly** — H2 predicts
"activity_started for it lacking scored salience metadata." Both live
activity_started events for e93d29dae5ae in my sample carry a real,
non-null `salience: 0.1` — not absent, not null (contrast with the
EMITTING activity_started in the same window, which correctly shows
`salience: null` since EMITTING isn't a needs-scored kind the same way).
That's the opposite of what H2 predicts.

**Verdict contribution: H2 evidence so far is negative across every
angle checked** — no forcing call site targets pictures, no orchestrator
path touches visual attention, both autonomy paths share one scorer, the
env flag doesn't change that, and the live salience metadata is present
and real. I'm not calling H2 dead — A.3 (post-deploy) is the CMD's
designated positive-control check, per Eve's note: once d45e877 is live,
any activity_started missing `top_scores` is the tell. But everything
gatherable without that instrumentation points away from H2.

---

## Out-of-band: task:453 → task:454 during this investigation

Not part of the CMD, filing because it changes what "currently live"
means and because Eve's ruling assumed "she stays undisturbed."

- task:453 (image `deploy-20260703T190054Z`, the one in the handoff doc)
  started **19:06:47Z**, stopped **20:15:38Z**, reason: *"Task failed
  container health checks."* A second task instance on the same
  definition stopped 10s later, reason: *"Scaling activity initiated by
  (deployment ecs-svc/4221757956583147941)"* — i.e. a real deployment
  was in flight at the same moment the first instance failed its health
  check. I can't fully separate "coincidental failure during a routine
  rolling deploy" from "the deploy was a reaction to the failure" from
  the ECS API alone.
- task:454 (image `deploy-20260703T200824Z`) started **20:16:54Z** and
  is what's running now.
- **This deploy does NOT contain my Part A instrumentation (d45e877).**
  Confirmed by commit timestamp, not inference: the image was built at
  20:08:24Z; d45e877 was committed at 20:11:04Z — nearly 3 minutes
  *after* the build. c1b's -108 fix (b7fd05e, committed 20:07:42Z, 42s
  before the build) is almost certainly what shipped. This fully
  explains why every activity_started I captured above has `salience`
  but no `top_scores`/`needs_sd` — not a bug, just: the instrumented
  code genuinely isn't running yet.
- State continuity across the restart looks clean on everything I can
  check: IMG_6254.HEIC's `times_attended` read 473 (CMD) → 483 (first
  guala_status this session) → 489 (after the restart) — monotonic, no
  reset. `target_familiarity` is the one dict I can confirm did NOT
  carry a nonzero state across (see A.2), though as noted I can't yet
  tell if that's restart-related or was already empty going in.

**Practical implication for Eve's item 3 (consolidated build):** c1b's
-108 already shipped alone — that build predates Eve's "ship as one"
ruling (the commit landed 42 seconds before the image build, and Eve's
ruling text explicitly approves d45e877 by name, which didn't exist yet
at build time). So this wasn't a violation of the one-wake-cycle
instruction, just prior, independent motion. The next deploy — whenever
c1b runs it — is what needs to actually be the consolidated one carrying
d45e877.

---

## Status / next

Holding here. Not deploying anything myself (c1b owns deploy mechanics
per -108 Part B). Once that consolidated build is live, I'll capture
A.3 (≥3 consecutive ATTENDING_VISUAL selections with `top_scores` +
`needs_sd`) and A.4 (one live `needs.signed_distance()` dict), then
render the H1/H2/H3 verdict and file the complete
`GL-RPT-ATTEND-GROOVE-C1-20260703-107-v1` against gates G-107-1..5.

No fix commit before then, per G-107-1.
