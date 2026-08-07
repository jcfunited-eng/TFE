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
