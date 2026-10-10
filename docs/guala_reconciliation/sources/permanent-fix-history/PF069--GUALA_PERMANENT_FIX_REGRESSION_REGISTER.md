# Guala Permanent Fix and Anti-Resurrection Register

Status: active production-development authority.

Purpose: keep one cumulative list of accepted fixes and require every later
candidate to prove that it does not restore the rejected mechanism. Sprint
ledgers retain the detailed evidence; this register is the cross-sprint gate.

## Required check for every candidate

Before commit and again after live cutover, record for every applicable row:

1. the exact source symbol or production surface checked;
2. whether the rejected mechanism is absent or unreachable;
3. the focused proof or live observation used;
4. the candidate commit and, after deployment, the task definition.

A row may not be called preserved from a source comment, ledger claim, or test
fixture alone. If it cannot be checked, the candidate remains open.

## Current accepted fixes

| ID | Accepted correction | Mechanism that must not return | Required regression check | Current evidence |
|---|---|---|---|---|
| F-001 | One resident organism restores only from authenticated `CURRENT`; identity survives cutover. | Ghost successor organisms, alternate restore authority, or observer-owned cognition. | Confirm one running writer, one `CURRENT` lineage, and unchanged organism identity after cutover. | Production task 1283 reports identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`; detailed custody evidence remains in the A-009/A-011 ledgers. |
| F-002 | Unattended native life advances without an external request. | Request-driven or observer-driven cognition. | Observe ticks advance while request logs contain only health/read traffic; observers remain read-only. | Live unattended advancement was measured before and after task 1280. |
| F-003 | Electrical settlement is per connected physical pathway. | One global minimizing fraction allowing disconnected pathways to suppress each other. | Inspect the mounted solver boundary and retain the disconnected-path falsifier. | Accepted correction `662f9cce`; A-006 ledger. |
| F-004 | Coincidence-based layer-11 to motor/articulatory fan-out is removed. Root-guided movement is not contact-authoring evidence; every learned motor contact, including root yaw, requires the exact two-interval ordering -> affective -> regulation chain. General whole-tract or returned-sound evidence cannot name a vocal motor; only that axis's exact proprioceptive return may author its route. | Authoring every simultaneous or merely preceding ordering/motor pair; guided movement, self-hearing, or general tract consequence as motor-contact authority; restart restoration of removed contacts. | Require the exact causal-chain and ambiguous-whole-tract falsifiers; observe zero unproved layer-11 -> layer-12 contacts after migration and again after unattended successors; recheck after every later motor or articulatory change. | **Closed live again 2026-08-31 on production task 1398**, commit `fce1ae2c`. The exact task-1397 predecessor had 26 vocal fan-out contacts on only two ordering cells. V38 retired all 26 once and deleted their authorship branch. Custodied successors at ticks 345534 and 345558 both retained `11->12 = 0`, fixed `12->13 = 26`, 1,809 neurons and 7,353 total contacts. |
| F-005 | Contact settlement uses the mounted event frontier and the old unconditional full-contact sweep is deleted. | Production reachability of the old whole-fabric sweep, a second scheduler authority, or a charged root-yaw terminal that can discharge only when an unrelated contact happens to wake it. | Inspect the production call graph, observe due/sleeping census from the sole resident frontier, and prove a charged root-yaw terminal schedules its own next local membrane event. | Task-1248 lineage and later releases; detailed scheduler evidence in A-006. Task 1282 exposed the missing terminal-event case; the copied reached-interval proof alone is permanently insufficient. |
| F-006 | Passive membrane return is a local neuron transition; the pump serves only the causal frontier. | Pump-as-rest, pumping every touched neuron, or outside-energy creation. | Preserve positive/negative return, zero-crossing, carrier conservation, and untouched-neuron falsifiers. | Deployed in `cd9ffa93`; A-006 ledger. |
| F-007 | Ordinary cognition never seals, encodes, stages, or uploads its body. One bounded external custodian prepares the exact resident checkpoint off the lived-time boundary, publishes as the sole `CURRENT` writer, then atomically adopts that same body as the resident recovery predecessor without replacing newer cognition. | Restoring the synchronous fourth-interval seal; mounting an independent checkpoint writer that advances `CURRENT` without native predecessor adoption; publishing a stale/abandoned trajectory; or encoding the snapshot twice. | Require the native newer-life/adopt/abort falsifier, exact raw-stage read-back, publish-before-adopt ordering, trajectory-epoch abandonment refusal, one custodian thread, and multiple live checkpoint cycles followed by uninterrupted sensory intake and cold restore. | **Closed live on task 1382, 2026-08-30**, commit `5a8d61f4`. Five consecutive checkpoints at ticks 340814, 340821, 340833, 340839, and 340851 published with every lived interval reporting `seal_ms=0`; each custody cycle retained one or two newer intervals while encoding/staging the older exact checkpoint. Warm resident snapshot borrow was 17.1-17.3 ms, off-lock encoding 3.91-4.15 s, off-lock staging 1.57-1.77 s, and the final publish/adopt borrow 0.74-1.06 s. No error, stale predecessor, 503, panic, or restart occurred. |
| F-008 | Observers are read-only and have no authority to admit, discard, choose, pause, or mutate cognition. | Observer labels, polling windows, or proof caches controlling organism transitions. | Review every changed observation callsite for immutable access only; live ticks must not depend on observer availability. | A-009/A-011 observer corrections and live continuity evidence. |
| F-009 | Native motor output is the neuron's exact local membrane whole-carrier discharge; contact transfer is preparation evidence only. | Relabeling incoming or net inter-neuron contact flow as efferent motor discharge. | Preserve positive/zero/negative/no-preparation falsifiers and inspect the runtime action payload source. | Commit `40a0222c`, focused proof passed, live task 1280. |
| F-010 | Root-yaw proprioception uses compact disjoint layer-6/layer-8 anatomy; malformed historical root paths are retired one way. | Recursive Cantor projection into a 93,824,443 pF regulation cell, restoration of its contacts, or a second root route beside the corrected route. | Prove V32 retirement is one-way; after one real root movement require exactly receptor -> compact integration -> compact regulation -> paired motor, with the malformed regulation isolated. | Commit `c8f84bd1`, live task 1281. V32 left malformed lineage `...02ecfd` isolated and mounted compact regulation `...000ecf` at 37,393 pF between layer-6 `...002ae9` and paired motor `...00009b`. |
| F-011 | A charged mounted root-yaw terminal schedules its own next local membrane event and discharges through its own carrier path. | Waiting for an unrelated contact to wake a prepared terminal, using passive return as action, or relabelling contact current as output. | From a restored charged root motor, require native recruitment, applied world movement, exact sensory consequence re-entry to the same identity, and later unattended advancement. | Commit `0931c5f2`, live task 1283: lineage `...00009b` emitted one positive carrier; world moved +1 millidegree; all mounted sense families returned under identity `1cc4e70a...`; tick advanced from 209159 through at least 209176. |
| F-012 | Innate vocal anatomy is one fixed bridge from the ten antagonist terminals of the five physical vocal axes to one layer-13 excitation cell; learned meaning remains upstream and sparse. | Requiring a prior utterance before mounting the anatomy needed for the first utterance; restoring the broad layer-13 coincidence pool; connecting a limb, eye, or unrelated motor to speech. | Migrate an exact V33 body with no speech bridge to V34; require ten and only ten vocal-motor contacts converging on one layer-13 cell; refuse non-vocal motor routes; require V34 restart identity. | **Closed 2026-08-28 on production task 1285**, commit `89fff22a562ed25a4849c11addab838a03e882de`. Same identity, one writer, V34-only persisted CURRENT, ticks 211768 through at least 211840, and approximately 3,750 scheduled contacts. L-006 utterance evidence remains separate and open. |
| F-013 | Root translation returns through the same organism as sensory proprioception and cannot feed directly back into the translation motor. Explicit migration must traverse current-body structural corrections even when the format magic is already current. | The stale place-6/178-pF motor; any direct layer-8 -> translation-motor contact; counting returned feedback as another command; a current-format early return that skips the one-way repair; or declaring a padded 250 ms consequence occurrence with only the two-millisecond raw capture interval. | Restore and explicitly migrate a copied production CURRENT twice to identical bytes; require the fixed terminal at its exact declared place and no layer-8 motor contact; preserve the intake-hop causal gate for padded self-hearing; then complete one full returned translation consequence with zero repeated recruitment. Synthetic helper fixtures alone are forbidden closure evidence. | **Direct Live-Closed 2026-08-29.** Commit `118ed8526db20a4a60828a4a8267c190ab813ab7`, task 1314, moved x=6707 -> 6708 exactly once, accepted 29 consequence hops through tick 251426, persisted the successor, and continued unattended beyond tick 251476. The failed `de856a63` and `04429e17` attempts remain recorded. |
| F-014 | Crash-left private persistence stages are retired only at cold start after a valid CURRENT establishes the authoritative life. | Accumulating raw `.stage-*.glorun` bodies; restoring from a stage; deleting damage evidence when CURRENT is absent; or allowing a stage to authorize genesis. | With valid CURRENT, cold boot retires only exact private regular stage files before the writer starts; with no CURRENT, stages remain and restore/genesis refuses. Recheck resident-root bytes after cutover. | **Direct Live-Closed 2026-08-29.** Commit `d0364541035da890f7ff65017bdd5327e97080cc`, task 1315, retired 10 stages / 180,580,001 bytes; no stage remained and the root measured about 14 MB. |
| F-015 | The production task exposes no retired Python-brain resurrection switches. | Reintroducing `DECAY_PAUSED`, `EVENT_DRIVEN_SUBSTRATE`, `HOMEOSTATIC_SCALING_ENABLED`, `SUBSTRATE_HEARTBEAT`, `SUBSTRATE_MODE`, or `LATERAL_INHIBITION_ENABLED` as alternate cognition/runtime authority. | Inspect the registered task definition and live container environment; verify the immutable manifest still boots only `native_production_app`. | **Closed 2026-08-29 on task 1315.** All six switches are absent; PID 1 is the single Uvicorn native-production app. |
| F-016 | Exact contact settlement integrates each already-derived scaled current once and computes released electrostatic work from the direct exact energy difference. | Repeated BigRational integration of the same current; constructing and normalizing separate predecessor/successor energy totals for one contact transition; or replacing exact arithmetic with floating point, a heuristic, or a reduced DSF field. | Preserve the contact-energy and connected-component falsifiers; require unchanged full seven-field evaluation and measure the live shared-field phases. | **Closed live 2026-08-30.** Commits `c719157a`, `d2d0c588`, and `df3693d4`; live released-work attachment fell from 23–32 ms to 5–8 ms and shared-field settlement fell from approximately 333–354 ms to approximately 108–143 ms. |
| F-017 | Passive-return scheduling compares the exact one-carrier stored-work delta without constructing a complete candidate neuron, and next-clock events use their own preallocated frontier instead of the future heap. | Cloning a whole neuron and evaluating two complete stored-work totals merely to decide one return event; remove/reinsert churn for events already known to be due next clock; or any approximate event threshold. | Preserve positive/negative displacement, lawful rest floor, depleted sender, exact due order, future-to-next and next-to-future rescheduling falsifiers; measure live event sub-phases. | **Closed live 2026-08-30 on task 1366.** Commits `1ae21e33` and `be68f672`; return scheduling fell from 64–78 ms to 39–47 ms and total event work from 122–134 ms to 94–108 ms while the same organism advanced beyond tick 311761. |
| F-018 | Resident cohort settlement remains in its one owner after in-place application; no identical complete cohort successor is cloned and assigned back. | Restoring `let settlement_successor = cohort.state.clone()` or another full-cohort copy after the in-place transition. | Inspect the production path for one in-place owner and no post-settlement whole-state clone; retain the reached sparse settlement checks. | **Closed live 2026-08-30 on task 1365**, commit `32214758`. The copy was removed permanently; live timing showed it was visible bloat but not a material latency source. |
| F-019 | One gate-owned full seven-field MathLoom delivery is converted once per mounted width and borrowed by every reached neuron on that same completed gate. | Rebuilding the identical `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`, `P_k`, `B_k` exact-rational balanced-ternary delivery independently for every reached neuron; flattening or approximating any DSF field. | Require the shared-field/gate identity check, preserve each neuron-local Psi settlement, and compare live preparation and interval times. | **Closed live 2026-08-30 on task 1371**, commit `02cac523`. Input/Psi preparation fell from 322–335 ms aggregate CPU to 206–215 ms and cohort wall time from 176–187 ms to 140–149 ms on the same organism. |
| F-020 | A Psi energy landscape is prepared once per shared heavy neuron anatomy and exact gate delivery; each neuron applies that immutable plan to its own retained winding, dissipation, and capacity. | Recomputing identical exact ring energy landscapes for every neuron; mirroring neuron state, capacity, carriers, or consequences; replacing exact descent with a lookup approximation. | Preserve exact tie refusal, reachability, dissipation quantization/capacity, full DSF/Psi and receptor-transition proofs; require live preparation reduction without state or identity reset. | **Closed live 2026-08-30 on task 1372**, commit `55dc2d67`. Input/Psi preparation fell again from 206–215 ms aggregate CPU to 29–36 ms; cohort wall time fell to 115–133 ms while the same organism advanced beyond tick 314403. |
| F-021 | One exact gate population descent is prepared from the interval's unchanged structural inputs, used to derive required recovery, then re-quantized only against the actual post-recovery dissipation capacity. | Selecting the same gate destination twice around recovery; reusing a stale capacity result; flattening gate free energy, tie refusal, residue, carrier, or heat physics. | Compare prepared versus direct capacity-bounded settlement across gate populations, predecessor openings, residues, capacities, and signed work; preserve recovery conservation; require live reduction on the same organism. | **Closed live 2026-08-30 on task 1375**, commit `9af26bc9`. Gate-recovery work fell from 68–75 ms aggregate CPU to 2–4 ms; extended gate/membrane work fell from 200–207 ms to 106–111 ms; the same organism was live-verified at or beyond tick 332182. |
| F-022 | Ordinary elementary carrier settlement uses exact cancellation-first fixed-width ratios and falls back to the existing arbitrary-precision law only on a real width overflow. | Rounding carrier counts or retained phase; accepting zero-duration settlement; treating fixed-width equivalence as proof of a speed gain; removing the exact fallback. | Differentially compare carrier count and retained phase with the arbitrary-precision law across both current directions, signed phases, boundary durations, and wide values; compile the native crate; require live production timing before claiming performance. | **Closed for physics equivalence, not credited as a speed improvement, 2026-08-30 on task 1376**, commit `44a38700`. Six elementary-transfer and six local-membrane tests passed, native compilation passed, and the same organism advanced beyond tick 332841. Live extended work remained 101–112 ms and whole physical intervals remained 0.56–0.89 s, so no further speed surgery is justified by this cut. |
| F-023 | Continuous browser audiovisual ingress is a microphone-clocked sequence of four exact 250 ms pressure hops, each paired at capture time with its own camera frame; only the newest complete one-second window may exist locally, and transport failure discards the failed window without closing either sense. “Microphone active” requires the browser audio clock to be running and real PCM samples to have arrived; permission alone is not activity. Both capture and window dispatch are driven by arrival of those audio-clock samples, never by a foreground page timer. Long native settlement remains owned by the production transport boundary rather than a shorter competing page timer. A failed upload may arm exactly one bounded transport-retry window for the same live sense epoch; audio-clock callbacks cannot create parallel or repeated retries during that window. Public frame totals count captured camera frames, never internal action/consequence hops. | Pairing independently timed camera and microphone queues; allowing a slow response to expand the next window from four to eight hops and double its native work; counting internal consequence hops as camera frames; using the foreground-timer `ScriptProcessor` for continuous capture; dispatching audio-clocked windows from a normal page `setTimeout` loop that browsers may throttle; reporting permission as live samples; failing to resume or verify the audio clock; adding a page abort shorter than the organism's measured settlement; stopping senses on tab visibility or one failed request; retaining a stale backlog; retrying device permission denial; allowing every audio callback to retry a failed upload during a target outage; letting UI/observer state acquire cognition authority. | Require page syntax and focused audiovisual/lifecycle contracts; use the browser audio-thread worklet, dispatch directly when its PCM arrival completes one exact four-hop current window, evict older captured hops, explicitly resume/verify its clock, and refuse the active-samples label until PCM arrives; permit timers only as a one-time missing-clock watchdog and one epoch-owned transport-retry window; leave in-flight request lifetime to user/device/page abort plus the measured production load-balancer boundary; verify the exact committed public bytes; retain epoch/abort ownership, exact native audiovisual cardinality, truthful captured-frame accounting, and one resident organism across cutover; sustained real-device/resource proof remains mandatory before claiming 24/7 closure. | **Event-driven correction live; sustained-device proof open, 2026-08-30 on task 1378.** Service commits `d08fd2dd` and `46054734`; UI commits `f686ec0b`, `7c85d20b`, and `a8d4bb4e`. Post-cutover ALB evidence corrected the preliminary diagnosis: the browser offered each next window about 0.4 seconds after the preceding response; 29–102 seconds were target processing, not hidden-tab dispatch. Clean task-1378 evidence then measured four-hop target work at 25.5 seconds while backlog-expanded eight-hop windows took 34.7–62.3 seconds. The task-1378 zero-target handoff also exposed a retry burst: rejected uploads never entered the organism, but audio callbacks retried after each fast rejection. The page correction now retains only the newest exact four-hop second, permits exactly one epoch-owned retry window, clears it when the sense closes, and reports actual captured frames rather than native consequence hops. The page-only cutover did not restart or replace the organism. |
| F-024 | An arriving external sensory request announces itself at the outer ASGI request boundary before dependency solving or synchronous worker admission; unattended life may finish the one atomic interval already in flight but cannot start more intervals ahead of the waiting experience. | Relying only on a route dependency—even an async generator—when production proves the handler can remain queued while unattended transport reacquires the organism; interrupting an already-started native interval; or letting transport select cognition or action. | Preserve the global waiter count, event, non-blocking unattended lock, and `finally` release. Require an outer-boundary proof showing the signal is set before downstream routing, plus live ALB and interval logs showing no newly started unattended interval between request arrival and native sensory settlement. | **Closed again live on task 1383, 2026-08-30**, commit `de71074e`. The prior task-1378 async dependency was insufficient in production. The outer ASGI boundary now announces paired camera/microphone arrival before route queuing; the first measured post-cutover capture carried exactly four ordered audiovisual moments plus one action consequence, with no serial 16-19-moment expansion attributable to that capture. |
| F-025 | The exact world, visual, auditory, tactile, chemical, thermal and sparse body consequences of one action coexist at their receptors in one physical interval and the shared resident fabric settles once. | Passing coexisting consequence sources through the ordered-trajectory helper so every source becomes another organism tick; dropping body consequences to save time; merging or flattening their distinct DSF occurrences; or giving an observer authority over the grouping. | Require each source to retain its own authenticated episode, occurrence admissions and full seven-field evaluation; refuse sources with unequal physical duration; prove two coexisting sources advance one organism tick and produce one causal-interval record while the same sources through the temporal API advance two; live action evidence must report one consequence interval under the same resident identity. | **Closed live on task 1379, 2026-08-30**, commit `d0c33af2`. Under identity `1cc4e70a...`, one real action returned six sparse body-source packets carrying 47 exact body consequences beside the complete world consequence and advanced exactly tick 338977 -> 338978. Live action-consequence settlement measured 2.44-2.49 seconds versus the prior approximately 5.9-8.2 seconds. L0-L4 and every source-local full seven-field DSF occurrence remain unchanged. |
| F-026 | An unattended transport borrow ends after one exact physical hop so waiting external sight, sound, or other experience enters at the next physical boundary. | Calling eight successive 250 ms physical moments one "interval" and holding the transition lock across the whole trajectory; interrupting a physical hop already settling; or allowing transport priority to select cognition. | Require the unattended transport unit and world advance to equal exactly one declared 250 ms hop; preserve non-blocking external-wait admission before each hop; prove the relationship is locked in source and measure live ALB target wait after cutover. | **Closed live on task 1380, 2026-08-30**, commit `77b90a5d`. Before cutover, real audiovisual target time was 19.8-42.0 seconds because an eight-hop unattended borrow could consume about 12 seconds before the waiting experience entered. The first post-cutover audiovisual request completed in 7.433 seconds, spanning exactly four temporal camera/microphone moments followed by one exact action-consequence interval. The same identity restored beyond tick 339551; L0-L4 and full occurrence-local DSF delivery are unchanged. |
| F-027 | Whole-body terminal energy observation uses available CPU without changing settlement or arithmetic order. | Serially walking every cohort's reservoir and every neuronal dissipation lane after each unsealed native advance; parallel-reducing exact rationals in a different order; or letting the observation feed back into physics. | Compute each independent cohort subtotal in parallel, collect subtotals in canonical cohort order, then perform the original exact BigRational accumulation in that unchanged order; compare the parallel result with the retained serial reference and require live timing before crediting a speed gain. | **Exact correction live on task 1382, but no isolated speed credit claimed, 2026-08-30.** Commit `92187c03`; Rust compilation and the focused equality falsifier passed before inclusion in release `5a8d61f4`. No physics, persistence bytes, L0-L4 field, or neuronal state changed. |

| F-028 | A read-only observation refresh is never awaited by camera, microphone, action, speech, autonomy, curriculum, or sensory dispatch. Observation may update independently after a committed transition but cannot hold a sense closed, delay the next capture or lesson, or acquire organism authority. | `await refreshObservation(...)` or any equivalent observer promise on a lived transport path; treating a report as the acknowledgement required to continue sensing, speaking, acting, or teaching. | Inspect every lived-path caller; the complete public page must contain zero awaited observation refreshes, and focused proof must reject an awaited refresh. Verify the exact public S3/CloudFront artifact, then measure consecutive real-device capture cadence. | **Systemic correction live on public page origin, 2026-08-30**, commits `e94bed62` and `bec0d1d4`; focused browser proof 9/9, zero awaited observation refreshes in the complete served page, S3/CloudFront SHA-256 `0fdeeb566979b553d1a4f5e71fb0c2162d22588747ecbb1d248c25c41cfcf574`, invalidation `I6L8WJZDJT0H7ARM1EERN9OQE8`. Task 1384 carries the microphone correction; the public origin carries the complete systemic closure. Sustained real-device cadence remains part of R-005. |
| F-029 | One native layer-13 discharge drives one exact 1 ms articulatory motor event; the remaining physical interval is passive vocal-tube pressure settlement, and unresolved acoustic pressure/flow/phase persists in the resident body across intervals and restarts. The exact emitted PCM is both self-heard and exposed for user-controlled playback. | Stretching one discharge across the complete 250 ms sensory interval; resetting acoustic wave/flow/phase at every interval; browser-generated buzz, TTS, phonemes, scripted waveform, or separate self-hearing/playback audio. | Require current and legacy body-format restoration, exact acoustic-state persistence, quiescent no-allocation, a shared pressure/body/cochlear clock retaining the 1 ms event, nonperiodic live PCM, exact playback/self-hearing hash identity, and uninterrupted unattended plus audiovisual transitions after cutover. | **Closed live on task 1389, 2026-08-30.** Source commits `b10ccfa2` and `8310ee0c`; bridge corrections `e8478464` and `099cf40a`. The first autonomous production pressure returned 4,000 samples at 16 kHz, with 26 nonzero samples spanning indices 9-40, no 160-sample repetition, unequal first and second 160-sample windows, and exact PCM/observation SHA-256 `368b845f04f457375788bb6905614827229621066431447e6f951581fcbfb5ad`. Guala self-heard that same pressure; subsequent unattended ticks and real audiovisual requests completed. |
| F-030 | One exact 1 ms layer-13 discharge changes a bounded resident respiratory/laryngeal activation once; the body then carries its own exhalation and glottal cycles across physical intervals and restart until that activation exhausts. | Re-stretching the neuronal discharge, returning to millisecond pressure clicks, using a sensory interval as motor duration, scripting pressure/phonemes/words, allowing body activation to grow without a fixed anatomical bound, or letting an outer envelope assume the newest body width before reading the embedded body version. | Restore the prior V4 body without inventing activation; require one discharge, nonzero pressure in every complete 160-sample glottal cycle of the bounded exhalation, zero additional applied motor quanta during continuation, exact cold persistence, and exact exhaustion without a timer or observer. Embed that exact V4 body in a current organism envelope and prove migration does not consume the following acoustic-length, joint, or cognitive fields. Live closure additionally requires the emitted/self-heard WAV and bounded CPU/RAM/state evidence. | **Closed live on task 1397, 2026-08-31.** Source commits `bd3f0ca4` and `a8ba50cf`; task 1396 failed before health on the exact predecessor-width defect and was recorded rather than hidden. The corrected task restored the same identity and advanced unattended. Live PCM changed from 22/22/27 nonzero samples per 4,000 to 1,646/1,647/1,724/1,725/1,748, persisted through 126 consecutive complete glottal cycles, then exhausted to exact zero. PCM SHA `3e04a2c0...` matched the report; 34 auditory consequences were transported and the next interval carried 442 sound ingresses. Immediate live bounds were one task, 41.9% CPU, 7.18% memory, and 93.8–94.0 MB resident state. This closes duration physics only; no learned-word or intelligibility claim is made. |
| F-031 | A Guala release artifact is built only from the governed 280-file release package and `dsf_ai_service/Dockerfile`; image identity, naming, or a successful generic Docker build is not provenance. | Building or rehearsing the unrelated TFE `web/Dockerfile`; copying generated TFE context files to make that image build; treating a missing `dsf_ai_service` import as an organism/voice failure; pushing or registering an image before proving its packaged entrypoint and candidate native module. | Run `tools/package_guala_release.py` package/context/archive verification first; require the receipt to name the clean candidate commit and `dsf_ai_service/Dockerfile`; inside the digest-pinned image import `dsf_ai_service` and the candidate `guala_core`, verify their paths/provenance, then cold-restore the authenticated predecessor before registration or cutover. | **Added 2026-09-04 after a local attempt-44 invocation exposed the error before production.** Image `sha256:c4c6f902...` was built from `web/Dockerfile`, failed immediately with `ModuleNotFoundError`, and was permanently rejected. The correct governed package for commit `63a2d7da` verified 280 files with receipt `7ee2365f...`; immutable image proof remains the next gate. |

F-031 live closure: the later clean `a7398bc1` package again verified all 280
governed files and selected `dsf_ai_service/Dockerfile`. CodeBuild produced
digest `sha256:92c7353b...`; disposable task
`dsf-ai-native-candidate-cold-restore:275` restored the authenticated body and
exited zero before that same digest was registered as production task 1429.
The rejected `sha256:c4c6f902...` image was never pushed, registered or used.

## Active recurrence corrections

| ID | Status | Rejected mechanism | Closure required before deployment |
|---|---|---|---|
| R-001 | **Open — reproduced on the exact restored production body at tick 224721.** A lawful twelve-second sound completed all 48 auditory/neuronal intervals, then the articulation-to-self-hearing boundary refused with `ArithmeticWidth`. | Treating the 30-second intake refusal ceiling as every shorter recording's physical duration; imposing an unrelated five-second semantic ceiling on an exact finite vocal-pressure timeline; retrying, clipping, scaling, dropping discharges, suppressing the refusal, or buffering an organism's lifetime speech as one waveform. | Preserve the exact capture duration at admission; retain the exact interval timing and every native discharge; replace the five-second ceiling with checked exact allocation for the finite lived intake; preserve recurrent bounded causal intakes so total lifetime speech has no duration limit; prove the previously failing frozen body completes articulation and self-hearing without changing DSF, neuron, contact, carrier, work, heat, or body laws; then verify one non-retried varied sound live and recheck F-001 through F-012. |
| R-002 | **Closed live on task 1322 after 33 recurrences.** Task 1321 proved the downstream-only attempt insufficient at 127 motor recruitments. Commit `dc6673af` removed the upstream authority leak; live recruitment drained 127 -> 96 -> 53, then the exact sleep/wake sequence appeared. | Commit `9228fa81` promoted an unseeded scheduled carrier crossing into `ActiveElectricalFrontierEntry`. That gave the physical maintenance schedule cognitive/action authority and resurrected C-021 attempt 2: background balancing current becomes motor preparation and keeps the organism continuously acting. | Preserve the absence of `scheduled_contact_arrival_frontier`; a scheduler-selected crossing with neither endpoint causal must fail `causal_frontier_crossing`. Preserve the independent changed-endpoint incident-contact wake law, all three seeded motor paths, and the live sequence: tick 258821 action-free recovery/internal re-entry, tick 258822 wake/action, consequence returned by tick 258828 to identity `1cc4e70a...`. |
| R-003 | **Closed live 2026-08-29 on task 1330; current acoustic-state extension live on task 1389.** The eight persisted vocal-tract section areas are appended physical body axes with their own receptors, regulation cells, antagonist motors, one bounded first-use calibration, exact returned proprioception, and 70 bytes of resident acoustic pressure/flow/phase state. | Duplicating the areas beside the body axes; adding phonemes, word targets, stored waveforms or Python speech authority; moving any original terminal address; recurring tonic-pose motor drive; reopening first-use calibration after V3 has recorded it consumed; or restoring the retired fixed 195-byte bridge check after the body gained acoustic state. | Decode legacy 195-byte V1/V2/V3 bodies without moving old addresses, migrate once to the current 265-byte V4 body, and derive every Python/probe width check from the native body authority rather than another hard-coded size; admit the complete 45-axis position source only once; reject sparse consequences as calibration authority; preserve the consumed calibration flag and acoustic state across restart. Commits `88b05fe1`, `b10ccfa2`, and `e8478464`; task 1389, same identity. |
| R-006 | **Closed live on task 1389 after two bridge refusals during the temporal-articulation cutover.** The first candidate migrated the native body to 265 bytes while Python still required 195. The recovery candidate then exposed that the Python causal-interval record omitted all nine newly returned vocal fields, causing unattended and audiovisual publication failures despite completed native physics. | Hard-coded duplicate native-body widths; extending a Rust/Python tuple or named record on only one side; accepting startup health without one real post-start interval; repeatedly treating a bridge mismatch as a physics defect. | The native core is the sole body-width authority; both readiness and causal-interval checks call it. The interval record explicitly carries and validates pressure, body trajectory, sample rate, four mechanical measures, applied work, and stalled work. Live closure requires one autonomous articulation, self-hearing, later unattended advancement, and successful real audiovisual POSTs on the exact production task. |
| R-007 | **Open — directly reproduced on production task 1391 at tick 343291.** The first lawful learned-ordering articulation emitted pressure and self-heard it. That self-hearing hop then caused another layer-13 discharge, which Rust physically settled into the resident vocal body, but the Python boundary recorded only `deferred_recurrent_articulation_count = 1`; it did not retain that hop's articulatory interval evidence or return its emitted pressure through hearing. | Calling the recurrence safely deferred while dropping its exact acoustic consequence; recursively draining an indefinitely self-exciting chain inside one request; stretching one discharge beyond F-029's exact 1 ms event; using the observer pressure cache, TTS, phonemes, scripted waveforms, or an arbitrary repetition cap as causal authority. | Preserve F-029. Require every recurrent body emission to become exactly one subsequent physical acoustic occurrence in the same organism, with no loss, duplication, observer authority, or synchronous run-until-quiet loop. The current propagating sound state must be bounded, cold-restorable, and cleared by physical passage rather than a software timeout. Prove a two-event causal sequence, restart between emission and hearing, eventual quiescence under depleted input, and bounded CPU/RAM/storage before live cutover. |
| R-008 | **Closed live on task 1398, 2026-08-31.** Task 1397 at tick 344995 had all 26 vocal antagonist terminals attached to only two ordering cells, 23 plus 3. This was the same forbidden fan-out class as F-004, reintroduced by V37's general whole-tract returned-sound branch. | Letting general breath, glottis, mouth, perioral or self-hearing evidence identify every vocal motor that discharged nearby in time; preserving unprovable contacts or their dependent formations as learned truth; restoring them after restart. | Commit `fce1ae2c` deleted the ambiguous branch and V38 retired the 26 contacts plus five dependent false formations. Frozen migration was idempotent. Live custodied ticks 345534 and 345558 both report `11->12 = 0`, fixed `12->13 = 26`, 7,353 total contacts, 1,809 neurons, 160 formations and continued 12,000-sample native phonation; the latest current self-hearing counters were zero, so no new self-hearing event is inferred from those samples. One writer remained healthy; startup/settlement CPU averaged 39.6% and memory 7.26%. |
| R-009 | **Open — reproduced on task 1398 through exact raw tick 345645; two candidates rejected locally.** The corrected V38 body preserved zero ambiguous vocal contacts for more than one hundred unattended ticks, but produced no fresh self-hearing and formed no exact-axis layer-11 -> layer-12 route. Reopening the old calibration once was falsified: the exact production body moved and returned precise proprioception for twelve consecutive intervals but produced zero learned vocal routes and zero articulatory discharge, creating reflex motion rather than learning. That code was removed. A deeper diagnostic then proved the supposed exact-axis boundary ignored its moved-axis input: one movement exposed 38–42 transitioned vocal terminal candidates. The source-local correction now derives exactly one moved terminal from authenticated GLBPEV01 arithmetic and passes its focused falsifiers. Adding the already-retained third exact frontier also passed its unit falsifier, but exact production-body replay rejected it as the repair: over six returned-body intervals every exact moved regulation had zero layer-10 affective neighbours, so no frontier width could complete the join. The absence traces to the `6e6d220b` anti-fan-out guard: it requires newly mounted association/regulation cells to have already transferred carriers and restricts pairing to one source occurrence, although the exact body consequence and coexisting world source are separate occurrences in the same physical interval. | Restoring contaminated contacts; reopening calibration on restart; recurring tonic or reflexive body input; treating every transitioned regulation as a moved terminal; retaining more frontiers downstream of absent anatomy; restoring body-wide association/regulation Cartesian pairing; teacher-selected or random motor targets; TTS, phonemes, word tables, scripted pressure, or observer authority. | Preserve the exact-terminal, missing-older-frontier, directed-chain, and ambiguous whole-tract/sound falsifiers. Correct only the layer-10 developmental join: one unambiguous association physically derived in the shared interval may pair only with the exact GLBPEV01-moved terminal's regulation. Static pose, body-only input, ambiguous associations, and non-moved regulations must add zero. Then require one sparse route, fresh native articulation/self-hearing, and cold restore without fan-out or resurrection before R-009 can close. |
| R-004 | **Closed live 2026-08-29 on task 1331.** The bounded read-only causal trace keeps an external or internal retained-formation origin through its later motor and layer-13 events, then discards it immediately after exact articulation completion. | Letting motor completion erase the origin before a later articulation can join it; retaining completed origins indefinitely; or allowing the observer trace to admit, select, delay, or alter any organism transition. | Preserve the motor-then-later-articulation falsifier and the completion-discard falsifier; inspect the changed call graph for observation-only mutation; require unattended ticks to advance when the public observer is stale or unavailable. Commit `e6aa0f86`, task 1331, same identity. Native settlement continued independently while the public snapshot lagged, proving the trace has no cognition authority. |
| R-005 | **Corrected diagnosis; open only for sustained real-time cadence.** Task-1382 ALB windows of 49.580 and 44.347 seconds contained 19 and 16 total native moments, but 8 and 6 of those were separate unattended intakes that started while the audiovisual request waited. One capture itself carries four ordered 250 ms audiovisual moments, plus only physically caused action/self-hearing consequences. Task 1383 removed the server-side starvation; task 1384 and the live S3/CloudFront page removed the read-only observer wait from the browser sender. | Reintroducing route-only admission as sufficient; making camera/microphone transport await `refreshObservation`; counting unrelated unattended moments inside an HTTP wall window as capture expansion; serializing coexisting consequence sources; dropping sensory or consequence physics to improve a timing number. | Keep F-023 through F-026 and F-028 locked. After one hard refresh of the already-open browser, measure consecutive real-device requests: observer refresh must not delay the next bounded four-hop capture, no unattended intake may start after an arrived request, the page retains only the newest complete one-second window, and CPU/RAM/storage remain bounded. Native per-moment settlement remains a separate measured speed item until sustained real-time capture is achieved. |

### R-009 candidate-attempt history — 2026-08-31

- Attempt 1, restored production tick `345645`: rejected before commit. The
  first sparse layer-10 resolver demanded a reached reacted-load regulation
  for every terminal whose authenticated body record reported movement. Real
  production anatomy showed why that was false: a joint may move while its
  load receptor does not cross enough gate work to reach layer 8 in the same
  interval. The exact refusal was `LipAperture/TowardMinimum`, two reached
  regulations, zero matching load regulation. Nothing was deployed.
- Attempt 2, same restored production generation: accepted locally. The rule
  now considers only regulations that physically reached layer 8 and maps
  each through its exact source integration/load ending to a proved moved
  terminal. One unambiguous coexisting sensory/body interval added exactly one
  layer-10 neuron plus one `7->10` and one `8->10` contact. The identical body
  source without the sensory association added zero of all three. This is not
  an utterance claim and not a production closure: layer-11 ordering, exact
  motor discharge, emitted pressure, and self-hearing still must be proved.
- Attempt 3, same restored production generation: rejected locally after 64
  intervals. One exact ordering cell formed, but `11->12` stayed zero because
  the candidate incorrectly demanded that a developmental affective cell keep
  exactly one layer-8 neighbour forever. Later proved body experience had
  lawfully widened that cell. No pressure or articulation occurred.
- Attempt 4, same restored production generation: accepted locally for the
  thought-to-motor boundary. The resolver now follows only the persisted
  founding association/body-regulation pair and ignores later widening for
  route identity. The replay added exactly one `11->12`, one `7->11`, one
  `10->11`, and one layer-11 neuron; the body-only falsifier stayed zero.
  Articulation and pressure remained zero, so R-009 and L-006 remain open at
  the downstream vocal-motor discharge boundary. Nothing was deployed.
- Permanent regression condition: no candidate may restore body-wide
  association/regulation pairing, require an unreached receptor to exist, use
  static pose as movement, or treat a missing load response as authority to
  guess another terminal. The positive sparse delta and the body-only zero
  delta must both remain true on the restored production body.
- Attempt 5, same restored production lineage: accepted locally for the exact
  learned motor boundary. Removing the leftover software seed-membership gate
  allowed the prepared typed motor to discharge four to five of its own
  carriers repeatedly. The old layer-12 -> layer-13 hub still emitted no
  pressure, so this attempt is not an utterance or R-009 closure.
- Attempt 6, exact post-learning body: the first V39 migration refused because
  deleting the rejected hub edge disconnected a retained recurrence witness.
  The repair does not fabricate a replacement history edge. Contact retirement
  now removes any latest recurrence claim that no longer has a physical path,
  while leaving neuronal state and unrelated learned structure resident.
  Focused proof passes.
- Attempt 7, exact post-learning body: accepted locally. V39 retained one exact
  `11->12` vocal-motor route, removed all `12->13` hub contacts, derived one
  parallel `11->13` respiratory route, and a second migration was byte-exact.
  The first continued interval produced four motor events, one articulatory
  recruitment, and 7 nonzero samples among 16 physical pressure samples. The
  candidate is not deployed and R-009 remains open until that pressure returns
  through the resident cochlea and survives cold restart without fan-out.
- Attempt 8, exact post-learning body: accepted locally for consequence
  continuity. The seal had encoded emitted sound but failed to retain it in the
  active resident owner; the resulting snapshot dropped the consequence. One
  ownership assignment fixes that already-recorded R-007 class. The exact
  32-byte pressure hash survived cold restore, entered 34 sound receptors,
  changed 35 inputs, and transitioned 1,301 neurons. A resulting 8,000-byte
  vocal consequence also survived the following cold restore. Live production
  evidence remains required before R-009 or L-006 can close.

- Task-1399 live recurrence, commit `9fd774385`: V39 hub retirement survived
  cutover and cold custody (`12->13 = 0`), but eight real audiovisual windows
  and one grounded world-voice occurrence produced neither an exact
  `11->12` learned vocal route nor native pressure. The two playback controls
  remained disabled because the current process had no native pressure bytes;
  this is the visible consequence of R-009, not a separate control defect.
  The page's `not_mounted` wording is observationally inaccurate and may be
  corrected only to `mounted, no utterance observed`; it may never enable
  playback, infer articulation, or alter cognition.
- Diagnostic attempt 9: a copied-live-body reservoir probe produced no report
  because `cargo test <short-name> -- --exact` did not match the test's fully
  qualified name. The envelope remained intact and production was untouched.
  Earliest deterministic check: require a nonempty report containing exactly
  one record before interpreting any probe output; use the fully qualified
  test name and never repeat the short exact filter.
- Diagnostic attempt 10: the corrected probe at live tick `347243` found the
  mature upstream route intact (62 exact layer-7/layer-8/layer-10 cells and
  273 layer-7/layer-10/layer-11 ordering cells) but zero motor events and zero
  `11->12`. Root cause: `mount_reached_ordering_reach` evaluated the exact
  founding regulation-to-motor path only inside `newly_mounted`, permanently
  excluding an existing ordering cell after V39 route retirement. Regression
  condition: the same exact active founding bond must produce the same one
  typed route on first use and after cold restore/route retirement; an inactive
  or ambiguous bond must still produce none, and no `12->13` contact may exist.
- Diagnostic attempt 11 repeated the short-name-plus-`--exact` Cargo error on
  the first focused candidate proof and ran zero tests. It is explicitly not a
  pass. Permanent command gate: obtain the fully qualified name from
  `cargo test -- --list`, then require output containing `running 1 test` and
  `1 passed`; a zero-test exit code is failure even when Cargo returns zero.
- Candidate attempt 12 passed its exact one-test recurrence falsifier and the
  mature copied production body restored two sparse `11->12` routes plus one
  direct `11->13` route over 64 intervals, with `12->13 = 0`. It produced no
  articulation or pressure. This closes only the existing-ordering lifecycle
  omission; it is not deployable or an L-006 pass. The next diagnostic must
  inspect the exact electrical state of those new route endpoints rather than
  widening history, replaying more lessons, or restoring the old hub.

## Latest correction closure

| ID | Status | Regression scope |
|---|---|---|
| O-001 | **Closed live on task 1283.** The charged retained root motor scheduled itself, emitted native output, moved the persistent world, received all applicable consequences in the same resident identity, and continued unattended. | Every candidate must preserve F-001 through F-011. A lesson is not claimed landed until the native motor discharges, the world applies it, all applicable consequences return to the same identity, and unattended life continues. |

### O-001 current causal boundary — 2026-08-28

- Corrected in the local candidate: signed contact evidence now follows the
  electrical anatomy's physical endpoint order rather than canonical bond
  identity order. The copied live body proves regulation-to-motor arrival.
- Corrected in the local candidate: the explicitly mounted terminal is a
  distinct local carrier path. Incoming contact current may only leave
  retained positive membrane displacement; the terminal then moves the
  motor's own carriers outward, never past zero, only under exact stored-work
  descent, and deposits released work in the cohort thermal reservoir.
- Copied-body evidence: restored production lineage `...00009b` held seven
  separated charges and, on its next reached interval, emitted exactly seven
  local carriers through its positive root-yaw terminal. No contact current
  was relabelled and no observer or action command participated.
- Rejected during development: using the passive-return event as the terminal
  discharge. Its exact crossing on this motor was 20,143 intervals away, so
  that candidate was removed rather than mislabeled as a useful action path.
- Next acceptance: the live world must apply that native discharge, then move,
  return every applicable consequence to identity
  `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`, and unattended ticks must continue.
- Live task 1282 restored the exact candidate and advanced unattended beyond
  tick 208965, but more than twelve intervals reported
  `native_action_consequence=0.0`. The carrier law was intact; the causal-event
  residency scheduled contacts and passive returns but did not schedule a
  charged mounted terminal as its own local event. The copied proof had reached
  every external receptor and therefore masked that missing wake source.
- The correction uses the existing local membrane-event schedule: a mounted
  root-yaw terminal with positive retained displacement is due on the next
  physical clock, enters the selected frontier without being metabolically
  pumped, and reschedules from its exact successor. No full-neuron scan, second
  schedule, timer threshold, or contact-as-output path is introduced.
- Commit `0931c5f2b13ab3cce8afb3d36b7f6b21e0d380bb` is live as sole healthy
  task `dsf-ai-task:1283`, image
  `sha256:0ac8e67b1a97a7bb5b3ab577acd200d9a488dc7d6bcf8760f5118cc24937e3f9`.
  Root motor `...00009b` emitted one positive carrier and the persistent world
  applied a +1 millidegree turn at organism tick 209159. The returned sensory
  occurrence carried sight, sound, touch, smell, taste, body/thermal and one
  changed vestibular tick under the same organism identity. Later unattended
  settlement advanced through at least tick 209176. Public world truth reports
  `she_moves_herself=true`; O-001 is closed.

## Release 1281 cumulative preservation check

| Prior fix | Source and live result |
|---|---|
| F-001 one organism | Task 1281 is the sole writer and reports the same identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1` from one raw `CURRENT` lineage. |
| F-002 unattended life | Tick advanced unattended from 207797 through at least 208070 while public reads remained non-authoritative. |
| F-003 connected-path settlement | No solver or DSF equation changed; live contact-frontier settlement continued on the mounted connected-path law. |
| F-004 fan-out cleanup | Live layer-pair census contains no layer-11/layer-12 contacts; the contaminated ordering-to-motor pool did not return. |
| F-005 event frontier | Live event census remained mounted (`due_now_contacts`, `future_contacts`, and exact selected frontier); no full-sweep authority was restored. |
| F-006 passive return | No return/pump law changed; live census continued to publish separate return events and causal seeds. |
| F-007 custody outside cognition | Live transition stopwatch kept ordinary `seal_ms=0`; the candidate introduced no custody path. |
| F-008 read-only observers | Public contract reports `cognition_authority=false` and `read_advances_organism=false`; reads did not stop unattended advancement. |
| F-009 membrane-owned motor output | The runtime payload source and all four falsifiers are unchanged from `40a0222c`; the new root route prepares the existing motor but no output is claimed before local discharge. |
| F-010 compact root anatomy | V32 removed every contact incident to malformed regulation `...02ecfd`. A real one-millidegree world movement mounted exactly `layer-5 ...00090e -> layer-6 ...002ae9 -> layer-8 ...000ecf (37,393 pF) -> layer-12 ...00009b`; no parallel malformed route exists. |

## Historical reconciliation backlog

The delivery ledger and item ledgers contain older claimed fixes. They are not
silently promoted here. Each older claim will be added only when its current
source reachability and, where relevant, live production evidence have been
rechecked. This prevents a stale historical `complete` label from becoming
architecture authority.

## R-009 motor-coupled vocal-body boundary — 2026-08-31

| Requirement | Current regression bar |
|---|---|
| No passive vocal hub | Current cognition has zero contacts incident to layer 13; any layer-11 -> 13 or layer-12 -> 13 contact is refused. |
| Exact anatomical identity | One persisted resident lineage names the vocal-body effector; migration derives it only from the predecessor's validated unique target. |
| No motor coincidence | Layer 13 can discharge only after an exact same-interval layer-11 -> typed vocal layer-12 transfer and that motor's own discharge. |
| Bounded physical output | Vocal-body output is positive and cannot exceed the causing motor output; carriers and work come from its own neuron and reservoir. |
| Same-organism return | Pressure survives seal/restart and returns through ordinary cochlear ingress to the same identity. |
| No resurrection | Ordinary growth cannot author a layer-13 contact, the V39 route author is deleted, and a second V40 migration is byte-identical. |

Rejected attempts retained permanently: zero-test short-name `--exact` runs;
assuming one layer-13 cell when three exist; treating any vocal-tract motor as
breath; trusting transfers absent from the same interval's motor recruitment;
and using a passive bidirectional contact as vocal-body actuation authority.

Live status: commit `c978fbfb6315482b916b99569b7fb3e663f00a5c` is deployed as
sole healthy task `dsf-ai-task:1400`. Identity continuity, unattended ticks,
ordinary typed motor/body consequence, bounded state size, and approximately
`0.78-1.14 s` native intervals are live-observed. A task-1400 vocal-body
discharge and exact self-hearing consequence have not yet been observed, so
R-009 and L-006 remain open and the playback controls remain truthfully
disabled.

Current-body diagnostic at tick `352577`: zero layer-11 -> layer-12 contacts,
zero contacts incident to layer 13, and zero motor recruitments under a
maximal external-receptor frontier. The next repair may not alter pressure,
self-hearing, playback, or restore an electrical layer-13 bridge; it must begin
at the absent learned ordering-to-vocal-motor route and preserve the retained
`apple` formation at recurrent lineage `...055a`.

### R-009 rejected attempt 18 — task 1401

- Commit `16313bc5e1a41c219d00a9cb90ca8ced9fa586c3` attempted to permit
  prelinguistic respiratory recruitment from one physically prepared,
  discharged closing-glottis motor and to preserve the true layer-8 or
  layer-11 preparation sender in the Python evidence surface. Its isolated
  Rust predicate and Python evidence-join tests passed, but those tests did not
  exercise one complete mature production-body interval.
- The candidate was hot-deployed once as task `dsf-ai-task:1401`. It restored
  the same identity but then refused every sampled unattended interval with
  `resident neuron lineage authority changed`; 22 occurrences were measured
  in task 1401 versus zero in the predecessor task-1400 log. Public generation
  remained `353081`, no native pressure appeared, and no behavioral fix is
  credited.
- Task 1401 was rolled back immediately. Task 1400 restored the same resident
  identity and resumed ordinary advancement through at least ticks
  `353137-353143` without the refusal. Revert commit `902edd0a` removes the
  failed candidate from the active source tree while retaining both commits in
  history.
- Permanent analysis/test consequence: no later R-009 candidate may deploy on
  helper, predicate, tuple, codec, or synthetic evidence alone. It must first
  restore the newest authenticated production body and complete the exact
  initiation -> motor -> respiratory body -> pressure -> byte-identical
  cochlear return -> persistence -> cold restore -> next ordinary interval
  path. The first task-1401 lineage-authority refusal must be localized on that
  copied body before another mechanism is proposed.

### R-009 causal-localization attempt 19 — input-shape mismatch

- Exact task-1401 source on exact copied task-1400 bodies at ticks `352577`,
  `353993`, and `354001` did not reproduce the refusal under the existing
  maximal-external-receptor probe. Those intervals changed `1,366`, `1,339`,
  and `1,341` neurons but recruited zero motors, so the rejected glottal branch
  was never entered. These runs are failed reproduction attempts, not passes.
- The falsified assumption is permanent: a maximal receptor census is not an
  ordinary production interval. The rejected live task deterministically used
  `106` external and `3` regulation causes, selected `1,538` neurons and
  `7,197` contacts, completed cohort settlement, then refused before aggregate
  evidence/commit. A future proof must reproduce that causal shape rather than
  increase receptor coverage.
- The exact stalled tick-`353081` raw body has aged out of the intentionally
  bounded two-generation remote store and cannot be reconstructed from its
  receipt. Current exact task-1400 bodies and an exact production world body
  have been captured read-only instead. No new mechanism may be proposed until
  one of those bodies executes the ordinary production-shaped interval and the
  first failing lineage assertion is identified.
- Restart protection remains an explicit acceptance boundary: a candidate's
  in-process successor must equal published `CURRENT`; cold restore must
  preserve the same identity, learned formations, full seven-field DSF state,
  neurons, contacts, body, and in-flight sensory custody; and the next ordinary
  interval must advance from that exact successor. A narrower fresh restore or
  predecessor overwrite is a failure even if an earlier in-process utterance
  occurred.
- Causal-localization attempt 20 is rejected: a host-namespace `/tmp` bind was
  empty from the Docker daemon's namespace, so the exact task-1401 image made a
  fresh genesis and began at generation `1`. A container run is not copied-body
  proof unless its startup observation first equals the exact copied
  predecessor tick, identity, byte count, and SHA-256. Use a Docker-managed
  volume populated through the daemon boundary; never infer bind visibility.
- Causal-localization attempt 21 reproduced task 1401 with the exact rejected
  production image on an exact copied mature task-1400 body at tick `354137`,
  raw SHA-256
  `619c8615a464266334a6aa75644c209fc625a918b13490d5739b982315a921cf`.
  The first ordinary interval had `106` external and `3` regulation causes and
  refused after cohort settlement with the same lineage-authority error.
  `CURRENT`, the current generation, tick, identity, and learned body remained
  unchanged after every refusal; no failed successor was published. This is
  accepted reproduction evidence, but not yet localization and not speech.

### R-009 causal-localization attempt 22 — identical-input control

- The exact accepted task-1400 production image
  `sha256:b91aba6fb8e13081be9db4646d69f6a66e0974f49908c1479fbac06a744fce89`
  identified itself as commit `c978fbfb6315482b916b99569b7fb3e663f00a5c`
  and was started network-disabled with four CPUs and 16 GiB on a fresh
  Docker-managed volume. Before startup, that volume matched attempt 21
  byte-for-byte: tick-`354137` `CURRENT` SHA-256
  `18316fbf42c8f8e37c2468f35c7c3ea800019f6bd6c2a47a7b3194321df93839`,
  world SHA-256
  `be1cb8b166324d4188c6bf7d1dce0def98961a0f75ea5538b4eb873941cf6b4e`,
  current compact-object SHA-256
  `d0fe3016834564baea2bb074e0fe58c38add2e4dffe23ef7e9cc5c8667af1537`,
  and predecessor compact-object SHA-256
  `588f5a81efec88247a3a7c155137be96d2a8d2874e399170b6c5414891d090c2`.
- Its first ordinary interval had exactly the attempt-21 candidate shape:
  `external=106`, `regulation=3`, `frontier=4338`, `total=746`, selected
  `1550` neurons and `7210` contacts. Unlike task 1401, task 1400 crossed
  `guala-contact-phases`, completed its physical transition, and published
  generation `354138`; it then continued without a lineage refusal through
  generation `354163`. This controlled A/B excludes the copied mature body,
  copied world, resource envelope, and ordinary causal input as the refusal's
  source. The refusal is introduced by task 1401's four-file change set.
- This is localization to the rejected change set, not yet localization to one
  assertion and not speech. The control emitted no claimed conversational
  result. The exact first assertion, the glottal recruitment that reaches it,
  all downstream state/persistence effects, and cold-restart behavior remain
  required before a repair can be designed.
- Speech completion is now explicitly end-to-end and human-facing: one live
  microphone-clocked sequence must pair each camera frame with its exact audio
  hop, reach the same resident organism, cause learned substrate-owned vocal
  action, produce the exact audible speaker body returned through self-hearing,
  and support a subsequent causally related turn. Pressure bytes, an enabled
  button, an isolated WAV, or a one-off utterance cannot close speech or
  conversation. F-023 through F-030, R-001, R-005, R-007, and R-009 are one
  combined acceptance boundary for that proof.

### R-009 causal-localization attempt 23 — accepted-successor cold restore

- The attempt-22 task-1400 control was stopped only after its copied
  tick-`354137` predecessor had advanced and published through generation
  `354163`. The same exact accepted image and the same Docker-managed volume
  were then cold-started without reseeding or replacing any file. Its first
  new native interval was generation `354164`, followed by `354165-354167`,
  with no lineage-authority refusal. It did not restart at `354137`, select the
  older retained generation, create genesis, or replace the accepted
  successor with the original copied body.
- After the second stop, `CURRENT` changed again to SHA-256
  `447df664d12c1ecb3a3f921cc686e8a6670c67b3894ab9f339c39010aef42d70`;
  the bounded generation directory retained exactly two objects. This proves
  the accepted task-1400 restore/publish path advances from its latest
  successor under the copied-body control. It does not prove a future speech
  candidate: that candidate must repeat this boundary with the emitted
  pressure and in-flight self-hearing body present.
- The current public page is byte-identical to the repository
  `gualaloom.html` at SHA-256
  `0fdeeb566979b553d1a4f5e71fb0c2162d22588747ecbb1d248c25c41cfcf574`
  and contains the audio-worklet microphone clock, microphone-clocked camera
  pairing, bounded transport retry, and opt-in continuous exact-pressure
  speaker playback. The live task-1400 observation nevertheless reports no
  camera or microphone batch committed in the current process and no native
  articulation. Presence of these page mechanisms is not live conversational
  proof.

### R-009 causal-localization attempt 24 — exact failed invariant

- The copied tick-`354137` raw body contains `GLCOG040` at raw offset `684` and
  exact marker byte `0` at raw offset `710`; its persisted
  `vocal_articulatory_effector_lineage` is `None`. Three uncontacted historical
  layer-13 neurons remain resident at topologies `0`, `1`, and `2`, but the body
  supplies no authority to choose among them.
- Task 1400 does not enter vocal-body co-recruitment because the body has no
  learned layer-11 -> vocal layer-12 transfer. Task 1401 newly enters from the
  exact layer-8 reached-load preparation of a discharged closing-glottis motor.
  Its subsequent exact-one marker lookup yields zero and returns
  `NeuronLineageAuthorityChanged`. Exact binary disassembly confirms the vector
  length comparison at `0x37683f` and the error-discriminant write at
  `0x376b34`.
- This localizes the first refusal completely. The task-1401 executable delta
  consists of three production runtime files; the remaining changed files are
  ledgers, a measurement probe, and a synthetic test. No persistence or L0-L4
  field path changed. The tests missed the failure because they supplied the
  downstream motor/articulatory tuples without the marker-absent mature body.
- The governing complete analysis and mandatory copied-body acceptance matrix
  are `docs/GUALA_TASK1401_COMPLETE_CAUSAL_IMPACT_ANALYSIS_2026-08-31.md`.
  A later repair may not select an old layer-13 cell, retry task 1401 unchanged,
  or call reflex pressure learned speech. It must mount one dedicated bounded
  vocal-body identity from unclaimed anatomy, retain every existing neuron and
  contact, prove exact emitted/self-heard custody across cold restart, reach
  physical quiescence, and finally complete a synchronized human audiovisual
  conversation before R-009 or L-006 closes.

### R-009 repair attempt 25 — dedicated identity only

- V41 mounts exactly one new, electrically isolated intrinsic layer-13 cell
  for a mature marker-absent V40 body and persists it as the dedicated vocal
  effector. It does not choose any historical layer-13 lineage. Marker-present
  bodies preserve their authority, and pre-embodied bodies without vocal
  anatomy remain unmounted.
- On the exact copied tick-`354137` body, the isolated candidate binary proved
  `1810 -> 1811` neurons, `107623033 -> 107625626` cognitive bytes, three
  unchanged historical layer-13 cells, new lineage
  `474c4e4c494e4531000000000000008e`, zero changed prior state or contacts,
  and a byte-identical second migration.
- Candidate/control compilation outputs were separated after a shared Cargo
  directory produced an invalid zero-test apparent pass. With distinct
  binaries, the candidate's two V41 tests both executed and passed.
- Full serial library comparison is exact: untouched `faff9e06` has
  `549 passed, 16 failed, 11 ignored`; V41 has
  `551 passed, 16 failed, 11 ignored`; the 16 failing names are identical.
  Thus V41 adds two passing tests and zero new failures. The inherited failures
  remain open evidence, not a waived green suite.
- R-009 remains open. This attempt proves anatomy identity only, not body
  discharge, pressure, same-organism hearing, recurrence, restart custody,
  physical rest, speaker audibility, or conversation. No deployment is
  authorized.

### R-009 repair attempt 26 — flattened multi-interval recruitment refusal

- The first exact copied-body rehearsal of local commit
  `2440a9ed56834afeca70ed19e41680608f63b57e` is permanently rejected. Its
  image and extension hashes were recorded before startup, its input matched
  all four original tick-`354137` production-copy hashes, it had no network,
  and it made no production or registry change.
- Native crossed the V41 migration and ran generations `354138-354148`, then
  Python refused the third aggregate with
  `motor-unit recruitment repeated a lineage`. The refusal happened twice.
  Each time the next native calculation restarted at `354138`, not the reached
  frontier, proving rollback of the whole unsealed trajectory and repeated
  computation over a world that had already advanced.
- Cause: interval evidence retains lawful temporal boundaries and validates
  motor/articulatory ownership within each one; the top-level transport also
  concatenates those events for presentation. Python incorrectly requires
  lineage uniqueness across that flattened multi-interval aggregate. The
  permanent regression rule is: repeated lineage is forbidden within one
  interval, lawful across distinct intervals, and every aggregate event must
  equal the ordered concatenation of the independently validated interval
  events. Cross-interval lookup or carrier borrowing remains forbidden.
- The stopped failure volume is retained with post-stop `CURRENT` tick
  `354144`, pointer SHA-256
  `a99c8b6c93a6fba3c8cacad0a75808c04cc16425331a9131852e4843bc00c713`,
  raw state SHA-256 `3d824751...`, predecessor raw SHA-256 `6e6d2001...`,
  exactly two generation objects, and changed world SHA-256
  `0e4b4989010348c50e0218250e6bea12e62d75ed203983b5d981ed36deb18bde`.
  It is evidence, not an admissible future candidate seed.
- R-009 and L-006 remain open. No pressure or speech claim survives this
  refusal, and deployment remains prohibited.

### R-009 repair attempt 27 — pressure cannot be called self-hearing

- Commit `5f0df594` on a fresh exact copied body passed the attempt-26 boundary
  and advanced monotonically from `354137` through `354182` with no refusal.
- A public tick-`354158` record paired nonzero pressure and four moving body
  ports with zero layer-13 recruitment, zero applied motor quanta, and zero
  self-hearing evidence, yet labelled self-hearing committed. Nine transport
  records independently reported zero native self-hearing time.
- Permanent rule: nonzero residual pressure is not a layer-13 discharge;
  emitted pressure is not heard pressure; and an observation may claim
  self-hearing only after the exact in-flight bytes cause a later ordinary
  cochlear/body interval. Attempt 27 is rejected as speech proof.
- Scope rule: the immediate repair is deliberately reduced to prelinguistic
  embodiment. An existing layer-8 reached-load closing-glottis discharge may
  drive the typed motor and dedicated vocal body without first requiring a
  layer-11 learned ordering route. That removes the repeatedly failing learned
  route from this gate; it does not authorize calling reflex phonation learned
  speech.
- The tick-`354182` envelope cold-restored an exact tick-`354180` in-flight
  consequence: pressure SHA-256 `96b9644d...` over 40,000 bytes and body SHA-256
  `8bf4af3c...` over 160,000 bytes. Normal restart continued at `354183`, but
  every completed transport through persisted checkpoint `354225` still
  reported `native_self_hearing=0.0ms`. Repeating intervals did not consume the
  occurrence. The stopped isolated checkpoint has pointer SHA-256 `4d57aa35...`,
  current raw SHA-256 `1777ec33...`, predecessor raw SHA-256 `c886d63c...`, and
  world SHA-256 `5297e993...`. This restart-consumption failure remains open.
- Exact migration-isolation proof: real migration startup on a fresh
  tick-`354182` clone changed raw state `a5f4e5bc...` at `107639965` bytes to
  `3637dc55...` at `107439953` bytes while retaining identity and tick, and
  changed source tick/pressure/body to `None`. The `200012` lost bytes are
  exactly the encoded 12-byte header plus five signed-16 channels over 20,000
  samples. Source parses this bounded field, omits it from the migration tuple,
  and passes literal `None` to the encoder. Permanent rule: every structural
  migration preserves a current in-flight acoustic consequence byte-for-byte;
  only the later authenticated cochlear admission may consume it exactly once.

### R-009 repair attempt 45 — isolated respiratory thermal deadlock

- The attempt-44 voice organ is not reusable on the later mature task-1429
  body. Exact tick-434112 copied-body tests produced two simultaneous learned
  vocal-motor discharges but zero dedicated layer-13 recruitment over three
  native frontiers and 32 production-shaped intervals.
- The persisted layer-13 reservoir is at approximately 128.755740 of 129 zJ
  thermal capacity. Its real two-carrier act releases approximately 0.320140
  zJ, exceeding its approximately 0.244260-zJ headroom. The thermal deposit is
  refused, and current code silently omits the entire respiratory act.
- Permanent rule: every specially co-recruited motor cell must receive its
  ordinary bounded local metabolic/environment settlement. An electrically
  isolated effector may not accumulate discharge heat while being unreachable
  from the only heat-export path. Capacity inflation, state reset, dropping
  carriers, free heat deletion, or synthetic pressure are prohibited repairs.
- Attempt 45 does not prove a word. After exact mature-body reuse and cold
  repeat, the retained vocal controls must still prove ordered multi-posture
  production rather than their current simultaneous event.
- The candidate passed 512 exact copied-production whole-roster hops with 256
  dedicated respiratory recruitments, 469 pressure occurrences, 468 later
  self-heard occurrences, constant resident bytes, exact cold restore and no
  AWS alarm. The vocal coordinates were identical across all 512 hops. This
  permanently separates reusable phonation from the still-open learned
  posture-ordering defect; do not reopen breath or renderer tuning to explain
  the absence of a word.

### R-009 repair attempt 46 — native whole-word control accepted

- Joseph accepted every bounded native-organ candidate as recognizable
  `ma-ma` and selected **Mama-A**. The slightly robotic tonal character is a
  deferred refinement, not a reason to reopen the organ or renderer.
- Permanent separation: attempt 46 proves actuator capacity only. Its
  test-supplied posture trajectory may never enter the organism as a word,
  phoneme program, sequence table, replay, or observer command. The remaining
  repair is organism-owned causal ordering of learned typed vocal motors.

### R-009 repair attempt 47 — fixed learned-motor output rejected

- The production task-1429 learned L11/L12 transducer assigns exactly one
  carrier to every eligible motor branch. Exact copied-body ranges prove the
  lawful descending region varies from one carrier to at least 64 with current
  physical state. The literal is a developer-authored action magnitude, not a
  developmental law.
- Replacing one with another constant, fixed fraction, sampled maximum, or
  output selected for audibility is permanently prohibited. Strict aggregate
  work descent and charge conservation do not by themselves cause a nonzero
  motor allocation.
- The three-terminal substitute also edits endpoint carrier counts after the
  ordinary contact transition has already fixed its phase, current, work,
  heat, and persisted successor. It must be replaced in full, not tuned.
- Repeating the existing motor gradient-pump range is prohibited unless a new
  physical energy source is first named. Earlier history and the exact
  task-1429 copy both prove the two vocal endpoints have less available work
  than one inward carrier requires.
- The durable governing design, accepted subsystem boundaries, rejected
  mechanisms, and test doctrine are reconciled in
  `GUALA_DEVELOPMENTAL_VOICE_ORGAN_SPECIFICATION_AND_DESIGN.md`.
- Candidate 47C is rejected before implementation: the A-011.6 transition-work
  phase is sub-quantum junction-channel-transition bookkeeping whose completed
  work dissipates. It may not be reinterpreted or spent as a motor-energy
  reservoir, even on a learned L11/L12 contact.
- Candidate 47D is rejected despite nonzero copied-body output: adding real
  source work to recovery `available` manufactures conserved recovery material.
- Candidate 47E's grouped copied-body harness establishes a narrower surviving
  fact: the actual source-transition work can pay the exact shortfall directly
  while source heat falls by the same amount. Four reached motors discharge
  state-varying extents `1,2,7,1`; 96/96 regimes conserve work and recovery
  material; zero source and seven-bond severing are silent. Do not promote this
  to production until absolute learned-bond coupling, actual transition heat,
  permutation, exhaustion, cold continuation, typed consequences and resource
  bounds are proved.
