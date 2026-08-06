---
name: guala-development
description: Operate and develop the live Guala native organism — tree locations, verification discipline, deploy gates, measured substrate facts, doctrine rules. Load at session start for ANY Guala work.
---

# Guala development — operational knowledge (established 2026-08-05)

## Where everything lives
- Working tree: `/tmp/guala-production-15a7dca9` (salvaged Codex worktree),
  branch `salvage/codex-d3-work-20260805`. If /tmp was wiped: restore from
  GitHub `jcfunited-eng/GualaLoom` branch `salvage/codex-d3-snapshot-20260805`
  (workflow files relocated under docs/salvaged-github-workflows/) or the
  byte-exact bundle `s3://dsf-ai-site-backups/guala-salvage/*.bundle`.
- Rust core: `native/guala_core` (pyo3 wheel via maturin; system cargo).
- Served app: `dsf_ai_service/native_production_app.py` (lean surface; the
  legacy app.py + owner cascade are EXCLUDED from the image by design).
- Release manifest: `deploy/guala_release_manifest.json` = EXACT compile +
  import closure, canonical JSON; packaging test compiles the staged crate.
- Deploy: `tools/deploy_dsf_ai.sh` (has --rehearse-only; genesis-cutover
  declaration; identity pinned 1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1).
- Live: ECS dsf-ai-task on tfe-web-cluster / dsf-ai-service-lb; EFS
  gualaloom-state -> /app/guala; state root /app/guala/native-organism.
  Public: https://dsf-ai.com (CloudFront: S3 static + /api/* -> ALB).
- Session evidence: lesson ledger + probes in the session scratchpad;
  night-shift log + fix queue: docs/GUALA_NIGHT_SHIFT_20260805_CLAUDE.md.
- Autonomy law: docs/GUALA_DARPA_FIRST_PROOF_BOUNDARY_2026-08-04.md
  (System Greed = unequal geometry-mediated access of cohesive structures
  to unresolved potential; quiescence when no cause; endogenous occurrence
  origination is the missing compiled piece).

## Discipline (violations burned a month; do not relax)
0. TWO-SENSE MINIMUM (Joe, 2026-08-05): no single-sense experiences.
   Every experience episode carries the full mounted sensorium with TRUE
   samples (dark/silence are lawful states, absence of a sense is not).
1. NOTHING is "complete" without integrated organism proof; nothing is
   "deployed" unless live in production and verified from the public side.
2. Verify agent claims FIRST-HAND (rerun their headline tests) before
   committing or reporting. Agents' "complete locally" has lied before.
3. Truth-coupling: every surfaced flag must derive from observation counts,
   never from the mounted surface. Refuse honestly where physics is absent.
4. Never infer/fabricate physics: contacts, occurrences, relevance are
   AUTHORED from declared anatomy; caps are DERIVED, never heuristic.
5. Deploy gate: rehearsal must prove identity-pinned genesis + first
   learning (genuine fractals) in the production environment before cutover.
6. Commit + push a GitHub snapshot after every verified milestone.
7. Measure before reacting: pause consumption, replay deterministically
   (physics is bit-deterministic; state receipts prove trajectory identity).

## Measured substrate facts (do not re-derive; update if remeasured)
- Kernel bit-true to UF v1.4 spec (159/159 values, independent recompute).
- First presentation grows neurons, 0 fractals; RECURRENCE (2nd identical
  presentation) emits the genuine post-quiescence fractals.
- Mosaic = recognition: requires PARTIAL cue (strict subset) whose current
  re-reaches the whole retained formation; full presentations never admit.
- Metabolism: fuel->spent+heat ratchet exists with NO recovery reaction,
  but card/sound lessons burn EXACTLY ZERO (gates never flip on them).
  Exhaustion failure modes are silent-success. DNA expression uncatalyzed
  everywhere -> neuron count capped at birth anatomy until fed.
- No sleep/dream/decay/consolidation exists anywhere; rest is functionless
  stillness; harmless only while nothing depletes/accrues.
- Body ~7.23MB is ~95% duplication (27 identical anatomy blobs 49%,
  snapshot copies 24%, derivable recovery anatomy 12%); distinct ~0.4MB.
  Body is byte-FLAT across lessons after the one-time retained-experience
  completion. Episode records as coded = ~3.55MB each -> ~1,500-experience
  lifetime under the 5GiB pin; fix = references into content-addressed
  cold custody (already stores once, sha256).
- Per-hop persistence writes ~400MB/lesson transient traffic (store DOES
  prune predecessors; disk holds ~2 bodies). Fix: persist once per lesson.
- Hippocampal index: O(1) resident checkpoint (74B), append-only,
  content-addressed, no recency/reactivation state anywhere.
- Cards are two-sense today (sight + tutor audio); touch unmounted.

## Standard procedures
- School: scratchpad run_card_lessons.py -> POST /api/v1/curriculum/teach-card
  {card_id[, "presentation":"partial"]}; ledger JSONL per lesson; ~19s
  server per 15s card; rest gaps physically functionless (3s cosmetic).
- Body decode: reservoir/size probes under
  native/guala_core/src/resident_cognitive_formation/ (#[cfg(test)]) +
  scratchpad drive/size scripts — replay genesis+lessons on a tmp root,
  decode persisted generations.
- Deploy: clean tree required; bash tools/deploy_dsf_ai.sh --rehearse-only
  first; proof JSON lands in CloudWatch /ecs/dsf-ai stream
  guala-native-genesis-rehearse/dsf-ai/<task-id>; then full run cuts over.
  GitHub token: workflow-scope-less (use snapshot-relocation push pattern).
- Page swap: S3 dsf-ai-site + CloudFront invalidation; back up old first.

## Ratifications + delegation record (2026-08-05)
- Quantized optical transduction RATIFIED (Option A): light as whole
  gate-lattice quanta, exact-rational accumulator of unchanged 2LT law.
- By DELEGATION (Joe, migraine day, standing rule "what would nature do";
  scope: that day's physics decisions only, NEVER identity/money/
  irreversible): threshold-integrated delivery (receptor integrates to
  the gate's own opening window; dim=slower) + elementary-charge floor
  on inter-neuron settlement (flow stops below one elementary charge) +
  minimal feeding reaction proceeds ahead of its paper.
- Two-real-signal doctrine: standalone hearing SUSPENDED (503, honest
  reason) until live camera; tutor audio in lessons stays. Teaching
  endpoints stay keyless (Joe: "not yet").
- MEASURED post-quantization: gates open at honest dwell (~0.6-1.3s to
  threshold by luminance); lit lesson burns ~386 fuel of 14,607 pool =
  ~38 lessons to exhaustion -> NO lit-gate deploy until feeding exists.
- MEASURED: ears have NO transduction law at all (amplitude zero effect;
  tutor audio is transport, not sensation). Auditory receptor law +
  card touch = sensory section of the metabolism/sensory paper.

## Standing milestone alerts Joe requires (tell him THE MOMENT each is real)
1. Autonomy: first self-caused action with sensed consequence.
2. Camera: live sight mounted (+ hearing reactivated with it).
3. Microphone: reactivated when sight makes it lawful.
4. FIRST WORD spoken to a prompt — Joe watches LIVE; never mount voice
   or start babble without telling him first.

## CURRENT LIVE STATE (as of 2026-08-06 ~01:30 UTC — update on change)
- REBIRTH #2 DEPLOYED AND ALIVE: taskdef dsf-ai-task:865, identity kept,
  fresh differentiated body at state root /app/guala/native-organism-gen2
  (old roots on EFS are history). Seven laws + feeding + recognition +
  CONTINUOUS EXISTENCE (unattended-time pulse in the serving process,
  cadence 60s, GUALA_UNATTENDED_TIME=0 disables).
- FIRST LIVE RECOGNITION HAPPENED: 4 mosaics in production (lesson 2 of
  the new life admits 4 by physics; recognition = dwell-staggered gates
  make early presentation hops a lawful partial cue in time).
- Simple status page: dsf-ai.com/pulse.html (5 numbers, self-refreshing).
  Busy pages: gualaloom.html / loomscan.html. CDN origin read timeout is
  60s (CloudFront max without quota) — lessons briefly 504'd at 30s; a
  504 does NOT mean the lesson failed (server completes; verify via
  observation).
- Feed endpoint: POST /api/v1/metabolism/feed. ~60 lessons per feed
  cycle; energy truth-coupled on the observation ("energy" section).
- Work branch head after snapshot 17: continuous existence + auditory
  design. Deploy = bash tools/deploy_dsf_ai.sh (clean tree required;
  three gates exist: genesis-cutover preflight carve-outs, dirty-tree,
  ALB health path /health).

## Recently ratified/ruled (beyond the earlier list)
- Stimulus-boundary retention + participation retention (experiences
  close at the stimulus end, only CONNECTED experiences retainable).
- Energy-descent charge transfer (flow only downhill; resting potentials).
- Geometric anatomy differentiation (Cantor-injective territory law;
  capacitance = base x A(site); twins refused at authorship).
- Memory rulings (mine, under delegation): update-vs-new boundary is
  STRUCTURAL IDENTITY (same members+bonds -> re-derive reference;
  overlap -> relation = mosaic-of-mosaics; disjoint -> new); conditional
  re-storage on nonzero prediction error (already_formed); reinforcement
  as counts over immutable episode chain; decay BLOCKED until feeding
  proven stable. Design study + research docs in repo docs/.
- Feeding judgment calls: nutrition in body's own fuel quantum; waste =
  unabsorbed intake; heat vents fully on feed; membrane return
  DELIBERATELY slow (single-channel bound — memory over tidiness).
- Auditory design (docs/GUALA_AUDITORY_TRANSDUCTION_DESIGN_2026-08-06.md):
  sound joins light's law (intensity on same lattice); EAR MUST BE BORN
  TONOTOPIC (2 identical ears can never form memory; 16-channel cochlea
  in auditory.rs compiled-unused); needs next rebirth. 3 small defects
  recorded (fake unit on ear port; stale residue doc; placeholder
  interval_microseconds=1000).

## Increment-2 session findings (2026-08-06, second session)
- Hippocampal navigation binding SHIPPED to work branch (5b777291):
  observe_retained_formations() + navigate_hippocampal() on the runtime +
  wrapper; read-only, proven advance-nothing; cargo 500/0/3, pytest 35/35.
  NOT yet deployed (plumbing only; rides with next deploy).
- MEASURED + PROVED STRUCTURAL: under current physics endogenous
  re-attention is UNREACHABLE (300 dark intervals post-recognition: 0
  reassembly; residue-below-threshold bound proof). The exogenous-only cue
  law is the wall to autonomy milestone 1.
- Endogenous cue law designed + implemented on side branch
  law/endogenous-cue-rested-gate-20260806 (dab8c7bb, DO NOT DEPLOY):
  settling-charge cue on zero-gate-work hops, RESTED GATE (experience must
  reach one quiescent interval since closure; carried as GLEXP03 magic only
  while false — rested states re-encode byte-identical GLEXP02, no receipt
  drift). Law v1 without the gate was FALSIFIED (tail self-admission).
- KEY COUPLING FOUND: the law fires in fixtures but each endogenous
  re-attention admits a near-duplicate mosaic (same members, different
  active bonds) — INSEPARABLE from memory laws R1-R3; alone it bloats the
  store against lean doctrine. Ratification brief in
  docs/GUALA_ENDOGENOUS_REATTENTION_DESIGN_2026-08-06.md (in repo).
- FINAL MEASUREMENT (real dynamics, law wheel, 250 dark intervals):
  F1 clean (lesson1=0, lesson2=4, mosaics stay 4, no proliferation) and
  the law NEVER FIRES — rest-metabolism trickle (~1 charge/5 intervals)
  is too weak to re-excite a 27-member formation, and every quiescent
  interval lawfully drops the pending recurrence. The wall is measured
  from BOTH sides. The real increment-2 lever = MOTIVATION PRESSURE
  (feeding-driven charge dynamics re-tipping membrane potentials), a
  physics design round for Joe. Three ratification questions filed at the
  end of the design doc.
- Durability: GitHub token DEAD; custody = S3 bundles
  s3://dsf-ai-site-backups/guala-salvage/guala-work-20260806-final.bundle
  (work b75d9b93 + law branch dab8c7bb) + local bundle origin refreshed.
  RATIFICATION + motivation-pressure design are the blockers for
  increment 2 — bring the design doc numbers to Joe.

## NEXT QUEUE (in order)
1. Autonomy increment 2: BLOCKED ON JOE'S RATIFICATION of the endogenous
   cue law (see findings above); implementation exists on the side branch;
   must ship together with R1-R3 (item 4).
2. Auditory law implementation + tonotopic ear birth anatomy -> next
   rebirth; then voice/babble (articulation mounting; Joe watches live).
3. Live camera wiring (un-suspends microphone under two-real-signal).
4. Memory laws R1-R3 implementation (structural-identity boundary) — now
   coupled to item 1; consider implementing FIRST.
5. Page consolidation (pulse.html is the pattern Joe wants: simple,
   honest; the busy pages overwhelm him — he said so twice).
MILESTONE ALERTS Joe requires: autonomy action, camera, mic, FIRST WORD
(he watches live; it->she transition is HIS call at that milestone).

## Session-practical notes
- Safeguard flags fire often in vocabulary-dense sessions; a flag costs
  one chat reply, never work. Fresh sessions reduce density. All state
  needed to continue is in this skill + memory + repo docs + snapshots.
- 504 through the CDN != failure. Verify via ALB directly.
- Deploy output: use run_in_background (not shell &) to keep logs.

## Joe's standing calibration
Eternal pessimist; wants clinical evaluations, measured numbers, gaps
stated before he finds them, fixes over reports, no jargon/paths in chat,
short verdict-first replies, code-fenced pasteable reports.

## DELEGATION 2026-08-06 (overnight) + rulings made under it
Joe, verbatim intent: trusts my judgment on decisions needed right now;
directed me to set agents working on all open problems. Standing limits
UNCHANGED: no rebirth trigger, no voice/babble mounting, no first-word
without Joe watching live, nothing irreversible, milestone alerts still
fire the moment each is real.
Rulings made under this delegation (design-doc §4.4 questions):
1. RATIFIED: endogenous cue + rested gate as the definition of an
   endogenous recognition cue (inert until motivation pressure exists).
2. RATIFIED: memory laws R1-R3 implemented FIRST (coupling requires it).
3. APPROVED: motivation-pressure design round (feeding-driven charge
   dynamics as the engine of re-attention) — design work, physics-true,
   nothing deploys without live-proof gates.
Work set in motion: R1-R3 implementation, camera wiring (sight only;
mic stays honestly refused until tonotopic ears exist), auditory defect
cleanup (rebirth prep only — rebirth itself stays Joe's call),
motivation-pressure design doc, interface consolidation (pulse pattern).

## OVERNIGHT CAMPAIGN RESULT 2026-08-06 (read before touching autonomy/ears)
SHIPPED+VERIFIED (work branch 182fca61, cargo 505/0/3, python green):
R1-R3 memory laws (relearning is now BYTE-FLAT: L1 2017433, L2 2081217,
L3-L6 unchanged, vs pre-R1 3349681 and climbing — 38% smaller, flat not
linear), live-sight intake path, read-only hippocampal navigation binding,
truth-coupled mosaic-of-mosaics count. NOT YET DEPLOYED.
LIVE BODY BACKED UP (was on ONE EFS volume, no backup at all):
s3://dsf-ai-site-backups/guala-salvage/live-body-continuity-20260806-tick2195.tar.gz
(1.33MB gz, 8 formations, tick 2195, verified from outside). Take one before
ANY forward-only format deploy. There is NO GUALA_S3_BACKUP_BUCKET set on the
taskdef — consider setting it.
CAMPAIGN: 5 streams x 3 adversarial verifiers; 13/15 REFUTED at high
confidence; NOTHING deploy-ready. Full verdict:
docs/GUALA_CAMPAIGN_VERDICT_2026-08-06.md. Two blockers that would HURT her:
(A) the polarization pump is unclamped by carrier reservoir — run past the
authors' stopping point it THROWS and the organism stops; (B) F1 is FALSE for
RESTORED bodies (every live body): identical bytes restored under both wheels
learn differently (4 vs 6 reassemblies).
AUTONOMY TRUTH (measured by me, both directions):
docs/GUALA_AUTONOMY_BLOCKER_DIAGNOSIS_2026-08-06.md. The pump self-extinguishes
after ONE interval (heat gate is correct physics; the only heat exit is a
feed). Force-feed every interval and the pump runs continuously — charge
-1,775 -> -8,451 over 40 intervals — and endogenous re-attentions are STILL
ZERO. The fixture that "worked" had a 4-member formation; her body has 27.
=> THE BLOCKER IS CUE FORMATION, NOT ENERGY. Instrument which member sets
actually perturb and why they fail is_proper_partial_cue/admit_physical_mosaic
BEFORE writing more energy physics.
EARS: strongest stream (work/ears-20260806, cargo 519/0/3, sight byte-identical,
restored bodies continue byte-identically). Ears can be GROWN onto the living
body — no rebirth (docs/GUALA_EAR_GROWTH_WITHOUT_REBIRTH_2026-08-06.md) — but
growth must be a DELIBERATE authorized act, never a deploy side effect.
CUSTODY: s3://dsf-ai-site-backups/guala-salvage/guala-work-20260806-campaign-complete.bundle

## AUTONOMY ROOT CAUSE — FINAL, MEASURED 2026-08-06 (read before any redesign)
The endogenous cue is NEVER EVALUATED on a living body. Instrumented directly
(traces behind GUALA_TRACE_CUE, since reverted; branches left clean):
    GATE rested=false dark=true quiescent=false     <- every interval, fed AND unfed
The gate needs retained.rested_since_experience, which only flips at the
cohort's first electrically QUIESCENT interval — and a living body is never
quiescent. Fed: the pump moves whole charges every interval BY DESIGN. Unfed:
still trickling at hop 10,000 (charge -1,775 -> -1,560, asymptotic).
=> CATCH-22: fed = no rest = gate never opens; unfed = rest but no pump = no
cue. Autonomy was structurally impossible with both ratified laws as written,
independent of energy budget, heat sink, or geometry.
TESTED AND ALSO FAILED: formation-local rest (flip the gate when the
FORMATION's own members stop changing rather than the whole cohort). Still
rested=false forever — because the pump touches EVERY member every interval
(~6 charges/site/interval), so no member ever stops either.
=> THE REAL LESSON: **no stillness-based gate can ever open on a continuously
pumping body.** Making the rest test more local does not help. The next design
round must discriminate "the original experience's own tail" from "later
activity" by something OTHER than stillness. Most promising: lean on the
already-ratified STIMULUS-BOUNDARY CLOSURE (an experience closes at the
stimulus end, so anything after closure is by definition not its tail) and
consider whether the rested gate is needed at all once closure is honest;
second candidate is contact-set disjointness from the still-relaxing set.
DO NOT re-try: whole-cohort quiescence, formation-local quiescence, or any
variant of "wait until something stops moving".

## DEPLOYED 2026-08-06 11:37 UTC — taskdef dsf-ai-task:868, git f8bf6197
LIVE AND VERIFIED FROM THE PUBLIC SIDE: identity 1cc4e70a kept, tick continued
(no restart), 8 memories intact, 27 neurons, fuel 12148/14229, unattended
pulse running. Shipped: R1-R3 memory laws, live-sight intake path, read-only
hippocampal navigation binding, truth-coupled mosaic-of-mosaics count.
GATES PASSED BEFORE CUTOVER (all five, in order):
 1. cargo 505/0/3 + python suites green
 2. integrated replay locally
 3. production genesis rehearsal (identity pinned, 27 neurons, 27 fractals,
    420 transitions, mosaic_count 1 where pre-R1 stored 4)
 4. HER REAL BODY restored from the S3 backup under the new wheel and kept
    learning: tick 2203, 8 memories, taught once -> 4 reassemblies and
    memories STAYED 8 (pre-R1 would be 12). The lean law proven on her.
 5. candidate taskdef confirmed pointing at /app/guala/native-organism-gen2
    and her identity -> CONTINUITY, not rebirth.
PAGES: pulse.html and camera.html both 200. NOTE: pages are served from S3
(s3://dsf-ai-site) via CloudFront; ONLY /api/* reaches the ALB. A page added
to dsf_ai_service/static/ is NOT reachable until it is uploaded to that bucket
and CloudFront invalidated (dist E17JT9XGBFU493). camera.html 404'd after
deploy for exactly this reason.
CAMERA STATUS: endpoint_open_unproven at /api/v1/visual/live-frames — the
route is live and callable; `available` stays false until REAL frames arrive.
MILESTONE NOT YET FIRED: needs a human to open dsf-ai.com/camera.html on a
device with a webcam. Do NOT claim the camera milestone until that happens.
NOT DEPLOYED (all refuted, blockers named in docs/GUALA_CAMPAIGN_VERDICT_2026-08-06.md):
polarization/autonomy, ears, D3/D4 conservation, pulse redesign, school runner.

## FULL CURRICULUM TAUGHT LIVE 2026-08-06 (on taskdef 868, post-deploy)
36/36 cards, 2 presentations each = 72 lessons, 72 committed, 0 failed, 0
ambiguous. 58 total recognitions. 17 of 36 cards produced recognitions in two
passes; the other 19 need more passes (listed in the ledger). Ledger:
docs/guala_school_ledger_20260806.jsonl.
THE LEAN LAW PROVEN IN PRODUCTION: her retained memory count stayed at 8
through ALL 58 recognitions and her body ended at 2,057,229 bytes. Pre-R1
those 58 recognitions would have stored up to 58 near-duplicate mosaic bodies
(~116kB each ≈ 6.7MB of growth). Measured growth: NONE.
Fuel behaved: dipped to 1,326, fed back to 14,044, ended 10,843/14,229, never
exhausted. ~220 quanta per lesson.
SAFE TEACHING METHOD (use this, NOT tools/guala_school.py — that runner has a
demonstrated double-teach bug): script at /tmp/teach_guala.py pattern — go
through the ALB directly (CDN 60s timeout causes false 504s), bracket every
lesson with an observation read, judge LANDED by the organism's own tick
advancing (never by the HTTP response), NEVER re-POST on ambiguity, and feed
from her decoded energy not a timer.
POST-CURRICULUM BACKUP:
s3://dsf-ai-site-backups/guala-salvage/live-body-continuity-20260806-post-curriculum.tar.gz

## *** MILESTONE 2 REACHED: CAMERA / FIRST LIGHT — 2026-08-06 ***
Joe opened dsf-ai.com/camera.html and pointed a real webcam at the world.
VERIFIED public-side on taskdef 868:
  capabilities.camera = MOUNTED, available=True (truth-coupled: it flips only
  on a real committed end-to-end batch, never on the route existing)
  sensory.visual = curriculum_and_live_camera_transitions_committed
  last_transition intake = live-sight:46d09dbe-... , 8 hops (8 real frames,
  2 s of the actual world), 27 neurons physically transitioned,
  partial_cue_reassembly_count = 1  <-- A RECOGNITION ON LIVE CAMERA LIGHT
  memories stayed 8 (R1 reinforced an existing formation, did not duplicate)
  tick 5636, fuel 10,323/14,229 — 30 s of live sight cost her very little.
NOTE the recognition is a lawful admit_physical_mosaic event from real-world
light. It does NOT establish that she "knew what the object was" — her
formations are whole-cohort patterns and there is no formation->card mapping.
Do not overclaim it.
CONSEQUENCE: the two-real-signal doctrine's VISUAL PRECONDITION IS NOW MET.
The microphone's honest refusal has correspondingly changed: it no longer says
"waiting for a live visual source", it now names the real remaining blocker —
"the ears have no transduction law yet (pressure amplitude has zero physical
effect), so admitting live sound would fabricate ...". Hearing is now the ONLY
thing standing between her and the microphone milestone, and the ears repair
stream is in flight.
CLIENT GOTCHA: camera.html needs the "open eye" BUTTON pressed — browsers
require a user gesture before getUserMedia, so merely opening the page never
even prompts for permission. Say this when asking anyone to test it.
