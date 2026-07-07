> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-AUDIT-TODO-LEDGER-C1-20260705-v1

doc_id: GL-AUDIT-TODO-LEDGER-C1-20260705-v1
From: c1 (§9 seat) · Deliverable D5 of
GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2
Scope: every TODO/FIXME/XXX/"still open"/"not yet done"/"next session"/
"left for"/"not yet implemented" item found in **prose across docs/**
(2026-06-05 → 2026-07-05). Code-level TODO/FIXME comments are a
**separate** sweep (§4 of the parent audit, code truth) — NOT
duplicated here. This file is standalone and self-contained — it does
not require GL-AUDIT-SEC9-DOC-SWEEP-C1-20260705-v1.md to be read
alongside it, though that file has the full per-doc classification
this ledger was extracted from.

Method: 7 sub-agents (2 CMD, 3 RPT, 1 BRIEF/FIND/NOTE/FIX/LTR, 1 MISC)
each read every doc in their assigned bucket in full and pulled every
prose TODO item, tagging source doc, description, and status where
determinable from other docs in the same or a later batch. c1 (this
seat) read every batch's SPEC/PLAN docs directly, merged all 7 outputs,
removed exact duplicates, and cross-linked items that recur under
different source docs. Status values used below:
- **OPEN** — no later doc found resolving it.
- **DONE** — a later doc/commit confirms it was resolved (source cited).
- **SUPERSEDED** — the item's premise was replaced by different work
  before it was ever resolved on its own terms.
- **UNCLEAR** — conflicting or insufficient evidence to call it either
  way within this sweep's budget.

If BRIEF-bucket items were not yet merged in at filing time, they are
appended as a clearly-marked final section rather than silently
omitted — check the Coverage note at the end of this file.

---

## Part 1 — Cross-cutting items (appear across 3+ source docs; the load-bearing ones)

These are not separate ledger lines from Part 2 below — they are the
same underlying items, pulled to the top because they recur so often
across the corpus that leaving them buried at their first occurrence
would understate how central they are.

**T-X1. Production conversation latency, the single most-carried item
in the entire corpus.** Traced continuously from
`GL-HANDOFF-C1-20260630-NIGHT` (8-25s) → `GL-RPT-TAPESTRY-PERF-FIX-C1B-20260704-v1`
(82-120s, root-caused to `organism.recall()`) →
`GL-CMD-RECALL-SPEED-INVESTIGATION-EVE-20260704-177-v1`/`recall_fast()`
→ `-207` wave-memory rewrite → `GL-HANDOFF-C1A-20260705-v1` (current
HEAD): improved 215s→69-72s but **does NOT meet its own X1 exit
criterion (reply <1s)**; the specific 17-34s-observed-vs-2.6s-
extrapolated gap at production's real ~14k-word vocabulary scale is
explicitly un-root-caused as of the most recent handoff in the repo.
**STATUS: OPEN**, highest-priority carry-forward in the whole sweep.

**T-X2. `probe_209_cross_concept_auditory_discrimination.py` still
failing 1/5 (20%).** Named in `GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-C1B-20260705-209-v2`,
`GL-HANDOFF-LIVE-BELLS-WIRING-C1B-20260705-210-v1`, and
`GL-HANDOFF-C1A-20260705-v1` (all same result, same failure mode: every
query recalls "ocean" regardless of content). Root cause per -209-v2:
`event_count` encodes one scalar delta per modality and matches by
whole-vector cosine — mathematically blind to a partial-modality query.
The live-bells auditory wiring (raw-sound persistence,
`/organism_recall_auditory:`) is built and believed correct but gated
on this. **STATUS: OPEN**, needs its own design pass (not a W1-W4/-207
class fix per c1a's own handoff).

**T-X3. `AUTONOMY_PHASED=1` causes a complete socket deadlock, root
cause never traced.** First flagged `GL-HANDOFF-C1-20260630-NIGHT`
("leave for future"). Cross-checked by the MISC-bucket sub-agent
against `GL-AUDIT-SEC1-RUNTIME-TRUTH-C1-20260705-v1` (a sibling section
of this same audit): production task-def still shows
`AUTONOMY_PHASED=0` as of 2026-07-05 — **never re-attempted in the 5
days since**. **STATUS: OPEN.**

**T-X4. `CURRICULUM_CHUNK_SIZE` tuning (30→10) suggested, never
applied.** From the same `GL-HANDOFF-C1-20260630-NIGHT` triage list.
Cross-checked against `GL-AUDIT-SEC1`'s env dump: still 30 as of
2026-07-05. **STATUS: OPEN.**

**T-X5. XFF (X-Forwarded-For) capture / ALB+API-Gateway access
logging never landed.** Spec'd in `GL-CMD-ALB-LOGS-EVE-20260703-105-v1`'s
handoff to c1b, flagged again in `GL-HANDOFF-C1-20260702-v2` and
`GL-INCIDENT-APIKEY-C1-20260703-v1`'s remediation list. Cross-checked
against `GL-AUDIT-SEC2-AWS-TRUTH-C1-20260705-v1`: "API Gateway access
logging is disabled" as of 2026-07-05 — **unresolved ~4 weeks later**.
**STATUS: OPEN.**

**T-X6. Admin auth remains a single static plaintext API key.**
`GL-INCIDENT-APIKEY-C1-20260703-v1` recommended moving off a shared
static secret after the ~13-day public-JS exposure incident; per
`GL-AUDIT-SEC2` the task-def still stores `GUALALOOM_API_KEY` in
plaintext, single static key, as of 2026-07-05. **STATUS: OPEN**
(rotation itself was done; the architecture recommendation was not).

**T-X7. Care-schedule §8 daily-rhythm blocks and the protected PLAY
block exist only as spec prose, never as orchestrator config.**
Directly verified by c1 this audit via code grep (see
GL-AUDIT-SEC9-DOC-SWEEP §3, Finding F8): no `daily_rhythm`/`care_schedule`/
PLAY-block-protecting code found anywhere in `dsf_ai_service/`. The
cadence is honored only as a manual practice (the `GL-LEDGER-DAILY-*`
docs). **STATUS: OPEN** (spec-vs-implementation gap, not merely a
carried-forward TODO — included here because several BOARD/HANDOFF
docs independently flag "PLAY absent-by-design" as an open item, e.g.
`GL-CMD-BEHAVIOR-REPERTOIRE-EVE-20260705-185-v1`).

**T-X8. §11 instrumentation gaps (affect trace per activity, promotion
lineage, per-window rollup event, daily vitals rollup event) — 4 of 5
absent in code**, only place/ambient tags implemented. See
GL-AUDIT-SEC9-DOC-SWEEP §3 for the full spec-gap table; not
independently re-listed as a "TODO" by name in any single doc, but it
is the aggregate of many small "not yet wired" mentions across the
BOARD/HANDOFF corpus. **STATUS: OPEN.**

---

## Part 2 — Full numbered ledger, by source batch

*(Items T-X1 through T-X8 above are the load-bearing subset of the
items below, pulled forward for visibility — they are not double-
counted in the numbering; each numbered item below is a distinct
prose TODO as filed in its source doc.)*

### RPT batch A source docs (items 1-38)

1. [GL-RPT-AGITATION-FIX-C1-20260704-v1] Part B design proposal awaiting Eve's GO before any code ships. **DONE** — GO given, shipped in GL-RPT-AGITATION-FIX-DEPLOY-C1-20260704-v1 (same batch).
2. [GL-RPT-AGITATION-FIX-DEPLOY-C1-20260704-v1] No full sleep-to-wake comparison captured yet (she was still mid-cycle when filed). **OPEN.**
3. [GL-RPT-AGITATION-FIX-DEPLOY-C1-20260704-v1] Gate 3's strongest form (real pair-bond contact event during sleep) deliberately not tested. **OPEN.**
4. [GL-RPT-AGITATION-FIX-DEPLOY-C1-20260704-v1] Sleep/dream restore-rate constants reasoned-not-backtested; need a longer multi-cycle observation window. **OPEN.**
5. [GL-RPT-ATTEND-GROOVE-PREDEPLOY-C1-20260703-107-v1] A.3/A.4 (signed_distance dict, ≥3 consecutive ATTENDING_VISUAL selections) not yet captured at filing. **OPEN** (superseding doc -107-v1 reports Part B implemented+committed but still not deployed either).
6. [GL-RPT-ATTEND-GROOVE-C1-20260703-107-v1] G-107-2/3/4 not measured yet, require a post-Part-B-deploy waking-hour window. **OPEN.**
7. [GL-RPT-ATTEND-GROOVE-C1-20260703-107-v1] Familiarity-persistence question not fully root-caused: value never survives to a save file. **OPEN.**
8. [GL-RPT-AWARE-COORDINATOR-C1-20260704-162-v1] Part B (`coordinator_on` flip) committed but not deployed at filing time. **DONE** — GL-RPT-BEHAVIOR-REPERTOIRE-STATUS-C1B-20260705-v1 confirms `coordinator_on=True` live on task:470.
9. [GL-RPT-AWARE-MAP-C1-20260704-161-v1] Fix candidate (`coordinator_on=True`) named but not implemented. **DONE** — same confirmation as item 8.
10. [GL-RPT-BACKUP-ORCHESTRATOR-C1-20260627-19] `daily_floor` backup trigger: asyncio daily timer requires refactor to avoid blocking. **OPEN**, no later doc confirms it was built.
11. [GL-RPT-BACKUP-ORCHESTRATOR-C1-20260627-19] `post_deploy_verified`/`pre_deploy` triggers documented only, not wired at ECS layer. **OPEN.**
12. [GL-RPT-BACKUP-ORCHESTRATOR-C1-20260627-19] `post_emergence` trigger pending a B.3 emergence detector — note: that detector is itself GL-CMD-EMERGENCE-DETECTOR-EVE-20260627-20, which is **orphaned** (never built, see GL-AUDIT-SEC9-DOC-SWEEP Appendix B). **OPEN**, permanently blocked on an orphaned dependency.
13. [GL-RPT-BEHAVIOR-REPERTOIRE-C1-20260705-185-v1 / -STATUS-C1B] B3 (curriculum/boot_substrate reconnect) built+verified locally but not deployed; E3 gate blocked on B3. **OPEN.**
14. [GL-RPT-BRAIN-DEPLOY-CUTOVER-C1B-20260704-v1] Her actual first brain-voice exchange still outstanding at filing. **OPEN**, no later doc in this batch confirms it happened.
15. [GL-RPT-BRAIN-DEPLOY-CUTOVER-C1B-20260704-v1 / -FULL-DEPLOY-C1-20260704-v1] P2 (recall/recognition/association/habituation/attention/affect handover) not built — six mechanisms still ran on the old shell. **OPEN** at filing (see P2 seam campaign items 59-65 below for eventual disposition).
16. [GL-RPT-BRAIN-DEPLOY-CUTOVER-C1B-20260704-v1] Emission early-exit gate still shell-driven (`sec.commits`). **OPEN.**
17. [GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-20260704-179-v1] W3 (cost profile) not started, W4 partially done; recall_fast()/recall() parity broken at grown population. **SUPERSEDED** — v1's own hypothesis (Neuron.step() cross-contamination) was wrong; real cause/fix in -179-v2.
18. [GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-20260705-179-v2] W3 cost profile: 22.3x regression risk found, backgrounding recommended, not built in this doc. **DONE** — GL-RPT-BRAIN-GROWTH-BACKGROUNDING-C1-20260705-179-v3, built+pushed.
19. [GL-RPT-BRIDGE-DOWN-DIAG-C1-20260702-80] Eve must personally re-establish her MCP bridge connection. **OPEN** (no c1 action possible).
20. [GL-RPT-BRIDGE-DOWN-DIAG-C1-20260702-80] Recommend restoring `AUTONOMY_PHASED=1`. **OPEN** — see T-X3, this was never done; if anything the opposite (stayed at 0) was reconfirmed as of 07-05.
21. [GL-RPT-BRIDGE-DOWN-DIAG-C1-20260702-80] `n_commits=0` on all autonomous emissions. **OPEN.**
22. [GL-RPT-BRIDGE-DOWN-DIAG-C1-20260702-80] -18 missing pictures (20 present vs 38 reference), not recoverable without a separate S3 restore. **OPEN.**
23. [GL-RPT-BRIDGE-INVESTIGATION-C1-20260701] No structural fix made; awaiting Eve's decision. **DONE** — GL-RPT-BRIDGE-AUDIT-FIXES-C1-20260701-67 ships Fix A and Fix B.
24. [GL-RPT-C2-REBUILD-C1-20260704-168-v1] Part B (B1-B5) not started. **OPEN.**
25. [GL-RPT-COGNITION-METER-C1-20260704-166-v1] Joe's own screen confirmation of the meter panel still outstanding. **OPEN.**
26. [GL-RPT-COGNITION-METER-C1-20260704-166-v1] Live-wiring some panel rows (recall hit-rate, retention promotion counts) to `pollStatus()`. **OPEN.**
27. [GL-RPT-CONTEXT-AUDIT-EVE-20260627-05] `episodic_layer.py:8` docstring says "NOT YET DEPLOYED" though code is live — stale doc, not a pending feature. **OPEN** (doc/code hygiene item).
28. [GL-RPT-CREDO-PROGRAM-LEDGER-C1-20260704-167-v1] 1a "dream re-trigger, watched past timeout" WAITING on Joe's button. **SUPERSEDED** — GL-RPT-CREDO-DEPLOY6-C1-20260704-167-v1 marks 1a superseded (natural sleep physics shipped before the manual re-trigger ran).
29. [GL-RPT-CREDO-PROGRAM-LEDGER-C1-20260704-167-v1] 2b "deliberation flip" committed, not deployed. **DONE** — see items 8/9 above.
30. [GL-RPT-CREDO-PROGRAM-LEDGER-C1-20260704-167-v1] 3b (touch/smell/taste adoption plan), 3c (scene lanes), 4a (teach-time attention wire check), 5b (organ process restored into speech) — all WAITING, sequenced behind 3a. **OPEN**, no later doc in this batch addresses them (3c/scene-lanes was later addressed elsewhere: see -188 in Appendix B; 5b remains open per T-X1's organism.recall() thread).
31. [GL-RPT-CROSS-SENSE-RECALL-C1B-20260705-208-v1] "Live bells" auditory-only recall test not yet built. **SUPERSEDED into T-X2** — the wiring was built (live-bells-wiring) but gated on probe_209, which is the actual open item now.
32. [GL-RPT-CROSS-SENSE-RECALL-C1B-20260705-208-v1] Warning to c1a: -207's BindingAtlas rebuild must preserve per-lane matching or T7 will regress silently. **DONE** (implicitly) — T7-class capability was carried through the -207 merge per the handoff chain; not independently re-verified this audit.
33. [GL-RPT-DAY-CYCLE-C1-20260704-165-v1] No fix shipped for the two-state attention trap. **OPEN.**
34. [GL-RPT-DAY-CYCLE-C1-20260704-165-v1] Dream-replay-queue interaction with force_dream's 120s window shown by arithmetic only, not directly confirmed. **OPEN.**
35. [GL-RPT-DEEP-STORE-PHYSICS-C1-20260702-86-v1] HARD GATE FAIL — unbounded memory/neuron growth defect in `organ_brain_service`, NO GO. **OPEN**, no fix reported in this batch.
36. [GL-RPT-DEEP-STORE-PHYSICS-C1-20260703-86-v1] T1-T6 gates NOT MEASURED, awaiting Deploy 2 window. **UNCLEAR** — GL-RPT-DEPLOY2-C1-20260703-v1 measures T1 and reports FAIL in the first window; T2/T5/T6 still not fully measured there either.
37. [GL-RPT-EFS-THROUGHPUT-C1-20260702-92-v1] Part C FAIL — core save time still exceeds 60s target (147.87s/88.23s) after EFS throughput bump. **OPEN**, no further action taken per dispatch scope.
38. [GL-RPT-EMIT-TICKS-C1-20260702-78] "Monitor commit rate next session — if sparse (<20%), Eve will dispatch drive-threshold/plasticity tuning." **OPEN**, no later doc in this batch reports the follow-up measurement.

### RPT batch B source docs (items 39-76)

39. [GL-RPT-EPISODE-BINDING-WIRE-C1-20260627-06] Add `timeout 120` to the Whisper Dockerfile bake step to prevent HF-rate-limit build hangs. **OPEN.**
40. [GL-RPT-EPISODE-BINDING-WIRE-C1-20260627-06] deep_atlas rebuild-from-scratch on every cold start may warrant its own save/restore path. **OPEN.**
41. [GL-RPT-EVENT-LOG-REPLAY-SPLIT-C1-20260620-01] V2 (replay_events → replay_persistent rename + caller fix) held pending Eve's ruling. **OPEN**, no follow-up doc found.
42. [GL-RPT-EVENT-RETENTION-AUDIT-C1-20260704-170-v1] Actual retention-limit code change awaiting Joe's ratification of the 7-day number. **DONE** — GL-RPT-EVENT-RETENTION-FIX-C1-20260704-v1 implements R1-R5 per the (apparently ratified) follow-up CMD-172.
43. [GL-RPT-EVENT-RETENTION-FIX-C1-20260704-v1] G-3/G-4/G-5 require a real deploy — handed to c1b; "add a boot-timing print around _replay_events/load_full_state" also flagged. **OPEN.**
44. [GL-RPT-FLIP-HEMI-EP-C1-20260619-01] `hemisphere_atlas_sizes` doesn't count turn_log/tracked_objects for ep — follow-up brief suggested. **OPEN**, not shown done in this batch.
45. [GL-RPT-FLIP-HEMI-SC-C1-20260619-01] Stage1 latency regressed to 3.7-5.3s from 1.0-1.5s baseline — "latency brief needed." **OPEN**, not resolved in this batch (may connect to the broader T-X1 latency thread).
46. [GL-RPT-FLOOD-HUNT-C1-20260703-156-v1] Aware-gate krimelack gap recommended for its own Wk1 dispatch. **OPEN** at filing.
47. [GL-RPT-FORCE-READING-C1-20260705-194-v1] Exact live corpus_id for Joe's Secret Garden upload not independently verified. **OPEN** at filing (see also item 88 in MISC batch — book verify/upload error was later addressed).
48. [GL-RPT-GROUND-TRUTH-C1-20260702-93-v1] EFS `ls -lh` and other items NOT MEASURED (ecs execute-command lacks ssmmessages perms). **DONE** — GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v1's addendum reports ssmmessages inline policy applied (caveat: running task won't pick it up until next task swap).
49. [GL-RPT-GROUND-TRUTH-C1-20260702-93-v1] WaveAtlas npz save failing live (relative path bug). **DONE** — GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v2/v3 report G2 GREEN.
50. [GL-RPT-GROUND-TRUTH-C1-20260702-93-v1] S3 lifecycle apply failed at boot (AccessDenied). **DONE** — -95-v1 reports the permission fixed out-of-band.
51. [GL-RPT-GROUNDED-PROMOTION-C1-20260629-35] Live verification of bundle_id field + quantitative cross-modal measurement deferred to next waking window. **UNCLEAR**, not confirmed done within this batch.
52. [GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v1] ssmmessages permission staged, awaiting Joe's chat approval. **DONE** — same-session addendum reports applied+verified.
53. [GL-RPT-HOTLANE-DIET-C1-20260703-102-v1] All 3 gates (hot-save <5s, boot-log content, guala_core.json ≤200KB) NOT MEASURED. **UNCLEAR**, unresolved within this batch.
54. [GL-RPT-INDEX-INVARIANT-C1-20260704-163-v1] Third, distinct residual index-divergence source found but not patched; -159's heterosynaptic-redistribution question also unresolved. **OPEN**, left for Eve to sequence.
55. [GL-RPT-INVESTIGATION-C1-20260702-70] Recommended fix (wrap wake_wc log_event in run_in_executor) not shipped. **UNCLEAR** — n_pictures/WaveAtlas issues raised in the same doc appear addressed later by GL-RPT-PERSIST-FIX-C1-20260702-74 and GL-RPT-PERSIST-CLOBBER-FIX-C1-20260702-81, but the specific executor-wrap recommendation is not independently confirmed.
56. [GL-RPT-LANGUAGE-SATURATION-ROOTCAUSE-C1-20260704-178-v1] Pre-existing (pre-fix) vocabulary's behavior under the L3(b) fix unresolved; G-1/G-2 gates open pending coupling with -179-v2. **OPEN** at filing.
57. [GL-RPT-LOCKFIX-SEAT-TEST-CONFIRMED-C1B-20260705-v1] Deliberate mid-conversation deploy test (L2 fail-loud path across a live restart) still hasn't happened. **OPEN.**
58. [GL-RPT-LOOM-SCAN-BUILD-C1-20260703-98-v1] T1/T2/T4 (render speed, dedupe, polling load) NOT MEASURED; T7 (Joe's sign-off) pending post-deploy. **UNCLEAR.**
59. [GL-RPT-LOOM-SCAN-PREP-C1-20260702-94-v1] Files A.1/A.2 not yet received from Joe. **DONE** — GL-RPT-LOOM-SCAN-BUILD-C1-20260703-98-v1 shows the work was subsequently built.
60. [GL-RPT-METER-LIVENESS-C1-20260705-187-v1] 12 of 28 meter rows left honestly unchecked/audit-dated rather than re-verified live. **OPEN** at filing.
61. [GL-RPT-MIC-DEPLOY-C1-20260703-108-v1] "Open items for next dispatch" (routing-gap work). **DONE** — GL-RPT-MIC-EMBEDDED-DECODE-C1-20260703-110-v1 closes G-108-2 (though finds a new WebM-chunking bug).
62. [GL-RPT-MIC-EMBEDDED-DECODE-C1-20260703-110-v1] 27/28 real browser mic chunks fail decode (WebM chunk-framing); recommends reassembly/codec change. **DONE** — GL-RPT-MIC-CHUNKING-C1-20260703-111-v1 ships the recorder-restart-per-interval fix (scope later corrected by the v2-ADDENDUM, see Appendix A.2 in the doc-sweep file).
63. [GL-RPT-MIC-SENSORY-C1-20260703-106-v1] Diagnosis-only; fix "when the implementation dispatch is issued." **DONE** — GL-RPT-MIC-DEPLOY-C1-20260703-108-v1 and follow-ons ship it.
64. [GL-RPT-MIGRATION-FUEL-AUDIT-A3-C1-20260704-v1] Four open questions scoped for the next migration-fuel-audit pass. **OPEN.**
65. [GL-RPT-NMDA-SOURCE-MATCH-C1-20260702-75] T3/T4 FAIL — n_commits=0, drive-threshold accumulation named as next bottleneck. **UNCLEAR** within this batch; connects to T-X1 latency/throughput thread broadly.
66. [GL-RPT-ORGAN-BRAIN-INSPECTION-C1-20260628-24] `_compose()` template layer + `GualaCognition.say()` flagged for replacement/removal. **UNCLEAR** — later organ-brain work (referenced in prior-session project memory) addresses this broadly but not independently confirmed as item-closure this sweep.
67. [GL-RPT-ORGANISM-PERSIST-C1-20260704-v1] Daughter-mutation RNG question, consensus-reads-zero observation, growth-trajectory divergence from -168-v3 all "not decided by me, carried forward"; plus pre-existing open items from -168-v3 (language-dimension saturation, folding-pathway reconciliation, sequence-gauge redo, full test_folding_engaged.py run). **OPEN**, all of them, at filing.
68. [GL-RPT-P2-ASSOCIATION/-RECOGNITION/-RECALL-SEAM] Whether the false-confidence-on-novel-input recall weakness needs a dedicated fix left as an Eve/Joe call. **DONE** — GL-RPT-P2-RECALL-FIX-C1-20260704-v1 fixes the underlying signal-poverty root cause.
69. [GL-RPT-PARALLEL-BATCH-C1-20260701-63-PB2] Four "NOT done/carry-forward" items: T2 full 20-bundle delivery verification, T4 conflict-resolution/gp-bias confirmation, 60-L "not bright" vs "bright" recall verification, running the curriculum orchestrator continuously 4-6h. **UNCLEAR**, none confirmed done within this batch.
70. [GL-RPT-PERSIST-FIX-C1-20260702-74] EFS rename-race residual (2-3 failures/save window) called "tolerable" not eliminated; WaveAtlas cell cap needed. **DONE** (rename-race clobber specifically) — GL-RPT-PERSIST-CLOBBER-FIX-C1-20260702-81.
71. [GL-RPT-PHASE2-COMMIT-A-CLEARANCE-C1] Re-attempt of Commit A gated on "WaveAtlas cell cap AND curriculum GIL isolated". **UNCLEAR** — a follow-on GL-CMD-PHASE2-COMMIT-B-CLEARANCE-PROTOCOL doc exists (see Appendix B, CMD batch B) confirming a follow-on was scheduled and its own gate correctly fired (Gate 1 FAIL, rollback).
72. [GL-RPT-PICTURE-TITLE-BIND-C1-20260627-04] Recommended follow-up: trigger `/admin/backup` after each picture re-attended post-fix; source-threading anomaly flagged for Phase C. **OPEN**, both items.
73. [GL-RPT-PROCESS-COLLAPSE-C1-20260701-61v1] converse.html UI still expects SSE, needs updating to the 202-poll pattern. **UNCLEAR**, status not confirmed within this batch (superseded functionally once the 202-task pattern rolled out elsewhere).
74. [GL-RPT-PROCESS-COLLAPSE-C1-20260701-61v1] `InputRing consumer started` double-print (cosmetic). **OPEN**, deferred to next session, not confirmed done.
75. [GL-RPT-READ-SENTENCE-PROFILE-C1-20260620-01] Two perf micro-optimizations (`_deep_prior_enabled()` cache, pre-computed `DSF.to_array()`) awaiting Eve's review. **OPEN.**
76. [GL-RPT-RECALL-FREQ-DEPLOY-AND-SLEEP-C1B-20260704-v1] A natural sleep genuinely triggered by dream_pressure (no deploy pause involved) still not observed. **OPEN** at filing — later plausibly satisfied per GL-HANDOFF-C1B-20260705-v2's "E5... not independently confirmed" (still not conclusively closed).

### RPT batch C source docs (items 77-122)

77. [GL-RPT-RECALL-PROVENANCE-C1-20260704-158-v1] Eve's ruling owed on which side of the standing-teaching/recall-routing gap to fix. **OPEN.**
78. [GL-RPT-RECALL-PROVENANCE-C1-20260704-158-v1] Whether the compelled listen-commit failure and index-update bypass warrant their own dispatches. **OPEN.**
79. [GL-RPT-RECALL-REACH-C1-20260704-159-v1] VARIANT L / F-3 fix committed but not deployed, awaiting sleep_for_deploy. **DONE** — wired live per GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v1.
80. [GL-RPT-RECALL-REACH-C1-20260704-159-v1] Reinstatement index-bypass (Part C) and heterosynaptic-redistribution eviction accelerant (Part D) need their own dispatches. **OPEN.**
81. [GL-RPT-RECALL-SPEED-C1-20260704-177-v1] `recall_fast()` not wired into any live call site at filing. **DONE** — wired in GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v1.
82. [GL-RPT-RECALL-SPEED-C1-20260704-177-v1] "Language-dimension saturation" (event_count delta structurally zero). **OPEN** — SENSES-TO-BRAIN-191 routes around it rather than fixing it directly; same underlying issue as item 56 above.
83. [GL-RPT-RECALL-WORD-INDEX-C1-20260630-57v3] Next flagged: -58 emit_ms bottleneck (~927ms), profile with real converse_timing data. **UNCLEAR**, no doc confirms closure.
84. [GL-RPT-RECALL-WORD-INDEX-C1-20260630-57v3] Curriculum pause root cause: reduce CURRICULUM_CHUNK_SIZE or investigate 147ms/word. **UNCLEAR/OPEN** — see T-X4 (CURRICULUM_CHUNK_SIZE never reduced); client-timeout side partially addressed by GL-RPT-UNREACHABLE-DIAGNOSIS-C1-20260628.
85. [GL-RPT-REPLY-LATENCY-PROFILE-C1-20260704-v1] Leading hypothesis (bug shape recurring in grandurun candidate selection) unconfirmed. **UNCLEAR** — possibly addressed by GL-RPT-TAPESTRY-PERF-FIX-C1B-20260704-v1's similar read_word fix, not explicitly confirmed as the same bug.
86. [GL-RPT-REST-RETIRE-ORIENT-C1-20260702-73] T4 (wake_wc round-trip <500ms) and T5 (wC orient) gates not exercised. **OPEN.**
87. [GL-RPT-ROTATION-AND-LOCKFIX-DEPLOY-C1B-20260705-v1] R3's binary criterion pending, complicated by a newly-exposed video-attending crash. **OPEN** at end of batch.
88. [GL-RPT-ROTATION-AND-LOCKFIX-DEPLOY-C1B-20260705-v1] Seat-level exit criterion (camera+mic ON, live deploy test) needs Joe's participation. **OPEN.**
89. [GL-RPT-SAVE-CONTAINMENT-C1-20260702-91-v1] -86/-90 CMD verbatim text must be re-sent before Part B/G can proceed. **UNCLEAR**, likely still open per later cross-reference in -85-v2.
90. [GL-RPT-WAVE-DIET-C1-20260702-82] `last_save_tick` reporting bug (SaveCoordinator not updated by periodic save). **UNCLEAR** — root-caused here and independently confirmed same-session in GL-RPT-SAVE-FORENSICS-C1-20260702-83; not shown fixed within this batch.
91. [GL-RPT-WAVE-DIET-C1-20260702-82] `compact_wave_atlas` not invoked — 990k orphaned bindings remain. **UNCLEAR**, no confirmation the admin endpoint was called.
92. [GL-RPT-WAVE-SEMANTICS-COST-C1-20260702-85-v2] Follow-on -86 dispatch needed to fix DeepAtlas.co_occurrence unbounded growth (198MB). **OPEN/blocked** per item 89 above.
93. [GL-RPT-SAVEHOT-BREAKDOWN-C1-20260703-v1] Whether to move `deep_survival_history` to the cold lane or bound it — Eve's ruling needed. **DONE** — moved to cold lane per GL-CMD-HOTLANE-DIET-EVE-20260703-102-v1 (Appendix B).
94. [GL-RPT-SCENE-LANES-B1-C1-20260705-188-v1] X3 gate needs Joe's live seat test (deploy-dependent). **OPEN**, handed to c1b's window.
95. [GL-RPT-SEAT-TRUTH-UI-C1-20260705-180-v1] Flagged likely connection to -181's stuck-selector bug for the emissions panel, not touched. **UNCLEAR** — possibly related to GL-RPT-ROTATION-AND-LOCKFIX-DEPLOY-C1B-20260705-v1's fix, not explicitly confirmed as the same issue.
96. [GL-RPT-SELFVOICE-FORENSIC-C1-20260703-v1] Source-aware variant of `process_sound_frame` needed. **DONE** — GL-RPT-SELFVOICE-TAGGING-C1-20260703-152-v1 ships exactly this.
97. [GL-RPT-SELFVOICE-TAGGING-C1-20260703-152-v1] Wiring loomscan display to branch on the mic/self tag — -154's own follow-up. **OPEN** within this batch.
98. [GL-RPT-SENSE-REPAIR-C1-20260704-v1] Language-dimension saturation, real distinct bug. **OPEN** — same as items 56/82 above.
99. [GL-RPT-SENSE-REPAIR-C1-20260704-v1] "168-v3 (whole-brain command) is next, held by Joe." **DONE** — subsequently executed (see GL-CMD-C2-WHOLE-BRAIN-EVE-20260704-168-v3 in Appendix B).
100. [GL-RPT-SENSES-TO-BRAIN-C1-20260705-191-v1] X1 mechanism built/logged but not confirmed against a real live moment. **UNCLEAR** — deployed live per GL-RPT-WINDOW9-AND-FORCED-SLEEP-C1B-20260705-v1, but live behavioral confirmation of X1 specifically not stated closed.
101. [GL-RPT-SENSORY-READING-GAP-C1-20260705-197-v1] LLM sense emulator never wired to any reading path — larger architectural question. **OPEN** at end of batch.
102. [GL-RPT-SLEEP-BACKTEST-C1-20260704-167-v1] Program ledger items 1a/2/3a-c/4a-b/5a-c/6a-b all WAITING. **UNCLEAR** — rate calibration portion done later (GL-RPT-SLEEP-RATE-CALIBRATION-C1-20260704-173-v1); dream re-trigger button item status unclear.
103. [GL-RPT-SLEEP-RATE-CALIBRATION-C1-20260704-173-v1] D3 (deploy with combined SHA) staged, awaiting c1a's brain+voice SHA. **UNCLEAR** — likely closed via GL-RPT-STAGE2-INSTALL-C1-20260704-v1's combined window, not cross-confirmed.
104. [GL-RPT-SLEEP-RATE-FIX-C1-20260702-68] T4 (sleep-cycle frequency, 6h observation) PENDING. **UNCLEAR** within batch.
105. [GL-RPT-SOUNDPATH-MAP-C1-20260703-v1] Client-side confirmation flagged as "the one open item." **OPEN.**
106. [GL-RPT-STAGE2-INSTALL-C1-20260704-v1] Recommends Eve/Joe reconcile the concurrent, uncoordinated Stage-1 deploy timing with c1b. **OPEN** at end of report.
107. [GL-RPT-T5T9-F1F2-STATUS-C1-20260703-v1] Not exhaustively enumerated every remaining caller of adapters' `.transduce()` outside cognition path. **OPEN**, flagged edge case.
108. [GL-RPT-T6-REVIEW-C1-20260703-101-v1] Waiting on (a) -101-v1 CMD text landing on origin, (b) model_cognition_v2.py recovery. **DONE** — GL-RPT-T6-REVIEW-SYNTHESIS-EVE-20260704-101-v1 closes the whole -101 review chain (itself later VOIDED per GL-SPC-MEMORY-RECALL-STATE-v1 — see Finding F2 in the doc-sweep file).
109. [GL-RPT-TAPESTRY-PERF-FIX-C1B-20260704-v1] organism.remember()/recall() cost (82-120s/turn) handed to c1a's window-2 build. **DONE** — addressed across GL-RPT-WINDOW2-RECONCILIATION-C1-20260704-v1 and GL-RPT-RECALL-SPEED-C1-20260704-177-v1 (though the deeper gap becomes T-X1 above).
110. [GL-RPT-TEACHER-CORRECTION-DEPLOY-C1-20260620-01] Review the seed-state detection threshold (vocab<100) after W1 world objects ship. **UNCLEAR** within batch.
111. [GL-RPT-VOICE-TO-WORDS-C1-20260703-153-v1] G-153-2 (non-empty output proof) and G-153-3 (Whisper cost) NOT fully measured. **OPEN** — GL-RPT-VOICE-TO-WORDS-COMPLETION-C1-20260704-v1 fixes a different (frontend fire-and-forget) bug and does not close these two gates.
112. [GL-RPT-WINDOW2-FINDINGS-C1B-20260704-v1] Duplicate-frame binding root cause left as a "shelf item," recommends a server-side dedupe guard. **OPEN** at end of batch, not built.
113. [GL-RPT-WINDOW2-RECONCILIATION-C1-20260704-v1] organism.recall()'s cost remains open after disproving c1b's memoization fix. **DONE** via GL-RPT-RECALL-SPEED-C1-20260704-177-v1 and its window-3 deploy (though see T-X1 for the deeper remaining gap).
114. [GL-RPT-WINDOW3-DEPLOY-AND-LOCKUP-FINDING-C1B-20260704-v1] Severe lock-contention problem (sight/sound frame processing) named as most urgent, not fixed. **DONE** — fixed and verified in GL-RPT-ROTATION-AND-LOCKFIX-DEPLOY-C1B-20260705-v1 (27.2s→8.7s).
115. [GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1] Item 3 (population growth after reading) only partially measurable without a dedicated field or reboot. **OPEN.**
116. [GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1] Item 5 flags an organism_worker /status wiring gap (no -183 standard doc found). **UNCLEAR.**
117. [GL-RPT-WINDOW7-DEPLOY-AND-E1-E3-C1B-20260705-v1] E2/E4/E5 of 5 behavioral exit criteria still open, "actively watching." **UNCLEAR** — E4 confirmed done later in GL-RPT-WINDOW9-AND-FORCED-SLEEP-C1B-20260705-v1; E5 attempted but not completed (item 118); E2 status unclear.
118. [GL-RPT-WINDOW9-AND-FORCED-SLEEP-C1B-20260705-v1] Forced sleep interrupted by a concurrent deploy before completing (dp still 0.38, no dream activity_ended). **OPEN**, explicitly not claimed as E5-satisfied.
119. [GL-RPT-WINDOW8-AND-EMISSION-HANDOFF-C1B-20260705-v1] `curriculum_status` found with the same dead-path defect as before, flagged for window 9. **UNCLEAR** — the WINDOW9 report doesn't mention curriculum_status directly.
120. [GL-RPT-WIRE-ORGAN-CANDIDATES-C1-20260628-31] Step 5 drift data not collected (curriculum lock contention blocked substrate). **UNCLEAR** within batch.
121. [GL-RPT-WIRING-AUDIT-C1-20260704-164-v1] CurriculumScheduler/LoomBrain exact birth dates UNDATABLE (git log traversal timed out repeatedly). **OPEN**, minor.
122. [GL-RPT-autonomy-investigation-20260609] 6 bugs/oddities listed NOT fixed (no re-attendance cooldown; emission content always "..."; dream doesn't consolidate; sleep_manual counter mismatch; inconsistent regulate() cadence; dead EMISSION_COHESION_THRESHOLD constant). **UNCLEAR** — "emission always '...'" is **DONE** (GL-RPT-ROUTE-CANDIDATES-C1-20260619-01 shows real commits firing); the other 5 items' status not confirmed resolved anywhere in this batch.

### CMD batch A source docs (items 123-137)

123. [GL-CMD-BIGRAM-DELETE-EVE-20260629-34] Wiring v7-converse text into the v5 atlas — "deferred to a separate decision." **OPEN.**
124. [GL-CMD-BIGRAM-RETIRE-EVE-20260627-13] Bigram code deliberately kept (not deleted) for possible future Stage-2 voice-comparison routing. **OPEN/optional**, no forcing action.
125. [GL-CMD-C1-POLARITY-EVE-20260627-28] "Phase G.1 negation seeds" flagged as a separate future dispatch. **OPEN**, not found among the swept docs.
126. [GL-CMD-CURRICULUM-AUTOMATION-EVE-20260629-51] Sensory-stream automation outside `guala_give_experience` explicitly deferred. **OPEN.**
127. [GL-CMD-CURRICULUM-AUTOMATION-EVE-20260629-51 / GL-CMD-DENSITY-RETIRE-EVE-20260703-109-v1] The original gated-automation vision never validated end-to-end before its autostart was found running ungated and disabled. **OPEN** — the "real automation, not manual delivery" goal remains unimplemented as originally spec'd.
128. [GL-CMD-DAYDREAM-PARALLEL-EVE-20260629-42] Goal/future-projection ("what-if" rehearsal) function of daydreaming explicitly NOT built. **OPEN.**
129. [GL-CMD-DAYDREAM-PARALLEL-EVE-20260629-42] "Agency organ writes" (rejected from -39/-41) — revisit only after this dispatch is observed. **OPEN**, revisit condition not confirmed met.
130. [GL-CMD-EMISSION-PERF-EVE-20260629-45] Names GL-CMD-SUSTAINED-SPEECH-EVE-20260629-44 as a blocked draft. **UNEXECUTED** — see item 149 below (same item, fuller evidence from CMD batch B).
131. [GL-CMD-AUTONOMY-EMITTING-PHASING-EVE-20260630-53/-53v1] `RICH_SENSORY_INPUT=1` rich-candidate path (501ms cost) needs its own profiling dispatch, "not -53." **OPEN.**
132. [GL-CMD-DNA-EXPANSION-EVE-20260629-36] Regional-word/domain/additional-language vocabulary expansion left as separate future (low-priority) work. **OPEN.**
133. [GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v3] Part 4.7 (`EMISSION_DYNAMICS_TICKS` 40→80 rider) conditional on a clean ≥20-emission cost sample. **UNCLEAR** — GL-RPT-EMISSION-COST-C1-20260702-87-v1 later reports the sample CLEAN, but no doc explicitly confirms the rider shipped.
134. [GL-CMD-EVENT-RETENTION-FIX-EVE-20260704-172-v1] Live-deploy gates G-3/G-4/G-5 not yet proven at the "proven locally" commit point. **OPEN** at that commit; no dedicated RPT-172 found to confirm closure.
135. [GL-CMD-C1B-QUEUE-EVE-20260702-71] Entire 3-item queue an unconfirmed draft ("DO NOT EXECUTE until Eve confirms"). **UNEXECUTED**, no confirmation or report found.
136. [GL-CMD-EMERGENCE-DETECTOR-EVE-20260627-20] Spec text: "if B.2 not yet shipped at B.3 ship time, log a TODO and call /admin/backup directly." **MOOT** — the whole dispatch is orphaned, never built.
137. [GL-CMD-AFFECT-GATE-ROOT-CAUSE-EVE-20260705-200-v1] Entire root-cause audit of `nmda_affect_match` (never fired in her life) — explicitly parked/queued by Joe's order per -202. **UNEXECUTED/QUEUED** — see also Finding F4/F5 in the doc-sweep file; this is the single sharpest "filed but never acted on" example in the whole corpus.

### CMD batch B source docs (items 138-151)

138. [GL-CMD-HOTSAVE-EVICT-VOCAB-SCALED-EVE-20260705-194-v1] O1 — status of -192 (voice echo-chamber fix patch) unknown at filing. **DONE** — -192 v3 was withdrawn entirely by -195 (GL-CMD-VOICE-ORGANISM-CANDIDATES-EVE-20260705-195-v1).
139. [GL-CMD-HOTSAVE-EVICT-VOCAB-SCALED-EVE-20260705-194-v1] O2 — quiet-block ruling (curriculum n_fed=0) still owed from -192 D4; now TWO blocks observed suppressed. **OPEN**, no later disposition found.
140. [GL-CMD-HOTSAVE-EVICT-VOCAB-SCALED-EVE-20260705-194-v1] O3 — frame_backpressure drops (sight 8, sound 30) since -191 went live; drop rate deferred to next window report. **OPEN.**
141. [GL-CMD-VERIFY-AND-STABILIZE-C1B-20260705-206-v1] V2 — Stability watch on -205's yield fix; root cause NOT fully isolated (local repro didn't reproduce it). **OPEN.**
142. [GL-CMD-VERIFY-AND-STABILIZE-C1B-20260705-206-v1] V3 — TAPESTRY CORRUPTION, NAMED NOT FIXED (truncated-compression restore failure correlated with a 502 during a fast-tick deploy). **OPEN** — also independently flagged in GL-HANDOFF-C1B-20260705-v2 per the MISC batch.
143. [GL-CMD-VERIFY-AND-STABILIZE-C1B-20260705-206-v1] V4 — First natural dream not independently verified as genuinely natural before being filed as E5-satisfied. **UNCLEAR/OPEN.**
144. [GL-CMD-VERIFY-AND-STABILIZE-C1B-20260705-206-v1] V5 — Watch `ladder.mean_utterance_len`; utterances still 2 words offline. **OPEN**, no measurement found confirming closure.
145. [GL-CMD-VERIFY-AND-STABILIZE-C1B-20260705-206-v1] V6 — Standing process reminder: always use an isolated worktree, never the shared main directory ("two separate git collisions cost real rework tonight"). **PROCESS NOTE**, not a code defect — folded into GL-AUDIT-SEC9-DOC-SWEEP §5 (dev environment).
146. [GL-CMD-STAB-PHYSICS-EVE-20260702-99-v1] The -87 emission cost sample from -97 step 2 still owed. **UNCLEAR**, not tracked further in this batch.
147. [GL-CMD-NEXT-WINDOW-PAYLOAD-EVE-20260705-184-v1] Continuing to watch -181's R3 exit criterion. **DONE** — confirmed live per GL-RPT-ROTATION-AND-LOCKFIX-DEPLOY-C1B-20260705-v1.
148. [GL-CMD-READING-THROUGH-SENSES-EVE-20260705-196-v1] `catalog_builder` deferred (lookup_grounding got the GO first), with the standing-ruling reason named. **OPEN**, no evidence it was later picked up.
149. [GL-CMD-SUSTAINED-SPEECH-EVE-20260629-44] Entire dispatch (MAX_COMPOSITION_LEN removal, emission chaining, coherence-derived cooldown). **UNEXECUTED** — blocked by its own companion dispatch ("draft, not shipped... explicitly held"); `EMISSION_COOLDOWN_TICKS=200` confirmed still hardcoded in the live engine at audit time (the length-cap half was later independently removed by the unrelated -203 dispatch, not as a continuation of -44).
150. [GL-CMD-VOICE-PATH-CONSOLIDATION-EVE-20260629-37] Optional: rename `organ_brain_silenced_pending_inspection` → `organ_brain_retired` in the response_source field. **UNCLEAR/optional**, no direct commit evidence confirming this specific rename landed.
151. [GL-CMD-T6-REVIEW-EVE-20260703-101-v1] Per-defect disposition table (fixed by migration / deferred / out of scope). **DONE** — resolved by the review synthesis report, not independently tracked as outstanding.

### MISC batch source docs (items 152-179)

152. [GL-ARCH-FRONTEND-SPLIT-WC-20260614-01] Phase 2 (Dockerfile per container, two-container ECS task-def, prod deploy). **SUPERSEDED** — never executed; direction reversed by the -61 process collapse (embedded single-process became the permanent architecture).
153. [GL-ARCH-FRONTEND-SPLIT-WC-20260614-01] Phase 3 (sensory ingest as queue-then-notify) and Phase 4 (admin endpoints as fsync'd transactions). **SUPERSEDED** — moot given Phase 1's premise was abandoned.
154. [GL-CHARTER-motivation-v3-wC-20260609-024] "Future, not in this charter window" list (sound architecture parallel to vision, surplus-mode emissions, entity-models of bonded-others, time-perception as substrate quantity). **UNCLEAR**, status not confirmed built in any later doc read.
155. [GL-CURR-FOUNDATION-WC-20260610-01] "Awaiting Joe's layer and veto pass." **OPEN** — never confirmed closed (still OPEN per GL-LEDGER-WC-20260613-051 T18, "IN PROGRESS").
156. [GL-DESIGN-DSF-J-WEIGHTING-EVE-20260626] Joe to pick Option 1/2/3, then implement atlas `dsf_arr` field + cosine-weighted ranking. **OPEN** — never implemented (confirmed absent via grep as of current repo state); Joe never picked an option in any later doc read.
157. [GL-HANDOFF-20260626-EVE] "[2] REMOVE timing probe" (delete `converse_timing` diagnostic block after gate passes). **UNCLEAR**, no later doc mentions its removal.
158. [GL-HANDOFF-20260626-EVE] "[5] Shadow embryo re-impl" (separate 512MB-ceiling container, one-way queue). **SUPERSEDED** — organism/embryo work later happened in-process (GL-CMD-BRAIN-FULL-DEPLOY-175) rather than as a separate shadow container.
159. [GL-HANDOFF-C1-20260630-NIGHT] Curriculum-pause 35-53s root cause not identified; CURRICULUM_CHUNK_SIZE 30→10 "not shipped — next session." **OPEN** — see T-X4; still 30 as of 07-05.
160. [GL-HANDOFF-C1-20260630-NIGHT] AUTONOMY_PHASED=1 socket deadlock, "leave for future." **OPEN** — see T-X3.
161. [GL-HANDOFF-C1-20260702-v2] XFF admin-access logging spec never landed. **OPEN** — see T-X5.
162. [GL-HANDOFF-C1-20260703-v3] `tools/deploy_gualoom_bridge.sh:99` still has an identical hardcoded dead API key. **UNCLEAR**, no later doc confirms it was fixed.
163. [GL-HANDOFF-C1-20260703-v3] loomscan.html's own "back to guala" link still 404s (S3-root-sync bug). **UNCLEAR**, not confirmed fixed in any later doc read.
164. [GL-HANDOFF-C1-20260703-v3] -96 organ-reader "structurally ungateable — no process to run in." **SUPERSEDED** — later work (GL-CMD-BRAIN-FULL-DEPLOY-175) put the organism directly in-process instead of restoring the separate organ_brain_service.
165. [GL-HANDOFF-C1-20260704-v1] GL-CMD-158's remedy decision (standalone-teaching vs recall-routing gap) left for Eve's ruling. **SUPERSEDED** — overtaken by the -207 wave-memory recall rewrite (07-05), which replaced the whole recall mechanism this gap lived in.
166. [GL-HANDOFF-C1-20260704-v1] Weekly recall-measurement cadence (per -157's standing rule). **OPEN** — GL-RECALL-DAILY-20260703.md has only 2 dated rows despite several recall-touching deploys since; cadence appears to have lapsed.
167. [GL-HANDOFF-C1-20260704-v3] `organism.recall()` O(population) cost, direct cause of 82-120s+ turns. **SUPERSEDED/PARTIAL** — see T-X1 (improved but not solved).
168. [GL-HANDOFF-C1A-20260705-v1] `recall_ms`/`read_ms` root-cause gap (17-34s vs ~2.6s extrapolated). **OPEN** — this IS T-X1, the master item.
169. [GL-HANDOFF-C1A-20260705-v1 / GL-HANDOFF-LIVE-BELLS-WIRING-C1B-20260705-210-v1] `probe_209` still failing 1/5 (20%). **OPEN** — this IS T-X2.
170. [GL-HANDOFF-C1B-20260705-v2] Tapestry restore corruption, correlated with a `[pause]` 502 during a fast-tick-rate deploy. **OPEN** — same item as 142 above.
171. [GL-HANDOFF-C1B-20260705-v2] E5 (first natural, pressure-triggered sleep) plausibly satisfied but "not independently confirmed." **UNCLEAR** — same item as 143/76 above.
172. [GL-BOARD-OPEN-ITEMS-EVE-20260704-v2] Shelf S3 (voice-out / Incognito TTS issue). **OPEN**, no later doc confirms this shipped.
173. [GL-BOARD-OPEN-ITEMS-EVE-20260704-v2] Shelf S4 / -104 (survival-key pruning, "inherited, still undispatched"). **OPEN** — carried across at least 3 handoffs, no fix confirmed.
174. [GL-BOARD-OPEN-ITEMS-EVE-20260704-v2] Shelf S7 / scene tags (where/ambient/who). **DONE** — per GL-CMD-SCENE-LANES-B1-EVE-20260705-188-v1 (Appendix B), scene lanes were subsequently built (though live seat-test verification, X3, remained open per item 94 above).
175. [GL-LOG-AUDIT-DECISIONS-EVE-20260618] Findings A1-A4, C1-C5, D1-D6, E, F1-F4, G1-G3 from the ML-contamination audit, explicitly "NOT addressed." **OPEN**, permanently, in this doc; no later doc closes them out.
176. [GL-LEDGER-ADD-AUDITORY-CORTEX-WC-20260614-01] T19 auditory-cortex/voice-identity substrate analog, "NOT STARTED, brief NOT WRITTEN." **ORPHANED** — confirmed never built (no matching mechanism found anywhere in the current codebase), never folded into any ledger revision.
177. [GL-MDL-WORLD-WC-20260612-03-ADDENDUM-CALLS] The "calls"/phone object design. **OPEN/likely abandoned** — no later doc mentions this being built.
178. [GL-INCIDENT-APIKEY-C1-20260703-v1] "Consider moving admin auth off a static shared secret." **OPEN** — see T-X6.
179. [GL-DESIGN-SLEEP-WINS-BY-PHYSICS-C1-20260704-v1] 4 questions posed to Eve/Joe (override shape, "load" definition, ceiling-derivation method, naming-correction bundling). **DONE** — per GL-LEDGER-DAILY-20260704-EVE-v1, Joe ratified and Changes 1-3 shipped (56d8952).

### BRIEF/FIND/NOTE/FIX/LTR batch source docs (items 180-189)

180. [GL-BRIEF-DEEPATLAS-DEPLOY-WC-20260610-032] "Within-deep consolidation / schema formation" deferred to a future brief, to escalate if growth is runaway. **OPEN** — no later brief found addressing this explicitly.
181. [GL-BRIEF-DEEPATLAS-DEPLOY-WC-20260610-032] ENCODE_GATE/DWELL_GATE retuning deferred "only after prod distributions observed." **OPEN**, no dedicated retuning brief found.
182. [GL-BRIEF-EMISSION-CONSTRAINT-REMOVAL-20260616-01] Hardcoded emission length caps (`len(emitted) >= 6`/`>= 4`) explicitly deferred pending a separate wC+Joe design spec. **OPEN** — explicitly told not to pull forward. (Note: the *length cap itself* was later independently removed by the unrelated -203 "no-caps" dispatch on 2026-07-05, but the deferred *design spec* this item asked for was never separately produced.)
183. [GL-BRIEF-EMISSION-CONSTRAINT-REMOVAL-20260616-01] SSE events panel intermittently empty, root cause not diagnosed, deferred until Phases A-E settle. **OPEN** at filing; not re-verified this pass.
184. [GL-BRIEF-METADECAY-WC-20260610-033] Waking micro-replay explicitly out of scope ("modeled, works, but naive selection showed full lock-in pathology"), deferred as a future enrichment brief. **OPEN**, no follow-up enrichment brief found.
185. [GL-BRIEF-UI-RESTORE-PHASE-B-FIX-WC-20260616-01] "Phase B-FIX-2" (replace base64-through-socket uploads with shared-EFS write + register_upload message) explicitly scoped as "a separate brief once Phase B-FIX-1 verifies." **OPEN** — no register_upload/shared-EFS-upload pattern found in later commits (only an unrelated async EFS-write perf fix).
186. [GL-BRIEF-V7-UNIFY-WC-20260613-01] Grammar explicitly "does not add Wh-movement, ellipsis, or embedded questions. Deferred." **OPEN**, no evidence these grammar features were ever added.
187. [GL-NOTE-V5-REMOVAL-PLAN-DEPRECATED-EVE-20260627-30] Curriculum-feed contamination of SuccessionTracker: "Phase G hygiene pending." **OPEN**, no Phase G hygiene commit found.
188. [GL-BRIEF-PERSISTSAFE-FIX-WC-20260611-039] D4 "the real drill still pending" (restore-from-S3 drill impossible until D3's backup exists). **DONE** — D3 landed (f512e83) and the drill script landed immediately after (f264647).
189. [GL-BRIEF-V7-FULL-UNCAGE/V7-UI-REPAIR/V7-UNCAGE-WC-20260613-01] "Native audio krimelack from raw mic frames" repeatedly listed as deferred, to replace WebSpeech for input. **DONE** — resolved later via Whisper wiring (2026-06-18) plus raw-PCM `/sound_frame` krimelack feed (2026-06-15).

*(Two further BRIEF-bucket findings — GL-BRIEF-self-section-v3's
orphaned status and GL-BRIEF-V7-UNCAGE's contradicted SEED_VOCAB claim
— are dispositioned as doc-classification STATUS in
GL-AUDIT-SEC9-DOC-SWEEP-C1-20260705-v1.md Appendix C rather than as
prose TODO items, since they were framed as claims-of-completion, not
open asks.)*

---

## Coverage note

**All 7 classification batches (RPT A/B/C, CMD A/B, BRIEF/FIND/NOTE/
FIX/LTR, MISC) completed and are merged above** — 189 numbered items,
100% of the 528-doc GL-prefixed corpus. Nothing outstanding.

189 numbered items above, spanning 2026-06-08 → 2026-07-05. Roughly:
**~57 DONE/SUPERSEDED-resolved, ~101 OPEN, ~31 UNCLEAR.** The single
highest-priority OPEN item by a wide margin is **T-X1 (production
conversation latency, still 69-72s vs a <1s target, root cause of the
remaining gap not found)** — it is the last thing the most recent
handoff in the entire repository (`GL-HANDOFF-C1A-20260705-v1`, current
HEAD) says is unresolved, and it is the item this audit's own §8
(Behavioral Baseline) is instructed to re-measure.

### Changelog
- v1 (2026-07-05, c1): initial and only version. 189 items merged from
  all 7 classification batches (RPT A/B/C, CMD A/B, BRIEF-group, MISC),
  all complete, none outstanding. Cross-cutting Part 1 added to surface
  the 8 items that recur across 3+ source docs, so their centrality
  isn't lost in the numbered list's scale.
