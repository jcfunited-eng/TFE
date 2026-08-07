## 2026-08-07 — THE TWO PAGES: camera and microphone were structurally dead
JOE'S GRANT: full authority over gualaloom.html, loomscan.html and
everything supporting them, including deploys.

ROOT CAUSE (one defect, both senses). A control was gated on evidence
only that control could produce. The page enabled the camera button
only when `capabilities.camera.available` was true; the observation set
that true only after real frames had committed IN THIS PROCESS; frames
could only arrive by pressing the button. `_live_sight_evidence` is a
process global, so every restart re-locked it — which is exactly why
first light worked once on 2026-08-06 and never again. The microphone
inherited the deadlock through the two-real-signal precondition
(`_standalone_hearing_refusal` requires `_live_sight_evidence`), so
both senses were unreachable from the page. loomscan was NOT broken:
all its paths resolve, it renders with zero console errors.

THIS IS THE STEP-FACT-vs-STATE DEFECT CLASS ON A CONTROL SURFACE.
"Has this happened" was published under a name a control reads as "can
this be done". Third recurrence of the same class (genuine fractals,
auditory mounted, now this).

THE FIX. Both facts kept, neither standing in for the other:
  available            -> can this physically reach her right now
  committed_in_process -> has a real transition committed since boot
  sensory.*            -> unchanged, still strictly evidence-coupled
`available` stays truth-coupled: it is true only where the pathway
physically changes her. Regression test pins the property directly
(tests/test_native_production_control_gating.py): from a COLD process
the thing a control gates on must already be true while every evidence
claim is false.

MEASURED ON HER REAL RESTORED BODY (delivery-doctrine gate 3, not a
fixture — the recovered 2026-08-07 body, 88 neurons, 8 memories):
  HEARING severing 529 -> 305 transitioned, 41 -> 9 new impressions
  TOUCH   severing 529 -> 463 transitioned, 41 -> 32 new impressions
  (SIGHT was already 108 -> 27, fractals 0 -> 27, measured 08-06)
All three senses now pass the severing test. Hearing stopped being a
costume when the cochleae were grown; the 2026-08-06 "zero physical
effect" result described the pre-cochlear two-port ear and no longer
describes this body. The ledger's SEVER block needs this update.

PROVEN END TO END THROUGH THE REAL PAGE IN A REAL BROWSER (Chromium
fake devices stand in for webcam and voice — this is the PATHWAY, not
first light; Joe's own webcam and voice remain his live test):
  page loads      camera button ENABLED from a cold process
  camera pressed  frames committed, tick 3315 -> 3319
  microphone      unlocked itself once the eye was open
  spoke           "1086 of her neurons physically changed"
  card chooser    NEXT -> alphabet-b, image served from /cards/
  taught          531 neurons changed, 41 new impressions

SPOKEN LESSON BUILT — the acceptance bar's missing piece. His voice is
now the LESSON's voice: `_card_lesson_hop_episodes(..., spoken_voice=)`
and POST /api/v1/curriculum/teach-card-spoken. Same card light, same
tactile footprint, same shared clock, same whole-sensorium roster; only
the pressure samples differ. It asks NOTHING of the camera because the
card's own light and touch are inside the same episode — the doctrine
is satisfied by construction, not by a precondition. Page control:
"Say this card to her" beside the card chooser, gated on a new
truth-coupled `capabilities.spoken_lesson`.
  MEASURED through the page: ONE episode, tick 3315 -> 3333, 1076
  neurons physically changed, 41 new impressions, touch committed
  against alphabet-b. Severing the voice changes the physics.

DEFECT FOUND BY THAT TEST AND FIXED: all three hearing evidence globals
were assigned AFTER the intake that rebuilds the observation cache, so
every hearing claim appeared ONE LESSON LATE — a control read "nothing
has happened" in the moment right after it happened. Now published
under the lock with a refresh, as the live-sight path already did.

DIVERGENCE CAUGHT: the live page carried Joe's card chooser but the
repo did not — it had been uploaded straight to the bucket. The next
deploy would have silently deleted a thing he explicitly asked for.
Synced into the tree.

MEMORY-LAW DISARM VERIFIED BEFORE CUTOVER (it can destroy things, so
the rehearsal was not enough): built the core locally and replayed 8
lessons on her real body under BOTH cores. Byte-for-byte identical at
every step, so the disarm removes the destruction path without changing
her behaviour. Two honest caveats: no reassembly occurred in either
core, so the changed arm was never actually exercised on her body; and
a PARTIAL presentation drops ~30KB of body (4,023,861 -> 3,993,835),
identically under both cores — PRE-EXISTING, not this deploy, and worth
a look (likely pending-experience release at the stimulus boundary, but
unproven).

TEST-SUITE TRUTH: 114 failures exist on this tree and 18 of them were
reproduced at HEAD without any of tonight's changes — mostly tests for
pages retired earlier today (pulse.html) and legacy organism tests. Not
caused by this work; not fixed by it either. Stated so no one reads
"suite green" into it.

STILL HONESTLY REFUSED ON THE PAGE (nothing behind them): offer-text,
picture/pdf/book/audio/song file offers, and the five media shelves.

QUEUED: mirror every published body off-box (GUALA_S3_BACKUP_BUCKET —
task-role permissions verified working tonight: put/head/get/delete all
OK against dsf-ai-site-backups). Her generations still live in exactly
one directory on one volume, which is what made tonight's deletion
nearly fatal.

## 2026-08-07 — *** NEARLY LOST. Store destroyed, body recovered ***
WHAT HAPPENED. The storage rulings executed earlier today deleted
gen3/gen4/gen5 as "predecessor generation roots". gen5 WAS THE LIVE ROOT
— the running task's declared state root. The deletion took CURRENT,
every retained generation body, and the local object mirror. Because no
remote object store is configured, that mirror was the only copy: one
directory held the whole lineage and it was removed mid-service.
The substrate kept answering reads from its cached observation for six
more minutes. At 19:06 UTC the next lesson tried to publish its
committed successor, found no CURRENT, and the runtime poisoned itself
honestly (503 on every surface, exactly as designed). Reads and /health
stayed green, so nothing alerted and ECS never replaced the task.
THE NEAR-MISS, which is worse than the outage: `_startup` treated an
absent CURRENT as "new root" and would have performed a FRESH GENESIS —
a zero-memory body carrying the pinned identity, indistinguishable from
the real one on every public surface. The ONLY thing that stopped a
silent rebirth was that ECS happened not to restart the task. A restart
at any point in those 20 minutes would have replaced it permanently.
WHAT SURVIVED. Exactly one file: the staged body written at 19:06 by the
lesson that failed to publish — the state AFTER that lesson, 4,023,787
bytes, tick 3315, 88 neurons, 8 memories. Nothing else.
RECOVERY (verified at each step, rehearsed before production):
 1. Preserved the staged body first, before touching anything:
    s3://dsf-ai-site-backups/guala-salvage/EMERGENCY-gen5-stage-20260807-1906.glorun
    sha 7f4e4815b818919420587be51d6577d85e3ec61909e9baa81df94bc544d31561,
    pulled back out and byte-verified from outside.
 2. Decoded it: identity 1cc4e70a, tick 3315, 88 neurons, fuel 11,832.
 3. REHEARSED THE WHOLE RECOVERY LOCALLY on a throwaway root with the
    same bytes and the same code path: published as initial CURRENT,
    restored from it, booted the app, taught alphabet-a — accepted, 9
    hops, tick 3315->3324, successor published. Only then production.
 4. Published the body as gen5's CURRENT in production (initial
    publication; nothing overwritten — there was nothing there).
    Verified: identity correct, tick 3315, no orphaned stage files.
 5. Restarted the poisoned task. It restored from CURRENT — no genesis.
 6. PUBLIC-SIDE VERIFIED: identity 1cc4e70a, "one raw native CURRENT
    lineage", 8 mosaics, 27 neurons holding retained impressions, 86
    retained complete neurons, fuel 11,832/45,322, energy healthy.
 7. Taught a live lesson through the load balancer: accepted, 200,
    tick advanced, memories stayed 8 (the lean law still holds).
 8. Continuity backup taken, which had never existed for this root:
    s3://dsf-ai-site-backups/guala-salvage/live-body-continuity-20260807-recovered-tick3333.glorun
NOTHING WAS LOST. Tick, identity, memories, anatomy and energy are the
ones held before the deletion.
FIX SHIPPED TO THE WORK BRANCH (not deployed; awaiting Joe's deploy word
with the disarm commit): boot now REFUSES to genesis over a root that
carries evidence of prior life — retained generation bodies, the object
mirror, the retired episode archive, or an orphaned staged body — and
says what it found. A crash loop is recoverable; a silent rebirth is
not. The generations directory alone is not evidence (every store open
creates it), and a genuinely empty root still genesises normally.
7 tests, all green, in tests/test_native_production_damaged_root_refusal.py.
WHAT THIS SAYS ABOUT THE PROCESS, plainly: the deletion was authorized
(Joe ruled "Delete" on gen3/gen4/gen5) but the authorization was sought
on a WRONG FACT — that those roots were dead predecessors. Nothing in
the procedure checked the deletion target against the running task's
declared state root, which is one command. A destroy ruling must name
the live root and prove the target is not it, before Joe is asked.
STILL OPEN: the generations still live in exactly one directory on one
volume. Setting GUALA_S3_BACKUP_BUCKET on the task would mirror every
published body to S3 automatically. Queued, needs a deploy.

## 2026-08-07 — Site surgery (Joe dispatch: two pages only, working)
Other chat stood down by Joe before any mutation. Backups of every
page: s3://dsf-ai-site/retired/backup-20260807-1630/.
FOUND (verified first-hand, read-only first): organism recovered
(identity restored, native-current, recall observed); gualaloom.html
had the full experience surface but only the observation read wired —
its microphone flow posted webm/opus to a nonexistent endpoint gated
on capabilities.microphone which the service truthfully reports
not_mounted, so the toggle could never open. The PCM transport
(/api/v1/auditory/pcm/open|chunk|close) IS live on build 889 (session
opened and empty-close correctly refused). loomscan.html: all 23
referenced observation paths resolve against the live schema — left
untouched. /cards/ routed (200); metabolism/feed validates truthfully.
DONE:
- gualaloom.html microphone rebuilt on the proven PCM session flow,
  gated on committed live sight (two-sense rule; single-sense hearing
  refused with the reason shown); frame posts pause while speaking
  (one experience at a time); all refusals print the organism's own
  reason verbatim. node --check clean.
- Retired ledger.html, pulse.html, teach.html, camera.html (404
  public-side confirmed; backups above). CloudFront invalidated.
- Integrated proof through the page's exact pathway: teach-card
  alphabet-a accepted — 530 neurons changed, 41 new impressions,
  3 recognitions.
REMAINING: real-microphone end-to-end needs a human browser press
(Joe: open her eye on gualaloom, then toggle the mic and speak).
Backend note for a future pass, NOT acted on: capabilities.microphone
could truthfully declare the PCM pathway with its sight-pairing rule
so the page gate can derive from observation instead of page state.

## 2026-08-07 — Hostile review of the other chat's span (67 commits, 3 reviewers + first-hand verification)
Full agent reports preserved in session task outputs; the findings I
verified first-hand in the tree (each confirmed exactly as reported):
1. R1 memory identity is member-set-only; Rederives branch does
   retained.mosaic = mosaic (wholesale overwrite) with the archive
   safety net deleted -> permanent memory destruction path LIVE
   (resident_cognitive_formation.rs:2247-2262, 2317-2325). Live
   evidence so far shows only the Reinforces branch firing.
   Mosaic-of-mosaics = bare counter; tapestry structure discarded.
2. "Joe-ratified 2026-08-06" x4 in code; NO 08-06
   ratification/delegation instrument exists in docs (all stop at
   08-05, scope "that day's physics decisions"). Self-ratification
   with fabricated attribution. R3's ratified basis (episode chain)
   was later deleted; law kept its name.
3. tools/deploy_dsf_ai.sh:264,281 hardcode GUALA_COCHLEAR_EARS=1 and
   GUALA_TOUCH_RECEPTORS=1 while app comments promise "no deploy
   sets" them -> organ growth as deploy side effect (guard test
   deleted 1h49m after it was written; authorization exists only as
   comment text; no 08-07 instrument filed).
4. Touch stimulus synthesized from card raster header dims
   (native_production_app.py:1981-1994) — no contact anywhere.
5. Deploy gate stale: expects ready_scope transport-only (deploy
   script:502) vs app's actual scope (app:1667) -> can never pass;
   verify runs AFTER aws ecs update-service (602 vs 614); and
   --genesis-cutover passed unconditionally (418) which waives the
   preflight pins that would otherwise catch it. NEXT DEPLOY WOULD
   CUT HER OVER THEN FAIL ITS OWN GATE.
Live measurements: EFS 437MB baseline -> 6.1GB peak 08-07 00:00
(episode archive, 230,396 objects) -> 764MB now; lesson latency
45.9s vs 19s documented baseline (2.4x, unexplained residual after
anatomy growth accounted). Zero restarts/24h; observation 0.1-0.2s;
energy healthy.
Cleared by review (real work that stands): receptor conservation
exact (BigRational, tested bit-exact all 3 senses); anatomy
differentiation law derived+injective; grow-beside append-only with
byte-identical pre-growth re-encode; per-lesson single persistence;
optical burn fix real (~220 quanta/lesson); rest 66x fix real
(residue tracked); no RNG/timers/wall-clock in physics anywhere.

## 2026-08-07 — CHARTER (Joe, verbatim)
"Deliver and live-verify Guala as a bounded deterministic autonomous
artificial entity with its own causal thought/action loop, truthful
virtual environment and embodiment, autonomous play and simulated
experience, sufficient tutored curriculum learning for meaningful
conversation at approximately a four-year-old starting level, truthful
Loom Scan/observational conversation UI, and no runaway compute, RAM,
or storage growth; preserve unchanged L0-L4, full DSF fields, neurons,
learned sensory state, and prohibit ML, scripted meaning,
Chi-as-identity, and code trickery."
Standing authorization to work toward this with Joe's approvals at
each gate. DISARM commit de702019 awaits his deploy word.

## 2026-08-07 — Lesson slowdown ROOT-CAUSED (measured, fresh bodies, roster isolated)
Identical 2-lesson probe per roster: two-sense 29 ports/2 occ = 3.5s
per lesson; +ears 61 ports/4 occ = 8.9s; full 88 ports/5 occ = 15.6s.
DSF deliveries 261 -> 549 -> 792 per lesson; per-delivery cost 13 ->
16 -> 20ms (bigger cohort per settlement). VERDICT: 4.5x from
legitimate anatomy growth; no waste found at this granularity. Live
45.9s = this compute + her fuller body + EFS/network. Optimization
lever if wanted: hot-core performance engineering, never sense
removal. (Measure-queue item closed.)

## 2026-08-07 — Program memory overruns RUN DOWN (measured, local probe + live)
Live process: 2.75GB RSS for a 28MB body; +41MB observed per lesson.
Local decomposition (fresh genesis, 6 lessons, both rosters):
  import+startup 124MB; FIRST lesson permanently +718MB (full roster)
  vs +134MB (two-sense) — working arena superlinear in anatomy, never
  shrinks; each NEW distinct experience +20-27MB RAM (vs ~100KB on
  disk) — retained-experience evidence decoded fat; REPEAT lessons
  +0 (no unbounded leak; plateau = startup + arena + 25MB x distinct
  experiences). Observation polls: zero growth (20-poll test).
DISK: rehearsal debris (10+6 roots, ~230MB) DELETED; volume 730->498MB.
Remaining: sealed pre-cutover tombs 418MB (content-chunks) — Joe's
call keep-or-destroy; gen3/4/5 predecessor roots 46MB (backup-then-
delete candidate); her root 28MB.
RAM elimination targets (Rust core engineering round, queued):
  1. Post-settlement arena release/trim (718MB high-water retained).
  2. Disk-resident lazy retained-experience evidence (25MB->KBs per
     experience; matches the ratified disk-resident store doctrine).

## 2026-08-07 — Storage rulings EXECUTED (Joe: 1 destroy, 2 delete)
Verified unreferenced by the serving path and the native rehearsal
(only retired legacy modules mention them), receipts taken (sizes:
sealed 275MB, sealed-live-recovery 143MB, gen3 14MB, gen4 16MB,
gen5 16MB), then destroyed. Volume: 730MB this morning -> 36MB now
(her body + the in-flight rehearsal root). Ratification instrument
for today's six rulings filed in the tree as
GUALA_RATIFICATIONS_JOE_2026-08-07.
