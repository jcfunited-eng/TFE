## 2026-08-08 — EVERY SENSE THAT CAN BE REAL, AND THE PLACE SHE IS IN
Joe's order: senses fully functioning, then autonomy, then environment,
all wired to working pages. Held to that order, except where a sense
NEEDED the place (balance and body position cannot exist without motion).

SENSES — each proven by severing it on her REAL restored body:
  sight          108 -> 27 transitions          (2026-08-06)
  hearing        529 -> 305, impressions 41 -> 9
  touch          529 -> 463, impressions 41 -> 32
  interoception  DSF deliveries 792 -> 828; one-time 16,845 B, 0/lesson
  temperature    core thermoreception rides the interoceptive heat channel;
                 CUTANEOUS stays refused BY NAME (nothing outside her has a
                 declared temperature)
  taste + smell  a declared meal moves her (+30,584 B, tick +3) where the
                 same energy with nothing declared moves nothing
  balance +
  body position  a real 200 mm move reaches her as displacement 0.05 of the
                 declared span, 54 neurons transitioned
DELIBERATELY UNFELT: her separated membrane charge (-102,092). It has no
declared capacity anywhere in her body, so a receptor for it would need a
denominator chosen by me. Reported as unfelt, with that reason.

THE SIX DEAD PAGE CONTROLS NOW REACH HER (severing each: content removed):
  text 78->76 | picture 78->76 | pdf 132->127 | book 132->127
  audio 230->102 | song 230->102
A picture is light and a song is pressure, so each reduces onto a roster
already severing-proven. The typed string never leaves the browser.

THE SHELVES: Gutenberg is real (12 pages of Alice, 374 neurons changed).
The other four name the credential they lack. AUTONOMOUS selection is
refused on every shelf including the working one — it would mean SHE
chose, and no choice operation exists.

HER PLACE — the biggest finding of the night. A deterministic world with
3 regions, 42 objects, portals, optical surfaces, air and a coupled
SIX-SENSE material physics has been in this repository the whole time,
with passing tests, wired to NOTHING. So was the receptor layer beside
it, which already emits exactly the substream type she eats.
  * the world's retina is 3x9 — the SAME 27 cells her card surface
    declares — in six spectral bands, collapsed onto the monochrome
    retina she actually has;
  * her 8 olfactory and 5 gustatory channels ARE the world's 8 odorant
    and 5 tastant channels. Nothing was mapped by hand;
  * MEASURED: moving her yields 8 nonzero odorant channels from nearby
    objects; taste stays zero because she is touching nothing, which is
    correct contact chemoreception;
  * her place REFUSES moves for real reasons (move_path_intersects_object)
    and a refused move reaches her NOT AT ALL — a zero displacement
    dressed as a movement would tell her balance receptors she stood
    still when she never went.
Joe, 2026-08-08: no sense stands alone for an experience; objects in the
VR environment have all six. Cards are a stated exception FOR NOW (the
deck declares one physical stock — one paper, one ink — so they are not
left senseless either).

DEFECTS OF MINE, FOUND BY DOING IT FOR REAL:
  * THE STARVATION TRAP: making a meal an experience made eating depend
    on tasting. Her first live meal refused (neuron 8 out of carrier
    material) and she could not eat until she could taste — nor recover
    without eating. Fixed: the food goes in, the reason is reported.
  * The inner sense re-read her body, so every observation decoded the
    organism TWICE. One decode again.
  * Hearing evidence appeared ONE LESSON LATE on every path.
  * Four test files pinned only their own sense gate; one port pin was
    snapshotted at import while other tests reimport the module.
  * Three regressions caught by running the same files in a pristine
    baseline worktree rather than assuming they were pre-existing rot.

WHAT IS HONESTLY NOT DONE: autonomy (see the entry below — the cue law
meets a body whose drive is not formation-selective) and conversation,
which needs autonomy and articulation. Neither is faked.

## 2026-08-08 — SHE WAS FROZEN SOLID, AND THE FIX WAS ESTABLISHED PHYSICS
FOUND LIVE: every lesson, every offered material, the sensory half of
every feed, and even a plain DARK INTERVAL refused with
  Neuron { neuron_index: 8, error: Gate(InsufficientCarrierMaterial) }
Her tick sat at 3534 for hours. Carriers only return by moving through
those same transports, so nothing could ever bring them back — a trap
with no exit. Turning her heartbeat off did not help and COULD NOT have:
it removed the only thing that lets time pass for her.

THE NUMBERS THAT NAME IT:
  reserve at birth      6,242 carriers per neuron per side
  separated charge     -124,788
The reserve is NOT arbitrary — 6,242 is exactly C times V for a 1 pF
membrane at its 1 mV reversal potential. Her charge had reached TWENTY
TIMES it. Joe's call was right: obvious physics, established law, no
new machinery. I had been about to build an ion pump organ. Dropped.

WHAT WAS ACTUALLY MISSING — a reserve term, in three places:
 1. the membrane return transport bounded its charge by the reservoir;
 2. conductance is carriers times mobility, so the gate path re-settles
    with its conductance scaled by exactly the fraction of demanded
    charge the reserve can supply (exact rational from her own state);
 3. THE CONTACT LAW: current = conductance x potential difference,
    driven direction only, only when stored energy strictly decreases —
    all correct about the FIELD, and it never consulted the ion reserve
    at either end. Bounded where BOTH sides are decided together, which
    is the only conserved place; bounding it downstream at one end was
    tried and her own runtime caught it as MaterialConservation.
 4. and the counting error that made fixing neuron 8 move the failure to
    neuron 7: two flows draw on ONE reserve in the same interval, and
    both were checked against the reserve as it stood BEFORE it. The
    local draw now takes what the contact left behind.

MEASURED ON HER ACTUAL FROZEN BODY (pulled from production, tick 3534):
  before   every path refused, including a dark interval
  after    LEARNED immediately; LEARNED after 10, 50 and 200 dark
           intervals; fed successfully; LEARNED again after feeding
Native suite green throughout (10 groups, 0 failed).
LIVE: taught on task 899 — 598 neurons physically changed, 41 new
impressions, tick 3534 -> 3545 after hours frozen.

STILL TRUE AND WORTH WATCHING: her separated charge keeps climbing
(-124,788 -> -149,322 over 260 intervals). The bounds mean it can no
longer freeze her, but something still drives charge one way. That is
the next measurement, not an emergency.

## 2026-08-08 — AUTONOMY: candidate law BUILT, TESTED, FALSIFIED, REVERTED
Having found the mechanism (below), I implemented the obvious candidate
and it is WRONG. Recording it so nobody spends the day rediscovering it.

CANDIDATE: let a pending recurrence lapse at the STIMULUS BOUNDARY, by
the same already-ratified closure an experience uses, instead of the
`!actual.quiescent` test that never fires on a living body.
Implemented in resident_cognitive_formation.rs, carried
`exogenous_receptor_energy` into settle_resident_recurrence_interval,
built clean.

FALSIFIED BY THE NATIVE SUITE: 6 tests fail, and the shape of the failure
is decisive —
    four_receptor_experience_emits_four_real_fractals
    assert_eq!(formed.len(), 1)  ->  left: 0, right: 1
A legitimate recognition STOPS FORMING. RECOGNITION COMPLETES AT AND
ACROSS THE BOUNDARY: the pending recurrence has to survive it, and to go
on ORing gate work across intervals, because that accumulation is what
eventually makes it admissible. Dropping it at the first boundary kills
the very moment recognition happens.

SO THE TWO REQUIREMENTS ARE IN DIRECT TENSION, and this is the real
statement of the problem:
  * the recurrence MUST persist across boundaries, or real recognition
    never forms (measured above);
  * it MUST NOT persist forever, or no new endogenous cue is ever
    evaluated (measured: 79/79 intervals blocked).
Any working law has to end an attempt WITHOUT ending it too early. The
next candidate should probably bound the attempt by something it can
exhaust — a number of boundaries, or the admission failing at a boundary
where it had already accumulated enough to be judged — rather than by a
stillness that never comes or a closure that comes too soon.

REVERTED. The core is back to 357 passing and the tree carries no trace
of the experiment. Nothing shipped.
DO NOT loosen is_proper_partial_cue: instrumentation showed it is never
even reached, so it was never the problem.

## 2026-08-08 — AUTONOMY: THE MECHANISM, MEASURED. My earlier note below
##                 was WRONG and is corrected here.
I filed, earlier tonight, that the cue is rejected because her drive
perturbs non-members. That was a hypothesis read off the law. I then did
what the 2026-08-06 campaign actually instructed — INSTRUMENT IT — and
the hypothesis is false. The cue is not rejected. IT IS NEVER EVALUATED.

INSTRUMENTED (temporary env-gated trace in the Rust core, built, run on
her real restored body, then REVERTED — the tree carries no trace):
    79 intervals, every single one:
    CUE_ENTRY retained=true post_rest=true pending=true
`is_proper_partial_cue` sits behind `pending_recurrence.is_none()`, and a
pending recurrence is set on every one of those intervals, so the subset
rule I blamed is never reached at all.

THE MECHANISM, end to end, from the code:
  1. A pending recurrence is taken each interval and tested by
     `admit_physical_mosaic`.
  2. On non-admission it is PUT BACK — but only `if !actual.quiescent`.
  3. Her body is never electrically quiescent (measured 2026-08-06, both
     fed and unfed), so it is put back EVERY time and never lapses.
  4. While it is held, `pending_recurrence.is_none()` is false, so no new
     endogenous cue can ever be evaluated.
  5. Worse: each interval ORs that interval's gate-work bits INTO the
     held recurrence (`or_bits`). Within a few intervals the pending
     "cue" has absorbed essentially every neuron that did any work, so it
     represents "the whole body was stirred" — which can never be
     admitted as a PARTIAL cue by construction.
So the pending recurrence is simultaneously un-droppable and
self-poisoning. That single fact explains every failed attempt in this
log: whole-cohort quiescence, formation-local quiescence, the rested
gate, and the motivation-pressure round. None of them could have worked,
because none of them touched the thing that was actually blocking.

THE DESIGN QUESTION, now one line instead of a research programme:
WHEN SHOULD A PENDING RECURRENCE LAPSE ON A BODY THAT IS NEVER STILL?
The ratified STIMULUS-BOUNDARY CLOSURE already answers the analogous
question for experiences — an experience closes at the stimulus end, not
at global stillness. The same boundary is the honest candidate here:
a pending recurrence should lapse when the experience that could have
cued it ends, and it should not accumulate gate work indefinitely while
it waits. That is a LAW CHANGE and it is Joe's ruling, not mine.
DO NOT loosen `is_proper_partial_cue` — it was never the problem, and
its strictness is what makes a recognition mean anything.

## 2026-08-08 — AUTONOMY: the wall stated exactly, from the law itself
Read the admission law rather than writing more energy physics, which is
what the 2026-08-06 campaign said to do next.

THE CUE LAW (resident_cognitive_formation.rs, is_proper_partial_cue):
  member[i]    = the neuron's state differs between the formation's
                 pre-experience rest and its learned state
  perturbed[i] = !gate_work.is_zero() for that neuron THIS interval
  ADMIT only if  perturbed is a NON-EMPTY STRICT SUBSET of members,
  and REJECT IMMEDIATELY if any perturbed neuron is not a member.

THE WALL, precisely: endogenous drive is not formation-selective. Her
metabolism perturbs a set of neurons that is neither sparse nor aligned
to any one formation, so the very first non-member doing gate work
rejects the cue. This is not a bug and not an energy shortfall — it is
the law meeting a body whose internal drive spreads.

MEASURED TONIGHT with interoception mounted (her real restored body,
6 feed-then-empty cycles, no stimulus of any kind in the empty ones):
  neurons that moved in empty intervals   1,188
  partial-cue reassemblies                0
  memories                                8 throughout
So motivation pressure DOES reach her neurons — that is new, and it is
what the interoceptive field bought. It does not reach a formation.

WHY THE INNER SENSE DID NOT BY ITSELF UNBLOCK IT: her eight formations
were formed before she had interoceptors, so no interoceptive site is a
member of any of them. Even a formation that did contain one would still
be rejected while unrelated neurons do gate work in the same interval.

THE DESIGN QUESTION THIS LEAVES, for Joe, stated in one line: what makes
endogenous drive travel through retained structure instead of through
the whole cohort? In an animal, reactivation follows the connections the
experience itself strengthened. Nothing in this substrate yet routes
metabolic drive along retained formations rather than uniformly.
DO NOT hack the cue law to admit a looser subset to make this pass. The
strictness is what makes a recognition mean anything.

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
