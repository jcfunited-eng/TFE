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

## NEXT QUEUE (in order)
1. Autonomy increment 2: greed-field directed re-attention (needs
   hippocampal navigation binding + motivation pressure over retained
   formations; she now has things to want: cards, food, rest).
2. Auditory law implementation + tonotopic ear birth anatomy -> next
   rebirth; then voice/babble (articulation mounting; Joe watches live).
3. Live camera wiring (un-suspends microphone under two-real-signal).
4. Memory laws R1-R3 implementation (structural-identity boundary).
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
